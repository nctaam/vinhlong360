"""
visits.py — "Đã đi / Muốn đi": đánh dấu địa điểm theo người dùng (bản đồ cá nhân).
Postgres-only (UGC parity); 503 ở SQLite dev. status ∈ {want, visited}, 1 status/địa-điểm.
"""
import asyncio

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from auth_middleware import require_user, require_csrf, validate_path_id
from database import db
from ratelimit import check_rate


from auth_middleware import require_pg as _require_pg

router = APIRouter(prefix="/api/me/visits", tags=["visits"], dependencies=[Depends(_require_pg)])


class VisitBody(BaseModel):
    entity_id: str = Field(max_length=200)
    status: str

    @field_validator("status")
    @classmethod
    def _v(cls, v):
        if v not in ("want", "visited"):
            raise ValueError("status: want | visited")
        return v


@router.get("",
            summary="List visit marks",
            description="Returns all entities marked as 'want' or 'visited' by the user. Optionally filter by status. Ordered by most recent, limited to 5000.")
async def list_visits(status: Optional[str] = Query(None, pattern="^(want|visited)$"), user=Depends(require_user)):
    def _query():
        ph = db._ph
        sql = f"SELECT entity_id, status, created_at FROM user_visits WHERE user_id = {ph}::uuid"
        params = [str(user["id"])]
        if status in ("want", "visited"):
            sql += f" AND status = {ph}"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT 5000"
        with db._conn() as conn:
            rows = db._fetchall(conn, sql, tuple(params))
        return {"visits": [{"entity_id": (rd := db._row_to_dict(r))["entity_id"], "status": rd["status"]} for r in rows]}
    return await asyncio.to_thread(_query)


@router.get("/check/{entity_id}",
            summary="Check visit status for an entity",
            description="Returns the current visit status ('want', 'visited', or null) for a specific entity. Used to render toggle state in the UI.")
async def check_visit(entity_id: str, user=Depends(require_user)):
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT status FROM user_visits WHERE user_id = {ph}::uuid AND entity_id = {ph}",
                               (str(user["id"]), entity_id))
        return {"status": db._row_to_dict(row)["status"] if row else None}
    return await asyncio.to_thread(_query)


@router.post("",
             summary="Set visit status",
             description="Marks an entity as 'want' or 'visited' for the user. Upserts on conflict, updating the status and timestamp.")
async def set_visit(body: VisitBody, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"visit:{user['id']}", 60, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                INSERT INTO user_visits (user_id, entity_id, status) VALUES ({ph}::uuid, {ph}, {ph})
                ON CONFLICT (user_id, entity_id) DO UPDATE SET status = EXCLUDED.status, created_at = NOW()
            """, (str(user["id"]), body.entity_id, body.status))
    await asyncio.to_thread(_query)

    if body.status == "visited":
        # Fire-and-forget: chỉ tính thành tích khi thật sự "đã đi" (không
        # phải "muốn đi"). Inline closure (không import social) để tránh
        # phụ thuộc chéo module không cần thiết trong visits.py.
        def _check_visit_achievements_bg(uid=str(user["id"])):
            try:
                from achievements import check_achievements
                with db._conn() as conn:
                    check_achievements(conn, uid, notify=True)
            except Exception:
                pass
        asyncio.create_task(asyncio.to_thread(_check_visit_achievements_bg))

    return {"status": body.status}


@router.get("/review-prompts",
            summary="Get review prompts",
            description="Returns entities the user has visited but not yet reviewed. Used to prompt the user to write reviews for places they have been to.")
async def review_prompts(user=Depends(require_user), limit: int = Query(10, ge=1, le=30)):
    """Entities visited but not yet reviewed — prompt user to write a review."""
    def _query():
        ph = db._ph
        uid = str(user["id"])
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT v.entity_id, v.created_at as visited_at
                FROM user_visits v
                WHERE v.user_id = {ph}::uuid
                AND v.status = 'visited'
                AND v.entity_id NOT IN (
                    SELECT p.entity_id FROM posts p
                    WHERE p.user_id = {ph}::uuid
                    AND p.post_type = 'review'
                    AND p.entity_id IS NOT NULL
                )
                ORDER BY v.created_at DESC
                LIMIT {ph}
            """, (uid, uid, limit))
        return {"prompts": [db._row_to_dict(r) for r in rows]}
    return await asyncio.to_thread(_query)


@router.get("/stats",
            summary="Visit statistics",
            description="Returns aggregate visit statistics for the user: total count, visited vs. want breakdown, and per-entity-type counts.")
async def visit_stats(user=Depends(require_user)):
    def _query():
        ph = db._ph
        uid = str(user["id"])
        with db._conn() as conn:
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE status = 'visited') as visited,
                       COUNT(*) FILTER (WHERE status = 'want') as want
                FROM user_visits WHERE user_id = {ph}::uuid
            """, (uid,))
            by_type = db._fetchall(conn, f"""
                SELECT e.type, v.status, COUNT(*) as cnt
                FROM user_visits v
                JOIN entities e ON e.id = v.entity_id
                WHERE v.user_id = {ph}::uuid
                GROUP BY e.type, v.status
                ORDER BY cnt DESC
            """, (uid,))
        td = db._row_to_dict(total) if total else {}
        breakdown = {}
        for r in by_type:
            rd = db._row_to_dict(r)
            etype = rd.get("type", "unknown")
            if etype not in breakdown:
                breakdown[etype] = {"visited": 0, "want": 0}
            breakdown[etype][rd["status"]] = rd["cnt"]
        return {
            "total": td.get("total", 0),
            "visited": td.get("visited", 0),
            "want": td.get("want", 0),
            "by_type": breakdown,
        }
    return await asyncio.to_thread(_query)


@router.delete("/{entity_id}",
               summary="Remove visit mark",
               description="Removes the visit mark (want or visited) for a specific entity. Returns {status: null} on success.")
async def remove_visit(entity_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    entity_id = validate_path_id(entity_id, "entity_id")
    check_rate(f"visit:{user['id']}", 60, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"DELETE FROM user_visits WHERE user_id = {ph}::uuid AND entity_id = {ph}",
                        (str(user["id"]), entity_id))
    await asyncio.to_thread(_query)
    return {"status": None}
