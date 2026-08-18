"""Correction intake orchestration.

One public request becomes exactly one case, or nothing at all: validation and
safety routing run before any transaction opens, and the case, its interaction,
E0 evidence, items, clocks, first work item, transition, audit, receipt and
notification intent all commit together.
"""
from __future__ import annotations

import hmac
import json
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from .audit import CaseAuditDraft, safe_case_projection
from .domain import (
    CaseActivity,
    CasePhase,
    CaseProblem,
    CaseSnapshot,
    Channel,
    CommandEnvelope,
    DispositionFamily,
    EvidenceLevel,
    PromiseClock,
    PromiseHealth,
    RiskClass,
    ServiceKind,
)
from .queue_policy import WorkItemDraft
from .rate_limit import check_case_rate_limit, rate_subject_digest
from .store import (
    CaseNotFound,
    CaseInteractionDraft,
    CorrectionEvidenceDraft,
    CorrectionItemDraft,
    OutboxDraft,
    PartyAuthorityDraft,
)
from .transitions import TransitionDraft

# The pilot corrects published facts only. Promoting this table into
# config/case-service-policy.json would change a locked policy structure and
# needs a policy revision bump, so it stays an explicit code-level bound.
CORRECTABLE_FIELD_PATHS: dict[str, RiskClass] = {
    "name": RiskClass.R2,
    "summary": RiskClass.R1,
    "description": RiskClass.R1,
    "attributes.phone": RiskClass.R1,
    "attributes.address": RiskClass.R1,
    "attributes.opening_hours": RiskClass.R0,
    "attributes.website": RiskClass.R1,
    "attributes.price_range": RiskClass.R0,
}
MAX_CORRECTION_ITEMS = 10
MAX_CORRECTION_VALUE = 2000

# Bounded pre-intake classifier. It only decides that a report belongs on the
# existing safety lane; it never grades the report and never creates a case.
_EMERGENCY_MARKERS = (
    "doa giet", "de doa tinh mang", "giet nguoi", "tu tu", "tu sat",
    "cap cuu", "khan cap", "bat coc", "hiep dam", "danh dap",
    "emergency", "dying", "suicide", "kidnap", "assault", "death threat",
)
_SAFE_URGENT_MESSAGE = (
    "Việc này cần cơ quan chức năng xử lý ngay, không phải kênh đính chính nội dung. "
    "Gọi 113 (công an), 114 (cứu hoả) hoặc 115 (cấp cứu) để được hỗ trợ khẩn cấp. "
    "Kênh đính chính không trực 24/7 và không thay thế các số khẩn cấp trên."
)
_OPERATOR_SCOPES = frozenset({"cases:operate", "cases:admin", "cases:decide"})


class CorrectionRejected(ValueError):
    def __init__(self, problem: CaseProblem) -> None:
        super().__init__(problem.code)
        self.problem = problem


class SafetyRoutingRequired(Exception):
    def __init__(self, problem: CaseProblem, safe_message: str) -> None:
        super().__init__(problem.code)
        self.problem = problem
        self.safe_message = safe_message


class IdempotencyConflict(Exception):
    def __init__(self, problem: CaseProblem) -> None:
        super().__init__(problem.code)
        self.problem = problem


def _reject(code: str, detail: str, status: int = 400) -> CorrectionRejected:
    return CorrectionRejected(CaseProblem(code=code, detail=detail, status=status))


@dataclass(frozen=True)
class CorrectionItemInput:
    entity_id: str
    field_path: str
    reported_value: str
    proposed_value: str
    base_entity_revision: int


@dataclass(frozen=True)
class ZaloHandoff:
    """Only a confirmation and a digest cross the trust boundary."""

    conversation_digest: str
    user_confirmed: bool
    transcript: object = None

    def __post_init__(self) -> None:
        if (
            type(self.conversation_digest) is not str
            or len(self.conversation_digest) != 64
            or any(character not in "0123456789abcdef" for character in self.conversation_digest)
            or type(self.user_confirmed) is not bool
            or self.transcript is not None
        ):
            raise ValueError("invalid_case_handoff")


@dataclass(frozen=True)
class CreateCorrectionCommand:
    envelope: CommandEnvelope
    reporter_privacy: str
    items: tuple[CorrectionItemInput, ...]
    optional_phone: str | None = None
    notification_consent: bool = False
    authenticated_user_ref: str | None = None
    handoff: ZaloHandoff | None = None


@dataclass(frozen=True)
class CreateCorrectionResult:
    case_id: str
    public_reference: str
    capability: str
    received_at: datetime
    next_update_at: datetime
    replayed: bool = False


def _fold(value: str) -> str:
    # NFD strips the tone marks but leaves U+0111 "đ" intact, so a marker such as
    # "đánh đập" would never match without folding that letter explicitly.
    stripped = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return "".join(character for character in stripped if not unicodedata.combining(character))


def _looks_urgent(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _EMERGENCY_MARKERS)


class CaseService:
    create_rate_limit = 5
    create_rate_window = 3600

    def __init__(self, store, crypto, policy, *, owner_ref: str, database=None) -> None:
        self._store = store
        self._crypto = crypto
        self._policy = policy
        self._owner_ref = owner_ref
        self._database = database

    # ── Projections the transport layer needs without touching the database ──

    def identity_assurance_for(self, command: CreateCorrectionCommand) -> str:
        """An optional contact is a reply address, never proof of who someone is."""
        return "session" if command.authenticated_user_ref else "none"

    def reporter_privacy_for(self, command: CreateCorrectionCommand) -> str:
        return "attributed" if command.authenticated_user_ref else "anonymous"

    def party_authority_draft_for(
        self, command: CreateCorrectionCommand, *, case_id: str, now: datetime
    ) -> PartyAuthorityDraft | None:
        if not command.authenticated_user_ref:
            return None
        return PartyAuthorityDraft(
            case_id=case_id,
            party_ref=command.authenticated_user_ref,
            authority_kind="account_owner",
            scope="correction:self",
            assurance_level="session",
            granted_at=now,
        )

    # ── Validation ──

    def _validate_actor(self, command: CreateCorrectionCommand, session_user_ref: str | None) -> None:
        envelope = command.envelope
        if type(envelope) is not CommandEnvelope or not envelope.idempotency_key:
            raise _reject("invalid_command_envelope", "A command envelope is required.")
        if _OPERATOR_SCOPES & set(envelope.actor.scopes):
            raise _reject(
                "operator_actor_not_allowed",
                "Operator actors must use the assisted intake path.",
                status=403,
            )
        claimed = command.authenticated_user_ref
        if claimed is not None and claimed != session_user_ref:
            raise _reject(
                "authenticated_ref_not_server_derived",
                "Account linkage is taken from the signed-in session only.",
                status=403,
            )

    def _validate_handoff(self, command: CreateCorrectionCommand) -> None:
        if command.envelope.actor.channel is Channel.ZALO_AI_HANDOFF and command.handoff is None:
            raise _reject("handoff_confirmation_required", "A confirmed handoff is required.")
        if command.handoff is not None and not command.handoff.user_confirmed:
            raise _reject("handoff_confirmation_required", "The reporter must confirm the details.")

    def _validate_items(self, command: CreateCorrectionCommand) -> None:
        items = command.items
        if type(items) is not tuple or not items:
            raise _reject("correction_items_required", "At least one correction is required.")
        if len(items) > MAX_CORRECTION_ITEMS:
            raise _reject("too_many_correction_items", "Too many corrections in one request.")
        seen: set[tuple[str, str]] = set()
        for item in items:
            if type(item) is not CorrectionItemInput:
                raise _reject("invalid_correction_item", "A correction item is malformed.")
            if item.field_path not in CORRECTABLE_FIELD_PATHS:
                raise _reject("field_path_not_correctable", "That field cannot be corrected here.")
            if type(item.entity_id) is not str or not item.entity_id.strip():
                raise _reject("invalid_correction_entity", "A target entity is required.")
            for value in (item.reported_value, item.proposed_value):
                if type(value) is not str or not value.strip():
                    raise _reject("invalid_correction_value", "Both values are required.")
                if len(value) > MAX_CORRECTION_VALUE:
                    raise _reject("correction_value_too_long", "That value is too long.")
            if item.reported_value.strip() == item.proposed_value.strip():
                raise _reject("correction_value_unchanged", "The proposed value is identical.")
            if type(item.base_entity_revision) is not int or item.base_entity_revision < 1:
                raise _reject("invalid_base_entity_revision", "A base revision is required.")
            key = (item.entity_id, item.field_path)
            if key in seen:
                raise _reject("duplicate_correction_field", "That field appears twice.")
            seen.add(key)

    def _route_safety(self, command: CreateCorrectionCommand) -> None:
        for item in command.items:
            if _looks_urgent(item.reported_value) or _looks_urgent(item.proposed_value):
                raise SafetyRoutingRequired(
                    CaseProblem(
                        code="correction_safety_routing",
                        detail="This report belongs on the urgent safety lane.",
                        status=409,
                    ),
                    _SAFE_URGENT_MESSAGE,
                )

    # ── Idempotency ──

    def _request_digest(self, command: CreateCorrectionCommand) -> str:
        body = {
            "reporter_privacy": command.reporter_privacy,
            "notification_consent": bool(command.notification_consent),
            "has_contact": command.optional_phone is not None,
            "handoff": command.handoff.conversation_digest if command.handoff else None,
            "items": [
                {
                    "entity_id": item.entity_id,
                    "field_path": item.field_path,
                    "reported_value": item.reported_value,
                    "proposed_value": item.proposed_value,
                    "base_entity_revision": item.base_entity_revision,
                }
                for item in command.items
            ],
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return self._crypto.digest_capability(f"create:{canonical}")

    def _replay(self, row, *, actor_ref, request_digest, now) -> CreateCorrectionResult:
        if row["expires_at"] <= now:
            raise IdempotencyConflict(
                CaseProblem(
                    code="idempotency_expired",
                    detail="That request key has expired; start a new request.",
                    status=409,
                )
            )
        if (
            row["response_key_version"] != "v1"
            or not hmac.compare_digest(str(row["actor_ref"]), actor_ref)
            or not hmac.compare_digest(str(row["request_digest"]), request_digest)
        ):
            raise IdempotencyConflict(
                CaseProblem(
                    code="idempotency_conflict",
                    detail="That request key was already used for a different request.",
                    status=409,
                )
            )
        payload = self._crypto.decrypt_replay(str(row["response_enc"]), now=now)
        return CreateCorrectionResult(
            case_id=payload["case_id"],
            public_reference=payload["public_reference"],
            capability=payload["capability"],
            received_at=datetime.fromisoformat(payload["received_at"]),
            next_update_at=datetime.fromisoformat(payload["next_update_at"]),
            replayed=True,
        )

    # ── Create ──

    def _clocks(self, *, now: datetime, risk: RiskClass) -> tuple[PromiseClock, ...]:
        policy = self._policy
        targets = (
            ("receipt", policy.receipt_target_seconds),
            ("triage", policy.triage_target_seconds),
            ("update", policy.update_target_seconds),
            ("resolution", policy.resolution_target_seconds_by_risk[risk.value]),
        )
        return tuple(
            PromiseClock(
                kind=kind,
                started_at=now,
                due_at=now + timedelta(seconds=seconds),
                observed_at=now,
                health=PromiseHealth.ON_TRACK,
                policy_revision=policy.revision,
            )
            for kind, seconds in targets
        )

    def create_correction(
        self,
        command: CreateCorrectionCommand,
        *,
        now: datetime,
        session_user_ref: str | None = None,
        rate_subject: str = "anonymous",
    ) -> CreateCorrectionResult:
        if type(command) is not CreateCorrectionCommand:
            raise _reject("invalid_command", "A create-correction command is required.")
        if type(now) is not datetime or now.tzinfo is None:
            raise _reject("invalid_command_clock", "An aware timestamp is required.")
        self._validate_actor(command, session_user_ref)
        self._validate_handoff(command)
        self._validate_items(command)
        self._route_safety(command)

        actor_ref = session_user_ref or "anonymous"
        if self._database is not None:
            allowed = check_case_rate_limit(
                "correction_create",
                rate_subject_digest(rate_subject, master_key=self._digest_key()),
                limit=self.create_rate_limit,
                window=self.create_rate_window,
                now=now,
                database=self._database,
            )
            if not allowed:
                raise _reject(
                    "case_rate_limited", "Too many corrections from here; try again later.", status=429
                )

        key = f"create:{command.envelope.idempotency_key}"
        request_digest = self._request_digest(command)
        with self._store.transaction() as transaction:
            existing = transaction.claim_idempotency(key, now=now)
            if existing is not None:
                return self._replay(
                    existing, actor_ref=actor_ref, request_digest=request_digest, now=now
                )
            result = self._commit_case(
                transaction, command, now=now, session_user_ref=session_user_ref
            )
            transaction.record_idempotency(
                key,
                actor_ref=actor_ref,
                request_digest=request_digest,
                response_enc=self._crypto.encrypt_replay(
                    {
                        "case_id": result.case_id,
                        "public_reference": result.public_reference,
                        "capability": result.capability,
                        "received_at": result.received_at.isoformat(),
                        "next_update_at": result.next_update_at.isoformat(),
                    },
                    now=now,
                ),
                now=now,
            )
        return result

    def _digest_key(self) -> str:
        """Bucket subjects are keyed, so the digest never reveals the raw address."""
        return self._crypto.digest_capability("case-rate-subject")

    def _commit_case(
        self,
        transaction,
        command: CreateCorrectionCommand,
        *,
        now: datetime,
        session_user_ref: str | None,
    ) -> CreateCorrectionResult:
        crypto = self._crypto
        policy = self._policy
        actor = command.envelope.actor
        case_id = str(uuid.uuid4())
        risk = max(
            (CORRECTABLE_FIELD_PATHS[item.field_path] for item in command.items),
            key=lambda value: value.value,
        )
        snapshot = CaseSnapshot(
            case_id=case_id,
            service_kind=ServiceKind.CORRECTION,
            category="correction",
            phase=CasePhase.INTAKE,
            activity=CaseActivity.ACTIVE,
            disposition_family=DispositionFamily.UNDETERMINED,
            domain_outcome=None,
            severity=None,
            reporter_privacy=self.reporter_privacy_for(command),
            owner_ref=self._owner_ref,
            current_revision=1,
            promise_policy_ref=policy.revision,
            created_at=now,
            updated_at=now,
            closed_at=None,
        )
        # correction_items carries a real foreign key to entities; check it here
        # so an unknown target is a stable problem rather than a driver error.
        try:
            transaction.require_entities(tuple(item.entity_id for item in command.items))
        except CaseNotFound as exc:
            raise _reject(
                "correction_entity_unknown", "That entry is not published here.", status=404
            ) from exc
        stored = transaction.insert_case(snapshot)

        transaction.insert_interaction(
            CaseInteractionDraft(
                case_id=case_id,
                channel=actor.channel,
                actor_ref=actor.actor_ref,
                direction="inbound",
                consent_ref="notify:granted" if command.notification_consent else None,
                identity_assurance=self.identity_assurance_for(command),
                payload_enc=crypto.encrypt_private_payload(
                    {
                        "contact": command.optional_phone,
                        "handoff_digest": command.handoff.conversation_digest
                        if command.handoff
                        else None,
                    }
                ),
                created_at=now,
            )
        )

        authority = self.party_authority_draft_for(command, case_id=case_id, now=now)
        if authority is not None:
            transaction.insert_party_authority(authority)

        item_ids = transaction.insert_correction_items(
            case_id,
            tuple(
                CorrectionItemDraft(
                    entity_id=item.entity_id,
                    field_path=item.field_path,
                    reported_value_enc=crypto.encrypt_private_payload({"value": item.reported_value}),
                    proposed_value_enc=crypto.encrypt_private_payload({"value": item.proposed_value}),
                    base_entity_revision=item.base_entity_revision,
                    risk_class=CORRECTABLE_FIELD_PATHS[item.field_path],
                    evidence_level=EvidenceLevel.E0,
                    created_at=now,
                )
                for item in command.items
            ),
        )

        transaction.insert_correction_evidence(
            tuple(
                CorrectionEvidenceDraft(
                    case_id=case_id,
                    item_id=item_id,
                    evidence_level=EvidenceLevel.E0,
                    source_ref=str(actor.channel),
                    descriptor={"kind": "reporter_assertion"},
                    content_enc=None,
                    created_by_ref=actor.actor_ref,
                    created_at=now,
                )
                for item_id in item_ids
            )
        )

        transaction.insert_promise_clocks(case_id, self._clocks(now=now, risk=risk))
        transaction.insert_work_items(
            (
                WorkItemDraft(
                    case_id=case_id,
                    kind="triage",
                    required_role="case_operator",
                    risk_class=risk,
                    ready_at=now,
                    received_at=now,
                    promise_health=PromiseHealth.ON_TRACK,
                ),
            )
        )
        transaction.append_transition(
            TransitionDraft(
                case_id=case_id,
                from_phase=None,
                to_phase=CasePhase.INTAKE,
                from_revision=0,
                to_revision=1,
                actor_ref=actor.actor_ref,
                reason_code="correction_received",
                policy_revision=policy.revision,
                correlation_id=actor.correlation_id,
                occurred_at=now,
                waiting=None,
            )
        )
        transaction.append_audit(
            CaseAuditDraft(
                case_id=case_id,
                actor_ref=actor.actor_ref,
                actor_scopes=tuple(sorted(set(actor.scopes))),
                channel=actor.channel,
                reason_code="correction_received",
                policy_revision=policy.revision,
                correlation_id=actor.correlation_id,
                before_snapshot=None,
                after_snapshot=safe_case_projection(stored),
                occurred_at=now,
            )
        )

        grant = transaction.issue_receipt(
            case_id,
            crypto,
            now=now,
            current_user_id=session_user_ref,
        )

        # Intent only: the dispatcher re-checks consent, verification and
        # revocation immediately before delivery, and never carries a secret.
        transaction.enqueue_outbox(
            OutboxDraft(
                case_id=case_id,
                idempotency_key=f"notify:{case_id}:received",
                topic="correction.received",
                descriptor={"reason": "received", "policy_revision": policy.revision},
                available_at=now,
            )
        )

        return CreateCorrectionResult(
            case_id=case_id,
            public_reference=grant.public_reference,
            capability=grant.capability,
            received_at=now,
            next_update_at=now + timedelta(seconds=policy.update_target_seconds),
            replayed=False,
        )
