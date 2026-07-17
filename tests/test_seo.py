from __future__ import annotations

import seo


def test_entity_jsonld_accepts_list_coordinates() -> None:
    by_id = {
        "xa-ao-ba-om": {"id": "xa-ao-ba-om", "type": "place", "name": "Xa Ao Ba Om", "area": "tra-vinh"},
        "ao-ba-om": {
            "id": "ao-ba-om",
            "type": "attraction",
            "name": "Ao Ba Om",
            "summary": "Diem tham quan van hoa Khmer.",
            "placeId": "xa-ao-ba-om",
            "coordinates": [9.934, 106.345],
            "source": {"title": "Verified", "url": "https://example.com/ao-ba-om"},
        },
    }

    ld = seo.build_entity_jsonld(by_id["ao-ba-om"], by_id)

    assert ld["@type"] == "TouristAttraction"
    assert ld["geo"] == {"@type": "GeoCoordinates", "latitude": 9.934, "longitude": 106.345}
    assert ld["address"]["addressRegion"] == "Trà Vinh"
    assert ld["citation"]["url"] == "https://example.com/ao-ba-om"


def test_itinerary_jsonld_keeps_fixed_detail_url_contract() -> None:
    itinerary_ld = seo.build_itinerary_jsonld(
        {"id": "hanh-trinh-a", "title": "Hanh trinh A", "stops": []}, {}
    )
    assert itinerary_ld["url"] == "https://vinhlong360.vn/lich-trinh/hanh-trinh-a"
