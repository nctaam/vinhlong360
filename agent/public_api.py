"""
vinhlong360 — Public API.

Read-only endpoints for the frontend to consume entities, itineraries,
and search results from the database instead of static data.json.

Mount: app.include_router(public_router)
"""

import asyncio
from dataclasses import asdict
import hashlib
import json
from ocop import is_ocop_certified, ocop_tier
import logging
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Literal, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    ValidationError,
)
from api_schemas import (  # W6.3: response_model (extra="allow" — không strip field FE)
    AreasResponse, AutocompleteResponse, CollectionsResponse, CorrectionIntakeContract, EntityDetailResponse, EntityListResponse, EntityMapResponse, EntityTypesResponse,  # noqa: F401  (be mat va cua test — mien entity sang goi rieng 2026-08-28)
    EventsResponse, HomepageResponse, MapPin, SearchResponse, StatsResponse, TransparencyResponse,
    # SiteSettingsResponse sang siteops/api.py cung route cua no (2026-08-29, lat 3)
)
import lunar_calendar
from config import settings  # noqa: F401  (be mat va cua test — mien entity sang goi rieng 2026-08-28)
from database import db
from search_contract import SearchFilters, coerce_query_int, search_public_entities, normalize_search_text
from control_plane.clock import system_clock
from middleware import report_limiter, get_client_ip
from auth_middleware import validate_path_id, require_pg, require_user, require_csrf, get_current_user
from user_preferences import (
    MAX_PREFERENCE_REVISION,
    MAX_RECOMMENDATION_RESET_AT_LENGTH,
    PreferenceRevisionConflict,
    PreferenceValidationError,
    _public_snapshot,
    load_preference_consents,
    load_preferences,
    patch_preferences_with_consents,
    recommendation_cutoff,
)
from location_resolver import (
    IpGeocoder,
    LocationConfirmationError,
    LocationInputError,
    ReverseGeocoder,
    get_ip_geocoder,
    get_reverse_geocoder,
    issue_location_confirmation,
    resolve_gps,
    resolve_ip,
    verify_location_confirmation,
)
from personalization_events import (
    PERSONALIZATION_CONTEXTS,
    PERSONALIZATION_EVENT_TYPES,
    PersonalizationEventError,
    read_legacy_events_if_allowed,
    read_personalization_events,
    record_recommendation_reset,
    write_personalization_event,
)

if __package__:
    from .image_descriptor import describe_review_image
    # Route itinerary sang itineraries/api.py (2026-08-29, lát 2). HAI tên service
    # ở lại: test_itineraries_boundary.py:48-49 chốt consumer trỏ CÙNG OBJECT với
    # nhà thật qua public_api.<tên> — giữ nguyên văn là lưới kiểm chứng của cú dời.
    from .itineraries.itinerary_optimizer import optimize_stop_order  # noqa: F401
    from .itineraries.itinerary_schedule import parse_opening_hours  # noqa: F401
    from .trust_policy import build_explanation, derive_freshness, derive_source_tier
else:
    from image_descriptor import describe_review_image
    from itineraries.itinerary_optimizer import optimize_stop_order  # noqa: F401
    from itineraries.itinerary_schedule import parse_opening_hours  # noqa: F401
    from trust_policy import build_explanation, derive_freshness, derive_source_tier

if __package__:
    from .launch_evidence import current_policy_evidence
    from .profile_access import resolve_profile_access
else:
    from launch_evidence import current_policy_evidence  # noqa: F401  (be mat va cua test — mien entity sang goi rieng 2026-08-28)
    from profile_access import resolve_profile_access

# Tầng đọc entity dùng chung — tách 2026-08-28 (bước 1a của lát entities/).
# Cả gói entities/ sắp bóc LẪN file này đều gọi; để nguyên chỗ cũ là buộc
# entities/ import ngược public_api — vòng. Xem agent/entity_read.py.
from entity_read import (  # noqa: F401  (tái xuất: test vá qua public_api.<tên>)
    _EVENT_SCAN_LIMIT,
    _FULL_SCAN_LIMIT,
    _GALLERY_DISCLOSURE,
    _PLACE_CACHE_MAX,
    _apply_cached_place,
    _enrich_place,
    _err,
    _filter_public_entities,
    _gallery_editorial_images,
    _get_place,
    _get_public_entities_batch,
    _get_public_entity,
    _is_public,
    _itinerary_stop_entity_id,
    _place_cache,
    _place_cache_lock,
    _project_public_entity_media,
    _public_entity_has_media,
    _public_facilities_by_place,
    _public_itinerary_stops,
    _warn_if_scan_truncated,
)

# Mien ENTITY sang agent/entities/ (2026-08-28, buoc 1b). Tai xuat de bo test
# hien co van va duoc qua `public_api.<ten>` — giu chung NGUYEN VAN chinh la
# luoi kiem chung cua cu doi nay.
from entity_read import _require_rollout, _rollout_enabled  # noqa: F401
from entity_read import invalidate_entity_cache, invalidate_place_cache  # noqa: F401
from entities.api import (  # noqa: F401
    DEFAULT_RELATIONSHIP_LIMIT,
    EntityClaimIn,
    _DAY_PLAN_SLOTS,
    _MINIMAL_FIELDS,
    _PRACTICAL_FACTS_KEYS,
    _PUNCT_RE,
    _REVIEW_STATS_CACHE,
    _REVIEW_STATS_TTL,
    _SIMILAR_TTL,
    _VN_STOPWORDS,
    _WARD_GROUPS,
    _apply_practical_fact_fallbacks,
    _build_day_plan_stops,
    _build_practical_facts,
    _build_similar_cards,
    _build_source_freshness,
    _compute_similar_entities,
    _coords_in_bbox,
    _days_since,
    _enrich_entity_place,
    _entity_card_shape,
    _entity_detail_index_policy,
    _extract_mentions,
    _filter_popular_entities,
    _filter_public_relationships,
    _haversine_km,
    _int0,
    _map_search_shape,
    _public_entities_by_place,
    _public_entity_revision,
    _public_index_policy_child_count,
    _score_popular_entity,
    _select_day_plan_candidates,
    _shape_popular_entity,
    _shape_review_row,
    _similar_cache,
    _similar_reason_vi,
    _to_minimal,
    compare_entities,
    entities_map_search,
    entities_trending,
    entity_search,
    entity_types,
    get_collection_by_slug,
    get_entity,
    get_entity_gallery,
    get_entity_qa,
    get_entity_rating_breakdown,
    get_entity_relationships,
    get_entity_reviews,
    get_entity_stats,
    get_featured_entities,
    get_nearby_entities,
    get_review_stats,
    get_similar_entities,
    list_entities,
    list_places,
    list_public_collections,
    place_day_plan,
    place_overview,
    popular_entities,
    submit_entity_claim,
)

router = APIRouter(prefix="/api", tags=["public"])

# Load the release-owned disclosure artifact once so every gallery descriptor uses
# the same canonical copy and revision.








import threading as _threading


# Perf-P0: cache payload /homepage (endpoint nóng nhất) — trước đây scan toàn bảng entity
# + 6×COUNT mỗi request. Curation tất định theo tháng → cache TTL ngắn, theo tháng.
import time as _time
_homepage_cache: dict = {"month": None, "data": None, "ts": 0.0}
_HOMEPAGE_TTL = 120  # giây
_homepage_rebuilding = False
_homepage_lock = asyncio.Lock()

# invalidate_entity_cache: sang entity_read (2026-08-28) — tai xuat o khoi import.


















# _itinerary_stop_entity_id + _public_itinerary_stops: sang entity_read (2026-08-29,
# bước 1a lát itineraries/) — tái xuất ở khối import đầu file; homepage bên dưới
# vẫn gọi qua tên module này.


def _itinerary_coverage_areas(itinerary: dict) -> set[str]:
    areas = {str(area) for area in (itinerary.get("areas") or []) if area}
    primary = itinerary.get("area")
    if primary and (primary != "lien-vung" or not areas):
        areas.add(str(primary))
    return areas














# invalidate_place_cache: sang entity_read (2026-08-28). Phan viec CUA FILE NAY
# (refresh homepage-cache) dang ky qua listener — xem cuoi file.

# GĐ13.6f: báo cáo thông tin sai / nội dung vi phạm — lưu JSONL nhẹ (free-tier),
# admin xem qua /admin/reports để xử lý (takedown/sửa). KHÔNG dùng DB/dịch vụ trả phí.
REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
SEARCH_LOG_FILE = Path(__file__).resolve().parent / "data" / "search_queries.jsonl"
_VALID_TARGET_TYPES = {"facility", "entity", "post", "comment", "other"}

_JSONL_MAX_LINES = 5000
_jsonl_lock = _threading.Lock()


def _maybe_rotate_jsonl(filepath: Path) -> None:
    try:
        if not filepath.exists():
            return
        lines = filepath.read_text(encoding="utf-8").splitlines()
        if len(lines) <= _JSONL_MAX_LINES:
            return
        archive = filepath.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.jsonl")
        archive.write_text("\n".join(lines[:-_JSONL_MAX_LINES]) + "\n", encoding="utf-8")
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text("\n".join(lines[-_JSONL_MAX_LINES:]) + "\n", encoding="utf-8")
        tmp.replace(filepath)
    except Exception:
        logger.exception("JSONL rotation failed for %s", filepath)


def _log_search_query(q: str, entity_type: str | None, area: str | None, total: int) -> None:
    try:
        record = json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "q": q[:200],
            "type": entity_type,
            "area": area,
            "results": total,
            "zero_result": int(total or 0) == 0,
        }, ensure_ascii=False)
        with _jsonl_lock:
            SEARCH_LOG_FILE.parent.mkdir(exist_ok=True)
            with open(SEARCH_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(record + "\n")
            _maybe_rotate_jsonl(SEARCH_LOG_FILE)
    except Exception:
        logger.debug("search log write failed", exc_info=True)


_VALID_USER_EVENT_TYPES = PERSONALIZATION_EVENT_TYPES
_VALID_RECOMMENDATION_CONTEXTS = PERSONALIZATION_CONTEXTS - {"unknown"}
_EVENT_WEIGHTS = {
    "save_add": 5.0,
    "visit_mark": 4.0,
    "entity_view": 2.2,
    "map_focus": 1.8,
    "itinerary_view": 1.8,
    "search": 1.4,
    "community_view": 1.0,
    "post_view": 1.0,
    "save_remove": -2.0,
}
_EXPLICIT_INTEREST_BASE_SCORE = 1_000_000.0
_INTEREST_RULES: dict[str, dict[str, Any]] = {
    "food": {
        "label": "Ẩm thực",
        "types": {"dish", "restaurant", "cafe", "drink"},
        "terms": ("am thuc", "mon", "quan", "banh", "bun", "lau", "ca", "che", "an", "uong"),
    },
    "local_products": {
        "label": "Đặc sản & OCOP",
        "types": {"product"},
        "terms": ("ocop", "dac san", "qua", "mua", "trai cay", "dua", "buoi", "cam", "keo"),
    },
    "garden": {
        "label": "Miệt vườn",
        "types": {"experience", "nature"},
        "terms": ("vuon", "miet vuon", "song nuoc", "cu lao", "trai cay", "sinh thai"),
    },
    "culture": {
        "label": "Văn hóa",
        "types": {"attraction", "history", "event"},
        "terms": ("chua", "le hoi", "di tich", "van hoa", "khmer", "lich su"),
    },
    "craft": {
        "label": "Làng nghề",
        "types": {"craft_village", "organization"},
        "terms": ("lang nghe", "gom", "thu cong", "co so", "htx", "san xuat"),
    },
    "stay": {
        "label": "Lưu trú",
        "types": {"accommodation"},
        "terms": ("luu tru", "homestay", "khach san", "nghi dem", "resort"),
    },
}


PreferenceInterest = Annotated[str, Field(max_length=64)]


class UserEventIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(max_length=64)
    context: Optional[str] = Field(None, max_length=64)
    entity_id: Optional[str] = Field(None, max_length=200)
    entity_type: Optional[str] = Field(None, max_length=64)
    area_id: Optional[str] = Field(None, max_length=200)
    interest_keys: list[PreferenceInterest] = Field(default_factory=list, max_length=12)


PreferenceTimestamp = Annotated[
    str, Field(max_length=MAX_RECOMMENDATION_RESET_AT_LENGTH)
]


class PreferencePatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: StrictInt = Field(ge=0, le=MAX_PREFERENCE_REVISION)
    region_id: Optional[str] = Field(None, max_length=128)
    region_label: Optional[str] = Field(None, max_length=160)
    region_scope: Optional[str] = Field(None, max_length=16)
    location_source: Optional[str] = Field(None, max_length=16)
    location_accuracy: Optional[str] = Field(None, max_length=16)
    location_consent_state: Optional[str] = Field(None, max_length=16)
    location_enabled: Optional[StrictBool] = None
    personalization_enabled: Optional[StrictBool] = None
    explicit_interests: Optional[list[PreferenceInterest]] = Field(
        None, max_length=12
    )
    recommendation_reset_at: PreferenceTimestamp | None = None
    consent_version: Optional[str] = Field(None, max_length=64)
    location_confirmation_token: Optional[str] = Field(None, max_length=2048)


class LocationResolveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["gps", "ip"]
    latitude: StrictFloat | StrictInt | None = None
    longitude: StrictFloat | StrictInt | None = None


def _fold_text(value: Any) -> str:
    return normalize_search_text(value)


def _clean_short_text(value: Any, max_len: int = 200) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _entity_area(entity: dict | None) -> str:
    if not entity:
        return ""
    return str(entity.get("place_area") or entity.get("area") or entity.get("legacyArea") or "").strip()


def _interest_hits_from_text(text: str, entity_type: str | None = None) -> Counter:
    folded = _fold_text(text)
    hits: Counter = Counter()
    for key, rule in _INTEREST_RULES.items():
        if entity_type and entity_type in rule["types"]:
            hits[key] += 3
        for term in rule["terms"]:
            folded_term = _fold_text(term)
            if folded_term and folded_term in folded:
                hits[key] += 1
    return hits


def _interest_hits_from_entity(entity: dict | None) -> Counter:
    if not entity:
        return Counter()
    attrs = entity.get("attributes") or {}
    attr_text = " ".join(str(v) for v in attrs.values() if isinstance(v, (str, int, float)))
    text = " ".join([
        str(entity.get("name") or ""),
        str(entity.get("summary") or ""),
        str(entity.get("description") or ""),
        attr_text,
    ])
    return _interest_hits_from_text(text, entity.get("type"))


def _label_for_interest(key: str) -> str:
    rule = _INTEREST_RULES.get(key) or {}
    return str(rule.get("label") or key)


def _load_user_signal_entities(
    user_id: str, cutoff: datetime | None = None, limit: int = 80
) -> list[tuple[dict, str]]:
    if not db._use_pg:
        return []
    ph = db._ph
    uid = str(user_id)
    signals: list[tuple[dict, str]] = []
    saved_cutoff = f" AND s.created_at > {ph}" if cutoff is not None else ""
    visit_cutoff = f" AND v.created_at > {ph}" if cutoff is not None else ""
    saved_params: list[Any] = [uid]
    visit_params: list[Any] = [uid]
    if cutoff is not None:
        saved_params.append(cutoff)
        visit_params.append(cutoff)
    saved_params.append(limit // 2)
    visit_params.append(limit // 2)
    try:
        with db._conn() as conn:
            saved_rows = db._fetchall(conn, f"""
                SELECT e.* FROM saved_entities s
                JOIN entities e ON e.id = s.entity_id
                WHERE s.user_id = {ph}::uuid
                  AND COALESCE(e.status, '') != 'provisional'
                  AND (e.verified IS NULL OR e.verified != 0)
                  {saved_cutoff}
                ORDER BY s.created_at DESC
                LIMIT {ph}
            """, saved_params)
            visit_rows = db._fetchall(conn, f"""
                SELECT e.* FROM user_visits v
                JOIN entities e ON e.id = v.entity_id
                WHERE v.user_id = {ph}::uuid
                  AND COALESCE(e.status, '') != 'provisional'
                  AND (e.verified IS NULL OR e.verified != 0)
                  {visit_cutoff}
                ORDER BY v.created_at DESC
                LIMIT {ph}
            """, visit_params)
        _append_public_signals(saved_rows, "saved", signals)
        _append_public_signals(visit_rows, "visit", signals)
    except Exception:
        logger.debug("user signal entity query failed", exc_info=True)
    return signals


def _append_public_signals(rows: list, source: str, signals: list[tuple[dict, str]]) -> None:
    for row in rows:
        ent = db._parse_entity(row)
        if ent and _is_public(ent):
            signals.append((ent, source))


def _top_counter(counter: Counter, limit: int = 5, labels: dict[str, str] | None = None) -> list[dict]:
    items = []
    for key, score in counter.most_common(limit):
        if not key or score <= 0:
            continue
        item = {"key": key, "score": round(float(score), 2)}
        if labels:
            item["label"] = labels.get(key, key)
        items.append(item)
    return items


class _InterestAccumulator:
    """Mutable scratch state shared by the interest-profile passes (extract-method
    helper — behavior identical to the previous inline Counters/lists)."""

    def __init__(self) -> None:
        self.interest_scores: Counter = Counter()
        self.type_scores: Counter = Counter()
        self.area_scores: Counter = Counter()
        self.recent_entity_ids: list[str] = []
        self.recent_intents: list[dict] = []


def _apply_event_entity(acc: "_InterestAccumulator", entity: dict, entity_id: str, weight: float) -> None:
    acc.type_scores[str(entity.get("type") or "")] += weight
    if area := _entity_area(entity):
        acc.area_scores[area] += weight
    acc.interest_scores.update({k: v * weight for k, v in _interest_hits_from_entity(entity).items()})
    if entity_id and entity_id not in acc.recent_entity_ids:
        acc.recent_entity_ids.append(entity_id)


def _apply_event_fallback(acc: "_InterestAccumulator", event: dict, weight: float) -> None:
    entity_type = _clean_short_text(event.get("entity_type"), 60)
    if entity_type:
        acc.type_scores[entity_type] += weight
    if area := _clean_short_text(event.get("area_id"), 200):
        acc.area_scores[area] += weight
    for key in event.get("interest_keys") or []:
        normalized = _clean_short_text(key, 64)
        if normalized:
            acc.interest_scores[normalized] += weight


def _score_event_interest_keys(acc: "_InterestAccumulator", event: dict, weight: float) -> None:
    for key in event.get("interest_keys") or []:
        normalized = _clean_short_text(key, 64)
        if normalized:
            acc.interest_scores[normalized] += weight


def _apply_one_event(acc: "_InterestAccumulator", event: dict, event_entities: dict) -> None:
    etype = str(event.get("event_type") or "")
    weight = float(_EVENT_WEIGHTS.get(etype, 1.0))
    if weight == 0:
        return
    _score_event_interest_keys(acc, event, weight)
    entity_id = str(event.get("entity_id") or "")
    entity = event_entities.get(entity_id) if entity_id else None
    if entity and _is_public(entity):
        _apply_event_entity(acc, entity, entity_id, weight)
    else:
        fallback = dict(event)
        fallback["interest_keys"] = []
        _apply_event_fallback(acc, fallback, weight)
    if len(acc.recent_intents) < 8:
        acc.recent_intents.append({
            "event_type": etype,
            "context": event.get("context"),
            "entity_id": entity_id or None,
            "interest_keys": list(event.get("interest_keys") or [])[:12],
        })


def _apply_events_to_profile(acc: "_InterestAccumulator", events: list[dict], event_entities: dict) -> None:
    for event in events:
        _apply_one_event(acc, event, event_entities)


def _apply_signals_to_profile(
    acc: "_InterestAccumulator", user_id: str, cutoff: datetime | None
) -> None:
    for entity, source in _load_user_signal_entities(user_id, cutoff=cutoff):
        weight = 5.0 if source == "saved" else 4.0
        acc.type_scores[str(entity.get("type") or "")] += weight
        if area := _entity_area(entity):
            acc.area_scores[area] += weight
        acc.interest_scores.update({k: v * weight for k, v in _interest_hits_from_entity(entity).items()})
        eid = str(entity.get("id") or "")
        if eid and eid not in acc.recent_entity_ids:
            acc.recent_entity_ids.append(eid)


def _apply_query_and_context(acc: "_InterestAccumulator", query: str | None, context_entity: dict | None) -> None:
    if query:
        acc.interest_scores.update(_interest_hits_from_text(query))
    if context_entity:
        acc.type_scores[str(context_entity.get("type") or "")] += 2
        if area := _entity_area(context_entity):
            acc.area_scores[area] += 2
        acc.interest_scores.update({k: v * 1.5 for k, v in _interest_hits_from_entity(context_entity).items()})


def _apply_preference_profile(
    acc: "_InterestAccumulator", preferences: dict, *, include_interests: bool
) -> int:
    signal_count = 0
    source = preferences.get("location_source")
    location_allowed = source == "manual" or (
        source in {"gps", "ip"} and preferences.get("location_enabled") is True
    )
    if location_allowed:
        region = preferences.get("region_id") or preferences.get("region_label")
        if region:
            acc.area_scores[str(region)] += 50.0
            signal_count += 1
    if include_interests:
        for index, key in enumerate(preferences.get("explicit_interests") or []):
            normalized = _clean_short_text(key, 64)
            if normalized:
                acc.interest_scores[normalized] += (
                    _EXPLICIT_INTEREST_BASE_SCORE - index
                )
                signal_count += 1
    return signal_count


def _build_user_interest_profile(user_id: str, query: str | None = None, context_entity: dict | None = None) -> dict:
    acc = _InterestAccumulator()
    if not _rollout_enabled("PREFERENCE_PROFILE_V1"):
        _apply_query_and_context(acc, query, context_entity)
        labels = {key: _label_for_interest(key) for key in _INTEREST_RULES}
        return {
            "interests": _top_counter(acc.interest_scores, labels=labels),
            "areas": _top_counter(acc.area_scores),
            "types": _top_counter(acc.type_scores),
            "interest_scores": dict(acc.interest_scores),
            "area_scores": dict(acc.area_scores),
            "type_scores": dict(acc.type_scores),
            "recent_entity_ids": [],
            "recent_intents": [],
            "confidence": 0.0,
            "signal_count": 0,
            "personalization_enabled": False,
            "explicit_interests": [],
            "preference_snapshot": None,
        }
    preferences = _public_snapshot(load_preferences(user_id))
    personalization_enabled = preferences.get("personalization_enabled") is True
    preference_signal_count = _apply_preference_profile(
        acc, preferences, include_interests=personalization_enabled
    )
    if not personalization_enabled:
        return {
            "interests": [],
            "areas": _top_counter(acc.area_scores),
            "types": [],
            "interest_scores": {},
            "area_scores": dict(acc.area_scores),
            "type_scores": {},
            "recent_entity_ids": [],
            "recent_intents": [],
            "confidence": round(min(1.0, preference_signal_count / 20), 2),
            "signal_count": preference_signal_count,
            "personalization_enabled": False,
            "explicit_interests": [],
            "preference_snapshot": preferences,
        }

    cutoff = recommendation_cutoff(preferences)
    events = read_personalization_events(user_id, cutoff=cutoff)
    legacy = read_legacy_events_if_allowed(
        user_id, cutoff=cutoff, now=datetime.now(timezone.utc)
    )
    events = (events + legacy)[:300]

    event_entity_ids = [str(e.get("entity_id")) for e in events if e.get("entity_id")]
    event_entities = db.get_entities_batch(event_entity_ids[:80]) if event_entity_ids else {}

    _apply_events_to_profile(acc, events, event_entities)
    _apply_signals_to_profile(acc, user_id, cutoff)
    _apply_query_and_context(acc, query, context_entity)

    interest_scores = acc.interest_scores
    type_scores = acc.type_scores
    area_scores = acc.area_scores
    recent_entity_ids = acc.recent_entity_ids
    recent_intents = acc.recent_intents
    signal_count = preference_signal_count + len(events) + len(recent_entity_ids)
    labels = {key: _label_for_interest(key) for key in _INTEREST_RULES}
    return {
        "interests": _top_counter(interest_scores, labels=labels),
        "areas": _top_counter(area_scores),
        "types": _top_counter(type_scores),
        "interest_scores": dict(interest_scores),
        "area_scores": dict(area_scores),
        "type_scores": dict(type_scores),
        "recent_entity_ids": recent_entity_ids[:30],
        "recent_intents": recent_intents,
        "confidence": round(min(1.0, signal_count / 20), 2),
        "signal_count": signal_count,
        "personalization_enabled": True,
        "explicit_interests": list(preferences.get("explicit_interests") or []),
        "preference_snapshot": preferences,
    }


def _profile_next_actions(profile: dict) -> list[dict]:
    interests = [item.get("key") for item in profile.get("interests", [])]
    actions = []
    if "food" in interests:
        actions.append({"label": "Lưu quán muốn thử", "to": "/kham-pha/am-thuc"})
    if "local_products" in interests:
        actions.append({"label": "Tìm quà đặc sản", "to": "/ocop"})
    if "garden" in interests:
        actions.append({"label": "Lên lịch trình miệt vườn", "to": "/lich-trinh"})
    if "culture" in interests or "craft" in interests:
        actions.append({"label": "Khám phá văn hóa bản địa", "to": "/kham-pha/van-hoa"})
    if not actions:
        actions.append({"label": "Mở bản đồ khám phá", "to": "/ban-do"})
    return actions[:3]


def _project_public_profile_entries(items: object) -> list[dict[str, str]]:
    projected: list[dict[str, str]] = []
    if not isinstance(items, list):
        return projected
    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not isinstance(key, str) or not key:
            continue
        entry = {"key": key}
        label = item.get("label")
        if isinstance(label, str) and label:
            entry["label"] = label
        projected.append(entry)
    return projected


def _project_public_next_actions(profile: dict) -> list[dict[str, str]]:
    return [
        {"label": action["label"], "to": action["to"]}
        for action in _profile_next_actions(profile)
        if isinstance(action.get("label"), str) and isinstance(action.get("to"), str)
    ]


def _candidate_card(
    entity: dict, reasons: list[str], preference_snapshot: dict | None = None
) -> dict:
    projected = _project_public_entity_media(entity, limit=2)
    reason_vi = reasons[0] if reasons else ""
    card = {
        "id": projected.get("id"),
        "name": projected.get("name", ""),
        "type": projected.get("type", ""),
        "place": projected.get("place", ""),
        "place_name": projected.get("place_name"),
        "place_area": projected.get("place_area") or projected.get("area"),
        "summary": (projected.get("summary") or "")[:240],
        "image_descriptors": projected["image_descriptors"],
        "attributes": {
            "rating": (entity.get("attributes") or {}).get("rating"),
            "review_count": (entity.get("attributes") or {}).get("review_count"),
        },
        "recommendation_reasons": reasons[:2],
        "reason_vi": reason_vi,
    }
    if _rollout_enabled("RECOMMENDATION_EXPLANATIONS_V1"):
        card["explanation"] = build_explanation(
            entity, reasons, preference_snapshot
        )
    if _rollout_enabled("TRUST_DRAWER_V1"):
        card["source_tier"] = derive_source_tier(entity)
        card["freshness_status"] = derive_freshness(entity)
    return card


def _accumulate_interest_hits(
    hits: dict, profile: dict, explicit_set: set[str]
) -> tuple[float, set[str], bool]:
    score = 0.0
    matched_explicit: set[str] = set()
    inferred_match = False
    for key, hit_score in hits.items():
        pref = float(profile.get("interest_scores", {}).get(key, 0) or 0)
        if pref > 0 and hit_score > 0:
            contribution = min(pref * 0.8 + hit_score, 20)
            if key in explicit_set:
                # Explicit preference intent must dominate any number of inferred hits.
                score += _EXPLICIT_INTEREST_BASE_SCORE + contribution
                matched_explicit.add(key)
            else:
                score += contribution
                inferred_match = True
    return score, matched_explicit, inferred_match


def _score_interest_hits(entity: dict, profile: dict, reasons: list[str]) -> float:
    hits = _interest_hits_from_entity(entity)
    explicit_keys = [str(key) for key in profile.get("explicit_interests") or []]
    score, matched_explicit, inferred_match = _accumulate_interest_hits(
        hits, profile, set(explicit_keys)
    )
    for key in reversed([key for key in explicit_keys if key in matched_explicit]):
        label = _label_for_interest(key)
        if label:
            reasons.insert(0, f"Khớp sở thích {str(label).lower()}")
    if inferred_match and len(reasons) < 2:
        reasons.append("Hợp với nội dung bạn quan tâm")
    return score


def _score_current_context(entity_type: str, area: str, current: dict | None, reasons: list[str]) -> float:
    score = 0.0
    if current:
        if entity_type and entity_type == current.get("type"):
            score += 10
            reasons.append("Cùng chủ đề với nơi đang xem")
        if area and area == _entity_area(current):
            score += 7
            reasons.append("Gần mạch khám phá hiện tại")
    return score


def _score_query_and_attrs(entity: dict, attrs: dict, query: str, reasons: list[str]) -> float:
    score = 0.0
    folded_query = _fold_text(query)
    if folded_query:
        haystack = _fold_text(" ".join([str(entity.get("name") or ""), str(entity.get("summary") or "")]))
        if folded_query in haystack:
            score += 18
            reasons.append("Liên quan trực tiếp tới tìm kiếm")

    if _public_entity_has_media(entity):
        score += 2
    try:
        score += min(float(attrs.get("rating") or 0), 5)
        score += min(float(attrs.get("review_count") or 0) / 20, 4)
    except (TypeError, ValueError):
        pass
    return score


def _score_candidate(entity: dict, profile: dict, context: str, current: dict | None, query: str) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    entity_type = str(entity.get("type") or "")
    area = _entity_area(entity)
    attrs = entity.get("attributes") or {}
    type_score = float(profile.get("type_scores", {}).get(entity_type, 0) or 0)
    area_score = float(profile.get("area_scores", {}).get(area, 0) or 0)
    if type_score > 0:
        score += min(type_score * 2.4, 28)
        reasons.append("Hợp với nhóm nội dung bạn quan tâm")
    if area_score > 0:
        score += min(area_score * 1.8, 18)
        reasons.append("Cùng khu vực bạn hay xem")

    score += _score_interest_hits(entity, profile, reasons)
    score += _score_current_context(entity_type, area, current, reasons)
    score += _score_query_and_attrs(entity, attrs, query, reasons)

    if entity.get("id") in set(profile.get("recent_entity_ids") or []) and context not in {"saved", "entity"}:
        score -= 6
    return score, list(dict.fromkeys(reasons))[:3]


def _add_candidates(candidates: dict[str, dict], items: list[dict] | None, entity_id: str | None) -> None:
    for item in items or []:
        if not item or not _is_public(item):
            continue
        eid = str(item.get("id") or "")
        if not eid or eid == entity_id or eid in candidates:
            continue
        candidates[eid] = item


def _add_profile_type_candidates(candidates: dict[str, dict], profile: dict, entity_id: str | None) -> None:
    top_types = [item["key"] for item in profile.get("types", []) if item.get("key") and item.get("key") != "place"][:4]
    top_areas = [item["key"] for item in profile.get("areas", []) if item.get("key")][:3]
    for entity_type in top_types:
        if top_areas:
            for area in top_areas:
                _add_candidates(candidates, db.search_entities(entity_type=entity_type, area=area, limit=30, public_only=True), entity_id)
        _add_candidates(candidates, db.list_entities(entity_type=entity_type, limit=40, public_only=True, sort="rating"), entity_id)
    if top_areas and not top_types:
        for area in top_areas:
            _add_candidates(
                candidates,
                db.search_entities(area=area, limit=40, public_only=True),
                entity_id,
            )


def _gather_recommendation_candidates(profile: dict, current: dict | None, entity_id: str | None, query: str) -> dict[str, dict]:
    candidates: dict[str, dict] = {}

    if current:
        _add_candidates(candidates, db.search_entities(entity_type=current.get("type"), area=_entity_area(current) or None, limit=60, public_only=True), entity_id)
        _add_candidates(candidates, db.list_entities(entity_type=current.get("type"), limit=60, public_only=True, sort="rating"), entity_id)
    if query:
        _add_candidates(candidates, db.search_entities(q=query, limit=80, public_only=True), entity_id)

    _add_profile_type_candidates(candidates, profile, entity_id)

    if not candidates:
        _add_candidates(candidates, db.list_entities(limit=120, public_only=True, sort="rating"), entity_id)
    else:
        _add_candidates(candidates, db.list_entities(limit=80, public_only=True, sort="rating"), entity_id)
    return candidates


def _contextual_recommendations(user_id: str, context: str, entity_id: str | None, query: str, limit: int) -> dict:
    current = _get_public_entity(entity_id) if entity_id else None
    profile = _build_user_interest_profile(user_id, query=query, context_entity=current)
    personalized = profile.get("personalization_enabled") is True
    scoring_current = current if personalized else None
    scoring_query = query if personalized else ""
    candidates = _gather_recommendation_candidates(
        profile, scoring_current, entity_id, scoring_query
    )

    scored = []
    for entity in candidates.values():
        score, reasons = _score_candidate(
            entity, profile, context, scoring_current, scoring_query
        )
        if not reasons:
            reasons = ["Được cộng đồng quan tâm"]
        scored.append((score, entity, reasons))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("name") or "")))

    selected = [entity for _, entity, _ in scored[:limit]]
    if selected:
        _enrich_place(selected)
    preference_snapshot = profile.get("preference_snapshot")
    items = [
        _candidate_card(entity, reasons, preference_snapshot)
        for _, entity, reasons in scored[:limit]
    ]
    return {
        "context": context,
        "items": items,
        "reasons": {item["id"]: item.get("recommendation_reasons", []) for item in items if item.get("id")},
        "profile": {
            "interests": _project_public_profile_entries(profile.get("interests")),
            "areas": _project_public_profile_entries(profile.get("areas")),
            "types": _project_public_profile_entries(profile.get("types")),
            "signal_count": profile.get("signal_count", 0),
        },
    }


PREFERENCE_READ_RATE_LIMIT = 120
PREFERENCE_PATCH_RATE_LIMIT = 30
LOCATION_RESOLVE_RATE_LIMIT = 30
RECOMMENDATION_RESET_RATE_LIMIT = 5


@router.get(
    "/me/preferences",
    summary="Get current user preferences",
    # §1.3: route đòi đăng nhập PHẢI khai require_pg. Không có nó, chạy trên SQLite
    # sẽ nổ 500 lúc truy vấn bảng users thay vì trả 503 rõ ràng. Nhánh NP-1 thiếu
    # cả 5 route này; test hợp đồng tests/test_api_surface_contract.py bắt được.
    dependencies=[Depends(require_pg)],
    description="Returns the authenticated user's privacy-safe preference snapshot.",
)
async def get_my_preferences(response: Response, user=Depends(require_user)):
    from ratelimit import check_rate

    _require_rollout("PREFERENCE_PROFILE_V1")
    owner = str(user["id"])
    check_rate(
        f"preferences-read:{owner}",
        PREFERENCE_READ_RATE_LIMIT,
        300,
        "Too many preference requests",
    )
    response.headers["Cache-Control"] = "no-store"
    return _public_snapshot(await asyncio.to_thread(load_preferences, owner))


@router.patch(
    "/me/preferences",
    summary="Update current user preferences",
    # §1.3: route đòi đăng nhập PHẢI khai require_pg. Không có nó, chạy trên SQLite
    # sẽ nổ 500 lúc truy vấn bảng users thay vì trả 503 rõ ràng. Nhánh NP-1 thiếu
    # cả 5 route này; test hợp đồng tests/test_api_surface_contract.py bắt được.
    dependencies=[Depends(require_pg)],
    description="Applies a bounded optimistic preference patch and records consent changes atomically.",
)
async def update_my_preferences(
    response: Response,
    body: Any = Body(...),
    user=Depends(require_user),
    _csrf=Depends(require_csrf),
):
    from ratelimit import check_rate

    _require_rollout("PREFERENCE_PROFILE_V1")
    owner = str(user["id"])
    check_rate(
        f"preferences-patch:{owner}",
        PREFERENCE_PATCH_RATE_LIMIT,
        300,
        "Too many preference updates",
    )
    try:
        validated = PreferencePatchIn.model_validate(body)
    except ValidationError:
        raise HTTPException(422, "Invalid preference patch") from None
    values = validated.model_dump(exclude_unset=True)
    expected_revision = values.pop("revision")
    confirmation_token = values.pop("location_confirmation_token", None)
    try:
        confirmation = (
            verify_location_confirmation(confirmation_token, owner)
            if confirmation_token is not None
            else None
        )
        if (
            confirmation is not None
            and confirmation.preference_revision != expected_revision
        ):
            current = await asyncio.to_thread(load_preferences, owner)
            return JSONResponse(
                status_code=409,
                content=jsonable_encoder(current),
                headers={"Cache-Control": "no-store"},
            )
        confirmed_location = (
            confirmation.resolution if confirmation is not None else None
        )
        snapshot = await asyncio.to_thread(
            patch_preferences_with_consents,
            owner,
            values,
            expected_revision,
            confirmed_location=confirmed_location,
        )
    except PreferenceRevisionConflict:
        current = await asyncio.to_thread(load_preferences, owner)
        return JSONResponse(
            status_code=409,
            content=jsonable_encoder(_public_snapshot(current)),
            headers={"Cache-Control": "no-store"},
        )
    except (LocationConfirmationError, PreferenceValidationError):
        raise HTTPException(422, "Invalid preference patch") from None
    response.headers["Cache-Control"] = "no-store"
    return _public_snapshot(snapshot)


@router.get(
    "/me/preferences/consents",
    summary="Get current user preference consent history",
    # §1.3: route đòi đăng nhập PHẢI khai require_pg. Không có nó, chạy trên SQLite
    # sẽ nổ 500 lúc truy vấn bảng users thay vì trả 503 rõ ràng. Nhánh NP-1 thiếu
    # cả 5 route này; test hợp đồng tests/test_api_surface_contract.py bắt được.
    dependencies=[Depends(require_pg)],
    description="Returns bounded consent decisions without IP or location coordinates.",
)
async def get_my_preference_consents(
    response: Response, user=Depends(require_user)
):
    from ratelimit import check_rate

    _require_rollout("PREFERENCE_PROFILE_V1")
    owner = str(user["id"])
    check_rate(
        f"preferences-consents:{owner}",
        PREFERENCE_READ_RATE_LIMIT,
        300,
        "Too many preference requests",
    )
    response.headers["Cache-Control"] = "no-store"
    consents = await asyncio.to_thread(load_preference_consents, owner)
    return {"consents": consents}


@router.post(
    "/me/recommendations/reset",
    summary="Reset recommendation history",
    # §1.3: route đòi đăng nhập PHẢI khai require_pg. Không có nó, chạy trên SQLite
    # sẽ nổ 500 lúc truy vấn bảng users thay vì trả 503 rõ ràng. Nhánh NP-1 thiếu
    # cả 5 route này; test hợp đồng tests/test_api_surface_contract.py bắt được.
    dependencies=[Depends(require_pg)],
    description="Advances the recommendation cutoff without deleting workspace data.",
)
async def reset_my_recommendations(
    response: Response,
    user=Depends(require_user),
    _csrf=Depends(require_csrf),
):
    from ratelimit import check_rate

    _require_rollout("PREFERENCE_PROFILE_V1")
    owner = str(user["id"])
    check_rate(
        f"recommendations-reset:{owner}",
        RECOMMENDATION_RESET_RATE_LIMIT,
        3600,
        "Too many recommendation resets",
    )
    snapshot = await asyncio.to_thread(record_recommendation_reset, owner)
    response.headers["Cache-Control"] = "no-store"
    return _public_snapshot(snapshot)


@router.post(
    "/me/location/resolve",
    summary="Resolve current user location",
    # §1.3: route đòi đăng nhập PHẢI khai require_pg. Không có nó, chạy trên SQLite
    # sẽ nổ 500 lúc truy vấn bảng users thay vì trả 503 rõ ràng. Nhánh NP-1 thiếu
    # cả 5 route này; test hợp đồng tests/test_api_surface_contract.py bắt được.
    dependencies=[Depends(require_pg)],
    description="Returns a transient normalized region suggestion without persisting it.",
)
async def resolve_my_location(
    request: Request,
    response: Response,
    user=Depends(require_user),
    _csrf=Depends(require_csrf),
    reverse_geocoder: ReverseGeocoder = Depends(get_reverse_geocoder),
    ip_geocoder: IpGeocoder = Depends(get_ip_geocoder),
):
    from ratelimit import check_rate

    _require_rollout("LOCATION_RESOLVER_V1")
    owner = str(user["id"])
    check_rate(
        f"location-resolve:{owner}",
        LOCATION_RESOLVE_RATE_LIMIT,
        300,
        "Too many location resolution requests",
    )
    try:
        body = await request.json()
        validated = LocationResolveIn.model_validate(body)
        if validated.mode == "gps":
            if validated.latitude is None or validated.longitude is None:
                raise LocationInputError("Invalid location input")
            resolution = await asyncio.to_thread(
                resolve_gps,
                validated.latitude,
                validated.longitude,
                reverse_geocoder,
            )
        else:
            if validated.latitude is not None or validated.longitude is not None:
                raise LocationInputError("Invalid location input")
            resolution = await asyncio.to_thread(
                resolve_ip,
                get_client_ip(request),
                ip_geocoder,
            )
    except (LocationInputError, ValidationError, ValueError):
        raise HTTPException(422, "Invalid location input") from None
    response.headers["Cache-Control"] = "no-store"
    payload = asdict(resolution)
    preferences = await asyncio.to_thread(load_preferences, owner)
    confirmation_token = issue_location_confirmation(
        resolution, owner, preferences["revision"]
    )
    if confirmation_token is not None:
        payload["confirmation_token"] = confirmation_token
    return payload


@router.post("/me/events",
             status_code=202,
             dependencies=[Depends(require_pg)],
             summary="Track a user experience event",
             description="Stores a bounded first-party event for personalized recommendations. Requires login and CSRF.")
async def track_user_event(
    body: UserEventIn,
    response: Response,
    user=Depends(require_user),
    _csrf=Depends(require_csrf),
):
    """Ghi nhận một sự kiện trải nghiệm của user đang đăng nhập vào log sự kiện (HTTP 202).

    event_type ngoài danh sách trắng → 400; các trường text bị cắt ngắn; giới hạn 120 sự
    kiện/300 giây mỗi user. Bản ghi lưu hash IP rút gọn, không lưu IP thô.

    HỢP TỪ HAI NHÁNH. Cả `main` lẫn `codex/np1-identity-location-trust` đều định nghĩa
    hàm này và bản union thô để lọt hai `async def` trùng tên — bản sau âm thầm thắng,
    tức toàn bộ khâu làm sạch của main biến mất. Ruff F811 bắt được.

    NP-1 **thay hẳn kho lưu**: bỏ log JSONL trên đĩa (`USER_EVENTS_FILE`,
    `_log_user_event`, `_read_user_events`, `_safe_event_metadata` — nhánh xoá cả bốn)
    sang bảng Postgres qua `write_personalization_event`. Giữ hướng đó, đúng §1.1
    (DB là nguồn sự thật). KHÔNG ghi kép: file JSONL đã bị khai tử có chủ đích.

    Nhưng giữ lại khâu LÀM SẠCH của main, thứ bản NP-1 không có: lọc trắng
    `event_type`, cắt ngắn mọi trường text, kiểm `entity_id`. Đây là ranh giới đầu vào,
    mất nó thì client gửi gì cũng xuống thẳng DB.
    """
    from ratelimit import check_rate
    event_type = (body.event_type or "").strip().lower()
    if event_type not in _VALID_USER_EVENT_TYPES:
        raise HTTPException(400, "event_type khong hop le")
    body.event_type = event_type
    body.context = _clean_short_text(body.context, 40)
    if body.context and body.context not in _VALID_RECOMMENDATION_CONTEXTS and body.context != "search_submit":
        body.context = "home"
    if body.entity_id:
        body.entity_id = validate_path_id(body.entity_id, "entity_id")
    body.entity_type = _clean_short_text(body.entity_type, 60)
    body.area_id = _clean_short_text(body.area_id, 200)
    # CHỈ làm sạch các trường CÓ THẬT trên `UserEventIn` sau khi hợp NP-1.
    # Bản của main còn cắt ngắn `entity_name`, `area`, `query` — ba trường đó KHÔNG tồn
    # tại trên model của NP-1 (model đó đã thắng ở bước hợp, và nó hẹp hơn có chủ đích:
    # `extra="ignore"` nên client gửi thừa cũng bị bỏ). Giữ nguyên ba dòng cũ thì handler
    # nổ AttributeError ở MỌI sự kiện — agent/tests/test_qa_fixes.py bắt được.
    check_rate(f"user-event:{user['id']}", 120, 300, "Too many events")
    try:
        await asyncio.to_thread(
            write_personalization_event, str(user["id"]), body.model_dump()
        )
    except PersonalizationEventError:
        raise HTTPException(422, "Invalid personalization event") from None
    response.headers["Cache-Control"] = "no-store"
    return {"accepted": True}


@router.get("/me/insights",
            dependencies=[Depends(require_pg)],
            summary="Get current user interest profile",
            description="Returns lightweight interest, area, and next-action insights inferred from saved items, visits, and recent events.")
async def get_my_insights(response: Response, user=Depends(require_user)):
    """Hồ sơ quan tâm của user: interests, areas, types, recent_intents, next_actions, confidence, signal_count.

    Hồ sơ được suy ra từ sự kiện đã ghi và tín hiệu lưu/đánh dấu của user; đặt Cache-Control: no-store.
    """
    response.headers["Cache-Control"] = "no-store"
    profile = await asyncio.to_thread(_build_user_interest_profile, str(user["id"]))
    return {
        "interests": _project_public_profile_entries(profile.get("interests")),
        "areas": _project_public_profile_entries(profile.get("areas")),
        "types": _project_public_profile_entries(profile.get("types")),
        "signal_count": profile.get("signal_count", 0),
        "next_actions": _project_public_next_actions(profile),
    }


@router.get("/me/recommendations/contextual",
            dependencies=[Depends(require_pg)],
            summary="Get contextual user recommendations",
            description="Returns personalized entity recommendations with short reasons for a page context such as home, entity detail, search, saved, map, or itinerary.")
async def contextual_recommendations(
    request: Request,
    response: Response,
    context: str = Query("home", max_length=40),
    entity_id: Optional[str] = Query(None, max_length=200),
    q: str = Query("", max_length=200),
    limit: int = Query(6, ge=1, le=20),
    user=Depends(require_user),
):
    """Trả entity gợi ý kèm lý do ngắn cho một context trang của user đang đăng nhập.

    context ngoài danh sách hợp lệ bị ép về "home"; giới hạn 60 lượt/300 giây mỗi user;
    đặt Cache-Control: private, max-age=30.
    """
    from ratelimit import check_rate
    context = (context or "home").strip().lower()
    if context not in _VALID_RECOMMENDATION_CONTEXTS:
        context = "home"
    if entity_id:
        entity_id = validate_path_id(entity_id, "entity_id")
    q = (q or "").strip()[:200]
    check_rate(f"contextual-rec:{user['id']}", 60, 300, "Too many recommendation requests")
    response.headers["Cache-Control"] = "private, max-age=30"
    return await asyncio.to_thread(_contextual_recommendations, str(user["id"]), context, entity_id, q, limit)

import site_settings  # van dung tai cho khac trong file (seasonal_taglines override)

# Mien VAN HANH SITE cong khai (GET /site-settings + GET /announcements) sang
# agent/siteops/api.py (2026-08-29, lat 3 dot cat module). Tai xuat de bo test
# hien co van va duoc qua `public_api.<ten>` (getsource qua function object);
# router con mount o cuoi file, TRUOC _fix_route_order().
from siteops.api import get_site_settings, list_active_announcements  # noqa: F401
















def _first_entity_image(entity: dict) -> str:
    images = entity.get("images") or entity.get("image_urls") or []
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except (json.JSONDecodeError, ValueError, TypeError):
            images = []
    if isinstance(images, list):
        for item in images:
            if isinstance(item, str) and item:
                return item
            if isinstance(item, dict) and item.get("url"):
                return str(item["url"])
    image = entity.get("image")
    return str(image) if image else ""



def _compact_user_result(row: dict) -> dict:
    return {
        "id": str(row.get("id", "")),
        "display_name": row.get("display_name"),
        "avatar_url": row.get("avatar_url"),
        "username": row.get("username"),
        "post_count": int(row.get("post_count") or 0),
    }

def _search_posts_for_contract(q: str, user: dict | None, limit: int) -> tuple[list[dict], int]:
    if not db._use_pg or len((q or "").strip()) < 2:
        return [], 0
    from database import escape_like
    from community.api import (
        _POST_COLS, _block_sql, _mute_sql, _prod_seed_post_filter,
        _format_post, _enrich_all,
    )
    stripped = q.strip()
    ph = db._ph
    pattern = "%" + escape_like(stripped.lower()) + "%"
    bc, bc_p = _block_sql(user, "p.user_id")
    mc, mc_p = _mute_sql(user, "p.user_id")
    seed_filter, seed_params = _prod_seed_post_filter("p")
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT {_POST_COLS}, u.display_name, u.avatar_url, u.username,
                   e.name as entity_name, e.type as entity_type
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE p.moderation_status = 'approved' AND p.deleted_at IS NULL
              AND f_unaccent(lower(p.content)) LIKE f_unaccent({ph}) ESCAPE '\\'
              {bc} {mc} {seed_filter}
            ORDER BY p.created_at DESC
            LIMIT {ph}
        """, (pattern, *bc_p, *mc_p, *seed_params, limit))
        total_row = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM posts p
            WHERE p.moderation_status = 'approved' AND p.deleted_at IS NULL
              AND f_unaccent(lower(p.content)) LIKE f_unaccent({ph}) ESCAPE '\\'
              {bc} {mc} {seed_filter}
        """, (pattern, *bc_p, *mc_p, *seed_params))
    posts = [_format_post(db._row_to_dict(r)) for r in rows]
    try:
        _enrich_all(posts, user)
    except Exception:
        logger.debug("search post enrich failed", exc_info=True)
    total = db._row_to_dict(total_row)["c"] if total_row else 0
    return posts, int(total or 0)

def _search_users_for_contract(q: str, user: dict | None, limit: int) -> tuple[list[dict], int]:
    if not db._use_pg or len((q or "").strip()) < 2:
        return [], 0
    from database import escape_like
    from community.api import _block_sql, _mute_sql
    stripped = q.strip()
    ph = db._ph
    pattern = "%" + escape_like(stripped.lower()) + "%"
    bc, bc_p = _block_sql(user)
    mc, mc_p = _mute_sql(user, "u.id")
    params: list = [pattern] + bc_p + mc_p + [limit]
    count_params: list = [pattern] + bc_p + mc_p
    with db._conn() as conn:
        total_row = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM users u
            WHERE u.is_active = TRUE AND u.deleted_at IS NULL AND u.display_name IS NOT NULL
              AND f_unaccent(lower(u.display_name)) LIKE f_unaccent({ph}) ESCAPE '\\'
              {bc} {mc}
        """, tuple(count_params))
        rows = db._fetchall(conn, f"""
            SELECT u.id, u.display_name, u.avatar_url, u.username,
                   COUNT(p.id) AS post_count
            FROM users u
            LEFT JOIN posts p ON p.user_id = u.id AND p.moderation_status = 'approved' AND p.deleted_at IS NULL
            WHERE u.is_active = TRUE AND u.deleted_at IS NULL AND u.display_name IS NOT NULL
              AND f_unaccent(lower(u.display_name)) LIKE f_unaccent({ph}) ESCAPE '\\'
              {bc} {mc}
            GROUP BY u.id, u.display_name, u.avatar_url, u.username
            ORDER BY post_count DESC, u.display_name
            LIMIT {ph}
        """, tuple(params))
    users = [_compact_user_result(db._row_to_dict(r)) for r in rows if db._row_to_dict(r).get("display_name")]
    total = db._row_to_dict(total_row)["c"] if total_row else 0
    return users, int(total or 0)










@router.get("/areas", response_model=AreasResponse,
            summary="List areas with places",
            description="Returns all administrative areas grouped with their places (wards/communes). Cached for 1 hour.")
async def list_areas(response: Response):
    """LUÔN trả về danh sách rỗng ở bản hiện tại — endpoint đang hỏng, không phải theo thiết kế.

    Ý định là gom entity type=place theo `area`, nhưng nó gọi
    `db.list_entities(entity_type="place", ...)` mà hàm đó có điều kiện cứng
    `e.type != 'place'` (database.py:1122). Hai điều kiện loại trừ nhau nên truy vấn
    luôn rỗng, dù DB có 125 entity type=place. Test hiện có chỉ assert cấu trúc
    (200 + có khoá) nên bug lọt lưới. Frontend không gọi endpoint này.
    """
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    def _query():
        # KHÔNG dùng db.list_entities(entity_type="place"): hàm đó loại cứng
        # `e.type != 'place'` nên hai điều kiện loại trừ nhau và truy vấn LUÔN
        # rỗng — endpoint này chết im lặng cho tới 2026-08-06. Lọc từ
        # all_entities() và áp đúng luật công khai của _append_public_only.
        places = [
            e for e in db.all_entities()
            if e.get("type") == "place"
            and e.get("status") != "provisional"
            and e.get("verified") is not False
        ][:1000]
        areas: dict[str, list] = {}
        for p in places:
            area = p.get("area", "")
            if area not in areas:
                areas[area] = []
            areas[area].append({"id": p["id"], "name": p["name"]})
        return [{"area": k, "places": v, "count": len(v)} for k, v in sorted(areas.items())]
    result = await asyncio.to_thread(_query)
    return {"areas": result, "total_places": sum(a["count"] for a in result)}














@router.get("/facilities",
            summary="List public facilities",
            description="Returns administrative facilities (government offices, police, etc.) for a given ward/commune. Cached for 1 hour.")
async def list_facilities(response: Response, place: Optional[str] = Query(None, max_length=100)):
    """GĐ13.4: danh bạ hành chính — cơ quan công vụ (UBND/công an/...) theo xã/phường."""
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    facilities = await asyncio.to_thread(_public_facilities_by_place, place)
    return {"facilities": facilities}


# Nhóm loại entity cho trang hub xã/phường (theo 4 mục người dùng cần).




_DAY_PLAN_TYPE_PRIORITY = [
    "attraction", "nature", "history", "experience", "craft_village",
    "dish", "drink", "product", "market", "accommodation", "event",
]










# Mien LICH TRINH (3 route public /itineraries* + cum validation/schedule/serialize)
# sang itineraries/api.py (2026-08-29, lat 2 dot cat module) — mount lai vao router
# nay o cuoi file, TRUOC _fix_route_order(), nhu mien entity.


def _normalize_text(value: Any) -> str:
    """Accent-insensitive fold for lexical ranking (delegates to _fold_text; đ→d for VN)."""
    return _fold_text(value).replace("đ", "d")


def _name_match_score(name: str, qn: str, terms: list[str]) -> tuple[float, str] | None:
    if qn and name == qn:
        return 100.0, "exact_name"
    if qn and name.startswith(qn):
        return 80.0, "name_prefix"
    if terms and all(term in name for term in terms):
        return 65.0, "name_terms"
    if qn and qn in name:
        return 55.0, "name_contains"
    return None


def _lexical_match_score(name: str, summary: str, qn: str, terms: list[str]) -> tuple[float, str]:
    name_match = _name_match_score(name, qn, terms)
    if name_match is not None:
        return name_match
    if terms and all(term in summary for term in terms):
        return 35.0, "summary_terms"
    return 0.0, "confidence"


def _rank_search_entities(items: list[dict], query: str) -> list[dict]:
    from search_contract import _rank as canonical_rank
    ranked = []
    for idx, item in enumerate(items):
        match = canonical_rank(item, query)
        if match is None:
            score, reason = 0.0, "confidence"
        else:
            score, reason = match
        score += float(item.get("confidence") or 0) * 0.01
        copy = dict(item)
        copy["_search_meta"] = {"score": round(score, 2), "reason": reason, "rank_source": "lexical", "ranking_version": "search-v1"}
        ranked.append((score, idx, copy))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _score, _idx, item in ranked]

@router.get("/search", response_model=SearchResponse,
            summary="Unified public search",
            description="Searches entities, community posts, and users with one contract. Keeps legacy results/total fields for existing clients.")
async def search(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=1, max_length=200),
    type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    user=Depends(get_current_user),
):
    """Tìm hợp nhất entity + bài viết + người dùng cho một truy vấn, kèm suggestions và totals.

    Giới hạn 30 lượt/60 giây theo IP; q bị bỏ thẻ HTML trước khi tìm post/user và trước khi
    ghi log truy vấn. Trường results giữ lại cho client cũ, trùng nội dung với entities.
    """
    from ratelimit import check_rate
    check_rate(f"search:{get_client_ip(request)}", 30, 60, "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
    offset = coerce_query_int(offset, 0)
    limit = coerce_query_int(limit, 20)
    entity_limit = min(limit, 100)
    safe_q = re.sub(r"<[^>]+>", "", q)
    social_limit = min(max(3, limit // 3), 10)
    page = await asyncio.to_thread(
        search_public_entities,
        safe_q,
        offset=offset,
        limit=entity_limit,
        filters=SearchFilters(entity_type=type, area=area, public_only=True),
    )
    results = page.items
    await asyncio.to_thread(_enrich_place, results)
    results = [_project_public_entity_media(entity) for entity in results]
    total = page.total
    posts, post_total = await asyncio.to_thread(_search_posts_for_contract, safe_q, user, social_limit)
    users, user_total = await asyncio.to_thread(_search_users_for_contract, safe_q, user, social_limit)
    suggestions = [
        {"kind": "entity", "id": e.get("id"), "label": e.get("name"), "type": e.get("type"), "to": f"/dia-diem/{e.get('id')}"}
        for e in results[:5]
    ] + [
        {"kind": "post", "id": p.get("id"), "label": (p.get("content") or "")[:80], "type": p.get("post_type"), "to": f"/bai-viet/{p.get('id')}"}
        for p in posts[:3]
    ] + [
        {"kind": "user", "id": u.get("username") or u.get("id"), "label": u.get("display_name"), "type": "user", "to": f"/nguoi-dung/{u.get('username') or u.get('id')}"}
        for u in users[:3]
    ]
    await asyncio.to_thread(_log_search_query, safe_q, type, area, total)
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=10"
    return {
        "q": safe_q,
        "total": total,
        "offset": page.offset,
        "limit": page.limit,
        "truncated": page.truncated,
        "ranking_version": page.ranking_version,
        "results": results,
        "entities": results,
        "posts": posts,
        "users": users,
        "suggestions": suggestions[:12],
        "totals": {"entities": total, "posts": post_total, "users": user_total},
        "filters": {"q": safe_q, "type": type, "area": area, "limit": limit},
    }


@router.get("/autocomplete", response_model=AutocompleteResponse,
            summary="Autocomplete entity names",
            description="Lightweight typeahead suggestions for entity name search. Returns id, name, type, and place for up to 8 matches.")
async def autocomplete(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=1, max_length=100),
    type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(8, ge=1, le=20),
):
    """Lightweight typeahead for entity name search."""
    from ratelimit import check_rate
    check_rate(f"autocomplete:{get_client_ip(request)}", 60, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    limit = coerce_query_int(limit, 8)
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    class _AutocompleteCatalog:
        def list_entities(self, **kwargs):
            return db.search_entities(
                q=q,
                entity_type=type,
                limit=kwargs.get("limit", limit),
                offset=0,
                public_only=True,
            )

        def count_entities_filtered(self, **kwargs):
            return db.count_entities_filtered(
                q=q, entity_type=type, public_only=True,
            )

    page = await asyncio.to_thread(
        search_public_entities,
        q,
        offset=0,
        limit=limit,
        filters=SearchFilters(entity_type=type, public_only=True),
        database=_AutocompleteCatalog(),
    )
    results = page.items
    return {
        "suggestions": [
            {"id": e["id"], "name": e["name"], "type": e.get("type", ""),
             "place": e.get("place", "")}
            for e in results
        ],
        "total": page.total,
        "offset": page.offset,
        "limit": page.limit,
        "truncated": page.truncated,
        "ranking_version": page.ranking_version,
    }


# GET /api/me/activity sống ở social.py (router UGC có guard require_pg).
# Bản trùng từng nằm ở đây thắng thứ tự đăng ký nhưng lại không có guard đó,
# nên chế độ SQLite ném 500 thay vì 503, và payload của nó không khớp client.

PUBLIC_STATS_FIELDS = (
    "entities",
    "places",
    "relationships",
    "itineraries",
    "feedback_entries",
    "query_log_entries",
)


@router.get("/stats", response_model=StatsResponse,
            summary="Get public stats",
            description="Returns aggregate platform statistics. Cached for 5 minutes.",
            openapi_extra={
                "x-auth": "none",
                "x-scope": "public:read",
                "x-csrf": False,
            })
async def public_stats(response: Response):
    """Return only the stable public aggregate projection; never expose topology."""
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    stats = await asyncio.to_thread(db.stats)
    return {key: stats.get(key, 0) for key in PUBLIC_STATS_FIELDS}


# ── Homepage curated feed ──────────────────────────────────────────

_TOURISM_TYPES = {"experience", "attraction", "dish", "nature", "craft_village",
                  "history", "accommodation", "event"}


def _parse_event_iso_date(attrs: dict, *keys: str):
    for key in keys:
        raw = attrs.get(key)
        if not raw:
            continue
        try:
            return datetime.strptime(str(raw), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
    return None

def _event_is_past(e: dict) -> bool:
    """True if an event's reliable end/start date is already passed."""
    attrs = e.get("attributes") or {}
    event_date = _parse_event_iso_date(attrs, "date_end_iso", "date_end", "date_start_iso", "date_start")
    if not event_date:
        return False
    # Giờ VN, không phải UTC: máy chủ chạy UTC nên từ 17:00Z tới nửa đêm, ngày
    # dương ở Việt Nam đã sang hôm sau. Lấy UTC thì một lễ hội KẾT THÚC hôm qua
    # (giờ VN) vẫn được tính là chưa qua, suốt 7 tiếng mỗi ngày.
    return event_date < _today_vietnam().date()


_GENERIC_NAMES = {"tắm sông", "đi ghe", "đi đò", "tham quan", "du lịch",
                   "ăn uống", "mua sắm", "chụp ảnh", "câu cá", "dạo phố"}


def _homepage_score(e: dict, month: int) -> float:
    from smart_rank import smart_score
    s = smart_score(e, month=month, q_match_level="none")
    if _public_entity_has_media(e):
        s += 2.0
    if len(e.get("summary", "") or "") > 80:
        s += 1.0
    if e["name"].lower().strip() in _GENERIC_NAMES:
        s -= 5.0
    return s


def _name_key(name: str) -> str:
    """Normalize name for dedup: lowercase, strip common prefixes/suffixes."""
    import re
    n = name.lower().strip()
    n = re.sub(r"^(hái|mùa|tham quan|khu du lịch|làng nghề)\s+", "", n)
    n = re.sub(r"\s+(tại|ở|cù lao|cồn)\s+.*$", "", n)
    return n


def _dedup_by_name(entities: list[dict], limit: int) -> list[dict]:
    """Pick top entities, skipping near-duplicate names and same placeId."""
    result = []
    seen_keys: set[str] = set()
    seen_place_ids: set[str] = set()
    for e in entities:
        nk = _name_key(e["name"])
        pid = e.get("placeId") or ""
        if any(nk in sk or sk in nk for sk in seen_keys if len(nk) > 3 and len(sk) > 3):
            continue
        if pid and pid in seen_place_ids:
            continue
        result.append(e)
        seen_keys.add(nk)
        if pid:
            seen_place_ids.add(pid)
        if len(result) >= limit:
            break
    return result


def _diverse_should_skip(e, t, a, nk, pid, type_counts, area_counts, seen_keys,
                         seen_place_ids, exclude_ids, max_per_type, max_per_area) -> bool:
    if exclude_ids and e["id"] in exclude_ids:
        return True
    if type_counts.get(t, 0) >= max_per_type:
        return True
    if area_counts.get(a, 0) >= max_per_area:
        return True
    if any(nk in sk or sk in nk for sk in seen_keys if len(nk) > 3 and len(sk) > 3):
        return True
    if pid and pid in seen_place_ids:
        return True
    return False


def _diverse_pick(entities: list[dict], max_per_type: int = 2,
                  max_per_area: int = 4, limit: int = 8,
                  exclude_ids: set | None = None) -> list[dict]:
    result = []
    type_counts: dict[str, int] = {}
    area_counts: dict[str, int] = {}
    seen_keys: set[str] = set()
    seen_place_ids: set[str] = set()
    for e in entities:
        t = e["type"]
        a = e.get("place_area") or "unknown"
        nk = _name_key(e["name"])
        pid = e.get("placeId") or ""
        if _diverse_should_skip(e, t, a, nk, pid, type_counts, area_counts, seen_keys,
                                seen_place_ids, exclude_ids, max_per_type, max_per_area):
            continue
        result.append(e)
        type_counts[t] = type_counts.get(t, 0) + 1
        area_counts[a] = area_counts.get(a, 0) + 1
        seen_keys.add(nk)
        if pid:
            seen_place_ids.add(pid)
        if len(result) >= limit:
            break
    return result


def _entity_in_season(e: dict, month: int) -> bool:
    s = e.get("season")
    if not s or not isinstance(s, dict):
        return False
    months = s.get("months") or []
    if len(months) >= 11:
        return False
    return month in months or month in (s.get("peak") or [])


def _select_upcoming_events(public: list[dict], today, cutoff) -> list[dict]:
    upcoming_pool = []
    for e in public:
        if e["type"] != "event":
            continue
        attrs = e.get("attributes") or {}
        cat = attrs.get("category", "")
        if cat == "mua":
            continue
        ds = attrs.get("date_start")
        if not ds:
            continue
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        # Skip if month field set but conflicts with date_start (fabricated date)
        attr_month = attrs.get("month")
        if attr_month and isinstance(attr_month, (int, float)) and int(attr_month) != d.month:
            continue
        if today <= d <= cutoff:
            e["_days_until"] = (d - today).days
            upcoming_pool.append(e)
    upcoming_pool.sort(key=lambda x: x.get("_days_until", 999))
    return upcoming_pool[:3]


def _score_one_itinerary(it: dict, public_by_id: dict, month: int) -> float:
    it_score = 0.0
    stops = it.get("stops") or []
    for stop in stops:
        eid = _itinerary_stop_entity_id(stop)
        matched = public_by_id.get(eid)
        if matched:
            if _entity_in_season(matched, month):
                it_score += 2.0
            if _public_entity_has_media(matched):
                it_score += 0.5
    dur = it.get("duration") or ""
    if dur:
        m = re.search(r"(\d+)", str(dur))
        if m:
            try:
                d = int(m.group(1))
                if 1 <= d <= 3:
                    it_score += 1.0
            except (ValueError, TypeError):
                pass
    return it_score


def _pick_diverse_itineraries(all_itineraries: list[dict]) -> tuple[list[dict], set[str]]:
    seen_areas: set[str] = set()
    selected_itinerary_ids: set[str] = set()
    itineraries: list[dict] = []
    for it in all_itineraries:
        coverage = _itinerary_coverage_areas(it)
        if coverage and coverage <= seen_areas and len(itineraries) < 3:
            continue
        itineraries.append(it)
        if it.get("id"):
            selected_itinerary_ids.add(str(it["id"]))
        seen_areas.update(coverage)
        if len(itineraries) >= 4:
            break
    return itineraries, selected_itinerary_ids


def _fill_remaining_itineraries(itineraries: list[dict], all_itineraries: list[dict], selected_itinerary_ids: set[str]) -> None:
    if len(itineraries) >= 4:
        return
    for it in all_itineraries:
        if it.get("id") and str(it["id"]) in selected_itinerary_ids:
            continue
        itineraries.append(it)
        if len(itineraries) >= 4:
            break


def _select_homepage_itineraries(all_itineraries: list[dict], public: list[dict], month: int) -> list[dict]:
    public_by_id = {e["id"]: e for e in public}  # index O(1) thay vì quét tuyến tính public mỗi stop
    for it in all_itineraries:
        it["stops"] = _public_itinerary_stops(it.get("stops", []), public_by_id)
        it["_score"] = _score_one_itinerary(it, public_by_id, month)
    all_itineraries.sort(key=lambda x: x.get("_score", 0), reverse=True)
    itineraries, selected_itinerary_ids = _pick_diverse_itineraries(all_itineraries)
    _fill_remaining_itineraries(itineraries, all_itineraries, selected_itinerary_ids)
    for it in itineraries:
        it.pop("_score", None)
    return itineraries


def _compute_homepage_area_counts(public: list[dict]) -> dict[str, int]:
    card_types = {"product", "dish", "drink", "experience", "attraction", "nature",
                  "craft_village", "history", "accommodation", "event"}
    area_counts: dict[str, int] = {}
    for e in public:
        a = e.get("place_area") or e.get("area")
        if e["type"] in card_types and a:
            area_counts[a] = area_counts.get(a, 0) + 1
    return area_counts


_HOMEPAGE_TAGLINES = {
    1: "Sắc xuân Vĩnh Long bên sông và vườn Tết",
    2: "Đầu xuân ghé vườn, thử đặc sản mới",
    3: "Tháng lễ hội đình làng và nếp xưa Nam Bộ",
    4: "Chôl Chnăm Thmây rộn ràng phum sóc",
    5: "Trái ngọt đầu mùa, hành trình miệt vườn bắt đầu",
    6: "Vườn chín rộ, đặc sản địa phương lên hương",
    7: "Mùa miệt vườn đang mở cửa",
    8: "Vu Lan bên sông, chùa cổ và món chay",
    9: "Trung thu miền Tây, đèn lồng và bánh dân gian",
    10: "Ok Om Bok rộn ràng, ghe ngo trên dòng nước",
    11: "Cuối năm ghé làng nghề, chọn quà đặc sản",
    12: "Mùa Tết đang về, tìm quà ngon Vĩnh Long",
}


def _resolve_seasonal_tagline(month: int) -> str:
    # A7: admin can override taglines via site_settings (homepage.seasonal_taglines:
    # a {"<month>": "<text>"} object). Falls back to defaults; {} on SQLite.
    seasonal_tagline = ""
    try:
        _ov = site_settings.get_all_public().get("homepage.seasonal_taglines")
        if isinstance(_ov, dict):
            seasonal_tagline = _ov.get(str(month)) or _ov.get(month) or ""
    except Exception:
        logger.warning("Failed to load seasonal taglines override", exc_info=True)
        seasonal_tagline = ""
    if not seasonal_tagline:
        seasonal_tagline = _HOMEPAGE_TAGLINES.get(month, "Khám phá Vĩnh Long theo cách của người bản địa")
    return seasonal_tagline


def _select_top_dishes(public: list[dict]) -> list[dict]:
    dishes_pool = [e for e in public
                   if e["type"] == "dish"
                   and isinstance((e.get("attributes") or {}).get("rating"), (int, float))
                   and (e.get("attributes") or {}).get("review_count", 0) >= 3]
    dishes_pool.sort(key=lambda e: (
        (e.get("attributes") or {}).get("rating", 0),
        (e.get("attributes") or {}).get("review_count", 0),
    ), reverse=True)
    return _dedup_by_name(dishes_pool, limit=6)


def _build_homepage_trending(public: list[dict]) -> list[dict]:
    from proactive import get_trending_entities
    trending_raw = get_trending_entities(limit=6)
    trending = []
    for t in trending_raw:
        ent = next((e for e in public if e["id"] == t["id"]), None)
        if ent:
            item = {k: ent[k] for k in ("id", "name", "type", "summary", "images", "place_name", "place_area") if k in ent}
            item["hit_count"] = t["hit_count"]
            trending.append(item)
    return trending


def _homepage_cache_hit(month: int) -> dict | None:
    _now = _time.time()
    cache_fresh = (_homepage_cache["data"] is not None and _homepage_cache["month"] == month
                   and _now - _homepage_cache["ts"] < _HOMEPAGE_TTL)
    if cache_fresh:
        return _homepage_cache["data"]
    if _homepage_lock.locked() and _homepage_cache["data"] is not None:
        return _homepage_cache["data"]
    return None



# ── «Tin chính đặc sản»: chọn MỘT sản phẩm dựng lớn cho trang chủ ──────────
# Luật TẤT ĐỊNH, chạy từ dữ liệu — thay cho giả định "chủ dự án chọn tay
# shortlist": AdminCP không có màn nào để chọn, nên chọn-tay nghĩa là mỗi lần
# đổi tin chính phải sửa mã + deploy.
#
# KHÔNG gọi smart_score/_homepage_score: hai hàm đó cộng popularity_score()
# đọc agent/data/analytics.json (smart_rank.py:145), biến động theo lượt bấm
# và tự nạp lại mỗi 300s — tin chính sẽ lật giữa tháng. Bug đó VÔ HÌNH ở local
# (chỉ 3 entity có hit) nhưng bonus tới +3.0 trên prod, thừa sức đảo thứ tự.
# Mục nhạy-với-độ-quan-tâm đã có sẵn và đúng vai: trending[].

_PRODUCT_LEAD_BLOCKLIST = frozenset({
    # type=product nhưng thực chất là TỔ CHỨC / ĐIỂM BÁN — gắn nhầm type, không
    # phải kiểm duyệt nội dung. Khoá bằng ID chứ không regex tên: regex bắt hụt
    # tên lai ("Kẹo dừa Mỏ Cày (cơ sở Tuyết Phụng)"), mà nới regex thì giết oan
    # "Cá phi sả ớt Thạnh Phước" (summary có nhắc HTX sản xuất).
    "htx-thuy-san-sinh-thai-thanh-phuoc",
    "cua-hang-ocop-vung-liem",
    "diem-trung-bay-va-ban-san-pham-ocop-vinh-long-tai-ben-cang",
    "diem-trung-bay-va-gioi-thieu-san-pham-ocop-vinh-long",
    "hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop",
    "hop-tac-xa-cam-phuong-thuy",
    "keo-dua-mo-cay-co-so-tuyet-phung",
    "rau-thom-ocop-hop-tac-xa-phuoc-hau",
    "banh-trang-ngot-le-hang-htx-banh-trang-cu-lao-may",
})

# Trần cứng cho ba truy vấn QUÉT TOÀN KHO. Chúng không phân trang: hàm gọi lấy
# một lát rồi tự xếp hạng/lọc, nên khi kho vượt trần thì phần dôi ra biến mất
# LẶNG LẼ — không lỗi, không log, chỉ là vài entity không bao giờ lên trang, và
# không ai biết để đi tìm.
#
# Đo 2026-08-27: 1746 entity, 67 event — còn dư ~2,9 lần. Nhưng "còn dư" là
# trạng thái tạm thời, và cái nguy hiểm không phải con số mà là sự IM LẶNG.
# Nâng trần không giải quyết gì: trần nào rồi cũng có ngày chạm, và lúc đó vẫn
# im như cũ. Nên giữ trần (an toàn bộ nhớ) + nói ra khi chạm.




_LEAD_MIN_SUMMARY = 120     # ngắn hơn thì khối dựng lớn trống trải
_LEAD_MAX_SUMMARY = 400     # dài hơn thì kẹp 2 dòng cắt giữa ý
_LEAD_MAX_NAME = 42         # dài hơn thì vỡ dòng ở cỡ chữ tin chính

_RE_STALE_LEVEL = re.compile(r"\bhuyen\b", re.IGNORECASE)
_RE_STALE_PROVINCE = re.compile(r"(ben\s*tre|tra\s*vinh)", re.IGNORECASE)
# Dấu lịch sử dò trên chuỗi CÒN DẤU, không dò trên chuỗi đã bỏ dấu. Bản đầu là
# r"\b(cu|truoc)\b" chạy SAU khi bỏ dấu, nên mọi âm tiết cù/củ/cú/cứ/cụ/cư đều
# thành token "cu" và được tính là đã ghi "cũ" — cổng §1.6 fail-OPEN. Đo trên
# web/data.json: 8 entity gọi Bến Tre/Trà Vinh trần vẫn qua cổng, được cứu bởi
# những chữ chẳng liên quan: "cù lao An Bình", "Trà Cú", "Cứ mười con còng".
#
# "truoc" không dấu vẫn nhận vì nó không đụng chữ nào khác; "cu" không dấu thì
# KHÔNG, vì nó chính là cái lỗ. Văn bản viết không dấu sẽ bị coi là thiếu dấu
# lịch sử — fail-CLOSED, đúng hướng an toàn của §1.6: thà loại oan một entity
# lành còn hơn dựng lớn một cái tên gọi tỉnh cũ như đang tồn tại.
# Chữ "cũ" TRẦN chỉ được tính khi nó BÁM NGAY SAU tên tỉnh ("Trà Vinh (cũ)",
# "Bến Tre cũ"). Cửa sổ ±40 rộng rãi để lọt ba ca thật, trong đó dấu thuộc về
# một danh từ KHÁC:
#   nem-nuong-thanh-binh-ben-tre  "bến phà Hàm Luông (cũ), TP. Bến Tre"
#   sieu-thi-go-big-c-ben-tre     "chuỗi GO! (trước đây là Big C)"
#   song-co-chien-vinh-long       "…và Trà Vinh trước khi đổ ra Biển Đông"
# Cả ba đều gọi tỉnh cũ TRẦN mà vẫn qua cổng.
_RE_MARKER_SAU_TINH = re.compile(r"^\W{0,3}cũ\b", re.IGNORECASE)

# Cụm chỉ-đích-danh việc sáp nhập thì được tính ở BẤT KỲ đâu trong cửa sổ, vì
# chúng không thể mang nghĩa nào khác — cho phép lối viết đặt mốc trước tên tỉnh
# ("trước 7-2025 thuộc tỉnh Trà Vinh"). Chữ "trước" TRẦN thì KHÔNG: nó là từ
# thường gặp bậc nhất ("phía trước", "trước khi", "trước đây").
_RE_MOC_SAP_NHAP = re.compile(
    r"trước\s+(?:7[-/. ]*2025|tháng\s*7|khi\s+sáp\s+nhập|sáp\s+nhập)"
    r"|truoc\s+(?:7[-/. ]*2025|thang\s*7|khi\s+sap\s+nhap|sap\s+nhap)"
    r"|(?:sau|từ)\s+(?:khi\s+)?sáp\s+nhập",
    re.IGNORECASE)


def _fold_ascii(value: str) -> str:
    """Bỏ dấu để so chuỗi, BẢO TOÀN ĐỘ DÀI 1:1 với chuỗi gốc.

    Độ dài 1:1 không phải chi tiết trang trí: `_has_stale_geography` tìm tên
    tỉnh trên chuỗi bỏ dấu rồi soi cửa sổ ±40 trên chuỗi GỐC ở CÙNG chỉ số.
    Lệch một ký tự là cắt trượt cửa sổ.

    Tách riêng đ/Đ vì NFD KHÔNG tách được chữ này.
    """
    out = []
    for ch in unicodedata.normalize("NFC", value):
        if ch == "đ":
            out.append("d")
            continue
        if ch == "Đ":
            out.append("D")
            continue
        base = "".join(c for c in unicodedata.normalize("NFD", ch)
                       if unicodedata.category(c) != "Mn")
        # Ký tự nào bỏ dấu ra khác 1 ký tự thì giữ nguyên, để không phá thế 1:1.
        out.append(base if len(base) == 1 else ch)
    return "".join(out)


def _has_stale_geography(entity: dict) -> bool:
    """§1.6: cấp 'huyện' đã bỏ, và tên tỉnh cũ gọi như đang tồn tại.

    Cửa sổ ±40 ký tự quanh tên tỉnh để tìm dấu 'cũ'/'trước' là BẮT BUỘC, không
    phải trang trí: "tỉnh Trà Vinh (cũ)" là cách viết ĐÚNG chuẩn và sẽ bị giết
    oan nếu chỉ chặn chuỗi trần.
    """
    raw = f"{entity.get('name', '')} {entity.get('summary') or ''}"
    flat = _fold_ascii(raw)   # cùng độ dài nên chỉ số dùng chung được
    if _RE_STALE_LEVEL.search(flat):
        return True
    for match in _RE_STALE_PROVINCE.finditer(flat):
        # Tìm TỈNH trên chuỗi bỏ dấu (bắt được cả "Ben Tre" viết không dấu),
        # nhưng tìm DẤU LỊCH SỬ trên chuỗi còn dấu (để "cù" không giả làm "cũ").
        ngay_sau = raw[match.end(): match.end() + 16]
        cua_so = raw[max(0, match.start() - 40): match.end() + 40]
        if not (_RE_MARKER_SAU_TINH.search(ngay_sau) or _RE_MOC_SAP_NHAP.search(cua_so)):
            return True
    return False


def _lead_ocop_star(entity: dict) -> int:
    """Điểm OCOP cho việc CHỌN MỒI trang chủ — không phải để lộ hạng ra ngoài.

    Bản cũ là bản sao THỨ BA của luật rút hạng, kèm chính lỗi bắt chữ số đầu
    tiên ở bất kỳ đâu trong chuỗi. Nay uỷ quyền cho `ocop.ocop_tier`.

    Vẫn giữ nấc "có chứng nhận nhưng chưa rõ hạng = 1": đây là thiết bị XẾP
    HẠNG (sản phẩm có chứng nhận phải đứng trên sản phẩm không có), không phải
    lời khai hạng. Đổi nó thành 0 sẽ đổi cả cách chọn mồi trang chủ.
    """
    tier = ocop_tier(entity)
    if tier:
        return tier
    return 1 if is_ocop_certified(entity) else 0


def _lead_rank_key(entity: dict) -> tuple:
    """Sao OCOP giảm dần → summary dài dần → id (khoá phá hoà, giữ tất định)."""
    return (-_lead_ocop_star(entity),
            -len((entity.get("summary") or "").strip()),
            entity["id"])


def _lead_is_year_round(entity: dict) -> bool:
    """Cùng quy ước với _entity_in_season: months >= 11 nghĩa là quanh năm."""
    season = entity.get("season")
    months = (season.get("months") or []) if isinstance(season, dict) else []
    return len(months) >= 11 or not months


def _product_lead_eligible(entity: dict) -> bool:
    if entity.get("type") != "product":
        return False
    if entity["id"] in _PRODUCT_LEAD_BLOCKLIST:
        return False
    if not _public_entity_has_media(entity):
        return False
    if _has_stale_geography(entity):
        return False
    if len(entity.get("name") or "") > _LEAD_MAX_NAME:
        return False
    summary_len = len((entity.get("summary") or "").strip())
    return _LEAD_MIN_SUMMARY <= summary_len <= _LEAD_MAX_SUMMARY


def _select_product_lead(public: list[dict], month: int,
                         exclude_ids: set[str]) -> dict | None:
    """MỘT sản phẩm dựng lớn cho mục «Tin chính đặc sản», hoặc None.

    Cùng snapshot dữ liệu + cùng tháng ⇒ cùng kết quả, không phụ thuộc lượt
    bấm, giờ chạy, hay thứ tự hàng DB trả về.

    Mùa KHÔNG dùng làm điều kiện lọc mà làm THỨ TỰ ƯU TIÊN giữa ba túi: lọc
    theo mùa cho 3/12 tháng rỗng lead, vì _entity_in_season trả False cho hàng
    quanh năm (months >= 11) kể cả khi `peak` khớp tháng.

    Vòng xoay theo tháng là thứ thay cho "chọn tay": kho ứng viên nhỏ (đo local:
    218 product → 19 có ảnh → 9 đủ điều kiện) nên mọi khoá thuần-điểm đều
    degenerate về một entity duy nhất suốt 12 tháng.
    """
    pool = [e for e in public
            if _product_lead_eligible(e) and e["id"] not in exclude_ids]
    if not pool:
        return None
    in_season = sorted((e for e in pool if _entity_in_season(e, month)),
                       key=_lead_rank_key)
    year_round = sorted((e for e in pool if _lead_is_year_round(e)),
                        key=_lead_rank_key)
    relaxed = sorted(pool, key=_lead_rank_key)
    for ring in (in_season, year_round, relaxed):
        if ring:
            return ring[(month - 1) % len(ring)]
    return None


def _mark_signal_lead(upcoming_events: list[dict], seasonal: list[dict]) -> None:
    """Gắn `signal_lead_ok` cho MỌI hàng ĐƯỢC PHÉP dựng ảnh — không chọn ai.

    Chia vai có chủ đích, vì mỗi tầng chỉ biết được một nửa:

    * Backend biết ĐIỀU KIỆN: hàng có ảnh thật không, tên có còn mang địa danh
      cũ trần không (§1.6). Dùng lại `_has_stale_geography` đã có test — hai
      bản của cùng một luật thì chỉ một bản được sửa khi luật đổi.
    * Frontend biết AI CÒN SỐNG: `homeNocturnePresentation` loại các entity đã
      bị hero/spotlight/quick-decision tiêu thụ, nên hàng backend chấm có thể
      không bao giờ hiện. Đã đo đúng bẫy này: `vuon-dua-sinh-thai-cau-ke-tra-vinh`
      được chấm nhưng bị mục "Đang vào mùa" ăn mất, trang ra 0 tin dẫn.

    Chạy SAU `_project_public_entity_media_sections` vì trước đó chưa có
    `image_descriptors` để biết hàng nào thật sự có ảnh.

    Bìa sinh KHÔNG bao giờ đủ điều kiện: nó là mảng bão hoà nhất mục mà mang 0
    thông tin, và nó cướp trọng âm của hai điểm dừng thật. Không ảnh thì mục
    giữ dạng chữ — đó là trạng thái ĐÚNG, không phải thiếu sót.
    """
    for section in (upcoming_events, seasonal):
        for entity in section:
            descriptors = entity.get("image_descriptors") or []
            if not (descriptors and (descriptors[0] or {}).get("url")):
                continue
            if _has_stale_geography(entity):
                continue
            entity["signal_lead_ok"] = True


def _finalize_homepage_sections(sections: list[list[dict]], upcoming_events: list[dict]) -> None:
    for section in sections:
        for e in section:
            e.pop("_score", None)
    for e in upcoming_events:
        e.pop("_score", None)
        e["days_until"] = e.pop("_days_until", None)
        # KHÔNG gắn nhãn âm lịch theo-sự-kiện ở đây. C1 từng suy nhãn đó từ
        # attributes.date_start; đo lại thấy nó NÓI NGƯỢC attributes.lunar_date
        # mà /le-hoi đang in cho cùng lễ hội đó (24/36 sự kiện lệch, có ca lệch
        # cả tháng âm). Bảng quyết định của dự án
        # (docs/2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md) phân loại
        # 67 event: chỉ 12 ca KHỚP mọi trường, 3 ca date_start CHÍNH LÀ ô sai,
        # 14 ca tự mâu thuẫn và ghi rõ "KHÔNG giải được từ dữ liệu — phải có
        # người chốt". Suy từ date_start là khuếch đại đúng ô hỏng.
        # Măng-sét vẫn in ngày âm của HÔM NAY — đó là ngày lịch, không phải dữ
        # liệu entity, nên không có ô nào để nói ngược.


def _project_public_entity_media_sections(
    *sections: list[dict],
) -> tuple[list[dict], ...]:
    return tuple(
        [_project_public_entity_media(entity) for entity in section]
        for section in sections
    )


_TZ_VIETNAM = timezone(timedelta(hours=lunar_calendar.TZ_VIETNAM))
_WEEKDAY_VI = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật")


def _today_vietnam() -> datetime:
    """Hôm nay theo giờ Việt Nam.

    `datetime.now(timezone.utc)` cho SAI tháng trong 7 tiếng mỗi lần sang tháng:
    31/08 23:00 UTC đã là 01/09 giờ VN, mà payload vẫn dựng mùa vụ tháng 8. Cùng
    lớp lỗi với măng-sét frontend — chốt một nguồn giờ cho cả hai đầu.
    """
    return system_clock.now_vietnam()


def _lunar_phrase(day: int, month: int, year: int) -> str:
    """«15 tháng 7 năm Bính Ngọ» — giọng chữ dùng chung với trang lịch vạn niên."""
    lunar = lunar_calendar.solar_to_lunar(day, month, year)
    if lunar.month == 1:
        thang = "tháng Giêng"
    elif lunar.month == 12:
        thang = "tháng Chạp"
    else:
        thang = f"tháng {lunar.month}"
    nhuan = " nhuận" if lunar.leap else ""
    return f"{lunar.day} {thang}{nhuan} năm {lunar_calendar.can_chi_year(lunar.year)}"


def _build_masthead(now_vn: datetime) -> dict:
    """Dòng ngày âm–dương cho măng-sét trang chủ.

    Tính Ở BACKEND chứ không ở trình duyệt vì ba lẽ: (1) oracle âm lịch là Python
    (agent/lunar_calendar.py) nên tính tại nguồn thì không có rủi ro lệch bản port;
    (2) trang chủ khỏi phải nạp bản port JS chỉ để in một dòng chữ — bundle đang
    vượt trần; (3) hết hẳn rủi ro SSR bất đồng client.
    Câu chữ giữ đúng giọng đang dùng ở trang lịch vạn niên.
    """
    d, m, y = now_vn.day, now_vn.month, now_vn.year
    return {
        "solar_label": f"{_WEEKDAY_VI[now_vn.weekday()]}, {d:02d}/{m:02d}/{y}",
        "lunar_label": _lunar_phrase(d, m, y),
    }


async def _build_homepage_payload(month: int) -> dict:
    all_ents = await asyncio.to_thread(
        db.list_entities, limit=_FULL_SCAN_LIMIT, offset=0, public_only=True)
    _warn_if_scan_truncated(all_ents, _FULL_SCAN_LIMIT, "trang chủ")
    public = [e for e in all_ents if not _event_is_past(e)]
    await asyncio.to_thread(_enrich_place, public)

    for e in public:
        e["_score"] = _homepage_score(e, month)

    # Seasonal: entities actually in season this month (not year-round)
    seasonal_pool = [e for e in public
                     if e["type"] in ("product", "experience", "dish")
                     and _entity_in_season(e, month)]
    seasonal_pool.sort(key=lambda e: e["_score"], reverse=True)
    seasonal = _dedup_by_name(seasonal_pool, limit=4)

    seasonal_ids = {e["id"] for e in seasonal}

    # Upcoming events (next 30 days, sorted by date_start)
    # Only show events with reliable dates: must have lunar_date OR
    # consistent month field. Exclude cat=mua (seasonal, not event).
    # MỘT đồng hồ cho cả payload. B1a đổi `month` và măng-sét sang giờ VN nhưng
    # bỏ sót đúng dòng này, nên trang TỰ CÃI NHAU 7 tiếng mỗi ngày: măng-sét in
    # "Thứ Ba, 15/09" trong khi thẻ sự kiện ngày 15/09 vẫn ghi "Ngày mai".
    today = _today_vietnam().date()
    cutoff = today + timedelta(days=30)
    upcoming_events = _select_upcoming_events(public, today, cutoff)

    upcoming_ids = {e["id"] for e in upcoming_events}
    exclude_from_exp = seasonal_ids | upcoming_ids

    # Experiences: tourism types, diverse, excluding seasonal + upcoming event dupes
    tourism = [e for e in public if e["type"] in _TOURISM_TYPES]
    tourism.sort(key=lambda e: e.get("_score", 0), reverse=True)
    experiences = _diverse_pick(tourism, max_per_type=2, max_per_area=4, limit=8,
                                exclude_ids=exclude_from_exp)

    # Products fallback (when seasonal is empty)
    products_pool = [e for e in public if e["type"] == "product"]
    products_pool.sort(key=lambda e: e.get("_score", 0), reverse=True)
    products = _dedup_by_name(products_pool, limit=8)

    # Itineraries: score by seasonal relevance + area diversity
    all_itineraries = await asyncio.to_thread(db.list_itineraries)
    itineraries = _select_homepage_itineraries(all_itineraries, public, month)

    stats = await asyncio.to_thread(db.stats)

    # Area counts for region tiles
    area_counts = _compute_homepage_area_counts(public)

    seasonal_tagline = _resolve_seasonal_tagline(month)

    # Top dishes by rating (social proof for "Tinh hoa" section)
    top_dishes = _select_top_dishes(public)

    _finalize_homepage_sections([seasonal, experiences, products, top_dishes], upcoming_events)

    # Trending: entities with highest chat/search hit counts
    trending = _build_homepage_trending(public)

    # Tin chính đặc sản: loại trùng seasonal[] và upcoming_events[] để mục này
    # không nói lại thứ vừa hiện ngay trên nó.
    product_lead = _select_product_lead(public, month, exclude_ids=seasonal_ids | upcoming_ids)
    products_total = sum(1 for e in public if e.get("type") == "product")

    (
        seasonal,
        experiences,
        products,
        top_dishes,
        trending,
        upcoming_events,
    ) = _project_public_entity_media_sections(
        seasonal,
        experiences,
        products,
        top_dishes,
        trending,
        upcoming_events,
    )
    _mark_signal_lead(upcoming_events, seasonal)

    return {
        "seasonal": seasonal,
        "experiences": experiences,
        "products": products,
        "top_dishes": top_dishes,
        "trending": trending,
        "itineraries": itineraries,
        "stats": stats,
        "area_counts": area_counts,
        "month": month,
        "upcoming_events": upcoming_events,
        "seasonal_tagline": seasonal_tagline,
        "masthead": _build_masthead(_today_vietnam()),
        "product_lead": _project_public_entity_media(
            {k: v for k, v in product_lead.items() if k != "_score"}
        ) if product_lead else None,
        "products_total": products_total,
    }


@router.get("/homepage", response_model=HomepageResponse,
            summary="Get curated homepage feed",
            description="Returns the curated homepage with seasonal picks, diverse experiences, products, top dishes, trending entities, upcoming events, itineraries, and area counts. Cached for 2 minutes.")
async def homepage_curated(response: Response):
    """Curated homepage: smart-scored, type/area diverse, seasonal-aware, deduped."""
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    month = _today_vietnam().month

    global _homepage_rebuilding
    hit = _homepage_cache_hit(month)
    if hit is not None:
        return hit
    async with _homepage_lock:
        cache_fresh = (_homepage_cache["data"] is not None and _homepage_cache["month"] == month
                       and _time.time() - _homepage_cache["ts"] < _HOMEPAGE_TTL)
        if cache_fresh:
            return _homepage_cache["data"]
        _homepage_rebuilding = True

    result = await _build_homepage_payload(month)
    _homepage_cache.update(month=month, data=result, ts=_time.time())
    _homepage_rebuilding = False
    return result


# ── Map pins (lightweight endpoint for MapListView) ──────────────────

_TYPE_META = {
    "attraction": {"emoji": "\U0001f3de️", "color": "#2E86AB"},
    "nature": {"emoji": "\U0001f333", "color": "#4CAF50"},
    "experience": {"emoji": "\U0001f3ad", "color": "#FF6B35"},
    "dish": {"emoji": "\U0001f35c", "color": "#D94F3D"},
    "drink": {"emoji": "\U0001f964", "color": "#E57373"},
    "product": {"emoji": "\U0001f381", "color": "#FF9800"},
    "craft_village": {"emoji": "\U0001f3e1", "color": "#8D6E63"},
    "accommodation": {"emoji": "\U0001f3e8", "color": "#7E57C2"},
    "event": {"emoji": "\U0001f389", "color": "#EC407A"},
    "history": {"emoji": "\U0001f3db️", "color": "#795548"},
    "person": {"emoji": "\U0001f9d1", "color": "#607D8B"},
    "economy": {"emoji": "\U0001f4b0", "color": "#43A047"},
    "organization": {"emoji": "\U0001f3e2", "color": "#546E7A"},
    "facility": {"emoji": "\U0001f3e5", "color": "#1976D2"},
}
_TYPE_META.update({
    "restaurant": {"emoji": "\U0001f37d\ufe0f", "color": "#C75C2E"},
    "cafe": {"emoji": "\u2615", "color": "#8D6E63"},
    "place": {"emoji": "\U0001f4cd", "color": "#546E7A"},
    "itinerary": {"emoji": "\U0001f5fa\ufe0f", "color": "#4A6FA5"},
})

_map_pins_cache: dict = {"data": None, "filters": None, "ts": 0.0}
_MAP_PINS_TTL = 120


def _build_map_pin(e: dict) -> dict | None:
    coords = e.get("coordinates")
    if not coords or not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    try:
        lat, lng = float(coords[0]), float(coords[1])
    except (TypeError, ValueError, IndexError):
        return None
    etype = e.get("type", "")
    meta = _TYPE_META.get(etype, {"emoji": "\U0001f4cd", "color": "#9E9E9E"})
    attrs = e.get("attributes") or {}
    pin = {
        "id": e["id"],
        "name": e["name"],
        "type": etype,
        "lat": lat,
        "lng": lng,
        "emoji": meta["emoji"],
        "category_color": meta["color"],
        "rating": attrs.get("rating"),
        "review_count": attrs.get("review_count", 0),
        "confidence": e.get("confidence"),
        "coords_approximate": bool(attrs.get("coords_approximate")),
        "area": e.get("area") or attrs.get("area"),
    }
    pid = e.get("placeId")
    if pid:
        p = _get_place(pid)
        if p:
            pin["place_name"] = p["name"]
            pin["place_area"] = p.get("area")
    return pin


@router.get("/map-pins", response_model=list[MapPin],
            summary="Get map pins",
            description="Returns lightweight map pin data for all entities with coordinates. Includes emoji, color, rating, and place name. Filterable by type and area.")
async def get_map_pins(
    response: Response,
    type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=50),
):
    """Trả pin bản đồ (lat/lng, emoji, màu theo type, rating, place) của entity công khai có toạ độ.

    Lọc theo type (nhiều giá trị phân tách dấu phẩy) và area; quét tối đa 5000 entity và
    bỏ qua entity thiếu toạ độ hợp lệ. Kết quả giữ trong cache tiến trình 120 giây cho
    đúng MỘT tổ hợp filter gần nhất.
    """
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    cache_key = f"{type}:{area}"
    _now = _time.time()
    if (_map_pins_cache["data"] is not None
            and _map_pins_cache["filters"] == cache_key
            and _now - _map_pins_cache["ts"] < _MAP_PINS_TTL):
        return _map_pins_cache["data"]

    type_filters: list[str] | None = None
    if type:
        type_filters = [t.strip() for t in type.split(",") if t.strip()]

    def _query():
        all_ents = db.list_entities(limit=_FULL_SCAN_LIMIT, offset=0, area=area,
                                    public_only=True, entity_types=type_filters)
        _warn_if_scan_truncated(all_ents, _FULL_SCAN_LIMIT, "ghim bản đồ")
        pins = []
        for e in all_ents:
            pin = _build_map_pin(e)
            if pin is not None:
                pins.append(pin)
        return pins

    result = await asyncio.to_thread(_query)
    _map_pins_cache.update(data=result, filters=cache_key, ts=_now)
    return result


def _event_date_reliable(e: dict) -> bool:
    # Exclude seasonal items (cat=mua) and events with unreliable dates
    attrs = e.get("attributes") or {}
    if attrs.get("category") == "mua":
        return False
    ds_date = _parse_event_iso_date(attrs, "date_start_iso", "date_start")
    if not ds_date:
        return False
    attr_month = attrs.get("month")
    if attr_month and isinstance(attr_month, (int, float)) and int(attr_month) != ds_date.month:
        return False
    attrs["date_start_iso"] = attrs.get("date_start_iso") or ds_date.isoformat()
    e["date_reliable"] = True
    return True


def _event_sort_key(e: dict, today):
    attrs = e.get("attributes") or {}
    ds = _parse_event_iso_date(attrs, "date_start_iso", "date_start")
    if ds:
        return (0, ds)
    s = (e.get("season") or {}).get("months") or []
    if s:
        first = min(s)
        d = datetime(today.year, first, 1).date()
        if d < today:
            d = datetime(today.year + 1, first, 1).date()
        return (1, d)
    return (2, datetime(today.year, 12, 31).date())


@router.get("/events", response_model=EventsResponse,
            summary="List events",
            description="Returns upcoming events sorted by date. Filters out past events by default and excludes unreliable dates. Filterable by area.")
async def list_events(
    response: Response,
    area: Optional[str] = Query(None, max_length=100),
    include_past: bool = False,
    limit: int = Query(50, ge=1, le=200),
):
    """Trả entity type=event công khai sắp theo ngày bắt đầu, mặc định ẩn sự kiện đã qua.

    Chỉ giữ sự kiện có ngày bắt đầu đáng tin (loại mục category=mua và mục có tháng khai
    báo lệch với ngày bắt đầu); lọc tuỳ chọn theo area. total đếm sau khi lọc, events cắt
    theo limit.
    """
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    today = _today_vietnam().date()   # cùng đồng hồ với trang chủ (§B1a)
    all_ents = await asyncio.to_thread(
        db.list_entities, entity_type="event", limit=_EVENT_SCAN_LIMIT, offset=0,
        public_only=True)
    _warn_if_scan_truncated(all_ents, _EVENT_SCAN_LIMIT, "lịch sự kiện")
    events = list(all_ents)
    _enrich_place(events)

    if area:
        events = [e for e in events
                  if (e.get("place_area") or e.get("area")) == area]

    if not include_past:
        events = [e for e in events if not _event_is_past(e)]

    events = [e for e in events if _event_date_reliable(e)]
    events.sort(key=lambda e: _event_sort_key(e, today))
    public_events = [_project_public_entity_media(event) for event in events[:limit]]
    return {"total": len(events), "events": public_events}


_REPORT_FIELD_OPTIONS = {"phone", "hours", "address", "source", "name", "price", "images", "other"}


class ReportIn(BaseModel):
    target_id: str = Field(..., min_length=1, max_length=200)
    target_type: str = Field("entity", max_length=20)
    reason: str = Field(..., min_length=1, max_length=60)
    detail: str = Field("", max_length=2000)
    contact: str = Field("", max_length=120)
    field: Optional[str] = Field(None, max_length=20)


# ── Legacy correction adapter (Task 15) ──
#
# One write authority per report. While correction intake is off the old JSONL
# behaviour stands untouched. While it is on, a factual field report the kernel
# can hold is filed there alone and answered with the canonical receipt; the
# JSONL file is not written. Cutover is recorded as a file, so rolling the flag
# back cannot quietly reopen the JSONL lane for corrections — a forked record is
# worse than an honest refusal.

LEGACY_STALE_FIELD_PATHS = {
    "phone": "attributes.phone",
    "hours": "attributes.opening_hours",
    "address": "attributes.address",
    "name": "name",
    "price": "attributes.price_range",
}


def _correction_cutover_marker() -> Path:
    # Derived from REPORTS_FILE so tests that redirect one redirect both.
    return REPORTS_FILE.with_name("corrections-cutover.marker")


def _correction_intake_live() -> bool:

    return bool(getattr(settings, "CASE_KERNEL_ENABLED", False)) and bool(
        getattr(settings, "CORRECTION_INTAKE_ENABLED", False)
    )


def _legacy_value_at(entity: dict, field_path: str) -> str:
    node = entity
    for part in field_path.split("."):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return ""
    return str(node)


def _file_legacy_correction(entity_id: str, field: str, detail: str, request: Request):
    """Route one legacy factual report into the kernel, or refuse honestly."""
    from cases.public_api import _service as _case_service
    from cases.service import CorrectionRejected

    field_path = LEGACY_STALE_FIELD_PATHS[field]
    entity = _get_public_entity(entity_id)
    if not entity:
        return _err(404, "not_found")
    proposed = detail.strip()
    if not proposed:
        # A correction is a claim about what the page should say; with nothing
        # proposed there is nothing to decide, and downgrading to the old lane
        # would fork the record by the reporter's punctuation.
        return JSONResponse(status_code=422, content={
            "error": "proposed_value_required",
            "message": "Hãy ghi thông tin đúng để chúng tôi sửa theo.",
        })
    payload = SimpleNamespace(
        reporter_privacy="anonymous",
        items=(SimpleNamespace(
            entity_id=str(entity["id"]),
            field_path=field_path,
            # What the page says now is ours to read, never the reporter's to
            # assert: trusting them for both sides would let one request forge
            # the diff a decision is judged on.
            reported_value=_legacy_value_at(entity, field_path),
            proposed_value=proposed,
            base_entity_revision=int(entity.get("revision") or 1),
            reported_value_known=True,
        ),),
        optional_phone=None,
        notification_consent=False,
        handoff_digest=None,
        handoff_confirmed=False,
    )
    try:
        # Legacy reports now cross the same discriminator boundary as the
        # canonical route before the kernel can mutate any case state.
        CorrectionIntakeContract.model_validate({
            "reported_value_known": True,
            "reported_value": payload.items[0].reported_value,
        })
    except ValidationError:
        reported_value = payload.items[0].reported_value
        if type(reported_value) is str and len(reported_value) > 2000:
            code, message = "correction_value_too_long", "That value is too long."
        else:
            code, message = "invalid_correction_value", "Both values are required."
        return JSONResponse(status_code=400, content={
            "error": code,
            "message": message,
        })
    try:
        result = _case_service().create_correction_from_transport(
            payload,
            idempotency_key=f"legacy:{uuid4().hex}",
            correlation_id=request.headers.get("x-request-id") or uuid4().hex,
            rate_subject=get_client_ip(request),
        )
    except CorrectionRejected as exc:
        return JSONResponse(status_code=exc.problem.status, content={
            "error": exc.problem.code, "message": exc.problem.detail,
        })
    # The kernel now owns corrections; record that durably before answering.
    marker = _correction_cutover_marker()
    if not marker.exists():
        marker.parent.mkdir(exist_ok=True)
        marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return JSONResponse(status_code=201, content={
        "publicReference": result.public_reference,
        "capability": result.capability,
        "receivedAt": result.received_at.isoformat(),
        "nextUpdateAt": result.next_update_at.isoformat(),
        "replayed": result.replayed,
    })


def _legacy_correction_closed() -> JSONResponse | None:
    """After cutover, the JSONL lane for corrections stays closed, flag or not."""
    if _correction_cutover_marker().exists():
        return JSONResponse(status_code=503, content={
            "error": "correction_intake_paused",
            "message": "Kênh sửa thông tin đang tạm dừng. Vui lòng quay lại sau.",
        })
    return None


@router.post("/report",
             summary="Submit a report",
             description="Submits a report for incorrect information or policy-violating content. Stored in JSONL for admin review. Rate-limited per IP.")
async def submit_report(payload: ReportIn, request: Request):
    """GĐ13.6f: tiếp nhận báo-sai (facility/entity) & báo cáo nội dung (post/comment).

    Lưu vào reports.jsonl cho admin xử lý — KHÔNG đăng/khoá tự động. Rate-limit theo IP.
    """
    ip = get_client_ip(request)
    allowed, info = report_limiter.is_allowed(ip)
    if not allowed:
        return _err(429, "Bạn gửi quá nhiều báo cáo. Vui lòng thử lại sau.",
                    retry_after=info.get("retry_after", 60))
    target_type = payload.target_type if payload.target_type in _VALID_TARGET_TYPES else "other"
    report_field = payload.field if payload.field and payload.field in _REPORT_FIELD_OPTIONS else None
    # A factual entity report the kernel can hold is a correction, and after the
    # cutover the kernel is its only authority. Content reports (post/comment)
    # are moderation work and keep their lane untouched.
    if target_type in {"entity", "facility"} and report_field in LEGACY_STALE_FIELD_PATHS:
        if _correction_intake_live():
            return _file_legacy_correction(
                payload.target_id.strip(), report_field, payload.detail, request
            )
        closed = _legacy_correction_closed()
        if closed is not None:
            return closed
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "target_id": payload.target_id.strip(),
        "target_type": target_type,
        "reason": payload.reason.strip(),
        "detail": payload.detail.strip(),
        "contact": payload.contact.strip(),
        "field": report_field,
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
        "status": "open",
    }
    def _write():
        with _jsonl_lock:
            REPORTS_FILE.parent.mkdir(exist_ok=True)
            with open(REPORTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            _maybe_rotate_jsonl(REPORTS_FILE)
    try:
        await asyncio.to_thread(_write)
    except OSError:
        logger.exception("Failed to write report to %s", REPORTS_FILE)
        return _err(500, "store_failed")
    return {"ok": True, "message": "Đã ghi nhận. Cảm ơn bạn đã góp ý — chúng tôi sẽ kiểm tra."}


# ── Report stale field (U-02: field-level freshness reports) ─────────

_STALE_FIELDS = {"phone", "hours", "address", "source", "name", "price", "images", "other"}


class ReportStaleIn(BaseModel):
    field: str = Field(..., min_length=1, max_length=20)
    detail: str = Field("", max_length=2000)


@router.post("/entities/{entity_id}/report-stale",
             summary="Report stale entity field",
             description="Reports a specific field (phone, hours, address, etc.) as outdated or incorrect on an entity. Rate-limited per IP.")
async def report_stale_field(entity_id: str, payload: ReportStaleIn, request: Request):
    """U-02: Report a specific field as stale/incorrect on an entity."""
    validate_path_id(entity_id, "entity_id")
    if payload.field not in _STALE_FIELDS:
        return JSONResponse(status_code=422, content={
            "error": "invalid_field",
            "valid_fields": sorted(_STALE_FIELDS),
        })
    ip = get_client_ip(request)
    allowed, info = report_limiter.is_allowed(ip)
    if not allowed:
        return _err(429, "Bạn gửi quá nhiều yêu cầu. Vui lòng thử lại sau.",
                    retry_after=info.get("retry_after", 60))
    if payload.field in LEGACY_STALE_FIELD_PATHS:
        if _correction_intake_live():
            return _file_legacy_correction(entity_id, payload.field, payload.detail, request)
        closed = _legacy_correction_closed()
        if closed is not None:
            return closed
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "target_id": entity_id,
        "target_type": "stale_field",
        "field": payload.field,
        "detail": payload.detail.strip(),
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
        "status": "open",
    }
    def _write():
        with _jsonl_lock:
            REPORTS_FILE.parent.mkdir(exist_ok=True)
            with open(REPORTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            _maybe_rotate_jsonl(REPORTS_FILE)
    try:
        await asyncio.to_thread(_write)
    except OSError:
        logger.exception("Failed to write stale report")
        return _err(500, "store_failed")
    return {"ok": True, "message": "Đã ghi nhận — chúng tôi sẽ kiểm tra và cập nhật."}


# ── Entity gallery (entity images + review images) ───────────────────



def _append_review_gallery_images(images: list[dict], review_rows: list[dict], entity_name: str) -> None:
    for row in review_rows:
        review_imgs = row.get("images") or []
        if isinstance(review_imgs, str):
            try:
                review_imgs = json.loads(review_imgs)
            except (json.JSONDecodeError, ValueError):
                review_imgs = []
        if type(review_imgs) not in {list, tuple}:
            continue
        credit = row.get("display_name")
        if type(credit) is not str or not credit.strip():
            credit = None
        for url in review_imgs:
            descriptor = describe_review_image(
                url,
                entity_name=entity_name,
                credit=credit,
                disclosure=_GALLERY_DISCLOSURE,
            )
            if descriptor is not None:
                images.append(asdict(descriptor))




# ── Review stats (rating distribution + mention extraction) ──────────










# ── Similar entity recommendations (U-29: rule-based) ────────────────











# ── Entity Q&A (U-09: questions with best answer resolution) ─────────

from fastapi import Depends



# ── Contact view tracking (CTA analytics) ───────────────────────────

CONTACT_VIEWS_FILE = Path(__file__).resolve().parent / "data" / "contact_views.jsonl"
_VALID_CONTACT_ACTIONS = {"zalo", "phone", "website", "map"}


@router.post("/entities/{entity_id}/view-contact",
             summary="Track contact view",
             description="Logs a CTA analytics event when a user views contact info (Zalo, phone, website, or map). Rate-limited to 10 per minute per IP.")
async def track_contact_view(
    entity_id: str,
    request: Request,
    action: str = Query(..., pattern="^(zalo|phone|website|map)$"),
):
    """Ghi một lượt xem thông tin liên hệ (zalo/phone/website/map) của entity vào contact_views.jsonl.

    Giới hạn 10 lượt/60 giây theo IP; bản ghi chỉ lưu hash IP rút gọn, không lưu IP thô.
    Không kiểm tra entity có tồn tại hay không. Lỗi ghi file → 500.
    """
    validate_path_id(entity_id, "entity_id")
    ip = get_client_ip(request)
    from ratelimit import check_rate
    check_rate(f"contact-view:{ip}", 10, 60,
               "Quá nhiều yêu cầu. Vui lòng thử lại sau.")

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "entity_id": entity_id,
        "action": action,
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
    }

    def _write():
        with _jsonl_lock:
            CONTACT_VIEWS_FILE.parent.mkdir(exist_ok=True)
            with open(CONTACT_VIEWS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            _maybe_rotate_jsonl(CONTACT_VIEWS_FILE)

    try:
        await asyncio.to_thread(_write)
    except OSError:
        logger.exception("Failed to write contact view log")
        return _err(500, "store_failed")
    return {"ok": True}


# ── Entity claims (U-30) ────────────────────────────────────────────





# ── What's-new feed (U-15): route về agent/community/api.py cạnh cụm /feed*
# (lát 4 đợt hoàn-thiện-sâu 2026-08-29; trên SQLite nay trả 503 theo §1.3 —
# behavior change có duyệt). Tái xuất 2 ký hiệu vì test soi nguồn qua
# public_api.<tên> (inspect.getsource đi theo object nên vẫn đúng nhà thật).
from community.api import _collect_new_entities, feed_new_since  # noqa: F401, E402


# ── Collections (U-28, public read-only): sang entities/api.py cạnh cụm
# /featured (lát 6 đợt cắt module 2026-08-29). Ký hiệu tái xuất ở block
# `from entities.api import` đầu file — test soi qua public_api.<tên> vẫn và
# được, inspect.getsource đi theo object nên trỏ đúng nhà thật.


# ── Public Announcements: sang siteops/api.py (2026-08-29, lat 3) ────────


# ── Entity Map Search (bounding box) ────────────────────────────────────







# ── Entity Trending (hot entities recently) ──────────────────────────────



# ── User Engagement Stats ────────────────────────────────────────────────

@router.get("/users/{user_id}/engagement",
            summary="Get user engagement stats",
            description="Returns engagement metrics for a user profile: total posts, reviews, questions, average rating, follower count, and likes received. Requires Postgres.")
async def user_engagement_stats(
    user_id: str,
    request: Request,
    response: Response,
    user=Depends(get_current_user),
):
    """Lightweight engagement stats for a user profile card."""
    validate_path_id(user_id, "user_id")
    require_pg()
    ph = db._ph
    viewer_id = str(user["id"]) if user else None

    def _query():
        with db._conn() as conn:
            # The shared resolver owns active (is_active), deletion, and privacy checks.
            access = resolve_profile_access(
                conn, user_id, viewer_id, require_activity=True
            )
            if access.status != "ok":
                return access, None
            target_id = access.target_id or user_id
            stats = db._fetchone(conn, f"""
                SELECT
                    COUNT(*) FILTER (WHERE moderation_status = 'approved') as total_posts,
                    COUNT(*) FILTER (WHERE post_type = 'review' AND moderation_status = 'approved') as total_reviews,
                    COALESCE(AVG(rating) FILTER (WHERE post_type = 'review' AND rating IS NOT NULL), 0) as avg_rating,
                    COUNT(*) FILTER (WHERE post_type = 'question' AND moderation_status = 'approved') as total_questions,
                    COUNT(DISTINCT entity_id) FILTER (WHERE entity_id IS NOT NULL AND moderation_status = 'approved') as entities_reviewed
                FROM posts WHERE user_id::text = {ph} AND deleted_at IS NULL
            """, (target_id,))
            stats_d = db._row_to_dict(stats) if stats else {}
            followers = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM follows
                WHERE target_type = 'user' AND target_id = {ph}
            """, (target_id,))
            likes = db._fetchone(conn, f"""
                SELECT COALESCE(SUM(like_count), 0) as total_likes
                FROM posts WHERE user_id::text = {ph} AND moderation_status = 'approved' AND deleted_at IS NULL
            """, (target_id,))
        return access, {
            "user_id": target_id,
            "total_posts": stats_d.get("total_posts", 0),
            "total_reviews": stats_d.get("total_reviews", 0),
            "avg_rating": round(float(stats_d.get("avg_rating", 0)), 1),
            "total_questions": stats_d.get("total_questions", 0),
            "entities_reviewed": stats_d.get("entities_reviewed", 0),
            "followers": db._row_to_dict(followers)["c"] if followers else 0,
            "total_likes_received": db._row_to_dict(likes)["total_likes"] if likes else 0,
        }

    access, result = await asyncio.to_thread(_query)
    if access.status == "not_found":
        raise HTTPException(404, "Người dùng không tồn tại")
    if access.status == "hidden":
        result = {
            "user_id": user_id,
            "total_posts": 0,
            "total_reviews": 0,
            "avg_rating": 0.0,
            "total_questions": 0,
            "entities_reviewed": 0,
            "followers": 0,
            "total_likes_received": 0,
        }
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return result


# ── Entity comparison ─────────────────────────────────────────────────



# ── Popular entities by type ─────────────────────────────────────────









# ── Dedicated entity search with advanced filters ─────────────────────



# ── ND 147/2024 Compliance & Transparency ──────────────────────────────

@router.get("/transparency", response_model=TransparencyResponse,
            summary="Get transparency report",
            description="Returns ND 147/2024 compliance info: moderation policy, takedown SLA, data practices, and contact details. Cached for 24 hours.")
async def transparency_report(response: Response):
    """ND 147/2024 transparency: moderation policy, contact, takedown SLA."""
    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=172800"
    return {
        "platform": "VinhLong360",
        "legal_entity": "Cá nhân vận hành — vinhlong360.vn",
        "contact_email": "lienhe@vinhlong360.vn",
        "content_policy": {
            "moderation": "Tất cả nội dung người dùng được kiểm duyệt tự động trước khi hiển thị.",
            "takedown_sla_hours": 24,
            "appeal_process": "Gửi email đến lienhe@vinhlong360.vn trong 7 ngày.",
            "prohibited_content": [
                "Vi phạm pháp luật Việt Nam",
                "Thông tin sai sự thật gây hoang mang",
                "Xúc phạm, phân biệt đối xử",
                "Spam, quảng cáo trái phép",
                "Nội dung khiêu dâm, bạo lực",
            ],
        },
        "data_practices": {
            "storage_location": "Việt Nam",
            "data_retention": "Dữ liệu cá nhân được lưu khi tài khoản hoạt động. Xóa khi deactivate.",
            "third_party_sharing": "Không chia sẻ dữ liệu với bên thứ ba ngoài mục đích vận hành.",
        },
        "nd147_compliance": {
            "regulation": "Nghị định 147/2024/NĐ-CP",
            "content_removal_within_24h": True,
            "user_data_on_request": True,
            "cooperation_with_authorities": True,
        },
    }


# ── Health (alias for /health under /api prefix) ────────────────────────
@router.get("/health", tags=["health"],
            summary="System health check",
            description="Returns minimal public liveness status and entity count. Detailed diagnostics are available through admin-only health endpoints.")
async def api_health():
    """Trả nguyên kết quả của server.health() dưới prefix /api, kèm Cache-Control: no-store."""
    from server import health
    data = await health()
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


# ── Route ordering fix ───────────────────────────────────────────────────
# Static paths like /entities/map must match BEFORE /entities/{entity_id}.
# Starlette resolves routes in definition order, so late-defined static
# paths are shadowed by earlier parameterized ones. Fix: reorder once at
# module load so static entity sub-paths precede the catch-all.
_STATIC_ENTITY_PATHS = frozenset({
    "/api/entities/map", "/api/entities/trending", "/api/entities/compare",
    "/api/entities/popular", "/api/entities/search",
})

def _fix_route_order():
    static = []
    rest = []
    insert_idx = None
    for r in router.routes:
        path = getattr(r, "path", "")
        if path in _STATIC_ENTITY_PATHS:
            static.append(r)
        else:
            if path == "/api/entities/{entity_id}" and insert_idx is None:
                insert_idx = len(rest)
            rest.append(r)
    if static and insert_idx is not None:
        rest[insert_idx:insert_idx] = static
        router.routes[:] = rest

# Gop route mien entity TRUOC khi sap thu tu. Mien da sang agent/entities/
# (2026-08-28) nhung 34 cho trong bo test hoi `public_api.router` xem mat cong
# khai co route X hay khong — y dinh do dung o TANG APP.
#
# THU TU QUAN TRONG: noi SAU `_fix_route_order()` la route tinh
# (/api/entities/popular) bi route tham so (/api/entities/{entity_id}) che —
# do duoc 70 bai do, trong do co dung bai canh chuyen chuyen do
# (TestRouteOrdering::test_public_entities_popular_not_shadowed).
from entities.api import router as _entities_router  # noqa: E402

# `include_router` THẬT chứ không chép router.routes bằng tay: cổng R20.9 dựng
# đồ thị mount từ các lời gọi include_router, nên vòng append thủ công là vô
# hình với nó — hai bài launch_safety đỏ với "route is not mounted". Chuỗi mount
# nay là app -> public_api.router -> entities.router, cổng nhìn thấy đủ.
router.include_router(_entities_router)

# Mien LICH TRINH cung khuon (2026-08-29, lat 2): 3 route public /itineraries*
# song o itineraries/api.py, mount long vao router nay TRUOC _fix_route_order()
# — cong R20.9 dung do thi tu cac loi goi include_router.
from itineraries.api import router as _itineraries_router  # noqa: E402

router.include_router(_itineraries_router)

# Mien VAN HANH SITE cung khuon (2026-08-29, lat 3): 2 route public doc
# (/site-settings, /announcements) song o siteops/api.py, mount long vao router
# nay TRUOC _fix_route_order() — cong R20.9 dung do thi tu cac loi goi
# include_router.
from siteops.api import router as _siteops_router  # noqa: E402

router.include_router(_siteops_router)

_fix_route_order()


# Homepage-cache la trang thai cua FILE NAY; viec xoa no khi place-cache doi
import entity_read as _entity_read
_entity_read._place_invalidation_listeners.append(
    lambda: _homepage_cache.update(month=None, data=None, ts=0.0)  # Perf-P0
)
