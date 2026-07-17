"""Tests for the PostgreSQL-only sitemap snapshot boundary."""

import importlib
import importlib.util
import inspect
import sys
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


BEGIN_SQL = "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
ENTITIES_SQL = "SELECT * FROM entities"
RELATIONSHIPS_SQL = (
    "SELECT from_id AS source_id, to_id AS target_id, type FROM relationships"
)


def _snapshot_module():
    spec = importlib.util.find_spec("sitemap_snapshot")
    assert spec is not None, (
        "agent/sitemap_snapshot.py must define the snapshot feature"
    )
    return importlib.import_module("sitemap_snapshot")


class FakeRow:
    def __init__(self, **values):
        self.values = values


class FakeCursor:
    def __init__(self, rows=()):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class FakeConnection:
    def __init__(self):
        self.rollback_calls = 0

    def rollback(self):
        self.rollback_calls += 1


class FakeDatabase:
    def __init__(self, *, use_pg=True, fail_sql=None, fail_conversion=False):
        self._use_pg = use_pg
        self.connection = FakeConnection()
        self.conn_calls = []
        self.execute_calls = []
        self.row_conversion_calls = []
        self.context_rollbacks = 0
        self.context_exits = 0
        self.fail_sql = fail_sql
        self.fail_conversion = fail_conversion
        self.rows_by_sql = {
            ENTITIES_SQL: (
                FakeRow(id="ward-1", type="place", name="Ward One"),
                FakeRow(id="dish-1", type="dish", name="Dish One"),
            ),
            RELATIONSHIPS_SQL: (
                FakeRow(source_id="ward-1", target_id="dish-1", type="hosts"),
            ),
        }

    @contextmanager
    def _conn(self, *args, **kwargs):
        self.conn_calls.append((args, kwargs))
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            self.context_rollbacks += 1
            raise
        else:
            if kwargs.get("commit_on_success", True):
                raise AssertionError("snapshot connection must never commit")
            self.connection.rollback()
        finally:
            self.context_exits += 1

    def _execute(self, conn, sql, params):
        self.execute_calls.append((conn, sql, params))
        if sql == self.fail_sql:
            raise LookupError("snapshot query failed")
        return FakeCursor(self.rows_by_sql.get(sql, ()))

    def _row_to_dict(self, row):
        self.row_conversion_calls.append(row)
        if self.fail_conversion:
            raise ValueError("snapshot conversion failed")
        return dict(row.values)


def test_snapshot_value_is_frozen_and_tuple_backed_without_connection_ids():
    module = _snapshot_module()
    snapshot = module.SitemapSnapshot(entities=({},), relationships=({},), wards=({},))

    assert [field.name for field in fields(snapshot)] == [
        "entities",
        "relationships",
        "wards",
    ]
    assert isinstance(snapshot.entities, tuple)
    assert isinstance(snapshot.relationships, tuple)
    assert isinstance(snapshot.wards, tuple)
    assert not hasattr(snapshot, "connection_ids")
    with pytest.raises(FrozenInstanceError):
        snapshot.entities = ()


def test_loader_uses_one_connection_and_exact_read_only_transaction_order():
    module = _snapshot_module()
    database = FakeDatabase()

    module.load_sitemap_snapshot(database)

    assert database.conn_calls == [((), {"commit_on_success": False})]
    assert [(sql, params) for _, sql, params in database.execute_calls] == [
        (BEGIN_SQL, ()),
        (ENTITIES_SQL, ()),
        (RELATIONSHIPS_SQL, ()),
    ]
    assert all(conn is database.connection for conn, _, _ in database.execute_calls)
    assert database.context_exits == 1


def test_open_manager_materializes_before_yield_and_rolls_back_after_exit():
    module = _snapshot_module()
    database = FakeDatabase()

    with module.open_sitemap_snapshot(database) as snapshot:
        assert snapshot.entities
        assert snapshot.relationships
        assert [(sql, params) for _, sql, params in database.execute_calls] == [
            (BEGIN_SQL, ()),
            (ENTITIES_SQL, ()),
            (RELATIONSHIPS_SQL, ()),
        ]
        assert database.connection.rollback_calls == 0
        assert database.context_exits == 0

    assert database.connection.rollback_calls == 1
    assert database.context_exits == 1


def test_loader_populates_tuples_normalizes_relationships_and_derives_wards():
    module = _snapshot_module()
    database = FakeDatabase()

    snapshot = module.load_sitemap_snapshot(database)

    assert snapshot.entities == (
        {"id": "ward-1", "type": "place", "name": "Ward One"},
        {"id": "dish-1", "type": "dish", "name": "Dish One"},
    )
    assert snapshot.relationships == (
        {"source_id": "ward-1", "target_id": "dish-1", "type": "hosts"},
    )
    assert snapshot.wards == (snapshot.entities[0],)
    assert snapshot.wards[0] is snapshot.entities[0]
    assert len(database.row_conversion_calls) == 3


def test_loader_manager_rolls_back_once_after_success():
    module = _snapshot_module()
    database = FakeDatabase()

    module.load_sitemap_snapshot(database)

    assert database.connection.rollback_calls == 1
    assert database.context_rollbacks == 0


@pytest.mark.parametrize(
    ("database", "error", "message"),
    [
        (
            FakeDatabase(fail_sql=RELATIONSHIPS_SQL),
            LookupError,
            "snapshot query failed",
        ),
        (FakeDatabase(fail_conversion=True), ValueError, "snapshot conversion failed"),
    ],
)
def test_loader_propagates_failures_and_context_rolls_back(database, error, message):
    module = _snapshot_module()

    with pytest.raises(error, match=message):
        module.load_sitemap_snapshot(database)

    assert database.connection.rollback_calls == 1
    assert database.context_rollbacks == 1
    assert database.context_exits == 1


def test_loader_rejects_non_postgres_before_opening_a_connection():
    module = _snapshot_module()

    class NonPostgresDatabase:
        _use_pg = False

        def _conn(self, *args, **kwargs):  # pragma: no cover - must stay unopened
            raise AssertionError("non-PostgreSQL snapshots must fail before connecting")

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        module.load_sitemap_snapshot(NonPostgresDatabase())


def test_loader_has_no_public_bulk_api_json_or_itinerary_fallback():
    module = _snapshot_module()
    source = "\n".join(
        (
            inspect.getsource(module.open_sitemap_snapshot),
            inspect.getsource(module.load_sitemap_snapshot),
        )
    )

    for forbidden in (
        "initialize",
        "all_entities",
        "all_relationships",
        "all_itineraries",
        "itinerar",
        "data.json",
        "data.js",
        "json",
        "Path",
        "open(",
    ):
        assert forbidden not in source
