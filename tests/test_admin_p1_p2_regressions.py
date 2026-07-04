"""P1/P2 AdminCP regression guards."""

import inspect

import admin
import data_quality
import site_settings


def test_data_quality_decision_history_latest_wins(tmp_path):
    data_quality._append_decision_history(
        {
            "batch_id": "b1",
            "candidate_ids": ["c1"],
            "decision": "reject",
            "decided_at": "2026-01-01T00:00:00+00:00",
        },
        output_dir=tmp_path,
    )
    data_quality._append_decision_history(
        {
            "batch_id": "b2",
            "candidate_ids": ["c1"],
            "decision": "defer",
            "decided_at": "2026-01-02T00:00:00+00:00",
        },
        output_dir=tmp_path,
    )

    history = data_quality.load_decision_history(limit=1, output_dir=tmp_path)
    latest = data_quality.latest_candidate_decisions(output_dir=tmp_path)

    assert history["total"] == 2
    assert history["decisions"][0]["decision"] == "defer"
    assert latest["c1"]["decision"] == "defer"


def test_data_quality_review_candidates_include_latest_decision(monkeypatch):
    monkeypatch.setattr(
        data_quality,
        "latest_candidate_decisions",
        lambda: {
            "c1": {
                "decision": "reject",
                "note": "weak evidence",
                "decided_at": "2026-01-02T00:00:00+00:00",
                "reviewer": "u1",
            }
        },
    )
    queue = {
        "needs_review": [
            {
                "candidate_id": "c1",
                "entity_id": "e1",
                "field": "source",
                "suggested_value": {"url": "https://example.com"},
            }
        ]
    }

    result = data_quality.filter_candidates(queue, bucket="needs_review")
    candidate = result["candidates"][0]

    assert candidate["decision"] == "reject"
    assert candidate["decision_note"] == "weak evidence"
    assert candidate["decision_by"] == "u1"


def test_admin_p1_p2_endpoints_are_mounted_in_source():
    src = inspect.getsource(admin)

    assert 'class DataQualityDecisionRequest' in src
    assert '@router.post("/data-quality/decision"' in src
    assert "data_quality.decide_candidates" in src
    assert 'class BulkAssignPlaceRequest' in src
    assert '@router.post("/entities/bulk-place"' in src
    assert '@router.get("/ops-summary"' in src
    assert "deploy_health_blocking" in src
    assert "schema_ok" in inspect.getsource(admin.ops_summary)
    assert "shared_controls" in inspect.getsource(admin.ops_summary)
    assert "check_migration_gate.py" in src
    assert "quality_budget.py" in src
    assert "_quality_trend_ops_snapshot" in src
    assert '"quality_trend": quality_trend' in inspect.getsource(admin.ops_summary)
    assert "rollback" in inspect.getsource(admin.ops_summary)
    assert "restore_drill_script" in inspect.getsource(admin.ops_summary)
    assert '@router.get("/site-settings-history"' in src
    assert '@router.post("/site-settings-history/{history_id}/rollback"' in src

def test_admin_audit_uses_db_append_only_with_jsonl_fallback():
    src = inspect.getsource(admin)
    log_src = inspect.getsource(admin._log_admin_audit)
    db_src = inspect.getsource(admin._log_admin_audit_db)
    read_src = inspect.getsource(admin.get_audit_log)
    require_src = inspect.getsource(admin.require_admin)

    assert "ADMIN_ROLE_SCOPES" in src
    assert "ADMIN_SCOPE_RULES" in src
    assert "admin_scopes_for_user" in src
    assert "request.state.admin_scopes" in inspect.getsource(admin.require_admin)
    assert "_has_admin_entry_scope(user)" in require_src
    assert "_admin_required_scope_for_path(request.url.path)" in require_src
    assert "_ensure_admin_scope(request, required_scope)" in require_src
    assert "admin_audit_events" in db_src
    assert "before_json" in db_src
    assert "after_json" in db_src
    assert "actor_scopes" in db_src
    assert "_log_admin_audit_db(rec)" in log_src
    assert "_query_admin_audit_db" in read_src
    assert '_ensure_admin_scope(request, "security.admin")' in inspect.getsource(admin.set_user_role)

def test_admin_scope_matrix_maps_core_route_groups():
    assert admin.admin_scopes_for_user({"role": "moderator"}) == ["moderation.manager"]
    assert admin._has_admin_entry_scope({"role": "moderator"}) is True
    assert admin._has_admin_entry_scope({"role": "user"}) is False

    cases = {
        "/admin/users": "security.admin",
        "/admin-api/users/abc/role": "security.admin",
        "/admin/activity-feed": "security.admin",
        "/admin/user-growth": "security.admin",
        "/admin/site-settings/footer": "settings.admin",
        "/admin/moderation/queue": "moderation.manager",
        "/admin/reports/bulk": "moderation.manager",
        "/admin/entities": "content.editor",
        "/admin/data-quality/decision": "content.editor",
        "/admin/backup-trigger": "ops.deploy",
        "/admin/ai/triage": "ops.deploy",
        "/admin/analytics-overview": "ops.deploy",
    }
    for path, scope in cases.items():
        assert admin._admin_required_scope_for_path(path) == scope

    assert admin._admin_required_scope_for_path("/admin") is None
    assert admin._admin_required_scope_for_path("/admin/badge-counts") is None

def test_admin_audit_migration_and_schema_version_exist():
    migration = admin.ROOT / "agent" / "migrations" / "054_admin_audit_events.sql"
    sql = migration.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS admin_audit_events" in sql
    assert "actor_scopes TEXT[]" in sql
    assert "request_id" in sql
    assert "before_json" in sql
    assert "after_json" in sql
    assert "CREATE TABLE IF NOT EXISTS schema_version" in sql
    assert "054_admin_audit_events.sql" in sql


def test_site_settings_history_supports_audit_and_rollback():
    src = inspect.getsource(site_settings)
    record_src = inspect.getsource(site_settings._record_history)
    upsert_src = inspect.getsource(site_settings.upsert)
    bulk_src = inspect.getsource(site_settings.bulk_upsert)
    reset_src = inspect.getsource(site_settings.reset_category)
    rollback_src = inspect.getsource(site_settings.rollback_history)

    assert "site_settings_history" in src
    assert "INSERT INTO site_settings_history" in record_src
    assert "_ensure_history_table()" not in record_src
    assert "actor: str | None = None" in upsert_src
    assert "action=\"bulk_update\"" in bulk_src
    assert "action=\"reset\"" in reset_src
    assert "action=\"rollback\"" in rollback_src
    assert "previous_value" in rollback_src


def test_batch_reject_requires_reason_server_side():
    src = inspect.getsource(admin.batch_moderation)

    assert 'body.action == "reject"' in src
    assert "body.reason.strip()" in src
    assert "reason is required when rejecting posts" in src
