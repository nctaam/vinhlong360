"""B4 tests for JSON-LD structured-data expansions in seo.py.

Covers the P2/P4 SEO/GEO additions:
- BreadcrumbList is emitted on entity detail JSON-LD.
- ItemList collection route returns the expected items.
- ImageObject is emitted only when an entity has real image URLs, with
  attribution fields present only when the entity actually carries them (B6).
"""

import seo


def _by_id(entities):
    return {str(e["id"]): e for e in entities if e.get("id")}


# ── BreadcrumbList ───────────────────────────────────────────────────────────


def test_entity_jsonld_emits_breadcrumb(sample_entities):
    by_id = _by_id(sample_entities)
    cam = by_id["cam-sanh-vinh-long"]
    ld = seo.build_entity_jsonld(cam, by_id)

    assert "breadcrumb" in ld
    bc = ld["breadcrumb"]
    assert bc["@type"] == "BreadcrumbList"
    items = bc["itemListElement"]
    # Trang chủ > Sản phẩm (type) > Vĩnh Long (area) > entity
    assert items[0]["name"] == "Trang chủ"
    assert items[0]["item"] == f"{seo.SITE}/"
    names = [i["name"] for i in items]
    assert "Sản phẩm" in names  # product -> /san-pham tier
    assert "Vĩnh Long" in names  # area tier resolved via placeId
    assert items[-1]["name"] == "Cam sành Vĩnh Long"
    assert items[-1]["item"] == seo._entity_url("cam-sanh-vinh-long")
    # positions are contiguous starting at 1
    assert [i["position"] for i in items] == list(range(1, len(items) + 1))
    # type tier points to a real catalog route
    type_item = next(i for i in items if i["name"] == "Sản phẩm")
    assert type_item["item"] == f"{seo.SITE}/san-pham"


def test_breadcrumb_skips_area_when_unknown(sample_entities):
    by_id = _by_id(sample_entities)
    # An entity with no placeId/area should not get an area tier.
    orphan = {"id": "lone-event", "name": "Hội chợ", "type": "event"}
    ld = seo.build_entity_jsonld(orphan, by_id)
    names = [i["name"] for i in ld["breadcrumb"]["itemListElement"]]
    assert names == ["Trang chủ", "Lễ hội", "Hội chợ"]


# ── ItemList collection route ────────────────────────────────────────────────


def test_collection_jsonld_returns_items(sample_data):
    ld = seo.build_collection_jsonld("du-lich", sample_data)
    assert ld is not None
    assert ld["@type"] == "ItemList"
    assert ld["url"] == f"{seo.SITE}/du-lich"
    # bun-mam (dish) is in the du-lich collection types
    elements = ld["itemListElement"]
    assert ld["numberOfItems"] == len(elements)
    assert len(elements) >= 1
    urls = [el["url"] for el in elements]
    assert seo._entity_url("bun-mam") in urls
    # products/places are NOT in du-lich set
    assert seo._entity_url("cam-sanh-vinh-long") not in urls
    # positions contiguous from 1
    assert [el["position"] for el in elements] == list(range(1, len(elements) + 1))


def test_collection_jsonld_unknown_returns_none(sample_data):
    assert seo.build_collection_jsonld("khong-ton-tai", sample_data) is None


def test_collection_route_handler_unknown_raises_404(monkeypatch, sample_data):
    import pytest
    from fastapi import HTTPException
    monkeypatch.setattr(seo, "_load", lambda: sample_data)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    with pytest.raises(HTTPException) as exc_info:
        seo.collection_jsonld("khong-ton-tai")
    assert exc_info.value.status_code == 404


def test_collection_ocop_requires_ocop_attr(sample_data):
    ld = seo.build_collection_jsonld("ocop", sample_data)
    assert ld is not None
    urls = [el["url"] for el in ld["itemListElement"]]
    # cam-sanh has attributes.ocop -> included; bun-mam has no ocop -> excluded
    assert seo._entity_url("cam-sanh-vinh-long") in urls
    assert seo._entity_url("bun-mam") not in urls


def test_collection_excludes_non_public_entities(sample_data):
    data = {
        "entities": [
            {"id": "ok-stay", "name": "Homestay OK", "type": "accommodation", "confidence": 0.9},
            {"id": "prov-stay", "name": "Tạm", "type": "accommodation", "status": "provisional"},
            {"id": "unverified-stay", "name": "Chưa duyệt", "type": "accommodation", "verified": False},
        ],
        "relationships": [],
        "itineraries": [],
    }
    ld = seo.build_collection_jsonld("luu-tru", data)
    urls = [el["url"] for el in ld["itemListElement"]]
    assert seo._entity_url("ok-stay") in urls
    assert seo._entity_url("prov-stay") not in urls
    assert seo._entity_url("unverified-stay") not in urls


# ── ImageObject (B6) ─────────────────────────────────────────────────────────


def test_image_object_only_when_images_present(sample_entities):
    by_id = _by_id(sample_entities)
    # cam-sanh has one real http image -> ImageObject[]
    cam = seo.build_entity_jsonld(by_id["cam-sanh-vinh-long"], by_id)
    assert "image" in cam
    img = cam["image"]
    assert isinstance(img, list) and img[0]["@type"] == "ImageObject"
    assert img[0]["url"] == "https://example.com/cam.jpg"
    # no fabricated attribution when entity carries none (B6)
    assert "author" not in img[0]
    assert "license" not in img[0]

    # bun-mam has images: [] -> no image key at all
    bun = seo.build_entity_jsonld(by_id["bun-mam"], by_id)
    assert "image" not in bun


def test_image_object_includes_attribution_when_present():
    by_id = {}
    entity = {
        "id": "lang-nghe",
        "name": "Làng nghề",
        "type": "craft_village",
        "images": ["https://example.com/a.jpg"],
        "attributes": {
            "image_author": "Nguyễn Văn A",
            "image_license": "https://creativecommons.org/licenses/by/4.0/",
        },
    }
    ld = seo.build_entity_jsonld(entity, by_id)
    img = ld["image"][0]
    assert img["author"] == "Nguyễn Văn A"
    assert img["copyrightHolder"] == "Nguyễn Văn A"
    assert img["license"] == "https://creativecommons.org/licenses/by/4.0/"


def test_image_object_skips_non_http_values():
    out = seo._build_image_objects(["/relative/path.jpg", "data:image/png;base64,xxx", None, 42], "X", {})
    assert out == []


# ── TYPE_SCHEMA coverage ────────────────────────────────────────────────────


def test_type_schema_maps_restaurant():
    entity = {"id": "nha-hang-test", "name": "Nhà hàng test", "type": "restaurant"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Restaurant"


def test_type_schema_maps_cafe():
    entity = {"id": "cafe-test", "name": "Cafe test", "type": "cafe"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "CafeOrCoffeeShop"


def test_type_schema_maps_facility():
    entity = {"id": "facility-test", "name": "UBND test", "type": "facility"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "CivicStructure"


def test_unknown_type_falls_back_to_thing():
    entity = {"id": "unknown-type", "name": "Unknown", "type": "nonexistent_type"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Thing"


# ── 404 for entity_jsonld ───────────────────────────────────────────────────


def test_entity_jsonld_raises_404_for_missing(monkeypatch, sample_data):
    import pytest
    from fastapi import HTTPException
    monkeypatch.setattr(seo, "_load", lambda: sample_data)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    with pytest.raises(HTTPException) as exc_info:
        seo.entity_jsonld("nonexistent-entity-id")
    assert exc_info.value.status_code == 404


# ── Offer price guard ───────────────────────────────────────────────────────


def test_offer_omitted_when_price_has_no_digits():
    entity = {
        "id": "product-no-price",
        "name": "Test product",
        "type": "product",
        "attributes": {"price": ""},
    }
    ld = seo.build_entity_jsonld(entity, {})
    # Empty price string should not produce an Offer
    assert "offers" not in ld


def test_offer_emitted_when_price_has_digits():
    entity = {
        "id": "product-with-price",
        "name": "Test product",
        "type": "product",
        "attributes": {"price": "50.000 VND"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "offers" in ld
    assert ld["offers"]["price"] == "50000"
    assert ld["offers"]["priceCurrency"] == "VND"


# ── Event JSON-LD ───────────────────────────────────────────────────────────


def test_event_jsonld_reads_date_start_field():
    entity = {
        "id": "event-test",
        "name": "Test event",
        "type": "event",
        "attributes": {"date_start": "2026-03-01", "date_end": "2026-03-05"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Event"
    assert ld["startDate"] == "2026-03-01"
    assert ld["endDate"] == "2026-03-05"


def test_event_without_date_omits_startDate():
    entity = {
        "id": "event-no-date",
        "name": "Event without date",
        "type": "event",
        "attributes": {},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Event"
    assert "startDate" not in ld


# ── FoodEstablishment / Restaurant enrichment ──────────────────────────────


def test_dish_emits_serves_cuisine():
    entity = {
        "id": "bun-mam-test",
        "name": "Bún mắm",
        "type": "dish",
        "attributes": {"specialty": "Bún mắm Trà Vinh", "price_range": "30.000-50.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "FoodEstablishment"
    assert ld["servesCuisine"] == "Bún mắm Trà Vinh"
    assert ld["priceRange"] == "30.000-50.000"


def test_restaurant_emits_serves_cuisine():
    entity = {
        "id": "nha-hang-test",
        "name": "Nhà hàng Phương Nam",
        "type": "restaurant",
        "attributes": {"specialty": "Hải sản", "price_range": "100.000-300.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Restaurant"
    assert ld["servesCuisine"] == "Hải sản"
    assert ld["priceRange"] == "100.000-300.000"


def test_food_type_fallback_for_cuisine():
    entity = {
        "id": "dish-ft",
        "name": "Món test",
        "type": "dish",
        "attributes": {"food_type": "Chay"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["servesCuisine"] == "Chay"


def test_food_without_attrs_omits_cuisine():
    entity = {"id": "dish-empty", "name": "Món", "type": "dish", "attributes": {}}
    ld = seo.build_entity_jsonld(entity, {})
    assert "servesCuisine" not in ld
    assert "priceRange" not in ld


# ── LodgingBusiness enrichment ─────────────────────────────────────────────


def test_accommodation_emits_star_rating():
    entity = {
        "id": "ks-test",
        "name": "Khách sạn test",
        "type": "accommodation",
        "attributes": {"star_rating": 3, "price_range": "500.000-1.000.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "LodgingBusiness"
    assert ld["starRating"] == {"@type": "Rating", "ratingValue": "3"}
    assert ld["priceRange"] == "500.000-1.000.000"


def test_accommodation_stars_fallback():
    entity = {
        "id": "ks-stars",
        "name": "KS Stars",
        "type": "accommodation",
        "attributes": {"stars": 4},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["starRating"]["ratingValue"] == "4"


def test_accommodation_checkin_checkout():
    entity = {
        "id": "ks-time",
        "name": "KS Time",
        "type": "accommodation",
        "attributes": {"check_in": "14:00", "check_out": "12:00", "rooms": 20},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["checkinTime"] == "14:00"
    assert ld["checkoutTime"] == "12:00"
    assert ld["numberOfRooms"] == 20


def test_accommodation_amenities_list():
    entity = {
        "id": "ks-amen",
        "name": "KS Amenities",
        "type": "accommodation",
        "attributes": {"amenities": ["WiFi", "Hồ bơi", "Bãi đỗ xe"]},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert len(ld["amenityFeature"]) == 3
    assert ld["amenityFeature"][0] == {"@type": "LocationFeatureSpecification", "name": "WiFi"}


def test_accommodation_without_attrs_omits_enrichment():
    entity = {"id": "ks-empty", "name": "KS", "type": "accommodation", "attributes": {}}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "LodgingBusiness"
    assert "starRating" not in ld
    assert "priceRange" not in ld
    assert "amenityFeature" not in ld


# ── Sitemap completeness ──────────────────────────────────────────────────


def test_sitemap_includes_all_public_entities(monkeypatch, sample_data):
    monkeypatch.setattr(seo, "_load", lambda: sample_data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    for entity in sample_data["entities"]:
        eid = entity["id"]
        if entity["type"] == "place":
            assert f"/xa-phuong/{eid}" in xml, f"place {eid} missing from sitemap"
        else:
            assert f"/dia-diem/{eid}" in xml, f"entity {eid} missing from sitemap"


def test_sitemap_excludes_provisional(monkeypatch):
    data = {
        "entities": [
            {"id": "ok", "name": "OK", "type": "attraction"},
            {"id": "prov", "name": "Provisional", "type": "attraction", "status": "provisional"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    assert "/dia-diem/ok" in xml
    assert "/dia-diem/prov" not in xml
