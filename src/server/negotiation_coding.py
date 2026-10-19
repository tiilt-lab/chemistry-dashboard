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
import bisect
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
# utterance is dropped. The two clocks are not equal, though: a laptop's
# stamps count the audio samples it sent from the moment its stream
# started, so a late microphone, a stalled tab or a replayed backlog shifts
# one device by seconds for the rest of the session (Group 1 on 2026-10-16
# ran 18 s apart, then 5 s). The offset is estimated from utterances both
# devices heard and taken out before the copies are matched.
PAIR_START_TOLERANCE = 1.5   # s: starts this close are the same moment ...
PAIR_OVERLAP_MIN = 0.5       # ... or the two overlap this share of the shorter one
PAIR_TEXT_SIMILARITY = 0.5   # token ratio from which two copies are one utterance
# An unnamed row overlapping a named line from the other laptop is that line
# bleeding into the far microphone only when it says some of the same words.
# Overlap alone was enough until 2026-10-19, and across sessions 432-437 most
# such drops (936 of 986 under 0.3) were different speech: the room talking
# over itself, with the line then lost from the group transcript.
PAIR_BLEED_SIMILARITY = 0.3
PAIR_BLEED_CONTAINED = 0.5    # ... or this share of the unnamed row's words is in the named line
# Tuned on the real rows of 2026-10-16 (Group 1: 853 rows, clocks 18 then
# 6 s apart; Group 3: 1200 rows, one laptop reconnecting, offsets wandering
# 1 to 8 s). With 0.7/8 words/3 s, 7 clear duplicates survived in Group 3
# and 4 in Group 1; with these values 0 and 3, at the cost of 20-odd more
# rows dropped per group. Short lines repeat in a negotiation, so the anchor
# minimum stays well above the two or three words of "yeah, exactly".
PAIR_ANCHOR_SIMILARITY = 0.6  # token ratio from which a cross-device match anchors the clock alignment
PAIR_ANCHOR_MIN_TOKENS = 6    # anchors need this many words: short lines repeat
PAIR_SEARCH_WINDOW = 600.0    # s: how far apart the two clocks may be (2026-10-16: up to 260 s)
PAIR_VOTE_BIN = 2.0           # s: candidate offsets are binned this coarsely to find the dominant one
PAIR_ANCHOR_SPREAD = 30.0     # s: anchors this far from the dominant offset are repeats, not the clock
PAIR_MIN_ANCHORS = 3          # fewer than this: the clocks are taken as equal
PAIR_ANCHOR_NEIGHBOURS = 5    # the offset at a moment is the median of this many nearest anchors
PAIR_ALIGNED_TOLERANCE = 5.0  # s: after alignment, how differently the two recognizers may cut a start
# The two recognizers also cut the same stretch of speech at different
# points: one laptop makes two utterances where the other makes one that
# straddles them, and a straddler matches neither half well enough to be a
# duplicate. A kept utterance whose words are this far covered, in runs of
# PAIR_COVER_RUN tokens or more, by the other laptop's kept utterances at the
# same moment is a copy of them and is dropped ("covered").
PAIR_COVERED_SHARE = 0.6
PAIR_COVER_RUN = 3           # ... but a two- or three-word fragment must simply appear whole
PAIR_KEEP_REMAINDER = 3      # a covered utterance keeps its words when this many in a row are its own
# A far-side row is one laptop's hearing of the other laptop's side. Where
# the near laptop has a row of its own in the same moment, the far hearing is
# redundant whatever its words say (the two recognizers rarely agree on them).
FAR_SIDE_OVERLAP = 0.3       # share of the far row's span a near row must overlap ...
FAR_SIDE_PAD = 0.5           # ... with the near row's span padded by this (the cuts never line up exactly)
# Sentence stitching (post): the recognizers cut speech at pauses, not at
# sentences, so one speaker's sentence arrives in pieces and a piece often
# starts with the tail word of the previous speaker's sentence ("it. What's
# bothering me most?"). Pieces are stitched back into sentences before coding.
STITCH_LEAD_WORDS = 3        # a sentence end within this many words of the start is a tail of the previous line (live rows; MOSS cuts by speaker)
STITCH_GAP = 1.5             # s between a speaker's pieces for them to be one sentence
STITCH_MAX_SECONDS = 30.0    # a stitched sentence never spans more than this
STITCH_MAX_WORDS = 70
STITCH_SHORT_WORDS = 3       # an unnamed piece this short next to a named piece on the same laptop is that speaker's
_SENTENCE_END = re.compile(r"[.?!]['\"\)\]]*$")
# The recognizer's event tags ("[breath]", "[laughter]", "[UM] [UH]") on
# their own are not an utterance: nothing to code and nobody to name. Such
# rows are left out of the coding (dropped, reason "non_speech"); on
# 2026-10-16 they were 2-6% of every group's coded lines, most of them unnamed.
_NON_SPEECH = re.compile(r"^(\s*\[[a-z_\- ]+\][.,!?]*\s*)+$", re.I)
_TAG = re.compile(r"\[[a-z_\- ]+\]", re.I)
_LEXICAL_WORD = re.compile(r"[a-z0-9']+", re.I)
# Chat completions in flight at once for one run (NEGOTIATION_LLM_PARALLEL):
# the llama-server has four slots, so a run's chunks can go four at a time,
# at the price of more GPU load beside a live class. 1 = one after another.
DEFAULT_LLM_PARALLEL = 1
# How many of the rows left out of a run are listed, with their reason, in
# the run's record (summary.cross_talk.detail): the transcript export reads
# it. A group's two laptops leave out 300-600 rows (2026-10-16).
DROP_DETAIL_MAX = 1500

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


def llm_parallel():
    try:
        return max(1, int(os.environ.get("NEGOTIATION_LLM_PARALLEL") or DEFAULT_LLM_PARALLEL))
    except ValueError:
        return DEFAULT_LLM_PARALLEL


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
    conf = _attribution_confidence(r)
    u = {"transcript_id": r.id, "start_time": r.start_time, "length": r.length,
         "speaker_tag": r.speaker_tag, "text": r.transcript,
         "session_device_id": getattr(r, "session_device_id", None),
         "speaker_id": getattr(r, "speaker_id", None),
         "question": bool(getattr(r, "question", False))}
    if team:
        u["team"] = team
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


def same_moment(a, b, tolerance=PAIR_START_TOLERANCE):
    """Two utterances from different devices that started within
    ``tolerance`` of each other, or overlap for at least PAIR_OVERLAP_MIN of
    the shorter one."""
    a0, a1 = _span(a)
    b0, b1 = _span(b)
    if abs(a0 - b0) <= tolerance:
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
    # A far-side match (the other team's voice, named from the partner pod's
    # roster) is this microphone hearing across the table: real, but the
    # weaker copy whenever the near laptop has one. A name the laptop gave
    # to two clusters (duplicate_name) is a print matching two voices: a
    # claim, not a hearing.
    return strength - (0.3 if conf.get("closed_world") else 0.0) - (0.3 if conf.get("far_side") else 0.0) \
        - (0.3 if conf.get("duplicate_name") else 0.0)


RECONCILE_MIN_PAIRS = 3     # duplicate copies two clusters must share to be one voice...
RECONCILE_MIN_LINES = 0.10  # ...covering this share of the cluster's lines (2 of 76 proves nothing)
RECONCILE_SHARE = 0.6       # ...and that pairing's share of the cluster's duplicates
RECONCILE_MARGIN = 0.02     # the other laptop's claim must beat this one's by this much


def _cluster_key(u):
    conf = u.get("confidence") or {}
    c = conf.get("cluster")
    return (u.get("session_device_id"), c) if c else None


def flag_duplicate_names(units):
    """Mark the rows of every name a laptop gave to two or more diarizer
    clusters (confidence.duplicate_name): one print matching two voices,
    which is how a session print cut from misnamed live rows shows itself
    (Group 1, 2026-10-16: one laptop's print for its second student was a
    voice from across the table, and two clusters took the name). Returns
    {name: clusters}."""
    clusters = {}
    for u in units:
        key = _cluster_key(u)
        if key and u.get("speaker_tag"):
            clusters.setdefault(u["speaker_tag"], set()).add(key[1])
    dup = {n: cs for n, cs in clusters.items() if len(cs) > 1}
    for u in units:
        if u.get("speaker_tag") in dup and _cluster_key(u):
            u["confidence"] = dict(u.get("confidence") or {}, duplicate_name=True)
    return dup


def _claim_score(rec):
    # How much a laptop's name for a cluster is worth against the other
    # laptop's: the print similarity, less the demotions match_strength
    # applies; nothing for an unnamed cluster.
    if not rec["name"]:
        return 0.0
    conf = rec["conf"]
    score = float(conf.get("sim") or 0.5)
    for flag in ("closed_world", "far_side", "duplicate_name"):
        if conf.get(flag):
            score -= 0.3
    return score


def reconcile_clusters(pool, dropped, diagnostics=None, placed=None):
    """One voice, one name, across both laptops. The duplicate copies the
    merge matched pair this laptop's diarizer clusters with the other's;
    a cluster whose copies mostly fall on one cluster of the other laptop
    is that voice, and when the two laptops named it differently the
    stronger claim (print similarity, less the demotions) names every line
    of both clusters, lone fragments the other laptop never transcribed
    included. Without this the kept copy's name flipped with the kept
    laptop, mid-sentence: Group 1 of session 434 showed 41 such flips.
    Relabelled lines carry confidence.reconciled_from. ``placed``: device
    -> whether the laptop named a student of its own team (merge_paired
    knows the sides); without it, a name that is not a far hearing."""
    by_id = {u["transcript_id"]: u for u in pool}
    members, pairs = {}, {}
    if placed is None:
        placed = {}
        for u in pool:
            dev = u.get("session_device_id")
            placed[dev] = placed.get(dev, False) or (bool(u.get("speaker_tag"))
                                                     and not (u.get("confidence") or {}).get("far_side"))
    for u in pool:
        key = _cluster_key(u)
        if key:
            members.setdefault(key, []).append(u)
    for d in dropped:
        if d.get("reason") != "duplicate":
            continue
        a, b = by_id.get(d["transcript_id"]), by_id.get(d["kept_transcript_id"])
        ka, kb = (_cluster_key(a) if a else None), (_cluster_key(b) if b else None)
        if not ka or not kb or ka[0] == kb[0]:
            continue
        pairs.setdefault(ka, {}).setdefault(kb, 0)
        pairs[ka][kb] += 1
        pairs.setdefault(kb, {}).setdefault(ka, 0)
        pairs[kb][ka] += 1

    def record(key):
        us = members[key]
        names = {}
        for u in us:
            names[u.get("speaker_tag")] = names.get(u.get("speaker_tag"), 0) + 1
        name = max(names, key=lambda n: (names[n], n is not None)) if names else None
        named = [u for u in us if u.get("speaker_tag") == name] or us
        teams = {}
        for u in named:
            teams[u.get("team")] = teams.get(u.get("team"), 0) + 1
        return {"name": name, "conf": named[0].get("confidence") or {},
                "team": max(teams, key=teams.get) if teams else None}

    changes = []
    decided = {}
    for key, partners in pairs.items():
        total = sum(partners.values())
        partner, n = max(partners.items(), key=lambda kv: kv[1])
        if n < RECONCILE_MIN_PAIRS or n / float(total) < RECONCILE_SHARE \
                or n < RECONCILE_MIN_LINES * len(members[key]):
            continue
        mine, theirs = record(key), record(partner)
        if not theirs["name"] or theirs["name"] == mine["name"]:
            continue
        my_standing, their_standing = placed.get(key[0], False), placed.get(partner[0], False)
        if mine["name"] and my_standing and not their_standing:
            # A laptop that named none of its own side heard only the other
            # team's voices: every claim it makes is a far hearing, and it
            # has no standing to rename a voice a laptop that can place its
            # own side named. (Group 6, 2026-10-16: one laptop named only
            # the other team's students, and its claims renamed the
            # partner's 237 lines of one of its own students to the other
            # team, leaving that team no lines at all.)
            continue
        if not (their_standing and not my_standing) \
                and _claim_score(theirs) - _claim_score(mine) < RECONCILE_MARGIN:
            # ... and the other way round the placing laptop's name wins
            # whatever the similarities say, so the voice reads as one.
            continue
        decided[key] = (mine, theirs, n)
    for key, (mine, theirs, n) in decided.items():
        for u in members[key]:
            if u.get("speaker_tag") == theirs["name"]:
                continue
            u["confidence"] = dict(u.get("confidence") or {}, reconciled_from=u.get("speaker_tag"))
            u["speaker_tag"] = theirs["name"]
            if theirs["team"]:
                u["team"] = theirs["team"]
        changes.append({"session_device_id": key[0], "cluster": key[1], "from": mine["name"],
                        "to": theirs["name"], "lines": len(members[key]), "pairs": n})
        logging.debug("paired merge: cluster %s of pod %s (%s, %d lines) is %s: %d duplicate copies agree",
                     key[1], key[0], mine["name"], len(members[key]), theirs["name"], n)
    if diagnostics is not None:
        diagnostics["reconciled"] = changes
    return changes


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


def _names_team(alias, names):
    """The team an alias's prefix names ("Bet2G4S31" is the second team of
    ("Alpha", "Beta")), else None: a username that is a real name says
    nothing."""
    low = (alias or "").lower()
    for team in names:
        if team and low.startswith(team.lower()[:3]):
            return team
    return None


def _places_own_side(u, side, names):
    """Whether this row shows its laptop can place its own side: a name of
    a student of the laptop's own team by its prefix, or, for a username
    that is a real name, a name that is not a far hearing. (The flag alone
    does not do: a student enrolled on the wrong laptop is "own" there.)"""
    tag = u.get("speaker_tag")
    if not tag or side is None:
        return False
    team = _names_team(tag, names)
    if team is not None:
        return team == side
    return not (u.get("confidence") or {}).get("far_side")


def _unflag_unplaceable(by_device, sides, placed):
    """A laptop that named none of its own side cannot place an unnamed
    voice either: the far flag on its unnamed rows came from the only
    prints it had, the other team's. Those rows are its own side's unnamed
    speech, kept and teamed with the laptop, not yielded to the partner.
    (Group 2, 2026-10-16: the Pat students never enrolled, so the Pat
    laptop's every row was far-side and the merge kept 3 of its 743.)"""
    for dev, units in by_device.items():
        if placed.get(dev):
            continue
        for u in units:
            conf = u.get("confidence") or {}
            if not u.get("speaker_tag") and conf.get("far_side"):
                u["confidence"] = dict(conf, far_side=False, side_unknown=True)
                if sides.get(dev):
                    u["team"] = sides[dev]


def _far_side_yields(pool, dropped, dropped_ids):
    """A far-side row (named from the partner's roster) goes wherever the
    near laptop has a row of its own overlapping FAR_SIDE_OVERLAP of its
    span, whatever either says: the near laptop heard its own side better,
    and the two recognizers' words rarely match well enough for the text
    rules. A far row the near laptop missed stays (its team already flipped
    by line_team)."""
    for u in pool:
        if not (u.get("confidence") or {}).get("far_side"):
            continue
        u0, u1 = _span(u)
        span = max(u1 - u0, 0.1)
        for v in pool:
            if v["session_device_id"] == u["session_device_id"] or v["transcript_id"] in dropped_ids:
                continue
            if (v.get("confidence") or {}).get("far_side"):
                continue
            v0, v1 = _span(v)
            overlap = min(u1, v1 + FAR_SIDE_PAD) - max(u0, v0 - FAR_SIDE_PAD)
            if overlap / span >= FAR_SIDE_OVERLAP:
                dropped_ids.add(u["transcript_id"])
                dropped.append({"transcript_id": u["transcript_id"], "kept_transcript_id": v["transcript_id"],
                                "reason": "far_side", "similarity": round(overlap / span, 2)})
                break


def _composite(a, b):
    """True when the longer of two same-moment utterances is a composite:
    both laptops named their OWN speaker with a clear match (neither far
    side, neither a closed-world pick), the speakers differ, and the shorter
    sits almost whole inside the longer. One recognizer ran the far side's
    tail into its own speaker's reply; the pair is not two copies of one
    thing, and the coverage pass trims the composite to its own words."""
    if (a.get("speaker_tag") or "") == (b.get("speaker_tag") or "") or not a.get("speaker_tag") or not b.get("speaker_tag"):
        return False
    for u in (a, b):
        conf = u.get("confidence") or {}
        if conf.get("far_side") or conf.get("closed_world") or match_strength(u) < 0.5:
            return False
    ta, tb = _utterance_tokens(a), _utterance_tokens(b)
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if not short or len(long_) < 1.5 * len(short):
        return False
    matched = sum(size for _, _, size in difflib.SequenceMatcher(None, short, long_, autojunk=False).get_matching_blocks())
    return matched >= 0.8 * len(short)


def _neighbours(pool, i, reach, tolerance=PAIR_START_TOLERANCE):
    # The pool entries that could share pool[i]'s moment: forward until a
    # start passes its end plus the tolerance, backward while a start within
    # ``reach`` (the longest utterance plus the tolerance) could still
    # overlap it.
    u = pool[i]
    horizon = _span(u)[1] + tolerance
    for j in range(i + 1, len(pool)):
        if pool[j]["start_time"] > horizon:
            break
        yield pool[j]
    floor = u["start_time"] - reach
    for j in range(i - 1, -1, -1):
        if pool[j]["start_time"] < floor:
            break
        yield pool[j]


def _utterance_tokens(u):
    toks = u.get("_tokens")
    if toks is None:
        toks = u["_tokens"] = _tokens(u.get("text"))
    return toks


class ClockAlignment(object):
    """The offset of one device's clock relative to the other's, estimated
    from utterances both heard (``anchors``: [(other device's start, other
    start - reference start)], keyed on the other device's clock because
    that is the clock ``at`` is asked about). The offset at a moment is the
    median over the nearest anchors, so a step (a reconnect, a stall) moves
    it where it happened instead of smearing it over the session."""

    def __init__(self, anchors, reference_device, other_device, method="text"):
        self.anchors = sorted(anchors)
        self.reference_device = reference_device
        self.other_device = other_device
        self.method = method

    def at(self, t):
        # The median of the nearest anchors (fewer when there are few, so a
        # step is not averaged away); when those straddle a step, i.e. they
        # disagree by more than the aligned tolerance, the nearest anchor in
        # time decides.
        if not self.anchors:
            return 0.0
        k = min(PAIR_ANCHOR_NEIGHBOURS, max(3, len(self.anchors) // 4))
        near = sorted(self.anchors, key=lambda a: abs(a[0] - t))[:k]
        offsets = sorted(a[1] for a in near)
        if offsets[-1] - offsets[0] > PAIR_ALIGNED_TOLERANCE:
            return near[0][1]
        return offsets[len(offsets) // 2]

    def largest(self):
        """How far apart the clocks were found at most, in seconds."""
        return max((abs(float(a[1])) for a in self.anchors), default=0.0)

    def median_offset(self):
        """The offset most anchors agree on, in seconds (signed)."""
        offsets = sorted(float(a[1]) for a in self.anchors)
        return offsets[len(offsets) // 2] if offsets else 0.0

    def decisive(self):
        """Whether the anchors say the clocks are really apart: the median
        offset beyond the start tolerance. A few far anchors (repeated
        phrases) move the largest offset but not this."""
        return abs(self.median_offset()) > PAIR_START_TOLERANCE

    def summary(self):
        offsets = [a[1] for a in self.anchors]
        # The offset every ten minutes of the other device's clock, for the
        # run's record: a reader sees a step at a glance.
        first, last = self.anchors[0][0], self.anchors[-1][0]
        samples = [{"at": round(float(t), 1), "offset": round(self.at(t), 1)}
                   for t in range(int(first), int(last) + 1, 600)]
        return {"reference_device": self.reference_device, "other_device": self.other_device,
                "method": self.method, "anchors": len(self.anchors),
                "offset_min": round(min(offsets), 2), "offset_max": round(max(offsets), 2), "offsets": samples}


def estimate_clock_offset(reference, other, reference_device=None, other_device=None):
    """ClockAlignment of ``other`` (one device's utterances) against
    ``reference`` (the other device's), or None when fewer than
    PAIR_MIN_ANCHORS utterances match well enough to tell. A candidate is a
    reference utterance of at least PAIR_ANCHOR_MIN_TOKENS words whose best
    text match on the other device, within PAIR_SEARCH_WINDOW, reaches
    PAIR_ANCHOR_SIMILARITY. The clocks may be minutes apart (a backlog
    replayed at the wrong time), so the window is wide and a negotiation
    repeats its phrases; the candidates therefore vote, in PAIR_VOTE_BIN
    bins, for the dominant offset, and only those within PAIR_ANCHOR_SPREAD
    of it become anchors."""
    others = sorted(other, key=lambda u: float(u.get("start_time") or 0))
    starts = [float(u.get("start_time") or 0) for u in others]
    anchors = []
    for a in reference:
        ta = _utterance_tokens(a)
        if len(ta) < PAIR_ANCHOR_MIN_TOKENS:
            continue
        t = float(a.get("start_time") or 0)
        lo = bisect.bisect_left(starts, t - PAIR_SEARCH_WINDOW)
        hi = bisect.bisect_right(starts, t + PAIR_SEARCH_WINDOW)
        best, best_sim = None, 0.0
        for b in others[lo:hi]:
            tb = _utterance_tokens(b)
            if len(tb) < PAIR_ANCHOR_MIN_TOKENS:
                continue
            sim = difflib.SequenceMatcher(None, ta, tb).ratio()
            if sim > best_sim:
                best, best_sim = b, sim
        if best is not None and best_sim >= PAIR_ANCHOR_SIMILARITY:
            other_start = float(best.get("start_time") or 0)
            anchors.append((other_start, other_start - t))
    if len(anchors) < PAIR_MIN_ANCHORS:
        return None

    def dominant_of(cands):
        votes = {}
        for _, offset in cands:
            b = round(offset / PAIR_VOTE_BIN)
            votes[b] = votes.get(b, 0) + 1
        return max(votes, key=lambda b: (votes[b], -abs(b))) * PAIR_VOTE_BIN
    # The offset is not one number for the session: a laptop that
    # reconnected (Group 2, 2026-10-16: 257 s apart in the first minutes,
    # 8 s after the reconnect) moves it, and to a single session-wide vote
    # the anchors from before the move looked like repeats, so the copies
    # there were never matched and the lines showed twice. The candidates
    # settle into levels, the dominant offset first; a further level is the
    # clock too when, over the stretch its anchors span, it outnumbers the
    # dominant one (a phrase said again two minutes later never does).
    levels, pool = [], list(anchors)
    while len(pool) >= PAIR_MIN_ANCHORS:
        d = dominant_of(pool)
        level = [a for a in pool if abs(a[1] - d) <= PAIR_ANCHOR_SPREAD]
        if len(level) < PAIR_MIN_ANCHORS:
            break
        pool = [a for a in pool if abs(a[1] - d) > PAIR_ANCHOR_SPREAD]
        levels.append(level)
    if not levels:
        return None
    primary = levels[0]
    anchors = list(primary)
    for level in levels[1:]:
        lo, hi = min(a[0] for a in level), max(a[0] for a in level)
        rivals = sum(1 for a in primary if lo <= a[0] <= hi)
        if len(level) > rivals:
            anchors.extend(level)
    if len(anchors) < PAIR_MIN_ANCHORS:
        return None
    # Two recognizers cut the same speech a second or so apart either way;
    # that is jitter the matching tolerances absorb, not a clock offset, and
    # shifting stamps by it would only move real times around.
    if max(abs(a[1]) for a in anchors) <= PAIR_ALIGNED_TOLERANCE:
        return None
    return ClockAlignment(anchors, reference_device, other_device)


def audio_recordings_dir():
    """Where the live audio service keeps the pods' recordings
    (``<key> (<start>)_redu.wav`` and their clock sidecars). The two
    services share this host and checkout; DC_AUDIO_RECORDINGS_DIR points
    elsewhere when they do not."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.environ.get("DC_AUDIO_RECORDINGS_DIR") or os.path.join(here, "..", "audio_processing", "recordings")


def recordings_of(processing_key, directory=None):
    """The reduced (16 kHz mono) recordings of a pod that carry a clock
    sidecar, oldest first. Recordings from before the sidecar existed cannot
    be placed on the session clock and are left out."""
    import glob
    import recording_sidecar
    directory = directory or audio_recordings_dir()
    out = []
    for path in sorted(glob.glob(os.path.join(directory, glob.escape(str(processing_key)) + "*_redu.wav"))):
        info = recording_sidecar.read(path)
        if info is not None:
            out.append((path, info))
    return out


def has_audio_recording(session_device_id):
    """Whether the live audio service kept a recording of the pod — what a
    post-hoc audio leg analyses: a ``<pod id>-…`` capture in the recordings
    directory, the ``.dat`` still being written while the pod streams (the
    session-end hook runs before the pods hang up) or the ``.wav`` closed
    at disconnect. The clock sidecars beside them are not recordings."""
    import glob
    try:
        prefix = "%d-" % int(session_device_id)
    except (TypeError, ValueError):
        return False
    paths = glob.glob(os.path.join(audio_recordings_dir(), glob.escape(prefix) + "*"))
    return any(p.endswith((".wav", ".dat")) for p in paths)


def audio_gate(session_device_ids):
    """The pods of a coding run whose post-hoc audio analysis the coding
    waits for: every covered pod whose analysis is recorded complete, in
    flight, or still to be run (a recording to analyse). A pod with none of
    those has nothing to wait for and is coded as it stands."""
    import database
    return [d for d in session_device_ids
            if database.audio_posthoc_status(d) != "missing" or has_audio_recording(d)]


def _pod_envelope(recordings):
    """(timeline_start, envelope) of a pod on its own transcript clock from
    its recordings, read in blocks so a long one never sits in memory."""
    import wave
    import audio_align
    import recording_sidecar
    import numpy as np

    def _blocks(w, frames):
        # The reduced recordings are 16-bit mono; read ten seconds at a time.
        while True:
            raw = w.readframes(frames)
            if not raw:
                return
            yield np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0

    segments = []
    for path, info in recordings:
        with wave.open(path, "rb") as w:
            sr = w.getframerate()
            if w.getsampwidth() != 2 or w.getnchannels() != 1:
                logging.warning("paired merge: %s is not 16-bit mono; skipped for alignment", path)
                continue
            env = audio_align.envelope_of_blocks(_blocks(w, sr * 10), sr)
        # The sidecar maps sample 0 to the session clock; clock moves inside
        # a recording are rare and small next to the window, so the start is
        # what places it.
        segments.append((recording_sidecar.session_time(info, 0.0), env))
    return audio_align.place_on_timeline(segments)


def acoustic_anchors(reference_recordings, other_recordings):
    """[(other_time, other_time - reference_time)] from the two pods' sound:
    both microphones heard the same table, so cross-correlating their
    loudness envelopes (audio_align) gives, per window, how far the other
    pod's transcript clock runs ahead of the reference pod's. Empty when
    either side has no recording with a clock sidecar."""
    import audio_align
    if not reference_recordings or not other_recordings:
        return []
    ref_start, ref_env = _pod_envelope(reference_recordings)
    other_start, other_env = _pod_envelope(other_recordings)
    anchors = []
    for t_ref, lag, _score in audio_align.windowed_offsets(ref_start, ref_env, other_start, other_env):
        anchors.append((t_ref + lag, lag))
    return anchors


_WORD_RE = re.compile(r"\S+")


def merge_texts(primary, secondary):
    """One rendering of an utterance from two recognizers' copies: the
    primary's words as written (its punctuation and casing included), plus
    any run of words only the secondary heard, in place. Where the two
    disagree on the same stretch the primary wins: it is the copy with the
    stronger attribution, i.e. the nearer microphone."""
    pw = [(w, re.sub(r"[^a-z0-9']", "", w.lower())) for w in _WORD_RE.findall(primary or "")]
    sw = [(w, re.sub(r"[^a-z0-9']", "", w.lower())) for w in _WORD_RE.findall(secondary or "")]
    pn, sn = [n for _, n in pw], [n for _, n in sw]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, pn, sn, autojunk=False).get_opcodes():
        if op == "insert":
            out.extend(w for w, _ in sw[j1:j2])
        else:
            out.extend(w for w, _ in pw[i1:i2])
    return " ".join(out)


def merge_paired(rows_by_device, sides, diagnostics=None, recordings=None):
    """One conversation from two devices' transcripts. ``rows_by_device`` maps
    device id -> transcript rows, ``sides`` device id -> team. Rows are put
    on one timeline and each utterance looks for its best text match among
    the other device's same-moment utterances, earlier or later. A text
    match (>= PAIR_TEXT_SIMILARITY) keeps the better-attributed copy
    ("duplicate"), an unmatched voice against a matched one drops the
    unmatched copy ("bleed": the far side heard faintly), and anything else
    stays (both sides really talking at once). The two recognizers cut the
    speech differently, so a kept copy stays in play for further pieces of
    the same utterance from the other device; when a later piece is the
    better copy it takes over, and the drops already pointed at the first
    copy follow it. Before any of that the two clocks are aligned: the
    second device's starts are shifted by the offset estimate_clock_offset
    finds (the original stamp stays in ``device_start_time``), and a
    duplicate's kept copy carries the words of both renderings
    (merge_texts). ``recordings``, when given, maps device id -> the pod's
    recordings with clock sidecars (recordings_of); the alignment then comes
    from the sound itself (acoustic_anchors) and the text is the fallback.
    ``diagnostics``, when a dict, receives the alignment found (or None).
    Returns (utterances in time order, re-indexed, each with team and
    session_device_id; dropped: [{transcript_id, kept_transcript_id,
    reason, similarity}])."""
    by_device = {}
    names = tuple(sorted(set(v for v in sides.values() if v))) or TEAMS
    for device_id, rows in rows_by_device.items():
        units = []
        for r in rows:
            team = sides.get(device_id)
            if team and len(set(sides.values())) == 2:
                # The same rule as the read-back (line_team): a line named
                # from the partner's roster belongs to the other side.
                team = line_team(r, sides, None, names)
            units.append(_utterance(r, team))
        flag_duplicate_names(units)
        by_device[device_id] = units
    tolerance = PAIR_START_TOLERANCE
    alignment = None
    moss_pair = _speaker_bounded_pair(by_device)
    if len(by_device) == 2:
        reference_device, other_device = sorted(by_device)
        if recordings:
            try:
                anchors = acoustic_anchors(recordings.get(reference_device), recordings.get(other_device))
            except Exception:  # noqa: BLE001 - the sound is a bonus; the text still works
                logging.exception("paired merge: acoustic alignment failed; using the text")
                anchors = []
            if len(anchors) >= PAIR_MIN_ANCHORS:
                alignment = ClockAlignment(anchors, reference_device, other_device, method="acoustic")
        if alignment is None:
            found = estimate_clock_offset(by_device[reference_device], by_device[other_device],
                                          reference_device, other_device)
            # MOSS rows are stamped on their recording's own clock, and two
            # of those usually agree (Group 7, 2026-10-19: 0.3 s apart, where
            # the text put 18 % of one laptop's rows more than 5 s off). But
            # a live clock move or a reconnect can leave the two recordings
            # minutes apart (Group 10: 117 s, 417 anchors agreeing), so for
            # two MOSS laptops the text decides only when it is decisive.
            if found is not None and (not moss_pair or found.decisive()):
                alignment = found
        if alignment is not None:
            tolerance = PAIR_ALIGNED_TOLERANCE
            if moss_pair:
                # Clocks found under a second apart need no 5 s window,
                # which reached the echo of a line three seconds earlier.
                tolerance = min(PAIR_ALIGNED_TOLERANCE, PAIR_START_TOLERANCE + alignment.largest())
            for u in by_device[other_device]:
                u["device_start_time"] = u["start_time"]
                u["start_time"] = float(u["start_time"]) - alignment.at(float(u["start_time"]))
    if diagnostics is not None:
        diagnostics["alignment"] = alignment.summary() if alignment is not None else None
        diagnostics["tolerance"] = tolerance
    placed = {dev: any(_places_own_side(u, sides.get(dev), names) for u in units) for dev, units in by_device.items()}
    _unflag_unplaceable(by_device, sides, placed)
    pool = [u for units in by_device.values() for u in units]
    pool.sort(key=lambda u: (u["start_time"], u["transcript_id"]))
    reach = max((_span(u)[1] - _span(u)[0] for u in pool), default=0.0) + tolerance
    kept, dropped, dropped_ids = {}, [], set()      # kept: transcript_id -> utterance
    if len(by_device) == 2:
        _far_side_yields(pool, dropped, dropped_ids)
    for i, u in enumerate(pool):
        if u["transcript_id"] in dropped_ids:
            continue
        best, best_sim = None, -1.0
        for v in _neighbours(pool, i, reach, tolerance):
            if v["session_device_id"] == u["session_device_id"] or v["transcript_id"] in dropped_ids:
                continue
            if not same_moment(u, v, tolerance):
                continue
            sim = text_similarity(u["text"], v["text"])
            if sim > best_sim:
                best, best_sim = v, sim
        if best is not None and best_sim >= PAIR_TEXT_SIMILARITY \
                and not (_speaker_bounded(u) and _speaker_bounded(best)) and _composite(u, best):
            # (Two MOSS turns are each one speaker's: what looked composite
            # was one voice the laptops named differently, 4 of 5 on
            # Group 7, 2026-10-19; they are resolved as duplicates.)
            # Not two copies of one line: the longer one also holds the
            # other laptop's own speaker. Both stay; _drop_covered trims.
            kept.setdefault(u["transcript_id"], u)
            continue
        if best is not None and best_sim >= PAIR_TEXT_SIMILARITY:
            winner, loser, reason = _prefer(u, best) + ("duplicate",)
            if not (_speaker_bounded(winner) and _speaker_bounded(loser)):
                # The kept copy says what both recognizers heard. (Two MOSS
                # turns are punctuated sentences; splicing the other copy's
                # words in garbled the three lines it touched on Group 7.)
                winner["text"] = merge_texts(winner["text"], loser["text"])
                winner.pop("_tokens", None)
            winner.setdefault("merged_from", []).append(loser["transcript_id"])
        elif best is not None and bool(u.get("speaker_tag")) != bool(best.get("speaker_tag")) \
                and _is_bleed(u, best, best_sim):
            winner, loser = (u, best) if u.get("speaker_tag") else (best, u)
            reason = "bleed"
        else:
            kept.setdefault(u["transcript_id"], u)
            continue
        kept.pop(loser["transcript_id"], None)
        # The loser stood for copies dropped in its favour (earlier pieces of
        # this utterance, or the other laptop's far-side copy); they follow
        # the winner. Only following those the loser had already been KEPT
        # for left a far-side copy pointing at a row that was itself dropped
        # moments later: both copies gone, the line missing from the group
        # transcript (session 434, Group 7, 2026-10-19).
        for d in dropped:
            if d["kept_transcript_id"] == loser["transcript_id"]:
                d["kept_transcript_id"] = winner["transcript_id"]
        dropped_ids.add(loser["transcript_id"])
        kept.setdefault(winner["transcript_id"], winner)
        dropped.append({"transcript_id": loser["transcript_id"], "kept_transcript_id": winner["transcript_id"],
                        "reason": reason, "similarity": round(best_sim, 2)})
    if len(by_device) == 2:
        _name_from_far_copy(pool, kept, dropped)
        reconcile_clusters(pool, dropped, diagnostics, placed=placed)
    kept = _drop_covered(kept, dropped, tolerance)
    kept = sorted(kept.values(), key=lambda u: (u["start_time"], u["transcript_id"]))
    for i, u in enumerate(kept):
        u["index"] = i
        u.pop("_tokens", None)
    return kept, dropped


def _is_bleed(u, v, sim):
    """Whether the unnamed one of ``u``/``v`` is the named one's words heard
    faintly by the far microphone: the two texts are similar, or most of the
    unnamed row's words are in the named line (a garbled fragment of a
    longer line scores low on plain similarity). Overlapping in time with
    different words is the room talking over itself, not bleed."""
    if sim >= PAIR_BLEED_SIMILARITY:
        return True
    unnamed, named = (v, u) if u.get("speaker_tag") else (u, v)
    mine = [t for _, t in _words_and_tokens(unnamed.get("text"))]
    if not mine:
        return True                      # no words at all: nothing to lose
    theirs = {t for _, t in _words_and_tokens(named.get("text"))}
    return sum(1 for t in mine if t in theirs) / float(len(mine)) >= PAIR_BLEED_CONTAINED


def _name_from_far_copy(pool, kept, dropped):
    """A kept row its own laptop left unnamed takes the name the other
    laptop gave the same line, when that copy was dropped in its favour
    (far_side: the speaker's own laptop is preferred) and named a student of
    the same team. Otherwise the line kept no name, and the stitcher handed
    it to whoever spoke just before, possibly across the table (session 434,
    Group 7: a line the partner laptop named at 0.96 was shown under a
    student of the other team)."""
    by_id = {u["transcript_id"]: u for u in pool}
    for d in dropped:
        if d["reason"] != "far_side":
            continue
        keep, copy = kept.get(d["kept_transcript_id"]), by_id.get(d["transcript_id"])
        if keep is None or copy is None or keep.get("speaker_tag") or not copy.get("speaker_tag"):
            continue
        if keep.get("team") and copy.get("team") and keep["team"] != copy["team"]:
            continue
        keep["speaker_tag"] = copy["speaker_tag"]
        keep["speaker_id"] = copy.get("speaker_id")
        keep["named_from_partner"] = copy["transcript_id"]


def _words_and_tokens(text):
    """[(word as written, token)] for a text; words with no letters or digits
    (a lone dash) are dropped so words and tokens stay one to one."""
    out = []
    for w in _WORD_RE.findall(text or ""):
        tok = re.sub(r"[^a-z0-9']", "", w.lower())
        if tok:
            out.append((w, tok))
    return out


def _coverage(u, others):
    """(share, covered mask, words) of ``u``'s words found in the other
    laptop's utterances ``others`` (time order) taken together, in runs of
    PAIR_COVER_RUN tokens or more; a shorter utterance must appear whole."""
    pairs = _words_and_tokens(u.get("text"))
    mine = [t for _, t in pairs]
    if not mine:
        return 0.0, [], pairs
    theirs = [t for v in others for _, t in _words_and_tokens(v.get("text"))]
    if not theirs:
        return 0.0, [False] * len(mine), pairs
    run_min = min(PAIR_COVER_RUN, len(mine))
    covered = [False] * len(mine)
    for i, _j, size in difflib.SequenceMatcher(None, mine, theirs, autojunk=False).get_matching_blocks():
        if size >= run_min:
            for k in range(i, i + size):
                covered[k] = True
    return sum(covered) / float(len(mine)), covered, pairs


def _longest_uncovered(covered):
    best, run_start = (0, 0), None
    for i, c in enumerate(list(covered) + [True]):
        if not c and run_start is None:
            run_start = i
        elif c and run_start is not None:
            if i - run_start > best[0] - best[1]:
                best = (i, run_start)
            run_start = None
    return best[1], best[0]      # [start, end)


def _drop_covered(kept, dropped, tolerance):
    """Second pass over the kept utterances. The two recognizers cut speech
    at different points, so a laptop's hearing of the far side can be a
    two-word sliver ("read. What") or a composite that runs the far side's
    tail into its own speaker's reply. Each round: among the utterances
    covered (PAIR_COVERED_SHARE of their words, in runs of PAIR_COVER_RUN,
    found in the other laptop's overlapping utterances) first trim the one
    with the longest run of its own words, when that run reaches
    PAIR_KEEP_REMAINDER: a composite loses the words the other laptop has
    and keeps its own speaker's. Only when no covered utterance has words of
    its own is the most covered one dropped. Trimming first keeps a near
    laptop's clean line from looking redundant against a composite. One-word
    utterances are never covered: "yeah" is anyone's. Two people really
    talking at once share no runs of words, so they stay."""
    while True:
        rows = sorted(kept.values(), key=lambda u: (u["start_time"], u["transcript_id"]))
        covered = []       # (share, remainder length, u, mask, pairs, others)
        for u in rows:
            # A MOSS turn is its speaker's words as heard: never trimmed or
            # dropped as covered (on Group 7, 2026-10-19, the one trim cut
            # the right speaker's words and half the drops were echoes).
            if u.get("trimmed") or len(_utterance_tokens(u)) < 2 or _speaker_bounded(u):
                continue
            u0, u1 = _span(u)
            others = [v for v in rows
                      if v["session_device_id"] != u["session_device_id"]
                      and _span(v)[0] <= u1 + tolerance and _span(v)[1] >= u0 - tolerance]
            if not others:
                continue
            share, mask, pairs = _coverage(u, others)
            if share >= PAIR_COVERED_SHARE:
                start, end = _longest_uncovered(mask)
                covered.append((share, end - start, u, mask, pairs, others, start, end))
        if not covered:
            return kept
        trimmable = [c for c in covered if c[1] >= PAIR_KEEP_REMAINDER]
        if trimmable:
            _share, _n, u, _mask, pairs, _others, start, end = max(trimmable, key=lambda c: (c[1], c[0]))
            u["text"] = " ".join(w for w, _ in pairs[start:end])
            u["trimmed"] = True
            u.pop("_tokens", None)
            logging.debug("paired merge: trimmed transcript %s to its own %d words", u["transcript_id"], end - start)
            continue
        share, _n, u, _mask, _pairs, others, _s, _e = max(covered, key=lambda c: c[0])
        kept.pop(u["transcript_id"])
        for d in dropped:
            if d["kept_transcript_id"] == u["transcript_id"]:
                d["kept_transcript_id"] = others[0]["transcript_id"]
        dropped.append({"transcript_id": u["transcript_id"], "kept_transcript_id": others[0]["transcript_id"],
                        "reason": "covered", "similarity": round(share, 2)})


# ------------------------------------------------------- sentence stitching

def _ends_sentence(text):
    return bool(_SENTENCE_END.search((text or "").strip()))


def is_non_speech(text):
    """True for a row that is only recognizer event tags ("[breath]")."""
    text = (text or "").strip()
    return bool(text) and bool(_NON_SPEECH.match(text))


def lexical_words(text):
    """The words of a text, event tags left out."""
    return _LEXICAL_WORD.findall(_TAG.sub(" ", text or ""))


def _speaker_bounded_pair(by_device):
    """True when every row of both laptops carries a diarizer cluster: two
    MOSS runs, each cut by speaker and stamped on its recording's clock."""
    return len(by_device) == 2 and all(_speaker_bounded(u) for units in by_device.values() for u in units)


def _speaker_bounded(u):
    """True for a row the recognizer cut by speaker: a MOSS turn, which
    carries its diarizer cluster. Its first words are its speaker's own,
    never the tail of whoever spoke before, so step (1) leaves it alone."""
    return bool((u.get("confidence") or {}).get("cluster"))


def _leading_tail(text):
    """(tail, rest) when a sentence ends within the first STITCH_LEAD_WORDS
    words of ``text`` and more words follow: the tail is the end of the
    previous speaker's sentence that landed in this segment."""
    words = (text or "").split()
    for i in range(min(STITCH_LEAD_WORDS, len(words) - 1)):
        if _ends_sentence(words[i]):
            return " ".join(words[:i + 1]), " ".join(words[i + 1:])
    return None, text


def stitch_sentences(utterances, dropped=None):
    """Post: the kept utterances in time order, stitched back into sentences.
    (1) A leading sentence tail ("it." in "it. What's bothering me most?")
    moves to the previous utterance when that one does not end a sentence
    and started within STITCH_GAP seconds of this one ending its tail; rows
    the recognizer cut by speaker (MOSS turns, which carry their cluster)
    keep their first words.
    (2) Consecutive utterances of one speaker on one device within
    STITCH_GAP become one turn, sentence ends or not: a turn is the unit a
    negotiation move is coded on, and the recognizer's cuts fall at pauses.
    (3) An unnamed piece between two pieces of one speaker, within the gap on
    both sides, is that speaker's. Each stitched utterance keeps the first
    piece's transcript_id, lists the others in ``stitched_from`` and carries
    the sentence in ``text``; nothing exceeds STITCH_MAX_SECONDS or
    STITCH_MAX_WORDS. (4) A short unnamed piece (STITCH_SHORT_WORDS words or
    fewer) right after or right before a named piece on the same device,
    within the gap, is that speaker's: "[UH] So" before a sentence, "Yeah."
    after one. An adopted piece carries ``_speaker`` so the stored codes
    show the name the coder saw. Rows of event tags alone ("[breath]") are
    not utterances and are left out first. ``dropped`` receives pieces
    emptied by (1) and the non-speech rows."""
    rows = sorted((dict(u) for u in utterances), key=lambda u: (u["start_time"], u["transcript_id"]))
    # (0) event tags alone
    speech = []
    for u in rows:
        if is_non_speech(u.get("text")):
            if dropped is not None:
                dropped.append({"transcript_id": u["transcript_id"], "kept_transcript_id": None,
                                "reason": "non_speech", "similarity": 1.0})
            continue
        speech.append(u)
    rows = speech
    # (1) leading tails
    out = []
    for u in rows:
        tail, rest = _leading_tail(u.get("text"))
        prev = out[-1] if out else None
        if tail and prev is not None and not _ends_sentence(prev.get("text")) \
                and not _speaker_bounded(u) and not _speaker_bounded(prev) \
                and float(u["start_time"]) - _span(prev)[1] <= STITCH_GAP:
            prev["text"] = ((prev.get("text") or "").rstrip() + " " + tail).strip()
            prev["length"] = max(float(prev.get("length") or 0), float(u["start_time"]) - float(prev["start_time"]) + 0.5)
            prev.setdefault("stitched_from", []).append(u["transcript_id"])
            if not rest.strip():
                if dropped is not None:
                    dropped.append({"transcript_id": u["transcript_id"], "kept_transcript_id": prev["transcript_id"],
                                    "reason": "fragment", "similarity": 1.0})
                continue
            u["text"] = rest
            u["start_time"] = float(u["start_time"]) + 0.3   # the tail took the first beat
            u["length"] = max(float(u.get("length") or 0) - 0.3, 0.1)
        out.append(u)
    # (3) unnamed pieces between one speaker's pieces
    for i in range(1, len(out) - 1):
        u, prev, nxt = out[i], out[i - 1], out[i + 1]
        if not u.get("speaker_tag") and prev.get("speaker_tag") and prev.get("speaker_tag") == nxt.get("speaker_tag") \
                and float(u["start_time"]) - _span(prev)[1] <= STITCH_GAP and float(nxt["start_time"]) - _span(u)[1] <= STITCH_GAP:
            u["speaker_tag"] = prev["speaker_tag"]
            u["team"] = prev.get("team", u.get("team"))
            u["adopted"] = True
    # (4) short unnamed pieces beside a named piece on the same device; not
    # a MOSS turn, whose cluster naming could not place: adoption by its
    # neighbour was a coin flip on Group 7 (2026-10-19) and moved rows
    # across teams. (3) still applies: between two pieces of one speaker.
    for i, u in enumerate(out):
        if u.get("speaker_tag") or len(lexical_words(u.get("text"))) > STITCH_SHORT_WORDS or _speaker_bounded(u):
            continue
        owners = []
        if i > 0:
            prev = out[i - 1]
            gap = float(u["start_time"]) - _span(prev)[1]
            if prev.get("speaker_tag") and prev.get("session_device_id") == u.get("session_device_id") and gap <= STITCH_GAP:
                owners.append((max(gap, 0.0), prev))
        if i + 1 < len(out):
            nxt = out[i + 1]
            gap = float(nxt["start_time"]) - _span(u)[1]
            if nxt.get("speaker_tag") and nxt.get("session_device_id") == u.get("session_device_id") and gap <= STITCH_GAP:
                owners.append((max(gap, 0.0), nxt))
        if owners:
            owner = min(owners, key=lambda o: o[0])[1]
            u["speaker_tag"] = owner["speaker_tag"]
            u["team"] = owner.get("team", u.get("team"))
            u["adopted"] = True
    # (2) one speaker's consecutive pieces
    stitched = []
    for u in out:
        prev = stitched[-1] if stitched else None
        same = prev is not None and u.get("speaker_tag") and u.get("speaker_tag") == prev.get("speaker_tag") \
            and u.get("session_device_id") == prev.get("session_device_id")
        gap_ok = prev is not None and float(u["start_time"]) - _span(prev)[1] <= STITCH_GAP
        if same and gap_ok:
            words = len((prev.get("text") or "").split()) + len((u.get("text") or "").split())
            if _span(u)[1] - float(prev["start_time"]) <= STITCH_MAX_SECONDS and words <= STITCH_MAX_WORDS:
                prev["text"] = ((prev.get("text") or "").rstrip() + " " + (u.get("text") or "").strip()).strip()
                prev["length"] = _span(u)[1] - float(prev["start_time"])
                seen = prev.setdefault("stitched_from", [])
                for tid in [u["transcript_id"]] + list(u.get("stitched_from") or []):
                    if tid not in seen and tid != prev["transcript_id"]:
                        seen.append(tid)
                continue
        stitched.append(u)
    for i, u in enumerate(stitched):
        u["index"] = i
        if u.get("stitched_from") or u.get("trimmed"):
            u["_text"] = u["text"]
            u["_stitched"] = list(u.get("stitched_from") or [])
        if u.get("adopted") and u.get("speaker_tag"):
            u["_speaker"] = u["speaker_tag"]
    return stitched


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


def code_utterances(codebook, utterances, llm=None, size=CHUNK_SIZE, context=CONTEXT_SIZE, names=DEFAULT_TEAMS,
                    parallel=None):
    """Every utterance coded, chunk by chunk. Returns (codes aligned with
    ``utterances``, each the utterance dict plus its four codes; invalid_codes).
    ``parallel`` chunks are coded at once (default NEGOTIATION_LLM_PARALLEL);
    the result is in transcript order whatever the order the answers came."""
    llm = llm or call_llm
    parts = list(chunks(utterances, size, context))

    def code_chunk(ctx, chunk, depth):
        # An answer with no JSON array (the model talked instead, or ran out
        # of room mid-list) is asked for again with the lapse pointed out;
        # still nothing, and the chunk is coded in two halves, twice over,
        # before the run gives up. Group 2 of session 434 lost a whole run
        # to one such answer on utterances 40-79.
        prompt = build_prompt(codebook, chunk, ctx, names)
        lo, hi = chunk[0]["index"], chunk[-1]["index"]
        answer = llm(prompt)
        items = extract_array(answer)
        if not items:
            logging.warning("negotiation coding: no parseable codes for utterances %d-%d (answer began %r); asking again",
                            lo, hi, (answer or "")[:160])
            nudge = prompt + [
                {"role": "assistant", "content": (answer or "")[:400]},
                {"role": "user", "content": "That answer held no JSON array. Reply with only the JSON array of "
                                            "codes, one object per utterance, i from %d to %d." % (lo, hi)}]
            items = extract_array(llm(nudge))
        if items:
            return validate_codes(items, codebook, [u["index"] for u in chunk])
        if len(chunk) > 1 and depth < 2:
            mid = len(chunk) // 2
            left = code_chunk(ctx, chunk[:mid], depth + 1)
            right_ctx = (list(ctx) + chunk[:mid])[-context:] if context else []
            right = code_chunk(right_ctx, chunk[mid:], depth + 1)
            return {**left[0], **right[0]}, left[1] + right[1]
        raise RuntimeError("LLM returned no parseable codes for utterances %d-%d" % (lo, hi))

    def one(part):
        ctx, chunk = part
        try:
            return code_chunk(ctx, chunk, 0)
        except RuntimeError as e:
            raise RuntimeError("LLM returned no parseable codes for utterances %d-%d (%s)"
                               % (chunk[0]["index"], chunk[-1]["index"], e)) from e

    workers = max(1, int(parallel if parallel is not None else llm_parallel()))
    if workers > 1 and len(parts) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(workers, len(parts))) as pool:
            results = list(pool.map(one, parts))
    else:
        results = [one(part) for part in parts]
    coded, invalid = [], 0
    for (_ctx, chunk), (by_index, bad) in zip(parts, results):
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


def infer_teams(speaker_tags, names=TEAMS):
    """Teams read off speaker names: a tag that begins with exactly one team
    name (case-insensitive, letters and digits only: "Buyer1", "buyer-g3",
    "SELLER 2") is that team's. Lets a class that enrols students as
    <team>1..<team>3 skip the manual assignment; anything ambiguous or
    unmatched is left unassigned."""
    out = {}
    lowered = [(n, n.lower()) for n in names]
    for tag in speaker_tags:
        if not tag:
            continue
        key = "".join(ch for ch in str(tag).lower() if ch.isalnum())
        hits = [n for n, low in lowered if key.startswith("".join(ch for ch in low if ch.isalnum()))]
        if len(hits) == 1:
            out[str(tag)] = hits[0]
    return out


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


# ------------------------------------------------------------- export

EXPORT_COLUMNS = ("group", "pod", "side", "team", "speaker_tag", "named", "far_side", "closed_world", "match_sim",
                  "run_id", "transcript_id", "start_time", "clock", "length", "text", "stitched_from")


def clock_text(seconds):
    """Session-clock seconds as h:mm:ss (what the transcript panel shows)."""
    try:
        s = int(round(float(seconds)))
    except (TypeError, ValueError):
        return ""
    return "%d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60)


def _natural(text):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", str(text or ""))]


def group_sort_key(group):
    """"Group 2" before "Group 10"; unnamed groups last."""
    return (group in (None, ""), _natural(group))


def export_row(code, pods, dims, run_id=None, labels=None):
    """One CSV row (EXPORT_COLUMNS then the scheme's dimensions) for a
    code_row dict; ``pods`` maps device id -> {name, group, side}. With
    ``labels`` (alias -> "<team> 2", speaker_labels) the speaker column
    carries the team label, so an export names nobody."""
    pod = pods.get(code.get("session_device_id")) or {}
    named = "adopted" if code.get("adopted") else ("yes" if code.get("speaker_tag") else "no")
    values = [";".join(code[d]) if isinstance(code.get(d), list) else (code.get(d) or "") for d in dims]
    tag = code.get("speaker_tag") or ""
    return [pod.get("group") or "", pod.get("name") or "", pod.get("side") or "", code.get("team") or "",
            (labels or {}).get(tag, tag), named, "yes" if code.get("far_side") else "",
            "yes" if code.get("closed_world") else "", "" if code.get("match_sim") is None else code["match_sim"],
            "" if run_id is None else run_id, code.get("transcript_id"), code.get("start_time"),
            clock_text(code.get("start_time")), code.get("length"), code.get("text") or "",
            ";".join(str(t) for t in (code.get("stitched_from") or []))] + values


# --------------------------------------------------------- orchestration

def line_team(transcript, sides=None, teams=None, names=TEAMS):
    """The team a transcript line counts for. In a paired session that is
    its device's side, except that a line the device named from the partner
    pod's roster (confidence.far_side: heard across the table) belongs to
    the other side. Without a side it is the tag's assignment, else
    "unassigned". The one rule for the run, the read-back and the re-roll,
    so a person is never on two teams at once."""
    side = (sides or {}).get(getattr(transcript, "session_device_id", None))
    if side in names:
        conf = _attribution_confidence(transcript)
        if conf and conf.get("far_side") and not conf.get("closed_world"):
            return other_team(side, names)
        return side
    return team_of(getattr(transcript, "speaker_tag", None) or "", teams, names)


def code_row(code, transcript, teams=None, sides=None, names=TEAMS):
    # One entry of the API's "codes" list: the utterance, its codes (one key
    # per dimension of the run's scheme), its team and whether the device
    # heard it from across the table.
    device_id = transcript.session_device_id
    conf = _attribution_confidence(transcript)
    values = dict(code.values())
    # A stitched or trimmed utterance was coded as the sentence the model saw,
    # not the stored fragment; show that sentence.
    presented = values.pop("_text", None)
    stitched = values.pop("_stitched", None) or []
    # An unnamed fragment the stitcher gave to the speaker around it was
    # coded, and is shown, under that name.
    adopted = values.pop("_speaker", None)
    # Runs since 2026-10-19 store the attribution the model saw: the speaker
    # after reconcile_clusters, the team the merge settled on, the start on
    # the aligned clock. The raw transcript row knows none of that, so the
    # read-back used to disagree with the summary (and a re-roll rewrote the
    # summary to match the raw rows). Older runs fall back to the row.
    stored = "_speaker_tag" in values
    tag = values.pop("_speaker_tag", None)
    coded_team = values.pop("_team", None)
    start = values.pop("_start", None)
    length = values.pop("_length", None)
    values.pop("_device", None)
    speaker_tag = tag if stored else (transcript.speaker_tag or adopted)
    side = (sides or {}).get(device_id)
    if stored and coded_team is not None and side in names:
        team = coded_team                            # paired: the side the run coded it under
    elif stored:
        team = team_of(speaker_tag or "", teams, names)   # single pod: the assignment, at read time
    else:
        team = line_team(transcript, sides, teams, names)
    row = {"transcript_id": transcript.id, "session_device_id": device_id,
           "start_time": start if (stored and start is not None) else transcript.start_time,
           "length": length if (stored and length is not None) else transcript.length,
           "speaker_tag": speaker_tag,
           "adopted": bool(adopted and not transcript.speaker_tag),
           "text": presented if presented else transcript.transcript,
           "team": team,
           "far_side": bool(conf and conf.get("far_side")),
           "closed_world": bool(conf and conf.get("closed_world")),
           "match_sim": conf.get("sim") if conf else None,
           "stitched_from": stitched}
    row.update(values)
    return row


def coded_rows(run_id, teams=None, sides=None, names=TEAMS):
    """The run's code_row dicts in the order the model saw them: by the
    stored aligned start (older runs: the row's own clock), then transcript
    id. One list for the panel, the exports and the re-roll."""
    import database
    rows = [code_row(c, t, teams, sides, names) for c, t in database.get_negotiation_codes(run_id)]
    rows.sort(key=lambda r: (float(r.get("start_time") or 0.0), r["transcript_id"]))
    return rows


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
    # A side's primary is its pod with transcripts (a laptop that joined,
    # recorded nothing and was replaced by another must not stand in for
    # the side: Group 8 on 2026-10-16 paired an empty pod and coded the
    # real one alone), the lowest id among those.
    for d in sorted(database.get_negotiation_group_devices(device),
                    key=lambda d: (not database.session_device_transcript_count(d.id), d.id)):
        side = _side_of(d, names)
        if side and side not in primaries:
            primaries[side] = d
    # The pod is always in its own group list; .get() keeps a surprise from
    # the lookup a lone run rather than a crash that queues nothing.
    mine = primaries.get(my_side) if my_side else None
    if mine is not None and mine.id != device.id:
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
            diagnostics = {}
            recordings = {}
            for d in run.device_ids():
                pod = database.get_session_devices(id=d)
                if pod is not None and pod.processing_key:
                    recordings[d] = recordings_of(pod.processing_key)
            utterances, dropped = merge_paired(rows_by_device, sides, diagnostics, recordings)
            extra["cross_talk"] = {"dropped": len(dropped), "kept": len(utterances),
                                   "alignment": diagnostics.get("alignment"),
                                   "detail": dropped[:DROP_DETAIL_MAX]}
        else:
            rows = database.get_transcripts(session_device_id=run.session_device_id)
            utterances = utterances_from_rows(rows, sides.get(run.session_device_id))
            dropped = []
        utterances = stitch_sentences(utterances, dropped)
        if run.is_paired() or dropped:
            # Everything left out of the coding and why (duplicates, far-side
            # copies, fragments, non-speech rows); a single pod's record has
            # no alignment.
            extra.setdefault("cross_talk", {"alignment": None})
            extra["cross_talk"]["dropped"] = len(dropped)
            extra["cross_talk"]["kept"] = len(utterances)
            extra["cross_talk"]["detail"] = dropped[:DROP_DETAIL_MAX]
        coded, invalid = code_utterances(codebook, utterances, llm, names=names)
        database.add_negotiation_codes(run.id, coded, list(codebook["dimensions"]))
        if teams is None:
            teams = database.get_negotiation_run(run.id).teams_dict()
        if not teams and not run.is_paired():
            # Nobody assigned yet: the team on each speaker's profile first
            # (typed when enrolling), then names like Buyer1 / Seller2 for
            # the rest.
            tags = {u.get("speaker_tag") for u in utterances}
            teams = database.student_teams(tags, names)
            for tag, team in infer_teams(tags, names).items():
                teams.setdefault(tag, team)
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
        codes = coded_rows(run.id, teams, sides, names)
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
    pods = run_pods(run, sides)
    for pod in pods:
        pod["audio_posthoc_done"] = database.audio_posthoc_done(pod["id"])
    # A queued run is waiting on these pods' audio analyses (the gate its
    # job was queued with, audio_gate); the panel names them.
    waiting = [p["id"] for p in pods if not p["audio_posthoc_done"]] if run.status == "queued" else []
    payload = {"run": run.json(), "mode": "paired" if run.is_paired() else "single",
               "codebook": coding_scheme.panel_json(codebook_for_device(run.session_device_id)),
               "team_names": list(names), "pods": pods, "waiting_for": audio_gate(waiting),
               "teams": run.teams_dict(), "summary": run.summary_dict()}
    if with_codes:
        payload["codes"] = coded_rows(run.id, payload["teams"], sides, names)
    return payload


def queue_coding_run(session_id, session_device_id, teams=None, partner_device_id=None):
    """A run row for the pod (and its partner, in a paired session) and a
    coding job on the post-hoc queue. A run still queued for the same
    device(s) is reused (its teams updated when given) rather than stacking
    a second identical run behind it.

    Coding is the last stage of the post-hoc pipeline: it codes the post-hoc
    transcripts. A covered pod whose audio analysis is neither recorded
    complete nor in flight gets its audio leg queued ahead (when it has a
    recording to analyse), and the coding job waits for every gated pod's
    analysis (``after_audio``) — with all of them already analysed it runs
    as soon as it is reached, as before."""
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
    covered = [d for d in (session_device_id, partner_device_id) if d is not None]
    gated = audio_gate(covered)
    # The partner's audio job ahead of the first device's: the queue is
    # sequential, so the pair is analysed in one fixed order whichever pod
    # the instructor clicked. One pending GPU job per pod is the queue's rule.
    for d in reversed(gated):
        if database.audio_posthoc_status(d) == "missing":
            posthoc_queue.enqueue(session_id, [d], legs=("audio",))
    posthoc_queue.enqueue_coding(session_id, session_device_id, run.id, after_audio=gated)
    return run


def fail_run(run_id, error):
    """A queued run the queue will never execute (its audio prerequisite
    failed, or it was dropped): the row must not say "queued" forever."""
    import database
    run = database.get_negotiation_run(run_id)
    if run is not None and run.status in ("queued", "running"):
        database.update_negotiation_run(run_id, status="error", finished_at=_now(), error=error)


def cancel_run(run_id, reason):
    # A queued job dropped from the queue.
    fail_run(run_id, "cancelled: " + reason)


# ----------------------------------------------------------------- groups
#
# A group is a breakout table: the laptops that share a negotiation_group,
# each recording the same conversation from its own side. The group view
# shows the one conversation the coder reads (merge_paired, then
# stitch_sentences, over the group's primary laptops) and offers every
# laptop of the group as a view of it.

def group_pods(devices, names=TEAMS, transcript_count=None):
    """The laptops of one group: [{id, name, side, primary, transcripts}]
    in side order, then id. A side's primary is its lowest-id laptop with
    transcripts, the rule resolve_pair codes by; an extra laptop that joined
    the same slot is a view only, so the side's hearing is not merged twice.
    ``transcript_count`` maps a device id to its row count
    (database.session_device_transcript_count); without it every laptop
    counts as recorded."""
    count = transcript_count or (lambda device_id: 1)
    pods, primaries = [], set()
    for d in sorted(devices, key=lambda d: _pair_rank(d, names)):
        side = _side_of(d, names)
        n = int(count(d.id) or 0)
        key = side or "unsided"
        primary = n > 0 and key not in primaries
        if primary:
            primaries.add(key)
        pods.append({"id": d.id, "name": getattr(d, "name", None) or "Pod %s" % d.id,
                     "side": side, "primary": primary, "transcripts": n})
    return pods


def session_groups(devices, names=TEAMS, transcript_count=None):
    """The session's groups, [{group, pods}] in group order; laptops without
    a group make no group."""
    groups = {}
    for d in devices:
        group = getattr(d, "negotiation_group", None)
        if group:
            groups.setdefault(group, []).append(d)
    return [{"group": g, "pods": group_pods(groups[g], names, transcript_count)}
            for g in sorted(groups, key=group_sort_key)]


def group_line(u):
    """A merged utterance as the transcript panel's row (id, transcript,
    speaker_tag, ...) plus which laptop heard it and what was folded in."""
    conf = u.get("confidence") or {}
    line = {"id": u["transcript_id"], "session_device_id": u.get("session_device_id"),
            "start_time": u["start_time"], "length": u.get("length"),
            "transcript": u.get("text"), "speaker_tag": u.get("speaker_tag") or u.get("_speaker"),
            "speaker_id": u.get("speaker_id"), "question": bool(u.get("question")),
            "team": u.get("team"), "far_side": bool(conf.get("far_side")),
            "speaker_confidence": conf.get("percent"), "adopted": bool(u.get("adopted")),
            "reconciled_from": conf.get("reconciled_from"),
            "stitched_from": list(u.get("stitched_from") or []),
            "merged_from": list(u.get("merged_from") or [])}
    if u.get("device_start_time") is not None:
        # The merge moved this laptop onto the other's clock; its own clock
        # is what seeks its recording.
        line["device_start_time"] = u["device_start_time"]
    return line


def group_transcript(devices, rows_by_device, names=TEAMS, recordings=None):
    """The one conversation of a group as the coder reads it: merge_paired
    over the primary laptops' rows (``rows_by_device``: device id -> rows),
    then stitch_sentences. Returns {lines, dropped, alignment}: lines are
    group_line dicts in time order, dropped the merge's record of what was
    folded or left out, alignment the clock offset found (or None)."""
    sides = {d.id: _side_of(d, names) for d in devices if d.id in rows_by_device}
    diagnostics = {}
    utterances, dropped = merge_paired(rows_by_device, sides, diagnostics, recordings)
    stitched = stitch_sentences(utterances, dropped)
    return {"lines": [group_line(u) for u in stitched], "dropped": dropped,
            "alignment": diagnostics.get("alignment")}


def _alias_number(alias, team):
    """The number a class's own username carries for its team: with teams
    named Alpha and Beta, "Alp2G1S32" is Alpha 2 (the team's first three
    letters, then at most two more letters, then the digits). "AlphaG4S31"
    carries none: its 4 is the group."""
    stem = re.escape((team or "")[:3])
    if not stem:
        return None
    m = re.match(r"^%s[a-z]{0,2}(\d+)" % stem, alias or "", re.I)
    return int(m.group(1)) if m else None


def speaker_labels(rosters, names=TEAMS, lines=None):
    """Display names for a group's speakers: "<team> <n>" for each student
    on a laptop's roster, numbered within the team. A username that carries
    its own number keeps it (_alias_number); the rest, a real name or a
    nickname, take the lowest free numbers in alphabetical order, so a
    laptop whose three students signed up with their names reads
    "<team> 1", 2 and 3 and no name leaves the roster. A name the merge
    carries that no roster lists (a guest, a student of a laptop outside the
    group) keeps its tag. ``rosters`` is [{session_device_id, side,
    aliases}] per laptop; the result is a list of {alias, label, team,
    team_index, index, session_device_id} in team order, then number."""
    teams = list(names)
    seen = {}
    per_team = {t: [] for t in teams}
    for roster in rosters or []:
        side = roster.get("side")
        for alias in roster.get("aliases") or []:
            alias = (alias or "").strip()
            if not alias or alias in seen:
                continue
            entry = {"alias": alias, "team": side if side in teams else None,
                     "session_device_id": roster.get("session_device_id")}
            seen[alias] = entry
            if entry["team"]:
                per_team[entry["team"]].append(entry)
    for team, entries in per_team.items():
        taken, unnumbered = set(), []
        for e in sorted(entries, key=lambda e: e["alias"].lower()):
            n = _alias_number(e["alias"], team)
            if n is not None and n not in taken:
                taken.add(n)
                e["index"] = n
            else:
                unnumbered.append(e)
        free = 1
        for e in unnumbered:
            while free in taken:
                free += 1
            taken.add(free)
            e["index"] = free
        for e in entries:
            e["label"] = "%s %d" % (team, e["index"])
            e["team_index"] = teams.index(team)
    for l in lines or []:
        tag = l.get("speaker_tag")
        if tag and tag not in seen:
            team = l.get("team") if l.get("team") in teams else None
            seen[tag] = {"alias": tag, "team": team, "session_device_id": l.get("session_device_id")}
    for e in seen.values():
        e.setdefault("label", e["alias"])
        e.setdefault("index", None)
        e.setdefault("team_index", teams.index(e["team"]) if e.get("team") in teams else None)
    return sorted(seen.values(), key=lambda e: (
        e["team_index"] if e["team_index"] is not None else len(teams),
        e["index"] if e["index"] is not None else 10 ** 6, e["alias"].lower()))


def _line_team_for(line, team_of, names):
    # The team a merged line counts for in the team view: the roster team of
    # the speaker it was named as (the one place a person is on one team),
    # else the team the merge gave the line (a guest named on one side),
    # else none: an unnamed line is nobody's floor time.
    if not line.get("speaker_tag"):
        return None
    team = team_of.get(line["speaker_tag"])
    if team in names:
        return team
    return line.get("team") if line.get("team") in names else None


def group_team_dynamics(lines, speakers, names=TEAMS):
    """The group's dynamics with each team as one voice: each team's
    speaking share and floor-takes (turns), who hands the floor to whom
    across and within the teams, each team's questions and
    interruptions. ``speakers`` is speaker_labels' list, which says whose
    team each name is on. Unnamed lines are 'Unattributed' in the talk
    metrics, as in the per-speaker view, and left out of the networks."""
    from analytics import compute_conversation_dynamics, compute_talk_metrics
    teams = list(names)
    team_of = {s["alias"]: s.get("team") for s in speakers or []}
    ordered = sorted(lines, key=lambda l: (float(l.get("start_time") or 0), l.get("id") or 0))
    tagged = [(l, _line_team_for(l, team_of, teams)) for l in ordered]
    result = compute_conversation_dynamics(
        [(team, l["start_time"], l.get("length")) for l, team in tagged if team])
    result["talk"] = compute_talk_metrics(
        [(team, l["start_time"], l.get("length"), l.get("question"), l.get("transcript")) for l, team in tagged],
        enrolled=teams)
    # Hand-offs by team pair from the speaker changes: within a team the
    # floor passes between teammates, across it the other side answers.
    handoffs = {}
    prev = None
    for l, team in tagged:
        if not team:
            continue
        tag = l["speaker_tag"]
        if prev is not None and tag != prev[0]:
            key = (prev[1], team)
            handoffs[key] = handoffs.get(key, 0) + 1
        prev = (tag, team)
    result["handoffs"] = [{"from": f, "to": t, "count": handoffs.get((f, t), 0)}
                          for f in teams for t in teams]
    result["names"] = teams
    result["members"] = {t: [s["label"] for s in speakers or [] if s.get("team") == t] for t in teams}
    return result


PIECE_MIN_PAIRS = 3        # duplicate copies a partner cluster must share to cut a piece...
PIECE_MIN_SHARE = 0.10     # ...and that share of the cluster's rows
PIECE_NEAR_S = 90.0        # an unpaired row joins the piece of the nearest paired row this close
PRINT_ROW_MIN_SIM = 0.8    # rows that may be cut into a session print for the renaming


def _partner_on_own_clock(alignment, own_device):
    # A partner row's session time as this laptop's clock reads it: the
    # merge's alignment maps the other device onto the reference.
    if not alignment:
        return lambda t: t
    offsets = alignment.get("offsets") or []
    if not offsets:
        return lambda t: t

    def off(t):
        return float(min(offsets, key=lambda o: abs(float(o["at"]) - t))["offset"] or 0.0)
    if alignment.get("reference_device") == own_device:
        return lambda t: t - off(t)
    return lambda t: t + off(t)


def rename_plan(own_rows, partner_rows, own_device, partner_device, sides):
    """What a renaming pass (asr_connectors/moss_rename.py) names: this
    laptop's diarizer clusters cut into pieces where the partner laptop's
    clusters split them. The duplicate copies the merge matches pair each
    own row with a partner cluster; a cluster paired with two or more
    partner clusters (PIECE_MIN_PAIRS copies each, PIECE_MIN_SHARE of its
    rows) holds that many voices, one piece per partner cluster; its other
    rows join the piece of the nearest paired row within PIECE_NEAR_S, the
    rest a remainder piece. A cluster the partner does not split is one
    piece. ``print_rows``: rows of either laptop that a session print may
    be cut from, named from prints at PRINT_ROW_MIN_SIM or better, not in
    a split cluster and not a contested name (a voice both laptops claim as
    their own student under different names), partner rows moved onto this
    laptop's clock. Each piece carries a ``side_hint``: the partner's claim
    on the voice when uncontested, else this laptop's earlier hearing.
    Returns {pieces: [{id, cluster, source_cluster, partner_cluster, rows,
    spans}], print_rows: [...], alignment}."""
    rows_by_device = {own_device: list(own_rows)}
    if partner_device is not None and partner_rows:
        rows_by_device[partner_device] = list(partner_rows)
    diagnostics = {}
    _kept, dropped = merge_paired(rows_by_device, sides, diagnostics)
    by_id, cluster_of = {}, {}
    for device_id, rows in rows_by_device.items():
        for r in rows:
            u = _utterance(r, sides.get(device_id))
            by_id[r.id] = (device_id, r, u)
            c = (u.get("confidence") or {}).get("cluster")
            if c:
                cluster_of[r.id] = (device_id, c)
    pairs = {}                              # (own cluster, partner cluster) -> count
    partner_of = {}                         # own row id -> partner cluster
    for d in dropped:
        if d.get("reason") != "duplicate":
            continue
        a, b = cluster_of.get(d["transcript_id"]), cluster_of.get(d["kept_transcript_id"])
        if not a or not b or a[0] == b[0]:
            continue
        own, far = (a, b) if a[0] == own_device else (b, a)
        own_row = d["transcript_id"] if a[0] == own_device else d["kept_transcript_id"]
        pairs[(own[1], far[1])] = pairs.get((own[1], far[1]), 0) + 1
        partner_of[own_row] = far[1]
    members = {}
    for rid, (device_id, r, _u) in by_id.items():
        if device_id == own_device and rid in cluster_of:
            members.setdefault(cluster_of[rid][1], []).append(r)
    # Which side a partner cluster's voice is on, by the partner's own
    # claim: a cluster it named as its student sits across this laptop's
    # table; one it heard from across its table is this laptop's own.
    partner_claim, partner_name = {}, {}
    for rid, (device_id, r, u) in by_id.items():
        if device_id == own_device or rid not in cluster_of:
            continue
        conf = u.get("confidence") or {}
        if u.get("speaker_tag") and conf.get("named_by") in ("prints", "elimination"):
            votes = partner_claim.setdefault(cluster_of[rid][1], {"far": 0, "own": 0})
            votes["own" if conf.get("far_side") else "far"] += 1
            names = partner_name.setdefault(cluster_of[rid][1], {})
            names[u["speaker_tag"]] = names.get(u["speaker_tag"], 0) + 1
    # A voice both laptops claim as their own student under different
    # names is contested: one of them is wrong, and neither name may seed
    # a session print from it (that is how a print comes to be another
    # student's voice), nor is the partner's side claim worth a hint.
    own_name = {}
    for cluster, rows in members.items():
        names = {}
        for r in rows:
            u = by_id[r.id][2]
            conf = u.get("confidence") or {}
            if u.get("speaker_tag") and conf.get("named_by") == "prints" and not conf.get("far_side"):
                names[u["speaker_tag"]] = names.get(u["speaker_tag"], 0) + 1
        if names:
            own_name[cluster] = max(names, key=names.get)
    contested_pairs, contested_names = set(), set()
    for (c, far), n in pairs.items():
        rows = members.get(c) or []
        if n < PIECE_MIN_PAIRS or n < PIECE_MIN_SHARE * len(rows):
            continue
        mine, theirs = own_name.get(c), partner_name.get(far)
        claim = partner_claim.get(far)
        if mine and theirs and claim and claim["far"] > claim["own"]:
            their_name = max(theirs, key=theirs.get)
            if their_name != mine:
                contested_pairs.add((c, far))
                contested_names.update((mine, their_name))

    def side_hint(partner_cluster, own_rows):
        cluster = cluster_of[own_rows[0].id][1] if own_rows and own_rows[0].id in cluster_of else None
        votes = partner_claim.get(partner_cluster) if partner_cluster else None
        if votes and votes["far"] != votes["own"] and (cluster, partner_cluster) not in contested_pairs:
            return "far" if votes["far"] > votes["own"] else "own"
        own_votes = {"far": 0, "own": 0}
        for r in own_rows:
            u = by_id[r.id][2]
            conf = u.get("confidence") or {}
            if u.get("speaker_tag") and conf.get("named_by") == "prints":
                own_votes["far" if conf.get("far_side") else "own"] += 1
        if own_votes["far"] != own_votes["own"]:
            return "far" if own_votes["far"] > own_votes["own"] else "own"
        return None
    split = {}
    pieces = []
    for cluster, rows in sorted(members.items()):
        rows = sorted(rows, key=lambda r: float(r.start_time or 0))
        strong = sorted(((n, far) for (c, far), n in pairs.items()
                         if c == cluster and n >= PIECE_MIN_PAIRS and n >= PIECE_MIN_SHARE * len(rows)),
                        key=lambda nf: (-nf[0], nf[1]))
        if len(strong) < 2:
            pieces.append({"id": cluster, "cluster": cluster, "source_cluster": None,
                           "partner_cluster": strong[0][1] if strong else None,
                           "side_hint": side_hint(strong[0][1] if strong else None, rows),
                           "rows": [r.id for r in rows], "spans": [[float(r.start_time), float(r.start_time) + float(r.length or 0)] for r in rows]})
            continue
        split[cluster] = [far for _n, far in strong]
        groups = {far: [] for _n, far in strong}
        loose = []
        for r in rows:
            far = partner_of.get(r.id)
            (groups[far] if far in groups else loose).append(r)
        anchors = [(float(r.start_time), far) for far, rs in groups.items() for r in rs]
        remainder = []
        for r in loose:
            t = float(r.start_time or 0)
            near = min(anchors, key=lambda a: abs(a[0] - t)) if anchors else None
            if near and abs(near[0] - t) <= PIECE_NEAR_S:
                groups[near[1]].append(r)
            else:
                remainder.append(r)
        parts = [(far, sorted(rs, key=lambda r: float(r.start_time or 0))) for far, rs in groups.items()]
        if remainder:
            parts.append((None, remainder))
        for i, (far, rs) in enumerate(parts):
            pieces.append({"id": "%s%s" % (cluster, chr(ord("a") + i)), "cluster": cluster, "source_cluster": cluster,
                           "partner_cluster": far, "side_hint": side_hint(far, rs), "rows": [r.id for r in rs],
                           "spans": [[float(r.start_time), float(r.start_time) + float(r.length or 0)] for r in rs]})
    # Which partner clusters this laptop's clusters split, symmetrically.
    partner_members = {}
    for rid, (device_id, r, _u) in by_id.items():
        if device_id != own_device and rid in cluster_of:
            partner_members.setdefault(cluster_of[rid][1], []).append(r)
    partner_split = set()
    for pc, rs in partner_members.items():
        strong = [c for (c, far), n in pairs.items() if far == pc and n >= PIECE_MIN_PAIRS and n >= PIECE_MIN_SHARE * len(rs)]
        if len(strong) >= 2:
            partner_split.add(pc)
    shift = _partner_on_own_clock(diagnostics.get("alignment"), own_device)
    print_rows = []
    for rid, (device_id, r, u) in by_id.items():
        conf = u.get("confidence") or {}
        if not u.get("speaker_tag") or conf.get("named_by") != "prints" or float(conf.get("sim") or 0) < PRINT_ROW_MIN_SIM:
            continue
        if u["speaker_tag"] in contested_names:
            continue
        c = cluster_of.get(rid)
        if not c or (device_id == own_device and c[1] in split) or (device_id != own_device and c[1] in partner_split):
            continue
        start = float(r.start_time) if device_id == own_device else shift(float(r.start_time))
        print_rows.append({"speaker_tag": u["speaker_tag"], "start_time": start, "length": float(r.length or 0),
                           "sim": conf.get("sim"), "far_side": bool(conf.get("far_side")), "device": device_id})
    return {"pieces": pieces, "print_rows": print_rows, "split": {c: f for c, f in split.items()},
            "contested": sorted(contested_names), "alignment": diagnostics.get("alignment")}


def group_dynamics(lines, enrolled=None, speakers=None, names=TEAMS):
    """The conversation dynamics of a group's merged transcript: the same
    per-speaker equity, response network and talk metrics a single pod
    gets (analytics.compute_conversation_dynamics / compute_talk_metrics),
    over the merged lines (group_line dicts) of both laptops, so a line is
    counted once and under the laptop that heard its speaker best. With
    ``speakers`` (speaker_labels) the result also carries ``teams``: the
    same analyses with each team as one voice (group_team_dynamics)."""
    from analytics import compute_conversation_dynamics, compute_talk_metrics
    ordered = sorted(lines, key=lambda l: (float(l.get("start_time") or 0), l.get("id") or 0))
    named = [(l["speaker_tag"], l["start_time"], l.get("length")) for l in ordered if l.get("speaker_tag")]
    result = compute_conversation_dynamics(named)
    result["talk"] = compute_talk_metrics(
        [(l.get("speaker_tag"), l["start_time"], l.get("length"), l.get("question"), l.get("transcript")) for l in ordered],
        enrolled=list(enrolled or []))
    if speakers is not None:
        result["teams"] = group_team_dynamics(ordered, speakers, names)
    return result
