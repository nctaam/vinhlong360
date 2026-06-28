"""
vinhlong360 — Authentication (OTP + Password).

Endpoints:
  POST /auth/request-otp   — gửi OTP qua SMS (eSMS.vn)
  POST /auth/verify-otp    — xác minh OTP, tạo session
  POST /auth/set-password   — đặt/đổi mật khẩu (cần đăng nhập)
  POST /auth/login          — đăng nhập bằng SĐT + mật khẩu
  POST /auth/check-phone    — kiểm tra SĐT đã có mật khẩu chưa
  POST /auth/logout         — hủy session
  GET  /auth/me             — thông tin user hiện tại

Tuân thủ NĐ 147/2024: xác thực SĐT VN trước khi cho đăng bài/bình luận.
"""
import html as _html

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("auth")

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from database import db


async def _require_csrf_lazy(request: Request) -> None:
    from auth_middleware import require_csrf
    await require_csrf(request)


async def _check_session_binding_safe(request, user):
    try:
        from auth_middleware import check_session_binding
        return await check_session_binding(request, user)
    except Exception:
        return True


def _require_pg():
    if not db._use_pg:
        raise HTTPException(503, detail="Tính năng UGC/auth cần Postgres. Local dev: docker compose up postgres.")


router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(_require_pg)])

# ── Config ──

OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RATE_LIMIT_SECONDS = 60
SESSION_EXPIRE_DAYS = 30

ESMS_API_KEY = os.getenv("ESMS_API_KEY", "")
ESMS_SECRET = os.getenv("ESMS_SECRET", "")
ESMS_BRANDNAME = os.getenv("ESMS_BRANDNAME", "VinhLong360")

VN_PHONE_RE = re.compile(r"^(0|\+84)(3|5|7|8|9)\d{8}$")

_otp_rate: dict[str, float] = {}

from config import settings as _cfg

OTP_IP_LIMIT = _cfg.OTP_IP_LIMIT
OTP_IP_WINDOW = _cfg.OTP_IP_WINDOW
_otp_ip_rate: dict[str, list[float]] = {}

LOGIN_IP_LIMIT = _cfg.LOGIN_IP_LIMIT
LOGIN_IP_WINDOW = _cfg.LOGIN_IP_WINDOW
_login_ip_rate: dict[str, list[float]] = {}

LOGIN_PHONE_LIMIT = _cfg.LOGIN_PHONE_LIMIT
LOGIN_PHONE_WINDOW = _cfg.LOGIN_PHONE_WINDOW
_login_phone_fails: dict[str, list[float]] = {}

OTP_VERIFY_IP_LIMIT = 15
OTP_VERIFY_IP_WINDOW = 300
_otp_verify_ip_rate: dict[str, list[float]] = {}

ACCOUNT_DELETE_GRACE_DAYS = 30

_RATE_MAX_KEYS = 2000

def _gc_rate_dict(d: dict, window: float) -> None:
    if len(d) <= _RATE_MAX_KEYS:
        return
    now = time.time()
    stale = [k for k, v in d.items()
             if not v or now - (max(v) if isinstance(v, list) else v) > window]
    for k in stale:
        del d[k]


# ── Models ──

class OTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        if not VN_PHONE_RE.match(v):
            raise ValueError("Số điện thoại VN không hợp lệ")
        return v


CONSENT_VERSION = "1.0"


class OTPVerify(BaseModel):
    phone: str
    code: str
    consent: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        return v


class PasswordLogin(BaseModel):
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        return v


class SetPassword(BaseModel):
    password: str = Field(..., max_length=128)
    current_password: str | None = Field(None, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu phải từ 8 ký tự trở lên")
        if not any(c.isdigit() for c in v):
            raise ValueError("Mật khẩu cần có ít nhất 1 chữ số")
        if not any(c.isalpha() for c in v):
            raise ValueError("Mật khẩu cần có ít nhất 1 chữ cái")
        return v


class CheckPhone(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        return v


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    username: str | None = None


# ── Helpers ──

def _normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+84"):
        phone = "0" + phone[3:]
    return phone


def _generate_otp() -> str:
    return "".join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    """P0-6: lưu + tra cứu session token bằng SHA-256, KHÔNG plaintext.
    Token entropy cao (token_urlsafe 48) nên SHA-256 đủ (không cần PBKDF2 như mật khẩu).
    Lộ DB ⇒ chỉ thấy hash, không dùng lại được."""
    return hashlib.sha256(token.encode()).hexdigest()


_PBKDF2_ITERATIONS = 310_000

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return base64.b64encode(salt + key).decode()


def _verify_password(password: str, stored: str) -> bool:
    decoded = base64.b64decode(stored)
    salt, stored_key = decoded[:16], decoded[16:]
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    if hmac.compare_digest(key, stored_key):
        return True
    key_legacy = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return hmac.compare_digest(key_legacy, stored_key)


async def _send_sms(phone: str, message: str) -> bool:
    """Send SMS via eSMS.vn API."""
    if not ESMS_API_KEY:
        logger.debug("DEV MODE — SMS to %s: %s", phone, message)
        return True

    intl_phone = "84" + phone[1:] if phone.startswith("0") else phone
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "http://rest.esms.vn/MainService.svc/json/SendMultipleMessage_V4_post_json/",
                json={
                    "ApiKey": ESMS_API_KEY,
                    "Content": message,
                    "Phone": intl_phone,
                    "SecretKey": ESMS_SECRET,
                    "SmsType": "2",
                    "Brandname": ESMS_BRANDNAME,
                },
            )
            data = resp.json()
            return data.get("CodeResult") == "100"
    except Exception:
        logger.exception("SMS send failed to %s", phone)
        return False


# ── Endpoints ──

@router.post("/request-otp")
async def request_otp(body: OTPRequest, request: Request):
    phone = body.phone

    now = time.time()
    last = _otp_rate.get(phone, 0)
    if now - last < OTP_RATE_LIMIT_SECONDS:
        wait = int(OTP_RATE_LIMIT_SECONDS - (now - last))
        raise HTTPException(429, f"Vui lòng đợi {wait}s trước khi gửi lại OTP")

    # GĐ4.7: chặn SMS-pump theo IP. SEC-002: dùng get_client_ip (chỉ tin XFF từ
    # TRUSTED_PROXIES) — tránh giả mạo X-Forwarded-For để vượt rate-limit.
    from middleware import get_client_ip
    ip = get_client_ip(request)
    hits = [t for t in _otp_ip_rate.get(ip, []) if now - t < OTP_IP_WINDOW]
    if len(hits) >= OTP_IP_LIMIT:
        raise HTTPException(429, "Quá nhiều yêu cầu OTP từ IP này. Vui lòng thử lại sau.")
    hits.append(now)
    _otp_ip_rate[ip] = hits
    _gc_rate_dict(_otp_ip_rate, OTP_IP_WINDOW)

    _otp_rate[phone] = now
    _gc_rate_dict(_otp_rate, OTP_RATE_LIMIT_SECONDS)

    code = _generate_otp()
    hashed = _hash_otp(code)
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    def _save_otp():
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO otp_sessions (phone, code, expires_at)
                VALUES ({db._ph}, {db._ph}, {db._ph})
            """, (phone, hashed, expires.isoformat()))
    await asyncio.to_thread(_save_otp)

    message = f"Ma OTP cua ban la {code}. Het han sau {OTP_EXPIRE_MINUTES} phut."
    sent = await _send_sms(phone, message)

    # SEC-001: KHÔNG BAO GIỜ trả OTP trong HTTP response (auth-bypass nếu prod thiếu
    # ESMS_API_KEY). Khi chưa cấu hình SMS provider (dev), in ra log server để dev đọc.
    if not ESMS_API_KEY:
        logger.warning("[DEV] OTP cho %s: %s (chưa cấu hình ESMS_API_KEY)", phone, code)

    return {
        "success": True,
        "message": "OTP đã được gửi" if sent else "Không gửi được SMS, thử lại sau",
        "expires_in": OTP_EXPIRE_MINUTES * 60,
    }


@router.post("/verify-otp")
async def verify_otp(body: OTPVerify, request: Request):
    from middleware import get_client_ip
    ip = get_client_ip(request)
    now = time.time()
    hits = [t for t in _otp_verify_ip_rate.get(ip, []) if now - t < OTP_VERIFY_IP_WINDOW]
    if len(hits) >= OTP_VERIFY_IP_LIMIT:
        raise HTTPException(429, "Quá nhiều lần xác thực OTP từ IP này. Vui lòng thử lại sau.")
    hits.append(now)
    _otp_verify_ip_rate[ip] = hits
    _gc_rate_dict(_otp_verify_ip_rate, OTP_VERIFY_IP_WINDOW)

    phone = _normalize_phone(body.phone)
    hashed = _hash_otp(body.code.strip())

    def _verify():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT * FROM otp_sessions
                WHERE phone = {db._ph} AND verified = FALSE
                ORDER BY created_at DESC LIMIT 1
                FOR UPDATE SKIP LOCKED
            """, (phone,))
            if not row:
                raise HTTPException(400, "Không tìm thấy OTP. Vui lòng yêu cầu mã mới")
            otp = db._row_to_dict(row)
            if isinstance(otp.get("expires_at"), str):
                exp = datetime.fromisoformat(otp["expires_at"])
            else:
                exp = otp["expires_at"]
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                raise HTTPException(400, "OTP đã hết hạn. Vui lòng yêu cầu mã mới")
            attempts = otp.get("attempts", 0) + 1
            if attempts > OTP_MAX_ATTEMPTS:
                raise HTTPException(429, "Quá nhiều lần thử. Vui lòng yêu cầu mã mới")
            if not hmac.compare_digest(otp["code"], hashed):
                db._execute(conn, f"""
                    UPDATE otp_sessions SET attempts = {db._ph} WHERE id::text = {db._ph}
                """, (attempts, str(otp["id"])))
                raise HTTPException(400, f"OTP không đúng. Còn {OTP_MAX_ATTEMPTS - attempts} lần thử")
            db._execute(conn, f"""
                UPDATE otp_sessions SET verified = TRUE WHERE id::text = {db._ph}
            """, (str(otp["id"]),))
    await asyncio.to_thread(_verify)

    def _get_or_create_user():
        u = db.get_user_by_phone(phone)
        if not u:
            if not body.consent:
                raise HTTPException(400, "Vui lòng đồng ý Điều khoản sử dụng và Chính sách bảo mật")
            u = db.create_user(phone, consent_version=CONSENT_VERSION)
        else:
            updates = {}
            if not u.get("is_active", True):
                updates["is_active"] = True
            if u.get("deleted_at"):
                updates["deleted_at"] = None
                updates["is_active"] = True
            if updates:
                db.update_user(str(u["id"]), **updates)
                u.update(updates)
        return u
    user = await asyncio.to_thread(_get_or_create_user)

    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    from middleware import get_client_ip
    ip = get_client_ip(request)

    if body.consent:
        await asyncio.to_thread(_log_consent, str(user["id"]), CONSENT_VERSION, ip)
    ua = request.headers.get("user-agent", "")

    def _create_session():
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
                VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
            """, (str(user["id"]), _hash_token(token), ua, ip, expires.isoformat()))
    await asyncio.to_thread(_create_session)

    await asyncio.to_thread(_log_login, phone, "otp", True, request, str(user["id"]))

    return {
        "success": True,
        "token": token,
        "user": _safe_user(user),
        "has_password": bool(user.get("password_hash")),
        "expires_at": expires.isoformat(),
    }


CHECK_PHONE_IP_LIMIT = _cfg.CHECK_PHONE_IP_LIMIT
CHECK_PHONE_IP_WINDOW = _cfg.CHECK_PHONE_IP_WINDOW
_check_phone_ip_rate: dict[str, list[float]] = {}


@router.post("/check-phone")
async def check_phone(body: CheckPhone, request: Request):
    from middleware import get_client_ip
    ip = get_client_ip(request)
    now = time.time()
    hits = [t for t in _check_phone_ip_rate.get(ip, []) if now - t < CHECK_PHONE_IP_WINDOW]
    if len(hits) >= CHECK_PHONE_IP_LIMIT:
        raise HTTPException(429, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    hits.append(now)
    _check_phone_ip_rate[ip] = hits
    _gc_rate_dict(_check_phone_ip_rate, CHECK_PHONE_IP_WINDOW)

    phone = _normalize_phone(body.phone)
    user = await asyncio.to_thread(db.get_user_by_phone, phone)
    return {"has_password": bool(user and user.get("password_hash"))}


@router.post("/login")
async def login_password(body: PasswordLogin, request: Request):
    # P0-15: rate-limit theo IP (chống brute-force mật khẩu).
    from middleware import get_client_ip
    ip = get_client_ip(request)
    now = time.time()
    hits = [t for t in _login_ip_rate.get(ip, []) if now - t < LOGIN_IP_WINDOW]
    if len(hits) >= LOGIN_IP_LIMIT:
        raise HTTPException(429, "Quá nhiều lần đăng nhập. Vui lòng thử lại sau.")
    hits.append(now)
    _login_ip_rate[ip] = hits
    _gc_rate_dict(_login_ip_rate, LOGIN_IP_WINDOW)

    phone = _normalize_phone(body.phone)

    phone_hits = [t for t in _login_phone_fails.get(phone, []) if now - t < LOGIN_PHONE_WINDOW]
    if len(phone_hits) >= LOGIN_PHONE_LIMIT:
        raise HTTPException(429, "Tài khoản tạm khoá do đăng nhập sai nhiều lần. Thử lại sau 15 phút.")

    user = await asyncio.to_thread(db.get_user_by_phone, phone)

    if not user or not user.get("password_hash"):
        phone_hits.append(now)
        _login_phone_fails[phone] = phone_hits
        _gc_rate_dict(_login_phone_fails, LOGIN_PHONE_WINDOW)
        await asyncio.to_thread(_log_login, phone, "password", False, request)
        raise HTTPException(401, "Số điện thoại hoặc mật khẩu không đúng")

    if not user.get("is_active", True):
        await asyncio.to_thread(_log_login, phone, "password", False, request, str(user["id"]))
        raise HTTPException(403, "Tài khoản đã bị vô hiệu hóa")

    if not _verify_password(body.password, user["password_hash"]):
        phone_hits.append(now)
        _login_phone_fails[phone] = phone_hits
        _gc_rate_dict(_login_phone_fails, LOGIN_PHONE_WINDOW)
        await asyncio.to_thread(_log_login, phone, "password", False, request, str(user["id"]))
        raise HTTPException(401, "Số điện thoại hoặc mật khẩu không đúng")

    _login_phone_fails.pop(phone, None)

    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    ua = request.headers.get("user-agent", "")

    def _create_session():
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
                VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
            """, (str(user["id"]), _hash_token(token), ua, ip, expires.isoformat()))
    await asyncio.to_thread(_create_session)

    await asyncio.to_thread(_log_login, phone, "password", True, request, str(user["id"]))

    return {
        "success": True,
        "token": token,
        "user": _safe_user(user),
        "expires_at": expires.isoformat(),
    }


@router.post("/set-password")
async def set_password(body: SetPassword, request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    if not await _check_session_binding_safe(request, user):
        logger.warning("Session binding mismatch on set-password for user %s", user.get("id"))

    if user.get("password_hash"):
        if not body.current_password:
            raise HTTPException(400, "Vui lòng nhập mật khẩu hiện tại")
        if not _verify_password(body.current_password, user["password_hash"]):
            raise HTTPException(400, "Mật khẩu hiện tại không đúng")

    hashed = _hash_password(body.password)
    await asyncio.to_thread(db.update_user, str(user["id"]), password_hash=hashed)

    # P1-9: đổi mật khẩu → thu hồi MỌI phiên khác (giữ phiên hiện tại), chống chiếm dụng.
    cur = _extract_token(request)
    cur_hash = _hash_token(cur) if cur else None
    def _revoke_others():
        with db._conn() as conn:
            if cur_hash:
                db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph} AND token != {db._ph}",
                            (str(user["id"]), cur_hash))
            else:
                db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}", (str(user["id"]),))
    await asyncio.to_thread(_revoke_others)
    return {"success": True, "message": "Đã đặt mật khẩu thành công"}


@router.post("/logout")
async def logout(request: Request):
    token = _extract_token(request)
    if not token:
        return {"success": True}
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM user_sessions WHERE token = {db._ph}", (_hash_token(token),))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.get("/sessions")
async def list_sessions(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    cur_token = _extract_token(request)
    cur_hash = _hash_token(cur_token) if cur_token else None
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT id, user_agent, ip_address, created_at, expires_at, token
                FROM user_sessions
                WHERE user_id::text = {db._ph} AND expires_at > NOW()
                ORDER BY created_at DESC
            """, (str(user["id"]),))
    rows = await asyncio.to_thread(_query)
    sessions = []
    for r in rows:
        rd = db._row_to_dict(r)
        sessions.append({
            "id": str(rd["id"]),
            "user_agent": rd.get("user_agent", ""),
            "ip_address": rd.get("ip_address", ""),
            "created_at": str(rd.get("created_at", "")),
            "expires_at": str(rd.get("expires_at", "")),
            "is_current": hmac.compare_digest(rd.get("token") or "", cur_hash or ""),
        })
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"""
                DELETE FROM user_sessions
                WHERE id::text = {db._ph} AND user_id::text = {db._ph}
            """, (session_id, str(user["id"])))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.get("/me")
async def get_me(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    return {"user": _safe_user(user)}


@router.post("/deactivate")
async def deactivate_account(request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    if not await _check_session_binding_safe(request, user):
        logger.warning("Session binding mismatch on deactivate for user %s", user.get("id"))
    uid = str(user["id"])
    await asyncio.to_thread(db.update_user, uid, is_active=False)
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}", (uid,))
    await asyncio.to_thread(_query)
    return {"success": True, "message": "Tài khoản đã bị vô hiệu hóa. Đăng nhập lại bằng OTP để kích hoạt."}


@router.delete("/account")
async def delete_account(request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    if not await _check_session_binding_safe(request, user):
        logger.warning("Session binding mismatch on delete-account for user %s", user.get("id"))
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE users SET deleted_at = NOW(), is_active = FALSE
                WHERE id::text = {db._ph}
            """, (uid,))
            db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}", (uid,))
    await asyncio.to_thread(_query)
    return {
        "success": True,
        "status": "scheduled",
        "message": f"Tài khoản sẽ bị xoá vĩnh viễn sau {ACCOUNT_DELETE_GRACE_DAYS} ngày. Đăng nhập lại bằng OTP để huỷ.",
        "grace_days": ACCOUNT_DELETE_GRACE_DAYS,
    }


@router.put("/profile")
async def update_profile(body: ProfileUpdate, request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")

    fields = {}
    if body.display_name is not None:
        name = body.display_name.strip()[:50]
        if len(name) < 2:
            raise HTTPException(400, "Tên hiển thị phải từ 2 ký tự trở lên")
        fields["display_name"] = _html.escape(name)
    if body.bio is not None:
        fields["bio"] = _html.escape(body.bio.strip()[:300])
    if body.username is not None:
        uname = body.username.strip().lower()
        if uname == "":
            fields["username"] = None
        else:
            if len(uname) < 3 or len(uname) > 30:
                raise HTTPException(400, "Username phải từ 3–30 ký tự")
            if not re.match(r'^[a-z][a-z0-9._-]*$', uname):
                raise HTTPException(400, "Username chỉ gồm chữ cái, số, dấu chấm, gạch ngang (bắt đầu bằng chữ)")
            _reserved = {"admin", "mod", "moderator", "support", "help", "system", "root",
                         "api", "auth", "login", "signup", "register", "settings", "caidat",
                         "vinhlong360", "congdong", "baiviet", "thongbao", "nguoidung"}
            if uname in _reserved:
                raise HTTPException(400, "Username này không được phép sử dụng")
            ph = db._ph
            def _check_uname():
                with db._conn() as conn:
                    return db._fetchone(conn,
                        f"SELECT id FROM users WHERE lower(username) = {ph} AND id != {ph}::uuid",
                        (uname, str(user["id"])))
            existing = await asyncio.to_thread(_check_uname)
            if existing:
                raise HTTPException(409, "Username đã được sử dụng")
            fields["username"] = uname

    if fields:
        user = await asyncio.to_thread(lambda: db.update_user(str(user["id"]), **fields))

    return {"user": _safe_user(user)}


@router.get("/check-username/{username}")
async def check_username(username: str, request: Request):
    uname = username.strip().lower()
    if len(uname) < 3 or len(uname) > 30:
        return {"available": False, "reason": "Username phải từ 3–30 ký tự"}
    if not re.match(r'^[a-z][a-z0-9._-]*$', uname):
        return {"available": False, "reason": "Username chỉ gồm chữ cái, số, dấu chấm, gạch ngang"}
    ph = db._ph
    def _query():
        with db._conn() as conn:
            return db._fetchone(conn, f"SELECT id FROM users WHERE lower(username) = {ph}", (uname,))
    existing = await asyncio.to_thread(_query)
    if existing:
        user = await _get_current_user_or_none(request)
        if user and str(existing["id"]) == str(user["id"]):
            return {"available": True}
        return {"available": False, "reason": "Username đã được sử dụng"}
    return {"available": True}


@router.post("/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"avatar:{user['id']}", 5, 600, "Upload ảnh quá nhanh. Vui lòng thử lại sau.")

    from storage import storage, MAX_IMAGE_SIZE, sniff_image_type

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    if not sniff_image_type(data):
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")

    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "avatars", str(user["id"])[:8])
    except ValueError:
        raise HTTPException(400, "Ảnh không hợp lệ hoặc đã hỏng")
    except Exception:
        logger.exception("Avatar upload failed for user %s", user["id"])
        raise HTTPException(500, "Không thể upload ảnh, vui lòng thử lại")

    avatar_url = urls.get("md") or urls.get("sm")
    await asyncio.to_thread(db.update_user, str(user["id"]), avatar_url=avatar_url)
    return {"avatar_url": avatar_url, "sizes": urls}


@router.post("/cover")
async def upload_cover(request: Request, file: UploadFile = File(...)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"cover:{user['id']}", 5, 600, "Upload ảnh quá nhanh. Vui lòng thử lại sau.")

    from storage import storage, MAX_IMAGE_SIZE, sniff_image_type

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    if not sniff_image_type(data):
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")

    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "covers", str(user["id"])[:8])
    except ValueError:
        raise HTTPException(400, "Ảnh không hợp lệ hoặc đã hỏng")
    except Exception:
        logger.exception("Cover upload failed for user %s", user["id"])
        raise HTTPException(500, "Không thể upload ảnh, vui lòng thử lại")

    cover_url = urls.get("lg") or urls.get("md")
    await asyncio.to_thread(db.update_user, str(user["id"]), cover_url=cover_url)
    return {"cover_url": cover_url, "sizes": urls}


# ── Consent logging ──

def _log_consent(user_id: str, version: str, ip: str):
    try:
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO consent_log (user_id, version, ip)
                VALUES ({ph}::uuid, {ph}, {ph})
            """, (user_id, version, ip))
    except Exception as e:
        logger.warning("Failed to log consent for user %s: %s", user_id, e)


@router.get("/consent-history")
async def consent_history(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, version, ip, created_at
                FROM consent_log
                WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC
                LIMIT 20
            """, (str(user["id"]),))
        return {"history": [dict(r) for r in rows]}
    return await asyncio.to_thread(_query)


# ── Login history ──

def _log_login(phone: str, method: str, success: bool, request: Request, user_id: str | None = None):
    from middleware import get_client_ip
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")[:500]
    try:
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO login_history (user_id, phone, method, success, ip, user_agent)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (user_id, phone, method, success, ip, ua))
    except Exception as e:
        logger.warning("Failed to log login for %s: %s", phone, e)


@router.get("/login-history")
async def get_login_history(request: Request, limit: int = 20):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, method, success, ip, user_agent, created_at
                FROM login_history
                WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC
                LIMIT {ph}
            """, (str(user["id"]), min(limit, 50)))
        return {"history": [dict(r) for r in rows]}
    return await asyncio.to_thread(_query)


# ── Privacy settings ──

class PrivacyUpdate(BaseModel):
    profile_visibility: str | None = None
    show_activity: bool | None = None
    show_saved: bool | None = None


@router.get("/privacy")
async def get_privacy(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT * FROM user_privacy WHERE user_id = {ph}::uuid", (str(user["id"]),))
        if row:
            row = db._row_to_dict(row)
            return {"profile_visibility": row["profile_visibility"], "show_activity": row["show_activity"], "show_saved": row["show_saved"]}
        return {"profile_visibility": "public", "show_activity": True, "show_saved": True}
    return await asyncio.to_thread(_query)


@router.put("/privacy")
async def update_privacy(body: PrivacyUpdate, request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")

    valid_vis = ("public", "followers", "private")
    if body.profile_visibility and body.profile_visibility not in valid_vis:
        raise HTTPException(400, f"profile_visibility phải là một trong: {', '.join(valid_vis)}")

    def _query():
        ph = db._ph
        uid = str(user["id"])
        with db._conn() as conn:
            existing = db._fetchone(conn, f"SELECT 1 FROM user_privacy WHERE user_id = {ph}::uuid", (uid,))
            if existing:
                sets, params = [], []
                if body.profile_visibility is not None:
                    sets.append(f"profile_visibility = {ph}")
                    params.append(body.profile_visibility)
                if body.show_activity is not None:
                    sets.append(f"show_activity = {ph}")
                    params.append(body.show_activity)
                if body.show_saved is not None:
                    sets.append(f"show_saved = {ph}")
                    params.append(body.show_saved)
                if sets:
                    sets.append(f"updated_at = NOW()")
                    params.append(uid)
                    db._execute(conn, f"UPDATE user_privacy SET {', '.join(sets)} WHERE user_id = {ph}::uuid", params)
            else:
                db._execute(conn, f"""
                    INSERT INTO user_privacy (user_id, profile_visibility, show_activity, show_saved)
                    VALUES ({ph}::uuid, {ph}, {ph}, {ph})
                """, (uid, body.profile_visibility or "public", body.show_activity if body.show_activity is not None else True, body.show_saved if body.show_saved is not None else True))
    await asyncio.to_thread(_query)
    return await get_privacy(request)


# ── Auth helpers (used by other modules) ──

def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("token")


async def _get_current_user_or_none(request: Request) -> dict | None:
    token = _extract_token(request)
    if not token:
        return None
    def _query():
        try:
            with db._conn() as conn:
                row = db._fetchone(conn, f"""
                    SELECT u.*, s.ip_address AS session_ip, s.user_agent AS session_ua
                    FROM user_sessions s
                    JOIN users u ON u.id = s.user_id
                    WHERE s.token = {db._ph} AND s.expires_at > NOW()
                      AND u.is_active = TRUE AND u.deleted_at IS NULL
                """, (_hash_token(token),))
                return db._row_to_dict(row)
        except Exception:
            logger.exception("DB error in _get_current_user_or_none")
            return None
    return await asyncio.to_thread(_query)


def _safe_user(user: dict) -> dict:
    if not user:
        return None
    return {
        "id": str(user["id"]),
        "phone": user["phone"][:3] + "****" + user["phone"][-3:],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "cover_url": user.get("cover_url"),
        "bio": user.get("bio", ""),
        "username": user.get("username"),
        "role": user.get("role", "user"),
        "created_at": str(user.get("created_at", "")),
    }
