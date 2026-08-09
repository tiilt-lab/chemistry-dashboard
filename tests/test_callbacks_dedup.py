"""callbacks_common owns the callback-base derivation and the simple POST idiom.

Both trees' callbacks.py had a _callback_base copy (same rsplit, different
config URL) and repeated `requests.post(...); return status==200; except log;
False` in each simple poster. Those live in callbacks_common now
(callback_base / post_json_ok). callbacks.py imports requests, which CI does
not install, so this is a source-level contract.
"""
import os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def _read(*p):
    with open(os.path.join(SRC, *p)) as f:
        return f.read()


def test_common_exposes_the_shared_helpers():
    c = _read("common", "callbacks_common.py")
    assert "def callback_base(url):" in c
    assert "def post_json_ok(url, payload, name):" in c


def test_both_trees_use_the_shared_helpers():
    for tree in ("audio_processing", "video_processing"):
        s = _read(tree, "callbacks.py")
        assert "callbacks_common.callback_base(" in s, f"{tree}: _callback_base must delegate"
        assert "callbacks_common.post_json_ok(" in s, f"{tree}: simple posters must use post_json_ok"
        assert ".rsplit('/', 1)[0]" not in s, f"{tree}: the rsplit base copy must be gone"


def test_simple_posters_no_longer_hand_roll_the_idiom():
    # The audio Tagging/Speaker-metrics and video video-metric/gaze posters
    # must not still contain the raw try/post/status==200 idiom.
    audio = _read("audio_processing", "callbacks.py")
    video = _read("video_processing", "callbacks.py")
    # post_transcripts (audio) legitimately still parses the response body, so
    # we don't ban requests.post outright; we ban the bool idiom specifically.
    assert "return response.status_code == 200\n    except" not in audio
    assert "return response.status_code == 200\n    except" not in video
