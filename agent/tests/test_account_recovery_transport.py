"""Real-ASGI contracts for recovery and post-commit quarantine ordering."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

import httpx
import pytest

import auth
import ratelimit
import server
from erasure_state import ErasureState
from quarantine import QuarantineResult, RecoveryResult


USER_ID = "00000000-0000-0000-0000-000000000001"
PHONE = "0900000001"
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
DUE = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _override_pg_and_csrf():
    async def no_dependency():
        return None

    server.app.dependency_overrides[auth._require_pg] = no_dependency
    server.app.dependency_overrides[auth._require_csrf_lazy] = no_dependency


@pytest.mark.anyio
async def test_otp_recovery_commits_before_session_creation(monkeypatch):
    events = []
    deleted_user = {
        "id": USER_ID,
        "phone": PHONE,
        "is_active": False,
        "deleted_at": NOW,
        "password_hash": None,
    }
    recovered_user = {**deleted_user, "is_active": True, "deleted_at": None}

    class FakeDB:
        @contextmanager
        def _conn(self):
            yield self

        def get_user_by_phone(self, phone):
            assert phone == PHONE
            return dict(deleted_user)

    def recover(user_id, *, now):
        assert user_id == USER_ID
        assert now.tzinfo is not None
        events.append("recovery_commit")
        return RecoveryResult(recovered=True, user=dict(recovered_user))

    async def finish(*_args):
        events.append("session_insert")
        return {"success": True, "token": "session"}

    monkeypatch.setattr(auth, "db", FakeDB())
    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "recover_account", recover)
    monkeypatch.setattr(auth, "_finish_login", finish)
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: False)
    monkeypatch.setattr(auth, "_hash_otp", lambda code: code)
    monkeypatch.setattr(auth, "_check_shared_auth_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_enforce_local_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_utc_now", lambda: NOW)
    monkeypatch.setattr(auth, "_log_consent", lambda *_args: None)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    _override_pg_and_csrf()

    try:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/auth/verify-otp",
                json={"phone": PHONE, "code": "123456"},
            )
    finally:
        server.app.dependency_overrides.pop(auth._require_pg, None)
        server.app.dependency_overrides.pop(auth._require_csrf_lazy, None)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert events == ["recovery_commit", "session_insert"]


@pytest.mark.anyio
async def test_otp_recovery_at_deadline_returns_generic_unavailable_without_session(
    monkeypatch,
):
    finish_calls = []

    class FakeDB:
        @contextmanager
        def _conn(self):
            yield self

        def get_user_by_phone(self, _phone):
            return {
                "id": USER_ID,
                "phone": PHONE,
                "is_active": False,
                "deleted_at": NOW,
                "password_hash": None,
            }

    async def finish(*_args):
        finish_calls.append(True)
        return {"success": True}

    monkeypatch.setattr(auth, "db", FakeDB())
    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(
        auth,
        "recover_account",
        lambda *_args, **_kwargs: RecoveryResult(recovered=False, user=None),
    )
    monkeypatch.setattr(auth, "_finish_login", finish)
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: False)
    monkeypatch.setattr(auth, "_hash_otp", lambda code: code)
    monkeypatch.setattr(auth, "_check_shared_auth_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_enforce_local_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_utc_now", lambda: DUE)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    _override_pg_and_csrf()

    try:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/auth/verify-otp",
                json={"phone": PHONE, "code": "123456"},
            )
    finally:
        server.app.dependency_overrides.pop(auth._require_pg, None)
        server.app.dependency_overrides.pop(auth._require_csrf_lazy, None)

    assert response.status_code == 403
    assert response.json()["detail"] == "Tài khoản không khả dụng"
    assert finish_calls == []


@pytest.mark.anyio
async def test_delete_transport_quarantines_only_after_durable_request_commit(
    monkeypatch, caplog
):
    events = []

    async def current_user(_request):
        return {"id": USER_ID, "phone": PHONE}

    async def binding_ok(_request, _user):
        return True

    def request_erasure(user_id, *, now):
        events.append(("request_commit", user_id, now))
        return ErasureState(
            deleted_at=NOW,
            erasure_due_at=DUE,
            erasure_attempt_count=0,
            erasure_last_attempt_at=None,
            erasure_last_error_code=None,
        )

    class Gate:
        def block_owner(self, owner_key):
            events.append(("block", owner_key))

    def quarantine_account(user_id, *, now):
        events.append(("quarantine", user_id, now))
        return QuarantineResult(
            run_id="run-1",
            attempted_store_names=("hot_memory",),
            failed_store_names=("hot_memory",),
            error_code="STORE_UNAVAILABLE",
            status="failed",
        )

    monkeypatch.setattr(auth, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(auth, "_check_session_binding_safe", binding_ok)
    monkeypatch.setattr(auth, "_utc_now", lambda: NOW)
    monkeypatch.setattr(auth, "request_account_erasure", request_erasure)
    monkeypatch.setattr(auth, "owner_write_gate", Gate())
    monkeypatch.setattr(auth, "quarantine_account", quarantine_account)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    _override_pg_and_csrf()

    try:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/auth/account")
    finally:
        server.app.dependency_overrides.pop(auth._require_pg, None)
        server.app.dependency_overrides.pop(auth._require_csrf_lazy, None)

    assert response.status_code == 200
    assert [event[0] for event in events] == [
        "request_commit",
        "block",
        "quarantine",
    ]
    assert events[2][2] == NOW
    assert "run-1" in caplog.text
    assert "STORE_UNAVAILABLE" in caplog.text
    assert USER_ID not in caplog.text
