"""src/audio_processing/timeline_recorder.py: one track per pod, gaps as silence."""
import json
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

import timeline_recorder as tr  # noqa: E402

SR = 16000


def tone(seconds, value=1000):
    return (np.ones(int(seconds * SR), dtype="<i2") * value).tobytes()


def read(path):
    with wave.open(path, "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SR, 1, 2)
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")


def test_gaps_become_silence_and_overlaps_are_skipped(tmp_path):
    rec = tr.TimelineRecorder(str(tmp_path / "k_timeline_redu"))
    rec.write(tone(1.0, 1), 100.0)              # 100-101
    rec.write(tone(1.0, 2), 103.0)              # 2 s gap -> 2 s silence, then 103-104
    rec.write(tone(1.0, 3), 103.5)              # overlaps 0.5 s: only 104-104.5 is new
    rec.write(tone(0.5, 4), 104.5 + 0.01)       # 10 ms early/late is jitter: appended as is
    rec.finalize()
    x = read(str(tmp_path / "k_timeline_redu.wav"))
    assert rec.start == 100.0 and abs(rec.end - 105.0) < 1e-6
    assert len(x) == 5 * SR
    assert x[0] == 1 and x[SR - 1] == 1
    assert x[SR] == 0 and x[3 * SR - 1] == 0                   # the gap
    assert x[3 * SR] == 2 and x[4 * SR - 1] == 2
    assert x[4 * SR] == 3 and x[int(4.5 * SR) - 1] == 3        # only the new half of the overlap
    assert x[int(4.5 * SR)] == 4 and x[-1] == 4


def test_a_reconnect_appends_to_the_same_track_and_the_wav_is_refreshed(tmp_path):
    base = str(tmp_path / "k_timeline_redu")
    first = tr.TimelineRecorder(base)
    first.write(tone(2.0, 7), 50.0)
    first.finalize()
    assert len(read(base + ".wav")) == 2 * SR
    # the first write recorded where the track begins, beside the .dat
    assert json.load(open(base + ".start"))["start"] == 50.0
    # the next connection in a NEW process (a service restart mid-session):
    # a new recorder object on the same files recovers the start, so the
    # reconnect's frames land after the existing audio, not over it
    second = tr.TimelineRecorder(base)
    assert second.samples == 2 * SR and second.start == 50.0
    second.write(tone(1.0, 8), 53.0)           # 1 s gap after 52
    second.finalize()
    x = read(base + ".wav")
    assert len(x) == 4 * SR and x[2 * SR] == 0 and x[3 * SR] == 8
    assert abs(second.end - 54.0) < 1e-6


def test_a_track_whose_start_is_unknown_is_set_aside_not_appended_to(tmp_path):
    # A .dat from a process that crashed before writing .start or a clock
    # sidecar: appending would stamp its first sample at the reconnect time
    # and drop the next frames as overlap (2026-10-19 sweep P1 #5).
    base = str(tmp_path / "k_timeline_redu")
    with open(base + ".dat", "wb") as f:
        f.write(tone(2.0, 7))
    rec = tr.TimelineRecorder(base)
    assert rec.samples == 0 and rec.start is None
    assert not os.path.exists(base + ".dat")
    assert any(".orphan-" in name for name in os.listdir(str(tmp_path)))
    rec.write(tone(1.0, 8), 200.0)
    rec.finalize()
    assert rec.start == 200.0 and len(read(base + ".wav")) == SR


def test_the_clock_sidecar_recovers_a_start_without_a_start_file(tmp_path):
    # Tracks written before the .start file existed ended cleanly with a
    # recording_sidecar beside them; its start_offset is the same number.
    base = str(tmp_path / "k_timeline_redu")
    with open(base + ".dat", "wb") as f:
        f.write(tone(2.0, 7))
    with open(base + ".clock.json", "w") as f:
        json.dump({"start_offset": 50.0, "moves": []}, f)
    rec = tr.TimelineRecorder(base)
    assert rec.start == 50.0 and rec.samples == 2 * SR
    rec.write(tone(1.0, 8), 53.0)
    assert abs(rec.end - 54.0) < 1e-6 and rec.samples == 4 * SR


def test_registry_returns_one_recorder_per_pod(tmp_path):
    tr._registry.clear()
    a = tr.for_pod(str(tmp_path), "pod-a")
    assert tr.for_pod(str(tmp_path), "pod-a") is a
    assert tr.for_pod(str(tmp_path), "pod-b") is not a
    assert a.base.endswith("pod-a_timeline_redu")


def test_an_absurd_gap_is_not_padded(tmp_path):
    rec = tr.TimelineRecorder(str(tmp_path / "k_timeline_redu"))
    rec.write(tone(1.0), 100.0)
    rec.write(tone(1.0), 100.0 + 1.0 + 5 * 3600)   # five hours "later": a clock fault
    assert rec.samples == 2 * SR
