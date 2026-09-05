#!/usr/bin/env python3
"""Fail-closed backup/restore drill harness for disposable PostgreSQL targets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
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
        result = {"status": "unavailable", "reasons": reasons}
        receipt = _write_receipt(args.receipt, result=result, exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started)
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 2
    if not args.execute:
        result = {
            "status": "unavailable",
            "reasons": ["restore execution requires explicit --execute on a disposable target"],
        }
        receipt = _write_receipt(args.receipt, result=result, exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started)
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 2
    if shutil.which("pg_restore") is None:
        result = {"status": "unavailable", "reasons": ["pg_restore is not available"]}
        receipt = _write_receipt(args.receipt, result=result, exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started)
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 2

    backup_sha = hashlib.sha256(args.backup.read_bytes()).hexdigest()
    try:
        connection_env, target_identity = _restore_connection_env(target_dsn)
    except ValueError as exc:
        result = {"status": "unavailable", "reasons": [str(exc)]}
        receipt = _write_receipt(args.receipt, result=result, exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started)
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 2
    # pg_restore receives only the database name on argv; credentials stay in
    # libpq environment variables and therefore cannot leak into the receipt.
    command = ["pg_restore", "--exit-on-error", "--dbname", str(target_identity["database"]), str(args.backup)]
    restore_env = os.environ.copy()
    restore_env.update(connection_env)
    completed = subprocess.run(
        command, cwd=ROOT, env=restore_env, capture_output=True, text=True, timeout=900, check=False
    )
    result = {
        "status": "incomplete" if completed.returncode == 0 else "failed",
        "backup_sha256": backup_sha,
        "restore_return_code": completed.returncode,
        "target": target_identity,
        "checksum_scope": "backup-bytes-only; table-row parity requires an operator-supplied manifest",
    }
    if completed.returncode != 0:
        result["error"] = "pg_restore failed"
    # A successful pg_restore is not enough to prove table/row parity.  Keep
    # the receipt explicitly non-pass until a manifest-backed checksum phase is
    # supplied by the operator.
    receipt = _write_receipt(
        args.receipt,
        result=result,
        exit_code=completed.returncode if completed.returncode else 2,
        verdict="UNAVAILABLE" if completed.returncode == 0 else "BLOCKED",
        nodeids=[],
        started=started,
    )
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return completed.returncode if completed.returncode else 2


if __name__ == "__main__":
    raise SystemExit(main())
