"""Persistence tests for the posthoc queue: restarts must restore pending
jobs (and re-queue any job that was mid-run when the process died)."""
import json
import os
import sys
import types
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

# posthoc_state has no heavy deps, but stub it so this test stays hermetic.
sys.modules.setdefault('posthoc_state',
                       types.SimpleNamespace(is_running=lambda d: False))


class _NoStartThread(threading.Thread):
    def start(self):  # the worker would fire real service triggers
        pass


def _import_queue():
    real = threading.Thread
    threading.Thread = _NoStartThread
    try:
        import posthoc_queue
        return posthoc_queue
    finally:
        threading.Thread = real


def test_restore_requeues_running_and_persists(tmp_path):
    q = _import_queue()
    state = tmp_path / "posthoc_queue.json"
    q._state_file = lambda: str(state)

    jobs = [
        {"session_id": 1, "device_id": 10, "state": "done", "models": None,
         "error": None, "queued_at": 1.0, "started_at": 2.0, "finished_at": 3.0},
        {"session_id": 1, "device_id": 11, "state": "running", "models": None,
         "error": None, "queued_at": 1.0, "started_at": 2.0, "finished_at": None},
    ]
    state.write_text(json.dumps(jobs))

    real = threading.Thread
    threading.Thread = _NoStartThread
    try:
        q._restore()
    finally:
        threading.Thread = real

    st = {j["device_id"]: j["state"] for j in q.status()}
    assert st[10] == "done"
    assert st[11] == "queued", "job caught mid-run must be re-queued"

    assert q.clear_pending() == 1
    on_disk = json.loads(state.read_text())
    assert [j["device_id"] for j in on_disk] == [10]
