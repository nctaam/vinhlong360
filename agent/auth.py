"""
vinhlong360 — OTP SMS Authentication.

Endpoints:
  POST /auth/request-otp  — gửi OTP qua SMS (eSMS.vn)
  POST /auth/verify-otp   — xác minh OTP, tạo session
  POST /auth/logout        — hủy session
  GET  /auth/me            — thông tin user hiện tại

Tuân thủ NĐ 147/2024: xác thực SĐT VN trước khi cho đăng bài/bình luận.
"""

import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
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


class OTPVerify(BaseModel):
    phone: str
    code: str

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

    # GĐ4.7: chặn SMS-pump theo IP (xoay nhiều số). XFF lấy IP gốc nếu sau proxy.
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "unknown"))
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

    return {
        "success": True,
        "message": "OTP đã được gửi" if sent else "Không gửi được SMS, thử lại sau",
        "expires_in": OTP_EXPIRE_MINUTES * 60,
        "dev_code": code if not ESMS_API_KEY else None,
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
        user = db.create_user(phone)

    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")

    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
        """, (str(user["id"]), token, ua, ip, expires.isoformat()))

    return {
        "success": True,
        "token": token,
        "user": _safe_user(user),
        "expires_at": expires.isoformat(),
    }


@router.post("/logout")
async def logout(request: Request):
    token = _extract_token(request)
    if not token:
        return {"success": True}
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM user_sessions WHERE token = {db._ph}", (token,))
    return {"success": True}


@router.get("/me")
async def get_me(request: Request):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    return {"user": _safe_user(user)}


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
        fields["display_name"] = name
    if body.bio is not None:
        fields["bio"] = body.bio.strip()[:300]

    if fields:
        user = db.update_user(str(user["id"]), **fields)

    return {"user": _safe_user(user)}


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
        """, (token,))
        return db._row_to_dict(row)


def _safe_user(user: dict) -> dict:
    if not user:
        return None
    return {
        "id": str(user["id"]),
        "phone": user["phone"][:3] + "****" + user["phone"][-3:],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "bio": user.get("bio", ""),
        "role": user.get("role", "user"),
        "created_at": str(user.get("created_at", "")),
    }
