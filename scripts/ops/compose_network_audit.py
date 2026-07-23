"""Audit the rendered production Compose listener boundary.

The validator intentionally accepts the JSON model emitted by Docker Compose,
so unit tests do not need Docker or a YAML parser.  The command-line entrypoint
is the only code that shells out to Compose.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import ipaddress
import json
import os
import secrets
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, NamedTuple, Sequence


SCHEMA_VERSION = 1
AUDIT_REVISION = "compose-network-audit-v2"
CHECK_NAMES = (
    "agent_bind_host",
    "bot_bind_host_and_agent_url",
    "container_names_absent",
    "developer_added_publications_loopback",
    "exact_healthcheck_commands",
    "non_nginx_services_unpublished",
    "no_external_or_host_network",
    "nginx_exclusive_public_endpoints",
    "maintenance_initializer_exact",
    "maintenance_runtime_shared_with_host",
    "nginx_depends_on_healthy_nuxt_and_completed_maintenance_init",
    "nuxt_backend_independent_readiness",
    "nuxt_bind_host",
    "nuxt_compose_api_origins",
    "no_launch_unlock_environment",
    "required_services_present",
    "shared_private_bridge_network",
    "systemd_dependency_topology",
)
INTERNAL_SERVICES = {
    "postgres",
    "redis",
    "agent",
    "bot-gateway",
    "nuxt",
    "maintenance-runtime-init",
    "prometheus",
    "grafana",
    "loki",
    "promtail",
}
FORBIDDEN_ENV_KEYS = {
    "LAUNCH_INDEXING_MODE",
    "LAUNCH_INDEXING_OWNER_APPROVED",
}
REQUIRED_SERVICES = INTERNAL_SERVICES | {"nginx"}
EXPECTED_HEALTHCHECKS = {
    "agent": ("CMD", "curl", "-f", "http://127.0.0.1:8360/health"),
    "bot-gateway": ("CMD", "curl", "-f", "http://127.0.0.1:8361/"),
    "nuxt": (
        "CMD-SHELL",
        "wget -qO- http://127.0.0.1:3000/_internal/launch-readiness >/dev/null",
    ),
}
SOURCE_DIGEST_KIND = "sha256-utf8-lf-v1"
SNAPSHOT_FILE_NAMES = (
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "docker-compose.dev.yml",
    "docker-compose.systemd-deps.yml",
)
LAUNCH_NETWORK_SERVICES = ("agent", "bot-gateway", "nuxt", "nginx")
NUXT_ALLOWED_ENV_KEYS = {"HOST", "NITRO_HOST", "NUXT_API_BASE", "PORT"}
EXPECTED_NUXT_API_BASE = "http://agent:8360"
MAINTENANCE_RUNTIME_TARGET = "/etc/nginx/vl360-maintenance"
MAINTENANCE_SOURCE_TARGET = "/opt/vl360-maintenance-source"
MAINTENANCE_SOURCE_SUFFIX = "/ops/nginx/maintenance"
EXPECTED_MAINTENANCE_INIT_COMMAND = (
    "/bin/sh",
    "-ec",
    "set -eu\n"
    "install -d -m 0755 /etc/nginx/vl360-maintenance\n"
    "sed 's#__OPERATOR_CIDR__#127.0.0.1/32#' "
    "/opt/vl360-maintenance-source/http-context.conf.template "
    "> /etc/nginx/vl360-maintenance/http-context.conf\n"
    "install -m 0644 /opt/vl360-maintenance-source/server-enabled.conf "
    "/etc/nginx/vl360-maintenance/server-enabled.conf\n"
    "install -m 0644 /opt/vl360-maintenance-source/server-disabled.conf "
    "/etc/nginx/vl360-maintenance/server-disabled.conf\n"
    "ln -sfn server-disabled.conf /etc/nginx/vl360-maintenance/active-server.conf\n",
)
EXPECTED_DEVELOPER_ENDPOINTS = {
    ("postgres", "127.0.0.1", 5432, 5432, "tcp"),
    ("redis", "127.0.0.1", 6379, 6379, "tcp"),
    ("agent", "127.0.0.1", 8360, 8360, "tcp"),
    ("bot-gateway", "127.0.0.1", 8361, 8361, "tcp"),
    ("nuxt", "127.0.0.1", 3000, 3000, "tcp"),
    ("prometheus", "127.0.0.1", 9090, 9090, "tcp"),
    ("grafana", "127.0.0.1", 3001, 3000, "tcp"),
    ("loki", "127.0.0.1", 3100, 3100, "tcp"),
}
EXPECTED_SYSTEMD_ENDPOINTS = {
    ("postgres", "127.0.0.1", 5432, 5432, "tcp"),
    ("redis", "127.0.0.1", 6379, 6379, "tcp"),
}


class SourceSnapshot(NamedTuple):
    relative_path: str
    normalized_sha256: str
    raw_content: bytes


class SnapshotRenderInputs(NamedTuple):
    root: Path
    compose: Path
    production: Path
    developer: Path
    systemd: Path


def canonical_json_bytes(value: object) -> bytes:
    """Return stable UTF-8 JSON bytes with one trailing newline."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _exact_port(value: object) -> int | None:
    if type(value) is int:
        port = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        port = int(value)
    else:
        return None
    return port if 1 <= port <= 65535 else None


def _port_endpoint(service: str, value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    target = _exact_port(value.get("target"))
    published = _exact_port(value.get("published"))
    if target is None or published is None:
        return None
    host_value = value.get("host_ip") or "0.0.0.0"
    if not isinstance(host_value, str):
        return None
    try:
        host_ip = ipaddress.ip_address(host_value).compressed
    except ValueError:
        return None
    protocol_value = value.get("protocol", "tcp")
    if not isinstance(protocol_value, str):
        return None
    return {
        "service": service,
        "host_ip": host_ip,
        "published": published,
        "target": target,
        "protocol": protocol_value.lower(),
    }


def published_endpoints(model: Mapping[str, Any]) -> list[dict[str, object]]:
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return []
    endpoints: list[dict[str, object]] = []
    for service_name, service in services.items():
        if not isinstance(service, Mapping):
            continue
        ports = service.get("ports", ())
        if not isinstance(ports, Sequence) or isinstance(ports, (str, bytes)):
            continue
        for port in ports:
            endpoint = _port_endpoint(str(service_name), port)
            if endpoint is not None:
                endpoints.append(endpoint)
    return endpoints


def published_ports(model: Mapping[str, Any]) -> set[tuple[str, int]]:
    """Return ``(service, host-port)`` entries from a Compose model."""

    return {
        (str(endpoint["service"]), int(endpoint["published"]))
        for endpoint in published_endpoints(model)
    }


def _published_port_entry_count(model: Mapping[str, Any]) -> int | None:
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return None
    count = 0
    for service in services.values():
        if not isinstance(service, Mapping):
            return None
        ports = service.get("ports", ())
        if not isinstance(ports, Sequence) or isinstance(ports, (str, bytes)):
            return None
        count += len(ports)
    return count


def _endpoint_identity(endpoint: Mapping[str, object]) -> tuple[str, str, int, int, str]:
    return (
        str(endpoint["service"]),
        str(endpoint["host_ip"]),
        int(endpoint["published"]),
        int(endpoint["target"]),
        str(endpoint["protocol"]),
    )


def _environment(service: Mapping[str, Any]) -> Mapping[str, Any]:
    value = service.get("environment", {})
    if isinstance(value, Mapping):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        pairs: dict[str, str | None] = {}
        for item in value:
            if isinstance(item, str):
                name, separator, env_value = item.partition("=")
                pairs[name] = env_value if separator else None
        return pairs
    return {}


def _service_networks(service: Mapping[str, Any]) -> set[str]:
    value = service.get("networks", {})
    if isinstance(value, Mapping):
        return {str(name) for name in value}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return {str(name) for name in value}
    return set()


def _has_shared_private_bridge_network(
    model: Mapping[str, Any], services: Mapping[str, Any]
) -> bool:
    network_sets: list[set[str]] = []
    for name in LAUNCH_NETWORK_SERVICES:
        service = services.get(name, {})
        if not isinstance(service, Mapping):
            return False
        networks = _service_networks(service)
        if not networks:
            return False
        network_sets.append(networks)
    shared = set.intersection(*network_sets)
    definitions = model.get("networks", {})
    if not shared or not isinstance(definitions, Mapping):
        return False
    for name in shared:
        definition = definitions.get(name, {})
        if not isinstance(definition, Mapping):
            continue
        if definition.get("external") is True:
            continue
        if definition.get("driver", "bridge") == "bridge":
            return True
    return False


def _exposed(service: Mapping[str, Any], port: int) -> bool:
    exposed = service.get("expose", ())
    if not isinstance(exposed, Sequence) or isinstance(exposed, (str, bytes)):
        return False
    return any(str(item).split("/")[0] == str(port) for item in exposed)


def _healthcheck_command(service: Mapping[str, Any]) -> tuple[str, ...] | None:
    healthcheck = service.get("healthcheck", {})
    if not isinstance(healthcheck, Mapping):
        return None
    if healthcheck.get("disable") is True:
        return None
    test = healthcheck.get("test", ())
    if (
        isinstance(test, Sequence)
        and not isinstance(test, (str, bytes))
        and all(isinstance(item, str) for item in test)
    ):
        return tuple(test)
    return None


def _nginx_endpoints_are_exact(model: Mapping[str, Any]) -> bool:
    endpoints = _nginx_endpoints(model)
    if endpoints is None:
        return False
    for endpoint in endpoints:
        host_ip = ipaddress.ip_address(str(endpoint["host_ip"]))
        if host_ip.is_loopback or endpoint["protocol"] != "tcp":
            return False
    return {
        (int(endpoint["published"]), int(endpoint["target"]))
        for endpoint in endpoints
    } == {(80, 80), (443, 443)}


def _nginx_endpoints(model: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return None
    nginx = services.get("nginx", {})
    if not isinstance(nginx, Mapping):
        return None
    ports = nginx.get("ports", ())
    if (
        not isinstance(ports, Sequence)
        or isinstance(ports, (str, bytes))
        or len(ports) != 2
    ):
        return None
    endpoints = [_port_endpoint("nginx", port) for port in ports]
    if any(endpoint is None for endpoint in endpoints):
        return None
    return [endpoint for endpoint in endpoints if endpoint is not None]


def validate_production_model(
    model: Mapping[str, Any], *, compose_root: Path | None = None
) -> list[str]:
    """Return stable issue strings for a rendered production Compose model."""

    issues: list[str] = []
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return ["services must be an object"]
    issues.extend(_production_required_issues(model, services))
    issues.extend(_production_service_issues(services))
    issues.extend(_production_nuxt_issues(services))
    issues.extend(_production_maintenance_issues(services, compose_root=compose_root))
    issues.extend(_production_healthcheck_issues(services))
    issues.extend(_production_nginx_issues(services))
    return sorted(set(issues))


def _production_required_issues(
    model: Mapping[str, Any], services: Mapping[str, Any]
) -> list[str]:
    issues = [
        f"required service is missing: {missing}"
        for missing in sorted(REQUIRED_SERVICES.difference(services))
    ]
    if not _nginx_endpoints_are_exact(model):
        issues.append("nginx exclusive public endpoints violated")

    networks = model.get("networks", {})
    if isinstance(networks, Mapping):
        for name, network in networks.items():
            if isinstance(network, Mapping) and network.get("external") is True:
                issues.append(f"external network is forbidden: {name}")
    if not _has_shared_private_bridge_network(model, services):
        issues.append("launch services must share a private bridge network")

    return issues


def _production_service_issues(services: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for name, service in services.items():
        issues.extend(_production_single_service_issues(name, service))
    issues.extend(_production_agent_issues(services.get("agent", {})))
    issues.extend(_production_bot_issues(services.get("bot-gateway", {})))
    return issues


def _production_single_service_issues(name: object, service: object) -> list[str]:
    if not isinstance(service, Mapping):
        return [f"service is not an object: {name}"]
    issues: list[str] = []
    if str(service.get("network_mode", "")).strip().lower() == "host":
        issues.append(f"host network is forbidden: {name}")
    if name in {"nuxt", "nginx"} and "network_mode" in service:
        issues.append(f"network_mode is forbidden: {name}")
    if "container_name" in service:
        issues.append(f"container_name is forbidden: {name}")
    if name != "nginx" and service.get("ports"):
        issues.append(f"non-nginx service publishes host ports: {name}")
    environment = _environment(service)
    if FORBIDDEN_ENV_KEYS.intersection(environment):
        issues.append(f"unlock environment is forbidden: {name}")
    if (
        name == "nuxt"
        and str(environment.get("NUXT_PUBLIC_SITE_NOINDEX", "")).lower() == "false"
    ):
        issues.append("unlock environment is forbidden: nuxt")
    return issues


def _production_agent_issues(agent: object) -> list[str]:
    if isinstance(agent, Mapping) and _environment(agent).get("BIND_HOST") != "0.0.0.0":
        return ["agent BIND_HOST must be 0.0.0.0"]
    return []


def _production_bot_issues(bot: object) -> list[str]:
    if not isinstance(bot, Mapping):
        return []
    issues: list[str] = []
    bot_env = _environment(bot)
    if bot_env.get("BIND_HOST") != "0.0.0.0":
        issues.append("bot BIND_HOST must be 0.0.0.0")
    if bot_env.get("AGENT_URL") != "http://agent:8360":
        issues.append("bot AGENT_URL must target agent:8360")
    return issues


def _production_nuxt_issues(services: Mapping[str, Any]) -> list[str]:
    nuxt = services.get("nuxt", {})
    if not isinstance(nuxt, Mapping):
        return []
    nuxt_env = _environment(nuxt)
    issues = _nuxt_runtime_issues(nuxt, nuxt_env)
    build = nuxt.get("build", {})
    build_args = build.get("args", {}) if isinstance(build, Mapping) else {}
    if (
        not isinstance(build_args, Mapping)
        or build_args.get("API_BASE") != EXPECTED_NUXT_API_BASE
    ):
        issues.append("nuxt build API_BASE must target agent:8360")
    if nuxt_env.get("NUXT_API_BASE") != EXPECTED_NUXT_API_BASE:
        issues.append("nuxt runtime NUXT_API_BASE must target agent:8360")
    return issues


def _nuxt_runtime_issues(
    nuxt: Mapping[str, Any], nuxt_env: Mapping[str, str]
) -> list[str]:
    issues: list[str] = []
    if nuxt.get("depends_on", {}):
        issues.append("nuxt must not declare dependencies")
    if "command" in nuxt or "entrypoint" in nuxt:
        issues.append("nuxt command or entrypoint override is forbidden")
    if "env_file" in nuxt:
        issues.append("nuxt env_file is forbidden")
    if not _exposed(nuxt, 3000):
        issues.append("nuxt must expose port 3000")
    if not set(nuxt_env).issubset(NUXT_ALLOWED_ENV_KEYS):
        issues.append("nuxt environment key is forbidden")
    if nuxt_env.get("HOST") != "0.0.0.0" or nuxt_env.get("NITRO_HOST") != "0.0.0.0":
        issues.append("nuxt HOST and NITRO_HOST must be 0.0.0.0")
    return issues


def _volume_at_target(service: object, target: str) -> Mapping[str, Any] | None:
    if not isinstance(service, Mapping):
        return None
    volumes = service.get("volumes", ())
    if not isinstance(volumes, Sequence) or isinstance(volumes, (str, bytes)):
        return None
    matches = [
        volume
        for volume in volumes
        if isinstance(volume, Mapping) and volume.get("target") == target
    ]
    return matches[0] if len(matches) == 1 else None


def _maintenance_command_is_exact(initializer: Mapping[str, Any]) -> bool:
    command = initializer.get("command", ())
    if (
        not isinstance(command, Sequence)
        or isinstance(command, (str, bytes))
        or not all(isinstance(item, str) for item in command)
    ):
        return False
    return tuple(command) == EXPECTED_MAINTENANCE_INIT_COMMAND


def _maintenance_source_is_exact(
    volume: Mapping[str, Any] | None, *, compose_root: Path | None
) -> bool:
    if (
        volume is None
        or volume.get("type") != "bind"
        or volume.get("read_only") is not True
    ):
        return False
    source = volume.get("source")
    if not isinstance(source, str):
        return False
    normalized = source.replace("\\", "/").rstrip("/")
    relative_source = MAINTENANCE_SOURCE_SUFFIX.removeprefix("/")
    if normalized == relative_source:
        return True
    if compose_root is None:
        return False
    expected = str(compose_root / relative_source).replace("\\", "/").rstrip("/")
    return normalized.casefold() == expected.casefold()


def _canonical_writable_bind(volume: Mapping[str, Any] | None) -> bool:
    return (
        volume is not None
        and volume.get("type") == "bind"
        and volume.get("source") == MAINTENANCE_RUNTIME_TARGET
        and volume.get("read_only") is not True
    )


def _maintenance_runtime_mount_issues(
    initialized_runtime: Mapping[str, Any] | None,
    nginx_runtime: Mapping[str, Any] | None,
) -> list[str]:
    issues: list[str] = []
    if not _canonical_writable_bind(initialized_runtime):
        issues.append(
            "maintenance runtime initializer must use the writable host bind authority"
        )
    if not _canonical_writable_bind(nginx_runtime):
        issues.append("maintenance runtime nginx must use the writable host bind authority")
    if (
        initialized_runtime is not None
        and nginx_runtime is not None
        and initialized_runtime.get("source") != nginx_runtime.get("source")
    ):
        issues.append("maintenance runtime host bind must be shared with nginx")
    return issues


def _initializer_volume_targets_are_exact(initializer: Mapping[str, Any]) -> bool:
    volumes = initializer.get("volumes", ())
    if not isinstance(volumes, Sequence) or isinstance(volumes, (str, bytes)):
        return False
    targets = [
        volume.get("target")
        for volume in volumes
        if isinstance(volume, Mapping)
    ]
    return len(volumes) == 2 and set(targets) == {
        MAINTENANCE_SOURCE_TARGET,
        MAINTENANCE_RUNTIME_TARGET,
    }


def _production_maintenance_issues(
    services: Mapping[str, Any], *, compose_root: Path | None
) -> list[str]:
    initializer = services.get("maintenance-runtime-init")
    nginx = services.get("nginx")
    if not isinstance(initializer, Mapping):
        return ["maintenance runtime initializer is missing"]

    issues: list[str] = []
    source = _volume_at_target(initializer, MAINTENANCE_SOURCE_TARGET)
    initialized_runtime = _volume_at_target(initializer, MAINTENANCE_RUNTIME_TARGET)
    nginx_runtime = _volume_at_target(nginx, MAINTENANCE_RUNTIME_TARGET)
    if not _maintenance_source_is_exact(source, compose_root=compose_root):
        issues.append("maintenance runtime source must be the reviewed read-only bind")
    issues.extend(_maintenance_runtime_mount_issues(initialized_runtime, nginx_runtime))
    if (
        initializer.get("restart") != "no"
        or not _initializer_volume_targets_are_exact(initializer)
        or not _maintenance_command_is_exact(initializer)
    ):
        issues.append("maintenance runtime initializer contract must be exact")
    if not isinstance(nginx, Mapping) or not _nginx_dependencies_are_exact(
        nginx.get("depends_on", {})
    ):
        issues.append("maintenance runtime initialization must complete before nginx")
    return issues


def _production_healthcheck_issues(services: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for service_name, expected_command in EXPECTED_HEALTHCHECKS.items():
        service = services.get(service_name, {})
        command = _healthcheck_command(service) if isinstance(service, Mapping) else None
        if command != expected_command:
            issues.append(f"{service_name} healthcheck command mismatch")

    return issues


def _production_nginx_issues(services: Mapping[str, Any]) -> list[str]:
    nginx = services.get("nginx", {})
    if isinstance(nginx, Mapping) and not _nginx_dependencies_are_exact(
        nginx.get("depends_on", {})
    ):
        return [
            "nginx must depend on healthy nuxt and completed maintenance initialization"
        ]
    return []


def _nginx_dependencies_are_exact(depends_on: object) -> bool:
    if not isinstance(depends_on, Mapping):
        return False
    if set(depends_on) != {"maintenance-runtime-init", "nuxt"}:
        return False
    return _dependency_is_exact(
        depends_on.get("nuxt", {}), "service_healthy"
    ) and _dependency_is_exact(
        depends_on.get("maintenance-runtime-init", {}),
        "service_completed_successfully",
    )


def _dependency_is_exact(dependency: object, condition: str) -> bool:
    return (
        isinstance(dependency, Mapping)
        and dependency.get("condition") == condition
        and set(dependency).issubset({"condition", "required", "restart"})
        and dependency.get("required", True) is True
        and dependency.get("restart", False) is False
    )


def _network_definition_issues(model: Mapping[str, Any], label: str) -> list[str]:
    issues: list[str] = []
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return [f"{label} services must be an object"]
    for name, service in services.items():
        if not isinstance(service, Mapping):
            issues.append(f"{label} service is not an object: {name}")
            continue
        if str(service.get("network_mode", "")).strip().lower() == "host":
            issues.append(f"{label} host network is forbidden: {name}")
        if "container_name" in service:
            issues.append(f"{label} container_name is forbidden: {name}")
    networks = model.get("networks", {})
    if isinstance(networks, Mapping):
        for name, network in networks.items():
            if isinstance(network, Mapping) and network.get("external") is True:
                issues.append(f"{label} external network is forbidden: {name}")
    return issues


def validate_developer_model(model: Mapping[str, Any]) -> list[str]:
    issues = _network_definition_issues(model, "developer")
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return sorted(set(issues))
    if set(services) != REQUIRED_SERVICES:
        issues.append("developer services must match the production service set")
    if not _nginx_endpoints_are_exact(model):
        issues.append("developer nginx endpoint topology mismatch")
    endpoints = published_endpoints(model)
    non_nginx = {
        _endpoint_identity(endpoint)
        for endpoint in endpoints
        if endpoint["service"] != "nginx"
    }
    expected_count = len(EXPECTED_DEVELOPER_ENDPOINTS) + 2
    if (
        non_nginx != EXPECTED_DEVELOPER_ENDPOINTS
        or _published_port_entry_count(model) != expected_count
        or len(endpoints) != expected_count
    ):
        issues.append("developer endpoint topology mismatch")
    return sorted(set(issues))


def validate_systemd_dependency_model(model: Mapping[str, Any]) -> list[str]:
    issues = _network_definition_issues(model, "systemd dependency")
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return sorted(set(issues))
    if set(services) != {"postgres", "redis"}:
        issues.append("systemd dependency services must be exactly postgres and redis")
    postgres = services.get("postgres", {})
    postgres_environment = _environment(postgres) if isinstance(postgres, Mapping) else {}
    password = postgres_environment.get("POSTGRES_PASSWORD")
    if (
        not isinstance(password, str)
        or not password.strip()
        or password == "vl360_dev_password"
        or ":-vl360_dev_password" in password
    ):
        issues.append("systemd dependency database password must be explicit")
    parsed_endpoints = published_endpoints(model)
    endpoints = {_endpoint_identity(endpoint) for endpoint in parsed_endpoints}
    if (
        endpoints != EXPECTED_SYSTEMD_ENDPOINTS
        or _published_port_entry_count(model) != len(EXPECTED_SYSTEMD_ENDPOINTS)
        or len(parsed_endpoints) != len(EXPECTED_SYSTEMD_ENDPOINTS)
    ):
        issues.append("systemd dependency endpoint topology mismatch")
    return sorted(set(issues))


def _repo_relative(root: Path, path: Path) -> str:
    root = Path(os.path.abspath(root))
    path = Path(os.path.abspath(path))
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"source path is outside repository root: {path}") from exc


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(metadata, "st_file_attributes", 0) & attribute)


def _assert_no_symlink_components(
    root: Path,
    path: Path,
    *,
    label: str,
    allow_missing: bool,
) -> None:
    root = Path(os.path.abspath(root))
    path = Path(os.path.abspath(path))
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if not os.path.lexists(current):
            if allow_missing:
                break
            raise ValueError(f"{label} is missing")
        metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse_point(metadata):
            raise ValueError(f"{label} symlink is forbidden")


def _resolve_output_path(root: Path, path: Path) -> Path:
    root = Path(os.path.abspath(root))
    resolved = Path(os.path.abspath(path if path.is_absolute() else root / path))
    _repo_relative(root, resolved)
    _assert_no_symlink_components(
        root, resolved.parent, label="output path", allow_missing=True
    )
    return resolved


def _normalized_source_bytes(raw: bytes) -> bytes:
    text = raw.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def source_sha256(path: Path) -> str:
    return hashlib.sha256(_normalized_source_bytes(path.read_bytes())).hexdigest()


def _source_state(path: Path) -> tuple[int, int, int, int]:
    metadata = path.stat()
    return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns


def capture_source_snapshots(
    root: Path, source_files: Sequence[Path]
) -> tuple[SourceSnapshot, ...]:
    root = Path(os.path.abspath(root))
    snapshots: list[SourceSnapshot] = []
    for path in source_files:
        resolved = _resolve_repo_source(root, path)
        before = _source_state(resolved)
        raw = resolved.read_bytes()
        after = _source_state(resolved)
        if before != after or len(raw) != before[2]:
            raise RuntimeError(f"source changed while snapshotting: {_repo_relative(root, resolved)}")
        snapshots.append(
            SourceSnapshot(
                relative_path=_repo_relative(root, resolved),
                normalized_sha256=hashlib.sha256(
                    _normalized_source_bytes(raw)
                ).hexdigest(),
                raw_content=raw,
            )
        )
    return tuple(snapshots)


@contextmanager
def materialize_source_snapshots(
    snapshots: Sequence[SourceSnapshot],
):
    if len(snapshots) != len(SNAPSHOT_FILE_NAMES):
        raise ValueError("compose source snapshot set is incomplete")
    temporary = tempfile.TemporaryDirectory(prefix="vl360-compose-audit-")
    root = Path(temporary.name)
    try:
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
        paths: list[Path] = []
        for filename, snapshot in zip(SNAPSHOT_FILE_NAMES, snapshots):
            path = root / filename
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                0o600,
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    descriptor = -1
                    stream.write(snapshot.raw_content)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                if descriptor != -1:
                    os.close(descriptor)
            try:
                os.chmod(path, 0o400)
            except OSError:
                pass
            paths.append(path)
        yield SnapshotRenderInputs(root, *paths)
    finally:
        temporary.cleanup()


def build_audit_artifact(
    root: Path,
    rendered_model: Mapping[str, Any],
    *,
    developer_model: Mapping[str, Any],
    systemd_model: Mapping[str, Any],
    source_files: Sequence[Path] | None = None,
    source_snapshots: Sequence[SourceSnapshot] | None = None,
    compose_root: Path | None = None,
) -> dict[str, Any]:
    """Build the canonical, model-free audit evidence document."""

    issues = validate_production_model(rendered_model, compose_root=compose_root)
    issues.extend(validate_developer_model(developer_model))
    issues.extend(validate_systemd_dependency_model(systemd_model))
    if issues:
        raise ValueError("production Compose audit failed: " + "; ".join(issues))
    if source_files is not None and source_snapshots is not None:
        raise ValueError("source files and source snapshots are mutually exclusive")
    files = source_files if source_files is not None else (
        root / "docker-compose.yml",
        root / "docker-compose.prod.yml",
        root / "docker-compose.dev.yml",
        root / "docker-compose.systemd-deps.yml",
    )
    snapshots = (
        tuple(source_snapshots)
        if source_snapshots is not None
        else capture_source_snapshots(root, files)
    )
    sources = [
        {
            "path": snapshot.relative_path,
            "sha256": snapshot.normalized_sha256,
        }
        for snapshot in sorted(snapshots, key=lambda item: item.relative_path)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": AUDIT_REVISION,
        "check_names": sorted(CHECK_NAMES),
        "checks": {name: "passed" for name in sorted(CHECK_NAMES)},
        "published_ports": sorted(
            published_endpoints(rendered_model),
            key=lambda endpoint: (
                str(endpoint["service"]),
                int(endpoint["published"]),
                int(endpoint["target"]),
                str(endpoint["host_ip"]),
                str(endpoint["protocol"]),
            ),
        ),
        "source_digest_kind": SOURCE_DIGEST_KIND,
        "sources": sources,
    }


def write_audit_artifact(
    path: Path,
    artifact: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> Path:
    """Publish canonical bytes atomically without replacing an existing file."""

    if root is not None:
        path = _resolve_output_path(root, path)
    if path.exists() or os.path.lexists(path):
        raise FileExistsError(f"audit artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if root is not None:
        _assert_no_symlink_components(
            root, path.parent, label="output path", allow_missing=False
        )
    pending = path.with_name(f".{path.name}.pending-{secrets.token_hex(12)}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    payload = canonical_json_bytes(artifact)
    descriptor = os.open(pending, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            if root is not None:
                _assert_no_symlink_components(
                    root, path.parent, label="output path", allow_missing=False
                )
            os.link(pending, path, follow_symlinks=False)
        except FileExistsError:
            raise
    finally:
        if descriptor != -1:
            os.close(descriptor)
        try:
            pending.unlink()
        except FileNotFoundError:
            pass
    return path


def _resolve_repo_source(root: Path, path: Path) -> Path:
    root = Path(os.path.abspath(root))
    resolved = Path(os.path.abspath(path if path.is_absolute() else root / path))
    _repo_relative(root, resolved)
    _assert_no_symlink_components(
        root, resolved, label="source", allow_missing=False
    )
    metadata = os.lstat(resolved)
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("source must be a regular file")
    return resolved


def _resolve_compose_source(project_root: Path, path: Path) -> Path:
    """Resolve a repository source or an immutable external snapshot file."""

    project_root = Path(os.path.abspath(project_root))
    resolved = Path(os.path.abspath(path if path.is_absolute() else project_root / path))
    try:
        resolved.relative_to(project_root)
    except ValueError:
        # Snapshot files deliberately live outside the project root.  Keep the
        # check narrow so arbitrary external Compose files cannot be rendered.
        if resolved.name not in SNAPSHOT_FILE_NAMES:
            raise ValueError("snapshot compose filename is invalid")
        parent_metadata = os.lstat(resolved.parent)
        metadata = os.lstat(resolved)
        if (
            stat.S_ISLNK(parent_metadata.st_mode)
            or _is_reparse_point(parent_metadata)
            or stat.S_ISLNK(metadata.st_mode)
            or _is_reparse_point(metadata)
        ):
            raise ValueError("snapshot compose symlink is forbidden")
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("snapshot compose source must be a regular file")
        return resolved
    return _resolve_repo_source(project_root, resolved)


def render_production_compose(
    root: Path,
    compose: Path | None = None,
    production: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    compose = _resolve_compose_source(root, compose or Path("docker-compose.yml"))
    production = _resolve_compose_source(
        root, production or Path("docker-compose.prod.yml")
    )
    return _render_compose(root, (compose, production))


def render_developer_compose(
    root: Path,
    compose: Path,
    developer: Path,
) -> dict[str, Any]:
    root = root.resolve()
    compose = _resolve_compose_source(root, compose)
    developer = _resolve_compose_source(root, developer)
    return _render_compose(root, (compose, developer))


def render_systemd_dependency_compose(root: Path, systemd: Path) -> dict[str, Any]:
    root = root.resolve()
    systemd = _resolve_compose_source(root, systemd)
    return _render_compose(root, (systemd,))


def _render_compose(root: Path, sources: Sequence[Path]) -> dict[str, Any]:
    root = root.resolve()
    resolved_sources = tuple(_resolve_compose_source(root, source) for source in sources)
    snapshot_parents = {
        source.parent
        for source in resolved_sources
        if not source.is_relative_to(root)
    }
    if len(snapshot_parents) > 1:
        raise ValueError("snapshot compose sources must share one directory")
    command = ["docker", "compose"]
    command.extend(("--project-directory", str(root)))
    for source in resolved_sources:
        try:
            argument = _repo_relative(root, source)
        except ValueError:
            argument = str(source)
        command.extend(("-f", argument))
    command.extend(("config", "--format", "json", "--no-env-resolution"))
    try:
        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError("Docker Compose CLI is unavailable") from exc
    if result.returncode != 0:
        raise RuntimeError("Docker Compose render failed")
    try:
        model = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("docker compose emitted invalid JSON") from exc
    if not isinstance(model, dict):
        raise RuntimeError("docker compose JSON root must be an object")
    return model


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--compose", type=Path, required=True)
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--developer", type=Path)
    parser.add_argument("--systemd-deps", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        compose = _resolve_repo_source(root, args.compose)
        production = _resolve_repo_source(root, args.production)
        developer = _resolve_repo_source(
            root, args.developer or compose.parent / "docker-compose.dev.yml"
        )
        systemd_deps = _resolve_repo_source(
            root,
            args.systemd_deps or compose.parent / "docker-compose.systemd-deps.yml",
        )
        output = _resolve_output_path(root, args.output)
        source_files = (compose, production, developer, systemd_deps)
        source_snapshots = capture_source_snapshots(root, source_files)
        with materialize_source_snapshots(source_snapshots) as render_inputs:
            model = render_production_compose(
                root,
                render_inputs.compose,
                render_inputs.production,
            )
            developer_model = render_developer_compose(
                root,
                render_inputs.compose,
                render_inputs.developer,
            )
            systemd_model = render_systemd_dependency_compose(
                root,
                render_inputs.systemd,
            )
            artifact = build_audit_artifact(
                root,
                model,
                developer_model=developer_model,
                systemd_model=systemd_model,
                source_snapshots=source_snapshots,
                compose_root=root,
            )
        write_audit_artifact(output, artifact, root=root)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"compose network audit refused: {exc}", file=sys.stderr)
        return 2
    print(canonical_json_bytes(artifact).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
