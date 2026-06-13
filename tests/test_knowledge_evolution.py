"""Tests for knowledge_evolution.py -- Level 7 knowledge evolution engine."""

import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

# Mock the knowledge module before importing knowledge_evolution
_mock_entities = {
    "e1": {
        "id": "e1", "type": "dish", "name": "Bun nuoc leo",
        "summary": "Mon bun nuoc leo truyen thong Vinh Long voi huong vi dam da mien Tay.",
        "placeId": "p1", "confidence": 0.8,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "https://example.com",
        "season": {"peak": [1, 2, 3]},
    },
    "e2": {
        "id": "e2", "type": "dish", "name": "Banh khot",
        "summary": "Short",
        "placeId": "p1", "confidence": 0.7,
        "updatedAt": "2020-01-01T00:00:00",
        "source": "https://example.com",
        "season": {"peak": [1, 2, 3]},
    },
    "e3": {
        "id": "e3", "type": "attraction", "name": "Cu Lao An Binh",
        "summary": "Cu Lao An Binh la diem du lich noi tieng voi vuon trai cay va song nuoc mien Tay.",
        "placeId": "p2", "confidence": 0.9,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "https://example.com/attraction",
    },
    "e4": {
        "id": "e4", "type": "accommodation", "name": "Homestay Ut Trinh",
        "summary": "",
        "placeId": "p2",
    },
}

_mock_all_entities = dict(_mock_entities)
_mock_all_entities["p1"] = {"id": "p1", "type": "place", "name": "Vinh Long City", "area": "vinh-long-city"}
_mock_all_entities["p2"] = {"id": "p2", "type": "place", "name": "Long Ho", "area": "long-ho"}

_mock_relationships = [
    {"from": "e1", "to": "e2", "type": "similar"},
]


def _mock_ensure():
    pass


# Patch only while importing knowledge_evolution, then restore sys.modules so
# other test modules can import the real knowledge module in the same pytest run.
_mock_kb = MagicMock()
_mock_kb._ensure = _mock_ensure
_mock_kb._entities = _mock_all_entities
_mock_kb._relationships = _mock_relationships

_original_knowledge = sys.modules.get("knowledge")
_original_agent_knowledge = sys.modules.get("agent.knowledge")
sys.modules["knowledge"] = _mock_kb
sys.modules["agent.knowledge"] = _mock_kb

import knowledge_evolution as ke

if _original_knowledge is not None:
    sys.modules["knowledge"] = _original_knowledge
else:
    sys.modules.pop("knowledge", None)
if _original_agent_knowledge is not None:
    sys.modules["agent.knowledge"] = _original_agent_knowledge
else:
    sys.modules.pop("agent.knowledge", None)


class TestSchemaAnalyzer(unittest.TestCase):
    """Tests for SchemaAnalyzer."""

    def setUp(self):
        self.analyzer = ke.SchemaAnalyzer()

    def test_analyze_schema_returns_dict(self):
        result = self.analyzer.analyze_schema()
        self.assertIsInstance(result, dict)
        self.assertIn("total", result)
        self.assertIn("fields", result)
        self.assertIn("types", result)
        self.assertIn("coverage", result)

    def test_analyze_schema_total_count(self):
        result = self.analyzer.analyze_schema()
        # Only content entities (not places)
        self.assertGreater(result["total"], 0)

    def test_get_field_coverage_returns_dict(self):
        coverage = self.analyzer.get_field_coverage()
        self.assertIsInstance(coverage, dict)
        # "id" should be present in 100% of entities
        self.assertEqual(coverage.get("id", 0.0), 1.0)

    def test_get_type_distribution(self):
        dist = self.analyzer.get_type_distribution()
        self.assertIsInstance(dist, dict)
        self.assertIn("dish", dist)
        self.assertEqual(dist["dish"], 2)


class TestRelationInferrer(unittest.TestCase):
    """Tests for RelationInferrer."""

    def setUp(self):
        self.inferrer = ke.RelationInferrer()
        self.inferrer._relations = []  # Start fresh

    def test_infer_relations_returns_list(self):
        result = self.inferrer.infer_relations(entities=ke._content_entities())
        self.assertIsInstance(result, list)

    def test_infer_relations_finds_located_in(self):
        """Entities with same placeId should get located_in relation."""
        result = self.inferrer.infer_relations(entities=ke._content_entities())
        located_in = [r for r in result if r["type"] == "located_in"]
        # e1 and e2 share placeId p1
        self.assertTrue(len(located_in) > 0)

    def test_get_relation_types(self):
        self.inferrer.infer_relations(entities=ke._content_entities())
        types = self.inferrer.get_relation_types()
        self.assertIsInstance(types, list)


class TestKnowledgeGapDetector(unittest.TestCase):
    """Tests for KnowledgeGapDetector."""

    def setUp(self):
        self.detector = ke.KnowledgeGapDetector()

    def test_detect_gaps_returns_list(self):
        gaps = self.detector.detect_gaps()
        self.assertIsInstance(gaps, list)

    def test_detect_gaps_finds_thin_description(self):
        """e2 has summary 'Short' (<50 chars), e4 has empty summary."""
        gaps = self.detector.detect_gaps()
        thin = [g for g in gaps if g["type"] == "thin_description"]
        thin_ids = [g["entity_id"] for g in thin]
        self.assertIn("e2", thin_ids)
        self.assertIn("e4", thin_ids)

    def test_detect_gaps_finds_stale_data(self):
        """e2 has updatedAt in 2020, >180 days ago."""
        gaps = self.detector.detect_gaps()
        stale = [g for g in gaps if g["type"] == "stale_data"]
        stale_ids = [g["entity_id"] for g in stale]
        self.assertIn("e2", stale_ids)

    def test_detect_gaps_finds_missing_category(self):
        """Most CARD_TYPES have <5 entities."""
        gaps = self.detector.detect_gaps()
        missing_cat = [g for g in gaps if g["type"] == "missing_category"]
        self.assertTrue(len(missing_cat) > 0)

    def test_get_coverage_score(self):
        score = self.detector.get_coverage_score()
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)


class TestEvolutionTracker(unittest.TestCase):
    """Tests for EvolutionTracker."""

    def setUp(self):
        self.tracker = ke.EvolutionTracker()
        self.tracker._changelog = []  # Start fresh

    def test_record_change(self):
        self.tracker.record_change(
            entity_id="e1", field="summary",
            old_value="old text", new_value="new text",
            source="test",
        )
        self.assertEqual(len(self.tracker._changelog), 1)
        entry = self.tracker._changelog[0]
        self.assertEqual(entry["entity_id"], "e1")
        self.assertEqual(entry["field"], "summary")

    def test_get_changelog(self):
        self.tracker.record_change("e1", "name", "old", "new", "test")
        self.tracker.record_change("e2", "name", "old", "new", "test")
        # All changes
        changes = self.tracker.get_changelog(days=1)
        self.assertEqual(len(changes), 2)

    def test_get_changelog_filtered_by_entity(self):
        self.tracker.record_change("e1", "name", "old", "new", "test")
        self.tracker.record_change("e2", "name", "old", "new", "test")
        changes = self.tracker.get_changelog(entity_id="e1", days=1)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["entity_id"], "e1")


class TestAutoEnricher(unittest.TestCase):
    """Tests for AutoEnricher."""

    def setUp(self):
        self.enricher = ke.AutoEnricher()

    def test_suggest_enrichments(self):
        suggestions = self.enricher.suggest_enrichments("e4")
        self.assertIsInstance(suggestions, list)
        # e4 is missing several fields that e1-e3 have

    def test_suggest_enrichments_for_nonexistent(self):
        suggestions = self.enricher.suggest_enrichments("nonexistent_id")
        self.assertEqual(suggestions, [])


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for module-level convenience functions."""

    def test_analyze_knowledge(self):
        result = ke.analyze_knowledge()
        self.assertIsInstance(result, dict)
        self.assertIn("schema", result)
        self.assertIn("gaps", result)
        self.assertIn("relations", result)
        self.assertIn("coverage_score", result)

    def test_get_knowledge_score(self):
        result = ke.get_knowledge_score()
        self.assertIsInstance(result, dict)
        self.assertIn("overall", result)
        self.assertIn("breakdown", result)
        self.assertIn("grade", result)
        self.assertIn("total_entities", result)
        # Grade should be a letter
        self.assertIn(result["grade"], ["A", "B", "C", "D", "F"])


if __name__ == "__main__":
    unittest.main()
