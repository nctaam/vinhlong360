# -*- coding: utf-8 -*-
"""Đặc tả hành vi hiện tại — miền HỒ SƠ CÔNG KHAI của community.api trên PostgreSQL thật.

Chạy xuyên các closure `_query` chưa từng chạy trên DB thật: upload_image,
danh tiếng/badge (_reputation, _badge_progress_stats, get_badge_progress),
log lượt xem hồ sơ, resolve hồ sơ + quan hệ viewer, timeline, wrapper cho AI
(get_community_reviews / get_trending_posts) và các helper thuần đi kèm.

Cổng env: UGC_SURFACE_TEST_DATABASE_URL (DB PG dùng-một-lần đã đủ 81 migration).
Mọi query đi qua adapter PG được patch THẲNG vào community.api + profile_access;
side-effect ngoài miền (achievements, storage đích, rate-limit) được stub.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import io
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException

import achievements as achievements_module
import database as database_module
import profile_access as profile_access_module
import storage as storage_module
from community import api as community_api
from media_policy import AI_ONLY_MEDIA_DETAIL


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
            "PostgreSQL community-profile tests require a database name containing "
            "'test' or UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL community-profile tests require "
            "UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set UGC_SURFACE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)

# Các bảng miền hồ sơ mà file này ghi vào — TRUNCATE quanh mỗi test.
_TABLES = (
    "profile_views, post_reactions, likes, bookmarks, user_visits, "
    "user_mutes, blocks, follows, user_privacy, posts, users, entities"
)


def _truncate() -> None:
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE {_TABLES} CASCADE")


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    # Patch db vào ĐÚNG module thực thi query: community.api và profile_access
    # (resolve_profile_access đọc db riêng của nó — bẫy trục-4).
    monkeypatch.setattr(community_api, "db", adapter)
    monkeypatch.setattr(profile_access_module, "db", adapter)

    _truncate()
    try:
        yield adapter
    finally:
        _truncate()


# ── Seed helpers (SQL INSERT qua adapter PG) ──


def _seed_user(pg_db, *, username=None, display_name="Người dùng Test",
               is_active=True, deleted=False, created_days_ago=0) -> str:
    user_id = str(uuid.uuid4())
    phone = f"test-{uuid.uuid4().hex}"
    created = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
    deleted_at = datetime.now(timezone.utc) if deleted else None
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (id, phone, display_name, username, role,
                               is_active, deleted_at, created_at, updated_at)
            VALUES (%s::uuid, %s, %s, %s, 'user', %s, %s, %s, %s)
            """,
            (user_id, phone, display_name, username, is_active,
             deleted_at, created, created),
        )
    return user_id


def _seed_entity(pg_db, *, etype="destination", name="Điểm đến Vĩnh Long",
                 area=None) -> str:
    entity_id = f"ent-{uuid.uuid4().hex[:10]}"
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO entities (id, type, name, area) VALUES (%s, %s, %s, %s)",
            (entity_id, etype, name, area),
        )
    return entity_id


def _seed_post(pg_db, user_id, content="Bài viết", *, post_type="share",
               entity_id=None, rating=None, images=None, like_count=0,
               comment_count=0, moderation_status="approved", is_pinned=False,
               deleted=False, minutes_ago=0) -> str:
    post_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    deleted_at = datetime.now(timezone.utc) if deleted else None
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO posts (id, user_id, entity_id, content, images, post_type,
                               rating, moderation_status, like_count, comment_count,
                               is_pinned, deleted_at, created_at, updated_at)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s::jsonb, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s)
            """,
            (post_id, user_id, entity_id, content, json.dumps(images or []),
             post_type, rating, moderation_status, like_count, comment_count,
             is_pinned, deleted_at, ts, ts),
        )
    return post_id


def _seed_follow(pg_db, follower_id, target_id, *, minutes_ago=0) -> None:
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO follows (follower_id, target_type, target_id, created_at)
            VALUES (%s::uuid, 'user', %s, %s)
            """,
            (follower_id, str(target_id), ts),
        )


def _seed_privacy(pg_db, user_id, *, visibility="public", show_activity=True,
                  show_saved=True) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_privacy (user_id, profile_visibility, show_activity, show_saved)
            VALUES (%s::uuid, %s, %s, %s)
            """,
            (user_id, visibility, show_activity, show_saved),
        )


def _seed_reaction(pg_db, post_id, user_id, reaction_type="heart") -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO post_reactions (post_id, user_id, reaction_type)
            VALUES (%s::uuid, %s::uuid, %s)
            """,
            (post_id, user_id, reaction_type),
        )


def _seed_visit(pg_db, user_id, entity_id, status="visited") -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_visits (user_id, entity_id, status)
            VALUES (%s::uuid, %s, %s)
            """,
            (user_id, entity_id, status),
        )


def _seed_block(pg_db, blocker_id, blocked_id) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s::uuid, %s::uuid)",
            (blocker_id, blocked_id),
        )


def _seed_mute(pg_db, user_id, muted_id) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO user_mutes (user_id, muted_id) VALUES (%s::uuid, %s::uuid)",
            (user_id, muted_id),
        )


def _seed_profile_view(pg_db, viewer_id, viewed_id, *, days_ago=0) -> None:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO profile_views (viewer_id, viewed_id, viewed_date)
            VALUES (%s::uuid, %s::uuid, CURRENT_DATE - %s::int)
            """,
            (viewer_id, viewed_id, days_ago),
        )


def _count_profile_views(pg_db, viewed_id) -> int:
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS c FROM profile_views WHERE viewed_id = %s::uuid",
            (viewed_id,),
        )
    return pg_db._row_to_dict(row)["c"]


def _seed_reputation_world(pg_db) -> dict:
    """Thế giới dữ liệu chung cho các test danh tiếng/badge.

    Chủ hồ sơ tạo 200 ngày trước; 1 follower cũ (10 ngày, được _reputation tính)
    + 1 follower mới (bị lọc 7-ngày của _reputation nhưng _badge_progress_stats
    vẫn đếm); 1 review có ảnh + entity, 1 share; bài pending/deleted không tính;
    2 lượt ghé 'visited' ở 2 khu vực + 1 lượt 'want' không tính.
    """
    owner = _seed_user(pg_db, display_name="Chủ Hồ Sơ", created_days_ago=200)
    follower_old = _seed_user(pg_db, created_days_ago=10)
    follower_new = _seed_user(pg_db, created_days_ago=0)
    _seed_follow(pg_db, follower_old, owner)
    _seed_follow(pg_db, follower_new, owner)

    ent_a = _seed_entity(pg_db, name="Làng gốm Mang Thít", area="khu-vuc-a")
    ent_b = _seed_entity(pg_db, name="Cù lao An Bình", area="khu-vuc-b")

    _seed_post(pg_db, owner, "Đánh giá làng gốm", post_type="review",
               entity_id=ent_a, rating=5, images=["/media/posts/a.webp"],
               like_count=3, minutes_ago=60)
    _seed_post(pg_db, owner, "Chia sẻ chuyến đi", like_count=2, minutes_ago=30)
    _seed_post(pg_db, owner, "Bài chờ duyệt", like_count=100,
               moderation_status="pending", minutes_ago=20)
    _seed_post(pg_db, owner, "Bài đã xoá", like_count=50, deleted=True,
               minutes_ago=10)

    _seed_visit(pg_db, owner, ent_a, "visited")
    _seed_visit(pg_db, owner, ent_b, "visited")
    _seed_visit(pg_db, owner, "ent-chua-ghe", "want")
    return {"owner": owner, "ent_a": ent_a, "ent_b": ent_b}


class _FakeUpload:
    """UploadFile giả — chỉ cần .read(n) async như handler dùng."""

    def __init__(self, data: bytes):
        self._data = data
        self.read_calls = []

    async def read(self, size=-1):
        self.read_calls.append(size)
        if size is None or size < 0:
            return self._data
        return self._data[:size]


def _png_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 120, 40)).save(buf, format="PNG")
    return buf.getvalue()


# ── upload_image ──


def test_upload_image_chan_moi_media_theo_chinh_sach_ai_only(monkeypatch):
    """Hành vi hiện tại: cổng AI-only chặn NGAY dòng đầu — trước cả rate-limit và đọc file."""
    rate_calls = []
    monkeypatch.setattr(community_api, "check_rate",
                        lambda *a, **k: rate_calls.append(a))
    fake = _FakeUpload(_png_bytes())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.upload_image(
            file=fake, user={"id": str(uuid.uuid4())}, _csrf=None, _idem=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == AI_ONLY_MEDIA_DETAIL
    assert fake.read_calls == []
    assert rate_calls == []


def test_upload_image_openapi_mo_ta_dung_chinh_sach_ai_only():
    """Bug 13 đã sửa: summary/description của route /upload/image phải nói đúng
    hành vi thật (từ chối 400 ai_only_media), không hứa 'returns the URL'."""
    route = next(
        r for r in community_api.router.routes
        if getattr(r, "path", "") == "/api/upload/image"
    )
    assert "AI-only" in route.summary
    assert "ai_only_media" in route.description
    assert "rejected" in route.description
    assert "Returns the uploaded image URL" not in route.description


def test_upload_image_sau_cong_luu_webp_vao_thu_muc_duoc_tro(monkeypatch, tmp_path):
    """Khi cổng AI-only được nới (stub), ảnh PNG hợp lệ được convert WebP và lưu local."""
    monkeypatch.setattr(community_api, "_reject_non_ai_media", lambda: None)
    rate_calls = []
    monkeypatch.setattr(community_api, "check_rate",
                        lambda key, *a, **k: rate_calls.append(key))
    monkeypatch.setattr(storage_module, "LOCAL_MEDIA_DIR", tmp_path)
    monkeypatch.setattr(storage_module.storage, "use_s3", False)
    monkeypatch.setattr(storage_module.storage, "backend", "local")
    uid = str(uuid.uuid4())
    fake = _FakeUpload(_png_bytes())

    result = asyncio.run(community_api.upload_image(
        file=fake, user={"id": uid}, _csrf=None, _idem=None))

    assert re.fullmatch(r"/media/posts/[0-9a-f]{12}\.webp", result["url"])
    saved = list((tmp_path / "posts").glob("*.webp"))
    assert len(saved) == 1 and saved[0].stat().st_size > 0
    assert rate_calls == [f"upload:{uid}"]


def test_upload_image_sau_cong_tu_choi_byte_khong_phai_anh(monkeypatch, tmp_path):
    monkeypatch.setattr(community_api, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(community_api, "check_rate", lambda *a, **k: None)
    monkeypatch.setattr(storage_module, "LOCAL_MEDIA_DIR", tmp_path)
    fake = _FakeUpload(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.upload_image(
            file=fake, user={"id": str(uuid.uuid4())}, _csrf=None, _idem=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)"


def test_upload_image_sau_cong_tu_choi_qua_5mb(monkeypatch, tmp_path):
    monkeypatch.setattr(community_api, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(community_api, "check_rate", lambda *a, **k: None)
    monkeypatch.setattr(storage_module, "LOCAL_MEDIA_DIR", tmp_path)
    fake = _FakeUpload(b"\xff\xd8\xff" + b"\x00" * (5 * 1024 * 1024))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.upload_image(
            file=fake, user={"id": str(uuid.uuid4())}, _csrf=None, _idem=None))
    assert exc.value.status_code == 400
    assert exc.value.detail == "Ảnh tối đa 5MB"


# ── badge helpers thuần ──


def test_reputation_badges_contrib_nguong_va_rong():
    assert community_api._reputation_badges_contrib(0, 0, 0, 0, 0) == []
    ids = [b["id"] for b in
           community_api._reputation_badges_contrib(25, 10, 10, 20, 50)]
    assert ids == ["first_review", "review_master", "photographer",
                   "explorer", "popular", "quality"]


def test_reputation_badges_activity_nguong_va_rong():
    assert community_api._reputation_badges_activity(0, 0, 0, 0, 0, 0) == []
    ids = [b["id"] for b in
           community_api._reputation_badges_activity(5, 3, 3, 10, 3, 180)]
    assert ids == ["allrounder", "traveler", "local", "veteran"]


# ── _reputation / _badge_progress_stats / get_badge_progress trên PG ──


def test_reputation_tinh_diem_tren_pg_that(pg_db):
    world = _seed_reputation_world(pg_db)
    with pg_db._conn(commit_on_success=False) as conn:
        rep = community_api._reputation(conn, world["owner"], 2, 1)

    # reviews=1→5đ, posts-ngoài-review=1→2đ, photos=1→3đ, follower-cũ=1→1đ,
    # places=1→2đ, likes=3+2=5→5đ ⇒ 18 điểm, cấp 1.
    assert rep["points"] == 18
    assert rep["level"] == 1
    assert rep["level_label"] == "Người mới"
    assert rep["photos"] == 1
    assert rep["followers"] == 1  # follower mới (<7 ngày tuổi) bị lọc
    assert rep["places"] == 1
    assert rep["likes"] == 5
    assert [b["id"] for b in rep["badges"]] == ["first_review", "veteran"]


def test_badge_progress_stats_gom_du_8_chi_so_tren_pg(pg_db):
    world = _seed_reputation_world(pg_db)
    stats = community_api._badge_progress_stats(pg_db._ph, world["owner"])
    reviews, photos, places, likes, followers, visits, areas, age_days = stats
    assert (reviews, photos, places, likes) == (1, 1, 1, 5)
    assert followers == 2  # KHÔNG lọc tuổi follower như _reputation
    assert (visits, areas) == (2, 2)
    assert age_days == 200


def test_get_badge_progress_handler_tren_pg(pg_db):
    world = _seed_reputation_world(pg_db)
    resp = asyncio.run(community_api.get_badge_progress(user={"id": world["owner"]}))
    badges = resp["badges"]
    assert len(badges) == 10
    earned = {b["id"]: b["earned"] for b in badges}
    assert earned == {
        "first_review": True, "review_master": False, "photographer": False,
        "explorer": False, "popular": False, "quality": False,
        "allrounder": False, "traveler": False, "local": False,
        "veteran": True,
    }
    by_id = {b["id"]: b for b in badges}
    assert by_id["review_master"]["current"] == 1
    assert by_id["review_master"]["target"] == 25
    assert by_id["veteran"]["current"] == 200
    assert by_id["allrounder"]["hint"] == "Cần: 2 nơi, 4 đánh giá, 2 ảnh"


# ── profile view logs ──


def test_log_profile_view_dedup_theo_ngay(pg_db):
    viewer = _seed_user(pg_db)
    viewed = _seed_user(pg_db)
    with pg_db._conn() as conn:
        community_api._log_profile_view(conn, viewer, viewed)
        community_api._log_profile_view(conn, viewer, viewed)
    assert _count_profile_views(pg_db, viewed) == 1


def test_log_profile_view_bo_qua_tu_xem(pg_db):
    user_id = _seed_user(pg_db)
    with pg_db._conn() as conn:
        community_api._log_profile_view(conn, user_id, user_id)
    assert _count_profile_views(pg_db, user_id) == 0


def test_log_profile_view_threaded_ghi_hang_that(pg_db):
    viewer = _seed_user(pg_db)
    viewed = _seed_user(pg_db)
    community_api._log_profile_view_threaded(viewer, viewed)
    assert _count_profile_views(pg_db, viewed) == 1


def test_log_profile_view_threaded_nuot_loi_khong_lan(pg_db, monkeypatch):
    class _BrokenDB:
        def _conn(self, **_kw):
            raise RuntimeError("db down")

    monkeypatch.setattr(community_api, "db", _BrokenDB())
    # Không được raise — số liệu phụ không được phá response chính.
    assert community_api._log_profile_view_threaded(
        str(uuid.uuid4()), str(uuid.uuid4())) is None


# ── _check_achievements_bg (side-effect ngoài miền → stub) ──


def test_check_achievements_bg_goi_stub_voi_notify_true(pg_db, monkeypatch):
    calls = []

    def _fake_check(conn, user_id, notify=True):
        assert conn is not None
        calls.append((user_id, notify))
        return []

    monkeypatch.setattr(achievements_module, "check_achievements", _fake_check)
    uid = str(uuid.uuid4())
    community_api._check_achievements_bg(uid)
    assert calls == [(uid, True)]


def test_check_achievements_bg_nuot_loi_khong_lan(pg_db, monkeypatch):
    def _boom(conn, user_id, notify=True):
        raise RuntimeError("hỏng bên trong")

    monkeypatch.setattr(achievements_module, "check_achievements", _boom)
    assert community_api._check_achievements_bg(str(uuid.uuid4())) is None


# ── _profile_resolve / _profile_is_follower / _profile_viewer_rel / _profile_view_count_7d ──


def test_profile_resolve_theo_uuid_va_username(pg_db):
    owner = _seed_user(pg_db, username="traveler-vl-01",
                       display_name="Chủ Hồ Sơ")
    viewer = _seed_user(pg_db)
    ph = pg_db._ph
    with pg_db._conn(commit_on_success=False) as conn:
        profile, rid, is_self, is_blocked = community_api._profile_resolve(
            conn, ph, owner, True, owner)
        assert rid == owner
        assert is_self is True
        assert is_blocked is False
        assert profile["display_name"] == "Chủ Hồ Sơ"

        # Username không phân biệt hoa thường.
        _p2, rid2, is_self2, blocked2 = community_api._profile_resolve(
            conn, ph, "Traveler-VL-01", False, viewer)
        assert rid2 == owner
        assert is_self2 is False
        assert blocked2 is False


def test_profile_resolve_khong_thay_tra_404(pg_db):
    with pg_db._conn(commit_on_success=False) as conn:
        with pytest.raises(HTTPException) as exc:
            community_api._profile_resolve(
                conn, pg_db._ph, str(uuid.uuid4()), True, None)
    assert exc.value.status_code == 404


def test_profile_resolve_phat_hien_block_hai_chieu(pg_db):
    owner = _seed_user(pg_db)
    viewer_a = _seed_user(pg_db)
    viewer_b = _seed_user(pg_db)
    _seed_block(pg_db, viewer_a, owner)  # viewer chặn chủ hồ sơ
    _seed_block(pg_db, owner, viewer_b)  # chủ hồ sơ chặn viewer
    ph = pg_db._ph
    with pg_db._conn(commit_on_success=False) as conn:
        assert community_api._profile_resolve(conn, ph, owner, True, viewer_a)[3] is True
        assert community_api._profile_resolve(conn, ph, owner, True, viewer_b)[3] is True


def test_profile_is_follower_cac_nhanh(pg_db):
    owner = _seed_user(pg_db)
    viewer = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    _seed_follow(pg_db, viewer, owner)
    ph = pg_db._ph
    with pg_db._conn(commit_on_success=False) as conn:
        assert community_api._profile_is_follower(
            conn, ph, False, "followers_only", viewer, owner) is True
        assert community_api._profile_is_follower(
            conn, ph, False, "followers_only", stranger, owner) is False
        # vis public / is_self: đoản mạch, không query.
        assert community_api._profile_is_follower(
            conn, ph, False, "public", viewer, owner) is False
        assert community_api._profile_is_follower(
            conn, ph, True, "followers_only", viewer, owner) is False


def test_profile_viewer_rel_du_ba_quan_he(pg_db):
    owner = _seed_user(pg_db)
    viewer = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    _seed_follow(pg_db, viewer, owner)
    _seed_block(pg_db, viewer, owner)
    _seed_mute(pg_db, viewer, owner)
    ph = pg_db._ph
    with pg_db._conn(commit_on_success=False) as conn:
        assert community_api._profile_viewer_rel(conn, ph, viewer, owner) == (
            True, True, True)
        assert community_api._profile_viewer_rel(conn, ph, stranger, owner) == (
            False, False, False)


def test_profile_view_count_7d_dem_distinct_trong_7_ngay(pg_db):
    owner = _seed_user(pg_db)
    v1 = _seed_user(pg_db)
    v2 = _seed_user(pg_db)
    v3 = _seed_user(pg_db)
    _seed_profile_view(pg_db, v1, owner, days_ago=0)
    _seed_profile_view(pg_db, v1, owner, days_ago=1)   # cùng viewer → distinct
    _seed_profile_view(pg_db, v2, owner, days_ago=3)
    _seed_profile_view(pg_db, v3, owner, days_ago=10)  # ngoài cửa sổ 7 ngày
    assert community_api._profile_view_count_7d(pg_db._ph, owner) == 2


# ── get_user_posts._query / get_user_reviews._query ──


def test_get_user_posts_query_pinned_truoc_va_enrich_reactions(pg_db, monkeypatch):
    owner = _seed_user(pg_db, display_name="Chủ Bài")
    reactor = _seed_user(pg_db)
    _seed_privacy(pg_db, owner, visibility="public", show_activity=True)
    ent = _seed_entity(pg_db, name="Cù lao An Bình")
    p_pinned = _seed_post(pg_db, owner, "Bài ghim", entity_id=ent,
                          is_pinned=True, minutes_ago=60)
    p_new = _seed_post(pg_db, owner, "Bài mới", minutes_ago=5)
    _seed_post(pg_db, owner, "Chờ duyệt", moderation_status="pending")
    _seed_reaction(pg_db, p_new, reactor, "heart")

    async def _anon(_request):
        return None

    monkeypatch.setattr(community_api, "get_current_user", _anon)
    resp = asyncio.run(community_api.get_user_posts(
        owner, SimpleNamespace(), page=1, limit=20))

    assert resp["total"] == 2
    assert resp["has_more"] is False
    assert [p["id"] for p in resp["posts"]] == [p_pinned, p_new]
    # Bug 12 đã sửa: p.is_pinned có trong _POST_COLS nên payload phản ánh
    # đúng cột DB (trước đây _format_post luôn trả False vì thiếu cột).
    assert resp["posts"][0]["is_pinned"] is True
    assert resp["posts"][1]["is_pinned"] is False
    assert resp["posts"][0]["entity"] == {
        "id": ent, "name": "Cù lao An Bình", "type": "destination"}
    assert resp["posts"][0]["post_type_label"] == "Chia sẻ trải nghiệm"
    assert resp["posts"][0]["reactions"] == {}
    assert resp["posts"][1]["reactions"] == {"heart": 1}
    assert resp["posts"][0]["author"]["display_name"] == "Chủ Bài"


def test_get_user_posts_404_khi_user_khong_ton_tai(pg_db, monkeypatch):
    async def _anon(_request):
        return None

    monkeypatch.setattr(community_api, "get_current_user", _anon)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.get_user_posts(
            str(uuid.uuid4()), SimpleNamespace(), page=1, limit=20))
    assert exc.value.status_code == 404


def test_get_user_reviews_query_chi_tra_review_khi_tu_xem(pg_db, monkeypatch):
    owner = _seed_user(pg_db)
    _seed_post(pg_db, owner, "Chia sẻ thường", minutes_ago=10)
    r = _seed_post(pg_db, owner, "Đánh giá 4 sao", post_type="review",
                   rating=4, minutes_ago=5)

    async def _self(_request):
        return {"id": owner, "role": "user"}

    monkeypatch.setattr(community_api, "get_current_user", _self)
    resp = asyncio.run(community_api.get_user_reviews(
        owner, SimpleNamespace(), page=1, limit=20))

    assert resp["total"] == 1
    assert [p["id"] for p in resp["reviews"]] == [r]
    assert resp["reviews"][0]["rating"] == 4
    assert resp["has_more"] is False


def test_get_user_reviews_an_khi_ho_so_private_voi_nguoi_la(pg_db, monkeypatch):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    _seed_privacy(pg_db, owner, visibility="private", show_activity=True)
    _seed_post(pg_db, owner, "Đánh giá kín", post_type="review", rating=5)

    async def _stranger(_request):
        return {"id": stranger, "role": "user"}

    monkeypatch.setattr(community_api, "get_current_user", _stranger)
    resp = asyncio.run(community_api.get_user_reviews(
        owner, SimpleNamespace(), page=1, limit=20))
    assert resp == {"reviews": [], "total": 0, "page": 1, "has_more": False}


# ── timeline ──


def test_timeline_visibility_gate_ba_nhanh(pg_db):
    owner = _seed_user(pg_db)
    other = _seed_user(pg_db)
    _seed_privacy(pg_db, owner, visibility="public", show_activity=False)
    ph = pg_db._ph
    with pg_db._conn(commit_on_success=False) as conn:
        assert community_api._timeline_visibility_gate(
            conn, ph, str(uuid.uuid4()), None) == ("notfound", None)
        assert community_api._timeline_visibility_gate(
            conn, ph, owner, owner) == ("ok", owner)
        # show_activity=FALSE → người khác bị ẩn (require_activity).
        assert community_api._timeline_visibility_gate(
            conn, ph, owner, other) == ("hidden", owner)


def test_timeline_fetch_union_post_review_follow(pg_db):
    owner = _seed_user(pg_db)
    friend = _seed_user(pg_db, display_name="Bạn Đồng Hành")
    ent = _seed_entity(pg_db, name="Làng gốm Mang Thít")
    _seed_post(pg_db, owner, "Chia sẻ chuyến đi", minutes_ago=120)
    _seed_post(pg_db, owner, "Đánh giá làng gốm", post_type="review",
               entity_id=ent, rating=4, minutes_ago=60)
    _seed_follow(pg_db, owner, friend, minutes_ago=30)

    with pg_db._conn(commit_on_success=False) as conn:
        rows, total = community_api._timeline_fetch(
            conn, pg_db._ph, owner, None, 20, 0)

    assert total == 3
    ds = [pg_db._row_to_dict(r) for r in rows]
    assert [d["type"] for d in ds] == ["follow", "review", "post"]
    assert ds[0]["target_name"] == "Bạn Đồng Hành"
    assert ds[0]["ref_id"] == friend
    assert ds[1]["rating"] == 4
    assert ds[1]["entity_name"] == "Làng gốm Mang Thít"
    assert ds[2]["content"] == "Chia sẻ chuyến đi"


def test_timeline_item_ba_dang():
    ts = "2026-08-28 10:00:00"
    post = community_api._timeline_item({
        "type": "post", "created_at": ts, "ref_id": "p1", "content": None,
        "post_type": "share", "entity_name": None, "like_count": None,
    })
    assert post == {"type": "post", "created_at": ts, "data": {
        "id": "p1", "content": "", "post_type": "share",
        "entity_name": None, "like_count": 0}}

    review = community_api._timeline_item({
        "type": "review", "created_at": ts, "ref_id": "p2", "content": "Ngon",
        "post_type": "review", "entity_name": "Chợ Vĩnh Long", "like_count": 3,
        "rating": 5,
    })
    assert review["data"]["rating"] == 5
    assert review["data"]["entity_name"] == "Chợ Vĩnh Long"

    follow = community_api._timeline_item({
        "type": "follow", "created_at": ts, "ref_id": "u9", "target_name": None,
    })
    assert follow == {"type": "follow", "created_at": ts, "data": {
        "target_id": "u9", "target_name": "Người dùng"}}


def test_get_user_timeline_tu_xem_du_ba_loai_item(pg_db):
    owner = _seed_user(pg_db)
    friend = _seed_user(pg_db, display_name="Bạn Đồng Hành")
    ent = _seed_entity(pg_db, name="Làng gốm Mang Thít")
    _seed_post(pg_db, owner, "Chia sẻ chuyến đi", minutes_ago=120)
    _seed_post(pg_db, owner, "Đánh giá làng gốm", post_type="review",
               entity_id=ent, rating=4, minutes_ago=60)
    _seed_follow(pg_db, owner, friend, minutes_ago=30)

    resp = asyncio.run(community_api.get_user_timeline(
        owner, page=1, limit=20, user={"id": owner}))

    assert resp["total"] == 3
    assert resp["page"] == 1
    assert resp["has_more"] is False
    assert [it["type"] for it in resp["items"]] == ["follow", "review", "post"]
    assert resp["items"][0]["data"]["target_name"] == "Bạn Đồng Hành"
    assert resp["items"][1]["data"]["rating"] == 4


def test_get_user_timeline_404_khi_khong_ton_tai(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.get_user_timeline(
            str(uuid.uuid4()), page=1, limit=20, user=None))
    assert exc.value.status_code == 404


def test_get_user_timeline_an_voi_khach_khi_chua_dat_privacy(pg_db):
    # Không có hàng user_privacy → mặc định followers_only → khách bị ẩn.
    owner = _seed_user(pg_db)
    _seed_post(pg_db, owner, "Bài của chủ")
    resp = asyncio.run(community_api.get_user_timeline(
        owner, page=1, limit=20, user=None))
    assert resp == {"items": [], "total": 0, "page": 1, "has_more": False}


# ── wrappers cho AI (tools.py) ──


def test_get_community_reviews_chi_review_da_duyet_moi_truoc(pg_db):
    owner = _seed_user(pg_db, display_name="Chị Hai")
    ent = _seed_entity(pg_db, name="Bánh tráng cù lao Mây")
    other_ent = _seed_entity(pg_db)
    _seed_post(pg_db, owner, "Ngon lắm", post_type="review", entity_id=ent,
               rating=5, minutes_ago=60)
    _seed_post(pg_db, owner, "Rất đáng thử", post_type="review", entity_id=ent,
               rating=4, minutes_ago=5)
    _seed_post(pg_db, owner, "Chờ duyệt", post_type="review", entity_id=ent,
               rating=1, moderation_status="pending", minutes_ago=1)
    _seed_post(pg_db, owner, "Nơi khác", post_type="review",
               entity_id=other_ent, rating=2, minutes_ago=2)

    out = community_api.get_community_reviews(ent, limit=5)
    assert [o["content"] for o in out] == ["Rất đáng thử", "Ngon lắm"]
    assert out[0]["rating"] == 4
    assert out[0]["display_name"] == "Chị Hai"

    assert [o["content"] for o in community_api.get_community_reviews(ent, limit=1)] == [
        "Rất đáng thử"]


def test_get_trending_posts_xep_theo_diem_tuong_tac_va_loc_entity_type(pg_db):
    owner = _seed_user(pg_db)
    ent_food = _seed_entity(pg_db, etype="food", name="Bánh xèo hến Vĩnh Long")
    _seed_post(pg_db, owner, "Bài A", like_count=10, comment_count=0,
               minutes_ago=10)
    _seed_post(pg_db, owner, "Bài B", like_count=2, comment_count=5,
               entity_id=ent_food, minutes_ago=20)
    _seed_post(pg_db, owner, "Bài C", like_count=0, comment_count=0,
               minutes_ago=30)
    _seed_post(pg_db, owner, "Bài pending", like_count=99,
               moderation_status="pending")

    out = community_api.get_trending_posts(limit=10)
    # điểm = like + 2*comment: B=12 > A=10 > C=0; pending bị loại.
    assert [o["content"] for o in out] == ["Bài B", "Bài A", "Bài C"]

    out_food = community_api.get_trending_posts(limit=10, entity_type="food")
    assert [o["content"] for o in out_food] == ["Bài B"]
    assert out_food[0]["entity_name"] == "Bánh xèo hến Vĩnh Long"


# ── _resolve_user_id / _format_post_jobj ──


def test_resolve_user_id_cac_nhanh(pg_db):
    owner = _seed_user(pg_db, username="dan-vinh-long-x1")
    inactive = _seed_user(pg_db, is_active=False)
    erased = _seed_user(pg_db, deleted=True)

    assert community_api._resolve_user_id(owner) == owner
    assert community_api._resolve_user_id("Dan-Vinh-Long-X1") == owner
    assert community_api._resolve_user_id(inactive) is None
    assert community_api._resolve_user_id(erased) is None
    assert community_api._resolve_user_id(str(uuid.uuid4())) is None
    assert community_api._resolve_user_id("") is None
    assert community_api._resolve_user_id("   ") is None


def test_format_post_jobj_chuan_hoa_json_object():
    assert community_api._format_post_jobj({"a": 1}) == {"a": 1}
    assert community_api._format_post_jobj('{"a": 1}') == {"a": 1}
    assert community_api._format_post_jobj("không phải json") is None
    assert community_api._format_post_jobj("[1, 2]") is None
    assert community_api._format_post_jobj(None) is None
    assert community_api._format_post_jobj(42) is None
