from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.checks.build_image_provenance_review import ProvenanceReviewError, build_packet as _build_packet, main as provenance_main


ROOT = Path(__file__).resolve().parents[2]
SQLITE = ROOT / "agent/data/vinhlong360.db"
JSON_STORE = ROOT / "web/data.json"
PHOTO_LEDGER = ROOT / "outputs/batch_culinary_restaurants_photos.json"
TARGET_ID = "lang-nghe-san-xuat-chi-xo-dua-an-thanh"
TARGET_IMAGE = f"/img/entities/{TARGET_ID}.webp"


def build_packet(*args, **kwargs):
    kwargs.setdefault("entity_id", TARGET_ID)
    kwargs.setdefault("image_path", TARGET_IMAGE)
    return _build_packet(*args, **kwargs)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prov1_ledger(tmp_path: Path, **updates: object) -> Path:
    rows = [{
        "entity_id": TARGET_ID,
        "image": f"web-nuxt/public{TARGET_IMAGE}",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "license": "Bản quyền thuộc tác giả và Báo Vĩnh Long",
    }]
    rows[0].update(updates)
    path = tmp_path / "photos.json"
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return path


def _write_ledger(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "photos.json"
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return path


def _json_with_complete_metadata(tmp_path: Path) -> Path:
    payload = json.loads(JSON_STORE.read_text(encoding="utf-8"))
    entity = next(item for item in payload["entities"] if item["id"] == "lang-nghe-san-xuat-chi-xo-dua-an-thanh")
    entity["attributes"].update(
        {
            "image_source_url": "https://baovinhlong.com.vn/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
            "image_author": "Trần Phước",
            "image_source": "Báo Vĩnh Long",
            "image_license": "Được phép re-host theo văn bản lưu trữ",
        }
    )
    entity["source"] = [{"name": "Báo Vĩnh Long", "url": "https://baovinhlong.com.vn/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp"}]
    path = tmp_path / "data.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _json_with_unrelated_entity_citation(tmp_path: Path) -> Path:
    payload = json.loads(JSON_STORE.read_text(encoding="utf-8"))
    entity = next(item for item in payload["entities"] if item["id"] == "lang-nghe-san-xuat-chi-xo-dua-an-thanh")
    entity["source"] = [{"name": "Báo Vĩnh Long", "url": "https://baovinhlong.com.vn/articles/unrelated"}]
    entity["attributes"]["source_citations"] = [
        {"url": "https://baovinhlong.com.vn/articles/also-unrelated"}
    ]
    path = tmp_path / "data.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _json_with_target_images(tmp_path: Path, images: object) -> Path:
    payload = json.loads(JSON_STORE.read_text(encoding="utf-8"))
    entity = next(item for item in payload["entities"] if item["id"] == "lang-nghe-san-xuat-chi-xo-dua-an-thanh")
    entity["images"] = images
    path = tmp_path / "data.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _isolated_review_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    database = root / "agent/data/vinhlong360.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE entities (id TEXT PRIMARY KEY, images TEXT, attributes TEXT)"
        )
        connection.execute(
            "INSERT INTO entities (id, images, attributes) VALUES (?, ?, ?)",
            ("lang-nghe-san-xuat-chi-xo-dua-an-thanh", json.dumps(["/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp"]), "{}"),
        )

    json_store = root / "web/data.json"
    json_store.parent.mkdir(parents=True)
    json_store.write_text(
        json.dumps(
            {
                "entities": [
                    {
                        "id": "lang-nghe-san-xuat-chi-xo-dua-an-thanh",
                        "images": ["/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp"],
                        "attributes": {
                            "image_author": "Author",
                            "image_source": "Publisher",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ledger = root / "outputs/batch_culinary_restaurants_photos.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps(
            [
                {
                    "entity_id": "lang-nghe-san-xuat-chi-xo-dua-an-thanh",
                    "image": "web-nuxt/public/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
                    "author": "Author",
                    "source": "Publisher",
                }
            ]
        ),
        encoding="utf-8",
    )
    return root


def test_current_prov1_packet_is_review_only_and_exposes_missing_requirements(tmp_path: Path):
    before = (_sha(SQLITE), _sha(JSON_STORE))

    packet = build_packet(ROOT, tmp_path / "packet.json", photo_ledger=_prov1_ledger(tmp_path))

    assert packet["status"] == "ready_for_owner_review"
    assert packet["mutationAllowed"] is False
    assert packet["target"]["entityId"] == "lang-nghe-san-xuat-chi-xo-dua-an-thanh"
    assert set(packet["requirements"]["missing"]) == {
        "image-specific source URL",
        "explicit permission evidence",
        "license or re-host scope",
    }
    assert all(item["status"] == "review_required" for item in packet["evidenceChecklist"])
    assert all(item["mutationAllowed"] is False for item in packet["evidenceChecklist"])
    assert all(item["status"] == "review_required" for item in packet["ledgerEvidence"])
    assert all(item["mutationAllowed"] is False for item in packet["ledgerEvidence"])
    assert "after" not in json.dumps(packet)
    assert before == (_sha(SQLITE), _sha(JSON_STORE))


@pytest.mark.parametrize("host", ["example.test", "foo.example.com", "foo.localhost"])
def test_placeholder_source_url_never_satisfies_source_requirement(tmp_path: Path, host: str):
    ledger = _prov1_ledger(
        tmp_path,
        image_source_url=f"https://{host}/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        permission_evidence="written release",
    )

    packet = build_packet(ROOT, photo_ledger=ledger)

    assert "image-specific source URL" in packet["requirements"]["missing"]
    assert "explicit permission evidence" in packet["requirements"]["missing"]


@pytest.mark.parametrize("host", ["127.0.0.2", "[::1]", "10.25.0.8"])
def test_non_public_ip_source_url_never_satisfies_source_requirement(tmp_path: Path, host: str):
    ledger = _prov1_ledger(tmp_path, image_source_url=f"https://{host}/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp")

    packet = build_packet(ROOT, photo_ledger=ledger)

    assert "image-specific source URL" in packet["requirements"]["missing"]


@pytest.mark.parametrize(
    "url",
    [
        "https://intranet/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "https://rights.corp/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "https://printer.local/image.webp",
        "https://2130706433/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "https://[::1/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
    ],
)
def test_non_public_or_malformed_source_url_fails_closed(tmp_path: Path, url: str):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path, image_source_url=url))

    assert "image-specific source URL" in packet["requirements"]["missing"]


def test_unrelated_entity_citation_never_satisfies_image_source_requirement(tmp_path: Path):
    packet = build_packet(ROOT, json_path=_json_with_unrelated_entity_citation(tmp_path), photo_ledger=_prov1_ledger(tmp_path))

    assert "image-specific source URL" in packet["requirements"]["missing"]


@pytest.mark.parametrize("claim", ["yes", "written release"])
def test_free_text_rights_claim_never_satisfies_permission_requirement(tmp_path: Path, claim: str):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path, permission_evidence=claim))

    assert "explicit permission evidence" in packet["requirements"]["missing"]


def test_copyright_attribution_is_retained_but_not_rehost_authorization(tmp_path: Path):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path))

    assert "license or re-host scope" in packet["requirements"]["missing"]
    assert packet["ledgerEvidence"][0]["license"] == "Bản quyền thuộc tác giả và Báo Vĩnh Long"


@pytest.mark.parametrize(
    "license",
    [
        "Not public domain",
        "Not CC BY 4.0",
        "CC BY 4.0 not permitted",
        "No Creative Commons license",
        "Creative Commons is unavailable",
        "Public Domain Mark 1.0 - all rights reserved",
        "Creative Commons licenses are not available",
        "Creative Commons information - all rights reserved",
        "Not licensed for re-hosting",
        "reuse prohibited",
        "no permission to re-host",
        "Re-host prohibited",
        "Reuse not permitted",
        "Not authorized for reuse",
        "No re-host rights granted",
    ],
)
def test_negative_rights_statement_never_satisfies_rehost_scope(tmp_path: Path, license: str):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path, license=license))

    assert "license or re-host scope" in packet["requirements"]["missing"]


@pytest.mark.parametrize(
    "license",
    [
        pytest.param("CC BY 4.0 prohibited", id="license-before-prohibited"),
        pytest.param("Prohibited: CC BY 4.0", id="prohibited-before-license"),
        pytest.param("CC BY 4.0 forbidden", id="license-before-forbidden"),
        pytest.param("Forbidden under CC BY 4.0", id="forbidden-before-license"),
        pytest.param("CC BY 4.0 denied", id="license-before-denied"),
        pytest.param("Denied: CC BY 4.0", id="denied-before-license"),
        pytest.param("Public Domain Mark 1.0 prohibited", id="public-domain-prohibited"),
        pytest.param("Unavailable: Public Domain Mark 1.0", id="unavailable-before-license"),
        pytest.param("CC BY-SA 4.0 unavailable", id="license-before-unavailable"),
        pytest.param("All rights reserved; CC0 1.0", id="reserved-before-license"),
        pytest.param("CC BY 4.0; no permission", id="license-before-no-permission"),
        pytest.param("No permission; CC BY 4.0", id="no-permission-before-license"),
        pytest.param("CC BY 4.0; not authorized", id="license-before-not-authorized"),
        pytest.param("Not permitted; CC BY 4.0", id="not-permitted-before-license"),
        pytest.param("CC BY 4.0; cannot reuse", id="license-before-cannot"),
        pytest.param("May not republish; CC BY 4.0", id="may-not-before-license"),
        pytest.param("Permitted to re-host; permission denied", id="grant-before-denial"),
        pytest.param("No permission; permitted to re-host", id="denial-before-grant"),
    ],
)
def test_denial_anywhere_overrides_concrete_license_or_grant(tmp_path: Path, license: str):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path, license=license))

    assert "license or re-host scope" in packet["requirements"]["missing"]


def test_affirmative_license_statement_satisfies_rehost_scope(tmp_path: Path):
    packet = build_packet(
        ROOT,
        photo_ledger=_prov1_ledger(tmp_path, license="Licensed under CC BY 4.0 for re-hosting"),
    )

    assert "license or re-host scope" not in packet["requirements"]["missing"]


@pytest.mark.parametrize(
    "license",
    [
        "CC0 1.0",
        "CC BY 4.0",
        "CC BY-SA 4.0",
        "CC BY-NC-ND 4.0",
        "CC BY-NC-ND 4.0 for non-commercial use",
        "Public Domain Mark 1.0",
        "Permitted to re-host for this project",
        "Allowed to re-host non-commercially",
        "Licensed under CC BY 4.0",
        "CC BY 4.0 notwithstanding attribution terms",
        "Được phép tái sử dụng cho dự án này",
        "Cho phép tái lưu trữ trên trang này",
    ],
)
def test_affirmative_rehost_grant_satisfies_rehost_scope(tmp_path: Path, license: str):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path, license=license))

    assert "license or re-host scope" not in packet["requirements"]["missing"]


@pytest.mark.parametrize("license", ["creative commons", "public domain"])
def test_bare_license_label_never_satisfies_rehost_scope(tmp_path: Path, license: str):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path, license=license))

    assert "license or re-host scope" in packet["requirements"]["missing"]


def test_complete_fixture_evidence_is_still_non_authorizing(tmp_path: Path):
    ledger = _prov1_ledger(
        tmp_path,
        image_source_url="https://baovinhlong.com.vn/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        permission_evidence="owner-record:IMG-2026-001",
    )
    json_path = _json_with_complete_metadata(tmp_path)

    packet = build_packet(ROOT, json_path=json_path, photo_ledger=ledger)

    assert packet["status"] == "ready_for_owner_review"
    assert packet["requirements"]["missing"] == []
    assert packet["mutationAllowed"] is False
    assert all(item["mutationAllowed"] is False for item in packet["evidenceChecklist"])


@pytest.mark.parametrize(
    "permission_evidence",
    ["https://baovinhlong.com.vn/rights/lang-nghe-san-xuat-chi-xo-dua-an-thanh", "owner-record:IMG-2026-001"],
)
def test_traceable_permission_reference_satisfies_permission_requirement(tmp_path: Path, permission_evidence: str):
    packet = build_packet(ROOT, photo_ledger=_prov1_ledger(tmp_path, permission_evidence=permission_evidence))

    assert "explicit permission evidence" not in packet["requirements"]["missing"]


@pytest.mark.parametrize(
    "permission_evidence",
    [
        "https://intranet/rights/lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "https://rights.corp/rights/lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "https://printer.local/rights/lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "https://2130706433/rights/lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "https://[::1/rights/lang-nghe-san-xuat-chi-xo-dua-an-thanh",
    ],
)
def test_non_public_or_malformed_permission_url_fails_closed(
    tmp_path: Path, permission_evidence: str
):
    packet = build_packet(
        ROOT,
        photo_ledger=_prov1_ledger(
            tmp_path, permission_evidence=permission_evidence
        ),
    )

    assert "explicit permission evidence" in packet["requirements"]["missing"]


def test_conflicting_matching_license_evidence_never_satisfies_rehost_scope(
    tmp_path: Path,
):
    common = {
        "entity_id": "lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "image": "web-nuxt/public/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
    }
    ledger = _write_ledger(
        tmp_path,
        [
            {**common, "license": "CC BY 4.0"},
            {**common, "license": "Reuse prohibited"},
        ],
    )

    packet = build_packet(ROOT, photo_ledger=ledger)

    assert "license or re-host scope" in packet["requirements"]["missing"]
    assert {row["license"] for row in packet["ledgerEvidence"]} == {
        "CC BY 4.0",
        "Reuse prohibited",
    }


def test_matching_photo_ledger_rows_render_identically_after_reordering(tmp_path: Path):
    first_row = {
        "entity_id": "lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "image": "web-nuxt/public/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "license": "CC BY 4.0",
        "image_source_url": "https://baovinhlong.com.vn/images/a.webp",
        "permission_evidence": "owner-record:IMG-2026-001",
    }
    second_row = {**first_row, "image_source_url": "https://baovinhlong.com.vn/images/b.webp", "permission_evidence": "owner-record:IMG-2026-002"}
    ledger_path = _write_ledger(tmp_path / "ledger", [second_row, first_row])
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    first = build_packet(ROOT, first_path, photo_ledger=ledger_path)
    _write_ledger(ledger_path.parent, [first_row, second_row])
    second = build_packet(ROOT, second_path, photo_ledger=ledger_path)

    assert first["ledgerEvidence"] == second["ledgerEvidence"]
    assert first["requirements"] == second["requirements"]
    assert first["evidenceChecklist"] == second["evidenceChecklist"]
    assert first["inputs"]["photoLedger"]["canonicalEvidenceSha256"] == second["inputs"]["photoLedger"]["canonicalEvidenceSha256"]
    assert first["inputs"]["photoLedger"]["sha256"] != second["inputs"]["photoLedger"]["sha256"]
    assert first_path.read_bytes() != second_path.read_bytes()
    assert next(item for item in first["evidenceChecklist"] if item["requirement"] == "image-specific source URL")["observedValue"] == "https://baovinhlong.com.vn/images/a.webp"


def test_canonical_evidence_digest_ignores_unrelated_rows_and_unused_fields(
    tmp_path: Path,
):
    matching = {
        "entity_id": "lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "image": "web-nuxt/public/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "author": "Trần Phước",
        "source": "Báo Vĩnh Long",
        "license": "CC BY 4.0",
        "image_source_url": "https://baovinhlong.com.vn/images/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "unused_note": "first",
    }
    unrelated = {
        "entity_id": "not-lang-nghe-san-xuat-chi-xo-dua-an-thanh",
        "image": "web-nuxt/public/img/entities/not-lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
        "license": "CC BY 4.0",
        "unused_note": "before",
    }
    ledger = _write_ledger(tmp_path, [matching, unrelated])
    first = build_packet(ROOT, photo_ledger=ledger)

    ledger = _write_ledger(
        tmp_path,
        [
            {**unrelated, "unused_note": "after", "extra": "changed"},
            {**matching, "unused_note": "second"},
        ],
    )
    second = build_packet(ROOT, photo_ledger=ledger)

    assert first["ledgerEvidence"] == second["ledgerEvidence"]
    assert (
        first["inputs"]["photoLedger"]["canonicalEvidenceSha256"]
        == second["inputs"]["photoLedger"]["canonicalEvidenceSha256"]
    )
    assert (
        first["inputs"]["photoLedger"]["sha256"]
        != second["inputs"]["photoLedger"]["sha256"]
    )


def test_different_image_ledger_row_never_satisfies_target_requirements(tmp_path: Path):
    ledger = _write_ledger(
        tmp_path,
        [
            {
                "entity_id": "lang-nghe-san-xuat-chi-xo-dua-an-thanh",
                "image": "web-nuxt/public/img/entities/not-lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
                "author": "Other author",
                "source": "Other publisher",
                "license": "CC BY 4.0",
                "image_source_url": "https://baovinhlong.com.vn/images/not-lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
                "permission_evidence": "owner-record:IMG-2026-999",
            }
        ],
    )

    packet = build_packet(ROOT, photo_ledger=ledger)

    assert packet["ledgerEvidence"] == []
    assert {"image-specific source URL", "license or re-host scope", "explicit permission evidence"}.issubset(
        packet["requirements"]["missing"]
    )


@pytest.mark.parametrize("images", [None, [], [None], [{"path": "/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp"}]])
def test_packet_fails_closed_when_target_has_no_valid_image(tmp_path: Path, images: object):
    with pytest.raises(ProvenanceReviewError):
        build_packet(ROOT, json_path=_json_with_target_images(tmp_path, images))


@pytest.mark.parametrize("image", [None, "", 7, {"path": "/img/entities/lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp"}])
def test_missing_or_malformed_ledger_image_never_matches_target_image(tmp_path: Path, image: object):
    ledger = _write_ledger(
        tmp_path,
        [
            {
                "entity_id": "lang-nghe-san-xuat-chi-xo-dua-an-thanh",
                "image": image,
                "author": "Other author",
                "source": "Other publisher",
                "license": "CC BY 4.0",
                "image_source_url": "https://baovinhlong.com.vn/images/not-lang-nghe-san-xuat-chi-xo-dua-an-thanh.webp",
                "permission_evidence": "owner-record:IMG-2026-999",
            }
        ],
    )

    packet = build_packet(ROOT, photo_ledger=ledger)

    assert packet["ledgerEvidence"] == []
    assert {"image-specific source URL", "license or re-host scope", "explicit permission evidence"}.issubset(
        packet["requirements"]["missing"]
    )


def test_photo_ledger_input_sha256_is_the_raw_file_digest(tmp_path: Path):
    ledger = _prov1_ledger(tmp_path, license="CC BY 4.0")

    packet = build_packet(ROOT, photo_ledger=ledger)

    assert packet["inputs"]["photoLedger"]["sha256"] == _sha(ledger)
    assert packet["inputs"]["photoLedger"]["canonicalEvidenceSha256"] != _sha(ledger)


def test_packet_rendering_is_deterministic_and_atomically_replaced(tmp_path: Path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    ledger = _prov1_ledger(tmp_path)
    first = build_packet(ROOT, first_path, photo_ledger=ledger)
    second = build_packet(ROOT, second_path, photo_ledger=ledger)

    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()
    assert not list(tmp_path.glob("*.tmp"))


def test_packet_bytes_use_utf8_lf_and_end_in_exactly_one_lf(tmp_path: Path):
    output = tmp_path / "packet.json"

    build_packet(ROOT, output, photo_ledger=_prov1_ledger(tmp_path))

    raw = output.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_packet_fails_closed_on_malformed_json(tmp_path: Path):
    malformed = tmp_path / "data.json"
    malformed.write_text("{", encoding="utf-8")

    with pytest.raises(ProvenanceReviewError, match="JSON fixture"):
        build_packet(ROOT, json_path=malformed)


def test_packet_fails_closed_when_target_entity_is_missing(tmp_path: Path):
    payload = json.loads(JSON_STORE.read_text(encoding="utf-8"))
    payload["entities"] = [item for item in payload["entities"] if item["id"] != "prov-1"]
    missing = tmp_path / "data.json"
    missing.write_text(json.dumps(payload), encoding="utf-8")

    packet = build_packet(
        ROOT,
        json_path=missing,
        entity_id="prov-1",
        image_path="/img/entities/prov-1.webp",
    )
    assert packet == {
        "schemaVersion": 1,
        "mode": "read-only-image-provenance-review",
        "status": "target_absent",
        "mutationAllowed": False,
        "target": {"entityId": "prov-1", "imagePath": "/img/entities/prov-1.webp"},
        "supersededBy": "batch-21-media-truth-v1",
        "evidenceChecklist": [],
    }


def test_cli_emits_target_absent_summary_without_requirements_key(tmp_path, capsys):
    payload = json.loads(JSON_STORE.read_text(encoding="utf-8"))
    payload["entities"] = [item for item in payload["entities"] if item["id"] != "prov-1"]
    missing = tmp_path / "data.json"
    missing.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "packet.json"

    assert provenance_main([
        "--root", str(ROOT),
        "--json", str(missing),
        "--entity-id", "prov-1",
        "--image-path", "/img/entities/prov-1.webp",
        "--output", str(output),
    ]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary == {
        "status": "target_absent",
        "missingRequirementCount": 0,
        "mutationAllowed": False,
    }


def test_packet_fails_closed_when_photo_ledger_is_missing(tmp_path: Path):
    with pytest.raises(ProvenanceReviewError, match="photo ledger"):
        build_packet(ROOT, photo_ledger=tmp_path / "missing.json")


def test_packet_refuses_to_overwrite_any_input(tmp_path: Path):
    json_path = _json_with_complete_metadata(tmp_path)
    before = json_path.read_bytes()

    with pytest.raises(ProvenanceReviewError, match="output collides"):
        build_packet(ROOT, output=json_path, json_path=json_path)

    assert json_path.read_bytes() == before


@pytest.mark.parametrize(
    "suffix",
    ["-wal", "-shm", "-journal", ".reconciliation.lock"],
)
def test_packet_refuses_protected_sqlite_sidecar_and_lock_outputs(
    tmp_path: Path, suffix: str
):
    root = _isolated_review_root(tmp_path)
    database = root / "agent/data/vinhlong360.db"
    output = database.with_name(f"{database.name}{suffix}")
    assert not output.exists()

    with pytest.raises(ProvenanceReviewError, match="output collides"):
        build_packet(root, output=output)

    assert not output.exists()
