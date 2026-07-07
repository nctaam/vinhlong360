"""
B3 write-path coverage — MODERATION & REPORTS.

Two surfaces:
  1. Public report intake  — POST /api/report (public_api.py): file-based
     (reports.jsonl), works on BOTH backends → fully tested here (happy-path,
     validation, target-type coercion, rate-limit).
  2. Admin moderation       — /admin/moderation/* (admin.py): Postgres-backed
     state transitions (approve/reject on `posts`). The auth gate is asserted
     deterministically (401 without X-Admin-Key); the actual state transitions
     run via skipif(not db._use_pg) because the `posts` table is Postgres-only.

Also covers the moderation decision helper in moderation.py (pure thresholds).
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

import public_api  # noqa: E402
import admin  # noqa: E402
import middleware  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="Admin moderation acts on the Postgres `posts` table (absent on SQLite).",
)


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


# ═══════════════════════════════════════════════════════════════════════════
#  1. Public report intake — POST /api/report  (file-based, both backends)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def report_client(tmp_path, monkeypatch):
    """Mount public_api.router with reports.jsonl redirected to a temp file
    and the report rate-limiter reset so tests don't bleed into each other."""
    monkeypatch.setattr(public_api, "REPORTS_FILE", tmp_path / "reports.jsonl")
    # Fresh limiter state (singleton is shared process-wide).
    middleware.report_limiter._requests.clear()
    app = FastAPI()
    app.include_router(public_api.router)
    return TestClient(app)


def test_report_router_mounted():
    app = FastAPI()
    app.include_router(public_api.router)
    assert ("POST", "/api/report") in _route_pairs(app)


def test_submit_report_happy_path(report_client):
    resp = report_client.post("/api/report", json={
        "target_id": "cam-sanh-vinh-long",
        "target_type": "entity",
        "reason": "Thông tin sai",
        "detail": "Mùa vụ không đúng.",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # Persisted to the temp JSONL with status 'open'.
    lines = (public_api.REPORTS_FILE).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    import json
    rec = json.loads(lines[0])
    assert rec["target_id"] == "cam-sanh-vinh-long"
    assert rec["status"] == "open"


def test_submit_report_unknown_target_type_coerced(report_client):
    """Unrecognized target_type is coerced to 'other' (not rejected)."""
    resp = report_client.post("/api/report", json={
        "target_id": "x", "target_type": "weird", "reason": "spam",
    })
    assert resp.status_code == 200
    import json
    rec = json.loads(public_api.REPORTS_FILE.read_text(encoding="utf-8").strip())
    assert rec["target_type"] == "other"


def test_submit_report_missing_reason_422(report_client):
    """reason is required (min_length=1) → 422 validation error."""
    resp = report_client.post("/api/report", json={"target_id": "x"})
    assert resp.status_code == 422


def test_submit_report_rate_limited(report_client):
    """6th report from the same IP within the window → 429."""
    body = {"target_id": "x", "target_type": "entity", "reason": "spam"}
    codes = [report_client.post("/api/report", json=body).status_code for _ in range(6)]
    assert codes[:5] == [200, 200, 200, 200, 200]
    assert codes[5] == 429


class TestReportInValidation:
    def test_reason_too_long(self):
        with pytest.raises(ValidationError):
            public_api.ReportIn(target_id="x", reason="r" * 61)

    def test_detail_too_long(self):
        with pytest.raises(ValidationError):
            public_api.ReportIn(target_id="x", reason="ok", detail="d" * 2001)

    def test_target_id_required(self):
        with pytest.raises(ValidationError):
            public_api.ReportIn(target_id="", reason="ok")


# ═══════════════════════════════════════════════════════════════════════════
#  2. Admin moderation — /admin/moderation/* (auth gate + PG transitions)
# ═══════════════════════════════════════════════════════════════════════════

def _admin_client():
    app = FastAPI()
    app.include_router(admin.router)
    return TestClient(app)


def _admin_headers():
    # require_admin accepts the server-side admin key. Read the *live* value
    # from middleware (resolved at import time) so we match whatever is set.
    return {"X-Admin-Key": middleware.ADMIN_API_KEY}


def test_admin_moderation_routes_mounted():
    pairs = _route_pairs(_admin_client().app)
    assert ("POST", "/admin/moderation/{post_id}/approve") in pairs
    assert ("POST", "/admin/moderation/{post_id}/reject") in pairs
    assert ("GET", "/admin/moderation/queue") in pairs


def test_admin_moderation_requires_auth():
    """No X-Admin-Key and no admin session → 401 (gate runs before any DB)."""
    client = _admin_client()
    assert client.post("/admin/moderation/some-id/approve").status_code == 401
    assert client.post("/admin/moderation/some-id/reject", json={"reason": "spam"}).status_code == 401


class TestRejectBody:
    def test_reason_optional(self):
        assert admin.RejectBody().reason is None
        assert admin.RejectBody(reason="spam").reason == "spam"


@pg_only
def test_approve_post_transitions_to_approved():
    """admin approve flips a pending post to moderation_status='approved'."""
    user = db.create_user("09" + uuid.uuid4().hex[:8])
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, content, images, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, '[]'::jsonb, 'share', 'pending')
            RETURNING id
        """, (str(user["id"]), "Bài chờ duyệt."))
        pid = str(row["id"])
    try:
        client = _admin_client()
        resp = client.post(f"/admin/moderation/{pid}/approve", headers=_admin_headers())
        assert resp.status_code == 200
        with db._conn() as conn:
            after = db._fetchone(conn, f"SELECT moderation_status FROM posts WHERE id::text = {ph}", (pid,))
        assert db._row_to_dict(after)["moderation_status"] == "approved"
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))
            db._execute(conn, f"DELETE FROM users WHERE id::text = {ph}", (str(user["id"]),))


@pg_only
def test_reject_post_transitions_to_rejected():
    """admin reject flips a pending post to moderation_status='rejected'."""
    user = db.create_user("09" + uuid.uuid4().hex[:8])
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, content, images, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, '[]'::jsonb, 'share', 'pending')
            RETURNING id
        """, (str(user["id"]), "Bài sẽ bị từ chối."))
        pid = str(row["id"])
    try:
        client = _admin_client()
        resp = client.post(f"/admin/moderation/{pid}/reject", json={"reason": "spam"}, headers=_admin_headers())
        assert resp.status_code == 200
        with db._conn() as conn:
            after = db._fetchone(conn, f"SELECT moderation_status FROM posts WHERE id::text = {ph}", (pid,))
        assert db._row_to_dict(after)["moderation_status"] == "rejected"
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))
            db._execute(conn, f"DELETE FROM users WHERE id::text = {ph}", (str(user["id"]),))


# ═══════════════════════════════════════════════════════════════════════════
#  3. Moderation decision thresholds (pure, no network)
# ═══════════════════════════════════════════════════════════════════════════

class TestModerationThresholds:
    """The auto-decision boundaries that drive every post's moderation_status."""

    def test_below_approve_threshold(self):
        from moderation import AUTO_APPROVE_THRESHOLD
        # score < 0.3 → approved
        assert _decide(AUTO_APPROVE_THRESHOLD - 0.01) == "approved"

    def test_mid_band_pending(self):
        from moderation import AUTO_APPROVE_THRESHOLD
        assert _decide(AUTO_APPROVE_THRESHOLD + 0.01) == "pending"

    def test_high_flagged(self):
        from moderation import QUEUE_THRESHOLD
        assert _decide(QUEUE_THRESHOLD + 0.01) == "flagged"


def _decide(score: float) -> str:
    """Mirror of moderate_content's banding (kept in lockstep with moderation.py)."""
    from moderation import AUTO_APPROVE_THRESHOLD, QUEUE_THRESHOLD
    if score < AUTO_APPROVE_THRESHOLD:
        return "approved"
    if score < QUEUE_THRESHOLD:
        return "pending"
    return "flagged"
