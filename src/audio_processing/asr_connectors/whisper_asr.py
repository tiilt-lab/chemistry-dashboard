"""Whisper ASR connector (faster-whisper).

A modern, open, offline-capable alternative to Google Cloud Speech. Selected
with ``asr=whisper`` in config.ini.

Whisper is not a native streaming model, so this connector batches: it
accumulates incoming PCM and transcribes fixed windows, emitting word-timed
results (offset to absolute session time) on the shared transcript_queue in the
Google-compatible shape from base_asr. This trades a little latency for
substantially better accuracy and no per-request cloud cost.

Requires:  pip install faster-whisper
Model size / device are configurable via the [whisper] config section.
"""
import queue
import logging
import threading

import numpy as np

from .base_asr import BaseASR, AsrResult


class WhisperASR(BaseASR):
    # Transcribe roughly every WINDOW_SECONDS of buffered audio.
    WINDOW_SECONDS = 12.0

    def __init__(self, audio_queue, transcript_queue, config, media_type, interval):
        super().__init__(audio_queue, transcript_queue, config, media_type, interval)
        self._model = None
        self._buffer = bytearray()
        self._window_start = 0.0  # absolute seconds of the buffer's first sample
        self._consumed = 0.0  # absolute seconds already emitted

    def _load_model(self):
        if self._model is not None:
            return
        # Lazy import so the Google path never requires faster-whisper.
        from faster_whisper import WhisperModel
        import config as cf  # deployment-level [whisper] settings

        model_size = cf.whisper_model_size()
        device = cf.whisper_device()
        compute_type = cf.whisper_compute_type()
        logging.info(
            "Loading Whisper model '%s' (device=%s, compute=%s)",
            model_size, device, compute_type,
        )
        self._model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )

    def start(self):
        self.running = True
        self._load_model()
        self.asr_thread = threading.Thread(target=self._processing, name="whisper-asr")
        self.asr_thread.daemon = True
        self.asr_thread.start()

    def _window_full(self):
        samples = len(self._buffer) / self.DEPTH
        return samples / self.SAMPLE_RATE >= self.WINDOW_SECONDS

    def _processing(self):
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            # None is the live pipeline's end sentinel; the post-hoc stream
            # reader pushes an arbitrary STOP_SIGNAL object instead, so treat
            # anything that isn't audio bytes as end-of-stream.
            if chunk is None or not isinstance(chunk, (bytes, bytearray)):
                break
            self._buffer.extend(chunk)
            if self._window_full():
                self._flush()
        # Final partial window on stop.
        self._flush()
        self.transcript_queue.put(None)

    def _flush(self):
        if len(self._buffer) < self.DEPTH:
            return
        audio = (
            np.frombuffer(bytes(self._buffer), dtype=np.int16).astype(np.float32)
            / 32768.0
        )
        window_len = len(audio) / self.SAMPLE_RATE
        try:
            segments, _info = self._model.transcribe(
                audio, language="en", word_timestamps=True
            )
            for segment in segments:
                words = []
                for w in segment.words or []:
                    words.append(
                        (
                            w.word.strip(),
                            self._window_start + w.start,
                            self._window_start + w.end,
                        )
                    )
                text = (segment.text or "").strip()
                if text and words:
                    self.transcript_queue.put(AsrResult(text, words))
        except Exception as e:
            logging.warning("Whisper transcription failed: %s", e)
        # Advance the window; drop the consumed audio.
        self._window_start += window_len
        self._buffer = bytearray()


