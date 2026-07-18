from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
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


def _expected_closed_model() -> dict[str, object]:
    return {
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
    actual = {
        line.strip().strip('- ').strip('"')
        for line in compose.splitlines()
        if "127.0.0.1:" in line
    }
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
    assert '"127.0.0.1:5432:5432"' in compose
    assert '"127.0.0.1:6379:6379"' in compose
    assert "0.0.0.0:" not in compose


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
        "exact_healthcheck_commands",
        "nginx_depends_on_healthy_nuxt_only",
        "nginx_exclusive_public_endpoints",
        "no_external_or_host_network",
        "no_launch_unlock_environment",
        "non_nginx_services_unpublished",
        "nuxt_backend_independent_readiness",
        "nuxt_bind_host",
        "required_services_present",
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


def test_audit_artifact_refuses_overwrite_and_leaves_no_pending_file(tmp_path: Path):
    audit = _load_audit()
    output = tmp_path / "compose-network-audit.json"
    artifact = audit.build_audit_artifact(ROOT, _expected_closed_model(), source_files=[])
    audit.write_audit_artifact(output, artifact)
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        audit.write_audit_artifact(output, {**artifact, "revision": "mutated"})
    assert output.read_bytes() == original
    assert list(tmp_path.glob(".*pending*")) == []


def test_cli_render_uses_no_env_resolution(monkeypatch):
    audit = _load_audit()
    calls: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = json.dumps(_expected_closed_model())
        stderr = ""

    def run(command, **kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr(audit.subprocess, "run", run)
    rendered = audit.render_production_compose(
        ROOT,
        ROOT / "docker-compose.yml",
        ROOT / "docker-compose.prod.yml",
    )
    assert rendered["services"]["nginx"]
    assert calls == [[
        "docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.prod.yml",
        "config", "--format", "json", "--no-env-resolution",
    ]]


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

    def render(root, compose, production):
        calls.append((root, compose, production))
        return _expected_closed_model()

    monkeypatch.setattr(audit, "render_production_compose", render)
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
    assert calls == [
        (
            tmp_path.resolve(),
            (tmp_path / "docker-compose.yml").resolve(),
            (tmp_path / "docker-compose.prod.yml").resolve(),
        )
    ]
    artifact = json.loads(
        (tmp_path / "build" / "compose-network-audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert [source["path"] for source in artifact["sources"]] == [
        "docker-compose.dev.yml",
        "docker-compose.prod.yml",
        "docker-compose.systemd-deps.yml",
        "docker-compose.yml",
    ]
