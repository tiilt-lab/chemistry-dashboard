"""Active-speaker detection over a pod recording (TalkNCE-UniTalk).

Standalone subprocess invoked by the video post-hoc service when the trigger
requests ASD. Pipeline: S3FD face detection (full resolution — pod faces are
~35px and vanish at the usual 4x downscale) -> greedy IOU tracker with linear
box interpolation -> tight 112x112 grayscale crops -> LoCoNet/TalkNCE scoring
in 200-frame chunks with cross-speaker context -> dlib identity per track from
the enrolled facial-embedding gallery -> JSON artifact next to the recording:

    {"fps": 25, "video": ..., "tracks": [
        {"id": 0, "frames": [...], "scores": [...],
         "identity": "username"|null, "identity_distance": 0.42}, ...]}

Fusion with transcripts happens at read time in the Flask API (no schema
changes; audio and video posthoc can finish in either order).

Usage:
    python run_asd.py video.webm --out artifact.json \
        [--gallery ../facial_embeddings] [--candidates alice,bob]
"""

import argparse
import glob
import json
import logging
import os
import sys
import types

import cv2
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "talknce"))
sys.path.insert(0, HERE)

FPS = 25
CHUNK = 200           # TalkNCE training clip length
DET_CONF = 0.85
IOU_JOIN = 0.30
MIN_TRACK_DETS = 20   # detections (not frames) before a track is kept
FACE_MIN_HALF = 8     # px half-size; smaller boxes are background blobs


def detect_faces(video_path, stride):
    from s3fd import S3FD
    det = S3FD(device="cuda" if torch.cuda.is_available() else "cpu")
    cap = cv2.VideoCapture(video_path)
    dets = {}
    f = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        if f % stride == 0:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            boxes = det.detect_faces(rgb, conf_th=DET_CONF, scales=[1.0])
            dets[f] = [b[:4].astype(float) for b in boxes]
            if f % (stride * 500) == 0:
                logging.info("ASD detect: frame %d, %d faces", f, len(dets[f]))
        f += 1
    cap.release()
    return dets, f


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def build_tracks(dets, stride, embeds=None):
    """Greedy IOU association over the sampled detection frames. When `embeds`
    (per-frame ArcFace vectors aligned with dets) is given, each track carries
    the embeddings of its detections for identity matching."""
    open_tracks, done = [], []
    max_gap = stride * 8  # tolerate short detection dropouts (~0.6s)
    for f in sorted(dets):
        used = set()
        for tr in open_tracks:
            lf, lbox = tr[-1][0], tr[-1][1]
            best_j, best_v = None, IOU_JOIN
            if f - lf <= max_gap:
                for j, box in enumerate(dets[f]):
                    if j in used:
                        continue
                    v = iou(lbox, box)
                    if v > best_v:
                        best_j, best_v = j, v
            if best_j is not None:
                emb = embeds[f][best_j] if embeds else None
                tr.append((f, dets[f][best_j], emb))
                used.add(best_j)
        still_open = []
        for tr in open_tracks:
            if f - tr[-1][0] > max_gap:
                done.append(tr)
            else:
                still_open.append(tr)
        open_tracks = still_open
        for j, box in enumerate(dets[f]):
            if j not in used:
                open_tracks.append([(f, box, embeds[f][j] if embeds else None)])
    done.extend(open_tracks)

    tracks = []
    for tr in done:
        if len(tr) < MIN_TRACK_DETS:
            continue
        half = np.median([max(b[2] - b[0], b[3] - b[1]) / 2 for _, b, _ in tr])
        if half < FACE_MIN_HALF:
            continue
        # interpolate (x, y, s) per frame across the sampled detections
        fs = np.array([f for f, _, _ in tr])
        xs = np.array([(b[0] + b[2]) / 2 for _, b, _ in tr])
        ys = np.array([(b[1] + b[3]) / 2 for _, b, _ in tr])
        ss = np.array([max(b[2] - b[0], b[3] - b[1]) / 2 for _, b, _ in tr])
        frames = np.arange(fs[0], fs[-1] + 1)
        embv = [e for _, _, e in tr if e is not None]
        tracks.append({
            "frames": frames,
            "x": np.interp(frames, fs, xs),
            "y": np.interp(frames, fs, ys),
            "s": np.interp(frames, fs, ss),
            "embeddings": embv,
        })
    tracks.sort(key=lambda t: t["frames"][0])
    return tracks


def crop_face(img, x, y, s):
    m = s * 1.1  # tight UniTalk-style box; loose crops starve the model
    y0, y1 = max(0, int(y - m)), int(y + m)
    x0, x1 = max(0, int(x - m)), int(x + m)
    crop = img[y0:y1, x0:x1]
    if crop.size == 0:
        return np.zeros((112, 112), dtype=np.float32)
    return cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (112, 112)).astype(np.float32)


def collect_crops(video_path, tracks):
    """One sequential pass over the video, harvesting crops for every track."""
    want = {}
    for i, tr in enumerate(tracks):
        for j, f in enumerate(tr["frames"]):
            want.setdefault(int(f), []).append((i, j))
    for tr in tracks:
        tr["crops"] = {}
        tr["color_samples"] = []
    cap = cv2.VideoCapture(video_path)
    f = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        for i, j in want.get(f, []):
            tr = tracks[i]
            tr["crops"][int(tr["frames"][j])] = crop_face(
                img, tr["x"][j], tr["y"][j], tr["s"][j])
            # a few color crops per track for identity matching
            if len(tr["color_samples"]) < 6 and j % max(1, len(tr["frames"]) // 6) == 0:
                x, y, s = tr["x"][j], tr["y"][j], tr["s"][j]
                m = s * 1.3
                c = img[max(0, int(y - m)):int(y + m), max(0, int(x - m)):int(x + m)]
                if c.size:
                    tr["color_samples"].append(c.copy())
        f += 1
    cap.release()


def load_scorer():
    from model.loconet_encoder import locoencoder
    cfg = types.SimpleNamespace(MODEL=types.SimpleNamespace(
        ADJUST_ATTENTION=0, AV_layers=3, NUM_SPEAKERS=3, CLIP_LENGTH=CHUNK,
        AV="speaker_temporal", FUSION="cross-att", SIM="default", LIM="self-att"))
    model = locoencoder(cfg).cuda().eval()
    fc = torch.nn.Linear(256, 2).cuda().eval()
    sd = torch.load(os.path.join(HERE, "weights", "talknce_unitalk.model"),
                    map_location="cpu")
    enc, fcw = {}, {}
    for k, v in sd.items():
        k2 = k.replace("model.module.", "")
        if k2.startswith("model."):
            enc[k2[len("model."):]] = v
        elif k2.startswith("lossAV.FC."):
            fcw[k2[len("lossAV.FC."):]] = v
    model.load_state_dict(enc, strict=True)
    fc.load_state_dict(fcw, strict=True)
    return model, fc


def score_tracks(tracks, audio, model, fc):
    from torchvggish import vggish_input
    for i, tr in enumerate(tracks):
        frames = [int(f) for f in tr["frames"]]
        scores = {}
        for c0 in range(0, len(frames), CHUNK):
            span = frames[c0:c0 + CHUNK]
            t = len(span)
            if t < 5:
                continue
            target = np.stack([tr["crops"].get(f, np.zeros((112, 112), np.float32))
                               for f in span])
            # context: the other track with most temporal overlap on this span
            ctx = np.zeros_like(target)
            best_ov = 0
            for k, other in enumerate(tracks):
                if k == i:
                    continue
                ov = len(set(span) & set(int(f) for f in other["frames"]))
                if ov > best_ov:
                    best_ov = ov
                    ctx = np.stack([other["crops"].get(f, np.zeros((112, 112), np.float32))
                                    for f in span])
            visual = torch.FloatTensor(np.stack([target, ctx, ctx]))
            a0 = int(span[0] / FPS * 16000)
            a1 = int((span[-1] + 1) / FPS * 16000)
            mel = vggish_input.waveform_to_examples(audio[a0:a1], 16000, t, FPS,
                                                    return_tensor=False)
            with torch.no_grad():
                audioFeature = torch.FloatTensor(mel)[None, :, :].unsqueeze(0).cuda()
                visualFeature = visual.unsqueeze(0).cuda()
                b, s = 1, 3
                visualFeature = visualFeature.view(b * s, *visualFeature.shape[2:])
                audioEmbed = model.forward_audio_frontend(audioFeature)
                visualEmbed = model.forward_visual_frontend(visualFeature)
                audioEmbed = audioEmbed.repeat(s, 1, 1)
                audioEmbed, visualEmbed = model.forward_cross_attention(audioEmbed, visualEmbed)
                outsAV = model.forward_audio_visual_backend(audioEmbed, visualEmbed, b, s)
                outsAV = outsAV.view(b, s, t, -1)[:, 0, :, :].view(b * t, -1)
                prob = torch.softmax(fc(outsAV.squeeze(1)), dim=-1)[:, 1].cpu().numpy()
            for j, f in enumerate(span):
                scores[f] = float(prob[j])
        tr["scores"] = scores
        logging.info("ASD score: track %d done (%d frames)", i, len(scores))


def identify_tracks(tracks, gallery_dir, candidates=None):
    try:
        import face_recognition
    except ImportError:
        logging.warning("ASD identify: face_recognition unavailable; skipping")
        return
    # Gallery files are {alias: embedding(s)} dicts saved via np.save (see
    # facial_biometric_processing_service). Average multi-sample enrollments.
    gallery = {}
    for path in glob.glob(os.path.join(gallery_dir, "*.npy")):
        alias = os.path.splitext(os.path.basename(path))[0]
        if candidates and alias not in candidates:
            continue
        try:
            raw = np.load(path, allow_pickle=True)
            data = raw.item() if raw.dtype == object else {alias: raw}
            emb = np.asarray(data.get(alias))
            if emb is None or emb.size < 128:
                continue
            emb = emb.reshape(-1, 128).mean(axis=0)
            gallery[alias] = emb
        except Exception as e:
            logging.warning("ASD identify: bad gallery file %s: %s", path, e)
    if not gallery:
        logging.warning("ASD identify: empty gallery")
        return
    names = list(gallery)
    mat = np.stack([gallery[n] for n in names])
    for i, tr in enumerate(tracks):
        dists = []
        for img in tr.get("color_samples", []):
            # The sample IS the face crop — pod faces are too small for the
            # HOG detector to re-find inside it, so upscale and pass the whole
            # frame as the face location.
            up = cv2.resize(img, (256, 256), interpolation=cv2.INTER_CUBIC)
            rgb = cv2.cvtColor(up, cv2.COLOR_BGR2RGB)
            encs = face_recognition.face_encodings(
                rgb, known_face_locations=[(16, 240, 240, 16)])
            if encs:
                dists.append(np.linalg.norm(mat - encs[0], axis=1))
        if not dists:
            tr["identity"], tr["identity_distance"] = None, None
            logging.info("ASD identify: track %d -> no encodable face", i)
            continue
        mean_d = np.mean(dists, axis=0)
        order = np.argsort(mean_d)
        j = int(order[0])
        best = float(mean_d[j])
        second = float(mean_d[order[1]]) if len(order) > 1 else 999.0
        # Track-level identity averages several samples, so accept either a
        # solid absolute match or a clearly-separated relative one — current
        # enrollment galleries run hot (0.55-0.70 even for correct matches).
        accept = best <= 0.60 or (best <= 0.68 and second - best >= 0.06)
        tr["identity"] = names[j] if accept else None
        tr["identity_distance"] = round(best, 3)
        logging.info("ASD identify: track %d -> %s (best %s=%.3f, next %.3f)",
                     i, tr["identity"], names[j], best, second)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--out", required=True)
    parser.add_argument("--gallery", default=os.path.join(HERE, "..", "facial_embeddings"))
    parser.add_argument("--candidates", default="",
                        help="comma-separated aliases to restrict identity matching")
    parser.add_argument("--det-stride", type=int, default=2)
    parser.add_argument("--face-backend", choices=["s3fd", "insightface"],
                        default="s3fd",
                        help="s3fd+dlib (baseline) or insightface SCRFD+ArcFace (SOTA)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - ASD %(levelname)s: %(message)s")

    # Decode to a temp 25fps mp4 + 16k wav so frame indexes are exact.
    import subprocess
    import tempfile
    tmp = tempfile.mkdtemp(prefix="asd_")
    v25 = os.path.join(tmp, "v25.mp4")
    wav = os.path.join(tmp, "a16.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.video,
                    "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "23", v25], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.video,
                    "-ac", "1", "-ar", "16000", wav], check=True)

    from scipy.io import wavfile
    _, audio = wavfile.read(wav)

    cands = set(filter(None, args.candidates.split(","))) or None
    if args.face_backend == "insightface":
        from insightface_faces import (detect_and_embed, load_arcface_gallery,
                                       identify_tracks as identify_arcface)
        dets, embeds, total = detect_and_embed(v25, args.det_stride)
        tracks = build_tracks(dets, args.det_stride, embeds)
    else:
        dets, total = detect_faces(v25, args.det_stride)
        tracks = build_tracks(dets, args.det_stride)
    logging.info("ASD: %d frames, %d tracks (%s)", total, len(tracks), args.face_backend)
    collect_crops(v25, tracks)  # visual crops still feed the talking-scorer
    model, fc = load_scorer()
    score_tracks(tracks, audio, model, fc)
    del model, fc
    torch.cuda.empty_cache()
    if args.face_backend == "insightface":
        identify_arcface(tracks, load_arcface_gallery(
            os.path.abspath(args.gallery), cands))
    else:
        identify_tracks(tracks, os.path.abspath(args.gallery), cands)

    out = {"fps": FPS, "video": os.path.basename(args.video), "tracks": []}
    for i, tr in enumerate(tracks):
        frames = sorted(tr["scores"])
        out["tracks"].append({
            "id": i,
            "frames": frames,
            "scores": [tr["scores"][f] for f in frames],
            "x": round(float(np.mean(tr["x"])), 1),
            "identity": tr.get("identity"),
            "identity_distance": tr.get("identity_distance"),
        })
    with open(args.out, "w") as f:
        json.dump(out, f)
    logging.info("ASD: artifact written to %s", args.out)

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
