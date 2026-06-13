"""Tests for advanced_graph.py -- Level 7 graph analytics."""

import sys
import os
import time
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from advanced_graph import (
    _build_adjacency_list,
    _bfs_components,
    _estimate_diameter,
    CommunityDetector,
    LinkPredictor,
    AnomalyDetector,
    TemporalEvolution,
    GraphAnalytics,
)


# ── Sample data builders ─────────────────────────────────────────────────────

def _sample_nodes():
    return {
        "A": {"id": "A", "type": "user", "properties": {"mention_count": 5}},
        "B": {"id": "B", "type": "entity", "properties": {"mention_count": 3}},
        "C": {"id": "C", "type": "entity", "properties": {"mention_count": 0}},
        "D": {"id": "D", "type": "entity", "properties": {"mention_count": 2}},
        "E": {"id": "E", "type": "entity", "properties": {"mention_count": 0}},
    }


def _sample_edges():
    now = time.time()
    return [
        {"source": "A", "target": "B", "relation": "discussed", "weight": 2.0,
         "timestamps": [now - 3600, now]},
        {"source": "A", "target": "C", "relation": "discussed", "weight": 1.0,
         "timestamps": [now - 7200]},
        {"source": "B", "target": "C", "relation": "co_mentioned", "weight": 1.0,
         "timestamps": [now - 7200]},
        {"source": "B", "target": "D", "relation": "co_mentioned", "weight": 1.0,
         "timestamps": [now - 3600]},
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestBuildAdjacencyList(unittest.TestCase):
    """Tests for _build_adjacency_list helper."""

    def test_basic_undirected(self):
        edges = [{"source": "X", "target": "Y"}]
        adj = _build_adjacency_list(edges)
        self.assertIn("Y", adj["X"])
        self.assertIn("X", adj["Y"])

    def test_empty_edges(self):
        adj = _build_adjacency_list([])
        self.assertEqual(adj, {})

    def test_skips_empty_source_target(self):
        edges = [{"source": "", "target": "Y"}, {"source": "X", "target": ""}]
        adj = _build_adjacency_list(edges)
        self.assertEqual(adj, {})


class TestBfsComponents(unittest.TestCase):
    """Tests for _bfs_components helper."""

    def test_single_component(self):
        adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B"}}
        comps = _bfs_components(adj)
        self.assertEqual(len(comps), 1)
        self.assertEqual(comps[0], {"A", "B", "C"})

    def test_two_components(self):
        adj = {"A": {"B"}, "B": {"A"}, "C": {"D"}, "D": {"C"}}
        comps = _bfs_components(adj)
        self.assertEqual(len(comps), 2)

    def test_empty_graph(self):
        comps = _bfs_components({})
        self.assertEqual(comps, [])

    def test_isolated_node(self):
        adj = {"A": set()}
        comps = _bfs_components(adj)
        self.assertEqual(len(comps), 1)
        self.assertIn("A", comps[0])


class TestCommunityDetector(unittest.TestCase):
    """Tests for CommunityDetector."""

    def setUp(self):
        self.detector = CommunityDetector()

    def test_detect_communities_returns_list_of_sets(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        communities = self.detector.detect_communities(nodes, edges)
        self.assertIsInstance(communities, list)
        for c in communities:
            self.assertIsInstance(c, set)

    def test_all_nodes_covered(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        communities = self.detector.detect_communities(nodes, edges)
        all_detected = set()
        for c in communities:
            all_detected.update(c)
        self.assertEqual(all_detected, set(nodes.keys()))

    def test_get_community_summary_structure(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        self.detector.detect_communities(nodes, edges)
        summaries = self.detector.get_community_summary()
        self.assertIsInstance(summaries, list)
        if summaries:
            s = summaries[0]
            self.assertIn("community_id", s)
            self.assertIn("size", s)
            self.assertIn("top_nodes", s)
            self.assertIn("theme", s)

    def test_get_community_for_known_node(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        self.detector.detect_communities(nodes, edges)
        comm = self.detector.get_community_for("A")
        self.assertIsNotNone(comm)
        self.assertIn("A", comm)

    def test_get_community_for_unknown_node(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        self.detector.detect_communities(nodes, edges)
        self.assertIsNone(self.detector.get_community_for("NONEXISTENT"))


class TestLinkPredictor(unittest.TestCase):
    """Tests for LinkPredictor."""

    def setUp(self):
        self.predictor = LinkPredictor()

    def test_predict_links_returns_tuples(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        predictions = self.predictor.predict_links(nodes, edges, top_k=5)
        self.assertIsInstance(predictions, list)
        for item in predictions:
            self.assertEqual(len(item), 3)
            self.assertIsInstance(item[2], float)

    def test_predict_links_no_existing_edges_predicted(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        existing = set()
        for e in edges:
            existing.add(frozenset((e["source"], e["target"])))
        predictions = self.predictor.predict_links(nodes, edges)
        for src, tgt, _ in predictions:
            self.assertNotIn(frozenset((src, tgt)), existing)

    def test_suggest_exploration_returns_list(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        suggestions = self.predictor.suggest_exploration("A", nodes=nodes, edges=edges)
        self.assertIsInstance(suggestions, list)


class TestAnomalyDetector(unittest.TestCase):
    """Tests for AnomalyDetector."""

    def setUp(self):
        self.detector = AnomalyDetector()

    def test_detect_anomalies_returns_list(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        anomalies = self.detector.detect_anomalies(nodes, edges)
        self.assertIsInstance(anomalies, list)

    def test_dead_end_entity_detected(self):
        """Node E has mention_count=0 and no edges -> dead_end_entity."""
        nodes = _sample_nodes()
        edges = _sample_edges()
        anomalies = self.detector.detect_anomalies(nodes, edges)
        dead_ends = [a for a in anomalies if a["type"] == "dead_end_entity"]
        dead_end_node_ids = []
        for a in dead_ends:
            dead_end_node_ids.extend(a["nodes"])
        self.assertIn("E", dead_end_node_ids)

    def test_isolated_cluster_detected(self):
        """Two disconnected components, small one should be flagged."""
        nodes = {
            "A": {"id": "A", "type": "user", "properties": {"mention_count": 1}},
            "B": {"id": "B", "type": "entity", "properties": {"mention_count": 1}},
            "C": {"id": "C", "type": "entity", "properties": {"mention_count": 1}},
            "X": {"id": "X", "type": "entity", "properties": {"mention_count": 1}},
        }
        edges = [
            {"source": "A", "target": "B", "weight": 1.0, "timestamps": []},
            {"source": "B", "target": "C", "weight": 1.0, "timestamps": []},
            {"source": "X", "target": "X", "weight": 1.0, "timestamps": []},
        ]
        anomalies = self.detector.detect_anomalies(nodes, edges)
        types = {a["type"] for a in anomalies}
        self.assertIn("isolated_cluster", types)

    def test_anomaly_has_required_keys(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        anomalies = self.detector.detect_anomalies(nodes, edges)
        for a in anomalies:
            self.assertIn("type", a)
            self.assertIn("severity", a)
            self.assertIn("nodes", a)
            self.assertIn("description", a)

    def test_sudden_weight_change(self):
        now = time.time()
        nodes = {"A": {"id": "A", "type": "user", "properties": {"mention_count": 1}},
                 "B": {"id": "B", "type": "user", "properties": {"mention_count": 1}}}
        edges = [{"source": "A", "target": "B", "weight": 5.0,
                  "timestamps": [now - 100, now - 50, now - 10]}]
        anomalies = self.detector.detect_anomalies(nodes, edges)
        weight_spikes = [a for a in anomalies if a["type"] == "sudden_weight_change"]
        self.assertTrue(len(weight_spikes) > 0)


class TestTemporalEvolution(unittest.TestCase):
    """Tests for TemporalEvolution."""

    def setUp(self):
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmpfile.close()
        self.te = TemporalEvolution(snapshots_path=self._tmpfile.name)

    def tearDown(self):
        try:
            os.unlink(self._tmpfile.name)
        except OSError:
            pass

    def test_record_snapshot(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        self.te.record_snapshot(nodes=nodes, edges=edges)
        evolution = self.te.get_evolution(days=1)
        self.assertEqual(len(evolution), 1)

    def test_snapshot_fields(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        self.te.record_snapshot(nodes=nodes, edges=edges)
        snap = self.te.get_evolution(days=1)[0]
        self.assertIn("timestamp", snap)
        self.assertIn("node_count", snap)
        self.assertIn("edge_count", snap)
        self.assertIn("density", snap)

    def test_get_evolution_filters_by_days(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        self.te.record_snapshot(nodes=nodes, edges=edges)
        # Should find it within 1 day
        self.assertEqual(len(self.te.get_evolution(days=1)), 1)
        # Manually inject an old snapshot
        self.te._snapshots.append({
            "timestamp": time.time() - 86400 * 60,
            "node_count": 1, "edge_count": 0, "density": 0.0,
            "component_count": 1, "largest_component_size": 1,
        })
        # Only recent should appear in a 1-day window
        recent = self.te.get_evolution(days=1)
        self.assertEqual(len(recent), 1)

    def test_get_growth_rate_with_two_snapshots(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        self.te.record_snapshot(nodes=nodes, edges=edges)
        self.te.record_snapshot(nodes=nodes, edges=edges)
        rate = self.te.get_growth_rate()
        self.assertIn("nodes_per_day", rate)
        self.assertIn("edges_per_day", rate)
        self.assertEqual(rate["snapshot_count"], 2)


class TestGraphAnalytics(unittest.TestCase):
    """Tests for GraphAnalytics facade."""

    def test_compute_health(self):
        nodes = _sample_nodes()
        edges = _sample_edges()
        health = GraphAnalytics._compute_health(nodes, edges)
        self.assertIn("node_count", health)
        self.assertIn("edge_count", health)
        self.assertIn("density", health)
        self.assertIn("avg_degree", health)
        self.assertIn("diameter_estimate", health)
        self.assertIn("component_count", health)
        self.assertEqual(health["node_count"], 5)
        self.assertEqual(health["edge_count"], 4)

    def test_compute_health_empty(self):
        health = GraphAnalytics._compute_health({}, [])
        self.assertEqual(health["node_count"], 0)
        self.assertEqual(health["edge_count"], 0)
        self.assertEqual(health["density"], 0.0)


class TestEstimateDiameter(unittest.TestCase):
    """Tests for _estimate_diameter helper."""

    def test_empty_graph(self):
        self.assertEqual(_estimate_diameter({}), 0)

    def test_single_node(self):
        self.assertEqual(_estimate_diameter({"A": set()}), 0)

    def test_linear_graph(self):
        adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B"}}
        d = _estimate_diameter(adj, samples=3)
        self.assertEqual(d, 2)


if __name__ == "__main__":
    unittest.main()
