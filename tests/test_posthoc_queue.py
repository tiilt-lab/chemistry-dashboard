"""Persistence tests for the posthoc queue: a coordinator (re)start must pick
up pending jobs — from Redis (re-queuing a job that was mid-run when the
process died) and, once, from the JSON snapshot the single-process server
kept before the queue moved to Redis."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# posthoc_state has no heavy deps, but stub it so this test stays hermetic.
sys.modules.setdefault('posthoc_state',
                       types.SimpleNamespace(is_running=lambda d: False))

from fake_redis import FakeRedis  # noqa: E402
import redis_sync  # noqa: E402
import posthoc_queue as q  # noqa: E402


def test_migration_requeues_running_and_retires_the_file(tmp_path, monkeypatch):
    monkeypatch.setattr(redis_sync, "_client", FakeRedis())
    state = tmp_path / "posthoc_queue.json"
    monkeypatch.setattr(q, "_state_file", lambda: str(state))

    jobs = [
        {"session_id": 1, "device_id": 10, "state": "done", "models": None,
         "error": None, "queued_at": 1.0, "started_at": 2.0, "finished_at": 3.0},
        {"session_id": 1, "device_id": 11, "state": "running", "models": None,
         "error": None, "queued_at": 1.0, "started_at": 2.0, "finished_at": None},
    ]
    state.write_text(json.dumps(jobs))

    assert q.migrate_state_file() == 1
    st = {j["device_id"]: j["state"] for j in q.status()}
    assert 10 not in st, "a settled job is not carried over"
    assert st[11] == "queued", "job caught mid-run must be re-queued"
    assert not state.exists() and (tmp_path / "posthoc_queue.json.migrated").exists()

    assert q.clear_pending() == 1
    assert q.status() == []


def test_restart_requeues_a_job_the_runner_was_on(monkeypatch):
    monkeypatch.setattr(redis_sync, "_client", FakeRedis())
    q.enqueue(1, [12])
    job = q._all_jobs()[0]
    job["state"] = "running"
    q._save(job)
    assert q._requeue_running() == 1
    (row,) = q.status()
    assert row["id"] == job["id"] and row["queued_at"] == job["queued_at"]
    assert {k: v for k, v in row.items() if k not in ("id", "queued_at")} == {
        "session_id": 1, "device_id": 12, "state": "queued", "error": None,
        "legs": ["audio", "video"], "run_id": None, "started_at": None, "finished_at": None}


def test_coding_jobs_audio_gate_persists_and_a_job_without_one_is_never_gated(monkeypatch):
    monkeypatch.setattr(redis_sync, "_client", FakeRedis())
    assert q.enqueue_coding(1, 13, 6) is True                      # queued before the gate existed
    assert q.enqueue_coding(1, 11, 5, after_audio=["11", 12]) is True
    plain, gated = q._all_jobs()
    assert "after_audio" not in plain
    assert gated["after_audio"] == [11, 12] and q._load(gated["id"])["after_audio"] == [11, 12]
    assert q._requeue_running() == 0
    assert q._load(gated["id"])["after_audio"] == [11, 12]        # a restart keeps the gate
    assert [(r["device_id"], r["state"], r["legs"], r["run_id"]) for r in q.status(1)] == [
        (13, "queued", ["coding"], 6), (11, "queued", ["coding"], 5)]
    monkeypatch.setattr(q, "_audio_done", lambda d: pytest.fail("a job without the field consults nothing"))
    assert q._audio_prerequisites(plain) == ([], [])
    assert q._next_queued()["id"] == plain["id"]
    monkeypatch.setattr(q, "_audio_done", lambda d: d == 11)
    monkeypatch.setattr(q, "_scope_running", lambda d, s: False)
    assert q._audio_prerequisites(gated) == ([], [12])             # 12: nothing will analyse it
    q.enqueue(1, [12], legs=("audio",))
    assert q._audio_prerequisites(gated) == ([12], [])             # now its audio leg is ahead


def test_a_rename_leg_goes_to_the_audio_service_and_gates_coding_like_audio(monkeypatch):
    monkeypatch.setattr(redis_sync, "_client", FakeRedis())
    assert "rename" in q.LEGS and q.LEGS.index("rename") < q.LEGS.index("coding")
    assert q._leg_url("rename") == q.AUDIO_WS and q._leg_url("audio") == q.AUDIO_WS
    assert q.enqueue(1, [21], legs=("rename",)) == [21]
    assert q.enqueue_coding(1, 21, 7, after_audio=[21]) is True
    coding = next(j for j in q._all_jobs() if j.get("run_id") == 7)
    monkeypatch.setattr(q, "_audio_done", lambda d: False)
    monkeypatch.setattr(q, "_scope_running", lambda d, s: False)
    waiting, failed = q._audio_prerequisites(coding)
    assert waiting == [21] and failed == []
