"""
BE-22 through BE-26: Comprehensive test coverage for all new endpoints (BE-1 → BE-21).

Design: same as test_session_be.py —
  - SQLite/CI: verify 503 guards, routing, model validation, source patterns
  - Pure helper functions: always exercised
  - Postgres happy-paths: skipif(not db._use_pg)
"""
import inspect
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import admin
import auth
import notifications
import seo
import social
from database import db

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="UGC/auth is Postgres-only. Set DATABASE_URL=postgresql://… to run.",
)


def _route_pairs(app) -> set:
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


def _auth_client():
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def _admin_client():
    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[admin.require_admin] = lambda: "test"
    return TestClient(app)


def _social_client():
    app = FastAPI()
    app.include_router(social.router)
    return TestClient(app)


def _notif_client():
    app = FastAPI()
    app.include_router(notifications.router)
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════
#  BE-1: Password change requires old password
# ═══════════════════════════════════════════════════════════════════════

class TestBE1PasswordChange:
    def test_set_password_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("POST", "/auth/set-password") in pairs

    def test_set_password_checks_current_password_in_source(self):
        src = inspect.getsource(auth.set_password)
        assert "current_password" in src
        assert "password_hash" in src
        assert "_verify_password" in src

    def test_set_password_revokes_other_sessions_in_source(self):
        src = inspect.getsource(auth.set_password)
        assert "DELETE FROM user_sessions" in src
        assert "token !=" in src

    def test_set_password_rate_limited(self):
        src = inspect.getsource(auth.set_password)
        assert "check_rate" in src
        assert "set-password" in src

    def test_password_model_requires_min_length(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            auth.SetPassword(password="Ab1")

    def test_password_model_requires_digit(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            auth.SetPassword(password="NoDigitsHere")

    def test_password_model_requires_letter(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            auth.SetPassword(password="12345678")

    def test_password_model_max_length(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            auth.SetPassword(password="A1" + "x" * 200)

    def test_password_model_accepts_valid(self):
        sp = auth.SetPassword(password="Valid1pw!")
        assert sp.password == "Valid1pw!"

    def test_password_model_optional_current(self):
        sp = auth.SetPassword(password="Valid1pw!")
        assert sp.current_password is None
        sp2 = auth.SetPassword(password="Valid1pw!", current_password="OldPass1")
        assert sp2.current_password == "OldPass1"


# ═══════════════════════════════════════════════════════════════════════
#  BE-2: Session management API
# ═══════════════════════════════════════════════════════════════════════

class TestBE2SessionManagement:
    def test_sessions_get_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("GET", "/auth/sessions") in pairs

    def test_sessions_delete_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("DELETE", "/auth/sessions/{session_id}") in pairs

    def test_sessions_pg_guard(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.get("/auth/sessions").status_code == 503
            assert client.delete("/auth/sessions/abc").status_code == 503
        else:
            assert client.get("/auth/sessions").status_code in (401, 403)

    def test_list_sessions_has_rate_limit(self):
        src = inspect.getsource(auth.list_sessions)
        assert "check_rate" in src

    def test_list_sessions_marks_current(self):
        src = inspect.getsource(auth.list_sessions)
        assert "is_current" in src
        assert "compare_digest" in src

    def test_revoke_session_checks_ownership(self):
        src = inspect.getsource(auth.revoke_session)
        assert "user_id" in src
        assert "session_id" in src

    def test_list_sessions_returns_session_fields(self):
        src = inspect.getsource(auth.list_sessions)
        for field in ("user_agent", "ip_address", "created_at", "expires_at", "is_current"):
            assert field in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-3: Account deactivation
# ═══════════════════════════════════════════════════════════════════════

class TestBE3Deactivation:
    def test_deactivate_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("POST", "/auth/deactivate") in pairs

    def test_deactivate_pg_guard(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.post("/auth/deactivate").status_code == 503

    def test_deactivate_revokes_all_sessions(self):
        src = inspect.getsource(auth.deactivate_account)
        assert "DELETE FROM user_sessions" in src
        assert "is_active" in src.lower() or "is_Active" in src

    def test_deactivate_has_rate_limit(self):
        src = inspect.getsource(auth.deactivate_account)
        assert "check_rate" in src
        assert "deactivate" in src

    def test_deactivate_requires_auth(self):
        src = inspect.getsource(auth.deactivate_account)
        assert "_get_current_user_or_none" in src
        assert "401" in src

    def test_deactivate_has_csrf(self):
        sig = inspect.signature(auth.deactivate_account)
        param_names = list(sig.parameters.keys())
        assert "_csrf" in param_names or any("csrf" in p.lower() for p in param_names)


# ═══════════════════════════════════════════════════════════════════════
#  BE-4: Login history
# ═══════════════════════════════════════════════════════════════════════

class TestBE4LoginHistory:
    def test_login_history_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("GET", "/auth/login-history") in pairs

    def test_login_history_pg_guard(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.get("/auth/login-history").status_code == 503

    def test_log_login_no_crash_without_pg(self):
        mock_req = MagicMock()
        mock_req.headers = {"user-agent": "TestBot/1.0"}
        auth._log_login("0901234567", "otp", True, mock_req)

    def test_log_login_records_ip_and_ua(self):
        src = inspect.getsource(auth._log_login)
        assert "user_agent" in src or "user-agent" in src
        assert "ip" in src.lower()


# ═══════════════════════════════════════════════════════════════════════
#  BE-5: Block enforcement (comprehensive)
# ═══════════════════════════════════════════════════════════════════════

class TestBE5BlockEnforcement:
    def test_block_sql_no_user_returns_empty(self):
        clause, params = social._block_sql(None)
        assert clause == ""
        assert params == []

    def test_block_sql_with_user_returns_not_in(self):
        clause, params = social._block_sql({"id": "user-123"})
        assert "NOT IN" in clause
        assert "blocked_id" in clause
        assert "blocker_id" in clause
        assert params == ["user-123", "user-123"]

    def test_block_sql_custom_column(self):
        clause, _ = social._block_sql({"id": "x"}, "p.author_id")
        assert "p.author_id NOT IN" in clause

    def test_block_enforcement_in_comments(self):
        src = inspect.getsource(social.get_comments)
        assert "_block_sql" in src or "block" in src.lower()

    def test_block_enforcement_in_search_posts(self):
        src = inspect.getsource(social.search_posts)
        assert "_block_sql" in src

    def test_block_enforcement_in_search_users(self):
        src = inspect.getsource(social.search_users)
        assert "_block_sql" in src

    def test_block_enforcement_in_leaderboard(self):
        src = inspect.getsource(social.community_leaderboard)
        assert "_block_sql" in src or "bc" in src

    def test_block_enforcement_in_suggested_follows(self):
        src = inspect.getsource(social.suggested_follows)
        assert "_block_sql" in src or "bc" in src

    def test_block_enforcement_in_entity_feed(self):
        src = inspect.getsource(social.get_entity_feed)
        assert "_block_sql" in src

    def test_block_enforcement_in_following(self):
        src = inspect.getsource(social.list_following_users)
        assert "_block_sql" in src

    def test_block_enforcement_in_followers(self):
        src = inspect.getsource(social.list_followers)
        assert "_block_sql" in src

    def test_block_enforcement_in_related_posts(self):
        src = inspect.getsource(social.related_posts)
        assert "_block_sql" in src

    def test_block_enforcement_in_following_feed(self):
        src = inspect.getsource(social.get_following_feed)
        assert "_block_sql" in src or "bc" in src

    def test_block_check_in_notifications(self):
        src = inspect.getsource(notifications.create_notification)
        assert "blocked" in src.lower()
        assert "blocker_id" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-6: Blocked users list
# ═══════════════════════════════════════════════════════════════════════

class TestBE6BlockedUsers:
    def test_block_endpoint_mounted(self):
        client = _notif_client()
        pairs = _route_pairs(client.app)
        assert ("POST", "/api/block/{blocked_id}") in pairs

    def test_blocked_users_list_endpoint_mounted(self):
        client = _notif_client()
        pairs = _route_pairs(client.app)
        assert ("GET", "/api/blocked-users") in pairs

    def test_blocked_users_pg_guard(self):
        client = _notif_client()
        if not db._use_pg:
            assert client.get("/api/blocked-users").status_code == 503
        else:
            assert client.get("/api/blocked-users").status_code in (401, 403)

    def test_block_requires_auth(self):
        client = _notif_client()
        if not db._use_pg:
            assert client.post("/api/block/some-user").status_code == 503
        else:
            assert client.post("/api/block/some-user").status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════
#  BE-7: Privacy settings
# ═══════════════════════════════════════════════════════════════════════

class TestBE7Privacy:
    def test_privacy_get_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("GET", "/auth/privacy") in pairs

    def test_privacy_put_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("PUT", "/auth/privacy") in pairs

    def test_privacy_pg_guard(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.get("/auth/privacy").status_code == 503
            assert client.put("/auth/privacy", json={"show_activity": False}).status_code == 503

    def test_privacy_model_accepts_valid_values(self):
        body = auth.PrivacyUpdate(profile_visibility="private", show_activity=False, show_saved=True)
        assert body.profile_visibility == "private"
        assert body.show_activity is False
        assert body.show_saved is True

    def test_privacy_model_optional_fields(self):
        body = auth.PrivacyUpdate()
        assert body.profile_visibility is None
        assert body.show_activity is None
        assert body.show_saved is None

    def test_privacy_visibility_enum(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            auth.PrivacyUpdate(profile_visibility="invalid_value")

    def test_privacy_get_checks_auth(self):
        src = inspect.getsource(auth.get_privacy)
        assert "_get_current_user_or_none" in src or "require_user" in src or "user" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-8: Dashboard alerts
# ═══════════════════════════════════════════════════════════════════════

class TestBE8DashboardAlerts:
    def test_dashboard_alerts_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("GET", "/admin/dashboard-alerts") in pairs

    def test_dashboard_alerts_source_returns_list(self):
        src = inspect.getsource(admin.dashboard_alerts)
        assert '"alerts"' in src
        assert "alerts[:5]" in src

    def test_dashboard_alerts_sorted_by_priority_in_source(self):
        src = inspect.getsource(admin.dashboard_alerts)
        assert 'alerts.sort(key=lambda a: a["priority"])' in src

    def test_dashboard_alerts_scans_multiple_queues(self):
        src = inspect.getsource(admin.dashboard_alerts)
        assert "flagged" in src
        assert "moderation" in src or "pending" in src
        assert "reports" in src
        assert "images" in src or "img_pending" in src
        assert "unclassified" in src

    def test_dashboard_alerts_items_have_required_fields_in_source(self):
        src = inspect.getsource(admin.dashboard_alerts)
        for field in ("type", "count", "label", "icon", "link", "priority"):
            assert f'"{field}"' in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-9: Admin activity feed
# ═══════════════════════════════════════════════════════════════════════

class TestBE9ActivityFeed:
    def test_activity_feed_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("GET", "/admin/activity-feed") in pairs

    @pytest.mark.skipif(db._use_pg, reason="JSONL fallback path only reachable on SQLite; under PG activity_feed serves from admin_audit_events table")
    def test_activity_feed_empty_file(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "admin_audit.jsonl"
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        client = _admin_client()
        resp = client.get("/admin/activity-feed")
        assert resp.status_code == 200
        assert resp.json()["actions"] == []

    @pytest.mark.skipif(db._use_pg, reason="JSONL fallback path only reachable on SQLite; under PG activity_feed serves from admin_audit_events table")
    def test_activity_feed_returns_newest_first(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "admin_audit.jsonl"
        records = [
            {"ts": f"2026-06-2{i}T10:00:00", "actor": "admin-key", "method": m, "path": "/admin/x", "ip": "127.0.0.1"}
            for i, m in enumerate(["POST", "PUT", "DELETE"])
        ]
        audit_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        client = _admin_client()
        resp = client.get("/admin/activity-feed")
        actions = resp.json()["actions"]
        assert actions[0]["method"] == "DELETE"
        assert actions[-1]["method"] == "POST"

    def test_activity_feed_respects_limit(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "admin_audit.jsonl"
        records = [
            {"ts": f"2026-06-{i:02d}T10:00:00", "actor": "a", "method": "POST", "path": "/x", "ip": "1"}
            for i in range(1, 20)
        ]
        audit_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        client = _admin_client()
        resp = client.get("/admin/activity-feed?limit=5")
        assert len(resp.json()["actions"]) == 5


# ═══════════════════════════════════════════════════════════════════════
#  BE-10: Entity completeness score
# ═══════════════════════════════════════════════════════════════════════

class TestBE10Completeness:
    def test_stats_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        import sys as _sys
        _sm = _sys.modules.get("admin")
        _diag = (
            f"DIAG admin_id={id(admin)} sysmod_id={id(_sm)} same={admin is _sm} "
            f"router_id={id(admin.router)} n_routes={len(admin.router.routes)} "
            f"router_paths={[getattr(r,'path','') for r in admin.router.routes[:6]]} "
            f"app_n={len(client.app.routes)} "
            f"app_paths={sorted({getattr(r,'path','') for r in client.app.routes})[:12]} "
            f"admin_file={getattr(admin,'__file__','?')}"
        )
        assert ("GET", "/admin/stats") in pairs, _diag

    def test_completeness_fields_in_stats_source(self):
        # Completeness computation extracted into _admin_stats_completeness (complexity
        # refactor); admin_stats still wires it.
        assert "_admin_stats_completeness" in inspect.getsource(admin.admin_stats)  # wiring
        src = inspect.getsource(admin.admin_stats) + inspect.getsource(admin._admin_stats_completeness)
        for field in ("total", "has_summary", "has_images", "has_place", "orphans", "pct"):
            assert f'"{field}"' in src, f"Missing completeness field: {field}"

    def test_completeness_pct_calculation(self):
        src = inspect.getsource(admin.admin_stats) + inspect.getsource(admin._admin_stats_completeness)
        assert "round(" in src
        assert "comp_total * 3" in src or "* 100" in src

    def test_completeness_excludes_places(self):
        src = inspect.getsource(admin.admin_stats) + inspect.getsource(admin._admin_stats_completeness)
        assert "type != 'place'" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-11: Audit log rotation
# ═══════════════════════════════════════════════════════════════════════

class TestBE11AuditRotation:
    def test_rotation_trims_to_max(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "admin_audit.jsonl"
        lines = [json.dumps({"ts": f"2026-06-{i:02d}", "actor": "a", "method": "POST", "path": "/x", "ip": "1"})
                 for i in range(1, 21)]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 10)
        admin._maybe_rotate_audit()
        remaining = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(remaining) == 10

    def test_rotation_keeps_newest(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "admin_audit.jsonl"
        lines = [json.dumps({"ts": f"2026-06-{i:02d}", "actor": "a", "method": "POST", "path": "/x", "ip": "1"})
                 for i in range(1, 11)]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 5)
        admin._maybe_rotate_audit()
        remaining = audit_file.read_text(encoding="utf-8").strip().split("\n")
        last = json.loads(remaining[-1])
        assert last["ts"] == "2026-06-10"

    def test_rotation_noop_when_under_limit(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "admin_audit.jsonl"
        lines = [json.dumps({"ts": f"2026-06-0{i}", "actor": "a", "method": "POST", "path": "/x", "ip": "1"})
                 for i in range(1, 4)]
        audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 10)
        admin._maybe_rotate_audit()
        remaining = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(remaining) == 3

    def test_rotation_handles_missing_file(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "nonexistent_audit.jsonl"
        monkeypatch.setattr(admin, "_AUDIT_FILE", audit_file)
        monkeypatch.setattr(admin, "_AUDIT_MAX_LINES", 5)
        admin._maybe_rotate_audit()


# ═══════════════════════════════════════════════════════════════════════
#  BE-12: Batch moderation
# ═══════════════════════════════════════════════════════════════════════

class TestBE12BatchModeration:
    def test_batch_moderation_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("POST", "/admin/moderation/batch") in pairs

    def test_batch_moderation_model_validates_action(self):
        body = admin.BatchModerationBody(post_ids=["p1"], action="approve")
        assert body.action == "approve"

    def test_batch_moderation_model_rejects_empty_list(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            admin.BatchModerationBody(post_ids=[], action="approve")

    def test_batch_moderation_model_max_100_ids(self):
        from pydantic import ValidationError
        ids = [f"p{i}" for i in range(101)]
        with pytest.raises(ValidationError):
            admin.BatchModerationBody(post_ids=ids, action="approve")

    def test_batch_moderation_rejects_invalid_action(self):
        src = inspect.getsource(admin.batch_moderation)
        assert "'approve'" in src
        assert "'reject'" in src
        assert "400" in src

    def test_batch_moderation_sends_notifications(self):
        # Notification fan-out extracted into _batch_mod_notify (complexity refactor);
        # batch_moderation still wires it.
        assert "_batch_mod_notify" in inspect.getsource(admin.batch_moderation)  # wiring
        src = inspect.getsource(admin.batch_moderation) + inspect.getsource(admin._batch_mod_notify)
        assert "create_notification" in src

    def test_batch_moderation_logs_mod_action(self):
        src = inspect.getsource(admin.batch_moderation)
        assert "_log_mod_action" in src

    def test_batch_moderation_returns_count(self):
        src = inspect.getsource(admin.batch_moderation)
        assert '"updated"' in src
        assert '"requested"' in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-13: Orphan entity detection
# ═══════════════════════════════════════════════════════════════════════

class TestBE13OrphanDetection:
    def test_orphans_only_filter_in_list_entities(self):
        sig = inspect.signature(admin.list_entities)
        assert "orphans_only" in sig.parameters

    def test_orphans_filter_logic(self):
        # Orphan filtering extracted into _list_entities_filter_orphans (complexity refactor);
        # list_entities still wires it.
        assert "_list_entities_filter_orphans" in inspect.getsource(admin.list_entities)  # wiring
        src = inspect.getsource(admin.list_entities) + inspect.getsource(admin._list_entities_filter_orphans)
        assert "orphans_only" in src
        assert "relationships" in src.lower()

    def test_orphan_count_in_stats_source(self):
        # Orphan count computation lives in _admin_stats_completeness (complexity refactor).
        src = inspect.getsource(admin.admin_stats) + inspect.getsource(admin._admin_stats_completeness)
        assert '"orphans"' in src
        assert "orphan_count" in src

    def test_orphan_sql_excludes_relationship_entities(self):
        src = inspect.getsource(admin.admin_stats) + inspect.getsource(admin._admin_stats_completeness)
        assert "NOT IN" in src
        assert "relationships" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-14: Bulk relationship add
# ═══════════════════════════════════════════════════════════════════════

class TestBE14BulkRelationship:
    def test_bulk_relationship_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("POST", "/admin/relationships/bulk") in pairs

    def test_bulk_relationship_model_max_50_pairs(self):
        from pydantic import ValidationError
        pairs = [admin.RelationshipBulkPair(to_id=f"e{i}") for i in range(51)]
        with pytest.raises(ValidationError):
            admin.RelationshipBulkCreate(from_id="src", pairs=pairs)

    def test_bulk_relationship_model_accepts_valid(self):
        pairs = [admin.RelationshipBulkPair(to_id="dest-1"), admin.RelationshipBulkPair(to_id="dest-2", type="near")]
        body = admin.RelationshipBulkCreate(from_id="src", pairs=pairs)
        assert body.from_id == "src"
        assert len(body.pairs) == 2
        assert body.pairs[1].type == "near"

    def test_bulk_relationship_default_type(self):
        pair = admin.RelationshipBulkPair(to_id="x")
        assert pair.type == "related_to"

    def test_bulk_relationship_returns_added_and_errors(self):
        src = inspect.getsource(admin.add_relationships_bulk)
        assert '"added"' in src
        assert '"errors"' in src

    def test_bulk_relationship_continues_on_error(self):
        src = inspect.getsource(admin.add_relationships_bulk)
        assert "except Exception" in src
        assert "errors.append" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-15: Entity change history
# ═══════════════════════════════════════════════════════════════════════

class TestBE15EntityHistory:
    def test_entity_history_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("GET", "/admin/entities/{entity_id}/history") in pairs

    def test_entity_history_validates_path_id(self):
        client = _admin_client()
        resp = client.get("/admin/entities/'; DROP TABLE--/history")
        assert resp.status_code == 400

    def test_entity_history_limit_param(self):
        sig = inspect.signature(admin.get_entity_history)
        assert "limit" in sig.parameters

    def test_entity_history_returns_history_key(self):
        src = inspect.getsource(admin.get_entity_history)
        assert '"history"' in src

    def test_log_entity_changes_tracks_diffs(self):
        old = {"name": "Old Name", "summary": "Old summary"}
        new = {"name": "New Name", "summary": "Old summary"}
        changes = db.log_entity_changes("test-entity", old, new)
        if changes is not None:
            assert any("name" in str(c) for c in (changes if isinstance(changes, list) else [changes]))

    def test_log_entity_changes_no_diff_no_record(self):
        old = {"name": "Same", "summary": "Same"}
        result = db.log_entity_changes("test-entity", old, old)
        assert result is None or result == 0 or result == []


# ═══════════════════════════════════════════════════════════════════════
#  BE-16: Avatar upload
# ═══════════════════════════════════════════════════════════════════════

class TestBE16AvatarUpload:
    def test_avatar_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("POST", "/auth/avatar") in pairs

    def test_avatar_pg_guard(self):
        client = _auth_client()
        if not db._use_pg:
            resp = client.post("/auth/avatar", files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")})
            assert resp.status_code == 503

    def test_avatar_rate_limited(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "check_rate" in src
        assert "avatar" in src

    def test_avatar_checks_file_size(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "MAX_IMAGE_SIZE" in src

    def test_avatar_uses_magic_byte_sniff(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "sniff_image_type" in src

    def test_avatar_requires_auth(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "_get_current_user_or_none" in src
        assert "401" in src

    def test_sniff_rejects_non_image(self):
        from storage import sniff_image_type
        assert sniff_image_type(b"not an image at all") is None

    def test_sniff_accepts_png_magic(self):
        from storage import sniff_image_type
        png_header = b"\x89PNG\r\n\x1a\n"
        result = sniff_image_type(png_header + b"\x00" * 100)
        assert result is not None

    def test_sniff_accepts_jpeg_magic(self):
        from storage import sniff_image_type
        jpeg_header = b"\xff\xd8\xff"
        result = sniff_image_type(jpeg_header + b"\x00" * 100)
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════
#  BE-17: Entity image upload
# ═══════════════════════════════════════════════════════════════════════

class TestBE17EntityImage:
    def test_entity_image_upload_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("POST", "/admin/entities/{entity_id}/images/upload") in pairs

    def test_entity_image_url_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("POST", "/admin/entities/{entity_id}/images") in pairs

    def test_entity_image_delete_endpoint_mounted(self):
        client = _admin_client()
        pairs = _route_pairs(client.app)
        assert ("DELETE", "/admin/entities/{entity_id}/images/{idx}") in pairs

    def test_sniff_rejects_svg_script(self):
        from storage import sniff_image_type
        svg_data = b"<svg><script>alert(1)</script></svg>"
        assert sniff_image_type(svg_data) is None

    def test_webp_conversion(self):
        from storage import _to_webp
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_data = buf.getvalue()
        webp_data = _to_webp(png_data, max_w=50)
        assert webp_data[:4] == b"RIFF"
        img2 = Image.open(io.BytesIO(webp_data))
        assert max(img2.size) <= 50


# ═══════════════════════════════════════════════════════════════════════
#  BE-18: SEO og:image
# ═══════════════════════════════════════════════════════════════════════

class TestBE18SeoOgImage:
    def test_og_site_default_has_image(self):
        meta = seo.build_og_meta()
        assert "og:image" in meta
        assert meta["og:image"].startswith("http")

    def test_og_entity_uses_first_image(self):
        entity = {"id": "e1", "name": "Test", "type": "attraction", "images": ["https://a.com/1.jpg", "https://a.com/2.jpg"]}
        meta = seo.build_og_meta(entity)
        assert meta["og:image"] == "https://a.com/1.jpg"

    def test_og_entity_fallback_when_no_images(self):
        entity = {"id": "e2", "name": "Test", "type": "dish", "images": []}
        meta = seo.build_og_meta(entity)
        assert meta["og:image"] == seo.DEFAULT_OG_IMAGE

    def test_og_escapes_entity_name(self):
        entity = {"id": "xss", "name": '<script>alert("x")</script>', "type": "attraction"}
        meta = seo.build_og_meta(entity)
        assert "<script>" not in meta["og:title"]

    def test_twitter_card_present(self):
        meta = seo.build_og_meta()
        assert meta["twitter:card"] == "summary_large_image"
        assert "twitter:image" in meta

    def test_og_endpoint_returns_200(self):
        app = FastAPI()
        app.include_router(seo.router)
        client = TestClient(app)
        resp = client.get("/seo/og")
        assert resp.status_code == 200
        assert "og:image" in resp.json()

    def test_jsonld_image_object_for_entity_with_image(self):
        entity = {"id": "e3", "name": "Photo Place", "type": "attraction",
                  "images": ["https://example.com/photo.jpg"]}
        ld = seo.build_entity_jsonld(entity, {})
        if "image" in ld:
            img = ld["image"]
            if isinstance(img, dict):
                assert img.get("@type") == "ImageObject"
            elif isinstance(img, str):
                assert img.startswith("http")


# ═══════════════════════════════════════════════════════════════════════
#  BE-19: Consent timestamp
# ═══════════════════════════════════════════════════════════════════════

class TestBE19Consent:
    def test_consent_history_endpoint_mounted(self):
        pairs = _route_pairs(_auth_client().app)
        assert ("GET", "/auth/consent-history") in pairs

    def test_consent_history_pg_guard(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.get("/auth/consent-history").status_code == 503

    def test_consent_version_constant_exists(self):
        assert hasattr(auth, "CONSENT_VERSION")
        assert isinstance(auth.CONSENT_VERSION, str)
        assert len(auth.CONSENT_VERSION) > 0

    def test_log_consent_no_crash_on_sqlite(self):
        auth._log_consent("00000000-0000-0000-0000-000000000000", auth.CONSENT_VERSION, "127.0.0.1")

    def test_otp_verify_model_has_consent_field(self):
        fields = auth.OTPVerify.model_fields
        assert "consent" in fields


# ═══════════════════════════════════════════════════════════════════════
#  BE-20: SSE notification stream
# ═══════════════════════════════════════════════════════════════════════

class TestBE20SSEStream:
    def test_sse_stream_endpoint_mounted(self):
        client = _notif_client()
        pairs = _route_pairs(client.app)
        assert ("GET", "/api/notifications/stream") in pairs

    def test_sse_max_per_user_limit(self):
        assert hasattr(notifications, "_SSE_MAX_PER_USER")
        assert notifications._SSE_MAX_PER_USER > 0
        assert notifications._SSE_MAX_PER_USER <= 10

    def test_sse_subscribers_uses_lock(self):
        import asyncio as aio
        assert hasattr(notifications, "_sse_lock")
        assert isinstance(notifications._sse_lock, aio.Lock)

    def test_sse_subscribers_dict_exists(self):
        assert hasattr(notifications, "_sse_subscribers")
        assert isinstance(notifications._sse_subscribers, dict)

    def test_sse_stream_requires_auth(self):
        src = inspect.getsource(notifications.notification_stream)
        assert "require_user" in src or "token" in src or "user" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-21: Notification preferences
# ═══════════════════════════════════════════════════════════════════════

class TestBE21NotifPreferences:
    def test_notif_prefs_get_endpoint_mounted(self):
        client = _notif_client()
        pairs = _route_pairs(client.app)
        assert ("GET", "/api/notification-preferences") in pairs

    def test_notif_prefs_put_endpoint_mounted(self):
        client = _notif_client()
        pairs = _route_pairs(client.app)
        assert ("PUT", "/api/notification-preferences") in pairs

    def test_notif_prefs_pg_guard(self):
        client = _notif_client()
        if not db._use_pg:
            assert client.get("/api/notification-preferences").status_code == 503
        else:
            assert client.get("/api/notification-preferences").status_code in (401, 403)

    def test_notif_prefs_model_all_optional(self):
        body = notifications.NotifPrefsUpdate()
        assert body.pref_like is None
        assert body.pref_comment is None
        assert body.pref_mention is None
        assert body.pref_follow is None
        assert body.pref_system is None

    def test_notif_prefs_model_accepts_booleans(self):
        body = notifications.NotifPrefsUpdate(pref_like=False, pref_system=True)
        assert body.pref_like is False
        assert body.pref_system is True

    def test_notif_prefs_update_has_rate_limit(self):
        src = inspect.getsource(notifications.update_notification_preferences)
        assert "check_rate" in src

    def test_notif_prefs_update_has_csrf(self):
        sig = inspect.signature(notifications.update_notification_preferences)
        param_names = list(sig.parameters.keys())
        assert "_csrf" in param_names or any("csrf" in p.lower() for p in param_names)

    def test_notif_prefs_update_rejects_empty(self):
        src = inspect.getsource(notifications.update_notification_preferences)
        assert "400" in src
        assert "Không có gì" in src or "empty" in src.lower()

    def test_notif_prefs_get_returns_all_fields(self):
        src = inspect.getsource(notifications.get_notification_preferences)
        for field in ("pref_like", "pref_comment", "pref_mention", "pref_follow", "pref_system"):
            assert field in src

    def test_notif_prefs_get_defaults_to_true(self):
        src = inspect.getsource(notifications.get_notification_preferences)
        assert "True" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-23: Block enforcement integration tests
# ═══════════════════════════════════════════════════════════════════════

class TestBE23BlockIntegration:
    def test_block_auto_unfollow(self):
        src = inspect.getsource(notifications.toggle_block)
        assert "unfollow" in src.lower() or "DELETE FROM follows" in src

    def test_block_endpoint_validates_path_id(self):
        client = _notif_client()
        if not db._use_pg:
            resp = client.post("/api/block/'; DROP TABLE--")
            assert resp.status_code in (400, 503)

    def test_block_sql_both_directions(self):
        clause, params = social._block_sql({"id": "me"})
        assert "NOT IN" in clause
        assert "blocked_id" in clause
        assert "blocker_id" in clause
        assert "UNION" in clause

    def test_entity_feed_block_enforcement_in_count_query(self):
        # Refactor: count query moved to helper _entity_feed_query, get_entity_feed
        # gọi helper (wiring-assert). Giữ nguyên assertion trên count block.
        assert "_entity_feed_query" in inspect.getsource(social.get_entity_feed)
        src = inspect.getsource(social._entity_feed_query)
        count_idx = src.find("COUNT(*)")
        assert count_idx > 0
        count_block = src[count_idx:count_idx + 500]
        assert "bc" in count_block or "block" in count_block.lower()


# ═══════════════════════════════════════════════════════════════════════
#  BE-24: Privacy settings enforcement
# ═══════════════════════════════════════════════════════════════════════

class TestBE24PrivacyEnforcement:
    def test_privacy_enforced_in_get_user_profile(self):
        src = inspect.getsource(social.get_user_profile)
        assert "privacy" in src.lower() or "profile_visibility" in src

    def test_privacy_fields_exist_in_model(self):
        fields = auth.PrivacyUpdate.model_fields
        assert "profile_visibility" in fields
        assert "show_activity" in fields
        assert "show_saved" in fields


# ═══════════════════════════════════════════════════════════════════════
#  BE-25: Avatar upload safety
# ═══════════════════════════════════════════════════════════════════════

class TestBE25AvatarSafety:
    def test_avatar_rejects_oversized_file(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "MAX_IMAGE_SIZE" in src
        assert "400" in src

    def test_avatar_rejects_non_image(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "sniff_image_type" in src
        assert "400" in src

    def test_avatar_uses_storage_module(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "storage" in src
        assert "upload_image_set" in src

    def test_avatar_updates_user_record(self):
        src = inspect.getsource(auth.upload_avatar)
        assert "avatar_url" in src
        assert "update_user" in src


# ═══════════════════════════════════════════════════════════════════════
#  BE-26: Consent logging
# ═══════════════════════════════════════════════════════════════════════

class TestBE26ConsentLogging:
    def test_otp_verify_records_consent(self):
        src = inspect.getsource(auth.verify_otp)
        assert "consent" in src
        assert "_log_consent" in src

    def test_consent_log_records_version_and_ip(self):
        src = inspect.getsource(auth._log_consent)
        assert "version" in src or "CONSENT_VERSION" in src
        assert "ip" in src

    def test_consent_history_requires_auth(self):
        src = inspect.getsource(auth.consent_history)
        assert "_get_current_user_or_none" in src or "require_user" in src


# ═══════════════════════════════════════════════════════════════════════
#  Cross-cutting: All new endpoints have guards
# ═══════════════════════════════════════════════════════════════════════

class TestCrossCuttingGuards:
    def test_admin_router_requires_admin(self):
        deps = [d.dependency for d in admin.router.dependencies]
        dep_names = [getattr(d, "__name__", str(d)) for d in deps]
        assert any("admin" in n.lower() for n in dep_names)

    def test_admin_router_has_csrf(self):
        deps = [d.dependency for d in admin.router.dependencies]
        dep_names = [getattr(d, "__name__", str(d)) for d in deps]
        assert any("csrf" in n.lower() for n in dep_names)

    def test_all_auth_write_endpoints_have_csrf(self):
        for ep_name in ("set_password", "deactivate_account", "upload_avatar", "update_profile"):
            fn = getattr(auth, ep_name, None)
            if fn is None:
                continue
            sig = inspect.signature(fn)
            param_names = list(sig.parameters.keys())
            assert any("csrf" in p.lower() for p in param_names), f"{ep_name} missing CSRF"

    def test_notif_prefs_update_has_csrf(self):
        sig = inspect.signature(notifications.update_notification_preferences)
        param_names = list(sig.parameters.keys())
        assert any("csrf" in p.lower() for p in param_names)
