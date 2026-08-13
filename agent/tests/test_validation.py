import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_validation_rejects_naive_and_future_clock_observations():
    from cases.domain import PromiseClock, PromiseHealth
    from cases.validation import PolicyRejected, validate_clock

    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    naive = PromiseClock("update", now.replace(tzinfo=None), now, health=PromiseHealth.ON_TRACK)
    future = PromiseClock("update", now, now, observed_at=datetime(2026, 8, 13, tzinfo=timezone.utc))
    for clock in (naive, future):
        with pytest.raises(PolicyRejected, match="invalid_case_time"):
            validate_clock(clock, now)


@pytest.mark.parametrize("value", [
    "", " ", " leading", "trailing ", "internal space", "identity:separator",
    "tab\tvalue", "line\nvalue", "carriage\rvalue",
])
def test_identifier_validation_rejects_whitespace_and_identity_separator(value):
    from cases.validation import PolicyRejected, validate_identifier

    with pytest.raises(PolicyRejected, match="^invalid_case_contract$"):
        validate_identifier(value)


@pytest.mark.parametrize("value", ["opaque-id", "opaque_id", "opaque.id", "opaque/id", "opaque@id"])
def test_identifier_validation_preserves_safe_opaque_special_characters(value):
    from cases.validation import validate_identifier

    validate_identifier(value)
