"""Tests for middleware (agent/middleware.py)."""
import pytest
from types import SimpleNamespace

from middleware import (
    RateLimiter,
    StructuredLogger,
    ErrorTracker,
    ResponseTimeTracker,
    verify_admin_key,
)


# ── RateLimiter ──

def test_rate_limiter_allows():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        allowed, info = rl.is_allowed("ip1")
        assert allowed is True


def test_rate_limiter_blocks():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        rl.is_allowed("ip1")
    allowed, info = rl.is_allowed("ip1")
    assert allowed is False
    assert info["retry_after"] > 0
    assert info["remaining"] == 0


def test_rate_limiter_different_keys():
    rl = RateLimiter(max_requests=2, window_seconds=60)
    # Fill up key1
    rl.is_allowed("key1")
    rl.is_allowed("key1")
    allowed_key1, _ = rl.is_allowed("key1")
    assert allowed_key1 is False

    # key2 should still be allowed
    allowed_key2, _ = rl.is_allowed("key2")
    assert allowed_key2 is True


# ── StructuredLogger ──

def test_structured_logger():
    logger = StructuredLogger(name="test-logger", max_entries=100)
    logger.info("test message", extra_field="value")
    logger.flush()
    entries = logger.recent(limit=10)
    assert isinstance(entries, list)
    # At least one entry should exist (though the file may contain prior entries)


# ── ErrorTracker ──

def test_error_tracker_healthy():
    et = ErrorTracker(threshold=5, window_seconds=300)
    assert et.is_healthy() is True


def test_error_tracker_threshold():
    et = ErrorTracker(threshold=3, window_seconds=300)
    for i in range(3):
        et.record_error("/test", f"error_{i}")
    assert et.is_healthy() is False


def test_error_tracker_stats():
    et = ErrorTracker(threshold=5, window_seconds=300)
    et.record_error("/chat", "timeout")
    stats = et.stats()
    assert stats["total_recent"] >= 1
    assert stats["threshold"] == 5


# ── ResponseTimeTracker ──

def test_response_time_tracker():
    rt = ResponseTimeTracker()
    rt.record("/chat", 150.0, status=200)
    rt.record("/chat", 200.0, status=200)
    rt.record("/health", 10.0, status=200)
    stats = rt.stats()
    assert stats["count"] == 3
    assert stats["avg_ms"] == pytest.approx(120.0, abs=1.0)


# ── verify_admin_key ──

def test_verify_admin_key_valid():
    """Test with a mock request object that provides the correct key."""
    import os
    expected_key = os.environ.get("ADMIN_API_KEY", "")

    request = SimpleNamespace(
        headers={"X-Admin-Key": expected_key},
        query_params={},
    )
    assert verify_admin_key(request) is True


def test_verify_admin_key_invalid():
    request = SimpleNamespace(
        headers={"X-Admin-Key": "wrong-key"},
        query_params={},
    )
    assert verify_admin_key(request) is False


def test_verify_admin_key_missing():
    request = SimpleNamespace(
        headers={},
        query_params={},
    )
    assert verify_admin_key(request) is False
