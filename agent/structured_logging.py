"""Small, dependency-free privacy boundary for operational events.

Structured events are deliberately lossy: sensitive values are represented by
their length, category, and a one-way digest so operators can correlate events
without being able to reconstruct the input.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Mapping

_EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_PHONE = re.compile(r"(?:\+84|0084|0[1-9])[\d\s().-]{7,14}\d")
_TOKEN = re.compile(r"\b(?:sk-[A-Z0-9_-]{8,}|(?:token|secret|password|api[_-]?key)\s*[:=]\s*\S+)", re.I)

_SENSITIVE_KEY_HINTS = (
    "phone", "email", "token", "secret", "password", "authorization",
    "message", "prompt", "query", "input", "output", "content",
)
_KEY_CATEGORY_HINTS = (
    ("message", ("message", "prompt", "query", "input", "output", "content")),
    ("token", ("token", "secret", "password", "authorization", "api_key")),
    ("email", ("email",)),
    ("phone", ("phone",)),
)


def _category(key: str | None, value: str) -> str | None:
    key_name = (key or "").lower().replace("-", "_")
    # Preserve the semantic category of named event fields even when their
    # text contains another sensitive value (for example, a phone in message).
    for category, hints in _KEY_CATEGORY_HINTS:
        if any(hint in key_name for hint in hints):
            return category
    if _EMAIL.search(value):
        return "email"
    if _PHONE.search(value):
        return "phone"
    if _TOKEN.search(value):
        return "token"
    return None


def _digest(value: object, category: str) -> dict[str, object]:
    raw = str(value)
    return {
        "length": len(raw),
        "category": category,
        "digest": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


def _redact_string(value: str, key: str | None) -> object:
    category = _category(key, value)
    return _digest(value, category) if category else value


def _has_sensitive_key(key: str | None) -> bool:
    return any(hint in (key or "").lower() for hint in _SENSITIVE_KEY_HINTS)


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, (bool, int, float))


def _redact(value: object, key: str | None = None) -> object:
    if isinstance(value, Mapping):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item, key) for item in value]
    if isinstance(value, str):
        return _redact_string(value, key)
    if _has_sensitive_key(key):
        return _digest(value, _category(key, str(value)) or "message")
    if _is_scalar(value):
        return value
    return _digest(value, "message")


def redact_event(event: Mapping[str, object]) -> dict[str, object]:
    """Return a JSON-safe event with sensitive values irreversibly summarized."""
    if not isinstance(event, Mapping):
        raise TypeError("event must be a mapping")
    return _redact(event)  # type: ignore[return-value]


def log_user_event(event: Mapping[str, object], *, level: int = logging.INFO, logger: logging.Logger | None = None) -> dict[str, object]:
    """Emit a redacted JSON event and return the exact safe payload."""
    safe = redact_event(event)
    target = logger or logging.getLogger("vinhlong360.user")
    # Keep the privacy-boundary logger observable when it inherits a stricter
    # application threshold, without overriding an explicit per-logger policy.
    target.disabled = False
    target.propagate = True
    # ``NOTSET`` inherits the application logger's threshold, so inspect the
    # effective level rather than only the logger's explicitly configured one.
    if target.level == logging.NOTSET and not target.isEnabledFor(level):
        target.setLevel(level)
    target.log(level, json.dumps(safe, ensure_ascii=False, sort_keys=True))
    return safe


class RedactingLogFilter(logging.Filter):
    """Replace a formatted LogRecord before any handler can observe raw args."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            template = str(record.msg)
            args = record.args
            if isinstance(args, Mapping):
                items = list(args.items())
                record.args = {
                    str(key): _redact(value, str(key)) for key, value in items
                }
                return True
            if not args:
                return True

            # Keep stable operational context while replacing interpolated
            # values. Labels such as ``token=%s`` provide stronger category
            # hints than content heuristics alone.
            safe_args = []
            cursor = 0
            for value in args:
                marker = template.find("%", cursor)
                prefix = template[cursor:marker] if marker >= 0 else ""
                match = re.search(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*$", prefix)
                key = match.group(1) if match else None
                safe_args.append(_redact(value, key))
                cursor = marker + 1 if marker >= 0 else len(template)
            record.args = tuple(safe_args)
        except Exception:
            record.msg = "event=%s"
            record.args = ("[REDACTION_FAILED]",)
        return True


def install_redaction_filter(logger: logging.Logger) -> None:
    """Install the idempotent record-level filter on a logger."""
    if not any(isinstance(item, RedactingLogFilter) for item in logger.filters):
        logger.addFilter(RedactingLogFilter())
