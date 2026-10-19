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
sys.path.insert(0, os.path.join(ROOT, "src", "common"))   # recording_sidecar, as the service has it

from asr_connectors import moss_run  # noqa: E402
from asr_connectors.base_asr import AsrFailed  # noqa: E402
from asr_connectors.moss_asr import MossASR  # noqa: E402


# --- the wrapper --------------------------------------------------------------

def test_wrapper_builds_the_cli_command_and_sorts_the_turns(monkeypatch):
    seen = {}

    def fake_worker(build_argv, timeout, handle=None, **kwargs):
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

def _connector(monkeypatch, turns, roster=("Pat3G1S32",), partner=("Bo Example",), audio=None, prints=None, rows=None):
    """A connector whose recording is synthetic (a speaker = a constant sample
    value, the embedder a one-hot of it) and whose naming rows come in by
    hand, so the ported rules run end to end without the model or the API."""
    import numpy as np
    import asr_connectors.moss_asr as mod
    monkeypatch.setattr(mod, "run_moss", lambda *a, **k: {"turns": turns, "tokens_per_s": 40.0})
    sr = 100
    audio = np.zeros(sr * 200, dtype=np.float32) if audio is None else audio
    monkeypatch.setattr(mod, "_read_audio", lambda path: (audio, sr))

    def onehot(k):
        v = np.zeros(8, dtype=np.float32); v[k] = 1.0
        return v
    monkeypatch.setattr(mod, "_embedder", lambda model: (lambda sig: onehot(int(round(float(np.mean(sig)))))))
    monkeypatch.setattr(mod, "_enrolment_print", lambda alias, model: (prints or {}).get(alias))
    config = types.SimpleNamespace(auth_key="1436-k", start_offset=0.0)
    asr = MossASR(queue.Queue(), queue.Queue(), config=config, media_type="audio", interval=10,
                  audio_file="/rec/pod.wav", hotwords=["Viking"], enrolled=None, speaker_model="ecapa",
                  roster=list(roster), naming_rows={"device": 1436, "partner": 1447, "partner_speakers": list(partner), "rows": rows or []})
    asr.running = True
    return asr


def _drain(q):
    out = []
    while True:
        item = q.get(timeout=1)
        out.append(item)
        if item is None:
            return out


def _audio(spans, sr=100):
    import numpy as np
    n = int(max(e for _, e, _ in spans) * sr) + sr
    a = np.zeros(n, dtype=np.float32)
    for s, e, k in spans:
        a[int(s * sr):int(e * sr)] = k
    return a


def _onehot(k):
    import numpy as np
    v = np.zeros(8, dtype=np.float32); v[k] = 1.0
    return v


def test_connector_names_speakers_from_both_rosters_prints_and_emits_one_result_per_turn(monkeypatch):
    # Pat3 (own) has an enrolment print; Bo (far) none, but the live rows named
    # her confidently for 30 s on this recording, so she gets a session print.
    turns = [{"start": 0.0, "end": 50.0, "speaker": "S01", "text": "we hold the debt"},
             {"start": 50.0, "end": 100.0, "speaker": "S02", "text": "the market is bad"},
             {"start": 100.0, "end": 100.5, "speaker": "S03", "text": "okay"},
             {"start": 101.0, "end": 102.0, "speaker": "S01", "text": "   "}]
    audio = _audio([(0, 50, 1), (50, 100, 2), (100, 100.5, 3)])
    rows = [{"device": 1447, "start_time": 50, "length": 30, "speaker_tag": "Bo Example", "sim": 0.8, "far_side": False}]
    asr = _connector(monkeypatch, turns, audio=audio, prints={"Pat3G1S32": _onehot(1)}, rows=rows)
    asr._transcribe_file()
    out = _drain(asr.transcript_queue)
    assert out[-1] is None and len(out) == 4               # blank-text turn skipped
    tags = [(r.speaker_tag, r.alternatives[0].transcript) for r in out[:-1]]
    assert tags == [("Pat3G1S32", "we hold the debt"), ("Bo Example", "the market is bad"), (None, "okay")]
    first, second, third = out[:3]
    assert first.named_by_asr and first.speaker_confidence["named_by"] == "prints" and first.speaker_confidence["cluster"] == "S01"
    assert first.speaker_confidence["percent"] >= 0 and "far_side" not in first.speaker_confidence
    assert second.speaker_confidence["far_side"] is True            # Bo sits across the table
    assert third.speaker_confidence == {"cluster": "S03"}          # half a second of voice: not scored
    assert asr.diarizer_used == "moss"


def test_connector_without_any_print_keeps_turns_unnamed_and_flagged(monkeypatch):
    asr = _connector(monkeypatch, [{"start": 0.0, "end": 5.0, "speaker": "S01", "text": "hi"}], roster=(), partner=())
    asr._transcribe_file()
    out = _drain(asr.transcript_queue)
    assert out[0].speaker_tag is None and out[0].named_by_asr and out[0].speaker_confidence == {"cluster": "S01"}


def test_a_naming_failure_still_sends_the_transcript(monkeypatch):
    import asr_connectors.moss_asr as mod
    asr = _connector(monkeypatch, [{"start": 0.0, "end": 5.0, "speaker": "S01", "text": "hi"}])
    monkeypatch.setattr(mod, "_read_audio", lambda path: (_ for _ in ()).throw(OSError("no such recording")))
    asr._transcribe_file()
    out = _drain(asr.transcript_queue)
    assert out[0].alternatives[0].transcript == "hi" and out[0].speaker_tag is None and out[-1] is None


def test_the_processor_keeps_a_connector_named_turn_instead_of_rechecking_prints():
    src = open(os.path.join(ROOT, "src", "audio_processing", "processor_posthoc.py")).read()
    i = src.index("if named_by_asr or (self.config.diarization and self.fingerprints and len(self.fingerprints)):")
    j = src.index("if named_by_asr:", i)
    assert j < src.index("checkFingerprints(", i)
    assert "speaker_confidence" in src[j:j + 900]


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
    assert 'const diarizer = asr === "moss" ? "moss" : "fingerprint"' in ui   # no diarizer picker: the engine decides


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
