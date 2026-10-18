"""Run moss_cli.py in its venv and return the turns (the post-hoc engine's
subprocess wrapper, like nemotron_diar.py / diarizen_diar.py). The venv is
resolved relative to this file so deploys from any checkout find it."""
import logging
import os

from .base_asr import POSTHOC_WORKER_TIMEOUT, run_json_worker

_HERE = os.path.dirname(os.path.abspath(__file__))
_CLI = os.path.join(_HERE, "moss_cli.py")
_GRANITE_PYTHON = os.path.abspath(os.path.join(_HERE, "..", "..", "venv-granite", "bin", "python"))
DEFAULT_MAX_NEW_TOKENS = 40000   # about 10 tokens per audio second; an hour needs up to 38K


def run_moss(audio_file, hotwords=None, max_new_tokens=DEFAULT_MAX_NEW_TOKENS, handle=None,
             timeout=POSTHOC_WORKER_TIMEOUT):
    """Transcribe + diarize ``audio_file`` in one pass. Returns the CLI's dict:
    ``turns`` = [{start, end, speaker, text}], plus run statistics. Raises
    RuntimeError when the venv is missing, the worker fails, times out or is
    cancelled through ``handle``."""
    if not os.path.exists(_GRANITE_PYTHON):
        raise RuntimeError("MOSS venv missing at {0}".format(_GRANITE_PYTHON))

    def argv(out_path):
        cmd = [_GRANITE_PYTHON, _CLI, audio_file, "--out", out_path, "--max-new-tokens", str(int(max_new_tokens))]
        if hotwords:
            cmd += ["--hotwords", ", ".join(h.strip() for h in hotwords if h and h.strip())]
        return cmd

    logging.info("MOSS: launching end-to-end transcription for %s", audio_file)
    result = run_json_worker(argv, timeout, handle=handle)
    turns = [t for t in result.get("turns", []) if t.get("end", 0) > t.get("start", 0)]
    result["turns"] = sorted(turns, key=lambda t: (t["start"], t["end"]))
    if result.get("capped"):
        logging.warning("MOSS: token budget %d reached before the end of %s; the tail is missing", max_new_tokens, audio_file)
    logging.info("MOSS: %d turns, %d speakers, %.1f tok/s", len(turns), len({t["speaker"] for t in turns}), result.get("tokens_per_s", 0))
    return result
