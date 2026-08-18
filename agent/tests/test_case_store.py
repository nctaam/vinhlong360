from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import cases.audit as case_audit
import cases.store as case_store
from cases import store as store_pairing  # staged pairing guard for the store adapter
from cases.audit import CaseAuditDraft, safe_case_projection
from cases.domain import (
    ActorContext,
    CaseActivity,
    CasePhase,
    CaseSnapshot,
    Channel,
    DispositionFamily,
    PromiseClock,
    PromiseHealth,
    ServiceKind,
)
from cases.store import (
    CaseInteractionDraft,
    CaseNotFound,
    OutboxDraft,
    PostgresCaseStore,
    RevisionConflict,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
CASE_ID = "11111111-1111-1111-1111-111111111111"


def test_store_adapter_module_is_importable_for_security_lifecycle_pairing():
    assert store_pairing.PostgresCaseStore is PostgresCaseStore


def test_store_security_methods_remain_on_the_transaction_adapter():
    assert {"issue_receipt", "rotate_receipt", "revoke_access"} <= set(dir(PostgresCaseStore))


def test_store_rotation_is_postgres_only_at_the_security_boundary():
    store = PostgresCaseStore.__new__(PostgresCaseStore)
    store._db = type("Db", (), {"_use_pg": False})()
    with pytest.raises(RuntimeError, match="case_postgresql_required"):
        store.rotate_receipt("token", None, now=NOW)


def snapshot(*, revision: int = 1, phase: CasePhase = CasePhase.INTAKE) -> CaseSnapshot:
    return CaseSnapshot(
        case_id=CASE_ID,
        service_kind=ServiceKind.CORRECTION,
        category="place-name",
        phase=phase,
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


def _case_row(value: CaseSnapshot) -> dict[str, object]:
    return {
        "case_id": value.case_id,
        "service_kind": value.service_kind.value,
        "category": value.category,
        "phase": value.phase.value,
        "activity": value.activity.value,
        "disposition_family": value.disposition_family.value,
        "domain_outcome": value.domain_outcome,
        "severity": value.severity,
        "reporter_privacy": value.reporter_privacy,
        "owner_ref": value.owner_ref,
        "current_revision": value.current_revision,
        "promise_policy_ref": value.promise_policy_ref,
        "created_at": value.created_at,
        "updated_at": value.updated_at,
        "closed_at": value.closed_at,
    }


class _Connection:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class _DatabaseDouble:
    _use_pg = True

    def __init__(self, *, current: CaseSnapshot | None = None) -> None:
        self.connection = _Connection()
        self.current = current
        self.conn_calls = 0
        self.connections_seen: list[_Connection] = []
        self.sql: list[tuple[str, tuple[object, ...]]] = []

    @contextmanager
    def _conn(self, *, commit_on_success: bool = True):
        assert commit_on_success is False
        self.conn_calls += 1
        try:
            yield self.connection
            self.connection.rollback()
        except BaseException:
            self.connection.rollback()
            raise

    def _record(self, conn, sql, params):
        self.connections_seen.append(conn)
        normalized = " ".join(sql.split())
        self.sql.append((normalized, tuple(params or ())))
        return normalized

    def _execute(self, conn, sql, params=None):
        self._record(conn, sql, params)
        return SimpleNamespace(rowcount=1)

    def _fetchone(self, conn, sql, params=None):
        normalized = self._record(conn, sql, params)
        if "UPDATE cases" in normalized:
            return None
        if "INSERT INTO cases" in normalized:
            return None if self.current is None else _case_row(self.current)
        if "FROM cases" in normalized:
            return None if self.current is None else _case_row(self.current)
        return {"case_id": CASE_ID}

    def _fetchall(self, conn, sql, params=None):
        self._record(conn, sql, params)
        if "case_promise_clocks" not in sql or self.current is None:
            return []
        return [
            {
                "kind": "triage",
                "started_at": NOW,
                "due_at": NOW + timedelta(hours=2),
                "health": "at_risk",
                "policy_revision": "correction-pilot-v1",
                "observed_at": NOW + timedelta(hours=1),
            }
        ]

    @staticmethod
    def _row_to_dict(row):
        return dict(row)


def test_transaction_uses_one_connection_and_commits_once_on_clean_exit():
    database = _DatabaseDouble(current=snapshot())
    store = PostgresCaseStore(database)
    interaction = CaseInteractionDraft(
        case_id=CASE_ID,
        channel=Channel.WEB,
        actor_ref="person:reporter",
        direction="inbound",
        payload_enc="ciphertext:v1",
        created_at=NOW,
    )

    with store.transaction() as transaction:
        transaction.insert_case(snapshot())
        transaction.insert_interaction(interaction)
        transaction.load_case(CASE_ID)

    assert database.conn_calls == 1
    assert set(map(id, database.connections_seen)) == {id(database.connection)}
    assert database.connection.commit_calls == 1
    assert database.connection.rollback_calls == 1


def test_store_module_exposes_the_postgresql_boundary():
    assert case_store.PostgresCaseStore is PostgresCaseStore
    assert case_audit.CaseAuditDraft is CaseAuditDraft


def test_transaction_relies_on_database_context_for_one_exception_rollback():
    database = _DatabaseDouble()
    store = PostgresCaseStore(database)

    with pytest.raises(RuntimeError, match="injected"):
        with store.transaction():
            raise RuntimeError("injected")

    assert database.connection.commit_calls == 0
    assert database.connection.rollback_calls == 1


def test_load_case_maps_driver_rows_to_frozen_typed_snapshot_and_locks_when_requested():
    database = _DatabaseDouble(current=snapshot())
    store = PostgresCaseStore(database)

    with store.transaction() as transaction:
        loaded = transaction.load_case(CASE_ID, for_update=True)

    assert loaded.service_kind is ServiceKind.CORRECTION
    assert loaded.phase is CasePhase.INTAKE
    assert loaded.activity is CaseActivity.ACTIVE
    assert loaded.disposition_family is DispositionFamily.UNDETERMINED
    assert loaded.promise_health is PromiseHealth.AT_RISK
    assert loaded.promise_clocks == (
        PromiseClock(
            kind="triage",
            started_at=NOW,
            due_at=NOW + timedelta(hours=2),
            observed_at=NOW + timedelta(hours=1),
            health=PromiseHealth.AT_RISK,
            policy_revision="correction-pilot-v1",
        ),
    )
    assert any("FOR UPDATE" in sql for sql, _params in database.sql)


def test_cas_conflict_loads_current_snapshot_on_the_same_transaction_connection():
    database = _DatabaseDouble(current=snapshot(revision=2))
    store = PostgresCaseStore(database)

    with pytest.raises(RevisionConflict) as exc_info:
        with store.transaction() as transaction:
            transaction.update_case(1, replace(snapshot(), current_revision=2))

    assert exc_info.value.current.current_revision == 2
    assert database.conn_calls == 1
    assert set(map(id, database.connections_seen)) == {id(database.connection)}


def test_cas_miss_for_absent_case_raises_case_not_found():
    store = PostgresCaseStore(_DatabaseDouble(current=None))

    with pytest.raises(CaseNotFound):
        with store.transaction() as transaction:
            transaction.update_case(1, replace(snapshot(), current_revision=2))


def test_update_rejects_a_snapshot_that_does_not_increment_expected_revision():
    database = _DatabaseDouble(current=snapshot())
    store = PostgresCaseStore(database)

    with pytest.raises(ValueError, match="invalid_case_update"):
        with store.transaction() as transaction:
            transaction.update_case(1, snapshot())

    assert not any("UPDATE cases" in sql for sql, _params in database.sql)


def test_audit_projection_and_outbox_descriptor_are_secret_free_and_deterministic():
    actor = ActorContext(
        actor_ref="person:operator",
        channel=Channel.ZALO_HUMAN,
        scopes=frozenset(("case:write", "case:read")),
        correlation_id="correlation-1",
    )
    projection = safe_case_projection(snapshot())
    draft = CaseAuditDraft.from_snapshots(
        actor=actor,
        reason_code="case_created",
        policy_revision="correction-pilot-v1",
        before=None,
        after=snapshot(),
        occurred_at=NOW,
    )
    outbox = OutboxDraft(
        case_id=CASE_ID,
        idempotency_key=f"{CASE_ID}:case-created:v1",
        topic="case.lifecycle",
        descriptor={"event": "case_created", "revision": 1},
        available_at=NOW,
    )

    assert projection == {
        "case_id": CASE_ID,
        "phase": "intake",
        "activity": "active",
        "disposition_family": "undetermined",
        "domain_outcome": None,
        "severity": "normal",
        "current_revision": 1,
        "promise_policy_ref": "correction-pilot-v1",
        "promise_health": "on_track",
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        "closed_at": None,
    }
    assert not {
        "service_kind",
        "category",
        "reporter_privacy",
        "owner_ref",
        "waiting",
        "promise_clocks",
    } & projection.keys()
    assert draft.actor_scopes == ("case:read", "case:write")
    assert draft.channel is Channel.ZALO_HUMAN
    assert "cipher" not in repr(draft).lower()
    assert outbox.idempotency_key == f"{CASE_ID}:case-created:v1"

    for forbidden in ("contact", "phone", "email", "evidence", "capability", "receipt", "secret"):
        with pytest.raises(ValueError, match="unsafe_outbox_descriptor"):
            OutboxDraft(
                case_id=CASE_ID,
                idempotency_key=f"{CASE_ID}:{forbidden}",
                topic="case.lifecycle",
                descriptor={forbidden: "plaintext"},
                available_at=NOW,
            )


def test_direct_audit_draft_rejects_non_allowlisted_snapshot_fields():
    with pytest.raises(ValueError, match="unsafe_case_audit_snapshot"):
        CaseAuditDraft(
            case_id=CASE_ID,
            actor_ref="person:operator",
            actor_scopes=("case:read",),
            channel=Channel.WEB,
            reason_code="case_created",
            policy_revision="correction-pilot-v1",
            correlation_id="correlation-1",
            before_snapshot=None,
            after_snapshot={"phase": "intake", "contact": "reporter@example.test"},
            occurred_at=NOW,
        )


def test_append_audit_revalidates_and_serializes_before_business_sql():
    database = _DatabaseDouble()
    draft = CaseAuditDraft(
        case_id=CASE_ID,
        actor_ref="person:operator",
        actor_scopes=("case:read",),
        channel=Channel.WEB,
        reason_code="case_created",
        policy_revision="correction-pilot-v1",
        correlation_id="correlation-1",
        before_snapshot=None,
        after_snapshot={"phase": "intake"},
        occurred_at=NOW,
    )
    object.__setattr__(draft, "after_snapshot", {"phase": {"contact": "private"}})

    with pytest.raises(ValueError, match="unsafe_case_audit_snapshot"):
        with PostgresCaseStore(database).transaction() as transaction:
            transaction.append_audit(draft)

    assert not any("case_audit_events" in sql for sql, _params in database.sql)


def test_repository_boundary_exposes_append_only_ledgers_without_mutation_methods():
    store = PostgresCaseStore(_DatabaseDouble())

    with store.transaction() as transaction:
        assert hasattr(transaction, "append_transition")
        assert hasattr(transaction, "append_audit")
        assert not any(
            hasattr(transaction, name)
            for name in (
                "update_transition",
                "delete_transition",
                "update_audit",
                "delete_audit",
            )
        )


def test_transaction_cannot_be_used_after_its_context_exits():
    database = _DatabaseDouble(current=snapshot())
    store = PostgresCaseStore(database)

    with store.transaction() as transaction:
        transaction.load_case(CASE_ID)

    with pytest.raises(RuntimeError, match="case_transaction_closed"):
        transaction.load_case(CASE_ID)


# ── Task 6 additions: evidence, entity guard, and idempotency claims ──

class _RecordingDatabase:
    _use_pg = True

    def __init__(self, rows=None) -> None:
        self.statements: list[tuple[str, tuple]] = []
        self._rows = list(rows or [])

    def _execute(self, conn, sql, params):
        self.statements.append((" ".join(sql.split()), params))

    def _fetchone(self, conn, sql, params):
        self.statements.append((" ".join(sql.split()), params))
        return self._rows.pop(0) if self._rows else None

    @staticmethod
    def _row_to_dict(row):
        return row


def _transaction(database):
    return case_store.CaseTransaction(database, object())


def test_require_entities_rejects_an_unknown_correction_target():
    database = _RecordingDatabase(rows=[None])

    with pytest.raises(CaseNotFound):
        _transaction(database).require_entities(("p-missing",))


def test_require_entities_checks_each_distinct_target_once():
    database = _RecordingDatabase(rows=[{"id": "p-a"}, {"id": "p-b"}])

    _transaction(database).require_entities(("p-b", "p-a", "p-b"))

    assert [params for _, params in database.statements] == [("p-a",), ("p-b",)]


@pytest.mark.parametrize("entity_ids", [["p-a"], ("",), (None,), "p-a"])
def test_require_entities_refuses_a_malformed_reference(entity_ids):
    with pytest.raises(ValueError, match="invalid_entity_reference"):
        _transaction(_RecordingDatabase()).require_entities(entity_ids)


def test_claim_idempotency_takes_a_transaction_lock_before_reading_the_row():
    database = _RecordingDatabase(rows=[None, None])

    assert _transaction(database).claim_idempotency("create:k", now=NOW) is None

    assert "pg_advisory_xact_lock" in database.statements[0][0]
    assert "FOR UPDATE" in database.statements[1][0]


@pytest.mark.parametrize(
    ("key", "now"),
    [("", NOW), ("create:k", datetime(2026, 8, 12, 9, 0)), (None, NOW)],
)
def test_claim_idempotency_refuses_a_malformed_claim(key, now):
    with pytest.raises(ValueError, match="invalid_idempotency_claim"):
        _transaction(_RecordingDatabase()).claim_idempotency(key, now=now)


def test_record_idempotency_stores_a_bounded_ttl_and_the_current_key_version():
    database = _RecordingDatabase()

    _transaction(database).record_idempotency(
        "create:k", actor_ref="anonymous", request_digest="d" * 64,
        response_enc="cipher", now=NOW,
    )

    sql, params = database.statements[0]
    assert "'v1'" in sql
    assert params[4] == NOW + timedelta(hours=24)
    assert "cipher" in params


def test_evidence_drafts_must_carry_a_real_evidence_level():
    draft = case_store.CorrectionEvidenceDraft(
        case_id=CASE_ID, item_id=None, evidence_level="E0", source_ref=None,
        descriptor={}, content_enc=None, created_by_ref="anonymous",
    )

    with pytest.raises(ValueError, match="invalid_correction_evidence_drafts"):
        _transaction(_RecordingDatabase()).insert_correction_evidence((draft,))


def test_evidence_descriptors_cannot_smuggle_contact_or_secret_keys():
    draft = case_store.CorrectionEvidenceDraft(
        case_id=CASE_ID, item_id=None, evidence_level=case_store.EvidenceLevel.E0,
        source_ref=None, descriptor={"contact": "0901234567"}, content_enc=None,
        created_by_ref="anonymous",
    )

    with pytest.raises(ValueError, match="unsafe_outbox_descriptor"):
        _transaction(_RecordingDatabase()).insert_correction_evidence((draft,))


def test_require_entities_holds_the_row_against_a_concurrent_delete():
    """The guard must outlive the check, or the FK raises a driver error later."""
    database = _RecordingDatabase(rows=[{"id": "p-a"}])

    _transaction(database).require_entities(("p-a",))

    assert "FOR KEY SHARE" in database.statements[0][0]


# ── Task 7: reads that feed the public projection ──

class _ReadingDatabase(_RecordingDatabase):
    def __init__(self, rows=None, many=None) -> None:
        super().__init__(rows)
        self._many = list(many or [])

    def _fetchall(self, conn, sql, params):
        self.statements.append((" ".join(sql.split()), params))
        return self._many.pop(0) if self._many else []


def test_the_item_read_never_selects_an_encrypted_value():
    database = _ReadingDatabase(many=[[]])

    _transaction(database).load_correction_items(CASE_ID)

    sql = database.statements[0][0]
    assert "reported_value_enc" not in sql and "proposed_value_enc" not in sql
    assert "risk_class" in sql and "evidence_level" in sql


def test_items_are_returned_as_domain_objects_in_creation_order():
    database = _ReadingDatabase(many=[[
        {"item_id": "i-1", "entity_id": "p-a", "field_path": "attributes.phone",
         "base_entity_revision": 7, "risk_class": "R1", "evidence_level": "E0"},
    ]])

    items = _transaction(database).load_correction_items(CASE_ID)

    assert len(items) == 1
    assert items[0].item_id == "i-1"
    assert items[0].risk_class.value == "R1"
    assert "ORDER BY created_at, item_id" in database.statements[0][0]


def test_the_public_reference_read_ignores_a_revoked_receipt():
    database = _ReadingDatabase(rows=[{"public_reference": "VL-COR-ABCDEFGHJKMN0"}])

    reference = _transaction(database).load_public_reference(CASE_ID)

    sql = database.statements[0][0]
    assert reference == "VL-COR-ABCDEFGHJKMN0"
    assert "revoked_at IS NULL" in sql
    assert "ORDER BY receipt_revision DESC" in sql


def test_a_case_with_no_live_receipt_reports_no_reference():
    assert _transaction(_ReadingDatabase(rows=[None])).load_public_reference(CASE_ID) is None


@pytest.mark.parametrize(
    ("phase", "expected"),
    [("intake", "requested"), ("triage", "in_progress"), ("closed", "completed")],
)
def test_review_links_map_a_backstage_phase_to_a_review_status(phase, expected):
    database = _ReadingDatabase(many=[[{"case_id": "r-1", "phase": phase}]])

    links = _transaction(database).load_review_links(CASE_ID)

    assert links[0].status.value == expected


def test_linking_a_review_updates_only_the_new_case_row():
    database = _ReadingDatabase()

    _transaction(database).link_review_case("r-1", review_of_case_id=CASE_ID)

    sql, params = database.statements[0]
    assert sql.startswith("UPDATE cases SET review_of_case_id")
    assert params == (CASE_ID, "r-1")
