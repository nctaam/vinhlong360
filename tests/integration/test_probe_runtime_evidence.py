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
