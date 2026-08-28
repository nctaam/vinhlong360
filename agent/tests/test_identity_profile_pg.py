# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI của miền HỒ SƠ/RIÊNG TƯ trong identity/api.py trên
PostgreSQL thật (các closure _query chưa từng chạy trên DB thật — 0% phủ).

Phạm vi (targets_b.txt dòng 200-215): get_me, get_csrf, _persist_profile_fields,
_profile_apply_email, check_username(+_query), upload_avatar, upload_cover,
_check_suspicious_login, _update_login_streak, get_login_history(+_query),
get_privacy(+_query), _upsert_privacy, update_privacy; kèm
reset_password_otp._ach_bg (:1077) qua stub achievements.

Khuôn harness: theo agent/tests/test_account_control_plane_postgres.py —
adapter Database() ép _use_pg/_dsn, monkeypatch identity_api.db, TRUNCATE quanh
mỗi test, seed bằng SQL INSERT trực tiếp. Side-effect ngoài miền (notifications,
achievements, storage backend) được stub/chuyển hướng — KHÔNG chạm SQLite thật.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import io
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException, Request, Response

import achievements
import auth_middleware
import database as database_module
import notifications
import storage as storage_module
from identity import api as identity_api

WAIT_TIMEOUT = 5


def _test_database_url() -> str | None:
    url = os.environ.get("IDENTITY_SURFACE_TEST_DATABASE_URL")
    if not url:
        return None

    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    explicitly_allowed = os.environ.get(
        "IDENTITY_SURFACE_ALLOW_PG_TESTS", ""
    ).lower() in {"1", "true", "yes", "on"}
    if parsed.scheme not in {"postgres", "postgresql"} or not database_name:
        raise pytest.UsageError(
            "IDENTITY_SURFACE_TEST_DATABASE_URL must be a PostgreSQL URL"
        )
    if "test" not in database_name.lower() and not explicitly_allowed:
        raise pytest.UsageError(
            "PostgreSQL identity-surface tests require a database name containing "
            "'test' or IDENTITY_SURFACE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL identity-surface tests require "
            "IDENTITY_SURFACE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set IDENTITY_SURFACE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)

# Các bảng file này chạm tới — TRUNCATE quanh mỗi test (schema đã migrate sẵn 81).
_TRUNCATE_SQL = (
    "TRUNCATE user_privacy, login_history, pending_2fa, user_sessions, "
    "otp_sessions, users CASCADE"
)


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    # update_user() gọi initialize() → _verify_pg_schema; schema đã migrate sẵn,
    # đánh dấu sẵn để không chạy verify/nạp cache trong mỗi test.
    adapter._initialized = True
    monkeypatch.setattr(identity_api, "db", adapter)

    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(_TRUNCATE_SQL)
    try:
        yield adapter
    finally:
        with psycopg2.connect(TEST_DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(_TRUNCATE_SQL)


# ── Seed helpers ──


def _vn_phone() -> str:
    return f"09{uuid.uuid4().int % 10**8:08d}"


def _unique_ip() -> str:
    n = uuid.uuid4().int
    return f"10.{n % 250}.{(n >> 8) % 250}.{(n >> 16) % 250 + 1}"


def _seed_user(
    pg_db,
    *,
    phone: str | None = None,
    username: str | None = None,
    password_hash: str | None = "old-hash",
    display_name: str = "Người Test",
) -> tuple[str, str]:
    user_id = str(uuid.uuid4())
    phone = phone or _vn_phone()
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (id, phone, password_hash, display_name, username, role, is_active)
            VALUES (%s::uuid, %s, %s, %s, %s, 'user', TRUE)
            """,
            (user_id, phone, password_hash, display_name, username),
        )
    return user_id, phone


def _seed_session(pg_db, user_id: str, *, expired: bool = False) -> str:
    raw_token = uuid.uuid4().hex  # 32 ký tự — nằm trong cửa 16..128 của _extract_token
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES (%s::uuid, %s, %s, %s, %s)
            """,
            (
                user_id,
                identity_api._hash_token(raw_token),
                "pytest-agent",
                "127.0.0.1",
                datetime.now(timezone.utc) + delta,
            ),
        )
    return raw_token


def _seed_login_row(
    pg_db,
    user_id: str,
    *,
    method: str = "password",
    success: bool = True,
    ip: str = "203.113.55.9",
    ua: str = "pytest-agent",
    age_minutes: int = 0,
) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO login_history (user_id, phone, method, success, ip, user_agent, created_at)
            VALUES (%s::uuid, %s, %s, %s, %s, %s, NOW() - %s * INTERVAL '1 minute')
            """,
            (user_id, "091***456", method, success, ip, ua, age_minutes),
        )


def _fetch_user(pg_db, user_id: str) -> dict:
    with pg_db._conn() as conn:
        row = pg_db._fetchone(
            conn, "SELECT * FROM users WHERE id = %s::uuid", (user_id,)
        )
    return pg_db._row_to_dict(row)


def _fetch_privacy(pg_db, user_id: str) -> dict | None:
    with pg_db._conn() as conn:
        row = pg_db._fetchone(
            conn, "SELECT * FROM user_privacy WHERE user_id = %s::uuid", (user_id,)
        )
    return pg_db._row_to_dict(row) if row else None


def _request(
    token: str | None = None,
    *,
    ip: str | None = None,
    headers: dict | None = None,
) -> Request:
    hdrs = {"host": "localhost", "user-agent": "pytest-agent"}
    if headers:
        hdrs.update(headers)
    if token:
        hdrs["authorization"] = f"Bearer {token}"
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/x",
            "query_string": b"",
            "headers": [(k.encode(), v.encode()) for k, v in hdrs.items()],
            "client": (ip or _unique_ip(), 4321),
            "server": ("localhost", 80),
            "scheme": "http",
        }
    )


class _FakeUpload:
    """UploadFile giả — chỉ cần .read() async như handler dùng."""

    def __init__(self, data: bytes):
        self._data = data

    async def read(self, size: int = -1) -> bytes:
        return self._data


def _png_bytes(color=(200, 30, 30), size=(32, 32)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _local_storage(monkeypatch, tmp_path) -> None:
    """Chuyển backend storage về local + trỏ thư mục ra tmp_path (không ghi web/media)."""
    monkeypatch.setattr(storage_module, "LOCAL_MEDIA_DIR", tmp_path)
    monkeypatch.setattr(storage_module.storage, "backend", "local")
    monkeypatch.setattr(storage_module.storage, "use_s3", False)


# ── get_me ──


def test_get_me_returns_masked_profile(pg_db):
    user_id, phone = _seed_user(pg_db, display_name="Chị Bảy")
    token = _seed_session(pg_db, user_id)

    result = asyncio.run(identity_api.get_me(_request(token)))

    user = result["user"]
    assert user["id"] == user_id
    assert user["phone"] == phone[:3] + "****" + phone[-3:]
    assert user["display_name"] == "Chị Bảy"
    assert user["role"] == "user"
    assert user["has_password"] is True
    assert "password_hash" not in user


def test_get_me_requires_login(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.get_me(_request()))
    assert exc.value.status_code == 401


def test_get_me_rejects_expired_session(pg_db):
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id, expired=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.get_me(_request(token)))
    assert exc.value.status_code == 401


# ── get_csrf ──


def test_get_csrf_returns_hmac_of_session_token(pg_db):
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)

    result = asyncio.run(identity_api.get_csrf(_request(token)))

    assert result["csrf_token"] == auth_middleware.generate_csrf_token(token)
    assert len(result["csrf_token"]) == 64


def test_get_csrf_requires_login(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.get_csrf(_request()))
    assert exc.value.status_code == 401


# ── _persist_profile_fields ──


def test_persist_profile_fields_writes_to_db(pg_db):
    user_id, _ = _seed_user(pg_db)

    updated = asyncio.run(
        identity_api._persist_profile_fields(
            user_id,
            {"display_name": "Tên Mới", "bio": "xin chào Vĩnh Long", "email": "a@b.vn"},
        )
    )

    assert updated["display_name"] == "Tên Mới"
    row = _fetch_user(pg_db, user_id)
    assert row["display_name"] == "Tên Mới"
    assert row["bio"] == "xin chào Vĩnh Long"
    assert row["email"] == "a@b.vn"


def test_persist_profile_fields_maps_db_error_to_500(pg_db, monkeypatch):
    user_id, _ = _seed_user(pg_db)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(pg_db, "update_user", _boom)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api._persist_profile_fields(user_id, {"bio": "x"}))
    assert exc.value.status_code == 500


# ── _profile_apply_email ──


def test_profile_apply_email_accepts_valid_and_maps_empty_to_none():
    fields = {}
    identity_api._profile_apply_email(
        identity_api.ProfileUpdate(email="ban@vinhlong.vn"), fields
    )
    assert fields["email"] == "ban@vinhlong.vn"

    fields = {}
    identity_api._profile_apply_email(identity_api.ProfileUpdate(email=""), fields)
    assert fields["email"] is None


def test_profile_apply_email_rejects_invalid():
    with pytest.raises(HTTPException) as exc:
        identity_api._profile_apply_email(
            identity_api.ProfileUpdate(email="khong-phai-email"), {}
        )
    assert exc.value.status_code == 400


# ── check_username ──


def test_check_username_free_name_available(pg_db):
    _seed_user(pg_db)  # có user nhưng username khác/null
    result = asyncio.run(
        identity_api.check_username(f"tu-do-{uuid.uuid4().hex[:8]}", _request())
    )
    assert result == {"available": True}


def test_check_username_taken_by_other(pg_db):
    uname = f"chuky{uuid.uuid4().hex[:8]}"
    _seed_user(pg_db, username=uname)
    result = asyncio.run(identity_api.check_username(uname.upper(), _request()))
    assert result["available"] is False
    assert "sử dụng" in result["reason"]


def test_check_username_own_name_is_available(pg_db):
    uname = f"cuaminh{uuid.uuid4().hex[:8]}"
    user_id, _ = _seed_user(pg_db, username=uname)
    token = _seed_session(pg_db, user_id)
    result = asyncio.run(identity_api.check_username(uname, _request(token)))
    assert result == {"available": True}


def test_check_username_rejects_bad_format(pg_db):
    too_short = asyncio.run(identity_api.check_username("ab", _request()))
    assert too_short["available"] is False
    assert "3" in too_short["reason"]

    bad_chars = asyncio.run(identity_api.check_username("9batdau", _request()))
    assert bad_chars["available"] is False


# ── upload_avatar / upload_cover ──


def test_upload_avatar_processes_and_persists(pg_db, monkeypatch, tmp_path):
    _local_storage(monkeypatch, tmp_path)
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)

    result = asyncio.run(
        identity_api.upload_avatar(_request(token), file=_FakeUpload(_png_bytes()))
    )

    assert set(result["sizes"]) == {"sm", "md", "lg"}
    assert result["avatar_url"] == result["sizes"]["md"]
    assert result["avatar_url"].startswith("/media/avatars/")
    assert len(list((tmp_path / "avatars").glob("*.webp"))) == 3
    assert _fetch_user(pg_db, user_id)["avatar_url"] == result["avatar_url"]


def test_upload_avatar_rejects_non_image(pg_db, monkeypatch, tmp_path):
    _local_storage(monkeypatch, tmp_path)
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.upload_avatar(
                _request(token), file=_FakeUpload(b"chac chan khong phai anh")
            )
        )
    assert exc.value.status_code == 400
    assert _fetch_user(pg_db, user_id)["avatar_url"] is None


def test_upload_avatar_rejects_oversize_content_length(pg_db, monkeypatch, tmp_path):
    _local_storage(monkeypatch, tmp_path)
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)
    oversized = str(storage_module.MAX_IMAGE_SIZE * 2 + 1)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.upload_avatar(
                _request(token, headers={"content-length": oversized}),
                file=_FakeUpload(b""),
            )
        )
    assert exc.value.status_code == 413


def test_upload_cover_processes_and_persists(pg_db, monkeypatch, tmp_path):
    _local_storage(monkeypatch, tmp_path)
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)

    result = asyncio.run(
        identity_api.upload_cover(_request(token), file=_FakeUpload(_png_bytes()))
    )

    assert set(result["sizes"]) == {"sm", "md", "lg"}
    assert result["cover_url"] == result["sizes"]["lg"]
    assert result["cover_url"].startswith("/media/covers/")
    assert len(list((tmp_path / "covers").glob("*.webp"))) == 3
    assert _fetch_user(pg_db, user_id)["cover_url"] == result["cover_url"]


def test_upload_cover_requires_login(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.upload_cover(_request(), file=_FakeUpload(b"")))
    assert exc.value.status_code == 401


# ── _check_suspicious_login ──


def test_check_suspicious_login_notifies_new_device(pg_db, monkeypatch):
    user_id, _ = _seed_user(pg_db)
    calls = []
    monkeypatch.setattr(
        notifications, "create_notification", lambda **kwargs: calls.append(kwargs)
    )

    identity_api._check_suspicious_login(
        user_id, "203.113.55.9", "Mozilla/5.0 (Windows NT 10.0)"
    )

    assert len(calls) == 1
    assert calls[0]["user_id"] == user_id
    assert calls[0]["notif_type"] == "security_alert"
    assert calls[0]["ref_type"] == "login_history"
    assert "Windows" in calls[0]["body"]
    assert "203.113.*.*" in calls[0]["body"]


def test_check_suspicious_login_skips_known_device(pg_db, monkeypatch):
    user_id, _ = _seed_user(pg_db)
    _seed_login_row(pg_db, user_id, ip="203.113.55.9", ua="ua-khac", age_minutes=30)
    calls = []
    monkeypatch.setattr(
        notifications, "create_notification", lambda **kwargs: calls.append(kwargs)
    )

    # IP trùng lịch sử 90 ngày (dù UA khác) → thiết bị/mạng đã biết, không thông báo
    identity_api._check_suspicious_login(user_id, "203.113.55.9", "ua-moi")

    assert calls == []


def test_check_suspicious_login_swallows_db_error(pg_db, monkeypatch):
    user_id, _ = _seed_user(pg_db)
    calls = []
    monkeypatch.setattr(
        notifications, "create_notification", lambda **kwargs: calls.append(kwargs)
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(pg_db, "_fetchone", _boom)
    # Không raise — fire-and-forget nuốt lỗi
    identity_api._check_suspicious_login(user_id, "1.2.3.4", "ua")
    assert calls == []


# ── _update_login_streak ──


def test_update_login_streak_first_login_and_same_day(pg_db):
    user_id, _ = _seed_user(pg_db)

    assert identity_api._update_login_streak(user_id) == 1
    # Cùng ngày: giữ nguyên, không tính 2 lần
    assert identity_api._update_login_streak(user_id) == 1

    row = _fetch_user(pg_db, user_id)
    assert row["login_streak"] == 1
    assert str(row["last_login_date"]) == datetime.now(timezone.utc).date().isoformat()


def test_update_login_streak_increments_from_yesterday(pg_db):
    user_id, _ = _seed_user(pg_db)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE users SET login_streak = 4, last_login_date = CURRENT_DATE - INTERVAL '1 day' WHERE id = %s::uuid",
            (user_id,),
        )

    assert identity_api._update_login_streak(user_id) == 5
    assert _fetch_user(pg_db, user_id)["login_streak"] == 5


def test_update_login_streak_resets_after_gap(pg_db):
    user_id, _ = _seed_user(pg_db)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE users SET login_streak = 9, last_login_date = CURRENT_DATE - INTERVAL '3 day' WHERE id = %s::uuid",
            (user_id,),
        )

    assert identity_api._update_login_streak(user_id) == 1


def test_update_login_streak_unknown_user_returns_zero(pg_db):
    assert identity_api._update_login_streak(str(uuid.uuid4())) == 0


# ── get_login_history ──


def test_get_login_history_returns_masked_rows_newest_first(pg_db):
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)
    _seed_login_row(pg_db, user_id, method="otp", success=True, age_minutes=10)
    _seed_login_row(
        pg_db, user_id, method="password", success=False, ip="14.161.7.20", age_minutes=1
    )

    result = asyncio.run(identity_api.get_login_history(_request(token), limit=20))

    history = result["history"]
    assert [h["method"] for h in history] == ["password", "otp"]
    assert history[0]["success"] is False
    assert history[0]["ip"] == "14.161.*.*"
    assert history[1]["ip"] == "203.113.*.*"
    assert all(isinstance(h["id"], str) for h in history)


def test_get_login_history_respects_limit(pg_db):
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)
    for age in (1, 2, 3):
        _seed_login_row(pg_db, user_id, age_minutes=age)

    result = asyncio.run(identity_api.get_login_history(_request(token), limit=2))
    assert len(result["history"]) == 2


def test_get_login_history_requires_login(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.get_login_history(_request(), limit=20))
    assert exc.value.status_code == 401


# ── get_privacy / _upsert_privacy / update_privacy ──


def test_get_privacy_defaults_without_row(pg_db):
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)

    result = asyncio.run(identity_api.get_privacy(_request(token)))
    assert result == {
        "profile_visibility": "public",
        "show_activity": True,
        "show_saved": True,
    }


def test_get_privacy_reads_existing_row(pg_db):
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_privacy (user_id, profile_visibility, show_activity, show_saved)
            VALUES (%s::uuid, 'private', FALSE, TRUE)
            """,
            (user_id,),
        )

    result = asyncio.run(identity_api.get_privacy(_request(token)))
    assert result == {
        "profile_visibility": "private",
        "show_activity": False,
        "show_saved": True,
    }


def test_get_privacy_requires_login(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.get_privacy(_request()))
    assert exc.value.status_code == 401


def test_upsert_privacy_inserts_with_defaults(pg_db):
    user_id, _ = _seed_user(pg_db)

    identity_api._upsert_privacy(
        user_id, identity_api.PrivacyUpdate(profile_visibility="followers")
    )

    row = _fetch_privacy(pg_db, user_id)
    assert row["profile_visibility"] == "followers"
    assert row["show_activity"] is True
    assert row["show_saved"] is True


def test_upsert_privacy_updates_only_given_fields(pg_db):
    user_id, _ = _seed_user(pg_db)
    identity_api._upsert_privacy(
        user_id, identity_api.PrivacyUpdate(profile_visibility="private")
    )

    identity_api._upsert_privacy(user_id, identity_api.PrivacyUpdate(show_saved=False))

    row = _fetch_privacy(pg_db, user_id)
    assert row["profile_visibility"] == "private"  # không bị đè
    assert row["show_activity"] is True
    assert row["show_saved"] is False
    assert row["updated_at"] is not None


def test_upsert_privacy_noop_update_keeps_row(pg_db):
    user_id, _ = _seed_user(pg_db)
    identity_api._upsert_privacy(
        user_id, identity_api.PrivacyUpdate(profile_visibility="followers")
    )

    identity_api._upsert_privacy(user_id, identity_api.PrivacyUpdate())

    row = _fetch_privacy(pg_db, user_id)
    assert row["profile_visibility"] == "followers"


def test_update_privacy_roundtrip(pg_db):
    user_id, _ = _seed_user(pg_db)
    token = _seed_session(pg_db, user_id)
    body = identity_api.PrivacyUpdate(profile_visibility="private", show_activity=False)

    result = asyncio.run(identity_api.update_privacy(body, _request(token)))

    assert result == {
        "profile_visibility": "private",
        "show_activity": False,
        "show_saved": True,
    }
    row = _fetch_privacy(pg_db, user_id)
    assert row["profile_visibility"] == "private"
    assert row["show_activity"] is False


def test_update_privacy_requires_login(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.update_privacy(identity_api.PrivacyUpdate(), _request())
        )
    assert exc.value.status_code == 401


# ── reset_password_otp._ach_bg (:1077) ──


def test_reset_password_otp_runs_achievement_hook(pg_db, monkeypatch):
    user_id, phone = _seed_user(pg_db)
    _seed_session(pg_db, user_id)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO pending_2fa (user_id, token_hash, expires_at) VALUES (%s::uuid, %s, %s)",
            (
                user_id,
                f"pending-{uuid.uuid4().hex}",
                datetime.now(timezone.utc) + timedelta(minutes=5),
            ),
        )
        pg_db._execute(
            conn,
            "INSERT INTO otp_sessions (phone, code, expires_at) VALUES (%s, %s, %s)",
            (
                phone,
                identity_api._hash_otp("123456"),
                datetime.now(timezone.utc) + timedelta(minutes=5),
            ),
        )
    monkeypatch.setattr(identity_api, "_hash_password", lambda _password: "reset-hash")

    ach_calls = []
    ach_ran = threading.Event()

    def fake_check_achievements(conn, uid, notify=True):
        ach_calls.append((uid, notify))
        ach_ran.set()
        return []

    monkeypatch.setattr(achievements, "check_achievements", fake_check_achievements)
    body = identity_api.ResetPasswordOTP(
        phone=phone, code="123456", new_password="MatKhau2026"
    )

    async def _call():
        result = await identity_api.reset_password_otp(body, _request(), Response())
        others = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if others:
            await asyncio.wait(others, timeout=WAIT_TIMEOUT)
        return result

    result = asyncio.run(_call())

    assert result["success"] is True
    assert ach_ran.wait(WAIT_TIMEOUT)
    assert ach_calls == [(user_id, True)]

    row = _fetch_user(pg_db, user_id)
    assert row["password_hash"] == "reset-hash"
    assert row["login_streak"] == 1
    with pg_db._conn() as conn:
        sessions = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS n FROM user_sessions WHERE user_id = %s::uuid",
            (user_id,),
        )["n"]
        pending = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS n FROM pending_2fa WHERE user_id = %s::uuid",
            (user_id,),
        )["n"]
        otp_verified = pg_db._fetchone(
            conn, "SELECT verified FROM otp_sessions WHERE phone = %s", (phone,)
        )["verified"]
        login_row = pg_db._fetchone(
            conn,
            "SELECT method, success FROM login_history WHERE user_id = %s::uuid",
            (user_id,),
        )
    assert sessions == 0
    assert pending == 0
    assert otp_verified is True
    assert login_row["method"] == "password_reset"
    assert login_row["success"] is True
