from __future__ import annotations

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts" / "verify_entity_invariants.py"


@pytest.fixture(autouse=True)
def _safe_test_environment(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")


def _load_verifier():
    name = "verify_entity_invariants_test_module"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _ready_schema():
    required = {
        "trg_entity_ratings": "posts",
        "trg_entity_ratings_del": "posts",
    }
    return {
        "version": 71,
        "required_version": 71,
        "required_triggers": required,
        "triggers": dict(required),
    }


def _empty_details(verifier):
    return {table: {} for table in verifier.DETAIL_TABLES}


def test_equal_conflict_missing_and_uncoercible_counts():
    verifier = _load_verifier()
    entities = [
        {
            "id": "sentinel-equal",
            "type": "product",
            "attributes": {"ocop_star": 4, "producer": "JSON producer"},
            "address": None,
        },
        {
            "id": "sentinel-uncoercible",
            "type": "person",
            "attributes": {"birth_year": "Thế kỷ 19"},
        },
    ]
    details = _empty_details(verifier)
    details["entity_product_details"] = {
        "sentinel-equal": {
            "entity_id": "sentinel-equal",
            "ocop_star": Decimal("4"),
            "producer": "Column producer",
        },
    }

    report = verifier.evaluate_invariants(entities, details, _ready_schema())

    assert report.counts["typed_jsonb_equal"] == 1
    assert report.counts["typed_jsonb_conflict"] == 1
    assert report.counts["typed_uncoercible"] == 1


def test_typed_jsonb_value_without_a_column_is_counted_per_key():
    verifier = _load_verifier()
    entity = {
        "id": "sentinel-without-column",
        "type": "attraction",
        "attributes": {"address": "  Ward 1  ", "phone": "0123"},
        "address": None,
        "phone": None,
    }

    report = verifier.evaluate_invariants(
        [entity], _empty_details(verifier), _ready_schema()
    )

    assert report.counts["typed_jsonb_without_column"] == 2


def test_missing_expected_cti_is_counted_per_entity():
    verifier = _load_verifier()
    entity = {
        "id": "sentinel-missing-cti",
        "type": "product",
        "attributes": {"producer": "Producer"},
    }

    report = verifier.evaluate_invariants(
        [entity], _empty_details(verifier), _ready_schema()
    )

    assert report.counts["missing_expected_cti"] == 1


def test_typed_no_cti_kind_does_not_require_a_detail_row():
    verifier = _load_verifier()
    entity = {
        "id": "sentinel-itinerary",
        "type": "itinerary",
        "attributes": {"duration": "2 days"},
    }

    report = verifier.evaluate_invariants(
        [entity], _empty_details(verifier), _ready_schema()
    )

    assert report.counts["missing_expected_cti"] == 0
    assert report.counts["typed_jsonb_without_column"] == 0


def test_wrong_kind_cti_is_counted_per_entity():
    verifier = _load_verifier()
    details = _empty_details(verifier)
    details["entity_person_details"] = {
        "sentinel-wrong-kind": {"entity_id": "sentinel-wrong-kind"}
    }
    entity = {
        "id": "sentinel-wrong-kind",
        "type": "product",
        "attributes": {},
    }

    report = verifier.evaluate_invariants([entity], details, _ready_schema())

    assert report.counts["wrong_kind_cti"] == 1


def test_multi_cti_is_counted_once_per_entity():
    verifier = _load_verifier()
    details = _empty_details(verifier)
    details["entity_product_details"] = {
        "sentinel-multi": {
            "entity_id": "sentinel-multi",
            "producer": "Producer",
        }
    }
    details["entity_person_details"] = {
        "sentinel-multi": {"entity_id": "sentinel-multi"}
    }
    entity = {
        "id": "sentinel-multi",
        "type": "product",
        "attributes": {"producer": "Producer"},
    }

    report = verifier.evaluate_invariants([entity], details, _ready_schema())

    assert report.counts["multi_cti"] == 1


def test_missing_required_trigger_is_counted_per_contract_entry():
    verifier = _load_verifier()
    schema = _ready_schema()
    schema["triggers"] = {"trg_entity_ratings": "unexpected_table"}

    report = verifier.evaluate_invariants([], _empty_details(verifier), schema)

    assert report.counts["missing_required_trigger"] == 2


def test_schema_version_below_required_is_one_aggregate_violation():
    verifier = _load_verifier()
    schema = _ready_schema()
    schema["version"] = 70

    report = verifier.evaluate_invariants([], _empty_details(verifier), schema)

    assert report.counts["schema_version_below_required"] == 1


def test_report_has_stable_keys_and_sorted_aggregate_output():
    verifier = _load_verifier()

    report = verifier.evaluate_invariants([], _empty_details(verifier), _ready_schema())

    assert tuple(report.counts) == verifier.INVARIANT_KEYS
    assert report.as_dict() == {
        "ok": True,
        "total_entities": 0,
        "counts": dict(sorted(report.counts.items())),
        "schema": _ready_schema(),
    }


class _FakeCursor:
    def __init__(self, events, queries):
        self.events = events
        self.queries = queries
        self.last_query = ""

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.events.append("execute")
        self.queries.append((normalized, params))
        self.last_query = normalized

    def fetchall(self):
        if "FROM entities" in self.last_query:
            return [
                {
                    "id": "sentinel-loader",
                    "type": "product",
                    "attributes": {"producer": "Producer"},
                    "address": None,
                    "phone": None,
                    "website": None,
                    "hours": None,
                    "price_range": None,
                    "sub_category": None,
                    "best_time": None,
                    "highlight": None,
                }
            ]
        if "FROM entity_product_details" in self.last_query:
            return [
                {
                    "entity_id": "sentinel-loader",
                    "producer": "Producer",
                }
            ]
        if "FROM entity_" in self.last_query and "_details" in self.last_query:
            return []
        if "FROM schema_version" in self.last_query:
            return [{"version": 71}]
        if "FROM pg_catalog.pg_trigger" in self.last_query:
            return [
                {"trigger_name": "trg_entity_ratings", "table_name": "posts"},
                {
                    "trigger_name": "trg_entity_ratings_del",
                    "table_name": "posts",
                },
            ]
        raise AssertionError(f"unexpected SELECT shape: {self.last_query}")

    def close(self):
        self.events.append("cursor_close")


class _FakeConnection:
    def __init__(self, events, queries):
        self.events = events
        self.queries = queries

    def set_session(self, **kwargs):
        self.events.append(("set_session", kwargs))

    def cursor(self, **kwargs):
        self.events.append(("cursor", kwargs))
        return _FakeCursor(self.events, self.queries)

    def close(self):
        self.events.append("connection_close")


def _install_fake_psycopg2(monkeypatch, connect):
    psycopg2 = ModuleType("psycopg2")
    extras = ModuleType("psycopg2.extras")
    extras.RealDictCursor = object
    psycopg2.connect = connect
    psycopg2.extras = extras
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", extras)


def test_schema_loader_does_not_let_same_named_stray_trigger_mask_required_pair():
    verifier = _load_verifier()

    class Cursor:
        def __init__(self):
            self.query_number = 0

        def execute(self, _sql, _params=None):
            self.query_number += 1

        def fetchall(self):
            if self.query_number == 1:
                return [{"version": 71}]
            return [
                {"trigger_name": "trg_entity_ratings", "table_name": "posts"},
                {
                    "trigger_name": "trg_entity_ratings",
                    "table_name": "stray_table",
                },
                {
                    "trigger_name": "trg_entity_ratings_del",
                    "table_name": "posts",
                },
            ]

    schema = verifier._load_schema(Cursor())
    report = verifier.evaluate_invariants([], _empty_details(verifier), schema)

    assert schema["triggers"] == _ready_schema()["triggers"]
    assert report.counts["missing_required_trigger"] == 0


def test_run_uses_explicit_url_sets_readonly_before_cursor_and_only_selects(
    monkeypatch,
):
    verifier = _load_verifier()
    events = []
    queries = []
    connections = []

    def connect(database_url, **kwargs):
        events.append(("connect", database_url, kwargs))
        connection = _FakeConnection(events, queries)
        connections.append(connection)
        return connection

    _install_fake_psycopg2(monkeypatch, connect)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://ambient-user:ambient-pass@ambient/prod"
    )

    report = verifier.run("postgresql://explicit-user:explicit-pass@explicit/db")

    assert report.total_entities == 1
    assert events[0] == (
        "connect",
        "postgresql://explicit-user:explicit-pass@explicit/db",
        {"connect_timeout": 5},
    )
    assert events[1] == (
        "set_session",
        {"readonly": True, "autocommit": True},
    )
    assert events[2][0] == "cursor"
    assert events[-1] == "connection_close"
    assert connections
    assert len(queries) == len(verifier.DETAIL_TABLES) + 3
    assert all(sql.lstrip().upper().startswith("SELECT") for sql, _ in queries)


def test_import_does_not_connect(monkeypatch):
    calls = []

    def connect(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("module import attempted a database connection")

    _install_fake_psycopg2(monkeypatch, connect)
    monkeypatch.setenv("DATABASE_URL", "postgresql://sentinel-import/db")
    saved_modules = {
        name: sys.modules.get(name)
        for name in ("config", "entity_schemas", "entity_details", "database")
    }
    for name in saved_modules:
        sys.modules.pop(name, None)
    try:
        _load_verifier()
    finally:
        for name, module in saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    assert calls == []


def test_run_rejects_non_postgresql_url_without_connecting(monkeypatch):
    verifier = _load_verifier()
    calls = []
    _install_fake_psycopg2(monkeypatch, lambda *args, **kwargs: calls.append(args))

    with pytest.raises(ValueError, match="PostgreSQL"):
        verifier.run("sqlite:///sentinel.db")

    assert calls == []


def test_json_output_is_aggregate_and_redacted(capsys, monkeypatch):
    verifier = _load_verifier()
    report = verifier.InvariantReport(
        total_entities=1,
        counts={"typed_jsonb_conflict": 1},
        schema={"version": 70, "required_version": 71},
    )
    monkeypatch.setattr(verifier, "run", lambda _dsn: report)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://secret-user:secret-pass@db/prod"
    )

    assert verifier.main(["--json"]) == 1
    output = capsys.readouterr().out
    assert json.loads(output) == report.as_dict()
    assert "secret-user" not in output
    assert "secret-pass" not in output
    assert "sentinel" not in output


def test_text_output_has_one_aggregate_line_per_invariant(capsys, monkeypatch):
    verifier = _load_verifier()
    counts = {key: 0 for key in verifier.INVARIANT_KEYS}
    report = verifier.InvariantReport(0, counts, _ready_schema())
    monkeypatch.setattr(verifier, "run", lambda _dsn: report)

    assert verifier.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [f"{key}=0" for key in verifier.INVARIANT_KEYS]


def test_cli_error_redacts_exception_details_and_returns_two(capsys, monkeypatch):
    verifier = _load_verifier()
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://secret-user:secret-pass@db/prod"
    )

    def fail(_database_url):
        raise RuntimeError("sentinel-row secret-user secret-pass")

    monkeypatch.setattr(verifier, "run", fail)

    assert verifier.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "entity invariant verification failed: RuntimeError\n"
    assert "sentinel-row" not in captured.err
    assert "secret-user" not in captured.err
    assert "secret-pass" not in captured.err
