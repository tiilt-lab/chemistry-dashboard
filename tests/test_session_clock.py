"""src/server/session_clock.py: the processors' clock follows the database's."""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

import session_clock  # noqa: E402

STARTED = datetime(2026, 10, 16, 14, 3, 22)


def test_server_start_uses_the_processors_format():
    assert session_clock.server_start_value(STARTED) == "2026-10-16 14:03:22"
    # processing_config.py parses it back with this format
    assert datetime.strptime(session_clock.server_start_value(STARTED), "%Y-%m-%d %H:%M:%S") == STARTED


def test_moves_a_stale_server_start_and_keeps_the_rest():
    raw = json.dumps({"server_start": "2026-10-15 20:31:26", "transcribe": True, "keywords": ["x"], "asr": None})
    config, previous = session_clock.synced_config(raw, STARTED)
    assert previous == "2026-10-15 20:31:26"
    assert config == {"server_start": "2026-10-16 14:03:22", "transcribe": True, "keywords": ["x"], "asr": None}


def test_a_config_that_agrees_is_left_alone():
    raw = json.dumps({"server_start": "2026-10-16 14:03:22", "transcribe": True})
    assert session_clock.synced_config(raw, STARTED) == (None, "2026-10-16 14:03:22")
    assert session_clock.synced_config(raw.encode("utf-8"), STARTED) == (None, "2026-10-16 14:03:22")


def test_missing_or_broken_config_is_not_invented():
    for raw in (None, "", b"", "not json", json.dumps(["list"])):
        assert session_clock.synced_config(raw, STARTED) == (None, None)
