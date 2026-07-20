from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "ops" / "probe_launch_boundary.py"
BROWSER_SMOKE = ROOT / "scripts" / "launch_safety_browser_e2e.mjs"
NUXT_PACKAGE = ROOT / "web-nuxt" / "package.json"

POLICY_FINGERPRINT = "ef12661b898905bd8b31804475aca64accd4c8b2df32b5252c3b2f61eeeca44c"
ROUTE_MANIFEST_REVISION = "launch-indexing-policy-v1"
BACKEND_POLICY_REVISION = "index-policy-v1"
SITEMAP_BATCH_REVISION = "b" * 64
PROCESS_LOCAL_READINESS_URL = "http://127.0.0.1:3000/_internal/launch-readiness"
PUBLIC_INTERNAL_PATHS = (
    "/_internal/launch-readiness",
    "/_internal/launch-policy-attestation",
    f"/_internal/launch-sitemaps/sitemap.xml?batch={SITEMAP_BATCH_REVISION}",
)
DIRECT_BYPASS_URLS = (
    "http://vinhlong360.vn:3000/",
    "http://vinhlong360.vn:3000/_internal/launch-readiness",
    "http://vinhlong360.vn:8360/",
    "http://vinhlong360.vn:8360/sitemap.xml",
    "http://vinhlong360.vn:8360/sitemap-media.xml",
    "http://vinhlong360.vn:8360/sitemap-index.xml",
    "http://vinhlong360.vn:8360/_internal/launch-policy-attestation",
    "http://vinhlong360.vn:8360/_internal/launch-sitemaps/sitemap.xml",
)
READINESS_CHECKS = [
    {"name": "manifest-schema", "ok": True, "reason": "manifest-valid"},
    {"name": "artifact-evidence", "ok": True, "reason": "artifact-evidence-valid"},
    {"name": "compiled-cache-rules", "ok": True, "reason": "compiled-cache-rules-safe"},
    {"name": "public-prerender", "ok": True, "reason": "public-prerender-safe"},
    {"name": "service-worker-cache-purge", "ok": True, "reason": "cache-purge-verified"},
]
PAGE_EVIDENCE = {
    "x-launch-policy-fingerprint": POLICY_FINGERPRINT,
    "x-launch-route-manifest-revision": ROUTE_MANIFEST_REVISION,
    "x-launch-backend-policy-revision": BACKEND_POLICY_REVISION,
}
PINNED_EVIDENCE = {
    **PAGE_EVIDENCE,
    "x-launch-sitemap-batch-revision": SITEMAP_BATCH_REVISION,
}
CASE_KEYS = {
    "policy",
    "robots",
    "evidence_headers",
    "html_status",
    "sitemap_discovery",
    "sitemap_status",
    "requires_matching_batch_revision",
    "fixture",
    "surface",
}


def _load_probe() -> ModuleType:
    spec = importlib.util.spec_from_file_location("launch_matrix_probe", PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _closed_boundary_responses(probe: ModuleType) -> dict[str, object]:
    responses = {
        "/": probe.HttpResponse(
            path="/",
            status=200,
            headers={
                "cache-control": ("no-store",),
                "content-type": ("text/html; charset=utf-8",),
                "x-launch-indexing-policy": ("closed",),
                "x-robots-tag": ("noindex, follow",),
            },
            body=b'<meta name="robots" content="noindex, follow">',
        ),
        "/robots.txt": probe.HttpResponse(
            path="/robots.txt",
            status=200,
            headers={
                "cache-control": ("no-store",),
                "content-type": ("text/plain; charset=utf-8",),
                "x-launch-indexing-policy": ("closed",),
            },
            body=b"User-agent: *\nAllow: /\n",
        ),
        "/sitemap.xml": probe.HttpResponse(
            path="/sitemap.xml",
            status=200,
            headers={
                "cache-control": ("no-store",),
                "content-type": ("application/xml; charset=utf-8",),
                "x-launch-indexing-policy": ("closed",),
            },
            body=probe.EMPTY_URLSET.encode(),
        ),
        "/sitemap-media.xml": probe.HttpResponse(
            path="/sitemap-media.xml",
            status=200,
            headers={
                "cache-control": ("no-store",),
                "content-type": ("application/xml; charset=utf-8",),
                "x-launch-indexing-policy": ("closed",),
            },
            body=probe.EMPTY_MEDIA_URLSET.encode(),
        ),
        "/sitemap-index.xml": probe.HttpResponse(
            path="/sitemap-index.xml",
            status=200,
            headers={
                "cache-control": ("no-store",),
                "content-type": ("application/xml; charset=utf-8",),
                "x-launch-indexing-policy": ("closed",),
            },
            body=probe.EMPTY_SITEMAP_INDEX.encode(),
        ),
    }
    for path in PUBLIC_INTERNAL_PATHS:
        responses[path] = probe.HttpResponse(
            path=path,
            status=404,
            headers={"content-type": ("text/plain; charset=utf-8",)},
            body=b"not found",
        )
    return responses


def test_launch_matrix_contract_is_exact_and_deeply_immutable():
    contract = _load_probe().load_launch_matrix_contract()

    assert tuple(contract) == (
        "closed",
        "selective-static",
        "selective-entity-positive",
        "selective-entity-negative",
        "entity-request-failed-open",
        "sitemap-pinned",
        "agent-absent-closed",
    )
    assert all(set(case) == CASE_KEYS for case in contract.values())

    with pytest.raises(TypeError):
        contract["unexpected"] = contract["closed"]
    with pytest.raises(TypeError):
        contract["closed"]["policy"] = "selective-open"
    with pytest.raises(TypeError):
        contract["sitemap-pinned"]["evidence_headers"]["unexpected"] = "value"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (
            "closed",
            {
                "policy": "closed",
                "robots": "noindex, follow",
                "evidence_headers": {},
                "html_status": 200,
                "sitemap_discovery": False,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "closed-with-backend-sentinel",
                "surface": "/",
            },
        ),
        (
            "selective-static",
            {
                "policy": "selective-open",
                "robots": "index, follow",
                "evidence_headers": PAGE_EVIDENCE,
                "html_status": 200,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "matching-backend",
                "surface": "/du-lich",
            },
        ),
        (
            "selective-entity-positive",
            {
                "policy": "selective-open",
                "robots": "index, follow",
                "evidence_headers": PAGE_EVIDENCE,
                "html_status": 200,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "matching-indexable-entity",
                "surface": "/dia-diem/launch-matrix-positive",
            },
        ),
        (
            "selective-entity-negative",
            {
                "policy": "selective-open",
                "robots": "noindex, follow",
                "evidence_headers": PAGE_EVIDENCE,
                "html_status": 200,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "matching-noindex-entity",
                "surface": "/dia-diem/launch-matrix-negative",
            },
        ),
        (
            "entity-request-failed-open",
            {
                "policy": "failed-open",
                "robots": "noindex, follow",
                "evidence_headers": {},
                "html_status": 503,
                "sitemap_discovery": False,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "failed-entity-request",
                "surface": "/dia-diem/launch-matrix-failed",
            },
        ),
        (
            "sitemap-pinned",
            {
                "policy": "selective-open",
                "robots": None,
                "evidence_headers": PINNED_EVIDENCE,
                "html_status": 200,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": True,
                "fixture": "matching-pinned-sitemap",
                "surface": "/sitemap.xml",
            },
        ),
        (
            "agent-absent-closed",
            {
                "policy": "closed",
                "robots": "noindex, follow",
                "evidence_headers": {},
                "html_status": 200,
                "sitemap_discovery": False,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "agent-absent",
                "surface": "/",
            },
        ),
    ],
)
def test_launch_matrix_case_contract(name: str, expected: dict[str, object]):
    case = _load_probe().load_launch_matrix_contract()[name]

    assert dict(case) == expected
    assert dict(case["evidence_headers"]) == expected["evidence_headers"]


def test_launch_matrix_contract_captures_fail_safe_invariants():
    contract = _load_probe().load_launch_matrix_contract()

    assert contract["closed"]["evidence_headers"] == {}
    assert contract["closed"]["sitemap_status"] == 200
    assert contract["selective-entity-negative"]["policy"] == "selective-open"
    assert contract["selective-entity-negative"]["robots"] == "noindex, follow"
    assert contract["selective-entity-negative"]["evidence_headers"]
    assert contract["selective-entity-negative"]["sitemap_discovery"] is True
    assert contract["entity-request-failed-open"]["robots"] == "noindex, follow"
    assert contract["entity-request-failed-open"]["evidence_headers"] == {}
    assert contract["entity-request-failed-open"]["html_status"] == 503
    assert contract["entity-request-failed-open"]["sitemap_discovery"] is False
    assert contract["entity-request-failed-open"]["sitemap_status"] == 200

    pinned = contract["sitemap-pinned"]
    assert dict(pinned["evidence_headers"]) == PINNED_EVIDENCE
    assert len(pinned["evidence_headers"]) == 4
    assert pinned["requires_matching_batch_revision"] is True


def test_browser_smoke_exposes_the_task44_compatible_cli_and_npm_entry():
    assert BROWSER_SMOKE.is_file()

    syntax = subprocess.run(
        ["node", "--check", str(BROWSER_SMOKE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert syntax.returncode == 0, syntax.stderr

    help_result = subprocess.run(
        ["node", str(BROWSER_SMOKE), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0, help_result.stderr
    for flag in (
        "--base-url",
        "--profile",
        "--install-legacy-worker-first",
        "--activate-current-worker",
        "--assert-policy-cache-storage-empty",
        "--assert-offline-policy-replay-denied",
        "--evidence",
    ):
        assert flag in help_result.stdout

    package = json.loads(NUXT_PACKAGE.read_text(encoding="utf-8"))
    assert package["scripts"]["smoke:launch-safety"] == (
        "node ../scripts/launch_safety_browser_e2e.mjs "
        "--install-legacy-worker-first --activate-current-worker "
        "--assert-policy-cache-storage-empty --assert-offline-policy-replay-denied"
    )


def test_browser_cdp_endpoint_is_owned_by_the_spawned_chrome_process():
    contract = f"""
import {{ parseSpawnedCdpEndpoint, verifySpawnedCdpEndpoint }} from {json.dumps(BROWSER_SMOKE.as_uri())}

const endpoint = parseSpawnedCdpEndpoint(
  'startup noise\\nDevTools listening on ws://127.0.0.1:43123/devtools/browser/spawn-token\\n',
)
if (endpoint.port !== 43123) throw new Error('ephemeral port was not parsed')
verifySpawnedCdpEndpoint(endpoint, {{ webSocketDebuggerUrl: endpoint.webSocketDebuggerUrl }})

let rejected = false
try {{
  verifySpawnedCdpEndpoint(endpoint, {{
    webSocketDebuggerUrl: 'ws://127.0.0.1:43123/devtools/browser/pre-existing-token',
  }})
}} catch (error) {{
  rejected = error?.code === 'chrome-cdp-ownership-mismatch'
}}
if (!rejected) throw new Error('pre-existing CDP endpoint was accepted')
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", contract],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    source = BROWSER_SMOKE.read_text(encoding="utf-8")
    assert "--remote-debugging-port=0" in source
    assert "await waitForSpawnedChrome(chrome)" in source
    assert "DEFAULT_CDP_PORT" not in source


def test_probe_executes_exact_task44_process_local_readiness_invocation():
    probe = _load_probe()
    calls: list[str] = []
    readiness = probe.HttpResponse(
        path="/_internal/launch-readiness",
        status=200,
        headers={
            "cache-control": ("no-store",),
            "content-type": ("application/json; charset=utf-8",),
        },
        body=json.dumps(
            {"ok": True, "state": "closed", "checks": READINESS_CHECKS}
        ).encode(),
    )

    def requester(target: str, _timeout: float):
        calls.append(target)
        assert target == PROCESS_LOCAL_READINESS_URL
        return readiness

    result = probe.main(
        [
            "--process-local-readiness",
            PROCESS_LOCAL_READINESS_URL,
            "--expect",
            "closed",
            "--require-complete-check-set",
        ],
        requester=requester,
    )

    assert result == 0
    assert calls == [PROCESS_LOCAL_READINESS_URL]


@pytest.mark.parametrize(
    "checks",
    [
        [*READINESS_CHECKS, dict(READINESS_CHECKS[0])],
        [{**READINESS_CHECKS[0], "name": []}, *READINESS_CHECKS[1:]],
        [{**READINESS_CHECKS[0], "reason": "unexpected-reason"}, *READINESS_CHECKS[1:]],
    ],
    ids=("duplicate", "malformed-name", "wrong-reason"),
)
def test_probe_rejects_non_exact_readiness_check_sets(
    tmp_path: Path,
    checks: list[object],
):
    probe = _load_probe()
    evidence = tmp_path / "readiness.json"
    readiness = probe.HttpResponse(
        path="/_internal/launch-readiness",
        status=200,
        headers={
            "cache-control": ("no-store",),
            "content-type": ("application/json; charset=utf-8",),
        },
        body=json.dumps({"ok": True, "state": "closed", "checks": checks}).encode(),
    )

    result = probe.main(
        [
            "--process-local-readiness",
            PROCESS_LOCAL_READINESS_URL,
            "--expect",
            "closed",
            "--require-complete-check-set",
            "--evidence",
            str(evidence),
        ],
        requester=lambda _target, _timeout: readiness,
    )

    assert result == 1
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["errors"] == ["readiness-check-set-incomplete"]
    assert payload["observations"]["process-local-readiness"] == {
        "contract_passed": False,
        "reasons": ["readiness-check-set-incomplete"],
        "request_completed": True,
    }


def test_probe_executes_exact_task44_closed_operator_invocation():
    probe = _load_probe()
    responses = _closed_boundary_responses(probe)
    calls: list[str] = []

    def requester(target: str, _timeout: float):
        calls.append(target)
        if target in DIRECT_BYPASS_URLS:
            raise probe._ProbeRequestError("direct bypass denied")
        return responses[target]

    result = probe.main(
        [
            "--expect",
            "closed",
            "--maintenance-probe",
            "--operator-source",
            "--require-rich-thin-html",
            "--require-meta-header-noindex",
            "--require-robots-without-sitemap",
            "--require-three-empty-sitemap-shapes",
            "--require-no-store",
            "--require-no-evidence",
            "--require-no-discovery",
            "--require-public-internal-404",
            "--require-direct-bypass-denied",
        ],
        requester=requester,
    )

    assert result == 0
    assert set(calls) == {*responses, *DIRECT_BYPASS_URLS}


def test_probe_rejects_exposed_public_internal_and_direct_bypass_surfaces(tmp_path: Path):
    probe = _load_probe()
    responses = _closed_boundary_responses(probe)
    for path in PUBLIC_INTERNAL_PATHS:
        responses[path] = probe.HttpResponse(
            path=path,
            status=200,
            headers={"x-vl360-upstream-internal": ("true",)},
            body=b"stub-internal-upstream",
        )
    evidence = tmp_path / "exposed-boundary.json"

    def requester(target: str, _timeout: float):
        if target in DIRECT_BYPASS_URLS:
            return probe.HttpResponse(path=target, status=404, headers={}, body=b"")
        return responses[target]

    result = probe.main(
        [
            "--expect",
            "closed",
            "--maintenance-probe",
            "--operator-source",
            "--require-public-internal-404",
            "--require-direct-bypass-denied",
            "--evidence",
            str(evidence),
        ],
        requester=requester,
    )

    assert result == 1
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert "public-internal-route-exposed" in payload["errors"]
    assert "direct-bypass-response-present" in payload["errors"]
