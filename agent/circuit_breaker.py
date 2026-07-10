"""
vinhlong360 — Circuit Breaker & Retry Module.

Production-grade fault tolerance cho external API calls:
  1. CircuitBreaker — 3 trạng thái (CLOSED / OPEN / HALF_OPEN)
  2. RetryWithBackoff — Exponential backoff + jitter
  3. Pre-configured instances cho LLM, Weather, Web Search
  4. safe_llm_call() — convenience wrapper cho OpenAI chat completion

Mục đích:
  - Ngăn cascade failure khi LLM hoặc API ngoài sập
  - Tự phục hồi (auto-recovery) sau recovery_timeout
  - Giảm tải cho service đang gặp sự cố
  - Cung cấp fallback graceful thay vì crash

Thread-safe: mọi state mutation đều qua threading.Lock.
"""

import functools
import logging
import random
import time
from enum import Enum
from threading import Lock
from typing import Any, Callable, Optional, Sequence, Type

logger = logging.getLogger("vinhlong360.circuit_breaker")


# ══════════════════════════════════════════════════
#  CIRCUIT BREAKER
# ══════════════════════════════════════════════════

class CircuitState(Enum):
    """Trạng thái của circuit breaker."""
    CLOSED = "closed"       # Hoạt động bình thường, cho phép mọi request
    OPEN = "open"           # Đang lỗi, từ chối mọi request
    HALF_OPEN = "half_open" # Đang thử phục hồi, cho 1 vài request qua


class CircuitOpenError(Exception):
    """Raised khi circuit đang OPEN, request bị từ chối."""

    def __init__(self, breaker_name: str, recovery_remaining: float):
        self.breaker_name = breaker_name
        self.recovery_remaining = recovery_remaining
        super().__init__(
            f"Circuit '{breaker_name}' is OPEN. "
            f"Recovery in {recovery_remaining:.1f}s."
        )


class CircuitBreaker:
    """
    Circuit breaker pattern cho external service calls.

    Ba trạng thái:
      CLOSED    → Bình thường. Ghi nhận failure; nếu failures >= threshold → OPEN.
      OPEN      → Từ chối mọi call. Sau recovery_timeout → HALF_OPEN.
      HALF_OPEN → Cho phép thử lại. Nếu đủ success → CLOSED; nếu fail → OPEN.

    Args:
        name: Tên circuit (dùng trong log).
        failure_threshold: Số lần fail liên tiếp trước khi mở circuit.
        recovery_timeout: Số giây chờ trước khi thử lại (OPEN → HALF_OPEN).
        success_threshold: Số lần thành công trong HALF_OPEN để đóng circuit.
        excluded_exceptions: Tuple các exception KHÔNG tính là failure
            (vd: ValueError do input sai, không phải lỗi service).
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        excluded_exceptions: tuple = (),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions

        self._lock = Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.time()
        self._total_calls = 0
        self._total_failures = 0
        self._total_rejected = 0

    @property
    def state(self) -> CircuitState:
        """Trạng thái hiện tại (có tự chuyển OPEN → HALF_OPEN nếu hết timeout)."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    @property
    def is_healthy(self) -> bool:
        """True when the circuit is CLOSED (not degraded)."""
        return self.state == CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Thực thi func qua circuit breaker.

        Args:
            func: Hàm cần gọi.
            *args, **kwargs: Tham số truyền cho func.

        Returns:
            Kết quả của func nếu thành công.

        Raises:
            CircuitOpenError: Nếu circuit đang OPEN và chưa hết recovery timeout.
            Exception: Re-raise exception gốc nếu circuit CLOSED hoặc HALF_OPEN.
        """
        with self._lock:
            self._total_calls += 1

            # Kiểm tra trạng thái và chuyển đổi nếu cần
            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    self._total_rejected += 1
                    remaining = self._recovery_remaining()
                    raise CircuitOpenError(self.name, remaining)

        # Thực thi ngoài lock để không block thread khác
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            # Excluded exceptions không tính là circuit failure
            if isinstance(exc, self.excluded_exceptions):
                raise
            self._on_failure(exc)
            raise
        else:
            self._on_success()
            return result

    def stats(self) -> dict:
        """
        Trả về thống kê circuit breaker.

        Returns:
            dict với state, failure_count, last_failure_time, counters.
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
                "total_calls": self._total_calls,
                "total_failures": self._total_failures,
                "total_rejected": self._total_rejected,
                "recovery_remaining": (
                    self._recovery_remaining()
                    if self._state == CircuitState.OPEN
                    else 0
                ),
            }

    def reset(self):
        """Reset circuit về trạng thái CLOSED ban đầu."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            logger.info("Circuit '%s' manually reset to CLOSED", self.name)

    # ── Internal helpers ──

    def _on_success(self):
        """Xử lý khi call thành công."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(
                        "Circuit '%s' RECOVERED: HALF_OPEN -> CLOSED "
                        "(%d consecutive successes)",
                        self.name, self.success_threshold,
                    )
            elif self._state == CircuitState.CLOSED:
                # Reset failure streak on success
                self._failure_count = 0

    def _on_failure(self, exc: Exception):
        """Xử lý khi call thất bại."""
        with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Fail during recovery attempt -> back to OPEN
                self._transition_to(CircuitState.OPEN)
                self._success_count = 0
                logger.warning(
                    "Circuit '%s' recovery FAILED: HALF_OPEN -> OPEN (%s: %s)",
                    self.name, type(exc).__name__, exc,
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    logger.error(
                        "Circuit '%s' OPENED after %d consecutive failures. "
                        "Last error: %s: %s. Recovery in %ds.",
                        self.name, self._failure_count,
                        type(exc).__name__, exc,
                        self.recovery_timeout,
                    )
                else:
                    logger.warning(
                        "Circuit '%s' failure %d/%d: %s: %s",
                        self.name, self._failure_count,
                        self.failure_threshold,
                        type(exc).__name__, exc,
                    )

    def _should_attempt_recovery(self) -> bool:
        """Kiểm tra đã qua recovery timeout chưa."""
        if self._last_failure_time is None:
            return True
        return (time.time() - self._last_failure_time) >= self.recovery_timeout

    def _recovery_remaining(self) -> float:
        """Số giây còn lại trước khi thử recovery."""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.time() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def _transition_to(self, new_state: CircuitState):
        """Chuyển trạng thái (gọi trong lock)."""
        old = self._state
        self._state = new_state
        self._last_state_change = time.time()
        if old != new_state:
            logger.info(
                "Circuit '%s' state: %s -> %s",
                self.name, old.value, new_state.value,
            )

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name!r}, state={self._state.value}, "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )


# ══════════════════════════════════════════════════
#  RETRY WITH BACKOFF
# ══════════════════════════════════════════════════

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: Sequence[Type[Exception]] = (Exception,),
    jitter: bool = True,
):
    """
    Decorator: retry hàm với exponential backoff + jitter.

    Backoff schedule (jitter=False): 1s, 2s, 4s, 8s, ...
    Với jitter: thêm random [0, delay * 0.5) để tránh thundering herd.

    Args:
        max_retries: Số lần retry tối đa (không tính lần đầu).
        base_delay: Delay ban đầu (giây).
        max_delay: Delay tối đa (giây), cap exponential growth.
        retryable_exceptions: Tuple/list các exception class được phép retry.
            Chỉ retry nếu exception isinstance() của 1 trong số này.
        jitter: Thêm random jitter vào delay (recommended True).

    Returns:
        Decorated function.

    Example::

        @retry_with_backoff(max_retries=3, retryable_exceptions=(TimeoutError, ConnectionError))
        def call_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(retryable_exceptions) as exc:
                    last_exception = exc

                    if attempt == max_retries:
                        logger.error(
                            "Retry exhausted for %s after %d attempts. "
                            "Last error: %s: %s",
                            func.__name__, max_retries + 1,
                            type(exc).__name__, exc,
                        )
                        raise

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    if jitter:
                        delay += random.uniform(0, delay * 0.5)

                    logger.warning(
                        "Retry %d/%d for %s in %.2fs — %s: %s",
                        attempt + 1, max_retries,
                        func.__name__, delay,
                        type(exc).__name__, exc,
                    )
                    time.sleep(delay)
                except Exception:
                    # Non-retryable exception — raise immediately
                    raise

            # Should not reach here, but safety net
            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator


def retry_call(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: Sequence[Type[Exception]] = (Exception,),
    jitter: bool = True,
) -> Any:
    """
    Functional (non-decorator) retry: gọi func với retry + backoff.

    Dùng khi không thể dùng decorator (vd: lambda, method từ thư viện).

    Args:
        func: Hàm cần gọi.
        args: Positional args.
        kwargs: Keyword args.
        max_retries: Số lần retry tối đa.
        base_delay: Delay ban đầu (giây).
        max_delay: Delay tối đa (giây).
        retryable_exceptions: Exception types cho phép retry.
        jitter: Thêm random jitter.

    Returns:
        Kết quả của func.

    Raises:
        Exception cuối cùng nếu hết retry.
    """
    if kwargs is None:
        kwargs = {}

    @retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retryable_exceptions=retryable_exceptions,
        jitter=jitter,
    )
    def _inner():
        return func(*args, **kwargs)

    return _inner()


# ══════════════════════════════════════════════════
#  PRE-CONFIGURED INSTANCES
# ══════════════════════════════════════════════════

# LLM API: nhiều failure threshold hơn vì là core service,
# recovery nhanh (30s) để không block quá lâu.
llm_breaker = CircuitBreaker(
    name="llm_api",
    failure_threshold=5,
    recovery_timeout=30,
    success_threshold=2,
    excluded_exceptions=(ValueError, TypeError),
)

# Weather API: ít critical hơn, có fallback data sẵn,
# recovery chậm hơn (120s) vì free tier có rate limit.
weather_breaker = CircuitBreaker(
    name="weather_api",
    failure_threshold=3,
    recovery_timeout=120,
    success_threshold=2,
)

# DuckDuckGo web search: supplementary, recovery 60s.
web_search_breaker = CircuitBreaker(
    name="web_search",
    failure_threshold=3,
    recovery_timeout=60,
    success_threshold=2,
)


# ══════════════════════════════════════════════════
#  SAFE LLM CALL
# ══════════════════════════════════════════════════

_LLM_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# Catch OpenAI-specific errors if the library is available
try:
    from openai import (
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )
    _LLM_RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        OSError,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )
except ImportError:
    pass

FALLBACK_MESSAGE = (
    "Xin lỗi, hệ thống AI đang tạm gặp sự cố. "
    "Vui lòng thử lại sau ít phút. "
    "Bạn vẫn có thể tra cứu trực tiếp tại vinhlong360.vn."
)


def safe_llm_call(
    client,
    model: Optional[str] = None,
    messages: Optional[list] = None,
    timeout: float = 30.0,
    fallback_message: str = FALLBACK_MESSAGE,
    **kwargs,
):
    """
    Gọi LLM chat completion an toàn qua circuit breaker + retry.

    Kết hợp CircuitBreaker (llm_breaker) và retry_call để:
      1. Reject ngay nếu circuit đang OPEN (trả fallback).
      2. Retry tối đa 3 lần với exponential backoff nếu gặp lỗi tạm thời.
      3. Mở circuit nếu liên tục fail.

    Args:
        client: OpenAI-compatible client instance.
        model: Model name (vd: 'cx/gpt-5.4'). Nếu None, dùng kwargs.
        messages: Danh sách messages. Nếu None, dùng kwargs.
        timeout: Timeout cho mỗi request (giây).
        fallback_message: Thông báo trả về khi circuit OPEN.
        **kwargs: Tham số khác cho chat.completions.create()
            (tools, temperature, max_tokens, ...).

    Returns:
        dict với keys:
          - success (bool)
          - response: ChatCompletion object (nếu success=True)
          - message: fallback text (nếu success=False)
          - error: error info (nếu success=False)
          - circuit_state: trạng thái circuit hiện tại
    """
    if messages is not None:
        kwargs["messages"] = messages
    if model is not None:
        kwargs["model"] = model
    kwargs.setdefault("timeout", timeout)

    def _do_call():
        return client.chat.completions.create(**kwargs)

    try:
        def _retryable():
            return retry_call(
                _do_call,
                max_retries=3,
                base_delay=1.0,
                retryable_exceptions=_LLM_RETRYABLE_EXCEPTIONS,
            )
        response = llm_breaker.call(_retryable)
        return {
            "success": True,
            "response": response,
            "circuit_state": llm_breaker.state.value,
        }

    except CircuitOpenError as exc:
        logger.warning(
            "LLM call rejected — circuit OPEN (recovery in %.1fs)",
            exc.recovery_remaining,
        )
        return {
            "success": False,
            "message": fallback_message,
            "error": str(exc),
            "circuit_state": "open",
        }

    except Exception as exc:
        logger.error(
            "LLM call failed after retries: %s: %s",
            type(exc).__name__, exc,
        )
        return {
            "success": False,
            "message": fallback_message,
            "error": f"{type(exc).__name__}: {exc}",
            "circuit_state": llm_breaker.state.value,
        }


# ══════════════════════════════════════════════════
#  UTILITY: ALL BREAKERS STATUS
# ══════════════════════════════════════════════════

def all_breaker_stats() -> dict:
    """Trả về stats của tất cả pre-configured circuit breakers."""
    return {
        "llm": llm_breaker.stats(),
        "weather": weather_breaker.stats(),
        "web_search": web_search_breaker.stats(),
    }
