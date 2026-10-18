"""DiariZen as a post-hoc diarizer: the subprocess wrapper (run_diarizen —
success, non-zero exit, timeout, missing venv), the WhisperX connector's
diarizen branch (same word attachment + enrolled reconciliation as
Sortformer, pyannote 3.1 fallback when the subprocess fails, and the
``diarizer_used`` provenance that server_posthoc records), and the trigger
panel's option list. The services import torch/twisted, so the GPU pipeline
is driven here with stub whisperx/torch modules."""
import json
import os
import subprocess
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))

from asr_connectors import diarizen_diar  # noqa: E402


@pytest.fixture
def venv(tmp_path, monkeypatch):
    # The venv is a host artefact (not in the tree); point the wrapper at a
    # file that exists so the missing-venv guard passes.
    python = tmp_path / "python"
    python.write_text("")
    monkeypatch.setattr(diarizen_diar, "_DIARIZEN_PYTHON", str(python))
    return str(python)


def _out_path(cmd):
    return cmd[cmd.index("--out") + 1]


def test_run_diarizen_returns_turns_and_removes_the_temp_file(venv, monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        with open(_out_path(cmd), "w") as f:
            json.dump({"turns": [{"start": 0.5, "end": 2.0, "speaker": "speaker_0"},
                                 {"start": 1.8, "end": 3.1, "speaker": "speaker_1"}]}, f)
        return subprocess.CompletedProcess(cmd, 0, stdout="wrote 2 turns", stderr="")

    monkeypatch.setattr(diarizen_diar.subprocess, "run", fake_run)
    turns = diarizen_diar.run_diarizen("/rec/pod_redu.wav")
    assert turns == [(0.5, 2.0, "speaker_0"), (1.8, 3.1, "speaker_1")]
    cmd = seen["cmd"]
    assert cmd[:2] == [venv, diarizen_diar._CLI] and cmd[2] == "/rec/pod_redu.wav"
    assert cmd[cmd.index("--model") + 1] == "BUT-FIT/diarizen-wavlm-large-s80-md-v2"
    assert cmd[cmd.index("--max-speakers") + 1] == "8"
    assert cmd[cmd.index("--batch") + 1] == "16"
    assert seen["kw"]["timeout"] == 60 * 60
    # Offline: a missing network must never block a run.
    assert seen["kw"]["env"]["HF_HUB_OFFLINE"] == "1"
    assert not os.path.exists(_out_path(cmd))


def test_run_diarizen_passes_overrides(venv, monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        with open(_out_path(cmd), "w") as f:
            json.dump({"turns": []}, f)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(diarizen_diar.subprocess, "run", fake_run)
    assert diarizen_diar.run_diarizen("a.wav", model="BUT-FIT/other", max_speakers=4, batch=4) == []
    cmd = seen["cmd"]
    assert cmd[cmd.index("--model") + 1] == "BUT-FIT/other"
    assert cmd[cmd.index("--max-speakers") + 1] == "4"
    assert cmd[cmd.index("--batch") + 1] == "4"


def test_run_diarizen_raises_with_the_stderr_tail_on_failure(venv, monkeypatch):
    paths = []

    def fake_run(cmd, **kw):
        paths.append(_out_path(cmd))
        return subprocess.CompletedProcess(cmd, 1, stdout="",
                                           stderr="x" * 3000 + "\nRuntimeError: CUDA out of memory")

    monkeypatch.setattr(diarizen_diar.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError) as err:
        diarizen_diar.run_diarizen("a.wav")
    msg = str(err.value)
    assert msg.startswith("diarizen_cli failed (rc=1)")
    assert "CUDA out of memory" in msg and len(msg) < 2100
    assert not os.path.exists(paths[0])


def test_run_diarizen_turns_a_timeout_into_a_runtime_error(venv, monkeypatch):
    paths = []

    def fake_run(cmd, **kw):
        paths.append(_out_path(cmd))
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(diarizen_diar.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="timed out after 3600s"):
        diarizen_diar.run_diarizen("a.wav")
    assert not os.path.exists(paths[0])


def test_run_diarizen_without_the_venv_raises_before_spawning(tmp_path, monkeypatch):
    monkeypatch.setattr(diarizen_diar, "_DIARIZEN_PYTHON", str(tmp_path / "missing" / "python"))

    def fake_run(cmd, **kw):
        raise AssertionError("must not spawn")

    monkeypatch.setattr(diarizen_diar.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="DiariZen venv missing"):
        diarizen_diar.run_diarizen("a.wav")


# ---- WhisperX connector: diarizen branch + fallback ------------------------

class _Pipeline:
    """Stub whisperx/torch so _run_gpu_pipeline runs on CPU with a canned
    transcript; records what the pyannote path and the reconciliation saw."""

    def __init__(self, monkeypatch):
        self.pyannote_calls = []
        self.assigned = []
        self.reconciled = []
        segments = {"segments": [{"text": "hi", "start": 0.0, "end": 1.0,
                                  "words": [{"word": "hi", "start": 0.0, "end": 1.0}]}],
                    "language": "en"}

        torch = types.ModuleType("torch")
        torch.cuda = types.SimpleNamespace(is_available=lambda: False, empty_cache=lambda: None)
        self.torch = torch

        wx = types.ModuleType("whisperx")
        wx.load_model = lambda *a, **k: types.SimpleNamespace(transcribe=lambda *a, **k: dict(segments))
        wx.load_audio = lambda path: "audio:" + path
        wx.load_align_model = lambda **k: ("align", "meta")
        wx.align = lambda segs, *a, **k: {"segments": segs}
        diarize = types.ModuleType("whisperx.diarize")

        def assign_word_speakers(frame, result):
            self.assigned.append([tuple(r) for r in frame[["start", "end", "speaker"]].itertuples(index=False)])
            return result

        class DiarizationPipeline:
            def __init__(this, **kw):
                self.pyannote_calls.append(kw)

            def __call__(this, audio, max_speakers=None):
                import pandas as pd
                return pd.DataFrame([{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}])

        diarize.assign_word_speakers = assign_word_speakers
        diarize.DiarizationPipeline = DiarizationPipeline
        wx.diarize = diarize
        monkeypatch.setitem(sys.modules, "whisperx", wx)
        monkeypatch.setitem(sys.modules, "whisperx.diarize", diarize)

        reconcile = types.ModuleType("asr_connectors.cluster_reconcile")

        def build_cluster_to_enrolled_map(audio_file, turns, enrolled, model):
            self.reconciled.append((audio_file, list(turns), enrolled, model))
            return {t[2]: "alias" for t in turns}

        reconcile.build_cluster_to_enrolled_map = build_cluster_to_enrolled_map
        monkeypatch.setitem(sys.modules, "asr_connectors.cluster_reconcile", reconcile)


def _connector(**kw):
    from asr_connectors.whisperx_asr import WhisperXASR
    return WhisperXASR(None, None, None, "audio", 5, audio_file="/rec/pod_redu.wav", **kw)


def test_diarizen_turns_are_attached_like_sortformer_and_reconciled(monkeypatch, caplog):
    pipe = _Pipeline(monkeypatch)
    calls = []
    monkeypatch.setattr(diarizen_diar, "run_diarizen",
                        lambda path: calls.append(path) or [(0.0, 1.0, "speaker_0"), (1.0, 2.0, "speaker_1")])
    asr = _connector(diarizer="diarizen", enrolled={"ann": object()}, speaker_model="ecapa")
    assert asr.diarize and asr.diarizer_used is None
    with caplog.at_level("INFO"):
        result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert calls == ["/rec/pod_redu.wav"]
    assert pipe.assigned == [[(0.0, 1.0, "speaker_0"), (1.0, 2.0, "speaker_1")]]
    assert pipe.reconciled == [("/rec/pod_redu.wav", [(0.0, 1.0, "speaker_0"), (1.0, 2.0, "speaker_1")],
                                {"ann": pipe.reconciled[0][2]["ann"]}, "ecapa")]
    assert cluster_map == {"speaker_0": "alias", "speaker_1": "alias"}
    assert pipe.pyannote_calls == [], "pyannote must not run when DiariZen succeeded"
    assert asr.diarizer_used == "diarizen"
    assert "diarizen diarization attached" in caplog.text


def test_diarizen_failure_falls_back_to_pyannote_and_says_so(monkeypatch, caplog):
    pipe = _Pipeline(monkeypatch)

    def boom(path):
        raise RuntimeError("DiariZen venv missing at /nowhere")

    monkeypatch.setattr(diarizen_diar, "run_diarizen", boom)
    asr = _connector(diarizer="diarizen", max_speakers=3)
    with caplog.at_level("INFO"):
        result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert len(pipe.pyannote_calls) == 1
    assert pipe.assigned == [[(0.0, 1.0, "SPEAKER_00")]]
    assert cluster_map == {}
    assert asr.diarizer_used == "pyannote", "provenance must name what actually ran"
    warning = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning) == 1 and "falling back to pyannote 3.1" in warning[0].message
    assert "DiariZen venv missing" in warning[0].message
    assert "pyannote diarization attached" in caplog.text


def test_sortformer_still_raises_rather_than_falling_back(monkeypatch):
    pipe = _Pipeline(monkeypatch)
    from asr_connectors import sortformer_diar

    def boom(path):
        raise RuntimeError("NeMo venv missing")

    monkeypatch.setattr(sortformer_diar, "run_sortformer", boom)
    asr = _connector(diarizer="sortformer")
    with pytest.raises(RuntimeError, match="NeMo venv missing"):
        asr._run_gpu_pipeline(pipe.torch)
    assert pipe.pyannote_calls == [] and asr.diarizer_used is None


def test_no_diarizer_leaves_provenance_untouched(monkeypatch):
    pipe = _Pipeline(monkeypatch)
    asr = _connector()
    result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert pipe.assigned == [] and pipe.pyannote_calls == []
    assert asr.diarizer_used is None and cluster_map == {}


# ---- trigger panel ----------------------------------------------------------

def test_trigger_panel_offers_diarizen_and_defaults_to_it():
    with open(os.path.join(ROOT, "frontend", "src", "components", "posthoc", "posthoc-trigger.jsx"),
              encoding="utf-8") as f:
        trigger = f.read()
    options = trigger[trigger.index("const DIARIZER_OPTIONS"):trigger.index("const EMBEDDER_OPTIONS")]
    for choice in ("fingerprint", "diarizen", "pyannote", "sortformer"):
        assert 'id: "%s"' % choice in options, choice
    diarizen = options[options.index('id: "diarizen"'):].splitlines()[0]
    assert "DiariZen Large-s80-v2" in diarizen and "research licence" in diarizen
    assert 'podModels.diarizer || "diarizen"' in trigger
    assert 'diarizen: "DiariZen"' in trigger
