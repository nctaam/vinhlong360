"""Durable owner-write admission contracts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from owner_write_gate import (
    OwnerWriteBlocked,
    OwnerWriteGate,
    owner_key_for_user,
)


USER_ID = "00000000-0000-0000-0000-000000000001"
OWNER_KEY = f"user:{USER_ID}"
ANON_OWNER = "anon:" + "a" * 64


class MutableStateReader:
    def __init__(self, deleted_at=None):
        self.deleted_at = deleted_at
        self.calls = []
        self.error = None

    def __call__(self, user_id):
        self.calls.append(user_id)
        if self.error is not None:
            raise self.error
        return self.deleted_at


def test_active_authenticated_owner_is_checked_on_every_write():
    """Caching an active decision would permit writes after a later deletion."""
    reader = MutableStateReader()
    gate = OwnerWriteGate(reader)

    gate.assert_writable(OWNER_KEY)
    gate.assert_writable(OWNER_KEY)

    assert reader.calls == [USER_ID, USER_ID]


def test_deleted_owner_is_blocked_after_restart():
    """A fresh process must still honor durable deleted_at state."""
    deleted_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
    first_reader = MutableStateReader(deleted_at)
    first_gate = OwnerWriteGate(first_reader)

    with pytest.raises(OwnerWriteBlocked, match="OWNER_WRITE_BLOCKED"):
        first_gate.assert_writable(OWNER_KEY)

    restarted_reader = MutableStateReader(deleted_at)
    restarted_gate = OwnerWriteGate(restarted_reader)
    with pytest.raises(OwnerWriteBlocked, match="OWNER_WRITE_BLOCKED") as exc:
        restarted_gate.assert_writable(OWNER_KEY)

    assert restarted_reader.calls == [USER_ID]
    assert USER_ID not in str(exc.value)
    assert OWNER_KEY not in str(exc.value)


def test_durable_lookup_failure_blocks_without_leaking_owner():
    """Database outages must fail closed and expose no subject identifier."""
    reader = MutableStateReader()
    reader.error = RuntimeError(f"database failed for {USER_ID}")
    gate = OwnerWriteGate(reader)

    with pytest.raises(OwnerWriteBlocked) as exc:
        gate.assert_writable(OWNER_KEY)

    assert str(exc.value) == "OWNER_WRITE_BLOCKED"


def test_anonymous_owner_does_not_use_account_state_reader():
    """Anonymous abuse policy is separate from authenticated account deletion."""
    reader = MutableStateReader(deleted_at=datetime.now(timezone.utc))
    gate = OwnerWriteGate(reader)

    gate.assert_writable(ANON_OWNER)

    assert reader.calls == []


def test_block_unblock_and_refresh_hooks_preserve_durable_authority():
    """Hooks may accelerate state changes but cannot override durable deletion."""
    reader = MutableStateReader()
    gate = OwnerWriteGate(reader)
    gate.block_owner(OWNER_KEY)

    with pytest.raises(OwnerWriteBlocked):
        gate.assert_writable(OWNER_KEY)
    assert reader.calls == []

    gate.unblock_owner(OWNER_KEY)
    gate.assert_writable(OWNER_KEY)
    assert reader.calls == [USER_ID]

    reader.deleted_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
    with pytest.raises(OwnerWriteBlocked):
        gate.refresh(OWNER_KEY)


def test_owner_key_for_user_normalizes_uuid_and_rejects_other_ids():
    assert owner_key_for_user(USER_ID.upper()) == OWNER_KEY
    with pytest.raises(ValueError, match="user UUID"):
        owner_key_for_user("alice")
