from database import (
    Database,
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
    # 74 -> 78 khi hợp NP-1: ba migration của nhánh đó được đánh số lại thành 076-078,
    # và code NP-1 đọc user_preferences/consents/events nên thật sự cần cả ba đã chạy.
    assert PG_REQUIRED_SCHEMA_VERSION == 78
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
    # Truyền đúng ngưỡng hiện hành để bài này CHỈ kiểm nhánh trigger, không lẫn thêm
    # khiếu nại schema_version (bản cũ ghim 74, nay ngưỡng là 78 nên nó sinh 2 issue).
    issues = _pg_schema_issues([], [], ["trg_entity_ratings on posts"], PG_REQUIRED_SCHEMA_VERSION)
    assert issues == ["missing triggers: trg_entity_ratings on posts"]


def test_pg_schema_status_redacts_connection_error_details(monkeypatch):
    detail = "credential-canary host-canary driver-canary dsn-canary"

    class FailingConnection:
        def __enter__(self):
            raise RuntimeError(detail)

        def __exit__(self, *_args):
            return None

    adapter = Database()
    adapter._use_pg = True
    adapter._dsn = None
    monkeypatch.setattr(adapter, "_conn", lambda: FailingConnection())

    status = adapter.pg_schema_status()

    assert status["error"] == "RuntimeError"
    assert all(token not in repr(status) for token in detail.split())
