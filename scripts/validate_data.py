#!/usr/bin/env python3
"""Validate the VinhLong360 static knowledge data contract."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
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

VN_PHONE = re.compile(r"^(\+84|0)\d{9,10}$|^1(800|900)\d{4,6}$|^11[345]$")

BOILERPLATE_SUMMARY = re.compile(
    r"không\s*(có\s*)?đủ thông tin|404|không tìm thấy thông tin|no information|not found",
    re.IGNORECASE,
)

BAD_SENTENCE_JOIN = re.compile(r"(?<=[a-zA-ZÀ-ỹ])\.(?=[a-zà-ỹ])")
SAFE_DOT_TOKEN = re.compile(
    r"\b(?:Co\.opmart|TP\.HCM|[\w-]+\.(?:vn|com(?:\.vn)?|net|org|edu|gov))\b",
    re.IGNORECASE,
)
TEXT_QUALITY_FIELDS = ("summary", "desc", "description")
MAX_REASONABLE_TEXT_LEN = 1500

def _normalize_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\sÀ-ỹ]", "", sentence.lower())).strip()

def has_adjacent_repeated_sentence(text: str) -> bool:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    previous = ""
    for part in parts:
        normalized = _normalize_sentence(part)
        if len(normalized) >= 20 and normalized == previous:
            return True
        previous = normalized
    return False

def has_bad_sentence_join(text: str) -> bool:
    masked = SAFE_DOT_TOKEN.sub(lambda m: m.group(0).replace(".", " "), text)
    return BAD_SENTENCE_JOIN.search(masked) is not None

def is_external_gateway(entity: dict[str, Any]) -> bool:
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    return bool(attrs.get("external_gateway"))

def image_url(value: Any) -> str:
    if isinstance(value, str) and value.startswith("http"):
        return value
    if isinstance(value, dict):
        url = value.get("url") or value.get("src") or value.get("contentUrl")
        if isinstance(url, str) and url.startswith("http"):
            return url
    return ""

def _image_credit_from_raw(raw_image: Any) -> dict[str, Any] | None:
    if not isinstance(raw_image, dict):
        return None
    direct = {
        "author": raw_image.get("author") or raw_image.get("credit"),
        "credit": raw_image.get("credit"),
        "license": raw_image.get("license"),
        "source": raw_image.get("source"),
        "source_url": raw_image.get("source_url") or raw_image.get("sourceUrl"),
    }
    if any(direct.values()):
        return {k: v for k, v in direct.items() if v}
    return None


def image_credit_for_url(entity: dict[str, Any], img_url: str, raw_image: Any = None) -> dict[str, Any]:
    from_raw = _image_credit_from_raw(raw_image)
    if from_raw is not None:
        return from_raw
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    credits = attrs.get("image_credits")
    if isinstance(credits, list):
        for item in credits:
            if isinstance(item, dict) and str(item.get("url") or "") == img_url:
                return item
    return {
        "author": attrs.get("image_author") or attrs.get("image_credit"),
        "credit": attrs.get("image_credit"),
        "license": attrs.get("image_license"),
        "source": attrs.get("image_source"),
        "source_url": attrs.get("image_source_url"),
    }

def has_approximate_coordinates(entity: dict[str, Any]) -> bool:
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    return bool(attrs.get("coords_approximate"))

def itinerary_declared_areas(itinerary: dict[str, Any]) -> set[str] | None:
    """Return allowed stop areas. None means an intentionally cross-region route."""
    declared: set[str] = set()
    raw_areas = itinerary.get("areas")
    if isinstance(raw_areas, list):
        declared.update(str(area) for area in raw_areas if area)
    elif isinstance(raw_areas, str) and raw_areas.strip():
        declared.update(part.strip() for part in raw_areas.split(",") if part.strip())

    area = itinerary.get("area")
    if area and area != "lien-vung":
        declared.add(str(area))
    elif area == "lien-vung" and not declared:
        return None

    return declared

def itinerary_stop_ref(stop: Any) -> str:
    if isinstance(stop, str):
        return stop
    if isinstance(stop, dict):
        return str(stop.get("entityId") or stop.get("entity_id") or stop.get("id") or "")
    return ""

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


def _quality_summary_penalty(summary_val: Any) -> int:
    if not summary_val:
        return 20
    if isinstance(summary_val, str):
        s = summary_val.strip()
        if BOILERPLATE_SUMMARY.search(s):
            return 20
        if len(s) < 50:
            return 5
        if len(s) > 500:
            return 3
    return 0


def _quality_seo_attr_penalty(entity: dict[str, Any]) -> int:
    etype = str(entity.get("type")) if entity.get("type") else None
    req = SEO_REQUIRED.get(etype) if etype else None
    if req:
        attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        if not any(attrs.get(k) for k in req):
            return 10
    return 0


def _quality_coords_penalty(
    entity: dict[str, Any], is_itinerary: bool, external_gateway: bool
) -> int:
    if not is_itinerary and not external_gateway and not entity.get("coordinates") and not entity.get("coords"):
        return 15
    return 0


def _quality_placeid_area_penalty(
    entity: dict[str, Any], is_place: bool, is_itinerary: bool, external_gateway: bool
) -> int:
    if is_place or is_itinerary or external_gateway:
        return 0
    penalty = 0
    if not entity.get("placeId"):
        penalty += 10
    if not entity.get("area"):
        penalty += 5
    return penalty


def _quality_location_penalty(
    entity: dict[str, Any], is_place: bool, is_itinerary: bool, external_gateway: bool
) -> int:
    return (
        _quality_coords_penalty(entity, is_itinerary, external_gateway)
        + _quality_placeid_area_penalty(entity, is_place, is_itinerary, external_gateway)
    )


def _quality_source_image_penalty(entity: dict[str, Any]) -> int:
    penalty = 0
    source = entity.get("source")
    if not source or (isinstance(source, list) and len(source) == 0):
        penalty += 10
    imgs = entity.get("images")
    if not isinstance(imgs, list) or not any(isinstance(i, str) and i.startswith("http") for i in imgs):
        penalty += 10
    return penalty


def _quality_meta_penalty(entity: dict[str, Any]) -> int:
    penalty = 0
    confidence = entity.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.5:
        penalty += 5
    updated_at = entity.get("updatedAt")
    created_at_val = entity.get("created_at")
    if isinstance(updated_at, str) and isinstance(created_at_val, str) and updated_at < created_at_val:
        penalty += 2
    return penalty


def _quality_field_penalties(
    entity: dict[str, Any], is_place: bool, is_itinerary: bool, external_gateway: bool
) -> int:
    return (
        _quality_location_penalty(entity, is_place, is_itinerary, external_gateway)
        + _quality_source_image_penalty(entity)
        + _quality_meta_penalty(entity)
    )


def entity_quality_score(entity: dict[str, Any]) -> int:
    """Compute a 0-100 quality score for a single entity."""
    score = 100
    etype_raw = entity.get("type")
    is_place = etype_raw == "place"
    is_itinerary = etype_raw == "itinerary"
    external_gateway = is_external_gateway(entity)

    score -= _quality_summary_penalty(entity.get("summary"))
    score -= _quality_field_penalties(entity, is_place, is_itinerary, external_gateway)
    score -= _quality_seo_attr_penalty(entity)

    return max(0, score)


def _graph_adjacency(id_set: set[str], relationships: list[Any]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {eid: set() for eid in id_set}
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        src = str(rel_source(rel) or "")
        dst = str(rel_target(rel) or "")
        if src in id_set and dst in id_set and src != dst:
            adj[src].add(dst)
            adj[dst].add(src)
    return adj


def _graph_component_size(start: str, adj: dict[str, set[str]], visited: set[str]) -> int:
    size = 0
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        size += 1
        stack.extend(adj[node] - visited)
    return size


def graph_connectivity(entities: list[Any], relationships: list[Any]) -> dict[str, Any]:
    """Find disconnected subgraphs in the entity-relationship graph."""
    id_set: set[str] = set()
    for e in entities:
        if isinstance(e, dict) and e.get("id"):
            id_set.add(str(e["id"]))

    adj = _graph_adjacency(id_set, relationships)

    visited: set[str] = set()
    components: list[int] = []

    for start in id_set:
        if start in visited:
            continue
        components.append(_graph_component_size(start, adj, visited))

    components.sort(reverse=True)
    return {
        "total_components": len(components),
        "largest_component": components[0] if components else 0,
        "isolated_entities": sum(1 for c in components if c == 1),
        "component_sizes": components[:10],
    }


@dataclass
class _EntityStats:
    missing_id: int = 0
    missing_name: int = 0
    missing_type: int = 0
    missing_summary: int = 0
    missing_summary_non_place: int = 0
    missing_summary_place: int = 0
    boilerplate_summary: int = 0
    missing_source: int = 0
    missing_source_non_place: int = 0
    missing_source_place: int = 0
    missing_location: int = 0
    missing_location_non_place: int = 0
    missing_location_place: int = 0
    legacy_coords_only: int = 0
    invalid_coordinates: int = 0
    out_of_bounds_coordinates: int = 0
    invalid_attributes: int = 0
    missing_place_id: int = 0
    missing_area_non_place: int = 0
    source_not_list: int = 0
    season_integrity_errors: int = 0
    low_confidence_count: int = 0
    empty_attrs_non_place: int = 0
    timestamp_inversions: int = 0
    summary_short: int = 0
    summary_long: int = 0
    text_repeated_sentence: int = 0
    text_bad_sentence_join: int = 0
    text_excessive_length: int = 0
    has_images_non_place: int = 0
    image_total: int = 0
    image_missing_credit: int = 0
    image_missing_license: int = 0
    image_missing_source: int = 0
    name_too_short: int = 0
    name_too_long: int = 0
    invalid_source_urls: int = 0
    invalid_phone_format: int = 0
    invalid_website_urls: int = 0
    invalid_entity_ids: int = 0
    coords_without_address: int = 0
    summary_truncated: int = 0
    unknown_type_count: int = 0
    unknown_types_seen: set[str] = field(default_factory=set)
    short_summary_examples: list[str] = field(default_factory=list)
    source_url_reuse: Counter[str] = field(default_factory=Counter)


def _check_entity_identity(entity: dict[str, Any], entity_id: Any, acc: _EntityStats) -> None:
    if entity_id is None or entity_id == "":
        acc.missing_id += 1
    else:
        eid_str = str(entity_id)
        if " " in eid_str or len(eid_str) > 200 or any(ord(c) < 32 for c in eid_str):
            acc.invalid_entity_ids += 1
    if not entity.get("name"):
        acc.missing_name += 1
    if not entity.get("type"):
        acc.missing_type += 1
    entity_type = entity.get("type")
    if entity_type and entity_type not in VALID_ENTITY_TYPES:
        acc.unknown_type_count += 1
        acc.unknown_types_seen.add(str(entity_type))


def _check_entity_summary_presence(entity: dict[str, Any], is_place: bool, acc: _EntityStats) -> None:
    summary_val = entity.get("summary")
    if not summary_val:
        acc.missing_summary += 1
        if is_place:
            acc.missing_summary_place += 1
        else:
            acc.missing_summary_non_place += 1
    elif BOILERPLATE_SUMMARY.search(str(summary_val)):
        acc.boilerplate_summary += 1


def _check_entity_source_presence(entity: dict[str, Any], is_place: bool, acc: _EntityStats) -> None:
    source = entity.get("source")
    if not source or (isinstance(source, list) and len(source) == 0):
        acc.missing_source += 1
        if is_place:
            acc.missing_source_place += 1
        else:
            acc.missing_source_non_place += 1
    if source is not None and not isinstance(source, list):
        acc.source_not_list += 1


def _check_entity_placeid_area(
    entity: dict[str, Any], is_place: bool, is_itinerary: bool, external_gateway: bool, acc: _EntityStats
) -> None:
    if not is_place and not is_itinerary and not external_gateway and not entity.get("placeId"):
        acc.missing_place_id += 1
    if not is_place and not is_itinerary and not external_gateway and not entity.get("area"):
        acc.missing_area_non_place += 1


def _check_entity_summary_source(
    entity: dict[str, Any], is_place: bool, is_itinerary: bool, external_gateway: bool, acc: _EntityStats
) -> None:
    _check_entity_summary_presence(entity, is_place, acc)
    _check_entity_source_presence(entity, is_place, acc)
    _check_entity_placeid_area(entity, is_place, is_itinerary, external_gateway, acc)


def _check_entity_season(entity: dict[str, Any], acc: _EntityStats) -> None:
    season = entity.get("season")
    if isinstance(season, dict):
        s_months = season.get("months", [])
        s_peak = season.get("peak", [])
        if isinstance(s_months, list) and isinstance(s_peak, list):
            if not all(isinstance(m, int) and 1 <= m <= 12 for m in s_months):
                acc.season_integrity_errors += 1
            elif s_peak and not set(s_peak).issubset(set(s_months)):
                acc.season_integrity_errors += 1
    elif season is not None and season != "":
        acc.season_integrity_errors += 1


def _check_entity_confidence_attrs_ts(entity: dict[str, Any], is_place: bool, acc: _EntityStats) -> None:
    confidence = entity.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.5:
        acc.low_confidence_count += 1

    if not is_place:
        attrs = entity.get("attributes")
        if not attrs or (isinstance(attrs, dict) and len(attrs) == 0):
            acc.empty_attrs_non_place += 1

    # DI-008: timestamp inversion
    updated_at = entity.get("updatedAt")
    created_at_val = entity.get("created_at")
    if isinstance(updated_at, str) and isinstance(created_at_val, str) and updated_at < created_at_val:
        acc.timestamp_inversions += 1


def _check_entity_season_confidence_attrs(entity: dict[str, Any], is_place: bool, acc: _EntityStats) -> None:
    _check_entity_season(entity, acc)
    _check_entity_confidence_attrs_ts(entity, is_place, acc)


def _check_image_credit(entity: dict[str, Any], img_url: str, raw_img: Any, acc: _EntityStats) -> None:
    acc.image_total += 1
    credit_meta = image_credit_for_url(entity, img_url, raw_img)
    credit = credit_meta.get("author") or credit_meta.get("credit")
    license_value = credit_meta.get("license")
    source_value = credit_meta.get("source_url") or credit_meta.get("source")
    if not (isinstance(credit, str) and credit.strip()):
        acc.image_missing_credit += 1
    if not (isinstance(license_value, str) and license_value.strip()):
        acc.image_missing_license += 1
    if not (isinstance(source_value, str) and source_value.strip()):
        acc.image_missing_source += 1


def _check_entity_images(entity: dict[str, Any], is_place: bool, acc: _EntityStats) -> None:
    # DI-009: image coverage (non-place only)
    valid_images: list[tuple[str, Any]] = []
    imgs = entity.get("images")
    if isinstance(imgs, list):
        for raw_img in imgs:
            url = image_url(raw_img)
            if url:
                valid_images.append((url, raw_img))
    if not is_place:
        if valid_images:
            acc.has_images_non_place += 1
    for img_url, raw_img in valid_images:
        _check_image_credit(entity, img_url, raw_img, acc)


def _check_entity_summary_tiers(entity: dict[str, Any], acc: _EntityStats) -> None:
    # DI-010: summary quality tiers
    summary_val = entity.get("summary")
    if isinstance(summary_val, str) and summary_val.strip():
        stripped = summary_val.strip()
        slen = len(stripped)
        if slen < 50:
            acc.summary_short += 1
            if len(acc.short_summary_examples) < 10:
                acc.short_summary_examples.append(f"{entity.get('id')} ({slen} chars)")
        elif slen > 500:
            acc.summary_long += 1
        # DI-029: truncated summaries (end with "..." or "…")
        if stripped.endswith("...") or stripped.endswith("…"):
            acc.summary_truncated += 1


def _check_entity_text_quality(entity: dict[str, Any], acc: _EntityStats) -> None:
    text_values = [
        str(entity.get(field)).strip()
        for field in TEXT_QUALITY_FIELDS
        if isinstance(entity.get(field), str) and str(entity.get(field)).strip()
    ]
    if any(len(text) > MAX_REASONABLE_TEXT_LEN for text in text_values):
        acc.text_excessive_length += 1
    if any(has_bad_sentence_join(text) for text in text_values):
        acc.text_bad_sentence_join += 1
    if any(has_adjacent_repeated_sentence(text) for text in text_values):
        acc.text_repeated_sentence += 1


def _check_entity_name_length(entity: dict[str, Any], acc: _EntityStats) -> None:
    # DI-015: name length anomalies
    ename = entity.get("name")
    if isinstance(ename, str):
        elen = len(ename.strip())
        if 0 < elen < 2:
            acc.name_too_short += 1
        elif elen > 100:
            acc.name_too_long += 1


def _check_entity_source_urls(entity: dict[str, Any], acc: _EntityStats) -> None:
    # DI-019: source URL validation + DI-030: source URL reuse tracking
    source = entity.get("source")
    if isinstance(source, list):
        for src_item in source:
            url_val = src_item.get("url") if isinstance(src_item, dict) else (src_item if isinstance(src_item, str) else None)
            if isinstance(url_val, str) and url_val.strip():
                clean_url = url_val.strip()
                parsed = urlparse(clean_url)
                if parsed.scheme not in ("http", "https", "") or (parsed.scheme and not parsed.netloc):
                    acc.invalid_source_urls += 1
                else:
                    acc.source_url_reuse[clean_url] += 1


def _check_entity_phone(attrs: dict[str, Any], acc: _EntityStats) -> None:
    # DI-020: phone format validation
    phone = attrs.get("phone") if isinstance(attrs, dict) else None
    if isinstance(phone, str) and phone.strip():
        cleaned = re.sub(r"[\s\-\.]", "", phone.strip())
        if not VN_PHONE.match(cleaned):
            acc.invalid_phone_format += 1


def _check_entity_website(attrs: dict[str, Any], acc: _EntityStats) -> None:
    # DI-022: website URL validation
    website = attrs.get("website") if isinstance(attrs, dict) else None
    if isinstance(website, str) and website.strip():
        parsed_w = urlparse(website.strip())
        if parsed_w.scheme not in ("http", "https") or not parsed_w.netloc:
            acc.invalid_website_urls += 1


def _check_entity_contact(entity: dict[str, Any], is_place: bool, acc: _EntityStats) -> None:
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    _check_entity_phone(attrs, acc)
    _check_entity_website(attrs, acc)

    # DI-028: coordinates without address (hurts local SEO)
    if not is_place and entity.get("coordinates") and not attrs.get("address"):
        acc.coords_without_address += 1


def _check_place_level(entity: dict[str, Any], entity_id: Any, issues: list[Issue]) -> None:
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


def _count_missing_location(is_place: bool, acc: _EntityStats) -> None:
    acc.missing_location += 1
    if is_place:
        acc.missing_location_place += 1
    else:
        acc.missing_location_non_place += 1


def _check_coord_bounds(coords: Any, acc: _EntityStats) -> None:
    if normalized_coordinates(coords) and not in_mekong_bbox(normalized_coordinates(coords)):
        acc.out_of_bounds_coordinates += 1


def _check_entity_coordinates(entity: dict[str, Any], is_place: bool, is_itinerary: bool, acc: _EntityStats) -> None:
    coords = entity.get("coordinates")
    legacy = entity.get("coords")
    if coords is None and legacy is not None:
        if normalized_coordinates(legacy):
            acc.legacy_coords_only += 1
        else:
            acc.invalid_coordinates += 1
    elif coords is not None and normalized_coordinates(coords) is None:
        acc.invalid_coordinates += 1
    elif coords is None and legacy is None and not is_itinerary:
        _count_missing_location(is_place, acc)
    else:
        _check_coord_bounds(coords, acc)

    attrs = entity.get("attributes")
    if attrs is not None and not isinstance(attrs, dict):
        acc.invalid_attributes += 1


def _scan_entities(entities: list[Any], issues: list[Issue], ids: list[str]) -> _EntityStats:
    acc = _EntityStats()
    for index, entity in enumerate(entities):
        if not isinstance(entity, dict):
            issues.append(Issue("error", "entity_not_object", f"entities[{index}] must be an object"))
            continue
        entity_id = entity.get("id")
        if not (entity_id is None or entity_id == ""):
            ids.append(str(entity_id))
        entity_type = entity.get("type")
        is_place = entity_type == "place"
        is_itinerary = entity_type == "itinerary"
        external_gateway = is_external_gateway(entity)

        _check_entity_identity(entity, entity_id, acc)
        _check_entity_summary_source(entity, is_place, is_itinerary, external_gateway, acc)
        _check_entity_season_confidence_attrs(entity, is_place, acc)
        _check_entity_images(entity, is_place, acc)
        _check_entity_summary_tiers(entity, acc)
        _check_entity_text_quality(entity, acc)
        _check_entity_name_length(entity, acc)
        _check_entity_source_urls(entity, acc)
        _check_entity_contact(entity, is_place, acc)
        if is_place:
            _check_place_level(entity, entity_id, issues)
        _check_entity_coordinates(entity, is_place, is_itinerary, acc)
    return acc


def _effective_area(entity: dict[str, Any] | None, entity_by_id: dict[str, Any]) -> str | None:
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


@dataclass
class _RelStats:
    broken_relationships: int = 0
    missing_relationship_fields: int = 0
    area_place_conflicts: int = 0
    produced_in_area_conflicts: int = 0
    produced_in_target_type_errors: int = 0
    produced_in_source_type_errors: int = 0
    far_near_relationships: int = 0
    near_missing_location: int = 0
    self_loop_relationships: int = 0
    relationship_type_counts: Counter[str] = field(default_factory=Counter)
    duplicate_relationships: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    relationship_fanout: Counter[str] = field(default_factory=Counter)


def _count_area_place_conflicts(entities: list[Any], entity_by_id: dict[str, Any], acc: _RelStats) -> None:
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
            acc.area_place_conflicts += 1


def _check_near_rel(src: str, dst: str, entity_by_id: dict[str, Any], acc: _RelStats) -> None:
    src_coords = normalized_coordinates(entity_by_id[src].get("coordinates"))
    dst_coords = normalized_coordinates(entity_by_id[dst].get("coordinates"))
    if not src_coords or not dst_coords:
        acc.near_missing_location += 1
        return
    distance = haversine_km(src_coords, dst_coords)
    if distance is not None and distance > MAX_NEAR_DISTANCE_KM:
        acc.far_near_relationships += 1


def _check_produced_in_rel(src: str, dst: str, entity_by_id: dict[str, Any], acc: _RelStats) -> None:
    dst_entity = entity_by_id.get(dst)
    src_entity = entity_by_id.get(src)
    if isinstance(dst_entity, dict) and dst_entity.get("type") not in (
        "place", "craft_village", None
    ):
        acc.produced_in_target_type_errors += 1
    if isinstance(src_entity, dict) and src_entity.get("type") not in (
        "product", "dish", "drink", "craft_village", None
    ):
        acc.produced_in_source_type_errors += 1
    src_area = _effective_area(src_entity, entity_by_id)
    dst_area = _effective_area(dst_entity, entity_by_id)
    if src_area and dst_area and src_area != dst_area:
        acc.produced_in_area_conflicts += 1


def _scan_one_relationship(
    rel: dict[str, Any], entity_by_id: dict[str, Any], id_set: set[str],
    dangling_rel_targets: set[str], acc: _RelStats,
) -> None:
    src = rel_source(rel)
    dst = rel_target(rel)
    kind = rel_type(rel)
    if not src or not dst or not kind:
        acc.missing_relationship_fields += 1
        return
    src = str(src)
    dst = str(dst)
    kind = str(kind)
    if src == dst:  # DI-005: self-loop vô nghĩa
        acc.self_loop_relationships += 1
        return
    acc.relationship_type_counts[kind] += 1
    acc.duplicate_relationships[(src, dst, kind)] += 1
    # Quan hệ PHÂN-CẤP (located_in/part_of) là chứa-đựng cấu trúc, KHÔNG phải
    # fanout kiểu "liên quan/gần đây" mà ngưỡng 120 muốn chặn — một tỉnh chứa
    # ~124 xã/phường là hợp lệ. Chỉ tính fanout cho quan hệ phi-phân-cấp.
    if kind not in HIERARCHICAL_REL_TYPES:
        acc.relationship_fanout[src] += 1
        acc.relationship_fanout[dst] += 1
    if src not in id_set or dst not in id_set:
        acc.broken_relationships += 1
        if src not in id_set:
            dangling_rel_targets.add(src)
        if dst not in id_set:
            dangling_rel_targets.add(dst)
        return
    if kind == "near":
        _check_near_rel(src, dst, entity_by_id, acc)
    elif kind == "produced_in":
        _check_produced_in_rel(src, dst, entity_by_id, acc)


def _scan_relationships(
    relationships: list[Any], entities: list[Any], entity_by_id: dict[str, Any],
    id_set: set[str], issues: list[Issue], dangling_rel_targets: set[str],
) -> _RelStats:
    acc = _RelStats()
    _count_area_place_conflicts(entities, entity_by_id, acc)
    for index, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            issues.append(Issue("error", "relationship_not_object", f"relationships[{index}] must be an object"))
            continue
        _scan_one_relationship(rel, entity_by_id, id_set, dangling_rel_targets, acc)
    return acc


def _count_dangling_stops(itineraries: list[Any], id_set: set[str]) -> int:
    dangling_stops = 0
    for it in itineraries:
        if not isinstance(it, dict):
            continue
        for stop in (it.get("stops") or []):
            ref = itinerary_stop_ref(stop)
            if ref and str(ref) not in id_set:
                dangling_stops += 1
    return dangling_stops


def _count_itinerary_stop_sanity(itineraries: list[Any]) -> tuple[int, int]:
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
    return itinerary_empty_stops, itinerary_excessive_stops


def _count_near_edges(relationships: list[Any]) -> tuple[int, int]:
    near_edges: set[tuple[str, str]] = set()
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        if rel_type(rel) == "near":
            s, d = str(rel_source(rel) or ""), str(rel_target(rel) or "")
            if s and d:
                near_edges.add((s, d))
    near_one_way_edges = sum(1 for s, d in near_edges if (d, s) not in near_edges)
    near_reciprocal_pairs = sum(1 for s, d in near_edges if s < d and (d, s) in near_edges)
    return near_one_way_edges, near_reciprocal_pairs


def _build_coord_buckets(entities: list[Any]) -> dict[tuple[float, float], list[tuple[str, bool]]]:
    coord_buckets: dict[tuple[float, float], list[tuple[str, bool]]] = defaultdict(list)
    for entity in entities:
        if not isinstance(entity, dict) or not entity.get("id"):
            continue
        c = normalized_coordinates(entity.get("coordinates"))
        if c:
            coord_buckets[(c[0], c[1])].append((str(entity["id"]), has_approximate_coordinates(entity)))
    return coord_buckets


def _count_coord_clusters_precise(
    coord_buckets: dict[tuple[float, float], list[tuple[str, bool]]]
) -> tuple[int, int]:
    coord_clusters_precise = sum(1 for rows in coord_buckets.values() if sum(1 for _id, is_approx in rows if not is_approx) > 1)
    coord_clustered_entities_precise = sum(
        sum(1 for _id, is_approx in rows if not is_approx)
        for rows in coord_buckets.values()
        if sum(1 for _id, is_approx in rows if not is_approx) > 1
    )
    return coord_clusters_precise, coord_clustered_entities_precise


def _count_coord_clusters(entities: list[Any]) -> tuple[int, int, int, int, int, int]:
    coord_buckets = _build_coord_buckets(entities)
    coord_clusters = sum(1 for rows in coord_buckets.values() if len(rows) > 1)
    coord_clustered_entities = sum(len(rows) for rows in coord_buckets.values() if len(rows) > 1)
    coord_clusters_approximate = sum(1 for rows in coord_buckets.values() if len(rows) > 1 and all(is_approx for _id, is_approx in rows))
    coord_clustered_entities_approximate = sum(len(rows) for rows in coord_buckets.values() if len(rows) > 1 and all(is_approx for _id, is_approx in rows))
    coord_clusters_precise, coord_clustered_entities_precise = _count_coord_clusters_precise(coord_buckets)
    return (coord_clusters, coord_clustered_entities, coord_clusters_approximate,
            coord_clustered_entities_approximate, coord_clusters_precise,
            coord_clustered_entities_precise)


def _count_itinerary_area_mismatches(itineraries: list[Any], entity_by_id: dict[str, Any]) -> int:
    itinerary_area_mismatches = 0
    for it in itineraries:
        if not isinstance(it, dict):
            continue
        declared_areas = itinerary_declared_areas(it)
        if declared_areas == set():
            continue
        for stop in (it.get("stops") or []):
            ref = itinerary_stop_ref(stop)
            if not ref:
                continue
            stop_entity = entity_by_id.get(str(ref))
            if not stop_entity:
                continue
            stop_area = _effective_area(stop_entity, entity_by_id)
            if stop_area and declared_areas is not None and stop_area not in declared_areas:
                itinerary_area_mismatches += 1
    return itinerary_area_mismatches


def _count_rel_type_singletons(relationships: list[Any], entity_by_id: dict[str, Any]) -> int:
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
    return sum(1 for count in rel_type_triple_counts.values() if count == 1)


def _emit_entity_issues_a(acc: _EntityStats, duplicate_ids: dict[str, int], issues: list[Issue]) -> None:
    if acc.missing_id:
        issues.append(Issue("error", "missing_entity_id", f"{acc.missing_id} entities are missing id"))
    if duplicate_ids:
        examples = ", ".join(list(duplicate_ids)[:5])
        issues.append(Issue("error", "duplicate_entity_id", f"{len(duplicate_ids)} duplicate entity ids: {examples}"))
    if acc.missing_name:
        issues.append(Issue("error", "missing_entity_name", f"{acc.missing_name} entities are missing name"))
    if acc.missing_type:
        issues.append(Issue("error", "missing_entity_type", f"{acc.missing_type} entities are missing type"))
    if acc.unknown_type_count:
        examples = ", ".join(sorted(acc.unknown_types_seen)[:10])
        issues.append(Issue("warning", "unknown_entity_type", f"{acc.unknown_type_count} entities have unknown type: {examples}"))
    if acc.invalid_coordinates:
        issues.append(Issue("error", "invalid_coordinates", f"{acc.invalid_coordinates} entities have invalid coordinates/coords"))
    if acc.out_of_bounds_coordinates:
        issues.append(Issue("error", "out_of_bounds_coordinates", f"{acc.out_of_bounds_coordinates} entities have coordinates outside the Mekong bbox"))


def _emit_entity_issues_b(acc: _EntityStats, issues: list[Issue]) -> None:
    if acc.invalid_attributes:
        issues.append(Issue("error", "invalid_attributes", f"{acc.invalid_attributes} entities have non-object attributes"))
    if acc.legacy_coords_only:
        issues.append(Issue("error", "legacy_coords_only", f"{acc.legacy_coords_only} entities have coords but no canonical coordinates"))
    if acc.source_not_list:
        issues.append(Issue("error", "source_not_list", f"{acc.source_not_list} entities have source field that is not a list"))
    if acc.season_integrity_errors:
        issues.append(Issue("error", "season_integrity", f"{acc.season_integrity_errors} entities have invalid season data (bad months or peak not subset)"))
    if acc.low_confidence_count:
        issues.append(Issue("warning", "low_confidence", f"{acc.low_confidence_count} entities have confidence < 0.5"))
    if acc.empty_attrs_non_place:
        issues.append(Issue("warning", "empty_attributes", f"{acc.empty_attrs_non_place} non-place entities have empty attributes"))


def _emit_entity_issues(acc: _EntityStats, duplicate_ids: dict[str, int], issues: list[Issue]) -> None:
    _emit_entity_issues_a(acc, duplicate_ids, issues)
    _emit_entity_issues_b(acc, issues)


def _emit_relationship_issues(
    rel_acc: _RelStats, dangling_rel_targets: set[str], unknown_rel_types: set[str], issues: list[Issue]
) -> None:
    if rel_acc.missing_relationship_fields:
        issues.append(Issue("error", "missing_relationship_fields", f"{rel_acc.missing_relationship_fields} relationships miss source/target/type"))
    if rel_acc.broken_relationships:
        examples = ", ".join(sorted(dangling_rel_targets)[:5])
        issues.append(Issue("error", "broken_relationships", f"{rel_acc.broken_relationships} relationships reference {len(dangling_rel_targets)} missing entities: {examples}"))
    if rel_acc.area_place_conflicts:
        issues.append(Issue("error", "area_place_conflicts", f"{rel_acc.area_place_conflicts} non-place entities have area conflicting with their placeId area"))
    if rel_acc.near_missing_location:
        issues.append(Issue("error", "near_missing_location", f"{rel_acc.near_missing_location} near relationships have an endpoint without coordinates"))
    if rel_acc.far_near_relationships:
        issues.append(Issue("error", "far_near_relationships", f"{rel_acc.far_near_relationships} near relationships are farther than {MAX_NEAR_DISTANCE_KM:g} km"))
    if rel_acc.produced_in_area_conflicts:
        issues.append(Issue("error", "produced_in_area_conflicts", f"{rel_acc.produced_in_area_conflicts} produced_in relationships cross conflicting entity areas"))
    if rel_acc.produced_in_target_type_errors:
        issues.append(Issue("error", "produced_in_target_type", f"{rel_acc.produced_in_target_type_errors} produced_in relationships target an entity that is not place or craft_village"))
    if rel_acc.produced_in_source_type_errors:
        issues.append(Issue("error", "produced_in_source_type", f"{rel_acc.produced_in_source_type_errors} produced_in relationships have source that is not product/dish/drink/craft_village"))
    if rel_acc.self_loop_relationships:
        issues.append(Issue("error", "self_loop_relationships", f"{rel_acc.self_loop_relationships} relationships have source==target"))
    if unknown_rel_types:
        examples = ", ".join(sorted(unknown_rel_types)[:5])
        issues.append(Issue("warning", "unknown_rel_types", f"{len(unknown_rel_types)} unknown relationship types: {examples}"))


def _emit_warnings_chunk_a(
    acc: _EntityStats, issues: list[Issue], *, high_fanout_count: int, duplicate_rel_count: int,
    coord_clusters_precise: int, coord_clustered_entities_precise: int, itinerary_area_mismatches: int,
) -> None:
    if high_fanout_count:
        issues.append(Issue("error", "relationship_fanout", f"{high_fanout_count} entities have more than {MAX_DIRECT_RELATIONSHIPS} direct relationships"))
    if duplicate_rel_count:
        issues.append(Issue("warning", "duplicate_relationships", f"{duplicate_rel_count} duplicate relationship keys found"))
    if coord_clusters_precise:
        issues.append(Issue("warning", "coordinate_clusters_precise", f"{coord_clusters_precise} precise coordinate clusters ({coord_clustered_entities_precise} precise entities share exact same coordinates)"))
    if acc.timestamp_inversions:
        issues.append(Issue("warning", "timestamp_inversions", f"{acc.timestamp_inversions} entities have updatedAt before created_at"))
    if acc.image_missing_credit:
        issues.append(Issue("warning", "image_missing_credit", f"{acc.image_missing_credit} image URLs have no author/credit metadata"))
    if acc.image_missing_license:
        issues.append(Issue("warning", "image_missing_license", f"{acc.image_missing_license} image URLs have no license metadata"))
    if acc.image_missing_source:
        issues.append(Issue("warning", "image_missing_source", f"{acc.image_missing_source} image URLs have no source metadata"))
    if itinerary_area_mismatches:
        issues.append(Issue("warning", "itinerary_area_mismatch", f"{itinerary_area_mismatches} itinerary stops reference entities outside the itinerary's declared area"))


def _emit_warnings_chunk_b(
    acc: _EntityStats, issues: list[Issue], *, itinerary_empty_stops: int, itinerary_excessive_stops: int,
) -> None:
    if acc.summary_short:
        issues.append(Issue("warning", "summary_short", f"{acc.summary_short} entities have summary < 50 chars"))
    if acc.summary_long:
        issues.append(Issue("warning", "summary_long", f"{acc.summary_long} entities have summary > 500 chars"))
    if acc.text_repeated_sentence:
        issues.append(Issue("warning", "text_repeated_sentence", f"{acc.text_repeated_sentence} entities have adjacent repeated sentences"))
    if acc.text_bad_sentence_join:
        issues.append(Issue("warning", "text_bad_sentence_join", f"{acc.text_bad_sentence_join} entities have suspicious joined sentences like 'word.next'"))
    if acc.text_excessive_length:
        issues.append(Issue("warning", "text_excessive_length", f"{acc.text_excessive_length} entities have text fields > {MAX_REASONABLE_TEXT_LEN} chars"))
    if acc.name_too_short:
        issues.append(Issue("warning", "name_too_short", f"{acc.name_too_short} entities have name < 2 chars"))
    if acc.name_too_long:
        issues.append(Issue("warning", "name_too_long", f"{acc.name_too_long} entities have name > 100 chars"))
    if itinerary_empty_stops:
        issues.append(Issue("warning", "itinerary_empty_stops", f"{itinerary_empty_stops} itineraries have no stops"))
    if itinerary_excessive_stops:
        issues.append(Issue("warning", "itinerary_excessive_stops", f"{itinerary_excessive_stops} itineraries have > 20 stops"))


def _emit_warnings_chunk_c(acc: _EntityStats, issues: list[Issue]) -> None:
    if acc.missing_summary_non_place:
        issues.append(Issue("warning", "missing_summary_non_place", f"{acc.missing_summary_non_place} non-place entities are missing summary"))
    if acc.boilerplate_summary:
        issues.append(Issue("error", "boilerplate_summary", f"{acc.boilerplate_summary} entities have placeholder '404 / không đủ thông tin' summaries"))
    if acc.missing_summary_place:
        issues.append(Issue("warning", "missing_summary_place", f"{acc.missing_summary_place} place entities are missing summary"))
    if acc.missing_source:
        issues.append(Issue("warning", "missing_source", f"{acc.missing_source} entities are missing source ({acc.missing_source_non_place} non-place, {acc.missing_source_place} place)"))
    if acc.missing_place_id:
        issues.append(Issue("warning", "missing_place_id", f"{acc.missing_place_id} non-place entities are missing placeId"))
    if acc.missing_location:
        issues.append(Issue("warning", "missing_location", f"{acc.missing_location} entities have no coordinates or coords ({acc.missing_location_non_place} non-place, {acc.missing_location_place} place)"))
    if acc.invalid_entity_ids:
        issues.append(Issue("warning", "invalid_entity_ids", f"{acc.invalid_entity_ids} entity IDs contain spaces, control chars, or are excessively long"))
    if acc.invalid_source_urls:
        issues.append(Issue("warning", "invalid_source_urls", f"{acc.invalid_source_urls} source URLs have invalid format"))
    if acc.invalid_phone_format:
        issues.append(Issue("warning", "invalid_phone_format", f"{acc.invalid_phone_format} entities have phone not matching VN format (+84/0 + 9-10 digits)"))
    if acc.invalid_website_urls:
        issues.append(Issue("warning", "invalid_website_urls", f"{acc.invalid_website_urls} entities have invalid website URLs in attributes"))


def _emit_mixed_warning_issues(
    acc: _EntityStats, issues: list[Issue], *, high_fanout_count: int, duplicate_rel_count: int,
    coord_clusters_precise: int, coord_clustered_entities_precise: int, itinerary_area_mismatches: int,
    itinerary_empty_stops: int, itinerary_excessive_stops: int,
) -> None:
    _emit_warnings_chunk_a(
        acc, issues, high_fanout_count=high_fanout_count, duplicate_rel_count=duplicate_rel_count,
        coord_clusters_precise=coord_clusters_precise,
        coord_clustered_entities_precise=coord_clustered_entities_precise,
        itinerary_area_mismatches=itinerary_area_mismatches,
    )
    _emit_warnings_chunk_b(
        acc, issues, itinerary_empty_stops=itinerary_empty_stops,
        itinerary_excessive_stops=itinerary_excessive_stops,
    )
    _emit_warnings_chunk_c(acc, issues)


def _compute_seo_coverage(entities: list[Any]) -> dict[str, dict[str, Any]]:
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
    return type_coverage


def _compute_entities_by_area(entities: list[Any]) -> dict[str, int]:
    area_counts: dict[str, int] = Counter()
    for e in entities:
        if not isinstance(e, dict) or e.get("type") == "place":
            continue
        ea = e.get("area")
        area_counts[ea if ea else "(none)"] += 1
    return dict(area_counts.most_common())


def _compute_confidence_distribution(entities: list[Any]) -> dict[str, Any] | None:
    confidence_values = []
    for e in entities:
        if isinstance(e, dict) and e.get("type") != "place":
            c = e.get("confidence")
            if isinstance(c, (int, float)):
                confidence_values.append(float(c))
    if not confidence_values:
        return None
    sorted_conf = sorted(confidence_values)
    mid = len(sorted_conf) // 2
    median = sorted_conf[mid] if len(sorted_conf) % 2 else round((sorted_conf[mid - 1] + sorted_conf[mid]) / 2, 3)
    return {
        "min": round(min(sorted_conf), 3),
        "max": round(max(sorted_conf), 3),
        "median": median,
        "count": len(sorted_conf),
    }


def _compute_quality_stats(entities: list[Any], stats: dict[str, Any]) -> None:
    non_place = [e for e in entities if isinstance(e, dict) and e.get("type") != "place"]
    conf_dist = _compute_confidence_distribution(entities)
    if conf_dist is not None:
        stats["confidence_distribution"] = conf_dist

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


def _collect_referenced_ids(relationships: list[Any], itineraries: list[Any]) -> set[str]:
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
            ref = itinerary_stop_ref(stop)
            if ref:
                referenced_ids.add(str(ref))
    return referenced_ids


def _compute_orphan_count(entities: list[Any], relationships: list[Any], itineraries: list[Any]) -> int:
    referenced_ids = _collect_referenced_ids(relationships, itineraries)
    return sum(
        1 for e in entities
        if isinstance(e, dict) and e.get("type") != "place" and e.get("id")
        and str(e["id"]) not in referenced_ids
    )


def _derive_rel_counts(rel_acc: _RelStats) -> tuple[set[str], int, int]:
    unknown_rel_types = {t for t in rel_acc.relationship_type_counts if t not in KNOWN_REL_TYPES}
    duplicate_rel_count = sum(1 for count in rel_acc.duplicate_relationships.values() if count > 1)
    high_fanout_count = sum(1 for count in rel_acc.relationship_fanout.values() if count > MAX_DIRECT_RELATIONSHIPS)
    return unknown_rel_types, duplicate_rel_count, high_fanout_count


def _build_entity_by_id(entities: list[Any]) -> dict[str, Any]:
    return {
        str(entity.get("id")): entity
        for entity in entities
        if isinstance(entity, dict) and entity.get("id")
    }


def _normalize_top_level(data: dict[str, Any], issues: list[Issue]) -> tuple[list[Any], list[Any], list[Any]]:
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
    return entities, relationships, itineraries


def _check_xa_phuong_count(entities: list[Any], issues: list[Issue]) -> None:
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


def _compute_place_coords_pct(entities: list[Any]) -> float:
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
    return round(100 * place_with_coords / max(place_xa_phuong, 1), 1)


def _check_place_level_none(entities: list[Any], issues: list[Issue]) -> int:
    place_level_none = 0
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        if entity.get("type") == "place" and entity.get("level") is None:
            place_level_none += 1
    if place_level_none:
        issues.append(Issue("warning", "place_level_none",
            f"{place_level_none} place entities have level=None (should be xa/phuong/thi-tran/tp/huyen/tinh)"))
    return place_level_none


def _check_duplicate_names(entities: list[Any], issues: list[Issue]) -> dict[str, int]:
    name_counts = Counter((e.get("name") or "").strip() for e in entities if isinstance(e, dict) and e.get("name"))
    duplicate_names = {name: count for name, count in name_counts.items() if count > 1}
    if duplicate_names:
        examples = ", ".join(list(duplicate_names)[:5])
        issues.append(Issue("warning", "duplicate_names", f"{len(duplicate_names)} duplicate display names: {examples}"))
    return duplicate_names


def _check_duplicate_name_type(entities: list[Any], issues: list[Issue]) -> int:
    name_type_counts = Counter(
        ((e.get("name") or "").strip(), e.get("type"))
        for e in entities
        if isinstance(e, dict) and e.get("name") and e.get("type")
    )
    duplicate_name_type = {k: c for k, c in name_type_counts.items() if c > 1}
    if duplicate_name_type:
        examples = ", ".join(f"{n}({t})" for (n, t), _ in list(duplicate_name_type.items())[:5])
        issues.append(Issue("warning", "duplicate_name_type", f"{len(duplicate_name_type)} entities share same name+type: {examples}"))
    return len(duplicate_name_type)


def _check_data_js(data_path: Path, issues: list[Issue]) -> str:
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
    return data_js_status


def validate(data: dict[str, Any], data_path: Path) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    entities, relationships, itineraries = _normalize_top_level(data, issues)

    ids: list[str] = []
    dangling_rel_targets: set[str] = set()

    acc = _scan_entities(entities, issues, ids)
    missing_summary = acc.missing_summary
    missing_summary_non_place = acc.missing_summary_non_place
    missing_summary_place = acc.missing_summary_place
    boilerplate_summary = acc.boilerplate_summary
    missing_source = acc.missing_source
    missing_source_non_place = acc.missing_source_non_place
    missing_source_place = acc.missing_source_place
    missing_location = acc.missing_location
    missing_location_non_place = acc.missing_location_non_place
    missing_location_place = acc.missing_location_place
    legacy_coords_only = acc.legacy_coords_only
    out_of_bounds_coordinates = acc.out_of_bounds_coordinates
    missing_place_id = acc.missing_place_id
    missing_area_non_place = acc.missing_area_non_place
    source_not_list = acc.source_not_list
    season_integrity_errors = acc.season_integrity_errors
    low_confidence_count = acc.low_confidence_count
    empty_attrs_non_place = acc.empty_attrs_non_place
    timestamp_inversions = acc.timestamp_inversions
    summary_short = acc.summary_short
    summary_long = acc.summary_long
    text_repeated_sentence = acc.text_repeated_sentence
    text_bad_sentence_join = acc.text_bad_sentence_join
    text_excessive_length = acc.text_excessive_length
    has_images_non_place = acc.has_images_non_place
    image_total = acc.image_total
    image_missing_credit = acc.image_missing_credit
    image_missing_license = acc.image_missing_license
    image_missing_source = acc.image_missing_source
    name_too_short = acc.name_too_short
    name_too_long = acc.name_too_long
    invalid_source_urls = acc.invalid_source_urls
    invalid_phone_format = acc.invalid_phone_format
    invalid_website_urls = acc.invalid_website_urls
    invalid_entity_ids = acc.invalid_entity_ids
    coords_without_address = acc.coords_without_address
    summary_truncated = acc.summary_truncated
    unknown_type_count = acc.unknown_type_count
    short_summary_examples = acc.short_summary_examples
    source_url_reuse = acc.source_url_reuse

    _check_xa_phuong_count(entities, issues)

    id_counts = Counter(ids)
    duplicate_ids = {entity_id: count for entity_id, count in id_counts.items() if count > 1}
    id_set = set(ids)
    entity_by_id = _build_entity_by_id(entities)

    _emit_entity_issues(acc, duplicate_ids, issues)

    place_coords_pct = _compute_place_coords_pct(entities)
    place_level_none = _check_place_level_none(entities, issues)

    rel_acc = _scan_relationships(relationships, entities, entity_by_id, id_set, issues, dangling_rel_targets)
    broken_relationships = rel_acc.broken_relationships
    area_place_conflicts = rel_acc.area_place_conflicts
    produced_in_area_conflicts = rel_acc.produced_in_area_conflicts
    produced_in_target_type_errors = rel_acc.produced_in_target_type_errors
    produced_in_source_type_errors = rel_acc.produced_in_source_type_errors
    far_near_relationships = rel_acc.far_near_relationships
    near_missing_location = rel_acc.near_missing_location
    relationship_type_counts = rel_acc.relationship_type_counts

    unknown_rel_types, duplicate_rel_count, high_fanout_count = _derive_rel_counts(rel_acc)
    _emit_relationship_issues(rel_acc, dangling_rel_targets, unknown_rel_types, issues)
    # DI-005: itinerary stop trỏ entity không tồn tại (free-text stop không có id → bỏ qua)
    dangling_stops = _count_dangling_stops(itineraries, id_set)
    if dangling_stops:
        issues.append(Issue("error", "dangling_itinerary_stops", f"{dangling_stops} itinerary stops reference missing entities"))
    # DI-016: itinerary stops sanity
    itinerary_empty_stops, itinerary_excessive_stops = _count_itinerary_stop_sanity(itineraries)
    # DI-006: near relationships are stored canonically; runtime indexes them bidirectionally.
    near_one_way_edges, near_reciprocal_pairs = _count_near_edges(relationships)

    # DI-007: coordinate clustering. Approximate centroids are allowed; precise duplicates are suspicious.
    (coord_clusters, coord_clustered_entities, coord_clusters_approximate,
     coord_clustered_entities_approximate, coord_clusters_precise,
     coord_clustered_entities_precise) = _count_coord_clusters(entities)

    # DI-012: itinerary-stop area mismatch
    itinerary_area_mismatches = _count_itinerary_area_mismatches(itineraries, entity_by_id)

    # DI-013: relationship type singleton combos are tracked as entropy, not warnings.
    rel_type_singletons = _count_rel_type_singletons(relationships, entity_by_id)

    _emit_mixed_warning_issues(
        acc, issues,
        high_fanout_count=high_fanout_count,
        duplicate_rel_count=duplicate_rel_count,
        coord_clusters_precise=coord_clusters_precise,
        coord_clustered_entities_precise=coord_clustered_entities_precise,
        itinerary_area_mismatches=itinerary_area_mismatches,
        itinerary_empty_stops=itinerary_empty_stops,
        itinerary_excessive_stops=itinerary_excessive_stops,
    )

    duplicate_names = _check_duplicate_names(entities, issues)
    stats_dup_name_type = _check_duplicate_name_type(entities, issues)
    data_js_status = _check_data_js(data_path, issues)

    entity_types_dist = dict(Counter(e.get("type") for e in entities if isinstance(e, dict)).most_common())
    non_place_total = sum(1 for e in entities if isinstance(e, dict) and e.get("type") != "place")
    image_coverage_pct = round(100 * has_images_non_place / max(non_place_total, 1), 1)
    duplicate_source_urls = sum(1 for c in source_url_reuse.values() if c > 1)

    stats = {
        "entities": len(entities),
        "relationships": len(relationships),
        "itineraries": len(itineraries),
        "entity_types": entity_types_dist,
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
        "near_one_way_edges": near_one_way_edges,
        "near_reciprocal_pairs": near_reciprocal_pairs,
        "coordinate_clusters": coord_clusters,
        "coordinate_clustered_entities": coord_clustered_entities,
        "coordinate_clusters_approximate": coord_clusters_approximate,
        "coordinate_clustered_entities_approximate": coord_clustered_entities_approximate,
        "coordinate_clusters_precise": coord_clusters_precise,
        "coordinate_clustered_entities_precise": coord_clustered_entities_precise,
        "timestamp_inversions": timestamp_inversions,
        "image_coverage_pct": image_coverage_pct,
        "image_total": image_total,
        "image_missing_credit": image_missing_credit,
        "image_missing_license": image_missing_license,
        "image_missing_source": image_missing_source,
        "summary_short": summary_short,
        "summary_long": summary_long,
        "text_repeated_sentence": text_repeated_sentence,
        "text_bad_sentence_join": text_bad_sentence_join,
        "text_excessive_length": text_excessive_length,
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
        "duplicate_source_urls": duplicate_source_urls,
        "data_js_status": data_js_status,
    }

    # DI-014: per-type SEO attribute coverage
    stats["seo_attr_coverage"] = _compute_seo_coverage(entities)
    # DI-027: per-area entity counts
    stats["entities_by_area"] = _compute_entities_by_area(entities)
    # DI-017: entity quality score distribution
    _compute_quality_stats(entities, stats)
    # DI-018: graph connectivity
    stats["graph_connectivity"] = graph_connectivity(entities, relationships)

    # DI-021: orphan non-place entities (no relationship, no itinerary stop reference)
    orphan_count = _compute_orphan_count(entities, relationships, itineraries)
    stats["orphan_entities"] = orphan_count
    stats["unknown_entity_types"] = unknown_type_count
    stats["short_summary_examples"] = short_summary_examples
    stats["dangling_rel_entity_ids"] = sorted(dangling_rel_targets)[:20]
    if orphan_count:
        issues.append(Issue("warning", "orphan_entities",
            f"{orphan_count} non-place entities have no relationships or itinerary references"))

    return issues, stats


DATA_QUALITY_KEYS = [
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
    "near_one_way_edges",
    "near_reciprocal_pairs",
    "coordinate_clusters",
    "coordinate_clustered_entities",
    "coordinate_clusters_approximate",
    "coordinate_clustered_entities_approximate",
    "coordinate_clusters_precise",
    "coordinate_clustered_entities_precise",
    "timestamp_inversions",
    "image_coverage_pct",
    "image_total",
    "image_missing_credit",
    "image_missing_license",
    "image_missing_source",
    "summary_short",
    "summary_long",
    "text_repeated_sentence",
    "text_bad_sentence_join",
    "text_excessive_length",
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
]


def _print_report_header(stats: dict[str, Any]) -> None:
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
    for key in DATA_QUALITY_KEYS:
        print(f"  {key}: {stats.get(key)}")


def _print_report_examples(stats: dict[str, Any]) -> None:
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


def _print_report_seo_coverage(stats: dict[str, Any]) -> None:
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


def _print_report_distributions(stats: dict[str, Any]) -> None:
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
        print("\nGraph connectivity:")
        print(f"  components: {gc.get('total_components', 0)}")
        print(f"  largest: {gc.get('largest_component', 0)}")
        print(f"  isolated: {gc.get('isolated_entities', 0)}")


def _print_report_issues(issues: list[Issue]) -> None:
    grouped: dict[str, list[Issue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.severity].append(issue)
    for severity in ["error", "warning"]:
        if not grouped.get(severity):
            continue
        print(f"\n{severity.upper()}S:")
        for issue in grouped[severity]:
            print(f"  [{issue.code}] {issue.message}")


def print_report(issues: list[Issue], stats: dict[str, Any]) -> None:
    _print_report_header(stats)
    _print_report_examples(stats)
    _print_report_seo_coverage(stats)
    _print_report_distributions(stats)
    _print_report_issues(issues)


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
