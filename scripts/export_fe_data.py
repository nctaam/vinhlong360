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


def export_entity_index(entities: list, places: dict):
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

    out_path = OUT_DIR / "entity-index.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[OK] entity-index.json: {len(items)} entities ({out_path.stat().st_size / 1024:.0f} KB)")
    return items


def export_areas(entities: list):
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

    out_path = OUT_DIR / "areas.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[OK] areas.json: {len(items)} areas")
    return items


def export_types(entities: list):
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

    out_path = OUT_DIR / "types.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[OK] types.json: {len(items)} types")
    return items


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    entities, source = load_all()
    print(f"[INFO] Loaded {len(entities)} entities from {source}")

    # Build place lookup
    places = {}
    for e in entities:
        if e.get("type") == "place":
            places[e.get("id", "")] = e.get("name", "")

    index = export_entity_index(entities, places)
    areas = export_areas(entities)
    types = export_types(entities)

    print(f"\n{'='*40}")
    print("Export Summary")
    print(f"{'='*40}")
    print(f"  Entities:  {len(index)}")
    print(f"  Areas:     {len(areas)}")
    print(f"  Types:     {len(types)}")
    print(f"  Source:    {source}")
    print(f"  Output:    {OUT_DIR}")


if __name__ == "__main__":
    main()
