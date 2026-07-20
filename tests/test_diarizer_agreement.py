"""Unit tests for the permutation-invariant ASD-vs-diarizer agreement core."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src",
                                "audio_processing", "reattribution"))

try:
    from diarizer_agreement import agreement_score, _turns_frame_labels
except Exception as e:  # pragma: no cover
    pytest.skip("agreement import failed: %s" % e, allow_module_level=True)


def test_identical_partition_scores_one_regardless_of_label_names():
    # same frames, different label STRINGS -> perfect agreement (permutation)
    asd = {f: ("A" if f < 50 else "B") for f in range(100)}
    dia = {f: ("spk1" if f < 50 else "spk0") for f in range(100)}
    r = agreement_score(asd, dia)
    assert r["accuracy"] == 1.0
    assert r["kappa"] == 1.0
    assert r["n_frames"] == 100


def test_random_disagreement_scores_low_kappa():
    asd = {f: ("A" if f % 2 == 0 else "B") for f in range(100)}
    dia = {f: ("X" if f < 50 else "Y") for f in range(100)}  # uncorrelated split
    r = agreement_score(asd, dia)
    assert r["kappa"] <= 0.2  # near chance


def test_partial_overlap_only_scores_shared_frames():
    asd = {f: "A" for f in range(30)}          # frames 0..29
    dia = {f: "z" for f in range(20, 60)}      # frames 20..59
    r = agreement_score(asd, dia)              # shared = 20..29 = 10 frames
    assert r["n_frames"] == 10
    assert r["accuracy"] == 1.0


def test_too_few_shared_frames_returns_none():
    r = agreement_score({1: "A", 2: "A"}, {1: "z"})
    assert r["accuracy"] is None


def test_turns_to_frames_maps_seconds_by_fps():
    # a turn 1.0s..2.0s at 25fps -> frames 25..50
    labels = _turns_frame_labels([(1.0, 2.0, "S0")], fps=25, offset=0, max_frame=100)
    assert labels[25] == "S0" and labels[50] == "S0"
    assert 24 not in labels and 51 not in labels
