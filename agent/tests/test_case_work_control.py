"""Queue order, lease authority, takeover, recusal and escalation."""
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
from cases.domain import ActorContext, Channel, RiskClass  # noqa: E402
from cases.work_control import (  # noqa: E402
    EscalationSummary,
    QueuePage,
    WorkControlRejected,
    WorkItem,
    claim_work_item,
    complete_work_item,
    configure_case_work_control,
    heartbeat_lease,
    list_queue,
    recuse_actor,
    release_work_item,
    scan_escalations,
    takeover_work_item,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
LEASE = timedelta(seconds=1800)


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


def _actor(ref="person:operator", scopes=("cases:work",)) -> ActorContext:
    return ActorContext(
        actor_ref=ref, channel=Channel.WEB, scopes=frozenset(scopes),
        correlation_id="corr-work",
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


def _case(adapter, *, phase="triage") -> str:
    with adapter._conn(commit_on_success=False) as conn:
        row = adapter._fetchone(
            conn,
            """
            INSERT INTO cases (service_kind, category, phase, activity, disposition_family,
                               reporter_privacy, owner_ref, current_revision, promise_policy_ref)
            VALUES ('correction','correction',%s,'active','undetermined','anonymous',
                    'person:owner',1,'correction-pilot-v1')
            RETURNING case_id
            """,
            (phase,),
        )
        case_id = str(row["case_id"])
        conn.commit()
    return case_id


def _work(adapter, case_id, *, kind="triage", risk="R1", priority=0, ready_at=NOW,
          status="ready") -> str:
    with adapter._conn(commit_on_success=False) as conn:
        row = adapter._fetchone(
            conn,
            """
            INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,
                                         ready_at, priority)
            VALUES (%s, %s, 'case_operator', %s, %s, %s, %s)
            RETURNING work_item_id
            """,
            (case_id, kind, risk, status, ready_at, priority),
        )
        work_id = str(row["work_item_id"])
        conn.commit()
    return work_id


def _clock(adapter, case_id, *, kind="triage", due_at=NOW + timedelta(days=1)) -> None:
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            """
            INSERT INTO case_promise_clocks (case_id, kind, started_at, due_at, health,
                                             policy_revision, observed_at)
            VALUES (%s, %s, %s, %s, 'on_track', 'correction-pilot-v1', %s)
            """,
            (case_id, kind, NOW - timedelta(days=1), due_at, NOW),
        )
        conn.commit()


# ── Queue order ──

@pg_only
def test_the_queue_puts_emergency_then_breached_then_risk_then_age_first(pg_database):
    old_case = _case(pg_database)
    old = _work(pg_database, old_case, kind="old", ready_at=NOW - timedelta(days=5))
    _clock(pg_database, old_case)

    risky_case = _case(pg_database)
    risky = _work(pg_database, risky_case, kind="risky", risk="R3")
    _clock(pg_database, risky_case)

    breached_case = _case(pg_database)
    breached = _work(pg_database, breached_case, kind="breached")
    _clock(pg_database, breached_case, due_at=NOW - timedelta(hours=1))

    emergency_case = _case(pg_database)
    emergency = _work(pg_database, emergency_case, kind="urgent", priority=100)
    _clock(pg_database, emergency_case)

    page = list_queue(_actor(), {}, now=NOW)

    assert type(page) is QueuePage
    order = [item.work_item_id for item in page.items]
    assert order == [emergency, breached, risky, old]


@pg_only
def test_a_claimed_item_with_a_live_lease_leaves_the_queue(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    _clock(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    visible = [item.work_item_id for item in list_queue(_actor(), {}, now=NOW).items]

    assert work_id not in visible


@pg_only
def test_an_expired_lease_returns_the_item_to_the_queue(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    _clock(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    later = NOW + LEASE + timedelta(seconds=1)
    visible = [item.work_item_id for item in list_queue(_actor(), {}, now=later).items]

    assert work_id in visible


# ── Lease authority ──

@pg_only
def test_a_claim_is_refused_when_the_revision_moved(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)

    with pytest.raises(WorkControlRejected) as excinfo:
        claim_work_item(work_id, _actor(), expected_revision=99, now=NOW)

    assert excinfo.value.problem.code == "work_item_revision_conflict"


@pg_only
def test_a_second_claim_on_a_live_lease_is_refused(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    first = claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    with pytest.raises(WorkControlRejected) as excinfo:
        claim_work_item(work_id, _actor("person:other"), expected_revision=first.revision, now=NOW)

    assert excinfo.value.problem.code == "work_item_already_claimed"


@pg_only
def test_an_expired_lease_can_be_reclaimed_by_somebody_else(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    first = claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    later = NOW + LEASE + timedelta(seconds=1)
    second = claim_work_item(
        work_id, _actor("person:other"), expected_revision=first.revision, now=later
    )

    assert type(second) is WorkItem
    assert second.assignee_ref == "person:other"
    assert second.lease_expires_at > later


@pg_only
def test_a_heartbeat_cannot_revive_an_expired_lease(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    with pytest.raises(WorkControlRejected) as excinfo:
        heartbeat_lease(work_id, _actor(), now=NOW + LEASE + timedelta(seconds=1))

    assert excinfo.value.problem.code == "work_item_lease_expired"


@pg_only
def test_a_heartbeat_from_another_actor_is_refused(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    with pytest.raises(WorkControlRejected):
        heartbeat_lease(work_id, _actor("person:other"), now=NOW + timedelta(minutes=1))


@pg_only
def test_a_heartbeat_extends_a_live_lease_for_its_owner(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    claimed = claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    beaten = heartbeat_lease(work_id, _actor(), now=NOW + timedelta(minutes=5))

    assert beaten.lease_expires_at > claimed.lease_expires_at


# ── Clearance ──

@pg_only
def test_an_actor_without_the_work_scope_cannot_claim(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)

    with pytest.raises(WorkControlRejected) as excinfo:
        claim_work_item(work_id, _actor(scopes=()), expected_revision=1, now=NOW)

    assert excinfo.value.problem.code == "work_scope_required"


@pg_only
@pytest.mark.parametrize("risk", ["R2", "R3"])
def test_high_risk_work_needs_an_explicit_clearance(pg_database, risk):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id, risk=risk)

    with pytest.raises(WorkControlRejected) as excinfo:
        claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    assert excinfo.value.problem.code == "risk_clearance_required"
    cleared = claim_work_item(
        work_id, _actor(scopes=("cases:work", "cases:high_risk")),
        expected_revision=1, now=NOW,
    )
    assert cleared.risk_class is RiskClass(risk)


# ── Takeover and recusal ──

@pg_only
def test_takeover_needs_the_supervisor_scope_and_a_reason(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    with pytest.raises(WorkControlRejected) as excinfo:
        takeover_work_item(work_id, _actor("person:boss"), reason="stuck", now=NOW)
    assert excinfo.value.problem.code == "supervisor_scope_required"

    supervisor = _actor("person:boss", scopes=("cases:work", "case.supervisor"))
    with pytest.raises(WorkControlRejected) as excinfo:
        takeover_work_item(work_id, supervisor, reason="  ", now=NOW)
    assert excinfo.value.problem.code == "takeover_reason_required"

    taken = takeover_work_item(work_id, supervisor, reason="operator unavailable", now=NOW)
    assert taken.assignee_ref == "person:boss"


@pg_only
def test_a_supervisor_still_cannot_bypass_the_risk_guard(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id, risk="R3")
    supervisor = _actor("person:boss", scopes=("cases:work", "case.supervisor"))

    with pytest.raises(WorkControlRejected) as excinfo:
        takeover_work_item(work_id, supervisor, reason="mine now", now=NOW)

    assert excinfo.value.problem.code == "risk_clearance_required"


@pg_only
def test_recusal_frees_the_item_and_bars_the_recused_actor(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    replacement = recuse_actor(work_id, _actor(), reason="knows the reporter", now=NOW)

    assert replacement.work_item_id != work_id
    assert replacement.assignee_ref is None
    with pytest.raises(WorkControlRejected) as excinfo:
        claim_work_item(
            replacement.work_item_id, _actor(), expected_revision=replacement.revision, now=NOW
        )
    assert excinfo.value.problem.code == "actor_recused"


# ── Completion ──

@pg_only
def test_completing_work_requires_a_result_reference(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    claimed = claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    with pytest.raises(WorkControlRejected) as excinfo:
        complete_work_item(work_id, _actor(), result_ref="", now=NOW)
    assert excinfo.value.problem.code == "result_reference_required"

    done = complete_work_item(work_id, _actor(), result_ref="decision:abc", now=NOW)
    assert done.status == "completed"
    assert done.revision > claimed.revision


@pg_only
def test_only_the_lease_owner_can_complete(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    with pytest.raises(WorkControlRejected):
        complete_work_item(work_id, _actor("person:other"), result_ref="decision:abc", now=NOW)


@pg_only
def test_releasing_returns_the_item_without_completing_it(pg_database):
    case_id = _case(pg_database)
    work_id = _work(pg_database, case_id)
    _clock(pg_database, case_id)
    claim_work_item(work_id, _actor(), expected_revision=1, now=NOW)

    released = release_work_item(work_id, _actor(), now=NOW)

    assert released.status == "ready"
    assert released.assignee_ref is None
    assert work_id in [item.work_item_id for item in list_queue(_actor(), {}, now=NOW).items]


# ── Escalation ──

@pg_only
def test_a_breached_clock_raises_exactly_one_escalation(pg_database):
    case_id = _case(pg_database)
    _work(pg_database, case_id)
    _clock(pg_database, case_id, due_at=NOW - timedelta(hours=2))

    first = scan_escalations(now=NOW)
    second = scan_escalations(now=NOW)

    assert type(first) is EscalationSummary
    assert first.created == 1
    assert second.created == 0, "escalation must be idempotent"
    with pg_database._conn(commit_on_success=False) as conn:
        kinds = [
            row["kind"] for row in pg_database._fetchall(
                conn, "SELECT kind FROM case_work_items WHERE case_id=%s", (case_id,)
            )
        ]
    assert kinds.count("escalation") == 1


@pg_only
def test_escalation_never_edits_the_case_it_escalates(pg_database):
    case_id = _case(pg_database)
    _work(pg_database, case_id)
    _clock(pg_database, case_id, due_at=NOW - timedelta(hours=2))
    with pg_database._conn(commit_on_success=False) as conn:
        before = dict(pg_database._fetchone(
            conn, "SELECT phase, activity, current_revision FROM cases WHERE case_id=%s",
            (case_id,),
        ))

    scan_escalations(now=NOW)

    with pg_database._conn(commit_on_success=False) as conn:
        after = dict(pg_database._fetchone(
            conn, "SELECT phase, activity, current_revision FROM cases WHERE case_id=%s",
            (case_id,),
        ))
    assert after == before


@pg_only
def test_a_lease_expiry_scan_leaves_a_capacity_trace(pg_database, monkeypatch):
    events = []
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append((kind, kw.get("case_id"))) or True)
    case_id = _case(pg_database)
    _work(pg_database, case_id)
    _clock(pg_database, case_id, due_at=NOW - timedelta(hours=2))

    scan_escalations(now=NOW)

    assert ("lease_expired", case_id) in events
