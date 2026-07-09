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
