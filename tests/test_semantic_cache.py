"""Tests for agent/semantic_cache.py -- Semantic Cache & Request Deduplication."""

import sys
import os
import time
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from semantic_cache import (
    SemanticMatcher,
    MultiTierCache,
    RequestDeduplicator,
    CacheWarmer,
    semantic_get,
    semantic_put,
    _make_key,
    _SEASONAL_QUERIES,
)


# ---- SemanticMatcher ----


class TestSemanticMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = SemanticMatcher()

    def test_find_similar_empty_index(self):
        key, sim = self.matcher.find_similar("any query")
        self.assertIsNone(key)
        self.assertEqual(sim, 0.0)

    def test_find_similar_identical_query(self):
        self.matcher.add("k1", "du lich vinh long mekong")
        key, sim = self.matcher.find_similar("du lich vinh long mekong")
        self.assertEqual(key, "k1")
        self.assertGreater(sim, 0.9)

    def test_find_similar_different_query(self):
        self.matcher.add("k1", "du lich vinh long mekong delta")
        key, sim = self.matcher.find_similar("am thuc sai gon nha hang com tam")
        # Very different query -- should not match with high threshold
        if key is not None:
            self.assertLess(sim, 0.88)
        # Either None or below threshold
        key2, sim2 = self.matcher.find_similar(
            "am thuc sai gon nha hang com tam", threshold=0.88
        )
        self.assertIsNone(key2)

    def test_find_similar_threshold(self):
        self.matcher.add("k1", "lich trinh 3 ngay vinh long mekong delta")
        # Use a completely different query with very high threshold
        key, sim = self.matcher.find_similar(
            "am thuc sai gon com tam pho bo bun cha", threshold=0.5
        )
        # The queries are so different that even a moderate threshold should reject
        self.assertIsNone(key)

    def test_add_and_remove(self):
        self.matcher.add("k1", "hello world test query")
        self.matcher.remove("k1")
        key, sim = self.matcher.find_similar("hello world test query")
        self.assertIsNone(key)

    def test_cosine_similarity_identical_vectors(self):
        v = {"a": 1.0, "b": 2.0}
        sim = SemanticMatcher._cosine_similarity(v, v)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_cosine_similarity_empty_vectors(self):
        sim = SemanticMatcher._cosine_similarity({}, {"a": 1.0})
        self.assertEqual(sim, 0.0)
        sim2 = SemanticMatcher._cosine_similarity({"a": 1.0}, {})
        self.assertEqual(sim2, 0.0)

    def test_cosine_similarity_orthogonal(self):
        v1 = {"a": 1.0}
        v2 = {"b": 1.0}
        sim = SemanticMatcher._cosine_similarity(v1, v2)
        self.assertEqual(sim, 0.0)


# ---- MultiTierCache ----


class TestMultiTierCache(unittest.TestCase):
    def setUp(self):
        self.matcher = SemanticMatcher()
        self.cache = MultiTierCache(matcher=self.matcher, l1_max=10, l2_max=50)
        self.cache._l2_loaded = True  # skip disk I/O

    def test_put_and_get_l1(self):
        self.cache.put("test query", {"answer": "hello"}, ttl=3600)
        result = self.cache.get("test query")
        self.assertIsNotNone(result)
        self.assertEqual(result["answer"], "hello")
        self.assertEqual(self.cache.hits_l1, 1)

    def test_get_miss(self):
        result = self.cache.get("nonexistent query")
        self.assertIsNone(result)
        self.assertEqual(self.cache.misses, 1)

    def test_ttl_expiry(self):
        self.cache.put("expire me", {"data": "old"}, ttl=1)
        # Manually expire by backdating timestamp
        key = _make_key("expire me")
        if key in self.cache._l1:
            self.cache._l1[key]["timestamp"] = time.time() - 10
        if key in self.cache._l2:
            self.cache._l2[key]["timestamp"] = time.time() - 10
        result = self.cache.get("expire me")
        self.assertIsNone(result)

    def test_invalidate(self):
        self.cache.put("to remove", {"data": "value"}, ttl=3600)
        self.cache.invalidate("to remove")
        result = self.cache.get("to remove")
        self.assertIsNone(result)

    def test_invalidate_entity(self):
        self.cache.put("query about entity_123", {"entity_id": "entity_123", "name": "Test"}, ttl=3600)
        self.cache.put("unrelated query", {"other": "data"}, ttl=3600)
        self.cache.invalidate_entity("entity_123")
        # The entry mentioning entity_123 should be removed
        result = self.cache.get("query about entity_123")
        self.assertIsNone(result)
        # The unrelated entry should survive
        result2 = self.cache.get("unrelated query")
        self.assertIsNotNone(result2)

    def test_stats_tracking(self):
        self.cache.put("q1", {"r": 1}, ttl=3600)
        self.cache.get("q1")  # L1 hit
        self.cache.get("nonexistent")  # miss
        self.assertEqual(self.cache.hits_l1, 1)
        self.assertEqual(self.cache.misses, 1)
        self.assertEqual(self.cache.total_queries, 2)

    def test_l1_eviction(self):
        for i in range(15):
            self.cache.put(f"query {i} unique", {"i": i}, ttl=3600)
        # L1 should be capped at l1_max
        self.assertLessEqual(len(self.cache._l1), 10)

    def test_l2_gets_promoted_to_l1(self):
        # Put an entry, then remove from L1 only, keeping in L2
        self.cache.put("promote me", {"data": "value"}, ttl=3600)
        key = _make_key("promote me")
        self.cache._l1.pop(key, None)
        self.assertNotIn(key, self.cache._l1)
        self.assertIn(key, self.cache._l2)
        # Get should promote from L2
        result = self.cache.get("promote me")
        self.assertIsNotNone(result)
        self.assertEqual(self.cache.hits_l2, 1)
        self.assertIn(key, self.cache._l1)


# ---- RequestDeduplicator ----


class TestRequestDeduplicator(unittest.TestCase):
    def setUp(self):
        self.dedup = RequestDeduplicator()

    def test_acquire_first_returns_true(self):
        is_first, key = self.dedup.acquire("test query")
        self.assertTrue(is_first)
        self.assertIsInstance(key, str)

    def test_acquire_duplicate_returns_false(self):
        is_first, key1 = self.dedup.acquire("same query")
        self.assertTrue(is_first)
        is_first2, key2 = self.dedup.acquire("same query")
        self.assertFalse(is_first2)
        self.assertEqual(key1, key2)

    def test_resolve_and_wait_for(self):
        is_first, key = self.dedup.acquire("resolve test")
        self.assertTrue(is_first)
        result = {"answer": "resolved"}
        self.dedup.resolve(key, result)
        waited = self.dedup.wait_for(key, timeout=1)
        self.assertEqual(waited, result)

    def test_wait_for_nonexistent_returns_none(self):
        result = self.dedup.wait_for("nonexistent_key", timeout=0.1)
        self.assertIsNone(result)

    def test_resolve_wakes_waiter(self):
        is_first, key = self.dedup.acquire("wake test")
        result_holder = [None]

        def waiter():
            result_holder[0] = self.dedup.wait_for(key, timeout=5)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)
        self.dedup.resolve(key, {"woken": True})
        t.join(timeout=2)
        self.assertEqual(result_holder[0], {"woken": True})


# ---- CacheWarmer ----


class TestCacheWarmer(unittest.TestCase):
    def setUp(self):
        self.matcher = SemanticMatcher()
        self.cache = MultiTierCache(matcher=self.matcher, l1_max=10, l2_max=50)
        self.cache._l2_loaded = True
        self.warmer = CacheWarmer(cache=self.cache)

    def test_get_seasonal_queries_returns_for_known_month(self):
        queries = CacheWarmer.get_seasonal_queries(6)
        self.assertIsInstance(queries, list)
        self.assertGreater(len(queries), 0)

    def test_get_seasonal_queries_returns_empty_for_unknown(self):
        queries = CacheWarmer.get_seasonal_queries(13)
        self.assertEqual(queries, [])

    def test_get_seasonal_queries_covers_all_months(self):
        for month in range(1, 13):
            queries = CacheWarmer.get_seasonal_queries(month)
            self.assertIsInstance(queries, list)
            self.assertGreater(len(queries), 0, f"Month {month} has no queries")


# ---- Convenience functions ----


class TestConvenienceFunctions(unittest.TestCase):
    def test_semantic_get_miss(self):
        # On a cache miss with no duplicate in-flight, should return None
        result = semantic_get("completely unique query " + str(time.time()))
        self.assertIsNone(result)

    def test_semantic_put_and_get(self):
        unique = f"semantic roundtrip {time.time()}"
        semantic_put(unique, {"reply": "test"})
        # Now the module-level cache has it
        from semantic_cache import multi_tier_cache
        result = multi_tier_cache.get(unique)
        self.assertIsNotNone(result)
        self.assertEqual(result["reply"], "test")

    def test_make_key_deterministic(self):
        key1 = _make_key("hello world")
        key2 = _make_key("hello world")
        self.assertEqual(key1, key2)

    def test_make_key_different_queries(self):
        key1 = _make_key("query A")
        key2 = _make_key("query B")
        self.assertNotEqual(key1, key2)


if __name__ == "__main__":
    unittest.main()
