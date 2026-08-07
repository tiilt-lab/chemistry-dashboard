"""Filesystem-name sanitizers shared by the processing services.

The enrollment WebSocket handlers build recording/biometric paths from an
`alias` taken straight off the socket. Without a check, `../../x` is arbitrary
file write/delete. These helpers enforce the app's own alias rules
(Speaker.NAME_CHARS = "a-zA-Z0-9._:' -", max 64) at the socket boundary — that
charset excludes / and \\, so a name that passes cannot contain a path
separator. basename() and an explicit dot-only reject are belt-and-braces.
"""
import os
import re

# Same character class as src/server/tables/speaker.py NAME_CHARS.
_ALLOWED = re.compile(r"^[A-Za-z0-9._:' -]{1,64}$")
_MEDIA_EXTS = {'webm', 'mp4', 'ogg', 'wav'}


class UnsafeName(ValueError):
    """Raised when a name can't be made safe for use in a path."""


def safe_name(value):
    """Return a filesystem-safe leaf name or raise UnsafeName.

    Requires the app's alias charset (which excludes / and \\) and rejects
    dot-only names, so a traversal attempt like '../x' is refused outright
    rather than silently collapsed to its basename. The basename call is
    belt-and-braces given the charset already bars separators.
    """
    raw = str(value or '').strip()
    if not raw or set(raw) <= {'.'} or not _ALLOWED.match(raw):
        raise UnsafeName('unsafe name: {0!r}'.format(value))
    name = os.path.basename(raw)
    if name != raw:
        raise UnsafeName('unsafe name: {0!r}'.format(value))
    return name


def safe_media_ext(value, default='webm'):
    """Allowlist a client-supplied media extension; fall back to default."""
    ext = str(value or '').lower().lstrip('.')
    return ext if ext in _MEDIA_EXTS else default
