"""Capacity evidence: a denominator that survives restarts, and nobody in it.

Eligibility must be earned by 28 complete consecutive UTC days computed from
the database — 27 is not 28, a gap is not coverage, and a deploy must not hand
anyone a fresh clean month. And no metric row may carry a phone number, a
bearer, or an evidence value: the measuring system must not become a second
copy of what it measures.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.metrics import (  # noqa: E402
    WINDOW_DAYS,
    CapacityEventRejected,
    EligibilityEvidence,
    capacity_window,
    public_sla_eligible,
    record_capacity_event,
)
from cases.store import PostgresCaseStore  # noqa: E402

UTC = timezone.utc


class _Recorder:
    def __init__(self, daily=None) -> None:
        self.rows: list[dict] = []
        self._daily = daily or []

    def record_capacity_event(self, **row) -> None:
        self.rows.append(row)

    def capacity_daily_counts(self, start_day, end_day):
        return [row for row in self._daily if start_day <= row["day"] <= end_day]


def _daily(end_day: date, days: int, *, skip: set | None = None) -> list[dict]:
    skip = skip or set()
    return [
        {"day": end_day - timedelta(days=offset), "arrivals": 2, "completions": 1,
         "by_risk": {"R1": 3}, "by_channel": {"web": 3}}
        for offset in range(days)
        if (end_day - timedelta(days=offset)) not in skip
    ]


NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)
YESTERDAY = NOW.date() - timedelta(days=1)


# ── Recording ──

def test_an_event_is_appended_with_its_grouping_and_nothing_personal():
    recorder = _Recorder()

    record_capacity_event(recorder, kind="received", channel="web",
                          risk_class="R1", case_id="c-1", now=NOW)

    row = recorder.rows[0]
    assert row["kind"] == "received" and row["risk_class"] == "R1"
    assert row["observed_at"] == NOW


def test_an_unknown_event_kind_is_refused_not_invented():
    with pytest.raises(CapacityEventRejected):
        record_capacity_event(_Recorder(), kind="vibes", channel="web",
                              risk_class="R1", now=NOW)


@pytest.mark.parametrize("key", ["contact", "phone_digest", "capability",
                                 "bearer_token", "reported_value", "reporter_name"])
def test_metadata_that_smells_of_private_data_is_refused(key):
    # The measuring system must not become a second copy of what it measures.
    with pytest.raises(CapacityEventRejected):
        record_capacity_event(_Recorder(), kind="received", channel="web",
                              risk_class="R1", metadata={key: "x"}, now=NOW)


def test_nested_metadata_is_refused_wholesale():
    with pytest.raises(CapacityEventRejected):
        record_capacity_event(_Recorder(), kind="received", channel="web",
                              risk_class="R1", metadata={"detail": {"a": 1}}, now=NOW)


def test_a_negative_duration_is_a_bug_not_a_measurement():
    with pytest.raises(CapacityEventRejected):
        record_capacity_event(_Recorder(), kind="completed", channel="web",
                              risk_class="R1", duration_seconds=-1, now=NOW)


# ── The window ──

def test_the_window_is_the_last_28_complete_days_and_excludes_today():
    window = capacity_window(_Recorder(_daily(YESTERDAY, WINDOW_DAYS)), NOW)

    assert window.end_day == YESTERDAY
    assert window.start_day == YESTERDAY - timedelta(days=27)
    assert window.covered_days == 28 and window.missing_days == ()
    assert window.arrivals == 56 and window.completions == 28
    assert window.by_risk == {"R1": 84}


def test_the_window_names_every_missing_day():
    gap = YESTERDAY - timedelta(days=3)
    window = capacity_window(
        _Recorder(_daily(YESTERDAY, WINDOW_DAYS, skip={gap})), NOW
    )

    assert window.covered_days == 27
    assert window.missing_days == (gap,)


def test_the_denominator_is_computed_from_storage_not_from_the_process():
    daily = _daily(YESTERDAY, WINDOW_DAYS)

    # Two independent "processes" over the same store see the same window: a
    # restart resets nothing because nothing lives in memory to reset.
    first = capacity_window(_Recorder(daily), NOW)
    second = capacity_window(_Recorder(daily), NOW)

    assert first == second


# ── Eligibility ──

def test_a_full_window_with_named_coverage_yields_evidence_only():
    window = capacity_window(_Recorder(_daily(YESTERDAY, WINDOW_DAYS)), NOW)

    outcome = public_sla_eligible(window, coverage_named="Ban biên tập vinhlong360",
                                  now=NOW)

    assert isinstance(outcome, EligibilityEvidence)
    assert outcome.coverage_named == "Ban biên tập vinhlong360"
    # An evidence object, not a switch: nothing public changed by computing it.


def test_twenty_seven_days_is_not_twenty_eight():
    window = capacity_window(
        _Recorder(_daily(YESTERDAY, WINDOW_DAYS, skip={YESTERDAY - timedelta(days=5)})),
        NOW,
    )

    assert public_sla_eligible(window, coverage_named="Ban biên tập") is False


def test_zero_arrivals_or_completions_is_no_record_to_promise_on():
    quiet = [{**row, "arrivals": 0} for row in _daily(YESTERDAY, WINDOW_DAYS)]

    window = capacity_window(_Recorder(quiet), NOW)

    assert public_sla_eligible(window, coverage_named="Ban biên tập") is False


def test_unnamed_coverage_is_refused():
    window = capacity_window(_Recorder(_daily(YESTERDAY, WINDOW_DAYS)), NOW)

    assert public_sla_eligible(window, coverage_named="   ") is False


# ── Against the real database ──

def _pg_url():
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = _pg_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)


@pg_only
def test_events_round_trip_through_postgres_grouped_by_day(tmp_path):
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(conn, "DELETE FROM case_capacity_events", ())
        conn.commit()
    store = PostgresCaseStore(adapter)

    with store.transaction() as transaction:
        for offset, kind in ((2, "received"), (2, "completed"), (1, "received")):
            record_capacity_event(
                transaction, kind=kind, channel="web", risk_class="R1",
                now=NOW - timedelta(days=offset),
            )
    with store.transaction() as transaction:
        window = capacity_window(transaction, NOW)

    assert window.arrivals == 2 and window.completions == 1
    assert window.covered_days == 2
    assert window.by_channel == {"web": 3}


# ── The observer at the boundaries ──

def test_observe_without_a_database_is_a_quiet_no_op():
    from cases.metrics import configure_case_metrics, observe

    configure_case_metrics(database=None)

    assert observe("received", channel="web") is False


def test_observe_swallows_a_broken_pipe_instead_of_breaking_the_action(monkeypatch):
    from cases import metrics as metrics_module

    class _Broken:
        def transaction(self):
            raise RuntimeError("db down")

    monkeypatch.setattr(metrics_module, "configure_case_metrics", metrics_module.configure_case_metrics)
    metrics_module.configure_case_metrics(database=object())
    monkeypatch.setattr("cases.store.PostgresCaseStore", lambda db: _Broken())

    try:
        # Measurement failing must never raise into the business action.
        assert metrics_module.observe("received", channel="web") is False
    finally:
        metrics_module.configure_case_metrics(database=None)
