"""Tests for the Proactive Agent engine (agent/proactive.py)."""
import pytest
import knowledge
from proactive import (
    get_seasonal_suggestions,
    get_time_suggestions,
    generate_welcome_message,
)


@pytest.fixture(autouse=True)
def ensure_loaded():
    # reload() (không phải _ensure) để khôi phục KB thật nếu test khác đã để
    # _entities global rỗng/nhỏ — tránh flaky phụ thuộc thứ tự collection.
    if not knowledge._entities or len(knowledge._entities) < 100:
        knowledge.reload()


# ── get_seasonal_suggestions ──

def test_seasonal_suggestions():
    results = get_seasonal_suggestions(6)
    assert isinstance(results, list)
    assert len(results) > 0
    # Each suggestion should have text and type
    for s in results:
        assert "text" in s
        assert "type" in s


def test_seasonal_suggestions_all_months():
    """Every month should have at least one suggestion."""
    for month in range(1, 13):
        results = get_seasonal_suggestions(month)
        assert isinstance(results, list)
        assert len(results) > 0, f"Month {month} has no seasonal suggestions"


# ── get_time_suggestions ──

def test_time_suggestions():
    result = get_time_suggestions()
    assert isinstance(result, dict)
    assert "text" in result
    assert "activities" in result
    assert isinstance(result["activities"], list)
    assert len(result["activities"]) > 0


# ── generate_welcome_message ──

def test_welcome_message():
    result = generate_welcome_message()
    assert isinstance(result, dict)
    assert "greeting" in result
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)
    assert len(result["suggestions"]) > 0


def test_welcome_message_with_preferences():
    prefs = {"interests": ["ẩm thực", "lịch sử"]}
    result = generate_welcome_message(user_preferences=prefs)
    assert "greeting" in result
    # Should mention user interests
    assert "sở thích" in result["greeting"]
