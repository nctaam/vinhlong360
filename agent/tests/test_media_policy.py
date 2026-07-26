from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException, Response


AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))


def _policy():
    try:
        return importlib.import_module("media_policy")
    except ModuleNotFoundError:
        pytest.fail("media_policy must own the canonical AI-only media contract")


def test_media_policy_owns_exact_source_triples_and_shared_error_detail():
    policy = _policy()

    assert policy.ENTITY_AI_SOURCE == (
        "ai-generated",
        "entity-editorial",
        "entity-ai",
    )
    assert policy.ENTITY_PLACEHOLDER_SOURCE == (
        "placeholder",
        "generated-placeholder",
        "entity-placeholder",
    )
    assert policy.REVIEW_UGC_SOURCE == (
        "user-uploaded",
        "review-ugc",
        "ugc-photo",
    )
    assert policy.POST_UGC_SOURCE == (
        "user-uploaded",
        "post-ugc",
        "ugc-photo",
    )
    assert policy.AI_ONLY_MEDIA_DETAIL["code"] == "ai_only_media"
    assert policy.AI_ONLY_MEDIA_DETAIL["message"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/img/entities/ok.webp", True),
        ("/img/entities/ben-ninh-kieu-2.webp", True),
        ("/img/entities/UPPER.webp", False),
        ("/img/entities/under_score.webp", False),
        ("/img/entities/nested/ok.webp", False),
        ("/img/entities/ok.jpg", False),
        ("/img/entities/ok.webp?size=md", False),
        ("/img/entities/ok.webp#hero", False),
        ("https://cdn.example/ok.webp", False),
        (None, False),
    ],
)
def test_legacy_entity_images_require_the_canonical_ai_path(
    value: object,
    expected: bool,
):
    assert _policy().is_canonical_legacy_entity_image(value) is expected


def test_renderable_entity_descriptors_allow_only_ai_and_placeholders():
    policy = _policy()

    assert policy.is_renderable_entity_descriptor({
        "source_class": "ai-generated",
        "source_kind": "entity-editorial",
        "disclosure_key": "entity-ai",
    })
    assert policy.is_renderable_entity_descriptor({
        "source_class": "placeholder",
        "source_kind": "generated-placeholder",
        "disclosure_key": "entity-placeholder",
    })
    assert not policy.is_renderable_entity_descriptor({
        "source_class": "user-uploaded",
        "source_kind": "review-ugc",
        "disclosure_key": "ugc-photo",
    })
    assert not policy.is_renderable_entity_descriptor({
        "source_class": "unknown",
        "source_kind": "entity-editorial",
        "disclosure_key": "entity-ai",
    })


def _assert_ai_only_error(call):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(call())
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == _policy().AI_ONLY_MEDIA_DETAIL


@pytest.mark.parametrize("operation", ["post", "draft-create", "draft-update"])
def test_social_non_ai_images_are_rejected_before_rate_or_database_mutation(
    monkeypatch,
    operation: str,
):
    import social

    def unexpected_side_effect(*_args, **_kwargs):
        pytest.fail("social mutation path ran before the AI-only media rejection")

    monkeypatch.setattr(social, "check_rate", unexpected_side_effect)
    user = {"id": "00000000-0000-0000-0000-000000000001"}

    if operation == "post":
        body = social.CreatePost(
            content="Noi dung hop le cho bai viet",
            images=["/uploads/community.webp"],
        )
        _assert_ai_only_error(lambda: social.create_post(body, user=user))
    elif operation == "draft-create":
        body = social.DraftPost(
            content="Ban nhap co anh cong dong",
            images=["https://cdn.example/community.webp"],
        )
        _assert_ai_only_error(lambda: social.save_draft(body, user=user))
    else:
        body = social.DraftPost(
            content="Cap nhat ban nhap co anh",
            images=["/uploads/community.webp"],
        )
        _assert_ai_only_error(
            lambda: social.update_draft(
                "00000000-0000-0000-0000-000000000002",
                body,
                user=user,
            )
        )


def test_social_upload_is_rejected_before_reading_or_storing_the_file(monkeypatch):
    import social

    def unexpected_side_effect(*_args, **_kwargs):
        pytest.fail("social upload side effect ran before the AI-only rejection")

    class UnreadableUpload:
        async def read(self, *_args, **_kwargs):
            pytest.fail("social upload read the file before the AI-only rejection")

    monkeypatch.setattr(social, "check_rate", unexpected_side_effect)
    monkeypatch.setattr(social.storage, "upload_image", unexpected_side_effect)

    _assert_ai_only_error(
        lambda: social.upload_image(
            UnreadableUpload(),
            user={"id": "00000000-0000-0000-0000-000000000001"},
        )
    )


def test_public_events_project_entity_media_before_response(monkeypatch):
    import public_api

    source = {
        "id": "event-1",
        "name": "Su kien cong khai",
        "type": "event",
        "status": "published",
        "verified": True,
        "images": [
            "https://cdn.example/user.webp",
            "/img/entities/event-1.webp",
        ],
        "attributes": {"date_start_iso": "2099-01-01"},
    }
    monkeypatch.setattr(public_api.db, "list_entities", lambda **_kwargs: [source])

    result = asyncio.run(public_api.list_events(
        Response(),
        area=None,
        include_past=True,
        limit=50,
    ))

    event = result["events"][0]
    assert "images" not in event
    assert [descriptor["url"] for descriptor in event["image_descriptors"]] == [
        "/img/entities/event-1.webp",
    ]
    assert source["images"] == [
        "https://cdn.example/user.webp",
        "/img/entities/event-1.webp",
    ]
