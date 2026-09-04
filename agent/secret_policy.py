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


def is_strong_production_secret(value: object) -> bool:
    """Return whether a value meets the shared production secret policy."""
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    if (
        len(normalized) < 20
        or normalized in PRODUCTION_SECRET_PLACEHOLDERS
        or any(
            marker in normalized
            for marker in (
                "<your-",
                "replace-me",
                "example-secret",
                "dev_password",
                "change_me",
            )
        )
    ):
        return False

    # Use the prefix function to reject any repeated cycle, including units
    # longer than the old 16-character cap.
    prefix = [0] * len(normalized)
    for index in range(1, len(normalized)):
        candidate = prefix[index - 1]
        while candidate and normalized[index] != normalized[candidate]:
            candidate = prefix[candidate - 1]
        if normalized[index] == normalized[candidate]:
            candidate += 1
        prefix[index] = candidate
    period = len(normalized) - prefix[-1]
    if prefix[-1] and len(normalized) % period == 0:
        return False

    # Reject low-entropy canaries even when they are not periodic.
    if len(set(normalized)) < 5:
        return False
    length = len(normalized)
    entropy = -sum(
        (count / length) * log2(count / length)
        for count in Counter(normalized).values()
    )
    return entropy > 2.0
