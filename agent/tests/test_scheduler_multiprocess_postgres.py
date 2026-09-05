"""Disposable PostgreSQL multi-process scheduler lease evidence."""

from __future__ import annotations

import multiprocessing
import os
import uuid
from urllib.parse import parse_qs, urlparse

import pytest


def _validated_url() -> str | None:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return None
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return None
    if "disposable" not in parse_qs(parsed.query, keep_blank_values=True).get("marker", []):
        return None
    return raw


def _claim_worker(dsn: str, task_name: str, slot_key: str, owner_id: str, queue) -> None:
    from datetime import datetime, timezone

    import database
    from scheduler_control import claim_task_slot

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
    queue.put(claim.acquired)


@pytest.mark.skipif(
    _validated_url() is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL DSN with marker=disposable",
)
def test_only_one_postgres_worker_claims_slot():
    dsn = _validated_url()
    task_name = "scheduler-test-" + uuid.uuid4().hex
    slot_key = "slot-" + uuid.uuid4().hex
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    workers = [
        ctx.Process(target=_claim_worker, args=(dsn, task_name, slot_key, f"worker-{idx}", queue))
        for idx in range(2)
    ]
    for worker in workers:
        worker.start()
    results = [queue.get(timeout=30) for _ in workers]
    for worker in workers:
        worker.join(timeout=30)
    assert sorted(results) == [False, True]

