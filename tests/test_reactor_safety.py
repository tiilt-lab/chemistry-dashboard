"""Tests for the reactor/thread boundary helper (src/common/reactor_safety.py).

The whole point of this module is that a transport write is NEVER done
synchronously from the calling thread — it is always marshalled onto the
reactor via callFromThread. These tests inject a fake reactor (so they run
under CI's pytest env with no Twisted installed) and assert exactly that.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))

import reactor_safety  # noqa: E402


class _FakeReactor:
    """Records callFromThread(fn, *args) without executing fn — so a test can
    prove the send was scheduled on the reactor, not run inline. ``run_all``
    then executes the scheduled callables to test what they do."""
    def __init__(self):
        self.scheduled = []

    def callFromThread(self, fn, *args):
        self.scheduled.append((fn, args))

    def run_all(self):
        for fn, args in self.scheduled:
            fn(*args)


class _FakeThreads:
    def __init__(self):
        self.deferred = []

    def deferToThread(self, fn, *args, **kwargs):
        token = object()
        self.deferred.append((fn, args, kwargs, token))
        return token


class _FakeProtocol:
    def __init__(self):
        self.direct_calls = []           # sendMessage called INLINE (must stay empty)

    def sendMessage(self, payload, isBinary=False):
        self.direct_calls.append((payload, isBinary))


def _fresh(monkeypatch=None):
    r = _FakeReactor()
    reactor_safety.set_reactor(r)
    return r


def test_send_message_marshals_onto_reactor_never_inline():
    r = _fresh()
    p = _FakeProtocol()
    reactor_safety.send_message(p, b"hello", is_binary=False)
    # It must be SCHEDULED on the reactor, not called directly.
    assert p.direct_calls == []
    assert len(r.scheduled) == 1
    # Executing the scheduled work performs the actual send.
    r.run_all()
    assert p.direct_calls == [(b"hello", False)]


def test_send_message_binary_flag_is_boolean():
    r = _fresh()
    p = _FakeProtocol()
    reactor_safety.send_message(p, b"\x00\x01", is_binary=1)  # truthy non-bool
    r.run_all()
    assert p.direct_calls == [(b"\x00\x01", True)]


def test_send_json_encodes_and_marshals():
    r = _fresh()
    p = _FakeProtocol()
    reactor_safety.send_json(p, {"type": "start", "n": 3})
    assert p.direct_calls == []          # not inline
    r.run_all()
    import json
    (payload, is_binary), = p.direct_calls
    assert json.loads(payload.decode("utf8")) == {"type": "start", "n": 3}
    assert is_binary is False


def test_send_json_unserializable_does_not_raise_or_schedule():
    r = _fresh()
    p = _FakeProtocol()
    reactor_safety.send_json(p, {"bad": object()})  # not JSON-serializable
    assert r.scheduled == []      # nothing scheduled
    assert p.direct_calls == []   # and definitely nothing sent


def test_deferred_send_on_closed_transport_does_not_raise_into_reactor():
    # The regression this caught: the send runs LATER on the reactor; a closed
    # transport (autobahn Disconnected) must be swallowed there, not surface
    # as an unhandled reactor error.
    r = _fresh()

    class _ClosedProtocol:
        def sendMessage(self, payload, is_binary=False):
            raise RuntimeError("Attempt to send on a closed protocol")

    reactor_safety.send_json(_ClosedProtocol(), {"ok": True})
    r.run_all()  # must not raise


def test_defer_blocking_routes_through_thread_pool():
    t = _FakeThreads()
    reactor_safety.set_threads(t)

    def work(a, b):
        return a + b

    token = reactor_safety.defer_blocking(work, 1, b=2)
    assert len(t.deferred) == 1
    fn, args, kwargs, tok = t.deferred[0]
    assert fn is work and args == (1,) and kwargs == {"b": 2}
    assert token is tok  # returns the Deferred so callers can attach errbacks


def teardown_function(_):
    # Don't leak the injected fakes into other test modules.
    reactor_safety.set_reactor(None)
    reactor_safety.set_threads(None)
