"""Snapshot data before ETL/migration work, locally or from PostgreSQL."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    from .postgres_target import (
        IDENTITY_KEYS,
        pg_cli_connection,
        read_target_identity,
        resolve_database_url,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
        write_exclusive,
    )
except ImportError:
    from postgres_target import (
        IDENTITY_KEYS,
        pg_cli_connection,
        read_target_identity,
        resolve_database_url,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
        write_exclusive,
    )

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
DB_FILE = ROOT / "agent" / "data" / "vinhlong360.db"
BACKUP_ROOT = ROOT / "scratch" / "backups"
PG_REQUIRED_TABLES = ("entities", "entity_changes")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _count_data_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except Exception as exc:  # noqa: BLE001 - counts are advisory metadata
        return {"error": f"{type(exc).__name__}: {exc}"}

    def _len(key: str) -> int:
        value = data.get(key) if isinstance(data, dict) else None
        return len(value) if isinstance(value, list) else 0

    return {
        "entities": _len("entities"),
        "relationships": _len("relationships"),
        "itineraries": _len("itineraries"),
    }


def _file_size_human(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _cleanup_old_backups(
    keep: int = 5,
    max_age_days: int = 30,
    backup_root: Path | None = None,
) -> None:
    """Remove expired backups while preserving at least the newest entries."""
    root = backup_root or BACKUP_ROOT
    if not root.is_dir():
        return
    directories = sorted(
        [path for path in root.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if len(directories) <= keep:
        return
    cutoff = datetime.now().timestamp() - max_age_days * 86400
    for directory in directories[keep:]:
        if directory.stat().st_mtime < cutoff:
            shutil.rmtree(directory, ignore_errors=True)
            print(f"[backup] cleanup: removed old backup {directory.name}")


def _backup_sqlite(source_path: Path, artifact_path: Path) -> None:
    wal_path = Path(f"{source_path}-wal")
    shm_path = Path(f"{source_path}-shm")
    sidecars_existed = wal_path.exists() or shm_path.exists()
    source_uri = f"{source_path.resolve().as_uri()}?mode=ro"
    source = sqlite3.connect(source_uri, uri=True)
    try:
        destination = sqlite3.connect(artifact_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()

    if not sidecars_existed:
        try:
            if wal_path.is_file() and wal_path.stat().st_size == 0:
                shm_path.unlink(missing_ok=True)
                if wal_path.is_file() and wal_path.stat().st_size == 0:
                    wal_path.unlink()
        except OSError:
            # A concurrent writer owns the sidecars now; never remove active WAL state.
            pass


def _create_local_backup(destination: Path, timestamp: str) -> tuple[Path, dict]:
    destination.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "timestamp": timestamp,
        "copied": [],
        "counts": {},
        "sizes": {},
    }

    if DATA_JSON.exists():
        data_artifact = destination / "data.json"
        shutil.copy2(DATA_JSON, data_artifact)
        manifest["copied"].append("web/data.json")
        manifest["counts"] = _count_data_json(DATA_JSON)
        manifest["sizes"]["data.json"] = _file_size_human(data_artifact)
    else:
        manifest["counts"] = {"warning": "web/data.json không tồn tại"}

    if DB_FILE.exists():
        database_artifact = destination / "vinhlong360.db"
        _backup_sqlite(DB_FILE, database_artifact)
        manifest["copied"].append("agent/data/vinhlong360.db")
        manifest["sizes"]["vinhlong360.db"] = _file_size_human(database_artifact)

    with (destination / "manifest.json").open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    return destination, manifest


def _run_command(runner, command: list[str], environment: dict[str, str]):
    try:
        return runner(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
    except (FileNotFoundError, OSError) as exc:
        raise RuntimeError(f"Required PostgreSQL tool is unavailable: {command[0]}") from exc


def create_postgres_backup(
    *,
    database_url: str,
    destination: Path,
    identity: dict[str, object],
    runner=subprocess.run,
    now=_utc_now,
) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    artifact = destination / "postgres.dump"
    started_at = now()
    connection_args, connection_environment = pg_cli_connection(database_url)
    environment = os.environ.copy()
    environment.update(connection_environment)

    versions: dict[str, str] = {}
    for tool in ("pg_dump", "pg_restore"):
        result = _run_command(runner, [tool, "--version"], environment)
        version = result.stdout.strip() if result.returncode == 0 else ""
        if not version:
            raise RuntimeError(f"Unable to determine {tool} version")
        versions[tool] = version

    dump_result = _run_command(
        runner,
        [
            "pg_dump",
            "--format=custom",
            "--file",
            str(artifact),
            *connection_args,
        ],
        environment,
    )
    if dump_result.returncode != 0 or not artifact.is_file() or artifact.stat().st_size == 0:
        raise RuntimeError("pg_dump failed to create a non-empty custom-format backup")

    listing_result = _run_command(
        runner,
        ["pg_restore", "--list", str(artifact)],
        environment,
    )
    if listing_result.returncode != 0:
        raise RuntimeError("pg_restore --list failed to validate the backup")
    listing = listing_result.stdout
    for table in PG_REQUIRED_TABLES:
        if re.search(rf"\b{re.escape(table)}\b", listing) is None:
            raise RuntimeError(f"PostgreSQL backup is missing required table: {table}")

    database_identity = {key: identity[key] for key in IDENTITY_KEYS}
    manifest = {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target_fingerprint(database_identity),
        "database_identity": database_identity,
        "started_at": started_at,
        "completed_at": now(),
        "max_age_seconds": 3600,
        "tools": versions,
        "artifact": {
            "path": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": sha256_file(artifact),
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": list(PG_REQUIRED_TABLES),
            "listing_sha256": sha256_bytes(listing.encode("utf-8")),
        },
        "policy_revision": "published-v1",
    }
    return write_exclusive(destination / "manifest.json", manifest)


def _read_postgres_identity(database_url: str) -> dict[str, object]:
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError("psycopg2 is required for PostgreSQL backups") from None

    connection = None
    try:
        connection = psycopg2.connect(database_url)
        with connection.cursor() as cursor:
            return read_target_identity(cursor)
    except Exception:
        raise RuntimeError("Unable to read PostgreSQL target identity") from None
    finally:
        if connection is not None:
            connection.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Snapshot data.json + database trước thao tác dữ liệu."
    )
    parser.add_argument("--target", choices=("local", "pg"), default="local")
    parser.add_argument("--database-url-env", default="VL360_BACKUP_DATABASE_URL")
    parser.add_argument("--out-dir", type=Path, default=BACKUP_ROOT)
    parser.add_argument("--label", default="", help="nhãn thêm vào tên thư mục backup")
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="số bản backup giữ lại tối thiểu (mặc định: 5)",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="xóa backup cũ hơn N ngày (mặc định: 30)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{timestamp}-{args.label}" if args.label else timestamp
    destination = args.out_dir / name

    if args.target == "pg":
        try:
            database_url = resolve_database_url(args.database_url_env)
            identity = _read_postgres_identity(database_url)
            create_postgres_backup(
                database_url=database_url,
                destination=destination,
                identity=identity,
            )
        except Exception as exc:  # noqa: BLE001 - CLI emits a credential-safe error
            print(f"[backup] ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"[backup] -> {destination}")
        return 0

    _, manifest = _create_local_backup(destination, timestamp)
    print(f"[backup] -> {destination}")
    print(f"[backup] copied: {', '.join(manifest['copied']) or '(none)'}")
    for filename, size in manifest["sizes"].items():
        print(f"[backup] size: {filename} = {size}")
    print(f"[backup] counts: {manifest['counts']}")

    if not manifest["copied"]:
        print("[backup] CẢNH BÁO: không có gì để sao lưu.", file=sys.stderr)
        return 1

    _cleanup_old_backups(
        keep=args.keep,
        max_age_days=args.max_age_days,
        backup_root=args.out_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
