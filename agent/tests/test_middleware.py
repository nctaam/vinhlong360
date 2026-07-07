"""
Tests for middleware.py — rate limiting, logging, IP handling.
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import middleware
from middleware import RateLimiter, get_client_ip, verify_admin_key, generate_request_id, _is_valid_ip


class TestRateLimiter:
    """Test sliding window rate limiter."""

    def test_allows_within_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            allowed, info = limiter.is_allowed("test-ip")
            assert allowed is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("test-ip")
        allowed, info = limiter.is_allowed("test-ip")
        assert allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] > 0

    def test_different_keys_independent(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("ip-1")
        limiter.is_allowed("ip-1")
        # ip-1 is at limit
        allowed, _ = limiter.is_allowed("ip-1")
        assert allowed is False
        # ip-2 should still be allowed
        allowed, _ = limiter.is_allowed("ip-2")
        assert allowed is True

    def test_remaining_decreases(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        _, info = limiter.is_allowed("test")
        assert info["remaining"] == 4
        _, info = limiter.is_allowed("test")
        assert info["remaining"] == 3

    def test_cleanup(self):
        limiter = RateLimiter(max_requests=10, window_seconds=1)
        limiter.is_allowed("old-ip")
        time.sleep(1.1)  # Wait for window to expire
        limiter.cleanup()
        stats = limiter.stats()
        assert stats["active_keys"] == 0

    def test_stats(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        limiter.is_allowed("ip-1")
        limiter.is_allowed("ip-2")
        stats = limiter.stats()
        assert stats["active_keys"] == 2
        assert stats["max_requests"] == 10
        assert stats["window_seconds"] == 60


class TestIPValidation:
    """Test IP address validation and extraction."""

    def test_valid_ipv4(self):
        assert _is_valid_ip("192.168.1.1") is True

    def test_valid_ipv6(self):
        assert _is_valid_ip("::1") is True

    def test_invalid_ip(self):
        assert _is_valid_ip("not-an-ip") is False

    def test_empty_string(self):
        assert _is_valid_ip("") is False

    def test_none(self):
        assert _is_valid_ip(None) is False


class TestGetClientIP:
    """Test client IP extraction with proxy validation."""

    def _mock_request(self, host="1.2.3.4", forwarded_for=None, real_ip=None):
        req = MagicMock()
        req.client.host = host
        headers = {}
        if forwarded_for:
            headers["X-Forwarded-For"] = forwarded_for
        if real_ip:
            headers["X-Real-IP"] = real_ip
        req.headers.get = lambda k, d=None: headers.get(k, d)
        return req

    def test_direct_ip(self):
        req = self._mock_request(host="10.0.0.1")
        assert get_client_ip(req) == "10.0.0.1"

    def test_trusted_proxy_forwarded(self):
        """When request comes from trusted proxy (127.0.0.1), trust X-Forwarded-For."""
        req = self._mock_request(host="127.0.0.1", forwarded_for="203.0.113.50")
        ip = get_client_ip(req)
        assert ip == "203.0.113.50"

    def test_untrusted_proxy_ignored(self):
        """When request comes from untrusted IP, ignore X-Forwarded-For."""
        req = self._mock_request(host="1.2.3.4", forwarded_for="spoofed-ip")
        ip = get_client_ip(req)
        assert ip == "1.2.3.4"

    def test_trusted_proxy_invalid_forwarded(self):
        """Even from trusted proxy, reject invalid IP in X-Forwarded-For."""
        req = self._mock_request(host="127.0.0.1", forwarded_for="not-an-ip")
        ip = get_client_ip(req)
        assert ip == "127.0.0.1"

    def test_no_client(self):
        req = MagicMock()
        req.client = None
        req.headers.get = lambda k, d=None: d
        assert get_client_ip(req) == "unknown"


class TestAdminKeyVerification:
    """Test admin API key verification."""

    def test_valid_key_header(self):
        req = MagicMock()
        req.headers.get = lambda k, d=None: middleware.ADMIN_API_KEY if k == "X-Admin-Key" else d
        req.query_params.get = lambda k, d=None: d
        assert verify_admin_key(req) is True

    def test_query_key_rejected(self):
        req = MagicMock()
        req.headers.get = lambda k, d=None: d
        req.query_params.get = lambda k, d=None: middleware.ADMIN_API_KEY if k == "admin_key" else d
        assert verify_admin_key(req) is False

    def test_invalid_key(self):
        req = MagicMock()
        req.headers.get = lambda k, d=None: "wrong-key" if k == "X-Admin-Key" else d
        req.query_params.get = lambda k, d=None: d
        assert verify_admin_key(req) is False

    def test_no_key(self):
        req = MagicMock()
        req.headers.get = lambda k, d=None: d
        req.query_params.get = lambda k, d=None: d
        assert verify_admin_key(req) is False


class TestRequestId:
    """Test request ID generation."""

    def test_generates_string(self):
        rid = generate_request_id()
        assert isinstance(rid, str)
        assert len(rid) == 12

    def test_uniqueness(self):
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100  # All unique
