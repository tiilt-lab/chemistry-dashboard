"""Standalone Nemotron-3 diarization CLI.

Runs inside the dedicated NeMo venv src/venv-nemo3 (Python 3.10, torch 2.11
cu128, NeMo from GitHub main): nvidia/Nemotron-3-Diarization needs a
transformer encoder with self_attention_model='rope', which neither the
PyPI NeMo 3.0.0 release nor the production src/venv-nemo (NeMo 2.7.3,
Sortformer) can load. The audio service invokes this as a subprocess and
reads JSON, exactly like sortformer_cli.py / diarizen_cli.py.

Usage:
    venv-nemo3/bin/python nemotron_cli.py input.wav --out turns.json \
        [--model nvidia/Nemotron-3-Diarization] [--preset offline]

Input: a 16 kHz mono WAV (the post-hoc service's <key>_redu.wav files).
Output JSON: {"turns": [{"start": s, "end": e, "speaker": "speaker_0"}, ...]}

Licence: OpenMDW-1.1 (commercial use allowed); public checkpoint, up to 8
speakers. Loaded from the Hugging Face cache with HF_HUB_OFFLINE=1 so a
missing network never blocks a run.
"""

import argparse
import json
import logging
import os
import sys

# Sortformer-module settings from the model card. "offline" is its "very
# high latency" preset — the whole recording is available, so the widest
# context wins; the streaming presets are for live use, not post-hoc.
PRESETS = {
    "offline": dict(spkcache_len=264, fifo_len=40, chunk_len=340,
                    chunk_right_context=40, spkcache_update_period=300),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio")
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="nvidia/Nemotron-3-Diarization")
    parser.add_argument("--preset", default="offline", choices=sorted(PRESETS))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    if not os.path.isfile(args.audio):
        sys.exit("nemotron_cli: no such audio file: {0}".format(args.audio))

    import torch
    from nemo.collections.asr.models import SortformerEncLabelModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SortformerEncLabelModel.from_pretrained(args.model, map_location=device)
    model.eval()
    for name, value in PRESETS[args.preset].items():
        setattr(model.sortformer_modules, name, value)

    outputs = model.diarize(audio=[args.audio], batch_size=1)
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
    turns.sort(key=lambda t: (t["start"], t["end"]))
    with open(args.out, "w") as f:
        json.dump({"turns": turns}, f)
    print("wrote {0} turns".format(len(turns)))


if __name__ == "__main__":
    main()
