"""Đợt 4 — HMAC webhook Zalo (B3 vùng mù). verify_zalo_signature là auth DUY NHẤT cho
endpoint public POST /webhook/zalo; trước chỉ có source-grep test. Test HÀNH VI: một
refactor bỏ prefix 'mac=' / đổi sang '==' / đảo nhánh empty-secret phải làm test đỏ.
"""
import hashlib
import hmac
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot_gateway import BotGateway  # noqa: E402


def _gw(secret: str = "") -> BotGateway:
    gw = BotGateway()
    gw._zalo_oa_secret = secret
    return gw


def _sign(secret: str, body: bytes) -> str:
    return "mac=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_accepted():
    secret, body = "s3cr3t-oa", b'{"event_name":"user_send_text"}'
    assert _gw(secret).verify_zalo_signature(body, _sign(secret, body)) is True


def test_wrong_signature_rejected():
    assert _gw("s3cr3t-oa").verify_zalo_signature(b'{"e":"x"}', "mac=deadbeef") is False


def test_tampered_body_rejected():
    secret = "s3cr3t-oa"
    good = _sign(secret, b'{"amount":10}')
    assert _gw(secret).verify_zalo_signature(b'{"amount":9999}', good) is False


def test_empty_signature_rejected():
    assert _gw("s3cr3t-oa").verify_zalo_signature(b'{}', "") is False


def test_missing_mac_prefix_rejected():
    secret = "s3cr3t-oa"
    raw_hex = hmac.new(secret.encode(), b'{}', hashlib.sha256).hexdigest()  # thiếu "mac="
    assert _gw(secret).verify_zalo_signature(b'{}', raw_hex) is False


def test_no_secret_configured_is_open():
    # Không cấu hình secret → open (behavior hiện tại, documented). Nếu ai đảo thành
    # trả False khi rỗng thì webhook dev sẽ vỡ — guard chủ ý.
    assert _gw("").verify_zalo_signature(b'{}', "anything") is True
