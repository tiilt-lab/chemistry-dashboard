"""Pilot stage 3: fuse video active-speaker detection with the audio pilot.

The voice-only pilot pinned pod 801's clusters where prints were usable
(JoshMay26, RishiRama) and left the rest low-confidence — but the pod's
VIDEO sees all four faces, and the TalkNCE ASD pass scores who is talking,
frame by frame, with face-gallery identities. This merges the two:

  per transcript row  ->  ASD vote (who was visibly talking then)
                      ->  voice vote (pyannote cluster -> print match)
  agree            -> attribute, high confidence
  video-only       -> attribute from video (voice prints too weak to object)
  conflict/neither -> abstain

Read-only: writes a fused report; no DB writes.

Usage:
  ../venv-unified/bin/python3 reattribution/fuse_asd.py \
      --asd <801_asd.json> --pilot <pilot801py/report.json> \
      --offset 1918 --out <dir>
"""
import argparse
import json
import os
from collections import defaultdict

FPS = 25.0
# TalkNCE emits a per-frame softmax "talking" PROBABILITY (0..1), not a
# sign — so the active speaker is the co-present face with the highest prob,
# not "everyone above zero". Far-field pod audio keeps absolute probs low, so
# we compare faces to each other per frame rather than to a fixed cutoff.
TALK_FLOOR = 0.10       # min prob to be a candidate talker at all
LEAD_RATIO = 1.5        # winner must beat runner-up by this within a frame
MIN_TALK_FRAMES = 8     # ~1/3 s of winning frames to attribute a row
ROW_LEAD_RATIO = 1.3    # winning face must lead the row by this


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asd", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--transcripts", required=True,
                    help="the pod's transcript rows (for segment lengths)")
    ap.add_argument("--offset", type=int, required=True,
                    help="session seconds at which the recording starts")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    asd = json.load(open(args.asd))
    pilot = json.load(open(args.pilot))
    lengths = {t["id"]: int(t["length"])
               for t in json.load(open(args.transcripts))}
    fps = asd.get("fps", FPS)

    # Per-frame talking probability for each identified face.
    frame_probs = defaultdict(dict)  # frame -> {identity: prob}
    for tr in asd["tracks"]:
        ident = tr.get("identity")
        if not ident:
            continue
        for f, s in zip(tr["frames"], tr["scores"]):
            frame_probs[f][ident] = max(frame_probs[f].get(ident, 0.0), float(s))

    # The talking speaker at frame f: highest-prob co-present face, if it
    # clears the floor and clearly leads the runner-up. Else None (silence,
    # overlap, or the model is unsure — all honest abstentions).
    def frame_speaker(f):
        d = frame_probs.get(f)
        if not d:
            return None
        r = sorted(d.items(), key=lambda kv: -kv[1])
        if r[0][1] < TALK_FLOOR:
            return None
        if len(r) > 1 and r[0][1] < LEAD_RATIO * max(r[1][1], 1e-6):
            return None
        return r[0][0]

    # video coverage window (frames -> which session the video spans)
    max_frame = max((f for f in frame_probs), default=0)
    print("video covers %d frames (~%ds); identities seen: %s"
          % (max_frame, max_frame / fps, sorted({i for d in frame_probs.values() for i in d})))

    # Video is the stronger signal in this pod (all four faces tracked, mouth
    # motion watched), so it leads; the weak-print voice vote only confirms or
    # fills silence. A clear single talking face wins; if two faces tie in a
    # window it's overlap -> defer to voice or abstain.
    rows_out = []
    fused_secs = defaultdict(int)
    tally = defaultdict(int)
    for row in pilot["rows"]:
        length = lengths.get(row["transcript_id"], 0)
        a = int((row["start"] - args.offset) * fps)
        b = a + int(max(1, length) * fps)
        in_video = a <= max_frame  # does the video reach this utterance?
        votes = defaultdict(int)
        for f in range(a, b):
            sp = frame_speaker(f)
            if sp:
                votes[sp] += 1
        ranked = sorted(votes.items(), key=lambda kv: -kv[1])
        video_vote = None
        if ranked and ranked[0][1] >= MIN_TALK_FRAMES and \
                (len(ranked) == 1 or ranked[0][1] >= ROW_LEAD_RATIO * ranked[1][1]):
            video_vote = ranked[0][0]
        voice_vote = row.get("new")

        if video_vote and voice_vote == video_vote:
            fused, conf, why = video_vote, "high", "agree"
        elif video_vote:
            fused, conf, why = video_vote, "medium", \
                ("override_voice" if voice_vote else "video_only")
        elif not in_video and voice_vote:
            # beyond the video: voice is all we have
            fused, conf, why = voice_vote, "low", "voice_only_no_video"
        elif in_video and voice_vote:
            # video present but saw no clear talker (far-field / off-frame);
            # the weak voice guess stands but only tentatively
            fused, conf, why = voice_vote, "low", "voice_only_unclear_video"
        else:
            fused, conf, why = None, "none", "abstain"

        tally[why] += 1
        fused_secs[fused or "(abstain)"] += length
        rows_out.append({**row, "length": length, "video_vote": video_vote,
                         "in_video": in_video, "fused": fused,
                         "confidence": conf, "basis": why})

    report = {
        "asd_artifact": os.path.basename(args.asd),
        "counts": {**tally, "rows": len(rows_out)},
        "fused_seconds": {k: round(v, 1) for k, v in sorted(
            fused_secs.items(), key=lambda x: -x[1])},
        "voice_only_seconds": pilot.get("seconds_by_new_tag"),
        "old_seconds": pilot.get("seconds_by_old_tag"),
        "rows": rows_out,
    }
    with open(os.path.join(args.out, "fused_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("basis counts:", dict(tally))
    print("old attribution (s): ", report["old_seconds"])
    print("voice-only (s):      ", report["voice_only_seconds"])
    print("VIDEO-FUSED (s):     ", report["fused_seconds"])
    print("report:", os.path.join(args.out, "fused_report.json"))


if __name__ == "__main__":
    main()
