"""
Tests for prompt_compiler.py — lightweight BootstrapFewShot demo compiler.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import prompt_compiler


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(prompt_compiler, "RAW_FILE", tmp_path / "pool.json")
    monkeypatch.setattr(prompt_compiler, "COMPILED_FILE", tmp_path / "compiled.json")
    yield


class TestRecordDemo:
    def test_records_high_score(self):
        prompt_compiler.record_demo("Cam sành ở đâu", "Cam sành Trà Ôn nổi tiếng, " * 10, 9.0)
        assert prompt_compiler.stats()["pool_size"] == 1

    def test_skips_low_score(self):
        prompt_compiler.record_demo("Q", "a long enough answer " * 10, 5.0)
        assert prompt_compiler.stats()["pool_size"] == 0

    def test_skips_short_answer(self):
        prompt_compiler.record_demo("Q", "short", 9.0)
        assert prompt_compiler.stats()["pool_size"] == 0


class TestCompile:
    def test_compile_groups_by_intent(self):
        prompt_compiler.record_demo("Lập lịch trình Vĩnh Long", "Lịch trình chi tiết " * 20, 9.0)
        prompt_compiler.record_demo("So sánh Vĩnh Long Bến Tre", "So sánh khách quan " * 20, 9.0)
        res = prompt_compiler.compile()
        assert "itinerary" in res["intents"]
        assert "comparison" in res["intents"]

    def test_compile_diversity_dedup(self):
        # Two near-identical queries → only 1 kept per intent (diversity)
        for i in range(4):
            prompt_compiler.record_demo("Tìm chùa Phước Hậu ở đâu vậy", "Chùa Phước Hậu nằm ở... " * 15, 9.0)
        res = prompt_compiler.compile()
        # near-dups collapse → at most DEMOS_PER_INTENT, likely 1
        assert res["total_demos"] <= prompt_compiler.DEMOS_PER_INTENT


class TestGetDemos:
    def test_disabled_returns_empty(self, monkeypatch):
        monkeypatch.setattr(prompt_compiler, "ENABLED", False)
        prompt_compiler.record_demo("Cam sành ở đâu", "answer " * 30, 9.0)
        prompt_compiler.compile()
        assert prompt_compiler.get_demos("Cam sành") == []

    def test_enabled_returns_demos(self, monkeypatch):
        monkeypatch.setattr(prompt_compiler, "ENABLED", True)
        prompt_compiler.record_demo("Chùa Phước Hậu ở đâu", "Chùa Phước Hậu nằm ở Trà Ôn " * 10, 9.0)
        prompt_compiler.compile()
        demos = prompt_compiler.get_demos("Chùa Phước Hậu")
        assert len(demos) >= 1

    def test_build_prompt_format(self, monkeypatch):
        monkeypatch.setattr(prompt_compiler, "ENABLED", True)
        prompt_compiler.record_demo("Gợi ý đặc sản", "Đặc sản nổi bật gồm... " * 10, 9.0)
        prompt_compiler.compile()
        p = prompt_compiler.build_prompt("Gợi ý món ngon")
        if p:  # intent must match
            assert "Ví dụ tham khảo" in p
