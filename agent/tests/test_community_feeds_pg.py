# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI của miền FEED/KHÁM PHÁ (community.api) trên PostgreSQL thật.

Phủ các closure `_query` chưa từng chạy trên DB thật: feed chính, following,
friend-reviews, trending, explore, search (bài + người), stats/counts/activity,
hashtag, leaderboard, follows, entity feed và related posts. Mỗi test tự seed
dữ liệu riêng (uuid ngẫu nhiên) và fixture TRUNCATE quanh mỗi test.

Ghi chú bẫy trục-4: db được patch vào ĐÚNG module thực thi query
(community.api + profile_access — resolve_profile_access chạy SQL bằng db
riêng của nó). Các handler miền feed là đường ĐỌC, không có side-effect
notify/achievement; riêng check_rate được stub tại community.api.
"""
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException, Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database as database_module
import profile_access
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
            "PostgreSQL feed-surface tests require a database name containing "
            "'test' or UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL feed-surface tests require "
            "UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set UGC_SURFACE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)

_TABLES = (
    "post_reactions", "user_collections", "user_privacy", "entity_ratings",
    "user_hidden_posts", "user_mutes", "blocks", "bookmarks", "saved_entities",
    "user_visits", "notifications", "likes", "comments", "follows", "posts",
    "entities", "users",
)


def _truncate_all():
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE {', '.join(_TABLES)} CASCADE")


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    # Schema đã migrate đủ 81 bước từ trước; bỏ qua verify-schema lúc
    # get_entity gọi initialize() để không kéo cache detail ngoài miền.
    adapter._initialized = True
    monkeypatch.setattr(community_api, "db", adapter)
    monkeypatch.setattr(profile_access, "db", adapter)
    # Cache module-level phải sạch giữa các test (trending + leaderboard).
    community_api._trending_cache["ts"] = 0.0
    community_api._trending_cache["data"] = {}
    community_api._leaderboard_cache.clear()
    _truncate_all()
    try:
        yield adapter
    finally:
        _truncate_all()


# ── Seed helpers (SQL INSERT qua adapter PG) ──


def _seed_user(pg_db, display_name="Người dùng", username=None,
               active=True, deleted=False):
    user_id = str(uuid.uuid4())
    username = username or f"u{uuid.uuid4().hex[:12]}"
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (id, phone, display_name, username, is_active, deleted_at)
            VALUES (%s::uuid, %s, %s, %s, %s, %s)
            """,
            (
                user_id, f"test-{uuid.uuid4().hex}", display_name, username,
                active, datetime.now(timezone.utc) if deleted else None,
            ),
        )
    return user_id


def _viewer(user_id, display_name="Người xem", reputation=0):
    return {"id": user_id, "role": "user", "display_name": display_name,
            "reputation": reputation}


def _seed_post(pg_db, user_id, *, content="Một bài viết đủ dài mười ký tự.",
               post_type="share", rating=None, entity_id=None,
               status="approved", hashtags=(), like_count=0, comment_count=0,
               created_at=None, deleted=False, is_draft=False):
    post_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO posts (id, user_id, entity_id, content, post_type, rating,
                               moderation_status, like_count, comment_count,
                               hashtags, is_draft, deleted_at, created_at)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s,
                    %s, COALESCE(%s::timestamptz, NOW()))
            """,
            (
                post_id, user_id, entity_id, content, post_type, rating,
                status, like_count, comment_count,
                json.dumps(list(hashtags), ensure_ascii=False), is_draft,
                datetime.now(timezone.utc) if deleted else None, created_at,
            ),
        )
    return post_id


def _seed_entity(pg_db, *, entity_type="place", name="Chợ nổi thử",
                 summary="", area=None, season=None, place_id=None):
    entity_id = f"ent-{uuid.uuid4().hex[:12]}"
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO entities (id, type, name, summary, season, area, "placeId")
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                entity_id, entity_type, name, summary,
                json.dumps(season, ensure_ascii=False) if season else None,
                area, place_id,
            ),
        )
    return entity_id


def _seed_follow(pg_db, follower_id, target_id, target_type="user"):
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO follows (follower_id, target_type, target_id) VALUES (%s::uuid, %s, %s)",
            (follower_id, target_type, str(target_id)),
        )


def _seed_block(pg_db, blocker_id, blocked_id):
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s::uuid, %s::uuid)",
            (blocker_id, blocked_id),
        )


def _seed_mute(pg_db, user_id, muted_id):
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO user_mutes (user_id, muted_id) VALUES (%s::uuid, %s::uuid)",
            (user_id, muted_id),
        )


def _hide_post(pg_db, user_id, post_id):
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO user_hidden_posts (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (user_id, post_id),
        )


def _seed_privacy(pg_db, user_id, visibility="public", show_activity=True):
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_privacy (user_id, profile_visibility, show_activity)
            VALUES (%s::uuid, %s, %s)
            """,
            (user_id, visibility, show_activity),
        )


def _post_ids(result):
    return {p["id"] for p in result["posts"]}


def _run_feed(user=None, **kw):
    args = dict(page=1, limit=20, post_type=None, entity_type=None, area=None, tag=None)
    args.update(kw)
    return asyncio.run(community_api.get_feed(user=user, **args))


# ── _feed_build_conditions (helper thuần) ──


def test_feed_build_conditions_anonymous_defaults(pg_db):
    conditions, params = community_api._feed_build_conditions(
        "%s", None, None, None, None, None
    )
    assert conditions == ["p.moderation_status = 'approved'", "p.deleted_at IS NULL"]
    assert params == []


def test_feed_build_conditions_filters_and_viewer(pg_db):
    viewer_id = str(uuid.uuid4())
    conditions, params = community_api._feed_build_conditions(
        "%s", "review", "place", "vinh-long", "#Xoài", _viewer(viewer_id)
    )
    assert "p.post_type = %s" in conditions
    assert "e.type = %s" in conditions
    assert any('e."placeId" IN' in c for c in conditions)
    # tag hạ chữ + bỏ '#' rồi mới đóng gói jsonb
    assert json.dumps(["xoài"]) in params
    # viewer thêm block (2 uid) + mute (1 uid) + hidden (1 uid)
    assert params.count(viewer_id) == 4
    # post_type ngoài whitelist thì KHÔNG thêm điều kiện
    loose, loose_params = community_api._feed_build_conditions(
        "%s", "bogus-type", None, None, None, None
    )
    assert loose == ["p.moderation_status = 'approved'", "p.deleted_at IS NULL"]
    assert loose_params == []


# ── get_feed ──


def test_get_feed_filters_visibility_and_boost(pg_db):
    author = _seed_user(pg_db, "Tác giả")
    viewer_id = _seed_user(pg_db, "Người xem")
    blocked = _seed_user(pg_db, "Bị chặn")
    muted = _seed_user(pg_db, "Bị ẩn tiếng")
    stranger = _seed_user(pg_db, "Người lạ")
    viewer = _viewer(viewer_id)
    _seed_block(pg_db, viewer_id, blocked)
    _seed_mute(pg_db, viewer_id, muted)

    month_str = str(datetime.now(timezone.utc).month)
    ent = _seed_entity(
        pg_db, season={"peak": [month_str], "months": [month_str]}
    )
    now = datetime.now(timezone.utc)
    post_ok = _seed_post(pg_db, author, created_at=now - timedelta(hours=2))
    post_boosted = _seed_post(
        pg_db, stranger, entity_id=ent, created_at=now - timedelta(hours=5)
    )
    post_review = _seed_post(
        pg_db, author, post_type="review", rating=5, hashtags=("xoai",),
        created_at=now - timedelta(hours=3),
    )
    _seed_post(pg_db, author, status="pending")
    _seed_post(pg_db, author, deleted=True)
    post_blocked = _seed_post(pg_db, blocked)
    post_muted = _seed_post(pg_db, muted)
    post_hidden = _seed_post(pg_db, stranger)
    _hide_post(pg_db, viewer_id, post_hidden)
    # viewer đã thích post_ok → enrich phải trả is_liked=True
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO likes (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (viewer_id, post_ok),
        )

    result = _run_feed(user=viewer)
    assert _post_ids(result) == {post_ok, post_boosted, post_review}
    assert result["total"] == 3
    assert result["has_more"] is False
    # boost mùa vụ: bài gắn entity đúng tháng cao điểm đứng đầu dù cũ hơn
    assert result["posts"][0]["id"] == post_boosted
    by_id = {p["id"]: p for p in result["posts"]}
    assert by_id[post_ok]["is_liked"] is True
    assert by_id[post_review]["is_liked"] is False
    assert by_id[post_boosted]["entity_name"] == "Chợ nổi thử"

    # khách vãng lai: không lọc block/mute/hidden
    anon = _run_feed(user=None)
    assert _post_ids(anon) == {
        post_ok, post_boosted, post_review, post_blocked, post_muted, post_hidden
    }
    assert anon["total"] == 6

    # lọc theo loại bài + hashtag
    only_review = _run_feed(user=viewer, post_type="review")
    assert _post_ids(only_review) == {post_review}
    only_tag = _run_feed(user=viewer, tag="#Xoai")
    assert _post_ids(only_tag) == {post_review}


def test_get_feed_area_filter_matches_place_and_children(pg_db):
    author = _seed_user(pg_db)
    ent_place = _seed_entity(pg_db, entity_type="place", area="khu-tay")
    ent_prod = _seed_entity(pg_db, entity_type="product", place_id=ent_place)
    p_place = _seed_post(pg_db, author, entity_id=ent_place)
    p_prod = _seed_post(pg_db, author, entity_id=ent_prod)
    _seed_post(pg_db, author)  # không gắn entity → ngoài vùng

    result = _run_feed(user=None, area="khu-tay")
    assert _post_ids(result) == {p_place, p_prod}
    assert result["total"] == 2


# ── get_following_feed ──


def test_get_following_feed_includes_followed_users_and_entities(pg_db):
    viewer_id = _seed_user(pg_db, "Người theo dõi")
    viewer = _viewer(viewer_id)
    followed = _seed_user(pg_db, "Được theo dõi")
    stranger = _seed_user(pg_db, "Người lạ")
    blocked = _seed_user(pg_db, "Theo dõi nhưng chặn")
    ent = _seed_entity(pg_db)
    _seed_follow(pg_db, viewer_id, followed, "user")
    _seed_follow(pg_db, viewer_id, ent, "entity")
    _seed_follow(pg_db, viewer_id, blocked, "user")
    _seed_block(pg_db, viewer_id, blocked)

    p_user = _seed_post(pg_db, followed)
    p_entity = _seed_post(pg_db, stranger, entity_id=ent)
    _seed_post(pg_db, stranger)          # không follow → ngoài feed
    _seed_post(pg_db, viewer_id)         # bài của chính mình, không tự follow
    _seed_post(pg_db, blocked)           # follow nhưng đã chặn → loại

    result = asyncio.run(
        community_api.get_following_feed(page=1, limit=20, user=viewer)
    )
    assert _post_ids(result) == {p_user, p_entity}
    assert result["total"] == 2
    assert result["has_more"] is False


# ── get_friend_reviews ──


def test_get_friend_reviews_only_reviews_from_followed_users(pg_db):
    viewer_id = _seed_user(pg_db)
    viewer = _viewer(viewer_id)
    friend = _seed_user(pg_db, "Bạn đánh giá")
    stranger = _seed_user(pg_db)
    _seed_follow(pg_db, viewer_id, friend, "user")

    long_content = "a" * 200
    r_ok = _seed_post(pg_db, friend, post_type="review", rating=4,
                      content=long_content)
    _seed_post(pg_db, friend, post_type="share")                      # không phải review
    _seed_post(pg_db, stranger, post_type="review", rating=5)         # không follow
    r_hidden = _seed_post(pg_db, friend, post_type="review", rating=3)
    _hide_post(pg_db, viewer_id, r_hidden)

    result = asyncio.run(community_api.get_friend_reviews(limit=5, user=viewer))
    assert [r["id"] for r in result["reviews"]] == [r_ok]
    review = result["reviews"][0]
    assert review["rating"] == 4
    assert review["user"]["display_name"] == "Bạn đánh giá"
    # LEFT(content, 150) cắt tại 150 ký tự
    assert len(review["content"]) == 150


# ── trending_posts ──


def test_trending_posts_ranks_by_engagement_within_window(pg_db):
    author = _seed_user(pg_db)
    now = datetime.now(timezone.utc)
    t_likes = _seed_post(pg_db, author, like_count=10,
                         created_at=now - timedelta(days=1))
    t_comments = _seed_post(pg_db, author, comment_count=10,
                            created_at=now - timedelta(days=2))
    _seed_post(pg_db, author, like_count=100,
               created_at=now - timedelta(days=10))  # ngoài cửa sổ 7d

    result = asyncio.run(
        community_api.trending_posts(window="7d", limit=20, user=None)
    )
    # điểm = like*2 + comment*3 → bài 10 comment (30) đứng trên bài 10 like (20)
    assert [p["id"] for p in result["posts"]] == [t_comments, t_likes]
    assert result["total"] == 2
    assert result["window"] == "7d"
    assert result["days"] == 7
    assert result["has_more"] is False

    # window lạ rơi về mặc định 7 ngày
    fallback = asyncio.run(
        community_api.trending_posts(window="1y", limit=20, user=None)
    )
    assert fallback["days"] == 7


# ── explore_feed ──


def test_explore_feed_excludes_self_and_followed_authors(pg_db):
    viewer_id = _seed_user(pg_db)
    viewer = _viewer(viewer_id)
    followed = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    _seed_follow(pg_db, viewer_id, followed, "user")

    p_followed = _seed_post(pg_db, followed)
    p_self = _seed_post(pg_db, viewer_id)
    p_stranger = _seed_post(pg_db, stranger)

    result = asyncio.run(
        community_api.explore_feed(page=1, limit=20, user=viewer)
    )
    assert _post_ids(result) == {p_stranger}
    assert result["total"] == 1

    anon = asyncio.run(community_api.explore_feed(page=1, limit=20, user=None))
    assert _post_ids(anon) == {p_followed, p_self, p_stranger}
    assert anon["total"] == 3


# ── search_posts / search_users ──


def test_search_posts_accent_insensitive_match(pg_db, monkeypatch):
    calls = []
    monkeypatch.setattr(
        community_api, "check_rate",
        lambda key, limit, window, msg=None: calls.append(key),
    )
    author = _seed_user(pg_db)
    viewer_id = _seed_user(pg_db)
    blocked = _seed_user(pg_db)
    _seed_block(pg_db, viewer_id, blocked)
    match = _seed_post(pg_db, author, content="Chợ nổi Cái Bè sáng sớm rất đông vui")
    _seed_post(pg_db, author, content="Bánh xèo miền quê giòn rụm thơm lừng")
    _seed_post(pg_db, blocked, content="Chợ nổi của người bị chặn nói về")

    result = asyncio.run(
        community_api.search_posts(q="cho noi", page=1, user=_viewer(viewer_id))
    )
    assert _post_ids(result) == {match}
    assert result["total"] == 1
    assert result["q"] == "cho noi"
    assert calls and calls[0].startswith("search:")

    # q sau strip ngắn hơn 2 ký tự → trả rỗng, không chạy SQL
    empty = asyncio.run(
        community_api.search_posts(q=" a ", page=1, user=None)
    )
    assert empty == {"posts": [], "total": 0, "page": 1, "has_more": False}


def test_search_posts_propagates_rate_limit(pg_db, monkeypatch):
    def _deny(key, limit, window, msg=None):
        raise HTTPException(429, "Tìm kiếm quá nhanh")

    monkeypatch.setattr(community_api, "check_rate", _deny)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.search_posts(q="cho noi", page=1, user=None))
    assert exc.value.status_code == 429


def test_search_users_matches_display_name_and_counts_posts(pg_db, monkeypatch):
    monkeypatch.setattr(
        community_api, "check_rate", lambda *a, **k: None
    )
    top = _seed_user(pg_db, "Trần Xoài Vàng")
    other = _seed_user(pg_db, "Người Xoài Khác")
    _seed_user(pg_db, "Xoài Ẩn", active=False)
    _seed_user(pg_db, "Xoài Xoá", deleted=True)
    _seed_post(pg_db, top)
    _seed_post(pg_db, top)
    _seed_post(pg_db, top, status="pending")  # không tính vào post_count

    result = asyncio.run(community_api.search_users(q="xoai", page=1, user=None))
    assert [(u["id"], u["post_count"]) for u in result["users"]] == [
        (top, 2), (other, 0)
    ]
    assert result["total"] == 2

    # viewer chặn `other` thì kết quả bỏ người đó
    viewer_id = _seed_user(pg_db, "Người tìm")
    _seed_block(pg_db, viewer_id, other)
    filtered = asyncio.run(
        community_api.search_users(q="xoai", page=1, user=_viewer(viewer_id))
    )
    assert [u["id"] for u in filtered["users"]] == [top]

    empty = asyncio.run(community_api.search_users(q=" b ", page=1, user=None))
    assert empty == {"users": [], "total": 0, "page": 1, "has_more": False}


# ── community_stats / user_counts / user_stats / user_activity ──


def test_community_stats_counts_real_rows(pg_db):
    active = _seed_user(pg_db)
    _seed_user(pg_db, active=False)
    _seed_post(pg_db, active)
    _seed_post(pg_db, active, post_type="review", rating=5)
    _seed_post(pg_db, active, status="pending")
    _seed_post(pg_db, active, deleted=True)

    response = Response()
    result = asyncio.run(community_api.community_stats(response))
    assert result == {"posts": 2, "reviews": 1, "members": 1}
    assert "max-age=60" in response.headers["Cache-Control"]


def test_user_counts_reads_each_bucket(pg_db):
    uid = _seed_user(pg_db)
    other = _seed_user(pg_db)
    _seed_post(pg_db, uid)
    _seed_post(pg_db, uid, status="pending")     # != rejected → vẫn tính
    _seed_post(pg_db, uid, status="rejected")    # loại
    _seed_post(pg_db, uid, is_draft=True)        # sang ô drafts
    _seed_post(pg_db, uid, deleted=True)         # loại
    _seed_post(pg_db, other)
    ent = _seed_entity(pg_db)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO notifications (user_id, type, title, is_read) VALUES "
            "(%s::uuid, 'like', 'Chưa đọc 1', FALSE), "
            "(%s::uuid, 'like', 'Chưa đọc 2', FALSE), "
            "(%s::uuid, 'like', 'Đã đọc', TRUE)",
            (uid, uid, uid),
        )
        pg_db._execute(
            conn,
            "INSERT INTO saved_entities (user_id, entity_id) VALUES (%s::uuid, %s)",
            (uid, ent),
        )
        pg_db._execute(
            conn,
            "INSERT INTO user_visits (user_id, entity_id, status) VALUES "
            "(%s::uuid, %s, 'visited'), (%s::uuid, %s, 'want')",
            (uid, ent, uid, f"{ent}-2"),
        )

    result = asyncio.run(community_api.user_counts(Response(), user=_viewer(uid)))
    assert result == {
        "unread_notifications": 2,
        "posts": 2,
        "drafts": 1,
        "bookmarks": 1,
        "visits": 2,
    }


def test_user_stats_aggregates_profile_numbers(pg_db):
    uid = _seed_user(pg_db)
    fan1 = _seed_user(pg_db)
    fan2 = _seed_user(pg_db)
    idol = _seed_user(pg_db)
    ent = _seed_entity(pg_db)
    r1 = _seed_post(pg_db, uid, post_type="review", rating=4, entity_id=ent,
                    like_count=3)
    _seed_post(pg_db, uid, post_type="review", rating=5, entity_id=ent)
    _seed_post(pg_db, uid, post_type="review", rating=1, status="rejected")
    _seed_post(pg_db, uid, post_type="question")
    _seed_follow(pg_db, fan1, uid, "user")
    _seed_follow(pg_db, fan2, uid, "user")
    _seed_follow(pg_db, uid, idol, "user")
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO post_reactions (post_id, user_id, reaction_type) "
            "VALUES (%s::uuid, %s::uuid, 'heart')",
            (r1, fan1),
        )
        pg_db._execute(
            conn,
            "INSERT INTO user_collections (user_id, name) VALUES (%s::uuid, %s)",
            (uid, "Bộ sưu tập"),
        )

    result = asyncio.run(
        community_api.user_stats(user=_viewer(uid, reputation=7))
    )
    assert result == {
        "reviews": 2,
        "avg_rating": 4.5,
        "questions": 1,
        "followers": 2,
        "following": 1,
        "likes_received": 3,
        "reactions_received": 1,
        "entities_reviewed": 1,
        "collections": 1,
        "reputation": 7,
    }


def test_user_activity_merges_streams_and_paginates(pg_db):
    uid = _seed_user(pg_db)
    other = _seed_user(pg_db)
    now = datetime.now(timezone.utc)
    own_post = _seed_post(pg_db, uid, created_at=now - timedelta(hours=3))
    target = _seed_post(pg_db, other, created_at=now - timedelta(hours=6))
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO comments (post_id, user_id, content, created_at) "
            "VALUES (%s::uuid, %s::uuid, %s, %s)",
            (target, uid, "Bình luận thử nghiệm", now - timedelta(hours=2)),
        )
        pg_db._execute(
            conn,
            "INSERT INTO likes (user_id, post_id, created_at) "
            "VALUES (%s::uuid, %s::uuid, %s)",
            (uid, target, now - timedelta(hours=1)),
        )

    result = asyncio.run(
        community_api.user_activity(limit=30, offset=0, user=_viewer(uid))
    )
    assert [it["action"] for it in result["items"]] == ["like", "comment", "post"]
    assert all(it["ref_type"] == "post" for it in result["items"])
    assert result["items"][0]["ref_id"] == target
    assert result["items"][2]["ref_id"] == own_post
    assert result["has_more"] is False

    page1 = asyncio.run(
        community_api.user_activity(limit=2, offset=0, user=_viewer(uid))
    )
    assert [it["action"] for it in page1["items"]] == ["like", "comment"]
    assert page1["has_more"] is True
    page2 = asyncio.run(
        community_api.user_activity(limit=2, offset=2, user=_viewer(uid))
    )
    assert [it["action"] for it in page2["items"]] == ["post"]
    assert page2["has_more"] is False


# ── hashtags ──


def test_trending_tags_counts_and_caches(pg_db):
    author = _seed_user(pg_db)
    _seed_post(pg_db, author, hashtags=("xoai", "cho-noi"))
    _seed_post(pg_db, author, hashtags=("xoai",))
    _seed_post(pg_db, author, hashtags=("xoai",), status="pending")

    async def _scenario():
        first = await community_api.trending_tags(
            Response(), limit=10, period="30d"
        )
        # bài mới sau khi cache còn hạn → kết quả vẫn là bản cache
        _seed_post(pg_db, author, hashtags=("moi-toanh",))
        second = await community_api.trending_tags(
            Response(), limit=10, period="30d"
        )
        return first, second

    first, second = asyncio.run(_scenario())
    assert first["tags"] == [
        {"tag": "xoai", "count": 2},
        {"tag": "cho-noi", "count": 1},
    ]
    assert first["period"] == "30d"
    assert first["days"] == 30
    assert second == first


def test_list_hashtags_counts_and_search_filter(pg_db):
    author = _seed_user(pg_db)
    _seed_post(pg_db, author, hashtags=("xoai", "cho-noi"))
    _seed_post(pg_db, author, hashtags=("xoai",))

    result = asyncio.run(
        community_api.list_hashtags(Response(), limit=50, page=1, search="")
    )
    assert result["hashtags"] == [
        {"tag": "xoai", "post_count": 2},
        {"tag": "cho-noi", "post_count": 1},
    ]
    assert result["total"] == 2
    assert result["has_more"] is False

    narrowed = asyncio.run(
        community_api.list_hashtags(Response(), limit=50, page=1, search="cho")
    )
    assert narrowed["hashtags"] == [{"tag": "cho-noi", "post_count": 1}]
    assert narrowed["total"] == 1


def test_hashtag_posts_sorting_and_validation(pg_db, monkeypatch):
    async def _anon(_request):
        return None

    monkeypatch.setattr(community_api, "get_current_user", _anon)
    author = _seed_user(pg_db)
    now = datetime.now(timezone.utc)
    older_liked = _seed_post(pg_db, author, hashtags=("xoai",), like_count=5,
                             created_at=now - timedelta(hours=4))
    newer = _seed_post(pg_db, author, hashtags=("xoai",), like_count=1,
                       created_at=now - timedelta(hours=1))
    _seed_post(pg_db, author, hashtags=("khac",))

    request = SimpleNamespace()
    newest = asyncio.run(
        community_api.hashtag_posts("#XOAI", request, page=1, limit=20, sort="newest")
    )
    assert newest["tag"] == "xoai"
    assert [p["id"] for p in newest["posts"]] == [newer, older_liked]
    assert newest["total"] == 2

    popular = asyncio.run(
        community_api.hashtag_posts("xoai", request, page=1, limit=20, sort="popular")
    )
    assert [p["id"] for p in popular["posts"]] == [older_liked, newer]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.hashtag_posts("#", request, page=1, limit=20, sort="newest")
        )
    assert exc.value.status_code == 400


# ── leaderboard helpers + handler ──


def test_leaderboard_fresh_respects_ttl(pg_db):
    assert community_api._leaderboard_fresh("all:total") is None
    entry = {"ts": time.time(), "data": [{"id": "x"}]}
    community_api._leaderboard_cache["all:total"] = entry
    assert community_api._leaderboard_fresh("all:total") is entry
    community_api._leaderboard_cache["all:total"] = {
        "ts": time.time() - 999, "data": [],
    }
    assert community_api._leaderboard_fresh("all:total") is None


def test_leaderboard_period_clause():
    clause, params = community_api._leaderboard_period("%s", "7d")
    assert clause == "AND p.created_at > NOW() - CAST(%s AS INTERVAL)"
    assert params == ["7 days"]
    assert community_api._leaderboard_period("%s", "all") == ("", [])


def test_leaderboard_row_and_build():
    base = {"id": str(uuid.uuid4()), "display_name": "A", "avatar_url": None,
            "username": "a", "reviews": 1, "posts": 1, "photos": 0,
            "followers": 0, "places": 1, "likes": 0}
    entry = community_api._leaderboard_row(base)
    # 1 review (5đ) + 1 địa điểm (2đ) = 7đ, cấp 1
    assert entry["points"] == 7
    assert entry["level"] == 1
    assert entry["level_label"] == "Người mới"
    zero = dict(base, reviews=0, posts=0, places=0)
    assert community_api._leaderboard_row(zero) is None

    poster = dict(base, id=str(uuid.uuid4()), display_name="B", username="b",
                  reviews=0, posts=5, places=0)
    rows = [base, poster]
    by_posts = community_api._leaderboard_build(rows, "posts")
    assert [e["display_name"] for e in by_posts] == ["B", "A"]
    by_total = community_api._leaderboard_build(rows, "total")
    # B: 5 bài thường = 10đ > A: 7đ
    assert [e["display_name"] for e in by_total] == ["B", "A"]


def test_self_ranked_result_ranks_and_finds_self():
    leaders = [{"id": "a", "points": 30}, {"id": "b", "points": 20},
               {"id": "c", "points": 10}]
    result = community_api._self_ranked_result(leaders, 2, {"id": "c"})
    assert [ld["id"] for ld in result["leaders"]] == ["a", "b"]
    assert [ld["rank"] for ld in result["leaders"]] == [1, 2]
    assert result["self"]["id"] == "c"
    assert result["self"]["rank"] == 3
    assert community_api._self_ranked_result(leaders, 2, None)["self"] is None


def test_community_leaderboard_on_postgres(pg_db):
    reviewer = _seed_user(pg_db, "Anh Xoài Vàng")
    poster = _seed_user(pg_db, "Bạn Bến Trẻ")
    _seed_user(pg_db, "Không bài viết")
    ent = _seed_entity(pg_db)
    _seed_post(pg_db, reviewer, post_type="review", rating=5, entity_id=ent)
    _seed_post(pg_db, reviewer, post_type="review", rating=4, entity_id=ent)
    _seed_post(pg_db, poster)

    async def _scenario():
        public = await community_api.community_leaderboard(
            limit=10, period="all", category="total", q="", user=None
        )
        with_self = await community_api.community_leaderboard(
            limit=10, period="all", category="total", q="", user=_viewer(poster)
        )
        searched = await community_api.community_leaderboard(
            limit=10, period="all", category="total", q="xoai", user=None
        )
        return public, with_self, searched

    public, with_self, searched = asyncio.run(_scenario())
    # reviewer: 2 review (10đ) + 1 địa điểm (2đ) = 12đ; poster: 1 bài thường = 2đ
    assert [(ld["id"], ld["points"], ld["rank"]) for ld in public["leaders"]] == [
        (reviewer, 12, 1), (poster, 2, 2),
    ]
    assert public["self"] is None
    assert with_self["self"]["id"] == poster
    assert with_self["self"]["rank"] == 2
    assert [ld["id"] for ld in searched["leaders"]] == [reviewer]


# ── follows: following / followers / suggested ──


def test_list_following_users_public_profile(pg_db):
    target = _seed_user(pg_db, "Chủ hồ sơ", username="chuhoso")
    _seed_privacy(pg_db, target, visibility="public")
    friend1 = _seed_user(pg_db, "Bạn Một")
    friend2 = _seed_user(pg_db, "Bạn Hai")
    ghost = _seed_user(pg_db, "Ngưng hoạt động", active=False)
    _seed_follow(pg_db, target, friend1, "user")
    _seed_follow(pg_db, target, friend2, "user")
    _seed_follow(pg_db, target, ghost, "user")

    result = asyncio.run(
        community_api.list_following_users("chuhoso", limit=50, offset=0, user=None)
    )
    assert {u["id"] for u in result["users"]} == {friend1, friend2}
    assert result["total"] == 2
    assert result["has_more"] is False

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.list_following_users(
                str(uuid.uuid4()), limit=50, offset=0, user=None
            )
        )
    assert exc.value.status_code == 404


def test_list_following_users_hidden_without_privacy_row(pg_db):
    # Không có dòng user_privacy → visibility mặc định followers_only →
    # khách vãng lai bị giấu danh sách (hành vi hiện tại).
    target = _seed_user(pg_db)
    friend = _seed_user(pg_db)
    _seed_follow(pg_db, target, friend, "user")
    result = asyncio.run(
        community_api.list_following_users(target, limit=50, offset=0, user=None)
    )
    assert result == {"users": [], "total": 0, "offset": 0, "has_more": False}


def test_list_followers_public_profile(pg_db):
    target = _seed_user(pg_db, "Được theo dõi")
    _seed_privacy(pg_db, target, visibility="public")
    fan1 = _seed_user(pg_db, "Fan Một")
    fan2 = _seed_user(pg_db, "Fan Hai")
    _seed_follow(pg_db, fan1, target, "user")
    _seed_follow(pg_db, fan2, target, "user")

    result = asyncio.run(
        community_api.list_followers(target, limit=50, offset=0, user=None)
    )
    assert {u["id"] for u in result["users"]} == {fan1, fan2}
    assert result["total"] == 2

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.list_followers(
                str(uuid.uuid4()), limit=50, offset=0, user=None
            )
        )
    assert exc.value.status_code == 404


def test_suggested_follows_excludes_followed_self_and_blocked(pg_db):
    viewer_id = _seed_user(pg_db, "Người xem")
    followed = _seed_user(pg_db, "Đã theo dõi")
    fresh = _seed_user(pg_db, "Chưa theo dõi")
    silent = _seed_user(pg_db, "Chưa có bài")
    blocked = _seed_user(pg_db, "Đã chặn")
    _seed_follow(pg_db, viewer_id, followed, "user")
    _seed_block(pg_db, viewer_id, blocked)
    _seed_post(pg_db, followed)
    _seed_post(pg_db, fresh)
    _seed_post(pg_db, blocked)
    _seed_post(pg_db, viewer_id)
    assert silent  # không có bài → HAVING COUNT>0 loại

    result = asyncio.run(
        community_api.suggested_follows(user=_viewer(viewer_id), limit=5)
    )
    assert [u["id"] for u in result["users"]] == [fresh]
    assert result["users"][0]["points"] > 0


# ── entity feed ──


def test_entity_feed_filters_builder(pg_db):
    params = []
    extra = community_api._entity_feed_filters("%s", 4, True, "review", "default", params)
    assert " AND p.rating >= %s" in extra
    assert "jsonb_array_length(p.images) > 0" in extra
    assert " AND p.post_type = %s" in extra
    assert params == [4, "review"]

    params2 = []
    extra2 = community_api._entity_feed_filters("%s", None, None, "bogus", "unanswered", params2)
    assert extra2 == " AND p.post_type = 'question' AND p.best_answer_id IS NULL"
    assert params2 == []


def test_entity_feed_response_defaults_without_rating_row(pg_db):
    entity = {"id": "ent-x", "name": "Tên", "type": "place", "summary": "Tóm tắt"}
    result = community_api._entity_feed_response(entity, [], None, None)
    assert result["entity"] == {"id": "ent-x", "name": "Tên", "type": "place",
                                "summary": "Tóm tắt"}
    assert result["rating"] == {"avg": 0, "count": 0}
    assert result["posts"] == []
    assert result["total"] == 0


def test_get_entity_feed_star_sort_and_min_rating(pg_db):
    author = _seed_user(pg_db)
    ent = _seed_entity(pg_db, name="Cù lao thử", summary="Tóm tắt ngắn")
    other_ent = _seed_entity(pg_db)
    r_top = _seed_post(pg_db, author, post_type="review", rating=5, entity_id=ent)
    r_low = _seed_post(pg_db, author, post_type="review", rating=3, entity_id=ent)
    _seed_post(pg_db, author, post_type="review", rating=5, entity_id=other_ent)
    _seed_post(pg_db, author, entity_id=ent, status="pending")
    # entity_ratings do trigger trg_entity_ratings tự đắp khi INSERT review:
    # (5 + 3) / 2 = 4.0 trên 2 review đã duyệt của ent.

    result = asyncio.run(
        community_api.get_entity_feed(
            ent, page=1, limit=20, sort="star", min_rating=None,
            has_photo=None, post_type=None, user=None,
        )
    )
    assert result["entity"]["id"] == ent
    assert result["entity"]["name"] == "Cù lao thử"
    assert [p["id"] for p in result["posts"]] == [r_top, r_low]
    assert result["total"] == 2
    assert result["rating"] == {"avg": 4.0, "count": 2}

    strict = asyncio.run(
        community_api.get_entity_feed(
            ent, page=1, limit=20, sort="star", min_rating=4,
            has_photo=None, post_type=None, user=None,
        )
    )
    assert [p["id"] for p in strict["posts"]] == [r_top]
    assert strict["total"] == 1

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.get_entity_feed(
                "ent-khong-ton-tai", page=1, limit=20, sort="default",
                min_rating=None, has_photo=None, post_type=None, user=None,
            )
        )
    assert exc.value.status_code == 404


# ── related posts ──


def test_related_posts_same_entity_branch(pg_db):
    author = _seed_user(pg_db)
    ent = _seed_entity(pg_db)
    other_ent = _seed_entity(pg_db)
    # nguồn KHÔNG có hashtag để đi trọn nhánh cùng-entity (nhánh hashtag
    # hiện đổ vỡ trên PG — xem suspected_bugs của phiên đo này)
    source = _seed_post(pg_db, author, entity_id=ent)
    rel_hot = _seed_post(pg_db, author, entity_id=ent, like_count=9)
    rel_cold = _seed_post(pg_db, author, entity_id=ent, like_count=1)
    _seed_post(pg_db, author, entity_id=other_ent)
    _seed_post(pg_db, author, entity_id=ent, status="pending")

    result = asyncio.run(
        community_api.related_posts(source, limit=4, user=None)
    )
    assert [p["id"] for p in result["posts"]] == [rel_hot, rel_cold]

    missing = asyncio.run(
        community_api.related_posts(str(uuid.uuid4()), limit=4, user=None)
    )
    assert missing == {"posts": []}
