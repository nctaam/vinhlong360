from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Mapping

import pytest


ROOT = Path(__file__).resolve().parents[3]
PROBE = ROOT / "scripts" / "ops" / "probe_launch_boundary.py"
HARNESS = ROOT / "tests" / "launch_safety" / "integration" / "conftest.py"
pytestmark = [pytest.mark.integration, pytest.mark.slow]

EVIDENCE_HEADERS = {
    "x-launch-policy-fingerprint",
    "x-launch-route-manifest-revision",
    "x-launch-backend-policy-revision",
    "x-launch-sitemap-batch-revision",
    "x-launch-sitemap-requested-batch",
}
SITEMAP_BATCH_REVISION = "b" * 64
EMPTY_SITEMAP_INDEX = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>'
)
ACTIVE_SITEMAP_INDEX = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    '<sitemap><loc>https://vinhlong360.vn/sitemap.xml?batch='
    f"{SITEMAP_BATCH_REVISION}"
    '</loc></sitemap></sitemapindex>'
)
PINNED_SITEMAP = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    '<url><loc>https://vinhlong360.vn/du-lich</loc></url></urlset>'
)

MATRIX_BACKEND = r"""
const fs = require('node:fs')
const http = require('node:http')
const fixture = process.env.MATRIX_FIXTURE
const fingerprint = process.env.MATRIX_POLICY_FINGERPRINT
const routeRevision = process.env.MATRIX_ROUTE_REVISION
const backendRevision = process.env.MATRIX_BACKEND_REVISION
const batch = process.env.MATRIX_SITEMAP_BATCH
const countPath = '/tmp/vl360-matrix-counts.json'
const counts = { launch: 0, entity: 0 }
const persist = () => fs.writeFileSync(countPath, JSON.stringify(counts))
persist()

const send = (response, status, headers, body) => {
  response.writeHead(status, { 'cache-control': 'no-store', ...headers })
  response.end(body)
}
const json = (response, status, body) => send(
  response,
  status,
  { 'content-type': 'application/json; charset=utf-8' },
  JSON.stringify(body),
)
const evidence = {
  'x-launch-policy-fingerprint': fingerprint,
  'x-launch-route-manifest-revision': routeRevision,
  'x-launch-backend-policy-revision': backendRevision,
  'x-launch-sitemap-batch-revision': batch,
}
const indexPolicy = (indexable, mismatch = false) => ({
  indexable,
  kind: 'entity',
  policy_fingerprint: mismatch ? 'c'.repeat(64) : fingerprint,
  policy_revision: backendRevision,
  reasons: indexable ? [] : ['description-below-130-words'],
})
const entity = (id, indexable, mismatch = false) => ({
  id,
  type: 'attraction',
  name: `Launch matrix ${id}`,
  summary: 'Deterministic integration fixture.',
  description: 'Deterministic integration fixture.',
  attributes: {},
  images: [],
  coordinates: null,
  index_policy: indexPolicy(indexable, mismatch),
})

http.createServer((request, response) => {
  const url = new URL(request.url, 'http://agent')
  const path = url.pathname
  if (path === '/_matrix/counts') return json(response, 200, counts)

  if (path === '/_internal/launch-policy-attestation') {
    counts.launch += 1
    persist()
    return json(response, 200, {
      policy_fingerprint: fingerprint,
      route_manifest_revision: routeRevision,
      backend_policy_revision: backendRevision,
    })
  }

  if (path.startsWith('/_internal/launch-sitemaps/')) {
    counts.launch += 1
    persist()
    const document = path.split('/').pop()
    const requested = url.searchParams.get('batch')
    if (document === 'sitemap-index.xml' && requested === null) {
      return send(
        response,
        200,
        { ...evidence, 'content-type': 'application/xml; charset=utf-8' },
        process.env.MATRIX_ACTIVE_INDEX,
      )
    }
    if (document === 'sitemap.xml' && requested === batch) {
      return send(
        response,
        200,
        {
          ...evidence,
          'x-launch-sitemap-requested-batch': requested,
          'content-type': 'application/xml; charset=utf-8',
        },
        process.env.MATRIX_PINNED_SITEMAP,
      )
    }
    return json(response, 503, { detail: 'fixture sitemap unavailable' })
  }

  const match = /^\/api\/entities\/([^/]+)$/.exec(path)
  if (match) {
    counts.entity += 1
    persist()
    const id = decodeURIComponent(match[1])
    if (fixture === 'failed-entity-request' && id === 'launch-matrix-failed') {
      return json(response, 503, { detail: 'fixture entity unavailable' })
    }
    if (id === 'launch-matrix-positive') return json(response, 200, entity(id, true))
    if (id === 'launch-matrix-negative') return json(response, 200, entity(id, false))
    if (id === 'launch-matrix-mismatch') return json(response, 200, entity(id, true, true))
  }
  if (/^\/api\/entities\/[^/]+\/gallery$/.test(path)) return json(response, 200, { images: [] })
  if (path.startsWith('/seo/jsonld/')) return json(response, 200, {})
  return json(response, 404, { detail: 'fixture route absent' })
}).listen(8360, '0.0.0.0')
""".strip()


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PROBE_MODULE = _load_module("launch_matrix_contract_probe", PROBE)
HARNESS_MODULE = _load_module("launch_matrix_harness", HARNESS)
LAUNCH_MATRIX = PROBE_MODULE.load_launch_matrix_contract()


class LaunchMatrixProject(HARNESS_MODULE.ComposeProject):
    def __init__(self, runtime, case: Mapping[str, object]) -> None:
        selective = case["policy"] != "closed"
        super().__init__(
            runtime,
            nuxt_environment=(
                {
                    "LAUNCH_INDEXING_MODE": "selective-open",
                    "LAUNCH_INDEXING_OWNER_APPROVED": "true",
                }
                if selective
                else None
            ),
        )
        self.case = case

    def _override_source(self) -> str:
        base = super()._override_source()
        evidence = dict(self.case["evidence_headers"])
        fingerprint = evidence.get(
            "x-launch-policy-fingerprint",
            LAUNCH_MATRIX["selective-static"]["evidence_headers"][
                "x-launch-policy-fingerprint"
            ],
        )
        return base + (
            "  matrix-backend:\n"
            "    image: node:22-alpine\n"
            f"    command: [\"node\", \"-e\", {json.dumps(MATRIX_BACKEND)}]\n"
            "    environment:\n"
            f"      MATRIX_FIXTURE: {json.dumps(str(self.case['fixture']))}\n"
            f"      MATRIX_POLICY_FINGERPRINT: {json.dumps(str(fingerprint))}\n"
            "      MATRIX_ROUTE_REVISION: launch-indexing-policy-v1\n"
            "      MATRIX_BACKEND_REVISION: index-policy-v1\n"
            f"      MATRIX_SITEMAP_BATCH: {json.dumps(SITEMAP_BATCH_REVISION)}\n"
            f"      MATRIX_ACTIVE_INDEX: {json.dumps(ACTIVE_SITEMAP_INDEX)}\n"
            f"      MATRIX_PINNED_SITEMAP: {json.dumps(PINNED_SITEMAP)}\n"
            "    expose:\n"
            "      - '8360'\n"
            "    networks:\n"
            "      default:\n"
            "        aliases:\n"
            "          - agent\n"
        )

    def backend_counts(self) -> dict[str, int]:
        response = self.fetch("nuxt", "http://matrix-backend:8360/_matrix/counts")
        assert response.status == 200
        payload = json.loads(response.body)
        assert set(payload) == {"launch", "entity"}
        return {key: int(value) for key, value in payload.items()}


def _has_sitemap_discovery(body: str) -> bool:
    return bool(
        re.search(
            r'<link\b[^>]*\brel=["\'][^"\']*\bsitemap\b[^"\']*["\'][^>]*>',
            body,
            flags=re.IGNORECASE,
        )
    )


def _assert_html_contract(response, case: Mapping[str, object]) -> None:
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-launch-indexing-policy"] == case["policy"]
    assert response.headers["x-robots-tag"] == case["robots"]
    expected_evidence = dict(case["evidence_headers"])
    actual_evidence = {
        name: response.headers[name]
        for name in EVIDENCE_HEADERS
        if name in response.headers
    }
    assert actual_evidence == expected_evidence
    assert _has_sitemap_discovery(response.body) is case["sitemap_discovery"]
    meta = re.findall(
        r'<meta\b[^>]*\bname=["\']robots["\'][^>]*>',
        response.body,
        flags=re.IGNORECASE,
    )
    assert len(meta) == 1
    assert re.search(
        rf'\bcontent=["\']{re.escape(str(case["robots"]))}["\']',
        meta[0],
        flags=re.IGNORECASE,
    )


def _assert_project_boundary(project) -> None:
    published = project.all_published_endpoints()
    assert len(published) == 2
    assert {endpoint["service"] for endpoint in published} == {"nginx"}
    assert {endpoint["target"] for endpoint in published} == {80, 443}
    assert {endpoint["host_ip"] for endpoint in published} == {"127.0.0.1"}
    assert project.compose_port_is_empty("nuxt", 3000)
    assert project.compose_port_is_empty("agent", 8360)
    assert project.compose_port_is_empty("matrix-backend", 8360)

    for path in (
        "/_internal/launch-readiness",
        "/_internal/launch-policy-attestation",
        f"/_internal/launch-sitemaps/sitemap.xml?batch={SITEMAP_BATCH_REVISION}",
    ):
        response = project.wait_for_host_http(80, path, status=404)
        assert response.headers.get("x-vl360-upstream-internal") is None
        assert "stub-internal-upstream" not in response.body


@pytest.mark.parametrize(
    ("case_name", "case"),
    tuple(LAUNCH_MATRIX.items()),
    ids=tuple(LAUNCH_MATRIX),
)
def test_launch_matrix_contract_over_public_boundary(
    docker_runtime,
    case_name: str,
    case: Mapping[str, object],
):
    project = LaunchMatrixProject(docker_runtime, case)
    with project:
        backend_present = case["fixture"] != "agent-absent"
        if backend_present:
            project.up("matrix-backend", no_deps=True)
            project.wait_for_container("matrix-backend", state="running")

        project.up("nuxt", build=True, no_deps=True)
        project.wait_for_container("nuxt", state="running", health="healthy")
        project.up("nginx", no_deps=True)
        project.wait_for_container("nginx", state="running")
        _assert_project_boundary(project)

        if case_name == "sitemap-pinned":
            surface = f"{case['surface']}?batch={SITEMAP_BATCH_REVISION}"
            response = project.wait_for_host_http(80, surface, status=case["sitemap_status"])
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-launch-indexing-policy"] == case["policy"]
            assert response.body == PINNED_SITEMAP
            expected = dict(case["evidence_headers"])
            for name, value in expected.items():
                assert response.headers[name] == value
            assert set(response.headers).intersection(EVIDENCE_HEADERS) == {
                *expected,
                "x-launch-sitemap-requested-batch",
            }
            assert response.headers["x-launch-sitemap-requested-batch"] == response.headers[
                "x-launch-sitemap-batch-revision"
            ]
            html = project.wait_for_host_http(80, "/du-lich", status=case["html_status"])
            assert _has_sitemap_discovery(html.body) is case["sitemap_discovery"]
        else:
            response = project.wait_for_host_http(
                80,
                str(case["surface"]),
                status=case["html_status"],
            )
            _assert_html_contract(response, case)

            sitemap = project.wait_for_host_http(
                80,
                "/sitemap-index.xml",
                status=case["sitemap_status"],
            )
            assert sitemap.headers["cache-control"] == "no-store"
            if case["policy"] == "closed":
                assert sitemap.body == EMPTY_SITEMAP_INDEX
                assert EVIDENCE_HEADERS.isdisjoint(sitemap.headers)
            elif case["sitemap_status"] == 503:
                assert sitemap.headers["x-launch-indexing-policy"] == "failed-open"
                assert sitemap.body == ""
                assert EVIDENCE_HEADERS.isdisjoint(sitemap.headers)
            else:
                assert sitemap.body == ACTIVE_SITEMAP_INDEX
                assert sitemap.headers["x-launch-sitemap-batch-revision"] == SITEMAP_BATCH_REVISION

        if case_name == "closed":
            assert project.backend_counts() == {"launch": 0, "entity": 0}
        if case_name == "agent-absent-closed":
            assert project.container_state("agent") is None
            assert project.container_state("matrix-backend") is None
        if case_name == "entity-request-failed-open":
            assert sitemap.headers["x-launch-indexing-policy"] == "selective-open"
            assert sitemap.headers["x-launch-sitemap-batch-revision"] == SITEMAP_BATCH_REVISION
            assert sitemap.body == ACTIVE_SITEMAP_INDEX

            valid = project.wait_for_host_http(
                80,
                "/dia-diem/launch-matrix-positive",
                status=200,
            )
            _assert_html_contract(valid, LAUNCH_MATRIX["selective-entity-positive"])

            mismatch = project.wait_for_host_http(
                80,
                "/dia-diem/launch-matrix-mismatch",
                status=200,
            )
            assert mismatch.headers["cache-control"] == "no-store"
            assert mismatch.headers["x-launch-indexing-policy"] == "failed-open"
            assert mismatch.headers["x-robots-tag"] == "noindex, follow"
            assert EVIDENCE_HEADERS.isdisjoint(mismatch.headers)
            assert not _has_sitemap_discovery(mismatch.body)
