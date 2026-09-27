from __future__ import annotations
import json
from pathlib import Path
import pytest
from media_provenance import SourcedPhotoEvidence, sourced_photo_evidence

CORPUS = json.loads((Path(__file__).parents[2] / "tests/fixtures/media-provenance-validator-corpus.json").read_text(encoding="utf-8"))

def valid_press_attributes():
    return dict(CORPUS[0]["attributes"])

def test_sourced_photo_evidence_requires_the_complete_rights_bundle():
    evidence = sourced_photo_evidence(valid_press_attributes())
    assert evidence == SourcedPhotoEvidence("press", "Tran Phuoc", "Bao Vinh Long", "https://baovinhlong.com.vn/images/photo.webp", "Permission granted for re-hosting", "owner-record:IMG-2026-001", "Tran Phuoc · Bao Vinh Long")

@pytest.mark.parametrize("url", ["https://user@baovinhlong.com.vn/photo.webp", "https://baovinhlong.com.vn:99999/photo.webp", "https://baovinhlong.com.vn/photo.webp#fragment"])
def test_public_provenance_url_rejects_unsafe_authority_and_fragments(url):
    from media_provenance import is_public_provenance_url
    assert not is_public_provenance_url(url)

@pytest.mark.parametrize("missing", ["image_author", "image_source", "image_source_url", "image_license", "permission_evidence"])
def test_sourced_photo_evidence_fails_closed_when_a_requirement_is_missing(missing):
    attrs = valid_press_attributes(); attrs.pop(missing)
    assert sourced_photo_evidence(attrs) is None

@pytest.mark.parametrize("row", CORPUS)
def test_shared_provenance_corpus(row):
    assert (sourced_photo_evidence(row["attributes"]) is not None) is row["accepted"]
