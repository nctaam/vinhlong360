"""The entity write boundary: one caller-owned transaction, or nothing."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from entity_write import (  # noqa: E402
    EntitySnapshot,
    EntityWriteResult,
    EntityWriteRejected,
    EntityWriteService,
)


def _pg_url() -> str | None:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = _pg_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)
ENTITY_ID = "p-write-boundary"


@pytest.fixture
def pg_database():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(conn, "DELETE FROM entity_changes WHERE entity_id = %s", (ENTITY_ID,))
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, summary, revision)"
            " VALUES (%s,'place','Quán A','tóm tắt cũ',3)"
            " ON CONFLICT (id) DO UPDATE SET name='Quán A', summary='tóm tắt cũ', revision=3",
            (ENTITY_ID,),
        )
        conn.commit()
    return adapter


def _service(adapter) -> EntityWriteService:
    return EntityWriteService(adapter)


def _row(adapter) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        return dict(adapter._fetchone(
            conn, "SELECT name, summary, revision FROM entities WHERE id=%s", (ENTITY_ID,)
        ))


def _change_count(adapter) -> int:
    with adapter._conn(commit_on_success=False) as conn:
        return adapter._fetchone(
            conn, "SELECT count(*) AS n FROM entity_changes WHERE entity_id=%s", (ENTITY_ID,)
        )["n"]


# ── The whole point: one transaction owned by the caller ──

@pg_only
def test_a_failure_after_the_row_write_leaves_no_entity_change_behind(pg_database):
    service = _service(pg_database)

    with pytest.raises(RuntimeError, match="injected"):
        with pg_database._conn(commit_on_success=False) as conn:
            result = service.apply_patch(
                conn, ENTITY_ID, {"summary": "tóm tắt mới"},
                expected_revision=3, actor="person:operator", provenance="correction-apply",
            )
            service.write_change_audit(conn, result, actor="person:operator",
                                       provenance="correction-apply")
            raise RuntimeError("injected failure before commit")

    # Neither half survived: that is what a caller-owned transaction buys.
    assert _row(pg_database)["summary"] == "tóm tắt cũ"
    assert _row(pg_database)["revision"] == 3
    assert _change_count(pg_database) == 0


@pg_only
def test_a_successful_write_commits_the_row_and_its_audit_together(pg_database):
    service = _service(pg_database)

    with pg_database._conn(commit_on_success=False) as conn:
        result = service.apply_patch(
            conn, ENTITY_ID, {"summary": "tóm tắt mới"},
            expected_revision=3, actor="person:operator", provenance="correction-apply",
        )
        service.write_change_audit(conn, result, actor="person:operator",
                                   provenance="correction-apply")
        conn.commit()

    assert type(result) is EntityWriteResult
    row = _row(pg_database)
    assert row["summary"] == "tóm tắt mới"
    assert row["revision"] == 4
    assert _change_count(pg_database) == 1
    assert result.changed_fields == ("summary",)


@pg_only
def test_the_writer_never_opens_its_own_connection():
    import inspect

    import entity_write

    source = inspect.getsource(entity_write)
    # A nested connection is exactly how the rollback guarantee above dies.
    assert "_conn(" not in source
    assert "commit()" not in source


# ── Revision semantics ──

@pg_only
def test_a_no_op_patch_changes_nothing_and_does_not_burn_a_revision(pg_database):
    service = _service(pg_database)

    with pg_database._conn(commit_on_success=False) as conn:
        result = service.apply_patch(
            conn, ENTITY_ID, {"summary": "tóm tắt cũ"},
            expected_revision=3, actor="person:operator", provenance="correction-apply",
        )
        service.write_change_audit(conn, result, actor="person:operator",
                                   provenance="correction-apply")
        conn.commit()

    assert result.changed_fields == ()
    assert _row(pg_database)["revision"] == 3
    assert _change_count(pg_database) == 0


@pg_only
def test_one_content_change_increments_the_revision_exactly_once(pg_database):
    service = _service(pg_database)

    with pg_database._conn(commit_on_success=False) as conn:
        service.apply_patch(
            conn, ENTITY_ID, {"name": "Quán B", "summary": "tóm tắt mới"},
            expected_revision=3, actor="person:operator", provenance="correction-apply",
        )
        conn.commit()

    assert _row(pg_database)["revision"] == 4


@pg_only
def test_a_stale_expected_revision_is_refused(pg_database):
    service = _service(pg_database)

    with pytest.raises(EntityWriteRejected) as excinfo:
        with pg_database._conn(commit_on_success=False) as conn:
            service.apply_patch(
                conn, ENTITY_ID, {"summary": "tóm tắt mới"},
                expected_revision=99, actor="person:operator", provenance="correction-apply",
            )

    assert excinfo.value.code == "entity_revision_conflict"
    assert _row(pg_database)["summary"] == "tóm tắt cũ"


@pg_only
def test_load_for_update_reports_the_current_revision(pg_database):
    service = _service(pg_database)

    with pg_database._conn(commit_on_success=False) as conn:
        snapshot = service.load_for_update(conn, ENTITY_ID)

    assert type(snapshot) is EntitySnapshot
    assert snapshot.revision == 3
    assert snapshot.values["summary"] == "tóm tắt cũ"
    # attributes rides along because a nested correction (attributes.phone) has to
    # merge into the stored map, and reading it outside this lock would race.
    assert "attributes" in snapshot.values


# ── The trust marker is not editable here ──

@pg_only
@pytest.mark.parametrize("field", ["verifiedAt", "attributes.verifiedAt", "verified"])
def test_a_verification_marker_can_never_be_written_through_this_path(pg_database, field):
    service = _service(pg_database)

    with pytest.raises(EntityWriteRejected) as excinfo:
        with pg_database._conn(commit_on_success=False) as conn:
            service.apply_patch(
                conn, ENTITY_ID, {field: "2026-08-18T00:00:00Z"},
                expected_revision=3, actor="person:operator", provenance="correction-apply",
            )

    assert excinfo.value.code == "verification_marker_not_writable"


@pg_only
def test_cache_mutations_are_returned_for_the_caller_to_apply_after_commit(pg_database):
    service = _service(pg_database)

    with pg_database._conn(commit_on_success=False) as conn:
        result = service.apply_patch(
            conn, ENTITY_ID, {"summary": "tóm tắt mới"},
            expected_revision=3, actor="person:operator", provenance="correction-apply",
        )
        # Still inside the transaction: nothing may have been published to a cache.
        assert result.cache_mutations is not None
        conn.commit()

    assert isinstance(result.cache_mutations, tuple)
