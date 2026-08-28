# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI của miền TƯƠNG TÁC (community.api) trên PostgreSQL thật.

Phủ các handler/closure chưa từng chạy trên DB thật: toggle_like/_like_check_self,
get_post_likers, toggle_comment_like, toggle_reaction, get_reactions, bookmark
(toggle/get_my), collections (list/delete/add/remove/items), track_share,
hide/unhide/list_hidden, pin_comment/unpin_comment, pin_post_to_profile.

Khuôn harness: adapter Database() ép `_use_pg=True` + `_dsn` trỏ DB test riêng,
monkeypatch vào ĐÚNG module thực thi (community.api). Side-effect ngoài miền
(create_notification, check_rate, check_rate_ip) được stub ghi-nhận-lời-gọi —
không cho module notifications/ratelimit chạm db toàn cục của chúng.

Toggle nào cũng test cả hai chiều bật/tắt và đọc lại bằng SQL để chứng minh
hàng đã vào/ra bảng đúng giá trị.
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException

import database as database_module
from community import api as community_api


def _test_database_url() -> str | None:
    url = os.environ.get("UGC_SURFACE_TEST_DATABASE_URL")
    if not url:
        return None

    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    explicitly_allowed = os.environ.get(
        "UGC_SURFACE_ALLOW_PG_TESTS", ""
    ).lower() in {"1", "true", "yes", "on"}
    if parsed.scheme not in {"postgres", "postgresql"} or not database_name:
        raise pytest.UsageError(
            "UGC_SURFACE_TEST_DATABASE_URL must be a PostgreSQL URL"
        )
    if "test" not in database_name.lower() and not explicitly_allowed:
        raise pytest.UsageError(
            "PostgreSQL UGC-surface tests require a database name containing "
            "'test' or UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL UGC-surface tests require "
            "UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set UGC_SURFACE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)

_TRUNCATE_SQL = (
    "TRUNCATE post_reactions, comment_likes, likes, bookmarks, collection_items, "
    "user_collections, user_hidden_posts, blocks, comments, posts, users CASCADE"
)


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    monkeypatch.setattr(community_api, "db", adapter)

    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(_TRUNCATE_SQL)
    try:
        yield adapter
    finally:
        with psycopg2.connect(TEST_DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(_TRUNCATE_SQL)


@pytest.fixture(autouse=True)
def side_effects(monkeypatch):
    """Stub side-effect ngoài miền: notifications + ratelimit (ghi nhận lời gọi)."""
    calls = {"notify": [], "rate": [], "rate_ip": []}
    monkeypatch.setattr(
        community_api, "create_notification",
        lambda *a, **k: calls["notify"].append((a, k)),
    )
    monkeypatch.setattr(
        community_api, "check_rate", lambda *a, **k: calls["rate"].append(a)
    )
    monkeypatch.setattr(
        community_api, "check_rate_ip", lambda *a, **k: calls["rate_ip"].append(a)
    )
    return calls


# ── Seed helpers (SQL thẳng qua adapter, dữ liệu ngẫu nhiên mỗi test) ──

def _seed_user(pg_db, display_name="Người dùng thử") -> str:
    user_id = str(uuid.uuid4())
    phone = f"test-{uuid.uuid4().hex}"
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO users (id, phone, display_name) VALUES (%s::uuid, %s, %s)",
            (user_id, phone, display_name),
        )
    return user_id


def _user(uid: str, name="Người dùng thử") -> dict:
    return {"id": uid, "display_name": name, "role": "user"}


def _seed_post(pg_db, user_id: str, content="Bài kiểm thử",
               moderation_status="approved", is_pinned=False) -> str:
    post_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO posts (id, user_id, content, moderation_status, is_pinned)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s)
            """,
            (post_id, user_id, content, moderation_status, is_pinned),
        )
    return post_id


def _seed_comment(pg_db, post_id: str, user_id: str, content="Bình luận thử") -> str:
    comment_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO comments (id, post_id, user_id, content)
            VALUES (%s::uuid, %s::uuid, %s::uuid, %s)
            """,
            (comment_id, post_id, user_id, content),
        )
    return comment_id


def _seed_block(pg_db, blocker_id: str, blocked_id: str) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s::uuid, %s::uuid)",
            (blocker_id, blocked_id),
        )


def _seed_collection(pg_db, user_id: str, name="Bộ sưu tập thử", is_public=False) -> str:
    collection_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_collections (id, user_id, name, is_public)
            VALUES (%s::uuid, %s::uuid, %s, %s)
            """,
            (collection_id, user_id, name, is_public),
        )
    return collection_id


def _seed_collection_item(pg_db, collection_id: str, post_id: str) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO collection_items (collection_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (collection_id, post_id),
        )


def _row(pg_db, sql: str, params=()) -> dict | None:
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(conn, sql, params)
    return pg_db._row_to_dict(row) if row is not None else None


def _count(pg_db, sql: str, params=()) -> int:
    return _row(pg_db, sql, params)["c"]


def _request() -> SimpleNamespace:
    return SimpleNamespace(headers={}, client=None, cookies={})


# ── toggle_like + _like_check_self ──

def test_toggle_like_both_directions_with_sql_readback(pg_db, side_effects):
    author = _seed_user(pg_db, "Tác giả")
    liker = _seed_user(pg_db, "Người thích")
    post_id = _seed_post(pg_db, author)

    res_on = asyncio.run(
        community_api.toggle_like(post_id, user=_user(liker, "Người thích"), _csrf=None)
    )
    assert res_on["liked"] is True
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM likes WHERE user_id = %s::uuid AND post_id = %s::uuid",
        (liker, post_id),
    ) == 1
    # Trigger trg_like_count đã cập nhật đếm trên posts sau statement.
    assert _row(pg_db, "SELECT like_count FROM posts WHERE id = %s::uuid", (post_id,))[
        "like_count"
    ] == 1
    # Thông báo gửi đúng chủ bài, đúng actor.
    assert len(side_effects["notify"]) == 1
    notify_args, notify_kwargs = side_effects["notify"][0]
    assert notify_args[0] == author
    assert notify_args[1] == "like"
    assert notify_kwargs["actor_id"] == liker
    # LƯU Ý (không khoá bằng assertion): like_count trong response đọc trong
    # CÙNG statement với CTE insert nên là giá trị TRƯỚC toggle (đo được 0 dù
    # DB sau statement là 1) — nghi ngờ bug, ghi ở báo cáo, không đặc tả cứng.
    assert "like_count" in res_on

    res_off = asyncio.run(
        community_api.toggle_like(post_id, user=_user(liker, "Người thích"), _csrf=None)
    )
    assert res_off["liked"] is False
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM likes WHERE user_id = %s::uuid AND post_id = %s::uuid",
        (liker, post_id),
    ) == 0
    assert _row(pg_db, "SELECT like_count FROM posts WHERE id = %s::uuid", (post_id,))[
        "like_count"
    ] == 0
    # Unlike không gửi thêm thông báo.
    assert len(side_effects["notify"]) == 1


def test_toggle_like_rejects_self_and_missing_post(pg_db):
    author = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.toggle_like(post_id, user=_user(author), _csrf=None))
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.toggle_like(str(uuid.uuid4()), user=_user(author), _csrf=None)
        )
    assert exc.value.status_code == 404
    assert _count(pg_db, "SELECT COUNT(*) AS c FROM likes") == 0


def test_toggle_like_blocked_pair_returns_403(pg_db):
    author = _seed_user(pg_db)
    liker = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)
    _seed_block(pg_db, author, liker)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.toggle_like(post_id, user=_user(liker), _csrf=None))
    assert exc.value.status_code == 403
    assert _count(pg_db, "SELECT COUNT(*) AS c FROM likes") == 0


# ── get_post_likers ──

def test_get_post_likers_lists_and_excludes_blocked_viewer_pair(pg_db, monkeypatch):
    author = _seed_user(pg_db, "Tác giả")
    liker = _seed_user(pg_db, "Người thích")
    viewer_blocking = _seed_user(pg_db, "Người xem có chặn")
    post_id = _seed_post(pg_db, author)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO likes (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (liker, post_id),
        )

    viewer_holder = {"user": _user(author, "Tác giả")}

    async def _fake_current_user(_request):
        return viewer_holder["user"]

    monkeypatch.setattr(community_api, "get_current_user", _fake_current_user)

    res = asyncio.run(community_api.get_post_likers(post_id, _request(), limit=20))
    assert res["total"] == 1
    assert res["has_more"] is False
    assert len(res["likers"]) == 1
    assert res["likers"][0]["id"] == liker
    assert res["likers"][0]["display_name"] == "Người thích"
    assert res["likers"][0]["liked_at"]

    # Người xem đã chặn người thích → bị loại khỏi danh sách lẫn tổng đếm.
    _seed_block(pg_db, viewer_blocking, liker)
    viewer_holder["user"] = _user(viewer_blocking)
    res_blocked = asyncio.run(
        community_api.get_post_likers(post_id, _request(), limit=20)
    )
    assert res_blocked["total"] == 0
    assert res_blocked["likers"] == []


# ── toggle_comment_like ──

def test_toggle_comment_like_both_directions_with_sql_readback(pg_db):
    author = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    liker = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)
    comment_id = _seed_comment(pg_db, post_id, commenter)

    res_on = asyncio.run(
        community_api.toggle_comment_like(comment_id, user=_user(liker), _csrf=None)
    )
    assert res_on == {"liked": True, "like_count": 1}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM comment_likes WHERE user_id = %s::uuid AND comment_id = %s::uuid",
        (liker, comment_id),
    ) == 1
    assert _row(
        pg_db, "SELECT like_count FROM comments WHERE id = %s::uuid", (comment_id,)
    )["like_count"] == 1

    res_off = asyncio.run(
        community_api.toggle_comment_like(comment_id, user=_user(liker), _csrf=None)
    )
    assert res_off == {"liked": False, "like_count": 0}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM comment_likes WHERE comment_id = %s::uuid",
        (comment_id,),
    ) == 0
    assert _row(
        pg_db, "SELECT like_count FROM comments WHERE id = %s::uuid", (comment_id,)
    )["like_count"] == 0


def test_toggle_comment_like_error_branches(pg_db):
    author = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    blocked_liker = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)
    comment_id = _seed_comment(pg_db, post_id, commenter)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.toggle_comment_like(
                str(uuid.uuid4()), user=_user(commenter), _csrf=None
            )
        )
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.toggle_comment_like(
                comment_id, user=_user(commenter), _csrf=None
            )
        )
    assert exc.value.status_code == 400

    _seed_block(pg_db, blocked_liker, commenter)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.toggle_comment_like(
                comment_id, user=_user(blocked_liker), _csrf=None
            )
        )
    assert exc.value.status_code == 403
    assert _count(pg_db, "SELECT COUNT(*) AS c FROM comment_likes") == 0


# ── toggle_reaction + get_reactions ──

def test_toggle_reaction_both_directions_with_notification(pg_db, side_effects):
    author = _seed_user(pg_db, "Tác giả")
    reactor = _seed_user(pg_db, "Người thả cảm xúc")
    post_id = _seed_post(pg_db, author)

    res_on = asyncio.run(
        community_api.toggle_reaction(
            post_id, reaction_type="heart",
            user=_user(reactor, "Người thả cảm xúc"), _csrf=None,
        )
    )
    assert res_on["reacted"] is True
    assert res_on["reaction_type"] == "heart"
    assert res_on["reactions"] == {"heart": 1}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM post_reactions "
        "WHERE post_id = %s::uuid AND user_id = %s::uuid AND reaction_type = 'heart'",
        (post_id, reactor),
    ) == 1
    assert len(side_effects["notify"]) == 1
    notify_args, notify_kwargs = side_effects["notify"][0]
    assert notify_args[0] == author
    assert notify_args[1] == "reaction"
    assert notify_kwargs["actor_id"] == reactor

    res_off = asyncio.run(
        community_api.toggle_reaction(
            post_id, reaction_type="heart", user=_user(reactor), _csrf=None
        )
    )
    assert res_off["reacted"] is False
    assert res_off["reactions"] == {}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM post_reactions WHERE post_id = %s::uuid",
        (post_id,),
    ) == 0
    # Gỡ cảm xúc không gửi thêm thông báo.
    assert len(side_effects["notify"]) == 1


def test_toggle_reaction_error_branches(pg_db):
    author = _seed_user(pg_db)
    reactor = _seed_user(pg_db)
    approved_post = _seed_post(pg_db, author)
    pending_post = _seed_post(pg_db, author, moderation_status="pending")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.toggle_reaction(
                approved_post, reaction_type="wow", user=_user(reactor), _csrf=None
            )
        )
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.toggle_reaction(
                pending_post, reaction_type="heart", user=_user(reactor), _csrf=None
            )
        )
    assert exc.value.status_code == 404

    _seed_block(pg_db, author, reactor)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.toggle_reaction(
                approved_post, reaction_type="heart", user=_user(reactor), _csrf=None
            )
        )
    assert exc.value.status_code == 403
    assert _count(pg_db, "SELECT COUNT(*) AS c FROM post_reactions") == 0


def test_get_reactions_counts_grouped_by_type(pg_db):
    author = _seed_user(pg_db)
    first = _seed_user(pg_db)
    second = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)
    with pg_db._conn() as conn:
        for uid, rtype in ((first, "heart"), (second, "heart"), (second, "useful")):
            pg_db._execute(
                conn,
                "INSERT INTO post_reactions (post_id, user_id, reaction_type) "
                "VALUES (%s::uuid, %s::uuid, %s)",
                (post_id, uid, rtype),
            )

    res = asyncio.run(community_api.get_reactions(post_id))
    assert res == {"reactions": {"heart": 2, "useful": 1}, "total": 3}


# ── Bookmarks ──

def test_toggle_bookmark_both_directions_with_sql_readback(pg_db):
    author = _seed_user(pg_db)
    reader = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)

    res_on = asyncio.run(
        community_api.toggle_bookmark(post_id, user=_user(reader), _csrf=None)
    )
    assert res_on == {"bookmarked": True}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM bookmarks WHERE user_id = %s::uuid AND post_id = %s::uuid",
        (reader, post_id),
    ) == 1

    res_off = asyncio.run(
        community_api.toggle_bookmark(post_id, user=_user(reader), _csrf=None)
    )
    assert res_off == {"bookmarked": False}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM bookmarks WHERE user_id = %s::uuid",
        (reader,),
    ) == 0


def test_get_my_bookmarks_lists_only_approved_posts(pg_db):
    author = _seed_user(pg_db, "Tác giả")
    reader = _seed_user(pg_db)
    approved_post = _seed_post(pg_db, author, content="Bài đã duyệt")
    pending_post = _seed_post(pg_db, author, moderation_status="pending")
    with pg_db._conn() as conn:
        for pid in (approved_post, pending_post):
            pg_db._execute(
                conn,
                "INSERT INTO bookmarks (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
                (reader, pid),
            )

    res = asyncio.run(
        community_api.get_my_bookmarks(page=1, limit=20, user=_user(reader))
    )
    assert res["total"] == 1
    assert res["page"] == 1
    assert res["has_more"] is False
    assert len(res["posts"]) == 1
    assert res["posts"][0]["id"] == approved_post
    assert res["posts"][0]["content"] == "Bài đã duyệt"
    assert res["posts"][0]["author"]["display_name"] == "Tác giả"
    assert res["posts"][0]["reactions"] == {}


# ── Collections ──

def test_list_my_collections_with_item_counts(pg_db):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    collection_id = _seed_collection(pg_db, owner, name="Điểm muốn ghé")
    _seed_collection(pg_db, stranger, name="Của người khác")
    for _ in range(2):
        post_id = _seed_post(pg_db, owner)
        _seed_collection_item(pg_db, collection_id, post_id)

    res = asyncio.run(community_api.list_my_collections(user=_user(owner)))
    assert len(res["collections"]) == 1
    coll = res["collections"][0]
    assert coll["id"] == collection_id
    assert coll["name"] == "Điểm muốn ghé"
    assert coll["item_count"] == 2
    assert coll["is_public"] is False


def test_delete_collection_cascades_items_and_404_for_foreign(pg_db):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    collection_id = _seed_collection(pg_db, owner)
    post_id = _seed_post(pg_db, owner)
    _seed_collection_item(pg_db, collection_id, post_id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.delete_collection(
                collection_id, user=_user(stranger), _csrf=None
            )
        )
    assert exc.value.status_code == 404
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM user_collections WHERE id = %s::uuid",
        (collection_id,),
    ) == 1

    res = asyncio.run(
        community_api.delete_collection(collection_id, user=_user(owner), _csrf=None)
    )
    assert res == {"success": True}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM user_collections WHERE id = %s::uuid",
        (collection_id,),
    ) == 0
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM collection_items WHERE collection_id = %s::uuid",
        (collection_id,),
    ) == 0


def test_add_to_collection_inserts_item_and_bumps_updated_at(pg_db):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    collection_id = _seed_collection(pg_db, owner)
    post_id = _seed_post(pg_db, owner)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE user_collections SET updated_at = NOW() - INTERVAL '1 hour' "
            "WHERE id = %s::uuid",
            (collection_id,),
        )
    stale_updated_at = _row(
        pg_db,
        "SELECT updated_at FROM user_collections WHERE id = %s::uuid",
        (collection_id,),
    )["updated_at"]

    res = asyncio.run(
        community_api.add_to_collection(
            collection_id, post_id=post_id, user=_user(owner), _csrf=None, _idem=None
        )
    )
    assert res == {"success": True}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM collection_items "
        "WHERE collection_id = %s::uuid AND post_id = %s::uuid",
        (collection_id, post_id),
    ) == 1
    fresh_updated_at = _row(
        pg_db,
        "SELECT updated_at FROM user_collections WHERE id = %s::uuid",
        (collection_id,),
    )["updated_at"]
    assert fresh_updated_at > stale_updated_at

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.add_to_collection(
                collection_id, post_id=post_id,
                user=_user(stranger), _csrf=None, _idem=None,
            )
        )
    assert exc.value.status_code == 404


def test_add_to_collection_full_returns_400(pg_db):
    owner = _seed_user(pg_db)
    collection_id = _seed_collection(pg_db, owner)
    extra_post = _seed_post(pg_db, owner)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            WITH new_posts AS (
                INSERT INTO posts (user_id, content, moderation_status)
                SELECT %s::uuid, 'bài lót đầy danh sách', 'approved'
                FROM generate_series(1, 100)
                RETURNING id
            )
            INSERT INTO collection_items (collection_id, post_id)
            SELECT %s::uuid, id FROM new_posts
            """,
            (owner, collection_id),
        )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.add_to_collection(
                collection_id, post_id=extra_post,
                user=_user(owner), _csrf=None, _idem=None,
            )
        )
    assert exc.value.status_code == 400
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM collection_items WHERE collection_id = %s::uuid",
        (collection_id,),
    ) == 100


def test_remove_from_collection_deletes_item_and_404_for_foreign(pg_db):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    collection_id = _seed_collection(pg_db, owner)
    post_id = _seed_post(pg_db, owner)
    _seed_collection_item(pg_db, collection_id, post_id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.remove_from_collection(
                collection_id, post_id, user=_user(stranger), _csrf=None
            )
        )
    assert exc.value.status_code == 404

    res = asyncio.run(
        community_api.remove_from_collection(
            collection_id, post_id, user=_user(owner), _csrf=None
        )
    )
    assert res == {"success": True}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM collection_items WHERE collection_id = %s::uuid",
        (collection_id,),
    ) == 0


def test_get_collection_items_owner_sees_approved_posts(pg_db):
    owner = _seed_user(pg_db)
    collection_id = _seed_collection(pg_db, owner)
    approved_post = _seed_post(pg_db, owner, content="Bài trong bộ sưu tập")
    pending_post = _seed_post(pg_db, owner, moderation_status="pending")
    _seed_collection_item(pg_db, collection_id, approved_post)
    _seed_collection_item(pg_db, collection_id, pending_post)

    res = asyncio.run(
        community_api.get_collection_items(
            collection_id, page=1, limit=20, user=_user(owner)
        )
    )
    assert res["total"] == 1
    assert len(res["posts"]) == 1
    assert res["posts"][0]["id"] == approved_post
    assert res["posts"][0]["is_bookmarked"] is False

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.get_collection_items(
                str(uuid.uuid4()), page=1, limit=20, user=_user(owner)
            )
        )
    assert exc.value.status_code == 404


def test_get_collection_items_privacy_gate(pg_db):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    private_collection = _seed_collection(pg_db, owner, is_public=False)
    public_collection = _seed_collection(pg_db, owner, name="Công khai", is_public=True)
    post_id = _seed_post(pg_db, owner)
    _seed_collection_item(pg_db, public_collection, post_id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.get_collection_items(
                private_collection, page=1, limit=20, user=_user(stranger)
            )
        )
    assert exc.value.status_code == 403

    res = asyncio.run(
        community_api.get_collection_items(
            public_collection, page=1, limit=20, user=_user(stranger)
        )
    )
    assert res["total"] == 1
    assert res["posts"][0]["id"] == post_id


# ── track_share ──

def test_track_share_increments_counter_and_404_when_missing(pg_db):
    author = _seed_user(pg_db)
    sharer = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)

    res = asyncio.run(
        community_api.track_share(post_id, _request(), user=_user(sharer), _csrf=None)
    )
    assert res == {"share_count": 1}
    assert _row(
        pg_db, "SELECT share_count FROM posts WHERE id = %s::uuid", (post_id,)
    )["share_count"] == 1

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.track_share(
                str(uuid.uuid4()), _request(), user=_user(sharer), _csrf=None
            )
        )
    assert exc.value.status_code == 404


# ── Hide / Unhide / List hidden ──

def test_hide_unhide_and_list_hidden_posts(pg_db):
    author = _seed_user(pg_db, "Tác giả")
    viewer = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author, content="Bài sẽ bị ẩn")

    res_hide = asyncio.run(
        community_api.hide_post(post_id, user=_user(viewer), _csrf=None)
    )
    assert res_hide == {"success": True}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM user_hidden_posts "
        "WHERE user_id = %s::uuid AND post_id = %s::uuid",
        (viewer, post_id),
    ) == 1

    res_list = asyncio.run(
        community_api.list_hidden_posts(page=1, limit=20, user=_user(viewer))
    )
    assert res_list["total"] == 1
    assert len(res_list["posts"]) == 1
    assert res_list["posts"][0]["id"] == post_id
    assert res_list["posts"][0]["content"] == "Bài sẽ bị ẩn"

    res_unhide = asyncio.run(
        community_api.unhide_post(post_id, user=_user(viewer), _csrf=None)
    )
    assert res_unhide == {"success": True}
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM user_hidden_posts WHERE user_id = %s::uuid",
        (viewer,),
    ) == 0

    res_empty = asyncio.run(
        community_api.list_hidden_posts(page=1, limit=20, user=_user(viewer))
    )
    assert res_empty["total"] == 0
    assert res_empty["posts"] == []


def test_hide_post_404_when_missing(pg_db):
    viewer = _seed_user(pg_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.hide_post(str(uuid.uuid4()), user=_user(viewer), _csrf=None)
        )
    assert exc.value.status_code == 404


# ── Pin comment / Unpin comment ──

def test_pin_comment_then_unpin_with_sql_readback(pg_db):
    author = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)
    comment_id = _seed_comment(pg_db, post_id, commenter)

    res_pin = asyncio.run(
        community_api.pin_comment(
            post_id, comment_id=comment_id, user=_user(author), _csrf=None
        )
    )
    assert res_pin == {"success": True}
    assert str(
        _row(pg_db, "SELECT pinned_comment_id FROM posts WHERE id = %s::uuid", (post_id,))[
            "pinned_comment_id"
        ]
    ) == comment_id

    res_unpin = asyncio.run(
        community_api.unpin_comment(post_id, user=_user(author), _csrf=None)
    )
    assert res_unpin == {"success": True}
    assert _row(
        pg_db, "SELECT pinned_comment_id FROM posts WHERE id = %s::uuid", (post_id,)
    )["pinned_comment_id"] is None


def test_pin_comment_permission_and_wrong_post_branches(pg_db):
    author = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)
    other_post = _seed_post(pg_db, author)
    comment_id = _seed_comment(pg_db, post_id, commenter)

    # Không phải tác giả bài → 403.
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.pin_comment(
                post_id, comment_id=comment_id, user=_user(commenter), _csrf=None
            )
        )
    assert exc.value.status_code == 403

    # Bình luận không thuộc bài được ghim → 404.
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.pin_comment(
                other_post, comment_id=comment_id, user=_user(author), _csrf=None
            )
        )
    assert exc.value.status_code == 404

    # Gỡ ghim bởi người không phải tác giả → 403.
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.unpin_comment(post_id, user=_user(commenter), _csrf=None)
        )
    assert exc.value.status_code == 403
    assert _row(
        pg_db, "SELECT pinned_comment_id FROM posts WHERE id = %s::uuid", (post_id,)
    )["pinned_comment_id"] is None


# ── Pin post to profile ──

def test_pin_post_to_profile_toggle_both_directions(pg_db):
    author = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author)

    res_pin = asyncio.run(
        community_api.pin_post_to_profile(post_id, user=_user(author), _csrf=None)
    )
    assert res_pin == {"pinned": True}
    assert _row(pg_db, "SELECT is_pinned FROM posts WHERE id = %s::uuid", (post_id,))[
        "is_pinned"
    ] is True

    res_unpin = asyncio.run(
        community_api.pin_post_to_profile(post_id, user=_user(author), _csrf=None)
    )
    assert res_unpin == {"pinned": False}
    assert _row(pg_db, "SELECT is_pinned FROM posts WHERE id = %s::uuid", (post_id,))[
        "is_pinned"
    ] is False


def test_pin_post_to_profile_error_branches(pg_db):
    author = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    approved_post = _seed_post(pg_db, author)
    pending_post = _seed_post(pg_db, author, moderation_status="pending")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.pin_post_to_profile(
                approved_post, user=_user(stranger), _csrf=None
            )
        )
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.pin_post_to_profile(
                pending_post, user=_user(author), _csrf=None
            )
        )
    assert exc.value.status_code == 400

    # Đã đủ 3 bài ghim → bài thứ tư bị chặn 400, DB giữ nguyên.
    for _ in range(3):
        _seed_post(pg_db, author, is_pinned=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.pin_post_to_profile(
                approved_post, user=_user(author), _csrf=None
            )
        )
    assert exc.value.status_code == 400
    assert _row(
        pg_db, "SELECT is_pinned FROM posts WHERE id = %s::uuid", (approved_post,)
    )["is_pinned"] is False
