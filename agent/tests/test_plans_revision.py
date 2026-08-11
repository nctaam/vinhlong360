import asyncio
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import plans


MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "079_user_plans_revision.sql"
PLAN_ID = "11111111-1111-4111-8111-111111111111"
OWNER_ID = "22222222-2222-4222-8222-222222222222"
SERVER_SNAPSHOT_ROW = {
    "id": PLAN_ID,
    "title": "Server",
    "stops": [],
    "is_public": False,
    "created_at": "2026-08-10T01:00:00+00:00",
    "revision": 4,
    "updated_at": "2026-08-10T02:00:00+00:00",
}


class _Conn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_revision_migration_is_additive_and_idempotent():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1" in sql
    assert "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_user_plans_user_updated" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "DELETE FROM user_plans" not in sql


@pytest.mark.parametrize("bad", [True, "3", 0, -1])
def test_update_body_rejects_non_positive_integer_revision(bad):
    with pytest.raises(ValidationError):
        plans.PlanUpdateBody(title="A", stops=[], expected_revision=bad)


@pytest.mark.parametrize("bad", [True, "3", 0, -1])
def test_publish_body_rejects_non_positive_integer_revision(bad):
    with pytest.raises(ValidationError):
        plans.PublishBody(is_public=True, expected_revision=bad)


def test_row_plan_exposes_revision_and_updated_at():
    out = plans._row_plan(SERVER_SNAPSHOT_ROW)
    assert out["revision"] == 4
    assert out["savedAt"].startswith("2026-08-10T01:00")
    assert out["updatedAt"].startswith("2026-08-10T02:00")


@pytest.fixture
def recording_db(monkeypatch):
    calls = {"fetchone": [], "execute": [], "update_row": SERVER_SNAPSHOT_ROW}

    def fake_fetchone(conn, sql, params=()):
        calls["fetchone"].append((sql, params))
        if "UPDATE user_plans" in sql:
            return calls["update_row"]
        return calls.get("current_row")

    monkeypatch.setattr(plans.db, "_conn", lambda: _Conn())
    monkeypatch.setattr(plans.db, "_fetchone", fake_fetchone)
    monkeypatch.setattr(plans.db, "_execute", lambda conn, sql, params=(): calls["execute"].append((sql, params)))
    monkeypatch.setattr(plans, "check_rate", lambda *args: None)
    return calls


def test_update_sql_is_atomic_and_owner_bound(recording_db):
    result = asyncio.run(plans.update_plan(
        plan_id=PLAN_ID,
        body=plans.PlanUpdateBody(title="Mới", stops=[], expected_revision=3),
        user={"id": OWNER_ID},
        _csrf=None,
    ))
    sql, params = recording_db["fetchone"][0]
    assert "WHERE id::text" in sql
    assert "user_id" in sql
    assert "revision" in sql
    assert "revision = revision + 1" in sql
    assert params[-1] == 3
    assert result["plan"]["revision"] == 4


def test_stale_update_returns_409_with_current_snapshot(recording_db):
    recording_db["update_row"] = None
    recording_db["current_row"] = SERVER_SNAPSHOT_ROW
    response = asyncio.run(plans.update_plan(
        plan_id=PLAN_ID,
        body=plans.PlanUpdateBody(title="Local", stops=[], expected_revision=3),
        user={"id": OWNER_ID},
        _csrf=None,
    ))
    assert response.status_code == 409
    payload = json.loads(response.body)
    assert payload["code"] == "plan_revision_conflict"
    assert payload["current"]["revision"] == 4


def test_missing_or_foreign_owner_returns_404(recording_db):
    recording_db["update_row"] = None
    recording_db["current_row"] = None
    with pytest.raises(HTTPException) as exc:
        asyncio.run(plans.update_plan(
            plan_id=PLAN_ID,
            body=plans.PlanUpdateBody(title="Local", stops=[], expected_revision=3),
            user={"id": OWNER_ID},
            _csrf=None,
        ))
    assert exc.value.status_code == 404


def test_insert_returns_snapshot_with_revision_one(monkeypatch):
    monkeypatch.setattr(plans.db, "_fetchone", lambda conn, sql, params=(): {
        **SERVER_SNAPSHOT_ROW, "revision": 1,
    })
    snapshot = plans._insert(_Conn(), OWNER_ID, plans.PlanBody(title="A", stops=[]))
    assert snapshot["revision"] == 1


def test_merge_remains_create_only():
    source = Path(plans.__file__).read_text(encoding="utf-8")
    merge = source[source.index("async def merge_plans"):source.index("class PublishBody")]
    assert "_insert(conn, uid, p)" in merge
    assert "UPDATE user_plans" not in merge


def test_publish_matching_revision_is_atomic_owner_bound_and_returns_snapshot(recording_db):
    recording_db["update_row"] = {
        **SERVER_SNAPSHOT_ROW,
        "is_public": True,
        "revision": 5,
        "updated_at": "2026-08-10T03:00:00+00:00",
    }
    out = asyncio.run(plans.publish_plan(
        plan_id=PLAN_ID,
        body=plans.PublishBody(is_public=True, expected_revision=4),
        user={"id": OWNER_ID},
        _csrf=None,
    ))

    sql, params = recording_db["fetchone"][0]
    assert "WHERE id::text" in sql
    assert "user_id" in sql
    assert "revision =" in sql
    assert "revision = revision + 1" in sql
    assert "RETURNING id, title, stops, is_public, created_at, revision, updated_at" in sql
    assert params == (True, PLAN_ID, OWNER_ID, 4)
    assert out["is_public"] is True
    assert out["revision"] == 5
    assert out["plan"] == {
        "id": PLAN_ID,
        "title": "Server",
        "stops": [],
        "is_public": True,
        "savedAt": "2026-08-10T01:00:00+00:00",
        "revision": 5,
        "updatedAt": "2026-08-10T03:00:00+00:00",
    }


def test_stale_publish_returns_409_with_current_snapshot_without_mutation(recording_db):
    recording_db["update_row"] = None
    recording_db["current_row"] = SERVER_SNAPSHOT_ROW.copy()

    response = asyncio.run(plans.publish_plan(
        plan_id=PLAN_ID,
        body=plans.PublishBody(is_public=True, expected_revision=3),
        user={"id": OWNER_ID},
        _csrf=None,
    ))

    assert response.status_code == 409
    payload = json.loads(response.body)
    assert payload == {
        "detail": "Lịch trình đã thay đổi trên thiết bị khác",
        "code": "plan_revision_conflict",
        "current": plans._row_plan(SERVER_SNAPSHOT_ROW),
    }
    assert recording_db["current_row"]["is_public"] is False
    assert recording_db["current_row"]["revision"] == 4


def test_missing_or_foreign_owner_publish_returns_404(recording_db):
    recording_db["update_row"] = None
    recording_db["current_row"] = None

    with pytest.raises(HTTPException) as exc:
        asyncio.run(plans.publish_plan(
            plan_id=PLAN_ID,
            body=plans.PublishBody(is_public=True, expected_revision=4),
            user={"id": OWNER_ID},
            _csrf=None,
        ))

    assert exc.value.status_code == 404
