from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from agent.control_plane.evidence import verify_probe_receipt
from scripts.ops.probe_multiprocess_scheduler import main as scheduler_probe_main
from scripts.ops.probe_multiprocess_scheduler import _dsn as scheduler_probe_dsn
from scripts.ops.probe_provider_sandbox import run_deterministic_scenarios
from scripts.ops.probe_proxy_contract import validate_base_url
from scripts.ops.probe_rollback import run_local_rollback_rehearsal
from scripts.ops.restore_drill import main as restore_drill_main
from scripts.ops.restore_drill import validate_restore_inputs
from scripts.ops.run_pilot_acceptance import _required_probe_receipts_pass, AcceptanceBundle, load_probe_receipts


def _valid_receipt() -> dict[str, object]:
    started = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)
    finished = started + timedelta(seconds=3)
    output = '{"status":"pass"}\n'
    return {
        "probe_id": "provider-sandbox",
        "head_sha": "a" * 40,
        "environment_id": "local-disposable-sandbox",
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "command": "python scripts/ops/probe_provider_sandbox.py --mode deterministic",
        "exit_code": 0,
        "output_sha256": sha256(output.encode("utf-8")).hexdigest(),
        "captured_output": output,
        "test_nodeids": ["provider:accept", "provider:timeout", "provider:reject"],
        "verdict": "PASS",
    }


def test_valid_probe_receipt_is_passable():
    result = verify_probe_receipt(_valid_receipt())

    assert result.verdict == "PASS"
    assert result.reasons == ()


def test_staging_receipt_rejects_missing_environment_or_output_hash():
    receipt = {"probe_id": "scheduler", "head_sha": "a" * 40, "verdict": "PASS"}

    result = verify_probe_receipt(receipt)

    assert result.verdict == "BLOCKED"
    assert "missing or invalid field: environment_id" in result.reasons
    assert "missing or invalid field: output_sha256" in result.reasons


def test_pass_receipt_requires_zero_exit_and_executed_nodeids():
    receipt = _valid_receipt()
    receipt["exit_code"] = 1
    receipt["test_nodeids"] = []

    result = verify_probe_receipt(receipt)

    assert result.verdict == "BLOCKED"
    assert "PASS receipt must have exit_code 0" in result.reasons
    assert "PASS receipt must list executed test_nodeids" in result.reasons


def test_receipt_rejects_naive_or_reversed_timestamps():
    receipt = _valid_receipt()
    receipt["started_at"] = "2026-09-05T10:00:00"
    receipt["finished_at"] = "2026-09-05T09:59:00+00:00"

    result = verify_probe_receipt(receipt)

    assert result.verdict == "BLOCKED"
    assert "timestamps must be timezone-aware" in result.reasons


def test_receipt_binds_declared_output_hash_when_captured_output_is_present():
    receipt = _valid_receipt()
    receipt["captured_output"] = "tampered\n"

    result = verify_probe_receipt(receipt)

    assert result.verdict == "BLOCKED"
    assert "output_sha256 does not match captured_output" in result.reasons


def test_pass_receipt_without_transcript_is_blocked():
    receipt = _valid_receipt()
    receipt.pop("captured_output")

    result = verify_probe_receipt(receipt)

    assert result.verdict == "BLOCKED"
    assert "PASS receipt requires captured_output" in result.reasons


def test_unavailable_probe_is_not_a_pass():
    receipt = _valid_receipt()
    receipt["verdict"] = "UNAVAILABLE"
    receipt["exit_code"] = 2
    receipt["test_nodeids"] = []

    result = verify_probe_receipt(receipt)

    assert result.verdict == "UNAVAILABLE"
    assert result.reasons == ()


def test_unavailable_receipt_requires_nonzero_exit():
    receipt = _valid_receipt()
    receipt["verdict"] = "UNAVAILABLE"
    receipt["exit_code"] = 0
    receipt["test_nodeids"] = []

    result = verify_probe_receipt(receipt)

    assert result.verdict == "BLOCKED"
    assert "UNAVAILABLE receipt must have nonzero exit_code" in result.reasons


def test_blocked_receipt_requires_nonzero_exit():
    receipt = _valid_receipt()
    receipt["verdict"] = "BLOCKED"
    receipt["exit_code"] = 0
    receipt["test_nodeids"] = []

    result = verify_probe_receipt(receipt)

    assert result.verdict == "BLOCKED"
    assert "BLOCKED receipt must have nonzero exit_code" in result.reasons


def test_provider_sandbox_exercises_accept_timeout_and_reject_without_external_calls():
    result = run_deterministic_scenarios()

    assert result["status"] == "pass"
    assert result["external_calls"] == 0
    assert result["scenarios"]["accepted"]["state"] == "accepted"
    assert result["scenarios"]["timeout"]["state"] == "ambiguous"
    assert result["scenarios"]["timeout"]["calls"] == 1
    assert result["scenarios"]["rejected"]["state"] == "rejected"


def test_proxy_probe_allows_only_explicit_loopback_base_urls():
    assert validate_base_url("http://127.0.0.1:8360") == (True, "")
    assert validate_base_url("http://localhost:8080") == (True, "")
    assert validate_base_url("https://vinhlong360.vn") == (False, "non-loopback host")
    assert validate_base_url("") == (False, "base URL is required")


def test_scheduler_probe_writes_unavailable_receipt_without_a_disposable_dsn(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("VL360_TEST_DATABASE_URL", raising=False)
    receipt_path = tmp_path / "scheduler-receipt.json"

    assert scheduler_probe_main(["--receipt", str(receipt_path)]) == 2
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert verify_probe_receipt(payload).verdict == "UNAVAILABLE"
    assert json.loads(capsys.readouterr().out)["verdict"] == "UNAVAILABLE"


def test_restore_drill_rejects_missing_backup_and_non_disposable_target(tmp_path):
    ok, reasons = validate_restore_inputs(tmp_path / "missing.dump", "postgresql://db.example/app")

    assert ok is False
    assert "backup file does not exist" in reasons
    assert "target must be loopback PostgreSQL" in reasons


def test_postgres_probes_reject_hostaddr_override(tmp_path, monkeypatch):
    hostile = "postgresql://localhost/app?marker=disposable&hostaddr=203.0.113.9"
    monkeypatch.setenv("VL360_TEST_DATABASE_URL", hostile)

    with pytest.raises(RuntimeError, match="hostaddr"):
        scheduler_probe_dsn()
    ok, reasons = validate_restore_inputs(tmp_path / "missing.dump", hostile)
    assert ok is False
    assert "target must not override hostaddr" in reasons


def test_restore_drill_keeps_password_out_of_command_receipt(tmp_path, monkeypatch, capsys):
    backup = tmp_path / "backup.dump"
    backup.write_bytes(b"dump")
    monkeypatch.setenv(
        "VL360_RESTORE_DATABASE_URL",
        "postgresql://127.0.0.1:5432/app?marker=disposable",
    )
    monkeypatch.setenv("PGUSER", "restore-user")
    monkeypatch.setenv("PGPASSWORD", "super-secret")
    monkeypatch.setattr("scripts.ops.restore_drill.shutil.which", lambda _name: "pg_restore")

    class Completed:
        returncode = 1
        stdout = ""

    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):
        calls.append((list(command), kwargs))
        if command[:2] == ["git", "rev-parse"]:
            result = Completed()
            result.returncode = 0
            result.stdout = "a" * 40
            return result
        return Completed()

    monkeypatch.setattr("scripts.ops.restore_drill.subprocess.run", fake_run)

    assert restore_drill_main(["--backup", str(backup), "--execute", "--receipt", str(tmp_path / "receipt.json")]) == 1
    printed = capsys.readouterr().out
    assert "super-secret" not in printed
    assert "super-secret" not in (tmp_path / "receipt.json").read_text(encoding="utf-8")
    assert "super-secret" not in " ".join(calls[0][0])
    assert calls[0][1]["env"]["PGPASSWORD"] == "super-secret"


def test_acceptance_loads_probe_receipts_fail_closed(tmp_path):
    statuses = load_probe_receipts(tmp_path)

    assert statuses["multiprocess-scheduler"]["verdict"] == "UNAVAILABLE"
    assert statuses["provider-sandbox"]["verdict"] == "UNAVAILABLE"
    assert statuses["proxy-contract"]["verdict"] == "UNAVAILABLE"
    assert statuses["backup-restore-checksum"]["verdict"] == "UNAVAILABLE"


def test_acceptance_rejects_receipt_stored_under_the_wrong_probe_slot(tmp_path):
    payload = _valid_receipt()
    payload["probe_id"] = "proxy-contract"
    (tmp_path / "provider-sandbox-receipt.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    statuses = load_probe_receipts(tmp_path)

    assert statuses["provider-sandbox"]["verdict"] == "BLOCKED"
    assert "probe_id does not match expected slot" in statuses["provider-sandbox"]["reasons"]


def test_acceptance_binds_receipt_to_head_environment_and_command(tmp_path):
    payload = _valid_receipt()
    payload["head_sha"] = "b" * 40
    payload["environment_id"] = "staging-unapproved"
    payload["command"] = "python arbitrary.py"
    (tmp_path / "provider-sandbox-receipt.json").write_text(json.dumps(payload), encoding="utf-8")

    status = load_probe_receipts(tmp_path, expected_head_sha="a" * 40)["provider-sandbox"]

    assert status["verdict"] == "BLOCKED"
    assert "head_sha does not match checked-out HEAD" in status["reasons"]
    assert "environment_id does not match expected probe environment" in status["reasons"]
    assert "command does not match expected probe identity" in status["reasons"]


def test_acceptance_missing_probe_receipts_field_is_not_passable():
    assert _required_probe_receipts_pass(AcceptanceBundle(environment={})) is False


def test_acceptance_rejects_unverified_pass_statuses():
    statuses = {
        probe_id: {"verdict": "PASS", "reasons": []}
        for probe_id in (
            "multiprocess-scheduler", "provider-sandbox", "proxy-contract",
            "backup-restore-checksum",
        )
    }
    bundle = AcceptanceBundle(head_sha="a" * 40, environment={"probe_receipts": statuses})

    assert _required_probe_receipts_pass(bundle) is False


def test_local_rollback_rehearsal_proves_revert_without_claiming_staging(tmp_path):
    result = run_local_rollback_rehearsal(tmp_path)

    assert result["status"] == "pass"
    assert result["environment"] == "local-rehearsal"
    assert result["candidate_health"] == "failed"
    assert result["restored_release"] == "release-a"
    assert result["staging_claim"] is False
