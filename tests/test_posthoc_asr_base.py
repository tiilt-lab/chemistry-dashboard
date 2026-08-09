"""Shared scaffolding for the post-hoc file ASR connectors.

WhisperX, Qwen3 and CrisperWhisper (post-hoc) each hand-copied: a _drain_queue
loop (byte-identical), a _worker_python() venv resolver (differing only in the
venv name/depth), a temp-json subprocess runner (with an undocumented
3600-vs-7200 timeout DRIFT), and a torch.load permissive monkeypatch. Those
live once in base_asr now. The connectors themselves import torch/whisperx and
can't load in CI, but base_asr is import-light, so the extracted helpers are
tested directly here.
"""
import json
import os
import queue as queue_module
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src",
                                "audio_processing", "asr_connectors"))

import base_asr  # noqa: E402


def test_worker_python_falls_back_to_current_interpreter():
    # No such venv -> current interpreter (the unified py3.10 env).
    assert base_asr.worker_python("no_such_venv_xyz", levels_up=2) == sys.executable
    assert base_asr.worker_python("no_such_venv_xyz", levels_up=3) == sys.executable


def test_run_json_worker_parses_worker_output():
    def build_argv(out_path):
        return [sys.executable, "-c",
                "import json,sys; json.dump({'segments': [1, 2]}, open(sys.argv[1], 'w'))",
                out_path]
    data = base_asr.run_json_worker(build_argv, timeout=30)
    assert data == {"segments": [1, 2]}


def test_run_json_worker_raises_on_nonzero_exit():
    def build_argv(out_path):
        return [sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"]
    try:
        base_asr.run_json_worker(build_argv, timeout=30)
        assert False, "expected RuntimeError on worker failure"
    except RuntimeError as e:
        assert "boom" in str(e)


def test_run_json_worker_cleans_up_temp_file(tmp_path, monkeypatch):
    created = {}

    real_named = base_asr.tempfile.NamedTemporaryFile

    def spy(*a, **k):
        f = real_named(*a, **k)
        created["path"] = f.name
        return f

    monkeypatch.setattr(base_asr.tempfile, "NamedTemporaryFile", spy)
    base_asr.run_json_worker(
        lambda out: [sys.executable, "-c",
                     "import json,sys; json.dump({}, open(sys.argv[1],'w'))", out],
        timeout=30)
    assert not os.path.exists(created["path"]), "temp json must be removed"


def test_drain_queue_stops_on_sentinel():
    q = queue_module.Queue()
    for chunk in (b"aa", b"bb", None):
        q.put(chunk)

    class _Conn(base_asr.PosthocFileASR):
        DRAIN_NAME = "test"

        def __init__(self, audio_queue):
            self.audio_queue = audio_queue
            self.running = True

        def _transcribe_file(self):
            pass

    conn = _Conn(q)
    conn._drain_queue()  # returns when it hits the None sentinel
    assert conn.audio_queue.empty()


def test_posthoc_timeout_is_a_single_documented_constant():
    # The 3600-vs-7200 drift is gone: both connectors use the shared constant.
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src",
                           "audio_processing", "asr_connectors")
    assert base_asr.POSTHOC_WORKER_TIMEOUT >= 7200
    for name in ("qwen3_asr.py", "crisperwhisper_asr.py"):
        with open(os.path.join(src_dir, name)) as f:
            s = f.read()
        assert "run_json_worker(" in s, f"{name}: must use the shared subprocess runner"
        assert "timeout=3600" not in s and "timeout=7200" not in s, \
            f"{name}: must not hardcode a drifting timeout"
