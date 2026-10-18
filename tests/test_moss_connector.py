"""MOSS end to end as the default post-hoc engine (src/audio_processing/asr_connectors/
moss_run.py, moss_asr.py; server_posthoc.py; posthoc_queue.py; the trigger UI).
The subprocess and the voice-print reconciliation are faked; CI has no GPU."""
import os
import queue
import sys
import types

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))

from asr_connectors import moss_run  # noqa: E402
from asr_connectors.base_asr import AsrFailed  # noqa: E402
from asr_connectors.moss_asr import MossASR  # noqa: E402


# --- the wrapper --------------------------------------------------------------

def test_wrapper_builds_the_cli_command_and_sorts_the_turns(monkeypatch):
    seen = {}

    def fake_worker(build_argv, timeout, handle=None):
        seen["argv"] = build_argv("/tmp/out.json"); seen["timeout"] = timeout; seen["handle"] = handle
        return {"turns": [{"start": 5.0, "end": 7.0, "speaker": "S02", "text": "later"},
                          {"start": 1.0, "end": 1.0, "speaker": "S01", "text": "zero length"},
                          {"start": 0.0, "end": 2.5, "speaker": "S01", "text": "first"}],
                "tokens_per_s": 41.9, "capped": False}
    monkeypatch.setattr(moss_run, "run_json_worker", fake_worker)
    monkeypatch.setattr(moss_run, "_GRANITE_PYTHON", sys.executable)
    result = moss_run.run_moss("/rec/pod.wav", hotwords=["Viking", " Pat ", ""], max_new_tokens=12345, handle="H")
    argv = seen["argv"]
    assert argv[0] == sys.executable and argv[1].endswith("moss_cli.py") and argv[2] == "/rec/pod.wav"
    assert argv[argv.index("--out") + 1] == "/tmp/out.json"
    assert argv[argv.index("--max-new-tokens") + 1] == "12345"
    assert argv[argv.index("--hotwords") + 1] == "Viking, Pat"
    assert seen["handle"] == "H" and seen["timeout"] == moss_run.POSTHOC_WORKER_TIMEOUT
    assert [t["text"] for t in result["turns"]] == ["first", "later"]     # sorted, zero-length dropped


def test_wrapper_without_the_venv_raises_before_spawning(monkeypatch):
    monkeypatch.setattr(moss_run, "_GRANITE_PYTHON", "/nowhere/python")
    monkeypatch.setattr(moss_run, "run_json_worker", lambda *a, **k: pytest.fail("must not spawn"))
    with pytest.raises(RuntimeError, match="venv missing"):
        moss_run.run_moss("/rec/pod.wav")


# --- the connector ------------------------------------------------------------

def _connector(monkeypatch, turns, enrolled=("Pat3G1S32", "Jing Yuan"), reconcile=None):
    import asr_connectors.moss_asr as mod
    monkeypatch.setattr(mod, "run_moss", lambda *a, **k: {"turns": turns, "tokens_per_s": 40.0})
    calls = []

    def fake_map(audio_file, turn_tuples, enrolled_names, model):
        calls.append((audio_file, list(turn_tuples), enrolled_names, model))
        return reconcile or {}
    stub = types.ModuleType("asr_connectors.cluster_reconcile"); stub.build_cluster_to_enrolled_map = fake_map
    monkeypatch.setitem(sys.modules, "asr_connectors.cluster_reconcile", stub)
    asr = MossASR(queue.Queue(), queue.Queue(), config=None, media_type="audio", interval=10,
                  audio_file="/rec/pod.wav", hotwords=["Viking"], enrolled=list(enrolled), speaker_model="ecapa")
    asr.running = True
    return asr, calls


def _drain(q):
    out = []
    while True:
        item = q.get(timeout=1)
        out.append(item)
        if item is None:
            return out


def test_connector_names_speakers_from_the_prints_and_emits_one_result_per_turn(monkeypatch):
    turns = [{"start": 0.0, "end": 2.5, "speaker": "S01", "text": "What time is our flight?"},
             {"start": 3.0, "end": 4.0, "speaker": "S02", "text": "Three."},
             {"start": 4.5, "end": 5.0, "speaker": "S03", "text": "  "}]
    asr, calls = _connector(monkeypatch, turns, reconcile={"S01": "Jing Yuan"})
    asr._transcribe_file()
    items = _drain(asr.transcript_queue)
    results = [i for i in items if i is not None]
    assert items[-1] is None and len(results) == 2          # the blank turn is skipped
    assert [r.speaker_tag for r in results] == ["Jing Yuan", "S02"]   # named when a print matched, else the label
    assert results[0].alternatives[0].transcript == "What time is our flight?"
    w = results[0].alternatives[0].words[0]
    assert (w.word, w.start_time.seconds, w.end_time.seconds, w.end_time.nanos) == ("What time is our flight?", 0, 2, 500000000)
    assert calls[0][0] == "/rec/pod.wav" and calls[0][1] == [(0.0, 2.5, "S01"), (3.0, 4.0, "S02"), (4.5, 5.0, "S03")]
    assert asr.diarizer_used == "moss" and asr.running is False


def test_connector_without_prints_keeps_the_labels_and_skips_reconciliation(monkeypatch):
    asr, calls = _connector(monkeypatch, [{"start": 0.0, "end": 1.0, "speaker": "S01", "text": "hi"}], enrolled=())
    asr._transcribe_file()
    results = [i for i in _drain(asr.transcript_queue) if i is not None]
    assert [r.speaker_tag for r in results] == ["S01"] and calls == []


def test_connector_reports_a_failed_pass_then_ends_the_stream(monkeypatch):
    import asr_connectors.moss_asr as mod

    def boom(*a, **k):
        raise RuntimeError("worker failed: CUDA out of memory")
    monkeypatch.setattr(mod, "run_moss", boom)
    asr = MossASR(queue.Queue(), queue.Queue(), config=None, media_type="audio", interval=10, audio_file="/rec/pod.wav")
    asr.running = True
    asr._transcribe_file()
    items = _drain(asr.transcript_queue)
    assert isinstance(items[0], AsrFailed) and "out of memory" in asr.error and items[-1] is None


# --- the defaults (source-level contracts, as the other post-hoc tests do) ------

def _read(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return f.read()


def test_moss_is_the_post_hoc_default_everywhere():
    server = _read("src", "audio_processing", "server_posthoc.py")
    assert "self.asr_choice = data.get('asr') or 'moss'" in server
    assert "== 'moss'" in server and "from asr_connectors.moss_asr import MossASR" in server
    assert 'models.get("asr", "moss")' in _read("src", "server", "posthoc_queue.py")
    ui = _read("frontend", "src", "components", "posthoc", "posthoc-trigger.jsx")
    assert 'podModels.asr || "moss"' in ui and '{ id: "moss"' in ui
    assert 'disabled={running || asr === "moss"}' in ui      # the diarizer picker is moot for MOSS


def test_the_word_timing_helper_matches_the_other_engines():
    # whisperx_asr falls back to the segment span as a single word when alignment
    # skips tokens; MOSS always emits that shape, so downstream timing is unchanged.
    wx = _read("src", "audio_processing", "asr_connectors", "whisperx_asr.py")
    assert 'words = [(text, segment.get("start", 0.0), segment.get("end", 0.0))]' in wx


def test_audio_seconds_reads_the_pods_float_wav(tmp_path, monkeypatch):
    # The pods record 32-bit float WAV, which the wave module refuses
    # ("unknown format"); the worker's duration must still come out right,
    # with or without soundfile on the box.
    import struct
    import wave
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "moss_cli", os.path.join(ROOT, "src", "audio_processing", "asr_connectors", "moss_cli.py"))
    moss_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(moss_cli)
    rate, seconds = 16000, 2.5
    frames = int(rate * seconds)
    data = struct.pack("<%df" % frames, *([0.0] * frames))
    fmt = struct.pack("<HHIIHH", 3, 1, rate, rate * 4, 4, 32)   # format 3 = IEEE float
    path = tmp_path / "pod_orig.wav"
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt) + 8 + len(data)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<I", len(fmt)) + fmt)
        f.write(b"data" + struct.pack("<I", len(data)) + data)
    with pytest.raises(wave.Error):
        wave.open(str(path))
    assert moss_cli.audio_seconds(str(path)) == pytest.approx(seconds)
    # the header fallback alone (no soundfile) agrees
    monkeypatch.setitem(sys.modules, "soundfile", None)
    assert moss_cli.audio_seconds(str(path)) == pytest.approx(seconds)
