"""Disposable PostgreSQL uniqueness evidence for image suggestions."""

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
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return None
    if "disposable" not in parse_qs(parsed.query, keep_blank_values=True).get("marker", []):
        return None
    return raw


def _worker(dsn: str, entity_id: str, url: str, queue) -> None:
    import database
    import image_suggestions

    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = dsn
    image_suggestions.db = adapter
    image_suggestions._table_ready = False
    result = image_suggestions.create_batch([{"entity_id": entity_id, "candidate_url": url}])
    queue.put(result["created"])


@pytest.mark.skipif(
    _validated_url() is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL DSN with marker=disposable",
)
def test_only_one_postgres_ingest_creates_pending_candidate():
    dsn = _validated_url()
    import database

    entity_id = "image-race-" + uuid.uuid4().hex
    candidate_url = "https://example.test/" + uuid.uuid4().hex + ".jpg"
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = dsn
    with adapter._conn() as conn:
        adapter._execute(conn, "INSERT INTO entities (id, type, name) VALUES (%s, 'facility', 'image race')", (entity_id,))
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    workers = [ctx.Process(target=_worker, args=(dsn, entity_id, candidate_url, queue)) for _ in range(2)]
    try:
        for worker in workers:
            worker.start()
        results = [queue.get(timeout=30) for _ in workers]
        for worker in workers:
            worker.join(timeout=30)
        assert sorted(results) == [0, 1]
    finally:
        with adapter._conn() as conn:
            adapter._execute(conn, "DELETE FROM image_suggestions WHERE entity_id=%s", (entity_id,))
            adapter._execute(conn, "DELETE FROM entities WHERE id=%s", (entity_id,))

