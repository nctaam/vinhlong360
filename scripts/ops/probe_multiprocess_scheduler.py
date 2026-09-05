"""Run a disposable PostgreSQL multi-process scheduler lease probe."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AGENT = os.path.join(ROOT, "agent")
if AGENT not in sys.path:
    sys.path.insert(0, AGENT)


def _dsn() -> str:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("VL360_TEST_DATABASE_URL must be loopback PostgreSQL")
    if "disposable" not in parse_qs(parsed.query, keep_blank_values=True).get("marker", []):
        raise RuntimeError("VL360_TEST_DATABASE_URL requires marker=disposable")
    return raw


def _worker(dsn: str, task_name: str, slot_key: str, owner_id: str, queue) -> None:
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
    queue.put(claim.acquired)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--slots", type=int, default=20)
    args = parser.parse_args()
    if args.workers < 2 or args.slots < 1:
        parser.error("--workers must be >=2 and --slots must be >=1")
    try:
        dsn = _dsn()
    except RuntimeError as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}))
        return 2

    ctx = multiprocessing.get_context("spawn")
    totals = {"slots": args.slots, "claims": 0, "contention_losses": 0}
    for slot_index in range(args.slots):
        queue = ctx.Queue()
        task_name = f"scheduler-probe-{uuid.uuid4().hex}"
        slot_key = f"slot-{slot_index}"
        processes = [
            ctx.Process(target=_worker, args=(dsn, task_name, slot_key, f"worker-{idx}", queue))
            for idx in range(args.workers)
        ]
        for process in processes:
            process.start()
        results = [queue.get(timeout=60) for _ in processes]
        for process in processes:
            process.join(timeout=60)
        if sum(bool(value) for value in results) != 1:
            print(json.dumps({"status": "fail", "slot": slot_key, "results": results}))
            return 1
        totals["claims"] += 1
        totals["contention_losses"] += len(results) - 1
    totals["status"] = "pass"
    print(json.dumps(totals, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
