"""Contract for the durable case rate buckets."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.rate_limit import (  # noqa: E402
    CASE_RATE_BUCKETS,
    check_case_rate_limit,
    rate_subject_digest,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def test_every_credential_command_named_by_the_plan_has_a_bucket():
    assert CASE_RATE_BUCKETS == {
        "correction_create", "receipt_exchange", "contact_otp",
        "contact_otp_requester", "contact_otp_verify", "contact_otp_withdraw",
        "case_review", "receipt_rotation",
    }


def test_subject_digest_hides_the_raw_address_and_is_key_separated():
    digest = rate_subject_digest("203.0.113.7", master_key="k" * 43)

    assert "203.0.113.7" not in digest
    assert len(digest) == 64
    assert digest != rate_subject_digest("203.0.113.7", master_key="j" * 43)
    assert digest == rate_subject_digest("  203.0.113.7  ", master_key="k" * 43)


@pytest.mark.parametrize("subject", ["", "   ", None, 7])
def test_an_unusable_subject_is_refused_rather_than_bucketed_together(subject):
    with pytest.raises(ValueError, match="invalid_rate_subject"):
        rate_subject_digest(subject, master_key="k" * 43)


class _SqliteDatabase:
    _use_pg = False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"limit": 0, "window": 60}, "invalid_rate_window"),
        ({"limit": 5, "window": 0}, "invalid_rate_window"),
        ({"limit": "5", "window": 60}, "invalid_rate_window"),
    ],
)
def test_a_meaningless_window_is_refused(kwargs, message):
    with pytest.raises(ValueError, match=message):
        check_case_rate_limit(
            "correction_create", "a" * 64, now=NOW, database=_SqliteDatabase(), **kwargs
        )


def test_a_naive_clock_is_refused():
    with pytest.raises(ValueError, match="invalid_rate_clock"):
        check_case_rate_limit(
            "correction_create", "a" * 64, limit=5, window=60,
            now=datetime(2026, 8, 18, 9, 0), database=_SqliteDatabase(),
        )


def test_buckets_are_postgresql_only_so_sqlite_cannot_silently_allow_everything():
    with pytest.raises(RuntimeError, match="case_postgresql_required"):
        check_case_rate_limit(
            "correction_create", "a" * 64, limit=5, window=60, now=NOW,
            database=_SqliteDatabase(),
        )
