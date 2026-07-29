from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "agent" / "migrations" / "071_restore_entity_rating_triggers.sql"


def test_migration_071_restores_both_rating_triggers_only():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "DROP TRIGGER IF EXISTS trg_entity_ratings ON posts" in sql
    assert "AFTER INSERT OR UPDATE ON posts" in sql
    assert "WHEN (NEW.post_type = 'review')" in sql
    assert "DROP TRIGGER IF EXISTS trg_entity_ratings_del ON posts" in sql
    assert "AFTER DELETE ON posts" in sql
    assert "WHEN (OLD.post_type = 'review')" in sql
    assert sql.count("EXECUTE FUNCTION update_entity_ratings()") == 2
    assert "CREATE OR REPLACE FUNCTION update_entity_ratings" not in sql
    assert "UPDATE entity_ratings" not in sql
    assert "VALUES ('agent', 71, '071_restore_entity_rating_triggers.sql'" in sql
