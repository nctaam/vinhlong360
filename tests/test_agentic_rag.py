"""Tests for the Agentic RAG layer (agent/agentic_rag.py)."""
import pytest
import knowledge
import agentic_rag
from agentic_rag import (
    classify_query,
    _detect_areas,
    _detect_intent,
    _is_seasonal_query,
    _normalize,
    build_rag_context,
)


@pytest.fixture(autouse=True)
def ensure_loaded():
    # reload() (không phải _ensure) để khôi phục KB thật nếu test khác đã để
    # _entities global rỗng/nhỏ — tránh flaky phụ thuộc thứ tự collection.
    if not knowledge._entities or len(knowledge._entities) < 100:
        knowledge.reload()


# ── classify_query ──

def test_classify_simple():
    result = classify_query("Chùa Âng là gì")
    assert result["intent"] == "entity_detail"
    assert result["complexity"] in ("simple", "moderate")


def test_classify_comparison():
    result = classify_query("So sánh Bến Tre và Vĩnh Long")
    assert result["complexity"] == "complex"
    assert result["intent"] == "comparison"


def test_classify_itinerary():
    result = classify_query("Lịch trình 2 ngày")
    assert result["intent"] == "itinerary"
    assert result["complexity"] == "complex"


def test_classify_without_diacritics():
    result = classify_query("So sanh Ben Tre va Vinh Long")
    assert result["intent"] == "comparison"
    assert result["complexity"] == "complex"


# ── _detect_areas ──

def test_detect_areas():
    areas = _detect_areas("du lịch Bến Tre")
    assert "ben-tre" in areas


def test_detect_areas_no_diacritics():
    areas = _detect_areas("du lich Ben Tre")
    assert "ben-tre" in areas


# ── _detect_intent ──

def test_detect_intent_multi_hop():
    intent = _detect_intent("gần đây có gì")
    assert intent == "multi_hop"


# ── _is_seasonal_query ──

def test_is_seasonal():
    assert _is_seasonal_query("tháng này nên đi đâu") is True


def test_is_not_seasonal():
    assert _is_seasonal_query("chùa nào đẹp nhất") is False


# ── _normalize ──

def test_normalize():
    result = _normalize("Vĩnh Long")
    assert "vinh" in result
    assert "long" in result
    # Should not contain Vietnamese diacritics
    assert "ĩ" not in result


# ── build_rag_context ──

def test_build_rag_context():
    context = build_rag_context("ẩm thực")
    assert isinstance(context, str)
    assert len(context) > 0
