"""Unit tests for the pure enrollment-verdict logic (no ECAPA, no WAV)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

# enrollment_check imports numpy/scipy at module load but evaluate_enrollment
# itself is pure; import guarded so the suite skips cleanly if audio deps are
# absent in a minimal CI image.
import pytest  # noqa: E402

try:
    from enrollment_check import (
        evaluate_enrollment,
        MIN_NET_SPEECH_SECONDS,
        MIN_SELF_SIMILARITY,
    )
except Exception as e:  # pragma: no cover
    pytest.skip("enrollment_check deps unavailable: %s" % e, allow_module_level=True)


def test_ok_when_enough_speech_and_self_consistent():
    v = evaluate_enrollment(speech_seconds=MIN_NET_SPEECH_SECONDS + 5,
                            self_sim=0.8, similar_to=[], duration_seconds=30.0)
    assert v["ok"] is True
    assert v["message"] == ""
    assert v["still_needed_seconds"] == 0.0


def test_insufficient_speech_flags_and_computes_deficit():
    v = evaluate_enrollment(speech_seconds=9.0, self_sim=0.9,
                            similar_to=[], duration_seconds=12.0)
    assert v["ok"] is False
    assert v["still_needed_seconds"] == round(MIN_NET_SPEECH_SECONDS - 9.0, 1)
    assert "more are needed" in v["message"]


def test_low_self_similarity_rejects():
    v = evaluate_enrollment(speech_seconds=MIN_NET_SPEECH_SECONDS + 1,
                            self_sim=MIN_SELF_SIMILARITY - 0.1,
                            similar_to=[], duration_seconds=20.0)
    assert v["ok"] is False
    assert "match itself" in v["message"]


def test_similar_voices_do_not_reject():
    # Similar voices are surfaced, never a rejection reason.
    similar = [{"username": "someoneelse", "similarity": 0.71}]
    v = evaluate_enrollment(speech_seconds=MIN_NET_SPEECH_SECONDS + 1,
                            self_sim=0.8, similar_to=similar,
                            duration_seconds=20.0, nearest_sim=0.71)
    assert v["ok"] is True
    assert v["similar_to"] == similar
    assert v["nearest_other_similarity"] == 0.71


def test_self_similarity_unknown_is_not_a_rejection():
    # Too little speech to split-half embed -> self_sim None -> not a reason
    v = evaluate_enrollment(speech_seconds=MIN_NET_SPEECH_SECONDS + 1,
                            self_sim=None, similar_to=[], duration_seconds=18.0)
    assert v["ok"] is True
    assert v["self_similarity"] is None
