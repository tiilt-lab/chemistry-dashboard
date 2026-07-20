"""Mint ArcFace face-gallery entries from session video — the visual mirror
of voice-print minting. Self-enrollment for faces: no student access needed.

An insightface ASD run gives, per face track, a mean ArcFace-512 embedding.
Distinct people appear as several tracks (entrances, occlusions), so this
clusters tracks into faces, then writes one <alias>.arc.npy per NAMED face
into a staging dir. Names come from:

  * --tags JSON: {"track:<id>": alias} or {"face<k>": alias} (eye-tags, or
    the voice->face alignment from align_faces_to_voice), else faces stay
    "face0/1/…" for review.

Production facial_embeddings is never written here; promotion is deliberate.

Usage:
  ../../venv-unified/bin/python3 asd/mint_face_gallery.py \
      --asd 801_asd_insightface.json --out <staging> [--tags tags.json]
"""
import argparse
import json
import os

import numpy as np


def cosine(a, b):
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))


def cluster_faces(tracks, link_threshold=0.45):
    """Agglomerate tracks into distinct faces by ArcFace cosine. Returns
    [{tracks:[id...], embedding, talk_seconds}]."""
    nodes = [{"id": t["id"], "emb": np.asarray(t["embedding"], float),
              "talk": sum(1 for s in t["scores"] if s > 0)}
             for t in tracks if t.get("embedding")]
    faces = [{"ids": [n["id"]], "emb": n["emb"].copy(), "talk": n["talk"]}
             for n in nodes]

    merged = True
    while merged:
        merged = False
        best = None
        for i in range(len(faces)):
            for j in range(i + 1, len(faces)):
                s = cosine(faces[i]["emb"], faces[j]["emb"])
                if s >= link_threshold and (best is None or s > best[2]):
                    best = (i, j, s)
        if best:
            i, j, _ = best
            wi = max(faces[i]["talk"], 1)
            wj = max(faces[j]["talk"], 1)
            faces[i]["emb"] = (faces[i]["emb"] * wi + faces[j]["emb"] * wj) / (wi + wj)
            faces[i]["ids"] += faces[j]["ids"]
            faces[i]["talk"] += faces[j]["talk"]
            faces.pop(j)
            merged = True
    faces.sort(key=lambda f: -f["talk"])
    return faces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tags", default=None)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    asd = json.load(open(args.asd))
    fps = asd.get("fps", 25.0)
    faces = cluster_faces(asd["tracks"])
    tags = json.load(open(args.tags)) if args.tags else {}

    # name each face: explicit track/face tag, else the ASD identity most of
    # its tracks already carry, else a placeholder for review.
    id_to_identity = {t["id"]: t.get("identity") for t in asd["tracks"]}
    manifest, minted = [], 0
    for k, face in enumerate(faces):
        name = None
        for tid in face["ids"]:
            if ("track:%d" % tid) in tags:
                name = tags["track:%d" % tid]
                break
        name = name or tags.get("face%d" % k)
        if not name:
            ids = [id_to_identity.get(t) for t in face["ids"] if id_to_identity.get(t)]
            if ids:
                name = max(set(ids), key=ids.count)
        emb = face["emb"] / (np.linalg.norm(face["emb"]) + 1e-9)
        label = name or ("face%d" % k)
        np.save(os.path.join(args.out, label + ".arc.npy"), emb.astype(np.float32))
        manifest.append({
            "label": label, "named": bool(name),
            "tracks": face["ids"], "talk_seconds": round(face["talk"] / fps, 1),
        })
        if name:
            minted += 1

    json.dump({"faces": len(faces), "named": minted, "entries": manifest},
              open(os.path.join(args.out, "manifest.json"), "w"), indent=2)
    print("clustered %d tracks into %d faces (%d named) -> %s"
          % (sum(len(f["ids"]) for f in faces), len(faces), minted, args.out))
    for m in manifest:
        print("  %-14s %s  %5.0fs  tracks=%s"
              % (m["label"], "NAMED" if m["named"] else "review",
                 m["talk_seconds"], m["tracks"]))


if __name__ == "__main__":
    main()
