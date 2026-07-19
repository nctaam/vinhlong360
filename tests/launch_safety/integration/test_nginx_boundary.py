from __future__ import annotations

import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import pytest


ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "tests" / "launch_safety" / "harness" / "docker-compose.yml"

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _compose(runtime, project: str, environment: dict[str, str], *args: str, capture: bool = False):
    env = os.environ.copy()
    for key in ("COMPOSE_FILE", "COMPOSE_PROJECT_NAME", "COMPOSE_PROFILES", "COMPOSE_ENV_FILES"):
        env.pop(key, None)
    env.update(environment)
    return subprocess.run(
        [runtime.executable, "compose", "-p", project, "-f", str(HARNESS), *args],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
        timeout=180,
    )


def _request(path: str) -> tuple[int, dict[str, str], str]:
    request = urllib.request.Request(
        f"http://127.0.0.1:18080{path}",
        headers={"Host": "vinhlong360.vn"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, {key.lower(): value for key, value in error.headers.items()}, error.read().decode()


def _wait(path: str, expected: int, timeout: int = 90) -> tuple[int, dict[str, str], str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = _request(path)
        if response[0] == expected:
            return response
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {path}={expected}")


def test_nginx_boundary_routes_seo_denies_internal_and_keeps_optional_upstreams_closed(docker_runtime):
    project = f"vl360boundary{os.getpid()}{secrets.token_hex(4)}"
    with tempfile.TemporaryDirectory(prefix="vl360-nginx-boundary-") as temporary:
        runtime_dir = Path(temporary) / "maintenance"
        runtime_dir.mkdir()
        (runtime_dir / "http-context.conf").write_text(
            "geo $launch_maintenance_operator { default 0; 127.0.0.1/32 1; ::1/128 1; }\n",
            encoding="ascii",
        )
        (runtime_dir / "active-server.conf").write_text(
            "# boundary harness keeps the reviewed server open\n", encoding="ascii"
        )
        environment = {
            "COMPOSE_DISABLE_ENV_FILE": "1",
            "VL360_MAINTENANCE_RUNTIME": str(runtime_dir).replace("\\", "/"),
        }
        try:
            result = _compose(docker_runtime, project, environment, "up", "-d", "nginx", capture=True)
            assert result.returncode == 0, result.stderr
            for path in (
                "/robots.txt",
                "/sitemap.xml?batch=raw%2Fbatch",
                "/sitemap-media.xml",
                "/sitemap-index.xml",
            ):
                status, headers, body = _wait(path, 200)
                assert body.startswith("stub-nuxt-upstream:3000:"), (path, body)
                assert headers["cache-control"] == "no-store"
                assert headers["x-launch-indexing-policy"] == "failed-open"

            for path in (
                "/_internal/launch-readiness",
                "/_internal/launch-policy-attestation",
                "/_internal/launch-sitemaps/sitemap.xml?batch=abc",
            ):
                status, headers, body = _wait(path, 404)
                assert "x-vl360-upstream-internal" not in headers
                assert "stub-internal-upstream" not in body

            # Optional agent and bot services are not started, but Nginx remains
            # healthy and closed because their DNS is request-time only.
            status, _headers, _body = _wait("/api/entities?x=%2F", 502)
            assert status == 502
            assert _compose(
                docker_runtime,
                project,
                environment,
                "--profile",
                "optional-upstreams",
                "up",
                "-d",
                "agent",
                "bot-gateway",
            ).returncode == 0
            status, _headers, body = _wait("/api/raw%2Fpath?x=%2F", 200)
            assert body == "stub-agent-upstream:8360:/api/raw%2Fpath?x=%2F\n"
            status, _headers, body = _wait("/admin-api/users?x=%2F", 200)
            assert body == "stub-agent-upstream:8360:/admin/users?x=%2F\n"
            status, _headers, body = _wait("/webhook/raw?x=%2F", 200)
            assert body == "stub-bot-upstream:8361:/webhook/raw?x=%2F\n"
        finally:
            cleanup = _compose(
                docker_runtime,
                project,
                environment,
                "down",
                "-v",
                "--remove-orphans",
                capture=True,
            )
            assert cleanup.returncode == 0, cleanup.stderr
