"""Migration 070 — trigger correctness hành vi (B3/B4). PG-only.

BUG 1: rating aggregate đếm cả review soft-deleted → sao không hồi phục.
BUG 2: comment_count đếm dư (+1 tay chồng recount) + drift khi soft-delete.
Test end-to-end qua API (social.router) → chứng minh trigger là nguồn-sự-thật.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import social  # noqa: E402
from auth_middleware import get_current_user, require_user  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(not db._use_pg, reason="Trigger PG-only (UGC là Postgres-only).")


@pytest.fixture
def pg_user():
    user = db.create_user("09" + uuid.uuid4().hex[:8])
    yield user
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM users WHERE id::text = {db._ph}", (str(user["id"]),))


@pytest.fixture
def pg_entity():
    eid = "test-trig-" + uuid.uuid4().hex[:8]
    db.upsert_entity({"id": eid, "name": "Test Trigger Entity", "type": "product",
                      "summary": "Entity tạm cho test trigger 070."})
    yield eid
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM entities WHERE id = {db._ph}", (eid,))


def _client_as(user):
    app = FastAPI()
    app.include_router(social.router)
    app.dependency_overrides[require_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _entity_rating(eid):
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT avg_rating, rating_count FROM entity_ratings WHERE entity_id = {db._ph}", (eid,))
    return db._row_to_dict(row) if row else None


def _comment_count(pid):
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT comment_count FROM posts WHERE id::text = {db._ph}", (pid,))
    return int(db._row_to_dict(row)["comment_count"]) if row else None


@pg_only
def test_rating_excludes_soft_deleted_review(pg_user, pg_entity):
    client = _client_as(pg_user)
    r = client.post("/api/posts", json={"content": "Đánh giá 5 sao cho địa điểm này nhé.",
                                        "post_type": "review", "entity_id": pg_entity, "rating": 5})
    assert r.status_code == 201, r.text
    pid = r.json()["post"]["id"]
    try:
        rating = _entity_rating(pg_entity)
        assert rating and float(rating["avg_rating"]) == 5.0 and int(rating["rating_count"]) == 1
        # Soft-delete review → trigger 070 (lọc deleted_at) reset sao về 0.
        assert client.delete(f"/api/posts/{pid}").status_code == 200
        rating2 = _entity_rating(pg_entity)
        assert rating2 and float(rating2["avg_rating"]) == 0.0 and int(rating2["rating_count"]) == 0
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {db._ph}", (pid,))


@pg_only
def test_comment_count_no_double_and_soft_delete(pg_user, pg_entity):
    client = _client_as(pg_user)
    p = client.post("/api/posts", json={"content": "Bài để test đếm bình luận nhé."})
    assert p.status_code == 201, p.text
    pid = p.json()["post"]["id"]
    try:
        c1 = client.post(f"/api/posts/{pid}/comments", json={"content": "Bình luận số một"})
        c2 = client.post(f"/api/posts/{pid}/comments", json={"content": "Bình luận số hai"})
        assert c1.status_code == 201 and c2.status_code == 201, (c1.text, c2.text)
        assert _comment_count(pid) == 2  # KHÔNG +1 dư — trigger recount là nguồn duy nhất
        cid1 = c1.json()["comment"]["id"]
        assert client.delete(f"/api/comments/{cid1}").status_code == 200
        assert _comment_count(pid) == 1  # soft-delete → trigger fire ON UPDATE recount
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {db._ph}", (pid,))
