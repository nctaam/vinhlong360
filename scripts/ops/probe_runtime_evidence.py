#!/usr/bin/env python3
"""Measure which runtime/operations receipts this host can actually produce.

The seven operational proofs a launch decision needs — browser/proxy end-to-end,
multi-process contention, HA failover, backup to offsite and back, staging
rollout with rollback, a monitoring alert that reaches a receiver, and a
provider sandbox retry — are not all reachable from one laptop.  Writing
"not done" by hand invites drift; this probe measures the prerequisites and
records what is genuinely missing, so the gap is evidence rather than an
assertion.

The probe is deliberately read-only.  It starts no servers, mutates no
database, contacts no provider, and runs no drill.  Its output states what
*could* run here, never that anything did.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXECUTED = "EXECUTED"
AVAILABLE = "AVAILABLE_NOT_RUN"
UNAVAILABLE = "UNAVAILABLE"


def _tool(name: str) -> bool:
    """Report whether an executable is resolvable on PATH."""

    return shutil.which(name) is not None


def _file(relative: str) -> bool:
    """Report whether a repository-relative path exists."""

    return (ROOT / relative).exists()


def _docker_running() -> bool:
    """Report whether a Docker daemon answers, without starting anything."""

    if not _tool("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _loopback_port_open(port: int) -> bool:
    """Report whether something is listening on one loopback port."""

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            return True
    except OSError:
        return False


def _second_host_available() -> bool:
    """Report whether a second node is configured for HA/failover work.

    Nothing in this repository provisions one, so this is recorded explicitly
    rather than inferred from the absence of an error.
    """

    return bool(os.environ.get("VL360_SECOND_NODE_HOST", "").strip())


def _env_configured(name: str) -> bool:
    """Report whether a non-empty external prerequisite is configured."""

    return bool(os.environ.get(name, "").strip())


def _browser_check(file_exists=None) -> dict[str, Any]:
    """Report readiness of the browser and reverse-proxy end-to-end proof."""

    file_exists = file_exists or _file
    # The checked-in browser runner has no nginx/base-URL option yet, so this
    # combined proof remains unavailable even when the browser script exists.
    ready = False
    missing = []
    if not _tool("node"):
        missing.append("node")
    if not file_exists("scripts/launch_safety_browser_e2e.mjs"):
        missing.append("scripts/launch_safety_browser_e2e.mjs")
    missing.append("nginx harness base URL support")
    return {
        "id": "browser-proxy-e2e",
        "title": "Browser and reverse-proxy end-to-end",
        "status": AVAILABLE if ready else UNAVAILABLE,
        "command": "node scripts/launch_safety_browser_e2e.mjs --probe-browser",
        "missing": missing,
        "note": (
            "A browser harness exists, but it is pinned to the application port; driving the browser "
            "THROUGH the nginx harness needs a base-URL parameter the harness does not yet expose. "
            "Browser-only and proxy-only receipts are each reachable; the combined proof is not."
        ),
    }


def _multi_process_check(postgres_up: bool, file_exists=None) -> dict[str, Any]:
    """Report readiness of the multi-process contention proof."""

    file_exists = file_exists or _file
    ready = postgres_up and file_exists("agent/tests/test_case_contention_postgres.py")
    return {
        "id": "multi-process-contention",
        "title": "Multi-process contention",
        "status": AVAILABLE if ready else UNAVAILABLE,
        "command": "python -m pytest agent/tests/test_case_contention_postgres.py -v",
        "missing": (
            []
            if ready
            else (["disposable PostgreSQL on 127.0.0.1:55432"] if not postgres_up
                  else ["agent/tests/test_case_contention_postgres.py"])
        ),
        "note": (
            "Genuine multi-process contention against one disposable PostgreSQL is reachable here. "
            "Multi-NODE contention is not: it needs a second host."
        ),
    }


def _ha_check() -> dict[str, Any]:
    """Report readiness of the high-availability failover proof."""

    return {
        "id": "ha-failover",
        "title": "High availability and failover",
        # A hostname is only an input to an HA drill.  Until a replica,
        # promoter, and rerouting path are also present, this proof is not
        # runnable and must remain explicitly unavailable.
        "status": UNAVAILABLE,
        "command": "",
        "missing": ["PostgreSQL replica", "failover promoter", "proxy or VIP that reroutes", "second host"],
        "note": (
            "Nothing in this repository provisions a replica, a promoter, or a rerouting proxy: no "
            "compose service, no configuration, no runbook, no test. This is the largest genuine gap "
            "of the seven. A same-laptop primary/replica exercise would be a drill, never HA proof."
        ),
    }


def _backup_check(docker: bool, file_exists=None) -> dict[str, Any]:
    """Report readiness of the backup, offsite, restore and checksum proof."""

    file_exists = file_exists or _file
    missing = []
    if not file_exists("scripts/backup_data.py"):
        missing.append("scripts/backup_data.py")
    if not file_exists("scripts/restore_drill.py"):
        missing.append("scripts/restore_drill.py")
    if not docker:
        missing.append("Docker daemon")
    missing.extend(f"{name} on PATH" for name in ("pg_dump", "pg_restore", "aws") if not _tool(name))
    if not _env_configured("VL360_OFFSITE_BACKUP_TARGET"):
        missing.append("an offsite destination")
    ready = (
        file_exists("scripts/backup_data.py")
        and file_exists("scripts/restore_drill.py")
        and docker
        and not missing
    )
    return {
        "id": "backup-offsite-restore-checksum",
        "title": "Backup, offsite copy, restore, checksum",
        "status": AVAILABLE if ready else UNAVAILABLE,
        "command": "python scripts/backup_data.py --target local --out-dir <dir>",
        "missing": missing,
        "note": (
            "Backup and checksum are reachable. The restore leg needs PostgreSQL client tools, absent "
            "from PATH on this host; they do exist inside the postgres container, so a container-mediated "
            "restore drill is possible but has not been run. The offsite leg has no destination and no "
            "client, and provisioning one is a spend decision for the owner."
        ),
    }


def _staging_check(file_exists=None) -> dict[str, Any]:
    """Report readiness of the staging rollout, smoke and rollback proof."""

    file_exists = file_exists or _file
    missing = []
    if not file_exists("scripts/ops/rehearse_launch_rollback.sh"):
        missing.append("scripts/ops/rehearse_launch_rollback.sh")
    if not _env_configured("VL360_STAGING_HOST"):
        missing.append("a second Linux host with systemd and nginx")
    if not _env_configured("VL360_STAGING_ENVIRONMENT"):
        missing.append("a staging environment")
    ready = file_exists("scripts/ops/rehearse_launch_rollback.sh") and not missing
    return {
        "id": "staging-rollout-smoke-rollback",
        "title": "Staging rollout, smoke test, rollback",
        "status": AVAILABLE if ready else UNAVAILABLE,
        "command": "bash scripts/ops/rehearse_launch_rollback.sh --local-rehearsal",
        "missing": missing,
        "note": (
            "A local rehearsal against a command stub is reachable and must be reported as a rehearsal, "
            "never as 'rollback verified'. A real staging receipt needs a host this project does not have."
        ),
    }


def _monitoring_check(docker: bool) -> dict[str, Any]:
    """Report readiness of the monitoring alert delivery proof."""

    missing = [] if _env_configured("VL360_ALERT_RECEIVER_URL") else ["an alert receiver endpoint"]
    return {
        "id": "monitoring-alert-receiver",
        "title": "Monitoring alert reaching a receiver",
        "status": AVAILABLE if docker and not missing else UNAVAILABLE,
        "command": "docker compose up -d prometheus alertmanager backup-status-exporter",
        "missing": missing,
        "note": (
            "The monitoring stack starts and the alert rule loads, but the alert has nowhere to land: no "
            "receiver route exists. Until a sink accepts the payload, the only evidence is a set of string "
            "assertions over configuration, which does not prove delivery."
        ),
    }


def _provider_check() -> dict[str, Any]:
    """Report readiness of the provider and object-store retry proof."""

    return {
        "id": "provider-sandbox-retry",
        "title": "Provider and object-store retry and idempotency",
        "status": UNAVAILABLE,
        "command": "",
        "missing": ["a provider sandbox account", "an object-store sandbox"],
        "note": (
            "No sandbox exists. The acceptance runner's --external-sandbox flag writes a local file "
            "asserting provider_call=false; that records restraint, not retry behaviour, and it is "
            "deliberately left off. Provider-side idempotency across the crash window remains an open "
            "decision (audit F-53)."
        ),
    }


def probe(root: Path = ROOT) -> dict[str, Any]:
    """Return one measured receipt-readiness record per operational proof."""

    root = Path(root).resolve()

    def file_exists(relative: str) -> bool:
        return (root / relative).exists()

    docker = _docker_running()
    postgres_up = _loopback_port_open(55432)
    checks = [
        _browser_check(file_exists),
        _multi_process_check(postgres_up, file_exists),
        _ha_check(),
        _backup_check(docker, file_exists),
        _staging_check(file_exists),
        _monitoring_check(docker),
        _provider_check(),
    ]
    return {
        "version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "host": {
            "docker_daemon": docker,
            "disposable_postgres_55432": postgres_up,
            "second_node_configured": _second_host_available(),
            "tools": {name: _tool(name) for name in ("node", "docker", "psql", "pg_dump", "pg_restore", "aws", "bash", "pwsh")},
        },
        "checks": checks,
        "executed_count": sum(1 for item in checks if item["status"] == EXECUTED),
        "available_count": sum(1 for item in checks if item["status"] == AVAILABLE),
        "unavailable_count": sum(1 for item in checks if item["status"] == UNAVAILABLE),
        # No probe result can raise the launch verdict: measuring that a drill
        # COULD run is not the same as having run it.
        "launch_verdict": "NO_GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    output = args.output or (args.root / "artifacts" / "runtime-evidence-gaps.json")
    report = probe(args.root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "artifact": str(output),
        "executed": report["executed_count"],
        "available_not_run": report["available_count"],
        "unavailable": report["unavailable_count"],
        "launch_verdict": report["launch_verdict"],
    }, ensure_ascii=True, sort_keys=True))
    # Exit non-zero while any operational proof is missing, so this can never be
    # mistaken for a green operational gate.
    return 0 if report["executed_count"] == len(report["checks"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
