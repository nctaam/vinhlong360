from database import (
    PG_REQUIRED_SCHEMA_VERSION,
    PG_REQUIRED_TRIGGERS,
    _pg_missing_triggers,
    _pg_schema_issues,
)


class TriggerCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = None

    def execute(self, sql, params=None):
        self.sql = " ".join(sql.split())
        self.params = params

    def fetchall(self):
        return self.rows


def test_required_schema_version_and_rating_trigger_registry():
    assert PG_REQUIRED_SCHEMA_VERSION == 71
    assert PG_REQUIRED_TRIGGERS == {
        "trg_entity_ratings": "posts",
        "trg_entity_ratings_del": "posts",
    }


def test_missing_trigger_scan_requires_name_and_table():
    cursor = TriggerCursor([
        {"trigger_name": "trg_entity_ratings", "table_name": "posts"},
        {"trigger_name": "trg_entity_ratings_del", "table_name": "wrong_table"},
    ])
    assert _pg_missing_triggers(cursor) == ["trg_entity_ratings_del on posts"]
    assert "pg_catalog.pg_trigger" in cursor.sql


def test_schema_issues_include_missing_triggers():
    issues = _pg_schema_issues([], [], ["trg_entity_ratings on posts"], 71)
    assert issues == ["missing triggers: trg_entity_ratings on posts"]
