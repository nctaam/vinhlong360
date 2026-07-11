from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_migration_gate_static_contracts_pass_current_repo():
    gate = load_script("check_migration_gate")

    issues, stats = gate.validate_static(ROOT / "agent" / "migrations")
    errors = [issue for issue in issues if issue.severity == "error"]

    assert errors == []
    assert stats["latest"] == "070_fix_trigger_correctness.sql"
    assert stats["latest_schema_version"] == 70

def test_shared_rate_limit_and_idempotency_contracts_exist():
    migration = (ROOT / "agent" / "migrations" / "056_shared_rate_idempotency.sql").read_text(encoding="utf-8")
    ratelimit = (ROOT / "agent" / "ratelimit.py").read_text(encoding="utf-8")
    auth_middleware = (ROOT / "agent" / "auth_middleware.py").read_text(encoding="utf-8")
    auth = (ROOT / "agent" / "auth.py").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS shared_rate_limits" in migration
    assert "CREATE TABLE IF NOT EXISTS request_idempotency_keys" in migration
    assert "VL360_SHARED_RATE_LIMIT" in ratelimit
    assert "pg_advisory_xact_lock" in ratelimit
    assert "VL360_SHARED_IDEMPOTENCY" in auth_middleware
    assert "request_idempotency_keys" in auth_middleware
    assert "_check_shared_auth_rate" in auth
    for key in (
        "otp_phone:",
        "otp_ip:",
        "otp_verify_ip:",
        "otp_verify_phone:",
        "check_phone_ip:",
        "login_ip:",
        "login_phone_fail:",
    ):
        assert key in auth

def test_http_only_cookie_auth_migration_contracts():
    auth = (ROOT / "agent" / "auth.py").read_text(encoding="utf-8")
    auth_middleware = (ROOT / "agent" / "auth_middleware.py").read_text(encoding="utf-8")
    frontend_auth = (ROOT / "web-nuxt" / "composables" / "useAuth.ts").read_text(encoding="utf-8")
    auth_plugin = (ROOT / "web-nuxt" / "plugins" / "auth.ts").read_text(encoding="utf-8")
    admin_middleware = (ROOT / "web-nuxt" / "middleware" / "admin.ts").read_text(encoding="utf-8")

    assert "SESSION_COOKIE_NAME = \"vl360_token\"" in auth
    assert "def _set_session_cookie" in auth
    assert "def _clear_session_cookie" in auth
    assert "response.set_cookie" in auth
    assert "x-forwarded-host" in auth
    assert "host == \"vinhlong360.vn\"" in auth
    assert "VL360_FORCE_SECURE_COOKIES" in auth
    assert "not is_production" in auth
    assert "{\"production\", \"prod\", \"prd\"}" in auth
    assert "httponly" in auth_middleware
    assert ".vinhlong360.vn" in auth_middleware
    assert "production\", \"prod\", \"prd\"" in auth_middleware
    # verify_otp / login_password establish the session cookie via the shared
    # _finish_login helper (Wave 4 2FA refactor); refresh_token sets it directly.
    # Accept either form, then assert _finish_login itself sets the cookie so the
    # indirection stays an honest cookie-setting path (contract preserved, not weakened).
    for fn in ("verify_otp", "login_password", "refresh_token"):
        block = auth[auth.index(f"async def {fn}") : auth.index("async def", auth.index(f"async def {fn}") + 10)]
        assert "_set_session_cookie" in block or "_finish_login" in block
    _fl = auth.index("def _finish_login")
    _fl_end = min((x for x in (auth.find("\nasync def", _fl + 10), auth.find("\ndef ", _fl + 10)) if x > 0), default=len(auth))
    assert "_set_session_cookie" in auth[_fl:_fl_end]
    for fn in ("reset_password_otp", "logout", "deactivate_account", "delete_account"):
        block = auth[auth.index(f"async def {fn}") : auth.index("async def", auth.index(f"async def {fn}") + 10)]
        assert "_clear_session_cookie" in block

    assert "credentials: 'include'" in frontend_auth
    assert "useRequestHeaders(['cookie']).cookie" in frontend_auth
    assert "token.value = res.token" not in frontend_auth
    assert "if (!token.value)" not in frontend_auth[frontend_auth.index("async function fetchMe") : frontend_auth.index("async function requestOtp")]
    assert "token.value && !user.value" not in auth_plugin
    assert "token.value" not in admin_middleware

def test_admin_cookie_auth_requires_csrf_for_mutations():
    admin = (ROOT / "agent" / "admin.py").read_text(encoding="utf-8")
    server = (ROOT / "agent" / "server.py").read_text(encoding="utf-8")
    notifications = (ROOT / "agent" / "notifications.py").read_text(encoding="utf-8")

    require_admin_block = admin[admin.index("async def require_admin") : admin.index("async def require_admin_scope")]
    # Refactor (complexity ≤12): require_csrf + audit side-effects dời sang
    # _require_admin_mutation_side_effects, require_admin GỌI nó (move-not-delete —
    # CSRF-cho-mutation vẫn bắt buộc). Giữ nguyên cả 2 assertion bảo mật.
    assert "_require_admin_mutation_side_effects(request" in require_admin_block  # wiring
    _se_idx = admin.index("def _require_admin_mutation_side_effects")
    side_effects_block = admin[_se_idx : _se_idx + 1600]
    assert "await require_csrf(request)" in side_effects_block
    assert "actor = \"admin-key\"" in require_admin_block
    for prefix in (
        "/api/notifications",
        "/api/me",
        "/api/saved",
        "/api/my-plans",
        "/api/following",
        "/api/blocked-users",
        "/api/notification-preferences",
    ):
        assert prefix in server
    stream_start = notifications.index("async def notification_stream")
    stream_block = notifications[stream_start : notifications.index('@router.post("/follow', stream_start)]
    assert "_extract_token(request)" in stream_block
    assert "not in {\"production\", \"prod\", \"prd\"}" in stream_block


def test_quality_budget_blocks_regressions(tmp_path: Path):
    budget = load_script("quality_budget")
    data = {
        "entities": [
            {
                "id": "a",
                "type": "attraction",
                "name": "A",
                "summary": "A useful summary that is long enough for validation.",
                "area": "vinh-long",
                "placeId": "p1",
                "coordinates": [10.25, 106.0],
                "source": [{"url": "https://vinhlong360.vn/self"}],
                "images": ["https://example.com/a.webp"],
                "attributes": {"admission": "free"},
            }
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")

    results, stats, _issues = budget.evaluate(
        data,
        data_path,
        max_budget={"self_citation_pct": 0},
        min_budget={"quality_score_avg": 90},
    )

    failed = {result.key for result in results if not result.ok}
    assert "self_citation_pct" in failed
    assert stats["self_citation_pct"] == 100.0


def test_quality_budget_tracks_media_trust_contracts():
    budget = load_script("quality_budget")
    src = (ROOT / "scripts" / "quality_budget.py").read_text(encoding="utf-8")

    assert "image_missing_credit" in budget.DEFAULT_MAX
    assert "image_missing_license" in budget.DEFAULT_MAX
    assert "image_missing_source" in budget.DEFAULT_MAX
    assert "image_missing_license" in src

def test_quality_budget_records_db_snapshots_contracts():
    src = (ROOT / "scripts" / "quality_budget.py").read_text(encoding="utf-8")

    assert "def record_db_snapshots" in src
    assert "quality_metric_snapshots" in src
    assert "--record-db" in src
    assert "psycopg2.connect" in src
    assert "metadata" in src

def test_restore_drill_contracts_exist():
    src = (ROOT / "scripts" / "restore_drill.py").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "deployment-guide.md").read_text(encoding="utf-8")

    assert "pg_restore" in src
    assert "CREATE DATABASE" in src
    assert "DROP DATABASE IF EXISTS" in src
    assert "runuser" in src
    assert "createdb" in src
    assert "dropdb" in src
    assert "check_migration_gate.py" in src
    assert "--keep-db" in src
    assert "restore_drill.py --backup-dir backups" in docs

def test_perf_quality_trend_migration_contracts_exist():
    migration = (ROOT / "agent" / "migrations" / "057_perf_quality_trends.sql").read_text(encoding="utf-8")
    init_sql = (ROOT / "init.sql").read_text(encoding="utf-8")
    database = (ROOT / "agent" / "database.py").read_text(encoding="utf-8")

    for token in (
        "ALTER TABLE entities ADD COLUMN IF NOT EXISTS status",
        "ALTER TABLE entities ADD COLUMN IF NOT EXISTS verified",
        "idx_entities_public_type_area_updated",
        "idx_entities_public_coordinates",
        "idx_posts_review_entity_recent_public",
        "quality_metric_snapshots",
        "VALUES ('agent', 57, '057_perf_quality_trends.sql'",
    ):
        assert token in migration
    assert "quality_metric_snapshots" in init_sql
    assert "PG_REQUIRED_SCHEMA_VERSION = 70" in database

def test_itinerary_areas_schema_migration_contracts_exist():
    migration = (ROOT / "agent" / "migrations" / "058_itinerary_areas_schema.sql").read_text(encoding="utf-8")
    gate = (ROOT / "scripts" / "check_migration_gate.py").read_text(encoding="utf-8")

    assert "ALTER TABLE itineraries" in migration
    assert "ADD COLUMN IF NOT EXISTS areas" in migration
    assert "to_jsonb(ARRAY[area])" in migration
    assert "VALUES ('agent', 58, '058_itinerary_areas_schema.sql'" in migration
    assert "itineraries_areas_column" in gate


def test_release_gate_runs_migration_and_quality_budgets():
    gate = (ROOT / "scripts" / "release_gate.ps1").read_text(encoding="utf-8")
    deploy = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert "check_migration_gate.py" in gate
    assert "scripts/apply_migrations.py" in gate
    assert "--db-check" in gate
    assert "quality_budget.py" in gate
    assert "scripts/apply_migrations.py" in deploy
    assert "apply_migrations.py --database-url" in deploy
    assert "scripts/validate_data.py" in deploy
    assert "scripts/restore_drill.py" in deploy
    assert "quality_budget.py --data web/data.json --record-db" in deploy
    assert "for mf in agent/migrations/053_saved_kind_superadmin.sql" not in deploy

def test_apply_migrations_runner_uses_legacy_baseline_and_latest_plan():
    runner = load_script("apply_migrations")

    migrations = runner.migration_files(ROOT / "agent" / "migrations")
    pending_after_legacy_baseline = [m.path.name for m in migrations if m.version > runner.LEGACY_BASELINE_VERSION]

    assert runner.LEGACY_BASELINE_VERSION == 52
    assert migrations[-1].path.name == "070_fix_trigger_correctness.sql"
    assert pending_after_legacy_baseline == [
        "053_saved_kind_superadmin.sql",
        "054_admin_audit_events.sql",
        "055_homepage_hero_refresh.sql",
        "056_shared_rate_idempotency.sql",
        "057_perf_quality_trends.sql",
        "058_itinerary_areas_schema.sql",
        "059_repair_migration_chain.sql",
        "060_entity_universal_columns.sql",
        "061_entity_detail_tables.sql",
        "062_experience_admission.sql",
        "063_profile_views.sql",
        "064_login_streak.sql",
        "065_achievements.sql",
        "066_two_factor_auth.sql",
        "067_trusted_devices.sql",
        "068_comments_deleted_at.sql",
        "069_recreate_social_indexes.sql",
        "070_fix_trigger_correctness.sql",
    ]

def test_chrome_smoke_redacts_sensitive_urls():
    smoke = (ROOT / "scripts" / "smoke_e2e_chrome.mjs").read_text(encoding="utf-8")

    assert "function redactSensitiveUrl" in smoke
    assert "function isSameOriginNuxtAsset" in smoke
    assert "function probeSameOriginAsset" in smoke
    assert "vl360_token" in smoke
    assert "Bearer [redacted]" in smoke
    assert "net::ERR_FAILED" in smoke
    assert "redactSensitiveUrl(params.response.url)" in smoke
