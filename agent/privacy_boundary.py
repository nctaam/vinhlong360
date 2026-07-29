"""Mandatory source-aware privacy boundary for chat content."""

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from guardrails import (
    PII_CANDIDATE_CHARS,
    PII_MAX_SPAN_BY_KIND,
    PII_REPLACEMENTS,
    PIISpan,
    check_input,
    check_output,
    pii_masker,
)
from metrics import track_privacy_boundary_failure, track_privacy_redaction


PrivacySource = Literal[
    "private_user_data",
    "untrusted_external",
    "verified_public_contact",
    "provider_output",
    "legacy_cache",
    "log",
]

_PRIVACY_SOURCES = frozenset(
    {
        "private_user_data",
        "untrusted_external",
        "verified_public_contact",
        "provider_output",
        "legacy_cache",
        "log",
    }
)


class _PrivacyBoundaryError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class PrivacyBoundaryBlocked(_PrivacyBoundaryError):
    """The supplied content violates a caller-facing privacy policy."""


class PrivacyBoundaryUnavailable(_PrivacyBoundaryError):
    """The mandatory boundary could not safely classify or redact content."""


@dataclass(frozen=True)
class SafeHistoryItem:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class SafeChatInput:
    message: str
    history: tuple[SafeHistoryItem, ...]
    redaction_types: tuple[str, ...]


@dataclass(frozen=True)
class SafeText:
    text: str
    redaction_types: tuple[str, ...] = ()


_REDACTION_FAILED = "[REDACTION_FAILED]"


def _validate_source(source: PrivacySource) -> None:
    if source not in _PRIVACY_SOURCES:
        raise PrivacyBoundaryUnavailable("INVALID_PRIVACY_SOURCE")


def _verified_contacts(values: Sequence[str]) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise PrivacyBoundaryUnavailable("INVALID_VERIFIED_CONTACTS")
    try:
        contacts = tuple(values)
    except (TypeError, ValueError) as exc:
        raise PrivacyBoundaryUnavailable("INVALID_VERIFIED_CONTACTS") from exc
    if any(not isinstance(value, str) or not value for value in contacts):
        raise PrivacyBoundaryUnavailable("INVALID_VERIFIED_CONTACTS")
    return frozenset(contacts)


def _unique_types(types: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(types))


def _redact_spans(
    text: str,
    spans: Sequence[PIISpan],
    *,
    allowed_contacts: frozenset[str],
) -> SafeText:
    parts: list[str] = []
    redaction_types: list[str] = []
    cursor = 0
    for span in spans:
        parts.append(text[cursor:span.start])
        raw_value = text[span.start:span.end]
        if raw_value in allowed_contacts:
            parts.append(raw_value)
        else:
            parts.append(PII_REPLACEMENTS[span.kind])
            redaction_types.append(span.kind)
        cursor = span.end
    parts.append(text[cursor:])
    return SafeText("".join(parts), _unique_types(redaction_types))


def redact_text(
    text: str,
    *,
    source: PrivacySource,
    verified_public_contacts: Sequence[str] = (),
) -> SafeText:
    """Return text that is safe for the declared provenance."""
    _validate_source(source)
    if not isinstance(text, str):
        raise PrivacyBoundaryUnavailable("INVALID_TEXT")

    contacts = _verified_contacts(verified_public_contacts)
    allowed_contacts = contacts if source == "verified_public_contact" else frozenset()
    try:
        spans = pii_masker.detect_spans(text)
        safe = _redact_spans(text, spans, allowed_contacts=allowed_contacts)
        for redaction_type in safe.redaction_types:
            track_privacy_redaction(source, redaction_type)
        return safe
    except PrivacyBoundaryUnavailable:
        raise
    except Exception as exc:
        raise PrivacyBoundaryUnavailable("TEXT_REDACTION_FAILED") from exc


def redact_log_value(value):
    if isinstance(value, str):
        try:
            safe = redact_text(value, source="log")
        except Exception:
            track_privacy_boundary_failure("log")
            return _REDACTION_FAILED
        return safe.text
    if isinstance(value, Mapping):
        try:
            return {key: redact_log_value(item) for key, item in value.items()}
        except Exception:
            track_privacy_boundary_failure("log")
            return _REDACTION_FAILED
    if isinstance(value, list):
        return [redact_log_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_log_value(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    track_privacy_boundary_failure("log")
    return _REDACTION_FAILED


def privacy_boundary_readiness() -> bool:
    try:
        safe = redact_text("privacy-boundary-ready", source="log")
        return safe.text == "privacy-boundary-ready"
    except Exception:
        track_privacy_boundary_failure("readiness")
        return False


def redact_payload(
    value: Any,
    *,
    source: PrivacySource,
    verified_public_contacts: Sequence[str] = (),
):
    """Recursively redact text in JSON-like payloads."""
    _validate_source(source)
    if isinstance(value, str):
        return redact_text(
            value,
            source=source,
            verified_public_contacts=verified_public_contacts,
        ).text
    if isinstance(value, Mapping):
        return {
            redact_payload(
                key,
                source=source,
                verified_public_contacts=verified_public_contacts,
            ) if isinstance(key, str) else key:
            redact_payload(
                item,
                source=source,
                verified_public_contacts=verified_public_contacts,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            redact_payload(
                item,
                source=source,
                verified_public_contacts=verified_public_contacts,
            )
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            redact_payload(
                item,
                source=source,
                verified_public_contacts=verified_public_contacts,
            )
            for item in value
        )
    return value


def _collect_redaction_types(text: str) -> tuple[str, ...]:
    try:
        return _unique_types([span.kind for span in pii_masker.detect_spans(text)])
    except Exception as exc:
        raise PrivacyBoundaryUnavailable("TEXT_CLASSIFICATION_FAILED") from exc


def _validate_history(history: Sequence[Mapping[str, str]]) -> tuple[Mapping[str, str], ...]:
    if isinstance(history, (str, bytes)) or not isinstance(history, Sequence):
        raise PrivacyBoundaryBlocked("INVALID_CHAT_HISTORY")

    validated = []
    for item in history:
        if not isinstance(item, Mapping) or set(item.keys()) != {"role", "content"}:
            raise PrivacyBoundaryBlocked("INVALID_CHAT_HISTORY")
        role = item["role"]
        content = item["content"]
        if role not in ("user", "assistant") or not isinstance(content, str):
            raise PrivacyBoundaryBlocked("INVALID_CHAT_HISTORY")
        validated.append(item)
    return tuple(validated)


def prepare_chat_input(
    message: str,
    history: Sequence[Mapping[str, str]],
    *,
    owner_key: str,
) -> SafeChatInput:
    """Validate and redact the complete provider-bound chat envelope."""
    if not isinstance(message, str) or not isinstance(owner_key, str) or not owner_key:
        raise PrivacyBoundaryBlocked("INVALID_CHAT_INPUT")
    validated_history = _validate_history(history)

    try:
        guard = check_input(message, owner_key)
    except Exception as exc:
        raise PrivacyBoundaryUnavailable("INPUT_GUARD_UNAVAILABLE") from exc

    if not isinstance(guard, Mapping):
        raise PrivacyBoundaryUnavailable("INVALID_INPUT_GUARD_RESULT")
    if guard.get("allowed") is not True:
        raise PrivacyBoundaryBlocked("INPUT_BLOCKED")
    guarded_message = guard.get("message")
    if not isinstance(guarded_message, str):
        raise PrivacyBoundaryUnavailable("INVALID_INPUT_GUARD_RESULT")

    raw_types = list(_collect_redaction_types(message))
    safe_message = redact_text(guarded_message, source="private_user_data")
    raw_types.extend(safe_message.redaction_types)

    safe_history = []
    for item in validated_history:
        safe_content = redact_text(item["content"], source="private_user_data")
        raw_types.extend(safe_content.redaction_types)
        safe_history.append(SafeHistoryItem(item["role"], safe_content.text))

    if (
        safe_history
        and safe_history[-1].role == "user"
        and safe_history[-1].content == safe_message.text
    ):
        safe_history.pop()

    return SafeChatInput(
        message=safe_message.text,
        history=tuple(safe_history),
        redaction_types=_unique_types(raw_types),
    )


def _protect_verified_contacts(
    text: str,
    contacts: frozenset[str],
) -> tuple[str, tuple[tuple[str, str], ...]]:
    if not contacts:
        return text, ()

    spans = pii_masker.detect_spans(text)
    allowed = [span for span in spans if text[span.start:span.end] in contacts]
    if not allowed:
        return text, ()

    protected = text
    restorations = []
    for index, span in reversed(list(enumerate(allowed))):
        placeholder = f"__VL360_VERIFIED_CONTACT_{index}__"
        while placeholder in text:
            placeholder = "_" + placeholder
        raw_value = text[span.start:span.end]
        protected = protected[:span.start] + placeholder + protected[span.end:]
        restorations.append((placeholder, raw_value))
    return protected, tuple(restorations)


def prepare_chat_output(
    reply: str,
    *,
    query: str,
    entities: Mapping[str, Any],
    verified_public_contacts: Sequence[str] = (),
) -> SafeText:
    """Apply output validation and a second, source-aware redaction pass."""
    if not isinstance(reply, str) or not isinstance(query, str) or not isinstance(entities, Mapping):
        raise PrivacyBoundaryUnavailable("INVALID_CHAT_OUTPUT")

    contacts = _verified_contacts(verified_public_contacts)
    try:
        original_spans = pii_masker.detect_spans(reply)
    except Exception as exc:
        raise PrivacyBoundaryUnavailable("TEXT_CLASSIFICATION_FAILED") from exc
    original_types = _unique_types(
        [
            span.kind
            for span in original_spans
            if reply[span.start:span.end] not in contacts
        ]
    )
    try:
        protected_reply, restorations = _protect_verified_contacts(reply, contacts)
        guard = check_output(protected_reply, query, dict(entities))
    except PrivacyBoundaryUnavailable:
        raise
    except Exception as exc:
        raise PrivacyBoundaryUnavailable("OUTPUT_GUARD_UNAVAILABLE") from exc

    if not isinstance(guard, Mapping) or not isinstance(guard.get("cleaned_reply"), str):
        raise PrivacyBoundaryUnavailable("INVALID_OUTPUT_GUARD_RESULT")

    cleaned_reply = guard["cleaned_reply"]
    for placeholder, raw_value in restorations:
        cleaned_reply = cleaned_reply.replace(placeholder, raw_value)

    safe = redact_text(
        cleaned_reply,
        source="verified_public_contact",
        verified_public_contacts=contacts,
    )
    redaction_types = list(original_types)
    redaction_types.extend(safe.redaction_types)
    return SafeText(safe.text, _unique_types(redaction_types))


_OVERLONG_REDACTION = "[SECRET]"
_DEFAULT_STREAM_PATTERN_SPAN = max(PII_MAX_SPAN_BY_KIND.values())
_MIN_STREAM_PATTERN_SPAN = _DEFAULT_STREAM_PATTERN_SPAN


class StreamingPIIRedactor:
    """Release only text that is outside the bounded PII detection suffix."""

    def __init__(
        self,
        max_pattern_span: int = _DEFAULT_STREAM_PATTERN_SPAN,
        *,
        verified_public_contacts: Sequence[str] = (),
    ):
        if not isinstance(max_pattern_span, int) or max_pattern_span < _MIN_STREAM_PATTERN_SPAN:
            raise ValueError("max_pattern_span is too small")
        self.max_pattern_span = max_pattern_span
        self._verified_public_contacts = _verified_contacts(verified_public_contacts)
        self._pending = ""
        self._aborted = False
        self._finished = False
        self._discarding_overlong_candidate = False

    def _consume_discarded_candidate(self, chunk: str) -> str:
        for index, char in enumerate(chunk):
            if char not in PII_CANDIDATE_CHARS:
                self._discarding_overlong_candidate = False
                return chunk[index:]
        return ""

    @staticmethod
    def _trailing_candidate_start(text: str) -> int:
        index = len(text)
        while index > 0 and text[index - 1] in PII_CANDIDATE_CHARS:
            index -= 1
        return index

    def _redact_prefix(self, prefix: str) -> str:
        if not prefix:
            return ""
        if self._verified_public_contacts:
            return redact_text(
                prefix,
                source="verified_public_contact",
                verified_public_contacts=tuple(self._verified_public_contacts),
            ).text
        return redact_text(prefix, source="provider_output").text

    def _release_overlong_candidate(self) -> str | None:
        trailing_start = self._trailing_candidate_start(self._pending)
        if len(self._pending) - trailing_start < self.max_pattern_span:
            return None
        safe_prefix = self._redact_prefix(self._pending[:trailing_start])
        self._pending = ""
        self._discarding_overlong_candidate = True
        return safe_prefix + _OVERLONG_REDACTION

    def _safe_candidate_cut(self) -> int:
        candidate_cut = max(0, len(self._pending) - self.max_pattern_span)
        if candidate_cut == 0:
            return 0

        spans = pii_masker.detect_spans(self._pending)
        while True:
            crossing = [
                span
                for span in spans
                if span.start < candidate_cut < span.end
            ]
            if not crossing:
                return candidate_cut
            left_cut = min(span.start for span in crossing)
            if len(self._pending) - left_cut <= self.max_pattern_span:
                return left_cut
            candidate_cut = max(span.end for span in crossing)

    def feed(self, chunk: str) -> str:
        if self._aborted or self._finished:
            return ""
        if not isinstance(chunk, str):
            self.abort()
            raise PrivacyBoundaryUnavailable("INVALID_STREAM_CHUNK")

        try:
            if self._discarding_overlong_candidate:
                chunk = self._consume_discarded_candidate(chunk)
                if not chunk:
                    return ""

            self._pending += chunk
            overlong_release = self._release_overlong_candidate()
            if overlong_release is not None:
                return overlong_release

            candidate_cut = self._safe_candidate_cut()
            if candidate_cut == 0:
                return ""

            prefix = self._pending[:candidate_cut]
            self._pending = self._pending[candidate_cut:]
            return self._redact_prefix(prefix)
        except PrivacyBoundaryUnavailable:
            self.abort()
            raise
        except Exception as exc:
            self.abort()
            raise PrivacyBoundaryUnavailable("STREAM_REDACTION_FAILED") from exc

    def finish(self) -> str:
        if self._aborted or self._finished:
            return ""
        self._finished = True
        if self._discarding_overlong_candidate:
            self._pending = ""
            return ""

        pending = self._pending
        self._pending = ""
        try:
            return self._redact_prefix(pending)
        except PrivacyBoundaryUnavailable:
            self._aborted = True
            raise
        except Exception as exc:
            self._aborted = True
            raise PrivacyBoundaryUnavailable("STREAM_REDACTION_FAILED") from exc

    def abort(self) -> None:
        self._pending = ""
        self._discarding_overlong_candidate = False
        self._aborted = True
