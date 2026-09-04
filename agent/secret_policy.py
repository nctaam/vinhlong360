"""Shared validation rules for production secrets."""

from collections import Counter
from math import log2


PRODUCTION_SECRET_PLACEHOLDERS = frozenset(
    {
        "",
        "change-me",
        "changeme",
        "secret",
        "password",
        "admin",
        "test",
        "test-key",
        "test-admin-key",
        "vl360_dev_password",
    }
)


def _contains_placeholder_marker(normalized: str) -> bool:
    markers = (
        "<your-",
        "replace-me",
        "example-secret",
        "dev_password",
        "change_me",
    )
    return any(marker in normalized for marker in markers)


def _is_repeated_cycle(normalized: str) -> bool:
    """Reject any repeated cycle using the KMP prefix table."""
    prefix = [0] * len(normalized)
    for index in range(1, len(normalized)):
        candidate = prefix[index - 1]
        while candidate and normalized[index] != normalized[candidate]:
            candidate = prefix[candidate - 1]
        if normalized[index] == normalized[candidate]:
            candidate += 1
        prefix[index] = candidate
    period = len(normalized) - prefix[-1]
    return bool(prefix[-1] and len(normalized) % period == 0)


def _has_sufficient_entropy(normalized: str) -> bool:
    if len(set(normalized)) < 5:
        return False
    length = len(normalized)
    entropy = -sum(
        (count / length) * log2(count / length)
        for count in Counter(normalized).values()
    )
    return entropy > 2.0


def is_strong_production_secret(value: object) -> bool:
    """Return whether a value meets the shared production secret policy."""
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    if (
        len(normalized) < 20
        or normalized in PRODUCTION_SECRET_PLACEHOLDERS
        or _contains_placeholder_marker(normalized)
    ):
        return False

    if _is_repeated_cycle(normalized):
        return False
    return _has_sufficient_entropy(normalized)
