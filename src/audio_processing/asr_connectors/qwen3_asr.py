"""Qwen3-ASR connector for post-hoc re-analysis.

Qwen3-ASR (Alibaba, Jan 2026; Apache-2.0) tops the open ASR leaderboards on
English WER. The qwen-asr package requires Python >=3.10, so transcription
runs in a dedicated qwen_venv via the qwen3_worker.py subprocess; this
connector parses its JSON and emits Google-shaped AsrResults, optionally
attaching pyannote speaker labels (same as the WhisperX path).

Measured on this instance: ~2.2x slower than real time for transcription +
alignment (a 5.5-min recording takes ~2 min), vs. seconds for WhisperX.
"""

import os
import json
import logging
import subprocess
import threading
import queue as queue_module

from .base_asr import AsrResult

_WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qwen3_worker.py")


def _worker_python():
    # Historically qwen-asr lived in a dedicated py3.10 venv (the pipeline ran
    # py3.9). On the unified py3.10 environment qwen-asr is installed alongside
    # everything else, so the current interpreter works; prefer the dedicated
    # venv only if it still exists.
    import sys
    dedicated = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "qwen_venv", "bin", "python")
    return dedicated if os.path.exists(dedicated) else sys.executable


class Qwen3ASR:
    def __init__(self, audio_queue, transcript_queue, config, media_type,
                 interval, audio_file=None, model_id=None, diarize=False):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.audio_file = audio_file
        self.model_id = model_id or "Qwen/Qwen3-ASR-1.7B"
        self.diarize = diarize
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._drain_queue, daemon=True,
                         name="qwen3-queue-drain").start()
        threading.Thread(target=self._transcribe_file, daemon=True,
                         name="qwen3-transcribe").start()

    def stop(self):
        self.running = False

    def _drain_queue(self):
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.25)
            except queue_module.Empty:
                continue
            if chunk is None or not isinstance(chunk, (bytes, bytearray)):
                break

    def _speaker_turns(self):
        # pyannote diarization runs in THIS (3.9) process — only qwen-asr
        # itself needs 3.10.
        import torch
        original_load = torch.load

        def _permissive_load(*args, **kwargs):
            kwargs["weights_only"] = False
            return original_load(*args, **kwargs)

        torch.load = _permissive_load
        try:
            from pyannote.audio import Pipeline
            token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1", use_auth_token=token)
            pipeline.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
            diarization = pipeline(self.audio_file)
            return [(turn.start, turn.end, label)
                    for turn, _, label in diarization.itertracks(yield_label=True)]
        finally:
            torch.load = original_load

    @staticmethod
    def _speaker_at(turns, midpoint):
        for start, end, label in turns:
            if start <= midpoint <= end:
                return label
        return None

    def _transcribe_file(self):
        try:
            logging.info("Qwen3-ASR: transcribing %s via %s", self.audio_file, self.model_id)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
                out_path = tf.name
            try:
                proc = subprocess.run(
                    [_worker_python(), _WORKER, self.audio_file, self.model_id, out_path],
                    capture_output=True, timeout=3600)
                if proc.returncode != 0:
                    raise RuntimeError("worker failed: %s" % proc.stderr.decode()[-500:])
                with open(out_path) as f:
                    data = json.load(f)
            finally:
                try:
                    os.remove(out_path)
                except OSError:
                    pass
            segments = data.get("segments", [])
            logging.info("Qwen3-ASR: %d segments", len(segments))

            turns = []
            if self.diarize:
                logging.info("Qwen3-ASR: running pyannote diarization")
                turns = self._speaker_turns()

            for segment in segments:
                words = [(w, s, e) for (w, s, e) in segment.get("words", [])]
                text = segment.get("text", "").strip()
                if not text or not words:
                    continue
                result = AsrResult(text, words)
                if turns:
                    midpoint = (words[0][1] + words[-1][2]) / 2.0
                    result.speaker_tag = self._speaker_at(turns, midpoint)
                self.transcript_queue.put(result)
        except Exception as e:
            logging.error("Qwen3-ASR transcription failed: %s", e, exc_info=True)
        finally:
            self.running = False
            self.transcript_queue.put(None)
