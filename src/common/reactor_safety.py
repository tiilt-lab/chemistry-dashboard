"""The single sanctioned boundary between worker threads and the Twisted reactor.

Autobahn/Twisted transports and reactor state are NOT thread-safe. The audio,
video, and device WebSocket services all run a single reactor plus a fan of
worker threads (per-utterance ASR, per-batch video analytics, blocking HTTP
callbacks, ffmpeg, model inference). Historically every service re-discovered
that a transport write from a worker thread corrupts WebSocket framing, and
"fixed" it ad hoc with a local ``reactor.callFromThread`` — or forgot to, and
shipped a heisenbug. That is an architectural gap: the thread boundary was
*remembered* at each call site instead of *enforced* in one place.

This module is that one place. Two rules, and a contract test
(tests/test_sweep_contracts.py) that fails CI if either is bypassed:

  1. Every transport write goes through ``send_message`` / ``send_json`` —
     which marshal onto the reactor. No code calls ``transport.sendMessage``
     directly.
  2. Every piece of blocking work started from reactor-driven code goes
     through ``defer_blocking`` — which runs it off the reactor thread.

The reactor and thread-pool are resolved lazily and are injectable
(``set_reactor`` / ``set_threads``) so this is unit-testable without a running
reactor (and under CI, which has no Twisted installed).
"""
import json
import logging

_reactor = None
_threads = None


def set_reactor(reactor):
    """Test seam: inject a fake reactor. Pass None to reset."""
    global _reactor
    _reactor = reactor


def set_threads(threads):
    """Test seam: inject a fake twisted.internet.threads. Pass None to reset."""
    global _threads
    _threads = threads


def _get_reactor():
    global _reactor
    if _reactor is None:
        from twisted.internet import reactor
        _reactor = reactor
    return _reactor


def _get_threads():
    global _threads
    if _threads is None:
        from twisted.internet import threads
        _threads = threads
    return _threads


def send_message(protocol, payload, is_binary=False):
    """Write bytes to an autobahn WebSocket transport from ANY thread.

    Always marshals onto the reactor: from a worker thread this makes the
    write thread-safe; from the reactor thread it simply schedules it for the
    next iteration. Never calls ``protocol.sendMessage`` inline.

    The actual send is wrapped so it CANNOT raise into the reactor loop: the
    write runs later on the reactor, and a closed transport (autobahn
    Disconnected) would otherwise surface as an unhandled reactor error, not
    something the calling thread's try/except could catch.
    """
    flag = bool(is_binary)

    def _send():
        try:
            protocol.sendMessage(payload, flag)
        except Exception as e:
            # Best-effort: the socket may already be gone (inactivity close,
            # client refresh). A failed notify must not fault the reactor.
            logging.debug("reactor_safety: transport send failed: %s", e)

    _get_reactor().callFromThread(_send)


def send_json(protocol, message):
    """JSON-encode ``message`` and send it over ``protocol``.

    Best-effort by design: an unserializable payload or a dead transport is
    logged, never raised — a failed status/notify send must not kill the
    worker thread that produced it (or the reactor).
    """
    try:
        payload = json.dumps(message).encode("utf8")
    except (TypeError, ValueError):
        logging.warning("reactor_safety.send_json: unserializable payload: %r", message)
        return
    send_message(protocol, payload, False)


def defer_blocking(fn, *args, **kwargs):
    """Run blocking work (DB, HTTP, ffmpeg, model inference) OFF the reactor
    thread and return a Deferred, so reactor-driven code never blocks the
    reactor. Attach ``.addErrback`` for failure handling.
    """
    return _get_threads().deferToThread(fn, *args, **kwargs)
