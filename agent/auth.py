"""
vinhlong360 — Authentication (OTP + Password).

Endpoints:
  POST /auth/request-otp        — gửi OTP qua SMS (eSMS.vn)
  POST /auth/verify-otp         — xác minh OTP, tạo session
  POST /auth/set-password        — đặt/đổi mật khẩu (cần đăng nhập)
  POST /auth/reset-password-otp  — đặt lại mật khẩu qua OTP (quên mật khẩu)
  POST /auth/login               — đăng nhập bằng SĐT + mật khẩu
  POST /auth/check-phone         — kiểm tra SĐT đã có mật khẩu chưa
  POST /auth/logout              — hủy session
  GET  /auth/me                  — thông tin user hiện tại
  GET  /auth/export-data         — xuất toàn bộ dữ liệu user (GDPR)

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
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from config import settings as _cfg
from database import db


async def _require_csrf_lazy(request: Request) -> None:
    from auth_middleware import require_csrf
    await require_csrf(request)


async def _check_session_binding_safe(request, user):
    try:
        from auth_middleware import check_session_binding
        return await check_session_binding(request, user)
    except Exception:
        logging.getLogger("auth").warning("session binding check failed, denying access", exc_info=True)
        return False


def _require_pg():
    if not db._use_pg:
        raise HTTPException(503, detail="Tính năng UGC/auth cần Postgres. Local dev: docker compose up postgres.")


router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(_require_pg)])

# ── Config ──

OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = _cfg.OTP_EXPIRE_MINUTES
OTP_MAX_ATTEMPTS = 5
OTP_RATE_LIMIT_SECONDS = 60
SESSION_EXPIRE_DAYS = _cfg.SESSION_EXPIRE_DAYS

ESMS_API_KEY = _cfg.ESMS_API_KEY
ESMS_SECRET = _cfg.ESMS_SECRET
ESMS_BRANDNAME = _cfg.ESMS_BRANDNAME

VN_PHONE_RE = re.compile(r"^(0|\+84)(3|5|7|8|9)\d{8}$")

_otp_rate: dict[str, float] = {}

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
OTP_VERIFY_PHONE_LIMIT = 5
OTP_VERIFY_PHONE_WINDOW = 300
_otp_verify_phone_rate: dict[str, list[float]] = {}

ACCOUNT_DELETE_GRACE_DAYS = _cfg.ACCOUNT_DELETE_GRACE_DAYS

_RATE_GC_THRESHOLD = 500

def _gc_rate_dict(d: dict, window: float) -> None:
    if len(d) <= _RATE_GC_THRESHOLD:
        return
    now = time.time()
    stale = [k for k, v in d.items()
             if not v or now - (max(v) if isinstance(v, list) else v) > window]
    for k in stale:
        del d[k]
    if len(d) > _RATE_GC_THRESHOLD * 4:
        oldest = sorted(d.keys(), key=lambda k: max(d[k]) if isinstance(d[k], list) else d[k])
        for k in oldest[:len(d) - _RATE_GC_THRESHOLD]:
            del d[k]


def cleanup_expired_data() -> dict:
    """Remove expired sessions, OTP records, and old login history. Call from scheduler."""
    if not db._use_pg:
        return {"skipped": True}
    ph = db._ph
    results = {}
    try:
        with db._conn() as conn:
            r = db._execute(conn, "DELETE FROM user_sessions WHERE expires_at < NOW()", ())
            results["expired_sessions"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, "DELETE FROM otp_sessions WHERE expires_at < NOW()", ())
            results["expired_otps"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, f"""
                DELETE FROM login_history WHERE created_at < NOW() - INTERVAL '90 days'
            """, ())
            results["old_login_history"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, f"""
                DELETE FROM notifications WHERE read = TRUE AND created_at < NOW() - INTERVAL '60 days'
            """, ())
            results["old_read_notifications"] = getattr(r, "rowcount", 0) if r else 0
    except Exception as e:
        logger.warning("cleanup_expired_data error: %s", e)
        results["error"] = str(e)
    return results


def _mask_phone(phone: str) -> str:
    if len(phone) <= 6:
        return phone[:2] + "***"
    return phone[:3] + "***" + phone[-3:]


def _mask_ip(ip: str | None) -> str:
    """Mask IP for user-facing responses (keep first two octets for rough geo)."""
    if not ip:
        return ""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return ip[:8] + "***"


def _create_session_atomic(uid: str, token_hash: str, ua: str, ip: str, expires_iso: str):
    from auth_middleware import MAX_CONCURRENT_SESSIONS
    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
        """, (uid, token_hash, ua, ip, expires_iso))
        db._execute(conn, f"""
            DELETE FROM user_sessions WHERE id IN (
                SELECT id FROM user_sessions
                WHERE user_id::text = {db._ph} AND expires_at > NOW()
                ORDER BY created_at DESC
                OFFSET {db._ph}
            )
        """, (uid, MAX_CONCURRENT_SESSIONS))


# ── Models ──

class OTPRequest(BaseModel):
    phone: str = Field(..., max_length=20)

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
    phone: str = Field(..., max_length=20)
    code: str = Field(..., max_length=10)
    consent: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        if not VN_PHONE_RE.match(v):
            raise ValueError("Số điện thoại VN không hợp lệ")
        return v


class PasswordLogin(BaseModel):
    phone: str = Field(..., max_length=20)
    password: str = Field(..., max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        if not VN_PHONE_RE.match(v):
            raise ValueError("Số điện thoại VN không hợp lệ")
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


class ResetPasswordOTP(BaseModel):
    phone: str = Field(..., max_length=20)
    code: str = Field(..., max_length=10)
    new_password: str = Field(..., max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        if not VN_PHONE_RE.match(v):
            raise ValueError("Số điện thoại VN không hợp lệ")
        return v

    @field_validator("new_password")
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
    phone: str = Field(..., max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+84"):
            v = "0" + v[3:]
        return v


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=50)
    bio: str | None = Field(None, max_length=300)
    username: str | None = Field(None, max_length=30)


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


_PBKDF2_ITERATIONS = _cfg.PBKDF2_ITERATIONS

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return base64.b64encode(salt + key).decode()


_DUMMY_HASH = _hash_password("timing_safety_dummy")


def _verify_password(password: str, stored: str, *, _return_legacy=False):
    decoded = base64.b64decode(stored)
    salt, stored_key = decoded[:16], decoded[16:]
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    if hmac.compare_digest(key, stored_key):
        return (True, False) if _return_legacy else True
    key_legacy = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    matched = hmac.compare_digest(key_legacy, stored_key)
    return (matched, matched) if _return_legacy else matched


_SMS_MAX_RETRIES = 3

async def _send_sms(phone: str, message: str) -> bool:
    """Send SMS via eSMS.vn API with retry + exponential backoff."""
    if not ESMS_API_KEY:
        logger.debug("DEV MODE — SMS to %s: %s", phone, message)
        return True

    intl_phone = "84" + phone[1:] if phone.startswith("0") else phone
    payload = {
        "ApiKey": ESMS_API_KEY,
        "Content": message,
        "Phone": intl_phone,
        "SecretKey": ESMS_SECRET,
        "SmsType": "2",
        "Brandname": ESMS_BRANDNAME,
    }
    for attempt in range(_SMS_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://rest.esms.vn/MainService.svc/json/SendMultipleMessage_V4_post_json/",
                    json=payload,
                )
                data = resp.json()
                if data.get("CodeResult") == "100":
                    return True
                logger.warning("SMS attempt %d failed for %s: code=%s",
                               attempt + 1, _mask_phone(phone), data.get("CodeResult"))
        except Exception:
            logger.warning("SMS attempt %d exception for %s",
                           attempt + 1, _mask_phone(phone), exc_info=True)
        if attempt < _SMS_MAX_RETRIES - 1:
            await asyncio.sleep(0.5 * (2 ** attempt))
    logger.error("SMS delivery failed after %d attempts for %s",
                 _SMS_MAX_RETRIES, _mask_phone(phone))
    return False


# ── Endpoints ──

@router.post("/request-otp",
             summary="Request OTP code",
             description="Sends a one-time password to the provided phone number via SMS. Rate-limited per phone and per IP to prevent abuse.")
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
        logger.warning("[DEV] OTP cho %s (chưa cấu hình ESMS_API_KEY)", _mask_phone(phone))

    return {
        "success": True,
        "message": "OTP đã được gửi" if sent else "Không gửi được SMS, thử lại sau",
        "expires_in": OTP_EXPIRE_MINUTES * 60,
    }


@router.post("/verify-otp",
             summary="Verify OTP and create session",
             description="Verifies the OTP code for a phone number. On success, creates or reactivates the user account and returns a session token.")
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
    phone_hits = [t for t in _otp_verify_phone_rate.get(phone, []) if now - t < OTP_VERIFY_PHONE_WINDOW]
    if len(phone_hits) >= OTP_VERIFY_PHONE_LIMIT:
        raise HTTPException(429, "Quá nhiều lần nhập OTP cho số này. Vui lòng yêu cầu mã mới sau 5 phút.")
    phone_hits.append(now)
    _otp_verify_phone_rate[phone] = phone_hits
    _gc_rate_dict(_otp_verify_phone_rate, OTP_VERIFY_PHONE_WINDOW)
    hashed = _hash_otp(body.code.strip())

    def _verify():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT id, code, expires_at, attempts, phone FROM otp_sessions
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
    ua = request.headers.get("user-agent", "")[:500]

    await asyncio.to_thread(
        _create_session_atomic, str(user["id"]), _hash_token(token), ua, ip, expires.isoformat()
    )

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


@router.post("/check-phone",
             summary="Check if phone number exists",
             description="Checks whether a phone number is already registered. Returns a boolean indicating account existence.")
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
    return {"exists": bool(user)}


@router.post("/login",
             summary="Login with phone and password",
             description="Authenticates a user with phone number and password. Returns a session token on success. Rate-limited per IP and per phone to prevent brute-force attacks.")
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
        # Constant-time: always run PBKDF2 to prevent timing oracle
        await asyncio.to_thread(_verify_password, body.password, _DUMMY_HASH)
        phone_hits.append(now)
        _login_phone_fails[phone] = phone_hits
        _gc_rate_dict(_login_phone_fails, LOGIN_PHONE_WINDOW)
        await asyncio.to_thread(_log_login, phone, "password", False, request)
        raise HTTPException(401, "Số điện thoại hoặc mật khẩu không đúng")

    if not user.get("is_active", True):
        await asyncio.to_thread(_log_login, phone, "password", False, request, str(user["id"]))
        raise HTTPException(403, "Tài khoản đã bị vô hiệu hóa")

    matched, is_legacy = await asyncio.to_thread(_verify_password, body.password, user["password_hash"], _return_legacy=True)
    if not matched:
        phone_hits.append(now)
        _login_phone_fails[phone] = phone_hits
        _gc_rate_dict(_login_phone_fails, LOGIN_PHONE_WINDOW)
        await asyncio.to_thread(_log_login, phone, "password", False, request, str(user["id"]))
        raise HTTPException(401, "Số điện thoại hoặc mật khẩu không đúng")

    if is_legacy:
        new_hash = await asyncio.to_thread(_hash_password, body.password)
        def _rehash():
            with db._conn() as conn:
                db._execute(conn, f"UPDATE users SET password_hash = {db._ph} WHERE id::text = {db._ph}",
                            (new_hash, str(user["id"])))
        await asyncio.to_thread(_rehash)
        logger.info("Rehashed legacy PBKDF2 password for user %s", user["id"])

    _login_phone_fails.pop(phone, None)

    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    ua = request.headers.get("user-agent", "")[:500]

    await asyncio.to_thread(
        _create_session_atomic, str(user["id"]), _hash_token(token), ua, ip, expires.isoformat()
    )

    await asyncio.to_thread(_log_login, phone, "password", True, request, str(user["id"]))

    return {
        "success": True,
        "token": token,
        "user": _safe_user(user),
        "expires_at": expires.isoformat(),
    }


@router.post("/set-password",
             summary="Set or change password",
             description="Sets a new password for the authenticated user. If a password already exists, the current password must be verified first. Revokes all other sessions on success.")
async def set_password(body: SetPassword, request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"set-password:{user['id']}", 5, 600, "Đổi mật khẩu quá nhanh. Vui lòng thử lại sau.")
    if not await _check_session_binding_safe(request, user):
        logger.warning("Session binding mismatch on set-password for user %s", user.get("id"))
        raise HTTPException(403, "Phiên không hợp lệ. Vui lòng đăng nhập lại.")

    if user.get("password_hash"):
        if not body.current_password:
            raise HTTPException(400, "Vui lòng nhập mật khẩu hiện tại")
        if not await asyncio.to_thread(_verify_password, body.current_password, user["password_hash"]):
            raise HTTPException(400, "Mật khẩu hiện tại không đúng")

    hashed = await asyncio.to_thread(_hash_password, body.password)
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


@router.post("/reset-password-otp",
             summary="Reset password via OTP",
             description="Resets the user's password by verifying an OTP code. Revokes all existing sessions, requiring the user to log in again with the new password.")
async def reset_password_otp(body: ResetPasswordOTP, request: Request, _csrf=Depends(_require_csrf_lazy)):
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
    phone_hits = [t for t in _otp_verify_phone_rate.get(phone, []) if now - t < OTP_VERIFY_PHONE_WINDOW]
    if len(phone_hits) >= OTP_VERIFY_PHONE_LIMIT:
        raise HTTPException(429, "Quá nhiều lần nhập OTP cho số này. Vui lòng yêu cầu mã mới sau 5 phút.")
    phone_hits.append(now)
    _otp_verify_phone_rate[phone] = phone_hits
    _gc_rate_dict(_otp_verify_phone_rate, OTP_VERIFY_PHONE_WINDOW)
    hashed_code = _hash_otp(body.code.strip())

    def _verify_and_reset():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT id, code, expires_at, attempts, phone FROM otp_sessions
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
            if not hmac.compare_digest(otp["code"], hashed_code):
                db._execute(conn, f"""
                    UPDATE otp_sessions SET attempts = {db._ph} WHERE id::text = {db._ph}
                """, (attempts, str(otp["id"])))
                raise HTTPException(400, f"OTP không đúng. Còn {OTP_MAX_ATTEMPTS - attempts} lần thử")
            db._execute(conn, f"""
                UPDATE otp_sessions SET verified = TRUE WHERE id::text = {db._ph}
            """, (str(otp["id"]),))

            user = db.get_user_by_phone(phone)
            if not user:
                raise HTTPException(404, "Không tìm thấy tài khoản với số điện thoại này")
            pw_hash = _hash_password(body.new_password)
            db._execute(conn, f"""
                UPDATE users SET password_hash = {db._ph} WHERE id::text = {db._ph}
            """, (pw_hash, str(user["id"])))
            db._execute(conn, f"""
                DELETE FROM user_sessions WHERE user_id::text = {db._ph}
            """, (str(user["id"]),))
            return user

    user = await asyncio.to_thread(_verify_and_reset)
    await asyncio.to_thread(_log_login, phone, "password_reset", True, request, str(user["id"]))
    return {"success": True, "message": "Đã đặt lại mật khẩu. Vui lòng đăng nhập lại."}


@router.post("/logout",
             summary="Logout current session",
             description="Invalidates the current session token. Returns success even if no valid session exists.")
async def logout(request: Request, _csrf=Depends(_require_csrf_lazy)):
    from ratelimit import check_rate
    from middleware import get_client_ip
    check_rate(f"logout:{get_client_ip(request)}", 10, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    token = _extract_token(request)
    if not token:
        return {"success": True}
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM user_sessions WHERE token = {db._ph}", (_hash_token(token),))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/refresh",
             summary="Refresh session token",
             description="Rotates the session token by issuing a new token and revoking the old one. Extends the session expiry.")
async def refresh_token(request: Request, _csrf=Depends(_require_csrf_lazy)):
    """Rotate session token — issue new token, revoke old. Reduces compromise window."""
    from ratelimit import check_rate
    from middleware import get_client_ip
    check_rate(f"refresh:{get_client_ip(request)}", 10, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    old_token = _extract_token(request)
    if not old_token:
        raise HTTPException(401, "Chưa đăng nhập")

    new_token = _generate_token()
    new_hash = _hash_token(new_token)
    old_hash = _hash_token(old_token)
    new_expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)

    def _rotate():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE user_sessions SET token = {db._ph}, expires_at = {db._ph}
                WHERE token = {db._ph} AND expires_at > NOW()
                RETURNING user_id
            """, (new_hash, new_expires.isoformat(), old_hash))
            return row
    result = await asyncio.to_thread(_rotate)
    if not result:
        raise HTTPException(401, "Session không hợp lệ hoặc đã hết hạn")

    return {
        "success": True,
        "token": new_token,
        "expires_at": new_expires.isoformat(),
    }


@router.get("/sessions",
            summary="List active sessions",
            description="Returns all active sessions for the authenticated user, including device info, IP address, and which session is current.")
async def list_sessions(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"sessions:{user['id']}", 10, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    cur_token = _extract_token(request)
    cur_hash = _hash_token(cur_token) if cur_token else None
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT id, user_agent, ip_address, created_at, expires_at, token
                FROM user_sessions
                WHERE user_id::text = {db._ph} AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 50
            """, (str(user["id"]),))
    rows = await asyncio.to_thread(_query)
    sessions = []
    for r in rows:
        rd = db._row_to_dict(r)
        sessions.append({
            "id": str(rd["id"]),
            "user_agent": rd.get("user_agent", ""),
            "ip_address": _mask_ip(rd.get("ip_address", "")),
            "created_at": str(rd.get("created_at", "")),
            "expires_at": str(rd.get("expires_at", "")),
            "is_current": hmac.compare_digest(rd.get("token") or "", cur_hash or ""),
        })
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}",
               summary="Revoke a session",
               description="Revokes a specific session by ID, logging out that device. Only sessions belonging to the authenticated user can be revoked.")
async def revoke_session(session_id: str, request: Request, _csrf=Depends(_require_csrf_lazy)):
    from auth_middleware import validate_path_id
    session_id = validate_path_id(session_id, "session_id")
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"revoke:{user['id']}", 20, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"""
                DELETE FROM user_sessions
                WHERE id::text = {db._ph} AND user_id::text = {db._ph}
            """, (session_id, str(user["id"])))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.get("/me",
            summary="Get current user profile",
            description="Returns the profile of the currently authenticated user, including display name, avatar, role, and masked phone number.")
async def get_me(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"me:{user['id']}", 60, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    return {"user": _safe_user(user)}


@router.post("/deactivate",
             summary="Deactivate account",
             description="Deactivates the authenticated user's account and revokes all sessions. The account can be reactivated by logging in again via OTP.")
async def deactivate_account(request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"deactivate:{user['id']}", 3, 3600, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    if not await _check_session_binding_safe(request, user):
        logger.warning("Session binding mismatch on deactivate for user %s", user.get("id"))
        raise HTTPException(403, "Phiên không hợp lệ. Vui lòng đăng nhập lại.")
    uid = str(user["id"])
    await asyncio.to_thread(db.update_user, uid, is_active=False)
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}", (uid,))
    await asyncio.to_thread(_query)
    return {"success": True, "message": "Tài khoản đã bị vô hiệu hóa. Đăng nhập lại bằng OTP để kích hoạt."}


@router.delete("/account",
               summary="Schedule account deletion",
               description="Schedules the authenticated user's account for permanent deletion after a grace period. Revokes all sessions. Logging in via OTP within the grace period cancels deletion.")
async def delete_account(request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"delete-account:{user['id']}", 3, 3600, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    if not await _check_session_binding_safe(request, user):
        logger.warning("Session binding mismatch on delete-account for user %s", user.get("id"))
        raise HTTPException(403, "Phiên không hợp lệ. Vui lòng đăng nhập lại.")
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


@router.put("/profile",
            summary="Update user profile",
            description="Updates the authenticated user's display name, bio, and/or username. Content is moderated and HTML-escaped. Returns the updated profile.")
async def update_profile(body: ProfileUpdate, request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"profile:{user['id']}", 20, 600, "Cập nhật hồ sơ quá nhanh. Vui lòng thử lại sau.")

    from moderation import moderate_content
    fields = {}
    if body.display_name is not None:
        name = body.display_name.strip()[:50]
        if len(name) < 2:
            raise HTTPException(400, "Tên hiển thị phải từ 2 ký tự trở lên")
        mod = await moderate_content(name)
        if mod["status"] == "flagged":
            raise HTTPException(400, "Tên hiển thị chứa nội dung không phù hợp")
        fields["display_name"] = _html.escape(name)
    if body.bio is not None:
        bio_text = body.bio.strip()[:300]
        if bio_text:
            mod = await moderate_content(bio_text)
            if mod["status"] == "flagged":
                raise HTTPException(400, "Tiểu sử chứa nội dung không phù hợp")
        fields["bio"] = _html.escape(bio_text)
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
        try:
            user = await asyncio.to_thread(lambda: db.update_user(str(user["id"]), **fields))
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise HTTPException(409, "Username đã được sử dụng")
            logger.exception("Profile update failed")
            raise HTTPException(500, "Cập nhật hồ sơ thất bại")

    return {"user": _safe_user(user)}


@router.get("/check-username/{username}",
            summary="Check username availability",
            description="Checks whether a username is available for registration. Returns availability status and a reason if unavailable.")
async def check_username(username: str, request: Request):
    from middleware import get_client_ip
    from ratelimit import check_rate
    check_rate(f"check-username:{get_client_ip(request)}", 20, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
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


@router.post("/avatar",
             summary="Upload avatar image",
             description="Uploads and processes a user avatar image. The image is resized to multiple sizes in WebP format. Returns the avatar URL and all available sizes.")
async def upload_avatar(request: Request, file: UploadFile = File(...), _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"avatar:{user['id']}", 5, 600, "Upload ảnh quá nhanh. Vui lòng thử lại sau.")

    from storage import storage, MAX_IMAGE_SIZE, sniff_image_type

    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_IMAGE_SIZE * 2:
        raise HTTPException(413, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    data = await file.read(MAX_IMAGE_SIZE + 1)
    if len(data) > MAX_IMAGE_SIZE:
        del data
        raise HTTPException(413, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
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


@router.post("/cover",
             summary="Upload cover image",
             description="Uploads and processes a profile cover image. The image is resized to multiple sizes in WebP format. Returns the cover URL and all available sizes.")
async def upload_cover(request: Request, file: UploadFile = File(...), _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"cover:{user['id']}", 5, 600, "Upload ảnh quá nhanh. Vui lòng thử lại sau.")

    from storage import storage, MAX_IMAGE_SIZE, sniff_image_type

    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_IMAGE_SIZE * 2:
        raise HTTPException(413, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    data = await file.read(MAX_IMAGE_SIZE + 1)
    if len(data) > MAX_IMAGE_SIZE:
        del data
        raise HTTPException(413, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
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


@router.get("/consent-history",
            summary="Get consent history",
            description="Returns the authenticated user's consent acceptance history, including version, masked IP, and timestamp for each record.")
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
        return {"history": [{"id": str(db._row_to_dict(r)["id"]),
                             "version": db._row_to_dict(r).get("version"),
                             "ip": _mask_ip(db._row_to_dict(r).get("ip")),
                             "created_at": str(db._row_to_dict(r).get("created_at", ""))}
                            for r in rows]}
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
            """, (user_id, _mask_phone(phone), method, success, ip, ua))
    except Exception as e:
        logger.warning("Failed to log login for %s: %s", _mask_phone(phone), e)


@router.get("/login-history",
            summary="Get login history",
            description="Returns the authenticated user's recent login attempts, including method, success status, masked IP, and user agent.")
async def get_login_history(request: Request, limit: int = Query(20, ge=1, le=100)):
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
        result = []
        for r in rows:
            d = db._row_to_dict(r)
            result.append({"id": str(d["id"]), "method": d.get("method"),
                           "success": d.get("success"), "ip": _mask_ip(d.get("ip")),
                           "user_agent": d.get("user_agent"),
                           "created_at": str(d.get("created_at", ""))})
        return {"history": result}
    return await asyncio.to_thread(_query)


# ── Privacy settings ──

class PrivacyUpdate(BaseModel):
    profile_visibility: str | None = Field(None, max_length=20)
    show_activity: bool | None = None
    show_saved: bool | None = None

    @field_validator("profile_visibility")
    @classmethod
    def validate_visibility(cls, v):
        if v is not None and v not in ("public", "followers", "private"):
            raise ValueError("profile_visibility phải là: public, followers, private")
        return v


@router.get("/privacy",
            summary="Get privacy settings",
            description="Returns the authenticated user's privacy settings including profile visibility, activity visibility, and saved items visibility.")
async def get_privacy(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT user_id, profile_visibility, show_activity, show_saved FROM user_privacy WHERE user_id = {ph}::uuid", (str(user["id"]),))
        if row:
            row = db._row_to_dict(row)
            return {"profile_visibility": row["profile_visibility"], "show_activity": row["show_activity"], "show_saved": row["show_saved"]}
        return {"profile_visibility": "public", "show_activity": True, "show_saved": True}
    return await asyncio.to_thread(_query)


@router.put("/privacy",
            summary="Update privacy settings",
            description="Updates the authenticated user's privacy settings. Supports profile visibility (public/followers/private), activity visibility, and saved items visibility.")
async def update_privacy(body: PrivacyUpdate, request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"privacy:{user['id']}", 10, 600, "Cập nhật quá nhanh. Vui lòng thử lại sau.")

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


# ── Data export (GDPR / privacy compliance) ──

@router.get("/export-data",
            summary="Export all user data",
            description="Exports all data associated with the authenticated user for GDPR compliance. Includes profile, posts, comments, likes, bookmarks, follows, visits, reactions, collections, blocks, and mutes.")
async def export_user_data(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from ratelimit import check_rate
    check_rate(f"export-data:{user['id']}", 2, 86400, "Chỉ được xuất dữ liệu 2 lần/ngày.")
    uid = str(user["id"])
    ph = db._ph

    def _query():
        with db._conn() as conn:
            _EXPORT_CAP = 5000
            posts = db._fetchall(conn, f"""
                SELECT id, content, post_type, rating, entity_id, entity_name,
                       like_count, comment_count, created_at
                FROM posts WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            comments = db._fetchall(conn, f"""
                SELECT id, post_id, content, parent_id, created_at
                FROM comments WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            likes = db._fetchall(conn, f"""
                SELECT post_id, created_at
                FROM likes WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            bookmarks = db._fetchall(conn, f"""
                SELECT entity_id, created_at
                FROM saved_entities WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            follows = db._fetchall(conn, f"""
                SELECT target_type, target_id, created_at
                FROM follows WHERE follower_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            visits = db._fetchall(conn, f"""
                SELECT entity_id, status, visited_at, created_at
                FROM user_visits WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            reactions = db._fetchall(conn, f"""
                SELECT post_id, reaction_type, created_at
                FROM post_reactions WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            collections = db._fetchall(conn, f"""
                SELECT id, name, description, is_public, created_at
                FROM user_collections WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            blocks = db._fetchall(conn, f"""
                SELECT blocked_id, created_at
                FROM blocks WHERE blocker_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
            mutes = db._fetchall(conn, f"""
                SELECT muted_id, created_at
                FROM user_mutes WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC LIMIT {_EXPORT_CAP}
            """, (uid,))
        return {
            "posts": [db._row_to_dict(r) for r in posts],
            "comments": [db._row_to_dict(r) for r in comments],
            "likes": [db._row_to_dict(r) for r in likes],
            "bookmarks": [db._row_to_dict(r) for r in bookmarks],
            "follows": [db._row_to_dict(r) for r in follows],
            "visits": [db._row_to_dict(r) for r in visits],
            "reactions": [db._row_to_dict(r) for r in reactions],
            "collections": [db._row_to_dict(r) for r in collections],
            "blocks": [db._row_to_dict(r) for r in blocks],
            "mutes": [db._row_to_dict(r) for r in mutes],
        }

    ugc = await asyncio.to_thread(_query)
    profile = _safe_user(user)
    profile["bio"] = user.get("bio", "")
    return {
        "profile": profile,
        "data": ugc,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Auth helpers (used by other modules) ──

_TOKEN_MAX_LEN = 128

def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        t = auth[7:]
        if 16 <= len(t) <= _TOKEN_MAX_LEN:
            return t
        return None
    t = request.cookies.get("token")
    if t and 16 <= len(t) <= _TOKEN_MAX_LEN:
        return t
    return None


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
        "phone": (user.get("phone") or "")[:3] + "****" + (user.get("phone") or "")[-3:],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "cover_url": user.get("cover_url"),
        "bio": user.get("bio", ""),
        "username": user.get("username"),
        "role": user.get("role", "user"),
        "created_at": str(user.get("created_at", "")),
    }
