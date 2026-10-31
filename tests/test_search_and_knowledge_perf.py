# -*- coding: utf-8 -*-
"""Regression & performance tests for Wave 15 (QW-43):
1. Memoized normalize_search_text (@lru_cache(8192)) & lazy _rank short-circuiting
   in agent/search_contract.py.
2. Self-healing precomputed search & geo-graph index (_get_entity_indexes) in
   agent/knowledge.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "agent"))

import knowledge  # noqa: E402
import search_contract  # noqa: E402


def test_normalize_search_text_memoization_and_vietnamese_diacritics():
    search_contract._normalize_str.cache_clear()
    s1 = search_contract.normalize_search_text("  Đờn ca   tài tử   Vĩnh Long  ")
    s2 = search_contract.normalize_search_text("  Đờn ca   tài tử   Vĩnh Long  ")
    assert s1 == "don ca tai tu vinh long"
    assert s2 == "don ca tai tu vinh long"
    info = search_contract._normalize_str.cache_info()
    assert info.maxsize == 8192
    assert info.hits >= 1


def test_rank_short_circuits_source_walk_when_name_matches(monkeypatch):
    called_source = 0
    orig_source_text = search_contract._source_text

    def spy_source_text(entity):
        nonlocal called_source
        called_source += 1
        return orig_source_text(entity)

    monkeypatch.setattr(search_contract, "_source_text", spy_source_text)
    entity = {
        "id": "banh-xeo-1",
        "name": "Bánh xèo hến Cù lao Dài",
        "summary": "Món bánh xèo truyền thống",
        "source": [{"title": "Báo Vĩnh Long", "url": "https://baovinhlong.com.vn"}],
    }
    res = search_contract._rank(entity, "Bánh xèo hến")
    assert res == (900.0, "name_prefix")
    # Because name matched, _source_text must NOT have been called
    assert called_source == 0


def test_knowledge_self_healing_index_reflects_mutations(monkeypatch):
    sample_entities = {
        "p-vl": {"id": "p-vl", "type": "place", "level": "phuong", "name": "Phường Long Châu", "area": "vinh-long"},
        "e-1": {
            "id": "e-1",
            "type": "dish",
            "name": "Bánh xèo hến",
            "summary": "Đặc sản cù lao",
            "placeId": "p-vl",
        },
        "e-2": {
            "id": "e-2",
            "type": "attraction",
            "name": "Văn Thánh Miếu",
            "summary": "Di tích lịch sử",
            "placeId": "p-vl",
        },
    }
    monkeypatch.setattr(knowledge, "_entities", sample_entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})

    hits = knowledge.search_entities(q="Bánh xèo")
    assert [h["id"] for h in hits] == ["e-1"]
    nearby = knowledge.nearby_entities("e-1")
    assert [n["id"] for n in nearby] == ["e-2"]

    # Mutate _entities in place by adding a new entity in the same placeId
    sample_entities["e-3"] = {
        "id": "e-3",
        "type": "product",
        "name": "Bưởi Năm Roi Bình Minh",
        "summary": "Trái cây đặc sản",
        "placeId": "p-vl",
    }
    hits_after = knowledge.search_entities(q="Bưởi Năm Roi")
    assert [h["id"] for h in hits_after] == ["e-3"]
    nearby_after = knowledge.nearby_entities("e-1")
    assert {n["id"] for n in nearby_after} == {"e-2", "e-3"}
