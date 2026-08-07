"""Hợp đồng "tự dọn bảng tin" — hide / unhide / danh sách bài đã ẩn.

Ba endpoint này (social.py: hide_post / unhide_post / list_hidden_posts) đã có
test cấu-trúc ở test_upgrade_round2.py::TestHidePostEndpoints (soi source: có
route, có `db._ph`, có `require_user`...). File này kiểm HÀNH VI qua TestClient
trước khi frontend nối vào, và khoá đúng điều frontend đang giả định:

  1. ẨN LÀ RIÊNG TƯ, KHÔNG PHẢI KIỂM DUYỆT — người ẩn không thấy bài nữa,
     NGƯỜI KHÁC VẪN THẤY. Nếu bất biến này vỡ thì nhãn "Ẩn bài này" trên giao
     diện đang nói dối và phải đổi trước khi ship.
  2. `GET /api/posts/hidden` phải khớp TRƯỚC `GET /api/posts/{post_id}` — nếu
     bị che thì nó trả về "bài viết có id = 'hidden'" (404), tức endpoint chết.
  3. CHỈ 3 feed lọc `user_hidden_posts`. Frontend chỉ được bật nút "Ẩn" ở đúng
     những màn hình đó; test #4 khoá danh sách endpoint có/không lọc để khi
     backend mở rộng thì có chỗ nhắc mở rộng cả frontend.

SQLite/CI: router social gắn `Depends(_require_pg)` → 503 trước mọi handler,
nên phần hành vi chạy dưới @pg_only (job `test-pg` của CI có DATABASE_URL).
"""

import inspect
import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.routing import Match  # noqa: E402

import social  # noqa: E402
from auth_middleware import get_current_user, require_user  # noqa: E402
from database import db  # noqa: E402

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="UGC là Postgres-only (SQLite trả 503). Đặt DATABASE_URL=postgresql://… để chạy.",
)

HIDE_ENDPOINTS = ("/api/posts/{post_id}/hide", "/api/posts/{post_id}/unhide", "/api/posts/hidden")


def _app(user=None):
    """Mount social.router; nếu có `user` thì ghi đè dependency auth thành user đó."""
    app = FastAPI()
    app.include_router(social.router)
    if user is not None:
        app.dependency_overrides[require_user] = lambda: user
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def _client(user=None):
    return TestClient(_app(user))


# ── 1. Wiring: route tồn tại và KHÔNG bị route param che ──────────────────

def test_three_endpoints_registered():
    paths = {getattr(r, "path", "") for r in social.router.routes}
    for path in HIDE_ENDPOINTS:
        assert path in paths, f"thiếu route {path}"


def test_hidden_list_is_not_shadowed_by_post_detail():
    """`GET /api/posts/hidden` phải khớp handler list_hidden_posts.

    `GET /api/posts/{post_id}` được khai báo ở social.py:786, TRƯỚC
    `/posts/hidden` (:3395). Starlette khớp theo THỨ TỰ đăng ký, nên nếu
    `_fix_social_route_order()` ngừng chạy/ngừng nhận diện path này thì
    `/api/posts/hidden` sẽ rơi vào get_post với post_id="hidden" → 404 vĩnh
    viễn, và trang "Bài đã ẩn" ở /cai-dat sẽ luôn rỗng mà không báo lỗi gì.
    """
    app = _app()
    scope = {"type": "http", "method": "GET", "path": "/api/posts/hidden",
             "headers": [], "root_path": ""}
    matched = None
    for route in app.routes:
        match, _child = route.matches(scope)
        if match != Match.NONE:
            matched = route
            break
    assert matched is not None, "không route nào khớp /api/posts/hidden"
    assert matched.endpoint is social.list_hidden_posts, (
        f"/api/posts/hidden bị route {matched.path} che mất "
        f"(handler={getattr(matched.endpoint, '__name__', matched.endpoint)})"
    )


def test_sqlite_returns_503_before_auth():
    """Trên SQLite mọi endpoint UGC trả 503 rõ ràng (không 500, không 404 mơ hồ)."""
    if db._use_pg:
        pytest.skip("Postgres live — guard 503 không áp dụng")
    client = _client()
    assert client.post("/api/posts/abc/hide").status_code == 503
    assert client.post("/api/posts/abc/unhide").status_code == 503
    assert client.get("/api/posts/hidden").status_code == 503


def test_hide_requires_authentication():
    """Không đăng nhập thì không ẩn được bài của người khác (401/403, không 200)."""
    if not db._use_pg:
        pytest.skip("SQLite trả 503 trước cả tầng auth")
    client = _client()
    assert client.post(f"/api/posts/{uuid.uuid4()}/hide").status_code in (401, 403)
    assert client.post(f"/api/posts/{uuid.uuid4()}/unhide").status_code in (401, 403)
    assert client.get("/api/posts/hidden").status_code in (401, 403)


# ── 2. Đúng những feed nào tôn trọng bộ lọc (khoá phạm vi cho frontend) ───

def test_only_feed_endpoints_filter_hidden_posts():
    """Danh sách endpoint CÓ và KHÔNG lọc `user_hidden_posts`.

    Frontend chỉ bật nút "Ẩn bài này" ở màn hình đọc từ nhóm CÓ. Nếu backend
    thêm bộ lọc cho một endpoint nhóm KHÔNG, test này đỏ — đó là tín hiệu để
    mở rộng `canHidePosts` bên web-nuxt (pages/cong-dong.vue), đừng chỉ sửa
    danh sách dưới đây cho xanh.
    """
    filters_hidden = (
        social._feed_build_conditions,   # GET /api/feed (+ ?sort=trending)
        social.get_following_feed,       # GET /api/feed/following
        social.get_friend_reviews,       # GET /api/feed/friend-reviews
    )
    no_filter = (
        social.get_my_bookmarks,         # GET /api/me/bookmarks
        social.get_user_posts,           # GET /api/users/{id}/posts
        social.search_posts,             # GET /api/search/posts
        social.get_entity_feed,          # GET /api/entities/{id}/feed
    )
    for fn in filters_hidden:
        assert "user_hidden_posts" in inspect.getsource(fn), f"{fn.__name__} phải lọc bài đã ẩn"
    for fn in no_filter:
        assert "user_hidden_posts" not in inspect.getsource(fn), (
            f"{fn.__name__} nay CÓ lọc bài đã ẩn — mở rộng canHidePosts ở "
            f"web-nuxt/pages/cong-dong.vue rồi cập nhật danh sách này"
        )


# ── 3. Hành vi thật trên Postgres ─────────────────────────────────────────

@pytest.fixture
def pg_users():
    """Ba người: tác giả bài, người ẩn, người xem khác. Xoá sạch khi xong."""
    made = [db.create_user("09" + uuid.uuid4().hex[:8]) for _ in range(3)]
    yield made
    with db._conn() as conn:
        for u in made:
            db._execute(conn, f"DELETE FROM users WHERE id::text = {db._ph}", (str(u["id"]),))


@pytest.fixture
def pg_post(pg_users):
    """Một bài đã duyệt của tác giả, gắn hashtag duy nhất để lọc feed tất định."""
    author = pg_users[0]
    tag = "andi" + uuid.uuid4().hex[:8]
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, content, images, hashtags, post_type, moderation_status)
            VALUES ({ph}::uuid, {ph}, {ph}::jsonb, {ph}::jsonb, 'share', 'approved')
            RETURNING id
        """, (str(author["id"]), f"Ghi chép ven sông Cổ Chiên #{tag}",
              json.dumps([]), json.dumps([tag])))
        pid = str(row["id"])
    yield pid, tag
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (pid,))


def _feed_ids(user, tag):
    """Id bài trong /api/feed?tag=… dưới con mắt của `user` (None = khách)."""
    res = _client(user).get(f"/api/feed?tag={tag}&limit=50")
    assert res.status_code == 200, res.text
    return [p["id"] for p in res.json()["posts"]]


@pg_only
def test_hide_is_private_not_moderation(pg_users, pg_post):
    """Bất biến số 1: ẩn chỉ tác động lên bảng tin của CHÍNH người ẩn."""
    _author, hider, other = pg_users
    pid, tag = pg_post

    assert pid in _feed_ids(hider, tag), "tiền đề sai: bài chưa có trong feed"
    assert pid in _feed_ids(other, tag)

    res = _client(hider).post(f"/api/posts/{pid}/hide")
    assert res.status_code == 200, res.text
    assert res.json()["success"] is True

    assert pid not in _feed_ids(hider, tag), "bài vẫn còn trong feed của người đã ẩn"
    assert pid in _feed_ids(other, tag), "ẩn bị rò sang người khác — đây là kiểm duyệt, không phải ẩn riêng tư"


@pg_only
def test_hidden_list_is_per_user(pg_users, pg_post):
    """`GET /api/posts/hidden` chỉ trả bài do chính người gọi ẩn."""
    _author, hider, other = pg_users
    pid, _tag = pg_post
    assert _client(hider).post(f"/api/posts/{pid}/hide").status_code == 200

    mine = _client(hider).get("/api/posts/hidden")
    assert mine.status_code == 200, mine.text
    body = mine.json()
    assert pid in [p["id"] for p in body["posts"]]
    assert body["total"] >= 1
    assert body["page"] == 1 and body["has_more"] is False

    theirs = _client(other).get("/api/posts/hidden")
    assert theirs.status_code == 200
    assert pid not in [p["id"] for p in theirs.json()["posts"]]


@pg_only
def test_hidden_list_carries_fields_the_ui_renders(pg_users, pg_post):
    """Danh sách phải đủ trường để trang /cai-dat vẽ được dòng (không chỉ id)."""
    _author, hider, _other = pg_users
    pid, _tag = pg_post
    assert _client(hider).post(f"/api/posts/{pid}/hide").status_code == 200

    row = next(p for p in _client(hider).get("/api/posts/hidden").json()["posts"] if p["id"] == pid)
    assert row.get("content"), "thiếu content → không có gì để hiển thị trong danh sách"
    assert "display_name" in row and "created_at" in row


@pg_only
def test_unhide_restores_post_to_feed(pg_users, pg_post):
    """Bỏ ẩn đưa bài về feed và rời danh sách đã ẩn — đường lùi phải thật."""
    _author, hider, _other = pg_users
    pid, tag = pg_post
    assert _client(hider).post(f"/api/posts/{pid}/hide").status_code == 200
    assert pid not in _feed_ids(hider, tag)

    res = _client(hider).post(f"/api/posts/{pid}/unhide")
    assert res.status_code == 200, res.text

    assert pid in _feed_ids(hider, tag)
    assert pid not in [p["id"] for p in _client(hider).get("/api/posts/hidden").json()["posts"]]


@pg_only
def test_hide_is_idempotent(pg_users, pg_post):
    """Bấm hai lần (mạng chậm, người dùng bấm lại) không vỡ và không nhân đôi dòng."""
    _author, hider, _other = pg_users
    pid, _tag = pg_post
    assert _client(hider).post(f"/api/posts/{pid}/hide").status_code == 200
    assert _client(hider).post(f"/api/posts/{pid}/hide").status_code == 200

    hidden = [p["id"] for p in _client(hider).get("/api/posts/hidden").json()["posts"]]
    assert hidden.count(pid) == 1


@pg_only
def test_unhide_unknown_post_is_noop(pg_users):
    """Bỏ ẩn bài chưa từng ẩn: 200 im lặng (frontend không cần nhánh lỗi riêng)."""
    _author, hider, _other = pg_users
    assert _client(hider).post(f"/api/posts/{uuid.uuid4()}/unhide").status_code == 200


@pg_only
def test_hide_nonexistent_post_404(pg_users):
    """Ẩn bài không tồn tại trả 404 — frontend hoàn nguyên và báo lỗi được."""
    _author, hider, _other = pg_users
    res = _client(hider).post(f"/api/posts/{uuid.uuid4()}/hide")
    assert res.status_code == 404


@pg_only
def test_following_feed_also_hides(pg_users, pg_post):
    """Tab "Đang theo dõi" cũng phải tôn trọng bài đã ẩn (frontend bật nút ở đó)."""
    author, hider, _other = pg_users
    pid, _tag = pg_post
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO follows (follower_id, target_type, target_id)
            VALUES ({ph}::uuid, 'user', {ph})
        """, (str(hider["id"]), str(author["id"])))
    try:
        before = _client(hider).get("/api/feed/following?limit=50")
        assert before.status_code == 200, before.text
        assert pid in [p["id"] for p in before.json()["posts"]]

        assert _client(hider).post(f"/api/posts/{pid}/hide").status_code == 200

        after = _client(hider).get("/api/feed/following?limit=50")
        assert pid not in [p["id"] for p in after.json()["posts"]]
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM follows WHERE follower_id = {ph}::uuid",
                        (str(hider["id"]),))


@pg_only
def test_bookmarks_do_not_filter_hidden(pg_users, pg_post):
    """Giới hạn ĐANG CÓ THẬT: /api/me/bookmarks KHÔNG lọc bài đã ẩn.

    Đây là lý do frontend TẮT nút "Ẩn" ở tab "Đã lưu" (canHidePosts trong
    web-nuxt/pages/cong-dong.vue): bật ở đó thì bài biến mất rồi quay lại sau
    khi tải lại trang. Test này đỏ = backend đã lọc → hãy mở rộng frontend.
    """
    _author, hider, _other = pg_users
    pid, _tag = pg_post
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO bookmarks (user_id, post_id) VALUES ({ph}::uuid, {ph}::uuid)
            ON CONFLICT DO NOTHING
        """, (str(hider["id"]), pid))
    try:
        assert _client(hider).post(f"/api/posts/{pid}/hide").status_code == 200
        res = _client(hider).get("/api/me/bookmarks?limit=50")
        assert res.status_code == 200, res.text
        assert pid in [p["id"] for p in res.json()["posts"]], (
            "bookmarks nay ĐÃ lọc bài ẩn — cập nhật canHidePosts ở frontend "
            "rồi sửa test này"
        )
    finally:
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM bookmarks WHERE post_id = {ph}::uuid", (pid,))
