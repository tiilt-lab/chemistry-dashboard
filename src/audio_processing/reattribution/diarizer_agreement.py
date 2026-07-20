"""Rank audio diarizers by agreement with video ASD.

Video active-speaker detection is an INDEPENDENT modality (mouth motion +
face), so it's the best available proxy for ground truth of "who is talking
when". This scores any audio diarizer's turns against an ASD artifact,
permutation-invariantly (Hungarian label matching), so no identity/roster
mapping is needed — we measure whether the two induce the same speaker
PARTITION of the timeline.

Metrics on the frames where both sides are confident:
  * accuracy   — best-permutation frame agreement (1.0 = identical partition)
  * kappa      — Cohen's kappa (chance-corrected)
  * n_frames   — support

The core (agreement_score) is pure and unit-tested; drivers run a specific
diarizer and call it.
"""
import argparse
import json
import os

import numpy as np


def _asd_frame_labels(asd, floor=0.10, lead=1.5):
    """Per-frame talking speaker from ASD (argmax over co-present faces).
    Uses track identity if present, else the track index, so it works even
    with an empty gallery (we only need a consistent per-voice label)."""
    from collections import defaultdict
    probs = defaultdict(dict)
    for i, tr in enumerate(asd["tracks"]):
        who = tr.get("identity") or ("track%d" % i)
        for f, s in zip(tr["frames"], tr["scores"]):
            probs[f][who] = max(probs[f].get(who, 0.0), float(s))
    labels = {}
    for f, d in probs.items():
        r = sorted(d.items(), key=lambda kv: -kv[1])
        if r[0][1] < floor:
            continue
        if len(r) > 1 and r[0][1] < lead * max(r[1][1], 1e-6):
            continue
        labels[f] = r[0][0]
    return labels


def _turns_frame_labels(turns, fps, offset, max_frame):
    """Per-frame cluster label from diarizer turns (session-relative seconds).
    offset = session seconds at which the video/frames start."""
    labels = {}
    for start, end, spk in turns:
        a = int(round((start) * fps))
        b = int(round((end) * fps))
        for f in range(max(0, a), min(b, max_frame) + 1):
            labels[f] = spk
    return labels


def agreement_score(asd_labels, dia_labels):
    """Permutation-invariant agreement between two per-frame labelings on
    their shared confident frames. Returns dict(accuracy, kappa, n_frames)."""
    from scipy.optimize import linear_sum_assignment
    shared = sorted(set(asd_labels) & set(dia_labels))
    if len(shared) < 10:
        return {"accuracy": None, "kappa": None, "n_frames": len(shared)}
    a = [asd_labels[f] for f in shared]
    d = [dia_labels[f] for f in shared]
    au = {v: i for i, v in enumerate(sorted(set(a)))}
    du = {v: i for i, v in enumerate(sorted(set(d)))}
    M = np.zeros((len(au), len(du)), dtype=int)
    for x, y in zip(a, d):
        M[au[x], du[y]] += 1
    # best label permutation = max trace of the confusion matrix
    ri, ci = linear_sum_assignment(-M)
    correct = M[ri, ci].sum()
    n = len(shared)
    acc = correct / n
    # Cohen's kappa on the permuted labels
    inv = {ci[k]: ri[k] for k in range(len(ci))}
    d_mapped = [inv.get(du[y], -1) for y in d]
    a_idx = [au[x] for x in a]
    po = acc
    from collections import Counter
    ca, cd = Counter(a_idx), Counter(d_mapped)
    pe = sum((ca.get(k, 0) / n) * (cd.get(k, 0) / n) for k in set(a_idx) | set(d_mapped))
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    return {"accuracy": round(float(acc), 3), "kappa": round(float(kappa), 3),
            "n_frames": n}


def score_against_asd(asd_path, turns, fps, offset):
    asd = json.load(open(asd_path))
    fps = asd.get("fps", fps)
    max_frame = max((f for tr in asd["tracks"] for f in tr["frames"]), default=0)
    al = _asd_frame_labels(asd)
    dl = _turns_frame_labels(turns, fps, offset, max_frame)
    return agreement_score(al, dl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asd", required=True)
    ap.add_argument("--turns", required=True, help="JSON: {turns:[[start,end,spk],...]}")
    ap.add_argument("--offset", type=int, required=True)
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--label", default="diarizer")
    args = ap.parse_args()
    turns = json.load(open(args.turns))["turns"]
    r = score_against_asd(args.asd, turns, args.fps, args.offset)
    print("%s vs ASD: accuracy=%s kappa=%s (n=%d frames)" %
          (args.label, r["accuracy"], r["kappa"], r["n_frames"]))


if __name__ == "__main__":
    main()
