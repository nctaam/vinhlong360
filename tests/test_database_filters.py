"""Regression tests for database-level public filters."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from database import Database, db  # noqa: E402

# Các test này isolate qua Database(tmp_path/'filters.db') — chỉ đúng trên SQLite
# (mỗi path = file riêng). Dưới PG, Database bỏ qua path (dùng DATABASE_URL chung)
# → không isolate được, dính state rò rỉ từ test khác. Skip khi PG.
pytestmark = pytest.mark.skipif(
    db._use_pg, reason="SQLite-file-isolation: Database(tmp_path) bị bỏ qua dưới Postgres (dùng chung DATABASE_URL)")


def _make_db(tmp_path):
    db = Database(str(tmp_path / "filters.db"))
    db.upsert_entity({
        "id": "place-vl",
        "type": "place",
        "name": "Vinh Long",
        "area": "vinh-long",
    })
    db.upsert_entity({
        "id": "place-bt",
        "type": "place",
        "name": "Ben Tre",
        "area": "ben-tre",
    })
    db.upsert_entity({
        "id": "cake-vl",
        "type": "dish",
        "name": "Cake Vinh Long",
        "summary": "river cake",
        "placeId": "place-vl",
        "area": "vinh-long",
    })
    db.upsert_entity({
        "id": "cake-bt",
        "type": "dish",
        "name": "Cake Ben Tre",
        "summary": "coconut cake",
        "placeId": "place-bt",
    })
    return db


def test_list_entities_filters_by_place_area(tmp_path):
    db = _make_db(tmp_path)

    rows = db.list_entities(area="vinh-long", limit=10)

    assert [r["id"] for r in rows] == ["cake-vl"]


def test_search_entities_filters_by_place_area(tmp_path):
    db = _make_db(tmp_path)

    rows = db.search_entities(q="cake", area="ben-tre", limit=10)

    assert [r["id"] for r in rows] == ["cake-bt"]


def test_count_entities_filtered_ignores_limit_semantics(tmp_path):
    db = _make_db(tmp_path)

    assert db.count_entities_filtered(area="vinh-long") == 1
    assert db.count_entities_filtered(q="cake") == 2
    assert db.count_entities_filtered(q="cake", area="ben-tre") == 1

def test_get_relationships_sorts_filters_and_computes_near_distance(tmp_path):
    db = _make_db(tmp_path)
    db.upsert_entity({
        "id": "market-vl",
        "type": "attraction",
        "name": "Market Vinh Long",
        "summary": "market",
        "area": "vinh-long",
        "coordinates": [10.25, 106.0],
    })
    db.upsert_entity({
        "id": "dock-vl",
        "type": "attraction",
        "name": "Dock Vinh Long",
        "summary": "dock",
        "area": "vinh-long",
        "coordinates": [10.251, 106.001],
    })
    db.add_relationship("market-vl", "dock-vl", "near")
    db.add_relationship("market-vl", "cake-vl", "related_to")

    relationships = db.get_relationships("market-vl", limit=10)

    assert [rel["rel_type"] for rel in relationships] == ["related_to", "near"]
    assert relationships[1]["distance_km"] < 1
    assert db.get_relationships("market-vl", rel_type="near")[0]["target_id"] == "dock-vl"
    assert db.get_relationships("market-vl", include_near=False)[0]["rel_type"] == "related_to"
    assert db.count_relationships("market-vl") == 2
