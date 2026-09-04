# -*- coding: utf-8 -*-
"""Miền CỘNG ĐỒNG — mặt QUẢN TRỊ. Bóc khỏi `admin.py` (2026-08-29, lát 1 đợt cắt module; hồ sơ đo: journal wf_3f293d24-0a1, kết quả community-admin).

Gói miền cộng đồng theo khuôn `agent/cases/` và `agent/entities/`: mặt công khai
ở `community/api.py`, đây là 42 route quản trị UGC (kiểm duyệt post/comment,
qa-queue, review-response, appeals, reports, quản user + analytics/export user–post)
— 63 ký hiệu (42 handler + 11 helper + ADMIN_ROLE_RANKS + 9 model), bao đóng
bắc cầu, di chuyển NGUYÊN VĂN.

Mount qua `admin.router.include_router(...)` TRƯỚC `_fix_admin_route_order()`:
- cổng R20.9 chỉ nhìn thấy mount qua lời gọi include_router;
- router cha mang prefix "/admin" VÀ dependencies [require_admin, require_csrf]
  — router này KHÔNG tự mang cả hai, kế thừa từ cha khi include (kiểm bằng
  đo runtime trong test ranh giới, không tin trí nhớ API).
"""
from __future__ import annotations

import asyncio
import html as _html
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from admin_common import (
    _csv_row,
    _ensure_admin_scope,
    _log_mod_action,
    _mask,
    _require_admin_actor_id,
)
from auth_middleware import require_pg, validate_path_id
from database import db, escape_like as _escape_like  # alias như admin.py
from notifications import create_notification
from control_plane.concurrency import StateConflict, cas_transition, ensure_state_schema

logger = logging.getLogger("admin")   # giữ NGUYÊN kênh log admin
router = APIRouter(tags=["admin-community"])


ADMIN_ROLE_RANKS: dict[str, int] = {
    "user": 0,
    "moderator": 1,
    "admin": 2,
    "superadmin": 3,
}


def _assert_actor_can_manage_target(admin_user: dict | None, target_role: str | None) -> None:
    """Allow account control only when a session actor strictly outranks the target."""
    if admin_user is None:
        return
    actor_role = str(admin_user.get("role") or "")
    normalized_target = str(target_role or "")
    actor_rank = ADMIN_ROLE_RANKS.get(actor_role)
    target_rank = ADMIN_ROLE_RANKS.get(normalized_target)
    if actor_rank is None or target_rank is None or actor_rank <= target_rank:
        raise HTTPException(403, "Khong du quyen thao tac tai khoan nay")


# ── Q&A quality queue (U-24) ──


@router.get("/qa-queue",
            summary="List Q&A posts needing attention",
            description="Returns Q&A questions that are unanswered or lack a best answer. Supports filtering by status and entity.")
async def qa_queue(
    filter: Optional[str] = Query(None, pattern="^(unanswered|no_best_answer)$"),
    entity_id: Optional[str] = Query(None, max_length=100),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    """Admin queue: questions chưa có best answer hoặc chưa có reply."""
    require_pg()
    ph = db._ph
    def _query():
        conditions = ["p.post_type = 'question'", "p.moderation_status = 'approved'"]
        params: list = []
        if entity_id:
            conditions.append(f"p.entity_id::text = {ph}")
            params.append(entity_id)
        if filter == "unanswered":
            conditions.append("p.comment_count = 0")
        elif filter == "no_best_answer":
            conditions.append("p.best_answer_id IS NULL")
        where = " AND ".join(conditions)
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.content, p.entity_id, p.user_id,
                       p.comment_count, p.best_answer_id, p.created_at,
                       u.display_name
                FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE {where}
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts p WHERE {where}
            """, (*params,))
        total = db._row_to_dict(total_row)["c"] if total_row else 0
        return {
            "questions": [db._row_to_dict(r) for r in rows],
            "total": total,
            "filter": filter,
        }
    return await asyncio.to_thread(_query)


class SetBestAnswerBody(BaseModel):
    comment_id: str = Field(..., min_length=1, max_length=100)


@router.post("/qa-queue/{post_id}/set-best-answer",
             summary="Set best answer on Q&A post",
             description="Admin override to designate a comment as the best answer for a question post. Validates both the post and comment exist.")
async def qa_set_best_answer(post_id: str, body: SetBestAnswerBody):
    """Admin override: set best_answer_id cho 1 question."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT id, post_type FROM posts WHERE id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài hỏi không tồn tại")
            p = db._row_to_dict(post)
            if p.get("post_type") != "question":
                raise HTTPException(400, "Chỉ set best answer cho post_type=question")
            comment = db._fetchone(conn, f"""
                SELECT id FROM comments WHERE id::text = {ph} AND post_id::text = {ph}
            """, (body.comment_id, post_id))
            if not comment:
                raise HTTPException(404, "Comment không thuộc bài hỏi này")
            db._execute(conn, f"""
                UPDATE posts SET best_answer_id = {ph}::uuid WHERE id::text = {ph}
            """, (body.comment_id, post_id))
        return {"ok": True, "post_id": post_id, "best_answer_id": body.comment_id}
    return await asyncio.to_thread(_query)


# ── Review responses (U-11) ──


class ReviewResponseBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("/posts/{post_id}/response",
             summary="Respond to a review post",
             description="Creates an admin or business response to a review post. Only one response per review is allowed.")
async def admin_review_response(post_id: str, body: ReviewResponseBody, request: Request):
    """Admin/business reply to a review — one response per review (UNIQUE)."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    responder_id = _require_admin_actor_id(request)
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT user_id, post_type FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            pd = db._row_to_dict(post)
            if pd.get("post_type") != "review":
                raise HTTPException(400, "Chỉ phản hồi cho bài đánh giá (review)")
            db._execute(conn, f"SELECT pg_advisory_xact_lock(hashtext({ph}))", (f"review_resp:{post_id}",))
            existing = db._fetchone(conn, f"SELECT id FROM review_responses WHERE post_id::text = {ph}", (post_id,))
            if existing:
                raise HTTPException(409, "Bài đánh giá đã có phản hồi")
            db._execute(conn, f"""
                INSERT INTO review_responses (post_id, responder_id, content)
                VALUES ({ph}::uuid, {ph}::uuid, {ph})
            """, (post_id, responder_id, _html.escape(body.content.strip())))
            row = db._fetchone(conn, f"SELECT * FROM review_responses WHERE post_id::text = {ph}", (post_id,))
        _log_mod_action("review_response", post_id, "added")
        try:
            create_notification(str(pd["user_id"]), "social",
                                "Đánh giá của bạn đã nhận được phản hồi",
                                ref_type="post", ref_id=post_id)
        except Exception:
            logger.exception("Failed to notify review response %s", post_id)
        return db._row_to_dict(row) if row else {"ok": True}
    return await asyncio.to_thread(_query)


@router.get("/posts/{post_id}/response",
            summary="Get review response",
            description="Returns the admin response for a specific review post, if one exists.")
async def get_review_response(post_id: str):
    """Get the admin response for a review post."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT rr.*, u.display_name as responder_name
                FROM review_responses rr
                JOIN users u ON u.id = rr.responder_id
                WHERE rr.post_id::text = {ph}
            """, (post_id,))
        if not row:
            return None
        return db._row_to_dict(row)
    result = await asyncio.to_thread(_query)
    if not result:
        raise HTTPException(404, "Không tìm thấy phản hồi review")
    return result


@router.get("/user-engagement",
            summary="Get user engagement metrics",
            description="Returns engagement metrics over a configurable period: active posters, commenters, likers, retention rate, and daily active users.")
async def user_engagement_stats(days: int = Query(30, ge=1, le=365)):
    require_pg()
    ph = db._ph
    def _query():
        interval_param = f"{days} days"
        with db._conn() as conn:
            active_posters = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            active_commenters = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM comments
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            active_likers = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT user_id) as c FROM likes
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            new_users = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            retained = db._fetchone(conn, f"""
                SELECT COUNT(DISTINCT p.user_id) as c FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE p.created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND u.created_at < NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param, interval_param))
            total_users = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = TRUE", ())
            daily = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(DISTINCT user_id) as active_users
                FROM posts WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                GROUP BY DATE(created_at) ORDER BY day
            """, (interval_param,))
        tu = db._row_to_dict(total_users)["c"] if total_users else 1
        ap = db._row_to_dict(active_posters)["c"] if active_posters else 0
        return {
            "period_days": days,
            "total_active_users": tu,
            "active_posters": ap,
            "active_commenters": db._row_to_dict(active_commenters)["c"] if active_commenters else 0,
            "active_likers": db._row_to_dict(active_likers)["c"] if active_likers else 0,
            "new_users": db._row_to_dict(new_users)["c"] if new_users else 0,
            "retained_users": db._row_to_dict(retained)["c"] if retained else 0,
            "engagement_rate": round(ap / tu * 100, 1) if tu else 0,
            "daily_active": [{"day": str(db._row_to_dict(r)["day"]), "users": db._row_to_dict(r)["active_users"]} for r in daily],
        }
    return await asyncio.to_thread(_query)


@router.get("/user-growth",
            summary="Get user growth over time",
            description="Returns daily signup counts, total/deactivated user counts, and week-over-week growth rate.")
async def user_growth(days: int = Query(30, ge=7, le=365)):
    require_pg()
    ph = db._ph
    def _query():
        interval_param = f"{days} days"
        with db._conn() as conn:
            daily_reg = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(*) as signups
                FROM users
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                GROUP BY DATE(created_at) ORDER BY day
            """, (interval_param,))
            total = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = TRUE", ())
            deactivated = db._fetchone(conn, "SELECT COUNT(*) as c FROM users WHERE is_active = FALSE", ())
            week_ago = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM users WHERE created_at > NOW() - INTERVAL '7 days'
            """, ())
            prev_week = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM users
                WHERE created_at > NOW() - INTERVAL '14 days'
                  AND created_at <= NOW() - INTERVAL '7 days'
            """, ())
        t = db._row_to_dict(total)["c"] if total else 0
        d = db._row_to_dict(deactivated)["c"] if deactivated else 0
        w = db._row_to_dict(week_ago)["c"] if week_ago else 0
        pw = db._row_to_dict(prev_week)["c"] if prev_week else 0
        growth_rate = round((w - pw) / pw * 100, 1) if pw > 0 else 0
        return {
            "total_users": t,
            "active_users": t,
            "deactivated_users": d,
            "signups_this_week": w,
            "signups_prev_week": pw,
            "growth_rate_pct": growth_rate,
            "daily_signups": [{"day": str(db._row_to_dict(r)["day"]), "signups": db._row_to_dict(r)["signups"]} for r in daily_reg],
        }
    return await asyncio.to_thread(_query)


@router.get("/export/users",
            summary="Export user data as CSV",
            description="Exports all users with stats (post count, follower count, reputation) as a downloadable CSV file. Phone numbers are masked.")
async def export_users_csv():
    """CSV export of all users with stats."""
    require_pg()

    def _generate():
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT u.id, u.phone, u.display_name, u.role, u.is_active,
                       u.reputation, u.created_at,
                       COALESCE(pc.post_count, 0) AS post_count,
                       COALESCE(fc.follower_count, 0) AS follower_count
                FROM users u
                LEFT JOIN (
                    SELECT user_id, COUNT(*) AS post_count FROM posts
                    WHERE moderation_status != 'rejected'
                    GROUP BY user_id
                ) pc ON pc.user_id = u.id
                LEFT JOIN (
                    SELECT target_id, COUNT(*) AS follower_count FROM follows
                    WHERE target_type = 'user'
                    GROUP BY target_id
                ) fc ON fc.target_id = u.id::text
                ORDER BY u.created_at DESC
                LIMIT 50000
            """, ())
        yield _csv_row([
            "id", "phone", "display_name", "role", "is_active", "reputation",
            "created_at", "post_count", "follower_count",
        ])
        for r in rows:
            d = db._row_to_dict(r)
            phone = _mask(d.get("phone") or "")
            yield _csv_row([
                d["id"], phone, d.get("display_name") or "", d.get("role", "user"),
                d.get("is_active", True), d.get("reputation", 0), d.get("created_at", ""),
                d["post_count"], d["follower_count"],
            ])

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=users.csv"})


@router.get("/export/posts",
            summary="Export post data as CSV",
            description="Exports posts with author and entity info as a downloadable CSV. Supports filtering by moderation status and date range.")
async def export_posts_csv(
    status: str = Query("all", max_length=20),
    days: int = Query(90, ge=1, le=365),
):
    """CSV export of posts with author/entity info."""
    require_pg()
    ph = db._ph

    def _generate():
        where_parts = []
        params = []
        if status != "all":
            where_parts.append(f"p.moderation_status = {ph}")
            params.append(status)
        where_parts.append(f"p.created_at > NOW() - CAST({ph} AS INTERVAL)")
        params.append(f"{days} days")
        where_clause = " AND ".join(where_parts) if where_parts else "TRUE"
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.user_id, p.post_type, p.rating,
                       p.like_count, p.comment_count, p.share_count,
                       p.moderation_status, p.entity_id, p.created_at,
                       u.display_name AS author_name
                FROM posts p
                LEFT JOIN users u ON u.id = p.user_id
                WHERE {where_clause}
                ORDER BY p.created_at DESC
                LIMIT 50000
            """, tuple(params))
        yield _csv_row([
            "id", "user_id", "author_name", "post_type", "rating", "like_count",
            "comment_count", "share_count", "status", "entity_id", "created_at",
        ])
        for r in rows:
            d = db._row_to_dict(r)
            yield _csv_row([
                d["id"], d.get("user_id", ""), d.get("author_name") or "",
                d.get("post_type", ""), d.get("rating", ""), d.get("like_count", 0),
                d.get("comment_count", 0), d.get("share_count", 0),
                d.get("moderation_status", ""), d.get("entity_id", ""), d.get("created_at", ""),
            ])

    return StreamingResponse(_generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=posts.csv"})


# ═══════════════════════════════════════════════════════
# Moderation & Community Admin
# ═══════════════════════════════════════════════════════


@router.get("/moderation/queue",
            summary="Get moderation queue",
            description="Returns posts pending moderation review. Supports filtering by status and pagination.")
async def moderation_queue(
    status: str = Query("review", pattern="^(review|pending|flagged|approved|rejected)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    require_pg()
    ph = db._ph
    offset = (page - 1) * limit
    statuses = ["pending", "flagged"] if status == "review" else [status]
    placeholders = ", ".join([ph] * len(statuses))
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.*, u.display_name,
                       e.name as entity_name
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.moderation_status IN ({placeholders})
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*statuses, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ({placeholders})
            """, (*statuses,))
        return {
            "posts": [_mod_post(db._row_to_dict(r)) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }
    return await asyncio.to_thread(_query)


def _moderate_post(post_id: str, new_status: str, actor_id: str, reason: str | None = None):
    """Run one moderation decision as a status+revision CAS."""
    ph = db._ph
    with db._conn() as conn:
        class _Tx:
            _db = db
            _conn = conn
        ensure_state_schema(_Tx, "posts")
        id_expr = "id::text" if getattr(db, "_use_pg", False) else "id"
        row = db._fetchone(conn, f"SELECT id, user_id, moderation_status FROM posts WHERE {id_expr} = {ph}", (post_id,))
        if not row:
            raise HTTPException(404, "Bài viết không tồn tại")
        current = db._row_to_dict(row)
        if current.get("moderation_status") not in {"pending", "flagged"}:
            raise StateConflict()
        cas_transition(_Tx, "posts", post_id, expected_status=current["moderation_status"], new_status=new_status,
                       actor_id=actor_id, reason=reason or new_status, correlation_id=f"moderation:{post_id}")
    return str(current["user_id"])


def _decide_appeal(appeal_id: str, target_status: str, admin_id: str, note: str):
    """CAS the appeal and, on approval, CAS the rejected post restoration."""
    ph = db._ph
    with db._conn() as conn:
        class _Tx:
            _db = db
            _conn = conn
        ensure_state_schema(_Tx, "moderation_appeals")
        row = db._fetchone(conn, f"SELECT id, post_id, user_id, status FROM moderation_appeals WHERE id::text = {ph}", (appeal_id,))
        if not row:
            raise HTTPException(404, "Khiếu nại không tồn tại")
        data = db._row_to_dict(row)
        if data.get("status") != "pending":
            raise StateConflict()
        cas_transition(_Tx, "moderation_appeals", appeal_id, expected_status="pending", new_status=target_status,
                       actor_id=admin_id, reason=note or target_status, correlation_id=f"appeal:{appeal_id}")
        if target_status == "approved":
            post_expr = "id::text" if getattr(db, "_use_pg", False) else "id"
            post = db._fetchone(conn, f"SELECT moderation_status FROM posts WHERE {post_expr}={ph}", (str(data["post_id"]),))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            post_status = db._row_to_dict(post).get("moderation_status")
            if post_status not in {"rejected", "flagged"}:
                raise StateConflict()
            cas_transition(_Tx, "posts", str(data["post_id"]), expected_status=post_status, new_status="approved",
                           actor_id=admin_id, reason=note or "appeal_approved", correlation_id=f"appeal:{appeal_id}")
        # Keep reviewer metadata coupled to the winning appeal CAS.
        db._execute(conn, f"UPDATE moderation_appeals SET reviewer_note={ph}, reviewer_id={ph}::uuid, reviewed_at=NOW() WHERE id::text={ph}", (note or None, admin_id, appeal_id))
        return str(data["post_id"]), str(data["user_id"])


@router.post("/moderation/{post_id}/approve",
             summary="Approve moderated post",
             description="Approves a post pending moderation and notifies the author.")
async def approve_post(post_id: str, request: Request = None):
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    actor_id = str((getattr(request.state, "admin_user", None) or {}).get("id")) if request else "admin"
    def _query():
        return _moderate_post(post_id, "approved", actor_id)
    author_id = await asyncio.to_thread(_query)
    _log_mod_action("post", post_id, "approved")
    try:
        create_notification(author_id, "moderation",
                            "Bài viết của bạn đã được duyệt",
                            ref_type="post", ref_id=post_id)
    except Exception:
        logger.exception("Failed to notify post approval %s", post_id)
    return {"success": True}


class RejectBody(BaseModel):
    reason: str | None = Field(None, max_length=500)


@router.post("/moderation/{post_id}/reject",
             summary="Reject moderated post",
             description="Rejects a post pending moderation with an optional reason. Notifies the author.")
async def reject_post(post_id: str, body: RejectBody = RejectBody(), request: Request = None):
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    reason = (body.reason or "").strip() or None
    actor_id = str((getattr(request.state, "admin_user", None) or {}).get("id")) if request else "admin"
    author_id = await asyncio.to_thread(_moderate_post, post_id, "rejected", actor_id, reason)
    _log_mod_action("post", post_id, "rejected", reason)
    try:
        notif_body = f"Lý do: {reason}" if reason else None
        create_notification(author_id, "moderation",
                            "Bài viết của bạn đã bị từ chối",
                            body=notif_body,
                            ref_type="post", ref_id=post_id)
    except Exception:
        logger.exception("Failed to notify post rejection %s", post_id)
    return {"success": True}


class BatchModerationBody(BaseModel):
    post_ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., max_length=20)  # 'approve' or 'reject'
    reason: str = Field("", max_length=500)


def _batch_mod_notify(rows, status, reason) -> None:
    """Notify each affected post author of the batch moderation result."""
    if status == "approved":
        title = "Bài viết của bạn đã được duyệt"
        notif_body = None
    else:
        title = "Bài viết của bạn đã bị từ chối"
        notif_body = f"Lý do: {reason}" if reason else None
    for r in rows:
        rd = db._row_to_dict(r)
        try:
            create_notification(str(rd["user_id"]), "moderation", title,
                                body=notif_body,
                                ref_type="post", ref_id=str(rd["id"]))
        except Exception:
            logger.exception("Failed to notify batch moderation %s", rd["id"])


@router.post("/moderation/batch",
             summary="Batch moderate multiple posts",
             description="Approve or reject multiple posts at once. Notifies each author and logs moderation actions.")
async def batch_moderation(body: BatchModerationBody, request: Request):
    require_pg()
    from ratelimit import check_rate
    admin_user = getattr(request.state, "admin_user", None)
    rl_key = f"admin:batch-mod:{admin_user['id']}" if admin_user else "admin:batch-mod:key"
    check_rate(rl_key, 10, 60, "Thao tác quá nhanh")
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")
    if body.action == "reject" and not body.reason.strip():
        raise HTTPException(400, "reason is required when rejecting posts")
    if not body.post_ids or len(body.post_ids) > 100:
        raise HTTPException(400, "post_ids: 1-100 items")
    status = "approved" if body.action == "approve" else "rejected"
    reason = body.reason.strip() or None
    def _query():
        rows = []
        ph = db._ph
        with db._conn() as conn:
            class _Tx:
                _db = db
                _conn = conn
            ensure_state_schema(_Tx, "posts")
            id_expr = "id::text" if getattr(db, "_use_pg", False) else "id"
            for pid in body.post_ids:
                existing = db._fetchone(conn, f"SELECT id, user_id, moderation_status FROM posts WHERE {id_expr}={ph}", (pid,))
                if not existing:
                    continue
                current = db._row_to_dict(existing)
                if current.get("moderation_status") not in {"pending", "flagged"}:
                    continue
                try:
                    cas_transition(_Tx, "posts", pid, expected_status=current["moderation_status"], new_status=status,
                                   actor_id="batch", reason=reason or status, correlation_id=f"moderation:{pid}")
                except StateConflict:
                    continue
                rows.append(existing)
            updated = len(rows)
        for row in rows:
            pid = str(db._row_to_dict(row)["id"])
            _log_mod_action("post", pid, status, reason)
        _batch_mod_notify(rows, status, reason)
        return updated
    updated = await asyncio.to_thread(_query)
    return {"success": True, "updated": updated, "requested": len(body.post_ids)}


@router.get("/moderation/{post_id}/history",
            summary="Get post moderation history",
            description="Returns the full moderation action timeline for a specific post, including moderator names and scores.")
async def moderation_history(post_id: str):
    """Admin: view full moderation action timeline for a specific post."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT id, moderation_status, created_at FROM posts WHERE id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            rows = db._fetchall(conn, f"""
                SELECT ml.action, ml.reason, ml.auto, ml.scores, ml.created_at,
                       u.display_name AS moderator_name
                FROM moderation_log ml
                LEFT JOIN users u ON u.id = ml.moderator_id
                WHERE ml.target_type = 'post' AND ml.target_id = {ph}
                ORDER BY ml.created_at DESC
                LIMIT 50
            """, (post_id,))
        pd = db._row_to_dict(post)
        actions = []
        for r in rows:
            d = db._row_to_dict(r)
            scores = d.get("scores")
            if isinstance(scores, str):
                try:
                    scores = json.loads(scores)
                except (json.JSONDecodeError, ValueError, TypeError):
                    scores = {}
            actions.append({
                "action": d["action"],
                "reason": d.get("reason"),
                "auto": bool(d.get("auto")),
                "moderator": d.get("moderator_name"),
                "scores": scores or {},
                "created_at": str(d.get("created_at", "")),
            })
        return {
            "post_id": post_id,
            "current_status": pd.get("moderation_status"),
            "post_created_at": str(pd.get("created_at", "")),
            "actions": actions,
            "total": len(actions),
        }
    return await asyncio.to_thread(_query)


@router.post("/posts/{post_id}/feature",
             summary="Toggle post featured status",
             description="Toggles whether a post is featured at the top of its entity page. Logs the action.")
async def feature_post(post_id: str, request: Request):
    """Admin: toggle feature a post at the top of its entity page."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    admin_id = _require_admin_actor_id(request)

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id, entity_id, is_featured FROM posts WHERE id::text = {ph}", (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            rd = db._row_to_dict(row)
            if not rd.get("entity_id"):
                raise HTTPException(400, "Bài viết không thuộc entity nào")
            if rd.get("is_featured"):
                db._execute(conn, f"""
                    UPDATE posts SET is_featured = FALSE, featured_by = NULL, featured_at = NULL
                    WHERE id::text = {ph}
                """, (post_id,))
                return False
            db._execute(conn, f"""
                UPDATE posts SET is_featured = TRUE, featured_by = {ph}::uuid, featured_at = NOW()
                WHERE id::text = {ph}
            """, (admin_id, post_id))
            return True

    featured = await asyncio.to_thread(_query)
    _log_mod_action("post", post_id, "featured" if featured else "unfeatured", None)
    return {"featured": featured}



@router.delete("/posts/{post_id}/response",
               summary="Delete admin response",
               description="Deletes the admin review response for a post. Logs the deletion.")
async def delete_review_response(post_id: str):
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM review_responses WHERE post_id::text = {ph} RETURNING id
            """, (post_id,))
            if not row:
                raise HTTPException(404, "Không có phản hồi để xoá")
    await asyncio.to_thread(_query)
    _log_mod_action("review_response", post_id, "deleted")
    return {"success": True}


class ModNoteBody(BaseModel):
    note: str = Field(..., min_length=1, max_length=500)


@router.post("/moderation/{post_id}/note",
             summary="Add moderation note",
             description="Adds an internal admin note to a post. Notes are not visible to the post author.")
async def add_moderation_note(post_id: str, body: ModNoteBody):
    """B3d: Add internal admin note (not visible to poster)."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT id FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            db._execute(conn, f"""
                UPDATE posts SET moderation_notes = COALESCE(moderation_notes, '[]'::jsonb) || {ph}::jsonb
                WHERE id::text = {ph}
            """, (json.dumps({"text": body.note, "at": datetime.now(timezone.utc).isoformat()}), post_id))
    await asyncio.to_thread(_query)
    _log_mod_action("post", post_id, "note_added")
    return {"success": True}


@router.get("/moderation/{post_id}/notes",
            summary="Get moderation notes",
            description="Returns all internal admin notes for a specific post.")
async def get_moderation_notes(post_id: str):
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT moderation_notes FROM posts WHERE id::text = {ph}", (post_id,))
        if not row:
            raise HTTPException(404, "Bài viết không tồn tại")
        notes = db._row_to_dict(row).get("moderation_notes") or []
        return {"notes": notes}
    return await asyncio.to_thread(_query)


@router.get("/moderation/stats",
            summary="Get moderation statistics",
            description="Returns post counts grouped by moderation status, plus totals for today and this week.")
async def moderation_stats():
    require_pg()
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, """
                SELECT moderation_status, COUNT(*) as c FROM posts GROUP BY moderation_status
            """, ())
            today = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - INTERVAL '24 hours'
            """, ())
            week = db._fetchone(conn, """
                SELECT COUNT(*) as c FROM posts WHERE created_at > NOW() - INTERVAL '7 days'
            """, ())
        return {
            "counts": {db._row_to_dict(row)["moderation_status"]: db._row_to_dict(row)["c"] for row in rows},
            "today": db._row_to_dict(today)["c"] if today else 0,
            "week": db._row_to_dict(week)["c"] if week else 0,
        }
    return await asyncio.to_thread(_query)


# ── Admin Content Search ──────────────────────────────────────────────────

@router.get("/content/search",
            summary="Search across all content",
            description="Admin keyword search across posts and comments. Supports filtering by content type, moderation status, and post type.")
async def admin_content_search(
    q: str = Query(..., min_length=1, max_length=200),
    content_type: str = Query("post", pattern="^(post|comment|all)$"),
    status: str = Query("all", pattern="^(all|approved|pending|rejected|flagged)$"),
    post_type: str = Query(None, pattern="^(review|question|tip|photo|general)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    """Admin search across posts and comments by keyword."""
    require_pg()
    ph = db._ph
    offset = (page - 1) * limit
    search_esc = _escape_like(q)

    def _query():
        results = []
        total = 0
        with db._conn() as conn:
            if content_type in ("post", "all"):
                # `posts` has no title column — content is the only searchable text.
                conditions = [f"p.content ILIKE {ph} ESCAPE '\\'"]
                params = [f"%{search_esc}%"]
                if status != "all":
                    conditions.append(f"p.moderation_status = {ph}")
                    params.append(status)
                if post_type:
                    conditions.append(f"p.post_type = {ph}")
                    params.append(post_type)
                where = " AND ".join(conditions)
                post_rows = db._fetchall(conn, f"""
                    SELECT p.id, p.content, p.post_type, p.moderation_status,
                           p.entity_id, p.created_at, p.like_count,
                           u.display_name as author_name
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE {where}
                    ORDER BY p.created_at DESC
                    LIMIT {ph} OFFSET {ph}
                """, tuple(params + [limit, offset]))
                post_count = db._fetchone(conn, f"SELECT COUNT(*) as c FROM posts p WHERE {where}", tuple(params))
                for r in post_rows:
                    d = db._row_to_dict(r)
                    d["_type"] = "post"
                    if d.get("content"):
                        d["content"] = d["content"][:300]
                    results.append(d)
                total += db._row_to_dict(post_count)["c"] if post_count else 0

            if content_type in ("comment", "all"):
                c_conditions = [f"c.content ILIKE {ph} ESCAPE '\\'"]
                c_params = [f"%{search_esc}%"]
                c_where = " AND ".join(c_conditions)
                comment_rows = db._fetchall(conn, f"""
                    SELECT c.id, c.content, c.post_id, c.created_at,
                           u.display_name as author_name
                    FROM comments c JOIN users u ON u.id = c.user_id
                    WHERE {c_where}
                    ORDER BY c.created_at DESC
                    LIMIT {ph} OFFSET {ph}
                """, tuple(c_params + [limit, offset]))
                comment_count = db._fetchone(conn, f"SELECT COUNT(*) as c FROM comments c WHERE {c_where}", tuple(c_params))
                for r in comment_rows:
                    d = db._row_to_dict(r)
                    d["_type"] = "comment"
                    if d.get("content"):
                        d["content"] = d["content"][:300]
                    results.append(d)
                total += db._row_to_dict(comment_count)["c"] if comment_count else 0
        return {"results": results, "total": total, "query": q, "page": page}

    return await asyncio.to_thread(_query)


# ── Admin Post Detail ────────────────────────────────────────────────────

@router.get("/posts/{post_id}",
            summary="Get post details (admin view)",
            description="Returns full post details including comments, author info, and moderation data for admin review.")
async def admin_post_detail(post_id: str):
    """Full post detail with comments for admin review."""
    require_pg()
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"""
                SELECT p.*, u.display_name as author_name, u.phone as author_phone,
                       u.avatar_url as author_avatar, u.role as author_role
                FROM posts p JOIN users u ON u.id = p.user_id
                WHERE p.id::text = {ph}
            """, (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            pd = db._row_to_dict(post)
            pd["author_phone"] = _mask(pd.get("author_phone", ""))

            comments = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.created_at, c.parent_id,
                       u.display_name as author_name, u.id as user_id
                FROM comments c JOIN users u ON u.id = c.user_id
                WHERE c.post_id::text = {ph}
                ORDER BY c.created_at ASC
                LIMIT 100
            """, (post_id,))

            likes = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM likes WHERE post_id::text = {ph}
            """, (post_id,))

            reports = db._fetchall(conn, f"""
                SELECT r.id, r.reason, r.created_at, u.display_name as reporter_name
                FROM reports r JOIN users u ON u.id = r.reporter_id
                WHERE r.target_type = 'post' AND r.target_id = {ph}
                ORDER BY r.created_at DESC
            """, (post_id,))

        pd["comments"] = [db._row_to_dict(c) for c in comments]
        pd["comment_count"] = len(pd["comments"])
        pd["like_count_verified"] = db._row_to_dict(likes)["c"] if likes else 0
        pd["reports"] = [db._row_to_dict(r) for r in reports]
        pd["report_count"] = len(pd["reports"])
        return pd

    return await asyncio.to_thread(_query)


# ── Appeal management (NĐ147 compliance) ──

@router.get("/appeals",
            summary="List user appeals",
            description="Returns a paginated list of user appeals against moderation decisions. Supports filtering by status.")
async def list_appeals(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    require_pg()
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            where = "" if status == "all" else f"WHERE a.status = {ph}"
            params = [] if status == "all" else [status]
            rows = db._fetchall(conn, f"""
                SELECT a.*, u.display_name, u.username,
                       p.content AS post_content, p.post_type
                FROM moderation_appeals a
                JOIN users u ON u.id = a.user_id
                JOIN posts p ON p.id = a.post_id
                {where}
                ORDER BY a.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (*params, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM moderation_appeals a {where}
            """, tuple(params))
        return {
            "appeals": [{
                "id": str(db._row_to_dict(r)["id"]),
                "post_id": str(db._row_to_dict(r)["post_id"]),
                "post_content": db._row_to_dict(r).get("post_content", "")[:200],
                "post_type": db._row_to_dict(r).get("post_type"),
                "user": {"display_name": db._row_to_dict(r).get("display_name"),
                         "username": db._row_to_dict(r).get("username")},
                "reason": db._row_to_dict(r).get("reason"),
                "status": db._row_to_dict(r)["status"],
                "reviewer_note": db._row_to_dict(r).get("reviewer_note"),
                "reviewed_at": str(db._row_to_dict(r)["reviewed_at"]) if db._row_to_dict(r).get("reviewed_at") else None,
                "created_at": str(db._row_to_dict(r)["created_at"]),
            } for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }
    return await asyncio.to_thread(_query)


class AppealDecisionBody(BaseModel):
    note: str = Field("", max_length=500)


@router.post("/appeals/{appeal_id}/approve",
              summary="Approve a user appeal",
              description="Approves a moderation appeal, restoring the post and notifying the user.")
async def approve_appeal(appeal_id: str, body: AppealDecisionBody = AppealDecisionBody(), request: Request = None):
    require_pg()
    appeal_id = validate_path_id(appeal_id, "appeal_id")
    admin_id = _require_admin_actor_id(request)
    note = body.note.strip()
    post_id, user_id = await asyncio.to_thread(_decide_appeal, appeal_id, "approved", admin_id, note)
    _log_mod_action("appeal", appeal_id, "approved", note or None)
    try:
        create_notification(user_id, "moderation",
                            "Khiếu nại được chấp nhận — bài viết đã được duyệt lại",
                            ref_type="post", ref_id=post_id)
    except Exception:
        logger.exception("Failed to notify appeal approval %s", appeal_id)
    return {"success": True}


@router.post("/appeals/{appeal_id}/reject",
              summary="Reject a user appeal",
              description="Rejects a moderation appeal and notifies the user with an optional reason.")
async def reject_appeal(appeal_id: str, body: AppealDecisionBody = AppealDecisionBody(), request: Request = None):
    require_pg()
    appeal_id = validate_path_id(appeal_id, "appeal_id")
    admin_id = _require_admin_actor_id(request)
    note = body.note.strip()
    # _decide_appeal writes reviewer_id atomically with the CAS.
    post_id, user_id = await asyncio.to_thread(_decide_appeal, appeal_id, "rejected", admin_id, note)
    _log_mod_action("appeal", appeal_id, "rejected", note or None)
    try:
        note_msg = f" Lý do: {note}" if note else ""
        create_notification(user_id, "moderation",
                            f"Khiếu nại không được chấp nhận.{note_msg}",
                            ref_type="post", ref_id=post_id)
    except Exception:
        logger.exception("Failed to notify appeal rejection %s", appeal_id)
    return {"success": True}


# ── Admin Comment List ────────────────────────────────────────────────────

@router.get("/comments",
            summary="List comments for admin review",
            description="Returns a paginated list of comments with optional search and post filter.")
async def admin_list_comments(
    search: str = Query("", max_length=200),
    post_id: str = Query(None, max_length=50),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    """List comments for admin review with optional search and post filter."""
    ph = db._ph
    offset = (page - 1) * limit

    def _query():
        conditions = []
        params = []
        if search:
            search_esc = _escape_like(search)
            conditions.append(f"c.content ILIKE {ph} ESCAPE '\\'")
            params.append(f"%{search_esc}%")
        if post_id:
            conditions.append(f"c.post_id::text = {ph}")
            params.append(post_id)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_params = list(params)
        params.extend([limit, offset])
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT c.id, c.content, c.post_id, c.parent_id, c.created_at,
                       u.display_name as author_name, u.id as user_id,
                       p.post_type
                FROM comments c
                JOIN users u ON u.id = c.user_id
                JOIN posts p ON p.id = c.post_id
                {where}
                ORDER BY c.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params))
            total = db._fetchone(conn, f"SELECT COUNT(*) as c FROM comments c {where}", tuple(count_params))
        return {
            "comments": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page,
        }

    return await asyncio.to_thread(_query)


@router.delete("/comments/{comment_id}",
               summary="Delete a comment",
               description="Force-deletes a comment by ID and recalculates the parent post comment count.")
async def admin_delete_comment(comment_id: str, request: Request):
    """Admin force-delete a comment."""
    comment_id = validate_path_id(comment_id, "comment_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM comments WHERE id::text = {ph}
                RETURNING id, post_id, user_id
            """, (comment_id,))
            if not row:
                raise HTTPException(404, "Bình luận không tồn tại")
            rd = db._row_to_dict(row)
            db._execute(conn, f"""
                UPDATE posts
                SET comment_count = (
                    SELECT COUNT(*) FROM comments WHERE post_id = {ph}::uuid
                )
                WHERE id = {ph}::uuid
            """, (str(rd["post_id"]), str(rd["post_id"])))
        _log_mod_action("comment", comment_id, "deleted")
        return rd

    result = await asyncio.to_thread(_query)
    return {"success": True, "deleted_comment": str(result["id"])}


@router.get("/content-stats",
            summary="Get content statistics",
            description="Returns content statistics including posts by type/status, average ratings, and daily post counts for a given period.")
async def content_stats(days: int = Query(30, ge=1, le=365)):
    require_pg()
    ph = db._ph
    def _query():
        interval_param = f"{days} days"
        with db._conn() as conn:
            by_type = db._fetchall(conn, f"""
                SELECT post_type, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND moderation_status = 'approved'
                GROUP BY post_type ORDER BY cnt DESC
            """, (interval_param,))
            by_status = db._fetchall(conn, f"""
                SELECT moderation_status, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                GROUP BY moderation_status ORDER BY cnt DESC
            """, (interval_param,))
            avg_rating = db._fetchone(conn, f"""
                SELECT AVG(rating) as avg_r, COUNT(*) as cnt
                FROM posts
                WHERE post_type = 'review' AND rating IS NOT NULL
                  AND created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND moderation_status = 'approved'
            """, (interval_param,))
            total_comments = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM comments
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
            """, (interval_param,))
            daily_posts = db._fetchall(conn, f"""
                SELECT DATE(created_at) as day, COUNT(*) as cnt
                FROM posts
                WHERE created_at > NOW() - CAST({ph} AS INTERVAL)
                  AND moderation_status = 'approved'
                GROUP BY DATE(created_at) ORDER BY day
            """, (interval_param,))
        ar = db._row_to_dict(avg_rating) if avg_rating else {}
        return {
            "period_days": days,
            "posts_by_type": {db._row_to_dict(r)["post_type"]: db._row_to_dict(r)["cnt"] for r in by_type},
            "posts_by_status": {db._row_to_dict(r)["moderation_status"]: db._row_to_dict(r)["cnt"] for r in by_status},
            "avg_review_rating": round(float(ar["avg_r"]), 2) if ar.get("avg_r") else None,
            "total_reviews_with_rating": ar.get("cnt", 0),
            "total_comments": db._row_to_dict(total_comments)["c"] if total_comments else 0,
            "daily_posts": [{"day": str(db._row_to_dict(r)["day"]), "count": db._row_to_dict(r)["cnt"]} for r in daily_posts],
        }
    return await asyncio.to_thread(_query)


@router.get("/reports",
            summary="List user reports",
            description="Returns a paginated list of user reports with filtering by status, target type, reporter, and target user.")
async def get_reports(
    status: str = Query("pending", pattern="^(all|pending|resolved|dismissed)$"),
    target_type: str = Query(None, pattern="^(post|comment|user|entity)$"),
    reporter_id: str = Query(None, max_length=64),
    target_user_id: str = Query(None, max_length=64),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=500),
):
    require_pg()
    if reporter_id:
        reporter_id = validate_path_id(reporter_id, "reporter_id")
    if target_user_id:
        target_user_id = validate_path_id(target_user_id, "target_user_id")
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            conditions = []
            params = []
            if status != "all":
                conditions.append(f"r.status = {ph}")
                params.append(status)
            if target_type:
                conditions.append(f"r.target_type = {ph}")
                params.append(target_type)
            if reporter_id:
                conditions.append(f"r.reporter_id::text = {ph}")
                params.append(reporter_id)
            if target_user_id:
                conditions.append("r.target_type = 'user'")
                conditions.append(f"r.target_id = {ph}")
                params.append(target_user_id)
            where = " AND ".join(conditions) if conditions else "1=1"
            params.extend([limit, offset])
            rows = db._fetchall(conn, f"""
                SELECT r.id, r.target_type, r.target_id, r.reason, to_jsonb(r)->>'details' AS details,
                       r.reporter_id, r.status, r.created_at, u.display_name as reporter_name
                FROM reports r
                LEFT JOIN users u ON u.id = r.reporter_id
                WHERE {where}
                ORDER BY r.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports r WHERE {where}
            """, tuple(params[:-2]))
        return {
            "reports": [db._row_to_dict(r) for r in rows],
            "total": db._row_to_dict(total)["c"] if total else 0,
        }
    return await asyncio.to_thread(_query)


class BulkReportAction(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(resolve|dismiss)$")


@router.post("/reports/bulk",
              summary="Bulk action on reports",
              description="Applies a resolve or dismiss action to multiple reports at once.")
async def bulk_report_action(body: BulkReportAction):
    status = "resolved" if body.action == "resolve" else "dismissed"
    def _query():
        ph = db._ph
        placeholders = ",".join([ph] * len(body.ids))
        with db._conn() as conn:
            cur = db._execute(conn, f"UPDATE reports SET status = {ph} WHERE id::text IN ({placeholders})",
                              (status, *body.ids))
            return cur.rowcount
    updated = await asyncio.to_thread(_query)
    for rid in body.ids:
        _log_mod_action("report", rid, status)
    return {"success": True, "updated": updated, "requested": len(body.ids)}


@router.post("/reports/{report_id}/resolve",
              summary="Resolve a report",
              description="Marks a user report as resolved after admin review.")
async def resolve_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                UPDATE reports SET status = 'resolved' WHERE id::text = {ph}
            """, (report_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Báo cáo không tồn tại")
    await asyncio.to_thread(_query)
    _log_mod_action("report", report_id, "resolved")
    return {"success": True}


@router.post("/reports/{report_id}/dismiss",
              summary="Dismiss a report",
              description="Marks a user report as dismissed, indicating no action is needed.")
async def dismiss_report(report_id: str):
    report_id = validate_path_id(report_id, "report_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cur = db._execute(conn, f"""
                UPDATE reports SET status = 'dismissed' WHERE id::text = {ph}
            """, (report_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Báo cáo không tồn tại")
    await asyncio.to_thread(_query)
    _log_mod_action("report", report_id, "dismissed")
    return {"success": True}


def _list_users_where(ph, search, role_filter):
    """Build the users WHERE clause + params for the admin list, honoring search/role filters."""
    conditions = ["1=1"]
    params = []
    if search:
        search_esc = _escape_like(search)
        conditions.append(f"(display_name ILIKE {ph} ESCAPE '\\' OR phone LIKE {ph} ESCAPE '\\')")
        params.extend([f"%{search_esc}%", f"%{search_esc}%"])
    if role_filter:
        conditions.append(f"COALESCE(role, 'user') = {ph}")
        params.append(role_filter)
    return " AND ".join(conditions), params


def _list_users_role_counts() -> dict:
    role_counts = {}
    try:
        with db._conn() as conn2:
            rc_rows = db._fetchall(conn2, "SELECT COALESCE(role, 'user') as role, COUNT(*) as c FROM users GROUP BY COALESCE(role, 'user')", ())
        for rc in rc_rows:
            d = db._row_to_dict(rc)
            role_counts[d["role"]] = d["c"]
    except Exception:
        logger.debug("Role counts query failed", exc_info=True)
    return role_counts


@router.get("/users",
            summary="List all users",
            description="Returns a paginated list of users with post counts. Supports search by name or phone, and filtering by role.")
async def list_users(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    role_filter: Optional[str] = Query(None, pattern="^(user|moderator|admin)$"),
    q: Optional[str] = Query(None, max_length=100),
    offset: Optional[int] = Query(None, ge=0, le=100000),
):
    require_pg()
    ph = db._ph
    if q and not search:
        search = q
    actual_offset = offset if offset is not None else (page - 1) * limit
    where, params = _list_users_where(ph, search, role_filter)
    count_params = list(params)
    params.extend([limit, actual_offset])
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT u.id, u.phone, u.display_name, u.role, u.is_active, u.created_at,
                       (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.moderation_status = 'approved') as post_count
                FROM users u WHERE {where}
                ORDER BY u.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, params)
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM users WHERE {where}
            """, count_params)
        role_counts = _list_users_role_counts()
        return {
            "users": [{
                "id": str(r["id"]),
                "phone": _mask(r.get("phone", "")),
                "display_name": r.get("display_name", ""),
                "role": r.get("role", "user"),
                "is_active": r.get("is_active", True),
                "created_at": str(r.get("created_at", "")),
                "post_count": r.get("post_count", 0),
            } for r in [db._row_to_dict(row) for row in rows]],
            "total": db._row_to_dict(total)["c"] if total else 0,
            "page": page if offset is None else (actual_offset // limit) + 1,
            "limit": limit,
            "role_counts": role_counts,
        }
    return await asyncio.to_thread(_query)


@router.get("/users/{user_id}",
            summary="Get user details",
            description="Returns comprehensive user profile and activity statistics for the admin panel, including post counts, follow stats, reports, blocks, and reputation.")
async def admin_user_detail(user_id: str):
    """Comprehensive user detail for admin panel."""
    require_pg()
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            user = db._fetchone(conn, f"""
                SELECT id, phone, display_name, avatar_url, cover_url, bio,
                       username, role, is_active, created_at
                FROM users WHERE id::text = {ph}
            """, (user_id,))
            if not user:
                raise HTTPException(404, "Người dùng không tồn tại")
            ud = db._row_to_dict(user)
            ud["phone"] = _mask(ud.get("phone", ""))

            post_stats = db._fetchone(conn, f"""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE moderation_status = 'approved') as approved,
                       COUNT(*) FILTER (WHERE moderation_status = 'rejected') as rejected,
                       COUNT(*) FILTER (WHERE moderation_status = 'pending') as pending,
                       COUNT(*) FILTER (WHERE post_type = 'review') as reviews,
                       COUNT(*) FILTER (WHERE post_type = 'question') as questions
                FROM posts WHERE user_id::text = {ph}
            """, (user_id,))
            ps = db._row_to_dict(post_stats) if post_stats else {}

            comment_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM comments WHERE user_id::text = {ph}
            """, (user_id,))

            follow_stats = db._fetchone(conn, f"""
                SELECT
                    (SELECT COUNT(*) FROM follows WHERE follower_id::text = {ph} AND target_type = 'user') as following,
                    (SELECT COUNT(*) FROM follows WHERE target_id = {ph} AND target_type = 'user') as followers
            """, (user_id, user_id))
            fs = db._row_to_dict(follow_stats) if follow_stats else {}

            session_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM user_sessions WHERE user_id = {ph}::uuid
            """, (user_id,))

            report_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports WHERE reporter_id::text = {ph}
            """, (user_id,))

            reported_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM reports WHERE target_type = 'user' AND target_id = {ph}
            """, (user_id,))

            block_count = db._fetchone(conn, f"""
                SELECT
                    (SELECT COUNT(*) FROM blocks WHERE blocker_id::text = {ph}) as blocking,
                    (SELECT COUNT(*) FROM blocks WHERE blocked_id::text = {ph}) as blocked_by
            """, (user_id, user_id))
            blk = db._row_to_dict(block_count) if block_count else {}

            mute_count = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM user_mutes WHERE user_id::text = {ph}
            """, (user_id,))

            reputation = db._fetchone(conn, f"""
                SELECT reputation_score FROM users WHERE id::text = {ph}
            """, (user_id,))
            rep = db._row_to_dict(reputation).get("reputation_score", 0) if reputation else 0

            last_login = _admin_user_last_login(conn, ph, user_id)

            last_post = db._fetchone(conn, f"""
                SELECT created_at FROM posts
                WHERE user_id::text = {ph} AND moderation_status = 'approved'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))

        stats = _admin_user_detail_stats(
            ps, comment_count, fs, session_count, report_count, reported_count,
            blk, mute_count, rep, last_login, last_post)
        return {"user": ud, "stats": stats}

    return await asyncio.to_thread(_query)


def _admin_user_last_login(conn, ph, user_id):
    last_login = None
    try:
        ll = db._fetchone(conn, f"""
            SELECT created_at FROM login_history
            WHERE user_id = {ph}::uuid AND success = TRUE
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        if ll:
            last_login = str(db._row_to_dict(ll)["created_at"])
    except Exception:
        logger.debug("login_history query failed for user %s", user_id, exc_info=True)
    return last_login


def _admin_user_detail_stats(ps, comment_count, fs, session_count, report_count,
                             reported_count, blk, mute_count, rep, last_login, last_post):
    return {
        "posts": ps,
        "comments": db._row_to_dict(comment_count)["c"] if comment_count else 0,
        "following": fs.get("following", 0),
        "followers": fs.get("followers", 0),
        "active_sessions": db._row_to_dict(session_count)["c"] if session_count else 0,
        "reports_filed": db._row_to_dict(report_count)["c"] if report_count else 0,
        "reports_against": db._row_to_dict(reported_count)["c"] if reported_count else 0,
        "blocking": blk.get("blocking", 0),
        "blocked_by": blk.get("blocked_by", 0),
        "muted_users": db._row_to_dict(mute_count)["c"] if mute_count else 0,
        "reputation_score": rep,
        "last_login": last_login,
        "last_post_at": str(db._row_to_dict(last_post)["created_at"]) if last_post else None,
    }


@router.post("/users/{user_id}/ban",
             summary="Ban a user",
             description="Deactivate a user account and revoke all active sessions. Admins cannot ban themselves.")
async def ban_user(user_id: str, request: Request):
    require_pg()
    user_id = validate_path_id(user_id, "user_id")
    # require_admin already populated the request-scoped actor.
    admin_user = getattr(request.state, "admin_user", None)
    if admin_user and str(admin_user.get("id")) == user_id:
        raise HTTPException(400, "Không thể tự ban chính mình")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"""
                SELECT id, is_active, role FROM users
                WHERE id::text = {ph} FOR UPDATE
            """, (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            target_data = db._row_to_dict(target)
            _assert_actor_can_manage_target(admin_user, target_data.get("role"))
            db._execute(conn, f"""
                UPDATE users SET is_active = FALSE WHERE id::text = {ph}
            """, (user_id,))
            db._execute(conn, f"""
                DELETE FROM user_sessions WHERE user_id = {ph}::uuid
            """, (user_id,))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, "ban")
    return {"success": True}


@router.post("/users/{user_id}/unban",
             summary="Unban a user",
             description="Reactivate a previously banned user account. Returns an error if the user is not currently banned.")
async def unban_user(user_id: str):
    require_pg()
    user_id = validate_path_id(user_id, "user_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            td = db._row_to_dict(target)
            if td["is_active"]:
                raise HTTPException(400, "Người dùng không bị ban")
            db._execute(conn, f"""
                UPDATE users SET is_active = TRUE WHERE id::text = {ph}
            """, (user_id,))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, "unban")
    return {"success": True}


class BulkUserAction(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=50)
    reason: str = Field("", max_length=500)


@router.post("/users/bulk-ban",
             summary="Bulk ban users",
             description="Ban multiple users at once. Accepts a list of user IDs and an optional reason; skips non-existent users.")
async def bulk_ban_users(body: BulkUserAction, request: Request):
    # Parameterized SQL (db._ph) and session revocation (DELETE FROM user_sessions)
    # are kept in _bulk_ban_query so this endpoint remains orchestration-only.
    require_pg()
    from ratelimit import check_rate
    check_rate("admin:bulk-ban", 5, 60, "Thao tác quá nhanh")
    admin_user = getattr(request.state, "admin_user", None)
    admin_id = str(admin_user.get("id")) if admin_user else None
    ids = list(dict.fromkeys(validate_path_id(uid, "user_id") for uid in body.user_ids))
    if admin_id and admin_id in ids:
        raise HTTPException(400, "Không thể tự ban chính mình")
    banned = await asyncio.to_thread(_bulk_ban_query, ids, admin_user)
    for uid in banned:
        _log_mod_action("user", uid, "ban", body.reason or None)
    return {"success": True, "banned_count": len(banned), "banned_ids": banned}


def _bulk_ban_query(ids: list[str], admin_user) -> list[str]:
    ph = db._ph
    targets: dict[str, dict] = {}
    with db._conn() as conn:
        for uid in sorted(ids):
            row = db._fetchone(conn, f"""
                SELECT id, is_active, role FROM users
                WHERE id::text = {ph} FOR UPDATE
            """, (uid,))
            if row:
                targets[uid] = db._row_to_dict(row)
        for uid in ids:
            target = targets.get(uid)
            if target:
                _assert_actor_can_manage_target(admin_user, target.get("role"))
        return _apply_bulk_bans(conn, ids, targets, ph)


def _apply_bulk_bans(conn, ids: list[str], targets: dict[str, dict], ph: str) -> list[str]:
    banned: list[str] = []
    for uid in ids:
        if uid not in targets:
            continue
        db._execute(conn, f"UPDATE users SET is_active = FALSE WHERE id::text = {ph}", (uid,))
        db._execute(conn, f"DELETE FROM user_sessions WHERE user_id = {ph}::uuid", (uid,))
        banned.append(uid)
    return banned


@router.post("/users/bulk-unban",
             summary="Bulk unban users",
             description="Unban multiple users at once. Accepts a list of user IDs and an optional reason; skips non-existent or active users.")
async def bulk_unban_users(body: BulkUserAction):
    require_pg()
    from ratelimit import check_rate
    check_rate("admin:bulk-unban", 5, 60, "Thao tác quá nhanh")
    ids = [validate_path_id(uid, "user_id") for uid in body.user_ids]
    def _query():
        ph = db._ph
        unbanned = []
        with db._conn() as conn:
            for uid in ids:
                target = db._fetchone(conn, f"SELECT is_active FROM users WHERE id::text = {ph}", (uid,))
                if not target:
                    continue
                td = db._row_to_dict(target)
                if td["is_active"]:
                    continue
                db._execute(conn, f"UPDATE users SET is_active = TRUE WHERE id::text = {ph}", (uid,))
                unbanned.append(uid)
        return unbanned
    unbanned = await asyncio.to_thread(_query)
    for uid in unbanned:
        _log_mod_action("user", uid, "unban", body.reason or None)
    return {"success": True, "unbanned_count": len(unbanned), "unbanned_ids": unbanned}


def _assert_role_change_allowed(admin_user, admin_role, role, target_role) -> None:
    """Privilege-boundary guard: only superadmin/admin-key may grant/change the admin role."""
    if admin_user and admin_role != "superadmin":
        if role == "admin" and target_role != "admin":
            raise HTTPException(403, "Chỉ superadmin hoặc admin key mới được cấp quyền admin")
        if target_role == "admin" and role != "admin":
            raise HTTPException(403, "Chỉ superadmin hoặc admin key mới được đổi quyền admin khác")


def _assert_not_last_admin(conn, ph, user_id, role, target_role) -> None:
    """Prevent demoting the last remaining active admin."""
    if target_role == "admin" and role != "admin":
        remaining = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM users
            WHERE COALESCE(role, 'user') = 'admin'
              AND is_active = TRUE
              AND id::text <> {ph}
        """, (user_id,))
        remaining_count = db._row_to_dict(remaining)["c"] if remaining else 0
        if remaining_count <= 0:
            raise HTTPException(400, "Không thể hạ quyền admin cuối cùng")


@router.post("/users/{user_id}/role",
             summary="Set user role",
             description="Assign a role (user, moderator, or admin) to a user. Banned users cannot be assigned roles.")
async def set_user_role(request: Request, user_id: str, role: str = Query(..., pattern="^(user|moderator|admin)$")):
    require_pg()
    _ensure_admin_scope(request, "security.admin")
    user_id = validate_path_id(user_id, "user_id")
    admin_user = getattr(request.state, "admin_user", None)
    if admin_user and str(admin_user.get("id")) == user_id:
        raise HTTPException(400, "Không thể tự đổi role chính mình")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"SELECT id, is_active, role FROM users WHERE id::text = {ph}", (user_id,))
            if not target:
                raise HTTPException(404, "Không tìm thấy người dùng")
            td = db._row_to_dict(target)
            if not td["is_active"]:
                raise HTTPException(400, "Không thể gán quyền cho tài khoản đã bị ban")
            target_role = td.get("role") or "user"
            admin_role = (admin_user or {}).get("role") if admin_user else "admin-key"
            _assert_role_change_allowed(admin_user, admin_role, role, target_role)
            _assert_not_last_admin(conn, ph, user_id, role, target_role)
            db._execute(conn, f"""
                UPDATE users SET role = {ph} WHERE id::text = {ph}
            """, (role, user_id))
    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, f"set_role:{role}")
    return {"success": True}


class AdminUserNote(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


@router.post("/users/{user_id}/notes", status_code=201,
             summary="Add admin note to user",
             description="Create an internal admin note attached to a user profile. Notes are only visible to admins.")
async def add_user_note(user_id: str, body: AdminUserNote, request: Request):
    """Admin: add internal note to a user profile."""
    user_id = validate_path_id(user_id, "user_id")
    admin_id = _require_admin_actor_id(request)

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT id FROM users WHERE id::text = {ph}", (user_id,))
            if not row:
                raise HTTPException(404, "Người dùng không tồn tại")
            note = db._fetchone(conn, f"""
                INSERT INTO admin_user_notes (user_id, admin_id, content)
                VALUES ({ph}::uuid, {ph}::uuid, {ph}) RETURNING id, created_at
            """, (user_id, admin_id, body.content.strip()))
            return db._row_to_dict(note)

    result = await asyncio.to_thread(_query)
    return {"note": {"id": str(result["id"]), "created_at": str(result["created_at"])}}


@router.get("/users/{user_id}/notes",
            summary="List admin notes for user",
            description="Retrieve all internal admin notes for a user, ordered by most recent first.")
async def get_user_notes(user_id: str, limit: int = Query(50, ge=1, le=200)):
    """Admin: list internal notes for a user."""
    user_id = validate_path_id(user_id, "user_id")

    def _query():
        ph = db._ph
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT n.id, n.content, n.created_at, u.display_name as admin_name
                FROM admin_user_notes n JOIN users u ON u.id = n.admin_id
                WHERE n.user_id = {ph}::uuid ORDER BY n.created_at DESC LIMIT {ph}
            """, (user_id, limit))

    rows = await asyncio.to_thread(_query)
    notes = []
    for r in rows:
        d = db._row_to_dict(r)
        notes.append({"id": str(d["id"]), "content": d["content"],
                       "admin_name": d.get("admin_name"), "created_at": str(d["created_at"])})
    return {"notes": notes}


@router.delete("/users/{user_id}/notes/{note_id}",
               summary="Delete admin note",
               description="Delete a specific internal admin note from a user profile.")
async def delete_user_note(user_id: str, note_id: str):
    """Admin: delete an internal note."""
    user_id = validate_path_id(user_id, "user_id")
    note_id = validate_path_id(note_id, "note_id")

    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"DELETE FROM admin_user_notes WHERE id = {ph}::uuid AND user_id = {ph}::uuid RETURNING 1",
                               (note_id, user_id))
            if not row:
                raise HTTPException(404, "Ghi chú không tồn tại")

    await asyncio.to_thread(_query)
    return {"success": True}


# ── Admin: user mutes + reactions visibility ────────────────────────

@router.get("/users/{user_id}/mutes",
            summary="Get user mute list",
            description="List all users muted by a specific user, with display names and timestamps.")
async def admin_user_mutes(user_id: str, limit: int = Query(50, ge=1, le=200)):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT m.muted_id, u.display_name, u.username, m.created_at
                FROM user_mutes m JOIN users u ON u.id = m.muted_id
                WHERE m.user_id = {ph}::uuid
                ORDER BY m.created_at DESC LIMIT {ph}
            """, (user_id, limit))
            return [db._row_to_dict(r) for r in rows]
    mutes = await asyncio.to_thread(_query)
    return {"mutes": [{"muted_id": str(m["muted_id"]), "display_name": m.get("display_name"),
                        "username": m.get("username"), "created_at": str(m["created_at"])} for m in mutes],
            "total": len(mutes)}


@router.get("/users/{user_id}/reactions",
            summary="Get user reaction history",
            description="Retrieve a summary of reaction types and recent reactions made by a user.")
async def admin_user_reactions(user_id: str, limit: int = Query(100, ge=1, le=500)):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT r.reaction_type, COUNT(*) as count
                FROM post_reactions r WHERE r.user_id = {ph}::uuid
                GROUP BY r.reaction_type
            """, (user_id,))
            summary = {db._row_to_dict(r)["reaction_type"]: int(db._row_to_dict(r)["count"]) for r in rows}
            recent = db._fetchall(conn, f"""
                SELECT r.post_id, r.reaction_type, r.created_at, p.content
                FROM post_reactions r LEFT JOIN posts p ON p.id = r.post_id
                WHERE r.user_id = {ph}::uuid
                ORDER BY r.created_at DESC LIMIT {ph}
            """, (user_id, limit))
            return summary, [db._row_to_dict(r) for r in recent]
    summary, recent = await asyncio.to_thread(_query)
    return {"summary": summary, "total": sum(summary.values()),
            "recent": [{"post_id": str(r["post_id"]), "reaction_type": r["reaction_type"],
                        "created_at": str(r["created_at"]),
                        "content_preview": (r.get("content") or "")[:100]} for r in recent]}


def _mod_post(row: dict) -> dict:
    images = row.get("images", [])
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except Exception:
            images = []
    return {
        "id": str(row["id"]),
        "content": row.get("content", "")[:2000],
        "post_type": row.get("post_type", "share"),
        "moderation_status": row.get("moderation_status", "pending"),
        "images": images,
        "author": row.get("display_name", ""),
        "display_name": row.get("display_name", ""),
        "phone": _mask(row.get("phone", "")),
        "entity_name": row.get("entity_name"),
        "created_at": str(row.get("created_at", "")),
        "moderation_notes": row.get("moderation_notes") or [],
    }
