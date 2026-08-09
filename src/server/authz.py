"""Resource-centric authorization (architecture fix #3).

Round 3 found several cross-tenant IDOR holes, all the same shape: a route
resolved an object by URL id and *forgot* to check the caller owned it, while
the route two functions over remembered. Authorization was route-centric and
copy-pasted, so every new endpoint was a fresh chance to forget.

Here resolution and authorization are FUSED: the only way to get a device or
transcript is through a resolver that also enforces access, returning the
object or None (denied and missing are indistinguishable on purpose — ids are
sequential). A route physically cannot obtain the object without the check.

The module is import-light on purpose (no ``from app import db``): its
dependencies — DB lookups, the session-access matrix, and the pod-key check —
are injected via ``configure`` at app startup, which also keeps the
authorization logic unit-testable without Flask or a database.
"""


class Deps:
    """The four seams the resolvers need. Wired in app startup; faked in tests.

    - get_device(device_id)         -> device | None
    - get_transcript(transcript_id) -> transcript | None
    - session_access(session_id, user, write) -> bool   (owner/super/admin-read)
    - key_grants(device)            -> bool   (a valid pod processing key for
                                               THIS device is present on the
                                               request; grants READ only)
    """
    def __init__(self, get_device, get_transcript, session_access, key_grants):
        self.get_device = get_device
        self.get_transcript = get_transcript
        self.session_access = session_access
        self.key_grants = key_grants


_deps = None


def configure(deps):
    global _deps
    _deps = deps


def _access(session_id, user, write):
    return bool(user) and _deps.session_access(session_id, user, write)


def resolve_device(device_id, user, write=False):
    """The pod named by ``device_id``, IF the caller may touch it at the
    requested level, else None. Read is granted by session access OR a valid
    pod processing key; write requires session access (owner/super)."""
    device = _deps.get_device(device_id)
    if device is None:
        return None
    if not write and _deps.key_grants(device):
        return device
    if _access(device.session_id, user, write):
        return device
    return None


def resolve_transcript(transcript_id, user, write=False):
    """The transcript named by ``transcript_id``, scoped through its owning
    pod's session, else None. Returns the transcript object."""
    transcript = _deps.get_transcript(transcript_id)
    if transcript is None:
        return None
    device = _deps.get_device(transcript.session_device_id)
    if device is None:
        return None
    if not write and _deps.key_grants(device):
        return transcript
    if _access(device.session_id, user, write):
        return transcript
    return None


def device_in_session(device_id, session_id):
    """Membership only: the pod exists AND belongs to ``session_id``. For
    routes already guarded on the session that just need to reject a pod id
    from another session."""
    device = _deps.get_device(device_id)
    if device is not None and device.session_id == session_id:
        return device
    return None
