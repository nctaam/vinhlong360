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
    AT_RISK_FRACTION,
    LIVE_PROMISE_KINDS,
    CaseActivity,
    CasePhase,
    CaseSnapshot,
    Channel,
    CorrectionItem,
    DispositionFamily,
    EvidenceLevel,
    PromiseClock,
    PromiseHealth,
    recorded_health,
    PublicationState,
    ReviewCaseLink,
    ReviewCaseStatus,
    RiskClass,
    ServiceKind,
)
from .queue_policy import WorkItemDraft
from .transitions import TransitionDraft

import entity_write as _entity_write


class CaseNotFound(LookupError):
    pass


class ChangeSetNotFound(LookupError):
    pass


class ChangeSetStateConflict(RuntimeError):
    """Somebody else moved this change set between the read and the write."""


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


def _publication_state(item: Mapping) -> PublicationState:
    """What the reporter is owed, and how far it has got.

    Derived rather than stored: the change set is the only record of a promised
    public change, so reading it here cannot drift from what actually happened.
    """
    status = item.get("apply_status")
    if not status:
        return PublicationState.NOT_REQUIRED
    if status == "pending":
        return PublicationState.PENDING
    if status == "rolled_back":
        return PublicationState.ROLLED_BACK
    if status == "applied":
        # Applied says we wrote it. Verified says somebody checked the page.
        return (
            PublicationState.VERIFIED
            if item.get("public_projection_verified_at")
            else PublicationState.APPLIED
        )
    return PublicationState.NOT_REQUIRED


def _snapshot_from_row(database, conn, row) -> CaseSnapshot:
    item = _row_dict(database, row)
    clocks = _promise_clocks(database, conn, str(item["case_id"]))
    health = recorded_health(clocks)
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
        if draft.waiting is not None:
            from . import metrics as _metrics

            # Observed at append time. Metrics are operational evidence, not a
            # ledger: a rolled-back transition may leave one stray waiting event,
            # which is noise the 28-day window tolerates and audit does not use.
            _metrics.observe("waiting", channel="web", case_id=draft.case_id,
                             now=draft.occurred_at)
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
        if draft.event_id is not None:
            envelope = {
                "event_id": draft.event_id,
                "resource_id": draft.resource_id or draft.case_id,
                "revision": draft.revision,
                "generation": draft.generation,
                "correlation_id": draft.correlation_id,
            }
            # The existing JSONB snapshot is the schema-compatible durable
            # descriptor for audit metadata; no production migration is needed.
            target = after_snapshot if after_snapshot is not None else before_snapshot
            encoded = json.loads(target) if target is not None else {}
            encoded["_audit_event"] = envelope
            serialized = json.dumps(encoded, sort_keys=True, allow_nan=False)
            if after_snapshot is not None:
                after_snapshot = serialized
            else:
                before_snapshot = serialized
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
            SELECT i.item_id, i.entity_id, i.field_path, i.base_entity_revision,
                   i.risk_class, i.evidence_level,
                   cs.apply_status, cs.public_projection_verified_at,
                   d.outcome_code
            FROM correction_items i
            -- The ruling, so the reporter's page can say more than "đang xem
            -- xét" once one exists. Latest per item: a review may re-rule.
            LEFT JOIN LATERAL (
                SELECT outcome_code FROM case_decisions
                WHERE item_id = i.item_id
                ORDER BY decided_at DESC LIMIT 1
            ) d ON TRUE
            -- The item owes a public change only through a change set, and its
            -- latest one is what the reporter is currently being told about.
            LEFT JOIN LATERAL (
                SELECT c.apply_status, c.public_projection_verified_at
                FROM correction_change_set_items link
                JOIN correction_change_sets c ON c.change_set_id = link.change_set_id
                WHERE link.item_id = i.item_id
                ORDER BY c.created_at DESC LIMIT 1
            ) cs ON TRUE
            WHERE i.case_id = %s ORDER BY i.created_at, i.item_id
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
                accepted=item.get("outcome_code") == "corrected",
                # The ruling itself, not just whether it happened to be "yes":
                # the public status derives its answer from this.
                outcome_code=item.get("outcome_code"),
                publication_state=_publication_state(item),
            )
            for item in (_row_dict(self._db, row) for row in rows)
        )

    def load_correction_evidence(self, case_id: str, item_id: str | None = None) -> tuple:
        """Descriptors only. The private payload stays in its encrypted column."""
        self._require_active()
        sql = """
            SELECT evidence_id, case_id, item_id, evidence_level, source_ref,
                   descriptor, created_by_ref, created_at
            FROM correction_evidence WHERE case_id = %s
        """
        params = (case_id,)
        if item_id is not None:
            sql += " AND item_id = %s"
            params = (case_id, item_id)
        rows = self._db._fetchall(self._conn, sql + " ORDER BY created_at, evidence_id", params)
        return tuple(_row_dict(self._db, row) for row in rows)

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

    def actor_holds_lease(self, case_id: str, actor_ref: str, *, now: datetime) -> bool:
        """A decision is only allowed while its author is actually holding the work."""
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            SELECT 1 FROM case_work_items
            WHERE case_id = %s AND assignee_ref = %s AND status = 'claimed'
              AND lease_expires_at > %s
            LIMIT 1
            """,
            (case_id, actor_ref, now),
        )
        return row is not None

    def load_correction_item_payloads(
        self, case_id: str, item_ids: tuple[str, ...]
    ) -> tuple[dict, ...]:
        """The ciphertext-bearing read, used only to build a change set.

        Deliberately separate from `load_correction_items`, which feeds the
        public projection and must never select an encrypted value.
        """
        self._require_active()
        if type(item_ids) is not tuple or not item_ids:
            raise ValueError("invalid_correction_item_selection")
        rows = self._db._fetchall(
            self._conn,
            """
            SELECT i.item_id, i.entity_id, i.field_path, i.reported_value_enc,
                   i.proposed_value_enc, i.base_entity_revision, i.risk_class,
                   d.outcome_code
            FROM correction_items i
            -- The ruling that entitles this item to be published at all. Latest
            -- per item: a review may re-rule, and the newest ruling governs.
            LEFT JOIN LATERAL (
                SELECT outcome_code FROM case_decisions
                WHERE item_id = i.item_id
                ORDER BY decided_at DESC LIMIT 1
            ) d ON TRUE
            WHERE i.case_id = %s AND i.item_id = ANY(%s::uuid[])
            ORDER BY i.created_at, i.item_id
            """,
            (case_id, list(item_ids)),
        )
        return tuple(dict(_row_dict(self._db, row)) for row in rows)

    def entity_revision(self, entity_id: str) -> int | None:
        self._require_active()
        row = self._db._fetchone(
            self._conn, "SELECT revision FROM entities WHERE id = %s", (entity_id,)
        )
        return None if row is None else int(_row_dict(self._db, row)["revision"])

    def insert_decision(
        self, *, case_id: str, item_id: str | None, outcome_code: str, reason_code: str,
        evidence_refs: tuple[str, ...], decision_maker_ref: str, reviewer_ref: str | None,
        policy_revision: str, decided_at: datetime,
    ) -> str:
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            INSERT INTO case_decisions (
                case_id, item_id, outcome_code, reason_code, evidence_refs,
                decision_maker_ref, reviewer_ref, policy_revision, decided_at
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
            RETURNING decision_id
            """,
            (
                case_id, item_id, outcome_code, reason_code,
                json.dumps(list(evidence_refs), separators=(",", ":")),
                decision_maker_ref, reviewer_ref, policy_revision, decided_at,
            ),
        )
        return str(_row_dict(self._db, row)["decision_id"])

    def insert_change_set(
        self, *, case_id: str, base_entity_revision: int, before_patch: dict,
        after_patch: dict, inverse_patch: dict, evidence_refs: tuple[str, ...],
        policy_revision: str, risk_class: str, decision_maker_ref: str,
        reviewer_ref: str | None, created_at: datetime,
    ) -> str:
        """Always inserted `pending`; publication is a separate, later decision."""
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            INSERT INTO correction_change_sets (
                case_id, base_entity_revision, before_patch, after_patch, inverse_patch,
                evidence_refs, policy_revision, risk_class, decision_maker_ref,
                reviewer_ref, apply_status, created_at
            ) VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s,
                      'pending', %s)
            RETURNING change_set_id
            """,
            (
                case_id, base_entity_revision,
                json.dumps(before_patch, sort_keys=True, separators=(",", ":")),
                json.dumps(after_patch, sort_keys=True, separators=(",", ":")),
                json.dumps(inverse_patch, sort_keys=True, separators=(",", ":")),
                json.dumps(list(evidence_refs), separators=(",", ":")),
                policy_revision, risk_class, decision_maker_ref, reviewer_ref, created_at,
            ),
        )
        return str(_row_dict(self._db, row)["change_set_id"])

    def load_change_set(self, change_set_id: str, *, for_update: bool = False) -> dict:
        self._require_active()
        lock = " FOR UPDATE" if for_update else ""
        row = self._db._fetchone(
            self._conn,
            f"""
            SELECT change_set_id, case_id, base_entity_revision, before_patch, after_patch,
                   inverse_patch, policy_revision, risk_class, decision_maker_ref,
                   reviewer_ref, apply_status, public_projection_verified_at
            FROM correction_change_sets WHERE change_set_id = %s{lock}
            """,
            (change_set_id,),
        )
        if row is None:
            raise ChangeSetNotFound(change_set_id)
        return _row_dict(self._db, row)

    def load_change_set_target(self, change_set_id: str) -> tuple[str, tuple[str, ...]]:
        """The one entry a change set touches, and the items that asked for it."""
        self._require_active()
        rows = self._db._fetchall(
            self._conn,
            """
            SELECT i.item_id, i.entity_id
            FROM correction_change_set_items link
            JOIN correction_items i ON i.item_id = link.item_id
            WHERE link.change_set_id = %s ORDER BY i.created_at, i.item_id
            """,
            (change_set_id,),
        )
        items = tuple(_row_dict(self._db, row) for row in rows)
        entity_ids = {str(item["entity_id"]) for item in items}
        if len(entity_ids) != 1:
            # Task 10 refuses to build such a set; reaching here means the rows drifted.
            raise ValueError("change_set_spans_entities")
        return entity_ids.pop(), tuple(str(item["item_id"]) for item in items)

    def latest_change_set_for_case(self, case_id: str) -> dict | None:
        """The change set the workbench acts on: newest first, safe fields only."""
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            SELECT change_set_id, apply_status, risk_class, base_entity_revision
            FROM correction_change_sets WHERE case_id = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (case_id,),
        )
        return None if row is None else _row_dict(self._db, row)

    def set_change_set_apply_status(
        self, change_set_id: str, *, expected_status: str, status: str,
        verified_at: datetime | None = None,
    ) -> None:
        """Compare-and-set: two publishers cannot both believe they applied this."""
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            UPDATE correction_change_sets
            SET apply_status = %s,
                public_projection_verified_at = COALESCE(%s, public_projection_verified_at)
            WHERE change_set_id = %s AND apply_status = %s
            RETURNING change_set_id
            """,
            (status, verified_at, change_set_id, expected_status),
        )
        if row is None:
            raise ChangeSetStateConflict(change_set_id)

    def grant_admin_access(self, *, case_id: str, actor_ref: str, scope: str,
                           session_digest: str, expires_at: datetime) -> None:
        """A short-lived clearance to read what somebody actually reported.

        Only the digest is stored. The operator holds the secret for as long as
        the grant lasts, and a database copy could not be used to impersonate it.
        """
        self._require_active()
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_admin_access_sessions
                (case_id, actor_ref, scope, session_digest, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (case_id, actor_ref, scope, session_digest, expires_at),
        )

    def revoke_admin_access(self, *, case_id: str, actor_ref: str, now: datetime) -> None:
        self._require_active()
        self._db._execute(
            self._conn,
            """
            UPDATE case_admin_access_sessions SET revoked_at = %s
            WHERE case_id = %s AND actor_ref = %s AND revoked_at IS NULL
            """,
            (now, case_id, actor_ref),
        )

    def admin_access_is_live(self, *, case_id: str, actor_ref: str, scope: str,
                             session_digest: str, now: datetime) -> bool:
        """Every condition in one query: right case, right person, unexpired, unrevoked."""
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            SELECT 1 FROM case_admin_access_sessions
            WHERE case_id = %s AND actor_ref = %s AND scope = %s AND session_digest = %s
              AND revoked_at IS NULL AND expires_at > %s
            LIMIT 1
            """,
            (case_id, actor_ref, scope, session_digest, now),
        )
        return row is not None

    def record_legacy_intake(self, *, source_file: str, source_line: int,
                             raw_record_digest: str, legacy_status, mapping_decision: str,
                             import_result: str, missing_data_flags, imported_at,
                             imported_case_id=None) -> None:
        """One ledger row per source line; replaying the same line is a no-op.

        ON CONFLICT DO NOTHING on the (source_file, source_line) key is what
        makes a re-run idempotent instead of a second import.
        """
        self._require_active()
        self._db._execute(
            self._conn,
            """
            INSERT INTO legacy_intake_records
                (source_file, source_line, raw_record_digest, imported_case_id,
                 legacy_status, missing_data_flags, mapping_decision, import_result,
                 imported_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            ON CONFLICT (source_file, source_line) DO NOTHING
            """,
            (source_file, source_line, raw_record_digest, imported_case_id,
             legacy_status, json.dumps(list(missing_data_flags or [])),
             mapping_decision, import_result, imported_at),
        )

    def legacy_intake_summary(self, source_file: str) -> dict:
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            """
            SELECT count(*) AS rows,
                   count(*) FILTER (WHERE import_result = 'correction') AS corrections,
                   count(*) FILTER (WHERE import_result = 'duplicate') AS duplicates,
                   count(*) FILTER (WHERE import_result NOT IN
                       ('correction','moderation_link','manual_triage','rejected','duplicate')
                   ) AS unexplained
            FROM legacy_intake_records WHERE source_file = %s
            """,
            (source_file,),
        )
        item = _row_dict(self._db, row)
        return {key: int(item[key] or 0) for key in
                ("rows", "corrections", "duplicates", "unexplained")}

    def legacy_freeze_present(self, freeze_source: str) -> bool:
        self._require_active()
        return self._db._fetchone(
            self._conn,
            "SELECT 1 FROM legacy_intake_records WHERE source_file = %s"
            " AND import_result = 'freeze' LIMIT 1",
            (freeze_source,),
        ) is not None

    # ── Capacity evidence (Task 18) ──

    def record_capacity_event(self, *, kind: str, channel: str, risk_class,
                              case_id, duration_seconds, metadata: dict,
                              observed_at: datetime) -> None:
        self._require_active()
        self._db._execute(
            self._conn,
            """
            INSERT INTO case_capacity_events
                (case_id, channel, risk_class, event_kind, observed_at,
                 duration_seconds, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (case_id, channel, risk_class, kind, observed_at,
             duration_seconds, json.dumps(metadata)),
        )

    def capacity_daily_counts(self, start_day, end_day) -> list[dict]:
        """One row per UTC day that has any events; the caller finds the gaps."""
        self._require_active()
        rows = self._db._fetchall(
            self._conn,
            """
            SELECT (observed_at AT TIME ZONE 'UTC')::date AS day,
                   COALESCE(risk_class, 'none') AS risk_class, channel,
                   count(*) FILTER (WHERE event_kind = 'received') AS arrivals,
                   count(*) FILTER (WHERE event_kind = 'completed') AS completions,
                   count(*) AS events
            FROM case_capacity_events
            WHERE (observed_at AT TIME ZONE 'UTC')::date BETWEEN %s AND %s
            GROUP BY 1, 2, 3 ORDER BY 1
            """,
            (start_day, end_day),
        )
        days: dict = {}
        for row in rows:
            item = _row_dict(self._db, row)
            entry = days.setdefault(item["day"], {
                "day": item["day"], "arrivals": 0, "completions": 0,
                "by_risk": {}, "by_channel": {},
            })
            entry["arrivals"] += int(item["arrivals"] or 0)
            entry["completions"] += int(item["completions"] or 0)
            events = int(item["events"] or 0)
            risk = str(item["risk_class"])
            channel = str(item["channel"])
            entry["by_risk"][risk] = entry["by_risk"].get(risk, 0) + events
            entry["by_channel"][channel] = entry["by_channel"].get(channel, 0) + events
        return [days[key] for key in sorted(days)]

    # ── Retention (Task 18) ──

    def _count_execute(self, sql: str, params: tuple) -> int:
        cursor = self._db._execute(self._conn, sql, params)
        return int(getattr(cursor, "rowcount", 0) or 0)

    def purge_expired_access_sessions(self, *, now: datetime) -> int:
        self._require_active()
        return self._count_execute(
            "DELETE FROM case_access_sessions WHERE expires_at < %s", (now,)
        )

    def purge_expired_idempotency(self, *, now: datetime) -> int:
        self._require_active()
        return self._count_execute(
            "DELETE FROM case_idempotency WHERE expires_at < %s", (now,)
        )

    def purge_expired_contact_challenges(self, *, now: datetime) -> int:
        """Unanswered one-time codes only.

        expires_at is the code's ten-minute window, and verifying does not move
        it. Sweeping on that column alone deleted the VERIFIED row ten minutes
        after somebody consented — and that row is the only thing
        contact.verified_contact_for reads, so every message they had agreed to
        receive was suppressed from then on, silently. A verified challenge is
        the consent record; it retires with the address it belongs to.
        """
        self._require_active()
        return self._count_execute(
            "DELETE FROM case_contact_challenges"
            " WHERE expires_at < %s AND verified_at IS NULL",
            (now,),
        )

    def purge_consent_records(self, *, closed_before: datetime) -> int:
        """The verified challenge, retiring with the address it authorised.

        Same shelf as redact_closed_case_contacts: once the reply address is
        gone there is nothing left for the consent to authorise, and holding a
        contact digest past that point holds a person's phone number in a form
        we promised to let go.
        """
        self._require_active()
        return self._count_execute(
            """
            DELETE FROM case_contact_challenges
            WHERE verified_at IS NOT NULL
              AND case_id IN (
                  SELECT case_id FROM cases
                  WHERE closed_at IS NOT NULL AND closed_at < %s
              )
            """,
            (closed_before,),
        )

    def redact_closed_case_contacts(self, *, closed_before: datetime) -> int:
        """The optional reply address, 90 days after a terminal close.

        The interaction row stays — that a contact once existed is part of the
        lineage; the address itself is what stops being ours to hold.
        """
        self._require_active()
        return self._count_execute(
            """
            UPDATE case_interactions SET payload_enc = NULL
            WHERE payload_enc IS NOT NULL
              AND case_id IN (
                  SELECT case_id FROM cases
                  WHERE closed_at IS NOT NULL AND closed_at < %s
              )
            """,
            (closed_before,),
        )

    def redact_private_payloads(self, *, closed_before: datetime,
                                excluded_case_ids: tuple) -> tuple[int, tuple]:
        """Encrypted evidence and values, 365 days on — unless a hold is named."""
        self._require_active()
        exclusion = ""
        params: tuple = (closed_before,)
        if excluded_case_ids:
            exclusion = " AND case_id != ALL(%s::uuid[])"
            params = (closed_before, list(excluded_case_ids))
        eligible = (
            "SELECT case_id FROM cases WHERE closed_at IS NOT NULL"
            " AND closed_at < %s" + exclusion
        )
        count = self._count_execute(
            f"UPDATE correction_evidence SET content_enc = NULL"
            f" WHERE content_enc IS NOT NULL AND case_id IN ({eligible})",
            params,
        )
        count += self._count_execute(
            f"UPDATE correction_items SET reported_value_enc = NULL,"
            f" proposed_value_enc = NULL"
            f" WHERE (reported_value_enc IS NOT NULL OR proposed_value_enc IS NOT NULL)"
            f" AND case_id IN ({eligible})",
            params,
        )
        return count, tuple(excluded_case_ids)

    def deidentify_capacity_events(self, *, observed_before: datetime) -> int:
        """After 730 days the numbers stay and the case linkage goes."""
        self._require_active()
        return self._count_execute(
            "UPDATE case_capacity_events SET case_id = NULL"
            " WHERE case_id IS NOT NULL AND observed_at < %s",
            (observed_before,),
        )

    def open_case_clocks(self, *, now: datetime, limit: int = 500):
        """Every unclosed case with its clocks, for the one job that reads them.

        Only cases whose stamped health could still be wrong are returned: an
        already-BREACHED case needs no restamping, and a case whose earliest
        due date is comfortably ahead is not at risk yet either.
        """
        self._require_active()
        rows = self._db._fetchall(
            self._conn,
            """
            SELECT DISTINCT c.case_id, c.updated_at
            FROM cases c
            JOIN case_promise_clocks k ON k.case_id = c.case_id
            WHERE c.closed_at IS NULL
              AND k.health <> 'breached'
              AND k.kind = ANY(%s)
              -- At risk OR overdue. Keying on due_at alone would have meant
              -- AT_RISK was still never written anywhere, which is half the
              -- bug this query exists to fix.
              AND k.started_at + (k.due_at - k.started_at) * %s <= %s
            ORDER BY c.updated_at
            LIMIT %s
            """,
            (sorted(LIVE_PROMISE_KINDS), AT_RISK_FRACTION, now, limit),
        )
        out = []
        for row in rows:
            case_id = str(_row_dict(self._db, row)["case_id"])
            clocks = _promise_clocks(self._db, self._conn, case_id)
            out.append((case_id, clocks, recorded_health(clocks)))
        return tuple(out)

    def set_promise_health(self, case_id: str, health: str, *, observed_at: datetime) -> None:
        self._require_active()
        self._db._execute(
            self._conn,
            "UPDATE case_promise_clocks SET health = %s, observed_at = %s WHERE case_id = %s",
            (health, observed_at, case_id),
        )

    def complete_work_item_of_kind(self, case_id: str, kind: str, *, now: datetime) -> None:
        """Close out the work this step was claimed for, on this transaction."""
        self._require_active()
        self._db._execute(
            self._conn,
            """
            UPDATE case_work_items
            SET status = 'completed', lease_expires_at = NULL, revision = revision + 1,
                next_review_at = %s
            WHERE case_id = %s AND kind = %s AND status <> 'completed'
            """,
            (now, case_id, kind),
        )

    def access_session_count(self, case_id: str) -> int:
        self._require_active()
        row = self._db._fetchone(
            self._conn,
            "SELECT count(*) AS n FROM case_access_sessions WHERE case_id = %s",
            (case_id,),
        )
        return int(_row_dict(self._db, row)["n"])

    def completed_work_assignees(self, case_id: str, kind: str) -> tuple:
        """Who finished this kind of work on the case — the R3 review proof."""
        self._require_active()
        rows = self._db._fetchall(
            self._conn,
            "SELECT assignee_ref FROM case_work_items"
            " WHERE case_id = %s AND kind = %s AND status = 'completed'",
            (case_id, kind),
        )
        return tuple(
            str(_row_dict(self._db, row)["assignee_ref"])
            for row in rows if _row_dict(self._db, row)["assignee_ref"]
        )

    def load_entity_for_update(self, entity_id: str):
        """Lock the live entry inside this transaction before deciding anything."""
        self._require_active()
        return _entity_write.EntityWriteService(self._db).load_for_update(self._conn, entity_id)

    def apply_entity_patch(self, entity_id: str, patch: dict, *, expected_revision: int,
                           actor: str, provenance: str):
        """The only door from a case to a live entry, and it opens on THIS transaction.

        Routing through the writer keeps the entity row, its change audit and every
        case record in one transaction, so a correction cannot be half-published.
        """
        self._require_active()
        writer = _entity_write.EntityWriteService(self._db)
        result = writer.apply_patch(
            self._conn, entity_id, patch, expected_revision=expected_revision,
            actor=actor, provenance=provenance,
        )
        writer.write_change_audit(self._conn, result, actor=actor, provenance=provenance)
        return result

    def link_change_set_items(self, change_set_id: str, item_ids: tuple[str, ...]) -> None:
        self._require_active()
        for item_id in item_ids:
            self._db._execute(
                self._conn,
                """
                INSERT INTO correction_change_set_items (change_set_id, item_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
                """,
                (change_set_id, item_id),
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

    @staticmethod
    def _require_live_rotation_bearer(bearer, *, now, current_user_id) -> None:
        """Every way the presented session can be dead, checked in one place."""
        from .security import CaseSecurityError

        if (
            bearer["session_key_version"] != "v1"
            or bearer["session_revoked_at"] is not None
            or bearer["session_expires_at"] <= now
            or bearer["receipt_revoked_at"] is not None
            or bearer["receipt_expires_at"] <= now
        ):
            raise CaseSecurityError("invalid_case_credential")
        if bearer["subject_user_id"] is not None and not hmac.compare_digest(
            str(bearer["subject_user_id"]), current_user_id or ""
        ):
            raise CaseSecurityError("invalid_case_credential")

    @staticmethod
    def _rotation_replay_grant(item, bearer, crypto, *, case_id, actor_ref,
                               rotation_digest, now, current_user_id):
        """Re-answer a rotation the same actor already performed — or refuse."""
        from .security import CaseSecurityError, ReceiptGrant

        if (
            item["response_key_version"] != "v1"
            or not hmac.compare_digest(str(item["actor_ref"]), actor_ref)
            or not hmac.compare_digest(str(item["request_digest"]), rotation_digest)
        ):
            raise CaseSecurityError("invalid_case_credential")
        if bearer["session_key_version"] != "v1" or (
            bearer["subject_user_id"] is not None
            and not hmac.compare_digest(str(bearer["subject_user_id"]), actor_ref)
        ):
            raise CaseSecurityError("invalid_case_credential")
        payload = crypto.decrypt_replay(str(item["response_enc"]), now=now)
        if str(payload.get("case_id")) != case_id:
            raise CaseSecurityError("invalid_case_credential")
        return ReceiptGrant(
            payload["receipt_id"], payload["case_id"], payload["public_reference"],
            payload["capability"], datetime.fromisoformat(payload["expires_at"]),
            int(payload["revision"]), current_user_id,
        )

    def rotate_receipt(self, access_token, crypto, *, now, current_user_id=None, idempotency_key=None):
        from .security import CaseSecurityError

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
                return self._rotation_replay_grant(
                    _row_dict(self._db, replay), bearer, crypto,
                    case_id=case_id, actor_ref=actor_ref,
                    rotation_digest=rotation_digest, now=now,
                    current_user_id=current_user_id,
                )
            self._require_live_rotation_bearer(bearer, now=now,
                                               current_user_id=current_user_id)
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
