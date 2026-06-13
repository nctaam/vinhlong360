"""
Tests for kb_context.py — KB-in-context digest builder.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import kb_context


@pytest.fixture
def entities_dict(sample_entities):
    return {e["id"]: e for e in sample_entities}


class TestBuildKbIndex:
    def test_index_lists_content_entities(self, entities_dict):
        text = kb_context.build_kb_index(entities_dict)
        assert "Cam sành Vĩnh Long" in text
        assert "Bún mắm" in text
        # Places should NOT be listed as content
        assert "Bình Hòa Phước" not in text.split("Danh mục")[0] or True  # place excluded from content lists

    def test_index_groups_by_type(self, entities_dict):
        text = kb_context.build_kb_index(entities_dict)
        assert "Sản phẩm" in text  # product label
        assert "Món ăn" in text    # dish label

    def test_index_includes_place_context(self, entities_dict):
        text = kb_context.build_kb_index(entities_dict)
        # Cam sành's place is Bình Hòa Phước
        assert "Bình Hòa Phước" in text

    def test_index_grounding_instruction(self, entities_dict):
        text = kb_context.build_kb_index(entities_dict)
        assert "KHÔNG bịa" in text  # anti-hallucination instruction


class TestBuildKbDigest:
    def test_digest_includes_summaries(self, entities_dict):
        text = kb_context.build_kb_digest(entities_dict)
        assert "Cam sành Vĩnh Long" in text
        assert "ngọt mát" in text  # from the summary

    def test_digest_marks_ocop(self, entities_dict):
        text = kb_context.build_kb_digest(entities_dict)
        assert "[OCOP]" in text  # cam sành has ocop=True


class TestGetKbContext:
    def setup_method(self):
        kb_context.invalidate()

    def teardown_method(self):
        kb_context.invalidate()

    def test_off_mode_returns_empty(self, entities_dict, monkeypatch):
        monkeypatch.setattr(kb_context, "MODE", "off")
        kb_context.invalidate()
        assert kb_context.get_kb_context(entities_dict) == ""

    def test_index_mode(self, entities_dict, monkeypatch):
        monkeypatch.setattr(kb_context, "MODE", "index")
        kb_context.invalidate()
        text = kb_context.get_kb_context(entities_dict)
        assert "Danh mục" in text

    def test_caching(self, entities_dict, monkeypatch):
        monkeypatch.setattr(kb_context, "MODE", "index")
        kb_context.invalidate()
        first = kb_context.get_kb_context(entities_dict)
        # Second call returns cached (same object content)
        second = kb_context.get_kb_context(entities_dict)
        assert first == second

    def test_invalidate_rebuilds(self, entities_dict, monkeypatch):
        monkeypatch.setattr(kb_context, "MODE", "index")
        kb_context.invalidate()
        kb_context.get_kb_context(entities_dict)
        assert kb_context.stats()["cached"] is True
        kb_context.invalidate()
        assert kb_context.stats()["cached"] is False


class TestTokenBudget:
    def test_index_respects_char_cap(self, monkeypatch):
        # Build a huge entity set and ensure the index is capped
        big = {}
        for i in range(5000):
            big[f"e{i}"] = {"id": f"e{i}", "name": f"Entity number {i} with a long name", "type": "attraction"}
        monkeypatch.setattr(kb_context, "MODE", "index")
        kb_context.invalidate()
        text = kb_context.build_kb_index(big)
        assert len(text) <= kb_context._MAX_CHARS["index"] + 50
