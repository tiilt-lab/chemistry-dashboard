"""The better microphone, moment by moment, from a breakout group's two.

Each team's laptop sits on its own side of the table, so whoever is talking
is louder on one of the two recordings. Once the recordings are aligned
(audio_align), a single "best of both" track takes, for every short window,
the channel with the higher level, with a little hysteresis so one voice is
not chopped between microphones at every syllable. The choice per window is
also the cheapest team cue there is: a word that is louder on the Pat
laptop was most likely said by someone on Pat's side.

Pure numpy; callers hand in aligned sample arrays (see align_and_select for
the offset bookkeeping).
"""
import numpy as np

WINDOW_S = 0.25        # s: decision window
HYSTERESIS_DB = 3.0    # the other channel must be this much louder to take over


def window_levels(x, sample_rate, window_s=WINDOW_S):
    """RMS level in dB per window of ``x`` (mono float samples)."""
    x = np.asarray(x, dtype=np.float32)
    hop = max(1, int(round(sample_rate * window_s)))
    n = (len(x) // hop) * hop
    frames = x[:n].reshape(-1, hop).astype(np.float64)
    rms = np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-9
    return 20.0 * np.log10(rms)


def choose_channels(level_a, level_b, hysteresis_db=HYSTERESIS_DB):
    """0 (first channel) or 1 (second) per window: the louder one, switching
    only when the other is ``hysteresis_db`` louder than the current pick."""
    n = min(len(level_a), len(level_b))
    picks = np.zeros(n, dtype=np.int8)
    current = 0 if n == 0 or level_a[0] >= level_b[0] else 1
    for i in range(n):
        other = 1 - current
        mine, theirs = (level_a[i], level_b[i]) if current == 0 else (level_b[i], level_a[i])
        if theirs - mine > hysteresis_db:
            current = other
        picks[i] = current
    return picks


def select(a, b, sample_rate, window_s=WINDOW_S, hysteresis_db=HYSTERESIS_DB):
    """(best_of_both samples, picks per window) for two aligned mono arrays
    of equal length: each window comes from the channel chosen for it, with
    a short crossfade at every switch."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    hop = max(1, int(round(sample_rate * window_s)))
    picks = choose_channels(window_levels(a, sample_rate, window_s), window_levels(b, sample_rate, window_s), hysteresis_db)
    out = np.empty(n, dtype=np.float32)
    fade = min(hop // 4, int(0.01 * sample_rate))
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32) if fade > 1 else None
    for i, pick in enumerate(picks):
        s, e = i * hop, min(n, (i + 1) * hop)
        src, other = (a, b) if pick == 0 else (b, a)
        out[s:e] = src[s:e]
        if ramp is not None and i > 0 and picks[i - 1] != pick and e - s >= fade:
            out[s:s + fade] = other[s:s + fade] * (1.0 - ramp) + src[s:s + fade] * ramp
    tail = len(picks) * hop
    if tail < n:
        out[tail:] = (a if (picks[-1] == 0 if len(picks) else True) else b)[tail:]
    return out, picks


def align_and_select(a, a_start, b, b_start, offset_s, sample_rate, **kw):
    """Place ``b`` (whose first sample sits at session time ``b_start`` on
    its own clock, which runs ``offset_s`` ahead of ``a``'s) against ``a``
    (first sample at ``a_start``), then select. Returns (session_start of
    the output, best_of_both, picks). Where only one recording has sound
    (before the other began, or after it ended) that channel is used."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    # b's clock -> a's clock
    b_start_on_a = float(b_start) - float(offset_s)
    start = min(float(a_start), b_start_on_a)
    end = max(float(a_start) + len(a) / sample_rate, b_start_on_a + len(b) / sample_rate)
    n = int(round((end - start) * sample_rate))
    A = np.zeros(n, dtype=np.float32)
    B = np.zeros(n, dtype=np.float32)
    ia = int(round((float(a_start) - start) * sample_rate))
    ib = int(round((b_start_on_a - start) * sample_rate))
    A[ia:ia + len(a)] = a[:max(0, n - ia)]
    B[ib:ib + len(b)] = b[:max(0, n - ib)]
    out, picks = select(A, B, sample_rate, **kw)
    return start, out, picks
