"""Snapshot data before ETL/migration work, locally or from PostgreSQL."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import sys
from dataclasses import dataclass
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
LOCAL_BACKUP_NAME_RE = re.compile(r"^(?P<timestamp>\d{8}-\d{6})(?:-.+)?$")
LOCAL_BACKUP_SCHEMA = "vinhlong360-local-backup-v1"
LOCAL_BACKUP_TARGET = "local"
LOCAL_BACKUP_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
LOCAL_BACKUP_ARTIFACTS = {
    "web/data.json": "data.json",
    "agent/data/vinhlong360.db": "vinhlong360.db",
}
LOCAL_BACKUP_QUARANTINE_PREFIX = ".vinhlong360-quarantine-"
PG_TABLE_TOC_RE = re.compile(
    r"^\s*\d+;\s+\d+\s+\d+\s+TABLE\s+public\s+(?P<name>\S+)(?:\s|$)"
)


@dataclass(frozen=True)
class _OwnedLocalBackup:
    path: Path
    name: str
    modified_at: float
    device: int
    inode: int
    is_symlink: bool
    is_reparse: bool


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


def _lstat_status(path: Path):
    status = path.lstat()
    attributes = getattr(status, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return status, stat.S_ISLNK(status.st_mode), bool(attributes & reparse_flag)


def _safe_lstat_status(path: Path):
    try:
        return _lstat_status(path)
    except OSError:
        return None


def _is_plain_directory(status_info) -> bool:
    status, is_symlink, is_reparse = status_info
    return not is_symlink and not is_reparse and stat.S_ISDIR(status.st_mode)


def _is_plain_file(path: Path) -> bool:
    status_info = _safe_lstat_status(path)
    if status_info is None:
        return False
    status, is_symlink, is_reparse = status_info
    return not is_symlink and not is_reparse and stat.S_ISREG(status.st_mode)


def _direct_owned_directory(path: Path, managed_root: Path):
    status_info = _safe_lstat_status(path)
    if status_info is None or not _is_plain_directory(status_info):
        return None
    try:
        candidate = path.resolve(strict=True)
    except OSError:
        return None
    if candidate.parent != managed_root:
        return None
    resolved_info = _safe_lstat_status(candidate)
    if resolved_info is None or not _is_plain_directory(resolved_info):
        return None
    status = status_info[0]
    resolved_status = resolved_info[0]
    if (resolved_status.st_dev, resolved_status.st_ino) != (status.st_dev, status.st_ino):
        return None
    return candidate, status, status_info[1], status_info[2]


def _local_backup_timestamp(name: str) -> str | None:
    name_match = LOCAL_BACKUP_NAME_RE.fullmatch(name)
    if name_match is None:
        return None
    timestamp = name_match.group("timestamp")
    try:
        parsed_timestamp = datetime.strptime(timestamp, LOCAL_BACKUP_TIMESTAMP_FORMAT)
    except ValueError:
        return None
    if parsed_timestamp.strftime(LOCAL_BACKUP_TIMESTAMP_FORMAT) != timestamp:
        return None
    return timestamp


def _has_local_manifest_identity(manifest: dict, timestamp: str) -> bool:
    return (
        manifest.get("schema") == LOCAL_BACKUP_SCHEMA
        and manifest.get("target") == LOCAL_BACKUP_TARGET
        and manifest.get("timestamp") == timestamp
    )


def _read_local_backup_manifest(candidate: Path, timestamp: str) -> dict | None:
    manifest_path = candidate / "manifest.json"
    if not _is_plain_file(manifest_path):
        return None
    try:
        with manifest_path.open(encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict):
        return None
    if not _has_local_manifest_identity(manifest, timestamp):
        return None
    return manifest


def _declared_local_artifacts(manifest: dict) -> list[str] | None:
    copied = manifest.get("copied")
    if not isinstance(copied, list) or not copied:
        return None
    seen: set[str] = set()
    for source in copied:
        if not isinstance(source, str):
            return None
        if source in seen:
            return None
        if source not in LOCAL_BACKUP_ARTIFACTS:
            return None
        seen.add(source)
    return copied


def _local_artifacts_are_regular(candidate: Path, copied: list[str]) -> bool:
    for source in copied:
        artifact_path = candidate / LOCAL_BACKUP_ARTIFACTS[source]
        if not _is_plain_file(artifact_path):
            return False
    return True


def _owned_backup_record(candidate: Path, status_info) -> _OwnedLocalBackup:
    status, is_symlink, is_reparse = status_info
    return _OwnedLocalBackup(
        path=candidate,
        name=candidate.name,
        modified_at=status.st_mtime,
        device=status.st_dev,
        inode=status.st_ino,
        is_symlink=is_symlink,
        is_reparse=is_reparse,
    )


def _owned_local_backup(path: Path, managed_root: Path) -> _OwnedLocalBackup | None:
    directory = _direct_owned_directory(path, managed_root)
    if directory is None:
        return None
    candidate, status, is_symlink, is_reparse = directory
    timestamp = _local_backup_timestamp(candidate.name)
    if timestamp is None:
        return None
    manifest = _read_local_backup_manifest(candidate, timestamp)
    if manifest is None:
        return None
    copied = _declared_local_artifacts(manifest)
    if copied is None:
        return None
    if not _local_artifacts_are_regular(candidate, copied):
        return None
    return _owned_backup_record(candidate, (status, is_symlink, is_reparse))


def _quarantine_path(managed_root: Path) -> Path | None:
    for _attempt in range(16):
        candidate = managed_root / f"{LOCAL_BACKUP_QUARANTINE_PREFIX}{secrets.token_hex(16)}"
        try:
            candidate.lstat()
        except FileNotFoundError:
            return candidate
        except OSError:
            return None
    return None


def _restore_quarantine(quarantine: Path, original: Path) -> None:
    try:
        original.lstat()
        return
    except FileNotFoundError:
        pass
    except OSError:
        return
    try:
        os.replace(quarantine, original)
    except OSError:
        pass


def _quarantine_identity_matches(record: _OwnedLocalBackup, quarantine: Path) -> bool:
    try:
        status, is_symlink, is_reparse = _lstat_status(quarantine)
    except OSError:
        return False
    return (
        not is_symlink
        and not is_reparse
        and stat.S_ISDIR(status.st_mode)
        and (status.st_dev, status.st_ino) == (record.device, record.inode)
    )


def _warn_incomplete_cleanup(quarantine: Path) -> None:
    print(
        f"[backup] WARNING: cleanup incomplete for quarantine {quarantine.name}; "
        "manual review required.",
        file=sys.stderr,
    )


def _managed_cleanup_root(root: Path) -> Path | None:
    if not root.is_dir():
        return None
    managed_root = BACKUP_ROOT.resolve()
    if root.resolve() != managed_root:
        return None
    return managed_root


def _owned_backup_records(root: Path, managed_root: Path) -> list[_OwnedLocalBackup]:
    records: list[_OwnedLocalBackup] = []
    for path in root.iterdir():
        record = _owned_local_backup(path, managed_root)
        if record is not None:
            records.append(record)
    return sorted(records, key=lambda record: record.modified_at, reverse=True)


def _expired_backup_records(
    records: list[_OwnedLocalBackup],
    keep: int,
    max_age_days: int,
) -> list[_OwnedLocalBackup]:
    if len(records) <= keep:
        return []
    cutoff = datetime.now().timestamp() - max_age_days * 86400
    return [record for record in records[keep:] if record.modified_at < cutoff]


def _quarantine_owned_backup(
    record: _OwnedLocalBackup,
    managed_root: Path,
) -> Path | None:
    if _owned_local_backup(record.path, managed_root) != record:
        return None
    quarantine = _quarantine_path(managed_root)
    if quarantine is None:
        return None
    try:
        os.replace(record.path, quarantine)
    except OSError:
        return None
    if not _quarantine_identity_matches(record, quarantine):
        _restore_quarantine(quarantine, record.path)
        return None
    return quarantine


def _remove_quarantined_backup(record: _OwnedLocalBackup, quarantine: Path) -> None:
    destructive_started = False
    try:
        destructive_started = True
        shutil.rmtree(quarantine)
    except OSError:
        if destructive_started:
            _warn_incomplete_cleanup(quarantine)
        return
    try:
        quarantine.lstat()
    except FileNotFoundError:
        print(f"[backup] cleanup: removed old backup {record.name}")
    except OSError:
        _warn_incomplete_cleanup(quarantine)
    else:
        _warn_incomplete_cleanup(quarantine)


def _cleanup_old_backups(
    keep: int = 5,
    max_age_days: int = 30,
    backup_root: Path | None = None,
) -> None:
    """Remove expired backups while preserving at least the newest entries."""
    root = backup_root or BACKUP_ROOT
    managed_root = _managed_cleanup_root(root)
    if managed_root is None:
        return
    records = _owned_backup_records(root, managed_root)
    for record in _expired_backup_records(records, keep, max_age_days):
        quarantine = _quarantine_owned_backup(record, managed_root)
        if quarantine is not None:
            _remove_quarantined_backup(record, quarantine)


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
        "schema": LOCAL_BACKUP_SCHEMA,
        "target": LOCAL_BACKUP_TARGET,
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


def _pg_restore_table_names(listing: str) -> set[str]:
    return {
        match.group("name")
        for line in listing.splitlines()
        if (match := PG_TABLE_TOC_RE.match(line)) is not None
    }


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
    listed_tables = _pg_restore_table_names(listing)
    for table in PG_REQUIRED_TABLES:
        if table not in listed_tables:
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

    if args.out_dir.resolve() == BACKUP_ROOT.resolve():
        _cleanup_old_backups(
            keep=args.keep,
            max_age_days=args.max_age_days,
            backup_root=args.out_dir,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
