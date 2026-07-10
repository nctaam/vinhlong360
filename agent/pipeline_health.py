"""
vinhlong360 — Unified Pipeline Health Check.

Aggregates health probes from all AI pipeline subsystems into
a single status report. Used by /health endpoint and monitoring.
"""

import logging
import time

logger = logging.getLogger(__name__)


def _run_probe(report: dict, degraded: list, name: str, fn) -> None:
    """Run a single health probe, recording its result and degradation."""
    try:
        result = fn()
        report["subsystems"][name] = result
        if result.get("status") not in ("ok", None):
            degraded.append(name)
    except Exception as exc:
        logger.warning("Health probe %s failed: %s", name, exc)
        report["subsystems"][name] = {"status": "error", "error": str(exc)}
        degraded.append(name)


def _probe_knowledge(probe) -> None:
    """Probe the knowledge layer subsystem."""
    try:
        from knowledge import health_check as kb_health
        probe("knowledge", kb_health)
    except ImportError:
        pass


def _probe_search(probe) -> None:
    """Probe the search pipeline subsystem."""
    try:
        from contextual_retrieval import search_health
        probe("search", search_health)
    except ImportError:
        pass


def _probe_circuit_breakers(probe) -> None:
    """Probe the circuit breaker subsystems (LLM, weather, web)."""
    try:
        from circuit_breaker import llm_breaker, weather_breaker, web_search_breaker
        probe("circuit_breaker_llm", lambda: {
            "status": "ok" if llm_breaker.is_healthy else "degraded",
            **llm_breaker.stats(),
        })
        probe("circuit_breaker_weather", lambda: {
            "status": "ok" if weather_breaker.is_healthy else "degraded",
            **weather_breaker.stats(),
        })
        probe("circuit_breaker_web", lambda: {
            "status": "ok" if web_search_breaker.is_healthy else "degraded",
            **web_search_breaker.stats(),
        })
    except ImportError:
        pass


def _probe_memory(probe) -> None:
    """Probe the memory subsystem."""
    try:
        from memory import memory_health_check
        probe("memory", memory_health_check)
    except ImportError:
        pass


def _probe_cache(probe) -> None:
    """Probe the cache subsystem."""
    try:
        from cache import cache_health_check
        probe("cache", cache_health_check)
    except ImportError:
        pass


def _probe_guardrails(probe) -> None:
    """Probe the guardrails subsystem."""
    try:
        from guardrails import health_check as guard_health
        probe("guardrails", guard_health)
    except ImportError:
        pass


def pipeline_health() -> dict:
    """Collect health status from every AI pipeline subsystem.

    Each probe is wrapped in try/except so a broken subsystem
    never prevents the rest from reporting.
    """
    start = time.monotonic()
    report: dict = {"status": "ok", "subsystems": {}}
    degraded = []

    def _probe(name: str, fn):
        _run_probe(report, degraded, name, fn)

    _probe_knowledge(_probe)
    _probe_search(_probe)
    _probe_circuit_breakers(_probe)
    _probe_memory(_probe)
    _probe_cache(_probe)
    _probe_guardrails(_probe)

    report["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    if degraded:
        report["status"] = "degraded"
        report["degraded"] = degraded

    return report
