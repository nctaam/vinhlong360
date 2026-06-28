"""
saved.py — Saved entities (favorites) synced to the user account (P1).

Lets a logged-in user's saved places follow them across devices. Entity ids
are slugs (TEXT). A lightweight `snapshot` (name/type/image…) is stored so a new
device can render saved cards without fetching each entity. Postgres-only
(UGC parity); returns 503 on SQLite dev, like the rest of the social layer.
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

router = APIRouter(prefix="/api/saved", tags=["saved"], dependencies=[Depends(_require_pg)])

MAX_SAVED = 2000


class SavedItem(BaseModel):
    id: str = Field(max_length=200)
    name: Optional[str] = Field(None, max_length=300)
    type: Optional[str] = Field(None, max_length=50)
    place_name: Optional[str] = Field(None, max_length=300)
    place_area: Optional[str] = Field(None, max_length=100)
    summary: Optional[str] = Field(None, max_length=1000)
    image: Optional[str] = Field(None, max_length=500)


class MergeBody(BaseModel):
    items: list[SavedItem] = []


def _row_item(row) -> dict:
    d = db._row_to_dict(row)
    snap = d.get("snapshot") or {}
    if isinstance(snap, str):
        try:
            snap = json.loads(snap)
        except (json.JSONDecodeError, TypeError):
            snap = {}
    if not isinstance(snap, dict):
        snap = {}
    return {"id": d["entity_id"], **snap, "savedAt": str(d.get("created_at") or "")}


def _list(conn, uid: str) -> list[dict]:
    ph = db._ph
    rows = db._fetchall(conn, f"""
        SELECT entity_id, snapshot, created_at FROM saved_entities
        WHERE user_id = {ph}::uuid ORDER BY created_at DESC
    """, (uid,))
    return [_row_item(r) for r in rows]


def _upsert(conn, uid: str, item: SavedItem) -> None:
    ph = db._ph
    snap = item.model_dump(exclude={"id"}, exclude_none=True)
    db._execute(conn, f"""
        INSERT INTO saved_entities (user_id, entity_id, snapshot)
        VALUES ({ph}::uuid, {ph}, {ph}::jsonb)
        ON CONFLICT (user_id, entity_id) DO UPDATE SET snapshot = EXCLUDED.snapshot
    """, (uid, item.id, json.dumps(snap, ensure_ascii=False)))


@router.get("")
async def list_saved(user=Depends(require_user)):
    def _query():
        with db._conn() as conn:
            return {"items": _list(conn, str(user["id"]))}
    return await asyncio.to_thread(_query)


@router.post("")
async def add_saved(item: SavedItem, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"saved:{user['id']}", 60, 300, "Thao tác lưu quá nhanh. Vui lòng thử lại sau.")
    def _query():
        with db._conn() as conn:
            ph = db._ph
            cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM saved_entities WHERE user_id = {ph}::uuid",
                               (str(user["id"]),))
            if cnt and int(db._row_to_dict(cnt)["c"]) >= MAX_SAVED:
                raise HTTPException(400, f"Tối đa {MAX_SAVED} địa điểm đã lưu. Hãy xoá bớt.")
            _upsert(conn, str(user["id"]), item)
    await asyncio.to_thread(_query)
    return {"saved": True}


@router.delete("/{entity_id}")
async def remove_saved(entity_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    entity_id = validate_path_id(entity_id, "entity_id")
    check_rate(f"saved:{user['id']}", 60, 300, "Thao tác lưu quá nhanh. Vui lòng thử lại sau.")
    def _query():
        ph = db._ph
        with db._conn() as conn:
            db._execute(conn, f"""
                DELETE FROM saved_entities WHERE user_id = {ph}::uuid AND entity_id = {ph}
            """, (str(user["id"]), entity_id))
    await asyncio.to_thread(_query)
    return {"saved": False}


@router.post("/merge")
async def merge_saved(body: MergeBody, user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"saved-merge:{user['id']}", 10, 300, "Đồng bộ quá nhanh. Vui lòng thử lại sau.")
    uid = str(user["id"])
    items = (body.items or [])[:500]
    def _query():
        with db._conn() as conn:
            ph = db._ph
            for it in items:
                if it.id:
                    _upsert(conn, uid, it)
            cnt_row = db._fetchone(conn, f"SELECT COUNT(*) c FROM saved_entities WHERE user_id = {ph}::uuid", (uid,))
            total = int(db._row_to_dict(cnt_row)["c"]) if cnt_row else 0
            if total > MAX_SAVED:
                db._execute(conn, f"""
                    DELETE FROM saved_entities WHERE id IN (
                        SELECT id FROM saved_entities
                        WHERE user_id = {ph}::uuid
                        ORDER BY created_at ASC
                        LIMIT {ph}
                    )
                """, (uid, total - MAX_SAVED))
            return {"items": _list(conn, uid)}
    return await asyncio.to_thread(_query)
