from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from pydantic import ValidationError


AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

from ai_disclosure import load_ai_disclosure  # noqa: E402
from image_descriptor import (  # noqa: E402
    ImageDescriptor,
    describe_entity_image,
    describe_entity_images,
    describe_review_image,
    normalize_renderable_image_url,
)
from api_schemas import GalleryImageDescriptor, GalleryResponse  # noqa: E402


DISCLOSURE = load_ai_disclosure()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" /media/minh-họa.webp?size=large&crop=wide ", "/media/minh-họa.webp?size=large&crop=wide"),
        ("https://cdn.example/ảnh.webp?size=large", "https://cdn.example/ảnh.webp?size=large"),
        ("https://[2001:db8::1]:443/ảnh.webp", "https://[2001:db8::1]:443/ảnh.webp"),
    ],
)
def test_normalize_renderable_image_url_accepts_local_and_external_https(
    raw: str,
    expected: str,
):
    assert normalize_renderable_image_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        7,
        "",
        "   ",
        "relative/image.webp",
        "/image with-space.webp",
        "/image\twith-tab.webp",
        "/image\nwith-newline.webp",
        "/image\x1fcontrol.webp",
        "/image\x7fdel.webp",
        "/image\\backslash.webp",
        "/image.webp#fragment",
        "//cdn.example/image.webp",
        "///media/image.webp",
        "http://cdn.example/image.webp",
        "ftp://cdn.example/image.webp",
        "mailto:image@example.com",
        "https:///image.webp",
        "https://@cdn.example/image.webp",
        "https://:@cdn.example/image.webp",
        "https://%40cdn.example/image.webp",
        "https://user@cdn.example/image.webp",
        "https://user:secret@cdn.example/image.webp",
        "https://cdn.example:not-a-port/image.webp",
        "https://[2001:db8::1/image.webp",
        "https://example.com：443/image.webp",
    ],
)
def test_normalize_renderable_image_url_rejects_unsafe_or_malformed_values(raw: object):
    assert normalize_renderable_image_url(raw) is None


def test_describe_entity_image_returns_the_exact_frozen_ai_editorial_contract():
    descriptor = describe_entity_image(
        " /media/entity.webp ",
        entity_name="Chùa Phước Hậu",
        index=2,
        disclosure=DISCLOSURE,
    )

    assert descriptor == ImageDescriptor(
        url="/media/entity.webp",
        alt="Chùa Phước Hậu — ảnh minh họa 3",
        source_class="ai-generated",
        source_kind="entity-editorial",
        disclosure_key="entity-ai",
        short_label=DISCLOSURE.entity_ai.short_label,
        full_disclosure=DISCLOSURE.entity_ai.full_disclosure,
        credit=None,
        width=None,
        height=None,
    )
    with pytest.raises(AttributeError):
        descriptor.url = "/changed.webp"  # type: ignore[misc]


def test_describe_entity_image_accepts_zero_based_index_and_formats_alt_one_based():
    descriptor = describe_entity_image(
        "/media/first.webp",
        entity_name="Chùa Phước Hậu",
        index=0,
        disclosure=DISCLOSURE,
    )

    assert descriptor is not None
    assert descriptor.alt == "Chùa Phước Hậu — ảnh minh họa 1"


@pytest.mark.parametrize("invalid_disclosure", [None, object()])
def test_descriptor_requires_exact_loaded_disclosure_even_for_empty_input(
    invalid_disclosure: object,
):
    with pytest.raises(TypeError, match="disclosure must be LoadedAiDisclosure"):
        describe_entity_image(
            None,
            entity_name="Valid name",
            index=1,
            disclosure=invalid_disclosure,
        )
    with pytest.raises(TypeError, match="disclosure must be LoadedAiDisclosure"):
        describe_entity_images(
            {"name": "Valid name", "images": []},
            disclosure=invalid_disclosure,
        )


@pytest.mark.parametrize(
    "entity",
    [
        None,
        "not-an-entity",
        {"name": None, "images": ["/one.webp"]},
        {"name": "", "images": ["/one.webp"]},
        {"name": "   ", "images": ["/one.webp"]},
        {"name": "Entity", "images": "/one.webp"},
        {"name": "Entity", "images": {"url": "/one.webp"}},
        {"name": "Entity", "images": iter(["/one.webp"])},
    ],
)
def test_describe_entity_images_does_not_iterate_malformed_names_or_collections(
    entity: object,
):
    assert describe_entity_images(entity, disclosure=DISCLOSURE) == ()


def test_describe_entity_images_preserves_source_positions_and_skips_invalid_urls():
    descriptors = describe_entity_images(
        {
            "name": "Vườn trái cây",
            "images": ["/one.webp", "http://unsafe.example/two.webp", "/three.webp"],
        },
        disclosure=DISCLOSURE,
    )

    assert tuple(item.url for item in descriptors) == ("/one.webp", "/three.webp")
    assert tuple(item.alt for item in descriptors) == (
        "Vườn trái cây — ảnh minh họa 1",
        "Vườn trái cây — ảnh minh họa 3",
    )


def test_entity_and_review_images_have_distinct_source_classes():
    entity = describe_entity_image(
        "/img/entity.webp",
        entity_name="Chùa Vàm Ray",
        index=0,
        disclosure=DISCLOSURE,
    )
    review = describe_review_image(
        "/img/review.jpg",
        entity_name="Chùa Vàm Ray",
        credit="Lan",
        disclosure=DISCLOSURE,
    )

    assert entity is not None
    assert review is not None
    assert entity.source_class == "ai-generated"
    assert entity.source_kind == "entity-editorial"
    assert review == ImageDescriptor(
        url="/img/review.jpg",
        alt="Chùa Vàm Ray — ảnh đánh giá",
        source_class="user-uploaded",
        source_kind="review-ugc",
        disclosure_key="ugc-photo",
        short_label=DISCLOSURE.ugc_photo.short_label,
        full_disclosure=DISCLOSURE.ugc_photo.full_disclosure,
        credit="Lan",
        width=None,
        height=None,
    )


def _valid_api_descriptor(**overrides: object) -> dict[str, object]:
    descriptor = describe_review_image(
        "/img/review.jpg",
        entity_name="Chùa Vàm Ray",
        credit="Lan",
        disclosure=DISCLOSURE,
    )
    assert descriptor is not None
    value = asdict(descriptor)
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    "overrides",
    [
        {"extra": True},
        {"source_kind": "entity-editorial"},
        {
            "short_label": DISCLOSURE.entity_ai.short_label,
            "full_disclosure": DISCLOSURE.entity_ai.full_disclosure,
        },
        {"alt": " "},
        {"credit": " "},
        {"width": 640.5, "height": 480},
        {"width": 640, "height": None},
        {"url": "http://cdn.example/review.jpg"},
    ],
)
def test_gallery_image_response_rejects_noncanonical_descriptors(
    overrides: dict[str, object],
):
    with pytest.raises(ValidationError):
        GalleryImageDescriptor.model_validate(_valid_api_descriptor(**overrides))


@pytest.mark.parametrize(
    "triple",
    [
        ("ai-generated", "entity-editorial", "entity-ai"),
        ("placeholder", "generated-placeholder", "entity-placeholder"),
        ("user-uploaded", "review-ugc", "ugc-photo"),
        ("user-uploaded", "post-ugc", "ugc-photo"),
    ],
)
def test_gallery_image_response_accepts_only_the_documented_source_triples(
    triple: tuple[str, str, str],
):
    source_class, source_kind, disclosure_key = triple
    if disclosure_key == "entity-ai":
        copy = DISCLOSURE.entity_ai
        url = "/img/entity.webp"
        credit = None
    elif disclosure_key == "entity-placeholder":
        copy = DISCLOSURE.placeholder
        url = None
        credit = None
    else:
        copy = DISCLOSURE.ugc_photo
        url = "/img/review.jpg"
        credit = "Lan"

    descriptor = GalleryImageDescriptor.model_validate({
        "url": url,
        "alt": "Mô tả ảnh",
        "source_class": source_class,
        "source_kind": source_kind,
        "disclosure_key": disclosure_key,
        "short_label": copy.short_label,
        "full_disclosure": copy.full_disclosure,
        "credit": credit,
        "width": 640,
        "height": 480,
    })

    assert descriptor.source_kind == source_kind


def test_gallery_response_is_exactly_an_images_object():
    response = GalleryResponse.model_validate({"images": [_valid_api_descriptor()]})
    assert response.model_dump() == {"images": [_valid_api_descriptor()]}

    with pytest.raises(ValidationError):
        GalleryResponse.model_validate({"images": [], "total": 0})


def test_gallery_helpers_keep_entity_images_before_review_images():
    import public_api

    images = public_api._gallery_editorial_images({
        "name": "Chùa Vàm Ray",
        "images": ["/img/entity.webp", "http://unsafe.example/entity.webp"],
    })
    public_api._append_review_gallery_images(
        images,
        [{"images": '["/img/review.jpg"]', "display_name": "Lan"}],
        "Chùa Vàm Ray",
    )

    assert [image["source_kind"] for image in images] == [
        "entity-editorial",
        "review-ugc",
    ]
    assert GalleryResponse.model_validate({"images": images}).model_dump()["images"] == images
