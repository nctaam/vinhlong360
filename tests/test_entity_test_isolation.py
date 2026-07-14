import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CRITICAL_DECLARATIONS = (
    (
        "agent/tests/conftest.py",
        "def isolated_sqlite_db(tmp_path, monkeypatch):",
    ),
    (
        "agent/tests/conftest.py",
        'monkeypatch.setattr(database, "USE_PG", False)',
    ),
    (
        "agent/tests/conftest.py",
        'monkeypatch.setattr(database, "DATABASE_URL", "")',
    ),
    (
        "agent/tests/conftest.py",
        'instance = database.Database(str(tmp_path / "isolated.db"))',
    ),
    ("agent/tests/conftest.py", "assert instance._use_pg is False"),
    ("agent/tests/conftest.py", "assert instance._dsn is None"),
    ("agent/tests/conftest.py", "return instance"),
    (
        "agent/tests/test_admin_mutations.py",
        '_KNOWLEDGE_STATE_NAMES = (\n'
        '    "_entities",\n'
        '    "_relationships",\n'
        '    "_itineraries",\n'
        '    "_data_source",\n'
        '    "_adjacency",\n'
        '    "_adj_src",\n'
        ")",
    ),
    (
        "agent/tests/test_admin_mutations.py",
        "@pytest.fixture(autouse=True)\n"
        "def isolate_admin_database(isolated_sqlite_db, monkeypatch, "
        "knowledge_state_snapshot):",
    ),
    (
        "agent/tests/test_admin_mutations.py",
        "def knowledge_state_snapshot():",
    ),
    (
        "agent/tests/test_admin_mutations.py",
        'monkeypatch.setattr(database, "db", isolated_sqlite_db)',
    ),
    (
        "agent/tests/test_admin_mutations.py",
        'monkeypatch.setattr(admin, "db", isolated_sqlite_db)',
    ),
    (
        "agent/tests/test_admin_mutations.py",
        "for name, original in knowledge_state_snapshot.items():",
    ),
    (
        "agent/tests/test_admin_mutations.py",
        "setattr(knowledge, name, original)",
    ),
    (
        "agent/tests/test_kb_curation.py",
        "self, kb_with_provisional, isolated_sqlite_db, monkeypatch",
    ),
    (
        "agent/tests/test_kb_curation.py",
        'monkeypatch.setattr(database, "db", isolated_sqlite_db)',
    ),
    (
        "agent/tests/test_be_coverage.py",
        "def test_log_entity_changes_tracks_diffs(self, isolated_sqlite_db):",
    ),
    (
        "agent/tests/test_be_coverage.py",
        "def test_log_entity_changes_no_diff_no_record(self, isolated_sqlite_db):",
    ),
    (
        "agent/tests/test_be_coverage.py",
        'isolated_sqlite_db.log_entity_changes("test-entity", old, new)',
    ),
    (
        "agent/tests/test_be_coverage.py",
        'isolated_sqlite_db.log_entity_changes("test-entity", old, old)',
    ),
    (
        "agent/tests/test_entity_details_cleanup.py",
        "def _cleanup(isolated_sqlite_db, monkeypatch):",
    ),
    (
        "agent/tests/test_entity_details_cleanup.py",
        'monkeypatch.setattr(sys.modules[__name__], "db", isolated_sqlite_db)',
    ),
    (
        "agent/tests/test_entity_details_cleanup.py",
        'monkeypatch.setattr(cleanup_entity_jsonb, "db", isolated_sqlite_db)',
    ),
    (
        "agent/tests/test_entity_details_read_flip.py",
        "def _cleanup(isolated_sqlite_db, monkeypatch):",
    ),
    (
        "agent/tests/test_entity_details_read_flip.py",
        'monkeypatch.setattr(sys.modules[__name__], "db", isolated_sqlite_db)',
    ),
    (
        "agent/tests/test_entity_details_sync.py",
        "def _cleanup(isolated_sqlite_db, monkeypatch):",
    ),
    (
        "agent/tests/test_entity_details_sync.py",
        'monkeypatch.setattr(sys.modules[__name__], "db", isolated_sqlite_db)',
    ),
)


def _read_test_sources():
    return {
        relative_path: (ROOT / relative_path).read_text(encoding="utf-8")
        for relative_path in {path for path, _declaration in CRITICAL_DECLARATIONS}
    }


def _assert_entity_test_isolation(sources):
    for relative_path, declaration in CRITICAL_DECLARATIONS:
        assert declaration in sources[relative_path], (
            f"{relative_path} is missing isolation declaration: {declaration}"
        )

    be_coverage_tests = sources["agent/tests/test_be_coverage.py"]
    assert re.search(r"(?<![\w.])db\.log_entity_changes", be_coverage_tests) is None


def test_entity_mutation_tests_declare_temporary_database_isolation():
    _assert_entity_test_isolation(_read_test_sources())


@pytest.mark.parametrize(("relative_path", "declaration"), CRITICAL_DECLARATIONS)
def test_entity_isolation_guard_rejects_removed_critical_declaration(
    monkeypatch, relative_path, declaration
):
    target = (ROOT / relative_path).resolve()
    original_read_text = Path.read_text

    def read_with_declaration_removed(path, *args, **kwargs):
        source = original_read_text(path, *args, **kwargs)
        if path.resolve() == target:
            assert declaration in source
            return source.replace(declaration, "", 1)
        return source

    monkeypatch.setattr(Path, "read_text", read_with_declaration_removed)
    with pytest.raises(AssertionError):
        test_entity_mutation_tests_declare_temporary_database_isolation()
