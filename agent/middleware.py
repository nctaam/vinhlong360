"""
vinhlong360 — Production Middleware.

Bao gồm:
  - Rate Limiting (per-IP, sliding window)
  - Structured JSON Logging
  - Error Recovery (graceful degradation)
  - Request ID tracking
  - Response time monitoring
"""

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import time
import threading
import uuid
from collections import defaultdict
from datetime import datetime
from threading import Lock
from pathlib import Path

# ══════════════════════════════════════════════════
#  STRUCTURED LOGGING
# ══════════════════════════════════════════════════

LOG_DIR = Path(__file__).resolve().parent / "data"
LOG_DIR.mkdir(exist_ok=True)


class StructuredLogger:
    """JSON-based logger with rotation support."""

    def __init__(self, name: str = "vinhlong360", max_entries: int = 5000):
        self.name = name
        self.max_entries = max_entries
        self.log_file = LOG_DIR / "server.log.jsonl"
        self._lock = Lock()
        self._buffer: list[dict] = []
        self._flush_count = 0

        # Python logging bridge — configurable via LOG_LEVEL env var
        self._py_logger = logging.getLogger(name)
        if not self._py_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self._py_logger.addHandler(handler)
            log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
            self._py_logger.setLevel(getattr(logging, log_level, logging.INFO))

    def log(self, level: str, message: str, **extra):
        entry = {
            "ts": datetime.now().isoformat(),
            "level": level,
            "msg": message,
            **extra,
        }
        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= 50:
                self._flush()

        # Console output
        if level == "error":
            self._py_logger.error(f"{message} | {json.dumps(extra, ensure_ascii=False)}")
        elif level == "warn":
            self._py_logger.warning(f"{message} | {json.dumps(extra, ensure_ascii=False)}")
        else:
            self._py_logger.info(f"{message}")

    def info(self, msg: str, **kw):
        self.log("info", msg, **kw)

    def warn(self, msg: str, **kw):
        self.log("warn", msg, **kw)

    def error(self, msg: str, **kw):
        self.log("error", msg, **kw)

    def _flush(self):
        """Write buffer to file."""
        if not self._buffer:
            return
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for entry in self._buffer:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._flush_count += len(self._buffer)
            self._buffer.clear()

            # Rotate if too large
            if self._flush_count > self.max_entries:
                self._rotate()
        except Exception:
            pass

    def _rotate(self):
        """Keep only last N entries."""
        try:
            if self.log_file.exists():
                lines = self.log_file.read_text(encoding="utf-8").strip().split("\n")
                if len(lines) > self.max_entries:
                    keep = lines[-self.max_entries:]
                    self.log_file.write_text("\n".join(keep) + "\n", encoding="utf-8")
            self._flush_count = 0
        except Exception:
            pass

    def flush(self):
        with self._lock:
            self._flush()

    def recent(self, limit: int = 100, level: str = None) -> list[dict]:
        """Get recent log entries."""
        self.flush()
        entries = []
        try:
            if self.log_file.exists():
                lines = self.log_file.read_text(encoding="utf-8").strip().split("\n")
                for line in lines[-limit * 2:]:
                    try:
                        entry = json.loads(line)
                        if level and entry.get("level") != level:
                            continue
                        entries.append(entry)
                    except Exception:
                        continue
        except Exception:
            pass
        return entries[-limit:]


# Singleton
logger = StructuredLogger()


# ══════════════════════════════════════════════════
#  RATE LIMITER
# ══════════════════════════════════════════════════

class RateLimiter:
    """Sliding window rate limiter per key (IP/session)."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """
        Check if request is allowed.
        Returns (allowed, info) where info has remaining/retry_after.
        """
        now = time.time()
        with self._lock:
            # Clean old entries
            cutoff = now - self.window
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]

            count = len(self._requests[key])
            if count >= self.max_requests:
                oldest = self._requests[key][0]
                retry_after = int(oldest + self.window - now) + 1
                return False, {
                    "remaining": 0,
                    "retry_after": retry_after,
                    "limit": self.max_requests,
                    "window": self.window,
                }

            self._requests[key].append(now)
            return True, {
                "remaining": self.max_requests - count - 1,
                "retry_after": 0,
                "limit": self.max_requests,
                "window": self.window,
            }

    def cleanup(self):
        """Remove expired entries."""
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            expired = [k for k, v in self._requests.items() if all(t < cutoff for t in v)]
            for k in expired:
                del self._requests[k]

    def stats(self) -> dict:
        with self._lock:
            return {
                "active_keys": len(self._requests),
                "max_requests": self.max_requests,
                "window_seconds": self.window,
            }


# Singletons: different limits for different endpoints
chat_limiter = RateLimiter(max_requests=30, window_seconds=60)   # 30 req/min
admin_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 10 req/min
stream_limiter = RateLimiter(max_requests=20, window_seconds=60)  # 20 req/min
report_limiter = RateLimiter(max_requests=5, window_seconds=300)  # 5 báo cáo / 5 phút (chống spam)

# Auto-cleanup: periodically remove stale IP entries every 5 minutes
_all_limiters = [chat_limiter, admin_limiter, stream_limiter, report_limiter]

def _rate_limiter_cleanup_loop():
    while True:
        time.sleep(300)  # 5 minutes
        for limiter in _all_limiters:
            limiter.cleanup()

_cleanup_thread = threading.Thread(target=_rate_limiter_cleanup_loop, daemon=True, name="rate-limiter-cleanup")
_cleanup_thread.start()


# ══════════════════════════════════════════════════
#  RESPONSE TIME TRACKER
# ══════════════════════════════════════════════════

class ResponseTimeTracker:
    """Track response times for monitoring."""

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._samples: list[dict] = []
        self._lock = Lock()

    def record(self, endpoint: str, duration_ms: float, status: int = 200):
        entry = {
            "endpoint": endpoint,
            "duration_ms": round(duration_ms, 1),
            "status": status,
            "ts": datetime.now().isoformat(),
        }
        with self._lock:
            self._samples.append(entry)
            if len(self._samples) > self.max_samples:
                self._samples = self._samples[-self.max_samples:]

    def stats(self) -> dict:
        with self._lock:
            if not self._samples:
                return {"avg_ms": 0, "p95_ms": 0, "p99_ms": 0, "count": 0}

            durations = sorted(s["duration_ms"] for s in self._samples)
            n = len(durations)
            return {
                "avg_ms": round(sum(durations) / n, 1),
                "p50_ms": durations[n // 2],
                "p95_ms": durations[int(n * 0.95)] if n > 20 else durations[-1],
                "p99_ms": durations[int(n * 0.99)] if n > 100 else durations[-1],
                "count": n,
                "by_endpoint": self._by_endpoint(),
            }

    def _by_endpoint(self) -> dict:
        groups = defaultdict(list)
        for s in self._samples[-500:]:
            groups[s["endpoint"]].append(s["duration_ms"])
        return {
            ep: {
                "avg_ms": round(sum(ds) / len(ds), 1),
                "count": len(ds),
            }
            for ep, ds in groups.items()
        }


response_tracker = ResponseTimeTracker()


# ══════════════════════════════════════════════════
#  ERROR RECOVERY
# ══════════════════════════════════════════════════

class ErrorTracker:
    """Track errors for circuit-breaking."""

    def __init__(self, threshold: int = 10, window_seconds: int = 300):
        self.threshold = threshold
        self.window = window_seconds
        self._errors: list[dict] = []
        self._lock = Lock()

    def record_error(self, endpoint: str, error: str, details: str = ""):
        with self._lock:
            self._errors.append({
                "ts": time.time(),
                "endpoint": endpoint,
                "error": error,
                "details": details[:200],
            })
            # Trim old
            cutoff = time.time() - self.window
            self._errors = [e for e in self._errors if e["ts"] > cutoff]

        logger.error(f"Endpoint error: {endpoint}", error=error, details=details[:200])

    def is_healthy(self) -> bool:
        """Check if error rate is acceptable."""
        with self._lock:
            cutoff = time.time() - self.window
            recent = [e for e in self._errors if e["ts"] > cutoff]
            return len(recent) < self.threshold

    def recent_errors(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return self._errors[-limit:]

    def stats(self) -> dict:
        with self._lock:
            cutoff = time.time() - self.window
            recent = [e for e in self._errors if e["ts"] > cutoff]
            return {
                "total_recent": len(recent),
                "threshold": self.threshold,
                "healthy": len(recent) < self.threshold,
            }


error_tracker = ErrorTracker()


# ══════════════════════════════════════════════════
#  ADMIN AUTHENTICATION
# ══════════════════════════════════════════════════

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
# True chỉ khi key được sinh tạm ở DEV — server startup mới in giá trị cho dev xài.
ADMIN_KEY_AUTOGEN = False
_IS_PRODUCTION = os.environ.get("ENVIRONMENT", "development").strip().lower() == "production"

def _generate_default_key():
    """Generate a default admin key if not set in .env."""
    return secrets.token_hex(24)

if not ADMIN_API_KEY:
    if _IS_PRODUCTION:
        # Fail-closed: KHÔNG bao giờ auto-sinh secret ở production. Admin auth tắt
        # (verify_admin_key luôn False) tới khi đặt ADMIN_API_KEY thật trong .env.
        logger.error(
            "ADMIN_API_KEY not set in production — admin endpoints DISABLED (fail-closed). "
            "Set ADMIN_API_KEY in .env."
        )
    else:
        ADMIN_API_KEY = _generate_default_key()
        ADMIN_KEY_AUTOGEN = True
        logger.warn(
            "ADMIN_API_KEY not set — generated a temporary DEV key (printed at server startup). "
            "Set ADMIN_API_KEY in .env for a stable key."
        )


def verify_admin_key(request) -> bool:
    """Verify admin API key from the X-Admin-Key header."""
    if not ADMIN_API_KEY:  # fail-closed nếu chưa cấu hình (vd prod thiếu key)
        return False
    key = request.headers.get("X-Admin-Key")
    if not key:
        return False
    return hmac.compare_digest(key, ADMIN_API_KEY)


# ══════════════════════════════════════════════════
#  HELPER: Request ID
# ══════════════════════════════════════════════════

def generate_request_id() -> str:
    return str(uuid.uuid4())[:12]


def _is_valid_ip(ip_str: str) -> bool:
    """Check if string is a valid IP address."""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except (ValueError, TypeError):
        return False

# Trusted proxy IPs — only trust X-Forwarded-For from these
TRUSTED_PROXIES = os.environ.get("TRUSTED_PROXIES", "127.0.0.1,::1").split(",")

def get_client_ip(request) -> str:
    """Extract real client IP from request with proxy validation."""
    direct_ip = request.client.host if request.client else "unknown"

    # Only trust forwarded headers if request comes from a known proxy
    if direct_ip in TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            if _is_valid_ip(candidate):
                return candidate
        real_ip = request.headers.get("X-Real-IP")
        if real_ip and _is_valid_ip(real_ip):
            return real_ip

    return direct_ip
