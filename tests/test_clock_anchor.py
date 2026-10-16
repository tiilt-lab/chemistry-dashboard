"""src/audio_processing/clock_anchor.py: a pod's clock follows real time."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

from clock_anchor import ClockAnchor, RE_ANCHOR_THRESHOLD, RE_ANCHOR_SUSTAIN  # noqa: E402

FRAME = 0.085   # s of audio per live chunk


def _stream(anchor, start, seconds, audio_at=0.0, rate=1.0, step=FRAME):
    """Feed ``seconds`` of real time from ``start``: audio arrives at ``rate``
    x real time (1 = healthy, 0 = stalled). Returns (total correction, audio
    seconds received)."""
    total, t, audio = 0.0, start, audio_at
    while t < start + seconds - 1e-9:
        t += step
        audio += step * rate
        total += anchor.frame(audio, t)
    return total, audio


def test_a_late_first_frame_moves_the_anchor_by_the_gap():
    # Start message at t=100; the group deals with the mic prompt; audio
    # begins 18 s later. Group 1's Sandy laptop, 2026-10-16.
    a = ClockAnchor(100.0)
    assert a.first_frame(118.0) == 18.0 and a.late_start == 18.0
    # A prompt first frame (within half a second) moves nothing.
    b = ClockAnchor(100.0)
    assert b.first_frame(100.3) == 0.0 and b.late_start == 0.0


def test_healthy_streaming_never_moves_the_clock():
    a = ClockAnchor(0.0)
    a.first_frame(0.0)
    total, _ = _stream(a, 0.0, 600.0)
    assert total == 0.0 and abs(a.drift) < 0.01 and a.corrected == 0.0


def test_a_capture_stall_is_corrected_once_it_has_lasted():
    # Audio stops for 12 s (frames lost, never to arrive) then resumes at
    # the normal rate: the stamps would run 12 s early for ever. The first
    # move comes while the stall lasts, once it has outlived the sustain
    # window; the rest follows once the stream is back and the remaining
    # gap has held just as long.
    a = ClockAnchor(0.0)
    a.first_frame(0.0)
    _stream(a, 0.0, 60.0)
    during, audio = _stream(a, 60.0, 12.0, audio_at=60.0, rate=0.0)   # the stall
    assert RE_ANCHOR_THRESHOLD < during < 12.0
    after, _ = _stream(a, 72.0, 30.0, audio_at=audio)                 # back to normal
    assert 11.5 <= during + after <= 12.5 and 11.5 <= a.corrected <= 12.5
    assert abs(a.drift) < 0.5


def test_server_wires_the_anchor_into_the_stream():
    # Source contract (server.py loads models at import): the anchor is made
    # when the stream starts, fed from every audio frame after the chunk is
    # counted, published with presence and cleared with it.
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "..", "src", "audio_processing", "server.py")) as f:
        src = f.read()
    assert "self.clock = clock_anchor.ClockAnchor(time.time())" in src
    assert src.index("self.enqueue_latest_audio_chunk(asr_data)") < src.index("self._track_clock()")
    assert "self.config.start_offset += late" in src and "self.config.start_offset += delta" in src
    assert "live_presence.set_clock(r, key, clock)" in src and "live_presence.clear_clock(r, key)" in src


def test_a_short_hiccup_that_catches_up_moves_nothing():
    # Frames held back for 6 s then delivered in a burst: real time ran
    # ahead briefly, the burst caught up, nothing should move.
    a = ClockAnchor(0.0)
    a.first_frame(0.0)
    _stream(a, 0.0, 30.0)
    held, _ = _stream(a, 30.0, 6.0, audio_at=30.0, rate=0.0)             # nothing arrives
    burst = a.frame(36.0, 36.0)                                           # 6 s of audio at once
    after, _ = _stream(a, 36.0, 30.0, audio_at=36.0)
    assert held == 0.0 and burst == 0.0 and after == 0.0 and a.corrected == 0.0


def test_a_long_hiccup_is_corrected_then_undone_when_the_audio_arrives():
    # Held back longer than the sustain window, so the clock moves; the
    # burst then shows audio ahead of real time and the move is undone,
    # but never below the original anchor.
    a = ClockAnchor(0.0)
    a.first_frame(0.0)
    _stream(a, 0.0, 30.0)
    moved, _ = _stream(a, 30.0, RE_ANCHOR_SUSTAIN + RE_ANCHOR_THRESHOLD + 3.0, audio_at=30.0, rate=0.0)
    assert moved > RE_ANCHOR_THRESHOLD and a.corrected == moved
    t = 30.0 + RE_ANCHOR_SUSTAIN + RE_ANCHOR_THRESHOLD + 3.0
    a.frame(t, t)                                                         # the held audio lands
    undone, _ = _stream(a, t, RE_ANCHOR_SUSTAIN + 2.0, audio_at=t)
    assert undone < 0 and abs(a.corrected) < 0.5


def test_replayed_backlog_audio_from_the_past_is_left_where_its_samples_put_it():
    # A reconnect: the client reports its backlog in the start message (the
    # service subtracts it from start_offset) and drains it at once, so
    # audio runs "ahead" of real time from the first frame. No correction
    # has been made, so nothing is undone.
    a = ClockAnchor(0.0)
    a.first_frame(0.1)
    total, _ = _stream(a, 0.1, 60.0, audio_at=100.0)   # 100 s of backlog already counted
    assert total == 0.0 and a.corrected == 0.0 and a.drift < -90


def test_snapshot_is_what_the_devices_tab_shows():
    a = ClockAnchor(100.0)
    a.first_frame(118.0)
    assert a.snapshot() == {"drift": 0.0, "corrected": 0.0, "late_start": 18.0}
