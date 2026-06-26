"""
vinhlong360 -- OpenTelemetry Tracing Module.

Distributed tracing theo GenAI Semantic Conventions cho Knowledge Agent.
Ho tro theo doi toan bo pipeline: chat request -> RAG retrieval -> LLM call -> tool execution.

Span types:
  - chat          -- toan bo chat request (root span)
  - rag.retrieve  -- vector search / retrieval
  - llm.completion-- goi LLM (token usage, model, duration)
  - tool.*        -- thuc thi tool (search, weather, ...)
  - memory.*      -- doc/ghi memory (hot/cold)

Export:
  get_trace_summary()       -> dict   (thong ke span gan day)
  export_traces_json(limit) -> list   (cho /system/traces endpoint)

Configuration (env vars):
  OTEL_ENABLED               -- "true" (default) / "false"
  OTEL_EXPORTER              -- "console" (default) / "otlp" / "none"
  OTEL_EXPORTER_OTLP_ENDPOINT -- endpoint cho OTLP exporter

No-op mode: neu OTel SDK chua cai hoac OTEL_ENABLED=false,
moi function tra ve no-op context manager. Zero overhead.

Thread-safe: moi state mutation deu qua threading.Lock.
"""

import functools
import json
import logging
import os
import time
from collections import deque
from contextlib import contextmanager
from threading import Lock
from typing import Any, Callable, Deque, Dict, Generator, List, Optional

logger = logging.getLogger("vinhlong360.tracing")


# ==============================================================
#  CONFIGURATION
# ==============================================================

OTEL_ENABLED = os.environ.get("OTEL_ENABLED", "true").lower() == "true"
OTEL_EXPORTER = os.environ.get("OTEL_EXPORTER", "console").lower()
OTEL_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

SERVICE_NAME = "vinhlong360-agent"
SERVICE_VERSION = "7.0"


# ==============================================================
#  OPENTELEMETRY SDK IMPORT (try/except -- no-op neu thieu)
# ==============================================================

_HAS_OTEL = False

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import StatusCode, Status

    _HAS_OTEL = True
except ImportError:
    trace = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment,misc]
    SimpleSpanProcessor = None  # type: ignore[assignment,misc]
    ConsoleSpanExporter = None  # type: ignore[assignment,misc]
    Resource = None  # type: ignore[assignment,misc]
    StatusCode = None  # type: ignore[assignment,misc]
    Status = None  # type: ignore[assignment,misc]
    logger.info("OpenTelemetry SDK khong kha dung -- su dung no-op mode")


# ==============================================================
#  IN-MEMORY TRACE STORE
# ==============================================================

_MAX_STORED_SPANS = 1000
_span_store: Deque[Dict[str, Any]] = deque(maxlen=_MAX_STORED_SPANS)
_store_lock = Lock()


def _record_span(
    trace_id: str,
    span_id: str,
    name: str,
    start_time: float,
    duration_ms: float,
    status: str,
    attributes: Dict[str, Any],
) -> None:
    """Luu span vao in-memory store (thread-safe)."""
    record = {
        "trace_id": trace_id,
        "span_id": span_id,
        "name": name,
        "start_time": start_time,
        "duration_ms": round(duration_ms, 2),
        "status": status,
        "attributes": attributes,
    }
    with _store_lock:
        _span_store.append(record)


# ==============================================================
#  TRACER PROVIDER SETUP
# ==============================================================

_tracer = None  # Module-level tracer singleton


def _init_tracer() -> Any:
    """Khoi tao TracerProvider voi exporter duoc cau hinh.

    Tra ve tracer object hoac None neu khong kha dung.
    """
    if not _HAS_OTEL or not OTEL_ENABLED:
        logger.info("Tracing disabled (OTEL_ENABLED=%s, SDK=%s)", OTEL_ENABLED, _HAS_OTEL)
        return None

    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": SERVICE_VERSION,
    })

    provider = TracerProvider(resource=resource)

    # -- Chon exporter --
    if OTEL_EXPORTER == "console":
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        logger.info("Tracing exporter: ConsoleSpanExporter")

    elif OTEL_EXPORTER == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            processor = SimpleSpanProcessor(
                OTLPSpanExporter(endpoint=OTEL_OTLP_ENDPOINT)
            )
            provider.add_span_processor(processor)
            logger.info("Tracing exporter: OTLP -> %s", OTEL_OTLP_ENDPOINT)
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp chua cai dat -- fallback ve ConsoleSpanExporter"
            )
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)

    elif OTEL_EXPORTER == "none":
        logger.info("Tracing exporter: none (chi luu in-memory)")

    else:
        logger.warning("OTEL_EXPORTER='%s' khong hop le -- dung console", OTEL_EXPORTER)
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME, SERVICE_VERSION)


# Khoi tao tracer khi module duoc import
_tracer = _init_tracer()


# ==============================================================
#  NO-OP CONTEXT MANAGER
# ==============================================================

@contextmanager
def _noop_span(name: str = "", **kwargs: Any) -> Generator[Any, None, None]:
    """Context manager khong lam gi -- dung khi tracing tat."""
    yield None


# ==============================================================
#  SHARED SPAN HELPER
# ==============================================================

@contextmanager
def _traced_span(
    span_name: str,
    attrs: Dict[str, Any],
    collect_keys: Optional[List[str]] = None,
) -> Generator[Any, None, None]:
    """Shared boilerplate for all GenAI span creators.

    Args:
        span_name: OTel span name (e.g. "chat", "tool.search").
        attrs: Initial span attributes.
        collect_keys: Attribute keys to read back from the span after yield
                      (for caller-set values like token usage).
    """
    with _tracer.start_as_current_span(span_name) as span:
        start = time.monotonic()
        for k, v in attrs.items():
            span.set_attribute(k, v)

        status = "OK"
        try:
            yield span
        except Exception as exc:
            status = "ERROR"
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
        else:
            span.set_status(Status(StatusCode.OK))
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            span.set_attribute("duration_ms", round(duration_ms, 2))
            final_attrs = dict(attrs)
            if collect_keys:
                try:
                    for ck in collect_keys:
                        val = span.attributes.get(ck)
                        if val is not None:
                            final_attrs[ck] = val
                except Exception:
                    logger.debug("Could not read caller-set attrs from span %s", span_name)
            ctx = span.get_span_context()
            _record_span(
                trace_id=format(ctx.trace_id, "032x"),
                span_id=format(ctx.span_id, "016x"),
                name=span_name,
                start_time=start,
                duration_ms=duration_ms,
                status=status,
                attributes=final_attrs,
            )


# ==============================================================
#  GENAI-COMPATIBLE SPAN CREATORS
# ==============================================================

@contextmanager
def trace_chat_request(
    message: str,
    session_id: str,
    model: str = "unknown",
) -> Generator[Any, None, None]:
    """Root span for a chat request (GenAI Semantic Conventions)."""
    if _tracer is None:
        yield None
        return
    attrs = {
        "gen_ai.system": "vinhlong360",
        "gen_ai.request.model": model,
        "user.session_id": session_id,
        "gen_ai.prompt": message[:200],
    }
    with _traced_span("chat", attrs) as span:
        yield span


@contextmanager
def trace_tool_call(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """Child span for a tool invocation."""
    if _tracer is None:
        yield None
        return
    args_json = json.dumps(arguments or {}, ensure_ascii=False, default=str)
    attrs = {"tool.name": tool_name, "tool.arguments": args_json[:500]}
    with _traced_span(f"tool.{tool_name}", attrs) as span:
        yield span


@contextmanager
def trace_llm_call(
    model: str,
    messages_count: int = 0,
) -> Generator[Any, None, None]:
    """Span for an LLM completion call (caller sets token usage on span)."""
    if _tracer is None:
        yield None
        return
    attrs = {"gen_ai.request.model": model, "gen_ai.request.messages_count": messages_count}
    with _traced_span("llm.completion", attrs,
                      collect_keys=["gen_ai.usage.prompt_tokens",
                                    "gen_ai.usage.completion_tokens"]) as span:
        yield span


@contextmanager
def trace_rag_retrieval(
    query: str,
    strategy: str = "default",
) -> Generator[Any, None, None]:
    """Span for RAG retrieval (caller sets rag.results_count on span)."""
    if _tracer is None:
        yield None
        return
    attrs = {"rag.query": query[:200], "rag.strategy": strategy}
    with _traced_span("rag.retrieve", attrs,
                      collect_keys=["rag.results_count"]) as span:
        yield span


@contextmanager
def trace_memory_operation(
    operation: str,
    user_id: str = "unknown",
) -> Generator[Any, None, None]:
    """Span for memory read/write operations."""
    if _tracer is None:
        yield None
        return
    attrs = {"memory.operation": operation, "user.id": user_id}
    with _traced_span(f"memory.{operation}", attrs) as span:
        yield span


# ==============================================================
#  DECORATOR FOR EASY TRACING
# ==============================================================

def traced(operation_name: Optional[str] = None) -> Callable:
    """Decorator de tu dong trace mot function.

    Usage:
        @traced("custom_operation")
        def my_function(args):
            ...

        @traced()
        def another_function():
            ...  # span name = ten function
    """
    def decorator(func: Callable) -> Callable:
        span_name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _tracer is None:
                return func(*args, **kwargs)

            with _tracer.start_as_current_span(span_name) as span:
                start = time.monotonic()
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__ or "")

                status = "OK"
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    status = "ERROR"
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise
                finally:
                    duration_ms = (time.monotonic() - start) * 1000
                    span.set_attribute("duration_ms", round(duration_ms, 2))
                    ctx = span.get_span_context()
                    _record_span(
                        trace_id=format(ctx.trace_id, "032x"),
                        span_id=format(ctx.span_id, "016x"),
                        name=span_name,
                        start_time=start,
                        duration_ms=duration_ms,
                        status=status,
                        attributes={
                            "code.function": func.__name__,
                            "code.namespace": func.__module__ or "",
                        },
                    )

        return wrapper
    return decorator


# ==============================================================
#  TRACE SUMMARY & EXPORT
# ==============================================================

def get_trace_summary() -> Dict[str, Any]:
    """Thong ke tong hop ve cac span gan day.

    Returns:
        {
            "total_spans": int,
            "span_counts_by_name": {"chat": 10, "llm.completion": 25, ...},
            "avg_duration_ms_by_name": {"chat": 120.5, ...},
            "error_rate": 0.02,
            "errors_by_name": {"tool.search": 3, ...},
        }
    """
    with _store_lock:
        spans = list(_span_store)

    if not spans:
        return {
            "total_spans": 0,
            "span_counts_by_name": {},
            "avg_duration_ms_by_name": {},
            "error_rate": 0.0,
            "errors_by_name": {},
        }

    total = len(spans)
    counts: Dict[str, int] = {}
    durations: Dict[str, List[float]] = {}
    errors: Dict[str, int] = {}
    total_errors = 0

    for s in spans:
        name = s["name"]
        counts[name] = counts.get(name, 0) + 1

        if name not in durations:
            durations[name] = []
        durations[name].append(s["duration_ms"])

        if s["status"] == "ERROR":
            total_errors += 1
            errors[name] = errors.get(name, 0) + 1

    avg_durations = {
        name: round(sum(vals) / len(vals), 2) for name, vals in durations.items()
    }

    return {
        "total_spans": total,
        "span_counts_by_name": counts,
        "avg_duration_ms_by_name": avg_durations,
        "error_rate": round(total_errors / total, 4) if total else 0.0,
        "errors_by_name": errors,
    }


def export_traces_json(limit: int = 100) -> List[Dict[str, Any]]:
    """Xuat cac span gan nhat duoi dang list of dicts.

    Dung cho /system/traces API endpoint.
    Tra ve theo thu tu moi nhat truoc.

    Args:
        limit: so luong span toi da tra ve (default 100).
    """
    with _store_lock:
        spans = list(_span_store)

    # Moi nhat truoc
    spans.reverse()
    return spans[:limit]


# ==============================================================
#  MODULE SINGLETON
# ==============================================================

# `tracer` -- san sang de import tu cac module khac
# Usage: from agent.tracing import tracer, trace_chat_request
tracer = _tracer

# Logging trang thai khoi tao
if _HAS_OTEL and OTEL_ENABLED:
    logger.info(
        "OpenTelemetry tracing ACTIVE (service=%s, version=%s, exporter=%s)",
        SERVICE_NAME, SERVICE_VERSION, OTEL_EXPORTER,
    )
else:
    _reason = "SDK not installed" if not _HAS_OTEL else "OTEL_ENABLED=false"
    logger.info("OpenTelemetry tracing DISABLED (%s) -- all spans are no-op", _reason)
