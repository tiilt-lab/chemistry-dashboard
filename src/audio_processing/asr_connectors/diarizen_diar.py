"""Subprocess wrapper for the DiariZen diarizer (see diarizen_cli.py).

Returns [(start_seconds, end_seconds, cluster_label), ...] or raises — the
caller decides whether to fall back (whisperx_asr.py drops to pyannote 3.1).
The DiariZen venv is resolved relative to this file so deploys keep working
regardless of cwd.

Model: BUT-FIT/diarizen-wavlm-large-s80-md-v2 (WavLM-based, overlap-aware).
Weights are CC BY-NC 4.0 — research use only; the DiariZen code is MIT.
"""

import json
import logging
import os
import subprocess
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_DIARIZEN_PYTHON = os.path.abspath(os.path.join(_HERE, "..", "..", "venv-diarizen", "bin", "python"))
_CLI = os.path.join(_HERE, "diarizen_cli.py")
# Measured: 58.7 min of 16 kHz mono audio in 273 s on the Quadro RTX 8000
# (batch 16), but the GPU is shared and a long recording deserves headroom.
_TIMEOUT_SECONDS = 60 * 60

DEFAULT_MODEL = "BUT-FIT/diarizen-wavlm-large-s80-md-v2"


def run_diarizen(audio_file, model=DEFAULT_MODEL, max_speakers=8, batch=16):
    if not os.path.isfile(_DIARIZEN_PYTHON):
        raise RuntimeError("DiariZen venv missing at {0}".format(_DIARIZEN_PYTHON))
    # NamedTemporaryFile reserves a unique name atomically (no mktemp TOCTOU
    # race); the CLI overwrites the empty file with its JSON output.
    with tempfile.NamedTemporaryFile(suffix=".json", prefix="diarizen_", delete=False) as tf:
        out_path = tf.name
    cmd = [_DIARIZEN_PYTHON, _CLI, audio_file, "--out", out_path, "--model", model,
           "--max-speakers", str(max_speakers), "--batch", str(batch)]
    # Weights come from the Hugging Face cache; offline so a missing network
    # never blocks a run (set HF_HUB_OFFLINE=0 in the service env to refresh).
    env = dict(os.environ)
    env.setdefault("HF_HUB_OFFLINE", "1")
    logging.info("DiariZen: launching diarization subprocess for %s", audio_file)
    try:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                                  timeout=_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            raise RuntimeError("diarizen_cli timed out after {0}s".format(_TIMEOUT_SECONDS))
        if proc.returncode != 0:
            raise RuntimeError("diarizen_cli failed (rc={0}): {1}".format(
                proc.returncode, (proc.stderr or "")[-2000:]))
        with open(out_path) as f:
            data = json.load(f)
        turns = [(t["start"], t["end"], t["speaker"]) for t in data.get("turns", [])]
        logging.info("DiariZen: %d turns", len(turns))
        return turns
    finally:
        if os.path.isfile(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
