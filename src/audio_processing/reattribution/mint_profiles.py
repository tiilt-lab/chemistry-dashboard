"""Mint voice-print v2 from named cross-session chains — "self-enrollment"
from the retained recordings, no student access required.

A resolved chain's merged ECAPA embedding is already the weighted average of
that person's voice across ALL their sessions (up to ~60s each), so it IS a
strong voice print — far richer than the original 6-second enrollment. This
writes one <alias>.emb.npy per resolved person into a STAGING dir (production
audiobiometrics is never touched here), with provenance and an old-vs-new
comparison so each can be reviewed before promotion.

Anchors come from: roster-intersection singletons + enrolled-print matches
(automatic), plus an optional --ear-tags JSON of human confirmations
({"cluster_signature": "alias"} or {"pod:label": "alias"}). Promotion into
production is a separate, deliberate step (see --emit-promote-script).

Usage:
  ../venv-unified/bin/python3 reattribution/mint_profiles.py \
      --clusters-dir <dir> --out <staging_dir> [--ear-tags tags.json]
"""
import argparse
import glob
import json
import os

import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_chains import (link_clusters, anchor_and_propagate, cosine,
                         consolidate_within_pod)  # noqa: E402

BIOMETRICS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audiobiometrics")


def load_old_print(alias):
    p = os.path.join(BIOMETRICS, alias + ".emb.npy")
    if os.path.isfile(p):
        try:
            return np.load(p).astype(float)
        except Exception:
            return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ear-tags", default=None,
                    help='JSON of human anchors: {"pod:label": "alias"} and/or '
                         '{"cand,cand,cand": "alias"} keyed by sorted candidates')
    ap.add_argument("--print-threshold", type=float, default=0.30)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    pods = [json.load(open(p)) for p in
            sorted(glob.glob(os.path.join(args.clusters_dir, "pod_*.json")))]
    chains, _nodes = link_clusters(pods)

    # print anchors (automatic)
    prints = {}
    for p in pods:
        for alias, emb in p.get("enrolled_prints", {}).items():
            prints.setdefault(alias, []).append(np.asarray(emb, float))
    prints = {a: np.mean(v, 0) for a, v in prints.items()}
    print_match = {}
    for i, c in enumerate(chains):
        best = (None, 0.0)
        for alias in c["candidates"]:
            if alias in prints:
                s = cosine(c["embedding"], prints[alias])
                if s > best[1]:
                    best = (alias, s)
        if best[0] and best[1] >= args.print_threshold:
            print_match[i] = best[0]

    # human ear-tags (override/extend)
    tag_source = {}
    if args.ear_tags:
        tags = json.load(open(args.ear_tags))
        for i, c in enumerate(chains):
            member_keys = {"%d:%s" % (pod, lbl) for pod, lbl in c["members"]}
            sig = ",".join(sorted(c["candidates"]))
            hit = next((tags[k] for k in member_keys if k in tags), None) or tags.get(sig)
            if hit:
                print_match[i] = hit
                tag_source[i] = "ear_tag"

    resolved = anchor_and_propagate(chains, print_match)

    # Two chains can resolve to the same person (over-segmentation the
    # same-pod constraint couldn't merge). Combine them into ONE profile,
    # weighted by speech seconds, instead of letting the shorter clobber the
    # longer on write.
    by_alias = {}
    for i, c in enumerate(chains):
        if not c["resolved"]:
            continue
        a = c["resolved"]
        anchor = ("ear_tag" if tag_source.get(i)
                  else "print" if i in print_match
                  else "roster/elimination")
        by_alias.setdefault(a, []).append((c, anchor))

    manifest = []
    for alias, entries in by_alias.items():
        w = np.array([max(c["seconds"], 1e-6) for c, _ in entries])
        embs = np.stack([np.asarray(c["embedding"], float) for c, _ in entries])
        emb = (embs * w[:, None]).sum(0) / w.sum()
        emb = emb / (np.linalg.norm(emb) + 1e-9)
        np.save(os.path.join(args.out, alias + ".emb.npy"), emb.astype(np.float32))
        old = load_old_print(alias)
        pods_all = sorted({p for c, _ in entries for p in c["pods"]})
        # strongest anchor wins for the label; ear_tag > roster > print
        rank = {"ear_tag": 0, "roster/elimination": 1, "print": 2}
        anchor = sorted((a for _, a in entries), key=lambda x: rank.get(x, 3))[0]
        manifest.append({
            "alias": alias,
            "sessions": len(pods_all),
            "seconds": round(sum(c["seconds"] for c, _ in entries), 1),
            "chains_merged": len(entries),
            "anchor": anchor,
            "vs_old_print_cosine": (round(cosine(emb, old), 3)
                                    if old is not None else None),
            "had_old_print": old is not None,
        })
    minted = len(manifest)

    manifest.sort(key=lambda m: -m["seconds"])
    json.dump({"minted": minted, "unresolved_chains": len(chains) - resolved,
               "profiles": manifest},
              open(os.path.join(args.out, "manifest.json"), "w"), indent=2)

    print("minted %d voice profiles into %s (staging — production untouched)"
          % (minted, args.out))
    print("%-14s %-8s %-9s %-18s %s" %
          ("alias", "sessions", "seconds", "anchor", "cos vs old print"))
    for m in manifest:
        print("%-14s %-8d %-9.0f %-18s %s" %
              (m["alias"], m["sessions"], m["seconds"], m["anchor"],
               m["vs_old_print_cosine"] if m["had_old_print"] else "(no old print)"))
    print("\nreview these, then promote approved ones into audiobiometrics/.")


if __name__ == "__main__":
    main()
