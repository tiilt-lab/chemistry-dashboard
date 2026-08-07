"""Tracker of which pods currently have a full post-hoc analysis running.
Fed by the processing services' callbacks: posthoc_reset marks a scope
(audio/video) running; posthoc_completed clears it. A TTL guards against runs
that die without completing (crash, service restart) leaving a stale badge.

State lives in Redis so it survives capture-server restarts and is shared
across processes — the original in-memory dict was wiped by a mid-run server
restart, leaving the session overview showing nothing while the analysis was
in fact still going (the pod page's websocket probes disagreed). The dict
remains as a fallback when Redis is unreachable.
"""

import time
import threading
import logging

_TTL_SECONDS = 3 * 3600  # a full run takes minutes; anything older is stale
_RUN_KEY = 'posthoc:running'        # hash: "<device_id>:<scope>" -> started epoch
_DUR_KEY = 'posthoc:last_duration'  # hash: "<device_id>" -> seconds

_lock = threading.Lock()
_mem_running = {}    # (device_id, scope) -> started_epoch (fallback)
_mem_durations = {}  # device_id -> seconds (fallback)
_redis_warned = False


def _r():
    from redis_helper import r
    return r


def _warn_once(e):
    global _redis_warned
    if not _redis_warned:
        _redis_warned = True
        logging.warning(
            "posthoc_state: Redis unavailable, using in-memory fallback: %s", e)


def _entries():
    # {(device_id, scope): started_epoch}, pruned of stale/garbled entries.
    cutoff = time.time() - _TTL_SECONDS
    try:
        raw = _r().hgetall(_RUN_KEY)
        out = {}
        stale = []
        for field, ts in raw.items():
            try:
                device, scope = field.split(':', 1)
                started = float(ts)
                device = int(device)
            except ValueError:
                stale.append(field)
                continue
            if started < cutoff:
                stale.append(field)
            else:
                out[(device, scope)] = started
        if stale:
            _r().hdel(_RUN_KEY, *stale)
        return out
    except Exception as e:
        _warn_once(e)
        with _lock:
            for k in [k for k, ts in _mem_running.items() if ts < cutoff]:
                _mem_running.pop(k, None)
            return dict(_mem_running)


def mark_running(device_id, scope):
    scope = scope or 'audio'
    try:
        _r().hset(_RUN_KEY, '{0}:{1}'.format(int(device_id), scope), time.time())
    except Exception as e:
        _warn_once(e)
        with _lock:
            _mem_running[(int(device_id), scope)] = time.time()


def mark_done(device_id, scope=None):
    # scope None (e.g. the browser's completion post) clears both scopes.
    scopes = [scope] if scope else ['audio', 'video']
    fields = ['{0}:{1}'.format(int(device_id), s) for s in scopes]
    try:
        _r().hdel(_RUN_KEY, *fields)
    except Exception as e:
        _warn_once(e)
        with _lock:
            for s in scopes:
                _mem_running.pop((int(device_id), s), None)


def clear_scope(scope):
    # A processing service (re)started: any run it had in flight died with
    # the old process. Clearing its scope lets waiting queue jobs fail fast
    # instead of sitting out the full pod timeout.
    try:
        raw = _r().hgetall(_RUN_KEY)
        stale = [f for f in raw if f.endswith(':' + scope)]
        if stale:
            _r().hdel(_RUN_KEY, *stale)
        return len(stale)
    except Exception as e:
        _warn_once(e)
        with _lock:
            stale = [k for k in _mem_running if k[1] == scope]
            for k in stale:
                _mem_running.pop(k, None)
            return len(stale)


def is_running(device_id):
    return any(d == int(device_id) for d, _ in _entries())


def running_device_ids():
    return {d for d, _ in _entries()}


def elapsed_seconds(device_id, scope):
    # Wall-clock seconds since this scope's run was marked running, or None.
    # Read at completion time (before mark_done clears the entry) to record
    # how long the audio/video module took.
    ts = _entries().get((int(device_id), scope or 'audio'))
    return int(time.time() - ts) if ts else None


def running_detail(device_id):
    # Full run state for one pod: which scopes are active and since when.
    # Serves the pod page's HTTP status poll — the websocket status probes go
    # to the processing services themselves, whose event loops starve under a
    # heavy run (observed ~2-minute wake intervals mid-analysis).
    scopes = {s: ts for (d, s), ts in _entries().items() if d == int(device_id)}
    return {'running': bool(scopes),
            'scopes': sorted(scopes),
            'started_at': min(scopes.values()) if scopes else None}


def remember_duration(device_id, seconds):
    # Last-known pod duration, held across a run's wipe (it is derived from
    # the transcripts being deleted).
    if seconds is None:
        return
    try:
        _r().hset(_DUR_KEY, str(int(device_id)), int(seconds))
    except Exception as e:
        _warn_once(e)
        _mem_durations[int(device_id)] = int(seconds)


def last_duration(device_id):
    try:
        value = _r().hget(_DUR_KEY, str(int(device_id)))
        if value is not None:
            return int(value)
    except Exception as e:
        _warn_once(e)
    return _mem_durations.get(int(device_id))
