"""Common contract for ASR connectors.

Every connector consumes raw PCM audio chunks from ``audio_queue`` and pushes
recognition results onto ``transcript_queue``, terminating with a ``None``
sentinel. Downstream (``processor.py``) reads results in Google Cloud Speech's
object shape:

    result.alternatives[0].transcript
    result.alternatives[0].words[i].word
    result.alternatives[0].words[i].start_time.seconds / .nanos
    result.alternatives[0].words[i].end_time.seconds / .nanos

The adapter classes below reproduce that shape so a non-Google connector can
emit results without any change to the consumer. GoogleASR already emits native
protobuf objects of this shape, so it does not need the adapters.
"""

import json
import os
import queue as _queue_module
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager

NANO = 1_000_000_000

# One documented budget for the post-hoc one-shot workers. Whole-recording
# transcription of a long session can run several times slower than real time
# (Qwen3-ASR ~2.2x), so an hour of audio needs well over an hour of wall clock.
# The two connectors previously hardcoded 3600 and 7200 with no rationale — a
# silent drift where the shorter one could time out a long recording.
POSTHOC_WORKER_TIMEOUT = 2 * 60 * 60  # 2 hours


def worker_python(venv_dir, levels_up):
    """Path to a dedicated venv's python if it exists, else the current
    interpreter. ``venv_dir`` sits ``levels_up`` directories above THIS file
    (asr_connectors/): e.g. ``worker_python("qwen_venv", 2)`` -> audio_processing/,
    ``worker_python("venv-crisper", 3)`` -> src/. The unified py3.10 env means
    the current interpreter is the normal answer; the venv is a legacy fallback.
    """
    base = os.path.abspath(__file__)
    for _ in range(levels_up):
        base = os.path.dirname(base)
    dedicated = os.path.join(base, venv_dir, "bin", "python")
    return dedicated if os.path.exists(dedicated) else sys.executable


def run_json_worker(build_argv, timeout):
    """Run a subprocess that writes its result as JSON to a temp path and
    return the parsed dict. ``build_argv(out_path)`` returns the full argv with
    ``out_path`` placed wherever that worker expects it (the two workers put it
    at different positions). Raises RuntimeError on a non-zero exit. Always
    removes the temp file.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        out_path = tf.name
    try:
        proc = subprocess.run(build_argv(out_path), capture_output=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError("worker failed: %s" % proc.stderr.decode()[-500:])
        with open(out_path) as f:
            return json.load(f)
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass


@contextmanager
def permissive_torch_load():
    """torch>=2.6 defaults weights_only=True, which rejects the pyannote /
    wav2vec2 checkpoints these connectors load. They are trusted Hugging Face
    downloads; force the permissive behaviour for the duration of model loading
    and restore it afterward.
    """
    import torch
    original_load = torch.load

    def _permissive_load(*args, **kwargs):
        kwargs["weights_only"] = False
        return original_load(*args, **kwargs)

    torch.load = _permissive_load
    try:
        yield
    finally:
        torch.load = original_load


class AsrTime:
    def __init__(self, total_seconds):
        total_seconds = max(0.0, float(total_seconds))
        self.seconds = int(total_seconds)
        self.nanos = int(round((total_seconds - self.seconds) * NANO))


class AsrWord:
    def __init__(self, word, start_time, end_time):
        self.word = word
        self.start_time = AsrTime(start_time)
        self.end_time = AsrTime(end_time)


class AsrAlternative:
    def __init__(self, transcript, words):
        self.transcript = transcript
        self.words = words


class AsrResult:
    """Google-compatible result. ``words`` is a list of (text, start_s, end_s)."""

    def __init__(self, transcript, words):
        self.alternatives = [
            AsrAlternative(
                transcript,
                [AsrWord(w, s, e) for (w, s, e) in words],
            )
        ]


class BaseASR:
    """Base for ASR connectors. Subclasses implement start()/stop().

    Constructor signature is fixed so connectors are interchangeable via the
    factory:
        (audio_queue, transcript_queue, config, media_type, interval)
    """

    SAMPLE_RATE = 16000
    DEPTH = 2  # bytes per sample (16-bit PCM)

    def __init__(self, audio_queue, transcript_queue, config, media_type, interval):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.media_type = media_type
        self.audio_interval = interval
        self.running = False

    def start(self):
        raise NotImplementedError

    def stop(self):
        self.running = False


class PosthocFileASR:
    """Base for post-hoc connectors that read the WHOLE recording file directly
    (WhisperX / Qwen3 / CrisperWhisper-posthoc).

    These do not consume PCM from the audio queue — the post-hoc stream reader
    fills the AudioBuffer that downstream diarization/DoA need, and this
    connector just DRAINS the queue so the reader never blocks. Subclasses set
    ``self.audio_queue`` / ``self.running`` in their own __init__, define
    ``DRAIN_NAME`` (for thread names) and implement ``_transcribe_file``.
    """

    DRAIN_NAME = "posthoc"

    def start(self):
        self.running = True
        threading.Thread(target=self._drain_queue, daemon=True,
                         name="%s-queue-drain" % self.DRAIN_NAME).start()
        threading.Thread(target=self._transcribe_file, daemon=True,
                         name="%s-transcribe" % self.DRAIN_NAME).start()

    def stop(self):
        self.running = False

    def _drain_queue(self):
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.25)
            except _queue_module.Empty:
                continue
            if chunk is None or not isinstance(chunk, (bytes, bytearray)):
                break

    def _transcribe_file(self):
        raise NotImplementedError
