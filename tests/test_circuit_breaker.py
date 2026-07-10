"""Tests for agent/circuit_breaker.py — Circuit Breaker & Retry."""
import time

import pytest

from circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    all_breaker_stats,
    llm_breaker,
    weather_breaker,
    web_search_breaker,
)


@pytest.fixture
def breaker():
    """Fresh circuit breaker with low thresholds for testing."""
    return CircuitBreaker(
        name="test",
        failure_threshold=3,
        recovery_timeout=0.1,  # 100ms for fast tests
        success_threshold=2,
    )


# ── State transitions ────────────────────────────────


def test_initial_state_is_closed(breaker):
    assert breaker.state == CircuitState.CLOSED


def test_closed_to_open_on_failures(breaker):
    """After failure_threshold consecutive failures, state goes to OPEN."""
    for i in range(3):
        with pytest.raises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

    assert breaker._state == CircuitState.OPEN


def test_open_rejects_calls(breaker):
    """OPEN state rejects all calls with CircuitOpenError."""
    # Force to OPEN
    for i in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass

    with pytest.raises(CircuitOpenError) as exc_info:
        breaker.call(lambda: "should not execute")
    assert "test" in str(exc_info.value)


def test_open_to_half_open_after_timeout(breaker):
    """After recovery_timeout, OPEN transitions to HALF_OPEN."""
    for i in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass

    assert breaker._state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(0.15)

    # Accessing state should trigger transition
    assert breaker.state == CircuitState.HALF_OPEN


def test_half_open_to_closed_on_successes(breaker):
    """After success_threshold successes in HALF_OPEN, state goes to CLOSED."""
    # Force to OPEN
    for i in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass

    # Wait for recovery timeout
    time.sleep(0.15)

    # Two successful calls should close the circuit (success_threshold=2)
    breaker.call(lambda: "ok")
    breaker.call(lambda: "ok")

    assert breaker._state == CircuitState.CLOSED


def test_half_open_to_open_on_failure(breaker):
    """A failure in HALF_OPEN sends state back to OPEN."""
    # Force to OPEN
    for i in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass

    time.sleep(0.15)  # Wait for recovery

    # One failure in HALF_OPEN
    with pytest.raises(RuntimeError):
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail again")))

    assert breaker._state == CircuitState.OPEN


def test_successful_calls_reset_failure_count(breaker):
    """A success in CLOSED state resets the failure counter."""
    # Two failures (below threshold)
    for i in range(2):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass

    assert breaker._failure_count == 2

    # Successful call resets count
    breaker.call(lambda: "success")
    assert breaker._failure_count == 0


# ── Excluded exceptions ──────────────────────────────


def test_excluded_exceptions_not_counted():
    """Excluded exceptions should not increment failure count."""
    cb = CircuitBreaker(
        name="excl_test",
        failure_threshold=3,
        excluded_exceptions=(ValueError,),
    )

    for i in range(5):
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("input error")))

    # Should still be CLOSED since ValueError is excluded
    assert cb._state == CircuitState.CLOSED
    assert cb._failure_count == 0


# ── Return value ─────────────────────────────────────


def test_call_returns_function_result(breaker):
    result = breaker.call(lambda: 42)
    assert result == 42


def test_call_passes_args(breaker):
    result = breaker.call(lambda x, y: x + y, 3, 4)
    assert result == 7


def test_call_passes_kwargs(breaker):
    result = breaker.call(lambda x=0: x * 2, x=5)
    assert result == 10


# ── Stats ────────────────────────────────────────────


def test_stats_structure(breaker):
    stats = breaker.stats()
    assert stats["name"] == "test"
    assert stats["state"] == "closed"
    assert "failure_count" in stats
    assert "total_calls" in stats
    assert "total_failures" in stats
    assert "total_rejected" in stats


def test_stats_track_calls(breaker):
    breaker.call(lambda: "ok")
    stats = breaker.stats()
    assert stats["total_calls"] == 1


def test_stats_track_failures(breaker):
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    except RuntimeError:
        pass
    stats = breaker.stats()
    assert stats["total_failures"] == 1


def test_stats_track_rejections(breaker):
    """When circuit is OPEN, rejected calls are counted."""
    for i in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass

    try:
        breaker.call(lambda: "rejected")
    except CircuitOpenError:
        pass

    stats = breaker.stats()
    assert stats["total_rejected"] >= 1


# ── Reset ────────────────────────────────────────────


def test_reset(breaker):
    # Force to OPEN
    for i in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass

    breaker.reset()
    assert breaker._state == CircuitState.CLOSED
    assert breaker._failure_count == 0


# ── Pre-configured breakers ──────────────────────────


def test_preconfigured_llm_breaker():
    assert llm_breaker.name == "llm_api"
    assert llm_breaker.failure_threshold == 5
    assert llm_breaker.recovery_timeout == 30
    assert ValueError in llm_breaker.excluded_exceptions


def test_preconfigured_weather_breaker():
    assert weather_breaker.name == "weather_api"
    assert weather_breaker.failure_threshold == 3
    assert weather_breaker.recovery_timeout == 120


def test_preconfigured_web_search_breaker():
    assert web_search_breaker.name == "web_search"
    assert web_search_breaker.failure_threshold == 3
    assert web_search_breaker.recovery_timeout == 60


# ── all_breaker_stats ────────────────────────────────


def test_all_breaker_stats_structure():
    stats = all_breaker_stats()
    assert "llm" in stats
    assert "weather" in stats
    assert "web_search" in stats
    assert stats["llm"]["name"] == "llm_api"
    assert stats["weather"]["name"] == "weather_api"
    assert stats["web_search"]["name"] == "web_search"


# ── CircuitOpenError ─────────────────────────────────


def test_circuit_open_error_attributes():
    err = CircuitOpenError("my_breaker", 15.5)
    assert err.breaker_name == "my_breaker"
    assert err.recovery_remaining == 15.5
    assert "my_breaker" in str(err)
    assert "15.5" in str(err)


# ── repr ─────────────────────────────────────────────


def test_repr(breaker):
    r = repr(breaker)
    assert "test" in r
    assert "closed" in r
