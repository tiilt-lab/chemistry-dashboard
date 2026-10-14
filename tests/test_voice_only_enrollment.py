"""Voice-only enrollment: a student without a camera (or who would rather not
be filmed) enrols a voice print alone. The sign-up form offers the choice,
the page then opens only the microphone and talks only to the audio service,
and the audio service opens the audio-only take as sound rather than video."""
import os
import shutil
import subprocess
import sys
import wave

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))

import enrollment_media  # noqa: E402

FFMPEG = shutil.which("ffmpeg")


def _read(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return f.read()


def _take(tmp_path, name, video, seconds=4):
    """A MediaRecorder-like take: Opus in WebM or AAC in MP4, with or
    without a picture."""
    if not FFMPEG:
        pytest.skip("ffmpeg not installed")
    webm = name.endswith(".webm")
    args = [FFMPEG, "-loglevel", "error", "-y"]
    if video:
        args += ["-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=%d" % seconds]
    args += ["-f", "lavfi", "-i", "sine=frequency=220:duration=%d" % seconds, "-ac", "1"]
    args += ["-c:a", "libopus"] if webm else ["-c:a", "aac"]
    if video:
        args += ["-c:v", "libvpx" if webm else "libx264", "-pix_fmt", "yuv420p"]
    args += ["-shortest", str(tmp_path / name)]
    try:
        subprocess.run(args, check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.skip("ffmpeg could not make the fixture: %s" % e)
    return str(tmp_path / name)


def _wav_seconds(path):
    with wave.open(path) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        return w.getnframes() / w.getframerate()


@pytest.mark.parametrize("name", ["take.webm", "take.mp4"])
def test_voice_only_take_becomes_the_16k_mono_wav(tmp_path, name):
    src = _take(tmp_path, name, video=False)
    out = str(tmp_path / "print.wav")
    assert enrollment_media.extract_audio(src, out, voice_only=True) == ""
    assert abs(_wav_seconds(out) - 4) < 0.3


def test_a_take_with_a_picture_still_extracts(tmp_path):
    src = _take(tmp_path, "take.webm", video=True)
    out = str(tmp_path / "print.wav")
    assert enrollment_media.extract_audio(src, out, voice_only=False) == ""
    assert abs(_wav_seconds(out) - 4) < 0.3


def test_an_untagged_audio_only_take_is_read_as_sound(tmp_path):
    # A sign-up page from before the option sends no flag; the video reader
    # fails on the missing picture and the sound reader takes over.
    src = _take(tmp_path, "take.webm", video=False)
    out = str(tmp_path / "print.wav")
    assert enrollment_media.extract_audio(src, out, voice_only=False) == ""
    assert abs(_wav_seconds(out) - 4) < 0.3


def test_the_take_is_capped(tmp_path):
    src = _take(tmp_path, "take.webm", video=False, seconds=5)
    out = str(tmp_path / "print.wav")
    assert enrollment_media.extract_audio(src, out, voice_only=True, max_seconds=2) == ""
    assert _wav_seconds(out) <= 2.1


def test_audio_server_uses_the_shared_extractor_and_reads_the_flag():
    s = _read("src", "audio_processing", "server.py")
    assert "self.voice_only = bool(data.get('voice_only'))" in s
    assert "enrollment_media.extract_audio(src, audio_fingerprint_file," in s
    assert "mp.VideoFileClip" not in s and "import moviepy" not in s


def test_signup_form_offers_voice_only_and_passes_the_choice():
    page = _read("frontend", "src", "profile-creation", "html-pages.jsx")
    assert 'name="enrollMode"' in page and 'value="voice"' in page and 'value="both"' in page
    assert """(document.querySelector('input[name="enrollMode"]:checked') || {}).value === "voice",""" in page
    assert "voiceOnly={props.voiceOnly === true}" in page


def test_signup_component_keeps_the_video_service_out_of_a_voice_only_enrollment():
    comp = _read("frontend", "src", "profile-creation", "profile-creation-component.jsx")
    assert "constraint.video = voiceOnly ? false : {" in comp
    # the video socket is only opened with a camera
    opened = comp[comp.index("audiows.current = new WebSocket("):comp.index("connect_video_websocket_processor_service();")]
    assert "if (!voiceOnly) {" in opened
    # the audio service is told, and the take goes to the video service only when it exists
    assert "voice_only: voiceOnly" in comp
    assert "if (videows.current !== null) videows.current.send(blob)" in comp
    assert "if (videows.current === null && !voiceOnly) {" in comp
    # every "both services" gate counts the missing one as done
    for name in ("videoSocketReady", "videoAuthed", "videoDone"):
        assert "const %s = voiceOnly || " % name in comp
    assert 'mimetype.startsWith("audio/")' in comp
    assert '"audio/webm;codecs=opus"' in comp and '"audio/mp4"' in comp


def test_recording_coach_records_sound_only_without_a_camera():
    coach = _read("frontend", "src", "profile-creation", "recording-coach.jsx")
    assert "video: voiceOnly ? false : {" in coach
    assert "if (!voiceOnly) startVisionLoop();" in coach
    assert "if (!voiceOnly && videoRef.current) {" in coach
    assert "const VOICE_MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4;codecs=mp4a.40.2', 'audio/mp4'];" in coach
    assert "supportedMime(voiceOnly ? VOICE_MIME_TYPES : VIDEO_MIME_TYPES)" in coach
    assert "VOICE_SCRIPT" in coach and "Keep your face toward the camera" not in coach.split("const VOICE_SCRIPT")[1]
