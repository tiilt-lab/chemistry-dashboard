"""The group view's data (src/server/negotiation_coding.py, groups section):
which laptops of a breakout group carry the merged transcript, the session's
groups in order, and the merged lines in the transcript panel's shape."""
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


def _row(id, device, start, text, speaker=None, length=4, question=False):
    return types.SimpleNamespace(id=id, session_device_id=device, start_time=start, length=length,
                                 speaker_tag=speaker, transcript=text, question=question)


def test_primaries_are_each_sides_lowest_id_laptop_with_transcripts():
    devices = [_device(3, "Sandy laptop", side="Sandy"), _device(1, "Pat laptop", side="Pat"),
               _device(2, "Pat laptop 2", side="Pat"), _device(4, "Empty Sandy", side="Sandy")]
    counts = {1: 0, 2: 120, 3: 80, 4: 0}
    pods = nc.group_pods(devices, NAMES, lambda d: counts[d])
    assert [p["id"] for p in pods] == [1, 2, 3, 4]          # side order, then id
    assert [p["primary"] for p in pods] == [False, True, True, False]
    assert pods[1]["transcripts"] == 120 and pods[0]["side"] == "Pat"


def test_an_extra_laptop_on_a_side_is_a_view_only():
    devices = [_device(1, "Pat", side="Pat"), _device(2, "Pat 2", side="Pat"), _device(3, "Sandy", side="Sandy")]
    pods = nc.group_pods(devices, NAMES)
    assert [(p["id"], p["primary"]) for p in pods] == [(1, True), (2, False), (3, True)]


def test_session_groups_sort_naturally_and_skip_ungrouped_laptops():
    devices = [_device(1, "a", "Group 10", "Pat"), _device(2, "b", "Group 2", "Sandy"),
               _device(3, "hallway", None, None), _device(4, "c", "Group 2", "Pat")]
    tables = nc.session_groups(devices, NAMES)
    assert [t["group"] for t in tables] == ["Group 2", "Group 10"]
    assert [p["id"] for p in tables[0]["pods"]] == [4, 2]


def test_group_transcript_merges_both_laptops_into_one_conversation():
    pat, sandy = _device(1, "Pat laptop", side="Pat"), _device(2, "Sandy laptop", side="Sandy")
    rows = {
        1: [_row(11, 1, 100.0, "We hold four hundred thousand dollars of your debt.", "Pat1G7"),
            _row(12, 1, 105.0, "So what are you thinking?", "Pat1G7"),
            _row(13, 1, 112.0, "the market is really bad right now", None)],   # Sandy's side, heard faintly
        2: [_row(21, 2, 100.2, "We hold four hundred thousand dollars of your debt.", None),  # Pat, heard across the table
            _row(22, 2, 112.0, "The market is really bad right now.", "Sandy1G7"),
            _row(23, 2, 116.0, "If we can get through this hardship together.", "Sandy1G7")],
    }
    out = nc.group_transcript([pat, sandy], rows, NAMES)
    lines = out["lines"]
    texts = [(l["session_device_id"], l["speaker_tag"], l["transcript"]) for l in lines]
    # Pat's own laptop keeps Pat's line; Sandy's copy of it is folded in.
    assert texts[0][0] == 1 and texts[0][1] == "Pat1G7" and "debt" in texts[0][2]
    assert 21 in lines[0]["merged_from"] or 21 in lines[0]["stitched_from"] or \
        any(d["transcript_id"] == 21 for d in out["dropped"])
    # Sandy 1's two pieces on Sandy's laptop become one turn; Pat's faint hearing of it is gone.
    sandy1 = [l for l in lines if l["speaker_tag"] == "Sandy1G7"]
    assert len(sandy1) == 1 and 23 in sandy1[0]["stitched_from"] and sandy1[0]["session_device_id"] == 2
    assert not any(l["id"] == 13 for l in lines)
    # Panel field names and team stamps.
    for l in lines:
        assert {"id", "start_time", "length", "transcript", "speaker_tag", "team", "session_device_id"} <= set(l)
    assert lines[0]["team"] == "Pat" and sandy1[0]["team"] == "Sandy"
    assert out["alignment"] is None or isinstance(out["alignment"], dict)


def test_group_dynamics_counts_each_merged_line_once_under_its_speaker():
    pat, sandy = _device(1, "Pat laptop", side="Pat"), _device(2, "Sandy laptop", side="Sandy")
    rows = {
        1: [_row(11, 1, 100.0, "We hold four hundred thousand dollars of your debt.", "Pat1G7", length=5),
            _row(12, 1, 106.0, "So what are you thinking?", "Pat1G7", length=2, question=True)],
        2: [_row(21, 2, 100.2, "We hold four hundred thousand dollars of your debt.", None, length=5),
            _row(22, 2, 112.0, "The market is really bad right now.", "Sandy1G7", length=4),
            _row(23, 2, 116.0, "If we can get through this hardship together.", "Sandy1G7", length=4)],
    }
    out = nc.group_transcript([pat, sandy], rows, NAMES)
    assert all("question" in l for l in out["lines"])
    dyn = nc.group_dynamics(out["lines"], enrolled=["Pat1G7", "Sandy1G7"])
    names = {s["name"] for s in dyn["speakers"]}
    assert names == {"Pat1G7", "Sandy1G7"}                      # Sandy's unnamed copy of Pat's line is folded, not a third voice
    assert "talk" in dyn and dyn["talk"]


def test_speaker_labels_number_each_team_keeping_the_usernames_own_numbers():
    rosters = [{"session_device_id": 1, "side": "Pat", "aliases": ["Pat3G1S32", "Pat1G1S32", "Pat2G1S32"]},
               {"session_device_id": 2, "side": "Sandy", "aliases": ["Cy Example", "Ada Example", "Bo Example", ""]}]
    labels = nc.speaker_labels(rosters, NAMES)
    assert [(s["alias"], s["label"]) for s in labels] == [
        ("Pat1G1S32", "Pat 1"), ("Pat2G1S32", "Pat 2"), ("Pat3G1S32", "Pat 3"),
        ("Ada Example", "Sandy 1"), ("Bo Example", "Sandy 2"), ("Cy Example", "Sandy 3")]
    assert labels[0]["team_index"] == 0 and labels[3]["team_index"] == 1
    assert labels[3]["session_device_id"] == 2


def test_speaker_labels_fill_the_free_numbers_and_ignore_the_group_digit():
    # Sand2/Sand3 keep 2 and 3, the nickname takes 1; "SandyG4S31" carries
    # the group's 4, not a student number, so it takes the next free one.
    rosters = [{"session_device_id": 9, "side": "Sandy", "aliases": ["Sand3G2S32", "Nickname", "Sand2G2S32", "SandyG4S31"]}]
    labels = {s["alias"]: s["label"] for s in nc.speaker_labels(rosters, NAMES)}
    assert labels == {"Nickname": "Sandy 1", "Sand2G2S32": "Sandy 2", "Sand3G2S32": "Sandy 3", "SandyG4S31": "Sandy 4"}


def test_speaker_labels_keep_a_name_no_roster_lists():
    rosters = [{"session_device_id": 1, "side": "Pat", "aliases": ["Pat1G7"]}]
    lines = [{"speaker_tag": "Guest", "team": "Sandy", "session_device_id": 2},
             {"speaker_tag": None, "team": "Pat"}, {"speaker_tag": "Pat1G7", "team": "Pat"}]
    labels = nc.speaker_labels(rosters, NAMES, lines)
    assert [(s["alias"], s["label"], s["team"], s["index"]) for s in labels] == [
        ("Pat1G7", "Pat 1", "Pat", 1), ("Guest", "Guest", "Sandy", None)]


def test_group_dynamics_by_team_counts_floor_takes_and_handoffs():
    pat, sandy = _device(1, "Pat laptop", side="Pat"), _device(2, "Sandy laptop", side="Sandy")
    rows = {
        1: [_row(11, 1, 100.0, "We hold four hundred thousand dollars of your debt.", "Pat1G7", length=5),
            _row(12, 1, 106.0, "So what are you thinking?", "Pat2G7", length=2, question=True)],
        2: [_row(22, 2, 112.0, "The market is really bad right now.", "Sandy1G7", length=4),
            _row(23, 2, 116.0, "If we can get through this hardship together.", "Sandy1G7", length=4),
            _row(24, 2, 121.0, "Yes.", "Sandy2G7", length=1),
            _row(25, 2, 123.0, "We can do that.", "Pat1G7", length=3)],
    }
    out = nc.group_transcript([pat, sandy], rows, NAMES)
    speakers = nc.speaker_labels([{"session_device_id": 1, "side": "Pat", "aliases": ["Pat1G7", "Pat2G7"]},
                                  {"session_device_id": 2, "side": "Sandy", "aliases": ["Sandy1G7", "Sandy2G7"]}], NAMES, out["lines"])
    dyn = nc.group_dynamics(out["lines"], enrolled=["Pat1G7", "Pat2G7", "Sandy1G7", "Sandy2G7"], speakers=speakers, names=NAMES)
    teams = dyn["teams"]
    assert teams["names"] == ["Pat", "Sandy"]
    assert teams["members"] == {"Pat": ["Pat 1", "Pat 2"], "Sandy": ["Sandy 1", "Sandy 2"]}
    by_name = {s["name"]: s for s in teams["speakers"]}
    assert by_name["Pat"]["turns"] == 2 and by_name["Sandy"]["turns"] == 1      # Pat, Sandy, Pat again
    assert by_name["Pat"]["speaking_seconds"] == 10 and by_name["Sandy"]["speaking_seconds"] == 9
    assert {(t["from"], t["to"]): t["count"] for t in teams["transitions"]} == {("Pat", "Sandy"): 1, ("Sandy", "Pat"): 1}
    handoffs = {(h["from"], h["to"]): h["count"] for h in teams["handoffs"]}
    assert handoffs == {("Pat", "Pat"): 1, ("Pat", "Sandy"): 1, ("Sandy", "Sandy"): 1, ("Sandy", "Pat"): 1}
    assert teams["talk"]["questions"]["total"] == 1
    assert {s["name"] for s in teams["talk"]["per_speaker"]} >= {"Pat", "Sandy"}


def test_export_row_names_the_speaker_by_team_label():
    code = {"session_device_id": 1, "speaker_tag": "Ada Example", "team": "Sandy", "start_time": 100.0,
            "length": 3, "text": "Yes.", "transcript_id": 7}
    pods = {1: {"name": "Sandy laptop", "group": "Group 7", "side": "Sandy"}}
    row = nc.export_row(code, pods, [], 5, labels={"Ada Example": "Sandy 1"})
    assert row[:5] == ["Group 7", "Sandy laptop", "Sandy", "Sandy", "Sandy 1"]
    assert nc.export_row(code, pods, [], 5)[4] == "Ada Example"      # no labels: as stored
