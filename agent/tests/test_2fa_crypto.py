"""Đợt 4 — 2FA crypto primitives (B3 vùng mù). Trước chỉ có inspect.getsource test.
Test HÀNH VI thật: TOTP verify, encrypt/decrypt roundtrip, recovery hash single-use base.
Một refactor làm hỏng crypto (sai window, mã hoá không roundtrip, hash match nhầm code)
phải làm test này đỏ.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyotp  # noqa: E402
import twofactor  # noqa: E402


def test_generate_secret_verifies_with_current_totp():
    secret = twofactor.generate_secret()
    assert twofactor.verify_totp(secret, pyotp.TOTP(secret).now()) is True


def test_verify_totp_rejects_wrong_code():
    secret = twofactor.generate_secret()
    real = pyotp.TOTP(secret).now()
    wrong = "000000" if real != "000000" else "111111"
    assert twofactor.verify_totp(secret, wrong) is False


def test_encrypt_decrypt_secret_roundtrip():
    secret = twofactor.generate_secret()
    token = twofactor.encrypt_secret(secret)
    assert token != secret            # thực sự đã mã hoá (không lưu plaintext)
    assert twofactor.decrypt_secret(token) == secret


def test_generate_recovery_codes_unique_count():
    codes = twofactor.generate_recovery_codes(8)
    assert len(codes) == 8
    assert len(set(codes)) == 8       # không trùng


def test_recovery_code_hash_matches_only_correct_code():
    codes = twofactor.generate_recovery_codes(4)
    h = twofactor.hash_recovery_code(codes[0])
    assert twofactor.recovery_code_matches(codes[0], h) is True
    assert twofactor.recovery_code_matches(codes[1], h) is False
    assert twofactor.recovery_code_matches("wrong-code", h) is False
