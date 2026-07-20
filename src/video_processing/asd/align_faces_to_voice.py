"""Voice teaches face: name ASD face tracks from an attributed transcript.

Once a pod's transcript carries real names (voice profiles + ear-tags), each
row is name + time. A face track whose talking-frames (ASD) overlap rows
attributed to person X is X — so a handful of named voices names the faces
for free, and those faces become an ArcFace gallery (mint_face_gallery.py).

Emits a tags file: {"track:<id>": alias, ...} consumed by mint_face_gallery.

Usage:
  python3 asd/align_faces_to_voice.py --asd 801_asd.json \
      --transcripts 801_transcripts.json --offset 1918 --out tags.json
"""
import argparse
import json
from collections import defaultdict


def align(asd, transcripts, offset, fps, floor=0.10, lead=1.5, min_frac=0.5):
    # per-frame talking face (argmax over co-present tracks)
    probs = defaultdict(dict)
    for t in asd["tracks"]:
        for f, s in zip(t["frames"], t["scores"]):
            probs[f][t["id"]] = max(probs[f].get(t["id"], 0.0), float(s))

    def frame_talker(f):
        d = probs.get(f)
        if not d:
            return None
        r = sorted(d.items(), key=lambda kv: -kv[1])
        if r[0][1] < floor:
            return None
        if len(r) > 1 and r[0][1] < lead * max(r[1][1], 1e-6):
            return None
        return r[0][0]

    # for each track, tally the transcript speaker_tag it talks over
    track_votes = defaultdict(lambda: defaultdict(int))
    for row in transcripts:
        tag = row.get("speaker_tag")
        if not tag or tag.startswith("SPEAKER_"):
            continue  # only learn from real names, not raw clusters
        a = int((row["start_time"] - offset) * fps)
        b = a + int(max(1, row["length"]) * fps)
        for f in range(max(0, a), b):
            who = frame_talker(f)
            if who is not None:
                track_votes[who][tag] += 1

    tags = {}
    for tid, votes in track_votes.items():
        total = sum(votes.values())
        best, n = max(votes.items(), key=lambda kv: kv[1])
        if total >= 10 and n / total >= min_frac:
            tags["track:%d" % tid] = best
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asd", required=True)
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--offset", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    asd = json.load(open(args.asd))
    trans = json.load(open(args.transcripts))
    tags = align(asd, trans, args.offset, asd.get("fps", 25.0))
    json.dump(tags, open(args.out, "w"), indent=2)
    print("named %d face tracks from the attributed transcript:" % len(tags))
    for k, v in tags.items():
        print("  %s -> %s" % (k, v))


if __name__ == "__main__":
    main()
