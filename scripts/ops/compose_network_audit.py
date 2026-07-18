"""Audit the rendered production Compose listener boundary.

The validator intentionally accepts the JSON model emitted by Docker Compose,
so unit tests do not need Docker or a YAML parser.  The command-line entrypoint
is the only code that shells out to Compose.
"""

from __future__ import annotations

import argparse
import hashlib
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
    "bot_healthcheck",
    "bot_bind_host_and_agent_url",
    "internal_services_unpublished",
    "no_external_or_host_network",
    "nginx_exclusive_public_ports",
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


def canonical_json_bytes(value: object) -> bytes:
    """Return stable UTF-8 JSON bytes with one trailing newline."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _as_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _published_port(port: object) -> int | None:
    if isinstance(port, Mapping):
        return _as_int(port.get("published"))
    if isinstance(port, str):
        parts = port.split(":")
        if len(parts) < 2:
            return None
        return _as_int(parts[-2].split("/")[0])
    return None


def published_ports(model: Mapping[str, Any]) -> set[tuple[str, int]]:
    """Return ``(service, host-port)`` entries from a Compose model."""

    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return set()
    result: set[tuple[str, int]] = set()
    for service_name, service in services.items():
        if not isinstance(service, Mapping):
            continue
        ports = service.get("ports", ())
        if not isinstance(ports, Sequence) or isinstance(ports, (str, bytes)):
            continue
        for port in ports:
            published = _published_port(port)
            if published is not None:
                result.add((str(service_name), published))
    return result


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


def _healthcheck_text(service: Mapping[str, Any]) -> str:
    healthcheck = service.get("healthcheck", {})
    if not isinstance(healthcheck, Mapping):
        return ""
    test = healthcheck.get("test", ())
    if isinstance(test, Sequence) and not isinstance(test, (str, bytes)):
        return " ".join(str(item) for item in test)
    return str(test)


def validate_production_model(model: Mapping[str, Any]) -> list[str]:
    """Return stable issue strings for a rendered production Compose model."""

    issues: list[str] = []
    services = model.get("services", {})
    if not isinstance(services, Mapping):
        return ["services must be an object"]
    for missing in sorted(REQUIRED_SERVICES.difference(services)):
        issues.append(f"required service is missing: {missing}")

    expected_public = {("nginx", 80), ("nginx", 443)}
    actual_public = published_ports(model)
    if actual_public != expected_public:
        issues.append("nginx exclusive public ports violated")

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
        if name in INTERNAL_SERVICES and service.get("ports"):
            issues.append(f"internal service publishes host ports: {name}")
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
        if "http://127.0.0.1:8361/" not in _healthcheck_text(bot):
            issues.append("bot healthcheck must use loopback port 8361")

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
        if "http://127.0.0.1:3000/_internal/launch-readiness" not in _healthcheck_text(nuxt):
            issues.append("nuxt healthcheck must use launch-readiness")

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
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(files, key=lambda item: _repo_relative(root, item))
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": AUDIT_REVISION,
        "check_names": sorted(CHECK_NAMES),
        "checks": {name: "passed" for name in sorted(CHECK_NAMES)},
        "published_ports": [
            {"service": service, "port": port}
            for service, port in sorted(published_ports(rendered_model))
        ],
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


def render_production_compose(root: Path) -> dict[str, Any]:
    command = [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.prod.yml",
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        model = render_production_compose(args.root)
        artifact = build_audit_artifact(args.root, model)
        write_audit_artifact(args.output, artifact)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"compose network audit refused: {exc}", file=sys.stderr)
        return 2
    print(canonical_json_bytes(artifact).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
