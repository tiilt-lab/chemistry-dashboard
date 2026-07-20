"""Build ArcFace-512 gallery entries (<alias>.arc.npy) for ASD identity
matching, from the surviving enrollment signup videos.

The deployed face gallery is 128-D dlib; ArcFace identification needs 512-D
references. Only some enrollment videos are retained, so this writes .arc.npy
for whichever aliases still have source media, beside the existing .npy —
ASD's insightface path uses them where present and abstains otherwise (the
cross-session linker / ear-tags cover the rest).

Usage (writes into the facial_embeddings dir by default):
  ../venv-unified/bin/python3 asd/build_arcface_gallery.py \
      --videos ../videorecordings --out ../facial_embeddings
"""
import argparse
import glob
import logging
import os

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", required=True,
                    help="dir of enrollment videos named <alias>.<ext>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-frames", type=int, default=40)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    import cv2
    from insightface.app import FaceAnalysis
    import torch

    def sample_frames(path, n):
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        idxs = (set(int(i * total / n) for i in range(n)) if total > n
                else None)
        out, f = [], 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if idxs is None or f in idxs:
                out.append(img)  # BGR
            f += 1
        cap.release()
        return out

    providers = (["CUDAExecutionProvider", "CPUExecutionProvider"]
                 if torch.cuda.is_available() else ["CPUExecutionProvider"])
    app = FaceAnalysis(name="buffalo_l", providers=providers)
    app.prepare(ctx_id=0 if torch.cuda.is_available() else -1, det_size=(640, 640))

    # enrollment videos are the short single-face clips (alias-named, NOT the
    # <deviceid>-<uuid>_orig pod recordings).
    vids = [p for p in glob.glob(os.path.join(args.videos, "*"))
            if os.path.splitext(p)[1].lower() in (".webm", ".mp4", ".mov")
            and "_orig" not in os.path.basename(p)
            and not os.path.basename(p).split("-")[0].isdigit()]
    logging.info("candidate enrollment videos: %d", len(vids))

    built = 0
    for path in sorted(vids):
        alias = os.path.splitext(os.path.basename(path))[0]
        try:
            frames = sample_frames(path, args.max_frames)
            embs = []
            for bgr in frames:
                faces = app.get(bgr)
                if faces:
                    faces.sort(key=lambda f: -(f.bbox[2] - f.bbox[0]))
                    embs.append(np.asarray(faces[0].normed_embedding, np.float32))
            if not embs:
                logging.info("  %s: no face found — skipped", alias)
                continue
            v = np.mean(embs, axis=0)
            v = v / (np.linalg.norm(v) + 1e-9)
            np.save(os.path.join(args.out, alias + ".arc.npy"), v)
            built += 1
            logging.info("  %s: %d face frames -> arcface", alias, len(embs))
        except Exception as e:
            logging.warning("  %s FAILED: %s", alias, e)
    logging.info("built %d ArcFace gallery entries", built)


if __name__ == "__main__":
    main()
