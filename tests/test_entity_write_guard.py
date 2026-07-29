from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_entity_write_paths.py"
EXPECTED_REPOSITORY_WRITE_SITES = {
    ("agent/database.py", "Database._write_entity_row", "insert"),
    ("agent/database.py", "Database._bulk_insert_rows", "insert"),
    ("agent/entity_details.py", "sync_entity_details", "dynamic-update"),
    ("scripts/backfill_entity_details.py", "_apply_universal", "dynamic-update"),
    ("scripts/cleanup_entity_jsonb.py", "_process_entity", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_apply_one_local_fix", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_apply_one_local_fix", "dynamic-update"),
    ("scripts/sp2_reconcile.py", "_prod_patch_one", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_prod_patch_one", "dynamic-update"),
    ("scripts/sp2_reconcile.py", "_prod_insert", "insert"),
    ("scripts/sp6_fill_required.py", "_apply_sqlite", "attributes-update"),
    ("scripts/sp6_fill_required.py", "_apply_pg", "attributes-update"),
    (
        "scripts/import_enrichment_tips.py",
        "_apply_enrichment_row",
        "attributes-update",
    ),
    ("scripts/fix_tinh_moi.py", "apply_sqlite", "dynamic-update"),
    ("scripts/fix_tinh_moi.py", "apply_pg", "attributes-update"),
    ("scripts/fix_tinh_moi.py", "apply_pg", "dynamic-update"),
}


def _load_checker() -> ModuleType:
    name = "check_entity_write_paths"
    spec = importlib.util.spec_from_file_location(name, CHECKER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_source(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_scanner_detects_literal_and_dynamic_entity_writes(tmp_path):
    checker = _load_checker()
    _write_source(
        tmp_path / "unsafe.py",
        """
def literal(cur):
    cur.execute('UPDATE entities SET attributes = ? WHERE id = ?', ('{}', 'e1'))

def dynamic(cur, field):
    cur.execute(f'UPDATE entities SET {field} = ? WHERE id = ?', ('x', 'e1'))

def insert(cur, cols):
    cur.execute(f'INSERT INTO entities ({cols}) VALUES (?)', ('x',))
""",
    )

    sites = checker.find_write_sites(tmp_path)

    assert {(site.function, site.kind) for site in sites} == {
        ("literal", "attributes-update"),
        ("dynamic", "dynamic-update"),
        ("insert", "insert"),
    }


def test_scanner_qualifies_nested_functions_and_normalizes_sql(tmp_path):
    checker = _load_checker()
    _write_source(
        tmp_path / "nested.py",
        '''
class Outer:
    class Inner:
        def literal(self, cur):
            cur.execute("""
                UpDaTe entities
                SeT attributes = ?
                WHERE id = ?
            """)

        def dynamic(self, cur, field):
            cur.execute(f"""
                update entities
                set {field} = ?
                where id = ?
            """)
''',
    )

    sites = checker.find_write_sites(tmp_path)

    assert {(site.function, site.kind) for site in sites} == {
        ("Outer.Inner.literal", "attributes-update"),
        ("Outer.Inner.dynamic", "dynamic-update"),
    }


def test_scanner_detects_whole_dynamic_assignment_list(tmp_path):
    checker = _load_checker()
    _write_source(
        tmp_path / "dynamic_list.py",
        """
def dynamic_list(cur, sets):
    cur.execute(f'UPDATE entities SET {sets} WHERE id = ?', ('x',))
""",
    )

    sites = checker.find_write_sites(tmp_path)

    assert [(site.function, site.kind) for site in sites] == [
        ("dynamic_list", "dynamic-update")
    ]


def test_allowlist_is_exact_per_function_not_per_path(tmp_path, monkeypatch):
    checker = _load_checker()
    _write_source(
        tmp_path / "scripts" / "same_file.py",
        """
def approved(cur):
    cur.execute('UPDATE entities SET attributes = ?')

def bypass(cur):
    cur.execute('UPDATE entities SET attributes = ?')
""",
    )
    monkeypatch.setattr(
        checker,
        "ALLOWED_WRITE_SITES",
        {("scripts/same_file.py", "approved", "attributes-update")},
    )

    sites = checker.unapproved_write_sites(tmp_path)

    assert [(site.path, site.function, site.kind) for site in sites] == [
        ("scripts/same_file.py", "bypass", "attributes-update")
    ]


def test_repository_layout_scan_ignores_non_source_directories(tmp_path):
    checker = _load_checker()
    source = "def write(cur):\n    cur.execute('UPDATE entities SET attributes = ?')\n"
    _write_source(tmp_path / "agent" / "live.py", source)
    _write_source(tmp_path / "scripts" / "live.py", source)
    _write_source(tmp_path / "root_level.py", source)
    _write_source(tmp_path / "tests" / "ignored.py", source)
    _write_source(tmp_path / "agent" / "generated" / "ignored.py", source)
    _write_source(tmp_path / "scripts" / "cache" / "ignored.py", source)
    _write_source(tmp_path / "scripts" / "migrations" / "ignored.py", source)
    _write_source(tmp_path / "scripts" / "__pycache__" / "ignored.py", source)

    sites = checker.find_write_sites(tmp_path)

    assert [(site.path, site.function) for site in sites] == [
        ("agent/live.py", "write"),
        ("scripts/live.py", "write"),
    ]


def test_cli_output_contains_only_safe_site_metadata(tmp_path, capsys):
    checker = _load_checker()
    _write_source(
        tmp_path / "unsafe.py",
        """
def leak(cur):
    cur.execute('UPDATE entities SET attributes = ? WHERE id = ?', ('{}', 'e1'))
""",
    )

    exit_code = checker.main([str(tmp_path)])

    assert exit_code == 1
    assert capsys.readouterr().out.splitlines() == [
        "unsafe.py|leak|attributes-update|3"
    ]


def test_cli_parse_error_fails_closed_with_sanitized_output(tmp_path, capsys):
    checker = _load_checker()
    _write_source(tmp_path / "broken.py", "def broken(DO_NOT_PRINT:\n    pass\n")

    try:
        exit_code = checker.main([str(tmp_path)])
    except SyntaxError:
        pytest.fail("parse failure escaped instead of failing closed")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out.splitlines() == ["broken.py|<module>|parse-error|1"]
    assert captured.err == ""
    assert "DO_NOT_PRINT" not in captured.out
    assert "Traceback" not in captured.out


def test_declaration_expressions_use_enclosing_scope(tmp_path):
    checker = _load_checker()
    _write_source(
        tmp_path / "scopes.py",
        '''@mark("UPDATE entities SET attributes = ?")
def guarded(
    annotated: mark("UPDATE entities SET attributes = ?"),
    defaulted=mark("UPDATE entities SET attributes = ?"),
) -> mark("UPDATE entities SET attributes = ?"):
    sink("UPDATE entities SET attributes = ?")

@mark("UPDATE entities SET attributes = ?")
class Box(mark("UPDATE entities SET attributes = ?")):
    sink("UPDATE entities SET attributes = ?")
''',
    )

    sites = checker.find_write_sites(tmp_path)

    assert [(site.line, site.function) for site in sites] == [
        (1, "<module>"),
        (3, "<module>"),
        (4, "<module>"),
        (5, "<module>"),
        (8, "<module>"),
        (9, "<module>"),
        (10, "Box"),
        (6, "guarded"),
    ]


def test_current_repository_has_no_unapproved_direct_entity_writes():
    checker = _load_checker()
    discovered = {
        (site.path, site.function, site.kind)
        for site in checker.find_write_sites(ROOT)
    }
    assert discovered == EXPECTED_REPOSITORY_WRITE_SITES
    assert checker.ALLOWED_WRITE_SITES == EXPECTED_REPOSITORY_WRITE_SITES
    assert checker.unapproved_write_sites(ROOT) == []
