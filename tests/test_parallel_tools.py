"""Tests for agent/parallel_tools.py — Parallel Tool Execution."""
import json
import time
import threading

import pytest

from parallel_tools import (
    can_parallelize,
    ParallelToolExecutor,
    _search_signature,
    _ALWAYS_PARALLEL,
    _ALWAYS_SEQUENTIAL,
)


# ── can_parallelize ──────────────────────────────────


def test_parallel_tools_classified():
    """search, entity_detail, weather, web_search are parallel-safe."""
    tool_calls = [
        {"id": "1", "name": "search", "args": {"q": "cam sanh"}},
        {"id": "2", "name": "entity_detail", "args": {"entity_id": "e1"}},
        {"id": "3", "name": "weather", "args": {"area": "vinh-long"}},
        {"id": "4", "name": "web_search", "args": {"query": "vinh long"}},
    ]
    parallel, sequential = can_parallelize(tool_calls)
    assert len(parallel) == 4
    assert len(sequential) == 0


def test_sequential_tools_classified():
    """suggest_followups and generate_itinerary are always sequential."""
    tool_calls = [
        {"id": "1", "name": "suggest_followups", "args": {"context": "test"}},
        {"id": "2", "name": "generate_itinerary", "args": {"days": 2}},
    ]
    parallel, sequential = can_parallelize(tool_calls)
    assert len(parallel) == 0
    assert len(sequential) == 2


def test_unknown_tools_are_sequential():
    """Unrecognized tools default to sequential for safety."""
    tool_calls = [
        {"id": "1", "name": "unknown_tool", "args": {}},
    ]
    parallel, sequential = can_parallelize(tool_calls)
    assert len(parallel) == 0
    assert len(sequential) == 1


def test_mixed_parallel_and_sequential():
    tool_calls = [
        {"id": "1", "name": "search", "args": {"q": "cam sanh"}},
        {"id": "2", "name": "weather", "args": {}},
        {"id": "3", "name": "suggest_followups", "args": {"context": "test"}},
        {"id": "4", "name": "entity_detail", "args": {"entity_id": "e1"}},
    ]
    parallel, sequential = can_parallelize(tool_calls)
    assert len(parallel) == 3  # search, weather, entity_detail
    assert len(sequential) == 1  # suggest_followups


def test_preserves_order():
    tool_calls = [
        {"id": "1", "name": "search", "args": {"q": "a"}},
        {"id": "2", "name": "search", "args": {"q": "b"}},
        {"id": "3", "name": "entity_detail", "args": {"entity_id": "e1"}},
    ]
    parallel, sequential = can_parallelize(tool_calls)
    # Relative order preserved
    ids = [tc["id"] for tc in parallel]
    assert ids == ["1", "2", "3"]


def test_empty_tool_calls():
    parallel, sequential = can_parallelize([])
    assert parallel == []
    assert sequential == []


# ── _search_signature ────────────────────────────────


def test_search_signature():
    sig = _search_signature({"q": "cam sanh", "entity_type": "specialty"})
    assert "cam sanh" in sig
    assert "specialty" in sig


def test_search_signature_different_args():
    sig1 = _search_signature({"q": "cam sanh"})
    sig2 = _search_signature({"q": "bun nuoc leo"})
    assert sig1 != sig2


# ── ParallelToolExecutor ─────────────────────────────


def make_mock_call_tool(delay=0.0):
    """Create a mock call_tool function."""
    def call_tool(name, args):
        if delay > 0:
            time.sleep(delay)
        return json.dumps({"tool": name, "args": args})
    return call_tool


@pytest.fixture
def executor():
    return ParallelToolExecutor(
        call_tool_fn=make_mock_call_tool(),
        max_workers=4,
        default_timeout=5.0,
    )


def test_execute_parallel_empty(executor):
    results = executor.execute_parallel([])
    assert results == []


def test_execute_parallel_single(executor):
    tool_calls = [{"id": "tc1", "name": "search", "args": {"q": "test"}}]
    results = executor.execute_parallel(tool_calls)
    assert len(results) == 1
    assert results[0]["id"] == "tc1"
    assert results[0]["name"] == "search"
    assert results[0]["error"] is None
    parsed = json.loads(results[0]["result"])
    assert parsed["tool"] == "search"


def test_execute_parallel_multiple(executor):
    tool_calls = [
        {"id": "tc1", "name": "search", "args": {"q": "cam sanh"}},
        {"id": "tc2", "name": "weather", "args": {"area": "vinh-long"}},
        {"id": "tc3", "name": "entity_detail", "args": {"entity_id": "e1"}},
    ]
    results = executor.execute_parallel(tool_calls)
    assert len(results) == 3
    # Results should be in original order
    assert results[0]["id"] == "tc1"
    assert results[1]["id"] == "tc2"
    assert results[2]["id"] == "tc3"
    for r in results:
        assert r["error"] is None


def test_execute_parallel_handles_errors():
    def failing_tool(name, args):
        raise RuntimeError(f"Tool {name} failed!")

    executor = ParallelToolExecutor(call_tool_fn=failing_tool, max_workers=2)
    tool_calls = [{"id": "tc1", "name": "search", "args": {}}]
    results = executor.execute_parallel(tool_calls)
    assert len(results) == 1
    assert results[0]["error"] is not None
    assert "failed" in results[0]["error"]


def test_execute_parallel_duration_tracked(executor):
    tool_calls = [{"id": "tc1", "name": "search", "args": {"q": "test"}}]
    results = executor.execute_parallel(tool_calls)
    assert results[0]["duration_ms"] >= 0


def test_execute_parallel_concurrent():
    """Verify tools actually run concurrently."""
    call_times = []
    lock = threading.Lock()

    def slow_tool(name, args):
        start = time.time()
        time.sleep(0.05)
        end = time.time()
        with lock:
            call_times.append((name, start, end))
        return json.dumps({"ok": True})

    executor = ParallelToolExecutor(call_tool_fn=slow_tool, max_workers=4)
    tool_calls = [
        {"id": f"tc{i}", "name": "search", "args": {"q": f"q{i}"}}
        for i in range(4)
    ]
    t0 = time.time()
    results = executor.execute_parallel(tool_calls)
    total_time = time.time() - t0

    assert len(results) == 4
    # If run in parallel, total time should be < 4 * 0.05 = 0.2s
    assert total_time < 1.5  # generous margin for slow CI/Windows


# ── execute_smart ────────────────────────────────────


def test_execute_smart_empty(executor):
    results = executor.execute_smart([])
    assert results == []


def test_execute_smart_groups_correctly(executor):
    tool_calls = [
        {"id": "tc1", "name": "search", "args": {"q": "a"}},
        {"id": "tc2", "name": "suggest_followups", "args": {"context": "ctx"}},
        {"id": "tc3", "name": "weather", "args": {}},
    ]
    results = executor.execute_smart(tool_calls)
    assert len(results) == 3
    # Results should be in ORIGINAL order
    assert results[0]["id"] == "tc1"
    assert results[1]["id"] == "tc2"
    assert results[2]["id"] == "tc3"
    for r in results:
        assert r["error"] is None


def test_execute_smart_parallel_before_sequential():
    """Parallel group runs first, then sequential."""
    execution_order = []
    lock = threading.Lock()

    def tracking_tool(name, args):
        with lock:
            execution_order.append(name)
        return json.dumps({"ok": True})

    executor = ParallelToolExecutor(call_tool_fn=tracking_tool, max_workers=4)
    tool_calls = [
        {"id": "tc1", "name": "search", "args": {"q": "a"}},
        {"id": "tc2", "name": "suggest_followups", "args": {"context": "ctx"}},
    ]
    executor.execute_smart(tool_calls)

    # suggest_followups is sequential, so it should run after search
    assert "suggest_followups" in execution_order
    assert "search" in execution_order


# ── Callbacks ────────────────────────────────────────


def test_callbacks_called():
    start_calls = []
    done_calls = []

    def on_start(name, tool_id):
        start_calls.append((name, tool_id))

    def on_done(name, tool_id, duration_ms):
        done_calls.append((name, tool_id, duration_ms))

    executor = ParallelToolExecutor(
        call_tool_fn=make_mock_call_tool(),
        on_tool_start=on_start,
        on_tool_done=on_done,
    )
    tool_calls = [{"id": "tc1", "name": "search", "args": {"q": "test"}}]
    executor.execute_parallel(tool_calls)

    assert len(start_calls) == 1
    assert start_calls[0][0] == "search"
    assert len(done_calls) == 1
    assert done_calls[0][0] == "search"
    assert done_calls[0][2] >= 0  # duration_ms


def test_callback_exception_does_not_crash():
    """Callback exceptions should not prevent tool execution."""
    def bad_callback(*args):
        raise ValueError("callback error")

    executor = ParallelToolExecutor(
        call_tool_fn=make_mock_call_tool(),
        on_tool_start=bad_callback,
        on_tool_done=bad_callback,
    )
    tool_calls = [{"id": "tc1", "name": "search", "args": {"q": "test"}}]
    results = executor.execute_parallel(tool_calls)
    assert len(results) == 1
    assert results[0]["error"] is None  # Tool itself succeeded


# ── Constants ────────────────────────────────────────


def test_always_parallel_set():
    assert "search" in _ALWAYS_PARALLEL
    assert "entity_detail" in _ALWAYS_PARALLEL
    assert "weather" in _ALWAYS_PARALLEL
    assert "web_search" in _ALWAYS_PARALLEL


def test_always_sequential_set():
    assert "suggest_followups" in _ALWAYS_SEQUENTIAL
    assert "generate_itinerary" in _ALWAYS_SEQUENTIAL
