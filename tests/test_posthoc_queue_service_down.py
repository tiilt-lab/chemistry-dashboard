"""A post-hoc service that refuses the connection is restarting (its idle
recycle exits the process to hand the GPU memory back; the RSS recycle and
deploys restart it too). The queue must defer the job like gpu_busy, not mark
the pod failed."""
import asyncio
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.modules.setdefault('posthoc_state',
                       types.SimpleNamespace(is_running=lambda d: False))

import posthoc_queue as q  # noqa: E402


def test_refused_connection_defers_the_leg(monkeypatch):
    async def refuse(url):
        raise q._ServiceUnavailable(url, "ConnectionRefusedError")
    monkeypatch.setattr(q, "_connect", refuse)
    with pytest.raises(q._GpuBusy) as info:  # the worker loop's deferral path
        q._run_leg("ws://127.0.0.1:1/audio", {}, "start_posthoc_audio_processing", 7, "audio", 0)
    busy = info.value
    assert isinstance(busy, q._ServiceUnavailable)
    assert busy.retry_after == q._ServiceUnavailable.RETRY
    assert "127.0.0.1:1" in str(busy) and "ConnectionRefusedError" in str(busy)


class _FailingConnect:
    """websockets.connect(...) is an async context manager; the handshake
    failure surfaces from __aenter__."""
    def __init__(self, failure):
        self.failure = failure

    async def __aenter__(self):
        raise self.failure

    async def __aexit__(self, *a):
        return False


def _fake_websockets(failure):
    return types.SimpleNamespace(connect=lambda url, open_timeout=None: _FailingConnect(failure))


def test_connect_maps_refusal_and_open_timeout(monkeypatch):
    monkeypatch.setitem(sys.modules, "websockets",
                        _fake_websockets(ConnectionRefusedError(111, "Connection refused")))
    with pytest.raises(q._ServiceUnavailable):
        asyncio.run(q._connect("ws://127.0.0.1:1/video"))
    monkeypatch.setitem(sys.modules, "websockets", _fake_websockets(asyncio.TimeoutError()))
    with pytest.raises(q._ServiceUnavailable):
        asyncio.run(q._connect("ws://127.0.0.1:1/video"))


def test_other_connect_errors_still_fail(monkeypatch):
    monkeypatch.setitem(sys.modules, "websockets", _fake_websockets(ValueError("bad handshake")))
    with pytest.raises(ValueError):
        asyncio.run(q._connect("ws://127.0.0.1:1/video"))
