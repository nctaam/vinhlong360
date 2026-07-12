"""Regression tests for the public entity eligibility boundary."""

import asyncio
from contextlib import nullcontext

from fastapi import Response
from starlette.requests import Request

import public_api
import ratelimit


def _request(path: str = "/api/test") -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "client": ("127.0.0.1", 12345),
    })


def _entity(entity_id: str, **overrides) -> dict:
    entity = {
        "id": entity_id,
        "name": entity_id.title(),
        "type": "attraction",
        "status": "published",
        "verified": True,
        "attributes": {},
        "images": [],
    }
    entity.update(overrides)
    return entity


def _patch_rows(monkeypatch, rows: list[dict]) -> None:
    monkeypatch.setattr(public_api.db, "initialize", lambda: None)
    monkeypatch.setattr(public_api.db, "_conn", lambda: nullcontext(object()))
    monkeypatch.setattr(public_api.db, "_fetchall", lambda *_args, **_kwargs: rows)
    monkeypatch.setattr(public_api.db, "_row_to_dict", lambda row: dict(row))


def test_is_public_rejects_all_non_public_flag_shapes():
    assert public_api._is_public(_entity("public")) is True
    assert public_api._is_public(_entity("draft", status="provisional")) is False
    assert public_api._is_public(_entity("false", verified=False)) is False
    assert public_api._is_public(_entity("zero", verified=0)) is False


def test_public_batch_filters_hidden_entities(monkeypatch):
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": _entity("public"),
        "draft": _entity("draft", status="provisional"),
        "zero": _entity("zero", verified=0),
    })

    result = public_api._get_public_entities_batch(["public", "draft", "zero"])

    assert list(result) == ["public"]


def test_autocomplete_requests_public_only(monkeypatch):
    captured = {}

    def _search_entities(**kwargs):
        captured.update(kwargs)
        return [_entity("public")]

    monkeypatch.setattr(public_api.db, "search_entities", _search_entities)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)

    result = asyncio.run(public_api.autocomplete(
        _request("/api/autocomplete"), Response(), q="pub", type=None, limit=8,
    ))

    assert captured["public_only"] is True
    assert [item["id"] for item in result["suggestions"]] == ["public"]


def test_featured_filters_hidden_entities(monkeypatch):
    monkeypatch.setattr(public_api.db, "_use_pg", True)
    _patch_rows(monkeypatch, [
        {"entity_id": "public", "sort_order": 1},
        {"entity_id": "hidden", "sort_order": 2},
    ])
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": _entity("public"),
        "hidden": _entity("hidden", status="provisional"),
    })

    result = asyncio.run(public_api.get_featured_entities(Response()))

    assert [item["id"] for item in result["featured"]] == ["public"]


def test_places_directory_filters_hidden_rows(monkeypatch):
    _patch_rows(monkeypatch, [
        _entity("public-place", type="place", area="vinh-long", level="xa"),
        _entity("hidden-place", type="place", area="vinh-long", level="xa", verified=0),
    ])

    result = asyncio.run(public_api.list_places(Response(), area=None))

    assert [item["id"] for item in result] == ["public-place"]
    assert set(result[0]) == {"id", "name", "area", "level"}


def test_facilities_directory_filters_hidden_rows(monkeypatch):
    monkeypatch.setattr(public_api.db, "facilities_by_place", lambda _place: [
        _entity("public-facility", type="facility"),
        _entity("hidden-facility", type="facility", status="provisional"),
    ])

    result = asyncio.run(public_api.list_facilities(Response(), place=None))

    assert [item["id"] for item in result["facilities"]] == ["public-facility"]


def test_place_overview_filters_parent_children_and_facilities(monkeypatch):
    monkeypatch.setattr(public_api.db, "get_entity", lambda _id: _entity(
        "public-place", type="place", area="vinh-long", level="xa",
    ))
    monkeypatch.setattr(public_api.db, "entities_by_place", lambda _id: [
        _entity("public-child"),
        _entity("hidden-child", verified=0),
    ])
    monkeypatch.setattr(public_api.db, "facilities_by_place", lambda _id: [
        _entity("public-facility", type="facility"),
        _entity("hidden-facility", type="facility", status="provisional"),
    ])

    result = asyncio.run(public_api.place_overview("public-place", Response()))

    assert [item["id"] for item in result["tourism"]] == ["public-child"]
    assert [item["id"] for item in result["facilities"]] == ["public-facility"]
    assert result["counts"]["tourism"] == 1


def test_place_overview_rejects_hidden_parent(monkeypatch):
    monkeypatch.setattr(public_api.db, "get_entity", lambda _id: _entity(
        "hidden-place", type="place", status="provisional",
    ))

    result = asyncio.run(public_api.place_overview("hidden-place", Response()))

    assert result.status_code == 404


def test_day_plan_filters_hidden_children(monkeypatch):
    monkeypatch.setattr(public_api.db, "get_entity", lambda _id: _entity(
        "public-place", type="place", coordinates=[10.0, 106.0],
    ))
    monkeypatch.setattr(public_api.db, "entities_by_place", lambda _id: [
        _entity("public-child", coordinates=[10.1, 106.1]),
        _entity("hidden-child", type="nature", coordinates=[10.2, 106.2], verified=0),
    ])

    result = asyncio.run(public_api.place_day_plan("public-place", Response()))

    assert [item["entity_id"] for item in result["stops"]] == ["public-child"]


def test_collection_expansion_filters_hidden_entities(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    monkeypatch.setattr(public_api.db, "_conn", lambda: nullcontext(object()))
    monkeypatch.setattr(public_api.db, "_fetchone", lambda *_args, **_kwargs: {
        "id": "collection-1",
        "slug": "public-collection",
        "entity_ids": ["public", "hidden"],
    })
    monkeypatch.setattr(public_api.db, "_row_to_dict", lambda row: dict(row))
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": _entity("public"),
        "hidden": _entity("hidden", status="provisional"),
    })

    result = asyncio.run(public_api.get_collection_by_slug("public-collection", Response()))

    assert list(result["entities"]) == ["public"]


def test_collection_list_filters_hidden_entity_ids(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    _patch_rows(monkeypatch, [{
        "id": "collection-1",
        "slug": "public-collection",
        "entity_ids": ["public", "hidden"],
    }])
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": _entity("public"),
        "hidden": _entity("hidden", status="provisional"),
    })

    result = asyncio.run(public_api.list_public_collections(Response(), limit=20))

    assert result["collections"][0]["entity_ids"] == ["public"]


def test_empty_collection_preserves_existing_entities_shape(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    monkeypatch.setattr(public_api.db, "_conn", lambda: nullcontext(object()))
    monkeypatch.setattr(public_api.db, "_fetchone", lambda *_args, **_kwargs: {
        "id": "collection-1",
        "slug": "empty-collection",
        "entity_ids": [],
    })
    monkeypatch.setattr(public_api.db, "_row_to_dict", lambda row: dict(row))

    result = asyncio.run(public_api.get_collection_by_slug("empty-collection", Response()))

    assert result["entities"] == []


def test_trending_filters_hidden_entities(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    _patch_rows(monkeypatch, [
        {"entity_id": "public", "activity_count": 3, "review_count": 1, "avg_rating": 4.5},
        {"entity_id": "hidden", "activity_count": 2, "review_count": 1, "avg_rating": 4.0},
    ])
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": _entity("public"),
        "hidden": _entity("hidden", verified=0),
    })

    result = asyncio.run(public_api.entities_trending(
        days=7, entity_type=None, limit=10, response=Response(),
    ))

    assert [item["entity_id"] for item in result["entities"]] == ["public"]


def test_compare_filters_hidden_entities(monkeypatch):
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": _entity("public"),
        "hidden": _entity("hidden", status="provisional"),
    })

    result = asyncio.run(public_api.compare_entities(
        _request("/api/entities/compare"), Response(), ids="public,hidden",
    ))

    assert [item["id"] for item in result["entities"]] == ["public"]
    assert result["count"] == 1


def test_itinerary_omits_hidden_referenced_stops(monkeypatch):
    monkeypatch.setattr(public_api.db, "get_itinerary", lambda _id: {
        "id": "itinerary-1",
        "stops": [
            {"entityId": "public"},
            {"entityId": "hidden"},
            {"name": "Free-form stop"},
        ],
    })
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": _entity("public", summary="Public summary", coordinates=[10.0, 106.0]),
        "hidden": _entity("hidden", status="provisional"),
    })

    result = asyncio.run(public_api.get_itinerary("itinerary-1", Response()))

    assert [stop.get("entityId") for stop in result["stops"]] == ["public", None]
    assert result["stops"][0]["name"] == "Public"
    assert result["stops"][1] == {"name": "Free-form stop"}


def test_itinerary_list_filters_hidden_entity_stops(monkeypatch):
    monkeypatch.setattr(public_api.db, "list_itineraries", lambda **_kwargs: [{
        "id": "itinerary-1",
        "stops": [
            {"entity_id": "public-child", "name": "Public child"},
            {"entityId": "hidden-child", "name": "Hidden child"},
            {"name": "Free-form stop"},
        ],
    }])
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public-child": _entity("public-child"),
        "hidden-child": _entity("hidden-child", verified=0),
    })

    result = asyncio.run(public_api.list_itineraries(
        Response(), area=None, limit=50, offset=0,
    ))

    assert [item["name"] for item in result[0]["stops"]] == [
        "Public child", "Free-form stop",
    ]


def test_homepage_itineraries_filter_hidden_entity_stops():
    result = public_api._select_homepage_itineraries([{
        "id": "itinerary-1",
        "stops": [
            {"entityId": "public-child", "name": "Public child"},
            {"entityId": "hidden-child", "name": "Hidden child"},
            {"name": "Free-form stop"},
        ],
    }], [_entity("public-child")], month=7)

    assert [item["name"] for item in result[0]["stops"]] == [
        "Public child", "Free-form stop",
    ]
