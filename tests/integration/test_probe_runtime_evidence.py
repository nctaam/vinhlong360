from __future__ import annotations

import json

import scripts.ops.probe_runtime_evidence as probe_module
from scripts.ops.probe_runtime_evidence import AVAILABLE, EXECUTED, UNAVAILABLE, probe

SEVEN_PROOFS = {
    "browser-proxy-e2e",
    "multi-process-contention",
    "ha-failover",
    "backup-offsite-restore-checksum",
    "staging-rollout-smoke-rollback",
    "monitoring-alert-receiver",
    "provider-sandbox-retry",
}


def test_every_operational_proof_is_accounted_for():
    """No operational proof may quietly drop out of the inventory."""

    report = probe()
    assert {item["id"] for item in report["checks"]} == SEVEN_PROOFS


def test_the_probe_never_claims_a_drill_was_executed():
    """Measuring that a drill could run must not be recorded as having run it."""

    report = probe()
    assert report["executed_count"] == 0
    assert all(item["status"] in {AVAILABLE, UNAVAILABLE} for item in report["checks"])


def test_the_launch_verdict_stays_no_go_whatever_the_host_offers(monkeypatch):
    """A well-equipped host still cannot raise the verdict by being well equipped."""

    monkeypatch.setattr(probe_module, "_docker_running", lambda: True)
    monkeypatch.setattr(probe_module, "_loopback_port_open", lambda _port: True)
    monkeypatch.setattr(probe_module, "_tool", lambda _name: True)
    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)
    monkeypatch.setenv("VL360_SECOND_NODE_HOST", "node-2.example.internal")

    report = probe()
    assert report["launch_verdict"] == "NO_GO"
    assert report["executed_count"] == 0


def test_ha_failover_is_unavailable_without_a_second_host(monkeypatch):
    """HA cannot be proved on one machine, however capable that machine is."""

    monkeypatch.delenv("VL360_SECOND_NODE_HOST", raising=False)
    report = probe()
    entry = next(item for item in report["checks"] if item["id"] == "ha-failover")

    assert entry["status"] == UNAVAILABLE
    assert "second host" in entry["missing"]


def test_the_report_is_json_serialisable_and_stable():
    """The artifact must round-trip so it can be diffed between runs."""

    first = probe()
    serialised = json.dumps(first, ensure_ascii=True, sort_keys=True)
    assert json.loads(serialised)["checks"]

    second = probe()
    assert [item["id"] for item in first["checks"]] == [item["id"] for item in second["checks"]]


def test_the_executed_status_exists_but_is_never_self_assigned():
    """EXECUTED is reserved for a real receipt, which this probe cannot mint."""

    assert EXECUTED == "EXECUTED"
    assert all(item["status"] != EXECUTED for item in probe()["checks"])


def test_probe_uses_the_supplied_root_for_repository_prerequisites(tmp_path, monkeypatch):
    """A probe of another checkout must inspect that checkout, not this module's root."""

    monkeypatch.setattr(probe_module, "_tool", lambda name: name == "node")
    monkeypatch.setattr(probe_module, "_docker_running", lambda: False)
    monkeypatch.setattr(probe_module, "_loopback_port_open", lambda _port: False)

    report = probe(tmp_path)
    browser = next(item for item in report["checks"] if item["id"] == "browser-proxy-e2e")

    assert browser["status"] == UNAVAILABLE
    assert "scripts/launch_safety_browser_e2e.mjs" in browser["missing"]


def test_ha_never_becomes_available_from_a_host_name_alone(monkeypatch):
    """A configured second host is not evidence of replica, promotion, or rerouting."""

    monkeypatch.setenv("VL360_SECOND_NODE_HOST", "node-2.example.internal")

    report = probe()
    ha = next(item for item in report["checks"] if item["id"] == "ha-failover")

    assert ha["status"] == UNAVAILABLE
    assert {"PostgreSQL replica", "failover promoter", "proxy or VIP that reroutes"}.issubset(ha["missing"])


def test_combined_browser_proxy_proof_is_unavailable_without_proxy_base_url(monkeypatch):
    """Browser-only readiness must not masquerade as browser-through-nginx proof."""

    monkeypatch.setattr(probe_module, "_tool", lambda name: name == "node")
    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)

    report = probe()
    browser = next(item for item in report["checks"] if item["id"] == "browser-proxy-e2e")

    assert browser["status"] == UNAVAILABLE
    assert any("base" in item.lower() or "nginx" in item.lower() for item in browser["missing"])


def test_combined_backup_proof_is_unavailable_without_restore_and_offsite_prerequisites(monkeypatch):
    """A local backup script is not the complete backup/offsite/restore proof."""

    monkeypatch.setattr(probe_module, "_tool", lambda _name: False)
    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)

    report = probe()
    backup = next(item for item in report["checks"] if item["id"] == "backup-offsite-restore-checksum")

    assert backup["status"] == UNAVAILABLE
    assert "an offsite destination" in backup["missing"]


def test_backup_probe_does_not_promote_configuration_to_execution_readiness(monkeypatch):
    """Credentials and binaries alone cannot prove the composite drill is runnable."""

    monkeypatch.setattr(probe_module, "_tool", lambda _name: True)
    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)
    monkeypatch.setattr(probe_module, "_docker_running", lambda: True)
    for name, value in {
        "S3_ENDPOINT": "https://example.invalid",
        "S3_ACCESS_KEY": "placeholder-access",
        "S3_SECRET_KEY": "placeholder-secret",
        "S3_BUCKET": "placeholder-bucket",
    }.items():
        monkeypatch.setenv(name, value)

    report = probe()
    backup = next(item for item in report["checks"] if item["id"] == "backup-offsite-restore-checksum")

    assert backup["status"] == UNAVAILABLE
    assert "backup/offsite/restore execution receipt" in backup["missing"]
    assert "backup_data.py --target local" not in backup["command"]


def test_monitoring_delivery_proof_is_unavailable_without_alert_receiver(monkeypatch):
    """A running monitoring stack does not prove delivery to an external sink."""

    monkeypatch.setattr(probe_module, "_docker_running", lambda: True)

    report = probe()
    monitoring = next(item for item in report["checks"] if item["id"] == "monitoring-alert-receiver")

    assert monitoring["status"] == UNAVAILABLE
    assert "an alert receiver endpoint" in monitoring["missing"]


def test_monitoring_probe_uses_runtime_webhook_and_requires_delivery_receipt(monkeypatch):
    """An arbitrary receiver URL must not become monitoring delivery evidence."""

    monkeypatch.setattr(probe_module, "_docker_running", lambda: True)
    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)
    monkeypatch.setenv("VL360_ALERT_RECEIVER_URL", "https://wrong.example")
    monkeypatch.setenv("VL360_ALERT_WEBHOOK_URL", "https://placeholder.example")

    report = probe()
    monitoring = next(item for item in report["checks"] if item["id"] == "monitoring-alert-receiver")

    assert monitoring["status"] == UNAVAILABLE
    assert "alert delivery receipt" in monitoring["missing"]


def test_staging_combined_proof_is_unavailable_without_real_staging_host(monkeypatch):
    """A local rollback rehearsal is not a staging rollout receipt."""

    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)

    report = probe()
    staging = next(item for item in report["checks"] if item["id"] == "staging-rollout-smoke-rollback")

    assert staging["status"] == UNAVAILABLE
    assert "a staging environment" in staging["missing"]


def test_staging_probe_does_not_treat_host_strings_as_a_rollout_receipt(monkeypatch):
    """Host/environment strings cannot turn the local rehearsal command into staging proof."""

    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)
    monkeypatch.setenv("VL360_STAGING_HOST", "placeholder.example")
    monkeypatch.setenv("VL360_STAGING_ENVIRONMENT", "staging")
    monkeypatch.setenv("DEPLOY_ENVIRONMENT", "staging")

    report = probe()
    staging = next(item for item in report["checks"] if item["id"] == "staging-rollout-smoke-rollback")

    assert staging["status"] == UNAVAILABLE
    assert "staging rollout execution receipt" in staging["missing"]
    assert "--local-rehearsal" not in staging["command"]


def test_monitoring_probe_scopes_repository_files_to_supplied_root(monkeypatch, tmp_path):
    """An empty alternate checkout cannot inherit monitoring readiness from this checkout."""

    monkeypatch.setattr(probe_module, "_docker_running", lambda: True)
    monkeypatch.setattr(probe_module, "_file", lambda _relative: True)
    monkeypatch.setenv("VL360_ALERT_WEBHOOK_URL", "https://placeholder.example")

    report = probe(tmp_path)
    monitoring = next(item for item in report["checks"] if item["id"] == "monitoring-alert-receiver")

    assert monitoring["status"] == UNAVAILABLE
    assert "docker-compose.yml" in monitoring["missing"]
