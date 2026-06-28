"""
visits.py — "Đã đi / Muốn đi": đánh dấu địa điểm theo người dùng (bản đồ cá nhân).
Postgres-only (UGC parity); 503 ở SQLite dev. status ∈ {want, visited}, 1 status/địa-điểm.
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator

from auth_middleware import require_user, require_csrf, validate_path_id
from database import db
from ratelimit import check_rate


from auth_middleware import require_pg as _require_pg

router = APIRouter(prefix="/api/me/visits", tags=["visits"], dependencies=[Depends(_require_pg)])


class VisitBody(BaseModel):
    entity_id: str
    status: str

    @field_validator("status")
    @classmethod
    def _v(cls, v):
        if v not in ("want", "visited"):
            raise ValueError("status: want | visited")
        return v


@router.get("")
async def list_visits(status: str = Query(None), user=Depends(require_user)):
    def _query():
        ph = db._ph
        sql = f"SELECT entity_id, status, created_at FROM user_visits WHERE user_id = {ph}::uuid"
        params = [str(user["id"])]
        if status in ("want", "visited"):
            sql += f" AND status = {ph}"
            params.append(status)
        sql += " ORDER BY created_at DESC"
        with db._conn() as conn:
            rows = db._fetchall(conn, sql, tuple(params))
        return {"visits": [{"entity_id": db._row_to_dict(r)["entity_id"], "status": db._row_to_dict(r)["status"]} for r in rows]}
    return await asyncio.to_thread(_query)


@router.get("/check/{entity_id}")
async def check_visit(entity_id: str, user=Depends(require_user)):
    entity_id = validate_path_id(entity_id, "entity_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT status FROM user_visits WHERE user_id = {ph}::uuid AND entity_id = {ph}",
                               (str(user["id"]), entity_id))
        return {"status": db._row_to_dict(row)["status"] if row else None}
    return await asyncio.to_thread(_query)


@router.post("")
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
    return {"status": body.status}


@router.delete("/{entity_id}")
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
