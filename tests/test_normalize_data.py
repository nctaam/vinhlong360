from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("normalize_data", ROOT / "scripts" / "normalize_data.py")
normalize_data = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(normalize_data)


def test_n1_reclassifies_restaurant_and_cafe() -> None:
    entities = [
        {"id": "a", "type": "dish", "name": "Quán Ăn Hương Vị", "attributes": {"address": "123 ABC"}},
        {"id": "b", "type": "dish", "name": "Highlands Coffee", "attributes": {}},
        {"id": "c", "type": "dish", "name": "Bánh tráng Mỹ Lồng", "attributes": {}},
        {"id": "d", "type": "dish", "name": "Nhà Hàng Phước Thịnh", "attributes": {}},
    ]
    fixes = normalize_data.n1_reclassify_dishes(entities)
    ids = {eid: t for eid, t, _ in fixes}
    assert ids["a"] == "restaurant"
    assert ids["b"] == "cafe"
    assert ids["d"] == "restaurant"
    assert "c" not in ids


def test_n2_fixes_wrong_province_in_summary() -> None:
    entities = [
        {"id": "x", "area": "ben-tre", "name": "Chợ BT", "summary": "Nằm ở tỉnh Vĩnh Long, chợ này"},
        {"id": "y", "area": "tra-vinh", "name": "Chùa TV", "summary": "Thuộc tỉnh Vĩnh Long, chùa này"},
        {"id": "z", "area": "vinh-long", "name": "Đình VL", "summary": "Nằm ở tỉnh Vĩnh Long, đình này"},
    ]
    fixes = normalize_data.n2_fix_wrong_province_summary(entities)
    fixed_ids = {eid for eid, *_ in fixes}
    assert "x" in fixed_ids
    assert "y" in fixed_ids
    assert "z" not in fixed_ids
    assert entities[0]["_n2_summary"] == "Nằm ở tỉnh Bến Tre, chợ này"
    assert entities[1]["_n2_summary"] == "Thuộc tỉnh Trà Vinh, chùa này"


def test_n3_deletes_dish_craft_village_rels() -> None:
    entity_map = {
        "d1": {"id": "d1", "type": "dish"},
        "cv1": {"id": "cv1", "type": "craft_village"},
        "a1": {"id": "a1", "type": "attraction"},
    }
    rels = [
        {"from": "d1", "to": "cv1", "type": "associated_with"},
        {"from": "d1", "to": "a1", "type": "associated_with"},
        {"from": "a1", "to": "cv1", "type": "related_to"},
    ]
    to_delete = normalize_data.n3_delete_dish_craft_village_rels(rels, entity_map)
    assert to_delete == [0]


def test_n4_deletes_far_near_rels() -> None:
    entity_map = {
        "a": {"id": "a", "coordinates": [10.25, 106.0]},
        "b": {"id": "b", "coordinates": [10.251, 106.001]},
        "c": {"id": "c", "coordinates": [10.5, 106.5]},
    }
    rels = [
        {"from": "a", "to": "b", "type": "near"},
        {"from": "a", "to": "c", "type": "near"},
    ]
    to_delete = normalize_data.n4_delete_far_near_rels(rels, entity_map, set())
    assert 0 not in to_delete
    assert 1 in to_delete


def test_n5_removes_bidirectional_dupes() -> None:
    rels = [
        {"from": "a", "to": "b", "type": "related_to"},
        {"from": "b", "to": "a", "type": "related_to"},
        {"from": "a", "to": "c", "type": "related_to"},
    ]
    to_delete = normalize_data.n5_remove_bidirectional_dupes(rels, set())
    assert len(to_delete) == 1
    assert to_delete[0] == 1


def test_n6_normalizes_ocop_star() -> None:
    entities = [
        {"id": "p1", "name": "Sản phẩm OCOP 3 sao", "attributes": {"ocop_rating": "3 sao"}, "tags": []},
        {"id": "p2", "name": "Dừa sáp", "attributes": {"ocop": "OCOP"}, "tags": ["ocop"]},
    ]
    fixes = normalize_data.n6_normalize_ocop(entities)
    fix_map = {eid: (star, attrs) for eid, _, star, attrs in fixes}
    assert fix_map["p1"][0] == 3
    assert fix_map["p1"][1]["ocop_star"] == 3
    assert "ocop_rating" not in fix_map["p1"][1]
    assert fix_map["p2"][1].get("ocop_certified") is True


def test_n9_clears_out_of_bbox() -> None:
    entities = [
        {"id": "a", "name": "A", "coordinates": [10.25, 106.0]},
        {"id": "b", "name": "B", "coordinates": [10.95, 106.8]},
        {"id": "c", "name": "C", "coordinates": [10.1, 105.0]},
    ]
    fixes = normalize_data.n9_clear_bad_coordinates(entities)
    ids = {eid for eid, *_ in fixes}
    assert "a" not in ids
    assert "b" in ids
    assert "c" in ids


def test_n12_normalizes_price_vnd_to_dong() -> None:
    entities = [
        {"id": "a", "attributes": {"price": "50.000 VND/kg"}},
        {"id": "b", "attributes": {"price": "miễn phí"}},
    ]
    fixes = normalize_data.n12_normalize_prices(entities)
    assert len(fixes) == 1
    assert fixes[0][3] == "50.000 đ/kg"
