#!/usr/bin/env python3
"""Run a disposable PostgreSQL multi-process scheduler lease probe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import queue as queue_module
import subprocess
import sys
import uuid
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / "agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def _dsn() -> str:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("VL360_TEST_DATABASE_URL must be loopback PostgreSQL")
    if "disposable" not in parse_qs(parsed.query, keep_blank_values=True).get("marker", []):
        raise RuntimeError("VL360_TEST_DATABASE_URL requires marker=disposable")
    return raw


def _worker(dsn: str, task_name: str, slot_key: str, owner_id: str, result_queue) -> None:
    try:
        from datetime import datetime, timezone

        import database
        from scheduler_control import claim_task_slot, finish_task_slot

        adapter = database.Database()
        adapter._use_pg = True
        adapter._dsn = dsn
        claim = claim_task_slot(
            adapter,
            task_name=task_name,
            slot_key=slot_key,
            owner_id=owner_id,
            now=datetime.now(timezone.utc),
            lease_seconds=60,
        )
        if claim.acquired:
            finish_task_slot(
                adapter,
                lease_id=claim.lease_id,
                outcome="success",
                finished_at=datetime.now(timezone.utc),
                receipt={"owner_id": owner_id, "probe": True},
            )
        result_queue.put({"acquired": claim.acquired, "owner_id": owner_id})
    except Exception as exc:  # noqa: BLE001 - parent records worker failure in receipt
        result_queue.put({"error": type(exc).__name__, "owner_id": owner_id})


def run_probe(*, dsn: str, workers: int, slots: int) -> dict[str, object]:
    """Run contention and return a structured result suitable for a receipt."""

    ctx = multiprocessing.get_context("spawn")
    totals: dict[str, object] = {
        "slots": slots,
        "workers": workers,
        "claims": 0,
        "contention_losses": 0,
        "status": "pass",
    }
    for slot_index in range(slots):
        result_queue = ctx.Queue()
        task_name = f"scheduler-probe-{uuid.uuid4().hex}"
        slot_key = f"slot-{slot_index}"
        processes = [
            ctx.Process(target=_worker, args=(dsn, task_name, slot_key, f"worker-{idx}", result_queue))
            for idx in range(workers)
        ]
        try:
            for process in processes:
                process.start()
            results = [result_queue.get(timeout=60) for _ in processes]
        except queue_module.Empty as exc:
            raise RuntimeError(f"scheduler worker timeout at {slot_key}") from exc
        finally:
            for process in processes:
                process.join(timeout=60)
        errors = [item for item in results if "error" in item]
        if errors:
            raise RuntimeError(f"scheduler worker failed at {slot_key}: {errors[0]['error']}")
        acquired = sum(bool(item.get("acquired")) for item in results)
        if acquired != 1:
            return {**totals, "status": "fail", "slot": slot_key, "results": results}
        totals["claims"] = int(totals["claims"]) + 1
        totals["contention_losses"] = int(totals["contention_losses"]) + len(results) - 1
    return totals


def _command() -> str:
    return subprocess.list2cmdline([sys.executable, *sys.argv])


def _head_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "0" * 40
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else "0" * 40


def _write_receipt(path: Path, *, result: dict[str, object], exit_code: int,
                   verdict: str, nodeids: list[str], started: datetime) -> dict[str, object]:
    output = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    receipt = {
        "probe_id": "multiprocess-scheduler",
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--slots", type=int, default=20)
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "artifacts" / "staging-evidence" / "multiprocess-scheduler-receipt.json",
    )
    args = parser.parse_args(argv)
    if args.workers < 2 or args.slots < 1:
        parser.error("--workers must be >=2 and --slots must be >=1")
    started = datetime.now(timezone.utc)
    try:
        dsn = _dsn()
    except RuntimeError as exc:
        result = {"status": "unavailable", "reason": str(exc)}
        receipt = _write_receipt(args.receipt, result=result, exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started)
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 2
    try:
        result = run_probe(dsn=dsn, workers=args.workers, slots=args.slots)
    except Exception as exc:  # noqa: BLE001 - probe must leave a receipt on failure
        result = {"status": "failed", "error": type(exc).__name__}
        receipt = _write_receipt(args.receipt, result=result, exit_code=1, verdict="BLOCKED", nodeids=[], started=started)
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 1

    passed = result.get("status") == "pass"
    verdict = "PASS" if passed else "BLOCKED"
    exit_code = 0 if passed else 1
    nodeids = [f"scheduler::slot-{index}" for index in range(args.slots)]
    receipt = _write_receipt(args.receipt, result=result, exit_code=exit_code, verdict=verdict, nodeids=nodeids, started=started)
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
