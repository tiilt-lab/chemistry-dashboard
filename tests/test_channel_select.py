"""src/common/channel_select.py: the louder microphone, moment by moment."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))

import channel_select as cs  # noqa: E402

SR = 16000


def test_picks_follow_the_louder_channel_with_hysteresis():
    quiet, loud = -40.0, -20.0
    la = np.array([loud, loud, quiet, quiet, loud], dtype=float)
    lb = np.array([quiet, quiet, loud, loud, quiet], dtype=float)
    assert list(cs.choose_channels(la, lb)) == [0, 0, 1, 1, 0]
    # a difference inside the hysteresis band does not switch
    la = np.array([-20.0, -20.0, -20.0]); lb = np.array([-30.0, -18.0, -19.0])
    assert list(cs.choose_channels(la, lb)) == [0, 0, 0]
    la = np.array([-20.0, -20.0]); lb = np.array([-30.0, -15.0])
    assert list(cs.choose_channels(la, lb)) == [0, 1]


def test_select_takes_each_window_from_the_channel_that_has_the_sound():
    rng = np.random.default_rng(1)
    n = 4 * SR
    a = np.zeros(n, dtype=np.float32); b = np.zeros(n, dtype=np.float32)
    # Pat speaks for 2 s (loud on a, faint on b), then Sandy (the reverse)
    pat = rng.standard_normal(2 * SR).astype(np.float32) * 0.3
    sandy = rng.standard_normal(2 * SR).astype(np.float32) * 0.3
    a[:2 * SR] = pat; b[:2 * SR] = pat * 0.1
    a[2 * SR:] = sandy * 0.1; b[2 * SR:] = sandy
    out, picks = cs.select(a, b, SR)
    assert len(out) == n and len(picks) == 16
    assert list(picks[:7]) == [0] * 7 and list(picks[9:]) == [1] * 7
    assert np.allclose(out[SR:int(1.5 * SR)], a[SR:int(1.5 * SR)])
    assert np.allclose(out[3 * SR:int(3.5 * SR)], b[3 * SR:int(3.5 * SR)])


def test_align_and_select_places_the_second_recording_by_the_clock_offset():
    rng = np.random.default_rng(2)
    sound = rng.standard_normal(SR).astype(np.float32) * 0.3
    # a: starts at session 100, one second of sound at 101-102
    a = np.zeros(3 * SR, dtype=np.float32); a[SR:2 * SR] = sound
    # b's clock runs 191 s ahead; its recording starts at "291" on its own
    # clock, i.e. session 100, with the same sound faint at the same moment
    b = np.zeros(3 * SR, dtype=np.float32); b[SR:2 * SR] = sound * 0.1
    start, out, picks = cs.align_and_select(a, 100.0, b, 291.0, 191.0, SR)
    assert start == 100.0 and len(out) == 3 * SR
    assert np.allclose(out[SR:2 * SR], sound)
    # b alone covers the tail when a ended earlier
    start, out, _ = cs.align_and_select(a[:2 * SR], 100.0, b, 291.0, 191.0, SR)
    assert len(out) == 3 * SR and np.allclose(out[int(2.5 * SR):], 0.0)
