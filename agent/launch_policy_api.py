from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

if __package__:
    from .launch_evidence import current_policy_evidence
    from .sitemap_store import SitemapBundleStore
else:
    from launch_evidence import current_policy_evidence
    from sitemap_store import SitemapBundleStore


router = APIRouter(prefix="/_internal", include_in_schema=False)
logger = logging.getLogger(__name__)


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
    batch: str | None = None,
) -> Response:
    try:
        if document != "sitemap.xml" or batch is None:
            raise ValueError("unsupported or unpinned sitemap document")
        bundle = get_sitemap_bundle_store().load_batch(batch)
        body = bundle.documents["sitemap.xml"]
        revision = bundle.batch_revision
        return Response(
            content=body,
            media_type="application/xml",
            headers={"X-Launch-Sitemap-Batch-Revision": revision},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Launch sitemap document unavailable",
        ) from exc
