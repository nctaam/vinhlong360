# -*- coding: utf-8 -*-
"""Mặt LLM-ops — bóc khỏi `server.py` (2026-08-27, lát thứ hai sau `chat/`).

42 route `/system/*` `/checkpoints` `/vectors` `/freshness` `/analytics`: chi
phí, học máy, guardrail, eval, judge, cache ngữ nghĩa, A/B, checkpoint. Cả một
mặt vận hành LLM không liên quan gì tới việc khởi động app — nhưng ai sửa route
bất kỳ cũng phải mở file chứa nó.

Ranh giới TÍNH bằng bao đóng bắc cầu (như `chat/`): 47 ký hiệu / 517 dòng,
kiểm chéo 0 rò rỉ. Đo trước bằng phép đo ROADMAP §45.2: chỉ 2 điểm vá test —
lát rẻ nhất trong các ứng viên.

Theo khuôn `agent/cases/`: gói theo MIỀN, phát `APIRouter`, server chỉ
`include_router`.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

import analytics
import knowledge
from http_errors import _error_response
from memory import memory_manager
from middleware import error_tracker, logger, response_tracker
from reflexion import quality_tracker, reflexion_engine
from scheduler import scheduler_status

from features import (
    HAS_AB_TESTING,
    HAS_CHECKPOINTS,
    HAS_CIRCUIT_BREAKER,
    HAS_CONTEXTUAL,
    HAS_COST_TRACKER,
    HAS_DYNAMIC_AGENTS,
    HAS_EVAL,
    HAS_FRESHNESS,
    HAS_GUARDRAILS,
    HAS_IMAGE_RECOGNITION,
    HAS_LLM_JUDGE,
    HAS_MEMORY_GRAPH,
    HAS_OPTIMIZER,
    HAS_ORCHESTRATOR,
    HAS_PROMPT_CACHE,
    HAS_SEMANTIC_CACHE,
    HAS_TRACING,
    HAS_VECTOR,
    ab_manager,
    agent_factory,
    all_breaker_stats,
    auto_refresh_candidates,
    check_freshness,
    check_input,
    checkpoint_manager,
    confirmation_manager,
    cost_attribution,
    cost_budget,
    embedding_store,
    enhanced_hybrid_search,
    export_traces_json,
    format_confirmation_prompt,
    freshness_report,
    get_agent_report,
    get_cost_report,
    get_judge_report,
    get_latest_report,
    get_optimization_report,
    get_report_history,
    get_trace_summary,
    guardrail_budget,
    handoff_log,
    injection_detector,
    judge,
    memory_graph,
    multi_tier_cache,
    process_upload,
    prompt_cache,
    recognize_image,
    semantic_cache_stats,
)

_ADMIN_PREFIXES = (
    "/analytics", "/system", "/checkpoints", "/vectors", "/freshness",
    "/ab-testing", "/prompt-cache", "/confirmations", "/confirm/", "/reject/",
    "/image/",
)
_SCOPED_PATHS = {"/system/learning/run", "/system/client-errors", "/vectors/build",
                 "/vectors/search", "/system/dynamic-agents/create", "/image/recognize"}


async def _llmops_require_admin(request: Request) -> None:
    """Route dependency for admin auth; mark the request for handler reuse."""
    from admin import require_admin

    await require_admin(request)
    request.state._llmops_auth_applied = True


async def _llmops_require_admin_scope(request: Request) -> None:
    """Route dependency for the shared deployment scope."""
    from admin import require_admin_scope

    await require_admin_scope(request, "ops.deploy")
    request.state._llmops_auth_applied = True


async def _require_admin_once(request: Request, scope: str | None = None) -> None:
    """Keep direct handler calls safe without repeating dependency side effects."""
    if getattr(getattr(request, "state", None), "_llmops_auth_applied", False):
        return
    if scope:
        from admin import require_admin_scope

        await require_admin_scope(request, scope)
    else:
        from admin import require_admin

        await require_admin(request)
    if hasattr(request, "state"):
        request.state._llmops_auth_applied = True


class _AdminMetadataRouter(APIRouter):
    """Attach auth dependencies and machine-readable metadata to admin routes."""

    def add_api_route(self, path: str, endpoint, **kwargs):
        if path.startswith(_ADMIN_PREFIXES):
            extra = dict(kwargs.pop("openapi_extra", {}) or {})
            methods = kwargs.get("methods") or set()
            is_mutation = any(method in methods for method in ("POST", "PUT", "PATCH", "DELETE"))
            extra.update({"x-auth": "admin-key", "x-csrf": is_mutation})
            if path in _SCOPED_PATHS:
                extra["x-scope"] = "ops.deploy"
            kwargs["openapi_extra"] = extra
            dependencies = list(kwargs.pop("dependencies", []) or [])
            auth_dependency = (
                _llmops_require_admin_scope if path in _SCOPED_PATHS
                else _llmops_require_admin
            )
            kwargs["dependencies"] = [Depends(auth_dependency), *dependencies]
        return super().add_api_route(path, endpoint, **kwargs)


router = _AdminMetadataRouter()


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


@router.get("/analytics/summary")
async def analytics_summary(request: Request):
    await _require_admin_once(request)
    try:
        return await asyncio.to_thread(analytics.get_summary)
    except Exception:
        raise HTTPException(503, detail="Analytics data unavailable")


@router.get("/analytics/popular")
async def analytics_popular(request: Request, limit: int = Query(20, ge=1, le=200)):
    await _require_admin_once(request)
    return {"popular_queries": await asyncio.to_thread(analytics.get_popular_queries, limit)}


@router.get("/analytics/gaps")
async def analytics_gaps(request: Request, limit: int = Query(20, ge=1, le=200)):
    await _require_admin_once(request)
    return {"knowledge_gaps": await asyncio.to_thread(analytics.get_knowledge_gaps, limit)}


@router.get("/analytics/daily")
async def analytics_daily(request: Request, days: int = Query(30, ge=1, le=365)):
    await _require_admin_once(request)
    return {"daily_stats": await asyncio.to_thread(analytics.get_daily_stats, days)}


@router.get("/analytics/top-entities")
async def analytics_top_entities(request: Request, limit: int = Query(20, ge=1, le=200)):
    await _require_admin_once(request)
    return {"top_entities": await asyncio.to_thread(analytics.get_top_entities, limit)}


@router.get("/system/logs")
async def system_logs(request: Request, limit: int = Query(50, ge=1, le=500), level: str = None):
    await _require_admin_once(request)
    return {"logs": logger.recent(limit, level)}


@router.get("/system/errors")
async def system_errors(request: Request, limit: int = Query(20, ge=1, le=200)):
    await _require_admin_once(request)
    return {"errors": error_tracker.recent_errors(limit), **error_tracker.stats()}


@router.get("/system/response-times")
async def system_response_times(request: Request):
    await _require_admin_once(request)
    return response_tracker.stats()


@router.get("/system/scheduler")
async def system_scheduler(request: Request):
    await _require_admin_once(request)
    return scheduler_status()


@router.get("/system/learning", tags=["System"])
async def system_learning(request: Request):
    """Trạng thái vòng lặp tự học. Admin-only."""
    await _require_admin_once(request)
    try:
        from learn_loop import learning_status
        return learning_status()
    except ImportError:
        raise HTTPException(503, detail="learn_loop module not available")


@router.post("/system/learning/run", tags=["System"])
async def trigger_learning(request: Request):
    """Trigger 1 vòng lặp tự học SAU cổng fitness (admin only, eval-gated)."""
    await _require_admin_once(request, "ops.deploy")
    try:
        from self_evolve import guarded_evolve
        from learn_loop import run_full_cycle
        summary = guarded_evolve("learning-loop(manual)", lambda: run_full_cycle(dry_run=False))
        return {"status": "completed", "decision": summary["decision"],
                "reason": summary["reason"], "before": summary["before"], "after": summary["after"]}
    except Exception as e:
        logger.error("learning-loop error: %s", e)
        return _error_response(500, "Internal server error")


@router.get("/system/self-evolution", tags=["System"])
async def system_self_evolution(request: Request):
    """Trạng thái cơ chế tự tiến hoá. Admin-only."""
    await _require_admin_once(request)
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


@router.get("/system/memory")
async def system_memory(request: Request):
    await _require_admin_once(request)
    return memory_manager.stats()


@router.get("/system/traces", tags=["System"])
async def system_traces(request: Request, limit: int = Query(50, ge=1, le=500)):
    """OpenTelemetry trace data. Admin-only."""
    await _require_admin_once(request)
    if not HAS_TRACING:
        return {"available": False}
    return {
        "available": True,
        "summary": get_trace_summary(),
        "traces": export_traces_json(limit),
    }


@router.get("/system/handoffs", tags=["System"])
async def system_handoffs(request: Request, limit: int = Query(50, ge=1, le=200)):
    """Multi-agent orchestrator handoff log. Admin-only."""
    await _require_admin_once(request)
    if not HAS_ORCHESTRATOR:
        return {"available": False}
    from dataclasses import asdict
    records = handoff_log.recent(limit)
    return {
        "available": True,
        "handoffs": [asdict(r) for r in records],
        "stats": handoff_log.stats(),
    }


@router.get("/system/memory-graph", tags=["System"])
async def system_memory_graph(request: Request):
    """Memory graph statistics. Admin-only."""
    await _require_admin_once(request)
    if not HAS_MEMORY_GRAPH:
        return {"available": False}
    graph_stats = memory_graph.stats()
    return {
        "available": True,
        **graph_stats,
        "patterns": memory_graph.get_emerging_patterns()[:10],
    }


@router.get("/checkpoints/{session_id}", tags=["System"])
async def list_checkpoints(session_id: str, request: Request):
    """List conversation checkpoints. Admin-only."""
    await _require_admin_once(request)
    if not HAS_CHECKPOINTS:
        return {"available": False}
    return {"checkpoints": checkpoint_manager.list_checkpoints(session_id)}


@router.post("/checkpoints", tags=["System"])
async def save_checkpoint(req: CheckpointSaveRequest, request: Request):
    """Save a conversation checkpoint. Admin-only."""
    await _require_admin_once(request)
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


@router.post("/checkpoints/{checkpoint_id}/resume", tags=["System"])
async def resume_checkpoint(checkpoint_id: str, request: Request):
    """Resume from a conversation checkpoint. Admin-only."""
    await _require_admin_once(request)
    if not HAS_CHECKPOINTS:
        return _error_response(501, "Checkpoints not available")
    result = checkpoint_manager.resume_from(checkpoint_id)
    if result is None:
        return _error_response(404, "Checkpoint not found")
    messages, agent_state = result
    return {"messages": messages, "agent_state": agent_state}


@router.get("/system/quality")
async def system_quality(request: Request):
    await _require_admin_once(request)
    return {
        "quality": quality_tracker.stats(),
        "reflexion": reflexion_engine.stats(),
    }


@router.get("/system/client-errors", tags=["System"])
async def system_client_errors(request: Request, limit: int = Query(50, ge=1, le=500)):
    """Admin xem lỗi frontend gần đây (lọc source=client từ StructuredLogger).
    Gate bằng admin key (giống các /system/* khác ở production)."""
    await _require_admin_once(request, "ops.deploy")
    limit = max(1, min(limit, 200))
    rows = logger.recent(limit * 4, level="error")
    client_rows = [r for r in rows if r.get("source") == "client"]
    return {"errors": client_rows[-limit:], "count": len(client_rows[-limit:])}


@router.post("/vectors/build")
async def build_vectors(request: Request):
    """Build/rebuild vector embeddings index."""
    # GĐ4.2: rebuild nặng -> chỉ admin (chống DoS compute ẩn danh).
    await _require_admin_once(request, "ops.deploy")
    if not HAS_VECTOR:
        return _error_response(501, "Vector search module not available")
    def _build():
        knowledge._ensure()
        return embedding_store.build_index(knowledge._entities)
    return await asyncio.to_thread(_build)


@router.get("/vectors/stats")
async def vector_stats(request: Request):
    await _require_admin_once(request)
    if not HAS_VECTOR:
        return {"available": False}
    return {"available": True, **embedding_store.stats()}


@router.get("/vectors/search")
async def vector_search_endpoint(request: Request, q: str = Query(..., max_length=200), limit: int = Query(10, ge=1, le=100)):
    await _require_admin_once(request, "ops.deploy")
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


# ── Contextual retrieval endpoint ──
# Về từ server.py (lát 4 đợt hoàn-thiện-sâu 2026-08-29) — cùng loài chẩn đoán
# truy hồi với /vectors/search ngay trên. Chép NGUYÊN VĂN, path giữ nguyên
# (router llmops không prefix); KHÔNG thêm guard — bảo toàn hành vi public,
# câu hỏi require_admin ghi backlog chờ chủ dự án.

@router.get("/search/enhanced", tags=["Search"])
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


@router.get("/freshness/check")
async def freshness_check_endpoint(request: Request):
    await _require_admin_once(request)
    if not HAS_FRESHNESS:
        raise HTTPException(503, detail="Freshness module not available")
    def _check():
        knowledge._ensure()
        return check_freshness(knowledge._entities)
    return await asyncio.to_thread(_check)


@router.get("/freshness/report")
async def freshness_report_endpoint(request: Request):
    await _require_admin_once(request)
    if not HAS_FRESHNESS:
        raise HTTPException(503, detail="Freshness module not available")
    def _report():
        knowledge._ensure()
        return freshness_report(knowledge._entities)
    return {"report": await asyncio.to_thread(_report)}


@router.get("/freshness/candidates")
async def freshness_candidates_endpoint(request: Request, limit: int = Query(20, ge=1, le=200)):
    await _require_admin_once(request)
    if not HAS_FRESHNESS:
        raise HTTPException(503, detail="Freshness module not available")
    def _candidates():
        knowledge._ensure()
        return auto_refresh_candidates(knowledge._entities, limit)
    return {"candidates": await asyncio.to_thread(_candidates)}


@router.get("/system/circuit-breakers")
async def circuit_breaker_stats(request: Request):
    await _require_admin_once(request)
    if not HAS_CIRCUIT_BREAKER:
        return {"available": False}
    return {"available": True, **all_breaker_stats()}


@router.get("/system/guardrails", tags=["Level6"])
async def guardrails_status(request: Request):
    await _require_admin_once(request)
    if not HAS_GUARDRAILS:
        return {"available": False}
    return {
        "available": True,
        "injection_patterns": len(injection_detector._patterns) if hasattr(injection_detector, '_patterns') else 0,
        "budget_sessions": guardrail_budget.get_stats() if hasattr(guardrail_budget, 'get_stats') else {},
    }


@router.post("/system/guardrails/check-input", tags=["Level6"])
async def guardrails_check_input(req: GuardrailCheckRequest, request: Request):
    await _require_admin_once(request)
    if not HAS_GUARDRAILS:
        raise HTTPException(503, detail="Guardrails not available")
    return check_input(req.message, req.session_id)


@router.get("/system/costs", tags=["Level6"])
async def cost_tracker_report(request: Request):
    await _require_admin_once(request)
    if not HAS_COST_TRACKER:
        return {"available": False}
    return {"available": True, **get_cost_report()}


@router.get("/system/costs/session/{session_id}", tags=["Level6"])
async def cost_tracker_session(session_id: str, request: Request):
    await _require_admin_once(request)
    if not HAS_COST_TRACKER:
        raise HTTPException(503, detail="Cost tracker not available")
    return cost_attribution.get_session_cost(session_id)


@router.get("/system/costs/budget", tags=["Level6"])
async def cost_budget_status(request: Request):
    await _require_admin_once(request)
    if not HAS_COST_TRACKER:
        raise HTTPException(503, detail="Cost tracker not available")
    return {
        "daily": cost_budget.check_budget("daily"),
        "monthly": cost_budget.check_budget("monthly"),
    }


@router.get("/system/eval/latest", tags=["Level6"])
async def eval_latest(request: Request):
    await _require_admin_once(request)
    if not HAS_EVAL:
        return {"available": False}
    report = get_latest_report()
    return {"available": True, "report": report}


@router.get("/system/eval/history", tags=["Level6"])
async def eval_history(request: Request, limit: int = Query(10, ge=1, le=100)):
    await _require_admin_once(request)
    if not HAS_EVAL:
        return {"available": False}
    return {"available": True, "reports": get_report_history(limit)}


@router.get("/system/optimizer", tags=["Level6"])
async def optimizer_report(request: Request):
    await _require_admin_once(request)
    if not HAS_OPTIMIZER:
        return {"available": False}
    return {"available": True, **get_optimization_report()}


@router.get("/system/semantic-cache", tags=["Level6"])
async def semantic_cache_status(request: Request):
    await _require_admin_once(request)
    if not HAS_SEMANTIC_CACHE:
        return {"available": False}
    return {"available": True, **semantic_cache_stats()}


@router.post("/system/semantic-cache/invalidate", tags=["Level6"])
async def semantic_cache_invalidate(req: SemanticCacheInvalidateRequest, request: Request):
    await _require_admin_once(request)
    if not HAS_SEMANTIC_CACHE:
        raise HTTPException(503, detail="Semantic cache not available")
    if req.entity_id:
        multi_tier_cache.invalidate_entity(req.entity_id)
        return {"success": True, "invalidated": f"entity:{req.entity_id}"}
    elif req.query:
        multi_tier_cache.invalidate_all_namespaces(req.query)
        return {"success": True, "invalidated": f"query:{req.query[:50]}"}
    raise HTTPException(400, detail="Provide entity_id or query")


@router.get("/system/judge", tags=["Level7"])
async def judge_report(request: Request):
    await _require_admin_once(request)
    if not HAS_LLM_JUDGE:
        return {"available": False}
    return {"available": True, **get_judge_report()}


@router.post("/system/judge/evaluate", tags=["Level7"])
async def judge_evaluate(req: JudgeEvaluateRequest, request: Request):
    await _require_admin_once(request)
    if not HAS_LLM_JUDGE:
        raise HTTPException(503, detail="LLM Judge not available")
    result = judge(req.query, req.reply)
    return result


@router.get("/system/dynamic-agents", tags=["Level7"])
async def dynamic_agents_report(request: Request):
    await _require_admin_once(request)
    if not HAS_DYNAMIC_AGENTS:
        return {"available": False}
    return {"available": True, **get_agent_report()}


@router.post("/system/dynamic-agents/create", tags=["Level7"])
async def dynamic_agents_create(req: DynamicAgentCreateRequest, request: Request):
    # P0-12: chặn tạo agent không-auth (system_prompt_addon + tool_whitelist do client kiểm
    # soát → prompt-injection/đốt LLM budget nếu mở). Bắt buộc X-Admin-Key.
    await _require_admin_once(request, "ops.deploy")
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


# ── A/B Testing endpoints (server.py về nhà 2026-08-29, lát 9 — cùng họ
#    42 route /system: mặt vận hành LLM admin-gated, module nguồn ab_testing.py) ──

@router.get("/ab-testing/experiments", tags=["System"])
async def ab_experiments(request: Request):
    """List all A/B testing experiments. Admin-only."""
    await _require_admin_once(request)
    if not HAS_AB_TESTING:
        raise HTTPException(503, detail="A/B testing not available")
    return {"experiments": ab_manager.list_experiments()}

@router.get("/ab-testing/results/{experiment_name}", tags=["System"])
async def ab_results(experiment_name: str, request: Request):
    """Get A/B test results with statistics. Admin-only."""
    await _require_admin_once(request)
    if not HAS_AB_TESTING:
        raise HTTPException(503, detail="A/B testing not available")
    results = ab_manager.get_results(experiment_name)
    significance = ab_manager.is_significant(experiment_name)
    return {"experiment": experiment_name, "results": results, "significance": significance}

@router.get("/prompt-cache/stats", tags=["System"])
async def prompt_cache_stats(request: Request):
    """Get prompt cache statistics. Admin-only."""
    await _require_admin_once(request)
    if not HAS_PROMPT_CACHE:
        return {"available": False}
    return {"available": True, **prompt_cache.stats()}


# ── Checkpoint / Confirmation endpoints (server.py về nhà 2026-08-29, lát 9 —
#    anh em /checkpoints/* ngay trên, cùng module nguồn checkpoints.py) ──

@router.get("/confirmations/{session_id}", tags=["System"])
async def pending_confirmations(session_id: str, request: Request):
    """List pending confirmations. Admin-only."""
    await _require_admin_once(request)
    if not HAS_CHECKPOINTS:
        return {"available": False}
    pending = confirmation_manager.get_pending(session_id)
    return {"pending": [{"id": p.confirmation_id, "action_type": p.action_type,
                         "description": p.description, "prompt": format_confirmation_prompt(p)}
                        for p in pending]}


@router.post("/confirm/{confirmation_id}", tags=["System"])
async def confirm_action(confirmation_id: str, request: Request):
    """Confirm a pending action. Admin-only."""
    await _require_admin_once(request)
    if not HAS_CHECKPOINTS:
        return _error_response(501, "Checkpoints not available")
    params = confirmation_manager.confirm(confirmation_id)
    if params is None:
        return _error_response(404, "Confirmation not found or expired")
    return {"confirmed": True, "params": params}


@router.post("/reject/{confirmation_id}", tags=["System"])
async def reject_action(confirmation_id: str, request: Request):
    """Reject a pending action. Admin-only."""
    await _require_admin_once(request)
    if not HAS_CHECKPOINTS:
        return _error_response(501, "Checkpoints not available")
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    reason = body.get("reason", "")
    confirmation_manager.reject(confirmation_id, reason)
    return {"rejected": True}


# ── Image recognition endpoint (server.py về nhà 2026-08-29, lát 9 — một lượt
#    LLM vision/call, require_admin_scope('ops.deploy') y hệt /vectors/build) ──

@router.post("/image/recognize")
async def image_recognize_endpoint(request: Request):
    # GĐ4.2: mỗi call là 1 lượt LLM vision (tốn tiền) -> chỉ admin để chặn drain ví ẩn danh.
    # (Frontend hiện không dùng. Mở cho user đã xác thực + rate-limit khi cần — Backlog.)
    await _require_admin_once(request, "ops.deploy")
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
