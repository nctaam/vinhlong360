from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from route_manifest import (
    classify_request_target,
    extract_static_sitemap_paths,
    load_route_manifest,
    validate_route_manifest_data,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = REPO_ROOT / "web-nuxt"
MANIFEST_PATH = REPO_ROOT / "config" / "launch-indexing-policy.json"
ROUTE_CORPUS_PATH = REPO_ROOT / "tests" / "fixtures" / "launch-route-parity-corpus.json"
VALIDATOR_CORPUS_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "launch-route-validator-corpus.json"
)
NGINX_PATHS = (REPO_ROOT / "nginx.conf", REPO_ROOT / "nginx-ssl.conf")

ROUTE_CORPUS = json.loads(ROUTE_CORPUS_PATH.read_text(encoding="utf-8"))
VALIDATOR_CORPUS = json.loads(VALIDATOR_CORPUS_PATH.read_text(encoding="utf-8"))
STATIC_SITEMAP_PATHS = (
    "/",
    "/ban-do",
    "/chinh-sach-bao-mat",
    "/danh-ba",
    "/dia-diem",
    "/dieu-khoan-su-dung",
    "/du-lich",
    "/gioi-thieu",
    "/huong-dan",
    "/huong-dan-thanh-vien",
    "/kham-pha/am-thuc",
    "/kham-pha/lang-nghe",
    "/kham-pha/mua-sam",
    "/kham-pha/thien-nhien",
    "/kham-pha/van-hoa",
    "/khu-vuc/ben-tre",
    "/khu-vuc/tra-vinh",
    "/khu-vuc/vinh-long",
    "/le-hoi",
    "/lien-he",
    "/luu-tru",
    "/ocop",
    "/san-pham",
    "/su-kien",
    "/theo-mua",
    "/tuyen-duong",
)
LOCATION = re.compile(
    r"location\s+(?P<selector>[^{}]+?)\s*\{(?P<body>[^{}]*)\}", re.DOTALL
)
PROXY = re.compile(
    r"proxy_pass\s+http://(?P<upstream>vl360_agent|vl360_bots)(?:/[^;]*)?;"
)


def _manifest_source() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(child) for child in value]
    return value


def _pointer_parts(pointer: str) -> list[str]:
    assert pointer.startswith("/")
    return [
        part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")
    ]


def _pointer_parent(document: object, pointer: str) -> tuple[object, str]:
    parts = _pointer_parts(pointer)
    current = document
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def _apply_mutation(document: dict[str, object], mutation: dict[str, object]) -> None:
    parent, key = _pointer_parent(document, str(mutation["pointer"]))
    operation = mutation["operation"]
    if operation == "delete":
        if isinstance(parent, list):
            del parent[int(key)]
        else:
            del parent[key]
    elif operation == "set":
        if isinstance(parent, list):
            parent[int(key)] = copy.deepcopy(mutation["value"])
        else:
            parent[key] = copy.deepcopy(mutation["value"])
    elif operation == "append-copy":
        assert isinstance(parent, list)
        parent.append(copy.deepcopy(parent[int(key)]))
    elif operation == "append":
        target = parent[int(key)] if isinstance(parent, list) else parent[key]
        assert isinstance(target, list)
        target.append(copy.deepcopy(mutation["value"]))
    else:
        raise AssertionError(f"unsupported mutation operation: {operation}")


def _accepted_ingress_manifest() -> dict[str, object]:
    candidate = _manifest_source()
    for mutation in VALIDATOR_CORPUS:
        if (
            str(mutation["name"]).startswith("accepted-ingress-")
            or mutation["name"] == "accepted-nel-ingress-review"
        ):
            _apply_mutation(candidate, mutation)
    return candidate


def _backend_locations(source: str) -> list[tuple[str, str]]:
    locations: list[tuple[str, str]] = []
    for match in LOCATION.finditer(source):
        proxy = PROXY.search(match.group("body"))
        if proxy:
            selector = " ".join(match.group("selector").split())
            locations.append((selector, proxy.group("upstream")))
    return locations


def _selector_matches(selector: str, path: str) -> bool:
    if selector.startswith("~ "):
        return re.search(selector[2:], path) is not None
    if selector.startswith("= "):
        return path == selector[2:]
    if selector.startswith("^~ "):
        return path.startswith(selector[3:])
    raise AssertionError(
        f"backend selector lacks explicit boundary semantics: {selector}"
    )


def _selector_prefixes(selector: str) -> tuple[str, ...]:
    if selector.startswith("= "):
        return (selector[2:],)
    if selector.startswith("^~ "):
        return (selector[3:].rstrip("/"),)

    single = re.fullmatch(r"~ \^/([a-z0-9-]+)\(\?:/\|\$\)", selector)
    if single:
        return (f"/{single.group(1)}",)
    grouped = re.fullmatch(r"~ \^/\(([-a-z0-9|]+)\)\(\?:/\|\$\)", selector)
    if grouped:
        return tuple(f"/{part}" for part in grouped.group(1).split("|"))
    raise AssertionError(f"unsupported backend ingress selector: {selector}")


def _matches_any_selector(selectors: list[str], path: str) -> bool:
    return any(_selector_matches(selector, path) for selector in selectors)


def test_shared_validator_corpus_accepts_canonical_templates_and_matches_errors():
    parsed = validate_route_manifest_data(_manifest_source())
    assert [item["template"] for item in parsed["dynamic_templates"]] == [
        "/dia-diem/{entity_id}",
        "/xa-phuong/{ward_id}",
        "/bai-viet/{id}",
        "/nguoi-dung/{id}",
        "/lich-trinh/{id}",
        "/lich-trinh-chia-se/{id}",
    ]

    for mutation in VALIDATOR_CORPUS:
        candidate = _manifest_source()
        _apply_mutation(candidate, mutation)
        expected_error = mutation["error"]
        if expected_error is None:
            validate_route_manifest_data(candidate)
        else:
            with pytest.raises(ValueError, match=re.escape(str(expected_error))):
                validate_route_manifest_data(candidate)


def test_shared_route_corpus_matches_python_classifier():
    manifest = load_route_manifest()

    for row in ROUTE_CORPUS:
        decision = classify_request_target(
            row["target"], manifest, method=row["method"]
        )
        assert decision.classification == row["classification"], row
        assert decision.canonical_path == row["canonical"], row


def test_static_sitemap_paths_are_exact_manifest_inventory():
    assert extract_static_sitemap_paths(load_route_manifest()) == STATIC_SITEMAP_PATHS


def test_typescript_serialization_matches_python_byte_for_byte(tmp_path):
    module_url = (
        WEB_ROOT / "server" / "utils" / "launch" / "launchRouteManifest.ts"
    ).as_uri()
    runner = tmp_path / "route-parity-runner.ts"
    runner.write_text(
        f"""
import {{ readFileSync }} from 'node:fs'
import {{
  classifyRequestTarget,
  extractStaticSitemapPaths,
  parseLaunchRouteManifest,
}} from {json.dumps(module_url)}

const manifestSource = JSON.parse(readFileSync({json.dumps(str(MANIFEST_PATH))}, 'utf8'))
const routeCorpus = JSON.parse(readFileSync({json.dumps(str(ROUTE_CORPUS_PATH))}, 'utf8'))
const validatorCorpus = JSON.parse(readFileSync({json.dumps(str(VALIDATOR_CORPUS_PATH))}, 'utf8'))

function pointerParent(document, pointer) {{
  const parts = pointer.slice(1).split('/').map(part => part.replaceAll('~1', '/').replaceAll('~0', '~'))
  let current = document
  for (const part of parts.slice(0, -1)) current = Array.isArray(current) ? current[Number(part)] : current[part]
  return [current, parts.at(-1)]
}}

function applyMutation(document, mutation) {{
  const [parent, key] = pointerParent(document, mutation.pointer)
  if (mutation.operation === 'append') parent[key].push(structuredClone(mutation.value))
  else throw new Error(`unsupported runner mutation: ${{mutation.operation}}`)
}}

const manifest = parseLaunchRouteManifest(manifestSource)
const ingressCandidate = structuredClone(manifestSource)
for (const mutation of validatorCorpus) {{
  if (mutation.name.startsWith('accepted-ingress-') || mutation.name === 'accepted-nel-ingress-review') {{
    applyMutation(ingressCandidate, mutation)
  }}
}}
const ingressManifest = parseLaunchRouteManifest(ingressCandidate)
const output = {{
  decisions: routeCorpus.map(row => classifyRequestTarget(row.target, manifest, row.method)),
  static_sitemap_paths: extractStaticSitemapPaths(manifest),
  ingress_exceptions: ingressManifest.backend_ingress_exceptions,
}}
process.stdout.write(JSON.stringify(output))
""".strip(),
        encoding="utf-8",
    )

    node = shutil.which("node")
    assert node is not None, "Node.js is required for cross-runtime route parity"
    result = subprocess.run(
        [
            node,
            str(WEB_ROOT / "node_modules" / "vite-node" / "dist" / "cli.mjs"),
            "--config",
            "vitest.config.ts",
            str(runner),
        ],
        cwd=WEB_ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")

    manifest = load_route_manifest()
    ingress = validate_route_manifest_data(_accepted_ingress_manifest())
    python_output = {
        "decisions": [
            {
                "classification": decision.classification,
                "canonical_path": decision.canonical_path,
            }
            for row in ROUTE_CORPUS
            for decision in [
                classify_request_target(row["target"], manifest, method=row["method"])
            ]
        ],
        "static_sitemap_paths": list(extract_static_sitemap_paths(manifest)),
        "ingress_exceptions": _plain_json(ingress["backend_ingress_exceptions"]),
    }
    expected = json.dumps(
        python_output,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    assert result.stdout == expected
    assert python_output["ingress_exceptions"] == [
        {"prefix": "/hook", "upstream": "agent", "review_reason": "reviewed callback"},
        {"prefix": "/nel-hook", "upstream": "bot-gateway", "review_reason": "\u0085"},
    ]


def _nginx_location_pair() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    http_locations = _backend_locations(NGINX_PATHS[0].read_text(encoding="utf-8"))
    https_locations = _backend_locations(NGINX_PATHS[1].read_text(encoding="utf-8"))
    return http_locations, https_locations


def test_nginx_backend_locations_have_http_https_parity():
    http_locations, https_locations = _nginx_location_pair()

    assert http_locations == https_locations
    assert http_locations


def test_nginx_backend_locations_have_explicit_boundaries():
    http_locations, _https_locations = _nginx_location_pair()

    for selector, _upstream in http_locations:
        if selector.startswith("~ "):
            assert selector.endswith("(?:/|$)") or selector.endswith("$")
        else:
            assert selector.startswith("= ") or (
                selector.startswith("^~ ") and selector.endswith("/")
            )


def test_nginx_backend_ingress_is_reviewed_by_segment_prefix():
    http_locations, _https_locations = _nginx_location_pair()
    ingress_locations = [
        location for location in http_locations if "sitemap" not in location[0]
    ]
    manifest = load_route_manifest()
    prefixes = [item["prefix"] for item in manifest.data["sensitive_prefixes"]]
    exceptions = [
        item["prefix"] for item in manifest.data["backend_ingress_exceptions"]
    ]
    for selector, _upstream in ingress_locations:
        reviewed_prefixes = (*prefixes, *exceptions)
        for prefix in _selector_prefixes(selector):
            assert prefix in reviewed_prefixes, (selector, prefix)


def test_nginx_backend_boundaries_exclude_lookalike_public_paths():
    http_locations, _https_locations = _nginx_location_pair()
    ingress_locations = [
        location for location in http_locations if "sitemap" not in location[0]
    ]
    selectors = [selector for selector, _upstream in ingress_locations]
    assert _matches_any_selector(selectors, "/api")
    assert _matches_any_selector(selectors, "/api/entities")
    assert not _matches_any_selector(selectors, "/apiary")
    assert _matches_any_selector(selectors, "/webhook")
    assert not _matches_any_selector(selectors, "/webhooks")
