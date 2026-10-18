"""Subprocess wrapper for the Nemotron-3 diarizer (see nemotron_cli.py).

Returns [(start_seconds, end_seconds, cluster_label), ...] or raises — the
caller decides whether to fall back (whisperx_asr.py tries the other
post-hoc diarizer). The venv is resolved relative to this file so deploys
keep working regardless of cwd.

Model: nvidia/Nemotron-3-Diarization (streaming Sortformer, up to 8
speakers), licence OpenMDW-1.1 — commercial use allowed.
"""

import json
import logging
import os
import subprocess
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_NEMO3_PYTHON = os.path.abspath(os.path.join(_HERE, "..", "..", "venv-nemo3", "bin", "python"))
_CLI = os.path.join(_HERE, "nemotron_cli.py")
# Measured: a 3 min slice in 11.8 s (579 MiB GPU peak) — far faster than
# real time, but the GPU is shared and a long recording deserves headroom.
_TIMEOUT_SECONDS = 60 * 60

DEFAULT_MODEL = "nvidia/Nemotron-3-Diarization"


def run_nemotron3(audio_file, model=DEFAULT_MODEL, preset="offline"):
    if not os.path.isfile(_NEMO3_PYTHON):
        raise RuntimeError("Nemotron-3 venv missing at {0}".format(_NEMO3_PYTHON))
    # NamedTemporaryFile reserves a unique name atomically (no mktemp TOCTOU
    # race); the CLI overwrites the empty file with its JSON output.
    with tempfile.NamedTemporaryFile(suffix=".json", prefix="nemotron3_", delete=False) as tf:
        out_path = tf.name
    cmd = [_NEMO3_PYTHON, _CLI, audio_file, "--out", out_path, "--model", model,
           "--preset", preset]
    # The checkpoint comes from the Hugging Face cache; offline so a missing
    # network never blocks a run (set HF_HUB_OFFLINE=0 in the service env to
    # refresh).
    env = dict(os.environ)
    env.setdefault("HF_HUB_OFFLINE", "1")
    logging.info("Nemotron-3: launching diarization subprocess for %s", audio_file)
    try:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                                  timeout=_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            raise RuntimeError("nemotron_cli timed out after {0}s".format(_TIMEOUT_SECONDS))
        if proc.returncode != 0:
            raise RuntimeError("nemotron_cli failed (rc={0}): {1}".format(
                proc.returncode, (proc.stderr or "")[-2000:]))
        with open(out_path) as f:
            data = json.load(f)
        turns = [(t["start"], t["end"], t["speaker"]) for t in data.get("turns", [])]
        logging.info("Nemotron-3: %d turns", len(turns))
        return turns
    finally:
        if os.path.isfile(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
