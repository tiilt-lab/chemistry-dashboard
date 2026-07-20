"""Pilot stage 2: pyannote 3.1 diarization + roster-constrained identity.

Flat ECAPA windowing found no speaker structure in far-field pod audio
(silhouette 0.08 on device 801). pyannote's segmentation model is trained for
exactly this — overlapped, reverberant, multi-speaker meeting audio. This
runs the full pipeline on a retained _orig.wav, then maps the resulting
clusters onto the pod roster with Hungarian assignment + session-bootstrapped
prints (the two pieces cluster_reconcile.py lacks).

Read-only; report + ear-check samples only.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS = os.path.join(HERE, "recordings")
BIOMETRICS = os.path.join(HERE, "audiobiometrics")
TARGET_SR = 16000
ASSIGN_MIN_SIM = 0.25


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
    if not mask.any():
        return x
    return x[: n * frame][np.repeat(mask, frame)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device-id", type=int, required=True)
    ap.add_argument("--session-id", type=int, required=True)
    ap.add_argument("--base-url", default="https://nublinc.com")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    import librosa
    import requests
    import soundfile as sf
    import torch
    from scipy.optimize import linear_sum_assignment
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
    transcripts = s.get(args.base_url + "/api/v1/sessions/%d/devices/%d/transcripts"
                        % (args.session_id, args.device_id), timeout=60).json()
    log("roster: %s | transcript rows: %d" % (roster, len(transcripts)))

    wav_path = sorted(glob.glob(os.path.join(
        RECORDINGS, "%d-*_orig.wav" % args.device_id)))[-1]
    log("recording: %s" % os.path.basename(wav_path))

    # --- diarize ---------------------------------------------------------
    pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    if torch.cuda.is_available():
        pipe.to(torch.device("cuda:0"))
    log("diarizing (pyannote 3.1, %s)..."
        % ("cuda" if torch.cuda.is_available() else "cpu"))
    dia = pipe(wav_path, min_speakers=2, max_speakers=len(roster) + 2)
    # pyannote 4.x wraps the Annotation in a DiarizeOutput
    ann = getattr(dia, "speaker_diarization", dia)
    turns = [(t.start, t.end, lbl) for t, _, lbl in ann.itertracks(yield_label=True)]
    labels = sorted({l for _, _, l in turns})
    secs = {l: round(sum(e - a for a, e, x in turns if x == l), 1) for l in labels}
    log("pyannote clusters: %s" % secs)

    # --- identity: cluster embeddings vs roster prints -------------------
    model = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=os.path.join(HERE, "pretrained_models", "pretrained_ecapa"))
    audio, _ = librosa.load(wav_path, sr=TARGET_SR, mono=True)

    prints = {}
    for alias in roster:
        p = os.path.join(BIOMETRICS, alias + ".wav")
        if os.path.isfile(p):
            x, _ = librosa.load(p, sr=TARGET_SR, mono=True)
            prints[alias] = embed(model, energy_mask(x.astype(np.float32), TARGET_SR))

    def cluster_embedding(label, budget=60.0):
        # longest turns first, up to `budget` seconds of that cluster's audio
        mine = sorted([t for t in turns if t[2] == label],
                      key=lambda t: -(t[1] - t[0]))
        take, acc = [], 0.0
        for a, e, _ in mine:
            take.append(audio[int(a * TARGET_SR):int(e * TARGET_SR)])
            acc += e - a
            if acc >= budget:
                break
        return embed(model, np.concatenate(take)) if take else None

    cents = {l: cluster_embedding(l) for l in labels}
    cents = {l: v for l, v in cents.items() if v is not None}

    def assign(prints_now):
        names = sorted(prints_now)
        cl = sorted(cents)
        C = np.array([[float(np.dot(cents[c], prints_now[n])) for n in names]
                      for c in cl])
        # Pass 1: optimal 1:1 (each person claims their best-supported cluster)
        rows, cols = linear_sum_assignment(-C)
        mapping = {}
        for i, j in zip(rows, cols):
            mapping[cl[i]] = names[j] if C[i, j] >= ASSIGN_MIN_SIM else None
        # Pass 2: pyannote often splits one voice across clusters — let
        # leftover clusters join an already-assigned person if the voice
        # matches (many-to-one, still similarity-gated).
        for i, c in enumerate(cl):
            if mapping.get(c) is None:
                j = int(np.argmax(C[i]))
                if C[i, j] >= ASSIGN_MIN_SIM:
                    mapping[c] = names[j]
        # Record sims for EVERY cluster so unassigned ones are explainable.
        detail = {c: {"assigned": mapping.get(c),
                      "sims": {n: round(float(C[i, k]), 3)
                               for k, n in enumerate(names)}}
                  for i, c in enumerate(cl)}
        return mapping, detail

    mapping, detail = assign(prints)
    log("initial: %s" % mapping)
    # bootstrap: re-print each assigned speaker from their cluster's audio
    boot = dict(prints)
    for l, alias in mapping.items():
        if alias:
            boot[alias] = cents[l]
    mapping2, detail2 = assign(boot)
    log("bootstrapped: %s" % mapping2)

    # --- relabel transcript rows by overlap with diarized turns ----------
    dur = len(audio) / TARGET_SR
    max_end = max(int(t["start_time"]) + int(t["length"]) for t in transcripts)
    offset = max(0, max_end - int(dur))
    rows_out, old_secs, new_secs, changed = [], {}, {}, 0
    for t in transcripts:
        a = int(t["start_time"]) - offset
        b = a + int(t["length"])
        if a < 0:
            continue
        ov = {}
        for ta, te, l in turns:
            o = min(b, te) - max(a, ta)
            if o > 0:
                ov[l] = ov.get(l, 0) + o
        best = max(ov, key=ov.get) if ov else None
        new_tag = mapping2.get(best) if best else None
        old = t.get("speaker_tag")
        old_secs[old] = old_secs.get(old, 0) + t["length"]
        new_secs[new_tag or "(abstain)"] = \
            new_secs.get(new_tag or "(abstain)", 0) + t["length"]
        if new_tag != old:
            changed += 1
        rows_out.append({"transcript_id": t["id"], "start": t["start_time"],
                         "old": old, "new": new_tag,
                         "cluster": best, "text": (t.get("transcript") or "")[:60]})

    # ear-check samples: 3 longest turns per cluster
    for l in labels:
        mine = sorted([t for t in turns if t[2] == l],
                      key=lambda t: -(t[1] - t[0]))[:3]
        for i, (a, e, _) in enumerate(mine):
            sf.write(os.path.join(args.out, "%s_%s_sample%d_t%ds.wav"
                     % (l, mapping2.get(l) or "unassigned", i, int(a))),
                     audio[int(a * TARGET_SR):int(min(e, a + 15) * TARGET_SR)],
                     TARGET_SR)

    report = {
        "device_id": args.device_id, "session_id": args.session_id,
        "engine": "pyannote/speaker-diarization-3.1",
        "cluster_seconds": secs,
        "assignment_initial": detail,
        "assignment_bootstrapped": detail2,
        "seconds_by_old_tag": old_secs,
        "seconds_by_new_tag": new_secs,
        "segments_relabeled": changed,
        "rows": rows_out,
    }
    with open(os.path.join(args.out, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    log("\n=== PYANNOTE PILOT device %d ===" % args.device_id)
    log("old: %s" % old_secs)
    log("new: %s" % new_secs)
    log("relabeled %d rows; report in %s" % (changed, args.out))


if __name__ == "__main__":
    main()
