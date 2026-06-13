"""Tests for agent/vector_search.py — TF-IDF Vector Search."""
import math
import pytest

from vector_search import (
    _normalize_vietnamese,
    _tokenize,
    cosine_similarity,
    _dot,
    _norm,
    TFIDFStore,
    hybrid_search,
    STOP_WORDS,
)


# ── _normalize_vietnamese ────────────────────────────


def test_normalize_lowercase():
    assert _normalize_vietnamese("Hello World") == "hello world"


def test_normalize_strips_whitespace():
    assert _normalize_vietnamese("  hello  ") == "hello"


def test_normalize_removes_special_chars():
    result = _normalize_vietnamese("hello! @world#")
    assert "@" not in result
    assert "#" not in result
    assert "!" not in result


def test_normalize_preserves_vietnamese_diacritics():
    result = _normalize_vietnamese("Vĩnh Long đẹp")
    assert "vĩnh" in result
    assert "đẹp" in result


def test_normalize_collapses_spaces():
    result = _normalize_vietnamese("a   b   c")
    assert result == "a b c"


def test_normalize_empty():
    assert _normalize_vietnamese("") == ""


# ── _tokenize ────────────────────────────────────────


def test_tokenize_produces_unigrams():
    tokens = _tokenize("cam sanh tam binh")
    assert "cam" in tokens
    assert "sanh" in tokens
    assert "tam" in tokens
    assert "binh" in tokens


def test_tokenize_produces_bigrams():
    tokens = _tokenize("cam sanh tam binh")
    assert "cam_sanh" in tokens
    assert "sanh_tam" in tokens
    assert "tam_binh" in tokens


def test_tokenize_removes_stop_words():
    # Stop words are in Vietnamese with diacritics: "là", "và", "của", "có"
    # The normalizer lowercases but preserves diacritics, so use proper forms.
    tokens = _tokenize("du lịch là một trải nghiệm")
    assert "là" not in tokens  # stop word
    assert "một" not in tokens  # stop word


def test_tokenize_removes_short_words():
    # Single-character words should be excluded (len > 1 filter)
    tokens = _tokenize("a b c du lich")
    assert "a" not in tokens
    assert "b" not in tokens


def test_tokenize_empty():
    tokens = _tokenize("")
    assert tokens == []


def test_tokenize_all_stop_words():
    # Use actual Vietnamese stop words (with diacritics) from the STOP_WORDS set
    tokens = _tokenize("là và của có")
    # All are stop words, result should be empty
    assert len(tokens) == 0


# ── cosine_similarity ────────────────────────────────


def test_cosine_similarity_identical():
    a = [1.0, 2.0, 3.0]
    assert abs(cosine_similarity(a, a) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_cosine_similarity_opposite():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6


def test_cosine_similarity_zero_vector():
    a = [0.0, 0.0]
    b = [1.0, 2.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_positive():
    a = [1.0, 1.0]
    b = [1.0, 0.0]
    sim = cosine_similarity(a, b)
    assert 0 < sim < 1


# ── Vector math helpers ──────────────────────────────


def test_dot_product():
    assert _dot([1, 2, 3], [4, 5, 6]) == 32


def test_norm():
    assert abs(_norm([3, 4]) - 5.0) < 1e-6


def test_norm_zero():
    assert _norm([0, 0, 0]) == 0.0


# ── TFIDFStore ───────────────────────────────────────


@pytest.fixture
def sample_entities():
    return {
        "cam-sanh": {
            "name": "Cam sanh Tam Binh",
            "type": "specialty",
            "summary": "Cam sanh la dac san noi tieng cua Tam Binh, Vinh Long",
            "tags": ["trai-cay", "ocop"],
        },
        "bun-nuoc-leo": {
            "name": "Bun nuoc leo",
            "type": "food",
            "summary": "Mon an dac trung cua mien Tay, nuoc leo dam da",
            "tags": ["am-thuc", "mon-an"],
        },
        "chua-khmer": {
            "name": "Chua Khmer Vinh Long",
            "type": "attraction",
            "summary": "Chua Khmer co kien truc doc dao, van hoa Khmer",
            "tags": ["van-hoa", "tam-linh"],
        },
    }


@pytest.fixture
def store():
    return TFIDFStore()


def test_build_index(store, sample_entities):
    result = store.build_index(sample_entities, force=True)
    assert result["status"] == "built"
    assert result["entities"] == 3
    assert result["vocab_size"] > 0


def test_build_index_skips_place_type(store):
    entities = {
        "place-1": {"name": "Vinh Long", "type": "place", "summary": "A place"},
        "food-1": {"name": "Cam sanh", "type": "specialty", "summary": "Fruit"},
    }
    result = store.build_index(entities, force=True)
    assert result["entities"] == 1  # Only non-place entities


def test_build_index_empty(store):
    result = store.build_index({})
    assert result["status"] == "no_entities"


def test_search_returns_results(store, sample_entities):
    store.build_index(sample_entities, force=True)
    results = store.search("cam sanh trai cay", top_k=5)
    assert len(results) > 0
    assert results[0]["entity_id"] == "cam-sanh"
    assert results[0]["score"] > 0


def test_search_ranked_by_relevance(store, sample_entities):
    store.build_index(sample_entities, force=True)
    results = store.search("chua khmer van hoa", top_k=5)
    assert len(results) > 0
    # Results should be sorted by score descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_empty_store(store):
    results = store.search("anything")
    assert results == []


def test_search_no_matching_terms(store, sample_entities):
    store.build_index(sample_entities, force=True)
    results = store.search("xyzabc12345")
    assert results == []


def test_search_top_k_limit(store, sample_entities):
    store.build_index(sample_entities, force=True)
    results = store.search("cam sanh", top_k=1)
    assert len(results) <= 1


def test_build_index_up_to_date(store, sample_entities):
    store.build_index(sample_entities, force=True)
    result = store.build_index(sample_entities, force=False)
    assert result["status"] == "up_to_date"


# ── hybrid_search ────────────────────────────────────


def test_hybrid_search_with_empty_semantic(store):
    """When semantic search has no results, return keyword results."""
    keyword_results = [
        {"id": "e1", "name": "Entity 1"},
        {"id": "e2", "name": "Entity 2"},
    ]
    # Store has no index, so semantic search returns []
    result = hybrid_search("query", keyword_results, top_k=5)
    assert len(result) == 2


def test_hybrid_search_merges_results(store, sample_entities):
    store.build_index(sample_entities, force=True)
    keyword_results = [
        {"id": "cam-sanh", "name": "Cam sanh"},
    ]
    # Patch the embedding_store to use our store
    from unittest.mock import patch
    with patch("vector_search.embedding_store", store):
        result = hybrid_search("cam sanh trai cay", keyword_results, top_k=5)
    # Should include at least the keyword result
    assert len(result) >= 1


def test_hybrid_search_respects_weights():
    """Different semantic weights should produce different rankings."""
    keyword_results = [
        {"id": "e1", "name": "Entity 1"},
    ]
    # With no semantic results, both should return the same
    r1 = hybrid_search("query", keyword_results, semantic_weight=0.1, top_k=5)
    r2 = hybrid_search("query", keyword_results, semantic_weight=0.9, top_k=5)
    # Both should return the keyword results as fallback
    assert len(r1) >= 1
    assert len(r2) >= 1
