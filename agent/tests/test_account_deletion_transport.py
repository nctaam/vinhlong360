"""Real-ASGI transport contract for scheduling account erasure."""

from datetime import datetime, timezone

import httpx
import pytest

from identity import api as auth

from identity import api as identity_api  # mien dinh danh sang day 2026-08-28
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

    monkeypatch.setattr(identity_api, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(identity_api, "_check_session_binding_safe", binding_ok)
    monkeypatch.setattr(identity_api, "_utc_now", lambda: REQUESTED_AT, raising=False)
    monkeypatch.setattr(
        identity_api, "request_account_erasure", request_erasure, raising=False
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
        # Thêm 2026-08-30 cùng lượt đảo mặc định sang XOÁ THẬT. Câu `message` nay
        # phụ thuộc cấu hình — nếu ai kéo cầu dao (ERASURE_ACTIVATION_ENABLED=false)
        # thì nó thôi hứa "xoá vĩnh viễn". `erasure_active` là bản MÁY ĐỌC ĐƯỢC của
        # cùng sự thật đó, để người tích hợp không phải so chuỗi tiếng Việt.
        # Khẳng định True ở đây tức là: với cấu hình mặc định, lời hứa xoá-vĩnh-viễn
        # là lời hứa CÓ THẬT — đúng điều mà trước 2026-08-30 KHÔNG đúng.
        "erasure_active": True,
        "browser_clear_instruction": {
            "version": "v1",
            "action": "clear",
            "keys": [
                "vl360_favorites", "vl360_recent", "vl360_post_draft",
                "vl360_recent_searches", "vinhlong360:public-search-entries:v2",
                "chat_sid", "vl360_plans", "vl360_planner_draft",
            ],
            "issued": True,
            "subject_hash": __import__("hashlib").sha256(USER_ID.encode()).hexdigest(),
        },
    }
    assert calls == [(USER_ID, REQUESTED_AT)]


@pytest.mark.anyio
async def test_delete_account_binding_failure_log_is_subject_free(
    monkeypatch, caplog
):
    async def current_user(_request):
        return {"id": USER_ID, "phone": "0900000001"}

    async def binding_failed(_request, _user):
        return False

    async def no_dependency():
        return None

    monkeypatch.setattr(identity_api, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(identity_api, "_check_session_binding_safe", binding_failed)
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

    assert response.status_code == 403
    assert "Session binding mismatch on delete-account" in caplog.text
    assert USER_ID not in caplog.text


@pytest.mark.anyio
async def test_keo_cau_dao_thi_thoi_hua_xoa_vinh_vien(monkeypatch):
    """Tắt vòng xoá → câu trả lời PHẢI thôi hứa "xoá vĩnh viễn".

    Đây là bằng chứng HÀNH VI cho bản vá P0 ngày 2026-08-30. Trước đó câu hứa
    được ghim cứng trong payload, nên khi vòng xoá ở chế độ chỉ-đếm thì hệ thống
    nói với người dùng một điều nó không làm — 288 lần/ngày, không ai thấy.

    Test cấu trúc (`test_erasure_config.py`) chỉ khẳng định CÓ nhánh điều kiện.
    Bài này đi qua HTTP thật và đọc chữ người dùng nhận được, nên nó bắt được cả
    trường hợp nhánh còn đó mà rẽ sai đường.
    """
    from config import settings as _settings

    async def current_user(_request):
        return {"id": USER_ID, "phone": "0900000001"}

    async def binding_ok(_request, _user):
        return True

    def request_erasure(user_id, *, now):
        return ErasureState(
            deleted_at=REQUESTED_AT,
            erasure_due_at=DUE_AT,
            erasure_attempt_count=0,
            erasure_last_attempt_at=None,
            erasure_last_error_code=None,
        )

    async def no_dependency():
        return None

    monkeypatch.setattr(identity_api, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(identity_api, "_check_session_binding_safe", binding_ok)
    monkeypatch.setattr(identity_api, "_utc_now", lambda: REQUESTED_AT, raising=False)
    monkeypatch.setattr(
        identity_api, "request_account_erasure", request_erasure, raising=False
    )
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    # CẦU DAO: một cờ là đủ để dừng xoá.
    monkeypatch.setattr(_settings, "ERASURE_ACTIVATION_ENABLED", False)
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

    body = response.json()
    assert response.status_code == 200
    assert body["erasure_active"] is False
    # Ghim LỜI HỨA, không ghim TỪ. Bản tạm-dừng vẫn được phép nói "việc xoá vĩnh
    # viễn hiện đang tạm dừng" — đó là mô tả đúng sự thật. Cái bị cấm là câu
    # KHẲNG ĐỊNH sẽ xoá.
    assert "sẽ bị xoá vĩnh viễn" not in body["message"], (
        "vòng xoá đang tắt mà vẫn HỨA sẽ xoá vĩnh viễn — đúng lỗ hổng P0 quay lại"
    )
    assert "tạm dừng" in body["message"], "phải nói THẬT rằng việc xoá đang dừng"
    # Hạn vẫn được ghi nhận và trả về: yêu cầu của người dùng không bị mất.
    assert body["erasure_due_at"] == "2026-08-29T12:15:00+00:00"
