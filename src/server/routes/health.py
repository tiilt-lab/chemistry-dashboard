"""Operational health endpoint: the numbers we otherwise SSH in to check
(GPU memory, host RAM, disk, live pods, post-hoc queue depth, service
uptimes). Read-only, best-effort — every probe degrades to None rather than
failing the whole response, so the ops view still renders during trouble.
"""
import os
import shutil
import subprocess
import time

from flask import Blueprint
from utility import json_response
import wrappers

api_routes = Blueprint('health', __name__)

_SERVICES = [
    "blinc-discussion-capture.service",
    "blinc-audio-processor.service",
    "blinc-video-processor.service",
    "blinc-audio-posthoc-processor.service",
    "blinc-video-posthoc-processor.service",
]


def _run(cmd, timeout=5):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except Exception:
        return ""


def _gpu():
    out = _run(["nvidia-smi",
                "--query-gpu=memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits"])
    try:
        used, total, util = [int(x) for x in out.split(",")]
        return {"mem_used_mb": used, "mem_total_mb": total,
                "mem_pct": round(100 * used / total) if total else None,
                "util_pct": util}
    except Exception:
        return None


def _host_ram():
    try:
        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                k, _, v = line.partition(":")
                info[k.strip()] = int(v.strip().split()[0])  # kB
        total, avail = info.get("MemTotal", 0), info.get("MemAvailable", 0)
        return {"total_gb": round(total / 2**20, 1),
                "available_gb": round(avail / 2**20, 1),
                "used_pct": round(100 * (total - avail) / total) if total else None}
    except Exception:
        return None


def _disk():
    try:
        u = shutil.disk_usage("/")
        return {"free_gb": round(u.free / 1e9, 1),
                "total_gb": round(u.total / 1e9, 1),
                "used_pct": round(100 * u.used / u.total)}
    except Exception:
        return None


def _services():
    out = {}
    for svc in _SERVICES:
        active = _run(["systemctl", "is-active", svc]) or "unknown"
        # ActiveEnterTimestamp -> seconds of uptime
        uptime = None
        ts = _run(["systemctl", "show", svc, "-p",
                   "ActiveEnterTimestampMonotonic", "--value"])
        try:
            mono_us = int(ts)
            if mono_us > 0:
                now_us = time.clock_gettime(time.CLOCK_MONOTONIC) * 1e6
                uptime = int((now_us - mono_us) / 1e6)
        except Exception:
            pass
        short = svc.replace("blinc-", "").replace(".service", "")
        out[short] = {"active": active, "uptime_s": uptime}
    return out


def _live_pods():
    # Connected devices across active sessions (the live-recording count).
    try:
        import database
        sessions = database.get_sessions(active=True) or []
        n = 0
        for s in sessions:
            for d in database.get_session_devices(session_id=s.id):
                if getattr(d, "connected", False):
                    n += 1
        return {"connected_devices": n, "active_sessions": len(sessions)}
    except Exception:
        return None


def _queue():
    try:
        import posthoc_queue
        jobs = posthoc_queue.status()
        from collections import Counter
        by = Counter(j["state"] for j in jobs)
        return {"queued": by.get("queued", 0), "running": by.get("running", 0),
                "error": by.get("error", 0), "total": len(jobs)}
    except Exception:
        return None


@api_routes.route('/api/v1/health', methods=['GET'])
@wrappers.verify_login()
def health(**kwargs):
    return json_response({
        "gpu": _gpu(),
        "host_ram": _host_ram(),
        "disk": _disk(),
        "services": _services(),
        "live": _live_pods(),
        "posthoc_queue": _queue(),
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
