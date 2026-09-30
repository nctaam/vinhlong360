from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

import scripts.checks.build_media_truth_review as review_module
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
BACKUP = ROOT / ".tmp/media-truth-backups-phase-1/20260930-143449-before-media-truth-apply-review-exact"
OLD_BACKUP = ROOT / ".tmp/media-truth-backups-phase-1/20260929-054438-before-media-truth-review"
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
                "commands": [{"command": "python -m pytest -q", "exitCode": 0, "resultClassification": "passed", "outputSha256": "a" * 64}],
                "knownBaseline": [],
                "openFindings": findings or [],
                "generatedArtifacts": {"plan": True, "candidate": True, "inventory": True, "artifacts": True},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _command_evidence(*, exit_code: int, classification: str, output_hash: str = "a" * 64) -> dict:
    return {
        "commands": [
            {
                "command": "python -m pytest -q",
                "exitCode": exit_code,
                "resultClassification": classification,
                "outputSha256": output_hash,
            }
        ]
    }


def test_evidence_commands_reject_nonzero_exit_with_positive_classification() -> None:
    with pytest.raises(ReviewError, match="test evidence commands are malformed"):
        review_module._validate_evidence_commands(
            _command_evidence(exit_code=1, classification="passed_copy_only_rehearsal")
        )


def test_evidence_commands_reject_unknown_classification() -> None:
    with pytest.raises(ReviewError, match="test evidence commands are malformed"):
        review_module._validate_evidence_commands(
            _command_evidence(exit_code=0, classification="passed_custom")
        )


@pytest.mark.parametrize("output_hash", ["A" * 64, "a" * 63, "g" * 64, "not-a-hash"])
def test_evidence_commands_reject_malformed_output_hash(output_hash: str) -> None:
    with pytest.raises(ReviewError, match="test evidence commands are malformed"):
        review_module._validate_evidence_commands(
            _command_evidence(exit_code=0, classification="passed", output_hash=output_hash)
        )


@pytest.mark.parametrize("classification", ["passed", "passed_baseline", "passed_copy_only_rehearsal"])
def test_evidence_commands_accept_documented_passing_classifications(classification: str) -> None:
    checks = review_module._validate_evidence_commands(
        _command_evidence(exit_code=0, classification=classification)
    )
    assert checks[0]["resultClassification"] == classification


def _review(tmp_path: Path, *, root: Path = ROOT, backup_dir: Path = BACKUP) -> dict:
    return build_review_package(
        root,
        plan_path=PLAN,
        approved_plan_path=_approved_plan(tmp_path / "approved-plan.json"),
        stage_result_path=CANDIDATE / "stage-result.json",
        inventory_path=INVENTORY,
        artifact_manifest_path=ARTIFACT,
        backup_dir=backup_dir,
        test_evidence_path=_evidence(tmp_path / "test-evidence.json"),
    )


def _copied_backup(tmp_path: Path) -> Path:
    backup = tmp_path / "backup"
    shutil.copytree(BACKUP, backup)
    return backup


def _copied_protected_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / "web").mkdir(parents=True)
    (root / "agent/data").mkdir(parents=True)
    shutil.copy2(ROOT / "web/data.json", root / "web/data.json")
    shutil.copy2(ROOT / "agent/data/vinhlong360.db", root / "agent/data/vinhlong360.db")
    return root


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
    assert package["backupProcedure"]["manifestSha256"] == "af7937bee236ec4338716080887c931dbef9a09a855438d6547b060439c6be86"
    assert package["backupProcedure"]["copiedFiles"]["json"] == {
        "path": ".tmp/media-truth-backups-phase-1/20260930-143449-before-media-truth-apply-review-exact/data.json",
        "sha256": "8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f",
        "byteEqualToProtected": True,
    }
    assert package["backupProcedure"]["copiedFiles"]["sqlite"]["sha256"] == "ea83864990cf8455061b2436f072c097bc7011f56428c5ba3ba43bcd66fb78a4"
    assert package["backupProcedure"]["copiedFiles"]["sqlite"]["byteEqualToProtected"] is True
    assert package["recoveryProcedure"]["authorization"] == "owner_approval_required"
    assert package["openFindings"] == []


@pytest.mark.parametrize("mode", [None, "logical-copy-v1"])
def test_review_rejects_backup_without_exact_sqlite_mode(tmp_path: Path, mode: str | None) -> None:
    backup = _copied_backup(tmp_path)
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mode is None:
        manifest.pop("sqlite_backup_mode")
    else:
        manifest["sqlite_backup_mode"] = mode
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReviewError, match="byte-exact-v1"):
        _review(tmp_path, backup_dir=backup)


@pytest.mark.parametrize("artifact", ["data.json", "vinhlong360.db"])
def test_review_rejects_declared_backup_artifact_hash_mismatch(tmp_path: Path, artifact: str) -> None:
    backup = _copied_backup(tmp_path)
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_hashes"][artifact] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReviewError, match="artifact hash mismatch"):
        _review(tmp_path, backup_dir=backup)


def test_review_rejects_logically_equal_byte_different_sqlite_backup(tmp_path: Path) -> None:
    if not OLD_BACKUP.exists():
        pytest.skip("old logical backup fixture is not available")
    backup = tmp_path / "old-backup"
    shutil.copytree(OLD_BACKUP, backup)
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sqlite_backup_mode"] = "byte-exact-v1"
    manifest["artifact_hashes"] = {
        "data.json": hashlib.sha256((backup / "data.json").read_bytes()).hexdigest(),
        "vinhlong360.db": hashlib.sha256((backup / "vinhlong360.db").read_bytes()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ReviewError, match="backup SQLite is not byte-equal"):
        _review(tmp_path, backup_dir=backup)


def test_review_sqlite_reads_are_immutable_and_explicitly_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_connect = sqlite3.connect
    calls: list[dict] = []

    class TrackedConnection:
        def __init__(self, connection, call: dict) -> None:
            object.__setattr__(self, "_connection", connection)
            object.__setattr__(self, "_call", call)

        def __getattr__(self, name: str):
            return getattr(self._connection, name)

        def __setattr__(self, name: str, value) -> None:
            setattr(self._connection, name, value)

        def __enter__(self):
            self._connection.__enter__()
            return self

        def __exit__(self, *args):
            return self._connection.__exit__(*args)

        def close(self) -> None:
            self._call["closed"] = True
            self._connection.close()

    def tracked_connect(database, *args, **kwargs):
        call = {"database": str(database), "uri": kwargs.get("uri"), "closed": False}
        calls.append(call)
        return TrackedConnection(real_connect(database, *args, **kwargs), call)

    monkeypatch.setattr(review_module.sqlite3, "connect", tracked_connect)
    _review(tmp_path)

    assert calls
    assert all(call["uri"] is True for call in calls)
    assert all("mode=ro&immutable=1" in call["database"] for call in calls)
    assert all(call["closed"] is True for call in calls)


@pytest.mark.parametrize("target", ["protected", "backup"])
def test_review_rechecks_sqlite_sidecars_after_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    root = _copied_protected_root(tmp_path)
    backup = _copied_backup(tmp_path)
    protected_sqlite = root / "agent/data/vinhlong360.db"
    backup_sqlite = backup / "vinhlong360.db"
    selected = protected_sqlite if target == "protected" else backup_sqlite

    def inject_sidecar(path: Path) -> str:
        with sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        assert result == ("ok",)
        if Path(path).resolve() == selected.resolve():
            Path(f"{path}-journal").write_bytes(b"disposable-test-sidecar")
        return "ok"

    monkeypatch.setattr(review_module, "_sqlite_integrity", inject_sidecar, raising=False)
    try:
        with pytest.raises(ReviewError, match=f"{target} SQLite sidecar is present"):
            _review(tmp_path, root=root, backup_dir=backup)
    finally:
        Path(f"{selected}-journal").unlink(missing_ok=True)


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
