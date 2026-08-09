"""Model-table hygiene: no dead crypto imports; consistent UTC timestamps.

Seven non-crypto tables carried a verbatim dead import block
(hashlib/os/binascii/random/string/re) that nothing used. And user.py's json()
emitted creation_date with a ' UTC' suffix but last_login without one, so the
frontend's stringToDate parsed last_login as LOCAL time instead of UTC.
(These modules import Flask-SQLAlchemy, so this is a source-level contract.)
"""
import os

TABLES = os.path.join(os.path.dirname(__file__), "..", "src", "server", "tables")


def _read(name):
    with open(os.path.join(TABLES, name)) as f:
        return f.read()


def test_dead_crypto_imports_removed():
    dead = ("import hashlib", "import binascii", "import random",
            "import string")
    for name in ("rater.py", "rating.py", "survey_response.py", "student.py",
                 "llm_feedback_report.py", "llm_question_answer.py",
                 "session_synthesized_report.py"):
        s = _read(name)
        for imp in dead:
            assert imp not in s, f"{name}: dead `{imp}` must be removed"


def test_user_last_login_is_utc_tagged_like_creation_date():
    s = _read("user.py")
    assert "last_login=(str(self.last_login) + ' UTC')" in s, \
        "last_login must carry the ' UTC' suffix (guarded for null) like creation_date"
