"""TDD contract for the legacy raw-data scrubber."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

import legacy_scrub
from legacy_scrub import (
    BackupEvidenceRequired,
    ScrubDataError,
    ScrubError,
    StaleScrubPlan,
    apply_scrub_plan,
    build_scrub_plan,
    write_scrub_manifest,
)


OWNER = "user:alice"
OTHER = "user:bob"


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture
def legacy_root(tmp_path: Path) -> Path:
    _write_json(
        tmp_path / "analytics.json",
        {
            "queries": [
                {"owner_key": OWNER, "text": "alice private", "timestamp": "2026-01-01"},
                {"owner_key": OTHER, "text": "Call 0912345678", "timestamp": "2026-01-02"},
                {"text": f"note mentions {OWNER} but is not an owner field"},
            ],
            "unanswered": [],
            "daily_stats": {"2026-01-01": {"queries": 3}},
        },
    )
    _write_json(
        tmp_path / "costs.json",
        {
            "records": [
                {"owner_key": OWNER, "query": "alice secret", "cost": 1},
                {"owner_key": OTHER, "query": "Email bob@example.com", "cost": 2},
            ]
        },
    )
    _write_json(
        tmp_path / "ab_tests.json",
        {
            "outcome_owners": {"exp": {"alice-session": OWNER, "bob-session": OTHER}},
            "outcomes": {"exp": {"alice-session": [1], "bob-session": [2]}},
            "assignments": {"exp": {"alice-session": "a", "bob-session": "b"}},
        },
    )
    _write_json(
        tmp_path / "semantic_cache" / "entries.json",
        {
            "alice-key": {"owner_key": OWNER, "query": "alice query", "response": {"reply": "private"}},
            "bob-key": {"owner_key": OTHER, "query": "bob query", "response": {"reply": "Phone 0912345678"}},
        },
    )
    _write_json(
        tmp_path / "memory" / "graph.json",
        {
            "nodes": [{"id": OWNER, "type": "user"}, {"id": OTHER, "type": "user"}, {"id": "place-1", "type": "entity"}],
            "edges": [
                {"source": OWNER, "target": "place-1", "relation": "visited"},
                {"source": OTHER, "target": "place-1", "relation": "visited"},
            ],
        },
    )
    _write_json(
        tmp_path / "memory" / "experience_bank.json",
        [{"owner_key": OWNER, "title": "alice"}, {"owner_key": OTHER, "title": "bob"}],
    )
    _write_json(
        tmp_path / "memory" / "user_profiles.json",
        {OWNER: {"semantic_facts": ["alice"]}, OTHER: {"semantic_facts": ["bob"]}},
    )
    _write_json(
        tmp_path / "optimizer" / "performance.json",
        {"records": [{"owner_key": OWNER, "query": "alice"}, {"owner_key": OTHER, "query": "bob"}]},
    )
    _write_json(
        tmp_path / "guardrails_budget.json",
        {"sessions": {OWNER: {"tokens_used": 1}, OTHER: {"tokens_used": 2}}},
    )
    _write_json(
        tmp_path / "optimizer" / "demo_pool.json",
        [{"owner_key": OWNER, "query": "alice", "answer": "private"}, {"owner_key": OTHER, "query": "bob", "answer": "ok"}],
    )
    _write_json(
        tmp_path / "optimizer" / "compiled_demos.json",
        {"demos": {"factual": [{"owner_key": OWNER}, {"owner_key": OTHER}]}},
    )
    conversations = tmp_path / "conversations"
    _write_json(conversations / "alice.json", {"owner_key": OWNER, "messages": [{"content": "alice"}]})
    _write_json(conversations / "bob.json", {"owner_key": OTHER, "messages": [{"content": "bob"}]})
    (tmp_path / "learn_loop_log.jsonl").write_text(
        json.dumps({"event": "feedback", "query": "Email alice@example.com"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "admin_audit.jsonl").write_text(
        json.dumps({"actor": OWNER, "reason": "Call 0912345678"}) + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_build_plan_is_dry_run_and_reports_exact_owner_counts(legacy_root: Path):
    before = {path: path.read_bytes() for path in legacy_root.rglob("*") if path.is_file()}

    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])

    after = {path: path.read_bytes() for path in legacy_root.rglob("*") if path.is_file()}
    assert after == before
    assert plan.owner_ids == (OWNER,)
    assert plan.store_count >= 11
    assert plan.total_matches >= 11
    assert all(item.before_digest for item in plan.files)


def test_build_plan_rejects_a_root_without_declared_stores(tmp_path: Path):
    with pytest.raises(ScrubDataError, match="no declared stores"):
        build_scrub_plan(tmp_path, owner_ids=[OWNER])


def test_apply_requires_backup_evidence(legacy_root: Path):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])

    with pytest.raises(BackupEvidenceRequired):
        apply_scrub_plan(plan)


def test_apply_rechecks_digests_and_rewrites_atomically(legacy_root: Path, tmp_path: Path):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    (legacy_root / "analytics.json").write_text(
        (legacy_root / "analytics.json").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")

    with pytest.raises(StaleScrubPlan):
        apply_scrub_plan(plan, backup_evidence=backup)


def test_apply_rejects_unsafe_rendered_output_before_any_mutation(
    legacy_root: Path, tmp_path: Path, monkeypatch
):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")
    before = {item.path: item.path.read_bytes() for item in plan.files}
    real_scrub = legacy_scrub._scrub_payload

    def broken_scrub(store_name, payload, owner_ids):
        if store_name == "analytics":
            return payload, 0, False
        return real_scrub(store_name, payload, owner_ids)

    monkeypatch.setattr(legacy_scrub, "_scrub_payload", broken_scrub)

    with pytest.raises(ScrubError, match="planned output"):
        apply_scrub_plan(plan, backup_evidence=backup)

    assert {path: path.read_bytes() for path in before} == before


def test_apply_removes_exact_structured_links_preserves_unrelated_text_and_redacts_pii(
    legacy_root: Path, tmp_path: Path
):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")

    manifest = apply_scrub_plan(plan, backup_evidence=backup)

    analytics = json.loads((legacy_root / "analytics.json").read_text(encoding="utf-8"))
    assert all(row.get("owner_key") != OWNER for row in analytics["queries"])
    assert any(OWNER in row.get("text", "") for row in analytics["queries"])
    costs = json.loads((legacy_root / "costs.json").read_text(encoding="utf-8"))
    assert all(row.get("owner_key") != OWNER for row in costs["records"])
    assert "bob@example.com" not in (legacy_root / "costs.json").read_text(encoding="utf-8")
    graph = json.loads((legacy_root / "memory" / "graph.json").read_text(encoding="utf-8"))
    assert all(node["id"] != OWNER for node in graph["nodes"])
    assert all(OWNER not in (edge["source"], edge["target"]) for edge in graph["edges"])
    profiles = json.loads((legacy_root / "memory" / "user_profiles.json").read_text(encoding="utf-8"))
    assert OWNER not in profiles
    performance = json.loads((legacy_root / "optimizer" / "performance.json").read_text(encoding="utf-8"))
    assert all(row.get("owner_key") != OWNER for row in performance["records"])
    budgets = json.loads((legacy_root / "guardrails_budget.json").read_text(encoding="utf-8"))
    assert OWNER not in budgets["sessions"]
    assert not (legacy_root / "conversations" / "alice.json").exists()
    assert (legacy_root / "conversations" / "bob.json").exists()
    assert manifest.scanner["pii_findings"] == 0
    assert manifest.counts["files_rewritten"] >= 6
    assert manifest.after_digests


def test_manifest_never_contains_raw_owner_or_content(legacy_root: Path, tmp_path: Path):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")
    manifest = apply_scrub_plan(plan, backup_evidence=backup)
    manifest_path = tmp_path / "scrub-manifest.json"

    write_scrub_manifest(manifest, manifest_path)

    encoded = manifest_path.read_text(encoding="utf-8")
    assert OWNER not in encoded
    assert "alice private" not in encoded
    assert "alice.json" not in encoded
    assert "bob.json" not in encoded
    assert "conversations/" not in encoded
    parsed = json.loads(encoded)
    assert parsed["tool_version"]
    assert parsed["stores"]
    assert parsed["scanner"]["pii_findings"] == 0


def test_manifest_writer_does_not_overwrite_existing_evidence(legacy_root: Path, tmp_path: Path):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")
    manifest = apply_scrub_plan(plan, backup_evidence=backup)
    manifest_path = tmp_path / "scrub-manifest.json"
    manifest_path.write_text("immutable-existing-evidence", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_scrub_manifest(manifest, manifest_path)

    assert manifest_path.read_text(encoding="utf-8") == "immutable-existing-evidence"


def test_cli_rejects_existing_manifest_before_apply_mutates_files(
    legacy_root: Path, tmp_path: Path
):
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")
    manifest_path = tmp_path / "scrub-manifest.json"
    manifest_path.write_text("immutable-existing-evidence", encoding="utf-8")
    before = {path: path.read_bytes() for path in legacy_root.rglob("*") if path.is_file()}
    script = Path(__file__).parents[2] / "scripts" / "scrub_legacy_personal_data.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(legacy_root),
            "--owner-id",
            OWNER,
            "--apply",
            "--backup-evidence",
            str(backup),
            "--manifest",
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "already exists" in result.stderr
    assert {path: path.read_bytes() for path in before} == before


def test_plan_and_apply_cover_primary_and_legacy_prompt_artifact_layouts(
    legacy_root: Path, tmp_path: Path
):
    _write_json(legacy_root / "demos" / "demo_pool.json", [{"owner_key": OWNER}])
    _write_json(
        legacy_root / "demos" / "compiled_demos.json",
        {"demos": {"factual": [{"owner_key": OWNER}]}},
    )
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")

    assert sum(item.store_name == "prompt_demonstrations_raw" for item in plan.files) == 2
    assert sum(item.store_name == "prompt_demonstrations_compiled" for item in plan.files) == 2
    apply_scrub_plan(plan, backup_evidence=backup)

    assert json.loads((legacy_root / "optimizer" / "demo_pool.json").read_text(encoding="utf-8")) == [
        {"owner_key": OTHER, "query": "bob", "answer": "ok"}
    ]
    assert json.loads((legacy_root / "demos" / "demo_pool.json").read_text(encoding="utf-8")) == []


def test_apply_rejects_new_declared_files_created_after_planning(
    legacy_root: Path, tmp_path: Path
):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")
    before = {item.path: item.path.read_bytes() for item in plan.files}
    _write_json(
        legacy_root / "conversations" / "late.json",
        {"owner_key": OWNER, "messages": []},
    )

    with pytest.raises(StaleScrubPlan, match="inventory changed"):
        apply_scrub_plan(plan, backup_evidence=backup)

    assert {path: path.read_bytes() for path in before} == before


def test_apply_rejects_backup_evidence_that_is_a_scrub_input(legacy_root: Path):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])

    with pytest.raises(ScrubError, match="backup evidence overlaps"):
        apply_scrub_plan(plan, backup_evidence=legacy_root / "analytics.json")


@pytest.mark.parametrize(
    ("relative", "payload"),
    [
        ("analytics.json", {"queries": {"owner_key": OWNER}}),
        ("costs.json", {"records": {"owner_key": OWNER}}),
        ("ab_tests.json", {"outcome_owners": [OWNER]}),
        ("guardrails_budget.json", {"sessions": [OWNER]}),
    ],
)
def test_plan_fails_closed_on_declared_store_schema_drift(
    tmp_path: Path, relative: str, payload
):
    _write_json(tmp_path / relative, payload)

    with pytest.raises(ScrubDataError):
        build_scrub_plan(tmp_path, owner_ids=[OWNER])


def test_apply_fails_when_post_apply_pii_scan_is_nonzero(
    legacy_root: Path, tmp_path: Path, monkeypatch
):
    plan = build_scrub_plan(legacy_root, owner_ids=[OWNER])
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")
    monkeypatch.setattr(legacy_scrub, "_scan_after_apply", lambda _plan: (1, {"phone"}))

    with pytest.raises(ScrubError, match="PII remains after scrub"):
        apply_scrub_plan(plan, backup_evidence=backup)


def test_encrypted_cold_memory_is_scrubbed_with_its_existing_key(tmp_path: Path):
    key = Fernet.generate_key()
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / ".key").write_bytes(key)
    plaintext = json.dumps({OWNER: {"facts": ["alice"]}, OTHER: {"facts": ["bob"]}})
    encrypted = Fernet(key).encrypt(plaintext.encode("utf-8")).decode("utf-8")
    (memory_dir / "user_profiles.json").write_text(encrypted, encoding="utf-8")
    backup = tmp_path / "backup.marker"
    backup.write_text("verified-backup", encoding="utf-8")

    plan = build_scrub_plan(tmp_path, owner_ids=[OWNER])
    apply_scrub_plan(plan, backup_evidence=backup)

    scrubbed_token = (memory_dir / "user_profiles.json").read_text(encoding="utf-8")
    scrubbed = json.loads(Fernet(key).decrypt(scrubbed_token.encode("utf-8")))
    assert OWNER not in scrubbed
    assert OTHER in scrubbed


def test_cli_dry_run_exposes_reviewable_store_digests_and_pii_counts(
    legacy_root: Path
):
    script = Path(__file__).parents[2] / "scripts" / "scrub_legacy_personal_data.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(legacy_root), "--owner-id", OWNER],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["mode"] == "dry-run"
    assert output["owner_matches"] >= 11
    assert output["pii_findings"] > 0
    assert any(item["store_name"] == "analytics" and item["before_digest"] for item in output["files"])
    assert OWNER not in result.stdout
