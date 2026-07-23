from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "deploy.sh"
ADMISSION = ROOT / "scripts" / "ops" / "deploy_launch_admission.sh"
PROBE = ROOT / "scripts" / "ops" / "probe_launch_boundary.py"
SOCKET_PROBE = ROOT / "scripts" / "ops" / "socket_boundary_probe.py"

EMPTY_URLSET = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
)
EMPTY_MEDIA_URLSET = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"></urlset>'
)
EMPTY_SITEMAP_INDEX = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>'
)


def _git_bash() -> str:
    preferred = Path(r"C:\Program Files\Git\bin\bash.exe")
    if preferred.is_file():
        return str(preferred)
    discovered = shutil.which("bash")
    assert discovered is not None, "Bash is required for launch admission tests"
    return discovered


def _load_probe() -> ModuleType:
    assert PROBE.is_file(), "launch boundary probe is not materialized"
    spec = importlib.util.spec_from_file_location("probe_launch_boundary", PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_socket_probe() -> ModuleType:
    assert SOCKET_PROBE.is_file(), "socket boundary probe is not materialized"
    spec = importlib.util.spec_from_file_location("socket_boundary_probe", SOCKET_PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _deploy_remote_install_block(script: str) -> str:
    start = script.index("close_launch_admission")
    end = script.index("reopen_launch_admission", start)
    return script[start:end]


def test_deploy_sources_admission_and_closes_before_remote_mutation():
    script = DEPLOY.read_text(encoding="utf-8")

    assert "deploy_launch_admission.sh" in script
    assert "scripts/package_launch_release.py launch-release" in script
    assert "verify_closed_release.py" in script
    assert "install_closed_release.sh" in script
    assert "vl-deploy.tar.gz" not in script
    assert "vl-nuxt-output.tar.gz" not in script
    assert "tar -xzf" not in script
    assert "rm -rf $REMOTE/web-nuxt/.output" not in script
    block = _deploy_remote_install_block(script)
    assert block.index("close_launch_admission") < block.index(
        "install_closed_release.sh"
    )
    assert block.index("close_launch_admission") < block.index("systemctl restart")
    assert "maintenance_mode.sh disable" not in script


def test_deploy_uses_a_unique_remote_stage_with_per_stage_archives_and_evidence():
    script = DEPLOY.read_text(encoding="utf-8")
    stage_start = script.index('LAUNCH_STAGE="$("${SSH[@]}"')
    stage_end = script.index("# 5. Ship tarballs", stage_start)
    stage = script[stage_start:stage_end]

    assert 'LAUNCH_STAGE="$(' in stage
    assert "'$LAUNCH_STAGE/archives'" in stage
    assert "'$LAUNCH_STAGE/evidence'" in stage
    assert "'$LAUNCH_STAGE/maintenance'" in stage
    for source in (
        "ops/nginx/maintenance/http-context.conf.template",
        "ops/nginx/maintenance/server-enabled.conf",
        "ops/nginx/maintenance/server-disabled.conf",
    ):
        assert source in stage
    assert (
        '"${SCP[@]}" "${MAINTENANCE_FILES[@]}" '
        '"$VPS:$LAUNCH_STAGE/maintenance/"'
    ) in stage

    upload = script[stage_end : script.index("# 6a.", stage_end)]
    assert '"$VPS:$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz"' in upload
    assert (
        '"$VPS:$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz.sha256"'
        in upload
    )
    assert '"$VPS:/tmp/"' not in upload

    remote_setup = script[script.index("export READINESS_EVIDENCE") :]
    source_override = (
        'export MAINTENANCE_SOURCE_DIR="\\$LAUNCH_STAGE/maintenance"'
    )
    assert source_override in remote_setup
    assert remote_setup.index(source_override) < remote_setup.index(
        'source "\\$LAUNCH_STAGE/deploy_launch_admission.sh"'
    )
    assert remote_setup.index(source_override) < remote_setup.index(
        "close_launch_admission"
    )
    assert 'export READINESS_EVIDENCE="\\$LAUNCH_STAGE/evidence/readiness.json"' in remote_setup
    assert (
        'export SOCKET_BOUNDARY_EVIDENCE="\\$LAUNCH_STAGE/evidence/socket-boundary.json"'
        in remote_setup
    )
    assert (
        'export PUBLIC_BOUNDARY_EVIDENCE="\\$LAUNCH_STAGE/evidence/public-closed.json"'
        in remote_setup
    )


def test_deploy_cleans_pre_close_stage_but_preserves_post_close_failures():
    script = DEPLOY.read_text(encoding="utf-8")

    assert "REMOTE_STAGE_PRESERVE=0" in script
    assert "cleanup_remote_stage" in script
    close_index = script.index("close_launch_admission")
    preserve_index = script.rindex("REMOTE_STAGE_PRESERVE=1", 0, close_index)
    assert preserve_index < close_index
    cleanup_function = script[
        script.index("cleanup_remote_stage()") : script.index("trap cleanup_deploy EXIT")
    ]
    assert 'if [ "$REMOTE_STAGE_PRESERVE" = 0 ]' in cleanup_function
    assert 'rm -rf -- \'$LAUNCH_STAGE\'' in cleanup_function


def test_deploy_persists_success_evidence_atomically_before_stage_cleanup():
    script = DEPLOY.read_text(encoding="utf-8")
    reopen_index = script.index("reopen_launch_admission", script.index("# 6b."))
    success_block = script[reopen_index : script.index("EOF", reopen_index)]

    assert '"$VPS:$LAUNCH_STAGE/evidence/operator-maintenance.json"' in script
    assert 'evidence_tmp="\\$(mktemp -d' in success_block
    assert 'mv -T -- "\\$evidence_tmp" "\\$evidence_final"' in success_block
    assert success_block.index("evidence_tmp=") < success_block.index("mv -T --")
    assert success_block.index("mv -T --") < success_block.index(
        'rm -rf -- "\\$LAUNCH_STAGE"'
    )


def test_success_evidence_lifecycle_exit_trap_preserves_zero_status(tmp_path: Path):
    script = DEPLOY.read_text(encoding="utf-8")
    function_start = script.index("cleanup_evidence() {")
    function_end = script.index("trap cleanup_evidence EXIT", function_start)
    cleanup_function = script[function_start:function_end].replace("\\$", "$")
    scenario = tmp_path / "evidence-success.sh"
    scenario.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
{cleanup_function}
evidence_tmp="$(mktemp -d)"
evidence_final="$evidence_tmp.persisted"
trap cleanup_evidence EXIT
mv -T -- "$evidence_tmp" "$evidence_final"
evidence_tmp=""
rm -rf -- "$evidence_final"
true
""",
        encoding="utf-8",
        newline="\n",
    )

    result = subprocess.run(
        [_git_bash(), "--login", str(scenario)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_deploy_probes_from_the_local_operator_before_remote_install():
    script = DEPLOY.read_text(encoding="utf-8")
    close_index = script.index("close_launch_admission")
    close_session_end = script.index("\nEOF", close_index)
    operator_probe = script.index(
        "python scripts/ops/probe_launch_boundary.py", close_session_end
    )
    install_session = script.index('"${SSH[@]}" "OPERATOR_CIDR=', operator_probe)
    install_index = script.index("install_closed_release.sh", install_session)

    assert close_index < close_session_end < operator_probe
    assert operator_probe < install_session < install_index
    operator_block = script[operator_probe:install_session]
    assert "--expect maintenance" in operator_block
    assert "--operator-source" in operator_block
    assert "--base-url https://vinhlong360.vn" in operator_block


def test_deploy_verifies_remote_archive_before_close_and_installs_only_after_probe():
    script = DEPLOY.read_text(encoding="utf-8")
    remote_verify = script.index("verify_closed_release.py", script.index("# 5."))
    close = script.index("close_launch_admission", remote_verify)
    operator_probe = script.index("python scripts/ops/probe_launch_boundary.py", close)
    installer = script.index("install_closed_release.sh", operator_probe)

    assert remote_verify < close < operator_probe < installer
    assert '--archive-digest-file "\\$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz.sha256"' in script
    assert "--require-closed" in script


def test_systemd_release_bakes_loopback_api_origin_and_gates_proxy_before_reopen():
    script = DEPLOY.read_text(encoding="utf-8")
    build = script[script.index("# 1. Build") : script.index("# 2.")]
    restart = script.index("systemctl restart vl-nuxt", script.index("# 6b."))
    reopen = script.index("reopen_launch_admission", restart)
    restart_to_reopen = script[restart:reopen]

    assert "API_BASE=http://127.0.0.1:8360" in build
    assert "API_BASE=http://agent:8360" not in build
    assert "http://127.0.0.1:3000/api/homepage" in restart_to_reopen
    assert "nuxt-api-proxy.json" in restart_to_reopen


def test_deploy_keeps_destructive_data_and_migration_flags_outside_closed_release():
    script = DEPLOY.read_text(encoding="utf-8")

    for flag in ("--data", "--replace", "--migrate"):
        assert flag in script
    assert "destructive data and migration operations are not supported" in script
    assert "agent/database.py --replace" not in script
    assert "scripts/apply_migrations.py" not in script


def test_launch_admission_uses_only_nuxt_readiness_and_listener_isolation():
    helper = ADMISSION.read_text(encoding="utf-8")

    assert "http://127.0.0.1:3000/_internal/launch-readiness" in helper
    assert "socket_boundary_probe.py" in helper
    assert "--expect-loopback 3000" in helper
    assert "--expect-loopback 3000 8360" not in helper
    assert "--operator-source" not in helper
    assert "/health" not in helper
    assert "vl-agent" not in helper
    assert "vl-bot" not in helper


def test_deploy_backend_diagnostics_are_not_a_post_reopen_gate():
    script = DEPLOY.read_text(encoding="utf-8")
    remote_install = _deploy_remote_install_block(script)
    diagnostics = script[script.index("# 7. Post-admission diagnostics") :]

    assert "/api/search" not in remote_install
    assert '"$agent" = 200' not in diagnostics
    assert '"$ready" = 200' not in diagnostics
    assert '"$search" = 200' not in diagnostics
    assert "'set -e" not in diagnostics
    assert "exit 0'" in diagnostics


def _write_fake_runner(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >>"${COMMAND_LOG:?}"
case "$*" in
  *"maintenance_mode.sh enable"*) printf 'enabled\\n' >"${STATE_FILE:?}" ;;
  *"maintenance_mode.sh disable"*) printf 'disabled\\n' >"${STATE_FILE:?}" ;;
esac
if [[ -n "${FAIL_MATCH:-}" && "$*" == *"$FAIL_MATCH"* ]]; then
  exit 41
fi
if [[ "$*" == "systemctl reload nginx" ]]; then
  reload_count=0
  [[ -f "${RELOAD_COUNT_FILE:?}" ]] && reload_count=$(<"$RELOAD_COUNT_FILE")
  reload_count=$((reload_count + 1))
  printf '%s\n' "$reload_count" >"$RELOAD_COUNT_FILE"
  if [[ -n "${FAIL_RELOAD_AT:-}" && "$reload_count" -eq "$FAIL_RELOAD_AT" ]]; then
    exit 42
  fi
fi
""",
        encoding="utf-8",
        newline="\n",
    )


def _run_admission_sandbox(
    tmp_path: Path,
    *,
    failure: str = "",
    fail_reload_at: int | None = None,
) -> subprocess.CompletedProcess[str]:
    runner = tmp_path / "fake-runner.sh"
    _write_fake_runner(runner)
    maintenance = tmp_path / "maintenance_mode.sh"
    maintenance.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8", newline="\n")
    log = tmp_path / "commands.log"
    state = tmp_path / "maintenance.state"
    readiness = tmp_path / "readiness.json"
    scenario = tmp_path / "scenario.sh"
    scenario.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export RUNNER={str(runner)!r}
export COMMAND_LOG={str(log)!r}
export STATE_FILE={str(state)!r}
export RELOAD_COUNT_FILE={str(tmp_path / 'reload-count')!r}
export READINESS_EVIDENCE={str(readiness)!r}
export OPERATOR_CIDR=192.0.2.10/32
export LAUNCH_ADMISSION_OPS_DIR={str(ROOT / 'scripts' / 'ops')!r}
export MAINTENANCE_MODE_SCRIPT={str(maintenance)!r}
export FAIL_MATCH={failure!r}
export FAIL_RELOAD_AT={str(fail_reload_at or '')!r}
source {str(ADMISSION)!r}
close_launch_admission
"$RUNNER" local-operator-probe
"$RUNNER" verify-archive
"$RUNNER" install-release
"$RUNNER" restart-services
reopen_launch_admission
""",
        encoding="utf-8",
        newline="\n",
    )
    result = subprocess.run(
        [_git_bash(), "--login", str(scenario)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    result.command_log = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    result.maintenance_state = state.read_text(encoding="utf-8").strip() if state.exists() else ""
    return result


def _command_index(commands: list[str], fragment: str) -> int:
    return next(index for index, command in enumerate(commands) if fragment in command)


def test_admission_sandbox_orders_close_operator_probe_install_and_reopen(tmp_path: Path):
    result = _run_admission_sandbox(tmp_path)

    assert result.returncode == 0, result.stderr
    commands = result.command_log
    assert _command_index(commands, "maintenance_mode.sh enable") < _command_index(
        commands, "local-operator-probe"
    )
    assert _command_index(commands, "local-operator-probe") < _command_index(
        commands, "verify-archive"
    )
    assert _command_index(commands, "restart-services") < _command_index(
        commands, "/_internal/launch-readiness"
    )
    assert _command_index(commands, "/_internal/launch-readiness") < _command_index(
        commands, "socket_boundary_probe.py"
    )
    assert _command_index(commands, "socket_boundary_probe.py") < _command_index(
        commands, "maintenance_mode.sh disable"
    )
    assert _command_index(commands, "maintenance_mode.sh disable") < _command_index(
        commands, "--require-public-post-reopen-matrix"
    )
    assert result.maintenance_state == "disabled"


def test_safe_closed_reopen_does_not_require_an_agent_listener(tmp_path: Path):
    result = _run_admission_sandbox(tmp_path)

    assert result.returncode == 0, result.stderr
    socket_command = next(
        command for command in result.command_log if "socket_boundary_probe.py" in command
    )
    assert "--expect-loopback 3000" in socket_command
    assert "8360" not in socket_command
    assert result.maintenance_state == "disabled"


def test_socket_boundary_still_rejects_a_public_agent_listener():
    probe = _load_socket_probe()
    listeners = [
        probe.Listener(host="0.0.0.0", port=22, owners=("sshd",)),
        probe.Listener(host="0.0.0.0", port=80, owners=("nginx",)),
        probe.Listener(host="0.0.0.0", port=443, owners=("nginx",)),
        probe.Listener(host="127.0.0.1", port=3000, owners=("node",)),
        probe.Listener(host="0.0.0.0", port=8360, owners=("python",)),
    ]

    violations = probe.validate_listeners(
        listeners,
        expect_nginx_public_only=True,
        expected_loopback_ports=[3000],
    )

    assert "internal-port-not-loopback:8360:0.0.0.0:python" in violations
    assert "missing-loopback-listener:8360" not in violations


@pytest.mark.parametrize(
    "failure",
    [
        "local-operator-probe",
        "install-release",
        "restart-services",
        "/_internal/launch-readiness",
        "socket_boundary_probe.py",
    ],
)
def test_pre_reopen_failure_never_disables_maintenance(tmp_path: Path, failure: str):
    result = _run_admission_sandbox(tmp_path, failure=failure)

    assert result.returncode != 0
    assert result.maintenance_state == "enabled"
    assert not any("maintenance_mode.sh disable" in item for item in result.command_log)


def test_failed_post_reopen_probe_immediately_redrains(tmp_path: Path):
    result = _run_admission_sandbox(
        tmp_path,
        failure="--require-public-post-reopen-matrix",
    )

    assert result.returncode != 0
    assert result.maintenance_state == "enabled"
    commands = result.command_log
    assert sum("maintenance_mode.sh enable" in item for item in commands) == 2
    assert _command_index(commands, "maintenance_mode.sh disable") < _command_index(
        commands, "--require-public-post-reopen-matrix"
    )


def test_failed_maintenance_disable_immediately_redrains(tmp_path: Path):
    result = _run_admission_sandbox(
        tmp_path,
        failure="maintenance_mode.sh disable",
    )

    assert result.returncode != 0
    assert result.maintenance_state == "enabled"
    commands = result.command_log
    assert sum("maintenance_mode.sh enable" in item for item in commands) == 2


def test_close_reload_failure_stops_nginx_and_proves_it_inactive(tmp_path: Path):
    result = _run_admission_sandbox(tmp_path, fail_reload_at=1)

    assert result.returncode != 0
    commands = result.command_log
    assert _command_index(commands, "systemctl reload nginx") < _command_index(
        commands, "systemctl stop nginx"
    )
    assert _command_index(commands, "systemctl stop nginx") < _command_index(
        commands, "systemctl is-inactive --quiet nginx"
    )
    assert not any("local-operator-probe" in item for item in commands)


def test_redrain_reload_failure_stops_nginx_and_is_never_swallowed(tmp_path: Path):
    result = _run_admission_sandbox(
        tmp_path,
        failure="--require-public-post-reopen-matrix",
        fail_reload_at=3,
    )

    assert result.returncode != 0
    commands = result.command_log
    assert sum("systemctl reload nginx" in item for item in commands) == 3
    assert _command_index(commands, "systemctl stop nginx") < _command_index(
        commands, "systemctl is-inactive --quiet nginx"
    )
    helper = ADMISSION.read_text(encoding="utf-8")
    assert "_redrain_launch_admission || true" not in helper


def _response(
    probe: ModuleType,
    path: str,
    *,
    body: str,
    content_type: str,
    x_robots_tag: str | None = None,
    extra_headers: dict[str, str] | None = None,
):
    headers = {
        "cache-control": ("no-store",),
        "content-type": (content_type,),
        "x-launch-indexing-policy": ("closed",),
    }
    if x_robots_tag is not None:
        headers["x-robots-tag"] = (x_robots_tag,)
    for name, value in (extra_headers or {}).items():
        headers[name.lower()] = (value,)
    return probe.HttpResponse(path=path, status=200, headers=headers, body=body.encode())


def _closed_responses(probe: ModuleType) -> dict[str, object]:
    return {
        "/": _response(
            probe,
            "/",
            body=(
                '<!doctype html><html><head><meta name="robots" '
                'content="noindex, follow"></head><body>closed</body></html>'
            ),
            content_type="text/html; charset=utf-8",
            x_robots_tag="noindex, follow",
        ),
        "/robots.txt": _response(
            probe,
            "/robots.txt",
            body="User-agent: *\nAllow: /\nHost: https://vinhlong360.vn\n",
            content_type="text/plain; charset=utf-8",
        ),
        "/sitemap.xml": _response(
            probe,
            "/sitemap.xml",
            body=EMPTY_URLSET,
            content_type="application/xml; charset=utf-8",
        ),
        "/sitemap-media.xml": _response(
            probe,
            "/sitemap-media.xml",
            body=EMPTY_MEDIA_URLSET,
            content_type="application/xml; charset=utf-8",
        ),
        "/sitemap-index.xml": _response(
            probe,
            "/sitemap-index.xml",
            body=EMPTY_SITEMAP_INDEX,
            content_type="application/xml; charset=utf-8",
        ),
    }


@pytest.mark.parametrize(
    ("expect", "required_flag"),
    [
        ("maintenance", "--operator-source"),
        ("closed", "--require-public-post-reopen-matrix"),
    ],
)
def test_probe_accepts_only_exact_safe_closed_matrix(
    tmp_path: Path,
    expect: str,
    required_flag: str,
):
    probe = _load_probe()
    responses = _closed_responses(probe)
    evidence = tmp_path / "probe.json"

    result = probe.main(
        ["--expect", expect, required_flag, "--evidence", str(evidence)],
        requester=lambda path, _timeout: responses[path],
    )

    assert result == 0
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["verdict"] == "pass"
    assert payload["expect"] == expect
    assert payload["errors"] == []
    assert set(payload["observations"]) == set(responses)
    serialized = evidence.read_text(encoding="utf-8")
    assert "vinhlong360.vn" not in serialized
    assert "closed</body>" not in serialized


def test_operator_source_uses_the_supplied_public_https_origin(
    monkeypatch: pytest.MonkeyPatch,
):
    probe = _load_probe()
    responses = _closed_responses(probe)
    calls: list[tuple[str, str | None]] = []

    def requester_factory(base_url: str, *, host_header: str | None = None):
        calls.append((base_url, host_header))

        def request(path: str, _timeout: float):
            return responses[path]

        return request

    monkeypatch.setattr(probe, "_make_requester", requester_factory)

    result = probe.main(["--expect", "maintenance", "--operator-source"])

    assert result == 0
    assert calls == [("https://vinhlong360.vn", None)]


@pytest.mark.parametrize(
    "base_url",
    [
        "http://vinhlong360.vn",
        "https://example.com",
        "https://vinhlong360.vn/launch",
        "https://vinhlong360.vn/",
    ],
)
def test_probe_cli_rejects_every_noncanonical_production_origin(base_url: str):
    probe = _load_probe()

    with pytest.raises(SystemExit):
        probe.main(
            [
                "--expect",
                "maintenance",
                "--operator-source",
                "--base-url",
                base_url,
            ],
            requester=lambda _path, _timeout: None,
        )


@pytest.mark.parametrize(
    "base_url",
    [
        "http://vinhlong360.vn",
        "https://staging.vinhlong360.vn",
        "https://vinhlong360.vn/private",
    ],
)
def test_probe_env_rejects_every_noncanonical_production_origin(
    monkeypatch: pytest.MonkeyPatch,
    base_url: str,
):
    probe = _load_probe()
    monkeypatch.setenv("VL360_LAUNCH_PUBLIC_URL", base_url)

    with pytest.raises(SystemExit):
        probe.main(
            ["--expect", "maintenance", "--operator-source"],
            requester=lambda _path, _timeout: None,
        )


@pytest.mark.parametrize(
    ("surface", "mutation", "error_code"),
    [
        ("/", "cache", "html-cache-control-invalid"),
        ("/", "header", "html-x-robots-tag-invalid"),
        ("/", "meta", "html-robots-meta-invalid"),
        ("/robots.txt", "discovery", "robots-sitemap-discovery-present"),
        ("/sitemap.xml", "nonempty", "sitemap-root-not-empty"),
        ("/sitemap-media.xml", "shape", "sitemap-media-shape-invalid"),
        ("/sitemap-index.xml", "shape", "sitemap-index-shape-invalid"),
        ("/", "evidence", "launch-evidence-present"),
    ],
)
def test_probe_rejects_closed_matrix_mutations(
    surface: str,
    mutation: str,
    error_code: str,
):
    probe = _load_probe()
    responses = _closed_responses(probe)
    original = responses[surface]

    if mutation == "cache":
        original.headers["cache-control"] = ("public, max-age=60",)
    elif mutation == "header":
        original.headers["x-robots-tag"] = ("index, follow",)
    elif mutation == "meta":
        original.body = original.body.replace(b"noindex, follow", b"index, follow")
    elif mutation == "discovery":
        original.body += b"Sitemap: https://example.invalid/sitemap.xml\n"
    elif mutation == "nonempty":
        original.body = original.body.replace(b"></urlset>", b"><url></url></urlset>")
    elif mutation == "shape":
        original.body = EMPTY_URLSET.encode()
    elif mutation == "evidence":
        original.headers["x-launch-policy-fingerprint"] = ("a" * 64,)

    errors, _observations = probe.probe_closed_matrix(
        requester=lambda path, _timeout: responses[path],
        timeout_seconds=1,
    )

    assert error_code in errors


def test_probe_collection_error_is_sanitized(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    probe = _load_probe()
    evidence = tmp_path / "probe.json"
    secret = "token-super-secret"

    result = probe.main(
        [
            "--expect",
            "closed",
            "--require-public-post-reopen-matrix",
            "--evidence",
            str(evidence),
        ],
        requester=lambda _path, _timeout: (_ for _ in ()).throw(
            OSError(f"network failed with {secret}")
        ),
    )

    assert result == 2
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    serialized = evidence.read_text(encoding="utf-8")
    assert secret not in combined
    assert secret not in serialized
    assert json.loads(serialized)["errors"] == ["http-request-failed"]


def test_probe_evidence_contains_only_stable_booleans_and_reason_codes(tmp_path: Path):
    probe = _load_probe()
    responses = _closed_responses(probe)
    evidence = tmp_path / "probe.json"
    secret = "header-and-body-super-secret"
    responses["/"].headers["x-robots-tag"] = (secret,)
    responses["/"].body += secret.encode("utf-8")

    result = probe.main(
        [
            "--expect",
            "closed",
            "--require-public-post-reopen-matrix",
            "--evidence",
            str(evidence),
        ],
        requester=lambda path, _timeout: responses[path],
    )

    assert result == 1
    serialized = evidence.read_text(encoding="utf-8")
    payload = json.loads(serialized)
    assert secret not in serialized
    assert "body_sha256" not in serialized
    assert '"headers"' not in serialized
    assert set(payload["observations"]["/"]) == {
        "contract_passed",
        "reasons",
        "request_completed",
    }
    assert payload["observations"]["/"]["contract_passed"] is False
    assert payload["observations"]["/"]["reasons"] == ["html-x-robots-tag-invalid"]


@pytest.mark.parametrize(
    "argv",
    [
        ["--expect", "maintenance"],
        ["--expect", "closed"],
        ["--expect", "closed", "--operator-source"],
        ["--expect", "maintenance", "--require-public-post-reopen-matrix"],
        ["--expect", "selective-open", "--require-public-post-reopen-matrix"],
    ],
)
def test_probe_refuses_wrong_mode_or_source_contract(argv: list[str]):
    probe = _load_probe()
    with pytest.raises(SystemExit):
        probe.main(argv, requester=lambda _path, _timeout: None)


def test_shell_scripts_are_syntax_valid():
    for script in (DEPLOY, ADMISSION):
        result = subprocess.run(
            [_git_bash(), "--login", "-n", str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ.copy(),
        )
        assert result.returncode == 0, result.stderr
