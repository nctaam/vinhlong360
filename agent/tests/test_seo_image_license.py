"""B4 test suite: Google Images License structured data and Event AEO schema invariants."""

import seo


def test_verified_documentary_photo_emits_google_image_license_metadata():
    entity = {
        "id": "thoai-ngoc-hau",
        "name": "Thoại Ngọc Hầu",
        "type": "person",
        "images": ["/img/entities/thoai-ngoc-hau.webp"],
        "attributes": {
            "image_author": "Thành Duy",
            "image_source": "Báo Vĩnh Long",
            "image_type": "documentary",
            "is_verified_photo": True,
        },
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "image" in ld
    img = ld["image"][0]
    assert img["@type"] == "ImageObject"
    assert img["url"] == f"{seo.SITE}/img/entities/thoai-ngoc-hau.webp"
    assert img["contentUrl"] == f"{seo.SITE}/img/entities/thoai-ngoc-hau.webp"
    assert img["creator"] == {"@type": "Person", "name": "Thành Duy"}
    assert img["creditText"] == "Thành Duy · Báo Vĩnh Long"
    assert img["copyrightNotice"] == "Ảnh tư liệu báo chí: Thành Duy · Báo Vĩnh Long"
    assert img["license"] == f"{seo.SITE}/dieu-khoan-su-dung"
    assert img["acquireLicensePage"] == f"{seo.SITE}/lien-he"
    assert img["caption"] == "Ảnh: Thành Duy · Báo Vĩnh Long"


def test_unverified_or_ai_photo_does_not_emit_image_license():
    entity = {
        "id": "ai-sample",
        "name": "Mẫu AI",
        "type": "attraction",
        "images": ["/img/entities/ai-sample.webp"],
        "attributes": {},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "image" in ld
    img = ld["image"][0]
    assert "creator" not in img
    assert "creditText" not in img
    assert "copyrightNotice" not in img
    assert "license" not in img
    assert "acquireLicensePage" not in img


def test_event_schema_emits_aeo_and_free_offer():
    entity = {
        "id": "le-hoi-ok-om-bok",
        "name": "Lễ hội Ok Om Bok",
        "type": "event",
        "images": ["/img/entities/le-hoi-ok-om-bok.webp"],
        "attributes": {
            "date_start": "2026-11-23",
            "date_end": "2026-11-25",
            "image_author": "Bá Thi",
            "image_source": "Báo Trà Vinh",
            "image_type": "documentary",
            "is_verified_photo": True,
        },
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Event"
    assert ld["eventStatus"] == "https://schema.org/EventScheduled"
    assert ld["eventAttendanceMode"] == "https://schema.org/OfflineEventAttendanceMode"
    assert ld["isAccessibleForFree"] is True
    assert ld["offers"]["price"] == "0"
    assert ld["offers"]["priceCurrency"] == "VND"
    assert ld["offers"]["availability"] == "https://schema.org/InStock"
