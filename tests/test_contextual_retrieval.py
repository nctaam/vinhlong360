"""Tests for agent/contextual_retrieval.py -- BM25, contextual text, and hybrid search."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from contextual_retrieval import (
    ContextualRetrieval,
    BM25,
    LLMReranker,
    enhanced_hybrid_search,
    contextual,
    bm25,
    reranker,
)


# ---- BM25 ----


class TestBM25:
    @pytest.fixture()
    def index(self):
        b = BM25()
        docs = {
            "chua-vinh-trang": "Chua Vinh Trang la ngoi chua lon nhat Vinh Long",
            "cu-lao-an-binh": "Cu Lao An Binh la diem du lich sinh thai noi tieng",
            "bun-nuoc-leo": "Bun nuoc leo la dac san Vinh Long thom ngon",
            "cho-noi": "Cho noi Cai Be la cho noi tren song noi tieng mien Tay",
            "homestay": "Homestay Ut Trinh la noi nghi duong yên binh tren con",
        }
        b.build_index(docs)
        return b

    def test_build_index_sets_doc_count(self, index):
        assert index._N == 5

    def test_build_index_computes_avg_dl(self, index):
        assert index._avg_dl > 0

    def test_score_returns_ranked_results(self, index):
        results = index.score("chua Vinh Long", top_k=3)
        assert len(results) > 0
        # Should be sorted by score descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_score_top_result_relevant(self, index):
        results = index.score("chua Vinh Trang", top_k=3)
        assert results[0]["entity_id"] == "chua-vinh-trang"

    def test_score_bun_nuoc_leo(self, index):
        results = index.score("dac san ngon Vinh Long", top_k=3)
        ids = [r["entity_id"] for r in results]
        assert "bun-nuoc-leo" in ids

    def test_empty_query_returns_empty(self, index):
        results = index.score("", top_k=5)
        assert results == []

    def test_no_match_query(self, index):
        results = index.score("quantum physics algorithm", top_k=5)
        assert results == []

    def test_empty_index_returns_empty(self):
        b = BM25()
        results = b.score("anything", top_k=5)
        assert results == []

    def test_score_has_entity_id_and_score(self, index):
        results = index.score("chua", top_k=1)
        if results:
            assert "entity_id" in results[0]
            assert "score" in results[0]
            assert isinstance(results[0]["score"], float)

    def test_top_k_limits_results(self, index):
        results = index.score("Vinh Long", top_k=2)
        assert len(results) <= 2

    def test_build_index_with_single_doc(self):
        b = BM25()
        b.build_index({"only": "one single document here"})
        assert b._N == 1
        results = b.score("document", top_k=5)
        assert len(results) >= 1


# ---- ContextualRetrieval ----


class TestContextualRetrieval:
    def test_build_contextual_text_basic(self):
        cr = ContextualRetrieval()
        entity = {
            "id": "test-entity",
            "name": "Test Entity",
            "type": "attraction",
            "summary": "A test attraction in Vinh Long",
            "tags": ["du_lich", "sinh_thai"],
        }
        text = cr.build_contextual_text(entity, relationships=[])
        assert "Test Entity" in text
        assert "attraction" in text
        assert "du_lich" in text

    def test_build_contextual_text_with_location(self):
        cr = ContextualRetrieval()
        entity = {
            "id": "chua",
            "name": "Chua Vinh Trang",
            "type": "temple",
            "summary": "Historic temple",
            "location": {"name": "Tp Vinh Long"},
        }
        text = cr.build_contextual_text(entity, relationships=[])
        assert "Tp Vinh Long" in text

    def test_build_contextual_text_with_relationships(self):
        cr = ContextualRetrieval()
        entity = {"id": "a", "name": "Entity A", "type": "attraction", "summary": ""}
        rels = [
            {"source": "a", "target": "b", "type": "near", "label": "Entity B"},
            {"source": "a", "target": "c", "type": "related", "label": "Entity C"},
        ]
        text = cr.build_contextual_text(entity, rels)
        assert "Entity B" in text
        assert "Entity C" in text

    def test_build_contextual_text_with_season(self):
        cr = ContextualRetrieval()
        entity = {
            "id": "cam",
            "name": "Cam Sanh",
            "type": "product",
            "summary": "",
            "season": {"peak": [10, 11, 12]},
        }
        text = cr.build_contextual_text(entity, relationships=[])
        assert "10" in text
        assert "peak" in text.lower() or "thu hoach" in text

    def test_build_contextual_text_with_ocop(self):
        cr = ContextualRetrieval()
        entity = {
            "id": "ocop",
            "name": "San pham OCOP",
            "type": "product",
            "summary": "",
            "attributes": {"ocop": 4},
        }
        text = cr.build_contextual_text(entity, relationships=[])
        assert "OCOP" in text
        assert "4" in text

    def test_build_all_contextual(self):
        cr = ContextualRetrieval()
        entities = {
            "a": {"id": "a", "name": "A", "type": "attraction", "summary": "Place A"},
            "b": {"id": "b", "name": "B", "type": "food", "summary": "Food B"},
            "p": {"id": "p", "name": "P", "type": "place", "summary": "Area P"},
        }
        texts = cr.build_all_contextual(entities, relationships=[])
        # "place" type entities are skipped by build_all_contextual
        assert "a" in texts
        assert "b" in texts
        assert "p" not in texts


# ---- LLMReranker ----


class TestLLMReranker:
    def test_has_rerank_method(self):
        r = LLMReranker()
        assert callable(getattr(r, "rerank", None))

    def test_rerank_empty_returns_empty(self):
        r = LLMReranker()
        assert r.rerank("query", [], top_k=5) == []

    def test_rerank_single_item(self):
        r = LLMReranker()
        candidates = [{"id": "a", "name": "A"}]
        result = r.rerank("query", candidates, top_k=5)
        assert len(result) == 1
        assert result[0]["id"] == "a"


# ---- enhanced_hybrid_search ----


class TestEnhancedHybridSearch:
    def test_empty_inputs_returns_empty(self):
        result = enhanced_hybrid_search(
            query="test",
            keyword_results=[],
            entities={},
            relationships=[],
            rerank=False,
        )
        assert result == []

    def test_returns_list(self):
        keyword_results = [
            {"id": "a", "name": "Entity A"},
            {"id": "b", "name": "Entity B"},
        ]
        result = enhanced_hybrid_search(
            query="test",
            keyword_results=keyword_results,
            entities={"a": keyword_results[0], "b": keyword_results[1]},
            relationships=[],
            rerank=False,
            top_k=5,
        )
        assert isinstance(result, list)

    def test_respects_top_k(self):
        keyword_results = [
            {"id": f"e{i}", "name": f"Entity {i}"} for i in range(20)
        ]
        entities = {e["id"]: e for e in keyword_results}
        result = enhanced_hybrid_search(
            query="something",
            keyword_results=keyword_results,
            entities=entities,
            relationships=[],
            rerank=False,
            top_k=3,
        )
        assert len(result) <= 3


# ---- Singletons ----


class TestSingletons:
    def test_contextual_initialized(self):
        assert isinstance(contextual, ContextualRetrieval)

    def test_bm25_initialized(self):
        assert isinstance(bm25, BM25)

    def test_reranker_initialized(self):
        assert isinstance(reranker, LLMReranker)
