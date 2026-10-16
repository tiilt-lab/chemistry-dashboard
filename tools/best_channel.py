#!/usr/bin/env python
"""Best-of-both track for a breakout group from its two pods' recordings.

    python tools/best_channel.py <pod_a_redu.wav> <pod_b_redu.wav> <out.wav> [--offset S]

Both recordings must carry a clock sidecar (<recording>.clock.json, written
by the audio service since 2026-10-16); the offset between the two laptops'
clocks is then measured from the sound (audio_align) unless --offset is
given. The output is 16 kHz mono: for every quarter second the louder of
the two microphones (channel_select), which is also the better input for a
post-hoc transcription of the whole table.
"""
import argparse
import os
import statistics
import sys
import wave

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "common"))
import audio_align  # noqa: E402
import channel_select  # noqa: E402
import recording_sidecar  # noqa: E402


def read_mono16(path):
    with wave.open(path, "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise SystemExit("%s: need a 16-bit mono recording (the _redu.wav)" % path)
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return x, sr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pod_a"); ap.add_argument("pod_b"); ap.add_argument("out")
    ap.add_argument("--offset", type=float, default=None, help="seconds pod_b's clock runs ahead of pod_a's (measured when omitted)")
    args = ap.parse_args()
    a, sr = read_mono16(args.pod_a)
    b, sr_b = read_mono16(args.pod_b)
    if sr != sr_b:
        raise SystemExit("sample rates differ")
    info_a, info_b = recording_sidecar.read(args.pod_a), recording_sidecar.read(args.pod_b)
    if info_a is None or info_b is None:
        raise SystemExit("both recordings need a clock sidecar (.clock.json)")
    a_start, b_start = recording_sidecar.session_time(info_a, 0.0), recording_sidecar.session_time(info_b, 0.0)
    offset = args.offset
    if offset is None:
        ea, eb = audio_align.envelope_of_samples(a, sr), audio_align.envelope_of_samples(b, sr)
        found = audio_align.windowed_offsets(a_start, ea, b_start, eb)
        if len(found) < 3:
            raise SystemExit("could not align the two recordings from their sound (%d windows)" % len(found))
        offset = statistics.median(lag for _, lag, _ in found)
        print("offset measured from %d windows: %+.3f s (pod_b ahead of pod_a)" % (len(found), offset))
    start, out, picks = channel_select.align_and_select(a, a_start, b, b_start, offset, sr)
    wavfile.write(args.out, sr, (np.clip(out, -1.0, 1.0) * 32767).astype(np.int16))
    recording_sidecar.write(args.out, {"start_offset": round(start, 3), "moves": [], "best_of": [args.pod_a, args.pod_b],
                                       "offset": round(offset, 3), "picked_b_share": round(float(np.mean(picks)), 3)})
    print("wrote %s: %.1f min, pod_b chosen for %.0f%% of windows" % (args.out, len(out) / sr / 60, 100 * float(np.mean(picks))))


if __name__ == "__main__":
    main()
