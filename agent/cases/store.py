from __future__ import annotations

import json
import hmac
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .audit import CaseAuditDraft, serialize_case_projection
from .domain import (
    CaseActivity,
    CasePhase,
    CaseSnapshot,
    Channel,
    CorrectionItem,
    DispositionFamily,
    EvidenceLevel,
    PromiseClock,
    PromiseHealth,
    ReviewCaseLink,
    ReviewCaseStatus,
    RiskClass,
    ServiceKind,
)
from .queue_policy import WorkItemDraft
from .transitions import TransitionDraft


class CaseNotFound(LookupError):
    pass


class RevisionConflict(RuntimeError):
    def __init__(self, current: CaseSnapshot):
        super().__init__("case_revision_conflict")
        self.current = current


@dataclass(frozen=True)
class CaseInteractionDraft:
    case_id: str
    channel: Channel
    actor_ref: str
    direction: str
    consent_ref: str | None = None
    identity_assurance: str | None = None
    payload_enc: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class PartyAuthorityDraft:
    case_id: str
    party_ref: str
    authority_kind: str
    scope: str
    assurance_level: str
    granted_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class CorrectionItemDraft:
    entity_id: str | None
    field_path: str
    reported_value_enc: str | None
    proposed_value_enc: str | None
    base_entity_revision: int
    risk_class: RiskClass
    evidence_level: EvidenceLevel
    created_at: datetime | None = None


@dataclass(frozen=True)
class CorrectionEvidenceDraft:
    case_id: str
    item_id: str | None
    evidence_level: EvidenceLevel
    source_ref: str | None
    descriptor: Mapping[str, object]
    content_enc: str | None
    created_by_ref: str
    created_at: datetime | None = None


def _freeze_json(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError("invalid_outbox_descriptor")


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


_FORBIDDEN_OUTBOX_KEYS = (
    "contact",
    "phone",
    "email",
    "evidence",
    "capability",
    "receipt",
    "secret",
    "plaintext",
)


def _validate_descriptor(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str or not key:
                raise ValueError("unsafe_outbox_descriptor")
            normalized = key.lower().replace("-", "_")
            if any(token in normalized for token in _FORBIDDEN_OUTBOX_KEYS):
                raise ValueError("unsafe_outbox_descriptor")
            _validate_descriptor(item)
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_descriptor(item)


@dataclass(frozen=True)
class OutboxDraft:
    case_id: str | None
    idempotency_key: str
    topic: str
    descriptor: Mapping[str, object]
    available_at: datetime

    def __post_init__(self) -> None:
        if (
            self.case_id is not None
            and (type(self.case_id) is not str or not self.case_id)
        ) or (
            type(self.idempotency_key) is not str
            or not self.idempotency_key
            or type(self.topic) is not str
            or not self.topic
            or not isinstance(self.descriptor, Mapping)
            or type(self.available_at) is not datetime
            or self.available_at.tzinfo is None
        ):
            raise ValueError("invalid_outbox_draft")
        frozen = _freeze_json(self.descriptor)
        _validate_descriptor(frozen)
        object.__setattr__(self, "descriptor", frozen)


def _enum_value(value: object) -> object:
    return value.value if isinstance(value, Enum) else value


def _row_dict(database, row) -> dict[str, object]:
    return database._row_to_dict(row)


def _promise_clocks(database, conn, case_id: str) -> tuple[PromiseClock, ...]:
    rows = database._fetchall(
        conn,
        """
        SELECT kind, started_at, due_at, health, policy_revision, observed_at
        FROM case_promise_clocks
        WHERE case_id = %s
        ORDER BY started_at, clock_id
        """,
        (case_id,),
    )
    return tuple(
        PromiseClock(
            kind=item["kind"],
            started_at=item["started_at"],
            due_at=item["due_at"],
            observed_at=item["observed_at"],
            health=PromiseHealth(item["health"]),
            policy_revision=item["policy_revision"],
        )
        for item in (_row_dict(database, row) for row in rows)
    )


def _snapshot_from_row(database, conn, row) -> CaseSnapshot:
    item = _row_dict(database, row)
    clocks = _promise_clocks(database, conn, str(item["case_id"]))
    health_rank = {
        PromiseHealth.ON_TRACK: 0,
        PromiseHealth.RECOVERY: 1,
        PromiseHealth.AT_RISK: 2,
        PromiseHealth.BREACHED: 3,
    }
    health = max(
        (PromiseHealth.ON_TRACK, *(clock.health for clock in clocks)),
        key=health_rank.__getitem__,
    )
    return CaseSnapshot(
        case_id=str(item["case_id"]),
        service_kind=ServiceKind(item["service_kind"]),
        category=item["category"],
        phase=CasePhase(item["phase"]),
        activity=CaseActivity(item["activity"]),
        disposition_family=DispositionFamily(item["disposition_family"]),
        domain_outcome=item["domain_outcome"],
        severity=item["severity"],
        reporter_privacy=item["reporter_privacy"],
        owner_ref=item["owner_ref"],
        current_revision=int(item["current_revision"]),
        promise_policy_ref=item["promise_policy_ref"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        closed_at=item["closed_at"],
        promise_health=health,
        promise_clocks=clocks,
    )


_CASE_COLUMNS = """
case_id, service_kind, category, phase, activity, disposition_family,
domain_outcome, severity, reporter_privacy, owner_ref, current_revision,
promise_policy_ref, created_at, updated_at, closed_at
"""


class CaseTransaction:
    def __init__(self, database, conn) -> None:
        self._db = database
        self._conn = conn
        self._active = True

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError("case_transaction_closed")

    def _close(self) -> None:
        self._active = False

    def insert_case(self, snapshot: CaseSnapshot) -> CaseSnapshot:
        self._require_active()
        if type(snapshot) is not CaseSnapshot:
            raise ValueError("invalid_case_snapshot")
        row = self._db._fetchone(
            self._conn,
            f"""
            INSERT INTO cases ({_CASE_COLUMNS})
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_CASE_COLUMNS}
            """,
            (
                snapshot.case_id,
                snapshot.service_kind.value,
                snapshot.category,
                snapshot.phase.value,
                snapshot.activity.value,
                snapshot.disposition_family.value,
                _enum_value(snapshot.domain_outcome),
                snapshot.severity,
                snapshot.reporter_privacy,
                snapshot.owner_ref,
                snapshot.current_revision,
                snapshot.promise_policy_ref,
                snapshot.created_at,
                snapshot.updated_at,
                snapshot.closed_at,
            ),
        )
        return _snapshot_from_row(self._db, self._conn, row)

    def insert_interaction(self, draft: CaseInteractionDraft) -> None:
        self._require_active()
        if type(draft) is not CaseInteractionDraft or type(draft.channel) is not Channel:
            raise ValueError("invalid_interaction_draft")
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_interactions (
                case_id, channel, actor_ref, direction, consent_ref,
                identity_assurance, payload_enc, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))
            """,
            (
                draft.case_id,
                draft.channel.value,
                draft.actor_ref,
                draft.direction,
                draft.consent_ref,
                draft.identity_assurance,
                draft.payload_enc,
                draft.created_at,
            ),
        )

    def insert_party_authority(self, draft: PartyAuthorityDraft) -> None:
        self._require_active()
        if type(draft) is not PartyAuthorityDraft:
            raise ValueError("invalid_party_authority_draft")
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_party_authorities (
                case_id, party_ref, authority_kind, scope, assurance_level,
                granted_at, expires_at, revoked_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                draft.case_id,
                draft.party_ref,
                draft.authority_kind,
                draft.scope,
                draft.assurance_level,
                draft.granted_at,
                draft.expires_at,
                draft.revoked_at,
            ),
        )

    def insert_correction_items(
        self, case_id: str, drafts: tuple[CorrectionItemDraft, ...]
    ) -> tuple[str, ...]:
        self._require_active()
        if type(drafts) is not tuple or not all(
            type(draft) is CorrectionItemDraft for draft in drafts
        ):
            raise ValueError("invalid_correction_item_drafts")
        item_ids = []
        for draft in drafts:
            row = self._db._fetchone(
                self._conn,
                """
                INSERT INTO correction_items (
                    case_id, entity_id, field_path, reported_value_enc,
                    proposed_value_enc, base_entity_revision, risk_class,
                    evidence_level, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))
                RETURNING item_id
                """,
                (
                    case_id,
                    draft.entity_id,
                    draft.field_path,
                    draft.reported_value_enc,
                    draft.proposed_value_enc,
                    draft.base_entity_revision,
                    draft.risk_class.value,
                    draft.evidence_level.value,
                    draft.created_at,
                ),
            )
            item_ids.append(str(_row_dict(self._db, row)["item_id"]))
        return tuple(item_ids)

    def insert_correction_evidence(
        self, drafts: tuple[CorrectionEvidenceDraft, ...]
    ) -> tuple[str, ...]:
        self._require_active()
        if type(drafts) is not tuple or not all(
            type(draft) is CorrectionEvidenceDraft for draft in drafts
        ):
            raise ValueError("invalid_correction_evidence_drafts")
        evidence_ids = []
        for draft in drafts:
            if type(draft.evidence_level) is not EvidenceLevel:
                raise ValueError("invalid_correction_evidence_drafts")
            descriptor = _freeze_json(draft.descriptor)
            _validate_descriptor(descriptor)
            row = self._db._fetchone(
                self._conn,
                """
                INSERT INTO correction_evidence (
                    case_id, item_id, evidence_level, source_ref, descriptor,
                    content_enc, created_by_ref, created_at
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, COALESCE(%s, NOW()))
                RETURNING evidence_id
                """,
                (
                    draft.case_id,
                    draft.item_id,
                    draft.evidence_level.value,
                    draft.source_ref,
                    json.dumps(_plain_json(descriptor), sort_keys=True),
                    draft.content_enc,
                    draft.created_by_ref,
                    draft.created_at,
                ),
            )
            evidence_ids.append(str(_row_dict(self._db, row)["evidence_id"]))
        return tuple(evidence_ids)

    def insert_promise_clocks(
        self, case_id: str, clocks: tuple[PromiseClock, ...]
    ) -> None:
        self._require_active()
        if type(clocks) is not tuple or not all(type(clock) is PromiseClock for clock in clocks):
            raise ValueError("invalid_promise_clocks")
        for clock in clocks:
            self._db._execute(
                self._conn,
                """
                INSERT INTO case_promise_clocks (
                    case_id, kind, started_at, due_at, health,
                    policy_revision, observed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    clock.kind,
                    clock.started_at,
                    clock.due_at,
                    clock.health.value,
                    clock.policy_revision,
                    clock.observed_at,
                ),
            )

    def insert_work_items(self, drafts: tuple[WorkItemDraft, ...]) -> None:
        self._require_active()
        if type(drafts) is not tuple or not all(type(draft) is WorkItemDraft for draft in drafts):
            raise ValueError("invalid_work_item_drafts")
        for draft in drafts:
            self._db._execute(
                self._conn,
                """
                INSERT INTO case_work_items (
                    case_id, kind, required_role, risk_class, status,
                    ready_at, next_review_at, priority
                ) VALUES (%s, %s, %s, %s, 'ready', %s, NULL, %s)
                """,
                (
                    draft.case_id,
                    draft.kind,
                    draft.required_role,
                    draft.risk_class.value,
                    draft.ready_at,
                    100 if draft.emergency else 0,
                ),
            )

    def append_transition(self, draft: TransitionDraft) -> None:
        self._require_active()
        if type(draft) is not TransitionDraft:
            raise ValueError("invalid_transition_draft")
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_transitions (
                case_id, from_phase, to_phase, from_revision, to_revision,
                actor_ref, reason_code, policy_revision, correlation_id, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                draft.case_id,
                draft.from_phase.value if draft.from_phase is not None else None,
                draft.to_phase.value,
                draft.from_revision,
                draft.to_revision,
                draft.actor_ref,
                draft.reason_code,
                draft.policy_revision,
                draft.correlation_id,
                draft.occurred_at,
            ),
        )

    def append_audit(self, draft: CaseAuditDraft) -> None:
        self._require_active()
        if type(draft) is not CaseAuditDraft:
            raise ValueError("invalid_case_audit")
        before_snapshot = serialize_case_projection(draft.before_snapshot)
        after_snapshot = serialize_case_projection(draft.after_snapshot)
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_audit_events (
                case_id, actor_ref, actor_scopes, channel, reason_code,
                policy_revision, correlation_id, before_snapshot,
                after_snapshot, created_at
            ) VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
            """,
            (
                draft.case_id,
                draft.actor_ref,
                json.dumps(draft.actor_scopes, separators=(",", ":")),
                draft.channel.value,
                draft.reason_code,
                draft.policy_revision,
                draft.correlation_id,
                before_snapshot,
                after_snapshot,
                draft.occurred_at,
            ),
        )

    def enqueue_outbox(self, draft: OutboxDraft) -> None:
        self._require_active()
        if type(draft) is not OutboxDraft:
            raise ValueError("invalid_outbox_draft")
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_outbox (
                case_id, idempotency_key, topic, payload, available_at
            ) VALUES (%s, %s, %s, %s::jsonb, %s)
            """,
            (
                draft.case_id,
                draft.idempotency_key,
                draft.topic,
                json.dumps(_plain_json(draft.descriptor), sort_keys=True),
                draft.available_at,
            ),
        )

    def load_correction_items(self, case_id: str) -> tuple[CorrectionItem, ...]:
        """Public-projection view: identifiers and classification, never values."""
        self._require_active()
        rows = self._db._fetchall(
            self._conn,
            """
            SELECT item_id, entity_id, field_path, base_entity_revision,
                   risk_class, evidence_level
            FROM correction_items WHERE case_id = %s ORDER BY created_at, item_id
            """,
            (case_id,),
        )
        return tuple(
            CorrectionItem(
                item_id=str(item["item_id"]),
                risk_class=RiskClass(item["risk_class"]),
                evidence_level=EvidenceLevel(item["evidence_level"]),
                entity_id=item["entity_id"],
                field_path=item["field_path"],
                base_entity_revision=int(item["base_entity_revision"]),
            )
            for item in (_row_dict(self._db, row) for row in rows)
        )

    def load_public_reference(self, case_id: str) -> str | None:
        """The live receipt's reference; a rotated or revoked one is not it."""
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            SELECT public_reference FROM case_receipts
            WHERE case_id = %s AND revoked_at IS NULL
            ORDER BY receipt_revision DESC LIMIT 1
            """,
            (case_id,),
        )
        return None if row is None else str(_row_dict(self._db, row)["public_reference"])

    def load_review_links(self, case_id: str) -> tuple[ReviewCaseLink, ...]:
        self._require_active()
        rows = self._db._fetchall(
            self._conn,
            "SELECT case_id, phase FROM cases WHERE review_of_case_id = %s ORDER BY created_at",
            (case_id,),
        )
        statuses = {
            CasePhase.INTAKE.value: ReviewCaseStatus.REQUESTED,
            CasePhase.CLOSED.value: ReviewCaseStatus.COMPLETED,
        }
        return tuple(
            ReviewCaseLink(
                review_case_id=str(item["case_id"]),
                status=statuses.get(item["phase"], ReviewCaseStatus.IN_PROGRESS),
            )
            for item in (_row_dict(self._db, row) for row in rows)
        )

    def link_review_case(self, case_id: str, *, review_of_case_id: str) -> None:
        """Additive linkage written inside the same transaction as the new case."""
        self._require_active()
        self._db._execute(
            self._conn,
            "UPDATE cases SET review_of_case_id = %s WHERE case_id = %s",
            (review_of_case_id, case_id),
        )

    def require_entities(self, entity_ids: tuple[str, ...]) -> None:
        """Fail closed on an unknown correction target before any insert runs."""
        self._require_active()
        if type(entity_ids) is not tuple or not all(
            type(entity_id) is str and entity_id for entity_id in entity_ids
        ):
            raise ValueError("invalid_entity_reference")
        for entity_id in sorted(set(entity_ids)):
            row = self._db._fetchone(
                self._conn,
                # KEY SHARE is the lock the foreign key would take at insert
                # time; taking it now stops a concurrent delete from turning
                # this guard into a driver error later in the transaction.
                "SELECT id FROM entities WHERE id = %s FOR KEY SHARE",
                (entity_id,),
            )
            if row is None:
                raise CaseNotFound(entity_id)

    def claim_idempotency(self, key: str, *, now: datetime) -> dict | None:
        """Serialize one operation key inside this transaction and read its row."""
        self._require_active()
        if type(key) is not str or not key or type(now) is not datetime or now.tzinfo is None:
            raise ValueError("invalid_idempotency_claim")
        self._db._fetchone(
            self._conn, "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,)
        )
        row = self._db._fetchone(
            self._conn,
            """
            SELECT actor_ref, request_digest, response_enc, response_key_version, expires_at
            FROM case_idempotency WHERE idempotency_key = %s FOR UPDATE
            """,
            (key,),
        )
        return None if row is None else dict(_row_dict(self._db, row))

    def record_idempotency(
        self, key: str, *, actor_ref: str, request_digest: str, response_enc: str,
        now: datetime, ttl_hours: int = 24,
    ) -> None:
        self._require_active()
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_idempotency (
                idempotency_key, actor_ref, request_digest, response_enc,
                response_key_version, expires_at, created_at
            ) VALUES (%s, %s, %s, %s, 'v1', %s, %s)
            """,
            (key, actor_ref, request_digest, response_enc, now + timedelta(hours=ttl_hours), now),
        )

    def load_case(self, case_id: str, *, for_update: bool = False) -> CaseSnapshot:
        self._require_active()
        lock = " FOR UPDATE" if for_update else ""
        row = self._db._fetchone(
            self._conn,
            f"SELECT {_CASE_COLUMNS} FROM cases WHERE case_id = %s{lock}",
            (case_id,),
        )
        if row is None:
            raise CaseNotFound(case_id)
        return _snapshot_from_row(self._db, self._conn, row)

    def update_case(
        self, expected_revision: int, snapshot: CaseSnapshot
    ) -> CaseSnapshot:
        self._require_active()
        if (
            type(expected_revision) is not int
            or type(snapshot) is not CaseSnapshot
            or snapshot.current_revision != expected_revision + 1
        ):
            raise ValueError("invalid_case_update")
        row = self._db._fetchone(
            self._conn,
            f"""
            UPDATE cases SET
                service_kind = %s, category = %s, phase = %s, activity = %s,
                disposition_family = %s, domain_outcome = %s, severity = %s,
                reporter_privacy = %s, owner_ref = %s, current_revision = %s,
                promise_policy_ref = %s, updated_at = %s, closed_at = %s
            WHERE case_id = %s AND current_revision = %s
            RETURNING {_CASE_COLUMNS}
            """,
            (
                snapshot.service_kind.value,
                snapshot.category,
                snapshot.phase.value,
                snapshot.activity.value,
                snapshot.disposition_family.value,
                _enum_value(snapshot.domain_outcome),
                snapshot.severity,
                snapshot.reporter_privacy,
                snapshot.owner_ref,
                snapshot.current_revision,
                snapshot.promise_policy_ref,
                snapshot.updated_at,
                snapshot.closed_at,
                snapshot.case_id,
                expected_revision,
            ),
        )
        if row is None:
            try:
                current = self.load_case(snapshot.case_id)
            except CaseNotFound:
                raise CaseNotFound(snapshot.case_id) from None
            raise RevisionConflict(current)
        return _snapshot_from_row(self._db, self._conn, row)

    def issue_receipt(self, case_id, crypto, *, now, current_user_id=None, idempotency_key=None):
        """Issue a receipt on this transaction's connection (no intermediate commit)."""
        self._require_active()
        from .security import CaseSecurityError
        if idempotency_key is not None and (type(idempotency_key) is not str or not idempotency_key):
            raise CaseSecurityError("invalid_case_credential")
        self._db._fetchone(self._conn, "SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
        if idempotency_key:
            self._db._fetchone(self._conn, "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (idempotency_key,))
        revision = self._db._fetchone(self._conn, "SELECT COALESCE(MAX(receipt_revision), 0) + 1 AS revision FROM case_receipts WHERE case_id=%s", (case_id,))
        return PostgresCaseStore(self._db)._insert_receipt(self._conn, case_id, crypto, now=now, current_user_id=current_user_id, revision=int(_row_dict(self._db, revision)["revision"]))


class PostgresCaseStore:
    def __init__(self, database=None) -> None:
        if database is None:
            from database import db

            database = db
        self._db = database

    @contextmanager
    def transaction(self):
        if not self._db._use_pg:
            raise RuntimeError("case_postgresql_required")
        with self._db._conn(commit_on_success=False) as conn:
            transaction = CaseTransaction(self._db, conn)
            try:
                yield transaction
                conn.commit()
            finally:
                transaction._close()

    def _require_pg(self) -> None:
        if not self._db._use_pg:
            raise RuntimeError("case_postgresql_required")

    def peek_idempotency(self, key: str) -> dict | None:
        """Unlocked read on its own connection.

        Callers use this to recognise a lost-response retry before spending a
        rate slot. It is advisory only: the authoritative, locked claim still
        happens inside the case transaction, and nesting a second pooled
        connection inside that transaction could exhaust a small pool.
        """
        self._require_pg()
        if type(key) is not str or not key:
            raise ValueError("invalid_idempotency_claim")
        with self._db._conn(commit_on_success=False) as conn:
            row = self._db._fetchone(
                conn,
                """
                SELECT actor_ref, request_digest, response_enc, response_key_version,
                       expires_at
                FROM case_idempotency WHERE idempotency_key = %s
                """,
                (key,),
            )
            return None if row is None else dict(_row_dict(self._db, row))

    def _insert_receipt(self, conn, case_id, crypto, *, now, current_user_id, revision):
        from .security import ReceiptGrant

        expires_at = now + timedelta(days=365)
        for attempt in range(4):
            reference = crypto.issue_public_reference()
            capability = crypto.issue_capability()
            digest = crypto.digest_capability(capability)
            try:
                savepoint = f"receipt_attempt_{attempt}"
                self._db._execute(conn, f"SAVEPOINT {savepoint}", ())
                row = self._db._fetchone(conn, """
                    INSERT INTO case_receipts(case_id, public_reference, capability_digest,
                        capability_key_version, receipt_revision, subject_user_id, expires_at, created_at)
                    VALUES (%s, %s, %s, 'v1', %s, %s, %s, %s)
                    RETURNING receipt_id
                """, (case_id, reference, digest, revision, current_user_id, expires_at, now))
                self._db._execute(conn, f"RELEASE SAVEPOINT {savepoint}", ())
                return ReceiptGrant(str(_row_dict(self._db, row)["receipt_id"]), case_id, reference, capability, expires_at, revision, current_user_id)
            except Exception as exc:
                self._db._execute(conn, f"ROLLBACK TO SAVEPOINT {savepoint}", ())
                self._db._execute(conn, f"RELEASE SAVEPOINT {savepoint}", ())
                if attempt == 3 or not self._is_expected_receipt_collision(exc):
                    raise
        raise RuntimeError("case_receipt_collision")

    @staticmethod
    def _is_expected_receipt_collision(exc) -> bool:
        """Retry only PostgreSQL uniqueness collisions on the two random secrets."""
        if getattr(exc, "pgcode", None) != "23505":
            return False
        constraint = getattr(getattr(exc, "diag", None), "constraint_name", None)
        return constraint in {
            "case_receipts_public_reference_key",
            "case_receipts_capability_digest_key",
        }

    def _replay_request_digest(self, crypto, case_id, current_user_id, idempotency_key):
        return crypto.digest_capability(f"issue:{case_id}:{current_user_id or 'anonymous'}:{idempotency_key}")

    def issue_receipt(self, case_id, crypto, *, now, current_user_id=None, idempotency_key=None):
        """Persist only a capability digest; the caller receives the raw value once."""
        from .security import CaseSecurityError, ReceiptGrant

        self._require_pg()
        if idempotency_key is not None and (type(idempotency_key) is not str or not idempotency_key):
            raise CaseSecurityError("invalid_case_credential")
        with self._db._conn(commit_on_success=False) as conn:
            self._db._fetchone(conn, "SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
            if idempotency_key:
                # Serialize reuse of the same operation key, including when the
                # competing requests target different case rows.
                self._db._fetchone(conn, "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (idempotency_key,))
                actor_ref = current_user_id or "anonymous"
                request_digest = self._replay_request_digest(crypto, case_id, current_user_id, idempotency_key)
                self._db._execute(conn, "DELETE FROM case_idempotency WHERE idempotency_key=%s AND expires_at<=%s", (idempotency_key, now))
                replay = self._db._fetchone(conn, "SELECT actor_ref, request_digest, response_enc, response_key_version FROM case_idempotency WHERE idempotency_key=%s FOR UPDATE", (idempotency_key,))
                if replay is not None:
                    item = _row_dict(self._db, replay)
                    if not hmac.compare_digest(str(item["actor_ref"]), actor_ref) or item["response_key_version"] != "v1" or not hmac.compare_digest(str(item["request_digest"]), request_digest):
                        raise CaseSecurityError("invalid_case_credential")
                    payload = crypto.decrypt_replay(str(item["response_enc"]), now=now)
                    return ReceiptGrant(payload["receipt_id"], case_id, payload["public_reference"], payload["capability"], datetime.fromisoformat(payload["expires_at"]), int(payload["revision"]), current_user_id)
            revision_row = self._db._fetchone(conn, "SELECT COALESCE(MAX(receipt_revision), 0) + 1 AS revision FROM case_receipts WHERE case_id=%s", (case_id,))
            grant = self._insert_receipt(conn, case_id, crypto, now=now, current_user_id=current_user_id, revision=int(_row_dict(self._db, revision_row)["revision"]))
            if idempotency_key:
                payload = {"receipt_id": grant.receipt_id, "public_reference": grant.public_reference, "capability": grant.capability, "expires_at": grant.expires_at.isoformat(), "revision": grant.revision}
                self._db._execute(conn, "INSERT INTO case_idempotency(idempotency_key, actor_ref, request_digest, response_enc, response_key_version, expires_at, created_at) VALUES (%s,%s,%s,%s,'v1',%s,%s)", (idempotency_key, actor_ref, request_digest, crypto.encrypt_replay(payload, now=now), now + timedelta(hours=24), now))
            conn.commit()
        return grant

    def exchange_receipt(self, public_reference, capability, crypto, *, now, current_user_id=None):
        from .security import AccessGrant, CaseSecurityError

        self._require_pg()
        if not crypto.validate_public_reference(public_reference):
            raise CaseSecurityError("invalid_case_credential")
        digest = crypto.digest_capability(capability)
        with self._db._conn(commit_on_success=False) as conn:
            row = self._db._fetchone(conn, """
                SELECT receipt_id, case_id, receipt_revision, subject_user_id, capability_digest FROM case_receipts
                WHERE public_reference=%s AND revoked_at IS NULL AND expires_at > %s
                FOR UPDATE
            """, (public_reference, now))
            if row is None:
                raise CaseSecurityError("invalid_case_credential")
            receipt = _row_dict(self._db, row)
            if not hmac.compare_digest(str(receipt["capability_digest"]), digest):
                raise CaseSecurityError("invalid_case_credential")
            if receipt["subject_user_id"] is not None and not hmac.compare_digest(str(receipt["subject_user_id"]), current_user_id or ""):
                raise CaseSecurityError("invalid_case_credential")
            token = crypto.issue_capability()
            session_digest = crypto.digest_capability(token)
            self._db._execute(conn, """
                INSERT INTO case_access_sessions(case_id, receipt_id, session_digest, session_key_version, expires_at, created_at)
                VALUES (%s, %s, %s, 'v1', %s, %s)
            """, (receipt["case_id"], receipt["receipt_id"], session_digest, now + timedelta(minutes=15), now))
            conn.commit()
        access = crypto.make_access(str(receipt["case_id"]), str(receipt["receipt_id"]), int(receipt["receipt_revision"]), session_digest, current_user_id)
        return AccessGrant(token, access)

    def validate_access(self, token, crypto, *, now, current_user_id=None):
        from .security import CaseSecurityError

        self._require_pg()
        digest = crypto.digest_capability(token)
        with self._db._conn(commit_on_success=False) as conn:
            row = self._db._fetchone(conn, """
                SELECT s.case_id, s.receipt_id, s.session_digest, s.session_key_version, r.receipt_revision, r.subject_user_id
                FROM case_access_sessions s JOIN case_receipts r ON r.receipt_id=s.receipt_id
                WHERE s.session_digest = %s AND s.case_id = r.case_id
                  AND s.revoked_at IS NULL AND s.expires_at > %s
                  AND r.revoked_at IS NULL AND r.expires_at > %s AND s.session_key_version = 'v1'
            """, (digest, now, now))
        if row is None:
            raise CaseSecurityError("invalid_case_credential")
        item = _row_dict(self._db, row)
        if not hmac.compare_digest(str(item["session_digest"]), digest):
            raise CaseSecurityError("invalid_case_credential")
        if item["subject_user_id"] is not None and not hmac.compare_digest(str(item["subject_user_id"]), current_user_id or ""):
            raise CaseSecurityError("invalid_case_credential")
        return crypto.make_access(str(item["case_id"]), str(item["receipt_id"]), int(item["receipt_revision"]), str(item["session_digest"]), current_user_id)

    def revoke_access(self, case_id, *, now):
        self._require_pg()
        with self._db._conn(commit_on_success=False) as conn:
            locked = self._db._fetchone(conn, "SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,))
            if locked is None:
                from .security import CaseSecurityError
                raise CaseSecurityError("invalid_case_credential")
            # Every mutating path locks case -> receipts -> sessions in this order.
            self._db._fetchall(conn, "SELECT receipt_id FROM case_receipts WHERE case_id=%s ORDER BY receipt_id FOR UPDATE", (case_id,))
            self._db._fetchall(conn, "SELECT access_session_id FROM case_access_sessions WHERE case_id=%s ORDER BY access_session_id FOR UPDATE", (case_id,))
            self._db._execute(conn, "UPDATE case_receipts SET revoked_at=%s WHERE case_id=%s AND revoked_at IS NULL", (now, case_id))
            self._db._execute(conn, "UPDATE case_access_sessions SET revoked_at=%s WHERE case_id=%s AND revoked_at IS NULL", (now, case_id))
            conn.commit()

    def rotate_receipt(self, access_token, crypto, *, now, current_user_id=None, idempotency_key=None):
        from .security import CaseSecurityError, ReceiptGrant

        self._require_pg()
        digest = crypto.digest_capability(access_token)
        with self._db._conn(commit_on_success=False) as conn:
            rotation_key = f"rotate:{idempotency_key}" if idempotency_key else None
            actor_ref = current_user_id or "anonymous"
            bearer = self._db._fetchone(conn, """
                SELECT s.case_id, s.receipt_id, s.session_digest, s.session_key_version,
                       s.revoked_at AS session_revoked_at, s.expires_at AS session_expires_at,
                       r.receipt_revision, r.subject_user_id,
                       r.revoked_at AS receipt_revoked_at, r.expires_at AS receipt_expires_at
                FROM case_access_sessions s
                JOIN case_receipts r ON r.receipt_id=s.receipt_id AND r.case_id=s.case_id
                WHERE s.session_digest=%s
            """, (digest,))
            if bearer is None:
                raise CaseSecurityError("invalid_case_credential")
            bearer = _row_dict(self._db, bearer)
            case_id = str(bearer["case_id"])
            rotation_digest = crypto.digest_capability(
                f"{rotation_key}:{case_id}:{digest}:{actor_ref}"
            ) if rotation_key else None
            if rotation_key:
                self._db._fetchone(conn, "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (rotation_key,))
                self._db._execute(conn, "DELETE FROM case_idempotency WHERE idempotency_key=%s AND expires_at<=%s", (rotation_key, now))
            # Lock rows in the same deterministic order as revoke_access.
            if self._db._fetchone(conn, "SELECT case_id FROM cases WHERE case_id=%s FOR UPDATE", (case_id,)) is None:
                raise CaseSecurityError("invalid_case_credential")
            self._db._fetchall(conn, "SELECT receipt_id FROM case_receipts WHERE case_id=%s ORDER BY receipt_id FOR UPDATE", (case_id,))
            self._db._fetchall(conn, "SELECT access_session_id FROM case_access_sessions WHERE case_id=%s ORDER BY access_session_id FOR UPDATE", (case_id,))
            replay = self._db._fetchone(conn, "SELECT actor_ref, request_digest, response_enc, response_key_version FROM case_idempotency WHERE idempotency_key=%s FOR UPDATE", (rotation_key,)) if rotation_key else None
            if replay is not None:
                item = _row_dict(self._db, replay)
                if item["response_key_version"] != "v1" or not hmac.compare_digest(str(item["actor_ref"]), actor_ref) or not hmac.compare_digest(str(item["request_digest"]), rotation_digest):
                    raise CaseSecurityError("invalid_case_credential")
                if bearer["session_key_version"] != "v1" or bearer["subject_user_id"] is not None and not hmac.compare_digest(str(bearer["subject_user_id"]), actor_ref):
                    raise CaseSecurityError("invalid_case_credential")
                payload = crypto.decrypt_replay(str(item["response_enc"]), now=now)
                if str(payload.get("case_id")) != case_id:
                    raise CaseSecurityError("invalid_case_credential")
                return ReceiptGrant(payload["receipt_id"], payload["case_id"], payload["public_reference"], payload["capability"], datetime.fromisoformat(payload["expires_at"]), int(payload["revision"]), current_user_id)
            if bearer["session_key_version"] != "v1" or bearer["session_revoked_at"] is not None or bearer["session_expires_at"] <= now or bearer["receipt_revoked_at"] is not None or bearer["receipt_expires_at"] <= now:
                raise CaseSecurityError("invalid_case_credential")
            if bearer["subject_user_id"] is not None and not hmac.compare_digest(str(bearer["subject_user_id"]), current_user_id or ""):
                raise CaseSecurityError("invalid_case_credential")
            updated = self._db._fetchone(conn, "UPDATE case_receipts SET revoked_at=%s WHERE receipt_id=%s AND revoked_at IS NULL RETURNING receipt_id", (now, bearer["receipt_id"]))
            if updated is None:
                raise CaseSecurityError("invalid_case_credential")
            self._db._execute(conn, "UPDATE case_access_sessions SET revoked_at=%s WHERE receipt_id=%s AND revoked_at IS NULL", (now, bearer["receipt_id"]))
            row = self._db._fetchone(conn, "SELECT COALESCE(MAX(receipt_revision), 0) + 1 AS revision FROM case_receipts WHERE case_id=%s", (case_id,))
            grant = self._insert_receipt(conn, case_id, crypto, now=now, current_user_id=current_user_id, revision=int(_row_dict(self._db, row)["revision"]))
            if rotation_key:
                payload = {"receipt_id": grant.receipt_id, "case_id": grant.case_id, "public_reference": grant.public_reference, "capability": grant.capability, "expires_at": grant.expires_at.isoformat(), "revision": grant.revision}
                self._db._execute(conn, "INSERT INTO case_idempotency(idempotency_key, actor_ref, request_digest, response_enc, response_key_version, expires_at, created_at) VALUES (%s,%s,%s,%s,'v1',%s,%s)", (rotation_key, actor_ref, rotation_digest, crypto.encrypt_replay(payload, now=now), now + timedelta(hours=24), now))
            conn.commit()
        return grant
