"""
vinhlong360 — Knowledge Agent Server (v3 — Production).

FastAPI server cung cấp:
  POST /chat          — chat endpoint (JSON) + rate limiting
  GET  /chat/stream   — SSE streaming chat + rate limiting
  POST /reload        — hot-reload data + cache invalidation + data sync
  GET  /health        — health check + cache stats + response times
  GET  /              — trang chat
  /admin/*            — Admin API (CRUD, review, analytics, trigger-learn)
  /analytics/*        — Analytics dashboard data
  /system/*           — System monitoring (logs, rate limits, errors)

Chạy:
  pip install -r requirements.txt
  python agent/server.py
"""

import json
import os
import re
import sys
import time
import traceback
import uuid
import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


BUILD_SEARCH_INDEXES = _env_bool("BUILD_SEARCH_INDEXES", True)
BACKGROUND_INDEX_BUILD = _env_bool("BACKGROUND_INDEX_BUILD", True)
# GĐ4.4: LLM Judge tốn nguyên 1 lượt LLM/chat cho telemetry -> mặc định TẮT (bật khi cần đo).
LLM_JUDGE_ENABLED = _env_bool("LLM_JUDGE_ENABLED", False)

import analytics
import cache
import knowledge
from admin import router as admin_router
from auth import router as auth_router
from notifications import router as community_router
from public_api import router as public_router
import public_api as _public_api
from saved import router as saved_router
from plans import router as plans_router, public_router as plans_public_router
from visits import router as visits_router
from achievements import router as achievements_router
from seo import router as seo_router
from social import router as social_router
from tools import TOOLS, SYSTEM_PROMPT
from middleware import (
    logger, chat_limiter, stream_limiter, report_limiter,
    response_tracker, error_tracker, generate_request_id, get_client_ip,
)
from itinerary_gen import generate_itinerary
from scheduler import start_scheduler, stop_scheduler, scheduler_status, sync_data_json_to_js
from memory import memory_manager
from reflexion import reflexion_engine, quality_tracker
from proactive import get_proactive_context, generate_welcome_message
from agentic_rag import build_rag_context

try:
    from vector_search import embedding_store, hybrid_search  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_VECTOR = True
    logger.info("Vector search enabled")
except ImportError:
    HAS_VECTOR = False
    logger.info("Vector search disabled (optional dependency)")

try:
    from realtime import get_realtime_context, get_weather, get_all_weather, get_upcoming_events
    HAS_REALTIME = True
except ImportError:
    HAS_REALTIME = False
    logger.info("Realtime data disabled (optional dependency)")

try:
    from circuit_breaker import safe_llm_call, all_breaker_stats, llm_breaker, web_search_breaker, weather_breaker  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_CIRCUIT_BREAKER = True
except ImportError:
    HAS_CIRCUIT_BREAKER = False

try:
    from parallel_tools import ParallelToolExecutor, can_parallelize  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_PARALLEL = True
except ImportError:
    HAS_PARALLEL = False

try:
    from autocorrect import autocorrect, load_entity_names
    HAS_AUTOCORRECT = True
except ImportError:
    HAS_AUTOCORRECT = False

try:
    from recommender import recommend
    HAS_RECOMMENDER = True
except ImportError:
    HAS_RECOMMENDER = False

try:
    from freshness import check_freshness, freshness_report, auto_refresh_candidates
    HAS_FRESHNESS = True
except ImportError:
    HAS_FRESHNESS = False

try:
    from image_recognition import process_upload, recognize_image
    HAS_IMAGE_RECOGNITION = True
except ImportError:
    HAS_IMAGE_RECOGNITION = False

try:
    from metrics import generate_metrics, track_chat_request, track_tool_call, track_cache, track_feedback, track_error, set_gauge, track_http_request  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_METRICS = True
except ImportError:
    HAS_METRICS = False

try:
    from ab_testing import ab_manager
    HAS_AB_TESTING = True
except ImportError:
    HAS_AB_TESTING = False

try:
    from prompt_cache import prompt_cache, estimate_tokens, compress_history  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_PROMPT_CACHE = True
except ImportError:
    HAS_PROMPT_CACHE = False

try:
    from orchestrator import Orchestrator, QueryRouter, handoff_log  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_ORCHESTRATOR = True
except ImportError:
    HAS_ORCHESTRATOR = False

try:
    from memory_graph import memory_graph
    HAS_MEMORY_GRAPH = True
except ImportError:
    HAS_MEMORY_GRAPH = False

try:
    from tracing import tracer, trace_chat_request, trace_tool_call, trace_llm_call, trace_rag_retrieval, get_trace_summary, export_traces_json  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_TRACING = True
except ImportError:
    HAS_TRACING = False

try:
    from contextual_retrieval import contextual, bm25, enhanced_hybrid_search
    HAS_CONTEXTUAL = True
except ImportError:
    HAS_CONTEXTUAL = False

try:
    import kb_context
    HAS_KB_CONTEXT = True
except ImportError:
    HAS_KB_CONTEXT = False

try:
    import experience_memory
    HAS_EXPERIENCE = True
except ImportError:
    HAS_EXPERIENCE = False

try:
    import prompt_compiler
    HAS_FEWSHOT = True
except ImportError:
    HAS_FEWSHOT = False

try:
    from checkpoints import checkpoint_manager, confirmation_manager, needs_confirmation, format_confirmation_prompt  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_CHECKPOINTS = True
except ImportError:
    HAS_CHECKPOINTS = False

# ── Level 6 modules ──

try:
    from guardrails import injection_detector, pii_masker, output_validator, budget_manager as guardrail_budget, check_input, check_output  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_GUARDRAILS = True
except ImportError:
    HAS_GUARDRAILS = False

try:
    from cost_tracker import token_counter, cost_attribution, budget_manager as cost_budget, track_llm_call, get_cost_report  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_COST_TRACKER = True
except ImportError:
    HAS_COST_TRACKER = False

try:
    from eval_framework import eval_runner, BENCHMARK_SUITE, run_benchmark, get_latest_report, get_report_history  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_EVAL = True
except ImportError:
    HAS_EVAL = False

try:
    from self_optimizer import performance_collector, prompt_optimizer, parameter_tuner, tool_weight_optimizer, record_outcome, get_optimization_report  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_OPTIMIZER = True
except ImportError:
    HAS_OPTIMIZER = False

try:
    from semantic_cache import multi_tier_cache, semantic_get, semantic_put, cache_stats as semantic_cache_stats, cache_warmer  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_SEMANTIC_CACHE = True
except ImportError:
    HAS_SEMANTIC_CACHE = False

# ── Level 7 modules ──

try:
    from llm_judge import llm_judge, judge_analytics, judge, get_judge_report  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_LLM_JUDGE = True
except ImportError:
    HAS_LLM_JUDGE = False

try:
    from dynamic_agents import agent_factory, dynamic_router, pattern_analyzer, agent_evolution, check_dynamic_route, get_agent_report  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_DYNAMIC_AGENTS = True
except ImportError:
    HAS_DYNAMIC_AGENTS = False

# GĐ6/11: federation, a2a_protocol, advanced_graph, agent_relay, streaming_tools,
# multimodal_engine, knowledge_evolution đã bị XOÁ (dead-weight) — import/flag/endpoint
# tương ứng đã gỡ. KHÔNG thêm lại trừ khi tái triển khai module thật.

# ── Feature flag registry ──
from feature_flags import features
for _name, _val in {
    "vector": HAS_VECTOR, "realtime": HAS_REALTIME, "circuit_breaker": HAS_CIRCUIT_BREAKER,
    "parallel": HAS_PARALLEL, "autocorrect": HAS_AUTOCORRECT, "recommender": HAS_RECOMMENDER,
    "freshness": HAS_FRESHNESS, "image_recognition": HAS_IMAGE_RECOGNITION,
    "metrics": HAS_METRICS, "ab_testing": HAS_AB_TESTING, "prompt_cache": HAS_PROMPT_CACHE,
    "orchestrator": HAS_ORCHESTRATOR, "memory_graph": HAS_MEMORY_GRAPH, "tracing": HAS_TRACING,
    "contextual": HAS_CONTEXTUAL, "kb_context": HAS_KB_CONTEXT, "experience": HAS_EXPERIENCE,
    "fewshot": HAS_FEWSHOT, "checkpoints": HAS_CHECKPOINTS, "guardrails": HAS_GUARDRAILS,
    "cost_tracker": HAS_COST_TRACKER, "eval": HAS_EVAL, "optimizer": HAS_OPTIMIZER,
    "semantic_cache": HAS_SEMANTIC_CACHE, "llm_judge": HAS_LLM_JUDGE,
    "dynamic_agents": HAS_DYNAMIC_AGENTS,
}.items():
    features.register(_name, _val)

# ── OpenAI client (runtime-configurable via admin) ──

from llm_config import get_client, get_model, get_model_mini

# ── Web search (DuckDuckGo) ──

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


def generate_followups(context: str) -> list[str]:
    try:
        response = get_client().chat.completions.create(
            model=get_model_mini(),
            messages=[{"role": "user", "content": f"""Dựa vào ngữ cảnh sau, gợi ý 3 câu hỏi tiếp theo ngắn gọn (< 40 ký tự) mà du khách có thể muốn hỏi.

Ngữ cảnh: {context}

Trả về JSON array gồm 3 string. Chỉ trả JSON, không text khác."""}],
            temperature=0.7,
            timeout=LLM_TIMEOUT,
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return json.loads(content)[:3]
    except Exception:
        logger.debug("Follow-up generation failed", exc_info=True)
        return []


# ── Tool dispatcher ──

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


def call_tool(name: str, args: dict) -> str:
    # P1: cô lập lỗi tool (KeyError do LLM thiếu tham số, lỗi tool…) → trả lỗi có cấu trúc
    # thay vì propagate (trước đây args["x"] thiếu field → 500 ở serial path).
    try:
        return _call_tool_impl(name, args or {})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"call_tool '{name}' lỗi: {e}")
        return json.dumps({"error": "Không thực hiện được công cụ (thiếu hoặc sai tham số)."}, ensure_ascii=False)


# ── Tool helpers (tách để complexity ≤12, extract-verbatim) ──
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
    return bool((place and place.get("area") == area) or prov == _PROV_NAMES.get(area, ""))


def _search_card_practical(card: dict, attrs: dict) -> None:
    hours = attrs.get("hours") or attrs.get("open_hours")
    if hours:
        card["hours"] = hours
    if attrs.get("admission_fee") or attrs.get("admission"):
        card["admission_fee"] = attrs.get("admission_fee") or attrs.get("admission")
    if attrs.get("best_time"):
        card["best_time"] = attrs["best_time"]
    if attrs.get("key_facts"):
        card["key_facts"] = attrs["key_facts"]
    if attrs.get("ocop"):
        card["ocop"] = attrs["ocop"]
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
        text = (e.get("name", "") + e.get("summary", "") + attrs.get("booking_note", "")).lower()
        if not any(kw in text for kw in _ACCOM_FAMILY_KW):
            return False
    return True


def _ocop_card(e: dict, attrs: dict, star_num: int) -> dict:
    card = {
        "id": e["id"], "name": e["name"],
        "ocop": attrs["ocop"],
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
        "verified": e.get("verified", True) is not False and e.get("status") != "provisional",
    }
    # Include coords when available (powers map display)
    coords = e.get("coords") or e.get("coordinates")
    if coords:
        card["coords"] = coords
    _search_card_practical(card, attrs)
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
        if attrs.get("ocop"):          card["ocop"] = attrs["ocop"]
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
        if attrs.get("ocop"):          card["ocop"] = attrs["ocop"]
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
        if not attrs.get("ocop"):
            continue
        if not _area_matches(e, attrs, area):
            continue
        # Star filter
        m = re.search(r"(\d)", str(attrs["ocop"]))
        star_num = int(m.group(1)) if m else 0
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


def _tool_suggest_followups(args: dict) -> str:
    suggestions = generate_followups(args["context"])
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
        from social import get_community_reviews
        entity_id = args.get("entity_id", "")
        limit = args.get("limit", 5)
        reviews = get_community_reviews(entity_id, limit)
        if not reviews:
            return json.dumps({"reviews": [], "note": f"Chưa có đánh giá cộng đồng cho '{entity_id}'"}, ensure_ascii=False)
        return json.dumps({"reviews": reviews, "count": len(reviews)}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning("community_reviews tool error: %s", e)
        return json.dumps({"reviews": [], "error": "Không thể tải đánh giá"})


def _tool_trending_posts(args: dict) -> str:
    try:
        from social import get_trending_posts
        entity_type = args.get("entity_type")
        limit = args.get("limit", 10)
        posts = get_trending_posts(limit, entity_type)
        if not posts:
            return json.dumps({"posts": [], "note": "Chưa có bài viết nổi bật"}, ensure_ascii=False)
        return json.dumps({"posts": posts, "count": len(posts)}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning("trending_posts tool error: %s", e)
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
        return json.dumps({"weather": weather_data, "events": events}, ensure_ascii=False, default=str)
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


def _call_tool_impl(name: str, args: dict) -> str:
    handler = _TOOL_HANDLERS.get(name)
    if handler is not None:
        return handler(args)
    return json.dumps({"error": f"Unknown tool: {name}"})


# ── FastAPI app ──

def build_search_indexes():
    """Build BM25 + contextual + TF-IDF indexes from the KB.

    These power enhanced_hybrid_search. Previously they were never built at
    startup (only via an admin endpoint), so the agent's search ran on plain
    substring matching. Called at startup and after every KB reload.
    """
    knowledge._ensure()
    entities = knowledge._entities
    rels = getattr(knowledge, "_relationships", []) or []

    # Adapt relationship key names (knowledge uses from/to/type; contextual
    # expects source/target/label) so related-entity context is included.
    adapted_rels = [
        {"source": r.get("from", ""), "target": r.get("to", ""),
         "type": r.get("type", ""), "label": ""}
        for r in rels
    ]

    built = {}
    if HAS_CONTEXTUAL:
        try:
            texts = contextual.build_all_contextual(entities, adapted_rels)
            bm25.build_index(texts)
            built["bm25_docs"] = len(texts)
        except Exception as e:
            logger.error(f"BM25/contextual index build failed: {e}")
    if HAS_VECTOR:
        try:
            res = embedding_store.build_index(entities)
            built["embeddings"] = res.get("total_embeddings", res) if isinstance(res, dict) else res
        except Exception as e:
            logger.error(f"Vector index build failed: {e}")
    logger.info(f"Search indexes built: {built}")
    return built


_index_build_lock = threading.Lock()
_index_build_state = {
    "enabled": BUILD_SEARCH_INDEXES,
    "background": BACKGROUND_INDEX_BUILD,
    "running": False,
    "started_at": None,
    "finished_at": None,
    "last_result": None,
    "last_error": None,
}


def start_search_index_build(background: bool = True):
    if not BUILD_SEARCH_INDEXES:
        logger.info("Search index build disabled by BUILD_SEARCH_INDEXES")
        return {"enabled": False}
    with _index_build_lock:
        if _index_build_state["running"]:
            return {"running": True}
        _index_build_state["running"] = True

    def _run():
        with _index_build_lock:
            _index_build_state.update({
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "last_error": None,
            })
        try:
            result = build_search_indexes()
            with _index_build_lock:
                _index_build_state["last_result"] = result
        except Exception as e:
            with _index_build_lock:
                _index_build_state["last_error"] = str(e)
            logger.error(f"Index build error: {e}")
        finally:
            with _index_build_lock:
                _index_build_state["running"] = False
                _index_build_state["finished_at"] = datetime.now(timezone.utc).isoformat()

    if background:
        thread = threading.Thread(target=_run, daemon=True, name="search-index-build")
        thread.start()
        return {"running": True, "background": True}

    _run()
    with _index_build_lock:
        return dict(_index_build_state)


@asynccontextmanager
async def lifespan(app):
    """Khởi động background scheduler và preload data."""
    global _draining
    _draining = False  # reset drain-flag mỗi lần (re)start — TestClient tái dùng lifespan/process trong test
    # Audit vòng 2 fix #4: default executor trên 1 vCPU = min(32, cpu+4) = 5 thread,
    # mỗi phiên /chat giữ 1 thread 30-120s → 5 chat đồng thời là toàn bộ API
    # (auth lookup cũng tranh pool này) tê liệt. Nới lên 16 (I/O-bound là chính).
    from concurrent.futures import ThreadPoolExecutor
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=int(os.environ.get("EXECUTOR_MAX_WORKERS", "16")),
                           thread_name_prefix="vl-exec"))
    knowledge._ensure()
    # Load autocorrect entity names
    if HAS_AUTOCORRECT:
        try:
            load_entity_names(knowledge._entities)
            logger.info("Autocorrect loaded", entities=len(knowledge._entities))
        except Exception:
            logger.debug("Autocorrect load failed", exc_info=True)
    # Build search indexes without blocking readiness. Use BACKGROUND_INDEX_BUILD=false
    # only when deployment should wait for the full enhanced search index.
    start_search_index_build(background=BACKGROUND_INDEX_BUILD)
    start_scheduler()
    logger.info("Server started", model=get_model(), entities=len(knowledge._entities))
    yield
    _draining = True
    logger.info("Server shutting down — draining in-flight requests")
    deadline = time.time() + 30
    while _inflight > 0 and time.time() < deadline:  # noqa: ASYNC110 (shutdown-drain poll có deadline — Event không phù hợp vì đếm inflight giảm dần)
        await asyncio.sleep(0.5)
    if _inflight > 0:
        logger.warning("Force shutdown with in-flight requests", inflight=_inflight)
    stop_scheduler()
    from database import db as _db
    if _db._pg_pool:
        try:
            _db._pg_pool.closeall()
            logger.info("PG connection pool closed")
        except Exception:
            logger.debug("PG pool close failed", exc_info=True)
    if not _db._use_pg:
        try:
            import sqlite3
            conn = sqlite3.connect(_db.db_path, timeout=5)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            logger.info("SQLite WAL checkpoint complete")
        except Exception:
            logger.debug("SQLite WAL checkpoint failed", exc_info=True)
    logger.info("Shutdown complete")
    logger.flush()


_server_start_time = time.time()

# GĐ4.7: ẩn tài liệu API (docs/redoc/openapi) ở production để giảm lộ bề mặt nội bộ.
_IS_PROD = os.environ.get("ENVIRONMENT", "development").strip().lower() == "production"

app = FastAPI(
    title="vinhlong360 Knowledge Agent",
    version="8.2",
    description="AI tourism assistant cho Vĩnh Long (Vĩnh Long + Bến Tre + Trà Vinh).",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
    openapi_tags=[
        {"name": "Chat", "description": "AI chat endpoints"},
        {"name": "Analytics", "description": "Usage analytics and insights"},
        {"name": "System", "description": "System monitoring and health"},
        {"name": "Search", "description": "Vector and knowledge search"},
        {"name": "Recommendations", "description": "Smart recommendation engine"},
        {"name": "Admin", "description": "Administration and CRUD"},
    ],
    lifespan=lifespan,
)
_raw_origins = os.environ.get("CORS_ORIGINS", "http://localhost:8360,http://localhost:3000,https://vinhlong360.vn")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
_env_name = os.environ.get("ENVIRONMENT", "").strip().lower()
if _env_name in ("production", "prod", "prd"):
    _local = [o for o in ALLOWED_ORIGINS if "localhost" in o or "127.0.0.1" in o]
    if _local:
        logger.warning("CORS: removing localhost origins in production mode: %s", _local)
        ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if o not in _local]
    if not os.environ.get("CORS_ORIGINS"):
        logger.warning("CORS_ORIGINS not explicitly set in production — using defaults without localhost")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Admin-Key", "Authorization", "X-CSRF-Token"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def security_headers(request, call_next):
    from auth_middleware import generate_csp_nonce, build_csp, get_security_headers
    nonce = generate_csp_nonce()
    request.state.csp_nonce = nonce
    response = await call_next(request)
    for k, v in get_security_headers(_IS_PROD).items():
        response.headers[k] = v
    response.headers["Content-Security-Policy"] = build_csp(nonce)
    response.headers["X-API-Version"] = "1.0"
    # Vary: phản hồi /api|/admin|/auth phụ thuộc Authorization → cache đúng theo user
    # (salvage session-be af90dbb: tránh cache lẫn giữa các phiên đăng nhập).
    if request.url.path.startswith(("/api/", "/admin/", "/auth/")):
        response.headers["Vary"] = "Authorization, Accept"
    if request.method == "GET" and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "private, max-age=30"
    return response


def _error_response(status_code: int, detail: str, request: Request = None, **extra) -> JSONResponse:
    body = {"detail": detail}
    if request:
        rid = getattr(getattr(request, "state", None), "request_id", None)
        if rid:
            body["request_id"] = rid
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException):
    return _error_response(exc.status_code, exc.detail, request)


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    exc_name = type(exc).__name__
    if exc_name in ("OperationalError", "InterfaceError", "DatabaseError", "PoolTimeout"):
        logger.error("Database connection error",
                     method=request.method, path=request.url.path,
                     error_type=exc_name, error=str(exc)[:300])
        return _error_response(503, "Dịch vụ tạm gián đoạn, vui lòng thử lại sau.", request)
    logger.error("Unhandled error",
                 method=request.method, path=request.url.path,
                 error_type=exc_name, error=str(exc)[:300],
                 traceback=traceback.format_exc()[-4000:])
    return _error_response(500, "Lỗi hệ thống.", request)

app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(public_router)
app.include_router(saved_router)
app.include_router(plans_router)
app.include_router(plans_public_router)
app.include_router(visits_router)
app.include_router(achievements_router)
app.include_router(seo_router)
app.include_router(social_router)
app.include_router(community_router)


TYPE_LABELS_VI = {
    "dish": "Món ăn", "attraction": "Điểm đến", "place": "Xã/phường", "nature": "Thiên nhiên",
    "product": "Sản phẩm", "history": "Di tích", "accommodation": "Lưu trú",
    "craft_village": "Làng nghề", "event": "Sự kiện", "experience": "Trải nghiệm",
    "landmark": "Địa danh", "culture": "Văn hoá", "facility": "Cơ quan",
}


async def _mention_users(ql: str) -> list:
    """@-mention: người dùng khớp (chỉ khi có Postgres)."""
    out: list[dict] = []
    try:
        from database import db
        if db._use_pg:
            ph = db._ph
            def _user_search():
                with db._conn() as conn:
                    return db._fetchall(conn, f"""
                        SELECT id, display_name, avatar_url FROM users
                        WHERE is_active = TRUE AND display_name ILIKE {ph}
                        ORDER BY display_name LIMIT 5
                    """, (f"%{ql}%",))
            rows = await asyncio.to_thread(_user_search)
            for r in rows:
                d = db._row_to_dict(r)
                if d.get("display_name"):
                    out.append({"type": "user", "id": str(d["id"]), "label": d["display_name"],
                                "sub": "Người dùng", "avatar": d.get("avatar_url")})
    except Exception:
        logger.debug("Mention search user query failed", exc_info=True)
    return out


def _mention_entities(ql: str) -> list:
    """@-mention: địa điểm/entity khớp (in-RAM, nhanh)."""
    out: list[dict] = []
    try:
        ents = [e for e in (knowledge._entities or {}).values() if ql in (e.get("name") or "").lower()]
        ents.sort(key=lambda e: (0 if (e.get("name") or "").lower().startswith(ql) else 1, len(e.get("name") or "")))
        for e in ents[:6]:
            out.append({"type": "entity", "id": e["id"], "label": e["name"],
                        "sub": TYPE_LABELS_VI.get(e.get("type"), e.get("type") or "Địa điểm")})
    except Exception:
        logger.debug("Mention search entity query failed", exc_info=True)
    return out


@app.get("/api/mentions", tags=["social"])
async def mention_search(q: str = ""):
    """Autocomplete cho @-mention: người dùng (PG) + địa điểm (KB in-RAM). Trả tối đa ~11 mục."""
    ql = (q or "").strip().lower()
    if len(ql) < 1:
        return {"results": []}
    results = await _mention_users(ql)
    results += _mention_entities(ql)
    return {"results": results}


MAX_BODY_SIZE = 1_048_576  # 1MB
_BODY_LIMITS = {
    "/api/comments": 10_240,        # 10KB for comments
    "/api/posts": 51_200,           # 50KB for posts (text+mentions)
    "/chat": 10_240,                # 10KB for chat messages
    "/auth/avatar": MAX_BODY_SIZE,  # 1MB for avatar upload
}
_STREAMING_REQUEST_PATHS = {"/chat", "/chat/stream", "/api/notifications/stream"}
_NO_TIMEOUT_STREAM_PATHS = {"/api/notifications/stream"}

def _is_streaming_request_path(path: str) -> bool:
    return path in _STREAMING_REQUEST_PATHS

def _is_request_timeout_exempt(path: str) -> bool:
    return path in _NO_TIMEOUT_STREAM_PATHS

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Reject requests with body > limit to prevent DoS. Per-endpoint limits."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
        except ValueError:
            return _error_response(400, "Invalid Content-Length header")
        path = request.url.path
        limit = MAX_BODY_SIZE
        for prefix, plimit in _BODY_LIMITS.items():
            if path.startswith(prefix):
                limit = plimit
                break
        if size > limit:
            return _error_response(413, f"Request body too large (max {limit // 1024}KB)")
    return await call_next(request)


_GATED_EXACT_PATHS = ("/metrics", "/vectors/stats")
_GATED_PREFIX_PATHS = (
    "/system", "/analytics", "/checkpoints", "/confirmations",
    "/confirm/", "/reject/", "/ab-testing", "/prompt-cache", "/freshness",
)


def _is_gated_path(path: str) -> bool:
    return path in _GATED_EXACT_PATHS or any(path.startswith(p) for p in _GATED_PREFIX_PATHS)


@app.middleware("http")
async def gate_internal_endpoints(request: Request, call_next):
    """Gate internal endpoints behind admin key in ALL environments.
    Prevents accidental exposure of /system/*, /analytics/*, /metrics, checkpoints, etc."""
    if _is_gated_path(request.url.path):
        from middleware import verify_admin_key
        if not verify_admin_key(request):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return await call_next(request)


_inflight = 0
_draining = False


@app.middleware("http")
async def graceful_drain(request: Request, call_next):
    global _inflight
    if _draining and not request.url.path.startswith("/health"):
        resp = _error_response(503, "Server shutting down", request)
        resp.headers["Retry-After"] = "5"
        return resp
    _inflight += 1
    try:
        return await call_next(request)
    finally:
        _inflight -= 1


@app.middleware("http")
async def track_response_time(request: Request, call_next):
    """Track response time + request logging."""
    start = time.time()
    req_id = generate_request_id()
    request.state.request_id = req_id
    from middleware import _request_id_var
    _request_id_var.set(req_id)

    path = request.url.path
    is_streaming = _is_streaming_request_path(path)
    timeout_s = 120 if is_streaming else 30

    try:
        if _is_request_timeout_exempt(path):
            response = await call_next(request)
        else:
            response = await asyncio.wait_for(call_next(request), timeout=timeout_s)
        duration_ms = (time.time() - start) * 1000
        endpoint = f"{request.method} {request.url.path}"
        response_tracker.record(endpoint, duration_ms, response.status_code)
        if HAS_METRICS:
            track_http_request(request.method, request.url.path, response.status_code, duration_ms / 1000)

        if duration_ms > 5000:
            logger.warning("Slow request", endpoint=endpoint, duration_ms=round(duration_ms), req_id=req_id)

        response.headers["X-Request-Id"] = req_id
        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"
        if "Cache-Control" not in response.headers:
            path = request.url.path
            if path.startswith((
                "/auth/",
                "/admin/",
                "/api/posts",
                "/api/comments",
                "/api/notifications",
                "/api/me",
                "/api/saved",
                "/api/my-plans",
                "/api/following",
                "/api/blocked-users",
                "/api/notification-preferences",
            )):
                response.headers["Cache-Control"] = "no-store"
            elif path.startswith(("/seo/", "/api/entities", "/api/transparency")):
                response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
            else:
                response.headers["Cache-Control"] = "no-cache"
        return response

    except asyncio.TimeoutError:
        duration_ms = (time.time() - start) * 1000
        endpoint = f"{request.method} {request.url.path}"
        response_tracker.record(endpoint, duration_ms, 504)
        logger.error("Request timeout", endpoint=endpoint, req_id=req_id,
                      duration_ms=round(duration_ms), timeout_s=timeout_s)
        return _error_response(504, "Request timeout", request)
    except Exception as exc:
        duration_ms = (time.time() - start) * 1000
        endpoint = f"{request.method} {request.url.path}"
        error_tracker.record_error(endpoint, str(exc), traceback.format_exc())
        response_tracker.record(endpoint, duration_ms, 500)
        logger.error("Unhandled exception", endpoint=endpoint, req_id=req_id,
                      duration_ms=round(duration_ms), error=str(exc)[:200])
        return _error_response(500, "Internal server error", request)


from pydantic import Field, field_validator

def _sanitize_message(v: str) -> str:
    """Strip HTML/script tags khỏi message người dùng. Dùng cho cả POST /chat
    (validator) lẫn GET /chat/stream (query param) — đảm bảo parity."""
    v = re.sub(r"<script[^>]*>.*?</script>", "", v or "", flags=re.DOTALL | re.IGNORECASE)
    v = re.sub(r"<[^>]+>", "", v)
    v = v.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return v.strip()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    history: list[dict] = Field(default=[], max_length=50, description="Conversation history")
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


# ── Pydantic models for validated POST endpoints ──

class FeedbackRequest(BaseModel):
    query: str = Field(default="", max_length=2000)
    rating: int = Field(..., ge=0, le=1)
    user_id: str = Field(default="anonymous", max_length=64)
    session_id: str = Field(default="anonymous", max_length=64)
    entity_id: str | None = Field(default=None, max_length=64)

class CheckpointSaveRequest(BaseModel):
    session_id: str = Field(default="", max_length=64)
    messages: list[dict] = Field(default=[], max_length=200)
    tools_used: list[str] = Field(default=[], max_length=50)
    agent_state: dict = Field(default={})
    metadata: dict = Field(default={})

class GuardrailCheckRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(default="test", max_length=64)

class JudgeEvaluateRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    reply: str = Field(..., min_length=1, max_length=5000)

class DynamicAgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    trigger_patterns: list[str] = Field(default=[], max_length=20)
    system_prompt_addon: str = Field(default="", max_length=2000)
    tool_whitelist: list[str] | None = Field(None, max_length=50)

class SemanticCacheInvalidateRequest(BaseModel):
    entity_id: str | None = Field(default=None, max_length=64)
    query: str | None = Field(default=None, max_length=500)


# ── P3: Client-side error capture (B8 — KHÔNG Sentry/dịch vụ trả phí) ──
# Thu lỗi frontend qua POST /api/client-error: rate-limit + cap kích thước +
# che PII, ghi vào StructuredLogger (JSONL xoay vòng) đã có sẵn. Opt-in,
# fire-and-forget từ phía client (không chặn UI).

ENABLE_CLIENT_ERROR_CAPTURE = _env_bool("ENABLE_CLIENT_ERROR_CAPTURE", True)

_PII_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"\b(?:0|\+?84)\d{8,10}\b"), "[PHONE]"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP]"),
    # token/bearer/api-key-ish chuỗi dài
    (re.compile(r"\b[A-Za-z0-9_-]{32,}\b"), "[TOKEN]"),
]


def _sanitize_client_text(text: str, max_len: int) -> str:
    """Che PII (email/phone/IP/token) + strip HTML, cắt theo max_len. B6/privacy."""
    if not text or not isinstance(text, str):
        return ""
    out = re.sub(r"<[^>]+>", "", text)
    out = out.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    for pat, repl in _PII_PATTERNS:
        out = pat.sub(repl, out)
    return out[:max_len].strip()


class ClientErrorRequest(BaseModel):
    """Lỗi do frontend gửi lên. Mọi field optional/có default để fire-and-forget
    không bao giờ fail vì thiếu dữ liệu; size-capped để chống abuse/DoS."""
    message: str = Field(default="", max_length=500)
    error: str = Field(default="", max_length=500)
    stack: str = Field(default="", max_length=2000)
    url: str = Field(default="", max_length=300)
    level: str = Field(default="error", max_length=10)
    timestamp: str = Field(default="", max_length=40)
    user_agent: str = Field(default="", max_length=300)
    session_id: str = Field(default="", max_length=64)

    @field_validator("level")
    @classmethod
    def _clamp_level(cls, v):
        return v if v in {"error", "warn", "info"} else "error"


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


def _gather_context_pieces(current_month, rag_query, session_id, user_id, message):
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
            graph_ctx = memory_graph.build_graph_context(user_id) or ""
        except Exception:
            logger.debug("Memory graph context failed", exc_info=True)
    return {
        "proactive": get_proactive_context(month=current_month),
        "rag": build_rag_context(rag_query),
        "realtime": realtime_ctx,
        "memory": memory_manager.build_context(session_id, user_id, message),
        "reflexion": reflexion_engine.get_reflection_prompt(message),
        "graph": graph_ctx,
    }


def _resolve_base_prompt(session_id):
    """Chọn base_prompt (A/B variant) + tiêm KB-in-context. Trả (base_prompt, ab_info)."""
    ab_info = {}
    base_prompt = SYSTEM_PROMPT
    if HAS_AB_TESTING and session_id:
        try:
            variant = ab_manager.assign_variant("prompt_style", session_id)
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


def _assemble_manual_messages(base_prompt, current_month, pieces, reflexion_ctx, history, session_id, message):
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

    if session_id:
        session = memory_manager.get_session(session_id)
        ctx_messages = session.get_context_messages()
        if ctx_messages:
            messages.extend(ctx_messages)
        else:
            messages.extend(history[-20:])
    else:
        messages.extend(history[-20:])

    messages.append({"role": "user", "content": message})
    return messages


def _build_messages(
    message: str,
    history: list[dict],
    session_id: str = "",
    user_id: str = "",
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

    # Resolve anaphoric references (e.g. "bảo tàng" → specific museum from history)
    # before RAG so entity detection picks up the correct entity.
    rag_query = _resolve_contextual_query(message, history)

    pieces = _gather_context_pieces(current_month, rag_query, session_id, user_id, message)
    base_prompt, ab_info = _resolve_base_prompt(session_id)
    # Experience-memory + few-shot fold vào reflexion để chảy qua CẢ cached lẫn manual path.
    reflexion_ctx = _fold_experience_fewshot(message, pieces["reflexion"])

    # Use prompt cache if available
    if HAS_PROMPT_CACHE:
        # Get session history from memory or request
        effective_history = history[-20:]
        if session_id:
            session = memory_manager.get_session(session_id)
            ctx_messages = session.get_context_messages()
            if ctx_messages:
                effective_history = ctx_messages

        messages, cache_info = prompt_cache.build_cached_prompt(
            message=message,
            history=effective_history,
            session_id=session_id,
            user_id=user_id,
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
        base_prompt, current_month, pieces, reflexion_ctx, history, session_id, message)
    return messages, {"ab": ab_info}


LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "30"))


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
                return _MockResponse()
            return cb_result["response"]
        return get_client().chat.completions.create(model=_model, messages=messages, timeout=LLM_TIMEOUT)

    return _llm_call_fn


_llm_call_fn_default = _make_llm_call_fn(get_model)
_llm_call_fn_mini = _make_llm_call_fn(get_model_mini)


# Orchestrator singleton (lazy init)
_orchestrator = None
_orchestrator_lock = threading.Lock()

def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None and HAS_ORCHESTRATOR:
        with _orchestrator_lock:
            if _orchestrator is None:
                _orchestrator = Orchestrator(TOOLS)
    return _orchestrator


# Shared parallel tool executor (concurrent multi-tool rounds in the live loop)
_parallel_executor = None

def _get_parallel_executor():
    global _parallel_executor
    if _parallel_executor is None and HAS_PARALLEL:
        with _orchestrator_lock:
            if _parallel_executor is None:
                _parallel_executor = ParallelToolExecutor(call_tool, max_workers=4)
    return _parallel_executor


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


def _run_agent_orchestrated(message, history, session_id, base_system_prompt):
    """Run agent via the orchestrator, now wired with tuned params + parallel tools
    + learned tool ordering + smart model routing."""
    orch = _get_orchestrator()
    # Pre-route to pick model BEFORE the full run (so the LLM call function
    # is bound to the right model from the first round).
    _cat, _agent = orch.route(message)
    _use_mini = getattr(_agent, "use_mini", False)
    _call_fn = _llm_call_fn_mini if _use_mini else _llm_call_fn_default
    if _use_mini:
        logger.info("Model routing: using MINI", category=_cat.value, agent=_agent.name)

    result = orch.run(
        message=message,
        history=history,
        session_id=session_id,
        base_system_prompt=base_system_prompt,
        call_tool_fn=call_tool,
        llm_call_fn=_call_fn,
        get_params_fn=_optimal_params_fn if HAS_OPTIMIZER else None,
        tool_executor=_get_parallel_executor() if HAS_PARALLEL else None,
        tool_order_fn=_tool_order_fn if HAS_OPTIMIZER else None,
    )
    return result["reply"], result["tools_used"], result["suggestions"]


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
                           empty_results_count, round_num, total_tool_calls):
    """Thực thi pending tool-calls (parallel khi >1, else serial). Trả empty_results_count."""
    if parallel_exec and len(pending_calls) > 1:
        call_items = [{"id": c["id"], "name": c["name"], "args": c["args"]} for c in pending_calls]
        results = parallel_exec.execute_smart(call_items)
        for pc, res in zip(pending_calls, results):
            logger.info("Tool call (parallel)", tool=pc["name"],
                        duration_ms=round(res.get("duration_ms", 0)), round=round_num + 1)
            result = res.get("result", json.dumps({"error": res.get("error", "Unknown")}))
            messages.append({"role": "tool", "tool_call_id": pc["id"], "content": result})
            _post_tool_process(pc["name"], pc["args"], result, suggestions, messages, empty_results_count)
    else:
        for pc in pending_calls:
            logger.info(f"Tool call #{total_tool_calls}", tool=pc["name"],
                        args=str(pc["args"])[:200], round=round_num + 1)
            result = call_tool(pc["name"], pc["args"])
            messages.append({"role": "tool", "tool_call_id": pc["id"], "content": result})
            empty_results_count = _post_tool_process(pc["name"], pc["args"], result, suggestions, messages, empty_results_count)
    return empty_results_count


def _run_agent(messages: list[dict], max_rounds: int = 8, max_tool_calls: int = 15):
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

    # Setup parallel executor if available
    parallel_exec = None
    if HAS_PARALLEL:
        parallel_exec = ParallelToolExecutor(call_tool, max_workers=4)

    for round_num in range(max_rounds):
        # Circuit breaker protected LLM call
        try:
            if HAS_CIRCUIT_BREAKER:
                cb_result = safe_llm_call(get_client(), model=get_model(), messages=messages, tools=TOOLS, tool_choice="auto")
                if not cb_result["success"]:
                    return cb_result["message"], tools_used, suggestions
                response = cb_result["response"]
            else:
                response = get_client().chat.completions.create(
                    model=get_model(), messages=messages, tools=TOOLS, tool_choice="auto",
                    timeout=LLM_TIMEOUT,
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
            empty_results_count, round_num, total_tool_calls)

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


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    # Rate limiting
    client_ip = get_client_ip(request)
    allowed, rate_info = chat_limiter.is_allowed(client_ip)
    if not allowed:
        logger.warning("Rate limited", ip=client_ip, endpoint="/chat")
        _resp = _error_response(429, "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
                                retry_after=rate_info["retry_after"])
        _resp.headers["Retry-After"] = str(rate_info["retry_after"])
        return _resp

    session_id = req.session_id or str(uuid.uuid4())[:8]
    user_id = session_id  # For now, session_id = user_id

    # ── Guardrails: input safety (injection detect + PII mask + budget) ──
    if HAS_GUARDRAILS:
        try:
            guard = check_input(req.message, session_id)
            if not guard.get("allowed", True):
                # P1: log lý do chi tiết server-side, KHÔNG lộ chuỗi chẩn-đoán ra user.
                logger.warning("Guardrails blocked input", reason=guard.get("blocked_reason", ""), session_id=session_id)
                return ChatResponse(
                    reply="Xin lỗi, tin nhắn này không thể xử lý vì lý do an toàn. Vui lòng diễn đạt lại.",
                    tool_calls=[], suggestions=[], session_id=session_id,
                )
        except Exception as _gerr:
            # P1: fail-CLOSED — guardrail lỗi thì KHÔNG cho qua không kiểm.
            logger.warning(f"Guardrail check_input lỗi → fail-closed: {_gerr}")
            return ChatResponse(
                reply="Xin lỗi, hệ thống đang bận kiểm tra an toàn. Vui lòng thử lại sau ít phút.",
                tool_calls=[], suggestions=[], session_id=session_id,
            )

    # Record user message in memory
    memory_manager.on_message(session_id, "user", req.message)

    # ── Semantic cache: embedding-based dedup (before regular cache) ──
    if not req.history and HAS_SEMANTIC_CACHE:
        try:
            sem_cached = semantic_get(req.message)
            if sem_cached:
                if HAS_METRICS:
                    track_cache("hit")
                return ChatResponse(**sem_cached, session_id=session_id, cached=True)
        except Exception:
            logger.debug("Semantic cache retrieval failed", exc_info=True)

    # Check cache (only for new conversations without history)
    if not req.history:
        cached = cache.get(req.message)
        if cached:
            if HAS_METRICS:
                track_cache("hit")
            return ChatResponse(**cached, session_id=session_id, cached=True)
        elif HAS_METRICS:
            track_cache("miss")

    # Autocorrect user input
    corrected_message = req.message
    if HAS_AUTOCORRECT:
        ac = autocorrect(req.message)
        if ac.get("was_corrected"):
            corrected_message = ac["corrected"]

    t0 = time.time()
    build_info = {}
    _trace_ctx = None
    try:
        if HAS_TRACING:
            _trace_ctx = trace_chat_request(corrected_message, session_id, get_model())
            _trace_ctx.__enter__()
        messages, build_info = _build_messages(corrected_message, req.history, session_id, user_id)

        # ── Dynamic agents: check for specialist match before orchestrator ──
        _dyn_prompt_addon = ""
        if HAS_DYNAMIC_AGENTS:
            try:
                dyn_route = check_dynamic_route(corrected_message)
                if dyn_route:
                    _dyn_prompt_addon = dyn_route.get("system_prompt_addon", "")
                    agent_factory.update_performance(dyn_route["agent_id"], 5.0)  # default, updated later
                    logger.info("Dynamic agent matched", agent=dyn_route.get("name", ""), session_id=session_id)
            except Exception:
                logger.debug("Dynamic agent matching failed", exc_info=True)

        # Extract the enriched system context (proactive + RAG + realtime + memory
        # + reflexion + graph) that _build_messages just computed. Previously the
        # orchestrated path received only the bare SYSTEM_PROMPT and discarded all
        # of this — making the entire RAG/memory/reflexion pipeline dead weight on
        # /chat. messages[0] is always the single consolidated system message.
        _enriched_system = SYSTEM_PROMPT
        if messages and messages[0].get("role") == "system" and isinstance(messages[0].get("content"), str):
            _enriched_system = messages[0]["content"]
        if _dyn_prompt_addon:
            _enriched_system = _enriched_system + "\n\n" + _dyn_prompt_addon

        # Inject the self_optimizer's active prompt variant (previously computed
        # but never applied to the live prompt).
        if HAS_OPTIMIZER:
            try:
                _variant = prompt_optimizer.get_current_variant()
                _variant_addon = _variant.get("prompt_addon", "")
                if _variant_addon:
                    _enriched_system = _enriched_system + "\n\n" + _variant_addon
            except Exception:
                logger.debug("Self-optimizer variant failed", exc_info=True)

        # Use orchestrator when available for specialist routing.
        # GĐ4.1: offload vòng lặp agent (OpenAI client ĐỒNG BỘ) sang thread để KHÔNG
        # chặn event loop -> nhiều /chat đồng thời + /health không bị đóng băng.
        if HAS_ORCHESTRATOR:
            reply, tools_used, suggestions = await asyncio.to_thread(
                _run_agent_orchestrated,
                corrected_message, req.history, session_id, _enriched_system,
            )
        else:
            messages[0]["content"] = _enriched_system
            reply, tools_used, suggestions = await asyncio.to_thread(_run_agent, messages)
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

    # ── Knowledge-only fallback: supplement with KB data when LLM fails ──
    # P0/chat: chỉ coi là lỗi khi reply RỖNG, hoặc là fallback hệ-thống thật (mọi fallback
    # đều mở đầu "Xin lỗi/Rất tiếc/Hệ thống..." + chứa cụm sự-cố), hoặc reply rất ngắn báo lỗi.
    # Tránh false-positive: câu trả lời ĐÚNG có chứa "lỗi"/"sự cố" (vd "sự cố giao thông")
    # trước đây bị ghi đè bằng KB-fallback.
    _low = (reply or "").lower().lstrip()
    _starts_apology = _low.startswith(("xin lỗi", "rất tiếc", "hệ thống ai đang", "hệ thống đang"))
    _has_fail_word = any(w in _low for w in (
        "sự cố", "đã xảy ra lỗi", "không thể trả lời", "đang bảo trì", "thử lại sau", "thử lại.",
    ))
    _is_error_reply = (
        not reply
        or (_starts_apology and _has_fail_word)
        or (len(reply) < 80 and _has_fail_word)
    )
    logger.info(f"KB fallback check | is_error={_is_error_reply} | reply_len={len(reply) if reply else 0}")
    if _is_error_reply and corrected_message.strip():
        try:
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
            # Detect month numbers for seasonal queries
            _month_match = re.search(r'(?:tháng|thang)\s*(\d{1,2})', corrected_message, re.IGNORECASE)
            _search_month = int(_month_match.group(1)) if _month_match and 1 <= int(_month_match.group(1)) <= 12 else None

            logger.info(f"KB fallback search | query={_clean_q} | month={_search_month} | original={corrected_message[:80]}")
            # Call knowledge.search_entities directly — avoid call_tool() which has
            # analytics tracking that can crash on corrupt analytics files
            # Check if query is purely about a month (e.g. cleaned to "Tháng 6" or empty)
            _is_month_only = _search_month and re.match(
                r'^(tháng|thang)?\s*\d{1,2}\s*$', _clean_q, re.IGNORECASE
            )
            if _is_month_only:
                # Pure seasonal query — get seasonal + attractions for that month
                kb_data = knowledge.seasonal_now(_search_month)
                if not kb_data:
                    kb_data = knowledge.search_entities(month=_search_month, limit=10)
            else:
                # Use hybrid rerank (BM25 + semantic) for better relevance when
                # available; this is the degraded-mode path so quality matters.
                kb_data = _hybrid_rerank_search({"q": _clean_q, "month": _search_month, "limit": 10})

            # Progressive search: if full query returns nothing, try sub-phrases
            if not kb_data:
                words = _clean_q.split()
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
                    tools_used = ["abstain (kb-fallback)"]
                    suggestions = []
                    kb_data = []  # skip the listing block below
                else:
                    kb_data = _relevant
            if isinstance(kb_data, list) and kb_data:
                if _search_month:
                    lines = [f"Hệ thống AI đang bảo trì. Thông tin tháng {_search_month} từ cơ sở dữ liệu:\n"]
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
                reply = "\n".join(lines)
                tools_used = ["search (kb-fallback)"]
                suggestions = []
        except Exception as kb_err:
            logger.warning("KB fallback error", error=str(kb_err))
            if not reply:
                reply = "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi. Vui lòng thử lại."

    duration = time.time() - t0

    # ── Cost tracking: record token usage ──
    if HAS_COST_TRACKER:
        try:
            # Estimate tokens from message + reply when no response object
            est_in = token_counter.estimate_tokens(corrected_message)
            est_out = token_counter.estimate_tokens(reply)
            # Audit vòng 2 fix #8: record_usage để check_budget (guardrails) có số thật
            if HAS_GUARDRAILS:
                guardrail_budget.record_usage(session_id, est_in + est_out)
            cost_attribution.record(session_id, corrected_message[:200], "chat", None, get_model(),
                                     {"prompt_tokens": est_in, "completion_tokens": est_out, "total_tokens": est_in + est_out},
                                     token_counter.calculate_cost({"prompt_tokens": est_in, "completion_tokens": est_out}, get_model()))
        except Exception:
            logger.debug("Cost tracking failed", exc_info=True)

    # Record assistant reply in memory
    memory_manager.on_message(session_id, "assistant", reply)

    # Memory graph: record entity interactions
    if HAS_MEMORY_GRAPH:
        try:
            memory_graph.on_chat_complete(user_id, corrected_message, reply, [])
        except Exception:
            logger.debug("Memory graph record failed", exc_info=True)

    # LLM memory extraction: extract preferences/facts
    try:
        memory_manager.on_chat_complete(session_id, user_id, corrected_message, reply)
    except Exception:
        logger.debug("LLM memory extraction failed", exc_info=True)

    # Reflexion: evaluate answer quality
    try:
        evaluation = reflexion_engine.evaluate_answer(req.message, reply, tools_used)
        quality_tracker.record(req.message, evaluation["score"], tools_used)

        if evaluation["score"] < 5:
            reflexion_engine.reflect_on_failure(req.message, reply, evaluation)
            logger.warning("Low quality answer", score=evaluation["score"],
                         issues=evaluation["issues"], query=req.message[:100])
        elif evaluation["score"] >= 8:
            # Good answer → save as skill
            memory_manager.on_good_answer(
                req.message[:100], tools_used,
                f"Score {evaluation['score']}: {', '.join(evaluation['good_points'][:2])}",
                reflexion_engine._categorize_query(req.message),
            )
        # Experience memory: distill a strategy item (≥8) or negative constraint (<5)
        if HAS_EXPERIENCE:
            try:
                experience_memory.record(req.message, tools_used, evaluation["score"], reply)
            except Exception:
                logger.debug("Experience memory record failed", exc_info=True)
        # Few-shot demo pool: capture high-scoring (query, answer) exemplars
        if HAS_FEWSHOT:
            try:
                prompt_compiler.record_demo(req.message, reply, evaluation["score"])
            except Exception:
                logger.debug("Few-shot demo record failed", exc_info=True)
    except Exception as eval_err:
        logger.warning("Reflexion evaluation error", error=str(eval_err))
        evaluation = {"score": 0, "issues": [], "good_points": []}

    # ── Self optimizer: record outcome for auto-tuning ──
    if HAS_OPTIMIZER:
        try:
            est_tokens = token_counter.estimate_tokens(reply) if HAS_COST_TRACKER else len(reply) // 3
            record_outcome(session_id, corrected_message, "orchestrator" if HAS_ORCHESTRATOR else "direct",
                          tools_used, evaluation["score"], duration, est_tokens)
        except Exception:
            logger.debug("Self-optimizer outcome record failed", exc_info=True)

    # ── LLM Judge: quality evaluation (non-blocking, best-effort) ──
    if HAS_LLM_JUDGE and LLM_JUDGE_ENABLED and evaluation["score"] >= 3:
        try:
            judge_result = judge(corrected_message, reply)
            if judge_result and judge_result.get("weighted_score", 0) < 4:
                logger.info("LLM Judge low score", score=judge_result.get("weighted_score"), query=req.message[:80])
        except Exception:
            logger.debug("LLM Judge evaluation failed", exc_info=True)

    # A/B testing: record outcome
    if HAS_AB_TESTING and session_id:
        try:
            ab_manager.record_outcome("prompt_style", session_id, evaluation["score"])
        except Exception:
            logger.debug("A/B outcome record failed", exc_info=True)

    # Metrics tracking
    if HAS_METRICS:
        track_chat_request("ok", duration)

    # Track analytics
    try:
        analytics.track_query(req.message, tools_used, reply, session_id)
    except Exception:
        logger.debug("Analytics tracking failed", exc_info=True)

    # ── Guardrails: output validation (PII mask + hallucination check) ──
    if HAS_GUARDRAILS:
        try:
            out_check = check_output(reply, corrected_message, knowledge._entities if hasattr(knowledge, '_entities') else {})
            if out_check.get("cleaned_reply"):
                reply = out_check["cleaned_reply"]
        except Exception as guard_err:
            # GĐ4.5: không nuốt lỗi im lặng — log để biết guardrail output hỏng.
            logger.error("Output guardrail failed", error=str(guard_err))

    # Cache response (only if good quality)
    if not req.history and len(reply) > 30 and evaluation["score"] >= 5:
        cache_data = {"reply": reply, "tool_calls": tools_used, "suggestions": suggestions}
        cache.put(req.message, cache_data)
        # ── Semantic cache: store for embedding-based dedup ──
        if HAS_SEMANTIC_CACHE:
            try:
                semantic_put(req.message, cache_data)
            except Exception:
                pass
        if HAS_METRICS:
            track_cache("set")

    return ChatResponse(reply=reply, tool_calls=tools_used, suggestions=suggestions, session_id=session_id)


# ── SSE Streaming ──

@app.get("/chat/stream")
async def chat_stream(request: Request, message: str, history: str = "[]", session_id: str = ""):
    # Rate limiting
    client_ip = get_client_ip(request)
    allowed, rate_info = stream_limiter.is_allowed(client_ip)
    if not allowed:
        logger.warning("Rate limited", ip=client_ip, endpoint="/chat/stream")
        async def rate_limit_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Quá nhiều yêu cầu. Vui lòng thử lại sau.'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(rate_limit_stream(), media_type="text/event-stream")

    # Parity với POST /chat: cắt độ dài + strip HTML (query param không qua pydantic validator).
    message = _sanitize_message(message)[:2000]
    if not message:
        async def empty_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Tin nhắn trống.'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    try:
        hist = json.loads(history)
        if not isinstance(hist, list):
            hist = []
        hist = hist[:50]
    except Exception:
        hist = []

    sid = session_id or str(uuid.uuid4())[:8]
    user_id = sid

    # ── Guardrails: input safety ──
    if HAS_GUARDRAILS:
        def _safe_block_stream(msg: str):
            async def _gen():
                yield f"data: {json.dumps({'type': 'text', 'content': msg}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'tools': [], 'suggestions': [], 'session_id': sid}, ensure_ascii=False)}\n\n"
            return _gen
        try:
            guard = check_input(message, sid)
            if not guard.get("allowed", True):
                # P1: ẩn blocked_reason (chẩn-đoán) khỏi user, chỉ log server-side
                logger.warning("Guardrails blocked stream input", reason=guard.get("blocked_reason", ""), session_id=sid)
                gen = _safe_block_stream("Xin lỗi, tin nhắn này không thể xử lý vì lý do an toàn. Vui lòng diễn đạt lại.")
                return StreamingResponse(gen(), media_type="text/event-stream")
        except Exception as _gerr:
            # P1: fail-CLOSED
            logger.warning(f"Guardrail stream check lỗi → fail-closed: {_gerr}")
            gen = _safe_block_stream("Xin lỗi, hệ thống đang bận kiểm tra an toàn. Vui lòng thử lại sau ít phút.")
            return StreamingResponse(gen(), media_type="text/event-stream")

    # Record in memory
    memory_manager.on_message(sid, "user", message)

    # ── Semantic cache: check before regular cache ──
    if not hist and HAS_SEMANTIC_CACHE:
        try:
            sem_cached = semantic_get(message)
            if sem_cached:
                async def sem_cached_stream():
                    reply = sem_cached.get("reply", "")
                    words = reply.split(" ")
                    for i in range(0, len(words), 3):
                        chunk = " ".join(words[i:i+3])
                        if i > 0:
                            chunk = " " + chunk
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"
                    suggestions = sem_cached.get("suggestions", [])
                    yield f"data: {json.dumps({'type': 'done', 'tools': ['semantic_cache_hit'], 'suggestions': suggestions, 'session_id': sid}, ensure_ascii=False)}\n\n"
                analytics.track_query(message, ["semantic_cache_hit"], sem_cached.get("reply", ""), sid)
                return StreamingResponse(sem_cached_stream(), media_type="text/event-stream")
        except Exception:
            logger.debug("Semantic cache retrieval failed (stream)", exc_info=True)

    # Check cache for history-less requests
    if not hist:
        cached = cache.get(message)
        if cached:
            async def cached_stream():
                reply = cached.get("reply", "")
                words = reply.split(" ")
                for i in range(0, len(words), 3):
                    chunk = " ".join(words[i:i+3])
                    if i > 0:
                        chunk = " " + chunk
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"
                suggestions = cached.get("suggestions", [])
                yield f"data: {json.dumps({'type': 'done', 'tools': ['cache_hit'], 'suggestions': suggestions, 'session_id': sid}, ensure_ascii=False)}\n\n"
            analytics.track_query(message, ["cache_hit"], cached.get("reply", ""), sid)
            return StreamingResponse(cached_stream(), media_type="text/event-stream")

    # Autocorrect
    original_message = message
    if HAS_AUTOCORRECT:
        ac = autocorrect(message)
        if ac.get("was_corrected"):
            message = ac["corrected"]

    # Build messages with full 2026 architecture context
    messages, _build_info = _build_messages(message, hist, sid, user_id)

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

    async def event_stream():
        # Send autocorrect info if corrected
        if HAS_AUTOCORRECT and message != original_message:
            yield f"data: {json.dumps({'type': 'autocorrect', 'original': original_message, 'corrected': message}, ensure_ascii=False)}\n\n"
        tools_used = []
        suggestions = []
        max_rounds = _stream_rounds

        for round_num in range(max_rounds):
            try:
                _kw = {"model": _stream_model, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "timeout": LLM_TIMEOUT}
                if _stream_temp is not None:
                    _kw["temperature"] = _stream_temp
                # CONC-001: chạy LLM-call ĐỒNG-BỘ trong thread để KHÔNG chặn event loop
                # (request /chat khác + /health vẫn xử lý được trong lúc chờ LLM).
                response = await asyncio.to_thread(lambda: get_client().chat.completions.create(**_kw))
                msg = response.choices[0].message
            except Exception as exc:
                error_tracker.record_error("/chat/stream", str(exc), traceback.format_exc())
                yield f"data: {json.dumps({'type': 'text', 'content': 'Xin lỗi, đã xảy ra lỗi. Vui lòng thử lại.'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'tools': tools_used, 'suggestions': [], 'session_id': sid}, ensure_ascii=False)}\n\n"
                return

            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, TypeError):
                        fn_args = {}  # EH-02: JSON args lỗi → {} thay vì crash stream
                    tools_used.append(fn_name)

                    # Tool-use Tracing: send start event with description
                    tool_desc = _tool_description(fn_name, fn_args)
                    yield f"data: {json.dumps({'type': 'tool_start', 'name': fn_name, 'description': tool_desc, 'args': fn_args}, ensure_ascii=False)}\n\n"

                    t0 = time.time()
                    result = await asyncio.to_thread(call_tool, fn_name, fn_args)  # CONC-001: tool I/O off event loop
                    duration_ms = round((time.time() - t0) * 1000)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

                    # Tool-use Tracing: send done event with timing
                    result_preview = result[:200] if len(result) > 200 else result
                    yield f"data: {json.dumps({'type': 'tool_done', 'name': fn_name, 'duration_ms': duration_ms, 'preview': result_preview}, ensure_ascii=False)}\n\n"

                    # Track entity discussions in memory
                    if fn_name in ("entity_detail", "nearby_entities") and "entity_id" in fn_args:
                        memory_manager.on_entity_discussed(sid, fn_args["entity_id"])

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

                def _produce_stream():
                    try:
                        stream = get_client().chat.completions.create(
                            model=_stream_model, messages=messages, stream=True,
                            timeout=LLM_TIMEOUT,
                        )
                        for chunk in stream:
                            if _cancelled.is_set():
                                break
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
                try:
                    while True:
                        item = await chunk_q.get()
                        if item is None:
                            break
                        if isinstance(item, Exception):
                            raise item
                        _chunks.append(item)
                        yield f"data: {json.dumps({'type': 'text', 'content': item}, ensure_ascii=False)}\n\n"
                except (asyncio.CancelledError, GeneratorExit):
                    _cancelled.set()
                    await producer
                    return
                await producer
                full_text = "".join(_chunks)

                # Record in memory
                memory_manager.on_message(sid, "assistant", full_text)

                # Memory graph: record entity interactions
                if HAS_MEMORY_GRAPH:
                    try:
                        memory_graph.on_chat_complete(user_id, message, full_text, [])
                    except Exception:
                        logger.debug("Memory graph record failed (stream)", exc_info=True)

                # LLM memory extraction
                try:
                    memory_manager.on_chat_complete(sid, user_id, message, full_text)
                except Exception:
                    logger.debug("LLM memory extraction failed (stream)", exc_info=True)

                # ── Cost tracking ──
                if HAS_COST_TRACKER:
                    try:
                        est_in = token_counter.estimate_tokens(message)
                        est_out = token_counter.estimate_tokens(full_text)
                        # Audit vòng 2 fix #8: đồng bộ với đường non-stream
                        if HAS_GUARDRAILS:
                            guardrail_budget.record_usage(sid, est_in + est_out)
                        cost_attribution.record(sid, message[:200], "stream", None, get_model(),
                                                 {"prompt_tokens": est_in, "completion_tokens": est_out, "total_tokens": est_in + est_out},
                                                 token_counter.calculate_cost({"prompt_tokens": est_in, "completion_tokens": est_out}, get_model()))
                    except Exception:
                        logger.debug("Cost tracking failed (stream)", exc_info=True)

                # Reflexion: evaluate quality
                evaluation = reflexion_engine.evaluate_answer(message, full_text, tools_used)
                quality_tracker.record(message, evaluation["score"], tools_used)
                if evaluation["score"] < 5:
                    reflexion_engine.reflect_on_failure(message, full_text, evaluation)
                elif evaluation["score"] >= 8:
                    memory_manager.on_good_answer(
                        message[:100], tools_used,
                        f"Score {evaluation['score']}",
                        reflexion_engine._categorize_query(message),
                    )
                if HAS_EXPERIENCE:
                    try:
                        experience_memory.record(message, tools_used, evaluation["score"], full_text)
                    except Exception:
                        logger.debug("Experience memory record failed (stream)", exc_info=True)
                if HAS_FEWSHOT:
                    try:
                        prompt_compiler.record_demo(message, full_text, evaluation["score"])
                    except Exception:
                        logger.debug("Few-shot demo record failed (stream)", exc_info=True)

                # ── Self optimizer: record outcome ──
                if HAS_OPTIMIZER:
                    try:
                        est_tok = token_counter.estimate_tokens(full_text) if HAS_COST_TRACKER else len(full_text) // 3
                        record_outcome(sid, message, "stream", tools_used, evaluation["score"], 0, est_tok)
                    except Exception:
                        logger.debug("Self-optimizer outcome failed (stream)", exc_info=True)

                # ── LLM Judge: quality evaluation ──
                if HAS_LLM_JUDGE and LLM_JUDGE_ENABLED and evaluation["score"] >= 3:
                    try:
                        judge(message, full_text)
                    except Exception:
                        logger.debug("LLM Judge failed (stream)", exc_info=True)

                # A/B testing: record outcome
                if HAS_AB_TESTING and sid:
                    try:
                        ab_manager.record_outcome("prompt_style", sid, evaluation["score"])
                    except Exception:
                        logger.debug("A/B outcome record failed (stream)", exc_info=True)

                # Metrics tracking
                if HAS_METRICS:
                    track_chat_request("ok", 0)  # duration not tracked in stream

                # ── Guardrails: output validation ──
                if HAS_GUARDRAILS:
                    try:
                        out_check = check_output(full_text, message, knowledge._entities if hasattr(knowledge, '_entities') else {})
                        if out_check.get("cleaned_reply") and out_check["cleaned_reply"] != full_text:
                            full_text = out_check["cleaned_reply"]
                    except Exception:
                        logger.debug("Stream guardrail check failed", exc_info=True)

                # Track & cache
                analytics.track_query(message, tools_used, full_text, sid)
                if not hist and len(full_text) > 30 and evaluation["score"] >= 5:
                    cache_data = {"reply": full_text, "tool_calls": tools_used, "suggestions": suggestions}
                    # Lưu theo original_message (khoá lúc cache.get) — không phải bản đã autocorrect,
                    # nếu không lần sau cùng câu gốc sẽ luôn MISS (đã sửa: stream cache key mismatch).
                    cache.put(original_message, cache_data)
                    # ── Semantic cache: store ──
                    if HAS_SEMANTIC_CACHE:
                        try:
                            semantic_put(message, cache_data)
                        except Exception:
                            logger.debug("Semantic cache put failed", exc_info=True)

                # Send quality score for UI feedback prompt
                yield f"data: {json.dumps({'type': 'done', 'tools': tools_used, 'suggestions': suggestions, 'session_id': sid, 'quality': evaluation['score']}, ensure_ascii=False)}\n\n"
                return

        # ── Round-exhaustion: every round called tools without a final answer.
        # Force ONE synthesis turn (no tools) so the user gets an answer built
        # from gathered evidence instead of an empty response.
        try:
            messages.append({
                "role": "system",
                "content": ("[Hệ thống]: Đã đạt giới hạn số vòng. Hãy tổng hợp câu trả lời "
                            "tốt nhất TỪ thông tin đã thu thập, KHÔNG gọi thêm tool, "
                            "trả lời trực tiếp bằng tiếng Việt."),
            })
            synth_q: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()
            def _synth_produce():
                try:
                    resp = get_client().chat.completions.create(model=_stream_model, messages=messages, stream=True, timeout=LLM_TIMEOUT)
                    for chunk in resp:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            loop.call_soon_threadsafe(synth_q.put_nowait, delta.content)
                finally:
                    loop.call_soon_threadsafe(synth_q.put_nowait, None)
            loop.run_in_executor(None, _synth_produce)
            synth_text = ""
            while True:
                token = await synth_q.get()
                if token is None:
                    break
                synth_text += token
                yield f"data: {json.dumps({'type': 'text', 'content': token}, ensure_ascii=False)}\n\n"
            if synth_text:
                memory_manager.on_message(sid, "assistant", synth_text)
                analytics.track_query(message, tools_used, synth_text, sid)
        except Exception:
            logger.debug("Stream synthesis fallback failed", exc_info=True)

        yield f"data: {json.dumps({'type': 'done', 'tools': tools_used, 'suggestions': suggestions, 'session_id': sid}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── System endpoints ──

@app.post("/reload")
async def reload_data(request: Request):
    # GĐ3.8: /reload giờ AN TOÀN (nạp lại từ DB, không xoá gì). Yêu cầu admin để
    # chống DoS rebuild ẩn danh (security audit). data-quality/replace VẪN khoá.
    from middleware import verify_admin_key
    # Chấp nhận X-Admin-Key (server) HOẶC phiên admin đăng nhập (frontend admin) — đồng bộ
    # với require_admin của /admin-api/* (trước đây /reload chỉ nhận X-Admin-Key nên nút
    # "Reload KB" trong admin UI luôn bị 401).
    authed = verify_admin_key(request)
    if not authed:
        from admin import require_admin_scope
        await require_admin_scope(request, "ops.deploy")
        authed = True
    if not authed:
        try:
            from auth_middleware import get_current_user
            _u = await get_current_user(request)
            authed = bool(_u and _u.get("role") == "admin")
        except Exception:
            authed = False
    if not authed:
        return _error_response(403, "Cần X-Admin-Key hoặc phiên admin")

    def _reload_blocking():
        # GĐ11.4: toàn bộ phần nặng (reload DB + rebuild index + sync) chạy trong thread
        # → event loop không bị đóng băng (/health vẫn đáp ứng trong lúc reload).
        result = knowledge.reload()
        cache.invalidate_all()
        _public_api.invalidate_place_cache()  # tránh phục vụ place_name/area cũ sau reload
        if HAS_PROMPT_CACHE:
            prompt_cache.invalidate()
        if HAS_KB_CONTEXT:
            kb_context.invalidate()
        # Rebuild search indexes so new/changed entities are searchable via hybrid.
        try:
            result["indexes"] = build_search_indexes()
        except Exception as e:
            logger.error(f"Index rebuild on reload failed: {e}")
        sync_data_json_to_js()
        return result

    result = await asyncio.to_thread(_reload_blocking)
    logger.info("Data reloaded", **{k: v for k, v in result.items() if k != "indexes"})
    return result


_health_llm_cache = {"status": "not_checked", "checked_at": 0.0}


async def _check_llm_health() -> str:
    def _ping() -> str:
        try:
            get_client().chat.completions.create(
                model=get_model_mini(),
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                timeout=8,
            )
            return "ok"
        except Exception as e:
            return f"error: {type(e).__name__}"

    status = await asyncio.to_thread(_ping)
    global _health_llm_cache
    _health_llm_cache = {"status": status, "checked_at": time.time()}
    return status


def _health_core() -> tuple:
    """Shared health probes — returns (overall_status, db_ok, llm_status)."""
    knowledge._ensure()
    llm_status = _health_llm_cache["status"]
    db_ok = False
    try:
        from database import db as _db
        with _db._conn() as conn:
            _db._fetchone(conn, "SELECT 1", ())
        db_ok = True
    except Exception:
        logger.debug("Health check DB probe failed", exc_info=True)
    errors_healthy = error_tracker.is_healthy()
    llm_ok = llm_status != "error"
    overall = "ok" if (errors_healthy and db_ok and llm_ok) else "degraded"
    return overall, db_ok, llm_status


@app.get("/health")
async def health():
    overall, _, _ = await asyncio.to_thread(_health_core)
    return {
        "status": overall,
        "time": datetime.now(timezone.utc).isoformat(),
        "entities": len(knowledge._entities),
    }


def _health_data_quality() -> dict:
    total_entities = len([e for e in knowledge._entities.values() if e.get("type") != "place"])
    missing_summary = len([e for e in knowledge._entities.values() if e.get("type") != "place" and not e.get("summary")])
    return {
        "total_entities": total_entities,
        "missing_summary": missing_summary,
        "coverage_pct": round((total_entities - missing_summary) / total_entities * 100, 1) if total_entities else 0,
    }


def _health_features() -> dict:
    """Cờ khả-dụng feature (simple data-driven) + feature có stats phụ."""
    _flags = {
        "realtime": HAS_REALTIME, "parallel_tools": HAS_PARALLEL,
        "autocorrect": HAS_AUTOCORRECT, "recommender": HAS_RECOMMENDER,
        "freshness": HAS_FRESHNESS, "image_recognition": HAS_IMAGE_RECOGNITION,
        "metrics": HAS_METRICS, "orchestrator": HAS_ORCHESTRATOR,
        "memory_graph": HAS_MEMORY_GRAPH, "tracing": HAS_TRACING,
        "contextual_retrieval": HAS_CONTEXTUAL, "checkpoints": HAS_CHECKPOINTS,
        "guardrails": HAS_GUARDRAILS, "cost_tracker": HAS_COST_TRACKER,
        "eval_framework": HAS_EVAL, "self_optimizer": HAS_OPTIMIZER,
        "llm_judge": HAS_LLM_JUDGE,
    }
    feats = {k: {"available": v} for k, v in _flags.items()}
    feats["vector_search"] = embedding_store.stats() if HAS_VECTOR else {"available": False}
    feats["kb_context"] = kb_context.stats() if HAS_KB_CONTEXT else {"available": False}
    feats["experience_memory"] = experience_memory.stats() if HAS_EXPERIENCE else {"available": False}
    feats["fewshot_compiler"] = prompt_compiler.stats() if HAS_FEWSHOT else {"available": False}
    feats["circuit_breaker"] = all_breaker_stats() if HAS_CIRCUIT_BREAKER else {"available": False}
    feats["ab_testing"] = {"available": HAS_AB_TESTING, "experiments": len(ab_manager.list_experiments()) if HAS_AB_TESTING else 0}
    feats["prompt_cache"] = prompt_cache.stats() if HAS_PROMPT_CACHE else {"available": False}
    feats["semantic_cache"] = {"available": HAS_SEMANTIC_CACHE, **(semantic_cache_stats() if HAS_SEMANTIC_CACHE else {})}
    feats["dynamic_agents"] = {"available": HAS_DYNAMIC_AGENTS, "active_agents": len(agent_factory.get_active_agents()) if HAS_DYNAMIC_AGENTS else 0}
    return feats


async def _health_detail() -> dict:
    """Full health payload — internal use by admin-gated endpoints."""
    overall, db_ok, llm_status = _health_core()
    try:
        import psutil
        memory_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
    except Exception:
        memory_mb = None
    from database import db as _db
    return {
        "status": overall,
        "version": "8.2",
        "uptime_seconds": round(time.time() - _server_start_time, 0),
        "memory_mb": memory_mb,
        "database": {"ok": db_ok, "backend": "postgres" if _db._use_pg else "sqlite"},
        "llm_api": llm_status,
        "llm_api_checked_at": datetime.fromtimestamp(_health_llm_cache["checked_at"]).isoformat() if _health_llm_cache["checked_at"] else None,
        "deep_checks": False,
        "entities": len(knowledge._entities),
        "data_quality": _health_data_quality(),
        "model": get_model(),
        "cache": cache.stats(),
        "response_times": response_tracker.stats(),
        "rate_limits": chat_limiter.stats(),
        "errors": error_tracker.stats(),
        "scheduler": scheduler_status(),
        "search_index": dict(_index_build_state),
        **_health_features(),
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/deep")
async def deep_health(request: Request):
    from admin import require_admin
    await require_admin(request)
    await _check_llm_health()
    payload = await _health_detail()
    payload["deep_checks"] = True
    if payload["llm_api"] != "ok" and payload["status"] == "ok":
        payload["status"] = "degraded"
    return payload


@app.get("/health/details")
async def health_details(request: Request):
    from admin import require_admin
    await require_admin(request)
    return await _health_detail()

@app.get("/health/internal")
async def health_internal(request: Request):
    from admin import require_admin
    await require_admin(request)
    return await _health_detail()


@app.get("/health/ready")
async def readiness_probe():
    """Lightweight readiness probe for load balancers / orchestrators."""
    def _probe():
        from database import db as _db
        data_source = getattr(knowledge, "_data_source", None) or "unknown"
        entity_count = len(getattr(knowledge, "_entities", None) or {})
        checks = {
            "knowledge": entity_count > 0,
            "data_source": data_source == "db" if getattr(_db, "_use_pg", False) else data_source in {"db", "json"},
        }
        try:
            with _db._conn() as conn:
                _db._fetchone(conn, "SELECT 1", ())
            checks["database"] = True
        except Exception:
            checks["database"] = False
        schema = _db.pg_schema_status()
        checks["schema"] = bool(schema.get("ok"))
        checks["schema_version"] = schema
        return checks
    checks = await asyncio.to_thread(_probe)
    ready = all(value for key, value in checks.items() if key != "schema_version")
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"ready": ready, "checks": checks},
    )


@app.get("/health/slo")
async def slo_metrics(request: Request):
    """Basic SLO tracking: uptime, error rate, p95 latency. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    uptime_s = time.time() - _server_start_time
    rt_stats = response_tracker.stats()
    err_stats = error_tracker.stats()
    total_req = rt_stats.get("total_requests", 0)
    error_count = err_stats.get("recent_errors", 0)
    error_rate = round(error_count / max(total_req, 1) * 100, 2)
    p95 = rt_stats.get("p95_ms", 0)
    return {
        "uptime_seconds": round(uptime_s, 0),
        "uptime_pct": round(min(100, uptime_s / max(uptime_s, 1) * 100), 2),
        "total_requests": total_req,
        "error_rate_pct": error_rate,
        "p95_latency_ms": p95,
        "slo_targets": {
            "error_rate_pct": 1.0,
            "p95_latency_ms": 3000,
        },
        "slo_met": {
            "error_rate": error_rate <= 1.0,
            "latency": p95 <= 3000,
        },
    }


# ── Prometheus metrics endpoint ──

@app.get("/metrics", tags=["System"])
async def metrics_endpoint(request: Request):
    """Prometheus-compatible metrics in text exposition format. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_METRICS:
        return _error_response(501, "Metrics module not available")
    set_gauge("cache_size", len(cache._cache) if hasattr(cache, '_cache') else 0)
    set_gauge("entities_total", len(knowledge._entities))
    from fastapi.responses import Response
    return Response(content=generate_metrics(), media_type="text/plain; charset=utf-8")


# ── A/B Testing endpoints ──

@app.get("/ab-testing/experiments", tags=["System"])
async def ab_experiments(request: Request):
    """List all A/B testing experiments. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_AB_TESTING:
        raise HTTPException(503, detail="A/B testing not available")
    return {"experiments": ab_manager.list_experiments()}

@app.get("/ab-testing/results/{experiment_name}", tags=["System"])
async def ab_results(experiment_name: str, request: Request):
    """Get A/B test results with statistics. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_AB_TESTING:
        raise HTTPException(503, detail="A/B testing not available")
    results = ab_manager.get_results(experiment_name)
    significance = ab_manager.is_significant(experiment_name)
    return {"experiment": experiment_name, "results": results, "significance": significance}

@app.get("/prompt-cache/stats", tags=["System"])
async def prompt_cache_stats(request: Request):
    """Get prompt cache statistics. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_PROMPT_CACHE:
        return {"available": False}
    return {"available": True, **prompt_cache.stats()}


# ── Analytics endpoints ──

@app.get("/analytics/summary")
async def analytics_summary(request: Request):
    from admin import require_admin
    await require_admin(request)
    try:
        return await asyncio.to_thread(analytics.get_summary)
    except Exception:
        raise HTTPException(503, detail="Analytics data unavailable")


@app.get("/analytics/popular")
async def analytics_popular(request: Request, limit: int = Query(20, ge=1, le=200)):
    from admin import require_admin
    await require_admin(request)
    return {"popular_queries": await asyncio.to_thread(analytics.get_popular_queries, limit)}


@app.get("/analytics/gaps")
async def analytics_gaps(request: Request, limit: int = Query(20, ge=1, le=200)):
    from admin import require_admin
    await require_admin(request)
    return {"knowledge_gaps": await asyncio.to_thread(analytics.get_knowledge_gaps, limit)}


@app.get("/analytics/daily")
async def analytics_daily(request: Request, days: int = Query(30, ge=1, le=365)):
    from admin import require_admin
    await require_admin(request)
    return {"daily_stats": await asyncio.to_thread(analytics.get_daily_stats, days)}


@app.get("/analytics/top-entities")
async def analytics_top_entities(request: Request, limit: int = Query(20, ge=1, le=200)):
    from admin import require_admin
    await require_admin(request)
    return {"top_entities": await asyncio.to_thread(analytics.get_top_entities, limit)}


# ── System monitoring endpoints ──

@app.get("/system/logs")
async def system_logs(request: Request, limit: int = Query(50, ge=1, le=500), level: str = None):
    from admin import require_admin
    await require_admin(request)
    return {"logs": logger.recent(limit, level)}


@app.get("/system/errors")
async def system_errors(request: Request, limit: int = Query(20, ge=1, le=200)):
    from admin import require_admin
    await require_admin(request)
    return {"errors": error_tracker.recent_errors(limit), **error_tracker.stats()}


@app.get("/system/response-times")
async def system_response_times(request: Request):
    from admin import require_admin
    await require_admin(request)
    return response_tracker.stats()


@app.get("/system/scheduler")
async def system_scheduler(request: Request):
    from admin import require_admin
    await require_admin(request)
    return scheduler_status()


@app.get("/system/learning", tags=["System"])
async def system_learning(request: Request):
    """Trạng thái vòng lặp tự học. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    try:
        from learn_loop import learning_status
        return learning_status()
    except ImportError:
        raise HTTPException(503, detail="learn_loop module not available")


@app.post("/system/learning/run", tags=["System"])
async def trigger_learning(request: Request):
    """Trigger 1 vòng lặp tự học SAU cổng fitness (admin only, eval-gated)."""
    from admin import require_admin_scope
    await require_admin_scope(request, "ops.deploy")
    try:
        from self_evolve import guarded_evolve
        from learn_loop import run_full_cycle
        summary = guarded_evolve("learning-loop(manual)", lambda: run_full_cycle(dry_run=False))
        return {"status": "completed", "decision": summary["decision"],
                "reason": summary["reason"], "before": summary["before"], "after": summary["after"]}
    except Exception as e:
        logger.error("learning-loop error: %s", e)
        return _error_response(500, "Internal server error")


@app.get("/system/self-evolution", tags=["System"])
async def system_self_evolution(request: Request):
    """Trạng thái cơ chế tự tiến hoá. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    out = {}
    try:
        import self_evolve
        out["evolution"] = self_evolve.status()
    except Exception as e:
        logger.warning("self_evolve status error: %s", e)
        out["evolution"] = {"error": "unavailable"}
    try:
        import self_eval
        out["current_fitness"] = self_eval.compute_fitness()
    except Exception as e:
        logger.warning("self_eval fitness error: %s", e)
        out["current_fitness"] = {"error": "unavailable"}
    try:
        import kb_curation
        out["curation"] = kb_curation.stats()
    except Exception as e:
        logger.warning("kb_curation stats error: %s", e)
        out["curation"] = {"error": "unavailable"}
    try:
        import experience_memory
        out["experience"] = experience_memory.stats()
    except Exception as e:
        logger.warning("experience_memory stats error: %s", e)
        out["experience"] = {"error": "unavailable"}
    try:
        import geocode
        out["geocode"] = geocode.stats()
    except Exception as e:
        logger.warning("geocode stats error: %s", e)
        out["geocode"] = {"error": "unavailable"}
    return out


@app.get("/system/memory")
async def system_memory(request: Request):
    from admin import require_admin
    await require_admin(request)
    return memory_manager.stats()


@app.get("/system/traces", tags=["System"])
async def system_traces(request: Request, limit: int = Query(50, ge=1, le=500)):
    """OpenTelemetry trace data. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_TRACING:
        return {"available": False}
    return {
        "available": True,
        "summary": get_trace_summary(),
        "traces": export_traces_json(limit),
    }


@app.get("/system/handoffs", tags=["System"])
async def system_handoffs(request: Request, limit: int = Query(50, ge=1, le=200)):
    """Multi-agent orchestrator handoff log. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_ORCHESTRATOR:
        return {"available": False}
    from dataclasses import asdict
    records = handoff_log.recent(limit)
    return {
        "available": True,
        "handoffs": [asdict(r) for r in records],
        "stats": handoff_log.stats(),
    }


@app.get("/system/memory-graph", tags=["System"])
async def system_memory_graph(request: Request):
    """Memory graph statistics. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_MEMORY_GRAPH:
        return {"available": False}
    graph_stats = memory_graph.stats()
    return {
        "available": True,
        **graph_stats,
        "patterns": memory_graph.get_emerging_patterns()[:10],
    }


# ── Checkpoint / Confirmation endpoints ──

@app.get("/checkpoints/{session_id}", tags=["System"])
async def list_checkpoints(session_id: str, request: Request):
    """List conversation checkpoints. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_CHECKPOINTS:
        return {"available": False}
    return {"checkpoints": checkpoint_manager.list_checkpoints(session_id)}


@app.post("/checkpoints", tags=["System"])
async def save_checkpoint(req: CheckpointSaveRequest, request: Request):
    """Save a conversation checkpoint. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_CHECKPOINTS:
        return _error_response(501, "Checkpoints not available")
    cp_id = checkpoint_manager.save_checkpoint(
        session_id=req.session_id,
        messages=req.messages,
        tools_used=req.tools_used,
        agent_state=req.agent_state,
        metadata=req.metadata,
    )
    return {"checkpoint_id": cp_id}


@app.post("/checkpoints/{checkpoint_id}/resume", tags=["System"])
async def resume_checkpoint(checkpoint_id: str, request: Request):
    """Resume from a conversation checkpoint. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_CHECKPOINTS:
        return _error_response(501, "Checkpoints not available")
    result = checkpoint_manager.resume_from(checkpoint_id)
    if result is None:
        return _error_response(404, "Checkpoint not found")
    messages, agent_state = result
    return {"messages": messages, "agent_state": agent_state}


@app.get("/confirmations/{session_id}", tags=["System"])
async def pending_confirmations(session_id: str, request: Request):
    """List pending confirmations. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_CHECKPOINTS:
        return {"available": False}
    pending = confirmation_manager.get_pending(session_id)
    return {"pending": [{"id": p.confirmation_id, "action_type": p.action_type,
                         "description": p.description, "prompt": format_confirmation_prompt(p)}
                        for p in pending]}


@app.post("/confirm/{confirmation_id}", tags=["System"])
async def confirm_action(confirmation_id: str, request: Request):
    """Confirm a pending action. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_CHECKPOINTS:
        return _error_response(501, "Checkpoints not available")
    params = confirmation_manager.confirm(confirmation_id)
    if params is None:
        return _error_response(404, "Confirmation not found or expired")
    return {"confirmed": True, "params": params}


@app.post("/reject/{confirmation_id}", tags=["System"])
async def reject_action(confirmation_id: str, request: Request):
    """Reject a pending action. Admin-only."""
    from admin import require_admin
    await require_admin(request)
    if not HAS_CHECKPOINTS:
        return _error_response(501, "Checkpoints not available")
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    reason = body.get("reason", "")
    confirmation_manager.reject(confirmation_id, reason)
    return {"rejected": True}


# ── Contextual retrieval endpoint ──

@app.get("/search/enhanced", tags=["Search"])
async def enhanced_search(q: str = Query(..., max_length=200), limit: int = Query(10, ge=1, le=100), rerank: bool = False):
    """Enhanced hybrid search with BM25 + contextual embeddings."""
    if not HAS_CONTEXTUAL:
        raise HTTPException(503, detail="Contextual retrieval not available")
    def _search():
        knowledge._ensure()
        keyword_results = knowledge.search_entities(q=q, limit=limit * 3)
        relationships = knowledge._relationships if hasattr(knowledge, '_relationships') else []
        results = enhanced_hybrid_search(
            query=q,
            keyword_results=keyword_results,
            entities=knowledge._entities,
            relationships=relationships,
            rerank=rerank,
            top_k=limit,
        )
        enriched = []
        for r in results:
            eid = r.get("entity_id", r.get("id", ""))
            e = knowledge.get_entity(eid)
            if e:
                enriched.append({
                    "entity_id": eid,
                    "name": e["name"],
                    "type": e["type"],
                    "summary": e.get("summary", "")[:150],
                    "score": r.get("score", r.get("combined_score", 0)),
                })
        return enriched
    return {"results": await asyncio.to_thread(_search)}


@app.get("/system/quality")
async def system_quality(request: Request):
    from admin import require_admin
    await require_admin(request)
    return {
        "quality": quality_tracker.stats(),
        "reflexion": reflexion_engine.stats(),
    }


@app.post("/feedback")
async def user_feedback(req: FeedbackRequest, request: Request):
    """Nhận feedback từ user (thumbs up/down)."""
    client_ip = get_client_ip(request)
    allowed, _ = chat_limiter.is_allowed(f"fb:{client_ip}")
    if not allowed:
        return _error_response(429, "Too many requests")

    user_id = req.user_id or req.session_id or "anonymous"
    query = req.query
    rating = req.rating
    entity_id = req.entity_id
    memory_manager.feedback(user_id, query, rating * 5, entity_id)
    if HAS_METRICS:
        track_feedback(positive=(rating == 1))

    # Feed into learning loop
    try:
        from learn_loop import record_feedback
        record_feedback(query=query, rating=rating, entity_id=entity_id, session_id=user_id)
    except Exception:
        logger.debug("Learn loop feedback record failed", exc_info=True)
    logger.info("User feedback", user_id=user_id, rating=rating, query=query[:50])
    return {"success": True}


@app.post("/api/client-error")
async def client_error(req: ClientErrorRequest, request: Request):
    """P3: Nhận lỗi frontend (uncaught/unhandledrejection/component) để admin xem.

    B8: KHÔNG Sentry/dịch vụ trả phí — chỉ ghi vào StructuredLogger (JSONL xoay vòng)
    đã có sẵn. Rate-limit (report_limiter: 5 lỗi/IP/5 phút) + cap kích thước (model
    Field max_length) + che PII. Best-effort: luôn trả 200 để client fire-and-forget,
    kể cả khi bị giới hạn (không để client retry loop)."""
    if not ENABLE_CLIENT_ERROR_CAPTURE:
        return {"status": "disabled"}

    client_ip = get_client_ip(request)
    allowed, _ = report_limiter.is_allowed(f"clienterr:{client_ip}")
    if not allowed:
        # Không trả 429 để tránh client coi là lỗi → vòng lặp báo lỗi-của-lỗi.
        return {"status": "rate_limited"}

    try:
        logger.error(
            "Client error",
            source="client",
            level=req.level,
            client_message=_sanitize_client_text(req.message, 500),
            client_error=_sanitize_client_text(req.error, 500),
            stack=_sanitize_client_text(req.stack, 800),
            url=_sanitize_client_text(req.url, 300),
            user_agent=req.user_agent[:200],
            session_id=req.session_id[:64],
            client_ts=req.timestamp[:40],
        )
    except Exception:
        # Ghi log không bao giờ được làm vỡ response.
        pass
    return {"success": True}


@app.get("/system/client-errors", tags=["System"])
async def system_client_errors(request: Request, limit: int = Query(50, ge=1, le=500)):
    """Admin xem lỗi frontend gần đây (lọc source=client từ StructuredLogger).
    Gate bằng admin key (giống các /system/* khác ở production)."""
    from admin import require_admin_scope
    await require_admin_scope(request, "ops.deploy")
    limit = max(1, min(limit, 200))
    rows = logger.recent(limit * 4, level="error")
    client_rows = [r for r in rows if r.get("source") == "client"]
    return {"errors": client_rows[-limit:], "count": len(client_rows[-limit:])}


@app.get("/welcome")
async def welcome_message(session_id: str = ""):
    """Welcome message cá nhân hóa."""
    preferences = None
    if session_id:
        profile = memory_manager.cold.get_profile(session_id)
        if profile.conversation_count > 0:
            preferences = {
                "interests": profile.interests,
                "preferred_areas": profile.preferred_areas,
            }
    return generate_welcome_message(preferences)


# ── Vector search endpoints ──

@app.post("/vectors/build")
async def build_vectors(request: Request):
    """Build/rebuild vector embeddings index."""
    # GĐ4.2: rebuild nặng -> chỉ admin (chống DoS compute ẩn danh).
    from admin import require_admin_scope
    await require_admin_scope(request, "ops.deploy")
    if not HAS_VECTOR:
        return _error_response(501, "Vector search module not available")
    def _build():
        knowledge._ensure()
        return embedding_store.build_index(knowledge._entities)
    return await asyncio.to_thread(_build)

@app.get("/vectors/stats")
async def vector_stats(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_VECTOR:
        return {"available": False}
    return {"available": True, **embedding_store.stats()}

@app.get("/vectors/search")
async def vector_search_endpoint(request: Request, q: str = Query(..., max_length=200), limit: int = Query(10, ge=1, le=100)):
    from admin import require_admin_scope
    await require_admin_scope(request, "ops.deploy")
    if not HAS_VECTOR:
        raise HTTPException(503, detail="Vector search not available")
    def _search():
        results = embedding_store.search(q, top_k=limit)
        enriched = []
        for r in results:
            e = knowledge.get_entity(r["entity_id"])
            if e:
                enriched.append({
                    **r,
                    "name": e["name"],
                    "type": e["type"],
                    "summary": e.get("summary", "")[:100],
                })
        return enriched
    return {"results": await asyncio.to_thread(_search)}


# ── Realtime endpoints ──

@app.get("/weather")
async def weather_endpoint(area: str = Query("vinh-long", max_length=50)):
    if not HAS_REALTIME:
        raise HTTPException(503, detail="Realtime module not available")
    return await asyncio.to_thread(get_weather, area)

@app.get("/weather/all")
async def weather_all():
    if not HAS_REALTIME:
        raise HTTPException(503, detail="Realtime module not available")
    return {"areas": await asyncio.to_thread(get_all_weather)}

@app.get("/events")
async def events_endpoint(days: int = Query(30, ge=1, le=365), area: str = Query(None, max_length=50)):
    if not HAS_REALTIME:
        raise HTTPException(503, detail="Realtime module not available")
    return {"events": await asyncio.to_thread(get_upcoming_events, days, area)}


# ── Recommendation endpoints ──

@app.get("/recommend")
async def recommend_endpoint(
    entity_id: str = Query(None, max_length=200), month: int = Query(None, ge=1, le=12),
    weather: str = Query(None, max_length=50), time_of_day: str = Query(None, max_length=50),
    limit: int = Query(10, ge=1, le=100),
):
    if not HAS_RECOMMENDER:
        raise HTTPException(503, detail="Recommender not available")
    def _rec():
        knowledge._ensure()
        ctx = {}
        if entity_id:
            ctx["entity_id"] = entity_id
        if month:
            ctx["month"] = month
        else:
            ctx["month"] = datetime.now(timezone.utc).month
        if weather:
            ctx["weather"] = weather
        if time_of_day:
            ctx["time_of_day"] = time_of_day
        ctx["entities"] = knowledge._entities
        ctx["relationships"] = knowledge._relationships if hasattr(knowledge, '_relationships') else []
        ctx["limit"] = limit
        return recommend(ctx)
    return await asyncio.to_thread(_rec)


# ── Freshness endpoints ──

@app.get("/freshness/check")
async def freshness_check_endpoint(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_FRESHNESS:
        raise HTTPException(503, detail="Freshness module not available")
    def _check():
        knowledge._ensure()
        return check_freshness(knowledge._entities)
    return await asyncio.to_thread(_check)

@app.get("/freshness/report")
async def freshness_report_endpoint(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_FRESHNESS:
        raise HTTPException(503, detail="Freshness module not available")
    def _report():
        knowledge._ensure()
        return freshness_report(knowledge._entities)
    return {"report": await asyncio.to_thread(_report)}

@app.get("/freshness/candidates")
async def freshness_candidates_endpoint(request: Request, limit: int = Query(20, ge=1, le=200)):
    from admin import require_admin
    await require_admin(request)
    if not HAS_FRESHNESS:
        raise HTTPException(503, detail="Freshness module not available")
    def _candidates():
        knowledge._ensure()
        return auto_refresh_candidates(knowledge._entities, limit)
    return {"candidates": await asyncio.to_thread(_candidates)}


# ── Image recognition endpoint ──

@app.post("/image/recognize")
async def image_recognize_endpoint(request: Request):
    # GĐ4.2: mỗi call là 1 lượt LLM vision (tốn tiền) -> chỉ admin để chặn drain ví ẩn danh.
    # (Frontend hiện không dùng. Mở cho user đã xác thực + rate-limit khi cần — Backlog.)
    from admin import require_admin_scope
    await require_admin_scope(request, "ops.deploy")
    if not HAS_IMAGE_RECOGNITION:
        return _error_response(501, "Image recognition not available")
    content_type = request.headers.get("content-type", "")
    if "multipart" in content_type:
        form = await request.form()
        file = form.get("file")
        if not file:
            return _error_response(400, "No file uploaded")
        max_bytes = 10 * 1024 * 1024
        file_bytes = await file.read(max_bytes + 1)
        if len(file_bytes) > max_bytes:
            return _error_response(413, "Image too large (max 10MB)")
        filename = getattr(file, "filename", "image.jpg")
        ct = getattr(file, "content_type", "image/jpeg")
        result = process_upload(file_bytes, filename, ct)
        return result
    else:
        body = await request.json()
        image_b64 = body.get("image")
        if not image_b64:
            return _error_response(400, "No image data")
        # Limit base64 image size to ~10MB (13.3M base64 chars)
        if len(image_b64) > 13_400_000:
            return _error_response(413, "Image too large (max 10MB)")
        knowledge._ensure()
        result = recognize_image(image_b64, knowledge._entities)
        return result


# ── Autocorrect endpoint ──

@app.get("/autocorrect")
async def autocorrect_endpoint(q: str):
    if not HAS_AUTOCORRECT:
        return {"original": q, "corrected": q, "was_corrected": False}
    return await asyncio.to_thread(autocorrect, q)


# ── Circuit breaker stats ──

@app.get("/system/circuit-breakers")
async def circuit_breaker_stats(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_CIRCUIT_BREAKER:
        return {"available": False}
    return {"available": True, **all_breaker_stats()}


# ── Knowledge graph data endpoint (for frontend visualization) ──

@app.get("/graph")
async def graph_endpoint(entity_id: str, hops: int = 2, max_nodes: int = 30):
    """Return subgraph data for knowledge graph visualization."""
    from agentic_rag import graph_expand
    return await asyncio.to_thread(lambda: graph_expand(entity_id, max_hops=min(hops, 4), max_nodes=min(max_nodes, 50)))


# ════════════════════════════════════════════════════════════════
# Level 6 endpoints
# ════════════════════════════════════════════════════════════════

# ── Guardrails ──

@app.get("/system/guardrails", tags=["Level6"])
async def guardrails_status(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_GUARDRAILS:
        return {"available": False}
    return {
        "available": True,
        "injection_patterns": len(injection_detector._patterns) if hasattr(injection_detector, '_patterns') else 0,
        "budget_sessions": guardrail_budget.get_stats() if hasattr(guardrail_budget, 'get_stats') else {},
    }

@app.post("/system/guardrails/check-input", tags=["Level6"])
async def guardrails_check_input(req: GuardrailCheckRequest, request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_GUARDRAILS:
        raise HTTPException(503, detail="Guardrails not available")
    return check_input(req.message, req.session_id)


# ── Cost tracker ──

@app.get("/system/costs", tags=["Level6"])
async def cost_tracker_report(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_COST_TRACKER:
        return {"available": False}
    return {"available": True, **get_cost_report()}

@app.get("/system/costs/session/{session_id}", tags=["Level6"])
async def cost_tracker_session(session_id: str, request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_COST_TRACKER:
        raise HTTPException(503, detail="Cost tracker not available")
    return cost_attribution.get_session_cost(session_id)

@app.get("/system/costs/budget", tags=["Level6"])
async def cost_budget_status(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_COST_TRACKER:
        raise HTTPException(503, detail="Cost tracker not available")
    return {
        "daily": cost_budget.check_budget("daily"),
        "monthly": cost_budget.check_budget("monthly"),
    }


# ── Eval framework ──

@app.get("/system/eval/latest", tags=["Level6"])
async def eval_latest(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_EVAL:
        return {"available": False}
    report = get_latest_report()
    return {"available": True, "report": report}

@app.get("/system/eval/history", tags=["Level6"])
async def eval_history(request: Request, limit: int = Query(10, ge=1, le=100)):
    from admin import require_admin
    await require_admin(request)
    if not HAS_EVAL:
        return {"available": False}
    return {"available": True, "reports": get_report_history(limit)}


# ── Self optimizer ──

@app.get("/system/optimizer", tags=["Level6"])
async def optimizer_report(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_OPTIMIZER:
        return {"available": False}
    return {"available": True, **get_optimization_report()}


# ── Semantic cache ──

@app.get("/system/semantic-cache", tags=["Level6"])
async def semantic_cache_status(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_SEMANTIC_CACHE:
        return {"available": False}
    return {"available": True, **semantic_cache_stats()}

@app.post("/system/semantic-cache/invalidate", tags=["Level6"])
async def semantic_cache_invalidate(req: SemanticCacheInvalidateRequest, request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_SEMANTIC_CACHE:
        raise HTTPException(503, detail="Semantic cache not available")
    if req.entity_id:
        multi_tier_cache.invalidate_entity(req.entity_id)
        return {"success": True, "invalidated": f"entity:{req.entity_id}"}
    elif req.query:
        multi_tier_cache.invalidate(req.query)
        return {"success": True, "invalidated": f"query:{req.query[:50]}"}
    raise HTTPException(400, detail="Provide entity_id or query")


# ════════════════════════════════════════════════════════════════
# Level 7 endpoints
# ════════════════════════════════════════════════════════════════

# ── LLM Judge ──

@app.get("/system/judge", tags=["Level7"])
async def judge_report(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_LLM_JUDGE:
        return {"available": False}
    return {"available": True, **get_judge_report()}

@app.post("/system/judge/evaluate", tags=["Level7"])
async def judge_evaluate(req: JudgeEvaluateRequest, request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_LLM_JUDGE:
        raise HTTPException(503, detail="LLM Judge not available")
    result = judge(req.query, req.reply)
    return result


# ── Dynamic agents ──

@app.get("/system/dynamic-agents", tags=["Level7"])
async def dynamic_agents_report(request: Request):
    from admin import require_admin
    await require_admin(request)
    if not HAS_DYNAMIC_AGENTS:
        return {"available": False}
    return {"available": True, **get_agent_report()}

@app.post("/system/dynamic-agents/create", tags=["Level7"])
async def dynamic_agents_create(req: DynamicAgentCreateRequest, request: Request):
    # P0-12: chặn tạo agent không-auth (system_prompt_addon + tool_whitelist do client kiểm
    # soát → prompt-injection/đốt LLM budget nếu mở). Bắt buộc X-Admin-Key.
    from admin import require_admin_scope
    await require_admin_scope(request, "ops.deploy")
    if not HAS_DYNAMIC_AGENTS:
        raise HTTPException(503, detail="Dynamic agents not available")
    spec = agent_factory.create_agent(
        name=req.name,
        description=req.description,
        trigger_patterns=req.trigger_patterns,
        system_prompt_addon=req.system_prompt_addon,
        tool_whitelist=req.tool_whitelist,
    )
    return {"status": "created", "agent": spec.to_dict()}


# P2-5: route legacy /admin-dashboard + /admincp ĐÃ XOÁ — admin thật là Nuxt SPA /admin/*
# (web/admin*.html không còn tồn tại; route cũ không-auth = bề mặt thừa).

# ── Chat UI ──

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    nonce = getattr(request.state, "csp_nonce", "")
    return CHAT_HTML.replace("<script>", f'<script nonce="{nonce}">', 1)


CHAT_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>vinhlong360 — Knowledge Agent</title>
<style>
* { box-sizing: border-box; margin: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #fbf7ef; color: #20312b; }
.chat-wrap { max-width: 720px; margin: 0 auto; padding: 20px; min-height: 100vh; display: flex; flex-direction: column; }
.header { text-align: center; margin-bottom: 20px; }
h1 { font-size: 1.4rem; margin-bottom: 4px; }
h1 span { color: #e8743b; }
.subtitle { color: #6b7b73; font-size: .9rem; }
.stats-bar { display: flex; justify-content: center; gap: 16px; margin-top: 8px; font-size: .8rem; color: #8a9a92; }
.stats-bar span { background: #f0ece3; padding: 3px 10px; border-radius: 12px; }
.messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding-bottom: 16px; }
.msg { padding: 14px 18px; border-radius: 18px; max-width: 88%; line-height: 1.6; font-size: .95rem; }
.msg.user { align-self: flex-end; background: #1f7a4d; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant { align-self: flex-start; background: #fff; border: 1px solid #e6e0d4; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
.msg.assistant h1,.msg.assistant h2,.msg.assistant h3 { font-size: 1rem; margin: 10px 0 4px; color: #1f7a4d; }
.msg.assistant h1:first-child,.msg.assistant h2:first-child,.msg.assistant h3:first-child { margin-top: 0; }
.msg.assistant ul,.msg.assistant ol { margin: 4px 0; padding-left: 20px; }
.msg.assistant li { margin: 2px 0; }
.msg.assistant strong { color: #1f7a4d; }
.msg.assistant code { background: #f5f1e8; padding: 1px 5px; border-radius: 3px; font-size: .9em; }
.msg.assistant p { margin: 6px 0; }
.msg.assistant p:first-child { margin-top: 0; }
.msg.assistant p:last-child { margin-bottom: 0; }
.tools-info { font-size: .78rem; color: #8a9a92; margin-top: 10px; border-top: 1px solid #f0ece3; padding-top: 6px; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.tools-info::before { content: "\\2699"; font-size: 1rem; }
.tool-badge { display: inline-block; background: #f0ece3; padding: 2px 8px; border-radius: 8px; margin: 2px; font-family: monospace; font-size: .75rem; }
.trace-panel { background: #f8f6f0; border: 1px solid #e6e0d4; border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; font-size: .82rem; }
.trace-step { display: flex; align-items: center; gap: 8px; padding: 4px 0; color: #6b7b73; transition: all .3s; }
.trace-step.active { color: #1f7a4d; font-weight: 500; }
.trace-step.done { color: #8a9a92; }
.trace-icon { width: 18px; text-align: center; flex-shrink: 0; }
.trace-step.active .trace-icon::after { content: ""; display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #1f7a4d; animation: pulse-dot 1s infinite; }
.trace-step.done .trace-icon::after { content: "\\2713"; color: #1f7a4d; }
.trace-time { margin-left: auto; font-size: .72rem; color: #b0bdb6; font-family: monospace; }
@keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: .3; } }
.code-block { background: #2d2d2d; color: #f8f8f2; padding: 12px 16px; border-radius: 8px; overflow-x: auto; font-size: .85rem; margin: 8px 0; }
.code-block code { background: none; padding: 0; color: inherit; }
blockquote { border-left: 3px solid #1f7a4d; padding: 4px 12px; margin: 8px 0; color: #4a5a52; background: #f5faf7; border-radius: 0 8px 8px 0; }
.md-table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: .88rem; }
.md-table td { border: 1px solid #e6e0d4; padding: 6px 10px; }
.md-table tr:nth-child(even) { background: #faf8f3; }
.md-table tr:first-child td { background: #f0ece3; font-weight: 600; }
hr { border: none; border-top: 1px solid #e6e0d4; margin: 12px 0; }
.msg.assistant a { color: #1f7a4d; text-decoration: underline; }
.msg.assistant a:hover { color: #0d5a33; }
/* Accessibility: focus indicators */
*:focus-visible { outline: 2px solid #1f7a4d; outline-offset: 2px; }
.input-row input:focus-visible { box-shadow: 0 0 0 3px rgba(31,122,77,.2); }
@media (prefers-reduced-motion: reduce) { .typing-dots span { animation: none; } .trace-step.active .trace-icon::after { animation: none; } }
@media (prefers-contrast: more) { .msg.assistant { border-width: 2px; } .tool-badge { border: 1px solid #333; } }
.feedback-row { display: flex; gap: 6px; margin-top: 8px; }
.feedback-row button { padding: 4px 12px; border: 1px solid #e6e0d4; border-radius: 14px; background: #fff; cursor: pointer; font-size: .82rem; transition: all .15s; }
.feedback-row button:hover { border-color: #1f7a4d; }
.feedback-row button.voted { background: #f0faf5; border-color: #1f7a4d; color: #1f7a4d; pointer-events: none; }
.typing { align-self: flex-start; padding: 14px 18px; }
.typing-dots { display: flex; gap: 4px; align-items: center; }
.typing-dots span { width: 8px; height: 8px; border-radius: 50%; background: #b0bdb6; animation: bounce .6s infinite alternate; }
.typing-dots span:nth-child(2) { animation-delay: .2s; }
.typing-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes bounce { to { opacity: .3; transform: translateY(-4px); } }
.suggestions { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0; }
.suggestions button { padding: 8px 14px; border: 1px solid #e6e0d4; border-radius: 999px; background: #fff; cursor: pointer; font-size: .88rem; color: #20312b; transition: all .15s; }
.suggestions button:hover { border-color: #1f7a4d; color: #1f7a4d; background: #f0faf5; }
.input-row { display: flex; gap: 8px; position: sticky; bottom: 0; background: #fbf7ef; padding: 12px 0; }
.input-row input { flex: 1; padding: 14px 16px; border: 1px solid #e6e0d4; border-radius: 14px; font-size: 1rem; background: #fff; outline: none; transition: border-color .15s; }
.input-row input:focus { border-color: #1f7a4d; }
.input-row button { padding: 0 24px; border: none; border-radius: 14px; background: #1f7a4d; color: #fff; font-weight: 700; font-size: 1rem; cursor: pointer; transition: opacity .15s; }
.input-row button:disabled { opacity: .4; cursor: default; }
</style>
</head>
<body>
<div class="chat-wrap">
  <div class="header">
    <h1>vinhlong<span>360</span> Knowledge Agent</h1>
    <p class="subtitle">Chuyên gia AI về tỉnh Vĩnh Long — du lịch, văn hóa, lịch sử, ẩm thực</p>
    <div class="stats-bar" id="statsBar"></div>
  </div>
  <div class="suggestions" id="initSuggestions">
    <button onclick="ask(this.textContent)">Tháng này nên đi đâu?</button>
    <button onclick="ask(this.textContent)">Đặc sản OCOP nổi bật?</button>
    <button onclick="ask(this.textContent)">Lập lịch trình 2 ngày ẩm thực</button>
    <button onclick="ask(this.textContent)">Chùa Khmer ở Trà Vinh?</button>
    <button onclick="ask(this.textContent)">So sánh Bến Tre và Trà Vinh</button>
    <button onclick="ask(this.textContent)">Gần Cầu Mỹ Thuận có gì?</button>
  </div>
  <div class="messages" id="messages" role="log" aria-live="polite" aria-label="Lịch sử hội thoại"></div>
  <div class="input-row">
    <input id="input" type="text" placeholder="Hỏi về Vĩnh Long..." autofocus aria-label="Nhập câu hỏi về Vĩnh Long" role="textbox">
    <button id="sendBtn" onclick="send()" aria-label="Gửi câu hỏi">Gửi</button>
  </div>
</div>
<script>
const msgs=document.getElementById('messages'),input=document.getElementById('input'),sendBtn=document.getElementById('sendBtn');
let history=[];
fetch('/health').then(r=>r.json()).then(d=>{
  document.getElementById('statsBar').innerHTML=
    '<span>'+d.entities+' thực thể</span><span>'+d.status+'</span>';
}).catch(()=>{});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!sendBtn.disabled)send()});
function ask(t){input.value=t;send()}
async function send(){
  const text=input.value.trim();if(!text)return;input.value='';
  document.getElementById('initSuggestions').style.display='none';
  addMsg('user',text);history.push({role:'user',content:text});sendBtn.disabled=true;
  const typing=document.createElement('div');typing.className='typing';
  typing.innerHTML='<div class="typing-dots"><span></span><span></span><span></span></div>';
  msgs.appendChild(typing);msgs.scrollTop=msgs.scrollHeight;
  const params=new URLSearchParams({message:text,history:JSON.stringify(history.slice(-20))});
  try{
    const response=await fetch('/chat/stream?'+params);const reader=response.body.getReader();
    const decoder=new TextDecoder();typing.remove();
    const msgDiv=addMsg('assistant','',true);const contentDiv=msgDiv.querySelector('.content')||msgDiv;
    let fullText='',tools=[],buffer='';
    while(true){const{done,value}=await reader.read();if(done)break;
      buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\\n');buffer=lines.pop();
      for(const line of lines){if(!line.startsWith('data: '))continue;
        try{const data=JSON.parse(line.slice(6));
          if(data.type==='autocorrect'){
            const acDiv=document.createElement('div');
            acDiv.style.cssText='font-size:.82rem;color:#8a9a92;padding:4px 10px;margin-bottom:6px;background:#fef9f0;border-radius:8px;border:1px solid #f0e6d4;';
            acDiv.innerHTML='\\u270E \\u0110\\u00e3 s\\u1eeda: <s>'+data.original+'</s> \\u2192 <b>'+data.corrected+'</b>';
            msgDiv.insertBefore(acDiv,contentDiv);
          }else if(data.type==='tool_start'){tools.push(data.name);
            if(!msgDiv.querySelector('.trace-panel')){const tp=document.createElement('div');tp.className='trace-panel';msgDiv.insertBefore(tp,contentDiv);}
            const tp=msgDiv.querySelector('.trace-panel');
            const step=document.createElement('div');step.className='trace-step active';step.id='trace-'+data.name+'-'+tools.length;
            step.innerHTML='<span class="trace-icon"></span><span>'+data.description+'</span>';
            tp.appendChild(step);msgs.scrollTop=msgs.scrollHeight;
          }else if(data.type==='tool_done'){
            const steps=msgDiv.querySelectorAll('.trace-step.active');
            if(steps.length){const s=steps[steps.length-1];s.classList.remove('active');s.classList.add('done');
              const tm=document.createElement('span');tm.className='trace-time';tm.textContent=data.duration_ms+'ms';s.appendChild(tm);}
          }else if(data.type==='tool'){tools.push(data.name);
            if(!msgDiv.querySelector('.tools-row')){const row=document.createElement('div');row.className='tools-info tools-row';row.textContent=' ';msgDiv.appendChild(row);}
            const b=document.createElement('span');b.className='tool-badge';b.textContent=data.name;msgDiv.querySelector('.tools-row').appendChild(b);
          }else if(data.type==='text'){fullText+=data.content;contentDiv.innerHTML=renderMd(fullText);msgs.scrollTop=msgs.scrollHeight;
          }else if(data.type==='done'){
            const tp=msgDiv.querySelector('.trace-panel');if(tp)tp.style.opacity='.6';
            if(data.suggestions&&data.suggestions.length)showSuggestions(data.suggestions);
            showFeedback(msgDiv,text);
          }
        }catch(e){}}
    }
    history.push({role:'assistant',content:fullText});
  }catch(err){typing.remove();addMsg('assistant','Lỗi kết nối: '+err.message);}
  sendBtn.disabled=false;input.focus();
}
function addMsg(role,content,isHtml){const div=document.createElement('div');div.className='msg '+role;
  if(role==='assistant'&&isHtml)div.innerHTML='<div class="content"></div>';
  else if(isHtml)div.innerHTML=content;else div.textContent=content;
  msgs.appendChild(div);msgs.scrollTop=msgs.scrollHeight;return div;}
function showSuggestions(items){const old=document.querySelector('.suggestions.dynamic');if(old)old.remove();
  const div=document.createElement('div');div.className='suggestions dynamic';
  items.forEach(t=>{const b=document.createElement('button');b.textContent=t;b.onclick=()=>{div.remove();ask(t);};div.appendChild(b);});
  msgs.appendChild(div);msgs.scrollTop=msgs.scrollHeight;}
function showFeedback(msgDiv,query){
  const row=document.createElement('div');row.className='feedback-row';
  const up=document.createElement('button');up.textContent='👍 Hữu ích';
  const down=document.createElement('button');down.textContent='👎 Chưa tốt';
  up.onclick=()=>{sendFeedback(query,1);up.classList.add('voted');down.style.display='none';};
  down.onclick=()=>{sendFeedback(query,0);down.classList.add('voted');up.style.display='none';};
  row.appendChild(up);row.appendChild(down);msgDiv.appendChild(row);
}
function sendFeedback(query,rating){
  fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({query:query,rating:rating,session_id:'web'})}).catch(()=>{});
}
function renderMd(t){let h=t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Code blocks (``` ... ```)
  h=h.replace(/```(\\w*)\\n([\\s\\S]*?)```/g,function(m,lang,code){return '<pre class="code-block"><code>'+code.trim()+'</code></pre>';});
  // Inline code
  h=h.replace(/`(.+?)`/g,'<code>$1</code>');
  // Bold, italic
  h=h.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>').replace(/\\*(.+?)\\*/g,'<em>$1</em>');
  // Headings
  h=h.replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^# (.+)$/gm,'<h1>$1</h1>');
  // Blockquotes
  h=h.replace(/^&gt; (.+)$/gm,'<blockquote>$1</blockquote>').replace(/<\\/blockquote>\\s*<blockquote>/g,'<br>');
  // Links [text](url)
  h=h.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  // Tables
  h=h.replace(/^\\|(.+)\\|$/gm,function(m,row){
    var cells=row.split('|').map(function(c){return c.trim();});
    return '<tr>'+cells.map(function(c){return c.match(/^[\\-:]+$/)?'':'<td>'+c+'</td>';}).join('')+'</tr>';
  });
  h=h.replace(/(<tr>.*<\\/tr>\\s*)+/gs,function(m){
    var rows=m.trim();if(rows.indexOf('<td>')>=0)return '<table class="md-table">'+rows.replace(/<tr><\\/tr>/g,'')+'</table>';return rows;
  });
  // Lists
  h=h.replace(/^[\\-\\*] (.+)$/gm,'<li>$1</li>').replace(/^(\\d+)\\. (.+)$/gm,'<li>$2</li>');
  h=h.replace(/(<li>.*<\\/li>)/gs,function(m){return '<ul>'+m+'</ul>';}).replace(/<\\/ul>\\s*<ul>/g,'');
  // Horizontal rule
  h=h.replace(/^---$/gm,'<hr>');
  // Paragraphs
  h=h.replace(/\\n\\n/g,'</p><p>');h='<p>'+h+'</p>';
  h=h.replace(/<p><(h[123]|ul|ol|pre|blockquote|table|hr)/g,'<$1').replace(/<\\/(h[123]|ul|ol|pre|blockquote|table)><\\/p>/g,'</$1>').replace(/<p><\\/p>/g,'').replace(/<hr><\\/p>/g,'<hr>');
  return h;}
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    print("=" * 64)
    print("  vinhlong360 Knowledge Agent v8.2 — Level 7 Architecture")
    print("=" * 64)
    print(f"  Model:       {get_model()}")
    print(f"  API:         {os.environ.get('LLM_BASE_URL', '(unset)')}")
    print("  Chat:        /chat, /chat/stream  (+rate limit)")
    print("  Admin:       /admin/* (Nuxt SPA)")
    print("  Analytics:   /analytics/*  (summary, gaps, daily)")
    print("  System:      /system/*  (logs, errors, memory, quality)")
    print("  Level 5:     /system/traces, /system/handoffs, /system/memory-graph")
    print("               /checkpoints/*, /confirm/*, /search/enhanced")
    print("  Level 6:     /system/guardrails, /system/costs, /system/eval/*")
    print("               /system/optimizer, /system/semantic-cache")
    print("  Level 7:     /system/judge, /system/dynamic-agents")
    print("  Feedback:    /feedback, /welcome")
    print("  Tools:       13 AI tools (parallel execution)")
    print("  Core Stack:")
    print("    Agentic RAG:   Adaptive + Corrective + Graph (3-hop)")
    print("    Memory:        Hot (session) + Cold (encrypted)")
    print("    Reflexion:     Self-evaluation + skill documents")
    print("    Proactive:     Seasonal + time-aware + trending")
    print("    Middleware:     Rate-limit + logging + error-tracking")
    print("    Scheduler:     auto-learn(6h) + rels(24h) + sync(1h)")
    print(f"    Vector:        {'✓' if HAS_VECTOR else '✗'}")
    print(f"    Realtime:      {'✓' if HAS_REALTIME else '✗'}")
    print(f"    Circuit Break: {'✓' if HAS_CIRCUIT_BREAKER else '✗'}")
    print(f"    Parallel:      {'✓' if HAS_PARALLEL else '✗'}")
    print(f"    Autocorrect:   {'✓' if HAS_AUTOCORRECT else '✗'}")
    print(f"    Recommender:   {'✓' if HAS_RECOMMENDER else '✗'}")
    print(f"    Freshness:     {'✓' if HAS_FRESHNESS else '✗'}")
    print(f"    Image Recog:   {'✓' if HAS_IMAGE_RECOGNITION else '✗'}")
    print("  Level 5 (Multi-Agent):")
    print(f"    Orchestrator:  {'✓' if HAS_ORCHESTRATOR else '✗'}  (Specialist Routing)")
    print(f"    Memory Graph:  {'✓' if HAS_MEMORY_GRAPH else '✗'}  (Knowledge Compounding)")
    print(f"    OTel Tracing:  {'✓' if HAS_TRACING else '✗'}  (GenAI Semantic)")
    print(f"    Contextual:    {'✓' if HAS_CONTEXTUAL else '✗'}  (BM25 + Reranking)")
    print(f"    Checkpoints:   {'✓' if HAS_CHECKPOINTS else '✗'}  (Human-in-the-Loop)")
    print(f"    Metrics:       {'✓' if HAS_METRICS else '✗'}  (Prometheus)")
    print(f"    A/B Testing:   {'✓' if HAS_AB_TESTING else '✗'}")
    print(f"    Prompt Cache:  {'✓' if HAS_PROMPT_CACHE else '✗'}")
    print("  Level 6 (Self-Optimizing):")
    print(f"    Guardrails:    {'✓' if HAS_GUARDRAILS else '✗'}  (Safety + PII)")
    print(f"    Cost Tracker:  {'✓' if HAS_COST_TRACKER else '✗'}  (Token Attribution)")
    print(f"    Eval Framework:{'✓' if HAS_EVAL else '✗'}  (Benchmarks)")
    print(f"    Self Optimizer:{'✓' if HAS_OPTIMIZER else '✗'}  (Auto-Tuning)")
    print(f"    Semantic Cache:{'✓' if HAS_SEMANTIC_CACHE else '✗'}  (Embedding Dedup)")
    print("  Level 7 (Self-Evolving):")
    print(f"    LLM Judge:     {'✓' if HAS_LLM_JUDGE else '✗'}  (Quality Eval)")
    print(f"    Dynamic Agents:{'✓' if HAS_DYNAMIC_AGENTS else '✗'}  (Self-Creating)")
    from middleware import ADMIN_API_KEY, ADMIN_KEY_AUTOGEN
    if ADMIN_KEY_AUTOGEN:
        # DEV-only: in full key đã auto-sinh để dev xài (log cục bộ). KHÔNG bao giờ
        # in key đã cấu hình từ .env (tránh rò qua log container ở prod).
        print(f"  Admin Key:   {ADMIN_API_KEY}  (DEV auto-gen — set ADMIN_API_KEY in .env)")
    elif ADMIN_API_KEY:
        print("  Admin Key:   (configured via .env)")
    else:
        print("  Admin Key:   (NOT SET — admin endpoints disabled)")
    print("  URL:         http://localhost:8360")
    print("=" * 64)
    uvicorn.run(app, host="0.0.0.0", port=8360)
