"""Standalone Sortformer diarization CLI.

Runs inside the dedicated NeMo venv (src/venv-nemo) — NeMo's dependency tree
(lightning, hydra, its own torch pins) must not share an environment with
whisperx, so the audio service invokes this as a subprocess and reads JSON.

Usage:
    venv-nemo/bin/python sortformer_cli.py input.wav --out turns.json

Output JSON: {"turns": [{"start": s, "end": e, "speaker": "speaker_0"}, ...]}
"""

import argparse
import json
import logging


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio")
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="nvidia/diar_streaming_sortformer_4spk-v2.1")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    import torch
    from nemo.collections.asr.models import SortformerEncLabelModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SortformerEncLabelModel.from_pretrained(args.model, map_location=device)
    model.eval()

    outputs = model.diarize(audio=args.audio, batch_size=1)
    # diarize() returns one entry per input file; each entry is a list of
    # "start end speaker_N" strings (occasionally already-split tuples).
    entry = outputs[0] if outputs and isinstance(outputs[0], (list, tuple)) else outputs
    turns = []
    for item in entry or []:
        parts = item.split() if isinstance(item, str) else list(item)
        if len(parts) >= 3:
            turns.append({
                "start": float(parts[0]),
                "end": float(parts[1]),
                "speaker": str(parts[2]),
            })
    with open(args.out, "w") as f:
        json.dump({"turns": turns}, f)
    print("wrote {0} turns".format(len(turns)))


if __name__ == "__main__":
    main()
