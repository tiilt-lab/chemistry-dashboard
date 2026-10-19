"""Name MOSS's anonymous speakers (S01, S02, ...) against the students' voice
prints, the way the bake-off did (tools/bakeoff/name_turns.py; 2026-10-18,
Group 7: 94% of speech named on both laptops).

Prints per student, own roster and the partner pod's: the enrolment print
when there is one, else a print cut from the student's confidently named
live rows (sim >= LIVE_SIM, >= 2 s, not heard from across the table) on THIS
recording, PRINT_MIN_S or more of audio. A cluster is named once on up to
MAX_CLUSTER_S of its longest turns: the best print wins above its kind's
floor (an enrolment print was made on another day and microphone, a session
print on this one) and by MARGIN over the runner-up of any kind. The side a
cluster sits on (own laptop or the far side of the table) comes from the
prints, or from the live rows' majority when the best own and far prints are
of different kinds (a session print scores ~0.3-0.4 even on other voices of
its channel; an enrolment print ~0.2 on its own speaker, so own-vs-far across
kinds is biased); a weak enrolment name on the side the live rows contradict
is a guess, not a name. By elimination, exactly one unprinted student on a
side takes the largest unnamed cluster (>= ELIM_MIN_S) on that side.

Pure functions over numpy audio and an ``embed(signal) -> unit vector``
callable, so the rules are testable without the model.
"""
import numpy as np

MARGIN = 0.06               # best print over the runner-up of any kind
MIN_TURN = 1.0              # turns shorter than this carry no voice
MAX_CLUSTER_S = 120.0       # audio a cluster is named on
PRINT_MIN_S = 20.0          # a session print needs this much of the student
PRINT_MAX_S = 60.0          # and uses at most this much
LIVE_SIM = 0.6              # a live row this sure is cut into the print
LIVE_MIN_LEN = 2.0
MIN_SIM = {"enrolment": 0.35, "session": 0.60}
SIDE_MARGIN = 0.05          # best own print vs best far print: this far apart decides the side
LIVE_SIDE_SHARE = 0.10      # live rows: own minus far share of the cluster's time that decides its side
ELIM_MIN_S = 60.0


def unit(v):
    v = np.asarray(v, dtype=np.float32).ravel()
    return v / (np.linalg.norm(v) + 1e-9)


def session_prints(audio, sr, to_rec, rows, embed, wanted):
    """{alias: (unit vector, seconds used)} for the students in ``wanted``
    from their confidently named live rows. ``rows``: dicts with
    speaker_tag, start_time (session clock), length, sim, far_side, from
    either laptop of the group; only the stretches inside this recording
    (``to_rec`` maps the session clock to seconds into ``audio``) are cut."""
    out = {}
    n = len(audio)
    by_alias = {}
    for r in rows:
        tag = r.get("speaker_tag")
        if not tag or tag not in wanted or r.get("far_side"):
            continue
        if float(r.get("length") or 0.0) < LIVE_MIN_LEN or float(r.get("sim") or 0.0) < LIVE_SIM:
            continue
        by_alias.setdefault(tag, []).append(r)
    for alias, rs in by_alias.items():
        sig, total = [], 0.0
        for r in sorted(rs, key=lambda r: -float(r.get("sim") or 0.0)):
            s = to_rec(float(r["start_time"])); e = s + float(r["length"])
            i0, i1 = int(s * sr), int(e * sr)
            if i0 < 0 or i1 > n or i1 <= i0:
                continue
            sig.append(audio[i0:i1]); total += e - s
            if total >= PRINT_MAX_S:
                break
        if total >= PRINT_MIN_S:
            out[alias] = (unit(embed(np.concatenate(sig))), round(total, 1))
    return out


def live_majority(turns, to_session, live_rows_own):
    """(side or None, shares): per cluster, the share of its time the live
    service called own-side, far-side or unnamed on this laptop's own rows."""
    own = far = unnamed = 0.0
    spans = [(float(r["start_time"]), float(r["start_time"]) + float(r.get("length") or 0.0),
              r.get("speaker_tag"), bool(r.get("far_side"))) for r in live_rows_own]
    for t in turns:
        s0, s1 = to_session(float(t["start"])), to_session(float(t["end"]))
        for s, e, tag, is_far in spans:
            ov = min(s1, e) - max(s0, s)
            if ov <= 0:
                continue
            if not tag:
                unnamed += ov
            elif is_far:
                far += ov
            else:
                own += ov
    total = own + far + unnamed
    if total <= 0:
        return None, {}
    shares = {"own": round(own / total, 2), "far": round(far / total, 2), "unnamed": round(unnamed / total, 2)}
    if own - far >= LIVE_SIDE_SHARE * total:
        return "own", shares
    if far - own >= LIVE_SIDE_SHARE * total:
        return "far", shares
    return None, shares


def score(vec, prints, kinds, roster):
    """(name or None, best sim, margin, side or None, all sims, guess)."""
    sims = sorted(((float(vec @ prints[n]), n) for n in prints), reverse=True)
    best, runner = sims[0], (sims[1] if len(sims) > 1 else (-1.0, None))
    margin = best[0] - runner[0]
    own = max((s for s, n in sims if roster.get(n) == "own"), default=-1.0)
    far = max((s for s, n in sims if roster.get(n) == "far"), default=-1.0)
    side = "far" if far - own >= SIDE_MARGIN else ("own" if own - far >= SIDE_MARGIN else None)
    ok = best[0] >= MIN_SIM[kinds.get(best[1], "enrolment")] and margin >= MARGIN
    return (best[1] if ok else None), best[0], margin, side, {n: round(s, 3) for s, n in sims}, (None if ok else best[1])


def name_clusters(audio, sr, turns, roster, prints, kinds, live_rows_own, to_session, embed):
    """{cluster: {name, guess, sim, margin, side, side_from, seconds, named_from,
    by_elimination, live}} for MOSS turns (dicts with start, end, speaker) in
    recording seconds. ``roster`` alias -> "own" | "far"; ``prints`` alias ->
    unit vector; ``kinds`` alias -> "enrolment" | "session"."""
    by_cluster = {}
    for t in turns:
        by_cluster.setdefault(t["speaker"], []).append(t)
    out = {}
    for c, ts in by_cluster.items():
        seconds = round(sum(float(t["end"]) - float(t["start"]) for t in ts), 1)
        longest = sorted((t for t in ts if float(t["end"]) - float(t["start"]) >= MIN_TURN),
                         key=lambda t: -(float(t["end"]) - float(t["start"])))
        sig, total = [], 0.0
        for t in longest:
            i0, i1 = int(float(t["start"]) * sr), int(float(t["end"]) * sr)
            if i1 <= i0 or i1 > len(audio):
                continue
            sig.append(audio[i0:i1]); total += float(t["end"]) - float(t["start"])
            if total >= MAX_CLUSTER_S:
                break
        if total < MIN_TURN or not prints:
            out[c] = dict(name=None, guess=None, sim=None, margin=None, side=None, side_from=None,
                          seconds=seconds, named_from=0.0, by_elimination=False, live={})
            continue
        n, sim, margin, side, allsims, guess = score(unit(embed(np.concatenate(sig))), prints, kinds, roster)
        best_own = max(((allsims[x], x) for x in allsims if roster.get(x) == "own"), default=(None, None))
        best_far = max(((allsims[x], x) for x in allsims if roster.get(x) == "far"), default=(None, None))
        lm_side, lm_shares = live_majority(ts, to_session, live_rows_own)
        side_from = "prints"
        if best_own[1] and best_far[1] and kinds.get(best_own[1]) != kinds.get(best_far[1]):
            side, side_from = lm_side, "live"
        elif side is None and lm_side is not None:
            side, side_from = lm_side, "live"
        if n is not None and side is not None and roster.get(n) != side and kinds.get(n) != "session":
            guess, n = n, None
        if n is not None:
            # A named cluster sits where its student does; the side question
            # only remains for the unnamed.
            side, side_from = roster.get(n), "name"
        out[c] = dict(name=n, guess=guess, sim=round(sim, 3), margin=round(margin, 3), side=side, side_from=side_from,
                      seconds=seconds, named_from=round(total, 1), by_elimination=False, live=lm_shares)
    # One name per laptop: a print two clusters match is matching two voices
    # (a session print cut from misnamed live rows, or one voice the
    # diarizer split). The closest cluster keeps the name; the others carry
    # it as a guess, so the merge can give them the other laptop's name.
    by_name = {}
    for c, v in out.items():
        if v["name"]:
            by_name.setdefault(v["name"], []).append(c)
    for name, cs in by_name.items():
        if len(cs) < 2:
            continue
        cs.sort(key=lambda c: (-(out[c]["sim"] or 0.0), -out[c]["seconds"]))
        for c in cs[1:]:
            out[c].update(name=None, guess=name, side_from="duplicate", duplicate_of=cs[0])
    for side in ("own", "far"):
        unprinted = [al for al, sd in roster.items() if sd == side and al not in prints]
        if len(unprinted) != 1:
            continue
        cands = sorted(((c, v) for c, v in out.items() if v["name"] is None and v.get("side") == side and v["seconds"] >= ELIM_MIN_S),
                       key=lambda cv: -cv[1]["seconds"])
        if cands:
            cands[0][1].update(name=unprinted[0], guess=None, by_elimination=True)
    return out


def turn_attribution(cluster, roster):
    """(speaker_tag, confidence dict) for a turn of a named cluster record:
    the tag is the name (None when unnamed), far_side marks a far-roster name
    or an unnamed voice the far roster fits better; named_by says how."""
    name = cluster.get("name")
    far = bool((name and roster.get(name) == "far") or (not name and cluster.get("side") == "far"))
    conf = {"cluster": None}
    if cluster.get("sim") is not None:
        conf["sim"] = cluster["sim"]
        conf["margin"] = cluster["margin"]
    if far:
        conf["far_side"] = True
    if name:
        conf["named_by"] = "elimination" if cluster.get("by_elimination") else "prints"
    elif cluster.get("guess"):
        conf["guess"] = cluster["guess"]
        if cluster.get("duplicate_of"):
            conf["duplicate_of"] = cluster["duplicate_of"]
    return name, conf
