"""The live-socket handlers must stay registered.

routes/socket.py registers the /session socketio event handlers purely as an
import side effect (the @socketio.on decorators run at import time). It is
imported by discussion_capture.py and referenced by no name, so a linter sees
it as "unused" — and a ruff --fix once removed it, which unregistered the
namespace and made every client's room_joined never fire (pods loaded forever).
Pin the import so that can't recur silently.
"""
import os

SERVER = os.path.join(os.path.dirname(__file__), "..", "src", "server")


def _read(name):
    with open(os.path.join(SERVER, name)) as f:
        return f.read()


def test_discussion_capture_imports_the_socket_handlers():
    s = _read("discussion_capture.py")
    assert "from routes import socket" in s, \
        "discussion_capture.py must import routes.socket to register the /session socketio handlers"


def test_socket_module_registers_the_session_namespace():
    s = _read(os.path.join("routes", "socket.py"))
    assert "@socketio.on('connect', namespace='/session')" in s
    assert "join_room" in s  # the join_room / room_joined flow the overview waits on
