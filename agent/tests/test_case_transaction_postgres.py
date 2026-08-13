"""Real PostgreSQL transaction checks for the correction-case store."""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.audit import CaseAuditDraft  # noqa: E402
from cases.domain import (  # noqa: E402
    ActorContext,
    CaseActivity,
    CasePhase,
    CaseSnapshot,
    Channel,
    DispositionFamily,
    EvidenceLevel,
    PromiseClock,
    RiskClass,
    ServiceKind,
)
from cases.queue_policy import WorkItemDraft  # noqa: E402
from cases.store import (  # noqa: E402
    CaseInteractionDraft,
    CorrectionItemDraft,
    OutboxDraft,
    PartyAuthorityDraft,
    PostgresCaseStore,
    RevisionConflict,
)
from cases.transitions import TransitionDraft  # noqa: E402


UTC = timezone.utc
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def _validated_url() -> str | None:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
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


@pytest.fixture(scope="module")
def pg_db():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    return adapter


def _snapshot(case_id: str, revision: int = 1) -> CaseSnapshot:
    return CaseSnapshot(
        case_id=case_id,
        service_kind=ServiceKind.CORRECTION,
        category="place-name",
        phase=CasePhase.INTAKE,
        activity=CaseActivity.ACTIVE,
        disposition_family=DispositionFamily.UNDETERMINED,
        domain_outcome=None,
        severity="normal",
        reporter_privacy="anonymous",
        owner_ref="person:owner",
        current_revision=revision,
        promise_policy_ref="correction-pilot-v1",
        created_at=NOW,
        updated_at=NOW + timedelta(minutes=revision - 1),
        closed_at=None,
    )


def _actor() -> ActorContext:
    return ActorContext(
        actor_ref="person:operator",
        channel=Channel.WEB,
        scopes=frozenset(("case:read", "case:write")),
        correlation_id="correlation-1",
    )


def _insert_bundle(store: PostgresCaseStore, case_id: str, *, fail_after: str | None = None):
    current = _snapshot(case_id)
    clock = PromiseClock(
        kind="triage",
        started_at=NOW,
        due_at=NOW + timedelta(hours=2),
        observed_at=NOW,
        policy_revision="correction-pilot-v1",
    )
    with store.transaction() as transaction:
        transaction.insert_case(current)
        transaction.insert_interaction(
            CaseInteractionDraft(case_id, Channel.WEB, "person:reporter", "inbound", None, "low", "ciphertext:v1", NOW)
        )
        if fail_after == "interaction":
            raise RuntimeError("after interaction")
        transaction.insert_party_authority(
            PartyAuthorityDraft(case_id, "person:reporter", "self", "case:read", "low", NOW)
        )
        transaction.insert_correction_items(
            case_id,
            (CorrectionItemDraft(None, "name", "enc:old", "enc:new", 1, RiskClass.R0, EvidenceLevel.E0),),
        )
        transaction.insert_promise_clocks(case_id, (clock,))
        transaction.insert_work_items(
            (WorkItemDraft(case_id, "decision", "decision_maker", RiskClass.R0, NOW, NOW, current.promise_health),)
        )
        transition = TransitionDraft(
            case_id,
            CasePhase.INTAKE,
            CasePhase.INTAKE,
            0,
            1,
            "person:operator",
            "case_created",
            "correction-pilot-v1",
            "correlation-1",
            NOW,
            None,
        )
        transaction.append_transition(transition)
        transaction.append_audit(
            CaseAuditDraft.from_snapshots(
                actor=_actor(),
                reason_code="case_created",
                policy_revision="correction-pilot-v1",
                before=None,
                after=current,
                occurred_at=NOW,
            )
        )
        if fail_after == "audit":
            raise RuntimeError("after audit")
        transaction.enqueue_outbox(
            OutboxDraft(case_id, f"{case_id}:created:v1", "case.lifecycle", {"event": "case_created", "revision": 1}, NOW)
        )
        if fail_after == "outbox":
            raise RuntimeError("after outbox")


@pg_only
def test_create_bundle_commits_all_rows_and_maps_typed_snapshot(pg_db):
    import uuid

    case_id = str(uuid.uuid4())
    store = PostgresCaseStore(pg_db)
    _insert_bundle(store, case_id)

    with store.transaction() as transaction:
        loaded = transaction.load_case(case_id)
    assert loaded == replace(
        _snapshot(case_id),
        promise_health=loaded.promise_health,
        promise_clocks=(
            PromiseClock(
                kind="triage",
                started_at=NOW,
                due_at=NOW + timedelta(hours=2),
                observed_at=NOW,
                health=loaded.promise_health,
                policy_revision="correction-pilot-v1",
            ),
        ),
    )
    assert type(loaded.phase) is CasePhase

    with pg_db._conn(commit_on_success=False) as conn:
        counts = {
            table: pg_db._row_to_dict(pg_db._fetchone(conn, f"SELECT COUNT(*) AS count FROM {table} WHERE case_id=%s", (case_id,)))["count"]
            for table in (
                "cases",
                "case_interactions",
                "case_party_authorities",
                "correction_items",
                "case_promise_clocks",
                "case_work_items",
                "case_transitions",
                "case_audit_events",
                "case_outbox",
            )
        }
    assert set(counts.values()) == {1}


@pg_only
@pytest.mark.parametrize("failure_point", ("interaction", "audit", "outbox"))
def test_failure_at_each_create_boundary_rolls_back_every_row(pg_db, failure_point):
    import uuid

    case_id = str(uuid.uuid4())
    with pytest.raises(RuntimeError, match=f"after {failure_point}"):
        _insert_bundle(PostgresCaseStore(pg_db), case_id, fail_after=failure_point)

    with pg_db._conn(commit_on_success=False) as conn:
        assert pg_db._fetchone(conn, "SELECT 1 FROM cases WHERE case_id=%s", (case_id,)) is None


@pg_only
def test_two_cas_writers_have_one_winner_and_conflict_carries_revision_two(pg_db):
    import uuid

    case_id = str(uuid.uuid4())
    store = PostgresCaseStore(pg_db)
    with store.transaction() as transaction:
        transaction.insert_case(_snapshot(case_id))

    replacement = replace(_snapshot(case_id), current_revision=2, updated_at=NOW + timedelta(minutes=1))

    def writer():
        try:
            with store.transaction() as transaction:
                current = transaction.update_case(1, replacement)
                return ("updated", current.current_revision)
        except RevisionConflict as exc:
            return ("conflict", exc.current.current_revision)

    with ThreadPoolExecutor(max_workers=2) as pool:
        revisions = list(pool.map(lambda _index: writer(), range(2)))

    assert sorted(revisions) == [("conflict", 2), ("updated", 2)]
    with store.transaction() as transaction:
        assert transaction.load_case(case_id).current_revision == 2


@pg_only
def test_for_update_blocks_second_transaction_until_first_releases_lock(pg_db):
    import uuid

    case_id = str(uuid.uuid4())
    store = PostgresCaseStore(pg_db)
    with store.transaction() as transaction:
        transaction.insert_case(_snapshot(case_id))

    acquired = Event()
    marker = f"case-lock-{case_id}"

    def wait_until_contender_is_blocked(future) -> None:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if future.done():
                future.result()
                pytest.fail("contender acquired the lock before observation")
            with pg_db._conn(commit_on_success=False) as observer:
                row = pg_db._fetchone(
                    observer,
                    """
                    SELECT wait_event_type, wait_event
                    FROM pg_stat_activity
                    WHERE application_name = %s
                      AND query ILIKE '%%FROM cases%%FOR UPDATE%%'
                    """,
                    (marker,),
                )
            if row is not None and pg_db._row_to_dict(row)["wait_event_type"] == "Lock":
                return
            time.sleep(0.01)
        pytest.fail("contender never reached a PostgreSQL row-lock wait")

    def contender():
        with store.transaction() as transaction:
            pg_db._execute(
                transaction._conn,
                "SET LOCAL application_name = %s",
                (marker,),
            )
            transaction.load_case(case_id, for_update=True)
            acquired.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with store.transaction() as transaction:
            transaction.load_case(case_id, for_update=True)
            future = pool.submit(contender)
            wait_until_contender_is_blocked(future)
            assert not acquired.is_set()
        assert acquired.wait(2)
        future.result(timeout=2)


@pg_only
def test_invalid_audit_rolls_back_case_written_earlier_in_the_transaction(pg_db):
    import uuid

    case_id = str(uuid.uuid4())
    draft = CaseAuditDraft.from_snapshots(
        actor=_actor(),
        reason_code="case_created",
        policy_revision="correction-pilot-v1",
        before=None,
        after=_snapshot(case_id),
        occurred_at=NOW,
    )
    object.__setattr__(draft, "after_snapshot", {"phase": {"contact": "private"}})

    with pytest.raises(ValueError, match="unsafe_case_audit_snapshot"):
        with PostgresCaseStore(pg_db).transaction() as transaction:
            transaction.insert_case(_snapshot(case_id))
            transaction.append_audit(draft)

    with pg_db._conn(commit_on_success=False) as conn:
        assert pg_db._fetchone(
            conn, "SELECT 1 FROM cases WHERE case_id=%s", (case_id,)
        ) is None


@pg_only
def test_append_ledgers_are_immutable_and_stored_descriptors_are_secret_free(pg_db):
    import json
    import uuid

    case_id = str(uuid.uuid4())
    store = PostgresCaseStore(pg_db)
    _insert_bundle(store, case_id)

    with pg_db._conn(commit_on_success=False) as conn:
        audit = pg_db._row_to_dict(pg_db._fetchone(conn, "SELECT * FROM case_audit_events WHERE case_id=%s", (case_id,)))
        outbox = pg_db._row_to_dict(pg_db._fetchone(conn, "SELECT * FROM case_outbox WHERE case_id=%s", (case_id,)))
        serialized = json.dumps({"audit": audit, "outbox": outbox}, default=str).lower()
        assert not any(secret in serialized for secret in ("ciphertext:v1", "phone", "email", "capability", "receipt"))
        for table in ("case_transitions", "case_audit_events"):
            pg_db._execute(conn, "SAVEPOINT immutable", ())
            with pytest.raises(Exception, match="immutable_case_ledger"):
                pg_db._execute(conn, f"DELETE FROM {table} WHERE case_id=%s", (case_id,))
            pg_db._execute(conn, "ROLLBACK TO SAVEPOINT immutable", ())
        conn.rollback()
