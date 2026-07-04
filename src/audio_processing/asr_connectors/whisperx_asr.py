"""WhisperX connector for post-hoc re-analysis.

WhisperX (open source: faster-whisper backend + wav2vec2 forced alignment)
transcribes the WHOLE stored recording in one batched pass and returns
word-level timestamps far more accurate than streaming windows — the right
shape for post-hoc work, where the full file is available up front.

Unlike the streaming connectors it does not consume PCM from the audio queue;
it reads the recording file directly (the post-hoc stream reader still fills
the AudioBuffer that downstream diarization/DoA extraction needs — this
connector just drains the queue so the reader never blocks). Speaker
attribution stays with the existing fingerprint matching downstream.
"""

import logging
import threading
import queue as queue_module

from .base_asr import AsrResult


class WhisperXASR:
    def __init__(self, audio_queue, transcript_queue, config, media_type,
                 interval, audio_file=None, model_size=None):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.audio_file = audio_file
        self.model_size = model_size or "small"
        self.running = False

    def start(self):
        self.running = True
        drain = threading.Thread(target=self._drain_queue, daemon=True,
                                 name="whisperx-queue-drain")
        drain.start()
        worker = threading.Thread(target=self._transcribe_file, daemon=True,
                                  name="whisperx-transcribe")
        worker.start()

    def stop(self):
        self.running = False

    def _drain_queue(self):
        # The post-hoc reader pushes PCM chunks for streaming ASRs; WhisperX
        # reads the file directly, so just keep the queue from filling up.
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.25)
            except queue_module.Empty:
                continue
            if chunk is None or not isinstance(chunk, (bytes, bytearray)):
                break

    def _transcribe_file(self):
        try:
            import torch
            # torch>=2.6 defaults weights_only=True, which rejects the
            # pyannote/wav2vec2 checkpoints whisperx loads. These are trusted
            # Hugging Face downloads; restore the permissive behaviour for the
            # duration of model loading.
            original_load = torch.load

            def _permissive_load(*args, **kwargs):
                kwargs["weights_only"] = False
                return original_load(*args, **kwargs)

            torch.load = _permissive_load
            try:
                import whisperx
                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute = "float16" if device == "cuda" else "int8"
                logging.info("WhisperX: loading model '%s' on %s", self.model_size, device)
                model = whisperx.load_model(self.model_size, device, compute_type=compute)
                audio = whisperx.load_audio(self.audio_file)
                result = model.transcribe(audio, batch_size=16)
                language = result.get("language", "en")
                logging.info("WhisperX: transcribed %d segments (lang=%s); aligning",
                             len(result["segments"]), language)
                align_model, metadata = whisperx.load_align_model(
                    language_code=language, device=device)
                result = whisperx.align(result["segments"], align_model,
                                        metadata, audio, device)
            finally:
                torch.load = original_load

            emitted = 0
            for segment in result["segments"]:
                text = (segment.get("text") or "").strip()
                if not text:
                    continue
                words = [
                    (w["word"], w["start"], w["end"])
                    for w in segment.get("words", [])
                    if "start" in w and "end" in w
                ]
                if not words:
                    # Alignment can skip tokens (numbers etc.); fall back to
                    # the segment span so downstream timing still works.
                    words = [(text, segment.get("start", 0.0), segment.get("end", 0.0))]
                self.transcript_queue.put(AsrResult(text, words))
                emitted += 1
            logging.info("WhisperX: emitted %d transcript results", emitted)
        except Exception as e:
            logging.error("WhisperX transcription failed: %s", e, exc_info=True)
        finally:
            self.running = False
            self.transcript_queue.put(None)
