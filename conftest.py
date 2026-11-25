"""Process-wide pytest safety rails that must run before test collection."""

import os
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent
PYTEST_BASETEMP = (ROOT / ".tmp" / "pytest").resolve()


def _temporary_database_path() -> Path:
    temporary_directory = Path(tempfile.mkdtemp(prefix="vinhlong360-pytest-")).resolve()
    protected_data_directory = (ROOT / "agent" / "data").resolve()
    if temporary_directory.is_relative_to(protected_data_directory):
        raise pytest.UsageError(
            "pytest temporary database directory must not be under agent/data; "
            f"configured pytest basetemp is {PYTEST_BASETEMP}"
        )
    return temporary_directory / "database.db"


def pytest_configure(config):
    """Bind the database singleton to one host-temporary SQLite file for pytest."""
    agent_dir = ROOT / "agent"
    if str(agent_dir) not in sys.path:
        sys.path.insert(0, str(agent_dir))

    # database.py snapshots this value at import time, so it cannot inherit CI's DSN.
    os.environ["DATABASE_URL"] = ""

    import database

    temporary_db = _temporary_database_path()
    database.DATABASE_URL = ""
    database.USE_PG = False
    database.DB_PATH = temporary_db
    database.db = database.Database(db_path=str(temporary_db))

    import agent

    sys.modules["agent.database"] = database
    agent.database = database


PROVINCE_DATA_TEST_PATHS: frozenset[str] = frozenset({
    "agent/tests/test_admin_mutations.py",
    "agent/tests/test_adversarial_architecture_remediation.py",
    "agent/tests/test_auto_learn_gaps.py",
    "agent/tests/test_discover_province_gaps.py",
    "agent/tests/test_kb_curation.py",
    "agent/tests/test_knowledge.py",
    "agent/tests/test_learn_loop.py",
    "agent/tests/test_learn_loop_gaps.py",
    "agent/tests/test_media_truth_manifest.py",
    "agent/tests/test_ocop.py",
    "agent/tests/test_phase16_coverage.py",
    "agent/tests/test_phat_hien_tu_doc_code.py",
    "agent/tests/test_public_api.py",
    "agent/tests/test_resilience.py",
    "agent/tests/test_seo.py",
    "agent/tests/test_seo_breadcrumb_admin_unit.py",
    "agent/tests/test_seo_structured.py",
    "tests/test_adversarial_challenger_1.py",
    "tests/test_backup_data.py",
    "tests/test_coords_guard.py",
    "tests/test_db_isolation_contract.py",
    "tests/test_entity_status_migration_guardrails.py",
    "tests/test_export_fe_data.py",
    "tests/test_place_admin_code.py",
    "tests/test_release_quality_gates.py",
    "tests/test_runtime_place_mappings.py",
    "tests/test_validate_data.py",
})


def pytest_collection_modifyitems(items):
    """Tag province-dataset-coupled tests so core vs province suites run independently."""
    marker = pytest.mark.province_data
    for item in items:
        try:
            rel = Path(str(item.path)).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if rel in PROVINCE_DATA_TEST_PATHS:
            item.add_marker(marker)
