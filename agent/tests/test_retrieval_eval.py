"""
CI gate for retrieval quality + degraded-mode resilience (offline, no LLM).

These run against the real KB and the hybrid search stack, so they catch
regressions in the retrieval layer and the LLM-down fallback behaviour.
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import knowledge
import retrieval_eval


# Build indexes once for the whole module
@pytest.fixture(scope="module", autouse=True)
def _indexes():
    # GĐ-audit: reset KB in-memory về DB thật trước khi build index — tránh flaky khi test
    # khác (integration) đã mutate KB global trước đó (_ensure() là no-op nếu _entities đã set).
    knowledge.reload()
    retrieval_eval._build_indexes()
    yield


class TestRetrievalRecall:
    """Recall@K: known Vietnamese queries must surface the expected entity."""

    def test_recall_at_5_threshold(self):
        report = retrieval_eval.run_eval(k=5, verbose=False)
        # Recall@5 should be high — the hybrid stack is wired and indexes built.
        assert report["recall_at_k"] >= 0.8, f"Recall@5 too low: {report['recall_at_k']}, misses={report['misses']}"

    @pytest.mark.parametrize("query,accept", [
        ("chợ nổi Trà Ôn ở đâu", ["cho-noi-tra-on"]),
        ("chùa Phước Hậu", ["chua-phuoc-hau"]),
        ("khoai lang Bình Tân", ["khoai-lang-binh-tan"]),
    ])
    def test_specific_lookups(self, query, accept):
        ids = retrieval_eval._search(query, k=5)
        ids_norm = [knowledge._normalize_vn(i) for i in ids]
        assert any(any(knowledge._normalize_vn(a) in i for i in ids_norm) for a in accept), \
            f"'{query}' did not surface {accept}; got {ids}"


class TestAbstention:
    """Out-of-domain queries must not surface relevant KB entities."""

    def test_abstention_rate(self):
        report = retrieval_eval.run_eval(k=5, verbose=False)
        assert report["abstention_rate"] >= 0.7, \
            f"Abstention too low: {report['abstention_rate']}, detail={report['abstention_detail']}"

    @pytest.mark.parametrize("query", [
        "vé concert BlackPink ở Bangkok",   # ngoài-vùng, không trùng tên entity local (xem retrieval_eval)
        "qwxzpklmn random gibberish 12345",
    ])
    def test_out_of_domain_no_relevant(self, query):
        ids = retrieval_eval._search(query, k=5)
        relevant = [eid for eid in ids
                    if knowledge.get_entity(eid) and knowledge.query_relevance(query, knowledge.get_entity(eid))]
        assert len(relevant) == 0, f"'{query}' wrongly matched: {relevant}"


class TestQueryRelevance:
    """Unit tests for the relevance gate."""

    def test_relevant_by_name_token(self):
        e = {"name": "Chùa Phước Hậu", "summary": "Ngôi chùa cổ"}
        assert knowledge.query_relevance("chùa Phước Hậu ở đâu", e) is True

    def test_relevant_by_substring(self):
        e = {"name": "Cam sành Trà Ôn", "summary": "Đặc sản nổi tiếng"}
        assert knowledge.query_relevance("cam sành", e) is True

    def test_irrelevant(self):
        e = {"name": "Cam sành Trà Ôn", "summary": "Đặc sản trái cây"}
        assert knowledge.query_relevance("vé máy bay đi Paris", e) is False

    def test_stopwords_dont_match(self):
        e = {"name": "Chùa Hang", "summary": "Có nhiều du khách"}
        # "có" / "ở" are stopwords — should not make it relevant
        assert knowledge.query_relevance("có gì ở đâu", e) is False
