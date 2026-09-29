#!/usr/bin/env python3
"""Xuất dữ liệu nhẹ cho FE prerender/SSG.

Output files:
  - web-nuxt/public/data/entity-index.json: tất cả entities (minimal fields)
  - web-nuxt/public/data/areas.json: danh sách khu vực + counts
  - web-nuxt/public/data/types.json: danh sách entity types + counts

Dùng cho: FilterChips, search suggestions, autocomplete, sitemap.

Usage:
  python scripts/export_fe_data.py
"""

import json
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
OUT_DIR = ROOT / "web-nuxt" / "public" / "data"

sys.path.insert(0, str(AGENT_DIR))

TYPE_META = {
    "dish":          {"label": "Ẩm thực",      "emoji": "🍜"},
    "experience":    {"label": "Trải nghiệm",  "emoji": "🎯"},
    "product":       {"label": "Đặc sản",      "emoji": "🎁"},
    "accommodation": {"label": "Lưu trú",      "emoji": "🏨"},
    "nature":        {"label": "Thiên nhiên",   "emoji": "🌿"},
    "history":       {"label": "Di tích",       "emoji": "🏛️"},
    "attraction":    {"label": "Tham quan",     "emoji": "📸"},
    "craft_village": {"label": "Làng nghề",     "emoji": "🏺"},
    "event":         {"label": "Sự kiện",       "emoji": "🎉"},
    "facility":      {"label": "Tiện ích",      "emoji": "🏢"},
    "organization":  {"label": "Tổ chức",       "emoji": "🤝"},
    "person":        {"label": "Nhân vật",      "emoji": "👤"},
    "cafe":          {"label": "Cà phê",        "emoji": "☕"},
    "restaurant":    {"label": "Nhà hàng",      "emoji": "🍽️"},
    "drink":         {"label": "Thức uống",     "emoji": "🥤"},
    "itinerary":     {"label": "Lộ trình",      "emoji": "🗺️"},
    "economy":       {"label": "Kinh tế",       "emoji": "💰"},
}

AREA_LABELS = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}


def load_all():
    try:
        from database import db
        entities = db.all_entities()
        source = "database"
    except Exception as e:
        print(f"[WARN] DB import failed ({e}), using data.json")
        data_path = ROOT / "web" / "data.json"
        if not data_path.exists():
            print(f"[ERROR] {data_path} not found and DB unavailable")
            sys.exit(1)
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        entities = data.get("entities", [])
        source = "data.json"
    return entities, source


def get_place_name(entities: list, place_id: str) -> str:
    for e in entities:
        if e.get("id") == place_id and e.get("type") == "place":
            return e.get("name", "")
    return ""


def export_entity_index(entities: list, places: dict, output_dir: Path | None = None):
    content_entities = [e for e in entities if e.get("type") != "place"]

    items = []
    for e in content_entities:
        summary = (e.get("summary") or "")[:120]
        images = e.get("images") or []
        image = images[0] if images else None
        coords = e.get("coordinates")
        place_id = e.get("placeId", "")
        place_name = places.get(place_id, "")
        area = e.get("area", "")

        items.append({
            "id": e.get("id", ""),
            "name": e.get("name", ""),
            "type": e.get("type", ""),
            "summary": summary,
            "image": image,
            "place_name": place_name,
            "place_area": AREA_LABELS.get(area, area),
            "coords": coords,
        })

    out_path = (output_dir or OUT_DIR) / "entity-index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[OK] entity-index.json: {len(items)} entities ({out_path.stat().st_size / 1024:.0f} KB)")
    return items


def export_areas(entities: list, output_dir: Path | None = None):
    area_counts = {}
    for e in entities:
        if e.get("type") == "place":
            continue
        area = e.get("area", "") or "unknown"
        area_counts[area] = area_counts.get(area, 0) + 1

    items = []
    for area_id, count in sorted(area_counts.items(), key=lambda x: -x[1]):
        items.append({
            "id": area_id,
            "name": AREA_LABELS.get(area_id, area_id),
            "entity_count": count,
        })

    out_path = (output_dir or OUT_DIR) / "areas.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[OK] areas.json: {len(items)} areas")
    return items


def export_types(entities: list, output_dir: Path | None = None):
    type_counts = {}
    for e in entities:
        if e.get("type") == "place":
            continue
        etype = e.get("type", "unknown")
        type_counts[etype] = type_counts.get(etype, 0) + 1

    items = []
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        meta = TYPE_META.get(etype, {"label": etype, "emoji": "📍"})
        items.append({
            "type": etype,
            "label": meta["label"],
            "emoji": meta["emoji"],
            "count": count,
        })

    out_path = (output_dir or OUT_DIR) / "types.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[OK] types.json: {len(items)} types")
    return items


def _load_json_source(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list):
        raise ValueError("JSON source must contain an entities list")
    return payload["entities"]


def _load_sqlite_source(path: Path) -> list[dict]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM entities ORDER BY id").fetchall()
    except sqlite3.Error as exc:
        raise ValueError(f"cannot read SQLite source: {path}") from exc
    entities = []
    for row in rows:
        item = dict(row)
        for field in ("images", "coordinates", "attributes", "season"):
            if isinstance(item.get(field), str):
                try:
                    item[field] = json.loads(item[field])
                except json.JSONDecodeError:
                    pass
        entities.append(item)
    return entities


def export_frontend_data(*, sqlite_path: Path | None, json_path: Path | None, output_dir: Path) -> dict[str, Path]:
    """Export all FE indexes from exactly one explicitly selected source."""
    if (sqlite_path is None) == (json_path is None):
        raise ValueError("exactly one of sqlite_path or json_path must be provided")
    output_dir = Path(output_dir)
    if sqlite_path is not None:
        entities = _load_sqlite_source(Path(sqlite_path))
    else:
        entities = _load_json_source(Path(json_path))
    places = {
        e.get("id", ""): e.get("name", "")
        for e in entities
        if e.get("type") == "place"
    }
    export_entity_index(entities, places, output_dir)
    export_areas(entities, output_dir)
    export_types(entities, output_dir)
    return {
        "entity_index": output_dir / "entity-index.json",
        "areas": output_dir / "areas.json",
        "types": output_dir / "types.json",
    }


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--sqlite", type=Path)
    source_group.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    outputs = export_frontend_data(
        sqlite_path=args.sqlite,
        json_path=args.json_path,
        output_dir=args.output_dir,
    )
    entities = _load_sqlite_source(args.sqlite) if args.sqlite else _load_json_source(args.json_path)
    print(f"[INFO] Loaded {len(entities)} entities from {'sqlite' if args.sqlite else 'json'}")
    index = json.loads(outputs["entity_index"].read_text(encoding="utf-8"))
    areas = json.loads(outputs["areas"].read_text(encoding="utf-8"))
    types = json.loads(outputs["types"].read_text(encoding="utf-8"))

    print(f"\n{'='*40}")
    print("Export Summary")
    print(f"{'='*40}")
    print(f"  Entities:  {len(index)}")
    print(f"  Areas:     {len(areas)}")
    print(f"  Types:     {len(types)}")
    print(f"  Source:    {'sqlite' if args.sqlite else 'json'}")
    print(f"  Output:    {args.output_dir}")


if __name__ == "__main__":
    main()
