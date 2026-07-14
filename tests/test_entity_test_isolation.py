import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_entity_mutation_tests_declare_temporary_database_isolation():
    conftest = (ROOT / "agent" / "tests" / "conftest.py").read_text(encoding="utf-8")
    admin_tests = (
        ROOT / "agent" / "tests" / "test_admin_mutations.py"
    ).read_text(encoding="utf-8")
    kb_tests = (
        ROOT / "agent" / "tests" / "test_kb_curation.py"
    ).read_text(encoding="utf-8")
    be_coverage_tests = (
        ROOT / "agent" / "tests" / "test_be_coverage.py"
    ).read_text(encoding="utf-8")
    entity_detail_tests = [
        (ROOT / "agent" / "tests" / name).read_text(encoding="utf-8")
        for name in (
            "test_entity_details_cleanup.py",
            "test_entity_details_read_flip.py",
            "test_entity_details_sync.py",
        )
    ]
    assert "def isolated_sqlite_db" in conftest
    assert "def isolate_admin_database" in admin_tests
    assert "isolated_sqlite_db" in kb_tests
    assert "isolated_sqlite_db.log_entity_changes" in be_coverage_tests
    assert re.search(r"(?<![\w.])db\.log_entity_changes", be_coverage_tests) is None
    for source in entity_detail_tests:
        assert "monkeypatch.setattr(sys.modules[__name__], \"db\", isolated_sqlite_db)" in source
    assert (
        "monkeypatch.setattr(cleanup_entity_jsonb, \"db\", isolated_sqlite_db)"
        in entity_detail_tests[0]
    )
