# -*- coding: utf-8 -*-
"""Phủ trực tiếp verify_user_bound_token — trước đây chỉ được phủ gián tiếp
qua location_resolver/user_preferences; ghim các nhánh từ chối khi tách
_decode_signed_envelope (lát 3 trả nợ R20.8)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

import auth_middleware
from auth_middleware import generate_user_bound_token, verify_user_bound_token

NOW = 1_700_000_000


def _make(payload=None, *, purpose="p", user_id="u-1", expires_at=NOW + 300):
    return generate_user_bound_token(
        purpose, user_id, payload if payload is not None else {"k": "v"},
        expires_at=expires_at,
    )


def test_round_trip_returns_payload():
    token = _make({"region": "vinh-long"})
    assert verify_user_bound_token(token, "p", "u-1", now=NOW) == {
        "region": "vinh-long"
    }


def test_oversized_token_rejected():
    token = _make({"pad": "x" * 4000})
    assert len(token) > 2048
    assert verify_user_bound_token(token, "p", "u-1", now=NOW) is None


def test_wrong_dot_count_rejected():
    token = _make()
    assert verify_user_bound_token(token.replace(".", "", 1), "p", "u-1", now=NOW) is None
    assert verify_user_bound_token(token + ".extra", "p", "u-1", now=NOW) is None


def test_non_canonical_signature_encoding_rejected():
    # Cùng một chữ ký nhưng chuỗi hoá kèm padding '=' — decode ra y hệt,
    # so canonical phải từ chối (chống né so-chuỗi bằng biến thể base64).
    token = _make()
    encoded_text, signature_text = token.split(".", 1)
    padded = signature_text + "=" * (-len(signature_text) % 4)
    assert padded != signature_text
    assert verify_user_bound_token(f"{encoded_text}.{padded}", "p", "u-1", now=NOW) is None


def test_tampered_payload_rejected():
    token = _make()
    encoded_text, signature_text = token.split(".", 1)
    raw = base64.urlsafe_b64decode(encoded_text + "=" * (-len(encoded_text) % 4))
    envelope = json.loads(raw)
    envelope["user_id"] = "u-2"
    forged = base64.urlsafe_b64encode(
        json.dumps(envelope, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    ).rstrip(b"=")
    assert verify_user_bound_token(
        forged.decode() + "." + signature_text, "p", "u-2", now=NOW
    ) is None


def test_expired_wrong_purpose_wrong_user_rejected():
    token = _make()
    assert verify_user_bound_token(token, "p", "u-1", now=NOW + 300) is None
    assert verify_user_bound_token(token, "khac", "u-1", now=NOW) is None
    assert verify_user_bound_token(token, "p", "u-2", now=NOW) is None


def test_signed_non_dict_envelope_rejected():
    # Ký đúng bí mật nhưng envelope là list — verify phải trả None thay vì nổ.
    raw = json.dumps(["not", "a", "dict"]).encode()
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=")
    signature = hmac.new(
        auth_middleware._CSRF_SECRET.encode(), encoded, hashlib.sha256
    ).digest()
    token = (
        encoded.decode()
        + "."
        + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    )
    assert verify_user_bound_token(token, "p", "u-1", now=NOW) is None


def test_boolean_expires_at_rejected():
    # type(expires_at) is not int: bool là int-subclass nhưng type() chặn được.
    token = _make(expires_at=True)
    assert verify_user_bound_token(token, "p", "u-1", now=NOW) is None
