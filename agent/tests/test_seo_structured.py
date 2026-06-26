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


def test_sitemap_includes_guide_pages(monkeypatch, sample_data):
    monkeypatch.setattr(seo, "_load", lambda: sample_data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    assert "/kham-pha/am-thuc" in xml
    assert "/kham-pha/lang-nghe" in xml


def test_sitemap_no_fake_lastmod_on_core_pages(monkeypatch, sample_data):
    monkeypatch.setattr(seo, "_load", lambda: sample_data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    # Core pages should NOT have today's date as lastmod
    import re as _re
    homepage_block = _re.search(r"<url>.*?<loc>[^<]*/</loc>.*?</url>", xml, _re.DOTALL)
    assert homepage_block
    assert "<lastmod>" not in homepage_block.group()


# ── Event enrichment ──────────────────────────────────────────────────────


def test_event_emits_status_and_attendance_mode():
    entity = {
        "id": "event-test",
        "name": "Lễ hội trái cây",
        "type": "event",
        "attributes": {"date_start": "2026-07-01"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["eventStatus"] == "https://schema.org/EventScheduled"
    assert ld["eventAttendanceMode"] == "https://schema.org/OfflineEventAttendanceMode"


def test_event_emits_organizer_when_present():
    entity = {
        "id": "event-org",
        "name": "Hội chợ OCOP",
        "type": "event",
        "attributes": {"organizer": "Sở Công Thương Vĩnh Long"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["organizer"] == {"@type": "Organization", "name": "Sở Công Thương Vĩnh Long"}


# ── TouristAttraction enrichment ──────────────────────────────────────────


def test_attraction_emits_is_accessible_for_free():
    entity = {
        "id": "att-free",
        "name": "Vườn trái cây",
        "type": "attraction",
        "attributes": {"admission": "miễn phí"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "TouristAttraction"
    assert ld["isAccessibleForFree"] is True


def test_attraction_paid_admission():
    entity = {
        "id": "att-paid",
        "name": "Khu du lịch",
        "type": "attraction",
        "attributes": {"admission": "50.000 VND"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["isAccessibleForFree"] is False


def test_attraction_without_admission_omits_field():
    entity = {"id": "att-no", "name": "Điểm", "type": "attraction", "attributes": {}}
    ld = seo.build_entity_jsonld(entity, {})
    assert "isAccessibleForFree" not in ld


# ── WebSite + Organization schema ─────────────────────────────────────────


def test_site_jsonld_returns_website_and_org():
    result = seo.site_jsonld()
    assert len(result) == 2
    website = result[0]
    assert website["@type"] == "WebSite"
    assert website["name"] == "VinhLong360"
    assert website["potentialAction"]["@type"] == "SearchAction"
    assert "search_term_string" in website["potentialAction"]["target"]["urlTemplate"]
    org = result[1]
    assert org["@type"] == "Organization"
    assert org["name"] == "VinhLong360"


# ── parse_coordinates ─────────────────────────────────────────────────────


def test_parse_coordinates_list():
    assert seo.parse_coordinates([10.25, 106.0]) == (10.25, 106.0)


def test_parse_coordinates_dict_lat_lng():
    assert seo.parse_coordinates({"lat": 10.25, "lng": 106.0}) == (10.25, 106.0)


def test_parse_coordinates_dict_latitude_longitude():
    assert seo.parse_coordinates({"latitude": 10.25, "longitude": 106.0}) == (10.25, 106.0)


def test_parse_coordinates_json_string():
    assert seo.parse_coordinates("[10.25, 106.0]") == (10.25, 106.0)


def test_parse_coordinates_transposed():
    assert seo.parse_coordinates([106.0, 10.25]) == (10.25, 106.0)


def test_parse_coordinates_none_for_invalid():
    assert seo.parse_coordinates(None) is None
    assert seo.parse_coordinates("not json") is None
    assert seo.parse_coordinates([1, 2, 3]) is None
    assert seo.parse_coordinates(42) is None


# ── _source_info ──────────────────────────────────────────────────────────


def test_source_info_string_url():
    title, url = seo._source_info({"source": "https://example.com/page"})
    assert title == "https://example.com/page"
    assert url == "https://example.com/page"


def test_source_info_string_non_url():
    title, url = seo._source_info({"source": "manual"})
    assert title == "manual"
    assert url is None


def test_source_info_dict():
    title, url = seo._source_info({"source": {"title": "Wikipedia", "url": "https://vi.wikipedia.org/wiki/X"}})
    assert title == "Wikipedia"
    assert url == "https://vi.wikipedia.org/wiki/X"


def test_source_info_list():
    title, url = seo._source_info({"source": [{"title": "First", "url": "https://example.com"}]})
    assert title == "First"
    assert url == "https://example.com"


def test_source_info_self_link_excluded():
    title, url = seo._source_info({"source": "https://vinhlong360.vn/dia-diem/x"})
    assert url is None


def test_source_info_empty():
    assert seo._source_info({}) == (None, None)
    assert seo._source_info({"source": []}) == (None, None)


# ── _same_as_values ───────────────────────────────────────────────────────


def test_same_as_includes_website():
    entity = {"attributes": {"website": "https://example.com"}}
    values = seo._same_as_values(entity)
    assert "https://example.com" in values


def test_same_as_deduplicates():
    entity = {"attributes": {"website": "https://example.com"}, "source": "https://example.com"}
    values = seo._same_as_values(entity)
    assert values.count("https://example.com") == 1


def test_same_as_excludes_self_links():
    entity = {"attributes": {"website": "https://vinhlong360.vn"}, "source": "manual"}
    values = seo._same_as_values(entity)
    assert len(values) == 1
    assert values[0] == "https://vinhlong360.vn"


# ── _safe_date ────────────────────────────────────────────────────────────


def test_safe_date_valid():
    assert seo._safe_date("2026-06-15", "fallback") == "2026-06-15"


def test_safe_date_invalid():
    assert seo._safe_date("not a date", "2026-01-01") == "2026-01-01"
    assert seo._safe_date(None, "2026-01-01") == "2026-01-01"
    assert seo._safe_date(12345, None) is None


def test_safe_date_strips_whitespace():
    assert seo._safe_date("  2026-06-15  ", None) == "2026-06-15"


# ── _is_public ────────────────────────────────────────────────────────────


def test_is_public_normal():
    assert seo._is_public({"id": "x", "type": "attraction"}) is True


def test_is_public_provisional():
    assert seo._is_public({"status": "provisional"}) is False


def test_is_public_unverified():
    assert seo._is_public({"verified": False}) is False


def test_is_public_verified_true():
    assert seo._is_public({"verified": True}) is True


# ── robots.txt ────────────────────────────────────────────────────────────


def test_robots_contains_sitemaps():
    resp = seo.robots()
    assert "sitemap-index.xml" in resp


def test_robots_disallows_api_and_seo():
    resp = seo.robots()
    assert "Disallow: /api/" in resp
    assert "Disallow: /seo/" in resp


def test_robots_disallows_admin():
    resp = seo.robots()
    assert "Disallow: /admin" in resp


# ── Media sitemap ─────────────────────────────────────────────────────────


def test_media_sitemap_includes_image_title(monkeypatch):
    data = {
        "entities": [
            {"id": "e1", "name": "Test Entity", "type": "attraction", "images": ["https://example.com/img.jpg"]},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    resp = seo.sitemap_media()
    xml = resp.body.decode()
    assert "<image:title>Test Entity</image:title>" in xml
    assert "<image:loc>https://example.com/img.jpg</image:loc>" in xml


def test_media_sitemap_excludes_non_public(monkeypatch):
    data = {
        "entities": [
            {"id": "e1", "name": "OK", "type": "attraction", "images": ["https://example.com/a.jpg"]},
            {"id": "e2", "name": "Hidden", "type": "attraction", "status": "provisional", "images": ["https://example.com/b.jpg"]},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    resp = seo.sitemap_media()
    xml = resp.body.decode()
    assert "/dia-diem/e1" in xml
    assert "/dia-diem/e2" not in xml


# ── Person type ───────────────────────────────────────────────────────────


def test_person_emits_job_title():
    entity = {
        "id": "person-test",
        "name": "Nguyễn Văn A",
        "type": "person",
        "attributes": {"role": "Nghệ nhân"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Person"
    assert ld["jobTitle"] == "Nghệ nhân"


# ── Itinerary TouristTrip ─────────────────────────────────────────────────


def test_itinerary_jsonld_basic():
    it = {
        "id": "1-ngay-vl",
        "title": "1 ngày Vĩnh Long",
        "area": "vinh-long",
        "duration": "1 ngày",
        "summary": "Trọn 1 ngày miệt vườn.",
        "stops": [
            {"id": "cam-sanh", "time": "Sáng"},
            {"id": "bun-mam", "time": "Trưa", "note": "Ăn trưa"},
        ],
    }
    by_id = {
        "cam-sanh": {"id": "cam-sanh", "name": "Cam sành", "type": "product"},
        "bun-mam": {"id": "bun-mam", "name": "Bún mắm", "type": "dish"},
    }
    ld = seo.build_itinerary_jsonld(it, by_id)
    assert ld["@type"] == "TouristTrip"
    assert ld["name"] == "1 ngày Vĩnh Long"
    assert ld["duration"] == "P1D"
    assert ld["inLanguage"] == "vi-VN"
    assert ld["itinerary"]["@type"] == "ItemList"
    assert ld["itinerary"]["numberOfItems"] == 2
    items = ld["itinerary"]["itemListElement"]
    assert items[0]["item"]["name"] == "Cam sành"
    assert items[1]["position"] == 2


def test_itinerary_jsonld_no_stops():
    it = {"id": "empty", "title": "Empty", "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert "itinerary" not in ld


def test_itinerary_duration_hours():
    it = {"id": "quick", "title": "Quick", "duration": "3 giờ", "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["duration"] == "PT3H"


def test_itinerary_endpoint_404(monkeypatch, sample_data):
    import pytest
    from fastapi import HTTPException
    monkeypatch.setattr(seo, "_load", lambda: sample_data)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    with pytest.raises(HTTPException) as exc_info:
        seo.itinerary_jsonld("nonexistent")
    assert exc_info.value.status_code == 404


# ── FAQ schema ────────────────────────────────────────────────────────────


def test_faq_jsonld_from_tips():
    entity = {
        "id": "test-faq",
        "name": "Vườn trái cây",
        "type": "attraction",
        "attributes": {
            "travel_tip": "Đến sáng sớm để có trái tươi nhất.",
            "best_time": "tháng 5-7",
        },
    }
    faq = seo.build_faq_jsonld(entity)
    assert faq is not None
    assert faq["@type"] == "FAQPage"
    assert len(faq["mainEntity"]) == 2
    q_names = [q["name"] for q in faq["mainEntity"]]
    assert any("Mẹo du lịch" in q for q in q_names)
    assert any("Thời điểm tốt nhất" in q for q in q_names)


def test_faq_jsonld_returns_none_without_tips():
    entity = {"id": "no-tips", "name": "X", "attributes": {"phone": "123"}}
    assert seo.build_faq_jsonld(entity) is None


def test_faq_jsonld_handles_list_answer():
    entity = {
        "id": "list-tip",
        "name": "Y",
        "attributes": {"travel_tip": ["Tip 1", "Tip 2"]},
    }
    faq = seo.build_faq_jsonld(entity)
    assert faq is not None
    assert "Tip 1; Tip 2" in faq["mainEntity"][0]["acceptedAnswer"]["text"]


# ── Area TouristDestination ───────────────────────────────────────────────


def test_area_jsonld_valid():
    ld = seo.build_area_jsonld("vinh-long")
    assert ld is not None
    assert ld["@type"] == "TouristDestination"
    assert ld["name"] == "Vĩnh Long"
    assert ld["containedInPlace"]["name"] == "Việt Nam"
    assert ld["inLanguage"] == "vi-VN"


def test_area_jsonld_unknown():
    assert seo.build_area_jsonld("nonexistent") is None


def test_area_endpoint_404(monkeypatch):
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        seo.area_jsonld("nonexistent")
    assert exc_info.value.status_code == 404


# ── inLanguage ────────────────────────────────────────────────────────────


def test_entity_jsonld_includes_in_language():
    entity = {"id": "x", "name": "Test", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["inLanguage"] == "vi-VN"


# ── entity_jsonld returns FAQ alongside ────────────────────────────────────


def test_entity_jsonld_endpoint_includes_faq(monkeypatch):
    data = {
        "entities": [
            {"id": "with-tip", "name": "Place", "type": "attraction",
             "attributes": {"travel_tip": "Go early"}},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    result = seo.entity_jsonld("with-tip")
    assert "@graph" in result
    types = [r.get("@type") for r in result["@graph"]]
    assert "TouristAttraction" in types
    assert "FAQPage" in types
    assert result["@context"] == "https://schema.org"
    for item in result["@graph"]:
        assert "@context" not in item


# ── _load graceful degradation ────────────────────────────────────────────


def test_load_returns_empty_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(seo, "DATA_PATH", tmp_path / "nonexistent.json")
    monkeypatch.setattr(seo, "_data", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 1)
    data = seo._load()
    assert data["entities"] == []
    assert data["relationships"] == []


# ── @id on JSON-LD ───────────────────────────────────────────────────────


def test_entity_jsonld_has_id():
    entity = {"id": "test-id", "name": "Test", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@id"] == seo._entity_url("test-id")


def test_itinerary_jsonld_has_id():
    it = {"id": "it-test", "title": "Test Trip", "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["@id"] == seo._itinerary_url("it-test")


def test_area_jsonld_has_id():
    ld = seo.build_area_jsonld("vinh-long")
    assert ld is not None
    assert "@id" in ld
    assert "khu-vuc/vinh-long" in ld["@id"]


# ── containsPlace on area JSON-LD ────────────────────────────────────────


def test_area_jsonld_contains_place_with_data():
    data = {
        "entities": [
            {"id": "e1", "name": "Entity 1", "type": "attraction", "area": "vinh-long"},
            {"id": "e2", "name": "Entity 2", "type": "dish", "area": "vinh-long"},
            {"id": "e3", "name": "Entity 3", "type": "product", "area": "ben-tre"},
            {"id": "p1", "name": "Place 1", "type": "place", "area": "vinh-long"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    ld = seo.build_area_jsonld("vinh-long", data)
    assert ld is not None
    assert "containsPlace" in ld
    names = [c["name"] for c in ld["containsPlace"]]
    assert "Entity 1" in names
    assert "Entity 2" in names
    assert "Entity 3" not in names
    assert "Place 1" not in names


def test_area_jsonld_no_contains_without_data():
    ld = seo.build_area_jsonld("vinh-long")
    assert ld is not None
    assert "containsPlace" not in ld


def test_area_jsonld_excludes_provisional_from_contains():
    data = {
        "entities": [
            {"id": "e1", "name": "OK", "type": "attraction", "area": "vinh-long"},
            {"id": "e2", "name": "Prov", "type": "attraction", "area": "vinh-long", "status": "provisional"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    ld = seo.build_area_jsonld("vinh-long", data)
    names = [c["name"] for c in ld["containsPlace"]]
    assert "OK" in names
    assert "Prov" not in names


# ── TYPE_SCHEMA validation ──────────────────────────────────────────────


def test_type_schema_all_values_are_known_schema_org_types():
    known_types = {
        "Thing", "Place", "Organization", "Person", "Event", "Product",
        "Restaurant", "CafeOrCoffeeShop", "FoodEstablishment",
        "LodgingBusiness", "TouristAttraction", "TouristTrip",
        "CivicStructure", "LocalBusiness", "LandmarksOrHistoricalBuildings",
    }
    for entity_type, schema_type in seo.TYPE_SCHEMA.items():
        assert schema_type in known_types, (
            f"TYPE_SCHEMA['{entity_type}'] = '{schema_type}' is not a known schema.org type"
        )


def test_type_schema_covers_all_data_types():
    expected = {
        "accommodation", "attraction", "cafe", "craft_village", "dish", "drink",
        "economy", "event", "experience", "facility", "history", "itinerary",
        "nature", "organization", "person", "place", "product", "restaurant",
    }
    assert set(seo.TYPE_SCHEMA.keys()) == expected


# ── Edge cases ───────────────────────────────────────────────────────────


def test_entity_jsonld_null_type_falls_back():
    entity = {"id": "null-type", "name": "Test", "type": None}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Thing"


def test_entity_jsonld_empty_type_falls_back():
    entity = {"id": "empty-type", "name": "Test", "type": ""}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Thing"


def test_entity_jsonld_list_attributes_ignored():
    entity = {"id": "list-attrs", "name": "Test", "type": "attraction", "attributes": ["not", "a", "dict"]}
    ld = seo.build_entity_jsonld(entity, {})
    assert "telephone" not in ld
    assert "openingHours" not in ld


def test_entity_jsonld_mixed_images_filtered():
    entity = {
        "id": "mixed-img",
        "name": "Test",
        "type": "attraction",
        "images": ["https://example.com/ok.jpg", None, 42, "/relative.jpg", "data:image/png;base64,xxx"],
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert len(ld["image"]) == 1
    assert ld["image"][0]["url"] == "https://example.com/ok.jpg"


def test_itinerary_jsonld_string_stops_skipped():
    it = {"id": "str-stops", "title": "Test", "stops": ["stop1", "stop2", {"id": "real", "name": "Real"}]}
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["itinerary"]["numberOfItems"] == 1
    assert ld["itinerary"]["itemListElement"][0]["item"]["name"] == "Real"


def test_collection_caps_at_100():
    entities = [
        {"id": f"e-{i}", "name": f"Entity {i}", "type": "attraction", "confidence": 0.9}
        for i in range(150)
    ]
    data = {"entities": entities, "relationships": [], "itineraries": []}
    ld = seo.build_collection_jsonld("du-lich", data)
    assert ld is not None
    assert len(ld["itemListElement"]) == 100
    assert ld["numberOfItems"] == 100


def test_parse_coordinates_deeply_nested_json():
    assert seo.parse_coordinates('{"lat":10.25,"lng":106.0}') == (10.25, 106.0)


def test_entity_jsonld_xml_safe_name():
    entity = {"id": "xss-test", "name": '<script>alert("xss")</script>', "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert "<script>" in ld["name"]


def test_entity_jsonld_no_id_uses_fallback_name():
    entity = {"id": "no-name", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["name"] == "no-name"


def test_faq_jsonld_ignores_empty_string_tip():
    entity = {"id": "empty-tip", "name": "X", "attributes": {"travel_tip": "   "}}
    assert seo.build_faq_jsonld(entity) is None


def test_safe_date_rejects_partial_date():
    assert seo._safe_date("2026-06") is None
    assert seo._safe_date("06-15-2026") is None


# ── @id on site/collection JSON-LD ───────────────────────────────────────


def test_site_jsonld_has_ids():
    result = seo.site_jsonld()
    website = result[0]
    org = result[1]
    assert website["@id"] == f"{seo.SITE}/#website"
    assert org["@id"] == f"{seo.SITE}/#organization"
    assert website["publisher"]["@id"] == f"{seo.SITE}/#organization"


def test_collection_jsonld_has_id(sample_data):
    ld = seo.build_collection_jsonld("du-lich", sample_data)
    assert ld is not None
    assert ld["@id"] == f"{seo.SITE}/du-lich"
    assert ld["isPartOf"]["@id"] == f"{seo.SITE}/#website"


def test_entity_jsonld_has_is_part_of():
    entity = {"id": "test", "name": "Test", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["isPartOf"]["@id"] == f"{seo.SITE}/#website"


# ── _parse_duration extended ─────────────────────────────────────────────


def test_parse_duration_nights():
    assert seo._parse_duration("2 đêm") == "P3D"
    assert seo._parse_duration("1 đêm") == "P2D"


def test_parse_duration_none_for_non_string():
    assert seo._parse_duration(None) is None
    assert seo._parse_duration(42) is None
    assert seo._parse_duration("random text") is None


# ── Place JSON-LD hierarchy ──────────────────────────────────────────────


def test_place_has_additional_type():
    entity = {"id": "xa-test", "name": "Xã Test", "type": "place", "level": "xa"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "Place"
    assert ld["additionalType"] == "AdministrativeArea"


def test_place_contained_in_place_parent():
    parent = {"id": "huyen-a", "name": "Huyện A", "type": "place", "level": "huyen"}
    child = {"id": "xa-b", "name": "Xã B", "type": "place", "level": "xa", "parentId": "huyen-a"}
    by_id = _by_id([parent, child])
    ld = seo.build_entity_jsonld(child, by_id)
    assert "containedInPlace" in ld
    assert ld["containedInPlace"]["name"] == "Huyện A"
    assert "huyen-a" in ld["containedInPlace"]["url"]


def test_place_contains_child_entities():
    place = {"id": "xa-c", "name": "Xã C", "type": "place", "level": "xa"}
    entity1 = {"id": "e1", "name": "Điểm 1", "type": "attraction", "placeId": "xa-c"}
    entity2 = {"id": "e2", "name": "Điểm 2", "type": "dish", "placeId": "xa-c"}
    entity3 = {"id": "e3", "name": "Điểm 3", "type": "product", "placeId": "other"}
    by_id = _by_id([place, entity1, entity2, entity3])
    ld = seo.build_entity_jsonld(place, by_id)
    assert "containsPlace" in ld
    names = [c["name"] for c in ld["containsPlace"]]
    assert "Điểm 1" in names
    assert "Điểm 2" in names
    assert "Điểm 3" not in names


def test_place_excludes_provisional_from_contains():
    place = {"id": "xa-d", "name": "Xã D", "type": "place", "level": "xa"}
    ok = {"id": "ok", "name": "OK", "type": "attraction", "placeId": "xa-d"}
    prov = {"id": "prov", "name": "Prov", "type": "attraction", "placeId": "xa-d", "status": "provisional"}
    by_id = _by_id([place, ok, prov])
    ld = seo.build_entity_jsonld(place, by_id)
    names = [c["name"] for c in ld["containsPlace"]]
    assert "OK" in names
    assert "Prov" not in names


def test_place_no_contains_when_no_children():
    place = {"id": "xa-e", "name": "Xã E", "type": "place", "level": "xa"}
    by_id = _by_id([place])
    ld = seo.build_entity_jsonld(place, by_id)
    assert "containsPlace" not in ld


# ── relatedLink from relationships ──────────────────────────────────────


def test_entity_jsonld_related_link_from_relationships():
    entities = [
        {"id": "a", "name": "A", "type": "attraction"},
        {"id": "b", "name": "B", "type": "dish"},
        {"id": "c", "name": "C", "type": "product"},
    ]
    by_id = _by_id(entities)
    relationships = [
        {"from": "a", "to": "b", "type": "near"},
        {"from": "c", "to": "a", "type": "related_to"},
    ]
    ld = seo.build_entity_jsonld(by_id["a"], by_id, relationships=relationships)
    assert "relatedLink" in ld
    assert seo._entity_url("b") in ld["relatedLink"]
    assert seo._entity_url("c") in ld["relatedLink"]


def test_entity_jsonld_no_related_link_without_relationships():
    entity = {"id": "solo", "name": "Solo", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert "relatedLink" not in ld


def test_entity_jsonld_related_link_caps_at_10():
    entities = [{"id": f"e-{i}", "name": f"E{i}", "type": "attraction"} for i in range(15)]
    entities.append({"id": "hub", "name": "Hub", "type": "attraction"})
    by_id = _by_id(entities)
    relationships = [{"from": "hub", "to": f"e-{i}", "type": "near"} for i in range(15)]
    ld = seo.build_entity_jsonld(by_id["hub"], by_id, relationships=relationships)
    assert len(ld["relatedLink"]) == 10


def test_entity_jsonld_related_link_skips_missing_entities():
    entities = [{"id": "a", "name": "A", "type": "attraction"}]
    by_id = _by_id(entities)
    relationships = [{"from": "a", "to": "nonexistent", "type": "near"}]
    ld = seo.build_entity_jsonld(by_id["a"], by_id, relationships=relationships)
    assert "relatedLink" not in ld


def test_entity_jsonld_related_link_no_duplicates():
    entities = [
        {"id": "a", "name": "A", "type": "attraction"},
        {"id": "b", "name": "B", "type": "dish"},
    ]
    by_id = _by_id(entities)
    relationships = [
        {"from": "a", "to": "b", "type": "near"},
        {"from": "a", "to": "b", "type": "related_to"},
    ]
    ld = seo.build_entity_jsonld(by_id["a"], by_id, relationships=relationships)
    assert len(ld["relatedLink"]) == 1


def test_entity_jsonld_related_link_from_id_to_id():
    """Relationships using from_id/to_id field names should work too."""
    entities = [
        {"id": "a", "name": "A", "type": "attraction"},
        {"id": "b", "name": "B", "type": "dish"},
    ]
    by_id = _by_id(entities)
    relationships = [{"from_id": "a", "to_id": "b", "type": "near"}]
    ld = seo.build_entity_jsonld(by_id["a"], by_id, relationships=relationships)
    assert "relatedLink" in ld
    assert seo._entity_url("b") in ld["relatedLink"]


def test_entity_jsonld_endpoint_passes_relationships(monkeypatch):
    data = {
        "entities": [
            {"id": "x", "name": "X", "type": "attraction"},
            {"id": "y", "name": "Y", "type": "dish"},
        ],
        "relationships": [{"from": "x", "to": "y", "type": "near"}],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    result = seo.entity_jsonld("x")
    assert "relatedLink" in result
    assert seo._entity_url("y") in result["relatedLink"]


# ── Sitemap index ───────────────────────────────────────────────────────


def test_sitemap_index_contains_both_sitemaps():
    resp = seo.sitemap_index()
    xml = resp.body.decode()
    assert "sitemap-index" not in xml or "sitemapindex" in xml
    assert f"{seo.SITE}/sitemap.xml" in xml
    assert f"{seo.SITE}/sitemap-media.xml" in xml
    assert "<sitemapindex" in xml


def test_robots_references_sitemap_index():
    resp = seo.robots()
    assert "sitemap-index.xml" in resp
    assert "sitemap.xml\n" not in resp


# ── Adversarial edge cases ──────────────────────────────────────────────


def test_entity_jsonld_unicode_name():
    entity = {"id": "unicode", "name": "Bánh tráng phơi sương 🌙", "type": "dish"}
    ld = seo.build_entity_jsonld(entity, {})
    assert "🌙" in ld["name"]
    assert ld["@type"] == "FoodEstablishment"


def test_entity_jsonld_very_long_summary_truncation():
    """Very long summary should be included as-is (JSON-LD has no length limit)."""
    entity = {"id": "long-desc", "name": "Test", "type": "attraction", "summary": "X" * 5000}
    ld = seo.build_entity_jsonld(entity, {})
    assert len(ld["description"]) == 5000


def test_entity_jsonld_coordinates_zero_zero():
    """Coordinates [0, 0] are valid (Gulf of Guinea) but unusual."""
    entity = {"id": "zero", "name": "Zero", "type": "attraction", "coordinates": [0, 0]}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["geo"]["latitude"] == 0
    assert ld["geo"]["longitude"] == 0


def test_entity_jsonld_source_with_html():
    """Source title with HTML should not be sanitized — JSON-LD handles it."""
    entity = {
        "id": "html-src",
        "name": "Test",
        "type": "attraction",
        "source": [{"title": "<b>Source</b>", "url": "https://example.com"}],
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["citation"]["name"] == "<b>Source</b>"


def test_collection_jsonld_empty_entities():
    data = {"entities": [], "relationships": [], "itineraries": []}
    ld = seo.build_collection_jsonld("du-lich", data)
    assert ld is not None
    assert ld["numberOfItems"] == 0
    assert ld["itemListElement"] == []


def test_sitemap_xml_special_chars_in_id(monkeypatch):
    """Entity IDs with special XML chars should be escaped in sitemap."""
    data = {
        "entities": [
            {"id": "test&entity<>", "name": "Test", "type": "attraction"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    assert "%26" in xml or "&amp;" in xml
    assert "%3C" in xml or "&lt;" in xml


def test_itinerary_jsonld_with_entity_ref_and_name():
    """Stop with both entityId and name — entity name wins."""
    it = {
        "id": "mixed-stop",
        "title": "Mixed",
        "stops": [{"entityId": "cam", "name": "Override Name"}],
    }
    by_id = {"cam": {"id": "cam", "name": "Cam sành", "type": "product"}}
    ld = seo.build_itinerary_jsonld(it, by_id)
    assert ld["itinerary"]["itemListElement"][0]["item"]["name"] == "Cam sành"


def test_build_entity_jsonld_multiple_same_as():
    entity = {
        "id": "multi-same",
        "name": "Multi",
        "type": "attraction",
        "source": "https://source.example.com",
        "attributes": {"website": "https://website.example.com"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert isinstance(ld["sameAs"], list)
    assert len(ld["sameAs"]) == 2


def test_event_with_place_emits_location():
    """Event with placeId should emit location."""
    place = {"id": "xa-a", "name": "Xã A", "type": "place", "area": "vinh-long"}
    event = {
        "id": "ev-1", "name": "Lễ hội", "type": "event",
        "placeId": "xa-a",
        "attributes": {"date_start": "2026-07-01"},
    }
    by_id = _by_id([place, event])
    ld = seo.build_entity_jsonld(event, by_id)
    assert "location" in ld
    assert ld["location"]["name"] == "Xã A"


# ── Collection hardening ────────────────────────────────────────────────


def test_collection_sorts_by_confidence():
    entities = [
        {"id": "low", "name": "Low", "type": "attraction", "confidence": 0.3},
        {"id": "high", "name": "High", "type": "attraction", "confidence": 0.95},
        {"id": "mid", "name": "Mid", "type": "attraction", "confidence": 0.7},
    ]
    data = {"entities": entities, "relationships": [], "itineraries": []}
    ld = seo.build_collection_jsonld("du-lich", data)
    names = [el["name"] for el in ld["itemListElement"]]
    assert names[0] == "High"


def test_collection_description_truncated():
    entity = {
        "id": "verbose", "name": "Verbose", "type": "attraction",
        "summary": "X" * 500,
    }
    data = {"entities": [entity], "relationships": [], "itineraries": []}
    ld = seo.build_collection_jsonld("du-lich", data)
    desc = ld["itemListElement"][0].get("description", "")
    assert len(desc) <= 200


def test_itinerary_jsonld_duration_none_for_unknown():
    it = {"id": "no-dur", "title": "No duration", "duration": "unknown", "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert "duration" not in ld


def test_itinerary_jsonld_location_area():
    it = {"id": "area-it", "title": "Area trip", "area": "ben-tre", "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["contentLocation"]["name"] == "Bến Tre"
    assert ld["touristType"] == "Sightseeing"


def test_area_jsonld_all_three_areas():
    for slug in ["vinh-long", "ben-tre", "tra-vinh"]:
        ld = seo.build_area_jsonld(slug)
        assert ld is not None
        assert ld["@type"] == "TouristDestination"


def test_faq_jsonld_all_four_question_types():
    entity = {
        "id": "full-faq",
        "name": "Test",
        "type": "attraction",
        "attributes": {
            "travel_tip": "Tip answer",
            "tip": "Warning answer",
            "booking_note": "Booking answer",
            "best_time": "Best time answer",
        },
    }
    faq = seo.build_faq_jsonld(entity)
    assert faq is not None
    assert len(faq["mainEntity"]) == 4


def test_product_brand_ocop_format():
    entity = {
        "id": "ocop-prod",
        "name": "Sản phẩm OCOP",
        "type": "product",
        "attributes": {"ocop": "4 sao", "price": "150.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["brand"]["name"] == "OCOP 4 sao"
    assert ld["offers"]["priceCurrency"] == "VND"


def test_lodging_amenities_skips_empty():
    entity = {
        "id": "ks-empty-amen",
        "name": "KS",
        "type": "accommodation",
        "attributes": {"amenities": ["WiFi", None, "", "Pool"]},
    }
    ld = seo.build_entity_jsonld(entity, {})
    names = [a["name"] for a in ld["amenityFeature"]]
    assert "WiFi" in names
    assert "Pool" in names
    assert None not in names
    assert "" not in names


def test_sitemap_index_has_lastmod():
    resp = seo.sitemap_index()
    xml = resp.body.decode()
    assert "<lastmod>" in xml


# ── Itinerary stop type + @id enrichment ────────────────────────────────


def test_itinerary_stop_uses_entity_schema_type():
    """Stop entity type should map to correct schema.org type."""
    it = {
        "id": "type-it",
        "title": "Type test",
        "stops": [{"entityId": "r1"}, {"entityId": "a1"}],
    }
    by_id = {
        "r1": {"id": "r1", "name": "Nhà hàng", "type": "restaurant"},
        "a1": {"id": "a1", "name": "Điểm tham quan", "type": "attraction"},
    }
    ld = seo.build_itinerary_jsonld(it, by_id)
    items = ld["itinerary"]["itemListElement"]
    assert items[0]["item"]["@type"] == "Restaurant"
    assert items[1]["item"]["@type"] == "TouristAttraction"


def test_itinerary_stop_has_id_link():
    it = {
        "id": "id-it",
        "title": "ID test",
        "stops": [{"entityId": "e1"}],
    }
    by_id = {"e1": {"id": "e1", "name": "Test", "type": "attraction"}}
    ld = seo.build_itinerary_jsonld(it, by_id)
    item = ld["itinerary"]["itemListElement"][0]["item"]
    assert "@id" in item
    assert item["@id"] == seo._entity_url("e1")


def test_itinerary_stop_without_entity_ref_no_id():
    it = {
        "id": "no-ref",
        "title": "Free text",
        "stops": [{"name": "Random stop"}],
    }
    ld = seo.build_itinerary_jsonld(it, {})
    item = ld["itinerary"]["itemListElement"][0]["item"]
    assert "@id" not in item
    assert item["@type"] == "TouristAttraction"


# ── _load with injected data ─────────────────────────────────────────────


def test_load_with_injected_data(monkeypatch):
    """_load with _data already set and _data_mtime_ns=None returns injected data."""
    test_data = {"entities": [{"id": "test"}], "relationships": [], "itineraries": []}
    monkeypatch.setattr(seo, "_data", test_data)
    monkeypatch.setattr(seo, "_data_mtime_ns", None)
    result = seo._load()
    assert result is test_data


def test_by_id_caches_correctly(monkeypatch):
    """_by_id returns a stable cache for the same data object."""
    data = {"entities": [{"id": "a", "name": "A"}], "relationships": [], "itineraries": []}
    monkeypatch.setattr(seo, "_by_id_cache", None)
    monkeypatch.setattr(seo, "_by_id_cache_key", None)
    result1 = seo._by_id(data)
    result2 = seo._by_id(data)
    assert result1 is result2
    assert "a" in result1


# ── dateModified / dateCreated ──────────────────────────────────────────


def test_entity_jsonld_date_modified():
    entity = {
        "id": "dated", "name": "Dated", "type": "attraction",
        "updatedAt": "2026-06-20",
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["dateModified"] == "2026-06-20"


def test_entity_jsonld_date_created():
    entity = {
        "id": "created", "name": "Created", "type": "attraction",
        "created_at": "2026-01-15",
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["dateCreated"] == "2026-01-15"


def test_entity_jsonld_no_dates_when_invalid():
    entity = {
        "id": "no-date", "name": "No date", "type": "attraction",
        "updatedAt": "not-a-date", "created_at": None,
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "dateModified" not in ld
    assert "dateCreated" not in ld


def test_entity_jsonld_both_dates():
    entity = {
        "id": "both", "name": "Both", "type": "attraction",
        "updatedAt": "2026-06-25", "created_at": "2026-06-01",
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["dateModified"] == "2026-06-25"
    assert ld["dateCreated"] == "2026-06-01"


# ── mainEntityOfPage ───────────────────────────────────────────────────


def test_entity_jsonld_main_entity_of_page():
    entity = {"id": "meop-test", "name": "Test", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert "mainEntityOfPage" in ld
    meop = ld["mainEntityOfPage"]
    assert meop["@type"] == "WebPage"
    assert meop["@id"] == seo._entity_url("meop-test")
    assert meop["url"] == seo._entity_url("meop-test")


# ── numberOfRooms coercion ────────────────────────────────────────────


def test_accommodation_rooms_string_coerced_to_int():
    entity = {
        "id": "ks-str-rooms",
        "name": "KS String Rooms",
        "type": "accommodation",
        "attributes": {"rooms": "25"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["numberOfRooms"] == 25
    assert isinstance(ld["numberOfRooms"], int)


def test_accommodation_rooms_int_preserved():
    entity = {
        "id": "ks-int-rooms",
        "name": "KS Int Rooms",
        "type": "accommodation",
        "attributes": {"rooms": 30},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["numberOfRooms"] == 30


def test_accommodation_rooms_invalid_string_omitted():
    entity = {
        "id": "ks-bad-rooms",
        "name": "KS Bad Rooms",
        "type": "accommodation",
        "attributes": {"rooms": "many"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "numberOfRooms" not in ld


# ── _load edge cases ─────────────────────────────────────────────────


def test_load_returns_empty_on_corrupted_json(monkeypatch, tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{corrupted", encoding="utf-8")
    monkeypatch.setattr(seo, "DATA_PATH", bad_file)
    monkeypatch.setattr(seo, "_data", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 1)
    data = seo._load()
    assert data["entities"] == []
    assert data["relationships"] == []


def test_load_invalidates_by_id_cache_on_data_change(monkeypatch, tmp_path):
    f = tmp_path / "data.json"
    import json
    f.write_text(json.dumps({"entities": [{"id": "a"}]}), encoding="utf-8")
    monkeypatch.setattr(seo, "DATA_PATH", f)
    monkeypatch.setattr(seo, "_data", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 1)
    seo._load()
    by_id1 = seo._by_id()
    assert "a" in by_id1
    f.write_text(json.dumps({"entities": [{"id": "b"}]}), encoding="utf-8")
    monkeypatch.setattr(seo, "_data_mtime_ns", 1)
    seo._load()
    by_id2 = seo._by_id()
    assert "b" in by_id2


# ── Sitemap deduplication ────────────────────────────────────────────


def test_sitemap_deduplicates_entity_urls(monkeypatch):
    data = {
        "entities": [
            {"id": "dup", "name": "Dup 1", "type": "attraction"},
            {"id": "dup", "name": "Dup 2", "type": "dish"},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    assert xml.count("<loc>https://vinhlong360.vn/dia-diem/dup</loc>") == 1


# ── Itinerary isPartOf graph linking ─────────────────────────────────


def test_itinerary_jsonld_has_is_part_of():
    it = {"id": "it-graph", "title": "Graph test", "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["isPartOf"]["@id"] == f"{seo.SITE}/#website"


# ── _by_id with non-dict entities ────────────────────────────────────


def test_by_id_skips_non_dict_entities():
    data = {
        "entities": [{"id": "a", "name": "A"}, "not-a-dict", None, 42],
        "relationships": [],
        "itineraries": [],
    }
    import seo as _seo_mod
    _seo_mod._by_id_cache = None
    _seo_mod._by_id_cache_key = None
    result = _seo_mod._by_id(data)
    assert "a" in result
    assert len(result) == 1


def test_by_id_skips_entities_without_id():
    data = {
        "entities": [{"name": "No ID"}, {"id": "b", "name": "B"}],
        "relationships": [],
        "itineraries": [],
    }
    import seo as _seo_mod
    _seo_mod._by_id_cache = None
    _seo_mod._by_id_cache_key = None
    result = _seo_mod._by_id(data)
    assert "b" in result
    assert len(result) == 1


# ── Parameterized parse_coordinates ─────────────────────────────────

import pytest


@pytest.mark.parametrize("input_val,expected", [
    ([10.25, 106.0], (10.25, 106.0)),
    ({"lat": 10.25, "lng": 106.0}, (10.25, 106.0)),
    ({"latitude": 10.25, "longitude": 106.0}, (10.25, 106.0)),
    ("[10.25, 106.0]", (10.25, 106.0)),
    ([106.0, 10.25], (10.25, 106.0)),
    ([0, 0], (0, 0)),
    ([-33.8, 151.2], (-33.8, 151.2)),
    (None, None),
    ("not json", None),
    ([1, 2, 3], None),
    (42, None),
    ({"lat": "abc"}, None),
])
def test_parse_coordinates_parameterized(input_val, expected):
    assert seo.parse_coordinates(input_val) == expected


# ── Parameterized _safe_date ────────────────────────────────────────


@pytest.mark.parametrize("input_val,fallback,expected", [
    ("2026-06-15", None, "2026-06-15"),
    ("  2026-06-15  ", None, "2026-06-15"),
    ("2026-06-15T10:30:00", None, "2026-06-15"),
    ("2026-06-15 14:00:00", None, "2026-06-15"),
    ("not-a-date", "fb", "fb"),
    (None, "fb", "fb"),
    (12345, None, None),
    ("2026-06", None, None),
    ("06-15-2026", None, None),
])
def test_safe_date_parameterized(input_val, fallback, expected):
    assert seo._safe_date(input_val, fallback) == expected


# ── _parse_duration extended formats ─────────────────────────────────


@pytest.mark.parametrize("input_val,expected", [
    ("1 ngày", "P1D"),
    ("3 giờ", "PT3H"),
    ("2 đêm", "P3D"),
    ("2 ngày 1 đêm", "P2D"),
    ("30 phút", "PT30M"),
    ("2 giờ 30 phút", "PT2H30M"),
    (None, None),
    (42, None),
    ("random text", None),
])
def test_parse_duration_parameterized(input_val, expected):
    assert seo._parse_duration(input_val) == expected


# ── _is_external_url hardening ───────────────────────────────────────


def test_is_external_url_rejects_self():
    assert seo._is_external_url("https://vinhlong360.vn/page") is False
    assert seo._is_external_url("https://www.vinhlong360.vn/page") is False
    assert seo._is_external_url("http://vinhlong360.vn") is False


def test_is_external_url_accepts_external():
    assert seo._is_external_url("https://example.com") is True
    assert seo._is_external_url("https://vi.wikipedia.org/wiki/X") is True


def test_is_external_url_rejects_invalid():
    assert seo._is_external_url("") is False
    assert seo._is_external_url("not-a-url") is False
    assert seo._is_external_url(None) is False
    assert seo._is_external_url(42) is False


def test_is_external_url_rejects_self_case_insensitive():
    assert seo._is_external_url("https://VINHLONG360.VN/page") is False


def test_source_info_maps_fallback():
    """When source has no url but has maps, use maps as external URL."""
    title, url = seo._source_info({"source": {"title": "Place", "maps": "https://goo.gl/maps/x"}})
    assert title == "Place"
    assert url == "https://goo.gl/maps/x"


def test_source_info_prefers_url_over_maps():
    title, url = seo._source_info({"source": {
        "title": "Place", "url": "https://example.com", "maps": "https://goo.gl/maps/x"
    }})
    assert url == "https://example.com"


def test_same_as_includes_maps_url():
    entity = {
        "source": [{"title": "Place", "maps": "https://goo.gl/maps/xyz"}],
        "attributes": {},
    }
    values = seo._same_as_values(entity)
    assert "https://goo.gl/maps/xyz" in values


def test_same_as_no_duplicate_maps():
    entity = {
        "source": [{"url": "https://goo.gl/maps/xyz", "maps": "https://goo.gl/maps/xyz"}],
        "attributes": {},
    }
    values = seo._same_as_values(entity)
    assert values.count("https://goo.gl/maps/xyz") == 1


# ── Collection sorting stability ─────────────────────────────────────


def test_entity_jsonld_endpoint_without_faq_returns_single(monkeypatch):
    data = {
        "entities": [
            {"id": "no-faq", "name": "No FAQ", "type": "attraction",
             "attributes": {}},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    result = seo.entity_jsonld("no-faq")
    assert "@graph" not in result
    assert result["@type"] == "TouristAttraction"
    assert result["@context"] == "https://schema.org"


def test_collection_sorts_stably_with_same_confidence():
    entities = [
        {"id": "z", "name": "Zzz", "type": "attraction", "confidence": 0.8},
        {"id": "a", "name": "Aaa", "type": "attraction", "confidence": 0.8},
        {"id": "m", "name": "Mmm", "type": "attraction", "confidence": 0.8},
    ]
    data = {"entities": entities, "relationships": [], "itineraries": []}
    ld = seo.build_collection_jsonld("du-lich", data)
    names = [el["name"] for el in ld["itemListElement"]]
    assert names == ["Aaa", "Mmm", "Zzz"]


# ── Itinerary date enrichment ────────────────────────────────────────


def test_itinerary_jsonld_date_modified():
    it = {
        "id": "dated-it", "title": "Dated", "stops": [],
        "updatedAt": "2026-06-20",
    }
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["dateModified"] == "2026-06-20"


def test_itinerary_jsonld_date_created():
    it = {
        "id": "created-it", "title": "Created", "stops": [],
        "created_at": "2026-01-15",
    }
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["dateCreated"] == "2026-01-15"


def test_itinerary_jsonld_no_dates_when_invalid():
    it = {
        "id": "no-date-it", "title": "No date", "stops": [],
        "updatedAt": "bad", "created_at": None,
    }
    ld = seo.build_itinerary_jsonld(it, {})
    assert "dateModified" not in ld
    assert "dateCreated" not in ld


# ── OCOP identifier ──────────────────────────────────────────────────


def test_entity_jsonld_ocop_identifier():
    entity = {
        "id": "ocop-id", "name": "SP OCOP", "type": "product",
        "attributes": {"ocop": "4 sao", "price": "100.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "identifier" in ld
    assert ld["identifier"]["propertyID"] == "OCOP"
    assert ld["identifier"]["value"] == "4 sao"


def test_craft_village_has_tourist_attraction_additional_type():
    entity = {"id": "cv-test", "name": "Làng nghề Test", "type": "craft_village"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "LocalBusiness"
    assert ld["additionalType"] == "https://schema.org/TouristAttraction"


def test_non_craft_village_local_business_no_additional_type():
    entity = {"id": "econ-test", "name": "Kinh tế Test", "type": "economy"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["@type"] == "LocalBusiness"
    assert "additionalType" not in ld


def test_entity_jsonld_has_map_with_coordinates():
    entity = {
        "id": "map-test", "name": "Map test", "type": "attraction",
        "coordinates": [10.25, 106.0],
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "hasMap" in ld
    assert "10.25,106.0" in ld["hasMap"]
    assert ld["hasMap"].startswith("https://www.google.com/maps")


def test_entity_jsonld_no_map_without_coordinates():
    entity = {"id": "no-map", "name": "No map", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert "hasMap" not in ld


def test_entity_jsonld_no_identifier_without_ocop():
    entity = {
        "id": "no-ocop", "name": "SP", "type": "product",
        "attributes": {"price": "50.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "identifier" not in ld


def test_collection_handles_none_confidence():
    entities = [
        {"id": "no-conf", "name": "No conf", "type": "attraction"},
        {"id": "high", "name": "High", "type": "attraction", "confidence": 0.95},
    ]
    data = {"entities": entities, "relationships": [], "itineraries": []}
    ld = seo.build_collection_jsonld("du-lich", data)
    assert ld["itemListElement"][0]["name"] == "High"


# ── Event location enhancement ──────────────────────────────────────


def test_event_coordinates_only_emits_location_with_geo():
    """Event with coordinates but no placeId should still emit location."""
    event = {
        "id": "ev-coords", "name": "Lễ hội rồng", "type": "event",
        "coordinates": [10.25, 106.0],
        "attributes": {"date_start": "2026-07-01"},
    }
    ld = seo.build_entity_jsonld(event, {})
    assert "location" in ld
    loc = ld["location"]
    assert loc["@type"] == "Place"
    assert "name" not in loc
    assert "geo" in loc
    assert loc["geo"]["latitude"] == 10.25


def test_event_place_and_coordinates_emits_full_location():
    """Event with both placeId + coordinates should emit name + geo."""
    place = {"id": "xa-b", "name": "Xã B", "type": "place", "area": "vinh-long"}
    event = {
        "id": "ev-full", "name": "Hội chợ", "type": "event",
        "placeId": "xa-b",
        "coordinates": [10.3, 105.9],
        "attributes": {"date_start": "2026-08-01"},
    }
    by_id = _by_id([place, event])
    ld = seo.build_entity_jsonld(event, by_id)
    loc = ld["location"]
    assert loc["name"] == "Xã B"
    assert loc["geo"]["latitude"] == 10.3


def test_event_no_place_no_coordinates_no_location():
    """Event with neither place nor coordinates should not emit location."""
    event = {
        "id": "ev-bare", "name": "Sự kiện trực tuyến", "type": "event",
        "attributes": {"date_start": "2026-09-01"},
    }
    ld = seo.build_entity_jsonld(event, {})
    assert "location" not in ld


# ── availableLanguage ───────────────────────────────────────────────


def test_entity_jsonld_has_available_language():
    entity = {"id": "lang-test", "name": "Test", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["availableLanguage"] == "vi"


# ── offers.url enrichment ────────────────────────────────────────────


def test_product_offers_includes_url():
    entity = {
        "id": "prod-url", "name": "SP", "type": "product",
        "attributes": {"price": "150.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["offers"]["url"] == seo._entity_url("prod-url")


# ── aggregateRating ──────────────────────────────────────────────────


def test_entity_jsonld_aggregate_rating():
    entity = {
        "id": "rated", "name": "Rated", "type": "attraction",
        "attributes": {"rating": 4.5, "review_count": 120},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "aggregateRating" in ld
    agg = ld["aggregateRating"]
    assert agg["@type"] == "AggregateRating"
    assert agg["ratingValue"] == 4.5
    assert agg["bestRating"] == 5
    assert agg["reviewCount"] == 120


def test_entity_jsonld_aggregate_rating_without_review_count():
    entity = {
        "id": "rated-no-cnt", "name": "Rated", "type": "restaurant",
        "attributes": {"rating": 3.8},
    }
    ld = seo.build_entity_jsonld(entity, {})
    agg = ld["aggregateRating"]
    assert agg["ratingValue"] == 3.8
    assert "reviewCount" not in agg


def test_entity_jsonld_no_aggregate_rating_when_zero():
    entity = {
        "id": "zero-rate", "name": "Zero", "type": "attraction",
        "attributes": {"rating": 0},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "aggregateRating" not in ld


def test_entity_jsonld_no_aggregate_rating_when_over_5():
    entity = {
        "id": "over-rate", "name": "Over", "type": "attraction",
        "attributes": {"rating": 6},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "aggregateRating" not in ld


def test_entity_jsonld_no_aggregate_rating_when_string():
    entity = {
        "id": "str-rate", "name": "String", "type": "attraction",
        "attributes": {"rating": "good"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "aggregateRating" not in ld


# ── telephone / email / openingHours ─────────────────────────────────


def test_entity_jsonld_telephone():
    entity = {
        "id": "phone-test", "name": "Quán", "type": "restaurant",
        "attributes": {"phone": "0270 1234 567"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["telephone"] == "0270 1234 567"


def test_entity_jsonld_no_telephone_when_empty():
    entity = {
        "id": "no-phone", "name": "Quán", "type": "restaurant",
        "attributes": {"phone": ""},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "telephone" not in ld


def test_entity_jsonld_email():
    entity = {
        "id": "email-test", "name": "KS", "type": "accommodation",
        "attributes": {"email": "info@hotel.vn"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["email"] == "info@hotel.vn"


def test_entity_jsonld_opening_hours():
    entity = {
        "id": "hours-test", "name": "Quán Café", "type": "cafe",
        "attributes": {"opening_hours": "Mo-Fr 07:00-22:00"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["openingHours"] == "Mo-Fr 07:00-22:00"


def test_entity_jsonld_no_opening_hours_when_missing():
    entity = {
        "id": "no-hours", "name": "Quán", "type": "cafe",
        "attributes": {},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "openingHours" not in ld


# ── Event maximumAttendeeCapacity ────────────────────────────────────


def test_event_maximum_attendee_capacity():
    event = {
        "id": "ev-cap", "name": "Lễ hội lớn", "type": "event",
        "attributes": {"date_start": "2026-07-01", "capacity": 5000},
    }
    ld = seo.build_entity_jsonld(event, {})
    assert ld["maximumAttendeeCapacity"] == 5000


def test_event_no_capacity_when_zero():
    event = {
        "id": "ev-no-cap", "name": "Lễ hội", "type": "event",
        "attributes": {"date_start": "2026-07-01", "capacity": 0},
    }
    ld = seo.build_entity_jsonld(event, {})
    assert "maximumAttendeeCapacity" not in ld


def test_event_no_capacity_when_string():
    event = {
        "id": "ev-str-cap", "name": "Lễ hội", "type": "event",
        "attributes": {"date_start": "2026-07-01", "capacity": "many"},
    }
    ld = seo.build_entity_jsonld(event, {})
    assert "maximumAttendeeCapacity" not in ld


# ── Sitemap hreflang ────────────────────────────────────────────────


def test_sitemap_has_xhtml_namespace(monkeypatch):
    data = {"entities": [], "relationships": [], "itineraries": []}
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    assert 'xmlns:xhtml="http://www.w3.org/1999/xhtml"' in xml


def test_robots_has_crawl_delay():
    resp = seo.robots()
    assert "Crawl-delay: 2" in resp
    assert "Googlebot" in resp
    assert f"Host: {seo.SITE}" in resp


def test_breadcrumb_unknown_type_skips_type_tier():
    entity = {"id": "unk-1", "name": "Unknown", "type": "unknown_type_xyz"}
    ld = seo.build_entity_jsonld(entity, {})
    bc = ld["breadcrumb"]
    names = [item["name"] for item in bc["itemListElement"]]
    assert names[0] == "Trang chủ"
    assert names[-1] == "Unknown"
    assert len(names) == 2


def test_breadcrumb_no_area_skips_area_tier():
    entity = {"id": "no-area", "name": "No Area", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    bc = ld["breadcrumb"]
    names = [item["name"] for item in bc["itemListElement"]]
    assert "Trang chủ" in names
    assert "No Area" in names


# ── Itinerary duration from days fallback ────────────────────────────


def test_itinerary_duration_from_days_field():
    it = {"id": "days-it", "title": "2-day trip", "days": 2, "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["duration"] == "P2D"


def test_itinerary_duration_prefers_explicit_over_days():
    it = {"id": "explicit-dur", "title": "Trip", "duration": "3 ngày", "days": 5, "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert ld["duration"] == "P3D"


def test_itinerary_no_duration_when_days_zero():
    it = {"id": "zero-days", "title": "No days", "days": 0, "stops": []}
    ld = seo.build_itinerary_jsonld(it, {})
    assert "duration" not in ld


# ── _source_info edge cases ──────────────────────────────────────────


def test_source_info_empty_list_returns_none():
    title, url = seo._source_info({"source": []})
    assert title is None
    assert url is None


def test_source_info_string_external():
    title, url = seo._source_info({"source": "https://example.com"})
    assert title == "https://example.com"
    assert url == "https://example.com"


def test_source_info_string_self_link():
    title, url = seo._source_info({"source": "https://vinhlong360.vn/page"})
    assert title == "https://vinhlong360.vn/page"
    assert url is None


# ── Sitemap-media caption ────────────────────────────────────────────


def test_sitemap_media_has_caption(monkeypatch):
    data = {
        "entities": [
            {"id": "cap-e", "name": "Captioned", "type": "attraction",
             "summary": "Beautiful place in VL", "confidence": 0.9,
             "images": ["https://example.com/img.jpg"]},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    resp = seo.sitemap_media()
    xml = resp.body.decode()
    assert "<image:caption>Beautiful place in VL</image:caption>" in xml


def test_product_country_of_origin():
    entity = {
        "id": "vn-prod", "name": "SP VN", "type": "product",
        "attributes": {"price": "50.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["countryOfOrigin"]["name"] == "Việt Nam"


def test_product_material():
    entity = {
        "id": "mat-prod", "name": "SP Material", "type": "product",
        "attributes": {"price": "50.000", "material": "Tre và lá dừa"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert ld["material"] == "Tre và lá dừa"


def test_product_no_material_when_absent():
    entity = {
        "id": "no-mat", "name": "SP", "type": "product",
        "attributes": {"price": "50.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "material" not in ld


def test_same_as_includes_facebook():
    entity = {
        "source": [],
        "attributes": {"facebook": "https://facebook.com/test"},
    }
    values = seo._same_as_values(entity)
    assert "https://facebook.com/test" in values


def test_entity_jsonld_keywords_with_type_and_area():
    entity = {
        "id": "kw-test", "name": "Cam sành", "type": "product",
        "area": "vinh-long",
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "keywords" in ld
    assert "Cam sành" in ld["keywords"]
    assert "Sản phẩm" in ld["keywords"]
    assert "Vĩnh Long" in ld["keywords"]


def test_entity_jsonld_season_months():
    entity = {
        "id": "season-test", "name": "Cam", "type": "product",
        "season": {"months": [10, 11, 12, 1, 2], "peak": [11, 12]},
        "attributes": {"price": "50.000"},
    }
    ld = seo.build_entity_jsonld(entity, {})
    assert "additionalProperty" in ld
    props = ld["additionalProperty"]
    season_prop = next(p for p in props if p["propertyID"] == "seasonMonths")
    assert "Tháng 10" in season_prop["value"]
    peak_prop = next(p for p in props if p["propertyID"] == "peakSeason")
    assert "Tháng 11" in peak_prop["value"]


def test_entity_jsonld_no_season_when_absent():
    entity = {"id": "no-season", "name": "No Season", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    assert "additionalProperty" not in ld


def test_entity_jsonld_keywords_without_area():
    entity = {"id": "kw-no-area", "name": "Test", "type": "attraction"}
    ld = seo.build_entity_jsonld(entity, {})
    kw = ld["keywords"]
    assert "Test" in kw
    assert "Du lịch" in kw


def test_same_as_no_duplicate_social():
    entity = {
        "source": [],
        "attributes": {
            "website": "https://example.com",
            "facebook": "https://example.com",
        },
    }
    values = seo._same_as_values(entity)
    assert values.count("https://example.com") == 1


def test_sitemap_media_no_caption_without_summary(monkeypatch):
    data = {
        "entities": [
            {"id": "no-cap", "name": "NoCap", "type": "attraction",
             "confidence": 0.9,
             "images": ["https://example.com/img.jpg"]},
        ],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    resp = seo.sitemap_media()
    xml = resp.body.decode()
    assert "<image:caption>" not in xml


def test_sitemap_url_has_hreflang(monkeypatch):
    data = {
        "entities": [{"id": "a", "name": "A", "type": "attraction", "confidence": 0.9}],
        "relationships": [],
        "itineraries": [],
    }
    monkeypatch.setattr(seo, "_load", lambda: data)
    monkeypatch.setattr(seo, "_sitemap_cache", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", 0)
    resp = seo.sitemap()
    xml = resp.body.decode()
    assert 'hreflang="vi"' in xml
    assert 'hreflang="x-default"' in xml
