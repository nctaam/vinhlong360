#!/usr/bin/env python3
"""Fail-closed backup/restore drill harness for disposable PostgreSQL targets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]


def validate_restore_inputs(backup_path: Path, target_dsn: str) -> tuple[bool, list[str]]:
    """Validate inputs without opening a database connection or mutating data."""

    reasons: list[str] = []
    backup = Path(backup_path)
    if not backup.is_file():
        reasons.append("backup file does not exist")
    parsed = urlparse(str(target_dsn or ""))
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        reasons.append("target must be loopback PostgreSQL")
    elif "disposable" not in parse_qs(parsed.query, keep_blank_values=True).get("marker", []):
        reasons.append("target requires marker=disposable")
    return not reasons, reasons


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
    parser.add_argument("--target-dsn", default="")
    parser.add_argument("--execute", action="store_true", help="opt in to a disposable restore")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "artifacts" / "staging-evidence" / "backup-restore-receipt.json",
    )
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    valid, reasons = validate_restore_inputs(args.backup, args.target_dsn)
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
    command = ["pg_restore", "--exit-on-error", "--dbname", args.target_dsn, str(args.backup)]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=900, check=False)
    result = {
        "status": "incomplete" if completed.returncode == 0 else "failed",
        "backup_sha256": backup_sha,
        "restore_return_code": completed.returncode,
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
