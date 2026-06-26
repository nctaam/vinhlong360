"""Tests cho cache.py — in-memory LRU, metrics integration."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cache  # noqa: E402


@pytest.fixture(autouse=True)
def clean_cache():
    """Reset cache state between tests."""
    cache.invalidate_all()
    cache._stats["hits"] = 0
    cache._stats["misses"] = 0
    cache._stats["evictions"] = 0
    yield
    cache.invalidate_all()


class TestCacheGetPut:
    def test_miss_returns_none(self):
        assert cache.get("nonexistent query") is None

    def test_put_and_get(self):
        cache.put("hello", {"reply": "world"})
        result = cache.get("hello")
        assert result == {"reply": "world"}

    def test_case_insensitive(self):
        cache.put("Hello World", {"r": 1})
        assert cache.get("hello world") is not None

    def test_trailing_punctuation_normalized(self):
        cache.put("where is the market?", {"r": 1})
        assert cache.get("where is the market") is not None

    def test_ttl_expiry(self):
        cache.put("old", {"r": 1}, ttl=0)
        import time
        time.sleep(0.01)
        assert cache.get("old") is None


class TestCacheStats:
    def test_stats_structure(self):
        s = cache.stats()
        assert "size" in s
        assert "hits" in s
        assert "misses" in s
        assert "evictions" in s
        assert "backend" in s
        assert s["backend"] == "in-memory"

    def test_hit_miss_counting(self):
        cache.put("q1", {"r": 1})
        cache.get("q1")
        cache.get("q1")
        cache.get("missing")
        s = cache.stats()
        assert s["hits"] == 2
        assert s["misses"] == 1


class TestCacheEviction:
    def test_evicts_oldest_when_full(self, monkeypatch):
        monkeypatch.setattr(cache, "MAX_SIZE", 3)
        cache.put("a", {"r": 1})
        cache.put("b", {"r": 2})
        cache.put("c", {"r": 3})
        cache.put("d", {"r": 4})
        assert cache.get("a") is None
        assert cache.get("d") is not None
        assert cache._stats["evictions"] >= 1


class TestInvalidateAll:
    def test_clears_all(self):
        cache.put("x", {"r": 1})
        cache.put("y", {"r": 2})
        cache.invalidate_all()
        assert cache.get("x") is None
        assert cache.get("y") is None


class TestNormalizeKey:
    def test_different_queries_different_keys(self):
        k1 = cache._normalize_key("hello")
        k2 = cache._normalize_key("world")
        assert k1 != k2

    def test_session_isolation(self):
        k1 = cache._normalize_key("hello", session_id="s1")
        k2 = cache._normalize_key("hello", session_id="s2")
        assert k1 != k2

    def test_empty_session_shared(self):
        k1 = cache._normalize_key("hello", session_id="")
        k2 = cache._normalize_key("hello")
        assert k1 == k2
