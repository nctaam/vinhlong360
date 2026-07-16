import copy
import asyncio
import inspect
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import public_api  # noqa: E402
from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence  # noqa: E402

try:
    import policy_http  # noqa: E402
except ModuleNotFoundError:
    policy_http = None


EVIDENCE = PolicyEvidence(
    policy_fingerprint="b" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision=INDEX_POLICY_REVISION,
)


def _words(count: int) -> str:
    return " ".join(["word"] * count)


def _entity(summary: str | None = None) -> dict[str, object]:
    return {
        "id": "public-entity",
        "type": "attraction",
        "name": "Public entity",
        "status": "published",
        "verified": True,
        "summary": _words(130) if summary is None else summary,
        "description": "",
        "source": {"title": "Source", "url": "https://example.test/source"},
    }


def _assert_no_store_no_validator(response) -> None:
    assert response.status_code != 304
    assert response.headers.get_list("cache-control") == ["no-store"]
    assert not ({"etag", "last-modified", "expires"} & set(response.headers))


@pytest.fixture
def entity_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, dict]]:
    state = {"entity": _entity()}
    monkeypatch.setattr(
        public_api.db,
        "get_entity",
        lambda entity_id: copy.deepcopy(state["entity"] if entity_id == "public-entity" else None),
    )
    monkeypatch.setattr(
        public_api.db,
        "get_relationships",
        lambda *args, **kwargs: ([], 0),
    )
    monkeypatch.setattr(public_api.db, "entities_by_place", lambda _place_id: [])
    monkeypatch.setattr(public_api, "current_policy_evidence", lambda: EVIDENCE)

    app = FastAPI()
    app.include_router(public_api.router)
    if policy_http is not None:
        app.add_middleware(policy_http.PolicyHttpMiddleware)
    with TestClient(app) as client:
        yield client, state


def test_entity_detail_never_returns_304(entity_client):
    client, _state = entity_client

    first = client.get("/api/entities/public-entity")
    second = client.get(
        "/api/entities/public-entity",
        headers={"If-None-Match": first.headers.get("etag", '"legacy"')},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    _assert_no_store_no_validator(first)
    _assert_no_store_no_validator(second)


def test_direct_policy_input_change_is_visible_without_invalidation(entity_client):
    client, state = entity_client

    before = client.get("/api/entities/public-entity").json()["index_policy"]
    state["entity"] = _entity(summary="")
    after = client.get("/api/entities/public-entity").json()["index_policy"]

    assert before["indexable"] is True
    assert after["indexable"] is False
    assert after["reasons"] == ["description-below-130-words"]


def _policy_contract_app() -> FastAPI:
    assert policy_http is not None, "agent.policy_http must exist"
    router = APIRouter(prefix="/api")

    def dependency_guard(dependency_failure: bool = False) -> None:
        if dependency_failure:
            raise HTTPException(status_code=503, detail="dependency unavailable")

    @router.get("/entities/map", name="entity_map")
    def static_entity_route():
        return Response(headers={"Cache-Control": "public, max-age=3600", "ETag": '"map"'})

    @router.get("/entities/{entity_id}", name="get_entity")
    def policy_route(entity_id: int, _guard: None = Depends(dependency_guard)):
        headers = {
            "Cache-Control": "public, max-age=60",
            "ETag": '"legacy"',
            "Last-Modified": "Wed, 15 Jul 2026 00:00:00 GMT",
            "Expires": "Wed, 15 Jul 2026 01:00:00 GMT",
        }
        if entity_id == 404:
            response = JSONResponse({"detail": "returned"}, status_code=404, headers=headers)
        elif entity_id == 405:
            raise HTTPException(status_code=404, detail="raised")
        elif entity_id == 304:
            response = Response(status_code=304, headers=headers)
        else:
            response = JSONResponse({"index_policy": {"indexable": False}}, headers=headers)
        response.raw_headers.append((b"cAcHe-CoNtRoL", b"private, max-age=1"))
        response.raw_headers.append((b"eTaG", b'"duplicate"'))
        response.raw_headers.append((b"lAsT-mOdIfIeD", b"duplicate"))
        response.raw_headers.append((b"eXpIrEs", b"duplicate"))
        return response

    app = FastAPI()
    app.include_router(router)
    app.add_middleware(policy_http.PolicyHttpMiddleware)
    return app


class _PreRouteShortCircuitMiddleware:
    def __init__(self, app, status_code=503):
        self.app = app
        self.status_code = status_code

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            response = Response(
                status_code=self.status_code,
                headers={
                    "Cache-Control": "public, max-age=60",
                    "ETag": '"pre-route"',
                    "Last-Modified": "Wed, 15 Jul 2026 00:00:00 GMT",
                    "Expires": "Wed, 15 Jul 2026 01:00:00 GMT",
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _pre_route_short_circuit_app(status_code=503) -> FastAPI:
    assert policy_http is not None, "agent.policy_http must exist"
    router = APIRouter(prefix="/api")

    @router.get("/entities/map", name="entity_map")
    def entity_map():
        return {"ok": True}

    @router.get("/entities/{entity_id}", name="get_entity")
    def get_entity(entity_id: str):
        return {"id": entity_id}

    app = FastAPI()
    app.include_router(router)
    app.add_middleware(_PreRouteShortCircuitMiddleware, status_code=status_code)
    middleware_kwargs = {}
    if "route_resolver" in inspect.signature(policy_http.PolicyHttpMiddleware).parameters:
        middleware_kwargs["route_resolver"] = app.router
    app.add_middleware(policy_http.PolicyHttpMiddleware, **middleware_kwargs)
    return app


@pytest.mark.parametrize(
    ("url", "expected_status"),
    [
        ("/api/entities/1", 200),
        ("/api/entities/404", 404),
        ("/api/entities/405", 404),
        ("/api/entities/not-an-int", 422),
        ("/api/entities/1?dependency_failure=true", 503),
    ],
)
def test_registered_route_contract_covers_every_response_path(url: str, expected_status: int):
    with TestClient(_policy_contract_app()) as client:
        response = client.get(url, headers={"If-None-Match": '"legacy"'})

    assert response.status_code == expected_status
    _assert_no_store_no_validator(response)


def test_registered_304_is_a_contract_error():
    assert policy_http is not None, "agent.policy_http must exist"
    with TestClient(_policy_contract_app()) as client:
        with pytest.raises(policy_http.PolicyHttpContractError, match="304"):
            client.get("/api/entities/304")


def test_registered_304_production_response_is_no_store_contract_failure():
    with TestClient(_policy_contract_app(), raise_server_exceptions=False) as client:
        response = client.get("/api/entities/304")

    assert response.status_code == 500
    _assert_no_store_no_validator(response)


def test_static_entity_route_keeps_existing_cache_contract():
    with TestClient(_policy_contract_app()) as client:
        response = client.get("/api/entities/map")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.headers["etag"] == '"map"'


def test_unmatched_404_is_not_swept_by_lexical_path():
    with TestClient(_policy_contract_app()) as client:
        response = client.get("/api/entities/not/a/registered/route")

    assert response.status_code == 404
    assert response.headers.get("cache-control") != "no-store"


def test_exact_lexical_path_without_resolved_route_is_untouched():
    assert policy_http is not None, "agent.policy_http must exist"
    messages = []

    async def inner(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 304,
                "headers": [(b"cache-control", b"public"), (b"etag", b'"legacy"')],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "method": "GET", "path": "/api/entities/1"}
    asyncio.run(policy_http.PolicyHttpMiddleware(inner)(scope, receive, send))

    assert messages[0]["status"] == 304
    assert messages[0]["headers"] == [
        (b"cache-control", b"public"),
        (b"etag", b'"legacy"'),
    ]


@pytest.mark.parametrize(
    ("path", "status_code", "expected_cache"),
    [
        ("/api/entities/1", 503, "no-store"),
        ("/api/entities/1", 413, "no-store"),
        ("/api/entities/map", 503, "public, max-age=60"),
        ("/api/entities/not/a/route", 503, "public, max-age=60"),
    ],
)
def test_pre_route_short_circuit_uses_exact_application_route_identity(
    path: str,
    status_code: int,
    expected_cache: str,
):
    with TestClient(_pre_route_short_circuit_app(status_code)) as client:
        response = client.get(path, headers={"If-None-Match": '"pre-route"'})

    assert response.status_code == status_code
    assert response.headers["cache-control"] == expected_cache
    if expected_cache == "no-store":
        assert not ({"etag", "last-modified", "expires"} & set(response.headers))
    else:
        assert response.headers["etag"] == '"pre-route"'


def test_server_registers_policy_middleware_after_every_decorator_middleware():
    source = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
    registration = source.index("app.add_middleware(PolicyHttpMiddleware")

    assert registration > source.rfind('@app.middleware("http")')


def test_registry_is_exact_frozen_and_validated():
    assert policy_http is not None, "agent.policy_http must exist"
    assert [
        (row.method, row.path, row.route_name, row.exposure, row.cache_contract)
        for row in policy_http.POLICY_ENDPOINTS
    ] == [
        ("GET", "/api/entities/{entity_id}", "get_entity", "public", "no-store-no-validator"),
        (
            "GET",
            "/_internal/launch-policy-attestation",
            "launch_policy_attestation",
            "internal",
            "no-store-no-validator",
        ),
        (
            "GET",
            "/_internal/launch-sitemaps/{document}",
            "launch_sitemap_document",
            "internal",
            "no-store-no-validator",
        ),
    ]
    with pytest.raises(Exception):
        policy_http.POLICY_ENDPOINTS[0].exposure = "changed"
    with pytest.raises(ValueError):
        policy_http.validate_policy_endpoints(
            (
                policy_http.PolicyEndpoint("GET", "/x", "duplicate", "public"),
                policy_http.PolicyEndpoint("GET", "/x", "duplicate", "public"),
            )
        )
    with pytest.raises(ValueError):
        policy_http.PolicyEndpoint("GET", "/x", "x", "external")
