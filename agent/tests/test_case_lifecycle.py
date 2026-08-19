"""Retention on a real database: private data ends, the answerable minimum stays.

The shelves: expired session artifacts go promptly; the optional contact goes
90 days after a terminal close; encrypted evidence and payloads go at 365 days
unless a hold was explicitly audited; the case, decision and audit lineage is
untouched until 730 days, when capacity events lose their case linkage.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.lifecycle import cleanup_case_data  # noqa: E402
from cases.store import PostgresCaseStore  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)


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


@pytest.fixture
def pg(tmp_path):
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    return adapter, PostgresCaseStore(adapter)


def _case(adapter, *, closed_days_ago: int | None) -> str:
    closed = None if closed_days_ago is None else NOW - timedelta(days=closed_days_ago)
    with adapter._conn(commit_on_success=False) as conn:
        case_id = str(adapter._fetchone(
            conn,
            "INSERT INTO cases (service_kind, category, phase, activity,"
            " disposition_family, reporter_privacy, owner_ref, current_revision,"
            " promise_policy_ref, closed_at)"
            " VALUES ('correction','correction',%s,'active',"
            " 'undetermined','anonymous','person:owner',1,'correction-pilot-v1',%s)"
            " RETURNING case_id",
            ("closed" if closed else "triage", closed),
        )["case_id"])
        adapter._execute(
            conn,
            "INSERT INTO case_interactions (case_id, channel, actor_ref, direction,"
            " payload_enc) VALUES (%s,'web','anonymous','inbound','enc:contact')",
            (case_id,),
        )
        adapter._execute(
            conn,
            "INSERT INTO correction_items (case_id, entity_id, field_path,"
            " reported_value_enc, proposed_value_enc, base_entity_revision,"
            " risk_class, evidence_level)"
            " SELECT %s, id, 'attributes.phone', 'enc:a', 'enc:b', 1, 'R1', 'E0'"
            " FROM entities LIMIT 1",
            (case_id,),
        )
        adapter._execute(
            conn,
            "INSERT INTO case_audit_events (case_id, actor_ref, reason_code,"
            " policy_revision, correlation_id, before_snapshot, after_snapshot)"
            " VALUES (%s,'person:test','created','p','c','{}'::jsonb,'{}'::jsonb)",
            (case_id,),
        )
        conn.commit()
    return case_id


def _payloads(adapter, case_id: str) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        contact = adapter._fetchone(
            conn, "SELECT payload_enc FROM case_interactions WHERE case_id=%s", (case_id,)
        )["payload_enc"]
        item = dict(adapter._fetchone(
            conn,
            "SELECT reported_value_enc, proposed_value_enc FROM correction_items"
            " WHERE case_id=%s", (case_id,),
        ))
        audits = adapter._fetchone(
            conn, "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s", (case_id,)
        )["n"]
    return {"contact": contact, "item": item, "audits": int(audits)}


@pg_only
def test_a_recent_close_keeps_its_contact_and_payloads(pg):
    adapter, store = pg
    case_id = _case(adapter, closed_days_ago=30)

    with store.transaction() as transaction:
        cleanup_case_data(transaction, now=NOW)

    state = _payloads(adapter, case_id)
    assert state["contact"] == "enc:contact"
    assert state["item"]["reported_value_enc"] == "enc:a"


@pg_only
def test_the_contact_goes_at_90_days_and_the_evidence_stays(pg):
    adapter, store = pg
    case_id = _case(adapter, closed_days_ago=120)

    with store.transaction() as transaction:
        summary = cleanup_case_data(transaction, now=NOW)

    state = _payloads(adapter, case_id)
    assert state["contact"] is None
    # 120 days is past the contact shelf and short of the evidence shelf.
    assert state["item"]["reported_value_enc"] == "enc:a"
    assert summary.contacts_redacted >= 1


@pg_only
def test_private_payloads_go_at_365_days_but_the_lineage_stays(pg):
    adapter, store = pg
    case_id = _case(adapter, closed_days_ago=400)

    with store.transaction() as transaction:
        cleanup_case_data(transaction, now=NOW)

    state = _payloads(adapter, case_id)
    assert state["item"]["reported_value_enc"] is None
    assert state["item"]["proposed_value_enc"] is None
    # The audit lineage is not this module's to shorten.
    assert state["audits"] == 1


@pg_only
def test_an_audited_hold_keeps_a_case_payload_past_the_shelf(pg):
    adapter, store = pg
    held = _case(adapter, closed_days_ago=400)
    unheld = _case(adapter, closed_days_ago=400)

    with store.transaction() as transaction:
        summary = cleanup_case_data(transaction, now=NOW,
                                    audited_holds=frozenset({held}))

    assert _payloads(adapter, held)["item"]["reported_value_enc"] == "enc:a"
    assert _payloads(adapter, unheld)["item"]["reported_value_enc"] is None
    assert held in summary.held_cases_skipped


@pg_only
def test_an_open_case_is_never_touched_regardless_of_age(pg):
    adapter, store = pg
    case_id = _case(adapter, closed_days_ago=None)

    with store.transaction() as transaction:
        cleanup_case_data(transaction, now=NOW)

    # No terminal close, no clock: retention runs from the answer, not the ask.
    assert _payloads(adapter, case_id)["contact"] == "enc:contact"


@pg_only
def test_old_capacity_events_lose_their_case_link_and_keep_their_numbers(pg):
    adapter, store = pg
    case_id = _case(adapter, closed_days_ago=800)
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO case_capacity_events (case_id, channel, risk_class,"
            " event_kind, observed_at) VALUES (%s,'web','R1','received',%s)",
            (case_id, NOW - timedelta(days=800)),
        )
        conn.commit()

    with store.transaction() as transaction:
        summary = cleanup_case_data(transaction, now=NOW)

    with adapter._conn(commit_on_success=False) as conn:
        row = dict(adapter._fetchone(
            conn,
            "SELECT case_id, event_kind FROM case_capacity_events"
            " WHERE observed_at = %s", (NOW - timedelta(days=800),),
        ))
    assert row["case_id"] is None and row["event_kind"] == "received"
    assert summary.capacity_links_removed >= 1
