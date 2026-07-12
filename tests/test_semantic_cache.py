"""Tests for agent/semantic_cache.py -- Semantic Cache & Request Deduplication."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
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
)
import semantic_cache as semantic_cache_mod


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

    def test_find_similar_searches_only_the_requested_owner_namespace(self):
        query = "du lich vinh long mekong delta"
        self.matcher.add("alice-key", query, owner_key="user:alice")
        self.matcher.add(
            "bob-key",
            "du lich vinh long mekong delta homestay",
            owner_key="user:bob",
        )

        key, sim = self.matcher.find_similar(
            query,
            threshold=0.3,
            owner_key="user:bob",
        )

        self.assertEqual(key, "bob-key")
        self.assertGreaterEqual(sim, 0.3)

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

    def test_l1_isolated_by_owner(self):
        alice_response = {"answer": "alice sentinel"}
        self.cache.put("same query", alice_response, owner_key="user:alice")

        self.assertEqual(
            self.cache.get("same query", owner_key="user:alice"),
            alice_response,
        )
        self.assertIsNone(self.cache.get("same query", owner_key="user:bob"))

    def test_l2_isolated_by_owner_and_persists_owner_metadata(self):
        alice_response = {"answer": "alice sentinel"}
        self.cache.put("same query", alice_response, owner_key="user:alice")
        alice_key = _make_key("same query", owner_key="user:alice")
        self.cache._l1.clear()

        self.assertEqual(self.cache._l2[alice_key]["owner_key"], "user:alice")
        self.assertIsNone(self.cache.get("same query", owner_key="user:bob"))
        self.assertEqual(
            self.cache.get("same query", owner_key="user:alice"),
            alice_response,
        )

    def test_semantic_fallback_isolated_by_owner(self):
        alice_response = {"answer": "alice sentinel"}
        self.cache.put(
            "du lich vinh long mekong delta homestay",
            alice_response,
            owner_key="user:alice",
        )

        self.assertIsNone(
            self.cache.get("du lich vinh long mekong delta", owner_key="user:bob")
        )
        self.assertEqual(
            self.cache.get(
                "du lich vinh long mekong delta",
                owner_key="user:alice",
            ),
            alice_response,
        )

    def test_legacy_entry_is_not_visible_to_owner_scoped_chat(self):
        query = "legacy cached query"
        legacy_key = _make_key(query)
        self.cache._l2[legacy_key] = {
            "query": query,
            "response": {"answer": "legacy sentinel"},
            "timestamp": time.time(),
            "ttl": 3600,
        }
        self.matcher.add(legacy_key, query)

        self.assertIsNone(self.cache.get(query, owner_key="user:alice"))
        self.assertEqual(self.cache.get(query)["answer"], "legacy sentinel")

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

    def test_invalidate_removes_only_the_requested_owner_entry(self):
        self.cache.put("same query", {"owner": "alice"}, owner_key="user:alice")
        self.cache.put("same query", {"owner": "bob"}, owner_key="user:bob")

        self.cache.invalidate("same query", owner_key="user:alice")

        self.assertIsNone(self.cache.get("same query", owner_key="user:alice"))
        self.assertEqual(
            self.cache.get("same query", owner_key="user:bob"),
            {"owner": "bob"},
        )

    def test_invalidate_all_namespaces_removes_owner_and_legacy_entries(self):
        query = "same query"
        self.cache.put(query, {"owner": "alice"}, owner_key="user:alice")
        self.cache.put(query, {"owner": "bob"}, owner_key="user:bob")
        self.cache.put(query, {"owner": "legacy"})

        self.cache.invalidate_all_namespaces(query)

        self.assertIsNone(self.cache.get(query, owner_key="user:alice"))
        self.assertIsNone(self.cache.get(query, owner_key="user:bob"))
        self.assertIsNone(self.cache.get(query))

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

    def test_identical_queries_from_different_owners_do_not_deduplicate(self):
        alice_first, alice_key = self.dedup.acquire(
            "same query", owner_key="user:alice"
        )
        bob_first, bob_key = self.dedup.acquire("same query", owner_key="user:bob")

        self.assertTrue(alice_first)
        self.assertTrue(bob_first)
        self.assertNotEqual(alice_key, bob_key)

        self.dedup.resolve(
            alice_key,
            {"reply": "alice sentinel"},
            owner_key="user:alice",
        )
        self.assertIsNone(self.dedup.wait_for(bob_key, timeout=0.01))

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


class TestRequestDeduplicatorAsync(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.dedup = RequestDeduplicator()

    async def test_resolve_wakes_async_waiter_and_removes_registration(self):
        is_first, key = self.dedup.acquire("async resolve")
        self.assertTrue(is_first)
        waiter = asyncio.create_task(self.dedup.wait_for_async(key, timeout=1))
        await asyncio.sleep(0)

        self.assertEqual(len(self.dedup._pending[key]["async_waiters"]), 1)
        self.dedup.resolve(key, {"reply": "resolved"})

        self.assertEqual(await waiter, {"reply": "resolved"})
        self.assertEqual(self.dedup._pending[key]["async_waiters"], {})

    async def test_async_waiter_timeout_returns_none_and_removes_registration(self):
        _is_first, key = self.dedup.acquire("async timeout")

        result = await self.dedup.wait_for_async(key, timeout=0.01)

        self.assertIsNone(result)
        self.assertEqual(self.dedup._pending[key]["async_waiters"], {})

    async def test_async_waiter_observes_result_resolved_before_registration(self):
        _is_first, key = self.dedup.acquire("async resolve race")
        self.dedup.resolve(key, {"reply": "already resolved"})

        result = await self.dedup.wait_for_async(key, timeout=1)

        self.assertEqual(result, {"reply": "already resolved"})
        self.assertEqual(self.dedup._pending[key]["async_waiters"], {})

    async def test_async_waiter_cancellation_removes_registration(self):
        _is_first, key = self.dedup.acquire("async cancellation")
        waiter = asyncio.create_task(self.dedup.wait_for_async(key, timeout=30))
        await asyncio.sleep(0)
        self.assertEqual(len(self.dedup._pending[key]["async_waiters"]), 1)

        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter

        self.assertEqual(self.dedup._pending[key]["async_waiters"], {})

    async def test_async_waiters_remain_isolated_by_owner(self):
        _alice_first, alice_key = self.dedup.acquire(
            "same async query",
            owner_key="user:alice",
        )
        _bob_first, bob_key = self.dedup.acquire(
            "same async query",
            owner_key="user:bob",
        )
        alice_waiter = asyncio.create_task(
            self.dedup.wait_for_async(alice_key, timeout=1)
        )
        bob_waiter = asyncio.create_task(
            self.dedup.wait_for_async(bob_key, timeout=1)
        )
        await asyncio.sleep(0)

        self.dedup.resolve(
            alice_key,
            {"reply": "alice"},
            owner_key="user:alice",
        )

        self.assertEqual(await alice_waiter, {"reply": "alice"})
        self.assertFalse(bob_waiter.done())
        self.dedup.resolve(
            bob_key,
            {"reply": "bob"},
            owner_key="user:bob",
        )
        self.assertEqual(await bob_waiter, {"reply": "bob"})

    async def test_threaded_resolve_wakes_sync_and_async_waiters_together(self):
        _is_first, key = self.dedup.acquire("mixed sync async waiters")
        sync_started = threading.Event()
        sync_result = {}

        def wait_synchronously():
            sync_started.set()
            sync_result["value"] = self.dedup.wait_for(key, timeout=1)

        sync_waiter = threading.Thread(target=wait_synchronously)
        async_waiter = asyncio.create_task(
            self.dedup.wait_for_async(key, timeout=1)
        )
        await asyncio.sleep(0)
        sync_waiter.start()
        self.assertTrue(await asyncio.to_thread(sync_started.wait, 1))

        resolver = threading.Thread(
            target=self.dedup.resolve,
            args=(key, {"reply": "mixed resolved"}),
        )
        resolver.start()
        resolver.join(timeout=1)

        self.assertEqual(await async_waiter, {"reply": "mixed resolved"})
        sync_waiter.join(timeout=1)
        self.assertEqual(sync_result["value"], {"reply": "mixed resolved"})
        self.assertFalse(resolver.is_alive())
        self.assertFalse(sync_waiter.is_alive())
        self.assertEqual(self.dedup._pending[key]["async_waiters"], {})


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

    def test_semantic_get_async_propagates_waiter_error(self):
        matcher = SemanticMatcher()
        cache = MultiTierCache(matcher=matcher, l1_max=10, l2_max=50)
        cache._l2_loaded = True

        class RaisingDeduplicator(RequestDeduplicator):
            def acquire(self, query, timeout=5.0, owner_key=""):
                return False, _make_key(query, owner_key=owner_key)

            def wait_for(self, dedup_key, timeout=30):
                raise RuntimeError("semantic waiter failed")

            async def wait_for_async(self, dedup_key, timeout=30):
                raise RuntimeError("semantic waiter failed")

        with (
            patch.object(semantic_cache_mod, "multi_tier_cache", cache),
            patch.object(
                semantic_cache_mod,
                "deduplicator",
                RaisingDeduplicator(),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "semantic waiter failed"):
                asyncio.run(
                    semantic_cache_mod.semantic_get_async(
                        "async semantic error",
                        owner_key="user:alice",
                    )
                )

    def test_cancelled_async_waiters_do_not_starve_default_executor(self):
        matcher = SemanticMatcher()
        cache = MultiTierCache(matcher=matcher, l1_max=10, l2_max=50)
        cache._l2_loaded = True
        executor = ThreadPoolExecutor(max_workers=2)
        release_source = {"value": None}
        source_lock = threading.Lock()
        provider_completed = threading.Event()
        query = "cancelled semantic waiters executor isolation"
        owner_key = "user:alice"

        async def exercise():
            loop = asyncio.get_running_loop()
            loop.set_default_executor(executor)
            waiters_started = asyncio.Event()

            class SaturatingDeduplicator(RequestDeduplicator):
                def __init__(self):
                    super().__init__()
                    self._started = 0
                    self._started_lock = threading.Lock()

                def _mark_started(self):
                    with self._started_lock:
                        self._started += 1
                        if self._started == 2:
                            loop.call_soon_threadsafe(waiters_started.set)

                def wait_for(self, dedup_key, timeout=30):
                    self._mark_started()
                    return super().wait_for(dedup_key, timeout=5)

                async def wait_for_async(self, dedup_key, timeout=30):
                    self._mark_started()
                    return await super().wait_for_async(dedup_key, timeout=timeout)

            dedup = SaturatingDeduplicator()
            is_holder, key = dedup.acquire(query, owner_key=owner_key)
            self.assertTrue(is_holder)

            with (
                patch.object(semantic_cache_mod, "multi_tier_cache", cache),
                patch.object(semantic_cache_mod, "deduplicator", dedup),
            ):
                waiters = [
                    asyncio.create_task(
                        semantic_cache_mod.semantic_get_async(
                            query,
                            owner_key=owner_key,
                        )
                    )
                    for _ in range(2)
                ]
                await asyncio.wait_for(waiters_started.wait(), timeout=1)
                for waiter in waiters:
                    waiter.cancel()
                results = await asyncio.gather(*waiters, return_exceptions=True)
                self.assertTrue(
                    all(isinstance(result, asyncio.CancelledError) for result in results)
                )
                self.assertEqual(
                    dedup._pending[key].get("async_waiters", {}),
                    {},
                )

                def release_only_to_break_starvation():
                    if not provider_completed.wait(timeout=2):
                        with source_lock:
                            release_source["value"] = "watchdog"
                        semantic_cache_mod.semantic_put(
                            query,
                            {"reply": "watchdog release"},
                            owner_key=owner_key,
                        )

                watchdog = threading.Thread(
                    target=release_only_to_break_starvation
                )
                watchdog.start()
                provider_result = await asyncio.to_thread(
                    lambda: "unrelated provider work"
                )
                with source_lock:
                    if release_source["value"] is None:
                        release_source["value"] = "provider"
                semantic_cache_mod.semantic_put(
                    query,
                    {"reply": "provider completed first"},
                    owner_key=owner_key,
                )
                provider_completed.set()
                watchdog.join(timeout=3)

                self.assertEqual(provider_result, "unrelated provider work")
                self.assertFalse(watchdog.is_alive())

        asyncio.run(exercise())

        self.assertEqual(release_source["value"], "provider")
        self.assertTrue(all(not thread.is_alive() for thread in executor._threads))

    def test_semantic_convenience_functions_isolate_cache_and_dedup_by_owner(self):
        matcher = SemanticMatcher()
        cache = MultiTierCache(matcher=matcher, l1_max=10, l2_max=50)
        cache._l2_loaded = True
        dedup = RequestDeduplicator()
        query = "du lich vinh long owner scoped"
        sentinel = {"reply": "alice sentinel"}

        with (
            patch.object(semantic_cache_mod, "multi_tier_cache", cache),
            patch.object(semantic_cache_mod, "deduplicator", dedup),
        ):
            semantic_put(query, sentinel, owner_key="user:alice")

            self.assertEqual(
                semantic_get(query, owner_key="user:alice"),
                sentinel,
            )
            self.assertIsNone(semantic_get(query, owner_key="user:bob"))

    def test_owner_scoped_convenience_get_ignores_legacy_namespace(self):
        matcher = SemanticMatcher()
        cache = MultiTierCache(matcher=matcher, l1_max=10, l2_max=50)
        cache._l2_loaded = True
        dedup = RequestDeduplicator()
        query = "legacy semantic convenience"

        with (
            patch.object(semantic_cache_mod, "multi_tier_cache", cache),
            patch.object(semantic_cache_mod, "deduplicator", dedup),
        ):
            semantic_put(query, {"reply": "legacy sentinel"})

            self.assertIsNone(semantic_get(query, owner_key="user:alice"))

    def test_make_key_deterministic(self):
        key1 = _make_key("hello world")
        key2 = _make_key("hello world")
        self.assertEqual(key1, key2)

    def test_make_key_different_queries(self):
        key1 = _make_key("query A")
        key2 = _make_key("query B")
        self.assertNotEqual(key1, key2)

    def test_make_key_includes_owner_namespace(self):
        alice = _make_key("same query", owner_key="user:alice")
        bob = _make_key("same query", owner_key="user:bob")
        legacy = _make_key("same query")

        self.assertEqual(len({alice, bob, legacy}), 3)


if __name__ == "__main__":
    unittest.main()
