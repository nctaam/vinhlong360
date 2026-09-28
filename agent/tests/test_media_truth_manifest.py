import json
from pathlib import Path

from agent.media_truth_manifest import (
    load_batch_21_truth,
    reviewed_removal_ids,
    revoked_legacy_image_ids,
)


def test_batch_21_manifest_freezes_exact_partition_and_revision() -> None:
    truth = load_batch_21_truth()
    assert truth.schema_version == 1
    assert truth.revision == "batch-21-media-truth-v1"
    assert truth.source_ledger_commit == "68d59f0f"
    assert truth.ai_evidence_commit == "30a3fae9"
    assert truth.delete == ("prov-1",)
    assert truth.ai_generated == ("cua-com-duyen-hai", "tep-rang-dua")
    assert len(truth.generated_placeholder) == 37
    all_ids = truth.delete + truth.ai_generated + truth.generated_placeholder
    assert len(all_ids) == 40
    assert len(set(all_ids)) == 40
    assert all_ids == tuple(dict.fromkeys(all_ids))
    assert truth.generated_placeholder == tuple(sorted(truth.generated_placeholder))


def test_manifest_loaders_return_immutable_revocation_inventory() -> None:
    root = Path(__file__).resolve().parents[2]
    truth = load_batch_21_truth(root)
    assert reviewed_removal_ids(root) == frozenset(truth.delete)
    revoked = revoked_legacy_image_ids()
    assert isinstance(revoked, frozenset)
    assert len(revoked) == 40
    assert revoked == frozenset(truth.delete + truth.ai_generated + truth.generated_placeholder)


def test_manifest_json_has_authoritative_top_level_contract() -> None:
    path = Path(__file__).resolve().parents[2] / "docs/standards/batch-21-media-truth.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert list(payload) == [
        "schemaVersion",
        "revision",
        "sourceLedgerCommit",
        "aiEvidenceCommit",
        "delete",
        "ai_generated",
        "generated_placeholder",
    ]
