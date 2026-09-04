"""Transport contract for /api/cases: gating, credentials, headers, disclosure."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.domain import (  # noqa: E402
    DispositionFamily,
    PromiseHealth,
    PublicCaseStatus,
    PublicItemDecision,
    PublicItemPublication,
    PublicationState,
)
from cases.public_api import case_public_router, configure_case_public_api  # noqa: E402
from cases.service import CreateCorrectionResult  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
ORIGIN = "https://vinhlong360.vn"
CAPABILITY = "c" * 43
REFERENCE = "VL-COR-ABCDEFGHJKMN0"


class _ServiceDouble:
    def __init__(self) -> None:
        self.created = []
        self.rotated = []
        self.reviewed = []
        self.revoked = []
        self.revoke_threads = []
        self.contact_requests = []
        self.contact_request_threads = []
        self.contact_verifications = []
        self.pre_case_contact_requests = []

    def create_correction_from_transport(self, payload, **kwargs):
        self.created.append((payload, kwargs))
        return CreateCorrectionResult(
            case_id="11111111-1111-1111-1111-111111111111",
            public_reference=REFERENCE,
            capability=CAPABILITY,
            received_at=NOW,
            next_update_at=NOW + timedelta(days=3),
            replayed=False,
            revision=1,
            outbox_event_id="notify:11111111-1111-1111-1111-111111111111:received",
        )

    def exchange_receipt(self, **kwargs):
        return SimpleNamespace(access_token="a" * 43, csrf_token="b" * 43)

    def public_status(self, **kwargs):
        return PublicCaseStatus(
            public_reference=REFERENCE,
            received_at=NOW,
            current_step="checking",
            waiting_for=None,
            next_action="Chúng tôi đang đối chiếu thông tin bạn gửi.",
            next_update_at=NOW + timedelta(days=3),
            promise_health=PromiseHealth.ON_TRACK,
            item_decisions=(
                PublicItemDecision(
                    item_id="item-1", outcome=None,
                    disposition_family=DispositionFamily.UNDETERMINED,
                ),
            ),
            item_publication_states=(
                PublicItemPublication(item_id="item-1", state=PublicationState.NOT_REQUIRED),
            ),
            review_path="none",
            current_revision=7,
        )

    def rotate_receipt(self, **kwargs):
        self.rotated.append(kwargs)
        return SimpleNamespace(public_reference=REFERENCE, capability="d" * 43)

    def open_review(self, **kwargs):
        self.reviewed.append(kwargs)
        return SimpleNamespace(
            public_reference="VL-COR-REVIEW00000X", capability="e" * 43,
            case_id="22222222-2222-2222-2222-222222222222",
        )

    def revoke_access(self, **kwargs):
        import threading

        self.revoke_threads.append(threading.get_ident())
        self.revoked.append(kwargs)

    def request_contact_verification(self, **kwargs):
        import threading

        self.contact_request_threads.append(threading.get_ident())
        self.contact_requests.append(kwargs)

    def verify_contact(self, **kwargs):
        self.contact_verifications.append(kwargs)

    def request_pre_case_contact_verification(self, **kwargs):
        self.pre_case_contact_requests.append(kwargs)
        return SimpleNamespace(challenge_id="receipt-token", expires_at=NOW, delivery_key="")


def _flags(**overrides):
    base = dict(
        CASE_KERNEL_ENABLED=True,
        CORRECTION_INTAKE_ENABLED=True,
        CORRECTION_ADMIN_ENABLED=False,
        CORRECTION_ASSISTED_ENABLED=False,
        CORRECTION_PUBLICATION_ENABLED=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def client(request, monkeypatch):
    # These transport tests inject only the public collaborator; bypass the
    # composition-root latch so they can exercise validation independently.
    from cases import wiring

    monkeypatch.setattr(wiring, "case_kernel_ready", lambda: True)
    service = _ServiceDouble()
    flags = getattr(request, "param", None) or _flags()
    configure_case_public_api(service=service, settings=flags, allowed_origin=ORIGIN)
    app = FastAPI()
    app.include_router(case_public_router)
    with TestClient(app) as test_client:
        test_client.service = service
        yield test_client
    configure_case_public_api(service=None, settings=None, allowed_origin=None)


def _headers(**extra):
    base = {
        "Origin": ORIGIN,
        "Sec-Fetch-Site": "same-origin",
        "Content-Type": "application/json",
        "Idempotency-Key": "idem-1",
    }
    base.update(extra)
    return base


def _body():
    return {
        "items": [
            {
                "entityId": "p-vinh-long",
                "fieldPath": "attributes.phone",
                "reportedValue": "0270 111 2222",
                "proposedValue": "0270 333 4444",
                "baseEntityRevision": 7,
            }
        ],
        "reporterPrivacy": "anonymous",
    }


def test_contact_verify_lane_rejects_access_cookie_with_opaque_receipt(client):
    from cases import public_api

    request = client.build_request(
        "POST",
        "/api/cases/contact/verify",
        headers=_headers(),
        cookies={public_api.ACCESS_COOKIE: "access-token"},
    )
    body = public_api._ContactVerifyIn(receipt="opaque-receipt", code="123456")

    use_access, blocked = public_api._contact_verify_lane(request, body, has_access=True)

    assert use_access is False
    assert blocked is None


# ── Flag gating ──

ROUTES = [
    ("post", "/api/cases/corrections"),
    ("post", "/api/cases/access"),
    ("get", "/api/cases/status"),
    ("post", "/api/cases/receipts/rotate"),
    ("delete", "/api/cases/access"),
    ("post", "/api/cases/review"),
    ("post", "/api/cases/contact/request"),
    ("post", "/api/cases/contact/verify"),
]


@pytest.mark.parametrize("client", [_flags(CASE_KERNEL_ENABLED=False)], indirect=True)
@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_every_route_is_invisible_while_the_kernel_flag_is_off(client, method, path):
    response = client.request(method.upper(), path, headers=_headers(), json={})

    assert response.status_code == 404
    assert response.json()["code"] == "capability_unavailable"


@pytest.mark.parametrize("client", [_flags(CORRECTION_INTAKE_ENABLED=False)], indirect=True)
def test_intake_is_invisible_while_the_intake_flag_is_off(client):
    response = client.post("/api/cases/corrections", headers=_headers(), json=_body())

    assert response.status_code == 404
    assert response.json()["code"] == "capability_unavailable"


# ── Create ──

def test_create_returns_the_one_time_capability_and_never_caches_it(client):
    response = client.post("/api/cases/corrections", headers=_headers(), json=_body())

    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    payload = response.json()
    assert payload["publicReference"] == REFERENCE
    assert payload["capability"] == CAPABILITY
    assert payload["replayed"] is False
    assert payload["revision"] == 1
    assert payload["outboxEventId"].endswith(":received")
    # The capability must never be handed back through a URL or a cookie.
    assert CAPABILITY not in str(response.headers)


@pytest.mark.parametrize(
    ("header", "value"),
    [("Origin", "https://evil.example"), ("Sec-Fetch-Site", "cross-site"),
     ("Content-Type", "text/plain")],
)
def test_create_rejects_a_wrong_origin_site_or_content_type(client, header, value):
    response = client.post(
        "/api/cases/corrections", headers=_headers(**{header: value}), content="{}"
    )

    assert response.status_code in {400, 403, 415}
    assert response.json()["code"] in {
        "origin_not_allowed", "unsupported_media_type", "invalid_request",
    }


def test_create_refuses_unknown_json_fields(client):
    body = _body()
    body["ownerRef"] = "person:someone"

    response = client.post("/api/cases/corrections", headers=_headers(), json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_create_requires_an_idempotency_key_header(client):
    headers = _headers()
    del headers["Idempotency-Key"]

    response = client.post("/api/cases/corrections", headers=headers, json=_body())

    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


@pytest.mark.parametrize("bad_value", ["false", 0, 1, "0"])
def test_create_rejects_non_boolean_reported_value_discriminator_before_service(client, bad_value):
    body = _body()
    body["items"][0]["reportedValueKnown"] = bad_value

    response = client.post(
        "/api/cases/corrections",
        headers=_headers(**{"X-Request-Id": "corr-strict-bool"}),
        json=body,
    )

    assert response.status_code == 422
    assert response.json()["field"] == "items.0.reportedValueKnown"
    assert response.json()["correlation_id"] == "corr-strict-bool"
    assert client.service.created == []


def test_create_preserves_reported_value_field_path_for_discriminator_mismatch(client):
    body = _body()
    body["items"][0].update({"reportedValueKnown": False, "reportedValue": "stale"})

    response = client.post(
        "/api/cases/corrections",
        headers=_headers(**{"X-Request-Id": "corr-field-path"}),
        json=body,
    )

    assert response.status_code == 422
    assert response.json()["field"] == "items.0.reportedValue"
    assert response.json()["correlation_id"] == "corr-field-path"
    assert client.service.created == []


def test_create_rejects_unsupported_contract_version(client):
    response = client.post(
        "/api/cases/corrections",
        headers=_headers(**{"X-Correction-Contract-Version": "999"}),
        json=_body(),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CONTRACT_INVALID"
    assert client.service.created == []


def test_create_requires_explicit_discriminator_when_version_header_is_present(client):
    body = _body()
    del body["items"][0]["reportedValue"]

    response = client.post(
        "/api/cases/corrections",
        headers=_headers(**{"X-Correction-Contract-Version": "1"}),
        json=body,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CONTRACT_INVALID"
    assert response.json()["field"] == "items.0.reportedValueKnown"


def test_create_rejects_missing_reported_value_for_versioned_unknown_item(client):
    body = _body()
    body["items"][0]["reportedValueKnown"] = False
    del body["items"][0]["reportedValue"]

    response = client.post(
        "/api/cases/corrections",
        headers=_headers(**{"X-Correction-Contract-Version": "1"}),
        json=body,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CONTRACT_INVALID"
    assert response.json()["field"] == "items.0.reportedValue"
    assert client.service.created == []


def test_create_rejects_missing_current_value_with_contract_error(client):
    body = _body()
    del body["items"][0]["reportedValue"]

    response = client.post(
        "/api/cases/corrections", headers=_headers(), json=body,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CONTRACT_INVALID"
    assert response.json()["field"] == "items.0.reportedValue"


def test_create_invokes_the_shared_correction_schema_before_service(client, monkeypatch):
    import api_schemas

    calls = []
    original = api_schemas.CorrectionIntakeContract.model_validate

    def spy(cls, value, *args, **kwargs):
        calls.append(value)
        return original(value, *args, **kwargs)

    monkeypatch.setattr(
        api_schemas.CorrectionIntakeContract,
        "model_validate",
        classmethod(spy),
    )

    response = client.post("/api/cases/corrections", headers=_headers(), json=_body())

    assert response.status_code == 201
    assert calls == [{
        "reported_value_known": True,
        "reported_value": "0270 111 2222",
    }]
    assert len(client.service.created) == 1


# ── Access, status, logout ──

def test_access_sets_a_scoped_http_only_cookie_and_a_readable_csrf_cookie(client):
    response = client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )

    assert response.status_code == 204
    cookies = response.headers.get_list("set-cookie")
    access = next(value for value in cookies if value.startswith("vl360_case_access="))
    csrf = next(value for value in cookies if value.startswith("vl360_case_csrf="))
    # SameSite is case-insensitive per RFC 6265bis; Starlette emits it lowercase.
    assert "HttpOnly" in access and "Path=/api/cases" in access
    assert "samesite=lax" in access.lower()
    assert "Max-Age=900" in access
    assert "HttpOnly" not in csrf
    assert "Path=/api/cases" in csrf


def test_status_requires_the_access_cookie(client):
    assert client.get("/api/cases/status").status_code == 401


def test_status_publishes_only_safe_fields(client):
    client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )

    response = client.get("/api/cases/status")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    payload = response.json()
    assert set(payload) == {
        "publicReference", "receivedAt", "currentStep", "waitingFor", "nextAction",
        "nextUpdateAt", "promiseHealth", "itemDecisions", "itemPublicationStates",
        "reviewPath", "currentRevision",
    }
    # Con số này KHÔNG phải trang trí: POST /review đòi đúng nó ở `expectedRevision`.
    assert payload["currentRevision"] == 7
    rendered = response.text
    for forbidden in ("caseId", "ownerRef", "severity", "riskClass", "evidence",
                      "capabilityDigest", "auditEvent", "triage", "investigation"):
        assert forbidden not in rendered


def test_status_payload_matches_the_strict_public_response_contract(client):
    from api_schemas import CaseStatusResponse
    from pydantic import ValidationError

    client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )
    payload = client.get("/api/cases/status").json()

    parsed = CaseStatusResponse.model_validate(payload)
    assert parsed.model_dump(by_alias=True) == payload

    with pytest.raises(ValidationError):
        CaseStatusResponse.model_validate({**payload, "undocumented": "nope"})


def test_status_rejects_an_invalid_internal_projection(client, monkeypatch):
    from cases import public_api
    from pydantic import ValidationError

    original = public_api.status_payload
    monkeypatch.setattr(
        public_api,
        "status_payload",
        lambda status: {**original(status), "undocumented": "nope"},
    )

    client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )
    with pytest.raises(ValidationError):
        client.get("/api/cases/status")


def test_logout_clears_both_cookies(client):
    client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )

    response = client.delete(
        "/api/cases/access", headers=_headers(**{"X-Case-CSRF": "b" * 43})
    )

    assert response.status_code == 204
    cleared = " ".join(response.headers.get_list("set-cookie"))
    assert "vl360_case_access=" in cleared and "vl360_case_csrf=" in cleared
    assert cleared.count("Max-Age=0") >= 2


# ── CSRF on cookie-authenticated mutations ──

MUTATIONS = [
    ("post", "/api/cases/receipts/rotate", {}),
    ("delete", "/api/cases/access", None),
    ("post", "/api/cases/review", {"reason": "sai số điện thoại", "expectedRevision": 3}),
    ("post", "/api/cases/contact/request", {"phone": "0901234567"}),
    ("post", "/api/cases/contact/verify", {"code": "123456"}),
]


@pytest.mark.parametrize(("method", "path", "body"), MUTATIONS)
def test_cookie_mutations_refuse_a_caller_with_no_access_cookie(client, method, path, body):
    """Không đổi phiếu lấy phiên thì năm route này phải từ chối ngay ở cửa.

    Hai test dưới đã phủ "có phiên nhưng CSRF sai" và "có phiên nhưng khác origin";
    trường hợp gốc — KHÔNG có phiên nào cả — thì chưa ai khẳng định. Nó là mắt xích
    khiến `tests/test_api_surface_contract.py` nhìn năm route này như "ghi ẩn danh":
    chúng không dùng `require_user` (đúng, vì đính chính không cần tài khoản) mà
    dựa vào phiếu-năng-lực đổi ra cookie phiên. Ngoại lệ khai trong
    PUBLIC_WRITE_ALLOWLIST nói đúng điều đó, và đây là chỗ chứng minh nó không rỗng.
    """
    response = client.request(method.upper(), path, headers=_headers(), json=body)

    assert response.status_code == 401, (
        f"{method.upper()} {path} nhận yêu cầu không có cookie phiên"
    )
    assert response.json()["code"] == "invalid_case_credential"


@pytest.mark.parametrize(("method", "path", "body"), MUTATIONS)
def test_cookie_mutations_require_a_matching_csrf_header(client, method, path, body):
    client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )

    without = client.request(method.upper(), path, headers=_headers(), json=body)
    wrong = client.request(
        method.upper(), path, headers=_headers(**{"X-Case-CSRF": "z" * 43}), json=body
    )

    assert without.status_code == 403
    assert wrong.status_code == 403
    assert without.json()["code"] == "invalid_case_credential"


@pytest.mark.parametrize(("method", "path", "body"), MUTATIONS)
def test_cookie_mutations_require_a_same_origin_request(client, method, path, body):
    client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )

    response = client.request(
        method.upper(),
        path,
        headers=_headers(**{"X-Case-CSRF": "b" * 43, "Origin": "https://evil.example"}),
        json=body,
    )

    assert response.status_code == 403


# ── Problem details ──

def test_problem_details_carry_a_request_id_and_no_secret(client):
    response = client.post("/api/cases/corrections", headers=_headers(), json={})

    body = response.json()
    assert set(body) >= {"type", "title", "status", "detail", "code", "request_id"}
    assert body["request_id"]
    assert CAPABILITY not in response.text


# ── End to end against real PostgreSQL: the router wired to the real service ──





# One loopback-only rule for every suite that opens the disposable database.
from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402


@pytest.fixture
def live_client(monkeypatch):
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    import database
    from cases.policy import load_case_policy
    from cases.security import CaseCrypto
    from cases.service import CaseService
    from cases.store import PostgresCaseStore
    from cases import wiring

    monkeypatch.setattr(wiring, "case_kernel_ready", lambda: True)

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, revision) VALUES (%s,'place','Vĩnh Long',1)"
            " ON CONFLICT (id) DO NOTHING",
            ("p-vinh-long",),
        )
        adapter._execute(conn, "DELETE FROM shared_rate_limits WHERE key LIKE %s", ("case:%",))
        adapter._execute(
            conn, "DELETE FROM case_idempotency WHERE idempotency_key LIKE %s", ("create:%",)
        )
        conn.commit()

    service = CaseService(
        store=PostgresCaseStore(adapter),
        crypto=CaseCrypto("0" * 43),
        policy=load_case_policy(),
        owner_ref="person:case-owner",
        database=adapter,
    )
    configure_case_public_api(service=service, settings=_flags(), allowed_origin=ORIGIN)
    app = FastAPI()
    app.include_router(case_public_router)
    with TestClient(app) as client:
        client.database = adapter
        yield client
    configure_case_public_api(service=None, settings=None, allowed_origin=None)


@pg_only
def test_a_reporter_can_file_then_read_their_own_status(live_client):
    created = live_client.post(
        "/api/cases/corrections",
        headers=_headers(**{"Idempotency-Key": "e2e-1"}),
        json=_body(),
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["revision"] == 1
    assert payload["outboxEventId"].endswith(":received")

    opened = live_client.post(
        "/api/cases/access",
        headers=_headers(),
        json={
            "publicReference": payload["publicReference"],
            "capability": payload["capability"],
        },
    )
    assert opened.status_code == 204, opened.text

    status = live_client.get("/api/cases/status")

    assert status.status_code == 200, status.text
    body = status.json()
    assert body["publicReference"] == payload["publicReference"]
    assert body["currentStep"] == "received"
    assert body["reviewPath"] == "none"
    assert len(body["itemDecisions"]) == 1


@pg_only
def test_a_rejected_correction_becomes_a_problem_document_not_a_traceback(live_client):
    body = _body()
    body["items"][0]["fieldPath"] = "verifiedAt"

    response = live_client.post(
        "/api/cases/corrections",
        headers=_headers(**{"Idempotency-Key": "e2e-reject-1"}),
        json=body,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "field_path_not_correctable"


@pg_only
def test_urgent_language_is_answered_with_the_safe_routing_problem(live_client):
    body = _body()
    body["items"][0]["reportedValue"] = "có người dọa giết chủ quán"

    response = live_client.post(
        "/api/cases/corrections",
        headers=_headers(**{"Idempotency-Key": "e2e-urgent-1"}),
        json=body,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "correction_safety_routing"
    assert "113" in response.json()["detail"]


@pg_only
def test_an_invalid_capability_cannot_be_distinguished_from_an_unknown_one(live_client):
    unknown = live_client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": "c" * 43},
    )

    assert unknown.status_code == 403
    assert unknown.json()["code"] == "invalid_case_credential"


@pg_only
def test_rotation_issues_a_new_capability_and_retires_the_old_one(live_client):
    created = live_client.post(
        "/api/cases/corrections",
        headers=_headers(**{"Idempotency-Key": "e2e-rotate-1"}),
        json=_body(),
    ).json()
    live_client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": created["publicReference"], "capability": created["capability"]},
    )
    csrf = live_client.cookies.get("vl360_case_csrf")

    rotated = live_client.post(
        "/api/cases/receipts/rotate", headers=_headers(**{"X-Case-CSRF": csrf}), json={}
    )

    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["capability"] != created["capability"]
    # The retired capability must no longer open a session.
    replay = live_client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": created["publicReference"], "capability": created["capability"]},
    )
    assert replay.status_code == 403


@pg_only
def test_review_on_a_closed_case_creates_a_linked_case_and_leaves_the_original_alone(
    live_client,
):
    created = live_client.post(
        "/api/cases/corrections",
        headers=_headers(**{"Idempotency-Key": "e2e-review-1"}),
        json=_body(),
    ).json()
    live_client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": created["publicReference"], "capability": created["capability"]},
    )
    csrf = live_client.cookies.get("vl360_case_csrf")
    database = live_client.database

    # A review only starts after the original closes.
    still_open = live_client.post(
        "/api/cases/review",
        headers=_headers(**{"X-Case-CSRF": csrf}),
        json={"reason": "số điện thoại vẫn sai", "expectedRevision": 1},
    )
    assert still_open.status_code == 409
    assert still_open.json()["code"] == "review_requires_a_closed_case"

    with database._conn(commit_on_success=False) as conn:
        original = database._fetchone(
            conn,
            "SELECT case_id FROM cases WHERE case_id = (SELECT case_id FROM case_receipts"
            " WHERE public_reference=%s)",
            (created["publicReference"],),
        )["case_id"]
        database._execute(
            conn,
            "UPDATE cases SET phase='closed', closed_at=NOW(), current_revision=2"
            " WHERE case_id=%s",
            (original,),
        )
        conn.commit()

    stale = live_client.post(
        "/api/cases/review",
        headers=_headers(**{"X-Case-CSRF": csrf}),
        json={"reason": "số điện thoại vẫn sai", "expectedRevision": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "case_revision_conflict"

    opened = live_client.post(
        "/api/cases/review",
        headers=_headers(**{"X-Case-CSRF": csrf}),
        json={"reason": "số điện thoại vẫn sai", "expectedRevision": 2},
    )

    assert opened.status_code == 201, opened.text
    assert opened.json()["publicReference"] != created["publicReference"]

    with database._conn(commit_on_success=False) as conn:
        review = database._fetchone(
            conn,
            "SELECT case_id, category, service_kind, phase FROM cases WHERE review_of_case_id=%s",
            (original,),
        )
        untouched = database._fetchone(
            conn, "SELECT phase, current_revision FROM cases WHERE case_id=%s", (original,)
        )
    assert review["category"] == "review"
    assert review["service_kind"] == "correction"
    assert review["phase"] == "intake"
    # The closed original is never reopened by asking for a review.
    assert untouched["phase"] == "closed"
    assert untouched["current_revision"] == 2


def test_a_successful_create_is_observed_as_one_arrival(client, monkeypatch):
    events = []
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append((kind, kw.get("channel"))) or True)

    response = client.post("/api/cases/corrections", headers=_headers(), json=_body())

    assert response.status_code == 201
    # One arrival, on the web channel; a replayed create would add nothing.
    assert events == [("received", "web")]


def test_the_declared_wire_format_is_camel_case_and_only_that():
    """The exact bodies web-nuxt/composables/useCorrectionCases.ts sends.

    These models carry an alias on every field and forbid extras, so there is no
    "close enough": a snake_case body is two errors per field. Nothing caught
    that for the whole pilot because every test built the models the way the
    server likes them. This one is written the way the browser sends them.
    """
    from cases.public_api import _AccessIn, _CreateIn, _ItemIn

    item = {
        "entityId": "p-quan-com", "fieldPath": "attributes.phone",
        "reportedValue": "0270 111 2222", "proposedValue": "0270 333 4444",
        "baseEntityRevision": 7,
    }
    parsed = _CreateIn(
        reporterPrivacy="anonymous", items=[_ItemIn(**item)],
        optionalPhone=None, notificationConsent=False,
        handoffDigest=None, handoffConfirmed=False,
    )
    assert parsed.items[0].entity_id == "p-quan-com"

    access = _AccessIn(publicReference="VL-COR-0000000000001", capability="A" * 43)
    assert access.public_reference == "VL-COR-0000000000001"


def test_a_snake_case_body_is_refused_outright():
    import pytest as _pytest
    from pydantic import ValidationError

    from cases.public_api import _ItemIn

    # Not a warning, not a coercion: the reporter's whole submission dies here,
    # and the page has no way to tell them it was our bug and not their code.
    with _pytest.raises(ValidationError):
        _ItemIn(
            entity_id="p-quan-com", field_path="attributes.phone",
            reported_value="a", proposed_value="b", base_entity_revision=7,
        )


def test_the_contact_route_accepts_a_withdrawal():
    from cases.public_api import _ContactRequestIn

    # Consent defaults to true so an ordinary request is unchanged, and false is
    # now expressible — the model forbade extra fields, so before this the
    # privacy policy's "rút lại đồng ý trong 15 ngày" had no route to happen on.
    assert _ContactRequestIn(phone="0901234567").consent is True
    assert _ContactRequestIn(phone="0901234567", consent=False).consent is False


def test_anonymous_withdrawal_requires_the_opaque_receipt(client):
    response = client.post(
        "/api/cases/contact/start",
        headers=_headers(),
        json={"phone": "0901234567", "consent": False},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_case_credential"
    assert client.service.pre_case_contact_requests == []


def test_anonymous_withdrawal_binds_the_receipt_to_the_service(client):
    response = client.post(
        "/api/cases/contact/start",
        headers=_headers(),
        json={"phone": "0901234567", "consent": False, "receipt": "receipt-token"},
    )

    assert response.status_code == 202
    assert len(client.service.pre_case_contact_requests) == 1
    assert client.service.pre_case_contact_requests[0].items() >= {
        "phone": "0901234567",
        "consent": False,
        "receipt": "receipt-token",
    }.items()


def test_opaque_pre_case_receipt_uses_public_lane_despite_stale_access_cookie(client):
    calls = []

    def verify_pre_case_contact(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(contact_digest="digest", verified_at=NOW), "opaque-receipt"

    client.service.verify_pre_case_contact = verify_pre_case_contact
    client.service._crypto = SimpleNamespace(
        open_contact_receipt=lambda _receipt, now: {"expires_at": int(now.timestamp())}
    )
    client.cookies.set("vl360_case_access", "stale-cookie", path="/api/cases")

    response = client.post(
        "/api/cases/contact/verify",
        headers=_headers(),
        json={"code": "123456", "receipt": "opaque-receipt"},
    )

    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert calls == [{"receipt": "opaque-receipt", "code": "123456"}]
    assert client.service.contact_verifications == []


def test_the_blocking_sms_send_never_runs_on_the_event_loop(client):
    """Route công khai DUY NHẤT gọi ra ngoài mạng phải được đẩy khỏi event loop.

    EsmsProvider.send thử 3 lần, mỗi lần total_timeout 20s, xen time.sleep(0.5)
    và time.sleep(1.0) — tối đa ~61,5 giây. Gọi thẳng trong async handler thì
    một POST /api/cases/contact/request đóng băng CẢ vl-agent: chat, /api/entities,
    /auth đứng theo, không riêng luồng đính chính.

    Đo bằng danh tính LUỒNG, không so chuỗi mã nguồn: /access chạy thẳng trên
    event loop nên nó là mốc đối chứng; /contact/request phải rơi vào luồng khác.
    """
    client.post(
        "/api/cases/access",
        headers=_headers(),
        json={"publicReference": REFERENCE, "capability": CAPABILITY},
    )
    csrf = _headers(**{"X-Case-CSRF": "b" * 43})
    client.post(
        "/api/cases/contact/request", headers=csrf, json={"phone": "0901234567"}
    )
    client.delete("/api/cases/access", headers=csrf)

    assert client.service.revoke_threads, "route đối chứng chưa chạy"
    assert client.service.contact_request_threads, "route gửi SMS chưa chạy"
    loop_thread = client.service.revoke_threads[0]
    send_thread = client.service.contact_request_threads[0]
    assert send_thread != loop_thread, (
        "lời gọi gửi SMS chạy trên chính luồng event loop — một lần thử lại của "
        "nhà mạng sẽ đóng băng toàn bộ tiến trình tới ~61 giây"
    )


def test_the_route_passes_the_caller_choice_rather_than_a_constant():
    import inspect

    from cases.public_api import request_contact_verification

    source = inspect.getsource(request_contact_verification)

    assert "consent=body.consent" in source
    assert "consent=True" not in source
