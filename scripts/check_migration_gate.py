#!/usr/bin/env python3
"""Static and optional DB checks for release-blocking schema drift."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "agent" / "migrations"
LATEST_SCHEMA_VERSION = 68
LATEST_MIGRATION = "068_comments_deleted_at.sql"


@dataclass
class Issue:
    severity: str
    code: str
    message: str


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def migration_files(migrations_dir: Path = MIGRATIONS) -> list[Path]:
    return sorted(migrations_dir.glob("*.sql"))


def _parse_prefixes(files: list[Path], issues: list[Issue]) -> list[int]:
    prefixes: list[int] = []
    seen: set[int] = set()
    duplicate_prefixes: set[int] = set()

    for path in files:
        match = re.match(r"^(\d{3})_[a-z0-9_]+\.sql$", path.name)
        if not match:
            issues.append(Issue("error", "bad_filename", f"{path.name} must match 000_name.sql"))
            continue
        prefix = int(match.group(1))
        if prefix in seen:
            duplicate_prefixes.add(prefix)
        seen.add(prefix)
        prefixes.append(prefix)

    if duplicate_prefixes:
        issues.append(Issue("error", "duplicate_prefix", f"duplicate migration prefixes: {sorted(duplicate_prefixes)}"))
    return prefixes


def _check_prefix_sequence(files: list[Path], prefixes: list[int], issues: list[Issue]) -> None:
    if not prefixes:
        return
    expected = list(range(min(prefixes), max(prefixes) + 1))
    missing = sorted(set(expected) - set(prefixes))
    if min(prefixes) != 2:
        issues.append(Issue("error", "unexpected_baseline", f"first migration prefix is {min(prefixes)}, expected 002 after init.sql baseline"))
    if missing:
        issues.append(Issue("error", "missing_prefix", f"missing migration prefixes: {missing}"))
    if max(prefixes) < LATEST_SCHEMA_VERSION:
        issues.append(Issue("error", "old_latest_migration", f"latest migration is {max(prefixes):03d}, expected at least {LATEST_SCHEMA_VERSION:03d}"))
    if files and files[-1].name != LATEST_MIGRATION:
        issues.append(Issue("warning", "latest_marker_mismatch", f"latest migration is {files[-1].name}, update gate marker from {LATEST_MIGRATION}"))


def _check_required_contracts(files: list[Path], issues: list[Issue]) -> None:
    all_sql = "\n".join(_read(path) for path in files)
    required_contracts = {
        "saved_entities_kind": ["saved_entities", "kind", "itinerary"],
        "superadmin_role": ["users_role_check", "superadmin"],
        "admin_audit_db": ["admin_audit_events", "actor_scopes", "request_id", "before_json", "after_json"],
        "shared_rate_idempotency": ["shared_rate_limits", "request_idempotency_keys", "expires_at"],
        "perf_quality_trends": ["quality_metric_snapshots", "idx_entities_public_type_area_updated", "idx_posts_review_entity_recent_public"],
        "itinerary_areas_schema": ["ALTER TABLE itineraries", "ADD COLUMN IF NOT EXISTS areas", "to_jsonb(ARRAY[area])"],
        "schema_version": ["schema_version", str(LATEST_SCHEMA_VERSION), LATEST_MIGRATION],
    }
    for code, tokens in required_contracts.items():
        missing = [token for token in tokens if token not in all_sql]
        if missing:
            issues.append(Issue("error", code, f"schema contract missing tokens: {', '.join(missing)}"))


def _check_destructive_sql(files: list[Path], issues: list[Issue]) -> None:
    destructive_pattern = re.compile(r"\b(DROP\s+TABLE|TRUNCATE|DELETE\s+FROM)\b", re.IGNORECASE)
    for path in files:
        sql = _read(path)
        for match in destructive_pattern.finditer(sql):
            line_no = sql[:match.start()].count("\n") + 1
            issues.append(Issue("error", "destructive_sql", f"{path.name}:{line_no} contains {match.group(1)}"))


def validate_static(migrations_dir: Path = MIGRATIONS) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    files = migration_files(migrations_dir)

    prefixes = _parse_prefixes(files, issues)
    _check_prefix_sequence(files, prefixes, issues)
    _check_required_contracts(files, issues)
    _check_destructive_sql(files, issues)

    stats = {
        "migration_count": len(files),
        "latest": files[-1].name if files else None,
        "latest_schema_version": LATEST_SCHEMA_VERSION,
    }
    return issues, stats


def validate_database(database_url: str) -> list[Issue]:
    issues: list[Issue] = []
    try:
        import psycopg2  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return [Issue("error", "missing_psycopg2", f"cannot import psycopg2: {exc}")]

    checks = [
        (
            "saved_entities_kind_column",
            "SELECT 1 FROM information_schema.columns WHERE table_name='saved_entities' AND column_name='kind'",
        ),
        (
            "saved_entities_id_column",
            "SELECT 1 FROM information_schema.columns WHERE table_name='saved_entities' AND column_name='id'",
        ),
        (
            "admin_audit_events_table",
            "SELECT 1 FROM information_schema.tables WHERE table_name='admin_audit_events'",
        ),
        (
            "shared_rate_limits_table",
            "SELECT 1 FROM information_schema.tables WHERE table_name='shared_rate_limits'",
        ),
        (
            "request_idempotency_keys_table",
            "SELECT 1 FROM information_schema.tables WHERE table_name='request_idempotency_keys'",
        ),
        (
            "quality_metric_snapshots_table",
            "SELECT 1 FROM information_schema.tables WHERE table_name='quality_metric_snapshots'",
        ),
        (
            "itineraries_areas_column",
            "SELECT 1 FROM information_schema.columns WHERE table_name='itineraries' AND column_name='areas'",
        ),
        (
            "entities_status_column",
            "SELECT 1 FROM information_schema.columns WHERE table_name='entities' AND column_name='status'",
        ),
        (
            "entities_verified_column",
            "SELECT 1 FROM information_schema.columns WHERE table_name='entities' AND column_name='verified'",
        ),
        (
            "schema_version_agent_58",
            "SELECT 1 FROM schema_version WHERE component='agent' AND version >= 58",
        ),
    ]

    try:
        with psycopg2.connect(database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                for code, sql in checks:
                    cur.execute(sql)
                    if cur.fetchone() is None:
                        issues.append(Issue("error", code, f"database check failed: {code}"))
                cur.execute(
                    """
                    SELECT 1
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    WHERE rel.relname = 'users'
                      AND con.contype = 'c'
                      AND pg_get_constraintdef(con.oid) LIKE '%superadmin%'
                    """
                )
                if cur.fetchone() is None:
                    issues.append(Issue("error", "users_role_superadmin", "users role constraint does not include superadmin"))
    except Exception as exc:  # noqa: BLE001
        issues.append(Issue("error", "db_connect", f"database check failed: {exc}"))
    return issues


def print_report(issues: list[Issue], stats: dict[str, Any]) -> None:
    print("VinhLong360 migration gate")
    print("==========================")
    print(f"migration_count: {stats.get('migration_count')}")
    print(f"latest: {stats.get('latest')}")
    print(f"latest_schema_version: {stats.get('latest_schema_version')}")
    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"  [{issue.severity}] {issue.code}: {issue.message}")
    else:
        print("\nOK")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migrations", type=Path, default=MIGRATIONS)
    parser.add_argument("--db-check", action="store_true", help="Also check DATABASE_URL schema state.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    args = parser.parse_args()

    issues, stats = validate_static(args.migrations)
    if args.db_check:
        if not args.database_url:
            issues.append(Issue("error", "missing_database_url", "--db-check requires DATABASE_URL"))
        else:
            issues.extend(validate_database(args.database_url))

    print_report(issues, stats)
    return 1 if any(issue.severity == "error" for issue in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
