"""Đặc tả hành vi HIỆN TẠI của miền 2FA trong identity/api.py trên PostgreSQL thật.

Phủ các handler/closure chưa từng chạy trên DB thật:
- _get_2fa_row, twofa_setup (+_store), twofa_verify_setup (+_enable),
  twofa_disable (+_check_code, _disable), twofa_status (+_q), _verify_2fa_code,
  list_trusted_devices (+_q), delete_trusted_device (+_del),
  _get_current_user_or_none (+_query).

Khuôn harness: adapter Database() ép _use_pg/_dsn, patch identity_api.db;
side-effect ngoài miền (ratelimit.check_rate) stub ghi-nhận-lời-gọi;
TOTP mã hoá bằng khoá giả qua env TOTP_ENC_KEY (monkeypatch, không đụng secret thật).
Handler gọi thẳng qua asyncio.run với Request giả SimpleNamespace.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database as database_module
import pyotp
import ratelimit
import twofactor
from identity import api as identity_api


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

_TABLES = (
    "users",
    "user_sessions",
    "user_2fa",
    "user_2fa_recovery_codes",
    "trusted_devices",
    "pending_2fa",
)
_TRUNCATE_SQL = (
    "TRUNCATE user_2fa, user_2fa_recovery_codes, trusted_devices, "
    "pending_2fa, user_sessions, users CASCADE"
)


@pytest.fixture(scope="session", autouse=True)
def _postgres_schema():
    # DB đã migrate sẵn (81 migration) — chỉ xác nhận các bảng miền 2FA tồn tại.
    # Nếu env có mà DB chết: connect() nổ → cả file ĐỎ (không skip), đúng yêu cầu cổng.
    assert TEST_DATABASE_URL is not None
    conn = psycopg2.connect(TEST_DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cursor:
                for table in _TABLES:
                    cursor.execute("SELECT to_regclass(%s)", (table,))
                    assert cursor.fetchone()[0] is not None, (
                        f"thiếu bảng {table} — DB test chưa migrate đủ"
                    )
    finally:
        conn.close()
    try:
        yield
    finally:
        conn = psycopg2.connect(TEST_DATABASE_URL)
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(_TRUNCATE_SQL)
        finally:
            conn.close()


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
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


@pytest.fixture
def rate_calls(monkeypatch):
    """Stub ratelimit.check_rate (handler import cục bộ lúc gọi nên patch module là đủ).
    check_rate thật có nhánh _check_rate_pg đụng bảng shared_rate_limits — không để chạy."""
    calls = []

    def _record(key, limit, window, msg=None):
        calls.append((key, limit, window))

    monkeypatch.setattr(ratelimit, "check_rate", _record)
    return calls


@pytest.fixture
def totp_key(monkeypatch):
    """Khoá mã hoá TOTP giả, chỉ sống trong test — twofactor._app_secret đọc env mỗi lần."""
    monkeypatch.setenv("TOTP_ENC_KEY", "vl360-totp-test-key-gia-lap-khong-dung-that")


def _enable_2fa_flag(monkeypatch, value: bool = True):
    monkeypatch.setattr(identity_api._cfg, "TWO_FACTOR_ENABLED", value)


# ── Seed helpers (mỗi test dữ liệu riêng, uuid ngẫu nhiên) ──


def _seed_user(pg_db) -> tuple[str, str]:
    user_id = str(uuid.uuid4())
    phone = f"test-{uuid.uuid4().hex}"
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (id, phone, password_hash, role, is_active)
            VALUES (%s::uuid, %s, 'seed-hash', 'user', TRUE)
            """,
            (user_id, phone),
        )
    return user_id, phone


def _seed_session_token(pg_db, user_id: str, expired: bool = False) -> str:
    token = f"tok-{uuid.uuid4().hex}"
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES (%s::uuid, %s, 'pytest-ua', '127.0.0.1', %s)
            """,
            (user_id, identity_api._hash_token(token), datetime.now(timezone.utc) + delta),
        )
    return token


def _request(token: str | None = None, cookies: dict | None = None) -> SimpleNamespace:
    headers = {"user-agent": "pytest-ua"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    return SimpleNamespace(
        headers=headers,
        cookies=cookies or {},
        client=SimpleNamespace(host="127.0.0.1", port=12345),
    )


def _logged_in(pg_db) -> tuple[str, SimpleNamespace]:
    user_id, _phone = _seed_user(pg_db)
    token = _seed_session_token(pg_db, user_id)
    return user_id, _request(token)


def _seed_2fa(pg_db, user_id: str, secret: str, enabled: bool = True) -> None:
    enc = twofactor.encrypt_secret(secret)
    verified_at = datetime.now(timezone.utc) if enabled else None
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_2fa (user_id, secret_enc, enabled, verified_at)
            VALUES (%s::uuid, %s, %s, %s)
            """,
            (user_id, enc, enabled, verified_at),
        )


def _seed_recovery_code(pg_db, user_id: str, code: str, used: bool = False) -> None:
    used_at = datetime.now(timezone.utc) if used else None
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_2fa_recovery_codes (user_id, code_hash, used_at)
            VALUES (%s::uuid, %s, %s)
            """,
            (user_id, twofactor.hash_recovery_code(code), used_at),
        )


def _seed_trusted_device(
    pg_db,
    user_id: str,
    device_name: str = "May pytest",
    ip: str = "203.0.113.7",
    last_used_offset_hours: int = 0,
    expired: bool = False,
) -> str:
    device_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now - timedelta(days=1) if expired else now + timedelta(days=30)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO trusted_devices
                (id, user_id, token_hash, device_name, ip, user_agent, last_used_at, expires_at)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s, 'pytest-ua', %s, %s)
            """,
            (
                device_id,
                user_id,
                f"th-{uuid.uuid4().hex}",
                device_name,
                ip,
                now - timedelta(hours=last_used_offset_hours),
                expires_at,
            ),
        )
    return device_id


def _fetch_2fa_state(pg_db, user_id: str) -> tuple[dict | None, list, int]:
    with pg_db._conn() as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT secret_enc, enabled, verified_at FROM user_2fa WHERE user_id::text = %s",
            (user_id,),
        )
        codes = pg_db._fetchall(
            conn,
            "SELECT code_hash, used_at FROM user_2fa_recovery_codes WHERE user_id::text = %s",
            (user_id,),
        )
        devices = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS c FROM trusted_devices WHERE user_id::text = %s",
            (user_id,),
        )
    return (dict(row) if row else None), [dict(c) for c in codes], int(devices["c"])


def _totp_now(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def _wrong_totp(secret: str) -> str:
    good = _totp_now(secret)
    return "000000" if good != "000000" else "111111"


def _tfa_verify_body(code: str, recovery: bool = False) -> "identity_api._TwoFAVerify":
    return identity_api._TwoFAVerify(
        challenge_id=f"challenge-{uuid.uuid4().hex}", code=code, recovery=recovery
    )


# ── _get_2fa_row ──


def test_get_2fa_row_tra_none_khi_chua_co(pg_db):
    user_id, _phone = _seed_user(pg_db)
    assert identity_api._get_2fa_row(user_id) is None


def test_get_2fa_row_tra_dict_day_du(pg_db, totp_key):
    user_id, _phone = _seed_user(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, user_id, secret, enabled=False)
    row = identity_api._get_2fa_row(user_id)
    assert row is not None
    assert str(row["user_id"]) == user_id
    assert row["enabled"] is False
    assert twofactor.decrypt_secret(row["secret_enc"]) == secret


# ── twofa_setup (+ closure _store) ──


def test_twofa_setup_401_khi_chua_dang_nhap(pg_db, monkeypatch, rate_calls, totp_key):
    _enable_2fa_flag(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_setup(_request(None), _csrf=None))
    assert exc.value.status_code == 401


def test_twofa_setup_403_khi_tinh_nang_tat(pg_db, monkeypatch, rate_calls, totp_key):
    _enable_2fa_flag(monkeypatch, False)
    _user_id, request = _logged_in(pg_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_setup(request, _csrf=None))
    assert exc.value.status_code == 403


def test_twofa_setup_luu_secret_ma_hoa_o_trang_thai_chua_bat(
    pg_db, monkeypatch, rate_calls, totp_key
):
    _enable_2fa_flag(monkeypatch)
    user_id, request = _logged_in(pg_db)
    out = asyncio.run(identity_api.twofa_setup(request, _csrf=None))
    assert set(out) == {"secret", "otpauth_uri", "qr"}
    assert out["otpauth_uri"].startswith("otpauth://totp/")
    assert out["qr"].startswith("data:image/png;base64,")
    row, codes, _devices = _fetch_2fa_state(pg_db, user_id)
    assert row is not None
    assert row["enabled"] is False
    assert row["verified_at"] is None
    # secret trả về đúng là bản giải mã của secret_enc trong bảng
    assert twofactor.decrypt_secret(row["secret_enc"]) == out["secret"]
    assert codes == []
    assert (f"2fa-setup:{user_id}", 5, 600) in rate_calls


def test_twofa_setup_goi_lai_ghi_de_secret_dang_cho(
    pg_db, monkeypatch, rate_calls, totp_key
):
    # Nhánh ON CONFLICT của _store: setup lần 2 thay secret, vẫn enabled = FALSE.
    _enable_2fa_flag(monkeypatch)
    user_id, request = _logged_in(pg_db)
    first = asyncio.run(identity_api.twofa_setup(request, _csrf=None))
    second = asyncio.run(identity_api.twofa_setup(request, _csrf=None))
    assert first["secret"] != second["secret"]
    row, _codes, _devices = _fetch_2fa_state(pg_db, user_id)
    assert row["enabled"] is False
    assert twofactor.decrypt_secret(row["secret_enc"]) == second["secret"]


def test_twofa_setup_400_khi_da_bat(pg_db, monkeypatch, rate_calls, totp_key):
    _enable_2fa_flag(monkeypatch)
    user_id, request = _logged_in(pg_db)
    _seed_2fa(pg_db, user_id, pyotp.random_base32(), enabled=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_setup(request, _csrf=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == "2FA đã được bật"


# ── twofa_verify_setup (+ closure _enable) ──


def test_twofa_verify_setup_bat_2fa_va_phat_ma_khoi_phuc(
    pg_db, monkeypatch, rate_calls, totp_key
):
    _enable_2fa_flag(monkeypatch)
    user_id, request = _logged_in(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, user_id, secret, enabled=False)
    # mã khôi phục cũ phải bị _enable xoá trước khi phát bộ mới
    _seed_recovery_code(pg_db, user_id, "stale-00000")

    body = identity_api._TwoFACode(code=_totp_now(secret))
    out = asyncio.run(identity_api.twofa_verify_setup(body, request, _csrf=None))
    assert out["success"] is True
    assert len(out["recovery_codes"]) == 8

    row, codes, _devices = _fetch_2fa_state(pg_db, user_id)
    assert row["enabled"] is True
    assert row["verified_at"] is not None
    assert len(codes) == 8
    assert {c["code_hash"] for c in codes} == {
        twofactor.hash_recovery_code(c) for c in out["recovery_codes"]
    }
    assert all(c["used_at"] is None for c in codes)
    assert (f"2fa-verify-setup:{user_id}", 5, 600) in rate_calls


def test_twofa_verify_setup_400_ma_sai_khong_doi_trang_thai(
    pg_db, monkeypatch, rate_calls, totp_key
):
    _enable_2fa_flag(monkeypatch)
    user_id, request = _logged_in(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, user_id, secret, enabled=False)
    body = identity_api._TwoFACode(code=_wrong_totp(secret))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_verify_setup(body, request, _csrf=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == "Mã không đúng. Vui lòng thử lại"
    row, codes, _devices = _fetch_2fa_state(pg_db, user_id)
    assert row["enabled"] is False
    assert codes == []


def test_twofa_verify_setup_400_khi_chua_setup(pg_db, monkeypatch, rate_calls, totp_key):
    _enable_2fa_flag(monkeypatch)
    _user_id, request = _logged_in(pg_db)
    body = identity_api._TwoFACode(code="123456")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_verify_setup(body, request, _csrf=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == "Chưa bắt đầu thiết lập 2FA"


# ── twofa_disable (+ closure _check_code, _disable) ──


def test_twofa_disable_401_khi_chua_dang_nhap(pg_db, rate_calls, totp_key):
    body = identity_api._TwoFACode(code="123456")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_disable(body, _request(None), _csrf=None))
    assert exc.value.status_code == 401


def test_twofa_disable_bang_totp_xoa_sach_trang_thai(
    pg_db, monkeypatch, rate_calls, totp_key
):
    # Hành vi hiện tại: /2fa/disable KHÔNG đọc cờ TWO_FACTOR_ENABLED — để cờ tắt
    # (mặc định) mà disable vẫn chạy, đặc tả sự độc lập đó luôn.
    _enable_2fa_flag(monkeypatch, False)
    user_id, request = _logged_in(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, user_id, secret, enabled=True)
    _seed_recovery_code(pg_db, user_id, "aaaaa-11111")
    _seed_trusted_device(pg_db, user_id)

    body = identity_api._TwoFACode(code=_totp_now(secret))
    out = asyncio.run(identity_api.twofa_disable(body, request, _csrf=None))
    assert out == {"success": True}
    row, codes, devices = _fetch_2fa_state(pg_db, user_id)
    assert row is None
    assert codes == []
    assert devices == 0
    assert (f"2fa-disable:{user_id}", 5, 600) in rate_calls


def test_twofa_disable_bang_ma_khoi_phuc(pg_db, monkeypatch, rate_calls, totp_key):
    user_id, request = _logged_in(pg_db)
    _seed_2fa(pg_db, user_id, pyotp.random_base32(), enabled=True)
    _seed_recovery_code(pg_db, user_id, "bbbbb-22222")
    body = identity_api._TwoFACode(code="bbbbb-22222")
    out = asyncio.run(identity_api.twofa_disable(body, request, _csrf=None))
    assert out == {"success": True}
    row, codes, _devices = _fetch_2fa_state(pg_db, user_id)
    assert row is None
    assert codes == []


def test_twofa_disable_400_ma_sai_giu_nguyen_trang_thai(
    pg_db, monkeypatch, rate_calls, totp_key
):
    user_id, request = _logged_in(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, user_id, secret, enabled=True)
    _seed_recovery_code(pg_db, user_id, "ccccc-33333")
    _seed_trusted_device(pg_db, user_id)
    body = identity_api._TwoFACode(code=_wrong_totp(secret))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_disable(body, request, _csrf=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == "Mã không đúng"
    row, codes, devices = _fetch_2fa_state(pg_db, user_id)
    assert row["enabled"] is True
    assert len(codes) == 1
    assert devices == 1


def test_twofa_disable_400_khi_chua_bat(pg_db, monkeypatch, rate_calls, totp_key):
    user_id, request = _logged_in(pg_db)
    _seed_2fa(pg_db, user_id, pyotp.random_base32(), enabled=False)
    body = identity_api._TwoFACode(code="123456")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_disable(body, request, _csrf=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == "2FA chưa được bật"


# ── twofa_status (+ closure _q) ──


def test_twofa_status_401_khi_chua_dang_nhap(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.twofa_status(_request(None)))
    assert exc.value.status_code == 401


def test_twofa_status_mac_dinh_tat(pg_db, totp_key):
    # Không có hàng user_2fa → enabled False; có hàng nhưng enabled FALSE cũng vậy
    # (và _q bỏ qua luôn phần đếm mã khôi phục).
    _user_id, request = _logged_in(pg_db)
    assert asyncio.run(identity_api.twofa_status(request)) == {
        "enabled": False,
        "recovery_remaining": 0,
    }

    other_id, other_request = _logged_in(pg_db)
    _seed_2fa(pg_db, other_id, pyotp.random_base32(), enabled=False)
    _seed_recovery_code(pg_db, other_id, "ddddd-44444")
    assert asyncio.run(identity_api.twofa_status(other_request)) == {
        "enabled": False,
        "recovery_remaining": 0,
    }


def test_twofa_status_dem_ma_khoi_phuc_chua_dung(pg_db, totp_key):
    user_id, request = _logged_in(pg_db)
    _seed_2fa(pg_db, user_id, pyotp.random_base32(), enabled=True)
    _seed_recovery_code(pg_db, user_id, "eeee1-55555")
    _seed_recovery_code(pg_db, user_id, "eeee2-55555")
    _seed_recovery_code(pg_db, user_id, "eeee3-55555")
    _seed_recovery_code(pg_db, user_id, "eeee4-55555", used=True)
    assert asyncio.run(identity_api.twofa_status(request)) == {
        "enabled": True,
        "recovery_remaining": 3,
    }


# ── _verify_2fa_code ──


def _call_verify_2fa(user_id: str, body) -> bool:
    return identity_api._verify_2fa_code(
        user_id,
        body,
        twofactor.decrypt_secret,
        twofactor.verify_totp,
        twofactor.recovery_code_matches,
    )


def test_verify_2fa_code_totp_dung(pg_db, totp_key):
    user_id, _phone = _seed_user(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, user_id, secret, enabled=True)
    assert _call_verify_2fa(user_id, _tfa_verify_body(_totp_now(secret))) is True


def test_verify_2fa_code_false_khi_chua_bat(pg_db, totp_key):
    # Không có hàng → False; có hàng nhưng enabled FALSE cũng False (WHERE enabled = TRUE).
    absent_id, _phone = _seed_user(pg_db)
    assert _call_verify_2fa(absent_id, _tfa_verify_body("123456")) is False

    disabled_id, _phone2 = _seed_user(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, disabled_id, secret, enabled=False)
    assert _call_verify_2fa(disabled_id, _tfa_verify_body(_totp_now(secret))) is False


def test_verify_2fa_code_ma_khoi_phuc_danh_dau_da_dung(pg_db, totp_key):
    user_id, _phone = _seed_user(pg_db)
    _seed_2fa(pg_db, user_id, pyotp.random_base32(), enabled=True)
    _seed_recovery_code(pg_db, user_id, "fffff-66666")

    assert _call_verify_2fa(
        user_id, _tfa_verify_body("fffff-66666", recovery=True)
    ) is True
    _row, codes, _devices = _fetch_2fa_state(pg_db, user_id)
    assert len(codes) == 1
    assert codes[0]["used_at"] is not None
    # dùng-một-lần: cùng mã đó lần hai phải False
    assert _call_verify_2fa(
        user_id, _tfa_verify_body("fffff-66666", recovery=True)
    ) is False


def test_verify_2fa_code_co_recovery_thi_bo_qua_totp(pg_db, totp_key):
    # Hành vi hiện tại: body.recovery=True làm nhánh TOTP bị bỏ qua hoàn toàn —
    # mã TOTP đúng vẫn False nếu không khớp mã khôi phục nào.
    user_id, _phone = _seed_user(pg_db)
    secret = pyotp.random_base32()
    _seed_2fa(pg_db, user_id, secret, enabled=True)
    assert _call_verify_2fa(
        user_id, _tfa_verify_body(_totp_now(secret), recovery=True)
    ) is False


# ── list_trusted_devices (+ closure _q) ──


def test_list_trusted_devices_401_khi_chua_dang_nhap(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(identity_api.list_trusted_devices(_request(None)))
    assert exc.value.status_code == 401


def test_list_trusted_devices_loc_het_han_che_ip_va_sap_xep(pg_db):
    user_id, request = _logged_in(pg_db)
    older = _seed_trusted_device(
        pg_db, user_id, device_name="May cu", last_used_offset_hours=2
    )
    newer = _seed_trusted_device(
        pg_db, user_id, device_name="May moi", last_used_offset_hours=1
    )
    _seed_trusted_device(pg_db, user_id, device_name="Het han", expired=True)
    other_id, _phone = _seed_user(pg_db)
    _seed_trusted_device(pg_db, other_id, device_name="Cua nguoi khac")

    out = asyncio.run(identity_api.list_trusted_devices(request))
    devices = out["devices"]
    # thiết bị hết hạn và của user khác không xuất hiện; sắp theo last_used_at DESC
    assert [d["id"] for d in devices] == [newer, older]
    assert devices[0]["device_name"] == "May moi"
    assert devices[0]["ip"] == "203.0.*.*"
    # response không lộ token_hash/expires_at — đúng bộ khoá hiện tại
    assert set(devices[0]) == {"id", "device_name", "ip", "created_at", "last_used_at"}
    assert devices[0]["created_at"] and devices[0]["last_used_at"]


# ── delete_trusted_device (+ closure _del) ──


def test_delete_trusted_device_xoa_dung_hang(pg_db, rate_calls):
    user_id, request = _logged_in(pg_db)
    target = _seed_trusted_device(pg_db, user_id, device_name="Xoa toi")
    keep = _seed_trusted_device(pg_db, user_id, device_name="Giu lai")

    out = asyncio.run(
        identity_api.delete_trusted_device(target, request, _csrf=None)
    )
    assert out == {"success": True}
    with pg_db._conn() as conn:
        rows = pg_db._fetchall(
            conn,
            "SELECT id::text AS id FROM trusted_devices WHERE user_id::text = %s",
            (user_id,),
        )
    assert [r["id"] for r in rows] == [keep]
    assert (f"trusted_del:{user_id}", 20, 300) in rate_calls


def test_delete_trusted_device_khong_dung_thiet_bi_nguoi_khac(pg_db, rate_calls):
    # Hành vi hiện tại: xoá device_id của user khác vẫn trả success=True (không 404),
    # nhưng hàng của người khác còn nguyên nhờ điều kiện user_id trong _del.
    _user_id, request = _logged_in(pg_db)
    victim_id, _phone = _seed_user(pg_db)
    victim_device = _seed_trusted_device(pg_db, victim_id)

    out = asyncio.run(
        identity_api.delete_trusted_device(victim_device, request, _csrf=None)
    )
    assert out == {"success": True}
    with pg_db._conn() as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS c FROM trusted_devices WHERE id::text = %s",
            (victim_device,),
        )
    assert int(row["c"]) == 1


def test_delete_trusted_device_400_id_khong_hop_le(pg_db, rate_calls):
    _user_id, request = _logged_in(pg_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            identity_api.delete_trusted_device("khong*hop*le", request, _csrf=None)
        )
    assert exc.value.status_code == 400


# ── _get_current_user_or_none (+ closure _query) ──


def test_get_current_user_qua_bearer_token(pg_db):
    user_id, _phone = _seed_user(pg_db)
    token = _seed_session_token(pg_db, user_id)
    user = asyncio.run(identity_api._get_current_user_or_none(_request(token)))
    assert user is not None
    assert str(user["id"]) == user_id
    assert user["session_ip"] == "127.0.0.1"
    assert user["session_ua"] == "pytest-ua"


def test_get_current_user_qua_cookie(pg_db):
    user_id, _phone = _seed_user(pg_db)
    token = _seed_session_token(pg_db, user_id)
    request = SimpleNamespace(
        headers={"user-agent": "pytest-ua"},
        cookies={"vl360_token": token},
        client=SimpleNamespace(host="127.0.0.1", port=12345),
    )
    user = asyncio.run(identity_api._get_current_user_or_none(request))
    assert user is not None
    assert str(user["id"]) == user_id


def test_get_current_user_none_khi_khong_co_hoac_token_ngan(pg_db):
    assert asyncio.run(identity_api._get_current_user_or_none(_request(None))) is None
    # token < 16 ký tự bị _extract_token loại ngay, không chạm DB
    assert asyncio.run(
        identity_api._get_current_user_or_none(_request("ngan-qua"))
    ) is None


def test_get_current_user_none_khi_session_het_han(pg_db):
    user_id, _phone = _seed_user(pg_db)
    token = _seed_session_token(pg_db, user_id, expired=True)
    assert asyncio.run(identity_api._get_current_user_or_none(_request(token))) is None


def test_get_current_user_none_khi_user_bi_khoa(pg_db):
    user_id, _phone = _seed_user(pg_db)
    token = _seed_session_token(pg_db, user_id)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn, "UPDATE users SET is_active = FALSE WHERE id::text = %s", (user_id,)
        )
    assert asyncio.run(identity_api._get_current_user_or_none(_request(token))) is None


def test_get_current_user_none_khi_db_loi(pg_db, monkeypatch):
    # _query nuốt exception DB (log rồi trả None) — đặc tả nhánh except.
    user_id, _phone = _seed_user(pg_db)
    token = _seed_session_token(pg_db, user_id)

    def _boom(_conn, _sql, _params=None):
        raise RuntimeError("db down (gia lap)")

    monkeypatch.setattr(pg_db, "_fetchone", _boom)
    assert asyncio.run(identity_api._get_current_user_or_none(_request(token))) is None
