"""Every SQL statement in the case kernel, parsed by the real PostgreSQL.

This guard exists because of a specific failure. A query in store.py selected
`cases.promise_health` — a column that has never existed — and shipped. Its unit
test used a recording double and asserted the TEXT of the query, so the double
happily accepted a column name the database would reject. In production it would
have raised UndefinedColumn into a scheduler task's except block: logged,
swallowed, and the whole promise watch silently doing nothing.

PREPARE makes PostgreSQL parse and plan a statement without running it, which
resolves every table and column against the live schema. A statement that cannot
be reconstructed statically (an f-string interpolating a local) is reported as
skipped rather than quietly passed — a guard that hides its own gaps is the
thing it is guarding against.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402

CASES_DIR = ROOT / "agent" / "cases"
VERBS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")
MIN_LENGTH = 40


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level `NAME = "..."` strings, so f-strings using them resolve."""
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        out[target.id] = node.value.value
    return out


def _literal(node: ast.AST, constants: dict[str, str]) -> str | None:
    """The statement text, or None when it cannot be reconstructed statically."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for piece in node.values:
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                parts.append(piece.value)
            elif isinstance(piece, ast.FormattedValue) and isinstance(piece.value, ast.Name):
                resolved = constants.get(piece.value.id)
                if resolved is None:
                    return None
                parts.append(resolved)
            else:
                return None
        return "".join(parts)
    return None


def collect_statements() -> tuple[list[tuple[str, int, str]], list[tuple[str, int]]]:
    found: list[tuple[str, int, str]] = []
    skipped: list[tuple[str, int]] = []
    for path in sorted(CASES_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = _module_constants(tree)
        # ast.walk visits the static pieces INSIDE an f-string as Constants of
        # their own. Collecting those would probe half a statement and report a
        # syntax error that only exists in the probe.
        inside_fstring = {
            id(piece)
            for node in ast.walk(tree) if isinstance(node, ast.JoinedStr)
            for piece in node.values
        }
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Constant, ast.JoinedStr)):
                continue
            if id(node) in inside_fstring:
                continue
            text = _literal(node, constants)
            if text is None:
                # An f-string we could not rebuild. Only interesting if the
                # static part looks like a statement rather than a fragment.
                head = ""
                if isinstance(node, ast.JoinedStr) and node.values:
                    first = node.values[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        head = first.value.strip()
                if head.upper().startswith(VERBS):
                    skipped.append((path.name, node.lineno))
                continue
            text = text.strip()
            if text.upper().startswith(VERBS) and len(text) >= MIN_LENGTH:
                found.append((path.name, node.lineno, text))
    return found, skipped


def to_numbered_params(sql: str) -> str:
    """psycopg2 placeholders become PostgreSQL's, so PREPARE will accept them."""
    named = sorted(set(re.findall(r"%\((\w+)\)s", sql)))
    for index, key in enumerate(named, 1):
        sql = sql.replace(f"%({key})s", f"${index}")
    parts, counter = [], len(named)
    for piece in re.split(r"(%s)", sql):
        if piece == "%s":
            counter += 1
            parts.append(f"${counter}")
        else:
            parts.append(piece)
    return "".join(parts)


def test_statements_are_actually_found():
    found, _ = collect_statements()

    # A collector that silently matches nothing would make every assertion below
    # vacuously true — the exact shape of bug this file exists to catch.
    assert len(found) > 40
    assert {name for name, _, _ in found} >= {"store.py", "work_control.py"}


def test_placeholders_convert_without_eating_anything():
    assert to_numbered_params("SELECT %s, %s") == "SELECT $1, $2"
    assert to_numbered_params("SELECT %(a)s, %(b)s, %s") == "SELECT $1, $2, $3"
    assert to_numbered_params("SELECT id::uuid[] FROM t") == "SELECT id::uuid[] FROM t"


@pg_only
def test_every_reconstructable_statement_resolves_against_the_live_schema():
    import psycopg2
    import psycopg2.errors

    found, skipped = collect_statements()
    connection = psycopg2.connect(TEST_DATABASE_URL)
    rejected: list[str] = []
    try:
        for index, (name, lineno, sql) in enumerate(found):
            with connection.cursor() as cursor:
                try:
                    cursor.execute(f"PREPARE vl_sql_probe_{index} AS {to_numbered_params(sql)}")
                except psycopg2.errors.IndeterminateDatatype:
                    # Parsed and every table and column resolved; only the
                    # parameter's type is open, which the driver supplies.
                    pass
                except psycopg2.Error as error:
                    rejected.append(f"{name}:{lineno} — {str(error).splitlines()[0]}")
                finally:
                    connection.rollback()
    finally:
        connection.close()

    assert not rejected, "PostgreSQL refuses these:\n" + "\n".join(rejected)
    # Report the blind spots rather than passing over them in silence. 107 of
    # 111 statements are checked; the four that are not build their column list
    # or their IN-clause from a local at run time. A new one should be a
    # deliberate choice, not a quiet gap.
    assert len(skipped) <= 4, f"more unreconstructable statements than before: {skipped}"
    assert len(found) >= 100


@pg_only
def test_the_probe_would_actually_catch_a_phantom_column():
    """The guard, guarded.

    A green check that cannot go red is worse than no check, so this feeds the
    probe the exact mistake it was written for.
    """
    import psycopg2
    import psycopg2.errors

    connection = psycopg2.connect(TEST_DATABASE_URL)
    try:
        with connection.cursor() as cursor:
            with pytest.raises(psycopg2.errors.UndefinedColumn):
                cursor.execute(
                    "PREPARE vl_sql_probe_phantom AS "
                    + to_numbered_params("SELECT case_id, promise_health FROM cases WHERE case_id = %s")
                )
    finally:
        connection.rollback()
        connection.close()
