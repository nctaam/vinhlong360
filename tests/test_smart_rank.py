"""Paired unit tests for agent/smart_rank.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

import smart_rank  # noqa: E402


def _entity(eid: str, name: str, summary: str = "", etype: str = "dish"):
    return {
        "id": eid,
        "name": name,
        "type": etype,
        "summary": summary,
        "attributes": {},
        "tags": [],
    }


def test_classify_query_match_tiers():
    exact = _entity("1", "Bánh tét Trà Cuôn")
    prefix = _entity("2", "Bánh tét ba màu Cầu Ngang")
    contains = _entity("3", "Làng nghề Bánh tét truyền thống")
    fuzzy = _entity("4", "Chợ Trà Cuôn", summary="Bán nhiều bánh tét dịp Tết")
    none = _entity("5", "Vườn cây An Bình", summary="Miệt vườn sông nước")

    assert smart_rank._classify_query_match(exact, "banh tet tra cuon") == "exact"
    assert smart_rank._classify_query_match(prefix, "banh tet") == "prefix"
    assert smart_rank._classify_query_match(contains, "banh tet") == "contains"
    assert smart_rank._classify_query_match(fuzzy, "banh tet") == "fuzzy"
    assert smart_rank._classify_query_match(none, "banh tet") == "none"


def test_rank_entities_respects_query_affinity(monkeypatch):
    monkeypatch.setattr(smart_rank, "get_popularity", lambda _eid: 0)
    entities = [
        _entity("none", "Chùa Âng", summary="Di tích kiến trúc Khmer", etype="attraction"),
        _entity("fuzzy", "Chợ Trà Cú", summary="Nổi tiếng món bánh tét", etype="attraction"),
        _entity("exact", "Bánh tét", summary="Món ngon ngày Tết", etype="dish"),
    ]
    ranked = smart_rank.rank_entities(entities, query="banh tet")
    assert [e["id"] for e in ranked] == ["exact", "fuzzy", "none"]


def test_rank_entities_without_query_keeps_default_behavior(monkeypatch):
    monkeypatch.setattr(smart_rank, "get_popularity", lambda _eid: 0)
    entities = [
        _entity("low", "Món A", etype="product"),
        _entity("high", "Điểm B", summary="Rất giàu thông tin chi tiết " * 10, etype="attraction"),
    ]
    ranked = smart_rank.rank_entities(entities, query=None)
    assert [e["id"] for e in ranked] == ["high", "low"]
