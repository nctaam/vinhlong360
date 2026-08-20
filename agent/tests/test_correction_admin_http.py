"""The operator's commands over HTTP, through the routes the workbench posts to.

Same gap as the reporter's side: the admin case tests drive functions, not
routes. The workbench's dead publication chain lived in that gap for a whole
pilot — it posted an empty change_set_id because the payload never carried one,
and nothing that ran a route would have let that pass.

AdminCP authentication and CSRF are stubbed here on purpose. They have their own
suite and their own surface scan; what is under test is what a case route does
GIVEN an authenticated operator holding a particular scope.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402

MASTER_KEY = "0" * 43
ENTITY_ID = "p-admin-http"
UTC = timezone.utc


def _now():
    return datetime.now(UTC)


@pytest.fixture
def operator(monkeypatch):
    """The admin router, an authenticated operator, and a case to work on."""
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import admin
    import database
    from cases import wiring
    from cases.admin_api import case_admin_router
    from config import settings

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL

    held = {"scopes": ["service.operator", "correction.decide",
                       "publication.apply", "publication.verify"]}

    async def _authenticated(request, required_scope_override=None, **_):
        # Stands in for the AdminCP session. The scope check itself is the thing
        # under test, so it is enforced here rather than waved through.
        if required_scope_override and required_scope_override not in held["scopes"]:
            from fastapi import HTTPException

            raise HTTPException(403, detail={"code": "forbidden"})
        request.state.admin_user = {"id": 7}
        request.state.admin_scopes = list(held["scopes"])
        request.state.request_id = uuid.uuid4().hex
        return request.state.admin_user

    async def _no_csrf(request):
        return None

    monkeypatch.setattr(admin, "require_admin", _authenticated)
    monkeypatch.setattr(admin, "require_csrf", _no_csrf)
    for flag in ("CASE_KERNEL_ENABLED", "CORRECTION_ADMIN_ENABLED",
                 "CORRECTION_PUBLICATION_ENABLED"):
        monkeypatch.setattr(settings, flag, True, raising=False)
    monkeypatch.setattr(settings, "CASE_KERNEL_ENCRYPTION_KEY", MASTER_KEY, raising=False)
    assert wiring.wire_case_kernel(adapter, settings) is True

    app = FastAPI()
    app.include_router(case_admin_router)
    with TestClient(app, base_url="http://testserver") as client:
        yield client, adapter, held

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


def _seed(adapter, *, risk="R2"):
    """A claimed case with one item, as an operator finds it in the queue."""
    from cases.security import CaseCrypto

    crypto = CaseCrypto(MASTER_KEY)
    now = _now()
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, attributes, revision)"
            " VALUES (%s,'place','Chợ Nổi Trà Ôn',%s,3)"
            " ON CONFLICT (id) DO UPDATE SET revision=3, attributes=EXCLUDED.attributes",
            (ENTITY_ID, '{"phone": "0270 111 2222"}'),
        )
        case_id = str(adapter._fetchone(
            conn,
            "INSERT INTO cases (service_kind, category, phase, activity,"
            " disposition_family, reporter_privacy, owner_ref, current_revision,"
            " promise_policy_ref) VALUES ('correction','correction','decision','active',"
            "'undetermined','anonymous','person:owner',1,'correction-pilot-v1')"
            " RETURNING case_id",
            (),
        )["case_id"])
        item_id = str(adapter._fetchone(
            conn,
            "INSERT INTO correction_items (case_id, entity_id, field_path,"
            " reported_value_enc, proposed_value_enc, base_entity_revision,"
            " risk_class, evidence_level) VALUES (%s,%s,'attributes.phone',%s,%s,3,%s,'E3')"
            " RETURNING item_id",
            (case_id, ENTITY_ID,
             crypto.encrypt_private_payload({"value": "0270 111 2222"}),
             crypto.encrypt_private_payload({"value": "0270 333 4444"}), risk),
        )["item_id"])
        adapter._execute(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class,"
            " status, assignee_ref, lease_expires_at, ready_at, priority)"
            " VALUES (%s,'decide','case_operator',%s,'claimed','user:7',%s,%s,0)",
            (case_id, risk, now + timedelta(hours=2), now),
        )
        adapter._execute(
            conn,
            "INSERT INTO correction_evidence (case_id, item_id, evidence_level,"
            " source_ref, descriptor, content_enc, created_by_ref, created_at)"
            " VALUES (%s,%s,'E3','https://a.example','{}'::jsonb,NULL,'user:7',%s)",
            (case_id, item_id, now),
        )
        conn.commit()
    return case_id, item_id


@pg_only
def test_the_workbench_hands_the_operator_something_to_publish(operator):
    client, adapter, _ = operator
    case_id, item_id = _seed(adapter)

    detail = client.get(f"/admin/cases/{case_id}")

    assert detail.status_code == 200, detail.text
    body = detail.json()
    # Before this key existed the page could only post change_set_id: "", which
    # no command accepts — the whole publication chain was dead from the UI.
    assert "change_set" in body
    assert body["change_set"] is None
    assert body["items"][0]["item_id"] == item_id
    # Reported and proposed values are private; the workbench shows them only
    # behind a step-up, never in the case payload.
    assert "0270 111 2222" not in detail.text


@pg_only
def test_a_caller_cannot_talk_its_way_down_to_an_easier_risk_class(operator):
    client, adapter, _ = operator
    case_id, item_id = _seed(adapter, risk="R2")

    response = client.post(
        "/admin/cases/decisions",
        json={"case_id": case_id, "item_id": item_id, "outcome_code": "corrected",
              "reason_code": "source_confirms_change", "risk_class": "R1"},
    )

    # The item is R2 and R2 needs corroborating evidence plus author recusal.
    # Trusting the caller's "R1" would have judged it by the easiest rules on
    # offer; the route reads the risk the item was filed at, so an R2 item with
    # one E3 source and no second reviewer is refused however it is labelled.
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "author_recusal_required"
    with adapter._conn(commit_on_success=False) as conn:
        recorded = int(adapter._fetchone(
            conn, "SELECT count(*) AS n FROM case_decisions WHERE item_id=%s", (item_id,),
        )["n"])
    assert recorded == 0


@pg_only
def test_an_unknown_item_is_refused_rather_than_ruled_on(operator):
    client, adapter, _ = operator
    case_id, _ = _seed(adapter)

    response = client.post(
        "/admin/cases/decisions",
        json={"case_id": case_id, "item_id": str(uuid.uuid4()),
              "outcome_code": "corrected", "reason_code": "source_confirms_change"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "correction_item_not_found"


@pg_only
def test_a_scope_the_session_lacks_is_refused_at_the_door(operator):
    client, adapter, held = operator
    case_id, _ = _seed(adapter)
    held["scopes"] = ["service.operator"]

    response = client.post(
        "/admin/cases/change-sets/apply",
        json={"case_id": case_id, "change_set_id": str(uuid.uuid4()),
              "expected_case_revision": 1, "expected_entity_revision": 3},
    )

    # Hiding the button is a courtesy; this is the part that decides.
    assert response.status_code == 403


@pg_only
def test_the_queue_answers_with_work_and_not_with_an_exception(operator):
    client, adapter, _ = operator
    _seed(adapter)

    response = client.get("/admin/cases")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload.get("items"), list)
    # Every row carries the words the queue is triaged by. A fresh case is not
    # late, whatever the five-second receipt clock says.
    for row in payload["items"]:
        assert row["promise_health"] in {"on_track", "at_risk", "breached", "recovery"}
