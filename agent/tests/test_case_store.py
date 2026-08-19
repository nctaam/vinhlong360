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
    # Same ordering contract; the columns are aliased now that the query joins.
    assert "ORDER BY i.created_at, i.item_id" in database.statements[0][0]


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


# ── Task 10: decision and change-set write paths ──

def test_the_change_set_read_selects_the_ciphertext_the_public_read_must_not():
    public = _ReadingDatabase(many=[[]])
    private = _ReadingDatabase(many=[[]])

    _transaction(public).load_correction_items(CASE_ID)
    _transaction(private).load_correction_item_payloads(CASE_ID, ("i-1",))

    public_sql = public.statements[0][0]
    private_sql = private.statements[0][0]
    # One read feeds the public projection, the other builds a change set.
    assert "reported_value_enc" not in public_sql
    assert "reported_value_enc" in private_sql and "proposed_value_enc" in private_sql


@pytest.mark.parametrize("item_ids", [(), ["i-1"], "i-1"])
def test_the_change_set_read_refuses_a_malformed_selection(item_ids):
    with pytest.raises(ValueError, match="invalid_correction_item_selection"):
        _transaction(_ReadingDatabase()).load_correction_item_payloads(CASE_ID, item_ids)


def test_a_lease_check_only_counts_a_live_claim_by_that_actor():
    database = _ReadingDatabase(rows=[None])

    assert _transaction(database).actor_holds_lease(CASE_ID, "person:x", now=NOW) is False

    sql = database.statements[0][0]
    assert "status = 'claimed'" in sql
    assert "assignee_ref = %s" in sql
    assert "lease_expires_at > %s" in sql


def test_a_change_set_is_always_inserted_pending():
    database = _ReadingDatabase(rows=[{"change_set_id": "cs-1"}])

    _transaction(database).insert_change_set(
        case_id=CASE_ID, base_entity_revision=7, before_patch={"a": 1}, after_patch={"a": 2},
        inverse_patch={"a": 1}, evidence_refs=("e-1",), policy_revision="correction-pilot-v1",
        risk_class="R1", decision_maker_ref="person:maker", reviewer_ref=None, created_at=NOW,
    )

    sql = database.statements[0][0]
    assert "'pending'" in sql
    # Nothing here may pre-declare a public projection as verified.
    assert "public_projection_verified_at" not in sql


def test_a_decision_row_carries_its_lineage_and_policy_revision():
    database = _ReadingDatabase(rows=[{"decision_id": "d-1"}])

    decision_id = _transaction(database).insert_decision(
        case_id=CASE_ID, item_id="i-1", outcome_code="corrected",
        reason_code="source_confirms", evidence_refs=("e-1", "e-2"),
        decision_maker_ref="person:maker", reviewer_ref="person:checker",
        policy_revision="correction-pilot-v1", decided_at=NOW,
    )

    sql, params = database.statements[0]
    assert decision_id == "d-1"
    assert "evidence_refs" in sql and "policy_revision" in sql
    assert '["e-1","e-2"]' in params
    assert "person:checker" in params


def test_linking_change_set_items_is_repeatable():
    database = _ReadingDatabase()

    _transaction(database).link_change_set_items("cs-1", ("i-1", "i-2"))

    assert len(database.statements) == 2
    assert all("ON CONFLICT DO NOTHING" in sql for sql, _ in database.statements)


# ── Change set lifecycle (Task 12) ──

class _RowsDatabase(_RecordingDatabase):
    """A recording double that can also answer multi-row reads."""

    def __init__(self, rows=None, many=None) -> None:
        super().__init__(rows)
        self._many = list(many or [])

    def _fetchall(self, conn, sql, params):
        self.statements.append((" ".join(sql.split()), params))
        return self._many.pop(0) if self._many else []


def test_loading_a_change_set_for_update_takes_the_lock():
    database = _RowsDatabase(rows=[{"change_set_id": "cs-1", "apply_status": "pending"}])

    _transaction(database).load_change_set("cs-1", for_update=True)

    assert "FOR UPDATE" in database.statements[0][0]


def test_an_unknown_change_set_is_reported_as_missing_not_as_empty():
    with pytest.raises(case_store.ChangeSetNotFound):
        _transaction(_RowsDatabase()).load_change_set("cs-nope")


def test_a_change_set_target_is_one_entry_and_the_items_that_asked_for_it():
    database = _RowsDatabase(many=[[
        {"item_id": "i-1", "entity_id": "p-1"},
        {"item_id": "i-2", "entity_id": "p-1"},
    ]])

    entity_id, item_ids = _transaction(database).load_change_set_target("cs-1")

    assert entity_id == "p-1"
    assert item_ids == ("i-1", "i-2")


def test_a_change_set_whose_rows_drifted_across_entries_is_refused():
    database = _RowsDatabase(many=[[
        {"item_id": "i-1", "entity_id": "p-1"},
        {"item_id": "i-2", "entity_id": "p-2"},
    ]])

    # Task 10 refuses to build one; reaching here means the rows moved under us,
    # and publishing would edit an entry nobody decided about.
    with pytest.raises(ValueError, match="change_set_spans_entities"):
        _transaction(database).load_change_set_target("cs-1")


def test_marking_a_change_set_is_a_compare_and_set():
    database = _RowsDatabase(rows=[{"change_set_id": "cs-1"}])

    _transaction(database).set_change_set_apply_status(
        "cs-1", expected_status="pending", status="applied"
    )

    sql, params = database.statements[0]
    assert "apply_status = %s" in sql
    assert sql.endswith("RETURNING change_set_id")
    assert "AND apply_status = %s" in sql
    assert params[-1] == "pending"


def test_a_change_set_that_moved_underneath_refuses_the_mark():
    # No row came back: somebody else marked it between the read and the write.
    with pytest.raises(case_store.ChangeSetStateConflict):
        _transaction(_RowsDatabase()).set_change_set_apply_status(
            "cs-1", expected_status="pending", status="applied"
        )


def test_completing_work_touches_only_the_kind_it_was_asked_for():
    database = _RowsDatabase()
    now = datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc)

    _transaction(database).complete_work_item_of_kind("case-1", "publication", now=now)

    sql, params = database.statements[0]
    assert "status = 'completed'" in sql
    assert "AND kind = %s" in sql
    assert "status <> 'completed'" in sql
    assert params[1:] == ("case-1", "publication")


def test_an_item_with_no_change_set_owes_the_public_nothing():
    from cases.domain import PublicationState

    assert case_store._publication_state({}) is PublicationState.NOT_REQUIRED


def test_applied_and_verified_are_different_things_to_tell_the_reporter():
    from cases.domain import PublicationState

    applied = {"apply_status": "applied", "public_projection_verified_at": None}
    verified = {"apply_status": "applied", "public_projection_verified_at": "2026-08-19"}

    # Telling somebody their correction is live before anyone looked at the page
    # is the claim this distinction exists to prevent.
    assert case_store._publication_state(applied) is PublicationState.APPLIED
    assert case_store._publication_state(verified) is PublicationState.VERIFIED


def test_a_withdrawn_change_reads_as_rolled_back_not_as_done():
    from cases.domain import PublicationState

    assert case_store._publication_state(
        {"apply_status": "rolled_back", "public_projection_verified_at": "2026-08-19"}
    ) is PublicationState.ROLLED_BACK


# ── Private-data clearance (Task 13) ──

def test_a_clearance_is_stored_by_digest_and_nothing_else():
    database = _RowsDatabase()

    _transaction(database).grant_admin_access(
        case_id="case-1", actor_ref="user:7", scope="case.private_evidence",
        session_digest="d" * 64,
        expires_at=datetime(2026, 8, 19, 9, 15, tzinfo=timezone.utc),
    )

    sql, params = database.statements[0]
    assert "INSERT INTO case_admin_access_sessions" in sql
    assert "session_digest" in sql
    # The column list must not carry the secret itself under any name.
    assert "secret" not in sql and "capability" not in sql
    assert "d" * 64 in params


def test_checking_a_clearance_tests_every_condition_in_one_query():
    database = _RowsDatabase(rows=[{"?column?": 1}])

    live = _transaction(database).admin_access_is_live(
        case_id="case-1", actor_ref="user:7", scope="case.private_evidence",
        session_digest="d" * 64, now=datetime(2026, 8, 19, 9, 5, tzinfo=timezone.utc),
    )

    sql, _params = database.statements[0]
    assert live is True
    # Splitting these would let a revoked or expired grant pass one check and be
    # judged on another.
    for condition in ("case_id = %s", "actor_ref = %s", "scope = %s",
                      "session_digest = %s", "revoked_at IS NULL", "expires_at > %s"):
        assert condition in sql


def test_an_absent_clearance_reads_as_absent_rather_than_erroring():
    live = _transaction(_RowsDatabase()).admin_access_is_live(
        case_id="case-1", actor_ref="user:7", scope="case.private_evidence",
        session_digest="d" * 64, now=datetime(2026, 8, 19, 9, 5, tzinfo=timezone.utc),
    )

    assert live is False


def test_revoking_takes_back_every_live_clearance_that_person_holds():
    database = _RowsDatabase()

    _transaction(database).revoke_admin_access(
        case_id="case-1", actor_ref="user:7",
        now=datetime(2026, 8, 19, 9, 5, tzinfo=timezone.utc),
    )

    sql, _params = database.statements[0]
    assert "SET revoked_at = %s" in sql
    # Not just the newest one: logging out has to close all of them.
    assert "revoked_at IS NULL" in sql


def test_loading_evidence_returns_descriptors_and_never_the_payload():
    database = _RowsDatabase(many=[[
        {"evidence_id": "e-1", "case_id": "c-1", "item_id": "i-1",
         "evidence_level": "E3", "source_ref": None,
         "descriptor": {"source_scope": "place.contact"},
         "created_by_ref": "person:maker", "created_at": None},
    ]])

    rows = _transaction(database).load_correction_evidence("c-1")

    sql, params = database.statements[0]
    # content_enc is the private column; a reader of descriptors must not get it.
    assert "content_enc" not in sql
    assert params == ("c-1",)
    assert rows[0]["descriptor"]["source_scope"] == "place.contact"


def test_evidence_can_be_narrowed_to_one_item():
    database = _RowsDatabase(many=[[]])

    _transaction(database).load_correction_evidence("c-1", "i-1")

    sql, params = database.statements[0]
    assert "AND item_id = %s" in sql
    assert params == ("c-1", "i-1")


# ── The legacy ledger (Task 17) ──

def test_a_ledger_row_is_keyed_so_replays_are_no_ops():
    database = _RowsDatabase()
    now = datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc)

    _transaction(database).record_legacy_intake(
        source_file="agent/data/reports.jsonl", source_line=7,
        raw_record_digest="d" * 64, legacy_status="open",
        mapping_decision="factual_field_report", import_result="correction",
        missing_data_flags=[], imported_at=now,
    )

    sql, params = database.statements[0]
    # The conflict clause on the locator key is what makes a re-run idempotent.
    assert "ON CONFLICT (source_file, source_line) DO NOTHING" in sql
    assert params[0] == "agent/data/reports.jsonl" and params[1] == 7


def test_the_ledger_summary_counts_every_explanation_bucket():
    database = _RowsDatabase(rows=[{"rows": 5, "corrections": 1,
                                    "duplicates": 1, "unexplained": 0}])

    summary = _transaction(database).legacy_intake_summary("agent/data/reports.jsonl")

    sql, _params = database.statements[0]
    # A row whose import_result is outside the vocabulary counts as unexplained,
    # and reconciliation fails cutover on anything above zero.
    assert "NOT IN" in sql and "unexplained" in sql
    assert summary == {"rows": 5, "corrections": 1, "duplicates": 1, "unexplained": 0}


def test_the_freeze_probe_asks_only_for_the_marker_row():
    database = _RowsDatabase(rows=[{"?column?": 1}])

    assert _transaction(database).legacy_freeze_present("__correction_write_freeze__") is True
    sql, params = database.statements[0]
    assert "import_result = 'freeze'" in sql
    assert params == ("__correction_write_freeze__",)


# ── Capacity and retention (Task 18) ──

def test_a_capacity_event_travels_with_its_grouping_and_json_metadata():
    database = _RowsDatabase()
    now = datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc)

    _transaction(database).record_capacity_event(
        kind="received", channel="web", risk_class="R1", case_id=None,
        duration_seconds=None, metadata={"queue": "decide"}, observed_at=now,
    )

    sql, params = database.statements[0]
    assert "INSERT INTO case_capacity_events" in sql
    assert params[3] == "received" and '"queue"' in params[6]


def test_contact_redaction_only_reaches_terminally_closed_cases():
    database = _RowsDatabase()

    _transaction(database).redact_closed_case_contacts(
        closed_before=datetime(2026, 5, 19, tzinfo=timezone.utc)
    )

    sql, _params = database.statements[0]
    # An open case has no terminal close, so its clock has not started.
    assert "closed_at IS NOT NULL" in sql
    assert "payload_enc = NULL" in sql


def test_payload_redaction_names_its_holds_in_the_query():
    database = _RowsDatabase()

    count, held = _transaction(database).redact_private_payloads(
        closed_before=datetime(2025, 8, 19, tzinfo=timezone.utc),
        excluded_case_ids=("case-held",),
    )

    sql, params = database.statements[0]
    assert "case_id != ALL(%s::uuid[])" in sql
    assert held == ("case-held",)


def test_deidentifying_capacity_keeps_the_rows_and_drops_the_link():
    database = _RowsDatabase()

    _transaction(database).deidentify_capacity_events(
        observed_before=datetime(2024, 8, 19, tzinfo=timezone.utc)
    )

    sql, _params = database.statements[0]
    # UPDATE, not DELETE: the numbers stay; the person-linkable key goes.
    assert sql.startswith("UPDATE case_capacity_events SET case_id = NULL")


def test_public_items_carry_the_latest_ruling_so_the_page_can_answer():
    database = _RowsDatabase(many=[[
        {"item_id": "i-1", "entity_id": "p-1", "field_path": "attributes.phone",
         "base_entity_revision": 3, "risk_class": "R1", "evidence_level": "E3",
         "apply_status": None, "public_projection_verified_at": None,
         "outcome_code": "corrected"},
    ]])

    items = _transaction(database).load_correction_items("c-1")

    sql, _params = database.statements[0]
    # Latest per item, because a review may re-rule; without this join the
    # reporter's page said "đang xem xét" forever, whatever was decided.
    assert "case_decisions" in sql and "ORDER BY decided_at DESC LIMIT 1" in sql
    assert items[0].accepted is True


def test_a_waiting_transition_is_observed_when_it_is_appended(monkeypatch):
    from cases.domain import CasePhase, WaitingContext
    from cases.transitions import TransitionDraft

    events = []
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append((kind, kw.get("case_id"))) or True)
    database = _RowsDatabase(rows=[{"transition_id": "t-1"}])
    now = datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc)
    waiting = WaitingContext(
        requester_request="giấy phép", safe_message="đang chờ bạn bổ sung",
        waiting_on_ref="requester", evidence_ref="e-1",
        next_review_at=now + timedelta(days=2), started_at=now,
    )

    _transaction(database).append_transition(TransitionDraft(
        case_id="case-1", from_phase=CasePhase.TRIAGE, to_phase=CasePhase.INVESTIGATION,
        from_revision=1, to_revision=2, actor_ref="person:op",
        reason_code="waiting_on_requester", policy_revision="p", correlation_id="c",
        occurred_at=now, waiting=waiting,
    ))

    assert ("waiting", "case-1") in events


def test_completed_work_assignees_reads_only_finished_work():
    database = _RowsDatabase(many=[[{"assignee_ref": "person:checker"}]])

    finished = _transaction(database).completed_work_assignees("case-1", "truth_review")

    sql, params = database.statements[0]
    assert "status = 'completed'" in sql
    assert params == ("case-1", "truth_review")
    assert finished == ("person:checker",)


def test_a_dead_rotation_bearer_is_refused_for_every_reason_alike():
    from cases.security import CaseSecurityError
    from cases.store import PostgresCaseStore

    now = datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc)
    live = {
        "session_key_version": "v1", "session_revoked_at": None,
        "session_expires_at": now + timedelta(minutes=10),
        "receipt_revoked_at": None, "receipt_expires_at": now + timedelta(days=1),
        "subject_user_id": None,
    }

    # The live bearer passes; every single way it can be dead refuses alike.
    PostgresCaseStore._require_live_rotation_bearer(live, now=now, current_user_id=None)
    for poison in (
        {"session_key_version": "v0"},
        {"session_revoked_at": now},
        {"session_expires_at": now},
        {"receipt_revoked_at": now},
        {"receipt_expires_at": now},
        {"subject_user_id": "user:1001"},
    ):
        with pytest.raises(CaseSecurityError):
            PostgresCaseStore._require_live_rotation_bearer(
                {**live, **poison}, now=now, current_user_id=None,
            )
