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
