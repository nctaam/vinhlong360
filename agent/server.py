"""
vinhlong360 — Knowledge Agent Server (v3 — Production).

FastAPI server cung cấp:
  POST /chat          — chat endpoint (JSON) + rate limiting
  POST /chat/stream   — SSE streaming chat + rate limiting
  POST /reload        — hot-reload data + cache invalidation + rebuild index
  GET  /health        — health check + cache stats + response times
  GET  /              — trang chat
  /admin/*            — Admin API (CRUD, review, analytics, trigger-learn)
  /analytics/*        — Analytics dashboard data
  /system/*           — System monitoring (logs, rate limits, errors)

Chạy:
  pip install -r requirements.txt
  python agent/server.py           # lắng nghe BIND_HOST:AGENT_PORT (mặc định 127.0.0.1:8360)
"""

import json
import os
import re
import sys
import time
import traceback
import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from runtime_ports import resolve_port

BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")
# Cổng lắng nghe: mặc định 8360 = y hệt trước khi tham số hoá. Env chỉ cần khi
# chạy nhiều bản (dongthap360, cantho360…) trên cùng một máy — xem runtime_ports.
AGENT_PORT = resolve_port("AGENT_PORT", 8360)




# Vùng dò tính năng đã sang agent/features.py (đợt bóc chat 2026-08-27).
from features import _env_bool
from features import (
    HAS_AB_TESTING,
    HAS_AUTOCORRECT,
    HAS_CHECKPOINTS,
    HAS_CIRCUIT_BREAKER,
    HAS_CONTEXTUAL,
    HAS_COST_TRACKER,
    HAS_DYNAMIC_AGENTS,
    HAS_EVAL,
    HAS_EXPERIENCE,
    HAS_FEWSHOT,
    HAS_FRESHNESS,
    HAS_GUARDRAILS,
    HAS_IMAGE_RECOGNITION,
    HAS_KB_CONTEXT,
    HAS_LLM_JUDGE,
    HAS_MEMORY_GRAPH,
    HAS_METRICS,
    HAS_OPTIMIZER,
    HAS_ORCHESTRATOR,
    HAS_PARALLEL,
    HAS_PROMPT_CACHE,
    HAS_REALTIME,
    HAS_RECOMMENDER,
    HAS_SEMANTIC_CACHE,
    HAS_TRACING,
    HAS_VECTOR,
    ab_manager,
    agent_factory,
    all_breaker_stats,
    autocorrect,
    bm25,
    check_input,  # noqa: F401  (be mat va cua test — llmops sang goi rieng 2026-08-27)
    confirmation_manager,
    contextual,
    cost_attribution,  # noqa: F401  (be mat va cua test — llmops sang goi rieng 2026-08-27)
    embedding_store,
    enhanced_hybrid_search,
    experience_memory,
    format_confirmation_prompt,
    generate_metrics,
    get_all_weather,
    get_upcoming_events,
    get_weather,
    guardrail_budget,  # noqa: F401  (be mat va cua test — llmops sang goi rieng 2026-08-27)
    kb_context,
    load_entity_names,
    memory_graph,  # noqa: F401  (be mat va cua test — llmops sang goi rieng 2026-08-27)
    multi_tier_cache,  # noqa: F401  (be mat va cua test — llmops sang goi rieng 2026-08-27)
    process_upload,
    prompt_cache,
    prompt_compiler,
    recognize_image,
    recommend,
    semantic_cache_stats,
    set_gauge,
    track_feedback_attempt,
    track_http_request,
)


BUILD_SEARCH_INDEXES = _env_bool("BUILD_SEARCH_INDEXES", True)
BACKGROUND_INDEX_BUILD = _env_bool("BACKGROUND_INDEX_BUILD", True)
# GĐ4.4: LLM Judge tốn nguyên 1 lượt LLM/chat cho telemetry -> mặc định TẮT (bật khi cần đo).

import analytics  # noqa: F401  (be mat va cua test — llmops sang goi rieng 2026-08-27)
import cache
import knowledge
from admin import router as admin_router
from identity.api import router as auth_router
from notifications import router as community_router
from public_api import router as public_router
from cases.public_api import case_public_router
from cases.admin_api import case_admin_router
import public_api as _public_api
from saved import router as saved_router
from plans import router as plans_router, public_router as plans_public_router
from visits import router as visits_router
from achievements import router as achievements_router
from seo import router as seo_router
from community.api import router as social_router
from launch_policy_api import router as launch_policy_router
from launch_policy_api import validate_sitemap_bundle_on_startup
from middleware import (
    logger, chat_limiter, report_limiter,
    feedback_ip_limiter, feedback_owner_limiter,
    response_tracker, error_tracker, generate_request_id, get_client_ip,
)
from policy_http import PolicyHttpMiddleware
from scheduler import start_scheduler, stop_scheduler, scheduler_status
from chat_identity import resolve_chat_owner, set_chat_owner_cookie
from feedback_policy import (
    FeedbackRejected,
    FeedbackUnavailable,
    consume_feedback_receipt,
)
from memory import memory_manager
from reflexion import reflexion_engine, quality_tracker  # noqa: F401  (be mat va cua test — llmops sang goi rieng 2026-08-27)
from proactive import generate_welcome_message




















# ── Level 6 modules ──


from privacy_boundary import (
    privacy_boundary_readiness,
)
















# ── Level 7 modules ──



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







# ── Tool dispatcher ──









# ── Tool helpers (tách để complexity ≤12, extract-verbatim) ──
























































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
    validate_sitemap_bundle_on_startup(app)
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

# ── Bóc chat (2026-08-27) ─────────────────────────────────────
# `chat`/`chat_stream` + 106 ký hiệu phụ trợ đã sang `agent/chat/`; vùng dò
# tính năng sang `agent/features.py`; `_error_response` sang `agent/http_errors.py`.
# Ranh giới TÍNH ĐƯỢC: bao đóng bắc cầu từ 5 hạt giống, kiểm chéo 0 rò rỉ.
# Xem docs/2026-08-27-ban-do-module-de-xuat.md.
from http_errors import _error_response  # noqa: F401  (14 nơi trong file này dùng)


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
    allow_headers=["Content-Type", "X-Admin-Key", "Authorization", "X-CSRF-Token", "Idempotency-Key", "X-Case-CSRF"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


def _merge_vary_header(response, *members: str) -> None:
    """Merge Vary members case-insensitively without duplicate directives."""
    existing = []
    for name, value in getattr(response, "raw_headers", []):
        if name.lower() == b"vary":
            existing.extend(value.decode("latin-1").split(","))
    existing.extend(response.headers.get("Vary", "").split(","))
    existing.extend(members)

    merged = []
    seen = set()
    for member in existing:
        normalized = member.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)

    response.raw_headers = [
        (name, value)
        for name, value in getattr(response, "raw_headers", [])
        if name.lower() != b"vary"
    ]
    if merged:
        response.headers["Vary"] = ", ".join(merged)


def _apply_final_cache_policy(request, response) -> None:
    """Apply the last cache classification after endpoint processing."""
    path = request.url.path
    if not path.startswith(("/api/", "/admin/", "/auth/")):
        return

    _merge_vary_header(response, "Authorization", "Cookie", "Accept")
    if path.startswith("/api/") and getattr(
        request.state, "authenticated_user_id", None
    ):
        response.headers["Cache-Control"] = "private, no-store"


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
    if request.method == "GET" and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "private, max-age=30"
    # Finalize after endpoint headers are known so personalized API data cannot
    # retain an endpoint-provided public cache classification.
    _apply_final_cache_policy(request, response)
    return response




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
# Mien ENTITY sang agent/entities/ (2026-08-28). KHONG include_router rieng o
# day:  da GOP san route entity (xem cuoi public_api.py).
# Gan ca hai la dang ky TRUNG — do duoc 455 route thay vi 433, 17 ban trung.
# Flag-gated: every route answers 404 capability_unavailable while the case
# flags are off, so mounting it is inert until rollout is explicit.
# Chat: gói riêng từ 2026-08-27 (agent/chat/). Ranh giới TÍNH ĐƯỢC bằng bao
# đóng bắc cầu, kiểm chéo 0 rò rỉ — xem docs/2026-08-27-ban-do-module-de-xuat.md.
# LLM-ops: goi rieng tu 2026-08-27 (lat thu hai, sau chat/) — 42 route /system
# /checkpoints /vectors /freshness /analytics. Xem agent/llmops/api.py.
from llmops.api import router as llmops_router  # noqa: E402
from chat.api import router as chat_router  # noqa: E402
# TÁI XUẤT cho tương thích ngược: bộ test hiện có gọi qua `server.<tên>`, và
# giữ chúng NGUYÊN VĂN chính là lưới kiểm chứng của cú dời này — sửa test cho
# khớp bản vá thì mất chỗ dựa để nói "hành vi không đổi".
from chat.api import (  # noqa: E402,F401
    ChatRequest,
    _build_messages,
    _call_stream_decision,
    _execute_pending_calls,
    _issue_delivered_feedback_receipt,
    _prepare_pending_calls,
    _run_agent,
    _run_agent_orchestrated,
    _safe_tool_result,
    _sanitize_message,
    _search_card_practical,
    _search_result_card,
    call_tool,
    chat,
    chat_stream,
)

app.include_router(chat_router)
app.include_router(llmops_router)

app.include_router(case_public_router)
app.include_router(case_admin_router)
# The kernel's composition root: with the flag off this is a no-op and every
# case route stays a clean 404. With it on, every case module is configured
# against the live database — or none are, and the reason is in the log.
from cases.wiring import wire_case_kernel  # noqa: E402
from config import settings as _case_settings  # noqa: E402
from database import db as _case_db  # noqa: E402

wire_case_kernel(_case_db, _case_settings)
app.include_router(saved_router)
app.include_router(plans_router)
app.include_router(plans_public_router)
app.include_router(visits_router)
app.include_router(achievements_router)
app.include_router(seo_router)
app.include_router(social_router)
app.include_router(community_router)
app.include_router(launch_policy_router)


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
                "/api/cases",
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


# Registered after every decorator middleware so policy headers remain final.
app.add_middleware(PolicyHttpMiddleware, route_resolver=app.router)


from pydantic import ConfigDict, Field, ValidationError, field_validator















# ── Pydantic models for validated POST endpoints ──

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








































































# Orchestrator singleton (lazy init)























# ── SSE Streaming ──



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
        # GĐ11.4: toàn bộ phần nặng (reload DB + rebuild index) chạy trong thread
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


def _erasure_readiness(erasure_status: dict, schema: dict) -> dict:
    """Khối `erasure_scheduler` của /ready.

    Tách ra mức module để KIỂM ĐƯỢC: bản cũ nằm trong closure `_probe()` của
    route nên test duy nhất canh nó là test SO CHUỖI trên mã nguồn.

    `ok` GIỮ NGUYÊN nghĩa cũ có chủ đích. Chế độ chỉ-đếm là mặc định AN TOÀN cho
    giai đoạn chưa có người dùng thật; lật /ready đỏ vì nó là chặn deploy của một
    cấu hình cố ý, và đó là quyết định của chủ dự án chứ không phải của cổng.

    Cái thiếu không phải mức độ nghiêm mà là KHẢ KIẾN: `overdue_count` — số hồ sơ
    ĐÃ QUÁ HẠN xoá mà chưa xoá — vốn có sẵn trong `_ERASURE_STATUS` nhưng không
    được chiếu ra /ready. Người dùng được hứa "xoá vĩnh viễn sau N ngày"
    (agent/auth.py), tác vụ chạy 288 lần/ngày và lần nào cũng thoát trước vòng
    xoá, mà không dấu hiệu nào lộ ra ngoài. Nay con số đó nằm trên /ready, và
    `state` gọi đúng tên trạng thái đáng lo:
        ready                    — đang xoá thật
        audit_only               — chỉ đếm, chưa hồ sơ nào quá hạn
        audit_only_with_overdue  — chỉ đếm, VÀ đã có hồ sơ quá hạn lời hứa
    """
    audit_only = bool(erasure_status.get("audit_only", True))
    try:
        overdue = int(erasure_status.get("overdue_count") or 0)
    except (TypeError, ValueError):
        overdue = 0
    if not audit_only:
        state = "ready"
    elif overdue > 0:
        state = "audit_only_with_overdue"
    else:
        state = "audit_only"
    return {
        "ok": bool(schema.get("ok")) and "audit_only" in erasure_status,
        "audit_only": audit_only,
        "overdue_count": overdue,
        "state": state,
        "schema_version": schema.get("schema_version"),
        "required_schema_version": schema.get("required_schema_version"),
    }


@app.get("/health/ready")
async def readiness_probe():
    """Lightweight readiness probe for load balancers / orchestrators."""
    def _probe():
        from config import settings as _settings, _is_individual_actor_ref
        from data_lifecycle import lifecycle_registry_readiness
        from database import db as _db
        from privacy_policy import privacy_policy_readiness
        from cases.policy import load_case_policy
        from database import case_kernel_schema_status
        data_source = getattr(knowledge, "_data_source", None) or "unknown"
        entity_count = len(getattr(knowledge, "_entities", None) or {})
        checks = {
            "knowledge": entity_count > 0,
            "data_source": data_source == "db" if getattr(_db, "_use_pg", False) else data_source in {"db", "json"},
            "privacy_policy": privacy_policy_readiness(_settings),
            "privacy_boundary": privacy_boundary_readiness(),
        }
        checks["lifecycle_registry"] = lifecycle_registry_readiness()
        try:
            with _db._conn() as conn:
                _db._fetchone(conn, "SELECT 1", ())
            checks["database"] = True
        except Exception:
            checks["database"] = False
        schema = _db.pg_schema_status()
        checks["schema"] = bool(schema.get("ok"))
        checks["schema_version"] = schema
        case_enabled = any((
            _settings.CASE_KERNEL_ENABLED,
            _settings.CORRECTION_INTAKE_ENABLED,
            _settings.CORRECTION_ADMIN_ENABLED,
            _settings.CORRECTION_ASSISTED_ENABLED,
            _settings.CORRECTION_PUBLICATION_ENABLED,
        ))
        checks["case_kernel_schema"] = case_kernel_schema_status(schema, enabled=case_enabled)
        if not case_enabled:
            checks["case_policy"] = {"ok": True, "state": "dormant", "code": "case_policy_dormant"}
            checks["case_kernel_key"] = {"ok": True, "state": "dormant", "code": "case_kernel_key_dormant"}
            checks["case_owner"] = {"ok": True, "state": "dormant", "code": "case_owner_dormant"}
        else:
            from cases.security import validate_case_encryption_key
            try:
                validate_case_encryption_key(_settings.CASE_KERNEL_ENCRYPTION_KEY)
                key_valid = True
            except Exception:
                key_valid = False
            checks["case_kernel_key"] = (
                {"ok": True, "state": "ready", "code": "case_kernel_key_ready"}
                if key_valid
                else {"ok": False, "state": "blocked", "code": "case_encryption_key_required"}
            )
            checks["case_owner"] = (
                {"ok": True, "state": "ready", "code": "case_owner_ready"}
                if _is_individual_actor_ref(_settings.CASE_SERVICE_OWNER_REF)
                else {"ok": False, "state": "blocked", "code": "case_owner_individual_required"}
            )
            try:
                load_case_policy()
                checks["case_policy"] = {"ok": True, "state": "ready", "code": "case_policy_ready"}
            except Exception:
                checks["case_policy"] = {"ok": False, "state": "blocked", "code": "case_policy_invalid"}
        erasure_status = scheduler_status().get("erasure", {})
        checks["erasure_scheduler"] = _erasure_readiness(erasure_status, schema)
        return checks
    checks = await asyncio.to_thread(_probe)
    ready = all(
        value.get("ok", False)
        if isinstance(value, dict) and "ok" in value
        else bool(value)
        for key, value in checks.items()
        if key != "schema_version"
    )
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
    knowledge._ensure()
    set_gauge("cache_size", len(cache._cache) if hasattr(cache, '_cache') else 0)
    set_gauge("entities_total", len(knowledge._entities or {}))
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











# ── System monitoring endpoints ──























# ── Checkpoint / Confirmation endpoints ──







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


@app.post("/feedback")
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




@app.get("/welcome")
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


# ── Vector search endpoints ──





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




# ── Cost tracker ──





# ── Eval framework ──




# ── Self optimizer ──



# ── Semantic cache ──




# ════════════════════════════════════════════════════════════════
# Level 7 endpoints
# ════════════════════════════════════════════════════════════════

# ── LLM Judge ──




# ── Dynamic agents ──




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
.feedback-row button:disabled { opacity: .55; cursor: wait; }
.feedback-status { color: #66746e; font-size: .8rem; align-self: center; }
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
  try{
    const response=await fetch('/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({message:text,history:history.slice(-20)})});const reader=response.body.getReader();
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
            showFeedback(msgDiv,data.feedback_receipt,(rating,selected,other)=>sendFeedback(data.feedback_receipt,rating,selected,other));
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
function showFeedback(msgDiv,receipt,submitFeedback){
  if(!receipt)return;
  const row=document.createElement('div');row.className='feedback-row';
  const up=document.createElement('button');up.textContent='👍 Hữu ích';
  const down=document.createElement('button');down.textContent='👎 Chưa tốt';
  up.onclick=()=>submitFeedback(1,up,down);
  down.onclick=()=>submitFeedback(0,down,up);
  row.appendChild(up);row.appendChild(down);msgDiv.appendChild(row);
}
async function sendFeedback(receipt,rating,selected,other){
  selected.disabled=true;other.disabled=true;
  try{
    const response=await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({receipt:receipt,rating:rating})});
    if(!response.ok)throw new Error('feedback unavailable');
    selected.classList.add('voted');other.style.display='none';
  }catch(_error){
    selected.disabled=false;other.disabled=false;
    let status=selected.parentNode.querySelector('.feedback-status');
    if(!status){status=document.createElement('span');status.className='feedback-status';selected.parentNode.appendChild(status);}
    status.textContent='Chưa thể ghi nhận. Vui lòng thử lại.';
  }
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
    print(f"  URL:         http://localhost:{AGENT_PORT}")
    print("=" * 64)
    uvicorn.run(app, host=BIND_HOST, port=AGENT_PORT)
