"""The batched publish client (src/audio_processing/callbacks.py
post_transcripts_batch): one request per batch, a retryable failure tried
again inline a few times, a refusal returned at once, the stored ids on
success."""
import os
import sys
import types

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))
sys.path.insert(0, os.path.join(ROOT, "src", "common"))

pytest.importorskip("requests")


@pytest.fixture
def callbacks():
    # The audio tree's callbacks, loaded by path: the video tree has a module
    # of the same name, and whichever an earlier test bound must be put back.
    import importlib.util
    before = sys.modules.get("callbacks")
    spec = importlib.util.spec_from_file_location(
        "callbacks", os.path.join(ROOT, "src", "audio_processing", "callbacks.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["callbacks"] = module
    spec.loader.exec_module(module)
    yield module
    if before is not None:
        sys.modules["callbacks"] = before
    else:
        sys.modules.pop("callbacks", None)


def _reply(status, body=None):
    return types.SimpleNamespace(status_code=status, json=lambda: body or {})


def _fake(callbacks, replies, seen):
    def post_once(url, payload, headers, name):
        seen.append((url, len(payload["rows"]), headers.get(callbacks.callback_retry.IDEMPOTENCY_HEADER)))
        status = replies.pop(0)
        if status is None:
            return None, True
        return _reply(status, {"transcript_ids": [1, 2]}), callbacks._retryable(status)
    return post_once


def test_a_batch_lands_in_one_request_with_the_ids_back(callbacks, monkeypatch):
    seen = []
    monkeypatch.setattr(callbacks, "_post_once", _fake(callbacks, [200], seen))
    monkeypatch.setattr(callbacks, "_callback_base", lambda: "http://api/api/v1/callback")
    rows = [{"start_time": 5, "transcript": "a"}, {"start_time": 9, "transcript": "b"}]
    assert callbacks.post_transcripts_batch("pod-key", rows) == [1, 2]
    assert seen == [("http://api/api/v1/callback/transcripts_batch", 2, callbacks.callback_retry.idempotency_key("pod-key", "batch", 5))]
    assert callbacks.post_transcripts_batch("pod-key", []) == []


def test_a_retryable_failure_is_tried_again_inline_and_a_refusal_is_not(callbacks, monkeypatch):
    seen = []
    monkeypatch.setattr(callbacks, "_post_once", _fake(callbacks, [None, 503, 200], seen))
    monkeypatch.setattr(callbacks, "_callback_base", lambda: "http://api/api/v1/callback")
    rows = [{"start_time": 5, "transcript": "a"}]
    assert callbacks.post_transcripts_batch("pod-key", rows, attempts=3, backoff=0) == [1, 2] and len(seen) == 3
    seen.clear()
    monkeypatch.setattr(callbacks, "_post_once", _fake(callbacks, [503, 503], seen))
    assert callbacks.post_transcripts_batch("pod-key", rows, attempts=2, backoff=0) is None and len(seen) == 2
    seen.clear()
    monkeypatch.setattr(callbacks, "_post_once", _fake(callbacks, [400], seen))
    assert callbacks.post_transcripts_batch("pod-key", rows, attempts=3, backoff=0) is None and len(seen) == 1
