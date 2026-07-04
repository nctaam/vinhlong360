#!/usr/bin/env python3
"""Non-destructive PostgreSQL restore drill for vinhlong360 production backups.

The drill restores the latest deploy dump into a temporary database, runs the
migration gate against that restored database, performs a small sanity check,
then drops the temporary database unless --keep-db is passed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]

def _normalize_pg_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.startswith("postgresql+"):
        parsed = parsed._replace(scheme="postgresql")
    return urlunparse(parsed)

def _database_name(database_url: str) -> str:
    parsed = urlparse(database_url)
    name = parsed.path.lstrip("/").split("/", 1)[0]
    if not name:
        raise ValueError("DATABASE_URL must include a database name")
    return name

def _database_url_for(database_url: str, db_name: str) -> str:
    parsed = urlparse(database_url)
    return urlunparse(parsed._replace(path=f"/{db_name}"))

def _find_latest_dump(backup_dir: Path) -> Path | None:
    if not backup_dir.is_dir():
        return None
    candidates: list[Path] = []
    for pattern in ("db-pre-deploy-*.dump", "*.dump", "*.backup"):
        candidates.extend(backup_dir.glob(pattern))
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None

def _maintenance_urls(database_url: str) -> list[str]:
    current_db = _database_name(database_url)
    names = ["postgres", "template1", current_db]
    urls: list[str] = []
    for name in names:
        url = _database_url_for(database_url, name)
        if url not in urls:
            urls.append(url)
    return urls

def _connect_maintenance(database_url: str):
    import psycopg2  # type: ignore

    last_exc: Exception | None = None
    for url in _maintenance_urls(database_url):
        try:
            conn = psycopg2.connect(url, connect_timeout=8)
            conn.autocommit = True
            return conn
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise RuntimeError(f"cannot connect to a maintenance database: {last_exc}") from last_exc

def _can_run_as_system_postgres() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0 and bool(shutil.which("runuser"))

def _system_postgres_cmd(args: list[str]) -> None:
    result = subprocess.run(
        ["runuser", "-u", "postgres", "--", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"system postgres command failed: {' '.join(args)}: {detail[-800:]}")

def _create_database_with_system_postgres(database_url: str, db_name: str) -> None:
    parsed = urlparse(database_url)
    owner = unquote(parsed.username) if parsed.username else None
    _system_postgres_cmd(["dropdb", "--if-exists", db_name])
    cmd = ["createdb"]
    if owner:
        cmd.extend(["--owner", owner])
    cmd.append(db_name)
    _system_postgres_cmd(cmd)

def _drop_database_with_system_postgres(db_name: str) -> None:
    _system_postgres_cmd(["dropdb", "--if-exists", "--force", db_name])

def _create_database(database_url: str, db_name: str) -> None:
    from psycopg2 import sql  # type: ignore

    conn = _connect_maintenance(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
            cur.execute(
                sql.SQL("CREATE DATABASE {} WITH TEMPLATE template0 ENCODING 'UTF8'").format(
                    sql.Identifier(db_name)
                )
            )
    except Exception:
        if _can_run_as_system_postgres():
            _create_database_with_system_postgres(database_url, db_name)
            return
        raise
    finally:
        conn.close()

def _drop_database(database_url: str, db_name: str) -> None:
    from psycopg2 import sql  # type: ignore

    conn = _connect_maintenance(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (db_name,),
            )
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
    except Exception:
        if _can_run_as_system_postgres():
            _drop_database_with_system_postgres(db_name)
            return
        raise
    finally:
        conn.close()

def _restore_env_and_args(pg_restore: str, database_url: str, db_name: str, dump: Path) -> tuple[dict[str, str], list[str]]:
    parsed = urlparse(database_url)
    env = dict(os.environ)
    query = parse_qs(parsed.query)
    if parsed.password:
        env["PGPASSWORD"] = unquote(parsed.password)
    if query.get("sslmode"):
        env["PGSSLMODE"] = query["sslmode"][0]

    args = [pg_restore, "--exit-on-error", "--no-owner", "--no-privileges"]
    if parsed.hostname:
        args.extend(["--host", parsed.hostname])
    if parsed.port:
        args.extend(["--port", str(parsed.port)])
    if parsed.username:
        args.extend(["--username", unquote(parsed.username)])
    args.extend(["--dbname", db_name, str(dump)])
    return env, args

def _run_restore(database_url: str, db_name: str, dump: Path) -> None:
    pg_restore = shutil.which("pg_restore")
    if not pg_restore:
        raise RuntimeError("pg_restore not found in PATH")
    env, args = _restore_env_and_args(pg_restore, database_url, db_name, dump)
    result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"pg_restore failed with exit {result.returncode}: {detail[-1200:]}")

def _run_migration_gate(restore_url: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = restore_url
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_migration_gate.py"), "--db-check"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()
        raise RuntimeError(f"migration gate failed on restored database: {detail[-1200:]}")

def _sanity_check(restore_url: str) -> dict[str, int | str | None]:
    import psycopg2  # type: ignore

    with psycopg2.connect(restore_url, connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM entities")
            entities = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM relationships")
            relationships = int(cur.fetchone()[0])
            cur.execute("SELECT version FROM schema_version WHERE component = 'agent'")
            row = cur.fetchone()
    return {
        "entities": entities,
        "relationships": relationships,
        "schema_version": int(row[0]) if row else None,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--backup-dir", type=Path, default=ROOT / "backups")
    parser.add_argument("--dump", type=Path, default=None)
    parser.add_argument("--keep-db", action="store_true", help="Keep the temporary restored database for inspection.")
    parser.add_argument("--skip-migration-gate", action="store_true")
    args = parser.parse_args()

    if not args.database_url:
        print("[restore-drill] ERROR: DATABASE_URL is required", file=sys.stderr)
        return 2
    database_url = _normalize_pg_url(args.database_url)
    dump = args.dump or _find_latest_dump(args.backup_dir)
    if dump is None:
        print(f"[restore-drill] ERROR: no .dump backup found in {args.backup_dir}", file=sys.stderr)
        return 2
    if not dump.exists():
        print(f"[restore-drill] ERROR: dump not found: {dump}", file=sys.stderr)
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    db_name = f"{_database_name(database_url)}_restore_drill_{ts}"
    restore_url = _database_url_for(database_url, db_name)

    print(f"[restore-drill] dump={dump}")
    print(f"[restore-drill] temp_db={db_name}")
    created = False
    try:
        _create_database(database_url, db_name)
        created = True
        _run_restore(database_url, db_name, dump)
        if not args.skip_migration_gate:
            _run_migration_gate(restore_url)
        sanity = _sanity_check(restore_url)
        print(
            "[restore-drill] OK "
            f"entities={sanity['entities']} relationships={sanity['relationships']} "
            f"schema_version={sanity['schema_version']}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[restore-drill] FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        if created and not args.keep_db:
            try:
                _drop_database(database_url, db_name)
                print(f"[restore-drill] dropped temp_db={db_name}")
            except Exception as exc:  # noqa: BLE001
                print(f"[restore-drill] WARN: could not drop temp_db={db_name}: {exc}", file=sys.stderr)
        elif created:
            print(f"[restore-drill] kept temp_db={db_name}")

if __name__ == "__main__":
    raise SystemExit(main())
