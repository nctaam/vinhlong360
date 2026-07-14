from pathlib import Path

import pytest


@pytest.fixture
def cached_postgres_database_config(monkeypatch):
    import database

    monkeypatch.setattr(database, "USE_PG", True)
    monkeypatch.setattr(
        database,
        "DATABASE_URL",
        "postgresql://test-isolation.invalid/never-connect",
    )
    return database


def test_isolated_sqlite_db_overrides_cached_postgres_config(
    cached_postgres_database_config, request, tmp_path
):
    assert cached_postgres_database_config.USE_PG is True
    isolated_db = request.getfixturevalue("isolated_sqlite_db")

    assert isolated_db._use_pg is False
    assert isolated_db._dsn is None
    assert Path(isolated_db.db_path).parent == tmp_path
