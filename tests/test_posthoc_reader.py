"""The post-hoc stream reader's empty mode: MOSS reads the recording itself
and names its own turns, so the reader feeds neither the audio buffer nor
the ASR queue and only signals the end of the stream (the buffer used to
hold the whole recording, 1-2 GiB a pod, for nothing)."""
import os
import sys
from queue import Queue
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

pytest.importorskip("soundfile")      # the reader's file decoder; the source contract test covers CI
from audio_buffer import AudioBuffer  # noqa: E402
from audio_stream_reader import AudioStreamReader  # noqa: E402

STOP = object()


def _reader(path, fill):
    config = SimpleNamespace(channels=1, auth_key="pod-1")
    buf = AudioBuffer(config, max_seconds=7200)
    q = Queue()
    return AudioStreamReader(buf, q, path, 1, config, STOP, {}, realtime=False, fill=fill), buf, q


def test_an_empty_reader_signals_the_end_of_stream_without_opening_the_file(tmp_path):
    reader, buf, q = _reader(str(tmp_path / "missing.wav"), fill=False)
    reader._run()
    assert q.get(timeout=1) is STOP and q.empty()
    assert len(buf.audio_buffer) == 0


def test_a_filling_reader_feeds_the_buffer_and_the_queue(tmp_path):
    import numpy as np
    import soundfile as sf
    path = str(tmp_path / "pod.wav")
    sf.write(path, np.zeros(16000, dtype="float32"), 16000)
    reader, buf, q = _reader(path, fill=True)
    reader._run()
    chunks = []
    while True:
        item = q.get(timeout=1)
        if item is STOP:
            break
        chunks.append(item)
    assert sum(len(c) for c in chunks) == 16000 * 2 and len(buf.audio_buffer) == 16000 * 2
