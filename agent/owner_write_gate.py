"""Durable admission boundary for owner-linked writes."""

from __future__ import annotations

import time
import uuid
from threading import Lock
from typing import Callable

from database import db


class OwnerWriteBlocked(RuntimeError):
    """Raised when durable account state does not authorize a personal write."""


_BLOCKED_MESSAGE = "OWNER_WRITE_BLOCKED"
_MISSING_ACCOUNT = object()


def owner_key_for_user(user_id) -> str:
    """Return the canonical authenticated-owner namespace for a UUID."""
    try:
        normalized = str(uuid.UUID(str(user_id)))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("user UUID is required") from exc
    return f"user:{normalized}"


def _user_id_from_owner_key(owner_key: str) -> str | None:
    if not isinstance(owner_key, str) or not owner_key.startswith("user:"):
        return None
    raw_user_id = owner_key.removeprefix("user:")
    try:
        return str(uuid.UUID(raw_user_id))
    except (AttributeError, TypeError, ValueError):
        # Production authenticated owners are UUID-backed. Other namespaces are
        # legacy/synthetic owner keys and have no durable account row to query.
        return None


def _read_deleted_at(user_id: str):
    db.initialize()
    if not db._use_pg:
        raise RuntimeError("durable account state unavailable")
    with db._conn(commit_on_success=False) as conn:
        row = db._fetchone(
            conn,
            f"SELECT deleted_at FROM users WHERE id::text = {db._ph}",
            (user_id,),
        )
    if row is None:
        return _MISSING_ACCOUNT
    return db._row_to_dict(row).get("deleted_at")


class OwnerWriteGate:
    """Check every authenticated write against durable deletion state."""

    def __init__(
        self,
        state_reader: Callable[[str], object] | None = None,
        *,
        blocked_ttl_seconds: float = 5.0,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._state_reader = state_reader or _read_deleted_at
        self._blocked_ttl_seconds = max(float(blocked_ttl_seconds), 0.1)
        self._monotonic = monotonic
        self._blocked_until: dict[str, float] = {}
        self._lock = Lock()

    def assert_writable(self, owner_key: str) -> None:
        user_id = _user_id_from_owner_key(owner_key)
        if user_id is None:
            return

        now = self._monotonic()
        with self._lock:
            blocked_until = self._blocked_until.get(user_id)
            if blocked_until is not None and blocked_until > now:
                raise OwnerWriteBlocked(_BLOCKED_MESSAGE)
            if blocked_until is not None:
                self._blocked_until.pop(user_id, None)

        try:
            deleted_at = self._state_reader(user_id)
        except Exception:
            raise OwnerWriteBlocked(_BLOCKED_MESSAGE) from None
        if deleted_at is not None:
            self.block_owner(owner_key)
            raise OwnerWriteBlocked(_BLOCKED_MESSAGE)

    def refresh(self, owner_key: str) -> None:
        """Discard the short blocked cache and re-read durable state."""
        self.unblock_owner(owner_key)
        self.assert_writable(owner_key)

    def block_owner(self, owner_key: str) -> None:
        user_id = _user_id_from_owner_key(owner_key)
        if user_id is None:
            return
        with self._lock:
            self._blocked_until[user_id] = (
                self._monotonic() + self._blocked_ttl_seconds
            )

    def unblock_owner(self, owner_key: str) -> None:
        user_id = _user_id_from_owner_key(owner_key)
        if user_id is None:
            return
        with self._lock:
            self._blocked_until.pop(user_id, None)


owner_write_gate = OwnerWriteGate()
