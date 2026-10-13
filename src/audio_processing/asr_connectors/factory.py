"""ASR connector factory.

CrisperWhisper 2.0 is the only live transcription backend. Google Cloud
Speech-to-Text was removed on 2026-10-13 (audio no longer leaves the
machine) and plain Whisper was retired before that; both keys stay as
aliases so a session created under them keeps transcribing, and an unknown
key logs a warning and runs CrisperWhisper too. The backend is imported
lazily so this module stays importable without its dependencies.
"""
import logging

DEFAULT = "crisperwhisper"
CRISPER_KEYS = ("crisperwhisper", "crisper-whisper", "crisperwhisper2")
LEGACY_KEYS = ("whisper", "faster-whisper", "local-whisper", "google-cloud-speech", "google")


def normalize(name):
    """(backend key, note): the key a request or config value maps to, always
    ``crisperwhisper`` today, and why when it was not asked for by name."""
    key = (name or DEFAULT).strip().lower()
    if key in CRISPER_KEYS:
        return DEFAULT, None
    if key in LEGACY_KEYS:
        return DEFAULT, "legacy '%s' now runs CrisperWhisper 2.0" % key
    return DEFAULT, "unknown asr '%s'; running CrisperWhisper 2.0" % name


def create_asr(name, audio_queue, transcript_queue, config, media_type, interval):
    _, note = normalize(name)
    if note is None:
        logging.info("ASR backend: CrisperWhisper 2.0")
    elif note.startswith("legacy"):
        logging.info("ASR backend: %s", note)
    else:
        logging.warning("ASR backend: %s", note)
    from .crisperwhisper_asr import CrisperWhisperASR

    return CrisperWhisperASR(audio_queue, transcript_queue, config, media_type, interval)
