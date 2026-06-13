"""
Tests for experience_memory.py — ReasoningBank-lite strategy memory.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import experience_memory


@pytest.fixture(autouse=True)
def _isolate_bank(tmp_path, monkeypatch):
    bank = tmp_path / "experience_bank.json"
    monkeypatch.setattr(experience_memory, "BANK_FILE", bank)
    yield


class TestIntentClassification:
    def test_itinerary(self):
        assert experience_memory._intent("Lập lịch trình 2 ngày") == "itinerary"

    def test_comparison(self):
        assert experience_memory._intent("So sánh Vĩnh Long và Bến Tre") == "comparison"

    def test_recommendation(self):
        assert experience_memory._intent("Gợi ý đặc sản nên thử") == "recommendation"

    def test_factual_default(self):
        assert experience_memory._intent("Chùa Phước Hậu") == "factual"


class TestRecord:
    def test_positive_recorded(self):
        item = experience_memory.record("Cam sành ở đâu", ["search", "entity_detail"], 9.0, "A detailed answer")
        assert item is not None
        assert item["polarity"] == "positive"
        assert any("search" in p for p in item["principles"])

    def test_negative_recorded(self):
        item = experience_memory.record("Xyz là gì", [], 3.0, "short")
        assert item is not None
        assert item["polarity"] == "negative"
        assert any("tool" in p.lower() or "ngắn" in p.lower() for p in item["principles"])

    def test_middling_skipped(self):
        item = experience_memory.record("something", ["search"], 6.0, "ok answer")
        assert item is None

    def test_merge_reinforces(self):
        experience_memory.record("Cam sành ở đâu", ["search"], 9.0, "answer one")
        item2 = experience_memory.record("Bún mắm ở đâu", ["search"], 9.0, "answer two")
        # Same intent+polarity → merged, uses incremented
        assert item2["uses"] == 2


class TestRetrieve:
    def test_retrieve_by_intent(self):
        experience_memory.record("Lập lịch trình Vĩnh Long", ["generate_itinerary"], 9.0, "x" * 200)
        results = experience_memory.retrieve("Lên lịch trình Bến Tre 3 ngày")
        assert len(results) >= 1
        assert results[0]["intent"] == "itinerary"

    def test_retrieve_empty_bank(self):
        assert experience_memory.retrieve("anything") == []


class TestBuildPrompt:
    def test_prompt_includes_lessons(self):
        experience_memory.record("So sánh A và B", ["compare_areas"], 9.0, "x" * 200)
        prompt = experience_memory.build_prompt("So sánh X với Y")
        assert "Kinh nghiệm" in prompt
        assert "✓" in prompt

    def test_prompt_includes_negative(self):
        experience_memory.record("Tìm gì đó", [], 2.0, "short")
        prompt = experience_memory.build_prompt("Tìm cái khác")
        assert "Tránh" in prompt or "✗" in prompt

    def test_prompt_has_reference_disclaimer(self):
        """Safety: lessons must be labeled as reference, not ground truth."""
        experience_memory.record("Cam sành", ["search"], 9.0, "x" * 200)
        prompt = experience_memory.build_prompt("Cam sành ở đâu")
        assert "THAM KHẢO" in prompt

    def test_empty_when_no_match(self):
        assert experience_memory.build_prompt("totally unrelated query") == ""


class TestStats:
    def test_stats_structure(self):
        experience_memory.record("Q1", ["search"], 9.0, "x" * 200)
        experience_memory.record("Q2", [], 2.0, "y")
        s = experience_memory.stats()
        assert s["total"] == 2
        assert s["positive"] == 1
        assert s["negative"] == 1
