"""The session clock the processors stamp transcripts against.

The audio service reads ``server_start`` from the session's Redis config
(written once by session_handler.create_session) and stamps every transcript
relative to it. The database's session.creation_date is the dashboard's
clock, and the first device to join moves it (database.create_byod_
session_device: a session set up ahead of class counts from its first join).
The two must agree, or every transcript lands outside the dashboard's
window: session 434 on 2026-10-16 had waited 17.5 hours in the lobby, and
its transcripts were stamped 17.5 hours into a 15-minute session. Pure, so
the rule is unit-testable; the Redis round trip is the handler's.
"""
import json

SERVER_START_FORMAT = "%Y-%m-%d %H:%M:%S"


def server_start_value(creation_date):
    """The ``server_start`` string the processors parse (processing_config.py
    uses this exact format)."""
    return creation_date.strftime(SERVER_START_FORMAT)


def synced_config(raw, creation_date):
    """(config dict to store, previous value) when the stored session config
    needs its server_start moved to ``creation_date``; (None, previous) when
    it already agrees, is missing (a session from before Redis held one) or
    is not JSON (left alone rather than invented)."""
    if not raw:
        return None, None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    try:
        config = json.loads(raw)
    except (TypeError, ValueError):
        return None, None
    if not isinstance(config, dict):
        return None, None
    previous = config.get("server_start")
    want = server_start_value(creation_date)
    if previous == want:
        return None, previous
    config["server_start"] = want
    return config, previous
