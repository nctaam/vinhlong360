# -*- coding: utf-8 -*-
"""Dò tính năng TUỲ CHỌN — `HAS_*` + các ký hiệu đi kèm.

Tách khỏi `server.py` (2026-08-27) khi bóc `agent/chat/`. Lý do: cả server LẪN
chat đều đọc những cờ này, nên để chúng ở server.py là buộc chat import ngược
server — vòng. Đây là hạ tầng dùng chung, đúng loại thứ KHÔNG nên chia theo
miền (xem docs/2026-08-27-ban-do-module-de-xuat.md §5).

Mỗi khối giữ nguyên hình dạng `try/except ImportError` cũ: thiếu phụ thuộc tuỳ
chọn thì cờ về False và hệ thống chạy tiếp, không nổ lúc khởi động.
"""
from __future__ import annotations

import os

from middleware import logger  # noqa: F401  (các khối dưới log lúc dò)


# Dời từ server.py cùng đợt bóc chat: cả server lẫn chat đều đọc cờ env.
def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

try:
    from vector_search import embedding_store, hybrid_search  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_VECTOR = True
    logger.info("Vector search enabled")
except ImportError:
    HAS_VECTOR = False
    logger.info("Vector search disabled (optional dependency)")

try:
    from realtime import get_realtime_context, get_weather, get_all_weather, get_upcoming_events, weather_for_llm  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
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
    from autocorrect import autocorrect, load_entity_names  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_AUTOCORRECT = True
except ImportError:
    HAS_AUTOCORRECT = False

try:
    from recommender import recommend  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_RECOMMENDER = True
except ImportError:
    HAS_RECOMMENDER = False

try:
    from freshness import check_freshness, freshness_report, auto_refresh_candidates  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_FRESHNESS = True
except ImportError:
    HAS_FRESHNESS = False

try:
    from image_recognition import process_upload, recognize_image  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_IMAGE_RECOGNITION = True
except ImportError:
    HAS_IMAGE_RECOGNITION = False

try:
    from metrics import generate_metrics, track_chat_request, track_tool_call, track_cache, track_feedback, track_feedback_attempt, track_error, set_gauge, track_http_request  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_METRICS = True
except ImportError:
    HAS_METRICS = False

try:
    from ab_testing import ab_manager  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
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
    from memory_graph import memory_graph  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_MEMORY_GRAPH = True
except ImportError:
    HAS_MEMORY_GRAPH = False

try:
    from tracing import tracer, trace_chat_request, trace_tool_call, trace_llm_call, trace_rag_retrieval, get_trace_summary, export_traces_json  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_TRACING = True
except ImportError:
    HAS_TRACING = False

try:
    from contextual_retrieval import contextual, bm25, enhanced_hybrid_search  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_CONTEXTUAL = True
except ImportError:
    HAS_CONTEXTUAL = False

try:
    import kb_context  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_KB_CONTEXT = True
except ImportError:
    HAS_KB_CONTEXT = False

try:
    import experience_memory  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_EXPERIENCE = True
except ImportError:
    HAS_EXPERIENCE = False

try:
    import prompt_compiler  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_FEWSHOT = True
except ImportError:
    HAS_FEWSHOT = False

try:
    from checkpoints import checkpoint_manager, confirmation_manager, needs_confirmation, format_confirmation_prompt  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    HAS_CHECKPOINTS = True
except ImportError:
    HAS_CHECKPOINTS = False

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
    from semantic_cache import multi_tier_cache, semantic_get_async, semantic_put, semantic_take_dedup_lease, cache_stats as semantic_cache_stats, cache_warmer  # noqa: F401 (feature-probe try-import — HAS_* dùng runtime)
    from semantic_cache import semantic_abandon  # noqa: F401  (dò tính năng — tái xuất cho server/chat)
    HAS_SEMANTIC_CACHE = True
except ImportError:
    HAS_SEMANTIC_CACHE = False

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
