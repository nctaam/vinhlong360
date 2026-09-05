#!/usr/bin/env python3
"""Rehearse release rollback locally without mutating a host or claiming staging."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def run_local_rollback_rehearsal(work_dir: Path | None = None) -> dict[str, object]:
    """Simulate A -> B health failure -> A restoration using disposable files."""

    with tempfile.TemporaryDirectory(dir=str(work_dir) if work_dir is not None else None, prefix="rollback-") as raw:
        root = Path(raw)
        releases = root / "releases"
        releases.mkdir()
        release_a = releases / "release-a"
        release_b = releases / "release-b"
        release_a.write_text("known-good\n", encoding="utf-8")
        release_b.write_text("candidate\n", encoding="utf-8")
        current = root / "current"
        current.write_text(release_a.read_text(encoding="utf-8"), encoding="utf-8")
        known_good_sha = hashlib.sha256(current.read_bytes()).hexdigest()

        # Candidate health is deliberately injected as failed; no server,
        # service manager, network, database, or production path is touched.
        current.write_text(release_b.read_text(encoding="utf-8"), encoding="utf-8")
        candidate_health = "failed"
        current.write_text(release_a.read_text(encoding="utf-8"), encoding="utf-8")
        restored_sha = hashlib.sha256(current.read_bytes()).hexdigest()

        return {
            "status": "pass" if restored_sha == known_good_sha else "failed",
            "environment": "local-rehearsal",
            "candidate_health": candidate_health,
            "restored_release": "release-a",
            "known_good_sha256": known_good_sha,
            "restored_sha256": restored_sha,
            "staging_claim": False,
        }


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
        "probe_id": "rollback-local-rehearsal",
        "head_sha": _head_sha(),
        "environment_id": "local-rollback-rehearsal",
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
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "artifacts" / "staging-evidence" / "rollback-rehearsal-receipt.json",
    )
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    try:
        result = run_local_rollback_rehearsal(args.work_dir)
    except Exception as exc:  # noqa: BLE001 - probe must leave a receipt on failure
        result = {"status": "failed", "error": type(exc).__name__}
        receipt = _write_receipt(args.receipt, result=result, exit_code=1, verdict="BLOCKED", nodeids=[], started=started)
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 1
    passed = result["status"] == "pass"
    receipt = _write_receipt(
        args.receipt,
        result=result,
        exit_code=0 if passed else 1,
        verdict="PASS" if passed else "BLOCKED",
        nodeids=["rollback-local-rehearsal::restore-known-good"] if passed else [],
        started=started,
    )
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
