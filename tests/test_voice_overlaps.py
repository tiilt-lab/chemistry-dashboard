"""Unit tests for the pure pairwise voice-overlap computation."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

import pytest  # noqa: E402

try:
    from analytics import pairwise_voice_overlaps
except Exception as e:  # pragma: no cover
    pytest.skip("numpy unavailable: %s" % e, allow_module_level=True)


def test_identical_vectors_overlap_at_one():
    emb = {"a": [1.0, 0.0, 0.0], "b": [2.0, 0.0, 0.0]}  # same direction
    pairs = pairwise_voice_overlaps(emb, threshold=0.5)
    assert len(pairs) == 1
    assert pairs[0]["a"] == "a" and pairs[0]["b"] == "b"
    assert pairs[0]["similarity"] == 1.0


def test_orthogonal_vectors_do_not_overlap():
    emb = {"a": [1.0, 0.0], "b": [0.0, 1.0]}
    assert pairwise_voice_overlaps(emb, threshold=0.5) == []


def test_threshold_is_respected_and_sorted():
    emb = {
        "a": [1.0, 0.0, 0.0],
        "b": [0.9, 0.1, 0.0],   # very close to a
        "c": [0.3, 0.95, 0.0],  # farther
    }
    pairs = pairwise_voice_overlaps(emb, threshold=0.5)
    # sorted descending; the a/b pair must lead
    assert pairs[0]["similarity"] >= pairs[-1]["similarity"]
    assert {pairs[0]["a"], pairs[0]["b"]} == {"a", "b"}


def test_single_voice_has_no_pairs():
    assert pairwise_voice_overlaps({"only": [1.0, 2.0]}) == []


def test_mismatched_dims_skip_instead_of_crash():
    # A truncated write / model-version change can leave one embedding a
    # different length. The endpoint loads these straight from disk, so a crash
    # here 500s the whole feature. Comparable pairs must still be returned.
    emb = {"a": [1.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "bad": [1.0, 0.0]}
    pairs = pairwise_voice_overlaps(emb, threshold=0.5)
    assert len(pairs) == 1
    assert {pairs[0]["a"], pairs[0]["b"]} == {"a", "b"}
