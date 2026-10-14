"""Utterance coding: every utterance of a pod's transcript coded on the
dimensions of the session's coding scheme (coding_schemes.py: the built-in
negotiation scheme, or one an instructor made) by the local llama-server,
rolled up per team and per speaker. Schemes with the negotiation
dimensions also get the de-escalation timeline and per-team opening moves.
Built for the Kellogg "Viking" case; src/server/negotiation_codebook.json
is that scheme. Team names come from the session's pod setup
(pod_config.py); nothing here knows a case's sides by name.

Import-light on purpose: everything above ``run_coding`` is pure (prompt,
chunking, parsing/repair, pair merging, rollup, timeline) and runs with a fake
LLM in tests; the database and queue are imported inside the functions that
need them.

Two setups. One device per breakout group: the run codes that pod's
transcript and the instructor assigns speaker tags to teams afterwards
(``teams``). Two devices per group, one on each side of the table
(session.negotiation_paired, session_device.negotiation_side): a "paired"
run codes both pods' transcripts merged on the session clock, every
utterance belongs to its device's side, and near-duplicates (both
microphones hear the whole table) are dropped before coding.

The LLM contract (verified 2026-09-30 against qwen3.8-27b-uncensored): thinking
must be OFF — ``chat_template_kwargs.enable_thinking=false`` in the request
AND ``/no_think`` at the end of the prompt — or Qwen 3 spends the whole token
budget thinking and returns nothing; temperature 0; strict JSON array back.
"""
import difflib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_LLM_MODEL = "qwen3.8-27b-uncensored"
LLM_TIMEOUT = 300
LLM_RETRIES = 2
LLM_MAX_TOKENS = 4096   # ~45 tokens per coded utterance; a chunk needs < 2000
CHUNK_SIZE = 40         # utterances coded per call
CONTEXT_SIZE = 5        # preceding utterances shown read-only
PEAK_WINDOW = 60        # s: the window with the most escalating utterances
CALM_WINDOW = 120       # s: no escalation this long = sustained de-escalation
# Paired sessions: both microphones hear the whole table, so the two
# transcripts are merged on the session clock (transcript.start_time counts
# from the session's creation on every pod) and the far side's copy of an
# utterance is dropped.
PAIR_START_TOLERANCE = 1.5   # s: starts this close are the same moment ...
PAIR_OVERLAP_MIN = 0.5       # ... or the two overlap this share of the shorter one
PAIR_TEXT_SIMILARITY = 0.5   # token ratio from which two copies are one utterance

# Placeholder team names for a session whose setup names none; every real
# run takes its names from the session (run_names / device_team_names).
DEFAULT_TEAMS = ("Team A", "Team B")
TEAMS = DEFAULT_TEAMS
UNASSIGNED = "unassigned"
DIMENSIONS = ("emotion", "rip", "frame", "listening")   # the built-in negotiation scheme's
CODEBOOK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "negotiation_codebook.json")


def llm_url():
    return os.environ.get("NEGOTIATION_LLM_URL") or DEFAULT_LLM_URL


def llm_model():
    return os.environ.get("NEGOTIATION_LLM_MODEL") or DEFAULT_LLM_MODEL


def load_codebook(path=CODEBOOK_PATH):
    """The built-in negotiation codebook, in the engine shape (with labels)."""
    import coding_schemes as coding_scheme
    if path == CODEBOOK_PATH:
        scheme = coding_scheme.builtin_scheme(coding_scheme.BUILTIN_NEGOTIATION)
        return coding_scheme.to_codebook(scheme, scheme["ref"])
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def codebook_for_session(session):
    """The session's scheme as a codebook: its ref resolved (built-in or the
    instructor's stored scheme), the built-in negotiation scheme when the
    session has none or it was deleted."""
    import coding_schemes as coding_scheme
    import database
    ref = getattr(session, "coding_scheme", None)
    scheme = coding_scheme.resolve(ref, database.get_coding_scheme_dict)
    if scheme is None:
        return load_codebook()
    return coding_scheme.to_codebook(scheme, ref)


def codebook_for_device(session_device_id):
    import database
    device = database.get_session_devices(id=session_device_id)
    session = database.get_sessions(id=device.session_id) if device is not None else None
    return codebook_for_session(session)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- prompt

def _codebook_text(codebook):
    # Per dimension: the rule for the whole dimension, one decision rule plus
    # examples per code, the listening conventions, and the calibration
    # examples worded so they never read as extra codes (the model once
    # answered "strong listening" as a code).
    lines = []
    for dim, spec in codebook["dimensions"].items():
        rule = "list every code that applies, [] if none" if spec["multi"] else "exactly one code"
        lines.append("%s (%s). %s" % (dim, rule, spec.get("guidance", "")))
        for code, entry in spec["codes"].items():
            examples = "; ".join('"%s"' % e for e in entry.get("examples") or [])
            lines.append("  - %s: %s%s" % (code, entry["definition"], " e.g. " + examples if examples else ""))
        for convention in spec.get("conventions") or []:
            lines.append("  * " + convention)
        notes = spec.get("notes") or {}
        for kind in ("strong", "weak"):
            if notes.get(kind):
                lines.append("  (examples of %s %s moves, not codes: %s)"
                             % (kind, dim, "; ".join('"%s"' % e for e in notes[kind])))
        lines.append("")
    return "\n".join(lines).rstrip()


def _line(u):
    return "[%d] %s: %s" % (u["index"], u.get("speaker_tag") or "?", (u.get("text") or "").strip())


def build_prompt(codebook, utterances, context, names=DEFAULT_TEAMS):
    """Chat messages coding ``utterances`` with ``context`` (the preceding
    utterances) shown read-only. Each utterance is {index, speaker_tag, text};
    the index is its position in the WHOLE transcript and the model echoes it
    back, so chunking never renumbers anything. ``names`` are the two sides
    as the session calls them."""
    facts = "".join("- %s\n" % f for f in codebook.get("case_facts") or [])
    sides = " versus ".join("%s's team" % n for n in names)
    dims = list(codebook["dimensions"].items())
    shape = ", ".join('"%s": %s' % (k, '["<code>", ...]' if spec.get("multi") else '"<code>"') for k, spec in dims)
    about = codebook.get("description") or ""
    system = (
        "You code utterances from a recorded classroom discussion (%s)%s. "
        "For EVERY utterance in the CODE section give codes on %d dimension%s, using ONLY the codes "
        "defined here. Judge each utterance by its own words in the light of what came before; apply "
        "the decision rules literally.\n\n"
        % (sides, " — " + about if about else "", len(dims), "" if len(dims) == 1 else "s")
        + ("CONTEXT FACTS (so references in the transcript resolve):\n" + facts + "\n" if facts else "")
        + _codebook_text(codebook) + "\n\n"
        "Output a JSON array only: no prose, no markdown fence, no thinking. One object per "
        "utterance of the CODE section, in order, shaped "
        '{"i": <index>, ' + shape + "}. "
        "Never output objects for the CONTEXT section.")
    lines = []
    if context:
        lines.append("CONTEXT (what was said just before; do not code):")
        lines.extend(_line(u) for u in context)
        lines.append("")
    lines.append("CODE (one object per line):")
    lines.extend(_line(u) for u in utterances)
    lines.append("")
    lines.append("/no_think")
    return [{"role": "system", "content": system},
            {"role": "user", "content": "\n".join(lines)}]


def chunks(utterances, size=CHUNK_SIZE, context=CONTEXT_SIZE):
    """(context, chunk) pairs in transcript order; indices are untouched."""
    for start in range(0, len(utterances), size):
        yield utterances[max(0, start - context):start], utterances[start:start + size]


def _utterance(r, team=None):
    u = {"transcript_id": r.id, "start_time": r.start_time, "length": r.length,
         "speaker_tag": r.speaker_tag, "text": r.transcript,
         "session_device_id": getattr(r, "session_device_id", None)}
    if team:
        u["team"] = team
    conf = _attribution_confidence(r)
    if conf is not None:
        u["confidence"] = conf
    return u


def _attribution_confidence(r):
    # The live diarizer stores {percent, sim, margin[, closed_world]} under
    # voice_features.confidence; absent on older rows and post-hoc rows.
    getter = getattr(r, "_voice_features_json", None)
    vf = getter() if callable(getter) else None
    conf = (vf or {}).get("confidence") if isinstance(vf, dict) else None
    return conf if isinstance(conf, dict) else None


def utterances_from_rows(rows, team=None):
    # Transcript rows -> the dicts the engine works on; index = position.
    # ``team`` (a device with a fixed side) stamps every utterance.
    return [dict(_utterance(r, team), index=i) for i, r in enumerate(rows)]


# ------------------------------------------------------- paired devices

def _tokens(text):
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def text_similarity(a, b):
    """0..1 token-sequence similarity; 0 when either side has no words."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return difflib.SequenceMatcher(None, ta, tb).ratio()


def _span(u):
    start = float(u.get("start_time") or 0)
    return start, start + max(float(u.get("length") or 0), 0.0)


def same_moment(a, b):
    """Two utterances from different devices that started within
    PAIR_START_TOLERANCE of each other, or overlap for at least
    PAIR_OVERLAP_MIN of the shorter one."""
    a0, a1 = _span(a)
    b0, b1 = _span(b)
    if abs(a0 - b0) <= PAIR_START_TOLERANCE:
        return True
    shorter = min(a1 - a0, b1 - b0)
    return shorter > 0 and (min(a1, b1) - max(a0, b0)) / shorter >= PAIR_OVERLAP_MIN


def match_strength(u):
    """How surely the device's own roster claimed the words: the diarizer's
    similarity (a below-gate closed-world pick demoted), 0.5 for a tag with
    no stored confidence, 0 for an unmatched voice. The nearer microphone
    hears its own speakers best, so the stronger copy is that side's."""
    if not u.get("speaker_tag"):
        return 0.0
    conf = u.get("confidence") or {}
    sim = conf.get("sim")
    if sim is None:
        return 0.5
    try:
        strength = float(sim)
    except (TypeError, ValueError):
        return 0.5
    return strength - (0.3 if conf.get("closed_world") else 0.0)


def _prefer(a, b):
    # (winner, loser) between two copies of one utterance: the stronger
    # attribution, then the fuller text, then the earlier row.
    sa, sb = match_strength(a), match_strength(b)
    if abs(sa - sb) > 0.05:
        return (a, b) if sa > sb else (b, a)
    la, lb = len(_tokens(a.get("text"))), len(_tokens(b.get("text")))
    if la != lb:
        return (a, b) if la > lb else (b, a)
    return (a, b) if a["transcript_id"] <= b["transcript_id"] else (b, a)


def merge_paired(rows_by_device, sides):
    """One conversation from two devices' transcripts. ``rows_by_device`` maps
    device id -> transcript rows, ``sides`` device id -> team. Rows are put
    on one timeline; for a pair of same-moment utterances from the two
    devices, a text match (>= PAIR_TEXT_SIMILARITY) keeps the better-
    attributed copy ("duplicate"), an unmatched voice against a matched one
    drops the unmatched copy ("bleed": the far side heard faintly), and
    anything else stays (both sides really talking at once). Returns
    (utterances in time order, re-indexed, each with team and
    session_device_id; dropped: [{transcript_id, kept_transcript_id, reason,
    similarity}])."""
    pool = []
    for device_id, rows in rows_by_device.items():
        pool.extend(_utterance(r, sides.get(device_id)) for r in rows)
    pool.sort(key=lambda u: (u["start_time"], u["transcript_id"]))
    kept, dropped, settled = [], [], set()
    for i, u in enumerate(pool):
        if u["transcript_id"] in settled:
            continue
        horizon = _span(u)[1] + PAIR_START_TOLERANCE
        best, best_sim = None, -1.0
        for v in pool[i + 1:]:
            if v["start_time"] > horizon:
                break
            if v["session_device_id"] == u["session_device_id"] or v["transcript_id"] in settled:
                continue
            if not same_moment(u, v):
                continue
            sim = text_similarity(u["text"], v["text"])
            if sim > best_sim:
                best, best_sim = v, sim
        if best is None:
            kept.append(u)
            continue
        if best_sim >= PAIR_TEXT_SIMILARITY:
            winner, loser, reason = _prefer(u, best) + ("duplicate",)
        elif bool(u.get("speaker_tag")) != bool(best.get("speaker_tag")):
            winner, loser = (u, best) if u.get("speaker_tag") else (best, u)
            reason = "bleed"
        else:
            kept.append(u)
            continue
        settled.add(loser["transcript_id"])
        settled.add(winner["transcript_id"])
        kept.append(winner)
        dropped.append({"transcript_id": loser["transcript_id"], "kept_transcript_id": winner["transcript_id"],
                        "reason": reason, "similarity": round(best_sim, 2)})
    kept.sort(key=lambda u: (u["start_time"], u["transcript_id"]))
    for i, u in enumerate(kept):
        u["index"] = i
    return kept, dropped


# ------------------------------------------------------------------- llm

def call_llm(messages, url=None, model=None, timeout=LLM_TIMEOUT, retries=LLM_RETRIES):
    """One chat completion against the OpenAI-compatible llama-server; returns
    the assistant text. Transport/HTTP/shape failures are retried."""
    url = url or llm_url()
    body = json.dumps({
        "model": model or llm_model(),
        "messages": messages,
        "temperature": 0,
        "max_tokens": LLM_MAX_TOKENS,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    last = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(2 * attempt)
        try:
            req = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except (urllib.error.URLError, OSError, ValueError, LookupError, TypeError) as e:
            last = e
            logging.warning("negotiation coding: LLM call failed (attempt %d of %d): %s",
                            attempt + 1, retries + 1, e)
    raise RuntimeError("negotiation LLM at %s failed after %d attempt(s): %s" % (url, retries + 1, last))


# ------------------------------------------------------- parse and repair

_SEP = re.compile(r"[\s,]*")


def extract_array(text):
    """The outermost JSON array of objects in ``text``: tolerates prose or a
    code fence around it, and a truncated tail (every whole object before the
    cut is kept). [] when there is none."""
    text = text or ""
    starts = [m.start() for m in re.finditer(r"\[", text)]
    end = text.rfind("]")
    for s in starts:
        if end <= s:
            break
        try:
            arr = json.loads(text[s:end + 1])
        except ValueError:
            continue
        if isinstance(arr, list) and arr and all(isinstance(x, dict) for x in arr):
            return arr
    decoder = json.JSONDecoder()
    for s in starts:
        items, pos = [], s + 1
        while True:
            pos = _SEP.match(text, pos).end()
            if pos >= len(text) or text[pos] != "{":
                break
            try:
                obj, pos = decoder.raw_decode(text, pos)
            except ValueError:
                break
            items.append(obj)
        if items:
            return items
    return []


def _norm(value):
    if value is None:
        return None
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _coerce(value, spec):
    # (validated value, number of invalid codes seen) for one dimension.
    known = spec["codes"]
    if spec["multi"]:
        if value is None:
            return [], 0
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return [], 1
        kept, bad = [], 0
        for v in value:
            v = _norm(v)
            if v in known:
                if v not in kept:
                    kept.append(v)
            else:
                bad += 1
        return kept, bad
    v = _norm(value)
    if v in known:
        return v, 0
    return spec["default"], 1


def _defaults(codebook):
    return {dim: (list(spec["default"]) if spec["multi"] else spec["default"])
            for dim, spec in codebook["dimensions"].items()}


def validate_codes(items, codebook, indices):
    """{index: codes} for every index in ``indices`` from the model's items.
    An unknown code becomes the dimension's default and counts as invalid; an
    utterance the model skipped gets every default and counts once."""
    by_index = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            i = int(it.get("i", it.get("index")))
        except (TypeError, ValueError):
            continue
        by_index.setdefault(i, it)
    out, invalid = {}, 0
    for i in indices:
        it = by_index.get(i)
        if it is None:
            invalid += 1
            out[i] = _defaults(codebook)
            continue
        codes = {}
        for dim, spec in codebook["dimensions"].items():
            codes[dim], bad = _coerce(it.get(dim), spec)
            invalid += bad
        out[i] = codes
    return out, invalid


def code_utterances(codebook, utterances, llm=None, size=CHUNK_SIZE, context=CONTEXT_SIZE, names=DEFAULT_TEAMS):
    """Every utterance coded, chunk by chunk. Returns (codes aligned with
    ``utterances``, each the utterance dict plus its four codes; invalid_codes)."""
    llm = llm or call_llm
    coded, invalid = [], 0
    for ctx, chunk in chunks(utterances, size, context):
        items = extract_array(llm(build_prompt(codebook, chunk, ctx, names)))
        if not items:
            raise RuntimeError("LLM returned no parseable codes for utterances %d-%d"
                               % (chunk[0]["index"], chunk[-1]["index"]))
        by_index, bad = validate_codes(items, codebook, [u["index"] for u in chunk])
        invalid += bad
        coded.extend(dict(u, **by_index[u["index"]]) for u in chunk)
    return coded, invalid


# ------------------------------------------------------ rollup, timeline

def team_of(speaker_tag, teams, names=TEAMS):
    team = (teams or {}).get(speaker_tag)
    return team if team in names else UNASSIGNED


def team_of_code(code, teams, names=TEAMS):
    """A coded utterance's team: the one stamped on it (its device's side
    in a paired run) else its speaker tag's assignment. ``names`` are the
    session's team names (pod setup), the Viking pair by default."""
    team = code.get("team")
    return team if team in names else team_of(code.get("speaker_tag") or "", teams, names)


def other_team(team, names=TEAMS):
    return names[1] if team == names[0] else names[0]


def _bucket(codebook):
    b = {"utterances": 0}
    for dim, spec in codebook["dimensions"].items():
        b[dim] = {code: 0 for code in spec["codes"]}
    return b


def _tally(bucket, code):
    bucket["utterances"] += 1
    for dim, counts in bucket.items():
        if not isinstance(counts, dict):   # "utterances", a speaker bucket's "team"
            continue
        value = code.get(dim)
        for c in (value if isinstance(value, list) else [value]):
            if c in counts:
                counts[c] += 1


def rollup(codes, teams, codebook=None, names=TEAMS):
    """Counts of every code per team (each of ``names``, plus unassigned)
    and per speaker tag; ``teams`` maps speaker_tag -> team."""
    codebook = codebook or load_codebook()
    by_team = {t: _bucket(codebook) for t in tuple(names) + (UNASSIGNED,)}
    by_speaker = {}
    for code in codes:
        tag = code.get("speaker_tag") or ""
        team = team_of_code(code, teams, names)
        _tally(by_team[team], code)
        # Paired runs can carry the same tag on both sides (two unmatched
        # voices, or one name enrolled on both laptops): keyed apart.
        key = tag if tag not in by_speaker or by_speaker[tag]["team"] == team else "%s (%s)" % (tag, team)
        if key not in by_speaker:
            by_speaker[key] = dict(team=team, **_bucket(codebook))
        _tally(by_speaker[key], code)
    return {"by_team": by_team, "by_speaker": by_speaker}


def timeline(codes, codebook=None):
    """Landmarks in transcript seconds (None when the code never occurs;
    None altogether for a scheme without an escalating emotion code):
    the first escalating utterance; the start of the PEAK_WINDOW with most
    escalating utterances; the first utterance after the first escalation
    that opens a CALM_WINDOW with no escalation (a window the transcript
    ends inside counts: the group stayed calm to the end); the first
    future_problem_solving move."""
    if codebook is not None:
        import coding_schemes as coding_scheme
        if not coding_scheme.analytics(codebook)["timeline"]:
            return None
    esc = sorted(c["start_time"] for c in codes if c.get("emotion") == "escalating")
    first = esc[0] if esc else None
    peak, peak_n = None, 0
    for t in esc:
        n = sum(1 for e in esc if t <= e < t + PEAK_WINDOW)
        if n > peak_n:
            peak, peak_n = t, n
    calm = None
    if esc:
        for t in sorted(c["start_time"] for c in codes if c["start_time"] > first):
            if not any(t <= e < t + CALM_WINDOW for e in esc):
                calm = t
                break
    future = [c["start_time"] for c in codes if c.get("frame") == "future_problem_solving"]
    return {"first_escalating": first,
            "peak_escalation_window_start": peak,
            "peak_escalation_count": peak_n,
            "first_sustained_deescalation": calm,
            "first_future_move": min(future) if future else None}


OPENING_WINDOW = 180    # s: "how did each team open?" looks at its first 3 minutes
RIP_CODES = ("interest", "right", "power")
QUESTION_CODES = ("open_question", "closed_question", "ask_why", "ask_priority", "ask_constraint")


def team_dynamics(codes, teams, names=TEAMS, codebook=None):
    """Per team, the debrief's questions: opening_move (dominant rip code in
    the first OPENING_WINDOW seconds of the conversation, "none" if it made
    no rights/interests/power move), rip_sequence (its rip codes in order
    with repeats collapsed and none skipped), last_escalating (seconds of
    its last escalating utterance) and first_interest_question (seconds of
    its first interest-coded question)."""
    if codebook is not None:
        import coding_schemes as coding_scheme
        if not coding_scheme.analytics(codebook)["dynamics"]:
            return {}
    ordered = sorted(codes, key=lambda c: (c["start_time"], c.get("transcript_id") or 0))
    start = ordered[0]["start_time"] if ordered else 0
    out = {}
    for team in tuple(names) + (UNASSIGNED,):
        mine = [c for c in ordered if team_of_code(c, teams, names) == team]
        opening = [c["rip"] for c in mine if c["start_time"] < start + OPENING_WINDOW and c.get("rip") in RIP_CODES]
        # ties go to the code the team reached for first
        counts = {r: opening.count(r) for r in RIP_CODES if r in opening}
        move = max(counts, key=lambda r: (counts[r], -opening.index(r))) if counts else "none"
        sequence = []
        for c in mine:
            if c.get("rip") in RIP_CODES and (not sequence or sequence[-1] != c["rip"]):
                sequence.append(c["rip"])
        esc = [c["start_time"] for c in mine if c.get("emotion") == "escalating"]
        questions = [c["start_time"] for c in mine if c.get("rip") == "interest"
                     and any(q in (c.get("listening") or []) for q in QUESTION_CODES)]
        out[team] = {"opening_move": move, "rip_sequence": sequence,
                     "last_escalating": max(esc) if esc else None,
                     "first_interest_question": min(questions) if questions else None}
    return out


def summarize(codes, teams, codebook=None, extra=None, names=TEAMS):
    """Roll-up, team dynamics and timeline; ``extra`` (a paired run's
    cross_talk and pods) is merged in as further top-level keys."""
    codebook = codebook or load_codebook()
    summary = rollup(codes, teams, codebook, names)
    for team, dynamics in team_dynamics(codes, teams, names, codebook).items():
        summary["by_team"][team].update(dynamics)
    summary["timeline"] = timeline(codes, codebook)
    for key, value in (extra or {}).items():
        if value is not None:
            summary[key] = value
    return summary


def validate_teams(teams, names=TEAMS):
    """The request's {"<speaker_tag>": "<team name>"} -> (clean dict, error).
    Team names are matched case-insensitively against ``names`` (the
    session's teams). Missing/null means nobody is assigned; empty or null
    values unassign."""
    choices = " or ".join(names) if len(names) <= 2 else ", ".join(names[:-1]) + " or " + names[-1]
    if teams is None:
        return {}, None
    if not isinstance(teams, dict):
        return None, "teams must be an object mapping speaker tags to %s." % choices
    clean = {}
    for tag, team in teams.items():
        if team in (None, ""):
            continue
        wanted = " ".join(team.split()).lower() if isinstance(team, str) else None
        name = next((n for n in names if n.lower() == wanted), None)
        if name is None:
            return None, "team for speaker %r must be %s." % (tag, choices)
        clean[str(tag)] = name
    return clean, None


# --------------------------------------------------------- orchestration

def code_row(code, transcript, teams=None, sides=None, names=TEAMS):
    # One entry of the API's "codes" list: the utterance, its codes (one key
    # per dimension of the run's scheme) and its team (its device's side
    # when the device has one, else its tag's assignment, else "unassigned").
    device_id = transcript.session_device_id
    side = (sides or {}).get(device_id)
    row = {"transcript_id": transcript.id, "session_device_id": device_id,
           "start_time": transcript.start_time, "length": transcript.length,
           "speaker_tag": transcript.speaker_tag, "text": transcript.transcript,
           "team": side if side in names else team_of(transcript.speaker_tag or "", teams, names)}
    row.update(code.values())
    return row


def _side_of(device, names=TEAMS):
    side = getattr(device, "negotiation_side", None)
    return side if side in names else None


def _session_names(session):
    # The session's team names (pod setup); the placeholder pair without one.
    getter = getattr(session, "team_names", None)
    names = getter() if callable(getter) else None
    return tuple(names) if names and len(names) >= 2 else DEFAULT_TEAMS


def device_team_names(session_device_id):
    """The team names of the pod's session."""
    import database
    device = database.get_session_devices(id=session_device_id)
    session = database.get_sessions(id=device.session_id) if device is not None else None
    return _session_names(session)


def run_names(run):
    return device_team_names(run.session_device_id)


def run_sides(run, names=None):
    """{device id: team} for the run's devices (``names`` default to the
    run's session's). A single device counts only when it has a side (a
    paired session's lone pod). In a paired run a missing side is the
    complement of the other's, both missing makes the first device the first
    team, and two devices claiming one side give the partner the other."""
    import database
    names = tuple(names) if names else run_names(run)
    first = database.get_session_devices(id=run.session_device_id)
    if not run.is_paired():
        side = _side_of(first, names)
        return {run.session_device_id: side} if side else {}
    partner = database.get_session_devices(id=run.partner_device_id)
    a, b = _side_of(first, names), _side_of(partner, names)
    if a is None and b is None:
        a, b = names[0], names[1]
    elif a is None:
        a = other_team(b, names)
    elif b is None or b == a:
        b = other_team(a, names)
    return {run.session_device_id: a, run.partner_device_id: b}


def run_pods(run, sides):
    """[{id, name, group, side}] for the run's devices, first device first."""
    import database
    pods = []
    for device_id in run.device_ids():
        device = database.get_session_devices(id=device_id)
        pods.append({"id": device_id,
                     "name": getattr(device, "name", None),
                     "group": getattr(device, "negotiation_group", None),
                     "side": sides.get(device_id)})
    return pods


def _pair_rank(device, names=TEAMS):
    # The first team first, then the second, then unsided; ties by id: the
    # two pods of a group always agree on which is the run's first device.
    side = _side_of(device, names)
    return (names.index(side) if side else len(names), device.id)


def resolve_pair(session_device_id):
    """(first device id, partner id or None) of the pod's breakout group in a
    paired session; (pod id, None) in any other session or when the pod has
    no group or no partner yet."""
    import database
    device = database.get_session_devices(id=session_device_id)
    if device is None:
        return session_device_id, None
    session = database.get_sessions(id=device.session_id)
    if session is None or not getattr(session, "negotiation_paired", False):
        return device.id, None
    names = _session_names(session)
    # A group's pair is the first device (lowest id) of each side; an extra
    # laptop joined for a slot ("Table 3 Pat 2") is coded on its own, with
    # its side stamped, rather than pairing the other side twice.
    my_side = _side_of(device, names)
    primaries = {}
    for d in database.get_negotiation_group_devices(device):
        side = _side_of(d, names)
        if side and side not in primaries:
            primaries[side] = d
    if my_side and primaries[my_side].id != device.id:
        return device.id, None
    partner = database.get_negotiation_partner(device)
    if partner is None:
        return device.id, None
    partner_side = _side_of(partner, names)
    if partner_side:
        if partner_side == my_side:
            return device.id, None      # only this side has joined so far
        partner = primaries[partner_side]
    first, second = sorted((device, partner), key=lambda d: _pair_rank(d, names))
    return first.id, second.id


def run_coding(session_device_id, teams=None, llm=call_llm, run_id=None, codebook=None, partner_device_id=None):
    """Code one pod end to end: load its transcripts, code them, persist the
    codes, compute the summary. Reports to run ``run_id`` (created queued by
    the route or end_session) or creates one. Marks the run running -> done,
    or error (message kept) and re-raises so the queue job fails too.
    ``teams`` None = the run row's teams, re-read after coding so a PUT made
    meanwhile wins. A paired run (``partner_device_id`` on the row, or given
    here when the run is created) codes both devices' transcripts merged."""
    import database
    codebook = codebook or codebook_for_device(session_device_id)
    run = database.get_negotiation_run(run_id) if run_id is not None else None
    if run is None:
        if run_id is not None:
            raise RuntimeError("negotiation coding run %s does not exist" % run_id)
        run = database.create_negotiation_run(session_device_id, llm_model(), codebook["version"], teams or {},
                                              partner_device_id=partner_device_id)
    database.update_negotiation_run(run.id, status="running", started_at=_now(), finished_at=None, error=None)
    try:
        names = run_names(run)
        sides = run_sides(run, names)
        extra = {"pods": run_pods(run, sides)}
        if run.is_paired():
            rows_by_device = {d: database.get_transcripts(session_device_id=d) for d in run.device_ids()}
            utterances, dropped = merge_paired(rows_by_device, sides)
            extra["cross_talk"] = {"dropped": len(dropped), "kept": len(utterances),
                                   "detail": dropped[:500]}
        else:
            rows = database.get_transcripts(session_device_id=run.session_device_id)
            utterances = utterances_from_rows(rows, sides.get(run.session_device_id))
        coded, invalid = code_utterances(codebook, utterances, llm, names=names)
        database.add_negotiation_codes(run.id, coded, list(codebook["dimensions"]))
        if teams is None:
            teams = database.get_negotiation_run(run.id).teams_dict()
        database.update_negotiation_run(
            run.id, status="done", finished_at=_now(), teams=teams,
            summary=summarize(coded, teams, codebook, extra, names),
            utterances_coded=len(coded), invalid_codes=invalid)
    except Exception as e:
        logging.exception("negotiation coding: run %s for pod %s failed", run.id, session_device_id)
        database.update_negotiation_run(run.id, status="error", finished_at=_now(), error=str(e)[:2000])
        raise
    return database.get_negotiation_run(run.id)


def recompute_summary(run, teams, codebook=None):
    """New team assignment for a run: re-roll the stored codes, no LLM call.
    (In a paired run the devices' sides win over the assignment.)"""
    import database
    fields = {"teams": teams}
    if run.status == "done":
        names = run_names(run)
        sides = run_sides(run, names)
        codebook = codebook or codebook_for_device(run.session_device_id)
        codes = [code_row(c, t, teams, sides, names) for c, t in database.get_negotiation_codes(run.id)]
        previous = run.summary_dict() or {}
        extra = {"pods": run_pods(run, sides), "cross_talk": previous.get("cross_talk")}
        fields["summary"] = summarize(codes, teams, codebook, extra, names)
    return database.update_negotiation_run(run.id, **fields)


def run_payload(run, with_codes=True):
    """The GET shape: {run, mode, pods, teams, codes?, summary}; summary is
    None until done. mode is "paired" (two devices, teams by side) or
    "single" (teams by speaker tag)."""
    import database
    import coding_schemes as coding_scheme
    names = run_names(run)
    sides = run_sides(run, names)
    payload = {"run": run.json(), "mode": "paired" if run.is_paired() else "single",
               "codebook": coding_scheme.panel_json(codebook_for_device(run.session_device_id)),
               "team_names": list(names), "pods": run_pods(run, sides),
               "teams": run.teams_dict(), "summary": run.summary_dict()}
    if with_codes:
        teams = payload["teams"]
        payload["codes"] = [code_row(c, t, teams, sides, names) for c, t in database.get_negotiation_codes(run.id)]
    return payload


def queue_coding_run(session_id, session_device_id, teams=None, partner_device_id=None):
    """A run row for the pod (and its partner, in a paired session) and a
    coding job on the post-hoc queue. A run still queued for the same
    device(s) is reused (its teams updated when given) rather than stacking
    a second identical run behind it."""
    import database
    import posthoc_queue
    run = database.get_latest_negotiation_run(session_device_id)
    if run is not None and run.status == "queued" and run.session_device_id == session_device_id \
            and run.partner_device_id == partner_device_id:
        if teams is not None:
            run = database.update_negotiation_run(run.id, teams=teams)
    else:
        run = database.create_negotiation_run(session_device_id, llm_model(),
                                              codebook_for_device(session_device_id)["version"], teams or {},
                                              partner_device_id=partner_device_id)
    posthoc_queue.enqueue_coding(session_id, session_device_id, run.id)
    return run


def cancel_run(run_id, reason):
    # A queued job dropped from the queue: the row must not say "queued" forever.
    import database
    run = database.get_negotiation_run(run_id)
    if run is not None and run.status in ("queued", "running"):
        database.update_negotiation_run(run_id, status="error", finished_at=_now(), error="cancelled: " + reason)
