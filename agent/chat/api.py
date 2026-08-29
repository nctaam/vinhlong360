# -*- coding: utf-8 -*-
"""Chat + chat-stream — bóc khỏi `server.py` (2026-08-27).

VÌ SAO BÓC: `server.py` 5.507 dòng / 71 route, nhưng riêng ba hàm chat chiếm
1.959 dòng — 40% toàn bộ thân hàm. Nó không phải điểm-vào-ứng-dụng, nó là tính
năng chat mặc áo điểm-vào: ai sửa route bất kỳ cũng phải mở file mà chat chiếm
gần một nửa. Đo trên 1.923 commit 6 tháng, `server.py` bị chạm ở 7,4% số commit.

RANH GIỚI ĐƯỢC TÍNH, KHÔNG ĐOÁN: lấy bao đóng bắc cầu từ 5 hạt giống (`chat`,
`chat_stream`, `_run_agent`, `ChatRequest`, `ChatResponse`) — thêm dần mọi ký
hiệu mà MỌI nơi gọi đều đã nằm trong tập. Ra 58 ký hiệu, và kiểm chéo cho thấy
KHÔNG ký hiệu nào trong tập bị mã ngoài tham chiếu. Cộng 15 hằng/biến trạng thái
chỉ chat dùng.

Theo khuôn `agent/cases/` — gói theo MIỀN, phát `APIRouter` riêng, `server.py`
chỉ `include_router`. Đo được trên cases: 73% commit của nó ở lại trong gói.
"""
from __future__ import annotations

import hashlib
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from dataclasses import dataclass
from functools import partial, wraps
from typing import Literal

import anyio
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from agentic_rag import build_rag_context
from feedback_policy import (
    FeedbackRejected,
    FeedbackUnavailable,
    consume_feedback_receipt,
    issue_feedback_receipt,
)
from index_policy import is_publicly_eligible
from privacy_boundary import SafeText, prepare_chat_output, redact_text
from proactive import generate_welcome_message, get_proactive_context

import asyncio
import json
import re
import threading
import time
import traceback

from fastapi import APIRouter, Request, Response

import analytics
import cache
import knowledge
from owner_write_gate import owner_write_gate
from chat_identity import resolve_chat_owner, set_chat_owner_cookie
from chat_usage import UsageAccumulator
from llm_config import get_client, get_model, get_model_mini
from memory import UnknownConversation, memory_manager
from middleware import (
    chat_limiter,
    error_tracker,
    feedback_ip_limiter,
    feedback_owner_limiter,
    get_client_ip,
    logger,
    stream_limiter,
)
from privacy_boundary import (
    PrivacyBoundaryBlocked,
    PrivacyBoundaryUnavailable,
    StreamingPIIRedactor,
    prepare_chat_input,
    redact_payload,
)
from reflexion import quality_tracker, reflexion_engine
from tools import SYSTEM_PROMPT, TOOLS

from features import _env_bool  # noqa: F401
from http_errors import _error_response
from itineraries.itinerary_gen import generate_itinerary
from ocop import is_ocop_certified, ocop_display_label, ocop_tier

from features import (
    HAS_AB_TESTING,
    HAS_AUTOCORRECT,
    HAS_CIRCUIT_BREAKER,
    HAS_CONTEXTUAL,
    HAS_COST_TRACKER,
    HAS_DYNAMIC_AGENTS,
    HAS_EXPERIENCE,
    HAS_FEWSHOT,
    HAS_GUARDRAILS,
    HAS_KB_CONTEXT,
    HAS_LLM_JUDGE,
    HAS_MEMORY_GRAPH,
    HAS_METRICS,
    HAS_OPTIMIZER,
    HAS_ORCHESTRATOR,
    HAS_PARALLEL,
    HAS_PROMPT_CACHE,
    HAS_REALTIME,
    HAS_SEMANTIC_CACHE,
    HAS_TRACING,
    Orchestrator,
    ParallelToolExecutor,
    ab_manager,
    agent_factory,
    autocorrect,
    check_dynamic_route,
    cost_attribution,
    enhanced_hybrid_search,
    experience_memory,
    get_realtime_context,
    get_upcoming_events,
    get_weather,
    guardrail_budget,
    judge,
    kb_context,
    memory_graph,
    parameter_tuner,
    prompt_cache,
    prompt_compiler,
    prompt_optimizer,
    record_outcome,
    safe_llm_call,
    semantic_abandon,
    semantic_get_async,
    semantic_put,
    semantic_take_dedup_lease,
    token_counter,
    tool_weight_optimizer,
    trace_chat_request,
    track_cache,
    track_chat_request,
    track_error,
    track_feedback_attempt,
    weather_breaker,
    weather_for_llm,
    web_search_breaker,
)

router = APIRouter()


LLM_JUDGE_ENABLED = _env_bool("LLM_JUDGE_ENABLED", False)


_semantic_route_lease: ContextVar[tuple[str, str, str] | None] = ContextVar(
    "semantic_route_lease",
    default=None,
)


def _finalize_semantic_route_lease(func):
    """Abandon a captured semantic lease whenever a route task exits."""
    @wraps(func)
    async def wrapped(*args, **kwargs):
        token = _semantic_route_lease.set(None)
        try:
            return await func(*args, **kwargs)
        finally:
            lease = _semantic_route_lease.get()
            _semantic_route_lease.reset(token)
            if lease is not None and HAS_SEMANTIC_CACHE:
                query, owner_key, dedup_key = lease
                try:
                    semantic_abandon(
                        query,
                        owner_key=owner_key,
                        dedup_key=dedup_key,
                    )
                except Exception:
                    logger.debug("Semantic cache abandon failed", exc_info=True)

    return wrapped


def _hold_semantic_route_lease(
    query: str,
    owner_key: str,
    dedup_key: str | None,
) -> None:
    if dedup_key is not None:
        _semantic_route_lease.set((query, owner_key, dedup_key))


def _transfer_semantic_route_lease() -> None:
    _semantic_route_lease.set(None)


class _SemanticLeaseStreamingResponse(StreamingResponse):
    """Finalize an explicitly captured lease across the full ASGI response."""

    def __init__(self, *args, semantic_lease=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._semantic_lease = semantic_lease

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            lease = self._semantic_lease
            self._semantic_lease = None
            if lease is not None and HAS_SEMANTIC_CACHE:
                query, owner_key, dedup_key = lease
                try:
                    semantic_abandon(
                        query,
                        owner_key=owner_key,
                        dedup_key=dedup_key,
                    )
                except Exception:
                    logger.debug(
                        "Semantic cache abandon failed (stream)",
                        exc_info=True,
                    )


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo web search with circuit breaker protection (P0-7).

    After 3 consecutive failures the web_search_breaker opens for 60s,
    returning [] immediately instead of hammering a broken service.
    """
    def _do_search():
        from ddgs import DDGS
        with DDGS(timeout=10) as ddgs:  # EH-04: timeout to avoid blocking
            results = list(ddgs.text(query, region="vn-vi", max_results=max_results))
        return [{"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")} for r in results]

    try:
        if HAS_CIRCUIT_BREAKER:
            return web_search_breaker.call(_do_search)
        return _do_search()
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return []


def _tool_description(name: str, args: dict) -> str:
    """Human-readable description of a tool call for UI tracing."""
    descs = {
        "search": lambda a: f"Tìm kiếm '{a.get('q', '')}'..." if a.get('q') else "Tìm kiếm knowledge base...",
        "entity_detail": lambda a: f"Tra cứu chi tiết '{a.get('entity_id', '')}'...",
        "seasonal_now": lambda a: f"Kiểm tra mùa vụ tháng {a.get('month', '')}...",
        "list_itineraries": lambda a: f"Tìm lịch trình{' ' + a['area'] if a.get('area') else ''}...",
        "itinerary_detail": lambda a: f"Xem lịch trình '{a.get('itinerary_id', '')}'...",
        "places_in_area": lambda a: f"Liệt kê địa điểm tại {a.get('area', '')}...",
        "stats": lambda a: "Thống kê knowledge base...",
        "compare_areas": lambda a: f"So sánh {a.get('area_1', '')} và {a.get('area_2', '')}...",
        "nearby_entities": lambda a: f"Tìm điểm gần '{a.get('entity_id', '')}'...",
        "web_search": lambda a: f"Tìm trên web '{a.get('query', '')}'...",
        "suggest_followups": lambda a: "Gợi ý câu hỏi tiếp theo...",
        "generate_itinerary": lambda a: f"Tạo lịch trình {a.get('days', 1)} ngày...",
        "weather": lambda a: f"Tra thời tiết {a.get('area', 'Vĩnh Long')}...",
        "community_reviews": lambda a: f"Xem đánh giá cộng đồng về '{a.get('entity_id', '')}'...",
        "trending_posts": lambda a: "Xem bài viết nổi bật trên cộng đồng...",
    }
    fn = descs.get(name)
    if fn:
        try:
            return fn(args)
        except Exception:
            logger.debug("Tool description failed for %s", name, exc_info=True)
    return f"Đang xử lý {name}..."


def generate_followups(context: str, usage_accumulator=None) -> list[str]:
    try:
        model = get_model_mini()
        messages = [{"role": "user", "content": f"""Dựa vào ngữ cảnh sau, gợi ý 3 câu hỏi tiếp theo ngắn gọn (< 40 ký tự) mà du khách có thể muốn hỏi.

Ngữ cảnh: {context}

Trả về JSON array gồm 3 string. Chỉ trả JSON, không text khác."""}]
        response = get_client().chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            timeout=LLM_TIMEOUT,
        )
        if usage_accumulator is not None:
            usage_accumulator.add_response(
                response,
                model=model,
                messages=messages,
            )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return json.loads(content)[:3]
    except Exception:
        logger.debug("Follow-up generation failed", exc_info=True)
        return []


def _rerank_resolve_entities(reranked: list, allowed_ids: set, has_filters: bool) -> list:
    """Resolve reranked hits → full entities, honoring active structured filters."""
    out = []
    for r in reranked:
        eid = r.get("id", r.get("entity_id", ""))
        ent = knowledge.get_entity(eid) if eid else None
        if not ent:
            continue
        # With filters active, only keep entities that passed the filter.
        if has_filters and eid not in allowed_ids:
            continue
        out.append(ent)
    return out


def _backfill_from_keyword(out: list, keyword_results: list, limit: int) -> None:
    """Append keyword_results (in place) until `out` reaches limit."""
    seen = {e["id"] for e in out}
    for e in keyword_results:
        if e["id"] not in seen:
            out.append(e)
            if len(out) >= limit:
                break


def _hybrid_rerank_search(args: dict) -> list[dict]:
    """Run the KB search with hybrid reranking (BM25 + semantic + contextual).

    Falls back to plain knowledge.search_entities() when the query is empty,
    contextual retrieval is unavailable, or indexes aren't built. Structured
    filters (type/area/month/ocop) are always respected: hybrid reranking only
    reorders the filtered candidate set, never introduces entities outside it.
    """
    q = args.get("q")
    entity_type = args.get("entity_type")
    area = args.get("area")
    month = args.get("month")
    ocop_only = args.get("ocop_only", False)
    limit = args.get("limit", 10)

    has_filters = bool(entity_type or area or month or ocop_only)

    # Authoritative filtered candidate pool (ranked by smart_rank).
    keyword_results = knowledge.search_entities(
        q=q, entity_type=entity_type, area=area, month=month,
        ocop_only=ocop_only, limit=max(limit * 3, 30),
    )

    # Plain path: no text query, no hybrid infra, or empty pool.
    if not q or not HAS_CONTEXTUAL or not keyword_results:
        return keyword_results[:limit]

    try:
        allowed_ids = {e["id"] for e in keyword_results}
        reranked = enhanced_hybrid_search(
            query=q,
            keyword_results=keyword_results,
            entities=knowledge._entities,
            relationships=getattr(knowledge, "_relationships", []) or [],
            top_k=max(limit * 3, 30),
        )
        out = _rerank_resolve_entities(reranked, allowed_ids, has_filters)
        # Backfill from keyword_results if hybrid dropped too many.
        if len(out) < limit:
            _backfill_from_keyword(out, keyword_results, limit)
        return out[:limit]
    except Exception as e:
        logger.error(f"Hybrid search failed, using keyword fallback: {e}")
        return keyword_results[:limit]


def call_tool(name: str, args: dict, usage_accumulator=None) -> str:
    # P1: cô lập lỗi tool (KeyError do LLM thiếu tham số, lỗi tool…) → trả lỗi có cấu trúc
    # thay vì propagate (trước đây args["x"] thiếu field → 500 ở serial path).
    try:
        return _call_tool_impl(name, args or {}, usage_accumulator)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"call_tool '{name}' lỗi: {e}")
        return json.dumps({"error": "Không thực hiện được công cụ (thiếu hoặc sai tham số)."}, ensure_ascii=False)


_PROV_NAMES = {"ben-tre": "Bến Tre", "tra-vinh": "Trà Vinh", "vinh-long": "Vĩnh Long"}


_OCOP_CRAFT_KW = ["đan", "dệt", "gốm", "tre", "lá", "chiếu", "mây", "thủ công"]


_OCOP_DRINK_KW = ["rượu", "nước", "mật", "trà", "cà phê", "đường hoa"]


_ACCOM_TYPE_KW = {
    "homestay": ["homestay", "nhà vườn", "nhà cổ", "nhà dân"],
    "resort": ["resort", "khu nghỉ dưỡng"],
    "hotel": ["khách sạn", "hotel"],
    "guesthouse": ["nhà nghỉ", "guesthouse", "phòng trọ"],
}


_ACCOM_FAMILY_KW = ["gia đình", "trẻ em", "vườn", "sân chơi", "an toàn", "cù lao"]


def _area_matches(e: dict, attrs: dict, area) -> bool:
    if not area:
        return True
    place = knowledge.get_place(e["id"])
    prov = attrs.get("province_old", "")
    prov_name = _PROV_NAMES.get(area)
    return bool((place and place.get("area") == area) or (prov_name is not None and prov == prov_name))


def _search_card_practical(card: dict, attrs: dict, e: dict) -> None:
    hours = attrs.get("hours") or attrs.get("open_hours")
    if hours:
        card["hours"] = hours
    if attrs.get("admission_fee") or attrs.get("admission"):
        card["admission_fee"] = attrs.get("admission_fee") or attrs.get("admission")
    if attrs.get("best_time"):
        card["best_time"] = attrs["best_time"]
    if attrs.get("key_facts"):
        card["key_facts"] = attrs["key_facts"]
    _ocop = ocop_display_label(e)
    if _ocop:
        card["ocop"] = _ocop
    if attrs.get("address"):
        card["address"] = attrs["address"]
    elif attrs.get("district"):
        card["location"] = f"{attrs.get('ward', attrs['district'])}, {attrs.get('province_old', '')}"


def _ocop_category_ok(e: dict, category: str) -> bool:
    if category == "all":
        return True
    name_text = (e.get("name", "") + e.get("summary", "")).lower()
    if category == "craft":
        return any(kw in name_text for kw in _OCOP_CRAFT_KW)
    if category == "drink":
        return any(kw in name_text for kw in _OCOP_DRINK_KW)
    if category == "food":
        return not any(kw in name_text for kw in _OCOP_CRAFT_KW + _OCOP_DRINK_KW)
    return True


def _accom_filters_ok(e: dict, attrs: dict, acc_type: str, family: bool) -> bool:
    if acc_type != "all":
        kws = _ACCOM_TYPE_KW.get(acc_type, [])
        text = (e.get("name", "") + e.get("summary", "")).lower()
        if not any(kw in text for kw in kws):
            return False
    if family:
        text = (e.get("name", "") + e.get("summary", "") + (attrs.get("booking_note") or "")).lower()
        if not any(kw in text for kw in _ACCOM_FAMILY_KW):
            return False
    return True


def _ocop_card(e: dict, attrs: dict, star_num: int) -> dict:
    card = {
        "id": e["id"], "name": e["name"],
        "ocop": ocop_display_label(e),
        "summary": e.get("summary", "")[:120],
        "province": attrs.get("province_old", ""),
        "address": attrs.get("address", ""),
    }
    if attrs.get("admission_fee") or attrs.get("admission"): card["price"] = attrs.get("admission_fee") or attrs.get("admission")
    if attrs.get("phone"):         card["phone"] = attrs["phone"]
    if e.get("coords"):            card["coords"] = e["coords"]
    # Sort key: star desc
    card["_star"] = star_num
    return card


def _accom_card(e: dict, attrs: dict) -> dict:
    card = {
        "id": e["id"], "name": e["name"],
        "summary": e.get("summary", "")[:120],
        "province": attrs.get("province_old", ""),
        "address": attrs.get("address", ""),
    }
    if attrs.get("admission_fee") or attrs.get("admission") or attrs.get("price_range"):
        card["price"] = attrs.get("admission_fee") or attrs.get("admission") or attrs.get("price_range")
    if attrs.get("phone"):         card["phone"] = attrs["phone"]
    hours = attrs.get("hours") or attrs.get("open_hours")
    if hours:                      card["check_in"] = hours
    if attrs.get("booking_note"):  card["booking_note"] = attrs["booking_note"]
    if e.get("coords"):            card["coords"] = e["coords"]
    return card


def _search_result_card(e: dict) -> dict:
    attrs = e.get("attributes") or {}
    place_obj = knowledge.get_place(e["id"]) or {}
    # Location label: prefer places data, fallback to attributes
    place_label = place_obj.get("name") or attrs.get("ward") or attrs.get("district") or attrs.get("province_old") or ""
    card = {
        "id": e["id"], "type": e["type"], "name": e["name"],
        "summary": e.get("summary", ""),
        "place": place_label,
        "season": knowledge.season_text(e),
        "needs_verification": e.get("confidence", 1.0) < 0.7,
        # §1.7: KHÔNG gửi trường tên "verified" vào ngữ cảnh LLM. `entity.verified`
        # chỉ là cờ PUBLISH, không phải kiểm-chứng-thực-địa (nguồn duy nhất cho việc
        # đó là attributes.verifiedAt, hiện ~0 entity có). Một trường tên "verified:
        # true" phủ 1739/1746 entity là lời mời mô hình khẳng định "đã xác minh" —
        # đúng thứ §1.7 cấm. Tín hiệu độ-tin-cậy hợp lệ đã nằm ở `needs_verification`,
        # và nó CÓ hợp đồng trong tools.py:418,445 dạy mô hình dùng đúng cách.
    }
    # Include coords when available (powers map display)
    coords = e.get("coords") or e.get("coordinates")
    if coords:
        card["coords"] = coords
    _search_card_practical(card, attrs, e)
    return card


def _tool_search(args: dict) -> str:
    result = _hybrid_rerank_search(args)
    try:
        for e in result[:3]:
            analytics.track_entity_hit(e["id"])
    except Exception:
        logger.warning("analytics.track_entity_hit failed (search)", exc_info=True)
    return json.dumps([_search_result_card(e) for e in result], ensure_ascii=False)


def _tool_entity_detail(args: dict) -> str:
    detail = knowledge.entity_detail(args["entity_id"])
    try:
        analytics.track_entity_hit(args["entity_id"])
    except Exception:
        logger.warning("analytics.track_entity_hit failed (entity_detail)", exc_info=True)
    if not detail:
        return json.dumps({"error": "Không tìm thấy: " + args["entity_id"]})
    conf = detail.pop("confidence", 1.0)
    detail["needs_verification"] = (conf or 1.0) < 0.7
    # §1.7 — cửa thứ HAI của cùng một lỗ. d2a1a99a gỡ trường này khỏi
    # `_search_result_card` nhưng `knowledge.entity_detail()` trả `{**e, ...}`
    # nên nó giữ nguyên cột của entity, và tool này bơm thẳng vào ngữ cảnh LLM.
    # Trường đó phủ 1746/1746 entity và chỉ là cờ PUBLISH, không phải bằng chứng
    # kiểm chứng thực địa — để nó lọt vào là mời mô hình phát biểu "đã xác minh".
    # Nguồn thật duy nhất là attributes.verifiedAt, hiện gần như rỗng.
    # `needs_verification` (suy từ confidence) mới là thứ prompt được phép đọc.
    detail.pop("verified", None)
    return json.dumps(detail, ensure_ascii=False, default=str)


def _tool_seasonal_now(args: dict) -> str:
    raw_month = args["month"]
    try:
        raw_month = max(1, min(12, int(raw_month)))
    except (TypeError, ValueError):
        raw_month = datetime.now(timezone.utc).month
    result = knowledge.seasonal_now(raw_month)
    def _seasonal_card(e):
        attrs = e.get("attributes") or {}
        card = {
            "id": e["id"], "type": e["type"], "name": e["name"],
            "summary": e.get("summary", ""),
            "season": knowledge.season_text(e),
        }
        hours = attrs.get("hours") or attrs.get("open_hours")
        if hours:                      card["hours"] = hours
        if attrs.get("admission_fee") or attrs.get("admission"): card["admission_fee"] = attrs.get("admission_fee") or attrs.get("admission")
        if attrs.get("best_time"):     card["best_time"] = attrs["best_time"]
        _ocop = ocop_display_label(e)
        if _ocop:                      card["ocop"] = _ocop
        if e.get("coords"):            card["coords"] = e["coords"]
        return card
    return json.dumps([_seasonal_card(e) for e in result], ensure_ascii=False)


def _tool_list_itineraries(args: dict) -> str:
    result = knowledge.list_itineraries(args.get("area"))
    return json.dumps([{
        "id": it["id"], "title": it["title"],
        "area": it.get("area"), "duration": it.get("duration"),
        "summary": it.get("summary", ""),
        "stops": len(it.get("stops", [])),
    } for it in result], ensure_ascii=False)


def _tool_itinerary_detail(args: dict) -> str:
    it = knowledge.get_itinerary(args["itinerary_id"])
    if not it:
        return json.dumps({"error": "Không tìm thấy: " + args["itinerary_id"]})
    stops_detail = []
    for s in it.get("stops", []):
        e = knowledge.get_entity(s["id"])
        stops_detail.append({
            "time": s["time"], "id": s["id"],
            "name": e["name"] if e else s["id"],
            "summary": e.get("summary", "") if e else "",
            "note": s.get("note", ""),
        })
    return json.dumps({**it, "stops": stops_detail}, ensure_ascii=False)


def _tool_places_in_area(args: dict) -> str:
    ps = knowledge.places(args["area"])
    content_counts = {}
    for e in knowledge._entities.values():
        pid = e.get("placeId")
        if pid and e["type"] in knowledge.CARD_TYPES:
            content_counts[pid] = content_counts.get(pid, 0) + 1
    return json.dumps([{
        "id": p["id"], "name": p["name"], "level": p.get("level"),
        "legacyArea": p.get("legacyArea", ""),
        "content_count": content_counts.get(p["id"], 0),
    } for p in ps], ensure_ascii=False)


def _tool_stats(args: dict) -> str:
    return json.dumps(knowledge.stats(), ensure_ascii=False)


def _tool_compare_areas(args: dict) -> str:
    result = knowledge.compare_areas(args["area_1"], args["area_2"])
    return json.dumps(result, ensure_ascii=False)


def _tool_nearby_entities(args: dict) -> str:
    result = knowledge.nearby_entities(args["entity_id"], args.get("limit", 8))
    # Enrich with practical info for each nearby entity
    enriched_nearby = []
    for item in result:
        e = knowledge._entities.get(item["id"]) or {}
        attrs = e.get("attributes") or {}
        card = dict(item)
        hours = attrs.get("hours") or attrs.get("open_hours")
        if hours:                      card["hours"] = hours
        if attrs.get("admission_fee") or attrs.get("admission"): card["admission_fee"] = attrs.get("admission_fee") or attrs.get("admission")
        _ocop = ocop_display_label(e)
        if _ocop:                      card["ocop"] = _ocop
        if e.get("coords"):            card["coords"] = e["coords"]
        enriched_nearby.append(card)
    return json.dumps(enriched_nearby, ensure_ascii=False)


def _tool_ocop_products(args: dict) -> str:
    area = args.get("area")
    min_stars = args.get("min_stars", 3)
    category = args.get("category", "all")
    limit = args.get("limit", 12)
    results = []
    for e in knowledge._entities.values():
        attrs = e.get("attributes") or {}
        # Loc bang `attributes.ocop` truthy bo sot 73 san pham chi mang
        # `ocop_star` (do 2026-08-27) — cung loi da va o trang /ocop.
        if not is_ocop_certified(e):
            continue
        if not _area_matches(e, attrs, area):
            continue
        # Star filter
        # Ban cu bat CHU SO DAU TIEN o bat ky dau: "VICOSAP: 4 SP OCOP 5 sao
        # quoc gia..." cho ra 4, va mot chuoi co nam ban hanh cho ra chu so cua
        # nam. `ocop_tier` neo dau chuoi va co bo loc §1.7.
        star_num = ocop_tier(e)
        if star_num and star_num < min_stars:
            continue
        if not _ocop_category_ok(e, category):
            continue
        results.append(_ocop_card(e, attrs, star_num))
    results.sort(key=lambda x: -x.pop("_star", 0))
    return json.dumps(results[:limit], ensure_ascii=False)


def _tool_accommodation_search(args: dict) -> str:
    area = args.get("area")
    acc_type = args.get("type", "all")
    family = args.get("family_friendly", False)
    limit = args.get("limit", 8)
    results = []
    for e in knowledge._entities.values():
        if e.get("type") != "accommodation":
            continue
        attrs = e.get("attributes") or {}
        if not _area_matches(e, attrs, area):
            continue
        if not _accom_filters_ok(e, attrs, acc_type, family):
            continue
        results.append(_accom_card(e, attrs))
    return json.dumps(results[:limit], ensure_ascii=False)


def _tool_web_search(args: dict) -> str:
    results = web_search(args["query"])
    if not results:
        return json.dumps({"results": [], "note": "Không tìm thấy kết quả"})
    return json.dumps({"results": results}, ensure_ascii=False)


def _tool_suggest_followups(args: dict, usage_accumulator=None) -> str:
    suggestions = generate_followups(args["context"], usage_accumulator)
    return json.dumps({"suggestions": suggestions}, ensure_ascii=False)


def _tool_generate_itinerary(args: dict) -> str:
    result = generate_itinerary(
        days=args.get("days", 1),
        interests=args.get("interests"),
        areas=args.get("areas"),
        month=args.get("month"),
        budget=args.get("budget", "trung_binh"),
    )
    return json.dumps(result, ensure_ascii=False)


def _tool_community_reviews(args: dict) -> str:
    try:
        from community.api import get_community_reviews
        entity_id = args.get("entity_id", "")
        limit = args.get("limit", 5)
        reviews = get_community_reviews(entity_id, limit)
        if not reviews:
            return json.dumps({"reviews": [], "note": f"Chưa có đánh giá cộng đồng cho '{entity_id}'"}, ensure_ascii=False)
        return json.dumps({"reviews": reviews, "count": len(reviews)}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning("community_reviews tool error", error=str(e))
        return json.dumps({"reviews": [], "error": "Không thể tải đánh giá"})


def _tool_trending_posts(args: dict) -> str:
    try:
        from community.api import get_trending_posts
        entity_type = args.get("entity_type")
        limit = args.get("limit", 10)
        posts = get_trending_posts(limit, entity_type)
        if not posts:
            return json.dumps({"posts": [], "note": "Chưa có bài viết nổi bật"}, ensure_ascii=False)
        return json.dumps({"posts": posts, "count": len(posts)}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning("trending_posts tool error", error=str(e))
        return json.dumps({"posts": [], "error": "Không thể tải bài viết"})


def _tool_weather(args: dict) -> str:
    if HAS_REALTIME:
        area = args.get("area", "vinh-long")
        # P0-7: wrap weather call with circuit breaker — after 3 failures,
        # skip weather for 120s and return fallback instead of hanging.
        def _do_weather():
            return get_weather(area)
        try:
            if HAS_CIRCUIT_BREAKER:
                weather_data = weather_breaker.call(_do_weather)
            else:
                weather_data = _do_weather()
        except Exception as _we:
            logger.warning(f"Weather API error (circuit breaker): {_we}")
            weather_data = None
        events = get_upcoming_events(days_ahead=14, area=area)
        # §1.7 — `weather_data` ở đây có thể là payload dự phòng theo mùa
        # (realtime._fallback_weather): nó có ĐỦ temp_c/humidity/description y như
        # nhánh đo thật, chỉ khác ở key `fallback`. Json.dumps thẳng dict đó là LLM
        # đọc "28°C, mưa rào" rồi phát biểu như số đo. weather_for_llm() lược sạch
        # số và thay bằng cảnh báo tiếng Việt (cùng nguyên tắc với frontend
        # web-nuxt/composables/useWeather.ts). Nó cũng nuốt luôn trường hợp
        # weather_data is None ở trên (circuit breaker mở / lỗi gọi).
        # Đường HTTP GET /weather KHÔNG đi qua đây nên frontend vẫn nhận `fallback: true`.
        return json.dumps({"weather": weather_for_llm(weather_data), "events": events}, ensure_ascii=False, default=str)
    return json.dumps({"error": "Weather API not available"})


def _tool_directory_lookup(args: dict) -> str:
    results = knowledge.directory_search(args.get("query", ""))
    if not results:
        return json.dumps(
            {"results": [], "note": "Chưa có dữ liệu danh bạ hành chính cho yêu cầu này (đang bổ sung từ nguồn chính thống)."},
            ensure_ascii=False)
    return json.dumps({"results": results}, ensure_ascii=False)


_TOOL_HANDLERS = {
    "search": _tool_search,
    "entity_detail": _tool_entity_detail,
    "seasonal_now": _tool_seasonal_now,
    "list_itineraries": _tool_list_itineraries,
    "itinerary_detail": _tool_itinerary_detail,
    "places_in_area": _tool_places_in_area,
    "stats": _tool_stats,
    "compare_areas": _tool_compare_areas,
    "nearby_entities": _tool_nearby_entities,
    "ocop_products": _tool_ocop_products,
    "accommodation_search": _tool_accommodation_search,
    "web_search": _tool_web_search,
    "suggest_followups": _tool_suggest_followups,
    "generate_itinerary": _tool_generate_itinerary,
    "community_reviews": _tool_community_reviews,
    "trending_posts": _tool_trending_posts,
    "weather": _tool_weather,
    "directory_lookup": _tool_directory_lookup,
}


def _call_tool_impl(name: str, args: dict, usage_accumulator=None) -> str:
    handler = _TOOL_HANDLERS.get(name)
    if handler is not None:
        if handler is _tool_suggest_followups:
            return handler(args, usage_accumulator)
        return handler(args)
    return json.dumps({"error": f"Unknown tool: {name}"})


def _sanitize_message(v: str) -> str:
    """Strip HTML/script tags from user chat messages."""
    v = re.sub(r"<script[^>]*>.*?</script>", "", v or "", flags=re.DOTALL | re.IGNORECASE)
    v = re.sub(r"<[^>]+>", "", v)
    v = v.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return v.strip()


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=50, description="Conversation history")
    session_id: str | None = Field(default=None, max_length=32)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v):
        return _sanitize_message(v)


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[str] = []
    suggestions: list[str] = []
    session_id: str = ""
    cached: bool = False
    feedback_receipt: str | None = None


_FEEDBACK_MODEL_VARIANTS = {
    "cx/gpt-5.4": "cx-gpt-5-4",
    "cx/gpt-5.4-mini": "cx-gpt-5-4-mini",
    "cx/gpt-5.5": "cx-gpt-5-5",
    "cx/gpt-5.5-mini": "cx-gpt-5-5-mini",
    "cx-gpt-5-4": "cx-gpt-5-4",
    "cx-gpt-5-4-mini": "cx-gpt-5-4-mini",
    "cx-gpt-5-5": "cx-gpt-5-5",
    "cx-gpt-5-5-mini": "cx-gpt-5-5-mini",
}


_FEEDBACK_SEARCH_TOOLS = frozenset({"search", "web_search", "accommodation_search"})


_FEEDBACK_WEATHER_TOOLS = frozenset({"weather"})


_FEEDBACK_KNOWLEDGE_TOOLS = frozenset({
    "abstain",
    "community_reviews",
    "compare_areas",
    "directory_lookup",
    "entity_detail",
    "generate_itinerary",
    "itinerary_detail",
    "list_itineraries",
    "nearby_entities",
    "ocop_products",
    "places_in_area",
    "seasonal_now",
    "stats",
    "suggest_followups",
    "trending_posts",
})


def _feedback_tool_bucket(tools) -> str:
    if not tools:
        return "none"
    names = {
        value.split("(", 1)[0].strip()
        for value in tools
        if isinstance(value, str) and value.strip()
    }
    if not names:
        return "mixed"
    buckets = set()
    for name in names:
        if name in _FEEDBACK_SEARCH_TOOLS:
            buckets.add("search")
        elif name in _FEEDBACK_WEATHER_TOOLS:
            buckets.add("weather")
        elif name in _FEEDBACK_KNOWLEDGE_TOOLS:
            buckets.add("knowledge")
        else:
            return "mixed"
    return next(iter(buckets)) if len(buckets) == 1 else "mixed"


def _issue_delivered_feedback_receipt(
    owner_key,
    safe_message,
    safe_reply,
    model_variant,
    tools,
) -> str | None:
    canonical_turn = json.dumps(
        {"message": safe_message, "reply": safe_reply},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assistant_turn_digest = hashlib.sha256(
        b"feedback-assistant-turn:v1\x00" + canonical_turn
    ).hexdigest()
    bounded_model = _FEEDBACK_MODEL_VARIANTS.get(model_variant, "other")
    bounded_tools = _feedback_tool_bucket(tools)
    try:
        receipt = issue_feedback_receipt(
            owner_key,
            assistant_turn_digest,
            bounded_model,
            bounded_tools,
        )
    except Exception:
        logger.warning("FEEDBACK_RECEIPT_DELIVERY_ISSUE_FAILED")
        return None
    return receipt.token if receipt is not None else None


_ANAPHOR_TYPES = {
    "bảo tàng":     ["bảo tàng"],
    "khách sạn":    ["khách sạn", "hotel", "resort", "homestay"],
    "nhà hàng":     ["nhà hàng", "quán ăn", "restaurant"],
    "chùa":         ["chùa", "tịnh xá", "thiền viện"],
    "đình":         ["đình"],
    "khu du lịch":  ["khu du lịch", "khu nghỉ dưỡng"],
    "cồn":          ["cồn", "đảo"],
    "lăng":         ["lăng", "khu tưởng niệm"],
    "làng nghề":    ["làng nghề"],
    "điểm":         ["điểm du lịch", "điểm tham quan"],
}


_CONTEXT_PRONOUNS = ("ở đó", "đến đó", "tại đó", "nơi đó", "chỗ đó")


def _extract_reply_entities(history: list[dict]) -> list:
    """Bold (**...**) + header (## ...) names từ reply assistant gần nhất."""
    last_reply = ""
    for turn in reversed(history[-6:]):
        if turn.get("role") == "assistant":
            last_reply = turn.get("content", "")
            break
    if not last_reply:
        return []
    bold_entities = re.findall(r'\*\*([^*\n]{2,60})\*\*', last_reply)
    headers = re.findall(r'(?:^|\n)#+\s*(.{5,60}?)(?:\n|$)', last_reply)
    return bold_entities + headers


def _resolve_anaphors(msg_lower: str, resolved: str, all_entities: list) -> str:
    for anaphor, keywords in _ANAPHOR_TYPES.items():
        if anaphor not in msg_lower:
            continue
        # Heuristic: anaphor dạng bare → thay bằng entity type-khớp đủ dài.
        pattern = re.compile(r'\b' + re.escape(anaphor) + r'\b', re.IGNORECASE)
        for entity in all_entities:
            entity_lower = entity.lower()
            if any(kw in entity_lower for kw in keywords) and len(entity) > len(anaphor) + 3:
                new_resolved = pattern.sub(entity, resolved, count=1)
                if new_resolved != resolved:
                    resolved = new_resolved
                    break
    return resolved


def _resolve_pronouns(resolved: str, all_entities: list) -> str:
    top = all_entities[0]
    for pronoun in _CONTEXT_PRONOUNS:
        if pronoun in resolved.lower():
            resolved = re.sub(re.escape(pronoun), f"tại {top}", resolved, flags=re.IGNORECASE, count=1)
    return resolved


def _resolve_contextual_query(message: str, history: list[dict]) -> str:
    """
    Resolve anaphoric references in message using recent conversation history.
    E.g.: "từ bến tre đến bảo tàng" → "từ bến tre đến Bảo tàng Dừa Sáp Trà Vinh"
    when previous turn mentioned that museum.
    Pure rule-based, zero latency.
    """
    if not history:
        return message
    msg_lower = message.lower().strip()
    has_anaphor = any(a in msg_lower for a in _ANAPHOR_TYPES)
    has_pronoun = any(p in msg_lower for p in _CONTEXT_PRONOUNS)
    if not has_anaphor and not has_pronoun:
        return message
    all_entities = _extract_reply_entities(history)
    if not all_entities:
        return message
    resolved = _resolve_anaphors(msg_lower, message, all_entities)
    if has_pronoun:
        resolved = _resolve_pronouns(resolved, all_entities)
    return resolved


def _gather_context_pieces(current_month, rag_query, owner_key, session_id, message):
    """Thu 6 mảnh context (proactive/rag/realtime/memory/reflexion/graph). Trả dict."""
    realtime_ctx = ""
    if HAS_REALTIME:
        try:
            realtime_ctx = get_realtime_context() or ""
        except Exception:
            logger.debug("Realtime context failed", exc_info=True)
    graph_ctx = ""
    if HAS_MEMORY_GRAPH:
        try:
            graph_ctx = memory_graph.build_graph_context(owner_key) or ""
        except Exception:
            logger.debug("Memory graph context failed", exc_info=True)
    return {
        "proactive": get_proactive_context(month=current_month),
        "rag": build_rag_context(rag_query),
        "realtime": realtime_ctx,
        "memory": memory_manager.build_context(owner_key, session_id, message),
        "reflexion": reflexion_engine.get_reflection_prompt(message),
        "graph": graph_ctx,
    }


def _resolve_base_prompt(session_id):
    """Chọn base_prompt (A/B variant) + tiêm KB-in-context. Trả (base_prompt, ab_info)."""
    ab_info = {}
    base_prompt = SYSTEM_PROMPT
    if HAS_AB_TESTING and session_id:
        try:
            variant = ab_manager.assign_variant(
                "prompt_style",
                session_id,
                persist=False,
            )
            if variant:
                ab_info["prompt_style"] = variant["id"]
                style = variant.get("config", {}).get("style", "balanced")
                if style == "concise":
                    base_prompt = SYSTEM_PROMPT + "\nPhong cách trả lời: ngắn gọn, súc tích, đi thẳng vào trọng tâm."
                elif style == "detailed":
                    base_prompt = SYSTEM_PROMPT + "\nPhong cách trả lời: chi tiết, đầy đủ thông tin, có ví dụ minh họa."
        except Exception:
            logger.debug("A/B variant selection failed", exc_info=True)
    # KB-in-context: inject a compact index (or full digest) of the knowledge base
    # so the agent knows what exists → better searches + correct abstention. Static
    # until reload, so it lands in the cacheable static layer via base_prompt.
    if HAS_KB_CONTEXT:
        try:
            kb_ctx = kb_context.get_kb_context(knowledge._entities)
            if kb_ctx:
                base_prompt = base_prompt + "\n\n" + kb_ctx
        except Exception:
            logger.debug("KB context injection failed", exc_info=True)
    return base_prompt, ab_info


def _fold_lazy_prompt(builder, message, reflexion_ctx, label):
    """Gọi builder(message), gộp kết quả (nếu có) vào reflexion_ctx. Trả reflexion_ctx."""
    try:
        extra = builder(message) or ""
        if extra:
            reflexion_ctx = (reflexion_ctx or "") + ("\n" + extra)
    except Exception:
        logger.debug(f"{label} failed", exc_info=True)
    return reflexion_ctx


def _fold_experience_fewshot(message, reflexion_ctx):
    """Gộp experience-memory + few-shot demos vào reflexion_ctx (chỉ query phức tạp). Trả reflexion_ctx."""
    # Lazy context: skip heavy modules for simple queries (search/general)
    # to reduce token count and speed up responses. Only load for complex queries.
    _is_simple = not any(kw in message.lower() for kw in [
        "lịch trình", "so sánh", "kế hoạch", "tour", "ngày",
        "hành trình", "plan", "compare", "itinerary",
    ])
    if _is_simple:
        return reflexion_ctx
    # Experience memory (ReasoningBank-lite) + few-shot demos (BootstrapFewShot, OFF mặc định).
    if HAS_EXPERIENCE:
        reflexion_ctx = _fold_lazy_prompt(experience_memory.build_prompt, message, reflexion_ctx, "Experience memory")
    if HAS_FEWSHOT:
        reflexion_ctx = _fold_lazy_prompt(prompt_compiler.build_prompt, message, reflexion_ctx, "Few-shot prompt build")
    return reflexion_ctx


def _assemble_manual_messages(
    base_prompt, current_month, pieces, reflexion_ctx, history, owner_key, session_id, message
):
    """Fallback ráp tay (khi không có prompt-cache): system + history + user message. Trả messages."""
    system_parts = [
        base_prompt,
        f"\nHôm nay: {datetime.now(timezone.utc).strftime('%d/%m/%Y')}. Tháng hiện tại: {current_month}.",
    ]
    if pieces["proactive"]:
        system_parts.append(f"\n{pieces['proactive']}")
    if pieces["rag"]:
        system_parts.append(f"\n{pieces['rag']}")
    if pieces["realtime"]:
        system_parts.append(f"\n{pieces['realtime']}")
    if pieces["memory"]:
        system_parts.append(f"\n{pieces['memory']}")
    if pieces["graph"]:
        system_parts.append(f"\n{pieces['graph']}")
    if reflexion_ctx:
        system_parts.append(f"\n{reflexion_ctx}")

    system = "\n".join(system_parts)
    messages = [{"role": "system", "content": system}]

    messages.extend(history[-20:])

    messages.append({"role": "user", "content": message})
    return messages


def _fold_system_history_context(pieces: dict, history: list[dict]) -> tuple[dict, list[dict]]:
    """Move hot-memory summaries into the consolidated system context."""
    system_context = []
    conversation = []
    for item in history:
        if item.get("role") == "system":
            system_context.append(item["content"])
        else:
            conversation.append(item)
    if not system_context:
        return pieces, history
    folded = dict(pieces)
    folded["memory"] = "\n".join(
        part for part in (pieces["memory"], "\n".join(system_context)) if part
    )
    return folded, conversation


def _build_messages(
    message: str,
    history: list[dict],
    session_id: str = "",
    owner_key: str = "",
) -> tuple[list[dict], dict]:
    """
    Xây dựng messages cho LLM với đầy đủ context:
      1. System prompt cơ bản
      2. Proactive context (mùa vụ, thời gian, trending)
      3. Agentic RAG routing (query classification + graph context)
      4. Memory context (user profile + session preferences + skills)
      5. Reflexion context (lessons from past failures)
      6. A/B testing variant selection
      7. History + user message

    Returns: (messages, build_info) where build_info includes cache/AB stats
    """
    current_month = datetime.now(timezone.utc).month
    effective_history = history[-20:]
    if session_id:
        session = memory_manager.require_session(owner_key, session_id)
        ctx_messages = session.get_context_messages()
        if ctx_messages:
            effective_history = ctx_messages

    # Resolve anaphoric references (e.g. "bảo tàng" → specific museum from history)
    # before RAG so entity detection picks up the correct entity.
    rag_query = _resolve_contextual_query(message, effective_history)

    pieces = _gather_context_pieces(current_month, rag_query, owner_key, session_id, message)
    pieces, effective_history = _fold_system_history_context(pieces, effective_history)
    base_prompt, ab_info = _resolve_base_prompt(session_id)
    # Experience-memory + few-shot fold vào reflexion để chảy qua CẢ cached lẫn manual path.
    reflexion_ctx = _fold_experience_fewshot(message, pieces["reflexion"])

    # Use prompt cache if available
    if HAS_PROMPT_CACHE:
        messages, cache_info = prompt_cache.build_cached_prompt(
            message=message,
            history=effective_history,
            session_id=session_id,
            user_id=owner_key,
            system_prompt=base_prompt,
            proactive_context=pieces["proactive"] or "",
            rag_context=pieces["rag"] or "",
            realtime_context=pieces["realtime"],
            memory_context=(pieces["memory"] or "") + ("\n" + pieces["graph"] if pieces["graph"] else ""),
            reflexion_context=reflexion_ctx or "",
        )
        build_info = {**cache_info, "ab": ab_info}
        return messages, build_info

    # Fallback: manual assembly
    messages = _assemble_manual_messages(
        base_prompt, current_month, pieces, reflexion_ctx, effective_history, owner_key, session_id, message)
    return messages, {"ab": ab_info}


def _hydrate_empty_session(owner_key: str, session, history: list[dict[str, str]]) -> None:
    """Seed a new/empty hot session with bounded validated prior turns once."""
    if session.messages or not history:
        return
    for item in history[-session.max_messages:]:
        memory_manager.on_message(owner_key, session.session_id, item["role"], item["content"])


def _record_cached_exchange(owner_key: str, session_id: str, message: str, cached: dict) -> None:
    memory_manager.on_message(owner_key, session_id, "user", message)
    memory_manager.on_message(owner_key, session_id, "assistant", cached.get("reply", ""))


LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "30"))


SAFE_PRIVACY_FAILURE_REPLY = (
    "Xin lỗi, hệ thống không thể xác minh an toàn câu trả lời. Vui lòng thử lại."
)


_PUBLIC_CONTACT_FIELDS = ("phone", "email", "hotline", "contact_phone", "contact_email")


def _payload_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _payload_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _payload_strings(item)


def _entity_contact_values(entity: dict) -> set[str]:
    attrs = entity.get("attributes") or {}
    if not isinstance(attrs, dict):
        return set()
    return {
        value
        for field in _PUBLIC_CONTACT_FIELDS
        if isinstance((value := attrs.get(field)), str) and value
    }


def _payload_contact_values(value: dict) -> set[str]:
    attrs = value.get("attributes") or {}
    nested = attrs if isinstance(attrs, dict) else {}
    contacts = set()
    for field in _PUBLIC_CONTACT_FIELDS:
        for candidate in (value.get(field), nested.get(field)):
            if isinstance(candidate, str) and candidate:
                contacts.add(candidate)
    return contacts


def _eligible_public_entities() -> dict[str, dict]:
    return {
        entity_id: entity
        for entity_id, entity in (getattr(knowledge, "_entities", None) or {}).items()
        if isinstance(entity_id, str)
        and isinstance(entity, dict)
        and is_publicly_eligible(entity)
    }


def _public_entities_by_name(entities: dict[str, dict]) -> dict[str, list[dict]]:
    entities_by_name: dict[str, list[dict]] = {}
    for entity in entities.values():
        name = entity.get("name")
        if isinstance(name, str) and name:
            entities_by_name.setdefault(name, []).append(entity)
    return entities_by_name


def _selected_public_entity(
    item: dict,
    entities: dict[str, dict],
    entities_by_name: dict[str, list[dict]],
):
    for key in ("id", "entity_id"):
        entity_id = item.get(key)
        if isinstance(entity_id, str) and entity_id in entities:
            return entities[entity_id]
    name = item.get("name")
    matches = entities_by_name.get(name, []) if isinstance(name, str) else []
    return matches[0] if len(matches) == 1 else None


def _collect_verified_public_contacts(
    item,
    entities: dict[str, dict],
    entities_by_name: dict[str, list[dict]],
    contacts: set[str],
) -> None:
    if isinstance(item, dict):
        entity = _selected_public_entity(item, entities, entities_by_name)
        if entity is not None:
            contacts.update(
                _payload_contact_values(item) & _entity_contact_values(entity)
            )
        for child in item.values():
            _collect_verified_public_contacts(child, entities, entities_by_name, contacts)
    elif isinstance(item, (list, tuple)):
        for child in item:
            _collect_verified_public_contacts(child, entities, entities_by_name, contacts)


def _verified_public_contacts_from_payload(value) -> set[str]:
    """Return exact published contact fields present in this tool payload."""
    entities = _eligible_public_entities()
    entities_by_name = _public_entities_by_name(entities)
    contacts: set[str] = set()
    _collect_verified_public_contacts(value, entities, entities_by_name, contacts)
    return contacts


def _public_contact_markers(
    contacts: set[str], original_strings: tuple[str, ...]
) -> tuple[tuple[str, str], ...]:
    replacements = []
    for index, contact in enumerate(sorted(contacts, key=len, reverse=True)):
        marker = f"__VL360_PUBLIC_CONTACT_{index}__"
        while any(marker in original for original in original_strings):
            marker = "_" + marker
        replacements.append((contact, marker))
    return tuple(replacements)


def _protect_public_contact_value(
    item,
    replacements: tuple[tuple[str, str], ...],
    restorations: dict[str, str],
):
    if isinstance(item, str):
        protected = item
        for contact, marker in replacements:
            if contact in protected:
                protected = protected.replace(contact, marker)
                restorations[marker] = contact
        return protected
    if isinstance(item, dict):
        return {
            _protect_public_contact_value(key, replacements, restorations)
            if isinstance(key, str)
            else key: _protect_public_contact_value(child, replacements, restorations)
            for key, child in item.items()
        }
    if isinstance(item, list):
        return [
            _protect_public_contact_value(child, replacements, restorations)
            for child in item
        ]
    if isinstance(item, tuple):
        return tuple(
            _protect_public_contact_value(child, replacements, restorations)
            for child in item
        )
    return item


def _protect_public_contacts(value, contacts: set[str]):
    restorations: dict[str, str] = {}
    original_strings = tuple(_payload_strings(value))
    replacements = _public_contact_markers(contacts, original_strings)
    protected = _protect_public_contact_value(value, replacements, restorations)
    return protected, restorations


def _restore_public_contacts(value, restorations: dict[str, str]):
    if isinstance(value, str):
        restored = value
        for marker, contact in restorations.items():
            restored = restored.replace(marker, contact)
        return restored
    if isinstance(value, dict):
        return {
            _restore_public_contacts(key, restorations) if isinstance(key, str) else key:
            _restore_public_contacts(child, restorations)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_restore_public_contacts(child, restorations) for child in value]
    if isinstance(value, tuple):
        return tuple(_restore_public_contacts(child, restorations) for child in value)
    return value


def _safe_tool_result(result, verified_public_contacts: set[str]) -> str:
    """Redact one untrusted tool result before prompt, preview, or persistence use."""
    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False, default=str)
    try:
        parsed = json.loads(result)
        was_json = True
    except (json.JSONDecodeError, TypeError):
        parsed = result
        was_json = False

    new_contacts = _verified_public_contacts_from_payload(parsed)
    effective_contacts = verified_public_contacts | new_contacts
    protected, restorations = _protect_public_contacts(parsed, effective_contacts)
    safe_value = redact_payload(
        protected,
        source="untrusted_external",
        verified_public_contacts=tuple(effective_contacts),
    )
    safe_value = _restore_public_contacts(safe_value, restorations)
    if was_json:
        serialized = json.dumps(safe_value, ensure_ascii=False, default=str)
    else:
        serialized = str(safe_value)
    verified_public_contacts.update(new_contacts)
    return serialized


def _safe_delivered_reply(
    reply: str,
    query: str,
    entities,
    verified_public_contacts,
) -> SafeText:
    return prepare_chat_output(
        reply,
        query=query,
        entities=entities,
        verified_public_contacts=tuple(verified_public_contacts),
    )


def _safe_sse_event(payload: dict, verified_public_contacts: set[str]) -> dict:
    """Sanitize provider-derived SSE metadata before serialization."""
    return redact_payload(
        payload,
        source="verified_public_contact",
        verified_public_contacts=tuple(verified_public_contacts),
    )


def _safe_cached_reply(reply: str) -> SafeText:
    """Redact a legacy cache reply before any delivery or personal sink."""
    return redact_text(reply, source="legacy_cache")


def _safe_cached_payload(cached: dict) -> dict:
    """Apply the legacy-cache boundary to every retained cache field."""
    if not isinstance(cached, dict):
        raise PrivacyBoundaryUnavailable("INVALID_CACHED_RESPONSE")
    safe_payload = redact_payload(cached, source="legacy_cache")
    safe_reply = _safe_cached_reply(cached.get("reply", ""))
    safe_payload["reply"] = safe_reply.text
    return safe_payload


async def _safe_stream_text_events(chunks, redactor: StreamingPIIRedactor):
    """Yield only redacted stream text and abort on cancellation or failure."""
    try:
        async for chunk in chunks:
            safe_chunk = redactor.feed(chunk)
            if safe_chunk:
                yield safe_chunk
        safe_tail = redactor.finish()
        if safe_tail:
            yield safe_tail
    except BaseException:
        redactor.abort()
        raise


def _make_llm_call_fn(model_fn=None):
    """Create an LLM call function for orchestrator injection.

    ``model_fn`` is a callable returning the model name (resolved at call time).
    """

    def _llm_call_fn(messages, tools, temperature):
        _model = (model_fn or get_model)()
        if tools:
            if HAS_CIRCUIT_BREAKER:
                cb_result = safe_llm_call(get_client(), model=_model, messages=messages, tools=tools, tool_choice="auto", timeout=LLM_TIMEOUT)
                if not cb_result["success"]:
                    class _MockChoice:
                        class message:
                            content = cb_result["message"]
                            tool_calls = None
                    class _MockResponse:
                        choices = [_MockChoice()]
                        _skip_usage = True
                    return _MockResponse()
                return cb_result["response"]
            return get_client().chat.completions.create(
                model=_model, messages=messages, tools=tools, tool_choice="auto",
                timeout=LLM_TIMEOUT,
            )

        # No-tools synthesis call
        if HAS_CIRCUIT_BREAKER:
            cb_result = safe_llm_call(get_client(), model=_model, messages=messages, timeout=LLM_TIMEOUT)
            if not cb_result["success"]:
                class _MockChoice:
                    class message:
                        content = cb_result["message"]
                        tool_calls = None
                class _MockResponse:
                    choices = [_MockChoice()]
                    _skip_usage = True
                return _MockResponse()
            return cb_result["response"]
        return get_client().chat.completions.create(model=_model, messages=messages, timeout=LLM_TIMEOUT)

    return _llm_call_fn


_llm_call_fn_default = _make_llm_call_fn(get_model)


_llm_call_fn_mini = _make_llm_call_fn(get_model_mini)


_orchestrator = None


_orchestrator_lock = threading.Lock()


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None and HAS_ORCHESTRATOR:
        with _orchestrator_lock:
            if _orchestrator is None:
                _orchestrator = Orchestrator(TOOLS)
    return _orchestrator


def _optimal_params_fn(category: str) -> dict:
    """Return self_optimizer's tuned params for a query category (or {})."""
    if not HAS_OPTIMIZER:
        return {}
    try:
        return parameter_tuner.get_optimal_params(category)
    except Exception:
        logger.debug("Optimal params lookup failed for %s", category, exc_info=True)
        return {}


def _tool_order_fn(category: str) -> list:
    """Return learned tool ordering for a category (tool_weight_optimizer)."""
    if not HAS_OPTIMIZER:
        return []
    try:
        return tool_weight_optimizer.suggest_tool_order(category)
    except Exception:
        logger.debug("Tool order lookup failed for %s", category, exc_info=True)
        return []


def _run_agent_orchestrated(
    message,
    history,
    session_id,
    base_system_prompt,
    usage_accumulator=None,
    verified_public_contacts=None,
):
    """Run agent via the orchestrator, now wired with tuned params + parallel tools
    + learned tool ordering + smart model routing."""
    orch = _get_orchestrator()
    # Pre-route to pick model BEFORE the full run (so the LLM call function
    # is bound to the right model from the first round).
    _cat, _agent = orch.route(message)
    _use_mini = getattr(_agent, "use_mini", False)
    _call_fn = _llm_call_fn_mini if _use_mini else _llm_call_fn_default
    _model_fn = get_model_mini if _use_mini else get_model
    if _use_mini:
        logger.info("Model routing: using MINI", category=_cat.value, agent=_agent.name)

    contacts = verified_public_contacts if verified_public_contacts is not None else set()
    contacts_lock = threading.Lock()

    def _request_call_tool(name, args):
        result = call_tool(name, args, usage_accumulator)
        with contacts_lock:
            return _safe_tool_result(result, contacts)

    result = orch.run(
        message=message,
        history=history,
        session_id=session_id,
        base_system_prompt=base_system_prompt,
        call_tool_fn=_request_call_tool,
        llm_call_fn=_call_fn,
        get_params_fn=_optimal_params_fn if HAS_OPTIMIZER else None,
        tool_executor=(
            ParallelToolExecutor(_request_call_tool, max_workers=4)
            if HAS_PARALLEL else None
        ),
        tool_order_fn=_tool_order_fn if HAS_OPTIMIZER else None,
        usage_accumulator=usage_accumulator,
        model_name=_model_fn,
    )
    return result["reply"], result["tools_used"], result["suggestions"]


async def _await_chat_worker(func, *args):
    """Wait for provider work on cancellation, then preserve cancellation."""
    worker = asyncio.create_task(asyncio.to_thread(func, *args))
    try:
        await asyncio.wait({worker})
        return worker.result()
    except asyncio.CancelledError:
        with anyio.CancelScope(shield=True):
            while not worker.done():
                try:
                    await asyncio.wait({worker})
                except asyncio.CancelledError:
                    continue
            try:
                worker.result()
            except Exception:
                logger.debug("Chat worker failed after request cancellation", exc_info=True)
        raise


def _call_stream_decision(kwargs, usage_accumulator, model, messages):
    """Call and account for one stream tool-decision response in the worker."""
    if HAS_CIRCUIT_BREAKER:
        result = safe_llm_call(get_client(), **kwargs)
        if not result["success"]:
            return result
        response = result["response"]
    else:
        response = get_client().chat.completions.create(**kwargs)
        result = {"success": True, "response": response}
    usage_accumulator.add_response(
        response,
        model=model,
        messages=messages,
    )
    return result


def _prepare_pending_calls(tool_calls, tools_used, messages, total_tool_calls, max_tool_calls):
    """Chuẩn bị pending tool-calls từ msg.tool_calls (parse args, đếm, log tool). Trả (pending, total)."""
    pending_calls = []
    for tc in tool_calls:
        if total_tool_calls >= max_tool_calls:
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": json.dumps({"error": "Tool call limit reached. Please respond with available information."})
            })
            continue
        fn_name = tc.function.name
        try:
            fn_args = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, TypeError):
            fn_args = {}  # EH-02: LLM trả JSON args lỗi → dùng {} thay vì crash agent loop
        tools_used.append(f"{fn_name}({json.dumps(fn_args, ensure_ascii=False)})")
        total_tool_calls += 1
        pending_calls.append({"id": tc.id, "name": fn_name, "args": fn_args})
    return pending_calls, total_tool_calls


def _execute_pending_calls(pending_calls, parallel_exec, messages, suggestions,
                           empty_results_count, round_num, total_tool_calls,
                           call_tool_fn=None, verified_public_contacts=None):
    """Thực thi pending tool-calls (parallel khi >1, else serial). Trả empty_results_count."""
    if parallel_exec and len(pending_calls) > 1:
        call_items = [{"id": c["id"], "name": c["name"], "args": c["args"]} for c in pending_calls]
        results = parallel_exec.execute_smart(call_items)
        for pc, res in zip(pending_calls, results):
            logger.info("Tool call (parallel)", tool=pc["name"],
                        duration_ms=round(res.get("duration_ms", 0)), round=round_num + 1)
            result = res.get("result", json.dumps({"error": res.get("error", "Unknown")}))
            result = _safe_tool_result(
                result,
                verified_public_contacts if verified_public_contacts is not None else set(),
            )
            messages.append({"role": "tool", "tool_call_id": pc["id"], "content": result})
            _post_tool_process(pc["name"], pc["args"], result, suggestions, messages, empty_results_count)
    else:
        tool_caller = call_tool_fn or call_tool
        for pc in pending_calls:
            logger.info(f"Tool call #{total_tool_calls}", tool=pc["name"],
                        args=str(pc["args"])[:200], round=round_num + 1)
            result = tool_caller(pc["name"], pc["args"])
            result = _safe_tool_result(
                result,
                verified_public_contacts if verified_public_contacts is not None else set(),
            )
            messages.append({"role": "tool", "tool_call_id": pc["id"], "content": result})
            empty_results_count = _post_tool_process(pc["name"], pc["args"], result, suggestions, messages, empty_results_count)
    return empty_results_count


def _run_agent(
    messages: list[dict],
    max_rounds: int = 8,
    max_tool_calls: int = 15,
    usage_accumulator=None,
    verified_public_contacts=None,
):
    """
    ReAct-style agent loop with multi-turn tool calling.

    v7 enhancements:
    - Circuit breaker protection on LLM calls
    - Parallel tool execution for independent calls
    - Self-correction on empty search results

    Returns (reply, tools_used, suggestions).
    """
    tools_used = []
    suggestions = []
    total_tool_calls = 0
    empty_results_count = 0

    contacts = verified_public_contacts if verified_public_contacts is not None else set()
    contacts_lock = threading.Lock()

    def _request_call_tool(name, args):
        result = call_tool(name, args, usage_accumulator)
        with contacts_lock:
            return _safe_tool_result(result, contacts)

    # Setup parallel executor if available
    parallel_exec = None
    if HAS_PARALLEL:
        parallel_exec = ParallelToolExecutor(_request_call_tool, max_workers=4)

    for round_num in range(max_rounds):
        # Circuit breaker protected LLM call
        try:
            _model = get_model()
            if HAS_CIRCUIT_BREAKER:
                cb_result = safe_llm_call(get_client(), model=_model, messages=messages, tools=TOOLS, tool_choice="auto")
                if not cb_result["success"]:
                    return cb_result["message"], tools_used, suggestions
                response = cb_result["response"]
            else:
                response = get_client().chat.completions.create(
                    model=_model, messages=messages, tools=TOOLS, tool_choice="auto",
                    timeout=LLM_TIMEOUT,
                )
            if usage_accumulator is not None:
                usage_accumulator.add_response(
                    response,
                    model=_model,
                    messages=messages,
                )
            msg = response.choices[0].message
        except Exception as llm_err:
            logger.error("LLM API call failed", error=str(llm_err), round=round_num)
            return "Xin lỗi, hệ thống đang tạm thời gặp sự cố kết nối. Vui lòng thử lại sau ít phút.", tools_used, suggestions

        if not msg.tool_calls:
            return msg.content or "", tools_used, suggestions

        messages.append(msg)

        pending_calls, total_tool_calls = _prepare_pending_calls(
            msg.tool_calls, tools_used, messages, total_tool_calls, max_tool_calls)
        empty_results_count = _execute_pending_calls(
            pending_calls, parallel_exec, messages, suggestions,
            empty_results_count, round_num, total_tool_calls,
            _request_call_tool, contacts)

    return msg.content or "Xin lỗi, tôi không thể trả lời đầy đủ câu hỏi này.", tools_used, suggestions


def _post_tool_process(fn_name, fn_args, result, suggestions, messages, empty_results_count):
    """Post-process tool result: track analytics, collect suggestions, self-correct.
    Returns the updated empty_results_count (int is immutable, so must return).
    """
    # Track entity discussions
    if fn_name in ("entity_detail", "nearby_entities") and "entity_id" in fn_args:
        try:
            analytics.track_entity_hit(fn_args["entity_id"])
        except Exception:
            logger.warning("analytics.track_entity_hit failed (post-tool)", exc_info=True)

    # Collect suggestions
    if fn_name == "suggest_followups":
        try:
            data = json.loads(result)
            sug = data.get("suggestions", [])
            if sug:
                suggestions.clear()
                suggestions.extend(sug)
        except Exception:
            logger.debug("Failed to parse suggest_followups result", exc_info=True)

    # Self-correction: if search returned empty, inject a hint
    if fn_name == "search":
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list) and len(parsed) == 0:
                empty_results_count += 1
                if empty_results_count <= 2:
                    messages.append({
                        "role": "system",
                        "content": "[Observation]: Search returned 0 results. Try broader keywords, remove filters, or use web_search as fallback."
                    })
        except Exception:
            logger.debug("Tool loop search fallback failed", exc_info=True)

    return empty_results_count


def _pick_delivery_model(corrected_message: str) -> str:
    delivery_model = get_model()
    if HAS_ORCHESTRATOR:
        try:
            _feedback_category, _feedback_agent = _get_orchestrator().route(
                corrected_message
            )
            if getattr(_feedback_agent, "use_mini", False):
                delivery_model = get_model_mini()
        except Exception:
            logger.debug("Feedback model routing failed", exc_info=True)
    return delivery_model


def _dynamic_prompt_addon(corrected_message: str, session_id: str) -> str:
    """Dynamic agents: check for specialist match before orchestrator."""
    if not HAS_DYNAMIC_AGENTS:
        return ""
    try:
        dyn_route = check_dynamic_route(corrected_message)
        if dyn_route:
            agent_factory.update_performance(dyn_route["agent_id"], 5.0)  # default, updated later
            logger.info("Dynamic agent matched", agent=dyn_route.get("name", ""), session_id=session_id)
            return dyn_route.get("system_prompt_addon", "")
    except Exception:
        logger.debug("Dynamic agent matching failed", exc_info=True)
    return ""


def _compose_enriched_system(messages: list, dyn_prompt_addon: str) -> str:
    """Enriched system context (proactive + RAG + realtime + memory + reflexion
    + graph) mà _build_messages vừa tính — messages[0] luôn là system message
    hợp nhất; cộng thêm addon của dynamic-agent và biến thể self_optimizer."""
    _enriched_system = SYSTEM_PROMPT
    if messages and messages[0].get("role") == "system" and isinstance(messages[0].get("content"), str):
        _enriched_system = messages[0]["content"]
    if dyn_prompt_addon:
        _enriched_system = _enriched_system + "\n\n" + dyn_prompt_addon
    if HAS_OPTIMIZER:
        try:
            _variant = prompt_optimizer.get_current_variant()
            _variant_addon = _variant.get("prompt_addon", "")
            if _variant_addon:
                _enriched_system = _enriched_system + "\n\n" + _variant_addon
        except Exception:
            logger.debug("Self-optimizer variant failed", exc_info=True)
    return _enriched_system


def _is_error_reply(reply: str) -> bool:
    """P0/chat: chỉ coi là lỗi khi reply RỖNG, hoặc là fallback hệ-thống thật (mọi fallback
    đều mở đầu "Xin lỗi/Rất tiếc/Hệ thống..." + chứa cụm sự-cố), hoặc reply rất ngắn báo lỗi.
    Tránh false-positive: câu trả lời ĐÚNG có chứa "lỗi"/"sự cố" (vd "sự cố giao thông")
    trước đây bị ghi đè bằng KB-fallback."""
    _low = (reply or "").lower().lstrip()
    _starts_apology = _low.startswith(("xin lỗi", "rất tiếc", "hệ thống ai đang", "hệ thống đang"))
    _has_fail_word = any(w in _low for w in (
        "sự cố", "đã xảy ra lỗi", "không thể trả lời", "đang bảo trì", "thử lại sau", "thử lại.",
    ))
    return (
        not reply
        or (_starts_apology and _has_fail_word)
        or (len(reply) < 80 and _has_fail_word)
    )


def _kb_clean_query(corrected_message: str) -> str:
    # Clean query: strip question words (both with and without Vietnamese diacritics)
    _clean_q = re.sub(
        r'\b(ở đâu|o dau|đâu|dau|là gì|la gi|gì|gi|như thế nào|nhu the nao'
        r'|có gì|co gi|bao nhiêu|bao nhieu|khi nào|khi nao|tại sao|tai sao'
        r'|thế nào|the nao|nào|nao|ở|o|là|la|có|co|nên|nen|được|duoc'
        r'|không|khong|bao giờ|bao gio|mấy|may|sao|đi|di|nên đi|nen di)\b',
        '', corrected_message, flags=re.IGNORECASE
    ).strip().rstrip('?').strip()
    # Remove extra whitespace from stripping
    _clean_q = re.sub(r'\s+', ' ', _clean_q).strip()
    if not _clean_q:
        _clean_q = corrected_message
    return _clean_q


def _detect_search_month(corrected_message: str) -> int | None:
    # Detect month numbers for seasonal queries
    _month_match = re.search(r'(?:tháng|thang)\s*(\d{1,2})', corrected_message, re.IGNORECASE)
    return int(_month_match.group(1)) if _month_match and 1 <= int(_month_match.group(1)) <= 12 else None


def _kb_fallback_search(clean_q: str, search_month: int | None, is_month_only) -> list:
    # Call knowledge.search_entities directly — avoid call_tool() which has
    # analytics tracking that can crash on corrupt analytics files
    if is_month_only:
        # Pure seasonal query — get seasonal + attractions for that month
        kb_data = knowledge.seasonal_now(search_month)
        if not kb_data:
            kb_data = knowledge.search_entities(month=search_month, limit=10)
    else:
        # Use hybrid rerank (BM25 + semantic) for better relevance when
        # available; this is the degraded-mode path so quality matters.
        kb_data = _hybrid_rerank_search({"q": clean_q, "month": search_month, "limit": 10})

    # Progressive search: if full query returns nothing, try sub-phrases
    if not kb_data:
        words = clean_q.split()
        # Try bigrams first (e.g. "Chợ nổi", "Cái Bè")
        if len(words) >= 2:
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                kb_data = knowledge.search_entities(q=bigram, limit=10)
                if kb_data:
                    logger.info(f"KB fallback bigram hit | q={bigram} | count={len(kb_data)}")
                    break
        # Try individual words (skip short ones)
        if not kb_data:
            for w in sorted(words, key=len, reverse=True):
                if len(w) >= 3:
                    kb_data = knowledge.search_entities(q=w, limit=10)
                    if kb_data:
                        logger.info(f"KB fallback word hit | q={w} | count={len(kb_data)}")
                        break
    return kb_data


def _format_kb_reply(kb_data: list, search_month: int | None) -> str:
    if search_month:
        lines = [f"Hệ thống AI đang bảo trì. Thông tin tháng {search_month} từ cơ sở dữ liệu:\n"]
    else:
        lines = ["Hệ thống AI đang bảo trì. Dưới đây là thông tin từ cơ sở dữ liệu:\n"]
    for item in kb_data[:5]:
        name = item.get("name", "")
        summary = item.get("summary", "")
        etype = item.get("type", "")
        place = (knowledge.get_place(item["id"]) or {}).get("name", "")
        if name and summary:
            loc = f" — {place}" if place else ""
            lines.append(f"• **{name}** ({etype}{loc}): {summary}")
        elif name:
            lines.append(f"• **{name}** ({etype})")
    lines.append("\n*Khi hệ thống AI hoạt động trở lại, bạn sẽ nhận được câu trả lời chi tiết hơn.*")
    return "\n".join(lines)


def _kb_fallback_reply(corrected_message: str) -> tuple[str | None, list, set, bool]:
    """(reply|None, tools_used, verified_contacts, errored) — None = giữ reply cũ."""
    try:
        _clean_q = _kb_clean_query(corrected_message)
        _search_month = _detect_search_month(corrected_message)
        logger.info(f"KB fallback search | query={_clean_q} | month={_search_month} | original={corrected_message[:80]}")
        # Check if query is purely about a month (e.g. cleaned to "Tháng 6" or empty)
        _is_month_only = _search_month and re.match(
            r'^(tháng|thang)?\s*\d{1,2}\s*$', _clean_q, re.IGNORECASE
        )
        kb_data = _kb_fallback_search(_clean_q, _search_month, _is_month_only)

        _kb_count = len(kb_data) if isinstance(kb_data, list) else 0
        logger.info(f"KB fallback results | count={_kb_count}")
        # Relevance gate: drop entities that don't plausibly match the query
        # (weak token matches) so the degraded mode abstains honestly instead
        # of presenting irrelevant/out-of-domain data as an answer.
        if isinstance(kb_data, list) and kb_data and not _is_month_only:
            _relevant = [it for it in kb_data if knowledge.query_relevance(corrected_message, it)]
            if not _relevant:
                logger.info("KB fallback: no relevant entity → abstaining")
                reply = (
                    "Xin lỗi, hệ thống AI đang bảo trì và mình chưa tìm thấy thông tin "
                    "xác thực về câu hỏi này trong cơ sở dữ liệu Vĩnh Long 360. "
                    "Bạn thử hỏi về điểm tham quan, ẩm thực, đặc sản, lễ hội hoặc lịch trình "
                    "ở Vĩnh Long, Bến Tre, Trà Vinh nhé!"
                )
                return reply, ["abstain (kb-fallback)"], set(), False
            kb_data = _relevant
        if isinstance(kb_data, list) and kb_data:
            contacts = set(_verified_public_contacts_from_payload(kb_data))
            return _format_kb_reply(kb_data, _search_month), ["search (kb-fallback)"], contacts, False
        return None, [], set(), False
    except Exception as kb_err:
        logger.warning("KB fallback error", error=str(kb_err))
        return None, [], set(), True


def _open_chat_session(request: Request, owner_context, requested_session_id: str):
    """(session, None) | (None, response-lỗi 429/404) — rate-limit + require-session."""
    client_ip = get_client_ip(request)
    allowed, rate_info = chat_limiter.is_allowed(client_ip)
    if not allowed:
        logger.warning("Rate limited", ip=client_ip, endpoint="/chat")
        _resp = _error_response(429, "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
                                retry_after=rate_info["retry_after"])
        _resp.headers["Retry-After"] = str(rate_info["retry_after"])
        set_chat_owner_cookie(_resp, owner_context)
        return None, _resp

    session = None
    try:
        if requested_session_id:
            session = memory_manager.require_session(
                owner_context.owner_key, requested_session_id
            )
    except UnknownConversation:
        not_found = _error_response(404, "Không tìm thấy cuộc trò chuyện.", request)
        set_chat_owner_cookie(not_found, owner_context)
        return None, not_found
    return session, None


def _autocorrected(message: str) -> str:
    corrected_message = message
    if HAS_AUTOCORRECT:
        ac = autocorrect(message)
        if ac.get("was_corrected"):
            corrected_message = ac["corrected"]
    return corrected_message


def _settle_chat_usage(usage_accumulator, owner_key: str, corrected_message: str) -> None:
    try:
        usage_accumulator.settle(
            owner_key=owner_key,
            query=corrected_message[:200],
            agent_name="chat",
            guardrail_budget=guardrail_budget if HAS_GUARDRAILS else None,
            cost_attribution=cost_attribution if HAS_COST_TRACKER else None,
        )
    except Exception:
        logger.debug("Cost tracking failed", exc_info=True)


def _apply_kb_fallback(
    reply, tools_used, suggestions, corrected_message, verified_public_contacts
):
    """Áp KB-fallback khi reply là lỗi; trả bộ (reply, tools_used, suggestions) mới."""
    _error_reply = _is_error_reply(reply)
    logger.info(f"KB fallback check | is_error={_error_reply} | reply_len={len(reply) if reply else 0}")
    if _error_reply and corrected_message.strip():
        fb_reply, fb_tools, fb_contacts, fb_errored = _kb_fallback_reply(corrected_message)
        if fb_reply is not None:
            verified_public_contacts.update(fb_contacts)
            return fb_reply, fb_tools, []
        if fb_errored and not reply:
            return "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi. Vui lòng thử lại.", tools_used, suggestions
    return reply, tools_used, suggestions


async def _run_chat_round(
    corrected_message, history, session_id, owner_key,
    usage_accumulator, verified_public_contacts, settle_usage,
):
    """Một vòng LLM đầy đủ (build → dispatch → trace) với xử lý lỗi nguyên trạng."""
    _trace_ctx = None
    reply, tools_used, suggestions = "", [], []
    try:
        if HAS_TRACING:
            _trace_ctx = trace_chat_request(corrected_message, session_id, get_model())
            _trace_ctx.__enter__()
        messages, build_info = _build_messages(corrected_message, history, session_id, owner_key)

        _enriched_system = _compose_enriched_system(
            messages, _dynamic_prompt_addon(corrected_message, session_id)
        )

        # Use orchestrator when available for specialist routing.
        # GĐ4.1: offload vòng lặp agent (OpenAI client ĐỒNG BỘ) sang thread để KHÔNG
        # chặn event loop -> nhiều /chat đồng thời + /health không bị đóng băng.
        if HAS_ORCHESTRATOR:
            reply, tools_used, suggestions = await _await_chat_worker(
                _run_agent_orchestrated,
                corrected_message, messages[1:-1], session_id, _enriched_system,
                usage_accumulator,
                verified_public_contacts,
            )
        else:
            messages[0]["content"] = _enriched_system
            reply, tools_used, suggestions = await _await_chat_worker(
                _run_agent,
                messages,
                8,
                15,
                usage_accumulator,
                verified_public_contacts,
            )
    except asyncio.CancelledError:
        settle_usage()
        raise
    except Exception as exc:
        error_tracker.record_error("/chat", str(exc), traceback.format_exc())
        if HAS_METRICS:
            track_error("/chat", type(exc).__name__)
        logger.error("Chat error", error=str(exc), session_id=session_id)
        reply = ""
        tools_used, suggestions = [], []
    finally:
        if _trace_ctx:
            try:
                _trace_ctx.__exit__(None, None, None)
            except Exception:
                logger.debug("Trace context exit failed", exc_info=True)
    return reply, tools_used, suggestions


def _prepared_chat_input(req: "ChatRequest", owner_key: str, session_id: str):
    """(safe_input, None) hoặc (None, ChatResponse-từ-chối) — biên riêng tư đầu vào."""
    try:
        safe_input = prepare_chat_input(
            req.message,
            [item.model_dump() for item in req.history],
            owner_key=owner_key,
        )
    except PrivacyBoundaryBlocked as exc:
        logger.warning(
            "Privacy boundary blocked input",
            code=exc.code,
            session_id=session_id,
        )
        return None, ChatResponse(
            reply="Xin lỗi, tin nhắn này không thể xử lý vì lý do an toàn. Vui lòng diễn đạt lại.",
            tool_calls=[], suggestions=[], session_id=session_id,
        )
    except PrivacyBoundaryUnavailable as exc:
        logger.warning(
            "Privacy boundary unavailable",
            code=exc.code,
            session_id=session_id,
        )
        return None, ChatResponse(
            reply="Xin lỗi, hệ thống đang bận kiểm tra an toàn. Vui lòng thử lại sau ít phút.",
            tool_calls=[], suggestions=[], session_id=session_id,
        )
    except Exception:
        logger.warning(
            "Privacy boundary unavailable",
            code="UNEXPECTED_PRIVACY_BOUNDARY_ERROR",
            session_id=session_id,
        )
        return None, ChatResponse(
            reply="Xin lỗi, hệ thống đang bận kiểm tra an toàn. Vui lòng thử lại sau ít phút.",
            tool_calls=[], suggestions=[], session_id=session_id,
        )
    return safe_input, None


def _delivered_safe_reply_text(reply, message, verified_public_contacts, session_id):
    """(safe_text, None) hoặc (None, ChatResponse-từ-chối) — biên riêng tư đầu ra."""
    try:
        safe_reply = _safe_delivered_reply(
            reply,
            message,
            (knowledge._entities or {}) if hasattr(knowledge, "_entities") else {},
            verified_public_contacts,
        )
        return safe_reply.text, None
    except PrivacyBoundaryUnavailable as exc:
        logger.warning("Privacy boundary unavailable for output", code=exc.code)
    except Exception:
        logger.warning(
            "Privacy boundary unavailable for output",
            code="UNEXPECTED_PRIVACY_OUTPUT_ERROR",
        )
    return None, ChatResponse(
        reply=SAFE_PRIVACY_FAILURE_REPLY,
        tool_calls=[],
        suggestions=[],
        session_id=session_id,
    )


async def _semantic_cache_lookup(cache_eligible: bool, message: str, owner_key: str, session_id: str):
    """(semantic_dedup_key, ChatResponse-cache-hit|None).

    Chạy TRONG cùng task async của chat() — _hold_semantic_route_lease đặt
    contextvar, đẩy sang thread/context khác là mất lease.
    """
    semantic_dedup_key = None
    if not (cache_eligible and HAS_SEMANTIC_CACHE):
        return None, None
    try:
        sem_cached = await semantic_get_async(message, owner_key=owner_key)
        semantic_dedup_key = semantic_take_dedup_lease(
            message,
            owner_key=owner_key,
        )
        _hold_semantic_route_lease(
            message,
            owner_key,
            semantic_dedup_key,
        )
        if sem_cached:
            return semantic_dedup_key, _deliver_cached_response(
                owner_key, session_id, message, sem_cached,
                publish_semantic=False, semantic_dedup_key=None,
            )
    except Exception:
        logger.debug("Semantic cache retrieval failed", exc_info=True)
    return semantic_dedup_key, None


def _exact_cache_lookup(message, owner_key, session_id, semantic_dedup_key):
    """ChatResponse exact-cache-hit hoặc None (kèm đếm miss)."""
    cached = cache.get(message, owner_key=owner_key)
    if cached:
        return _deliver_cached_response(
            owner_key, session_id, message, cached,
            publish_semantic=HAS_SEMANTIC_CACHE,
            semantic_dedup_key=semantic_dedup_key,
        )
    if HAS_METRICS:
        track_cache("miss")
    return None


def _deliver_cached_response(
    owner_key, session_id, message, cached_payload, *,
    publish_semantic, semantic_dedup_key,
):
    """ChatResponse cho một cache-hit (semantic hoặc exact) sau biên riêng tư.

    publish_semantic: exact-hit công bố lại vào semantic cache; semantic-hit thì không.
    """
    try:
        safe_cached = _safe_cached_payload(cached_payload)
    except PrivacyBoundaryUnavailable as exc:
        logger.warning("Legacy cache privacy boundary unavailable", code=exc.code)
        return ChatResponse(
            reply=SAFE_PRIVACY_FAILURE_REPLY,
            tool_calls=[],
            suggestions=[],
            session_id=session_id,
        )
    if HAS_METRICS:
        track_cache("hit")
    _privacy_output_boundary_marker = True
    if publish_semantic:
        try:
            semantic_put(
                message,
                safe_cached,
                owner_key=owner_key,
                dedup_key=semantic_dedup_key,
            )
        except Exception:
            logger.debug("Semantic cache exact-hit publication failed", exc_info=True)
    _record_cached_exchange(owner_key, session_id, message, safe_cached)
    feedback_receipt = _issue_delivered_feedback_receipt(
        owner_key,
        message,
        safe_cached.get("reply", ""),
        "cache",
        safe_cached.get("tool_calls", []),
    )
    return ChatResponse(
        **safe_cached,
        session_id=session_id,
        cached=True,
        feedback_receipt=feedback_receipt,
    )


def _record_turn_memory(owner_key, session_id, message, reply, corrected_message) -> None:
    """Sink lịch-sử/bộ-nhớ — chỉ nhận text ĐÃ QUA biên riêng tư của chat()."""
    _privacy_output_boundary_marker = True
    memory_manager.on_message(owner_key, session_id, "user", message)
    memory_manager.on_message(owner_key, session_id, "assistant", reply)

    # Memory graph: record entity interactions
    if HAS_MEMORY_GRAPH:
        try:
            memory_graph.on_chat_complete(owner_key, corrected_message, reply, [])
        except Exception:
            logger.debug("Memory graph record failed", exc_info=True)

    # LLM memory extraction: extract preferences/facts
    try:
        memory_manager.on_chat_complete(owner_key, session_id, corrected_message, reply)
    except Exception:
        logger.debug("LLM memory extraction failed", exc_info=True)


def _evaluate_and_record(message, reply, tools_used, owner_key) -> dict:
    """Reflexion + các kho học-tập — chỉ nhận text ĐÃ QUA biên riêng tư."""
    _privacy_output_boundary_marker = True
    try:
        evaluation = reflexion_engine.evaluate_answer(message, reply, tools_used)
        quality_tracker.record(message, evaluation["score"], tools_used)

        if evaluation["score"] < 5:
            reflexion_engine.reflect_on_failure(message, reply, evaluation)
            logger.warning("Low quality answer", score=evaluation["score"],
                         issues=evaluation["issues"], query=message[:100])
        elif evaluation["score"] >= 8:
            # Good answer → save as skill
            memory_manager.on_good_answer(
                message[:100], tools_used,
                f"Score {evaluation['score']}: {', '.join(evaluation['good_points'][:2])}",
                reflexion_engine._categorize_query(message),
            )
        # Experience memory: distill a strategy item (≥8) or negative constraint (<5)
        if HAS_EXPERIENCE:
            try:
                experience_memory.record(
                    message,
                    tools_used,
                    evaluation["score"],
                    reply,
                    owner_key=owner_key,
                )
            except Exception:
                logger.debug("Experience memory record failed", exc_info=True)
        # Few-shot demo pool: capture high-scoring (query, answer) exemplars
        if HAS_FEWSHOT:
            try:
                prompt_compiler.record_demo(
                    message,
                    reply,
                    evaluation["score"],
                    owner_key=owner_key,
                )
            except Exception:
                logger.debug("Few-shot demo record failed", exc_info=True)
    except Exception as eval_err:
        logger.warning("Reflexion evaluation error", error=str(eval_err))
        evaluation = {"score": 0, "issues": [], "good_points": []}
    return evaluation


def _record_optimizer_and_judge(
    session_id, corrected_message, message, reply, tools_used,
    evaluation, duration, owner_key,
) -> None:
    _privacy_output_boundary_marker = True
    # ── Self optimizer: record outcome for auto-tuning ──
    if HAS_OPTIMIZER:
        try:
            est_tokens = token_counter.estimate_tokens(reply) if HAS_COST_TRACKER else len(reply) // 3
            record_outcome(session_id, corrected_message, "orchestrator" if HAS_ORCHESTRATOR else "direct",
                          tools_used, evaluation["score"], duration, est_tokens,
                          owner_key=owner_key)
        except Exception:
            logger.debug("Self-optimizer outcome record failed", exc_info=True)

    # ── LLM Judge: quality evaluation (non-blocking, best-effort) ──
    if HAS_LLM_JUDGE and LLM_JUDGE_ENABLED and evaluation["score"] >= 3:
        try:
            judge_result = judge(corrected_message, reply)
            if judge_result and judge_result.get("weighted_score", 0) < 4:
                logger.info("LLM Judge low score", score=judge_result.get("weighted_score"), query=message[:80])
        except Exception:
            logger.debug("LLM Judge evaluation failed", exc_info=True)


def _record_chat_telemetry(
    session_id, corrected_message, message, reply, tools_used,
    evaluation, duration, owner_key,
) -> None:
    """Optimizer/judge/AB/metrics/analytics — chỉ nhận text ĐÃ QUA biên riêng tư."""
    _privacy_output_boundary_marker = True
    _record_optimizer_and_judge(
        session_id, corrected_message, message, reply, tools_used,
        evaluation, duration, owner_key,
    )
    # A/B testing: record outcome
    if HAS_AB_TESTING and session_id:
        try:
            ab_manager.record_outcome(
                "prompt_style",
                session_id,
                evaluation["score"],
                owner_key=owner_key,
            )
        except Exception:
            logger.debug("A/B outcome record failed", exc_info=True)

    # Metrics tracking
    if HAS_METRICS:
        track_chat_request("ok", duration)

    # Track analytics
    try:
        analytics.track_query(
            message,
            tools_used,
            reply,
            session_id,
            owner_key=owner_key,
        )
    except Exception:
        logger.debug("Analytics tracking failed", exc_info=True)


def _maybe_cache_reply(
    cache_eligible, message, reply, tools_used, suggestions,
    evaluation, owner_key, semantic_dedup_key,
) -> None:
    """Cache put (thường + semantic) khi đủ chất lượng — text ĐÃ QUA biên riêng tư."""
    _privacy_output_boundary_marker = True
    if not (cache_eligible and len(reply) > 30 and evaluation["score"] >= 5):
        return
    cache_data = {"reply": reply, "tool_calls": tools_used, "suggestions": suggestions}
    owner_write_gate.assert_writable(owner_key)
    cache.put(message, cache_data, owner_key=owner_key)
    # ── Semantic cache: store for embedding-based dedup ──
    if HAS_SEMANTIC_CACHE:
        try:
            semantic_put(
                message,
                cache_data,
                owner_key=owner_key,
                dedup_key=semantic_dedup_key,
            )
        except Exception:
            pass
    if HAS_METRICS:
        track_cache("set")


@router.post("/chat", response_model=ChatResponse)
@_finalize_semantic_route_lease
async def chat(req: ChatRequest, request: Request, response: Response):
    owner_context = await resolve_chat_owner(request)
    owner_key = owner_context.owner_key
    session = None
    requested_session_id = req.session_id or ""
    session_id = requested_session_id
    set_chat_owner_cookie(response, owner_context)

    session, gate_response = _open_chat_session(
        request, owner_context, requested_session_id
    )
    if gate_response is not None:
        return gate_response

    safe_input, refusal = _prepared_chat_input(req, owner_key, session_id)
    if refusal is not None:
        return refusal

    _privacy_input_boundary_marker = True
    message = safe_input.message
    history = [
        {"role": item.role, "content": item.content}
        for item in safe_input.history
    ]

    if session is None:
        session = memory_manager.create_session(owner_key)
        session_id = session.session_id
    _hydrate_empty_session(owner_key, session, history)
    cache_eligible = not history and not session.get_context_messages()

    # ── Semantic cache: embedding-based dedup (before regular cache) ──
    semantic_dedup_key, cached_response = await _semantic_cache_lookup(
        cache_eligible, message, owner_key, session_id
    )
    if cached_response is not None:
        return cached_response

    # Check cache (only for new conversations without history)
    if cache_eligible:
        exact_hit = _exact_cache_lookup(
            message, owner_key, session_id, semantic_dedup_key
        )
        if exact_hit is not None:
            return exact_hit

    usage_accumulator = UsageAccumulator()
    verified_public_contacts: set[str] = set()

    corrected_message = _autocorrected(message)
    settle_usage = partial(
        _settle_chat_usage, usage_accumulator, owner_key, corrected_message
    )
    delivery_model = _pick_delivery_model(corrected_message)

    t0 = time.time()
    reply, tools_used, suggestions = await _run_chat_round(
        corrected_message, history, session_id, owner_key,
        usage_accumulator, verified_public_contacts, settle_usage,
    )

    # ── Knowledge-only fallback: supplement with KB data when LLM fails ──
    reply, tools_used, suggestions = _apply_kb_fallback(
        reply, tools_used, suggestions, corrected_message, verified_public_contacts
    )

    safe_text, refusal = _delivered_safe_reply_text(
        reply, message, verified_public_contacts, session_id
    )
    if refusal is not None:
        return refusal

    reply = safe_text
    tools_used = redact_payload(tools_used, source="provider_output")
    suggestions = redact_payload(suggestions, source="provider_output")
    _privacy_output_boundary_marker = True
    settle_usage()
    duration = time.time() - t0

    _record_turn_memory(owner_key, session_id, message, reply, corrected_message)
    evaluation = _evaluate_and_record(message, reply, tools_used, owner_key)

    _record_chat_telemetry(
        session_id, corrected_message, message, reply, tools_used,
        evaluation, duration, owner_key,
    )
    _maybe_cache_reply(
        cache_eligible, message, reply, tools_used, suggestions,
        evaluation, owner_key, semantic_dedup_key,
    )

    feedback_receipt = _issue_delivered_feedback_receipt(
        owner_key,
        message,
        reply,
        delivery_model,
        tools_used,
    )
    return ChatResponse(
        reply=reply,
        tool_calls=tools_used,
        suggestions=suggestions,
        session_id=session_id,
        feedback_receipt=feedback_receipt,
    )


@dataclass
class _StreamContext:
    """Trạng thái một lượt /chat/stream — thay bộ closure/nonlocal cũ."""

    owner_key: str
    message: str
    sid: str
    messages: list
    cache_query: str
    cache_eligible: bool
    verified_public_contacts: set
    usage_accumulator: object
    semantic_dedup_key: object
    stream_model: str
    stream_temp: object
    stream_rounds: int
    settlement_blocked: bool = False


async def _event_stream_body(ctx: "_StreamContext"):
    # Send autocorrect info if corrected
    if HAS_AUTOCORRECT and ctx.message != ctx.cache_query:
        yield f"data: {json.dumps({'type': 'autocorrect', 'original': ctx.cache_query, 'corrected': ctx.message}, ensure_ascii=False)}\n\n"
    tools_used = []
    suggestions = []
    max_rounds = ctx.stream_rounds

    def prepare_stream_fallback(raw_reply) -> str | None:
        try:
            safe_fallback = _safe_delivered_reply(
                raw_reply,
                ctx.message,
                (knowledge._entities or {}) if hasattr(knowledge, "_entities") else {},
                ctx.verified_public_contacts,
            )
        except PrivacyBoundaryUnavailable as exc:
            logger.warning(
                "Privacy boundary unavailable for stream fallback",
                code=exc.code,
            )
            ctx.settlement_blocked = True
            return None
        except Exception:
            logger.warning(
                "Privacy boundary unavailable for stream fallback",
                code="UNEXPECTED_PRIVACY_OUTPUT_ERROR",
            )
            ctx.settlement_blocked = True
            return None

        return safe_fallback.text

    def persist_stream_fallback(safe_text: str) -> None:
        _privacy_output_boundary_marker = True
        memory_manager.on_message(ctx.owner_key, ctx.sid, "user", ctx.cache_query)
        memory_manager.on_message(ctx.owner_key, ctx.sid, "assistant", safe_text)

    def prepare_tool_event(payload: dict) -> dict | None:
        try:
            return _safe_sse_event(payload, ctx.verified_public_contacts)
        except PrivacyBoundaryUnavailable as exc:
            code = exc.code
        except Exception:
            code = "UNEXPECTED_PRIVACY_TOOL_EVENT_ERROR"
        logger.warning(
            "Privacy boundary unavailable for stream tool event",
            code=code,
        )
        ctx.settlement_blocked = True
        return None

    for round_num in range(max_rounds):
        try:
            _kw = {"model": ctx.stream_model, "ctx.messages": ctx.messages, "tools": TOOLS, "tool_choice": "auto", "timeout": LLM_TIMEOUT}
            if ctx.stream_temp is not None:
                _kw["temperature"] = ctx.stream_temp
            # CONC-001: chạy LLM-call ĐỒNG-BỘ trong thread để KHÔNG chặn event loop
            # (request /chat khác + /health vẫn xử lý được trong lúc chờ LLM).
            # Route qua safe_llm_call (circuit breaker) như non-stream — fail-fast khi
            # LLM sập thay vì chờ trọn LLM_TIMEOUT + ghi nhận vào llm_breaker chung.
            decision = await _await_chat_worker(
                _call_stream_decision,
                _kw,
                ctx.usage_accumulator,
                ctx.stream_model,
                ctx.messages,
            )
            if not decision["success"]:
                fallback = prepare_stream_fallback(decision["message"])
                fallback_ready = fallback is not None
                if fallback is None:
                    fallback = SAFE_PRIVACY_FAILURE_REPLY
                yield f"data: {json.dumps({'type': 'text', 'content': fallback}, ensure_ascii=False)}\n\n"
                if fallback_ready:
                    persist_stream_fallback(fallback)
                feedback_receipt = (
                    _issue_delivered_feedback_receipt(
                        ctx.owner_key,
                        ctx.cache_query,
                        fallback,
                        ctx.stream_model,
                        tools_used,
                    )
                    if fallback_ready
                    else None
                )
                yield f"data: {json.dumps({'type': 'done', 'tools': tools_used, 'suggestions': [], 'session_id': ctx.sid, 'feedback_receipt': feedback_receipt}, ensure_ascii=False)}\n\n"
                return
            response = decision["response"]
            msg = response.choices[0].message
        except Exception as exc:
            error_tracker.record_error("/chat/stream", str(exc), traceback.format_exc())
            fallback = prepare_stream_fallback(
                "Xin lỗi, đã xảy ra lỗi. Vui lòng thử lại."
            )
            fallback_ready = fallback is not None
            if fallback is None:
                fallback = SAFE_PRIVACY_FAILURE_REPLY
            yield f"data: {json.dumps({'type': 'text', 'content': fallback}, ensure_ascii=False)}\n\n"
            if fallback_ready:
                persist_stream_fallback(fallback)
            feedback_receipt = (
                _issue_delivered_feedback_receipt(
                    ctx.owner_key,
                    ctx.cache_query,
                    fallback,
                    ctx.stream_model,
                    tools_used,
                )
                if fallback_ready
                else None
            )
            yield f"data: {json.dumps({'type': 'done', 'tools': tools_used, 'suggestions': [], 'session_id': ctx.sid, 'feedback_receipt': feedback_receipt}, ensure_ascii=False)}\n\n"
            return

        if msg.tool_calls:
            ctx.messages.append(msg)
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    fn_args = {}  # EH-02: JSON args lỗi → {} thay vì crash stream
                tools_used.append(fn_name)

                # Tool-use Tracing: send start event with description
                tool_desc = _tool_description(fn_name, fn_args)
                tool_start_event = prepare_tool_event({
                    "type": "tool_start",
                    "name": fn_name,
                    "description": tool_desc,
                    "args": fn_args,
                })
                if tool_start_event is None:
                    yield f"data: {json.dumps({'type': 'error', 'content': SAFE_PRIVACY_FAILURE_REPLY}, ensure_ascii=False)}\n\n"
                    return
                yield f"data: {json.dumps(tool_start_event, ensure_ascii=False)}\n\n"

                t0 = time.time()
                result = await _await_chat_worker(
                    call_tool, fn_name, fn_args, ctx.usage_accumulator,
                )  # CONC-001: tool I/O off event loop
                result = _safe_tool_result(result, ctx.verified_public_contacts)
                duration_ms = round((time.time() - t0) * 1000)
                ctx.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

                # Tool-use Tracing: send done event with timing
                result_preview = result[:200] if len(result) > 200 else result
                tool_done_event = prepare_tool_event({
                    "type": "tool_done",
                    "name": fn_name,
                    "duration_ms": duration_ms,
                    "preview": result_preview,
                })
                if tool_done_event is None:
                    yield f"data: {json.dumps({'type': 'error', 'content': SAFE_PRIVACY_FAILURE_REPLY}, ensure_ascii=False)}\n\n"
                    return
                yield f"data: {json.dumps(tool_done_event, ensure_ascii=False)}\n\n"

                # Track entity discussions in memory
                if fn_name in ("entity_detail", "nearby_entities") and "entity_id" in fn_args:
                    memory_manager.on_entity_discussed(ctx.owner_key, ctx.sid, fn_args["entity_id"])

                if fn_name == "suggest_followups":
                    try:
                        data = json.loads(result)
                        suggestions = data.get("suggestions", [])
                    except Exception:
                        logger.debug("Failed to parse suggest_followups result", exc_info=True)
        else:
            # CONC-001: SDK streaming là iterator ĐỒNG-BỘ — lặp nó trong async gen sẽ
            # chặn event loop từng token. Chạy create+iterate trong THREAD, đẩy từng
            # chunk qua asyncio.Queue (thread-safe) để consumer async yield không chặn.
            loop = asyncio.get_running_loop()
            chunk_q: asyncio.Queue = asyncio.Queue()
            _cancelled = threading.Event()
            stream_returned = False

            def _produce_stream():
                nonlocal stream_returned
                try:
                    stream = get_client().chat.completions.create(
                        model=ctx.stream_model, messages=ctx.messages, stream=True,
                        stream_options={"include_usage": True},
                        timeout=LLM_TIMEOUT,
                    )
                    stream_returned = True
                    for chunk in stream:
                        if _cancelled.is_set():
                            break
                        if getattr(chunk, "usage", None) is not None:
                            loop.call_soon_threadsafe(chunk_q.put_nowait, chunk)
                        if not getattr(chunk, "choices", None):
                            continue
                        delta = chunk.choices[0].delta
                        if delta.content:
                            loop.call_soon_threadsafe(chunk_q.put_nowait, delta.content)
                except Exception as exc:
                    if not _cancelled.is_set():
                        loop.call_soon_threadsafe(chunk_q.put_nowait, exc)
                finally:
                    loop.call_soon_threadsafe(chunk_q.put_nowait, None)

            producer = asyncio.create_task(asyncio.to_thread(_produce_stream))
            _chunks: list[str] = []
            terminal_chunk = None
            redactor = StreamingPIIRedactor(
                verified_public_contacts=tuple(ctx.verified_public_contacts),
            )

            async def _stream_text_chunks():
                nonlocal terminal_chunk
                while True:
                    item = await chunk_q.get()
                    if item is None:
                        return
                    if isinstance(item, Exception):
                        raise item
                    if getattr(item, "usage", None) is not None:
                        terminal_chunk = item
                        continue
                    yield item

            try:
                async for safe_chunk in _safe_stream_text_events(
                    _stream_text_chunks(),
                    redactor,
                ):
                    _chunks.append(safe_chunk)
                    yield f"data: {json.dumps({'type': 'text', 'content': safe_chunk}, ensure_ascii=False)}\n\n"
            except (asyncio.CancelledError, GeneratorExit):
                _cancelled.set()
                redactor.abort()
                return
            except PrivacyBoundaryUnavailable as exc:
                logger.warning(
                    "Privacy boundary unavailable for stream redaction",
                    code=exc.code,
                )
                ctx.settlement_blocked = True
                redactor.abort()
                yield f"data: {json.dumps({'type': 'error', 'content': SAFE_PRIVACY_FAILURE_REPLY}, ensure_ascii=False)}\n\n"
                return
            except Exception:
                redactor.abort()
                yield f"data: {json.dumps({'type': 'error', 'content': 'Xin lỗi, không thể hoàn tất câu trả lời. Vui lòng thử lại.'}, ensure_ascii=False)}\n\n"
                return
            finally:
                _cancelled.set()
                await producer
                if stream_returned:
                    ctx.usage_accumulator.add_response(
                        terminal_chunk,
                        model=ctx.stream_model,
                        messages=ctx.messages,
                        completion_text="".join(_chunks),
                    )
            full_text = "".join(_chunks)

            try:
                safe_reply = _safe_delivered_reply(
                    full_text,
                    ctx.message,
                    (knowledge._entities or {}) if hasattr(knowledge, "_entities") else {},
                    ctx.verified_public_contacts,
                )
            except PrivacyBoundaryUnavailable as exc:
                logger.warning(
                    "Privacy boundary unavailable for stream output",
                    code=exc.code,
                )
                ctx.settlement_blocked = True
                yield f"data: {json.dumps({'type': 'text', 'content': SAFE_PRIVACY_FAILURE_REPLY}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'tools': [], 'suggestions': [], 'session_id': ctx.sid}, ensure_ascii=False)}\n\n"
                return
            except Exception:
                logger.warning(
                    "Privacy boundary unavailable for stream output",
                    code="UNEXPECTED_PRIVACY_OUTPUT_ERROR",
                )
                ctx.settlement_blocked = True
                yield f"data: {json.dumps({'type': 'text', 'content': SAFE_PRIVACY_FAILURE_REPLY}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'tools': [], 'suggestions': [], 'session_id': ctx.sid}, ensure_ascii=False)}\n\n"
                return

            full_text = safe_reply.text
            tools_used = redact_payload(tools_used, source="provider_output")
            suggestions = redact_payload(suggestions, source="provider_output")
            _privacy_output_boundary_marker = True
            memory_manager.on_message(ctx.owner_key, ctx.sid, "user", ctx.cache_query)
            memory_manager.on_message(ctx.owner_key, ctx.sid, "assistant", full_text)

            # Memory graph: record entity interactions
            if HAS_MEMORY_GRAPH:
                try:
                    memory_graph.on_chat_complete(ctx.owner_key, ctx.message, full_text, [])
                except Exception:
                    logger.debug("Memory graph record failed (stream)", exc_info=True)

            # LLM memory extraction
            try:
                memory_manager.on_chat_complete(ctx.owner_key, ctx.sid, ctx.message, full_text)
            except Exception:
                logger.debug("LLM memory extraction failed (stream)", exc_info=True)

            # Reflexion: evaluate quality
            evaluation = reflexion_engine.evaluate_answer(ctx.message, full_text, tools_used)
            quality_tracker.record(ctx.message, evaluation["score"], tools_used)
            if evaluation["score"] < 5:
                reflexion_engine.reflect_on_failure(ctx.message, full_text, evaluation)
            elif evaluation["score"] >= 8:
                memory_manager.on_good_answer(
                    ctx.message[:100], tools_used,
                    f"Score {evaluation['score']}",
                    reflexion_engine._categorize_query(ctx.message),
                )
            if HAS_EXPERIENCE:
                try:
                    experience_memory.record(
                        ctx.message,
                        tools_used,
                        evaluation["score"],
                        full_text,
                        owner_key=ctx.owner_key,
                    )
                except Exception:
                    logger.debug("Experience memory record failed (stream)", exc_info=True)
            if HAS_FEWSHOT:
                try:
                    prompt_compiler.record_demo(
                        ctx.message,
                        full_text,
                        evaluation["score"],
                        owner_key=ctx.owner_key,
                    )
                except Exception:
                    logger.debug("Few-shot demo record failed (stream)", exc_info=True)

            # ── Self optimizer: record outcome ──
            if HAS_OPTIMIZER:
                try:
                    est_tok = token_counter.estimate_tokens(full_text) if HAS_COST_TRACKER else len(full_text) // 3
                    record_outcome(
                        ctx.sid,
                        ctx.message,
                        "stream",
                        tools_used,
                        evaluation["score"],
                        0,
                        est_tok,
                        owner_key=ctx.owner_key,
                    )
                except Exception:
                    logger.debug("Self-optimizer outcome failed (stream)", exc_info=True)

            # ── LLM Judge: quality evaluation ──
            if HAS_LLM_JUDGE and LLM_JUDGE_ENABLED and evaluation["score"] >= 3:
                try:
                    judge(ctx.message, full_text)
                except Exception:
                    logger.debug("LLM Judge failed (stream)", exc_info=True)

            # A/B testing: record outcome
            if HAS_AB_TESTING and ctx.sid:
                try:
                    ab_manager.record_outcome(
                        "prompt_style",
                        ctx.sid,
                        evaluation["score"],
                        owner_key=ctx.owner_key,
                    )
                except Exception:
                    logger.debug("A/B outcome record failed (stream)", exc_info=True)

            # Metrics tracking
            if HAS_METRICS:
                track_chat_request("ok", 0)  # duration not tracked in stream

            # Track & cache
            analytics.track_query(
                ctx.message,
                tools_used,
                full_text,
                ctx.sid,
                owner_key=ctx.owner_key,
            )
            if ctx.cache_eligible and len(full_text) > 30 and evaluation["score"] >= 5:
                cache_data = {"reply": full_text, "tool_calls": tools_used, "suggestions": suggestions}
                # Lưu theo ctx.cache_query (khoá lúc cache.get) — không phải bản đã autocorrect,
                # nếu không lần sau cùng câu gốc sẽ luôn MISS (đã sửa: stream cache key mismatch).
                owner_write_gate.assert_writable(ctx.owner_key)
                cache.put(ctx.cache_query, cache_data, owner_key=ctx.owner_key)
                # ── Semantic cache: store ──
                if HAS_SEMANTIC_CACHE:
                    try:
                        semantic_put(
                            ctx.cache_query,
                            cache_data,
                            owner_key=ctx.owner_key,
                            dedup_key=ctx.semantic_dedup_key,
                        )
                    except Exception:
                        logger.debug("Semantic cache put failed", exc_info=True)

            # Send quality score for UI feedback prompt
            feedback_receipt = _issue_delivered_feedback_receipt(
                ctx.owner_key,
                ctx.cache_query,
                full_text,
                ctx.stream_model,
                tools_used,
            )
            yield f"data: {json.dumps({'type': 'done', 'tools': tools_used, 'suggestions': suggestions, 'session_id': ctx.sid, 'quality': evaluation['score'], 'feedback_receipt': feedback_receipt}, ensure_ascii=False)}\n\n"
            return

    # ── Round-exhaustion: every round called tools without a final answer.
    # Force ONE synthesis turn (no tools) so the user gets an answer built
    # from gathered evidence instead of an empty response.
    delivered_synth = ""
    try:
        ctx.messages.append({
            "role": "system",
            "content": ("[Hệ thống]: Đã đạt giới hạn số vòng. Hãy tổng hợp câu trả lời "
                        "tốt nhất TỪ thông tin đã thu thập, KHÔNG gọi thêm tool, "
                        "trả lời trực tiếp bằng tiếng Việt."),
        })
        synth_q: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        _synth_cancelled = threading.Event()
        synth_stream_returned = False
        def _synth_produce():
            nonlocal synth_stream_returned
            try:
                resp = get_client().chat.completions.create(
                    model=ctx.stream_model,
                    messages=ctx.messages,
                    stream=True,
                    stream_options={"include_usage": True},
                    timeout=LLM_TIMEOUT,
                )
                synth_stream_returned = True
                for chunk in resp:
                    if _synth_cancelled.is_set():
                        break  # consumer đã thoát (client disconnect) → dừng, không leak thread
                    if getattr(chunk, "usage", None) is not None:
                        loop.call_soon_threadsafe(synth_q.put_nowait, chunk)
                    if not getattr(chunk, "choices", None):
                        continue
                    delta = chunk.choices[0].delta
                    if delta.content:
                        loop.call_soon_threadsafe(synth_q.put_nowait, delta.content)
            except Exception as exc:
                if not _synth_cancelled.is_set():
                    loop.call_soon_threadsafe(synth_q.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(synth_q.put_nowait, None)
        synth_producer = asyncio.create_task(asyncio.to_thread(_synth_produce))
        synth_chunks: list[str] = []
        synth_terminal_chunk = None
        synth_redactor = StreamingPIIRedactor(
            verified_public_contacts=tuple(ctx.verified_public_contacts),
        )

        async def _synth_text_chunks():
            nonlocal synth_terminal_chunk
            while True:
                item = await synth_q.get()
                if item is None:
                    return
                if isinstance(item, Exception):
                    raise item
                if getattr(item, "usage", None) is not None:
                    synth_terminal_chunk = item
                    continue
                yield item

        try:
            async for safe_chunk in _safe_stream_text_events(
                _synth_text_chunks(),
                synth_redactor,
            ):
                synth_chunks.append(safe_chunk)
                yield f"data: {json.dumps({'type': 'text', 'content': safe_chunk}, ensure_ascii=False)}\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            synth_redactor.abort()
            raise
        except PrivacyBoundaryUnavailable as exc:
            logger.warning(
                "Privacy boundary unavailable for stream synthesis redaction",
                code=exc.code,
            )
            ctx.settlement_blocked = True
            synth_redactor.abort()
            yield f"data: {json.dumps({'type': 'error', 'content': SAFE_PRIVACY_FAILURE_REPLY}, ensure_ascii=False)}\n\n"
            return
        finally:
            _synth_cancelled.set()  # generator đóng (disconnect/hoàn tất) → báo thread produce dừng
            await synth_producer
            if synth_stream_returned:
                ctx.usage_accumulator.add_response(
                    synth_terminal_chunk,
                    model=ctx.stream_model,
                    messages=ctx.messages,
                    completion_text="".join(synth_chunks),
                )
        synth_text = "".join(synth_chunks)
        if synth_text:
            try:
                safe_synth = _safe_delivered_reply(
                    synth_text,
                    ctx.message,
                    (knowledge._entities or {}) if hasattr(knowledge, "_entities") else {},
                    ctx.verified_public_contacts,
                )
            except PrivacyBoundaryUnavailable as exc:
                logger.warning(
                    "Privacy boundary unavailable for stream synthesis",
                    code=exc.code,
                )
                ctx.settlement_blocked = True
                return
            except Exception:
                logger.warning(
                    "Privacy boundary unavailable for stream synthesis",
                    code="UNEXPECTED_PRIVACY_OUTPUT_ERROR",
                )
                ctx.settlement_blocked = True
                return
            synth_text = safe_synth.text
            delivered_synth = synth_text
            _privacy_output_boundary_marker = True
            memory_manager.on_message(ctx.owner_key, ctx.sid, "user", ctx.cache_query)
            memory_manager.on_message(ctx.owner_key, ctx.sid, "assistant", synth_text)
            analytics.track_query(
                ctx.message,
                tools_used,
                synth_text,
                ctx.sid,
                owner_key=ctx.owner_key,
            )
    except Exception:
        logger.debug("Stream synthesis fallback failed", exc_info=True)

    feedback_receipt = (
        _issue_delivered_feedback_receipt(
            ctx.owner_key,
            ctx.cache_query,
            delivered_synth,
            ctx.stream_model,
            tools_used,
        )
        if delivered_synth
        else None
    )
    yield f"data: {json.dumps({'type': 'done', 'tools': tools_used, 'suggestions': suggestions, 'session_id': ctx.sid, 'feedback_receipt': feedback_receipt}, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
@_finalize_semantic_route_lease
async def chat_stream(req: ChatRequest, request: Request):
    owner_context = await resolve_chat_owner(request)
    owner_key = owner_context.owner_key
    session = None
    requested_session_id = req.session_id or ""
    sid = requested_session_id
    def _stream_response(generator, semantic_lease=None):
        stream_response = _SemanticLeaseStreamingResponse(
            generator,
            media_type="text/event-stream",
            semantic_lease=semantic_lease,
        )
        set_chat_owner_cookie(stream_response, owner_context)
        return stream_response

    # Rate limiting
    client_ip = get_client_ip(request)
    allowed, rate_info = stream_limiter.is_allowed(client_ip)
    if not allowed:
        logger.warning("Rate limited", ip=client_ip, endpoint="/chat/stream")
        limited = _error_response(
            429,
            "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
            request,
            retry_after=rate_info["retry_after"],
        )
        limited.headers["Retry-After"] = str(rate_info["retry_after"])
        set_chat_owner_cookie(limited, owner_context)
        return limited

    try:
        if requested_session_id:
            session = memory_manager.require_session(owner_key, requested_session_id)
    except UnknownConversation:
        not_found = _error_response(404, "Không tìm thấy cuộc trò chuyện.", request)
        set_chat_owner_cookie(not_found, owner_context)
        return not_found

    def _safe_block_stream(msg: str):
        async def _gen():
            yield f"data: {json.dumps({'type': 'text', 'content': msg}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'tools': [], 'suggestions': [], 'session_id': sid}, ensure_ascii=False)}\n\n"
        return _gen

    try:
        safe_input = prepare_chat_input(
            req.message,
            [item.model_dump() for item in req.history],
            owner_key=owner_key,
        )
    except PrivacyBoundaryBlocked as exc:
        logger.warning(
            "Privacy boundary blocked stream input",
            code=exc.code,
            session_id=sid,
        )
        gen = _safe_block_stream(
            "Xin lỗi, tin nhắn này không thể xử lý vì lý do an toàn. Vui lòng diễn đạt lại."
        )
        return _stream_response(gen())
    except PrivacyBoundaryUnavailable as exc:
        logger.warning(
            "Privacy boundary unavailable for stream",
            code=exc.code,
            session_id=sid,
        )
        gen = _safe_block_stream(
            "Xin lỗi, hệ thống đang bận kiểm tra an toàn. Vui lòng thử lại sau ít phút."
        )
        return _stream_response(gen())
    except Exception:
        logger.warning(
            "Privacy boundary unavailable for stream",
            code="UNEXPECTED_PRIVACY_BOUNDARY_ERROR",
            session_id=sid,
        )
        gen = _safe_block_stream(
            "Xin lỗi, hệ thống đang bận kiểm tra an toàn. Vui lòng thử lại sau ít phút."
        )
        return _stream_response(gen())

    _privacy_input_boundary_marker = True
    message = safe_input.message
    history = [
        {"role": item.role, "content": item.content}
        for item in safe_input.history
    ]

    if not message:
        async def empty_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Tin nhắn trống.'}, ensure_ascii=False)}\n\n"
        return _stream_response(empty_stream())

    if session is None:
        session = memory_manager.create_session(owner_key)
        sid = session.session_id
    _hydrate_empty_session(owner_key, session, history)
    cache_eligible = not history and not session.get_context_messages()

    # The cache/dedup lifecycle must use one stable pre-autocorrect query key.
    cache_query = message

    async def _cached_stream(safe_cached: dict, hit_name: str):
        reply = safe_cached.get("reply", "")
        words = reply.split(" ")
        emitted = []
        try:
            for index in range(0, len(words), 3):
                chunk = " ".join(words[index:index + 3])
                if index > 0:
                    chunk = " " + chunk
                emitted.append(chunk)
                yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"

            delivered = "".join(emitted)
            safe_cached["reply"] = delivered
            _privacy_output_boundary_marker = True
            _record_cached_exchange(owner_key, sid, cache_query, safe_cached)
            analytics.track_query(
                message,
                [hit_name],
                delivered,
                sid,
                owner_key=owner_key,
            )
            feedback_receipt = _issue_delivered_feedback_receipt(
                owner_key,
                cache_query,
                delivered,
                "cache",
                safe_cached.get("tool_calls", []),
            )
            yield f"data: {json.dumps({'type': 'done', 'tools': [hit_name], 'suggestions': safe_cached.get('suggestions', []), 'session_id': sid, 'feedback_receipt': feedback_receipt}, ensure_ascii=False)}\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            return
        except Exception:
            logger.debug("Legacy cache stream delivery failed", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': SAFE_PRIVACY_FAILURE_REPLY}, ensure_ascii=False)}\n\n"

    # ── Semantic cache: check before regular cache ──
    semantic_dedup_key = None
    if cache_eligible and HAS_SEMANTIC_CACHE:
        try:
            sem_cached = await semantic_get_async(cache_query, owner_key=owner_key)
            semantic_dedup_key = semantic_take_dedup_lease(
                cache_query,
                owner_key=owner_key,
            )
            _hold_semantic_route_lease(
                cache_query,
                owner_key,
                semantic_dedup_key,
            )
            if sem_cached:
                try:
                    safe_cached = _safe_cached_payload(sem_cached)
                except PrivacyBoundaryUnavailable as exc:
                    logger.warning("Legacy cache privacy boundary unavailable", code=exc.code)
                    return _stream_response(_safe_block_stream(SAFE_PRIVACY_FAILURE_REPLY)())
                return _stream_response(_cached_stream(safe_cached, "semantic_cache_hit"))
        except Exception:
            logger.debug("Semantic cache retrieval failed (stream)", exc_info=True)

    # Check cache for history-less requests
    if cache_eligible:
        cached = cache.get(cache_query, owner_key=owner_key)
        if cached:
            try:
                safe_cached = _safe_cached_payload(cached)
            except PrivacyBoundaryUnavailable as exc:
                logger.warning("Legacy cache privacy boundary unavailable", code=exc.code)
                return _stream_response(_safe_block_stream(SAFE_PRIVACY_FAILURE_REPLY)())
            if HAS_SEMANTIC_CACHE:
                _privacy_output_boundary_marker = True
                try:
                    semantic_put(
                        cache_query,
                        safe_cached,
                        owner_key=owner_key,
                        dedup_key=semantic_dedup_key,
                    )
                except Exception:
                    logger.debug(
                        "Semantic cache exact-hit publication failed (stream)",
                        exc_info=True,
                    )
            return _stream_response(_cached_stream(safe_cached, "cache_hit"))

    usage_accumulator = UsageAccumulator()
    verified_public_contacts: set[str] = set()

    # Autocorrect
    if HAS_AUTOCORRECT:
        ac = autocorrect(message)
        if ac.get("was_corrected"):
            message = ac["corrected"]

    # Build messages with full 2026 architecture context
    messages, _build_info = _build_messages(message, history, sid, owner_key)

    # ── Parity with /chat: apply dynamic-agent addon + active prompt variant ──
    # (Previously the streaming path missed these, giving lower quality than /chat.)
    if messages and messages[0].get("role") == "system" and isinstance(messages[0].get("content"), str):
        _sys = messages[0]["content"]
        if HAS_DYNAMIC_AGENTS:
            try:
                _dyn = check_dynamic_route(message)
                if _dyn and _dyn.get("system_prompt_addon"):
                    _sys += "\n\n" + _dyn["system_prompt_addon"]
            except Exception:
                logger.debug("Dynamic agent routing failed (stream)", exc_info=True)
        if HAS_OPTIMIZER:
            try:
                _v = prompt_optimizer.get_current_variant().get("prompt_addon", "")
                if _v:
                    _sys += "\n\n" + _v
            except Exception:
                logger.debug("Self-optimizer variant failed (stream)", exc_info=True)
        messages[0]["content"] = _sys

    # ── Smart model routing for stream path ──
    _stream_model = get_model()
    try:
        from orchestrator import QueryRouter as _QR2, _CATEGORY_AGENTS
        _stream_cat = _QR2.classify(message)
        _stream_agent = _CATEGORY_AGENTS.get(_stream_cat)
        if _stream_agent and getattr(_stream_agent, "use_mini", False):
            _stream_model = get_model_mini()
            logger.info("Stream model routing: MINI", category=_stream_cat.value)
    except Exception:
        logger.debug("Stream model routing failed", exc_info=True)

    # ── Tuned params (self_optimizer) for the streaming loop ──
    _stream_temp = None
    _stream_rounds = 4
    if HAS_OPTIMIZER:
        try:
            from orchestrator import QueryRouter as _QR
            _cat = _QR.classify(message).value
            _p = parameter_tuner.get_optimal_params(_cat)
            _stream_rounds = int(_p.get("max_rounds", 4))
            _stream_temp = _p.get("temperature")
        except Exception:
            logger.debug("Stream tuned params failed", exc_info=True)

    ctx = _StreamContext(
        owner_key=owner_key,
        message=message,
        sid=sid,
        messages=messages,
        cache_query=cache_query,
        cache_eligible=cache_eligible,
        verified_public_contacts=verified_public_contacts,
        usage_accumulator=usage_accumulator,
        semantic_dedup_key=semantic_dedup_key,
        stream_model=_stream_model,
        stream_temp=_stream_temp,
        stream_rounds=_stream_rounds,
    )

    async def event_stream():
        body = _event_stream_body(ctx)
        try:
            async for event in body:
                yield event
        finally:
            try:
                await body.aclose()
            finally:
                if not ctx.settlement_blocked:
                    try:
                        usage_accumulator.settle(
                            owner_key=owner_key,
                            query=message[:200],
                            agent_name="stream",
                            guardrail_budget=guardrail_budget if HAS_GUARDRAILS else None,
                            cost_attribution=cost_attribution if HAS_COST_TRACKER else None,
                        )
                    except Exception:
                        logger.debug("Cost tracking failed (stream)", exc_info=True)

    semantic_lease = None
    if semantic_dedup_key is not None:
        semantic_lease = (cache_query, owner_key, semantic_dedup_key)
    response = _stream_response(event_stream(), semantic_lease=semantic_lease)
    _transfer_semantic_route_lease()
    return response


# ── /feedback — mặt tiêu-thụ receipt (server.py về nhà 2026-08-29, lát 9).
#    Receipt do issue_feedback_receipt của CHÍNH gói này phát; identity =
#    resolve_chat_owner/set_chat_owner_cookie y hệt /chat. ──

class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: str
    rating: Literal[0, 1]

    @field_validator("rating", mode="before")
    @classmethod
    def reject_boolean_rating(cls, value):
        if type(value) is not int:
            raise ValueError("rating must be integer 0 or 1")
        return value


def _feedback_response(
    status_code: int,
    content: dict,
    *,
    owner_context=None,
    retry_after: int | None = None,
) -> JSONResponse:
    result = JSONResponse(status_code=status_code, content=content)
    if retry_after is not None:
        result.headers["Retry-After"] = str(max(1, retry_after))
    if owner_context is not None:
        set_chat_owner_cookie(result, owner_context)
    return result


def _feedback_owner_kind(owner_key: str) -> str:
    if owner_key.startswith("user:"):
        return "authenticated"
    if owner_key.startswith("anon:"):
        return "anonymous"
    return "unknown"


def _track_feedback_transport(
    reason: str,
    owner_kind: str,
    rating: int | None = None,
) -> None:
    if HAS_METRICS:
        track_feedback_attempt(
            reason=reason,
            owner_kind=owner_kind,
            rating=rating,
        )


@router.post("/feedback")
async def user_feedback(request: Request):
    """Consume one owner-bound receipt into deidentified aggregate telemetry."""
    client_ip = get_client_ip(request)
    allowed, rate_info = feedback_ip_limiter.is_allowed(client_ip)
    if not allowed:
        _track_feedback_transport("ip_limit", "unknown")
        return _feedback_response(
            429,
            {"detail": "Too many feedback requests"},
            retry_after=rate_info["retry_after"],
        )

    owner_context = await resolve_chat_owner(request)
    resolved_owner_kind = _feedback_owner_kind(owner_context.owner_key)
    allowed, rate_info = feedback_owner_limiter.is_allowed(owner_context.owner_key)
    if not allowed:
        _track_feedback_transport("owner_limit", resolved_owner_kind)
        return _feedback_response(
            429,
            {"detail": "Too many feedback requests"},
            owner_context=owner_context,
            retry_after=rate_info["retry_after"],
        )

    try:
        payload = await request.json()
        feedback = FeedbackRequest.model_validate(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, TypeError, ValueError):
        _track_feedback_transport("invalid_request", resolved_owner_kind)
        return _feedback_response(
            422,
            {"detail": "Invalid feedback request"},
            owner_context=owner_context,
        )

    if re.fullmatch(r"[A-Za-z0-9_-]{43}", feedback.receipt) is None:
        _track_feedback_transport("invalid_receipt", resolved_owner_kind, feedback.rating)
        return _feedback_response(
            503,
            {"detail": "Feedback unavailable"},
            owner_context=owner_context,
        )

    try:
        consumed = consume_feedback_receipt(
            feedback.receipt,
            owner_context.owner_key,
            feedback.rating,
        )
    except FeedbackUnavailable:
        _track_feedback_transport(
            "receipt_unavailable",
            resolved_owner_kind,
            feedback.rating,
        )
        return _feedback_response(
            503,
            {"detail": "Feedback unavailable"},
            owner_context=owner_context,
        )
    except FeedbackRejected:
        _track_feedback_transport(
            "receipt_rejected",
            resolved_owner_kind,
            feedback.rating,
        )
        return _feedback_response(
            503,
            {"detail": "Feedback unavailable"},
            owner_context=owner_context,
        )

    _track_feedback_transport(
        "idempotent" if consumed.idempotent else "accepted",
        resolved_owner_kind,
        feedback.rating,
    )
    return _feedback_response(200, {"success": True}, owner_context=owner_context)


# ── /welcome — identity + bộ nhớ chat (server.py về nhà 2026-08-29, lát 9) ──

@router.get("/welcome")
async def welcome_message(request: Request, response: Response):
    """Welcome message cá nhân hóa."""
    owner_context = await resolve_chat_owner(request)
    set_chat_owner_cookie(response, owner_context)
    preferences = None
    profile = memory_manager.cold.find_profile(owner_context.owner_key)
    if profile is not None and profile.conversation_count > 0:
        preferences = {
            "interests": profile.interests,
            "preferred_areas": profile.preferred_areas,
        }
    return generate_welcome_message(preferences)
