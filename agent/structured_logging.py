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
from urllib.parse import unquote_plus

_EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_PHONE = re.compile(r"(?:\+84|0084|0[1-9])[\d\s().-]{7,14}\d")
_TOKEN = re.compile(
    r"\b(?:Bearer\s+[A-Z0-9_-]+(?:\.[A-Z0-9_-]+){2}|"
    r"eyJ[A-Z0-9_-]{8,}(?:\.[A-Z0-9_-]+){2}|"
    r"sk-[A-Z0-9_-]{8,}|(?:token|secret|password|api[_-]?key)\s*[:=]\s*\S+|"
    r"(?:token|secret|password)[_-][A-Z0-9][A-Z0-9._-]{3,})\b",
    re.I,
)
_PROMPT_SIGNAL = re.compile(
    r"\b(?:ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|prompts?|rules?|context)|"
    r"(?:reveal|show|repeat|print|display)\s+(?:the\s+)?(?:system\s+)?prompt|"
    r"system\s*:\s*override|(?:forget|disregard)\s+(?:all\s+)?(?:your\s+|the\s+|previous\s+|prior\s+)?(?:instructions?|rules?|guidelines?)|"
    r"(?:jailbreak|do\s+anything\s+now|bypass\s+filters?))\b|"
    r"(?<![A-Za-z])DAN(?![A-Za-z])|(?:base64|eval|exec)\s*\(",
    re.I,
)

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


def _contains_prompt_signal(value: str) -> bool:
    """Recognize direct and compact injection text at the final log boundary."""
    if _PROMPT_SIGNAL.search(value):
        return True
    compact = re.sub(r"[^a-z0-9]", "", unquote_plus(value).lower())
    return bool(
        re.search(
            r"(?:ignore(?:all)?(?:previous|prior|above)(?:instructions?|prompts?|rules?)|"
            r"forget(?:all)?(?:your|the|previous|prior)?(?:instructions?|rules?|guidelines?)|"
            r"jailbreak|donothingnow|bypassfilters|base64(?:payload)?|eval(?:payload)?|exec(?:payload)?)|"
            r"(?<![a-z])dan(?![a-z])",
            compact,
        )
    )


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


def _redact_log_argument(value: object, key: str | None) -> object:
    """Treat unlabelled interpolated strings as untrusted log content."""
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact_log_argument(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_log_argument(item, key) for item in value]
    if isinstance(value, str) and not _category(key, value):
        return _digest(value, "text")
    return _redact(value, key)


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


def _sanitize_record_exception(record: logging.LogRecord) -> None:
    """Remove raw exception and stack details before a handler formats a record."""
    if record.exc_info:
        exc_type, exc_value, _traceback = record.exc_info
        exception_type = getattr(exc_type, "__qualname__", "Exception")
        exception_text = str(exc_value)
        safe_exception = _digest(exception_text, "exception")
        record.exc_info = None
        record.exc_text = (
            f"exception_type={exception_type} "
            f"length={safe_exception['length']} "
            f"digest={safe_exception['digest']}"
        )
    elif record.exc_text:
        record.exc_text = str(_redact_log_argument(record.exc_text, "exception"))
    record.stack_info = None


class RedactingLogFilter(logging.Filter):
    """Replace a formatted LogRecord before any handler can observe raw args."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # ``exc_info`` is a traceback object and therefore bypasses normal
            # argument redaction.  Drop it before handlers format the record;
            # retain only a stable exception type plus a one-way digest.
            _sanitize_record_exception(record)

            template = str(record.msg)
            args = record.args
            if isinstance(args, Mapping):
                items = list(args.items())
                record.args = {
                    str(key): _redact_log_argument(value, str(key)) for key, value in items
                }
                return True
            if not args:
                # Literal messages can still contain interpolated user data
                # (for example ``logger.error(f"phone={phone}")``).
                safe_literal = _redact_string(template, None)
                if safe_literal != template:
                    record.msg = "event=%s"
                    record.args = (safe_literal,)
                elif _contains_prompt_signal(template):
                    record.msg = "event=%s"
                    record.args = (_digest(template, "message"),)
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
                safe_args.append(_redact_log_argument(value, key))
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
