"""The renaming pass (src/audio_processing/asr_connectors/moss_rename.py):
the API's pieces named on synthetic audio, as test_moss_naming does for
clusters (a speaker is a constant sample value, the embedder a one-hot)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))
from asr_connectors import moss_rename as R  # noqa: E402

SR = 100
DIM = 8


def onehot(k):
    v = np.zeros(DIM, dtype=np.float32); v[k] = 1.0
    return v


def embed(sig):
    return onehot(int(round(float(np.mean(sig)))))


def audio_of(spans):
    n = int(max(e for _, e, _ in spans) * SR) + SR
    a = np.zeros(n, dtype=np.float32)
    for s, e, k in spans:
        a[int(s * SR):int(e * SR)] = k
    return a


CLOCK = {"start_offset": 0.0, "moves": []}


def test_pieces_are_named_from_the_prints_each_as_one_voice():
    # One stored cluster (S03) held two voices; the partner split it into
    # S03a (voice 1, own student Ann) and S03b (voice 2, far student Bob).
    audio = audio_of([(0, 60, 1), (60, 120, 2), (120, 150, 3)])
    plan = {
        "own_speakers": ["Ann", "Cy"], "partner_speakers": ["Bob"],
        "pieces": [
            {"id": "S03a", "cluster": "S03", "source_cluster": "S03", "partner_cluster": "S03", "rows": [1, 2], "spans": [[0, 30], [30, 60]]},
            {"id": "S03b", "cluster": "S03", "source_cluster": "S03", "partner_cluster": "S04", "rows": [3], "spans": [[60, 120]]},
            {"id": "S05", "cluster": "S05", "source_cluster": None, "partner_cluster": None, "rows": [4], "spans": [[120, 150]]},
        ],
        "print_rows": [],
    }
    prints = {"Ann": onehot(1), "Bob": onehot(2)}
    rows, records = R.rename_pod(audio, SR, CLOCK, plan, embed, lambda a: prints.get(a), percent=lambda s, m: 99)
    by_id = {r["id"]: r for r in rows}
    assert by_id[1]["speaker_tag"] == "Ann" and by_id[2]["speaker_tag"] == "Ann"
    assert by_id[1]["confidence"]["cluster"] == "S03a" and by_id[1]["confidence"]["split_from"] == "S03"
    assert by_id[1]["confidence"]["renamed"] is True and by_id[1]["confidence"]["percent"] == 99
    assert by_id[3]["speaker_tag"] == "Bob" and by_id[3]["confidence"]["far_side"] is True
    # voice 3 matches no print: unnamed, and Cy (the one printless own
    # student) takes it only when it is long enough to be a person (60 s)
    assert by_id[4]["speaker_tag"] is None and by_id[4]["confidence"]["cluster"] == "S05"
    assert records["S03b"]["side"] == "far"


def test_a_long_unnamed_piece_goes_to_the_one_printless_student_on_its_side():
    audio = audio_of([(0, 60, 1), (60, 140, 3)])
    plan = {"own_speakers": ["Ann", "Cy"], "partner_speakers": ["Bob"],
            "pieces": [{"id": "S01", "cluster": "S01", "rows": [1], "spans": [[0, 60]]},
                       {"id": "S02", "cluster": "S02", "rows": [2], "spans": [[60, 140]], "side_hint": "own"}],
            "print_rows": [{"speaker_tag": "Ann", "start_time": 0, "length": 25, "sim": 0.9, "far_side": False}]}
    prints = {"Bob": onehot(2)}
    rows, records = R.rename_pod(audio, SR, CLOCK, plan, embed, lambda a: prints.get(a))
    by_id = {r["id"]: r for r in rows}
    assert by_id[1]["speaker_tag"] == "Ann"            # from the session print cut from print_rows
    assert by_id[2]["speaker_tag"] == "Cy" and by_id[2]["confidence"]["named_by"] == "elimination"


def test_nothing_to_name_without_a_roster_or_pieces():
    audio = audio_of([(0, 10, 1)])
    assert R.rename_pod(audio, SR, CLOCK, {"own_speakers": [], "pieces": []}, embed, lambda a: None) == ([], {})
