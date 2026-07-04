# Wave 4: 2FA + Security Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add TOTP-based two-factor authentication (setup wizard, login challenge, recovery codes), trusted-device management, and suspicious-login alerts to the vinhlong360 auth system.

**Architecture:** New `agent/twofactor.py` module (TOTP wrappers via `pyotp`, Fernet encryption of the secret at rest, recovery-code + pending-challenge + trusted-device helpers) backed by two additive migrations (066: `user_2fa` + `user_2fa_recovery_codes` + `pending_2fa`; 067: `trusted_devices`). A shared `_finish_login` helper in `auth.py` centralizes session creation; the 2FA gate is injected once there. Enrollment/management/verify endpoints live on the existing `/auth` router. Frontend adds a `'twofactor'` login step (`AuthModal.vue` + `useAuth.ts`) and a settings security-tab wizard + trusted-device list (`cai-dat.vue`).

**Tech Stack:** FastAPI (backend), Nuxt 4 SSR / Vue 3 (frontend), PostgreSQL, `pyotp` + `qrcode` (both pure-Python, free), `cryptography` (already a dependency).

## Global Constraints

- **DB pattern:** `with db._conn() as conn:`, `db._ph`, `db._fetchone/_fetchall/_execute`, `db._row_to_dict`. Sync DB helpers wrapped in `await asyncio.to_thread(...)` from async endpoints.
- **Auth router:** `router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(_require_pg)])` at `auth.py:60`. New endpoints add to this existing router — NO server.py change needed. Every `/auth/*` route already 503s on non-Postgres.
- **CSRF:** `_csrf=Depends(_require_csrf_lazy)` on mutating endpoints called by a **logged-in** user (enable/disable 2FA, delete trusted device) — matches `set_password` (auth.py:749). The pending-2FA **verify** endpoint (caller not yet fully authenticated, authenticated by the challenge token) does NOT use CSRF — matches `verify_otp`/`login_password`.
- **Migrations:** additive only (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`). Runner blocks `DROP/TRUNCATE/DELETE`. New tables get `ALTER TABLE <t> OWNER TO vl360;` after `CREATE TABLE`. Exact `schema_version` footer (component 'agent'). **Do NOT bump `PG_REQUIRED_SCHEMA_VERSION` (database.py:90, stays 62)** — convention; 063/064/065 did not bump it. Next numbers: **066, 067**.
- **Token primitives:** `_generate_token()` = `secrets.token_urlsafe(48)` (auth.py:374); `_hash_token(t)` = `hashlib.sha256(t.encode()).hexdigest()` (auth.py:378). Use these for the pending-2FA challenge token and the trusted-device token (store the HASH, return the RAW to the client), mirroring `user_sessions.token`.
- **TOTP secret at rest:** MUST be **encrypted** (Fernet), NOT hashed — it must be decryptable to verify codes. Recovery codes ARE hashed (SHA-256, single-use). Never log or return a stored secret except the one-time setup display.
- **Rate limiting:** two-layer, mirror `verify_otp` (auth.py:512-526): `_check_shared_auth_rate(key, limit, window, msg)` (PG-backed) + a local in-process dict guard (`_gc_rate_dict`). Attempt-cap per challenge row (mirror `OTP_MAX_ATTEMPTS = 5`).
- **`create_notification`:** `create_notification(user_id, notif_type, title, body=None, ref_type=None, ref_id=None, actor_id=None)` (notifications.py:390) — sync, wrap in `asyncio.to_thread`. For `security_alert`: pass NO `actor_id`; leave `"security_alert"` OUT of `_NOTIF_TYPE_TO_PREF` so it's always delivered (security alerts are non-suppressible; `_user_wants_notif` returns True for unmapped types).
- **`get_client_ip(request)`** from `middleware.py` (import inline). UA: `request.headers.get("user-agent", "")[:500]`.
- **`update_user` allowlist caveat:** `db.update_user` (database.py:1480) silently no-ops for fields outside its allowlist. All 2FA state lives in dedicated tables written via raw `db._execute` helpers in `twofactor.py` — do NOT route 2FA writes through `update_user`.
- **Cookies:** session cookie `vl360_token` (HttpOnly, SameSite=Lax, Secure+Domain=.vinhlong360.vn in prod). Trusted-device cookie is a NEW cookie `vl360_trusted` with its own `_set_/_clear_` helpers reusing `get_secure_cookie_params(is_production=...)` (auth_middleware.py:1062) with a longer `max_age` (90 days).
- **CSP:** `img-src 'self' data: https:` (backend build_csp + nginx) already allows `data:` — QR renders via `<img :src="dataUri">`, no CSP change, no `v-html`.
- **FE auth:** `useAuth()` → `authHeaders()` (carries CSRF). Settings-tab fetches use `$fetch(url, { headers: authHeaders(), ... })` WITHOUT `credentials:'include'` (same-origin proxy). 401 handling: `if (getStatusCode(e) === 401) { handleSessionExpired(); return }` else `showToast(extractErrorMessage(e, '...'), 'error')`.
- **FE tokens/patterns:** `.settings-card.card` blocks (auto-spaced via `.settings-card + .settings-card`), `.sf-field`/`.sf-label`/`.sf-input`/`.sf-error`, `.btn.btn-primary/.btn-ghost/.btn-sm/.btn-danger-text`, `.sessions-list`/`.session-item`/`.session-info` (clone for trusted devices), `.otp-input` (global, reuse for TOTP box). `useToast().show(msg, type)`. Copy: `navigator.clipboard.writeText`. Download: Blob + `a.download`.
- **Test pattern:** new `agent/tests/test_wave4.py`, mirroring `test_wave3.py` — combine (1) route-mount smoke tests (`FastAPI()` + `include_router(auth.router)` + `TestClient`, assert `(METHOD, path)` in routes), (2) `inspect.getsource()` wiring assertions (no DB), (3) pure-logic tests for `twofactor.py` (encrypt/decrypt round-trip, TOTP verify with a known secret, recovery-code format). `pg_only = pytest.mark.skipif(not db._use_pg, ...)` for any DB happy-path. FE tasks verify via `cd web-nuxt && npm run build`.
- **Security discipline:** constant-time compares (`hmac.compare_digest`) for codes; never leak whether a phone/user has 2FA before password/OTP is verified; the challenge token is single-factor-bound (only valid after primary auth passed). Deploying/rotating the real TOTP encryption key is a §4 owner action — the code reads it from config with a dev-safe fallback; do NOT set a production secret in these tasks.

---

### Task 1: Migrations + Dependencies + TOTP Crypto Foundation

**Files:**
- Modify: `requirements.txt` (add `pyotp`, `qrcode`)
- Create: `agent/migrations/066_two_factor_auth.sql`
- Create: `agent/migrations/067_trusted_devices.sql`
- Create: `agent/twofactor.py` (crypto + TOTP + recovery-code pure helpers)
- Test: `agent/tests/test_wave4.py` (new; `TestTwoFactorCrypto`)

**Interfaces:**
- Produces:
  - `twofactor.generate_secret() -> str` (base32 TOTP secret)
  - `twofactor.provisioning_uri(secret: str, account: str) -> str` (otpauth:// URI)
  - `twofactor.qr_data_uri(otpauth_uri: str) -> str` (`data:image/png;base64,...`)
  - `twofactor.verify_totp(secret: str, code: str) -> bool` (±1 step window)
  - `twofactor.encrypt_secret(secret: str) -> str` / `twofactor.decrypt_secret(token: str) -> str` (Fernet)
  - `twofactor.generate_recovery_codes(n: int = 8) -> list[str]` and `hash_recovery_code(code: str) -> str`

- [ ] **Step 1: Add dependencies**

Append to `requirements.txt` (after the `# Dev / Testing` block, matching the `>=` style):

```
# Wave 4: 2FA (TOTP) — pure-Python, no paid services
pyotp>=2.9
qrcode>=7.4
```

(Install locally: `pip install "pyotp>=2.9" "qrcode>=7.4"`. `qrcode` uses the already-present `Pillow>=10.0` for PNG.)

- [ ] **Step 2: Write migration 066**

```sql
-- agent/migrations/066_two_factor_auth.sql
-- Migration 066: xác thực 2 bước (TOTP) — Wave 4 W4.1/W4.2/W4.3.
-- user_2fa: secret MÃ HOÁ (Fernet, KHÔNG hash — cần giải mã để verify) + cờ enabled.
-- user_2fa_recovery_codes: mã khôi phục HASH (SHA-256), dùng-một-lần qua used_at.
-- pending_2fa: thử thách nửa-đăng-nhập (mirror otp_sessions) — token_hash, hết hạn 5 phút.
-- Additive.

CREATE TABLE IF NOT EXISTS user_2fa (
    user_id      UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    secret_enc   TEXT NOT NULL,              -- Fernet-encrypted TOTP secret
    enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at  TIMESTAMPTZ
);
ALTER TABLE user_2fa OWNER TO vl360;

CREATE TABLE IF NOT EXISTS user_2fa_recovery_codes (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash  TEXT NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE user_2fa_recovery_codes OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_recovery_codes_user ON user_2fa_recovery_codes(user_id);

CREATE TABLE IF NOT EXISTS pending_2fa (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,
    ip         TEXT,
    user_agent TEXT,
    attempts   INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE pending_2fa OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_pending_2fa_token ON pending_2fa(token_hash);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 66, '066_two_factor_auth.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
```

- [ ] **Step 3: Write migration 067**

```sql
-- agent/migrations/067_trusted_devices.sql
-- Migration 067: thiết bị tin cậy — Wave 4 W4.5. token opaque (hash lưu, raw gửi cookie),
-- bỏ qua 2FA khi cookie khớp hàng chưa hết hạn. Tự hết hạn qua expires_at.
-- Additive.

CREATE TABLE IF NOT EXISTS trusted_devices (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   TEXT UNIQUE NOT NULL,
    device_name  TEXT,
    ip           TEXT,
    user_agent   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL
);
ALTER TABLE trusted_devices OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_trusted_devices_token ON trusted_devices(token_hash);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_user ON trusted_devices(user_id);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 67, '067_trusted_devices.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
```

- [ ] **Step 4: Write the crypto/TOTP test**

```python
# agent/tests/test_wave4.py
import inspect
import pytest

import twofactor


class TestTwoFactorCrypto:
    def test_generate_secret_is_base32(self):
        s = twofactor.generate_secret()
        assert isinstance(s, str) and len(s) >= 16
        # base32 alphabet
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in s)

    def test_encrypt_decrypt_roundtrip(self):
        s = twofactor.generate_secret()
        enc = twofactor.encrypt_secret(s)
        assert enc != s  # actually encrypted
        assert twofactor.decrypt_secret(enc) == s

    def test_verify_totp_accepts_current_code(self):
        import pyotp
        s = twofactor.generate_secret()
        code = pyotp.TOTP(s).now()
        assert twofactor.verify_totp(s, code) is True

    def test_verify_totp_rejects_wrong_code(self):
        s = twofactor.generate_secret()
        assert twofactor.verify_totp(s, "000000") is False or twofactor.verify_totp(s, "123456") is False

    def test_provisioning_uri_shape(self):
        uri = twofactor.provisioning_uri("JBSWY3DPEHPK3PXP", "0901234567")
        assert uri.startswith("otpauth://totp/")
        assert "secret=" in uri

    def test_qr_data_uri_is_png(self):
        uri = twofactor.qr_data_uri("otpauth://totp/x?secret=JBSWY3DPEHPK3PXP")
        assert uri.startswith("data:image/png;base64,")

    def test_recovery_codes_generated_and_hashed(self):
        codes = twofactor.generate_recovery_codes(8)
        assert len(codes) == 8
        assert len(set(codes)) == 8  # unique
        h = twofactor.hash_recovery_code(codes[0])
        assert h != codes[0] and len(h) == 64  # sha256 hex
```

- [ ] **Step 5: Run test → RED**

Run: `python -m pytest agent/tests/test_wave4.py::TestTwoFactorCrypto -v`
Expected: FAIL — `import twofactor` fails.

- [ ] **Step 6: Implement `agent/twofactor.py`**

```python
"""Two-factor authentication (TOTP) primitives — Wave 4.

Bí mật TOTP được MÃ HOÁ (Fernet) khi lưu, KHÔNG hash (cần giải mã để verify).
Khoá Fernet dẫn xuất từ bí mật ứng dụng sẵn có (không cần secret mới) qua HKDF,
có thể override bằng env TOTP_ENC_KEY (một Fernet key hợp lệ).
Mã khôi phục thì HASH (SHA-256), dùng-một-lần.
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
    nếu không có, dẫn xuất từ bí mật session/app sẵn có; dev fallback cố định."""
    override = os.environ.get("TOTP_ENC_KEY")
    if override:
        return override.encode()
    # Dùng lại bí mật app sẵn có (KHÔNG tạo secret mới). Xác nhận tên attr trong config.
    try:
        from config import settings as _cfg  # noqa
        for attr in ("SECRET_KEY", "SESSION_SECRET", "JWT_SECRET", "AUTH_SECRET"):
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
```

Note: the implementer MUST confirm the actual app-secret attribute name in `agent/config.py` and adjust the `for attr in (...)` list (or the whole `_app_secret` strategy) so a stable key is used in production. If none exists, report as a concern.

- [ ] **Step 7: Run test → GREEN + full suite**

Run: `python -m pytest agent/tests/test_wave4.py::TestTwoFactorCrypto -v` → PASS
Run: `python -m pytest -q -p no:randomly` → 34 baseline failures unchanged (deterministic; default pytest-randomly inflates via order-flakes)

- [ ] **Step 8: Commit**

```bash
git add requirements.txt agent/migrations/066_two_factor_auth.sql agent/migrations/067_trusted_devices.sql agent/twofactor.py agent/tests/test_wave4.py
git commit -m "feat(auth): 2FA foundation — migrations 066/067 + twofactor.py (pyotp+Fernet)"
```

---

### Task 2: 2FA Enrollment Endpoints

**Files:**
- Modify: `agent/auth.py` (DB helpers + 4 endpoints)
- Test: `agent/tests/test_wave4.py` (`TestTwoFactorEnrollment`)

**Interfaces:**
- Consumes: `twofactor.*`, `_get_current_user_or_none`, `_require_csrf_lazy`, `db._execute/_fetchone`.
- Produces:
  - `POST /auth/2fa/setup` → `{secret, otpauth_uri, qr}` (creates a disabled `user_2fa` row)
  - `POST /auth/2fa/verify-setup` (body: `{code}`) → `{success, recovery_codes: [...]}` (enables, one-time codes)
  - `POST /auth/2fa/disable` (body: `{code}`) → `{success}` (requires a valid TOTP or recovery code)
  - `GET /auth/2fa/status` → `{enabled, recovery_remaining}`
  - Helpers: `_get_2fa_row(user_id)`, `_2fa_is_enabled(user_id)`.

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave4.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
import auth


def _routes():
    app = FastAPI(); app.include_router(auth.router)
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


class TestTwoFactorEnrollment:
    def test_setup_route_mounted(self):
        assert ("POST", "/auth/2fa/setup") in _routes()

    def test_verify_setup_route_mounted(self):
        assert ("POST", "/auth/2fa/verify-setup") in _routes()

    def test_disable_route_mounted(self):
        assert ("POST", "/auth/2fa/disable") in _routes()

    def test_status_route_mounted(self):
        assert ("GET", "/auth/2fa/status") in _routes()

    def test_setup_stores_encrypted_secret(self):
        src = inspect.getsource(auth.twofa_setup)
        assert "encrypt_secret" in src
        assert "enabled" in src  # inserted disabled

    def test_verify_setup_enables_and_returns_recovery(self):
        src = inspect.getsource(auth.twofa_verify_setup)
        assert "verify_totp" in src
        assert "generate_recovery_codes" in src
        assert "hash_recovery_code" in src

    def test_disable_requires_code(self):
        src = inspect.getsource(auth.twofa_disable)
        assert "verify_totp" in src or "recovery_code_matches" in src

    def test_enrollment_endpoints_require_csrf(self):
        for fn in (auth.twofa_setup, auth.twofa_verify_setup, auth.twofa_disable):
            assert "_require_csrf_lazy" in inspect.getsource(fn)
```

- [ ] **Step 2: Run test → RED**

Run: `python -m pytest agent/tests/test_wave4.py::TestTwoFactorEnrollment -v` → FAIL (endpoints don't exist).

- [ ] **Step 3: Add DB helpers + endpoints to `auth.py`**

Add helpers near the other module-level DB helpers, and endpoints on the existing `router`. Add `import twofactor` at the top of auth.py (or inline in each function, matching the file's inline-import convention — prefer inline `from twofactor import ...` inside functions if that's the file's style; confirm).

```python
def _get_2fa_row(user_id: str) -> dict | None:
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT user_id, secret_enc, enabled FROM user_2fa WHERE user_id::text = {ph}", (user_id,))
        return db._row_to_dict(row) if row else None


def _2fa_is_enabled(user_id: str) -> bool:
    row = _get_2fa_row(user_id)
    return bool(row and row.get("enabled"))


@router.post("/2fa/setup", summary="Begin 2FA enrollment")
async def twofa_setup(request: Request, _csrf=Depends(_require_csrf_lazy)):
    from twofactor import generate_secret, provisioning_uri, qr_data_uri, encrypt_secret
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])
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


@router.post("/2fa/verify-setup", summary="Confirm 2FA enrollment")
async def twofa_verify_setup(body: _TwoFACode, request: Request, _csrf=Depends(_require_csrf_lazy)):
    from twofactor import decrypt_secret, verify_totp, generate_recovery_codes, hash_recovery_code
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])
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


@router.post("/2fa/disable", summary="Disable 2FA")
async def twofa_disable(body: _TwoFACode, request: Request, _csrf=Depends(_require_csrf_lazy)):
    from twofactor import decrypt_secret, verify_totp, recovery_code_matches
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    uid = str(user["id"])
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
```

(Confirm `BaseModel` is already imported in auth.py — it is, used by `OTPVerify`/`PasswordLogin`. Confirm `db._fetchall` exists — it does.)

- [ ] **Step 4: Run tests + full suite**

Run: `python -m pytest agent/tests/test_wave4.py -v` → PASS
Run: `python -m pytest -q -p no:randomly` → baseline unchanged

- [ ] **Step 5: Commit**

```bash
git add agent/tests/test_wave4.py
git add -p agent/auth.py
git commit -m "feat(auth): 2FA enrollment endpoints — setup/verify-setup/disable/status"
```

---

### Task 3: Login-Flow 2FA Gate + Pending Challenge + Verify Endpoint

**Files:**
- Modify: `agent/auth.py` (`_finish_login` refactor; gate in `verify_otp` + `login_password`; pending-2FA helpers; `POST /auth/2fa/verify`; add pending_2fa cleanup)
- Test: `agent/tests/test_wave4.py` (`TestTwoFactorLoginGate`)

**Interfaces:**
- Consumes: `_create_session_atomic`, `_generate_token`, `_hash_token`, `_set_session_cookie`, `_log_login`, `_update_login_streak`, `twofactor.*`, `_2fa_is_enabled`.
- Produces:
  - `_finish_login(user, phone, method, request, response) -> dict` (the existing session-creation sequence, extracted)
  - Gate: `verify_otp`/`login_password` return `{two_factor_required: True, challenge_id: <raw>}` when 2FA enabled.
  - `POST /auth/2fa/verify` (body: `{challenge_id, code, recovery?: bool, remember_device?: bool}`) → same success shape as login.
  - Pending helpers: `_create_pending_2fa(user_id, ip, ua) -> str` (raw token), `_consume_pending_2fa(raw_token) -> user_id|None`.

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave4.py

class TestTwoFactorLoginGate:
    def test_verify_route_mounted(self):
        assert ("POST", "/auth/2fa/verify") in _routes()

    def test_finish_login_helper_exists(self):
        assert callable(auth._finish_login)

    def test_verify_otp_uses_2fa_gate(self):
        src = inspect.getsource(auth.verify_otp)
        assert "_2fa_is_enabled" in src
        assert "two_factor_required" in src

    def test_login_password_uses_2fa_gate(self):
        src = inspect.getsource(auth.login_password)
        assert "_2fa_is_enabled" in src
        assert "two_factor_required" in src

    def test_both_login_paths_use_finish_login(self):
        assert "_finish_login" in inspect.getsource(auth.verify_otp)
        assert "_finish_login" in inspect.getsource(auth.login_password)

    def test_pending_challenge_hashed_and_expiring(self):
        src = inspect.getsource(auth._create_pending_2fa)
        assert "_hash_token" in src
        assert "expires_at" in src

    def test_verify_endpoint_rate_limited_and_attempt_capped(self):
        src = inspect.getsource(auth.twofa_verify)
        assert "_check_shared_auth_rate" in src or "check_rate" in src
        assert "attempts" in src

    def test_verify_supports_recovery_and_remember(self):
        src = inspect.getsource(auth.twofa_verify)
        assert "recovery" in src
        assert "remember_device" in src or "trusted" in src

    def test_pending_2fa_cleanup_registered(self):
        assert "pending_2fa" in inspect.getsource(auth.cleanup_expired_data)
```

- [ ] **Step 2: Run test → RED**

Run: `python -m pytest agent/tests/test_wave4.py::TestTwoFactorLoginGate -v` → FAIL.

- [ ] **Step 3: Extract `_finish_login` and inject the gate**

First extract the shared session-finalize sequence into a helper (both `verify_otp` ~608-631 and `login_password` ~721-743 currently duplicate it). Add near the session helpers:

```python
async def _finish_login(user: dict, phone: str, method: str, request: Request, response: Response) -> dict:
    """Tạo session + cookie + log + streak + achievement; trả về response đăng nhập.
    Dùng chung cho verify_otp/login_password và /2fa/verify."""
    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    from middleware import get_client_ip
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")[:500]
    await asyncio.to_thread(_create_session_atomic, str(user["id"]), _hash_token(token), ua, ip, expires.isoformat())
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
    return {"success": True, "token": token, "user": _safe_user(user),
            "has_password": bool(user.get("password_hash")), "expires_at": expires.isoformat()}
```

(Delete the `_finish_login_sync`/`_FakeReqForLog` stub above — it's illustrative only; use the async `_finish_login` which has the real `request`. The implementer replaces the duplicated blocks in both endpoints with `return await _finish_login(user, phone, "otp"|"password", request, response)`, but ONLY after the 2FA gate — see next.)

**Inject the gate** — in `verify_otp`, replace the block starting at `token = _generate_token()` (line ~599) with:

```python
    if _2fa_is_enabled(str(user["id"])):
        from middleware import get_client_ip
        ip = get_client_ip(request)
        ua = request.headers.get("user-agent", "")[:500]
        # Bỏ qua nếu thiết bị tin cậy (Task 4 sẽ chèn kiểm tra cookie ở đây).
        challenge = await asyncio.to_thread(_create_pending_2fa, str(user["id"]), ip, ua)
        await asyncio.to_thread(_log_login, phone, "otp", True, request, str(user["id"]))
        return {"two_factor_required": True, "challenge_id": challenge}
    if body.consent:
        from middleware import get_client_ip
        await asyncio.to_thread(_log_consent, str(user["id"]), CONSENT_VERSION, get_client_ip(request))
    return await _finish_login(user, phone, "otp", request, response)
```

Same pattern in `login_password` (after `_login_phone_fails.pop`, line ~715):

```python
    if _2fa_is_enabled(str(user["id"])):
        from middleware import get_client_ip
        ip = get_client_ip(request)
        ua = request.headers.get("user-agent", "")[:500]
        challenge = await asyncio.to_thread(_create_pending_2fa, str(user["id"]), ip, ua)
        await asyncio.to_thread(_log_login, phone, "password", True, request, str(user["id"]))
        return {"two_factor_required": True, "challenge_id": challenge}
    return await _finish_login(user, phone, "password", request, response)
```

(The implementer must preserve `verify_otp`'s existing consent-logging — fold it into `_finish_login` or keep it before the call as shown. `_finish_login`'s response omits nothing the old `verify_otp` returned; `login_password`'s old response lacked `has_password` — adding it is harmless/beneficial, note it.)

- [ ] **Step 4: Pending-2FA helpers + verify endpoint + rate limits + cleanup**

```python
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


class _TwoFAVerify(BaseModel):
    challenge_id: str
    code: str
    recovery: bool = False
    remember_device: bool = False


@router.post("/2fa/verify", summary="Complete login with a 2FA code")
async def twofa_verify(body: _TwoFAVerify, request: Request, response: Response):
    from middleware import get_client_ip
    from twofactor import decrypt_secret, verify_totp, recovery_code_matches
    ip = get_client_ip(request)
    now = time.time()
    _check_shared_auth_rate(f"tfa_verify_ip:{ip}", TFA_VERIFY_IP_LIMIT, TFA_VERIFY_IP_WINDOW, "Qua nhieu lan xac thuc 2FA. Thu lai sau.")
    hits = [t for t in _tfa_verify_ip_rate.get(ip, []) if now - t < TFA_VERIFY_IP_WINDOW]
    if len(hits) >= TFA_VERIFY_IP_LIMIT:
        raise HTTPException(429, "Quá nhiều lần xác thực 2FA. Vui lòng thử lại sau.")
    hits.append(now); _tfa_verify_ip_rate[ip] = hits; _gc_rate_dict(_tfa_verify_ip_rate, TFA_VERIFY_IP_WINDOW)

    token_hash = _hash_token(body.challenge_id)

    def _load_challenge():
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
    challenge = await asyncio.to_thread(_load_challenge)
    if challenge == "locked":
        raise HTTPException(429, "Quá nhiều lần thử. Vui lòng đăng nhập lại.")
    if not challenge:
        raise HTTPException(400, "Phiên xác thực không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.")
    uid = str(challenge["user_id"])

    def _check() -> bool:
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
    if not await asyncio.to_thread(_check):
        raise HTTPException(400, "Mã không đúng")

    # Thành công → nạp user đầy đủ, xoá challenge, hoàn tất đăng nhập.
    user = await asyncio.to_thread(_load_user_by_id, uid)
    if not user:
        raise HTTPException(400, "Không tìm thấy tài khoản")

    def _consume():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM pending_2fa WHERE id = {ph}", (challenge["id"],))
    await asyncio.to_thread(_consume)

    result = await _finish_login(user, user.get("phone", ""), "2fa", request, response)
    # body.remember_device: được HONORED ở Task 4 (ghi trusted_devices + set cookie). Inert ở Task 3.
    return result


def _load_user_by_id(user_id: str) -> dict | None:
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT * FROM users WHERE id::text = {ph} AND is_active = TRUE AND deleted_at IS NULL", (user_id,))
        return db._row_to_dict(row) if row else None
```

(Task 3 accepts `remember_device` in the body but does NOT act on it — Task 4 adds the `_remember_trusted_device` call here. Do NOT reference `_remember_trusted_device` in Task 3, it doesn't exist yet. Document this hand-off in the report.)

Add pending_2fa cleanup to `cleanup_expired_data` (auth.py:166-189):

```python
            db._execute(conn, "DELETE FROM pending_2fa WHERE expires_at < NOW()")
```

- [ ] **Step 5: Run tests + full suite**

Run: `python -m pytest agent/tests/test_wave4.py -v` → PASS
Run: `python -m pytest -q -p no:randomly` → baseline unchanged. **Manually confirm the existing auth login tests in `test_session_be.py` still pass** (this task refactors the hottest auth paths): `python -m pytest agent/tests/test_session_be.py -q -p no:randomly`.

- [ ] **Step 6: Commit**

```bash
git add agent/tests/test_wave4.py
git add -p agent/auth.py
git commit -m "feat(auth): 2FA login gate — _finish_login refactor + pending challenge + /2fa/verify"
```

---

### Task 4: Trusted Devices (skip 2FA + management)

**Files:**
- Modify: `agent/auth.py` (trusted-device cookie helpers, remember + skip-check, list/delete endpoints, cleanup)
- Test: `agent/tests/test_wave4.py` (`TestTrustedDevices`)

**Interfaces:**
- Consumes: `_generate_token`, `_hash_token`, `get_secure_cookie_params`, `_2fa_is_enabled`.
- Produces:
  - `_remember_trusted_device(user, request, response)` — writes a `trusted_devices` row + sets `vl360_trusted` cookie (90 days).
  - `_has_valid_trusted_device(user_id, request) -> bool` — checks the cookie against unexpired rows (updates last_used_at).
  - Modifies the gate in `verify_otp`/`login_password` to skip the challenge when `_has_valid_trusted_device`.
  - `GET /auth/trusted-devices` → `{devices: [...]}`; `DELETE /auth/trusted-devices/{id}` (CSRF'd).
  - trusted_devices cleanup in `cleanup_expired_data`.

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave4.py

class TestTrustedDevices:
    def test_list_route_mounted(self):
        assert ("GET", "/auth/trusted-devices") in _routes()

    def test_delete_route_mounted(self):
        pairs = _routes()
        assert any(m == "DELETE" and p.startswith("/auth/trusted-devices/") for (m, p) in pairs)

    def test_remember_hashes_token_and_sets_cookie(self):
        src = inspect.getsource(auth._remember_trusted_device)
        assert "_hash_token" in src
        assert "vl360_trusted" in src or "set_cookie" in src

    def test_skip_check_updates_last_used(self):
        src = inspect.getsource(auth._has_valid_trusted_device)
        assert "expires_at" in src
        assert "last_used_at" in src

    def test_login_gate_checks_trusted_device(self):
        assert "_has_valid_trusted_device" in inspect.getsource(auth.verify_otp)
        assert "_has_valid_trusted_device" in inspect.getsource(auth.login_password)

    def test_delete_requires_csrf(self):
        assert "_require_csrf_lazy" in inspect.getsource(auth.delete_trusted_device)

    def test_trusted_cleanup_registered(self):
        assert "trusted_devices" in inspect.getsource(auth.cleanup_expired_data)
```

- [ ] **Step 2: Run test → RED**

Run: `python -m pytest agent/tests/test_wave4.py::TestTrustedDevices -v` → FAIL.

- [ ] **Step 3: Implement helpers + endpoints; wire the skip-check into the gate**

```python
TRUSTED_DEVICE_COOKIE_NAME = "vl360_trusted"
TRUSTED_DEVICE_DAYS = 90


def _trusted_cookie_params(request: Request) -> dict:
    from auth_middleware import get_secure_cookie_params
    is_prod = _request_is_production(request)
    params = get_secure_cookie_params(is_production=is_prod)
    params["max_age"] = TRUSTED_DEVICE_DAYS * 86400
    host = (request.headers.get("host") or request.url.hostname or "").split(":")[0].lower()
    if not is_prod and (host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")):
        params.pop("domain", None); params.pop("secure", None)
    return params


async def _remember_trusted_device(user: dict, request: Request, response: Response):
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


def _short_ua(ua: str) -> str:
    # crude device label from UA; keep it simple
    ua = ua or ""
    for tok in ("iPhone", "iPad", "Android", "Windows", "Macintosh", "Linux"):
        if tok in ua:
            return tok
    return "Thiết bị"
```

Wire the **skip-check into the gate** in both `verify_otp` and `login_password` — change the gate condition to also check trusted device:

```python
    if _2fa_is_enabled(str(user["id"])) and not await asyncio.to_thread(_has_valid_trusted_device, str(user["id"]), request):
        # ... create pending challenge, return two_factor_required ...
```

Also **wire `remember_device` into `/2fa/verify`** (Task 3 left it inert) — in `twofa_verify`, replace the `# body.remember_device ... Inert` comment with the real call, right before `return result`:

```python
    result = await _finish_login(user, user.get("phone", ""), "2fa", request, response)
    if body.remember_device:
        await _remember_trusted_device(user, request, response)
    return result
```

Add the management endpoints:

```python
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
            return [{"id": str(db._row_to_dict(r)["id"]),
                     "device_name": db._row_to_dict(r).get("device_name"),
                     "ip": _mask_ip(db._row_to_dict(r).get("ip")),
                     "last_used_at": str(db._row_to_dict(r).get("last_used_at", ""))} for r in rows]
    return {"devices": await asyncio.to_thread(_q)}


@router.delete("/trusted-devices/{device_id}", summary="Remove a trusted device")
async def delete_trusted_device(device_id: str, request: Request, _csrf=Depends(_require_csrf_lazy)):
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Chưa đăng nhập")
    device_id = validate_path_id(device_id, "device_id")
    uid = str(user["id"])

    def _del():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM trusted_devices WHERE id::text = {ph} AND user_id::text = {ph}", (device_id, uid))
    await asyncio.to_thread(_del)
    return {"success": True}
```

Add trusted_devices cleanup to `cleanup_expired_data`:

```python
            db._execute(conn, "DELETE FROM trusted_devices WHERE expires_at < NOW()")
```

(Confirm `validate_path_id` is imported in auth.py; if not, use the auth_middleware import. Confirm `_mask_ip` exists — it does, auth.py:198.)

- [ ] **Step 4: Run tests + full suite + auth regression**

Run: `python -m pytest agent/tests/test_wave4.py -v` → PASS
Run: `python -m pytest agent/tests/test_session_be.py -q -p no:randomly` → still green
Run: `python -m pytest -q -p no:randomly` → baseline unchanged

- [ ] **Step 5: Commit**

```bash
git add agent/tests/test_wave4.py
git add -p agent/auth.py
git commit -m "feat(auth): trusted devices — remember-me cookie skips 2FA + list/delete management"
```

---

### Task 5: Suspicious Login Alert (W4.4)

**Files:**
- Modify: `agent/auth.py` (`_check_suspicious_login` helper + hook into both login success paths)
- Test: `agent/tests/test_wave4.py` (`TestSuspiciousLogin`)

**Interfaces:**
- Consumes: `login_history` (read), `create_notification`, `get_client_ip`.
- Produces: `_check_suspicious_login(user_id, ip, ua, display_name)` — if no prior successful login from this IP or UA in 90 days, create a `security_alert` notification (fire-and-forget).

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave4.py

class TestSuspiciousLogin:
    def test_helper_exists_and_queries_history(self):
        src = inspect.getsource(auth._check_suspicious_login)
        assert "login_history" in src
        assert "create_notification" in src
        assert "security_alert" in src

    def test_helper_swallows_errors(self):
        src = inspect.getsource(auth._check_suspicious_login)
        assert "except" in src

    def test_no_actor_id_passed(self):
        # security_alert must NOT pass actor_id (no social actor)
        src = inspect.getsource(auth._check_suspicious_login)
        assert "actor_id" not in src

    def test_hooked_in_finish_login(self):
        # single hook site: _finish_login (covers direct logins + post-2FA logins)
        assert "_check_suspicious_login" in inspect.getsource(auth._finish_login)
```

- [ ] **Step 2: Run test → RED**

- [ ] **Step 3: Implement + hook**

```python
def _check_suspicious_login(user_id: str, ip: str, ua: str, display_name: str = ""):
    """Nếu IP+UA này chưa từng đăng nhập thành công (90 ngày) → thông báo bảo mật.
    Fire-and-forget, nuốt lỗi. KHÔNG truyền actor_id (không có 'người thực hiện')."""
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
            return  # known device/network
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
```

Hook it at a **single site: `_finish_login`** — which both `verify_otp` and `login_password` call on a completed login (direct, or after a successful `/2fa/verify`). This alerts on every completed login without double-firing. Add after the `_log_login` line in `_finish_login` (from Task 3):

```python
    from middleware import get_client_ip
    _ip = get_client_ip(request); _ua = request.headers.get("user-agent", "")[:500]
    asyncio.create_task(asyncio.to_thread(_check_suspicious_login, str(user["id"]), _ip, _ua, user.get("display_name") or ""))
```

(The test `test_hooked_in_finish_login` asserts the helper appears in `_finish_login`'s source. Do NOT hook it separately in `verify_otp`/`login_password` — that would double-fire the alert on the 2FA path.)

- [ ] **Step 4: Run tests + full suite**

Run: `python -m pytest agent/tests/test_wave4.py -v` → PASS
Run: `python -m pytest -q -p no:randomly` → baseline unchanged

- [ ] **Step 5: Commit**

```bash
git add agent/tests/test_wave4.py
git add -p agent/auth.py
git commit -m "feat(auth): suspicious-login alert — notify on login from a new device/IP"
```

---

### Task 6: 2FA Login Flow FE

**Files:**
- Modify: `web-nuxt/composables/useAuth.ts` (`twoFactorChallenge` state + `verifyTwoFactor` + branch in `login`/`verifyOtp`)
- Modify: `web-nuxt/components/AuthModal.vue` (`'twofactor'` step)
- Test: build verification

**Interfaces:**
- Consumes: `POST /auth/2fa/verify` → `{token?, user?, error?}` (or `{two_factor_required, challenge_id}` from login/verify-otp).
- Produces: a login modal that, on `two_factor_required`, shows a TOTP code step (with a "use recovery code" toggle and a "remember this device" checkbox) and completes login.

- [ ] **Step 1: Extend `useAuth.ts`**

Add state + function (per the exploration's exact seam — the `if (res.user || res.token)` gate). Update the return types of `login`/`verifyOtp` to include `two_factor_required?: boolean; challenge_id?: string` and set the challenge on that branch:

```ts
const twoFactorChallenge = useState<{ challenge_id: string } | null>('auth-2fa-challenge', () => null)

// inside login() and verifyOtp(), change the response type and add BEFORE the (res.user||res.token) block:
//   if ((res as any).two_factor_required && (res as any).challenge_id) {
//     twoFactorChallenge.value = { challenge_id: (res as any).challenge_id }; return res
//   }

async function verifyTwoFactor(challengeId: string, code: string, opts?: { recovery?: boolean; remember_device?: boolean }) {
  const res = await $fetch<{ token?: string; user?: User; error?: string }>('/auth/2fa/verify', {
    method: 'POST', credentials: 'include',
    body: { challenge_id: challengeId, code, recovery: opts?.recovery ?? false, remember_device: opts?.remember_device ?? false },
  })
  if (res.user || res.token) {
    user.value = res.user || null
    twoFactorChallenge.value = null
    if (!user.value || typeof user.value.has_password !== 'boolean') await fetchMe()
    else await fetchCsrf()
  }
  return res
}
```

Add `twoFactorChallenge` and `verifyTwoFactor` to the exported object (useAuth.ts:176).

- [ ] **Step 2: Add the `'twofactor'` step to `AuthModal.vue`**

- Extend the `step` union (line 222) with `'twofactor'`.
- In `handleLogin()` (line 361) and `verifyCode()` (line 405), where `step.value = 'done'` is set on success, first branch: if the login/verify response has `two_factor_required`, set `challengeId.value = res.challenge_id` and `step.value = 'twofactor'` instead.
- Add refs: `const challengeId = ref(''); const totpDigits = ref<string[]>(['','','','','','']); const totpRefs: HTMLInputElement[] = []; const useRecovery = ref(false); const recoveryCode = ref(''); const rememberDevice = ref(false)`.
- Add `verifyTwoFactorCode()`:

```ts
async function verifyTwoFactorCode() {
  const code = useRecovery.value ? recoveryCode.value.trim() : totpDigits.value.join('')
  if (!code) { error.value = 'Vui lòng nhập mã'; return }
  sending.value = true; error.value = ''
  try {
    const res = await verifyTwoFactor(challengeId.value, code, { recovery: useRecovery.value, remember_device: rememberDevice.value })
    if (res.error) error.value = res.error
    else step.value = 'done'
  } catch (e: unknown) {
    error.value = (e as any).data?.detail || 'Mã không đúng'
  } finally { sending.value = false }
}
```

- Template block (after the `'otp'` block), reusing `.otp-input` (6 boxes wired to `onOtpInput`/`onOtpKeydown`/`onOtpPaste` generalized to `totpDigits`/`totpRefs`, OR a single `.sf-input maxlength=6`) plus a recovery toggle + remember checkbox:

```html
<div v-else-if="step === 'twofactor'" class="otp-step">
  <h3 tabindex="-1">Xác thực 2 bước</h3>
  <template v-if="!useRecovery">
    <p>Nhập mã 6 chữ số từ ứng dụng xác thực.</p>
    <input v-model="totpCode" type="text" inputmode="numeric" maxlength="6" autocomplete="one-time-code"
           class="sf-input" aria-label="Mã 2FA" @keyup.enter="verifyTwoFactorCode" />
  </template>
  <template v-else>
    <p>Nhập một mã khôi phục.</p>
    <input v-model="recoveryCode" type="text" class="sf-input" aria-label="Mã khôi phục" @keyup.enter="verifyTwoFactorCode" />
  </template>
  <label class="remember-row"><input v-model="rememberDevice" type="checkbox" /> Tin cậy thiết bị này 90 ngày</label>
  <p v-if="error" class="form-error" role="alert">{{ error }}</p>
  <button type="button" class="btn btn-primary btn-full" :disabled="sending" @click="verifyTwoFactorCode">
    {{ sending ? 'Đang xác minh…' : 'Xác nhận' }}
  </button>
  <button type="button" class="otp-resend" @click="useRecovery = !useRecovery">
    {{ useRecovery ? 'Dùng mã từ ứng dụng' : 'Dùng mã khôi phục' }}
  </button>
</div>
```

(Simpler single `totpCode` ref rather than 6-box for the wizard is fine — use `const totpCode = ref('')`. Add all new refs to `close()`'s reset block, line 262-282. Add `'twofactor'` branch to `modalTitle`, line 255. Destructure `verifyTwoFactor` from `useAuth()` at the top of AuthModal's script.)

- [ ] **Step 3: Build verification**

Run: `cd C:/Code/vinhlong360/web-nuxt && npm run build` → passes.

- [ ] **Step 4: Commit**

```bash
git add -p web-nuxt/composables/useAuth.ts web-nuxt/components/AuthModal.vue
git commit -m "feat(auth): 2FA login step — TOTP/recovery code + remember-device in AuthModal"
```

---

### Task 7: 2FA + Trusted-Devices Settings FE

**Files:**
- Modify: `web-nuxt/pages/cai-dat.vue` (security tab: 2FA wizard + status + trusted-devices list)
- Test: build verification

**Interfaces:**
- Consumes: `GET /auth/2fa/status`, `POST /auth/2fa/setup`, `POST /auth/2fa/verify-setup`, `POST /auth/2fa/disable`, `GET /auth/trusted-devices`, `DELETE /auth/trusted-devices/{id}`.
- Produces: a "Xác thực 2 bước" `.settings-card` (enable wizard: QR + code → recovery codes display/download; disable form) + a "Thiết bị tin cậy" `.settings-card` (clone of the sessions list).

- [ ] **Step 1: Add 2FA state + loaders (script)**

Follow cai-dat.vue's exact fetch/error conventions (Global Constraints). Add to `lazyLoadTab('bao-mat')` (line ~479): `load2FAStatus(); loadTrustedDevices()`.

```ts
const twoFA = ref<{ enabled: boolean; recovery_remaining: number }>({ enabled: false, recovery_remaining: 0 })
const twoFALoading = ref(true)
const setupData = ref<{ secret: string; otpauth_uri: string; qr: string } | null>(null)
const setupCode = ref('')
const recoveryCodes = ref<string[]>([])
const disableCode = ref('')
const trustedDevices = ref<any[]>([])

async function load2FAStatus() {
  twoFALoading.value = true
  try {
    twoFA.value = await $fetch('/auth/2fa/status', { headers: authHeaders() })
  } catch { /* ignore */ }
  twoFALoading.value = false
}
async function begin2FASetup() {
  try { setupData.value = await $fetch('/auth/2fa/setup', { method: 'POST', headers: authHeaders() }) }
  catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast(extractErrorMessage(e, 'Không thể bắt đầu thiết lập'), 'error') }
}
async function confirm2FASetup() {
  try {
    const res = await $fetch<{ recovery_codes: string[] }>('/auth/2fa/verify-setup', { method: 'POST', headers: authHeaders(), body: { code: setupCode.value } })
    recoveryCodes.value = res.recovery_codes || []
    setupData.value = null; setupCode.value = ''
    showToast('Đã bật xác thực 2 bước', 'success')
    await load2FAStatus()
  } catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast(extractErrorMessage(e, 'Mã không đúng'), 'error') }
}
async function disable2FA() {
  try {
    await $fetch('/auth/2fa/disable', { method: 'POST', headers: authHeaders(), body: { code: disableCode.value } })
    disableCode.value = ''; recoveryCodes.value = []
    showToast('Đã tắt xác thực 2 bước', 'success')
    await load2FAStatus(); await loadTrustedDevices()
  } catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast(extractErrorMessage(e, 'Mã không đúng'), 'error') }
}
async function loadTrustedDevices() {
  try { const r = await $fetch<{ devices: any[] }>('/auth/trusted-devices', { headers: authHeaders() }); trustedDevices.value = r.devices || [] }
  catch { /* ignore */ }
}
async function removeTrustedDevice(id: string) {
  try {
    await $fetch(`/auth/trusted-devices/${encodeURIComponent(id)}`, { method: 'DELETE', headers: authHeaders() })
    trustedDevices.value = trustedDevices.value.filter(d => d.id !== id)
    showToast('Đã xoá thiết bị', 'success')
  } catch (e: unknown) { if (getStatusCode(e) === 401) { handleSessionExpired(); return } showToast('Không thể xoá thiết bị', 'error') }
}
function copyRecoveryCodes() {
  navigator.clipboard.writeText(recoveryCodes.value.join('\n')).then(() => showToast('Đã sao chép mã khôi phục', 'success')).catch(() => showToast('Không thể sao chép', 'error'))
}
function downloadRecoveryCodes() {
  const blob = new Blob([recoveryCodes.value.join('\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob); const a = document.createElement('a')
  a.href = url; a.download = 'vinhlong360-recovery-codes.txt'; a.click(); URL.revokeObjectURL(url)
}
```

- [ ] **Step 2: Add the two `.settings-card` blocks (template, inside the `bao-mat` panel ~183)**

```html
<div class="settings-card card">
  <h2>Xác thực 2 bước (2FA)</h2>
  <div v-if="twoFALoading" class="sf-loading" role="status"><div class="spinner spinner-sm"></div> Đang tải...</div>
  <template v-else-if="recoveryCodes.length">
    <p class="sf-hint">Lưu các mã khôi phục này ở nơi an toàn — mỗi mã dùng một lần khi mất thiết bị.</p>
    <ul class="recovery-list"><li v-for="c in recoveryCodes" :key="c"><code>{{ c }}</code></li></ul>
    <div class="rc-actions">
      <button type="button" class="btn btn-secondary btn-sm" @click="copyRecoveryCodes">Sao chép</button>
      <button type="button" class="btn btn-secondary btn-sm" @click="downloadRecoveryCodes">Tải xuống</button>
      <button type="button" class="btn btn-ghost btn-sm" @click="recoveryCodes = []">Đã lưu, đóng</button>
    </div>
  </template>
  <template v-else-if="twoFA.enabled">
    <p class="sf-hint">✅ Đã bật. Còn {{ twoFA.recovery_remaining }} mã khôi phục.</p>
    <label class="sf-field">
      <span class="sf-label">Nhập mã để tắt 2FA</span>
      <input v-model="disableCode" type="text" inputmode="numeric" class="sf-input" placeholder="Mã 6 số hoặc mã khôi phục" />
    </label>
    <button type="button" class="btn btn-danger-text btn-sm" @click="disable2FA">Tắt xác thực 2 bước</button>
  </template>
  <template v-else-if="setupData">
    <p class="sf-hint">Quét mã QR bằng Google Authenticator / Authy, rồi nhập mã 6 số.</p>
    <img :src="setupData.qr" alt="QR 2FA" class="qr-img" width="180" height="180" />
    <p class="sf-hint">Hoặc nhập khoá thủ công: <code>{{ setupData.secret }}</code></p>
    <label class="sf-field">
      <span class="sf-label">Mã xác nhận</span>
      <input v-model="setupCode" type="text" inputmode="numeric" maxlength="6" class="sf-input" />
    </label>
    <button type="button" class="btn btn-primary btn-sm" @click="confirm2FASetup">Xác nhận &amp; bật</button>
  </template>
  <template v-else>
    <p class="sf-hint">Thêm một lớp bảo vệ: yêu cầu mã từ ứng dụng xác thực khi đăng nhập.</p>
    <button type="button" class="btn btn-primary btn-sm" @click="begin2FASetup">Bật xác thực 2 bước</button>
  </template>
</div>

<div v-if="twoFA.enabled" class="settings-card card">
  <h2>Thiết bị tin cậy</h2>
  <div v-if="trustedDevices.length" class="sessions-list">
    <div v-for="d in trustedDevices" :key="d.id" class="session-item">
      <div class="session-info">
        <span class="session-ua">{{ d.device_name || 'Thiết bị' }}</span>
        <span class="sf-hint">{{ d.ip }} &middot; {{ timeAgo(d.last_used_at) }}</span>
      </div>
      <button type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="removeTrustedDevice(d.id)">Xoá</button>
    </div>
  </div>
  <p v-else class="sf-hint">Chưa có thiết bị tin cậy nào.</p>
</div>
```

- [ ] **Step 3: Add minimal CSS (scoped)**

```css
.recovery-list { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-1); margin: var(--space-2) 0; }
.recovery-list code { font-size: var(--text-sm); letter-spacing: 0.05em; }
.rc-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.qr-img { display: block; margin: var(--space-2) 0; border-radius: var(--radius-sm); background: #fff; padding: var(--space-2); }
.remember-row { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); margin: var(--space-2) 0; }
```

- [ ] **Step 4: Build verification**

Run: `cd C:/Code/vinhlong360/web-nuxt && npm run build` → passes.

- [ ] **Step 5: Commit**

```bash
git add -p web-nuxt/pages/cai-dat.vue
git commit -m "feat(auth): 2FA settings — enable wizard (QR+recovery codes) + trusted-devices list"
```

---

### Task 8: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Install deps + run pytest**

Run: `pip install "pyotp>=2.9" "qrcode>=7.4"` (if not already)
Run: `python -m pytest -q -p no:randomly`
Expected: 34 baseline failures unchanged + all `test_wave4.py` classes pass.

- [ ] **Step 2: Nuxt build**

Run: `cd web-nuxt && npm run build` → passes.

- [ ] **Step 3: Routes registered**

Run (from `agent/`, PG-off env — routes still register even when the router 503s at call time):
```python
import auth
from fastapi import FastAPI
app = FastAPI(); app.include_router(auth.router)
pairs = {(m, r.path) for r in app.routes for m in (getattr(r, "methods", None) or set())}
for t in [("POST","/auth/2fa/setup"),("POST","/auth/2fa/verify-setup"),("POST","/auth/2fa/disable"),
          ("GET","/auth/2fa/status"),("POST","/auth/2fa/verify"),("GET","/auth/trusted-devices")]:
    assert t in pairs, t
print("routes OK")
```

- [ ] **Step 4: Migrations + schema-version guard**

Run: `ls agent/migrations/066_two_factor_auth.sql agent/migrations/067_trusted_devices.sql`
Run: `python -c "import sys; sys.path.insert(0,'agent'); import database; assert database.PG_REQUIRED_SCHEMA_VERSION == 62"`

- [ ] **Step 5: Security self-check**

- Confirm `twofactor.py` never logs/returns a decrypted secret except `/2fa/setup`'s one-time response.
- Confirm the TOTP secret column is `secret_enc` (encrypted), never a plaintext `secret`.
- Confirm `/2fa/verify` is attempt-capped + rate-limited and the pending row is consumed on success.
- Confirm `security_alert` is NOT in `_NOTIF_TYPE_TO_PREF` (always delivered).

- [ ] **Step 6: Mark complete**

---

## Notes for the Executor

- **Task order:** 1 (crypto/schema) → 2 (enrollment) → 3 (login gate; `remember_device` accepted-but-inert) → 4 (trusted devices; implements `_remember_trusted_device` + skip-check, wires the gate) → 5 (suspicious login) → 6 (login FE) → 7 (settings FE) → 8 (verify). Tasks 3 & 4 both edit the gate in `verify_otp`/`login_password` — Task 4 layers the trusted-device skip onto Task 3's gate.
- **The Task 3 code block contains deliberately-messy scaffolding** (`_consume_and_user`, a `lambda ... if False`) marking intent — the implementer MUST write it cleanly: load the full user by id (`_load_user_by_id`), delete the pending row, then `await _finish_login(...)`. Do not ship the scaffolding.
- **Do NOT apply migrations to prod or set the real `TOTP_ENC_KEY`** (§4 owner action). Migrations are created + committed; the code reads the encryption key from config/app-secret with a dev fallback. Flag in the final report that production must ensure a stable app secret (or `TOTP_ENC_KEY`) is set, else 2FA secrets become undecryptable across a secret change.
- **Confirm the app-secret attribute** name in `agent/config.py` for `twofactor._app_secret()` (Task 1). If no stable secret exists, report it — it's a prerequisite for safe at-rest encryption.
- **Pre-existing dirty branch:** `auth.py`, `useAuth.ts`, `AuthModal.vue`, `cai-dat.vue` may carry unrelated uncommitted work. Every task stages ONLY its own hunks (`git add -p` / hunk extraction) and verifies `git diff --cached` before committing.
- **This wave refactors the hottest auth paths** (`verify_otp`/`login_password`). After Tasks 3-5, always run `python -m pytest agent/tests/test_session_be.py -q -p no:randomly` to confirm no auth-login regression, in addition to the wave-4 tests.
- **No local Postgres:** `twofactor.py` pure functions (crypto/TOTP/recovery) ARE unit-testable without a DB and should be genuinely executed in tests; endpoint tests are route-mount + `inspect.getsource()` wiring assertions (the `test_wave3.py` convention).
