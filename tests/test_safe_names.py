"""Path-traversal-safe leaf names — one implementation, three call sites.

common/safe_names.safe_name is the canonical guard (raises UnsafeName). The
server had two more hand copies: utility.safe_name (returns None) and
routes/session.py _face_thumb_path (which only did os.path.basename — the
WEAKEST of the three: no charset or dot-only reject). All three now route
through the canonical one; the server sites catch UnsafeName -> None.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))

from safe_names import safe_name, safe_media_ext, UnsafeName  # noqa: E402


def test_accepts_a_normal_alias():
    assert safe_name("Ada Lovelace") == "Ada Lovelace"
    assert safe_name("student_01") == "student_01"


def test_rejects_path_traversal_and_separators():
    for bad in ("../etc/passwd", "a/b", "a\\b", "..", "...", "", "   ", None):
        try:
            safe_name(bad)
            assert False, f"expected UnsafeName for {bad!r}"
        except UnsafeName:
            pass


def test_rejects_overlong_and_out_of_charset():
    for bad in ("x" * 65, "na<me>", "semi;colon"):
        try:
            safe_name(bad)
            assert False, f"expected UnsafeName for {bad!r}"
        except UnsafeName:
            pass


def test_media_ext_allowlist():
    assert safe_media_ext("mp4") == "mp4"
    assert safe_media_ext(".WEBM") == "webm"
    assert safe_media_ext("exe") == "webm"  # falls back


def test_server_copies_delegate_to_common():
    root = os.path.join(os.path.dirname(__file__), "..", "src", "server")
    with open(os.path.join(root, "utility.py")) as f:
        util = f.read()
    assert "from safe_names import" in util, "utility.safe_name must delegate to common"
    assert "except UnsafeName" in util, "utility must map UnsafeName -> None"
    with open(os.path.join(root, "routes", "session.py")) as f:
        sess = f.read()
    # _face_thumb_path must no longer be a bare basename-only guard.
    assert "safe_name(" in sess, "_face_thumb_path must use the shared safe_name"
