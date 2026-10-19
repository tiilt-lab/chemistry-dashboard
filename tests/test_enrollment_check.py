"""Unit tests for the pure enrollment-verdict logic (no ECAPA, no WAV)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

# enrollment_check imports numpy/scipy at module load but evaluate_enrollment
# itself is pure; import guarded so the suite skips cleanly if audio deps are
# absent in a minimal CI image.
import pytest  # noqa: E402

try:
    import numpy as np
    import torch
    from enrollment_check import (
        evaluate_enrollment,
        enroll_take,
        has_print,
        JOIN_MIN_NET_SPEECH_SECONDS,
        MIN_NET_SPEECH_SECONDS,
        MIN_SELF_SIMILARITY,
    )
except Exception as e:  # pragma: no cover
    pytest.skip("enrollment_check deps unavailable: %s" % e, allow_module_level=True)


class _FakeEcapa:
    """encode_batch(x) -> a (1, 1, 8) embedding that depends only on the
    signal's loudness, so two halves of one take match each other."""

    def encode_batch(self, x):
        level = float(x.abs().mean()) if x.numel() else 0.0
        return torch.tensor([[[1.0, level, 0.5, 0.25, 0.0, 0.0, 0.0, 0.0]]])


def _take(speech_seconds, silence_seconds=4.0, sr=16000, seed=1):
    """int16 bytes: ``speech_seconds`` of loud noise then silence. The
    silence must be over a fifth of the take: the speech mask sets its noise
    floor at the 20th percentile of frame loudness, as real talk has pauses."""
    rng = np.random.default_rng(seed)
    talk = rng.uniform(-0.4, 0.4, int(sr * speech_seconds))
    quiet = np.zeros(int(sr * silence_seconds))
    return (np.concatenate([talk, quiet]) * 32767).astype("<i2").tobytes()


def test_join_floor_is_lower_than_the_sign_up_floor():
    assert JOIN_MIN_NET_SPEECH_SECONDS < MIN_NET_SPEECH_SECONDS
    v = evaluate_enrollment(speech_seconds=JOIN_MIN_NET_SPEECH_SECONDS + 1, self_sim=0.9,
                            similar_to=[], duration_seconds=12.0,
                            min_speech_seconds=JOIN_MIN_NET_SPEECH_SECONDS)
    assert v["ok"] is True
    v = evaluate_enrollment(speech_seconds=JOIN_MIN_NET_SPEECH_SECONDS + 1, self_sim=0.9,
                            similar_to=[], duration_seconds=12.0)
    assert v["ok"] is False                                    # the sign-up floor still applies by default


def test_enroll_take_keeps_a_good_join_take_as_the_print_and_never_replaces_one(tmp_path):
    folder = str(tmp_path)
    result = enroll_take("pat3", _take(10.0), 16000, folder, _FakeEcapa())
    assert result["saved"] is True and result["verdict"]["ok"] is True
    assert result["verdict"]["source"] == "join"
    assert has_print(folder, "pat3")
    assert os.path.isfile(os.path.join(folder, "pat3.emb.npy"))
    assert os.path.isfile(os.path.join(folder, "pat3.check.json"))
    assert not os.path.isfile(os.path.join(folder, "pat3.wav"))     # the recording goes, the print stays
    # a second take for the same name (another pod, another day) changes nothing
    before = os.path.getmtime(os.path.join(folder, "pat3.emb.npy"))
    again = enroll_take("pat3", _take(10.0, seed=2), 16000, folder, _FakeEcapa())
    assert again == {"saved": False, "reason": "exists"}
    assert os.path.getmtime(os.path.join(folder, "pat3.emb.npy")) == before


def test_enroll_take_leaves_nothing_behind_when_the_gate_rejects(tmp_path):
    folder = str(tmp_path)
    result = enroll_take("sandy4", _take(3.0), 16000, folder, _FakeEcapa())
    assert result["saved"] is False and result["reason"] == "quality"
    assert result["verdict"]["ok"] is False and "more are needed" in result["verdict"]["message"]
    assert os.listdir(folder) == []
    assert not has_print(folder, "sandy4")


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
