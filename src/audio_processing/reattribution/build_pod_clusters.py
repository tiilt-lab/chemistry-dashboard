"""Stage 1 of cross-session linking: diarize one pod and emit a compact
per-cluster fingerprint artifact.

For each retained _orig.wav: pyannote 3.1 clusters -> a mean ECAPA embedding
+ duration per cluster, plus the pod roster and any usable enrolled prints.
These small artifacts (no audio) are what link_chains.py consumes, so the
expensive GPU diarization runs once per pod and the linking is cheap to
iterate.

Usage (writes <out>/pod_<device>.json):
  ../venv-unified/bin/python3 reattribution/build_pod_clusters.py \
      --device-id 923 --session-id 292 --out <dir>
"""
import argparse
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS = os.path.join(HERE, "recordings")
BIOMETRICS = os.path.join(HERE, "audiobiometrics")
TARGET_SR = 16000


def log(m):
    print(m, flush=True)


def embed(model, x):
    import torch
    with torch.no_grad():
        e = model.encode_batch(torch.tensor(np.ascontiguousarray(x)))
    v = e[0, 0].detach().cpu().numpy()
    return v / (np.linalg.norm(v) + 1e-9)


def energy_mask(x, sr, frame_seconds=0.03):
    frame = max(1, int(sr * frame_seconds))
    n = len(x) // frame
    if n == 0:
        return x
    frames = x[: n * frame].reshape(n, frame)
    rms = np.sqrt((frames * frames).mean(axis=1))
    mask = rms > max(np.percentile(rms, 20) * 3.0, 0.008)
    return x[: n * frame][np.repeat(mask, frame)] if mask.any() else x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device-id", type=int, required=True)
    ap.add_argument("--session-id", type=int, required=True)
    ap.add_argument("--base-url", default="https://nublinc.com")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "pod_%d.json" % args.device_id)

    import librosa
    import requests
    import torch
    from pyannote.audio import Pipeline
    from speechbrain.inference import SpeakerRecognition

    s = requests.Session()
    s.post(args.base_url + "/api/v1/login", json={
        "email": os.environ["BLINC_EMAIL"],
        "password": os.environ["BLINC_PASSWORD"]}, timeout=30).raise_for_status()
    speakers = s.get(args.base_url + "/api/v1/sessions/%d/speakers"
                     % args.session_id, timeout=60).json()
    roster = sorted({sp["alias"] for sp in speakers
                     if sp["session_device_id"] == args.device_id and sp["alias"]})

    wav_path = sorted(glob.glob(os.path.join(
        RECORDINGS, "%d-*_orig.wav" % args.device_id)))[-1]
    log("pod %d | roster %s | %s" % (args.device_id, roster,
                                     os.path.basename(wav_path)))

    pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    if torch.cuda.is_available():
        pipe.to(torch.device("cuda:0"))
    dia = pipe(wav_path, min_speakers=2, max_speakers=len(roster) + 2)
    ann = getattr(dia, "speaker_diarization", dia)
    turns = [(t.start, t.end, lbl) for t, _, lbl in ann.itertracks(yield_label=True)]

    model = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=os.path.join(HERE, "pretrained_models", "pretrained_ecapa"))
    audio, _ = librosa.load(wav_path, sr=TARGET_SR, mono=True)

    clusters = {}
    for label in sorted({l for _, _, l in turns}):
        mine = sorted([t for t in turns if t[2] == label], key=lambda t: -(t[1] - t[0]))
        dur = sum(e - a for a, e, _ in mine)
        take, acc = [], 0.0
        for a, e, _ in mine:
            take.append(audio[int(a * TARGET_SR):int(e * TARGET_SR)])
            acc += e - a
            if acc >= 60:
                break
        if take:
            clusters[label] = {"seconds": round(dur, 1),
                               "embedding": embed(model, np.concatenate(take)).tolist()}

    # usable enrolled prints (so the linker can anchor from them where they exist)
    prints = {}
    for alias in roster:
        p = os.path.join(BIOMETRICS, alias + ".wav")
        if os.path.isfile(p):
            x, _ = librosa.load(p, sr=TARGET_SR, mono=True)
            prints[alias] = embed(model, energy_mask(x.astype(np.float32), TARGET_SR)).tolist()

    json.dump({"device_id": args.device_id, "session_id": args.session_id,
               "roster": roster, "clusters": clusters, "enrolled_prints": prints},
              open(out_path, "w"))
    log("wrote %s (%d clusters, %d prints)" % (out_path, len(clusters), len(prints)))


if __name__ == "__main__":
    main()
