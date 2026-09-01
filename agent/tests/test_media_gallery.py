from __future__ import annotations


def test_media_gallery_extracts_credit_metadata_without_mutating_entities():
    from entities.admin_api import _extract_media_items

    source = {
        "id": "e-gallery",
        "name": "Gallery",
        "type": "attraction",
        "images": [None, {"url": "/img/entities/gallery.webp"}],
        "attributes": {"image_credits": [{"url": "/img/entities/gallery.webp", "author": "A", "license": "CC0"}]},
    }
    result = _extract_media_items([source])
    assert result["items"][0]["credit"] == "A"
    assert result["items"][0]["license"] == "CC0"
    assert source["images"][0] is None
