"""Tests cho tracing.py — no-op mode (OTel SDK not installed in test env)."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tracing import (  # noqa: E402
    _noop_span,
    _record_span,
    _span_store,
    _store_lock,
    export_traces_json,
    get_trace_summary,
    trace_chat_request,
    trace_llm_call,
    trace_memory_operation,
    trace_rag_retrieval,
    trace_tool_call,
    traced,
)


@pytest.fixture(autouse=True)
def clear_span_store():
    """Reset span store between tests."""
    with _store_lock:
        _span_store.clear()
    yield
    with _store_lock:
        _span_store.clear()


# ── No-op context managers ──


class TestNoOpSpans:
    def test_noop_span_yields_none(self):
        with _noop_span("test") as s:
            assert s is None

    def test_trace_chat_request_noop(self):
        with patch("tracing._tracer", None):
            with trace_chat_request("hello", "s1") as s:
                assert s is None

    def test_trace_tool_call_noop(self):
        with patch("tracing._tracer", None):
            with trace_tool_call("search", {"q": "test"}) as s:
                assert s is None

    def test_trace_llm_call_noop(self):
        with patch("tracing._tracer", None):
            with trace_llm_call("gpt-4", 5) as s:
                assert s is None

    def test_trace_rag_retrieval_noop(self):
        with patch("tracing._tracer", None):
            with trace_rag_retrieval("query", "semantic") as s:
                assert s is None

    def test_trace_memory_operation_noop(self):
        with patch("tracing._tracer", None):
            with trace_memory_operation("read", "u1") as s:
                assert s is None


# ── In-memory span store ──


class TestSpanStore:
    def test_record_span(self):
        _record_span(
            trace_id="abc123",
            span_id="def456",
            name="test.op",
            start_time=100.0,
            duration_ms=42.5,
            status="OK",
            attributes={"key": "val"},
        )
        with _store_lock:
            assert len(_span_store) == 1
            s = _span_store[0]
        assert s["trace_id"] == "abc123"
        assert s["name"] == "test.op"
        assert s["duration_ms"] == 42.5
        assert s["status"] == "OK"
        assert s["attributes"]["key"] == "val"

    def test_store_bounded(self):
        for i in range(1100):
            _record_span(
                trace_id=str(i), span_id=str(i),
                name="spam", start_time=0, duration_ms=0,
                status="OK", attributes={},
            )
        with _store_lock:
            assert len(_span_store) <= 1000


# ── Summary & export ──


class TestTraceSummary:
    def test_empty_summary(self):
        s = get_trace_summary()
        assert s["total_spans"] == 0
        assert s["error_rate"] == 0.0

    def test_summary_counts(self):
        _record_span("t1", "s1", "chat", 0, 100, "OK", {})
        _record_span("t2", "s2", "chat", 0, 200, "OK", {})
        _record_span("t3", "s3", "tool.search", 0, 50, "ERROR", {})

        s = get_trace_summary()
        assert s["total_spans"] == 3
        assert s["span_counts_by_name"]["chat"] == 2
        assert s["span_counts_by_name"]["tool.search"] == 1
        assert s["errors_by_name"]["tool.search"] == 1
        assert s["avg_duration_ms_by_name"]["chat"] == 150.0
        assert s["error_rate"] == pytest.approx(1 / 3, abs=0.01)

    def test_export_json_order(self):
        _record_span("t1", "s1", "first", 0, 10, "OK", {})
        _record_span("t2", "s2", "second", 0, 20, "OK", {})
        _record_span("t3", "s3", "third", 0, 30, "OK", {})

        result = export_traces_json(limit=2)
        assert len(result) == 2
        assert result[0]["name"] == "third"
        assert result[1]["name"] == "second"

    def test_export_json_all(self):
        for i in range(5):
            _record_span(str(i), str(i), f"op{i}", 0, i, "OK", {})
        result = export_traces_json(limit=100)
        assert len(result) == 5


# ── @traced decorator ──


class TestTracedDecorator:
    def test_traced_noop_passthrough(self):
        @traced("my_op")
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_traced_default_name(self):
        @traced()
        def my_func():
            return 42

        assert my_func() == 42

    def test_traced_propagates_exception(self):
        @traced("failing_op")
        def boom():
            raise RuntimeError("test error")

        with pytest.raises(RuntimeError, match="test error"):
            boom()
