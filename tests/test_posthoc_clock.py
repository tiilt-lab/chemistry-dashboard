"""A post-hoc run on the recording's real clock (src/common/recording_fragments.py
choose_recording / stitch_fragments, recording_sidecar.recording_time,
processing_config.posthoc_start_offset): the session timeline first, fragments
stitched with their gaps, the sidecar's clock over the file's name stamp."""
import datetime
import os
import sys

import numpy as np
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src", "common"))
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))

import recording_fragments as rf  # noqa: E402
import recording_sidecar as rs  # noqa: E402

KEY = "1436-0f3c2d1e-9a8b-4c7d-8e6f-5a4b3c2d1e0f"  # gitleaks:allow (fake recording key)
SERVER_START = datetime.datetime(2026, 10, 15, 20, 31, 26)


def test_recording_time_inverts_session_time_through_forward_moves():
    info = {"start_offset": 81627.456, "moves": [{"at": 0.256, "delta": 218.976}, {"at": 1000.0, "delta": 5.0}]}
    for t in (0.0, 0.2, 0.256, 300.0, 999.9, 1000.0, 2500.0):
        assert rs.recording_time(info, rs.session_time(info, t)) == pytest.approx(t, abs=1e-6)
    # a session moment inside a jump lands on the move; no moves = a plain offset
    assert rs.recording_time(info, 81627.456 + 0.256 + 100.0) == pytest.approx(0.256)
    assert rs.recording_time({"start_offset": 10.0, "moves": []}, 25.0) == pytest.approx(15.0)


def test_pod_key_from_every_recording_name():
    assert rf.pod_key("/rec/%s (Fri Oct 16 19:08:14 2026)_orig.wav" % KEY) == KEY
    assert rf.pod_key("/rec/%s_timeline_redu.wav" % KEY) == KEY
    assert rf.pod_key("/rec/%s_timeline_f32.wav" % KEY) == KEY
    assert rf.pod_key("/rec/%s (Fri Oct 16 19:08:14 2026)_stitched.wav" % KEY) == KEY


def test_stamp_offset_is_the_name_stamp_against_the_sessions_start():
    path = "/rec/%s (Fri Oct 16 14:12:13 2026)_orig.wav" % KEY
    assert rf.stamp_offset(path, SERVER_START) == pytest.approx(63647.0)
    assert rf.stamp_offset("/rec/%s_timeline_redu.wav" % KEY, SERVER_START) is None
    assert rf.stamp_offset(path, None) is None


def _wav_io(store):
    def read(path):
        return store[path]

    def write(path, sr, data):
        store[path.replace(".part.wav", ".wav")] = (sr, np.asarray(data, dtype=np.float32))
    return read, write


def test_stitch_lays_fragments_on_the_session_clock_with_gaps_overlaps_and_moves(tmp_path):
    sr = 100
    a = ("/rec/%s (Fri Oct 16 14:09:56 2026)_orig.wav" % KEY, np.full(10 * sr, 1.0, dtype=np.float32))     # 10 s at 100 s
    b = ("/rec/%s (Fri Oct 16 14:45:20 2026)_orig.wav" % KEY, np.full(6 * sr, 2.0, dtype=np.float32))      # 6 s at 130 s, after a 20 s gap
    c = ("/rec/%s (Fri Oct 16 14:50:00 2026)_orig.wav" % KEY, np.full(4 * sr, 3.0, dtype=np.float32))      # 4 s starting 2 s before b ends
    store = {a[0]: (sr, a[1]), b[0]: (sr, b[1]), c[0]: (sr, c[1])}
    read, write = _wav_io(store)
    clocks = [{"start_offset": 100.0, "moves": [{"at": 4.0, "delta": 3.0}]},   # a 3 s jump 4 s in: silence inside a
              {"start_offset": 130.0, "moves": []},
              {"start_offset": 134.0, "moves": []}]
    out = str(tmp_path / ("%s (Fri Oct 16 14:09:56 2026)_stitched.wav" % KEY))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    rf.stitch_fragments([a[0], b[0], c[0]], clocks, out, sample_rate=sr, read=read, write=write)
    sr_out, data = store[out]
    t = lambda s: int(round((s - 100.0) * sr))     # session second -> sample
    assert sr_out == sr and len(data) == t(138.0)                      # ends where c ends: 134 + 4
    assert data[t(100.0)] == 1.0 and data[t(103.9)] == 1.0
    assert data[t(104.5)] == 0.0 and data[t(106.9)] == 0.0            # the 3 s jump is silence
    assert data[t(107.0)] == 1.0 and data[t(112.9)] == 1.0            # the rest of a, 3 s later
    assert data[t(120.0)] == 0.0                                      # the reconnect gap
    assert data[t(130.0)] == 2.0 and data[t(135.9)] == 2.0            # b, whole
    assert data[t(136.0)] == 3.0 and data[t(137.9)] == 3.0            # c, its overlapping first 2 s skipped
    info = rs.read(out)
    assert info["start_offset"] == 100.0 and info["moves"] == [] and info["timeline"] is True
    assert info["stitched_from"] == [os.path.basename(x[0]) for x in (a, b, c)]


def test_choose_recording_prefers_the_session_timeline_and_its_clock(tmp_path):
    timeline = str(tmp_path / ("%s_timeline_redu.wav" % KEY))
    orig = str(tmp_path / ("%s (Fri Oct 16 19:08:14 2026)_orig.wav" % KEY))
    for p in (timeline, orig):
        open(p, "wb").write(b"RIFF")
    rs.write(timeline, {"start_offset": 81627.456, "moves": [], "timeline": True})
    converted = []

    def convert(src, out):
        converted.append((src, out)); open(out, "wb").write(b"RIFF"); rs.write(out, rs.read(src))
    chosen, clock = rf.choose_recording([orig, timeline], SERVER_START, convert=convert)
    assert chosen == str(tmp_path / ("%s_timeline_f32.wav" % KEY)) and converted == [(timeline, chosen)]
    assert clock == {"start_offset": 81627.456, "moves": []}
    # a second call finds the conversion fresh
    rf.choose_recording([orig, timeline, chosen], SERVER_START, convert=convert)
    assert len(converted) == 1


def test_choose_recording_takes_a_lone_fragments_sidecar_else_its_stamp(tmp_path):
    orig = str(tmp_path / ("%s (Fri Oct 16 19:11:19 2026)_orig.wav" % KEY))
    open(orig, "wb").write(b"RIFF")
    chosen, clock = rf.choose_recording([orig], SERVER_START)
    assert chosen == orig and clock == {"start_offset": 81593.0, "moves": []}
    rs.write(orig, {"start_offset": 81627.131, "moves": [{"at": 0.256, "delta": 34.016}]})
    chosen, clock = rf.choose_recording([orig], SERVER_START)
    assert clock == {"start_offset": 81627.131, "moves": [{"at": 0.256, "delta": 34.016}]}


def test_choose_recording_stitches_several_fragments_once(tmp_path):
    a = str(tmp_path / ("%s (Fri Oct 16 14:09:56 2026)_orig.wav" % KEY))
    b = str(tmp_path / ("%s (Fri Oct 16 14:45:20 2026)_orig.wav" % KEY))
    for p in (a, b):
        open(p, "wb").write(b"RIFF")
    calls = []

    def stitch(fragments, clocks, out):
        calls.append((fragments, clocks, out)); open(out, "wb").write(b"RIFF")
        rs.write(out, {"start_offset": clocks[0]["start_offset"], "moves": [], "timeline": True})
    chosen, clock = rf.choose_recording([b, a], SERVER_START, stitch=stitch)
    assert chosen == str(tmp_path / ("%s (Fri Oct 16 14:09:56 2026)_stitched.wav" % KEY))
    assert calls[0][0] == [a, b] and [c["start_offset"] for c in calls[0][1]] == [63510.0, 65634.0]
    assert clock == {"start_offset": 63510.0, "moves": []}
    rf.choose_recording([b, a, chosen], SERVER_START, stitch=stitch)
    assert len(calls) == 1


def test_the_config_takes_the_sidecar_clock_over_the_name_stamp():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pc_src", os.path.join(ROOT, "src", "audio_processing", "processing_config.py"))
    src = open(spec.origin).read()
    ns = {}
    start = src.index("def posthoc_start_offset("); end = src.index("\n\n\nclass ProcessingConfig")
    exec("from datetime import datetime\n" + src[start:end], ns)
    f = ns["posthoc_start_offset"]
    stamped = {"off_set_date": "Fri Oct 16 19:11:19 2026"}
    assert f(stamped, SERVER_START) == pytest.approx(81593.0)
    assert f(dict(stamped, clock_start_offset=81627.131), SERVER_START) == pytest.approx(81627.131)
    assert f(dict(stamped, clock_start_offset=81627.131), SERVER_START, offset=27.131) == pytest.approx(81600.0)
    assert "config.clock_moves = list(data.get('clock_moves') or [])" in src


def test_the_processor_and_the_naming_stamp_through_the_clock_moves():
    proc = open(os.path.join(ROOT, "src", "audio_processing", "processor_posthoc.py")).read()
    assert "recording_sidecar.session_time(clock, start_time)" in proc and "start_time += self.config.start_offset" not in proc
    moss = open(os.path.join(ROOT, "src", "audio_processing", "asr_connectors", "moss_asr.py")).read()
    assert "recording_sidecar.recording_time(clock, session_t)" in moss
    server = open(os.path.join(ROOT, "src", "audio_processing", "server_posthoc.py")).read()
    assert server.count("conf_val.update(self._clock_fields())") == 3
    assert "recording_fragments.choose_recording(files, server_start)" in server
