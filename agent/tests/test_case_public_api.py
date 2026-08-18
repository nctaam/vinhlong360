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

    def create_correction_from_transport(self, payload, **kwargs):
        self.created.append((payload, kwargs))
        return CreateCorrectionResult(
            case_id="11111111-1111-1111-1111-111111111111",
            public_reference=REFERENCE,
            capability=CAPABILITY,
            received_at=NOW,
            next_update_at=NOW + timedelta(days=3),
            replayed=False,
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
        self.revoked.append(kwargs)


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
def client(request):
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
        "reviewPath",
    }
    rendered = response.text
    for forbidden in ("caseId", "ownerRef", "severity", "riskClass", "evidence",
                      "capabilityDigest", "auditEvent", "triage", "investigation"):
        assert forbidden not in rendered


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

import os  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402


def _pg_url() -> str | None:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = _pg_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)


@pytest.fixture
def live_client():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    import database
    from cases.policy import load_case_policy
    from cases.security import CaseCrypto
    from cases.service import CaseService
    from cases.store import PostgresCaseStore

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
