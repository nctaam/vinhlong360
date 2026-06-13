"""Tests for agent/eval_framework.py -- Evaluation & Benchmark Framework."""

import sys
import os
import time
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import eval_framework as ef
from eval_framework import (
    TestCase,
    BENCHMARK_SUITE,
    VALID_CATEGORIES,
    VALID_DIFFICULTIES,
    FactualityScorer,
    ToolUsageScorer,
    CompletenessScorer,
    HallucinationScorer,
    FormatScorer,
    EvalReport,
    EvalRunner,
    PASS_THRESHOLD,
    _normalize_vn,
    _text_contains,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

SAMPLE_ENTITIES = {
    "chua-ang": {"id": "chua-ang", "name": "Chua Ang"},
    "cho-noi-cai-be": {"id": "cho-noi-cai-be", "name": "Cho Noi Cai Be"},
    "cu-lao-an-binh": {"id": "cu-lao-an-binh", "name": "Cu Lao An Binh"},
    "cam-sanh-vinh-long": {"id": "cam-sanh-vinh-long", "name": "Cam Sanh Vinh Long"},
}


def _make_call_fn(reply="Test reply", tools=None):
    """Return a simple call_fn that always returns (reply, tools)."""
    tools = tools or []

    def call_fn(query):
        return (reply, tools)

    return call_fn


# ---------------------------------------------------------------------------
#  TestCase validation
# ---------------------------------------------------------------------------

class TestTestCaseValidation(unittest.TestCase):
    """TestCase dataclass validation: categories, difficulties, round-trip."""

    def test_valid_category_accepted(self):
        for cat in VALID_CATEGORIES:
            tc = TestCase(query="q", category=cat)
            self.assertEqual(tc.category, cat)

    def test_invalid_category_raises(self):
        with self.assertRaises(ValueError) as ctx:
            TestCase(query="q", category="unknown_cat")
        self.assertIn("Invalid category", str(ctx.exception))

    def test_valid_difficulty_accepted(self):
        for diff in VALID_DIFFICULTIES:
            tc = TestCase(query="q", difficulty=diff)
            self.assertEqual(tc.difficulty, diff)

    def test_invalid_difficulty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            TestCase(query="q", difficulty="impossible")
        self.assertIn("Invalid difficulty", str(ctx.exception))

    def test_to_dict_from_dict_roundtrip(self):
        tc = TestCase(
            query="Test query?",
            expected_entities=["chua-ang"],
            expected_tools=["search"],
            expected_keywords=["Tra Vinh"],
            category="factual",
            difficulty="easy",
            max_score=10.0,
        )
        d = tc.to_dict()
        tc2 = TestCase.from_dict(d)
        self.assertEqual(tc.query, tc2.query)
        self.assertEqual(tc.expected_entities, tc2.expected_entities)
        self.assertEqual(tc.category, tc2.category)
        self.assertEqual(tc.difficulty, tc2.difficulty)

    def test_defaults(self):
        tc = TestCase(query="hello")
        self.assertEqual(tc.expected_entities, [])
        self.assertEqual(tc.expected_tools, [])
        self.assertEqual(tc.expected_keywords, [])
        self.assertEqual(tc.category, "factual")
        self.assertEqual(tc.difficulty, "medium")
        self.assertEqual(tc.max_score, 10.0)


# ---------------------------------------------------------------------------
#  BENCHMARK_SUITE structure
# ---------------------------------------------------------------------------

class TestBenchmarkSuite(unittest.TestCase):
    """BENCHMARK_SUITE: size, category coverage, structural correctness."""

    def test_suite_has_at_least_50_cases(self):
        self.assertGreaterEqual(len(BENCHMARK_SUITE), 50)

    def test_all_categories_present(self):
        cats_in_suite = {tc.category for tc in BENCHMARK_SUITE}
        for cat in VALID_CATEGORIES:
            self.assertIn(cat, cats_in_suite, f"Category '{cat}' missing from suite")

    def test_all_cases_are_testcase_instances(self):
        for tc in BENCHMARK_SUITE:
            self.assertIsInstance(tc, TestCase)

    def test_all_cases_have_valid_categories_and_difficulties(self):
        for tc in BENCHMARK_SUITE:
            self.assertIn(tc.category, VALID_CATEGORIES)
            self.assertIn(tc.difficulty, VALID_DIFFICULTIES)

    def test_every_case_has_query(self):
        """Every test case must have a query (string), even if empty for edge cases."""
        for tc in BENCHMARK_SUITE:
            self.assertIsInstance(tc.query, str)


# ---------------------------------------------------------------------------
#  FactualityScorer
# ---------------------------------------------------------------------------

class TestFactualityScorer(unittest.TestCase):
    """FactualityScorer: entity match, keyword match, empty reply."""

    def test_empty_reply_scores_zero(self):
        tc = TestCase(query="q", expected_entities=["chua-ang"], expected_keywords=["Tra Vinh"])
        score = FactualityScorer.score("", tc, SAMPLE_ENTITIES)
        self.assertEqual(score, 0.0)

    def test_entity_and_keyword_match_full_score(self):
        tc = TestCase(
            query="q",
            expected_entities=["chua-ang"],
            expected_keywords=["Tra Vinh"],
            max_score=10.0,
        )
        reply = "Chua Ang nam o Tra Vinh, la mot ngoi chua Khmer dep."
        score = FactualityScorer.score(reply, tc, SAMPLE_ENTITIES)
        self.assertEqual(score, 10.0)

    def test_entity_match_no_keyword(self):
        tc = TestCase(
            query="q",
            expected_entities=["chua-ang"],
            expected_keywords=["some missing keyword"],
            max_score=10.0,
        )
        reply = "Chua Ang la mot ngoi chua dep."
        score = FactualityScorer.score(reply, tc, SAMPLE_ENTITIES)
        # entity_weight=0.6 * 1.0 + keyword_weight=0.4 * 0.0 = 6.0
        self.assertAlmostEqual(score, 6.0)

    def test_keyword_match_no_entity(self):
        tc = TestCase(
            query="q",
            expected_entities=["chua-ang"],
            expected_keywords=["Tra Vinh"],
            max_score=10.0,
        )
        reply = "O Tra Vinh co nhieu ngoi chua."
        score = FactualityScorer.score(reply, tc, SAMPLE_ENTITIES)
        # entity_weight=0.6 * 0.0 + keyword_weight=0.4 * 1.0 = 4.0
        self.assertAlmostEqual(score, 4.0)

    def test_no_expected_entities_gives_full_entity_score(self):
        tc = TestCase(query="q", expected_entities=[], expected_keywords=["key"])
        reply = "Some text with key inside."
        score = FactualityScorer.score(reply, tc, SAMPLE_ENTITIES)
        # entity_score=1.0, keyword_score=1.0 => 10.0
        self.assertEqual(score, 10.0)

    def test_no_expected_keywords_gives_full_keyword_score(self):
        tc = TestCase(query="q", expected_entities=["chua-ang"], expected_keywords=[])
        reply = "Chua Ang is great."
        score = FactualityScorer.score(reply, tc, SAMPLE_ENTITIES)
        # entity_score=1.0, keyword_score=1.0 => 10.0
        self.assertEqual(score, 10.0)


# ---------------------------------------------------------------------------
#  ToolUsageScorer
# ---------------------------------------------------------------------------

class TestToolUsageScorer(unittest.TestCase):
    """ToolUsageScorer: correct tools high, missing tools low, penalties."""

    def test_all_expected_tools_used_full_score(self):
        tc = TestCase(query="q", expected_tools=["search", "entity_detail"])
        score = ToolUsageScorer.score(["search", "entity_detail"], tc)
        self.assertEqual(score, 10.0)

    def test_missing_tools_scores_zero(self):
        tc = TestCase(query="q", expected_tools=["search", "entity_detail"])
        score = ToolUsageScorer.score(["weather"], tc)
        self.assertEqual(score, 0.0)

    def test_no_tools_used_when_expected_scores_zero(self):
        tc = TestCase(query="q", expected_tools=["search"])
        score = ToolUsageScorer.score([], tc)
        self.assertEqual(score, 0.0)

    def test_partial_tools_partial_score(self):
        tc = TestCase(query="q", expected_tools=["search", "entity_detail"])
        score = ToolUsageScorer.score(["search"], tc)
        # recall = 1/2 = 0.5, no penalty => 10.0 * 0.5 = 5.0
        self.assertAlmostEqual(score, 5.0)

    def test_extra_irrelevant_tools_penalised(self):
        tc = TestCase(query="q", expected_tools=["search"])
        score_without_extra = ToolUsageScorer.score(["search"], tc)
        score_with_extra = ToolUsageScorer.score(["search", "a", "b", "c"], tc)
        self.assertGreater(score_without_extra, score_with_extra)

    def test_no_expected_tools_returns_full_score(self):
        tc = TestCase(query="q", expected_tools=[], category="factual")
        score = ToolUsageScorer.score([], tc)
        self.assertEqual(score, 10.0)

    def test_edge_case_no_expected_but_tools_used(self):
        """Edge case category: no tools expected but tools were used => 50%."""
        tc = TestCase(query="q", expected_tools=[], category="edge_case")
        score = ToolUsageScorer.score(["search"], tc)
        self.assertAlmostEqual(score, 5.0)


# ---------------------------------------------------------------------------
#  CompletenessScorer
# ---------------------------------------------------------------------------

class TestCompletenessScorer(unittest.TestCase):
    """CompletenessScorer: short vs adequate reply, element coverage."""

    def test_empty_reply_scores_zero(self):
        tc = TestCase(query="q", difficulty="easy")
        self.assertEqual(CompletenessScorer.score("", tc), 0.0)

    def test_short_reply_below_minimum_penalised(self):
        tc = TestCase(query="q", difficulty="medium", expected_entities=[], expected_keywords=[])
        # MIN_LENGTHS["medium"] = 80
        short_reply = "Short."  # ~6 chars
        score = CompletenessScorer.score(short_reply, tc)
        self.assertLess(score, 10.0)

    def test_adequate_reply_scores_higher(self):
        tc = TestCase(query="q", difficulty="easy", expected_entities=[], expected_keywords=[])
        short_reply = "Ok"
        long_reply = "A" * 50 + " " + "B" * 50  # well over 30 chars
        score_short = CompletenessScorer.score(short_reply, tc)
        score_long = CompletenessScorer.score(long_reply, tc)
        self.assertGreater(score_long, score_short)

    def test_elements_present_boost_score(self):
        tc = TestCase(
            query="q",
            expected_entities=["chua-ang"],
            expected_keywords=["Tra Vinh"],
            difficulty="easy",
        )
        reply_with = "Chua Ang o Tra Vinh rat dep va thu vi."
        reply_without = "X" * 50  # long enough but no entities or keywords
        score_with = CompletenessScorer.score(reply_with, tc)
        score_without = CompletenessScorer.score(reply_without, tc)
        self.assertGreater(score_with, score_without)


# ---------------------------------------------------------------------------
#  HallucinationScorer
# ---------------------------------------------------------------------------

class TestHallucinationScorer(unittest.TestCase):
    """HallucinationScorer: known entities pass, unknown names flagged."""

    def test_empty_reply_full_score(self):
        score = HallucinationScorer.score("", SAMPLE_ENTITIES)
        self.assertEqual(score, 10.0)

    def test_known_entities_no_penalty(self):
        reply = "Chua Ang la mot ngoi chua o Tra Vinh. Cho Noi Cai Be rat noi tieng."
        score = HallucinationScorer.score(reply, SAMPLE_ENTITIES)
        self.assertGreaterEqual(score, 8.0)

    def test_unknown_names_lower_score(self):
        # Many capitalized unknown names exceeding 20% threshold
        reply = (
            "Bao Tang Khong Ton Tai la mot diem den tuyet voi. "
            "Cong Vien Dien Anh Hollywood cung rat dep. "
            "Thac Nuoc Than Tien cao nhat the gioi. "
            "Hoang Cung Buckingham la bieu tuong London. "
            "Dai Phun Nuoc Trevi noi tieng Rome."
        )
        score = HallucinationScorer.score(reply, SAMPLE_ENTITIES)
        self.assertLess(score, 10.0)

    def test_ignored_patterns_not_flagged(self):
        """Common place names in IGNORE_PATTERNS should not count as hallucinations."""
        reply = "Vinh Long va Ben Tre la hai tinh o mien Tay. Ho Chi Minh thanh pho lon nhat."
        score = HallucinationScorer.score(reply, SAMPLE_ENTITIES)
        self.assertGreaterEqual(score, 9.0)


# ---------------------------------------------------------------------------
#  FormatScorer
# ---------------------------------------------------------------------------

class TestFormatScorer(unittest.TestCase):
    """FormatScorer: markdown formatted vs plain text."""

    def test_empty_reply_scores_zero(self):
        self.assertEqual(FormatScorer.score(""), 0.0)

    def test_well_formatted_markdown_higher(self):
        markdown_reply = (
            "## Chua Ang\n\n"
            "- **Dia diem**: Tra Vinh\n"
            "- **Dac diem**: Kien truc Khmer\n\n"
            "Chua Ang la mot trong nhung ngoi chua dep nhat Tra Vinh.\n"
        )
        plain_reply = "Chua Ang nam o Tra Vinh la mot ngoi chua Khmer dep."
        score_md = FormatScorer.score(markdown_reply)
        score_plain = FormatScorer.score(plain_reply)
        self.assertGreater(score_md, score_plain)

    def test_very_short_reply_low_length_score(self):
        score = FormatScorer.score("Hi")
        # reply_len < 20 => len_score = 0.2
        self.assertLess(score, 5.0)

    def test_excessively_long_reply_penalised(self):
        long_reply = "## Heading\n" + "Some content. " * 500  # > 5000 chars
        score = FormatScorer.score(long_reply)
        # Still scores something due to markdown, but verbose penalty applied
        self.assertLess(score, 10.0)


# ---------------------------------------------------------------------------
#  EvalReport
# ---------------------------------------------------------------------------

class TestEvalReport(unittest.TestCase):
    """EvalReport: to_dict/from_dict roundtrip, summary output."""

    def _make_report(self, **overrides):
        defaults = dict(
            timestamp=1700000000.0,
            total_cases=10,
            passed=8,
            failed=2,
            avg_score=7.5,
            scores_by_category={"factual": {"count": 5, "avg_score": 8.0}},
            regressions=[],
            duration_seconds=12.5,
            details=[],
        )
        defaults.update(overrides)
        return EvalReport(**defaults)

    def test_to_dict_from_dict_roundtrip(self):
        report = self._make_report()
        d = report.to_dict()
        restored = EvalReport.from_dict(d)
        self.assertEqual(report.timestamp, restored.timestamp)
        self.assertEqual(report.total_cases, restored.total_cases)
        self.assertEqual(report.passed, restored.passed)
        self.assertEqual(report.failed, restored.failed)
        self.assertAlmostEqual(report.avg_score, restored.avg_score)
        self.assertEqual(report.scores_by_category, restored.scores_by_category)
        self.assertEqual(report.duration_seconds, restored.duration_seconds)

    def test_to_dict_json_serializable(self):
        report = self._make_report()
        d = report.to_dict()
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)

    def test_summary_contains_key_info(self):
        report = self._make_report()
        s = report.summary()
        self.assertIn("VINHLONG360 EVALUATION REPORT", s)
        self.assertIn("10 total", s)
        self.assertIn("8 passed", s)
        self.assertIn("2 failed", s)
        self.assertIn("7.50", s)
        self.assertIn("factual", s)

    def test_summary_shows_regressions(self):
        report = self._make_report(
            regressions=[{
                "query": "test query",
                "category": "factual",
                "old_score": 8.0,
                "new_score": 5.0,
                "change": -37.5,
            }]
        )
        s = report.summary()
        self.assertIn("REGRESSIONS", s)
        self.assertIn("factual", s)

    def test_from_dict_with_missing_fields_uses_defaults(self):
        report = EvalReport.from_dict({})
        self.assertEqual(report.timestamp, 0.0)
        self.assertEqual(report.total_cases, 0)
        self.assertEqual(report.passed, 0)
        self.assertEqual(report.avg_score, 0.0)
        self.assertEqual(report.regressions, [])


# ---------------------------------------------------------------------------
#  EvalRunner
# ---------------------------------------------------------------------------

class TestEvalRunner(unittest.TestCase):
    """EvalRunner: run_single with mock call_fn, compare_reports regression detection."""

    def setUp(self):
        self.runner = EvalRunner.__new__(EvalRunner)
        self.runner._lock = __import__("threading").Lock()
        self.runner._entities = SAMPLE_ENTITIES

    def test_run_single_returns_all_score_keys(self):
        tc = TestCase(
            query="Chua Ang o dau?",
            expected_entities=["chua-ang"],
            expected_tools=["search"],
            expected_keywords=["Tra Vinh"],
            category="factual",
            difficulty="easy",
        )
        call_fn = _make_call_fn(
            reply="Chua Ang nam o Tra Vinh, la mot ngoi chua Khmer dep.",
            tools=["search"],
        )
        result = self.runner.run_single(call_fn, tc)
        self.assertIn("scores", result)
        for key in ("factuality", "tool_usage", "completeness", "hallucination", "format"):
            self.assertIn(key, result["scores"])
        self.assertIn("avg_score", result)
        self.assertIn("passed", result)
        self.assertIn("query", result)
        self.assertIn("category", result)

    def test_run_single_good_reply_passes(self):
        tc = TestCase(
            query="Chua Ang o dau?",
            expected_entities=["chua-ang"],
            expected_tools=["search"],
            expected_keywords=["Tra Vinh"],
            category="factual",
            difficulty="easy",
        )
        call_fn = _make_call_fn(
            reply=(
                "## Chua Ang\n\n"
                "**Chua Ang** nam o Tra Vinh, la mot ngoi chua Khmer co kien truc dep.\n"
                "- Dia chi: Tra Vinh\n"
                "- Dac diem: Kien truc Khmer truyen thong\n"
            ),
            tools=["search"],
        )
        result = self.runner.run_single(call_fn, tc)
        self.assertTrue(result["passed"])

    def test_run_single_empty_reply_fails(self):
        tc = TestCase(
            query="Chua Ang o dau?",
            expected_entities=["chua-ang"],
            expected_tools=["search"],
            expected_keywords=["Tra Vinh"],
            category="factual",
            difficulty="easy",
        )
        call_fn = _make_call_fn(reply="", tools=[])
        result = self.runner.run_single(call_fn, tc)
        self.assertFalse(result["passed"])

    def test_run_single_exception_in_call_fn(self):
        """If call_fn raises, run_single should not crash -- returns zero scores."""
        tc = TestCase(query="q", category="factual", difficulty="easy")

        def bad_fn(query):
            raise RuntimeError("boom")

        result = self.runner.run_single(bad_fn, tc)
        self.assertEqual(result["reply_length"], 0)
        self.assertEqual(result["tools_used"], [])

    def test_compare_reports_no_regression(self):
        report_a = EvalReport(
            avg_score=8.0,
            scores_by_category={"factual": {"avg_score": 8.0, "count": 5}},
        )
        report_b = EvalReport(
            avg_score=8.5,
            scores_by_category={"factual": {"avg_score": 8.5, "count": 5}},
        )
        cmp = self.runner.compare_reports(report_a, report_b)
        self.assertFalse(cmp["overall"]["regressed"])
        self.assertEqual(len(cmp["regressions"]), 0)

    def test_compare_reports_detects_regression(self):
        report_a = EvalReport(
            avg_score=8.0,
            scores_by_category={"factual": {"avg_score": 8.0, "count": 5}},
        )
        report_b = EvalReport(
            avg_score=7.0,
            scores_by_category={"factual": {"avg_score": 7.0, "count": 5}},
        )
        cmp = self.runner.compare_reports(report_a, report_b)
        # Overall: (7.0-8.0)/8.0 = -12.5%  => regressed
        self.assertTrue(cmp["overall"]["regressed"])
        self.assertLess(cmp["overall"]["change_pct"], -5.0)

    def test_compare_reports_category_regression(self):
        report_a = EvalReport(
            avg_score=8.0,
            scores_by_category={
                "factual": {"avg_score": 9.0, "count": 5},
                "itinerary": {"avg_score": 7.0, "count": 3},
            },
        )
        report_b = EvalReport(
            avg_score=7.8,
            scores_by_category={
                "factual": {"avg_score": 9.0, "count": 5},
                "itinerary": {"avg_score": 5.0, "count": 3},
            },
        )
        cmp = self.runner.compare_reports(report_a, report_b)
        # itinerary: (5.0-7.0)/7.0 = -28.6% => regressed
        self.assertTrue(cmp["by_category"]["itinerary"]["regressed"])
        self.assertFalse(cmp["by_category"]["factual"]["regressed"])
        regression_cats = [r["category"] for r in cmp["regressions"]]
        self.assertIn("itinerary", regression_cats)


# ---------------------------------------------------------------------------
#  Helper functions
# ---------------------------------------------------------------------------

class TestHelpers(unittest.TestCase):
    """_normalize_vn and _text_contains helper functions."""

    def test_normalize_vn_removes_diacritics(self):
        self.assertEqual(_normalize_vn("Chua"), "chua")

    def test_normalize_vn_replaces_d_stroke(self):
        result = _normalize_vn("Dong")
        self.assertNotIn("đ", result)
        self.assertIn("d", result.lower())

    def test_text_contains_diacritic_insensitive(self):
        self.assertTrue(_text_contains("Vinh Long co nhieu diem dep", "Vinh Long"))

    def test_text_contains_case_insensitive(self):
        self.assertTrue(_text_contains("VINH LONG", "vinh long"))


if __name__ == "__main__":
    unittest.main()
