from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.checks.build_media_truth_review import (
    ReviewError,
    build_review_package,
    render_non_authorizing_apply_command,
    render_recovery_command,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "outputs/media-truth-plan-2026-09-25.json"
CANDIDATE = ROOT / ".tmp/media-truth-stage-test-4/candidate"
INVENTORY = ROOT / "outputs/media-truth-inventory-2026-09-25.json"
ARTIFACT = ROOT / ".tmp/media-truth-artifacts/first/manifest.json"
BACKUP = ROOT / ".tmp/media-truth-backups-phase-1/20260929-054438-before-media-truth-review"


def _evidence(path: Path, *, findings: list[dict] | None = None) -> Path:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "commands": [{"command": "python -m pytest -q", "exitCode": 0, "resultClassification": "pass", "outputSha256": "a" * 64}],
                "knownBaseline": [],
                "openFindings": findings or [],
                "generatedArtifacts": {"plan": True, "candidate": True, "inventory": True, "artifacts": True},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def test_command_renderers_are_explicitly_non_authorizing() -> None:
    apply = render_non_authorizing_apply_command(
        Path(".tmp/media-truth-approved/media-truth-plan-approved.json"),
        sqlite_path=Path("agent/data/vinhlong360.db"),
        json_path=Path("web/data.json"),
        sqlite_backup=Path("backup/vinhlong360.db"),
        json_backup=Path("backup/data.json"),
        plan_sha256="a" * 64,
        lock_path=Path(".tmp/reconciliation.lock"),
        journal_path=Path(".tmp/journal.json"),
    )
    recovery = render_recovery_command(Path(".tmp/journal.json"), sqlite_backup=Path("backup/vinhlong360.db"), json_backup=Path("backup/data.json"))
    for command in (apply, recovery):
        assert "mutationAllowed=false" in command
        assert "doNotExecute=true" in command
        assert "owner_approval_required" in command
    assert "--maintenance-window" in apply
    assert "--confirm-phase-b" in apply
    assert "--allow-live-protected-inputs" in apply
    assert "--plan-sha256 " + "a" * 64 in apply
    assert "--recover-phase-b-journal" in recovery


def test_review_package_is_hash_bound_and_non_authorizing(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    approved = tmp_path / "approved-plan.json"
    shutil.copyfile(PLAN, approved)
    evidence = _evidence(tmp_path / "test-evidence.json")
    package = build_review_package(
        ROOT,
        plan_path=PLAN,
        approved_plan_path=approved,
        stage_result_path=CANDIDATE / "stage-result.json",
        inventory_path=INVENTORY,
        artifact_manifest_path=ARTIFACT,
        backup_dir=BACKUP,
        test_evidence_path=evidence,
    )
    assert package["mutationAllowed"] is False
    assert package["status"] == "ready_for_owner_review"
    assert package["scope"]["counts"] == {"batch21Records": 40, "deletedEntities": 1, "retainedPlaceholders": 37, "retainedAi": 2, "jsonRelationshipsDeleted": 6, "sqliteRelationshipsDeleted": 0}
    assert package["applyProcedure"]["doNotExecute"] is True
    assert package["recoveryProcedure"]["authorization"] == "owner_approval_required"
    assert package["openFindings"] == []


def test_open_important_findings_are_rejected(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    approved = tmp_path / "approved-plan.json"
    shutil.copyfile(PLAN, approved)
    evidence = _evidence(
        tmp_path / "test-evidence.json",
        findings=[{"id": "F-1", "severity": "Important", "status": "open"}],
    )
    with pytest.raises(ReviewError, match="Critical/Important"):
        build_review_package(
            ROOT,
            plan_path=PLAN,
            approved_plan_path=approved,
            stage_result_path=CANDIDATE / "stage-result.json",
            inventory_path=INVENTORY,
            artifact_manifest_path=ARTIFACT,
            backup_dir=BACKUP,
            test_evidence_path=evidence,
        )


def test_plan_and_candidate_drift_are_rejected(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    approved = tmp_path / "approved-plan.json"
    altered = json.loads(PLAN.read_text(encoding="utf-8"))
    altered["status"] = "approved"
    approved.write_text(json.dumps(altered, sort_keys=True), encoding="utf-8")
    evidence = _evidence(tmp_path / "test-evidence.json")
    with pytest.raises(ReviewError, match="approved plan bytes"):
        build_review_package(
            ROOT,
            plan_path=PLAN,
            approved_plan_path=approved,
            stage_result_path=CANDIDATE / "stage-result.json",
            inventory_path=INVENTORY,
            artifact_manifest_path=ARTIFACT,
            backup_dir=BACKUP,
            test_evidence_path=evidence,
        )

    stage = tmp_path / "stage-result.json"
    payload = json.loads((CANDIDATE / "stage-result.json").read_text(encoding="utf-8"))
    payload["mutationAllowed"] = True
    stage.write_text(json.dumps(payload), encoding="utf-8")
    shutil.copyfile(PLAN, approved)
    with pytest.raises(ReviewError, match="mutationAllowed=false"):
        build_review_package(
            ROOT,
            plan_path=PLAN,
            approved_plan_path=approved,
            stage_result_path=stage,
            inventory_path=INVENTORY,
            artifact_manifest_path=ARTIFACT,
            backup_dir=BACKUP,
            test_evidence_path=evidence,
        )


def test_renderer_rejects_non_digest() -> None:
    with pytest.raises(ReviewError, match="SHA-256"):
        render_non_authorizing_apply_command(
            Path("approved.json"),
            sqlite_path=Path("db"),
            json_path=Path("data"),
            sqlite_backup=Path("db.bak"),
            json_backup=Path("data.bak"),
            plan_sha256="not-a-digest",
            lock_path=Path("lock"),
            journal_path=Path("journal"),
        )
