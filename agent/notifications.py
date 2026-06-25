"""
vinhlong360 — Notifications + Community Features.

Endpoints:
  GET  /api/notifications          — list notifications (polling)
  POST /api/notifications/read-all — mark all as read
  POST /api/follow/{type}/{id}     — toggle follow user/entity
  GET  /api/following              — list follows
  POST /api/report                 — report content
  POST /api/block/{user_id}        — toggle block user
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator

from auth_middleware import get_current_user, require_user
from database import db


def _require_pg():
    # GĐ3.1 (quyết định): UGC chạy Postgres. SQLite dev -> 503 rõ ràng.
    if not db._use_pg:
        raise HTTPException(503, detail="Tính năng cộng đồng (UGC) cần Postgres. Local dev: docker compose up postgres.")


router = APIRouter(prefix="/api", tags=["community"], dependencies=[Depends(_require_pg)])


# ── Models ──

class ReportRequest(BaseModel):
    target_type: str
    target_id: str
    reason: str

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

@router.get("/notifications")
async def get_notifications(
    limit: int = Query(20, ge=1, le=50),
    user=Depends(require_user),
):
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT * FROM notifications
            WHERE user_id = {ph}::uuid
            ORDER BY created_at DESC
            LIMIT {ph}
        """, (str(user["id"]), limit))

        unread = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM notifications
            WHERE user_id = {ph}::uuid AND is_read = FALSE
        """, (str(user["id"]),))

    return {
        "notifications": [_format_notif(db._row_to_dict(r)) for r in rows],
        "unread_count": unread["c"] if unread else 0,
    }


@router.post("/notifications/read-all")
async def mark_all_read(user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE notifications SET is_read = TRUE
            WHERE user_id = {ph}::uuid AND is_read = FALSE
        """, (str(user["id"]),))
    return {"success": True}


@router.post("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            UPDATE notifications SET is_read = TRUE
            WHERE id::text = {ph} AND user_id = {ph}::uuid
        """, (notif_id, str(user["id"])))
    return {"success": True}


def create_notification(user_id: str, notif_type: str, title: str,
                        body: str = None, ref_type: str = None, ref_id: str = None,
                        actor_id: str = None):
    """Create a notification (called internally by other modules)."""
    ph = db._ph
    with db._conn() as conn:
        if actor_id:
            blocked = db._fetchone(conn, f"""
                SELECT 1 FROM blocks WHERE blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid
            """, (user_id, actor_id))
            if blocked:
                return
        db._execute(conn, f"""
            INSERT INTO notifications (user_id, type, title, body, ref_type, ref_id)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id, notif_type, title, body, ref_type, ref_id))


# ── Follow ──

@router.post("/follow/{target_type}/{target_id}")
async def toggle_follow(target_type: str, target_id: str, user=Depends(require_user)):
    if target_type not in ("user", "entity"):
        raise HTTPException(400, "Loại follow: user hoặc entity")

    if target_type == "user" and target_id == str(user["id"]):
        raise HTTPException(400, "Không thể tự follow chính mình")

    # Guard: không tạo follow rác trỏ entity không tồn-tại (bug-hunt 2026-06-24)
    if target_type == "entity" and not db.get_entity(target_id):
        raise HTTPException(404, "Không tìm thấy địa điểm")

    ph = db._ph
    with db._conn() as conn:
        existing = db._fetchone(conn, f"""
            SELECT 1 FROM follows
            WHERE follower_id = {ph}::uuid AND target_type = {ph} AND target_id = {ph}
        """, (str(user["id"]), target_type, target_id))

        if existing:
            db._execute(conn, f"""
                DELETE FROM follows
                WHERE follower_id = {ph}::uuid AND target_type = {ph} AND target_id = {ph}
            """, (str(user["id"]), target_type, target_id))
            following = False
        else:
            db._execute(conn, f"""
                INSERT INTO follows (follower_id, target_type, target_id)
                VALUES ({ph}::uuid, {ph}, {ph})
            """, (str(user["id"]), target_type, target_id))
            following = True

            if target_type == "user":
                create_notification(
                    target_id, "follow",
                    f"{user.get('display_name', 'Ai đó')} đã theo dõi bạn",
                    ref_type="user", ref_id=str(user["id"]),
                )

    return {"following": following}


@router.get("/following")
async def get_following(
    target_type: Optional[str] = None,
    user=Depends(require_user),
):
    ph = db._ph
    conditions = [f"f.follower_id = {ph}::uuid"]
    params = [str(user["id"])]

    if target_type:
        conditions.append(f"f.target_type = {ph}")
        params.append(target_type)

    where = " AND ".join(conditions)

    with db._conn() as conn:
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
        """, params)

    return {
        "following": [{
            "target_type": r["target_type"],
            "target_id": r["target_id"],
            "target_name": r.get("target_name"),
            "entity_type": r.get("entity_type"),
            "created_at": str(r.get("created_at", "")),
        } for r in [db._row_to_dict(row) for row in rows]],
    }


@router.get("/followers/count/{target_type}/{target_id}")
async def get_follower_count(target_type: str, target_id: str):
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM follows
            WHERE target_type = {ph} AND target_id = {ph}
        """, (target_type, target_id))
    return {"count": row["c"] if row else 0}


# ── Report ──

# P0-20: đổi path để KHÔNG đụng `POST /api/report` của public_api (báo-sai ẩn danh → JSONL).
# Endpoint authed này ghi PG reports table; FE hiện dùng public JSONL, giữ cả hai tách bạch.
@router.post("/report-ugc")
async def create_report(body: ReportRequest, user=Depends(require_user)):
    ph = db._ph
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

    return {"success": True, "message": "Báo cáo đã được gửi. Cảm ơn bạn!"}


# ── Block ──

@router.post("/block/{blocked_id}")
async def toggle_block(blocked_id: str, user=Depends(require_user)):
    if blocked_id == str(user["id"]):
        raise HTTPException(400, "Không thể tự chặn chính mình")

    ph = db._ph
    with db._conn() as conn:
        existing = db._fetchone(conn, f"""
            SELECT 1 FROM blocks
            WHERE blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid
        """, (str(user["id"]), blocked_id))

        if existing:
            db._execute(conn, f"""
                DELETE FROM blocks
                WHERE blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid
            """, (str(user["id"]), blocked_id))
            blocked = False
        else:
            db._execute(conn, f"""
                INSERT INTO blocks (blocker_id, blocked_id)
                VALUES ({ph}::uuid, {ph}::uuid)
            """, (str(user["id"]), blocked_id))
            db._execute(conn, f"""
                DELETE FROM follows
                WHERE follower_id = {ph}::uuid AND followed_id = {ph}::uuid
                   OR follower_id = {ph}::uuid AND followed_id = {ph}::uuid
            """, (str(user["id"]), blocked_id, blocked_id, str(user["id"])))
            blocked = True

    return {"blocked": blocked}


@router.get("/blocked-users")
async def list_blocked_users(user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT u.id, u.display_name, u.avatar_url, b.created_at
            FROM blocks b JOIN users u ON u.id = b.blocked_id
            WHERE b.blocker_id = {ph}::uuid
            ORDER BY b.created_at DESC
        """, (str(user["id"]),))
    return {"blocked": [{"id": str(db._row_to_dict(r)["id"]), "display_name": db._row_to_dict(r).get("display_name"), "avatar_url": db._row_to_dict(r).get("avatar_url"), "blocked_at": str(db._row_to_dict(r).get("created_at", ""))} for r in rows]}


# ── Helpers ──

def _format_notif(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "type": row["type"],
        "title": row["title"],
        "body": row.get("body"),
        "ref_type": row.get("ref_type"),
        "ref_id": row.get("ref_id"),
        "is_read": row.get("is_read", False),
        "created_at": str(row.get("created_at", "")),
    }


# ── RSVP lễ-hội/sự-kiện: "Tôi sẽ đi" ──

@router.post("/events/{entity_id}/rsvp")
async def toggle_rsvp(entity_id: str, user=Depends(require_user)):
    """Bật/tắt RSVP cho 1 sự-kiện. Trả {going, count}."""
    ph = db._ph
    uid = str(user["id"])
    with db._conn() as conn:
        existing = db._fetchone(conn,
            f"SELECT 1 FROM event_rsvp WHERE user_id = {ph}::uuid AND entity_id = {ph}", (uid, entity_id))
        if existing:
            db._execute(conn, f"DELETE FROM event_rsvp WHERE user_id = {ph}::uuid AND entity_id = {ph}", (uid, entity_id))
            going = False
        else:
            db._execute(conn, f"INSERT INTO event_rsvp (user_id, entity_id) VALUES ({ph}::uuid, {ph})", (uid, entity_id))
            going = True
        cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM event_rsvp WHERE entity_id = {ph}", (entity_id,))
    return {"going": going, "count": int(db._row_to_dict(cnt)["c"]) if cnt else 0}


@router.get("/events/{entity_id}/rsvp")
async def get_rsvp(entity_id: str, request: Request = None):
    """Số người RSVP + (nếu đăng nhập) trạng thái của mình."""
    ph = db._ph
    with db._conn() as conn:
        cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM event_rsvp WHERE entity_id = {ph}", (entity_id,))
        count = int(db._row_to_dict(cnt)["c"]) if cnt else 0
        going = False
        u = await get_current_user(request) if request else None
        if u:
            mine = db._fetchone(conn,
                f"SELECT 1 FROM event_rsvp WHERE user_id = {ph}::uuid AND entity_id = {ph}", (str(u["id"]), entity_id))
            going = bool(mine)
    return {"count": count, "going": going}
