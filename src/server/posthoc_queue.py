"""Server-side queue for running full post-hoc analyses on multiple pods in
sequence. Jobs survive browser refreshes because the server both triggers the
runs (same WS protocol as the UI) and observes completion via posthoc_state
(fed by the services' reset/completed callbacks). One pod at a time; within a
pod, audio and video run concurrently as usual.
"""

import os
import json
import time
import logging
import threading
import asyncio

import posthoc_state

AUDIO_WS = "ws://127.0.0.1:%s" % os.getenv("DC_AUDIO_POSTHOC_WS_PORT", "9015")
VIDEO_WS = "ws://127.0.0.1:%s" % os.getenv("DC_VIDEO_POSTHOC_WS_PORT", "9014")
_POD_TIMEOUT = 150 * 60  # video-bound pods on long recordings can exceed an hour

_lock = threading.Lock()
_jobs = []  # {session_id, device_id, state: queued|running|done|error, error}
_worker = None


def _trigger(url, init, start_type):
    # Fire a run: connect, Initialize, wait for the readiness ack, send start.
    # The socket then closes; the run continues in the background (services are
    # disconnect-resilient) and completion is observed via posthoc_state.
    import websockets

    async def go():
        async with websockets.connect(url, open_timeout=15) as ws:
            await ws.send(json.dumps(init))
            deadline = time.time() + 120
            while time.time() < deadline:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
                t = msg.get("type", "")
                if t == "init posthoc analytics completed":
                    await ws.send(json.dumps({"type": start_type}))
                    return None
                if t == "error":
                    return msg.get("message", "service error")
            return "timed out waiting for init ack"

    return asyncio.run(go())


def _run_job(job):
    import app as A
    with A.app.app_context():
        import database
        session = database.get_sessions(id=job["session_id"])
        device_id = job["device_id"]
        speakers = [{"id": s.id, "alias": s.get_alias()}
                    for s in database.get_speakers(session_device_id=device_id)]
        base = {
            "sessionid": job["session_id"],
            "sessiondeviceid": device_id,
            "server_start": session.creation_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "keywords": (session.json() or {}).get("keywords") or [],
            "speakers": speakers,
        }
    models = job.get("models") or {}
    err_a = _trigger(AUDIO_WS, dict(base,
                                    type="Initialize_audio_processing_analytics",
                                    asr=models.get("asr", "whisperx"),
                                    scorer=models.get("scorer"),
                                    diarizer=models.get("diarizer", "pyannote"),
                                    embedder=models.get("embedder")),
                     "start_posthoc_audio_processing")
    err_v = _trigger(VIDEO_WS, dict(base, type="Initialize_video_processing_analytics"),
                     "start_posthoc_video_processing")
    if err_a:
        logging.warning("posthoc queue: pod %s audio trigger: %s", job["device_id"], err_a)
    if err_v:
        logging.warning("posthoc queue: pod %s video trigger: %s", job["device_id"], err_v)
    if err_a and err_v:
        raise RuntimeError("audio: %s / video: %s" % (err_a, err_v))
    # Wait for completion: the reset callback marks the device running; the
    # completed callbacks clear it. Require it to have been seen running first.
    deadline = time.time() + _POD_TIMEOUT
    seen_running = False
    while time.time() < deadline:
        running = posthoc_state.is_running(device_id)
        if running:
            seen_running = True
        elif seen_running:
            # Finished — verify the audio leg actually produced output. A silent
            # failure (OOM, empty recording) completes with zero transcripts and
            # must surface as an error, not "Analyzed".
            if not err_a:
                import app as A2
                with A2.app.app_context():
                    import database as db2
                    if db2.get_pod_duration(device_id) is None:
                        raise RuntimeError("audio produced no transcripts (empty recording or transcription failure)")
            return  # ran and finished
        time.sleep(10)
    raise RuntimeError("timed out waiting for pod %s to finish" % device_id)


def _worker_loop():
    while True:
        with _lock:
            job = next((j for j in _jobs if j["state"] == "queued"), None)
            if job is None:
                return  # drain and exit; next enqueue restarts the worker
            job["state"] = "running"
            job["started_at"] = time.time()
        try:
            _run_job(job)
            job["state"] = "done"
        except Exception as e:
            logging.warning("posthoc queue: pod %s failed: %s", job["device_id"], e)
            job["state"] = "error"
            job["error"] = str(e)
        finally:
            job["finished_at"] = time.time()


def enqueue(session_id, device_ids, models=None):
    global _worker
    with _lock:
        queued_or_running = {j["device_id"] for j in _jobs
                             if j["state"] in ("queued", "running")}
        added = []
        for d in device_ids:
            if int(d) in queued_or_running:
                continue
            _jobs.append({"session_id": int(session_id), "device_id": int(d),
                          "state": "queued", "models": models, "error": None,
                          "queued_at": time.time(),
                          "started_at": None, "finished_at": None})
            added.append(int(d))
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop,
                                       name="posthoc-queue", daemon=True)
            _worker.start()
    return added


def clear_pending():
    # Drop all queued jobs (running job finishes unless cancelled at the service).
    with _lock:
        n = 0
        for j in _jobs:
            if j["state"] == "queued":
                j["state"] = "error"; j["error"] = "cancelled"; n += 1
        return n


def status(session_id=None):
    with _lock:
        return [{"session_id": j["session_id"], "device_id": j["device_id"],
                 "state": j["state"], "error": j["error"],
                 "started_at": j.get("started_at"),
                 "finished_at": j.get("finished_at")}
                for j in _jobs
                if session_id is None or j["session_id"] == int(session_id)]
