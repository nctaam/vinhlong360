"""
vinhlong360 — Public API.

Read-only endpoints for the frontend to consume entities, itineraries,
and search results from the database instead of static data.json.

Mount: app.include_router(public_router)
"""

import asyncio
import hashlib
import json
import logging
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from api_schemas import (  # W6.3: response_model (extra="allow" — không strip field FE)
    AreasResponse, AutocompleteResponse, CollectionsResponse, CompareResponse,
    EntityDetailResponse, EntityListResponse, EntityMapResponse, EntityTypesResponse,
    EventsResponse, FeaturedResponse, HomepageResponse, MapPin, PopularResponse,
    SearchResponse, SiteSettingsResponse, StatsResponse, TransparencyResponse,
    TrendingResponse,
)
from database import db
from data_quality import entity_quality
from middleware import report_limiter, get_client_ip
from auth_middleware import validate_path_id, require_pg, require_user, require_csrf, get_current_user

router = APIRouter(prefix="/api", tags=["public"])


def _err(status_code: int, detail: str, **extra) -> JSONResponse:
    """Error-shape chuẩn (SP3 W6.2): {detail, ...} — đồng nhất với
    server._error_response và HTTPException handler. Trước đây public_api trả
    {error: code} bypass handler; nay dùng detail (FE dựa HTTP status, không đọc
    error-code — đã verify grep web-nuxt)."""
    body: dict = {"detail": detail}
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


from collections import OrderedDict
import threading as _threading

_PLACE_CACHE_MAX = 500
_place_cache: OrderedDict[str, dict] = OrderedDict()
_place_cache_lock = _threading.Lock()
DEFAULT_RELATIONSHIP_LIMIT = 24

# Perf-P0: cache payload /homepage (endpoint nóng nhất) — trước đây scan toàn bảng entity
# + 6×COUNT mỗi request. Curation tất định theo tháng → cache TTL ngắn, theo tháng.
import time as _time
_homepage_cache: dict = {"month": None, "data": None, "ts": 0.0}
_HOMEPAGE_TTL = 120  # giây
_homepage_rebuilding = False
_homepage_lock = asyncio.Lock()

_ENTITY_CACHE_MAX = 1000
_entity_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_ENTITY_TTL = 60  # 60s cache per entity

def invalidate_entity_cache(entity_id: str | None = None):
    """Clear entity cache entry or all entries."""
    if entity_id:
        to_del = [k for k in _entity_cache if k.startswith(f"{entity_id}:")]
        for k in to_del:
            _entity_cache.pop(k, None)
    else:
        _entity_cache.clear()


def _is_public(e: dict) -> bool:
    """Entity được hiển thị công khai (listing/homepage): loại entity provisional /
    chưa kiểm chứng (auto-learned). Quarantine cho public display — KB chat vẫn dùng,
    nhưng trang công khai KHÔNG show nội dung tự-học chưa duyệt (tránh cảm giác nghiệp dư)."""
    return e.get("status") != "provisional" and e.get("verified") is not False


def _get_public_entity(entity_id: str) -> Optional[dict]:
    entity = db.get_entity(entity_id)
    if not entity or not _is_public(entity):
        return None
    return entity


def _itinerary_stop_entity_id(stop) -> str:
    if isinstance(stop, str):
        return stop
    if isinstance(stop, dict):
        return str(stop.get("entityId") or stop.get("entity_id") or stop.get("id") or "")
    return ""


def _itinerary_coverage_areas(itinerary: dict) -> set[str]:
    areas = {str(area) for area in (itinerary.get("areas") or []) if area}
    primary = itinerary.get("area")
    if primary and (primary != "lien-vung" or not areas):
        areas.add(str(primary))
    return areas


def _filter_public_relationships(rels: list[dict]) -> list[dict]:
    other_ids = [r.get("other_id") for r in rels if r.get("other_id")]
    if not other_ids:
        return rels
    batch = db.get_entities_batch(other_ids)
    return [r for r in rels if _is_public(batch.get(r.get("other_id"), {}))]


def _days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError, AttributeError):
        # naive date (no tz) → aware-minus-naive raises TypeError; treat as unknown
        return None


def _build_source_freshness(entity: dict) -> dict:
    """Source freshness for entity detail. P0-6: freshness_status phản ánh NGÀY
    KIỂM-CHỨNG-THỰC-ĐỊA thật (verifiedAt) — KHÔNG bao giờ dùng updatedAt (timestamp
    import) — nên re-import hàng loạt không thể giả badge "mới kiểm chứng"."""
    from data_quality import source_info
    src = source_info(entity)
    updated_at = entity.get("updatedAt")
    verified_at = entity.get("verifiedAt")
    days_since_update = _days_since(updated_at)
    days_since_verified = _days_since(verified_at)
    if days_since_verified is None:
        status = "unknown"
    elif days_since_verified <= 90:
        status = "fresh"
    elif days_since_verified <= 180:
        status = "aging"
    else:
        status = "stale"
    return {
        "source_title": src.get("title") or None,
        "source_url": src.get("url") or None,
        "updated_at": updated_at,
        "verified_at": verified_at,
        "days_since_update": days_since_update,
        "days_since_verified": days_since_verified,
        "freshness_status": status,
    }


_PRACTICAL_FACTS_KEYS = [
    "hours", "admission_fee", "phone", "address", "website",
    "zalo", "parking", "best_time", "peak_hours", "tips",
    "price_range", "duration", "accessibility",
]


def _apply_practical_fact_fallbacks(facts: dict, attrs: dict) -> None:
    """U-07: fill standardized keys from alternate attribute names when missing."""
    if facts["hours"] is None:
        facts["hours"] = attrs.get("open_hours") or attrs.get("opening_hours")
    if facts["admission_fee"] is None:
        facts["admission_fee"] = attrs.get("admission") or attrs.get("ticket_price")
    if facts["price_range"] is None:
        facts["price_range"] = attrs.get("price") or attrs.get("gia")


def _build_practical_facts(entity: dict) -> dict:
    """U-07: Extract standardized practical info from entity attributes."""
    attrs = entity.get("attributes") or {}
    facts = {}
    for key in _PRACTICAL_FACTS_KEYS:
        facts[key] = attrs.get(key)
    _apply_practical_fact_fallbacks(facts, attrs)
    has_any = any(v is not None for v in facts.values())
    facts["_completeness"] = sum(1 for v in facts.values() if v is not None and v != "_completeness")
    return facts if has_any else facts


def invalidate_place_cache():
    """Xoá cache tên/khu-vực xã/phường — gọi sau /reload để tránh phục vụ tên cũ
    khi admin đổi/di chuyển place."""
    with _place_cache_lock:
        _place_cache.clear()
    _homepage_cache.update(month=None, data=None, ts=0.0)  # Perf-P0: refresh homepage sau reload

# GĐ13.6f: báo cáo thông tin sai / nội dung vi phạm — lưu JSONL nhẹ (free-tier),
# admin xem qua /admin/reports để xử lý (takedown/sửa). KHÔNG dùng DB/dịch vụ trả phí.
REPORTS_FILE = Path(__file__).resolve().parent / "data" / "reports.jsonl"
SEARCH_LOG_FILE = Path(__file__).resolve().parent / "data" / "search_queries.jsonl"
USER_EVENTS_FILE = Path(__file__).resolve().parent / "data" / "user_events.jsonl"
_VALID_TARGET_TYPES = {"facility", "entity", "post", "comment", "other"}

_JSONL_MAX_LINES = 5000
import threading as _threading
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


_VALID_USER_EVENT_TYPES = {
    "entity_view", "search", "save_add", "save_remove", "visit_mark",
    "community_view", "post_view", "map_focus", "itinerary_view",
}
_VALID_RECOMMENDATION_CONTEXTS = {"home", "entity", "search", "saved", "map", "itinerary", "community"}
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


class UserEventIn(BaseModel):
    event_type: str = Field(max_length=40)
    context: Optional[str] = Field(None, max_length=40)
    entity_id: Optional[str] = Field(None, max_length=200)
    entity_type: Optional[str] = Field(None, max_length=60)
    entity_name: Optional[str] = Field(None, max_length=300)
    area: Optional[str] = Field(None, max_length=120)
    query: Optional[str] = Field(None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _fold_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _clean_short_text(value: Any, max_len: int = 200) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _safe_event_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {}
    for key, raw in list(value.items())[:12]:
        k = _clean_short_text(key, 50)
        if not k or k.startswith("__"):
            continue
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            out[k] = raw if not isinstance(raw, str) else raw[:300]
        elif isinstance(raw, (list, tuple)):
            out[k] = [str(x)[:120] for x in raw[:8]]
        elif isinstance(raw, dict):
            out[k] = {str(sk)[:50]: str(sv)[:120] for sk, sv in list(raw.items())[:8]}
        else:
            out[k] = str(raw)[:120]
    return out


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


def _log_user_event(user_id: str, body: UserEventIn, request: Request) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": str(user_id),
        "event_type": body.event_type,
        "context": body.context,
        "entity_id": body.entity_id,
        "entity_type": body.entity_type,
        "entity_name": body.entity_name,
        "area": body.area,
        "query": body.query,
        "metadata": _safe_event_metadata(body.metadata),
        "ip_hash": hashlib.sha256(get_client_ip(request).encode("utf-8")).hexdigest()[:16],
    }
    with _jsonl_lock:
        USER_EVENTS_FILE.parent.mkdir(exist_ok=True)
        with open(USER_EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        _maybe_rotate_jsonl(USER_EVENTS_FILE)


def _read_user_events(user_id: str, limit: int = 300) -> list[dict]:
    try:
        if not USER_EVENTS_FILE.exists():
            return []
        rows: list[dict] = []
        for line in reversed(USER_EVENTS_FILE.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(item.get("user_id")) != str(user_id):
                continue
            rows.append(item)
            if len(rows) >= limit:
                break
        return rows
    except Exception:
        logger.debug("user event read failed", exc_info=True)
        return []


def _load_user_signal_entities(user_id: str, limit: int = 80) -> list[tuple[dict, str]]:
    if not db._use_pg:
        return []
    ph = db._ph
    uid = str(user_id)
    signals: list[tuple[dict, str]] = []
    try:
        with db._conn() as conn:
            saved_rows = db._fetchall(conn, f"""
                SELECT e.* FROM saved_entities s
                JOIN entities e ON e.id = s.entity_id
                WHERE s.user_id = {ph}::uuid
                  AND COALESCE(e.status, '') != 'provisional'
                  AND (e.verified IS NULL OR e.verified != 0)
                ORDER BY s.created_at DESC
                LIMIT {ph}
            """, (uid, limit // 2))
            visit_rows = db._fetchall(conn, f"""
                SELECT e.* FROM user_visits v
                JOIN entities e ON e.id = v.entity_id
                WHERE v.user_id = {ph}::uuid
                  AND COALESCE(e.status, '') != 'provisional'
                  AND (e.verified IS NULL OR e.verified != 0)
                ORDER BY v.created_at DESC
                LIMIT {ph}
            """, (uid, limit // 2))
        for row in saved_rows:
            ent = db._parse_entity(row)
            if ent and _is_public(ent):
                signals.append((ent, "saved"))
        for row in visit_rows:
            ent = db._parse_entity(row)
            if ent and _is_public(ent):
                signals.append((ent, "visit"))
    except Exception:
        logger.debug("user signal entity query failed", exc_info=True)
    return signals


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
    if area := _clean_short_text(event.get("area"), 120):
        acc.area_scores[area] += weight
    text = " ".join(str(event.get(k) or "") for k in ("entity_name", "query", "context"))
    acc.interest_scores.update({k: v * weight for k, v in _interest_hits_from_text(text, entity_type).items()})


def _apply_events_to_profile(acc: "_InterestAccumulator", events: list[dict], event_entities: dict) -> None:
    for event in events:
        etype = str(event.get("event_type") or "")
        weight = float(_EVENT_WEIGHTS.get(etype, 1.0))
        if weight == 0:
            continue
        entity_id = str(event.get("entity_id") or "")
        entity = event_entities.get(entity_id) if entity_id else None
        if entity and _is_public(entity):
            _apply_event_entity(acc, entity, entity_id, weight)
        else:
            _apply_event_fallback(acc, event, weight)
        if len(acc.recent_intents) < 8:
            acc.recent_intents.append({
                "event_type": etype,
                "context": event.get("context"),
                "entity_id": entity_id or None,
                "query": event.get("query"),
            })


def _apply_signals_to_profile(acc: "_InterestAccumulator", user_id: str) -> None:
    for entity, source in _load_user_signal_entities(user_id):
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


def _build_user_interest_profile(user_id: str, query: str | None = None, context_entity: dict | None = None) -> dict:
    acc = _InterestAccumulator()
    events = _read_user_events(user_id)

    event_entity_ids = [str(e.get("entity_id")) for e in events if e.get("entity_id")]
    event_entities = db.get_entities_batch(event_entity_ids[:80]) if event_entity_ids else {}

    _apply_events_to_profile(acc, events, event_entities)
    _apply_signals_to_profile(acc, user_id)
    _apply_query_and_context(acc, query, context_entity)

    interest_scores = acc.interest_scores
    type_scores = acc.type_scores
    area_scores = acc.area_scores
    recent_entity_ids = acc.recent_entity_ids
    recent_intents = acc.recent_intents
    signal_count = len(events) + len(recent_entity_ids)
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


def _candidate_card(entity: dict, reasons: list[str]) -> dict:
    return {
        "id": entity.get("id"),
        "name": entity.get("name", ""),
        "type": entity.get("type", ""),
        "place": entity.get("place", ""),
        "place_name": entity.get("place_name"),
        "place_area": entity.get("place_area") or entity.get("area"),
        "summary": (entity.get("summary") or "")[:240],
        "images": (entity.get("images") or [])[:2],
        "attributes": {
            "rating": (entity.get("attributes") or {}).get("rating"),
            "review_count": (entity.get("attributes") or {}).get("review_count"),
        },
        "recommendation_reasons": reasons[:2],
        "quality_score": entity_quality(entity),
    }


def _score_interest_hits(entity: dict, profile: dict, reasons: list[str]) -> float:
    score = 0.0
    hits = _interest_hits_from_entity(entity)
    for key, hit_score in hits.items():
        pref = float(profile.get("interest_scores", {}).get(key, 0) or 0)
        if pref > 0 and hit_score > 0:
            score += min(pref * 0.8 + hit_score, 20)
            label = _label_for_interest(key)
            if label and len(reasons) < 2:
                reasons.append(f"Khớp sở thích {label.lower()}")
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

    if entity.get("images"):
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
    candidates = _gather_recommendation_candidates(profile, current, entity_id, query)

    scored = []
    for entity in candidates.values():
        score, reasons = _score_candidate(entity, profile, context, current, query)
        if not reasons:
            reasons = ["Được cộng đồng quan tâm"]
        scored.append((score, entity, reasons))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("name") or "")))

    selected = [entity for _, entity, _ in scored[:limit]]
    if selected:
        _enrich_place(selected)
    items = [_candidate_card(entity, reasons) for _, entity, reasons in scored[:limit]]
    return {
        "context": context,
        "items": items,
        "reasons": {item["id"]: item.get("recommendation_reasons", []) for item in items if item.get("id")},
        "profile": {
            "interests": profile.get("interests", []),
            "areas": profile.get("areas", []),
            "types": profile.get("types", []),
            "confidence": profile.get("confidence", 0),
            "signal_count": profile.get("signal_count", 0),
        },
    }


@router.post("/me/events",
             status_code=202,
             dependencies=[Depends(require_pg)],
             summary="Track a user experience event",
             description="Stores a bounded first-party event for personalized recommendations. Requires login and CSRF.")
async def track_user_event(body: UserEventIn, request: Request, user=Depends(require_user), _csrf=Depends(require_csrf)):
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
    body.entity_name = _clean_short_text(body.entity_name, 300)
    body.area = _clean_short_text(body.area, 120)
    body.query = _clean_short_text(body.query, 200)
    check_rate(f"user-event:{user['id']}", 120, 300, "Too many events")
    await asyncio.to_thread(_log_user_event, str(user["id"]), body, request)
    return {"accepted": True}


@router.get("/me/insights",
            dependencies=[Depends(require_pg)],
            summary="Get current user interest profile",
            description="Returns lightweight interest, area, and next-action insights inferred from saved items, visits, and recent events.")
async def get_my_insights(response: Response, user=Depends(require_user)):
    response.headers["Cache-Control"] = "no-store"
    profile = await asyncio.to_thread(_build_user_interest_profile, str(user["id"]))
    return {
        "interests": profile.get("interests", []),
        "areas": profile.get("areas", []),
        "types": profile.get("types", []),
        "recent_intents": profile.get("recent_intents", []),
        "confidence": profile.get("confidence", 0),
        "signal_count": profile.get("signal_count", 0),
        "next_actions": _profile_next_actions(profile),
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

import site_settings


@router.get("/site-settings", response_model=SiteSettingsResponse,
            summary="Get site settings",
            description="Returns all public site settings as a flat key-value dict. Cached for 60 seconds.")
async def get_site_settings(response: Response):
    """Public flat {key: value} dict of all site settings (cached 60s)."""
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return site_settings.get_all_public()

def _get_place(place_id: str) -> dict | None:
    with _place_cache_lock:
        if place_id in _place_cache:
            _place_cache.move_to_end(place_id)
            return _place_cache[place_id]
    place = db.get_entity(place_id)
    if place:
        with _place_cache_lock:
            _place_cache[place_id] = {"name": place["name"], "area": place.get("area")}
            if len(_place_cache) > _PLACE_CACHE_MAX:
                _place_cache.popitem(last=False)
    with _place_cache_lock:
        return _place_cache.get(place_id)

def _apply_cached_place(e: dict) -> None:
    explicit_area = e.get("area")
    pid = e.get("placeId")
    if pid:
        with _place_cache_lock:
            p = _place_cache.get(pid)
        if p:
            e["place_name"] = p["name"]
            e["place_area"] = explicit_area or p.get("area")
    elif explicit_area:
        e["place_area"] = explicit_area
    e["quality"] = entity_quality(e)


def _enrich_place(entities: list[dict]):
    with _place_cache_lock:
        uncached = {e["placeId"] for e in entities if e.get("placeId") and e["placeId"] not in _place_cache}
    if uncached:
        batch = db.get_entities_batch(list(uncached))
        with _place_cache_lock:
            for pid, place in batch.items():
                _place_cache[pid] = {"name": place["name"], "area": place.get("area")}
    for e in entities:
        _apply_cached_place(e)

def _enrich_entity_place(entity: dict):
    pid = entity.get("placeId")
    explicit_area = entity.get("area")
    if pid:
        p = _get_place(pid)
        if p:
            entity["place_name"] = p["name"]
            entity["place_area"] = explicit_area or p.get("area")
    elif explicit_area:
        entity["place_area"] = explicit_area


_MINIMAL_FIELDS = {"id", "name", "type", "summary", "images", "place_name",
                    "place_area", "coordinates", "attributes"}


def _to_minimal(entity: dict) -> dict:
    out = {k: entity[k] for k in _MINIMAL_FIELDS if k in entity}
    imgs = entity.get("images")
    if imgs and isinstance(imgs, list):
        out["images"] = imgs[:1]
    attrs = entity.get("attributes") or {}
    out["rating"] = attrs.get("rating")
    out["review_count"] = attrs.get("review_count", 0)
    return out

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

def _entity_card_shape(entity: dict, *, score: float | None = None, reason_vi: str = "") -> dict:
    area = entity.get("place_area") or entity.get("area") or entity.get("legacyArea") or ""
    place = entity.get("place") or entity.get("place_name") or ""
    image = _first_entity_image(entity)
    images = entity.get("images") if isinstance(entity.get("images"), list) else []
    if image and image not in images:
        images = [image, *images]
    return {
        "id": entity.get("id"),
        "name": entity.get("name", ""),
        "type": entity.get("type", ""),
        "summary": entity.get("summary", ""),
        "image": image,
        "images": images[:2],
        "place": place,
        "place_name": entity.get("place_name") or place,
        "place_area": area,
        "area": area,
        "score": round(float(score or 0), 4),
        "reason_vi": reason_vi,
    }

def _similar_reason_vi(reason: str) -> str:
    raw = str(reason or "")
    if "related" in raw:
        return "Lien quan trong ban do tri thuc"
    if "same_ward" in raw:
        return "Gan nhau trong cung xa phuong"
    if "same_area" in raw:
        return "Cung khu vuc kham pha"
    if "shared_tags" in raw:
        return "Co chu de trai nghiem gan nhau"
    if "same_type" in raw:
        return "Cung nhom noi dung"
    return "Phu hop de kham pha tiep"

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
    from social import (
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
    from social import _block_sql, _mute_sql
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


@router.get("/entities", response_model=EntityListResponse,
            summary="List entities",
            description="Returns a paginated list of public entities. Supports filtering by type, area, search query, month, and sorting by rating/name/newest.")
async def list_entities(
    response: Response,
    type: Optional[str] = Query(None, max_length=100),
    area: Optional[str] = Query(None, max_length=50),
    q: Optional[str] = Query(None, max_length=200),
    month: Optional[int] = Query(None, ge=1, le=12),
    sort: Optional[str] = Query(None, pattern="^(rating|newest|name)$"),
    fields: Optional[str] = Query(None, pattern="^(minimal|full)$"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=10000),
):
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    entity_types: list[str] | None = None
    single_type = type
    if type and "," in type:
        entity_types = [t.strip() for t in type.split(",") if t.strip()][:10]
        single_type = None

    db_sort = sort if sort in ("rating", "name", "newest") else None
    db_month = month if month else None

    if q:
        results = await asyncio.to_thread(db.search_entities, q=q, entity_type=single_type, area=area, limit=limit, offset=offset, entity_types=entity_types, public_only=True, month=db_month)
        total = await asyncio.to_thread(db.count_entities_filtered, entity_type=single_type, area=area, q=q, entity_types=entity_types, public_only=True, month=db_month)
    else:
        results = await asyncio.to_thread(db.list_entities, entity_type=single_type, area=area, limit=limit, offset=offset, entity_types=entity_types, public_only=True, sort=db_sort, month=db_month)
        total = await asyncio.to_thread(db.count_entities_filtered, entity_type=single_type, area=area, entity_types=entity_types, public_only=True, month=db_month)
    await asyncio.to_thread(_enrich_place, results)
    if fields == "minimal":
        results = [_to_minimal(e) for e in results]
    return {"total": total, "entities": results}


@router.get("/entities/{entity_id}/relationships",
            summary="Get entity relationships",
            description="Returns paginated relationships for a given entity. Supports filtering by relationship type and including nearby entities.")
async def get_entity_relationships(
    entity_id: str,
    response: Response,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    type: Optional[str] = Query(None, max_length=50),
    include_near: bool = True,
):
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    validate_path_id(entity_id, "entity_id")
    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        rels, t = db.get_relationships(
            entity_id, limit=limit, offset=offset,
            rel_type=type, include_near=include_near, return_total=True,
        )
        rels = _filter_public_relationships(rels)
        # `t` giữ tổng thật từ DB (return_total=True) cho pagination — KHÔNG ghi đè
        # bằng len(trang đã lọc) (sẽ đếm thiếu, client dừng phân trang sớm).
        return {"entity_id": entity_id, "total": t, "limit": limit,
                "offset": offset, "relationships": rels}
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


@router.get("/featured", response_model=FeaturedResponse,
            summary="Get featured entities",
            description="Returns up to 20 editorially featured entities sorted by display order. Includes basic entity info and images.")
async def get_featured_entities(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    def _query():
        if not db._use_pg:
            return {"featured": []}
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT entity_id, sort_order FROM featured_entities
                ORDER BY sort_order LIMIT 20
            """, ())
        entity_ids = [db._row_to_dict(r)["entity_id"] for r in rows]
        batch = db.get_entities_batch(entity_ids)
        result = []
        for eid in entity_ids:
            entity = batch.get(eid)
            if entity:
                attrs = entity.get("attributes") or {}
                result.append({
                    "id": entity["id"],
                    "name": entity["name"],
                    "type": entity.get("type"),
                    "summary": entity.get("summary", ""),
                    "images": entity.get("images", [])[:1],
                    "rating": attrs.get("rating"),
                    "coordinates": entity.get("coordinates"),
                })
        return {"featured": result}
    return await asyncio.to_thread(_query)


@router.get("/entity-types", response_model=EntityTypesResponse,
            summary="List entity types",
            description="Returns all entity types with their counts, ordered by frequency. Cached for 1 hour.")
async def entity_types(response: Response):
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, "SELECT type, COUNT(*) as count FROM entities GROUP BY type ORDER BY count DESC", ())
        return [{"type": d["type"], "count": d["count"]} for d in (db._row_to_dict(r) for r in rows)]
    result = await asyncio.to_thread(_query)
    return {"types": result, "total": sum(t["count"] for t in result)}


@router.get("/areas", response_model=AreasResponse,
            summary="List areas with places",
            description="Returns all administrative areas grouped with their places (wards/communes). Cached for 1 hour.")
async def list_areas(response: Response):
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    def _query():
        places = db.list_entities(entity_type="place", limit=1000, offset=0, public_only=True)
        areas: dict[str, list] = {}
        for p in places:
            area = p.get("area", "")
            if area not in areas:
                areas[area] = []
            areas[area].append({"id": p["id"], "name": p["name"]})
        return [{"area": k, "places": v, "count": len(v)} for k, v in sorted(areas.items())]
    result = await asyncio.to_thread(_query)
    return {"areas": result, "total_places": sum(a["count"] for a in result)}


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse,
            summary="Get entity detail",
            description="Returns full entity detail including relationships, quality score, source freshness, and practical facts. Supports ETag caching.")
async def get_entity(
    entity_id: str,
    request: Request,
    response: Response,
    relationship_limit: int = Query(DEFAULT_RELATIONSHIP_LIMIT, ge=0, le=100),
):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    if not await asyncio.to_thread(_get_public_entity, entity_id):
        return _err(404, "not_found")
    cache_key = f"{entity_id}:{relationship_limit}"
    now = _time.time()
    cached = _entity_cache.get(cache_key)
    if cached and now - cached[0] < _ENTITY_TTL:
        _entity_cache.move_to_end(cache_key)
        etag = cached[2] if len(cached) > 2 else None
        if etag:
            response.headers["ETag"] = etag
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=60, stale-while-revalidate=120"})
        return cached[1]

    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        rels, rel_total = db.get_relationships(entity_id, limit=relationship_limit, return_total=True)
        rels = _filter_public_relationships(rels)
        # rel_total giữ tổng thật từ DB (return_total=True) — KHÔNG ghi đè bằng
        # len(trang đã lọc) để pagination quan hệ không đếm thiếu.
        e["relationship_total"] = rel_total
        e["relationships"] = rels
        _enrich_entity_place(e)
        e["quality"] = entity_quality(e)
        e["source_freshness"] = _build_source_freshness(e)
        e["practical_facts"] = _build_practical_facts(e)
        return e
    entity = await asyncio.to_thread(_query)
    if not entity:
        return _err(404, "not_found")

    etag = f'W/"{hashlib.md5(json.dumps(entity, sort_keys=True, default=str).encode()).hexdigest()[:16]}"'
    response.headers["ETag"] = etag
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=60, stale-while-revalidate=120"})

    _entity_cache[cache_key] = (now, entity, etag)
    while len(_entity_cache) > _ENTITY_CACHE_MAX:
        _entity_cache.popitem(last=False)

    return entity


@router.get("/entities/{entity_id}/stats",
            summary="Get entity social stats",
            description="Returns aggregated social stats for an entity: review count, average rating, post count, bookmark count, and follower count.")
async def get_entity_stats(entity_id: str, response: Response):
    validate_path_id(entity_id, "entity_id")
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    ph = db._ph
    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        with db._conn() as conn:
            review_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as review_count,
                       COALESCE(AVG(rating), 0) as avg_rating
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                  AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
            """, (entity_id,))
            post_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as post_count FROM posts
                WHERE entity_id = {ph} AND moderation_status = 'approved' AND deleted_at IS NULL
            """, (entity_id,))
            bookmark_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as bookmark_count FROM saved_entities
                WHERE entity_id = {ph}
            """, (entity_id,))
            follow_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as follower_count FROM follows
                WHERE target_id = {ph} AND target_type = 'entity'
            """, (entity_id,))
        rd = db._row_to_dict(review_row) if review_row else {}
        pd = db._row_to_dict(post_row) if post_row else {}
        bd = db._row_to_dict(bookmark_row) if bookmark_row else {}
        fd = db._row_to_dict(follow_row) if follow_row else {}
        return {
            "entity_id": entity_id,
            "review_count": rd.get("review_count", 0),
            "avg_rating": round(float(rd.get("avg_rating", 0)), 1),
            "post_count": pd.get("post_count", 0),
            "bookmark_count": bd.get("bookmark_count", 0),
            "follower_count": fd.get("follower_count", 0),
        }
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


@router.get("/entities/{entity_id}/rating-breakdown",
            summary="Get entity rating breakdown",
            description="Returns 5-star rating distribution with counts, percentages, total reviews, and average rating for an entity. Requires Postgres.")
async def get_entity_rating_breakdown(entity_id: str, response: Response):
    """5-star rating distribution for an entity."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    require_pg()
    ph = db._ph

    def _query():
        e = _get_public_entity(entity_id)
        if not e:
            return None
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT rating, COUNT(*) as count
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                  AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
                GROUP BY rating ORDER BY rating DESC
            """, (entity_id,))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as total, COALESCE(AVG(rating), 0) as avg
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                  AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
            """, (entity_id,))
        breakdown = {str(i): 0 for i in range(1, 6)}
        for r in rows:
            rd = db._row_to_dict(r)
            rating = rd.get("rating")
            count = rd.get("count", 0)
            if rating is not None:
                star = str(int(rating))
                if star in breakdown:
                    breakdown[star] = count
        td = db._row_to_dict(total_row) if total_row else {}
        total = td.get("total", 0)
        return {
            "entity_id": entity_id,
            "breakdown": breakdown,
            "total_reviews": total,
            "avg_rating": round(float(td.get("avg", 0)), 1),
            "percentages": {k: round(v / total * 100, 1) if total > 0 else 0 for k, v in breakdown.items()},
        }

    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


def _shape_review_row(rd: dict) -> dict:
    images = rd.get("images", [])
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except (json.JSONDecodeError, ValueError, TypeError):
            images = []
    return {
        "id": str(rd["id"]),
        "content": rd["content"],
        "rating": rd.get("rating"),
        "images": images,
        "like_count": rd.get("like_count", 0),
        "comment_count": rd.get("comment_count", 0),
        "created_at": str(rd.get("created_at", "")),
        "author": {
            "id": str(rd.get("user_id", "")),
            "display_name": rd.get("display_name", ""),
            "username": rd.get("username"),
            "avatar_url": rd.get("avatar_url"),
        },
    }


@router.get("/entities/{entity_id}/reviews",
            summary="Get entity reviews",
            description="Returns paginated user reviews for an entity with sorting, rating filter, distribution, and the current user's own review if logged in.")
async def get_entity_reviews(
    entity_id: str,
    response: Response,
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    sort: str = Query("newest", pattern="^(newest|helpful|highest|lowest)$"),
    min_rating: int = Query(None, ge=1, le=5),
    user=Depends(get_current_user),
):
    validate_path_id(entity_id, "entity_id")
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    if not await asyncio.to_thread(_get_public_entity, entity_id):
        return _err(404, "not_found")
    ph = db._ph
    offset = (page - 1) * limit
    uid = str(user["id"]) if user else None
    _REVIEW_SORT = {"newest": "p.created_at DESC", "helpful": "p.like_count DESC, p.created_at DESC",
                     "highest": "p.rating DESC, p.created_at DESC", "lowest": "p.rating ASC, p.created_at DESC"}
    order = _REVIEW_SORT.get(sort, "p.created_at DESC")
    def _query():
        conditions = [f"p.entity_id = {ph}", "p.post_type = 'review'", "p.moderation_status = 'approved'", "p.deleted_at IS NULL"]
        params = [entity_id]
        if min_rating is not None:
            conditions.append(f"p.rating >= {ph}")
            params.append(min_rating)
        where = " AND ".join(conditions)
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.user_id, p.content, p.rating, p.images, p.like_count,
                       p.comment_count, p.created_at, u.display_name, u.avatar_url, u.username
                FROM posts p JOIN users u ON u.id = p.user_id
                WHERE {where}
                ORDER BY {order}
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c, COALESCE(AVG(p.rating), 0) as avg_rating
                FROM posts p WHERE {where}
            """, tuple(params))
            dist_rows = db._fetchall(conn, f"""
                SELECT p.rating, COUNT(*) as cnt FROM posts p
                WHERE p.entity_id = {ph} AND p.post_type = 'review'
                  AND p.moderation_status = 'approved' AND p.deleted_at IS NULL AND p.rating IS NOT NULL
                GROUP BY p.rating ORDER BY p.rating DESC
            """, (entity_id,))
            my_review = None
            if uid:
                my_row = db._fetchone(conn, f"""
                    SELECT p.id, p.rating, p.content, p.created_at FROM posts p
                    WHERE p.entity_id = {ph} AND p.user_id = {ph}::uuid
                      AND p.post_type = 'review' AND p.moderation_status = 'approved' AND p.deleted_at IS NULL
                    ORDER BY p.created_at DESC LIMIT 1
                """, (entity_id, uid))
                if my_row:
                    mr = db._row_to_dict(my_row)
                    my_review = {"id": str(mr["id"]), "rating": mr["rating"],
                                 "content": mr["content"][:100], "created_at": str(mr.get("created_at", ""))}
        return rows, total_row, dist_rows, my_review
    rows, total_row, dist_rows, my_review = await asyncio.to_thread(_query)
    td = db._row_to_dict(total_row) if total_row else {}
    total = td.get("c", 0)
    distribution = {str(db._row_to_dict(r).get("rating", 0)): db._row_to_dict(r).get("cnt", 0) for r in dist_rows}
    reviews = [_shape_review_row(db._row_to_dict(r)) for r in rows]
    result = {
        "reviews": reviews,
        "total": total,
        "avg_rating": round(float(td.get("avg_rating", 0)), 1),
        "distribution": distribution,
        "page": page,
        "has_more": offset + limit < total,
    }
    if my_review is not None:
        result["my_review"] = my_review
    return result


@router.get("/places",
            summary="List places",
            description="Returns all place entities (wards/communes) with id, name, area, and level. Optionally filtered by area. Cached for 1 hour.")
async def list_places(response: Response, area: Optional[str] = Query(None, max_length=100)):
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    db.initialize()
    def _query():
        ph = db._ph
        with db._conn() as conn:
            if area:
                rows = db._fetchall(conn,
                    f"SELECT id, name, area, level FROM entities WHERE type = 'place' AND area = {ph} ORDER BY name",
                    (area,))
            else:
                rows = db._fetchall(conn,
                    "SELECT id, name, area, level FROM entities WHERE type = 'place' ORDER BY name LIMIT 500")
        return [db._row_to_dict(r) for r in rows]
    return await asyncio.to_thread(_query)


@router.get("/facilities",
            summary="List public facilities",
            description="Returns administrative facilities (government offices, police, etc.) for a given ward/commune. Cached for 1 hour.")
async def list_facilities(response: Response, place: Optional[str] = Query(None, max_length=100)):
    """GĐ13.4: danh bạ hành chính — cơ quan công vụ (UBND/công an/...) theo xã/phường."""
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=7200"
    facilities = await asyncio.to_thread(db.facilities_by_place, place)
    return {"facilities": facilities}


# Nhóm loại entity cho trang hub xã/phường (theo 4 mục người dùng cần).
_WARD_GROUPS = {
    "tourism": {"attraction", "nature", "experience", "craft_village", "history", "event"},
    "lodging": {"accommodation"},
    "products": {"product", "dish", "drink"},
}


@router.get("/places/{place_id}/overview",
            summary="Get place overview",
            description="Returns a ward/commune hub page with facilities, tourism, lodging, and product entities grouped by category with counts.")
async def place_overview(place_id: str, response: Response):
    """Trang hub 1 xã/phường: danh bạ hành chính + du lịch + lưu trú + sản phẩm.

    Gom theo placeId trong 1 lượt gọi. facilities rỗng đến khi có dữ liệu thật (Track-H 13.6).
    """
    validate_path_id(place_id, "place_id")
    def _query():
        p = db.get_entity(place_id)
        if not p or p.get("type") != "place":
            return None
        ents = db.entities_by_place(place_id)
        groups: dict[str, list] = {"tourism": [], "lodging": [], "products": [], "other": []}
        for e in ents:
            t = e.get("type")
            placed = False
            for g, types in _WARD_GROUPS.items():
                if t in types:
                    groups[g].append(e)
                    placed = True
                    break
            if not placed:
                groups["other"].append(e)
        return {
            "place": {"id": p["id"], "name": p.get("name"), "area": p.get("area"),
                      "level": p.get("level"), "summary": p.get("summary"),
                      "attributes": p.get("attributes", {}),
                      "coordinates": p.get("coordinates")},
            "facilities": db.facilities_by_place(place_id),
            "counts": {g: len(v) for g, v in groups.items()},
            "tourism": groups["tourism"],
            "lodging": groups["lodging"],
            "products": groups["products"],
            "other": groups["other"],
        }
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "Không phải xã/phường")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return result


_DAY_PLAN_TYPE_PRIORITY = [
    "attraction", "nature", "history", "experience", "craft_village",
    "dish", "drink", "product", "market", "accommodation", "event",
]
_DAY_PLAN_SLOTS = [
    {"label": "sáng", "start": "08:00", "duration_min": 60},
    {"label": "sáng", "start": "09:30", "duration_min": 45},
    {"label": "trưa", "start": "11:00", "duration_min": 60},
    {"label": "chiều", "start": "13:30", "duration_min": 60},
    {"label": "chiều", "start": "15:00", "duration_min": 45},
    {"label": "chiều", "start": "16:30", "duration_min": 45},
]


def _haversine_km(a: list | None, b: list | None) -> float:
    if not a or not b or len(a) < 2 or len(b) < 2:
        return 999.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def _select_day_plan_candidates(ents: list[dict], center) -> list[dict]:
    seen_types: set = set()
    candidates = []
    for e in sorted(ents, key=lambda x: _haversine_km(center, x.get("coordinates"))):
        t = e.get("type")
        if t in seen_types or t == "place":
            continue
        seen_types.add(t)
        candidates.append(e)
        if len(candidates) >= len(_DAY_PLAN_SLOTS):
            break
    if not candidates and ents:
        candidates = ents[:len(_DAY_PLAN_SLOTS)]
    return candidates


def _build_day_plan_stops(candidates: list[dict]) -> list[dict]:
    stops = []
    for i, e in enumerate(candidates):
        slot = _DAY_PLAN_SLOTS[i] if i < len(_DAY_PLAN_SLOTS) else _DAY_PLAN_SLOTS[-1]
        stops.append({
            "entity_id": e["id"],
            "name": e.get("name"),
            "type": e.get("type"),
            "suggested_time": slot["start"],
            "time_of_day": slot["label"],
            "visit_duration_min": slot["duration_min"],
            "coordinates": e.get("coordinates"),
        })
    return stops


@router.get("/places/{place_id}/day-plan",
            summary="Get place day plan",
            description="Returns a suggested one-day itinerary for a ward/commune with diverse entity types ordered by proximity. Includes time slots and durations.")
async def place_day_plan(place_id: str, response: Response):
    """Gợi ý lịch trình 1 ngày cho xã/phường — đa dạng loại hình, sắp theo khoảng cách."""
    validate_path_id(place_id, "place_id")

    def _query():
        p = db.get_entity(place_id)
        if not p or p.get("type") != "place":
            return None
        ents = db.entities_by_place(place_id)
        center = p.get("coordinates")
        candidates = _select_day_plan_candidates(ents, center)
        stops = _build_day_plan_stops(candidates)
        total_min = sum(s["visit_duration_min"] for s in stops)
        return {
            "place": {"id": p["id"], "name": p.get("name"), "area": p.get("area")},
            "stops": stops,
            "total_stops": len(stops),
            "total_duration_min": total_min,
        }

    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "Không phải xã/phường")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return result


@router.get("/itineraries",
            summary="List itineraries",
            description="Returns paginated travel itineraries. Optionally filtered by area. Cached for 5 minutes.")
async def list_itineraries(
    response: Response,
    area: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return await asyncio.to_thread(db.list_itineraries, area=area, limit=limit, offset=offset)


@router.get("/itineraries/{itin_id}",
            summary="Get itinerary detail",
            description="Returns a single itinerary with stops enriched with entity names, summaries, types, and coordinates.")
async def get_itinerary(itin_id: str, response: Response):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    validate_path_id(itin_id, "itin_id")
    def _query():
        it = db.get_itinerary(itin_id)
        if not it:
            return None
        stop_ids = [sid for sid in (_itinerary_stop_entity_id(s) for s in it.get("stops", [])) if sid]
        entities = db.get_entities_batch(stop_ids)
        for stop in it.get("stops", []):
            if not isinstance(stop, dict):
                continue
            stop_id = _itinerary_stop_entity_id(stop)
            entity = entities.get(stop_id)
            if entity:
                stop.setdefault("id", stop_id)
                stop.setdefault("entityId", stop_id)
                stop["name"] = entity["name"]
                if not stop.get("summary"):
                    stop["summary"] = entity.get("summary", "")
                stop["type"] = entity["type"]
                if entity.get("coordinates"):
                    stop["coordinates"] = entity["coordinates"]
        return it
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


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
    qn = _normalize_text(query)
    terms = [t for t in qn.split() if t]
    ranked = []
    for idx, item in enumerate(items):
        name = _normalize_text(item.get("name", ""))
        summary = _normalize_text(item.get("summary", ""))
        score, reason = _lexical_match_score(name, summary, qn, terms)
        score += float(item.get("confidence") or 0) * 10
        copy = dict(item)
        copy["_search_meta"] = {"score": round(score, 2), "reason": reason, "rank_source": "lexical"}
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
    user=Depends(get_current_user),
):
    from ratelimit import check_rate
    check_rate(f"search:{get_client_ip(request)}", 30, 60, "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
    entity_limit = min(limit, 100)
    social_limit = min(max(3, limit // 3), 10)
    results = await asyncio.to_thread(db.search_entities, q=q, entity_type=type, area=area, limit=entity_limit, public_only=True)
    await asyncio.to_thread(_enrich_place, results)
    results = _rank_search_entities(results, q)
    total = await asyncio.to_thread(db.count_entities_filtered, entity_type=type, area=area, q=q, public_only=True)
    safe_q = re.sub(r"<[^>]+>", "", q)
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
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    results = await asyncio.to_thread(db.search_entities, q=q, entity_type=type, limit=limit)
    return {
        "suggestions": [
            {"id": e["id"], "name": e["name"], "type": e.get("type", ""),
             "place": e.get("place", "")}
            for e in results
        ],
    }


@router.get("/me/activity",
            summary="Get current user activity",
            description="Returns the authenticated user's recent activity feed combining posts, comments, and likes sorted by recency. Requires authentication.")
async def user_activity(
    request: Request,
    response: Response,
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(require_user),
):
    from ratelimit import check_rate
    check_rate(f"activity:{user['id']}", 20, 60, "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    ph = db._ph
    offset = (page - 1) * limit
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            posts = db._fetchall(conn, f"""
                SELECT id, content, post_type, entity_id, created_at, like_count, comment_count
                FROM posts WHERE user_id = {ph}::uuid AND moderation_status != 'rejected' AND deleted_at IS NULL
                ORDER BY created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
            comments = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.post_id, c.created_at, p.entity_id
                FROM comments c JOIN posts p ON p.id = c.post_id
                WHERE c.user_id = {ph}::uuid
                ORDER BY c.created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
            likes = db._fetchall(conn, f"""
                SELECT l.post_id, l.created_at, p.content, p.entity_id
                FROM likes l JOIN posts p ON p.id = l.post_id
                WHERE l.user_id = {ph}::uuid
                ORDER BY l.created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
        return (
            [db._row_to_dict(r) for r in posts],
            [db._row_to_dict(r) for r in comments],
            [db._row_to_dict(r) for r in likes],
        )
    posts, comments, likes = await asyncio.to_thread(_query)
    for p in posts:
        p["id"] = str(p["id"])
        p["type"] = "post"
    for c in comments:
        c["id"] = str(c["id"])
        c["post_id"] = str(c["post_id"])
        c["type"] = "comment"
    for lk in likes:
        lk["post_id"] = str(lk["post_id"])
        lk["type"] = "like"
    items = sorted(posts + comments + likes, key=lambda x: str(x.get("created_at", "")), reverse=True)[:limit]
    response.headers["Cache-Control"] = "private, max-age=30"
    return {"activity": items, "page": page, "has_more": len(items) == limit}


@router.get("/stats", response_model=StatsResponse,
            summary="Get public stats",
            description="Returns aggregate platform statistics including entity counts, user counts, and other summary metrics. Cached for 5 minutes.")
async def public_stats(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return await asyncio.to_thread(db.stats)


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
    return event_date < datetime.now(timezone.utc).date()


_GENERIC_NAMES = {"tắm sông", "đi ghe", "đi đò", "tham quan", "du lịch",
                   "ăn uống", "mua sắm", "chụp ảnh", "câu cá", "dạo phố"}


def _homepage_score(e: dict, month: int) -> float:
    from smart_rank import smart_score
    s = smart_score(e, month=month, q_match_level="none")
    if e.get("images"):
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


def _score_one_itinerary(it: dict, public: list[dict], month: int) -> float:
    it_score = 0.0
    stops = it.get("stops") or []
    for stop in stops:
        eid = _itinerary_stop_entity_id(stop)
        matched = next((e for e in public if e["id"] == eid), None)
        if matched:
            if _entity_in_season(matched, month):
                it_score += 2.0
            if matched.get("images"):
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
    for it in all_itineraries:
        it["_score"] = _score_one_itinerary(it, public, month)
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


def _finalize_homepage_sections(sections: list[list[dict]], upcoming_events: list[dict]) -> None:
    for section in sections:
        for e in section:
            e.pop("_score", None)
    for e in upcoming_events:
        e.pop("_score", None)
        e["days_until"] = e.pop("_days_until", None)


async def _build_homepage_payload(month: int) -> dict:
    all_ents = await asyncio.to_thread(db.list_entities, limit=5000, offset=0, public_only=True)
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
    today = datetime.now(timezone.utc).date()
    from datetime import timedelta
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
    }


@router.get("/homepage", response_model=HomepageResponse,
            summary="Get curated homepage feed",
            description="Returns the curated homepage with seasonal picks, diverse experiences, products, top dishes, trending entities, upcoming events, itineraries, and area counts. Cached for 2 minutes.")
async def homepage_curated(response: Response):
    """Curated homepage: smart-scored, type/area diverse, seasonal-aware, deduped."""
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    month = datetime.now(timezone.utc).month

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
        all_ents = db.list_entities(limit=5000, offset=0, area=area, public_only=True, entity_types=type_filters)
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
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    """Sự kiện: sắp xếp theo date_start, mặc định ẩn sự kiện đã qua."""
    today = datetime.now(timezone.utc).date()
    all_ents = await asyncio.to_thread(db.list_entities, entity_type="event", limit=2000, offset=0, public_only=True)
    events = list(all_ents)
    _enrich_place(events)

    if area:
        events = [e for e in events
                  if (e.get("place_area") or e.get("area")) == area]

    if not include_past:
        events = [e for e in events if not _event_is_past(e)]

    events = [e for e in events if _event_date_reliable(e)]
    events.sort(key=lambda e: _event_sort_key(e, today))
    return {"total": len(events), "events": events[:limit]}


_REPORT_FIELD_OPTIONS = {"phone", "hours", "address", "source", "name", "price", "images", "other"}


class ReportIn(BaseModel):
    target_id: str = Field(..., min_length=1, max_length=200)
    target_type: str = Field("entity", max_length=20)
    reason: str = Field(..., min_length=1, max_length=60)
    detail: str = Field("", max_length=2000)
    contact: str = Field("", max_length=120)
    field: Optional[str] = Field(None, max_length=20)


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

def _gallery_editorial_images(entity: dict) -> list[dict]:
    images: list[dict] = []
    attrs = entity.get("attributes") or {}
    default_credit = attrs.get("image_credit", "AI-generated")
    for url in (entity.get("images") or []):
        if isinstance(url, str) and url:
            images.append({
                "url": url,
                "alt": f"{entity['name']} — ảnh {len(images) + 1}",
                "credit": default_credit,
                "width": None,
                "height": None,
            })
    return images


def _append_review_gallery_images(images: list[dict], review_rows: list[dict], entity_name: str) -> None:
    for row in review_rows:
        review_imgs = row.get("images") or []
        if isinstance(review_imgs, str):
            try:
                review_imgs = json.loads(review_imgs)
            except (json.JSONDecodeError, ValueError):
                continue
        credit = row.get("display_name", "Người dùng")
        for url in review_imgs:
            if isinstance(url, str) and url:
                images.append({
                    "url": url,
                    "alt": f"{entity_name} — ảnh đánh giá",
                    "credit": credit,
                    "width": None,
                    "height": None,
                })


@router.get("/entities/{entity_id}/gallery",
            summary="Get entity image gallery",
            description="Returns all images for an entity including editorial images and user review photos with credits and alt text.")
async def get_entity_gallery(entity_id: str, response: Response):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"

    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        return _err(404, "not_found")

    images = _gallery_editorial_images(entity)

    if db._use_pg:
        ph = db._ph
        def _review_images():
            with db._conn() as conn:
                rows = db._fetchall(conn, f"""
                    SELECT p.images, u.display_name
                    FROM posts p
                    JOIN users u ON u.id = p.user_id
                    WHERE p.entity_id = {ph} AND p.post_type = 'review'
                        AND p.moderation_status = 'approved' AND p.deleted_at IS NULL
                        AND p.images IS NOT NULL
                    ORDER BY p.created_at DESC
                    LIMIT 50
                """, (entity_id,))
            return [db._row_to_dict(r) for r in rows]

        try:
            review_rows = await asyncio.to_thread(_review_images)
            _append_review_gallery_images(images, review_rows, entity["name"])
        except Exception:
            logger.exception("gallery review-images query failed for %s", entity_id)

    return {"images": images, "total": len(images)}


# ── Review stats (rating distribution + mention extraction) ──────────

_REVIEW_STATS_CACHE: dict[str, tuple[float, dict]] = {}
_REVIEW_STATS_TTL = 300

_VN_STOPWORDS = frozenset(
    "và của là này đó có không được cho với từ tại ở về để bị do theo "
    "đã sẽ đang rất rồi nhưng hay hoặc nếu thì mà cũng các những một nhiều "
    "khi nên ra vào lên xuống đi lại còn quá nào ai gì sao thế nữa đây".split()
)
_PUNCT_RE = re.compile(r"[.,!?;:\"'()\[\]{}<>/\\@#$%^&*+=~`|…–—]")


def _extract_mentions(texts: list[str], top_n: int = 8) -> list[dict]:
    unigrams: Counter = Counter()
    bigrams: Counter = Counter()
    for text in texts:
        clean = _PUNCT_RE.sub(" ", text.lower())
        words = [w for w in clean.split() if w and w not in _VN_STOPWORDS and len(w) > 1]
        unigrams.update(words)
        for i in range(len(words) - 1):
            bigrams[f"{words[i]} {words[i+1]}"] += 1
    combined: Counter = Counter()
    for w, c in unigrams.items():
        if c >= 2:
            combined[w] = c
    for bg, c in bigrams.items():
        if c >= 2:
            combined[bg] = c
    return [{"keyword": kw, "count": cnt} for kw, cnt in combined.most_common(top_n)]


def _int0(v) -> int:
    """int() null-safe: NULL/None/'' → 0 (dùng cho review stats từ DB)."""
    return int(v or 0)


@router.get("/entities/{entity_id}/review-stats",
            summary="Get entity review stats",
            description="Returns review statistics for an entity: average rating, distribution by star, and frequently mentioned keywords extracted from review text.")
async def get_review_stats(entity_id: str, response: Response):
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        return _err(404, "not_found")

    now = _time.time()
    cached = _REVIEW_STATS_CACHE.get(entity_id)
    if cached and now - cached[0] < _REVIEW_STATS_TTL:
        return cached[1]

    _empty = {"avg": 0, "count": 0, "distribution": {}, "mentions": []}

    if not db._use_pg:
        return _empty

    ph = db._ph

    def _query():
        with db._conn() as conn:
            dist_rows = db._fetchall(conn, f"""
                SELECT rating, COUNT(*) as cnt
                FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                    AND moderation_status = 'approved' AND deleted_at IS NULL AND rating IS NOT NULL
                GROUP BY rating
            """, (entity_id,))
            content_rows = db._fetchall(conn, f"""
                SELECT content FROM posts
                WHERE entity_id = {ph} AND post_type = 'review'
                    AND moderation_status = 'approved' AND deleted_at IS NULL AND content IS NOT NULL
                    AND content != ''
                ORDER BY created_at DESC LIMIT 200
            """, (entity_id,))
        return dist_rows, content_rows

    try:
        dist_rows, content_rows = await asyncio.to_thread(_query)
    except Exception:
        logger.exception("review-stats query failed for %s", entity_id)
        return _empty

    distribution = {}
    total = 0
    weighted_sum = 0
    for row in dist_rows:
        r = db._row_to_dict(row)
        rating = _int0(r.get("rating"))
        cnt = _int0(r.get("cnt"))
        distribution[str(rating)] = cnt
        total += cnt
        weighted_sum += rating * cnt

    avg = round(weighted_sum / total, 1) if total > 0 else 0

    texts = [db._row_to_dict(r)["content"] for r in content_rows]
    mentions = _extract_mentions(texts)

    result = {"avg": avg, "count": total, "distribution": distribution, "mentions": mentions}
    _REVIEW_STATS_CACHE[entity_id] = (now, result)
    if len(_REVIEW_STATS_CACHE) > 500:
        oldest = min(_REVIEW_STATS_CACHE, key=lambda k: _REVIEW_STATS_CACHE[k][0])
        _REVIEW_STATS_CACHE.pop(oldest, None)
    return result


# ── Similar entity recommendations (U-29: rule-based) ────────────────

_similar_cache: OrderedDict[str, tuple[float, list]] = OrderedDict()
_SIMILAR_TTL = 300  # 5 min cache


def _build_similar_cards(raw_items: list[dict], full_entities: dict, entities_map: dict) -> list[dict]:
    cards: list[dict] = []
    for item in raw_items:
        candidate = full_entities.get(str(item.get("id"))) or entities_map.get(str(item.get("id"))) or item
        reason_vi = _similar_reason_vi(str(item.get("reason") or ""))
        card = _entity_card_shape(candidate, score=float(item.get("score") or 0), reason_vi=reason_vi)
        card["reason"] = item.get("reason", "")
        cards.append(card)
    return cards


def _compute_similar_entities(entity_id: str, limit: int) -> list[dict] | None:
    try:
        import knowledge
        knowledge._ensure()
        entities_map = {eid: e for eid, e in knowledge._entities.items() if _is_public(e)}
        rels = knowledge._relationships if hasattr(knowledge, "_relationships") else []
    except Exception:
        logger.warning("Knowledge load failed for recommendations", exc_info=True)
        return None
    if entity_id not in entities_map:
        return None
    from recommender import recommend_by_entity
    raw_items = recommend_by_entity(entity_id, entities_map, rels, limit=limit)
    entity_ids = [str(item.get("id")) for item in raw_items if item.get("id")]
    full_entities = db.get_entities_batch(entity_ids) if entity_ids else {}
    if full_entities:
        _enrich_place(list(full_entities.values()))
    return _build_similar_cards(raw_items, full_entities, entities_map)


@router.get("/entities/{entity_id}/similar",
            summary="Get similar entities",
            description="Returns rule-based similar entity recommendations based on type, area, and relationship graph. No ML required. Cached for 5 minutes.")
async def get_similar_entities(
    entity_id: str,
    response: Response,
    limit: int = Query(6, ge=1, le=20),
):
    """U-29: Rule-based similar entity recommendations (no ML)."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    if not await asyncio.to_thread(_get_public_entity, entity_id):
        return _err(404, "not_found")

    now = _time.time()
    cache_key = f"{entity_id}:{limit}"
    cached = _similar_cache.get(cache_key)
    if cached and now - cached[0] < _SIMILAR_TTL:
        _similar_cache.move_to_end(cache_key)
        return {"entity_id": entity_id, "similar": cached[1]}

    result = await asyncio.to_thread(_compute_similar_entities, entity_id, limit)
    if result is None:
        entity = await asyncio.to_thread(_get_public_entity, entity_id)
        if not entity:
            return _err(404, "not_found")
        return {"entity_id": entity_id, "similar": []}

    _similar_cache[cache_key] = (now, result)
    while len(_similar_cache) > 200:
        _similar_cache.popitem(last=False)

    return {"entity_id": entity_id, "similar": result}


@router.get("/entities/{entity_id}/nearby",
            summary="Get nearby entities",
            description="Returns entities within a given radius (km) of the specified entity, sorted by distance. Optionally filtered by entity type.")
async def get_nearby_entities(
    entity_id: str,
    response: Response,
    limit: int = Query(10, ge=1, le=30),
    radius_km: float = Query(10.0, ge=0.5, le=50.0),
    type: str = Query(None, max_length=50),
):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    validate_path_id(entity_id, "entity_id")
    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    center = entity.get("coordinates")
    if not center or not isinstance(center, (list, tuple)) or len(center) < 2:
        return {"entity_id": entity_id, "nearby": [], "message": "Entity không có tọa độ"}
    def _query():
        type_filters = [type] if type else None
        all_ents = db.list_entities(limit=3000, offset=0, public_only=True, entity_types=type_filters)
        nearby = []
        for e in all_ents:
            if e["id"] == entity_id:
                continue
            dist = _haversine_km(center, e.get("coordinates"))
            if dist <= radius_km:
                nearby.append({
                    "id": e["id"],
                    "name": e["name"],
                    "type": e.get("type"),
                    "distance_km": round(dist, 2),
                    "coordinates": e.get("coordinates"),
                })
        nearby.sort(key=lambda x: x["distance_km"])
        return nearby[:limit]
    result = await asyncio.to_thread(_query)
    return {"entity_id": entity_id, "nearby": result, "radius_km": radius_km}


# ── Entity Q&A (U-09: questions with best answer resolution) ─────────

from fastapi import Depends

@router.get("/entities/{entity_id}/qa",
            dependencies=[Depends(require_pg)],
            summary="Get entity Q&A",
            description="Returns paginated Q&A posts for an entity with accepted answer resolution. Questions with best answers are shown first. Requires Postgres.")
async def get_entity_qa(
    entity_id: str,
    response: Response,
    page: int = Query(1, ge=1, le=100),
    limit: int = Query(10, ge=1, le=50),
):
    """U-09: Surface Q&A posts for an entity with accepted answer resolution."""
    validate_path_id(entity_id, "entity_id")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"

    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        return _err(404, "not_found")

    ph = db._ph
    offset = (page - 1) * limit

    def _qa_query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.content, p.created_at, p.user_id, p.best_answer_id,
                       p.comment_count, p.like_count,
                       u.display_name, u.avatar_url, u.username
                FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE p.entity_id = {ph}
                  AND p.post_type = 'question'
                  AND p.moderation_status = 'approved' AND p.deleted_at IS NULL
                ORDER BY (CASE WHEN p.best_answer_id IS NOT NULL THEN 0 ELSE 1 END),
                         p.like_count DESC, p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (entity_id, limit, offset))

            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts
                WHERE entity_id = {ph} AND post_type = 'question'
                  AND moderation_status = 'approved' AND deleted_at IS NULL
            """, (entity_id,))

            questions = []
            for r in rows:
                d = db._row_to_dict(r)
                q = {
                    "id": d["id"],
                    "content": d["content"],
                    "created_at": d["created_at"],
                    "user": {
                        "id": d["user_id"],
                        "display_name": d.get("display_name"),
                        "avatar_url": d.get("avatar_url"),
                        "username": d.get("username"),
                    },
                    "comment_count": d.get("comment_count", 0),
                    "like_count": d.get("like_count", 0),
                    "best_answer_id": d.get("best_answer_id"),
                    "best_answer": None,
                }
                if d.get("best_answer_id"):
                    answer = db._fetchone(conn, f"""
                        SELECT c.id, c.content, c.created_at, c.user_id,
                               u2.display_name, u2.avatar_url, u2.username
                        FROM comments c
                        JOIN users u2 ON u2.id = c.user_id
                        WHERE c.id = {ph}
                    """, (d["best_answer_id"],))
                    if answer:
                        a = db._row_to_dict(answer)
                        q["best_answer"] = {
                            "id": a["id"],
                            "content": a["content"],
                            "created_at": a["created_at"],
                            "user": {
                                "id": a["user_id"],
                                "display_name": a.get("display_name"),
                                "avatar_url": a.get("avatar_url"),
                                "username": a.get("username"),
                            },
                        }
                questions.append(q)
            return questions, db._row_to_dict(total_row) if total_row else {}

    questions, total_d = await asyncio.to_thread(_qa_query)
    total = total_d.get("c", 0)
    return {
        "entity_id": entity_id,
        "questions": questions,
        "total": total,
        "has_more": (page * limit) < total,
    }


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

class EntityClaimIn(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=200)
    contact_phone: str = Field(..., min_length=10, max_length=15)
    contact_email: str = Field("", max_length=200)
    evidence: str = Field("", max_length=2000)


@router.post("/entities/{entity_id}/claim",
             dependencies=[Depends(require_pg)],
             summary="Submit entity ownership claim",
             description="Submits a business ownership claim for an entity. Requires authentication and CSRF. Limited to 3 claims per day per user. Requires Postgres.")
async def submit_entity_claim(entity_id: str, payload: EntityClaimIn, request: Request, user=Depends(require_user), _csrf=Depends(require_csrf)):
    validate_path_id(entity_id, "entity_id")
    from ratelimit import check_rate
    check_rate(f"claim:{user['id']}", 3, 86400, "Chỉ được gửi 3 yêu cầu xác nhận/ngày.")
    uid = str(user["id"])
    entity = await asyncio.to_thread(_get_public_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entity không tồn tại")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            existing = db._fetchone(conn, f"""
                SELECT id, status FROM entity_claims
                WHERE entity_id = {ph} AND claimant_id::text = {ph}
            """, (entity_id, uid))
            if existing:
                st = db._row_to_dict(existing)["status"]
                if st == "pending":
                    raise HTTPException(409, "Bạn đã gửi yêu cầu xác nhận cho entity này")
                if st == "approved":
                    raise HTTPException(409, "Entity này đã được xác nhận cho bạn")
            import html as _html
            db._execute(conn, f"""
                INSERT INTO entity_claims (entity_id, claimant_id, business_name, contact_phone, contact_email, evidence)
                VALUES ({ph}, {ph}::uuid, {ph}, {ph}, {ph}, {ph})
            """, (entity_id, uid, _html.escape(payload.business_name.strip()),
                  payload.contact_phone.strip(), payload.contact_email.strip(),
                  _html.escape(payload.evidence.strip()) if payload.evidence else ""))
    await asyncio.to_thread(_query)
    return {"success": True, "message": "Yêu cầu xác nhận đã được gửi. Chúng tôi sẽ xem xét."}


# ── What's-new feed (U-15) ────────────────────────────────────────────


def _collect_new_entities(entities: dict, since_dt, limit: int) -> list[dict]:
    new_entities = []
    for eid, e in entities.items():
        if e.get("type") == "place" or not _is_public(e):
            continue
        updated = e.get("updatedAt") or e.get("created_at")
        if not updated:
            continue
        try:
            dt = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if dt >= since_dt:
            new_entities.append({
                "id": eid, "name": e.get("name"), "type": e.get("type"),
                "area": e.get("area"), "updated_at": str(updated),
            })
    new_entities.sort(key=lambda x: x["updated_at"], reverse=True)
    return new_entities[:limit]


@router.get("/feed/new-since",
            summary="Get new content since timestamp",
            description="Returns entities and posts created or updated since a given ISO datetime. Useful for incremental feed updates.")
async def feed_new_since(
    response: Response,
    since: str = Query(..., min_length=10, max_length=30),
    limit: int = Query(50, ge=1, le=100),
):
    """Mới cập nhật/tạo từ `since` — entities + posts (public only)."""
    from database import db as _db
    ph = _db._ph
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return _err(400, "since phải là ISO datetime")

    def _query():
        import knowledge
        entities = knowledge._entities if hasattr(knowledge, "_entities") else {}
        new_entities = _collect_new_entities(entities, since_dt, limit)
        new_posts = []
        if _db._use_pg:
            with _db._conn() as conn:
                rows = _db._fetchall(conn, f"""
                    SELECT p.id, p.title, p.post_type, p.entity_id, p.created_at,
                           u.display_name
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE p.moderation_status = 'approved' AND p.deleted_at IS NULL
                    AND p.created_at >= {ph}
                    ORDER BY p.created_at DESC
                    LIMIT {ph}
                """, (since_dt.isoformat(), limit))
                new_posts = [_db._row_to_dict(r) for r in rows]
        return {
            "entities": new_entities,
            "posts": new_posts,
            "counts": {"entities": len(new_entities), "posts": len(new_posts)},
            "since": since,
        }
    result = await asyncio.to_thread(_query)
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return result


# ── Collections (U-28, public read-only) ──────────────────────────────


@router.get("/collections", response_model=CollectionsResponse,
            summary="List public collections",
            description="Returns published editorial collections sorted by display order. Each collection includes title, description, cover image, and entity IDs.")
async def list_public_collections(response: Response, limit: int = Query(20, ge=1, le=100)):
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, slug, title, description, cover_image, entity_ids, sort_order
                FROM collections
                WHERE is_published = TRUE
                ORDER BY sort_order, created_at DESC
                LIMIT {ph}
            """, (limit,))
        return {"collections": [db._row_to_dict(r) for r in rows]}
    return await asyncio.to_thread(_query)


@router.get("/collections/{slug}",
            summary="Get collection by slug",
            description="Returns a single published collection by its URL slug with entity IDs resolved to full entity summaries.")
async def get_collection_by_slug(slug: str, response: Response):
    require_pg()
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    validate_path_id(slug, "slug")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT * FROM collections WHERE slug = {ph} AND is_published = TRUE
            """, (slug,))
        if not row:
            return None
        col = db._row_to_dict(row)
        entity_ids = col.get("entity_ids") or []
        if isinstance(entity_ids, str):
            entity_ids = json.loads(entity_ids)
        entities = db.get_entities_batch(entity_ids) if entity_ids else []
        col["entities"] = entities
        return col
    result = await asyncio.to_thread(_query)
    if not result:
        return _err(404, "not_found")
    return result


# ── Public Announcements ─────────────────────────────────────────────────

@router.get("/announcements",
            summary="List active announcements",
            description="Returns currently active announcements sorted by priority. Only shows announcements within their active date range. Requires Postgres.")
async def list_active_announcements(response: Response, limit: int = Query(10, ge=1, le=50)):
    """Active announcements for display to users."""
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    require_pg()
    ph = db._ph

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, title, content, type, priority, starts_at, expires_at, created_at
                FROM announcements
                WHERE is_active = TRUE
                  AND starts_at <= NOW()
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY priority DESC, created_at DESC
                LIMIT {ph}
            """, (limit,))
        return [db._row_to_dict(r) for r in rows]

    items = await asyncio.to_thread(_query)
    return {"announcements": items, "total": len(items)}


# ── Entity Map Search (bounding box) ────────────────────────────────────

def _coords_in_bbox(lat, lng, north, south, east, west) -> bool:
    if not (south <= lat <= north):
        return False
    if west <= east:
        return west <= lng <= east
    return lng >= west or lng <= east


def _map_search_shape(e: dict, coords: list) -> dict:
    return {
        "id": e.get("id"),
        "name": e.get("name"),
        "type": e.get("type"),
        "coordinates": coords,
        "place": e.get("place"),
        "summary": (e.get("summary") or "")[:150],
        "images": (e.get("images") or [])[:1],
    }


@router.get("/entities/map", response_model=EntityMapResponse,
            summary="Search entities by bounding box",
            description="Returns entities within a geographic bounding box for map display. Supports entity type filter. Returns coordinates, summary, and first image.")
async def entities_map_search(
    response: Response,
    north: float = Query(..., ge=-90, le=90),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    west: float = Query(..., ge=-180, le=180),
    entity_type: str = Query(None, max_length=50),
    limit: int = Query(100, ge=1, le=500),
):
    """Entities within a bounding box for map display."""
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    if north <= south:
        raise HTTPException(400, "Giá trị north phải lớn hơn south")
    def _query():
        entities = db.list_entities(limit=5000, public_only=True)
        results = []
        for e in entities:
            coords = e.get("coordinates")
            if not coords or not isinstance(coords, list) or len(coords) < 2:
                continue
            if not _coords_in_bbox(coords[0], coords[1], north, south, east, west):
                continue
            if entity_type and e.get("type") != entity_type:
                continue
            results.append(_map_search_shape(e, coords))
            if len(results) >= limit:
                break
        return results
    results = await asyncio.to_thread(_query)
    return {"entities": results, "total": len(results), "bbox": {"north": north, "south": south, "east": east, "west": west}}


# ── Entity Trending (hot entities recently) ──────────────────────────────

@router.get("/entities/trending", response_model=TrendingResponse,
            summary="Get trending entities",
            description="Returns entities with the most activity (posts, reviews, bookmarks) in a recent time period. Filterable by entity type. Requires Postgres.")
async def entities_trending(
    days: int = Query(7, ge=1, le=90),
    entity_type: str = Query(None, max_length=50),
    limit: int = Query(10, ge=1, le=50),
    response: Response = None,
):
    """Entities with most activity (posts+reviews+bookmarks) in recent days."""
    require_pg()
    ph = db._ph
    if response:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT entity_id,
                       COUNT(*) as activity_count,
                       COUNT(*) FILTER (WHERE post_type = 'review') as review_count,
                       COALESCE(AVG(rating) FILTER (WHERE rating IS NOT NULL), 0) as avg_rating
                FROM posts
                WHERE entity_id IS NOT NULL
                  AND moderation_status = 'approved' AND deleted_at IS NULL
                  AND created_at >= NOW() - INTERVAL '1 day' * {ph}
                GROUP BY entity_id
                ORDER BY activity_count DESC, review_count DESC
                LIMIT {ph}
            """, (days, limit * 3))
        candidates = [db._row_to_dict(r) for r in rows]
        batch = db.get_entities_batch([c["entity_id"] for c in candidates])
        results = []
        for c in candidates:
            e = batch.get(c["entity_id"])
            if not e:
                continue
            if entity_type and e.get("type") != entity_type:
                continue
            results.append({
                "entity_id": c["entity_id"],
                "name": e.get("name"),
                "type": e.get("type"),
                "place": e.get("place"),
                "coordinates": e.get("coordinates"),
                "images": (e.get("images") or [])[:1],
                "activity_count": c["activity_count"],
                "review_count": c["review_count"],
                "avg_rating": round(float(c["avg_rating"]), 1),
            })
            if len(results) >= limit:
                break
        return {"entities": results, "total": len(results), "period_days": days}

    return await asyncio.to_thread(_query)


# ── User Engagement Stats ────────────────────────────────────────────────

@router.get("/users/{user_id}/engagement",
            summary="Get user engagement stats",
            description="Returns engagement metrics for a user profile: total posts, reviews, questions, average rating, follower count, and likes received. Requires Postgres.")
async def user_engagement_stats(user_id: str, response: Response):
    """Lightweight engagement stats for a user profile card."""
    validate_path_id(user_id, "user_id")
    require_pg()
    ph = db._ph

    def _query():
        with db._conn() as conn:
            user_check = db._fetchone(conn, f"SELECT id FROM users WHERE id::text = {ph} AND is_active = TRUE", (user_id,))
            if not user_check:
                raise HTTPException(404, "Người dùng không tồn tại")
            stats = db._fetchone(conn, f"""
                SELECT
                    COUNT(*) FILTER (WHERE moderation_status = 'approved') as total_posts,
                    COUNT(*) FILTER (WHERE post_type = 'review' AND moderation_status = 'approved') as total_reviews,
                    COALESCE(AVG(rating) FILTER (WHERE post_type = 'review' AND rating IS NOT NULL), 0) as avg_rating,
                    COUNT(*) FILTER (WHERE post_type = 'question') as total_questions,
                    COUNT(DISTINCT entity_id) FILTER (WHERE entity_id IS NOT NULL AND moderation_status = 'approved') as entities_reviewed
                FROM posts WHERE user_id::text = {ph} AND deleted_at IS NULL
            """, (user_id,))
            stats_d = db._row_to_dict(stats) if stats else {}
            followers = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM follows
                WHERE target_type = 'user' AND target_id = {ph}
            """, (user_id,))
            likes = db._fetchone(conn, f"""
                SELECT COALESCE(SUM(like_count), 0) as total_likes
                FROM posts WHERE user_id::text = {ph} AND moderation_status = 'approved' AND deleted_at IS NULL
            """, (user_id,))
        return {
            "user_id": user_id,
            "total_posts": stats_d.get("total_posts", 0),
            "total_reviews": stats_d.get("total_reviews", 0),
            "avg_rating": round(float(stats_d.get("avg_rating", 0)), 1),
            "total_questions": stats_d.get("total_questions", 0),
            "entities_reviewed": stats_d.get("entities_reviewed", 0),
            "followers": db._row_to_dict(followers)["c"] if followers else 0,
            "total_likes_received": db._row_to_dict(likes)["total_likes"] if likes else 0,
        }

    result = await asyncio.to_thread(_query)
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return result


# ── Entity comparison ─────────────────────────────────────────────────

@router.get("/entities/compare", response_model=CompareResponse,
            summary="Compare entities side by side",
            description="Returns side-by-side comparison data for 2-5 entities. Includes practical attributes (hours, phone, address) and quality scores.")
async def compare_entities(
    request: Request,
    response: Response,
    ids: str = Query(..., min_length=1, max_length=500),
):
    """Side-by-side entity comparison. Pass comma-separated IDs (max 5)."""
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    from ratelimit import check_rate
    check_rate(f"compare:{get_client_ip(request)}", 20, 60,
               "Quá nhiều yêu cầu. Vui lòng thử lại sau.")
    id_list = [validate_path_id(i.strip(), "entity_id") for i in ids.split(",") if i.strip()][:5]
    if len(id_list) < 2:
        raise HTTPException(400, "Cần ít nhất 2 entity để so sánh")

    def _query():
        batch = db.get_entities_batch(id_list)
        results = []
        for eid in id_list:
            e = batch.get(eid)
            if not e:
                continue
            attrs = e.get("attributes", {})
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except (json.JSONDecodeError, ValueError):
                    attrs = {}
            results.append({
                "id": e["id"], "name": e.get("name", ""),
                "type": e.get("type", ""),
                "place": e.get("place", ""),
                "summary": (e.get("summary") or "")[:300],
                "images": e.get("images", [])[:3],
                "coordinates": e.get("coordinates"),
                "attributes": {
                    "hours": attrs.get("hours"),
                    "phone": attrs.get("phone"),
                    "address": attrs.get("address"),
                    "admission_fee": attrs.get("admission_fee"),
                    "parking": attrs.get("parking"),
                },
                "quality_score": entity_quality(e),
            })
        return results

    entities = await asyncio.to_thread(_query)
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return {"entities": entities, "count": len(entities)}


# ── Popular entities by type ─────────────────────────────────────────

def _filter_popular_entities(all_entities: list[dict], entity_type: str | None, area: str | None) -> list[dict]:
    if entity_type:
        all_entities = [e for e in all_entities if e.get("type") == entity_type]
    if area:
        all_entities = [e for e in all_entities
                       if area.lower() in (e.get("place", "") or "").lower()
                       or area.lower() in (e.get("area", "") or "").lower()]
    return all_entities


def _score_popular_entity(e: dict) -> float:
    rc = e.get("rating_count", 0) or 0
    avg = e.get("rating_avg", 0) or 0
    has_img = 1 if e.get("images") else 0
    eq = entity_quality(e)
    eq_score = eq.get("score", 0) if isinstance(eq, dict) else eq
    return rc * 2 + avg * 3 + has_img * 5 + eq_score * 0.1


def _shape_popular_entity(e: dict) -> dict:
    return {
        "id": e["id"], "name": e.get("name", ""),
        "type": e.get("type", ""),
        "place": e.get("place", ""),
        "summary": (e.get("summary") or "")[:200],
        "images": e.get("images", [])[:2],
        "rating_count": e.get("rating_count", 0) or 0,
        "rating_avg": round(float(e.get("rating_avg", 0) or 0), 1),
        "quality_score": entity_quality(e),
    }


@router.get("/entities/popular", response_model=PopularResponse,
            summary="Get popular entities",
            description="Returns entities ranked by a composite popularity score based on review count, rating, images, and quality. Filterable by type and area.")
async def popular_entities(
    request: Request,
    response: Response,
    entity_type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=100),
    limit: int = Query(10, ge=1, le=50),
):
    """Popular entities by review count + rating. Filter by type and area."""
    from ratelimit import check_rate
    check_rate(f"popular:{get_client_ip(request)}", 20, 60,
               "Quá nhiều yêu cầu. Vui lòng thử lại sau.")

    def _query():
        all_entities = db.list_entities(limit=5000, public_only=True)
        all_entities = _filter_popular_entities(all_entities, entity_type, area)
        scored = [(_score_popular_entity(e), e) for e in all_entities]
        scored.sort(key=lambda x: -x[0])
        return [_shape_popular_entity(e) for _, e in scored[:limit]]

    results = await asyncio.to_thread(_query)
    response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=300"
    return {"entities": results, "entity_type": entity_type, "area": area}


# ── Dedicated entity search with advanced filters ─────────────────────

@router.get("/entities/search",
            summary="Advanced entity search",
            description="Entity search with advanced filters: type, area, image presence, and sort order. Returns paginated results with enriched place data.")
async def entity_search(
    request: Request,
    response: Response,
    q: str = Query("", max_length=200),
    entity_type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=100),
    has_image: Optional[bool] = Query(None),
    sort: str = Query("relevance", max_length=20),
    page: int = Query(1, ge=1, le=200),
    limit: int = Query(20, ge=1, le=50),
):
    """Entity search with type, area, image, and sort filters."""
    from ratelimit import check_rate
    check_rate(f"esearch:{get_client_ip(request)}", 30, 60,
               "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
    offset = (page - 1) * limit
    all_entities = await asyncio.to_thread(
        db.search_entities, q=q or None, entity_type=entity_type, area=area,
        limit=500, public_only=True
    )
    if has_image is True:
        all_entities = [e for e in all_entities if e.get("images")]
    elif has_image is False:
        all_entities = [e for e in all_entities if not e.get("images")]
    if sort == "name":
        all_entities.sort(key=lambda e: e.get("name", "").lower())
    elif sort == "newest":
        all_entities.sort(key=lambda e: str(e.get("updatedAt", "")), reverse=True)
    total = len(all_entities)
    page_items = all_entities[offset:offset + limit]
    _enrich_place(page_items)
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    return {
        "entities": page_items, "total": total,
        "page": page, "has_more": offset + limit < total,
        "filters": {
            "entity_type": entity_type, "area": area,
            "has_image": has_image, "sort": sort,
        },
    }


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

_fix_route_order()
