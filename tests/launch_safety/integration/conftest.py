from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import time
from typing import Callable, Iterator, Mapping
import urllib.error
import urllib.request
import warnings

import pytest


ROOT = Path(__file__).resolve().parents[3]
CLI_MISSING = "Docker integration unavailable: Docker CLI not found"
PLUGIN_MISSING = "Docker integration unavailable: Docker Compose plugin not available"
DAEMON_MISSING = "Docker integration unavailable: Docker daemon not reachable"
REQUIRE_DOCKER = "VL360_REQUIRE_DOCKER_INTEGRATION"
SOURCE_REVISION = re.compile(r"^[a-f0-9]{40}$")
MAX_CAPTURE = 1_500_000
ALLOWED_DIRTY_PREFIXES = ("tests/launch_safety/integration/",)
ALLOWED_DIRTY_PATHS = {
    "web/data.js",
    "web-nuxt/pnpm-lock.yaml",
    "web-nuxt/pnpm-workspace.yaml",
}
NODE_FETCH = r"""
const url = process.argv[1]
try {
  const response = await fetch(url)
  const body = await response.text()
  if (Buffer.byteLength(body, 'utf8') > 1048576) process.exit(24)
  const payload = {
    status: response.status,
    headers: Object.fromEntries([...response.headers].map(([key, value]) => [key.toLowerCase(), value])),
    body,
  }
  process.stdout.write(`VL360_RESPONSE:${JSON.stringify(payload)}`)
} catch {
  process.exit(23)
}
""".strip()
NODE_TCP = r"""
const net = await import('node:net')
const host = process.argv[1]
const port = Number(process.argv[2])
const socket = net.createConnection({ host, port })
socket.setTimeout(5000)
socket.once('connect', () => { socket.destroy(); process.exit(0) })
socket.once('timeout', () => { socket.destroy(); process.exit(1) })
socket.once('error', () => process.exit(1))
""".strip()
POISON_SERVER = r"""
const fs = require('node:fs')
const http = require('node:http')
const countPath = '/tmp/vl360-backend-count'
fs.writeFileSync(countPath, '0')
http.createServer((request, response) => {
  const path = new URL(request.url, 'http://agent').pathname
  const launchPolicyCall = path === '/_internal/launch-policy-attestation'
    || path.startsWith('/_internal/launch-sitemaps/')
  if (launchPolicyCall) {
    const count = Number(fs.readFileSync(countPath, 'utf8')) + 1
    fs.writeFileSync(countPath, String(count))
  }
  response.writeHead(503, { 'content-type': 'application/json', 'cache-control': 'no-store' })
  response.end('{"detail":"poison-backend"}')
}).listen(8360, '0.0.0.0')
""".strip()


@dataclass(frozen=True)
class DockerRuntime:
    executable: str
    revision: str


@dataclass(frozen=True)
class CommandResult:
    returncode: int


@dataclass(frozen=True)
class DockerResponse:
    status: int
    headers: dict[str, str]
    body: str


def _required_docker() -> bool:
    return os.environ.get(REQUIRE_DOCKER) == "1"


def _unavailable(reason: str) -> None:
    if _required_docker():
        pytest.fail(reason, pytrace=False)
    pytest.skip(reason)


def _preflight_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args, 1, "", "")


def _remote_endpoint(value: str) -> bool:
    endpoint = value.strip().strip('"').lower()
    return endpoint.startswith(("tcp://", "ssh://", "http://", "https://"))


def _porcelain_paths(source: str) -> list[str]:
    entries = source.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise AssertionError("Docker integration setup failed: invalid git status")
        paths.append(entry[3:].replace("\\", "/"))
        if "R" in entry[:2] or "C" in entry[:2]:
            if index >= len(entries) or not entries[index]:
                raise AssertionError("Docker integration setup failed: invalid git status")
            paths.append(entries[index].replace("\\", "/"))
            index += 1
    return paths


def _assert_head_snapshot_safe(source: str) -> None:
    for path in _porcelain_paths(source):
        if path in ALLOWED_DIRTY_PATHS:
            continue
        if any(path.startswith(prefix) for prefix in ALLOWED_DIRTY_PREFIXES):
            continue
        raise AssertionError(
            "Docker integration setup failed: runtime snapshot differs from HEAD"
        )


@pytest.fixture(scope="session")
def docker_runtime() -> DockerRuntime:
    docker = shutil.which("docker")
    if docker is None:
        _unavailable(CLI_MISSING)

    compose_version = _preflight_command([docker, "compose", "version"])
    if compose_version.returncode != 0:
        _unavailable(PLUGIN_MISSING)

    context = _preflight_command(
        [docker, "context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"],
    )
    if context.returncode != 0:
        pytest.fail("Docker integration preflight failed: Docker context inspection failed", pytrace=False)
    endpoints = [context.stdout, os.environ.get("DOCKER_HOST", "")]
    if any(_remote_endpoint(endpoint) for endpoint in endpoints):
        pytest.fail(
            "Docker integration refused: remote tcp/ssh Docker context is not allowed",
            pytrace=False,
        )

    daemon = _preflight_command([docker, "info", "--format", "{{json .ServerVersion}}"])
    if daemon.returncode != 0:
        _unavailable(DAEMON_MISSING)

    revision_result = _preflight_command(["git", "rev-parse", "--verify", "HEAD"])
    revision = revision_result.stdout.strip()
    if revision_result.returncode != 0 or not SOURCE_REVISION.fullmatch(revision):
        pytest.fail("Docker integration setup failed: source revision unavailable", pytrace=False)
    return DockerRuntime(executable=docker, revision=revision)


@pytest.fixture
def head_snapshot_validator(
    docker_runtime: DockerRuntime,
) -> Callable[[str], None]:
    del docker_runtime
    return _assert_head_snapshot_safe


class ComposeProject:
    def __init__(
        self,
        runtime: DockerRuntime,
        *,
        nuxt_environment: Mapping[str, str] | None = None,
        poison_backend: bool = False,
    ) -> None:
        allowed = {"LAUNCH_INDEXING_MODE", "LAUNCH_INDEXING_OWNER_APPROVED"}
        supplied = dict(nuxt_environment or {})
        unknown = set(supplied) - allowed
        if unknown:
            raise ValueError(f"unsupported Nuxt integration environment: {sorted(unknown)}")
        self.runtime = runtime
        self.nuxt_environment = supplied
        self.poison_backend = poison_backend
        self.name = f"vl360it{os.getpid()}{secrets.token_hex(5)}"
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self.root: Path | None = None
        self.compose_files: tuple[Path, ...] = ()
        self._closed = False
        self._cleanup_attempts = 0

    def __enter__(self) -> ComposeProject:
        try:
            self._prepare()
            self._compose("config", "--quiet", timeout=60)
            if self.poison_backend:
                self.up("backend-poison", no_deps=True)
                self.wait_for_container("backend-poison", state="running")
            return self
        except BaseException as error:
            try:
                self.close()
            except BaseException:
                add_note = getattr(error, "add_note", None)
                if callable(add_note):
                    add_note("Docker integration cleanup also failed during setup")
                else:
                    warnings.warn(
                        "Docker integration cleanup also failed during setup",
                        RuntimeWarning,
                        stacklevel=2,
                    )
            raise

    def __exit__(self, exc_type, exc, traceback) -> bool:
        try:
            self.close()
        except BaseException:
            if exc is not None:
                add_note = getattr(exc, "add_note", None)
                if callable(add_note):
                    add_note("Docker integration cleanup also failed")
                else:
                    warnings.warn(
                        "Docker integration cleanup also failed",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                return False
            raise
        return False

    def _prepare(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="vl360-integration-")
        temporary_root = Path(self._temporary.name)
        archive = temporary_root / "source.tar"
        self.root = temporary_root / "project"
        self.root.mkdir()

        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
        )
        if status_result.returncode != 0:
            raise AssertionError("Docker integration setup failed: git status failed")
        _assert_head_snapshot_safe(status_result.stdout)

        archive_result = subprocess.run(
            ["git", "archive", "--format=tar", f"--output={archive}", self.runtime.revision],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
        if archive_result.returncode != 0:
            raise AssertionError("Docker integration setup failed: git archive failed")
        with tarfile.open(archive, "r") as source:
            for member in source.getmembers():
                path = Path(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise AssertionError(
                        "Docker integration setup failed: unsafe git archive path"
                    )
            source.extractall(self.root)
        archive.unlink()

        if any(path.name == ".env" for path in self.root.rglob(".env")):
            raise AssertionError("Docker integration setup failed: sanitized archive contains .env")
        if (self.root / ".git").exists():
            raise AssertionError("Docker integration setup failed: sanitized archive contains .git")

        integration = self.root / ".vl360-integration"
        integration.mkdir(parents=True)
        override = integration / "docker-compose.integration.yml"
        override.write_text(self._override_source(), encoding="utf-8", newline="\n")
        self.compose_files = (self.root / "docker-compose.yml", override)

    def _override_source(self) -> str:
        environment = "".join(
            f"      {key}: {json.dumps(value)}\n"
            for key, value in sorted(self.nuxt_environment.items())
        )
        if not environment:
            environment = "      VL360_INTEGRATION_SAFE_CLOSED: '1'\n"
        return (
            "services:\n"
            "  nuxt:\n"
            "    environment:\n"
            f"{environment}"
            "  nginx:\n"
            "    ports: !override\n"
            "      - '127.0.0.1::80'\n"
            "      - '127.0.0.1::443'\n"
            "  backend-poison:\n"
            "    image: node:22-alpine\n"
            f"    command: [\"node\", \"-e\", {json.dumps(POISON_SERVER)}]\n"
            "    expose:\n"
            "      - '8360'\n"
            "    networks:\n"
            "      default:\n"
            "        aliases:\n"
            "          - agent\n"
        )

    def _environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        for key in (
            "COMPOSE_FILE",
            "COMPOSE_PROJECT_NAME",
            "COMPOSE_PROFILES",
            "COMPOSE_ENV_FILES",
            "LAUNCH_INDEXING_MODE",
            "LAUNCH_INDEXING_OWNER_APPROVED",
        ):
            environment.pop(key, None)
        token = self.name[-10:]
        environment.update({
            "BUILD_REVISION": self.runtime.revision,
            "COMPOSE_DISABLE_ENV_FILE": "1",
            "POSTGRES_PASSWORD": f"vl360-integration-postgres-{token}",
            "GRAFANA_ADMIN_PASSWORD": f"vl360-integration-grafana-{token}",
        })
        return environment

    def _command(self, *args: str) -> list[str]:
        command = [self.runtime.executable, "compose", "-p", self.name]
        for compose_file in self.compose_files:
            command.extend(("-f", str(compose_file)))
        command.extend(args)
        return command

    def _raw(
        self,
        *args: str,
        capture: bool = False,
        timeout: int = 180,
    ) -> subprocess.CompletedProcess[str]:
        assert self.root is not None
        try:
            result = subprocess.run(
                self._command(*args),
                cwd=self.root,
                env=self._environment(),
                check=False,
                stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise AssertionError(f"Docker integration command timed out: {args[0]}") from error
        if capture and len(result.stdout) > MAX_CAPTURE:
            raise AssertionError(f"Docker integration command exceeded output bound: {args[0]}")
        return result

    def _docker_raw(
        self,
        *args: str,
        capture: bool = False,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        assert self.root is not None
        try:
            result = subprocess.run(
                [self.runtime.executable, *args],
                cwd=self.root,
                env=self._environment(),
                check=False,
                stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise AssertionError(f"Docker integration Docker command timed out: {args[0]}") from error
        if capture and len(result.stdout) > MAX_CAPTURE:
            raise AssertionError(
                f"Docker integration Docker command exceeded output bound: {args[0]}"
            )
        return result

    def _compose(self, *args: str, check: bool = True, timeout: int = 180) -> CommandResult:
        result = self._raw(*args, timeout=timeout)
        if check and result.returncode != 0:
            raise AssertionError(
                f"Docker integration command failed: {args[0]} (exit {result.returncode}); "
                f"{self._diagnostics()}"
            )
        return CommandResult(result.returncode)

    def compose(self, *args: str, check: bool = True, timeout: int = 180) -> CommandResult:
        return self._compose(*args, check=check, timeout=timeout)

    def up(self, *services: str, build: bool = False, no_deps: bool = False) -> None:
        args = ["up", "-d"]
        if build:
            args.append("--build")
        if no_deps:
            args.append("--no-deps")
        args.extend(services)
        self._compose(*args, timeout=1200 if build else 300)

    def _ps(self) -> list[dict[str, object]]:
        result = self._raw("ps", "-a", "--format", "json", capture=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError("Docker integration probe failed: compose ps")
        source = result.stdout.strip()
        if not source:
            return []
        try:
            parsed = json.loads(source)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            rows: list[dict[str, object]] = []
            for line in source.splitlines():
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
            return rows
        raise AssertionError("Docker integration probe failed: invalid compose ps JSON")

    def _container_id(self, service: str) -> str | None:
        result = self._raw("ps", "-aq", service, capture=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError("Docker integration probe failed: compose ps id")
        identifiers = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(identifiers) > 1:
            raise AssertionError("Docker integration probe failed: duplicate service containers")
        return identifiers[0] if identifiers else None

    def inspect_container_state(self, service: str) -> dict[str, object] | None:
        identifier = self._container_id(service)
        if identifier is None:
            return None
        result = self._docker_raw(
            "inspect",
            "--format",
            "{{json .State}}\n{{.RestartCount}}",
            identifier,
            capture=True,
        )
        if result.returncode != 0:
            raise AssertionError("Docker integration probe failed: container state inspect")
        lines = result.stdout.splitlines()
        if len(lines) != 2:
            raise AssertionError("Docker integration probe failed: invalid container state inspect")
        try:
            state = json.loads(lines[0])
            restart_count = int(lines[1])
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise AssertionError(
                "Docker integration probe failed: invalid container state JSON"
            ) from error
        if not isinstance(state, dict):
            raise AssertionError("Docker integration probe failed: invalid container state")
        return {"state": state, "restart_count": restart_count}

    def container_never_started(self, service: str) -> bool:
        inspected = self.inspect_container_state(service)
        if inspected is None:
            return True
        state = inspected["state"]
        assert isinstance(state, dict)
        started_at = str(state.get("StartedAt", ""))
        zero_started_at = not started_at or started_at.startswith("0001-01-01T00:00:00")
        return (
            state.get("Running") is False
            and str(state.get("Status", "")).lower() in {"created", ""}
            and inspected["restart_count"] == 0
            and zero_started_at
        )

    def container_state(self, service: str) -> dict[str, str | None] | None:
        for item in self._ps():
            if item.get("Service") != service:
                continue
            health_value = item.get("Health")
            return {
                "state": str(item.get("State", "")).lower(),
                "health": str(health_value).lower() if health_value else None,
            }
        return None

    def wait_for_container(
        self,
        service: str,
        *,
        state: str,
        health: str | None = None,
        timeout: int = 180,
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            actual = self.container_state(service)
            if actual is not None and actual["state"] == state:
                if health is None or actual["health"] == health:
                    return
            time.sleep(2)
        raise AssertionError(
            f"Docker integration container wait failed: {service} expected {state}/{health}; "
            f"{self._diagnostics()}"
        )

    def running_services(self) -> list[str]:
        return sorted(
            str(item["Service"])
            for item in self._ps()
            if str(item.get("State", "")).lower() == "running"
        )

    def inspect_host_bindings(self, service: str) -> list[dict[str, object]]:
        identifier = self._container_id(service)
        if identifier is None:
            return []
        result = self._docker_raw(
            "inspect",
            "--format",
            "{{json .HostConfig.PortBindings}}\n{{json .NetworkSettings.Ports}}",
            identifier,
            capture=True,
        )
        if result.returncode != 0:
            raise AssertionError("Docker integration probe failed: port binding inspect")
        lines = result.stdout.splitlines()
        if len(lines) != 2:
            raise AssertionError("Docker integration probe failed: invalid port binding inspect")
        try:
            sources = [json.loads(line) for line in lines]
        except json.JSONDecodeError as error:
            raise AssertionError(
                "Docker integration probe failed: invalid port binding JSON"
            ) from error
        endpoints: list[dict[str, object]] = []
        seen: set[tuple[str, int, int, str]] = set()
        for ports in sources:
            if ports is None:
                continue
            if not isinstance(ports, dict):
                raise AssertionError("Docker integration probe failed: invalid port bindings")
            for target_protocol, bindings in ports.items():
                if not isinstance(bindings, list):
                    continue
                target_text, separator, protocol = str(target_protocol).partition("/")
                if not separator or not target_text.isdecimal():
                    raise AssertionError("Docker integration probe failed: invalid target port")
                for binding in bindings:
                    if not isinstance(binding, dict):
                        raise AssertionError("Docker integration probe failed: invalid port binding")
                    published = str(binding.get("HostPort", ""))
                    if not published.isdecimal() or int(published) <= 0:
                        continue
                    host_ip = str(binding.get("HostIp", ""))
                    identity = (host_ip, int(published), int(target_text), protocol)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    endpoints.append({
                        "service": service,
                        "host_ip": host_ip,
                        "published": int(published),
                        "target": int(target_text),
                        "protocol": protocol,
                    })
        return endpoints

    def all_published_endpoints(self) -> list[dict[str, object]]:
        return [
            endpoint
            for service in (str(item.get("Service", "")) for item in self._ps())
            for endpoint in self.inspect_host_bindings(service)
        ]

    def published_endpoints(self, service: str) -> list[dict[str, object]]:
        return self.inspect_host_bindings(service)

    def compose_port_is_empty(self, service: str, port: int) -> bool:
        result = self._raw("port", service, str(port), capture=True, timeout=30)
        if result.returncode not in {0, 1}:
            raise AssertionError("Docker integration probe failed: compose port")
        return not result.stdout.strip()

    def _fetch_result(self, from_service: str, url: str) -> DockerResponse | None:
        result = self._raw(
            "exec",
            "-T",
            from_service,
            "node",
            "-e",
            NODE_FETCH,
            url,
            capture=True,
            timeout=45,
        )
        if result.returncode != 0:
            return None
        marker = "VL360_RESPONSE:"
        if not result.stdout.startswith(marker):
            return None
        try:
            payload = json.loads(result.stdout.removeprefix(marker))
            return DockerResponse(
                status=int(payload["status"]),
                headers={str(key): str(value) for key, value in payload["headers"].items()},
                body=str(payload["body"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def fetch(self, from_service: str, url: str) -> DockerResponse:
        response = self._fetch_result(from_service, url)
        if response is None:
            raise AssertionError(
                f"Docker integration HTTP probe failed: {from_service}; {self._diagnostics()}"
            )
        return response

    def wait_for_http(
        self,
        from_service: str,
        url: str,
        *,
        status: int,
        timeout: int = 120,
    ) -> DockerResponse:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = self._fetch_result(from_service, url)
            if response is not None and response.status == status:
                return response
            time.sleep(2)
        raise AssertionError(
            f"Docker integration HTTP wait failed: {from_service} expected {status}; "
            f"{self._diagnostics()}"
        )

    def _host_http_result(self, target: int, path: str) -> DockerResponse | None:
        endpoints = [
            endpoint
            for endpoint in self.published_endpoints("nginx")
            if endpoint["target"] == target
        ]
        if len(endpoints) != 1:
            return None
        endpoint = endpoints[0]
        url = f"http://127.0.0.1:{endpoint['published']}{path}"
        request = urllib.request.Request(url, headers={"Host": "localhost"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=10) as response:
                body = response.read(1_048_577)
                if len(body) > 1_048_576:
                    raise AssertionError("Docker integration host HTTP response exceeded bound")
                return DockerResponse(
                    status=response.status,
                    headers={key.lower(): value for key, value in response.headers.items()},
                    body=body.decode("utf-8", errors="strict"),
                )
        except urllib.error.HTTPError as error:
            body = error.read(1_048_577)
            if len(body) > 1_048_576:
                raise AssertionError("Docker integration host HTTP response exceeded bound")
            return DockerResponse(
                status=error.code,
                headers={key.lower(): value for key, value in error.headers.items()},
                body=body.decode("utf-8", errors="strict"),
            )
        except (OSError, UnicodeError):
            return None

    def wait_for_host_http(
        self,
        target: int,
        path: str,
        *,
        status: int,
        timeout: int = 120,
    ) -> DockerResponse:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = self._host_http_result(target, path)
            if response is not None and response.status == status:
                return response
            time.sleep(2)
        raise AssertionError(
            f"Docker integration host HTTP wait failed: nginx target {target} expected {status}; "
            f"{self._diagnostics()}"
        )

    def tcp_reachable(self, from_service: str, host: str, port: int) -> bool:
        result = self._raw(
            "exec",
            "-T",
            from_service,
            "node",
            "-e",
            NODE_TCP,
            host,
            str(port),
            timeout=30,
        )
        return result.returncode == 0

    def launch_backend_request_count(self) -> int:
        script = (
            "const fs=require('node:fs');"
            "process.stdout.write(fs.readFileSync('/tmp/vl360-backend-count','utf8'))"
        )
        result = self._raw(
            "exec",
            "-T",
            "backend-poison",
            "node",
            "-e",
            script,
            capture=True,
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout.isdecimal():
            raise AssertionError("Docker integration poison-backend count probe failed")
        return int(result.stdout)

    def _diagnostics(self) -> str:
        states = "unavailable"
        try:
            rows = self._ps()
            states = ",".join(
                f"{item.get('Service')}={item.get('State')}/{item.get('Health') or '-'}"
                for item in rows
            ) or "none"
        except BaseException:
            pass
        log_summary = "unavailable"
        try:
            logs = self._raw("logs", "--no-color", "--tail", "40", capture=True, timeout=30)
            bounded = logs.stdout[:65536]
            log_summary = f"exit={logs.returncode},lines={len(bounded.splitlines())},bytes={len(bounded.encode('utf-8'))}"
        except BaseException:
            pass
        return f"ps[{states}] logs[{log_summary}]"

    def _assert_no_project_residue(self) -> None:
        label = f"label=com.docker.compose.project={self.name}"
        probes = (
            ("containers", ("ps", "-aq", "--filter", label)),
            ("networks", ("network", "ls", "-q", "--filter", label)),
            ("volumes", ("volume", "ls", "-q", "--filter", label)),
            ("images", ("image", "ls", "-q", "--filter", label)),
        )
        for resource, command in probes:
            result = self._docker_raw(*command, capture=True, timeout=30)
            if result.returncode != 0:
                raise AssertionError(
                    f"Docker integration cleanup verification failed: {resource} inspect"
                )
            if result.stdout.strip():
                raise AssertionError(
                    f"Docker integration cleanup verification failed: residual {resource}"
                )

    def close(self) -> None:
        if self._closed:
            return
        self._cleanup_attempts += 1
        if self._cleanup_attempts > 2:
            raise AssertionError("Docker integration cleanup retry limit exceeded")
        if self.root is not None and self.compose_files:
            result = self._raw(
                "down",
                "-v",
                "--remove-orphans",
                "--rmi",
                "local",
                "--timeout",
                "10",
                timeout=180,
            )
            if result.returncode != 0:
                raise AssertionError(
                    f"Docker integration cleanup failed: down exit {result.returncode}"
                )
            self._assert_no_project_residue()
        if self._temporary is not None:
            self._temporary.cleanup()
        self._closed = True


@pytest.fixture
def compose_project_factory(
    docker_runtime: DockerRuntime,
) -> Iterator[Callable[..., ComposeProject]]:
    projects: list[ComposeProject] = []

    def factory(**kwargs) -> ComposeProject:
        project = ComposeProject(docker_runtime, **kwargs)
        projects.append(project)
        return project

    yield factory

    errors: list[BaseException] = []
    for project in reversed(projects):
        try:
            project.close()
        except BaseException as error:
            errors.append(error)
    if errors:
        raise AssertionError(
            f"Docker integration fixture cleanup failed for {len(errors)} project(s)"
        ) from errors[0]
