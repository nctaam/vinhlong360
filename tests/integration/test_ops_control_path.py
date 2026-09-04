from __future__ import annotations

from pathlib import Path
import asyncio
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))


def test_monitoring_targets_are_declared_in_production_compose() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    monitoring = (ROOT / "scripts" / "monitoring" / "prometheus.yml").read_text(encoding="utf-8")
    assert "backup-status" in monitoring
    assert "node-exporter" in services
    assert "alertmanager" in services


def test_workflow_backup_and_health_gates_are_blocking() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "continue-on-error: true" not in workflow
    assert "backup" in workflow.lower()
    assert "health" in workflow.lower()


def test_rehearsal_requires_immutable_archive_and_staging_authority() -> None:
    script = (ROOT / "scripts" / "ops" / "rehearse_launch_rollback.sh").read_text(encoding="utf-8")
    assert "IMMUTABLE_ARCHIVE_ID" in script
    assert "staging" in script.lower()
    assert "production" in script.lower()
    assert "MIGRATION" in script


def test_notifier_contract_is_explicit() -> None:
    alertmanager = (ROOT / "scripts" / "monitoring" / "alertmanager.yml").read_text(encoding="utf-8")
    assert "vinhlong360-notifier" in alertmanager
    assert "VL360_ALERT_WEBHOOK_URL" in alertmanager


def test_backup_exporter_is_compose_wired_and_exposes_state_metrics() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    exporter = compose["services"]["backup-status-exporter"]
    assert exporter["expose"] == ["9105"]
    source = (ROOT / "scripts" / "monitoring" / "backup_status_exporter.py").read_text(encoding="utf-8")
    assert "vl360_backup_last_success_timestamp_seconds" in source
    assert "vl360_backup_last_failure_timestamp_seconds" in source
    assert "vl360_backup_stale" in source


def test_backup_status_marks_malformed_latest_as_stale(monkeypatch, tmp_path: Path) -> None:
    from siteops import admin_api

    backup_root = tmp_path / "scratch" / "backups"
    broken = backup_root / "20260902-120000"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(admin_api, "ROOT", tmp_path)
    status = admin_api._latest_backup_info()
    assert status["state"] == "failure"
    assert status["stale"] is True


def test_trigger_backup_failure_does_not_persist_cooldown(monkeypatch) -> None:
    from siteops import admin_api

    monkeypatch.setattr(admin_api, "_last_backup_time", 0)
    monkeypatch.setattr(admin_api.subprocess, "run", lambda *args, **kwargs: type("R", (), {"returncode": 1, "stderr": "failed", "stdout": ""})())
    with __import__("pytest").raises(Exception):
        asyncio.run(admin_api.trigger_backup())
    assert admin_api._last_backup_time == 0


def test_backup_missing_status_helper_has_stable_contract() -> None:
    """The extracted missing-backup branch keeps the endpoint's exact shape."""
    from siteops import admin_api

    assert admin_api._backup_missing_info() == {
        "ready": False,
        "latest": None,
        "count": 0,
        "size_mb": 0,
        "state": "missing",
        "last_success": None,
        "last_failure": None,
        "artifact_id": None,
        "stale": True,
    }


def test_backup_request_context_helper_preserves_legacy_defaults() -> None:
    """No request remains an anonymous admin operation without an idempotency key."""
    from siteops import admin_api

    assert admin_api._backup_request_context(None) == (None, "admin")
    assert admin_api._backup_request_hash("admin", "request-1") == admin_api._backup_request_hash(
        "admin", "request-1"
    )


class _HealthConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _HealthDatabase:
    _use_pg = True

    def __init__(self, *, fail_active_sessions=False, fail_size=False, fail_connection=False):
        self.queries = []
        self.fail_active_sessions = fail_active_sessions
        self.fail_size = fail_size
        self.fail_connection = fail_connection

    def _conn(self):
        if self.fail_connection:
            raise RuntimeError("database connection unavailable")
        return _HealthConnection()

    def _fetchone(self, _conn, sql, _params):
        self.queries.append(sql)
        if self.fail_size and "pg_database_size" in sql:
            raise RuntimeError("database size unavailable")
        if self.fail_active_sessions and "FROM user_sessions WHERE expires_at" in sql:
            raise RuntimeError("session metric unavailable")
        if "pg_database_size" in sql:
            return {"s": 1024 * 1024}
        if "FROM user_sessions WHERE expires_at" in sql:
            return {"c": 3}
        if "FROM posts WHERE moderation_status" in sql:
            return {"c": 2}
        if "FROM reports WHERE status" in sql:
            return {"c": 1}
        return {"c": 0}

    @staticmethod
    def _row_to_dict(row):
        return row


def test_system_health_uses_authority_session_table(monkeypatch) -> None:
    from siteops import admin_api

    fake_db = _HealthDatabase()
    monkeypatch.setattr(admin_api, "db", fake_db)
    result = {"postgres": {}}

    admin_api._system_health_pg(result)

    assert result["postgres"]["active_sessions"] == 3
    assert result["postgres"]["tables"]["sessions"] == 0
    assert any("FROM user_sessions WHERE expires_at" in sql for sql in fake_db.queries)
    assert not any("FROM sessions WHERE expires_at" in sql for sql in fake_db.queries)


def test_system_health_isolates_metric_failure(monkeypatch) -> None:
    from siteops import admin_api

    fake_db = _HealthDatabase(fail_active_sessions=True)
    monkeypatch.setattr(admin_api, "db", fake_db)
    result = {"postgres": {}}

    admin_api._system_health_pg(result)

    assert result["postgres"]["active_sessions"] == -1
    assert "active_sessions" in result["postgres"]["degraded_checks"]
    assert result["postgres"]["pending_moderation"] == 2
    assert result["postgres"]["open_reports"] == 1


def test_system_health_names_size_degradation(monkeypatch) -> None:
    from siteops import admin_api

    fake_db = _HealthDatabase(fail_size=True)
    monkeypatch.setattr(admin_api, "db", fake_db)
    result = {"postgres": {}}

    admin_api._system_health_pg(result)

    assert result["postgres"]["size_mb"] == -1
    assert "database_size" in result["postgres"]["degraded_checks"]


def test_system_health_connection_failure_is_degraded(monkeypatch) -> None:
    from siteops import admin_api

    fake_db = _HealthDatabase(fail_connection=True)
    monkeypatch.setattr(admin_api, "db", fake_db)
    result = {"postgres": {}}

    admin_api._system_health_pg(result)

    postgres = result["postgres"]
    assert postgres["tables"] == {}
    assert postgres["size_mb"] == -1
    assert postgres["active_sessions"] == -1
    assert postgres["pending_moderation"] == -1
    assert postgres["open_reports"] == -1
    assert postgres["degraded_checks"] == ["connection"]


def test_system_health_connection_degraded_shape_is_stable() -> None:
    from siteops import admin_api

    result = {"postgres": {"stale": "value"}}

    admin_api._system_health_pg_connection_degraded(result)

    assert result["postgres"] == {
        "tables": {},
        "size_mb": -1,
        "active_sessions": -1,
        "pending_moderation": -1,
        "open_reports": -1,
        "degraded_checks": ["connection"],
    }


def test_homepage_rebuild_is_single_flight(monkeypatch) -> None:
    import public_api

    builds = 0
    release = asyncio.Event()

    async def _build(_month):
        nonlocal builds
        builds += 1
        await release.wait()
        return {"build": builds}

    async def _run():
        first = asyncio.create_task(public_api.homepage_curated(__import__("fastapi").Response()))
        await asyncio.sleep(0)
        second = asyncio.create_task(public_api.homepage_curated(__import__("fastapi").Response()))
        await asyncio.sleep(0)
        assert builds == 1
        release.set()
        return await asyncio.gather(first, second)

    monkeypatch.setattr(public_api, "_today_vietnam", lambda: __import__("datetime").datetime(2026, 9, 4))
    monkeypatch.setattr(public_api, "_build_homepage_payload", _build)
    monkeypatch.setattr(public_api, "_homepage_cache", {"month": None, "data": None, "ts": 0})
    monkeypatch.setattr(public_api, "_homepage_lock", asyncio.Lock())
    monkeypatch.setattr(public_api, "_homepage_rebuilding", False)

    results = asyncio.run(_run())

    assert results == [{"build": 1}, {"build": 1}]
