import hashlib
import json
from pathlib import Path

import pytest

from scripts.checks.reconcile_data_dry_run import build_plan, main, render_plan
from scripts.checks.audit_data_parity import build_report


ROOT = Path(__file__).resolve().parents[2]
SQLITE = ROOT / "agent/data/vinhlong360.db"
JSON = ROOT / "web/data.json"
PARITY = ROOT / "outputs/data-parity-audit-2026-09-22.json"
LEDGERS = {
    "phase7": ROOT / "outputs/remediation_phase7_log.json",
    "spatial": ROOT / "outputs/remediation_spatial.json",
    "master": ROOT / "outputs/data_remediation_ledger.json",
    "photos": ROOT / "outputs/batch_culinary_restaurants_photos.json",
    "phase21": ROOT / "outputs/remediation_phase21_image_log.json",
    "batch7": ROOT / "outputs/batch7_master_enrichment_log.json",
    "temporal": ROOT / "outputs/remediation_temporal.json",
}


def _fresh_parity(tmp_path):
    path = tmp_path / "current-parity.json"
    path.write_text(json.dumps(build_report(SQLITE, JSON)), encoding="utf-8")
    return path


def test_production_counts_and_key_proposals(tmp_path):
    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), LEDGERS)
    assert plan["status"] == "review_required"
    assert sum(m["operation"] == "update" and m["recordType"] == "relationship" for m in plan["mutations"]) == 478
    assert sum(m["operation"] == "delete" and m["store"] == "sqlite" for m in plan["mutations"]) == 4
    assert sum(m["operation"] == "delete" and m["store"] == "json" for m in plan["mutations"]) == 6
    prov = [m for m in plan["mutations"] if m["recordId"] == "prov-1"]
    assert {m["store"] for m in prov} >= {"sqlite"}
    assert any(m["field"] == "coordinates" and m["after"] == [10.253, 106.012] for m in prov)
    assert any(m["field"] == "placeId" and m["after"] == "p-thanh-duc" for m in prov)
    assert any("verifiedAt" in str(d) for d in plan["deferred"])
    assert any(d["recordId"] == "vuon-trai-cay-cu-lao-dai" for d in plan["deferred"])
    assert any(d["itemId"] == "prov-1-text-gaps" and "parity" in d["evidence"][0] for d in plan["deferred"])


def test_prov1_documentary_image_bundle_is_deferred_until_provenance_is_complete(tmp_path):
    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), LEDGERS)
    image_fields = {
        "images",
        "attributes.image_type",
        "attributes.is_verified_photo",
        "attributes.image_author",
        "attributes.image_source",
        "attributes.image_caption",
        "attributes.image_license",
    }

    assert not any(
        mutation["recordId"] == "prov-1" and mutation["field"] in image_fields
        for mutation in plan["mutations"]
    )
    deferred = [item for item in plan["deferred"] if item["itemId"] == "prov-1-image-provenance"]
    assert len(deferred) == 1
    assert deferred[0]["recordId"] == "prov-1"
    assert deferred[0]["requirements"] == [
        "image-specific source URL",
        "explicit permission evidence",
    ]


def test_prov1_documentary_image_bundle_rejects_placeholder_source_url(tmp_path):
    photos = json.loads(LEDGERS["photos"].read_text(encoding="utf-8"))
    item = next(record for record in photos if record.get("entity_id") == "prov-1")
    item.update({"image_source_url": "https://example.test/source", "permission_evidence": "written release"})
    photos_path = tmp_path / "photos.json"
    photos_path.write_text(json.dumps(photos), encoding="utf-8")

    ledgers = {**LEDGERS, "photos": photos_path}
    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), ledgers)
    deferred = [item for item in plan["deferred"] if item["itemId"] == "prov-1-image-provenance"]

    assert len(deferred) == 1
    assert deferred[0]["requirements"] == ["image-specific source URL"]


@pytest.mark.parametrize(
    "host",
    ["foo.example.test", "foo.example.com", "foo.example.net", "foo.example.org", "foo.localhost", "foo.localdomain"],
)
def test_prov1_documentary_image_bundle_rejects_placeholder_subdomains(tmp_path, host):
    photos = json.loads(LEDGERS["photos"].read_text(encoding="utf-8"))
    item = next(record for record in photos if record.get("entity_id") == "prov-1")
    item.update({"image_source_url": f"https://{host}/source", "permission_evidence": "written release"})
    photos_path = tmp_path / "photos.json"
    photos_path.write_text(json.dumps(photos), encoding="utf-8")

    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), {**LEDGERS, "photos": photos_path})
    deferred = [item for item in plan["deferred"] if item["itemId"] == "prov-1-image-provenance"]

    assert len(deferred) == 1
    assert deferred[0]["requirements"] == ["image-specific source URL"]


def test_prov1_documentary_image_bundle_accepts_complete_image_provenance(tmp_path):
    photos = json.loads(LEDGERS["photos"].read_text(encoding="utf-8"))
    item = next(record for record in photos if record.get("entity_id") == "prov-1")
    item.update({"image_source_url": "https://baovinhlong.com.vn/images/prov-1.webp", "permission_evidence": "written release"})
    photos_path = tmp_path / "photos.json"
    photos_path.write_text(json.dumps(photos), encoding="utf-8")

    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), {**LEDGERS, "photos": photos_path})
    image_mutations = [
        mutation for mutation in plan["mutations"]
        if mutation["recordId"] == "prov-1" and mutation["field"].startswith("attributes.image_")
    ]

    assert len(image_mutations) == 5
    assert not any(item["itemId"] == "prov-1-image-provenance" for item in plan["deferred"])


def test_prov1_documentary_image_bundle_rejects_generic_or_malformed_url(tmp_path):
    photos = json.loads(LEDGERS["photos"].read_text(encoding="utf-8"))
    item = next(record for record in photos if record.get("entity_id") == "prov-1")
    item.update({"source_url": "https://news.example/article", "permission_evidence": "written release"})
    photos_path = tmp_path / "photos.json"
    photos_path.write_text(json.dumps(photos), encoding="utf-8")

    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), {**LEDGERS, "photos": photos_path})
    deferred = next(item for item in plan["deferred"] if item["itemId"] == "prov-1-image-provenance")

    assert deferred["requirements"] == ["image-specific source URL"]

    item["image_source_url"] = "https://"
    photos_path.write_text(json.dumps(photos), encoding="utf-8")
    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), {**LEDGERS, "photos": photos_path})
    deferred = next(item for item in plan["deferred"] if item["itemId"] == "prov-1-image-provenance")
    assert deferred["requirements"] == ["image-specific source URL"]


def test_prov1_documentary_image_bundle_deduplicates_duplicate_ledger_rows(tmp_path):
    photos = json.loads(LEDGERS["photos"].read_text(encoding="utf-8"))
    item = next(record for record in photos if record.get("entity_id") == "prov-1")
    photos.append(dict(item))
    photos_path = tmp_path / "photos.json"
    photos_path.write_text(json.dumps(photos), encoding="utf-8")

    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), {**LEDGERS, "photos": photos_path})

    assert sum(item["itemId"] == "prov-1-image-provenance" for item in plan["deferred"]) == 1


def test_stale_parity_fails_closed(tmp_path):
    stale = json.loads(PARITY.read_text(encoding="utf-8"))
    stale["inputs"]["json"]["sha256"] = "0" * 64
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        build_plan(SQLITE, JSON, path, LEDGERS)


def test_render_deterministic_and_inputs_unchanged(tmp_path):
    before = (hashlib.sha256(SQLITE.read_bytes()).hexdigest(), hashlib.sha256(JSON.read_bytes()).hexdigest())
    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), LEDGERS)
    assert render_plan(plan) == render_plan(json.loads(render_plan(plan)))
    after = (hashlib.sha256(SQLITE.read_bytes()).hexdigest(), hashlib.sha256(JSON.read_bytes()).hexdigest())
    assert before == after


def test_output_collision_returns_two(tmp_path):
    target = tmp_path / "collision.json"
    target.write_text("x", encoding="utf-8")
    assert main(["--parity", str(PARITY), "--output", str(target)]) == 2


def test_reviewed_tombstone_never_gets_repair_proposals(tmp_path):
    plan = build_plan(SQLITE, JSON, _fresh_parity(tmp_path), LEDGERS)
    assert not any(item["recordId"] == "prov-1" for item in plan["mutations"])
    assert not any(item["recordId"] == "prov-1" for item in plan["deferred"])
