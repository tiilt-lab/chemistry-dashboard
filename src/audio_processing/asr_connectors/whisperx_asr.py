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
                 interval, audio_file=None, model_size=None, diarize=False,
                 max_speakers=None, enrolled=None, speaker_model=None,
                 diarizer=None):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.audio_file = audio_file
        self.model_size = model_size or "small"
        # Optional constraint to a pod's known enrolled participants: cap
        # pyannote at max_speakers and remap clusters onto enrolled voices.
        self.max_speakers = max_speakers
        self.enrolled = enrolled
        self.speaker_model = speaker_model
        # Optional speaker-diarization pass. 'pyannote' (open SOTA clustering;
        # gated weights need HUGGING_FACE_HUB_TOKEN) or 'sortformer' (NVIDIA
        # streaming Sortformer 4-spk, runs in its own NeMo venv). Segments get
        # cluster labels attached as .speaker_tag on each AsrResult. The bare
        # `diarize` bool is the legacy pyannote switch.
        self.diarizer = diarizer or ("pyannote" if diarize else None)
        self.diarize = self.diarizer is not None
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
                cluster_map = {}
                if self.diarizer == "sortformer":
                    import pandas as pd
                    from whisperx.diarize import assign_word_speakers
                    from asr_connectors.sortformer_diar import run_sortformer
                    logging.info("WhisperX: running Sortformer diarization (NeMo venv)")
                    sf_turns = run_sortformer(self.audio_file)
                    diarize_segments = pd.DataFrame(
                        [{"start": s, "end": e, "speaker": spk} for s, e, spk in sf_turns])
                    if len(diarize_segments):
                        result = assign_word_speakers(diarize_segments, result)
                    logging.info("WhisperX: Sortformer diarization attached")
                    if self.enrolled and self.speaker_model and sf_turns:
                        from asr_connectors.cluster_reconcile import build_cluster_to_enrolled_map
                        cluster_map = build_cluster_to_enrolled_map(
                            self.audio_file, sf_turns, self.enrolled, self.speaker_model)
                elif self.diarize:
                    import os
                    from whisperx.diarize import DiarizationPipeline, assign_word_speakers
                    token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
                    logging.info("WhisperX: running pyannote diarization")
                    diarizer = DiarizationPipeline(model_name="pyannote/speaker-diarization-3.1", token=token, device=device)
                    diarize_segments = diarizer(audio, max_speakers=self.max_speakers)
                    result = assign_word_speakers(diarize_segments, result)
                    logging.info("WhisperX: diarization attached")
                    if self.enrolled and self.speaker_model:
                        from asr_connectors.cluster_reconcile import build_cluster_to_enrolled_map
                        turns = [(row['start'], row['end'], row['speaker'])
                                 for _, row in diarize_segments.iterrows()]
                        cluster_map = build_cluster_to_enrolled_map(
                            self.audio_file, turns, self.enrolled, self.speaker_model)
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
                asr_result = AsrResult(text, words)
                # pyannote cluster label (SPEAKER_00...), remapped to an enrolled
                # alias when reconciliation is on; consumed downstream when
                # fingerprint matching yields nothing.
                _sp = segment.get("speaker")
                asr_result.speaker_tag = cluster_map.get(_sp, _sp)
                self.transcript_queue.put(asr_result)
                emitted += 1
            logging.info("WhisperX: emitted %d transcript results", emitted)
        except Exception as e:
            logging.error("WhisperX transcription failed: %s", e, exc_info=True)
        finally:
            # Models are loaded fresh per pod inside a long-lived service;
            # without an explicit release the CUDA allocations accumulate
            # until a later pod's model load dies with CUDA OOM (observed
            # mid-batch after ~5 pods with two instances sharing the card).
            try:
                import gc
                import torch
                # locals()-based deletion is a no-op in CPython; drop each
                # reference explicitly so gc can actually free the models.
                try:
                    del model
                except NameError:
                    pass
                try:
                    del align_model, metadata
                except NameError:
                    pass
                try:
                    del diarizer, diarize_segments
                except NameError:
                    pass
                try:
                    del audio, result
                except NameError:
                    pass
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logging.info("WhisperX: released CUDA cache (%.1f GiB still reserved)",
                                 torch.cuda.memory_reserved() / 2**30)
            except Exception:
                pass
            self.running = False
            self.transcript_queue.put(None)
