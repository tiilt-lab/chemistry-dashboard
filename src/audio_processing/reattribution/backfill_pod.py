"""Backfill unassigned transcript rows for one pod from its retained
recording — the minimal end-of-session sweep.

For every row with no speaker_tag: slice the recording at the row's span,
run the SAME closed-world matcher the live path uses (cached prints +
session-style scoring), and push accepted names through the sanctioned
reassign endpoint (never direct DB). Dry-run by default.

Usage:
  BLINC_EMAIL=.. BLINC_PASSWORD=.. ../venv-unified/bin/python3 \
    reattribution/backfill_pod.py --session 366 --device 1078 [--execute]
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS = os.path.join(HERE, "recordings")
SR = 16000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", type=int, required=True)
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--base-url", default="https://nublinc.com")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    import librosa
    import requests
    import config as cf
    cf.initialize()
    from speaker_diarization.pyDiarization import checkFingerprints
    from speechbrain.inference import SpeakerRecognition

    s = requests.Session()
    s.post(args.base_url + "/api/v1/login", json={
        "email": os.environ["BLINC_EMAIL"],
        "password": os.environ["BLINC_PASSWORD"]}, timeout=30).raise_for_status()
    speakers = s.get(args.base_url + "/api/v1/sessions/%d/speakers"
                     % args.session, timeout=60).json()
    roster = sorted({sp["alias"] for sp in speakers
                     if sp["session_device_id"] == args.device and sp["alias"]})
    rows = s.get(args.base_url + "/api/v1/sessions/%d/devices/%d/transcripts"
                 % (args.session, args.device), timeout=60).json()
    wavs = sorted(glob.glob(os.path.join(RECORDINGS, "%d-*_orig.wav" % args.device)))
    if not wavs:
        print("no finalized recording for device %d (still .dat?)" % args.device)
        sys.exit(1)
    print("roster:", roster, "| rows:", len(rows),
          "| unassigned:", sum(1 for r in rows if not r.get("speaker_tag")))

    model = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=os.path.join(HERE, "pretrained_models", "pretrained_ecapa"))
    audio, _ = librosa.load(wavs[-1], sr=SR, mono=True)
    int16 = (audio * 32767).astype(np.int16)
    dur = len(int16) / SR
    max_end = max(int(r["start_time"]) + int(r["length"]) for r in rows)
    offset = max(0, max_end - int(dur))
    print("recording %.0fs, session offset %ds" % (dur, offset))

    fp = {i + 1: {"alias": a, "data": None} for i, a in enumerate(roster)}
    fixed = skipped = 0
    for r in rows:
        if r.get("speaker_tag"):
            continue
        a = (int(r["start_time"]) - offset) * SR
        b = a + max(1, int(r["length"])) * SR
        if a < 0 or b > len(int16):
            skipped += 1
            continue
        alias, _sid = checkFingerprints(int16[int(a):int(b)].tobytes(), fp, model)
        if alias is None:
            skipped += 1
            continue
        print("  row %d [%ss] %r -> %s" %
              (r["id"], r["length"], (r.get("transcript") or "")[:40], alias))
        if args.execute:
            resp = s.post(args.base_url + "/api/v1/transcripts/%d/reassign" % r["id"],
                          json={"alias": alias}, timeout=30)
            if resp.status_code == 200:
                fixed += 1
            else:
                print("    reassign failed:", resp.status_code)
        else:
            fixed += 1
    print(("BACKFILLED %d rows" if args.execute else
           "DRY RUN — %d rows would be backfilled") % fixed,
          "| left unassigned (noise/out-of-range):", skipped)


if __name__ == "__main__":
    main()
