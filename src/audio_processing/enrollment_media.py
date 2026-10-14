"""The enrollment recording -> the 16 kHz mono WAV the voice print is built
from. Kept apart from server.py so it can be exercised without the Twisted
service around it.

The sign-up page records with MediaRecorder: a camera-and-mic take is a
WebM/MP4 with a picture, a voice-only take (no camera) is an audio-only
WebM (Opus) or MP4 (AAC). moviepy's VideoFileClip refuses the latter (no
first frame to read), so a voice-only take is opened as an AudioFileClip;
both give the same audio export.
"""
import logging

try:
    import moviepy.editor as mp  # moviepy 1.x
except Exception:  # pragma: no cover - which one is installed
    import moviepy as mp  # moviepy 2.x dropped the .editor module

# The RecordingCoach caps a take at 60 s; anything longer is a stuck
# recorder, not more speech.
MAX_SECONDS = 60.0

_EXPORT = dict(fps=16000, nbytes=2, codec="pcm_s16le",
               ffmpeg_params=["-ac", "1", "-af", "aresample=resampler=soxr:precision=33"])


def _subclip(clip, end):
    return (clip.subclipped if hasattr(clip, 'subclipped') else clip.subclip)(0, end)  # moviepy 2 rename


def _export(audio, out_wav):
    kwargs = dict(_EXPORT)
    try:
        audio.write_audiofile(out_wav, logger=None, **kwargs)
    except TypeError:  # moviepy 1.x has no logger kwarg
        audio.write_audiofile(out_wav, **kwargs)


def extract_audio(src, out_wav, voice_only=False, max_seconds=MAX_SECONDS):
    """Write the first `max_seconds` of `src`'s sound to `out_wav`. Returns
    "" on success, else a short reason. `voice_only` says the take has no
    picture; a take that claims a picture but has none is retried as sound
    (a sign-up page from before the voice-only option sends no flag)."""
    if voice_only:
        return _from_audio(src, out_wav, max_seconds)
    try:
        with mp.VideoFileClip(src, audio=True) as clip:
            end = min(max_seconds, float(clip.duration or 0))
            if end <= 0:
                return "Clip has zero/unknown duration"
            sub = _subclip(clip, end)
            if sub.audio is None:
                return "No audio stream"
            _export(sub.audio, out_wav)
            return ""
    except OSError as e:
        # "failed to read the first frame": no picture in the file.
        logging.info('enrollment take %s has no video stream (%s); reading it as audio', src, str(e)[:80])
        return _from_audio(src, out_wav, max_seconds)


def _from_audio(src, out_wav, max_seconds):
    with mp.AudioFileClip(src) as clip:
        end = min(max_seconds, float(clip.duration or 0))
        if end <= 0:
            return "Clip has zero/unknown duration"
        _export(_subclip(clip, end), out_wav)
        return ""
