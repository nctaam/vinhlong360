"""Tests for dynamic_agents.py -- Level 7 self-creating specialist agents."""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from dynamic_agents import (
    AgentSpec,
    AgentFactory,
    DynamicRouter,
    PatternAnalyzer,
    AgentEvolution,
    check_dynamic_route,
)


class TestAgentSpec(unittest.TestCase):
    """Tests for AgentSpec dataclass."""

    def test_to_dict(self):
        spec = AgentSpec(
            agent_id="test-001",
            name="TestAgent",
            description="desc",
            system_prompt_addon="prompt",
            trigger_patterns=[r"test"],
            tool_whitelist=None,
            priority=50,
            created_at=time.time(),
            created_by="manual",
        )
        d = spec.to_dict()
        self.assertEqual(d["agent_id"], "test-001")
        self.assertEqual(d["name"], "TestAgent")
        self.assertTrue(d["active"])

    def test_from_dict_roundtrip(self):
        spec = AgentSpec(
            agent_id="test-002",
            name="RoundTripAgent",
            description="roundtrip test",
            system_prompt_addon="addon",
            trigger_patterns=[r"\bfood\b"],
            tool_whitelist=["search"],
            priority=75,
            created_at=time.time(),
            created_by="auto",
        )
        d = spec.to_dict()
        restored = AgentSpec.from_dict(d)
        self.assertEqual(restored.agent_id, spec.agent_id)
        self.assertEqual(restored.name, spec.name)
        self.assertEqual(restored.trigger_patterns, spec.trigger_patterns)
        self.assertEqual(restored.tool_whitelist, ["search"])

    def test_from_dict_defaults_performance(self):
        d = {
            "agent_id": "id1", "name": "N", "description": "D",
            "system_prompt_addon": "P", "trigger_patterns": [],
            "tool_whitelist": None, "priority": 1,
            "created_at": 0.0, "created_by": "manual",
        }
        spec = AgentSpec.from_dict(d)
        self.assertEqual(spec.performance["queries_handled"], 0)
        self.assertEqual(spec.performance["avg_score"], 0.0)
        self.assertTrue(spec.active)


class TestAgentFactory(unittest.TestCase):
    """Tests for AgentFactory."""

    def setUp(self):
        self.factory = AgentFactory()

    def test_pre_seeded_agents_exist(self):
        agents = self.factory.get_active_agents()
        names = {a.name for a in agents}
        self.assertIn("FoodAgent", names)
        self.assertIn("FestivalAgent", names)
        self.assertIn("TransportAgent", names)

    def test_create_agent(self):
        agent = self.factory.create_agent(
            name="NewTestAgent",
            description="test desc",
            trigger_patterns=[r"\bnew_pattern\b"],
            system_prompt_addon="test addon",
        )
        self.assertEqual(agent.name, "NewTestAgent")
        self.assertTrue(agent.active)
        # Clean up
        self.factory.deactivate(agent.agent_id)

    def test_get_active_agents_sorted_by_priority(self):
        agents = self.factory.get_active_agents()
        for i in range(len(agents) - 1):
            self.assertGreaterEqual(agents[i].priority, agents[i + 1].priority)

    def test_deactivate(self):
        agent = self.factory.create_agent(
            name="DeactivateMe",
            description="will be deactivated",
            trigger_patterns=[r"deactivate_test"],
            system_prompt_addon="addon",
        )
        self.factory.deactivate(agent.agent_id)
        fetched = self.factory.get_agent(agent.agent_id)
        self.assertFalse(fetched.active)

    def test_max_limit_raises(self):
        """Creating agents beyond DYNAMIC_AGENT_MAX should raise ValueError."""
        created = []
        try:
            for i in range(20):
                a = self.factory.create_agent(
                    name=f"Overflow_{i}",
                    description="overflow test",
                    trigger_patterns=[f"overflow_{i}"],
                    system_prompt_addon="addon",
                )
                created.append(a)
        except ValueError:
            pass  # Expected
        else:
            # If no error, we may have had room; just verify total count is bounded
            active = self.factory.get_active_agents()
            self.assertLessEqual(len(active), 20)
        finally:
            for a in created:
                self.factory.deactivate(a.agent_id)


class TestDynamicRouter(unittest.TestCase):
    """Tests for DynamicRouter."""

    def setUp(self):
        self.factory = AgentFactory()
        self.router = DynamicRouter(self.factory)

    def test_route_matches_food_agent(self):
        matched = self.router.route("cho toi biet ve mon an dac san Vinh Long")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "FoodAgent")

    def test_route_matches_festival_agent(self):
        matched = self.router.route("le hoi truyen thong Vinh Long")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "FestivalAgent")

    def test_route_no_match_returns_none(self):
        matched = self.router.route("what is the meaning of life?")
        self.assertIsNone(matched)

    def test_route_case_insensitive(self):
        matched = self.router.route("MON AN DAC SAN")
        self.assertIsNotNone(matched)


class TestPatternAnalyzer(unittest.TestCase):
    """Tests for PatternAnalyzer."""

    def setUp(self):
        self.analyzer = PatternAnalyzer()

    def test_extract_keywords(self):
        queries = ["mon an ngon Vinh Long", "dac san Vinh Long ngon lam"]
        kw = self.analyzer.extract_keywords(queries)
        self.assertIsInstance(kw, dict)
        self.assertIn("vinh", kw)
        self.assertIn("long", kw)
        self.assertIn("ngon", kw)

    def test_extract_keywords_excludes_stop_words(self):
        queries = ["cac mon an cua Vinh Long"]
        kw = self.analyzer.extract_keywords(queries)
        # "cac" and "cua" are stop words
        self.assertNotIn("cac", kw)
        self.assertNotIn("cua", kw)

    def test_cluster_queries(self):
        queries = [
            {"text": "mon an ngon Vinh Long"},
            {"text": "dac san am thuc Vinh Long"},
            {"text": "thoi tiet hom nay"},
        ]
        clusters = self.analyzer.cluster_queries(queries, threshold=0.3)
        self.assertIsInstance(clusters, list)
        self.assertGreater(len(clusters), 0)


class TestAgentEvolution(unittest.TestCase):
    """Tests for AgentEvolution."""

    def setUp(self):
        self.factory = AgentFactory()
        self.evolution = AgentEvolution(self.factory)

    def test_evaluate_agents_returns_list(self):
        results = self.evolution.evaluate_agents()
        self.assertIsInstance(results, list)

    def test_evaluate_agents_auto_deactivation_low_usage(self):
        """Agent with <20 queries and >7 days old should be deactivated."""
        agent = self.factory.create_agent(
            name="OldLowUsageAgent",
            description="test",
            trigger_patterns=[r"oldlowusage"],
            system_prompt_addon="addon",
        )
        # Simulate old agent with low usage
        agent.created_at = time.time() - 8 * 86400  # 8 days old
        agent.performance["queries_handled"] = 3

        results = self.evolution.evaluate_agents()
        deactivated = [r for r in results if r["agent_id"] == agent.agent_id and r["status"] == "deactivated"]
        self.assertTrue(len(deactivated) > 0)

    def test_evaluate_agents_auto_deactivation_low_score(self):
        """Agent with avg_score < 3.0 and >= 5 queries should be deactivated."""
        agent = self.factory.create_agent(
            name="LowScoreAgent",
            description="test",
            trigger_patterns=[r"lowscore"],
            system_prompt_addon="addon",
        )
        agent.performance["queries_handled"] = 10
        agent.performance["avg_score"] = 2.0

        results = self.evolution.evaluate_agents()
        deactivated = [r for r in results if r["agent_id"] == agent.agent_id and r["status"] == "deactivated"]
        self.assertTrue(len(deactivated) > 0)


class TestCheckDynamicRoute(unittest.TestCase):
    """Tests for check_dynamic_route convenience function."""

    def test_returns_dict_on_match(self):
        result = check_dynamic_route("quan an ngon nhat Vinh Long")
        self.assertIsNotNone(result)
        self.assertIn("agent_id", result)
        self.assertIn("name", result)
        self.assertIn("system_prompt_addon", result)

    def test_returns_none_on_no_match(self):
        result = check_dynamic_route("random unrelated topic about astronomy")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
