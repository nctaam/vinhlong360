from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


AGENT = Path(__file__).resolve().parent.parent
ROOT = AGENT.parent
sys.path.insert(0, str(AGENT))

try:
    import launch_policy_api
except ModuleNotFoundError:
    launch_policy_api = None

try:
    import policy_http
except ModuleNotFoundError:
    policy_http = None

from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence  # noqa: E402


EVIDENCE_A = PolicyEvidence(
    policy_fingerprint="a" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision=INDEX_POLICY_REVISION,
)
EVIDENCE_B = PolicyEvidence(
    policy_fingerprint="b" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision=INDEX_POLICY_REVISION,
)


def _focused_app(monkeypatch: pytest.MonkeyPatch, loader: Callable[[], PolicyEvidence]) -> FastAPI:
    assert launch_policy_api is not None, "agent.launch_policy_api must exist"
    assert policy_http is not None, "agent.policy_http must exist"
    monkeypatch.setattr(launch_policy_api, "current_policy_evidence", loader)

    app = FastAPI()

    @app.middleware("http")
    async def legacy_cache_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "public, max-age=3600"
        response.headers["ETag"] = '"legacy"'
        response.headers["Last-Modified"] = "Thu, 16 Jul 2026 00:00:00 GMT"
        response.headers["Expires"] = "Thu, 16 Jul 2026 01:00:00 GMT"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    app.include_router(launch_policy_api.router)
    app.add_middleware(policy_http.PolicyHttpMiddleware, route_resolver=app.router)
    return app


def _assert_no_store_no_validator(response, expected_status: int) -> None:
    assert response.status_code == expected_status
    assert response.status_code != 304
    assert response.headers.get_list("cache-control") == ["no-store"]
    assert not ({"etag", "last-modified", "expires"} & set(response.headers))


def _payload(evidence: PolicyEvidence) -> dict[str, str]:
    return {
        "policy_fingerprint": evidence.policy_fingerprint,
        "route_manifest_revision": evidence.route_manifest_revision,
        "backend_policy_revision": evidence.backend_policy_revision,
    }


def test_attestation_loads_exact_current_evidence_for_every_request(monkeypatch):
    evidence = iter((EVIDENCE_A, EVIDENCE_B))
    app = _focused_app(monkeypatch, lambda: next(evidence))

    with TestClient(app) as client:
        first = client.get("/_internal/launch-policy-attestation")
        second = client.get(
            "/_internal/launch-policy-attestation",
            headers={"If-None-Match": '"legacy"'},
        )

    assert first.json() == _payload(EVIDENCE_A)
    assert second.json() == _payload(EVIDENCE_B)
    _assert_no_store_no_validator(first, 200)
    _assert_no_store_no_validator(second, 200)


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (HTTPException(status_code=503, detail="evidence unavailable"), 503),
        (HTTPException(status_code=500, detail="explicit internal failure"), 500),
        (RuntimeError("invalid evidence artifact"), 503),
        (ValueError("invalid evidence shape"), 503),
        (FileNotFoundError("missing evidence artifact"), 503),
    ],
)
def test_attestation_loader_failures_keep_the_policy_cache_contract(
    monkeypatch,
    failure: Exception,
    expected_status: int,
):
    def fail() -> PolicyEvidence:
        raise failure

    with TestClient(_focused_app(monkeypatch, fail)) as client:
        response = client.get(
            "/_internal/launch-policy-attestation",
            headers={"If-None-Match": '"legacy"'},
        )

    _assert_no_store_no_validator(response, expected_status)


def test_attestation_router_identity_and_openapi_exclusion(monkeypatch):
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/_internal/launch-policy-attestation"
    )

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert launch_policy_api.router.prefix == "/_internal"
    assert launch_policy_api.router.include_in_schema is False
    assert route.name == "launch_policy_attestation"
    assert route.methods == {"GET"}
    assert "/_internal/launch-policy-attestation" not in schema["paths"]


def test_attestation_is_mounted_before_final_policy_middleware_registration():
    source = (AGENT / "server.py").read_text(encoding="utf-8")

    assert "from launch_policy_api import router as launch_policy_router" in source
    assert source.index("app.include_router(launch_policy_router)") < source.index(
        "app.add_middleware(PolicyHttpMiddleware"
    )


def test_attestation_uses_an_explicit_three_field_payload():
    source = (AGENT / "launch_policy_api.py").read_text(encoding="utf-8")

    assert "asdict" not in source
