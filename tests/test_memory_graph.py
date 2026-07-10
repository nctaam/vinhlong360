"""Tests for agent/memory_graph.py -- Graph-based relationship memory."""

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from memory_graph import MemoryGraph, MemoryNode, MemoryEdge


# ---- Fixtures ----


@pytest.fixture()
def graph(tmp_path):
    """Fresh MemoryGraph backed by a temp file."""
    return MemoryGraph(graph_path=tmp_path / "graph.json", auto_save_every=100)


# ---- Node Operations ----


class TestAddNode:
    def test_creates_node(self, graph):
        node = graph.add_node("a", type="entity")
        assert node.id == "a"
        assert node.type == "entity"

    def test_duplicate_updates_mention_count(self, graph):
        graph.add_node("a", type="entity")
        graph.add_node("a", type="entity")
        node = graph.get_node("a")
        assert node.properties["mention_count"] >= 1

    def test_properties_merged_on_duplicate(self, graph):
        graph.add_node("a", type="entity", properties={"color": "red"})
        graph.add_node("a", type="entity", properties={"size": "big"})
        node = graph.get_node("a")
        assert node.properties["color"] == "red"
        assert node.properties["size"] == "big"

    def test_get_node_returns_none_for_missing(self, graph):
        assert graph.get_node("nonexistent") is None

    def test_node_touch_increments_mention(self, graph):
        node = graph.add_node("a")
        old_count = node.properties["mention_count"]
        graph.add_node("a")
        assert graph.get_node("a").properties["mention_count"] == old_count + 1


# ---- Edge Operations ----


class TestAddEdge:
    def test_creates_edge(self, graph):
        edge = graph.add_edge("a", "b", "discussed", weight=2.0)
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.relation == "discussed"
        assert edge.weight == 2.0

    def test_auto_creates_missing_nodes(self, graph):
        graph.add_edge("x", "y", "co_mentioned")
        assert graph.get_node("x") is not None
        assert graph.get_node("y") is not None

    def test_reinforce_existing_edge(self, graph):
        graph.add_edge("a", "b", "discussed", weight=1.0)
        edge = graph.add_edge("a", "b", "discussed", weight=1.0)
        assert edge.weight == 2.0


# ---- Neighbors ----


class TestGetNeighbors:
    def test_returns_correct_neighbors(self, graph):
        graph.add_edge("a", "b", "discussed")
        graph.add_edge("a", "c", "discussed")
        neighbors = graph.get_neighbors("a")
        ids = {n["node_id"] for n in neighbors}
        assert ids == {"b", "c"}

    def test_filter_by_relation(self, graph):
        graph.add_edge("a", "b", "discussed")
        graph.add_edge("a", "c", "visited")
        neighbors = graph.get_neighbors("a", relation="discussed")
        assert len(neighbors) == 1
        assert neighbors[0]["node_id"] == "b"

    def test_filter_by_min_weight(self, graph):
        graph.add_edge("a", "b", "discussed", weight=1.0)
        graph.add_edge("a", "c", "discussed", weight=5.0)
        neighbors = graph.get_neighbors("a", min_weight=3.0)
        assert len(neighbors) == 1
        assert neighbors[0]["node_id"] == "c"

    def test_sorted_by_weight_descending(self, graph):
        graph.add_edge("a", "b", "discussed", weight=1.0)
        graph.add_edge("a", "c", "discussed", weight=3.0)
        graph.add_edge("a", "d", "discussed", weight=2.0)
        neighbors = graph.get_neighbors("a")
        weights = [n["weight"] for n in neighbors]
        assert weights == sorted(weights, reverse=True)


# ---- BFS Path ----


class TestGetPath:
    def test_finds_direct_path(self, graph):
        graph.add_edge("a", "b", "discussed")
        path = graph.get_path("a", "b")
        assert path == ["a", "b"]

    def test_finds_multi_hop_path(self, graph):
        graph.add_edge("a", "b", "discussed")
        graph.add_edge("b", "c", "discussed")
        path = graph.get_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_returns_none_when_no_path(self, graph):
        graph.add_node("a")
        graph.add_node("z")
        assert graph.get_path("a", "z") is None

    def test_same_node_returns_self(self, graph):
        graph.add_node("a")
        assert graph.get_path("a", "a") == ["a"]

    def test_returns_none_for_missing_nodes(self, graph):
        assert graph.get_path("missing1", "missing2") is None


# ---- Subgraph ----


class TestGetSubgraph:
    def test_returns_neighborhood(self, graph):
        graph.add_edge("a", "b", "discussed")
        graph.add_edge("b", "c", "co_mentioned")
        sub = graph.get_subgraph("a", hops=2)
        node_ids = {n["id"] for n in sub["nodes"]}
        assert {"a", "b", "c"} == node_ids

    def test_hops_limit(self, graph):
        graph.add_edge("a", "b", "discussed")
        graph.add_edge("b", "c", "discussed")
        graph.add_edge("c", "d", "discussed")
        sub = graph.get_subgraph("a", hops=1)
        node_ids = {n["id"] for n in sub["nodes"]}
        assert "d" not in node_ids

    def test_empty_for_missing_node(self, graph):
        sub = graph.get_subgraph("nonexistent")
        assert sub == {"nodes": [], "edges": []}


# ---- Memory-Specific Operations ----


class TestRecordInteraction:
    def test_creates_user_and_entity_nodes(self, graph):
        graph.record_interaction("user1", ["ent_a", "ent_b"])
        assert graph.get_node("user1") is not None
        assert graph.get_node("user1").type == "user"
        assert graph.get_node("ent_a") is not None

    def test_creates_discussed_edges(self, graph):
        graph.record_interaction("user1", ["ent_a"])
        neighbors = graph.get_neighbors("user1", relation="discussed")
        assert len(neighbors) == 1
        assert neighbors[0]["node_id"] == "ent_a"

    def test_creates_co_mention_edges(self, graph):
        graph.record_interaction("user1", ["ent_a", "ent_b", "ent_c"])
        # ent_a <-> ent_b, ent_a <-> ent_c, ent_b <-> ent_c co_mentioned edges
        neighbors = graph.get_neighbors("ent_a", relation="co_mentioned")
        ids = {n["node_id"] for n in neighbors}
        assert "ent_b" in ids
        assert "ent_c" in ids


class TestRecordPreference:
    def test_creates_preference_edge(self, graph):
        graph.record_preference("user1", "ent_a", score=3.0)
        neighbors = graph.get_neighbors("user1", relation="interested_in")
        assert len(neighbors) == 1
        assert neighbors[0]["node_id"] == "ent_a"
        assert neighbors[0]["weight"] == 3.0


class TestRecordComparison:
    def test_creates_compared_with_edge(self, graph):
        graph.record_comparison("user1", "ent_a", "ent_b")
        # Entities should be connected with compared_with
        a_neighbors = graph.get_neighbors("ent_a", relation="compared_with")
        b_neighbors = graph.get_neighbors("ent_b", relation="compared_with")
        # One of them should see the other (edges stored in alphabetical order)
        combined_ids = {n["node_id"] for n in a_neighbors} | {n["node_id"] for n in b_neighbors}
        assert "ent_a" in combined_ids or "ent_b" in combined_ids


class TestSuggestUnexplored:
    def test_returns_unseen_connected_entities(self, graph):
        # user discussed ent_a, ent_a co-mentioned with ent_b
        graph.record_interaction("user1", ["ent_a"])
        graph.add_edge("ent_a", "ent_b", "co_mentioned", weight=2.0)
        graph.add_node("ent_b", "entity", {"name": "Entity B"})
        suggestions = graph.suggest_unexplored("user1", limit=5)
        ids = [s["entity_id"] for s in suggestions]
        assert "ent_b" in ids

    def test_returns_empty_for_unknown_user(self, graph):
        assert graph.suggest_unexplored("nobody") == []


# ---- Knowledge Compounding ----


class TestEmergingPatterns:
    def test_returns_high_weight_co_mentions(self, graph):
        graph.add_edge("a", "b", "co_mentioned", weight=5.0)
        graph.add_edge("c", "d", "co_mentioned", weight=1.0)
        patterns = graph.get_emerging_patterns(min_weight=3.0)
        assert len(patterns) == 1
        assert patterns[0]["entity_a"] == "a"

    def test_returns_empty_below_threshold(self, graph):
        graph.add_edge("a", "b", "co_mentioned", weight=1.0)
        assert graph.get_emerging_patterns(min_weight=5.0) == []


class TestBuildGraphContext:
    def test_returns_formatted_string(self, graph):
        graph.record_interaction("user1", ["ent_a", "ent_b"])
        graph.add_node("ent_a", "entity", {"name": "Cu Lao An Binh"})
        graph.add_node("ent_b", "entity", {"name": "Homestay Ut Trinh"})
        ctx = graph.build_graph_context("user1")
        assert isinstance(ctx, str)
        assert "Cu Lao An Binh" in ctx

    def test_returns_empty_for_unknown_user(self, graph):
        assert graph.build_graph_context("nobody") == ""


# ---- Stats ----


class TestStats:
    def test_returns_correct_counts(self, graph):
        graph.add_node("a", "entity")
        graph.add_node("b", "user")
        graph.add_edge("a", "b", "discussed")
        s = graph.stats()
        assert s["total_nodes"] == 2
        assert s["total_edges"] == 1
        assert s["node_types"]["entity"] == 1
        assert s["node_types"]["user"] == 1
        assert s["relation_types"]["discussed"] == 1


# ---- Persistence ----


class TestPersistence:
    def test_save_then_load_preserves_data(self, tmp_path):
        path = tmp_path / "persist.json"
        g1 = MemoryGraph(graph_path=path, auto_save_every=100)
        g1.add_node("a", "entity", {"name": "Alpha"})
        g1.add_edge("a", "b", "discussed", weight=3.0)
        g1.save()

        # Load into a new instance
        g2 = MemoryGraph(graph_path=path, auto_save_every=100)
        node = g2.get_node("a")
        assert node is not None
        assert node.properties["name"] == "Alpha"
        neighbors = g2.get_neighbors("a")
        assert len(neighbors) == 1
        assert neighbors[0]["node_id"] == "b"
        assert neighbors[0]["weight"] == 3.0

    def test_load_nonexistent_file_no_error(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        g = MemoryGraph(graph_path=path, auto_save_every=100)
        assert g.stats()["total_nodes"] == 0


# ---- Thread Safety ----


class TestThreadSafety:
    def test_concurrent_add_nodes(self, graph):
        errors = []

        def worker(tid):
            try:
                for i in range(20):
                    graph.add_node(f"t{tid}_n{i}", "entity")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert graph.stats()["total_nodes"] == 100


# ---- MemoryNode / MemoryEdge dataclass ----


class TestDataclasses:
    def test_node_to_dict_roundtrip(self):
        node = MemoryNode(id="test", type="entity", properties={"name": "Test"})
        d = node.to_dict()
        restored = MemoryNode.from_dict(d)
        assert restored.id == "test"
        assert restored.properties["name"] == "Test"

    def test_edge_to_dict_roundtrip(self):
        edge = MemoryEdge(source="a", target="b", relation="discussed", weight=2.5)
        d = edge.to_dict()
        restored = MemoryEdge.from_dict(d)
        assert restored.source == "a"
        assert restored.weight == 2.5


# ---- §B8 gate: LLM fact-extraction phải opt-in ----


class TestExtractFactsB8Gate:
    def test_default_off_does_not_call_llm(self, graph, monkeypatch):
        """Mặc định (AUTONOMOUS_AGENT_ENABLED unset) → extract_facts KHÔNG gọi LLM."""
        monkeypatch.delenv("AUTONOMOUS_AGENT_ENABLED", raising=False)

        def _boom(*a, **k):
            raise AssertionError("LLM không được gọi khi autonomous OFF")

        monkeypatch.setattr(graph, "_extract_facts_llm", _boom)
        facts = graph.extract_facts("Chùa Ông ở Vĩnh Long", "Đúng vậy")
        assert isinstance(facts, list)  # fallback keyword, không raise

    def test_opt_in_within_cap_calls_llm(self, graph, monkeypatch):
        """Opt-in (AUTONOMOUS_AGENT_ENABLED=true) + còn cap → có gọi _extract_facts_llm."""
        monkeypatch.setenv("AUTONOMOUS_AGENT_ENABLED", "true")
        import autonomous_budget
        monkeypatch.setattr(autonomous_budget, "try_consume", lambda n=1: True)
        called = {"llm": False}

        def _stub(*a, **k):
            called["llm"] = True
            return [("a", "near", "b")]

        monkeypatch.setattr(graph, "_extract_facts_llm", _stub)
        facts = graph.extract_facts("x", "y")
        assert called["llm"] is True
        assert facts == [("a", "near", "b")]

    def test_opt_in_over_cap_falls_back(self, graph, monkeypatch):
        """Opt-in nhưng VƯỢT cap (try_consume=False) → KHÔNG gọi LLM, fallback keyword."""
        monkeypatch.setenv("AUTONOMOUS_AGENT_ENABLED", "true")
        import autonomous_budget
        monkeypatch.setattr(autonomous_budget, "try_consume", lambda n=1: False)
        monkeypatch.setattr(graph, "_extract_facts_llm",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("vượt cap không được gọi LLM")))
        facts = graph.extract_facts("x", "y")
        assert isinstance(facts, list)
