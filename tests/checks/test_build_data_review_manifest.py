from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.checks.build_data_review_manifest import ManifestError, build_manifest


ROOT = Path(__file__).resolve().parents[2]
SQLITE = ROOT / "agent/data/vinhlong360.db"
JSON_STORE = ROOT / "web/data.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_is_review_only_and_contains_known_findings(tmp_path: Path):
    before = (_sha(SQLITE), _sha(JSON_STORE))

    manifest = build_manifest(ROOT, tmp_path / "manifest.json")

    assert manifest["status"] == "review_required"
    assert manifest["mutationAllowed"] is False
    assert manifest["summary"]["findingCount"] == len(manifest["findings"])
    assert manifest["findings"]
    assert all(item["status"] == "review_required" for item in manifest["findings"])
    assert all(item["mutationAllowed"] is False for item in manifest["findings"])
    assert {item["category"] for item in manifest["findings"]} >= {
        "prov-1-contract-gaps",
        "relationship-parity-drift",
        "documentary-image-provenance",
        "phase4-cliche",
        "verifiedAt-conflicts",
        "owner-approved-conflict",
    }
    assert all(item["evidence"] for item in manifest["findings"])
    assert all("after" not in item for item in manifest["findings"])
    assert before == (_sha(SQLITE), _sha(JSON_STORE))


def test_manifest_is_deterministic_and_atomically_replaced(tmp_path: Path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    first = build_manifest(ROOT, first_path)
    second = build_manifest(ROOT, second_path)

    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()
    assert not list(tmp_path.glob("*.tmp"))


def test_manifest_fails_closed_when_required_fixture_is_missing(tmp_path: Path):
    (tmp_path / "agent/data").mkdir(parents=True)
    (tmp_path / "web").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "agent/data/vinhlong360.db").write_bytes(b"not sqlite")
    (tmp_path / "web/data.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ManifestError, match="parity report"):
        build_manifest(tmp_path)


def test_manifest_rejects_invalid_json_fixture(tmp_path: Path):
    (tmp_path / "agent/data").mkdir(parents=True)
    (tmp_path / "web").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "agent/data/vinhlong360.db").write_bytes(b"not sqlite")
    (tmp_path / "web/data.json").write_text("{", encoding="utf-8")
    (tmp_path / "outputs/data-parity-audit-2026-09-22.json").write_text(
        json.dumps({"relationshipDiff": {}}), encoding="utf-8"
    )

    with pytest.raises(ManifestError, match="JSON"):
        build_manifest(tmp_path)


def test_manifest_marks_deleted_prov1_history_superseded():
    manifest = build_manifest(ROOT)
    assert not any("prov-1" in item.get("recordIds", []) for item in manifest["findings"])
    assert any(
        item["recordId"] == "prov-1" and item["status"] == "superseded"
        for item in manifest["history"]
    )
