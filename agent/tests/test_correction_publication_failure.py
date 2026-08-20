"""Checking that the public actually got the correction, and what happens when it did not.

Applying wrote the row. Verification is the separate step that goes and looks at
what a reader is served and compares it to what was written, because a cache, a
prerender or a filtered projection can all leave the database correct and the
page wrong. Only this step may close a case as corrected.

A mismatch is never terminal. Nothing is marked verified, the case stays in
fulfilment, the promise moves to recovery, an escalation is recorded and the
person who reported is given a next update. Saying "done" when the page still
shows the old phone number is the failure this file exists to prevent.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.domain import ActorContext, Channel, PromiseHealth, PublicationState  # noqa: E402
from cases.policy import load_case_policy  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=5)
MASTER_KEY = "0" * 43
ENTITY_ID = "p-verify"




# One loopback-only rule for every suite that opens the disposable database.
from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402


@pytest.fixture
def pg_database(monkeypatch):
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    from cases.correction import configure_case_correction
    from cases.publication import configure_case_publication
    from config import settings

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(conn, "DELETE FROM entity_changes WHERE entity_id = %s", (ENTITY_ID,))
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, attributes, revision)"
            " VALUES (%s,'place','Quán Bún Cô Sáu',%s,7)"
            " ON CONFLICT (id) DO UPDATE SET revision = 7, attributes = EXCLUDED.attributes",
            (ENTITY_ID, '{"phone": "0270 111 2222"}'),
        )
        conn.commit()
    policy = load_case_policy()
    configure_case_correction(database=adapter, crypto=CaseCrypto(MASTER_KEY), policy=policy)
    configure_case_publication(database=adapter, crypto=CaseCrypto(MASTER_KEY), policy=policy)
    monkeypatch.setattr(settings, "CORRECTION_PUBLICATION_ENABLED", True, raising=False)
    yield adapter
    configure_case_correction(database=None, crypto=None, policy=None)
    configure_case_publication(database=None, crypto=None, policy=None)


def _actor(ref="person:publisher",
           scopes=("cases:work", "publication.apply", "publication.verify")) -> ActorContext:
    return ActorContext(actor_ref=ref, channel=Channel.WEB, scopes=frozenset(scopes),
                        correlation_id="corr-verify")


def _applied_case(adapter):
    """A case whose change set is already applied and waiting to be checked."""
    from cases.correction import build_change_set
    from cases.publication import ApplyChangeSetCommand, apply_change_set

    crypto = CaseCrypto(MASTER_KEY)
    with adapter._conn(commit_on_success=False) as conn:
        case_id = str(adapter._fetchone(
            conn,
            "INSERT INTO cases (service_kind, category, phase, activity, disposition_family,"
            " reporter_privacy, owner_ref, current_revision, promise_policy_ref)"
            " VALUES ('correction','correction','decision','active','undetermined','anonymous',"
            " 'person:owner',1,'correction-pilot-v1') RETURNING case_id",
            (),
        )["case_id"])
        item_id = str(adapter._fetchone(
            conn,
            "INSERT INTO correction_items (case_id, entity_id, field_path, reported_value_enc,"
            " proposed_value_enc, base_entity_revision, risk_class, evidence_level)"
            " VALUES (%s,%s,'attributes.phone',%s,%s,7,'R1','E3') RETURNING item_id",
            (case_id, ENTITY_ID,
             crypto.encrypt_private_payload({"value": "0270 111 2222"}),
             crypto.encrypt_private_payload({"value": "0270 333 4444"})),
        )["item_id"])
        adapter._execute(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,"
            " assignee_ref, lease_expires_at, ready_at, priority)"
            " VALUES (%s,'decide','case_operator','R1','claimed',%s,%s,%s,0)",
            (case_id, "person:maker", NOW + timedelta(hours=2), NOW),
        )
        # The ruling the change set is a consequence of.
        adapter._execute(
            conn,
            "INSERT INTO case_decisions (case_id, item_id, outcome_code, reason_code,"
            " evidence_refs, decision_maker_ref, policy_revision, decided_at)"
            " VALUES (%s,%s,'corrected','source_confirms_change','[\"e-1\"]'::jsonb,"
            " 'person:maker','correction-pilot-v1',%s)",
            (case_id, item_id, NOW),
        )
        adapter._execute(
            conn,
            "INSERT INTO case_promise_clocks (case_id, kind, started_at, due_at, health,"
            " policy_revision, observed_at) VALUES (%s,'update',%s,%s,'on_track',"
            " 'correction-pilot-v1',%s)",
            (case_id, NOW, NOW + timedelta(days=2), NOW),
        )
        conn.commit()

    class _Decider:
        actor_ref = "person:maker"
        reviewer_ref = None
        scopes = ("cases:work", "cases:decide")
        channel = Channel.WEB
        correlation_id = "corr-verify"

    build_change_set(case_id, (item_id,), _Decider(), expected_revision=1,
                     evidence_refs=("e-1",), now=NOW)
    with adapter._conn(commit_on_success=False) as conn:
        change_set_id = str(adapter._fetchone(
            conn, "SELECT change_set_id FROM correction_change_sets WHERE case_id=%s", (case_id,)
        )["change_set_id"])
        adapter._execute(
            conn,
            "UPDATE case_work_items SET status='claimed', assignee_ref=%s, lease_expires_at=%s"
            " WHERE case_id=%s AND kind='publication'",
            ("person:publisher", NOW + timedelta(hours=2), case_id),
        )
        conn.commit()
    apply_change_set(
        ApplyChangeSetCommand(
            case_id=case_id, change_set_id=change_set_id, actor=_actor(),
            expected_case_revision=2, expected_entity_revision=7,
        ),
        now=NOW,
    )
    return case_id, change_set_id


def _projection(**overrides) -> dict:
    """What a reader is served after a correct publication."""
    base = {
        "id": ENTITY_ID,
        "revision": 8,
        "name": "Quán Bún Cô Sáu",
        "attributes": {"phone": "0270 333 4444"},
        "source": {"name": "Ban biên tập vinhlong360"},
    }
    base.update(overrides)
    return base


def _fetcher(projection):
    def fetch(entity_id: str) -> dict:
        return projection
    return fetch


def _verify(case_id, change_set_id, projection=None, *, actor=None, now=LATER):
    from cases.publication import VerifyProjectionCommand, verify_public_projection

    return verify_public_projection(
        VerifyProjectionCommand(case_id=case_id, change_set_id=change_set_id,
                                actor=actor or _actor()),
        _fetcher(_projection() if projection is None else projection),
        now=now,
    )


def _case(adapter, case_id) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        return dict(adapter._fetchone(
            conn,
            "SELECT phase, domain_outcome, disposition_family FROM cases WHERE case_id=%s",
            (case_id,),
        ))


def _change_set(adapter, change_set_id) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        return dict(adapter._fetchone(
            conn,
            "SELECT apply_status, public_projection_verified_at"
            " FROM correction_change_sets WHERE change_set_id=%s",
            (change_set_id,),
        ))


def _count(adapter, sql, params) -> int:
    with adapter._conn(commit_on_success=False) as conn:
        return adapter._fetchone(conn, sql, params)["n"]


def _promise_health(adapter, case_id) -> str:
    with adapter._conn(commit_on_success=False) as conn:
        return adapter._fetchone(
            conn, "SELECT health FROM case_promise_clocks WHERE case_id=%s", (case_id,)
        )["health"]


# ── The projection matches ──

@pg_only
def test_a_matching_projection_is_what_finally_marks_the_case_corrected(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    result = _verify(case_id, change_set_id)

    assert result.verified is True
    assert result.state is PublicationState.VERIFIED
    assert result.mismatches == ()
    assert _change_set(pg_database, change_set_id)["public_projection_verified_at"] is not None
    case = _case(pg_database, case_id)
    assert case["phase"] == "closed"
    assert case["domain_outcome"] == "corrected"
    assert case["disposition_family"] == "action_taken"


@pg_only
def test_verifying_completes_the_publication_work(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    _verify(case_id, change_set_id)

    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_work_items WHERE case_id=%s AND kind='publication'"
        " AND status='completed'", (case_id,)
    ) == 1


@pg_only
def test_a_projection_check_does_not_mint_a_field_verification(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    _verify(case_id, change_set_id)

    # verifiedAt means a person went and looked at the place. Reading our own web
    # page is not that, and this step must never be able to claim it.
    with pg_database._conn(commit_on_success=False) as conn:
        attributes = pg_database._fetchone(
            conn, "SELECT attributes::text AS attributes FROM entities WHERE id=%s", (ENTITY_ID,)
        )["attributes"]
    assert "verifiedAt" not in attributes


# ── The projection does not match ──

@pg_only
@pytest.mark.parametrize("projection,expected", [
    (_projection(attributes={"phone": "0270 111 2222"}), "attributes.phone"),
    (_projection(revision=7), "revision"),
    (_projection(id="p-somewhere-else"), "id"),
    (_projection(source={}), "source"),
])
def test_every_way_the_public_copy_can_disagree_is_reported(pg_database, projection, expected):
    case_id, change_set_id = _applied_case(pg_database)

    result = _verify(case_id, change_set_id, projection)

    assert result.verified is False
    assert expected in result.mismatches
    assert _change_set(pg_database, change_set_id)["public_projection_verified_at"] is None


@pg_only
def test_a_stale_page_leaves_the_case_open_and_the_promise_in_recovery(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    result = _verify(case_id, change_set_id, _projection(revision=7))

    assert result.state is PublicationState.APPLIED
    case = _case(pg_database, case_id)
    assert case["phase"] == "fulfillment"
    assert case["domain_outcome"] is None, "a failed check may never write a terminal outcome"
    assert _promise_health(pg_database, case_id) == PromiseHealth.RECOVERY.value


@pg_only
def test_a_failed_check_records_an_escalation_and_promises_a_next_update(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    result = _verify(case_id, change_set_id, _projection(revision=7))

    assert result.next_update_at is not None and result.next_update_at > LATER
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s"
        " AND reason_code='projection_verification_failed'", (case_id,)
    ) == 1
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_outbox WHERE case_id=%s AND idempotency_key LIKE %s",
        (case_id, "%verification_failed%")
    ) == 1


@pg_only
def test_a_page_that_cannot_be_fetched_at_all_is_a_failure_not_a_pass(pg_database):
    from cases.publication import VerifyProjectionCommand, verify_public_projection

    case_id, change_set_id = _applied_case(pg_database)

    def broken(entity_id):
        raise RuntimeError("the public endpoint did not answer")

    result = verify_public_projection(
        VerifyProjectionCommand(case_id=case_id, change_set_id=change_set_id, actor=_actor()),
        broken,
        now=LATER,
    )

    # Not reaching the page tells us nothing, and nothing is not success.
    assert result.verified is False
    assert "unreachable" in result.mismatches
    assert _case(pg_database, case_id)["phase"] == "fulfillment"


@pg_only
def test_a_missing_page_is_a_failure(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    result = _verify(case_id, change_set_id, None if False else {})

    assert result.verified is False


# ── Authority and order ──

@pg_only
def test_verification_needs_its_own_scope(pg_database):
    from cases.publication import PublicationRejected

    case_id, change_set_id = _applied_case(pg_database)

    with pytest.raises(PublicationRejected) as excinfo:
        _verify(case_id, change_set_id,
                actor=_actor(scopes=("cases:work", "publication.apply")))

    assert excinfo.value.problem.code == "verification_scope_required"


@pg_only
def test_a_change_set_that_was_never_applied_cannot_be_verified(pg_database):
    from cases.correction import build_change_set
    from cases.publication import PublicationRejected

    crypto = CaseCrypto(MASTER_KEY)
    with pg_database._conn(commit_on_success=False) as conn:
        case_id = str(pg_database._fetchone(
            conn,
            "INSERT INTO cases (service_kind, category, phase, activity, disposition_family,"
            " reporter_privacy, owner_ref, current_revision, promise_policy_ref)"
            " VALUES ('correction','correction','decision','active','undetermined','anonymous',"
            " 'person:owner',1,'correction-pilot-v1') RETURNING case_id",
            (),
        )["case_id"])
        item_id = str(pg_database._fetchone(
            conn,
            "INSERT INTO correction_items (case_id, entity_id, field_path, reported_value_enc,"
            " proposed_value_enc, base_entity_revision, risk_class, evidence_level)"
            " VALUES (%s,%s,'attributes.phone',%s,%s,7,'R1','E3') RETURNING item_id",
            (case_id, ENTITY_ID,
             crypto.encrypt_private_payload({"value": "0270 111 2222"}),
             crypto.encrypt_private_payload({"value": "0270 333 4444"})),
        )["item_id"])
        pg_database._execute(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,"
            " assignee_ref, lease_expires_at, ready_at, priority)"
            " VALUES (%s,'decide','case_operator','R1','claimed',%s,%s,%s,0)",
            (case_id, "person:publisher", NOW + timedelta(hours=2), NOW),
        )
        pg_database._execute(
            conn,
            "INSERT INTO case_decisions (case_id, item_id, outcome_code, reason_code,"
            " evidence_refs, decision_maker_ref, policy_revision, decided_at)"
            " VALUES (%s,%s,'corrected','source_confirms_change','[\"e-1\"]'::jsonb,"
            " 'person:publisher','correction-pilot-v1',%s)",
            (case_id, item_id, NOW),
        )
        conn.commit()

    class _Decider:
        actor_ref = "person:publisher"
        reviewer_ref = None
        scopes = ("cases:work", "cases:decide")
        channel = Channel.WEB
        correlation_id = "corr-verify"

    build_change_set(case_id, (item_id,), _Decider(), expected_revision=1,
                     evidence_refs=("e-1",), now=NOW)
    with pg_database._conn(commit_on_success=False) as conn:
        change_set_id = str(pg_database._fetchone(
            conn, "SELECT change_set_id FROM correction_change_sets WHERE case_id=%s", (case_id,)
        )["change_set_id"])

    with pytest.raises(PublicationRejected) as excinfo:
        _verify(case_id, change_set_id)

    assert excinfo.value.problem.code == "change_set_not_applied"


@pg_only
def test_verification_outcomes_leave_their_own_capacity_traces(pg_database, monkeypatch):
    events = []
    # Both entry points: publication records on its own transaction now, and a
    # capture that watches only the connection-opening one sees nothing.
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append(kind) or True)
    monkeypatch.setattr("cases.metrics.observe_on",
                        lambda transaction, kind, **kw: events.append(kind) or True)

    case_id, change_set_id = _applied_case(pg_database)
    events.clear()  # the apply above already traced itself

    _verify(case_id, change_set_id, _projection(revision=7))
    assert events == ["recovery"], "a failed check is recovery, never completion"

    events.clear()
    _verify(case_id, change_set_id)
    # Two facts on purpose: the page checked out, and the case finished.
    assert events == ["verified", "completed"]
