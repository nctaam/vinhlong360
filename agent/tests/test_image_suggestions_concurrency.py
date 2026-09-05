"""Image suggestion uniqueness and approval race contracts."""

from pathlib import Path

import database as _database_module  # noqa: F401,E402
import image_suggestions


def test_pending_candidate_is_unique_even_when_precheck_races(monkeypatch, isolated_sqlite_db):
    monkeypatch.setattr(image_suggestions, "db", isolated_sqlite_db)
    monkeypatch.setattr(image_suggestions, "_table_ready", False)
    monkeypatch.setattr(image_suggestions, "_pending_exists", lambda *_args: False)

    first = image_suggestions.create_batch([
        {"entity_id": "entity-1", "candidate_url": "https://example.test/a.jpg"},
    ])
    second = image_suggestions.create_batch([
        {"entity_id": "entity-1", "candidate_url": "https://example.test/a.jpg"},
    ])

    assert first["created"] == 1
    assert second["created"] == 0
    with isolated_sqlite_db._conn() as conn:
        row = isolated_sqlite_db._fetchone(
            conn,
            "SELECT COUNT(*) AS c FROM image_suggestions WHERE entity_id=? AND candidate_url=? AND status='pending'",
            ("entity-1", "https://example.test/a.jpg"),
        )
    assert int(isolated_sqlite_db._row_to_dict(row)["c"]) == 1


def test_unique_index_is_partial_for_pending_status():
    migration = (Path(__file__).resolve().parents[1] / "migrations" / "090_image_suggestion_pending_unique.sql").read_text(encoding="utf-8")
    assert "UNIQUE INDEX" in migration
    assert "WHERE status = 'pending'" in migration
