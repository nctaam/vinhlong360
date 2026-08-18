"""Two operators, one lease: the race must have exactly one winner."""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.domain import ActorContext, Channel  # noqa: E402
from cases.work_control import (  # noqa: E402
    WorkControlRejected,
    claim_work_item,
    configure_case_work_control,
    heartbeat_lease,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _validated_url() -> str | None:
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


TEST_DATABASE_URL = _validated_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)


def _actor(ref: str) -> ActorContext:
    return ActorContext(
        actor_ref=ref, channel=Channel.WEB, scopes=frozenset({"cases:work"}),
        correlation_id=f"corr-{ref}",
    )


@pytest.fixture
def pg_database():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(conn, "DELETE FROM case_work_items", ())
        conn.commit()
    from cases.policy import load_case_policy

    configure_case_work_control(database=adapter, policy=load_case_policy())
    yield adapter
    configure_case_work_control(database=None, policy=None)


def _seeded_work(adapter) -> str:
    with adapter._conn(commit_on_success=False) as conn:
        case_row = adapter._fetchone(
            conn,
            """
            INSERT INTO cases (service_kind, category, phase, activity, disposition_family,
                               reporter_privacy, owner_ref, current_revision, promise_policy_ref)
            VALUES ('correction','correction','triage','active','undetermined','anonymous',
                    'person:owner',1,'correction-pilot-v1')
            RETURNING case_id
            """,
            (),
        )
        work_row = adapter._fetchone(
            conn,
            """
            INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,
                                         ready_at, priority)
            VALUES (%s, 'triage', 'case_operator', 'R1', 'ready', %s, 0)
            RETURNING work_item_id
            """,
            (str(case_row["case_id"]), NOW),
        )
        work_id = str(work_row["work_item_id"])
        conn.commit()
    return work_id


@pg_only
def test_two_operators_racing_one_claim_produce_exactly_one_winner(pg_database):
    work_id = _seeded_work(pg_database)
    barrier = Barrier(2)

    def attempt(actor_ref: str):
        barrier.wait(timeout=10)
        try:
            return claim_work_item(work_id, _actor(actor_ref), expected_revision=1, now=NOW)
        except WorkControlRejected as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result(timeout=30) for future in (
            pool.submit(attempt, "person:one"), pool.submit(attempt, "person:two")
        )]

    winners = [item for item in outcomes if not isinstance(item, WorkControlRejected)]
    losers = [item for item in outcomes if isinstance(item, WorkControlRejected)]
    assert len(winners) == 1, outcomes
    assert len(losers) == 1
    assert losers[0].problem.code in {
        "work_item_already_claimed", "work_item_revision_conflict",
    }

    with pg_database._conn(commit_on_success=False) as conn:
        row = dict(pg_database._fetchone(
            conn,
            "SELECT assignee_ref, status, revision FROM case_work_items WHERE work_item_id=%s",
            (work_id,),
        ))
    assert row["status"] == "claimed"
    assert row["assignee_ref"] == winners[0].assignee_ref
    # Exactly one successful compare-and-set moved the revision.
    assert row["revision"] == 2


@pg_only
def test_a_reclaim_race_after_expiry_also_has_one_winner(pg_database):
    work_id = _seeded_work(pg_database)
    first = claim_work_item(work_id, _actor("person:one"), expected_revision=1, now=NOW)
    expired = first.lease_expires_at + timedelta(seconds=1)
    barrier = Barrier(2)

    def attempt(actor_ref: str):
        barrier.wait(timeout=10)
        try:
            return claim_work_item(
                work_id, _actor(actor_ref), expected_revision=first.revision, now=expired
            )
        except WorkControlRejected as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result(timeout=30) for future in (
            pool.submit(attempt, "person:two"), pool.submit(attempt, "person:three")
        )]

    winners = [item for item in outcomes if not isinstance(item, WorkControlRejected)]
    assert len(winners) == 1, outcomes


@pg_only
def test_the_loser_of_a_race_cannot_heartbeat_the_winners_lease(pg_database):
    work_id = _seeded_work(pg_database)
    claim_work_item(work_id, _actor("person:one"), expected_revision=1, now=NOW)

    with pytest.raises(WorkControlRejected):
        heartbeat_lease(work_id, _actor("person:two"), now=NOW + timedelta(minutes=1))
