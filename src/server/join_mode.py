"""How a session's devices join by default: with audio only, or with video.

Set once by the session starter (create-session form), stored on
session.join_mode, read by the join page (which option "Join with" opens
on). Pure functions, no Flask or DB, so the rules are unit-testable.
"""

AUDIO = 'audio'
VIDEO = 'video'
MODES = (AUDIO, VIDEO)


def normalize(raw):
    """(mode, error) for a form/API value. None/'' means "not chosen", which
    is stored as NULL and reads back as audio."""
    if raw in (None, ''):
        return None, None
    if not isinstance(raw, str):
        return None, "joinMode must be 'audio' or 'video'."
    mode = raw.strip().lower()
    if mode not in MODES:
        return None, "joinMode must be 'audio' or 'video'."
    return mode, None


def effective(stored):
    """What the join page should preselect for a stored value: only an
    explicit 'video' opens on Video; NULL and anything else mean audio."""
    return VIDEO if stored == VIDEO else AUDIO
