"""Tests GĐ-A: per-kind admin views (kind param + completeness endpoint).

Spec: docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md
Plan: docs/superpowers/plans/2026-07-02-entity-split-per-kind.md
"""
import os
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-kindviews")
os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402
from server import app  # noqa: E402
from entity_schemas import KIND_OF_TYPE  # noqa: E402

client = TestClient(app)
H = {"X-Admin-Key": os.environ["ADMIN_API_KEY"]}
FOOD_TYPES = {t for t, k in KIND_OF_TYPE.items() if k == "food"}


def test_kind_param_returns_only_member_types():
    r = client.get("/admin/entities?kind=food&limit=500", headers=H)
    assert r.status_code == 200
    ents = r.json()["entities"]
    assert ents, "DB dev phải có entity ẩm thực"
    assert {e["type"] for e in ents} <= FOOD_TYPES


def test_kind_param_pagination_total():
    r = client.get("/admin/entities?kind=food&limit=5&offset=0", headers=H)
    body = r.json()
    assert len(body["entities"]) <= 5
    assert body["total"] >= len(body["entities"])


def test_kind_unknown_returns_empty():
    r = client.get("/admin/entities?kind=khong-ton-tai", headers=H)
    assert r.status_code == 200
    assert r.json()["entities"] == []


def test_type_param_still_works_unchanged():
    r = client.get("/admin/entities?type=product&limit=5", headers=H)
    assert r.status_code == 200
    assert all(e["type"] == "product" for e in r.json()["entities"])


def test_completeness_food_shape():
    r = client.get("/admin/entity-completeness?kind=food", headers=H)
    assert r.status_code == 200
    b = r.json()
    assert b["kind"] == "food" and b["total"] > 0
    keys = {f["key"] for f in b["fields"]}
    assert {"address", "phone", "season", "images", "price_range"} <= keys
    for f in b["fields"]:
        assert 0 <= f["pct"] <= 100
    assert b["worst"] and "missing" in b["worst"][0]


def test_completeness_requires_kind():
    assert client.get("/admin/entity-completeness", headers=H).status_code == 422
