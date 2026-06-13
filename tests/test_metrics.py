"""Tests for agent/metrics.py — Prometheus-compatible metrics."""
import threading

import pytest

# We need fresh metric instances for isolation, so we test the classes directly
# and also test the module-level convenience functions.
from metrics import (
    Counter, Gauge, Histogram,
    generate_metrics,
    track_chat_request, track_tool_call, track_cache,
    track_feedback, track_error,
    chat_requests_total, tool_calls_total, cache_operations_total,
    feedback_total, errors_total,
    _format_labels, _labels_key,
)


# ── Counter ──────────────────────────────────────────


class TestCounter:
    def test_inc_default(self):
        c = Counter("test_counter_1", "A test counter")
        c.inc()
        assert c.get() == 1.0

    def test_inc_with_amount(self):
        c = Counter("test_counter_2", "A test counter")
        c.inc(amount=5)
        assert c.get() == 5.0

    def test_inc_with_labels(self):
        c = Counter("test_counter_3", "Labeled counter", labels=["method"])
        c.inc({"method": "GET"})
        c.inc({"method": "GET"}, 2)
        c.inc({"method": "POST"})
        assert c.get({"method": "GET"}) == 3.0
        assert c.get({"method": "POST"}) == 1.0

    def test_inc_negative_raises(self):
        c = Counter("test_counter_4", "No negatives")
        with pytest.raises(ValueError, match="must be >= 0"):
            c.inc(amount=-1)

    def test_inc_wrong_labels_raises(self):
        c = Counter("test_counter_5", "Label mismatch", labels=["a"])
        with pytest.raises(ValueError, match="expects labels"):
            c.inc({"b": "val"})

    def test_get_missing_label_returns_zero(self):
        c = Counter("test_counter_6", "Missing label", labels=["x"])
        assert c.get({"x": "never_set"}) == 0.0

    def test_collect_format(self):
        c = Counter("http_total", "Total HTTP", labels=["method"])
        c.inc({"method": "GET"}, 10)
        output = c.collect()
        assert '# HELP http_total Total HTTP' in output
        assert '# TYPE http_total counter' in output
        assert 'http_total{method="GET"} 10' in output


# ── Gauge ────────────────────────────────────────────


class TestGauge:
    def test_set(self):
        g = Gauge("test_gauge_1", "A gauge")
        g.set(value=42.0)
        assert g.get() == 42.0

    def test_inc(self):
        g = Gauge("test_gauge_2", "Inc gauge")
        g.inc(amount=5)
        g.inc(amount=3)
        assert g.get() == 8.0

    def test_dec(self):
        g = Gauge("test_gauge_3", "Dec gauge")
        g.set(value=10)
        g.dec(amount=3)
        assert g.get() == 7.0

    def test_inc_negative(self):
        g = Gauge("test_gauge_4", "Negative inc")
        g.set(value=10)
        g.inc(amount=-2)
        assert g.get() == 8.0

    def test_collect_format(self):
        g = Gauge("temperature", "Current temp", labels=["city"])
        g.set({"city": "saigon"}, 35.0)
        output = g.collect()
        assert '# TYPE temperature gauge' in output
        assert 'temperature{city="saigon"} 35' in output


# ── Histogram ────────────────────────────────────────


class TestHistogram:
    def test_observe(self):
        h = Histogram("test_hist_1", "A histogram", buckets=[0.1, 0.5, 1.0])
        h.observe(value=0.3)
        h.observe(value=0.8)
        h.observe(value=0.05)
        output = h.collect()
        assert '# TYPE test_hist_1 histogram' in output
        assert 'test_hist_1_count 3' in output

    def test_bucket_boundaries(self):
        h = Histogram("test_hist_2", "Buckets", buckets=[1, 5, 10])
        h.observe(value=0.5)   # bucket 1
        h.observe(value=3)     # bucket 5
        h.observe(value=7)     # bucket 10
        h.observe(value=100)   # +Inf
        output = h.collect()
        assert 'le="1"' in output
        assert 'le="5"' in output
        assert 'le="10"' in output
        assert 'le="+Inf"' in output
        assert 'test_hist_2_count 4' in output

    def test_sum_tracking(self):
        h = Histogram("test_hist_3", "Sum", buckets=[10])
        h.observe(value=3)
        h.observe(value=7)
        output = h.collect()
        assert 'test_hist_3_sum 10' in output

    def test_inf_bucket_auto_appended(self):
        h = Histogram("test_hist_4", "Inf", buckets=[1, 2])
        # Internal buckets should be [1, 2, inf]
        assert len(h._buckets) == 3


# ── generate_metrics ──────────────────────────────────


def test_generate_metrics_returns_string():
    output = generate_metrics()
    assert isinstance(output, str)
    assert "# HELP" in output
    assert "# TYPE" in output


def test_generate_metrics_ends_with_newline():
    output = generate_metrics()
    assert output.endswith("\n")


# ── Convenience functions ─────────────────────────────


def test_track_chat_request():
    before = chat_requests_total.get({"status": "success"})
    track_chat_request("success", 1.5)
    after = chat_requests_total.get({"status": "success"})
    assert after == before + 1


def test_track_tool_call():
    before = tool_calls_total.get({"tool_name": "search"})
    track_tool_call("search", 0.1)
    after = tool_calls_total.get({"tool_name": "search"})
    assert after == before + 1


def test_track_cache():
    before = cache_operations_total.get({"operation": "hit"})
    track_cache("hit")
    after = cache_operations_total.get({"operation": "hit"})
    assert after == before + 1


def test_track_feedback_positive():
    before = feedback_total.get({"rating": "positive"})
    track_feedback(positive=True)
    after = feedback_total.get({"rating": "positive"})
    assert after == before + 1


def test_track_feedback_negative():
    before = feedback_total.get({"rating": "negative"})
    track_feedback(positive=False)
    after = feedback_total.get({"rating": "negative"})
    assert after == before + 1


def test_track_error():
    before = errors_total.get({"endpoint": "/chat", "error_type": "timeout"})
    track_error("/chat", "timeout")
    after = errors_total.get({"endpoint": "/chat", "error_type": "timeout"})
    assert after == before + 1


# ── Helper functions ──────────────────────────────────


def test_format_labels_empty():
    assert _format_labels({}) == ""


def test_format_labels_single():
    assert _format_labels({"a": "1"}) == '{a="1"}'


def test_format_labels_sorted():
    result = _format_labels({"z": "2", "a": "1"})
    assert result == '{a="1",z="2"}'


def test_labels_key_deterministic():
    k1 = _labels_key({"a": "1", "b": "2"})
    k2 = _labels_key({"b": "2", "a": "1"})
    assert k1 == k2


# ── Thread safety ─────────────────────────────────────


def test_counter_thread_safety():
    c = Counter("thread_safe_counter", "Thread test")
    num_threads = 10
    increments_per_thread = 100

    def worker():
        for _ in range(increments_per_thread):
            c.inc()

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert c.get() == num_threads * increments_per_thread


def test_gauge_thread_safety():
    g = Gauge("thread_safe_gauge", "Thread test gauge")
    num_threads = 10
    increments_per_thread = 100

    def worker():
        for _ in range(increments_per_thread):
            g.inc()

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert g.get() == num_threads * increments_per_thread
