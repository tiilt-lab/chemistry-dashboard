"""A session's join code when the starter chooses it instead of drawing a
random word (passcode_words.py).

Printed materials and slides carry the code (nublinc.com/join/MOON), so a
replacement session for the same class must be able to keep it. The rules
below are pure so they are unit-testable; the "not in use by another open
session" check needs the database and lives in database.py.
"""
import re

MIN_LENGTH = 3
# The join page keeps the first 16 characters of a typed code.
MAX_LENGTH = 16
_CODE_RE = re.compile(r"^[A-Z0-9]+$")


def normalize(raw):
    """(code, error) for a form/API value. None/blank means "not chosen":
    the server draws a random word as before. Codes are stored upper-case,
    which is how the join page sends them."""
    if raw is None:
        return None, None
    if not isinstance(raw, str):
        return None, "The join code must be text."
    code = raw.strip().upper()
    if not code:
        return None, None
    if len(code) < MIN_LENGTH or len(code) > MAX_LENGTH:
        return None, "The join code must be %d to %d characters." % (MIN_LENGTH, MAX_LENGTH)
    if not _CODE_RE.match(code):
        return None, "The join code may only use letters and digits."
    return code, None


def in_use_message(code, session_name):
    """Why a chosen code was refused: another open session owns it. Ended
    sessions free their code, so the fix is to end that one or pick another."""
    return ("The join code %s is in use by the open session \"%s\". "
            "End that session first, or choose another code." % (code, session_name))
