"""
Test discover_province._place_for — gán placeId cho entity phát hiện tự động.

Bảo vệ fix chống tái nhiễm lỗi "thùng chứa": KHÔNG dồn entity không khớp tên
vào ward đầu tiên của khu vực; trả None (chưa phân loại) thay vì gán sai xã.
"""
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discover_province
from discover_province import _place_for

PLACES = [
    {"id": "xa-an-binh", "type": "place", "name": "Xã An Bình", "area": "vinh-long"},
    {"id": "p-long-chau", "type": "place", "name": "Phường Long Châu", "area": "vinh-long"},
    {"id": "xa-ba-tri", "type": "place", "name": "Xã Ba Tri", "area": "ben-tre"},
]


def test_matches_ward_by_name_in_location():
    assert _place_for("vinh-long", "Ấp Bình Thuận, Xã An Bình", PLACES) == "xa-an-binh"
    assert _place_for("ben-tre", "Chợ Ba Tri, huyện Ba Tri", PLACES) == "xa-ba-tri"


def test_no_match_returns_none_not_first_place():
    # Địa chỉ không nêu tên ward nào → KHÔNG được dồn vào ward đầu tiên (xa-an-binh).
    assert _place_for("vinh-long", "Một nơi nào đó không rõ xã", PLACES) is None


def test_empty_location_returns_none():
    assert _place_for("vinh-long", "", PLACES) is None


def test_respects_area_scope():
    # location nêu 'Ba Tri' nhưng tìm trong area vinh-long → không khớp (Ba Tri ở ben-tre).
    assert _place_for("vinh-long", "Chợ Ba Tri", PLACES) is None


def test_apply_discovery_preserves_concurrent_fields(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    original = {
        "entities": [{"id": "existing", "name": "Existing", "type": "dish",
                      "attributes": {"phone": "0900000000"}}],
        "relationships": [],
        "itineraries": [],
    }
    data_path.write_text(json.dumps(original), encoding="utf-8")
    stale = deepcopy(original)
    latest = deepcopy(original)
    latest["entities"][0]["attributes"]["phone"] = "0911111111"
    data_path.write_text(json.dumps(latest), encoding="utf-8")
    persisted_to_db = []

    monkeypatch.setattr(discover_province, "DATA", data_path)
    monkeypatch.setattr(discover_province.kb_versioning, "snapshot", lambda **_kwargs: None)
    monkeypatch.setattr(
        discover_province,
        "_persist_to_db",
        lambda unique, data: persisted_to_db.extend(
            entity["id"] for entity in data["entities"]
            if entity["id"] in {item["id"] for item in unique}
        ),
    )
    monkeypatch.setattr(discover_province, "_sync_and_reload", lambda: None)

    summary = discover_province._apply_discovery(
        [{"id": "new-place", "name": "New Place", "type": "attraction",
          "summary": "New", "area": "vinh-long"}],
        stale,
        [],
        "test-model",
        "test",
        {"added": 0},
    )

    persisted = json.loads(data_path.read_text(encoding="utf-8"))
    assert summary["added"] == 1
    assert persisted["entities"][0]["attributes"]["phone"] == "0911111111"
    assert {entity["id"] for entity in persisted["entities"]} == {"existing", "new-place"}
    assert persisted_to_db == ["new-place"]
