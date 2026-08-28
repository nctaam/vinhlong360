# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI của miền BÀI VIẾT (community/api.py) trên PostgreSQL thật.

Phủ các handler/closure chưa từng chạy trên DB thật: helpers enrich/mentions/notify,
create_post/get_post/update_post/delete_post, nháp (save/list/update/publish/delete),
hẹn giờ (schedule/list/cancel) và get_post_edit_history.

Khuôn harness theo test_account_control_plane_postgres.py:
  - adapter = database.Database(); adapter._use_pg = True; adapter._dsn = URL
  - monkeypatch db vào ĐÚNG module thực thi (community.api) — handler đọc globals
    của module thật, shim không cứu được monkeypatch.
  - Side-effect ngoài miền (moderation, notifications, ratelimit, achievements)
    được stub thành recorder — module gốc của chúng import db RIÊNG (SQLite thật),
    tuyệt đối không để chạy thật.

Cổng env: UGC_SURFACE_TEST_DATABASE_URL (DB tên phải chứa 'test', host loopback;
override bằng UGC_SURFACE_ALLOW_PG_TESTS). Thiếu env → skip toàn file; env có mà
DB chết → test đỏ (fixture connect thẳng, không nuốt lỗi).
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
            "PostgreSQL community-posts tests require a database name containing "
            "'test' or UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL community-posts tests require "
            "UGC_SURFACE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set UGC_SURFACE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)

# Bảng miền bài viết đụng tới trong file này. TRUNCATE quanh mỗi test.
_TABLES = (
    "post_edit_history, post_reactions, likes, bookmarks, follows, blocks, "
    "user_mutes, notifications, posts, entities, users"
)


def _truncate() -> None:
    conn = psycopg2.connect(TEST_DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(f"TRUNCATE {_TABLES} CASCADE")
    finally:
        conn.close()


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    # database.py chỉ import psycopg2 khi USE_PG lúc import module — tiêm tay.
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    monkeypatch.setattr(community_api, "db", adapter)
    _truncate()
    try:
        yield adapter
    finally:
        _truncate()


@pytest.fixture
def stubs(monkeypatch):
    """Stub mọi side-effect ngoài miền thành recorder — không cho chạy thật."""
    calls = {
        "check_rate": [],
        "moderate": [],
        "log_mod": [],
        "notify": [],
        "achievements": [],
    }

    def _check_rate(*args, **kwargs):
        calls["check_rate"].append(args)

    async def _moderate(content, user_id="", ip="", image_urls=None):
        calls["moderate"].append(content)
        return {"status": "approved", "score": 0.0, "reasons": []}

    def _log_moderation(*args, **kwargs):
        calls["log_mod"].append(args)

    def _create_notification(*args, **kwargs):
        calls["notify"].append((args, kwargs))

    def _achievements(user_id):
        calls["achievements"].append(user_id)

    monkeypatch.setattr(community_api, "check_rate", _check_rate)
    monkeypatch.setattr(community_api, "moderate_content_enhanced", _moderate)
    monkeypatch.setattr(community_api, "log_moderation", _log_moderation)
    monkeypatch.setattr(community_api, "create_notification", _create_notification)
    monkeypatch.setattr(community_api, "_check_achievements_bg", _achievements)
    return calls


# ── Seed helpers (SQL thẳng qua adapter PG) ──

def _seed_user(pg_db, display_name="Người kiểm thử", role="user") -> dict:
    user_id = str(uuid.uuid4())
    phone = f"test-{uuid.uuid4().hex}"
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO users (id, phone, display_name, role, is_active)
            VALUES (%s::uuid, %s, %s, %s, TRUE)
            """,
            (user_id, phone, display_name, role),
        )
    return {"id": user_id, "display_name": display_name, "role": role}


def _seed_post(
    pg_db,
    user_id: str,
    *,
    content="Bài viết mẫu về cù lao An Bình đủ dài mười ký tự",
    status="approved",
    post_type="share",
    rating=None,
    entity_id=None,
    is_draft=False,
    scheduled_at=None,
    repost_of=None,
) -> str:
    post_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO posts (id, user_id, content, post_type, rating, entity_id,
                               moderation_status, is_draft, scheduled_at, repost_of)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::uuid)
            """,
            (post_id, user_id, content, post_type, rating, entity_id,
             status, is_draft, scheduled_at, repost_of),
        )
    return post_id


def _seed_entity(pg_db, entity_id="cho-noi-tra-on", name="Chợ nổi Trà Ôn") -> str:
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO entities (id, type, name) VALUES (%s, 'destination', %s)",
            (entity_id, name),
        )
    return entity_id


def _post_row(pg_db, post_id: str) -> dict | None:
    with pg_db._conn() as conn:
        row = pg_db._fetchone(
            conn, "SELECT * FROM posts WHERE id = %s::uuid", (post_id,)
        )
    return pg_db._row_to_dict(row) if row else None


def _count(pg_db, sql: str, params=()) -> int:
    with pg_db._conn() as conn:
        row = pg_db._fetchone(conn, sql, params)
    return pg_db._row_to_dict(row)["c"]


FUTURE_TS = "2035-01-01T07:00:00+07:00"
PAST_TS = "2020-01-01T00:00:00Z"


# ══════════════════════════════════════════════════
#  Helpers thuần + helpers chạm DB
# ══════════════════════════════════════════════════

def test_prod_seed_post_filter_ngoai_production(pg_db, monkeypatch):
    """Ngoài production: bộ lọc bài seed trả rỗng — không thêm điều kiện SQL."""
    monkeypatch.setattr(community_api, "_cfg", SimpleNamespace(is_production=False))
    assert community_api._prod_seed_post_filter() == ("", [])


def test_prod_seed_post_filter_production(pg_db, monkeypatch):
    """Production: mỗi cụm từ test sinh 2 mệnh đề NOT LIKE (content + snapshot)."""
    monkeypatch.setattr(community_api, "_cfg", SimpleNamespace(is_production=True))
    sql, params = community_api._prod_seed_post_filter(alias="p")
    assert sql.startswith(" AND ")
    assert sql.count("NOT LIKE") == len(community_api._PROD_TEST_POST_PHRASES) * 2
    assert len(params) == len(community_api._PROD_TEST_POST_PHRASES) * 2
    assert all(p.startswith("%") and p.endswith("%") for p in params)
    assert "%test admin%" in params


def test_enrich_user_status_gan_co_like_bookmark(pg_db):
    """Gắn is_liked/is_bookmarked theo đúng bảng likes/bookmarks trên PG."""
    user = _seed_user(pg_db)
    p1 = _seed_post(pg_db, user["id"])
    p2 = _seed_post(pg_db, user["id"], content="Bài thứ hai về làng nghề dừa Mỏ Cày")
    with pg_db._conn() as conn:
        pg_db._execute(
            conn, "INSERT INTO likes (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (user["id"], p1),
        )
        pg_db._execute(
            conn, "INSERT INTO bookmarks (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (user["id"], p2),
        )

    posts = [{"id": p1}, {"id": p2}]
    out = community_api._enrich_user_status(posts, user)
    assert out is posts
    assert posts[0]["is_liked"] is True and posts[0]["is_bookmarked"] is False
    assert posts[1]["is_liked"] is False and posts[1]["is_bookmarked"] is True


def test_enrich_user_status_khach_tra_nguyen_ven(pg_db):
    """Khách (user=None): trả nguyên danh sách, không gắn cờ, không chạm DB."""
    posts = [{"id": str(uuid.uuid4())}]
    out = community_api._enrich_user_status(posts, None)
    assert out is posts
    assert "is_liked" not in posts[0]


def test_enrich_reactions_dem_theo_loai(pg_db):
    """Đếm reaction theo loại cho từng bài; bài không có reaction → {}.

    Loại reaction phải nằm trong CHECK của bảng post_reactions:
    heart / useful / beautiful / funny / surprised.
    """
    u1 = _seed_user(pg_db)
    u2 = _seed_user(pg_db)
    p1 = _seed_post(pg_db, u1["id"])
    p2 = _seed_post(pg_db, u1["id"], content="Bài không có reaction nào ở đây cả")
    with pg_db._conn() as conn:
        for uid, rtype in ((u1["id"], "heart"), (u2["id"], "heart"), (u2["id"], "funny")):
            pg_db._execute(
                conn,
                "INSERT INTO post_reactions (post_id, user_id, reaction_type) "
                "VALUES (%s::uuid, %s::uuid, %s)",
                (p1, uid, rtype),
            )

    posts = [{"id": p1}, {"id": p2}]
    community_api._enrich_reactions(posts)
    assert posts[0]["reactions"] == {"heart": 2, "funny": 1}
    assert posts[1]["reactions"] == {}
    # Danh sách rỗng: trả sớm, không lỗi
    assert community_api._enrich_reactions([]) == []


def test_clean_mentions_chuan_hoa():
    """Bỏ mục sai, cắt id 64 / label 80, chỉ xét 20 mục đầu."""
    dai_id = "a" * 100
    dai_label = "b" * 100
    raw = [
        {"type": "user", "id": "u-1", "label": "Bạn A"},
        {"type": "entity", "id": "e-1", "label": "Chợ Lách"},
        {"type": "khac", "id": "x", "label": "sai type"},
        {"type": "user", "id": "", "label": "thiếu id"},
        {"type": "user", "id": "u-2", "label": ""},
        "không phải dict",
        {"type": "user", "id": dai_id, "label": dai_label},
    ]
    out = community_api._clean_mentions(raw)
    assert out[0] == {"type": "user", "id": "u-1", "label": "Bạn A"}
    assert out[1] == {"type": "entity", "id": "e-1", "label": "Chợ Lách"}
    assert out[2]["id"] == "a" * 64 and out[2]["label"] == "b" * 80
    assert len(out) == 3
    assert community_api._clean_mentions(None) == []
    # 25 mục hợp lệ nhưng chỉ 20 mục đầu được xét
    nhieu = [{"type": "user", "id": f"u{i}", "label": f"N{i}"} for i in range(25)]
    assert len(community_api._clean_mentions(nhieu)) == 20


def test_notify_mentions_bo_tu_nhac_va_trung(pg_db, stubs):
    """Chỉ báo mention type=user, bỏ tự-nhắc + trùng; preview cắt 80 ký tự."""
    author_id = str(uuid.uuid4())
    khac_id = str(uuid.uuid4())
    khac2_id = str(uuid.uuid4())
    mentions = [
        {"type": "user", "id": khac_id, "label": "Bạn"},
        {"type": "user", "id": khac_id, "label": "Bạn lần hai"},
        {"type": "user", "id": author_id, "label": "Chính mình"},
        {"type": "entity", "id": "e-1", "label": "Địa điểm"},
        {"type": "user", "id": khac2_id, "label": "Bạn khác"},
    ]
    content = "x" * 100
    community_api._notify_mentions(mentions, author_id, "Tác Giả", "post-1", content)
    assert [c[0][0] for c in stubs["notify"]] == [khac_id, khac2_id]
    args, kwargs = stubs["notify"][0]
    assert args[1] == "mention"
    assert "Tác Giả" in args[2]
    assert kwargs["body"] == "x" * 80 + "…"
    assert kwargs["ref_id"] == "post-1" and kwargs["actor_id"] == author_id


def test_notify_mentions_nuot_loi_notification(pg_db, monkeypatch):
    """Lỗi khi tạo notification bị nuốt (log), không lan ra ngoài."""
    def _no(*_args, **_kwargs):
        raise RuntimeError("hỏng notification")

    monkeypatch.setattr(community_api, "create_notification", _no)
    community_api._notify_mentions(
        [{"type": "user", "id": str(uuid.uuid4()), "label": "Bạn"}],
        str(uuid.uuid4()), "Ai đó", "post-1", "nội dung",
    )  # không raise là đạt


def test_notify_entity_followers_bao_dung_nguoi_theo_doi(pg_db, stubs):
    """Báo mọi follower của entity, loại chính tác giả."""
    author = _seed_user(pg_db)
    f1 = _seed_user(pg_db)
    f2 = _seed_user(pg_db)
    with pg_db._conn() as conn:
        for uid in (author["id"], f1["id"], f2["id"]):
            pg_db._execute(
                conn,
                "INSERT INTO follows (follower_id, target_type, target_id) "
                "VALUES (%s::uuid, 'entity', %s)",
                (uid, "diem-x"),
            )
    community_api._notify_entity_followers("diem-x", author["id"], "Tác Giả", "post-9")
    nhan = sorted(c[0][0] for c in stubs["notify"])
    assert nhan == sorted([f1["id"], f2["id"]])
    assert all(c[0][1] == "entity_post" for c in stubs["notify"])


def test_notify_entity_followers_khong_entity(pg_db, stubs):
    """entity_id rỗng → trả sớm, không notification nào."""
    community_api._notify_entity_followers(None, str(uuid.uuid4()), "Ai", "post-1")
    assert stubs["notify"] == []


def test_update_post_validate_rating():
    """UpdatePost.rating: None/1..5 hợp lệ; ngoài khoảng bị pydantic chặn."""
    assert community_api.UpdatePost(rating=3).rating == 3
    assert community_api.UpdatePost(rating=None).rating is None
    with pytest.raises(ValidationError):
        community_api.UpdatePost(rating=0)
    with pytest.raises(ValidationError):
        community_api.UpdatePost(rating=6)


def test_validate_post_type_guard():
    """review phải gắn entity và có sao; share không ràng buộc."""
    review_thieu_entity = community_api.CreatePost(
        content="Nội dung review đủ dài mười ký tự", post_type="review", rating=4
    )
    with pytest.raises(HTTPException) as exc:
        community_api._validate_post_type(review_thieu_entity)
    assert exc.value.status_code == 400

    review_thieu_sao = community_api.CreatePost(
        content="Nội dung review đủ dài mười ký tự", post_type="review",
        entity_id="diem-x",
    )
    with pytest.raises(HTTPException) as exc:
        community_api._validate_post_type(review_thieu_sao)
    assert exc.value.status_code == 400

    share = community_api.CreatePost(content="Chia sẻ bình thường đủ mười ký tự")
    community_api._validate_post_type(share)  # không raise


def test_process_repost_cac_nhanh(pg_db):
    """_process_repost: 404 bài gốc mất, 400 repost-của-repost, 400 tự repost, happy cắt 280."""
    user = {"id": str(uuid.uuid4())}
    with pytest.raises(HTTPException) as exc:
        community_api._process_repost(None, user)
    assert exc.value.status_code == 404

    da_la_repost = {"id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()),
                    "repost_of": str(uuid.uuid4()), "content": "x", "display_name": "A",
                    "created_at": "2026-01-01"}
    with pytest.raises(HTTPException) as exc:
        community_api._process_repost(da_la_repost, user)
    assert exc.value.status_code == 400

    bai_cua_minh = {"id": str(uuid.uuid4()), "user_id": user["id"], "repost_of": None,
                    "content": "x", "display_name": "A", "created_at": "2026-01-01"}
    with pytest.raises(HTTPException) as exc:
        community_api._process_repost(bai_cua_minh, user)
    assert exc.value.status_code == 400

    orig = {"id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "repost_of": None,
            "content": "d" * 300, "display_name": "Tác Giả Gốc", "created_at": "2026-01-01"}
    snapshot, orig_author = community_api._process_repost(orig, user)
    assert orig_author == orig["user_id"]
    assert snapshot["author"] == "Tác Giả Gốc"
    assert snapshot["content"] == "d" * 280


def test_notify_new_post_bao_repost(pg_db, stubs):
    """_notify_new_post: mention + repost đều báo; tự-repost thì không báo repost."""
    user = {"id": str(uuid.uuid4()), "display_name": "Người Đăng"}
    khac = str(uuid.uuid4())
    orig_author = str(uuid.uuid4())
    mentions = [{"type": "user", "id": khac, "label": "Bạn"}]
    community_api._notify_new_post(mentions, user, "post-1", "nội dung", None, orig_author)
    types = [c[0][1] for c in stubs["notify"]]
    assert types == ["mention", "repost"]
    assert stubs["notify"][1][0][0] == orig_author

    stubs["notify"].clear()
    community_api._notify_new_post([], user, "post-2", "nội dung", None, user["id"])
    assert stubs["notify"] == []


# ══════════════════════════════════════════════════
#  create_post
# ══════════════════════════════════════════════════

def test_create_post_share_hop_le(pg_db, stubs):
    """Happy path share: bài vào bảng posts đúng giá trị, hashtag trích từ nội dung."""
    user = _seed_user(pg_db, display_name="Chị Bảy Chợ Lách")
    body = community_api.CreatePost(
        content="Sáng ghé chợ nổi Trà Ôn, ghe trái cây đậu kín bến #chợnổi #TràÔn"
    )
    res = asyncio.run(community_api.create_post(body, user=user))
    post = res["post"]
    assert post["post_type"] == "share"
    assert post["hashtags"] == ["chợnổi", "tràôn"]
    assert post["author"]["display_name"] == "Chị Bảy Chợ Lách"
    assert "moderation_notice" not in post

    row = _post_row(pg_db, post["id"])
    assert row["content"] == body.content
    assert row["moderation_status"] == "approved"
    assert row["hashtags"] == ["chợnổi", "tràôn"]
    assert str(row["user_id"]) == user["id"]
    # log_moderation được gọi đúng đối tượng
    assert stubs["log_mod"] and stubs["log_mod"][0][:3] == ("post", post["id"], "approved")
    # share không mention, không entity → không notification nào
    assert stubs["notify"] == []


def test_create_post_trung_noi_dung_409(pg_db, stubs):
    """Đăng lại đúng nội dung trong 1 giờ → 409, DB vẫn chỉ 1 bài."""
    user = _seed_user(pg_db)
    body = community_api.CreatePost(content="Nội dung y hệt nhau để thử chống trùng")
    asyncio.run(community_api.create_post(body, user=user))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.create_post(body, user=user))
    assert exc.value.status_code == 409
    assert _count(pg_db, "SELECT COUNT(*) AS c FROM posts") == 1


def test_create_post_post_type_khong_hop_le():
    """post_type lạ bị pydantic chặn ngay từ model."""
    with pytest.raises(ValidationError):
        community_api.CreatePost(content="Nội dung đủ dài mười ký tự", post_type="tin-vit")


def test_create_post_review_gan_entity_hop_le(pg_db, stubs):
    """Review hợp lệ: entity thật trong bảng entities, sao được lưu, mention được báo."""
    user = _seed_user(pg_db)
    ban = _seed_user(pg_db)
    eid = _seed_entity(pg_db)
    body = community_api.CreatePost(
        content="Ốc gạo Tân Phú luộc sả chấm cơm mẻ, ngon nhức nách",
        post_type="review", entity_id=eid, rating=5,
        mentions=[{"type": "user", "id": ban["id"], "label": "Bạn đi cùng"}],
    )
    res = asyncio.run(community_api.create_post(body, user=user))
    post = res["post"]
    assert post["rating"] == 5
    assert post["entity_id"] == eid
    assert post["mentions"] == [{"type": "user", "id": ban["id"], "label": "Bạn đi cùng"}]

    row = _post_row(pg_db, post["id"])
    assert row["post_type"] == "review" and row["rating"] == 5
    assert row["entity_id"] == eid
    # mention được báo cho đúng người
    mention_calls = [c for c in stubs["notify"] if c[0][1] == "mention"]
    assert len(mention_calls) == 1 and mention_calls[0][0][0] == ban["id"]


def test_create_post_entity_khong_ton_tai_404(pg_db, stubs):
    """entity_id không có trong bảng entities → 404, không ghi bài."""
    user = _seed_user(pg_db)
    body = community_api.CreatePost(
        content="Nội dung đủ dài mười ký tự", entity_id="khong-ton-tai-dau"
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.create_post(body, user=user))
    assert exc.value.status_code == 404
    assert _count(pg_db, "SELECT COUNT(*) AS c FROM posts") == 0


def test_create_post_noi_dung_rong_400(pg_db, stubs):
    """Nội dung rỗng mà không phải repost → 400 (model cho rỗng, handler chặn)."""
    user = _seed_user(pg_db)
    body = community_api.CreatePost(content="")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.create_post(body, user=user))
    assert exc.value.status_code == 400


def test_create_post_repost_hop_le(pg_db, stubs):
    """Repost không lời: snapshot bài gốc vào DB, tác giả gốc được báo 'repost'."""
    tac_gia = _seed_user(pg_db, display_name="Tác Giả Gốc")
    orig_id = _seed_post(pg_db, tac_gia["id"],
                         content="Bài gốc kể chuyện đạp xe xuyên cù lao Minh")
    nguoi_dang_lai = _seed_user(pg_db, display_name="Người Đăng Lại")
    body = community_api.CreatePost(content="", repost_of=orig_id)
    res = asyncio.run(community_api.create_post(body, user=nguoi_dang_lai))
    post = res["post"]
    assert post["repost_of"] == orig_id
    assert post["repost"]["author"] == "Tác Giả Gốc"
    assert post["repost"]["content"].startswith("Bài gốc kể chuyện")

    row = _post_row(pg_db, post["id"])
    assert str(row["repost_of"]) == orig_id
    assert row["repost_snapshot"]["id"] == orig_id
    repost_calls = [c for c in stubs["notify"] if c[0][1] == "repost"]
    assert len(repost_calls) == 1 and repost_calls[0][0][0] == tac_gia["id"]


def test_create_post_moderation_pending(pg_db, stubs, monkeypatch):
    """Kiểm duyệt trả pending: có moderation_notice, KHÔNG bắn notification."""
    user = _seed_user(pg_db)
    ban = _seed_user(pg_db)

    async def _pending(content, user_id="", ip="", image_urls=None):
        return {"status": "pending", "score": 0.9, "reasons": ["nghi spam"]}

    monkeypatch.setattr(community_api, "moderate_content_enhanced", _pending)
    body = community_api.CreatePost(
        content="Nội dung chờ duyệt dài hơn mười ký tự",
        mentions=[{"type": "user", "id": ban["id"], "label": "Bạn"}],
    )
    res = asyncio.run(community_api.create_post(body, user=user))
    assert res["post"]["moderation_notice"] == "Bài viết đang chờ kiểm duyệt"
    row = _post_row(pg_db, res["post"]["id"])
    assert row["moderation_status"] == "pending"
    assert stubs["notify"] == []


def test_create_post_bi_can_rate_limit(pg_db, stubs, monkeypatch):
    """Nhánh bị-cản: check_rate raise 429 → handler dừng ngay, không ghi bài."""
    user = _seed_user(pg_db)

    def _chan(*_args, **_kwargs):
        raise HTTPException(429, "Bạn đăng bài quá nhanh.")

    monkeypatch.setattr(community_api, "check_rate", _chan)
    body = community_api.CreatePost(content="Nội dung đủ dài mười ký tự")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.create_post(body, user=user))
    assert exc.value.status_code == 429
    assert _count(pg_db, "SELECT COUNT(*) AS c FROM posts") == 0


def test_create_post_anh_bi_tu_choi_400(pg_db, stubs):
    """Chốt AI-only media: gửi ảnh UGC → 400 ngay trước mọi bước khác."""
    user = _seed_user(pg_db)
    body = community_api.CreatePost(
        content="Nội dung đủ dài mười ký tự", images=["https://x/anh.jpg"]
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.create_post(body, user=user))
    assert exc.value.status_code == 400


# ══════════════════════════════════════════════════
#  Nháp: save / list / update / publish / delete
# ══════════════════════════════════════════════════

def test_save_draft_hop_le(pg_db, stubs):
    """Nháp mới vào bảng posts với is_draft=TRUE, moderation_status 'pending'."""
    user = _seed_user(pg_db)
    body = community_api.DraftPost(content="Nháp về lò kẹo dừa ở Mỏ Cày Nam")
    res = asyncio.run(community_api.save_draft(body, user=user))
    draft = res["draft"]
    assert isinstance(draft["id"], str)
    row = _post_row(pg_db, draft["id"])
    assert row["is_draft"] is True
    assert row["moderation_status"] == "pending"
    assert row["content"] == body.content


def test_save_draft_qua_20_bi_chan_400(pg_db, stubs):
    """Đủ 20 nháp → nháp thứ 21 bị 400, DB giữ nguyên 20."""
    user = _seed_user(pg_db)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO posts (user_id, content, is_draft) "
            "SELECT %s::uuid, 'nháp số ' || g, TRUE FROM generate_series(1, 20) g",
            (user["id"],),
        )
    body = community_api.DraftPost(content="Nháp thứ hai mươi mốt")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.save_draft(body, user=user))
    assert exc.value.status_code == 400
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM posts WHERE user_id = %s::uuid AND is_draft",
        (user["id"],),
    ) == 20


def test_list_drafts_sap_xep_va_loc(pg_db, stubs):
    """Chỉ nháp của chính user, mới-sửa lên trước; bài thường không lọt vào.

    Không dùng UPDATE để lùi updated_at: trigger trg_posts_updated (BEFORE UPDATE)
    luôn ghi đè updated_at = NOW(). Lùi giờ phải đặt ngay trong INSERT.
    """
    user = _seed_user(pg_db)
    cu = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO posts (id, user_id, content, is_draft, updated_at) "
            "VALUES (%s::uuid, %s::uuid, %s, TRUE, NOW() - INTERVAL '1 hour')",
            (cu, user["id"], "Nháp cũ hơn một tiếng"),
        )
    moi = _seed_post(pg_db, user["id"], content="Nháp mới sửa xong", is_draft=True)
    _seed_post(pg_db, user["id"], content="Bài đã đăng không phải nháp")
    res = asyncio.run(community_api.list_drafts(page=1, limit=20, user=user))
    assert res["total"] == 2
    assert [d["id"] for d in res["drafts"]] == [moi, cu]
    assert res["has_more"] is False


def test_update_draft_hop_le(pg_db, stubs):
    """Sửa nháp: nội dung + sao mới nằm trong DB."""
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], content="Nháp trước khi sửa", is_draft=True)
    body = community_api.DraftPost(content="Nháp sau khi sửa xong xuôi",
                                   post_type="review", rating=4)
    res = asyncio.run(community_api.update_draft(draft_id, body, user=user))
    assert res["draft"]["id"] == draft_id
    row = _post_row(pg_db, draft_id)
    assert row["content"] == "Nháp sau khi sửa xong xuôi"
    assert row["post_type"] == "review" and row["rating"] == 4
    assert row["is_draft"] is True


def test_update_draft_khong_ton_tai_404(pg_db, stubs):
    user = _seed_user(pg_db)
    body = community_api.DraftPost(content="Không có nháp nào như vậy")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.update_draft(str(uuid.uuid4()), body, user=user))
    assert exc.value.status_code == 404


def test_publish_draft_hop_le(pg_db, stubs):
    """Đăng nháp: is_draft=FALSE, status theo kiểm duyệt, hashtag trích lại."""
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], status="pending", is_draft=True,
                          content="Nháp sắp đăng về #bánhtráng Mỹ Lồng")
    res = asyncio.run(community_api.publish_draft(draft_id, user=user))
    assert res["post"]["id"] == draft_id
    row = _post_row(pg_db, draft_id)
    assert row["is_draft"] is False
    assert row["moderation_status"] == "approved"
    assert row["hashtags"] == ["bánhtráng"]
    assert stubs["log_mod"] and stubs["log_mod"][0][:3] == ("post", draft_id, "approved")


def test_publish_draft_khong_ton_tai_404(pg_db, stubs):
    user = _seed_user(pg_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.publish_draft(str(uuid.uuid4()), user=user))
    assert exc.value.status_code == 404


def test_publish_draft_noi_dung_ngan_400(pg_db, stubs):
    """Nháp dưới 10 ký tự không đăng được, vẫn nằm ở dạng nháp."""
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], content="ngắn", is_draft=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.publish_draft(draft_id, user=user))
    assert exc.value.status_code == 400
    assert _post_row(pg_db, draft_id)["is_draft"] is True


def test_delete_draft_hop_le(pg_db, stubs):
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], content="Nháp sắp bị xoá đi", is_draft=True)
    res = asyncio.run(community_api.delete_draft(draft_id, user=user))
    assert res == {"success": True}
    assert _post_row(pg_db, draft_id) is None


def test_delete_draft_khong_ton_tai_404(pg_db, stubs):
    user = _seed_user(pg_db)
    # Bài KHÔNG phải nháp cũng không xoá được qua đường này
    post_id = _seed_post(pg_db, user["id"])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.delete_draft(post_id, user=user))
    assert exc.value.status_code == 404
    assert _post_row(pg_db, post_id) is not None


# ══════════════════════════════════════════════════
#  Hẹn giờ: schedule / list / cancel
# ══════════════════════════════════════════════════

def test_schedule_draft_hop_le(pg_db, stubs):
    """Đặt lịch: scheduled_at vào DB, nháp rời trạng thái draft."""
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], content="Nháp chờ đến giờ đăng", is_draft=True)
    res = asyncio.run(
        community_api.schedule_draft(draft_id, scheduled_at=FUTURE_TS, user=user)
    )
    assert res == {"success": True, "scheduled_at": FUTURE_TS}
    row = _post_row(pg_db, draft_id)
    assert row["scheduled_at"] is not None
    assert row["is_draft"] is False


def test_schedule_draft_qua_khu_400(pg_db, stubs):
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], content="Nháp đặt lịch lùi", is_draft=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.schedule_draft(draft_id, scheduled_at=PAST_TS, user=user))
    assert exc.value.status_code == 400
    assert exc.value.detail == "Thời gian đặt lịch phải trong tương lai"


def test_schedule_draft_dinh_dang_sai_400(pg_db, stubs):
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], content="Nháp đặt lịch hỏng", is_draft=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.schedule_draft(draft_id, scheduled_at="khong-phai-gio", user=user)
        )
    assert exc.value.status_code == 400
    assert "ISO 8601" in exc.value.detail


def test_schedule_draft_khong_ton_tai_404(pg_db, stubs):
    user = _seed_user(pg_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.schedule_draft(str(uuid.uuid4()), scheduled_at=FUTURE_TS, user=user)
        )
    assert exc.value.status_code == 404


def test_schedule_draft_noi_dung_ngan_400(pg_db, stubs):
    user = _seed_user(pg_db)
    draft_id = _seed_post(pg_db, user["id"], content="ngắn", is_draft=True)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.schedule_draft(draft_id, scheduled_at=FUTURE_TS, user=user)
        )
    assert exc.value.status_code == 400
    assert _post_row(pg_db, draft_id)["is_draft"] is True


def test_list_scheduled_chi_bai_tuong_lai(pg_db, stubs):
    """Chỉ liệt kê bài hẹn giờ CHƯA tới; bài lịch đã qua không hiện."""
    user = _seed_user(pg_db)
    sap_toi = _seed_post(pg_db, user["id"], content="Bài hẹn giờ sắp tới",
                         is_draft=False, scheduled_at=FUTURE_TS)
    _seed_post(pg_db, user["id"], content="Bài lịch đã trôi qua",
               is_draft=False, scheduled_at=PAST_TS)
    res = asyncio.run(community_api.list_scheduled(page=1, limit=20, user=user))
    assert res["total"] == 1
    assert res["scheduled"][0]["id"] == sap_toi
    assert res["has_more"] is False


def test_cancel_scheduled_hop_le(pg_db, stubs):
    """Huỷ lịch: bài quay về nháp, scheduled_at xoá sạch."""
    user = _seed_user(pg_db)
    post_id = _seed_post(pg_db, user["id"], content="Bài hẹn giờ sẽ bị huỷ",
                         is_draft=False, scheduled_at=FUTURE_TS)
    res = asyncio.run(community_api.cancel_scheduled(post_id, user=user))
    assert res == {"success": True}
    row = _post_row(pg_db, post_id)
    assert row["is_draft"] is True and row["scheduled_at"] is None


def test_cancel_scheduled_khong_co_lich_404(pg_db, stubs):
    user = _seed_user(pg_db)
    post_id = _seed_post(pg_db, user["id"])  # bài thường, không có lịch
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.cancel_scheduled(post_id, user=user))
    assert exc.value.status_code == 404


# ══════════════════════════════════════════════════
#  get_post
# ══════════════════════════════════════════════════

def test_get_post_khach_xem_duoc(pg_db):
    """Khách (user=None) đọc bài đã duyệt: đủ author + nhãn loại bài."""
    tac_gia = _seed_user(pg_db, display_name="Chú Tư Cồn Phụng")
    post_id = _seed_post(pg_db, tac_gia["id"])
    res = asyncio.run(community_api.get_post(post_id, user=None))
    post = res["post"]
    assert post["id"] == post_id
    assert post["author"]["display_name"] == "Chú Tư Cồn Phụng"
    assert post["post_type_label"] == "Chia sẻ trải nghiệm"
    assert post["is_liked"] is False and post["is_bookmarked"] is False


def test_get_post_dang_nhap_thay_co_like(pg_db):
    """Người xem đã like + bookmark: hai cờ bật đúng từ bảng thật."""
    tac_gia = _seed_user(pg_db)
    nguoi_xem = _seed_user(pg_db)
    post_id = _seed_post(pg_db, tac_gia["id"])
    with pg_db._conn() as conn:
        pg_db._execute(
            conn, "INSERT INTO likes (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (nguoi_xem["id"], post_id),
        )
        pg_db._execute(
            conn, "INSERT INTO bookmarks (user_id, post_id) VALUES (%s::uuid, %s::uuid)",
            (nguoi_xem["id"], post_id),
        )
    res = asyncio.run(community_api.get_post(post_id, user=nguoi_xem))
    assert res["post"]["is_liked"] is True
    assert res["post"]["is_bookmarked"] is True


def test_get_post_khong_ton_tai_hoac_chua_duyet_404(pg_db):
    tac_gia = _seed_user(pg_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.get_post(str(uuid.uuid4()), user=None))
    assert exc.value.status_code == 404
    # bài pending không lộ ra ngoài
    pending_id = _seed_post(pg_db, tac_gia["id"], status="pending")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.get_post(pending_id, user=None))
    assert exc.value.status_code == 404


def test_get_post_bi_chan_404(pg_db):
    """Tác giả block người xem → bài biến mất với người đó (404)."""
    tac_gia = _seed_user(pg_db)
    nguoi_xem = _seed_user(pg_db)
    post_id = _seed_post(pg_db, tac_gia["id"])
    with pg_db._conn() as conn:
        pg_db._execute(
            conn, "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s::uuid, %s::uuid)",
            (tac_gia["id"], nguoi_xem["id"]),
        )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.get_post(post_id, user=nguoi_xem))
    assert exc.value.status_code == 404


# ══════════════════════════════════════════════════
#  delete_post
# ══════════════════════════════════════════════════

def test_delete_post_chinh_chu_don_dep(pg_db, stubs):
    """Soft-delete + dọn notification tham chiếu + gỡ repost_of của bài đăng lại."""
    chu = _seed_user(pg_db)
    nguoi_khac = _seed_user(pg_db)
    post_id = _seed_post(pg_db, chu["id"])
    repost_id = _seed_post(pg_db, nguoi_khac["id"], content="", repost_of=post_id)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO notifications (user_id, type, title, ref_type, ref_id) "
            "VALUES (%s::uuid, 'like', 'Ai đó thích bài', 'post', %s)",
            (chu["id"], post_id),
        )

    res = asyncio.run(community_api.delete_post(post_id, user=chu))
    assert res == {"success": True}
    assert _post_row(pg_db, post_id)["deleted_at"] is not None
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM notifications WHERE ref_type='post' AND ref_id=%s",
        (post_id,),
    ) == 0
    assert _post_row(pg_db, repost_id)["repost_of"] is None


def test_delete_post_khong_quyen_403(pg_db, stubs):
    chu = _seed_user(pg_db)
    ke_la = _seed_user(pg_db)  # role 'user'
    post_id = _seed_post(pg_db, chu["id"])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.delete_post(post_id, user=ke_la))
    assert exc.value.status_code == 403
    assert _post_row(pg_db, post_id)["deleted_at"] is None


def test_delete_post_moderator_duoc_xoa(pg_db, stubs):
    chu = _seed_user(pg_db)
    mod = _seed_user(pg_db, role="moderator")
    post_id = _seed_post(pg_db, chu["id"])
    res = asyncio.run(community_api.delete_post(post_id, user=mod))
    assert res == {"success": True}
    assert _post_row(pg_db, post_id)["deleted_at"] is not None


def test_delete_post_khong_ton_tai_404(pg_db, stubs):
    user = _seed_user(pg_db)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.delete_post(str(uuid.uuid4()), user=user))
    assert exc.value.status_code == 404


# ══════════════════════════════════════════════════
#  update_post + helpers + edit history
# ══════════════════════════════════════════════════

def test_post_check_owner_cac_nhanh(pg_db):
    chu = _seed_user(pg_db)
    ke_la = _seed_user(pg_db)
    post_id = _seed_post(pg_db, chu["id"], post_type="review", rating=3)
    d = community_api._post_check_owner("%s", post_id, chu)
    assert d["post_type"] == "review"
    with pytest.raises(HTTPException) as exc:
        community_api._post_check_owner("%s", str(uuid.uuid4()), chu)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        community_api._post_check_owner("%s", post_id, ke_la)
    assert exc.value.status_code == 403


def test_validate_post_update_cac_nhanh():
    body = community_api.UpdatePost(rating=3)
    with pytest.raises(HTTPException) as exc:
        community_api._validate_post_update("ngắn", False, body)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        community_api._validate_post_update("d" * 5001, False, body)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        community_api._validate_post_update(None, False, body)
    assert exc.value.status_code == 400
    # hợp lệ: có nội dung đủ dài, không đổi sao
    community_api._validate_post_update("Nội dung mới đủ dài mười ký tự", False, body)


def test_update_post_noi_dung(pg_db, stubs):
    """Sửa nội dung: lịch sử giữ bản cũ, bài mang nội dung + hashtag mới."""
    chu = _seed_user(pg_db)
    post_id = _seed_post(pg_db, chu["id"], content="Nội dung ban đầu của bài viết")
    body = community_api.UpdatePost(content="Nội dung đã sửa nói về #bưởi da xanh")
    res = asyncio.run(community_api.update_post(post_id, body, user=chu))
    assert res["moderation_status"] == "approved"
    assert res["post"]["content"] == "Nội dung đã sửa nói về #bưởi da xanh"

    row = _post_row(pg_db, post_id)
    assert row["content"] == "Nội dung đã sửa nói về #bưởi da xanh"
    assert row["hashtags"] == ["bưởi"]
    with pg_db._conn() as conn:
        hist = pg_db._fetchall(
            conn,
            "SELECT editor_id::text AS eid, old_content, old_rating "
            "FROM post_edit_history WHERE post_id = %s::uuid",
            (post_id,),
        )
    hist = [pg_db._row_to_dict(h) for h in hist]
    assert len(hist) == 1
    assert hist[0]["old_content"] == "Nội dung ban đầu của bài viết"
    assert hist[0]["old_rating"] is None
    assert hist[0]["eid"] == chu["id"]


def test_update_post_chi_doi_sao_review(pg_db, stubs):
    """Review đổi sao không đổi lời: rating mới vào DB, nội dung giữ nguyên."""
    chu = _seed_user(pg_db)
    post_id = _seed_post(pg_db, chu["id"], post_type="review", rating=2,
                         content="Review ban đầu chấm hai sao")
    body = community_api.UpdatePost(rating=5)
    res = asyncio.run(community_api.update_post(post_id, body, user=chu))
    assert res["moderation_status"] is None
    row = _post_row(pg_db, post_id)
    assert row["rating"] == 5
    assert row["content"] == "Review ban đầu chấm hai sao"
    assert _count(
        pg_db,
        "SELECT COUNT(*) AS c FROM post_edit_history WHERE post_id = %s::uuid",
        (post_id,),
    ) == 1


def test_update_post_ca_noi_dung_lan_sao(pg_db, stubs):
    chu = _seed_user(pg_db)
    post_id = _seed_post(pg_db, chu["id"], post_type="review", rating=1,
                         content="Review cũ trước khi đổi cả hai")
    body = community_api.UpdatePost(content="Review mới sau khi quay lại lần hai", rating=4)
    res = asyncio.run(community_api.update_post(post_id, body, user=chu))
    assert res["post"]["rating"] == 4
    row = _post_row(pg_db, post_id)
    assert row["rating"] == 4
    assert row["content"] == "Review mới sau khi quay lại lần hai"


def test_update_post_khong_truong_nao_400(pg_db, stubs):
    """Không nội dung, không sao (hoặc sao trên bài share) → 400."""
    chu = _seed_user(pg_db)
    share_id = _seed_post(pg_db, chu["id"])  # post_type share
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.update_post(share_id, community_api.UpdatePost(), user=chu))
    assert exc.value.status_code == 400
    # share + rating: set_rating không kích hoạt vì bài không phải review
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            community_api.update_post(share_id, community_api.UpdatePost(rating=5), user=chu)
        )
    assert exc.value.status_code == 400


def test_update_post_khong_phai_chu_403(pg_db, stubs):
    chu = _seed_user(pg_db)
    ke_la = _seed_user(pg_db)
    post_id = _seed_post(pg_db, chu["id"])
    body = community_api.UpdatePost(content="Kẻ lạ cố sửa bài người khác")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.update_post(post_id, body, user=ke_la))
    assert exc.value.status_code == 403


def test_get_post_edit_history_sau_khi_sua(pg_db, stubs):
    """Lịch sử sửa bài công khai: bản cũ + người sửa, id/created_at là chuỗi."""
    chu = _seed_user(pg_db, display_name="Người Hay Sửa")
    post_id = _seed_post(pg_db, chu["id"], content="Bản đầu tiên của bài viết này")
    body = community_api.UpdatePost(content="Bản thứ hai sau một lần chỉnh")
    asyncio.run(community_api.update_post(post_id, body, user=chu))

    res = asyncio.run(community_api.get_post_edit_history(post_id, limit=20))
    assert res["total"] == 1
    edit = res["edits"][0]
    assert edit["old_content"] == "Bản đầu tiên của bài viết này"
    assert edit["display_name"] == "Người Hay Sửa"
    assert isinstance(edit["id"], str) and isinstance(edit["created_at"], str)


def test_get_post_edit_history_khong_ton_tai_404(pg_db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community_api.get_post_edit_history(str(uuid.uuid4()), limit=20))
    assert exc.value.status_code == 404
