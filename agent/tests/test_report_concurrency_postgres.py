"""Disposable PostgreSQL concurrency checks for reports."""
from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse

import pytest


def _validated_url():
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


@pytest.mark.skipif(_validated_url() is None, reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
def test_report_authority_postgres_schema_and_unique_key():
    """The live database test is enabled only with an explicitly disposable DSN."""
    import database
    from reports.models import ReportActor, ReportCreate, ReportTargetType
    from reports.service import ReportService
    from reports.repository import ReportRepository

    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = _validated_url()
    service = ReportService(database=adapter, repository=ReportRepository(adapter))
    actor = ReportActor(actor_scope="test:report", reporter_id=None, reporter_hash="hash")
    request = ReportCreate(target_id="report-test-entity", target_type=ReportTargetType.ENTITY, reason="stale")
    with adapter._conn() as conn:
        adapter._execute(conn, "INSERT INTO entities (id, type, name) VALUES (%s, 'facility', 'test') ON CONFLICT (id) DO NOTHING", ("report-test-entity",))
    first = service.create(request, actor=actor, idempotency_key="pg-race", correlation_id="one")
    second = service.create(request, actor=actor, idempotency_key="pg-race", correlation_id="two")
    assert first.report_id == second.report_id
