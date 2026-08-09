"""Enforces the reactor/thread boundary as a CI gate (architecture fix #2).

The recurring heisenbug across three sweeps was a transport write from a
worker thread, or blocking work on the reactor thread. Now there is exactly
one sanctioned path (src/common/reactor_safety.py). This test fails if any
service module goes around it — so the boundary is enforced by CI, not by
remembering it at each call site.
"""
import os
import re

SRC = os.path.join(os.path.dirname(__file__), "..", "src")

# Every dir whose modules run in a Twisted service (reactor + worker threads).
SERVICE_DIRS = [
    ("audio_processing",),
    ("video_processing",),
    ("common",),
    ("server",),
]
# The helper itself is the ONLY place these primitives may appear.
ALLOWED = {"reactor_safety.py"}
# Vendored model code under video_processing isn't service plumbing.
SKIP_SUBSTR = ("/venv", "/UA/", "video_cartoonizer/model/", "/migrations/")

RAW_SEND = re.compile(r"\.sendMessage\s*\(")
RAW_DEFER = re.compile(r"\bdeferToThread\s*\(")


def _service_py_files():
    for parts in SERVICE_DIRS:
        base = os.path.join(SRC, *parts)
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(root, fn)
                if any(s in path.replace(os.sep, "/") for s in SKIP_SUBSTR):
                    continue
                if fn in ALLOWED:
                    continue
                yield path


def test_no_raw_transport_writes_outside_helper():
    offenders = []
    for path in _service_py_files():
        with open(path) as f:
            for i, line in enumerate(f, 1):
                if RAW_SEND.search(line):
                    offenders.append(f"{os.path.relpath(path, SRC)}:{i}")
    assert not offenders, (
        "Raw transport writes bypass reactor_safety.send_message/send_json "
        "(thread-unsafe): " + ", ".join(offenders))


def test_no_raw_defer_to_thread_outside_helper():
    offenders = []
    for path in _service_py_files():
        with open(path) as f:
            for i, line in enumerate(f, 1):
                if RAW_DEFER.search(line):
                    offenders.append(f"{os.path.relpath(path, SRC)}:{i}")
    assert not offenders, (
        "Raw deferToThread bypasses reactor_safety.defer_blocking: "
        + ", ".join(offenders))


def test_helper_exposes_the_boundary_api():
    import sys
    sys.path.insert(0, os.path.join(SRC, "common"))
    import reactor_safety
    for name in ("send_message", "send_json", "defer_blocking",
                 "set_reactor", "set_threads"):
        assert hasattr(reactor_safety, name), f"reactor_safety missing {name}"
