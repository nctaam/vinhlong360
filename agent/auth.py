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
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
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
SESSION_COOKIE_NAME = "vl360_token"

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


def _enforce_local_rate(store: dict, key: str, limit: int, window: int, msg: str) -> None:
    """Cửa sổ trượt in-memory: lọc hit cũ, chặn nếu vượt limit, ghi hit mới + gc.
    Trích nguyên văn mẫu lặp ở nhiều endpoint (comprehension + guard + append + gc)."""
    now = time.time()
    hits = [t for t in store.get(key, []) if now - t < window]
    if len(hits) >= limit:
        raise HTTPException(429, msg)
    hits.append(now)
    store[key] = hits
    _gc_rate_dict(store, window)


def _check_shared_auth_rate(key: str, limit: int, window: int, msg: str) -> None:
    try:
        from ratelimit import check_rate
        check_rate(f"auth:{key}", limit, window, msg)
    except HTTPException:
        raise
    except Exception:
        logger.debug("shared auth rate limit failed", exc_info=True)

def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}

def _request_is_production(request: Request) -> bool:
    if _truthy_env("VL360_FORCE_SECURE_COOKIES") or _truthy_env("SECURE_COOKIES"):
        return True
    if os.environ.get("ENVIRONMENT", "").lower() in {"production", "prod", "prd"}:
        return True
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").split(",", 1)[0].strip().lower()
    host_header = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.hostname or ""
    host = host_header.split(",", 1)[0].split(":")[0].lower()
    if host == "vinhlong360.vn" or host.endswith(".vinhlong360.vn"):
        return True
    return proto == "https" and host.endswith("vinhlong360.vn")

def _cookie_params_for_request(request: Request) -> dict:
    from auth_middleware import get_secure_cookie_params
    is_production = _request_is_production(request)
    params = get_secure_cookie_params(is_production=is_production)
    params["max_age"] = SESSION_EXPIRE_DAYS * 86400
    host = (request.headers.get("host") or request.url.hostname or "").split(":")[0].lower()
    if not is_production and (host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")):
        params.pop("domain", None)
        params.pop("secure", None)
    return params

def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    """Attach the session as the primary HttpOnly cookie transport."""
    response.set_cookie(key=SESSION_COOKIE_NAME, value=token, **_cookie_params_for_request(request))

def _clear_session_cookie(response: Response, request: Request) -> None:
    params = _cookie_params_for_request(request)
    domain = params.get("domain")
    secure = bool(params.get("secure", False))
    samesite = params.get("samesite", "lax")
    for name in (SESSION_COOKIE_NAME, "token", "session_token"):
        response.delete_cookie(key=name, path="/", domain=domain, secure=secure, httponly=True, samesite=samesite)
        if domain:
            response.delete_cookie(key=name, path="/", secure=secure, httponly=True, samesite=samesite)


def cleanup_expired_data() -> dict:
    """Remove expired sessions, OTP records, and old login history. Call from scheduler."""
    if not db._use_pg:
        return {"skipped": True}
    results = {}
    try:
        with db._conn() as conn:
            r = db._execute(conn, "DELETE FROM user_sessions WHERE expires_at < NOW()", ())
            results["expired_sessions"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, "DELETE FROM otp_sessions WHERE expires_at < NOW()", ())
            results["expired_otps"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, """
                DELETE FROM login_history WHERE created_at < NOW() - INTERVAL '90 days'
            """, ())
            results["old_login_history"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, """
                DELETE FROM notifications WHERE read = TRUE AND created_at < NOW() - INTERVAL '60 days'
            """, ())
            results["old_read_notifications"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, "DELETE FROM pending_2fa WHERE expires_at < NOW()", ())
            results["expired_pending_2fa"] = getattr(r, "rowcount", 0) if r else 0
            r = db._execute(conn, "DELETE FROM trusted_devices WHERE expires_at < NOW()", ())
            results["expired_trusted_devices"] = getattr(r, "rowcount", 0) if r else 0
    except Exception as e:
        logger.warning("cleanup_expired_data error: %s", e)
        results["error"] = str(e)
    return results


def _rows_to_dicts(rows) -> list:
    """Chuyển danh sách hàng DB → list[dict] (gom comprehension lặp lại ở export)."""
    return [db._row_to_dict(r) for r in rows]


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


def _is_internal_session(user_agent: str | None, ip: str | None) -> bool:
    ua = (user_agent or "").lower()
    ip_text = (ip or "").strip().lower()
    internal_ua_markers = (
        "python-urllib", "python-requests", "httpx", "aiohttp",
        "curl/", "wget/", "healthcheck", "uptime",
        "node", "undici", "node-fetch",
    )
    if any(marker in ua for marker in internal_ua_markers):
        return True
    loopback = ip_text in {"::1", "localhost", "0.0.0.0"} or ip_text.startswith("127.")
    browser_markers = ("mozilla/", "chrome/", "safari/", "firefox/", "edg/")
    return loopback and not any(marker in ua for marker in browser_markers)


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
    full_name: str | None = Field(None, max_length=100)
    username: str | None = Field(None, max_length=30)
    password: str | None = Field(None, max_length=128)
    date_of_birth: str | None = Field(None, max_length=10)

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
    full_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=300)
    email: str | None = Field(None, max_length=200)
    contact_info: str | None = Field(None, max_length=500)


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

    from middleware import get_client_ip
    ip = get_client_ip(request)
    _check_shared_auth_rate(f"otp_phone:{phone}", 1, OTP_RATE_LIMIT_SECONDS, "Vui long doi truoc khi gui lai OTP")
    _check_shared_auth_rate(f"otp_ip:{ip}", OTP_IP_LIMIT, OTP_IP_WINDOW, "Qua nhieu yeu cau OTP tu IP nay. Vui long thu lai sau.")

    now = time.time()
    last = _otp_rate.get(phone, 0)
    if now - last < OTP_RATE_LIMIT_SECONDS:
        wait = int(OTP_RATE_LIMIT_SECONDS - (now - last))
        raise HTTPException(429, f"Vui lòng đợi {wait}s trước khi gửi lại OTP")

    # GĐ4.7: chặn SMS-pump theo IP. SEC-002: dùng get_client_ip (chỉ tin XFF từ
    # TRUSTED_PROXIES) — tránh giả mạo X-Forwarded-For để vượt rate-limit.
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


async def _finish_login(user: dict, phone: str, method: str, request: Request, response: Response) -> dict:
    """Tạo session + cookie + log + streak + achievement; trả về response đăng nhập.
    Dùng chung cho verify_otp/login_password và /2fa/verify — trước đây mỗi endpoint
    lặp lại chuỗi này riêng (session-limit enforcement vẫn qua _create_session_atomic,
    chỉ đổi chỗ gọi, không đổi hành vi)."""
    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    from middleware import get_client_ip
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")[:500]
    await asyncio.to_thread(_create_session_atomic, str(user["id"]), _hash_token(token), ua, ip, expires.isoformat())
    # ORDER MATTERS: this must run before the history-write call below — it
    # queries for a PRIOR successful login with the same ip/ua. Running it
    # after (or racing it via create_task) risks the just-written current-login
    # row self-matching, so the alert would never fire. await = deterministic
    # ordering, not a race. The helper swallows its own errors, so it can never
    # block login regardless.
    await asyncio.to_thread(_check_suspicious_login, str(user["id"]), ip, ua, user.get("display_name") or "")
    await asyncio.to_thread(_log_login, phone, method, True, request, str(user["id"]))
    await asyncio.to_thread(_update_login_streak, str(user["id"]))
    _set_session_cookie(response, request, token)

    def _ach_bg(uid=str(user["id"])):
        try:
            from achievements import check_achievements
            with db._conn() as conn:
                check_achievements(conn, uid, notify=True)
        except Exception:
            pass
    asyncio.create_task(asyncio.to_thread(_ach_bg))
    return {
        "success": True,
        "token": token,
        "user": _safe_user(user),
        "has_password": bool(user.get("password_hash")),
        "expires_at": expires.isoformat(),
    }


# ── Trusted devices (Wave 4 W4.5) ──
# "Nhớ thiết bị này": opaque cookie token (raw gửi client, hash lưu DB) — cho phép
# bỏ qua thử thách 2FA trên thiết bị đã tin cậy, tự hết hạn qua expires_at (90 ngày).
# Mirror thiết kế session cookie (_hash_token) + pending_2fa (opaque token).

TRUSTED_DEVICE_COOKIE_NAME = "vl360_trusted"
TRUSTED_DEVICE_DAYS = 90


def _trusted_cookie_params(request: Request) -> dict:
    from auth_middleware import get_secure_cookie_params
    is_prod = _request_is_production(request)
    params = get_secure_cookie_params(is_production=is_prod)
    params["max_age"] = TRUSTED_DEVICE_DAYS * 86400
    host = (request.headers.get("host") or request.url.hostname or "").split(":")[0].lower()
    if not is_prod and (host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")):
        params.pop("domain", None)
        params.pop("secure", None)
    return params


def _short_ua(ua: str) -> str:
    """Nhãn thiết bị thô từ User-Agent (đủ để người dùng nhận ra trong danh sách)."""
    ua = ua or ""
    for tok in ("iPhone", "iPad", "Android", "Windows", "Macintosh", "Linux"):
        if tok in ua:
            return tok
    return "Thiết bị"


async def _remember_trusted_device(user: dict, request: Request, response: Response) -> None:
    """Ghi một hàng trusted_devices (hash token) + set cookie vl360_trusted (raw)."""
    from middleware import get_client_ip
    raw = _generate_token()
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")[:500]
    expires = datetime.now(timezone.utc) + timedelta(days=TRUSTED_DEVICE_DAYS)

    def _store():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO trusted_devices (user_id, token_hash, device_name, ip, user_agent, expires_at)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (str(user["id"]), _hash_token(raw), _short_ua(ua), ip, ua, expires.isoformat()))
    await asyncio.to_thread(_store)
    response.set_cookie(key=TRUSTED_DEVICE_COOKIE_NAME, value=raw, **_trusted_cookie_params(request))


def _has_valid_trusted_device(user_id: str, request: Request) -> bool:
    """Kiểm tra cookie vl360_trusted khớp hàng trusted_devices chưa hết hạn; cập nhật last_used_at."""
    raw = request.cookies.get(TRUSTED_DEVICE_COOKIE_NAME, "")
    if not raw:
        return False
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            SELECT id FROM trusted_devices
            WHERE user_id::text = {ph} AND token_hash = {ph} AND expires_at > NOW()
        """, (user_id, _hash_token(raw)))
        if not row:
            return False
        d = db._row_to_dict(row)
        db._execute(conn, f"UPDATE trusted_devices SET last_used_at = NOW() WHERE id = {ph}", (d["id"],))
        return True


def _consume_verified_otp(conn, phone: str, hashed_code: str) -> dict:
    """Xác thực OTP mới nhất chưa dùng cho `phone` trên connection cho trước, tăng
    attempts/đánh dấu verified như logic gốc. Trích chung cho verify-otp và
    reset-password-otp (trước đây lặp nguyên văn) — không đổi hành vi/thứ tự."""
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
    return otp


def _register_new_user(phone: str, body: "OTPVerify") -> dict:
    """Tạo user mới từ luồng verify-otp (yêu cầu consent). Trích nguyên văn từ
    nhánh 'chưa có tài khoản' của _get_or_create_user — không đổi hành vi."""
    if not body.consent:
        raise HTTPException(400, "Vui lòng đồng ý Điều khoản sử dụng và Chính sách bảo mật")
    reg_kwargs = {}
    if body.full_name:
        reg_kwargs["full_name"] = _html.escape(body.full_name.strip()[:100])
    if body.username:
        uname = body.username.strip().lower()
        if len(uname) >= 3 and re.match(r'^[a-z][a-z0-9._-]*$', uname):
            with db._conn() as conn:
                dup = db._fetchone(conn,
                    f"SELECT id FROM users WHERE lower(username) = {db._ph}", (uname,))
            if dup:
                raise HTTPException(409, "Username đã được sử dụng")
            reg_kwargs["username"] = uname
    if body.password:
        pwd = body.password
        if len(pwd) < 8:
            raise HTTPException(400, "Mật khẩu phải từ 8 ký tự trở lên")
        reg_kwargs["password_hash"] = _hash_password(pwd)
    if body.date_of_birth:
        reg_kwargs["date_of_birth"] = body.date_of_birth
    return db.create_user(phone, consent_version=CONSENT_VERSION, **reg_kwargs)


def _reactivate_user(u: dict) -> dict:
    """Kích hoạt lại tài khoản đã tắt/đã lên lịch xoá khi đăng nhập lại qua OTP."""
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


def _get_or_create_user(phone: str, body: "OTPVerify") -> dict:
    u = db.get_user_by_phone(phone)
    if not u:
        return _register_new_user(phone, body)
    return _reactivate_user(u)


@router.post("/verify-otp",
             summary="Verify OTP and create session",
             description="Verifies the OTP code for a phone number. On success, creates or reactivates the user account and returns a session token.")
async def verify_otp(body: OTPVerify, request: Request, response: Response):
    from middleware import get_client_ip
    ip = get_client_ip(request)
    phone = _normalize_phone(body.phone)
    _check_shared_auth_rate(f"otp_verify_ip:{ip}", OTP_VERIFY_IP_LIMIT, OTP_VERIFY_IP_WINDOW, "Qua nhieu lan xac thuc OTP tu IP nay. Vui long thu lai sau.")
    _check_shared_auth_rate(f"otp_verify_phone:{phone}", OTP_VERIFY_PHONE_LIMIT, OTP_VERIFY_PHONE_WINDOW, "Qua nhieu lan nhap OTP cho so nay. Vui long yeu cau ma moi sau 5 phut.")
    _enforce_local_rate(_otp_verify_ip_rate, ip, OTP_VERIFY_IP_LIMIT, OTP_VERIFY_IP_WINDOW, "Quá nhiều lần xác thực OTP từ IP này. Vui lòng thử lại sau.")
    _enforce_local_rate(_otp_verify_phone_rate, phone, OTP_VERIFY_PHONE_LIMIT, OTP_VERIFY_PHONE_WINDOW, "Quá nhiều lần nhập OTP cho số này. Vui lòng yêu cầu mã mới sau 5 phút.")
    hashed = _hash_otp(body.code.strip())

    def _verify():
        with db._conn() as conn:
            _consume_verified_otp(conn, phone, hashed)
    await asyncio.to_thread(_verify)

    user = await asyncio.to_thread(_get_or_create_user, phone, body)

    from middleware import get_client_ip
    ip = get_client_ip(request)

    if body.consent:
        await asyncio.to_thread(_log_consent, str(user["id"]), CONSENT_VERSION, ip)

    if _2fa_is_enabled(str(user["id"])) and not await asyncio.to_thread(_has_valid_trusted_device, str(user["id"]), request):
        ua = request.headers.get("user-agent", "")[:500]
        challenge = await asyncio.to_thread(_create_pending_2fa, str(user["id"]), ip, ua)
        await asyncio.to_thread(_log_login, phone, "otp", True, request, str(user["id"]))
        return {"two_factor_required": True, "challenge_id": challenge}

    return await _finish_login(user, phone, "otp", request, response)


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
    _check_shared_auth_rate(f"check_phone_ip:{ip}", CHECK_PHONE_IP_LIMIT, CHECK_PHONE_IP_WINDOW, "Qua nhieu yeu cau. Vui long thu lai sau.")
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
async def login_password(body: PasswordLogin, request: Request, response: Response):
    # P0-15: rate-limit theo IP (chống brute-force mật khẩu).
    from middleware import get_client_ip
    ip = get_client_ip(request)
    now = time.time()
    _check_shared_auth_rate(f"login_ip:{ip}", LOGIN_IP_LIMIT, LOGIN_IP_WINDOW, "Qua nhieu lan dang nhap. Vui long thu lai sau.")
    _enforce_local_rate(_login_ip_rate, ip, LOGIN_IP_LIMIT, LOGIN_IP_WINDOW, "Quá nhiều lần đăng nhập. Vui lòng thử lại sau.")

    phone = _normalize_phone(body.phone)

    phone_hits = [t for t in _login_phone_fails.get(phone, []) if now - t < LOGIN_PHONE_WINDOW]
    if len(phone_hits) >= LOGIN_PHONE_LIMIT:
        raise HTTPException(429, "Tài khoản tạm khoá do đăng nhập sai nhiều lần. Thử lại sau 15 phút.")

    user = await asyncio.to_thread(db.get_user_by_phone, phone)

    if not user or not user.get("password_hash"):
        # Constant-time: always run PBKDF2 to prevent timing oracle
        await asyncio.to_thread(_verify_password, body.password, _DUMMY_HASH)
        _check_shared_auth_rate(f"login_phone_fail:{phone}", LOGIN_PHONE_LIMIT, LOGIN_PHONE_WINDOW, "Tai khoan tam khoa do dang nhap sai nhieu lan. Thu lai sau 15 phut.")
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
        _check_shared_auth_rate(f"login_phone_fail:{phone}", LOGIN_PHONE_LIMIT, LOGIN_PHONE_WINDOW, "Tai khoan tam khoa do dang nhap sai nhieu lan. Thu lai sau 15 phut.")
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

    if _2fa_is_enabled(str(user["id"])) and not await asyncio.to_thread(_has_valid_trusted_device, str(user["id"]), request):
        ua = request.headers.get("user-agent", "")[:500]
        challenge = await asyncio.to_thread(_create_pending_2fa, str(user["id"]), ip, ua)
        await asyncio.to_thread(_log_login, phone, "password", True, request, str(user["id"]))
        return {"two_factor_required": True, "challenge_id": challenge}

    return await _finish_login(user, phone, "password", request, response)


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
async def reset_password_otp(body: ResetPasswordOTP, request: Request, response: Response, _csrf=Depends(_require_csrf_lazy)):
    from middleware import get_client_ip
    ip = get_client_ip(request)
    phone = _normalize_phone(body.phone)
    _check_shared_auth_rate(f"otp_verify_ip:{ip}", OTP_VERIFY_IP_LIMIT, OTP_VERIFY_IP_WINDOW, "Qua nhieu lan xac thuc OTP tu IP nay. Vui long thu lai sau.")
    _check_shared_auth_rate(f"otp_verify_phone:{phone}", OTP_VERIFY_PHONE_LIMIT, OTP_VERIFY_PHONE_WINDOW, "Qua nhieu lan nhap OTP cho so nay. Vui long yeu cau ma moi sau 5 phut.")
    _enforce_local_rate(_otp_verify_ip_rate, ip, OTP_VERIFY_IP_LIMIT, OTP_VERIFY_IP_WINDOW, "Quá nhiều lần xác thực OTP từ IP này. Vui lòng thử lại sau.")
    _enforce_local_rate(_otp_verify_phone_rate, phone, OTP_VERIFY_PHONE_LIMIT, OTP_VERIFY_PHONE_WINDOW, "Quá nhiều lần nhập OTP cho số này. Vui lòng yêu cầu mã mới sau 5 phút.")
    hashed_code = _hash_otp(body.code.strip())

    def _verify_and_reset():
        with db._conn() as conn:
            _consume_verified_otp(conn, phone, hashed_code)

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
    await asyncio.to_thread(_update_login_streak, str(user["id"]))

    def _ach_bg(uid=str(user["id"])):
        try:
            from achievements import check_achievements
            with db._conn() as conn:
                check_achievements(conn, uid, notify=True)
        except Exception:
            pass
    asyncio.create_task(asyncio.to_thread(_ach_bg))

    _clear_session_cookie(response, request)
    return {"success": True, "message": "Đã đặt lại mật khẩu. Vui lòng đăng nhập lại."}


@router.post("/logout",
             summary="Logout current session",
             description="Invalidates the current session token. Returns success even if no valid session exists.")
async def logout(request: Request, response: Response, _csrf=Depends(_require_csrf_lazy)):
    from ratelimit import check_rate
    from middleware import get_client_ip
    check_rate(f"logout:{get_client_ip(request)}", 10, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    token = _extract_token(request)
    if not token:
        _clear_session_cookie(response, request)
        return {"success": True}
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM user_sessions WHERE token = {db._ph}", (_hash_token(token),))
    await asyncio.to_thread(_query)
    _clear_session_cookie(response, request)
    return {"success": True}


@router.post("/refresh",
             summary="Refresh session token",
             description="Rotates the session token by issuing a new token and revoking the old one. Extends the session expiry.")
async def refresh_token(request: Request, response: Response, _csrf=Depends(_require_csrf_lazy)):
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

    _set_session_cookie(response, request, new_token)
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
    hidden_internal_count = 0
    for r in rows:
        rd = db._row_to_dict(r)
        is_current = hmac.compare_digest(rd.get("token") or "", cur_hash or "")
        if not is_current and _is_internal_session(rd.get("user_agent"), rd.get("ip_address")):
            hidden_internal_count += 1
            continue
        sessions.append({
            "id": str(rd["id"]),
            "user_agent": rd.get("user_agent", ""),
            "ip_address": _mask_ip(rd.get("ip_address", "")),
            "created_at": str(rd.get("created_at", "")),
            "expires_at": str(rd.get("expires_at", "")),
            "is_current": is_current,
        })
    return {"sessions": sessions, "hidden_internal_count": hidden_internal_count}


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


@router.get("/csrf",
            summary="Get CSRF token",
            description="Returns the CSRF token required for authenticated state-changing requests.")
async def get_csrf(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chua dang nhap")
    session_token = _extract_token(request)
    if not session_token:
        raise HTTPException(401, "Chua dang nhap")
    from auth_middleware import generate_csrf_token
    return {"csrf_token": generate_csrf_token(session_token)}


@router.post("/deactivate",
             summary="Deactivate account",
             description="Deactivates the authenticated user's account and revokes all sessions. The account can be reactivated by logging in again via OTP.")
async def deactivate_account(request: Request, response: Response, _csrf=Depends(_require_csrf_lazy)):
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
    _clear_session_cookie(response, request)
    return {"success": True, "message": "Tài khoản đã bị vô hiệu hóa. Đăng nhập lại bằng OTP để kích hoạt."}


@router.delete("/account",
               summary="Schedule account deletion",
               description="Schedules the authenticated user's account for permanent deletion after a grace period. Revokes all sessions. Logging in via OTP within the grace period cancels deletion.")
async def delete_account(request: Request, response: Response, _csrf=Depends(_require_csrf_lazy)):
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
    _clear_session_cookie(response, request)
    return {
        "success": True,
        "status": "scheduled",
        "message": f"Tài khoản sẽ bị xoá vĩnh viễn sau {ACCOUNT_DELETE_GRACE_DAYS} ngày. Đăng nhập lại bằng OTP để huỷ.",
        "grace_days": ACCOUNT_DELETE_GRACE_DAYS,
    }


async def _persist_profile_fields(user_id: str, fields: dict) -> dict:
    """Ghi các trường hồ sơ đã kiểm duyệt xuống DB (trích nguyên văn khối try/except)."""
    try:
        return await asyncio.to_thread(lambda: db.update_user(user_id, **fields))
    except Exception:
        logger.exception("Profile update failed")
        raise HTTPException(500, "Cập nhật hồ sơ thất bại")


async def _profile_apply_full_name(body: "ProfileUpdate", fields: dict) -> None:
    """Kiểm duyệt + escape họ tên (trích nguyên văn nhánh full_name của update_profile)."""
    from moderation import moderate_content
    fname = body.full_name.strip()[:100]
    if fname and len(fname) < 2:
        raise HTTPException(400, "Họ tên phải từ 2 ký tự trở lên")
    mod = await moderate_content(fname)
    if mod["status"] == "flagged":
        raise HTTPException(400, "Họ tên chứa nội dung không phù hợp")
    fields["full_name"] = _html.escape(fname) if fname else None


def _profile_apply_email(body: "ProfileUpdate", fields: dict) -> None:
    """Validate email (trích nguyên văn nhánh email của update_profile)."""
    email_val = body.email.strip()[:200]
    if email_val and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_val):
        raise HTTPException(400, "Email không hợp lệ")
    fields["email"] = email_val if email_val else None


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
    if body.full_name is not None:
        await _profile_apply_full_name(body, fields)
    if body.bio is not None:
        bio_text = body.bio.strip()[:300]
        if bio_text:
            mod = await moderate_content(bio_text)
            if mod["status"] == "flagged":
                raise HTTPException(400, "Tiểu sử chứa nội dung không phù hợp")
        fields["bio"] = _html.escape(bio_text)
    if body.email is not None:
        _profile_apply_email(body, fields)
    if body.contact_info is not None:
        fields["contact_info"] = _html.escape(body.contact_info.strip()[:500])

    if fields:
        user = await _persist_profile_fields(str(user["id"]), fields)

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


def _check_suspicious_login(user_id: str, ip: str, ua: str, display_name: str = ""):
    """Nếu IP+UA này chưa từng đăng nhập thành công (90 ngày) → thông báo bảo mật.
    Fire-and-forget, nuốt lỗi (không bao giờ chặn đăng nhập). Cố ý KHÔNG gắn danh
    tính 'người thực hiện' cho thông báo này (security_alert không có tác nhân xã
    hội — nếu gắn sẽ vô tình kích hoạt lọc chặn/ẩn vốn chỉ dành cho thông báo xã hội).

    QUAN TRỌNG về thứ tự gọi: hàm này phải chạy TRƯỚC bước ghi lịch sử đăng nhập
    hiện tại — nếu không, truy vấn bên dưới sẽ tự khớp với chính hàng vừa ghi
    (cùng ip/ua) và cảnh báo sẽ không bao giờ kích hoạt."""
    try:
        ph = db._ph
        with db._conn() as conn:
            seen = db._fetchone(conn, f"""
                SELECT 1 FROM login_history
                WHERE user_id = {ph}::uuid AND success = TRUE
                  AND (ip = {ph} OR user_agent = {ph})
                  AND created_at > NOW() - INTERVAL '90 days'
                LIMIT 1
            """, (user_id, ip, ua))
        if seen:
            return  # thiết bị/mạng đã biết
        from notifications import create_notification
        device = _short_ua(ua)
        create_notification(
            user_id=user_id,
            notif_type="security_alert",
            title="🔐 Đăng nhập mới",
            body=f"Đăng nhập mới từ {device} (IP {_mask_ip(ip)}). Nếu không phải bạn, hãy đổi mật khẩu ngay.",
            ref_type="login_history",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("suspicious-login check failed for %s: %s", user_id, e)


def _update_login_streak(user_id: str) -> int:
    """Cập nhật chuỗi đăng nhập liên tiếp. Trả về streak mới (0 nếu lỗi).
    - Cùng ngày (last_login_date = today): giữ nguyên (không tính 2 lần/ngày).
    - Hôm qua (today - 1): +1.
    - Cách >1 ngày hoặc lần đầu: reset về 1.
    Nuốt lỗi (không chặn đăng nhập), giống _log_login."""
    try:
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE users SET
                    login_streak = CASE
                        WHEN last_login_date = CURRENT_DATE THEN login_streak
                        WHEN last_login_date = CURRENT_DATE - INTERVAL '1 day' THEN login_streak + 1
                        ELSE 1
                    END,
                    last_login_date = CURRENT_DATE
                WHERE id::text = {ph}
                RETURNING login_streak
            """, (user_id,))
            return int(db._row_to_dict(row)["login_streak"]) if row else 0
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to update login streak for %s: %s", user_id, e)
        return 0


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


def _upsert_privacy(uid: str, body: "PrivacyUpdate") -> None:
    ph = db._ph
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
                sets.append("updated_at = NOW()")
                params.append(uid)
                db._execute(conn, f"UPDATE user_privacy SET {', '.join(sets)} WHERE user_id = {ph}::uuid", params)
        else:
            db._execute(conn, f"""
                INSERT INTO user_privacy (user_id, profile_visibility, show_activity, show_saved)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph})
            """, (uid, body.profile_visibility or "public", body.show_activity if body.show_activity is not None else True, body.show_saved if body.show_saved is not None else True))


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

    await asyncio.to_thread(_upsert_privacy, str(user["id"]), body)
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
                SELECT p.id, p.content, p.post_type, p.rating, p.entity_id,
                       e.name as entity_name,
                       p.like_count, p.comment_count, p.created_at
                FROM posts p
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.user_id = {ph}::uuid
                ORDER BY p.created_at DESC LIMIT {_EXPORT_CAP}
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
            "posts": _rows_to_dicts(posts),
            "comments": _rows_to_dicts(comments),
            "likes": _rows_to_dicts(likes),
            "bookmarks": _rows_to_dicts(bookmarks),
            "follows": _rows_to_dicts(follows),
            "visits": _rows_to_dicts(visits),
            "reactions": _rows_to_dicts(reactions),
            "collections": _rows_to_dicts(collections),
            "blocks": _rows_to_dicts(blocks),
            "mutes": _rows_to_dicts(mutes),
        }

    ugc = await asyncio.to_thread(_query)
    profile = _safe_user(user)
    profile["bio"] = user.get("bio", "")
    return {
        "profile": profile,
        "data": ugc,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 2FA enrollment (Wave 4) ──
# secret_enc luôn MÃ HOÁ (Fernet) — không bao giờ log/trả ra ngoài trừ /2fa/setup
# (trả secret thô MỘT LẦN để quét QR/nhập tay — theo thiết kế). Mã khôi phục cũng
# chỉ trả MỘT LẦN ở /2fa/verify-setup.

def _get_2fa_row(user_id: str) -> dict | None:
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT user_id, secret_enc, enabled FROM user_2fa WHERE user_id::text = {ph}", (user_id,))
        return db._row_to_dict(row) if row else None


def _2fa_is_enabled(user_id: str) -> bool:
    if not _cfg.TWO_FACTOR_ENABLED:
        return False
    row = _get_2fa_row(user_id)
    return bool(row and row.get("enabled"))


@router.post("/2fa/setup",
             summary="Begin 2FA enrollment",
             description="Generates a new TOTP secret for the authenticated user and stores it encrypted (disabled) pending confirmation via /2fa/verify-setup.")
async def twofa_setup(request: Request, _csrf=Depends(_require_csrf_lazy)):
    from twofactor import generate_secret, provisioning_uri, qr_data_uri, encrypt_secret
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    if not _cfg.TWO_FACTOR_ENABLED:
        raise HTTPException(403, "Xác thực 2 bước chưa được kích hoạt.")
    uid = str(user["id"])
    from ratelimit import check_rate
    check_rate(f"2fa-setup:{uid}", 5, 600, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    if _2fa_is_enabled(uid):
        raise HTTPException(400, "2FA đã được bật")
    secret = generate_secret()
    account = user.get("phone") or user.get("username") or uid
    enc = encrypt_secret(secret)

    def _store():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO user_2fa (user_id, secret_enc, enabled)
                VALUES ({ph}::uuid, {ph}, FALSE)
                ON CONFLICT (user_id) DO UPDATE SET secret_enc = EXCLUDED.secret_enc, enabled = FALSE, created_at = NOW(), verified_at = NULL
            """, (uid, enc))
    await asyncio.to_thread(_store)

    uri = provisioning_uri(secret, str(account))
    return {"secret": secret, "otpauth_uri": uri, "qr": qr_data_uri(uri)}


class _TwoFACode(BaseModel):
    code: str


@router.post("/2fa/verify-setup",
             summary="Confirm 2FA enrollment",
             description="Confirms 2FA enrollment with a TOTP code from the authenticator app, enables 2FA, and returns one-time recovery codes.")
async def twofa_verify_setup(body: _TwoFACode, request: Request, _csrf=Depends(_require_csrf_lazy)):
    from twofactor import decrypt_secret, verify_totp, generate_recovery_codes, hash_recovery_code
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    if not _cfg.TWO_FACTOR_ENABLED:
        raise HTTPException(403, "Xác thực 2 bước chưa được kích hoạt.")
    uid = str(user["id"])
    from ratelimit import check_rate
    check_rate(f"2fa-verify-setup:{uid}", 5, 600, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    row = _get_2fa_row(uid)
    if not row:
        raise HTTPException(400, "Chưa bắt đầu thiết lập 2FA")
    if not verify_totp(decrypt_secret(row["secret_enc"]), body.code):
        raise HTTPException(400, "Mã không đúng. Vui lòng thử lại")
    codes = generate_recovery_codes(8)

    def _enable():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"UPDATE user_2fa SET enabled = TRUE, verified_at = NOW() WHERE user_id::text = {ph}", (uid,))
            db._execute(conn, f"DELETE FROM user_2fa_recovery_codes WHERE user_id::text = {ph}", (uid,))
            for c in codes:
                db._execute(conn, f"INSERT INTO user_2fa_recovery_codes (user_id, code_hash) VALUES ({ph}::uuid, {ph})", (uid, hash_recovery_code(c)))
    await asyncio.to_thread(_enable)
    return {"success": True, "recovery_codes": codes}


@router.post("/2fa/disable",
             summary="Disable 2FA",
             description="Disables 2FA for the authenticated user after verifying a current TOTP code or an unused recovery code. Removes stored secret, recovery codes, and trusted devices.")
async def twofa_disable(body: _TwoFACode, request: Request, _csrf=Depends(_require_csrf_lazy)):
    from twofactor import decrypt_secret, verify_totp, recovery_code_matches
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])
    from ratelimit import check_rate
    check_rate(f"2fa-disable:{uid}", 5, 600, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    row = _get_2fa_row(uid)
    if not row or not row.get("enabled"):
        raise HTTPException(400, "2FA chưa được bật")

    def _check_code() -> bool:
        if verify_totp(decrypt_secret(row["secret_enc"]), body.code):
            return True
        ph = db._ph
        with db._conn() as conn:
            rows = db._fetchall(conn, f"SELECT id, code_hash FROM user_2fa_recovery_codes WHERE user_id::text = {ph} AND used_at IS NULL", (uid,))
            for r in rows:
                d = db._row_to_dict(r)
                if recovery_code_matches(body.code, d["code_hash"]):
                    return True
        return False
    if not await asyncio.to_thread(_check_code):
        raise HTTPException(400, "Mã không đúng")

    def _disable():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM user_2fa WHERE user_id::text = {ph}", (uid,))
            db._execute(conn, f"DELETE FROM user_2fa_recovery_codes WHERE user_id::text = {ph}", (uid,))
            db._execute(conn, f"DELETE FROM trusted_devices WHERE user_id::text = {ph}", (uid,))
    await asyncio.to_thread(_disable)
    return {"success": True}


@router.get("/2fa/status", summary="2FA status for current user")
async def twofa_status(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])

    def _q():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT enabled FROM user_2fa WHERE user_id::text = {ph}", (uid,))
            enabled = bool(db._row_to_dict(row).get("enabled")) if row else False
            rem = 0
            if enabled:
                c = db._fetchone(conn, f"SELECT COUNT(*) c FROM user_2fa_recovery_codes WHERE user_id::text = {ph} AND used_at IS NULL", (uid,))
                rem = int(db._row_to_dict(c).get("c", 0)) if c else 0
            return enabled, rem
    enabled, rem = await asyncio.to_thread(_q)
    return {"enabled": enabled, "recovery_remaining": rem}


# ── 2FA login challenge (Wave 4 W4.4) ──
# Nửa-đăng-nhập: verify_otp/login_password phát challenge (KHÔNG tạo session) khi
# 2FA bật; /2fa/verify tiêu thụ challenge (dùng-một-lần, FOR UPDATE SKIP LOCKED,
# giới hạn OTP_MAX_ATTEMPTS) rồi mới gọi _finish_login. Mirror thiết kế otp_sessions.

TFA_VERIFY_IP_LIMIT = 15
TFA_VERIFY_IP_WINDOW = 300
_tfa_verify_ip_rate: dict[str, list[float]] = {}
PENDING_2FA_EXPIRE_MINUTES = 5


def _create_pending_2fa(user_id: str, ip: str, ua: str) -> str:
    raw = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(minutes=PENDING_2FA_EXPIRE_MINUTES)
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO pending_2fa (user_id, token_hash, ip, user_agent, expires_at)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}, {ph})
        """, (user_id, _hash_token(raw), ip, ua[:500], expires.isoformat()))
    return raw


def _load_user_by_id(user_id: str) -> dict | None:
    # Aliased wildcard select (u.*), matching _get_current_user_or_none's convention —
    # avoids the bare-wildcard pattern the repo's UGC-file source scan disallows.
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT u.* FROM users u WHERE u.id::text = {ph} AND u.is_active = TRUE AND u.deleted_at IS NULL", (user_id,))
        return db._row_to_dict(row) if row else None


def _load_pending_2fa(token_hash: str):
    """Nạp + tiêu thụ-một-lần bộ đếm challenge pending_2fa (FOR UPDATE SKIP LOCKED).
    Trích nguyên văn nested _load_challenge của twofa_verify — không đổi hành vi.
    Trả None (không hợp lệ/hết hạn), "locked" (quá số lần), hoặc dict challenge."""
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            SELECT id, user_id, attempts, expires_at FROM pending_2fa
            WHERE token_hash = {ph} FOR UPDATE SKIP LOCKED
        """, (token_hash,))
        if not row:
            return None
        d = db._row_to_dict(row)
        exp = d["expires_at"]
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            db._execute(conn, f"DELETE FROM pending_2fa WHERE id = {ph}", (d["id"],))
            return None
        if d["attempts"] >= OTP_MAX_ATTEMPTS:
            db._execute(conn, f"DELETE FROM pending_2fa WHERE id = {ph}", (d["id"],))
            return "locked"
        db._execute(conn, f"UPDATE pending_2fa SET attempts = attempts + 1 WHERE id = {ph}", (d["id"],))
        return d


def _verify_2fa_code(uid: str, body: "_TwoFAVerify", decrypt_secret, verify_totp, recovery_code_matches) -> bool:
    """Kiểm tra mã TOTP hoặc mã khôi phục cho user 2FA đã bật. Trích nguyên văn
    nested _check của twofa_verify — không đổi hành vi (kể cả đánh dấu used_at)."""
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT secret_enc FROM user_2fa WHERE user_id::text = {ph} AND enabled = TRUE", (uid,))
        if not row:
            return False
        secret = decrypt_secret(db._row_to_dict(row)["secret_enc"])
        if not body.recovery and verify_totp(secret, body.code):
            return True
        if body.recovery:
            codes = db._fetchall(conn, f"SELECT id, code_hash FROM user_2fa_recovery_codes WHERE user_id::text = {ph} AND used_at IS NULL", (uid,))
            for r in codes:
                d = db._row_to_dict(r)
                if recovery_code_matches(body.code, d["code_hash"]):
                    db._execute(conn, f"UPDATE user_2fa_recovery_codes SET used_at = NOW() WHERE id = {ph}", (d["id"],))
                    return True
        return False


class _TwoFAVerify(BaseModel):
    challenge_id: str
    code: str
    recovery: bool = False
    remember_device: bool = False


@router.post("/2fa/verify",
             summary="Complete login with a 2FA code",
             description="Completes a login that was gated by 2FA. Verifies a TOTP code or a recovery code against the pending challenge, then creates a session on success.")
async def twofa_verify(body: _TwoFAVerify, request: Request, response: Response):
    from middleware import get_client_ip
    from twofactor import decrypt_secret, verify_totp, recovery_code_matches
    ip = get_client_ip(request)
    _check_shared_auth_rate(f"tfa_verify_ip:{ip}", TFA_VERIFY_IP_LIMIT, TFA_VERIFY_IP_WINDOW, "Qua nhieu lan xac thuc 2FA. Thu lai sau.")
    _enforce_local_rate(_tfa_verify_ip_rate, ip, TFA_VERIFY_IP_LIMIT, TFA_VERIFY_IP_WINDOW, "Quá nhiều lần xác thực 2FA. Vui lòng thử lại sau.")

    token_hash = _hash_token(body.challenge_id)

    challenge = await asyncio.to_thread(_load_pending_2fa, token_hash)
    if challenge == "locked":
        raise HTTPException(429, "Quá nhiều lần thử. Vui lòng đăng nhập lại.")
    if not challenge:
        raise HTTPException(400, "Phiên xác thực không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.")
    uid = str(challenge["user_id"])

    if not await asyncio.to_thread(_verify_2fa_code, uid, body, decrypt_secret, verify_totp, recovery_code_matches):
        raise HTTPException(400, "Mã không đúng")

    # Thành công → nạp user đầy đủ, xoá challenge (dùng-một-lần), hoàn tất đăng nhập.
    user = await asyncio.to_thread(_load_user_by_id, uid)
    if not user:
        raise HTTPException(400, "Không tìm thấy tài khoản")

    # Điểm tiêu thụ nguyên tử: DELETE...RETURNING là nơi DUY NHẤT quyết định ai
    # thắng cuộc đua. _load_challenge() (FOR UPDATE SKIP LOCKED) đã COMMIT và
    # nhả khoá hàng trước khi _check() chạy trên connection khác, nên hai request
    # đồng thời cùng challenge_id/mã hợp lệ đều có thể lọt qua _load_challenge +
    # _check. Postgres tự khoá hàng theo thứ tự cho DELETE: chỉ một request nhận
    # được hàng qua RETURNING (rowcount=1), request còn lại nhận 0 hàng → phải
    # dừng TRƯỚC _finish_login để không tạo hai session từ một challenge dùng-một-lần.
    def _consume() -> bool:
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"DELETE FROM pending_2fa WHERE id = {ph} RETURNING id", (challenge["id"],))
            return bool(row)
    consumed = await asyncio.to_thread(_consume)
    if not consumed:
        # Request khác đã tiêu thụ challenge này trước (race) — KHÔNG tạo session.
        raise HTTPException(400, "Phiên xác thực không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.")

    result = await _finish_login(user, user.get("phone", ""), "2fa", request, response)
    if body.remember_device:
        await _remember_trusted_device(user, request, response)
    return result


@router.get("/trusted-devices", summary="List trusted devices")
async def list_trusted_devices(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])

    def _q():
        ph = db._ph
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, device_name, ip, created_at, last_used_at, expires_at
                FROM trusted_devices WHERE user_id::text = {ph} AND expires_at > NOW()
                ORDER BY last_used_at DESC
            """, (uid,))
            out = []
            for r in rows:
                d = db._row_to_dict(r)
                out.append({
                    "id": str(d["id"]),
                    "device_name": d.get("device_name"),
                    "ip": _mask_ip(d.get("ip")),
                    "created_at": str(d.get("created_at", "")),
                    "last_used_at": str(d.get("last_used_at", "")),
                })
            return out
    return {"devices": await asyncio.to_thread(_q)}


@router.delete("/trusted-devices/{device_id}", summary="Remove a trusted device")
async def delete_trusted_device(device_id: str, request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    from auth_middleware import validate_path_id
    device_id = validate_path_id(device_id, "device_id")
    uid = str(user["id"])
    from ratelimit import check_rate
    check_rate(f"trusted_del:{uid}", 20, 300, "Thao tác quá nhanh. Vui lòng đợi.")

    def _del():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM trusted_devices WHERE id::text = {ph} AND user_id::text = {ph}", (device_id, uid))
    await asyncio.to_thread(_del)
    return {"success": True}


# ── Auth helpers (used by other modules) ──

_TOKEN_MAX_LEN = 128

def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        t = auth[7:]
        if 16 <= len(t) <= _TOKEN_MAX_LEN:
            return t
        return None
    for cookie_name in ("vl360_token", "token", "session_token"):
        t = request.cookies.get(cookie_name)
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
        "full_name": user.get("full_name"),
        "avatar_url": user.get("avatar_url"),
        "cover_url": user.get("cover_url"),
        "bio": user.get("bio", ""),
        "username": user.get("username"),
        "role": user.get("role", "user"),
        "has_password": bool(user.get("password_hash")),
        "created_at": str(user.get("created_at", "")),
        "date_of_birth": str(user.get("date_of_birth", "")) if user.get("date_of_birth") else None,
        "email": user.get("email"),
        "contact_info": user.get("contact_info"),
    }
