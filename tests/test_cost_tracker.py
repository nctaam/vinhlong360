"""Tests for agent/cost_tracker.py — Token Usage & Cost Attribution."""
import os
import sys
import tempfile
import unittest
from collections import deque
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import cost_tracker as mod
from cost_tracker import (
    BudgetManager,
    CostAttribution,
    TokenCounter,
    get_cost_report,
    track_llm_call,
)


# ══════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════

def _make_response(prompt_tokens=100, completion_tokens=50, total_tokens=150):
    """Build a mock OpenAI-compatible response with usage."""
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    return SimpleNamespace(usage=usage)


def _fresh_attribution():
    """Create a CostAttribution with no disk persistence."""
    with patch.object(CostAttribution, "_load"):
        attr = CostAttribution()
    attr._records = deque(maxlen=10_000)
    return attr


def _record_helper(attr, session_id="s1", agent_name="knowledge",
                   tool_name="search", model="cx/gpt-5.4-mini",
                   prompt_tokens=100, completion_tokens=50, cost=0.001,
                   date=None):
    """Insert a record with optional date override."""
    tokens = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    attr.record(session_id, "query text", agent_name, tool_name, model, tokens, cost)
    if date is not None:
        # patch the date/timestamp on the last appended record
        attr._records[-1]["date"] = date
        attr._records[-1]["timestamp"] = date + "T00:00:00"


# ══════════════════════════════════════════════════
#  TokenCounter tests
# ══════════════════════════════════════════════════

class TestTokenCounterCountFromResponse(unittest.TestCase):

    def setUp(self):
        self.counter = TokenCounter()

    def test_count_from_response_normal(self):
        resp = _make_response(200, 80, 280)
        result = self.counter.count_from_response(resp)
        self.assertEqual(result["prompt_tokens"], 200)
        self.assertEqual(result["completion_tokens"], 80)
        self.assertEqual(result["total_tokens"], 280)

    def test_count_from_response_zero_total_recalculated(self):
        """When total_tokens is 0 but prompt/completion exist, total is recomputed."""
        resp = _make_response(100, 50, 0)
        result = self.counter.count_from_response(resp)
        self.assertEqual(result["total_tokens"], 150)

    def test_count_from_response_no_usage_attr(self):
        """Response without .usage returns all zeros."""
        resp = {"some": "dict"}
        result = self.counter.count_from_response(resp)
        self.assertEqual(result["prompt_tokens"], 0)
        self.assertEqual(result["completion_tokens"], 0)
        self.assertEqual(result["total_tokens"], 0)

    def test_count_from_response_none_fields(self):
        """Usage with None fields treated as 0."""
        usage = SimpleNamespace(prompt_tokens=None, completion_tokens=None, total_tokens=None)
        resp = SimpleNamespace(usage=usage)
        result = self.counter.count_from_response(resp)
        self.assertEqual(result["prompt_tokens"], 0)
        self.assertEqual(result["completion_tokens"], 0)
        self.assertEqual(result["total_tokens"], 0)


class TestTokenCounterEstimate(unittest.TestCase):

    def setUp(self):
        self.counter = TokenCounter()

    def test_estimate_tokens_empty(self):
        self.assertEqual(self.counter.estimate_tokens(""), 0)

    def test_estimate_tokens_english(self):
        """Pure English: ~4 chars/token."""
        text = "Hello world this is a test"  # 26 chars
        est = self.counter.estimate_tokens(text)
        # 26 / 4.0 = 6.5 -> round -> 7
        self.assertEqual(est, 7)

    def test_estimate_tokens_vietnamese(self):
        """Vietnamese text should yield more tokens per char (lower chars_per_token)."""
        # Heavy Vietnamese diacritics to ensure ratio is meaningful
        viet = "Đặc sản Vĩnh Long là bưởi Năm Roi và chôm chôm"
        eng = "a" * len(viet)  # same char count, pure ASCII
        est_viet = self.counter.estimate_tokens(viet)
        est_eng = self.counter.estimate_tokens(eng)
        # Vietnamese text should produce MORE tokens for same length
        # because chars_per_token is lower (closer to 2)
        self.assertGreater(est_viet, est_eng)

    def test_estimate_tokens_minimum_one(self):
        """Even a single char returns at least 1 token."""
        self.assertGreaterEqual(self.counter.estimate_tokens("a"), 1)


class TestTokenCounterCalculateCost(unittest.TestCase):

    def setUp(self):
        self.counter = TokenCounter()

    def test_calculate_cost_gpt54(self):
        tokens = {"prompt_tokens": 1000, "completion_tokens": 1000}
        cost = self.counter.calculate_cost(tokens, "cx/gpt-5.4")
        # input: (1000/1000)*0.005 = 0.005
        # output: (1000/1000)*0.015 = 0.015
        self.assertAlmostEqual(cost, 0.02, places=6)

    def test_calculate_cost_gpt54_mini(self):
        tokens = {"prompt_tokens": 1000, "completion_tokens": 1000}
        cost = self.counter.calculate_cost(tokens, "cx/gpt-5.4-mini")
        # input: (1000/1000)*0.0002 = 0.0002
        # output: (1000/1000)*0.0006 = 0.0006
        self.assertAlmostEqual(cost, 0.0008, places=6)

    def test_calculate_cost_unknown_model_uses_default(self):
        tokens = {"prompt_tokens": 1000, "completion_tokens": 1000}
        cost = self.counter.calculate_cost(tokens, "unknown/model-x")
        # default input: 0.001, output: 0.003 => 0.004
        self.assertAlmostEqual(cost, 0.004, places=6)

    def test_calculate_cost_zero_tokens(self):
        tokens = {"prompt_tokens": 0, "completion_tokens": 0}
        cost = self.counter.calculate_cost(tokens, "cx/gpt-5.4")
        self.assertEqual(cost, 0.0)


# ══════════════════════════════════════════════════
#  CostAttribution tests
# ══════════════════════════════════════════════════

class TestCostAttributionRecord(unittest.TestCase):

    def test_record_appends_entry(self):
        attr = _fresh_attribution()
        _record_helper(attr)
        self.assertEqual(len(attr._records), 1)
        entry = attr._records[0]
        self.assertEqual(entry["session_id"], "s1")
        self.assertEqual(entry["agent_name"], "knowledge")
        self.assertEqual(entry["tool_name"], "search")
        self.assertEqual(entry["cost"], 0.001)

    def test_record_truncates_query_to_200(self):
        attr = _fresh_attribution()
        long_query = "x" * 500
        tokens = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        attr.record("s1", long_query, "agent", None, "cx/gpt-5.4-mini", tokens, 0.0)
        self.assertEqual(len(attr._records[0]["query"]), 200)


class TestCostAttributionGetSessionCost(unittest.TestCase):

    def test_get_session_cost(self):
        attr = _fresh_attribution()
        _record_helper(attr, session_id="sess-A", cost=0.01)
        _record_helper(attr, session_id="sess-A", cost=0.02)
        _record_helper(attr, session_id="sess-B", cost=0.05)
        info = attr.get_session_cost("sess-A")
        self.assertEqual(info["session_id"], "sess-A")
        self.assertAlmostEqual(info["total_cost"], 0.03, places=6)
        self.assertEqual(info["query_count"], 2)

    def test_get_session_cost_empty(self):
        attr = _fresh_attribution()
        info = attr.get_session_cost("nonexistent")
        self.assertEqual(info["total_cost"], 0.0)
        self.assertEqual(info["query_count"], 0)


class TestCostAttributionAgentCosts(unittest.TestCase):

    def test_get_agent_costs(self):
        attr = _fresh_attribution()
        _record_helper(attr, agent_name="knowledge", cost=0.01)
        _record_helper(attr, agent_name="knowledge", cost=0.02)
        _record_helper(attr, agent_name="router", cost=0.005)
        agents = attr.get_agent_costs()
        self.assertIn("knowledge", agents)
        self.assertIn("router", agents)
        self.assertAlmostEqual(agents["knowledge"]["cost"], 0.03, places=6)
        self.assertEqual(agents["knowledge"]["queries"], 2)
        self.assertEqual(agents["router"]["queries"], 1)


class TestCostAttributionToolCosts(unittest.TestCase):

    def test_get_tool_costs_with_none(self):
        attr = _fresh_attribution()
        _record_helper(attr, tool_name=None, cost=0.01)
        _record_helper(attr, tool_name="search", cost=0.02)
        tools = attr.get_tool_costs()
        self.assertIn("(no tool)", tools)
        self.assertIn("search", tools)
        self.assertAlmostEqual(tools["(no tool)"]["cost"], 0.01, places=6)
        self.assertEqual(tools["search"]["calls"], 1)


class TestCostAttributionDailyCosts(unittest.TestCase):

    def test_daily_costs_grouped_by_date(self):
        attr = _fresh_attribution()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        _record_helper(attr, cost=0.01, date=today)
        _record_helper(attr, cost=0.02, date=today)
        _record_helper(attr, cost=0.05, date=yesterday)
        days = attr.get_daily_costs(days=7)
        self.assertEqual(len(days), 2)
        # sorted ascending
        self.assertEqual(days[0]["date"], yesterday)
        self.assertEqual(days[1]["date"], today)
        self.assertAlmostEqual(days[1]["cost"], 0.03, places=6)

    def test_daily_costs_excludes_old_dates(self):
        attr = _fresh_attribution()
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
        _record_helper(attr, cost=0.01, date=old_date)
        days = attr.get_daily_costs(days=30)
        self.assertEqual(len(days), 0)


class TestCostAttributionSummary(unittest.TestCase):

    def test_summary_empty(self):
        attr = _fresh_attribution()
        s = attr.get_summary()
        self.assertEqual(s["total_cost"], 0.0)
        self.assertEqual(s["total_queries"], 0)
        self.assertEqual(s["top_expensive_queries"], [])

    def test_summary_with_records(self):
        attr = _fresh_attribution()
        _record_helper(attr, cost=0.01)
        _record_helper(attr, cost=0.03)
        _record_helper(attr, cost=0.02)
        s = attr.get_summary()
        self.assertAlmostEqual(s["total_cost"], 0.06, places=6)
        self.assertEqual(s["total_queries"], 3)
        self.assertAlmostEqual(s["avg_cost_per_query"], 0.02, places=6)
        # top expensive: first is most expensive
        self.assertAlmostEqual(s["top_expensive_queries"][0]["cost"], 0.03, places=6)


class TestCostAttributionFIFOEviction(unittest.TestCase):

    def test_eviction_at_max_records(self):
        attr = _fresh_attribution()
        # Override maxlen to a small number for testing
        attr._records = deque(maxlen=5)
        for i in range(7):
            _record_helper(attr, session_id=f"s{i}", cost=float(i))
        # Only 5 should remain (most recent)
        self.assertEqual(len(attr._records), 5)
        session_ids = [r["session_id"] for r in attr._records]
        self.assertNotIn("s0", session_ids)
        self.assertNotIn("s1", session_ids)
        self.assertIn("s6", session_ids)


class TestCostAttributionPersistence(unittest.TestCase):

    def test_save_and_load(self):
        """Records survive a save+load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "costs.json")
            with patch.object(mod, "COSTS_FILE", mod.Path(test_file)):
                attr = _fresh_attribution()
                _record_helper(attr, cost=0.01)
                _record_helper(attr, cost=0.02)
                attr.force_save()
                self.assertTrue(os.path.exists(test_file))
                # Load into a new instance
                attr2 = _fresh_attribution()
                attr2._load()
                self.assertEqual(len(attr2._records), 2)


class TestCostAttributionAutoSave(unittest.TestCase):

    def test_auto_save_after_interval(self):
        from cost_tracker import _AUTO_SAVE_INTERVAL
        attr = _fresh_attribution()
        with patch.object(attr, "_save") as mock_save:
            for _ in range(_AUTO_SAVE_INTERVAL - 1):
                _record_helper(attr)
            mock_save.assert_not_called()
            _record_helper(attr)
            mock_save.assert_called_once()


# ══════════════════════════════════════════════════
#  BudgetManager tests
# ══════════════════════════════════════════════════

class TestBudgetManagerSetLimit(unittest.TestCase):

    def test_set_limit_valid_scopes(self):
        attr = _fresh_attribution()
        bm = BudgetManager(attr)
        for scope in ("daily", "monthly", "session"):
            bm.set_limit(scope, 42.0)
            self.assertEqual(bm._limits[scope], 42.0)

    def test_set_limit_invalid_scope_raises(self):
        attr = _fresh_attribution()
        bm = BudgetManager(attr)
        with self.assertRaises(ValueError):
            bm.set_limit("weekly", 10.0)


class TestBudgetManagerCheckBudget(unittest.TestCase):

    def test_check_budget_within(self):
        attr = _fresh_attribution()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _record_helper(attr, cost=1.0, date=today)
        bm = BudgetManager(attr)
        bm.set_limit("daily", 10.0)
        result = bm.check_budget("daily")
        self.assertTrue(result["within_budget"])
        self.assertAlmostEqual(result["spent"], 1.0, places=4)
        self.assertAlmostEqual(result["limit"], 10.0, places=4)
        self.assertAlmostEqual(result["remaining"], 9.0, places=4)
        self.assertAlmostEqual(result["utilization_pct"], 10.0, places=1)

    def test_check_budget_exceeded(self):
        attr = _fresh_attribution()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _record_helper(attr, cost=15.0, date=today)
        bm = BudgetManager(attr)
        bm.set_limit("daily", 10.0)
        result = bm.check_budget("daily")
        self.assertFalse(result["within_budget"])
        self.assertAlmostEqual(result["remaining"], 0.0, places=4)

    def test_check_budget_no_limit_set(self):
        """When limit is 0, within_budget is always True, remaining is inf."""
        attr = _fresh_attribution()
        bm = BudgetManager(attr)
        bm.set_limit("session", 0.0)
        result = bm.check_budget("session", session_id="s1")
        self.assertTrue(result["within_budget"])
        self.assertEqual(result["remaining"], float("inf"))

    def test_check_budget_session_scope(self):
        attr = _fresh_attribution()
        _record_helper(attr, session_id="sess-X", cost=2.0)
        _record_helper(attr, session_id="sess-Y", cost=5.0)
        bm = BudgetManager(attr)
        bm.set_limit("session", 3.0)
        result = bm.check_budget("session", session_id="sess-X")
        self.assertTrue(result["within_budget"])
        self.assertAlmostEqual(result["spent"], 2.0, places=4)

    def test_check_budget_monthly_scope(self):
        attr = _fresh_attribution()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _record_helper(attr, cost=50.0, date=today)
        bm = BudgetManager(attr)
        bm.set_limit("monthly", 200.0)
        result = bm.check_budget("monthly")
        self.assertTrue(result["within_budget"])
        self.assertAlmostEqual(result["spent"], 50.0, places=4)

    def test_check_budget_alert_threshold_warning(self):
        """When utilization >= 80%, a warning is logged."""
        attr = _fresh_attribution()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _record_helper(attr, cost=9.0, date=today)
        bm = BudgetManager(attr)
        bm.set_limit("daily", 10.0)
        with self.assertLogs("cost_tracker", level="WARNING") as cm:
            result = bm.check_budget("daily")
        self.assertTrue(any("Budget alert" in msg for msg in cm.output))
        self.assertTrue(result["within_budget"])


# ══════════════════════════════════════════════════
#  track_llm_call convenience function
# ══════════════════════════════════════════════════

class TestTrackLLMCall(unittest.TestCase):

    def setUp(self):
        # Isolate from module singletons
        self._orig_attr = mod.cost_attribution
        self._orig_counter = mod.token_counter
        self._orig_bm = mod.budget_manager
        mod.cost_attribution = _fresh_attribution()
        mod.token_counter = TokenCounter()
        mod.budget_manager = BudgetManager(mod.cost_attribution)

    def tearDown(self):
        mod.cost_attribution = self._orig_attr
        mod.token_counter = self._orig_counter
        mod.budget_manager = self._orig_bm

    def test_track_llm_call_returns_expected_keys(self):
        resp = _make_response(100, 50, 150)
        result = track_llm_call(
            session_id="sess-1",
            agent_name="knowledge",
            model="cx/gpt-5.4-mini",
            response=resp,
            query="What is Vinh Long?",
            tool_name="search",
        )
        self.assertIn("tokens", result)
        self.assertIn("cost", result)
        self.assertIn("budget", result)
        self.assertEqual(result["tokens"]["prompt_tokens"], 100)
        self.assertEqual(result["tokens"]["completion_tokens"], 50)
        self.assertGreater(result["cost"], 0)

    def test_track_llm_call_records_to_attribution(self):
        resp = _make_response(200, 100, 300)
        track_llm_call("s1", "knowledge", "cx/gpt-5.4", resp)
        info = mod.cost_attribution.get_session_cost("s1")
        self.assertEqual(info["query_count"], 1)
        self.assertGreater(info["total_cost"], 0)

    def test_track_llm_call_budget_keys(self):
        resp = _make_response(10, 5, 15)
        result = track_llm_call("s1", "agent", "cx/gpt-5.4-mini", resp)
        self.assertIn("daily", result["budget"])
        self.assertIn("monthly", result["budget"])
        self.assertIn("within_budget", result["budget"]["daily"])


# ══════════════════════════════════════════════════
#  get_cost_report
# ══════════════════════════════════════════════════

class TestGetCostReport(unittest.TestCase):

    def setUp(self):
        self._orig_attr = mod.cost_attribution
        self._orig_bm = mod.budget_manager
        mod.cost_attribution = _fresh_attribution()
        mod.budget_manager = BudgetManager(mod.cost_attribution)

    def tearDown(self):
        mod.cost_attribution = self._orig_attr
        mod.budget_manager = self._orig_bm

    def test_get_cost_report_structure(self):
        report = get_cost_report()
        self.assertIn("summary", report)
        self.assertIn("by_agent", report)
        self.assertIn("by_tool", report)
        self.assertIn("daily_trend", report)
        self.assertIn("budget", report)
        self.assertIn("daily", report["budget"])
        self.assertIn("monthly", report["budget"])

    def test_get_cost_report_with_data(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _record_helper(mod.cost_attribution, agent_name="knowledge",
                       tool_name="search", cost=0.01, date=today)
        report = get_cost_report()
        self.assertEqual(report["summary"]["total_queries"], 1)
        self.assertAlmostEqual(report["summary"]["total_cost"], 0.01, places=6)
        self.assertIn("knowledge", report["by_agent"])
        self.assertIn("search", report["by_tool"])
        self.assertEqual(len(report["daily_trend"]), 1)


if __name__ == "__main__":
    unittest.main()
