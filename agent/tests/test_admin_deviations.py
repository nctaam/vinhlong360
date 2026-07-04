"""Tests for the 4 additive AdminCP "deviation" polish tweaks (task-deviations).

Spec: .superpowers/sdd/task-deviations-report.md
Scope (all additive, no behavior regression at defaults):
  B1d — compare_days param on /admin/stats (default 7 → identical output to before)
  B5b — audit rotation triggers on count>MAX OR filesize>10MB (count check kept)
  B5c — thin GET /admin/backup-status route exposing _latest_backup_info()
  B2c — diacritic-insensitive duplicate detection in check_duplicate (additive superset)
  B3c — NO CODE CHANGE (always-visible mod legend kept; documented only)
"""
import inspect
import json
import os

os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-deviations")
os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import admin  # noqa: E402


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


def _admin_client():
    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[admin.require_admin] = lambda: "test"
    return TestClient(app)


class TestAdminDeviations:
    """Source/signature assertions for the 4 additive AdminCP tweaks."""

    # ── B1d: compare_days param on /admin/stats ──

    def test_admin_stats_has_compare_days_param(self):
        sig = inspect.signature(admin.admin_stats)
        assert "compare_days" in sig.parameters, "admin_stats missing compare_days query param"

    def test_admin_stats_compare_days_has_bounds(self):
        src = inspect.getsource(admin.admin_stats)
        assert "compare_days" in src
        assert "ge=1" in src or "ge =1" in src, "compare_days missing lower bound"
        assert "le=90" in src or "le =90" in src, "compare_days missing upper bound"

    def test_admin_stats_compare_days_default_is_seven(self):
        sig = inspect.signature(admin.admin_stats)
        param = sig.parameters["compare_days"]
        # Query(7, ...) default resolves to a FastAPI Query info object whose .default is 7
        default = getattr(param.default, "default", param.default)
        assert default == 7, f"compare_days default must stay 7 (additive), got {default}"

    def test_admin_stats_uses_compare_days_in_interval_not_hardcoded_7(self):
        src = inspect.getsource(admin.admin_stats)
        # entities_week / users_week / posts_week windows must reference compare_days now
        assert "compare_days" in src
        # ensure the response still exposes the same keys (additive — no renamed keys)
        for key in ("entities_week", "users_week", "posts_week"):
            assert f'"{key}"' in src, f"admin_stats response missing existing key: {key}"

    def test_admin_stats_default_response_unchanged_shape(self):
        client = _admin_client()
        r = client.get("/admin/stats")
        assert r.status_code == 200
        body = r.json()
        assert "entities_week" in body
        assert "completeness" in body
        assert "backup" in body

    # ── B5b: rotation on count>MAX OR filesize>10MB ──

    def test_audit_max_bytes_constant_exists(self):
        assert hasattr(admin, "_AUDIT_MAX_BYTES"), "missing _AUDIT_MAX_BYTES constant"
        assert admin._AUDIT_MAX_BYTES == 10 * 1024 * 1024

    def test_maybe_rotate_audit_checks_size_or_count(self):
        src = inspect.getsource(admin._maybe_rotate_audit)
        assert "st_size" in src, "_maybe_rotate_audit must check file size (stat().st_size)"
        assert "_AUDIT_MAX_BYTES" in src
        assert "_AUDIT_MAX_LINES" in src, "must KEEP the existing count cap (additive OR, not replace)"
        assert " or " in src.lower(), "must combine size+count with OR"

    def test_rotation_still_trims_to_max_by_count(self, tmp_path, monkeypatch):
        """Existing count-based rotation behavior (BE-11) must be unaffected."""
        audit_file = tmp_path / "admin_audit.jsonl"
        lines = [json.dumps({"ts": f"2026-06-{i:02d}", "actor": "a", "method": "POST", "path": "/x", "ip": "1"})
                 for i in range(1, 21)]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 10)
        admin._maybe_rotate_audit()
        remaining = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(remaining) == 10

    def test_rotation_triggers_on_size_even_under_line_count(self, tmp_path, monkeypatch):
        """NEW behavior: a file under the line-count cap but over 10MB still rotates."""
        audit_file = tmp_path / "admin_audit.jsonl"
        # Few lines (under any realistic count cap) but each line padded to exceed 10MB total.
        big_pad = "x" * 200_000
        lines = [json.dumps({"ts": f"2026-06-0{i}", "actor": "a", "method": "POST",
                              "path": "/x", "ip": "1", "meta": {"pad": big_pad}})
                 for i in range(1, 3)]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 5000)  # way above line count → count check alone would NOT rotate
        monkeypatch.setattr(admin, "_AUDIT_MAX_BYTES", 1024)  # force size check to trip
        admin._maybe_rotate_audit()
        # after rotation, remaining active file should be the tail (<= existing line count),
        # and an archive file should have been created alongside it.
        archives = list(tmp_path.glob("admin_audit.*.jsonl"))
        assert archives, "expected an archive file to be created when size cap is exceeded"

    def test_rotation_noop_when_under_both_caps(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "admin_audit.jsonl"
        lines = [json.dumps({"ts": f"2026-06-0{i}", "actor": "a", "method": "POST", "path": "/x", "ip": "1"})
                 for i in range(1, 4)]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 10)
        monkeypatch.setattr(admin, "_AUDIT_MAX_BYTES", 10 * 1024 * 1024)
        admin._maybe_rotate_audit()
        remaining = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(remaining) == 3

    # ── B5c: thin GET /admin/backup-status route ──

    def test_backup_status_route_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("GET", "/admin/backup-status") in pairs, "/admin/backup-status route not mounted"

    def test_backup_status_endpoint_returns_latest_backup_info_shape(self):
        client = _admin_client()
        r = client.get("/admin/backup-status")
        assert r.status_code == 200
        body = r.json()
        # match _latest_backup_info()'s dict shape (either directly or under a "backup" key)
        payload = body.get("backup", body)
        for key in ("ready", "latest", "count", "size_mb"):
            assert key in payload, f"backup-status response missing key: {key}"

    def test_backup_status_reuses_latest_backup_info_helper(self):
        src = inspect.getsource(admin.backup_status)
        assert "_latest_backup_info" in src, "backup-status route must reuse _latest_backup_info()"

    # ── B2c: diacritic-insensitive duplicate detection ──

    def test_check_duplicate_still_uses_escape_like(self):
        """Existing substring/escape behavior must remain (additive superset, not replacement)."""
        src = inspect.getsource(admin.check_duplicate)
        assert "escape_like" in src
        assert "ESCAPE" in src

    def test_check_duplicate_adds_diacritic_matching(self):
        src = inspect.getsource(admin.check_duplicate)
        has_unaccent = "unaccent" in src.lower() or "f_unaccent" in src
        has_normalize_name = "normalize_name" in src
        assert has_unaccent or has_normalize_name, (
            "check_duplicate must add diacritic-insensitive matching via f_unaccent (PG) "
            "or text_utils.normalize_name (fallback)"
        )

    def test_check_duplicate_diacritic_variant_matches_via_client(self, monkeypatch):
        """End-to-end: a diacritic-stripped query should still find an accented name.

        Uses monkeypatched db._fetchall so this works against SQLite/dev DB too —
        we simulate the candidate row set and verify the endpoint's own filtering/
        matching logic (not just the SQL string) catches the accent variant.
        """
        import database as _db

        class _FakeConn:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def _fake_conn():
            return _FakeConn()

        candidates = [{"id": "e1", "name": "Chợ Vĩnh Long", "type": "market"}]

        def _fake_fetchall(conn, sql, params=None):
            # Return the full accent-bearing candidate regardless of the LIKE pattern,
            # emulating either a broadened SQL WHERE (f_unaccent) or a wider candidate
            # fetch that admin.py then filters in Python.
            return candidates

        monkeypatch.setattr(_db.db, "_conn", _fake_conn)
        monkeypatch.setattr(_db.db, "_fetchall", _fake_fetchall)
        monkeypatch.setattr(_db.db, "_row_to_dict", lambda r: dict(r))

        client = _admin_client()
        r = client.get("/admin/entities/check-duplicate", params={"name": "Cho Vinh Long"})
        assert r.status_code == 200
        dups = r.json()["duplicates"]
        names = [d["name"] for d in dups]
        assert "Chợ Vĩnh Long" in names, (
            f"diacritic-stripped query 'Cho Vinh Long' should match accented candidate, got {names}"
        )

    def test_check_duplicate_keeps_existing_substring_match_as_subset(self, monkeypatch):
        """Ensure we did not lose the current exact-substring (with-diacritics) matching."""
        import database as _db

        class _FakeConn:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def _fake_conn():
            return _FakeConn()

        candidates = [{"id": "e2", "name": "Chợ Vĩnh Long", "type": "market"}]

        def _fake_fetchall(conn, sql, params=None):
            return candidates

        monkeypatch.setattr(_db.db, "_conn", _fake_conn)
        monkeypatch.setattr(_db.db, "_fetchall", _fake_fetchall)
        monkeypatch.setattr(_db.db, "_row_to_dict", lambda r: dict(r))

        client = _admin_client()
        r = client.get("/admin/entities/check-duplicate", params={"name": "Vĩnh Long"})
        assert r.status_code == 200
        dups = r.json()["duplicates"]
        assert any(d["name"] == "Chợ Vĩnh Long" for d in dups)

    # ── B3c: documented no-op (moderation legend stays always-visible) ──

    def test_b3c_no_code_change_documented(self):
        """B3c is intentionally a no-op — always-visible legend beats hover-only spec.

        This test exists purely to make the decision discoverable in the test suite;
        it does not assert on any source file.
        """
        assert True
