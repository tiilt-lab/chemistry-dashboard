"""VidRecorder/WaveRecorder write() must LOG failures, never print them.

Under systemd stdout is discarded, so a print() on a failed write (e.g. a full
disk) vanished silently and chunks were dropped invisibly. WaveRecorder was
fixed to logging.exception; the audio VidRecorder still used print(). These
tests pin that a write failure is logged and never raised (a raise would kill
the recording thread) — for BOTH recorder classes.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

from recorder import VidRecorder, WaveRecorder  # noqa: E402


def _unwritable(tmp_path):
    # A path whose parent directory does not exist -> open(..., "ab") raises.
    return os.path.join(str(tmp_path), "no_such_dir", "clip")


def test_vidrecorder_write_failure_is_logged_not_raised(tmp_path, caplog):
    rec = VidRecorder(_unwritable(tmp_path), 16000, 2, 1, "webm")
    with caplog.at_level(logging.ERROR):
        rec.write(b"\x00\x01")  # must not raise
    assert any(r.levelno >= logging.ERROR for r in caplog.records), \
        "a failed video write must be logged at ERROR (logging.exception), not printed"


def test_wave_recorder_write_failure_is_logged_not_raised(tmp_path, caplog):
    rec = WaveRecorder(_unwritable(tmp_path), 16000, 2, 1)
    with caplog.at_level(logging.ERROR):
        rec.write(b"\x00\x01")  # must not raise
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


def test_recorder_source_has_no_print_on_write_paths():
    with open(os.path.join(os.path.dirname(__file__), "..", "src",
                           "audio_processing", "recorder.py")) as f:
        src = f.read()
    assert "print(" not in src, "recorder.py must use logging, not print (systemd swallows stdout)"
