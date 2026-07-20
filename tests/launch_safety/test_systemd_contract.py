from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SYSTEMD_ROOT = ROOT / "ops" / "systemd"
PROBE_PATH = ROOT / "scripts" / "ops" / "socket_boundary_probe.py"

EXPECTED_UNITS = {
    "vl-agent.service": {
        "Unit": [
            ("Description", "VinhLong360 Backend (FastAPI)"),
            ("After", "network.target docker.service"),
            ("Wants", "docker.service"),
        ],
        "Service": [
            ("Type", "simple"),
            ("WorkingDirectory", "/opt/vinhlong360"),
            ("EnvironmentFile", "/opt/vinhlong360/.env"),
            (
                "ExecStart",
                "/usr/bin/env BIND_HOST=127.0.0.1 "
                "/opt/vinhlong360/venv/bin/python agent/server.py",
            ),
            ("Restart", "on-failure"),
            ("RestartSec", "5"),
        ],
        "Install": [("WantedBy", "multi-user.target")],
    },
    "vl-nuxt.service": {
        "Unit": [
            ("Description", "VinhLong360 Frontend (Nuxt SSR)"),
            ("After", "network.target"),
        ],
        "Service": [
            ("Type", "simple"),
            ("WorkingDirectory", "/opt/vinhlong360/web-nuxt"),
            ("ExecStart", "/usr/bin/node .output/server/index.mjs"),
            ("Environment", "NUXT_API_BASE=http://127.0.0.1:8360"),
            ("Environment", "HOST=127.0.0.1"),
            ("Environment", "NITRO_HOST=127.0.0.1"),
            ("Environment", "PORT=3000"),
            ("Environment", "NITRO_PORT=3000"),
            ("Restart", "on-failure"),
            ("RestartSec", "5"),
        ],
        "Install": [("WantedBy", "multi-user.target")],
    },
    "vl-bot.service": {
        "Unit": [
            ("Description", "VinhLong360 Bot Gateway"),
            ("After", "network.target vl-agent.service"),
            ("Requires", "vl-agent.service"),
        ],
        "Service": [
            ("Type", "simple"),
            ("WorkingDirectory", "/opt/vinhlong360"),
            ("EnvironmentFile", "/opt/vinhlong360/.env"),
            (
                "ExecStart",
                "/usr/bin/env BIND_HOST=127.0.0.1 "
                "AGENT_URL=http://127.0.0.1:8360 "
                "/opt/vinhlong360/venv/bin/python agent/bot_gateway.py",
            ),
            ("Restart", "on-failure"),
            ("RestartSec", "5"),
        ],
        "Install": [("WantedBy", "multi-user.target")],
    },
    "vl-watchdog.service": {
        "Unit": [
            ("Description", "vinhlong360 watchdog (health + search + nuxt)"),
        ],
        "Service": [
            ("Type", "oneshot"),
            (
                "Environment",
                "VL360_MAINTENANCE_SELECTOR="
                "/etc/nginx/vl360-maintenance/active-server.conf",
            ),
            ("ExecStart", "/bin/bash /opt/vinhlong360/scripts/ops/watchdog.sh"),
        ],
    },
    "vl-watchdog.timer": {
        "Unit": [("Description", "Watchdog moi 5 phut")],
        "Timer": [
            ("OnCalendar", "*:0/5"),
            ("Persistent", "false"),
            ("Unit", "vl-watchdog.service"),
        ],
        "Install": [("WantedBy", "timers.target")],
    },
}

PASSING_SS = """\
LISTEN 0 511 0.0.0.0:80 0.0.0.0:* users:((\"nginx\",pid=120,fd=6),(\"nginx\",pid=119,fd=6))
LISTEN 0 511 [::]:443 [::]:* users:((\"nginx\",pid=120,fd=7))
LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:((\"sshd\",pid=700,fd=3))
LISTEN 0 2048 127.0.0.1:3000 0.0.0.0:* users:((\"node\",pid=210,fd=18))
LISTEN 0 2048 127.0.0.2:8360 0.0.0.0:* users:((\"python\",pid=220,fd=11))
LISTEN 0 2048 [::1]:8361 [::]:* users:((\"python\",pid=230,fd=12))
LISTEN 0 244 127.0.0.1:5432 0.0.0.0:* users:((\"postgres\",pid=240,fd=7))
LISTEN 0 511 127.0.0.1:6379 0.0.0.0:* users:((\"redis-server\",pid=250,fd=6))
"""


def _parse_systemd(source: str) -> dict[str, list[tuple[str, str]]]:
    sections: dict[str, list[tuple[str, str]]] = {}
    active: list[tuple[str, str]] | None = None
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1]
            assert name not in sections, f"duplicate section [{name}]"
            active = []
            sections[name] = active
            continue
        assert active is not None, f"directive outside section: {line}"
        assert "=" in line, f"invalid directive: {line}"
        key, value = line.split("=", 1)
        active.append((key, value))
    return sections


def _effective_process(
    parsed: dict[str, list[tuple[str, str]]],
    environment_file: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    service = parsed["Service"]
    environment: dict[str, str] = {}
    for key, value in service:
        if key == "Environment":
            name, assigned = value.split("=", 1)
            environment[name] = assigned

    # systemd applies EnvironmentFile values after Environment directives.
    environment.update(environment_file)
    exec_values = [value for key, value in service if key == "ExecStart"]
    assert len(exec_values) == 1
    argv = shlex.split(exec_values[0], posix=True)
    if argv and argv[0] == "/usr/bin/env":
        index = 1
        while index < len(argv) and "=" in argv[index]:
            name, assigned = argv[index].split("=", 1)
            environment[name] = assigned
            index += 1
        argv = argv[index:]
    return environment, argv


def _load_probe():
    assert PROBE_PATH.is_file(), "socket boundary probe is not materialized"
    spec = importlib.util.spec_from_file_location("socket_boundary_probe", PROBE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_probe_subprocess(
    tmp_path: Path,
    args: list[str],
    *,
    source: str = "",
    collection_error: bool = False,
) -> subprocess.CompletedProcess[str]:
    runner = tmp_path / "run_socket_probe.py"
    collector_body = (
        'raise OSError("host-specific collection detail")'
        if collection_error
        else f"return {source!r}"
    )
    runner.write_text(
        f"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("socket_boundary_probe", {str(PROBE_PATH)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def collect():
    {collector_body}

raise SystemExit(module.main(sys.argv[1:], collector=collect))
""".lstrip(),
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(runner), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _evidence_temps(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def _module_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _bind_assignment(tree: ast.Module) -> ast.Assign:
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "BIND_HOST" for target in node.targets)
    ]
    assert len(assignments) == 1
    return assignments[0]


def _load_dotenv_line(tree: ast.Module) -> int:
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _call_name(node.func) == "load_dotenv"
    ]
    assert len(calls) == 1
    return calls[0].lineno


def _uvicorn_call(tree: ast.Module) -> ast.Call:
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _call_name(node.func) == "uvicorn.run"
    ]
    assert len(calls) == 1
    return calls[0]


def test_systemd_parser_preserves_duplicate_directives():
    parsed = _parse_systemd(
        """
        [Service]
        Environment=HOST=127.0.0.1
        Environment=NITRO_HOST=127.0.0.1
        """
    )

    assert parsed["Service"] == [
        ("Environment", "HOST=127.0.0.1"),
        ("Environment", "NITRO_HOST=127.0.0.1"),
    ]


def test_tracked_systemd_authority_is_exactly_five_units():
    assert SYSTEMD_ROOT.is_dir()
    assert {path.name for path in SYSTEMD_ROOT.iterdir() if path.is_file()} == set(
        EXPECTED_UNITS
    )


@pytest.mark.parametrize(("filename", "expected"), EXPECTED_UNITS.items())
def test_systemd_unit_matches_reviewed_contract(filename: str, expected):
    path = SYSTEMD_ROOT / filename
    assert path.is_file(), f"missing tracked unit: {filename}"

    assert _parse_systemd(path.read_text(encoding="utf-8")) == expected


def test_nuxt_has_no_agent_lifecycle_dependency():
    parsed = _parse_systemd(
        (SYSTEMD_ROOT / "vl-nuxt.service").read_text(encoding="utf-8")
    )
    dependencies = [
        value
        for key, value in parsed["Unit"]
        if key in {"After", "Wants", "Requires", "BindsTo", "PartOf"}
    ]

    assert all("vl-agent" not in value for value in dependencies)


@pytest.mark.parametrize(
    ("filename", "script"),
    [("vl-agent.service", "agent/server.py"), ("vl-bot.service", "agent/bot_gateway.py")],
)
@pytest.mark.parametrize("hostile_bind", ["0.0.0.0", "", "::"])
def test_process_launch_override_wins_over_environment_file(
    filename: str,
    script: str,
    hostile_bind: str,
):
    parsed = _parse_systemd(
        (SYSTEMD_ROOT / filename).read_text(encoding="utf-8")
    )

    environment, argv = _effective_process(parsed, {"BIND_HOST": hostile_bind})

    assert environment["BIND_HOST"] == "127.0.0.1"
    assert argv == ["/opt/vinhlong360/venv/bin/python", script]


def test_bot_launch_overrides_hostile_bind_and_agent_url_environment_file():
    parsed = _parse_systemd(
        (SYSTEMD_ROOT / "vl-bot.service").read_text(encoding="utf-8")
    )

    environment, argv = _effective_process(
        parsed,
        {
            "BIND_HOST": "0.0.0.0",
            "AGENT_URL": "http://agent:8360/remote",
        },
    )

    assert environment["BIND_HOST"] == "127.0.0.1"
    assert environment["AGENT_URL"] == "http://127.0.0.1:8360"
    assert argv == [
        "/opt/vinhlong360/venv/bin/python",
        "agent/bot_gateway.py",
    ]


def test_units_do_not_publish_internal_services_or_embed_indexing_unlocks():
    forbidden = (
        "0.0.0.0",
        "--host",
        "LAUNCH_INDEXING_MODE",
        "LAUNCH_INDEXING_OWNER_APPROVED",
        "NUXT_PUBLIC_SITE_NOINDEX=false",
    )
    for filename in EXPECTED_UNITS:
        source = (SYSTEMD_ROOT / filename).read_text(encoding="utf-8")
        assert all(token not in source for token in forbidden), filename


def test_watchdog_uses_bash_for_non_executable_tracked_script():
    parsed = _parse_systemd(
        (SYSTEMD_ROOT / "vl-watchdog.service").read_text(encoding="utf-8")
    )
    exec_start = [value for key, value in parsed["Service"] if key == "ExecStart"]

    assert exec_start == ["/bin/bash /opt/vinhlong360/scripts/ops/watchdog.sh"]


@pytest.mark.parametrize(
    ("relative_path", "port"),
    [("agent/server.py", 8360), ("agent/bot_gateway.py", 8361)],
)
def test_python_entrypoint_loads_loopback_bind_after_dotenv(relative_path: str, port: int):
    tree = _module_ast(ROOT / relative_path)
    assignment = _bind_assignment(tree)

    assert assignment.lineno > _load_dotenv_line(tree)
    assert isinstance(assignment.value, ast.Call)
    assert _call_name(assignment.value.func) == "os.environ.get"
    assert len(assignment.value.args) == 2
    assert isinstance(assignment.value.args[0], ast.Constant)
    assert assignment.value.args[0].value == "BIND_HOST"
    assert isinstance(assignment.value.args[1], ast.Constant)
    assert assignment.value.args[1].value == "127.0.0.1"

    run_call = _uvicorn_call(tree)
    keywords = {keyword.arg: keyword.value for keyword in run_call.keywords}
    assert isinstance(keywords["host"], ast.Name)
    assert keywords["host"].id == "BIND_HOST"
    assert isinstance(keywords["port"], ast.Constant)
    assert keywords["port"].value == port


def test_ss_parser_extracts_canonical_listener_fields_without_process_ids():
    probe = _load_probe()

    listeners = probe.parse_ss_output(PASSING_SS)

    assert [(item.host, item.port, item.owners) for item in listeners] == [
        ("0.0.0.0", 80, ("nginx",)),
        ("::", 443, ("nginx",)),
        ("0.0.0.0", 22, ("sshd",)),
        ("127.0.0.1", 3000, ("node",)),
        ("127.0.0.2", 8360, ("python",)),
        ("::1", 8361, ("python",)),
        ("127.0.0.1", 5432, ("postgres",)),
        ("127.0.0.1", 6379, ("redis-server",)),
    ]


def test_socket_validator_accepts_nginx_public_loopback_internal_and_public_ssh():
    probe = _load_probe()
    listeners = probe.parse_ss_output(PASSING_SS)

    violations = probe.validate_listeners(
        listeners,
        expect_nginx_public_only=True,
        expected_loopback_ports=[3000, 8360, 8361, 5432, 6379],
    )

    assert violations == []


@pytest.mark.parametrize("port", [3000, 3001, 5432, 6379, 8360, 8361, 9080, 9090, 3100])
@pytest.mark.parametrize("host", ["0.0.0.0", "::", "*", "10.10.0.8", "::ffff:127.0.0.1"])
def test_socket_validator_rejects_wildcard_or_nonloopback_internal_ports(
    host: str,
    port: int,
):
    probe = _load_probe()
    listener = probe.Listener(host=host, port=port, owners=("python",))

    violations = probe.validate_listeners(
        [listener],
        expect_nginx_public_only=False,
        expected_loopback_ports=[],
    )

    assert any(item.startswith(f"internal-port-not-loopback:{port}:") for item in violations)


def test_socket_validator_requires_every_expected_loopback_port():
    probe = _load_probe()

    violations = probe.validate_listeners(
        [probe.Listener(host="127.0.0.1", port=8360, owners=("python",))],
        expect_nginx_public_only=False,
        expected_loopback_ports=[3000, 8360],
    )

    assert "missing-loopback-listener:3000" in violations


def test_socket_validator_requires_nginx_ownership_on_public_http_ports():
    probe = _load_probe()
    listeners = probe.parse_ss_output(PASSING_SS.replace('"nginx",pid=120', '"caddy",pid=120'))

    violations = probe.validate_listeners(
        listeners,
        expect_nginx_public_only=True,
        expected_loopback_ports=[3000],
    )

    assert any(item.startswith("public-http-not-nginx:80:") for item in violations)
    assert any(item.startswith("public-http-not-nginx:443:") for item in violations)


def test_socket_validator_rejects_other_public_services_but_allows_owned_ssh():
    probe = _load_probe()
    listeners = [
        probe.Listener(host="0.0.0.0", port=22, owners=("sshd",)),
        probe.Listener(host="0.0.0.0", port=8080, owners=("python",)),
        probe.Listener(host="0.0.0.0", port=80, owners=("nginx",)),
        probe.Listener(host="0.0.0.0", port=443, owners=("nginx",)),
    ]

    violations = probe.validate_listeners(
        listeners,
        expect_nginx_public_only=True,
        expected_loopback_ports=[],
    )

    assert all(":22:" not in item for item in violations)
    assert "unexpected-public-listener:8080:0.0.0.0:python" in violations


@pytest.mark.parametrize("host", ["0.0.0.0", "::"])
@pytest.mark.parametrize("owners", [("python",), (), ("sshd", "python")])
def test_socket_validator_rejects_public_ssh_without_exact_sshd_ownership(
    host: str,
    owners: tuple[str, ...],
):
    probe = _load_probe()
    listeners = [
        probe.Listener(host=host, port=22, owners=owners),
        probe.Listener(host="0.0.0.0", port=80, owners=("nginx",)),
        probe.Listener(host="::", port=443, owners=("nginx",)),
    ]

    violations = probe.validate_listeners(
        listeners,
        expect_nginx_public_only=True,
        expected_loopback_ports=[],
    )

    assert any(item.startswith(f"public-ssh-not-sshd:22:{host}:") for item in violations)


@pytest.mark.parametrize(
    ("source", "collection_error", "args", "expected_code"),
    [
        (
            PASSING_SS,
            False,
            ["--expect-nginx-public-only", "--expect-loopback", "3000", "8360"],
            0,
        ),
        (
            PASSING_SS.replace("127.0.0.2:8360", "0.0.0.0:8360"),
            False,
            ["--expect-loopback", "8360"],
            1,
        ),
        ("", True, ["--expect-loopback", "8360"], 2),
    ],
)
def test_probe_subprocess_allows_omitted_evidence_and_preserves_exit_contract(
    tmp_path: Path,
    source: str,
    collection_error: bool,
    args: list[str],
    expected_code: int,
):
    result = _run_probe_subprocess(
        tmp_path,
        args,
        source=source,
        collection_error=collection_error,
    )

    assert result.returncode == expected_code, result.stderr
    assert "required: --evidence" not in result.stderr
    assert "host-specific collection detail" not in result.stderr
    assert not (tmp_path / "listeners.json").exists()


def test_probe_writes_deterministic_sanitized_pass_evidence(tmp_path: Path):
    probe = _load_probe()
    evidence_path = tmp_path / "listeners.json"
    argv = [
        "--expect-nginx-public-only",
        "--expect-loopback",
        "3000",
        "8360",
        "--expect-loopback",
        "8360",
        "--evidence",
        str(evidence_path),
    ]

    first_code = probe.main(argv, collector=lambda: PASSING_SS)
    first_bytes = evidence_path.read_bytes()
    second_code = probe.main(
        argv,
        collector=lambda: PASSING_SS.replace("pid=120", "pid=9999"),
    )
    second_bytes = evidence_path.read_bytes()
    evidence = json.loads(second_bytes)

    assert first_code == second_code == 0
    assert first_bytes == second_bytes
    assert evidence["verdict"] == "pass"
    assert evidence["expected_loopback_ports"] == [3000, 8360]
    assert evidence["violations"] == []
    assert "pid=" not in second_bytes.decode("utf-8")
    assert "fd=" not in second_bytes.decode("utf-8")
    assert "raw" not in evidence
    assert _evidence_temps(evidence_path) == []


def test_probe_evidence_write_is_atomic_restrictive_and_same_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    probe = _load_probe()
    evidence_path = tmp_path / "listeners.json"
    evidence_path.write_bytes(b"previous evidence\n")
    events: list[tuple[str, object]] = []
    real_mkstemp = probe.tempfile.mkstemp
    real_chmod = probe.os.chmod
    real_fsync = probe.os.fsync
    real_replace = probe.os.replace

    def tracked_mkstemp(*args, **kwargs):
        result = real_mkstemp(*args, **kwargs)
        events.append(("mkstemp", Path(result[1])))
        return result

    def tracked_chmod(path, mode):
        events.append(("chmod", mode))
        return real_chmod(path, mode)

    def tracked_fsync(fd):
        events.append(("fsync", fd))
        return real_fsync(fd)

    def tracked_replace(source, destination):
        events.append(("replace", (Path(source), Path(destination))))
        return real_replace(source, destination)

    monkeypatch.setattr(probe.tempfile, "mkstemp", tracked_mkstemp)
    monkeypatch.setattr(probe.os, "chmod", tracked_chmod)
    monkeypatch.setattr(probe.os, "fsync", tracked_fsync)
    monkeypatch.setattr(probe.os, "replace", tracked_replace)

    code = probe.main(
        ["--expect-loopback", "8360", "--evidence", str(evidence_path)],
        collector=lambda: PASSING_SS,
    )

    event_names = [name for name, _detail in events]
    temp_path = next(detail for name, detail in events if name == "mkstemp")
    replace = next(detail for name, detail in events if name == "replace")
    assert code == 0
    assert event_names.index("chmod") < event_names.index("fsync") < event_names.index("replace")
    assert temp_path.parent == evidence_path.parent
    assert next(detail for name, detail in events if name == "chmod") == 0o600
    assert replace == (temp_path, evidence_path)
    assert evidence_path.read_bytes() != b"previous evidence\n"
    assert _evidence_temps(evidence_path) == []
    if os.name != "nt":
        assert evidence_path.stat().st_mode & 0o077 == 0


def test_probe_preserves_existing_evidence_and_cleans_temp_on_pre_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    probe = _load_probe()
    evidence_path = tmp_path / "listeners.json"
    original = b"previous evidence\n"
    evidence_path.write_bytes(original)

    def fail_fsync(_fd):
        raise OSError("host-specific write detail")

    monkeypatch.setattr(probe.os, "fsync", fail_fsync)

    code = probe.main(
        ["--expect-loopback", "8360", "--evidence", str(evidence_path)],
        collector=lambda: PASSING_SS,
    )
    captured = capsys.readouterr()

    assert code == 2
    assert evidence_path.read_bytes() == original
    assert _evidence_temps(evidence_path) == []
    assert "host-specific write detail" not in captured.out + captured.err


def test_probe_rejects_final_symlink_without_touching_victim(
    tmp_path: Path,
):
    probe = _load_probe()
    victim = tmp_path / "victim.json"
    victim_bytes = b"victim evidence\n"
    victim.write_bytes(victim_bytes)
    evidence_path = tmp_path / "listeners.json"
    evidence_path.symlink_to(victim)

    code = probe.main(
        ["--expect-loopback", "8360", "--evidence", str(evidence_path)],
        collector=lambda: PASSING_SS,
    )

    assert code == 2
    assert evidence_path.is_symlink()
    assert victim.read_bytes() == victim_bytes
    assert _evidence_temps(evidence_path) == []


def test_probe_writes_failure_evidence_and_returns_one(tmp_path: Path):
    probe = _load_probe()
    evidence_path = tmp_path / "listeners.json"
    unsafe = PASSING_SS.replace("127.0.0.2:8360", "0.0.0.0:8360")

    code = probe.main(
        ["--expect-loopback", "8360", "--evidence", str(evidence_path)],
        collector=lambda: unsafe,
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert code == 1
    assert evidence["verdict"] == "fail"
    assert any(
        item.startswith("internal-port-not-loopback:8360:")
        for item in evidence["violations"]
    )


def test_probe_writes_sanitized_collection_error_evidence_and_returns_two(
    tmp_path: Path,
):
    probe = _load_probe()
    evidence_path = tmp_path / "listeners.json"

    def fail_collection():
        raise OSError("host-specific secret detail")

    code = probe.main(
        ["--expect-loopback", "8360", "--evidence", str(evidence_path)],
        collector=fail_collection,
    )
    evidence_text = evidence_path.read_text(encoding="utf-8")
    evidence = json.loads(evidence_text)

    assert code == 2
    assert evidence["verdict"] == "error"
    assert evidence["errors"] == ["socket-collection-failed"]
    assert "host-specific secret detail" not in evidence_text
