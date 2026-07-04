"""ASR connector factory.

Selects the transcription backend from the ``asr`` config key (config.py
``asr()``). Heavy backends are imported lazily so an unused one never needs its
dependencies installed.
"""
import logging


def create_asr(name, audio_queue, transcript_queue, config, media_type, interval):
    key = (name or "google-cloud-speech").strip().lower()
    args = (audio_queue, transcript_queue, config, media_type, interval)

    if key in ("whisper", "faster-whisper", "local-whisper"):
        from .whisper_asr import WhisperASR

        logging.info("ASR backend: Whisper")
        return WhisperASR(*args)

    if key not in ("google-cloud-speech", "google", ""):
        logging.warning("Unknown asr '%s'; falling back to Google Cloud Speech", name)

    from .google_asr_connector import GoogleASR

    logging.info("ASR backend: Google Cloud Speech")
    return GoogleASR(*args)
