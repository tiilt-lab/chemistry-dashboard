"""src/server/join_mode.py: the session's default way of joining."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

import join_mode  # noqa: E402


def test_not_chosen_is_stored_as_null_without_error():
    for raw in (None, ""):
        assert join_mode.normalize(raw) == (None, None)


def test_accepts_audio_and_video_in_any_case():
    assert join_mode.normalize("audio") == ("audio", None)
    assert join_mode.normalize(" Video ") == ("video", None)


def test_rejects_anything_else():
    for raw in ("Videocartoonify", "both", 3, True, ["audio"]):
        mode, err = join_mode.normalize(raw)
        assert mode is None
        assert "audio" in err and "video" in err


def test_effective_opens_on_video_only_when_stored_video():
    assert join_mode.effective("video") == "video"
    for stored in (None, "", "audio", "VIDEO", "garbage"):
        assert join_mode.effective(stored) == "audio"
