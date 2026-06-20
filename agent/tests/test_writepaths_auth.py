"""
B3 write-path coverage — AUTH (OTP / login / password / session).

Per CLAUDE.md §B3: auth.py is a 0%-test write-path that gates all UGC
(NĐ147 phone verification). This adds a safety net BEFORE any refactor.

Design (mirrors test_saved.py):
  - Fast: mount only auth.router on a bare FastAPI app, no full server import,
    no network (eSMS is only called on the real OTP path, which is PG-gated).
  - SQLite/CI: the router-level `Depends(_require_pg)` short-circuits every
    endpoint to 503 BEFORE the handler runs — that is the contract we assert.
  - Postgres: PG-only happy/validation paths run via skipif(not db._use_pg).
  - Pure helpers (phone normalization, password hash/verify, OTP hash) are
    backend-agnostic and always exercised.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

import auth  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="UGC/auth is Postgres-only (SQLite dev/CI returns 503). Set DATABASE_URL=postgresql://… to run.",
)


def _client():
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


# ── Router wiring ─────────────────────────────────────────────────────────

def test_auth_router_mounted():
    """All advertised auth write-paths are registered."""
    pairs = _route_pairs(_client().app)
    assert ("POST", "/auth/request-otp") in pairs
    assert ("POST", "/auth/verify-otp") in pairs
    assert ("POST", "/auth/login") in pairs
    assert ("POST", "/auth/set-password") in pairs
    assert ("POST", "/auth/logout") in pairs
    assert ("GET", "/auth/me") in pairs
    assert ("PUT", "/auth/profile") in pairs
    assert ("DELETE", "/auth/account") in pairs


# ── Postgres guard (deterministic on SQLite/CI) ───────────────────────────

def test_auth_pg_guard_on_sqlite():
    """SQLite dev/CI: the PG guard returns 503 before any handler/auth logic."""
    client = _client()
    if not db._use_pg:
        assert client.post("/auth/request-otp", json={"phone": "0901234567"}).status_code == 503
        assert client.post("/auth/verify-otp", json={"phone": "0901234567", "code": "123456"}).status_code == 503
        assert client.post("/auth/login", json={"phone": "0901234567", "password": "secret1"}).status_code == 503
        assert client.post("/auth/set-password", json={"password": "secret1"}).status_code == 503
        assert client.get("/auth/me").status_code == 503
    else:
        # Postgres: endpoints exist & enforce auth (not 404, not the 503 guard).
        assert client.get("/auth/me").status_code in (401, 403)


# ── Model validation (backend-agnostic) ───────────────────────────────────

class TestOTPRequestValidation:
    def test_valid_phone(self):
        assert auth.OTPRequest(phone="0901234567").phone == "0901234567"

    def test_intl_phone_normalized(self):
        assert auth.OTPRequest(phone="+84901234567").phone == "0901234567"

    def test_phone_strips_spaces_dashes(self):
        assert auth.OTPRequest(phone="090 123-4567").phone == "0901234567"

    def test_invalid_phone_rejected(self):
        with pytest.raises(ValidationError):
            auth.OTPRequest(phone="12345")

    def test_invalid_prefix_rejected(self):
        # leading digit after 0 must be 3/5/7/8/9
        with pytest.raises(ValidationError):
            auth.OTPRequest(phone="0123456789")


class TestSetPasswordValidation:
    def test_valid_password(self):
        assert auth.SetPassword(password="secret1").password == "secret1"

    def test_too_short_rejected(self):
        with pytest.raises(ValidationError):
            auth.SetPassword(password="123")


# ── Pure crypto/normalization helpers ─────────────────────────────────────

class TestAuthHelpers:
    def test_normalize_phone_intl(self):
        assert auth._normalize_phone("+84 901 234 567") == "0901234567"

    def test_password_hash_roundtrip(self):
        hashed = auth._hash_password("hunter22")
        assert auth._verify_password("hunter22", hashed) is True
        assert auth._verify_password("wrongpass", hashed) is False

    def test_password_hash_is_salted(self):
        # Two hashes of the same password must differ (random salt).
        assert auth._hash_password("samepw") != auth._hash_password("samepw")

    def test_otp_hash_deterministic(self):
        assert auth._hash_otp("123456") == auth._hash_otp("123456")
        assert auth._hash_otp("123456") != auth._hash_otp("654321")

    def test_generate_otp_shape(self):
        code = auth._generate_otp()
        assert len(code) == auth.OTP_LENGTH
        assert code.isdigit()


# ── Token extraction (used by every authed write-path) ─────────────────────

class TestTokenExtraction:
    def test_bearer_header(self):
        from starlette.requests import Request

        scope = {"type": "http", "headers": [(b"authorization", b"Bearer abc123")]}
        assert auth._extract_token(Request(scope)) == "abc123"

    def test_no_token_returns_none(self):
        from starlette.requests import Request

        scope = {"type": "http", "headers": []}
        assert auth._extract_token(Request(scope)) is None


# ── Postgres-only: rate limiting + auth-required state ─────────────────────

@pg_only
def test_request_otp_rate_limit_per_phone(monkeypatch):
    """A second OTP request for the same phone within the window returns 429."""
    monkeypatch.setitem(auth._otp_rate, "0909999999", __import__("time").time())
    client = _client()
    resp = client.post("/auth/request-otp", json={"phone": "0909999999"})
    assert resp.status_code == 429


@pg_only
def test_set_password_requires_auth():
    """set-password without a session token → 401 (not 503, PG is live)."""
    client = _client()
    resp = client.post("/auth/set-password", json={"password": "secret1"})
    assert resp.status_code == 401


@pg_only
def test_login_invalid_password_rejected():
    """Login with an unknown phone → 401 generic error (no user enumeration)."""
    client = _client()
    resp = client.post("/auth/login", json={"phone": "0900000001", "password": "nope123"})
    assert resp.status_code == 401
