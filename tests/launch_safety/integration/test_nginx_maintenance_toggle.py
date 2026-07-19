from __future__ import annotations

import ipaddress
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
import subprocess
import tempfile
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import pytest


ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "tests" / "launch_safety" / "harness" / "docker-compose.nginx-maintenance.yml"
STUB_UPSTREAM = ROOT / "tests" / "launch_safety" / "harness" / "stub_upstream.py"
HTTP_CONTEXT = """\
geo $launch_maintenance_operator {
    default 0;
    127.0.0.1/32 1;
    ::1/128 1;
    {operator_cidr} 1;
}
"""
SERVER_ENABLED = "if ($launch_maintenance_operator = 0) { return 503; }\n"
SERVER_DISABLED = "# Maintenance disabled: requests continue to the reviewed server locations.\n"

def _write_certificate(ssl: Path) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "vinhlong360.vn")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("vinhlong360.vn"), x509.DNSName("www.vinhlong360.vn")]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    (ssl / "fullchain.pem").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    (ssl / "privkey.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_nginx_maintenance_harness_assets_are_present():
    assert HARNESS.is_file()
    assert STUB_UPSTREAM.is_file()


def _compose(docker_runtime, project: str, maintenance: Path, *args: str, capture: bool = False):
    environment = os.environ.copy()
    for key in (
        "COMPOSE_FILE",
        "COMPOSE_PROJECT_NAME",
        "COMPOSE_PROFILES",
        "COMPOSE_ENV_FILES",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "COMPOSE_DISABLE_ENV_FILE": "1",
            "VL360_MAINTENANCE_RUNTIME": str(maintenance).replace("\\", "/"),
            "VL360_NGINX_SSL_RUNTIME": str(maintenance.parent / "ssl").replace("\\", "/"),
        }
    )
    command = [docker_runtime.executable, "compose", "-p", project, "-f", str(HARNESS), *args]
    return subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
        timeout=180,
    )


def _probe_script() -> str:
    return """\
import json, ssl, sys, urllib.error, urllib.request
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, new):
        return None
url = sys.argv[1]
request = urllib.request.Request(url, headers={"Host": "vinhlong360.vn"})
handlers = [NoRedirect(), urllib.request.ProxyHandler({})]
if url.startswith("https:"):
    handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
opener = urllib.request.build_opener(*handlers)
try:
    with opener.open(request, timeout=10) as response:
        body = response.read().decode("utf-8", errors="strict")
        print(json.dumps({"status": response.status, "headers": dict(response.headers), "body": body}))
except urllib.error.HTTPError as error:
    body = error.read().decode("utf-8", errors="strict")
    print(json.dumps({"status": error.code, "headers": dict(error.headers), "body": body}))
"""


def _probe(docker_runtime, project: str, maintenance: Path, service: str, url: str) -> dict[str, object] | None:
    result = _compose(
        docker_runtime,
        project,
        maintenance,
        "exec",
        "-T",
        service,
        "python",
        "-c",
        _probe_script(),
        url,
        capture=True,
    )
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _wait_probe(docker_runtime, project: str, maintenance: Path, service: str, url: str, status: int) -> dict[str, object]:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        response = _probe(docker_runtime, project, maintenance, service, url)
        if response is not None and response.get("status") == status:
            return response
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {service} {url} status {status}")


def _operator_ip(docker_runtime, project: str, maintenance: Path) -> str:
    container = _compose(docker_runtime, project, maintenance, "ps", "-q", "operator", capture=True).stdout.strip()
    assert container
    environment = os.environ.copy()
    result = subprocess.run(
        [docker_runtime.executable, "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container],
        cwd=ROOT,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    address = result.stdout.strip()
    ipaddress.ip_address(address)
    return address


def _assert_probe(response: dict[str, object], status: int, *, body: str | None = None) -> None:
    assert response["status"] == status
    if body is not None:
        assert response["body"] == body


def test_maintenance_toggle_gates_http_and_https_without_bypassing_upstream_or_ingress(
    docker_runtime,
):
    project = f"vl360maint{os.getpid()}{secrets.token_hex(4)}"
    with tempfile.TemporaryDirectory(prefix="vl360-nginx-maintenance-") as temporary:
        root = Path(temporary)
        runtime = root / "maintenance"
        ssl = root / "ssl"
        runtime.mkdir()
        ssl.mkdir()
        _write_certificate(ssl)
        (runtime / "http-context.conf").write_text(
            HTTP_CONTEXT.format(operator_cidr="192.0.2.1/32"),
            encoding="ascii",
        )

        try:
            for enabled in (True, False):
                active = SERVER_ENABLED if enabled else SERVER_DISABLED
                (runtime / "active-server.conf").write_text(active, encoding="ascii")
                _compose(docker_runtime, project, runtime, "up", "-d", "upstream", "operator", "visitor")
                operator = _operator_ip(docker_runtime, project, runtime)
                (runtime / "http-context.conf").write_text(
                    HTTP_CONTEXT.format(operator_cidr=f"{operator}/32"),
                    encoding="ascii",
                )
                _compose(
                    docker_runtime,
                    project,
                    runtime,
                    "up",
                    "-d",
                    "nginx-http",
                    "nginx-ssl",
                )

                expected_public = 503 if enabled else 200
                expected_redirect = 503 if enabled else 301
                for service, url, expected in (
                    ("visitor", "http://nginx-http/", expected_public),
                    ("operator", "http://nginx-http/", 200),
                    ("visitor", "https://nginx-ssl/", expected_public),
                    ("operator", "https://nginx-ssl/", 200),
                    ("visitor", "http://nginx-ssl/", expected_redirect),
                    ("operator", "http://nginx-ssl/", 301),
                ):
                    response = _wait_probe(docker_runtime, project, runtime, service, url, expected)
                    if expected == 200:
                        _assert_probe(response, 200, body="stub-upstream:3000:/\n")
                        assert response["headers"]["X-Robots-Tag"] == "noindex, follow"

                for service, url in (
                    ("visitor", "http://nginx-http/_internal/launch-readiness"),
                    ("operator", "http://nginx-http/_internal/launch-readiness"),
                    ("visitor", "https://nginx-ssl/_internal/launch-readiness"),
                    ("operator", "https://nginx-ssl/_internal/launch-readiness"),
                ):
                    response = _wait_probe(docker_runtime, project, runtime, service, url, 404)
                    _assert_probe(response, 404)

                _compose(docker_runtime, project, runtime, "down", "-v", "--remove-orphans")
        finally:
            _compose(docker_runtime, project, runtime, "down", "-v", "--remove-orphans")
