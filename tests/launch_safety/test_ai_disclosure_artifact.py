import json
from pathlib import Path

from scripts.package_launch_release import find_duplicate_artifacts


REPO_ROOT = Path(__file__).resolve().parents[2]
DISCLOSURE_PATH = REPO_ROOT / "config" / "ai-disclosure.json"
DISCLOSURE_FIELDS = {
    "short_label",
    "full_disclosure",
    "accessible_description_key",
}
EXPECTED_DISCLOSURE = {
    "schema_version": 1,
    "revision": "ai-disclosure-v1",
    "entity_ai": {
        "short_label": "Minh họa AI",
        "full_disclosure": "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.",
        "accessible_description_key": "entity-ai-full",
    },
    "placeholder": {
        "short_label": None,
        "full_disclosure": "Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.",
        "accessible_description_key": "entity-placeholder-full",
    },
    "ugc_photo": {
        "short_label": "Ảnh người dùng",
        "full_disclosure": "Ảnh do người dùng cung cấp.",
        "accessible_description_key": "ugc-photo-full",
    },
    "forbidden_entity_image_claims": [
        "ảnh thật",
        "real photo",
        "documentary photo",
        "on-site photo",
        "ảnh chụp tại chỗ",
    ],
}


def _reject_duplicate_keys(pairs):
    parsed = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"duplicate JSON key: {key}")
        parsed[key] = value
    return parsed


def _load_disclosure():
    return json.loads(
        DISCLOSURE_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )


def test_ai_disclosure_contains_exact_reviewed_schema_and_copy():
    disclosure = _load_disclosure()

    assert type(disclosure) is dict
    assert set(disclosure) == {
        "schema_version",
        "revision",
        "entity_ai",
        "placeholder",
        "ugc_photo",
        "forbidden_entity_image_claims",
    }
    assert disclosure == EXPECTED_DISCLOSURE
    assert type(disclosure["schema_version"]) is int
    assert disclosure["schema_version"] == 1
    assert disclosure["revision"] == "ai-disclosure-v1"

    for section_name in ("entity_ai", "placeholder", "ugc_photo"):
        section = disclosure[section_name]
        assert type(section) is dict
        assert set(section) == DISCLOSURE_FIELDS
        assert type(section["full_disclosure"]) is str
        assert type(section["accessible_description_key"]) is str

    assert type(disclosure["entity_ai"]["short_label"]) is str
    assert disclosure["placeholder"]["short_label"] is None
    assert type(disclosure["ugc_photo"]["short_label"]) is str

    for field in DISCLOSURE_FIELDS:
        ugc_value = disclosure["ugc_photo"][field]
        assert ugc_value != disclosure["entity_ai"][field]
        assert ugc_value != disclosure["placeholder"][field]

    forbidden_claims = disclosure["forbidden_entity_image_claims"]
    assert type(forbidden_claims) is list
    assert forbidden_claims == [
        "ảnh thật",
        "real photo",
        "documentary photo",
        "on-site photo",
        "ảnh chụp tại chỗ",
    ]
    assert all(type(claim) is str and claim for claim in forbidden_claims)
    assert len(forbidden_claims) == len(set(forbidden_claims))


def test_ai_disclosure_exists_only_at_the_canonical_root_config_location():
    assert find_duplicate_artifacts(REPO_ROOT) == []
