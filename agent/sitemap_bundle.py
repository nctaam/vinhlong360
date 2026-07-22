"""PostgreSQL-only generation of complete immutable sitemap bundles."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
for import_root in (PROJECT_DIR, AGENT_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


REFRESH_UNAVAILABLE_ERROR = "sitemap refresh unavailable"


class SitemapRefreshUnavailable(RuntimeError):
    """The complete PostgreSQL sitemap bundle cannot be generated."""


def _open_sitemap_snapshot(database):
    """Load the snapshot context lazily so importing this CLI is side-effect free."""
    if __package__:
        from .sitemap_snapshot import open_sitemap_snapshot
    else:
        from sitemap_snapshot import open_sitemap_snapshot
    return open_sitemap_snapshot(database)


def _load_database():
    if __package__:
        from .database import db
    else:
        from database import db
    return db


def _load_render_dependencies():
    if __package__:
        from .ai_disclosure import LoadedAiDisclosure, load_ai_disclosure
        from .launch_evidence import PolicyEvidence, current_policy_evidence
        from .route_manifest import LoadedRouteManifest, load_route_manifest
        from .sitemap_render import (
            compute_batch_revision,
            render_main_sitemap,
            render_media_sitemap,
            render_sitemap_index,
        )
    else:
        from ai_disclosure import LoadedAiDisclosure, load_ai_disclosure
        from launch_evidence import PolicyEvidence, current_policy_evidence
        from route_manifest import LoadedRouteManifest, load_route_manifest
        from sitemap_render import (
            compute_batch_revision,
            render_main_sitemap,
            render_media_sitemap,
            render_sitemap_index,
        )
    return {
        "LoadedAiDisclosure": LoadedAiDisclosure,
        "LoadedRouteManifest": LoadedRouteManifest,
        "PolicyEvidence": PolicyEvidence,
        "compute_batch_revision": compute_batch_revision,
        "current_policy_evidence": current_policy_evidence,
        "load_ai_disclosure": load_ai_disclosure,
        "load_route_manifest": load_route_manifest,
        "render_main_sitemap": render_main_sitemap,
        "render_media_sitemap": render_media_sitemap,
        "render_sitemap_index": render_sitemap_index,
    }


def _require_postgresql(database) -> None:
    if getattr(database, "_use_pg", False) is not True:
        raise SitemapRefreshUnavailable(
            "complete sitemap refresh requires PostgreSQL"
        )


def _document_hashes(documents: dict[str, bytes]) -> dict[str, str]:
    return {
        name: hashlib.sha256(documents[name]).hexdigest()
        for name in ("sitemap.xml", "sitemap-media.xml", "sitemap-index.xml")
    }


def _validate_index_document(index: bytes, origin: str, batch: str) -> None:
    if index.startswith(b"\xef\xbb\xbf") or index.endswith(b"\n"):
        raise ValueError("sitemap index has an invalid encoding boundary")
    try:
        root = ElementTree.fromstring(index)
    except ElementTree.ParseError as error:
        raise ValueError("sitemap index is not valid XML") from error
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    if root.tag != f"{{{namespace}}}sitemapindex" or len(root) != 2:
        raise ValueError("sitemap index must contain exactly two children")
    expected = (
        f"{origin}/sitemap.xml?batch={batch}",
        f"{origin}/sitemap-media.xml?batch={batch}",
    )
    for node, location in zip(root, expected, strict=True):
        if node.tag != f"{{{namespace}}}sitemap" or len(node) != 1:
            raise ValueError("sitemap index child shape is invalid")
        loc = node[0]
        if loc.tag != f"{{{namespace}}}loc" or loc.text != location:
            raise ValueError("sitemap index child is not pinned to the batch")


def build_bundle(
    *,
    database: Any | None = None,
    manifest: Any | None = None,
    evidence: Any | None = None,
    disclosure: Any | None = None,
) -> Any:
    """Render all three documents from one open, read-only PostgreSQL snapshot."""
    deps = _load_render_dependencies()
    database = _load_database() if database is None else database
    _require_postgresql(database)
    manifest, evidence, disclosure = _resolve_bundle_inputs(
        deps, manifest, evidence, disclosure
    )
    main, media, batch_revision, index = _render_bundle_documents(
        deps, database, manifest, evidence, disclosure
    )

    documents = {
        "sitemap.xml": main,
        "sitemap-media.xml": media,
        "sitemap-index.xml": index,
    }
    if any(type(body) is not bytes for body in documents.values()):
        raise TypeError("sitemap documents must contain exact bytes")
    _validate_index_document(
        index,
        manifest.data["canonical_origin"],
        batch_revision,
    )

    if __package__:
        from .sitemap_store import SITEMAP_METADATA_SCHEMA_VERSION, StoredBundle
    else:
        from sitemap_store import SITEMAP_METADATA_SCHEMA_VERSION, StoredBundle
    metadata = _bundle_metadata(
        SITEMAP_METADATA_SCHEMA_VERSION, batch_revision, documents, evidence
    )
    return StoredBundle(batch_revision, metadata, documents)


def _resolve_bundle_inputs(deps, manifest, evidence, disclosure):
    manifest = deps["load_route_manifest"]() if manifest is None else manifest
    evidence = deps["current_policy_evidence"]() if evidence is None else evidence
    disclosure = deps["load_ai_disclosure"]() if disclosure is None else disclosure
    if type(manifest) is not deps["LoadedRouteManifest"]:
        raise TypeError("manifest must be LoadedRouteManifest")
    if type(evidence) is not deps["PolicyEvidence"]:
        raise TypeError("evidence must be PolicyEvidence")
    if type(disclosure) is not deps["LoadedAiDisclosure"]:
        raise TypeError("disclosure must be LoadedAiDisclosure")
    return manifest, evidence, disclosure


def _render_bundle_documents(deps, database, manifest, evidence, disclosure):
    with _open_sitemap_snapshot(database) as snapshot:
        main = deps["render_main_sitemap"](snapshot, manifest, evidence)
        media = deps["render_media_sitemap"](snapshot, manifest, evidence, disclosure)
        if type(main) is not bytes or type(media) is not bytes:
            raise TypeError("sitemap renderers must return exact bytes")
        batch_revision = deps["compute_batch_revision"](
            fingerprint=evidence.policy_fingerprint,
            route_revision=evidence.route_manifest_revision,
            policy_revision=evidence.backend_policy_revision,
            main=main,
            media=media,
        )
        index = deps["render_sitemap_index"](
            manifest.data["canonical_origin"], batch_revision
        )
    return main, media, batch_revision, index


def _bundle_metadata(schema_version, batch_revision, documents, evidence):
    return {
        "schema_version": schema_version,
        "batch_revision": batch_revision,
        "documents": _document_hashes(documents),
        "renderer_evidence": {
            "policy_fingerprint": evidence.policy_fingerprint,
            "route_manifest_revision": evidence.route_manifest_revision,
            "backend_policy_revision": evidence.backend_policy_revision,
        },
    }


def refresh(
    *,
    database: Any | None = None,
    store: Any | None = None,
    release_root: str | Path | None = None,
    manifest: Any | None = None,
    evidence: Any | None = None,
    disclosure: Any | None = None,
) -> Any:
    """Build one complete bundle and publish it atomically through the store."""
    database = _load_database() if database is None else database
    bundle = build_bundle(
        database=database,
        manifest=manifest,
        evidence=evidence,
        disclosure=disclosure,
    )
    if store is None:
        if __package__:
            from .sitemap_store import SitemapBundleStore
        else:
            from sitemap_store import SitemapBundleStore
        if release_root is None:
            release_root = os.environ.get("SITEMAP_BUNDLE_RELEASE_ROOT")
        store = SitemapBundleStore.from_release_root(
            Path(release_root) if release_root else None
        )
    store.publish(bundle)
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("refresh",))
    args = parser.parse_args(argv)
    if args.command == "refresh":
        try:
            refresh()
        except Exception:
            print(REFRESH_UNAVAILABLE_ERROR, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
