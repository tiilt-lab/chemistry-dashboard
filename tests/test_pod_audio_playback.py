"""The analysis view's audio player (src/server/routes/session.py): the clock
sidecar's moves become the same segment layout the video player uses, so one
session<->media mapping (video-time.js) serves both."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))

# session.py pulls in the whole app; test the pure helper through a scratch
# import of its source, as the other route-helper tests do.

SRC = os.path.join(os.path.dirname(__file__), "..", "src", "server", "routes", "session.py")


def _load_helper(name):
    code = open(SRC).read()
    start = code.index("def %s(" % name)
    end = code.index("\n\n\n", start)
    ns = {}
    exec(code[start:end], ns)
    return ns[name]


_audio_segments = _load_helper("_audio_segments")


def test_no_sidecar_is_one_segment_from_zero():
    assert _audio_segments(None, 120.0) == [{"start": 0.0, "video_start": 0.0, "duration": 120.0}]


def test_no_moves_is_one_segment_at_the_start_offset():
    segs = _audio_segments({"start_offset": 81627.456, "moves": []}, 3519.1)
    assert segs == [{"start": 81627.456, "video_start": 0.0, "duration": 3519.1}]


def test_a_clock_move_splits_the_recording_like_a_disconnect():
    # recording_sidecar.session_time: at audio second 600 the session clock
    # jumps by +219 s (a backlog the live service caught up on)
    info = {"start_offset": 1000.0, "moves": [{"at": 600.0, "delta": 219.0}]}
    segs = _audio_segments(info, 3000.0)
    assert segs == [
        {"start": 1000.0, "video_start": 0.0, "duration": 600.0},
        {"start": 1000.0 + 600.0 + 219.0, "video_start": 600.0, "duration": 2400.0},
    ]


def test_moves_agree_with_the_sidecar_clock():
    # The segment map must reproduce recording_sidecar.session_time at every point.
    import recording_sidecar
    info = {"start_offset": 50.0, "moves": [{"at": 0.256, "delta": 218.976}, {"at": 1200.0, "delta": -3.5}]}
    segs = _audio_segments(info, 2000.0)
    for audio_s in (0.0, 0.3, 100.0, 1199.9, 1200.0, 1500.0, 1999.0):
        seg = [g for g in segs if g["video_start"] <= audio_s and (g["duration"] is None or audio_s < g["video_start"] + g["duration"] + 1e-9)]
        assert seg, audio_s
        g = seg[-1]
        assert abs((g["start"] + (audio_s - g["video_start"])) - recording_sidecar.session_time(info, audio_s)) < 1e-6, audio_s


def test_unknown_duration_leaves_the_last_segment_open():
    segs = _audio_segments({"start_offset": 5.0, "moves": []}, None)
    assert segs == [{"start": 5.0, "video_start": 0.0, "duration": None}]
