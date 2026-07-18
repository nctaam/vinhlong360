from __future__ import annotations

import re

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.slow]

APP_SERVICES = {
    "postgres",
    "redis",
    "agent",
    "bot-gateway",
    "nuxt",
    "nginx",
}
INTERNAL_HTTP_SERVICES = {
    "agent": (8360, "http://agent:8360/health"),
    "bot-gateway": (8361, "http://bot-gateway:8361/"),
    "nuxt": (3000, "http://nuxt:3000/_internal/launch-readiness"),
}
UNSTARTED_SUPPORT_SERVICES = {"prometheus", "grafana", "loki", "promtail"}


def test_app_stack_keeps_internal_services_private_and_bot_healthy(
    compose_project_factory,
):
    with compose_project_factory() as project:
        project.up(*sorted(APP_SERVICES), build=True)
        for service in APP_SERVICES:
            project.wait_for_container(service, state="running")
        for service in {"postgres", "redis", "agent", "bot-gateway", "nuxt"}:
            project.wait_for_container(service, state="running", health="healthy")

        assert set(project.running_services()) == APP_SERVICES
        assert all(project.container_state(service) is None for service in UNSTARTED_SUPPORT_SERVICES)

        for service, (port, url) in INTERNAL_HTTP_SERVICES.items():
            assert project.published_endpoints(service) == []
            assert project.compose_port_is_empty(service, port)
            response = project.fetch("nuxt", url)
            assert response.status == 200
            assert project.tcp_reachable("nuxt", service, port)

        assert project.published_endpoints("postgres") == []
        assert project.published_endpoints("redis") == []
        assert project.compose_port_is_empty("postgres", 5432)
        assert project.compose_port_is_empty("redis", 6379)
        assert project.tcp_reachable("nuxt", "postgres", 5432)
        assert project.tcp_reachable("nuxt", "redis", 6379)

        bot = project.fetch("nuxt", "http://bot-gateway:8361/")
        assert bot.status == 200


def test_only_nginx_is_published_and_public_html_stays_closed(
    compose_project_factory,
):
    with compose_project_factory() as project:
        project.up(*sorted(APP_SERVICES), build=True)
        project.wait_for_container("nginx", state="running")
        project.wait_for_container("nuxt", state="running", health="healthy")
        assert project.fetch("nuxt", "http://nginx/").status == 200

        published = project.all_published_endpoints()
        assert len(published) == 2
        assert [endpoint["service"] for endpoint in published] == ["nginx", "nginx"]
        assert {endpoint["target"] for endpoint in published} == {80, 443}
        assert {endpoint["host_ip"] for endpoint in published} == {"127.0.0.1"}
        assert {endpoint["protocol"] for endpoint in published} == {"tcp"}
        host_ports = [endpoint["published"] for endpoint in published]
        assert all(isinstance(port, int) and port > 0 for port in host_ports)
        assert len(set(host_ports)) == 2
        assert not project.compose_port_is_empty("nginx", 80)
        # Task 30 exercises base HTTP; production TLS startup remains a Task 32 boundary.
        assert not project.compose_port_is_empty("nginx", 443)

        html = project.wait_for_host_http(80, "/", status=200)
        assert html.status == 200
        assert html.headers["cache-control"] == "no-store"
        assert html.headers["x-launch-indexing-policy"] == "closed"
        assert html.headers["x-robots-tag"] == "noindex, follow"
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

        readiness = project.wait_for_host_http(
            80,
            "/_internal/launch-readiness",
            status=404,
        )
        assert readiness.status == 404
