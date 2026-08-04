"""Durable account-erasure state and transaction contracts."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

import erasure_state


UTC = timezone.utc
USER_ID = "00000000-0000-0000-0000-000000000001"
PHONE = "0900000001"


class FakeDatabase:
    """Stateful database boundary that preserves transaction-visible effects."""

    _ph = "%s"

    def __init__(self):
        self.user = {
            "id": USER_ID,
            "phone": PHONE,
            "is_active": True,
            "deleted_at": None,
            "erasure_due_at": None,
            "erasure_attempt_count": 0,
            "erasure_last_attempt_at": None,
            "erasure_last_error_code": None,
        }
        self.user_sessions = {"session"}
        self.otp_sessions = {PHONE}
        self.trusted_devices = {"device"}
        self.pending_2fa = {"challenge"}
        self.statements: list[str] = []
        self.transactions = 0

    def initialize(self):
        return None

    @contextmanager
    def _conn(self):
        yield self
        self.transactions += 1

    def _fetchone(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        if normalized.startswith("SELECT"):
            assert normalized.endswith("FOR UPDATE")
            assert params == (USER_ID,)
            return dict(self.user)
        if normalized.startswith("UPDATE users"):
            requested_at, due_at, user_id = params
            assert user_id == USER_ID
            if self.user["deleted_at"] is None:
                self.user["deleted_at"] = requested_at
            if self.user["erasure_due_at"] is None:
                self.user["erasure_due_at"] = due_at
            self.user["is_active"] = False
            return dict(self.user)
        raise AssertionError(f"Unexpected query: {normalized}")

    def _execute(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append(normalized)
        if "DELETE FROM user_sessions" in normalized:
            self.user_sessions.clear()
        elif "DELETE FROM otp_sessions" in normalized:
            assert params == (PHONE,)
            self.otp_sessions.clear()
        elif "DELETE FROM trusted_devices" in normalized:
            self.trusted_devices.clear()
        elif "DELETE FROM pending_2fa" in normalized:
            self.pending_2fa.clear()
        else:
            raise AssertionError(f"Unexpected statement: {normalized}")

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row is not None else None


def test_request_persists_exact_deadline_and_never_recomputes_retry(monkeypatch):
    """A retry must not move a previously committed deletion deadline."""
    fake = FakeDatabase()
    monkeypatch.setattr(erasure_state, "db", fake)
    requested_at = datetime(2026, 7, 30, 12, 15, 0, tzinfo=UTC)

    first = erasure_state.request_account_erasure(USER_ID, now=requested_at)
    retry = erasure_state.request_account_erasure(
        USER_ID, now=requested_at + timedelta(days=10)
    )

    expected_due_at = datetime(2026, 8, 29, 12, 15, 0, tzinfo=UTC)
    assert first.deleted_at == requested_at
    assert first.erasure_due_at == expected_due_at
    assert retry.deleted_at == requested_at
    assert retry.erasure_due_at == expected_due_at
    assert fake.user["is_active"] is False
    assert fake.transactions == 2


def test_request_revokes_every_registered_active_credential_in_same_transaction(monkeypatch):
    """Removing any credential DELETE would leave an active login path behind."""
    fake = FakeDatabase()
    monkeypatch.setattr(erasure_state, "db", fake)

    erasure_state.request_account_erasure(
        USER_ID, now=datetime(2026, 7, 30, tzinfo=UTC)
    )

    assert not fake.user_sessions
    assert not fake.otp_sessions
    assert not fake.trusted_devices
    assert not fake.pending_2fa
    assert fake.transactions == 1
    assert fake.statements[0].endswith("FOR UPDATE")


def test_load_state_uses_row_lock_when_requested(monkeypatch):
    """Dropping FOR UPDATE would make later recovery/erasure races unsafe."""
    fake = FakeDatabase()
    monkeypatch.setattr(erasure_state, "db", fake)

    state = erasure_state.load_erasure_state(fake, USER_ID, for_update=True)

    assert state.erasure_attempt_count == 0
    assert len(fake.statements) == 1
    assert fake.statements[0].endswith("FOR UPDATE")


def test_state_rejects_unbounded_error_text():
    """Raw exception strings must never enter durable erasure metadata."""
    with pytest.raises(ValueError, match="erasure error code"):
        erasure_state.ErasureState(
            deleted_at=None,
            erasure_due_at=None,
            erasure_attempt_count=0,
            erasure_last_attempt_at=None,
            erasure_last_error_code="database connection failed for user",
        )


def test_request_rejects_naive_clock(monkeypatch):
    """A timezone-naive clock can shift the exact UTC deadline."""
    fake = FakeDatabase()
    monkeypatch.setattr(erasure_state, "db", fake)

    with pytest.raises(ValueError, match="UTC-aware"):
        erasure_state.request_account_erasure(
            USER_ID, now=datetime(2026, 7, 30, 12, 15, 0)
        )
