from __future__ import annotations

import json
import re

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.slow]

EMPTY_SITEMAPS = {
    "/sitemap.xml": '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
    "/sitemap-media.xml": '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"></urlset>',
    "/sitemap-index.xml": '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
}
EVIDENCE_HEADERS = {
    "x-launch-policy-fingerprint",
    "x-launch-route-manifest-revision",
    "x-launch-backend-policy-revision",
    "x-launch-sitemap-batch-revision",
    "x-launch-sitemap-requested-batch",
}
VALIDATOR_HEADERS = {"etag", "last-modified"}


def _assert_closed_headers(response, *, html: bool = False) -> None:
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-launch-indexing-policy"] == "closed"
    if html:
        assert response.headers["x-robots-tag"] == "noindex, follow"
    assert EVIDENCE_HEADERS.isdisjoint(response.headers)


def test_agent_absent_closed_cold_start_serves_only_closed_policy(
    compose_project_factory,
):
    with compose_project_factory(poison_backend=True) as project:
        project.up("nuxt", build=True, no_deps=True)
        project.wait_for_container("nuxt", state="running", health="healthy")

        assert project.container_state("agent") is None

        readiness = project.fetch(
            "nuxt",
            "http://127.0.0.1:3000/_internal/launch-readiness",
        )
        readiness_body = json.loads(readiness.body)
        assert readiness.status == 200
        assert readiness.headers["cache-control"] == "no-store"
        assert readiness_body["ok"] is True
        assert readiness_body["state"] == "closed"
        assert readiness_body["checks"]
        assert all(check["ok"] is True for check in readiness_body["checks"])

        robots = project.fetch("nuxt", "http://127.0.0.1:3000/robots.txt")
        assert robots.status == 200
        _assert_closed_headers(robots)
        assert robots.headers["content-type"] == "text/plain; charset=utf-8"
        assert VALIDATOR_HEADERS.isdisjoint(robots.headers)
        assert "User-agent: *" in robots.body
        assert "Sitemap:" not in robots.body

        for path, expected_body in EMPTY_SITEMAPS.items():
            sitemap = project.fetch("nuxt", f"http://127.0.0.1:3000{path}")
            assert sitemap.status == 200
            _assert_closed_headers(sitemap)
            assert sitemap.headers["content-type"] == "application/xml; charset=utf-8"
            assert VALIDATOR_HEADERS.isdisjoint(sitemap.headers)
            assert sitemap.body == expected_body

        assert project.launch_backend_request_count() == 0

        html = project.fetch("nuxt", "http://127.0.0.1:3000/")
        assert html.status == 200
        _assert_closed_headers(html, html=True)
        robots_meta = re.findall(
            r'<meta\b[^>]*\bname=["\']robots["\'][^>]*>',
            html.body,
            flags=re.IGNORECASE,
        )
        assert len(robots_meta) == 1
        assert re.search(
            r'\bcontent=["\']noindex,\s*follow["\']',
            robots_meta[0],
            flags=re.IGNORECASE,
        )
        assert not re.search(
            r'<link\b[^>]*\brel=["\'][^"\']*\bsitemap\b[^"\']*["\']',
            html.body,
            flags=re.IGNORECASE,
        )
        assert project.launch_backend_request_count() == 0


def test_agent_absent_exact_open_intent_is_unhealthy_and_blocks_nginx(
    compose_project_factory,
):
    with compose_project_factory(
        nuxt_environment={
            "LAUNCH_INDEXING_MODE": "selective-open",
            "LAUNCH_INDEXING_OWNER_APPROVED": "true",
        },
        poison_backend=True,
    ) as project:
        project.up("nuxt", build=True, no_deps=True)
        project.wait_for_container("nuxt", state="running")
        assert project.container_state("agent") is None

        readiness = project.wait_for_http(
            "nuxt",
            "http://127.0.0.1:3000/_internal/launch-readiness",
            status=503,
        )
        assert json.loads(readiness.body) == {
            "ok": False,
            "reason": "policy-attestation-unavailable",
        }
        assert readiness.headers["cache-control"] == "no-store"

        project.wait_for_container("nuxt", state="running", health="unhealthy")
        admission = project.compose("up", "-d", "--no-build", "nginx", check=False)

        assert admission.returncode != 0
        assert project.container_state("nuxt") == {
            "state": "running",
            "health": "unhealthy",
        }
        assert project.container_never_started("nginx")
        assert project.published_endpoints("nginx") == []


def test_head_snapshot_allows_only_integration_and_excluded_dirty_paths(
    head_snapshot_validator,
):
    head_snapshot_validator(
        " M tests/launch_safety/integration/conftest.py\0"
        "?? web/data.js\0"
        "?? web-nuxt/pnpm-lock.yaml\0"
    )


def test_head_snapshot_rejects_dirty_runtime_input(head_snapshot_validator):
    with pytest.raises(
        AssertionError,
        match="runtime snapshot differs from HEAD",
    ):
        head_snapshot_validator(" M docker-compose.yml\0")
