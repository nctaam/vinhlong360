from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ops" / "compose_network_audit.py"


def _load_audit():
    spec = importlib.util.spec_from_file_location("compose_network_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _service_block(source: str, service: str, next_service: str | None = None) -> str:
    marker = f"\n  {service}:\n"
    block = source.split(marker, 1)[1]
    if next_service:
        block = block.split(f"\n  {next_service}:\n", 1)[0]
    return block


def _source_healthcheck_command(service_block: str) -> list[str]:
    line = next(
        line.strip()
        for line in service_block.splitlines()
        if line.strip().startswith("test: [")
    )
    return json.loads(line.removeprefix("test:").strip())


def _source_port_entries(service_block: str) -> list[str]:
    ports = service_block.split("    ports:\n", 1)[1]
    entries: list[str] = []
    for line in ports.splitlines():
        if not line.startswith("      - "):
            break
        entries.append(json.loads(line.removeprefix("      - ")))
    return entries


def _expected_closed_model() -> dict[str, object]:
    model = {
        "services": {
            "postgres": {"expose": ["5432"]},
            "redis": {"expose": ["6379"]},
            "agent": {
                "expose": ["8360"],
                "environment": {"BIND_HOST": "0.0.0.0"},
                "healthcheck": {
                    "test": [
                        "CMD",
                        "curl",
                        "-f",
                        "http://127.0.0.1:8360/health",
                    ]
                },
            },
            "bot-gateway": {
                "expose": ["8361"],
                "environment": {
                    "BIND_HOST": "0.0.0.0",
                    "AGENT_URL": "http://agent:8360",
                },
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://127.0.0.1:8361/"]
                },
            },
            "nuxt": {
                "expose": ["3000"],
                "environment": {"HOST": "0.0.0.0", "NITRO_HOST": "0.0.0.0"},
                "healthcheck": {
                    "test": [
                        "CMD-SHELL",
                        "wget -qO- http://127.0.0.1:3000/_internal/launch-readiness >/dev/null",
                    ]
                },
            },
            "nginx": {
                "ports": [
                    {
                        "host_ip": "0.0.0.0",
                        "target": 80,
                        "published": 80,
                        "protocol": "tcp",
                    },
                    {
                        "host_ip": "0.0.0.0",
                        "target": 443,
                        "published": 443,
                        "protocol": "tcp",
                    },
                ],
                "depends_on": {"nuxt": {"condition": "service_healthy"}},
            },
            "prometheus": {"expose": ["9090"]},
            "grafana": {"expose": ["3000"]},
            "loki": {"expose": ["3100"]},
            "promtail": {},
        },
        "networks": {"default": {"external": False}},
    }
    for service in model["services"].values():
        service["networks"] = {"default": None}
    return model


def _published_binding(host_ip: str, published: int, target: int) -> dict[str, object]:
    return {
        "host_ip": host_ip,
        "published": published,
        "target": target,
        "protocol": "tcp",
    }


def _expected_developer_model() -> dict[str, object]:
    model = copy.deepcopy(_expected_closed_model())
    for service, published, target in (
        ("postgres", 5432, 5432),
        ("redis", 6379, 6379),
        ("agent", 8360, 8360),
        ("bot-gateway", 8361, 8361),
        ("nuxt", 3000, 3000),
        ("prometheus", 9090, 9090),
        ("grafana", 3001, 3000),
        ("loki", 3100, 3100),
    ):
        model["services"][service]["ports"] = [
            _published_binding("127.0.0.1", published, target)
        ]
    return model


def _expected_systemd_model() -> dict[str, object]:
    return {
        "services": {
            "postgres": {
                "ports": [_published_binding("127.0.0.1", 5432, 5432)],
                "environment": {"POSTGRES_PASSWORD": "not-default-test-secret"},
            },
            "redis": {
                "ports": [_published_binding("127.0.0.1", 6379, 6379)]
            },
        },
        "networks": {"default": {"external": False}},
    }


def test_production_compose_source_removes_non_nginx_host_publications():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "container_name:" not in compose
    for service, next_service in (
        ("postgres", "redis"),
        ("redis", "agent"),
        ("agent", "bot-gateway"),
        ("bot-gateway", "nuxt"),
        ("nuxt", "nginx"),
        ("prometheus", "grafana"),
        ("grafana", "loki"),
        ("loki", "promtail"),
    ):
        assert "\n    ports:" not in _service_block(compose, service, next_service)
    nginx = _service_block(compose, "nginx", "prometheus")
    assert '"80:80"' in nginx
    assert '"443:443"' in nginx


def test_nuxt_and_nginx_compose_dependencies_are_backend_independent():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nuxt = _service_block(compose, "nuxt", "nginx")
    nginx = _service_block(compose, "nginx", "prometheus")
    assert "depends_on:\n      agent:" not in nuxt
    assert "http://127.0.0.1:3000/_internal/launch-readiness" in nuxt
    assert "HOST: 0.0.0.0" in nuxt
    assert "NITRO_HOST: 0.0.0.0" in nuxt
    assert _source_healthcheck_command(nuxt) == [
        "CMD-SHELL",
        "wget -qO- http://127.0.0.1:3000/_internal/launch-readiness >/dev/null",
    ]
    assert nginx.count("depends_on:") == 1
    assert "nuxt:" in nginx and "condition: service_healthy" in nginx
    assert "agent:" not in nginx


def test_container_bind_hosts_and_internal_agent_url_are_explicit():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    agent = _service_block(compose, "agent", "bot-gateway")
    bot = _service_block(compose, "bot-gateway", "nuxt")
    assert "BIND_HOST: 0.0.0.0" in agent
    assert "BIND_HOST: 0.0.0.0" in bot
    assert "AGENT_URL: http://agent:8360" in bot
    assert _source_healthcheck_command(agent) == [
        "CMD",
        "curl",
        "-f",
        "http://127.0.0.1:8360/health",
    ]
    assert _source_healthcheck_command(bot) == [
        "CMD",
        "curl",
        "-f",
        "http://127.0.0.1:8361/",
    ]
    assert "required: false" in agent
    assert "required: false" in bot


def test_dev_overlay_has_only_explicit_loopback_publications():
    compose = (ROOT / "docker-compose.dev.yml").read_text(encoding="utf-8")
    services = [
        line.strip()[:-1]
        for line in compose.splitlines()
        if line.startswith("  ")
        and not line.startswith("    ")
        and line.rstrip().endswith(":")
    ]
    assert services == [
        "postgres",
        "redis",
        "agent",
        "bot-gateway",
        "nuxt",
        "prometheus",
        "grafana",
        "loki",
    ]
    expected = {
        "127.0.0.1:5432:5432",
        "127.0.0.1:6379:6379",
        "127.0.0.1:8360:8360",
        "127.0.0.1:8361:8361",
        "127.0.0.1:3000:3000",
        "127.0.0.1:9090:9090",
        "127.0.0.1:3001:3000",
        "127.0.0.1:3100:3100",
    }
    actual = set()
    for service, next_service in (
        ("postgres", "redis"),
        ("redis", "agent"),
        ("agent", "bot-gateway"),
        ("bot-gateway", "nuxt"),
        ("nuxt", "prometheus"),
        ("prometheus", "grafana"),
        ("grafana", "loki"),
        ("loki", None),
    ):
        actual.update(_source_port_entries(_service_block(compose, service, next_service)))
    assert actual == expected


def test_systemd_dependency_compose_is_independent_and_loopback_only():
    compose = (ROOT / "docker-compose.systemd-deps.yml").read_text(encoding="utf-8")
    service_section = compose.split("\nvolumes:\n", 1)[0]
    services = [
        line.strip()[:-1]
        for line in service_section.splitlines()
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":")
    ]
    assert services == ["postgres", "redis"]
    assert "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" in compose
    assert "${POSTGRES_PASSWORD:-vl360_dev_password}" not in compose
    assert _source_port_entries(_service_block(compose, "postgres", "redis")) == [
        "127.0.0.1:5432:5432"
    ]
    assert _source_port_entries(_service_block(compose, "redis")) == [
        "127.0.0.1:6379:6379"
    ]


def test_production_validator_accepts_private_model_and_published_ports_are_exact():
    audit = _load_audit()
    model = _expected_closed_model()
    assert audit.validate_production_model(model) == []
    assert audit.published_ports(model) == {("nginx", 80), ("nginx", 443)}


def test_production_validator_accepts_compose_default_dependency_metadata():
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["nginx"]["depends_on"]["nuxt"].update(
        {"required": True, "restart": False}
    )
    assert audit.validate_production_model(model) == []


def test_production_validator_rejects_any_nuxt_dependency():
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["nuxt"]["depends_on"] = {
        "redis": {"condition": "service_healthy"}
    }
    assert any(
        "nuxt must not declare dependencies" in issue
        for issue in audit.validate_production_model(model)
    )


@pytest.mark.parametrize("field", ["command", "entrypoint"])
def test_production_validator_rejects_nuxt_startup_wrappers(field):
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["nuxt"][field] = [
        "sh",
        "-c",
        "until wget http://agent:8360/health; do sleep 1; done; node server.mjs",
    ]
    assert any(
        "nuxt command or entrypoint override is forbidden" in issue
        for issue in audit.validate_production_model(model)
    )


@pytest.mark.parametrize("service", ["nuxt", "nginx"])
def test_production_validator_rejects_any_network_mode_on_launch_services(service):
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"][service]["network_mode"] = "none"
    assert any(
        f"network_mode is forbidden: {service}" in issue
        for issue in audit.validate_production_model(model)
    )


def test_production_validator_requires_shared_private_bridge_network():
    audit = _load_audit()
    model = _expected_closed_model()
    model["networks"]["isolated"] = {"external": False, "driver": "bridge"}
    model["services"]["nginx"]["networks"] = {"isolated": None}
    assert any(
        "launch services must share a private bridge network" in issue
        for issue in audit.validate_production_model(model)
    )


@pytest.mark.parametrize("env_file", [".env", [{"path": ".env", "required": False}]])
def test_production_validator_rejects_nuxt_env_file(env_file):
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["nuxt"]["env_file"] = env_file
    assert any(
        "nuxt env_file is forbidden" in issue
        for issue in audit.validate_production_model(model)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("required", False), ("restart", True), ("unexpected", "value")],
)
def test_production_validator_rejects_noncanonical_nginx_dependency_metadata(
    field, value
):
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["nginx"]["depends_on"]["nuxt"][field] = value
    assert any(
        "nginx must depend on healthy nuxt only" in issue
        for issue in audit.validate_production_model(model)
    )


def test_production_validator_rejects_a_missing_required_service():
    audit = _load_audit()
    model = _expected_closed_model()
    del model["services"]["redis"]
    assert any(
        "required service is missing: redis" in issue
        for issue in audit.validate_production_model(model)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("host_ip", "127.0.0.1"),
        ("target", 8080),
        ("protocol", "udp"),
        ("published", "80-81"),
    ],
)
def test_production_validator_rejects_invalid_nginx_endpoint(field, value):
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["nginx"]["ports"][0][field] = value
    assert any(
        "nginx exclusive public endpoints" in issue
        for issue in audit.validate_production_model(model)
    )


def test_production_validator_rejects_fixed_container_names():
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["redis"]["container_name"] = "fixed-redis"
    assert any(
        "container_name is forbidden: redis" in issue
        for issue in audit.validate_production_model(model)
    )


def test_production_validator_rejects_unknown_service_publication():
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["rogue"] = {
        "ports": [
            {
                "host_ip": "0.0.0.0",
                "target": 9999,
                "published": 9999,
                "protocol": "tcp",
            }
        ]
    }
    assert any(
        "non-nginx service publishes host ports: rogue" in issue
        for issue in audit.validate_production_model(model)
    )


@pytest.mark.parametrize(
    ("service", "command"),
    [
        (
            "agent",
            ["CMD", "curl", "-f", "http://127.0.0.1:8360/health-comment"],
        ),
        (
            "bot-gateway",
            ["CMD", "curl", "-f", "http://127.0.0.1:8361/health"],
        ),
        (
            "nuxt",
            [
                "CMD-SHELL",
                "printf 'http://127.0.0.1:3000/_internal/launch-readiness' >/dev/null",
            ],
        ),
    ],
)
def test_production_validator_rejects_noncanonical_health_commands(service, command):
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"][service]["healthcheck"]["test"] = command
    assert any(
        f"{service} healthcheck command mismatch" in issue
        for issue in audit.validate_production_model(model)
    )


def test_production_validator_rejects_disabled_healthcheck_with_matching_command():
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["nuxt"]["healthcheck"]["disable"] = True
    assert any(
        "nuxt healthcheck command mismatch" in issue
        for issue in audit.validate_production_model(model)
    )


def test_production_validator_rejects_host_network_and_unlock_environment():
    audit = _load_audit()
    model = _expected_closed_model()
    model["services"]["agent"]["network_mode"] = "host"
    model["services"]["nuxt"]["environment"]["LAUNCH_INDEXING_MODE"] = "selective-open"
    model["services"]["nuxt"]["environment"]["NUXT_PUBLIC_SITE_NOINDEX"] = "false"
    model["networks"]["public"] = {"external": True}
    issues = audit.validate_production_model(model)
    assert any("host network" in issue for issue in issues)
    assert any("unlock" in issue for issue in issues)
    assert any("external network" in issue for issue in issues)


def test_developer_validator_accepts_only_exact_loopback_publications():
    audit = _load_audit()
    model = _expected_developer_model()
    assert audit.validate_developer_model(model) == []
    model["services"]["agent"]["ports"][0]["host_ip"] = "0.0.0.0"
    assert any(
        "developer endpoint topology mismatch" in issue
        for issue in audit.validate_developer_model(model)
    )
    model = _expected_developer_model()
    model["services"]["rogue"] = {}
    assert any(
        "developer services must match the production service set" in issue
        for issue in audit.validate_developer_model(model)
    )
    model = _expected_developer_model()
    model["services"]["agent"]["ports"].append(
        {
            "host_ip": "127.0.0.1",
            "published": "9999-10000",
            "target": 9999,
            "protocol": "tcp",
        }
    )
    assert any(
        "developer endpoint topology mismatch" in issue
        for issue in audit.validate_developer_model(model)
    )


def test_systemd_validator_requires_exact_dependency_topology():
    audit = _load_audit()
    model = _expected_systemd_model()
    assert audit.validate_systemd_dependency_model(model) == []
    model["services"]["agent"] = {}
    assert any(
        "systemd dependency services must be exactly postgres and redis" in issue
        for issue in audit.validate_systemd_dependency_model(model)
    )
    del model["services"]["agent"]
    model["services"]["redis"]["ports"][0]["host_ip"] = "0.0.0.0"
    assert any(
        "systemd dependency endpoint topology mismatch" in issue
        for issue in audit.validate_systemd_dependency_model(model)
    )
    model = _expected_systemd_model()
    model["services"]["postgres"]["ports"].append(
        {
            "host_ip": "127.0.0.1",
            "published": "9999-10000",
            "target": 9999,
            "protocol": "tcp",
        }
    )
    assert any(
        "systemd dependency endpoint topology mismatch" in issue
        for issue in audit.validate_systemd_dependency_model(model)
    )


@pytest.mark.parametrize(
    "password",
    [
        None,
        "",
        "   ",
        "vl360_dev_password",
        "${POSTGRES_PASSWORD:-vl360_dev_password}",
    ],
)
def test_systemd_validator_rejects_missing_or_default_database_password(password):
    audit = _load_audit()
    model = _expected_systemd_model()
    if password is None:
        del model["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"]
    else:
        model["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"] = password
    assert any(
        "systemd dependency database password must be explicit" in issue
        for issue in audit.validate_systemd_dependency_model(model)
    )


def test_bot_root_health_route_exists_without_importing_gateway():
    source = (ROOT / "agent" / "bot_gateway.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    create_app = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "create_bot_app"
    )
    routes = {
        decorator.args[0].value
        for node in ast.walk(create_app)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "bot_app"
        and decorator.func.attr == "get"
        and decorator.args
        and isinstance(decorator.args[0], ast.Constant)
        and isinstance(decorator.args[0].value, str)
    }
    assert "/" in routes


def test_source_sha256_normalizes_checkout_line_endings(tmp_path: Path):
    audit = _load_audit()
    lf = tmp_path / "lf.yml"
    crlf = tmp_path / "crlf.yml"
    lf.write_bytes(b"services:\n  nginx: {}\n")
    crlf.write_bytes(b"services:\r\n  nginx: {}\r\n")
    expected = hashlib.sha256(lf.read_bytes()).hexdigest()
    assert audit.source_sha256(lf) == expected
    assert audit.source_sha256(crlf) == expected


def test_audit_artifact_is_canonical_source_bound_and_has_no_raw_model(tmp_path: Path):
    audit = _load_audit()
    source = ROOT / "docker-compose.yml"
    artifact = audit.build_audit_artifact(
        ROOT,
        _expected_closed_model(),
        developer_model=_expected_developer_model(),
        systemd_model=_expected_systemd_model(),
        source_files=[source],
    )
    assert artifact["schema_version"] == 1
    assert artifact["revision"] == "compose-network-audit-v1"
    assert set(artifact) == {
        "schema_version",
        "revision",
        "check_names",
        "checks",
        "published_ports",
        "source_digest_kind",
        "sources",
    }
    assert artifact["check_names"] == [
        "agent_bind_host",
        "bot_bind_host_and_agent_url",
        "container_names_absent",
        "developer_added_publications_loopback",
        "exact_healthcheck_commands",
        "nginx_depends_on_healthy_nuxt_only",
        "nginx_exclusive_public_endpoints",
        "no_external_or_host_network",
        "no_launch_unlock_environment",
        "non_nginx_services_unpublished",
        "nuxt_backend_independent_readiness",
        "nuxt_bind_host",
        "required_services_present",
        "shared_private_bridge_network",
        "systemd_dependency_topology",
    ]
    assert artifact["checks"] == {name: "passed" for name in artifact["check_names"]}
    assert artifact["source_digest_kind"] == "sha256-utf8-lf-v1"
    assert artifact["published_ports"] == [
        {
            "host_ip": "0.0.0.0",
            "protocol": "tcp",
            "published": 80,
            "service": "nginx",
            "target": 80,
        },
        {
            "host_ip": "0.0.0.0",
            "protocol": "tcp",
            "published": 443,
            "service": "nginx",
            "target": 443,
        },
    ]
    assert artifact["sources"] == [
        {"path": "docker-compose.yml", "sha256": audit.source_sha256(source)}
    ]
    assert "services" not in artifact
    canonical = audit.canonical_json_bytes(artifact)
    assert canonical == audit.canonical_json_bytes(json.loads(canonical))
    assert b"tmp_path" not in canonical
    assert b"not-default-test-secret" not in canonical


def test_audit_artifact_refuses_overwrite_and_leaves_no_pending_file(tmp_path: Path):
    audit = _load_audit()
    output = tmp_path / "compose-network-audit.json"
    artifact = audit.build_audit_artifact(
        ROOT,
        _expected_closed_model(),
        developer_model=_expected_developer_model(),
        systemd_model=_expected_systemd_model(),
        source_files=[],
    )
    audit.write_audit_artifact(output, artifact)
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        audit.write_audit_artifact(output, {**artifact, "revision": "mutated"})
    assert output.read_bytes() == original
    assert list(tmp_path.glob(".*pending*")) == []


def test_cli_render_preserves_project_root_for_snapshot_relative_paths(
    monkeypatch, tmp_path: Path
):
    audit = _load_audit()
    calls: list[tuple[list[str], dict[str, object]]] = []
    project_root = tmp_path / "repo"
    snapshot_root = tmp_path / "snapshots"
    project_root.mkdir()
    snapshot_root.mkdir()
    snapshot_compose = snapshot_root / "docker-compose.yml"
    snapshot_production = snapshot_root / "docker-compose.prod.yml"
    snapshot_compose.write_text("services: {}\n", encoding="utf-8")
    snapshot_production.write_text("services: {}\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = json.dumps(_expected_closed_model())
        stderr = ""

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr(audit.subprocess, "run", run)
    rendered = audit.render_production_compose(
        project_root,
        snapshot_compose,
        snapshot_production,
    )
    assert rendered["services"]["nginx"]
    command, kwargs = calls[0]
    assert command == [
        "docker",
        "compose",
        "--project-directory",
        str(project_root.resolve()),
        "-f",
        str(snapshot_compose.resolve()),
        "-f",
        str(snapshot_production.resolve()),
        "config",
        "--format",
        "json",
        "--no-env-resolution",
    ]
    assert kwargs["cwd"] == project_root.resolve()
    assert "env" not in kwargs
    assert all(
        Path(path).parent == snapshot_root.resolve()
        for path in (command[5], command[7])
    )
    assert str(project_root.resolve()) not in " ".join((command[5], command[7]))


def test_systemd_snapshot_render_inherits_caller_env_without_serializing_password(
    monkeypatch, tmp_path: Path
):
    audit = _load_audit()
    project_root = tmp_path / "repo"
    snapshot_root = tmp_path / "snapshots"
    project_root.mkdir()
    snapshot_root.mkdir()
    systemd = snapshot_root / "docker-compose.systemd-deps.yml"
    systemd.write_text(
        'services:\n  postgres:\n    environment:\n      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"\n',
        encoding="utf-8",
    )
    calls = []

    class Completed:
        returncode = 0
        stdout = json.dumps(_expected_systemd_model())
        stderr = ""

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setenv("POSTGRES_PASSWORD", "caller-secret")
    monkeypatch.setattr(audit.subprocess, "run", run)
    rendered = audit.render_systemd_dependency_compose(project_root, systemd)

    assert rendered["services"]["postgres"]
    command, kwargs = calls[0]
    assert command[:5] == [
        "docker",
        "compose",
        "--project-directory",
        str(project_root.resolve()),
        "-f",
    ]
    assert command[5] == str(systemd.resolve())
    assert kwargs["cwd"] == project_root.resolve()
    assert "env" not in kwargs
    assert "caller-secret" not in command


def test_render_refusal_does_not_forward_docker_stderr(monkeypatch):
    audit = _load_audit()

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "secret=do-not-leak C:/private/repo/.env"

    monkeypatch.setattr(audit.subprocess, "run", lambda *_args, **_kwargs: Completed())
    with pytest.raises(RuntimeError) as refusal:
        audit.render_production_compose(
            ROOT,
            ROOT / "docker-compose.yml",
            ROOT / "docker-compose.prod.yml",
        )
    assert str(refusal.value) == "Docker Compose render failed"
    assert "secret" not in str(refusal.value)
    assert "C:/" not in str(refusal.value)


def test_cli_supports_planned_paths_and_sibling_source_defaults(
    monkeypatch, tmp_path: Path
):
    audit = _load_audit()
    for name in (
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "docker-compose.dev.yml",
        "docker-compose.systemd-deps.yml",
    ):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    calls = []

    def render_production(root, compose, production):
        calls.append(("production", root, compose, production))
        return _expected_closed_model()

    def render_developer(root, compose, developer):
        calls.append(("developer", root, compose, developer))
        return _expected_developer_model()

    def render_systemd(root, systemd):
        calls.append(("systemd", root, systemd))
        return _expected_systemd_model()

    monkeypatch.setattr(audit, "render_production_compose", render_production)
    monkeypatch.setattr(audit, "render_developer_compose", render_developer)
    monkeypatch.setattr(audit, "render_systemd_dependency_compose", render_systemd)
    monkeypatch.chdir(tmp_path)
    result = audit.main(
        [
            "--compose",
            "docker-compose.yml",
            "--production",
            "docker-compose.prod.yml",
            "--output",
            "build/compose-network-audit.json",
        ]
    )
    assert result == 0
    assert [call[0] for call in calls] == ["production", "developer", "systemd"]
    project_root = calls[0][1]
    assert project_root == tmp_path.resolve()
    assert all(call[1] == project_root for call in calls)
    snapshot_paths = [calls[0][2], calls[0][3], calls[1][3], calls[2][2]]
    snapshot_root = snapshot_paths[0].parent
    assert snapshot_root != project_root
    assert all(path.parent == snapshot_root for path in snapshot_paths)
    assert all(path.is_absolute() for path in snapshot_paths)
    assert [call[2].name for call in calls[:2]] == [
        "docker-compose.yml",
        "docker-compose.yml",
    ]
    assert calls[0][3].name == "docker-compose.prod.yml"
    assert calls[1][3].name == "docker-compose.dev.yml"
    assert calls[2][2].name == "docker-compose.systemd-deps.yml"
    assert not snapshot_root.exists()
    artifact = json.loads(
        (tmp_path / "build" / "compose-network-audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert str(snapshot_root) not in json.dumps(artifact)
    assert [source["path"] for source in artifact["sources"]] == [
        "docker-compose.dev.yml",
        "docker-compose.prod.yml",
        "docker-compose.systemd-deps.yml",
        "docker-compose.yml",
    ]


def test_cli_renders_immutable_snapshots_when_live_source_mutates_and_restores(
    monkeypatch, tmp_path: Path
):
    audit = _load_audit()
    for name in (
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "docker-compose.dev.yml",
        "docker-compose.systemd-deps.yml",
    ):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")

    original = (tmp_path / "docker-compose.yml").read_bytes()
    original_state = (tmp_path / "docker-compose.yml").stat()
    captured = []

    def render_production(root, compose, production):
        captured.append((root, compose, compose.read_bytes()))
        live = tmp_path / "docker-compose.yml"
        live.write_bytes(b"# transient live mutation\n")
        live.write_bytes(original)
        os.utime(
            live,
            ns=(original_state.st_atime_ns, original_state.st_mtime_ns),
        )
        return _expected_closed_model()

    monkeypatch.setattr(audit, "render_production_compose", render_production)
    monkeypatch.setattr(
        audit,
        "render_developer_compose",
        lambda *_args: _expected_developer_model(),
    )
    monkeypatch.setattr(
        audit,
        "render_systemd_dependency_compose",
        lambda *_args: _expected_systemd_model(),
    )
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "build" / "compose-network-audit.json"
    result = audit.main(
        [
            "--compose",
            "docker-compose.yml",
            "--production",
            "docker-compose.prod.yml",
            "--output",
            "build/compose-network-audit.json",
        ]
    )
    assert result == 0
    assert output.exists()
    assert captured[0][0] == tmp_path.resolve()
    assert captured[0][1].name == "docker-compose.yml"
    assert captured[0][1].parent != tmp_path.resolve()
    assert captured[0][2] == original
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["sources"][-1]["path"] == "docker-compose.yml"
    expected_sha = hashlib.sha256(original.replace(b"\r\n", b"\n")).hexdigest()
    assert artifact["sources"][-1]["sha256"] == expected_sha


def test_cli_cleans_snapshot_directory_and_hides_path_on_render_failure(
    monkeypatch, capsys, tmp_path: Path
):
    audit = _load_audit()
    for name in (
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "docker-compose.dev.yml",
        "docker-compose.systemd-deps.yml",
    ):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    render_inputs = []

    def render_production(root, compose, production):
        render_inputs.append((root, compose, production))
        raise RuntimeError("Docker Compose render failed")

    monkeypatch.setattr(audit, "render_production_compose", render_production)
    monkeypatch.chdir(tmp_path)
    result = audit.main(
        [
            "--compose",
            "docker-compose.yml",
            "--production",
            "docker-compose.prod.yml",
            "--output",
            "build/compose-network-audit.json",
        ]
    )
    assert result == 2
    assert render_inputs
    project_root, compose, production = render_inputs[0]
    assert project_root == tmp_path.resolve()
    assert compose.parent == production.parent
    assert not compose.parent.exists()
    assert str(compose.parent) not in capsys.readouterr().err


def test_cli_renders_snapshot_when_live_source_replaced_by_symlink_to_same_inode(
    monkeypatch, tmp_path: Path
):
    audit = _load_audit()
    for name in (
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "docker-compose.dev.yml",
        "docker-compose.systemd-deps.yml",
    ):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")

    def render_production(root, compose, production):
        live = tmp_path / "docker-compose.yml"
        actual = live.with_name("actual-compose.yml")
        live.replace(actual)
        try:
            os.symlink(actual, live)
        except OSError as exc:
            actual.replace(live)
            pytest.skip(f"symlink creation unavailable: {exc}")
        assert compose.read_text(encoding="utf-8") == "# docker-compose.yml\n"
        return _expected_closed_model()

    monkeypatch.setattr(audit, "render_production_compose", render_production)
    monkeypatch.setattr(
        audit,
        "render_developer_compose",
        lambda *_args: _expected_developer_model(),
    )
    monkeypatch.setattr(
        audit,
        "render_systemd_dependency_compose",
        lambda *_args: _expected_systemd_model(),
    )
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "build" / "compose-network-audit.json"
    result = audit.main(
        [
            "--compose",
            "docker-compose.yml",
            "--production",
            "docker-compose.prod.yml",
            "--output",
            "build/compose-network-audit.json",
        ]
    )
    assert result == 0
    assert output.exists()


def test_source_snapshot_rejects_symlink_without_changing_artifact_role(tmp_path: Path):
    audit = _load_audit()
    actual = tmp_path / "actual.yml"
    link = tmp_path / "docker-compose.yml"
    actual.write_text("services: {}\n", encoding="utf-8")
    try:
        os.symlink(actual, link)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(ValueError, match="source symlink is forbidden"):
        audit.capture_source_snapshots(tmp_path, [link])


def test_cli_refuses_symlink_output_parent_without_writing_outside(
    monkeypatch, tmp_path: Path
):
    audit = _load_audit()
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    for name in (
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "docker-compose.dev.yml",
        "docker-compose.systemd-deps.yml",
    ):
        (root / name).write_text(f"# {name}\n", encoding="utf-8")
    try:
        os.symlink(outside, root / "build", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation unavailable: {exc}")
    victim = outside / "victim.txt"
    victim.write_text("unchanged\n", encoding="utf-8")
    monkeypatch.setattr(
        audit,
        "render_production_compose",
        lambda *_args: _expected_closed_model(),
    )
    monkeypatch.setattr(
        audit,
        "render_developer_compose",
        lambda *_args: _expected_developer_model(),
    )
    monkeypatch.setattr(
        audit,
        "render_systemd_dependency_compose",
        lambda *_args: _expected_systemd_model(),
    )
    result = audit.main(
        [
            "--root",
            str(root),
            "--compose",
            "docker-compose.yml",
            "--production",
            "docker-compose.prod.yml",
            "--output",
            "build/compose-network-audit.json",
        ]
    )
    assert result == 2
    assert victim.read_text(encoding="utf-8") == "unchanged\n"
    assert not (outside / "compose-network-audit.json").exists()
