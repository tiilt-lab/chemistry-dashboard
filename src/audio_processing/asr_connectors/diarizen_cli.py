"""Standalone DiariZen diarization CLI.

Runs inside the dedicated DiariZen venv (src/venv-diarizen: Python 3.10,
torch 2.1.1+cu121, the DiariZen toolkit and its pyannote.audio 3.1.1 fork) —
those pins cannot share an environment with whisperx, so the audio service
invokes this as a subprocess and reads JSON, exactly like sortformer_cli.py.

Usage:
    venv-diarizen/bin/python diarizen_cli.py input.wav --out turns.json \
        [--model BUT-FIT/diarizen-wavlm-large-s80-md-v2] [--max-speakers 8] [--batch 16]

Input: a 16 kHz mono WAV (the post-hoc service's <key>_redu.wav files).
Output JSON: {"turns": [{"start": s, "end": e, "speaker": "speaker_0"}, ...]}

Licence: the BUT-FIT/diarizen-wavlm-large-s80-md-v2 weights are CC BY-NC 4.0
(research use only); the DiariZen code is MIT. Weights load from the Hugging
Face cache with HF_HUB_OFFLINE=1 so a missing network never blocks a run.
"""

import argparse
import json
import logging
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio")
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="BUT-FIT/diarizen-wavlm-large-s80-md-v2")
    # A pod is a handful of people; the checkpoint allows 20.
    parser.add_argument("--max-speakers", type=int, default=8)
    # Segmentation + embedding batch size: 5.8 GB GPU peak at 16 on an
    # hour-long recording, 11 GB at DiariZen's default 32. The GPU is shared.
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    if not os.path.isfile(args.audio):
        sys.exit("diarizen_cli: no such audio file: {0}".format(args.audio))

    from diarizen.pipelines.inference import DiariZenPipeline

    pipe = DiariZenPipeline.from_pretrained(args.model)
    pipe.max_speakers = args.max_speakers
    pipe.segmentation_batch_size = args.batch
    pipe.embedding_batch_size = args.batch
    # The pipeline takes channel 0 itself; sess_name only labels the output.
    annotation = pipe(args.audio, sess_name="pod")
    turns = [
        {"start": float(seg.start), "end": float(seg.end),
         "speaker": "speaker_{0}".format(label)}
        for seg, _, label in annotation.itertracks(yield_label=True)
    ]
    turns.sort(key=lambda t: (t["start"], t["end"]))
    with open(args.out, "w") as f:
        json.dump({"turns": turns}, f)
    print("wrote {0} turns".format(len(turns)))


if __name__ == "__main__":
    main()
