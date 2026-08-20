"""Correction intake orchestration.

One public request becomes exactly one case, or nothing at all: validation and
safety routing run before any transaction opens, and the case, its interaction,
E0 evidence, items, clocks, first work item, transition, audit, receipt and
notification intent all commit together.
"""
from __future__ import annotations

import hmac
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .audit import CaseAuditDraft, safe_case_projection
from .domain import (
    ActorContext,
    CaseActivity,
    CasePhase,
    CaseProblem,
    CaseSnapshot,
    Channel,
    CommandEnvelope,
    CorrectionItem,
    DispositionFamily,
    EvidenceLevel,
    PromiseClock,
    PromiseHealth,
    PublicCaseStatus,
    PublicItemDecision,
    PublicItemPublication,
    RiskClass,
    ServiceKind,
)
from .domain import disposition_for, review_relation
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
REPORTER_PRIVACY_CHOICES = frozenset({"anonymous", "attributed"})
MAX_CORRECTION_ITEMS = 10
MAX_CORRECTION_VALUE = 2000

# Bounded pre-intake classifier. It only decides that a report belongs on the
# existing safety lane; it never grades the report and never creates a case.
# Two sets on purpose. Folding diacritics makes "từ từ" (slowly) collide with
# "tự tử" (suicide) and "tủ sát" (cabinet against) with "tự sát", so the
# Vietnamese markers are matched WITH their diacritics. Only markers that stay
# unambiguous once folded are also matched without them, for reporters typing
# on a keyboard without Vietnamese input.
_URGENT_EXACT = (
    "dọa giết", "đe dọa tính mạng", "giết người", "tự tử", "tự sát",
    "cấp cứu", "khẩn cấp", "bắt cóc", "hiếp dâm", "đánh đập",
)
_URGENT_FOLDED = (
    "doa giet", "de doa tinh mang", "giet nguoi", "bat coc", "hiep dam",
    "danh dap", "cap cuu", "khan cap",
    "emergency", "dying", "suicide", "kidnap", "assault", "death threat",
)

# Whole words only. "dying" is a substring of "studying" and "khan cap" of
# "Khan Capital", so bare containment repeats on the English list exactly the
# mistake the diacritic split fixed on the Vietnamese one.
_URGENT_FOLDED_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(marker) for marker in _URGENT_FOLDED) + r")\b"
)
_SAFE_URGENT_MESSAGE = (
    "Việc này cần cơ quan chức năng xử lý ngay, không phải kênh đính chính nội dung. "
    "Gọi 113 (công an), 114 (cứu hoả) hoặc 115 (cấp cứu) để được hỗ trợ khẩn cấp. "
    "Kênh đính chính không trực 24/7 và không thay thế các số khẩn cấp trên."
)
# Both vocabularies: the internal one and the AdminCP scope names a real
# operator actually carries. Listing only the first left the guard blind to
# the very actors it exists to keep off the self-service path.
_OPERATOR_SCOPES = frozenset({
    "cases:operate", "cases:admin", "cases:decide",
    "service.operator", "correction.decide", "truth.review",
    "publication.apply", "publication.verify", "case.supervisor",
})


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
class AssistedIntake:
    """What the operator must already have done before the words were taken down.

    A transcriber is a weaker position than self-service, not a stronger one: the
    reporter cannot see the screen. So the record carries which notice was read
    out, what they agreed to, when, and that the values were read back and
    confirmed in their hearing. Without those the case would rest on the
    operator's word alone.
    """

    operator_ref: str
    privacy_notice_revision: str
    consent_scope: str
    consent_given_at: datetime
    read_back_confirmed: bool
    reporter_confirmed: bool


@dataclass(frozen=True)
class CreateCorrectionCommand:
    envelope: CommandEnvelope
    reporter_privacy: str
    items: tuple[CorrectionItemInput, ...]
    optional_phone: str | None = None
    notification_consent: bool = False
    authenticated_user_ref: str | None = None
    handoff: ZaloHandoff | None = None
    assisted: AssistedIntake | None = None


@dataclass(frozen=True)
class PublicAccessGrant:
    access_token: str
    csrf_token: str


@dataclass(frozen=True)
class AssistedCorrectionResult:
    """What the operator may read back down the phone, and nothing more.

    No capability: that is the reporter's key to their own case. An operator
    holding it would have standing access to somebody else's private thread long
    after the call ended.
    """

    case_id: str
    public_reference: str
    received_at: datetime
    next_update_at: datetime
    read_back: tuple = ()


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
    lowered = text.lower()
    if any(marker in lowered for marker in _URGENT_EXACT):
        return True
    return _URGENT_FOLDED_PATTERN.search(_fold(text)) is not None


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
        if command.assisted is not None:
            # The operator's identity is known; the caller's is not. Recording
            # "session" here would credit the reporter with the operator's login.
            return "transcribed"
        return "session" if command.authenticated_user_ref else "none"

    def consent_ref_for(self, command: CreateCorrectionCommand) -> str | None:
        """The consent this case rests on, in a form that can be read back later."""
        if command.assisted is not None:
            assisted = command.assisted
            return (
                f"assisted:{assisted.privacy_notice_revision}"
                f":{assisted.consent_scope}"
                f":{assisted.consent_given_at.isoformat()}"
                f":read_back={'yes' if assisted.read_back_confirmed else 'no'}"
                f":confirmed={'yes' if assisted.reporter_confirmed else 'no'}"
            )
        return "notify:granted" if command.notification_consent else None

    def reporter_privacy_for(self, command: CreateCorrectionCommand) -> str:
        """The reporter's stated choice, which `_validate_privacy` has bounded."""
        return command.reporter_privacy

    def party_authority_draft_for(
        self, command: CreateCorrectionCommand, *, case_id: str, now: datetime
    ) -> PartyAuthorityDraft | None:
        if command.assisted is not None:
            # Scoped to transcribing this one case. It is not authority to act for
            # the reporter anywhere else, and it is the operator who is named.
            return PartyAuthorityDraft(
                case_id=case_id,
                party_ref=command.assisted.operator_ref,
                authority_kind="transcriber",
                scope="correction:transcribe",
                assurance_level="operator_session",
                granted_at=now,
            )
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
        if _OPERATOR_SCOPES & set(envelope.actor.scopes) and command.assisted is None:
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

    def _validate_privacy(self, command: CreateCorrectionCommand) -> None:
        if command.reporter_privacy not in REPORTER_PRIVACY_CHOICES:
            raise _reject("invalid_reporter_privacy", "That reporting choice is not offered.")
        # Signing in never forces attribution, but claiming attribution without a
        # session would put a name on a case nobody proved they own.
        if command.reporter_privacy == "attributed" and not command.authenticated_user_ref:
            raise _reject(
                "attribution_requires_a_session",
                "Sign in to file this correction under your account.",
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

    @staticmethod
    def _idempotency_actor(
        command: CreateCorrectionCommand, *, session_user_ref: str | None
    ) -> str:
        """Normalized actor plus channel, per the approved plan.

        Deliberately the opt-in rather than the browser session: the receipt is
        bound the same way, so a reporter who filed anonymously while signed in
        can still replay after logging out. The trade is that anonymous filings
        share one scope, which is why the request digest - covering every item
        value and the keyed contact - stays part of the match.
        """
        del session_user_ref  # never widens or narrows the scope on its own
        subject = command.authenticated_user_ref or "anonymous"
        return f"{command.envelope.actor.channel.value}:{subject}"

    def _request_digest(self, command: CreateCorrectionCommand) -> str:
        body = {
            "reporter_privacy": command.reporter_privacy,
            "notification_consent": bool(command.notification_consent),
            # The value, not just its presence: a corrected phone under the same
            # key must conflict rather than silently replay the old grant. Only
            # the keyed digest enters the canonical body, never the number.
            "contact": self._crypto.digest_capability(command.optional_phone.strip())
            if command.optional_phone
            else None,
            "handoff": command.handoff.conversation_digest if command.handoff else None,
            # A different consent scope or notice is a different request, not a
            # replay of the last one under the same key.
            "assisted": (
                {
                    "operator_ref": command.assisted.operator_ref,
                    "privacy_notice_revision": command.assisted.privacy_notice_revision,
                    "consent_scope": command.assisted.consent_scope,
                    "consent_given_at": command.assisted.consent_given_at.isoformat(),
                }
                if command.assisted
                else None
            ),
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
        # ensure_ascii keeps the canonical form inside digest_capability's ASCII
        # contract; a Vietnamese value would otherwise raise a credential error.
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return self._crypto.digest_capability(f"create:{canonical}")

    @staticmethod
    def _replays_cleanly(row, *, actor_ref: str, request_digest: str, now: datetime) -> bool:
        return (
            row["expires_at"] > now
            and row["response_key_version"] == "v1"
            and hmac.compare_digest(str(row["actor_ref"]), actor_ref)
            and hmac.compare_digest(str(row["request_digest"]), request_digest)
        )

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
        rate_subject: str,
        session_user_ref: str | None = None,
    ) -> CreateCorrectionResult:
        if type(command) is not CreateCorrectionCommand:
            raise _reject("invalid_command", "A create-correction command is required.")
        if type(now) is not datetime or now.tzinfo is None:
            raise _reject("invalid_command_clock", "An aware timestamp is required.")
        self._validate_actor(command, session_user_ref)
        self._validate_privacy(command)
        self._validate_handoff(command)
        self._validate_items(command)
        self._route_safety(command)

        actor_ref = self._idempotency_actor(command, session_user_ref=session_user_ref)
        key = f"create:{command.envelope.idempotency_key}"
        request_digest = self._request_digest(command)

        # A lost-response retry must not spend a rate slot. Without this, a
        # client that retries a dropped response burns the bucket and the very
        # request that should replay the receipt is answered with 429 instead,
        # leaving a committed capability the reporter can never collect. Only a
        # clean replay skips the bucket; a conflicting body still pays for it.
        settled = self._store.peek_idempotency(key)
        if settled is not None and self._replays_cleanly(
            settled, actor_ref=actor_ref, request_digest=request_digest, now=now
        ):
            return self._replay(
                settled, actor_ref=actor_ref, request_digest=request_digest, now=now
            )

        # Unconditional: with no database wired this raises
        # case_postgresql_required rather than quietly accepting unlimited
        # submissions, so a missing dependency fails closed.
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
                consent_ref=self.consent_ref_for(command),
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

        # Bind the receipt to the account only when the reporter opted in.
        # Using the session here would silently lock a signed-in reporter who
        # filed anonymously out of their own capability after logging out.
        grant = transaction.issue_receipt(
            case_id,
            crypto,
            now=now,
            current_user_id=command.authenticated_user_ref,
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


    # ── Transport adapters ──
    #
    # The router hands over validated transport models and gets domain results
    # or domain exceptions back; it never reaches the store itself.

    @staticmethod
    def _now(now: datetime | None) -> datetime:
        return now if now is not None else datetime.now(timezone.utc)

    def _limit(
        self, bucket: str, rate_subject: str, *, limit: int, window: int, now: datetime
    ) -> None:
        allowed = check_case_rate_limit(
            bucket,
            rate_subject_digest(rate_subject, master_key=self._digest_key()),
            limit=limit,
            window=window,
            now=now,
            database=self._database,
        )
        if not allowed:
            raise _reject("case_rate_limited", "Too many attempts; try again later.", status=429)

    def create_assisted_correction(
        self,
        *,
        items: tuple[CorrectionItemInput, ...],
        assisted: AssistedIntake,
        channel: Channel,
        reporter_privacy: str,
        idempotency_key: str,
        correlation_id: str,
        rate_subject: str,
        optional_phone: str | None = None,
        notification_consent: bool = False,
        now: datetime,
    ) -> "AssistedCorrectionResult":
        """File a correction somebody gave over the phone, through the same Kernel.

        Same case, same receipt, same clocks and same work as self-service: an
        assisted report is not a lesser record. What differs is who is named and
        what the file has to prove — the operator, and the consent they took.

        The capability is deliberately not returned. It is the reporter's key to
        their own case, and handing it to the person who typed the report would
        give an operator standing access to somebody else's private thread.
        """
        result = self.create_correction(
            CreateCorrectionCommand(
                envelope=CommandEnvelope(
                    idempotency_key=idempotency_key,
                    expected_revision=None,
                    actor=ActorContext(
                        actor_ref=assisted.operator_ref,
                        channel=channel,
                        scopes=frozenset({"service.operator"}),
                        correlation_id=correlation_id,
                    ),
                ),
                reporter_privacy=reporter_privacy,
                items=items,
                optional_phone=optional_phone,
                notification_consent=notification_consent,
                authenticated_user_ref=None,
                assisted=assisted,
            ),
            now=now,
            rate_subject=rate_subject,
        )
        return AssistedCorrectionResult(
            case_id=result.case_id,
            public_reference=result.public_reference,
            received_at=result.received_at,
            next_update_at=result.next_update_at,
            read_back=tuple(
                {"entity_id": item.entity_id, "field_path": item.field_path,
                 "proposed_value": item.proposed_value}
                for item in items
            ),
        )

    def create_correction_from_transport(
        self,
        payload,
        *,
        idempotency_key: str,
        correlation_id: str,
        rate_subject: str,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ) -> CreateCorrectionResult:
        handoff = None
        if getattr(payload, "handoff_digest", None):
            handoff = ZaloHandoff(
                conversation_digest=payload.handoff_digest,
                user_confirmed=bool(payload.handoff_confirmed),
            )
        command = CreateCorrectionCommand(
            envelope=CommandEnvelope(
                idempotency_key=idempotency_key,
                expected_revision=None,
                actor=ActorContext(
                    actor_ref=session_user_ref or "anonymous",
                    channel=Channel.ZALO_AI_HANDOFF if handoff else Channel.WEB,
                    scopes=frozenset(),
                    correlation_id=correlation_id,
                ),
            ),
            reporter_privacy=payload.reporter_privacy,
            items=tuple(
                CorrectionItemInput(
                    entity_id=item.entity_id,
                    field_path=item.field_path,
                    reported_value=item.reported_value,
                    proposed_value=item.proposed_value,
                    base_entity_revision=item.base_entity_revision,
                )
                for item in payload.items
            ),
            optional_phone=payload.optional_phone,
            notification_consent=payload.notification_consent,
            authenticated_user_ref=session_user_ref,
            handoff=handoff,
        )
        return self.create_correction(
            command,
            now=self._now(now),
            rate_subject=rate_subject,
            session_user_ref=session_user_ref,
        )

    def exchange_receipt(
        self,
        *,
        public_reference: str,
        capability: str,
        rate_subject: str,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ) -> PublicAccessGrant:
        now = self._now(now)
        self._limit("receipt_exchange", rate_subject, limit=10, window=3600, now=now)
        grant = self._store.exchange_receipt(
            public_reference,
            capability,
            self._crypto,
            now=now,
            current_user_id=session_user_ref,
        )
        with self._store.transaction() as transaction:
            sessions = transaction.access_session_count(grant.access.case_id)
        if sessions > 1:
            from . import metrics as _metrics

            # Coming back for the same case is failure demand: the first answer
            # did not settle it. One event per return visit, none for the first.
            _metrics.observe("repeated_contact", channel="web",
                             case_id=grant.access.case_id, now=now)
        return PublicAccessGrant(
            access_token=grant.access_token,
            csrf_token=self._crypto.issue_case_csrf(grant.access),
        )

    def public_status(
        self,
        *,
        access_token: str,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ) -> PublicCaseStatus:
        now = self._now(now)
        access = self._store.validate_access(
            access_token, self._crypto, now=now, current_user_id=session_user_ref
        )
        with self._store.transaction() as transaction:
            case = transaction.load_case(access.case_id)
            items = transaction.load_correction_items(access.case_id)
            reference = transaction.load_public_reference(access.case_id)
            links = transaction.load_review_links(access.case_id)
        return project_public_status(
            case,
            items,
            review_relation=review_relation(links),
            public_reference=reference or "",
        )

    def rotate_receipt(
        self,
        *,
        access_token: str,
        rate_subject: str,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ):
        now = self._now(now)
        self._limit("receipt_rotation", rate_subject, limit=5, window=3600, now=now)
        return self._store.rotate_receipt(
            access_token, self._crypto, now=now, current_user_id=session_user_ref
        )

    def revoke_access(
        self,
        *,
        access_token: str,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ) -> None:
        now = self._now(now)
        access = self._store.validate_access(
            access_token, self._crypto, now=now, current_user_id=session_user_ref
        )
        self._store.revoke_access(access.case_id, now=now)

    def open_review(
        self,
        *,
        access_token: str,
        reason: str,
        expected_revision: int,
        rate_subject: str,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ):
        """A review is a new linked case; the closed original is never reopened."""
        now = self._now(now)
        self._limit("case_review", rate_subject, limit=3, window=86400, now=now)
        access = self._store.validate_access(
            access_token, self._crypto, now=now, current_user_id=session_user_ref
        )
        actor_ref = session_user_ref or "anonymous"
        correlation_id = uuid.uuid4().hex
        with self._store.transaction() as transaction:
            original = transaction.load_case(access.case_id, for_update=True)
            if original.phase is not CasePhase.CLOSED:
                raise _reject(
                    "review_requires_a_closed_case",
                    "This case is still open; a review starts after it closes.",
                    status=409,
                )
            if original.current_revision != expected_revision:
                raise _reject(
                    "case_revision_conflict",
                    "That case changed since you read it; reload and try again.",
                    status=409,
                )
            review_id = str(uuid.uuid4())
            stored = transaction.insert_case(
                CaseSnapshot(
                    case_id=review_id,
                    service_kind=ServiceKind.CORRECTION,
                    category="review",
                    phase=CasePhase.INTAKE,
                    activity=CaseActivity.ACTIVE,
                    disposition_family=DispositionFamily.UNDETERMINED,
                    domain_outcome=None,
                    severity=None,
                    reporter_privacy=original.reporter_privacy,
                    owner_ref=self._owner_ref,
                    current_revision=1,
                    promise_policy_ref=self._policy.revision,
                    created_at=now,
                    updated_at=now,
                    closed_at=None,
                )
            )
            transaction.link_review_case(review_id, review_of_case_id=original.case_id)
            transaction.insert_interaction(
                CaseInteractionDraft(
                    case_id=review_id,
                    channel=Channel.WEB,
                    actor_ref=actor_ref,
                    direction="inbound",
                    identity_assurance="session" if session_user_ref else "none",
                    payload_enc=self._crypto.encrypt_private_payload({"reason": reason}),
                    created_at=now,
                )
            )
            transaction.insert_promise_clocks(review_id, self._clocks(now=now, risk=RiskClass.R1))
            transaction.insert_work_items(
                (
                    WorkItemDraft(
                        case_id=review_id,
                        kind="review",
                        required_role="case_operator",
                        risk_class=RiskClass.R1,
                        ready_at=now,
                        received_at=now,
                        promise_health=PromiseHealth.ON_TRACK,
                    ),
                )
            )
            transaction.append_transition(
                TransitionDraft(
                    case_id=review_id,
                    from_phase=None,
                    to_phase=CasePhase.INTAKE,
                    from_revision=0,
                    to_revision=1,
                    actor_ref=actor_ref,
                    reason_code="review_requested",
                    policy_revision=self._policy.revision,
                    correlation_id=correlation_id,
                    occurred_at=now,
                    waiting=None,
                )
            )
            transaction.append_audit(
                CaseAuditDraft(
                    case_id=review_id,
                    actor_ref=actor_ref,
                    actor_scopes=(),
                    channel=Channel.WEB,
                    reason_code="review_requested",
                    policy_revision=self._policy.revision,
                    correlation_id=correlation_id,
                    before_snapshot=None,
                    after_snapshot=safe_case_projection(stored),
                    occurred_at=now,
                )
            )
            grant = transaction.issue_receipt(
                review_id, self._crypto, now=now, current_user_id=session_user_ref
            )
        return grant


    def request_contact_verification(
        self,
        *,
        access_token: str,
        phone: str,
        consent: bool,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ):
        """The case comes from the session; the body never names one."""
        from .contact import request_contact_verification as _request

        now = self._now(now)
        access = self._store.validate_access(
            access_token, self._crypto, now=now, current_user_id=session_user_ref
        )
        return _request(access, phone, consent, now=now)

    def verify_contact(
        self,
        *,
        access_token: str,
        code: str,
        session_user_ref: str | None = None,
        now: datetime | None = None,
    ):
        from .contact import verify_contact as _verify

        now = self._now(now)
        access = self._store.validate_access(
            access_token, self._crypto, now=now, current_user_id=session_user_ref
        )
        return _verify(access, code, now=now)


# ── Public status projection ──
#
# Backstage vocabulary never crosses this boundary. Phase, activity, outcome,
# publication state and promise health select a line from a fixed catalog; the
# case id, owner, severity, risk, evidence and any operator note stay behind.
_PUBLIC_STEPS = {
    CasePhase.INTAKE: "received",
    CasePhase.TRIAGE: "checking",
    CasePhase.INVESTIGATION: "checking",
    CasePhase.DECISION: "deciding",
    CasePhase.FULFILLMENT: "updating",
    CasePhase.CLOSED: "closed",
}
_WAITING_ACTORS = {
    CaseActivity.ACTIVE: None,
    CaseActivity.WAITING_ON_REQUESTER: "requester",
    CaseActivity.WAITING_ON_EXTERNAL: "external_source",
}
_SAFE_NEXT_ACTIONS = {
    ("received", None): "Chúng tôi đã nhận yêu cầu và sẽ xem trong thời gian tới.",
    ("checking", None): "Chúng tôi đang đối chiếu thông tin bạn gửi.",
    ("deciding", None): "Chúng tôi đang kết luận yêu cầu này.",
    ("updating", None): "Kết luận đã có; phần hiển thị công khai đang được xử lý.",
    ("closed", None): "Yêu cầu đã khép lại. Bạn có thể xin xem xét lại.",
    ("received", "requester"): "Chúng tôi cần bạn bổ sung thông tin để đi tiếp.",
    ("checking", "requester"): "Chúng tôi cần bạn bổ sung thông tin để đi tiếp.",
    ("deciding", "requester"): "Chúng tôi cần bạn bổ sung thông tin để đi tiếp.",
    ("updating", "requester"): "Chúng tôi cần bạn bổ sung thông tin để đi tiếp.",
    ("received", "external_source"): "Chúng tôi đang chờ phản hồi từ một nguồn bên ngoài.",
    ("checking", "external_source"): "Chúng tôi đang chờ phản hồi từ một nguồn bên ngoài.",
    ("deciding", "external_source"): "Chúng tôi đang chờ phản hồi từ một nguồn bên ngoài.",
    ("updating", "external_source"): "Chúng tôi đang chờ phản hồi từ một nguồn bên ngoài.",
}
_PUBLIC_FALLBACK_ACTION = "Chúng tôi sẽ cập nhật cho bạn theo lịch đã hẹn."


def _clock_due(case: CaseSnapshot, kind: str) -> datetime | None:
    for clock in case.promise_clocks:
        if clock.kind == kind:
            return clock.due_at
    return None


def project_public_status(
    case: CaseSnapshot,
    items: tuple[CorrectionItem, ...],
    *,
    review_relation: str,
    public_reference: str,
) -> PublicCaseStatus:
    """Render only what a reporter may see, from a fixed safe-copy catalog."""
    if type(case) is not CaseSnapshot or type(items) is not tuple:
        raise ValueError("invalid_public_projection")
    if type(review_relation) is not str or not review_relation:
        raise ValueError("invalid_public_projection")
    if type(public_reference) is not str or not public_reference:
        raise ValueError("invalid_public_projection")

    step = _PUBLIC_STEPS[case.phase]
    waiting_for = _WAITING_ACTORS[case.activity]
    next_action = _SAFE_NEXT_ACTIONS.get((step, waiting_for), _PUBLIC_FALLBACK_ACTION)
    # The resolution clock is measured internally but never published, so the
    # update clock alone carries the public promise.
    next_update_at = _clock_due(case, "update") or case.updated_at

    return PublicCaseStatus(
        public_reference=public_reference,
        received_at=case.created_at,
        current_step=step,
        waiting_for=waiting_for,
        next_action=next_action,
        next_update_at=next_update_at,
        promise_health=case.promise_health,
        item_decisions=tuple(
            PublicItemDecision(
                item_id=item.item_id,
                # The ruling, not the row id that recorded it: an internal
                # reference tells the reporter nothing they can act on.
                outcome=item.outcome_code,
                disposition_family=disposition_for(item.outcome_code),
            )
            for item in items
        ),
        item_publication_states=tuple(
            PublicItemPublication(item_id=item.item_id, state=item.publication_state)
            for item in items
        ),
        review_path=review_relation,
    )
