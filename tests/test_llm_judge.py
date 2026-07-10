"""Tests for llm_judge.py -- Level 7 LLM-based quality evaluation."""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from llm_judge import (
    DEFAULT_CRITERIA,
    RuleBasedFallback,
    JudgeResult,
    LLMJudge,
    JudgeAnalytics,
    judge,
)


class TestJudgeCriteria(unittest.TestCase):
    """Tests for JudgeCriteria and DEFAULT_CRITERIA."""

    def test_default_criteria_count(self):
        self.assertEqual(len(DEFAULT_CRITERIA), 5)

    def test_default_criteria_names(self):
        names = {c.name for c in DEFAULT_CRITERIA}
        self.assertEqual(names, {"relevance", "accuracy", "completeness", "helpfulness", "format"})

    def test_weights_sum_to_one(self):
        total = sum(c.weight for c in DEFAULT_CRITERIA)
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_criteria_has_prompt_template(self):
        for c in DEFAULT_CRITERIA:
            self.assertIsInstance(c.prompt_template, str)
            self.assertTrue(len(c.prompt_template) > 0)

    def test_criteria_scale(self):
        for c in DEFAULT_CRITERIA:
            self.assertEqual(c.scale, (1, 10))


class TestRuleBasedFallback(unittest.TestCase):
    """Tests for RuleBasedFallback heuristic scoring."""

    def setUp(self):
        self.fb = RuleBasedFallback()

    def test_score_returns_all_criteria_keys(self):
        result = self.fb.score("test query", "test reply with some content here")
        expected_keys = {"relevance", "accuracy", "completeness", "helpfulness", "format", "feedback"}
        self.assertEqual(set(result.keys()), expected_keys)

    def test_relevance_high_for_matching_query(self):
        result = self.fb.score("Vinh Long du lich", "Vinh Long la mot tinh dep, du lich rat thu vi")
        self.assertGreater(result["relevance"], 5.0)

    def test_relevance_low_for_unmatched_query(self):
        result = self.fb.score("dac san Vinh Long", "Hello this is a generic reply about nothing specific")
        self.assertLessEqual(result["relevance"], 5.0)

    def test_completeness_scales_with_length(self):
        short = self.fb.score("q", "ok")
        long = self.fb.score("q", "x " * 200)
        self.assertGreater(long["completeness"], short["completeness"])

    def test_accuracy_is_neutral(self):
        result = self.fb.score("q", "any reply")
        self.assertEqual(result["accuracy"], 5.0)

    def test_format_higher_with_markdown(self):
        plain = self.fb.score("q", "just plain text here with enough length to matter")
        md = self.fb.score("q", "## Heading\n- item one\n- item two\n- item three\n**bold text** here.")
        self.assertGreater(md["format"], plain["format"])

    def test_scores_clamped_1_to_10(self):
        result = self.fb.score("x" * 1000, "y" * 1000)
        for key in ["relevance", "accuracy", "completeness", "helpfulness", "format"]:
            self.assertGreaterEqual(result[key], 1)
            self.assertLessEqual(result[key], 10)

    def test_feedback_string_present(self):
        result = self.fb.score("q", "short")
        self.assertIsInstance(result["feedback"], str)
        self.assertTrue(len(result["feedback"]) > 0)


class TestJudgeResult(unittest.TestCase):
    """Tests for JudgeResult dataclass."""

    def test_to_dict_roundtrip(self):
        result = JudgeResult(
            query="test query",
            reply_preview="test reply",
            scores={"relevance": 7.0, "accuracy": 5.0, "completeness": 6.0,
                     "helpfulness": 8.0, "format": 7.0},
            weighted_score=6.5,
            feedback="Good quality",
            timestamp=time.time(),
            is_llm_judged=False,
        )
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["query"], "test query")
        self.assertEqual(d["weighted_score"], 6.5)
        self.assertEqual(d["is_llm_judged"], False)
        self.assertIn("scores", d)

    def test_to_dict_contains_all_fields(self):
        result = JudgeResult(
            query="q", reply_preview="r", scores={},
            weighted_score=0.0, feedback="", timestamp=0.0, is_llm_judged=True,
        )
        d = result.to_dict()
        expected_keys = {"query", "reply_preview", "scores", "weighted_score",
                         "feedback", "timestamp", "is_llm_judged"}
        self.assertEqual(set(d.keys()), expected_keys)


class TestLLMJudge(unittest.TestCase):
    """Tests for LLMJudge (fallback path only -- no API key needed)."""

    def setUp(self):
        self.judge = LLMJudge()

    def test_evaluate_returns_judge_result(self):
        result = self.judge.evaluate("Cho noi Cai Be o dau?", "Cho noi Cai Be nam tai...")
        self.assertIsInstance(result, JudgeResult)

    def test_evaluate_fallback_is_rule_based(self):
        """Without API key, should use rule-based fallback."""
        result = self.judge.evaluate("test", "test reply here with enough content")
        self.assertFalse(result.is_llm_judged)

    def test_evaluate_scores_have_all_criteria(self):
        result = self.judge.evaluate("query", "reply with some content")
        for c in DEFAULT_CRITERIA:
            self.assertIn(c.name, result.scores)

    def test_evaluate_weighted_score_in_range(self):
        result = self.judge.evaluate("query", "reply text")
        self.assertGreaterEqual(result.weighted_score, 1.0)
        self.assertLessEqual(result.weighted_score, 10.0)

    def test_reply_preview_truncated(self):
        long_reply = "x" * 500
        result = self.judge.evaluate("query", long_reply)
        self.assertLessEqual(len(result.reply_preview), 100)


class TestJudgeAnalytics(unittest.TestCase):
    """Tests for JudgeAnalytics."""

    def setUp(self):
        self.judge = LLMJudge()
        # Pre-populate cache with evaluations
        self.judge.evaluate("query1", "reply one with content about tourism")
        self.judge.evaluate("query2", "reply two about Vinh Long du lich dac san am thuc dia phuong rat ngon")
        self.judge.evaluate("query3", "short")
        self.analytics = JudgeAnalytics(self.judge)

    def test_get_quality_trend(self):
        trend = self.analytics.get_quality_trend(days=1)
        self.assertIsInstance(trend, list)
        if trend:
            entry = trend[0]
            self.assertIn("date", entry)
            self.assertIn("avg_score", entry)
            self.assertIn("count", entry)

    def test_get_worst_queries(self):
        worst = self.analytics.get_worst_queries(limit=5)
        self.assertIsInstance(worst, list)
        self.assertGreater(len(worst), 0)
        # Should be sorted ascending by weighted_score
        if len(worst) >= 2:
            self.assertLessEqual(worst[0]["weighted_score"], worst[1]["weighted_score"])

    def test_get_criteria_breakdown(self):
        breakdown = self.analytics.get_criteria_breakdown()
        self.assertIsInstance(breakdown, dict)
        if breakdown:
            for crit_name, stats in breakdown.items():
                self.assertIn("avg", stats)
                self.assertIn("min", stats)
                self.assertIn("max", stats)
                self.assertIn("count", stats)

    def test_get_criteria_breakdown_empty(self):
        empty_judge = LLMJudge()
        empty_judge._cache = []
        analytics = JudgeAnalytics(empty_judge)
        self.assertEqual(analytics.get_criteria_breakdown(), {})


class TestJudgeConvenience(unittest.TestCase):
    """Tests for the judge() convenience function."""

    def test_judge_returns_dict(self):
        result = judge("query text", "reply text with content about tourism")
        self.assertIsInstance(result, dict)
        self.assertIn("weighted_score", result)
        self.assertIn("scores", result)
        self.assertIn("feedback", result)


if __name__ == "__main__":
    unittest.main()
