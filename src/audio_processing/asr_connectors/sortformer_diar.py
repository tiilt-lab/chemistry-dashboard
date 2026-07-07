"""Subprocess wrapper for the Sortformer diarizer (see sortformer_cli.py).

Returns [(start_seconds, end_seconds, cluster_label), ...] or raises — the
caller decides whether to fall back. The NeMo venv is resolved relative to
this file so deploys keep working regardless of cwd.
"""

import json
import logging
import os
import subprocess
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_NEMO_PYTHON = os.path.abspath(os.path.join(_HERE, "..", "..", "venv-nemo", "bin", "python"))
_CLI = os.path.join(_HERE, "sortformer_cli.py")
# Streaming Sortformer is fast (faster than realtime on GPU), but first-run
# model download plus a long recording deserves headroom.
_TIMEOUT_SECONDS = 45 * 60


def run_sortformer(audio_file, model="nvidia/diar_streaming_sortformer_4spk-v2.1"):
    if not os.path.isfile(_NEMO_PYTHON):
        raise RuntimeError("NeMo venv missing at {0}".format(_NEMO_PYTHON))
    out_path = tempfile.mktemp(suffix=".json", prefix="sortformer_")
    cmd = [_NEMO_PYTHON, _CLI, audio_file, "--out", out_path, "--model", model]
    logging.info("Sortformer: launching diarization subprocess for %s", audio_file)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=_TIMEOUT_SECONDS)
        if proc.returncode != 0:
            raise RuntimeError("sortformer_cli failed (rc={0}): {1}".format(
                proc.returncode, (proc.stderr or "")[-2000:]))
        with open(out_path) as f:
            data = json.load(f)
        turns = [(t["start"], t["end"], t["speaker"]) for t in data.get("turns", [])]
        logging.info("Sortformer: %d turns", len(turns))
        return turns
    finally:
        if os.path.isfile(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
