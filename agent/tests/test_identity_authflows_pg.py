# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI của miền LUỒNG XÁC THỰC trong identity/api.py trên
PostgreSQL thật (các closure _query/_save_otp/_store/_rotate/_revoke_others và
handler bao quanh chưa từng chạy trên DB thật trước file này).

Khuôn harness: theo agent/tests/test_account_control_plane_postgres.py —
adapter Database() ép sang PG (_use_pg/_dsn), monkeypatch `identity.api.db`,
TRUNCATE các bảng auth quanh mỗi test. Cổng env:
IDENTITY_SURFACE_TEST_DATABASE_URL (DB dùng một lần, tên phải chứa 'test').

Chống trục-4: mọi side-effect ngoài miền (SMS eSMS, achievements, thông báo
đăng-nhập-lạ) đều bị monkeypatch thành stub ghi-nhận-lời-gọi — các module đó
import `db` RIÊNG của chúng, không được để chạy thật. Rate-limit chia sẻ
(ratelimit.check_rate) bị ép về nhánh in-memory để không đụng bảng
shared_rate_limits qua `database.db` toàn cục.
"""
import asyncio
import os
import re
import secrets
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException, Request, Response

import auth_middleware
import database as database_module
import ratelimit
from identity import api as identity_api


THREAD_TIMEOUT = 10


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
            "PostgreSQL identity-authflow tests require a database name containing "
            "'test' or IDENTITY_SURFACE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL identity-authflow tests require "
            "IDENTITY_SURFACE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set IDENTITY_SURFACE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)

# Các bảng miền auth mà file này ghi vào (TRUNCATE quanh mỗi test).
_AUTH_TABLES = (
    "trusted_devices, pending_2fa, user_2fa, user_sessions, otp_sessions, "
    "login_history, notifications, consent_log, users"
)


def _truncate_auth_tables() -> None:
    assert TEST_DATABASE_URL is not None
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE {_AUTH_TABLES} CASCADE")


@pytest.fixture(autouse=True)
def _force_inmemory_shared_rate(monkeypatch):
    """ratelimit.check_rate KHÔNG được đi nhánh PG: nhánh đó dùng `database.db`
    toàn cục (không phải adapter test) — ép về in-memory cho tất định + an toàn."""
    monkeypatch.setattr(ratelimit, "_check_rate_pg", lambda *args, **kwargs: False)


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    # DB test đã áp đủ migration; bỏ qua vòng verify-schema (initialize) để
    # get_user_by_phone/create_user/update_user không kéo thêm side-effect nạp cache.
    adapter._initialized = True
    monkeypatch.setattr(identity_api, "db", adapter)

    _truncate_auth_tables()
    try:
        yield adapter
    finally:
        _truncate_auth_tables()


# ── Helper seed/đọc dữ liệu ──

def _vn_phone() -> str:
    return "09" + f"{secrets.randbelow(10**8):08d}"


def _unique_ip() -> str:
    return f"10.{secrets.randbelow(250)}.{secrets.randbelow(250)}.{secrets.randbelow(250) + 1}"


def _seed_user(pg_db, phone=None, password_hash=None, username=None):
    user_id = str(uuid.uuid4())
    phone = phone or _vn_phone()
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (id, phone, password_hash, username, role, is_active)
            VALUES (%s::uuid, %s, %s, %s, 'user', TRUE)
            """,
            (user_id, phone, password_hash, username),
        )
    return user_id, phone


def _seed_session(pg_db, user_id, ua="pytest", ip="127.0.0.1", hours=1):
    raw = "raw-" + uuid.uuid4().hex
    with pg_db._conn() as conn:
        row = pg_db._fetchone(
            conn,
            """
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES (%s::uuid, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                identity_api._hash_token(raw),
                ua,
                ip,
                (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(),
            ),
        )
    return raw, str(pg_db._row_to_dict(row)["id"])


def _db_one(pg_db, sql, params=()):
    with pg_db._conn() as conn:
        row = pg_db._fetchone(conn, sql, params)
    return pg_db._row_to_dict(row) if row else None


def _db_all(pg_db, sql, params=()):
    with pg_db._conn() as conn:
        rows = pg_db._fetchall(conn, sql, params)
    return [pg_db._row_to_dict(r) for r in rows]


def _user_row(pg_db, user_id):
    return _db_one(pg_db, "SELECT * FROM users WHERE id::text = %s", (user_id,))


def _make_request(client_ip="127.0.0.1", ua="pytest", token=None, method="POST"):
    headers = [(b"host", b"localhost"), (b"user-agent", ua.encode())]
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/auth/x",
            "query_string": b"",
            "headers": headers,
            "client": (client_ip, 12345),
            "server": ("localhost", 80),
            "scheme": "http",
        }
    )


def _cookie_value(response: Response, name: str):
    for header in response.headers.getlist("set-cookie"):
        jar = SimpleCookie()
        jar.load(header)
        if name in jar:
            return jar[name].value
    return None


async def _drive(coro):
    """Chạy coroutine rồi chờ hết task nền (_ach_bg qua create_task/to_thread)
    NGAY TRONG loop — không để thread mồ côi ghi DB sau khi test kết thúc."""
    result = await coro
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        await asyncio.wait_for(asyncio.gather(*pending), timeout=THREAD_TIMEOUT)
    return result


# ── _check_session_binding_safe ──

def test_check_session_binding_safe_tra_true_khi_van_tay_khop():
    req = _make_request(client_ip="203.0.113.9", ua="pytest-agent")
    user = {"id": "u1", "session_ip": "203.0.113.9", "session_ua": "pytest-agent"}
    assert asyncio.run(identity_api._check_session_binding_safe(req, user)) is True
    # Phiên không lưu ngữ cảnh (ip/ua rỗng) → mặc định cho qua.
    empty_ctx = {"id": "u1", "session_ip": "", "session_ua": ""}
    assert asyncio.run(identity_api._check_session_binding_safe(req, empty_ctx)) is True


def test_check_session_binding_safe_tu_choi_khi_helper_no(monkeypatch):
    async def boom(request, user):
        raise RuntimeError("binding infra hong")

    monkeypatch.setattr(auth_middleware, "check_session_binding", boom)
    req = _make_request()
    assert asyncio.run(identity_api._check_session_binding_safe(req, {"id": "u1"})) is False


# ── _enforce_local_rate ──

def test_enforce_local_rate_chan_khi_vuot_va_ghi_hit():
    store: dict[str, list[float]] = {}
    identity_api._enforce_local_rate(store, "k", 2, 60, "cham lai")
    identity_api._enforce_local_rate(store, "k", 2, 60, "cham lai")
    assert len(store["k"]) == 2
    with pytest.raises(HTTPException) as exc:
        identity_api._enforce_local_rate(store, "k", 2, 60, "cham lai")
    assert exc.value.status_code == 429
    assert exc.value.detail == "cham lai"
    # Lượt bị chặn KHÔNG ghi thêm hit.
    assert len(store["k"]) == 2


def test_enforce_local_rate_bo_hit_ngoai_cua_so():
    store = {"k": [time.time() - 120.0]}
    identity_api._enforce_local_rate(store, "k", 1, 60, "cham lai")
    assert len(store["k"]) == 1
    assert store["k"][0] > time.time() - 5


# ── _check_shared_auth_rate ──

def test_check_shared_auth_rate_goi_check_rate_voi_tien_to_auth(monkeypatch):
    seen = []
    monkeypatch.setattr(
        ratelimit,
        "check_rate",
        lambda key, limit, window, msg: seen.append((key, limit, window, msg)),
    )
    identity_api._check_shared_auth_rate("otp_phone:0900", 3, 60, "cho da")
    assert seen == [("auth:otp_phone:0900", 3, 60, "cho da")]


def test_check_shared_auth_rate_lan_truyen_429(monkeypatch):
    def deny(key, limit, window, msg):
        raise HTTPException(429, msg)

    monkeypatch.setattr(ratelimit, "check_rate", deny)
    with pytest.raises(HTTPException) as exc:
        identity_api._check_shared_auth_rate("k", 1, 60, "qua nhanh")
    assert exc.value.status_code == 429
    assert exc.value.detail == "qua nhanh"


def test_check_shared_auth_rate_nuot_loi_ha_tang(monkeypatch):
    def broken(key, limit, window, msg):
        raise RuntimeError("backend rate hong")

    monkeypatch.setattr(ratelimit, "check_rate", broken)
    # Lỗi hạ tầng (không phải HTTPException) bị nuốt — auth không được chết vì limiter.
    assert identity_api._check_shared_auth_rate("k", 1, 60, "msg") is None


# ── cleanup_expired_data ──

def test_cleanup_expired_data_xoa_dung_hang_het_han(pg_db):
    uid, _phone = _seed_user(pg_db)
    with pg_db._conn() as conn:
        # user_sessions: 1 hết hạn + 1 còn hạn
        pg_db._execute(conn, """
            INSERT INTO user_sessions (user_id, token, expires_at)
            VALUES (%s::uuid, %s, NOW() - INTERVAL '1 hour'),
                   (%s::uuid, %s, NOW() + INTERVAL '1 hour')
        """, (uid, "tok-" + uuid.uuid4().hex, uid, "tok-" + uuid.uuid4().hex))
        # otp_sessions: 1 hết hạn + 1 còn hạn
        pg_db._execute(conn, """
            INSERT INTO otp_sessions (phone, code, expires_at)
            VALUES (%s, 'c', NOW() - INTERVAL '1 minute'),
                   (%s, 'c', NOW() + INTERVAL '5 minutes')
        """, (_vn_phone(), _vn_phone()))
        # login_history: 1 quá 90 ngày + 1 mới
        pg_db._execute(conn, """
            INSERT INTO login_history (user_id, phone, method, success, created_at)
            VALUES (%s::uuid, '091***678', 'otp', TRUE, NOW() - INTERVAL '91 days'),
                   (%s::uuid, '091***678', 'otp', TRUE, NOW())
        """, (uid, uid))
        # notifications: đã đọc + cũ (xoá), đã đọc + mới (giữ), chưa đọc + cũ (giữ)
        pg_db._execute(conn, """
            INSERT INTO notifications (user_id, type, title, is_read, created_at)
            VALUES (%s::uuid, 'like', 'a', TRUE, NOW() - INTERVAL '61 days'),
                   (%s::uuid, 'like', 'b', TRUE, NOW()),
                   (%s::uuid, 'like', 'c', FALSE, NOW() - INTERVAL '61 days')
        """, (uid, uid, uid))
        # pending_2fa + trusted_devices: mỗi bảng 1 hết hạn + 1 còn hạn
        pg_db._execute(conn, """
            INSERT INTO pending_2fa (user_id, token_hash, expires_at)
            VALUES (%s::uuid, %s, NOW() - INTERVAL '1 minute'),
                   (%s::uuid, %s, NOW() + INTERVAL '5 minutes')
        """, (uid, "p-" + uuid.uuid4().hex, uid, "p-" + uuid.uuid4().hex))
        pg_db._execute(conn, """
            INSERT INTO trusted_devices (user_id, token_hash, expires_at)
            VALUES (%s::uuid, %s, NOW() - INTERVAL '1 day'),
                   (%s::uuid, %s, NOW() + INTERVAL '30 days')
        """, (uid, "t-" + uuid.uuid4().hex, uid, "t-" + uuid.uuid4().hex))

    results = identity_api.cleanup_expired_data()

    assert results == {
        "expired_sessions": 1,
        "expired_otps": 1,
        "old_login_history": 1,
        "old_read_notifications": 1,
        "expired_pending_2fa": 1,
        "expired_trusted_devices": 1,
    }
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM user_sessions")["n"] == 1
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM otp_sessions")["n"] == 1
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM login_history")["n"] == 1
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM notifications")["n"] == 2
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM pending_2fa")["n"] == 1
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM trusted_devices")["n"] == 1


def test_cleanup_expired_data_tra_error_khi_db_no(pg_db, monkeypatch):
    def boom(conn, sql, params=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(pg_db, "_execute", boom)
    results = identity_api.cleanup_expired_data()
    assert results == {"error": "boom"}


def test_cleanup_expired_data_skip_khi_khong_pg(pg_db, monkeypatch):
    monkeypatch.setattr(pg_db, "_use_pg", False)
    assert identity_api.cleanup_expired_data() == {"skipped": True}


# ── CheckPhone.validate_phone ──

def test_checkphone_validator_chuan_hoa_khong_bat_dinh_dang():
    assert identity_api.CheckPhone(phone=" +84 912-345-678 ").phone == "0912345678"
    # Hành vi hiện tại: validator CHỈ chuẩn hoá (bỏ khoảng trắng + gạch nối),
    # KHÔNG bắt định dạng VN — chuỗi bất kỳ vẫn đi qua.
    assert identity_api.CheckPhone(phone="not-a-phone").phone == "notaphone"


# ── request_otp (+ _save_otp) ──

def test_request_otp_luu_otp_bam_va_gui_sms(pg_db, monkeypatch):
    sms_calls = []

    async def fake_send(phone, message):
        sms_calls.append((phone, message))
        return True

    monkeypatch.setattr(identity_api, "_send_sms", fake_send)
    phone = _vn_phone()
    before = datetime.now(timezone.utc)

    result = asyncio.run(
        identity_api.request_otp(
            identity_api.OTPRequest(phone=phone), _make_request(client_ip=_unique_ip())
        )
    )

    assert result["success"] is True
    assert result["message"] == "OTP đã được gửi"
    assert result["expires_in"] == identity_api.OTP_EXPIRE_MINUTES * 60

    assert len(sms_calls) == 1
    sent_phone, message = sms_calls[0]
    assert sent_phone == phone
    code = re.search(r"\b(\d{6})\b", message).group(1)

    rows = _db_all(pg_db, "SELECT * FROM otp_sessions WHERE phone = %s", (phone,))
    assert len(rows) == 1
    otp = rows[0]
    # DB chỉ giữ SHA-256 của mã, không bao giờ giữ mã trần.
    assert otp["code"] == identity_api._hash_otp(code)
    assert otp["verified"] is False
    assert otp["attempts"] == 0
    delta = otp["expires_at"] - before
    assert timedelta(minutes=4) < delta < timedelta(minutes=6)


def test_request_otp_429_khi_phone_vua_moi_xin(pg_db, monkeypatch):
    monkeypatch.setattr(identity_api, "_check_shared_auth_rate", lambda *a, **k: None)

    async def fail_send(phone, message):  # pragma: no cover - không được gọi tới
        raise AssertionError("khong duoc gui SMS khi da bi chan")

    monkeypatch.setattr(identity_api, "_send_sms", fail_send)
    phone = _vn_phone()
    monkeypatch.setitem(identity_api._otp_rate, phone, time.time())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.request_otp(
                identity_api.OTPRequest(phone=phone), _make_request(client_ip=_unique_ip())
            )
        )
    assert exc.value.status_code == 429
    assert "đợi" in exc.value.detail
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM otp_sessions WHERE phone = %s", (phone,))["n"] == 0


def test_request_otp_429_khi_ip_vuot_han_muc(pg_db, monkeypatch):
    monkeypatch.setattr(identity_api, "_check_shared_auth_rate", lambda *a, **k: None)

    async def fail_send(phone, message):  # pragma: no cover - không được gọi tới
        raise AssertionError("khong duoc gui SMS khi da bi chan")

    monkeypatch.setattr(identity_api, "_send_sms", fail_send)
    phone = _vn_phone()
    ip = _unique_ip()
    monkeypatch.setitem(
        identity_api._otp_ip_rate, ip, [time.time()] * identity_api.OTP_IP_LIMIT
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.request_otp(
                identity_api.OTPRequest(phone=phone), _make_request(client_ip=ip)
            )
        )
    assert exc.value.status_code == 429
    assert "IP" in exc.value.detail
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM otp_sessions WHERE phone = %s", (phone,))["n"] == 0


# ── _finish_login (+ _ach_bg) ──

def test_finish_login_tao_session_ghi_lich_su_streak_cookie(pg_db, monkeypatch):
    uid, phone = _seed_user(pg_db, password_hash="hash-x")
    user = _user_row(pg_db, uid)

    suspicious_calls = []
    monkeypatch.setattr(
        identity_api,
        "_check_suspicious_login",
        lambda *args: suspicious_calls.append(args),
    )
    ach_calls = []
    fake_ach = SimpleNamespace(
        check_achievements=lambda conn, u, notify=False: ach_calls.append((u, notify, conn is not None))
    )
    monkeypatch.setitem(sys.modules, "achievements", fake_ach)

    ip = _unique_ip()
    request = _make_request(client_ip=ip, ua="pytest-ua Windows NT")
    response = Response()

    result = asyncio.run(
        _drive(identity_api._finish_login(user, phone, "otp", request, response))
    )

    assert result["success"] is True
    assert result["has_password"] is True
    assert result["user"]["id"] == uid
    token = result["token"]
    assert len(token) >= 16

    session = _db_one(
        pg_db, "SELECT * FROM user_sessions WHERE user_id::text = %s", (uid,)
    )
    assert session is not None
    assert session["token"] == identity_api._hash_token(token)
    assert session["user_agent"] == "pytest-ua Windows NT"
    assert session["ip_address"] == ip
    assert session["expires_at"] > datetime.now(timezone.utc) + timedelta(days=29)

    history = _db_all(
        pg_db, "SELECT * FROM login_history WHERE user_id::text = %s", (uid,)
    )
    assert len(history) == 1
    assert history[0]["method"] == "otp"
    assert history[0]["success"] is True
    assert history[0]["phone"] == identity_api._mask_phone(phone)

    refreshed = _user_row(pg_db, uid)
    assert refreshed["login_streak"] == 1
    assert refreshed["last_login_date"] is not None

    assert suspicious_calls == [(uid, ip, "pytest-ua Windows NT", "")]
    assert ach_calls == [(uid, True, True)]
    assert _cookie_value(response, identity_api.SESSION_COOKIE_NAME) == token


# ── _short_ua ──

def test_short_ua_nhan_dien_thiet_bi():
    assert identity_api._short_ua("Mozilla/5.0 (iPhone; CPU iPhone OS 17)") == "iPhone"
    assert identity_api._short_ua("Mozilla/5.0 (Windows NT 10.0)") == "Windows"
    assert identity_api._short_ua("") == "Thiết bị"
    assert identity_api._short_ua(None) == "Thiết bị"


# ── _remember_trusted_device (+ _store) ──

def test_remember_trusted_device_ghi_hang_va_cookie(pg_db):
    uid, _phone = _seed_user(pg_db)
    ip = _unique_ip()
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X)"
    request = _make_request(client_ip=ip, ua=ua)
    response = Response()

    asyncio.run(identity_api._remember_trusted_device({"id": uid}, request, response))

    raw = _cookie_value(response, identity_api.TRUSTED_DEVICE_COOKIE_NAME)
    assert raw
    row = _db_one(
        pg_db, "SELECT * FROM trusted_devices WHERE user_id::text = %s", (uid,)
    )
    assert row is not None
    # Cookie giữ token trần, DB chỉ giữ hash.
    assert row["token_hash"] == identity_api._hash_token(raw)
    assert row["device_name"] == "Macintosh"
    assert row["ip"] == ip
    assert row["user_agent"] == ua
    assert row["expires_at"] > datetime.now(timezone.utc) + timedelta(days=89)


# ── _register_new_user ──

def test_register_new_user_tu_choi_khong_consent(pg_db):
    phone = _vn_phone()
    body = identity_api.OTPVerify(phone=phone, code="123456", consent=False)
    with pytest.raises(HTTPException) as exc:
        identity_api._register_new_user(phone, body)
    assert exc.value.status_code == 400
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM users WHERE phone = %s", (phone,))["n"] == 0


def test_register_new_user_tao_day_du(pg_db):
    phone = _vn_phone()
    uname = "user" + uuid.uuid4().hex[:10]
    body = identity_api.OTPVerify(
        phone=phone,
        code="123456",
        consent=True,
        full_name="Nguyễn <Văn> A",
        username=uname.upper(),
        password="matkhau123",
        date_of_birth="1990-01-01",
    )

    user = identity_api._register_new_user(phone, body)

    row = _db_one(pg_db, "SELECT * FROM users WHERE phone = %s", (phone,))
    assert row is not None
    assert str(user["id"]) == str(row["id"])
    # full_name được escape HTML, username hạ về chữ thường.
    assert row["full_name"] == "Nguyễn &lt;Văn&gt; A"
    assert row["display_name"] == "Nguyễn &lt;Văn&gt; A"
    assert row["username"] == uname
    assert row["consent_version"] == identity_api.CONSENT_VERSION
    assert str(row["date_of_birth"]).startswith("1990-01-01")
    assert identity_api._verify_password("matkhau123", row["password_hash"]) is True


def test_register_new_user_username_trung_409(pg_db):
    taken = "dupname" + uuid.uuid4().hex[:8]
    _seed_user(pg_db, username=taken)
    phone = _vn_phone()
    body = identity_api.OTPVerify(
        phone=phone, code="123456", consent=True, username=taken.upper()
    )
    with pytest.raises(HTTPException) as exc:
        identity_api._register_new_user(phone, body)
    assert exc.value.status_code == 409
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM users WHERE phone = %s", (phone,))["n"] == 0


def test_register_new_user_password_ngan_400(pg_db):
    phone = _vn_phone()
    body = identity_api.OTPVerify(phone=phone, code="123456", consent=True, password="a1")
    with pytest.raises(HTTPException) as exc:
        identity_api._register_new_user(phone, body)
    assert exc.value.status_code == 400
    assert _db_one(pg_db, "SELECT COUNT(*) AS n FROM users WHERE phone = %s", (phone,))["n"] == 0


def test_register_new_user_username_xau_bi_bo_qua(pg_db):
    phone = _vn_phone()
    # Bắt đầu bằng số → rớt regex → bị BỎ QUA im lặng, user vẫn được tạo.
    body = identity_api.OTPVerify(phone=phone, code="123456", consent=True, username="9bad")
    identity_api._register_new_user(phone, body)
    row = _db_one(pg_db, "SELECT username FROM users WHERE phone = %s", (phone,))
    assert row is not None
    assert row["username"] is None


# ── check_phone ──

def test_check_phone_ton_tai_va_khong_ton_tai(pg_db):
    _uid, phone = _seed_user(pg_db)
    result = asyncio.run(
        identity_api.check_phone(
            identity_api.CheckPhone(phone=phone), _make_request(client_ip=_unique_ip())
        )
    )
    assert result == {"exists": True}

    result = asyncio.run(
        identity_api.check_phone(
            identity_api.CheckPhone(phone=_vn_phone()), _make_request(client_ip=_unique_ip())
        )
    )
    assert result == {"exists": False}


def test_check_phone_429_khi_ip_vuot_han_muc(pg_db, monkeypatch):
    ip = _unique_ip()
    monkeypatch.setitem(
        identity_api._check_phone_ip_rate,
        ip,
        [time.time()] * identity_api.CHECK_PHONE_IP_LIMIT,
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.check_phone(
                identity_api.CheckPhone(phone=_vn_phone()), _make_request(client_ip=ip)
            )
        )
    assert exc.value.status_code == 429


# ── set_password (+ _revoke_others) ──

def test_set_password_dat_moi_va_thu_hoi_phien_khac(pg_db):
    uid, _phone = _seed_user(pg_db, password_hash=None)
    ip = _unique_ip()
    current_raw, _sid = _seed_session(pg_db, uid, ua="pytest", ip=ip)
    _other_raw, other_sid = _seed_session(pg_db, uid, ua="pytest", ip=ip)
    request = _make_request(client_ip=ip, ua="pytest", token=current_raw)

    result = asyncio.run(
        identity_api.set_password(
            identity_api.SetPassword(password="matkhaumoi1"), request
        )
    )

    assert result["success"] is True
    row = _user_row(pg_db, uid)
    assert identity_api._verify_password("matkhaumoi1", row["password_hash"]) is True
    # Phiên hiện tại được GIỮ, mọi phiên khác bị thu hồi.
    sessions = _db_all(
        pg_db, "SELECT id, token FROM user_sessions WHERE user_id::text = %s", (uid,)
    )
    assert len(sessions) == 1
    assert sessions[0]["token"] == identity_api._hash_token(current_raw)
    assert str(sessions[0]["id"]) != other_sid


def test_set_password_401_khi_chua_dang_nhap(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.set_password(
                identity_api.SetPassword(password="matkhaumoi1"),
                _make_request(client_ip=_unique_ip()),
            )
        )
    assert exc.value.status_code == 401


def test_set_password_400_thieu_mat_khau_hien_tai(pg_db):
    old_hash = identity_api._hash_password("matkhaucu1")
    uid, _phone = _seed_user(pg_db, password_hash=old_hash)
    ip = _unique_ip()
    current_raw, _sid = _seed_session(pg_db, uid, ua="pytest", ip=ip)
    request = _make_request(client_ip=ip, ua="pytest", token=current_raw)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.set_password(
                identity_api.SetPassword(password="matkhaumoi1"), request
            )
        )
    assert exc.value.status_code == 400
    assert _user_row(pg_db, uid)["password_hash"] == old_hash


# ── logout (+ _query) ──

def test_logout_xoa_phien_va_xoa_cookie(pg_db):
    uid, _phone = _seed_user(pg_db)
    raw, _sid = _seed_session(pg_db, uid)
    response = Response()

    result = asyncio.run(
        identity_api.logout(_make_request(client_ip=_unique_ip(), token=raw), response)
    )

    assert result == {"success": True}
    assert _db_one(
        pg_db, "SELECT COUNT(*) AS n FROM user_sessions WHERE user_id::text = %s", (uid,)
    )["n"] == 0
    headers = response.headers.getlist("set-cookie")
    assert any(h.startswith(identity_api.SESSION_COOKIE_NAME + "=") for h in headers)


def test_logout_khong_token_van_thanh_cong(pg_db):
    uid, _phone = _seed_user(pg_db)
    _seed_session(pg_db, uid)
    response = Response()

    result = asyncio.run(
        identity_api.logout(_make_request(client_ip=_unique_ip()), response)
    )

    assert result == {"success": True}
    # Không có token → không đụng DB, phiên của người khác còn nguyên.
    assert _db_one(
        pg_db, "SELECT COUNT(*) AS n FROM user_sessions WHERE user_id::text = %s", (uid,)
    )["n"] == 1
    assert response.headers.getlist("set-cookie")


# ── refresh_token (+ _rotate) ──

def test_refresh_token_xoay_token_va_gia_han(pg_db):
    uid, _phone = _seed_user(pg_db)
    old_raw, _sid = _seed_session(pg_db, uid)
    response = Response()

    result = asyncio.run(
        identity_api.refresh_token(
            _make_request(client_ip=_unique_ip(), token=old_raw), response
        )
    )

    assert result["success"] is True
    new_token = result["token"]
    assert new_token != old_raw
    assert _db_one(
        pg_db, "SELECT COUNT(*) AS n FROM user_sessions WHERE token = %s",
        (identity_api._hash_token(old_raw),),
    )["n"] == 0
    row = _db_one(
        pg_db, "SELECT * FROM user_sessions WHERE token = %s",
        (identity_api._hash_token(new_token),),
    )
    assert row is not None
    assert str(row["user_id"]) == uid
    assert row["expires_at"] > datetime.now(timezone.utc) + timedelta(days=29)
    assert _cookie_value(response, identity_api.SESSION_COOKIE_NAME) == new_token


def test_refresh_token_401_khong_token(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.refresh_token(_make_request(client_ip=_unique_ip()), Response())
        )
    assert exc.value.status_code == 401


def test_refresh_token_401_token_la(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.refresh_token(
                _make_request(client_ip=_unique_ip(), token="la-" + uuid.uuid4().hex),
                Response(),
            )
        )
    assert exc.value.status_code == 401
    assert "Session" in exc.value.detail


# ── list_sessions (+ _query) ──

def test_list_sessions_liet_ke_va_an_phien_noi_bo(pg_db):
    uid, _phone = _seed_user(pg_db)
    current_raw, current_sid = _seed_session(
        pg_db, uid, ua="Mozilla/5.0 Chrome/1.0", ip="203.0.113.7"
    )
    _other_raw, other_sid = _seed_session(
        pg_db, uid, ua="Mozilla/5.0 Safari/600", ip="198.51.100.9"
    )
    _seed_session(pg_db, uid, ua="python-requests/2.31", ip="127.0.0.1")

    result = asyncio.run(
        identity_api.list_sessions(
            _make_request(client_ip="203.0.113.7", ua="Mozilla/5.0 Chrome/1.0", token=current_raw)
        )
    )

    assert result["hidden_internal_count"] == 1
    sessions = {s["id"]: s for s in result["sessions"]}
    assert set(sessions) == {current_sid, other_sid}
    assert sessions[current_sid]["is_current"] is True
    assert sessions[other_sid]["is_current"] is False
    assert sessions[other_sid]["ip_address"] == "198.51.*.*"
    # Token hash KHÔNG được lộ ra ngoài payload.
    assert "token" not in sessions[current_sid]


def test_list_sessions_401_khi_chua_dang_nhap(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.list_sessions(_make_request(client_ip=_unique_ip())))
    assert exc.value.status_code == 401


# ── revoke_session (+ _query) ──

def test_revoke_session_xoa_phien_cua_minh(pg_db):
    uid, _phone = _seed_user(pg_db)
    current_raw, current_sid = _seed_session(pg_db, uid)
    _other_raw, other_sid = _seed_session(pg_db, uid)

    result = asyncio.run(
        identity_api.revoke_session(
            other_sid, _make_request(client_ip=_unique_ip(), token=current_raw)
        )
    )

    assert result == {"success": True}
    remaining = _db_all(
        pg_db, "SELECT id FROM user_sessions WHERE user_id::text = %s", (uid,)
    )
    assert [str(r["id"]) for r in remaining] == [current_sid]


def test_revoke_session_khong_xoa_phien_nguoi_khac(pg_db):
    uid_a, _pa = _seed_user(pg_db)
    raw_a, _sid_a = _seed_session(pg_db, uid_a)
    uid_b, _pb = _seed_user(pg_db)
    _raw_b, sid_b = _seed_session(pg_db, uid_b)

    result = asyncio.run(
        identity_api.revoke_session(
            sid_b, _make_request(client_ip=_unique_ip(), token=raw_a)
        )
    )

    # Hành vi hiện tại: vẫn trả success=True nhưng phiên người khác còn nguyên.
    assert result == {"success": True}
    assert _db_one(
        pg_db, "SELECT COUNT(*) AS n FROM user_sessions WHERE id::text = %s", (sid_b,)
    )["n"] == 1


def test_revoke_session_400_id_khong_hop_le(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.revoke_session("bad/id", _make_request(client_ip=_unique_ip()))
        )
    assert exc.value.status_code == 400
