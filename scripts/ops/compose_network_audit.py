"""Audit the rendered production Compose listener boundary.

The validator intentionally accepts the JSON model emitted by Docker Compose,
so unit tests do not need Docker or a YAML parser.  The command-line entrypoint
is the only code that shells out to Compose.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1
AUDIT_REVISION = "compose-network-audit-v1"
CHECK_NAMES = (
    "agent_bind_host",
    "bot_bind_host_and_agent_url",
    "container_names_absent",
    "exact_healthcheck_commands",
    "non_nginx_services_unpublished",
    "no_external_or_host_network",
    "nginx_exclusive_public_endpoints",
    "nginx_depends_on_healthy_nuxt_only",
    "nuxt_backend_independent_readiness",
    "nuxt_bind_host",
    "no_launch_unlock_environment",
    "required_services_present",
)
INTERNAL_SERVICES = {
    "postgres",
    "redis",
    "agent",
    "bot-gateway",
    "nuxt",
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


def _exposed(service: Mapping[str, Any], port: int) -> bool:
    exposed = service.get("expose", ())
    if not isinstance(exposed, Sequence) or isinstance(exposed, (str, bytes)):
        return False
    return any(str(item).split("/")[0] == str(port) for item in exposed)


def _healthcheck_command(service: Mapping[str, Any]) -> tuple[str, ...] | None:
    healthcheck = service.get("healthcheck", {})
    if not isinstance(healthcheck, Mapping):
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
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return False
    nginx = services.get("nginx", {})
    if not isinstance(nginx, Mapping):
        return False
    ports = nginx.get("ports", ())
    if (
        not isinstance(ports, Sequence)
        or isinstance(ports, (str, bytes))
        or len(ports) != 2
    ):
        return False
    endpoints = [_port_endpoint("nginx", port) for port in ports]
    if any(endpoint is None for endpoint in endpoints):
        return False
    valid_endpoints = [endpoint for endpoint in endpoints if endpoint is not None]
    for endpoint in valid_endpoints:
        host_ip = ipaddress.ip_address(str(endpoint["host_ip"]))
        if host_ip.is_loopback or endpoint["protocol"] != "tcp":
            return False
    return {
        (int(endpoint["published"]), int(endpoint["target"]))
        for endpoint in valid_endpoints
    } == {(80, 80), (443, 443)}


def validate_production_model(model: Mapping[str, Any]) -> list[str]:
    """Return stable issue strings for a rendered production Compose model."""

    issues: list[str] = []
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return ["services must be an object"]
    for missing in sorted(REQUIRED_SERVICES.difference(services)):
        issues.append(f"required service is missing: {missing}")

    if not _nginx_endpoints_are_exact(model):
        issues.append("nginx exclusive public endpoints violated")

    networks = model.get("networks", {})
    if isinstance(networks, Mapping):
        for name, network in networks.items():
            if isinstance(network, Mapping) and network.get("external") is True:
                issues.append(f"external network is forbidden: {name}")

    for name, service in services.items():
        if not isinstance(service, Mapping):
            issues.append(f"service is not an object: {name}")
            continue
        if str(service.get("network_mode", "")).strip().lower() == "host":
            issues.append(f"host network is forbidden: {name}")
        if "container_name" in service:
            issues.append(f"container_name is forbidden: {name}")
        if name != "nginx" and service.get("ports"):
            issues.append(f"non-nginx service publishes host ports: {name}")
        environment = _environment(service)
        if FORBIDDEN_ENV_KEYS.intersection(environment):
            issues.append(f"unlock environment is forbidden: {name}")
        if name == "nuxt" and str(environment.get("NUXT_PUBLIC_SITE_NOINDEX", "")).lower() == "false":
            issues.append("unlock environment is forbidden: nuxt")

    agent = services.get("agent", {})
    if isinstance(agent, Mapping) and _environment(agent).get("BIND_HOST") != "0.0.0.0":
        issues.append("agent BIND_HOST must be 0.0.0.0")

    bot = services.get("bot-gateway", {})
    if isinstance(bot, Mapping):
        bot_env = _environment(bot)
        if bot_env.get("BIND_HOST") != "0.0.0.0":
            issues.append("bot BIND_HOST must be 0.0.0.0")
        if bot_env.get("AGENT_URL") != "http://agent:8360":
            issues.append("bot AGENT_URL must target agent:8360")

    nuxt = services.get("nuxt", {})
    if isinstance(nuxt, Mapping):
        depends_on = nuxt.get("depends_on", {})
        if isinstance(depends_on, Mapping) and "agent" in depends_on:
            issues.append("nuxt must not depend on agent")
        elif isinstance(depends_on, Sequence) and "agent" in depends_on:
            issues.append("nuxt must not depend on agent")
        if not _exposed(nuxt, 3000):
            issues.append("nuxt must expose port 3000")
        nuxt_env = _environment(nuxt)
        if nuxt_env.get("HOST") != "0.0.0.0" or nuxt_env.get("NITRO_HOST") != "0.0.0.0":
            issues.append("nuxt HOST and NITRO_HOST must be 0.0.0.0")

    for service_name, expected_command in EXPECTED_HEALTHCHECKS.items():
        service = services.get(service_name, {})
        command = _healthcheck_command(service) if isinstance(service, Mapping) else None
        if command != expected_command:
            issues.append(f"{service_name} healthcheck command mismatch")

    nginx = services.get("nginx", {})
    if isinstance(nginx, Mapping):
        depends_on = nginx.get("depends_on", {})
        nuxt_dependency = (
            depends_on.get("nuxt", {}) if isinstance(depends_on, Mapping) else {}
        )
        if (
            not isinstance(depends_on, Mapping)
            or set(depends_on) != {"nuxt"}
            or not isinstance(nuxt_dependency, Mapping)
            or nuxt_dependency.get("condition") != "service_healthy"
        ):
            issues.append("nginx must depend on healthy nuxt only")

    return sorted(set(issues))


def _repo_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"source path is outside repository root: {path}") from exc


def source_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_audit_artifact(
    root: Path,
    rendered_model: Mapping[str, Any],
    *,
    source_files: Sequence[Path] | None = None,
) -> dict[str, Any]:
    """Build the canonical, model-free audit evidence document."""

    issues = validate_production_model(rendered_model)
    if issues:
        raise ValueError("production Compose audit failed: " + "; ".join(issues))
    files = source_files if source_files is not None else (
        root / "docker-compose.yml",
        root / "docker-compose.prod.yml",
    )
    sources = [
        {
            "path": _repo_relative(root, path),
            "sha256": source_sha256(path),
        }
        for path in sorted(files, key=lambda item: _repo_relative(root, item))
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


def write_audit_artifact(path: Path, artifact: Mapping[str, Any]) -> Path:
    """Publish canonical bytes atomically without replacing an existing file."""

    if path.exists() or os.path.lexists(path):
        raise FileExistsError(f"audit artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
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
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    _repo_relative(root, resolved)
    return resolved


def render_production_compose(
    root: Path,
    compose: Path | None = None,
    production: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    compose = _resolve_repo_source(root, compose or Path("docker-compose.yml"))
    production = _resolve_repo_source(
        root, production or Path("docker-compose.prod.yml")
    )
    command = [
        "docker",
        "compose",
        "-f",
        _repo_relative(root, compose),
        "-f",
        _repo_relative(root, production),
        "config",
        "--format",
        "json",
        "--no-env-resolution",
    ]
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
        detail = result.stderr.strip() or "docker compose config failed"
        raise RuntimeError(detail)
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
        output = args.output if args.output.is_absolute() else root / args.output
        model = render_production_compose(root, compose, production)
        artifact = build_audit_artifact(
            root,
            model,
            source_files=(compose, production, developer, systemd_deps),
        )
        write_audit_artifact(output, artifact)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"compose network audit refused: {exc}", file=sys.stderr)
        return 2
    print(canonical_json_bytes(artifact).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
