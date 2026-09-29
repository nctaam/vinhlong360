import hashlib
import json
from pathlib import Path

import pytest

from scripts.checks.reconcile_data_dry_run import _photo_mutations, build_plan, main, render_plan
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
    assert not any(m["recordId"] == "prov-1" for m in plan["mutations"])
    assert any("verifiedAt" in str(d) for d in plan["deferred"])
    assert any(d["recordId"] == "vuon-trai-cay-cu-lao-dai" for d in plan["deferred"])
    assert not any(d["recordId"] == "prov-1" for d in plan["deferred"])


def _retained_photo(tmp_path, **updates):
    row = {"entity_id": "retained-1", "image": "web-nuxt/public/img/entities/retained-1.webp", "author": "Author", "source": "Publisher", "license": "Copyright attribution"}
    row.update(updates)
    path = tmp_path / "photos.json"
    path.write_text(json.dumps([row]), encoding="utf-8")
    return path


def _retained_current():
    return {"id": "retained-1", "images": json.dumps(["/img/entities/retained-1.webp"]), "attributes": "{}"}


def test_present_target_photo_review_semantics_use_retained_fixture(tmp_path):
    changes, requirements, deferred = _photo_mutations(_retained_current(), _retained_photo(tmp_path), frozenset(), entity_id="retained-1")
    assert not changes
    assert requirements == ["image-specific source URL", "explicit permission evidence"]
    assert deferred is True


@pytest.mark.parametrize("host", ["foo.example.test", "foo.example.com", "foo.example.net", "foo.example.org", "foo.localhost", "foo.localdomain"])
def test_retained_photo_rejects_placeholder_source_url(tmp_path, host):
    changes, requirements, deferred = _photo_mutations(_retained_current(), _retained_photo(tmp_path, image_source_url=f"https://{host}/source", permission_evidence="written release"), frozenset(), entity_id="retained-1")
    assert not changes and deferred is True
    assert requirements == ["image-specific source URL"]


def test_retained_photo_rejects_generic_or_malformed_url(tmp_path):
    changes, requirements, deferred = _photo_mutations(_retained_current(), _retained_photo(tmp_path, source_url="https://news.example/article", permission_evidence="owner-record:IMG-2026-001"), frozenset(), entity_id="retained-1")
    assert not changes and deferred is True
    assert requirements == ["image-specific source URL"]


def test_retained_photo_rejects_malformed_url(tmp_path):
    changes, requirements, deferred = _photo_mutations(_retained_current(), _retained_photo(tmp_path, image_source_url="https://", permission_evidence="owner-record:IMG-2026-001"), frozenset(), entity_id="retained-1")
    assert not changes and deferred is True
    assert requirements == ["image-specific source URL"]


def test_retained_photo_duplicate_rows_do_not_duplicate_deferred_state(tmp_path):
    path = _retained_photo(tmp_path)
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows.append(dict(rows[0]))
    path.write_text(json.dumps(rows), encoding="utf-8")
    changes, requirements, deferred = _photo_mutations(_retained_current(), path, frozenset(), entity_id="retained-1")
    assert not changes and deferred is True
    assert requirements == ["image-specific source URL", "explicit permission evidence"]


def test_retained_photo_accepts_complete_image_provenance(tmp_path):
    changes, requirements, deferred = _photo_mutations(_retained_current(), _retained_photo(tmp_path, image_source_url="https://baovinhlong.com.vn/images/retained-1.webp", permission_evidence="owner-record:IMG-2026-001"), frozenset(), entity_id="retained-1")
    assert len(changes) == 7
    assert {item["recordId"] for item in changes} == {"retained-1"}
    assert not any(item["recordId"] == "prov-1" for item in changes)
    assert requirements == []
    assert deferred is False

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
