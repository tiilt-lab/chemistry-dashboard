"""src/audio_processing/timeline_recorder.py: one track per pod, gaps as silence."""
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
    # the next connection: a new recorder object on the same files
    second = tr.TimelineRecorder(base)
    assert second.samples == 2 * SR and second.start is None
    second.start = first.start                 # the registry keeps the object alive in practice
    second.write(tone(1.0, 8), 53.0)           # 1 s gap after 52
    second.finalize()
    x = read(base + ".wav")
    assert len(x) == 4 * SR and x[2 * SR] == 0 and x[3 * SR] == 8


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
