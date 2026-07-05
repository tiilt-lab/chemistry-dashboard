"""In-memory tracker of which pods currently have a full post-hoc analysis
running. Fed by the processing services' callbacks: posthoc_reset marks a scope
(audio/video) running; posthoc_completed clears it. A TTL guards against runs
that die without completing (crash, service restart) leaving a stale badge.
State is per-Flask-process and intentionally ephemeral.
"""

import time
import threading

_TTL_SECONDS = 3 * 3600  # a full run takes minutes; anything older is stale
_lock = threading.Lock()
_running = {}  # (device_id, scope) -> started_epoch


def _prune():
    cutoff = time.time() - _TTL_SECONDS
    for k in [k for k, ts in _running.items() if ts < cutoff]:
        _running.pop(k, None)


def mark_running(device_id, scope):
    with _lock:
        _running[(int(device_id), scope or 'audio')] = time.time()


def mark_done(device_id, scope=None):
    # scope None (e.g. the browser's completion post) clears both scopes.
    with _lock:
        if scope:
            _running.pop((int(device_id), scope), None)
        else:
            for s in ('audio', 'video'):
                _running.pop((int(device_id), s), None)


def is_running(device_id):
    with _lock:
        _prune()
        return any(d == int(device_id) for d, _ in _running)


def running_device_ids():
    with _lock:
        _prune()
        return {d for d, _ in _running}


_durations = {}  # device_id -> last-known duration, held across a run's wipe


def remember_duration(device_id, seconds):
    if seconds is not None:
        _durations[int(device_id)] = int(seconds)


def last_duration(device_id):
    return _durations.get(int(device_id))
