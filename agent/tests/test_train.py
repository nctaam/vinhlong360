"""
Tests for train.py — the training harness scoring logic (offline, no LLM/server).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import train


class TestScoreAnswer:
    def test_full_coverage_high_score(self):
        reply = "Cam sành Trà Ôn là đặc sản nổi tiếng " * 8  # long, substantive
        s = train.score_answer(reply, ["cam sành", "Trà Ôn"], ["search", "entity_detail"])
        assert s >= 8.0

    def test_no_coverage_low_score(self):
        reply = "Đây là một câu trả lời dài nhưng không nhắc tới điều mong đợi nào cả. " * 5
        s = train.score_answer(reply, ["cam sành", "Trà Ôn"], ["search"])
        # coverage 0 → base 0, +1.5 length +1.5 tools = 3.0
        assert s <= 3.5

    def test_empty_reply_zero(self):
        assert train.score_answer("", ["x"], []) == 0.0

    def test_too_short_zero(self):
        assert train.score_answer("ngắn", ["x"], []) == 0.0

    def test_partial_coverage(self):
        reply = "Cam sành rất ngon và ngọt, trồng nhiều ở vùng đồng bằng sông Cửu Long quanh năm."
        s = train.score_answer(reply, ["cam sành", "Trà Ôn"], ["search"])
        # 1 of 2 facts → partial
        assert 3.0 <= s <= 8.0

    def test_diacritic_insensitive(self):
        reply = "Cam sanh Tra On la dac san " * 8  # no diacritics
        s = train.score_answer(reply, ["cam sành", "Trà Ôn"], ["search"])
        assert s >= 7.0  # should still match

    def test_abstention_penalized_when_facts_expected(self):
        reply = "Xin lỗi, mình chưa tìm thấy thông tin xác thực về điều này. " * 4
        s = train.score_answer(reply, ["cam sành", "Trà Ôn"], [])
        assert s < 3.0  # penalized


class TestTrainset:
    def test_default_trainset_loads(self):
        import json
        data = json.loads((train.DEFAULT_DATA).read_text(encoding="utf-8"))
        examples = data["examples"]
        assert len(examples) >= 15
        # Every example has query + expect
        for ex in examples:
            assert "query" in ex
            assert "expect" in ex and isinstance(ex["expect"], list)

    def test_trainset_covers_categories(self):
        import json
        data = json.loads((train.DEFAULT_DATA).read_text(encoding="utf-8"))
        cats = {ex.get("category") for ex in data["examples"]}
        assert {"factual", "recommendation", "itinerary", "comparison", "seasonal"}.issubset(cats)
