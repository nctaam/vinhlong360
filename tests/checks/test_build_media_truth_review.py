from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from scripts.checks.apply_data_reconciliation import ApplyError, apply_plan
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
OWNER_REVIEW_MARKER = "owner-approved-2026-09-30-media-truth-phase-1-review-498ac0b8d5349f79"


def _canonical_digest(payload: dict) -> str:
    canonical = dict(payload)
    canonical.pop("planSha256", None)
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _approved_plan(path: Path, *, source: Path = PLAN, mutate=None) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["status"] = "approved"
    payload["reviewedPlanMarker"] = OWNER_REVIEW_MARKER
    if mutate is not None:
        mutate(payload)
    payload["planSha256"] = _canonical_digest(payload)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return path


def _apply_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, dict]:
    db = tmp_path / "fixture.db"
    payload = {
        "entities": [
            {"id": "a", "type": "place", "name": "A", "season": None, "attributes": {}, "source": None, "images": [], "coordinates": None},
            {"id": "b", "type": "place", "name": "B", "season": None, "attributes": {}, "source": None, "images": [], "coordinates": None},
        ],
        "relationships": [{"from": "a", "to": "b", "type": "near"}],
        "itineraries": [],
    }
    with sqlite3.connect(db) as connection:
        connection.executescript(
            "CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT, name TEXT, season TEXT, attributes TEXT, source TEXT, images TEXT, coordinates TEXT);"
            "CREATE TABLE relationships (from_id TEXT, to_id TEXT, type TEXT);"
            "CREATE TABLE itineraries (id TEXT);"
        )
        connection.execute("INSERT INTO entities VALUES ('a','place','A',NULL,'{}',NULL,'[]',NULL)")
        connection.execute("INSERT INTO entities VALUES ('b','place','B',NULL,'{}',NULL,'[]',NULL)")
        connection.execute("INSERT INTO relationships VALUES ('a','b','near')")
    data = tmp_path / "data.json"
    data.write_text(json.dumps(payload), encoding="utf-8")
    db_backup = tmp_path / "fixture.db.bak"
    db_backup.write_bytes(db.read_bytes())
    data_backup = tmp_path / "data.json.bak"
    data_backup.write_bytes(data.read_bytes())
    plan = {
        "schemaVersion": 1,
        "mode": "dry-run",
        "status": "review_required",
        "mutationAllowed": False,
        "inputs": {
            "sqlite": {"sha256": hashlib.sha256(db.read_bytes()).hexdigest()},
            "json": {"sha256": hashlib.sha256(data.read_bytes()).hexdigest()},
        },
        "mutations": [
            {"mutationId": "s1", "store": "sqlite", "recordType": "relationship", "recordId": "a->b", "operation": "update", "field": "type", "before": "near", "after": "related_to", "metadata": {"rowid": 1}},
            {"mutationId": "j1", "store": "json", "recordType": "relationship", "recordId": "a->b", "operation": "update", "field": "relationship", "before": payload["relationships"][0], "after": {"from": "a", "to": "b", "type": "related_to"}, "metadata": {"index": 0}},
        ],
        "deferred": [],
    }
    return db, data, db_backup, data_backup, plan


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


def test_apply_validation_rejects_review_file_digest_and_accepts_approved_digest(tmp_path: Path) -> None:
    db, data, db_backup, data_backup, source = _apply_fixture(tmp_path)
    review_bytes = (json.dumps(source, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    review_file_digest = hashlib.sha256(review_bytes).hexdigest()
    approved = dict(source)
    approved["status"] = "approved"
    approved["reviewedPlanMarker"] = OWNER_REVIEW_MARKER
    approved["planSha256"] = _canonical_digest(approved)

    with pytest.raises(ApplyError, match="plan hash"):
        apply_plan(
            approved,
            db,
            data,
            db_backup,
            data_backup,
            confirm=True,
            plan_sha256=review_file_digest,
        )

    result = apply_plan(
        approved,
        db,
        data,
        db_backup,
        data_backup,
        confirm=True,
        plan_sha256=approved["planSha256"],
    )
    assert result["status"] == "applied"


def test_review_package_is_hash_bound_and_non_authorizing(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    approved = _approved_plan(tmp_path / "approved-plan.json")
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
    assert package["plan"]["sha256"] == "aa5cbaec34c758e8b67f27ca943461c31d2d27bf661d4e8e013334892edcb37b"
    assert package["plan"]["approvedCanonicalSha256"] == "39d55df5e10897165dcdb2410def7ed1666b054d8e97e4818ea726bbb4b7a032"
    assert package["plan"]["approvedFileSha256"] == "524f0d18d48bebfc8cc768b60ecc5bfdeb7854cf8dc9ed04c3113c3ec0a106f6"
    assert package["plan"]["reviewedPlanMarker"] == OWNER_REVIEW_MARKER
    assert "--plan-sha256 39d55df5e10897165dcdb2410def7ed1666b054d8e97e4818ea726bbb4b7a032" in package["applyProcedure"]["command"]
    assert "--plan-sha256 aa5cbaec34c758e8b67f27ca943461c31d2d27bf661d4e8e013334892edcb37b" not in package["applyProcedure"]["command"]
    assert package["recoveryProcedure"]["authorization"] == "owner_approval_required"
    assert package["openFindings"] == []


def test_open_important_findings_are_rejected(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    approved = _approved_plan(tmp_path / "approved-plan.json")
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


def test_approved_plan_true_authorization_is_rejected(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    approved = _approved_plan(
        tmp_path / "approved-plan.json",
        mutate=lambda payload: payload.update({"authorization": True}),
    )
    evidence = _evidence(tmp_path / "test-evidence.json")
    with pytest.raises(ReviewError, match="authorization marker"):
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


def test_approved_plan_mutation_drift_and_candidate_authorization_are_rejected(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    approved = _approved_plan(
        tmp_path / "approved-plan.json",
        mutate=lambda payload: payload["mutations"][0].update({"recordId": "approval-copy-drift"}),
    )
    evidence = _evidence(tmp_path / "test-evidence.json")
    with pytest.raises(ReviewError, match="approval plan drift"):
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
    _approved_plan(approved)
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


def test_plan_target_id_drift_is_rejected(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    altered = json.loads(PLAN.read_text(encoding="utf-8"))
    altered["planSha256"] = None
    next(item for item in altered["mutations"] if item["recordType"] == "entity")["recordId"] = "drift-id"
    plan = tmp_path / "plan-target-drift.json"
    approved = tmp_path / "approved-target-drift.json"
    payload = json.dumps(altered, ensure_ascii=False, sort_keys=True)
    plan.write_text(payload, encoding="utf-8")
    _approved_plan(approved, source=plan)
    evidence = _evidence(tmp_path / "test-evidence.json")
    with pytest.raises(ReviewError, match="target ID set"):
        build_review_package(
            ROOT,
            plan_path=plan,
            approved_plan_path=approved,
            stage_result_path=CANDIDATE / "stage-result.json",
            inventory_path=INVENTORY,
            artifact_manifest_path=ARTIFACT,
            backup_dir=BACKUP,
            test_evidence_path=evidence,
        )


def test_plan_mutation_count_drift_is_rejected(tmp_path: Path) -> None:
    if not all(path.exists() for path in (PLAN, CANDIDATE, INVENTORY, ARTIFACT, BACKUP)):
        pytest.skip("review evidence fixtures are not available")
    altered = json.loads(PLAN.read_text(encoding="utf-8"))
    altered["planSha256"] = None
    next(item for item in altered["mutations"] if item["recordType"] == "entity" and item["operation"] == "remove")["operation"] = "update"
    plan = tmp_path / "plan-count-drift.json"
    approved = tmp_path / "approved-count-drift.json"
    payload = json.dumps(altered, ensure_ascii=False, sort_keys=True)
    plan.write_text(payload, encoding="utf-8")
    _approved_plan(approved, source=plan)
    evidence = _evidence(tmp_path / "test-evidence.json")
    with pytest.raises(ReviewError, match="mutation-count map"):
        build_review_package(
            ROOT,
            plan_path=plan,
            approved_plan_path=approved,
            stage_result_path=CANDIDATE / "stage-result.json",
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
