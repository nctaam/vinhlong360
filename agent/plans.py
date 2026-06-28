"""
plans.py — Lịch trình cá nhân đồng-bộ tài-khoản (builder /tao-lich-trinh).

Cho phép plan tự-tạo của user theo họ qua nhiều thiết bị (như favorites ở saved.py).
Postgres-only (UGC parity); 503 ở SQLite dev. Mỗi plan = {title, stops[]}.
"""
import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth_middleware import require_user, require_csrf, validate_path_id
from database import db
from ratelimit import check_rate


from auth_middleware import require_pg as _require_pg

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
        "is_public": bool(d.get("is_public")),
        "savedAt": str(d.get("created_at") or ""),
    }


def _list(conn, uid: str) -> list[dict]:
    ph = db._ph
    rows = db._fetchall(conn, f"""
        SELECT id, title, stops, is_public, created_at FROM user_plans
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
    def _query():
        with db._conn() as conn:
            return {"plans": _list(conn, str(user["id"]))}
    return await asyncio.to_thread(_query)


@router.post("")
async def add_plan(body: PlanBody, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"plan:{user['id']}", 30, 300, "Tạo lịch trình quá nhanh. Vui lòng thử lại sau.")
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            ph = db._ph
            cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM user_plans WHERE user_id = {ph}::uuid", (uid,))
            if cnt and int(db._row_to_dict(cnt)["c"]) >= MAX_PLANS:
                raise HTTPException(400, f"Tối đa {MAX_PLANS} lịch trình. Hãy xoá bớt.")
            pid = _insert(conn, uid, body)
            return {"id": pid, "saved": True}
    return await asyncio.to_thread(_query)


@router.delete("/{plan_id}")
async def remove_plan(plan_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    plan_id = validate_path_id(plan_id, "plan_id")
    check_rate(f"plan:{user['id']}", 30, 300, "Xóa lịch trình quá nhanh. Vui lòng thử lại sau.")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                DELETE FROM user_plans WHERE id::text = {ph} AND user_id = {ph}::uuid
            """, (plan_id, str(user["id"])))
    await asyncio.to_thread(_query)
    return {"deleted": True}


@router.post("/merge")
async def merge_plans(body: MergeBody, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"plan-merge:{user['id']}", 10, 300, "Đồng bộ lịch trình quá nhanh. Vui lòng thử lại sau.")
    uid = str(user["id"])
    incoming = (body.plans or [])[:MAX_PLANS]
    def _query():
        with db._conn() as conn:
            for p in incoming:
                if p.stops:
                    _insert(conn, uid, p)
            return {"plans": _list(conn, uid)}
    return await asyncio.to_thread(_query)


class PublishBody(BaseModel):
    is_public: bool = True


@router.post("/{plan_id}/publish")
async def publish_plan(plan_id: str, body: PublishBody, user=Depends(require_user), _csrf=Depends(require_csrf)):
    plan_id = validate_path_id(plan_id, "plan_id")
    check_rate(f"plan:{user['id']}", 30, 300, "Thao tác quá nhanh. Vui lòng thử lại sau.")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE user_plans SET is_public = {ph} WHERE id::text = {ph} AND user_id = {ph}::uuid
            """, (body.is_public, plan_id, str(user["id"])))
    await asyncio.to_thread(_query)
    return {"is_public": body.is_public}


# ── Public (no-auth): xem lịch trình được chia-sẻ công-khai ──
public_router = APIRouter(prefix="/api/shared-plans", tags=["plans"], dependencies=[Depends(_require_pg)])


@public_router.get("")
async def list_shared(limit: int = 30):
    limit = max(1, min(int(limit), 60))
    def _query():
        ph = db._ph
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, p.title, p.stops, p.is_public, p.created_at, u.display_name AS author
                FROM user_plans p JOIN users u ON u.id = p.user_id
                WHERE p.is_public = TRUE ORDER BY p.created_at DESC LIMIT {ph}
            """, (limit,))
        out = []
        for r in rows:
            d = db._row_to_dict(r)
            plan = _row_plan(r)
            plan["author"] = d.get("author")
            plan["stop_count"] = len(plan["stops"])
            out.append(plan)
        return {"plans": out}
    return await asyncio.to_thread(_query)


@public_router.get("/{plan_id}")
async def get_shared(plan_id: str):
    plan_id = validate_path_id(plan_id, "plan_id")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT p.id, p.title, p.stops, p.is_public, p.created_at, u.display_name AS author
                FROM user_plans p JOIN users u ON u.id = p.user_id
                WHERE p.id::text = {ph} AND p.is_public = TRUE
            """, (plan_id,))
        if not row:
            raise HTTPException(404, "Lịch trình không tồn tại hoặc chưa công khai")
        plan = _row_plan(row)
        plan["author"] = db._row_to_dict(row).get("author")
        return {"plan": plan}
    return await asyncio.to_thread(_query)
