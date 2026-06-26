"""Tests cho metrics.py — Counter, Gauge, Histogram, registry, convenience funcs."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics import (  # noqa: E402
    Counter,
    Gauge,
    Histogram,
    _format_labels,
    _labels_key,
    _registry,
    _registry_by_name,
    _registry_lock,
    generate_metrics,
    set_gauge,
    track_cache,
    track_chat_request,
    track_error,
    track_feedback,
    track_tool_call,
)


# ── Counter ──


class TestCounter:
    def test_inc_default(self):
        c = Counter("test_counter_1", "test")
        c.inc()
        assert c.get() == 1.0

    def test_inc_with_amount(self):
        c = Counter("test_counter_2", "test")
        c.inc(amount=5)
        assert c.get() == 5.0

    def test_inc_negative_raises(self):
        c = Counter("test_counter_3", "test")
        with pytest.raises(ValueError, match="must be >= 0"):
            c.inc(amount=-1)

    def test_inc_with_labels(self):
        c = Counter("test_counter_4", "test", labels=["method"])
        c.inc({"method": "GET"})
        c.inc({"method": "GET"}, 2)
        c.inc({"method": "POST"})
        assert c.get({"method": "GET"}) == 3.0
        assert c.get({"method": "POST"}) == 1.0

    def test_wrong_labels_raises(self):
        c = Counter("test_counter_5", "test", labels=["method"])
        with pytest.raises(ValueError, match="expects labels"):
            c.inc({"status": "ok"})

    def test_collect_format(self):
        c = Counter("test_counter_6", "test description")
        c.inc(amount=42)
        text = c.collect()
        assert "# HELP test_counter_6 test description" in text
        assert "# TYPE test_counter_6 counter" in text
        assert "test_counter_6 42" in text


# ── Gauge ──


class TestGauge:
    def test_set_and_get(self):
        g = Gauge("test_gauge_1", "test")
        g.set(value=10.5)
        assert g.get() == 10.5

    def test_inc_and_dec(self):
        g = Gauge("test_gauge_2", "test")
        g.set(value=10)
        g.inc(amount=5)
        assert g.get() == 15.0
        g.dec(amount=3)
        assert g.get() == 12.0

    def test_labels(self):
        g = Gauge("test_gauge_3", "test", labels=["loc"])
        g.set({"loc": "a"}, 1)
        g.set({"loc": "b"}, 2)
        assert g.get({"loc": "a"}) == 1.0
        assert g.get({"loc": "b"}) == 2.0

    def test_collect_format(self):
        g = Gauge("test_gauge_4", "test gauge")
        g.set(value=99)
        text = g.collect()
        assert "# TYPE test_gauge_4 gauge" in text
        assert "test_gauge_4 99" in text


# ── Histogram ──


class TestHistogram:
    def test_observe_and_collect(self):
        h = Histogram("test_hist_1", "test", buckets=[1, 5, 10])
        h.observe(value=0.5)
        h.observe(value=3)
        h.observe(value=7)
        h.observe(value=15)
        text = h.collect()
        assert "# TYPE test_hist_1 histogram" in text
        assert 'le="1"' in text
        assert 'le="+Inf"' in text
        assert "test_hist_1_count 4" in text
        assert "test_hist_1_sum 25.5" in text

    def test_cumulative_buckets(self):
        h = Histogram("test_hist_2", "test", buckets=[1, 5, 10])
        h.observe(value=0.5)  # goes into bucket 1
        h.observe(value=3)    # goes into bucket 5
        text = h.collect()
        # Cumulative: le=1 → 1, le=5 → 2, le=10 → 2, le=+Inf → 2
        lines = text.split("\n")
        bucket_lines = [l for l in lines if "_bucket" in l]
        assert len(bucket_lines) == 4  # 1, 5, 10, +Inf
        # le="1" should be 1
        assert any('le="1"} 1' in l for l in bucket_lines)
        # le="5" should be 2 (cumulative)
        assert any('le="5"} 2' in l for l in bucket_lines)

    def test_inf_bucket_appended(self):
        h = Histogram("test_hist_3", "test", buckets=[1, 5])
        assert h._buckets[-1] == math.inf

    def test_observe_with_labels(self):
        h = Histogram("test_hist_4", "test", buckets=[1, 5], labels=["ep"])
        h.observe({"ep": "/chat"}, 0.5)
        h.observe({"ep": "/search"}, 3)
        text = h.collect()
        assert 'ep="/chat"' in text
        assert 'ep="/search"' in text


# ── Registry ──


class TestRegistry:
    def test_metrics_auto_registered(self):
        name = "test_auto_reg_1"
        c = Counter(name, "auto reg test")
        with _registry_lock:
            assert c in _registry
            assert _registry_by_name.get(name) is c

    def test_set_gauge_by_name(self):
        g = Gauge("test_set_gauge_by_name", "test")
        set_gauge("test_set_gauge_by_name", 42)
        assert g.get() == 42.0

    def test_set_gauge_unknown_name_raises(self):
        with pytest.raises(KeyError, match="No Gauge metric"):
            set_gauge("nonexistent_gauge_999", 1)

    def test_set_gauge_on_counter_raises(self):
        Counter("test_not_a_gauge", "test")
        with pytest.raises(KeyError, match="No Gauge metric"):
            set_gauge("test_not_a_gauge", 1)


# ── generate_metrics ──


def test_generate_metrics_returns_string():
    text = generate_metrics()
    assert isinstance(text, str)
    assert text.endswith("\n")
    assert "# HELP" in text


# ── Convenience funcs ──


def test_track_chat_request():
    track_chat_request("success", 1.23)


def test_track_tool_call():
    track_tool_call("search", 0.05)


def test_track_cache():
    track_cache("hit")
    track_cache("miss")
    track_cache("eviction")


def test_track_feedback():
    track_feedback(True)
    track_feedback(False)


def test_track_error():
    track_error("/chat", "timeout")


# ── Helpers ──


def test_labels_key_sorted():
    k1 = _labels_key({"b": "2", "a": "1"})
    k2 = _labels_key({"a": "1", "b": "2"})
    assert k1 == k2


def test_format_labels_empty():
    assert _format_labels({}) == ""


def test_format_labels_single():
    assert _format_labels({"method": "GET"}) == '{method="GET"}'
