from __future__ import annotations

import logging
import re
from hashlib import sha256

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

if __package__:
    from .launch_evidence import current_policy_evidence
    from .sitemap_store import SitemapBundleStore, compute_batch_revision
else:
    from launch_evidence import current_policy_evidence
    from sitemap_store import SitemapBundleStore, compute_batch_revision


router = APIRouter(prefix="/_internal", include_in_schema=False)
logger = logging.getLogger(__name__)
_SITEMAP_DOCUMENTS = frozenset(
    ("sitemap-index.xml", "sitemap.xml", "sitemap-media.xml")
)
_SITEMAP_HASH_KEYS = frozenset(_SITEMAP_DOCUMENTS)
_RENDERER_EVIDENCE_KEYS = frozenset(
    (
        "policy_fingerprint",
        "route_manifest_revision",
        "backend_policy_revision",
    )
)


def _validate_header_revision(value: object, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"sitemap evidence {label} is invalid")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in value):
        raise ValueError(f"sitemap evidence {label} contains invalid header characters")
    return value
_BATCH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def get_sitemap_bundle_store() -> SitemapBundleStore:
    return SitemapBundleStore.from_release_root()


def validate_sitemap_bundle_on_startup(app, store=None) -> bool:
    """Record selective sitemap availability without blocking closed startup."""
    try:
        selected_store = store if store is not None else get_sitemap_bundle_store()
        bundle = selected_store.load_active_on_startup()
        revision = bundle.batch_revision
    except Exception:
        app.state.launch_sitemaps_available = False
        app.state.launch_sitemap_batch_revision = None
        logger.warning("Immutable launch sitemap state unavailable at startup")
        return False
    app.state.launch_sitemaps_available = True
    app.state.launch_sitemap_batch_revision = revision
    return True


@router.get("/launch-policy-attestation")
def launch_policy_attestation() -> JSONResponse:
    try:
        evidence = current_policy_evidence()
        payload = {
            "policy_fingerprint": evidence.policy_fingerprint,
            "route_manifest_revision": evidence.route_manifest_revision,
            "backend_policy_revision": evidence.backend_policy_revision,
        }
        return JSONResponse(content=payload)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Launch policy evidence unavailable",
        ) from exc


@router.get("/launch-sitemaps/{document}")
def launch_sitemap_document(
    document: str,
    request: Request,
) -> Response:
    def failure() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Launch sitemap document unavailable"},
            headers={
                "Cache-Control": "no-store",
                "X-Launch-Indexing-Policy": "failed-open",
            },
        )

    try:
        if document not in _SITEMAP_DOCUMENTS:
            raise ValueError("unsupported sitemap document")
        raw_query = request.scope.get("query_string", b"")
        if type(raw_query) is not bytes:
            raise ValueError("invalid sitemap query")
        if raw_query == b"":
            requested_batch = None
        else:
            if not raw_query.startswith(b"batch="):
                raise ValueError("invalid sitemap query")
            raw_batch = raw_query[len(b"batch=") :]
            try:
                requested_batch = raw_batch.decode("ascii")
            except UnicodeDecodeError as error:
                raise ValueError("invalid sitemap batch") from error
            if _BATCH_PATTERN.fullmatch(requested_batch) is None:
                raise ValueError("invalid sitemap batch")

        if document != "sitemap-index.xml" and requested_batch is None:
            raise ValueError("child sitemap requires a pinned batch")
        if document == "sitemap-index.xml" and requested_batch is None:
            bundle = get_sitemap_bundle_store().load_active()
        elif requested_batch is not None:
            bundle = get_sitemap_bundle_store().load_batch(requested_batch)
        else:
            raise ValueError("invalid sitemap query")

        revision = bundle.batch_revision
        if type(revision) is not str or _BATCH_PATTERN.fullmatch(revision) is None:
            raise ValueError("invalid served sitemap batch")
        metadata = bundle.metadata
        if not isinstance(metadata, dict):
            raise ValueError("sitemap evidence unavailable")
        renderer_evidence = metadata.get("renderer_evidence")
        if not isinstance(renderer_evidence, dict) or set(
            renderer_evidence
        ) != _RENDERER_EVIDENCE_KEYS:
            raise ValueError("sitemap evidence shape mismatch")
        fingerprint = renderer_evidence.get("policy_fingerprint")
        route_revision = renderer_evidence.get("route_manifest_revision")
        backend_revision = renderer_evidence.get("backend_policy_revision")
        if type(fingerprint) is not str or _BATCH_PATTERN.fullmatch(fingerprint) is None:
            raise ValueError("sitemap policy fingerprint is invalid")
        route_revision = _validate_header_revision(route_revision, "route revision")
        backend_revision = _validate_header_revision(
            backend_revision, "backend policy revision"
        )
        if metadata.get("batch_revision") != revision:
            raise ValueError("sitemap metadata revision mismatch")
        body = bundle.documents[document]
        if type(body) is not bytes:
            raise ValueError("sitemap document is not bytes")
        main_body = bundle.documents["sitemap.xml"]
        media_body = bundle.documents["sitemap-media.xml"]
        if type(main_body) is not bytes or type(media_body) is not bytes:
            raise ValueError("sitemap bundle documents are not bytes")
        if compute_batch_revision(
            fingerprint=fingerprint,
            route_revision=route_revision,
            policy_revision=backend_revision,
            main=main_body,
            media=media_body,
        ) != revision:
            raise ValueError("sitemap batch evidence mismatch")
        document_hashes = metadata.get("documents")
        if (
            not isinstance(document_hashes, dict)
            or set(document_hashes) != _SITEMAP_HASH_KEYS
            or type(document_hashes.get(document)) is not str
            or not _BATCH_PATTERN.fullmatch(document_hashes[document])
            or document_hashes[document] != sha256(body).hexdigest()
        ):
            raise ValueError("sitemap document hash mismatch")
        headers = {
            "Cache-Control": "no-store",
            "X-Launch-Policy-Fingerprint": fingerprint,
            "X-Launch-Route-Manifest-Revision": route_revision,
            "X-Launch-Backend-Policy-Revision": backend_revision,
            "X-Launch-Sitemap-Batch-Revision": revision,
        }
        if requested_batch is not None:
            if requested_batch != revision:
                raise ValueError("requested sitemap batch mismatch")
            headers["X-Launch-Sitemap-Requested-Batch"] = requested_batch
        return Response(
            content=body,
            media_type="application/xml",
            headers=headers,
        )
    except Exception as exc:
        logger.warning("Immutable launch sitemap state unavailable: %s", type(exc).__name__)
        return failure()
