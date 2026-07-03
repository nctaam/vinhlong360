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
