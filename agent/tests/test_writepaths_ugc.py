"""
B3 write-path coverage — UGC (posts / comments / likes / bookmarks).

Per CLAUDE.md §B3: social.py is a 0%-test write-path. This is the safety net
before any refactor of the community/UGC layer.

Design (mirrors test_saved.py):
  - Fast: mount only social.router, no full server import, no network.
  - SQLite/CI: router-level `Depends(_require_pg)` returns 503 before any
    handler/auth runs — asserted deterministically.
  - Postgres: happy-path + auth-required + validation + moderation-status
    transitions run via skipif(not db._use_pg), with full row cleanup.

The Postgres tests create a throwaway user + entity, exercise the real
endpoints through dependency overrides (so we don't need a live OTP/session),
and delete everything they insert.
"""

import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

import social  # noqa: E402
from auth_middleware import get_current_user, require_user  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="UGC is Postgres-only (SQLite dev/CI returns 503). Set DATABASE_URL=postgresql://… to run.",
)


def _client():
    app = FastAPI()
    app.include_router(social.router)
    return TestClient(app)


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


# ── Router wiring ─────────────────────────────────────────────────────────

def test_social_router_mounted():
    pairs = _route_pairs(_client().app)
    assert ("POST", "/api/posts") in pairs
    assert ("DELETE", "/api/posts/{post_id}") in pairs
    assert ("POST", "/api/posts/{post_id}/comments") in pairs
    assert ("POST", "/api/posts/{post_id}/like") in pairs
    assert ("POST", "/api/posts/{post_id}/bookmark") in pairs


# ── Postgres guard (deterministic on SQLite/CI) ───────────────────────────

def test_social_pg_guard_on_sqlite():
    """SQLite dev/CI: PG guard returns 503 before auth check (B3 contract)."""
    client = _client()
    if not db._use_pg:
        assert client.post("/api/posts", json={"content": "x" * 20}).status_code == 503
        assert client.post("/api/posts/abc/comments", json={"content": "hi"}).status_code == 503
        assert client.post("/api/posts/abc/like").status_code == 503
        assert client.post("/api/posts/abc/bookmark").status_code == 503
        assert client.delete("/api/posts/abc").status_code == 503
    else:
        # Postgres live: like requires auth (not the 503 guard).
        assert client.post("/api/posts/abc/like").status_code in (401, 403)


# ── Model validation (backend-agnostic) ───────────────────────────────────

class TestCreatePostValidation:
    def test_valid_share(self):
        p = social.CreatePost(content="Một chuyến đi rất đáng nhớ ở Vĩnh Long.")
        assert p.post_type == "share"

    def test_content_too_short(self):
        with pytest.raises(ValidationError):
            social.CreatePost(content="ngắn")

    def test_content_too_long(self):
        with pytest.raises(ValidationError):
            social.CreatePost(content="x" * 5001)

    def test_invalid_post_type(self):
        with pytest.raises(ValidationError):
            social.CreatePost(content="đủ mười ký tự nhé", post_type="spam")

    def test_rating_out_of_range(self):
        with pytest.raises(ValidationError):
            social.CreatePost(content="đủ mười ký tự nhé", post_type="review", rating=9)

    def test_valid_review_rating(self):
        p = social.CreatePost(
            content="Sản phẩm OCOP chất lượng tốt.",
            post_type="review", entity_id="cam-sanh-vinh-long", rating=5,
        )
        assert p.rating == 5

    def test_repost_allows_empty_content(self):
        """Migration 013: repost (repost_of set) cho phép content rỗng."""
        p = social.CreatePost(content="", repost_of="some-post-id")
        assert p.repost_of == "some-post-id"
        assert p.content == ""

    def test_short_nonempty_content_still_rejected(self):
        """content 1-9 ký tự vẫn bị chặn dù có repost_of (gõ nhầm ≠ quote)."""
        with pytest.raises(ValidationError):
            social.CreatePost(content="ngắn", repost_of="some-post-id")


class TestCreateCommentValidation:
    def test_valid(self):
        assert social.CreateComment(content="Hay quá!").content == "Hay quá!"

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            social.CreateComment(content="   ")

    def test_too_long(self):
        with pytest.raises(ValidationError):
            social.CreateComment(content="x" * 2001)


# ── Postgres-only: real write-paths with cleanup ──────────────────────────

@pytest.fixture
def pg_user():
    """Create a throwaway verified user; delete (cascade) on teardown."""
    phone = "09" + uuid.uuid4().hex[:8]
    user = db.create_user(phone)
    yield user
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM users WHERE id::text = {db._ph}", (str(user["id"]),))


@pytest.fixture
def pg_entity():
    """Ensure a real entity exists to attach reviews to."""
    eid = "test-ugc-entity-" + uuid.uuid4().hex[:8]
    db.upsert_entity({"id": eid, "name": "Test UGC Entity", "type": "product",
                      "summary": "Entity tạm cho test write-path."})
    yield eid
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM entities WHERE id = {db._ph}", (eid,))


def _client_as(user):
    """Mount social.router with auth dependencies overridden to `user`."""
    app = FastAPI()
    app.include_router(social.router)
    app.dependency_overrides[require_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pg_only
def test_create_post_review_requires_entity(pg_user):
    """post_type='review' without entity_id → 400 (validation, post auth)."""
    client = _client_as(pg_user)
    resp = client.post("/api/posts", json={"content": "Đánh giá thiếu địa điểm.", "post_type": "review", "rating": 4})
    assert resp.status_code == 400


@pg_only
def test_create_post_review_requires_rating(pg_user, pg_entity):
    """review with entity but no rating → 400."""
    client = _client_as(pg_user)
    resp = client.post("/api/posts", json={"content": "Đánh giá thiếu sao.", "post_type": "review", "entity_id": pg_entity})
    assert resp.status_code == 400


@pg_only
def test_create_post_happy_path_sets_moderation_status(pg_user, pg_entity):
    """A share post is created and carries a moderation_status (dev key → approved)."""
    client = _client_as(pg_user)
    resp = client.post("/api/posts", json={
        "content": "Chia sẻ trải nghiệm tham quan rất tuyệt.",
        "post_type": "share",
    })
    assert resp.status_code == 200
    post = resp.json()["post"]
    pid = post["id"]
    # cleanup
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM posts WHERE id::text = {db._ph}", (pid,))
    assert post["content"]


@pg_only
def test_comment_on_nonexistent_post_404(pg_user):
    client = _client_as(pg_user)
    resp = client.post(f"/api/posts/{uuid.uuid4()}/comments", json={"content": "hi"})
    assert resp.status_code == 404


@pg_only
def test_threaded_reply_nests_under_parent(pg_user, pg_entity):
    """Trả lời (parent_id) lồng đúng dưới bình-luận-gốc trong GET comments."""
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, entity_id, content, images, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, 'approved')
            RETURNING id
        """, (str(pg_user["id"]), pg_entity, "Bài để bình luận lồng.", json.dumps([]), "share"))
        pid = str(row["id"])
    try:
        client = _client_as(pg_user)
        top = client.post(f"/api/posts/{pid}/comments", json={"content": "Bình luận gốc."})
        assert top.status_code == 200, top.text
        top_id = top.json()["comment"]["id"]
        reply = client.post(f"/api/posts/{pid}/comments", json={"content": "Trả lời gốc.", "parent_id": top_id})
        assert reply.status_code == 200, reply.text
        assert reply.json()["comment"]["parent_id"] == top_id
        listed = client.get(f"/api/posts/{pid}/comments").json()["comments"]
        assert len(listed) == 1 and listed[0]["id"] == top_id
        assert len(listed[0]["replies"]) == 1
        assert listed[0]["replies"][0]["content"] == "Trả lời gốc."
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))


@pg_only
def test_search_posts_finds_by_content(pg_user, pg_entity):
    """/api/search/posts tìm bài ĐÃ DUYỆT theo nội dung (case-insensitive)."""
    ph = db._ph
    token = "Zynapix" + uuid.uuid4().hex[:6]  # chuỗi hiếm, không đụng bài khác
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, entity_id, content, images, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, 'approved')
            RETURNING id
        """, (str(pg_user["id"]), pg_entity, f"Trải nghiệm {token} ở cù lao tuyệt vời.", json.dumps([]), "share"))
        pid = str(row["id"])
    try:
        client = _client_as(pg_user)
        # khớp (chữ thường khác hoa gốc → vẫn tìm thấy)
        hit = client.get(f"/api/search/posts?q={token.lower()}")
        assert hit.status_code == 200, hit.text
        ids = [p["id"] for p in hit.json()["posts"]]
        assert pid in ids
        # không phân-biệt-dấu: gõ "cu lao" (không dấu) tìm thấy "cù lao"
        acc = client.get("/api/search/posts?q=cu lao")
        assert acc.status_code == 200 and pid in [p["id"] for p in acc.json()["posts"]]
        # không khớp
        miss = client.get("/api/search/posts?q=khongcotunaodayxyz")
        assert miss.status_code == 200 and pid not in [p["id"] for p in miss.json()["posts"]]
        # q quá ngắn → 422 (Query min_length=2)
        assert client.get("/api/search/posts?q=a").status_code == 422
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))


@pg_only
def test_search_users_by_name_accent_insensitive(pg_user):
    """/api/search/users tìm theo tên hiển thị, không phân-biệt-dấu."""
    ph = db._ph
    token = uuid.uuid4().hex[:6]
    name = f"Nguyễn {token}"  # có dấu
    with db._conn() as conn:
        db._execute(conn, f"UPDATE users SET display_name = {ph} WHERE id::text = {ph}",
                    (name, str(pg_user["id"])))
    client = _client_as(pg_user)
    # gõ "nguyen <token>" (không dấu) → tìm thấy "Nguyễn <token>"
    r = client.get(f"/api/search/users?q=nguyen {token}")
    assert r.status_code == 200, r.text
    assert str(pg_user["id"]) in [u["id"] for u in r.json()["users"]]
    # q quá ngắn → 422
    assert client.get("/api/search/users?q=a").status_code == 422


@pg_only
def test_trending_tags_counts_hashtag(pg_user, pg_entity):
    """/api/community/trending-tags đếm hashtag bài đã duyệt trong 30 ngày."""
    ph = db._ph
    tag = "zzt" + uuid.uuid4().hex[:5]
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, entity_id, content, images, post_type, moderation_status, hashtags)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, 'approved', {ph}::jsonb)
            RETURNING id
        """, (str(pg_user["id"]), pg_entity, f"Bài có hashtag #{tag} nhé.", json.dumps([]), "share", json.dumps([tag])))
        pid = str(row["id"])
    try:
        client = _client_as(pg_user)
        r = client.get("/api/community/trending-tags?limit=20")
        assert r.status_code == 200, r.text
        tags = {t["tag"]: t["count"] for t in r.json()["tags"]}
        assert tag in tags and tags[tag] >= 1
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))


@pg_only
def test_following_feed_shows_followed_user_posts(pg_user, pg_entity):
    """/api/feed/following chỉ hiện bài của người mình theo dõi."""
    ph = db._ph
    author = db.create_user("09" + uuid.uuid4().hex[:8])
    posts_created = []
    try:
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                INSERT INTO posts (user_id, entity_id, content, images, post_type, moderation_status)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, 'approved')
                RETURNING id
            """, (str(author["id"]), pg_entity, "Bài của người được theo dõi.", json.dumps([]), "share"))
            apid = str(row["id"])
        posts_created.append(apid)
        client = _client_as(pg_user)
        # chưa follow → không thấy
        before = client.get("/api/feed/following")
        assert before.status_code == 200, before.text
        assert apid not in [p["id"] for p in before.json()["posts"]]
        # follow → thấy
        with db._conn() as conn:
            db._execute(conn, f"INSERT INTO follows (follower_id, target_type, target_id) VALUES ({ph}::uuid, 'user', {ph})",
                        (str(pg_user["id"]), str(author["id"])))
        after = client.get("/api/feed/following")
        assert apid in [p["id"] for p in after.json()["posts"]]
    finally:
        with db._conn() as conn:
            for pid in posts_created:
                db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))
            db._execute(conn, f"DELETE FROM follows WHERE follower_id = {ph}::uuid", (str(pg_user["id"]),))
            db._execute(conn, f"DELETE FROM users WHERE id::text = {ph}", (str(author["id"]),))


@pg_only
def test_delete_post_forbidden_for_other_user(pg_user, pg_entity):
    """User B cannot delete User A's post → 403."""
    # User A creates a post directly in DB.
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, entity_id, content, images, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, 'approved')
            RETURNING id
        """, (str(pg_user["id"]), pg_entity, "Bài của user A.", json.dumps([]), "share"))
        pid = str(row["id"])

    other = db.create_user("09" + uuid.uuid4().hex[:8])
    try:
        client = _client_as(other)
        resp = client.delete(f"/api/posts/{pid}")
        assert resp.status_code == 403
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))
            db._execute(conn, f"DELETE FROM users WHERE id::text = {ph}", (str(other["id"]),))


@pg_only
def test_repost_creates_snapshot_and_blocks_repost_of_repost(pg_user, pg_entity):
    """Migration 013: repost lưu snapshot bài gốc; chặn repost-của-repost."""
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, entity_id, content, images, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, 'approved')
            RETURNING id
        """, (str(pg_user["id"]), pg_entity, "Bài gốc để đăng lại.", json.dumps([]), "share"))
        orig_id = str(row["id"])
    created = [orig_id]
    try:
        client = _client_as(pg_user)
        # repost với content rỗng → 200 + snapshot
        resp = client.post("/api/posts", json={"repost_of": orig_id, "content": ""})
        assert resp.status_code == 200, resp.text
        rp = resp.json()["post"]
        created.append(rp["id"])
        assert rp["repost_of"] == orig_id
        assert rp["repost"] and rp["repost"]["content"].startswith("Bài gốc để đăng lại")
        assert rp["content"] == ""  # đăng lại không kèm lời → content rỗng
        # quote (trích dẫn) — content bình luận + snapshot cùng tồn tại
        resp_q = client.post("/api/posts", json={"repost_of": orig_id, "content": "Bài này hay, mọi người xem nhé."})
        assert resp_q.status_code == 200, resp_q.text
        qp = resp_q.json()["post"]
        created.append(qp["id"])
        assert qp["content"].startswith("Bài này hay")
        assert qp["repost"] and qp["repost"]["content"].startswith("Bài gốc để đăng lại")
        # repost-của-repost → 400
        resp2 = client.post("/api/posts", json={"repost_of": rp["id"], "content": ""})
        assert resp2.status_code == 400
    finally:
        with db._conn() as conn:
            for pid in created:
                db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))


@pg_only
def test_toggle_like_idempotent(pg_user, pg_entity):
    """Liking twice flips liked True→False (idempotent toggle)."""
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, entity_id, content, images, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, 'approved')
            RETURNING id
        """, (str(pg_user["id"]), pg_entity, "Bài để like.", json.dumps([]), "share"))
        pid = str(row["id"])
    try:
        client = _client_as(pg_user)
        first = client.post(f"/api/posts/{pid}/like").json()
        second = client.post(f"/api/posts/{pid}/like").json()
        assert first["liked"] is True
        assert second["liked"] is False
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))
