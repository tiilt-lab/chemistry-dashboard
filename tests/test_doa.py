"""DOA / GCC-PHAT regression tests for today's fixes.

- gcc_phat divided by a zero PHAT magnitude on a silent window, producing an
  all-NaN correlation and a garbage bearing.
- calculateDOA used the removed np.fromstring (dead under numpy 2.x) and its
  failure path returned -1 (a truthy, persisted-as-real bearing) instead of
  None.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

from doa.gcc_phat import gcc_phat  # noqa: E402
from doa.doa_respeaker_v2_6mic_array import calculateDOA  # noqa: E402


def test_gcc_phat_silent_window_no_nan():
    # All-zero (silent) input: |R| is zero, the PHAT whitening was 0/0 -> NaN.
    sig = np.zeros(800, dtype=np.int16)
    ref = np.zeros(800, dtype=np.int16)
    tau, cc = gcc_phat(sig, ref, fs=16000, max_tau=0.00027, interp=1)
    assert not np.isnan(cc).any()
    assert np.isfinite(tau)


def test_gcc_phat_identical_signals_zero_delay():
    rng = np.arange(800)
    sig = (1000 * np.sin(2 * np.pi * 5 * rng / 800)).astype(np.int16)
    tau, cc = gcc_phat(sig, sig.copy(), fs=16000, max_tau=0.00027, interp=1)
    assert not np.isnan(cc).any()
    # Same signal on both mics -> no time difference.
    assert abs(tau) < 1e-4


def test_calculate_doa_valid_input_in_range():
    # 6-channel interleaved int16, ~1s. Deterministic content.
    n = 16000
    rng = np.arange(n * 6)
    audio = (500 * np.sin(2 * np.pi * 3 * rng / 6)).astype(np.int16).tobytes()
    d = calculateDOA(0.0, audio, [(0.1, 0.4)], 16000, 6, 2)
    assert d is None or (0.0 <= d < 360.0)


def test_calculate_doa_failure_returns_none_not_minus_one():
    # audio_data=None makes the slice raise; the catch-all must return None,
    # never -1 (which is truthy and gets persisted as a real direction).
    d = calculateDOA(0.0, None, [(0.1, 0.4)], 16000, 6, 2)
    assert d is None
