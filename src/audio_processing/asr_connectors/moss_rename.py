"""Rename a pod's stored MOSS turns without transcribing again.

A laptop's diarizer sometimes puts two voices in one cluster (Group 1,
2026-10-16: one laptop's cluster held a Sandy student and a Pat student,
named as one). The partner laptop, hearing the same table, often keeps the
two apart; its clusters then split this laptop's cluster into pieces along
the duplicate copies the merge matched (negotiation_coding.rename_plan).
Each piece is one voice. This module names the pieces the way moss_naming
names clusters, from the student prints (the enrolment print where there
is one, else a session print cut from rows both laptops agree on), with
one name per laptop and elimination for a single printless student on a
side, and hands back a new name and confidence for every row.

Pure functions over numpy audio and an ``embed(signal) -> unit vector``
callable, like moss_naming; ``rename_pod`` is the glue the service calls.
"""
import logging

import numpy as np

from . import moss_naming


def piece_turns(piece, to_rec):
    """The piece's spans as MOSS-style turns in recording seconds."""
    out = []
    for start, end in piece.get("spans") or []:
        s, e = to_rec(float(start)), to_rec(float(end))
        if e > s:
            out.append({"start": s, "end": e, "speaker": piece["id"]})
    return out


def _eliminate(out, roster, prints):
    # moss_naming's last rule once more, now that the hints gave sides to
    # pieces the prints could not place: exactly one printless student on a
    # side takes the largest unnamed piece there that is long enough to be
    # a person.
    for side in ("own", "far"):
        unprinted = [al for al, sd in roster.items() if sd == side and al not in prints]
        if len(unprinted) != 1 or any(v.get("name") == unprinted[0] for v in out.values()):
            continue
        cands = sorted(((c, v) for c, v in out.items()
                        if v["name"] is None and v.get("side") == side and v["seconds"] >= moss_naming.ELIM_MIN_S),
                       key=lambda cv: -cv[1]["seconds"])
        if cands:
            cands[0][1].update(name=unprinted[0], guess=None, by_elimination=True)


def name_pieces(audio, sr, pieces, roster, prints, kinds, to_rec, embed):
    """{piece id: record} with the fields moss_naming.name_clusters gives a
    cluster: name, guess, sim, margin, side, seconds, by_elimination. The
    side comes from the prints, else from the piece's ``side_hint`` (the
    partner laptop's claim on the same voice, or this laptop's earlier
    hearing), which also lets elimination place a printless student."""
    turns = [t for p in pieces for t in piece_turns(p, to_rec)]
    out = moss_naming.name_clusters(audio, sr, turns, roster, prints, kinds, [], lambda t: t, embed)
    for p in pieces:
        rec = out.setdefault(p["id"], dict(name=None, guess=None, sim=None, margin=None, side=None, side_from=None,
                                           seconds=0.0, named_from=0.0, by_elimination=False, live={}))
        if rec.get("name") is None and rec.get("side") is None and p.get("side_hint") in ("own", "far"):
            rec["side"], rec["side_from"] = p["side_hint"], "hint"
    _eliminate(out, roster, prints)
    return out


def rows_from_records(pieces, records, roster, percent=None):
    """[{id, speaker_tag, confidence}] for every row of every piece: the
    piece's name (None when unnamed) and its naming confidence, the piece
    as the cluster, flagged renamed."""
    rows = []
    for p in pieces:
        rec = records.get(p["id"]) or {}
        name, conf = moss_naming.turn_attribution(rec, roster)
        conf["cluster"] = p["id"]
        conf["renamed"] = True
        if p.get("source_cluster"):
            conf["split_from"] = p["source_cluster"]
        if name and conf.get("sim") is not None and percent is not None:
            conf["percent"] = percent(conf["sim"], conf.get("margin") or 0.0)
        for rid in p.get("rows") or []:
            rows.append({"id": int(rid), "speaker_tag": name, "confidence": dict(conf)})
    return rows


def rename_pod(audio, sr, clock, plan, embed, enrolment_print, percent=None):
    """The service's one call: name the plan's pieces on this recording and
    return the rows to post. ``clock`` is the recording's {start_offset,
    moves}; ``enrolment_print(alias)`` the stored print or None."""
    import recording_sidecar
    to_rec = lambda t: recording_sidecar.recording_time(clock, t)      # noqa: E731
    roster = {str(a): "own" for a in plan.get("own_speakers") or []}
    for a in plan.get("partner_speakers") or []:
        roster.setdefault(str(a), "far")
    pieces = plan.get("pieces") or []
    if not roster or not pieces:
        return [], {}
    prints, kinds = {}, {}
    for alias in roster:
        vec = enrolment_print(alias)
        if vec is not None:
            prints[alias], kinds[alias] = vec, "enrolment"
    made = moss_naming.session_prints(audio, sr, to_rec, plan.get("print_rows") or [], embed,
                                      wanted={a for a in roster if a not in prints})
    for alias, (vec, seconds) in made.items():
        prints[alias], kinds[alias] = vec, "session"
    logging.info("MOSS rename: prints %s; no print: %s",
                 {a: (kinds[a] + (" %ss" % made[a][1] if a in made else "")) for a in prints},
                 [a for a in roster if a not in prints])
    records = name_pieces(audio, sr, pieces, roster, prints, kinds, to_rec, embed)
    logging.info("MOSS rename: %d of %d pieces named (%s)", sum(1 for r in records.values() if r.get("name")), len(pieces),
                 ", ".join("%s=%s" % (p["id"], (records[p["id"]].get("name") or ("?" + str(records[p["id"]].get("guess")))))
                           for p in pieces))
    return rows_from_records(pieces, records, roster, percent), records
