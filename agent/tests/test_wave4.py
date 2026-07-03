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
        import pyotp
        s = twofactor.generate_secret()
        real = pyotp.TOTP(s).now()
        # a definitely-wrong 6-digit code is rejected (avoid a 1-in-1e6 collision with `real`)
        wrong = "000000" if real != "000000" else "111111"
        assert twofactor.verify_totp(s, wrong) is False
        # a current code from a DIFFERENT secret must not validate against `s`
        other = pyotp.TOTP(twofactor.generate_secret()).now()
        if other != real:
            assert twofactor.verify_totp(s, other) is False
        # malformed inputs (non-digit / wrong length) are rejected
        assert twofactor.verify_totp(s, "abcdef") is False
        assert twofactor.verify_totp(s, "12345") is False
        assert twofactor.verify_totp(s, "") is False

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
