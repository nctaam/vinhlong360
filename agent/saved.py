"""
saved.py — Saved entities (favorites) synced to the user account (P1).

Lets a logged-in user's saved places follow them across devices. Entity ids
are slugs (TEXT). A lightweight `snapshot` (name/type/image…) is stored so a new
device can render saved cards without fetching each entity. Postgres-only
(UGC parity); returns 503 on SQLite dev, like the rest of the social layer.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_middleware import require_user
from database import db


def _require_pg():
    if not db._use_pg:
        raise HTTPException(status_code=503, detail="Tính năng cần Postgres (không khả dụng ở chế độ SQLite).")


router = APIRouter(prefix="/api/saved", tags=["saved"], dependencies=[Depends(_require_pg)])


class SavedItem(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    place_name: Optional[str] = None
    place_area: Optional[str] = None
    summary: Optional[str] = None
    image: Optional[str] = None


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
    with db._conn() as conn:
        return {"items": _list(conn, str(user["id"]))}


@router.post("")
async def add_saved(item: SavedItem, user=Depends(require_user)):
    with db._conn() as conn:
        _upsert(conn, str(user["id"]), item)
    return {"saved": True}


@router.delete("/{entity_id}")
async def remove_saved(entity_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            DELETE FROM saved_entities WHERE user_id = {ph}::uuid AND entity_id = {ph}
        """, (str(user["id"]), entity_id))
    return {"saved": False}


@router.post("/merge")
async def merge_saved(body: MergeBody, user=Depends(require_user)):
    """Merge local (device) favorites into the account on login; returns the
    full merged list (account is the union — nothing is dropped)."""
    uid = str(user["id"])
    items = (body.items or [])[:500]
    with db._conn() as conn:
        for it in items:
            if it.id:
                _upsert(conn, uid, it)
        return {"items": _list(conn, uid)}
