"""
visits.py — "Đã đi / Muốn đi": đánh dấu địa điểm theo người dùng (bản đồ cá nhân).
Postgres-only (UGC parity); 503 ở SQLite dev. status ∈ {want, visited}, 1 status/địa-điểm.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from auth_middleware import require_user
from database import db


def _require_pg():
    if not db._use_pg:
        raise HTTPException(status_code=503, detail="Tính năng cần Postgres (không khả dụng ở chế độ SQLite).")


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


@router.get("/check/{entity_id}")
async def check_visit(entity_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT status FROM user_visits WHERE user_id = {ph}::uuid AND entity_id = {ph}",
                           (str(user["id"]), entity_id))
    return {"status": db._row_to_dict(row)["status"] if row else None}


@router.post("")
async def set_visit(body: VisitBody, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO user_visits (user_id, entity_id, status) VALUES ({ph}::uuid, {ph}, {ph})
            ON CONFLICT (user_id, entity_id) DO UPDATE SET status = EXCLUDED.status, created_at = NOW()
        """, (str(user["id"]), body.entity_id, body.status))
    return {"status": body.status}


@router.delete("/{entity_id}")
async def remove_visit(entity_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM user_visits WHERE user_id = {ph}::uuid AND entity_id = {ph}",
                    (str(user["id"]), entity_id))
    return {"status": None}
