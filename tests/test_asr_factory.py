"""CrisperWhisper is the only live ASR (Google Cloud Speech removed
2026-10-13). The factory maps every legacy key to it, the session route
accepts nothing else, the post-hoc server has no Google path, and the Google
connector, its key file and its client library are gone from the tree."""
import ast
import os
import re
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUDIO = os.path.join(ROOT, "src", "audio_processing")
sys.path.insert(0, AUDIO)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _factory(monkeypatch):
    # The real connector imports torch and the worker pool; a stub records
    # its construction instead.
    made = []

    class CrisperWhisperASR:
        def __init__(self, *args):
            made.append(args)

    stub = types.ModuleType("asr_connectors.crisperwhisper_asr")
    stub.CrisperWhisperASR = CrisperWhisperASR
    monkeypatch.setitem(sys.modules, "asr_connectors.crisperwhisper_asr", stub)
    sys.modules.pop("asr_connectors.factory", None)
    import asr_connectors.factory as factory
    return factory, made, CrisperWhisperASR


def test_every_key_runs_crisperwhisper(monkeypatch, caplog):
    factory, made, cls = _factory(monkeypatch)
    assert factory.normalize(None) == ("crisperwhisper", None)
    assert factory.normalize(" CrisperWhisper ") == ("crisperwhisper", None)
    assert factory.normalize("google-cloud-speech")[1].startswith("legacy")
    assert factory.normalize("whisper")[1].startswith("legacy")
    assert factory.normalize("bogus")[1].startswith("unknown")
    args = ("aq", "tq", "cfg", "media", 5)
    with caplog.at_level("INFO"):
        for key in (None, "", "crisperwhisper", "google-cloud-speech", "whisper", "bogus"):
            assert isinstance(factory.create_asr(key, *args), cls)
    assert len(made) == 6 and all(a == args for a in made)
    assert "unknown asr 'bogus'" in caplog.text
    assert "legacy 'google-cloud-speech'" in caplog.text
    assert "Google" not in "".join(r.message for r in caplog.records if r.levelname == "INFO")


def test_google_connector_key_and_library_are_gone():
    connectors = os.path.join(AUDIO, "asr_connectors")
    assert not any(f.startswith("google") for f in os.listdir(connectors) if f.endswith(".py"))
    assert "google-cloud-speech" not in _read("src", "requirements-unified.txt")
    posthoc = _read("src", "audio_processing", "server_posthoc.py")
    assert "GoogleASR" not in posthoc and "google_asr_connector" not in posthoc
    assert "self.asr_choice = 'crisperwhisper'" in posthoc
    assert "batch_asr = True" in posthoc and "buffer_seconds = 7200\n" in posthoc
    config = _read("src", "audio_processing", "config.py")
    assert "config.get('processing', 'asr', fallback='crisperwhisper')" in config


def test_session_route_accepts_only_crisperwhisper():
    src = _read("src", "server", "routes", "session.py")
    tree = ast.parse(src)
    create = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "create_session")
    body = ast.get_source_segment(src, create)
    assert "if asr is not None and asr != 'crisperwhisper':" in body
    assert "google" not in body.lower().replace("google cloud speech was removed", "")
    callback = _read("src", "server", "routes", "callback.py")
    assert "models = {'asr': 'crisperwhisper'," in callback


def test_frontend_offers_no_google_engine():
    create = _read("frontend", "src", "create-session", "html-pages.jsx")
    assert "google-cloud-speech" not in create
    # The session form no longer offers an engine at all (CrisperWhisper is
    # the only one, mentioned in a comment); the server defaults it.
    assert 'value: "crisperwhisper"' not in create
    assert "google" not in create.lower()
    trigger = _read("frontend", "src", "components", "posthoc", "posthoc-trigger.jsx")
    options = trigger[trigger.index("const ASR_OPTIONS"):trigger.index("const DIARIZER_OPTIONS")]
    assert "google" not in options.lower()
    assert re.search(r'id: "crisperwhisper"', options)
