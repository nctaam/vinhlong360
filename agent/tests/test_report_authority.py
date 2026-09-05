"""Contract tests for the canonical report authority.

These tests intentionally start red: the report package is introduced by Task 1.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

# Pair the boundary modules touched by this authority migration for the
# repository's staged test-pairing gate. Imports are intentionally lightweight.
import admin as _admin_module  # noqa: F401,E402
from community import api as _community_api_module  # noqa: F401,E402
from community import admin_api as _community_admin_module  # noqa: F401,E402
from control_plane import lifecycle as _lifecycle_module  # noqa: F401,E402
import database as _database_module  # noqa: F401,E402
import erasure as _erasure_module  # noqa: F401,E402
import notifications as _notifications_module  # noqa: F401,E402
import public_api as _public_api_module  # noqa: F401,E402
import structured_references as _structured_references_module  # noqa: F401,E402
from reports import repository as _report_repository_module  # noqa: F401,E402
from reports.models import ReportActor, ReportCreate, ReportTargetType
from reports.service import ReportError, ReportService, ReportTargetNotFound, InvalidReportTargetType


def request(**overrides):
    base = ReportCreate(
        target_id="entity-1",
        target_type=ReportTargetType.ENTITY,
        reason="stale",
        detail="Số điện thoại đã đổi",
        field="phone",
    )
    return replace(base, **overrides)


def actor(**overrides):
    base = ReportActor(actor_scope="anon:ip-hash", reporter_id=None, reporter_hash="hash")
    return replace(base, **overrides)


def test_unknown_target_type_is_rejected():
    with pytest.raises(InvalidReportTargetType) as excinfo:
        ReportCreate(target_id="x", target_type="bogus", reason="x")
    assert excinfo.value.code == "invalid_target_type"


def test_target_must_exist(isolated_sqlite_db):
    service = ReportService(database=isolated_sqlite_db)
    with pytest.raises(ReportTargetNotFound) as excinfo:
        service.create(request(), actor=actor(), idempotency_key="missing", correlation_id="c")
    assert excinfo.value.code == "target_not_found"


def test_same_report_idempotency_key_replays_one_record(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({"id": "entity-1", "type": "facility", "name": "Trụ sở"})
    service = ReportService(database=isolated_sqlite_db)
    first = service.create(request(), actor=actor(), idempotency_key="r-1", correlation_id="c-1")
    second = service.create(request(), actor=actor(), idempotency_key="r-1", correlation_id="c-2")
    assert second.report_id == first.report_id
    with isolated_sqlite_db._conn() as conn:
        row = isolated_sqlite_db._fetchone(conn, "SELECT COUNT(*) AS n FROM reports", ())
    assert int(isolated_sqlite_db._row_to_dict(row)["n"]) == 1


def test_transition_uses_revision_cas(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({"id": "entity-1", "type": "facility", "name": "Trụ sở"})
    service = ReportService(database=isolated_sqlite_db)
    created = service.create(request(), actor=actor(), idempotency_key="r-2", correlation_id="c")
    updated = service.transition(
        created.report_id,
        expected_revision=created.revision,
        status="resolved",
        actor=actor(actor_scope="admin:one"),
        reason="đã kiểm tra",
    )
    assert updated.status.value == "resolved"
    assert updated.revision == created.revision + 1
    with pytest.raises(Exception):
        service.transition(
            created.report_id,
            expected_revision=created.revision,
            status="dismissed",
            actor=actor(actor_scope="admin:two"),
            reason="race",
        )


def test_transition_rejects_invalid_actor(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({"id": "entity-1", "type": "facility", "name": "Trụ sở"})
    service = ReportService(database=isolated_sqlite_db)
    created = service.create(request(), actor=actor(), idempotency_key="r-actor", correlation_id="c")
    with pytest.raises(ReportError) as excinfo:
        service.transition(created.report_id, expected_revision=1, status="resolved", actor={"actor_scope": "bad"}, reason="x")
    assert str(excinfo.value) == "invalid_report_actor"


def test_report_writers_use_canonical_service_only():
    """No runtime module may create a second reports write authority."""
    agent_root = Path(__file__).resolve().parents[1]
    direct_writers = []
    for path in agent_root.rglob("*.py"):
        if "tests" in path.parts or path.name == "repository.py":
            continue
        if "INSERT INTO reports" in path.read_text(encoding="utf-8"):
            direct_writers.append(path.relative_to(agent_root).as_posix())
    assert direct_writers == []


def test_legacy_jsonl_report_actions_are_read_import_only():
    source = (Path(__file__).resolve().parents[1] / "admin.py").read_text(encoding="utf-8")
    assert "legacy_report_mutation_disabled" in source
    assert "tmp.replace(_INFO_REPORTS_FILE)" not in source
