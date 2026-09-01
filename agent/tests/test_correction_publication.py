"""Publishing a correction: one transaction, and `applied` is not `verified`.

Applying a change set touches the live entry the public reads. Every participant
— the entity row and its revision, the entity change audit, the change set's own
state, the case transition, the case audit and the notification intent — commits
together or not at all. A half-applied correction is a public claim nobody
decided to make.

`applied` says the write landed. It does not say anyone saw it land: that is
`verified`, and it comes from a separate command in
test_correction_publication_failure.py.
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
MASTER_KEY = "0" * 43
ENTITY_ID = "p-pub"




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
            " VALUES (%s,'place','Quán Cơm Bà Tư',%s,7)"
            " ON CONFLICT (id) DO UPDATE SET revision = 7, attributes = EXCLUDED.attributes,"
            " name = EXCLUDED.name",
            (ENTITY_ID, '{"phone": "0270 111 2222", "verifiedAt": "2026-01-01T00:00:00Z"}'),
        )
        conn.commit()
    policy = load_case_policy()
    configure_case_correction(database=adapter, crypto=CaseCrypto(MASTER_KEY), policy=policy)
    configure_case_publication(database=adapter, crypto=CaseCrypto(MASTER_KEY), policy=policy)
    _enable_publication(monkeypatch)
    yield adapter
    configure_case_correction(database=None, crypto=None, policy=None)
    configure_case_publication(database=None, crypto=None, policy=None)


def _enable_publication(monkeypatch, enabled: bool = True) -> None:
    from config import settings

    monkeypatch.setattr(settings, "CORRECTION_PUBLICATION_ENABLED", enabled, raising=False)


def _actor(ref="person:publisher", scopes=("cases:work", "publication.apply")) -> ActorContext:
    return ActorContext(actor_ref=ref, channel=Channel.WEB, scopes=frozenset(scopes),
                        correlation_id="corr-publish")


def _seed_change_set(adapter, *, risk="R1", reviewer=None, publisher="person:publisher"):
    """A case that has already decided and built its change set, as Task 10 leaves it."""
    from cases.correction import build_change_set

    crypto = CaseCrypto(MASTER_KEY)
    maker = "person:maker"
    with adapter._conn(commit_on_success=False) as conn:
        case_id = str(adapter._fetchone(
            conn,
            """
            INSERT INTO cases (service_kind, category, phase, activity, disposition_family,
                               reporter_privacy, owner_ref, current_revision, promise_policy_ref)
            VALUES ('correction','correction','decision','active','undetermined','anonymous',
                    'person:owner',1,'correction-pilot-v1')
            RETURNING case_id
            """,
            (),
        )["case_id"])
        item_id = str(adapter._fetchone(
            conn,
            """
            INSERT INTO correction_items (case_id, entity_id, field_path, reported_value_enc,
                                          proposed_value_enc, base_entity_revision,
                                          risk_class, evidence_level)
            VALUES (%s,%s,'attributes.phone',%s,%s,7,%s,'E3') RETURNING item_id
            """,
            (case_id, ENTITY_ID,
             crypto.encrypt_private_payload({"value": "0270 111 2222"}),
             crypto.encrypt_private_payload({"value": "0270 333 4444"}), risk),
        )["item_id"])
        adapter._execute(
            conn,
            """
            INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,
                                         assignee_ref, lease_expires_at, ready_at, priority)
            VALUES (%s,'decide','case_operator',%s,'claimed',%s,%s,%s,0)
            """,
            (case_id, risk, maker, NOW + timedelta(hours=1), NOW),
        )
        # The ruling that entitles this item to be published. The helper's
        # docstring always claimed the case "has already decided"; until the
        # build path started checking, nothing here made that true.
        adapter._execute(
            conn,
            """
            INSERT INTO case_decisions (case_id, item_id, outcome_code, reason_code,
                                        evidence_refs, decision_maker_ref,
                                        policy_revision, decided_at)
            VALUES (%s,%s,'corrected','source_confirms_change','["e-1"]'::jsonb,
                    %s,'correction-pilot-v1',%s)
            """,
            (case_id, item_id, maker, NOW),
        )
        conn.commit()

    class _Decider:
        actor_ref = maker
        reviewer_ref = reviewer
        scopes = ("cases:work", "cases:decide")
        channel = Channel.WEB
        correlation_id = "corr-publish"

    build_change_set(case_id, (item_id,), _Decider(), expected_revision=1,
                     evidence_refs=("e-1",), now=NOW)
    with adapter._conn(commit_on_success=False) as conn:
        change_set_id = str(adapter._fetchone(
            conn,
            "SELECT change_set_id FROM correction_change_sets WHERE case_id=%s",
            (case_id,),
        )["change_set_id"])
        # Publication is its own work item; the publisher holds it, not the decider.
        adapter._execute(
            conn,
            "UPDATE case_work_items SET status='claimed', assignee_ref=%s, lease_expires_at=%s"
            " WHERE case_id=%s AND kind='publication'",
            (publisher, NOW + timedelta(hours=1), case_id),
        )
        conn.commit()
    return case_id, item_id, change_set_id


def _command(case_id, change_set_id, **overrides):
    from cases.publication import ApplyChangeSetCommand

    base = dict(
        case_id=case_id, change_set_id=change_set_id, actor=_actor(),
        expected_case_revision=2, expected_entity_revision=7,
    )
    base.update(overrides)
    return ApplyChangeSetCommand(**base)


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
            "SELECT apply_status, public_projection_verified_at"
            " FROM correction_change_sets WHERE change_set_id=%s",
            (change_set_id,),
        ))


def _count(adapter, sql, params) -> int:
    with adapter._conn(commit_on_success=False) as conn:
        return adapter._fetchone(conn, sql, params)["n"]


def _fail_writing(adapter, monkeypatch, marker: str) -> None:
    """Break exactly one participant, wherever it is issued from."""
    original = adapter._execute

    def failing(conn, sql, *args, **kwargs):
        if marker in sql:
            raise RuntimeError("injected failure at " + marker)
        return original(conn, sql, *args, **kwargs)

    monkeypatch.setattr(adapter, "_execute", failing)
    return original


# ── The whole step lands at once ──

@pg_only
def test_applying_a_change_set_commits_every_participant_together(pg_database):
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)

    result = apply_change_set(_command(case_id, change_set_id), now=NOW)

    entity = _entity(pg_database)
    assert "0270 333 4444" in entity["attributes"]
    assert entity["revision"] == 8
    assert result.entity_revision == 8
    assert result.applied_fields == ("attributes.phone",)
    assert _change_set(pg_database, change_set_id)["apply_status"] == "applied"
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM entity_changes WHERE entity_id=%s", (ENTITY_ID,)
    ) == 1
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s"
        " AND reason_code='change_set_applied'", (case_id,)
    ) == 1
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_outbox WHERE case_id=%s"
        " AND idempotency_key LIKE %s", (case_id, "%applied")
    ) == 1


@pg_only
@pytest.mark.parametrize("participant", [
    "entity_changes",
    "case_audit_events",
    "case_outbox",
    "case_transitions",
])
def test_a_failure_at_any_participant_leaves_the_entry_untouched(
    pg_database, monkeypatch, participant
):
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)
    original = _fail_writing(pg_database, monkeypatch, participant)

    with pytest.raises(RuntimeError, match="injected"):
        apply_change_set(_command(case_id, change_set_id), now=NOW)

    monkeypatch.setattr(pg_database, "_execute", original)
    entity = _entity(pg_database)
    assert "0270 111 2222" in entity["attributes"], "the public entry must not have moved"
    assert entity["revision"] == 7
    assert _change_set(pg_database, change_set_id)["apply_status"] == "pending"


@pg_only
def test_a_rolled_back_apply_publishes_nothing_to_the_entity_cache(pg_database, monkeypatch):
    import entity_details as _entity_details
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)
    applied = []
    monkeypatch.setattr(
        _entity_details, "apply_detail_cache_mutations",
        lambda mutations: applied.append(mutations),
    )
    _fail_writing(pg_database, monkeypatch, "case_outbox")

    with pytest.raises(RuntimeError, match="injected"):
        apply_change_set(_command(case_id, change_set_id), now=NOW)

    # A cache told about a change the transaction threw away would serve a
    # correction that does not exist in the database.
    assert applied == []


# ── Applied is not verified ──

@pg_only
def test_a_fresh_apply_is_applied_and_not_yet_verified(pg_database):
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)

    result = apply_change_set(_command(case_id, change_set_id), now=NOW)

    assert result.state is PublicationState.APPLIED
    stored = _change_set(pg_database, change_set_id)
    assert stored["apply_status"] == "applied"
    # Nobody has looked at the public page yet, so nothing may claim they have.
    assert stored["public_projection_verified_at"] is None


@pg_only
def test_the_case_stays_in_fulfillment_until_the_projection_is_checked(pg_database):
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)

    apply_change_set(_command(case_id, change_set_id), now=NOW)

    with pg_database._conn(commit_on_success=False) as conn:
        phase = pg_database._fetchone(
            conn, "SELECT phase FROM cases WHERE case_id=%s", (case_id,)
        )["phase"]
    assert phase == "fulfillment"


# ── What apply must never touch ──

@pg_only
def test_the_verification_timestamp_survives_an_apply_untouched(pg_database):
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)

    apply_change_set(_command(case_id, change_set_id), now=NOW)

    # verifiedAt says a human checked this on the ground. Correcting a phone
    # number is not that, and merging attributes must not quietly carry it away.
    assert "2026-01-01T00:00:00Z" in _entity(pg_database)["attributes"]


# ── Refusals write nothing ──

@pg_only
def test_an_apply_against_a_moved_entity_revision_is_refused(pg_database):
    from cases.publication import PublicationRejected, apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)
    with pg_database._conn(commit_on_success=False) as conn:
        pg_database._execute(
            conn, "UPDATE entities SET revision = 9 WHERE id=%s", (ENTITY_ID,)
        )
        conn.commit()

    with pytest.raises(PublicationRejected) as excinfo:
        apply_change_set(_command(case_id, change_set_id), now=NOW)

    assert excinfo.value.problem.code == "entity_revision_moved"
    assert _change_set(pg_database, change_set_id)["apply_status"] == "pending"


@pg_only
def test_an_apply_without_the_publication_scope_is_refused(pg_database):
    from cases.publication import PublicationRejected, apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)

    with pytest.raises(PublicationRejected) as excinfo:
        apply_change_set(
            _command(case_id, change_set_id, actor=_actor(scopes=("cases:work",))), now=NOW
        )

    assert excinfo.value.problem.code == "publication_scope_required"
    assert _change_set(pg_database, change_set_id)["apply_status"] == "pending"


@pg_only
def test_the_highest_risk_class_cannot_be_published_by_the_person_who_decided_it(pg_database):
    from cases.publication import PublicationRejected, apply_change_set

    # Task 10 already refuses to build an R3 set whose reviewer is its maker, so
    # the gap left for apply is the publisher: a second pair of eyes on the
    # decision means nothing if the decider is the one who pushes it live.
    case_id, item_id, change_set_id = _seed_change_set(
        pg_database, risk="R3", reviewer="person:checker", publisher="person:maker"
    )

    with pytest.raises(PublicationRejected) as excinfo:
        apply_change_set(
            _command(case_id, change_set_id, actor=_actor(ref="person:maker")), now=NOW
        )

    assert excinfo.value.problem.code == "independent_review_required"
    assert _change_set(pg_database, change_set_id)["apply_status"] == "pending"


@pg_only
def _finish_truth_review(adapter, case_id, *, by="person:checker"):
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class,"
            " status, assignee_ref, ready_at, priority)"
            " VALUES (%s,'truth_review','truth_reviewer','R3','completed',%s,%s,0)",
            (case_id, by, NOW),
        )
        conn.commit()


@pg_only
def test_a_named_reviewer_is_not_enough_until_the_truth_review_is_finished(pg_database):
    from cases.publication import PublicationRejected, apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(
        pg_database, risk="R3", reviewer="person:checker"
    )

    # A name on the change set is intent; only a completed truth_review work
    # item says the review actually happened.
    with pytest.raises(PublicationRejected) as excinfo:
        apply_change_set(_command(case_id, change_set_id), now=NOW)

    assert excinfo.value.problem.code == "truth_review_required"
    assert _change_set(pg_database, change_set_id)["apply_status"] == "pending"


@pg_only
def test_a_truth_review_finished_by_the_maker_does_not_count(pg_database):
    from cases.publication import PublicationRejected, apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(
        pg_database, risk="R3", reviewer="person:checker"
    )
    _finish_truth_review(pg_database, case_id, by="person:maker")

    with pytest.raises(PublicationRejected) as excinfo:
        apply_change_set(_command(case_id, change_set_id), now=NOW)

    assert excinfo.value.problem.code == "truth_review_required"


@pg_only
def test_the_highest_risk_class_applies_once_a_second_person_has_reviewed(pg_database):
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(
        pg_database, risk="R3", reviewer="person:checker"
    )
    _finish_truth_review(pg_database, case_id)

    result = apply_change_set(_command(case_id, change_set_id), now=NOW)

    assert result.state is PublicationState.APPLIED


@pg_only
def test_nothing_applies_while_the_publication_switch_is_off(pg_database, monkeypatch):
    from cases.publication import PublicationRejected, apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)
    _enable_publication(monkeypatch, False)

    with pytest.raises(PublicationRejected) as excinfo:
        apply_change_set(_command(case_id, change_set_id), now=NOW)

    assert excinfo.value.problem.code == "publication_disabled"
    assert _entity(pg_database)["revision"] == 7


@pg_only
def test_the_switch_stops_publishing_without_stopping_intake_or_receipts(pg_database,
                                                                        monkeypatch):
    from cases.publication import PublicationRejected, apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)
    _enable_publication(monkeypatch, False)

    with pytest.raises(PublicationRejected):
        apply_change_set(_command(case_id, change_set_id), now=NOW)

    # The case, its item and its audit trail are untouched by the kill switch:
    # it stops the site changing, not the promise to the person who reported.
    assert _count(
        pg_database, "SELECT count(*) AS n FROM correction_items WHERE case_id=%s", (case_id,)
    ) == 1
    assert _count(
        pg_database, "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s", (case_id,)
    ) >= 1


@pg_only
def test_retrying_an_apply_replays_the_committed_receipt(pg_database):
    from cases.publication import apply_change_set

    case_id, item_id, change_set_id = _seed_change_set(pg_database)
    first = apply_change_set(_command(case_id, change_set_id), now=NOW)
    second = apply_change_set(_command(case_id, change_set_id), now=NOW + timedelta(minutes=1))

    assert second == first
    assert _entity(pg_database)["revision"] == 8
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_transitions WHERE case_id=%s"
        " AND reason_code='change_set_applied'", (case_id,)
    ) == 1
    assert _count(
        pg_database,
        "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s"
        " AND reason_code='change_set_applied'", (case_id,)
    ) == 1


@pg_only
def test_an_applied_state_without_its_receipt_fails_closed(pg_database):
    from cases.publication import PublicationRejected, apply_change_set

    case_id, _item_id, change_set_id = _seed_change_set(pg_database)
    apply_change_set(_command(case_id, change_set_id), now=NOW)
    with pg_database._conn(commit_on_success=False) as conn:
        pg_database._execute(
            conn,
            "DELETE FROM case_outbox WHERE idempotency_key=%s",
            (f"notify:{change_set_id}:applied",),
        )
        conn.commit()

    with pytest.raises(PublicationRejected) as excinfo:
        apply_change_set(_command(case_id, change_set_id), now=NOW + timedelta(minutes=1))
    assert excinfo.value.problem.code == "publication_receipt_missing"


@pg_only
def test_the_reporter_is_told_the_change_is_applied_not_that_it_is_done(pg_database):
    from cases.domain import PublicationState
    from cases.publication import apply_change_set
    from cases.store import PostgresCaseStore

    case_id, item_id, change_set_id = _seed_change_set(pg_database)

    apply_change_set(_command(case_id, change_set_id), now=NOW)

    with PostgresCaseStore(pg_database).transaction() as transaction:
        items = transaction.load_correction_items(case_id)
    # The public status page reads this. Before Task 12 it said not_required
    # forever, which would have told the reporter nothing was owed to them.
    assert [item.publication_state for item in items] == [PublicationState.APPLIED]


@pg_only
def test_an_apply_leaves_an_applied_capacity_trace(pg_database, monkeypatch):
    from cases.publication import apply_change_set

    events = []
    # Both entry points: publication records on its own transaction now, and a
    # capture that watches only the connection-opening one sees nothing.
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append(kind) or True)
    monkeypatch.setattr("cases.metrics.observe_on",
                        lambda transaction, kind, **kw: events.append(kind) or True)
    case_id, item_id, change_set_id = _seed_change_set(pg_database)

    apply_change_set(_command(case_id, change_set_id), now=NOW)

    # Applied only: nothing may claim verified or completed at this boundary.
    assert events == ["applied"]
