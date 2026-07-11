"""
vinhlong360 — Production Middleware.

Bao gồm:
  - Rate Limiting (per-IP, sliding window)
  - Structured JSON Logging
  - Error Recovery (graceful degradation)
  - Request ID tracking
  - Response time monitoring
"""

import contextvars
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
from datetime import datetime, timezone
from threading import Lock
from pathlib import Path

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

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
        rid = _request_id_var.get("")
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "msg": message,
        }
        if rid:
            entry["req_id"] = rid
        entry.update(extra)
        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= 50:
                self._flush()

        # Console output
        if level == "error":
            self._py_logger.error("%s | %s", message, json.dumps(extra, ensure_ascii=False))
        elif level == "warn":
            self._py_logger.warning("%s | %s", message, json.dumps(extra, ensure_ascii=False))
        else:
            self._py_logger.info("%s", message)

    def info(self, msg: str, **kw):
        self.log("info", msg, **kw)

    def warn(self, msg: str, **kw):
        self.log("warn", msg, **kw)

    def warning(self, msg: str, **kw):
        self.log("warn", msg, **kw)

    def error(self, msg: str, **kw):
        self.log("error", msg, **kw)

    def debug(self, msg: str, **kw):
        self.log("debug", msg, **kw)

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
        except Exception as exc:
            self._py_logger.debug("Log flush failed: %s", exc)

    def _rotate(self):
        """Keep only last N entries (streaming read to avoid loading entire file)."""
        try:
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if len(lines) > self.max_entries:
                    keep = lines[-self.max_entries:]
                    with open(self.log_file, "w", encoding="utf-8") as f:
                        f.writelines(keep)
            self._flush_count = 0
        except Exception as exc:
            self._py_logger.debug("Log rotation failed: %s", exc)

    def flush(self):
        with self._lock:
            self._flush()

    def recent(self, limit: int = 100, level: str = None) -> list[dict]:
        """Get recent log entries."""
        self.flush()
        entries = []
        try:
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for line in lines[-limit * 2:]:
                    try:
                        entry = json.loads(line)
                        if level and entry.get("level") != level:
                            continue
                        entries.append(entry)
                    except Exception as e:
                        self._py_logger.debug("Skipping malformed log line: %s", e)
                        continue
        except Exception as exc:
            self._py_logger.debug("Failed to read log file: %s", exc)
        return entries[-limit:]


class _StructuredLogBridge(logging.Handler):
    """Routes Python stdlib logging calls to StructuredLogger JSONL output."""

    _LEVEL_MAP = {"WARNING": "warn", "ERROR": "error", "CRITICAL": "error", "DEBUG": "debug"}

    def __init__(self, slogger: StructuredLogger):
        super().__init__(level=logging.INFO)
        self._slogger = slogger

    def emit(self, record: logging.LogRecord):
        if record.name == self._slogger.name:
            return
        level = self._LEVEL_MAP.get(record.levelname, "info")
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        self._slogger.log(level, msg, module=record.name)


class _SSEAccessLogFilter(logging.Filter):
    """Keep long-lived notification SSE handshakes out of access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "uvicorn.access":
            return True
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        return "/api/notifications/stream" not in msg


# Singleton
logger = StructuredLogger()

# Bridge: all Python loggers → structured JSONL
_bridge = _StructuredLogBridge(logger)
logging.getLogger().addHandler(_bridge)
logging.getLogger("uvicorn.access").addFilter(_SSEAccessLogFilter())


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
admin_limiter = RateLimiter(max_requests=60, window_seconds=60)  # 60 req/min


def _reset_limiters() -> None:
    """Test-only: xoá state của mọi limiter singleton (TestClient dùng chung IP nên
    state cộng dồn qua cả suite → 429 giả ở test không tự-reset)."""
    for lim in (chat_limiter, admin_limiter):
        with lim._lock:
            lim._requests.clear()
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
            "ts": datetime.now(timezone.utc).isoformat(),
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

    def __init__(self, threshold: int = 50, window_seconds: int = 300):
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

        logger.error("Endpoint error: " + endpoint, error=error, details=details[:200])

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
    valid = hmac.compare_digest(key, ADMIN_API_KEY)
    if not valid:
        _log_admin_key_failure(request)
    return valid


def _log_admin_key_failure(request):
    """Deferred logging — security_logger defined later in this module."""
    try:
        ip = get_client_ip(request)
        path = getattr(request, "url", None)
        security_logger.admin_key_failure(ip, endpoint=str(path) if path else "")
    except Exception:
        logger.debug("Admin key failure logging failed", exc_info=True)


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
TRUSTED_PROXIES = [ip.strip() for ip in os.environ.get("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if ip.strip()]

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


# ══════════════════════════════════════════════════
#  SECURITY EVENT LOGGING
# ══════════════════════════════════════════════════

def _mask_ip(ip: str) -> str:
    if not ip:
        return ""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.*{parts[3][-1:]}"
    if ":" in ip:
        return ip[:ip.rfind(":")] + ":****"
    return ip[:4] + "****"


def _mask_phone(phone: str) -> str:
    if not phone or len(phone) < 6:
        return "***"
    return phone[:3] + "****" + phone[-3:]


class SecurityEventLogger:
    """Structured logging for security-relevant events (audit trail).

    All events go to the same StructuredLogger (server.log.jsonl) with
    level="security" so they can be filtered/exported separately.
    PII (IP, phone) is masked before writing to log files.
    """

    _EVENT_AUTH_FAILURE = "auth_failure"
    _EVENT_RATE_LIMIT = "rate_limit_hit"
    _EVENT_SUSPICIOUS_INPUT = "suspicious_input"
    _EVENT_ADMIN_KEY_FAILURE = "admin_key_failure"
    _EVENT_SESSION_ANOMALY = "session_anomaly"
    _EVENT_CSRF_FAILURE = "csrf_failure"

    _PII_FIELDS = {"ip", "phone", "user_phone"}

    def __init__(self, structured_logger: StructuredLogger):
        self._log = structured_logger
        self._lock = Lock()
        self._recent_events: list[dict] = []
        self._max_recent = 500

    @staticmethod
    def _mask_pii(entry: dict) -> dict:
        masked = dict(entry)
        if "ip" in masked:
            masked["ip"] = _mask_ip(masked["ip"])
        for k in ("phone", "user_phone"):
            if k in masked:
                masked[k] = _mask_phone(masked[k])
        return masked

    def _record(self, event_type: str, ip: str, **details):
        entry = {
            "event": event_type,
            "ip": ip,
            "ts": datetime.now(timezone.utc).isoformat(),
            **details,
        }
        self._log.log("security", f"[SEC] {event_type}", **self._mask_pii(entry))
        with self._lock:
            self._recent_events.append(entry)
            if len(self._recent_events) > self._max_recent:
                self._recent_events = self._recent_events[-self._max_recent:]

    def auth_failure(self, ip: str, reason: str, endpoint: str = "", **kw):
        self._record(self._EVENT_AUTH_FAILURE, ip, reason=reason, endpoint=endpoint, **kw)

    def rate_limit_hit(self, ip: str, endpoint: str, key: str = ""):
        self._record(self._EVENT_RATE_LIMIT, ip, endpoint=endpoint, key=key)

    def suspicious_input(self, ip: str, endpoint: str, detail: str):
        self._record(self._EVENT_SUSPICIOUS_INPUT, ip, endpoint=endpoint,
                      detail=detail[:200])

    def admin_key_failure(self, ip: str, endpoint: str = ""):
        self._record(self._EVENT_ADMIN_KEY_FAILURE, ip, endpoint=endpoint)

    def session_anomaly(self, ip: str, reason: str, **kw):
        self._record(self._EVENT_SESSION_ANOMALY, ip, reason=reason, **kw)

    def csrf_failure(self, ip: str, endpoint: str = ""):
        self._record(self._EVENT_CSRF_FAILURE, ip, endpoint=endpoint)

    def recent(self, limit: int = 100, event_type: str = None) -> list[dict]:
        with self._lock:
            events = self._recent_events
            if event_type:
                events = [e for e in events if e.get("event") == event_type]
            return events[-limit:]

    def stats(self) -> dict:
        with self._lock:
            by_type: dict[str, int] = defaultdict(int)
            for e in self._recent_events:
                by_type[e.get("event", "unknown")] += 1
            return {
                "total_events": len(self._recent_events),
                "by_type": dict(by_type),
            }


security_logger = SecurityEventLogger(logger)


# ══════════════════════════════════════════════════
#  IP REPUTATION & THREAT SCORING
# ══════════════════════════════════════════════════

class IPReputationTracker:
    """Per-IP threat scoring with progressive escalation.

    Threat levels:
      0 = clean (no action)
      1 = suspicious (log only)
      2 = elevated (stricter rate limits)
      3 = hostile (temporary block recommended)

    Points decay over time (half-life = decay_seconds). Each security event
    adds points to the IP's score.  Callers check threat_level() and decide
    whether to allow/throttle/block.
    """

    _POINT_MAP = {
        "auth_failure": 2,
        "rate_limit_hit": 1,
        "suspicious_input": 3,
        "admin_key_failure": 5,
        "csrf_failure": 3,
        "session_anomaly": 2,
        "xss_attempt": 5,
        "sqli_attempt": 5,
    }
    _LEVEL_THRESHOLDS = (5, 15, 30)  # suspicious, elevated, hostile

    def __init__(self, decay_seconds: int = 900, max_ips: int = 10_000):
        self._scores: dict[str, list[tuple[float, int]]] = {}
        self._lock = Lock()
        self._decay = decay_seconds
        self._max_ips = max_ips

    def record(self, ip: str, event_type: str) -> int:
        """Record a security event for an IP. Returns new threat level."""
        points = self._POINT_MAP.get(event_type, 1)
        now = time.time()
        with self._lock:
            if ip not in self._scores:
                self._scores[ip] = []
            self._scores[ip].append((now, points))
            if len(self._scores[ip]) > 500:
                cutoff = now - self._decay
                self._scores[ip] = [(t, p) for t, p in self._scores[ip] if t > cutoff]
            if len(self._scores) > self._max_ips:
                self._gc(now)
            return self._level_locked(ip, now)

    def threat_level(self, ip: str) -> int:
        """Current threat level for an IP (0-3)."""
        now = time.time()
        with self._lock:
            return self._level_locked(ip, now)

    def _level_locked(self, ip: str, now: float) -> int:
        entries = self._scores.get(ip, [])
        total = 0.0
        for ts, pts in entries:
            age = now - ts
            if age < self._decay:
                # linear decay within window
                weight = 1.0 - (age / self._decay)
                total += pts * weight
        for i, threshold in enumerate(self._LEVEL_THRESHOLDS):
            if total < threshold:
                return i
        return len(self._LEVEL_THRESHOLDS)

    def score(self, ip: str) -> float:
        """Raw weighted score for an IP (for diagnostics)."""
        now = time.time()
        with self._lock:
            entries = self._scores.get(ip, [])
            total = 0.0
            for ts, pts in entries:
                age = now - ts
                if age < self._decay:
                    total += pts * (1.0 - age / self._decay)
            return round(total, 2)

    def _gc(self, now: float):
        cutoff = now - self._decay
        dead = [ip for ip, entries in self._scores.items()
                if not entries or entries[-1][0] < cutoff]
        for ip in dead:
            del self._scores[ip]

    def stats(self) -> dict:
        with self._lock:
            levels = {0: 0, 1: 0, 2: 0, 3: 0}
            now = time.time()
            for ip in self._scores:
                lvl = self._level_locked(ip, now)
                levels[lvl] = levels.get(lvl, 0) + 1
            return {
                "tracked_ips": len(self._scores),
                "by_level": levels,
            }

    def _reset(self):
        """Test-only."""
        with self._lock:
            self._scores.clear()


ip_reputation = IPReputationTracker()


# Wire security_logger → ip_reputation: every logged security event also
# updates the IP's threat score.
_orig_record = security_logger._record

def _record_with_reputation(event_type: str, ip: str, **details):
    _orig_record(event_type, ip, **details)
    if ip and ip != "unknown":
        ip_reputation.record(ip, event_type)

security_logger._record = _record_with_reputation


# ══════════════════════════════════════════════════
#  CREDENTIAL STUFFING DETECTION
# ══════════════════════════════════════════════════

class CredentialStuffingDetector:
    """Detect credential stuffing attacks: same IP failing login across many accounts.

    Credential stuffing = attacker tries leaked username/password pairs from
    breaches against our login endpoint. Pattern: one IP, many different usernames,
    all failing authentication within a short window.
    """

    def __init__(self, window: int = 300, username_threshold: int = 5, max_ips: int = 10_000):
        self._attempts: dict[str, list[tuple[float, str]]] = {}
        self._lock = Lock()
        self._window = window
        self._username_threshold = username_threshold
        self._max_ips = max_ips

    def record_failure(self, ip: str, username: str) -> dict:
        """Record a login failure. Returns {is_stuffing: bool, unique_accounts: int}"""
        now = time.time()
        with self._lock:
            if ip not in self._attempts:
                self._attempts[ip] = []
            self._attempts[ip].append((now, username))
            # Prune old entries
            cutoff = now - self._window
            self._attempts[ip] = [(t, u) for t, u in self._attempts[ip] if t > cutoff]
            unique = len({u for _, u in self._attempts[ip]})

            if len(self._attempts) > self._max_ips:
                self._gc(now)

            is_stuffing = unique >= self._username_threshold
            if is_stuffing:
                security_logger._record("credential_stuffing", ip,
                                        unique_accounts=unique,
                                        window_seconds=self._window)
            return {"is_stuffing": is_stuffing, "unique_accounts": unique}

    def is_suspicious(self, ip: str) -> bool:
        """Check if an IP is currently flagged for credential stuffing."""
        now = time.time()
        with self._lock:
            entries = self._attempts.get(ip, [])
            recent = [(t, u) for t, u in entries if now - t < self._window]
            unique = len({u for _, u in recent})
            return unique >= self._username_threshold

    def _gc(self, now: float):
        cutoff = now - self._window
        dead = [ip for ip, entries in self._attempts.items()
                if not entries or entries[-1][0] < cutoff]
        for ip in dead:
            del self._attempts[ip]

    def stats(self) -> dict:
        with self._lock:
            return {
                "tracked_ips": len(self._attempts),
                "window_seconds": self._window,
                "threshold": self._username_threshold,
            }

    def _reset(self):
        with self._lock:
            self._attempts.clear()


credential_stuffing = CredentialStuffingDetector()


# ══════════════════════════════════════════════════
#  SECURITY EVENT CORRELATION ENGINE
# ══════════════════════════════════════════════════

def _correlator_pattern_matches(pattern: dict, entries: list, now: float) -> bool:
    """Return True if `entries` match a single attack pattern within its window."""
    window = pattern.get("window", 300)
    recent = [(t, e) for t, e in entries if now - t < window]
    if not recent:
        return False

    min_count = pattern.get("min_count", 3)
    if len(recent) < min_count:
        return False

    # Multi-vector pattern: check distinct event types
    if "min_distinct_types" in pattern:
        distinct = len({e for _, e in recent})
        return distinct >= pattern["min_distinct_types"]

    # Standard pattern: check required events
    required = pattern.get("required_events", set())
    event_types = {e for _, e in recent}
    if required and required & event_types:
        type_count = sum(1 for _, e in recent if e in required)
        return type_count >= min_count
    return False


class SecurityEventCorrelator:
    """Cross-reference multiple weak security signals into strong threat indicators.

    A single auth failure is noise. But auth_failure + suspicious_input + rate_limit_hit
    from the same IP within 5 minutes = active attack. This engine detects those patterns.
    """

    _ATTACK_PATTERNS = {
        "brute_force": {
            "required_events": {"auth_failure"},
            "min_count": 5,
            "window": 300,
        },
        "scanning": {
            "required_events": {"admin_key_failure", "suspicious_input"},
            "min_count": 3,
            "window": 300,
        },
        "content_abuse": {
            "required_events": {"rate_limit_hit"},
            "optional_events": {"suspicious_input", "csrf_failure"},
            "min_count": 3,
            "window": 600,
        },
        "multi_vector": {
            "min_distinct_types": 3,
            "min_count": 5,
            "window": 600,
        },
    }

    def __init__(self):
        self._events: dict[str, list[tuple[float, str]]] = {}
        self._lock = Lock()
        self._max_ips = 10_000
        self._alerts: list[dict] = []
        self._max_alerts = 200

    def ingest(self, ip: str, event_type: str):
        """Ingest a security event and check for attack patterns."""
        now = time.time()
        with self._lock:
            if ip not in self._events:
                self._events[ip] = []
            self._events[ip].append((now, event_type))

            if len(self._events) > self._max_ips:
                self._gc(now)

        return self.check(ip)

    def check(self, ip: str) -> dict:
        """Check if an IP matches any known attack pattern.

        Returns {is_attack: bool, patterns: list[str], severity: str}
        """
        now = time.time()
        matched = []
        with self._lock:
            entries = self._events.get(ip, [])

            for name, pattern in self._ATTACK_PATTERNS.items():
                if _correlator_pattern_matches(pattern, entries, now):
                    matched.append(name)

            if matched:
                self._append_alert_locked(ip, matched)

        return {
            "is_attack": bool(matched),
            "patterns": matched,
            "severity": "critical" if len(matched) >= 2 else ("high" if matched else "none"),
        }

    def _append_alert_locked(self, ip: str, matched: list) -> None:
        """Append a correlator alert (caller holds self._lock)."""
        severity = "critical" if len(matched) >= 2 else "high"
        alert = {
            "ip": ip,
            "patterns": matched,
            "severity": severity,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._alerts.append(alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

    def recent_alerts(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return self._alerts[-limit:]

    def stats(self) -> dict:
        with self._lock:
            return {
                "tracked_ips": len(self._events),
                "total_alerts": len(self._alerts),
            }

    def _gc(self, now: float):
        max_window = max(p.get("window", 300) for p in self._ATTACK_PATTERNS.values())
        cutoff = now - max_window
        dead = [ip for ip, entries in self._events.items()
                if not entries or entries[-1][0] < cutoff]
        for ip in dead:
            del self._events[ip]

    def _reset(self):
        with self._lock:
            self._events.clear()
            self._alerts.clear()


event_correlator = SecurityEventCorrelator()

# Wire: every security event also feeds the correlator
_record_before_correlator = security_logger._record


def _record_with_correlation(event_type: str, ip: str, **details):
    _record_before_correlator(event_type, ip, **details)
    if ip and ip != "unknown":
        event_correlator.ingest(ip, event_type)


security_logger._record = _record_with_correlation


# ══════════════════════════════════════════════════
#  REQUEST ANOMALY DETECTION
# ══════════════════════════════════════════════════

class RequestAnomalyDetector:
    """Detect anomalous request patterns that indicate automated attacks.

    Checks:
    - Entropy analysis: random-looking payloads (fuzzing)
    - Encoding attacks: excessive URL encoding, UTF-8 overlong sequences
    - Header anomalies: missing standard headers, unusual header combinations
    """

    @staticmethod
    def check_payload_entropy(payload: str) -> dict:
        """Calculate Shannon entropy of a payload to detect fuzzing/random data.

        Normal text: entropy 3-5 bits/char
        Random/encoded: entropy > 5.5 bits/char
        Returns {entropy: float, is_anomalous: bool}
        """
        if not payload or len(payload) < 20:
            return {"entropy": 0.0, "is_anomalous": False}
        import math
        freq: dict[str, int] = {}
        for c in payload:
            freq[c] = freq.get(c, 0) + 1
        length = len(payload)
        entropy = -sum(
            (count / length) * math.log2(count / length)
            for count in freq.values()
        )
        return {
            "entropy": round(entropy, 3),
            "is_anomalous": entropy > 5.5,
        }

    @staticmethod
    def check_encoding_attack(value: str) -> dict:
        """Detect encoding-based attacks (double encoding, overlong UTF-8, etc).

        Returns {is_attack: bool, reasons: list[str]}
        """
        if not value:
            return {"is_attack": False, "reasons": []}
        reasons = []
        # Double URL encoding
        if '%25' in value:
            reasons.append("double_url_encoding")
        # Excessive URL encoding (>30% of chars are %XX)
        percent_count = value.count('%')
        if len(value) > 10 and percent_count / len(value) > 0.3:
            reasons.append("excessive_url_encoding")
        # Null bytes
        if '%00' in value or '\x00' in value:
            reasons.append("null_byte")
        # Unicode tricks
        if '﻿' in value or '​' in value or '‎' in value:
            reasons.append("invisible_unicode")
        return {"is_attack": bool(reasons), "reasons": reasons}

    @staticmethod
    def check_header_anomalies(headers: dict) -> dict:
        """Detect suspicious header combinations.

        Returns {score: float, reasons: list[str]}
        """
        reasons = []
        score = 0.0

        # Missing Accept header (all real browsers send it)
        if not headers.get("accept"):
            reasons.append("missing_accept")
            score += 0.2

        # Missing Accept-Language (real browsers always send it)
        if not headers.get("accept-language"):
            reasons.append("missing_accept_language")
            score += 0.2

        # Connection: close (unusual for modern clients)
        if headers.get("connection", "").lower() == "close":
            reasons.append("connection_close")
            score += 0.1

        # X-Forwarded-For without being behind a proxy (could be spoofing)
        if headers.get("x-forwarded-for") and not headers.get("via"):
            reasons.append("xff_without_via")
            score += 0.1

        return {"score": round(score, 2), "reasons": reasons}


request_anomaly = RequestAnomalyDetector()


# ══════════════════════════════════════════════════
#  HONEYPOT / CANARY ENDPOINTS
# ══════════════════════════════════════════════════

class HoneypotTracker:
    """Track access to honeypot/canary endpoints.

    Honeypot endpoints are fake paths that no legitimate user would access:
    /admin/phpmyadmin, /wp-login.php, /.env, etc. Any access is 100% scanner.
    """

    HONEYPOT_PATHS = frozenset({
        "/admin/phpmyadmin",
        "/phpmyadmin",
        "/wp-login.php",
        "/wp-admin",
        "/.env",
        "/.git/config",
        "/.git/HEAD",
        "/actuator",
        "/actuator/health",
        "/debug/vars",
        "/server-status",
        "/server-info",
        "/.aws/credentials",
        "/config.php",
        "/xmlrpc.php",
        "/api/v1/admin/debug",
        "/solr/admin",
        "/console",
        "/_debug",
        "/telescope",
    })

    def __init__(self):
        self._hits: dict[str, list[tuple[float, str]]] = {}
        self._lock = Lock()
        self._max_ips = 10_000

    def check(self, path: str, ip: str) -> dict:
        """Check if a request path is a honeypot. If so, record the IP.

        Returns {is_honeypot: bool, path: str}
        """
        normalized = path.rstrip("/").lower()
        if normalized not in self.HONEYPOT_PATHS:
            return {"is_honeypot": False, "path": ""}

        now = time.time()
        with self._lock:
            if ip not in self._hits:
                self._hits[ip] = []
            self._hits[ip].append((now, normalized))

            if len(self._hits) > self._max_ips:
                cutoff = now - 3600
                dead = [k for k, v in self._hits.items()
                        if not v or v[-1][0] < cutoff]
                for k in dead:
                    del self._hits[k]

        # Auto-escalate IP reputation
        ip_reputation.record(ip, "suspicious_input")
        security_logger._record("honeypot_hit", ip, path=normalized)

        return {"is_honeypot": True, "path": normalized}

    def get_scanner_ips(self, min_hits: int = 1) -> list[str]:
        """Get IPs that have hit honeypot endpoints."""
        now = time.time()
        cutoff = now - 3600
        with self._lock:
            return [
                ip for ip, hits in self._hits.items()
                if len([t for t, _ in hits if t > cutoff]) >= min_hits
            ]

    def stats(self) -> dict:
        with self._lock:
            return {
                "tracked_ips": len(self._hits),
                "total_hits": sum(len(h) for h in self._hits.values()),
            }

    def _reset(self):
        with self._lock:
            self._hits.clear()


honeypot = HoneypotTracker()


# ══════════════════════════════════════════════════
#  CIRCUIT BREAKER (downstream service protection)
# ══════════════════════════════════════════════════

class CircuitBreaker:
    """Circuit breaker for downstream service calls.

    States:
      CLOSED  — normal operation, requests pass through
      OPEN    — circuit tripped, all requests fail fast
      HALF_OPEN — one test request allowed, success closes, failure re-opens

    Prevents cascade failures when a downstream service (OpenAI, Vision API, DB) is down.
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._lock = Lock()

    @property
    def state(self) -> str:
        now = time.time()
        with self._lock:
            if self._state == self.STATE_OPEN:
                if now - self._last_failure_time > self.recovery_timeout:
                    self._state = self.STATE_HALF_OPEN
                    self._success_count = 0
            return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        s = self.state
        return s != self.STATE_OPEN

    def record_success(self):
        """Record a successful downstream call."""
        with self._lock:
            self._failure_count = 0
            if self._state == self.STATE_HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = self.STATE_CLOSED
            else:
                self._state = self.STATE_CLOSED

    def record_failure(self):
        """Record a failed downstream call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == self.STATE_HALF_OPEN:
                self._state = self.STATE_OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = self.STATE_OPEN

    def stats(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
            }

    def _reset(self):
        with self._lock:
            self._state = self.STATE_CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = 0.0


# Pre-configured circuit breakers for downstream services
cb_moderation_api = CircuitBreaker("moderation_api", failure_threshold=3, recovery_timeout=30)
cb_vision_api = CircuitBreaker("vision_api", failure_threshold=3, recovery_timeout=60)


# ══════════════════════════════════════════════════
#  UNIFIED ABUSE SCORE CALCULATOR
# ══════════════════════════════════════════════════

class AbuseScoreCalculator:
    """Unified threat scoring that combines all security signals into one score.

    Ingests signals from IP reputation, rate limiting, content analysis,
    behavioral analysis, and honeypot hits to produce a 0-100 abuse score.
    """

    _SIGNAL_WEIGHTS = {
        "ip_reputation": 25,
        "rate_violations": 15,
        "honeypot_hits": 30,
        "credential_stuffing": 20,
        "event_correlation": 20,
        "bot_detection": 10,
    }

    def calculate(self, ip: str, extra_signals: dict = None) -> dict:
        """Calculate unified abuse score for an IP.

        Returns {score: int (0-100), level: str, signals: dict}
        """
        signals = {}
        score = 0.0

        # IP reputation component
        rep_level = ip_reputation.threat_level(ip)
        rep_score = {0: 0, 1: 30, 2: 60, 3: 100}.get(rep_level, 0)
        signals["ip_reputation"] = rep_score
        score += rep_score * self._SIGNAL_WEIGHTS["ip_reputation"] / 100

        # Credential stuffing component
        is_stuffing = credential_stuffing.is_suspicious(ip)
        stuff_score = 100 if is_stuffing else 0
        signals["credential_stuffing"] = stuff_score
        score += stuff_score * self._SIGNAL_WEIGHTS["credential_stuffing"] / 100

        # Event correlation component
        corr = event_correlator.check(ip)
        corr_score = {"none": 0, "high": 70, "critical": 100}.get(corr["severity"], 0)
        signals["event_correlation"] = corr_score
        score += corr_score * self._SIGNAL_WEIGHTS["event_correlation"] / 100

        # Honeypot component
        honeypot_ips = honeypot.get_scanner_ips()
        hp_score = 100 if ip in honeypot_ips else 0
        signals["honeypot_hits"] = hp_score
        score += hp_score * self._SIGNAL_WEIGHTS["honeypot_hits"] / 100

        # Extra signals from caller
        if extra_signals:
            if extra_signals.get("is_bot"):
                bot_score = 80
                signals["bot_detection"] = bot_score
                score += bot_score * self._SIGNAL_WEIGHTS["bot_detection"] / 100

        total = min(100, int(score))
        level = "clean"
        if total >= 80:
            level = "critical"
        elif total >= 50:
            level = "high"
        elif total >= 25:
            level = "elevated"
        elif total > 0:
            level = "low"

        return {"score": total, "level": level, "signals": signals}


abuse_score = AbuseScoreCalculator()


# ══════════════════════════════════════════════════
#  GEO-ANOMALY DETECTION (impossible travel)
# ══════════════════════════════════════════════════

class GeoAnomalyDetector:
    """Detect impossible travel: login from different geo regions too quickly.

    Uses IP class changes as a proxy for geographic distance (no external GeoIP DB).
    If the first two octets change between consecutive logins within a short window,
    it's flagged as suspicious.
    """

    def __init__(self, window: int = 3600, max_users: int = 50_000):
        self._last_login: dict[str, tuple[float, str]] = {}
        self._lock = Lock()
        self._window = window
        self._max_users = max_users

    def check_login(self, user_id: str, ip: str) -> dict:
        """Record a login and check for impossible travel.

        Returns {suspicious: bool, reason: str, previous_ip_class: str}
        """
        if not user_id or not ip:
            return {"suspicious": False, "reason": "", "previous_ip_class": ""}

        now = time.time()
        ip_class = self._ip_to_class(ip)

        with self._lock:
            prev = self._last_login.get(user_id)
            self._last_login[user_id] = (now, ip)

            if len(self._last_login) > self._max_users:
                cutoff = now - self._window
                dead = [u for u, (t, _) in self._last_login.items() if t < cutoff]
                for u in dead:
                    del self._last_login[u]

        if not prev:
            return {"suspicious": False, "reason": "first_login", "previous_ip_class": ""}

        prev_time, prev_ip = prev
        elapsed = now - prev_time

        if elapsed > self._window:
            return {"suspicious": False, "reason": "outside_window", "previous_ip_class": ""}

        prev_class = self._ip_to_class(prev_ip)
        if ip_class != prev_class and ip_class != "unknown" and prev_class != "unknown":
            return {
                "suspicious": True,
                "reason": "ip_class_change",
                "previous_ip_class": prev_class,
                "current_ip_class": ip_class,
                "elapsed_seconds": int(elapsed),
            }

        return {"suspicious": False, "reason": "", "previous_ip_class": prev_class}

    @staticmethod
    def _ip_to_class(ip: str) -> str:
        """Extract /16 class from IP for coarse geo comparison."""
        try:
            addr = ipaddress.ip_address(ip)
            if isinstance(addr, ipaddress.IPv4Address):
                parts = ip.split(".")
                return f"{parts[0]}.{parts[1]}"
            else:
                parts = ip.split(":")
                return f"{parts[0]}:{parts[1]}" if len(parts) >= 2 else "unknown"
        except (ValueError, TypeError):
            return "unknown"

    def _reset(self):
        with self._lock:
            self._last_login.clear()


geo_anomaly = GeoAnomalyDetector()


# ══════════════════════════════════════════════════
#  ABUSE ESCALATION ENGINE
# ══════════════════════════════════════════════════

class AbuseEscalationEngine:
    """Auto-escalate responses based on abuse score thresholds.

    Defines escalation tiers with automated actions:
      0-24:  clean    → no action
      25-49: warning  → log + soft-throttle
      50-74: restrict → hard-throttle + flag for review
      75-100: block   → block requests + alert
    """

    TIERS = [
        {"name": "clean",    "min": 0,  "max": 24,  "action": "none"},
        {"name": "warning",  "min": 25, "max": 49,  "action": "throttle"},
        {"name": "restrict", "min": 50, "max": 74,  "action": "restrict"},
        {"name": "block",    "min": 75, "max": 100, "action": "block"},
    ]

    def __init__(self):
        self._escalation_log: list[dict] = []
        self._lock = Lock()
        self._max_log = 500

    def evaluate(self, ip: str, score: int = -1) -> dict:
        """Evaluate an IP and determine escalation action.

        If score is not provided, calculates it from abuse_score.
        Returns {tier: str, action: str, score: int, should_block: bool}
        """
        if score < 0:
            result = abuse_score.calculate(ip)
            score = result["score"]

        tier_info = self.TIERS[0]
        for tier in self.TIERS:
            if tier["min"] <= score <= tier["max"]:
                tier_info = tier
                break

        should_block = tier_info["action"] == "block"

        with self._lock:
            self._escalation_log.append({
                "ip": ip,
                "score": score,
                "tier": tier_info["name"],
                "action": tier_info["action"],
                "ts": time.time(),
            })
            if len(self._escalation_log) > self._max_log:
                self._escalation_log = self._escalation_log[-self._max_log:]

        return {
            "tier": tier_info["name"],
            "action": tier_info["action"],
            "score": score,
            "should_block": should_block,
        }

    def recent_escalations(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return self._escalation_log[-limit:]

    def _reset(self):
        with self._lock:
            self._escalation_log.clear()


abuse_escalation = AbuseEscalationEngine()


# ══════════════════════════════════════════════════
#  SECURITY METRICS AGGREGATOR
# ══════════════════════════════════════════════════

class SecurityMetricsAggregator:
    """Aggregate security metrics across all subsystems for dashboard/monitoring.

    Provides a unified snapshot of security posture.
    """

    def snapshot(self) -> dict:
        """Collect current metrics from all security subsystems.

        Returns a flat dict suitable for JSON export to monitoring dashboards.
        """
        metrics = {
            "ts": datetime.now(timezone.utc).isoformat(),
        }

        # IP reputation stats
        metrics["ip_reputation_tracked"] = len(ip_reputation._scores)

        # Event correlator
        corr_stats = event_correlator.stats()
        metrics["correlator_tracked_ips"] = corr_stats["tracked_ips"]
        metrics["correlator_total_alerts"] = corr_stats["total_alerts"]

        # Credential stuffing
        cs_stats = credential_stuffing.stats()
        metrics["credential_stuffing_tracked_ips"] = cs_stats["tracked_ips"]

        # Honeypot
        hp_stats = honeypot.stats()
        metrics["honeypot_tracked_ips"] = hp_stats["tracked_ips"]
        metrics["honeypot_total_hits"] = hp_stats["total_hits"]

        # Circuit breakers
        metrics["cb_moderation_state"] = cb_moderation_api.stats()["state"]
        metrics["cb_vision_state"] = cb_vision_api.stats()["state"]

        # Geo anomaly
        metrics["geo_anomaly_tracked_users"] = len(geo_anomaly._last_login)

        # Security event log
        metrics["security_events_total"] = len(security_logger._recent_events)

        return metrics

    def health_check(self) -> dict:
        """Quick health status of security systems.

        Returns {healthy: bool, issues: list[str]}
        """
        issues = []

        if cb_moderation_api.state == "open":
            issues.append("circuit_breaker_moderation_open")
        if cb_vision_api.state == "open":
            issues.append("circuit_breaker_vision_open")

        corr_stats = event_correlator.stats()
        if corr_stats["total_alerts"] > 100:
            issues.append("high_alert_count")

        return {"healthy": not issues, "issues": issues}


security_metrics = SecurityMetricsAggregator()


# ══════════════════════════════════════════════════
#  REQUEST FORENSICS COLLECTOR
# ══════════════════════════════════════════════════

class RequestForensicsCollector:
    """Capture detailed request forensics for suspicious requests.

    Stores full request metadata (not body) for post-incident investigation.
    Only triggered when abuse score exceeds threshold.
    """

    def __init__(self, threshold: int = 40, max_records: int = 1000):
        self._records: list[dict] = []
        self._lock = Lock()
        self._threshold = threshold
        self._max_records = max_records

    def maybe_collect(
        self, ip: str, method: str, path: str, headers: dict,
        abuse_score_val: int = 0, user_id: str = "",
    ) -> bool:
        """Collect forensics if abuse score exceeds threshold.

        Returns True if collected.
        """
        if abuse_score_val < self._threshold:
            return False

        record = {
            "ts": time.time(),
            "ip": ip,
            "method": method,
            "path": path,
            "user_id": user_id,
            "abuse_score": abuse_score_val,
            "ua": headers.get("user-agent", "")[:200],
            "content_type": headers.get("content-type", ""),
            "accept": headers.get("accept", ""),
            "referer": headers.get("referer", "")[:200],
            "x_forwarded_for": headers.get("x-forwarded-for", ""),
        }

        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

        return True

    def get_records(self, ip: str = "", limit: int = 100) -> list[dict]:
        """Retrieve forensics records, optionally filtered by IP."""
        with self._lock:
            if ip:
                return [r for r in self._records if r["ip"] == ip][-limit:]
            return self._records[-limit:]

    def stats(self) -> dict:
        with self._lock:
            return {"total_records": len(self._records)}

    def _reset(self):
        with self._lock:
            self._records.clear()


request_forensics = RequestForensicsCollector()


# ══════════════════════════════════════════════════
#  BEHAVIORAL FINGERPRINTING
# ══════════════════════════════════════════════════

def _interval_regularity(intervals: list) -> float:
    """Compute interval regularity (0..1); higher = more bot-like regular timing."""
    regularity = 0.0
    if len(intervals) >= 5:
        avg = sum(intervals) / len(intervals)
        if avg > 0:
            variance = sum((x - avg) ** 2 for x in intervals) / len(intervals)
            std_dev = variance ** 0.5
            regularity = 1.0 - min(1.0, std_dev / avg)
    return regularity


def _bot_reasons(request_count: int, unique_paths: int, ua_changes: int,
                 regularity: float, get_count: int) -> list:
    """Build the list of bot-indicator reasons from behavioral metrics."""
    reasons = []
    if request_count > 50 and regularity > 0.8:
        reasons.append("high_regularity")
    if request_count > 100 and unique_paths > 50:
        reasons.append("excessive_crawling")
    if ua_changes > 3 and request_count > 20:
        reasons.append("ua_rotation")
    # Only GET requests (scraper pattern)
    if get_count == request_count and request_count > 30:
        reasons.append("get_only_pattern")
    return reasons


class BehavioralFingerprint:
    """Build behavioral fingerprints for IPs/users based on request patterns.

    Tracks: request frequency, endpoint diversity, timing patterns, UA consistency.
    Used to distinguish real users from bots/scrapers without UA string analysis.
    """

    def __init__(self, window: int = 600, max_keys: int = 20_000):
        self._profiles: dict[str, dict] = {}
        self._lock = Lock()
        self._window = window
        self._max_keys = max_keys

    def record(self, key: str, path: str, method: str, ua_hash: str = ""):
        """Record a request for behavioral fingerprinting."""
        now = time.time()
        with self._lock:
            if key not in self._profiles:
                self._profiles[key] = {
                    "first_seen": now,
                    "paths": [],
                    "methods": {},
                    "ua_hashes": set(),
                    "intervals": [],
                    "last_ts": now,
                }
            p = self._profiles[key]
            p["paths"].append((now, path))
            p["methods"][method] = p["methods"].get(method, 0) + 1
            if ua_hash and len(p["ua_hashes"]) < 50:
                p["ua_hashes"].add(ua_hash)
            if p["last_ts"] != now:
                p["intervals"].append(now - p["last_ts"])
            p["last_ts"] = now

            # Keep only recent entries
            cutoff = now - self._window
            p["paths"] = [(t, pa) for t, pa in p["paths"] if t > cutoff]
            if len(p["intervals"]) > 200:
                p["intervals"] = p["intervals"][-200:]

            if len(self._profiles) > self._max_keys:
                dead = [k for k, v in self._profiles.items()
                        if v["last_ts"] < cutoff]
                for k in dead:
                    del self._profiles[k]

    def analyze(self, key: str) -> dict:
        """Analyze behavioral fingerprint for an IP/user.

        Returns {
            is_bot_like: bool,
            request_count: int,
            unique_paths: int,
            ua_changes: int,
            interval_regularity: float,
            reasons: list[str]
        }
        """
        with self._lock:
            p = self._profiles.get(key)
            if not p:
                return {
                    "is_bot_like": False, "request_count": 0,
                    "unique_paths": 0, "ua_changes": 0,
                    "interval_regularity": 0.0, "reasons": [],
                }

            paths = p["paths"]
            request_count = len(paths)
            unique_paths = len({pa for _, pa in paths})

            # UA consistency — bots rarely change UA
            ua_changes = len(p["ua_hashes"])

            # Interval regularity — bots have very regular intervals
            regularity = _interval_regularity(p["intervals"])

            reasons = _bot_reasons(
                request_count, unique_paths, ua_changes, regularity,
                p["methods"].get("GET", 0),
            )

            return {
                "is_bot_like": len(reasons) >= 2,
                "request_count": request_count,
                "unique_paths": unique_paths,
                "ua_changes": ua_changes,
                "interval_regularity": round(regularity, 3),
                "reasons": reasons,
            }

    def _reset(self):
        with self._lock:
            self._profiles.clear()


behavioral_fp = BehavioralFingerprint()
