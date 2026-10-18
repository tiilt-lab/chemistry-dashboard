"""The post-hoc audio progress bar: the worker runner polls the worker's
progress sidecar (asr_connectors/base_asr.run_json_worker), the processor
turns the connector's stage and its own counters into one stage-weighted
percent (processor_posthoc.progress_of), the service pushes it every five
seconds and answers status probes with it, and the trigger shows it."""
import os
import sys
import textwrap

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))

from asr_connectors import base_asr  # noqa: E402


def test_the_runner_hands_the_workers_progress_sidecar_to_the_callback(tmp_path):
    script = tmp_path / "worker.py"
    script.write_text(textwrap.dedent('''
        import json, sys, time
        out = sys.argv[1]
        for pct in (10, 60):
            json.dump({"audio_reached_s": pct * 3.0, "audio_s": 300.0, "pct": pct, "tok_per_s": 50.0}, open(out + ".progress", "w"))
            time.sleep(0.6)
        json.dump({"turns": [], "done": True}, open(out, "w"))
    '''))
    seen = []
    result = base_asr.run_json_worker(lambda out: [sys.executable, str(script), out], timeout=30,
                                      on_progress=seen.append, progress_interval=0.2)
    assert result == {"turns": [], "done": True}
    assert seen and seen[0]["audio_s"] == 300.0 and seen[-1]["pct"] == 60
    assert base_asr.read_progress(str(tmp_path / "nope.progress")) is None


def _progress_of():
    src = open(os.path.join(ROOT, "src", "audio_processing", "processor_posthoc.py")).read()
    start = src.index("STAGE_RANGES = "); end = src.index("\n\n\nclass AudioProcessorPosthoc")
    ns = {}
    exec(src[start:end], ns)
    return ns["progress_of"]


def test_the_bar_is_one_stage_weighted_percent_with_a_plain_message():
    progress_of = _progress_of()
    assert progress_of("transcribing") == (0, "Transcribing")
    assert progress_of("transcribing", {"audio_reached_s": 1500.0, "audio_s": 3000.0, "tok_per_s": 51.8}) == (41, "Transcribing 25:00 of 50:00 (51 tokens/s)")
    assert progress_of("transcribing", {"audio_reached_s": 3100.0, "audio_s": 3000.0}) == (82, "Transcribing 51:40 of 50:00")
    assert progress_of("naming") == (82, "Naming the speakers")
    assert progress_of("scoring", done=10, total=100) == (85, "Scoring utterances 10 of 100")
    assert progress_of("scoring", done=0, total=None) == (84, "Scoring utterances 0 of ?")
    assert progress_of("publishing", published=50, publish_total=100) == (98, "Publishing 50 of 100")
    assert progress_of("publishing", published=100, publish_total=100) == (100, "Publishing 100 of 100")
    assert progress_of("something else") == (0, "Starting")


def test_the_service_pushes_progress_and_answers_status_probes_with_it():
    server = open(os.path.join(ROOT, "src", "audio_processing", "server_posthoc.py")).read()
    assert "self._progress_loop = task.LoopingCall(self.processor.report_progress)" in server
    assert "self._progress_loop.start(5.0, now=False)" in server
    i = server.index("def on_run_complete(")
    assert "loop.stop()" in server[i:i + 800]
    j = server.index("if data['type'] == 'query_posthoc_status':")
    assert "'_last_progress'" in server[j:j + 1200] and "status.update(" in server[j:j + 1200]
    processor = open(os.path.join(ROOT, "src", "audio_processing", "processor_posthoc.py")).read()
    assert "def report_progress(self):" in processor and "self.report_progress()" in processor[processor.index("def _publish("):]
    moss = open(os.path.join(ROOT, "src", "audio_processing", "asr_connectors", "moss_asr.py")).read()
    assert "on_progress=self._on_progress" in moss and 'self.stage = "naming"' in moss
    trigger = open(os.path.join(ROOT, "frontend", "src", "components", "posthoc", "posthoc-trigger.jsx")).read()
    k = trigger.index('if (msg.type !== "posthoc_status") return')
    assert "msg.percent" in trigger[k:k + 1500] and "msg.started_at" in trigger[k:k + 1500]
