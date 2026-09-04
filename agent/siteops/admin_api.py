# -*- coding: utf-8 -*-
"""Miền VẬN HÀNH SITE (siteops) — mặt QUẢN TRỊ. Bóc khỏi `admin.py` (2026-08-29,
lát 3 đợt hoàn-thiện-sâu; hồ sơ đo: journal wf_3f293d24-0a1, kết quả siteops).

Gói HAI MẶT theo khuôn `agent/cases/`/`entities/`/`community/`/`itineraries/`:
mặt công khai ở `siteops/api.py` (2 route đọc), đây là 22 route quản trị vận
hành site: data-quality ×6 · system-health · backup-status · ops-summary ·
backup-trigger · export toàn-DB · site-settings ×7 · announcements ×4 —
bao đóng bắc cầu, di chuyển NGUYÊN VĂN. Hai chỉnh MÁY MÓC duy nhất, ghi
chú tại chỗ: (a) đường dẫn tương-đối-__file__ sâu thêm một cấp thư mục
(admin.py → siteops/admin_api.py) nên parent-count +1; (b) hạ tầng audit
(_AUDIT_FILE/_query_admin_audit_db) Ở LẠI admin.py — lấy qua import LƯỜI
trong thân hàm (tiền lệ llmops/api.py).

Hai handler nhạy B1/B7 (`trigger_backup` chạy subprocess scripts/backup_data.py;
`data_quality_apply`/`data_quality_rollback` mutate DB qua data_quality) —
thân hàm giữ nguyên văn, KHÔNG refactor luồng.

Mount qua `admin.router.include_router(...)` TRƯỚC `_fix_admin_route_order()`:
- cổng R20.9 chỉ nhìn thấy mount qua lời gọi include_router;
- router cha mang prefix "/admin" VÀ dependencies [require_admin, require_csrf]
  — router này KHÔNG tự mang cả hai, kế thừa từ cha khi include (kiểm bằng
  đo runtime trong test ranh giới, không tin trí nhớ API).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

import data_quality
import site_settings
from admin_common import _require_admin_actor_id, _safe, _sync_kb
from auth_middleware import require_pg, validate_path_id
from config import settings as _cfg
from database import db

from control_plane.concurrency import IdempotencyKey, claim_idempotency, record_idempotency_receipt
try:
    from backup_manifest import find_latest_manifest
except ImportError:
    from scripts.backup_manifest import find_latest_manifest

logger = logging.getLogger("admin")

# admin.py dùng ROOT = parent.parent (agent/admin.py → gốc repo); file này sâu
# thêm một cấp nên parents[2] mới ra đúng gốc repo.
ROOT = Path(__file__).resolve().parents[2]

try:
    from cost_tracker import get_cost_report as _get_cost_report
    _HAS_COST = True
except Exception:  # noqa: BLE001
    logger.warning("Cost tracker unavailable", exc_info=True)
    _HAS_COST = False

router = APIRouter(tags=["admin-siteops"])


# ── Models ──

class DataQualityApplyRequest(BaseModel):
    candidate_ids: list[str] | None = Field(None, max_length=500)
    dry_run: bool = True

class DataQualityDecisionRequest(BaseModel):
    candidate_ids: list[str] = Field(..., min_length=1, max_length=200)
    decision: str = Field(..., pattern="^(approve|reject|defer)$")
    note: str = Field("", max_length=1000)
    apply: bool = False


# Data quality review queue

@router.get("/data-quality/summary",
            summary="Get data quality summary",
            description="Returns an overview of data quality metrics including candidate counts, stream counts, and sitemap expectations.")
async def data_quality_summary(refresh: bool = Query(False)):
    def _query():
        data_summary = data_quality.summarize_data()
        queue = data_quality.load_candidate_queue(refresh=refresh)
        return {
            "data": data_summary,
            "candidates": queue.get("counts", {}),
            "stream_counts": queue.get("stream_counts", {}),
            "cache": queue.get("cache", {}),
            "sitemap": {
                "expected_public_detail_urls": data_summary["public_entities"],
                "expected_itinerary_urls": data_summary["itineraries"],
                "expected_public_content_urls": data_summary["public_entities"] + data_summary["itineraries"],
            },
            "policy": queue.get("policy", {}),
        }
    return await asyncio.to_thread(_query)

@router.get("/data-quality/review",
            summary="Review data quality candidates",
            description="Returns filterable data quality improvement candidates. Supports filtering by kind, bucket, and pagination.")
async def data_quality_review(
    kind: Optional[str] = Query(None, pattern="^(source|location|placeid|accuracy|relationship)$"),
    bucket: Optional[str] = Query(None, pattern="^(auto_apply|needs_review|reject)$"),
    refresh: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
):
    def _query():
        queue = data_quality.load_candidate_queue(refresh=refresh)
        result = data_quality.filter_candidates(queue, kind=kind, bucket=bucket, limit=limit, offset=offset)
        result["cache"] = queue.get("cache", {})
        return result
    return await asyncio.to_thread(_query)

@router.post("/data-quality/apply",
             summary="Apply data quality improvements",
             description="Applies selected data quality candidates to entities. Supports dry-run mode for preview.")
async def data_quality_apply(body: DataQualityApplyRequest):
    def _query():
        result = data_quality.apply_candidates(body.candidate_ids, dry_run=body.dry_run)
        if result.get("applied_count") and not body.dry_run:
            _sync_kb()
        return result
    return await asyncio.to_thread(_query)

@router.get("/data-quality/history",
            summary="Get data quality apply history",
            description="Returns the history of applied data quality batches, ordered by most recent first.")
async def data_quality_history(limit: int = Query(20, ge=1, le=200)):
    result = await asyncio.to_thread(data_quality.load_apply_history, limit=limit)
    decisions = await asyncio.to_thread(data_quality.load_decision_history, limit=limit)
    result["decisions"] = decisions.get("decisions", [])
    result["decision_total"] = decisions.get("total", 0)
    return result

@router.post("/data-quality/decision",
             summary="Record data quality review decision",
             description="Records approve, reject, or defer decisions for data-quality candidates. Approved candidates can optionally be applied immediately.")
async def data_quality_decision(body: DataQualityDecisionRequest, request: Request):
    reviewer = _require_admin_actor_id(request)
    try:
        result = await asyncio.to_thread(
            data_quality.decide_candidates,
            body.candidate_ids,
            decision=body.decision,
            note=body.note,
            reviewer=reviewer,
            apply=body.apply,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result

@router.post("/data-quality/rollback/{batch_id}",
             summary="Rollback data quality batch",
             description="Reverts all changes from a previously applied data quality batch by restoring original entity data.")
async def data_quality_rollback(batch_id: str):
    validate_path_id(batch_id, "batch_id")
    def _query():
        try:
            result = data_quality.rollback_apply(batch_id)
        except ValueError:
            raise HTTPException(400, detail="Batch ID không hợp lệ")
        except FileNotFoundError:
            raise HTTPException(404, detail="Không tìm thấy batch")
        _sync_kb()
        return result
    return await asyncio.to_thread(_query)


# ── System health ──

_server_start_time = __import__("time").time()


def _system_health_server(result, os, _t) -> None:
    result["server"]["uptime_seconds"] = int(_t.time() - _server_start_time)
    result["server"]["uptime_human"] = _format_uptime(int(_t.time() - _server_start_time))
    result["server"]["pid"] = os.getpid()
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        result["server"]["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
    except (ImportError, Exception):
        result["server"]["memory_mb"] = -1


def _system_health_pg_connection_degraded(result) -> None:
    """Keep health reporting useful when PostgreSQL cannot be opened."""
    result["postgres"].update({
        "tables": {},
        "size_mb": -1,
        "active_sessions": -1,
        "pending_moderation": -1,
        "open_reports": -1,
        "degraded_checks": ["connection"],
    })


def _system_health_pg(result) -> None:
    try:
        with db._conn() as conn:
            _system_health_pg_queries(result, conn)
    except Exception:
        # A health endpoint must report an unavailable database, not become
        # unavailable itself because opening the diagnostic connection failed.
        _system_health_pg_connection_degraded(result)


def _system_health_pg_queries(result, conn) -> None:
    # Keep the legacy response key while querying the schema's authority table.
    # The identity subsystem owns ``user_sessions``; ``sessions`` is not a
    # PostgreSQL table in this deployment.
    tables = ["users", "posts", "comments", "likes", "follows",
              "notifications", "blocks", ("sessions", "user_sessions"),
              "user_visits", "reports", "saved_entities", "announcements"]
    pg_tables = {}
    degraded_checks = []
    for entry in tables:
        display_name, table_name = (entry if isinstance(entry, tuple)
                                    else (entry, entry))
        try:
            row = db._fetchone(conn, f"SELECT COUNT(*) as c FROM {table_name}", ())
            pg_tables[display_name] = db._row_to_dict(row)["c"] if row else 0
        except Exception:
            pg_tables[display_name] = -1
            degraded_checks.append(f"table:{display_name}")
    result["postgres"]["tables"] = pg_tables
    try:
        size_row = db._fetchone(conn, """
            SELECT pg_database_size(current_database()) as s
        """, ())
        result["postgres"]["size_mb"] = round(db._row_to_dict(size_row)["s"] / 1024 / 1024, 2) if size_row else 0
    except Exception:
        result["postgres"]["size_mb"] = -1
        degraded_checks.append("database_size")
    for metric_name, query in (
        ("active_sessions", """
            SELECT COUNT(*) as c FROM user_sessions WHERE expires_at > NOW()
        """),
        ("pending_moderation", """
            SELECT COUNT(*) as c FROM posts WHERE moderation_status = 'pending'
        """),
        ("open_reports", """
            SELECT COUNT(*) as c FROM reports WHERE status = 'pending'
        """),
    ):
        try:
            row = db._fetchone(conn, query, ())
            result["postgres"][metric_name] = db._row_to_dict(row)["c"] if row else 0
        except Exception:
            # One optional metric must not turn the entire health endpoint
            # into a 500; -1 plus a named degradation is explicit.
            result["postgres"][metric_name] = -1
            degraded_checks.append(metric_name)
    result["postgres"]["degraded_checks"] = sorted(set(degraded_checks))


@router.get("/system-health",
            summary="Get system health status",
            description="Returns system health information including SQLite/Postgres status, server uptime, memory usage, and storage metrics.")
async def system_health():
    import os
    import time as _t
    def _query():
        result = {"sqlite": {}, "postgres": {}, "server": {}}
        _system_health_server(result, os, _t)
        # Chỉnh máy móc khi đổi nhà admin.py → siteops/: agent/data/ nay là
        # ROOT/"agent"/"data" (dirname(__file__) cũ trỏ agent/, nay trỏ siteops/).
        db_path = os.path.join(str(ROOT / "agent"), "data", "knowledge.db")
        if os.path.exists(db_path):
            result["sqlite"]["size_mb"] = round(os.path.getsize(db_path) / 1024 / 1024, 2)
            result["sqlite"]["entities"] = sum(db.count_entities().values())
        if db._use_pg:
            _system_health_pg(result)
        data_dir = ROOT / "agent" / "data"  # chỉnh máy móc cùng lý do dòng trên
        jsonl_files = list(data_dir.glob("*.jsonl"))
        result["storage"] = {
            "jsonl_files": len(jsonl_files),
            "jsonl_size_mb": round(sum(f.stat().st_size for f in jsonl_files) / 1024 / 1024, 2),
        }
        return result
    return await asyncio.to_thread(_query)


def _format_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


# ── Backup status + ops cockpit ──

def _backup_missing_info() -> dict:
    return {
        "ready": False,
        "latest": None,
        "count": 0,
        "size_mb": 0,
        "state": "missing",
        "last_success": None,
        "last_failure": None,
        "artifact_id": None,
        "stale": True,
    }


def _backup_dirs(backup_dir: Path) -> list[Path]:
    return sorted(
        [path for path in backup_dir.iterdir() if path.is_dir()],
        key=lambda path: path.name,
        reverse=True,
    )


def _backup_size_mb(path: Path) -> float:
    return round(sum(file.stat().st_size for file in path.rglob("*") if file.is_file()) / 1048576, 1)


def _backup_manifest(path: Path) -> dict:
    try:
        value = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _backup_is_latest(backup_dir: Path, latest: Path) -> bool:
    try:
        normalized = find_latest_manifest(backup_dir)
    except Exception:
        return False
    return normalized is not None and normalized[0] == latest


def _backup_is_stale(created_at: object) -> bool:
    if not created_at:
        return True
    try:
        parsed = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return True
    return (datetime.now(timezone.utc) - parsed).total_seconds() > 86400


def _backup_failure_info(
    latest: Path, count: int, size_mb: float, created_at: object, artifact_id: str
) -> dict:
    return {
        "ready": False,
        "latest": latest.name,
        "count": count,
        "size_mb": size_mb,
        "state": "failure",
        "last_success": None,
        "last_failure": created_at,
        "artifact_id": artifact_id,
        "stale": True,
    }


def _latest_backup_info() -> dict:
    backup_dir = ROOT / "scratch" / "backups"
    if not backup_dir.exists():
        return _backup_missing_info()
    dirs = _backup_dirs(backup_dir)
    if not dirs:
        return _backup_missing_info()
    latest = dirs[0]
    size_mb = _backup_size_mb(latest)
    manifest = _backup_manifest(latest)
    created_at = manifest.get("created_at") or manifest.get("completed_at")
    artifact_id = manifest.get("artifact_id") or latest.name
    if not _backup_is_latest(backup_dir, latest):
        return _backup_failure_info(latest, len(dirs), size_mb, created_at, artifact_id)
    stale = _backup_is_stale(created_at)
    return {
        "ready": True,
        "latest": latest.name,
        "count": len(dirs),
        "size_mb": size_mb,
        "state": "stale" if stale else "success",
        "last_success": created_at,
        "last_failure": None,
        "artifact_id": artifact_id,
        "stale": stale,
    }


@router.get("/backup-status",
            summary="Get latest backup status",
            description="Returns a thin snapshot of the latest local backup (readiness, name, count, size) — same info already surfaced inside /admin/stats and /admin/ops-summary, exposed standalone for lightweight polling.")
async def backup_status():
    """B5c: route mỏng bọc _latest_backup_info() — không thêm logic mới."""
    status = await asyncio.to_thread(_latest_backup_info)
    return {"backup": status, **status}


def _data_quality_ops_snapshot() -> dict:
    queue_path = data_quality.BURST_DIR / data_quality.QUEUE_FILE
    counts = {"auto_apply": 0, "needs_review": 0, "reject": 0}
    stream_counts = {}
    cache = {"exists": queue_path.exists(), "path": str(queue_path)}
    policy = {}
    if queue_path.exists():
        try:
            queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
            for bucket in counts:
                counts[bucket] = len(queue.get(bucket, []) or [])
            stream_counts = queue.get("stream_counts", {}) or {}
            policy = queue.get("policy", {}) or {}
            stat = queue_path.stat()
            cache.update({
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            })
        except Exception:
            logger.debug("ops data-quality queue read failed", exc_info=True)
            cache["error"] = "read_failed"
    decisions = _safe(lambda: data_quality.load_decision_history(limit=20), {"total": 0, "decisions": []})
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "stream_counts": stream_counts,
        "cache": cache,
        "policy": policy,
        "decision_total": decisions.get("total", 0),
        "recent_decisions": decisions.get("decisions", [])[:5],
    }

_QUALITY_TREND_KEYS = (
    "quality_score_avg",
    "image_coverage_pct",
    "place_coords_coverage_pct",
    "image_missing_credit",
    "image_missing_license",
    "image_missing_source",
    "duplicate_source_urls",
    "self_citation_pct",
)

def _quality_trend_meta(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _quality_trend_fetch_rows():
    """Return (latest_rows, baseline_rows, count_row) or None on failure/no-pg."""
    with db._conn() as conn:
        latest_rows = db._fetchall(conn, """
            SELECT DISTINCT ON (metric_key)
                metric_key, metric_value, metric_unit, metadata, created_at
            FROM quality_metric_snapshots
            WHERE metric_key = ANY(%s)
            ORDER BY metric_key, created_at DESC
        """, (list(_QUALITY_TREND_KEYS),))
        baseline_rows = db._fetchall(conn, """
            SELECT DISTINCT ON (metric_key)
                metric_key, metric_value, created_at
            FROM quality_metric_snapshots
            WHERE metric_key = ANY(%s)
              AND created_at <= NOW() - INTERVAL '7 days'
            ORDER BY metric_key, created_at DESC
        """, (list(_QUALITY_TREND_KEYS),))
        count_row = db._fetchone(conn, """
            SELECT COUNT(*) AS c
            FROM quality_metric_snapshots
            WHERE created_at > NOW() - INTERVAL '30 days'
        """, ())
    return latest_rows, baseline_rows, count_row


def _quality_trend_budget_failure(meta, key, value):
    """Return a budget-failure dict for this metric, or None when the budget is met/absent."""
    budget = meta.get("budget") if isinstance(meta, dict) else None
    if isinstance(budget, dict) and budget.get("ok") is False:
        return {
            "metric_key": key,
            "value": round(value, 2),
            "expected": budget.get("expected"),
            "op": budget.get("op"),
            "severity": budget.get("severity") or "error",
        }
    return None


def _quality_trend_process_latest(latest_rows):
    """Return (latest, budget_failures, last_recorded_at) from the latest snapshot rows."""
    latest: dict[str, dict] = {}
    budget_failures: list[dict] = []
    last_recorded_at = None
    for row in latest_rows:
        item = db._row_to_dict(row)
        key = str(item.get("metric_key"))
        value = float(item.get("metric_value") or 0)
        created = item.get("created_at")
        created_iso = created.isoformat(timespec="seconds") if hasattr(created, "isoformat") else str(created or "")
        meta = _quality_trend_meta(item.get("metadata"))
        latest[key] = {
            "value": round(value, 2),
            "unit": item.get("metric_unit") or "count",
            "created_at": created_iso,
        }
        if created_iso and (not last_recorded_at or created_iso > last_recorded_at):
            last_recorded_at = created_iso
        failure = _quality_trend_budget_failure(meta, key, value)
        if failure is not None:
            budget_failures.append(failure)
    return latest, budget_failures, last_recorded_at


def _quality_trend_ops_snapshot() -> dict:
    empty = {
        "available": False,
        "latest": {},
        "delta_7d": {},
        "budget_failures": [],
        "sample_count": 0,
        "last_recorded_at": None,
    }
    if not db._use_pg:
        return empty

    try:
        latest_rows, baseline_rows, count_row = _quality_trend_fetch_rows()
    except Exception:
        logger.debug("ops quality trend read failed", exc_info=True)
        return empty

    latest, budget_failures, last_recorded_at = _quality_trend_process_latest(latest_rows)

    baseline = {str(db._row_to_dict(row).get("metric_key")): float(db._row_to_dict(row).get("metric_value") or 0) for row in baseline_rows}
    delta_7d = {
        key: round(item["value"] - baseline[key], 2)
        for key, item in latest.items()
        if key in baseline
    }
    return {
        "available": bool(latest),
        "latest": latest,
        "delta_7d": delta_7d,
        "budget_failures": budget_failures,
        "sample_count": int(db._row_to_dict(count_row).get("c") or 0) if count_row else 0,
        "last_recorded_at": last_recorded_at,
    }

def _ops_moderation_snapshot() -> dict:
    moderation = {"pending": 0, "flagged": 0, "reports": 0, "appeals": 0, "oldest_pending_hours": None}
    if db._use_pg:
        with db._conn() as conn:
            pending = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status IN ('pending','review')", ())
            flagged = db._fetchone(conn, "SELECT COUNT(*) as c FROM posts WHERE moderation_status = 'flagged'", ())
            reports = db._fetchone(conn, "SELECT COUNT(*) as c FROM reports WHERE status = 'pending'", ())
            appeals = db._fetchone(conn, "SELECT COUNT(*) as c FROM moderation_appeals WHERE status = 'pending'", ())
            oldest = db._fetchone(conn, """
                SELECT EXTRACT(EPOCH FROM (NOW() - MIN(created_at))) / 3600 as h
                FROM posts WHERE moderation_status IN ('pending','review','flagged')
            """, ())
        moderation.update({
            "pending": int(db._row_to_dict(pending)["c"] if pending else 0),
            "flagged": int(db._row_to_dict(flagged)["c"] if flagged else 0),
            "reports": int(db._row_to_dict(reports)["c"] if reports else 0),
            "appeals": int(db._row_to_dict(appeals)["c"] if appeals else 0),
            "oldest_pending_hours": round(float(db._row_to_dict(oldest).get("h") or 0), 1) if oldest else None,
        })
    return moderation


def _ops_audit_snapshot() -> dict:
    # Hạ tầng audit (_AUDIT_FILE + _query_admin_audit_db + writer/rotation) Ở LẠI
    # admin.py — activity_feed/get_audit_log cùng dùng. Import LƯỜI trong thân hàm
    # (tiền lệ llmops/api.py): tránh vòng import cấp module, và bản vá test lên
    # admin.<tên> vẫn ăn tới ops_summary vì tên được phân giải lúc GỌI.
    from admin import _AUDIT_FILE, _query_admin_audit_db
    audit = {"jsonl_exists": _AUDIT_FILE.exists(), "db_available": False, "source": "jsonl", "recent_entries": 0, "last_ts": None}
    db_audit = _query_admin_audit_db(100)
    if db_audit is not None:
        audit["db_available"] = True
        audit["source"] = "db"
        audit["recent_entries"] = min(int(db_audit.get("total") or 0), 100)
        entries = db_audit.get("entries") or []
        if entries:
            audit["last_ts"] = entries[0].get("ts")
    if _AUDIT_FILE.exists():
        try:
            lines = [l for l in _AUDIT_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not audit["db_available"]:
                audit["recent_entries"] = min(len(lines), 100)
                if lines:
                    audit["last_ts"] = json.loads(lines[-1]).get("ts")
        except Exception:
            logger.debug("ops audit read failed", exc_info=True)
    return audit


@router.get("/ops-summary",
            summary="Get AdminCP operations summary",
            description="Returns release/deploy readiness, queue backlog, data-quality budgets, audit freshness, cost budget, and rollback readiness for the admin cockpit.")
async def ops_summary():
    """Ops cockpit snapshot: lightweight, read-only, no background jobs."""
    def _query():
        deploy_path = ROOT / "scripts" / "deploy.sh"
        gate_path = ROOT / "scripts" / "release_gate.ps1"
        deploy_text = deploy_path.read_text(encoding="utf-8", errors="ignore") if deploy_path.exists() else ""
        gate_text = gate_path.read_text(encoding="utf-8", errors="ignore") if gate_path.exists() else ""
        migrations = sorted((ROOT / "agent" / "migrations").glob("*.sql"))
        backup = _latest_backup_info()
        dq = _data_quality_ops_snapshot()
        quality_trend = _quality_trend_ops_snapshot()

        moderation = _ops_moderation_snapshot()
        audit = _ops_audit_snapshot()

        cost = _safe(lambda: _get_cost_report(), {}) if _HAS_COST else {}
        schema_status = db.pg_schema_status()
        shared_controls = {
            "rate_limit_enabled": os.environ.get("VL360_SHARED_RATE_LIMIT", "true").strip().lower() not in {"0", "false", "no", "off"},
            "idempotency_enabled": os.environ.get("VL360_SHARED_IDEMPOTENCY", "true").strip().lower() not in {"0", "false", "no", "off"},
            "tables_ready": bool(schema_status.get("ok")),
        }
        deploy_ready = all([
            "VL360_DEPLOY_HOST" in deploy_text,
            "/health/ready" in deploy_text,
            "exit 1" in deploy_text,
        ])
        gate_ready = all(token in gate_text for token in ("test_qa_fixes.py", "vue-tsc", "smoke_e2e_chrome.mjs", "check_migration_gate.py", "quality_budget.py"))
        release_state = {
            "gate_script": gate_path.exists(),
            "gate_covers_backend_frontend_e2e": gate_ready,
            "deploy_script": deploy_path.exists(),
            "deploy_host_env_configured": bool(os.environ.get("VL360_DEPLOY_HOST")),
            "deploy_health_blocking": deploy_ready,
            "latest_migration": migrations[-1].name if migrations else None,
            "migration_count": len(migrations),
            "schema_ok": bool(schema_status.get("ok")),
            "schema_version": schema_status.get("schema_version"),
            "required_schema_version": schema_status.get("required_schema_version"),
        }
        queue_backlog = {
            "moderation": moderation["pending"] + moderation["flagged"],
            "reports": moderation["reports"],
            "appeals": moderation["appeals"],
            "data_quality": dq["total"],
        }
        rollback = {
            "backup_ready": backup["ready"],
            "latest_backup": backup["latest"],
            "backup_count": backup["count"],
            "backup_size_mb": backup["size_mb"],
            "restore_drill_documented": (ROOT / "docs" / "deployment-guide.md").exists(),
            "restore_drill_script": (ROOT / "scripts" / "restore_drill.py").exists(),
        }
        quality_budget_ok = not quality_trend.get("budget_failures")
        status = "ok" if gate_ready and deploy_ready and backup["ready"] and schema_status.get("ok") and quality_budget_ok else "attention"
        return {
            "status": status,
            "release": release_state,
            "schema": schema_status,
            "shared_controls": shared_controls,
            "queues": queue_backlog,
            "moderation_sla": moderation,
            "data_quality": dq,
            "quality_trend": quality_trend,
            "audit": audit,
            "cost": cost,
            "rollback": rollback,
        }
    return await asyncio.to_thread(_query)



_last_backup_time: float = 0
_BACKUP_COOLDOWN = _cfg.BACKUP_COOLDOWN


class _BackupTransaction:
    def __init__(self, connection):
        self._db = db
        self._conn = connection


def _backup_request_context(request: Request | None) -> tuple[str | None, str]:
    idem_key = request.headers.get("Idempotency-Key") if request is not None else None
    actor = "admin"
    if request is not None:
        actor_data = getattr(request.state, "admin_user", None)
        if isinstance(actor_data, dict):
            actor = str(actor_data.get("id") or actor)
    return idem_key, actor


def _check_shared_backup_cooldown(transaction: _BackupTransaction) -> None:
    if not getattr(db, "_use_pg", False):
        return
    # Serialize the first-run case as well as existing sentinel rows;
    # SELECT ... FOR UPDATE cannot lock a row that does not exist.
    db._execute(
        transaction._conn,
        "SELECT pg_advisory_xact_lock(hashtext('vinhlong360:backup-trigger'))",
        (),
    )
    row = db._fetchone(
        transaction._conn,
        "SELECT meta FROM request_idempotency_keys WHERE key=%s FOR UPDATE",
        ("backup-trigger:__cooldown__",),
    )
    if row is None:
        return
    meta = row.get("meta") if isinstance(row, dict) else row[0]
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (TypeError, ValueError, json.JSONDecodeError):
            meta = {}
    completed = meta.get("completed_at") if isinstance(meta, dict) else None
    try:
        elapsed = datetime.now(timezone.utc).timestamp() - float(completed)
    except (TypeError, ValueError):
        return
    if elapsed < _BACKUP_COOLDOWN:
        raise HTTPException(429, f"Backup đã chạy gần đây. Thử lại sau {int(_BACKUP_COOLDOWN - elapsed)} giây.")


def _record_shared_backup_cooldown(transaction: _BackupTransaction) -> None:
    if not getattr(db, "_use_pg", False):
        return
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    meta = json.dumps({"completed_at": datetime.now(timezone.utc).timestamp()})
    db._execute(
        transaction._conn,
        "INSERT INTO request_idempotency_keys(key, expires_at, meta) VALUES (%s,%s,%s::jsonb) "
        "ON CONFLICT (key) DO UPDATE SET expires_at=EXCLUDED.expires_at, meta=EXCLUDED.meta",
        ("backup-trigger:__cooldown__", expires, meta),
    )


def _backup_request_hash(actor: str, idem_key: str) -> str:
    return hashlib.sha256(f"backup:{actor}:{idem_key}".encode()).hexdigest()


def _run_backup_process(script_path: Path):
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--label", "admin-manual"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("Backup script failed: %s", result.stderr)
            raise HTTPException(500, "Backup thất bại. Kiểm tra log server.")
        backup_dir = ROOT / "scratch" / "backups"  # chỉnh máy móc cùng lý do dòng script ở trên
        dirs = _backup_dirs(backup_dir)
        latest = dirs[0] if dirs else None
        normalized = find_latest_manifest(backup_dir)
        if latest is None or normalized is None or normalized[0] != latest:
            raise HTTPException(500, "Backup không tạo manifest/checksum hợp lệ")
        return {
            "success": True,
            "backup_name": latest.name if latest else None,
            "size_mb": _backup_size_mb(latest) if latest else 0,
            "output": result.stdout.strip(),
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Backup timed out")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Backup failed")
        raise HTTPException(500, "Backup thất bại. Kiểm tra log server.")


def _run_pg_backup(script: Path, actor: str, idem_key: str | None, now: float):
    global _last_backup_time
    with db._conn() as conn:
        transaction = _BackupTransaction(conn)
        claim = None
        if idem_key:
            request_hash = _backup_request_hash(actor, idem_key)
            claim = claim_idempotency(transaction, IdempotencyKey("backup-trigger", actor, idem_key), request_hash)
            if claim.replayed:
                return claim.receipt
            if claim.conflict:
                raise HTTPException(409, "Idempotency-Key đã dùng cho yêu cầu khác")
        _check_shared_backup_cooldown(transaction)
        result = _run_backup_process(script)
        if claim is not None:
            record_idempotency_receipt(transaction, claim, result)
        _record_shared_backup_cooldown(transaction)
        _last_backup_time = now
        return result


def _run_sqlite_idempotent_backup(script: Path, actor: str, idem_key: str, now: float):
    global _last_backup_time
    with db._conn() as conn:
        request_hash = _backup_request_hash(actor, idem_key)
        transaction = _BackupTransaction(conn)
        claim = claim_idempotency(transaction, IdempotencyKey("backup-trigger", actor, idem_key), request_hash)
        if claim.replayed:
            return claim.receipt
        if claim.conflict:
            raise HTTPException(409, "Idempotency-Key đã dùng cho yêu cầu khác")
        result = _run_backup_process(script)
        record_idempotency_receipt(transaction, claim, result)
        _last_backup_time = now
        return result


def _run_backup_workflow(script: Path, request: Request | None, now: float):
    idem_key, actor = _backup_request_context(request)
    if getattr(db, "_use_pg", False):
        return _run_pg_backup(script, actor, idem_key, now)
    if idem_key:
        return _run_sqlite_idempotent_backup(script, actor, idem_key, now)
    result = _run_backup_process(script)
    global _last_backup_time
    _last_backup_time = now
    return result


@router.post("/backup-trigger",
             summary="Trigger data backup",
             description="Initiates a manual backup of the database. Returns the backup file path, size, and status. Rate-limited by a cooldown period.")
async def trigger_backup(request: Request = None):
    """B5c: trigger manual backup; failures remain ``Kiểm tra log server`` only."""
    import time as _time
    global _last_backup_time
    now = _time.monotonic()
    if now - _last_backup_time < _BACKUP_COOLDOWN:
        remaining = int(_BACKUP_COOLDOWN - (now - _last_backup_time))
        raise HTTPException(429, f"Backup đã chạy gần đây. Thử lại sau {remaining} giây.")
    # Chỉnh máy móc DUY NHẤT trong handler B1 này khi đổi nhà admin.py → siteops/:
    # parent.parent cũ (agent/admin.py → gốc repo) nay là ROOT (= parents[2]).
    # Luồng subprocess giữ NGUYÊN VĂN, không refactor.
    script = ROOT / "scripts" / "backup_data.py"  # noqa: ASYNC240 (dựng path rẻ; I/O thật bọc asyncio.to_thread bên dưới)
    if not script.exists():
        raise HTTPException(500, "Không tìm thấy script backup_data.py")
    return await asyncio.to_thread(_run_backup_workflow, script, request, now)


# ── Export toàn-DB ──

@router.post("/export",
             summary="Export entity data",
             description="Exports all entities, relationships, and itineraries as a streaming JSON file to avoid memory issues.")
async def export_data():
    """Export toàn bộ entities từ DB — streaming JSON để không OOM."""

    def _generate():
        yield '{"entities":['
        entities = db.all_entities()
        for i, e in enumerate(entities):
            if i:
                yield ","
            yield json.dumps(e, ensure_ascii=False, default=str)
        yield '],"relationships":['
        with db._conn() as conn:
            rels = db._fetchall(conn, "SELECT from_id, to_id, type FROM relationships", ())
        for i, r in enumerate(rels):
            if i:
                yield ","
            yield json.dumps(db._row_to_dict(r), ensure_ascii=False, default=str)
        yield '],"itineraries":['
        with db._conn() as conn:
            itins = db._fetchall(conn, "SELECT * FROM itineraries", ())
        for i, it in enumerate(itins):
            if i:
                yield ","
            yield json.dumps(db._row_to_dict(it), ensure_ascii=False, default=str)  # default=str: TIMESTAMPTZ (datetime) trên PG
        yield ']}'

    return StreamingResponse(_generate(), media_type="application/json",
                             headers={"Content-Disposition": "attachment; filename=vinhlong360-export.json"})


def _admin_actor_label(request: Request | None) -> str:
    if request is None:
        return "admin-key"
    user = getattr(request.state, "admin_user", None) or getattr(request.state, "user", None)
    return f"user:{user.get('id')}" if user and user.get("id") else "admin-key"


# ══════════════════════════════════════════════════
#  SITE SETTINGS — CMS admin endpoints
# ══════════════════════════════════════════════════

@router.get("/site-settings",
            summary="Get all site settings",
            description="Retrieve all site settings grouped by category for the admin overview panel.")
async def admin_get_all_settings():
    """All settings grouped by category (for admin overview)."""
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    return await asyncio.to_thread(site_settings.get_all_grouped)


_SETTING_KEY_RE = re.compile(r"^[a-zA-Z0-9_./:-]{1,200}$")

@router.get("/site-settings/{category}",
            summary="Get settings by category",
            description="Retrieve all site settings for a specific category, for the admin editor page.")
async def admin_get_settings_by_category(category: str):
    """Settings for a specific category (for admin editor page)."""
    if not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    def _query():
        items = site_settings.get_by_category(category)
        if not items:
            raise HTTPException(404, detail=f"Không tìm thấy cài đặt cho danh mục '{category}'")
        return {"category": category, "settings": items}
    return await asyncio.to_thread(_query)


class SettingUpdate(BaseModel):
    value: object = Field(..., description="New value for the setting")


@router.put("/site-settings/{key:path}",
            summary="Update a site setting",
            description="Update the value of a single site setting by its key path.")
async def admin_update_setting(key: str, body: SettingUpdate, request: Request):
    """Update a single setting value."""
    if not _SETTING_KEY_RE.match(key):
        raise HTTPException(400, detail="Tên cài đặt không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    actor = _admin_actor_label(request)
    def _query():
        ok = site_settings.upsert(key, body.value, actor=actor)
        if not ok:
            raise HTTPException(404, detail="Không tìm thấy cài đặt")
    await asyncio.to_thread(_query)
    return {"success": True, "key": key}


class BulkSettingUpdate(BaseModel):
    updates: dict[str, object] = Field(..., description="Map of key→value to update")


@router.post("/site-settings/bulk",
             summary="Bulk update site settings",
             description="Update multiple site settings at once. Accepts a map of key-value pairs.")
async def admin_bulk_update_settings(body: BulkSettingUpdate, request: Request):
    """Batch update multiple settings at once."""
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    count = await asyncio.to_thread(site_settings.bulk_upsert, body.updates, actor=_admin_actor_label(request))
    return {"success": True, "updated": count}


@router.post("/site-settings/reset/{category}",
             summary="Reset category settings to defaults",
             description="Reset all site settings in a category back to their default values.")
async def admin_reset_category(category: str, request: Request):
    """Reset all settings in a category to their defaults."""
    if not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    def _query():
        from seed_site_settings import DEFAULTS
        return site_settings.reset_category(category, DEFAULTS, actor=_admin_actor_label(request))
    count = await asyncio.to_thread(_query)
    return {"success": True, "reset": count}

@router.get("/site-settings-history",
            summary="Get site settings change history",
            description="Returns recent setting changes, optionally filtered by category or key.")
async def admin_site_settings_history(
    category: Optional[str] = Query(None, max_length=100),
    key: Optional[str] = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=200),
):
    if category and not _SETTING_KEY_RE.match(category):
        raise HTTPException(400, detail="Tên danh mục không hợp lệ")
    if key and not _SETTING_KEY_RE.match(key):
        raise HTTPException(400, detail="Tên cài đặt không hợp lệ")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    return await asyncio.to_thread(site_settings.load_history, category=category, key=key, limit=limit)

@router.post("/site-settings-history/{history_id}/rollback",
             summary="Rollback a site setting change",
             description="Restores a setting value from a previous history snapshot.")
async def admin_site_settings_rollback(history_id: str, request: Request):
    history_id = validate_path_id(history_id, "history_id")
    if not db._use_pg:
        raise HTTPException(503, detail="Cài đặt site yêu cầu PostgreSQL")
    ok = await asyncio.to_thread(site_settings.rollback_history, history_id, actor=_admin_actor_label(request))
    if not ok:
        raise HTTPException(404, detail="Không tìm thấy snapshot")
    return {"success": True, "rolled_back": history_id}


# ── Announcements (system notices for users) ────────────────────────────

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=5000)
    type: str = Field("info", max_length=20)
    priority: int = Field(0, ge=0, le=100)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v):
        allowed = ("info", "warning", "maintenance", "update")
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, max_length=5000)
    type: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v):
        if v is None:
            return v
        allowed = ("info", "warning", "maintenance", "update")
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}")
        return v


@router.get("/announcements",
            summary="List announcements",
            description="List system announcements with optional active-status filter. Supports pagination.")
async def list_announcements(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
):
    require_pg()
    ph = db._ph

    def _query():
        where_clauses = []
        params = []
        if is_active is not None:
            where_clauses.append(f"is_active = {ph}")
            params.append(is_active)
        where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT id, title, content, type, is_active, priority,
                       starts_at, expires_at, created_by, created_at, updated_at
                FROM announcements
                {where}
                ORDER BY priority DESC, created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, tuple(params + [limit, offset]))
            total_row = db._fetchone(conn, f"SELECT COUNT(*) as cnt FROM announcements {where}", tuple(params))
        total = db._row_to_dict(total_row)["cnt"] if total_row else 0
        return {
            "announcements": [db._row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    return await asyncio.to_thread(_query)


@router.post("/announcements", status_code=201,
             summary="Create an announcement",
             description="Create a new system announcement with title, content, type, priority, and optional schedule.")
async def create_announcement(body: AnnouncementCreate, request: Request):
    require_pg()
    ph = db._ph
    admin_user = getattr(request.state, "admin_user", None)

    def _query():
        created_by = str(admin_user["id"]) if admin_user else None
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                INSERT INTO announcements (title, content, type, priority, starts_at, expires_at, created_by)
                VALUES ({ph}, {ph}, {ph}, {ph},
                        COALESCE({ph}::timestamptz, NOW()),
                        {ph}::timestamptz,
                        {ph}::uuid)
                RETURNING id, title, type, is_active, priority, starts_at, expires_at, created_at
            """, (
                body.title.strip(), body.content.strip(), body.type,
                body.priority, body.starts_at, body.expires_at,
                created_by,
            ))
        return db._row_to_dict(row) if row else None

    result = await asyncio.to_thread(_query)
    return {"success": True, "announcement": result}


@router.put("/announcements/{announcement_id}",
            summary="Update an announcement",
            description="Update fields of an existing announcement. Only provided fields are changed.")
async def update_announcement(announcement_id: str, body: AnnouncementUpdate):
    require_pg()
    announcement_id = validate_path_id(announcement_id, "announcement_id")
    ph = db._ph

    def _query():
        sets = []
        params = []
        if body.title is not None:
            sets.append(f"title = {ph}")
            params.append(body.title.strip())
        if body.content is not None:
            sets.append(f"content = {ph}")
            params.append(body.content.strip())
        if body.type is not None:
            sets.append(f"type = {ph}")
            params.append(body.type)
        if body.is_active is not None:
            sets.append(f"is_active = {ph}")
            params.append(body.is_active)
        if body.priority is not None:
            sets.append(f"priority = {ph}")
            params.append(body.priority)
        if body.starts_at is not None:
            sets.append(f"starts_at = {ph}::timestamptz")
            params.append(body.starts_at)
        if body.expires_at is not None:
            sets.append(f"expires_at = {ph}::timestamptz")
            params.append(body.expires_at)
        if not sets:
            raise HTTPException(400, "Không có thay đổi")
        sets.append("updated_at = NOW()")
        params.append(announcement_id)
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE announcements SET {", ".join(sets)}
                WHERE id::text = {ph}
                RETURNING id, title, content, type, is_active, priority, starts_at, expires_at, updated_at
            """, tuple(params))
        if not row:
            raise HTTPException(404, "Thông báo không tồn tại")
        return db._row_to_dict(row)

    result = await asyncio.to_thread(_query)
    return {"success": True, "announcement": result}


@router.delete("/announcements/{announcement_id}",
               summary="Delete an announcement",
               description="Permanently delete an announcement by ID.")
async def delete_announcement(announcement_id: str):
    require_pg()
    announcement_id = validate_path_id(announcement_id, "announcement_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                DELETE FROM announcements WHERE id::text = {ph} RETURNING id
            """, (announcement_id,))
        if not row:
            raise HTTPException(404, "Thông báo không tồn tại")
        return True

    await asyncio.to_thread(_query)
    return {"success": True}
