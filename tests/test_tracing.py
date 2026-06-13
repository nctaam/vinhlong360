"""Tests for agent/tracing.py -- OpenTelemetry tracing (no-op mode).

These tests run WITHOUT the OpenTelemetry SDK installed (or with OTEL_ENABLED=false),
so all context managers yield None and functions return safe defaults.
No network calls or OTel dependencies required.
"""

import os
import sys
import time
from pathlib import Path

import pytest

# Force no-op mode before importing
os.environ["OTEL_ENABLED"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from tracing import (
    trace_chat_request,
    trace_tool_call,
    trace_llm_call,
    trace_rag_retrieval,
    trace_memory_operation,
    traced,
    get_trace_summary,
    export_traces_json,
    _span_store,
    _store_lock,
    _record_span,
)


# ---- Context Managers (no-op mode) ----


class TestTraceChatRequest:
    def test_yields_none(self):
        with trace_chat_request("hello", session_id="s1") as span:
            assert span is None

    def test_no_exception(self):
        with trace_chat_request("hello", session_id="s1", model="test"):
            pass  # should not raise


class TestTraceToolCall:
    def test_yields_none(self):
        with trace_tool_call("search", arguments={"q": "test"}) as span:
            assert span is None

    def test_no_exception(self):
        with trace_tool_call("entity_detail"):
            pass

    def test_with_none_arguments(self):
        with trace_tool_call("weather", arguments=None) as span:
            assert span is None


class TestTraceLlmCall:
    def test_yields_none(self):
        with trace_llm_call("gpt-4", messages_count=5) as span:
            assert span is None

    def test_no_exception(self):
        with trace_llm_call("gpt-4"):
            pass


class TestTraceRagRetrieval:
    def test_yields_none(self):
        with trace_rag_retrieval("du lich Vinh Long", strategy="hybrid") as span:
            assert span is None

    def test_no_exception(self):
        with trace_rag_retrieval("query"):
            pass


class TestTraceMemoryOperation:
    def test_yields_none(self):
        with trace_memory_operation("read", user_id="u1") as span:
            assert span is None

    def test_no_exception(self):
        with trace_memory_operation("write"):
            pass


# ---- @traced Decorator ----


class TestTracedDecorator:
    def test_wraps_function_correctly(self):
        @traced("my_op")
        def my_func(x, y):
            return x + y

        assert my_func(2, 3) == 5

    def test_preserves_function_name(self):
        @traced()
        def example_function():
            pass

        assert example_function.__name__ == "example_function"

    def test_passes_through_kwargs(self):
        @traced("op")
        def func(a, b=10):
            return a * b

        assert func(3, b=5) == 15

    def test_propagates_exceptions(self):
        @traced("fail_op")
        def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            failing()

    def test_no_span_name_uses_function_name(self):
        @traced()
        def auto_named():
            return 42

        assert auto_named() == 42


# ---- In-Memory Span Store ----


class TestRecordSpan:
    def test_records_span(self):
        initial_len = len(_span_store)
        _record_span(
            trace_id="abc123",
            span_id="def456",
            name="test.span",
            start_time=time.monotonic(),
            duration_ms=42.5,
            status="OK",
            attributes={"key": "value"},
        )
        assert len(_span_store) == initial_len + 1
        last = _span_store[-1]
        assert last["name"] == "test.span"
        assert last["status"] == "OK"
        assert last["duration_ms"] == 42.5


# ---- get_trace_summary ----


class TestGetTraceSummary:
    def test_returns_dict_with_expected_keys(self):
        summary = get_trace_summary()
        assert isinstance(summary, dict)
        assert "total_spans" in summary
        assert "span_counts_by_name" in summary
        assert "avg_duration_ms_by_name" in summary
        assert "error_rate" in summary
        assert "errors_by_name" in summary

    def test_total_spans_is_nonnegative(self):
        summary = get_trace_summary()
        assert summary["total_spans"] >= 0

    def test_error_rate_is_float(self):
        summary = get_trace_summary()
        assert isinstance(summary["error_rate"], float)


# ---- export_traces_json ----


class TestExportTracesJson:
    def test_returns_list(self):
        result = export_traces_json()
        assert isinstance(result, list)

    def test_respects_limit(self):
        result = export_traces_json(limit=1)
        assert len(result) <= 1


# ---- Multiple traces produce correct summary ----


class TestTraceSummaryStats:
    def test_multiple_spans_counted(self):
        # Record a few test spans
        for i in range(3):
            _record_span(
                trace_id=f"trace_{i}",
                span_id=f"span_{i}",
                name="test.multi",
                start_time=time.monotonic(),
                duration_ms=10.0 + i,
                status="OK",
                attributes={},
            )
        _record_span(
            trace_id="trace_err",
            span_id="span_err",
            name="test.multi",
            start_time=time.monotonic(),
            duration_ms=5.0,
            status="ERROR",
            attributes={},
        )

        summary = get_trace_summary()
        assert summary["total_spans"] >= 4
        assert summary["span_counts_by_name"].get("test.multi", 0) >= 4
        # At least one error should appear
        assert summary["errors_by_name"].get("test.multi", 0) >= 1
        assert summary["error_rate"] > 0
