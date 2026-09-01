"""Undoing a published correction, without guessing.

Every change set carries the inverse of its own patch, computed when the change
was decided. Rollback replays that inverse rather than recomputing anything, and
only while the entry is still at the revision the apply produced. If something
else edited the entry in between, undoing would silently discard that edit too,
so it fails closed and escalates instead.

A rolled back correction reopens the case. The promise to the person who
reported it is not kept by a change that no longer exists.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.domain import ActorContext, Channel, PublicationState  # noqa: E402
from cases.policy import load_case_policy  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=10)
MASTER_KEY = "0" * 43
ENTITY_ID = "p-rollback"
OLD_PHONE = "0270 111 2222"
NEW_PHONE = "0270 333 4444"




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
            " VALUES (%s,'place','Nhà Vườn Ông Bảy',%s,7)"
            " ON CONFLICT (id) DO UPDATE SET revision = 7, attributes = EXCLUDED.attributes",
            (ENTITY_ID, '{"phone": "%s", "address": "ấp 3, xã Long Hồ"}' % OLD_PHONE),
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
                        correlation_id="corr-rollback")


def _applied_case(adapter):
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
             crypto.encrypt_private_payload({"value": OLD_PHONE}),
             crypto.encrypt_private_payload({"value": NEW_PHONE})),
        )["item_id"])
        adapter._execute(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,"
            " assignee_ref, lease_expires_at, ready_at, priority)"
            " VALUES (%s,'decide','case_operator','R1','claimed',%s,%s,%s,0)",
            (case_id, "person:maker", NOW + timedelta(hours=3), NOW),
        )
        # The ruling the change set is a consequence of; without one the build
        # path now refuses, which is the point of that gate.
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
        correlation_id = "corr-rollback"

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
            ("person:publisher", NOW + timedelta(hours=3), case_id),
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


def _rollback(case_id, change_set_id, *, actor=None, now=LATER):
    from cases.publication import RollbackChangeSetCommand, rollback_change_set

    return rollback_change_set(
        RollbackChangeSetCommand(
            case_id=case_id, change_set_id=change_set_id, actor=actor or _actor(),
            reason_code="source_retracted",
        ),
        now=now,
    )


def _entity(adapter) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        return dict(adapter._fetchone(
            conn,
            "SELECT revision, attributes::text AS attributes FROM entities WHERE id=%s",
            (ENTITY_ID,),
        ))


def _change_set(adapter, change_set_id) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        return dict(adapter._fetchone(
            conn,
            "SELECT apply_status FROM correction_change_sets WHERE change_set_id=%s",
            (change_set_id,),
        ))


def _case(adapter, case_id) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        return dict(adapter._fetchone(
            conn,
            "SELECT phase, domain_outcome, closed_at FROM cases WHERE case_id=%s", (case_id,)
        ))


def _count(adapter, sql, params) -> int:
    with adapter._conn(commit_on_success=False) as conn:
        return adapter._fetchone(conn, sql, params)["n"]


# ── Undoing exactly what was done ──

@pg_only
def test_a_rollback_puts_back_the_value_the_change_set_recorded(pg_database):
    case_id, change_set_id = _applied_case(pg_database)
    assert NEW_PHONE in _entity(pg_database)["attributes"]

    result = _rollback(case_id, change_set_id)

    entity = _entity(pg_database)
    assert OLD_PHONE in entity["attributes"]
    assert result.state is PublicationState.ROLLED_BACK
    assert _change_set(pg_database, change_set_id)["apply_status"] == "rolled_back"


@pg_only
def test_a_rollback_leaves_untouched_fields_alone(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    _rollback(case_id, change_set_id)

    # The inverse patch names one field. Everything else on the entry, including
    # values this case never looked at, must survive the undo.
    assert "ấp 3, xã Long Hồ" in _entity(pg_database)["attributes"]


@pg_only
def test_undoing_moves_the_revision_forward_rather_than_backward(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    result = _rollback(case_id, change_set_id)

    # Rewinding the number would make a later correction, written against
    # revision 8, look current when it is not.
    assert result.entity_revision == 9
    assert _entity(pg_database)["revision"] == 9


@pg_only
def test_a_rollback_reopens_the_case_it_had_closed(pg_database):
    from cases.publication import VerifyProjectionCommand, verify_public_projection

    case_id, change_set_id = _applied_case(pg_database)
    verify_public_projection(
        VerifyProjectionCommand(case_id=case_id, change_set_id=change_set_id, actor=_actor()),
        lambda entity_id: {
            "id": ENTITY_ID, "revision": 8,
            "attributes": {"phone": NEW_PHONE}, "source": {"name": "Ban biên tập vinhlong360"},
        },
        now=NOW + timedelta(minutes=5),
    )
    assert _case(pg_database, case_id)["phase"] == "closed"
    # Verification completed the publication work, so undoing means picking that
    # work back up: nobody edits a live entry without holding the work for it.
    with pg_database._conn(commit_on_success=False) as conn:
        pg_database._execute(
            conn,
            "UPDATE case_work_items SET status='claimed', assignee_ref=%s, lease_expires_at=%s"
            " WHERE case_id=%s AND kind='publication'",
            ("person:publisher", LATER + timedelta(hours=1), case_id),
        )
        conn.commit()

    _rollback(case_id, change_set_id)

    case = _case(pg_database, case_id)
    assert case["phase"] == "fulfillment"
    assert case["domain_outcome"] is None, "a withdrawn change cannot leave a corrected outcome"
    assert case["closed_at"] is None


@pg_only
def test_a_rollback_is_recorded_where_the_case_can_be_read(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    _rollback(case_id, change_set_id)

    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s"
        " AND reason_code='change_set_rolled_back'", (case_id,)
    ) == 1
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM entity_changes WHERE entity_id=%s", (ENTITY_ID,)
    ) == 2


@pg_only
def test_retrying_a_rollback_replays_the_committed_receipt(pg_database):
    case_id, change_set_id = _applied_case(pg_database)

    first = _rollback(case_id, change_set_id)
    second = _rollback(case_id, change_set_id, now=LATER + timedelta(minutes=1))

    assert second == first
    assert _entity(pg_database)["revision"] == 9
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_transitions WHERE case_id=%s"
        " AND reason_code='change_set_rolled_back'", (case_id,)
    ) == 1
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s"
        " AND reason_code='change_set_rolled_back'", (case_id,)
    ) == 1


# ── When the entry moved underneath ──

@pg_only
def test_a_rollback_refuses_once_somebody_else_has_edited_the_entry(pg_database):
    from cases.publication import PublicationRejected

    case_id, change_set_id = _applied_case(pg_database)
    with pg_database._conn(commit_on_success=False) as conn:
        pg_database._execute(
            conn,
            "UPDATE entities SET attributes = %s, revision = revision + 1 WHERE id = %s",
            ('{"phone": "0270 999 0000"}', ENTITY_ID),
        )
        conn.commit()

    with pytest.raises(PublicationRejected) as excinfo:
        _rollback(case_id, change_set_id)

    # Replaying the inverse here would throw away the newer edit as well.
    assert excinfo.value.problem.code == "entity_drifted_after_apply"
    assert "0270 999 0000" in _entity(pg_database)["attributes"]
    assert _change_set(pg_database, change_set_id)["apply_status"] == "applied"


@pg_only
def test_a_refused_rollback_still_raises_the_alarm(pg_database):
    from cases.publication import PublicationRejected

    case_id, change_set_id = _applied_case(pg_database)
    with pg_database._conn(commit_on_success=False) as conn:
        pg_database._execute(
            conn, "UPDATE entities SET revision = revision + 1 WHERE id = %s", (ENTITY_ID,)
        )
        conn.commit()

    with pytest.raises(PublicationRejected):
        _rollback(case_id, change_set_id)

    # Failing closed silently would leave a correction nobody can undo and
    # nobody knows about.
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s"
        " AND reason_code='rollback_refused_entity_drift'", (case_id,)
    ) == 1


# ── Authority and order ──

@pg_only
def test_a_change_set_that_was_never_applied_cannot_be_rolled_back(pg_database):
    from cases.publication import PublicationRejected

    case_id, change_set_id = _applied_case(pg_database)
    _rollback(case_id, change_set_id)

    with pytest.raises(PublicationRejected) as excinfo:
        _rollback(case_id, change_set_id, now=LATER + timedelta(minutes=1))

    assert excinfo.value.problem.code == "change_set_not_applied"


@pg_only
def test_rolling_back_needs_the_publication_scope(pg_database):
    from cases.publication import PublicationRejected

    case_id, change_set_id = _applied_case(pg_database)

    with pytest.raises(PublicationRejected) as excinfo:
        _rollback(case_id, change_set_id, actor=_actor(scopes=("cases:work",)))

    assert excinfo.value.problem.code == "publication_scope_required"


@pg_only
def test_nothing_rolls_back_while_the_publication_switch_is_off(pg_database, monkeypatch):
    from config import settings

    from cases.publication import PublicationRejected

    case_id, change_set_id = _applied_case(pg_database)
    monkeypatch.setattr(settings, "CORRECTION_PUBLICATION_ENABLED", False, raising=False)

    with pytest.raises(PublicationRejected) as excinfo:
        _rollback(case_id, change_set_id)

    assert excinfo.value.problem.code == "publication_disabled"
    assert NEW_PHONE in _entity(pg_database)["attributes"]
