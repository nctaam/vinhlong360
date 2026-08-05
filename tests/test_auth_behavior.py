"""Kiểm HÀNH VI thật của agent/auth.py: đăng nhập, phiên, 2FA, thiết bị tin cậy.

Vì sao có file này: auth.py là một trong năm "vùng mù" mà CLAUDE.md §B3 gọi tên
(database.py, chat handler của server.py, social.py, auth.py, ETL), coverage ~25%.
Một phần test auth sẵn có đọc source bằng inspect.getsource() rồi so chuỗi — loại
đó đỏ khi refactor đúng và xanh khi hành vi sai; riêng
agent/tests/test_auth_security_hardening.py có 24 lần. Ở đây KHÔNG có assert nào
nhìn vào source: mọi kiểm tra đều gọi endpoint thật qua TestClient rồi soi status
code, cookie, và trạng thái DB sau đó.

Gắn marker `integration` vì file chạy ~58 giây qua TestClient. pytest.ini:2 loại
marker này khỏi lệnh chạy hàng ngày, còn CI vẫn chạy (`-m "not slow"`,
.github/workflows/ci.yml:88) nên vẫn được bảo vệ.

Chạy được khi máy không có Postgres bằng cách nào: auth.py là Postgres-only (§1.3)
nên test dựng một test double ở TẦNG TRUY VẤN (_PgLite). Nó nhận đúng câu SQL mà
auth.py phát ra, chỉ dịch vài cú pháp riêng của Postgres (NOW(), ::uuid,
FOR UPDATE, OFFSET không kèm LIMIT) rồi thi hành trên SQLite in-memory. Toàn bộ
logic auth — băm mật khẩu PBKDF2, băm token, đếm lần sai, tiêu thụ challenge 2FA,
dọn phiên — chạy nguyên vẹn, không bị mock. Chỉ hai thứ ngoài phạm vi auth bị
chặn ở biên: gửi thông báo (notifications) và huy hiệu (achievements).

Không phủ được, và cố ý KHÔNG giả xanh: ngữ nghĩa khoá hàng của Postgres
(FOR UPDATE SKIP LOCKED, DELETE ... RETURNING chạy đua giữa hai request đồng
thời). Nhánh đó cần Postgres thật — test tương ứng skip kèm lý do.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import auth_middleware
import twofactor
from database import Database

pytestmark = pytest.mark.integration

# ──────────────────────────────────────────────────────────────────────────
#  Test double ở tầng truy vấn: chạy SQL của Postgres trên SQLite
# ──────────────────────────────────────────────────────────────────────────

# Mốc thời gian được chuẩn hoá về đúng MỘT định dạng để so sánh chuỗi trong
# SQLite cho ra cùng thứ tự như so sánh timestamptz trong Postgres.
_TS_FMT = "%Y-%m-%dT%H:%M:%S.%f+00:00"
_UUID_DEFAULT = (
    "(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' ||"
    " substr(lower(hex(randomblob(2))),2) || '-a' || substr(lower(hex(randomblob(2))),2)"
    " || '-' || lower(hex(randomblob(6))))"
)
_NOW_DEFAULT = "(strftime('%Y-%m-%dT%H:%M:%f','now') || '000+00:00')"


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(_TS_FMT)


def _now() -> datetime:
    return datetime.now(timezone.utc)


_SCHEMA = f"""
CREATE TABLE users (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    phone TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    display_name TEXT,
    full_name TEXT,
    avatar_url TEXT,
    cover_url TEXT,
    username TEXT,
    bio TEXT DEFAULT '',
    role TEXT DEFAULT 'user',
    is_active INTEGER DEFAULT 1,
    deleted_at TEXT,
    erasure_due_at TEXT,
    consent_at TEXT,
    consent_version TEXT,
    email TEXT,
    contact_info TEXT,
    date_of_birth TEXT,
    login_streak INTEGER DEFAULT 0,
    last_login_date TEXT,
    created_at TEXT DEFAULT {_NOW_DEFAULT},
    updated_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE otp_sessions (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    phone TEXT NOT NULL,
    code TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    expires_at TEXT NOT NULL,
    verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE login_history (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT,
    phone TEXT,
    method TEXT,
    success INTEGER,
    ip TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE consent_log (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    version TEXT,
    ip TEXT,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE pending_2fa (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    ip TEXT,
    user_agent TEXT,
    attempts INTEGER DEFAULT 0,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE trusted_devices (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    device_name TEXT,
    ip TEXT,
    user_agent TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT {_NOW_DEFAULT},
    last_used_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE user_2fa (
    user_id TEXT PRIMARY KEY,
    secret_enc TEXT NOT NULL,
    enabled INTEGER DEFAULT 0,
    created_at TEXT DEFAULT {_NOW_DEFAULT},
    verified_at TEXT
);
CREATE TABLE user_2fa_recovery_codes (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    used_at TEXT
);
CREATE TABLE notifications (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT,
    read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
"""

_INTERVAL_UNITS = {
    "day": "days", "days": "days",
    "hour": "hours", "hours": "hours",
    "minute": "minutes", "minutes": "minutes",
}
_NOW_INTERVAL_RE = re.compile(
    r"NOW\(\)\s*-\s*INTERVAL\s*'(\d+)\s*(\w+)'", re.IGNORECASE
)
_DATE_INTERVAL_RE = re.compile(
    r"CURRENT_DATE\s*-\s*INTERVAL\s*'(\d+)\s*(\w+)'", re.IGNORECASE
)
_CAST_RE = re.compile(r"::(uuid|text|bigint|int|jsonb)", re.IGNORECASE)
_FOR_UPDATE_RE = re.compile(r"\s+FOR\s+UPDATE(\s+SKIP\s+LOCKED)?", re.IGNORECASE)
_ISO_PARAM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")


def _translate(sql: str) -> str:
    """Dịch câu SQL Postgres của auth.py sang phương ngữ SQLite.

    Chỉ đụng tới cú pháp, KHÔNG đụng tới ý nghĩa: NOW()/CURRENT_DATE thay bằng
    hằng thời gian tính ngay lúc chạy (nhờ vậy so sánh chuỗi ISO cho cùng kết
    quả), bỏ ép kiểu ::uuid, bỏ FOR UPDATE, và thêm LIMIT -1 cho OFFSET đứng
    một mình (SQLite bắt buộc, Postgres thì không).
    """
    now = _now()

    def _sub_now_interval(m: re.Match) -> str:
        unit = _INTERVAL_UNITS.get(m.group(2).lower())
        if unit is None:
            raise AssertionError(f"INTERVAL chưa hỗ trợ trong test double: {m.group(0)}")
        return "'" + _ts(now - timedelta(**{unit: int(m.group(1))})) + "'"

    def _sub_date_interval(m: re.Match) -> str:
        unit = _INTERVAL_UNITS.get(m.group(2).lower())
        if unit is None:
            raise AssertionError(f"INTERVAL chưa hỗ trợ trong test double: {m.group(0)}")
        return "'" + (now - timedelta(**{unit: int(m.group(1))})).strftime("%Y-%m-%d") + "'"

    out = _NOW_INTERVAL_RE.sub(_sub_now_interval, sql)
    out = re.sub(r"NOW\(\)", "'" + _ts(now) + "'", out, flags=re.IGNORECASE)
    out = _DATE_INTERVAL_RE.sub(_sub_date_interval, out)
    out = re.sub(r"CURRENT_DATE", "'" + now.strftime("%Y-%m-%d") + "'", out, flags=re.IGNORECASE)
    out = _CAST_RE.sub("", out)
    out = _FOR_UPDATE_RE.sub("", out)
    if re.search(r"\bOFFSET\b", out, re.IGNORECASE) and not re.search(r"\bLIMIT\b", out, re.IGNORECASE):
        out = re.sub(r"\bOFFSET\b", "LIMIT -1 OFFSET", out, flags=re.IGNORECASE)
    return out.replace("%s", "?")


def _norm_params(params):
    """Chuẩn hoá tham số: datetime và chuỗi ISO về đúng một định dạng."""
    if params is None:
        return ()
    out = []
    for p in params:
        if isinstance(p, datetime):
            out.append(_ts(p))
        elif isinstance(p, str) and _ISO_PARAM_RE.match(p):
            try:
                out.append(_ts(datetime.fromisoformat(p)))
            except ValueError:
                out.append(p)
        elif isinstance(p, bool):
            out.append(1 if p else 0)
        else:
            out.append(p)
    return tuple(out)


class _PgLite:
    """DB double cho auth.py — cùng bề mặt với Database (_conn/_execute/_fetchone/...).

    Các phương thức người-dùng (get_user_by_phone/create_user/update_user) mượn
    thẳng từ Database thật để giữ nguyên SQL sản xuất, không viết lại.
    """

    _use_pg = True

    def __init__(self):
        self._sql = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
        self._sql.row_factory = sqlite3.Row
        self._sql.executescript(_SCHEMA)
        self._lock = threading.RLock()

    def initialize(self):
        return None

    @property
    def _ph(self) -> str:
        return "%s"

    @contextmanager
    def _conn(self, *, commit_on_success: bool = True):
        with self._lock:
            yield self._sql

    def _execute(self, conn, sql, params=None):
        return conn.execute(_translate(sql), _norm_params(params))

    def _fetchone(self, conn, sql, params=None):
        return self._execute(conn, sql, params).fetchone()

    def _fetchall(self, conn, sql, params=None):
        return self._execute(conn, sql, params).fetchall()

    def _row_to_dict(self, row):
        return None if row is None else dict(row)

    # SQLite thuần — chỉ dùng để dựng dữ liệu và soi kết quả trong test.
    def raw(self, sql, params=()):
        with self._lock:
            return [dict(r) for r in self._sql.execute(sql, params).fetchall()]

    get_user_by_phone = Database.get_user_by_phone
    get_user_by_id = Database.get_user_by_id
    create_user = Database.create_user
    update_user = Database.update_user


# ──────────────────────────────────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────────────────────────────────

_PASSWORD = "MatKhau123"
# PBKDF2 310k vòng khá đắt — băm một lần rồi dùng lại cho mọi user trong file.
_PASSWORD_HASH = auth._hash_password(_PASSWORD)

_RATE_STORES = (
    "_otp_rate", "_otp_ip_rate", "_login_ip_rate", "_login_phone_fails",
    "_otp_verify_ip_rate", "_otp_verify_phone_rate", "_check_phone_ip_rate",
    "_tfa_verify_ip_rate",
)


def _clear_rate_state():
    for name in _RATE_STORES:
        getattr(auth, name).clear()
    import ratelimit
    ratelimit._reset()


class _Api:
    """Bọc TestClient: mỗi request tự quyết định mang token/CSRF/cookie nào."""

    def __init__(self, client: TestClient, db: _PgLite):
        self.client = client
        self.db = db
        self.notifications: list[dict] = []

    def call(self, method, path, *, token=None, csrf=True, cookies=None, **kw):
        self.client.cookies.clear()
        for name, value in (cookies or {}).items():
            self.client.cookies.set(name, value)
        headers = dict(kw.pop("headers", None) or {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
            if csrf:
                headers["X-CSRF-Token"] = auth_middleware.generate_csrf_token(token)
        return self.client.request(method, path, headers=headers, **kw)

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, **kw):
        return self.call("POST", path, **kw)

    def delete(self, path, **kw):
        return self.call("DELETE", path, **kw)

    # ── dựng dữ liệu ──

    def add_user(self, phone="0901234567", *, with_password=True, **cols):
        user = self.db.create_user(
            phone, password_hash=_PASSWORD_HASH if with_password else None
        )
        if cols:
            sets = ", ".join(f"{k} = ?" for k in cols)
            self.db.raw(
                f"UPDATE users SET {sets} WHERE id = ?", (*cols.values(), user["id"])
            )
            user = self.db.get_user_by_id(user["id"])
        return user

    def add_session(self, user_id, *, expires_in=timedelta(days=30), user_agent="testclient", ip="testclient"):
        token = auth._generate_token()
        self.db.raw(
            "INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, auth._hash_token(token), user_agent, ip, _ts(_now() + expires_in)),
        )
        return token

    def add_otp(self, phone, code, *, expires_in=timedelta(minutes=5), attempts=0):
        self.db.raw(
            "INSERT INTO otp_sessions (phone, code, attempts, expires_at) VALUES (?, ?, ?, ?)",
            (phone, auth._hash_otp(code), attempts, _ts(_now() + expires_in)),
        )

    def enable_2fa(self, user_id):
        secret = twofactor.generate_secret()
        self.db.raw(
            "INSERT INTO user_2fa (user_id, secret_enc, enabled) VALUES (?, ?, 1)",
            (user_id, twofactor.encrypt_secret(secret)),
        )
        return secret

    def add_recovery_code(self, user_id, code):
        self.db.raw(
            "INSERT INTO user_2fa_recovery_codes (user_id, code_hash) VALUES (?, ?)",
            (user_id, twofactor.hash_recovery_code(code)),
        )

    def add_trusted_device(self, user_id, *, expires_in=timedelta(days=90)):
        raw = auth._generate_token()
        self.db.raw(
            "INSERT INTO trusted_devices (user_id, token_hash, device_name, ip, user_agent, expires_at)"
            " VALUES (?, ?, 'Windows', 'testclient', 'testclient', ?)",
            (user_id, auth._hash_token(raw), _ts(_now() + expires_in)),
        )
        return raw

    # ── soi dữ liệu ──

    def sessions_of(self, user_id):
        return self.db.raw("SELECT * FROM user_sessions WHERE user_id = ?", (user_id,))

    def count(self, table, where="1=1", params=()):
        rows = self.db.raw(f"SELECT COUNT(*) AS c FROM {table} WHERE {where}", params)
        return rows[0]["c"]

    def login(self, phone="0901234567", password=_PASSWORD, **kw):
        return self.post("/auth/login", json={"phone": phone, "password": password}, **kw)

    def login_token(self, phone="0901234567", password=_PASSWORD, **kw):
        resp = self.login(phone, password, **kw)
        assert resp.status_code == 200, resp.text
        return resp.json()["token"]


@pytest.fixture
def api(monkeypatch):
    fake = _PgLite()
    monkeypatch.setattr(auth, "db", fake)
    _clear_rate_state()

    app = FastAPI()
    app.include_router(auth.router)
    with TestClient(app) as client:
        wrapper = _Api(client, fake)

        # Hai tác dụng phụ ngoài phạm vi auth bị chặn ở biên (chúng dùng db thật):
        # thông báo bảo mật và huy hiệu. Chặn ở đây để test không đụng DB thật,
        # đồng thời vẫn quan sát được auth có phát cảnh báo hay không.
        def _fake_notification(**kwargs):
            wrapper.notifications.append(kwargs)
            return {"id": "notif-test"}

        monkeypatch.setattr("notifications.create_notification", _fake_notification)
        monkeypatch.setattr("achievements.check_achievements", lambda *a, **k: [])
        yield wrapper
    _clear_rate_state()


@pytest.fixture
def api_2fa(api, monkeypatch):
    """Bật cờ 2FA toàn cục (mặc định TWO_FACTOR_ENABLED=False)."""
    monkeypatch.setattr(auth._cfg, "TWO_FACTOR_ENABLED", True)
    return api


# ──────────────────────────────────────────────────────────────────────────
#  Test double phải trung thực trước đã
# ──────────────────────────────────────────────────────────────────────────

class TestDoubleTuKiem:
    """Nếu double sai thì mọi test dưới đều vô nghĩa — kiểm nó trước."""

    def test_now_va_ts_so_sanh_cung_chieu(self, api):
        user = api.add_user()
        api.add_session(user["id"], expires_in=timedelta(days=1))
        api.add_session(user["id"], expires_in=timedelta(hours=-1))
        con_han = api.db.raw(
            "SELECT COUNT(*) AS c FROM user_sessions WHERE expires_at > ?", (_ts(_now()),)
        )[0]["c"]
        assert con_han == 1, "so sánh chuỗi ISO phải cho cùng thứ tự như timestamptz"

    def test_dich_sql_giu_nguyen_y_nghia(self):
        sql = "SELECT id FROM t WHERE user_id::text = %s AND expires_at > NOW() FOR UPDATE SKIP LOCKED"
        out = _translate(sql)
        assert "::text" not in out
        assert "FOR UPDATE" not in out
        assert "NOW()" not in out
        assert out.count("?") == 1

    def test_offset_khong_limit_duoc_va_limit(self):
        out = _translate("SELECT id FROM t ORDER BY created_at DESC OFFSET %s")
        assert "LIMIT -1 OFFSET ?" in out


# ──────────────────────────────────────────────────────────────────────────
#  Token & phiên
# ──────────────────────────────────────────────────────────────────────────

class TestPhienVaToken:

    def test_khong_token_thi_401(self, api):
        assert api.get("/auth/me").status_code == 401

    def test_token_gia_bi_tu_choi(self, api):
        api.add_user()
        assert api.get("/auth/me", token=auth._generate_token()).status_code == 401

    def test_token_het_han_bi_tu_choi(self, api):
        user = api.add_user()
        token = api.add_session(user["id"], expires_in=timedelta(seconds=-1))
        assert api.get("/auth/me", token=token).status_code == 401

    def test_token_con_han_thi_vao_duoc(self, api):
        user = api.add_user()
        token = api.add_session(user["id"])
        resp = api.get("/auth/me", token=token)
        assert resp.status_code == 200
        assert resp.json()["user"]["id"] == str(user["id"])

    def test_me_khong_tra_ve_mat_khau_hay_so_dien_thoai_day_du(self, api):
        user = api.add_user(phone="0901234567")
        token = api.add_session(user["id"])
        body = api.get("/auth/me", token=token).json()["user"]
        assert body["phone"] == "090****567"
        assert "password_hash" not in body

    def test_token_cua_user_bi_vo_hieu_hoa_bi_tu_choi(self, api):
        user = api.add_user()
        token = api.add_session(user["id"])
        assert api.get("/auth/me", token=token).status_code == 200
        api.db.raw("UPDATE users SET is_active = 0 WHERE id = ?", (user["id"],))
        assert api.get("/auth/me", token=token).status_code == 401, (
            "vô hiệu hoá tài khoản phải chặn ngay cả phiên đang mở"
        )

    def test_token_cua_user_da_xoa_mem_bi_tu_choi(self, api):
        user = api.add_user()
        token = api.add_session(user["id"])
        api.db.raw("UPDATE users SET deleted_at = ? WHERE id = ?", (_ts(_now()), user["id"]))
        assert api.get("/auth/me", token=token).status_code == 401

    def test_token_qua_ngan_hoac_qua_dai_khong_duoc_nhan(self, api):
        user = api.add_user()
        api.add_session(user["id"])
        assert api.get("/auth/me", token="abc").status_code == 401
        assert api.get("/auth/me", token="x" * 200).status_code == 401


class TestDangXuat:

    def test_dang_xuat_vo_hieu_hoa_phien_that_su(self, api):
        user = api.add_user()
        token = api.login_token()
        assert api.get("/auth/me", token=token).status_code == 200

        resp = api.post("/auth/logout", token=token)
        assert resp.status_code == 200

        assert api.get("/auth/me", token=token).status_code == 401
        assert api.count("user_sessions", "user_id = ?", (user["id"],)) == 0

    def test_dang_xuat_chi_giet_phien_hien_tai(self, api):
        user = api.add_user()
        token_a = api.login_token()
        token_b = api.login_token()
        api.post("/auth/logout", token=token_a)
        assert api.get("/auth/me", token=token_a).status_code == 401
        assert api.get("/auth/me", token=token_b).status_code == 200
        assert api.count("user_sessions", "user_id = ?", (user["id"],)) == 1

    def test_dang_xuat_thieu_csrf_bi_chan_va_phien_con_song(self, api):
        api.add_user()
        token = api.login_token()
        resp = api.post("/auth/logout", token=token, csrf=False)
        assert resp.status_code == 403
        assert api.get("/auth/me", token=token).status_code == 200, (
            "request bị CSRF chặn thì không được huỷ phiên"
        )

    def test_dang_xuat_csrf_cua_token_khac_bi_chan(self, api):
        api.add_user()
        api.add_user(phone="0912345678")
        token = api.login_token()
        khac = auth_middleware.generate_csrf_token(auth._generate_token())
        resp = api.post("/auth/logout", token=token, csrf=False, headers={"X-CSRF-Token": khac})
        assert resp.status_code == 403
        assert api.get("/auth/me", token=token).status_code == 200

    def test_dang_xuat_khong_token_van_tra_success(self, api):
        resp = api.post("/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestXoayVaThuHoiPhien:

    def test_refresh_doi_token_va_giet_token_cu(self, api):
        api.add_user()
        cu = api.login_token()
        resp = api.post("/auth/refresh", token=cu)
        assert resp.status_code == 200
        moi = resp.json()["token"]
        assert moi != cu
        assert api.get("/auth/me", token=moi).status_code == 200
        assert api.get("/auth/me", token=cu).status_code == 401

    def test_refresh_bang_token_het_han_bi_tu_choi(self, api):
        user = api.add_user()
        token = api.add_session(user["id"], expires_in=timedelta(seconds=-1))
        assert api.post("/auth/refresh", token=token).status_code == 401

    def test_thu_hoi_phien_cua_nguoi_khac_khong_an_thua(self, api):
        nan_nhan = api.add_user(phone="0901111111")
        ke_tan_cong = api.add_user(phone="0902222222")
        token_nan_nhan = api.add_session(nan_nhan["id"])
        token_ke_tan_cong = api.add_session(ke_tan_cong["id"])
        phien = api.sessions_of(nan_nhan["id"])[0]

        resp = api.delete(f"/auth/sessions/{phien['id']}", token=token_ke_tan_cong)
        assert resp.status_code == 200  # endpoint không lộ việc phiên tồn tại hay không
        assert api.get("/auth/me", token=token_nan_nhan).status_code == 200, (
            "phiên của người khác không được phép bị thu hồi"
        )

    def test_thu_hoi_phien_cua_chinh_minh_thi_token_do_chet(self, api):
        user = api.add_user()
        token_a = api.add_session(user["id"])
        token_b = api.add_session(user["id"])
        phien_b = [
            s for s in api.sessions_of(user["id"]) if s["token"] == auth._hash_token(token_b)
        ][0]
        assert api.delete(f"/auth/sessions/{phien_b['id']}", token=token_a).status_code == 200
        assert api.get("/auth/me", token=token_b).status_code == 401
        assert api.get("/auth/me", token=token_a).status_code == 200

    def test_danh_sach_phien_danh_dau_dung_phien_hien_tai(self, api):
        user = api.add_user()
        token = api.add_session(user["id"], user_agent="Mozilla/5.0 Windows")
        api.add_session(user["id"], user_agent="Mozilla/5.0 iPhone")
        data = api.get("/auth/sessions", token=token).json()["sessions"]
        assert len(data) == 2
        assert [s["is_current"] for s in data].count(True) == 1

    def test_qua_gioi_han_phien_thi_phien_cu_bi_don(self, api):
        api.add_user()
        gioi_han = auth_middleware.MAX_CONCURRENT_SESSIONS
        tokens = [api.login_token() for _ in range(gioi_han + 2)]
        con_lai = api.count("user_sessions")
        assert con_lai == gioi_han, f"phải giữ tối đa {gioi_han} phiên, đang có {con_lai}"
        assert api.get("/auth/me", token=tokens[-1]).status_code == 200
        assert api.get("/auth/me", token=tokens[0]).status_code == 401


class TestDoiMatKhau:

    def test_doi_mat_khau_thu_hoi_cac_phien_khac_giu_phien_hien_tai(self, api):
        api.add_user()
        token_hien_tai = api.login_token()
        token_khac = api.login_token()

        resp = api.post(
            "/auth/set-password",
            token=token_hien_tai,
            json={"password": "MatKhauMoi456", "current_password": _PASSWORD},
        )
        assert resp.status_code == 200, resp.text
        assert api.get("/auth/me", token=token_hien_tai).status_code == 200
        assert api.get("/auth/me", token=token_khac).status_code == 401

    def test_doi_mat_khau_sai_mat_khau_hien_tai_bi_tu_choi(self, api):
        api.add_user()
        token = api.login_token()
        resp = api.post(
            "/auth/set-password",
            token=token,
            json={"password": "MatKhauMoi456", "current_password": "SaiRoi999"},
        )
        assert resp.status_code == 400
        # mật khẩu cũ vẫn đăng nhập được
        _clear_rate_state()
        assert api.login().status_code == 200

    def test_doi_mat_khau_xong_thi_mat_khau_moi_moi_dang_nhap_duoc(self, api):
        api.add_user()
        token = api.login_token()
        api.post(
            "/auth/set-password",
            token=token,
            json={"password": "MatKhauMoi456", "current_password": _PASSWORD},
        )
        _clear_rate_state()
        assert api.login(password=_PASSWORD).status_code == 401
        _clear_rate_state()
        assert api.login(password="MatKhauMoi456").status_code == 200

    def test_doi_mat_khau_khong_dang_nhap_thi_401(self, api):
        resp = api.post("/auth/set-password", json={"password": "MatKhauMoi456"})
        assert resp.status_code == 401


class TestQuenMatKhauQuaOTP:

    def test_dat_lai_mat_khau_thu_hoi_toan_bo_phien(self, api):
        user = api.add_user()
        token_cu = api.add_session(user["id"])
        api.add_otp("0901234567", "123456")

        resp = api.post(
            "/auth/reset-password-otp",
            json={"phone": "0901234567", "code": "123456", "new_password": "MatKhauMoi456"},
        )
        assert resp.status_code == 200, resp.text
        assert api.get("/auth/me", token=token_cu).status_code == 401
        assert api.count("user_sessions", "user_id = ?", (user["id"],)) == 0

        assert api.login(password="MatKhauMoi456").status_code == 200
        _clear_rate_state()
        assert api.login(password=_PASSWORD).status_code == 401

    def test_otp_sai_thi_mat_khau_va_phien_giu_nguyen(self, api):
        user = api.add_user()
        token_cu = api.add_session(user["id"])
        api.add_otp("0901234567", "123456")

        resp = api.post(
            "/auth/reset-password-otp",
            json={"phone": "0901234567", "code": "999999", "new_password": "MatKhauMoi456"},
        )
        assert resp.status_code == 400
        assert api.get("/auth/me", token=token_cu).status_code == 200
        assert api.login().status_code == 200, "mật khẩu cũ phải còn nguyên"

    def test_dat_lai_mat_khau_huy_luon_thu_thach_2fa_dang_treo(self, api):
        """Nửa-đăng-nhập không được sống sót qua lần đổi mật khẩu."""
        user = api.add_user()
        api.db.raw(
            "INSERT INTO pending_2fa (user_id, token_hash, ip, user_agent, expires_at)"
            " VALUES (?, ?, 'testclient', 'testclient', ?)",
            (user["id"], auth._hash_token(auth._generate_token()), _ts(_now() + timedelta(minutes=5))),
        )
        api.add_otp("0901234567", "123456")
        resp = api.post(
            "/auth/reset-password-otp",
            json={"phone": "0901234567", "code": "123456", "new_password": "MatKhauMoi456"},
        )
        assert resp.status_code == 200
        assert api.count("pending_2fa") == 0

    def test_mat_khau_moi_yeu_bi_tu_choi(self, api):
        api.add_user()
        api.add_otp("0901234567", "123456")
        resp = api.post(
            "/auth/reset-password-otp",
            json={"phone": "0901234567", "code": "123456", "new_password": "abc"},
        )
        assert resp.status_code == 422
        assert api.login().status_code == 200, "mật khẩu cũ vẫn phải dùng được"


# ──────────────────────────────────────────────────────────────────────────
#  Đăng nhập sai nhiều lần
# ──────────────────────────────────────────────────────────────────────────

class TestChongDoMatKhau:

    def test_sai_mat_khau_tra_401_va_khong_tao_phien(self, api):
        user = api.add_user()
        resp = api.login(password="SaiBet999")
        assert resp.status_code == 401
        assert api.count("user_sessions", "user_id = ?", (user["id"],)) == 0

    def test_so_dien_thoai_la_va_mat_khau_sai_tra_cung_thong_diep(self, api):
        api.add_user(phone="0901111111")
        sai_mat_khau = api.login(phone="0901111111", password="SaiBet999")
        so_la = api.login(phone="0909999999", password="SaiBet999")
        assert sai_mat_khau.status_code == so_la.status_code == 401
        assert sai_mat_khau.json()["detail"] == so_la.json()["detail"], (
            "hai thông điệp khác nhau là lộ số nào đã đăng ký"
        )

    def test_sai_qua_nguong_thi_khoa_theo_so_dien_thoai(self, api, monkeypatch):
        # Nới trần theo IP để cô lập đúng bộ đếm theo số điện thoại.
        monkeypatch.setattr(auth, "LOGIN_IP_LIMIT", 100)
        api.add_user()
        for _ in range(auth.LOGIN_PHONE_LIMIT):
            assert api.login(password="SaiBet999").status_code == 401
        khoa = api.login(password="SaiBet999")
        assert khoa.status_code == 429
        assert "tạm khoá" in khoa.json()["detail"].lower()

    def test_dang_khoa_thi_mat_khau_dung_cung_khong_vao_duoc(self, api, monkeypatch):
        monkeypatch.setattr(auth, "LOGIN_IP_LIMIT", 100)
        user = api.add_user()
        for _ in range(auth.LOGIN_PHONE_LIMIT):
            api.login(password="SaiBet999")
        resp = api.login(password=_PASSWORD)
        assert resp.status_code == 429, "khoá phải chặn trước cả khi kiểm mật khẩu"
        assert api.count("user_sessions", "user_id = ?", (user["id"],)) == 0

    def test_khoa_theo_so_khong_lan_sang_so_khac(self, api, monkeypatch):
        monkeypatch.setattr(auth, "LOGIN_IP_LIMIT", 100)
        api.add_user(phone="0901111111")
        api.add_user(phone="0902222222")
        for _ in range(auth.LOGIN_PHONE_LIMIT):
            api.login(phone="0901111111", password="SaiBet999")
        assert api.login(phone="0901111111", password=_PASSWORD).status_code == 429
        assert api.login(phone="0902222222", password=_PASSWORD).status_code == 200

    def test_dang_nhap_dung_khong_xoa_het_bo_dem_sai(self, api, monkeypatch):
        """Ghi lại hành vi hiện tại — ĐÂY LÀ KHIẾM KHUYẾT, không phải yêu cầu.

        login_password có HAI bộ đếm sai theo số điện thoại: một bộ cục bộ
        (_login_phone_fails) và một bộ chung qua ratelimit.check_rate. Đăng nhập
        đúng chỉ xoá bộ cục bộ (agent/auth.py:934); bộ chung vẫn giữ nguyên các
        lần sai cũ suốt LOGIN_PHONE_WINDOW. Hệ quả quan sát được: sau khi vào
        thành công, người dùng chỉ còn ĐÚNG MỘT lần nhập sai nữa là bị khoá —
        gõ nhầm mật khẩu ở lần đổi mật khẩu kế tiếp là mất quyền vào trong 15 phút.

        Test này tồn tại để việc sửa khiếm khuyết đó là một thay đổi CÓ CHỦ Ý:
        ai xoá cả hai bộ đếm khi đăng nhập đúng sẽ thấy test này đỏ và phải sửa
        cả kỳ vọng ở đây. Đừng đọc nó như "hành vi mong muốn".
        """
        monkeypatch.setattr(auth, "LOGIN_IP_LIMIT", 100)
        api.add_user()
        for _ in range(auth.LOGIN_PHONE_LIMIT - 1):
            assert api.login(password="SaiBet999").status_code == 401
        assert api.login().status_code == 200

        assert api.login(password="SaiBet999").status_code == 401
        assert api.login(password="SaiBet999").status_code == 429, (
            "bộ đếm chung không được reset khi đăng nhập đúng — đây là hành vi thật"
        )

    def test_dang_nhap_dung_go_khoa_cuc_bo_ngay_lap_tuc(self, api, monkeypatch):
        """Bộ đếm cục bộ (chặn TRƯỚC khi tra DB) thì đúng là được xoá khi vào được.

        Soi thẳng `auth._login_phone_fails` thay vì đọc thông điệp lỗi. Bản đầu của
        test này phân biệt hai bộ đếm bằng việc một câu viết "tạm khoá" có dấu còn
        câu kia không — tức dựa vào một bất nhất chính tả tình cờ trong nguồn. Ai sửa
        chính tả là test vỡ dù hành vi vẫn đúng.
        """
        monkeypatch.setattr(auth, "LOGIN_IP_LIMIT", 100)
        api.add_user()
        for _ in range(auth.LOGIN_PHONE_LIMIT):
            api.login(password="SaiBet999")

        chan_cuc_bo = api.login(password="SaiBet999")
        assert chan_cuc_bo.status_code == 429
        assert auth._login_phone_fails, "bộ đếm cục bộ phải có dấu vết khi đang chặn"

        _clear_rate_state()
        for _ in range(auth.LOGIN_PHONE_LIMIT - 1):
            api.login(password="SaiBet999")
        assert auth._login_phone_fails, "đang tích luỹ lần sai thì bộ đếm phải khác rỗng"

        assert api.login().status_code == 200
        assert not any(auth._login_phone_fails.values()), (
            "sau khi đăng nhập đúng, bộ đếm cục bộ theo số điện thoại phải được xoá"
        )

    def test_qua_nhieu_lan_tu_mot_ip_thi_chan_ca_so_khac(self, api):
        api.add_user(phone="0901111111")
        for i in range(auth.LOGIN_IP_LIMIT):
            api.login(phone=f"09011111{i:02d}", password="SaiBet999")
        resp = api.login(phone="0901111111", password=_PASSWORD)
        assert resp.status_code == 429

    def test_moi_lan_sai_deu_duoc_ghi_lich_su(self, api, monkeypatch):
        monkeypatch.setattr(auth, "LOGIN_IP_LIMIT", 100)
        user = api.add_user()
        api.login(password="SaiBet999")
        api.login(password="SaiBet999")
        that_bai = api.count("login_history", "success = 0 AND user_id = ?", (user["id"],))
        assert that_bai == 2


class TestTaiKhoanBiVoHieuHoa:

    def test_tai_khoan_vo_hieu_hoa_mat_khau_dung_tra_403(self, api):
        api.add_user(is_active=0)
        resp = api.login()
        assert resp.status_code == 403
        assert api.count("user_sessions") == 0

    def test_tai_khoan_vo_hieu_hoa_mat_khau_sai_van_tra_401(self, api):
        """403 chỉ được lộ SAU khi mật khẩu đúng, nếu không là lộ trạng thái tài khoản."""
        api.add_user(is_active=0)
        assert api.login(password="SaiBet999").status_code == 401

    def test_tai_khoan_chua_dat_mat_khau_khong_dang_nhap_duoc(self, api):
        api.add_user(with_password=False)
        assert api.login(password="BatKyGi123").status_code == 401


# ──────────────────────────────────────────────────────────────────────────
#  OTP
# ──────────────────────────────────────────────────────────────────────────

class TestOTP:

    def test_otp_dung_tao_tai_khoan_va_phien(self, api):
        api.add_otp("0901234567", "123456")
        resp = api.post(
            "/auth/verify-otp",
            json={"phone": "0901234567", "code": "123456", "consent": True},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["token"]
        assert api.get("/auth/me", token=token).status_code == 200
        assert api.count("users", "phone = ?", ("0901234567",)) == 1

    def test_otp_sai_khong_tao_tai_khoan_va_tang_so_lan_thu(self, api):
        api.add_otp("0901234567", "123456")
        resp = api.post(
            "/auth/verify-otp",
            json={"phone": "0901234567", "code": "999999", "consent": True},
        )
        assert resp.status_code == 400
        assert api.count("users") == 0
        assert api.db.raw("SELECT attempts FROM otp_sessions")[0]["attempts"] == 1

    def test_otp_het_han_bi_tu_choi(self, api):
        api.add_otp("0901234567", "123456", expires_in=timedelta(minutes=-1))
        resp = api.post(
            "/auth/verify-otp",
            json={"phone": "0901234567", "code": "123456", "consent": True},
        )
        assert resp.status_code == 400
        assert "hết hạn" in resp.json()["detail"].lower()
        assert api.count("users") == 0

    def test_otp_chi_dung_duoc_mot_lan(self, api):
        api.add_otp("0901234567", "123456")
        payload = {"phone": "0901234567", "code": "123456", "consent": True}
        assert api.post("/auth/verify-otp", json=payload).status_code == 200
        lai = api.post("/auth/verify-otp", json=payload)
        assert lai.status_code == 400, "OTP đã dùng không được dùng lại"

    def test_otp_khong_dong_y_dieu_khoan_thi_khong_tao_tai_khoan(self, api):
        api.add_otp("0901234567", "123456")
        resp = api.post(
            "/auth/verify-otp",
            json={"phone": "0901234567", "code": "123456", "consent": False},
        )
        assert resp.status_code == 400
        assert api.count("users") == 0

    def test_otp_sai_qua_nam_lan_thi_khoa_ma(self, api, monkeypatch):
        # Nới trần tần suất để chạm được đúng bộ đếm attempts của chính mã OTP.
        monkeypatch.setattr(auth, "OTP_VERIFY_PHONE_LIMIT", 100)
        monkeypatch.setattr(auth, "OTP_VERIFY_IP_LIMIT", 100)
        api.add_otp("0901234567", "123456")
        sai = {"phone": "0901234567", "code": "999999", "consent": True}
        for _ in range(auth.OTP_MAX_ATTEMPTS):
            assert api.post("/auth/verify-otp", json=sai).status_code == 400
        het = api.post("/auth/verify-otp", json=sai)
        assert het.status_code == 429
        # mã đúng cũng vô dụng sau khi hết lượt
        dung = api.post(
            "/auth/verify-otp",
            json={"phone": "0901234567", "code": "123456", "consent": True},
        )
        assert dung.status_code == 429
        assert api.count("users") == 0

    def test_otp_nhap_qua_nhanh_bi_chan_theo_so(self, api):
        api.add_otp("0901234567", "123456")
        sai = {"phone": "0901234567", "code": "999999", "consent": True}
        for _ in range(auth.OTP_VERIFY_PHONE_LIMIT):
            api.post("/auth/verify-otp", json=sai)
        assert api.post("/auth/verify-otp", json=sai).status_code == 429

    def test_gui_otp_lai_ngay_bi_chan(self, api):
        assert api.post("/auth/request-otp", json={"phone": "0901234567"}).status_code == 200
        lai = api.post("/auth/request-otp", json={"phone": "0901234567"})
        assert lai.status_code == 429

    def test_request_otp_khong_bao_gio_tra_ma_ra_response(self, api):
        resp = api.post("/auth/request-otp", json={"phone": "0901234567"})
        assert resp.status_code == 200
        ma_that = api.db.raw("SELECT code FROM otp_sessions")[0]["code"]
        assert ma_that not in resp.text
        assert "code" not in resp.json()

    def test_so_dien_thoai_khong_hop_le_bi_tu_choi(self, api):
        resp = api.post("/auth/request-otp", json={"phone": "12345"})
        assert resp.status_code == 422
        assert api.count("otp_sessions") == 0


# ──────────────────────────────────────────────────────────────────────────
#  2FA
# ──────────────────────────────────────────────────────────────────────────

class TestHaiLopBaoVeKhiDangNhap:

    def test_bat_2fa_thi_login_chi_ra_challenge_chua_co_phien(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        body = api_2fa.login().json()
        assert body["two_factor_required"] is True
        assert "token" not in body
        assert api_2fa.count("user_sessions") == 0, "chưa qua 2FA thì không được có phiên"

    def test_co_challenge_nhung_ma_sai_thi_khong_co_phien(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        challenge = api_2fa.login().json()["challenge_id"]
        resp = api_2fa.post(
            "/auth/2fa/verify", json={"challenge_id": challenge, "code": "000000"}
        )
        assert resp.status_code == 400
        assert api_2fa.count("user_sessions") == 0

    def test_ma_dung_thi_tao_phien_dung_nguoi(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        challenge = api_2fa.login().json()["challenge_id"]
        resp = api_2fa.post(
            "/auth/2fa/verify",
            json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now()},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["token"]
        assert api_2fa.get("/auth/me", token=token).json()["user"]["id"] == str(user["id"])

    def test_challenge_chi_tieu_thu_duoc_mot_lan(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        challenge = api_2fa.login().json()["challenge_id"]
        payload = {"challenge_id": challenge, "code": pyotp.TOTP(secret).now()}
        assert api_2fa.post("/auth/2fa/verify", json=payload).status_code == 200
        lai = api_2fa.post("/auth/2fa/verify", json=payload)
        assert lai.status_code == 400, "challenge dùng-một-lần không được tái sử dụng"
        assert api_2fa.count("user_sessions") == 1

    def test_challenge_gia_bi_tu_choi(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        resp = api_2fa.post(
            "/auth/2fa/verify",
            json={"challenge_id": auth._generate_token(), "code": pyotp.TOTP(secret).now()},
        )
        assert resp.status_code == 400
        assert api_2fa.count("user_sessions") == 0

    def test_challenge_het_han_bi_tu_choi_va_bi_don(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        raw = auth._generate_token()
        api_2fa.db.raw(
            "INSERT INTO pending_2fa (user_id, token_hash, ip, user_agent, expires_at)"
            " VALUES (?, ?, 'testclient', 'testclient', ?)",
            (user["id"], auth._hash_token(raw), _ts(_now() - timedelta(minutes=1))),
        )
        resp = api_2fa.post(
            "/auth/2fa/verify", json={"challenge_id": raw, "code": pyotp.TOTP(secret).now()}
        )
        assert resp.status_code == 400
        assert api_2fa.count("pending_2fa") == 0
        assert api_2fa.count("user_sessions") == 0

    def test_thu_sai_qua_nguong_thi_challenge_bi_huy(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        challenge = api_2fa.login().json()["challenge_id"]
        sai = {"challenge_id": challenge, "code": "000000"}
        for _ in range(auth.OTP_MAX_ATTEMPTS):
            assert api_2fa.post("/auth/2fa/verify", json=sai).status_code == 400
        het = api_2fa.post("/auth/2fa/verify", json=sai)
        assert het.status_code == 429
        assert api_2fa.count("pending_2fa") == 0
        # mã đúng cũng không cứu được challenge đã bị huỷ
        dung = api_2fa.post(
            "/auth/2fa/verify",
            json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now()},
        )
        assert dung.status_code == 400
        assert api_2fa.count("user_sessions") == 0

    def test_ma_khoi_phuc_dung_duoc_dung_mot_lan(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        api_2fa.add_recovery_code(user["id"], "MA-KHOI-PHUC-1")

        challenge = api_2fa.login().json()["challenge_id"]
        ok = api_2fa.post(
            "/auth/2fa/verify",
            json={"challenge_id": challenge, "code": "MA-KHOI-PHUC-1", "recovery": True},
        )
        assert ok.status_code == 200, ok.text
        assert api_2fa.count("user_2fa_recovery_codes", "used_at IS NOT NULL") == 1

        _clear_rate_state()
        challenge2 = api_2fa.login().json()["challenge_id"]
        lai = api_2fa.post(
            "/auth/2fa/verify",
            json={"challenge_id": challenge2, "code": "MA-KHOI-PHUC-1", "recovery": True},
        )
        assert lai.status_code == 400, "mã khôi phục đã dùng không được dùng lại"

    def test_ma_totp_khong_dung_duoc_o_luong_recovery(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        challenge = api_2fa.login().json()["challenge_id"]
        resp = api_2fa.post(
            "/auth/2fa/verify",
            json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now(), "recovery": True},
        )
        assert resp.status_code == 400

    def test_co_gia_tri_2fa_nhung_co_toan_cuc_tat_thi_khong_chan(self, api):
        """TWO_FACTOR_ENABLED=False là kill-switch: có hàng user_2fa cũng bỏ qua."""
        user = api.add_user()
        api.enable_2fa(user["id"])
        body = api.login().json()
        assert "two_factor_required" not in body
        assert api.count("user_sessions") == 1

    def test_2fa_chua_bat_thi_login_binh_thuong(self, api_2fa):
        user = api_2fa.add_user()
        secret = twofactor.generate_secret()
        api_2fa.db.raw(
            "INSERT INTO user_2fa (user_id, secret_enc, enabled) VALUES (?, ?, 0)",
            (user["id"], twofactor.encrypt_secret(secret)),
        )
        assert api_2fa.login().status_code == 200
        assert api_2fa.count("user_sessions") == 1


class TestBatTatHaiLop:

    def test_tat_2fa_bang_ma_sai_bi_tu_choi_va_van_con_bat(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        token = api_2fa.add_session(user["id"])
        resp = api_2fa.post("/auth/2fa/disable", token=token, json={"code": "000000"})
        assert resp.status_code == 400
        assert api_2fa.get("/auth/2fa/status", token=token).json()["enabled"] is True

    def test_tat_2fa_bang_ma_dung_xoa_ca_thiet_bi_tin_cay(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        api_2fa.add_trusted_device(user["id"])
        token = api_2fa.add_session(user["id"])

        resp = api_2fa.post(
            "/auth/2fa/disable", token=token, json={"code": pyotp.TOTP(secret).now()}
        )
        assert resp.status_code == 200, resp.text
        assert api_2fa.get("/auth/2fa/status", token=token).json()["enabled"] is False
        assert api_2fa.count("trusted_devices") == 0
        assert api_2fa.count("user_2fa") == 0

    def test_tat_2fa_can_dang_nhap(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        assert api_2fa.post("/auth/2fa/disable", json={"code": "000000"}).status_code == 401

    def test_tat_2fa_thieu_csrf_bi_chan(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        token = api_2fa.add_session(user["id"])
        resp = api_2fa.post(
            "/auth/2fa/disable", token=token, csrf=False, json={"code": pyotp.TOTP(secret).now()}
        )
        assert resp.status_code == 403
        assert api_2fa.count("user_2fa", "enabled = 1") == 1

    def test_bat_2fa_can_ma_dung_va_tra_ma_khoi_phuc(self, api_2fa):
        user = api_2fa.add_user()
        token = api_2fa.add_session(user["id"])
        setup = api_2fa.post("/auth/2fa/setup", token=token)
        assert setup.status_code == 200, setup.text
        secret = setup.json()["secret"]
        assert api_2fa.count("user_2fa", "enabled = 1") == 0, "setup chưa được bật 2FA"

        sai = api_2fa.post("/auth/2fa/verify-setup", token=token, json={"code": "000000"})
        assert sai.status_code == 400
        assert api_2fa.count("user_2fa", "enabled = 1") == 0

        ok = api_2fa.post(
            "/auth/2fa/verify-setup", token=token, json={"code": pyotp.TOTP(secret).now()}
        )
        assert ok.status_code == 200, ok.text
        assert len(ok.json()["recovery_codes"]) == 8
        assert api_2fa.count("user_2fa", "enabled = 1") == 1

    def test_co_toan_cuc_tat_thi_khong_cho_bat_2fa(self, api):
        user = api.add_user()
        token = api.add_session(user["id"])
        assert api.post("/auth/2fa/setup", token=token).status_code == 403


class TestThietBiTinCay:

    def test_nho_thiet_bi_thi_lan_sau_khong_hoi_2fa(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        challenge = api_2fa.login().json()["challenge_id"]
        resp = api_2fa.post(
            "/auth/2fa/verify",
            json={
                "challenge_id": challenge,
                "code": pyotp.TOTP(secret).now(),
                "remember_device": True,
            },
        )
        assert resp.status_code == 200
        cookie = resp.cookies.get(auth.TRUSTED_DEVICE_COOKIE_NAME)
        assert cookie, "phải phát cookie thiết bị tin cậy"

        _clear_rate_state()
        lai = api_2fa.login(cookies={auth.TRUSTED_DEVICE_COOKIE_NAME: cookie})
        assert lai.status_code == 200
        assert "token" in lai.json(), "thiết bị tin cậy phải vào thẳng, không challenge"

    def test_khong_nho_thiet_bi_thi_khong_co_cookie(self, api_2fa):
        user = api_2fa.add_user()
        secret = api_2fa.enable_2fa(user["id"])
        challenge = api_2fa.login().json()["challenge_id"]
        resp = api_2fa.post(
            "/auth/2fa/verify",
            json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now()},
        )
        assert resp.status_code == 200
        assert resp.cookies.get(auth.TRUSTED_DEVICE_COOKIE_NAME) is None
        assert api_2fa.count("trusted_devices") == 0

    def test_cookie_thiet_bi_gia_van_bi_hoi_2fa(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        api_2fa.add_trusted_device(user["id"])  # thiết bị thật của user, cookie thì giả
        body = api_2fa.login(
            cookies={auth.TRUSTED_DEVICE_COOKIE_NAME: auth._generate_token()}
        ).json()
        assert body.get("two_factor_required") is True

    def test_thiet_bi_tin_cay_het_han_van_bi_hoi_2fa(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        cookie = api_2fa.add_trusted_device(user["id"], expires_in=timedelta(days=-1))
        body = api_2fa.login(cookies={auth.TRUSTED_DEVICE_COOKIE_NAME: cookie}).json()
        assert body.get("two_factor_required") is True

    def test_thiet_bi_cua_nguoi_khac_khong_dung_duoc(self, api_2fa):
        nguoi_a = api_2fa.add_user(phone="0901111111")
        nguoi_b = api_2fa.add_user(phone="0902222222")
        api_2fa.enable_2fa(nguoi_a["id"])
        api_2fa.enable_2fa(nguoi_b["id"])
        cookie_b = api_2fa.add_trusted_device(nguoi_b["id"])
        body = api_2fa.login(
            phone="0901111111", cookies={auth.TRUSTED_DEVICE_COOKIE_NAME: cookie_b}
        ).json()
        assert body.get("two_factor_required") is True, (
            "cookie thiết bị của người khác không được bỏ qua 2FA"
        )

    def test_xoa_thiet_bi_cua_minh_thi_lan_sau_bi_hoi_lai(self, api_2fa):
        user = api_2fa.add_user()
        api_2fa.enable_2fa(user["id"])
        cookie = api_2fa.add_trusted_device(user["id"])
        token = api_2fa.add_session(user["id"])

        thiet_bi = api_2fa.get("/auth/trusted-devices", token=token).json()["devices"]
        assert len(thiet_bi) == 1
        assert api_2fa.delete(
            f"/auth/trusted-devices/{thiet_bi[0]['id']}", token=token
        ).status_code == 200
        body = api_2fa.login(cookies={auth.TRUSTED_DEVICE_COOKIE_NAME: cookie}).json()
        assert body.get("two_factor_required") is True

    def test_khong_xoa_duoc_thiet_bi_cua_nguoi_khac(self, api_2fa):
        nguoi_a = api_2fa.add_user(phone="0901111111")
        nguoi_b = api_2fa.add_user(phone="0902222222")
        api_2fa.add_trusted_device(nguoi_b["id"])
        token_a = api_2fa.add_session(nguoi_a["id"])
        id_b = api_2fa.db.raw("SELECT id FROM trusted_devices")[0]["id"]

        assert api_2fa.delete(f"/auth/trusted-devices/{id_b}", token=token_a).status_code == 200
        assert api_2fa.count("trusted_devices", "id = ?", (id_b,)) == 1, (
            "thiết bị của người khác không được phép bị xoá"
        )

    def test_danh_sach_thiet_bi_khong_lo_token_va_che_ip(self, api_2fa):
        user = api_2fa.add_user()
        raw = api_2fa.add_trusted_device(user["id"])
        token = api_2fa.add_session(user["id"])
        resp = api_2fa.get("/auth/trusted-devices", token=token)
        assert resp.status_code == 200
        thiet_bi = resp.json()["devices"][0]
        assert "token_hash" not in resp.text
        assert raw not in resp.text and auth._hash_token(raw) not in resp.text
        assert thiet_bi["device_name"] == "Windows"
        assert thiet_bi["ip"] == auth._mask_ip("testclient") != "testclient"


# ──────────────────────────────────────────────────────────────────────────
#  Cảnh báo đăng nhập lạ + dọn dữ liệu hết hạn
# ──────────────────────────────────────────────────────────────────────────

class TestCanhBaoVaDonDep:

    def test_dang_nhap_lan_dau_tu_thiet_bi_la_thi_co_canh_bao(self, api):
        api.add_user()
        api.login_token()
        loai = [n.get("notif_type") for n in api.notifications]
        assert "security_alert" in loai

    def test_dang_nhap_lai_cung_thiet_bi_thi_khong_canh_bao_nua(self, api):
        api.add_user()
        api.login_token()
        api.notifications.clear()
        api.login_token()
        assert api.notifications == [], "cùng IP/UA đã biết thì không báo động nữa"

    def test_don_du_lieu_het_han_xoa_dung_thu(self, api):
        user = api.add_user()
        con_han = api.add_session(user["id"], expires_in=timedelta(days=1))
        api.add_session(user["id"], expires_in=timedelta(days=-1))
        api.add_otp("0901234567", "111111", expires_in=timedelta(minutes=-1))
        api.add_otp("0901234567", "222222", expires_in=timedelta(minutes=5))
        api.add_trusted_device(user["id"], expires_in=timedelta(days=-1))

        ket_qua = auth.cleanup_expired_data()
        assert ket_qua.get("error") is None, ket_qua
        assert ket_qua["expired_sessions"] == 1
        assert ket_qua["expired_otps"] == 1
        assert ket_qua["expired_trusted_devices"] == 1
        assert api.get("/auth/me", token=con_han).status_code == 200


# ──────────────────────────────────────────────────────────────────────────
#  Ràng buộc hạ tầng của chính router auth
# ──────────────────────────────────────────────────────────────────────────

class TestRouterAuth:

    def test_khong_route_nao_bi_khai_bao_hai_lan(self):
        """Bài học 2026-08: route khai báo hai lần trong app đã merge thì bản sau
        đè bản trước và không test nào bắt được, vì test chỉ soi router của module
        mình. Kiểm ngay trên app đã include."""
        app = FastAPI()
        app.include_router(auth.router)
        cap = []
        for route in app.routes:
            for method in getattr(route, "methods", None) or set():
                cap.append((method, route.path))
        trung = {c for c in cap if cap.count(c) > 1}
        assert not trung, f"route auth bị khai báo trùng: {sorted(trung)}"

    def test_khong_co_postgres_thi_tra_503_chu_khong_500(self):
        """§1.3: auth là Postgres-only. Trên SQLite phải là 503 nói rõ lý do."""
        import database

        if database.db._use_pg:
            pytest.skip("máy này đang chạy Postgres thật — nhánh 503 không áp dụng")
        app = FastAPI()
        app.include_router(auth.router)
        with TestClient(app) as client:
            resp = client.post(
                "/auth/login", json={"phone": "0901234567", "password": _PASSWORD}
            )
        assert resp.status_code == 503
        assert "Postgres" in resp.json()["detail"]


# ── Hai nhánh chỉ Postgres thật mới kiểm được ────────────────────────────────
#
# Ghi ở đây dưới dạng CHÚ THÍCH, không phải test skip vô điều kiện. Bản đầu viết
# chúng thành hai test gọi pytest.skip() không điều kiện — chúng không bao giờ
# chạy kể cả trên máy có Postgres, nhưng vẫn đếm vào tổng số test và làm số liệu
# "đã phủ" đẹp hơn thực tế.
#
# 1. Đua DELETE ... RETURNING trong auth.twofa_verify: hai request cùng một
#    challenge thì chỉ một cái được thắng. SQLite in-memory của test double tuần
#    tự hoá mọi truy cập nên không tái hiện được cuộc đua.
# 2. FOR UPDATE SKIP LOCKED trong auth._consume_verified_otp: SQLite không có
#    tương đương, test double bỏ mệnh đề này khi dịch SQL.
#
# Muốn phủ thật thì chạy trên job test-pg trong CI (.github/workflows/ci.yml),
# nơi có Postgres thật, và viết bằng hai connection song song.
