#!/usr/bin/env python3
"""Fail-closed backup/restore drill harness for disposable PostgreSQL targets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def validate_restore_inputs(backup_path: Path, target_dsn: str) -> tuple[bool, list[str]]:
    """Validate inputs without opening a database connection or mutating data."""

    reasons: list[str] = []
    backup = Path(backup_path)
    if not backup.is_file():
        reasons.append("backup file does not exist")
    parsed = urlsplit(str(target_dsn or ""))
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        reasons.append("target must be loopback PostgreSQL")
    else:
        query = parse_qs(parsed.query, keep_blank_values=True)
        if "disposable" not in query.get("marker", []):
            reasons.append("target requires marker=disposable")
        if query.get("hostaddr"):
            reasons.append("target must not override hostaddr")
        if parsed.username or parsed.password:
            reasons.append("target must not embed credentials; use PGUSER/PGPASSWORD")
    return not reasons, reasons


def _restore_connection_env(target_dsn: str) -> tuple[dict[str, str], dict[str, object]]:
    """Translate an env-only URL into libpq variables without exposing secrets."""

    parsed = urlsplit(target_dsn)
    database = unquote(parsed.path.lstrip("/"))
    if not database:
        raise ValueError("target database is required")
    connection_env = {
        "PGHOST": parsed.hostname or "",
        "PGPORT": str(parsed.port or 5432),
        "PGDATABASE": database,
    }
    identity = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": database,
    }
    return connection_env, identity


def _head_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "0" * 40
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else "0" * 40


def _command() -> str:
    return subprocess.list2cmdline([sys.executable, *sys.argv])


def _manifest_path_for_backup(backup_path: Path, explicit: Path | None) -> Path | None:
    """Resolve an explicit or conventional sidecar manifest without guessing."""

    if explicit is not None:
        return explicit
    candidates = (
        backup_path.with_name(backup_path.name + ".manifest.json"),
        backup_path.parent / "manifest.json",
    )
    return next((path for path in candidates if path.is_file()), None)


def _load_backup_manifest(backup_path: Path, explicit: Path | None):
    """Load and authenticate a manifest when one was supplied or discoverable."""

    manifest_path = _manifest_path_for_backup(backup_path, explicit)
    if manifest_path is None:
        return None, None
    try:
        from scripts.backup_manifest import load_manifest, validate_manifest_artifact
    except ImportError:
        from backup_manifest import load_manifest, validate_manifest_artifact
    try:
        manifest = load_manifest(manifest_path)
        validate_manifest_artifact(manifest, backup_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid backup manifest: {exc}") from exc
    if not manifest.row_counts:
        raise ValueError("backup manifest row_counts must not be empty")
    return manifest, manifest_path


def _query_restored_row_counts(target_dsn: str, tables: list[str]) -> dict[str, int]:
    """Read manifest-declared table counts from the disposable restore target."""

    import psycopg2  # type: ignore
    from psycopg2 import sql  # type: ignore

    connection_env, _identity = _restore_connection_env(target_dsn)
    table_name = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    validated_tables: list[tuple[str, list[str]]] = []
    for table in tables:
        parts = table.split(".")
        if not parts or any(not table_name.fullmatch(part) for part in parts):
            raise ValueError(f"invalid manifest table name: {table}")
        validated_tables.append((table, parts))

    with psycopg2.connect(
        host=connection_env["PGHOST"],
        port=int(connection_env["PGPORT"]),
        dbname=connection_env["PGDATABASE"],
    ) as connection:
        with connection.cursor() as cursor:
            observed: dict[str, int] = {}
            for table, parts in validated_tables:
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(*parts)))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"count query returned no row: {table}")
                observed[table] = int(row[0])
    return observed


def _write_receipt(path: Path, *, result: dict[str, object], exit_code: int,
                   verdict: str, nodeids: list[str], started: datetime) -> dict[str, object]:
    output = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    receipt = {
        "probe_id": "backup-restore-checksum",
        "head_sha": _head_sha(),
        "environment_id": "local-disposable-postgres",
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "command": _command(),
        "exit_code": exit_code,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "captured_output": output,
        "test_nodeids": nodeids,
        "verdict": verdict,
        "result": result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _emit_receipt(path: Path, *, result: dict[str, object], exit_code: int,
                  verdict: str, nodeids: list[str], started: datetime) -> int:
    receipt = _write_receipt(
        path, result=result, exit_code=exit_code, verdict=verdict,
        nodeids=nodeids, started=started,
    )
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return exit_code


def _run_restore(args, connection_env: dict[str, str], target_identity: dict[str, object]):
    """Run pg_restore with credentials kept in the process environment."""

    command = ["pg_restore", "--exit-on-error", "--dbname", str(target_identity["database"]), str(args.backup)]
    restore_env = os.environ.copy()
    restore_env.update(connection_env)
    return subprocess.run(
        command, cwd=ROOT, env=restore_env, capture_output=True, text=True, timeout=900, check=False,
    )


def _validate_manifest_counts(manifest, target_dsn: str) -> dict[str, int]:
    observed_counts = _query_restored_row_counts(target_dsn, list(manifest.row_counts))
    try:
        from scripts.backup_manifest import validate_row_counts
    except ImportError:
        from backup_manifest import validate_row_counts
    validate_row_counts(manifest.row_counts, observed_counts)
    return observed_counts


def _finish_restore(*, completed, manifest, manifest_path, target_dsn: str,
                    result: dict[str, object], receipt_path: Path, started: datetime) -> int:
    if completed.returncode != 0:
        result["error"] = "pg_restore failed"
        return _emit_receipt(
            receipt_path, result=result, exit_code=completed.returncode,
            verdict="BLOCKED", nodeids=[], started=started,
        )
    if manifest is None:
        return _emit_receipt(
            receipt_path, result=result, exit_code=2,
            verdict="UNAVAILABLE", nodeids=[], started=started,
        )
    try:
        observed_counts = _validate_manifest_counts(manifest, target_dsn)
    except Exception as exc:  # noqa: BLE001 - convert any DB/client error into a receipt
        result.update({
            "status": "blocked",
            "manifest": str(manifest_path),
            "expected_row_counts": manifest.row_counts,
            "error": str(exc),
            "checksum_scope": "manifest checksum plus restored table-row parity",
        })
        return _emit_receipt(
            receipt_path, result=result, exit_code=1, verdict="BLOCKED",
            nodeids=["backup-restore-checksum::pg-restore"], started=started,
        )
    result.update({
        "status": "pass",
        "manifest": str(manifest_path),
        "row_counts": observed_counts,
        "checksum_scope": "manifest checksum plus restored table-row parity",
    })
    return _emit_receipt(
        receipt_path, result=result, exit_code=0, verdict="PASS",
        nodeids=["backup-restore-checksum::pg-restore", "backup-restore-checksum::row-count-parity"],
        started=started,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="manifest JSON; otherwise use a backup sidecar when present")
    parser.add_argument("--execute", action="store_true", help="opt in to a disposable restore")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "artifacts" / "staging-evidence" / "backup-restore-receipt.json",
    )
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    # Secrets must come from the process environment, never argv or a receipt.
    target_dsn = os.environ.get("VL360_RESTORE_DATABASE_URL", "")
    valid, reasons = validate_restore_inputs(args.backup, target_dsn)
    if not valid:
        return _emit_receipt(
            args.receipt, result={"status": "unavailable", "reasons": reasons},
            exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started,
        )
    if not args.execute:
        return _emit_receipt(
            args.receipt,
            result={
                "status": "unavailable",
                "reasons": ["restore execution requires explicit --execute on a disposable target"],
            },
            exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started,
        )
    if shutil.which("pg_restore") is None:
        return _emit_receipt(
            args.receipt,
            result={"status": "unavailable", "reasons": ["pg_restore is not available"]},
            exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started,
        )

    backup_sha = hashlib.sha256(args.backup.read_bytes()).hexdigest()
    try:
        manifest, manifest_path = _load_backup_manifest(args.backup, args.manifest)
    except ValueError as exc:
        return _emit_receipt(
            args.receipt,
            result={"status": "unavailable", "backup_sha256": backup_sha, "reasons": [str(exc)]},
            exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started,
        )
    try:
        connection_env, target_identity = _restore_connection_env(target_dsn)
    except ValueError as exc:
        return _emit_receipt(
            args.receipt, result={"status": "unavailable", "reasons": [str(exc)]},
            exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started,
        )
    completed = _run_restore(args, connection_env, target_identity)
    result = {
        "status": "incomplete" if completed.returncode == 0 else "failed",
        "backup_sha256": backup_sha,
        "restore_return_code": completed.returncode,
        "target": target_identity,
        "checksum_scope": "backup-bytes-only; table-row parity requires an operator-supplied manifest",
    }
    return _finish_restore(
        completed=completed, manifest=manifest, manifest_path=manifest_path,
        target_dsn=target_dsn, result=result, receipt_path=args.receipt, started=started,
    )


if __name__ == "__main__":
    raise SystemExit(main())
