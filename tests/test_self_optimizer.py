"""Tests for agent/self_optimizer.py -- Auto Prompt Tuning & Parameter Optimization."""

import sys
import os
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from self_optimizer import (
    PerformanceCollector,
    PromptOptimizer,
    ParameterTuner,
    ToolWeightOptimizer,
    OptimizationReport,
    _categorize_query,
    _clamp,
    should_optimize,
    record_outcome,
    get_optimization_report,
    TEMP_MIN,
    TEMP_MAX,
    ROUNDS_MIN,
    ROUNDS_MAX,
    TOOL_CALLS_MIN,
    TOOL_CALLS_MAX,
    DEFAULT_PARAMS,
    MAX_RECORDS,
)


# ---- _categorize_query ----


class TestCategorizeQuery(unittest.TestCase):
    def test_itinerary(self):
        self.assertEqual(_categorize_query("lịch trình 3 ngày"), "itinerary")
        self.assertEqual(_categorize_query("plan for visit"), "itinerary")

    def test_food(self):
        self.assertEqual(_categorize_query("ăn gì ở vinh long"), "food")
        self.assertEqual(_categorize_query("món đặc sản"), "food")

    def test_history(self):
        self.assertEqual(_categorize_query("lịch sử vinh long"), "history")

    def test_culture(self):
        self.assertEqual(_categorize_query("lễ hội khmer"), "culture")
        self.assertEqual(_categorize_query("văn hóa mekong"), "culture")

    def test_comparison(self):
        self.assertEqual(_categorize_query("so sánh vinh long ben tre"), "comparison")

    def test_general(self):
        self.assertEqual(_categorize_query("xin chao"), "general")


# ---- _clamp ----


class TestClamp(unittest.TestCase):
    def test_within_range(self):
        self.assertEqual(_clamp(5, 0, 10), 5)

    def test_below_min(self):
        self.assertEqual(_clamp(-1, 0, 10), 0)

    def test_above_max(self):
        self.assertEqual(_clamp(15, 0, 10), 10)


# ---- PerformanceCollector ----


class TestPerformanceCollector(unittest.TestCase):
    def setUp(self):
        self.collector = PerformanceCollector()
        # Clear internal records for isolation
        self.collector._records = []

    def test_record_adds_entry(self):
        self.collector._save = lambda: None  # disable persistence
        self.collector.record(
            session_id="s1",
            query="test query",
            agent_name="GeneralAgent",
            tools_used=["search"],
            quality_score=7.5,
            duration=1.2,
            token_count=200,
        )
        self.assertEqual(self.collector.total_count, 1)

    def test_record_categorizes_query(self):
        self.collector._save = lambda: None
        self.collector.record(
            session_id="s1",
            query="ăn gì ở vinh long",
            agent_name="GeneralAgent",
            tools_used=[],
            quality_score=6.0,
            duration=1.0,
            token_count=100,
        )
        self.assertEqual(self.collector._records[0]["category"], "food")

    def test_get_stats_empty_window(self):
        stats = self.collector.get_stats(window_hours=24)
        self.assertEqual(stats["total_records"], 0)
        self.assertEqual(stats["avg_score"], 0.0)
        self.assertEqual(stats["by_agent"], {})

    def test_get_stats_with_records(self):
        self.collector._save = lambda: None
        now = time.time()
        for i in range(5):
            self.collector._records.append({
                "session_id": f"s{i}",
                "query": "test",
                "category": "general",
                "agent_name": "GeneralAgent",
                "tools_used": ["search"] if i % 2 == 0 else [],
                "quality_score": 7.0,
                "duration": 1.0,
                "token_count": 100,
                "timestamp": now,
            })
        stats = self.collector.get_stats(window_hours=1)
        self.assertEqual(stats["total_records"], 5)
        self.assertEqual(stats["avg_score"], 7.0)
        self.assertIn("GeneralAgent", stats["by_agent"])
        self.assertIn("general", stats["by_category"])

    def test_get_stats_window_filtering(self):
        self.collector._save = lambda: None
        old_time = time.time() - 100 * 3600  # 100 hours ago
        recent_time = time.time()
        self.collector._records = [
            {
                "session_id": "old",
                "query": "old query",
                "category": "general",
                "agent_name": "GeneralAgent",
                "tools_used": [],
                "quality_score": 3.0,
                "duration": 1.0,
                "token_count": 100,
                "timestamp": old_time,
            },
            {
                "session_id": "new",
                "query": "new query",
                "category": "general",
                "agent_name": "GeneralAgent",
                "tools_used": ["search"],
                "quality_score": 9.0,
                "duration": 0.5,
                "token_count": 200,
                "timestamp": recent_time,
            },
        ]
        stats = self.collector.get_stats(window_hours=24)
        self.assertEqual(stats["total_records"], 1)
        self.assertEqual(stats["avg_score"], 9.0)

    def test_max_records_trimming(self):
        self.collector._save = lambda: None
        self.collector._records = [
            {
                "session_id": f"s{i}",
                "query": "q",
                "category": "general",
                "agent_name": "A",
                "tools_used": [],
                "quality_score": 5.0,
                "duration": 1.0,
                "token_count": 100,
                "timestamp": time.time(),
            }
            for i in range(MAX_RECORDS + 10)
        ]
        self.collector.record(
            session_id="overflow",
            query="overflow",
            agent_name="A",
            tools_used=[],
            quality_score=8.0,
            duration=0.5,
            token_count=50,
        )
        self.assertLessEqual(self.collector.total_count, MAX_RECORDS)

    def test_tool_usage_and_hallucination_rates(self):
        self.collector._save = lambda: None
        now = time.time()
        # 2 records with tools, 2 without (1 low-score without tools = hallucination)
        self.collector._records = [
            {"session_id": "s1", "query": "q", "category": "general",
             "agent_name": "A", "tools_used": ["search"], "quality_score": 8.0,
             "duration": 1.0, "token_count": 100, "timestamp": now},
            {"session_id": "s2", "query": "q", "category": "general",
             "agent_name": "A", "tools_used": ["search"], "quality_score": 7.0,
             "duration": 1.0, "token_count": 100, "timestamp": now},
            {"session_id": "s3", "query": "q", "category": "general",
             "agent_name": "A", "tools_used": [], "quality_score": 3.0,
             "duration": 1.0, "token_count": 100, "timestamp": now},
            {"session_id": "s4", "query": "q", "category": "general",
             "agent_name": "A", "tools_used": [], "quality_score": 8.0,
             "duration": 1.0, "token_count": 100, "timestamp": now},
        ]
        stats = self.collector.get_stats(window_hours=1)
        self.assertEqual(stats["tool_usage_rate"], 50.0)
        self.assertEqual(stats["hallucination_rate"], 25.0)


# ---- PromptOptimizer ----


class TestPromptOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = PromptOptimizer()
        self.optimizer._variants = [self.optimizer._default_variant()]
        self.optimizer._active_id = "default"
        self.optimizer._save = lambda: None

    def test_get_current_variant_default(self):
        variant = self.optimizer.get_current_variant()
        self.assertEqual(variant["id"], "default")
        self.assertEqual(variant["prompt_addon"], "")

    def test_propose_variant_comparison_quality(self):
        perf = {
            "by_category": {
                "comparison": {"count": 5, "avg_score": 4.0},
            },
            "tool_usage_rate": 80,
            "avg_reply_length": 500,
            "hallucination_rate": 2,
            "avg_score": 5.0,
        }
        variant = self.optimizer.propose_variant(perf)
        self.assertIn("comparison_quality", variant["rules_applied"])
        self.assertIn("so sanh", variant["prompt_addon"].lower())

    def test_propose_variant_low_tool_usage(self):
        perf = {
            "by_category": {},
            "tool_usage_rate": 30,
            "avg_reply_length": 500,
            "hallucination_rate": 2,
            "avg_score": 7.0,
        }
        variant = self.optimizer.propose_variant(perf)
        self.assertIn("strengthen_tool_use", variant["rules_applied"])

    def test_propose_variant_high_hallucination(self):
        perf = {
            "by_category": {},
            "tool_usage_rate": 80,
            "avg_reply_length": 500,
            "hallucination_rate": 15,
            "avg_score": 7.0,
        }
        variant = self.optimizer.propose_variant(perf)
        self.assertIn("reduce_hallucination", variant["rules_applied"])

    def test_propose_variant_short_replies(self):
        perf = {
            "by_category": {},
            "tool_usage_rate": 80,
            "avg_reply_length": 100,
            "hallucination_rate": 2,
            "avg_score": 7.0,
        }
        variant = self.optimizer.propose_variant(perf)
        self.assertIn("increase_detail", variant["rules_applied"])

    def test_propose_variant_no_rules_needed(self):
        perf = {
            "by_category": {},
            "tool_usage_rate": 80,
            "avg_reply_length": 500,
            "hallucination_rate": 2,
            "avg_score": 8.0,
        }
        variant = self.optimizer.propose_variant(perf)
        self.assertEqual(variant["rules_applied"], [])
        self.assertEqual(variant["prompt_addon"], "")

    def test_activate_variant(self):
        perf = {
            "by_category": {"comparison": {"count": 5, "avg_score": 3.0}},
            "tool_usage_rate": 80,
            "avg_reply_length": 500,
            "hallucination_rate": 2,
            "avg_score": 5.0,
        }
        variant = self.optimizer.propose_variant(perf)
        result = self.optimizer.activate_variant(variant["id"])
        self.assertTrue(result)
        self.assertEqual(self.optimizer.get_current_variant()["id"], variant["id"])

    def test_activate_nonexistent_variant(self):
        result = self.optimizer.activate_variant("nonexistent")
        self.assertFalse(result)

    def test_rollback(self):
        perf = {
            "by_category": {"comparison": {"count": 5, "avg_score": 3.0}},
            "tool_usage_rate": 80,
            "avg_reply_length": 500,
            "hallucination_rate": 2,
            "avg_score": 5.0,
        }
        variant = self.optimizer.propose_variant(perf)
        self.optimizer.activate_variant(variant["id"])
        self.optimizer.rollback()
        self.assertEqual(self.optimizer.get_current_variant()["id"], "default")


# ---- ParameterTuner ----


class TestParameterTuner(unittest.TestCase):
    def setUp(self):
        self.tuner = ParameterTuner()
        self.tuner._save = lambda: None

    def test_get_optimal_params_known_category(self):
        params = self.tuner.get_optimal_params("itinerary")
        self.assertIn("temperature", params)
        self.assertIn("max_rounds", params)
        self.assertIn("max_tool_calls", params)

    def test_get_optimal_params_unknown_falls_back_to_general(self):
        params = self.tuner.get_optimal_params("nonexistent_category")
        general = DEFAULT_PARAMS["general"]
        self.assertEqual(params["temperature"], general["temperature"])

    def test_get_optimal_params_bounded(self):
        for cat, params in self.tuner.get_all_params().items():
            self.assertGreaterEqual(params["temperature"], TEMP_MIN)
            self.assertLessEqual(params["temperature"], TEMP_MAX)
            self.assertGreaterEqual(params["max_rounds"], ROUNDS_MIN)
            self.assertLessEqual(params["max_rounds"], ROUNDS_MAX)
            self.assertGreaterEqual(params["max_tool_calls"], TOOL_CALLS_MIN)
            self.assertLessEqual(params["max_tool_calls"], TOOL_CALLS_MAX)

    def test_tune_high_variance_lowers_temperature(self):
        original = self.tuner.get_optimal_params("general")
        perf = {
            "by_category": {
                "general": {"count": 10, "avg_score": 5.0, "score_std": 3.0},
            }
        }
        adjustments = self.tuner.tune(perf)
        if "general" in adjustments:
            self.assertLess(adjustments["general"]["temperature"], original["temperature"])

    def test_tune_low_score_increases_rounds(self):
        original = self.tuner.get_optimal_params("general")
        perf = {
            "by_category": {
                "general": {"count": 10, "avg_score": 4.0, "score_std": 1.5},
            }
        }
        adjustments = self.tuner.tune(perf)
        if "general" in adjustments:
            self.assertGreaterEqual(adjustments["general"]["max_rounds"], original["max_rounds"])

    def test_increment_query_count(self):
        self.tuner._queries_since_tune = 0
        for _ in range(99):
            self.assertFalse(self.tuner.increment_query_count())
        self.assertTrue(self.tuner.increment_query_count())

    def test_tune_not_enough_data_skipped(self):
        perf = {
            "by_category": {
                "general": {"count": 2, "avg_score": 3.0, "score_std": 3.0},
            }
        }
        adjustments = self.tuner.tune(perf)
        self.assertEqual(adjustments, {})


# ---- ToolWeightOptimizer ----


class TestToolWeightOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = ToolWeightOptimizer()
        self.optimizer._save = lambda: None

    def test_get_tool_scores_empty(self):
        self.optimizer._tool_data = {"scores": {}}
        scores = self.optimizer.get_tool_scores()
        self.assertIsInstance(scores, dict)

    def test_update_scores_with_records(self):
        now = time.time()
        records = [
            {"tools_used": ["search"], "quality_score": 8.0, "timestamp": now},
            {"tools_used": ["search", "entity_detail"], "quality_score": 9.0, "timestamp": now},
            {"tools_used": [], "quality_score": 4.0, "timestamp": now},
        ]
        self.optimizer.update_scores(records)
        scores = self.optimizer.get_tool_scores()
        self.assertIn("search", scores)

    def test_suggest_tool_order_returns_list(self):
        order = self.optimizer.suggest_tool_order("comparison")
        self.assertIsInstance(order, list)
        self.assertGreater(len(order), 0)
        # Category-specific tools should come first
        self.assertEqual(order[0], "compare_areas")

    def test_suggest_tool_order_general(self):
        order = self.optimizer.suggest_tool_order("general")
        self.assertEqual(order[0], "search")

    def test_get_unused_tools(self):
        # All tools are unused since no data
        self.optimizer._tool_data = {"scores": {}}
        unused = self.optimizer.get_unused_tools(window_hours=168)
        self.assertEqual(set(unused), set(self.optimizer.ALL_TOOLS))

    def test_get_unused_tools_some_recent(self):
        now = time.time()
        self.optimizer._tool_data = {
            "scores": {
                "search": {"last_used": now, "effectiveness": 10},
                "web_search": {"last_used": 0, "effectiveness": 0},
            }
        }
        unused = self.optimizer.get_unused_tools(window_hours=1)
        self.assertNotIn("search", unused)
        self.assertIn("web_search", unused)


# ---- OptimizationReport ----


class TestOptimizationReport(unittest.TestCase):
    def test_to_dict(self):
        report = OptimizationReport(
            current_variant={"id": "default"},
            param_recommendations={"general": {"temperature": 0.5}},
            tool_effectiveness={"search": 10},
            quality_trend={"direction": "stable"},
            action_items=["Review prompts"],
        )
        d = report.to_dict()
        self.assertIn("current_variant", d)
        self.assertIn("action_items", d)
        self.assertEqual(d["quality_trend"]["direction"], "stable")


# ---- Convenience functions ----


class TestConvenienceFunctions(unittest.TestCase):
    def test_should_optimize_returns_bool(self):
        result = should_optimize()
        self.assertIsInstance(result, bool)

    def test_get_optimization_report_returns_dict(self):
        report = get_optimization_report()
        self.assertIsInstance(report, dict)
        self.assertIn("current_variant", report)
        self.assertIn("quality_trend", report)
        self.assertIn("action_items", report)


if __name__ == "__main__":
    unittest.main()
