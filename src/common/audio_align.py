"""Acoustic alignment of two recordings of the same room.

Both laptops of a breakout group hear the whole table, so the two
recordings are the same sound through two microphones, offset by the
difference between the two laptops' clocks. Cross-correlating their
loudness envelopes finds that offset to a hundredth of a second, in
windows along the session, so a clock that steps (a reconnect, a stall)
is followed where it stepped. Text matching (negotiation_coding) gets a
second or so and needs the words to agree; this needs only sound.

Envelopes are RMS at ENVELOPE_HOP seconds (100 Hz), log-compressed so a
shout and a murmur both leave their shape. What is correlated is the onset
strength (the rises of the envelope): speech is bursty, so the raw envelope
correlates moderately at many lags, while onsets line up sharply at one.
Each window of the reference onsets is correlated against the other
recording's over +-max_lag; the peak is accepted when it is a real
correlation (MIN_PEAK) that stands PEAK_RATIO above the bulk (the 95th
percentile of the absolute correlation) and the window has sound in it.
numpy/scipy only, no I/O: callers hand in sample arrays or an iterable of
blocks, so a 200 MB recording never sits in memory.
"""
import math

import numpy as np
from scipy.signal import correlate

ENVELOPE_HOP = 0.01      # s per envelope sample (100 Hz)
WINDOW_S = 20.0          # s of reference audio per correlation window
STEP_S = 30.0            # s between windows
MAX_LAG_S = 600.0        # s: how far apart the two clocks may be
MIN_PEAK = 0.3           # the peak must be a real correlation of the two onset tracks ...
PEAK_RATIO = 3.0         # ... and stand this far above the 95th percentile of |corr|
MIN_ACTIVITY = 0.05      # a window whose envelope varies less than this is silence


def envelope_of_samples(samples, sample_rate, hop_s=ENVELOPE_HOP):
    """Log RMS envelope of mono float samples at ``hop_s`` resolution."""
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim > 1:
        x = x.mean(axis=1)
    hop = max(1, int(round(sample_rate * hop_s)))
    n = (len(x) // hop) * hop
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    frames = x[:n].reshape(-1, hop)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    return np.log1p(rms * 100.0).astype(np.float32)


def envelope_of_blocks(blocks, sample_rate, hop_s=ENVELOPE_HOP):
    """Same, from an iterable of sample blocks (soundfile.blocks), so the
    whole recording never has to be in memory. Blocks are concatenated
    across hop boundaries exactly."""
    hop = max(1, int(round(sample_rate * hop_s)))
    pieces, carry = [], np.zeros(0, dtype=np.float32)
    for block in blocks:
        b = np.asarray(block, dtype=np.float32)
        if b.ndim > 1:
            b = b.mean(axis=1)
        if len(carry):
            b = np.concatenate([carry, b])
        n = (len(b) // hop) * hop
        if n:
            frames = b[:n].reshape(-1, hop)
            pieces.append(np.log1p(np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1)) * 100.0).astype(np.float32))
        carry = b[n:]
    return np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)


def place_on_timeline(segments, hop_s=ENVELOPE_HOP):
    """One envelope on the session clock from (session_start_s, envelope)
    segments (one per connection of the pod), zeros where nothing was
    recorded. Returns (timeline_start_s, envelope)."""
    segments = [(float(t0), np.asarray(env, dtype=np.float32)) for t0, env in segments if len(env)]
    if not segments:
        return 0.0, np.zeros(0, dtype=np.float32)
    start = min(t0 for t0, _ in segments)
    end = max(t0 + len(env) * hop_s for t0, env in segments)
    out = np.zeros(int(math.ceil((end - start) / hop_s)) + 1, dtype=np.float32)
    for t0, env in segments:
        i = int(round((t0 - start) / hop_s))
        out[i:i + len(env)] = np.maximum(out[i:i + len(env)], env[:len(out) - i])
    return start, out


def onsets(env):
    """Onset strength of an envelope: its rises, zero elsewhere."""
    e = np.asarray(env, dtype=np.float64)
    if len(e) < 2:
        return np.zeros(len(e))
    d = np.diff(e, prepend=e[:1])
    return np.maximum(d, 0.0)


def windowed_offsets(ref_start, ref_env, other_start, other_env, hop_s=ENVELOPE_HOP,
                     window_s=WINDOW_S, step_s=STEP_S, max_lag_s=MAX_LAG_S,
                     peak_ratio=PEAK_RATIO, min_peak=MIN_PEAK, min_activity=MIN_ACTIVITY):
    """[(ref_time_s, lag_s, score)] : for each window of the reference
    envelope with sound in it, the lag by which the other recording's clock
    runs ahead of the reference clock for that sound (other_time -
    ref_time), when the correlation peak is clear."""
    hop = float(hop_s)
    win = int(round(window_s / hop))
    step = int(round(step_s / hop))
    max_lag = int(round(max_lag_s / hop))
    out = []
    if win < 10 or len(ref_env) < win or len(other_env) < win:
        return out
    ref_on, other_on = onsets(ref_env), onsets(other_env)
    for i in range(0, len(ref_env) - win + 1, step):
        if ref_env[i:i + win].std() < min_activity:
            continue
        a = ref_on[i:i + win]
        if a.std() <= 0:
            continue
        a = (a - a.mean()) / a.std()
        # The other envelope's stretch that could contain this window at any
        # lag within +-max_lag, in the other recording's own index space.
        t_ref = ref_start + i * hop
        j_center = int(round((t_ref - other_start) / hop))
        lo = max(0, j_center - max_lag)
        hi = min(len(other_env), j_center + win + max_lag)
        if hi - lo < win:
            continue
        if other_env[lo:hi].std() < min_activity:
            continue
        b = other_on[lo:hi]
        if b.std() <= 0:
            continue
        b = (b - b.mean()) / b.std()
        corr = correlate(b, a, mode='valid', method='fft') / win
        if not len(corr):
            continue
        k = int(np.argmax(corr))
        peak = float(corr[k])
        bulk = float(np.percentile(np.abs(corr), 95)) + 1e-9
        if peak < min_peak or peak / bulk < peak_ratio:
            continue
        # Sample k of the valid correlation aligns a[0] with b[k]: the sound at
        # ref_time t_ref sits at other index lo + k, i.e. other time ...
        t_other = other_start + (lo + k) * hop
        out.append((t_ref, t_other - t_ref, peak / bulk))
    return out
