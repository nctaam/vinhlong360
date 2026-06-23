"""Unit tests cho P0 bảo mật (offline-safe — không cần PG/mạng).

Khoá logic thuần của: P0-6 (hash session token), P0-13 (SSRF guard). Các phần DB-bound
(comment moderation, login rate-limit qua request) phủ ở integration test (CI/PG).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException


# ── P0-6: session token hashing ──

def test_hash_token_deterministic_and_not_plaintext():
    from auth import _hash_token, _generate_token
    tok = _generate_token()
    h1 = _hash_token(tok)
    h2 = _hash_token(tok)
    assert h1 == h2                       # deterministic → lookup khớp
    assert h1 != tok                      # KHÔNG lưu plaintext
    assert len(h1) == 64                  # sha256 hex
    assert all(c in "0123456789abcdef" for c in h1)


def test_hash_token_distinct_inputs_distinct_hash():
    from auth import _hash_token, _generate_token
    assert _hash_token(_generate_token()) != _hash_token(_generate_token())


# ── P0-13: SSRF guard (_assert_public_url) ──

@pytest.mark.parametrize("bad_url", [
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata (link-local)
    "http://127.0.0.1/admin",                     # loopback
    "http://10.0.0.5/x",                          # private A
    "http://192.168.1.1/x",                       # private C
    "http://172.16.0.1/x",                        # private B
    "http://[::1]/x",                             # ipv6 loopback
    "ftp://example.com/x",                        # scheme sai
    "file:///etc/passwd",                         # scheme sai
    "notaurl",                                    # không host
    "",                                           # rỗng
])
def test_assert_public_url_rejects_internal_and_bad(bad_url):
    from admin import _assert_public_url
    with pytest.raises(HTTPException):
        _assert_public_url(bad_url)
