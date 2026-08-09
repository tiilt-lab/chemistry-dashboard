"""AudioBuffer regression tests for today's fixes.

- append advanced buffer_start by the float trim amount while trimming
  int(extra_time*sr) samples, accumulating ~a sample of skew per trim.
- extract did not clamp, so a stale timestamp older than the retained window
  produced a NEGATIVE byte offset and returned audio from the wrong end.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

from audio_buffer import AudioBuffer  # noqa: E402

SR = 16000
FRAME = 1 * 2  # channels=1 * depth=2 bytes


def _buf(max_seconds):
    return AudioBuffer(SimpleNamespace(channels=1), max_seconds=max_seconds)


def test_extract_roundtrip():
    buf = _buf(max_seconds=180)
    # 100 frames of distinct little-endian int16 values 0,1,2,...
    import numpy as np
    data = np.arange(100, dtype=np.int16).tobytes()
    buf.append(data)
    # Window [10th frame, 20th frame) by time.
    got = buf.extract(10 / SR, 20 / SR)
    assert got == data[10 * FRAME:20 * FRAME]


def test_buffer_start_advances_by_exact_samples_no_drift():
    # A 1s window; append 1.5s so 0.5s (8000 samples) is trimmed.
    buf = _buf(max_seconds=1)
    buf.append(bytes(int(1.5 * SR) * FRAME))
    # New code: buffer_start is an EXACT integer number of samples / SR.
    start_samples = buf.buffer_start * SR
    assert abs(start_samples - round(start_samples)) < 1e-9
    assert round(start_samples) == int(0.5 * SR)


def test_extract_clamps_stale_timestamp():
    buf = _buf(max_seconds=1)
    buf.append(bytes(int(1.5 * SR) * FRAME))  # buffer_start now 0.5s
    # A timestamp well before the retained window: old code -> negative
    # offset -> tail bytes. Now it clamps to an empty slice, never tail data.
    stale = buf.extract(-100.0, -99.0)
    assert stale == b""
    # A normal in-window extract still returns head-anchored bytes.
    head = buf.extract(0.5, 0.5 + 5 / SR)
    assert len(head) == 5 * FRAME
