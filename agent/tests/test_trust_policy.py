from __future__ import annotations

import json

import pytest


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        ({"partner_verified": True}, "unknown"),
        ({"verified_at": "2026-07-01T00:00:00Z"}, "unknown"),
        (
            {"partner_verified": True, "verified_at": "not-a-timestamp"},
            "unknown",
        ),
        (
            {
                "partner_verified": True,
                "verified_at": "2026-07-01T00:00:00Z",
            },
            "verified",
        ),
    ],
)
def test_verified_requires_verification_evidence_and_verified_at(entity, expected):
    from trust_policy import derive_source_tier

    assert derive_source_tier(entity) == expected


def test_official_community_and_unknown_remain_distinct():
    from trust_policy import derive_source_tier

    assert derive_source_tier({"official": True, "verified_at": None}) == "official"
    assert (
        derive_source_tier(
            {"source_class": "user-uploaded", "moderation_status": "approved"}
        )
        == "community"
    )
    assert derive_source_tier({"moderation_status": "approved"}) == "unknown"


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        ({"updated_at": "2026-07-27T00:00:00Z"}, "fresh"),
        ({"updated_at": "2026-04-01T00:00:00Z"}, "aging"),
        ({"updated_at": "2020-01-01T00:00:00Z"}, "stale"),
        ({"updated_at": "not-a-timestamp"}, "unknown"),
        ({}, "unknown"),
    ],
)
def test_freshness_uses_normalized_recommendation_timestamps(entity, expected):
    from trust_policy import derive_freshness

    assert derive_freshness(entity, now="2026-07-28T00:00:00Z") == expected


def test_freshness_prefers_verification_time_without_changing_source_tier():
    from trust_policy import derive_freshness, derive_source_tier

    entity = {
        "partner_verified": True,
        "verified_at": "2026-07-01T00:00:00Z",
        "updated_at": "2020-01-01T00:00:00Z",
    }

    assert derive_source_tier(entity) == "verified"
    assert derive_freshness(entity, now="2026-07-28T00:00:00Z") == "fresh"


def test_entity_detail_freshness_still_ignores_import_updated_at():
    from public_api import _build_source_freshness

    result = _build_source_freshness({"updatedAt": "2026-07-27T00:00:00Z"})

    assert result["freshness_status"] == "unknown"
    assert result["verified_at"] is None


def test_explanation_prioritizes_explicit_interests_and_drops_sensitive_input():
    from trust_policy import build_explanation

    entity = {
        "id": "entity-1",
        "score": 99.7,
        "raw_query": "secret coconut query",
        "metadata": {"ip": "203.0.113.10", "latitude": 10.25},
    }
    preferences = {
        "personalization_enabled": True,
        "region_label": "Vĩnh Long",
        "explicit_interests": ["food", "culture"],
        "derived_age_band": "25_34",
        "exact_age": 31,
        "location_source": "gps",
        "location_enabled": True,
    }

    explanation = build_explanation(
        entity,
        [
            "Cùng khu vực bạn hay xem",
            "Khớp sở thích Ẩm thực",
            "secret coconut query",
        ],
        preferences,
    )

    assert explanation == {
        "primary_reason": "Phù hợp với sở thích bạn đã chọn",
        "reasons": [
            "Phù hợp với sở thích bạn đã chọn",
            "Cùng khu vực bạn quan tâm",
        ],
        "region_label": "Vĩnh Long",
        "explicit_interests": ["food", "culture"],
        "derived_age_band": "25_34",
    }
    serialized = json.dumps(explanation, ensure_ascii=True).lower()
    for forbidden in (
        "secret coconut query",
        "203.0.113.10",
        "10.25",
        "exact_age",
        '"score"',
        "metadata",
        '"gps"',
    ):
        assert forbidden not in serialized


def test_explanation_omits_personal_signals_when_personalization_is_disabled():
    from trust_policy import build_explanation

    explanation = build_explanation(
        {},
        ["untrusted arbitrary reason"],
        {
            "personalization_enabled": False,
            "region_label": "Vĩnh Long",
            "location_source": "manual",
            "explicit_interests": ["food"],
            "derived_age_band": "25_34",
        },
    )

    assert explanation == {
        "primary_reason": "Được cộng đồng quan tâm",
        "reasons": ["Được cộng đồng quan tâm"],
        "region_label": "Vĩnh Long",
    }


def test_scoring_labels_only_matching_explicit_interests_as_explicit():
    import public_api

    profile = {
        "explicit_interests": ["food"],
        "interest_scores": {"food": 1_000_000.0, "culture": 10.0},
        "area_scores": {},
        "type_scores": {},
        "recent_entity_ids": [],
    }

    _, explicit_reasons = public_api._score_candidate(
        {"id": "food-1", "type": "restaurant", "attributes": {}},
        profile,
        "home",
        None,
        "",
    )
    _, inferred_reasons = public_api._score_candidate(
        {"id": "culture-1", "type": "attraction", "attributes": {}},
        profile,
        "home",
        None,
        "",
    )

    assert explicit_reasons[0] == "Khớp sở thích ẩm thực"
    assert "Khớp sở thích" not in " ".join(inferred_reasons)
    assert "Hợp với nội dung bạn quan tâm" in inferred_reasons


def test_explicit_interest_reason_stays_first_when_other_signals_also_match():
    import public_api

    _, reasons = public_api._score_candidate(
        {
            "id": "food-1",
            "type": "restaurant",
            "area": "vinh-long",
            "attributes": {},
        },
        {
            "explicit_interests": ["food"],
            "interest_scores": {"food": 1_000_000.0},
            "area_scores": {"vinh-long": 50.0},
            "type_scores": {"restaurant": 5.0},
            "recent_entity_ids": [],
        },
        "home",
        None,
        "",
    )

    assert reasons[0] == "Khớp sở thích ẩm thực"


def test_contextual_cards_add_safe_projection_and_keep_legacy_reason(monkeypatch):
    import public_api

    entity = {
        "id": "entity-1",
        "name": "Chợ nổi",
        "type": "attraction",
        "official": True,
        "updated_at": "2020-01-01T00:00:00Z",
        "attributes": {},
    }
    preference_snapshot = {
        "personalization_enabled": True,
        "region_label": "Vĩnh Long",
        "explicit_interests": ["food"],
        "derived_age_band": "25_34",
    }
    monkeypatch.setattr(public_api, "_get_public_entity", lambda _entity_id: None)
    monkeypatch.setattr(
        public_api,
        "_build_user_interest_profile",
        lambda *_args, **_kwargs: {
            "personalization_enabled": True,
            "preference_snapshot": preference_snapshot,
        },
    )
    monkeypatch.setattr(
        public_api,
        "_gather_recommendation_candidates",
        lambda *_args, **_kwargs: {"entity-1": entity},
    )
    monkeypatch.setattr(
        public_api,
        "_score_candidate",
        lambda *_args, **_kwargs: (
            100.0,
            ["Cùng khu vực bạn hay xem", "Khớp sở thích Ẩm thực"],
        ),
    )
    monkeypatch.setattr(public_api, "_enrich_place", lambda _entities: None)

    response = public_api._contextual_recommendations(
        "user-1", "home", None, "secret coconut query", 1
    )

    card = response["items"][0]
    assert card["reason_vi"] == "Cùng khu vực bạn hay xem"
    assert card["recommendation_reasons"] == [
        "Cùng khu vực bạn hay xem",
        "Khớp sở thích Ẩm thực",
    ]
    assert card["source_tier"] == "official"
    assert card["freshness_status"] == "stale"
    assert (
        card["explanation"]["primary_reason"]
        == "Phù hợp với sở thích bạn đã chọn"
    )
    assert "secret coconut query" not in json.dumps(
        card["explanation"], ensure_ascii=True
    ).lower()


def test_public_similar_card_keeps_reason_vi_when_preferences_are_missing():
    import public_api

    card = public_api._entity_card_shape(
        {
            "id": "entity-1",
            "name": "Chợ nổi",
            "type": "attraction",
            "source_class": "user-uploaded",
            "updated_at": "2026-07-27T00:00:00Z",
        },
        score=0.75,
        reason_vi="Cung khu vuc kham pha",
    )

    assert card["reason_vi"] == "Cung khu vuc kham pha"
    assert card["source_tier"] == "community"
    assert card["freshness_status"] == "fresh"
    assert card["explanation"]["primary_reason"] == "Cùng khu vực khám phá"
