"""
Tests cho vector_search.py — TF-IDF semantic store (GĐ11.1).

Viết TRƯỚC khi refactor dense→sparse (CLAUDE §2 B3: test vùng mù trước khi sửa).
Mọi assertion ở đây mô tả HÀNH VI HỢP ĐỒNG (build/search/hybrid/stats/save-load)
phải giữ nguyên qua refactor. Dùng EMBEDDINGS_FILE tạm để không đụng cache thật.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vector_search as vs


@pytest.fixture
def store(tmp_path, monkeypatch):
    """TFIDFStore mới, ghi/đọc vào file tạm (không đụng agent/data/embeddings.json thật)."""
    monkeypatch.setattr(vs, "EMBEDDINGS_FILE", tmp_path / "embeddings.json")
    return vs.TFIDFStore()


@pytest.fixture
def corpus():
    return {
        "cam-sanh": {"type": "product", "name": "Cam sành Vĩnh Long",
                     "summary": "Cam sành ngọt mát, đặc sản trái cây Vĩnh Long."},
        "bun-mam": {"type": "dish", "name": "Bún mắm Trà Vinh",
                    "summary": "Món bún mắm đậm đà, hải sản tươi."},
        "gom-do": {"type": "craft_village", "name": "Làng gốm đỏ Mang Thít",
                   "summary": "Làng nghề gốm đỏ truyền thống ven sông Cổ Chiên."},
        # place phải bị BỎ QUA khỏi index
        "xa-an-binh": {"type": "place", "name": "Xã An Bình",
                       "summary": "Một xã của Vĩnh Long."},
    }


class TestTokenize:
    def test_normalize_lowercases_keeps_diacritics_strips_punct(self):
        # _normalize_vietnamese: lowercase + bỏ dấu câu, NHƯNG GIỮ dấu tiếng Việt
        assert vs._normalize_vietnamese("Vĩnh Long!").strip() == "vĩnh long"

    def test_tokenize_nonempty(self):
        toks = vs._tokenize("Cam sành Vĩnh Long")
        assert isinstance(toks, list) and len(toks) >= 1


class TestCosine:
    def test_identical(self):
        v = [0.6, 0.8]
        assert vs.cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert vs.cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_vector(self):
        assert vs.cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestBuildIndex:
    def test_builds_and_skips_places(self, store, corpus):
        res = store.build_index(corpus, force=True)
        assert res["status"] == "built"
        # 3 entity nội dung; place bị bỏ
        assert res["entities"] == 3
        assert "xa-an-binh" not in store._vectors
        assert set(store._vectors.keys()) == {"cam-sanh", "bun-mam", "gom-do"}

    def test_up_to_date_skips_rebuild(self, store, corpus):
        store.build_index(corpus, force=True)
        res = store.build_index(corpus, force=False)
        assert res["status"] == "up_to_date"

    def test_empty_corpus(self, store):
        res = store.build_index({}, force=True)
        assert res["status"] == "no_entities"


class TestSearch:
    def test_finds_relevant_entity(self, store, corpus):
        store.build_index(corpus, force=True)
        results = store.search("gốm đỏ Mang Thít", top_k=5)
        assert results, "phải có kết quả"
        assert results[0]["entity_id"] == "gom-do"
        assert 0.0 < results[0]["score"] <= 1.0

    def test_results_sorted_desc(self, store, corpus):
        store.build_index(corpus, force=True)
        results = store.search("Vĩnh Long đặc sản", top_k=5)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_no_vocab_match_returns_empty(self, store, corpus):
        store.build_index(corpus, force=True)
        assert store.search("xyzqwerty_khongtontai", top_k=5) == []

    def test_search_before_build_returns_empty(self, store):
        assert store.search("bất kỳ", top_k=5) == []


class TestSaveLoadRoundtrip:
    def test_persists_and_reloads(self, store, corpus, tmp_path, monkeypatch):
        store.build_index(corpus, force=True)
        assert (tmp_path / "embeddings.json").exists()
        before = store.search("bún mắm hải sản", top_k=3)

        # Store mới đọc lại từ cùng file → kết quả search giống
        fresh = vs.TFIDFStore()
        after = fresh.search("bún mắm hải sản", top_k=3)
        assert [r["entity_id"] for r in after] == [r["entity_id"] for r in before]
        assert after[0]["entity_id"] == "bun-mam"


class TestStats:
    def test_stats_structure(self, store, corpus):
        store.build_index(corpus, force=True)
        s = store.stats()
        assert s["type"] == "tfidf"
        assert s["total_embeddings"] == 3
        assert s["doc_count"] == 3
        assert s["vocab_size"] >= 1
        assert s["file_exists"] is True


class TestHybridSearch:
    def test_merges_keyword_and_semantic(self, store, corpus, monkeypatch):
        monkeypatch.setattr(vs, "embedding_store", store)
        store.build_index(corpus, force=True)
        keyword = [{"id": "cam-sanh"}, {"id": "bun-mam"}]
        merged = vs.hybrid_search("cam sành Vĩnh Long", keyword, semantic_weight=0.3, top_k=5)
        assert merged, "hybrid phải trả kết quả"
        ids = [m.get("entity_id", m.get("id")) for m in merged]
        assert "cam-sanh" in ids

    def test_falls_back_to_keyword_when_no_semantic(self, store, monkeypatch):
        monkeypatch.setattr(vs, "embedding_store", store)  # chưa build → semantic rỗng
        keyword = [{"id": "a"}, {"id": "b"}]
        merged = vs.hybrid_search("gì đó", keyword, top_k=5)
        assert merged == keyword[:5]
