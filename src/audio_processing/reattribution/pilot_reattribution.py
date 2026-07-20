"""Offline re-attribution pilot.

Relabels one pod's existing transcript segments by re-embedding the retained
_orig.wav with the same ECAPA model the pipeline uses, clustering globally,
then assigning clusters to the pod ROSTER (not all 172 students) with
abstention. Read-only: writes a JSON/text report + per-cluster audio samples
for human ear-verification. No database writes.

Why segment-level relabeling instead of full re-diarization: Whisper's
segment boundaries are trustworthy — it's the identity that's wrong — and
transcript rows are the unit any future write-back needs.

Run inside venv-unified:
  BLINC_EMAIL=... BLINC_PASSWORD=... \
  ../venv-unified/bin/python3 reattribution/pilot_reattribution.py \
      --device-id 923 --session-id 292 --out /tmp/pilot923
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/audio_processing")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS = os.path.join(HERE, "recordings")
BIOMETRICS = os.path.join(HERE, "audiobiometrics")

TARGET_SR = 16000          # ECAPA's training rate; everything is resampled
MIN_SEGMENT_SECONDS = 0.6  # too short to embed meaningfully
ASSIGN_MIN_SIM = 0.25      # below: cluster stays unassigned ("abstain")
ASSIGN_MIN_MARGIN = 0.03   # best must beat runner-up by this


def log(msg):
    print(msg, flush=True)


def api(session, base, path):
    r = session.get(base + path, timeout=60)
    r.raise_for_status()
    return r.json()


def load_mono_16k(path):
    import librosa
    x, _ = librosa.load(path, sr=TARGET_SR, mono=True)
    return x.astype(np.float32)


def energy_mask(x, sr, frame_seconds=0.03):
    frame = max(1, int(sr * frame_seconds))
    n = len(x) // frame
    if n == 0:
        return x
    frames = x[: n * frame].reshape(n, frame)
    rms = np.sqrt((frames * frames).mean(axis=1))
    floor = np.percentile(rms, 20)
    mask = rms > max(floor * 3.0, 0.008)
    if not mask.any():
        return x
    return x[: n * frame][np.repeat(mask, frame)]


def embed(model, x):
    import torch
    with torch.no_grad():
        e = model.encode_batch(torch.tensor(np.ascontiguousarray(x)))
    v = e[0, 0].detach().cpu().numpy()
    return v / (np.linalg.norm(v) + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device-id", type=int, required=True)
    ap.add_argument("--session-id", type=int, required=True)
    ap.add_argument("--base-url", default="https://nublinc.com")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    import requests
    import soundfile as sf
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import silhouette_score
    from scipy.optimize import linear_sum_assignment
    from speechbrain.inference import SpeakerRecognition

    # --- metadata via the API (no direct DB access) ---------------------
    s = requests.Session()
    r = s.post(args.base_url + "/api/v1/login", json={
        "email": os.environ["BLINC_EMAIL"],
        "password": os.environ["BLINC_PASSWORD"]}, timeout=30)
    r.raise_for_status()
    speakers = api(s, args.base_url,
                   "/api/v1/sessions/%d/speakers" % args.session_id)
    roster = sorted({sp["alias"] for sp in speakers
                     if sp["session_device_id"] == args.device_id and sp["alias"]})
    transcripts = api(s, args.base_url,
                      "/api/v1/sessions/%d/devices/%d/transcripts"
                      % (args.session_id, args.device_id))
    log("roster: %s | transcript rows: %d" % (roster, len(transcripts)))

    wavs = glob.glob(os.path.join(RECORDINGS, "%d-*_orig.wav" % args.device_id))
    if not wavs:
        log("FATAL: no retained recording for device %d" % args.device_id)
        sys.exit(1)
    wav_path = sorted(wavs)[-1]
    log("recording: %s" % os.path.basename(wav_path))

    model = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=os.path.join(HERE, "pretrained_models", "pretrained_ecapa"))

    # --- roster voice prints, re-embedded at a common rate --------------
    prints = {}
    for alias in roster:
        p = os.path.join(BIOMETRICS, alias + ".wav")
        if not os.path.isfile(p):
            log("no enrollment wav for %s" % alias)
            continue
        x = load_mono_16k(p)
        prints[alias] = embed(model, energy_mask(x, TARGET_SR))
    log("prints: %s" % sorted(prints))

    # --- embed every transcript segment ---------------------------------
    audio = load_mono_16k(wav_path)
    # start_time is session-relative; the recording starts later. Align by
    # pinning the LAST utterance's end to the end of the audio (there is at
    # most a few seconds of trailing silence), clamped at zero.
    duration = len(audio) / TARGET_SR
    max_end = max(int(t["start_time"]) + int(t["length"]) for t in transcripts)
    offset = max(0, max_end - int(duration))
    log("time base: session-relative; recording offset %ds (audio %.0fs)"
        % (offset, duration))
    # Long Whisper segments in a fast 4-way discussion MIX speakers, which
    # smears segment-level embeddings into an unclusterable blob. So: embed
    # short windows inside each segment, cluster the windows, and give each
    # transcript row the majority identity of its windows.
    WIN, HOP = 2.0, 1.0
    segs, windows = [], []
    for t in transcripts:
        a = (int(t["start_time"]) - offset) * TARGET_SR
        b = a + int(t["length"]) * TARGET_SR
        if a < 0:
            continue
        clip = audio[a:b]
        if len(clip) < MIN_SEGMENT_SECONDS * TARGET_SR:
            continue
        seg = {
            "id": t["id"], "start": t["start_time"], "length": t["length"],
            "old_tag": t.get("speaker_tag"), "text": (t.get("transcript") or "")[:60],
            "clip": (a, b), "win_idx": [],
        }
        pos = 0
        step = int(HOP * TARGET_SR)
        wlen = int(WIN * TARGET_SR)
        while pos + wlen <= len(clip) or (pos == 0 and len(clip) >= MIN_SEGMENT_SECONDS * TARGET_SR):
            w = clip[pos:pos + wlen] if pos + wlen <= len(clip) else clip
            seg["win_idx"].append(len(windows))
            windows.append(embed(model, w))
            pos += step
            if pos + wlen > len(clip) and pos > 0:
                break
        segs.append(seg)
    log("embedded %d/%d segments as %d windows"
        % (len(segs), len(transcripts), len(windows)))
    if len(segs) < 4:
        log("FATAL: too few segments")
        sys.exit(1)

    X = np.stack(windows)

    # --- global clustering of windows; k chosen by silhouette -----------
    best_k, best_score, best_labels = None, -2, None
    for k in range(2, min(len(roster) + 3, len(windows) - 1, 10)):
        labels = AgglomerativeClustering(
            n_clusters=k, metric="cosine", linkage="average").fit_predict(X)
        score = silhouette_score(X, labels, metric="cosine")
        log("  k=%d silhouette=%.3f" % (k, score))
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels
    labels = best_labels
    log("chose k=%d (silhouette %.3f)" % (best_k, best_score))
    if best_score < 0.15:
        log("WARNING: weak cluster structure — far-field/overlapped audio; "
            "treat assignments as low-confidence")

    def centroids(lbls):
        out = {}
        for c in sorted(set(lbls)):
            v = X[lbls == c].mean(axis=0)
            out[c] = v / (np.linalg.norm(v) + 1e-9)
        return out

    # --- roster-constrained assignment (Hungarian, with abstention) -----
    def assign(cents, prints_now):
        names = sorted(prints_now)
        C = np.zeros((len(cents), len(names)))
        cl = sorted(cents)
        for i, c in enumerate(cl):
            for j, n in enumerate(names):
                C[i, j] = float(np.dot(cents[c], prints_now[n]))
        rows, cols = linear_sum_assignment(-C)
        mapping, detail = {}, {}
        for i, j in zip(rows, cols):
            sims = sorted(C[i], reverse=True)
            margin = sims[0] - sims[1] if len(sims) > 1 else 1.0
            best = C[i, j]
            ok = best >= ASSIGN_MIN_SIM and \
                (best == sims[0] and margin >= ASSIGN_MIN_MARGIN or best >= 0.45)
            mapping[cl[i]] = names[j] if ok else None
            detail[cl[i]] = {
                "assigned": names[j] if ok else None,
                "sims": {n: round(float(C[i, k]), 3) for k, n in enumerate(names)},
            }
        return mapping, detail

    cents = centroids(labels)
    mapping, detail = assign(cents, prints)
    log("initial assignment: %s" % {int(k): v for k, v in mapping.items()})

    # Segment purity: fraction of a segment's windows in its majority cluster.
    def seg_majority(seg):
        votes = [labels[i] for i in seg["win_idx"]]
        if not votes:
            return None, 0.0
        top = max(set(votes), key=votes.count)
        return top, votes.count(top) / len(votes)

    # --- bootstrap: rebuild prints from the session's own audio ---------
    # Weak 6-second enrollments only need to SEED the mapping; the session
    # gives each assigned speaker minutes of PURE (>=80% one-cluster)
    # segments to re-print from.
    boot_prints = dict(prints)
    for c, alias in mapping.items():
        if alias is None:
            continue
        pure = [g for g in segs
                if seg_majority(g)[0] == c and seg_majority(g)[1] >= 0.8]
        pure.sort(key=lambda g: -g["length"])
        take, acc = [], 0
        for g in pure:
            take.append(audio[g["clip"][0]:g["clip"][1]])
            acc += g["length"]
            if acc >= 30:
                break
        if take:
            boot_prints[alias] = embed(model, energy_mask(
                np.concatenate(take), TARGET_SR))
    mapping2, detail2 = assign(cents, boot_prints)
    log("bootstrapped assignment: %s" % {int(k): v for k, v in mapping2.items()})

    # --- results: per-segment majority vote over window clusters --------
    old_secs, new_secs = {}, {}
    changed = 0
    rows = []
    for g in segs:
        c, purity = seg_majority(g)
        new_tag = mapping2.get(c) if purity >= 0.6 else None
        old_secs[g["old_tag"]] = old_secs.get(g["old_tag"], 0) + g["length"]
        key = new_tag or "(abstain)"
        new_secs[key] = new_secs.get(key, 0) + g["length"]
        if new_tag != g["old_tag"]:
            changed += 1
        rows.append({"transcript_id": g["id"], "start": g["start"],
                     "length": g["length"], "old": g["old_tag"],
                     "new": new_tag, "cluster": int(c) if c is not None else None,
                     "purity": round(purity, 2), "text": g["text"]})

    # sample clips per cluster (purest segments) for ear-verification
    for c in sorted(set(labels)):
        members = sorted(
            [g for g in segs if seg_majority(g)[0] == c],
            key=lambda g: (-seg_majority(g)[1], -g["length"]))[:3]
        for i, g in enumerate(members):
            sf.write(os.path.join(
                args.out, "cluster%d_%s_sample%d_t%ds.wav"
                % (c, mapping2.get(c) or "unassigned", i, g["start"])),
                audio[g["clip"][0]:g["clip"][1]], TARGET_SR)

    report = {
        "device_id": args.device_id, "session_id": args.session_id,
        "recording": os.path.basename(wav_path),
        "segments": len(segs), "clusters": int(best_k),
        "silhouette": round(float(best_score), 3),
        "assignment_initial": {int(k): v for k, v in detail.items()},
        "assignment_bootstrapped": {int(k): v for k, v in detail2.items()},
        "seconds_by_old_tag": old_secs,
        "seconds_by_new_tag": new_secs,
        "segments_relabeled": changed,
        "rows": rows,
    }
    with open(os.path.join(args.out, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    log("\n=== PILOT RESULT device %d ===" % args.device_id)
    log("old attribution (s): %s" % old_secs)
    log("new attribution (s): %s" % new_secs)
    log("segments relabeled: %d/%d" % (changed, len(segs)))
    log("report + ear-check samples in %s" % args.out)


if __name__ == "__main__":
    main()
