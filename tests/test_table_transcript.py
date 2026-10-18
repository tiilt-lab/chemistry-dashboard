"""The table view's data (src/server/negotiation_coding.py, tables section):
which laptops of a breakout group carry the merged transcript, the session's
tables in order, and the merged lines in the transcript panel's shape."""
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "server"))
sys.path.insert(0, os.path.join(ROOT, "src", "common"))
sys.modules.setdefault('posthoc_state', types.SimpleNamespace(is_running=lambda d: False))

import negotiation_coding as nc  # noqa: E402  (import-light: no Flask, no DB)

NAMES = ("Pat", "Sandy")


def _device(id, name, group="Group 7", side=None):
    return types.SimpleNamespace(id=id, name=name, negotiation_group=group, negotiation_side=side, session_id=434)


def _row(id, device, start, text, speaker=None, length=4):
    return types.SimpleNamespace(id=id, session_device_id=device, start_time=start, length=length,
                                 speaker_tag=speaker, transcript=text)


def test_primaries_are_each_sides_lowest_id_laptop_with_transcripts():
    devices = [_device(3, "Sandy laptop", side="Sandy"), _device(1, "Pat laptop", side="Pat"),
               _device(2, "Pat laptop 2", side="Pat"), _device(4, "Empty Sandy", side="Sandy")]
    counts = {1: 0, 2: 120, 3: 80, 4: 0}
    pods = nc.table_pods(devices, NAMES, lambda d: counts[d])
    assert [p["id"] for p in pods] == [1, 2, 3, 4]          # side order, then id
    assert [p["primary"] for p in pods] == [False, True, True, False]
    assert pods[1]["transcripts"] == 120 and pods[0]["side"] == "Pat"


def test_an_extra_laptop_on_a_side_is_a_media_source_only():
    devices = [_device(1, "Pat", side="Pat"), _device(2, "Pat 2", side="Pat"), _device(3, "Sandy", side="Sandy")]
    pods = nc.table_pods(devices, NAMES)
    assert [(p["id"], p["primary"]) for p in pods] == [(1, True), (2, False), (3, True)]


def test_session_tables_sort_naturally_and_skip_ungrouped_laptops():
    devices = [_device(1, "a", "Group 10", "Pat"), _device(2, "b", "Group 2", "Sandy"),
               _device(3, "hallway", None, None), _device(4, "c", "Group 2", "Pat")]
    tables = nc.session_tables(devices, NAMES)
    assert [t["group"] for t in tables] == ["Group 2", "Group 10"]
    assert [p["id"] for p in tables[0]["pods"]] == [4, 2]


def test_table_transcript_merges_both_laptops_into_one_conversation():
    pat, sandy = _device(1, "Pat laptop", side="Pat"), _device(2, "Sandy laptop", side="Sandy")
    rows = {
        1: [_row(11, 1, 100.0, "We hold four hundred thousand dollars of your debt.", "Pat1G7"),
            _row(12, 1, 105.0, "So what are you thinking?", "Pat1G7"),
            _row(13, 1, 112.0, "the market is really bad right now", None)],   # Sandy's side, heard faintly
        2: [_row(21, 2, 100.2, "We hold four hundred thousand dollars of your debt.", None),  # Pat, heard across the table
            _row(22, 2, 112.0, "The market is really bad right now.", "Jing"),
            _row(23, 2, 116.0, "If we can get through this hardship together.", "Jing")],
    }
    out = nc.table_transcript([pat, sandy], rows, NAMES)
    lines = out["lines"]
    texts = [(l["session_device_id"], l["speaker_tag"], l["transcript"]) for l in lines]
    # Pat's own laptop keeps Pat's line; Sandy's copy of it is folded in.
    assert texts[0][0] == 1 and texts[0][1] == "Pat1G7" and "debt" in texts[0][2]
    assert 21 in lines[0]["merged_from"] or 21 in lines[0]["stitched_from"] or \
        any(d["transcript_id"] == 21 for d in out["dropped"])
    # Jing's two pieces on Sandy's laptop become one turn; Pat's faint hearing of it is gone.
    jing = [l for l in lines if l["speaker_tag"] == "Jing"]
    assert len(jing) == 1 and 23 in jing[0]["stitched_from"] and jing[0]["session_device_id"] == 2
    assert not any(l["id"] == 13 for l in lines)
    # Panel field names and team stamps.
    for l in lines:
        assert {"id", "start_time", "length", "transcript", "speaker_tag", "team", "session_device_id"} <= set(l)
    assert lines[0]["team"] == "Pat" and jing[0]["team"] == "Sandy"
    assert out["alignment"] is None or isinstance(out["alignment"], dict)
