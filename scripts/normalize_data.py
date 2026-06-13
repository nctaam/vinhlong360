#!/usr/bin/env python3
"""Normalize VinhLong360 static data safely, with a backup before writes."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "web" / "data.json"
DEFAULT_BACKUP_DIR = ROOT / "agent" / "data" / "kb_snapshots"
MEKONG_LAT_RANGE = (8.0, 11.5)
MEKONG_LNG_RANGE = (104.0, 107.5)
MAX_NEAR_DISTANCE_KM = 50.0
MAX_NEAR_PER_ENTITY = 12


def _configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def _parse_json_string(value: Any) -> Any:
    current = value
    for _ in range(4):
        if not isinstance(current, str):
            return current
        text = current.strip()
        if not text:
            return None
        try:
            current = json.loads(text)
        except json.JSONDecodeError:
            return current
    return current


def normalized_coordinates(value: Any) -> list[float] | None:
    value = _parse_json_string(value)
    if isinstance(value, dict):
        lat = value.get("lat", value.get("latitude"))
        lng = value.get("lng", value.get("lon", value.get("longitude")))
        value = [lat, lng]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat = float(value[0])
        lng = float(value[1])
    except (TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return [lat, lng]
    if -180 <= lat <= 180 and -90 <= lng <= 90:
        # Common imported shape is [lng, lat]; contract requires [lat, lng].
        return [lng, lat]
    return None


def rel_source(rel: dict[str, Any]) -> Any:
    return rel.get("from") or rel.get("from_id") or rel.get("source_id")


def rel_target(rel: dict[str, Any]) -> Any:
    return rel.get("to") or rel.get("to_id") or rel.get("target_id")


def rel_type(rel: dict[str, Any]) -> Any:
    return rel.get("type") or rel.get("rel_type")

def in_mekong_bbox(coords: list[float] | None) -> bool:
    if not coords:
        return False
    lat, lng = coords
    return MEKONG_LAT_RANGE[0] <= lat <= MEKONG_LAT_RANGE[1] and MEKONG_LNG_RANGE[0] <= lng <= MEKONG_LNG_RANGE[1]

def haversine_km(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b:
        return None
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    val = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(val))

def entity_effective_area(entity: dict[str, Any], place_by_id: dict[str, dict[str, Any]]) -> str | None:
    area = entity.get("area")
    if area:
        return str(area)
    place_id = entity.get("placeId")
    place = place_by_id.get(str(place_id)) if place_id else None
    if place and place.get("area"):
        return str(place["area"])
    return None


AREA_KEYWORDS = {
    "vinh-long": ("vinh long", "vĩnh long"),
    "ben-tre": ("ben tre", "bến tre"),
    "tra-vinh": ("tra vinh", "trà vinh"),
}

AREA_LABELS = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}

LEVEL_LABELS = {
    "phuong": "phường",
    "xa": "xã",
    "ward": "phường",
    "commune": "xã",
}


def _fold_text(value: Any) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d")


def infer_area(entity: dict[str, Any]) -> str | None:
    attrs = entity.get("attributes") or {}
    fields = [
        entity.get("id"),
        entity.get("name"),
        entity.get("legacyArea"),
        attrs.get("address"),
        attrs.get("area"),
        attrs.get("province"),
        attrs.get("location"),
    ]
    text = _fold_text(" | ".join(str(value) for value in fields if value))
    hits = [
        area for area, keywords in AREA_KEYWORDS.items()
        if any(_fold_text(keyword) in text for keyword in keywords)
    ]
    return hits[0] if len(hits) == 1 else None

def infer_area_from_place(entity: dict[str, Any], place_by_id: dict[str, dict[str, Any]]) -> tuple[str | None, bool]:
    """Infer area from placeId only when entity text does not contradict it."""
    if entity.get("type") == "place" or entity.get("area"):
        return None, False
    place_id = entity.get("placeId")
    if not place_id:
        return None, False
    place = place_by_id.get(str(place_id))
    if not place:
        return None, False
    place_area = place.get("area")
    if not place_area:
        return None, False
    keyword_area = infer_area(entity)
    if keyword_area and keyword_area != place_area:
        return None, True
    return str(place_area), False

def generate_place_summary(entity: dict[str, Any]) -> str | None:
    if entity.get("type") != "place" or entity.get("summary"):
        return None
    name = entity.get("name")
    if not name:
        return None
    area = entity.get("area")
    area_label = AREA_LABELS.get(area, area)
    level = LEVEL_LABELS.get(entity.get("level"), "đơn vị hành chính")
    if area_label:
        summary = f"{name} là {level} thuộc khu vực {area_label}."
    else:
        summary = f"{name} là {level} trong bộ dữ liệu hành chính của vinhlong360."
    legacy_area = entity.get("legacyArea")
    if legacy_area:
        summary += f" Thông tin phân vùng hiện có trong dữ liệu: {legacy_area}."
    summary += " Bản ghi này đóng vai trò mốc hành chính để liên kết các điểm đến, sản phẩm và trải nghiệm địa phương trong vinhlong360."
    return summary


def render_data_js(data: dict[str, Any]) -> str:
    places = [e for e in data.get("entities", []) if e.get("type") == "place"]
    items = [e for e in data.get("entities", []) if e.get("type") != "place"]
    relationships = data.get("relationships", [])
    itineraries = data.get("itineraries", [])
    return (
        "/* vinhlong360 data - auto-synced from data.json */\n"
        "(function () {\n"
        f"var places = {json.dumps(places, ensure_ascii=False, indent=2)};\n"
        f"var items = {json.dumps(items, ensure_ascii=False, indent=2)};\n"
        f"var relationships = {json.dumps(relationships, ensure_ascii=False, indent=2)};\n"
        f"var itineraries = {json.dumps(itineraries, ensure_ascii=False, indent=2)};\n"
        "window.VL_DATA = {\n"
        "  entities: places.concat(items),\n"
        "  relationships: relationships,\n"
        "  itineraries: itineraries,\n"
        "  ALL_MONTHS: [1,2,3,4,5,6,7,8,9,10,11,12]\n"
        "};\n"
        "})();\n"
    )

def write_data_js(data: dict[str, Any], path: Path, content: str | None = None) -> bool:
    js = content if content is not None else render_data_js(data)
    if path.exists() and path.read_text(encoding="utf-8", errors="replace") == js:
        return False
    path.write_text(js, encoding="utf-8", newline="\n")
    return True

def regenerate_near_relationships(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    place_by_id: dict[str, dict[str, Any]],
    *,
    max_distance_km: float = MAX_NEAR_DISTANCE_KM,
    max_per_entity: int = MAX_NEAR_PER_ENTITY,
) -> tuple[list[dict[str, Any]], int, int]:
    non_near = [rel for rel in relationships if isinstance(rel, dict) and rel_type(rel) != "near"]
    before_near = len(relationships) - len(non_near)
    candidates: list[dict[str, Any]] = []
    for entity in entities:
        if not isinstance(entity, dict) or entity.get("type") == "place" or not entity.get("id"):
            continue
        coords = normalized_coordinates(entity.get("coordinates"))
        area = entity_effective_area(entity, place_by_id)
        if not area or not in_mekong_bbox(coords):
            continue
        candidates.append({"entity": entity, "id": str(entity["id"]), "coords": coords, "area": area, "placeId": entity.get("placeId")})

    pairs: list[tuple[int, float, str, str]] = []
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1:]:
            if left["area"] != right["area"]:
                continue
            distance = haversine_km(left["coords"], right["coords"])
            if distance is None or distance > max_distance_km:
                continue
            same_place = left.get("placeId") and left.get("placeId") == right.get("placeId")
            pairs.append((0 if same_place else 1, distance, left["id"], right["id"]))

    pairs.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    fanout: dict[str, int] = {}
    rebuilt: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for priority, distance, source_id, target_id in pairs:
        if fanout.get(source_id, 0) >= max_per_entity or fanout.get(target_id, 0) >= max_per_entity:
            continue
        key = (source_id, target_id, "near")
        if key in seen:
            continue
        seen.add(key)
        fanout[source_id] = fanout.get(source_id, 0) + 1
        fanout[target_id] = fanout.get(target_id, 0) + 1
        rebuilt.append({"from": source_id, "to": target_id, "type": "near", "distance_km": round(distance, 2)})

    return non_near + rebuilt, before_near, len(rebuilt)

def drop_produced_in_area_conflicts(
    relationships: list[dict[str, Any]],
    entity_by_id: dict[str, dict[str, Any]],
    place_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    kept: list[dict[str, Any]] = []
    dropped = 0
    for rel in relationships:
        if not isinstance(rel, dict) or rel_type(rel) != "produced_in":
            kept.append(rel)
            continue
        source_id = rel_source(rel)
        target_id = rel_target(rel)
        source = entity_by_id.get(str(source_id)) if source_id else None
        target = entity_by_id.get(str(target_id)) if target_id else None
        source_area = entity_effective_area(source, place_by_id) if source else None
        target_area = entity_effective_area(target, place_by_id) if target else None
        if source_area and target_area and source_area != target_area:
            dropped += 1
            continue
        kept.append(rel)
    return kept, dropped


def main() -> int:
    _configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to data.json")
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR, help="Directory for pre-write backup")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup")
    parser.add_argument("--drop-broken-relationships", action="store_true", help="Remove relationships that reference missing entity IDs")
    parser.add_argument("--remove-legacy-coords", action="store_true", help="Remove legacy coords after copying to coordinates")
    parser.add_argument("--infer-area", action="store_true", help="Infer province area when an entity clearly mentions Vinh Long, Ben Tre, or Tra Vinh")
    parser.add_argument("--infer-area-from-place", action="store_true", help="Infer missing entity area from placeId when entity text does not contradict the place area")
    parser.add_argument("--summarize-places", action="store_true", help="Generate concise summaries for place entities from existing administrative fields")
    parser.add_argument("--drop-out-of-bounds-coordinates", action="store_true", help="Remove coordinates outside the Mekong bbox instead of keeping wrong map points")
    parser.add_argument("--repair-area-place-conflicts", action="store_true", help="Remove non-place placeId values whose place area conflicts with explicit entity area")
    parser.add_argument("--repair-produced-in-area-conflicts", action="store_true", help="Remove produced_in relationships whose endpoints have conflicting province areas")
    parser.add_argument("--regenerate-near", action="store_true", help="Rebuild near relationships from verified in-bounds coordinates")
    parser.add_argument("--no-sync-js", action="store_true", help="Do not regenerate sibling data.js")
    parser.add_argument("--check", action="store_true", help="Report planned changes without writing")
    args = parser.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8-sig"))
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    if not isinstance(entities, list) or not isinstance(relationships, list):
        raise SystemExit("data.json must contain list fields: entities and relationships")

    added_coordinates = 0
    normalized_existing_coordinates = 0
    removed_legacy_coords = 0
    inferred_area = 0
    inferred_area_from_place = 0
    area_place_conflicts = 0
    generated_place_summaries = 0
    dropped_out_of_bounds_coordinates = 0
    repaired_area_place_conflicts = 0
    repaired_produced_in_area_conflicts = 0
    previous_near_relationships = 0
    regenerated_near_relationships = 0
    place_by_id = {
        str(entity.get("id")): entity
        for entity in entities
        if isinstance(entity, dict) and entity.get("type") == "place" and entity.get("id")
    }
    entity_by_id = {
        str(entity.get("id")): entity
        for entity in entities
        if isinstance(entity, dict) and entity.get("id")
    }

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        if args.infer_area and entity.get("type") != "place" and not entity.get("area"):
            area = infer_area(entity)
            if area:
                entity["area"] = area
                inferred_area += 1
        if args.infer_area_from_place and entity.get("type") != "place" and not entity.get("area"):
            area, conflict = infer_area_from_place(entity, place_by_id)
            if area:
                entity["area"] = area
                inferred_area_from_place += 1
            elif conflict:
                area_place_conflicts += 1
        if args.summarize_places:
            summary = generate_place_summary(entity)
            if summary:
                entity["summary"] = summary
                generated_place_summaries += 1
        coord = normalized_coordinates(entity.get("coordinates"))
        legacy = normalized_coordinates(entity.get("coords"))
        if args.drop_out_of_bounds_coordinates and coord is not None and not in_mekong_bbox(coord):
            entity.pop("coordinates", None)
            entity.pop("coords", None)
            dropped_out_of_bounds_coordinates += 1
            coord = None
            legacy = None
        if coord is None and legacy is not None:
            entity["coordinates"] = legacy
            added_coordinates += 1
        elif coord is not None:
            canonical = [coord[0], coord[1]]
            if entity.get("coordinates") != canonical:
                entity["coordinates"] = canonical
                normalized_existing_coordinates += 1
        if args.remove_legacy_coords and "coords" in entity and "coordinates" in entity:
            entity.pop("coords", None)
            removed_legacy_coords += 1

    if args.repair_area_place_conflicts:
        for entity in entities:
            if not isinstance(entity, dict) or entity.get("type") == "place" or not entity.get("placeId"):
                continue
            place = place_by_id.get(str(entity.get("placeId")))
            if not place:
                continue
            entity_area = entity.get("area")
            place_area = place.get("area")
            if entity_area and place_area and entity_area != place_area:
                entity.pop("placeId", None)
                repaired_area_place_conflicts += 1

    ids = {str(e.get("id")) for e in entities if isinstance(e, dict) and e.get("id")}
    dropped_relationships = 0
    if args.drop_broken_relationships:
        kept = []
        for rel in relationships:
            if not isinstance(rel, dict):
                dropped_relationships += 1
                continue
            src = rel_source(rel)
            dst = rel_target(rel)
            kind = rel_type(rel)
            if not src or not dst or not kind or str(src) not in ids or str(dst) not in ids:
                dropped_relationships += 1
                continue
            kept.append(rel)
        data["relationships"] = kept

    if args.repair_produced_in_area_conflicts:
        kept, repaired_produced_in_area_conflicts = drop_produced_in_area_conflicts(
            data.get("relationships", []),
            entity_by_id,
            place_by_id,
        )
        if kept != data.get("relationships", []):
            data["relationships"] = kept

    if args.regenerate_near:
        rebuilt, previous_near_relationships, regenerated_near_relationships = regenerate_near_relationships(
            entities,
            data.get("relationships", []),
            place_by_id,
        )
        if rebuilt != data.get("relationships", []):
            data["relationships"] = rebuilt

    data_js_changed = False
    rendered_data_js = None
    if not args.no_sync_js:
        data_js = args.data.with_name("data.js")
        rendered_data_js = render_data_js(data)
        data_js_changed = not data_js.exists() or data_js.read_text(encoding="utf-8", errors="replace") != rendered_data_js

    changed = any([
        added_coordinates,
        normalized_existing_coordinates,
        removed_legacy_coords,
        inferred_area,
        inferred_area_from_place,
        generated_place_summaries,
        dropped_out_of_bounds_coordinates,
        repaired_area_place_conflicts,
        repaired_produced_in_area_conflicts,
        previous_near_relationships != regenerated_near_relationships,
        dropped_relationships,
        data_js_changed,
    ])

    print("Normalization plan")
    print("==================")
    print(f"added_coordinates: {added_coordinates}")
    print(f"normalized_existing_coordinates: {normalized_existing_coordinates}")
    print(f"removed_legacy_coords: {removed_legacy_coords}")
    print(f"inferred_area: {inferred_area}")
    print(f"inferred_area_from_place: {inferred_area_from_place}")
    print(f"area_place_conflicts: {area_place_conflicts}")
    print(f"generated_place_summaries: {generated_place_summaries}")
    print(f"dropped_out_of_bounds_coordinates: {dropped_out_of_bounds_coordinates}")
    print(f"repaired_area_place_conflicts: {repaired_area_place_conflicts}")
    print(f"repaired_produced_in_area_conflicts: {repaired_produced_in_area_conflicts}")
    print(f"previous_near_relationships: {previous_near_relationships}")
    print(f"regenerated_near_relationships: {regenerated_near_relationships}")
    print(f"dropped_relationships: {dropped_relationships}")
    print(f"sync_js: {not args.no_sync_js}")
    print(f"data_js_changed: {data_js_changed}")

    if args.check:
        return 0
    if not changed:
        print("No changes needed.")
        return 0

    if not args.no_backup:
        args.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = args.backup_dir / f"snap_stabilization_{stamp}.json"
        shutil.copy2(args.data, backup)
        print(f"backup: {backup}")

    args.data.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"wrote: {args.data}")

    if not args.no_sync_js:
        data_js = args.data.with_name("data.js")
        if write_data_js(data, data_js, rendered_data_js):
            print(f"wrote: {data_js}")
        else:
            print(f"unchanged: {data_js}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
