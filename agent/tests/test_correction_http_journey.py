"""The reporter's journey over HTTP, through the routes a browser actually hits.

Every other journey test in this suite calls the service layer directly. That is
why a wire-format mismatch between the Nuxt composable and the request models
survived an entire pilot: the code under test was never the code a browser
reaches. Validation, the flag gates, the same-origin guard, the cookies and the
JSON shaping all live above the service, and none of them had ever run.

This drives the mounted FastAPI app with a TestClient against the disposable
PostgreSQL: create, exchange the one-time capability for a session, read status.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402

MASTER_KEY = "0" * 43
ENTITY_ID = "p-http-journey"
ORIGIN = "http://testserver"


@pytest.fixture
def client(monkeypatch):
    """The real app, with the kernel wired the way production wires it."""
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import database
    from cases import wiring
    from cases.public_api import case_public_router
    from config import settings

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL

    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, attributes, revision)"
            " VALUES (%s,'place','Bến Đò Cổ Chiên',%s,3)"
            " ON CONFLICT (id) DO UPDATE SET revision=3, attributes=EXCLUDED.attributes",
            (ENTITY_ID, '{"phone": "0270 111 2222"}'),
        )
        # A frozen clock is not in play here, but the rate limiter counts per
        # subject and this suite reruns; start from a clean window.
        adapter._execute(conn, "DELETE FROM shared_rate_limits WHERE key LIKE %s", ("case:%",))
        conn.commit()

    for flag in ("CASE_KERNEL_ENABLED", "CORRECTION_INTAKE_ENABLED"):
        monkeypatch.setattr(settings, flag, True, raising=False)
    monkeypatch.setattr(settings, "CORS_ORIGINS", ORIGIN, raising=False)
    monkeypatch.setattr(settings, "CASE_KERNEL_ENCRYPTION_KEY", MASTER_KEY, raising=False)

    # Not a formality. This returning False is how the kernel refuses to wire,
    # and it has been False twice this week for reasons a caller could not see:
    # a property called as a method, and a missing key. Assert it here so the
    # journey below cannot be reading a dormant kernel's 404s as passes.
    assert wiring.wire_case_kernel(adapter, settings) is True

    app = FastAPI()
    app.include_router(case_public_router)
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client

    from cases.admin_api import configure_case_admin_api
    from cases.contact import configure_case_contact
    from cases.correction import configure_case_correction
    from cases.metrics import configure_case_metrics
    from cases.public_api import configure_case_public_api
    from cases.publication import configure_case_publication
    from cases.work_control import configure_case_work_control

    configure_case_public_api(service=None, settings=None, allowed_origin=None)
    configure_case_correction(database=None, crypto=None, policy=None)
    configure_case_publication(database=None, crypto=None, policy=None)
    configure_case_work_control(database=None, policy=None)
    configure_case_admin_api(database=None, crypto=None, projection_fetcher=None, service=None)
    configure_case_contact(database=None, crypto=None, provider=None)
    configure_case_metrics(database=None)


def _headers():
    return {
        "Idempotency-Key": f"http-journey:{uuid.uuid4()}",
        "Origin": ORIGIN,
        "Sec-Fetch-Site": "same-origin",
    }


def _body():
    """Exactly what web-nuxt/composables/useCorrectionCases.ts sends."""
    return {
        "reporterPrivacy": "anonymous",
        "items": [{
            "entityId": ENTITY_ID,
            "fieldPath": "attributes.phone",
            "reportedValue": "0270 111 2222",
            "proposedValue": "0270 333 4444",
            "baseEntityRevision": 3,
        }],
        "optionalPhone": None,
        "notificationConsent": False,
        "handoffDigest": None,
        "handoffConfirmed": False,
    }


@pg_only
def test_the_browser_body_is_accepted_by_the_route_that_receives_it(client):
    response = client.post("/api/cases/corrections", json=_body(), headers=_headers())

    # The bug this file exists for: the composable sent snake_case at models
    # that validate by camelCase alias and forbid extras, so every submission
    # was a 422 the page showed the reporter as a problem with their own codes.
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["publicReference"].startswith("VL-COR-")
    assert len(receipt["capability"]) >= 40
    assert receipt["replayed"] is False


@pg_only
def test_the_capability_opens_the_status_page_it_was_issued_for(client):
    created = client.post("/api/cases/corrections", json=_body(), headers=_headers())
    receipt = created.json()

    exchanged = client.post(
        "/api/cases/access",
        json={"publicReference": receipt["publicReference"],
              "capability": receipt["capability"]},
        headers={"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"},
    )
    # 204: the session is in the cookies, and there is nothing about the case
    # worth putting in a body the browser did not ask for.
    assert exchanged.status_code == 204, exchanged.text

    status = client.get("/api/cases/status")

    assert status.status_code == 200, status.text
    body = status.json()
    assert body["publicReference"] == receipt["publicReference"]
    # The shape web-nuxt/types/cases.ts is written against, field for field.
    for key in ("receivedAt", "currentStep", "nextAction", "nextUpdateAt",
                "promiseHealth", "itemDecisions", "itemPublicationStates", "reviewPath"):
        assert key in body, key
    # A case filed seconds ago is not late. The receipt clock is due five
    # seconds in and satisfied by construction; counting it said otherwise.
    assert body["promiseHealth"] == "on_track"
    assert body["itemDecisions"][0]["dispositionFamily"] == "undetermined"


@pg_only
def test_a_snake_case_body_is_refused_without_quoting_anything_back(client):
    response = client.post(
        "/api/cases/corrections",
        json={"reporter_privacy": "anonymous", "items": [{
            "entity_id": ENTITY_ID, "field_path": "attributes.phone",
            "reported_value": "a", "proposed_value": "b", "base_entity_revision": 3,
        }]},
        headers=_headers(),
    )

    assert response.status_code == 422
    # A refusal must name the field, never echo what was sent: this endpoint
    # carries a phone number and a one-time secret in neighbouring requests.
    assert "0270" not in response.text


@pg_only
def test_no_idempotency_key_is_refused_before_anything_is_written(client):
    headers = _headers()
    del headers["Idempotency-Key"]

    response = client.post("/api/cases/corrections", json=_body(), headers=headers)

    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


@pg_only
def test_the_same_key_twice_returns_the_same_receipt_rather_than_two_cases(client):
    headers = _headers()

    first = client.post("/api/cases/corrections", json=_body(), headers=headers)
    second = client.post("/api/cases/corrections", json=_body(), headers=headers)

    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["publicReference"] == second.json()["publicReference"]
    # The replay is announced, so the page can say "we already have this".
    assert second.json()["replayed"] is True


@pg_only
def test_a_wrong_capability_fails_the_same_way_as_an_unknown_reference(client):
    created = client.post("/api/cases/corrections", json=_body(), headers=_headers())
    reference = created.json()["publicReference"]

    wrong_secret = client.post(
        "/api/cases/access",
        json={"publicReference": reference, "capability": "B" * 43},
        headers={"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"},
    )
    unknown_case = client.post(
        "/api/cases/access",
        json={"publicReference": "VL-COR-0000000000000", "capability": "B" * 43},
        headers={"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"},
    )

    # Distinguishable answers here would turn the lookup into an oracle for
    # which references exist. request_id differs by design — it correlates a
    # response to a log line and says nothing about the case.
    assert wrong_secret.status_code == unknown_case.status_code
    def without_id(payload):
        return {key: value for key, value in payload.items() if key != "request_id"}

    assert without_id(wrong_secret.json()) == without_id(unknown_case.json())


@pg_only
def test_status_without_a_session_says_nothing_about_any_case(client):
    response = client.get("/api/cases/status")

    assert response.status_code in (401, 403)
    assert "VL-COR" not in response.text
