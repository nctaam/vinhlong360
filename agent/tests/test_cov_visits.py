"""
Unit tests for visits.py — "Đã đi / Muốn đi" visit marks (Postgres-only UGC).

Two layers:
  1. Router-level: mount the router, confirm paths/methods and the PG guard
     (503 in SQLite dev) — mirrors test_saved.py.
  2. Handler-level: call the async handlers directly with a fake user, mocking
     ONLY the DB I/O boundary (db._conn / _fetchall / _fetchone / _execute) so
     the real branching + row-shaping logic runs without Postgres.

We assert real logic (status filters, want-vs-visited branch, stats breakdown
aggregation, null-status branch), not the values the mocks return.
"""

import asyncio
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from database import db  # noqa: E402
import visits  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────

FAKE_USER = {"id": "11111111-1111-1111-1111-111111111111"}


def _client():
    app = FastAPI()
    app.include_router(visits.router)
    return TestClient(app)


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


class _FakeConn:
    """Records SQL passed to it via the monkeypatched db._* helpers."""


@contextmanager
def _fake_conn_cm():
    yield _FakeConn()


def _install_fake_io(monkeypatch, *, fetchall=None, fetchone=None):
    """Mock the DB I/O boundary. Captures every (sql, params) tuple executed."""
    captured = {"fetchall": [], "fetchone": [], "execute": []}

    monkeypatch.setattr(db, "_conn", _fake_conn_cm)

    def _fa(conn, sql, params=None):
        captured["fetchall"].append((sql, params))
        return (fetchall if fetchall is not None else [])

    def _fo(conn, sql, params=None):
        captured["fetchone"].append((sql, params))
        return fetchone

    def _ex(conn, sql, params=None):
        captured["execute"].append((sql, params))
        return None

    monkeypatch.setattr(db, "_fetchall", _fa)
    monkeypatch.setattr(db, "_fetchone", _fo)
    monkeypatch.setattr(db, "_execute", _ex)
    return captured


# ── 1. Router mounting + PG guard ────────────────────────────────────────

def test_router_mounts_all_routes():
    pairs = _route_pairs(_client().app)
    assert ("GET", "/api/me/visits") in pairs
    assert ("POST", "/api/me/visits") in pairs
    assert ("GET", "/api/me/visits/check/{entity_id}") in pairs
    assert ("GET", "/api/me/visits/review-prompts") in pairs
    assert ("GET", "/api/me/visits/stats") in pairs
    assert ("DELETE", "/api/me/visits/{entity_id}") in pairs


def test_pg_guard_blocks_in_sqlite():
    # In this environment DATABASE_URL is unset → SQLite → the router-level
    # require_pg dependency short-circuits every endpoint with 503.
    client = _client()
    if not db._use_pg:
        assert client.get("/api/me/visits").status_code == 503
        assert client.get("/api/me/visits/check/some-id").status_code == 503
        assert client.post("/api/me/visits", json={"entity_id": "x", "status": "want"}).status_code == 503
        assert client.get("/api/me/visits/stats").status_code == 503
        assert client.get("/api/me/visits/review-prompts").status_code == 503
        assert client.delete("/api/me/visits/x").status_code == 503
    else:
        # Postgres: routes exist, auth required (not 404).
        assert client.get("/api/me/visits").status_code in (401, 403)


# ── 2. VisitBody pydantic validation (pure logic) ────────────────────────

def test_visitbody_accepts_valid_statuses():
    assert visits.VisitBody(entity_id="cam-sanh", status="want").status == "want"
    assert visits.VisitBody(entity_id="cam-sanh", status="visited").status == "visited"


def test_visitbody_rejects_bad_status():
    with pytest.raises(ValidationError) as exc:
        visits.VisitBody(entity_id="x", status="going")
    assert "want | visited" in str(exc.value)


def test_visitbody_rejects_empty_and_case_variants():
    for bad in ("", "Want", "VISITED", "wanted", "visit"):
        with pytest.raises(ValidationError):
            visits.VisitBody(entity_id="x", status=bad)


def test_visitbody_enforces_entity_id_max_length():
    # max_length=200 on entity_id
    ok = visits.VisitBody(entity_id="a" * 200, status="want")
    assert len(ok.entity_id) == 200
    with pytest.raises(ValidationError):
        visits.VisitBody(entity_id="a" * 201, status="want")


# ── 3. list_visits handler logic ─────────────────────────────────────────

def test_list_visits_without_filter_omits_status_clause():
    def run(mp):
        rows = [
            {"entity_id": "e1", "status": "want", "created_at": "t1"},
            {"entity_id": "e2", "status": "visited", "created_at": "t2"},
        ]
        cap = _install_fake_io(mp, fetchall=rows)
        out = asyncio.run(visits.list_visits(status=None, user=FAKE_USER))
        return out, cap

    with pytest.MonkeyPatch.context() as mp:
        out, cap = run(mp)
    # Real shaping logic: only entity_id + status kept, created_at dropped.
    assert out == {"visits": [
        {"entity_id": "e1", "status": "want"},
        {"entity_id": "e2", "status": "visited"},
    ]}
    sql, params = cap["fetchall"][0]
    # No status filter → single param (user id), no "AND status" clause.
    assert "AND status" not in sql
    assert params == (FAKE_USER["id"],)
    assert "LIMIT 5000" in sql


def test_list_visits_with_status_filter_adds_clause_and_param():
    with pytest.MonkeyPatch.context() as mp:
        cap = _install_fake_io(mp, fetchall=[])
        out = asyncio.run(visits.list_visits(status="visited", user=FAKE_USER))
    assert out == {"visits": []}
    sql, params = cap["fetchall"][0]
    assert "AND status = " in sql  # placeholder is ? (SQLite) or %s (PG)
    # The status value is appended as the 2nd bound param.
    assert params == (FAKE_USER["id"], "visited")


def test_list_visits_ignores_out_of_domain_status_value():
    # status only appends a clause when in ("want","visited"); a stray value
    # (Query pattern would normally block it, but the handler guards too).
    with pytest.MonkeyPatch.context() as mp:
        cap = _install_fake_io(mp, fetchall=[])
        asyncio.run(visits.list_visits(status="bogus", user=FAKE_USER))
    sql, params = cap["fetchall"][0]
    assert "AND status" not in sql
    assert params == (FAKE_USER["id"],)


# ── 4. check_visit handler logic (both branches) ─────────────────────────

def test_check_visit_returns_status_when_row_exists():
    with pytest.MonkeyPatch.context() as mp:
        cap = _install_fake_io(mp, fetchone={"status": "visited"})
        out = asyncio.run(visits.check_visit(entity_id="cam-sanh", user=FAKE_USER))
    assert out == {"status": "visited"}
    sql, params = cap["fetchone"][0]
    assert params == (FAKE_USER["id"], "cam-sanh")


def test_check_visit_returns_null_when_no_row():
    with pytest.MonkeyPatch.context() as mp:
        _install_fake_io(mp, fetchone=None)
        out = asyncio.run(visits.check_visit(entity_id="cam-sanh", user=FAKE_USER))
    assert out == {"status": None}


def test_check_visit_rejects_unsafe_entity_id():
    # validate_path_id runs before any DB access → HTTPException(400).
    from fastapi import HTTPException
    with pytest.MonkeyPatch.context() as mp:
        _install_fake_io(mp, fetchone=None)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(visits.check_visit(entity_id="bad id!/../x", user=FAKE_USER))
    assert exc.value.status_code == 400


# ── 5. set_visit handler: want vs visited branch ─────────────────────────

def test_set_visit_want_does_not_schedule_achievements(monkeypatch):
    monkeypatch.setattr(visits, "check_rate", lambda *a, **k: None)
    scheduled = []
    monkeypatch.setattr(visits.asyncio, "create_task", lambda coro: scheduled.append(coro))
    cap = _install_fake_io(monkeypatch)
    body = visits.VisitBody(entity_id="e1", status="want")

    out = asyncio.run(visits.set_visit(body=body, user=FAKE_USER, _csrf=None))

    assert out == {"status": "want"}
    # want → NOT visited → no achievement task scheduled.
    assert scheduled == []
    # The upsert was executed with the 3 bound params.
    sql, params = cap["execute"][0]
    assert "ON CONFLICT" in sql
    assert params == (FAKE_USER["id"], "e1", "want")
    # close any un-awaited coroutine to avoid warnings (none expected here).
    for c in scheduled:
        c.close()


def test_set_visit_visited_schedules_achievement_task(monkeypatch):
    monkeypatch.setattr(visits, "check_rate", lambda *a, **k: None)
    scheduled = []
    monkeypatch.setattr(visits.asyncio, "create_task", lambda coro: scheduled.append(coro))
    _install_fake_io(monkeypatch)
    body = visits.VisitBody(entity_id="e2", status="visited")

    out = asyncio.run(visits.set_visit(body=body, user=FAKE_USER, _csrf=None))

    assert out == {"status": "visited"}
    # visited → exactly one background achievement task scheduled.
    assert len(scheduled) == 1
    for c in scheduled:
        c.close()


def test_set_visit_calls_rate_limit_with_user_key(monkeypatch):
    calls = []
    monkeypatch.setattr(visits, "check_rate", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(visits.asyncio, "create_task", lambda coro: coro.close())
    _install_fake_io(monkeypatch)
    body = visits.VisitBody(entity_id="e1", status="want")

    asyncio.run(visits.set_visit(body=body, user=FAKE_USER, _csrf=None))

    assert calls, "check_rate must be invoked"
    # first positional arg is the per-user rate key.
    assert calls[0][0] == f"visit:{FAKE_USER['id']}"


# ── 6. review_prompts handler logic ──────────────────────────────────────

def test_review_prompts_shapes_rows_and_binds_limit():
    rows = [
        {"entity_id": "e1", "visited_at": "t1"},
        {"entity_id": "e2", "visited_at": "t2"},
    ]
    with pytest.MonkeyPatch.context() as mp:
        cap = _install_fake_io(mp, fetchall=rows)
        out = asyncio.run(visits.review_prompts(user=FAKE_USER, limit=7))
    assert out == {"prompts": rows}
    sql, params = cap["fetchall"][0]
    # uid bound twice (outer + NOT IN subquery) then limit.
    assert params == (FAKE_USER["id"], FAKE_USER["id"], 7)
    assert "post_type = 'review'" in sql


# ── 7. visit_stats handler: aggregation logic ────────────────────────────

def _stats_io(monkeypatch, total_row, by_type_rows):
    """visit_stats calls _fetchone (totals) then _fetchall (by_type)."""
    monkeypatch.setattr(db, "_conn", _fake_conn_cm)
    monkeypatch.setattr(db, "_fetchone", lambda conn, sql, params=None: total_row)
    monkeypatch.setattr(db, "_fetchall", lambda conn, sql, params=None: by_type_rows)


def test_visit_stats_builds_breakdown_and_totals():
    total = {"total": 5, "visited": 3, "want": 2}
    by_type = [
        {"type": "attraction", "status": "visited", "cnt": 2},
        {"type": "attraction", "status": "want", "cnt": 1},
        {"type": "food", "status": "visited", "cnt": 1},
    ]
    with pytest.MonkeyPatch.context() as mp:
        _stats_io(mp, total, by_type)
        out = asyncio.run(visits.visit_stats(user=FAKE_USER))
    assert out["total"] == 5
    assert out["visited"] == 3
    assert out["want"] == 2
    # Aggregation groups per type, seeding missing slots with 0.
    assert out["by_type"] == {
        "attraction": {"visited": 2, "want": 1},
        "food": {"visited": 1, "want": 0},
    }


def test_visit_stats_defaults_when_total_row_missing():
    # total is None → td == {} → .get fallbacks to 0 for every count.
    with pytest.MonkeyPatch.context() as mp:
        _stats_io(mp, None, [])
        out = asyncio.run(visits.visit_stats(user=FAKE_USER))
    assert out == {"total": 0, "visited": 0, "want": 0, "by_type": {}}


def test_visit_stats_unknown_type_bucket():
    # A row whose 'type' is absent falls into the "unknown" bucket.
    total = {"total": 1, "visited": 1, "want": 0}
    by_type = [{"status": "visited", "cnt": 1}]  # no 'type' key
    with pytest.MonkeyPatch.context() as mp:
        _stats_io(mp, total, by_type)
        out = asyncio.run(visits.visit_stats(user=FAKE_USER))
    assert out["by_type"] == {"unknown": {"visited": 1, "want": 0}}


# ── 8. remove_visit handler logic ────────────────────────────────────────

def test_remove_visit_executes_delete_and_returns_null(monkeypatch):
    monkeypatch.setattr(visits, "check_rate", lambda *a, **k: None)
    cap = _install_fake_io(monkeypatch)

    out = asyncio.run(visits.remove_visit(entity_id="cam-sanh", user=FAKE_USER, _csrf=None))

    assert out == {"status": None}
    sql, params = cap["execute"][0]
    assert sql.strip().startswith("DELETE FROM user_visits")
    assert params == (FAKE_USER["id"], "cam-sanh")


def test_remove_visit_rejects_unsafe_entity_id(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(visits, "check_rate", lambda *a, **k: None)
    _install_fake_io(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(visits.remove_visit(entity_id="../etc/passwd", user=FAKE_USER, _csrf=None))
    assert exc.value.status_code == 400
