from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_migration_gate.py"
MIGRATIONS = ROOT / "agent" / "migrations"


def _complexity(node: ast.AST) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.ExceptHandler,
                ast.With,
                ast.Assert,
                ast.comprehension,
                ast.IfExp,
            ),
        ):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
    return score


def test_migration_gate_functions_stay_below_the_complexity_limit() -> None:
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    violations = {
        node.name: _complexity(node)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _complexity(node) > 12
    }

    assert violations == {}


def test_evidence_publication_never_overwrites_a_competing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _load_checker()
    destination = tmp_path / "migration-gate.json"
    competitor = b"competitor-owned\n"
    real_link = gate.os.link

    def racing_link(source: Path, target: Path) -> None:
        Path(target).write_bytes(competitor)
        real_link(source, target)

    monkeypatch.setattr(gate.os, "link", racing_link)

    with pytest.raises(FileExistsError):
        gate._write_evidence(destination, {"status": "passed"})

    assert destination.read_bytes() == competitor


def _load_checker() -> ModuleType:
    name = f"check_migration_gate_test_{id(object())}"
    spec = importlib.util.spec_from_file_location(name, CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _production_authority(**overrides: str) -> bytes:
    values = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql://gate-user:password-canary@db/vl360",
        "ENTITY_DETAILS_TABLES": "true",
    }
    values.update(overrides)
    return "".join(f"{key}={value}\n" for key, value in values.items()).encode()


def test_environment_authority_accepts_explicit_production_contract():
    gate = _load_checker()
    values = gate._parse_environment(_production_authority())
    assert values["ENVIRONMENT"] == "production"


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (
            b"DATABASE_URL=postgresql://db/vl360\nENTITY_DETAILS_TABLES=true\n",
            "ENVIRONMENT=production",
        ),
        (_production_authority(ENVIRONMENT="development"), "ENVIRONMENT=production"),
        (_production_authority(DATABASE_URL="sqlite:///knowledge.db"), "PostgreSQL"),
        (
            _production_authority(ENTITY_DETAILS_TABLES="false"),
            "ENTITY_DETAILS_TABLES=true",
        ),
    ],
)
def test_environment_authority_rejects_nonproduction_contract(raw, message):
    gate = _load_checker()
    with pytest.raises(ValueError, match=message):
        gate._parse_environment(raw)


class _FakeCursor:
    def __init__(self, observed_version: int, statements: list[tuple[str, object]]) -> None:
        self.observed_version = observed_version
        self.statements = statements
        self._sql = ""
        self._params: object = None

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, sql: str, params: object = None) -> None:
        self._sql = " ".join(sql.split())
        self._params = params
        self.statements.append((self._sql, params))

    def fetchone(self) -> tuple[object, ...] | None:
        normalized = self._sql.lower()
        if "schema_version" not in normalized:
            return (1,)
        if "max(" in normalized or re.search(r"select\s+version\b", normalized):
            migration_name = {
                58: "058_itinerary_areas_schema.sql",
                70: "070_fix_trigger_correctness.sql",
                71: "071_restore_entity_rating_triggers.sql",
                72: "072_feedback_receipts.sql",
                73: "073_account_erasure_state.sql",
                74: "074_erasure_delete_actions.sql",
                75: "075_hot_path_indexes_and_session_timeouts.sql",
                76: "076_identity_location_preferences.sql",
                77: "077_personalization_legacy_purge_queue.sql",
                78: "078_location_preference_remediation.sql",
            }.get(self.observed_version, f"{self.observed_version:03d}_observed.sql")
            return (
                self.observed_version,
                migration_name,
            )

        required = None
        if isinstance(self._params, (tuple, list)) and self._params:
            required = int(self._params[0])
        if required is None:
            match = re.search(r"version\s*>=\s*(\d+)", normalized)
            required = int(match.group(1)) if match else None
        if required is None:
            return (self.observed_version,)
        return (1,) if self.observed_version >= required else None


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor, sessions: list[tuple[bool, bool]]) -> None:
        self._cursor = cursor
        self._sessions = sessions

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def set_session(self, *, readonly: bool, autocommit: bool) -> None:
        self._sessions.append((readonly, autocommit))


def _run_gate(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    observed_version: int,
) -> tuple[int, str, list[tuple[str, object]], list[tuple[bool, bool]]]:
    gate = _load_checker()
    statements: list[tuple[str, object]] = []
    sessions: list[tuple[bool, bool]] = []
    cursor = _FakeCursor(observed_version, statements)
    psycopg2 = SimpleNamespace(
        connect=lambda *_args, **_kwargs: _FakeConnection(cursor, sessions)
    )

    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2)
    monkeypatch.setenv("DATABASE_URL", "postgresql://gate-user:password-canary@db/gate")
    # A supplied chain must remain authoritative even if stale module markers survive.
    monkeypatch.setattr(gate, "LATEST_SCHEMA_VERSION", 58, raising=False)
    monkeypatch.setattr(gate, "LATEST_MIGRATION", "058_itinerary_areas_schema.sql", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(CHECKER),
            "--migrations",
            str(MIGRATIONS),
            "--db-check",
        ],
    )

    status = gate.main()
    captured = capsys.readouterr()
    return status, captured.out + captured.err, statements, sessions


def test_db_gate_requires_the_latest_version_from_the_supplied_migration_chain(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        sorted(MIGRATIONS.glob("*.sql"))[-1].name
        == "078_location_preference_remediation.sql"
    )

    status, output, statements, sessions = _run_gate(
        monkeypatch,
        capsys,
        observed_version=58,
    )

    assert status == 1
    assert "78" in output
    assert any("schema_version" in sql.lower() for sql, _params in statements)
    assert sessions == [(True, True)]


def test_db_gate_accepts_the_exact_latest_version_from_the_supplied_chain(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status, output, _statements, _sessions = _run_gate(
        monkeypatch,
        capsys,
        observed_version=78,
    )

    assert status == 0, output
