from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import unquote_to_bytes

if __package__:
    from .launch_artifacts import (
        ImmutableJSONObject,
        LoadedArtifact,
        _freeze_json,
        load_artifact,
    )
else:
    from launch_artifacts import (
        ImmutableJSONObject,
        LoadedArtifact,
        _freeze_json,
        load_artifact,
    )


ARTIFACT_NAME = "launch-indexing-policy.json"
EXPECTED_REVISION = "launch-indexing-policy-v1"
CANONICAL_ORIGIN = "https://vinhlong360.vn"
UNKNOWN_POLICY = "noindex-follow-public"
NORMALIZATION = MappingProxyType(
    {
        "percent_decode": "utf8-once",
        "encoded_separator_policy": "reject",
        "dot_segment_policy": "reject",
        "repeated_slash_policy": "redirect-canonical",
        "trailing_slash_policy": "redirect-except-root",
        "query_policy": "noindex-except-sitemap-batch",
    }
)
TOP_LEVEL_KEYS = frozenset(
    {
        "backend_ingress_exceptions",
        "canonical_origin",
        "dynamic_templates",
        "exact_routes",
        "normalization",
        "revision",
        "schema_version",
        "sensitive_prefixes",
        "unknown_policy",
    }
)
EXACT_KEYS = frozenset({"classification", "path", "sitemap"})
PREFIX_KEYS = frozenset({"classification", "prefix"})
INGRESS_KEYS = frozenset({"prefix", "review_reason", "upstream"})
TEMPLATE_KEYS = frozenset({"authority", "sitemap", "template"})
EXACT_CLASSIFICATIONS = frozenset({"indexable-public", "noindex-follow-public"})
SENSITIVE_CLASSIFICATIONS = frozenset({"crawl-blocked-sensitive"})
INGRESS_UPSTREAMS = frozenset({"agent", "bot-gateway"})
TEMPLATE_AUTHORITIES = frozenset({"backend-entity", "backend-ward", "fixed-noindex"})
PLACEHOLDER = re.compile(r"^\{([a-z_][a-z0-9_]*)\}$")
JS_EXTRA_WHITESPACE = frozenset(
    "\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
JS_TRIM_CHARACTERS = "\u0009\u000a\u000b\u000c\u000d\u0020" + "".join(
    JS_EXTRA_WHITESPACE
)


@dataclass(frozen=True)
class LoadedRouteManifest:
    artifact: LoadedArtifact
    revision: str
    data: ImmutableJSONObject

    def __post_init__(self) -> None:
        snapshot = validate_route_manifest_data(self.data)
        if self.revision != snapshot["revision"]:
            raise ValueError("route manifest revision does not match validated data")
        if snapshot != self.artifact.data:
            raise ValueError("route manifest data does not match artifact data")
        object.__setattr__(self, "data", snapshot)


@dataclass(frozen=True)
class RouteDecision:
    classification: str
    canonical_path: str | None


def _record(value: object, label: str) -> Mapping[str, Any]:
    if type(value) is not dict and not isinstance(value, MappingProxyType):
        raise ValueError(f"route manifest {label} must be a plain JSON object")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    keys: frozenset[str],
    label: str,
) -> None:
    actual = list(value.keys())
    if any(type(key) is not str for key in actual) or set(actual) != keys:
        raise ValueError(f"route manifest {label} keys mismatch")


def _array(value: object, label: str) -> Sequence[Any]:
    if type(value) is not list and type(value) is not tuple:
        raise ValueError(f"route manifest {label} must be a plain JSON array")
    return value


def _string_choice(value: object, choices: frozenset[str], message: str) -> str:
    if type(value) is not str or value not in choices:
        raise ValueError(f"route manifest {message}")
    return value


def _has_forbidden_path_character(value: str) -> bool:
    return any(
        ord(character) <= 0x20
        or ord(character) == 0x7F
        or character in "{}"
        or character in JS_EXTRA_WHITESPACE
        for character in value
    )


def _canonical_path(value: object, label: str) -> str:
    if type(value) is not str:
        raise ValueError(f"route manifest {label} is not canonical")
    if (
        not value.startswith("/")
        or "?" in value
        or "#" in value
        or "//" in value
        or "%" in value
        or "\\" in value
        or _has_forbidden_path_character(value)
        or (value != "/" and value.endswith("/"))
        or any(segment in {".", ".."} for segment in value.split("/"))
    ):
        raise ValueError(f"route manifest {label} is not canonical")
    return value


def _template_signature(template: object) -> str:
    if type(template) is not str:
        raise ValueError("route manifest dynamic template is invalid")

    names: set[str] = set()
    signature_segments: list[str] = []
    concrete_segments: list[str] = []
    for segment in template.split("/"):
        if "{" not in segment and "}" not in segment:
            signature_segments.append(segment)
            concrete_segments.append(segment)
            continue

        match = PLACEHOLDER.fullmatch(segment)
        name = match.group(1) if match else None
        if name is None or name in names:
            raise ValueError("route manifest dynamic template is invalid")
        names.add(name)
        signature_segments.append("{}")
        concrete_segments.append("value")

    if not names:
        raise ValueError("route manifest dynamic template is invalid")
    _canonical_path("/".join(concrete_segments), "dynamic template")
    return "/".join(signature_segments)


def _matches_template(path: str, template: str) -> bool:
    path_segments = path.split("/")[1:]
    template_segments = template.split("/")[1:]
    return len(path_segments) == len(template_segments) and all(
        PLACEHOLDER.fullmatch(segment) is not None or segment == path_segments[index]
        for index, segment in enumerate(template_segments)
    )


def _templates_overlap(left: str, right: str) -> bool:
    left_segments = left.split("/")
    right_segments = right.split("/")
    if len(left_segments) != len(right_segments):
        return False
    return all(
        PLACEHOLDER.fullmatch(segment) is not None
        or PLACEHOLDER.fullmatch(right_segments[index]) is not None
        or segment == right_segments[index]
        for index, segment in enumerate(left_segments)
    )


def _decode_once(raw_path: str) -> str | None:
    if re.search(r"%(?![0-9A-Fa-f]{2})", raw_path) or re.search(
        r"%2f|%5c", raw_path, re.IGNORECASE
    ):
        return None
    try:
        decoded = unquote_to_bytes(raw_path).decode("utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError):
        return None
    if "\x00" in decoded or re.search(r"%[0-9A-Fa-f]{2}", decoded):
        return None
    if any(segment in {".", ".."} for segment in decoded.split("/")):
        return None
    return decoded


def _segment_match(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _collapse_slashes(path: str) -> str:
    return "/" + "/".join(segment for segment in path.split("/") if segment)


def _sensitive_classification(
    raw_path: str,
    canonical_path: str,
    manifest: LoadedRouteManifest,
) -> str | None:
    for item in manifest.data["sensitive_prefixes"]:
        prefix = item["prefix"]
        if _segment_match(raw_path, prefix) or _segment_match(canonical_path, prefix):
            return item["classification"]
    return None


def _canonical_classification(
    path: str,
    manifest: LoadedRouteManifest,
) -> str:
    for item in manifest.data["exact_routes"]:
        if item["path"] == path:
            return item["classification"]
    for item in manifest.data["dynamic_templates"]:
        if _matches_template(path, item["template"]):
            return item["authority"]
    return manifest.data["unknown_policy"]


def _assert_unique(values: list[str], message: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"route manifest {message}")


def _validate_route_manifest_shape(
    value: object,
    *,
    expected_revision: str = EXPECTED_REVISION,
) -> Mapping[str, Any]:
    manifest = _record(value, "root")
    _exact_keys(manifest, TOP_LEVEL_KEYS, "root")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or type(manifest["revision"]) is not str
        or manifest["revision"] != expected_revision
        or type(manifest["canonical_origin"]) is not str
        or manifest["canonical_origin"] != CANONICAL_ORIGIN
        or type(manifest["unknown_policy"]) is not str
        or manifest["unknown_policy"] != UNKNOWN_POLICY
    ):
        raise ValueError("route manifest fixed fields mismatch")

    normalization = _record(manifest["normalization"], "normalization")
    _exact_keys(normalization, frozenset(NORMALIZATION), "normalization")
    if any(
        type(normalization[key]) is not str or normalization[key] != expected
        for key, expected in NORMALIZATION.items()
    ):
        raise ValueError("route manifest normalization mismatch")

    exact_routes: list[dict[str, Any]] = []
    for index, raw in enumerate(_array(manifest["exact_routes"], "exact_routes")):
        item = _record(raw, f"exact_routes[{index}]")
        _exact_keys(item, EXACT_KEYS, f"exact_routes[{index}]")
        path = _canonical_path(item["path"], "exact path")
        classification = _string_choice(
            item["classification"],
            EXACT_CLASSIFICATIONS,
            "exact route values mismatch",
        )
        if type(item["sitemap"]) is not bool:
            raise ValueError("route manifest exact route values mismatch")
        exact_routes.append(
            {"path": path, "classification": classification, "sitemap": item["sitemap"]}
        )

    sensitive_prefixes: list[dict[str, str]] = []
    for index, raw in enumerate(
        _array(manifest["sensitive_prefixes"], "sensitive_prefixes")
    ):
        item = _record(raw, f"sensitive_prefixes[{index}]")
        _exact_keys(item, PREFIX_KEYS, f"sensitive_prefixes[{index}]")
        prefix = _canonical_path(item["prefix"], "sensitive prefix")
        if prefix == "/":
            raise ValueError("route manifest sensitive prefix cannot be root")
        classification = _string_choice(
            item["classification"],
            SENSITIVE_CLASSIFICATIONS,
            "sensitive classification mismatch",
        )
        sensitive_prefixes.append({"prefix": prefix, "classification": classification})

    ingress_exceptions: list[dict[str, str]] = []
    for index, raw in enumerate(
        _array(manifest["backend_ingress_exceptions"], "backend_ingress_exceptions")
    ):
        item = _record(raw, f"backend_ingress_exceptions[{index}]")
        _exact_keys(item, INGRESS_KEYS, f"backend_ingress_exceptions[{index}]")
        prefix = _canonical_path(item["prefix"], "ingress prefix")
        if prefix == "/":
            raise ValueError("route manifest ingress prefix cannot be root")
        upstream = _string_choice(
            item["upstream"], INGRESS_UPSTREAMS, "ingress exception mismatch"
        )
        review_reason = item["review_reason"]
        if (
            type(review_reason) is not str
            or review_reason.strip(JS_TRIM_CHARACTERS) == ""
        ):
            raise ValueError("route manifest ingress exception mismatch")
        ingress_exceptions.append(
            {"prefix": prefix, "upstream": upstream, "review_reason": review_reason}
        )

    templates: list[dict[str, Any]] = []
    signatures: list[str] = []
    for index, raw in enumerate(
        _array(manifest["dynamic_templates"], "dynamic_templates")
    ):
        item = _record(raw, f"dynamic_templates[{index}]")
        _exact_keys(item, TEMPLATE_KEYS, f"dynamic_templates[{index}]")
        template = item["template"]
        signature = _template_signature(template)
        authority = _string_choice(
            item["authority"],
            TEMPLATE_AUTHORITIES,
            "dynamic authority mismatch",
        )
        if authority == "fixed-noindex":
            if type(item["sitemap"]) is not bool or item["sitemap"] is not False:
                raise ValueError("route manifest dynamic authority mismatch")
            sitemap: str | bool = False
        else:
            if type(item["sitemap"]) is not str or item["sitemap"] != "backend":
                raise ValueError("route manifest dynamic authority mismatch")
            sitemap = "backend"
        templates.append(
            {"template": template, "authority": authority, "sitemap": sitemap}
        )
        signatures.append(signature)

    _assert_unique([item["path"] for item in exact_routes], "duplicate exact route")
    _assert_unique(
        [item["prefix"] for item in sensitive_prefixes], "duplicate sensitive prefix"
    )
    _assert_unique(
        [item["prefix"] for item in ingress_exceptions], "duplicate ingress exception"
    )
    _assert_unique(signatures, "ambiguous dynamic template")
    for left_index, left in enumerate(templates):
        for right in templates[left_index + 1 :]:
            if _templates_overlap(left["template"], right["template"]):
                raise ValueError("route manifest overlapping dynamic template")

    if any(
        ingress["prefix"] == sensitive["prefix"]
        or ingress["prefix"].startswith(f"{sensitive['prefix']}/")
        or sensitive["prefix"].startswith(f"{ingress['prefix']}/")
        for ingress in ingress_exceptions
        for sensitive in sensitive_prefixes
    ):
        raise ValueError("route manifest ingress/sensitive ambiguity")
    if any(
        _matches_template(exact["path"], template["template"])
        for exact in exact_routes
        for template in templates
    ):
        raise ValueError("route manifest exact/template ambiguity")

    return manifest


def validate_route_manifest_data(
    value: object,
    *,
    expected_revision: str = EXPECTED_REVISION,
) -> ImmutableJSONObject:
    _validate_route_manifest_shape(value, expected_revision=expected_revision)
    snapshot = _freeze_json(value)
    if not isinstance(snapshot, Mapping):
        raise AssertionError("validated route manifest did not freeze to a mapping")
    _validate_route_manifest_shape(snapshot, expected_revision=expected_revision)
    return snapshot


def load_route_manifest(
    *,
    release_root: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> LoadedRouteManifest:
    artifact = load_artifact(
        ARTIFACT_NAME,
        release_root=release_root,
        fixture_path=fixture_path,
    )
    data = validate_route_manifest_data(artifact.data)
    return LoadedRouteManifest(artifact=artifact, revision=data["revision"], data=data)


def classify_request_target(
    target: str,
    manifest: LoadedRouteManifest,
    *,
    method: str = "GET",
) -> RouteDecision:
    if not target.startswith("/") or "#" in target:
        return RouteDecision("reject", None)

    raw_path, separator, query = target.partition("?")
    decoded = _decode_once(raw_path)
    if decoded is None:
        return RouteDecision("reject", None)

    raw_without_empty = _collapse_slashes(raw_path)
    normalized = _collapse_slashes(decoded)
    sensitive = _sensitive_classification(raw_without_empty, normalized, manifest)
    if sensitive is not None:
        return RouteDecision(sensitive, normalized)

    if raw_path != normalized:
        classification = (
            "redirect-canonical"
            if method in {"GET", "HEAD"}
            else "noindex-follow-public"
        )
        return RouteDecision(classification, normalized)

    if separator and query:
        return RouteDecision("noindex-follow-public", normalized)

    return RouteDecision(_canonical_classification(normalized, manifest), normalized)


def extract_static_sitemap_paths(manifest: LoadedRouteManifest) -> tuple[str, ...]:
    return tuple(
        sorted(
            item["path"]
            for item in manifest.data["exact_routes"]
            if item["classification"] == "indexable-public" and item["sitemap"] is True
        )
    )
