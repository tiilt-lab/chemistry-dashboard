"""Shared autobahn onMessage/onClose for the audio+video WS services.

The audio and video services, live and post-hoc, had four byte-identical
onMessage/onClose bodies — except that only ONE of the four logged the full
traceback when process_json raised; the other three logged str(e) and threw
the stack away, so a post-hoc processing failure was near-undebuggable. The
shared mixin fixes that everywhere. It only touches self.process_*/send_json/
signal_end, so it's testable with a fake protocol (the real ones subclass
autobahn, which isn't installed in CI).
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))

from ws_protocol import WsMessageMixin  # noqa: E402


class _FakeProto(WsMessageMixin):
    def __init__(self):
        self.last_message = None
        self.json_calls = []
        self.binary_calls = []
        self.sent = []
        self.ended = 0
        self.raise_on_json = False

    def process_json(self, data):
        self.json_calls.append(data)
        if self.raise_on_json:
            raise ValueError("boom-in-process-json")

    def process_binary(self, payload):
        self.binary_calls.append(payload)

    def send_json(self, message):
        self.sent.append(message)

    def signal_end(self):
        self.ended += 1


def test_valid_json_dispatches_to_process_json():
    p = _FakeProto()
    p.onMessage(b'{"type": "start", "n": 3}', is_binary=False)
    assert p.json_calls == [{"type": "start", "n": 3}]
    assert p.sent == []
    assert p.last_message is not None


def test_binary_dispatches_to_process_binary():
    p = _FakeProto()
    p.onMessage(b"\x00\x01", is_binary=True)
    assert p.binary_calls == [b"\x00\x01"]
    assert p.json_calls == []


def test_malformed_json_sends_error_and_skips_process_json():
    p = _FakeProto()
    p.onMessage(b"not json", is_binary=False)
    assert p.json_calls == []
    assert p.sent == [{"type": "error", "message": "Payload is not properly formatted JSON."}]


def test_process_json_failure_logs_full_traceback_and_is_swallowed(caplog):
    p = _FakeProto()
    p.raise_on_json = True
    with caplog.at_level(logging.WARNING):
        p.onMessage(b'{"type": "x"}', is_binary=False)  # must not raise
    joined = "\n".join(r.getMessage() for r in caplog.records)
    # The stack (Traceback / the raising line) must be present, not just str(e).
    assert "Traceback" in joined and "boom-in-process-json" in joined


def test_onclose_signals_end():
    p = _FakeProto()
    p.onClose(True, 1000, "bye")
    assert p.ended == 1


def test_all_four_servers_share_the_mixin():
    src = os.path.join(os.path.dirname(__file__), "..", "src")
    servers = [
        ("audio_processing", "server.py"),
        ("audio_processing", "server_posthoc.py"),
        ("video_processing", "server.py"),
        ("video_processing", "server_posthoc.py"),
    ]
    for parts in servers:
        with open(os.path.join(src, *parts)) as f:
            s = f.read()
        name = "/".join(parts)
        assert "WsMessageMixin, WebSocketServerProtocol" in s, \
            f"{name}: ServerProtocol must inherit the shared mixin"
        assert "def onMessage" not in s and "def onClose" not in s, \
            f"{name}: onMessage/onClose must come from the mixin"
        assert "Error processing json" not in s, \
            f"{name}: the (drifted) inline json-error log must be gone"
