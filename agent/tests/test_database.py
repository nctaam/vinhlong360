"""
Tests cho tầng KB của database.py (GĐ1.1 — trước đây 0% coverage).

Bọc các hàm mà GĐ2/GĐ3 sẽ sửa nặng: upsert/get/list/count/search entity,
relationship (dedup), itinerary, migrate_from_json, replace_from_json (+ khoá GĐ0.5).
Chạy trên SQLite tạm, không đụng DB thật.
"""

import json
import inspect
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure agent/ on path (cùng pattern các test khác trong agent/tests/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import (  # noqa: E402
    Database,
    PG_REQUIRED_COLUMNS,
    PG_REQUIRED_SCHEMA_VERSION,
    PG_REQUIRED_TABLES,
    _validate_place_level,
    _coords_in_region,
    _coerce_iso_date,
    _normalize_entity_timestamps,
    canonical_verified_at,
)
import os  # noqa: E402
import database as database_module  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Database SQLite cô lập trong tmp_path. Ép sqlite + mở khoá replace cho test."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    d = Database(db_path=str(tmp_path / "test.db"))
    d._use_pg = False          # hằng USE_PG ở module — ép sqlite cho chắc
    d._dsn = None
    d.initialize()
    return d


def _entity(eid="e1", etype="dish", **kw):
    base = {
        "id": eid,
        "type": etype,
        "name": kw.get("name", "Bún bò"),
        "summary": kw.get("summary", "Món ngon"),
        "area": kw.get("area", "vinh-long"),
        "placeId": kw.get("placeId"),
        "attributes": kw.get("attributes", {"price": "50k"}),
        "season": kw.get("season"),
        "source": kw.get("source", {"title": "seed"}),
        "images": kw.get("images", []),
        "coordinates": kw.get("coordinates", [10.25, 105.97]),
        "confidence": kw.get("confidence", 0.8),
    }
    return base


# ── Schema ──

def test_initialize_creates_core_tables(db):
    with db._conn() as conn:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"entities", "relationships", "itineraries", "feedback", "query_log"} <= names

def test_pg_initialize_verifies_schema_before_legacy_repair_code():
    """Postgres startup must be migration-driven, not runtime schema repair.

    Refactor 2026-07-08: nhánh tạo-bảng/repair SQLite tách sang
    Database._init_sqlite_schema (extract-method giảm complexity). initialize()
    ở nhánh PG chỉ verify; ALTER TABLE / CREATE INDEX phải KHÔNG xuất hiện trong
    initialize() nữa (đã dời sang helper SQLite-only).
    """
    src = inspect.getsource(Database.initialize)
    assert "self._verify_pg_schema(conn)" in src
    # Nhánh PG (initialize) chỉ verify — tuyệt đối không repair schema lúc chạy
    assert "ALTER TABLE" not in src
    assert "CREATE INDEX" not in src
    assert "conn.executescript" not in src
    # Code tạo bảng/repair sống trong helper SQLite-only, KHÔNG chạy cho PG
    sqlite_src = inspect.getsource(Database._init_sqlite_schema)
    assert "if not self._use_pg:" in sqlite_src
    assert "ALTER TABLE" in sqlite_src
    verify_src = inspect.getsource(Database._verify_pg_schema)
    assert "ALTER TABLE" not in verify_src
    assert "CREATE INDEX" not in verify_src

def test_pg_schema_contract_tracks_latest_release_tables():
    # 71 phục hồi trigger rating; 72-74 thêm feedback + vòng đời xoá tài khoản;
    # 75 index đường nóng; 76-78 là NP-1 identity/location/trust (đánh số lại khi hợp).
    assert PG_REQUIRED_SCHEMA_VERSION == 78
    assert {"schema_version", "admin_audit_events", "shared_rate_limits", "request_idempotency_keys"} <= PG_REQUIRED_TABLES
    assert {"feedback_receipts", "feedback_daily_rollups"} <= PG_REQUIRED_TABLES
    assert {"entity_changes", "site_settings_history"} <= PG_REQUIRED_TABLES
    assert {
        "user_preferences",
        "user_preference_consents",
        "user_personalization_events",
        "personalization_legacy_purge_queue",
    } <= PG_REQUIRED_TABLES
    assert {f"entity_{k}_details" for k in
            ("place", "food", "product", "lodging", "event",
             "experience", "facility", "person", "adminplace")} <= PG_REQUIRED_TABLES
    assert {"key", "hits", "expires_at", "updated_at"} <= PG_REQUIRED_COLUMNS["shared_rate_limits"]
    assert {"key", "first_seen_at", "expires_at", "meta"} <= PG_REQUIRED_COLUMNS["request_idempotency_keys"]
    assert {"token_digest", "owner_binding_digest", "expires_at"} <= PG_REQUIRED_COLUMNS["feedback_receipts"]
    assert {"day", "positive_count", "negative_count"} <= PG_REQUIRED_COLUMNS["feedback_daily_rollups"]
    assert "bucket" not in PG_REQUIRED_COLUMNS["shared_rate_limits"]
    assert "response_json" not in PG_REQUIRED_COLUMNS["request_idempotency_keys"]
    assert {
        "location_reconfirm_required",
        "location_provenance_version",
    } <= PG_REQUIRED_COLUMNS["user_preferences"]


_NP1_REQUIRED_COLUMNS = {
    "user_preferences": {
        "user_id", "region_id", "region_label", "region_scope",
        "location_source", "location_accuracy", "location_consent_state",
        "location_enabled", "personalization_enabled", "explicit_interests",
        "recommendation_reset_at", "consent_version", "revision",
        "location_reconfirm_required", "location_provenance_version",
        "created_at", "updated_at",
    },
    "user_preference_consents": {
        "id", "user_id", "consent_type", "state", "version", "created_at",
    },
    "user_personalization_events": {
        "id", "user_id", "event_type", "context", "entity_id",
        "entity_type", "area_id", "interest_keys", "occurred_at", "expires_at",
    },
    "personalization_legacy_purge_queue": {
        "user_id", "created_at", "attempt_count", "next_attempt_at", "last_error",
    },
}


class _SchemaReadinessCursor:
    """Test double cho vòng kiểm schema lúc khởi động Postgres.

    Nhánh NP-1 viết class này TRƯỚC khi `main` thêm bước kiểm trigger
    (`PG_REQUIRED_TRIGGERS`, `agent/database.py`), nên khi hợp hai nhánh thì mọi
    bài dùng nó nổ `unexpected readiness query`. Thêm nhánh `pg_trigger` để double
    phủ đúng những gì code thật hỏi — KHÔNG nới assertion để test xanh.
    """

    def __init__(self, *, tables, columns, version, triggers=None):
        self.tables = set(tables)
        self.columns = {table: set(values) for table, values in columns.items()}
        self.version = version
        # Mặc định = đủ trigger, để các bài đang kiểm THIẾU BẢNG/THIẾU CỘT không bị
        # trượt vì một lý do khác. Bài nào muốn kiểm thiếu trigger thì truyền vào.
        self.triggers = dict(database_module.PG_REQUIRED_TRIGGERS) if triggers is None else dict(triggers)
        self.rows = []

    def execute(self, sql, params=None):
        if "information_schema.tables" in sql:
            self.rows = [{"table_name": table} for table in sorted(self.tables)]
        elif "information_schema.columns" in sql:
            self.rows = [
                {"column_name": column}
                for column in sorted(self.columns.get(params[0], set()))
            ]
        elif "MAX(version)" in sql:
            self.rows = [{"version": self.version}]
        elif "pg_trigger" in sql or "tgname" in sql:
            self.rows = [
                {"trigger_name": name, "table_name": table}
                for name, table in sorted(self.triggers.items())
            ]
        else:
            raise AssertionError(f"unexpected readiness query: {sql}")

    def fetchall(self):
        return list(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _SchemaReadinessConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, **_kwargs):
        return self._cursor


@pytest.fixture(autouse=True)
def _restore_database_psycopg2():
    """Trả `database.psycopg2` về nguyên trạng sau MỖI bài trong file này.

    `_release_schema()` bên dưới thay nó bằng một `SimpleNamespace` để giả lập vòng
    kiểm schema, và bản gốc KHÔNG bao giờ khôi phục. Hậu quả chỉ lộ trên Postgres và
    chỉ khi chạy CẢ BỘ: mọi bài chạy SAU trong cùng tiến trình gọi `psycopg2.connect`
    đều chết với `'SimpleNamespace' object has no attribute 'connect'` — CI đếm được
    54 failed + 9 errors, gần hết nằm ở agent/tests/test_integration_api.py, và không
    bài nào trong số đó có lỗi thật.

    Đây là rò trạng thái global giữa các file test, không phải lỗi sản phẩm. Fixture
    autouse chặn cả những lần dùng về sau, không riêng chỗ hiện tại.
    """
    # `database.py` chỉ `import psycopg2` khi USE_PG, nên thuộc tính có thể KHÔNG
    # tồn tại (chạy SQLite). Dùng sentinel để trả đúng trạng thái ban đầu — gán đại
    # `None` sẽ tạo ra một thuộc tính chưa từng có.
    missing = object()
    original = getattr(database_module, "psycopg2", missing)
    try:
        yield
    finally:
        if original is missing:
            if hasattr(database_module, "psycopg2"):
                delattr(database_module, "psycopg2")
        else:
            database_module.psycopg2 = original


def test_release_schema_helper_does_not_leak_psycopg2():
    """Chốt chặn cho chính fixture trên — nếu ai gỡ nó, bài này đỏ."""
    _release_schema(version=database_module.PG_REQUIRED_SCHEMA_VERSION)
    assert isinstance(database_module.psycopg2, SimpleNamespace), (
        "_release_schema phải thay psycopg2 — nếu không, bài này vô nghĩa"
    )


def test_psycopg2_is_intact_after_release_schema():
    """Chạy SAU bài trên (pytest giữ thứ tự khai báo): psycopg2 phải nguyên vẹn."""
    leftover = getattr(database_module, "psycopg2", None)
    assert not isinstance(leftover, SimpleNamespace), (
        "psycopg2 còn là test double sau bài trước — fixture khôi phục đã bị gỡ"
    )


def _release_schema(*, version=73, missing_table=None, missing_column=None):
    database_module.psycopg2 = SimpleNamespace(
        extras=SimpleNamespace(RealDictCursor=object)
    )
    tables = set(PG_REQUIRED_TABLES) | set(_NP1_REQUIRED_COLUMNS)
    columns = {
        table: set(values) for table, values in PG_REQUIRED_COLUMNS.items()
    }
    columns.update({
        table: set(values) for table, values in _NP1_REQUIRED_COLUMNS.items()
    })
    if missing_table:
        tables.remove(missing_table)
    if missing_column:
        table, column = missing_column
        columns[table].remove(column)
    return _SchemaReadinessConnection(
        _SchemaReadinessCursor(tables=tables, columns=columns, version=version)
    )


def test_pg_startup_rejects_schema_version_72():
    """Ngưỡng lấy từ hằng số, không gõ cứng.

    Bản NP-1 gõ cứng `expected >= 73` vì đó là migration mới nhất CỦA NÓ. Sau khi hợp
    vào main, ba migration của nó được đánh số lại 076-078 nên ngưỡng thành 78 — gõ
    cứng thì lần bump tới lại đỏ vì một lý do vô nghĩa.
    """
    database = Database.__new__(Database)

    expected = database_module.PG_REQUIRED_SCHEMA_VERSION
    assert expected >= 78, "hợp NP-1 vào thì ngưỡng phải tính cả migration 076-078"
    with pytest.raises(
        RuntimeError, match=rf"schema_version agent=72, expected >= {expected}"
    ):
        database._verify_pg_schema(_release_schema(version=72))


@pytest.mark.parametrize("table", sorted(_NP1_REQUIRED_COLUMNS))
def test_pg_startup_rejects_each_missing_np1_table(table):
    database = Database.__new__(Database)

    with pytest.raises(RuntimeError, match=rf"missing tables:.*{table}"):
        database._verify_pg_schema(_release_schema(missing_table=table))


@pytest.mark.parametrize(
    ("table", "column"),
    [
        (table, column)
        for table, columns in sorted(_NP1_REQUIRED_COLUMNS.items())
        for column in sorted(columns)
    ],
)
def test_pg_startup_rejects_each_missing_np1_column(table, column):
    database = Database.__new__(Database)

    with pytest.raises(RuntimeError, match=rf"missing columns:.*{table}\.{column}"):
        database._verify_pg_schema(
            _release_schema(missing_column=(table, column))
        )


# ── Entity CRUD + JSON round-trip ──

def test_upsert_get_entity_roundtrip(db):
    db.upsert_entity(_entity(eid="e1", attributes={"price": "50k", "hours": "7-22"},
                             coordinates=[10.25, 105.97], season={"months": [6, 7]}))
    got = db.get_entity("e1")
    assert got is not None
    assert got["name"] == "Bún bò"
    # JSON fields phải được parse lại thành object (không phải chuỗi)
    assert got["attributes"] == {"price": "50k", "hours": "7-22"}
    assert got["coordinates"] == [10.25, 105.97]
    assert got["season"] == {"months": [6, 7]}


def test_upsert_is_update_on_same_id(db):
    db.upsert_entity(_entity(eid="e1", name="A"))
    db.upsert_entity(_entity(eid="e1", name="B"))
    assert db.get_entity("e1")["name"] == "B"
    assert db.count_entities().get("dish", 0) == 1


def test_upsert_preserves_publication_fields_when_omitted(db):
    db.upsert_entity({
        "id": "publication-preserve",
        "type": "dish",
        "name": "Initial",
        "status": "published",
        "verified": False,
    })
    db.upsert_entity({
        "id": "publication-preserve",
        "type": "dish",
        "name": "Updated",
    })
    saved = db.get_entity("publication-preserve")
    assert saved["status"] == "published"
    assert saved["verified"] in (False, 0)


def test_upsert_changes_publication_fields_only_when_explicit(db):
    db.upsert_entity({
        "id": "publication-explicit",
        "type": "dish",
        "name": "Initial",
        "status": "provisional",
        "verified": False,
    })
    db.upsert_entity({
        "id": "publication-explicit",
        "type": "dish",
        "name": "Approved",
        "status": "verified",
        "verified": True,
    })
    saved = db.get_entity("publication-explicit")
    assert saved["status"] == "verified"
    assert saved["verified"] in (True, 1)


def test_pg_upsert_publication_sql_and_parameter_order(monkeypatch):
    db = Database(db_path="unused.db")
    db._use_pg = True
    captured = {}

    def capture_execute(conn, sql, params=None):
        captured["sql"] = " ".join(sql.split())
        captured["params"] = params

    monkeypatch.setattr(db, "_execute", capture_execute)
    entity = {
        "id": "pg-publication-contract",
        "type": "dish",
        "name": "Contract",
        "status": "published",
    }
    db._write_entity_row(
        object(), entity, None, {}, [], [], None, "2026-07-14"
    )

    assert '"legacyArea", status, verified)' in captured["sql"]
    assert captured["sql"].count("%s") == 21
    assert "status = CASE WHEN %s THEN EXCLUDED.status ELSE entities.status END" in captured["sql"]
    assert "verified = CASE WHEN %s THEN EXCLUDED.verified ELSE entities.verified END" in captured["sql"]
    assert captured["params"][-4:] == ("published", True, True, False)


def test_upsert_refreshes_external_content_fts_without_rowid_drift(db):
    with db._conn() as conn:
        try:
            conn.execute("SELECT rowid FROM entities_fts LIMIT 1").fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table: entities_fts" in str(exc) or "no such module: fts5" in str(exc):
                pytest.skip("SQLite build does not provide FTS5")
            raise

    entity_id = "fts-rowid-alignment"
    db.upsert_entity({
        "id": entity_id,
        "type": "attraction",
        "name": "olduniqueterm attraction",
        "summary": "oldsummaryterm",
    })
    with db._conn() as conn:
        original_rowid = conn.execute(
            "SELECT rowid FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()["rowid"]

    db.upsert_entity({
        "id": entity_id,
        "type": "attraction",
        "name": "newuniqueterm attraction",
        "summary": "newsummaryterm",
    })

    with db._conn() as conn:
        current_rowid = conn.execute(
            "SELECT rowid FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()["rowid"]
        new_matches = conn.execute(
            "SELECT rowid, id, name FROM entities_fts WHERE entities_fts MATCH ?",
            ("newuniqueterm",),
        ).fetchall()
        old_matches = conn.execute(
            "SELECT rowid, id FROM entities_fts WHERE entities_fts MATCH ?",
            ("olduniqueterm",),
        ).fetchall()

    assert current_rowid == original_rowid
    assert [(row["id"], row["name"]) for row in new_matches] == [
        (entity_id, "newuniqueterm attraction")
    ]
    assert new_matches[0]["rowid"] == current_rowid
    assert old_matches == []


def test_get_missing_entity_returns_none(db):
    assert db.get_entity("khong-ton-tai") is None


def test_delete_entity_removes_entity_and_relationships(db):
    db.upsert_entity(_entity(eid="e1"))
    db.upsert_entity(_entity(eid="e2"))
    db.add_relationship("e1", "e2", "near")
    assert db.delete_entity("e1") is True
    assert db.get_entity("e1") is None
    with db._conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM relationships WHERE from_id='e1' OR to_id='e1'").fetchone()[0]
    assert n == 0


# ── List / count / search loại trừ type='place' (hợp đồng public) ──

def test_list_and_count_exclude_place(db):
    db.upsert_entity(_entity(eid="d1", etype="dish"))
    db.upsert_entity(_entity(eid="p1", etype="place", name="Xã A"))
    listed_ids = {e["id"] for e in db.list_entities()}
    assert "d1" in listed_ids and "p1" not in listed_ids
    counts = db.count_entities()
    assert "place" not in counts and counts.get("dish") == 1


def test_list_filter_by_type(db):
    db.upsert_entity(_entity(eid="d1", etype="dish"))
    db.upsert_entity(_entity(eid="a1", etype="attraction"))
    ids = {e["id"] for e in db.list_entities(entity_type="attraction")}
    assert ids == {"a1"}


def test_count_entities_filtered_by_query(db):
    db.upsert_entity(_entity(eid="d1", name="Bánh xèo", etype="dish"))
    db.upsert_entity(_entity(eid="d2", name="Hủ tiếu", etype="dish"))
    assert db.count_entities_filtered(q="Bánh") == 1
    assert db.count_entities_filtered(entity_type="dish") == 2


# ── Relationships ──

def test_add_relationship_dedup(db):
    """INSERT OR IGNORE: thêm cạnh trùng (from,to,type) chỉ lưu 1 lần.

    Ghi lại hành vi mất-mát mà GĐ3.2 sẽ giám sát khi migrate.
    """
    db.upsert_entity(_entity(eid="e1"))
    db.upsert_entity(_entity(eid="e2"))
    db.add_relationship("e1", "e2", "near")
    db.add_relationship("e1", "e2", "near")  # trùng
    with db._conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    assert n == 1


# ── Itineraries ──

def test_itinerary_roundtrip(db):
    it = {"id": "it1", "title": "1 ngày Vĩnh Long", "area": "vinh-long",
          "areas": ["vinh-long", "ben-tre"], "duration": "1 ngày", "summary": "x",
          "stops": [{"name": "A"}, {"name": "B"}]}
    db.upsert_itinerary(it)
    got = db.get_itinerary("it1")
    assert got["title"] == "1 ngày Vĩnh Long"
    assert got["areas"] == ["vinh-long", "ben-tre"]
    assert isinstance(got["stops"], list) and len(got["stops"]) == 2
    assert {i["id"] for i in db.list_itineraries()} == {"it1"}
    assert {i["id"] for i in db.list_itineraries(area="ben-tre")} == {"it1"}


# ── migrate_from_json ──

def test_migrate_from_json_roundtrip(db, tmp_path):
    data = {
        "entities": [_entity(eid="d1", etype="dish"), _entity(eid="p1", etype="place", name="Xã A")],
        "relationships": [
            {"from": "d1", "to": "p1", "type": "located_in"},
            {"from": "d1", "to": "p1", "type": "located_in"},  # trùng -> dedup khi lưu
        ],
        "itineraries": [{"id": "it1", "title": "T", "stops": []}],
    }
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    res = db.migrate_from_json(str(p))
    assert res["entities"] == 2
    assert res["itineraries"] == 1
    # report đếm số cạnh hợp lệ (2) nhưng lưu chỉ 1 do dedup -> bằng chứng mất-mát
    assert res["relationships"] == 2
    with db._conn() as conn:
        stored = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    assert stored == 1
    assert db.get_entity("d1") is not None and db.get_entity("p1") is not None


# ── replace_from_json + khoá GĐ0.5 ──

def test_replace_from_json_locked_by_default(db, tmp_path, monkeypatch):
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_DB_REPLACE", raising=False)
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"entities": [], "relationships": [], "itineraries": []}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="khoá|locked|DESTRUCTIVE"):
        db.replace_from_json(str(p))


def test_replace_from_json_with_override_roundtrip(db, tmp_path, monkeypatch):
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    db.upsert_entity(_entity(eid="old", etype="dish"))  # sẽ bị thay
    data = {
        "entities": [_entity(eid="new1", etype="attraction", name="Mới")],
        "relationships": [],
        "itineraries": [],
    }
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    db.replace_from_json(str(p))
    assert db.get_entity("old") is None
    assert db.get_entity("new1")["name"] == "Mới"


def test_replace_from_json_replaces_detail_cache_instead_of_merging(db, tmp_path, monkeypatch):
    import entity_details
    from config import settings

    monkeypatch.setattr(settings, "ENTITY_DETAILS_TABLES", True)
    db.reload_entity_details_cache()
    db.upsert_entity(_entity(
        eid="old-cache", etype="product", attributes={"producer": "Old"}))
    payload = {
        "entities": [_entity(
            eid="new-cache", etype="product", attributes={"producer": "New"})],
        "relationships": [],
        "itineraries": [],
    }
    path = tmp_path / "replace-cache.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")

    db.replace_from_json(str(path))

    assert "old-cache" not in (entity_details._DETAIL_CACHE or {})
    assert (entity_details._DETAIL_CACHE or {})["new-cache"]["producer"] == "New"


@pytest.mark.parametrize("later_operation", ["upsert", "delete", "replace"])
def test_detail_cache_publication_follows_commit_order_across_mutating_paths(
    db, tmp_path, monkeypatch, later_operation
):
    import threading

    import entity_details
    from config import settings

    monkeypatch.setattr(settings, "ENTITY_DETAILS_TABLES", True)
    db.reload_entity_details_cache()
    entity_id = f"ordered-cache-{later_operation}"
    db.upsert_entity(_entity(
        eid=entity_id, etype="product", attributes={"producer": "Seed"}))

    replacement_id = f"replacement-cache-{later_operation}"
    replacement_path = tmp_path / f"replace-{later_operation}.json"
    replacement_path.write_text(json.dumps({
        "entities": [_entity(
            eid=replacement_id,
            etype="product",
            attributes={"producer": "Replacement"},
        )],
        "relationships": [],
        "itineraries": [],
    }), encoding="utf-8")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")

    real_apply = entity_details.apply_detail_cache_mutations
    first_apply_started = threading.Event()
    later_apply_finished = threading.Event()
    call_lock = threading.Lock()
    call_count = 0

    def pause_first_apply(*args, **kwargs):
        nonlocal call_count
        with call_lock:
            call_index = call_count
            call_count += 1
        if call_index == 0:
            first_apply_started.set()
            later_apply_finished.wait(timeout=2)
            return real_apply(*args, **kwargs)
        try:
            return real_apply(*args, **kwargs)
        finally:
            later_apply_finished.set()

    monkeypatch.setattr(entity_details, "apply_detail_cache_mutations", pause_first_apply)
    errors = []

    def capture_error(operation):
        try:
            operation()
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    first = threading.Thread(target=lambda: capture_error(lambda: db.upsert_entity(_entity(
        eid=entity_id, etype="product", attributes={"producer": "First"}))))
    first.start()
    assert first_apply_started.wait(timeout=5)

    def run_later_operation():
        if later_operation == "upsert":
            db.upsert_entity(_entity(
                eid=entity_id, etype="product", attributes={"producer": "Second"}))
        elif later_operation == "delete":
            db.delete_entity(entity_id)
        else:
            db.replace_from_json(str(replacement_path))

    later = threading.Thread(target=lambda: capture_error(run_later_operation))
    later.start()
    first.join(timeout=10)
    later.join(timeout=10)

    assert not first.is_alive() and not later.is_alive()
    assert errors == []
    cache = entity_details._DETAIL_CACHE or {}
    with db._conn() as conn:
        entity_exists = conn.execute(
            "SELECT 1 FROM entities WHERE id = ?", (entity_id,)).fetchone()
        detail = conn.execute(
            "SELECT producer FROM entity_product_details WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()

    if later_operation == "upsert":
        assert detail[0] == "Second"
        assert cache[entity_id]["producer"] == "Second"
    elif later_operation == "delete":
        assert entity_exists is None
        assert entity_id not in cache
    else:
        assert entity_exists is None
        assert entity_id not in cache
        assert cache[replacement_id]["producer"] == "Replacement"


@pytest.mark.parametrize("operation", ["upsert", "delete", "replace"])
def test_committed_close_failure_does_not_skip_detail_cache_publication(
    db, tmp_path, monkeypatch, caplog, operation
):
    import entity_details
    from config import settings

    monkeypatch.setattr(settings, "ENTITY_DETAILS_TABLES", True)
    db.reload_entity_details_cache()
    entity_id = f"committed-close-{operation}"
    if operation in {"delete", "replace"}:
        db.upsert_entity(
            _entity(
                eid=entity_id,
                etype="product",
                attributes={"producer": "Before"},
            )
        )

    replacement_id = "committed-close-replacement"
    replacement_path = tmp_path / "committed-close-replace.json"
    replacement_path.write_text(
        json.dumps(
            {
                "entities": [
                    _entity(
                        eid=replacement_id,
                        etype="product",
                        attributes={"producer": "Replacement"},
                    )
                ],
                "relationships": [],
                "itineraries": [],
            }
        ),
        encoding="utf-8",
    )

    real_connect = sqlite3.connect
    sensitive_cleanup_error = (
        "postgresql://cleanup-user-canary:cleanup-pass-canary@cleanup-host-canary/db"
    )

    class CloseFailureConnection:
        def __init__(self, connection):
            self._connection = connection

        @property
        def row_factory(self):
            return self._connection.row_factory

        @row_factory.setter
        def row_factory(self, value):
            self._connection.row_factory = value

        def __getattr__(self, name):
            return getattr(self._connection, name)

        def close(self):
            self._connection.close()
            raise RuntimeError(sensitive_cleanup_error)

    database_path = Path(db.db_path).resolve()

    def connect(path, *args, **kwargs):
        connection = real_connect(path, *args, **kwargs)
        if Path(path).resolve() == database_path:
            return CloseFailureConnection(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)
    caplog.set_level("WARNING", logger="database")

    if operation == "upsert":
        db.upsert_entity(
            _entity(
                eid=entity_id,
                etype="product",
                attributes={"producer": "After"},
            )
        )
    elif operation == "delete":
        assert db.delete_entity(entity_id) is True
    else:
        monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
        monkeypatch.setattr(db, "backup", lambda: str(tmp_path / "backup.db"))
        db.replace_from_json(str(replacement_path))

    cache = entity_details._DETAIL_CACHE or {}
    if operation == "upsert":
        assert cache[entity_id]["producer"] == "After"
    elif operation == "delete":
        assert entity_id not in cache
    else:
        assert entity_id not in cache
        assert cache[replacement_id]["producer"] == "Replacement"
    assert "RuntimeError" in caplog.text
    for canary in ("cleanup-user-canary", "cleanup-pass-canary", "cleanup-host-canary"):
        assert canary not in caplog.text


def test_replace_from_json_auto_backup_stays_next_to_custom_db(db, tmp_path, monkeypatch):
    import database

    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    legacy_global = tmp_path / "legacy-global-replace"
    legacy_global.mkdir()
    monkeypatch.setattr(database, "DB_DIR", legacy_global)
    db.upsert_entity(_entity(eid="old-backup-location"))
    data_path = tmp_path / "replace-backup-location.json"
    data_path.write_text(json.dumps({
        "entities": [_entity(eid="new-backup-location")],
        "relationships": [],
        "itineraries": [],
    }, ensure_ascii=False), encoding="utf-8")

    try:
        result = db.replace_from_json(str(data_path))
        backup_path = Path(result["backup"])
        assert backup_path.parent == Path(db.db_path).parent
        assert backup_path.parent != legacy_global
        assert backup_path.name.startswith("vinhlong360_backup_")
        assert backup_path.suffix == ".db"
    finally:
        for directory in (Path(db.db_path).parent, legacy_global):
            for generated in directory.glob("vinhlong360_backup_*.db"):
                generated.unlink()


def test_replace_from_json_roundtrip_with_rels_itins(db, tmp_path, monkeypatch):
    """Replace nạp đủ entity + relationship + itinerary; xoá row cũ (stale)."""
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    db.upsert_entity(_entity(eid="stale"))  # phải biến mất sau replace
    data = {
        "entities": [_entity(eid="a"), _entity(eid="b")],
        "relationships": [{"from": "a", "to": "b", "type": "near"}],
        "itineraries": [{"id": "it1", "title": "T", "area": "vinh-long", "areas": ["vinh-long", "ben-tre"], "stops": [{"name": "A"}]}],
    }
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    db.replace_from_json(str(p))
    assert db.get_entity("stale") is None
    assert db.get_entity("a") and db.get_entity("b")
    assert db.all_relationships() == [{"from": "a", "to": "b", "type": "near"}]
    its = db.all_itineraries()
    assert len(its) == 1 and its[0]["id"] == "it1"
    assert its[0]["areas"] == ["vinh-long", "ben-tre"]


def test_replace_from_json_atomic_rollback(db, tmp_path, monkeypatch):
    """ATOMIC (F1): insert lỗi giữa chừng → DELETE rollback → data CŨ còn nguyên,
    KHÔNG để DB rỗng. (Hợp-nhất path: SQLite+PG cùng 1 transaction qua _bulk_load.)"""
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    db.upsert_entity(_entity(eid="old", name="Cũ"))
    data = {"entities": [_entity(eid="new1")], "relationships": [], "itineraries": []}
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def boom(conn, d):
        conn.execute("INSERT OR REPLACE INTO entities (id, type, name) VALUES ('partial','dish','X')")
        raise RuntimeError("simulated crash mid-insert")
    monkeypatch.setattr(db, "_bulk_load", boom)

    with pytest.raises(RuntimeError):
        db.replace_from_json(str(p))
    # DELETE + partial-INSERT đều rollback trong 1 transaction
    assert db.get_entity("old") is not None, "data cũ phải còn (transaction rollback)"
    assert db.get_entity("new1") is None
    assert db.get_entity("partial") is None


# ── Bulk getters (GĐ3.4: nguồn nạp knowledge in-memory) ──

def test_all_entities_includes_place(db):
    db.upsert_entity(_entity(eid="d1", etype="dish"))
    db.upsert_entity(_entity(eid="p1", etype="place", name="Xã A"))
    ids = {e["id"] for e in db.all_entities()}
    assert ids == {"d1", "p1"}  # KHÁC list_entities: gồm cả place


def test_all_relationships_shape(db):
    db.upsert_entity(_entity(eid="e1"))
    db.upsert_entity(_entity(eid="e2"))
    db.add_relationship("e1", "e2", "near")
    rels = db.all_relationships()
    assert rels == [{"from": "e1", "to": "e2", "type": "near"}]


def test_all_itineraries(db):
    db.upsert_itinerary({"id": "it1", "title": "T", "stops": [{"name": "A"}]})
    its = db.all_itineraries()
    assert len(its) == 1 and its[0]["id"] == "it1" and isinstance(its[0]["stops"], list)


# ── D02: PG connection pool — kill-switch + fallback (an-toàn, không cần PG thật) ──

def test_pg_pool_kill_switch(tmp_path, monkeypatch):
    """PG_USE_POOL=false → _get_pg_pool trả None (dùng connect-trực-tiếp)."""
    d = Database(db_path=str(tmp_path / "t.db"))
    d._use_pg = True
    d._dsn = "postgresql://x@127.0.0.1:5432/x"
    monkeypatch.setenv("PG_USE_POOL", "false")
    assert d._get_pg_pool() is None


def test_pg_pool_fallback_on_bad_dsn(tmp_path, monkeypatch):
    """DSN lỗi → tạo pool raise → fallback None + đánh dấu failed (không crash)."""
    d = Database(db_path=str(tmp_path / "t.db"))
    d._use_pg = True
    d._dsn = "not-a-valid-dsn"
    monkeypatch.setenv("PG_USE_POOL", "true")
    assert d._get_pg_pool() is None
    assert d._pg_pool_failed is True


def test_pg_pool_default_off(tmp_path, monkeypatch):
    """OPT-IN: KHÔNG set PG_USE_POOL → pool OFF (connect-trực-tiếp). Khoá incident-fix
    2026-06-22 (pool treo agent startup prod). Pool chỉ bật khi PG_USE_POOL=true tường minh."""
    d = Database(db_path=str(tmp_path / "t.db"))
    d._use_pg = True
    d._dsn = "postgresql://x@127.0.0.1:5432/x"
    monkeypatch.delenv("PG_USE_POOL", raising=False)
    assert d._get_pg_pool() is None


# ── GĐ13.3: danh bạ hành chính (facility theo placeId) ──

def test_facilities_by_place(db):
    db.upsert_entity({"id": "ubnd-xa-a", "type": "facility", "name": "UBND xã A",
                      "placeId": "xa-a",
                      "attributes": {"office_kind": "ubnd", "address": "Số 1", "phone": "0270..."}})
    db.upsert_entity({"id": "ca-xa-a", "type": "facility", "name": "Công an xã A",
                      "placeId": "xa-a", "attributes": {"office_kind": "cong_an"}})
    db.upsert_entity({"id": "ubnd-xa-b", "type": "facility", "name": "UBND xã B", "placeId": "xa-b"})

    a = db.facilities_by_place("xa-a")
    assert {f["id"] for f in a} == {"ubnd-xa-a", "ca-xa-a"}
    assert a[0]["attributes"].get("office_kind") in ("ubnd", "cong_an")  # JSON attrs parse lại
    assert {f["id"] for f in db.facilities_by_place("xa-b")} == {"ubnd-xa-b"}
    assert db.facilities_by_place("khong-co") == []
    assert len(db.facilities_by_place()) == 3  # tất cả facility


def test_upsert_accepts_coords_alias(db):
    # GĐ-audit: ETL/auto_learn ghi entity["coords"] (legacy) — upsert phải map sang coordinates
    # để không mất toạ độ đã geocode.
    db.upsert_entity({"id": "e-coords", "type": "attraction", "name": "Điểm có coords",
                      "coords": [10.25, 105.97]})
    e = db.get_entity("e-coords")
    assert e.get("coordinates") == [10.25, 105.97]
    # "coordinates" vẫn được ưu tiên nếu có cả hai
    db.upsert_entity({"id": "e-both", "type": "attraction", "name": "X",
                      "coordinates": [10.25, 105.97], "coords": [10.30, 106.00]})
    assert db.get_entity("e-both").get("coordinates") == [10.25, 105.97]


def test_entities_by_place(db):
    # Trang hub xã/phường: gom mọi entity nội dung theo placeId, trừ chính các place.
    db.upsert_entity({"id": "xa-h", "type": "place", "name": "Xã H", "placeId": None})
    db.upsert_entity({"id": "diem-1", "type": "attraction", "name": "Điểm 1", "placeId": "xa-h"})
    db.upsert_entity({"id": "ks-1", "type": "accommodation", "name": "KS 1", "placeId": "xa-h"})
    db.upsert_entity({"id": "sp-1", "type": "product", "name": "SP 1", "placeId": "xa-h"})
    db.upsert_entity({"id": "diem-x", "type": "attraction", "name": "Điểm X", "placeId": "xa-khac"})

    got = db.entities_by_place("xa-h")
    ids = {e["id"] for e in got}
    assert ids == {"diem-1", "ks-1", "sp-1"}          # đúng ward, gồm nhiều type
    assert "xa-h" not in ids                          # KHÔNG gồm chính đơn vị place
    assert "diem-x" not in ids                        # KHÔNG gồm ward khác
    assert db.entities_by_place("khong-co") == []


# ── GĐ3.8: data-quality apply/rollback DB-native (không DELETE-reload-json) ──

def test_data_quality_apply_and_rollback_db_native(db, tmp_path, monkeypatch):
    import data_quality

    db.upsert_entity(_entity(eid="e1", etype="dish",
                             source={"title": "old", "url": "https://old.example/"}))
    monkeypatch.setattr(data_quality, "db", db)          # apply/rollback dùng temp DB
    monkeypatch.setattr(data_quality, "BURST_DIR", tmp_path)  # cô lập apply_history

    cand = {
        "candidate_id": "c1", "entity_id": "e1", "field": "source",
        "apply_policy": "auto_apply", "url_verified": True,
        "suggested_value": {"title": "New", "url": "https://new.example/page"},
        "evidence_urls": ["https://new.example/page"], "confidence": 0.9,
    }
    monkeypatch.setattr(data_quality, "load_candidate_queue", lambda **k: {"auto_apply": [cand]})

    res = data_quality.apply_candidates(["c1"], dry_run=False)
    assert res["applied_count"] == 1
    # ghi THẲNG vào DB (không qua data.json)
    src = db.get_entity("e1")["source"]
    assert (src[0]["url"] if isinstance(src, list) else src["url"]) == "https://new.example/page"

    rb = data_quality.rollback_apply(res["batch_id"])
    assert rb["restored_changes"] == 1
    src_after = db.get_entity("e1")["source"]
    assert (src_after[0] if isinstance(src_after, list) else src_after) == {"title": "old", "url": "https://old.example/"}


# ── GĐ3.1 (QUYẾT ĐỊNH): UGC/auth Postgres-only; SQLite KHÔNG có bảng users (by design) ──
# Dev/prod parity. SQLite chỉ phục vụ tầng tri thức (entity/rel/itinerary).

@pytest.mark.xfail(reason="QUYẾT ĐỊNH: UGC Postgres-only — SQLite không có users (by design)", strict=False)
def test_create_user_unavailable_on_sqlite_by_design(db):
    db.create_user("0900000000", "Test")
    assert db.get_user_by_phone("0900000000") is not None


# ══════════════════════════════════════════════════════════════
#  BACKEND-INFRA: Expanded coverage for untested methods
# ══════════════════════════════════════════════════════════════


# ── Helper functions (pure, no DB) ──

class TestValidatePlaceLevel:
    def test_xa_prefix_fixes_phuong_level(self):
        e = {"type": "place", "name": "Xã Long Hồ", "level": "phuong", "id": "xa-long-ho"}
        _validate_place_level(e)
        assert e["level"] == "xa"

    def test_phuong_prefix_fixes_xa_level(self):
        e = {"type": "place", "name": "Phường 1", "level": "xa", "id": "p-1"}
        _validate_place_level(e)
        assert e["level"] == "phuong"

    def test_id_prefix_p_fixes_xa_level(self):
        e = {"type": "place", "name": "Đơn vị", "level": "xa", "id": "p-some-ward"}
        _validate_place_level(e)
        assert e["level"] == "phuong"

    def test_id_prefix_xa_fixes_phuong_level(self):
        e = {"type": "place", "name": "Đơn vị", "level": "phuong", "id": "xa-some-commune"}
        _validate_place_level(e)
        assert e["level"] == "xa"

    def test_non_place_type_ignored(self):
        e = {"type": "dish", "name": "Phường Bánh", "level": "xa", "id": "d1"}
        _validate_place_level(e)
        assert e["level"] == "xa"

    def test_no_level_no_crash(self):
        e = {"type": "place", "name": "Xã A", "id": "xa-a"}
        _validate_place_level(e)  # no error


class TestCoordsInRegion:
    def test_valid_coords_inside(self):
        assert _coords_in_region([10.25, 105.97]) is True

    def test_coords_outside_region(self):
        assert _coords_in_region([21.0, 105.8]) is False  # Hà Nội

    def test_invalid_coords_type(self):
        assert _coords_in_region(None) is False
        assert _coords_in_region("abc") is False
        assert _coords_in_region([]) is False

    def test_boundary_values(self):
        assert _coords_in_region([9.2, 105.6]) is True   # min corner
        assert _coords_in_region([10.65, 106.95]) is True  # max corner
        assert _coords_in_region([9.19, 105.6]) is False  # just outside lat_min


class TestCoerceIsoDate:
    def test_already_iso_with_z(self):
        assert _coerce_iso_date("2026-06-11T10:00:00Z") == "2026-06-11T10:00:00Z"

    def test_iso_without_z(self):
        assert _coerce_iso_date("2026-06-11T10:00:00") == "2026-06-11T10:00:00Z"

    def test_sqlite_datetime_format(self):
        result = _coerce_iso_date("2026-06-13 04:00:38")
        assert result == "2026-06-13T04:00:38Z"

    def test_date_only(self):
        result = _coerce_iso_date("2026-06-10")
        assert "2026-06-10" in result
        assert result.endswith("Z")

    def test_none_and_empty(self):
        assert _coerce_iso_date(None) is None
        assert _coerce_iso_date("") is None
        assert _coerce_iso_date("   ") is None

    def test_non_string(self):
        assert _coerce_iso_date(12345) is None


def test_canonical_verified_at_reads_only_attribute() -> None:
    entity = {
        "verifiedAt": "2026-07-27T00:00:00Z",
        "attributes": {"verifiedAt": "2026-06-08T07:00:00+07:00"},
    }

    assert canonical_verified_at(entity) == "2026-06-08T00:00:00Z"


@pytest.mark.parametrize(
    "entity",
    [
        {"verifiedAt": "2026-07-27T00:00:00Z"},
        {"updatedAt": "2026-07-27T00:00:00Z"},
        {"verified": True},
        {"attributes": {"verifiedAt": ""}},
        {"attributes": {"verifiedAt": "not-a-date"}},
        {"attributes": {"verifiedAt": 123}},
        {"attributes": "not-an-object"},
    ],
)
def test_canonical_verified_at_rejects_legacy_or_invalid_values(entity: dict) -> None:
    assert canonical_verified_at(entity) is None


class TestNormalizeEntityTimestamps:
    def test_sets_updated_no_verified_fallback(self):
        # P0-6: updatedAt is an IMPORT timestamp, not a field-verification date.
        # verifiedAt must NOT fall back to it — else every page shows a fake
        # "kiểm chứng thực địa" freshness. (Assertion flipped on purpose.)
        d = {"updatedAt": "2026-06-10", "created_at": "2026-06-09 12:00:00"}
        result = _normalize_entity_timestamps(d)
        assert result["updatedAt"].startswith("2026-06-10")
        assert result["updatedAt"].endswith("Z")
        assert result.get("verifiedAt") is None

    def test_no_verifiedAt_fallback_when_only_updatedAt(self):
        result = _normalize_entity_timestamps({"updatedAt": "2026-06-10"})
        assert result.get("verifiedAt") is None

    def test_fallback_to_created_at(self):
        d = {"created_at": "2026-06-09 12:00:00"}
        result = _normalize_entity_timestamps(d)
        assert result["updatedAt"] == "2026-06-09T12:00:00Z"

    def test_explicit_verified_at_in_attributes(self):
        d = {"updatedAt": "2026-06-10", "attributes": {"verifiedAt": "2026-06-08T00:00:00Z"}}
        result = _normalize_entity_timestamps(d)
        assert result["attributes"]["verifiedAt"] == "2026-06-08T00:00:00Z"
        assert "verifiedAt" not in result

    def test_removes_legacy_top_level_without_mirroring_attribute(self):
        entity = {
            "verifiedAt": "2026-07-27T00:00:00Z",
            "attributes": {"verifiedAt": "2026-06-08T00:00:00Z"},
        }

        result = _normalize_entity_timestamps(entity)

        assert "verifiedAt" not in result
        assert result["attributes"]["verifiedAt"] == "2026-06-08T00:00:00Z"

    def test_non_dict_returns_as_is(self):
        assert _normalize_entity_timestamps("not a dict") == "not a dict"

    def test_created_at_exposed_as_createdAt(self):
        d = {"created_at": "2026-06-09 12:00:00"}
        result = _normalize_entity_timestamps(d)
        assert result["createdAt"] == "2026-06-09T12:00:00Z"


# ── get_entities_batch ──

def test_get_entities_batch_returns_matching(db):
    db.upsert_entity(_entity(eid="b1", name="A"))
    db.upsert_entity(_entity(eid="b2", name="B"))
    db.upsert_entity(_entity(eid="b3", name="C"))
    result = db.get_entities_batch(["b1", "b3"])
    assert set(result.keys()) == {"b1", "b3"}
    assert result["b1"]["name"] == "A"


def test_get_entities_batch_empty_list(db):
    assert db.get_entities_batch([]) == {}


def test_get_entities_batch_deduplicates_ids(db):
    db.upsert_entity(_entity(eid="dup1", name="X"))
    result = db.get_entities_batch(["dup1", "dup1", "dup1"])
    assert len(result) == 1


def test_get_entities_batch_missing_ids_skipped(db):
    db.upsert_entity(_entity(eid="exists"))
    result = db.get_entities_batch(["exists", "ghost"])
    assert "exists" in result
    assert "ghost" not in result


# ── search_entities ──

def test_search_entities_by_query(db):
    db.upsert_entity(_entity(eid="s1", name="Bánh xèo", etype="dish"))
    db.upsert_entity(_entity(eid="s2", name="Hủ tiếu", etype="dish"))
    results = db.search_entities(q="Bánh")
    assert len(results) == 1 and results[0]["id"] == "s1"


def test_search_entities_by_type(db):
    db.upsert_entity(_entity(eid="s3", etype="dish"))
    db.upsert_entity(_entity(eid="s4", etype="attraction"))
    results = db.search_entities(entity_type="attraction")
    ids = {r["id"] for r in results}
    assert "s4" in ids and "s3" not in ids


def test_search_entities_by_area(db):
    db.upsert_entity(_entity(eid="a1", etype="dish", area="vinh-long"))
    db.upsert_entity(_entity(eid="a2", etype="dish", area="ben-tre"))
    results = db.search_entities(area="vinh-long")
    ids = {r["id"] for r in results}
    assert "a1" in ids


def test_search_entities_excludes_place(db):
    db.upsert_entity(_entity(eid="p1", etype="place", name="Xã A"))
    db.upsert_entity(_entity(eid="d1", etype="dish", name="Xã A dish"))
    results = db.search_entities(q="Xã A")
    ids = {r["id"] for r in results}
    assert "p1" not in ids


def test_search_entities_offset(db):
    for i in range(5):
        db.upsert_entity(_entity(eid=f"off{i}", etype="dish", name=f"Item {i}"))
    page1 = db.search_entities(limit=2, offset=0)
    page2 = db.search_entities(limit=2, offset=2)
    assert len(page1) == 2 and len(page2) == 2
    ids1 = {r["id"] for r in page1}
    ids2 = {r["id"] for r in page2}
    assert ids1.isdisjoint(ids2)


def test_search_entities_multiple_types(db):
    db.upsert_entity(_entity(eid="mt1", etype="dish"))
    db.upsert_entity(_entity(eid="mt2", etype="attraction"))
    db.upsert_entity(_entity(eid="mt3", etype="accommodation"))
    results = db.search_entities(entity_types=["dish", "attraction"])
    ids = {r["id"] for r in results}
    assert ids == {"mt1", "mt2"}


# ── update_description ──

def test_update_description(db):
    db.upsert_entity(_entity(eid="desc1"))
    db.update_description("desc1", "Mô tả chi tiết mới")
    got = db.get_entity("desc1")
    assert got["description"] == "Mô tả chi tiết mới"


def test_update_description_does_not_overwrite_name(db):
    db.upsert_entity(_entity(eid="desc2", name="Tên gốc"))
    db.update_description("desc2", "Desc mới")
    got = db.get_entity("desc2")
    assert got["name"] == "Tên gốc"
    assert got["description"] == "Desc mới"


# ── _parse_coordinates ──

class TestParseCoordinates:
    def setup_method(self):
        self.db = Database.__new__(Database)

    def test_list_coords(self):
        assert self.db._parse_coordinates([10.25, 105.97]) == [10.25, 105.97]

    def test_json_string(self):
        assert self.db._parse_coordinates("[10.25, 105.97]") == [10.25, 105.97]

    def test_dict_lat_lng(self):
        assert self.db._parse_coordinates({"lat": 10.25, "lng": 105.97}) == [10.25, 105.97]

    def test_dict_latitude_longitude(self):
        assert self.db._parse_coordinates({"latitude": 10.25, "longitude": 105.97}) == [10.25, 105.97]

    def test_double_encoded_json(self):
        import json
        val = json.dumps([10.25, 105.97])
        double = json.dumps(val)
        assert self.db._parse_coordinates(double) == [10.25, 105.97]

    def test_none_returns_none(self):
        assert self.db._parse_coordinates(None) is None

    def test_empty_string(self):
        assert self.db._parse_coordinates("") is None

    def test_invalid_json(self):
        assert self.db._parse_coordinates("not json") is None

    def test_wrong_length(self):
        assert self.db._parse_coordinates([10.0]) is None
        assert self.db._parse_coordinates([10.0, 20.0, 30.0]) is None

    def test_swapped_lat_lng_corrected(self):
        result = self.db._parse_coordinates([105.97, 10.25])
        assert result == [10.25, 105.97]

    def test_out_of_range(self):
        assert self.db._parse_coordinates([999, 999]) is None


# ── _haversine_km ──

class TestHaversine:
    def setup_method(self):
        self.db = Database.__new__(Database)

    def test_same_point_zero_distance(self):
        assert self.db._haversine_km([10.25, 105.97], [10.25, 105.97]) == 0.0

    def test_known_distance(self):
        # Vĩnh Long to Bến Tre city: roughly 30-40km
        d = self.db._haversine_km([10.25, 105.97], [10.24, 106.37])
        assert 30 < d < 50

    def test_none_inputs(self):
        assert self.db._haversine_km(None, [10.0, 105.0]) is None
        assert self.db._haversine_km([10.0, 105.0], None) is None


# ── get_relationships (pagination, filtering, sorting) ──

def test_get_relationships_basic(db):
    db.upsert_entity(_entity(eid="r1", etype="dish", name="Dish A", area="vinh-long"))
    db.upsert_entity(_entity(eid="r2", etype="attraction", name="Attr B", area="vinh-long"))
    db.add_relationship("r1", "r2", "near")
    rels = db.get_relationships("r1")
    assert len(rels) == 1
    assert rels[0]["other_id"] == "r2"
    assert rels[0]["rel_type"] == "near"


def test_get_relationships_exclude_near(db):
    db.upsert_entity(_entity(eid="rn1", etype="dish"))
    db.upsert_entity(_entity(eid="rn2", etype="attraction"))
    db.upsert_entity(_entity(eid="rn3", etype="dish"))
    db.add_relationship("rn1", "rn2", "near")
    db.add_relationship("rn1", "rn3", "hosts")
    rels = db.get_relationships("rn1", include_near=False)
    types = {r["rel_type"] for r in rels}
    assert "near" not in types
    assert "hosts" in types


def test_get_relationships_filter_by_type(db):
    db.upsert_entity(_entity(eid="ft1", etype="dish"))
    db.upsert_entity(_entity(eid="ft2", etype="attraction"))
    db.upsert_entity(_entity(eid="ft3", etype="dish"))
    db.add_relationship("ft1", "ft2", "near")
    db.add_relationship("ft1", "ft3", "hosts")
    rels = db.get_relationships("ft1", rel_type="hosts")
    assert len(rels) == 1 and rels[0]["rel_type"] == "hosts"


def test_get_relationships_pagination(db):
    db.upsert_entity(_entity(eid="pg0", etype="dish"))
    for i in range(1, 6):
        db.upsert_entity(_entity(eid=f"pg{i}", etype="attraction", name=f"Attr {i}"))
        db.add_relationship("pg0", f"pg{i}", "hosts")
    page1 = db.get_relationships("pg0", limit=2, offset=0)
    page2 = db.get_relationships("pg0", limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    ids1 = {r["other_id"] for r in page1}
    ids2 = {r["other_id"] for r in page2}
    assert ids1.isdisjoint(ids2)


def test_get_relationships_return_total(db):
    db.upsert_entity(_entity(eid="rt0", etype="dish"))
    for i in range(1, 4):
        db.upsert_entity(_entity(eid=f"rt{i}", etype="attraction"))
        db.add_relationship("rt0", f"rt{i}", "near")
    rels, total = db.get_relationships("rt0", limit=2, return_total=True)
    assert total == 3
    assert len(rels) == 2


def test_get_relationships_empty(db):
    db.upsert_entity(_entity(eid="lonely"))
    assert db.get_relationships("lonely") == []


# ── count_relationships ──

def test_count_relationships_basic(db):
    db.upsert_entity(_entity(eid="cr1"))
    db.upsert_entity(_entity(eid="cr2"))
    db.upsert_entity(_entity(eid="cr3"))
    db.add_relationship("cr1", "cr2", "near")
    db.add_relationship("cr1", "cr3", "hosts")
    assert db.count_relationships("cr1") == 2


def test_count_relationships_filter_type(db):
    db.upsert_entity(_entity(eid="crf1"))
    db.upsert_entity(_entity(eid="crf2"))
    db.upsert_entity(_entity(eid="crf3"))
    db.add_relationship("crf1", "crf2", "near")
    db.add_relationship("crf1", "crf3", "hosts")
    assert db.count_relationships("crf1", rel_type="hosts") == 1


def test_count_relationships_exclude_near(db):
    db.upsert_entity(_entity(eid="crn1"))
    db.upsert_entity(_entity(eid="crn2"))
    db.upsert_entity(_entity(eid="crn3"))
    db.add_relationship("crn1", "crn2", "near")
    db.add_relationship("crn1", "crn3", "hosts")
    assert db.count_relationships("crn1", include_near=False) == 1


# ── Feedback ──

def test_save_and_get_feedback_stats(db):
    db.save_feedback("u1", "bánh xèo", 1)
    db.save_feedback("u2", "hủ tiếu", 1)
    db.save_feedback("u3", "xấu", -1)
    stats = db.get_feedback_stats()
    assert stats["total"] == 3
    assert stats["positive"] == 2
    assert stats["negative"] == 1
    assert stats["positive_rate"] == pytest.approx(66.7, abs=0.1)


def test_feedback_stats_empty(db):
    stats = db.get_feedback_stats()
    assert stats["total"] == 0
    assert stats["positive_rate"] == 0.0


# ── Query Log ──

def test_log_query_and_stats(db):
    db.log_query("test query", ["search"], 100, 0.8, "session1")
    db.log_query("another", ["chat"], 200, 0.9, "session1")
    stats = db.get_query_stats(days=7)
    assert stats["total_queries"] == 2
    assert stats["avg_score"] == pytest.approx(0.85, abs=0.01)


def test_query_stats_empty(db):
    stats = db.get_query_stats()
    assert stats["total_queries"] == 0


# ── backup (SQLite) ──

def test_backup_creates_copy(db, tmp_path):
    db.upsert_entity(_entity(eid="bk1"))
    requested_path = tmp_path / "backup_test.db"
    backup_path = db.backup(str(requested_path))
    assert Path(backup_path) == requested_path
    assert os.path.exists(backup_path)
    backup_db = Database(db_path=backup_path)
    backup_db._use_pg = False
    backup_db._dsn = None
    backup_db.initialize()
    assert backup_db.get_entity("bk1") is not None


def test_backup_auto_generates_path_next_to_database(db, tmp_path, monkeypatch):
    import database

    legacy_global = tmp_path / "legacy-global-backup"
    legacy_global.mkdir()
    monkeypatch.setattr(database, "DB_DIR", legacy_global)
    db.upsert_entity(_entity(eid="bk2"))
    try:
        backup_path = Path(db.backup())
        assert backup_path.parent == Path(db.db_path).parent
        assert backup_path.parent != legacy_global
        assert backup_path.name.startswith("vinhlong360_backup_")
        assert backup_path.suffix == ".db"
        assert backup_path.exists()
    finally:
        for directory in (Path(db.db_path).parent, legacy_global):
            for generated in directory.glob("vinhlong360_backup_*.db"):
                generated.unlink()


# ── stats ──

def test_stats_returns_all_fields(db):
    db.upsert_entity(_entity(eid="st1", etype="dish"))
    db.upsert_entity({"id": "st2", "type": "place", "name": "Xã A", "level": "xa"})
    db.add_relationship("st1", "st2", "near")
    db.upsert_itinerary({"id": "it1", "title": "T", "stops": []})
    db.save_feedback("u1", "q", 1)
    db.log_query("q", ["chat"], 100)
    s = db.stats()
    assert s["entities"] == 1  # excludes place
    assert s["places"] == 1    # only level=xa/phuong
    assert s["relationships"] == 1
    assert s["itineraries"] == 1
    assert s["feedback_entries"] == 1
    assert s["query_log_entries"] == 1
    assert s["backend"] == "sqlite"
    assert "db_size_kb" in s


# ── Entity change history ──

def test_log_entity_changes_tracks_diffs(db):
    db.upsert_entity(_entity(eid="ch1", name="Old Name"))
    old = {"name": "Old Name", "summary": "Old"}
    new = {"name": "New Name", "summary": "Old"}
    db.log_entity_changes("ch1", old, new, actor="test")
    history = db.get_entity_history("ch1")
    assert len(history) == 1
    assert history[0]["field"] == "name"
    assert history[0]["old_value"] == "Old Name"
    assert history[0]["new_value"] == "New Name"
    assert history[0]["actor"] == "test"


def test_log_entity_changes_no_diff_no_record(db):
    db.upsert_entity(_entity(eid="ch2"))
    same = {"name": "Bún bò", "summary": "Món ngon"}
    db.log_entity_changes("ch2", same, same)
    assert db.get_entity_history("ch2") == []


def test_entity_history_limit(db):
    db.upsert_entity(_entity(eid="ch3"))
    for i in range(10):
        db.log_entity_changes("ch3", {"name": f"v{i}"}, {"name": f"v{i+1}"})
    history = db.get_entity_history("ch3", limit=3)
    assert len(history) == 3


# ── Source normalization on upsert ──

def test_upsert_normalizes_source_string_url(db):
    db.upsert_entity(_entity(eid="sn1", source="https://example.com/page"))
    got = db.get_entity("sn1")
    assert got["source"] == [{"url": "https://example.com/page"}]


def test_upsert_normalizes_source_string_name(db):
    db.upsert_entity(_entity(eid="sn2", source="Wikipedia"))
    got = db.get_entity("sn2")
    assert got["source"] == [{"name": "Wikipedia"}]


def test_upsert_normalizes_source_dict(db):
    db.upsert_entity(_entity(eid="sn3", source={"title": "Gov", "url": "https://gov.vn"}))
    got = db.get_entity("sn3")
    assert got["source"] == [{"title": "Gov", "url": "https://gov.vn"}]


# ── Attribute alias normalization on upsert ──

def test_upsert_normalizes_attribute_aliases(db):
    db.upsert_entity(_entity(eid="aa1", attributes={
        "open_hours": "7-22",
        "foodyRating": 4.5,
        "priceRange": "50k-100k",
    }))
    got = db.get_entity("aa1")
    attrs = got["attributes"]
    assert attrs.get("hours") == "7-22"
    assert attrs.get("rating") == 4.5
    assert attrs.get("price_range") == "50k-100k"
    assert "open_hours" not in attrs


# ── Coordinate region guard on upsert ──

def test_upsert_nullifies_out_of_region_coords(db):
    db.upsert_entity(_entity(eid="cg1", coordinates=[21.0, 105.8]))  # Hà Nội
    got = db.get_entity("cg1")
    assert got.get("coordinates") is None


def test_upsert_keeps_in_region_coords(db):
    db.upsert_entity(_entity(eid="cg2", coordinates=[10.25, 105.97]))
    got = db.get_entity("cg2")
    assert got["coordinates"] == [10.25, 105.97]


# ── Thread safety: concurrent upserts don't crash ──

def test_concurrent_upserts(db):
    import threading
    errors = []

    def upsert_batch(start):
        try:
            for i in range(20):
                db.upsert_entity(_entity(eid=f"thread-{start}-{i}", name=f"T{start}-{i}"))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=upsert_batch, args=(t,)) for t in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Concurrent upserts raised: {errors}"
    total = len(db.all_entities())
    assert total == 80  # 4 threads × 20 entities


# ── _conn rollback on error ──


class _ManagedConnectionDouble:
    def __init__(
        self,
        *,
        autocommit_error=None,
        row_factory_error=None,
        execute_error=None,
        commit_error=None,
        rollback_error=None,
        close_error=None,
    ):
        self._autocommit = None
        self._row_factory = None
        self.autocommit_error = autocommit_error
        self.row_factory_error = row_factory_error
        self.execute_error = execute_error
        self.commit_error = commit_error
        self.rollback_error = rollback_error
        self.close_error = close_error
        self.execute_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    @property
    def autocommit(self):
        return self._autocommit

    @autocommit.setter
    def autocommit(self, value):
        if self.autocommit_error:
            raise self.autocommit_error
        self._autocommit = value

    @property
    def row_factory(self):
        return self._row_factory

    @row_factory.setter
    def row_factory(self, value):
        if self.row_factory_error:
            raise self.row_factory_error
        self._row_factory = value

    def execute(self, _sql):
        self.execute_calls += 1
        if self.execute_error:
            raise self.execute_error
        return self

    def commit(self):
        self.commit_calls += 1
        if self.commit_error:
            raise self.commit_error

    def rollback(self):
        self.rollback_calls += 1
        if self.rollback_error:
            raise self.rollback_error

    def close(self):
        self.close_calls += 1
        if self.close_error:
            raise self.close_error


class _ConnectionPoolDouble:
    def __init__(self, conn, *, putconn_error=None):
        self.conn = conn
        self.putconn_error = putconn_error
        self.putconn_calls = []

    def getconn(self):
        return self.conn

    def putconn(self, conn, *, close):
        self.putconn_calls.append((conn, close))
        if self.putconn_error:
            raise self.putconn_error


def _pg_connection_manager(monkeypatch, conn, pool=None):
    database = Database.__new__(Database)
    database._use_pg = True
    database._dsn = "postgresql://example.invalid/test"
    monkeypatch.setattr(database, "_get_pg_pool", lambda: pool)
    monkeypatch.setattr(
        sys.modules[Database.__module__],
        "psycopg2",
        SimpleNamespace(connect=lambda *args, **kwargs: conn),
        raising=False,
    )
    return database


def _sqlite_connection_manager(monkeypatch, conn):
    monkeypatch.setattr(sqlite3, "connect", lambda *args, **kwargs: conn)
    database = Database.__new__(Database)
    database._use_pg = False
    database.db_path = "unused.db"
    return database


def test_conn_commit_option_is_keyword_only():
    parameter = inspect.signature(Database._conn).parameters["commit_on_success"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.annotation is bool
    assert parameter.default is True


@pytest.mark.parametrize(
    ("commit_on_success", "commit_calls", "rollback_calls"),
    [(True, 1, 0), (False, 0, 1)],
)
def test_pg_conn_success_finalizes_and_returns_reusable_pool_connection(
    monkeypatch, commit_on_success, commit_calls, rollback_calls
):
    conn = _ManagedConnectionDouble()
    pool = _ConnectionPoolDouble(conn)
    database = _pg_connection_manager(monkeypatch, conn, pool)

    with database._conn(commit_on_success=commit_on_success) as yielded:
        assert yielded is conn

    assert conn.autocommit is False
    assert conn.commit_calls == commit_calls
    assert conn.rollback_calls == rollback_calls
    assert pool.putconn_calls == [(conn, False)]


@pytest.mark.parametrize(
    ("commit_on_success", "commit_calls", "rollback_calls"),
    [(True, 1, 0), (False, 0, 1)],
)
def test_sqlite_conn_success_uses_requested_finalization(
    monkeypatch, commit_on_success, commit_calls, rollback_calls
):
    conn = _ManagedConnectionDouble()
    database = _sqlite_connection_manager(monkeypatch, conn)

    with database._conn(commit_on_success=commit_on_success) as yielded:
        assert yielded is conn

    assert conn.commit_calls == commit_calls
    assert conn.rollback_calls == rollback_calls
    assert conn.close_calls == 1


def test_pg_conn_base_exception_rolls_back_and_discards_pool_connection(monkeypatch):
    conn = _ManagedConnectionDouble()
    pool = _ConnectionPoolDouble(conn)
    database = _pg_connection_manager(monkeypatch, conn, pool)

    with pytest.raises(KeyboardInterrupt):
        with database._conn():
            raise KeyboardInterrupt

    assert conn.rollback_calls == 1
    assert pool.putconn_calls == [(conn, True)]


def test_pg_conn_finalization_failure_discards_pool_connection(monkeypatch):
    conn = _ManagedConnectionDouble(rollback_error=RuntimeError("rollback failed"))
    pool = _ConnectionPoolDouble(conn)
    database = _pg_connection_manager(monkeypatch, conn, pool)

    with pytest.raises(RuntimeError, match="rollback failed"):
        with database._conn(commit_on_success=False):
            pass

    assert conn.commit_calls == 0
    assert conn.rollback_calls >= 1
    assert pool.putconn_calls == [(conn, True)]


@pytest.mark.parametrize(
    "cleanup_error",
    [KeyboardInterrupt(), SystemExit("putconn failed")],
    ids=["keyboard-interrupt", "system-exit"],
)
def test_pg_conn_putconn_base_exception_closes_connection_and_propagates(
    monkeypatch, cleanup_error
):
    conn = _ManagedConnectionDouble()
    pool = _ConnectionPoolDouble(conn, putconn_error=cleanup_error)
    database = _pg_connection_manager(monkeypatch, conn, pool)

    with pytest.raises(type(cleanup_error)):
        with database._conn():
            pass

    assert pool.putconn_calls == [(conn, False)]
    assert conn.close_calls == 1


def test_pg_conn_committed_write_suppresses_ordinary_pool_return_failure(monkeypatch):
    conn = _ManagedConnectionDouble()
    pool = _ConnectionPoolDouble(
        conn,
        putconn_error=RuntimeError("pool return failed"),
    )
    database = _pg_connection_manager(monkeypatch, conn, pool)

    with database._conn():
        pass

    assert conn.commit_calls == 1
    assert conn.rollback_calls == 0
    assert pool.putconn_calls == [(conn, False)]
    assert conn.close_calls == 1


def test_pg_conn_read_rollback_propagates_ordinary_pool_return_failure(monkeypatch):
    conn = _ManagedConnectionDouble()
    pool = _ConnectionPoolDouble(
        conn,
        putconn_error=RuntimeError("pool return failed"),
    )
    database = _pg_connection_manager(monkeypatch, conn, pool)

    with pytest.raises(RuntimeError, match="pool return failed"):
        with database._conn(commit_on_success=False):
            pass

    assert conn.commit_calls == 0
    assert conn.rollback_calls == 1
    assert pool.putconn_calls == [(conn, False)]
    assert conn.close_calls == 1


@pytest.mark.parametrize("pooled", [True, False], ids=["pooled", "unpooled"])
def test_pg_conn_autocommit_setup_failure_discards_or_closes(
    monkeypatch, pooled
):
    error = RuntimeError("autocommit setup failed")
    conn = _ManagedConnectionDouble(
        autocommit_error=error,
        close_error=None if pooled else SystemExit("close failed"),
    )
    pool = _ConnectionPoolDouble(conn) if pooled else None
    database = _pg_connection_manager(monkeypatch, conn, pool)

    with pytest.raises(RuntimeError, match="autocommit setup failed"):
        with database._conn():
            pass

    if pooled:
        assert pool.putconn_calls == [(conn, True)]
    else:
        assert conn.close_calls == 1


@pytest.mark.parametrize(
    ("failure_kwargs", "message"),
    [
        ({"row_factory_error": RuntimeError("row factory failed")}, "row factory failed"),
        ({"execute_error": RuntimeError("pragma failed")}, "pragma failed"),
    ],
    ids=["row-factory", "pragma"],
)
def test_sqlite_conn_setup_failure_closes_and_preserves_error(
    monkeypatch, failure_kwargs, message
):
    conn = _ManagedConnectionDouble(
        **failure_kwargs,
        close_error=SystemExit("close failed"),
    )
    database = _sqlite_connection_manager(monkeypatch, conn)

    with pytest.raises(RuntimeError, match=message):
        with database._conn():
            pass

    assert conn.close_calls == 1


@pytest.mark.parametrize("backend", ["postgres", "sqlite"])
def test_unpooled_close_failure_does_not_replace_body_error(monkeypatch, backend):
    conn = _ManagedConnectionDouble(close_error=SystemExit("close failed"))
    database = (
        _pg_connection_manager(monkeypatch, conn)
        if backend == "postgres"
        else _sqlite_connection_manager(monkeypatch, conn)
    )

    with pytest.raises(ValueError, match="body failed"):
        with database._conn():
            raise ValueError("body failed")

    assert conn.rollback_calls == 1
    assert conn.close_calls == 1


@pytest.mark.parametrize("backend", ["postgres", "sqlite"])
def test_unpooled_close_failure_does_not_replace_finalization_error(
    monkeypatch, backend
):
    conn = _ManagedConnectionDouble(
        commit_error=RuntimeError("commit failed"),
        close_error=SystemExit("close failed"),
    )
    database = (
        _pg_connection_manager(monkeypatch, conn)
        if backend == "postgres"
        else _sqlite_connection_manager(monkeypatch, conn)
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        with database._conn():
            pass

    assert conn.commit_calls == 1
    assert conn.rollback_calls == 1
    assert conn.close_calls == 1


@pytest.mark.parametrize("backend", ["postgres", "sqlite"])
def test_unpooled_close_base_exception_propagates_after_success(monkeypatch, backend):
    conn = _ManagedConnectionDouble(close_error=SystemExit("close failed"))
    database = (
        _pg_connection_manager(monkeypatch, conn)
        if backend == "postgres"
        else _sqlite_connection_manager(monkeypatch, conn)
    )

    with pytest.raises(SystemExit, match="close failed"):
        with database._conn():
            pass

    assert conn.commit_calls == 1
    assert conn.close_calls == 1


def test_conn_rollback_on_error(db):
    db.upsert_entity(_entity(eid="rb1", name="Before"))
    try:
        with db._conn() as conn:
            conn.execute("UPDATE entities SET name='During' WHERE id='rb1'")
            raise ValueError("simulate crash")
    except ValueError:
        pass
    assert db.get_entity("rb1")["name"] == "Before"


# ── export_all (public API for export_data.py) ──

def test_export_all_returns_all_data(db):
    db.upsert_entity({"id": "ex1", "type": "place", "name": "Place A", "level": "xa"})
    db.upsert_entity({"id": "ex2", "type": "restaurant", "name": "Quán B"})
    db.add_relationship("ex2", "ex1", "located_in")
    result = db.export_all()
    assert "entities" in result
    assert "relationships" in result
    assert "itineraries" in result
    ids = {e["id"] for e in result["entities"]}
    assert "ex1" in ids
    assert "ex2" in ids
    assert len(result["relationships"]) >= 1
    rel = result["relationships"][0]
    assert "from" in rel and "to" in rel and "type" in rel


def test_pg_required_columns_only_names_columns_that_really_exist():
    """Hợp đồng cột KHÔNG được nêu cột không tồn tại trong schema.

    Bài này sinh ra từ một lỗi thật: khi hợp hai nhánh, khối `PG_REQUIRED_COLUMNS`
    xung đột giữa `feedback_daily_rollups` (phía main) và `user_preferences` (phía
    NP-1); người gộp thêm một dòng `"created_at",` để nối hai phía rồi đóng ngoặc —
    nhưng bảng đó không có cột ấy. Hậu quả: MỌI tiến trình nối Postgres tự từ chối
    khởi động với `schema is not ready ... missing columns`, còn SQLite thì im lặng
    vì `_verify_pg_schema` chỉ chạy khi `_use_pg`. Không test nào bắt được, chỉ CI
    trên Postgres thật mới lộ.

    Cách kiểm: gom mọi tên cột xuất hiện trong `init.sql` + `agent/migrations/*.sql`
    (CREATE TABLE và ALTER TABLE ... ADD COLUMN) rồi đòi hợp đồng là tập con. Cố ý
    đối chiếu theo TỪNG BẢNG chứ không gộp chung, để không bỏ lọt cột đúng tên nhưng
    sai bảng.
    """
    import re

    root = Path(__file__).resolve().parents[2]
    declared: dict[str, set[str]] = {}
    for path in [root / "init.sql", *sorted((root / "agent" / "migrations").glob("*.sql"))]:
        sql = path.read_text(encoding="utf-8")
        for block in re.finditer(
            r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)\s*\((.*?)\n\)\s*;", sql, re.S | re.I
        ):
            cols = declared.setdefault(block.group(1).lower(), set())
            for line in block.group(2).splitlines():
                name = re.match(r"\s*(\w+)\s+\w", line)
                if name and name.group(1).upper() not in {
                    "CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "EXCLUDE",
                }:
                    cols.add(name.group(1).lower())
        # ALTER TABLE có thể trải NHIỀU DÒNG và mang NHIỀU mệnh đề ADD COLUMN
        # (ví dụ agent/migrations/078:4-6). Bắt cả câu lệnh tới dấu `;` rồi mới quét
        # từng mệnh đề — regex một-dòng sẽ báo nhầm là cột không tồn tại.
        for stmt in re.finditer(
            r"ALTER TABLE(?:\s+IF EXISTS)?\s+(\w+)(.*?);", sql, re.S | re.I
        ):
            table_cols = declared.setdefault(stmt.group(1).lower(), set())
            for add in re.finditer(
                r"ADD COLUMN(?:\s+IF NOT EXISTS)?\s+(\w+)", stmt.group(2), re.I
            ):
                table_cols.add(add.group(1).lower())

    # Chốt để bài test không tự rỗng nếu regex hỏng.
    assert len(declared) > 30, f"đọc được quá ít bảng ({len(declared)}) — logic quét hỏng?"

    invented: list[str] = []
    for table, columns in database_module.PG_REQUIRED_COLUMNS.items():
        known = declared.get(table.lower())
        if not known:
            continue  # bảng do nguồn khác tạo — bài khác lo, không đoán ở đây
        for column in columns:
            if column.lower() not in known:
                invented.append(f"{table}.{column}")

    assert not invented, (
        "PG_REQUIRED_COLUMNS nêu cột KHÔNG có trong init.sql/migrations — "
        "Postgres sẽ từ chối khởi động: " + ", ".join(sorted(invented))
    )
