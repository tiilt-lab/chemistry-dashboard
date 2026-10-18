"""The two post-hoc diarizers, DiariZen and Nemotron-3: the subprocess
wrappers (run_diarizen / run_nemotron3 — success, non-zero exit, timeout,
missing venv), the WhisperX connector's choice + mutual fallback (same word
attachment and enrolled reconciliation as Sortformer; the OTHER diarizer runs
when the chosen one fails; both failing fails the run, never pyannote), the
``diarizer_used`` provenance server_posthoc records, and the trigger panel's
two-option contract. The services import torch/twisted, so the GPU pipeline
is driven here with stub whisperx/torch modules."""
import json
import os
import queue
import subprocess
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))

from asr_connectors import diarizen_diar, nemotron_diar  # noqa: E402
from asr_connectors.base_asr import AsrFailed  # noqa: E402


# ---- subprocess wrappers ----------------------------------------------------

_WRAPPERS = {
    "diarizen": dict(mod=diarizen_diar, run=diarizen_diar.run_diarizen, python_attr="_DIARIZEN_PYTHON",
                     cli="diarizen_cli", venv="DiariZen venv missing",
                     flags={"--model": "BUT-FIT/diarizen-wavlm-large-s80-md-v2", "--max-speakers": "8",
                            "--batch": "16"}),
    "nemotron3": dict(mod=nemotron_diar, run=nemotron_diar.run_nemotron3, python_attr="_NEMO3_PYTHON",
                      cli="nemotron_cli", venv="Nemotron-3 venv missing",
                      flags={"--model": "nvidia/Nemotron-3-Diarization", "--preset": "offline"}),
}


@pytest.fixture(params=sorted(_WRAPPERS), ids=sorted(_WRAPPERS))
def wrapper(request, tmp_path, monkeypatch):
    w = types.SimpleNamespace(name=request.param, **_WRAPPERS[request.param])
    # The venvs are host artefacts (not in the tree); point the wrapper at a
    # file that exists so the missing-venv guard passes.
    python = tmp_path / request.param / "python"
    python.parent.mkdir()
    python.write_text("")
    monkeypatch.setattr(w.mod, w.python_attr, str(python))
    w.python = str(python)
    return w


def _out_path(cmd):
    return cmd[cmd.index("--out") + 1]


def test_wrapper_returns_turns_and_removes_the_temp_file(wrapper, monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        with open(_out_path(cmd), "w") as f:
            json.dump({"turns": [{"start": 0.5, "end": 2.0, "speaker": "speaker_0"},
                                 {"start": 1.8, "end": 3.1, "speaker": "speaker_1"}]}, f)
        return subprocess.CompletedProcess(cmd, 0, stdout="wrote 2 turns", stderr="")

    monkeypatch.setattr(wrapper.mod.subprocess, "run", fake_run)
    turns = wrapper.run("/rec/pod_redu.wav")
    assert turns == [(0.5, 2.0, "speaker_0"), (1.8, 3.1, "speaker_1")]
    cmd = seen["cmd"]
    assert cmd[:2] == [wrapper.python, wrapper.mod._CLI] and cmd[2] == "/rec/pod_redu.wav"
    assert os.path.basename(wrapper.mod._CLI) == wrapper.cli + ".py"
    for flag, value in wrapper.flags.items():
        assert cmd[cmd.index(flag) + 1] == value, flag
    assert seen["kw"]["timeout"] == 60 * 60
    # Offline: a missing network must never block a run.
    assert seen["kw"]["env"]["HF_HUB_OFFLINE"] == "1"
    assert not os.path.exists(_out_path(cmd))


def test_wrapper_raises_with_the_stderr_tail_on_failure(wrapper, monkeypatch):
    paths = []

    def fake_run(cmd, **kw):
        paths.append(_out_path(cmd))
        return subprocess.CompletedProcess(cmd, 1, stdout="",
                                           stderr="x" * 3000 + "\nRuntimeError: CUDA out of memory")

    monkeypatch.setattr(wrapper.mod.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError) as err:
        wrapper.run("a.wav")
    msg = str(err.value)
    assert msg.startswith("%s failed (rc=1)" % wrapper.cli)
    assert "CUDA out of memory" in msg and len(msg) < 2100
    assert not os.path.exists(paths[0])


def test_wrapper_turns_a_timeout_into_a_runtime_error(wrapper, monkeypatch):
    paths = []

    def fake_run(cmd, **kw):
        paths.append(_out_path(cmd))
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(wrapper.mod.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="%s timed out after 3600s" % wrapper.cli):
        wrapper.run("a.wav")
    assert not os.path.exists(paths[0])


def test_wrapper_without_the_venv_raises_before_spawning(wrapper, tmp_path, monkeypatch):
    monkeypatch.setattr(wrapper.mod, wrapper.python_attr, str(tmp_path / "missing" / "python"))

    def fake_run(cmd, **kw):
        raise AssertionError("must not spawn")

    monkeypatch.setattr(wrapper.mod.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match=wrapper.venv):
        wrapper.run("a.wav")


def _capture(mod, monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        with open(_out_path(cmd), "w") as f:
            json.dump({"turns": []}, f)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return seen


def test_run_diarizen_passes_overrides(tmp_path, monkeypatch):
    (tmp_path / "python").write_text("")
    monkeypatch.setattr(diarizen_diar, "_DIARIZEN_PYTHON", str(tmp_path / "python"))
    seen = _capture(diarizen_diar, monkeypatch)
    assert diarizen_diar.run_diarizen("a.wav", model="BUT-FIT/other", max_speakers=4, batch=4) == []
    cmd = seen["cmd"]
    assert cmd[cmd.index("--model") + 1] == "BUT-FIT/other"
    assert cmd[cmd.index("--max-speakers") + 1] == "4"
    assert cmd[cmd.index("--batch") + 1] == "4"


def test_run_nemotron3_passes_overrides(tmp_path, monkeypatch):
    (tmp_path / "python").write_text("")
    monkeypatch.setattr(nemotron_diar, "_NEMO3_PYTHON", str(tmp_path / "python"))
    seen = _capture(nemotron_diar, monkeypatch)
    assert nemotron_diar.run_nemotron3("a.wav", model="nvidia/other", preset="offline") == []
    cmd = seen["cmd"]
    assert cmd[cmd.index("--model") + 1] == "nvidia/other"
    assert cmd[cmd.index("--preset") + 1] == "offline"


# ---- WhisperX connector: choice, fallback, provenance ------------------------

class _Pipeline:
    """Stub whisperx/torch so the connector runs on CPU with a canned
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
        torch.load = lambda *a, **k: None   # permissive_torch_load wraps it
        self.torch = torch
        monkeypatch.setitem(sys.modules, "torch", torch)

        # CI has no pandas: this is the sliver of DataFrame the connector
        # (pd.DataFrame(rows), len) and these stubs (column select,
        # itertuples, iterrows) touch.
        class _Frame:
            def __init__(this, rows):
                this.rows = [dict(r) for r in rows]

            def __len__(this):
                return len(this.rows)

            def __getitem__(this, cols):
                return _Frame([{c: r[c] for c in cols} for r in this.rows])

            def itertuples(this, index=False):
                return (tuple(r.values()) for r in this.rows)

            def iterrows(this):
                return ((i, r) for i, r in enumerate(this.rows))

        pandas = types.ModuleType("pandas")
        pandas.DataFrame = _Frame
        monkeypatch.setitem(sys.modules, "pandas", pandas)

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


DZ_TURNS = [(0.0, 1.0, "speaker_0"), (1.0, 2.0, "speaker_1")]
N3_TURNS = [(0.0, 0.7, "speaker_0"), (0.7, 2.0, "speaker_1"), (2.0, 2.5, "speaker_2")]


def _stub_diarizers(monkeypatch, diarizen=None, nemotron3=None):
    """Each value is a turns list (success) or an Exception (failure);
    records the order the wrappers were called in."""
    calls = []

    def make(name, outcome):
        def run(path):
            calls.append((name, path))
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return run

    monkeypatch.setattr(diarizen_diar, "run_diarizen", make("diarizen", diarizen))
    monkeypatch.setattr(nemotron_diar, "run_nemotron3", make("nemotron3", nemotron3))
    return calls


def _connector(**kw):
    from asr_connectors.whisperx_asr import WhisperXASR
    return WhisperXASR(None, kw.pop("transcript_queue", None), None, "audio", 5,
                       audio_file="/rec/pod_redu.wav", **kw)


def test_the_connector_offers_exactly_the_two_diarizers():
    from asr_connectors.whisperx_asr import POSTHOC_DIARIZERS
    assert POSTHOC_DIARIZERS == ("diarizen", "nemotron3")


def test_chosen_diarizen_is_attached_like_sortformer_and_reconciled(monkeypatch, caplog):
    pipe = _Pipeline(monkeypatch)
    calls = _stub_diarizers(monkeypatch, diarizen=DZ_TURNS, nemotron3=N3_TURNS)
    asr = _connector(diarizer="diarizen", enrolled={"ann": object()}, speaker_model="ecapa")
    assert asr.diarize and asr.diarizer_used is None
    with caplog.at_level("INFO"):
        result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert calls == [("diarizen", "/rec/pod_redu.wav")], "the other diarizer must not run"
    assert pipe.assigned == [DZ_TURNS]
    assert pipe.reconciled[0][:2] == ("/rec/pod_redu.wav", DZ_TURNS) and pipe.reconciled[0][3] == "ecapa"
    assert cluster_map == {"speaker_0": "alias", "speaker_1": "alias"}
    assert pipe.pyannote_calls == []
    assert asr.diarizer_used == "diarizen"
    assert "diarizen diarization attached" in caplog.text
    assert not [r for r in caplog.records if r.levelname == "WARNING"]


def test_chosen_nemotron3_runs_alone_when_it_succeeds(monkeypatch, caplog):
    pipe = _Pipeline(monkeypatch)
    calls = _stub_diarizers(monkeypatch, diarizen=DZ_TURNS, nemotron3=N3_TURNS)
    asr = _connector(diarizer="nemotron3", enrolled={"ann": object()}, speaker_model="ecapa")
    with caplog.at_level("INFO"):
        result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert calls == [("nemotron3", "/rec/pod_redu.wav")]
    assert pipe.assigned == [N3_TURNS]
    assert pipe.reconciled[0][1] == N3_TURNS
    assert cluster_map == {"speaker_0": "alias", "speaker_1": "alias", "speaker_2": "alias"}
    assert pipe.pyannote_calls == [] and asr.diarizer_used == "nemotron3"
    assert "nemotron3 diarization attached" in caplog.text


def test_diarizen_failure_runs_nemotron3_and_provenance_says_so(monkeypatch, caplog):
    pipe = _Pipeline(monkeypatch)
    calls = _stub_diarizers(monkeypatch, diarizen=RuntimeError("DiariZen venv missing at /nowhere"),
                            nemotron3=N3_TURNS)
    asr = _connector(diarizer="diarizen")
    with caplog.at_level("INFO"):
        result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert [c[0] for c in calls] == ["diarizen", "nemotron3"]
    assert pipe.assigned == [N3_TURNS]
    assert pipe.pyannote_calls == [], "pyannote is never the fallback"
    assert asr.diarizer_used == "nemotron3", "provenance must name what actually ran"
    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "diarizen diarization failed" in warnings[0] and "DiariZen venv missing" in warnings[0]
    assert "falling back to nemotron3" in warnings[0]
    assert "nemotron3 diarization attached" in caplog.text


def test_nemotron3_failure_runs_diarizen_and_provenance_says_so(monkeypatch, caplog):
    pipe = _Pipeline(monkeypatch)
    calls = _stub_diarizers(monkeypatch, diarizen=DZ_TURNS,
                            nemotron3=RuntimeError("nemotron_cli failed (rc=1): boom"))
    asr = _connector(diarizer="nemotron3")
    with caplog.at_level("INFO"):
        result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert [c[0] for c in calls] == ["nemotron3", "diarizen"]
    assert pipe.assigned == [DZ_TURNS]
    assert pipe.pyannote_calls == [] and asr.diarizer_used == "diarizen"
    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "nemotron3 diarization failed" in warnings[0] and "boom" in warnings[0]
    assert "falling back to diarizen" in warnings[0]


def test_both_failing_fails_the_run_naming_both_and_never_runs_pyannote(monkeypatch, caplog):
    pipe = _Pipeline(monkeypatch)
    calls = _stub_diarizers(monkeypatch, diarizen=RuntimeError("DiariZen venv missing at /a"),
                            nemotron3=RuntimeError("nemotron_cli timed out after 3600s"))
    out = queue.Queue()
    asr = _connector(diarizer="diarizen", transcript_queue=out)
    # Through the connector's own failure path: the run fails (AsrFailed ->
    # posthoc_failed, previous results kept) instead of quietly degrading.
    with caplog.at_level("INFO"):
        asr._transcribe_file()
    assert [c[0] for c in calls] == ["diarizen", "nemotron3"]
    assert pipe.pyannote_calls == [] and pipe.assigned == []
    assert asr.diarizer_used is None
    failed = out.get_nowait()
    assert isinstance(failed, AsrFailed)
    assert failed.reason.startswith("both post-hoc diarizers failed")
    assert "diarizen: DiariZen venv missing at /a" in failed.reason
    assert "nemotron3: nemotron_cli timed out after 3600s" in failed.reason
    assert asr.error == failed.reason
    assert out.get_nowait() is None   # the end-of-stream sentinel still follows
    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1 and "falling back to nemotron3" in warnings[0]


def test_legacy_sortformer_choice_still_raises_rather_than_falling_back(monkeypatch):
    pipe = _Pipeline(monkeypatch)
    calls = _stub_diarizers(monkeypatch, diarizen=DZ_TURNS, nemotron3=N3_TURNS)
    from asr_connectors import sortformer_diar

    def boom(path):
        raise RuntimeError("NeMo venv missing")

    monkeypatch.setattr(sortformer_diar, "run_sortformer", boom)
    asr = _connector(diarizer="sortformer")
    with pytest.raises(RuntimeError, match="NeMo venv missing"):
        asr._run_gpu_pipeline(pipe.torch)
    assert calls == [] and pipe.pyannote_calls == [] and asr.diarizer_used is None


def test_no_diarizer_leaves_provenance_untouched(monkeypatch):
    pipe = _Pipeline(monkeypatch)
    calls = _stub_diarizers(monkeypatch, diarizen=DZ_TURNS, nemotron3=N3_TURNS)
    asr = _connector()
    result, cluster_map = asr._run_gpu_pipeline(pipe.torch)
    assert calls == [] and pipe.assigned == [] and pipe.pyannote_calls == []
    assert asr.diarizer_used is None and cluster_map == {}


# ---- trigger panel ----------------------------------------------------------

def test_trigger_panel_offers_exactly_the_two_diarizers_and_defaults_to_diarizen():
    with open(os.path.join(ROOT, "frontend", "src", "components", "posthoc", "posthoc-trigger.jsx"),
              encoding="utf-8") as f:
        trigger = f.read()
    options = trigger[trigger.index("const DIARIZER_OPTIONS"):trigger.index("const DIARIZER_DEFAULT")]
    ids = [line.split('id: "')[1].split('"')[0] for line in options.splitlines() if 'id: "' in line]
    assert ids == ["diarizen", "nemotron3"]
    for gone in ("fingerprint", "pyannote", "sortformer"):
        assert gone not in options, gone
    diarizen = options[options.index('id: "diarizen"'):].splitlines()[0]
    assert "DiariZen Large-s80-v2" in diarizen and "research licence" in diarizen
    nemotron = options[options.index('id: "nemotron3"'):].splitlines()[0]
    assert "Nemotron-3 Diarization" in nemotron and "OpenMDW licence" in nemotron
    assert 'const DIARIZER_DEFAULT = "diarizen"' in trigger
    assert "diarizerChoice || storedDiarizer || DIARIZER_DEFAULT" in trigger
    # A pod last analysed by pyannote/sortformer/voice prints must not prefill
    # a choice that is no longer offered.
    assert "DIARIZER_OPTIONS.some((o) => o.id === podModels.diarizer)" in trigger
    # ...but those legacy names still display on the provenance chip.
    for shown in ('pyannote: "pyannote"', 'sortformer: "Sortformer"', 'fingerprint: "voice prints"',
                  'diarizen: "DiariZen"', 'nemotron3: "Nemotron-3"'):
        assert shown in trigger, shown
