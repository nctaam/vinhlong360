"""
vinhlong360 — image suggestion REVIEW QUEUE (P2, review-gated).

Human-in-the-loop store for LEGACY image candidates (old ingest pipeline —
now STOPPED/banned; new images are AI-generated only, CLAUDE.md §1.5).
NOTHING is auto-published: fuzzy name-matching is wrong
~50% of the time, so every candidate waits in `pending` until an admin approves
or rejects it on /admin/duyet-anh.

Why a standalone helper (not database.py):
  - additive + low-risk: keeps the queue self-contained, no edits to the core
    Database class. Reuses the existing connection/param primitives on `db`.
  - In Postgres (prod), the table is created by migrations/005_image_suggestions.sql.
  - In SQLite (dev), `database.initialize()` does not know this table, so we create
    it lazily here (idempotent CREATE TABLE IF NOT EXISTS) on first use.

All SQL goes through db._conn / db._ph / db._execute / db._fetchall so the same
code works on both backends.

Constitution:
  - B6: license + author + source captured per candidate; carried onto the entity
    on approve (attributes.image_credits). No re-host without attribution.
  - B8: pure DB; no LLM, no paid service.
  - Track-H / §1.4: review-gated, admin-only; no fabricated data, no booking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from database import db

VALID_STATUSES = ("pending", "approved", "rejected")

_table_ready = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_table() -> None:
    """Lazily create the table on SQLite dev (Postgres prod uses the migration).

    Idempotent. The `IF NOT EXISTS` guard means this is a no-op if the migration
    already created the table; we only run the SQLite-flavoured DDL on SQLite.
    """
    global _table_ready
    if _table_ready:
        return
    db.initialize()
    if not db._use_pg:
        with db._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS image_suggestions (
                    id               TEXT PRIMARY KEY,
                    entity_id        TEXT NOT NULL,
                    candidate_url    TEXT NOT NULL,
                    wp_title         TEXT DEFAULT '',
                    license          TEXT DEFAULT '',
                    author           TEXT DEFAULT '',
                    source           TEXT DEFAULT 'wikipedia-vi',
                    match_confidence REAL DEFAULT 0.7,
                    status           TEXT NOT NULL DEFAULT 'pending',
                    rejection_reason TEXT DEFAULT '',
                    approved_by      TEXT DEFAULT '',
                    approved_at      TEXT,
                    created_at       TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_image_suggestions_status
                    ON image_suggestions(status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_image_suggestions_entity
                    ON image_suggestions(entity_id);
                """
            )
    _table_ready = True


def _to_dict(row) -> dict:
    d = db._row_to_dict(row)
    if d is None:
        return None
    # Normalise types for JSON response (timestamps → str, confidence → float).
    if d.get("created_at") is not None:
        d["created_at"] = str(d["created_at"])
    if d.get("approved_at") is not None:
        d["approved_at"] = str(d["approved_at"])
    if d.get("match_confidence") is not None:
        try:
            d["match_confidence"] = float(d["match_confidence"])
        except (TypeError, ValueError):
            pass
    return d


def _clean_suggestion(s) -> Optional[tuple[str, str]]:
    """Validate one raw suggestion item; return (entity_id, candidate_url) or None.

    Returns None for anything that must be skipped: non-dict, missing
    entity_id/candidate_url, or a non-http(s) URL. Verbatim extraction of the
    original guard clauses in create_batch's loop body.
    """
    if not isinstance(s, dict):
        return None
    entity_id = (s.get("entity_id") or "").strip()
    candidate_url = (s.get("candidate_url") or s.get("url") or s.get("image") or "").strip()
    if not entity_id or not candidate_url:
        return None
    if not candidate_url.startswith(("http://", "https://")):
        return None
    return entity_id, candidate_url


def _pending_exists(conn, entity_id: str, candidate_url: str) -> bool:
    """De-dupe check: is there already an identical PENDING suggestion row?"""
    ph = db._ph
    existing = db._fetchone(
        conn,
        f"SELECT 1 FROM image_suggestions WHERE entity_id = {ph} AND candidate_url = {ph} AND status = 'pending'",
        (entity_id, candidate_url),
    )
    return bool(existing)


def _insert_suggestion(conn, s: dict, entity_id: str, candidate_url: str) -> str:
    """Insert one validated suggestion (status=pending); return its new id.

    Verbatim extraction of the sid/conf/INSERT block from create_batch's loop.
    """
    ph = db._ph
    sid = uuid.uuid4().hex
    try:
        conf = float(s.get("match_confidence", 0.7))
    except (TypeError, ValueError):
        conf = 0.7
    db._execute(
        conn,
        f"""INSERT INTO image_suggestions
            (id, entity_id, candidate_url, wp_title, license, author, source, match_confidence, status)
            VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},'pending')""",
        (
            sid, entity_id, candidate_url,
            (s.get("wp_title") or "")[:200],
            (s.get("license") or "")[:80],
            (s.get("author") or s.get("artist") or "")[:120],
            (s.get("source") or "wikipedia-vi")[:40],
            conf,
        ),
    )
    return sid


def _process_one_suggestion(conn, s) -> Optional[str]:
    """Validate + de-dupe + insert a single suggestion.

    Returns the new suggestion id when a row was inserted, or None when the
    item was skipped (invalid or duplicate). Verbatim per-item body of
    create_batch's original loop.
    """
    cleaned = _clean_suggestion(s)
    if cleaned is None:
        return None
    entity_id, candidate_url = cleaned
    if _pending_exists(conn, entity_id, candidate_url):
        return None
    return _insert_suggestion(conn, s, entity_id, candidate_url)


def create_batch(suggestions: list[dict]) -> dict:
    """Insert a batch of candidate suggestions (status=pending).

    Each item: {entity_id, candidate_url, wp_title?, license?, author?, source?,
                match_confidence?}. Items missing entity_id/candidate_url are skipped.
    De-dupes against existing PENDING rows with the same (entity_id, candidate_url)
    so re-running an ingest does not pile up duplicates.

    Returns {"created": n, "skipped": n, "ids": [...]}.
    """
    _ensure_table()
    created, skipped, ids = 0, 0, []
    with db._conn() as conn:
        for s in suggestions or []:
            sid = _process_one_suggestion(conn, s)
            if sid is None:
                skipped += 1
                continue
            created += 1
            ids.append(sid)
    return {"created": created, "skipped": skipped, "ids": ids}


def list_suggestions(status: Optional[str] = None, entity_id: Optional[str] = None,
                     limit: int = 50, offset: int = 0) -> dict:
    """Paginated list with optional status/entity filters. Joins entity name for context."""
    _ensure_table()
    ph = db._ph
    conditions, params = ["1=1"], []
    if status:
        conditions.append(f"s.status = {ph}")
        params.append(status)
    if entity_id:
        conditions.append(f"s.entity_id = {ph}")
        params.append(entity_id)
    where = " AND ".join(conditions)
    with db._conn() as conn:
        rows = db._fetchall(
            conn,
            f"""SELECT s.*, e.name AS entity_name, e.type AS entity_type, e.images AS entity_images
                FROM image_suggestions s
                LEFT JOIN entities e ON e.id = s.entity_id
                WHERE {where}
                ORDER BY s.created_at DESC
                LIMIT {ph} OFFSET {ph}""",
            (*params, limit, offset),
        )
        total_row = db._fetchone(
            conn,
            f"SELECT COUNT(*) AS c FROM image_suggestions s WHERE {where}",
            tuple(params),
        )
    items = [_to_dict(r) for r in rows]
    total = (db._row_to_dict(total_row) or {}).get("c", 0) if total_row else 0
    return {"suggestions": items, "total": total, "limit": limit, "offset": offset}


def get_suggestion(suggestion_id: str) -> Optional[dict]:
    _ensure_table()
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(
            conn,
            f"""SELECT s.*, e.name AS entity_name, e.type AS entity_type, e.images AS entity_images
                FROM image_suggestions s
                LEFT JOIN entities e ON e.id = s.entity_id
                WHERE s.id = {ph}""",
            (suggestion_id,),
        )
    return _to_dict(row) if row else None


def status_counts() -> dict:
    """Counts grouped by status (for review-page badges)."""
    _ensure_table()
    with db._conn() as conn:
        rows = db._fetchall(conn, "SELECT status, COUNT(*) AS c FROM image_suggestions GROUP BY status")
    out = {"pending": 0, "approved": 0, "rejected": 0}
    for r in rows:
        d = db._row_to_dict(r)
        out[d["status"]] = d["c"]
    return out


def mark_status(suggestion_id: str, status: str, approved_by: str = "",
                rejection_reason: str = "") -> bool:
    """Transition a suggestion to approved/rejected. Returns False if not found.

    Guards against re-processing: caller should check current status == 'pending'
    first (the approve/reject endpoints do). This only writes the new state.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}")
    _ensure_table()
    ph = db._ph
    with db._conn() as conn:
        cur = db._execute(
            conn,
            f"""UPDATE image_suggestions
                SET status = {ph}, approved_by = {ph}, rejection_reason = {ph}, approved_at = {ph}
                WHERE id = {ph}""",
            (status, approved_by or "", rejection_reason or "", _now_iso(), suggestion_id),
        )
        try:
            affected = cur.rowcount
        except Exception:
            affected = None
    if affected is None:
        # SQLite path returns a cursor with rowcount; fall back to existence check.
        return get_suggestion(suggestion_id) is not None
    return affected > 0
