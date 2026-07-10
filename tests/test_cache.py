"""Tests for agent/cache.py — LLM Response Cache."""
import time

import pytest

import cache as cache_mod


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the in-memory cache and stats before each test."""
    cache_mod._cache.clear()
    cache_mod._stats["hits"] = 0
    cache_mod._stats["misses"] = 0
    cache_mod._stats["evictions"] = 0
    yield
    cache_mod._cache.clear()


# ── get / put basics ─────────────────────────────────


def test_put_and_get():
    response = {"reply": "Cam sanh la dac san Tam Binh", "tool_calls": []}
    cache_mod.put("cam sanh la gi", response)
    result = cache_mod.get("cam sanh la gi")
    assert result == response


def test_get_miss():
    result = cache_mod.get("nonexistent query")
    assert result is None


def test_get_increments_hit():
    cache_mod.put("query1", {"reply": "answer"})
    cache_mod.get("query1")
    assert cache_mod._stats["hits"] >= 1


def test_get_miss_increments_miss():
    cache_mod.get("totally_unknown")
    assert cache_mod._stats["misses"] >= 1


# ── _normalize_key ───────────────────────────────────


def test_normalize_key_case_insensitive():
    k1 = cache_mod._normalize_key("Hello World")
    k2 = cache_mod._normalize_key("hello world")
    assert k1 == k2


def test_normalize_key_strips_punctuation():
    k1 = cache_mod._normalize_key("What is cam sanh?")
    k2 = cache_mod._normalize_key("What is cam sanh")
    assert k1 == k2


def test_normalize_key_strips_multiple_punct():
    k1 = cache_mod._normalize_key("What is this?!")
    k2 = cache_mod._normalize_key("What is this")
    assert k1 == k2


def test_normalize_key_session_isolation():
    k1 = cache_mod._normalize_key("hello", session_id="")
    k2 = cache_mod._normalize_key("hello", session_id="session_123")
    assert k1 != k2


def test_normalize_key_same_session():
    k1 = cache_mod._normalize_key("hello", session_id="abc")
    k2 = cache_mod._normalize_key("hello", session_id="abc")
    assert k1 == k2


# ── invalidate_all ───────────────────────────────────


def test_invalidate_all():
    cache_mod.put("q1", {"reply": "a1"})
    cache_mod.put("q2", {"reply": "a2"})
    assert len(cache_mod._cache) == 2
    cache_mod.invalidate_all()
    assert len(cache_mod._cache) == 0


# ── stats ────────────────────────────────────────────


def test_stats_structure():
    s = cache_mod.stats()
    assert "size" in s
    assert "max_size" in s
    assert "hits" in s
    assert "misses" in s
    assert "hit_rate" in s
    assert "evictions" in s
    assert "backend" in s
    assert s["backend"] == "in-memory"


def test_stats_hit_rate():
    cache_mod.put("q", {"reply": "a"})
    cache_mod.get("q")  # hit
    cache_mod.get("missing")  # miss
    s = cache_mod.stats()
    assert s["hits"] >= 1
    assert s["misses"] >= 1


# ── LRU eviction ─────────────────────────────────────


def test_lru_eviction():
    """When cache exceeds MAX_SIZE, oldest entries are evicted."""
    original_max = cache_mod.MAX_SIZE
    try:
        cache_mod.MAX_SIZE = 5

        for i in range(7):
            cache_mod.put(f"query_{i}", {"reply": f"answer_{i}"})

        assert len(cache_mod._cache) <= 5
        assert cache_mod._stats["evictions"] >= 2

        # Oldest entries should be evicted
        assert cache_mod.get("query_0") is None
        assert cache_mod.get("query_1") is None
        # Most recent should still be there
        assert cache_mod.get("query_6") is not None
    finally:
        cache_mod.MAX_SIZE = original_max


def test_eviction_stats_tracked():
    original_max = cache_mod.MAX_SIZE
    try:
        cache_mod.MAX_SIZE = 3
        for i in range(5):
            cache_mod.put(f"q_{i}", {"reply": f"a_{i}"})
        assert cache_mod._stats["evictions"] >= 2
    finally:
        cache_mod.MAX_SIZE = original_max


# ── TTL expiration ───────────────────────────────────


def test_ttl_expiration():
    """Entries should expire after their TTL."""
    cache_mod.put("ttl_test", {"reply": "temp"}, ttl=1)
    assert cache_mod.get("ttl_test") is not None

    # Manually expire the entry by modifying its timestamp
    key = cache_mod._normalize_key("ttl_test")
    cache_mod._cache[key]["timestamp"] = time.time() - 10  # 10 seconds in the past

    result = cache_mod.get("ttl_test")
    assert result is None  # Should be expired


def test_default_ttl():
    assert cache_mod.DEFAULT_TTL == 3600


# ── redis_stats ──────────────────────────────────────


def test_redis_stats_returns_empty_when_no_redis():
    """redis_stats() should return empty dict when Redis is not active."""
    result = cache_mod.redis_stats()
    assert result == {}


# ── Edge cases ───────────────────────────────────────


def test_put_overwrites_existing():
    cache_mod.put("overwrite_q", {"reply": "first"})
    cache_mod.put("overwrite_q", {"reply": "second"})
    result = cache_mod.get("overwrite_q")
    assert result["reply"] == "second"


def test_get_moves_to_end_lru():
    """Accessing an entry should refresh its LRU position."""
    original_max = cache_mod.MAX_SIZE
    try:
        cache_mod.MAX_SIZE = 3
        cache_mod.put("q_a", {"reply": "a"})
        cache_mod.put("q_b", {"reply": "b"})
        cache_mod.put("q_c", {"reply": "c"})

        # Access q_a to make it most recently used
        cache_mod.get("q_a")

        # Add one more, which should evict q_b (least recently used), not q_a
        cache_mod.put("q_d", {"reply": "d"})

        assert cache_mod.get("q_a") is not None  # q_a was refreshed
        assert cache_mod.get("q_b") is None       # q_b should be evicted
    finally:
        cache_mod.MAX_SIZE = original_max


def test_empty_query():
    cache_mod.put("", {"reply": "empty"})
    result = cache_mod.get("")
    assert result == {"reply": "empty"}
