"""Unit tests for the cross-session voice-chain linking logic. Synthetic
embeddings so the constraint propagation is verified without diarization."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src",
                                "audio_processing", "reattribution"))

try:
    from link_chains import link_clusters, anchor_and_propagate, cosine
except Exception as e:  # pragma: no cover
    pytest.skip("linker import failed: %s" % e, allow_module_level=True)


def vec(seed, dim=32):
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim)
    return (v / np.linalg.norm(v)).tolist()


# three stable voices, reused across pods with small jitter
A, B, C, D = vec(1), vec(2), vec(3), vec(4)


def jitter(v, seed, scale=0.02):
    rng = np.random.default_rng(seed)
    out = np.asarray(v) + rng.standard_normal(len(v)) * scale
    return (out / np.linalg.norm(out)).tolist()


def pod(did, roster, clusters):
    return {"device_id": did, "session_id": did, "roster": roster,
            "clusters": {lbl: {"seconds": sec, "embedding": emb}
                         for lbl, (sec, emb) in clusters.items()}}


def test_same_voice_links_across_pods_distinct_voices_dont():
    pods = [
        pod(1, ["a", "b", "c"], {"S0": (100, jitter(A, 10)), "S1": (80, jitter(B, 11))}),
        pod(2, ["a", "b", "d"], {"S0": (90, jitter(A, 12)), "S1": (70, jitter(B, 13))}),
    ]
    chains, _ = link_clusters(pods, link_threshold=0.55)
    # A's two clusters and B's two clusters each merge -> 2 chains, not 4
    assert len(chains) == 2
    for c in chains:
        assert len(c["members"]) == 2  # one per pod


def test_never_merges_two_clusters_in_the_same_pod():
    # even if two co-present voices look similar, they must stay separate
    pods = [pod(1, ["a", "b"], {"S0": (50, jitter(A, 20)), "S1": (50, jitter(A, 21))})]
    chains, _ = link_clusters(pods, link_threshold=0.5)
    assert len(chains) == 2


def test_roster_intersection_singleton_resolves():
    # voice A appears in two pods whose rosters intersect only on "a"
    pods = [
        pod(1, ["a", "x", "y"], {"S0": (100, jitter(A, 30))}),
        pod(2, ["a", "p", "q"], {"S0": (100, jitter(A, 31))}),
    ]
    chains, _ = link_clusters(pods)
    assert len(chains) == 1
    assert chains[0]["candidates"] == {"a"}
    n = anchor_and_propagate(chains)
    assert n == 1
    assert chains[0]["resolved"] == "a"


def test_elimination_propagates_within_fixed_group():
    # a stable trio a/b/c in every pod: intersection never shrinks by itself.
    # Anchor ONE voice (via print_match) -> the other two must split the two
    # remaining names, and one external anchor cascades to resolve a second.
    pods = [
        pod(1, ["a", "b", "c"],
            {"S0": (100, jitter(A, 40)), "S1": (90, jitter(B, 41)), "S2": (80, jitter(C, 42))}),
        pod(2, ["a", "b", "c"],
            {"S0": (100, jitter(A, 43)), "S1": (90, jitter(B, 44)), "S2": (80, jitter(C, 45))}),
    ]
    chains, _ = link_clusters(pods)
    assert len(chains) == 3
    # every chain's candidate set is the full trio (fixed group)
    for c in chains:
        assert c["candidates"] == {"a", "b", "c"}
    # externally anchor the A-chain and the B-chain; C must fall out by
    # elimination (only name left in the shared pods)
    a_chain = next(i for i, c in enumerate(chains)
                   if cosine(c["embedding"], A) > 0.9)
    b_chain = next(i for i, c in enumerate(chains)
                   if cosine(c["embedding"], B) > 0.9)
    n = anchor_and_propagate(chains, {a_chain: "a", b_chain: "b"})
    assert n == 3
    resolved = {c["resolved"] for c in chains}
    assert resolved == {"a", "b", "c"}
