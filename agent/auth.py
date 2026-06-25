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
from pydantic import BaseModel, field_validator

from database import db


def _require_pg():
    # GĐ3.1 (quyết định): UGC/auth chạy trên Postgres (dev/prod parity, đúng kiến trúc).
    # SQLite dev -> trả 503 rõ ràng thay vì crash 500.
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

# GĐ4.7: rate-limit theo IP (chống SMS-pump bằng cách xoay nhiều số điện thoại).
OTP_IP_LIMIT = 5          # tối đa 5 lần / cửa sổ
OTP_IP_WINDOW = 600       # 10 phút
_otp_ip_rate: dict[str, list[float]] = {}

# P0-15: rate-limit /login theo IP (chống brute-force mật khẩu — OTP đã có limit, login thì chưa).
LOGIN_IP_LIMIT = 10       # tối đa 10 lần / cửa sổ
LOGIN_IP_WINDOW = 300     # 5 phút
_login_ip_rate: dict[str, list[float]] = {}

LOGIN_PHONE_LIMIT = 5     # 5 sai → khoá phone 15 phút
LOGIN_PHONE_WINDOW = 900  # 15 phút
_login_phone_fails: dict[str, list[float]] = {}


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
    password: str
    current_password: str | None = None

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


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return base64.b64encode(salt + key).decode()


def _verify_password(password: str, stored: str) -> bool:
    decoded = base64.b64decode(stored)
    salt, stored_key = decoded[:16], decoded[16:]
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return hmac.compare_digest(key, stored_key)


async def _send_sms(phone: str, message: str) -> bool:
    """Send SMS via eSMS.vn API."""
    if not ESMS_API_KEY:
        print(f"[AUTH] DEV MODE — SMS to {phone}: {message}")
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
    except Exception as e:
        print(f"[AUTH] SMS send failed: {e}")
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

    _otp_rate[phone] = now

    code = _generate_otp()
    hashed = _hash_otp(code)
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO otp_sessions (phone, code, expires_at)
            VALUES ({db._ph}, {db._ph}, {db._ph})
        """, (phone, hashed, expires.isoformat()))

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
    phone = _normalize_phone(body.phone)
    hashed = _hash_otp(body.code.strip())

    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            SELECT * FROM otp_sessions
            WHERE phone = {db._ph} AND verified = FALSE
            ORDER BY created_at DESC LIMIT 1
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

    user = db.get_user_by_phone(phone)
    if not user:
        if not body.consent:
            raise HTTPException(400, "Vui lòng đồng ý Điều khoản sử dụng và Chính sách bảo mật")
        user = db.create_user(phone, consent_version=CONSENT_VERSION)
    elif not user.get("is_active", True):
        db.update_user(str(user["id"]), is_active=True)
        user["is_active"] = True

    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    from middleware import get_client_ip
    ip = get_client_ip(request)  # P1-19: IP thật (trusted-proxy), không phải IP proxy
    ua = request.headers.get("user-agent", "")

    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
        """, (str(user["id"]), _hash_token(token), ua, ip, expires.isoformat()))

    _log_login(phone, "otp", True, request, str(user["id"]))

    return {
        "success": True,
        "token": token,
        "user": _safe_user(user),
        "has_password": bool(user.get("password_hash")),
        "expires_at": expires.isoformat(),
    }


@router.post("/check-phone")
async def check_phone(body: CheckPhone):
    phone = _normalize_phone(body.phone)
    user = db.get_user_by_phone(phone)
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

    phone = _normalize_phone(body.phone)

    phone_hits = [t for t in _login_phone_fails.get(phone, []) if now - t < LOGIN_PHONE_WINDOW]
    if len(phone_hits) >= LOGIN_PHONE_LIMIT:
        raise HTTPException(429, "Tài khoản tạm khoá do đăng nhập sai nhiều lần. Thử lại sau 15 phút.")

    user = db.get_user_by_phone(phone)

    if not user or not user.get("password_hash"):
        phone_hits.append(now)
        _login_phone_fails[phone] = phone_hits
        _log_login(phone, "password", False, request)
        raise HTTPException(401, "Số điện thoại hoặc mật khẩu không đúng")

    if not user.get("is_active", True):
        _log_login(phone, "password", False, request, str(user["id"]))
        raise HTTPException(403, "Tài khoản đã bị vô hiệu hóa")

    if not _verify_password(body.password, user["password_hash"]):
        phone_hits.append(now)
        _login_phone_fails[phone] = phone_hits
        _log_login(phone, "password", False, request, str(user["id"]))
        raise HTTPException(401, "Số điện thoại hoặc mật khẩu không đúng")

    _login_phone_fails.pop(phone, None)

    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    ua = request.headers.get("user-agent", "")

    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
        """, (str(user["id"]), _hash_token(token), ua, ip, expires.isoformat()))

    _log_login(phone, "password", True, request, str(user["id"]))

    return {
        "success": True,
        "token": token,
        "user": _safe_user(user),
        "expires_at": expires.isoformat(),
    }


@router.post("/set-password")
async def set_password(body: SetPassword, request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")

    if user.get("password_hash"):
        if not body.current_password:
            raise HTTPException(400, "Vui lòng nhập mật khẩu hiện tại")
        if not _verify_password(body.current_password, user["password_hash"]):
            raise HTTPException(400, "Mật khẩu hiện tại không đúng")

    hashed = _hash_password(body.password)
    db.update_user(str(user["id"]), password_hash=hashed)

    # P1-9: đổi mật khẩu → thu hồi MỌI phiên khác (giữ phiên hiện tại), chống chiếm dụng.
    cur = _extract_token(request)
    cur_hash = _hash_token(cur) if cur else None
    with db._conn() as conn:
        if cur_hash:
            db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph} AND token != {db._ph}",
                        (str(user["id"]), cur_hash))
        else:
            db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}", (str(user["id"]),))

    return {"success": True, "message": "Đã đặt mật khẩu thành công"}


@router.post("/logout")
async def logout(request: Request):
    token = _extract_token(request)
    if not token:
        return {"success": True}
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM user_sessions WHERE token = {db._ph}", (_hash_token(token),))
    return {"success": True}


@router.get("/sessions")
async def list_sessions(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    cur_token = _extract_token(request)
    cur_hash = _hash_token(cur_token) if cur_token else None
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT id, user_agent, ip_address, created_at, expires_at, token
            FROM user_sessions
            WHERE user_id::text = {db._ph} AND expires_at > NOW()
            ORDER BY created_at DESC
        """, (str(user["id"]),))
    sessions = []
    for r in rows:
        rd = db._row_to_dict(r)
        sessions.append({
            "id": str(rd["id"]),
            "user_agent": rd.get("user_agent", ""),
            "ip_address": rd.get("ip_address", ""),
            "created_at": str(rd.get("created_at", "")),
            "expires_at": str(rd.get("expires_at", "")),
            "is_current": rd.get("token") == cur_hash,
        })
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    with db._conn() as conn:
        db._execute(conn, f"""
            DELETE FROM user_sessions
            WHERE id::text = {db._ph} AND user_id::text = {db._ph}
        """, (session_id, str(user["id"])))
    return {"success": True}


@router.get("/me")
async def get_me(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    return {"user": _safe_user(user)}


@router.post("/deactivate")
async def deactivate_account(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])
    db.update_user(uid, is_active=False)
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}", (uid,))
    return {"success": True, "message": "Tài khoản đã bị vô hiệu hóa. Đăng nhập lại bằng OTP để kích hoạt."}


@router.delete("/account")
async def delete_account(request: Request):
    # GĐ5.5: quyền xoá dữ liệu (PDPL). Xoá user -> FK ON DELETE CASCADE xoá posts/comments/
    # likes/bookmarks/follows/notifications/reports/sessions liên quan.
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM users WHERE id::text = {db._ph}", (uid,))
    return {"status": "deleted", "message": "Tài khoản và dữ liệu liên quan đã được xoá."}


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

    if fields:
        user = db.update_user(str(user["id"]), **fields)

    return {"user": _safe_user(user)}


@router.post("/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")

    from storage import storage, MAX_IMAGE_SIZE, sniff_image_type

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    if not sniff_image_type(data):
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")

    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "avatars", str(user["id"])[:8])
    except ValueError as e:
        raise HTTPException(400, f"Ảnh không hợp lệ: {e}")
    except Exception as e:
        raise HTTPException(500, f"Lỗi upload ảnh: {e}")

    avatar_url = urls.get("md") or urls.get("sm")
    db.update_user(str(user["id"]), avatar_url=avatar_url)
    return {"avatar_url": avatar_url, "sizes": urls}


@router.post("/cover")
async def upload_cover(request: Request, file: UploadFile = File(...)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")

    from storage import storage, MAX_IMAGE_SIZE, sniff_image_type

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"Ảnh quá lớn (tối đa {MAX_IMAGE_SIZE // 1024 // 1024}MB)")
    if not sniff_image_type(data):
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")

    try:
        urls = await run_in_threadpool(storage.upload_image_set, data, "covers", str(user["id"])[:8])
    except ValueError as e:
        raise HTTPException(400, f"Ảnh không hợp lệ: {e}")
    except Exception as e:
        raise HTTPException(500, f"Lỗi upload ảnh: {e}")

    cover_url = urls.get("lg") or urls.get("md")
    db.update_user(str(user["id"]), cover_url=cover_url)
    return {"cover_url": cover_url, "sizes": urls}


# ── Login history ──

def _log_login(phone: str, method: str, success: bool, request: Request, user_id: str | None = None):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
    ua = request.headers.get("user-agent", "")[:500]
    try:
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO login_history (user_id, phone, method, success, ip, user_agent)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (user_id, phone, method, success, ip, ua))
    except Exception:
        pass


@router.get("/login-history")
async def get_login_history(request: Request, limit: int = 20):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
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
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT * FROM user_privacy WHERE user_id = {ph}::uuid", (str(user["id"]),))
    if row:
        row = db._row_to_dict(row)
        return {"profile_visibility": row["profile_visibility"], "show_activity": row["show_activity"], "show_saved": row["show_saved"]}
    return {"profile_visibility": "public", "show_activity": True, "show_saved": True}


@router.put("/privacy")
async def update_privacy(body: PrivacyUpdate, request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")

    valid_vis = ("public", "followers", "private")
    if body.profile_visibility and body.profile_visibility not in valid_vis:
        raise HTTPException(400, f"profile_visibility phải là một trong: {', '.join(valid_vis)}")

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
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            SELECT u.* FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = {db._ph} AND s.expires_at > NOW() AND u.is_active = TRUE
        """, (_hash_token(token),))
        return db._row_to_dict(row)


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
        "role": user.get("role", "user"),
        "created_at": str(user.get("created_at", "")),
    }
