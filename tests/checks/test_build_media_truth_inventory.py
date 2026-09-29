from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.checks.build_media_truth_inventory import InventoryError, build_inventory, render_inventory


ROOT = Path(__file__).resolve().parents[2]
TRUTH = ROOT / "docs/standards/batch-21-media-truth.json"
CANDIDATE = ROOT / ".tmp/media-truth-stage-test-4/candidate"


def _write_fixture(tmp_path: Path, entities: list[dict], *, truth: Path = TRUTH) -> tuple[Path, Path, Path]:
    data_path = tmp_path / "data.json"
    asset_root = tmp_path / "public/img/entities"
    asset_root.mkdir(parents=True)
    data_path.write_text(
        json.dumps({"entities": entities, "relationships": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "vinhlong360.db").write_bytes(b"candidate-db")
    (tmp_path / "stage-result.json").write_text(
        json.dumps({"mutationAllowed": False}), encoding="utf-8"
    )
    for entity in entities:
        entity_id = entity["id"]
        (asset_root / f"{entity_id}.webp").write_bytes(b"asset:" + entity_id.encode())
    return tmp_path, data_path, asset_root


def _entity(entity_id: str, attrs: dict, image: str | None = None) -> dict:
    return {
        "id": entity_id,
        "name": entity_id,
        "images": [image or f"/img/entities/{entity_id}.webp"],
        "attributes": attrs,
    }


def test_candidate_inventory_has_one_row_per_remaining_entity():
    if not CANDIDATE.is_dir():
        pytest.skip("staged candidate fixture is not available")
    inventory = build_inventory(
        CANDIDATE,
        CANDIDATE / "data.json",
        CANDIDATE / "public/img/entities",
        TRUTH,
    )
    ids = [row["entityId"] for row in inventory["items"]]
    assert len(ids) == 1771
    assert len(set(ids)) == 1771
    assert "prov-1" not in ids
    assert inventory["mutationAllowed"] is False
    assert all(row["proposedMutation"] is None for row in inventory["items"])


def test_unknown_asset_is_quarantined_not_inferred_from_file_size(tmp_path: Path):
    root, data_path, asset_root = _write_fixture(
        tmp_path,
        [_entity("unknown-asset", {"is_verified_photo": True})],
    )
    row = build_inventory(root, data_path, asset_root, TRUTH)["items"][0]
    assert row["classification"] == "unknown-quarantined"
    assert row["proposedMutation"] is None


def test_missing_rights_evidence_stays_documentary_missing(tmp_path: Path):
    root, data_path, asset_root = _write_fixture(
        tmp_path,
        [
            _entity(
                "documentary-gap",
                {
                    "image_type": "documentary",
                    "is_verified_photo": True,
                    "image_author": "Author",
                    "image_source": "Publisher",
                    "image_source_url": "https://example.test/photo/1",
                    "image_license": "Bản quyền thuộc tác giả",
                    "verifiedAt": "2099-01-01T00:00:00Z",
                },
            )
        ],
    )
    row = build_inventory(root, data_path, asset_root, TRUTH)["items"][0]
    assert row["classification"] == "documentary-candidate-missing-evidence"
    assert "license or re-host scope" in row["missingRequirements"]
    assert "explicit permission evidence" in row["missingRequirements"]


def test_ai_and_placeholder_rows_require_explicit_non_photographic_contract(tmp_path: Path):
    entities = [
        _entity(
            "cua-com-duyen-hai",
            {
                "image_type": "ai-generated",
                "is_verified_photo": False,
                "image_generation_model": "cx/gpt-5.5-image",
                "image_generation_reference": "git:30a3fae9",
            },
        ),
        _entity(
            "ba-nhi-bun-bo-hue-vinh-long",
            {"image_type": "generated-placeholder", "is_verified_photo": False},
        ),
    ]
    root, data_path, asset_root = _write_fixture(tmp_path, entities)
    rows = {row["entityId"]: row for row in build_inventory(root, data_path, asset_root, TRUTH)["items"]}
    assert rows["cua-com-duyen-hai"]["classification"] == "ai-generated"
    assert rows["ba-nhi-bun-bo-hue-vinh-long"]["classification"] == "generated-placeholder"
    assert all(rows[key]["reviewStatus"] == "non_photographic" for key in rows)


@pytest.mark.parametrize("case", ["missing-asset", "hash-drift", "malformed-truth", "duplicate-id", "unsafe-path"])
def test_inventory_fail_closed(tmp_path: Path, case: str):
    entity = _entity("safe-id", {})
    root, data_path, asset_root = _write_fixture(tmp_path, [entity])
    if case == "missing-asset":
        (asset_root / "safe-id.webp").unlink()
    elif case == "hash-drift":
        stage = {"mutationAllowed": False, "assets": {"retained": [{"id": "safe-id", "sha256": hashlib.sha256(b"original").hexdigest()}]}}
        (root / "stage-result.json").write_text(json.dumps(stage), encoding="utf-8")
    elif case == "malformed-truth":
        bad_truth = tmp_path / "bad-truth.json"
        bad_truth.write_text("{", encoding="utf-8")
        with pytest.raises(InventoryError):
            build_inventory(root, data_path, asset_root, bad_truth)
        return
    elif case == "duplicate-id":
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        payload["entities"].append(copy.deepcopy(payload["entities"][0]))
        data_path.write_text(json.dumps(payload), encoding="utf-8")
    elif case == "unsafe-path":
        unsafe = tmp_path.parent / "outside.json"
        unsafe.write_text("{}", encoding="utf-8")
        with pytest.raises(InventoryError):
            build_inventory(root, unsafe, asset_root, TRUTH)
        return
    with pytest.raises(InventoryError):
        build_inventory(root, data_path, asset_root, TRUTH)


def test_repeated_generation_is_sorted_lf_and_byte_identical(tmp_path: Path):
    entities = [_entity("b-id", {}), _entity("a-id", {})]
    root, data_path, asset_root = _write_fixture(tmp_path, entities)
    first = render_inventory(build_inventory(root, data_path, asset_root, TRUTH))
    second = render_inventory(build_inventory(root, data_path, asset_root, TRUTH))
    assert first == second
    assert first.endswith(b"\n")
    assert b"\r" not in first
    parsed = json.loads(first)
    assert [row["entityId"] for row in parsed["items"]] == ["a-id", "b-id"]


def test_unsafe_image_path_is_rejected_even_when_basename_exists(tmp_path: Path):
    root, data_path, asset_root = _write_fixture(tmp_path, [_entity("unsafe-id", {})])
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    payload["entities"][0]["images"] = ["../../outside.webp"]
    data_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InventoryError, match="unsafe image path"):
        build_inventory(root, data_path, asset_root, TRUTH)


def test_stage_result_cannot_reference_unknown_entity(tmp_path: Path):
    root, data_path, asset_root = _write_fixture(tmp_path, [_entity("known-id", {})])
    stage = {
        "mutationAllowed": False,
        "assets": {"retained": [{"id": "ghost-id", "sha256": hashlib.sha256(b"ghost").hexdigest()}]},
    }
    (root / "stage-result.json").write_text(json.dumps(stage), encoding="utf-8")
    with pytest.raises(InventoryError, match="unknown entity"):
        build_inventory(root, data_path, asset_root, TRUTH)
