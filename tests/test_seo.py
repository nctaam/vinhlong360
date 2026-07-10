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


def test_sitemap_includes_all_public_non_place_entities_and_itineraries(monkeypatch) -> None:
    rich = "chu " * 140  # >=130 tu -> qua cong chat luong is_index_worthy (P0-1)
    monkeypatch.setattr(seo, "_data", {
        "entities": [
            {"id": "xa-vinh-long", "type": "place", "name": "Xa Vinh Long", "updatedAt": "2026-01-01"},
            {"id": "lich-su-a", "type": "history", "name": "Lich su A", "summary": rich, "updatedAt": "2026-01-02"},
            {"id": "nhan-vat-b", "type": "person", "name": "Nhan vat B", "summary": rich},
        ],
        "relationships": [],
        "itineraries": [{"id": "hanh-trinh-a", "title": "Hanh trinh A", "updatedAt": "2026-01-03"}],
    })

    body = seo.sitemap().body.decode("utf-8")

    assert "https://vinhlong360.vn/dia-diem/lich-su-a" in body
    assert "https://vinhlong360.vn/dia-diem/nhan-vat-b" in body
    assert "https://vinhlong360.vn/dia-diem/xa-vinh-long" not in body
    assert "https://vinhlong360.vn/lich-trinh/hanh-trinh-a" in body
    # P1-4: detail URL khong con phat lastmod=updatedAt (chong freshness-gaming);
    # lastmod hop le den tu itinerary (updatedAt 2026-01-03).
    assert "<lastmod>2026-01-03</lastmod>" in body
