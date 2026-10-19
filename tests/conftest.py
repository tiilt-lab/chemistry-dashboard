"""Suite-wide setup, loaded by pytest before any test module.

Tests that import the real src/server/app.py attach its file log handler.
Without this, every local test run appended its log lines (fake pods,
stubbed failures) to the production src/server/discussion_capture_server.log
on the deployment host. Point it at a temp file instead, before any import.
"""
import os
import tempfile

os.environ.setdefault(
    "DC_SERVER_LOG", os.path.join(tempfile.gettempdir(), "blinc-tests-discussion_capture_server.log"))
