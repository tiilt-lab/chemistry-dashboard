"""SOTA face front-end for ASD: InsightFace buffalo_l (SCRFD detector +
ArcFace-512 recogniser), replacing S3FD detection + dlib identification.

Why this matters for pod video:
  * SCRFD finds profile / partly-occluded / small far-field faces that S3FD's
    single-scale pass misses — the direct cause of "unidentified" ASD tracks.
  * ArcFace 512-D embeddings identify far more robustly than dlib's 128-D
    ResNet, especially across the enrollment-vs-classroom domain gap.

One FaceAnalysis pass yields, per frame, both the boxes (for tracking) and a
normalised ArcFace embedding per face (for identification), so detection and
recognition share a single decode. Kept as a drop-in alongside the S3FD path
so the two can be compared head to head.
"""
import logging
import os

import cv2
import numpy as np

_APP = None


def _app():
    global _APP
    if _APP is None:
        from insightface.app import FaceAnalysis
        import torch
        providers = (["CUDAExecutionProvider", "CPUExecutionProvider"]
                     if torch.cuda.is_available() else ["CPUExecutionProvider"])
        app = FaceAnalysis(name="buffalo_l", providers=providers)
        app.prepare(ctx_id=0 if torch.cuda.is_available() else -1,
                    det_size=(640, 640))
        _APP = app
        logging.info("ASD faces: InsightFace buffalo_l ready (%s)", providers[0])
    return _APP


def detect_and_embed(video_path, stride, det_conf=0.30):
    """One pass over the video. Returns:
        dets:   {frame: [ (x1,y1,x2,y2), ... ]}
        embeds: {frame: [ arcface_512(normed), ... ]}  aligned with dets
        total_frames
    """
    app = _app()
    cap = cv2.VideoCapture(video_path)
    dets, embeds, f = {}, {}, 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        if f % stride == 0:
            faces = app.get(img)  # BGR is fine; insightface handles it
            boxes, embs = [], []
            for fa in faces:
                if getattr(fa, "det_score", 1.0) < det_conf:
                    continue
                boxes.append(tuple(float(v) for v in fa.bbox[:4]))
                embs.append(np.asarray(fa.normed_embedding, dtype=np.float32))
            dets[f] = boxes
            embeds[f] = embs
            if f % (stride * 500) == 0:
                logging.info("ASD detect(SCRFD): frame %d, %d faces", f, len(boxes))
        f += 1
    cap.release()
    return dets, embeds, f


def load_arcface_gallery(gallery_dir, candidates=None):
    """ArcFace galleries live beside dlib ones as <alias>.arc.npy (512-D),
    written by build_arcface_gallery.py. Returns {alias: normed 512-vec}."""
    import glob
    gallery = {}
    for path in glob.glob(os.path.join(gallery_dir, "*.arc.npy")):
        alias = os.path.basename(path)[: -len(".arc.npy")]
        if candidates and alias not in candidates:
            continue
        try:
            v = np.load(path).astype(np.float32).reshape(-1)
            if v.size == 512:
                gallery[alias] = v / (np.linalg.norm(v) + 1e-9)
        except Exception as e:
            logging.warning("ASD identify: bad arcface gallery %s: %s", path, e)
    return gallery


def identify_tracks(tracks, gallery, min_sim=0.28, margin=0.03):
    """Assign each track an identity from an ArcFace gallery via mean cosine
    over the track's per-frame embeddings. Abstains (None) below min_sim or
    when the top two candidates are within `margin` (ambiguous)."""
    if not gallery:
        logging.warning("ASD identify: empty ArcFace gallery")
        for tr in tracks:
            tr["identity"], tr["identity_distance"] = None, None
        return
    names = list(gallery)
    mat = np.stack([gallery[n] for n in names])
    for i, tr in enumerate(tracks):
        embs = tr.get("embeddings", [])
        if not embs:
            tr["identity"], tr["identity_distance"] = None, None
            continue
        mean_emb = np.mean(embs, axis=0)
        mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-9)
        sims = mat @ mean_emb
        order = np.argsort(-sims)
        best, second = sims[order[0]], (sims[order[1]] if len(order) > 1 else -1)
        if best >= min_sim and (best - second) >= margin:
            tr["identity"] = names[order[0]]
            tr["identity_distance"] = round(float(1 - best), 3)  # keep "distance" field
            logging.info("ASD identify: track %d -> %s (sim %.3f, next %.3f)",
                         i, names[order[0]], best, second)
        else:
            tr["identity"], tr["identity_distance"] = None, None
            logging.info("ASD identify: track %d -> None (best %s=%.3f, next %.3f)",
                         i, names[order[0]], best, second)
