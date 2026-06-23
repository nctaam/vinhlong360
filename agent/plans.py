"""
plans.py — Lịch trình cá nhân đồng-bộ tài-khoản (builder /tao-lich-trinh).

Cho phép plan tự-tạo của user theo họ qua nhiều thiết bị (như favorites ở saved.py).
Postgres-only (UGC parity); 503 ở SQLite dev. Mỗi plan = {title, stops[]}.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_middleware import require_user
from database import db


def _require_pg():
    if not db._use_pg:
        raise HTTPException(status_code=503, detail="Tính năng cần Postgres (không khả dụng ở chế độ SQLite).")


router = APIRouter(prefix="/api/my-plans", tags=["plans"], dependencies=[Depends(_require_pg)])

MAX_PLANS = 100
MAX_STOPS = 50


class PlanBody(BaseModel):
    title: str = Field("Lịch trình", max_length=120)
    stops: list[dict] = Field(default_factory=list)


class MergeBody(BaseModel):
    plans: list[PlanBody] = Field(default_factory=list)


def _row_plan(row) -> dict:
    d = db._row_to_dict(row)
    stops = d.get("stops") or []
    if isinstance(stops, str):
        try:
            stops = json.loads(stops)
        except (json.JSONDecodeError, TypeError):
            stops = []
    return {
        "id": str(d["id"]),
        "title": d.get("title") or "Lịch trình",
        "stops": stops if isinstance(stops, list) else [],
        "savedAt": str(d.get("created_at") or ""),
    }


def _list(conn, uid: str) -> list[dict]:
    ph = db._ph
    rows = db._fetchall(conn, f"""
        SELECT id, title, stops, created_at FROM user_plans
        WHERE user_id = {ph}::uuid ORDER BY created_at DESC
    """, (uid,))
    return [_row_plan(r) for r in rows]


def _insert(conn, uid: str, body: PlanBody) -> str:
    ph = db._ph
    stops = (body.stops or [])[:MAX_STOPS]
    row = db._fetchone(conn, f"""
        INSERT INTO user_plans (user_id, title, stops)
        VALUES ({ph}::uuid, {ph}, {ph}::jsonb)
        RETURNING id
    """, (uid, (body.title or "Lịch trình")[:120], json.dumps(stops, ensure_ascii=False)))
    return str(db._row_to_dict(row)["id"])


@router.get("")
async def list_plans(user=Depends(require_user)):
    with db._conn() as conn:
        return {"plans": _list(conn, str(user["id"]))}


@router.post("")
async def add_plan(body: PlanBody, user=Depends(require_user)):
    uid = str(user["id"])
    with db._conn() as conn:
        # cap số plan/user (chống phình)
        ph = db._ph
        cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM user_plans WHERE user_id = {ph}::uuid", (uid,))
        if cnt and int(db._row_to_dict(cnt)["c"]) >= MAX_PLANS:
            raise HTTPException(400, f"Tối đa {MAX_PLANS} lịch trình. Hãy xoá bớt.")
        pid = _insert(conn, uid, body)
        return {"id": pid, "saved": True}


@router.delete("/{plan_id}")
async def remove_plan(plan_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            DELETE FROM user_plans WHERE id::text = {ph} AND user_id = {ph}::uuid
        """, (plan_id, str(user["id"])))
    return {"deleted": True}


@router.post("/merge")
async def merge_plans(body: MergeBody, user=Depends(require_user)):
    """Đẩy plan local (khách) lên tài-khoản khi đăng nhập, trả danh sách đầy đủ."""
    uid = str(user["id"])
    incoming = (body.plans or [])[:MAX_PLANS]
    with db._conn() as conn:
        for p in incoming:
            if p.stops:
                _insert(conn, uid, p)
        return {"plans": _list(conn, uid)}
