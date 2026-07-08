"""
vinhlong360 — Notifications + Community Features.

Endpoints:
  GET    /api/notifications            — list notifications (polling)
  GET    /api/notifications/stream     — SSE real-time stream
  POST   /api/notifications/read-all   — mark all as read
  DELETE /api/notifications/{id}       — delete single notification
  POST   /api/follow/{type}/{id}       — toggle follow user/entity
  GET    /api/following                — list follows
  POST   /api/report                   — report content
  POST   /api/block/{user_id}          — toggle block user
"""

import asyncio
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from auth_middleware import get_current_user, require_user, validate_path_id, require_csrf
from database import db
from ratelimit import check_rate


from auth_middleware import require_pg as _require_pg

router = APIRouter(prefix="/api", tags=["community"], dependencies=[Depends(_require_pg)])


# ── Models ──

class ReportRequest(BaseModel):
    target_type: str = Field(..., max_length=20)
    target_id: str = Field(..., max_length=128)
    reason: str = Field(..., max_length=500)

    @field_validator("target_type")
    @classmethod
    def validate_type(cls, v):
        if v not in ("post", "comment", "user", "entity"):
            raise ValueError("Loại báo cáo: post, comment, user")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v):
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Lý do cần ít nhất 5 ký tự")
        if len(v) > 500:
            raise ValueError("Lý do tối đa 500 ký tự")
        return v


# ── Notifications ──

@router.get("/notifications",
            summary="List notifications",
            description="Returns paginated notifications for the authenticated user, grouped by type. Includes unread count.")
async def get_notifications(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10000),
    user=Depends(require_user),
):
    ph = db._ph
    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, type, title, body, ref_type, ref_id, is_read, created_at
                FROM notifications
                WHERE user_id = {ph}::uuid
                ORDER BY created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (str(user["id"]), limit, offset))
            unread = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM notifications
                WHERE user_id = {ph}::uuid AND is_read = FALSE
            """, (str(user["id"]),))
        return rows, unread
    rows, unread = await asyncio.to_thread(_query)

    raw = [_format_notif(db._row_to_dict(r)) for r in rows]
    grouped = _group_notifications(raw)
    return {
        "notifications": grouped,
        "unread_count": db._row_to_dict(unread)["c"] if unread else 0,
    }


@router.get("/notifications/unread-count",
            summary="Get unread notification count",
            description="Returns the total number of unread notifications for the authenticated user.")
async def unread_count(user=Depends(require_user)):
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM notifications
                WHERE user_id = {ph}::uuid AND is_read = FALSE
            """, (str(user["id"]),))
        return db._row_to_dict(row)["c"] if row else 0
    count = await asyncio.to_thread(_query)
    return {"unread_count": count}


@router.post("/notifications/read-all",
             summary="Mark all notifications as read",
             description="Marks every unread notification as read for the authenticated user.")
async def mark_all_read(user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"notif-read:{user['id']}", 30, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE notifications SET is_read = TRUE
                WHERE user_id = {ph}::uuid AND is_read = FALSE
            """, (str(user["id"]),))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.post("/notifications/{notif_id}/read",
             summary="Mark single notification as read",
             description="Marks a specific notification as read. Only the notification owner can perform this action.")
async def mark_notification_read(notif_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"notif-read:{user['id']}", 60, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    notif_id = validate_path_id(notif_id, "notif_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE notifications SET is_read = TRUE
                WHERE id::text = {ph} AND user_id = {ph}::uuid
            """, (notif_id, str(user["id"])))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.delete("/notifications/{notif_id}",
               summary="Delete a notification",
               description="Permanently deletes a single notification by ID. Only the notification owner can delete it.")
async def delete_notification(notif_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"notif-del:{user['id']}", 30, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    notif_id = validate_path_id(notif_id, "notif_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                DELETE FROM notifications
                WHERE id::text = {ph} AND user_id = {ph}::uuid
            """, (notif_id, str(user["id"])))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.delete("/notifications",
               summary="Clear all notifications",
               description="Deletes all notifications for the authenticated user. Returns the count of deleted notifications.")
async def clear_all_notifications(user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"notif-clear:{user['id']}", 3, 60, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            result = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM notifications
                WHERE user_id = {ph}::uuid
            """, (str(user["id"]),))
            db._execute(conn, f"""
                DELETE FROM notifications
                WHERE user_id = {ph}::uuid
            """, (str(user["id"]),))
            return db._row_to_dict(result)["c"] if result else 0
    deleted = await asyncio.to_thread(_query)
    return {"success": True, "deleted": deleted}


# ── Notification Preferences ──

class NotifPrefsUpdate(BaseModel):
    pref_like: Optional[bool] = None
    pref_comment: Optional[bool] = None
    pref_mention: Optional[bool] = None
    pref_follow: Optional[bool] = None
    pref_system: Optional[bool] = None


@router.get("/notification-preferences",
            summary="Get notification preferences",
            description="Returns the user's notification preference flags for each notification type (like, comment, mention, follow, system).")
async def get_notification_preferences(user=Depends(require_user)):
    ph = db._ph
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            return db._fetchone(conn, f"""
                SELECT pref_like, pref_comment, pref_mention, pref_follow, pref_system
                FROM notification_preferences WHERE user_id = {ph}::uuid
            """, (uid,))
    row = await asyncio.to_thread(_query)
    if row:
        d = db._row_to_dict(row)
        return {k: bool(d[k]) for k in ("pref_like", "pref_comment", "pref_mention", "pref_follow", "pref_system")}
    return {"pref_like": True, "pref_comment": True, "pref_mention": True, "pref_follow": True, "pref_system": True}


@router.put("/notification-preferences",
            summary="Update notification preferences",
            description="Updates one or more notification preference flags. Only provided fields are changed; omitted fields keep their current value.")
async def update_notification_preferences(body: NotifPrefsUpdate, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"notif-prefs:{user['id']}", 10, 600, "Cập nhật cài đặt quá nhanh. Vui lòng thử lại sau.")
    ph = db._ph
    uid = str(user["id"])
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Không có gì để cập nhật")
    set_parts = [f"{k} = {ph}" for k in updates]
    set_parts.append("updated_at = NOW()")
    vals = list(updates.values())
    vals.append(uid)
    def _query():
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO notification_preferences (user_id) VALUES ({ph}::uuid)
                ON CONFLICT (user_id) DO NOTHING
            """, (uid,))
            db._execute(conn, f"""
                UPDATE notification_preferences SET {', '.join(set_parts)}
                WHERE user_id = {ph}::uuid
            """, vals)
    await asyncio.to_thread(_query)
    return {"success": True}


_sse_subscribers: dict[str, list[asyncio.Queue]] = {}
_sse_lock = asyncio.Lock()
_sse_thread_lock = __import__("threading").Lock()
_SSE_MAX_PER_USER = 5
_sse_loop: asyncio.AbstractEventLoop | None = None


def _notify_sse(user_id: str, data: dict):
    with _sse_thread_lock:
        queues = list(_sse_subscribers.get(user_id, []))
    loop = _sse_loop
    for q in queues:
        try:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(q.put_nowait, data)
            else:
                q.put_nowait(data)
        except (asyncio.QueueFull, RuntimeError):
            logger.debug("SSE queue full for user %s — notification dropped", user_id)


_sse_event_counter = 0
_sse_event_lock = asyncio.Lock()


async def _next_event_id() -> int:
    global _sse_event_counter
    async with _sse_event_lock:
        _sse_event_counter += 1
        return _sse_event_counter


@router.get("/notifications/stream",
            summary="SSE notification stream",
            description="Server-Sent Events stream for real-time notifications. Authenticates via auth cookie or legacy query token. Supports Last-Event-ID for missed event recovery.")
async def notification_stream(request: Request, token: str = Query(None, max_length=200)):
    from auth import _extract_token
    session_token = _extract_token(request)
    if not session_token and token and os.environ.get("ENVIRONMENT", "").lower() not in {"production", "prod", "prd"}:
        session_token = token
    if not session_token:
        raise HTTPException(401, "Yêu cầu token xác thực")
    row = await asyncio.to_thread(_query_sse_session, session_token)
    if not row:
        raise HTTPException(401, "Token không hợp lệ")
    uid = str(db._row_to_dict(row)["id"])

    last_event_id = request.headers.get("Last-Event-ID")
    missed = []
    if last_event_id:
        missed = await asyncio.to_thread(_fetch_missed_sse, uid)

    global _sse_loop
    if _sse_loop is None:
        _sse_loop = asyncio.get_running_loop()

    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    await _register_sse_subscriber(uid, queue)

    async def event_generator():
        try:
            yield ": connected\n\n"
            async for chunk in _replay_missed_sse(missed):
                yield chunk
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    if data is None:
                        break
                    eid = await _next_event_id()
                    yield f"id: {eid}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            await _unregister_sse_subscriber(uid, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def _register_sse_subscriber(uid: str, queue: "asyncio.Queue"):
    async with _sse_lock:
        with _sse_thread_lock:
            subs = _sse_subscribers.setdefault(uid, [])
            if len(subs) >= _SSE_MAX_PER_USER:
                evicted = subs.pop(0)
                try:
                    evicted.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            subs.append(queue)


def _query_sse_session(session_token: str):
    from auth import _hash_token
    with db._conn() as conn:
        return db._fetchone(conn, f"""
            SELECT u.id FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = {db._ph} AND s.expires_at > NOW() AND u.is_active = TRUE
        """, (_hash_token(session_token),))


def _fetch_missed_sse(uid: str):
    with db._conn() as conn:
        return db._fetchall(conn, f"""
            SELECT id, type, title, body, ref_type, ref_id, created_at
            FROM notifications
            WHERE user_id = {db._ph}::uuid AND is_read = FALSE
              AND created_at > NOW() - INTERVAL '5 minutes'
            ORDER BY created_at ASC LIMIT 50
        """, (uid,))


async def _replay_missed_sse(missed):
    for m in missed:
        md = db._row_to_dict(m)
        eid = await _next_event_id()
        payload = {k: str(md[k]) if md.get(k) is not None else None for k in ("id", "type", "title", "body", "ref_type", "ref_id")}
        payload["created_at"] = str(md["created_at"]) if md.get("created_at") is not None else ""
        yield f"id: {eid}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _unregister_sse_subscriber(uid: str, queue: "asyncio.Queue"):
    async with _sse_lock:
        with _sse_thread_lock:
            subs = _sse_subscribers.get(uid, [])
            if queue in subs:
                subs.remove(queue)
            if not subs:
                _sse_subscribers.pop(uid, None)


_NOTIF_TYPE_TO_PREF = {
    "like": "pref_like",
    "reaction": "pref_like",
    "comment": "pref_comment",
    "comment_reply": "pref_comment",
    "comment_like": "pref_like",
    "question_answer": "pref_comment",
    "mention": "pref_mention",
    "follow": "pref_follow",
    "event_reminder": "pref_system",
    "moderation": "pref_system",
    "social": "pref_system",
    "claim_approved": "pref_system",
    "claim_rejected": "pref_system",
    "digest": "pref_system",
    "achievement": "pref_system",
}


def _user_wants_notif(conn, user_id: str, notif_type: str) -> bool:
    pref_col = _NOTIF_TYPE_TO_PREF.get(notif_type)
    if not pref_col:
        return True
    ph = db._ph
    row = db._fetchone(conn, f"""
        SELECT {pref_col} FROM notification_preferences WHERE user_id = {ph}::uuid
    """, (user_id,))
    if not row:
        return True
    return bool(db._row_to_dict(row).get(pref_col, True))


def create_notification(user_id: str, notif_type: str, title: str,
                        body: str = None, ref_type: str = None, ref_id: str = None,
                        actor_id: str = None):
    """Create a notification (called internally by other modules)."""
    ph = db._ph
    with db._conn() as conn:
        if actor_id:
            blocked = db._fetchone(conn, f"""
                SELECT 1 FROM blocks
                WHERE (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
                   OR (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
            """, (user_id, actor_id, actor_id, user_id))
            if blocked:
                return
            muted = db._fetchone(conn, f"""
                SELECT 1 FROM user_mutes
                WHERE user_id = {ph}::uuid AND muted_id = {ph}::uuid
            """, (user_id, actor_id))
            if muted:
                return
        if not _user_wants_notif(conn, user_id, notif_type):
            return
        if ref_id:
            dup = db._fetchone(conn, f"""
                SELECT 1 FROM notifications
                WHERE user_id = {ph}::uuid AND type = {ph} AND ref_id = {ph}
                AND created_at > NOW() - INTERVAL '5 minutes'
            """, (user_id, notif_type, ref_id))
            if dup:
                return
        row = db._fetchone(conn, f"""
            INSERT INTO notifications (user_id, type, title, body, ref_type, ref_id)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}, {ph}, {ph})
            RETURNING id
        """, (user_id, notif_type, title, body, ref_type, ref_id))
        notif_id = str(db._row_to_dict(row)["id"]) if row else None
    _notify_sse(user_id, {"id": notif_id, "type": notif_type, "title": title, "body": body,
                          "ref_type": ref_type, "ref_id": str(ref_id) if ref_id else None})


# ── Follow ──

@router.post("/follow/{target_type}/{target_id}",
             summary="Toggle follow",
             description="Follows or unfollows a user or entity. Returns the new follow state. Blocked users cannot be followed.")
async def toggle_follow(target_type: str, target_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    target_id = validate_path_id(target_id, "target_id")
    check_rate(f"follow:{user['id']}", 30, 300, "Thao tác follow quá nhanh. Vui lòng thử lại sau.")
    if target_type not in ("user", "entity"):
        raise HTTPException(400, "Loại follow: user hoặc entity")

    if target_type == "user" and target_id == str(user["id"]):
        raise HTTPException(400, "Không thể tự follow chính mình")

    # Guard: không tạo follow rác trỏ đối tượng không tồn tại
    if target_type == "entity" and not await asyncio.to_thread(db.get_entity, target_id):
        raise HTTPException(404, "Không tìm thấy địa điểm")
    if target_type == "user":
        ph = db._ph
        def _check_user():
            with db._conn() as conn:
                return db._fetchone(conn, f"SELECT 1 FROM users WHERE id::text = {ph} AND is_active = TRUE", (target_id,))
        if not await asyncio.to_thread(_check_user):
            raise HTTPException(404, "Không tìm thấy người dùng")

        uid = str(user["id"])
        def _check_block():
            with db._conn() as conn:
                return db._fetchone(conn, f"""
                    SELECT 1 FROM blocks
                    WHERE (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
                       OR (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
                """, (uid, target_id, target_id, uid))
        if await asyncio.to_thread(_check_block):
            raise HTTPException(403, "Không thể follow người dùng này")

    uid = str(user["id"])
    following = await asyncio.to_thread(_toggle_follow_row, uid, target_type, target_id)

    await _run_follow_side_effects(user, target_id, target_type, following)

    return {"following": following}


_MAX_FOLLOW_USER = 500
_MAX_FOLLOW_ENTITY = 1000


def _toggle_follow_row(uid: str, target_type: str, target_id: str) -> bool:
    ph = db._ph
    with db._conn() as conn:
        deleted = db._fetchone(conn, f"""
            DELETE FROM follows
            WHERE follower_id = {ph}::uuid AND target_type = {ph} AND target_id = {ph}
            RETURNING 1
        """, (uid, target_type, target_id))
        if deleted:
            return False
        cap = _MAX_FOLLOW_USER if target_type == "user" else _MAX_FOLLOW_ENTITY
        cnt = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM follows
            WHERE follower_id = {ph}::uuid AND target_type = {ph}
        """, (uid, target_type))
        if cnt and db._row_to_dict(cnt)["c"] >= cap:
            raise HTTPException(400, f"Đã đạt giới hạn follow ({cap})")
        db._execute(conn, f"""
            INSERT INTO follows (follower_id, target_type, target_id)
            VALUES ({ph}::uuid, {ph}, {ph})
            ON CONFLICT DO NOTHING
        """, (uid, target_type, target_id))
        return True


async def _run_follow_side_effects(user, target_id: str, target_type: str, following: bool):
    if following and target_type == "user":
        def _notify_follow():
            create_notification(
                target_id, "follow",
                f"{user.get('display_name', 'Ai đó')} đã theo dõi bạn",
                ref_type="user", ref_id=str(user["id"]), actor_id=str(user["id"]),
            )
        await asyncio.to_thread(_notify_follow)

        # Thành tích tính cho người ĐƯỢC follow (target_id, số follower vừa
        # tăng), không phải người bấm follow. Inline closure (không import
        # social từ notifications) để tránh vòng import — social.py đã
        # import từ notifications.py.
        def _check_follow_achievements_bg(uid=target_id):
            try:
                from achievements import check_achievements
                with db._conn() as conn:
                    check_achievements(conn, uid, notify=True)
            except Exception as e:  # noqa: BLE001
                logger.warning("achievement check failed for %s: %s", uid, e)
        asyncio.create_task(asyncio.to_thread(_check_follow_achievements_bg))


@router.get("/follow/check/{target_type}/{target_id}",
            summary="Check follow status",
            description="Checks whether the authenticated user is following a specific user or entity.")
async def check_follow(target_type: str, target_id: str, user=Depends(require_user)):
    validate_path_id(target_id, "target_id")
    _require_pg()
    if target_type not in ("user", "entity"):
        raise HTTPException(400, "Loại follow: user hoặc entity")
    ph = db._ph
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            return db._fetchone(conn, f"""
                SELECT 1 FROM follows
                WHERE follower_id = {ph}::uuid AND target_type = {ph} AND target_id = {ph}
            """, (uid, target_type, target_id))
    row = await asyncio.to_thread(_query)
    return {"following": row is not None}


@router.get("/following",
            summary="List followed users and entities",
            description="Returns a paginated list of users and entities the authenticated user follows. Optionally filter by target type.")
async def get_following(
    target_type: Optional[str] = Query(None, pattern="^(user|entity)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    user=Depends(require_user),
):
    ph = db._ph
    conditions = [f"f.follower_id = {ph}::uuid"]
    params: list = [str(user["id"])]

    if target_type:
        conditions.append(f"f.target_type = {ph}")
        params.append(target_type)

    where = " AND ".join(conditions)
    params.extend([limit, offset])

    count_params = list(params[:-2])

    def _query():
        with db._conn() as conn:
            total_row = db._fetchone(conn, f"SELECT COUNT(*) as c FROM follows f WHERE {where}", count_params)
            total = db._row_to_dict(total_row)["c"] if total_row else 0
            rows = db._fetchall(conn, f"""
                SELECT f.*,
                       CASE WHEN f.target_type = 'user' THEN u.display_name
                            WHEN f.target_type = 'entity' THEN e.name END as target_name,
                       CASE WHEN f.target_type = 'entity' THEN e.type END as entity_type
                FROM follows f
                LEFT JOIN users u ON f.target_type = 'user' AND u.id::text = f.target_id
                LEFT JOIN entities e ON f.target_type = 'entity' AND e.id = f.target_id
                WHERE {where}
                ORDER BY f.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, params)
            return rows, total
    rows, total = await asyncio.to_thread(_query)

    items = [{
        "target_type": r["target_type"],
        "target_id": r["target_id"],
        "target_name": r.get("target_name"),
        "entity_type": r.get("entity_type"),
        "created_at": str(r.get("created_at", "")),
    } for r in [db._row_to_dict(row) for row in rows]]
    return {"following": items, "total": total, "has_more": offset + limit < total}


@router.get("/followers/count/{target_type}/{target_id}",
            summary="Get follower count",
            description="Returns the total number of followers for a given user or entity. No authentication required.")
async def get_follower_count(target_type: str, target_id: str):
    if target_type not in ("user", "entity"):
        raise HTTPException(400, "target_type phải là 'user' hoặc 'entity'")
    validate_path_id(target_id, "target_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM follows
                WHERE target_type = {ph} AND target_id = {ph}
            """, (target_type, target_id))
        return row
    row = await asyncio.to_thread(_query)
    return {"count": db._row_to_dict(row)["c"] if row else 0}


# ── Report ──

# P0-20: đổi path để KHÔNG đụng `POST /api/report` của public_api (báo-sai ẩn danh → JSONL).
# Endpoint authed này ghi PG reports table; FE hiện dùng public JSONL, giữ cả hai tách bạch.
RL_REPORT_LIMIT = 10
RL_REPORT_WINDOW = 3600

@router.post("/report-ugc",
             summary="Report user-generated content",
             description="Submits a moderation report for a post, comment, or user. Duplicate pending reports for the same target are rejected.")
async def create_report(body: ReportRequest, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"report:{user['id']}", RL_REPORT_LIMIT, RL_REPORT_WINDOW, "Bạn đã gửi quá nhiều báo cáo. Vui lòng thử lại sau.")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            existing = db._fetchone(conn, f"""
                SELECT 1 FROM reports
                WHERE reporter_id = {ph}::uuid AND target_type = {ph} AND target_id = {ph}
                    AND status = 'pending'
            """, (str(user["id"]), body.target_type, body.target_id))
            if existing:
                raise HTTPException(400, "Bạn đã báo cáo nội dung này rồi")
            db._execute(conn, f"""
                INSERT INTO reports (reporter_id, target_type, target_id, reason)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph})
            """, (str(user["id"]), body.target_type, body.target_id, body.reason))
    await asyncio.to_thread(_query)
    return {"success": True, "message": "Báo cáo đã được gửi. Cảm ơn bạn!"}


# ── Block ──

@router.post("/block/{blocked_id}",
             summary="Toggle block user",
             description="Blocks or unblocks a user. Blocking automatically removes mutual follows. Returns the new block state.")
async def toggle_block(blocked_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    blocked_id = validate_path_id(blocked_id, "blocked_id")
    check_rate(f"block:{user['id']}", 20, 300, "Thao tác chặn quá nhanh. Vui lòng thử lại sau.")
    if blocked_id == str(user["id"]):
        raise HTTPException(400, "Không thể tự chặn chính mình")

    ph = db._ph
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            deleted = db._fetchone(conn, f"""
                DELETE FROM blocks
                WHERE blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid
                RETURNING 1
            """, (uid, blocked_id))
            if deleted:
                return False
            db._execute(conn, f"""
                INSERT INTO blocks (blocker_id, blocked_id)
                VALUES ({ph}::uuid, {ph}::uuid)
                ON CONFLICT DO NOTHING
            """, (uid, blocked_id))
            db._execute(conn, f"""
                DELETE FROM follows
                WHERE (follower_id = {ph}::uuid AND target_type = 'user' AND target_id = {ph})
                   OR (follower_id = {ph}::uuid AND target_type = 'user' AND target_id = {ph})
            """, (uid, blocked_id, blocked_id, uid))
            return True
    blocked = await asyncio.to_thread(_query)
    return {"blocked": blocked}


@router.get("/blocked-users",
            summary="List blocked users",
            description="Returns a paginated list of users blocked by the authenticated user, with display name and avatar.")
async def list_blocked_users(page: int = Query(1, ge=1, le=100), limit: int = Query(50, ge=1, le=100),
                              user=Depends(require_user)):
    offset = (page - 1) * limit
    def _query():
        ph = db._ph
        uid = str(user["id"])
        with db._conn() as conn:
            total_row = db._fetchone(conn, f"SELECT COUNT(*) as c FROM blocks WHERE blocker_id = {ph}::uuid", (uid,))
            total = db._row_to_dict(total_row)["c"] if total_row else 0
            rows = db._fetchall(conn, f"""
                SELECT u.id, u.display_name, u.avatar_url, u.username, b.created_at
                FROM blocks b JOIN users u ON u.id = b.blocked_id
                WHERE b.blocker_id = {ph}::uuid
                ORDER BY b.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
            return rows, total
    rows, total = await asyncio.to_thread(_query)
    result = []
    for r in rows:
        d = db._row_to_dict(r)
        result.append({"id": str(d["id"]), "display_name": d.get("display_name"),
                        "avatar_url": d.get("avatar_url"), "username": d.get("username"),
                        "blocked_at": str(d.get("created_at", ""))})
    return {"blocked": result, "total": total, "page": page, "has_more": offset + limit < total}


# ── Mute (soft block — hides posts from feed only) ──

@router.post("/mute/{muted_id}",
             summary="Toggle mute user",
             description="Mutes or unmutes a user. Muted users' posts are hidden from the feed but they are not blocked. Returns the new mute state.")
async def toggle_mute(muted_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    muted_id = validate_path_id(muted_id, "muted_id")
    check_rate(f"mute:{user['id']}", 20, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    if muted_id == str(user["id"]):
        raise HTTPException(400, "Không thể tắt tiếng chính mình")
    ph = db._ph
    uid = str(user["id"])

    def _query():
        with db._conn() as conn:
            deleted = db._fetchone(conn, f"""
                DELETE FROM user_mutes
                WHERE user_id = {ph}::uuid AND muted_id = {ph}::uuid RETURNING 1
            """, (uid, muted_id))
            if deleted:
                return False
            db._execute(conn, f"""
                INSERT INTO user_mutes (user_id, muted_id) VALUES ({ph}::uuid, {ph}::uuid)
                ON CONFLICT DO NOTHING
            """, (uid, muted_id))
            return True

    muted = await asyncio.to_thread(_query)
    return {"muted": muted}


@router.get("/muted-users",
            summary="List muted users",
            description="Returns a paginated list of users muted by the authenticated user, with display name and avatar.")
async def list_muted_users(page: int = Query(1, ge=1, le=100), limit: int = Query(50, ge=1, le=100),
                            user=Depends(require_user)):
    offset = (page - 1) * limit
    def _query():
        ph = db._ph
        uid = str(user["id"])
        with db._conn() as conn:
            total_row = db._fetchone(conn, f"SELECT COUNT(*) as c FROM user_mutes WHERE user_id = {ph}::uuid", (uid,))
            total = db._row_to_dict(total_row)["c"] if total_row else 0
            rows = db._fetchall(conn, f"""
                SELECT u.id, u.display_name, u.avatar_url, u.username, m.created_at
                FROM user_mutes m JOIN users u ON u.id = m.muted_id
                WHERE m.user_id = {ph}::uuid ORDER BY m.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
            return rows, total

    rows, total = await asyncio.to_thread(_query)
    result = []
    for r in rows:
        d = db._row_to_dict(r)
        result.append({"id": str(d["id"]), "display_name": d.get("display_name"),
                        "avatar_url": d.get("avatar_url"), "username": d.get("username"),
                        "muted_at": str(d.get("created_at", ""))})
    return {"muted": result, "total": total, "page": page, "has_more": offset + limit < total}


# ── Helpers ──

def _group_notifications(notifs: list[dict]) -> list[dict]:
    """Group same (type, ref_type, ref_id) within 24h. Latest becomes the group representative."""
    from datetime import datetime
    groups: dict[str, dict] = {}
    result = []
    for n in notifs:
        key = f"{n['type']}:{n.get('ref_type', '')}:{n.get('ref_id', '')}"
        if key in groups:
            existing = groups[key]
            try:
                t1 = datetime.fromisoformat(str(existing["created_at"]).replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(str(n["created_at"]).replace("Z", "+00:00"))
                if abs((t1 - t2).total_seconds()) < 86400:
                    existing.setdefault("group_count", 1)
                    existing["group_count"] += 1
                    if not existing.get("is_read") and n.get("is_read"):
                        pass
                    continue
            except (ValueError, TypeError):
                pass
        groups[key] = n
        result.append(n)
    return result


def _format_notif(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "type": row["type"],
        "title": row["title"],
        "body": row.get("body"),
        "ref_type": row.get("ref_type"),
        "ref_id": str(row["ref_id"]) if row.get("ref_id") else None,
        "is_read": row.get("is_read", False),
        "created_at": str(row.get("created_at", "")),
    }


# ── RSVP lễ-hội/sự-kiện: "Tôi sẽ đi" ──

@router.post("/events/{entity_id}/rsvp",
             summary="Toggle event RSVP",
             description="Marks or unmarks the authenticated user as attending an event. Only entities of type 'event' are accepted. Returns the new RSVP state and attendee count.")
async def toggle_rsvp(entity_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    validate_path_id(entity_id, "entity_id")
    check_rate(f"rsvp:{user['id']}", 30, 300, "Thao tác RSVP quá nhanh. Vui lòng thử lại sau.")
    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Không tìm thấy sự kiện")
    etype = entity.get("type", "") if isinstance(entity, dict) else ""
    if etype != "event":
        raise HTTPException(400, "Chỉ có thể RSVP cho sự kiện (event)")
    ph = db._ph
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            deleted = db._fetchone(conn,
                f"DELETE FROM event_rsvp WHERE user_id = {ph}::uuid AND entity_id = {ph} RETURNING 1", (uid, entity_id))
            if deleted:
                going = False
            else:
                cur = db._execute(conn, f"INSERT INTO event_rsvp (user_id, entity_id) VALUES ({ph}::uuid, {ph}) ON CONFLICT DO NOTHING", (uid, entity_id))
                going = bool(cur and cur.rowcount > 0)
            cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM event_rsvp WHERE entity_id = {ph}", (entity_id,))
        return going, int(db._row_to_dict(cnt)["c"]) if cnt else 0
    going, count = await asyncio.to_thread(_query)
    return {"going": going, "count": count}


@router.get("/events/{entity_id}/rsvp",
            summary="Get event RSVP status",
            description="Returns the total attendee count and whether the current user (if authenticated) has RSVP'd to the event.")
async def get_rsvp(entity_id: str, request: Request = None):
    validate_path_id(entity_id, "entity_id")
    u = await get_current_user(request) if request else None
    uid = str(u["id"]) if u else None
    def _query():
        ph = db._ph
        with db._conn() as conn:
            cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM event_rsvp WHERE entity_id = {ph}", (entity_id,))
            count = int(db._row_to_dict(cnt)["c"]) if cnt else 0
            going = False
            if uid:
                mine = db._fetchone(conn,
                    f"SELECT 1 FROM event_rsvp WHERE user_id = {ph}::uuid AND entity_id = {ph}", (uid, entity_id))
                going = bool(mine)
        return count, going
    count, going = await asyncio.to_thread(_query)
    return {"count": count, "going": going}
