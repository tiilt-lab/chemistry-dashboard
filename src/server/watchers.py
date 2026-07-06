# In-process registry of "someone has this session's dashboard open".
# The session overview polls GET /sessions/<id>/devices every 2s while the
# page is open, so a recent poll means an instructor is actively watching.
# Single-process service (Flask + scheduler share the interpreter), so a
# module-level dict is sufficient; entries are a few bytes and harmless
# after a session ends.
import time

_last_watched = {}


def mark_watched(session_id):
    _last_watched[int(session_id)] = time.time()


def watched_within(session_id, seconds):
    ts = _last_watched.get(int(session_id))
    return ts is not None and (time.time() - ts) < seconds
