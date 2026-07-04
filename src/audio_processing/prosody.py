"""Prosodic feature extraction from an utterance's audio (pitch, energy, voicing,
duration). Vocal cues for engagement/uncertainty that complement the text and
facial signals. Pure w.r.t. its inputs (librosa) so it can be unit-tested with
synthetic audio; the audio processor calls compute_prosody per utterance when
[processing] prosody=true.
"""

import numpy as np


def compute_prosody(pcm_int16_bytes, sr=16000):
    """Return prosodic features for an int16 PCM segment, or None if too short.

    Keys: energy_rms, duration_s, voiced_fraction, and (when voiced speech is
    present) pitch_mean_hz / pitch_std_hz / pitch_min_hz / pitch_max_hz.
    """
    import librosa

    x = np.frombuffer(pcm_int16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    if x.size < sr // 10:  # < 100 ms is too short to be meaningful
        return None

    rms = float(np.sqrt(np.mean(x ** 2)))
    out = {
        'energy_rms': round(rms, 5),
        'duration_s': round(len(x) / sr, 3),
    }
    try:
        f0, voiced, _ = librosa.pyin(x, fmin=65, fmax=400, sr=sr)
    except Exception:
        f0, voiced = None, None
    out['voiced_fraction'] = round(
        float(np.mean(voiced)) if voiced is not None and voiced.size else 0.0, 3)
    if f0 is not None:
        voiced_f0 = f0[~np.isnan(f0)]
        if voiced_f0.size:
            out.update({
                'pitch_mean_hz': round(float(np.mean(voiced_f0)), 1),
                'pitch_std_hz': round(float(np.std(voiced_f0)), 1),
                'pitch_min_hz': round(float(np.min(voiced_f0)), 1),
                'pitch_max_hz': round(float(np.max(voiced_f0)), 1),
            })
    return out
