"""ASR connector factory.

Selects the transcription backend from the ``asr`` config key (config.py
``asr()``). Heavy backends are imported lazily so an unused one never needs its
dependencies installed.
"""
import logging


def create_asr(name, audio_queue, transcript_queue, config, media_type, interval):
    key = (name or "google-cloud-speech").strip().lower()
    args = (audio_queue, transcript_queue, config, media_type, interval)

    # Plain Whisper was retired in favour of CrisperWhisper; the old keys stay
    # as aliases so sessions created before the switch keep transcribing.
    if key in ("crisperwhisper", "crisper-whisper", "crisperwhisper2",
               "whisper", "faster-whisper", "local-whisper"):
        from .crisperwhisper_asr import CrisperWhisperASR

        if key.startswith(("whisper", "faster", "local")):
            logging.info("ASR backend: legacy '%s' now runs CrisperWhisper 2.0", key)
        else:
            logging.info("ASR backend: CrisperWhisper 2.0")
        return CrisperWhisperASR(*args)

    if key not in ("google-cloud-speech", "google", ""):
        logging.warning("Unknown asr '%s'; falling back to Google Cloud Speech", name)

    from .google_asr_connector import GoogleASR

    logging.info("ASR backend: Google Cloud Speech")
    return GoogleASR(*args)
