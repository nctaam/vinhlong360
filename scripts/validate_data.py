#!/usr/bin/env python3
"""Validate the VinhLong360 static knowledge data contract."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "web" / "data.json"
# Bao 3 tỉnh sáp nhập (Vĩnh Long+Bến Tre+Trà Vinh) + lề. Trước (8.0–11.5, 104.0–107.5)
# quá lỏng → lọt 58 toạ-độ sai (lat>11/lon>107/lon~104 transposed). Siết DI-001/005.
MEKONG_LAT_RANGE = (9.0, 11.0)
MEKONG_LNG_RANGE = (105.0, 107.0)
MAX_NEAR_DISTANCE_KM = 50.0
MAX_DIRECT_RELATIONSHIPS = 120
# Quan hệ phân-cấp (chứa-đựng) — không tính vào ngưỡng fanout-120 (vốn để chặn
# nhiễu "liên quan/gần đây" trên UI). located_in: entity→xã, xã→tỉnh.
HIERARCHICAL_REL_TYPES = {"located_in", "part_of"}
KNOWN_REL_TYPES = {
    "near", "related_to", "located_in", "part_of", "produced_in",
    "belongs_to", "serves", "famous_for", "associated_with",
    "ingredient_of", "sold_at", "managed_by", "owned_by",
}
# Placeholder summaries from failed LLM enrichment — must never ship to users.
# Phase 0 quarantined these (blanked to ""); this guard stops them returning.
from urllib.parse import urlparse  # noqa: E402

import re  # noqa: E402

VN_PHONE = re.compile(r"^(\+84|0)\d{9,10}$")

BOILERPLATE_SUMMARY = re.compile(
    r"không\s*(có\s*)?đủ thông tin|404|không tìm thấy thông tin|no information|not found",
    re.IGNORECASE,
)

VALID_ENTITY_TYPES = {
    "attraction", "place", "dish", "drink", "product", "itinerary",
    "facility", "organization", "accommodation", "experience",
    "craft_village", "event", "person", "history", "nature", "economy",
    "cafe", "restaurant",
}


@dataclass
class Issue:
    severity: str
    code: str
    message: str


def _configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


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


SEO_REQUIRED: dict[str, list[str]] = {
    "restaurant": ["specialty", "price_range", "phone", "hours"],
    "dish": ["specialty", "price_range", "origin"],
    "cafe": ["specialty", "price_range", "phone", "hours"],
    "accommodation": ["star_rating", "price_range", "phone"],
    "product": ["price", "price_range", "ocop", "ocop_star", "ocop_certified", "brand"],
    "event": ["date_start", "startDate"],
    "attraction": ["admission", "hours", "specialty", "price_range"],
    "experience": ["admission", "hours", "price_range"],
    "nature": ["admission", "hours"],
    "person": ["role"],
    "craft_village": ["specialty", "phone"],
    "drink": ["specialty", "price_range"],
}


def entity_quality_score(entity: dict[str, Any]) -> int:
    """Compute a 0-100 quality score for a single entity."""
    score = 100
    etype_raw = entity.get("type")
    is_place = etype_raw == "place"
    is_itinerary = etype_raw == "itinerary"

    summary_val = entity.get("summary")
    if not summary_val:
        score -= 20
    elif isinstance(summary_val, str):
        s = summary_val.strip()
        if BOILERPLATE_SUMMARY.search(s):
            score -= 20
        elif len(s) < 50:
            score -= 5
        elif len(s) > 500:
            score -= 3

    if not is_itinerary and not entity.get("coordinates") and not entity.get("coords"):
        score -= 15

    source = entity.get("source")
    if not source or (isinstance(source, list) and len(source) == 0):
        score -= 10

    if not is_place and not is_itinerary and not entity.get("placeId"):
        score -= 10

    if not is_place and not is_itinerary and not entity.get("area"):
        score -= 5

    imgs = entity.get("images")
    if not isinstance(imgs, list) or not any(isinstance(i, str) and i.startswith("http") for i in imgs):
        score -= 10

    confidence = entity.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.5:
        score -= 5

    etype = str(entity.get("type")) if entity.get("type") else None
    req = SEO_REQUIRED.get(etype) if etype else None
    if req:
        attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        if not any(attrs.get(k) for k in req):
            score -= 10

    updated_at = entity.get("updatedAt")
    created_at_val = entity.get("created_at")
    if isinstance(updated_at, str) and isinstance(created_at_val, str) and updated_at < created_at_val:
        score -= 2

    return max(0, score)


def graph_connectivity(entities: list[Any], relationships: list[Any]) -> dict[str, Any]:
    """Find disconnected subgraphs in the entity-relationship graph."""
    id_set: set[str] = set()
    for e in entities:
        if isinstance(e, dict) and e.get("id"):
            id_set.add(str(e["id"]))

    adj: dict[str, set[str]] = {eid: set() for eid in id_set}
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        src = str(rel_source(rel) or "")
        dst = str(rel_target(rel) or "")
        if src in id_set and dst in id_set and src != dst:
            adj[src].add(dst)
            adj[dst].add(src)

    visited: set[str] = set()
    components: list[int] = []

    for start in id_set:
        if start in visited:
            continue
        size = 0
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            size += 1
            stack.extend(adj[node] - visited)
        components.append(size)

    components.sort(reverse=True)
    return {
        "total_components": len(components),
        "largest_component": components[0] if components else 0,
        "isolated_entities": sum(1 for c in components if c == 1),
        "component_sizes": components[:10],
    }


def validate(data: dict[str, Any], data_path: Path) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    itineraries = data.get("itineraries", [])

    if not isinstance(entities, list):
        issues.append(Issue("error", "entities_not_list", "`entities` must be a list"))
        entities = []
    if not isinstance(relationships, list):
        issues.append(Issue("error", "relationships_not_list", "`relationships` must be a list"))
        relationships = []
    if not isinstance(itineraries, list):
        issues.append(Issue("error", "itineraries_not_list", "`itineraries` must be a list"))
        itineraries = []

    ids: list[str] = []
    missing_id = 0
    missing_name = 0
    missing_type = 0
    missing_summary = 0
    missing_summary_non_place = 0
    missing_summary_place = 0
    boilerplate_summary = 0
    missing_source = 0
    missing_source_non_place = 0
    missing_source_place = 0
    missing_location = 0
    missing_location_non_place = 0
    missing_location_place = 0
    legacy_coords_only = 0
    invalid_coordinates = 0
    out_of_bounds_coordinates = 0
    invalid_attributes = 0
    missing_place_id = 0
    missing_area_non_place = 0
    source_not_list = 0
    season_integrity_errors = 0
    low_confidence_count = 0
    empty_attrs_non_place = 0
    timestamp_inversions = 0
    summary_short = 0
    summary_long = 0
    has_images_non_place = 0
    name_too_short = 0
    name_too_long = 0
    invalid_source_urls = 0
    invalid_phone_format = 0
    invalid_website_urls = 0
    invalid_entity_ids = 0
    coords_without_address = 0
    summary_truncated = 0
    unknown_type_count = 0
    unknown_types_seen: set[str] = set()
    short_summary_examples: list[str] = []
    dangling_rel_targets: set[str] = set()
    source_url_reuse: Counter[str] = Counter()

    for index, entity in enumerate(entities):
        if not isinstance(entity, dict):
            issues.append(Issue("error", "entity_not_object", f"entities[{index}] must be an object"))
            continue
        entity_id = entity.get("id")
        if entity_id is None or entity_id == "":
            missing_id += 1
        else:
            ids.append(str(entity_id))
            eid_str = str(entity_id)
            if " " in eid_str or len(eid_str) > 200 or any(ord(c) < 32 for c in eid_str):
                invalid_entity_ids += 1
        if not entity.get("name"):
            missing_name += 1
        if not entity.get("type"):
            missing_type += 1
        entity_type = entity.get("type")
        if entity_type and entity_type not in VALID_ENTITY_TYPES:
            unknown_type_count += 1
            unknown_types_seen.add(str(entity_type))
        is_place = entity_type == "place"
        summary_val = entity.get("summary")
        if not summary_val:
            missing_summary += 1
            if is_place:
                missing_summary_place += 1
            else:
                missing_summary_non_place += 1
        elif BOILERPLATE_SUMMARY.search(str(summary_val)):
            boilerplate_summary += 1
        source = entity.get("source")
        if not source or (isinstance(source, list) and len(source) == 0):
            missing_source += 1
            if is_place:
                missing_source_place += 1
            else:
                missing_source_non_place += 1
        if source is not None and not isinstance(source, list):
            source_not_list += 1
        if not is_place and not entity.get("placeId"):
            missing_place_id += 1
        if not is_place and not entity.get("area"):
            missing_area_non_place += 1

        season = entity.get("season")
        if isinstance(season, dict):
            s_months = season.get("months", [])
            s_peak = season.get("peak", [])
            if isinstance(s_months, list) and isinstance(s_peak, list):
                if not all(isinstance(m, int) and 1 <= m <= 12 for m in s_months):
                    season_integrity_errors += 1
                elif s_peak and not set(s_peak).issubset(set(s_months)):
                    season_integrity_errors += 1
        elif season is not None and season != "":
            season_integrity_errors += 1

        confidence = entity.get("confidence")
        if isinstance(confidence, (int, float)) and confidence < 0.5:
            low_confidence_count += 1

        if not is_place:
            attrs = entity.get("attributes")
            if not attrs or (isinstance(attrs, dict) and len(attrs) == 0):
                empty_attrs_non_place += 1

        # DI-008: timestamp inversion
        updated_at = entity.get("updatedAt")
        created_at_val = entity.get("created_at")
        if isinstance(updated_at, str) and isinstance(created_at_val, str) and updated_at < created_at_val:
            timestamp_inversions += 1

        # DI-009: image coverage (non-place only)
        if not is_place:
            imgs = entity.get("images")
            if isinstance(imgs, list) and any(isinstance(i, str) and i.startswith("http") for i in imgs):
                has_images_non_place += 1

        # DI-010: summary quality tiers
        if isinstance(summary_val, str) and summary_val.strip():
            stripped = summary_val.strip()
            slen = len(stripped)
            if slen < 50:
                summary_short += 1
                if len(short_summary_examples) < 10:
                    short_summary_examples.append(f"{entity.get('id')} ({slen} chars)")
            elif slen > 500:
                summary_long += 1
            # DI-029: truncated summaries (end with "..." or "…")
            if stripped.endswith("...") or stripped.endswith("…"):
                summary_truncated += 1

        # DI-015: name length anomalies
        ename = entity.get("name")
        if isinstance(ename, str):
            elen = len(ename.strip())
            if 0 < elen < 2:
                name_too_short += 1
            elif elen > 100:
                name_too_long += 1

        # DI-019: source URL validation + DI-030: source URL reuse tracking
        if isinstance(source, list):
            for src_item in source:
                url_val = src_item.get("url") if isinstance(src_item, dict) else (src_item if isinstance(src_item, str) else None)
                if isinstance(url_val, str) and url_val.strip():
                    clean_url = url_val.strip()
                    parsed = urlparse(clean_url)
                    if parsed.scheme not in ("http", "https", "") or (parsed.scheme and not parsed.netloc):
                        invalid_source_urls += 1
                    else:
                        source_url_reuse[clean_url] += 1

        # DI-020: phone format validation
        attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        phone = attrs.get("phone") if isinstance(attrs, dict) else None
        if isinstance(phone, str) and phone.strip():
            cleaned = re.sub(r"[\s\-\.]", "", phone.strip())
            if not VN_PHONE.match(cleaned):
                invalid_phone_format += 1

        # DI-022: website URL validation
        website = attrs.get("website") if isinstance(attrs, dict) else None
        if isinstance(website, str) and website.strip():
            parsed_w = urlparse(website.strip())
            if parsed_w.scheme not in ("http", "https") or not parsed_w.netloc:
                invalid_website_urls += 1

        # DI-028: coordinates without address (hurts local SEO)
        if not is_place and entity.get("coordinates") and not attrs.get("address"):
            coords_without_address += 1

        if is_place:
            level = entity.get("level", "")
            name = entity.get("name", "")
            eid = str(entity_id or "")
            if name.startswith("Phường ") and level == "xa":
                issues.append(Issue("error", "level_name_mismatch",
                    f"{eid}: name='{name}' but level='xa' (should be 'phuong')"))
            if name.startswith("Xã ") and level == "phuong":
                issues.append(Issue("error", "level_name_mismatch",
                    f"{eid}: name='{name}' but level='phuong' (should be 'xa')"))
            if eid.startswith("p-") and level == "xa":
                issues.append(Issue("error", "level_id_mismatch",
                    f"{eid}: id prefix 'p-' but level='xa' (should be 'phuong')"))
            if eid.startswith("xa-") and level == "phuong":
                issues.append(Issue("error", "level_id_mismatch",
                    f"{eid}: id prefix 'xa-' but level='phuong' (should be 'xa')"))

        coords = entity.get("coordinates")
        legacy = entity.get("coords")
        if coords is None and legacy is not None:
            if normalized_coordinates(legacy):
                legacy_coords_only += 1
            else:
                invalid_coordinates += 1
        elif coords is not None and normalized_coordinates(coords) is None:
            invalid_coordinates += 1
        elif coords is None and legacy is None:
            missing_location += 1
            if is_place:
                missing_location_place += 1
            else:
                missing_location_non_place += 1
        elif normalized_coordinates(coords) and not in_mekong_bbox(normalized_coordinates(coords)):
            out_of_bounds_coordinates += 1

        attrs = entity.get("attributes")
        if attrs is not None and not isinstance(attrs, dict):
            invalid_attributes += 1

    xa_phuong_count = sum(
        1 for e in entities
        if isinstance(e, dict) and e.get("type") == "place"
        and e.get("level") in ("xa", "phuong")
        and e.get("parentId")
    )
    EXPECTED_XA_PHUONG = 124
    if xa_phuong_count != EXPECTED_XA_PHUONG:
        issues.append(Issue("warning", "xa_phuong_count",
            f"Expected {EXPECTED_XA_PHUONG} xã/phường, found {xa_phuong_count}"))

    id_counts = Counter(ids)
    duplicate_ids = {entity_id: count for entity_id, count in id_counts.items() if count > 1}
    id_set = set(ids)
    entity_by_id = {
        str(entity.get("id")): entity
        for entity in entities
        if isinstance(entity, dict) and entity.get("id")
    }

    if missing_id:
        issues.append(Issue("error", "missing_entity_id", f"{missing_id} entities are missing id"))
    if duplicate_ids:
        examples = ", ".join(list(duplicate_ids)[:5])
        issues.append(Issue("error", "duplicate_entity_id", f"{len(duplicate_ids)} duplicate entity ids: {examples}"))
    if missing_name:
        issues.append(Issue("error", "missing_entity_name", f"{missing_name} entities are missing name"))
    if missing_type:
        issues.append(Issue("error", "missing_entity_type", f"{missing_type} entities are missing type"))
    if unknown_type_count:
        examples = ", ".join(sorted(unknown_types_seen)[:10])
        issues.append(Issue("warning", "unknown_entity_type", f"{unknown_type_count} entities have unknown type: {examples}"))
    if invalid_coordinates:
        issues.append(Issue("error", "invalid_coordinates", f"{invalid_coordinates} entities have invalid coordinates/coords"))
    if out_of_bounds_coordinates:
        issues.append(Issue("error", "out_of_bounds_coordinates", f"{out_of_bounds_coordinates} entities have coordinates outside the Mekong bbox"))
    if invalid_attributes:
        issues.append(Issue("error", "invalid_attributes", f"{invalid_attributes} entities have non-object attributes"))
    if legacy_coords_only:
        issues.append(Issue("error", "legacy_coords_only", f"{legacy_coords_only} entities have coords but no canonical coordinates"))
    if source_not_list:
        issues.append(Issue("error", "source_not_list", f"{source_not_list} entities have source field that is not a list"))
    if season_integrity_errors:
        issues.append(Issue("error", "season_integrity", f"{season_integrity_errors} entities have invalid season data (bad months or peak not subset)"))
    if low_confidence_count:
        issues.append(Issue("warning", "low_confidence", f"{low_confidence_count} entities have confidence < 0.5"))
    if empty_attrs_non_place:
        issues.append(Issue("warning", "empty_attributes", f"{empty_attrs_non_place} non-place entities have empty attributes"))

    place_with_coords = sum(
        1 for e in entities
        if isinstance(e, dict) and e.get("type") == "place"
        and e.get("level") in ("xa", "phuong")
        and normalized_coordinates(e.get("coordinates")) is not None
    )
    place_xa_phuong = sum(
        1 for e in entities
        if isinstance(e, dict) and e.get("type") == "place"
        and e.get("level") in ("xa", "phuong")
    )
    place_coords_pct = round(100 * place_with_coords / max(place_xa_phuong, 1), 1)

    # Check place entities with level=None (data integrity gap)
    place_level_none = 0
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        if entity.get("type") == "place" and entity.get("level") is None:
            place_level_none += 1
    if place_level_none:
        issues.append(Issue("warning", "place_level_none",
            f"{place_level_none} place entities have level=None (should be xa/phuong/thi-tran/tp/huyen/tinh)"))

    broken_relationships = 0
    missing_relationship_fields = 0
    area_place_conflicts = 0
    produced_in_area_conflicts = 0
    produced_in_target_type_errors = 0  # produced_in should target place or craft_village
    produced_in_source_type_errors = 0  # produced_in source should be product/dish/drink
    far_near_relationships = 0
    near_missing_location = 0
    self_loop_relationships = 0  # DI-005: rel có source==target
    relationship_type_counts: Counter[str] = Counter()
    duplicate_relationships: Counter[tuple[str, str, str]] = Counter()
    relationship_fanout: Counter[str] = Counter()

    def effective_area(entity: dict[str, Any] | None) -> str | None:
        if not isinstance(entity, dict):
            return None
        area = entity.get("area")
        if area:
            return str(area)
        place_id = entity.get("placeId")
        place = entity_by_id.get(str(place_id)) if place_id else None
        if isinstance(place, dict) and place.get("area"):
            return str(place["area"])
        return None

    for entity in entities:
        if not isinstance(entity, dict) or entity.get("type") == "place":
            continue
        place_id = entity.get("placeId")
        if not place_id:
            continue
        place = entity_by_id.get(str(place_id))
        if not isinstance(place, dict):
            continue
        entity_area = entity.get("area")
        place_area = place.get("area")
        if entity_area and place_area and entity_area != place_area:
            area_place_conflicts += 1

    for index, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            issues.append(Issue("error", "relationship_not_object", f"relationships[{index}] must be an object"))
            continue
        src = rel_source(rel)
        dst = rel_target(rel)
        kind = rel_type(rel)
        if not src or not dst or not kind:
            missing_relationship_fields += 1
            continue
        src = str(src)
        dst = str(dst)
        kind = str(kind)
        if src == dst:  # DI-005: self-loop vô nghĩa
            self_loop_relationships += 1
            continue
        relationship_type_counts[kind] += 1
        duplicate_relationships[(src, dst, kind)] += 1
        # Quan hệ PHÂN-CẤP (located_in/part_of) là chứa-đựng cấu trúc, KHÔNG phải
        # fanout kiểu "liên quan/gần đây" mà ngưỡng 120 muốn chặn — một tỉnh chứa
        # ~124 xã/phường là hợp lệ. Chỉ tính fanout cho quan hệ phi-phân-cấp.
        if kind not in HIERARCHICAL_REL_TYPES:
            relationship_fanout[src] += 1
            relationship_fanout[dst] += 1
        if src not in id_set or dst not in id_set:
            broken_relationships += 1
            if src not in id_set:
                dangling_rel_targets.add(src)
            if dst not in id_set:
                dangling_rel_targets.add(dst)
            continue
        if kind == "near":
            src_coords = normalized_coordinates(entity_by_id[src].get("coordinates"))
            dst_coords = normalized_coordinates(entity_by_id[dst].get("coordinates"))
            if not src_coords or not dst_coords:
                near_missing_location += 1
                continue
            distance = haversine_km(src_coords, dst_coords)
            if distance is not None and distance > MAX_NEAR_DISTANCE_KM:
                far_near_relationships += 1
        elif kind == "produced_in":
            dst_entity = entity_by_id.get(dst)
            src_entity = entity_by_id.get(src)
            if isinstance(dst_entity, dict) and dst_entity.get("type") not in (
                "place", "craft_village", None
            ):
                produced_in_target_type_errors += 1
            if isinstance(src_entity, dict) and src_entity.get("type") not in (
                "product", "dish", "drink", "craft_village", None
            ):
                produced_in_source_type_errors += 1
            src_area = effective_area(src_entity)
            dst_area = effective_area(dst_entity)
            if src_area and dst_area and src_area != dst_area:
                produced_in_area_conflicts += 1

    unknown_rel_types = {t for t in relationship_type_counts if t not in KNOWN_REL_TYPES}
    duplicate_rel_count = sum(1 for count in duplicate_relationships.values() if count > 1)
    high_fanout_count = sum(1 for count in relationship_fanout.values() if count > MAX_DIRECT_RELATIONSHIPS)
    if missing_relationship_fields:
        issues.append(Issue("error", "missing_relationship_fields", f"{missing_relationship_fields} relationships miss source/target/type"))
    if broken_relationships:
        examples = ", ".join(sorted(dangling_rel_targets)[:5])
        issues.append(Issue("error", "broken_relationships", f"{broken_relationships} relationships reference {len(dangling_rel_targets)} missing entities: {examples}"))
    if area_place_conflicts:
        issues.append(Issue("error", "area_place_conflicts", f"{area_place_conflicts} non-place entities have area conflicting with their placeId area"))
    if near_missing_location:
        issues.append(Issue("error", "near_missing_location", f"{near_missing_location} near relationships have an endpoint without coordinates"))
    if far_near_relationships:
        issues.append(Issue("error", "far_near_relationships", f"{far_near_relationships} near relationships are farther than {MAX_NEAR_DISTANCE_KM:g} km"))
    if produced_in_area_conflicts:
        issues.append(Issue("error", "produced_in_area_conflicts", f"{produced_in_area_conflicts} produced_in relationships cross conflicting entity areas"))
    if produced_in_target_type_errors:
        issues.append(Issue("error", "produced_in_target_type", f"{produced_in_target_type_errors} produced_in relationships target an entity that is not place or craft_village"))
    if produced_in_source_type_errors:
        issues.append(Issue("error", "produced_in_source_type", f"{produced_in_source_type_errors} produced_in relationships have source that is not product/dish/drink/craft_village"))
    if self_loop_relationships:
        issues.append(Issue("error", "self_loop_relationships", f"{self_loop_relationships} relationships have source==target"))
    if unknown_rel_types:
        examples = ", ".join(sorted(unknown_rel_types)[:5])
        issues.append(Issue("warning", "unknown_rel_types", f"{len(unknown_rel_types)} unknown relationship types: {examples}"))
    # DI-005: itinerary stop trỏ entity không tồn tại (free-text stop không có id → bỏ qua)
    dangling_stops = 0
    for it in itineraries:
        if not isinstance(it, dict):
            continue
        for stop in (it.get("stops") or []):
            if not isinstance(stop, dict):
                continue
            ref = stop.get("entityId") or stop.get("id")
            if ref and str(ref) not in id_set:
                dangling_stops += 1
    if dangling_stops:
        issues.append(Issue("error", "dangling_itinerary_stops", f"{dangling_stops} itinerary stops reference missing entities"))
    # DI-016: itinerary stops sanity
    itinerary_empty_stops = 0
    itinerary_excessive_stops = 0
    for it in itineraries:
        if not isinstance(it, dict):
            continue
        stops = it.get("stops")
        if not isinstance(stops, list) or len(stops) == 0:
            itinerary_empty_stops += 1
        elif len(stops) > 20:
            itinerary_excessive_stops += 1
    # DI-006: near asymmetry — if A→B near exists, B→A should also exist
    near_edges: set[tuple[str, str]] = set()
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        if rel_type(rel) == "near":
            s, d = str(rel_source(rel) or ""), str(rel_target(rel) or "")
            if s and d:
                near_edges.add((s, d))
    near_asymmetric = sum(1 for s, d in near_edges if (d, s) not in near_edges)

    # DI-007: coordinate clustering — entities sharing exact same coordinates
    coord_buckets: dict[tuple[float, float], list[str]] = defaultdict(list)
    for entity in entities:
        if not isinstance(entity, dict) or not entity.get("id"):
            continue
        c = normalized_coordinates(entity.get("coordinates"))
        if c:
            coord_buckets[(c[0], c[1])].append(str(entity["id"]))
    coord_clusters = sum(1 for ids in coord_buckets.values() if len(ids) > 1)
    coord_clustered_entities = sum(len(ids) for ids in coord_buckets.values() if len(ids) > 1)

    # DI-012: itinerary-stop area mismatch
    itinerary_area_mismatches = 0
    for it in itineraries:
        if not isinstance(it, dict):
            continue
        it_area = it.get("area")
        if not it_area:
            continue
        for stop in (it.get("stops") or []):
            if not isinstance(stop, dict):
                continue
            ref = stop.get("entityId") or stop.get("id")
            if not ref:
                continue
            stop_entity = entity_by_id.get(str(ref))
            if not stop_entity:
                continue
            stop_area = effective_area(stop_entity)
            if stop_area and stop_area != it_area:
                itinerary_area_mismatches += 1

    # DI-013: relationship type singleton combos
    rel_type_triple_counts: Counter[tuple[str, str, str]] = Counter()
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        s, d, k = rel_source(rel), rel_target(rel), rel_type(rel)
        if not s or not d or not k:
            continue
        src_entity = entity_by_id.get(str(s))
        dst_entity = entity_by_id.get(str(d))
        src_type = src_entity.get("type", "?") if isinstance(src_entity, dict) else "?"
        dst_type = dst_entity.get("type", "?") if isinstance(dst_entity, dict) else "?"
        rel_type_triple_counts[(str(src_type), str(k), str(dst_type))] += 1
    rel_type_singletons = sum(1 for count in rel_type_triple_counts.values() if count == 1)

    if high_fanout_count:
        issues.append(Issue("error", "relationship_fanout", f"{high_fanout_count} entities have more than {MAX_DIRECT_RELATIONSHIPS} direct relationships"))
    if duplicate_rel_count:
        issues.append(Issue("warning", "duplicate_relationships", f"{duplicate_rel_count} duplicate relationship keys found"))
    if near_asymmetric:
        issues.append(Issue("warning", "near_asymmetric", f"{near_asymmetric} near relationships are one-way (A→B exists but B→A does not)"))
    if coord_clusters:
        issues.append(Issue("warning", "coordinate_clusters", f"{coord_clusters} coordinate clusters ({coord_clustered_entities} entities share exact same coordinates)"))
    if timestamp_inversions:
        issues.append(Issue("warning", "timestamp_inversions", f"{timestamp_inversions} entities have updatedAt before created_at"))
    if itinerary_area_mismatches:
        issues.append(Issue("warning", "itinerary_area_mismatch", f"{itinerary_area_mismatches} itinerary stops reference entities outside the itinerary's declared area"))
    if rel_type_singletons:
        issues.append(Issue("warning", "rel_type_singletons", f"{rel_type_singletons} relationship (src_type, rel, dst_type) combos appear only once"))
    if summary_short:
        issues.append(Issue("warning", "summary_short", f"{summary_short} entities have summary < 50 chars"))
    if summary_long:
        issues.append(Issue("warning", "summary_long", f"{summary_long} entities have summary > 500 chars"))
    if name_too_short:
        issues.append(Issue("warning", "name_too_short", f"{name_too_short} entities have name < 2 chars"))
    if name_too_long:
        issues.append(Issue("warning", "name_too_long", f"{name_too_long} entities have name > 100 chars"))
    if itinerary_empty_stops:
        issues.append(Issue("warning", "itinerary_empty_stops", f"{itinerary_empty_stops} itineraries have no stops"))
    if itinerary_excessive_stops:
        issues.append(Issue("warning", "itinerary_excessive_stops", f"{itinerary_excessive_stops} itineraries have > 20 stops"))
    if missing_summary_non_place:
        issues.append(Issue("warning", "missing_summary_non_place", f"{missing_summary_non_place} non-place entities are missing summary"))
    if boilerplate_summary:
        issues.append(Issue("error", "boilerplate_summary", f"{boilerplate_summary} entities have placeholder '404 / không đủ thông tin' summaries"))
    if missing_summary_place:
        issues.append(Issue("warning", "missing_summary_place", f"{missing_summary_place} place entities are missing summary"))
    if missing_source:
        issues.append(Issue("warning", "missing_source", f"{missing_source} entities are missing source ({missing_source_non_place} non-place, {missing_source_place} place)"))
    if missing_place_id:
        issues.append(Issue("warning", "missing_place_id", f"{missing_place_id} non-place entities are missing placeId"))
    if missing_location:
        issues.append(Issue("warning", "missing_location", f"{missing_location} entities have no coordinates or coords ({missing_location_non_place} non-place, {missing_location_place} place)"))
    if invalid_entity_ids:
        issues.append(Issue("warning", "invalid_entity_ids", f"{invalid_entity_ids} entity IDs contain spaces, control chars, or are excessively long"))
    if invalid_source_urls:
        issues.append(Issue("warning", "invalid_source_urls", f"{invalid_source_urls} source URLs have invalid format"))
    if invalid_phone_format:
        issues.append(Issue("warning", "invalid_phone_format", f"{invalid_phone_format} entities have phone not matching VN format (+84/0 + 9-10 digits)"))
    if invalid_website_urls:
        issues.append(Issue("warning", "invalid_website_urls", f"{invalid_website_urls} entities have invalid website URLs in attributes"))

    name_counts = Counter((e.get("name") or "").strip() for e in entities if isinstance(e, dict) and e.get("name"))
    duplicate_names = {name: count for name, count in name_counts.items() if count > 1}
    if duplicate_names:
        examples = ", ".join(list(duplicate_names)[:5])
        issues.append(Issue("warning", "duplicate_names", f"{len(duplicate_names)} duplicate display names: {examples}"))

    name_type_counts = Counter(
        ((e.get("name") or "").strip(), e.get("type"))
        for e in entities
        if isinstance(e, dict) and e.get("name") and e.get("type")
    )
    duplicate_name_type = {k: c for k, c in name_type_counts.items() if c > 1}
    if duplicate_name_type:
        examples = ", ".join(f"{n}({t})" for (n, t), _ in list(duplicate_name_type.items())[:5])
        issues.append(Issue("warning", "duplicate_name_type", f"{len(duplicate_name_type)} entities share same name+type: {examples}"))
    stats_dup_name_type = len(duplicate_name_type)

    data_js = data_path.with_name("data.js")
    data_js_status = "missing"
    if data_js.exists():
        text = data_js.read_text(encoding="utf-8", errors="replace")
        if "window.VL_DATA" in text or "globalThis.VL_DATA" in text:
            data_js_status = "window"
        elif "export const" in text:
            data_js_status = "module_export"
            issues.append(Issue("error", "data_js_not_legacy_script", "web/data.js uses module exports but web/index.html loads it as a plain script"))
        else:
            data_js_status = "unknown"
            issues.append(Issue("warning", "data_js_unknown_shape", "web/data.js shape is not recognized"))

    stats = {
        "entities": len(entities),
        "relationships": len(relationships),
        "itineraries": len(itineraries),
        "entity_types": dict(Counter(e.get("type") for e in entities if isinstance(e, dict)).most_common()),
        "relationship_types": dict(relationship_type_counts.most_common(10)),
        "missing_summary": missing_summary,
        "missing_summary_non_place": missing_summary_non_place,
        "boilerplate_summary": boilerplate_summary,
        "missing_summary_place": missing_summary_place,
        "missing_source": missing_source,
        "missing_source_non_place": missing_source_non_place,
        "missing_source_place": missing_source_place,
        "missing_place_id": missing_place_id,
        "missing_area_non_place": missing_area_non_place,
        "missing_location": missing_location,
        "missing_location_non_place": missing_location_non_place,
        "missing_location_place": missing_location_place,
        "legacy_coords_only": legacy_coords_only,
        "out_of_bounds_coordinates": out_of_bounds_coordinates,
        "area_place_conflicts": area_place_conflicts,
        "near_missing_location": near_missing_location,
        "far_near_relationships": far_near_relationships,
        "produced_in_area_conflicts": produced_in_area_conflicts,
        "produced_in_target_type_errors": produced_in_target_type_errors,
        "place_level_none": place_level_none,
        "relationship_fanout_over_limit": high_fanout_count,
        "broken_relationships": broken_relationships,
        "duplicate_names": len(duplicate_names),
        "source_not_list": source_not_list,
        "season_integrity_errors": season_integrity_errors,
        "low_confidence": low_confidence_count,
        "empty_attributes_non_place": empty_attrs_non_place,
        "place_coords_coverage_pct": place_coords_pct,
        "near_asymmetric": near_asymmetric,
        "coordinate_clusters": coord_clusters,
        "coordinate_clustered_entities": coord_clustered_entities,
        "timestamp_inversions": timestamp_inversions,
        "image_coverage_pct": round(100 * has_images_non_place / max(sum(1 for e in entities if isinstance(e, dict) and e.get("type") != "place"), 1), 1),
        "summary_short": summary_short,
        "summary_long": summary_long,
        "itinerary_area_mismatches": itinerary_area_mismatches,
        "rel_type_singletons": rel_type_singletons,
        "name_too_short": name_too_short,
        "name_too_long": name_too_long,
        "itinerary_empty_stops": itinerary_empty_stops,
        "itinerary_excessive_stops": itinerary_excessive_stops,
        "invalid_source_urls": invalid_source_urls,
        "invalid_phone_format": invalid_phone_format,
        "invalid_website_urls": invalid_website_urls,
        "invalid_entity_ids": invalid_entity_ids,
        "produced_in_source_type_errors": produced_in_source_type_errors,
        "duplicate_name_type": stats_dup_name_type,
        "unknown_rel_types": len(unknown_rel_types),
        "coords_without_address": coords_without_address,
        "summary_truncated": summary_truncated,
        "duplicate_source_urls": sum(1 for c in source_url_reuse.values() if c > 1),
        "data_js_status": data_js_status,
    }

    # DI-014: per-type SEO attribute coverage
    type_coverage: dict[str, dict[str, Any]] = {}
    for e in entities:
        if not isinstance(e, dict):
            continue
        etype = e.get("type")
        req = SEO_REQUIRED.get(str(etype)) if etype else None
        if not req:
            continue
        attrs = e.get("attributes") if isinstance(e.get("attributes"), dict) else {}
        if etype not in type_coverage:
            type_coverage[etype] = {"total": 0, "has_any_seo_attr": 0, "per_attr": {k: 0 for k in req}}
        type_coverage[etype]["total"] += 1
        if any(attrs.get(k) for k in req):
            type_coverage[etype]["has_any_seo_attr"] += 1
        for k in req:
            if attrs.get(k):
                type_coverage[etype]["per_attr"][k] += 1
    stats["seo_attr_coverage"] = type_coverage

    # DI-027: per-area entity counts
    area_counts: dict[str, int] = Counter()
    for e in entities:
        if not isinstance(e, dict) or e.get("type") == "place":
            continue
        ea = e.get("area")
        area_counts[ea if ea else "(none)"] += 1
    stats["entities_by_area"] = dict(area_counts.most_common())

    # DI-017: entity quality score distribution
    non_place = [e for e in entities if isinstance(e, dict) and e.get("type") != "place"]
    confidence_values = []
    for e in entities:
        if isinstance(e, dict) and e.get("type") != "place":
            c = e.get("confidence")
            if isinstance(c, (int, float)):
                confidence_values.append(float(c))
    if confidence_values:
        sorted_conf = sorted(confidence_values)
        mid = len(sorted_conf) // 2
        median = sorted_conf[mid] if len(sorted_conf) % 2 else round((sorted_conf[mid - 1] + sorted_conf[mid]) / 2, 3)
        stats["confidence_distribution"] = {
            "min": round(min(sorted_conf), 3),
            "max": round(max(sorted_conf), 3),
            "median": median,
            "count": len(sorted_conf),
        }

    if non_place:
        scores = [entity_quality_score(e) for e in non_place]
        stats["quality_score_avg"] = round(sum(scores) / len(scores), 1)
        stats["quality_score_distribution"] = {
            "critical_0_29": sum(1 for s in scores if s < 30),
            "needs_work_30_59": sum(1 for s in scores if 30 <= s < 60),
            "ok_60_79": sum(1 for s in scores if 60 <= s < 80),
            "good_80_100": sum(1 for s in scores if s >= 80),
        }
    else:
        stats["quality_score_avg"] = 0.0
        stats["quality_score_distribution"] = {
            "critical_0_29": 0, "needs_work_30_59": 0,
            "ok_60_79": 0, "good_80_100": 0,
        }

    # DI-018: graph connectivity
    stats["graph_connectivity"] = graph_connectivity(entities, relationships)

    # DI-021: orphan non-place entities (no relationship, no itinerary stop reference)
    referenced_ids: set[str] = set()
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        s = rel_source(rel)
        d = rel_target(rel)
        if s:
            referenced_ids.add(str(s))
        if d:
            referenced_ids.add(str(d))
    for it in itineraries:
        if not isinstance(it, dict):
            continue
        for stop in (it.get("stops") or []):
            if isinstance(stop, dict):
                ref = stop.get("entityId") or stop.get("id")
                if ref:
                    referenced_ids.add(str(ref))
    orphan_count = sum(
        1 for e in entities
        if isinstance(e, dict) and e.get("type") != "place" and e.get("id")
        and str(e["id"]) not in referenced_ids
    )
    stats["orphan_entities"] = orphan_count
    stats["unknown_entity_types"] = unknown_type_count
    stats["short_summary_examples"] = short_summary_examples
    stats["dangling_rel_entity_ids"] = sorted(dangling_rel_targets)[:20]
    if orphan_count:
        issues.append(Issue("warning", "orphan_entities",
            f"{orphan_count} non-place entities have no relationships or itinerary references"))

    return issues, stats


def print_report(issues: list[Issue], stats: dict[str, Any]) -> None:
    print("VinhLong360 data validation")
    print("===========================")
    for key in ["entities", "relationships", "itineraries", "legacy_coords_only", "broken_relationships", "data_js_status"]:
        print(f"{key}: {stats.get(key)}")
    print("\nEntity types:")
    for name, count in stats.get("entity_types", {}).items():
        print(f"  {name}: {count}")
    print("\nRelationship types:")
    for name, count in stats.get("relationship_types", {}).items():
        print(f"  {name}: {count}")

    print("\nData quality:")
    for key in [
        "missing_summary_non_place",
        "boilerplate_summary",
        "missing_summary_place",
        "missing_source_non_place",
        "missing_source_place",
        "missing_place_id",
        "missing_area_non_place",
        "missing_location_non_place",
        "missing_location_place",
        "out_of_bounds_coordinates",
        "area_place_conflicts",
        "near_missing_location",
        "far_near_relationships",
        "produced_in_area_conflicts",
        "produced_in_target_type_errors",
        "place_level_none",
        "relationship_fanout_over_limit",
        "duplicate_names",
        "source_not_list",
        "season_integrity_errors",
        "low_confidence",
        "empty_attributes_non_place",
        "place_coords_coverage_pct",
        "near_asymmetric",
        "coordinate_clusters",
        "coordinate_clustered_entities",
        "timestamp_inversions",
        "image_coverage_pct",
        "summary_short",
        "summary_long",
        "itinerary_area_mismatches",
        "rel_type_singletons",
        "name_too_short",
        "name_too_long",
        "itinerary_empty_stops",
        "itinerary_excessive_stops",
        "invalid_source_urls",
        "invalid_phone_format",
        "invalid_website_urls",
        "unknown_rel_types",
        "orphan_entities",
        "unknown_entity_types",
        "invalid_entity_ids",
        "produced_in_source_type_errors",
        "coords_without_address",
        "summary_truncated",
        "duplicate_source_urls",
    ]:
        print(f"  {key}: {stats.get(key)}")

    ss_examples = stats.get("short_summary_examples", [])
    if ss_examples:
        print(f"\nShort summary examples (top {len(ss_examples)}):")
        for ex in ss_examples:
            print(f"  {ex}")
    dangling_ids = stats.get("dangling_rel_entity_ids", [])
    if dangling_ids:
        print(f"\nDangling relationship entity IDs (top {len(dangling_ids)}):")
        for eid in dangling_ids:
            print(f"  {eid}")

    seo_cov = stats.get("seo_attr_coverage", {})
    if seo_cov:
        print("\nSEO attribute coverage:")
        for etype, info in sorted(seo_cov.items()):
            total = info["total"]
            has = info["has_any_seo_attr"]
            pct = round(100 * has / max(total, 1))
            per_attr = info.get("per_attr", {})
            attr_detail = " ".join(f"{k}={v}" for k, v in per_attr.items()) if per_attr else ""
            print(f"  {etype}: {has}/{total} ({pct}%) [{attr_detail}]")

    qs_avg = stats.get("quality_score_avg", 0)
    qs_dist = stats.get("quality_score_distribution", {})
    if qs_avg or qs_dist:
        print(f"\nEntity quality score: avg={qs_avg}")
        print(f"  critical (0-29): {qs_dist.get('critical_0_29', 0)}")
        print(f"  needs_work (30-59): {qs_dist.get('needs_work_30_59', 0)}")
        print(f"  ok (60-79): {qs_dist.get('ok_60_79', 0)}")
        print(f"  good (80-100): {qs_dist.get('good_80_100', 0)}")

    cd = stats.get("confidence_distribution")
    if cd:
        print(f"\nConfidence distribution: min={cd['min']}, max={cd['max']}, median={cd['median']}, n={cd['count']}")

    gc = stats.get("graph_connectivity", {})
    if gc:
        print(f"\nGraph connectivity:")
        print(f"  components: {gc.get('total_components', 0)}")
        print(f"  largest: {gc.get('largest_component', 0)}")
        print(f"  isolated: {gc.get('isolated_entities', 0)}")

    grouped: dict[str, list[Issue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.severity].append(issue)
    for severity in ["error", "warning"]:
        if not grouped.get(severity):
            continue
        print(f"\n{severity.upper()}S:")
        for issue in grouped[severity]:
            print(f"  [{issue.code}] {issue.message}")


def main() -> int:
    _configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to data.json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    parser.add_argument("--warnings-as-errors", action="store_true", help="Fail on warnings too")
    args = parser.parse_args()

    data = _load_json(args.data)
    issues, stats = validate(data, args.data)
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]

    if args.json:
        print(json.dumps({"stats": stats, "issues": [issue.__dict__ for issue in issues]}, ensure_ascii=False, indent=2))
    else:
        print_report(issues, stats)

    if errors or (args.warnings_as_errors and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
