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
    assert truth.generated_placeholder[0] == "ba-nhi-bun-bo-hue-vinh-long-vinh-long"
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


def test_manifest_loader_rejects_malformed_contract(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "docs/standards/batch-21-media-truth.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    manifest_path = tmp_path / "docs/standards/batch-21-media-truth.json"
    manifest_path.parent.mkdir(parents=True)

    malformed = [
        ("extra key", {**payload, "unexpected": True}),
        ("schema", {**payload, "schemaVersion": 999}),
        ("revision", {**payload, "revision": "wrong"}),
        ("ledger commit", {**payload, "sourceLedgerCommit": "wrong"}),
        ("ai commit", {**payload, "aiEvidenceCommit": "wrong"}),
        ("partition type", {**payload, "ai_generated": "cua-com-duyen-hai"}),
        ("delete count", {**payload, "delete": []}),
        ("ai count", {**payload, "ai_generated": ["cua-com-duyen-hai"]}),
        ("placeholder count", {**payload, "generated_placeholder": list(payload["generated_placeholder"][:-1])}),
        ("duplicate", {**payload, "delete": ["prov-1", "prov-1"]}),
        ("unsorted", {**payload, "generated_placeholder": list(reversed(payload["generated_placeholder"]))}),
        ("overlap", {**payload, "ai_generated": ["prov-1", "tep-rang-dua"]}),
    ]
    for _label, candidate in malformed:
        manifest_path.write_text(json.dumps(candidate), encoding="utf-8")
        try:
            load_batch_21_truth(tmp_path)
        except ValueError:
            continue
        raise AssertionError(f"malformed manifest accepted: {_label}")


def test_manifest_loader_accepts_valid_manifest_copy(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "docs/standards/batch-21-media-truth.json"
    manifest_path = tmp_path / "docs/standards/batch-21-media-truth.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    truth = load_batch_21_truth(tmp_path)
    assert truth.revision == "batch-21-media-truth-v1"
