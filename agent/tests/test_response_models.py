# -*- coding: utf-8 -*-
"""W6.3 — response_model an toàn (extra='allow' KHÔNG strip field FE)."""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import public_api  # noqa: E402
from api_schemas import ApiModel  # noqa: E402

WANT = {
    "/api/entities", "/api/entity-types", "/api/areas", "/api/search",
    "/api/featured", "/api/events", "/api/collections", "/api/autocomplete",
    "/api/entities/map", "/api/entities/trending", "/api/entities/compare",
    "/api/entities/popular",
    # batch-2
    "/api/homepage", "/api/stats", "/api/site-settings", "/api/transparency",
    "/api/entities/{entity_id}",
}


def _client():
    app = FastAPI()
    app.include_router(public_api.router)
    return TestClient(app)


def test_key_endpoints_have_apimodel_response_model():
    got = {r.path: getattr(r, "response_model", None)
           for r in public_api.router.routes if hasattr(r, "path")}
    for path in WANT:
        rm = got.get(path)
        assert rm is not None, f"{path} thiếu response_model"
        assert issubclass(rm, ApiModel), f"{path} response_model phải kế ApiModel (extra=allow)"


def test_apimodel_allows_extra_fields():
    # Guard: nếu ai đổi base sang extra='forbid'/'ignore' → strip field FE → test đỏ.
    assert ApiModel.model_config.get("extra") == "allow"
    m = ApiModel.model_validate({"declared": 1, "surprise_field": "x"})
    assert m.model_dump().get("surprise_field") == "x"


def test_response_model_does_not_strip_item_fields():
    # /entities: model chỉ khai top-level {entities,total}; item field (id/name/...)
    # KHÔNG khai → phải pass-through nhờ extra='allow' (nếu strip → FE vỡ).
    r = _client().get("/api/entities?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "entities" in data and "total" in data
    if data["entities"]:
        item = data["entities"][0]
        assert "id" in item  # item field không-khai vẫn còn → không strip


def test_entity_types_shape_preserved_under_model():
    r = _client().get("/api/entity-types")
    assert r.status_code == 200
    data = r.json()
    assert "types" in data and "total" in data
    if data["types"]:
        assert "type" in data["types"][0] and "count" in data["types"][0]


def test_map_pins_uses_list_response_model():
    # /map-pins trả LIST → response_model=list[MapPin]; kiểm có khai + trả 200 list.
    got = {r.path: getattr(r, "response_model", None)
           for r in public_api.router.routes if hasattr(r, "path")}
    assert got.get("/api/map-pins") is not None
    r = _client().get("/api/map-pins")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_entity_detail_no_strip_across_types():
    # entity-detail phục vụ MỌI type; model chỉ khai scalar → field container
    # (attributes/source/images) phải pass-through (extra="allow"), không 500.
    c = _client()
    ents = c.get("/api/entities?limit=500").json().get("entities", [])
    by_type = {}
    for e in ents:
        by_type.setdefault(e.get("type"), e.get("id"))
    assert by_type, "cần có entity để test"
    for _t, eid in list(by_type.items())[:20]:
        r = c.get(f"/api/entities/{eid}")
        assert r.status_code == 200, f"entity {eid} → {r.status_code}"
        d = r.json()
        # field KHÔNG khai trong EntityDetailResponse vẫn còn (không strip)
        assert "attributes" in d and "source" in d


def test_homepage_shape_preserved():
    r = _client().get("/api/homepage")
    assert r.status_code == 200
    d = r.json()
    for k in ("seasonal", "experiences", "products", "trending", "itineraries"):
        assert k in d
