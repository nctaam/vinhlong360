import copy
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import public_api  # noqa: E402
from index_policy import public_ward_child_counts  # noqa: E402
from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence  # noqa: E402


EVIDENCE = PolicyEvidence(
    policy_fingerprint="a" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision=INDEX_POLICY_REVISION,
)


def _words(count: int, word: str = "word") -> str:
    return " ".join([word] * count)


def _entity(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": "public-entity",
        "type": "attraction",
        "name": "Entity cong khai",
        "status": "published",
        "verified": True,
        "summary": _words(129),
        "description": "",
        "source": {"title": "Nguon", "url": "https://example.test/source"},
        "attributes": {"rating": 5},
    }
    value.update(overrides)
    return value


def _ward(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": "public-ward",
        "type": "place",
        "name": "Ward cong khai",
        "status": "published",
        "verified": True,
        "summary": _words(59, "phuong"),
        "description": "",
    }
    value.update(overrides)
    return value


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    entities = {
        "public-entity": _entity(),
        "public-ward": _ward(),
    }
    children = [
        _entity(id="child-public", placeId="public-ward"),
        _entity(id="child-draft", placeId="public-ward", status="draft"),
        _entity(id="child-unverified", placeId="public-ward", verified=False),
        _entity(id="public-ward", type="place", placeId="public-ward"),
        {
            "id": "",
            "placeId": "public-ward",
            "type": "attraction",
            "status": "published",
            "verified": True,
        },
        {
            "id": "   ",
            "placeId": "public-ward",
            "type": "attraction",
            "status": "published",
            "verified": True,
        },
        {
            "id": 123,
            "placeId": "public-ward",
            "type": "attraction",
            "status": "published",
            "verified": True,
        },
        {
            "id": "child-missing-place",
            "type": "attraction",
            "status": "published",
            "verified": True,
        },
    ]

    monkeypatch.setattr(
        public_api.db,
        "get_entity",
        lambda entity_id: copy.deepcopy(entities.get(entity_id)),
    )
    monkeypatch.setattr(
        public_api.db,
        "get_relationships",
        lambda *args, **kwargs: ([], 0),
    )
    monkeypatch.setattr(
        public_api.db,
        "entities_by_place",
        lambda place_id: copy.deepcopy(children if place_id == "public-ward" else []),
    )
    monkeypatch.setattr(
        public_api,
        "current_policy_evidence",
        lambda: EVIDENCE,
        raising=False,
    )
    public_api.invalidate_entity_cache()
    app = FastAPI()
    app.include_router(public_api.router)
    try:
        yield TestClient(app)
    finally:
        public_api.invalidate_entity_cache()


def test_entity_detail_contains_mandatory_boolean_policy(client: TestClient):
    response = client.get("/api/entities/public-entity")
    assert response.status_code == 200
    body = response.json()
    policy = body["index_policy"]
    assert set(policy) == {
        "kind", "indexable", "reasons", "policy_fingerprint", "policy_revision",
    }
    assert isinstance(policy["indexable"], bool)
    assert policy["kind"] == "entity"
    assert policy["reasons"] == ["description-below-130-words"]
    assert len(policy["policy_fingerprint"]) == 64
    assert policy["policy_revision"] == "index-policy-v1"
    assert body["id"] == "public-entity"
    assert body["source"]["url"] == "https://example.test/source"


def test_place_entity_uses_ward_policy(client: TestClient):
    response = client.get("/api/entities/public-ward")
    assert response.status_code == 200
    assert response.json()["index_policy"]["kind"] == "ward"


def test_ward_policy_counts_only_public_eligible_children(client: TestClient):
    response = client.get("/api/entities/public-ward")
    assert response.status_code == 200
    policy = response.json()["index_policy"]
    assert policy["indexable"] is False
    assert "ward-below-child-and-summary-threshold" in policy["reasons"]


def test_public_api_ward_count_matches_shared_sitemap_authority(monkeypatch):
    children = [
        _entity(id="one", placeId="public-ward"),
        _entity(id="one", placeId="public-ward"),
        _entity(id="two", placeId="public-ward"),
        _entity(id="draft", placeId="public-ward", status="draft"),
        _ward(id="nested", placeId="public-ward"),
    ]
    monkeypatch.setattr(
        public_api.db,
        "entities_by_place",
        lambda place_id: copy.deepcopy(children if place_id == "public-ward" else []),
    )

    assert public_api._public_index_policy_child_count("public-ward") == (
        public_ward_child_counts(children).get("public-ward", 0)
    ) == 2


def test_index_policy_nested_model_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        public_api.EntityDetailResponse.model_validate({"id": "x"})

    with pytest.raises(ValidationError):
        public_api.EntityDetailResponse.model_validate(
            {
                "id": "x",
                "index_policy": {
                    "kind": "entity",
                    "indexable": False,
                    "reasons": ["description-below-130-words"],
                    "policy_fingerprint": "a" * 64,
                    "policy_revision": "index-policy-v1",
                    "unexpected": True,
                },
            }
        )
