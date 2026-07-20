"""Stage 2 of cross-session linking: build a voice profile per student.

Consumes the per-pod cluster artifacts from build_pod_clusters.py and links
clusters across sessions into per-student "voice chains", using the constraint
that a recurring voice must belong to someone in EVERY pod it appears in.

The algorithm (sudoku-style constraint propagation):

  1. Link clusters across pods by embedding similarity -> chains. Each chain
     is one recurring voice; its candidate identities are the intersection of
     the rosters of the pods it touches.
  2. Anchor chains whose candidate set is a singleton (roster alone resolved
     them), or that match a usable enrolled print, or (later) a video ASD id.
  3. Propagate: an anchored identity is removed from OTHER chains' candidate
     sets within a shared pod (two voices in one pod can't be the same
     person). Repeat until no new singletons appear.
  4. Emit: resolved chains (-> a voice profile), and the residue that needs
     exactly one human ear-tag each.

The linking/anchoring logic is pure and unit-tested; I/O lives in main().
"""
import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np


def cosine(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))


def link_clusters(pods, link_threshold=0.55):
    """Greedy agglomerative linking of clusters ACROSS pods into chains.

    pods: [{device_id, roster:[..], clusters:{label:{seconds, embedding}}}]
    Returns chains: [{members:[(device_id,label)], embedding, candidates:set}]

    Two clusters never link if they're in the same pod (distinct diarized
    voices) — that's what keeps a chain from collapsing two co-present people.
    """
    nodes = []
    for p in pods:
        for label, c in p["clusters"].items():
            nodes.append({"pod": p["device_id"], "label": label,
                          "emb": np.asarray(c["embedding"], dtype=float),
                          "seconds": c.get("seconds", 0.0),
                          "roster": set(p["roster"])})
    # each chain: list of node indices; track pods used to forbid same-pod merge
    chains = [{"idx": [i], "pods": {n["pod"]}, "emb": n["emb"].copy()}
              for i, n in enumerate(nodes)]

    def chain_sim(c1, c2):
        return cosine(c1["emb"], c2["emb"])

    merged = True
    while merged:
        merged = False
        best = None
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                if chains[i]["pods"] & chains[j]["pods"]:
                    continue  # can't merge two voices sharing a pod
                sim = chain_sim(chains[i], chains[j])
                if sim >= link_threshold and (best is None or sim > best[2]):
                    best = (i, j, sim)
        if best:
            i, j, _ = best
            ci, cj = chains[i], chains[j]
            wi = sum(nodes[k]["seconds"] for k in ci["idx"]) or 1
            wj = sum(nodes[k]["seconds"] for k in cj["idx"]) or 1
            ci["emb"] = (ci["emb"] * wi + cj["emb"] * wj) / (wi + wj)
            ci["idx"] += cj["idx"]
            ci["pods"] |= cj["pods"]
            chains.pop(j)
            merged = True

    out = []
    for c in chains:
        members = [(nodes[k]["pod"], nodes[k]["label"]) for k in c["idx"]]
        cand = set.intersection(*[nodes[k]["roster"] for k in c["idx"]])
        out.append({"members": members, "pods": sorted(c["pods"]),
                    "embedding": c["emb"], "candidates": set(cand),
                    "seconds": sum(nodes[k]["seconds"] for k in c["idx"])})
    return out, nodes


def anchor_and_propagate(chains, print_match=None):
    """Resolve chains to identities by constraint propagation.

    print_match: optional {chain_index: alias} of externally-anchored chains
    (enrolled-print or video-ASD matches). Mutates chains, adding 'resolved'.
    Returns the number of chains resolved.
    """
    for c in chains:
        c["resolved"] = None
    # seed with external anchors
    if print_match:
        for i, alias in print_match.items():
            if alias in chains[i]["candidates"]:
                chains[i]["resolved"] = alias

    # pod -> chains touching it (two chains sharing a pod are distinct people)
    pod_chains = defaultdict(list)
    for i, c in enumerate(chains):
        for pod in c["pods"]:
            pod_chains[pod].append(i)

    changed = True
    while changed:
        changed = False
        # singleton candidate -> resolve
        for c in chains:
            if c["resolved"] is None and len(c["candidates"]) == 1:
                c["resolved"] = next(iter(c["candidates"]))
                changed = True
        # a resolved identity is removed from co-pod chains' candidate sets
        for pod, idxs in pod_chains.items():
            taken = {chains[i]["resolved"] for i in idxs
                     if chains[i]["resolved"]}
            for i in idxs:
                c = chains[i]
                if c["resolved"] is None and c["candidates"] & taken:
                    c["candidates"] -= taken
                    changed = True
    return sum(1 for c in chains if c["resolved"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters-dir", required=True)
    ap.add_argument("--print-threshold", type=float, default=0.45,
                    help="min cosine to anchor a chain to an enrolled print")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pods = [json.load(open(p)) for p in
            sorted(glob.glob(os.path.join(args.clusters_dir, "pod_*.json")))]
    print("pods: %d" % len(pods))

    chains, nodes = link_clusters(pods)
    print("linked %d clusters into %d chains" %
          (sum(len(p["clusters"]) for p in pods), len(chains)))

    # external anchors from usable enrolled prints
    prints = {}
    for p in pods:
        for alias, emb in p.get("enrolled_prints", {}).items():
            prints.setdefault(alias, []).append(np.asarray(emb, dtype=float))
    prints = {a: np.mean(v, axis=0) for a, v in prints.items()}
    print_match = {}
    for i, c in enumerate(chains):
        best = (None, 0.0)
        for alias in c["candidates"]:
            if alias in prints:
                sim = cosine(c["embedding"], prints[alias])
                if sim > best[1]:
                    best = (alias, sim)
        if best[0] and best[1] >= args.print_threshold:
            print_match[i] = best[0]

    resolved = anchor_and_propagate(chains, print_match)
    print("resolved %d/%d chains" % (resolved, len(chains)))

    profiles, residue = {}, []
    for c in chains:
        entry = {"pods": c["pods"], "seconds": round(c["seconds"], 1),
                 "members": c["members"], "candidates": sorted(c["candidates"])}
        if c["resolved"]:
            profiles.setdefault(c["resolved"], []).append(entry)
        else:
            residue.append(entry)

    result = {
        "n_pods": len(pods), "n_chains": len(chains), "n_resolved": resolved,
        "profiles": {a: {"sessions": len(v),
                         "total_seconds": round(sum(e["seconds"] for e in v), 1),
                         "chains": v} for a, v in profiles.items()},
        "needs_ear_tag": residue,
    }
    os.makedirs(args.out, exist_ok=True)
    json.dump(result, open(os.path.join(args.out, "chains.json"), "w"), indent=2)
    print("\nresolved voice profiles:")
    for a, v in result["profiles"].items():
        print("  %-14s %d sessions, %.0fs of speech" %
              (a, v["sessions"], v["total_seconds"]))
    print("chains still needing one ear-tag: %d" % len(residue))
    for r in residue:
        print("  candidates=%s across pods %s (%.0fs)" %
              (r["candidates"], r["pods"], r["seconds"]))


if __name__ == "__main__":
    main()
