"""The old write path keeps its behaviour; it stops owning the transaction.

`upsert_entity` and `log_entity_changes` predate the correction pilot and are
called from many places, so the refactor is judged by what does NOT change: the
same row, the same detail mirror, the same audit rows, the same public shape.
What changes is who owns the transaction. Once an admin edit and its change
audit share one, a failure between them can no longer leave an edited entry with
no record of who edited it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
import entity_details as _entity_details  # noqa: E402




# One loopback-only rule for every suite that opens the disposable database.
from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402
ENTITY_ID = "p-compat-boundary"


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
        adapter._execute(conn, "DELETE FROM entities WHERE id = %s", (ENTITY_ID,))
        conn.commit()
    # initialize() opens a connection of its own to verify the schema; getting it
    # out of the way here keeps the transaction counts below honest.
    adapter.initialize()
    return adapter


def _entity(**overrides) -> dict:
    base = {
        "id": ENTITY_ID,
        "type": "place",
        "name": "Phường Long Châu",
        "summary": "tóm tắt cũ",
        "description": "mô tả cũ",
        "level": "phuong",
        "attributes": {"address": "số 1 đường Hưng Đạo Vương"},
    }
    base.update(overrides)
    return base


def _edited(old: dict) -> dict:
    """What an admin edit actually submits: the entity it read back, one field changed.

    Handing `log_entity_changes` a partial dict instead would report every key the
    partial omits as a change to empty — an artefact of the comparison, not an edit.
    """
    updated = dict(old)
    updated["summary"] = "tóm tắt mới"
    return updated


def _row(adapter) -> dict | None:
    with adapter._conn(commit_on_success=False) as conn:
        row = adapter._fetchone(
            conn, "SELECT id, name, summary, type FROM entities WHERE id=%s", (ENTITY_ID,)
        )
    return dict(row) if row is not None else None


def _audits(adapter) -> list[dict]:
    with adapter._conn(commit_on_success=False) as conn:
        return [
            dict(row)
            for row in adapter._fetchall(
                conn,
                "SELECT field, old_value, new_value, actor FROM entity_changes"
                " WHERE entity_id=%s ORDER BY field",
                (ENTITY_ID,),
            )
        ]


def _revision(adapter) -> int:
    with adapter._conn(commit_on_success=False) as conn:
        return adapter._fetchone(
            conn, "SELECT revision FROM entities WHERE id=%s", (ENTITY_ID,)
        )["revision"]


def _count_transactions(adapter, monkeypatch) -> list:
    opened = []
    original = adapter._conn

    def counting(*args, **kwargs):
        opened.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(adapter, "_conn", counting)
    return opened


def _fail_on_audit_write(adapter, monkeypatch) -> None:
    """Break the audit half only, wherever it happens to be issued from."""
    original = adapter._execute

    def failing(conn, sql, *args, **kwargs):
        # Writes only: reading the table back is how these tests check the damage.
        if "INSERT INTO entity_changes" in sql:
            raise RuntimeError("injected failure writing the audit")
        return original(conn, sql, *args, **kwargs)

    monkeypatch.setattr(adapter, "_execute", failing)


# -- What must not change --

@pg_only
def test_upsert_entity_still_writes_the_row_it_always_wrote(pg_database):
    pg_database.upsert_entity(_entity())

    row = _row(pg_database)
    assert row["name"] == "Phường Long Châu"
    assert row["summary"] == "tóm tắt cũ"
    assert row["type"] == "place"


@pg_only
def test_the_entity_reads_back_in_its_public_shape(pg_database):
    pg_database.upsert_entity(_entity())

    parsed = pg_database.get_entity(ENTITY_ID)
    assert parsed["id"] == ENTITY_ID
    assert parsed["name"] == "Phường Long Châu"
    assert parsed["attributes"]["address"] == "số 1 đường Hưng Đạo Vương"


@pg_only
def test_upsert_entity_still_opens_exactly_one_transaction(pg_database, monkeypatch):
    opened = _count_transactions(pg_database, monkeypatch)

    pg_database.upsert_entity(_entity())

    # Delegating to the writer must not multiply connections: the row and its
    # detail mirror still land together or not at all.
    assert len(opened) == 1


@pg_only
def test_upsert_entity_with_audit_transaction_helper_preserves_audit_shape(pg_database):
    pg_database.upsert_entity(_entity())
    old = pg_database.get_entity(ENTITY_ID)

    with pg_database._conn() as conn:
        mutations = pg_database._upsert_entity_audit_tx(
            conn,
            _edited(old),
            old,
            "admin",
            "admin-editor",
            None,
            None,
        )

    assert mutations is not None
    assert _audits(pg_database)[0]["field"] == "summary"


@pg_only
def test_log_entity_changes_on_its_own_still_records_every_changed_field(pg_database):
    pg_database.upsert_entity(_entity())

    pg_database.log_entity_changes(
        ENTITY_ID, {"name": "Phường Long Châu"}, {"name": "Phường Long Châu B"}, "admin"
    )

    audits = _audits(pg_database)
    assert [entry["field"] for entry in audits] == ["name"]
    assert audits[0]["new_value"] == "Phường Long Châu B"


# -- What changes: the caller owns the transaction --

@pg_only
def test_log_entity_changes_can_ride_a_caller_owned_transaction(pg_database):
    pg_database.upsert_entity(_entity())

    with pg_database._conn(commit_on_success=False) as conn:
        pg_database.log_entity_changes(
            ENTITY_ID, {"summary": "tóm tắt cũ"}, {"summary": "tóm tắt mới"}, "admin", conn=conn
        )
        conn.rollback()

    # It wrote on the caller's connection, so the caller's rollback took it back.
    assert _audits(pg_database) == []


@pg_only
def test_an_admin_edit_and_its_audit_commit_together(pg_database):
    pg_database.upsert_entity(_entity())
    old = pg_database.get_entity(ENTITY_ID)

    pg_database.upsert_entity_with_audit(
        _edited(old), old, actor="admin", provenance="admin-editor"
    )

    assert _row(pg_database)["summary"] == "tóm tắt mới"
    assert [entry["field"] for entry in _audits(pg_database)] == ["summary"]


@pg_only
def test_an_admin_edit_records_where_it_came_from(pg_database):
    pg_database.upsert_entity(_entity())
    old = pg_database.get_entity(ENTITY_ID)

    pg_database.upsert_entity_with_audit(
        _edited(old), old, actor="admin", provenance="admin-editor"
    )

    # Provenance is what later tells an admin edit apart from a correction apply.
    assert "admin-editor" in _audits(pg_database)[0]["actor"]


@pg_only
def test_an_admin_edit_that_cannot_be_audited_is_not_written_at_all(pg_database, monkeypatch):
    pg_database.upsert_entity(_entity())
    old = pg_database.get_entity(ENTITY_ID)
    _fail_on_audit_write(pg_database, monkeypatch)

    with pytest.raises(RuntimeError, match="injected"):
        pg_database.upsert_entity_with_audit(
            _edited(old), old, actor="admin", provenance="admin-editor"
        )

    # An edited entry with no record of who edited it is the outcome this forbids.
    assert _row(pg_database)["summary"] == "tóm tắt cũ"
    assert _audits(pg_database) == []


# -- The number the correction guard is checked against --

@pg_only
def test_a_new_entity_starts_at_revision_one(pg_database):
    pg_database.upsert_entity(_entity())

    assert _revision(pg_database) == 1


@pg_only
def test_an_admin_edit_moves_the_revision_a_correction_is_checked_against(pg_database):
    pg_database.upsert_entity(_entity())
    old = pg_database.get_entity(ENTITY_ID)

    pg_database.upsert_entity_with_audit(
        _edited(old), old, actor="admin", provenance="admin-editor"
    )

    # A correction pins base_entity_revision when it reads the entry. If an admin
    # edit could change the content without moving this number, the conflict check
    # would wave through a correction written against wording that is already gone.
    assert _revision(pg_database) == 2


@pg_only
def test_saving_the_same_content_again_does_not_move_the_revision(pg_database):
    pg_database.upsert_entity(_entity())

    pg_database.upsert_entity(_entity())

    # Re-imports and re-saves are routine. If each one bumped the revision, every
    # correction in flight would read as stale over a change that never happened.
    assert _revision(pg_database) == 1


@pg_only
def test_a_rolled_back_admin_edit_publishes_nothing_to_the_detail_cache(pg_database, monkeypatch):
    pg_database.upsert_entity(_entity())
    old = pg_database.get_entity(ENTITY_ID)
    applied = []
    monkeypatch.setattr(
        _entity_details,
        "apply_detail_cache_mutations",
        lambda mutations: applied.append(mutations),
    )
    _fail_on_audit_write(pg_database, monkeypatch)

    with pytest.raises(RuntimeError, match="injected"):
        pg_database.upsert_entity_with_audit(
            _edited(old), old, actor="admin", provenance="admin-editor"
        )

    # A cache updated before the commit can advertise a change that never happened.
    assert applied == []
