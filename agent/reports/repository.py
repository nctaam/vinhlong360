"""Persistence for reports, using the existing database adapter."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from .models import ReportActor, ReportCreate, ReportRecord, ReportStatus, ReportTargetType


def _row_dict(database, row) -> dict[str, Any] | None:
    return None if row is None else database._row_to_dict(row)


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class ReportRepository:
    def __init__(self, database):
        self.db = database
        self._ensure_sqlite_schema()

    def _ensure_sqlite_schema(self) -> None:
        if getattr(self.db, "_use_pg", False):
            return
        with self.db._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    reporter_id TEXT,
                    target_type TEXT NOT NULL CHECK (target_type IN ('post','comment','user','entity','facility','stale_field')),
                    target_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','reviewed','dismissed','resolved')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    actor_scope TEXT,
                    reporter_hash TEXT,
                    detail TEXT NOT NULL DEFAULT '',
                    contact_ciphertext TEXT,
                    field TEXT,
                    revision INTEGER NOT NULL DEFAULT 1,
                    idempotency_key TEXT,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    resolved_by TEXT,
                    resolved_at TEXT,
                    correlation_id TEXT,
                    source_channel TEXT NOT NULL DEFAULT 'web',
                    legacy_locator TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_actor_idempotency
                    ON reports(actor_scope, idempotency_key);
                CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_legacy_locator
                    ON reports(legacy_locator);
                CREATE INDEX IF NOT EXISTS idx_reports_target_status
                    ON reports(target_type, target_id, status);
                """
            )

    def _target_query(self, target_type: ReportTargetType, target_id: str) -> tuple[str, tuple[Any, ...]]:
        ph = self.db._ph
        target_id = str(target_id)
        id_expr = "id::text" if getattr(self.db, "_use_pg", False) else "id"
        if target_type in {ReportTargetType.ENTITY, ReportTargetType.FACILITY, ReportTargetType.STALE_FIELD}:
            return f"SELECT id FROM entities WHERE id = {ph}", (target_id,)
        if target_type is ReportTargetType.POST:
            suffix = " AND deleted_at IS NULL" if getattr(self.db, "_use_pg", False) else " AND COALESCE(deleted_at, '') = ''"
            return f"SELECT id FROM posts WHERE {id_expr} = {ph}{suffix}", (target_id,)
        if target_type is ReportTargetType.COMMENT:
            suffix = " AND deleted_at IS NULL" if getattr(self.db, "_use_pg", False) else " AND COALESCE(deleted_at, '') = ''"
            return f"SELECT id FROM comments WHERE {id_expr} = {ph}{suffix}", (target_id,)
        return f"SELECT id FROM users WHERE {id_expr} = {ph} AND is_active = TRUE", (target_id,)

    def target_exists(self, target_type: ReportTargetType, target_id: str) -> bool:
        sql, params = self._target_query(target_type, target_id)
        try:
            with self.db._conn() as conn:
                return self.db._fetchone(conn, sql, params) is not None
        except Exception as exc:
            # A missing optional UGC table is equivalent to a missing target on
            # SQLite; the canonical service still returns a stable 404.
            if not getattr(self.db, "_use_pg", False) and "no such table" in str(exc).lower():
                return False
            raise

    def _select(self, conn, report_id: str | None = None, *, actor_scope: str | None = None, idempotency_key: str | None = None):
        ph = self.db._ph
        id_expr = "id::text" if getattr(self.db, "_use_pg", False) else "id"
        if report_id is not None:
            sql = f"SELECT * FROM reports WHERE {id_expr} = {ph}"
            return self.db._fetchone(conn, sql, (str(report_id),))
        sql = f"SELECT * FROM reports WHERE actor_scope = {ph} AND idempotency_key = {ph}"
        return self.db._fetchone(conn, sql, (actor_scope, idempotency_key))

    def _record(self, row, *, replayed: bool = False) -> ReportRecord:
        item = _row_dict(self.db, row)
        return ReportRecord(
            report_id=str(item["id"]),
            target_id=str(item["target_id"]),
            target_type=ReportTargetType(str(item["target_type"])),
            reason=str(item["reason"]),
            status=ReportStatus(str(item["status"])),
            actor_scope=str(item.get("actor_scope") or "legacy"),
            reporter_id=str(item["reporter_id"]) if item.get("reporter_id") is not None else None,
            reporter_hash=item.get("reporter_hash"),
            detail=str(item.get("detail") or ""),
            contact_ciphertext=item.get("contact_ciphertext"),
            field=item.get("field"),
            revision=int(item.get("revision") or 1),
            idempotency_key=item.get("idempotency_key"),
            created_at=_parse_time(item.get("created_at")),
            updated_at=_parse_time(item.get("updated_at") or item.get("created_at")),
            resolved_by=str(item["resolved_by"]) if item.get("resolved_by") is not None else None,
            resolved_at=_parse_time(item["resolved_at"]) if item.get("resolved_at") else None,
            correlation_id=item.get("correlation_id"),
            source_channel=str(item.get("source_channel") or "legacy"),
            legacy_locator=item.get("legacy_locator"),
            replayed=replayed,
        )

    def create(self, request: ReportCreate, *, actor: ReportActor, idempotency_key: str, correlation_id: str) -> ReportRecord:
        self._ensure_sqlite_schema()
        now = datetime.now(timezone.utc)
        ph = self.db._ph
        report_id = str(uuid.uuid4())
        # Never persist a raw contact value.  The current authority retains a
        # deterministic digest until a deployment supplies envelope encryption.
        contact_ciphertext = None
        if request.contact:
            contact_ciphertext = "sha256:" + hashlib.sha256(request.contact.encode("utf-8")).hexdigest()
        insert_sql = f"""
            INSERT INTO reports (
                id, reporter_id, target_type, target_id, reason, status,
                actor_scope, reporter_hash, detail, contact_ciphertext, field,
                revision, idempotency_key, updated_at, correlation_id,
                source_channel, legacy_locator
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'pending', {ph}, {ph}, {ph}, {ph}, {ph}, 1, {ph}, {ph}, {ph}, {ph}, {ph})
        """
        params = (
            report_id,
            actor.reporter_id,
            request.target_type.value,
            request.target_id.strip(),
            request.reason.strip(),
            actor.actor_scope,
            actor.reporter_hash,
            request.detail.strip(),
            contact_ciphertext,
            request.field,
            idempotency_key,
            now,
            correlation_id,
            actor.source_channel,
            request.legacy_locator,
        )
        with self.db._conn() as conn:
            if self.db._use_pg:
                sql = insert_sql.replace(
                    ")\n        ", ")\n        ON CONFLICT (actor_scope, idempotency_key) DO NOTHING\n        "
                )
            else:
                sql = insert_sql.replace(
                    ")\n        ", ")\n        ON CONFLICT(actor_scope, idempotency_key) DO NOTHING\n        "
                )
            self.db._execute(conn, sql, params)
            row = self._select(conn, actor_scope=actor.actor_scope, idempotency_key=idempotency_key)
            if row is None:
                raise RuntimeError("report_insert_failed")
            existing = str((_row_dict(self.db, row) or {}).get("id")) != report_id
            return self._record(row, replayed=existing)

    def get(self, report_id: str) -> ReportRecord | None:
        with self.db._conn() as conn:
            row = self._select(conn, report_id=report_id)
        return self._record(row) if row else None

    def list(self, *, limit: int = 100) -> list[ReportRecord]:
        self._ensure_sqlite_schema()
        limit = max(1, min(int(limit), 500))
        with self.db._conn() as conn:
            rows = self.db._fetchall(
                conn,
                f"SELECT * FROM reports ORDER BY created_at DESC, id DESC LIMIT {self.db._ph}",
                (limit,),
            )
        return [self._record(row) for row in rows]

    def transition(self, report_id: str, *, expected_revision: int, status: ReportStatus, actor: ReportActor, reason: str) -> ReportRecord:
        self._ensure_sqlite_schema()
        ph = self.db._ph
        now = datetime.now(timezone.utc)
        resolved = status in {ReportStatus.RESOLVED, ReportStatus.DISMISSED}
        sql = f"""
            UPDATE reports
            SET status = {ph}, revision = revision + 1, updated_at = {ph},
                resolved_by = {ph}, resolved_at = {ph}, reason = CASE WHEN {ph} <> '' THEN {ph} ELSE reason END
            WHERE {('id::text' if getattr(self.db, '_use_pg', False) else 'id')} = {ph} AND revision = {ph}
        """
        params = (
            status.value,
            now,
            actor.actor_scope if resolved else None,
            now if resolved else None,
            reason.strip(),
            reason.strip(),
            str(report_id),
            int(expected_revision),
        )
        with self.db._conn() as conn:
            cur = self.db._execute(conn, sql, params)
            if int(getattr(cur, "rowcount", 0) or 0) != 1:
                row = self._select(conn, report_id=report_id)
                if row is None:
                    raise LookupError("report_not_found")
                raise RuntimeError("report_revision_conflict")
            row = self._select(conn, report_id=report_id)
        return self._record(row)
