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
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictBool, ValidationError, field_validator

from .domain import PublicCaseStatus
from .security import CaseCrypto

# Deliberately not named `router`: the standards resolver matches an imported
# alias by its original symbol name, so a second module exporting `router`
# makes every such import ambiguous and silently unmounts the other one.
case_public_router = APIRouter(prefix="/api/cases", tags=["cases"])

ACCESS_COOKIE = "vl360_case_access"
CSRF_COOKIE = "vl360_case_csrf"
PROBLEM_MEDIA_TYPE = "application/problem+json"
_PROBLEM_BASE = "https://vinhlong360.vn/problems/"
_NO_STORE = {"Cache-Control": "no-store"}

_SERVICE = None
_SETTINGS = None
_ALLOWED_ORIGIN = None


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
    settings = _settings()
    if not getattr(settings, "CASE_KERNEL_ENABLED", False):
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
            validate_payload(
                "correction-intake",
                {
                    "reported_value_known": item.reported_value_known,
                    "reported_value": item.reported_value,
                },
                version=version,
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

    @field_validator("reported_value")
    @classmethod
    def _validate_reported_value_contract(cls, value: object | None, info) -> object | None:
        known = info.data.get("reported_value_known")
        if known is False:
            if value is not None:
                raise ValueError("reported_value must be null when current value is unknown")
            return value
        if known is True and (
            type(value) is not str
            or not value.strip()
            or len(value) > 2000
        ):
            raise ValueError("reported value must be a non-blank string")
        return value


class _CreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_ItemIn] = Field(min_length=1, max_length=10)
    reporter_privacy: str = Field(alias="reporterPrivacy", pattern="^(anonymous|attributed)$")
    optional_phone: str | None = Field(default=None, alias="optionalPhone", max_length=32)
    notification_consent: bool = Field(default=False, alias="notificationConsent")
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


class _ContactVerifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=16)


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


# ── Routes ──

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
        return _problem(
            422,
            exc.code,
            exc.detail,
            correlation_id=request.headers.get("x-request-id"),
        )
    body, invalid = await _model(request, _CreateIn)
    if invalid is not None:
        return invalid
    contract_error = _validate_correction_contract(body.items, request, version=version)
    if contract_error is not None:
        return contract_error

    try:
        result = _service().create_correction_from_transport(
            body,
            idempotency_key=idempotency_key,
            correlation_id=request.headers.get("x-request-id") or uuid.uuid4().hex,
            rate_subject=_rate_subject(request),
        )
    except Exception as exc:  # noqa: BLE001 - mapped or re-raised below
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    if not result.replayed:
        # A replay is the same arrival answered twice, not a second arrival.
        from . import metrics as _metrics

        _metrics.observe("received", channel="web", case_id=result.case_id)
    return JSONResponse(
        {
            "publicReference": result.public_reference,
            "capability": result.capability,
            "receivedAt": result.received_at.isoformat(),
            "nextUpdateAt": result.next_update_at.isoformat(),
            "replayed": result.replayed,
        },
        status_code=201,
        headers=dict(_NO_STORE),
    )


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


@case_public_router.get("/status")
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
    return JSONResponse(status_payload(status), headers=dict(_NO_STORE))


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
    for name in (ACCESS_COOKIE, CSRF_COOKIE):
        response.set_cookie(key=name, value="", max_age=0, path="/api/cases", samesite="lax")
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


@case_public_router.post("/contact/request")
async def request_contact_verification(request: Request):
    blocked = _guard_session_mutation(request)
    if blocked is not None:
        return blocked
    body, invalid = await _model(request, _ContactRequestIn)
    if invalid is not None:
        return invalid
    try:
        # Ra khỏi event loop. Route này là route công khai DUY NHẤT gọi ra
        # ngoài mạng: EsmsProvider.send thử 3 lần, mỗi lần total_timeout 20s,
        # xen time.sleep(0.5) và time.sleep(1.0) — tối đa ~61,5 giây. Gọi thẳng
        # trong async handler thì một POST đóng băng CẢ vl-agent, không riêng
        # luồng đính chính. sms_provider.send_async đã tồn tại đúng vì lý do đó
        # ("offloaded so an event loop is never blocked on the socket"), nhưng
        # đường này đi qua contact.py vốn đồng bộ, nên offload ở đây.
        await asyncio.to_thread(
            _service().request_contact_verification,
            access_token=request.cookies.get(ACCESS_COOKIE),
            phone=body.phone,
            consent=body.consent,
        )
    except ValueError as exc:
        if "invalid_contact_phone" not in str(exc):
            raise
        return _problem(400, "invalid_contact_phone", "That phone number is not usable.")
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    # 202, not 200: a code was queued, and the answer never reveals whether the
    # number exists or was reachable.
    return Response(status_code=202, headers=dict(_NO_STORE))


@case_public_router.post("/contact/verify")
async def verify_contact(request: Request):
    blocked = _guard_session_mutation(request)
    if blocked is not None:
        return blocked
    body, invalid = await _model(request, _ContactVerifyIn)
    if invalid is not None:
        return invalid
    try:
        _service().verify_contact(
            access_token=request.cookies.get(ACCESS_COOKIE), code=body.code
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_domain_error(exc)
        if mapped is None:
            raise
        return mapped
    return Response(status_code=204, headers=dict(_NO_STORE))
