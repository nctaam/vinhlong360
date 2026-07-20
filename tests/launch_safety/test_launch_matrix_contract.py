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


def test_probe_executes_exact_task44_closed_operator_invocation():
    probe = _load_probe()
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
        requester=lambda path, _timeout: responses[path],
    )

    assert result == 0
