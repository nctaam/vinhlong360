from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

if __package__:
    from .ai_disclosure import load_ai_disclosure
    from .route_manifest import EXPECTED_REVISION as ROUTE_MANIFEST_REVISION
    from .route_manifest import load_route_manifest
else:
    from ai_disclosure import load_ai_disclosure
    from route_manifest import EXPECTED_REVISION as ROUTE_MANIFEST_REVISION
    from route_manifest import load_route_manifest


INDEX_POLICY_REVISION = "index-policy-v1"
RESPONSE_MATRIX_REVISION = "launch-safety-matrix-v1"
CACHE_ISOLATION_REVISION = "launch-cache-isolation-v1"
SITEMAP_PROTOCOL_REVISION = "pinned-sitemap-bundle-v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _validated_revision(value: object, label: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{label} must be a string")
    if not value or value.strip() != value:
        raise ValueError(f"{label} must be a non-empty canonical revision")
    return value


def _validated_sha256(value: object, label: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{label} must be a string")
    if _SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def build_policy_fingerprint(
    *,
    route_revision: str,
    route_digest: str,
    disclosure_revision: str,
    disclosure_digest: str,
) -> str:
    payload = {
        "index_policy": _validated_revision(
            INDEX_POLICY_REVISION, "index policy revision"
        ),
        "response_matrix": _validated_revision(
            RESPONSE_MATRIX_REVISION, "response matrix revision"
        ),
        "cache_isolation": _validated_revision(
            CACHE_ISOLATION_REVISION, "cache isolation revision"
        ),
        "sitemap_protocol": _validated_revision(
            SITEMAP_PROTOCOL_REVISION, "sitemap protocol revision"
        ),
        "route_artifact": {
            "revision": _validated_revision(route_revision, "route revision"),
            "sha256": _validated_sha256(route_digest, "route digest"),
        },
        "disclosure_artifact": {
            "revision": _validated_revision(disclosure_revision, "disclosure revision"),
            "sha256": _validated_sha256(disclosure_digest, "disclosure digest"),
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256(canonical).hexdigest()


@dataclass(frozen=True)
class PolicyEvidence:
    policy_fingerprint: str
    route_manifest_revision: str
    backend_policy_revision: str

    def __post_init__(self) -> None:
        _validated_sha256(self.policy_fingerprint, "policy fingerprint")
        route_revision = _validated_revision(
            self.route_manifest_revision, "route manifest revision"
        )
        if route_revision != ROUTE_MANIFEST_REVISION:
            raise ValueError("route manifest revision is not current")
        backend_revision = _validated_revision(
            self.backend_policy_revision, "backend policy revision"
        )
        if backend_revision != INDEX_POLICY_REVISION:
            raise ValueError("backend policy revision is not current")


def current_policy_evidence() -> PolicyEvidence:
    route = load_route_manifest()
    disclosure = load_ai_disclosure()
    return PolicyEvidence(
        policy_fingerprint=build_policy_fingerprint(
            route_revision=route.revision,
            route_digest=route.artifact.sha256,
            disclosure_revision=disclosure.revision,
            disclosure_digest=disclosure.artifact.sha256,
        ),
        route_manifest_revision=route.revision,
        backend_policy_revision=INDEX_POLICY_REVISION,
    )
