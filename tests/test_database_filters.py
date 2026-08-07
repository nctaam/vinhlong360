"""Regression tests for database-level public filters."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

import database  # noqa: E402


# `USE_PG` là hằng module chốt lúc import (database.py:38) và `Database.__init__`
# chỉ copy nó, nên khi CI đặt DATABASE_URL thì tham số db_path bị BỎ QUA và đối
# tượng nối thẳng vào Postgres dùng chung — đó là lý do module này từng
# `pytestmark = skipif(db._use_pg)` và KHÔNG hề chạy trong job test-pg.
#
# Không cần đánh đổi đó: ghim backend tường minh (khuôn agent/tests/conftest.py:38)
# thì isolate thật ở MỌI môi trường, và cả 4 bài chạy được ở cả hai job thay vì im
# lặng biến mất. Nhánh SQL riêng của Postgres (_append_area_filter/_append_q_filter/
# _month_condition/e."updatedAt") vẫn CHƯA có test — xem báo cáo, đó là việc khác.
def _make_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "USE_PG", False)
    monkeypatch.setattr(database, "DATABASE_URL", "")
    db = database.Database(str(tmp_path / "filters.db"))
    assert db._use_pg is False and db._dsn is None
    assert Path(db.db_path).parent == tmp_path
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


def test_list_entities_filters_by_place_area(tmp_path, monkeypatch):
    db = _make_db(tmp_path, monkeypatch)

    rows = db.list_entities(area="vinh-long", limit=10)

    assert [r["id"] for r in rows] == ["cake-vl"]


def test_search_entities_filters_by_place_area(tmp_path, monkeypatch):
    db = _make_db(tmp_path, monkeypatch)

    rows = db.search_entities(q="cake", area="ben-tre", limit=10)

    assert [r["id"] for r in rows] == ["cake-bt"]


def test_count_entities_filtered_ignores_limit_semantics(tmp_path, monkeypatch):
    db = _make_db(tmp_path, monkeypatch)

    assert db.count_entities_filtered(area="vinh-long") == 1
    assert db.count_entities_filtered(q="cake") == 2
    assert db.count_entities_filtered(q="cake", area="ben-tre") == 1

def test_get_relationships_sorts_filters_and_computes_near_distance(tmp_path, monkeypatch):
    db = _make_db(tmp_path, monkeypatch)
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
