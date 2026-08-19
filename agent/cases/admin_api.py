"""The operator workbench: one scope per command, and no prefix that grants them all.

`/admin/cases` is not a permission. Reading the queue, transcribing a phone call,
ruling on an item, changing the live site and taking work off a colleague are
five different authorities, and each route names the one it needs. A single gate
on the prefix would mean whoever can read the queue can also publish, which is
the failure this module is shaped to prevent.

Responses here are the safe workbench projection: identifiers, classification and
state. What a person actually reported is private, and reaching it needs both the
work to justify it and a short-lived grant that a separate step-up creates. The
queue never carries it at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

if str(Path(__file__).resolve().parents[1]) not in sys.path:  # pragma: no cover - import shim
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from admin_permissions import admin_scopes_for_user  # noqa: E402

# Every command the workbench offers, against the single authority it needs.
# Kept as data so a route cannot be added without stating what it costs, and so
# the matrix is readable in one place rather than spread across decorators.
CASE_ACTION_SCOPE: dict[str, str] = {
    # Looking at work, and at one case's safe summary.
    "queue.view": "service.operator",
    "case.view": "service.operator",
    # Reaching what a person actually reported, for as long as the work lasts.
    "access.stepup": "service.operator",
    "access.revoke": "service.operator",
    # Holding and handing back work.
    "work.claim": "service.operator",
    "work.heartbeat": "service.operator",
    "work.release": "service.operator",
    "work.recuse": "service.operator",
    # Taking work off somebody else is a supervisor act, not a working one.
    "work.takeover": "case.supervisor",
    # Recording what was found, and ruling on it, are different jobs.
    "evidence.add": "service.operator",
    "item.decide": "correction.decide",
    "changeset.build": "correction.decide",
    # Changing what the public reads, and claiming they can see it.
    "changeset.apply": "publication.apply",
    "changeset.rollback": "publication.apply",
    "changeset.verify": "publication.verify",
    # Taking a correction down the phone on somebody's behalf.
    "assisted.create": "service.operator",
}


def _require_kernel() -> None:
    """A dormant capability answers 404, not 403.

    403 would confirm the workbench exists and that the caller merely lacks a
    scope. While the kernel is switched off there is nothing here to have.
    """
    from fastapi import HTTPException

    from config import settings

    if not getattr(settings, "CASE_KERNEL_ENABLED", False):
        raise HTTPException(404, detail={"code": "capability_unavailable",
                                         "detail": "This capability is not available."})


def action_scope(action: str) -> str:
    """The scope a command needs. Unknown commands raise rather than default.

    Defaulting would mean a new route silently inherits whatever the prefix
    allows, which is exactly the overgrant this table exists to stop.
    """
    return CASE_ACTION_SCOPE[action]


def may_perform(user: dict | None, action: str) -> bool:
    """Whether this administrative actor holds the authority for one command."""
    scopes = set(admin_scopes_for_user(user))
    return "*" in scopes or action_scope(action) in scopes


def require_case_action(action: str):
    """Build the dependency that guards one command.

    It reuses the AdminCP authentication, rate limiting and audit path, but
    overrides the scope with this command's own instead of letting the router's
    prefix decide. `action_scope` is called at build time so a typo fails when
    the route is declared, not when somebody is refused in production.
    """
    scope = action_scope(action)

    async def guard(request):
        import admin

        _require_kernel()
        await admin.require_admin(request, required_scope_override=scope)
        await admin.require_csrf(request)

    # Named for what it enforces. The AdminCP surface contract scans dependency
    # names for require_admin, and a closure that calls it under another name
    # reads to that scan as an unguarded /admin route.
    guard.__name__ = f"require_admin_case_{action.replace('.', '_')}"
    # The scan reads qualnames, and a closure keeps the factory's.
    guard.__qualname__ = guard.__name__
    guard.case_action = action
    guard.case_scope = scope
    return guard


# ── Private-data clearance ──
#
# The queue and a case's safe summary need no clearance: they carry identifiers,
# classification and state, never what a person wrote. Reading the report itself
# needs a second act — the operator proves who they are again, and gets a grant
# that lasts fifteen minutes and dies with their login session.

from dataclasses import dataclass  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

STEP_UP_LIFETIME = timedelta(minutes=15)
PRIVATE_EVIDENCE_SCOPE = "case.private_evidence"

_DATABASE = None
_CRYPTO = None
_PROJECTION_FETCHER = None


def configure_case_admin_api(*, database=None, crypto=None, projection_fetcher=None) -> None:
    global _DATABASE, _CRYPTO, _PROJECTION_FETCHER
    _DATABASE = database
    _CRYPTO = crypto
    _PROJECTION_FETCHER = projection_fetcher


def _store():
    from .store import PostgresCaseStore

    return PostgresCaseStore(_DATABASE) if _DATABASE is not None else PostgresCaseStore()


def _crypto():
    if _CRYPTO is None:
        raise RuntimeError("case_admin_api_not_configured")
    return _CRYPTO


class StepUpRefused(ValueError):
    def __init__(self, code: str, detail: str, status: int = 403) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class StepUpGrant:
    case_id: str
    actor_ref: str
    secret: str
    expires_at: datetime


def grant_private_evidence_access(case_id: str, actor, *, now: datetime) -> StepUpGrant:
    """Issue a clearance after the operator has just proved who they are.

    An admin API key cannot receive one. A key is a machine credential shared by
    deployment tooling; it identifies no person, and there would be nobody to
    hold answerable for reading somebody's report.
    """
    actor_ref = getattr(actor, "actor_ref", "") or ""
    if not actor_ref or actor_ref == "admin-key":
        raise StepUpRefused(
            "human_operator_required",
            "Reading a report needs a person, not a shared key.",
        )
    secret = _crypto().issue_capability()
    expires_at = now + STEP_UP_LIFETIME
    with _store().transaction() as transaction:
        # One live grant per person per case: re-authenticating replaces the old
        # one rather than quietly stacking a second way in.
        transaction.revoke_admin_access(case_id=case_id, actor_ref=actor_ref, now=now)
        transaction.grant_admin_access(
            case_id=case_id, actor_ref=actor_ref, scope=PRIVATE_EVIDENCE_SCOPE,
            session_digest=_crypto().digest_capability(secret), expires_at=expires_at,
        )
    return StepUpGrant(case_id=case_id, actor_ref=actor_ref, secret=secret,
                       expires_at=expires_at)


def revoke_private_evidence_access(case_id: str, actor, *, now: datetime) -> None:
    actor_ref = getattr(actor, "actor_ref", "") or ""
    with _store().transaction() as transaction:
        transaction.revoke_admin_access(case_id=case_id, actor_ref=actor_ref, now=now)


def require_private_evidence_access(case_id: str, actor, secret: str | None, *,
                                    now: datetime) -> None:
    """Fail the same way for expired, revoked, missing and wrong.

    Distinguishing them would tell somebody probing which half of the guess was
    right, and none of the four should let them read the report.
    """
    actor_ref = getattr(actor, "actor_ref", "") or ""
    live = False
    if secret and actor_ref:
        with _store().transaction() as transaction:
            live = transaction.admin_access_is_live(
                case_id=case_id, actor_ref=actor_ref, scope=PRIVATE_EVIDENCE_SCOPE,
                session_digest=_crypto().digest_capability(secret), now=now,
            )
    if not live:
        raise StepUpRefused(
            "case_private_access_required",
            "Re-authenticate to open this report.",
        )


# ── Routes ──
#
# Every route names its own action. There is deliberately no router-level scope
# dependency: one gate on `/admin/cases` would make reading the queue equivalent
# to publishing, which is the whole thing this module refuses to allow.

from fastapi import APIRouter, Depends, HTTPException, Request  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr  # noqa: E402

from .domain import ActorContext, Channel  # noqa: E402

MAX_READ_BACK = 2000

case_admin_router = APIRouter(prefix="/admin/cases", tags=["admin-cases"])


def _now() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


def _actor(request: Request, *, channel: Channel = Channel.WEB) -> ActorContext:
    state = getattr(request, "state", None)
    user = getattr(state, "admin_user", None)
    actor_ref = f"user:{user.get('id')}" if user and user.get("id") else "admin-key"
    return ActorContext(
        actor_ref=actor_ref,
        channel=channel,
        scopes=frozenset(getattr(state, "admin_scopes", None) or ()),
        correlation_id=getattr(state, "request_id", None) or "admin-cases",
    )


def _fail(error) -> HTTPException:
    """Domain refusals answer as themselves; anything else is not decoded here."""
    problem = getattr(error, "problem", None)
    if problem is not None:
        return HTTPException(problem.status, detail={"code": problem.code,
                                                     "detail": problem.detail})
    if isinstance(error, StepUpRefused):
        return HTTPException(error.status, detail={"code": error.code,
                                                   "detail": error.detail})
    return HTTPException(409, detail={"code": "case_command_refused",
                                      "detail": "That command was refused."})


def _guard(action: str):
    return Depends(require_case_action(action))


@case_admin_router.get("", dependencies=[_guard("queue.view")])
async def list_case_queue(request: Request, kind: str | None = None):
    """Work waiting, with no report content in it at all."""
    from . import work_control

    try:
        page = work_control.list_queue(
            _actor(request), {"kind": kind} if kind else None, now=_now()
        )
    except Exception as error:  # noqa: BLE001 - re-raised as a domain problem
        raise _fail(error) from error
    return {
        "items": [
            {
                "work_item_id": item.work_item_id,
                "case_id": item.case_id,
                "kind": item.kind,
                "risk_class": str(item.risk_class),
                "status": item.status,
                "revision": item.revision,
            }
            for item in page.items
        ]
    }


@case_admin_router.get("/{case_id}", dependencies=[_guard("case.view")])
async def get_case_workbench(request: Request, case_id: str):
    """The safe summary: what kind of work this is, never what was written."""
    try:
        with _store().transaction() as transaction:
            snapshot = transaction.load_case(case_id)
            items = transaction.load_correction_items(case_id)
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return {
        "case_id": snapshot.case_id,
        "phase": str(snapshot.phase),
        "activity": str(snapshot.activity),
        "disposition_family": str(snapshot.disposition_family),
        "current_revision": snapshot.current_revision,
        "promise_health": str(snapshot.promise_health),
        "items": [
            {
                "item_id": item.item_id,
                "entity_id": item.entity_id,
                "field_path": item.field_path,
                "risk_class": str(item.risk_class),
                "evidence_level": str(item.evidence_level),
                "publication_state": str(item.publication_state),
            }
            for item in items
        ],
    }


class StepUpBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: StrictStr


@case_admin_router.post("/access/step-up", dependencies=[_guard("access.stepup")])
async def open_private_evidence(request: Request, body: StepUpBody):
    try:
        grant = grant_private_evidence_access(body.case_id, _actor(request), now=_now())
    except StepUpRefused as error:
        raise _fail(error) from error
    return {"case_id": grant.case_id, "access": grant.secret,
            "expires_at": grant.expires_at.isoformat()}


@case_admin_router.delete("/access/step-up", dependencies=[_guard("access.revoke")])
async def close_private_evidence(request: Request, case_id: str):
    revoke_private_evidence_access(case_id, _actor(request), now=_now())
    return {"status": "revoked"}


# ── Work, decisions, publication ──

class WorkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: StrictStr
    expected_revision: StrictInt | None = None
    reason: StrictStr | None = Field(default=None, max_length=200)


def _work_control():
    from . import work_control

    return work_control


def _work_reply(item) -> dict:
    return {"work_item_id": item.work_item_id, "status": item.status,
            "revision": item.revision}


# Each route is written out rather than generated. A factory would hide the path
# from the static route registry, which is how a route stops being checked.

@case_admin_router.post("/work/claim", dependencies=[_guard("work.claim")])
async def claim_work(request: Request, body: WorkBody):
    try:
        item = _work_control().claim_work_item(
            body.work_item_id, _actor(request), body.expected_revision or 0, now=_now())
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return _work_reply(item)


@case_admin_router.post("/work/heartbeat", dependencies=[_guard("work.heartbeat")])
async def heartbeat_work(request: Request, body: WorkBody):
    try:
        item = _work_control().heartbeat_lease(body.work_item_id, _actor(request), now=_now())
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return _work_reply(item)


@case_admin_router.post("/work/release", dependencies=[_guard("work.release")])
async def release_work(request: Request, body: WorkBody):
    try:
        item = _work_control().release_work_item(body.work_item_id, _actor(request), now=_now())
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return _work_reply(item)


@case_admin_router.post("/work/takeover", dependencies=[_guard("work.takeover")])
async def takeover_work(request: Request, body: WorkBody):
    """Supervisor only, and the risk guards underneath still apply."""
    try:
        item = _work_control().takeover_work_item(
            body.work_item_id, _actor(request), body.reason or "", now=_now())
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return _work_reply(item)


@case_admin_router.post("/work/recuse", dependencies=[_guard("work.recuse")])
async def recuse_work(request: Request, body: WorkBody):
    try:
        item = _work_control().recuse_actor(
            body.work_item_id, _actor(request), body.reason or "", now=_now())
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return _work_reply(item)


class ChangeSetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: StrictStr
    change_set_id: StrictStr
    expected_case_revision: StrictInt
    expected_entity_revision: StrictInt | None = None
    reason_code: StrictStr | None = Field(default=None, max_length=200)


@case_admin_router.post("/change-sets/apply", dependencies=[_guard("changeset.apply")])
async def apply_change_set_route(request: Request, body: ChangeSetBody):
    from .publication import ApplyChangeSetCommand, apply_change_set

    try:
        result = apply_change_set(
            ApplyChangeSetCommand(
                case_id=body.case_id, change_set_id=body.change_set_id,
                actor=_actor(request), expected_case_revision=body.expected_case_revision,
                expected_entity_revision=body.expected_entity_revision or 0,
            ),
            now=_now(),
        )
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return {"change_set_id": result.change_set_id, "state": str(result.state),
            "entity_revision": result.entity_revision,
            "applied_fields": list(result.applied_fields)}


@case_admin_router.post("/change-sets/rollback", dependencies=[_guard("changeset.rollback")])
async def rollback_change_set_route(request: Request, body: ChangeSetBody):
    from .publication import RollbackChangeSetCommand, rollback_change_set

    try:
        result = rollback_change_set(
            RollbackChangeSetCommand(
                case_id=body.case_id, change_set_id=body.change_set_id,
                actor=_actor(request), reason_code=body.reason_code or "operator_request",
            ),
            now=_now(),
        )
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return {"change_set_id": result.change_set_id, "state": str(result.state),
            "entity_revision": result.entity_revision}


# ── Guided intake ──
#
# A transcriber types what somebody said on the phone. That is a weaker position
# than self-service, not a stronger one: the reporter cannot see the screen, so
# the record has to prove they were told what would be stored, agreed to it, and
# heard the value read back before it was accepted.
#
# `extra='forbid'` is the boundary. It refuses any field the schema does not name
# — including password, otp, recovery_code and secret — before validation reads a
# value, so an authentication secret cannot arrive here even by accident.

ASSISTED_CHANNELS = {Channel.PHONE.value, Channel.ZALO_HUMAN.value}


class AssistedItemBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: StrictStr = Field(max_length=200)
    field_path: StrictStr = Field(max_length=100)
    reported_value: StrictStr = Field(max_length=MAX_READ_BACK)
    proposed_value: StrictStr = Field(max_length=MAX_READ_BACK)
    base_entity_revision: StrictInt
    # Read back to the reporter, in their hearing, before this was accepted.
    read_back_confirmed: StrictBool


class AssistedCorrectionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: StrictStr
    privacy_notice_revision: StrictStr = Field(max_length=100)
    consent_scope: StrictStr = Field(max_length=100)
    consent_given_at: datetime
    reporter_privacy: StrictStr
    reporter_confirmed: StrictBool
    items: tuple[AssistedItemBody, ...]
    notification_consent: StrictBool = False
    optional_phone: StrictStr | None = Field(default=None, max_length=32)


def validate_assisted_intake(body: AssistedCorrectionBody, *, now: datetime) -> None:
    """Everything the reporter must actually have been given, checked before any write."""
    if body.channel not in ASSISTED_CHANNELS:
        raise StepUpRefused("assisted_channel_not_offered",
                            "That channel is not a transcribed one.", status=422)
    if not body.privacy_notice_revision.strip():
        raise StepUpRefused("privacy_notice_required",
                            "Record which notice was read out.", status=422)
    if not body.consent_scope.strip():
        raise StepUpRefused("consent_scope_required",
                            "Consent has to say what it covers.", status=422)
    if body.consent_given_at > now:
        raise StepUpRefused("consent_not_yet_given",
                            "Consent cannot be dated in the future.", status=422)
    if not body.items:
        raise StepUpRefused("correction_items_required",
                            "A correction needs at least one item.", status=422)
    if not all(item.read_back_confirmed for item in body.items):
        # Without this the record would be the operator's word for what was said.
        raise StepUpRefused("read_back_required",
                            "Read each value back before accepting it.", status=422)
    if not body.reporter_confirmed:
        raise StepUpRefused("reporter_confirmation_required",
                            "The reporter has to agree before this is filed.", status=422)


# The route is deliberately not mounted yet. Filing has to create the interaction,
# the scoped authority and the consent record inside the same transaction as the
# case, and until that exists an endpoint here would advertise a capability that
# does not work. The schema and its checks are what a route will stand on.


def parse_assisted_body(payload: dict) -> AssistedCorrectionBody:
    """Build the body, and refuse in a way that is safe to log.

    Pydantic's own `extra_forbidden` message quotes the offending value back
    (`input_value='...'`). For a field named `password` or `otp` that puts the
    secret into the error body, the server log and any client-side reporting --
    the exact leak the forbidden-extras rule exists to prevent. So the refusal is
    rebuilt here from field locations only, and never carries an input.
    """
    from pydantic import ValidationError

    try:
        return AssistedCorrectionBody(**payload)
    except ValidationError as error:
        fields = sorted({
            ".".join(str(part) for part in item.get("loc", ()))
            for item in error.errors()
        })
        raise StepUpRefused(
            "assisted_body_rejected",
            "These fields are not accepted here: " + ", ".join(fields),
            status=422,
        ) from None


# ── Evidence, decisions, change sets ──

class EvidenceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: StrictStr
    item_id: StrictStr | None = None
    level: StrictStr
    source_scope: StrictStr = Field(max_length=100)
    source_ref: StrictStr | None = Field(default=None, max_length=500)
    observed_at: datetime
    effective_at: datetime
    expires_at: datetime | None = None
    asserted_value: StrictStr | None = Field(default=None, max_length=MAX_READ_BACK)
    content: StrictStr | None = Field(default=None, max_length=MAX_READ_BACK)


@case_admin_router.post("/evidence", dependencies=[_guard("evidence.add")])
async def add_case_evidence(request: Request, body: EvidenceBody):
    from .correction import AddEvidenceCommand, add_evidence
    from .domain import EvidenceLevel

    try:
        record = add_evidence(
            AddEvidenceCommand(
                case_id=body.case_id, item_id=body.item_id,
                level=EvidenceLevel(body.level), source_scope=body.source_scope,
                source_ref=body.source_ref, descriptor={}, content=body.content,
                actor=_actor(request), observed_at=body.observed_at,
                effective_at=body.effective_at, expires_at=body.expires_at,
                asserted_value=body.asserted_value,
            ),
            now=_now(),
        )
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    # The identifier and its classification, never the payload back again.
    return {"evidence_id": record.evidence_id, "level": str(record.level),
            "source_scope": record.source_scope}


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: StrictStr
    item_id: StrictStr
    outcome_code: StrictStr
    reason_code: StrictStr = Field(max_length=200)
    risk_class: StrictStr
    reviewer_ref: StrictStr | None = Field(default=None, max_length=200)


@case_admin_router.post("/decisions", dependencies=[_guard("item.decide")])
async def decide_case_item(request: Request, body: DecisionBody):
    from .correction import DecideItemCommand, decide_item, load_evidence_records
    from .domain import CorrectionOutcome, RiskClass

    try:
        # Read the evidence back out of storage rather than trusting the caller
        # to say what supported their own ruling.
        evidence = load_evidence_records(body.case_id, body.item_id)
        outcome = decide_item(
            DecideItemCommand(
                case_id=body.case_id, item_id=body.item_id,
                outcome_code=CorrectionOutcome(body.outcome_code),
                reason_code=body.reason_code, evidence=evidence,
                risk_class=RiskClass(body.risk_class), actor=_actor(request),
                reviewer_ref=body.reviewer_ref,
            ),
            now=_now(),
        )
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return {"item_id": outcome.item_id, "outcome_code": str(outcome.outcome_code),
            "reason_code": outcome.reason_code}


class BuildChangeSetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: StrictStr
    item_ids: tuple[StrictStr, ...]
    expected_revision: StrictInt
    evidence_refs: tuple[StrictStr, ...]


@case_admin_router.post("/change-sets", dependencies=[_guard("changeset.build")])
async def build_case_change_set(request: Request, body: BuildChangeSetBody):
    from .correction import build_change_set

    try:
        draft = build_change_set(
            body.case_id, tuple(body.item_ids), _actor(request), body.expected_revision,
            evidence_refs=tuple(body.evidence_refs), now=_now(),
        )
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return {"case_id": draft.case_id, "entity_id": draft.entity_id,
            "risk_class": draft.risk_class, "apply_status": draft.apply_status}


class VerifyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: StrictStr
    change_set_id: StrictStr


@case_admin_router.post("/change-sets/verify", dependencies=[_guard("changeset.verify")])
async def verify_case_projection(request: Request, body: VerifyBody):
    from .publication import VerifyProjectionCommand, verify_public_projection

    fetcher = _PROJECTION_FETCHER
    if fetcher is None:
        # Refusing is not the same as a failed check. A failed check escalates and
        # tells the reporter their correction may not be visible; a missing
        # fetcher means we never looked, and must not be recorded as if we had.
        raise HTTPException(503, detail={
            "code": "verification_fetcher_unconfigured",
            "detail": "No public projection reader is configured.",
        })
    try:
        result = verify_public_projection(
            VerifyProjectionCommand(case_id=body.case_id, change_set_id=body.change_set_id,
                                    actor=_actor(request)),
            fetcher, now=_now(),
        )
    except Exception as error:  # noqa: BLE001
        raise _fail(error) from error
    return {"change_set_id": result.change_set_id, "verified": result.verified,
            "state": str(result.state), "mismatches": list(result.mismatches),
            "next_update_at": result.next_update_at.isoformat()
            if result.next_update_at else None}
