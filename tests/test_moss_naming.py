"""The MOSS naming rules (src/audio_processing/asr_connectors/moss_naming.py),
ported from the bake-off's name_turns.py, on synthetic audio: a speaker is a
constant sample value and the embedder a one-hot of it."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))
from asr_connectors import moss_naming as M  # noqa: E402

SR = 100          # samples per second: small audio, exact cuts
DIM = 8


def onehot(k, w=1.0):
    v = np.zeros(DIM, dtype=np.float32); v[k] = w
    return v


def embed(sig):
    k = int(round(float(np.mean(sig))))
    return onehot(k)


def audio_of(spans):
    """spans: [(start_s, end_s, speaker k)] -> float32 audio where each span holds its speaker's value."""
    n = int(max(e for _, e, _ in spans) * SR) + SR
    a = np.zeros(n, dtype=np.float32)
    for s, e, k in spans:
        a[int(s * SR):int(e * SR)] = k
    return a


ident = lambda t: t   # the recording starts at session second 0


def test_session_prints_need_confident_own_side_rows_inside_the_recording():
    audio = audio_of([(0, 100, 1), (100, 200, 2)])
    rows = [
        {"speaker_tag": "Ann", "start_time": 0, "length": 12, "sim": 0.9, "far_side": False},
        {"speaker_tag": "Ann", "start_time": 20, "length": 10, "sim": 0.7, "far_side": False},
        {"speaker_tag": "Ann", "start_time": 40, "length": 30, "sim": 0.5, "far_side": False},     # not sure enough
        {"speaker_tag": "Ann", "start_time": 50, "length": 1.5, "sim": 0.95, "far_side": False},   # too short
        {"speaker_tag": "Bob", "start_time": 100, "length": 30, "sim": 0.9, "far_side": True},     # heard across the table
        {"speaker_tag": "Cy", "start_time": 150, "length": 15, "sim": 0.9, "far_side": False},     # 15 s < 20 s
        {"speaker_tag": "Dee", "start_time": 500, "length": 40, "sim": 0.9, "far_side": False},    # outside this recording
    ]
    prints = M.session_prints(audio, SR, ident, rows, embed, wanted={"Ann", "Bob", "Cy", "Dee"})
    assert set(prints) == {"Ann"}
    vec, seconds = prints["Ann"]
    assert seconds == 22.0 and np.argmax(vec) == 1


def test_clusters_are_named_by_the_best_print_with_sides_and_far_side_flags():
    audio = audio_of([(0, 50, 1), (50, 100, 2), (100, 130, 3)])
    turns = [{"start": 0, "end": 50, "speaker": "S01"}, {"start": 50, "end": 100, "speaker": "S02"},
             {"start": 100, "end": 130, "speaker": "S03"}, {"start": 130, "end": 130.5, "speaker": "S04"}]
    roster = {"Ann": "own", "Bob": "far", "Cy": "far"}
    prints = {"Ann": onehot(1), "Bob": onehot(2)}
    kinds = {"Ann": "session", "Bob": "enrolment"}
    out = M.name_clusters(audio, SR, turns, roster, prints, kinds, [], ident, embed)
    assert out["S01"]["name"] == "Ann" and out["S01"]["side"] == "own"
    assert out["S02"]["name"] == "Bob" and out["S02"]["side"] == "far"
    assert out["S03"]["name"] is None and out["S03"]["guess"] in ("Ann", "Bob")
    assert out["S04"]["name"] is None and out["S04"]["named_from"] == 0.0     # under a second of voice
    assert M.turn_attribution(out["S01"], roster) == ("Ann", {"cluster": None, "sim": 1.0, "margin": 1.0, "named_by": "prints"})
    name, conf = M.turn_attribution(out["S02"], roster)
    assert name == "Bob" and conf["far_side"] is True


def test_each_print_kind_has_its_own_floor_and_the_margin_applies():
    audio = audio_of([(0, 50, 1), (50, 100, 2)])
    turns = [{"start": 0, "end": 50, "speaker": "S01"}, {"start": 50, "end": 100, "speaker": "S02"}]
    # Ann's enrolment print sits at 0.5 on her voice: above the 0.35 enrolment floor.
    # Bob's session print sits at 0.5 on his: below the 0.60 session floor, so a guess.
    prints = {"Ann": M.unit(onehot(1, 0.5) + onehot(6, 0.866)), "Bob": M.unit(onehot(2, 0.5) + onehot(7, 0.866))}
    kinds = {"Ann": "enrolment", "Bob": "session"}
    roster = {"Ann": "own", "Bob": "own"}
    out = M.name_clusters(audio, SR, turns, roster, prints, kinds, [], ident, embed)
    assert out["S01"]["name"] == "Ann"
    assert out["S02"]["name"] is None and out["S02"]["guess"] == "Bob"
    # Two prints within the margin of each other: nobody is named.
    prints = {"Ann": M.unit(onehot(1, 0.9) + onehot(6, 0.436)), "Al": M.unit(onehot(1, 0.88) + onehot(7, 0.475))}
    out = M.name_clusters(audio, SR, turns[:1], {"Ann": "own", "Al": "own"}, prints, {"Ann": "session", "Al": "session"}, [], ident, embed)
    assert out["S01"]["name"] is None and out["S01"]["margin"] < M.MARGIN


def test_the_live_rows_decide_the_side_across_print_kinds_and_veto_a_weak_name():
    audio = audio_of([(0, 80, 1)])
    turns = [{"start": 0, "end": 80, "speaker": "S01"}]
    # Bob's enrolment print (far side) matches at 0.45; Ann's session print (own) at 0.38:
    # prints of different kinds, so the live rows decide the side. They say own,
    # and a far-side enrolment name against the live side is a guess.
    prints = {"Bob": M.unit(onehot(1, 0.45) + onehot(6, 0.893)), "Ann": M.unit(onehot(1, 0.38) + onehot(7, 0.925))}
    kinds = {"Bob": "enrolment", "Ann": "session"}
    roster = {"Ann": "own", "Bob": "far"}
    live_own = [{"start_time": 0, "length": 60, "speaker_tag": "Ann", "far_side": False},
                {"start_time": 60, "length": 10, "speaker_tag": "Bob", "far_side": True}]
    out = M.name_clusters(audio, SR, turns, roster, prints, kinds, live_own, ident, embed)
    assert out["S01"]["side"] == "own" and out["S01"]["side_from"] == "live"
    assert out["S01"]["name"] is None and out["S01"]["guess"] == "Bob"
    assert out["S01"]["live"] == {"own": 0.86, "far": 0.14, "unnamed": 0.0}


def test_elimination_gives_the_one_unprinted_student_the_largest_unnamed_cluster_on_their_side():
    audio = audio_of([(0, 50, 1), (50, 140, 3), (140, 170, 4)])
    turns = [{"start": 0, "end": 50, "speaker": "S01"}, {"start": 50, "end": 140, "speaker": "S03"},
             {"start": 140, "end": 170, "speaker": "S04"}]
    roster = {"Ann": "own", "Cy": "own", "Bob": "far"}
    prints = {"Ann": onehot(1), "Bob": onehot(2)}
    kinds = {"Ann": "session", "Bob": "enrolment"}
    live_own = [{"start_time": 50, "length": 90, "speaker_tag": "Ann", "far_side": False}]   # the live service heard own-side voice there
    out = M.name_clusters(audio, SR, turns, roster, prints, kinds, live_own, ident, embed)
    assert out["S03"]["name"] == "Cy" and out["S03"]["by_elimination"] is True
    assert out["S04"]["name"] is None                      # 30 s, and the side is unknown
    name, conf = M.turn_attribution(out["S03"], roster)
    assert name == "Cy" and conf["named_by"] == "elimination"


def test_one_name_per_laptop_the_closest_cluster_keeps_it():
    # Two clusters match Ann's print, which happens when a session print was
    # cut from live rows that named another voice Ann: only the closest
    # (here, on a tie, the longer) keeps the name, the other carries it as a
    # guess that the merge can overrule with the other laptop's name.
    audio = audio_of([(0, 60, 1), (60, 90, 1), (90, 130, 2)])
    turns = [{"start": 0, "end": 60, "speaker": "S01"}, {"start": 60, "end": 90, "speaker": "S02"},
             {"start": 90, "end": 130, "speaker": "S03"}]
    roster = {"Ann": "own", "Bob": "far"}
    prints = {"Ann": onehot(1), "Bob": onehot(2)}
    kinds = {"Ann": "session", "Bob": "enrolment"}
    out = M.name_clusters(audio, SR, turns, roster, prints, kinds, [], ident, embed)
    assert out["S01"]["name"] == "Ann"
    assert out["S02"]["name"] is None and out["S02"]["guess"] == "Ann" and out["S02"]["duplicate_of"] == "S01"
    assert out["S03"]["name"] == "Bob"
    name, conf = M.turn_attribution(out["S02"], roster)
    assert name is None and conf["guess"] == "Ann" and conf["duplicate_of"] == "S01"


def test_a_turn_stamped_before_the_recording_starts_is_cut_at_its_first_sample():
    # The renaming pass maps stored stamps back onto the recording; a stamp
    # rounded below the recording's start handed the embedder an empty slice
    # (Group 7, 2026-10-19: "Padding size should be less than the
    # corresponding input dimension"). The in-range part names the cluster;
    # a turn wholly outside the recording carries no voice.
    audio = audio_of([(0, 50, 1), (50, 90, 2), (90, 100, 3)])
    turns = [{"start": -0.131, "end": 1.4, "speaker": "S01"}, {"start": -5, "end": -2, "speaker": "S02"},
             {"start": 60, "end": 85, "speaker": "S03"}, {"start": 92, "end": 130, "speaker": "S04"}]
    roster = {"Ann": "own", "Bob": "own"}
    prints = {"Ann": onehot(1), "Bob": onehot(2)}
    kinds = {"Ann": "enrolment", "Bob": "enrolment"}
    out = M.name_clusters(audio, SR, turns, roster, prints, kinds, [], ident, embed)
    assert out["S01"]["name"] == "Ann" and out["S01"]["named_from"] == 1.4
    assert out["S02"]["name"] is None and out["S02"]["named_from"] == 0.0
    assert out["S03"]["name"] == "Bob"
    assert out["S04"]["name"] is None and out["S04"]["named_from"] == 9.0   # the recording ends at 101 s
    rows = [{"speaker_tag": "Ann", "start_time": -3, "length": 30, "sim": 0.9, "far_side": False}]
    vec, seconds = M.session_prints(audio, SR, ident, rows, embed, wanted={"Ann"})["Ann"]
    assert seconds == 27.0 and np.argmax(vec) == 1
