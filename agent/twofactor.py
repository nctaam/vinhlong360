"""Two-factor authentication (TOTP) primitives — Wave 4.

Bí mật TOTP được MÃ HOÁ (Fernet) khi lưu, KHÔNG hash (cần giải mã để verify).
Khoá Fernet dẫn xuất từ bí mật ứng dụng sẵn có (không cần secret mới) qua HKDF,
có thể override bằng env TOTP_ENC_KEY (một Fernet key hợp lệ).
Mã khôi phục thì HASH (SHA-256), dùng-một-lần.

Ghi chú attr app-secret (đã xác nhận qua agent/config.py):
- `SECRET_KEY`, `SESSION_SECRET`, `AUTH_SECRET` KHÔNG tồn tại trong Settings.
- `JWT_SECRET` tồn tại nhưng default "" và bị SKIP khỏi validate_production_keys
  (config.py dòng ~133: "not yet used by any endpoint") -> có thể rỗng ở prod.
- `ADMIN_API_KEY` tồn tại VÀ bắt buộc non-empty ở production (validate_production_keys).
  Dùng làm secret ổn định fallback khi JWT_SECRET chưa được set.
Thứ tự ưu tiên: TOTP_ENC_KEY (env override) > JWT_SECRET (nếu có) > ADMIN_API_KEY
(bắt buộc ở prod) > dev fallback cố định (KHÔNG dùng ở prod).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

import pyotp
import qrcode
import qrcode.image.pil
from io import BytesIO
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_ISSUER = "vinhlong360"


def _app_secret() -> bytes:
    """Bí mật ổn định để dẫn xuất khoá mã hoá TOTP. Ưu tiên TOTP_ENC_KEY;
    nếu không có, dẫn xuất từ bí mật app sẵn có (JWT_SECRET rồi ADMIN_API_KEY —
    xem docstring module để biết vì sao); dev fallback cố định nếu không có gì."""
    override = os.environ.get("TOTP_ENC_KEY")
    if override:
        return override.encode()
    # Dùng lại bí mật app sẵn có (KHÔNG tạo secret mới).
    try:
        from config import settings as _cfg  # noqa
        for attr in ("JWT_SECRET", "ADMIN_API_KEY"):
            val = getattr(_cfg, attr, None)
            if val:
                return str(val).encode()
    except Exception:  # noqa: BLE001
        pass
    # Dev-only fallback (cảnh báo: prod PHẢI đặt TOTP_ENC_KEY hoặc bí mật app).
    return b"vl360-dev-totp-fallback-do-not-use-in-prod"


def _fernet() -> Fernet:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32,
                salt=b"vl360-totp-v1", info=b"totp-secret-encryption")
    key = hkdf.derive(_app_secret())
    return Fernet(base64.urlsafe_b64encode(key))


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=_ISSUER)


def qr_data_uri(otpauth_uri: str) -> str:
    img = qrcode.make(otpauth_uri, image_factory=qrcode.image.pil.PilImage)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def verify_totp(secret: str, code: str) -> bool:
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def generate_recovery_codes(n: int = 8) -> list[str]:
    # 10 hex chars, groups of 5 for readability: "a1b2c-3d4e5"
    out = []
    for _ in range(n):
        raw = secrets.token_hex(5)  # 10 hex chars
        out.append(f"{raw[:5]}-{raw[5:]}")
    return out


def hash_recovery_code(code: str) -> str:
    normalized = (code or "").strip().lower().replace("-", "")
    return hashlib.sha256(normalized.encode()).hexdigest()


def recovery_code_matches(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_recovery_code(code), code_hash)
