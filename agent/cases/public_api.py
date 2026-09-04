"""Public `/api/cases` transport.

Everything a reporter can reach goes through here: create, exchange a receipt
for a short access session, read a safe status, rotate or drop the credential,
and ask for a review. The router owns transport concerns only — flag gating,
origin and content type, the double-submit CSRF check, cookie policy, cache
headers and RFC 9457 problem details — and never renders backstage state.
"""
from __future__ import annotations

import asyncio
import hmac
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictBool, ValidationError

if __package__ and __package__.startswith("agent."):
    from ..api_schemas import CaseStatusResponse, CorrectionIntakeContract
else:
    # The service is deployed with `agent/` on sys.path, so this is the
    # top-level spelling used by the production server and legacy adapter.
    from api_schemas import CaseStatusResponse, CorrectionIntakeContract

from .domain import PublicCaseStatus
from .security import CaseCrypto, CaseSecurityError

# Deliberately not named `router`: the standards resolver matches an imported
# alias by its original symbol name, so a second module exporting `router`
# makes every such import ambiguous and silently unmounts the other one.
case_public_router = APIRouter(prefix="/api/cases", tags=["cases"])

ACCESS_COOKIE = "vl360_case_access"
CSRF_COOKIE = "vl360_case_csrf"
PROBLEM_MEDIA_TYPE = "application/problem+json"
_PROBLEM_BASE = "https://vinhlong360.vn/problems/"
_NO_STORE = {"Cache-Control": "no-store"}
_CONTACT_RECEIPT_RE = re.compile(r"^[A-Za-z0-9_-]{8,512}={0,2}$")

_SERVICE = None
_SETTINGS = None
_ALLOWED_ORIGIN = None


def _uuid_receipt(value: str) -> str | None:
    """Legacy case-bound challenges are UUIDs; reject junk before PostgreSQL."""
    try:
        return str(uuid.UUID(value))
    except (AttributeError, ValueError, TypeError):
        return None


def configure_case_public_api(*, service=None, settings=None, allowed_origin=None) -> None:
    """Inject the collaborators; unset values fall back to the real configuration."""
    global _SERVICE, _SETTINGS, _ALLOWED_ORIGIN
    _SERVICE = service
    _SETTINGS = settings
    _ALLOWED_ORIGIN = allowed_origin


def _settings():
    if _SETTINGS is not None:
        return _SETTINGS
    from config import settings

    return settings


def _service():
    if _SERVICE is None:
        raise RuntimeError("case_service_not_configured")
    return _SERVICE


def _allowed_origin() -> str | None:
    if _ALLOWED_ORIGIN is not None:
        return _ALLOWED_ORIGIN
    return getattr(_settings(), "PUBLIC_SITE_ORIGIN", None)


def _production() -> bool:
    return bool(getattr(_settings(), "IS_PRODUCTION", False))


# ── Problem details ──

def _problem(
    status: int,
    code: str,
    detail: str,
    *,
    title: str | None = None,
    field: str | None = None,
    correlation_id: str | None = None,
    retry_after: int | None = None,
) -> JSONResponse:
    """RFC 9457 shape. Never echoes a credential, a value, or backstage state."""
    try:
        from control_plane.contracts import problem_detail
    except ModuleNotFoundError:  # package import (`agent.cases`) in tooling/tests
        from agent.control_plane.contracts import problem_detail

    correlation_id = correlation_id or uuid.uuid4().hex
    body = problem_detail(code, detail, status, field=field, correlation_id=correlation_id)
    if title:
        body["title"] = title
    # Keep request_id as a compatibility alias while all new consumers use the
    # explicit correlation_id field.
    body["request_id"] = correlation_id
    if retry_after is not None:
        body["retry_after"] = max(0, int(retry_after))
    return JSONResponse(
        body,
        status_code=status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=dict(_NO_STORE),
    )


_UNAVAILABLE = ("capability_unavailable", "This capability is not available.")
_CREDENTIAL = ("invalid_case_credential", "That credential is not valid.")


def _unavailable() -> JSONResponse:
    # Deliberately 404, not 403: a disabled capability must not advertise itself.
    return _problem(404, *_UNAVAILABLE)


# ── Guards ──

def _kernel_ready(*, intake: bool = False) -> bool:
    from .wiring import case_kernel_ready

    settings = _settings()
    if not getattr(settings, "CASE_KERNEL_ENABLED", False):
        return False
    if not case_kernel_ready():
        return False
    return not intake or bool(getattr(settings, "CORRECTION_INTAKE_ENABLED", False))


def _same_origin(request: Request) -> bool:
    allowed = _allowed_origin()
    origin = request.headers.get("origin")
    site = request.headers.get("sec-fetch-site")
    if site is not None and site != "same-origin":
        return False
    if origin is None:
        return site == "same-origin"
    return allowed is not None and hmac.compare_digest(origin, allowed)


def _json_request(request: Request) -> bool:
    media = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    return media == "application/json"


def _csrf_matches(request: Request) -> bool:
    """Double submit at the transport edge; the HMAC binding is checked deeper."""
    header = request.headers.get("x-case-csrf") or ""
    cookie = request.cookies.get(CSRF_COOKIE) or ""
    return bool(header) and bool(cookie) and hmac.compare_digest(header, cookie)


def _guard_public_post(request: Request, *, intake: bool) -> JSONResponse | None:
    if not _kernel_ready(intake=intake):
        return _unavailable()
    if not _json_request(request):
        return _problem(415, "unsupported_media_type", "Send JSON.")
    if not _same_origin(request):
        return _problem(403, "origin_not_allowed", "This request came from another site.")
    return None


def _guard_session_mutation(request: Request) -> JSONResponse | None:
    if not _kernel_ready():
        return _unavailable()
    if not _same_origin(request):
        return _problem(403, "origin_not_allowed", "This request came from another site.")
    if not request.cookies.get(ACCESS_COOKIE):
        return _problem(401, *_CREDENTIAL)
    if not _csrf_matches(request):
        return _problem(403, *_CREDENTIAL)
    return None


async def _model(request: Request, model: type[BaseModel]):
    try:
        return model.model_validate(await request.json()), None
    except ValidationError as exc:
        errors = exc.errors()
        loc = errors[0].get("loc", ()) if errors else ()
        field = ".".join(str(part) for part in loc) or None
        return None, _problem(
            422,
            "invalid_request",
            "That request body is not accepted.",
            field=field,
            correlation_id=request.headers.get("x-request-id"),
        )
    except (ValueError, TypeError):
        return None, _problem(400, "invalid_request", "That request body is not readable.")


def _validate_shared_correction_payload(
    payload: dict[str, object],
    *,
    version: str,
    validate_payload,
    contract_violation,
) -> None:
    """Run the Pydantic contract, retaining registry error semantics."""
    try:
        # Keep the Pydantic contract in the production path. The registry
        # remains the stable error-code adapter for the transport.
        CorrectionIntakeContract.model_validate(payload)
    except ValidationError as exc:
        try:
            validate_payload("correction-intake", payload, version=version)
        except contract_violation as registry_exc:
            raise registry_exc
        error = exc.errors()[0] if exc.errors() else {}
        raise contract_violation(
            str(error.get("msg") or "correction intake contract is invalid"),
            field="reported_value",
        ) from exc
    validate_payload("correction-intake", payload, version=version)


def _validate_correction_contract(items, request: Request, *, version: str = "1") -> JSONResponse | None:
    """Validate each item against the shared registry before service mutation."""
    try:
        try:
            from control_plane.contracts import ContractViolation, validate_payload
        except ModuleNotFoundError:
            from agent.control_plane.contracts import ContractViolation, validate_payload
        for index, item in enumerate(items):
            fields_set = set(getattr(item, "model_fields_set", ()))
            reported_known_present = bool(
                {"reported_value_known", "reportedValueKnown"} & fields_set
            )
            reported_value_present = bool(
                {"reported_value", "reportedValue"} & fields_set
            )
            # The versioned transport requires the discriminator explicitly;
            # header-less legacy callers retain the historical default.
            if request.headers.get("x-correction-contract-version") is not None and not reported_known_present:
                raise ContractViolation(
                    "missing required contract field: reported_value_known",
                    field="reportedValueKnown",
                )
            # `None` is meaningful only when it was sent. A defaulted value
            # must not turn an omitted `reportedValue` into an unknown value.
            if not reported_value_present and (
                request.headers.get("x-correction-contract-version") is not None
                or reported_known_present
            ):
                raise ContractViolation(
                    "missing required contract field: reported_value",
                    field="reported_value",
                )
            payload = {
                "reported_value_known": item.reported_value_known,
                "reported_value": item.reported_value,
            }
            _validate_shared_correction_payload(
                payload,
                version=version,
                validate_payload=validate_payload,
                contract_violation=ContractViolation,
            )
    except ContractViolation as exc:
        field_name = {
            "reported_value": "reportedValue",
            "reported_value_known": "reportedValueKnown",
        }.get(exc.field or "", exc.field)
        return _problem(
            422,
            exc.code,
            exc.detail,
            field=f"items.{index}.{field_name}" if field_name else f"items.{index}",
            correlation_id=request.headers.get("x-request-id"),
        )
    return None


def _rate_subject(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _map_domain_error(exc: Exception) -> JSONResponse | None:
    """Domain failures become problem documents, never tracebacks or 500s."""
    from .security import CaseSecurityError
    from .contact import ContactDeliveryUnavailable
    from .service import CorrectionRejected, IdempotencyConflict, SafetyRoutingRequired
    from .store import CaseNotFound

    if isinstance(exc, SafetyRoutingRequired):
        # The safe routing copy is the whole point of this answer, so it is the
        # detail; it names the emergency services and no case is created.
        return _problem(exc.problem.status, exc.problem.code, exc.safe_message)
    if isinstance(exc, (CorrectionRejected, IdempotencyConflict)):
        return _problem(exc.problem.status, exc.problem.code, exc.problem.detail)
    if isinstance(exc, CaseSecurityError):
        # One shape for invalid, expired, revoked and unknown alike: a reporter
        # must not be able to probe which case references exist.
        return _problem(403, *_CREDENTIAL)
    if isinstance(exc, ContactDeliveryUnavailable):
        return _problem(503, "contact_verification_unavailable", "Chưa gửi được mã xác nhận. Vui lòng thử lại sau ít phút.", retry_after=30)
    if isinstance(exc, CaseNotFound):
        return _problem(404, *_CREDENTIAL)
    return None



# ── Request models: documented JSON names only, nothing extra ──

class _ItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(alias="entityId", min_length=1, max_length=128)
    field_path: str = Field(alias="fieldPath", min_length=1, max_length=128)
    reported_value_known: StrictBool = Field(
        default=True,
        validation_alias=AliasChoices("reportedValueKnown", "reported_value_known"),
    )
    reported_value: object | None = Field(
        default=None,
        validation_alias=AliasChoices("reportedValue", "reported_value"),
    )
    proposed_value: str = Field(alias="proposedValue", min_length=1, max_length=2000)
    base_entity_revision: int = Field(alias="baseEntityRevision", ge=1)


class _CreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_ItemIn] = Field(min_length=1, max_length=10)
    reporter_privacy: str = Field(alias="reporterPrivacy", pattern="^(anonymous|attributed)$")
    optional_phone: str | None = Field(default=None, alias="optionalPhone", max_length=32)
    notification_consent: bool = Field(default=False, alias="notificationConsent")
    contact_receipt: str | None = Field(default=None, alias="contactReceipt", max_length=512)
    handoff_digest: str | None = Field(
        default=None, alias="handoffDigest", min_length=64, max_length=64
    )
    handoff_confirmed: bool = Field(default=False, alias="handoffConfirmed")


class _AccessIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_reference: str = Field(alias="publicReference", min_length=1, max_length=32)
    capability: str = Field(min_length=1, max_length=64)


class _ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)
    expected_revision: int = Field(alias="expectedRevision", ge=1)


class _ContactRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(min_length=1, max_length=32)
    # Withdrawal has to be as reachable as consent. The domain has always
    # supported consent=False — it leaves no live challenge and no verified
    # contact — but the route hardcoded True and this model forbade the field,
    # so a reporter who had given their number had no way to take it back.
    # The privacy policy promises exactly that within 15 days.
    consent: bool = True
    # Pre-case withdrawal must present the opaque receipt issued by /start;
    # phone alone is not an ownership proof.
    receipt: str | None = Field(default=None, max_length=512)


class _ContactVerifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=16)
    receipt: str | None = Field(default=None, max_length=512)


# ── Response shaping ──

def status_payload(status: PublicCaseStatus) -> dict[str, object]:
    """Exactly the locked public fields, in the frontend's camelCase contract."""
    return {
        "publicReference": status.public_reference,
        "receivedAt": status.received_at.isoformat(),
        "currentStep": status.current_step,
        "waitingFor": status.waiting_for,
        "nextAction": status.next_action,
        "nextUpdateAt": status.next_update_at.isoformat(),
        "promiseHealth": status.promise_health.value,
        "itemDecisions": [
            {
                "itemId": decision.item_id,
                "outcome": decision.outcome,
                "dispositionFamily": decision.disposition_family.value,
            }
            for decision in status.item_decisions
        ],
        "itemPublicationStates": [
            {"itemId": entry.item_id, "state": entry.state.value}
            for entry in status.item_publication_states
        ],
        "reviewPath": status.review_path,
        # POST /review đòi `expectedRevision` và model FORBID extra + không có
        # default → thiếu là 422. Trước 2026-08-30 payload này không phát ra con
        # số đó ở bất kỳ đâu, nên nút "xin xét lại" hỏng 100% lượt và người báo
        # bị FE dịch thành "mã tra cứu sai".
        "currentRevision": status.current_revision,
    }


def _set_session_cookies(response: Response, access_token: str, csrf_token: str) -> None:
    production = _production()
    response.set_cookie(**CaseCrypto.case_access_cookie(access_token, production=production))
    response.set_cookie(**CaseCrypto.case_csrf_cookie(csrf_token, production=production))


def _clear_session_cookies(response: Response) -> None:
    """Expire case cookies with the same path and security flags used on issue."""
    production = _production()
    for name, httponly in ((ACCESS_COOKIE, True), (CSRF_COOKIE, False)):
        response.delete_cookie(
            key=name,
            path="/api/cases",
            secure=production,
            httponly=httponly,
            samesite="lax",
        )


# ── Routes ──

async def _parse_correction_intake(request: Request, version: str):
    body, invalid = await _model(request, _CreateIn)
    if invalid is not None:
        return None, invalid
    contract_error = _validate_correction_contract(body.items, request, version=version)
    if contract_error is not None:
        return None, contract_error
    if body.contact_receipt is not None and not _CONTACT_RECEIPT_RE.fullmatch(body.contact_receipt):
        return None, _problem(
            422,
            "invalid_contact_receipt",
            "Mã xác nhận không hợp lệ hoặc đã hết hạn.",
            field="contactReceipt",
            retry_after=0,
        )
    return body, None


def _create_correction_service_result(request: Request, body, idempotency_key: str):
    try:
        return _service().create_correction_from_transport(
            body,
            idempotency_key=idempotency_key,
            correlation_id=request.headers.get("x-request-id") or uuid.uuid4().hex,
            rate_subject=_rate_subject(request),
        ), None
    except Exception as exc:  # noqa: BLE001 - mapped or re-raised below
        if getattr(exc, "problem", None) is not None and exc.problem.code == "phone_verification_required":
            return None, _problem(
                422,
                exc.problem.code,
                exc.problem.detail,
                field="optionalPhone",
                retry_after=0,
                correlation_id=request.headers.get("x-request-id"),
            )
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return None, mapped


def _correction_response(result):
    from . import metrics as _metrics

    if not result.replayed:
        _metrics.observe("received", channel="web", case_id=result.case_id)
    response_payload = {
        "publicReference": result.public_reference,
        "capability": result.capability,
        "receivedAt": result.received_at.isoformat(),
        "nextUpdateAt": result.next_update_at.isoformat(),
        "replayed": result.replayed,
    }
    if getattr(result, "revision", None) is not None:
        response_payload["revision"] = result.revision
    if getattr(result, "outbox_event_id", None) is not None:
        response_payload["outboxEventId"] = result.outbox_event_id
    return JSONResponse(response_payload, status_code=201, headers=dict(_NO_STORE))


@case_public_router.post("/corrections")
async def create_correction(request: Request):
    blocked = _guard_public_post(request, intake=True)
    if blocked is not None:
        return blocked
    idempotency_key = request.headers.get("idempotency-key")
    if not idempotency_key:
        return _problem(400, "idempotency_key_required", "Send an Idempotency-Key header.")
    version = request.headers.get("x-correction-contract-version", "1")
    try:
        try:
            from control_plane.contracts import ContractViolation, get_contract
        except ModuleNotFoundError:
            from agent.control_plane.contracts import ContractViolation, get_contract
        get_contract("correction-intake", version)
    except ContractViolation as exc:
        return _problem(422, exc.code, exc.detail, correlation_id=request.headers.get("x-request-id"))
    body, invalid = await _parse_correction_intake(request, version)
    if invalid is not None:
        return invalid
    result, mapped = _create_correction_service_result(request, body, idempotency_key)
    if mapped is not None:
        return mapped
    return _correction_response(result)


@case_public_router.post("/access")
async def exchange_receipt(request: Request):
    blocked = _guard_public_post(request, intake=False)
    if blocked is not None:
        return blocked
    body, invalid = await _model(request, _AccessIn)
    if invalid is not None:
        return invalid

    try:
        grant = _service().exchange_receipt(
            public_reference=body.public_reference,
            capability=body.capability,
            rate_subject=_rate_subject(request),
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    response = Response(status_code=204, headers=dict(_NO_STORE))
    _set_session_cookies(response, grant.access_token, grant.csrf_token)
    return response


@case_public_router.get("/status", response_model=CaseStatusResponse)
async def read_status(request: Request):
    if not _kernel_ready():
        return _unavailable()
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        return _problem(401, *_CREDENTIAL)
    try:
        status = _service().public_status(access_token=token)
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    payload = CaseStatusResponse.model_validate(status_payload(status))
    return JSONResponse(
        payload.model_dump(mode="json", by_alias=True),
        headers=dict(_NO_STORE),
    )


@case_public_router.post("/receipts/rotate")
async def rotate_receipt(request: Request):
    blocked = _guard_session_mutation(request)
    if blocked is not None:
        return blocked
    try:
        grant = _service().rotate_receipt(
            access_token=request.cookies.get(ACCESS_COOKIE),
            rate_subject=_rate_subject(request),
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    return JSONResponse(
        {"publicReference": grant.public_reference, "capability": grant.capability},
        headers=dict(_NO_STORE),
    )


@case_public_router.delete("/access")
async def revoke_access(request: Request):
    blocked = _guard_session_mutation(request)
    if blocked is not None:
        return blocked
    try:
        _service().revoke_access(access_token=request.cookies.get(ACCESS_COOKIE))
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    response = Response(status_code=204, headers=dict(_NO_STORE))
    _clear_session_cookies(response)
    return response


@case_public_router.post("/review")
async def open_review(request: Request):
    blocked = _guard_session_mutation(request)
    if blocked is not None:
        return blocked
    body, invalid = await _model(request, _ReviewIn)
    if invalid is not None:
        return invalid

    try:
        review = _service().open_review(
            access_token=request.cookies.get(ACCESS_COOKIE),
            reason=body.reason,
            expected_revision=body.expected_revision,
            rate_subject=_rate_subject(request),
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    return JSONResponse(
        {"publicReference": review.public_reference, "capability": review.capability},
        status_code=201,
        headers=dict(_NO_STORE),
    )


async def _start_contact_verification(request: Request, *, pre_case: bool | None = None):
    # The new start route is always anonymous/pre-case. Do not let a stale or
    # attacker-supplied access cookie change its authentication lane.
    has_access = bool(request.cookies.get(ACCESS_COOKIE)) if pre_case is None else not pre_case
    blocked = _guard_session_mutation(request) if has_access else _guard_public_post(request, intake=True)
    if blocked is not None:
        return blocked
    body, invalid = await _model(request, _ContactRequestIn)
    if invalid is not None:
        return invalid
    if body.receipt is not None and not _CONTACT_RECEIPT_RE.fullmatch(body.receipt):
        return _problem(
            422,
            "invalid_contact_receipt",
            "Mã xác nhận không hợp lệ hoặc đã hết hạn.",
            field="receipt",
            retry_after=0,
        )
    if pre_case and not body.consent and not body.receipt:
        # A phone number is not enough to identify which pending challenge the
        # caller owns. Require the opaque proof before touching any row.
        return _problem(401, *_CREDENTIAL)
    challenge, error = await _request_contact_challenge(request, body, has_access)
    if error is not None:
        return error
    return _contact_challenge_response(challenge)


async def _request_contact_challenge(request: Request, body, has_access: bool):
    try:
        # Ra khỏi event loop. Route này là route công khai DUY NHẤT gọi ra
        # ngoài mạng: EsmsProvider.send thử 3 lần, mỗi lần total_timeout 20s,
        # xen time.sleep(0.5) và time.sleep(1.0) — tối đa ~61,5 giây. Gọi thẳng
        # trong async handler thì một POST đóng băng CẢ vl-agent, không riêng
        # luồng đính chính. sms_provider.send_async đã tồn tại đúng vì lý do đó
        # ("offloaded so an event loop is never blocked on the socket"), nhưng
        # đường này đi qua contact.py vốn đồng bộ, nên offload ở đây.
        if has_access:
            challenge = await asyncio.to_thread(
                _service().request_contact_verification,
                access_token=request.cookies.get(ACCESS_COOKIE),
                phone=body.phone,
                consent=body.consent,
            )
        else:
            challenge = await asyncio.to_thread(
                _service().request_pre_case_contact_verification,
                phone=body.phone,
                consent=body.consent,
                receipt=body.receipt,
                requester_subject=_rate_subject(request),
            )
    except ValueError as exc:
        if "invalid_contact_phone" not in str(exc):
            raise
        return None, _problem(400, "invalid_contact_phone", "That phone number is not usable.", field="phone")
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return None, mapped
    return challenge, None


def _contact_challenge_response(challenge):
    # The opaque challenge receipt binds the next verify call to this start;
    # it contains no case id, owner key, phone number or raw correlation id.
    if challenge is None:
        return Response(status_code=202, headers=dict(_NO_STORE))
    expires_at = getattr(challenge, "expires_at", None)
    return JSONResponse(
        {
            "receipt": str(getattr(challenge, "challenge_id", "")),
            "expiresAt": expires_at.isoformat() if expires_at is not None else "",
            "retryAfter": 60,
            "verified": False,
        },
        status_code=202,
        headers=dict(_NO_STORE),
    )


@case_public_router.post("/contact/start")
async def start_contact_verification(request: Request):
    return await _start_contact_verification(request, pre_case=True)


@case_public_router.post("/contact/request")
async def request_contact_verification(request: Request):
    # Legacy route retained for existing clients; the new start route exposes
    # the opaque receipt needed to bind a verify attempt to its challenge.
    # Preserve the caller's explicit consent choice; `_start_contact_verification`
    # passes it onward as `consent=body.consent` rather than assuming approval.
    blocked = _guard_session_mutation(request)
    if blocked is not None:
        return blocked
    result = await _start_contact_verification(request, pre_case=False)
    if isinstance(result, JSONResponse) and result.status_code == 202:
        return Response(status_code=202, headers=dict(_NO_STORE))
    return result


@case_public_router.post("/contact/verify")
async def verify_contact(request: Request):
    has_access = bool(request.cookies.get(ACCESS_COOKIE))
    # Check transport prerequisites before parsing the body, but defer the
    # authentication lane until receipt shape is known. A stale access cookie
    # must not turn an opaque pre-case receipt into a legacy UUID challenge.
    blocked = _guard_public_post(request, intake=False)
    if blocked is not None:
        return blocked
    body, invalid = await _model(request, _ContactVerifyIn)
    if invalid is not None:
        return invalid
    use_access, blocked = _contact_verify_lane(request, body, has_access)
    if blocked is not None:
        return blocked
    verified, verified_receipt, error = _perform_contact_verification(request, body, use_access)
    if error is not None:
        return error
    return _verified_contact_response(use_access, verified_receipt)


def _contact_verify_lane(request: Request, body, has_access: bool):
    legacy_receipt = _uuid_receipt(body.receipt) if body.receipt is not None else None
    use_access = (body.receipt is None and has_access) or legacy_receipt is not None
    blocked = _guard_session_mutation(request) if use_access else _guard_public_post(request, intake=True)
    if blocked is not None:
        return use_access, blocked
    malformed = body.receipt is not None and (
        not _CONTACT_RECEIPT_RE.fullmatch(body.receipt)
        or (use_access and legacy_receipt is None)
    )
    if malformed:
        return use_access, _problem(
            422,
            "invalid_contact_receipt",
            "Mã xác nhận không hợp lệ hoặc đã hết hạn.",
            field="receipt",
            retry_after=0,
        )
    return use_access, None


def _perform_contact_verification(request: Request, body, use_access: bool):
    try:
        if use_access:
            verified = _service().verify_contact(
                access_token=request.cookies.get(ACCESS_COOKIE), code=body.code,
                receipt=body.receipt,
            )
            verified_receipt = body.receipt or ""
        else:
            if not body.receipt:
                return None, None, _problem(401, *_CREDENTIAL)
            verified, verified_receipt = _service().verify_pre_case_contact(
                receipt=body.receipt, code=body.code,
            )
    except CaseSecurityError:
        return None, None, _problem(
            422,
            "invalid_contact_code",
            "Mã xác nhận không đúng hoặc đã hết hạn.",
            field="code",
            retry_after=30,
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return None, None, mapped
    return verified, verified_receipt, None


def _verified_contact_response(use_access: bool, verified_receipt: str):
    if use_access:
        return Response(status_code=204, headers=dict(_NO_STORE))
    try:
        verified_payload = _service()._crypto.open_contact_receipt(
            verified_receipt, now=datetime.now(timezone.utc)
        )
        expires_at = datetime.fromtimestamp(
            int(verified_payload["expires_at"]), tz=timezone.utc
        ).isoformat()
    except Exception:
        expires_at = ""
    return JSONResponse(
        {
            "receipt": verified_receipt,
            "expiresAt": expires_at,
            "retryAfter": 0,
            "verified": True,
        },
        headers=dict(_NO_STORE),
    )
