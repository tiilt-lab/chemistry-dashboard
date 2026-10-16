"""src/common/audio_align.py + recording_sidecar.py: two microphones, one clock."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))

import audio_align as aa  # noqa: E402
import recording_sidecar as sidecar  # noqa: E402

SR = 16000


def speech_like(seconds, seed=1):
    """Bursts of band-limited noise with pauses: a table talking."""
    rng = np.random.default_rng(seed)
    x = np.zeros(int(seconds * SR), dtype=np.float32)
    t = 0.0
    while t < seconds:
        burst = rng.uniform(0.4, 2.5)
        gap = rng.uniform(0.2, 1.5)
        s, e = int(t * SR), min(len(x), int((t + burst) * SR))
        if e > s:
            x[s:e] = (rng.standard_normal(e - s) * rng.uniform(0.05, 0.4)).astype(np.float32)
        t += burst + gap
    return x


def second_mic(x, shift_s, gain=0.4, noise=0.01, seed=2):
    """The same sound heard from the other side of the table, ``shift_s``
    later on that laptop's clock (positive = its clock runs ahead)."""
    rng = np.random.default_rng(seed)
    y = np.zeros(len(x) + int(abs(shift_s) * SR) + SR, dtype=np.float32)
    off = int(round(shift_s * SR)) if shift_s > 0 else 0
    y[off:off + len(x)] += x * gain
    y += (rng.standard_normal(len(y)) * noise).astype(np.float32)
    return y


def test_envelope_from_blocks_matches_envelope_from_samples():
    x = speech_like(12.0)
    whole = aa.envelope_of_samples(x, SR)
    blocks = [x[i:i + 7001] for i in range(0, len(x), 7001)]      # odd block size crosses hops
    assert np.allclose(aa.envelope_of_blocks(blocks, SR), whole, atol=1e-5)
    assert len(whole) == int(12.0 / aa.ENVELOPE_HOP)


def test_timeline_places_segments_with_silence_between():
    env1 = np.ones(100, dtype=np.float32)          # 1 s from t=10
    env2 = 2 * np.ones(50, dtype=np.float32)       # 0.5 s from t=13
    start, tl = aa.place_on_timeline([(10.0, env1), (13.0, env2)])
    assert start == 10.0
    assert tl[0] == 1.0 and tl[99] == 1.0 and tl[150] == 0.0 and tl[300] == 2.0 and tl[349] == 2.0
    assert aa.place_on_timeline([])[1].size == 0


def test_windowed_offsets_recover_a_constant_shift_to_a_hundredth():
    x = speech_like(120.0)
    y = second_mic(x, 191.0)
    ea, eb = aa.envelope_of_samples(x, SR), aa.envelope_of_samples(y, SR)
    found = aa.windowed_offsets(0.0, ea, 0.0, eb)
    assert len(found) >= 3
    lags = [lag for _, lag, _ in found]
    assert all(abs(lag - 191.0) <= 0.015 for lag in lags), lags


def test_windowed_offsets_follow_a_step_and_skip_silence():
    x = speech_like(180.0)
    # The other laptop's clock runs 18 s ahead for the first minute and 6 s
    # ahead after a 12 s stall at t=60: its recording holds the first minute
    # 18 s late and the rest 6 s late. Windows start every 30 s.
    first = second_mic(x[:60 * SR], 18.0)
    second = second_mic(x[60 * SR:], 6.0, seed=3)
    y = np.zeros(int(200 * SR), dtype=np.float32)
    y[:len(first)] += first
    y[60 * SR:60 * SR + len(second)] += second[:len(y) - 60 * SR]
    # 30 s of silence on the reference side yields no window there
    x[120 * SR:150 * SR] = 0.0
    found = aa.windowed_offsets(0.0, aa.envelope_of_samples(x, SR), 0.0, aa.envelope_of_samples(y, SR))
    by_time = {round(t): round(lag, 2) for t, lag, _ in found}
    assert any(t < 60 and abs(l - 18.0) <= 0.05 for t, l in by_time.items()), by_time
    assert any(60 <= t < 120 and abs(l - 6.0) <= 0.05 for t, l in by_time.items()), by_time
    assert not any(120 <= t < 150 for t in by_time), by_time


def test_unrelated_recordings_yield_few_or_no_windows():
    x = speech_like(120.0, seed=5)
    z = speech_like(120.0, seed=9) * 0.5
    found = aa.windowed_offsets(0.0, aa.envelope_of_samples(x, SR), 0.0, aa.envelope_of_samples(z, SR))
    assert len(found) <= 1


def test_sidecar_round_trip_and_session_time(tmp_path):
    wav = str(tmp_path / "1419-abc (Fri Oct 16 14:08:54 2026)_redu.wav")
    info = {"processing_key": "1419-abc", "start_offset": 63729.4, "sample_rate": 16000, "channels": 1,
            "moves": [{"at": 0.0, "delta": 18.0}, {"at": 600.0, "delta": -12.0}]}
    sidecar.write(wav, info)
    assert os.path.exists(str(tmp_path / "1419-abc (Fri Oct 16 14:08:54 2026)_redu.clock.json"))
    assert sidecar.read(wav) == info
    assert sidecar.read(wav.replace(".wav", ".dat")) == info
    assert sidecar.session_time(info, 0.0) == 63729.4 + 18.0
    assert sidecar.session_time(info, 599.9) == 63729.4 + 599.9 + 18.0
    assert abs(sidecar.session_time(info, 650.0) - (63729.4 + 650.0 + 18.0 - 12.0)) < 1e-6
    assert sidecar.read(str(tmp_path / "nothing_here.wav")) is None
    (tmp_path / "bad.clock.json").write_text("not json")
    assert sidecar.read(str(tmp_path / "bad.wav")) is None
    (tmp_path / "old.clock.json").write_text(json.dumps({"no": "start_offset"}))
    assert sidecar.read(str(tmp_path / "old.wav")) is None
