"""Change sets: immutable, bound to one entity revision, and never applied here."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.correction import (  # noqa: E402
    ChangeSetDraft,
    CorrectionRejected,
    ProposedChange,
    build_patches,
    validate_change_set,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _change(**overrides) -> ProposedChange:
    base = dict(
        item_id="i-1",
        entity_id="p-vinh-long",
        field_path="attributes.phone",
        before_value="0270 111 2222",
        after_value="0270 333 4444",
    )
    base.update(overrides)
    return ProposedChange(**base)


def _draft(**overrides) -> ChangeSetDraft:
    base = dict(
        case_id="c-1",
        entity_id="p-vinh-long",
        base_entity_revision=7,
        changes=(_change(),),
        risk_class="R1",
        decision_maker_ref="person:maker",
        reviewer_ref=None,
        evidence_refs=("e-1",),
    )
    base.update(overrides)
    return ChangeSetDraft(**base)


def test_the_patch_and_its_inverse_are_exact_opposites():
    before, after, inverse = build_patches(_draft())

    assert before == {"attributes.phone": "0270 111 2222"}
    assert after == {"attributes.phone": "0270 333 4444"}
    assert inverse == {"attributes.phone": "0270 111 2222"}


def test_a_no_op_change_is_refused():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(changes=(_change(after_value="0270 111 2222"),)),
            current_entity_revision=7,
            now=NOW,
        )

    assert excinfo.value.problem.code == "change_set_is_a_no_op"


def test_a_bundle_spanning_two_entities_is_refused():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(changes=(_change(), _change(item_id="i-2", entity_id="p-other"))),
            current_entity_revision=7,
            now=NOW,
        )

    assert excinfo.value.problem.code == "change_set_spans_entities"


def test_a_field_outside_the_approved_paths_is_refused():
    for path in ("verifiedAt", "attributes.__proto__", "owner_ref"):
        with pytest.raises(CorrectionRejected) as excinfo:
            validate_change_set(
                _draft(changes=(_change(field_path=path),)),
                current_entity_revision=7,
                now=NOW,
            )
        assert excinfo.value.problem.code == "field_path_not_correctable"


def test_a_change_set_is_refused_when_the_entity_moved_underneath_it():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(_draft(base_entity_revision=7), current_entity_revision=9, now=NOW)

    assert excinfo.value.problem.code == "entity_revision_moved"


def test_two_changes_to_the_same_field_are_refused():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(changes=(_change(), _change(item_id="i-2", after_value="0270 999 0000"))),
            current_entity_revision=7,
            now=NOW,
        )

    assert excinfo.value.problem.code == "duplicate_change_field"


def test_a_high_risk_change_set_carries_its_reviewer():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(risk_class="R3", reviewer_ref=None), current_entity_revision=7, now=NOW
        )
    assert excinfo.value.problem.code == "maker_checker_required"

    accepted = validate_change_set(
        _draft(risk_class="R3", reviewer_ref="person:checker"),
        current_entity_revision=7,
        now=NOW,
    )
    assert accepted.reviewer_ref == "person:checker"


def test_a_change_set_needs_the_evidence_it_rests_on():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(_draft(evidence_refs=()), current_entity_revision=7, now=NOW)

    assert excinfo.value.problem.code == "evidence_lineage_required"


def test_building_a_change_set_never_reaches_the_entity_writer():
    import inspect

    from cases import correction

    source = inspect.getsource(correction)
    for forbidden in ("upsert_entity", "update_entity", "db.upsert", "entity_writer"):
        assert forbidden not in source
    # apply_status starts pending; publication is a separate, later decision.
    assert 'apply_status' in source and 'pending' in source


# ── Persistence, against real PostgreSQL ──


import database  # noqa: E402
from cases.domain import ActorContext, Channel  # noqa: E402
from cases.policy import load_case_policy  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402




# One loopback-only rule for every suite that opens the disposable database.
from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402
MASTER_KEY = "0" * 43


@pytest.fixture
def pg_database():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    from cases.correction import configure_case_correction

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, revision) VALUES (%s,'place','Vinh Long',7)"
            " ON CONFLICT (id) DO UPDATE SET revision = 7",
            ("p-cs",),
        )
        conn.commit()
    configure_case_correction(
        database=adapter, crypto=CaseCrypto(MASTER_KEY), policy=load_case_policy()
    )
    yield adapter
    configure_case_correction(database=None, crypto=None, policy=None)


def _decider(ref="person:maker", scopes=("cases:work", "cases:decide")):
    return ActorContext(actor_ref=ref, channel=Channel.WEB, scopes=frozenset(scopes),
                        correlation_id="corr-persist")


def _seed_case_with_item(adapter, *, entity_id="p-cs", field_path="attributes.phone",
                         risk="R1", holder="person:maker"):
    from cases.security import CaseCrypto as _Crypto

    crypto = _Crypto(MASTER_KEY)
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
            VALUES (%s,%s,%s,%s,%s,7,%s,'E0') RETURNING item_id
            """,
            (case_id, entity_id, field_path,
             crypto.encrypt_private_payload({"value": "0270 111 2222"}),
             crypto.encrypt_private_payload({"value": "0270 333 4444"}), risk),
        )["item_id"])
        if holder:
            adapter._execute(
                conn,
                """
                INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,
                                             assignee_ref, lease_expires_at, ready_at, priority)
                VALUES (%s,'decide','case_operator',%s,'claimed',%s,%s,%s,0)
                """,
                (case_id, risk, holder, NOW + timedelta(hours=1), NOW),
            )
        conn.commit()
    return case_id, item_id


@pg_only
def test_building_a_change_set_commits_the_whole_fulfilment_step_at_once(pg_database):
    from cases.correction import build_change_set

    case_id, item_id = _seed_case_with_item(pg_database)

    change_set = build_change_set(
        case_id, (item_id,), _decider(), expected_revision=1,
        evidence_refs=("e-1",), now=NOW,
    )

    assert change_set.apply_status == "pending"
    with pg_database._conn(commit_on_success=False) as conn:
        stored = dict(pg_database._fetchone(
            conn,
            "SELECT base_entity_revision, before_patch::text AS before,"
            " after_patch::text AS after, inverse_patch::text AS inverse, apply_status,"
            " public_projection_verified_at"
            " FROM correction_change_sets WHERE case_id=%s",
            (case_id,),
        ))
        linked = pg_database._fetchone(
            conn,
            "SELECT count(*) AS n FROM correction_change_set_items WHERE item_id=%s",
            (item_id,),
        )["n"]
        phase = pg_database._fetchone(
            conn, "SELECT phase FROM cases WHERE case_id=%s", (case_id,)
        )["phase"]
        work = pg_database._fetchone(
            conn,
            "SELECT count(*) AS n FROM case_work_items WHERE case_id=%s AND kind='publication'",
            (case_id,),
        )["n"]
        audits = pg_database._fetchone(
            conn,
            "SELECT count(*) AS n FROM case_audit_events WHERE case_id=%s"
            " AND reason_code='change_set_built'",
            (case_id,),
        )["n"]
        outbox = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM case_outbox WHERE case_id=%s", (case_id,)
        )["n"]
        entity_revision = pg_database._fetchone(
            conn, "SELECT revision FROM entities WHERE id='p-cs'"
        )["revision"]

    assert stored["apply_status"] == "pending"
    assert stored["public_projection_verified_at"] is None
    assert stored["base_entity_revision"] == 7
    assert "0270 111 2222" in stored["before"] and "0270 333 4444" in stored["after"]
    assert stored["inverse"] == stored["before"]
    assert linked == 1
    assert phase == "fulfillment"
    assert work == 1
    assert audits == 1
    assert outbox == 1
    # The live entry is untouched: publication is a separate, later decision.
    assert entity_revision == 7


@pg_only
def test_a_change_set_is_refused_when_the_entity_moved_since_intake(pg_database):
    from cases.correction import CorrectionRejected as Refused
    from cases.correction import build_change_set

    case_id, item_id = _seed_case_with_item(pg_database)
    with pg_database._conn(commit_on_success=False) as conn:
        pg_database._execute(conn, "UPDATE entities SET revision = 9 WHERE id='p-cs'", ())
        conn.commit()

    with pytest.raises(Refused) as excinfo:
        build_change_set(
            case_id, (item_id,), _decider(), expected_revision=1,
            evidence_refs=("e-1",), now=NOW,
        )

    assert excinfo.value.problem.code == "entity_revision_moved"
    with pg_database._conn(commit_on_success=False) as conn:
        count = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM correction_change_sets WHERE case_id=%s", (case_id,)
        )["n"]
    assert count == 0


def test_the_plan_locked_type_name_reaches_the_same_class():
    from cases.correction import ChangeSetDraft, CorrectionChangeSet

    # Cross-task code written against the plan's name must find the real thing.
    assert CorrectionChangeSet is ChangeSetDraft
