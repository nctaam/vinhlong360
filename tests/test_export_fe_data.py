from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("export_fe_data", ROOT / "scripts" / "export_fe_data.py")
export_fe_data = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = export_fe_data
SPEC.loader.exec_module(export_fe_data)


SAMPLE_ENTITIES = [
    {"id": "xa-an-binh", "type": "place", "name": "Xã An Bình", "summary": "Xã",
     "area": "vinh-long", "coordinates": [10.25, 106.0]},
    {"id": "cam-sanh", "type": "product", "name": "Cam sành Vĩnh Long", "summary": "Cam đặc sản",
     "area": "vinh-long", "coordinates": [10.26, 106.01], "placeId": "xa-an-binh",
     "images": ["https://example.com/cam.jpg"]},
    {"id": "pho-bo", "type": "dish", "name": "Phở Bò", "summary": "Món ăn truyền thống",
     "area": "ben-tre", "coordinates": [10.24, 106.37]},
    {"id": "cafe-1", "type": "cafe", "name": "Coffee Shop", "summary": "Quán cà phê",
     "area": "tra-vinh"},
]


def test_export_entity_index_excludes_places(tmp_path: Path) -> None:
    places = {"xa-an-binh": "Xã An Bình"}
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        items = export_fe_data.export_entity_index(SAMPLE_ENTITIES, places)

    assert all(item["type"] != "place" for item in items)
    assert len(items) == 3


def test_export_entity_index_includes_place_name(tmp_path: Path) -> None:
    places = {"xa-an-binh": "Xã An Bình"}
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        items = export_fe_data.export_entity_index(SAMPLE_ENTITIES, places)

    cam = next(i for i in items if i["id"] == "cam-sanh")
    assert cam["place_name"] == "Xã An Bình"
    assert cam["image"] == "https://example.com/cam.jpg"


def test_export_entity_index_truncates_summary(tmp_path: Path) -> None:
    long_entities = [
        {"id": "long", "type": "attraction", "name": "Long",
         "summary": "x" * 200, "area": "vinh-long"},
    ]
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        items = export_fe_data.export_entity_index(long_entities, {})

    assert len(items[0]["summary"]) == 120


def test_export_entity_index_writes_json(tmp_path: Path) -> None:
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        export_fe_data.export_entity_index(SAMPLE_ENTITIES, {})

    out_file = out_dir / "entity-index.json"
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(data) == 3


def test_export_areas_counts_non_place(tmp_path: Path) -> None:
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        areas = export_fe_data.export_areas(SAMPLE_ENTITIES)

    area_map = {a["id"]: a for a in areas}
    assert area_map["vinh-long"]["entity_count"] == 1
    assert area_map["ben-tre"]["entity_count"] == 1
    assert area_map["tra-vinh"]["entity_count"] == 1


def test_export_areas_uses_vietnamese_labels(tmp_path: Path) -> None:
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        areas = export_fe_data.export_areas(SAMPLE_ENTITIES)

    names = {a["name"] for a in areas}
    assert "Vĩnh Long" in names
    assert "Bến Tre" in names


def test_export_types_counts_correctly(tmp_path: Path) -> None:
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        types = export_fe_data.export_types(SAMPLE_ENTITIES)

    type_map = {t["type"]: t for t in types}
    assert type_map["product"]["count"] == 1
    assert type_map["dish"]["count"] == 1
    assert type_map["cafe"]["count"] == 1
    assert "place" not in type_map


def test_export_types_includes_labels_and_emoji(tmp_path: Path) -> None:
    out_dir = tmp_path / "data"
    out_dir.mkdir()

    with patch.object(export_fe_data, "OUT_DIR", out_dir):
        types = export_fe_data.export_types(SAMPLE_ENTITIES)

    dish = next(t for t in types if t["type"] == "dish")
    assert dish["label"] == "Ẩm thực"
    assert dish["emoji"]


def test_load_all_falls_back_to_data_json(tmp_path: Path, monkeypatch) -> None:
    data = {"entities": [{"id": "x", "type": "dish", "name": "X"}], "relationships": []}
    data_json = tmp_path / "web" / "data.json"
    data_json.parent.mkdir(parents=True)
    data_json.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(export_fe_data, "ROOT", tmp_path)

    with patch.dict("sys.modules", {"database": None}):
        entities, source = export_fe_data.load_all()

    assert source == "data.json"
    assert len(entities) == 1


def test_load_all_exits_when_no_source(tmp_path: Path, monkeypatch) -> None:
    import pytest
    monkeypatch.setattr(export_fe_data, "ROOT", tmp_path)

    with patch.dict("sys.modules", {"database": None}):
        with pytest.raises(SystemExit):
            export_fe_data.load_all()


def test_type_meta_covers_all_common_types() -> None:
    expected = {"dish", "product", "attraction", "restaurant", "cafe", "accommodation",
                "nature", "craft_village", "event", "experience", "person", "drink"}
    for t in expected:
        assert t in export_fe_data.TYPE_META, f"{t} missing from TYPE_META"
