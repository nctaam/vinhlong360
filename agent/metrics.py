"""
vinhlong360 — Prometheus Metrics Module.

Lightweight, custom Prometheus-compatible metrics exporter.
Khong phu thuoc external library (stdlib only).

Metric types:
  - Counter  — monotonically increasing
  - Histogram — distribution tracking with configurable buckets
  - Gauge    — current value (can go up or down)

Pre-defined metrics for Knowledge Agent:
  - chat_requests_total, tool_calls_total, cache_operations_total, ...
  - chat_response_duration_seconds, tool_call_duration_seconds
  - active_sessions, cache_size, entities_total, circuit_breaker_state

Export:
  generate_metrics() -> str  (Prometheus text exposition format)
  GET /metrics               (mounted by server.py)

Thread-safe: all state mutations guarded by threading.Lock.
"""

import logging
import math
import time

logger = logging.getLogger(__name__)
from threading import Lock
from typing import Dict, List, Optional, Sequence, Tuple


# ══════════════════════════════════════════════════
#  METRIC REGISTRY
# ══════════════════════════════════════════════════

_registry: List["_MetricBase"] = []
_registry_by_name: Dict[str, "_MetricBase"] = {}
_registry_lock = Lock()


def _register(metric: "_MetricBase") -> None:
    """Add a metric to the global registry."""
    with _registry_lock:
        _registry.append(metric)
        _registry_by_name[metric.name] = metric


def _labels_key(labels: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    """Convert a labels dict to an immutable, sorted key for hashing."""
    return tuple(sorted(labels.items()))


def _format_labels(labels: Dict[str, str]) -> str:
    """Format labels as Prometheus label string: {key="val",key2="val2"}."""
    if not labels:
        return ""
    parts = ",".join(
        f'{k}="{v}"' for k, v in sorted(labels.items())
    )
    return "{" + parts + "}"


# ══════════════════════════════════════════════════
#  BASE CLASS
# ══════════════════════════════════════════════════

class _MetricBase:
    """Abstract base for all metric types."""

    def __init__(self, name: str, description: str, metric_type: str,
                 label_names: Sequence[str] = ()):
        self.name = name
        self.description = description
        self.metric_type = metric_type
        self.label_names = tuple(label_names)
        self._lock = Lock()
        _register(self)

    def _validate_labels(self, labels: Dict[str, str]) -> None:
        """Ensure supplied label keys match declared label_names."""
        if set(labels.keys()) != set(self.label_names):
            raise ValueError(
                f"Metric '{self.name}' expects labels {self.label_names}, "
                f"got {tuple(labels.keys())}"
            )

    def collect(self) -> str:
        """Return Prometheus text exposition lines for this metric."""
        raise NotImplementedError


# ══════════════════════════════════════════════════
#  COUNTER
# ══════════════════════════════════════════════════

class Counter(_MetricBase):
    """Monotonically increasing counter.

    Usage:
        c = Counter("http_requests_total", "Total HTTP requests", labels=["method"])
        c.inc({"method": "GET"})
        c.inc({"method": "POST"}, 5)
    """

    def __init__(self, name: str, description: str, labels: Sequence[str] = ()):
        super().__init__(name, description, "counter", labels)
        self._values: Dict[Tuple, float] = {}

    def inc(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0) -> None:
        """Increment the counter by *amount* (must be >= 0)."""
        if amount < 0:
            raise ValueError("Counter.inc amount must be >= 0")
        labels = labels or {}
        self._validate_labels(labels)
        key = _labels_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Return current counter value for the given label set."""
        labels = labels or {}
        key = _labels_key(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def collect(self) -> str:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            for key, value in sorted(self._values.items()):
                lbl = dict(key)
                lines.append(f"{self.name}{_format_labels(lbl)} {value:g}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════
#  GAUGE
# ══════════════════════════════════════════════════

class Gauge(_MetricBase):
    """Gauge that can go up and down.

    Usage:
        g = Gauge("temperature", "Current temperature", labels=["location"])
        g.set({"location": "saigon"}, 34.5)
        g.inc({"location": "saigon"}, -1.0)
    """

    def __init__(self, name: str, description: str, labels: Sequence[str] = ()):
        super().__init__(name, description, "gauge", labels)
        self._values: Dict[Tuple, float] = {}

    def set(self, labels: Optional[Dict[str, str]] = None, value: float = 0.0) -> None:
        """Set gauge to an absolute value."""
        labels = labels or {}
        self._validate_labels(labels)
        key = _labels_key(labels)
        with self._lock:
            self._values[key] = value

    def inc(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0) -> None:
        """Increment (or decrement if negative) the gauge."""
        labels = labels or {}
        self._validate_labels(labels)
        key = _labels_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0) -> None:
        """Decrement the gauge by *amount*."""
        self.inc(labels, -amount)

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Return current gauge value for the given label set."""
        labels = labels or {}
        key = _labels_key(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def collect(self) -> str:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            for key, value in sorted(self._values.items()):
                lbl = dict(key)
                lines.append(f"{self.name}{_format_labels(lbl)} {value:g}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════
#  HISTOGRAM
# ══════════════════════════════════════════════════

class Histogram(_MetricBase):
    """Histogram for distribution tracking.

    Tracks count per bucket, total sum, and total count.

    Usage:
        h = Histogram("duration_seconds", "Request duration",
                       buckets=[0.1, 0.5, 1, 5])
        h.observe({}, 0.42)
    """

    def __init__(self, name: str, description: str,
                 buckets: Sequence[float] = (0.005, 0.01, 0.025, 0.05, 0.1,
                                             0.25, 0.5, 1, 2.5, 5, 10),
                 labels: Sequence[str] = ()):
        super().__init__(name, description, "histogram", labels)
        self._buckets = sorted(buckets)
        if self._buckets[-1] != math.inf:
            self._buckets.append(math.inf)
        # Per-label-set state: {labels_key: {"buckets": [...], "sum": float, "count": int}}
        self._observations: Dict[Tuple, dict] = {}

    def _ensure_entry(self, key: Tuple) -> dict:
        """Lazily initialise bucket counters for a label set."""
        if key not in self._observations:
            self._observations[key] = {
                "buckets": [0] * len(self._buckets),
                "sum": 0.0,
                "count": 0,
            }
        return self._observations[key]

    def observe(self, labels: Optional[Dict[str, str]] = None,
                value: float = 0.0) -> None:
        """Record an observation into the histogram."""
        labels = labels or {}
        self._validate_labels(labels)
        key = _labels_key(labels)
        with self._lock:
            entry = self._ensure_entry(key)
            entry["sum"] += value
            entry["count"] += 1
            # Increment only the first bucket whose upper bound >= value.
            # The collect() method computes cumulative counts from these
            # per-bucket tallies.
            for i, bound in enumerate(self._buckets):
                if value <= bound:
                    entry["buckets"][i] += 1
                    break

    def collect(self) -> str:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for key in sorted(self._observations.keys()):
                entry = self._observations[key]
                lbl = dict(key)
                lbl_str_base = _format_labels(lbl)

                # Cumulative bucket counts
                cumulative = 0
                for i, bound in enumerate(self._buckets):
                    cumulative += entry["buckets"][i]
                    le_label = "+Inf" if math.isinf(bound) else f"{bound:g}"
                    if lbl:
                        inner = ",".join(
                            f'{k}="{v}"' for k, v in sorted(lbl.items())
                        )
                        bucket_lbl = "{" + inner + f',le="{le_label}"' + "}"
                    else:
                        bucket_lbl = '{le="' + le_label + '"}'
                    lines.append(f"{self.name}_bucket{bucket_lbl} {cumulative}")

                lines.append(
                    f"{self.name}_count{lbl_str_base} {entry['count']}"
                )
                lines.append(
                    f"{self.name}_sum{lbl_str_base} {entry['sum']:g}"
                )
        return "\n".join(lines)


# ══════════════════════════════════════════════════
#  PRE-DEFINED METRICS
# ══════════════════════════════════════════════════

# --- Counters ---

chat_requests_total = Counter(
    "chat_requests_total",
    "Total chat requests",
    labels=["status"],
)

tool_calls_total = Counter(
    "tool_calls_total",
    "Total tool calls",
    labels=["tool_name"],
)

cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    labels=["operation"],
)

feedback_total = Counter(
    "feedback_total",
    "Total user feedback events",
    labels=["rating"],
)

errors_total = Counter(
    "errors_total",
    "Total errors by endpoint and type",
    labels=["endpoint", "error_type"],
)

# --- Histograms ---

chat_response_duration_seconds = Histogram(
    "chat_response_duration_seconds",
    "Chat response latency in seconds",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

tool_call_duration_seconds = Histogram(
    "tool_call_duration_seconds",
    "Tool call latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],
)

# --- HTTP request metrics ---

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests by method and status",
    labels=["method", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds by method and path prefix",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30],
    labels=["method", "path"],
)

# --- Gauges ---

active_sessions = Gauge(
    "active_sessions",
    "Number of currently active sessions",
)

cache_size = Gauge(
    "cache_size",
    "Number of entries currently in the LLM response cache",
)

entities_total = Gauge(
    "entities_total",
    "Total number of entities loaded in the knowledge base",
)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 0.5=half_open, 1=open)",
    labels=["breaker"],
)


# ══════════════════════════════════════════════════
#  GENERATE PROMETHEUS TEXT EXPOSITION
# ══════════════════════════════════════════════════

def generate_metrics() -> str:
    """Return all registered metrics in Prometheus text exposition format.

    Returns a UTF-8 string ready to serve as ``text/plain; version=0.04;
    charset=utf-8`` at ``GET /metrics``.
    """
    with _registry_lock:
        metrics = list(_registry)
    blocks = [m.collect() for m in metrics]
    # Filter out empty blocks (metrics with no observations yet still emit
    # HELP/TYPE lines which is valid Prometheus format).
    return "\n\n".join(blocks) + "\n"


# ══════════════════════════════════════════════════
#  CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════

def track_chat_request(status: str, duration_seconds: float) -> None:
    """Record a chat request with its outcome and latency.

    Args:
        status: One of ``"success"``, ``"error"``, ``"cached"``,
                ``"rate_limited"``.
        duration_seconds: Wall-clock time the request took.
    """
    chat_requests_total.inc({"status": status})
    chat_response_duration_seconds.observe(value=duration_seconds)


def track_tool_call(tool_name: str, duration_seconds: float) -> None:
    """Record a tool invocation and its duration.

    Args:
        tool_name: The name of the tool that was called.
        duration_seconds: How long the tool call took.
    """
    tool_calls_total.inc({"tool_name": tool_name})
    tool_call_duration_seconds.observe(value=duration_seconds)


def track_cache(operation: str) -> None:
    """Record a cache operation.

    Args:
        operation: One of ``"hit"``, ``"miss"``, ``"eviction"``.
    """
    cache_operations_total.inc({"operation": operation})


def track_feedback(positive: bool) -> None:
    """Record user feedback.

    Args:
        positive: ``True`` for thumbs-up, ``False`` for thumbs-down.
    """
    rating = "positive" if positive else "negative"
    feedback_total.inc({"rating": rating})


def track_error(endpoint: str, error_type: str) -> None:
    """Record an error event.

    Args:
        endpoint: The API endpoint where the error occurred
                  (e.g. ``"/chat"``, ``"/admin/entities"``).
        error_type: Error classification (e.g. ``"ValueError"``,
                    ``"timeout"``, ``"llm_api_error"``).
    """
    errors_total.inc({"endpoint": endpoint, "error_type": error_type})


def track_http_request(method: str, path: str, status_code: int,
                       duration_seconds: float) -> None:
    """Record an HTTP request with method, path prefix, status, and duration."""
    status_bucket = f"{status_code // 100}xx"
    http_requests_total.inc({"method": method, "status": status_bucket})
    path_prefix = "/" + path.strip("/").split("/")[0] if path.strip("/") else "/"
    http_request_duration_seconds.observe(
        value=duration_seconds,
        labels={"method": method, "path": path_prefix},
    )


def set_gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """Set a gauge metric by name.

    Looks up the gauge in the registry by *name* and calls ``set()``.
    This is a convenience for callers that only know the metric name
    as a string (e.g. from config-driven code).

    Args:
        name: The metric name (e.g. ``"cache_size"``).
        value: The value to set.
        labels: Optional label dict matching the gauge's declared labels.

    Raises:
        KeyError: If no gauge with that name exists in the registry.
    """
    with _registry_lock:
        m = _registry_by_name.get(name)
    if m is None or not isinstance(m, Gauge):
        raise KeyError(f"No Gauge metric named '{name}' in the registry")
    m.set(labels, value)


# ══════════════════════════════════════════════════
#  MODULE-LEVEL SHORTCUTS
# ══════════════════════════════════════════════════

# For use by server.py:
#
#   from metrics import generate_metrics
#
#   @app.get("/metrics")
#   async def metrics_endpoint():
#       from fastapi.responses import PlainTextResponse
#       return PlainTextResponse(
#           generate_metrics(),
#           media_type="text/plain; version=0.04; charset=utf-8",
#       )
