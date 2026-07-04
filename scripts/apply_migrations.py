#!/usr/bin/env python3
"""Apply vinhlong360 PostgreSQL migrations that are missing.

The project uses init.sql as the baseline and agent/migrations/*.sql as
additive release migrations. schema_version was introduced late, so existing
production databases may not have a version row for older migrations. In that
case the runner assumes the legacy baseline version configured by
--baseline-version and applies only newer migrations.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIGRATIONS = ROOT / "agent" / "migrations"
DEFAULT_INIT = ROOT / "init.sql"
LEGACY_BASELINE_VERSION = 52
MIGRATION_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
DESTRUCTIVE_RE = re.compile(r"\b(DROP\s+TABLE|TRUNCATE|DELETE\s+FROM)\b", re.IGNORECASE)

SCHEMA_VERSION_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
  component  TEXT PRIMARY KEY,
  version    INTEGER NOT NULL,
  migration  TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


@dataclass(frozen=True)
class Migration:
    version: int
    path: Path


def migration_files(migrations_dir: Path) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(migrations_dir.glob("*.sql")):
        match = MIGRATION_RE.match(path.name)
        if not match:
            raise ValueError(f"Bad migration filename: {path.name}")
        migrations.append(Migration(int(match.group(1)), path))
    return migrations


def ensure_no_destructive_sql(paths: Iterable[Path]) -> None:
    for path in paths:
        sql = path.read_text(encoding="utf-8", errors="replace")
        match = DESTRUCTIVE_RE.search(sql)
        if match:
            line = sql[: match.start()].count("\n") + 1
            raise RuntimeError(f"Refusing destructive migration {path.name}:{line}: {match.group(1)}")


def table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    row = cur.fetchone()
    return bool(row and row[0])


def current_schema_version(cur) -> int | None:
    if not table_exists(cur, "schema_version"):
        return None
    cur.execute("SELECT version FROM schema_version WHERE component = %s", ("agent",))
    row = cur.fetchone()
    return int(row[0]) if row else None


def record_schema_version(cur, version: int, migration_name: str) -> None:
    cur.execute(SCHEMA_VERSION_SQL)
    cur.execute(
        """
        INSERT INTO schema_version(component, version, migration, updated_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (component) DO UPDATE SET
          version = GREATEST(schema_version.version, EXCLUDED.version),
          migration = CASE
            WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration
            ELSE schema_version.migration
          END,
          updated_at = NOW()
        """,
        ("agent", version, migration_name),
    )


def apply_sql_file(cur, path: Path) -> None:
    cur.execute(path.read_text(encoding="utf-8", errors="replace"))


def resolve_start_version(cur, *, baseline_version: int, init_baseline: bool, init_sql: Path) -> int:
    current = current_schema_version(cur)
    if current is not None:
        return current

    has_core_tables = table_exists(cur, "entities") and table_exists(cur, "users")
    if has_core_tables:
        return baseline_version

    if not init_baseline:
        raise RuntimeError(
            "Blank or incomplete database and no schema_version found. "
            "Apply init.sql first or pass --init-baseline."
        )
    if not init_sql.exists():
        raise RuntimeError(f"init.sql not found: {init_sql}")
    apply_sql_file(cur, init_sql)
    record_schema_version(cur, 1, init_sql.name)
    return 1


def run(
    database_url: str,
    *,
    migrations_dir: Path = DEFAULT_MIGRATIONS,
    init_sql: Path = DEFAULT_INIT,
    baseline_version: int = LEGACY_BASELINE_VERSION,
    init_baseline: bool = False,
    dry_run: bool = False,
) -> list[Migration]:
    if not database_url.startswith("postgresql"):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL DSN")

    try:
        import psycopg2  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"cannot import psycopg2: {exc}") from exc

    migrations = migration_files(migrations_dir)
    ensure_no_destructive_sql(m.path for m in migrations)

    with psycopg2.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            start_version = resolve_start_version(
                cur,
                baseline_version=baseline_version,
                init_baseline=init_baseline,
                init_sql=init_sql,
            )
            pending = [m for m in migrations if m.version > start_version]
            if dry_run:
                conn.rollback()
                return pending
            for migration in pending:
                apply_sql_file(cur, migration.path)
                record_schema_version(cur, migration.version, migration.path.name)
        conn.commit()
    return pending


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--migrations", type=Path, default=DEFAULT_MIGRATIONS)
    parser.add_argument("--init-sql", type=Path, default=DEFAULT_INIT)
    parser.add_argument("--baseline-version", type=int, default=LEGACY_BASELINE_VERSION)
    parser.add_argument("--init-baseline", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        pending = run(
            args.database_url,
            migrations_dir=args.migrations,
            init_sql=args.init_sql,
            baseline_version=args.baseline_version,
            init_baseline=args.init_baseline,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Migration apply failed: {exc}", file=sys.stderr)
        return 1

    label = "would apply" if args.dry_run else "applied"
    print(f"{label}: {len(pending)} migration(s)")
    for migration in pending:
        print(f"  {migration.path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
