"""Real-ASGI transport contract for scheduling account erasure."""

from datetime import datetime, timezone

import httpx
import pytest

import auth
import ratelimit
import server
from erasure_state import ErasureState


USER_ID = "00000000-0000-0000-0000-000000000001"
REQUESTED_AT = datetime(2026, 7, 30, 12, 15, 0, tzinfo=timezone.utc)
DUE_AT = datetime(2026, 8, 29, 12, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_delete_account_returns_committed_exact_deadline(monkeypatch):
    """Transport must expose the stored deadline, not calculate a second one."""
    async def current_user(_request):
        return {"id": USER_ID, "phone": "0900000001"}

    async def binding_ok(_request, _user):
        return True

    calls = []

    def request_erasure(user_id, *, now):
        calls.append((user_id, now))
        return ErasureState(
            deleted_at=REQUESTED_AT,
            erasure_due_at=DUE_AT,
            erasure_attempt_count=0,
            erasure_last_attempt_at=None,
            erasure_last_error_code=None,
        )

    async def no_dependency():
        return None

    monkeypatch.setattr(auth, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(auth, "_check_session_binding_safe", binding_ok)
    monkeypatch.setattr(auth, "_utc_now", lambda: REQUESTED_AT, raising=False)
    monkeypatch.setattr(
        auth, "request_account_erasure", request_erasure, raising=False
    )
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    server.app.dependency_overrides[auth._require_pg] = no_dependency
    server.app.dependency_overrides[auth._require_csrf_lazy] = no_dependency

    try:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.delete("/auth/account")
    finally:
        server.app.dependency_overrides.pop(auth._require_pg, None)
        server.app.dependency_overrides.pop(auth._require_csrf_lazy, None)

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "status": "scheduled",
        "message": (
            "Tài khoản sẽ bị xoá vĩnh viễn sau 30 ngày. "
            "Đăng nhập lại bằng OTP để huỷ."
        ),
        "grace_days": 30,
        "erasure_due_at": "2026-08-29T12:15:00+00:00",
    }
    assert calls == [(USER_ID, REQUESTED_AT)]

