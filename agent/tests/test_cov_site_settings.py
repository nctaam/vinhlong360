"""
Unit tests for agent/site_settings.py.

Two testing strategies:

1. Pure-logic functions (`is_public_key`, `_json_value`, cache invalidation) are
   tested directly with real inputs / real side-effects.

2. Functions that touch Postgres are exercised by swapping `db` into a
   PG-mode stub with an in-memory fake connection. We mock ONLY the I/O boundary
   (the fake cursor / fetch primitives) and assert the module's own LOGIC:
   which rows get updated, history rows recorded, cache invalidation, size
   guards, public-key filtering, category filtering, LIMIT clamping, etc.

The local environment has no real Postgres, so `db._use_pg` is False; the
no-PG early-return branches are tested against the real `db` directly.
"""

import json
from contextlib import contextmanager

import pytest

import site_settings as ss
from database import db


# --------------------------------------------------------------------------- #
# Fake Postgres layer                                                          #
# --------------------------------------------------------------------------- #

class FakeCursor:
    """Records rowcount for UPDATE/INSERT statements."""

    def __init__(self, rowcount=0):
        self.rowcount = rowcount


class FakeConn:
    """Minimal connection object; the real work happens in FakeDB methods."""


class FakeDB:
    """
    In-memory stand-in for `database.db`, PG-mode.

    Holds a `settings` table {key: {value, category, ...}} and a `history` list.
    Implements exactly the primitives site_settings.py calls.
    """

    def __init__(self, settings=None, history=None, fail_conn=False):
        self._use_pg = True
        self.settings = settings or {}
        self.history = history if history is not None else []
        self.fail_conn = fail_conn
        self.executed = []  # (sql, params) log for assertions

    @property
    def _ph(self):
        return "%s"

    @contextmanager
    def _conn(self):
        if self.fail_conn:
            raise RuntimeError("boom: connection failed")
        yield FakeConn()

    def _row_to_dict(self, row):
        if row is None:
            return None
        return dict(row)

    # -- SQL routing -------------------------------------------------------- #
    def _execute(self, conn, sql, params=None):
        params = params or ()
        self.executed.append((sql, params))
        s = " ".join(sql.split())  # normalize whitespace
        if s.startswith("CREATE TABLE") or s.startswith("CREATE INDEX"):
            return FakeCursor(0)
        if s.startswith("UPDATE site_settings SET value"):
            val_json, key = params
            if key in self.settings:
                self.settings[key]["value"] = json.loads(val_json)
                return FakeCursor(1)
            return FakeCursor(0)
        if s.startswith("INSERT INTO site_settings_history"):
            # id, setting_key, category, previous, next, action, actor
            self.history.append({
                "id": params[0],
                "setting_key": params[1],
                "category": params[2],
                "previous_value": params[3],
                "next_value": params[4],
                "action": params[5],
                "actor": params[6],
            })
            return FakeCursor(1)
        if s.startswith("INSERT INTO site_settings"):
            key, val_json = params[0], params[1]
            if key in self.settings:
                return FakeCursor(0)  # ON CONFLICT DO NOTHING
            self.settings[key] = {
                "key": key, "value": json.loads(val_json), "category": params[2],
                "label": params[3], "description": params[4], "input_type": params[5],
            }
            return FakeCursor(1)
        return FakeCursor(0)

    def _fetchone(self, conn, sql, params=None):
        params = params or ()
        s = " ".join(sql.split())
        if "FROM site_settings_history WHERE id" in s:
            hid = params[0]
            for h in self.history:
                if h["id"] == hid:
                    return dict(h)
            return None
        if "FROM site_settings WHERE key" in s:
            key = params[0]
            row = self.settings.get(key)
            return dict(row) if row else None
        if "COUNT(*)" in s:
            return {"c": len(self._filtered_history(sql, params))}
        return None

    def _fetchall(self, conn, sql, params=None):
        params = params or ()
        s = " ".join(sql.split())
        if "FROM site_settings_history" in s:
            return [dict(h) for h in self._filtered_history(sql, params)]
        if "SELECT key, value FROM site_settings" in s:
            return [{"key": k, "value": v["value"]} for k, v in self.settings.items()]
        if "FROM site_settings WHERE category" in s:
            cat = params[0]
            return [dict(v) for v in self.settings.values() if v.get("category") == cat]
        if "FROM site_settings ORDER BY category" in s:
            return [dict(v) for v in self.settings.values()]
        return []

    def _filtered_history(self, sql, params):
        s = " ".join(sql.split())
        rows = list(self.history)
        # params order for load_history: [category?, key?, limit?]  (COUNT omits limit)
        p = list(params)
        if "category = %s" in s:
            cat = p.pop(0)
            rows = [h for h in rows if h.get("category") == cat]
        if "setting_key = %s" in s:
            k = p.pop(0)
            rows = [h for h in rows if h.get("setting_key") == k]
        return rows


@pytest.fixture
def fake_pg(monkeypatch):
    """Install a fresh FakeDB with a couple of seeded settings."""
    fdb = FakeDB(settings={
        "branding.site_name": {"key": "branding.site_name", "value": "old",
                               "category": "branding", "label": "Name",
                               "description": "", "input_type": "text",
                               "updated_at": "2026-01-01T00:00:00+00:00"},
        "seo.title": {"key": "seo.title", "value": "T",
                      "category": "seo", "label": "", "description": "",
                      "input_type": "text", "updated_at": None},
    })
    monkeypatch.setattr(ss, "db", fdb)
    # cache must start clean and be observable
    ss._invalidate()
    return fdb


@pytest.fixture(autouse=True)
def _reset_cache():
    """Every test starts and ends with a clean module cache."""
    ss._invalidate()
    yield
    ss._invalidate()


# --------------------------------------------------------------------------- #
# is_public_key — pure logic                                                  #
# --------------------------------------------------------------------------- #

class TestIsPublicKey:
    def test_plain_key_is_public(self):
        assert ss.is_public_key("branding.site_name") is True

    def test_llm_prefix_hidden(self):
        assert ss.is_public_key("llm.model") is False
        # only a *prefix* match — "foollm." style must still be blocked only by prefix
        assert ss.is_public_key("allm.model") is True

    @pytest.mark.parametrize("marker", ["api_key", "secret", "token", "password"])
    def test_sensitive_markers_hidden(self, marker):
        assert ss.is_public_key(f"contact.{marker}_field") is False

    def test_marker_is_case_insensitive(self):
        assert ss.is_public_key("Contact.API_KEY") is False
        assert ss.is_public_key("LLM.model") is False

    def test_marker_as_substring_anywhere(self):
        # "token" embedded mid-word is still treated as sensitive
        assert ss.is_public_key("csrf_tokenizer") is False

    def test_non_string_coerced(self):
        # str() coercion path: an int key must not raise
        assert ss.is_public_key(123) is True


# --------------------------------------------------------------------------- #
# _json_value — size guard                                                     #
# --------------------------------------------------------------------------- #

class TestJsonValue:
    def test_roundtrips_small_value(self):
        out = ss._json_value({"a": 1, "b": "xin chào"})
        # non-ascii preserved (ensure_ascii=False)
        assert "xin chào" in out
        assert json.loads(out) == {"a": 1, "b": "xin chào"}

    def test_rejects_oversized_value(self):
        big = "x" * (ss._MAX_VALUE_SIZE + 10)
        with pytest.raises(ValueError) as ei:
            ss._json_value(big)
        assert "too large" in str(ei.value)

    def test_accepts_value_at_boundary(self):
        # a value whose JSON is exactly the max size must NOT raise
        # json.dumps("...") adds 2 quote chars
        s = "y" * (ss._MAX_VALUE_SIZE - 2)
        out = ss._json_value(s)
        assert len(out) == ss._MAX_VALUE_SIZE


# --------------------------------------------------------------------------- #
# cache invalidation & TTL — real module state                                #
# --------------------------------------------------------------------------- #

class TestCacheInvalidate:
    def test_invalidate_clears_state(self):
        ss._cache = {"x": 1}
        ss._cache_ts = 999999999.0
        ss._invalidate()
        assert ss._cache is None
        assert ss._cache_ts == 0

    def test_get_all_public_serves_from_cache(self, monkeypatch):
        # Prime the cache, then make db raise if touched — cache must short-circuit.
        ss._cache = {"cached.key": "v"}
        ss._cache_ts = ss.time.time()

        class Explode:
            _use_pg = True

            def _conn(self):  # pragma: no cover - must never be called
                raise AssertionError("db must not be touched when cache is warm")

        monkeypatch.setattr(ss, "db", Explode())
        assert ss.get_all_public() == {"cached.key": "v"}


# --------------------------------------------------------------------------- #
# No-PG early returns — against the REAL db (SQLite mode locally)              #
# --------------------------------------------------------------------------- #

class TestNoPgEarlyReturns:
    def test_real_db_is_sqlite(self):
        # sanity: local env genuinely has no PG, so these branches are live
        assert db._use_pg is False

    def test_get_all_public_empty(self):
        assert ss.get_all_public() == {}

    def test_get_by_category_empty(self):
        assert ss.get_by_category("branding") == []

    def test_get_all_grouped_empty(self):
        assert ss.get_all_grouped() == {}

    def test_upsert_false(self):
        assert ss.upsert("branding.site_name", "x") is False

    def test_bulk_upsert_zero(self):
        assert ss.bulk_upsert({"a": 1}) == 0

    def test_reset_category_zero(self):
        defaults = {"a": {"category": "branding", "value": 1}}
        assert ss.reset_category("branding", defaults) == 0

    def test_load_history_empty(self):
        assert ss.load_history() == {"total": 0, "history": []}

    def test_rollback_false(self):
        assert ss.rollback_history("nope") is False

    def test_seed_defaults_zero(self):
        assert ss.seed_defaults({"a": {"value": 1, "category": "c"}}) == 0

    def test_ensure_table_false(self):
        assert ss._ensure_table() is False

    def test_ensure_history_table_false(self):
        assert ss._ensure_history_table() is False


# --------------------------------------------------------------------------- #
# get_all_public — PG path                                                     #
# --------------------------------------------------------------------------- #

class TestEnsureTablesPg:
    def test_ensure_table_true_on_success(self, fake_pg):
        assert ss._ensure_table() is True

    def test_ensure_history_table_true_on_success(self, fake_pg):
        assert ss._ensure_history_table() is True

    def test_ensure_table_swallows_error_returns_false(self, monkeypatch):
        # PG mode but CREATE TABLE raises -> except branch returns False
        monkeypatch.setattr(ss, "db", FakeDB(fail_conn=True))
        assert ss._ensure_table() is False

    def test_ensure_history_table_swallows_error_returns_false(self, monkeypatch):
        monkeypatch.setattr(ss, "db", FakeDB(fail_conn=True))
        assert ss._ensure_history_table() is False


class TestGetAllPublicPg:
    def test_returns_and_caches(self, fake_pg):
        out = ss.get_all_public()
        assert out == {"branding.site_name": "old", "seo.title": "T"}
        # cache is now warm
        assert ss._cache == out

    def test_filters_sensitive_keys(self, fake_pg):
        fake_pg.settings["llm.model"] = {"value": "gpt", "category": "llm"}
        fake_pg.settings["contact.api_key"] = {"value": "sk-xxx", "category": "contact"}
        out = ss.get_all_public()
        assert "llm.model" not in out
        assert "contact.api_key" not in out
        assert "branding.site_name" in out

    def test_string_value_is_json_parsed(self, fake_pg):
        # value stored as a JSON string should be decoded into a dict
        fake_pg.settings["homepage.hero"] = {"value": '{"title": "Vĩnh Long"}',
                                             "category": "homepage"}
        out = ss.get_all_public()
        assert out["homepage.hero"] == {"title": "Vĩnh Long"}

    def test_non_json_string_left_as_is(self, fake_pg):
        fake_pg.settings["homepage.slug"] = {
            "value": "not-json", "category": "homepage"}
        out = ss.get_all_public()
        assert out["homepage.slug"] == "not-json"

    def test_db_error_returns_empty(self, monkeypatch):
        monkeypatch.setattr(ss, "db", FakeDB(fail_conn=True))
        assert ss.get_all_public() == {}


# --------------------------------------------------------------------------- #
# get_by_category / get_all_grouped — PG path                                 #
# --------------------------------------------------------------------------- #

class TestGetByCategoryPg:
    def test_returns_only_matching_category(self, fake_pg):
        rows = ss.get_by_category("branding")
        keys = {r["key"] for r in rows}
        assert keys == {"branding.site_name"}

    def test_updated_at_stringified(self, fake_pg):
        # Seed updated_at = datetime THẬT (không phải str sẵn) → kiểm module thực
        # sự str()-hoá. Nếu bỏ dòng `str(r["updated_at"])` trong get_by_category,
        # value còn là datetime → cả 2 assert đỏ (trước là tautology vì seed str).
        import datetime as _dt
        dt = _dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=_dt.timezone.utc)
        fake_pg.settings["branding.site_name"]["updated_at"] = dt
        rows = ss.get_by_category("branding")
        row = next(r for r in rows if r["key"] == "branding.site_name")
        assert isinstance(row["updated_at"], str)
        assert row["updated_at"] == str(dt)

    def test_json_string_value_parsed(self, fake_pg):
        fake_pg.settings["branding.logo"] = {
            "key": "branding.logo", "value": '["a","b"]', "category": "branding",
            "label": "", "description": "", "input_type": "text", "updated_at": None,
        }
        rows = ss.get_by_category("branding")
        logo = next(r for r in rows if r["key"] == "branding.logo")
        assert logo["value"] == ["a", "b"]


class TestGetAllGroupedPg:
    def test_groups_by_category(self, fake_pg):
        grouped = ss.get_all_grouped()
        assert set(grouped) == {"branding", "seo"}
        assert grouped["branding"][0]["key"] == "branding.site_name"

    def test_null_updated_at_not_stringified(self, fake_pg):
        grouped = ss.get_all_grouped()
        # seo.title has updated_at=None -> stays falsy, not "None"
        assert grouped["seo"][0]["updated_at"] is None


# --------------------------------------------------------------------------- #
# upsert — PG path                                                            #
# --------------------------------------------------------------------------- #

class TestUpsertPg:
    def test_updates_existing_and_records_history(self, fake_pg):
        assert ss.upsert("branding.site_name", "new", actor="admin") is True
        assert fake_pg.settings["branding.site_name"]["value"] == "new"
        # exactly one history row, action=update, previous captured
        assert len(fake_pg.history) == 1
        h = fake_pg.history[0]
        assert h["action"] == "update"
        assert h["setting_key"] == "branding.site_name"
        assert h["actor"] == "admin"
        assert json.loads(h["previous_value"]) == "old"
        assert json.loads(h["next_value"]) == "new"

    def test_missing_key_returns_false_no_history(self, fake_pg):
        assert ss.upsert("does.not.exist", "v") is False
        assert fake_pg.history == []

    def test_custom_action_flows_to_history(self, fake_pg):
        ss.upsert("seo.title", "New Title", action="import")
        assert fake_pg.history[-1]["action"] == "import"

    def test_oversized_value_raises_before_write(self, fake_pg):
        big = "z" * (ss._MAX_VALUE_SIZE + 5)
        with pytest.raises(ValueError):
            ss.upsert("branding.site_name", big)
        # value unchanged
        assert fake_pg.settings["branding.site_name"]["value"] == "old"

    def test_category_falls_back_to_key_prefix(self, fake_pg, monkeypatch):
        # simulate a settings row whose category is empty -> key.split(".")[0]
        fake_pg.settings["nav.top"] = {"key": "nav.top", "value": 1, "category": ""}
        ss.upsert("nav.top", 2)
        assert fake_pg.history[-1]["category"] == "nav"

    def test_invalidates_cache(self, fake_pg):
        # warm cache first
        ss.get_all_public()
        assert ss._cache is not None
        ss.upsert("branding.site_name", "changed")
        assert ss._cache is None

    def test_update_reporting_zero_rows_returns_false(self, fake_pg, monkeypatch):
        # SELECT finds the row, but UPDATE reports rowcount 0 (TOCTOU race):
        # upsert must return False and NOT record history.
        real_execute = fake_pg._execute

        def zero_update(conn, sql, params=None):
            if " ".join(sql.split()).startswith("UPDATE site_settings SET value"):
                return FakeCursor(0)
            return real_execute(conn, sql, params)

        monkeypatch.setattr(fake_pg, "_execute", zero_update)
        before = len(fake_pg.history)
        assert ss.upsert("branding.site_name", "x") is False
        assert len(fake_pg.history) == before  # no history recorded


# --------------------------------------------------------------------------- #
# bulk_upsert — PG path                                                       #
# --------------------------------------------------------------------------- #

class TestBulkUpsertPg:
    def test_counts_only_existing_keys(self, fake_pg):
        n = ss.bulk_upsert({
            "branding.site_name": "A",
            "seo.title": "B",
            "ghost.key": "C",  # not present -> skipped
        })
        assert n == 2
        assert fake_pg.settings["branding.site_name"]["value"] == "A"
        assert fake_pg.settings["seo.title"]["value"] == "B"
        assert len(fake_pg.history) == 2
        assert all(h["action"] == "bulk_update" for h in fake_pg.history)

    def test_empty_updates_returns_zero(self, fake_pg):
        assert ss.bulk_upsert({}) == 0
        assert fake_pg.history == []

    def test_oversized_value_aborts_that_batch(self, fake_pg):
        with pytest.raises(ValueError):
            ss.bulk_upsert({"branding.site_name": "z" * (ss._MAX_VALUE_SIZE + 1)})


# --------------------------------------------------------------------------- #
# reset_category — PG path                                                    #
# --------------------------------------------------------------------------- #

class TestResetCategoryPg:
    def test_resets_only_matching_category(self, fake_pg):
        defaults = {
            "branding.site_name": {"category": "branding", "value": "DEFAULT"},
            # different category -> must be skipped
            "seo.title": {"category": "seo", "value": "SEO-DEFAULT"},
        }
        n = ss.reset_category("branding", defaults)
        assert n == 1
        assert fake_pg.settings["branding.site_name"]["value"] == "DEFAULT"
        # seo untouched
        assert fake_pg.settings["seo.title"]["value"] == "T"
        assert fake_pg.history[-1]["action"] == "reset"

    def test_skips_default_key_absent_in_table(self, fake_pg):
        defaults = {
            "branding.missing": {"category": "branding", "value": 1},
        }
        assert ss.reset_category("branding", defaults) == 0
        assert fake_pg.history == []


# --------------------------------------------------------------------------- #
# load_history — PG path                                                      #
# --------------------------------------------------------------------------- #

class TestLoadHistoryPg:
    def _seed_history(self, fdb):
        fdb.history = [
            {"id": "h1", "setting_key": "branding.site_name",
             "category": "branding", "previous_value": "a", "next_value": "b",
             "action": "update", "actor": None, "created_at": "2026-01-01"},
            {"id": "h2", "setting_key": "seo.title", "category": "seo",
             "previous_value": "x", "next_value": "y", "action": "update",
             "actor": None, "created_at": "2026-01-02"},
        ]

    def test_no_filter_returns_all(self, fake_pg):
        self._seed_history(fake_pg)
        out = ss.load_history()
        assert out["total"] == 2
        assert len(out["history"]) == 2
        # created_at stringified
        assert isinstance(out["history"][0]["created_at"], str)

    def test_filter_by_category(self, fake_pg):
        self._seed_history(fake_pg)
        out = ss.load_history(category="seo")
        assert out["total"] == 1
        assert out["history"][0]["setting_key"] == "seo.title"

    def test_filter_by_key(self, fake_pg):
        self._seed_history(fake_pg)
        out = ss.load_history(key="branding.site_name")
        assert out["total"] == 1
        assert out["history"][0]["category"] == "branding"

    def test_limit_is_clamped_between_1_and_200(self, fake_pg, monkeypatch):
        # capture the LIMIT param the module builds
        captured = {}
        real_fetchall = fake_pg._fetchall

        def spy(conn, sql, params=None):
            if "FROM site_settings_history" in " ".join(sql.split()):
                captured["limit"] = params[-1]
            return real_fetchall(conn, sql, params)

        monkeypatch.setattr(fake_pg, "_fetchall", spy)

        ss.load_history(limit=99999)
        assert captured["limit"] == 200
        ss.load_history(limit=0)      # falsy -> defaults to 50
        assert captured["limit"] == 50
        ss.load_history(limit=-5)     # clamped up to 1
        assert captured["limit"] == 1


# --------------------------------------------------------------------------- #
# rollback_history — PG path                                                  #
# --------------------------------------------------------------------------- #

class TestRollbackHistoryPg:
    def test_restores_previous_value(self, fake_pg):
        fake_pg.history = [{
            "id": "hist-1", "setting_key": "branding.site_name", "category": "branding",
            "previous_value": "restore-me",
        }]
        assert ss.rollback_history("hist-1", actor="admin") is True
        assert fake_pg.settings["branding.site_name"]["value"] == "restore-me"
        # a new rollback history row is recorded
        assert fake_pg.history[-1]["action"] == "rollback"
        assert fake_pg.history[-1]["actor"] == "admin"

    def test_unknown_history_id_returns_false(self, fake_pg):
        assert ss.rollback_history("nope") is False

    def test_history_present_but_setting_deleted(self, fake_pg):
        fake_pg.history = [{
            "id": "hist-2", "setting_key": "deleted.key", "category": "x",
            "previous_value": "v",
        }]
        # setting row doesn't exist -> current is None -> False
        assert ss.rollback_history("hist-2") is False


# --------------------------------------------------------------------------- #
# seed_defaults — PG path                                                     #
# --------------------------------------------------------------------------- #

class TestSeedDefaultsPg:
    def test_inserts_new_keys_only(self, fake_pg):
        defaults = {
            # already exists -> ON CONFLICT DO NOTHING
            "branding.site_name": {"value": "X", "category": "branding"},
            "footer.copyright": {"value": "© 2026", "category": "footer",
                                 "label": "Copyright", "description": "d",
                                 "input_type": "text"},
        }
        n = ss.seed_defaults(defaults)
        assert n == 1
        assert "footer.copyright" in fake_pg.settings
        # existing key kept its old value (ON CONFLICT DO NOTHING)
        assert fake_pg.settings["branding.site_name"]["value"] == "old"

    def test_meta_defaults_applied(self, fake_pg):
        defaults = {"nav.brand": {"value": "V", "category": "nav"}}
        ss.seed_defaults(defaults)
        row = fake_pg.settings["nav.brand"]
        assert row["label"] == "" and row["input_type"] == "text"

    def test_invalidates_cache(self, fake_pg):
        ss.get_all_public()
        assert ss._cache is not None
        ss.seed_defaults({"x.y": {"value": 1, "category": "x"}})
        assert ss._cache is None
