from __future__ import annotations

import sys
import hashlib
from dataclasses import replace
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
from sitemap_store import (  # noqa: E402
    SitemapBundleStore,
    StoredBundle,
    compute_batch_revision,
)


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


def _bundle(revision: str, main: bytes = b"<urlset>pinned</urlset>") -> StoredBundle:
    documents = {
        "sitemap.xml": main,
        "sitemap-media.xml": b"<urlset>synthetic-media</urlset>",
        "sitemap-index.xml": b"<sitemapindex>synthetic-index</sitemapindex>",
    }
    evidence = {
        "policy_fingerprint": "a" * 64,
        "route_manifest_revision": "launch-indexing-policy-v1",
        "backend_policy_revision": INDEX_POLICY_REVISION,
    }
    if len(revision) == 64 and revision.islower() and revision.isalnum():
        revision = compute_batch_revision(
            fingerprint=evidence["policy_fingerprint"],
            route_revision=evidence["route_manifest_revision"],
            policy_revision=evidence["backend_policy_revision"],
            main=documents["sitemap.xml"],
            media=documents["sitemap-media.xml"],
        )
    return StoredBundle(
        batch_revision=revision,
        metadata={
            "schema_version": 1,
            "batch_revision": revision,
            "renderer_evidence": evidence,
            "documents": {
                name: hashlib.sha256(body).hexdigest()
                for name, body in documents.items()
            },
        },
        documents=documents,
    )


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
    "failure",
    [
        HTTPException(status_code=503, detail="evidence unavailable"),
        HTTPException(status_code=500, detail="secret upstream failure"),
        RuntimeError("invalid evidence artifact"),
        ValueError("invalid evidence shape"),
        FileNotFoundError("missing evidence artifact"),
    ],
)
def test_attestation_loader_failures_keep_the_policy_cache_contract(
    monkeypatch,
    failure: Exception,
):
    def fail() -> PolicyEvidence:
        raise failure

    with TestClient(_focused_app(monkeypatch, fail)) as client:
        response = client.get(
            "/_internal/launch-policy-attestation",
            headers={"If-None-Match": '"legacy"'},
        )

    assert response.json() == {"detail": "Launch policy evidence unavailable"}
    _assert_no_store_no_validator(response, 503)


def test_attestation_post_loader_field_failure_is_sanitized(monkeypatch):
    class GetterFailureEvidence:
        @property
        def policy_fingerprint(self):
            raise RuntimeError("secret")

        route_manifest_revision = EVIDENCE_A.route_manifest_revision
        backend_policy_revision = EVIDENCE_A.backend_policy_revision

    app = _focused_app(monkeypatch, lambda: GetterFailureEvidence())

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/_internal/launch-policy-attestation",
            headers={"If-None-Match": '"legacy"'},
        )

    assert response.json() == {"detail": "Launch policy evidence unavailable"}
    assert "secret" not in response.text
    _assert_no_store_no_validator(response, 503)


def test_attestation_post_loader_serialization_failure_is_sanitized(monkeypatch):
    class SerializationFailureEvidence:
        policy_fingerprint = object()
        route_manifest_revision = EVIDENCE_A.route_manifest_revision
        backend_policy_revision = EVIDENCE_A.backend_policy_revision

    app = _focused_app(monkeypatch, lambda: SerializationFailureEvidence())

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/_internal/launch-policy-attestation",
            headers={"If-None-Match": '"legacy"'},
        )

    assert response.json() == {"detail": "Launch policy evidence unavailable"}
    _assert_no_store_no_validator(response, 503)


def test_attestation_does_not_catch_base_exceptions(monkeypatch):
    class FatalEvidenceFailure(BaseException):
        pass

    def fail() -> PolicyEvidence:
        raise FatalEvidenceFailure

    assert launch_policy_api is not None
    monkeypatch.setattr(launch_policy_api, "current_policy_evidence", fail)
    with pytest.raises(FatalEvidenceFailure):
        launch_policy_api.launch_policy_attestation()


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


def test_pinned_main_sitemap_reads_only_requested_batch(tmp_path, monkeypatch):
    store = SitemapBundleStore(tmp_path / "bundles")
    previous = _bundle("a" * 64, b"<urlset>previous-pinned</urlset>")
    active = _bundle("b" * 64, b"<urlset>active-pinned</urlset>")
    store.publish(previous)
    store.publish(active)
    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: store)
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(
            f"/_internal/launch-sitemaps/sitemap.xml?batch={previous.batch_revision}",
            headers={"If-None-Match": '"legacy"'},
        )

    assert response.content == previous.documents["sitemap.xml"]
    assert response.headers["x-launch-sitemap-batch-revision"] == previous.batch_revision
    assert response.headers["content-type"].startswith("application/xml")
    _assert_no_store_no_validator(response, 200)


def test_active_index_reads_active_and_exposes_all_immutable_evidence(
    tmp_path, monkeypatch
):
    store = SitemapBundleStore(tmp_path / "bundles")
    active = _bundle("b" * 64)
    store.publish(active)
    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: store)
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(
            "/_internal/launch-sitemaps/sitemap-index.xml",
            headers={"If-None-Match": '"legacy"'},
        )

    assert response.content == active.documents["sitemap-index.xml"]
    assert response.headers["x-launch-policy-fingerprint"] == EVIDENCE_A.policy_fingerprint
    assert response.headers["x-launch-route-manifest-revision"] == EVIDENCE_A.route_manifest_revision
    assert response.headers["x-launch-backend-policy-revision"] == EVIDENCE_A.backend_policy_revision
    assert response.headers["x-launch-sitemap-batch-revision"] == active.batch_revision
    assert "x-launch-sitemap-requested-batch" not in response.headers
    _assert_no_store_no_validator(response, 200)


def test_sitemap_uses_retained_immutable_evidence_when_current_policy_differs(
    tmp_path, monkeypatch
):
    store = SitemapBundleStore(tmp_path / "bundles")
    retained = _bundle("a" * 64)
    store.publish(retained)
    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: store)
    app = _focused_app(monkeypatch, lambda: EVIDENCE_B)

    with TestClient(app) as client:
        response = client.get(
            f"/_internal/launch-sitemaps/sitemap.xml?batch={retained.batch_revision}"
        )

    assert response.content == retained.documents["sitemap.xml"]
    assert response.headers["x-launch-policy-fingerprint"] == "a" * 64
    assert response.headers["x-launch-route-manifest-revision"] == (
        "launch-indexing-policy-v1"
    )
    assert response.headers["x-launch-backend-policy-revision"] == INDEX_POLICY_REVISION
    assert response.headers["x-launch-sitemap-batch-revision"] == retained.batch_revision
    assert response.headers["x-launch-sitemap-requested-batch"] == retained.batch_revision
    _assert_no_store_no_validator(response, 200)


def test_sitemap_rejects_forged_metadata_evidence_for_unchanged_batch(
    monkeypatch,
):
    retained = _bundle("a" * 64)
    forged = replace(
        retained,
        metadata={
            **retained.metadata,
            "renderer_evidence": {
                **retained.metadata["renderer_evidence"],
                "policy_fingerprint": "e" * 64,
            },
        },
    )

    class Store:
        def load_batch(self, _revision):
            return forged

    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: Store())
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(
            f"/_internal/launch-sitemaps/sitemap.xml?batch={retained.batch_revision}"
        )

    assert response.status_code == 503
    assert response.headers["x-launch-indexing-policy"] == "failed-open"
    assert not any(
        name.startswith("x-launch-policy") or name.startswith("x-launch-sitemap")
        for name in response.headers
    )


def test_sitemap_rejects_control_character_in_immutable_revision(monkeypatch):
    retained = _bundle("a" * 64)
    forged = replace(
        retained,
        metadata={
            **retained.metadata,
            "renderer_evidence": {
                **retained.metadata["renderer_evidence"],
                "route_manifest_revision": "ok\r\nInjected: yes",
            },
        },
    )

    class Store:
        def load_batch(self, _revision):
            return forged

    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: Store())
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(
            f"/_internal/launch-sitemaps/sitemap.xml?batch={retained.batch_revision}"
        )

    assert response.status_code == 503
    assert response.headers["x-launch-indexing-policy"] == "failed-open"
    assert "x-launch-route-manifest-revision" not in response.headers


@pytest.mark.parametrize(
    "query",
    [
        "batch=",
        "batch=ABC",
        "batch=0",
        "batch=" + "a" * 64 + "&x=1",
        "batch=" + "a" * 64 + "&batch=" + "a" * 64,
        "batch%3D" + "a" * 64,
        "batch=" + "a" * 63 + "%61",
        "batch=" + "a" * 64 + "&",
        "&batch=" + "a" * 64,
    ],
)
def test_sitemap_queries_are_rejected_without_active_fallback(
    tmp_path, monkeypatch, query
):
    store = SitemapBundleStore(tmp_path / "bundles")
    active = _bundle("b" * 64)
    store.publish(active)

    class NoFallbackStore:
        def load_batch(self, _revision):
            raise RuntimeError("invalid pinned request")

        def load_active(self):
            raise AssertionError("invalid pinned request must not load active")

    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: NoFallbackStore())
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(f"/_internal/launch-sitemaps/sitemap.xml?{query}")

    assert response.status_code == 503
    assert response.json() == {"detail": "Launch sitemap document unavailable"}
    assert response.headers["x-launch-indexing-policy"] == "failed-open"
    assert not any(name.startswith("x-launch-") and name != "x-launch-indexing-policy" for name in response.headers)
    _assert_no_store_no_validator(response, 503)


@pytest.mark.parametrize(
    "path",
    [
        "/_internal/launch-sitemaps/sitemap.xml",
        "/_internal/launch-sitemaps/sitemap.xml?batch=bad",
        f"/_internal/launch-sitemaps/sitemap.xml?batch={'c' * 64}",
        f"/_internal/launch-sitemaps/sitemap-media.xml?batch={'c' * 64}",
        f"/_internal/launch-sitemaps/sitemap-index.xml?batch={'c' * 64}",
        f"/_internal/launch-sitemaps/unknown.xml?batch={'a' * 64}",
    ],
)
def test_sitemap_document_failures_are_sanitized_no_store(
    tmp_path,
    monkeypatch,
    path: str,
):
    store = SitemapBundleStore(tmp_path / "bundles")
    store.publish(_bundle("a" * 64))
    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: store)
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(path, headers={"If-Modified-Since": "today"})

    assert response.json() == {"detail": "Launch sitemap document unavailable"}
    _assert_no_store_no_validator(response, 503)


def test_sitemap_document_catches_document_access_failure(monkeypatch):
    class BrokenDocuments:
        def __getitem__(self, _name):
            raise RuntimeError("secret document failure")

    class Store:
        def load_batch(self, _batch):
            return type(
                "Bundle",
                (),
                {"batch_revision": "a" * 64, "documents": BrokenDocuments()},
            )()

        def load_active(self):
            raise AssertionError("GET must never fall back to active state")

    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: Store())
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(
            f"/_internal/launch-sitemaps/sitemap.xml?batch={'a' * 64}"
        )

    assert response.json() == {"detail": "Launch sitemap document unavailable"}
    assert "secret" not in response.text
    _assert_no_store_no_validator(response, 503)


def test_sitemap_document_catches_store_getter_failure(monkeypatch):
    def fail_store_getter():
        raise RuntimeError("secret store getter failure")

    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", fail_store_getter)
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(
            f"/_internal/launch-sitemaps/sitemap.xml?batch={'a' * 64}"
        )

    assert response.json() == {"detail": "Launch sitemap document unavailable"}
    assert "secret" not in response.text
    _assert_no_store_no_validator(response, 503)


def test_sitemap_document_catches_response_serialization_failure(monkeypatch):
    class Store:
        def load_batch(self, _batch):
            return type(
                "Bundle",
                (),
                {"batch_revision": "a" * 64, "documents": {"sitemap.xml": object()}},
            )()

    monkeypatch.setattr(launch_policy_api, "get_sitemap_bundle_store", lambda: Store())
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)

    with TestClient(app) as client:
        response = client.get(
            f"/_internal/launch-sitemaps/sitemap.xml?batch={'a' * 64}"
        )

    assert response.json() == {"detail": "Launch sitemap document unavailable"}
    _assert_no_store_no_validator(response, 503)


def test_sitemap_route_identity_and_openapi_exclusion(monkeypatch):
    app = _focused_app(monkeypatch, lambda: EVIDENCE_A)
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/_internal/launch-sitemaps/{document}"
    )

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert route.name == "launch_sitemap_document"
    assert route.methods == {"GET"}
    assert "/_internal/launch-sitemaps/{document}" not in schema["paths"]
