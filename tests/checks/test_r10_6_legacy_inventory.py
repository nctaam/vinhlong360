import json
from pathlib import Path

from scripts.checks.check_complexity import ComplexityCheck
from scripts.checks.check_banned_claims import (
    ImageSourcePolicyCheck,
    _load_legacy_generic_url_ids,
    _load_legacy_license_ids,
)


def test_documentary_missing_stays_within_complexity_limit() -> None:
    result = ComplexityCheck(root=Path(__file__).resolve().parents[2]).run(
        ["scripts/checks/check_banned_claims.py"]
    )
    violations = [
        violation
        for violation in result["violations"]
        if "_documentary_missing()" in violation["msg"]
    ]
    assert violations == []


def _mk(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_r10_6(tmp_path: Path, entity: dict) -> dict:
    _mk(
        tmp_path,
        "web/data.json",
        json.dumps({"entities": [entity], "relationships": [], "itineraries": []}),
    )
    return ImageSourcePolicyCheck(root=tmp_path).run()


def _entity(entity_id: str) -> dict:
    return {
        "id": entity_id,
        "createdAt": "2020-01-01",
        "images": [f"/img/entities/{entity_id}.webp"],
        "source": [{"url": "https://baovinhlong.com.vn/articles/story"}],
        "attributes": {
            "image_type": "documentary",
            "is_verified_photo": True,
            "image_author": "Author",
            "image_source": "Publisher",
            "image_license": "Bản quyền thuộc tác giả và Publisher",
        },
    }


def test_backdated_unlisted_id_cannot_use_legacy_license_or_generic_url(tmp_path):
    result = _run_r10_6(tmp_path, _entity("new-id"))
    message = result["violations"][0]["msg"]
    assert "image_license" in message
    assert "URL nguồn" in message


def test_inventoried_legacy_id_receives_only_legacy_license_compatibility(tmp_path):
    ids = sorted({"legacy-id", *(f"fixture-{index:04d}" for index in range(1771))})
    inventory = "\n".join(
        [
            "# Snapshot: 2026-09-21",
            "# Source: web/data.json",
            "# Source SHA-256: 8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f",
            "# Entity count: 1772",
            *ids,
            "",
        ]
    )
    _mk(tmp_path, "docs/standards/r10.6-legacy-image-license-ids.txt", inventory)
    entity = _entity("legacy-id")
    entity["source"] = []
    result = _run_r10_6(tmp_path, entity)
    message = result["violations"][0]["msg"]
    assert "image_license" not in message
    assert "URL nguồn" in message


def test_url_debt_id_does_not_grant_license_compatibility(tmp_path):
    _mk(tmp_path, "docs/standards/r10.6-image-url-debt.txt", "url-debt-id\n")
    result = _run_r10_6(tmp_path, _entity("url-debt-id"))
    message = result["violations"][0]["msg"]
    assert "image_license" in message
    assert "URL nguồn" not in message


def test_generic_url_inventory_allows_only_generic_url_compatibility(tmp_path):
    ids = sorted({"legacy-id", *(f"fixture-{index:04d}" for index in range(1263))})
    inventory = "\n".join(
        [
            "# Snapshot: 2026-09-21",
            "# Source: web/data.json",
            "# Source SHA-256: 8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f",
            "# Entity count: 1264",
            *ids,
            "",
        ]
    )
    _mk(tmp_path, "docs/standards/r10.6-legacy-generic-url-ids.txt", inventory)
    entity = _entity("legacy-id")
    entity["attributes"]["image_license"] = "CC BY 4.0"
    result = _run_r10_6(tmp_path, entity)
    assert result["count"] == 0


def test_generic_url_inventory_requires_current_public_citation(tmp_path):
    ids = sorted({"legacy-id", *(f"fixture-{index:04d}" for index in range(1263))})
    inventory = "\n".join(
        [
            "# Snapshot: 2026-09-21",
            "# Source: web/data.json",
            "# Source SHA-256: 8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f",
            "# Entity count: 1264",
            *ids,
            "",
        ]
    )
    _mk(tmp_path, "docs/standards/r10.6-legacy-generic-url-ids.txt", inventory)
    entity = _entity("legacy-id")
    entity["attributes"]["image_license"] = "CC BY 4.0"
    entity["source"] = []
    result = _run_r10_6(tmp_path, entity)
    assert "URL nguồn" in result["violations"][0]["msg"]


def test_generic_url_inventory_rejects_local_citation(tmp_path):
    ids = sorted({"legacy-id", *(f"fixture-{index:04d}" for index in range(1263))})
    inventory = "\n".join(
        [
            "# Snapshot: 2026-09-21",
            "# Source: web/data.json",
            "# Source SHA-256: 8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f",
            "# Entity count: 1264",
            *ids,
            "",
        ]
    )
    _mk(tmp_path, "docs/standards/r10.6-legacy-generic-url-ids.txt", inventory)
    entity = _entity("legacy-id")
    entity["attributes"]["image_license"] = "CC BY 4.0"
    entity["source"] = [{"url": "https://printer.local/article"}]
    result = _run_r10_6(tmp_path, entity)
    assert "URL nguồn" in result["violations"][0]["msg"]


def test_generic_inventory_mismatch_fails_closed(tmp_path):
    _mk(
        tmp_path,
        "docs/standards/r10.6-legacy-generic-url-ids.txt",
        "# Snapshot: 2026-09-20\nlegacy-id\n",
    )
    assert _load_legacy_generic_url_ids(tmp_path) == set()
    result = _run_r10_6(tmp_path, _entity("legacy-id"))
    message = result["violations"][0]["msg"]
    assert "URL nguồn" in message


def test_malformed_or_mismatched_inventory_fails_closed(tmp_path):
    _mk(
        tmp_path,
        "docs/standards/r10.6-legacy-image-license-ids.txt",
        "# Snapshot: 2026-09-20\nlegacy-id\n",
    )
    assert _load_legacy_license_ids(tmp_path) == set()
    result = _run_r10_6(tmp_path, _entity("legacy-id"))
    message = result["violations"][0]["msg"]
    assert "image_license" in message


def test_revoked_batch_21_id_cannot_use_legacy_license_compatibility(tmp_path):
    ids = sorted({"banh-trang-my-long", *(f"fixture-{index:04d}" for index in range(1771))})
    inventory = "\n".join([
        "# Snapshot: 2026-09-21",
        "# Source: web/data.json",
        "# Source SHA-256: 8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f",
        "# Entity count: 1772",
        *ids,
        "",
    ])
    _mk(tmp_path, "docs/standards/r10.6-legacy-image-license-ids.txt", inventory)
    _mk(
        tmp_path,
        "docs/standards/r10.6-legacy-image-revocations.txt",
        "# Manifest revision: batch-21-media-truth-v1\n# Inventory: subtractive legacy image compatibility revocations\n"
        "banh-trang-my-long\n",
    )
    result = _run_r10_6(tmp_path, _entity("banh-trang-my-long"))
    assert "image_license" in result["violations"][0]["msg"]
