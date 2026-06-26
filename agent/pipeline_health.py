"""
vinhlong360 — Unified Pipeline Health Check.

Aggregates health probes from all AI pipeline subsystems into
a single status report. Used by /health endpoint and monitoring.
"""

import logging
import time

logger = logging.getLogger(__name__)


def pipeline_health() -> dict:
    """Collect health status from every AI pipeline subsystem.

    Each probe is wrapped in try/except so a broken subsystem
    never prevents the rest from reporting.
    """
    start = time.monotonic()
    report: dict = {"status": "ok", "subsystems": {}}
    degraded = []

    def _probe(name: str, fn):
        try:
            result = fn()
            report["subsystems"][name] = result
            if result.get("status") not in ("ok", None):
                degraded.append(name)
        except Exception as exc:
            logger.warning("Health probe %s failed: %s", name, exc)
            report["subsystems"][name] = {"status": "error", "error": str(exc)}
            degraded.append(name)

    # Knowledge layer
    try:
        from knowledge import health_check as kb_health
        _probe("knowledge", kb_health)
    except ImportError:
        pass

    # Search pipeline
    try:
        from contextual_retrieval import search_health
        _probe("search", search_health)
    except ImportError:
        pass

    # Circuit breakers
    try:
        from circuit_breaker import llm_breaker, weather_breaker, web_search_breaker
        _probe("circuit_breaker_llm", lambda: {
            "status": "ok" if llm_breaker.is_healthy else "degraded",
            **llm_breaker.stats(),
        })
        _probe("circuit_breaker_weather", lambda: {
            "status": "ok" if weather_breaker.is_healthy else "degraded",
            **weather_breaker.stats(),
        })
        _probe("circuit_breaker_web", lambda: {
            "status": "ok" if web_search_breaker.is_healthy else "degraded",
            **web_search_breaker.stats(),
        })
    except ImportError:
        pass

    # Memory subsystem
    try:
        from memory import memory_health_check
        _probe("memory", memory_health_check)
    except ImportError:
        pass

    # Cache
    try:
        from cache import cache_health_check
        _probe("cache", cache_health_check)
    except ImportError:
        pass

    # Guardrails
    try:
        from guardrails import health_check as guard_health
        _probe("guardrails", guard_health)
    except ImportError:
        pass

    report["elapsed_ms"] = round((time.monotonic() - start) * 1000, 1)
    if degraded:
        report["status"] = "degraded"
        report["degraded"] = degraded

    return report
