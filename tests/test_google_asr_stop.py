"""Google ASR connector STOP-sentinel regression test.

The posthoc connector could never finish: generator() returned on the STOP
sentinel but left self.running True, so processing() built a fresh generator
that blocked forever on the empty queue — the run hung and pinned the pod's
buffers until service restart. STOP must be terminal (running -> False), and
chunks drained before the sentinel must still be yielded.

The connector imports google.cloud and a project config at module load; both
are stubbed here so the test runs under CI's pytest+numpy env.
"""
import os
import sys
import types
from queue import Queue

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

# --- stub the heavy / environment imports before importing the connector ---
_speech = types.ModuleType("google.cloud.speech")
_speech_v1p1 = types.ModuleType("google.cloud.speech_v1p1beta1")
_cloud = types.ModuleType("google.cloud")
_google = types.ModuleType("google")
_api_core = types.ModuleType("google.api_core")
_exceptions = types.ModuleType("google.api_core.exceptions")
_exceptions.InvalidArgument = type("InvalidArgument", (Exception,), {})
_exceptions.OutOfRange = type("OutOfRange", (Exception,), {})
for name, mod in [
    ("google", _google), ("google.cloud", _cloud),
    ("google.cloud.speech", _speech),
    ("google.cloud.speech_v1p1beta1", _speech_v1p1),
    ("google.api_core", _api_core),
    ("google.api_core.exceptions", _exceptions),
]:
    sys.modules.setdefault(name, mod)

# config.initialize() runs at module load and sets a credentials env var.
sys.modules.setdefault("config", types.SimpleNamespace(initialize=lambda: None))

from asr_connectors.google_asr_connector_posthoc import GoogleASR  # noqa: E402


class _Cfg:
    auth_key = "test-pod"


STOP = object()


def _connector():
    c = GoogleASR(Queue(), Queue(), _Cfg(), "audio", 10, STOP)
    c.running = True
    return c


def test_stop_is_terminal_and_yields_drained_chunk():
    c = _connector()
    c.audio_queue.put(b"\x00" * 3200)  # 0.1s of 16k pcm16
    c.audio_queue.put(STOP)
    chunks = list(c.generator())
    assert chunks == [b"\x00" * 3200]          # drained chunk still yielded
    assert c.running is False                    # STOP flipped the loop off
    assert abs(c.audio_time - 0.1) < 1e-9        # audio_time updated on exit


def test_stop_as_first_item_terminates_immediately():
    c = _connector()
    c.audio_queue.put(STOP)
    assert list(c.generator()) == []
    assert c.running is False


def test_none_sentinel_also_terminal():
    c = _connector()
    c.audio_queue.put(None)
    assert list(c.generator()) == []
