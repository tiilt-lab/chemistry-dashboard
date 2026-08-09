"""Tests for the resource-centric authorization layer (src/server/authz.py).

The architectural point: you cannot obtain a resource without the caller being
authorized for it — resolution and access are fused in one call. These tests
inject fake data/access seams so the authorization LOGIC is verified without
Flask or a DB (CI has neither).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

import authz  # noqa: E402


class _Device:
    def __init__(self, id, session_id, key=None):
        self.id = id
        self.session_id = session_id
        self.processing_key = key


class _Transcript:
    def __init__(self, id, session_device_id):
        self.id = id
        self.session_device_id = session_device_id


def _configure(devices, transcripts, owner_of, key_ok=lambda d: False):
    """owner_of: dict session_id -> owner user id. session_access mirrors the
    app's owner/super/admin(read) matrix using the injected map."""
    def get_device(did):
        return devices.get(did)

    def get_transcript(tid):
        return transcripts.get(tid)

    def session_access(session_id, user, write):
        role = user.get("role", "user")
        if role == "super":
            return session_id in owner_of
        if role == "admin" and not write:
            return session_id in owner_of
        return owner_of.get(session_id) == user.get("id")

    authz.configure(authz.Deps(
        get_device=get_device,
        get_transcript=get_transcript,
        session_access=session_access,
        key_grants=key_ok,
    ))


OWNER = {"id": 1, "role": "user"}
OTHER = {"id": 2, "role": "user"}
ADMIN = {"id": 9, "role": "admin"}
SUPER = {"id": 8, "role": "super"}


def setup_function(_):
    devices = {10: _Device(10, session_id=100, key="podkey")}
    transcripts = {500: _Transcript(500, session_device_id=10)}
    _configure(devices, transcripts, owner_of={100: 1})


def test_owner_can_resolve_their_device():
    assert authz.resolve_device(10, OWNER) is not None


def test_other_tenant_cannot_resolve_device():
    assert authz.resolve_device(10, OTHER) is None       # denied == missing


def test_missing_device_is_none():
    assert authz.resolve_device(999, OWNER) is None


def test_admin_reads_but_cannot_write_others_device():
    assert authz.resolve_device(10, ADMIN, write=False) is not None
    assert authz.resolve_device(10, ADMIN, write=True) is None


def test_super_can_write():
    assert authz.resolve_device(10, SUPER, write=True) is not None


def test_processing_key_grants_read_even_without_session_access():
    # BYOD client holds the pod key; it may read its own pod without a login.
    _configure({10: _Device(10, 100, key="podkey")}, {}, owner_of={100: 1},
               key_ok=lambda d: d.processing_key == "podkey")
    assert authz.resolve_device(10, OTHER, write=False) is not None
    # ...but the key does not grant WRITE.
    assert authz.resolve_device(10, OTHER, write=True) is None


def test_resolve_transcript_scopes_through_owning_session():
    t = authz.resolve_transcript(500, OWNER)
    assert t is not None and t.id == 500
    assert authz.resolve_transcript(500, OTHER) is None   # cross-tenant blocked


def test_resolve_transcript_missing_is_none():
    assert authz.resolve_transcript(4242, OWNER) is None


def test_device_in_session_membership():
    assert authz.device_in_session(10, 100) is not None
    assert authz.device_in_session(10, 999) is None       # wrong session
    assert authz.device_in_session(777, 100) is None       # missing device
