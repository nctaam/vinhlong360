"""Unit tests for SemanticMatcher sparse inverted posting index & L2 norm caching."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from semantic_cache import SemanticMatcher  # noqa: E402


class TestSemanticMatcherPostings(unittest.TestCase):
    def test_postings_and_norms_match_brute_force_across_updates(self):
        matcher = SemanticMatcher()
        corpus = [
            (f"v{i}", f"du lich sinh thai vuon trai cay co chien {i}", "user:a")
            for i in range(60)
        ] + [
            (f"b{i}", f"dac san keo dua ben tre lang nghe {i}", "user:b")
            for i in range(60)
        ] + [
            ("target", "kham pha quan the lo gach gom do mang thit ben kenh thay cai", "user:a"),
        ]
        for k, q, owner in corpus:
            matcher.add(k, q, owner_key=owner)

        # Overwrite and remove entries to ensure _postings and _norms stay consistent
        matcher.add("v5", "am thuc bun nuoc leo tra vinh dac san", owner_key="user:a")
        matcher.remove("v10")
        self.assertNotIn("v10", matcher._norms)
        self.assertFalse(any("v10" in docs for docs in matcher._postings.values()))

        query = "quan the lo gach gom do mang thit kenh thay cai"
        got_key, got_sim = matcher.find_similar(query, threshold=0.5, owner_key="user:a")
        self.assertEqual(got_key, "target")
        self.assertGreaterEqual(got_sim, 0.7)

        # Exact parity against brute-force pairwise cosine similarity
        qvec = matcher._vectorize(query)
        expected_key, expected_sim = max(
            (
                (k, SemanticMatcher._cosine_similarity(qvec, vec))
                for k, vec in matcher._vectors.items()
                if matcher._owners.get(k, "") == "user:a"
            ),
            key=lambda item: item[1],
        )
        self.assertEqual(got_key, expected_key)
        self.assertAlmostEqual(got_sim, expected_sim, places=9)

        # Cross-owner isolation preserved
        other_key, other_sim = matcher.find_similar(query, threshold=0.2, owner_key="user:b")
        self.assertIsNone(other_key)
        self.assertEqual(other_sim, 0.0)

        # Rebuild clears stale postings/norms
        matcher.rebuild({"only": {"query": "chua khmer ao ba om", "owner_key": ""}})
        self.assertEqual(set(matcher._norms.keys()), {"only"})
        key_only, _ = matcher.find_similar("chua khmer ao ba om", threshold=0.8)
        self.assertEqual(key_only, "only")


if __name__ == "__main__":
    unittest.main()
