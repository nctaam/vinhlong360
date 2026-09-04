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
