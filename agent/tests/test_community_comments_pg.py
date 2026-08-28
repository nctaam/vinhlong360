# -*- coding: utf-8 -*-
"""Đặc tả hành vi HIỆN TẠI của miền BÌNH LUẬN + BÁO CÁO (community/api.py) trên PostgreSQL thật.

Phủ các handler/closure chưa từng chạy trên DB thật:
  - get_comments (+ closure _get_comments)
  - create_comment (+ _comment_guard/_comment_insert/_comment_query/_notify_comment/_notify_owner_comment)
  - edit_comment (+ _check/_update), delete_comment (+ _query)
  - report_comment (+ _check/_write), report_post (+ _query), report_user (+ _query)
  - appeal_post (+ _query), get_appeal_status (+ _query)
  - set_best_answer (+ _query)

Khuôn harness: adapter Database() trỏ PG test, monkeypatch "db" vào ĐÚNG module
thực thi (community.api). Mọi side-effect ngoài miền (notifications, moderation,
achievements, ratelimit) đều stub ghi-nhận-lời-gọi — không chạm module db khác.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import json
import os
import uuid
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

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

_TABLES = (
    "comments, posts, blocks, reports, moderation_appeals, "
    "notifications, user_mutes, users"
)


def _truncate_all() -> None:
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
    monkeypatch.setattr(community_api, "db", adapter)
    _truncate_all()
    try:
        yield adapter
    finally:
        _truncate_all()


@pytest.fixture
def stubs(monkeypatch):
    """Stub mọi side-effect ngoài miền, ghi nhận lời gọi để assert."""
    calls = SimpleNamespace(notifications=[], moderation_logs=[], achievements=[])

    async def _moderate(content, user_id=None, **_kw):
        return {"status": "approved"}

    monkeypatch.setattr(community_api, "moderate_content_enhanced", _moderate)
    monkeypatch.setattr(
        community_api, "log_moderation",
        lambda *args, **kwargs: calls.moderation_logs.append({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setattr(
        community_api, "create_notification",
        lambda *args, **kwargs: calls.notifications.append({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setattr(community_api, "check_rate", lambda *_a, **_k: None)
    monkeypatch.setattr(
        community_api, "_check_achievements_bg",
        lambda user_id: calls.achievements.append(str(user_id)),
    )
    return calls


# ── Seed helpers (mỗi test dữ liệu riêng, id/phone ngẫu nhiên) ──

def _seed_user(pg_db, role="user", display_name="Người dùng thử") -> dict:
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
    return {"id": user_id, "phone": phone, "display_name": display_name, "role": role}


def _seed_post(pg_db, owner_id, *, post_type="share", moderation_status="approved",
               content="Bài viết dùng cho kiểm thử bình luận") -> str:
    post_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO posts (id, user_id, content, post_type, moderation_status)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s)
            """,
            (post_id, owner_id, content, post_type, moderation_status),
        )
    return post_id


def _seed_comment(pg_db, post_id, user_id, *, content="Một bình luận",
                  parent_id=None, moderation_status="approved",
                  deleted=False, hours_old=0) -> str:
    comment_id = str(uuid.uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            f"""
            INSERT INTO comments (id, post_id, user_id, parent_id, content,
                                  moderation_status, created_at, deleted_at)
            VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, %s,
                    NOW() - make_interval(hours => %s),
                    {'NOW()' if deleted else 'NULL'})
            """,
            (comment_id, post_id, user_id, parent_id, content,
             moderation_status, hours_old),
        )
    return comment_id


def _fetch_one(pg_db, sql, params=()):
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(conn, sql, params)
    return pg_db._row_to_dict(row) if row else None


def _comment_row(pg_db, comment_id):
    return _fetch_one(
        pg_db,
        "SELECT * FROM comments WHERE id::text = %s",
        (comment_id,),
    )


def _post_row(pg_db, post_id):
    return _fetch_one(
        pg_db,
        "SELECT * FROM posts WHERE id::text = %s",
        (post_id,),
    )


def _run(coro):
    return asyncio.run(coro)


async def _await_and_drain(coro):
    """Chạy handler rồi chờ hết task nền (create_task) trong cùng event loop."""
    result = await coro
    current = asyncio.current_task()
    pending = [t for t in asyncio.all_tasks() if t is not current]
    if pending:
        await asyncio.gather(*pending)
    return result


def _fake_request():
    return SimpleNamespace(
        headers={}, client=SimpleNamespace(host="127.0.0.1"), cookies={}
    )


# ── get_comments ──

def test_get_comments_nests_replies_and_hides_pending_deleted(pg_db, stubs):
    """Closure _get_comments trên PG: top-level + reply lồng, ẩn pending/đã xoá."""
    owner = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    top_id = _seed_comment(pg_db, post_id, commenter["id"], content="Bình luận gốc")
    reply_id = _seed_comment(
        pg_db, post_id, owner["id"], content="Trả lời", parent_id=top_id
    )
    _seed_comment(pg_db, post_id, commenter["id"],
                  content="Đang chờ duyệt", moderation_status="pending")
    _seed_comment(pg_db, post_id, commenter["id"],
                  content="Đã bị xoá", deleted=True)

    result = _run(community_api.get_comments(
        post_id, _fake_request(), limit=100, offset=0, user=owner,
    ))

    comments = result["comments"]
    assert [c["id"] for c in comments] == [top_id]
    assert comments[0]["content"] == "Bình luận gốc"
    assert comments[0]["author"]["id"] == commenter["id"]
    assert [r["id"] for r in comments[0]["replies"]] == [reply_id]
    assert comments[0]["replies"][0]["parent_id"] == top_id


def test_get_comments_excludes_blocked_author(pg_db, stubs):
    """_block_sql áp lên c.user_id: bình luận của người mình chặn không hiện."""
    owner = _seed_user(pg_db)
    blocked = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    _seed_comment(pg_db, post_id, blocked["id"], content="Từ người bị chặn")
    kept_id = _seed_comment(pg_db, post_id, owner["id"], content="Bình luận của tôi")
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s::uuid, %s::uuid)",
            (owner["id"], blocked["id"]),
        )

    result = _run(community_api.get_comments(
        post_id, _fake_request(), limit=100, offset=0, user=owner,
    ))

    assert [c["id"] for c in result["comments"]] == [kept_id]


# ── create_comment ──

def test_create_comment_inserts_row_and_notifies_post_owner(pg_db, stubs):
    owner = _seed_user(pg_db, display_name="Chủ bài")
    commenter = _seed_user(pg_db, display_name="Người bình luận")
    post_id = _seed_post(pg_db, owner["id"])
    body = community_api.CreateComment(content="Bình luận đầu tiên vào bài")

    result = _run(community_api.create_comment(post_id, body, user=commenter))

    comment = result["comment"]
    row = _comment_row(pg_db, comment["id"])
    assert row is not None
    assert row["content"] == "Bình luận đầu tiên vào bài"
    assert row["moderation_status"] == "approved"
    assert str(row["user_id"]) == commenter["id"]
    assert row["parent_id"] is None
    # trigger trg_comment_count (migration 070) recount — không tăng tay
    assert _post_row(pg_db, post_id)["comment_count"] == 1
    # log_moderation được gọi với id bình luận vừa tạo
    assert stubs.moderation_logs[0]["args"][:3] == ("comment", comment["id"], "approved")
    # chủ bài được báo "comment"
    assert len(stubs.notifications) == 1
    notif = stubs.notifications[0]
    assert notif["args"][0] == owner["id"]
    assert notif["args"][1] == "comment"
    assert notif["kwargs"]["ref_id"] == post_id
    assert notif["kwargs"]["actor_id"] == commenter["id"]


def test_create_comment_reply_notifies_parent_author_too(pg_db, stubs):
    owner = _seed_user(pg_db)
    parent_author = _seed_user(pg_db)
    replier = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    parent_id = _seed_comment(pg_db, post_id, parent_author["id"])
    body = community_api.CreateComment(
        content="Trả lời bình luận gốc", parent_id=parent_id
    )

    result = _run(community_api.create_comment(post_id, body, user=replier))

    row = _comment_row(pg_db, result["comment"]["id"])
    assert str(row["parent_id"]) == parent_id
    kinds = {(n["args"][0], n["args"][1]) for n in stubs.notifications}
    assert (owner["id"], "comment") in kinds
    assert (parent_author["id"], "comment_reply") in kinds


def test_create_comment_on_question_notifies_question_answer(pg_db, stubs):
    owner = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"], post_type="question")
    body = community_api.CreateComment(content="Câu trả lời cho câu hỏi")

    _run(community_api.create_comment(post_id, body, user=commenter))

    assert [n["args"][1] for n in stubs.notifications] == ["question_answer"]
    assert stubs.notifications[0]["args"][0] == owner["id"]


def test_create_comment_missing_post_404(pg_db, stubs):
    commenter = _seed_user(pg_db)
    body = community_api.CreateComment(content="Bình luận vào hư vô")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.create_comment(str(uuid.uuid4()), body, user=commenter))
    assert exc.value.status_code == 404


def test_create_comment_blocked_by_post_author_403(pg_db, stubs):
    owner = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s::uuid, %s::uuid)",
            (owner["id"], commenter["id"]),
        )
    body = community_api.CreateComment(content="Bình luận khi bị chặn")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.create_comment(post_id, body, user=commenter))
    assert exc.value.status_code == 403
    assert not _fetch_one(
        pg_db, "SELECT 1 FROM comments WHERE post_id::text = %s", (post_id,)
    )


def test_create_comment_limit_reached_400(pg_db, stubs, monkeypatch):
    owner = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    _seed_comment(pg_db, post_id, owner["id"])
    monkeypatch.setattr(community_api._cfg, "MAX_COMMENTS_PER_POST", 1)
    body = community_api.CreateComment(content="Bình luận vượt giới hạn")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.create_comment(post_id, body, user=commenter))
    assert exc.value.status_code == 400


def test_create_comment_parent_of_other_post_400(pg_db, stubs):
    owner = _seed_user(pg_db)
    commenter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    other_post = _seed_post(pg_db, owner["id"])
    foreign_parent = _seed_comment(pg_db, other_post, owner["id"])
    body = community_api.CreateComment(
        content="Trả lời sai chỗ", parent_id=foreign_parent
    )

    with pytest.raises(HTTPException) as exc:
        _run(community_api.create_comment(post_id, body, user=commenter))
    assert exc.value.status_code == 400


# ── edit_comment ──

def test_edit_comment_owner_updates_content(pg_db, stubs):
    owner = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    comment_id = _seed_comment(pg_db, post_id, owner["id"], content="Bản gốc nè")
    body = community_api.EditComment(content="Nội dung đã được sửa lại")

    result = _run(community_api.edit_comment(comment_id, body, user=owner))

    assert result["comment"]["id"] == comment_id
    assert result["comment"]["content"] == "Nội dung đã được sửa lại"
    row = _comment_row(pg_db, comment_id)
    assert row["content"] == "Nội dung đã được sửa lại"
    assert row["moderation_status"] == "approved"


def test_edit_comment_of_other_user_403(pg_db, stubs):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    comment_id = _seed_comment(pg_db, post_id, owner["id"], content="Của chủ bài")
    body = community_api.EditComment(content="Kẻ lạ sửa trộm")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.edit_comment(comment_id, body, user=stranger))
    assert exc.value.status_code == 403
    assert _comment_row(pg_db, comment_id)["content"] == "Của chủ bài"


def test_edit_comment_missing_404(pg_db, stubs):
    user = _seed_user(pg_db)
    body = community_api.EditComment(content="Sửa cái không tồn tại")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.edit_comment(str(uuid.uuid4()), body, user=user))
    assert exc.value.status_code == 404


def test_edit_comment_outside_window_400(pg_db, stubs):
    owner = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    comment_id = _seed_comment(
        pg_db, post_id, owner["id"], content="Bình luận cũ", hours_old=48
    )
    body = community_api.EditComment(content="Sửa sau 48 giờ")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.edit_comment(comment_id, body, user=owner))
    assert exc.value.status_code == 400
    assert _comment_row(pg_db, comment_id)["content"] == "Bình luận cũ"


# ── delete_comment ──

def test_delete_comment_owner_soft_deletes_tree_and_notifications(pg_db, stubs):
    owner = _seed_user(pg_db)
    replier = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    comment_id = _seed_comment(pg_db, post_id, owner["id"])
    reply_id = _seed_comment(pg_db, post_id, replier["id"], parent_id=comment_id)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO notifications (user_id, type, title, ref_type, ref_id)
            VALUES (%s::uuid, 'comment', 'Tiêu đề', 'comment', %s)
            """,
            (owner["id"], comment_id),
        )

    result = _run(community_api.delete_comment(comment_id, user=owner))

    assert result == {"success": True}
    assert _comment_row(pg_db, comment_id)["deleted_at"] is not None
    # Soft-delete cả reply con (SP3 W6.1) — hàng vẫn còn, chỉ gắn deleted_at
    assert _comment_row(pg_db, reply_id)["deleted_at"] is not None
    assert not _fetch_one(
        pg_db,
        "SELECT 1 FROM notifications WHERE ref_type = 'comment' AND ref_id = %s",
        (comment_id,),
    )
    # trigger recount về 0 sau khi cả cây bị soft-delete
    assert _post_row(pg_db, post_id)["comment_count"] == 0


def test_delete_comment_by_stranger_403_but_moderator_allowed(pg_db, stubs):
    owner = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    moderator = _seed_user(pg_db, role="moderator")
    post_id = _seed_post(pg_db, owner["id"])
    comment_id = _seed_comment(pg_db, post_id, owner["id"])

    with pytest.raises(HTTPException) as exc:
        _run(community_api.delete_comment(comment_id, user=stranger))
    assert exc.value.status_code == 403
    assert _comment_row(pg_db, comment_id)["deleted_at"] is None

    result = _run(community_api.delete_comment(comment_id, user=moderator))
    assert result == {"success": True}
    assert _comment_row(pg_db, comment_id)["deleted_at"] is not None


def test_delete_comment_missing_404(pg_db, stubs):
    user = _seed_user(pg_db)
    with pytest.raises(HTTPException) as exc:
        _run(community_api.delete_comment(str(uuid.uuid4()), user=user))
    assert exc.value.status_code == 404


# ── report_comment (JSONL) ──

def test_report_comment_writes_jsonl_record(pg_db, stubs, monkeypatch, tmp_path):
    """Closure _check chạy PG thật; _write ghi JSONL — chuyển hướng __file__ sang
    thư mục tạm để không đụng agent/community/data/ thật."""
    owner = _seed_user(pg_db)
    reporter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    comment_id = _seed_comment(pg_db, post_id, owner["id"])
    monkeypatch.setattr(community_api, "__file__", str(tmp_path / "api.py"))

    body = community_api.ReportCommentBody(reason="spam", detail="Rác quảng cáo")
    result = _run(community_api.report_comment(
        comment_id, body, _fake_request(), user=reporter,
    ))
    assert result["success"] is True

    # lý do ngoài danh sách bị chuẩn hoá thành "other"
    body2 = community_api.ReportCommentBody(reason="ly-do-la", detail="")
    _run(community_api.report_comment(
        comment_id, body2, _fake_request(), user=reporter,
    ))

    lines = (tmp_path / "data" / "reports.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == 2
    assert records[0]["target_id"] == comment_id
    assert records[0]["target_type"] == "comment"
    assert records[0]["reason"] == "spam"
    assert records[0]["detail"] == "Rác quảng cáo"
    assert records[0]["reporter_id"] == reporter["id"]
    assert records[0]["status"] == "open"
    assert records[1]["reason"] == "other"


def test_report_comment_missing_404(pg_db, stubs):
    reporter = _seed_user(pg_db)
    body = community_api.ReportCommentBody(reason="spam")
    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_comment(
            str(uuid.uuid4()), body, _fake_request(), user=reporter,
        ))
    assert exc.value.status_code == 404


def test_report_comment_own_comment_400(pg_db, stubs):
    owner = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    comment_id = _seed_comment(pg_db, post_id, owner["id"])
    body = community_api.ReportCommentBody(reason="spam")
    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_comment(
            comment_id, body, _fake_request(), user=owner,
        ))
    assert exc.value.status_code == 400


# ── report_post (bảng reports PG) ──

def test_report_post_inserts_row_and_rejects_duplicate(pg_db, stubs):
    owner = _seed_user(pg_db)
    reporter = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    body = community_api.ReportPostBody(reason="harassment", detail="")

    result = _run(community_api.report_post(post_id, body, user=reporter))
    assert result["success"] is True
    row = _fetch_one(
        pg_db,
        """
        SELECT reporter_id, target_type, target_id, reason, status
        FROM reports WHERE target_id = %s
        """,
        (post_id,),
    )
    assert str(row["reporter_id"]) == reporter["id"]
    assert row["target_type"] == "post"
    assert row["reason"] == "harassment"
    assert row["status"] == "pending"

    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_post(post_id, body, user=reporter))
    assert exc.value.status_code == 400
    count = _fetch_one(
        pg_db, "SELECT COUNT(*) AS c FROM reports WHERE target_id = %s", (post_id,)
    )
    assert count["c"] == 1


def test_report_post_own_post_400_and_missing_404(pg_db, stubs):
    owner = _seed_user(pg_db)
    post_id = _seed_post(pg_db, owner["id"])
    body = community_api.ReportPostBody(reason="spam")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_post(post_id, body, user=owner))
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_post(str(uuid.uuid4()), body, user=owner))
    assert exc.value.status_code == 404


# ── report_user ──

def test_report_user_inserts_row_and_rejects_duplicate(pg_db, stubs):
    target = _seed_user(pg_db)
    reporter = _seed_user(pg_db)
    body = community_api.ReportUserBody(reason="impersonation")

    result = _run(community_api.report_user(target["id"], body, user=reporter))
    assert result["success"] is True
    row = _fetch_one(
        pg_db,
        "SELECT reporter_id, target_type, reason FROM reports WHERE target_id = %s",
        (target["id"],),
    )
    assert str(row["reporter_id"]) == reporter["id"]
    assert row["target_type"] == "user"
    assert row["reason"] == "impersonation"

    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_user(target["id"], body, user=reporter))
    assert exc.value.status_code == 400


def test_report_user_self_400_and_inactive_404(pg_db, stubs):
    reporter = _seed_user(pg_db)
    inactive = _seed_user(pg_db)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE users SET is_active = FALSE WHERE id::text = %s",
            (inactive["id"],),
        )
    body = community_api.ReportUserBody(reason="spam")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_user(reporter["id"], body, user=reporter))
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        _run(community_api.report_user(inactive["id"], body, user=reporter))
    assert exc.value.status_code == 404


# ── appeal_post / get_appeal_status ──

def test_appeal_post_author_of_rejected_post_creates_appeal(pg_db, stubs):
    author = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author["id"], moderation_status="rejected")
    body = community_api.AppealBody(reason="Bài của tôi không vi phạm quy định nào")

    result = _run(community_api.appeal_post(post_id, body, user=author))
    assert result["success"] is True
    row = _fetch_one(
        pg_db,
        "SELECT user_id, reason, status FROM moderation_appeals WHERE post_id::text = %s",
        (post_id,),
    )
    assert str(row["user_id"]) == author["id"]
    assert row["reason"] == "Bài của tôi không vi phạm quy định nào"
    assert row["status"] == "pending"

    # khiếu nại lần hai cùng bài → 409
    with pytest.raises(HTTPException) as exc:
        _run(community_api.appeal_post(post_id, body, user=author))
    assert exc.value.status_code == 409


def test_appeal_post_permission_and_state_branches(pg_db, stubs):
    author = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    rejected_id = _seed_post(pg_db, author["id"], moderation_status="rejected")
    approved_id = _seed_post(pg_db, author["id"], moderation_status="approved")
    body = community_api.AppealBody(reason="Lý do khiếu nại đủ mười ký tự")

    with pytest.raises(HTTPException) as exc:
        _run(community_api.appeal_post(rejected_id, body, user=stranger))
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        _run(community_api.appeal_post(approved_id, body, user=author))
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        _run(community_api.appeal_post(str(uuid.uuid4()), body, user=author))
    assert exc.value.status_code == 404


def test_get_appeal_status_none_then_existing(pg_db, stubs):
    author = _seed_user(pg_db)
    post_id = _seed_post(pg_db, author["id"], moderation_status="rejected")

    assert _run(community_api.get_appeal_status(post_id, user=author)) == {"appeal": None}

    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO moderation_appeals (post_id, user_id, reason)
            VALUES (%s::uuid, %s::uuid, %s)
            """,
            (post_id, author["id"], "Nội dung của tôi hợp lệ"),
        )

    result = _run(community_api.get_appeal_status(post_id, user=author))
    appeal = result["appeal"]
    assert appeal["status"] == "pending"
    assert appeal["reviewer_note"] is None
    assert appeal["reviewed_at"] is None
    assert appeal["created_at"]


# ── set_best_answer ──

def test_set_best_answer_sets_column_and_rewards_comment_author(pg_db, stubs):
    asker = _seed_user(pg_db)
    answerer = _seed_user(pg_db)
    post_id = _seed_post(pg_db, asker["id"], post_type="question")
    comment_id = _seed_comment(pg_db, post_id, answerer["id"])
    body = community_api.BestAnswerBody(comment_id=comment_id)

    result = _run(_await_and_drain(
        community_api.set_best_answer(post_id, body, user=asker)
    ))

    assert result == {"best_answer_id": comment_id}
    assert str(_post_row(pg_db, post_id)["best_answer_id"]) == comment_id
    # thành tích cộng cho TÁC GIẢ bình luận, không phải chủ bài
    assert stubs.achievements == [answerer["id"]]


def test_set_best_answer_unset_clears_column(pg_db, stubs):
    asker = _seed_user(pg_db)
    answerer = _seed_user(pg_db)
    post_id = _seed_post(pg_db, asker["id"], post_type="question")
    comment_id = _seed_comment(pg_db, post_id, answerer["id"])
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE posts SET best_answer_id = %s::uuid WHERE id::text = %s",
            (comment_id, post_id),
        )
    body = community_api.BestAnswerBody(comment_id=None)

    result = _run(_await_and_drain(
        community_api.set_best_answer(post_id, body, user=asker)
    ))

    assert result == {"best_answer_id": None}
    assert _post_row(pg_db, post_id)["best_answer_id"] is None
    assert stubs.achievements == []


def test_set_best_answer_permission_and_validation_branches(pg_db, stubs):
    asker = _seed_user(pg_db)
    stranger = _seed_user(pg_db)
    post_id = _seed_post(pg_db, asker["id"], post_type="question")
    other_post = _seed_post(pg_db, asker["id"], post_type="question")
    foreign_comment = _seed_comment(pg_db, other_post, stranger["id"])

    body = community_api.BestAnswerBody(comment_id=foreign_comment)
    with pytest.raises(HTTPException) as exc:
        _run(community_api.set_best_answer(post_id, body, user=stranger))
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        _run(community_api.set_best_answer(post_id, body, user=asker))
    assert exc.value.status_code == 400
    assert _post_row(pg_db, post_id)["best_answer_id"] is None

    with pytest.raises(HTTPException) as exc:
        _run(community_api.set_best_answer(str(uuid.uuid4()), body, user=asker))
    assert exc.value.status_code == 404
