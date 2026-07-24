from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest

from scripts.package_launch_release import build_launch_release


ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "scripts" / "ops"
VERIFY = OPS / "verify_closed_release.py"
PURGE = OPS / "purge_launch_runtime.py"
INSTALL = OPS / "install_closed_release.sh"
REHEARSE = OPS / "rehearse_launch_rollback.sh"
RECORDER = OPS / "record_rollback_phase.py"
STUB = OPS / "local_command_stub.py"
POLICY = ROOT / "ops" / "launch-safety" / "cache-purge-paths.json"
RUNBOOK = ROOT / "docs" / "runbooks" / "launch-safety-rollback.md"

EXPECTED_PHASES = [
    "record-and-verify-evidence",
    "suspend-watchdog",
    "enable-maintenance",
    "stop-vl-nuxt",
    "purge-runtime-caches",
    "install-known-good-closed",
    "verify-dependencies-units-daemon-reload",
    "verify-readiness-and-listeners",
    "verify-nginx-closed-boundary",
    "verify-browser-worker-cache",
    "reopen-and-recover-watchdog",
]

REQUIRED_PACKAGE_MEMBERS = {
    "config/launch-indexing-policy.json",
    "config/ai-disclosure.json",
    "web-nuxt/.output/server/launch-readiness-manifest.json",
    "nginx.conf",
    "nginx-ssl.conf",
    "compose-network-audit.json",
    "ops/systemd/vl-agent.service",
    "ops/systemd/vl-nuxt.service",
    "ops/systemd/vl-bot.service",
    "ops/systemd/vl-watchdog.service",
    "ops/systemd/vl-watchdog.timer",
    "scripts/check_migration_gate.py",
    "scripts/ops/install_closed_release.sh",
    "scripts/ops/verify_closed_release.py",
}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_builder():
    return _load_module(
        "task44_release_fixture",
        ROOT / "tests" / "launch_safety" / "test_release_package.py",
    )


def _build_closed_package(tmp_path: Path):
    source = tmp_path / "source"
    audit = _fixture_builder()._write_launch_fixture(source)
    shutil.copytree(ROOT / "ops" / "systemd", source / "ops" / "systemd", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / "ops" / "nginx" / "maintenance",
        source / "ops" / "nginx" / "maintenance",
        dirs_exist_ok=True,
    )
    shutil.copytree(OPS, source / "scripts" / "ops", dirs_exist_ok=True)
    return build_launch_release(
        source,
        tmp_path / "known-good-closed.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_runbook_executes_every_design_phase_in_order():
    source = REHEARSE.read_text(encoding="utf-8")

    phase_lines = [
        line.split("=", 1)[1].strip().strip("'\"")
        for line in source.splitlines()
        if line.startswith("CURRENT_PHASE=") and line != "CURRENT_PHASE=initialization"
    ]

    assert phase_lines == EXPECTED_PHASES


def test_primary_service_order_proves_both_services_before_install_and_restart(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    source = REHEARSE.read_text(encoding="utf-8")
    prefix, main = source.split("CURRENT_PHASE=record-and-verify-evidence", 1)
    log = tmp_path / "commands.log"
    harness = tmp_path / "primary-order.sh"
    harness.write_text(
        prefix
        + r'''
NUXT_STATE=active
AGENT_STATE=active
log_command() { printf '%s\n' "$*" >> "$COMMAND_LOG"; }
run_privileged() {
  log_command "$@"
  if [ "${1:-} ${2:-}" = "systemctl is-active" ]; then
    case "${4:-}" in
      vl-watchdog.timer) return 0 ;;
      vl-nuxt) [ "$NUXT_STATE" = active ] && return 0 || return 3 ;;
      vl-agent) [ "$AGENT_STATE" = active ] && return 0 || return 3 ;;
    esac
  fi
  if [ "${1:-} ${2:-}" = "systemctl stop" ]; then
    [ "$3" != vl-nuxt ] || NUXT_STATE=inactive
    [ "$3" != vl-agent ] || AGENT_STATE=inactive
  elif [ "${1:-} ${2:-}" = "systemctl start" ]; then
    [ "$3" != vl-nuxt ] || NUXT_STATE=active
    [ "$3" != vl-agent ] || AGENT_STATE=active
  fi
  return 0
}
python() { return 0; }
node() { return 0; }
record_phase() { return 0; }
record_recovery_result() { return 0; }
prepare_local_maintenance_model() { return 0; }
maintenance_select() { log_command maintenance-select "$1"; }
install_closed_package() { log_command install-closed-package; }
verify_maintenance_boundary() { log_command maintenance-boundary; }
verify_readiness_and_listeners() { log_command readiness-and-listeners; }
verify_nginx_closed_boundary() { return 0; }
verify_browser_worker_cache() { return 0; }
'''
        + "CURRENT_PHASE=record-and-verify-evidence"
        + main,
        encoding="utf-8",
    )
    for path in (tmp_path / "evidence", tmp_path / "release", tmp_path / "runtime"):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "COMMAND_LOG": _bash_path(log),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    commands = log.read_text(encoding="utf-8").splitlines()
    expected = [
        "systemctl stop vl-nuxt",
        "systemctl is-active --quiet vl-nuxt",
        "systemctl stop vl-agent",
        "systemctl is-active --quiet vl-agent",
        "install-closed-package",
        "systemctl daemon-reload",
        "systemctl start vl-agent",
        "systemctl is-active --quiet vl-agent",
        "systemctl start vl-nuxt",
        "systemctl is-active --quiet vl-nuxt",
        "readiness-and-listeners",
    ]
    cursor = -1
    for item in expected:
        cursor = commands.index(item, cursor + 1)


def test_rehearsal_verifies_package_before_any_operational_mutation():
    source = REHEARSE.read_text(encoding="utf-8")
    main = source.split("CURRENT_PHASE=record-and-verify-evidence", 1)[1]

    verifier = main.index("verify_closed_release.py")
    mutations = [
        main.index(token)
        for token in (
            "run_privileged systemctl stop vl-watchdog.timer",
            "maintenance_select enable",
            "run_privileged systemctl stop vl-nuxt",
            "install_closed_package",
        )
    ]

    assert verifier < min(mutations)
    assert source.index("RECOVERY_TRAP_ARMED=true") > verifier


def test_recovery_trap_is_armed_before_first_watchdog_or_selector_mutation():
    source = REHEARSE.read_text(encoding="utf-8")
    trap = source.index("trap 'keep_maintenance_and_recover")
    armed = source.index("RECOVERY_TRAP_ARMED=true")
    watchdog_stop = source.index("run_privileged systemctl stop vl-watchdog.timer")
    local_prepare = source.index(
        "prepare_local_maintenance_model",
        source.index("CURRENT_PHASE=record-and-verify-evidence"),
    )
    maintenance_enable = source.index(
        "maintenance_select enable", source.index("CURRENT_PHASE=enable-maintenance")
    )

    assert armed < local_prepare
    assert trap < local_prepare
    assert armed < watchdog_stop
    assert trap < watchdog_stop
    assert trap < maintenance_enable


@pytest.mark.parametrize(
    ("proof_status", "expected_status", "expected_state"),
    [(0, 0, "drained"), (42, 42, "unknown")],
)
def test_maintenance_classifier_only_marks_drained_after_full_boundary_proof(
    tmp_path: Path,
    proof_status: int,
    expected_status: int,
    expected_state: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    harness = tmp_path / f"maintenance-classifier-{proof_status}.sh"
    harness.write_text(
        prefix
        + r'''
verify_maintenance_boundary() { return "$PROOF_STATUS"; }
set +e
classify_maintenance_boundary "$EVIDENCE_DIR/maintenance.json"
status=$?
printf 'status=%s\nstate=%s\n' "$status" "$TRAFFIC_STATE"
''',
        encoding="utf-8",
    )
    for path in (tmp_path / "evidence", tmp_path / "release", tmp_path / "runtime"):
        path.mkdir(exist_ok=True)
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "PROOF_STATUS": str(proof_status),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"status={expected_status}",
        f"state={expected_state}",
    ]


def test_local_maintenance_probe_propagates_its_exact_failure_status():
    source = REHEARSE.read_text(encoding="utf-8")
    probe = source.split("verify_maintenance_boundary()", 1)[1].split(
        "verify_browser_worker_cache()", 1
    )[0]

    assert "local probe_status=$?" in probe
    assert 'return "$probe_status"' in probe


def test_service_postcondition_helpers_preserve_unexpected_systemctl_status(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    harness = tmp_path / "service-status.sh"
    harness.write_text(
        prefix
        + r'''
run_privileged() { return 42; }
set +e
service_is_active vl-agent
printf 'active=%s\n' "$?"
service_is_inactive vl-agent
printf 'inactive=%s\n' "$?"
''',
        encoding="utf-8",
    )
    for path in (tmp_path / "evidence", tmp_path / "release", tmp_path / "runtime"):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["active=42", "inactive=42"]


def test_recovery_stops_and_proves_both_services_before_reinstalling_then_restarts_in_order(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    log = tmp_path / "commands.log"
    harness = tmp_path / "recovery-order.sh"
    harness.write_text(
        prefix
        + r'''
NUXT_STATE=active
AGENT_STATE=active
TRAFFIC_STATE=drained
WATCHDOG_TIMER_WAS_ACTIVE=true
log_command() { printf '%s\n' "$*" >> "$COMMAND_LOG"; }
run_privileged() {
  log_command "$@"
  if [ "${1:-} ${2:-}" = "systemctl is-active" ]; then
    case "${4:-}" in
      vl-nuxt) [ "$NUXT_STATE" = active ] && return 0 || return 3 ;;
      vl-agent) [ "$AGENT_STATE" = active ] && return 0 || return 3 ;;
    esac
  fi
  if [ "${1:-} ${2:-}" = "systemctl stop" ]; then
    [ "$3" != vl-nuxt ] || NUXT_STATE=inactive
    [ "$3" != vl-agent ] || AGENT_STATE=inactive
  elif [ "${1:-} ${2:-}" = "systemctl start" ]; then
    [ "$3" != vl-nuxt ] || NUXT_STATE=active
    [ "$3" != vl-agent ] || AGENT_STATE=active
  fi
  return 0
}
python() { return 0; }
record_phase() { return 0; }
record_recovery_result() { log_command record "$1" "$2" "${3:-0}"; }
install_closed_package() { log_command install-closed-package; }
verify_dependencies_units_daemon_reload() { run_privileged systemctl daemon-reload; }
verify_readiness_and_listeners() { log_command readiness-and-listeners; }
verify_nginx_closed_boundary() { return 0; }
verify_browser_worker_cache() { return 0; }
keep_maintenance_and_recover 47
''',
        encoding="utf-8",
    )
    for path in (tmp_path / "evidence", tmp_path / "release", tmp_path / "runtime"):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "COMMAND_LOG": _bash_path(log),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 47, result.stderr + result.stdout
    commands = log.read_text(encoding="utf-8").splitlines()
    expected = [
        "systemctl stop vl-nuxt",
        "systemctl is-active --quiet vl-nuxt",
        "systemctl stop vl-agent",
        "systemctl is-active --quiet vl-agent",
        "install-closed-package",
        "systemctl daemon-reload",
        "systemctl start vl-agent",
        "systemctl is-active --quiet vl-agent",
        "systemctl start vl-nuxt",
        "systemctl is-active --quiet vl-nuxt",
        "readiness-and-listeners",
    ]
    cursor = -1
    for item in expected:
        cursor = commands.index(item, cursor + 1)


def test_recovery_start_postcondition_failure_cleans_up_and_does_not_restore_watchdog(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    log = tmp_path / "commands.log"
    harness = tmp_path / "recovery-start-failure.sh"
    harness.write_text(
        prefix
        + r'''
NUXT_STATE=active
AGENT_STATE=active
AGENT_STARTED=false
TRAFFIC_STATE=drained
WATCHDOG_TIMER_WAS_ACTIVE=true
log_command() { printf '%s\n' "$*" >> "$COMMAND_LOG"; }
run_privileged() {
  log_command "$@"
  if [ "${1:-} ${2:-}" = "systemctl is-active" ]; then
    case "${4:-}" in
      vl-nuxt) [ "$NUXT_STATE" = active ] && return 0 || return 3 ;;
      vl-agent)
        [ "$AGENT_STATE" = active ] || return 3
        [ "$AGENT_STARTED" != true ] || return 42
        return 0
        ;;
    esac
  fi
  if [ "${1:-} ${2:-}" = "systemctl stop" ]; then
    [ "$3" != vl-nuxt ] || NUXT_STATE=inactive
    if [ "$3" = vl-agent ]; then
      AGENT_STATE=inactive
      AGENT_STARTED=false
    fi
  elif [ "${1:-} ${2:-}" = "systemctl start" ]; then
    [ "$3" != vl-nuxt ] || NUXT_STATE=active
    if [ "$3" = vl-agent ]; then
      AGENT_STATE=active
      AGENT_STARTED=true
    fi
  fi
  return 0
}
python() { return 0; }
record_phase() { return 0; }
record_recovery_result() { log_command record "$1" "$2" "${3:-0}"; }
install_closed_package() { return 0; }
verify_dependencies_units_daemon_reload() { return 0; }
verify_readiness_and_listeners() { return 0; }
verify_nginx_closed_boundary() { return 0; }
verify_browser_worker_cache() { return 0; }
keep_maintenance_and_recover 47
''',
        encoding="utf-8",
    )
    for path in (tmp_path / "evidence", tmp_path / "release", tmp_path / "runtime"):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "COMMAND_LOG": _bash_path(log),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 47, result.stderr + result.stdout
    commands = log.read_text(encoding="utf-8").splitlines()
    assert "record prove-vl-agent-active failed 42" in commands
    assert "record start-vl-nuxt skipped 0" in commands
    cleanup_nuxt = commands.index("systemctl stop vl-nuxt", commands.index("systemctl start vl-agent"))
    cleanup_agent = commands.index("systemctl stop vl-agent", cleanup_nuxt + 1)
    assert cleanup_nuxt < cleanup_agent
    assert "record cleanup-stop-vl-nuxt passed 0" in commands
    assert "record cleanup-stop-vl-agent passed 0" in commands
    assert "record restore-watchdog skipped 0" in commands
    assert "systemctl start vl-watchdog.timer" not in commands
    assert not any(command == "maintenance-select disable" for command in commands)


def test_recovery_attempts_both_stops_and_skips_reinstall_unless_both_are_inactive(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    log = tmp_path / "commands.log"
    harness = tmp_path / "recovery-stop-failure.sh"
    harness.write_text(
        prefix
        + r'''
NUXT_STATE=active
AGENT_STATE=active
TRAFFIC_STATE=drained
WATCHDOG_TIMER_WAS_ACTIVE=true
log_command() { printf '%s\n' "$*" >> "$COMMAND_LOG"; }
run_privileged() {
  log_command "$@"
  if [ "$*" = "systemctl stop vl-nuxt" ]; then
    return 55
  fi
  if [ "$*" = "systemctl stop vl-agent" ]; then
    AGENT_STATE=inactive
    return 0
  fi
  if [ "$*" = "systemctl is-active --quiet vl-nuxt" ]; then
    return 0
  fi
  if [ "$*" = "systemctl is-active --quiet vl-agent" ]; then
    [ "$AGENT_STATE" = active ] && return 0 || return 3
  fi
  return 0
}
python() { return 0; }
record_phase() { return 0; }
record_recovery_result() { log_command record "$1" "$2" "${3:-0}"; }
install_closed_package() { log_command install-closed-package; }
keep_maintenance_and_recover 47
''',
        encoding="utf-8",
    )
    for path in (tmp_path / "evidence", tmp_path / "release", tmp_path / "runtime"):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "COMMAND_LOG": _bash_path(log),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 47, result.stderr + result.stdout
    commands = log.read_text(encoding="utf-8").splitlines()
    assert commands.index("systemctl stop vl-nuxt") < commands.index("systemctl stop vl-agent")
    assert "record stop-vl-nuxt failed 55" in commands
    assert "record prove-vl-nuxt-inactive failed 1" in commands
    assert "record stop-vl-agent passed 0" in commands
    assert "record prove-vl-agent-inactive passed 0" in commands
    assert "install-closed-package" not in commands
    for phase in (
        "verify-recovery-package",
        "install-closed-release",
        "verify-dependencies-units-daemon-reload",
        "start-vl-agent",
        "prove-vl-agent-active",
        "start-vl-nuxt",
        "prove-vl-nuxt-active",
        "verify-readiness-and-listeners",
        "verify-nginx-closed-boundary",
        "verify-browser-worker-cache",
        "restore-watchdog",
    ):
        assert f"record {phase} skipped 0" in commands


def test_dependency_and_daemon_reload_helper_does_not_start_nuxt(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    log = tmp_path / "commands.log"
    harness = tmp_path / "dependency-helper.sh"
    harness.write_text(
        prefix
        + r'''
run_local_authority() { printf '{"dependency_check":"passed"}\n'; }
python() { return 0; }
run_privileged() { printf '%s\n' "$*" >> "$COMMAND_LOG"; }
verify_dependencies_units_daemon_reload
''',
        encoding="utf-8",
    )
    for path in (tmp_path / "evidence", tmp_path / "release", tmp_path / "runtime"):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "COMMAND_LOG": _bash_path(log),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert log.read_text(encoding="utf-8").splitlines() == ["systemctl daemon-reload"]


def test_host_dependency_verifier_consumes_installer_mount_evidence(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    log = tmp_path / "commands.log"
    mount_evidence = tmp_path / "evidence" / "primary" / "install" / "findmnt-after.json"
    harness = tmp_path / "host-dependency-helper.sh"
    harness.write_text(
        prefix
        + r'''
MODE=--execute-on-host
python() { printf 'python %s\n' "$*" >> "$COMMAND_LOG"; return 0; }
run_privileged() { printf '%s\n' "$*" >> "$COMMAND_LOG"; return 0; }
verify_dependencies_units_daemon_reload "$MOUNT_EVIDENCE"
''',
        encoding="utf-8",
    )
    for path in (
        tmp_path / "evidence",
        tmp_path / "release",
        tmp_path / "persistent",
        tmp_path / "runtime",
    ):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "COMMAND_LOG": _bash_path(log),
            "MOUNT_EVIDENCE": _bash_path(mount_evidence),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(tmp_path / "release"),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(tmp_path / "persistent"),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(tmp_path / "runtime"),
            "EVIDENCE_DIR": _bash_path(tmp_path / "evidence"),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    commands = log.read_text(encoding="utf-8").splitlines()
    verifier = next(line for line in commands if "verify_closed_release.py" in line)
    assert f"--persistent-mount-evidence {_bash_path(mount_evidence)}" in verifier

    source = " ".join(
        REHEARSE.read_text(encoding="utf-8").replace("\\\n", " ").split()
    )
    assert (
        'verify_dependencies_units_daemon_reload '
        '"$EVIDENCE_DIR/primary/install/findmnt-after.json"' in source
    )
    assert (
        'verify_dependencies_units_daemon_reload '
        '"$EVIDENCE_DIR/recovery/install/findmnt-after.json"' in source
    )


def _bash_path(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if len(resolved) >= 3 and resolved[1:3] == ":/":
        return f"/{resolved[0].lower()}/{resolved[3:]}"
    return resolved


def _find_bash() -> Path:
    candidates = (
        os.environ.get("GIT_BASH"),
        shutil.which("bash"),
        r"C:\Program Files\Git\bin\bash.exe",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return Path("bash-unavailable")


BASH = _find_bash()


def test_bash_discovery_uses_path_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fake_bash = tmp_path / "bash"
    fake_bash.write_text("#!/usr/bin/env bash\n", encoding="ascii")
    monkeypatch.delenv("GIT_BASH", raising=False)
    monkeypatch.setattr(
        shutil,
        "which",
        lambda executable: str(fake_bash) if executable == "bash" else None,
    )

    assert _find_bash() == fake_bash
    source = Path(__file__).read_text(encoding="utf-8")
    assert ("bash" + " = Path") not in source


def _run_rehearsal_prefix_harness(
    tmp_path: Path,
    body: str,
    *,
    extra_env: dict[str, str] | None = None,
    name: str = "harness.sh",
) -> subprocess.CompletedProcess[str]:
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    prefix = REHEARSE.read_text(encoding="utf-8").split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    harness = tmp_path / name
    harness.write_text(prefix + body, encoding="utf-8")
    evidence = tmp_path / "evidence"
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    runtime = tmp_path / "runtime"
    for path in (evidence, release, persistent, runtime):
        path.mkdir(exist_ok=True)
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(release),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(persistent),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(runtime),
            "EVIDENCE_DIR": _bash_path(evidence),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(BASH), str(harness)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_install_closed_package_omits_empty_mount_authority_and_preserves_value(
    tmp_path: Path,
):
    fake_scripts = tmp_path / "fake-scripts"
    fake_scripts.mkdir()
    installer = fake_scripts / "install_closed_release.sh"
    installer.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\0' \"$@\" > \"$ARGV_CAPTURE\"\n",
        encoding="ascii",
    )
    installer.chmod(0o755)
    empty_capture = tmp_path / "empty-argv"
    host_capture = tmp_path / "host-argv"
    mount_authority = tmp_path / "mount authority"

    result = _run_rehearsal_prefix_harness(
        tmp_path,
        r'''
SCRIPT_DIR="$FAKE_SCRIPT_DIR"
MOUNT_AUTHORITY=
ARGV_CAPTURE="$EMPTY_CAPTURE" install_closed_package \
  "$KNOWN_GOOD_CLOSED" "$EVIDENCE_DIR/empty"
MODE=--execute-on-host
MOUNT_AUTHORITY="$EXACT_MOUNT_AUTHORITY"
ARGV_CAPTURE="$HOST_CAPTURE" install_closed_package \
  "$KNOWN_GOOD_CLOSED" "$EVIDENCE_DIR/host"
''',
        extra_env={
            "EMPTY_CAPTURE": _bash_path(empty_capture),
            "EXACT_MOUNT_AUTHORITY": _bash_path(mount_authority),
            "FAKE_SCRIPT_DIR": _bash_path(fake_scripts),
            "HOST_CAPTURE": _bash_path(host_capture),
            "MOUNT_AUTHORITY": "",
        },
        name="install-closed-package-argv.sh",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    empty_args = empty_capture.read_bytes().split(b"\0")[:-1]
    host_args = host_capture.read_bytes().split(b"\0")[:-1]
    assert b"--mount-authority" not in empty_args
    mount_index = host_args.index(b"--mount-authority")
    assert host_args[mount_index : mount_index + 3] == [
        b"--mount-authority",
        os.fsencode(_bash_path(mount_authority)),
        b"--require-closed",
    ]


def test_local_maintenance_selector_preserves_real_selector_failure_before_stub(
    tmp_path: Path,
):
    fake_scripts = tmp_path / "fake-scripts"
    fake_scripts.mkdir()
    maintenance_mode = fake_scripts / "maintenance_mode.sh"
    maintenance_mode.write_text("#!/usr/bin/env bash\nprintf 'selector-output\\n'\nexit 61\n")
    maintenance_mode.chmod(0o755)
    result = _run_rehearsal_prefix_harness(
        tmp_path,
        r'''
SCRIPT_DIR="$FAKE_SCRIPT_DIR"
run_privileged() { printf 'stub-output\n'; return 0; }
set +e
maintenance_select enable
printf 'status=%s\n' "$?"
''',
        extra_env={"FAKE_SCRIPT_DIR": _bash_path(fake_scripts)},
        name="maintenance-status.sh",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == "status=61"
    assert "stub-output" not in result.stdout


def test_host_probe_authorities_are_required_before_mutation(tmp_path: Path):
    result = _run_rehearsal_prefix_harness(
        tmp_path,
        r'''
MODE=--execute-on-host
set +e
validate_host_probe_authorities
printf 'status=%s\n' "$?"
''',
        name="host-probe-authority-status.sh",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.splitlines()[-1] == "status=64"

    source = REHEARSE.read_text(encoding="utf-8")
    main = source.split("CURRENT_PHASE=record-and-verify-evidence", 1)[1]
    assert "validate_host_probe_authorities" in main
    assert main.index("validate_host_probe_authorities") < main.index(
        "CURRENT_PHASE=suspend-watchdog"
    )

    same_authority = _run_rehearsal_prefix_harness(
        tmp_path,
        r'''
MODE=--execute-on-host
set +e
validate_host_probe_authorities
printf 'status=%s\n' "$?"
''',
        extra_env={
            "NGINX_PUBLIC_PROBE_URL": "https://probe.example",
            "NGINX_OPERATOR_PROBE_URL": "https://probe.example",
        },
        name="same-host-probe-authority-status.sh",
    )
    assert same_authority.returncode == 0, same_authority.stderr + same_authority.stdout
    assert same_authority.stdout.splitlines()[-1] == "status=64"


def test_watchdog_probe_errors_are_not_treated_as_inactive(tmp_path: Path):
    result = _run_rehearsal_prefix_harness(
        tmp_path,
        r'''
run_privileged() { return 7; }
set +e
watchdog_timer_is_active
printf 'status=%s\n' "$?"
''',
        name="watchdog-probe-status.sh",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.splitlines()[-1] == "status=7"


def test_post_reopen_probe_binds_to_configured_operator_authority():
    source = REHEARSE.read_text(encoding="utf-8")
    post_reopen = source.split("CURRENT_PHASE=reopen-and-recover-watchdog", 1)[1].split(
        "TRAFFIC_STATE=open", 1
    )[0]

    assert "VL360_LAUNCH_PUBLIC_URL=" in post_reopen
    assert "NGINX_OPERATOR_PROBE_URL" in post_reopen


def test_local_listener_authority_nonzero_is_not_masked_by_valid_output(
    tmp_path: Path,
):
    result = _run_rehearsal_prefix_harness(
        tmp_path,
        r'''
SCRIPT_DIR="$REAL_SCRIPT_DIR"
run_local_authority() {
  case "$1" in
    readiness)
      printf '%s\n' '{"checks":[{"name":"manifest-schema","ok":true},{"name":"artifact-evidence","ok":true},{"name":"compiled-cache-rules","ok":true},{"name":"public-prerender","ok":true},{"name":"service-worker-cache-purge","ok":true}],"ok":true,"state":"closed"}'
      return 0
      ;;
    listener)
      printf '%s\n' 'LISTEN 0 511 0.0.0.0:80 0.0.0.0:* users:(("nginx",pid=1,fd=1))'
      printf '%s\n' 'LISTEN 0 511 [::]:443 [::]:* users:(("nginx",pid=1,fd=2))'
      printf '%s\n' 'LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=2,fd=3))'
      printf '%s\n' 'LISTEN 0 2048 127.0.0.1:3000 0.0.0.0:* users:(("node",pid=3,fd=4))'
      return 62
      ;;
  esac
}
set +e
verify_readiness_and_listeners "$EVIDENCE_DIR/listener-test"
printf 'status=%s\n' "$?"
''',
        extra_env={"REAL_SCRIPT_DIR": _bash_path(OPS)},
        name="listener-status.sh",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.splitlines()[-1] == "status=62"


def test_local_readiness_authority_nonzero_is_not_masked_by_blocked_evidence(
    tmp_path: Path,
):
    result = _run_rehearsal_prefix_harness(
        tmp_path,
        r'''
run_local_authority() {
  case "$1" in
    readiness)
      printf '%s\n' '{"checks":[{"name":"manifest-schema","ok":true}],"ok":true,"state":"closed"}'
      return 63
      ;;
    listener)
      printf 'listener-ran\n'
      return 0
      ;;
  esac
}
set +e
verify_readiness_and_listeners "$EVIDENCE_DIR/readiness-test"
printf 'status=%s\n' "$?"
''',
        name="readiness-status.sh",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.splitlines()[-1] == "status=63"
    assert "listener-ran" not in result.stdout


@pytest.mark.parametrize(
    ("failure_kind", "failure_status", "mode"),
    [
        ("dependency", 51, "--local-rehearsal"),
        ("pip", 52, "--execute-on-host"),
        ("installed-verifier", 53, "--local-rehearsal"),
        ("daemon-reload", 54, "--local-rehearsal"),
    ],
)
def test_recovery_dependency_chain_preserves_each_intermediate_failure(
    tmp_path: Path,
    failure_kind: str,
    failure_status: int,
    mode: str,
):
    result = _run_rehearsal_prefix_harness(
        tmp_path,
        rf'''
MODE={mode}
FAILURE_KIND={failure_kind}
FAILURE_STATUS={failure_status}
NUXT_STATE=active
AGENT_STATE=active
TRAFFIC_STATE=drained
WATCHDOG_TIMER_WAS_ACTIVE=true
run_privileged() {{
  printf 'command %s\n' "$*"
  if [ "$*" = "systemctl stop vl-nuxt" ]; then NUXT_STATE=inactive; return 0; fi
  if [ "$*" = "systemctl stop vl-agent" ]; then AGENT_STATE=inactive; return 0; fi
  if [ "$*" = "systemctl start vl-nuxt" ]; then NUXT_STATE=active; return 0; fi
  if [ "$*" = "systemctl start vl-agent" ]; then AGENT_STATE=active; return 0; fi
  if [ "$*" = "systemctl is-active --quiet vl-nuxt" ]; then
    [ "$NUXT_STATE" = active ] && return 0 || return 3
  fi
  if [ "$*" = "systemctl is-active --quiet vl-agent" ]; then
    [ "$AGENT_STATE" = active ] && return 0 || return 3
  fi
  if [ "$*" = "systemctl daemon-reload" ] && [ "$FAILURE_KIND" = daemon-reload ]; then
    return "$FAILURE_STATUS"
  fi
  return 0
}}
run_local_authority() {{
  printf '{{"dependency_check":"passed"}}\n'
  [ "$FAILURE_KIND" != dependency ] || return "$FAILURE_STATUS"
  return 0
}}
python() {{
  printf 'python-command %s\n' "$*"
  printf '{{"valid_looking":true}}\n'
  if [ "$FAILURE_KIND" = pip ] && [ "${{1:-}} ${{2:-}} ${{3:-}}" = "-m pip check" ]; then
    return "$FAILURE_STATUS"
  fi
  if [ "$FAILURE_KIND" = installed-verifier ] \
    && [[ " $* " == *" --installed-root "* ]]; then
    return "$FAILURE_STATUS"
  fi
  return 0
}}
record_phase() {{ return 0; }}
record_recovery_result() {{ printf 'record %s %s %s\n' "$1" "$2" "${{3:-0}}"; }}
install_closed_package() {{ return 0; }}
verify_readiness_and_listeners() {{ return 0; }}
verify_nginx_closed_boundary() {{ return 0; }}
verify_browser_worker_cache() {{ return 0; }}
keep_maintenance_and_recover 47
''',
        name=f"dependency-{failure_kind}.sh",
    )

    assert result.returncode == 47, result.stderr + result.stdout
    assert (
        f"record verify-dependencies-units-daemon-reload failed {failure_status}"
        in result.stdout
    )
    for phase in (
        "start-vl-agent",
        "prove-vl-agent-active",
        "start-vl-nuxt",
        "prove-vl-nuxt-active",
    ):
        assert f"record {phase} skipped 0" in result.stdout
    assert "record restore-watchdog skipped 0" in result.stdout
    assert "command systemctl start vl-agent" not in result.stdout
    assert "command systemctl start vl-nuxt" not in result.stdout
    assert "command systemctl start vl-watchdog.timer" not in result.stdout
    if failure_kind in {"dependency", "pip"}:
        assert " --installed-root " not in f" {result.stdout} "
        assert "command systemctl daemon-reload" not in result.stdout
    elif failure_kind == "installed-verifier":
        assert " --installed-root " in f" {result.stdout} "
        assert "command systemctl daemon-reload" not in result.stdout
    else:
        assert " --installed-root " in f" {result.stdout} "
        assert "command systemctl daemon-reload" in result.stdout


@pytest.mark.parametrize(
    ("operator_url", "legacy_url", "expected_url"),
    [
        ("https://operator.example", "https://legacy.example", "https://operator.example"),
        (None, "https://legacy.example", "https://legacy.example"),
    ],
)
def test_operator_probe_url_precedence_and_legacy_fallback_are_behavioral(
    tmp_path: Path,
    operator_url: str | None,
    legacy_url: str,
    expected_url: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    capture = tmp_path / "capture.txt"
    prefix = tmp_path / "rehearse-prefix.sh"
    prefix.write_text(
        REHEARSE.read_text(encoding="utf-8").split(
            "CURRENT_PHASE=record-and-verify-evidence", 1
        )[0],
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence"
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    runtime = tmp_path / "runtime"
    for path in (evidence, release, persistent, runtime):
        path.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "PROBE_CAPTURE": _bash_path(capture),
            "REHEARSE_PREFIX": _bash_path(prefix),
            "KNOWN_GOOD_CLOSED": _bash_path(tmp_path / "unused.tar.gz"),
            "LOCAL_RELEASE_ROOT": _bash_path(release),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(persistent),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(runtime),
            "EVIDENCE_DIR": _bash_path(evidence),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
            "NGINX_PROBE_URL": legacy_url,
        }
    )
    if operator_url is None:
        env.pop("NGINX_OPERATOR_PROBE_URL", None)
    else:
        env["NGINX_OPERATOR_PROBE_URL"] = operator_url
    command = """
set -Eeuo pipefail
source "$REHEARSE_PREFIX"
MODE=--execute-on-host
python() { printf 'python=%s\n' "$VL360_LAUNCH_PUBLIC_URL" >> "$PROBE_CAPTURE"; }
node() { printf 'node=%s\n' "$*" >> "$PROBE_CAPTURE"; }
verify_nginx_closed_boundary "$EVIDENCE_DIR/closed.json"
verify_browser_worker_cache "$EVIDENCE_DIR/browser.json"
"""
    result = subprocess.run(
        [str(BASH), "-c", command],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    captured = capture.read_text(encoding="utf-8").splitlines()
    assert captured[0] == f"python={expected_url}"
    assert f"--base-url {expected_url}" in captured[1]


def test_local_rehearsal_failure_injection_preserves_status_and_records_recovery(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    package = _build_closed_package(tmp_path / "package")
    later_skips = {
        "recovery:stop-vl-nuxt": ("skipped", 0),
        "recovery:prove-vl-nuxt-inactive": ("skipped", 0),
        "recovery:stop-vl-agent": ("skipped", 0),
        "recovery:prove-vl-agent-inactive": ("skipped", 0),
        "recovery:verify-recovery-package": ("skipped", 0),
        "recovery:install-closed-release": ("skipped", 0),
        "recovery:verify-dependencies-units-daemon-reload": ("skipped", 0),
        "recovery:start-vl-agent": ("skipped", 0),
        "recovery:prove-vl-agent-active": ("skipped", 0),
        "recovery:start-vl-nuxt": ("skipped", 0),
        "recovery:prove-vl-nuxt-active": ("skipped", 0),
        "recovery:verify-readiness-and-listeners": ("skipped", 0),
        "recovery:verify-nginx-closed-boundary": ("skipped", 0),
        "recovery:verify-browser-worker-cache": ("skipped", 0),
    }
    active_services = {
        "nginx": "active",
        "vl-nuxt": "active",
        "vl-watchdog.service": "inactive",
        "vl-watchdog.timer": "active",
    }
    cases = (
        {
            "failures": {"systemctl stop vl-watchdog.timer": 37},
            "expected": {
                "record-and-verify-evidence": ("passed", 0),
                "suspend-watchdog": ("failed", 37),
                **later_skips,
                "recovery:restore-watchdog": ("passed", 0),
                "recovery": ("failed", 37),
            },
            "traffic_state": "unknown",
        },
        {
            "failures": {"vl360-maintenance enable": 38},
            "services": {**active_services, "vl-watchdog.timer": "inactive"},
            "expected": {
                "record-and-verify-evidence": ("passed", 0),
                "suspend-watchdog": ("passed", 0),
                "enable-maintenance": ("failed", 38),
                "recovery:maintenance-enable": ("failed", 38),
                "recovery:nginx-test-closed": ("skipped", 0),
                "recovery:nginx-reload-closed": ("skipped", 0),
                "recovery:maintenance-probe": ("skipped", 0),
                "recovery:classify-traffic-state": ("passed", 0),
                **later_skips,
                "recovery:restore-watchdog": ("skipped", 0),
                "recovery": ("failed", 38),
            },
            "traffic_state": "open",
        },
        {
            "failures": {"systemctl reload nginx": 39},
            "expected": {
                "record-and-verify-evidence": ("passed", 0),
                "suspend-watchdog": ("passed", 0),
                "enable-maintenance": ("failed", 39),
                "recovery:maintenance-enable": ("passed", 0),
                "recovery:nginx-test-closed": ("passed", 0),
                "recovery:nginx-reload-closed": ("failed", 39),
                "recovery:maintenance-probe": ("skipped", 0),
                "recovery:classify-traffic-state": ("failed", 2),
                **later_skips,
                "recovery:restore-watchdog": ("passed", 0),
                "recovery": ("failed", 39),
            },
            "traffic_state": "unknown",
        },
        {
            "failures": {"vl360-maintenance-probe": 40},
            "expected": {
                "record-and-verify-evidence": ("passed", 0),
                "suspend-watchdog": ("passed", 0),
                "enable-maintenance": ("failed", 40),
                "recovery:maintenance-enable": ("passed", 0),
                "recovery:nginx-test-closed": ("passed", 0),
                "recovery:nginx-reload-closed": ("passed", 0),
                "recovery:maintenance-probe": ("failed", 40),
                "recovery:classify-traffic-state": ("failed", 2),
                **later_skips,
                "recovery:restore-watchdog": ("passed", 0),
                "recovery": ("failed", 40),
            },
            "traffic_state": "unknown",
        },
        {
            "failures": {
                "systemctl stop vl-watchdog.timer": 37,
                "systemctl start vl-watchdog.timer": 41,
            },
            "expected": {
                "record-and-verify-evidence": ("passed", 0),
                "suspend-watchdog": ("failed", 37),
                **later_skips,
                "recovery:restore-watchdog": ("failed", 41),
                "recovery": ("failed", 37),
            },
            "traffic_state": "unknown",
        },
    )

    def run_case(case: tuple[int, dict[str, object]]) -> None:
        index, configuration = case
        expected = configuration["expected"]
        failures = configuration["failures"]
        case_root = tmp_path / f"case-{index}"
        evidence = case_root / "evidence"
        release_root = case_root / "release"
        persistent = case_root / "persistent"
        runtime = case_root / "runtime"
        for path in (evidence, release_root, persistent, runtime):
            path.mkdir(parents=True)
        environment = case_root / "external.env"
        environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
        state = case_root / "state.json"
        state_payload: dict[str, object] = {"failures": failures}
        if "services" in configuration:
            state_payload["services"] = configuration["services"]
        state.write_text(
            json.dumps(state_payload) + "\n",
            encoding="ascii",
        )

        env = os.environ.copy()
        env.update(
            {
                "KNOWN_GOOD_CLOSED": _bash_path(package.archive),
                "LOCAL_RELEASE_ROOT": _bash_path(release_root),
                "PERSISTENT_AGENT_DATA_ROOT": _bash_path(persistent),
                "ENVIRONMENT_AUTHORITY": _bash_path(environment),
                "RUNTIME_AUTHORITY": _bash_path(runtime),
                "EVIDENCE_DIR": _bash_path(evidence),
                "LOCAL_COMMAND_STATE": _bash_path(state),
                "OPERATOR": "runtime-test",
                "OPERATOR_CIDR": "127.0.0.1/32",
                "CANDIDATE_RELEASE_ID": "candidate",
                "ROLLBACK_RELEASE_ID": "rollback",
            }
        )
        result = subprocess.run(
            [str(BASH), "scripts/ops/rehearse_launch_rollback.sh", "--local-rehearsal"],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        expected_status = expected["recovery"][1]
        assert result.returncode == expected_status, result.stderr + result.stdout
        records = [
            json.loads(line)
            for line in (evidence / "rollback-phases.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        actual = {
            record["phase"]: (record["status"], record["exit_code"])
            for record in records
        }
        assert actual == expected
        summary = json.loads(
            (evidence / "rollback-summary.json").read_text(encoding="utf-8")
        )
        assert summary["exit_code"] == expected_status
        assert summary["status"] == "failed"
        assert summary["recovery_status"] == "failed"
        assert summary["closed_verified"] is False
        assert summary["traffic_state"] == configuration["traffic_state"]
        restore_index = next(
            i for i, record in enumerate(records) if record["phase"] == "recovery:restore-watchdog"
        )
        summary_index = next(i for i, record in enumerate(records) if record["phase"] == "recovery")
        assert restore_index < summary_index

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(run_case, enumerate(cases)))


def test_local_selector_preparation_failure_runs_armed_recovery_without_false_claims(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    package = _build_closed_package(tmp_path / "package")
    evidence = tmp_path / "evidence"
    release_root = tmp_path / "release"
    persistent = tmp_path / "persistent"
    runtime = tmp_path / "runtime"
    maintenance = tmp_path / "maintenance"
    for path in (evidence, release_root, persistent, runtime, maintenance):
        path.mkdir(parents=True)
    # The three template copies mutate the local selector model before this
    # directory makes rm -f fail at the active-selector replacement boundary.
    (maintenance / "active-server.conf").mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    state = tmp_path / "state.json"
    env = os.environ.copy()
    env.update(
        {
            "KNOWN_GOOD_CLOSED": _bash_path(package.archive),
            "LOCAL_RELEASE_ROOT": _bash_path(release_root),
            "PERSISTENT_AGENT_DATA_ROOT": _bash_path(persistent),
            "ENVIRONMENT_AUTHORITY": _bash_path(environment),
            "RUNTIME_AUTHORITY": _bash_path(runtime),
            "EVIDENCE_DIR": _bash_path(evidence),
            "LOCAL_COMMAND_STATE": _bash_path(state),
            "LOCAL_MAINTENANCE_DIR": _bash_path(maintenance),
            "OPERATOR": "runtime-test",
            "OPERATOR_CIDR": "127.0.0.1/32",
            "CANDIDATE_RELEASE_ID": "candidate",
            "ROLLBACK_RELEASE_ID": "rollback",
        }
    )

    result = subprocess.run(
        [str(BASH), "scripts/ops/rehearse_launch_rollback.sh", "--local-rehearsal"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, result.stderr + result.stdout
    assert (maintenance / "http-context.conf").is_file()
    assert (maintenance / "server-enabled.conf").is_file()
    assert (maintenance / "server-disabled.conf").is_file()
    records = [
        json.loads(line)
        for line in (evidence / "rollback-phases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    verification_records = [
        record for record in records if record["phase"] == "record-and-verify-evidence"
    ]
    assert len(verification_records) == 1
    assert verification_records[0]["status"] == "passed"
    primary_failures = [
        record
        for record in records
        if record["status"] == "failed" and not record["phase"].startswith("recovery")
    ]
    assert [record["phase"] for record in primary_failures] == [
        "prepare-local-maintenance-model"
    ]
    assert records[-1]["phase"] == "recovery"
    assert records[-1]["status"] == "failed"
    assert records[-1]["exit_code"] == 1
    assert all(record["traffic_state"] == "unknown" for record in records)
    assert all(record.get("closed_verified") is not True for record in records)
    recovery_results = {
        record["phase"]: (record["status"], record["exit_code"])
        for record in records
        if record["phase"].startswith("recovery:")
    }
    for phase in (
        "stop-vl-nuxt",
        "prove-vl-nuxt-inactive",
        "stop-vl-agent",
        "prove-vl-agent-inactive",
        "verify-recovery-package",
        "install-closed-release",
        "verify-dependencies-units-daemon-reload",
        "start-vl-agent",
        "prove-vl-agent-active",
        "start-vl-nuxt",
        "prove-vl-nuxt-active",
        "verify-readiness-and-listeners",
        "verify-nginx-closed-boundary",
        "verify-browser-worker-cache",
        "restore-watchdog",
    ):
        assert recovery_results[f"recovery:{phase}"] == ("skipped", 0)
    assert not state.exists()


def test_live_mode_is_acknowledgement_and_authority_gated_without_live_claims():
    source = REHEARSE.read_text(encoding="utf-8")

    assert 'ACKNOWLEDGE_MAINTENANCE:-' in source
    assert "launch-safety-rollback" in source
    assert "ENVIRONMENT_AUTHORITY" in source
    assert "RUNTIME_AUTHORITY" in source
    assert "MOUNT_AUTHORITY" in source
    assert '"stage3_claim": false' in source
    assert '"live_sla_proven": false' in source
    assert '"observed_local_elapsed_seconds"' in source
    assert '"live_sla_proven": true' not in source


def test_archive_verifier_consumes_task31_package_and_sidecar(tmp_path: Path):
    package = _build_closed_package(tmp_path)
    module = _load_module("task44_verify_closed_release", VERIFY)

    evidence = module.verify_archive(package.archive, package.digest_file)

    assert evidence["archive_sha256"] == _sha256(package.archive)
    assert evidence["package_kind"] == "vl360-launch-release"
    assert evidence["launch_posture"] == "closed"
    assert set(evidence["required_members_verified"]) == REQUIRED_PACKAGE_MEMBERS
    assert evidence["member_digests_match_manifest"] is True
    assert evidence["persistent_paths"] == ["agent/data", "agent/data/sitemap-bundles"]
    assert evidence["developer_override_selected"] is False
    assert evidence["unlock_keys_present"] is False
    assert evidence["stage3_claim"] is False
    assert evidence["live_sla_proven"] is False


def test_archive_verifier_checks_sidecar_before_opening_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    package = _build_closed_package(tmp_path)
    module = _load_module("task44_verify_sidecar_first", VERIFY)
    opened = False

    def forbidden_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("archive opened before sidecar verification")

    package.archive.write_bytes(package.archive.read_bytes() + b"corrupt")
    monkeypatch.setattr(module.tarfile, "open", forbidden_open)

    with pytest.raises(ValueError, match="archive SHA-256 sidecar mismatch"):
        module.verify_archive(package.archive, package.digest_file)

    assert opened is False


def test_archive_verifier_rejects_agent_data_member(tmp_path: Path):
    package = _build_closed_package(tmp_path)
    injected = tmp_path / "injected.tar.gz"
    with tarfile.open(package.archive, "r:gz") as source, tarfile.open(injected, "w:gz") as target:
        for member in source.getmembers():
            target.addfile(member, source.extractfile(member) if member.isfile() else None)
        payload = b"must-not-ship\n"
        member = tarfile.TarInfo("agent/data/app.db")
        member.size = len(payload)
        import io

        target.addfile(member, io.BytesIO(payload))
    sidecar = injected.with_name(injected.name + ".sha256")
    sidecar.write_text(f"{_sha256(injected)}  {injected.name}\n", encoding="ascii")
    module = _load_module("task44_verify_agent_data", VERIFY)

    with pytest.raises(ValueError, match="persistent agent data"):
        module.verify_archive(injected, sidecar)


def test_cache_purge_policy_is_exact_and_protects_persistent_data():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))

    assert set(policy["required_paths"]) == {
        "web-nuxt/.output",
        "web-nuxt/.nuxt",
        "web-nuxt/.cache",
    }
    assert set(policy["protected_paths"]) >= {"agent/data", "agent/data/sitemap-bundles"}
    assert policy["reject_absolute_paths"] is True
    assert policy["reject_parent_segments"] is True
    assert policy["reject_symlinks"] is True


def test_cache_purge_removes_only_explicit_runtime_paths(tmp_path: Path):
    module = _load_module("task44_purge_runtime", PURGE)
    root = tmp_path / "release"
    for relative in ("web-nuxt/.output", "web-nuxt/.nuxt", "web-nuxt/.cache"):
        path = root / relative
        path.mkdir(parents=True)
        (path / "stale").write_bytes(relative.encode("ascii"))
    protected = root / "agent" / "data" / "sitemap-bundles" / "bundle" / "metadata.json"
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b"immutable evidence\n")
    unrelated = root / "web-nuxt" / "public" / "keep.txt"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_bytes(b"keep\n")
    before = _sha256(protected)

    evidence = module.purge_runtime(root, POLICY)

    assert [item["path"] for item in evidence["paths"]] == [
        "web-nuxt/.output",
        "web-nuxt/.nuxt",
        "web-nuxt/.cache",
    ]
    assert all(item["status"] == "removed" for item in evidence["paths"])
    assert _sha256(protected) == before
    assert unrelated.read_bytes() == b"keep\n"


@pytest.mark.parametrize("unsafe", ["../outside", "/absolute", "agent/data"])
def test_cache_purge_rejects_escape_absolute_and_protected_paths(
    tmp_path: Path, unsafe: str
):
    module = _load_module(f"task44_purge_unsafe_{unsafe.replace('/', '_')}", PURGE)
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    policy["required_paths"] = [unsafe]
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    root = tmp_path / "release"
    root.mkdir()

    with pytest.raises(ValueError):
        module.purge_runtime(root, policy_path)


def test_phase_recorder_appends_truthful_local_only_evidence(tmp_path: Path):
    module = _load_module("task44_phase_recorder", RECORDER)

    first = module.append_phase(tmp_path, phase="record-and-verify-evidence", status="passed")
    second = module.append_phase(
        tmp_path,
        phase="recovery:verify-recovery-package",
        status="failed",
        exit_code=37,
        traffic_state="drained",
    )
    records = [json.loads(line) for line in (tmp_path / "rollback-phases.jsonl").read_text().splitlines()]

    assert records == [first, second]
    assert all(record["stage3_claim"] is False for record in records)
    assert all(record["live_sla_proven"] is False for record in records)
    assert all(record["observed_local_elapsed_seconds"] == 0.0 for record in records)
    assert second["exit_code"] == 37
    assert second["traffic_state"] == "drained"


def test_installer_uses_one_verifier_and_persistent_safe_tree_swap():
    source = INSTALL.read_text(encoding="utf-8")

    verify_index = source.index("verify_closed_release.py")
    extract_index = source.index("tar ")
    detach_index = source.index("detach-agent-data", extract_index)
    swap_index = source.index("swap-release-root", extract_index)
    restore_index = source.index("restore-bind-agent-data", extract_index)
    mount_verify_index = source.index("verify-agent-data-mount", extract_index)

    assert verify_index < extract_index < detach_index < swap_index < restore_index < mount_verify_index
    assert "agent/data/sitemap-bundles" in source
    assert "trap install_recovery" in source


def test_recovery_preserves_original_exit_and_never_reopens():
    source = REHEARSE.read_text(encoding="utf-8")
    recovery = source.split("keep_maintenance_and_recover()", 1)[1].split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]

    assert 'original_status="${1:-1}"' in recovery
    assert 'exit "$original_status"' in recovery
    assert "verify-recovery-package" in recovery
    assert "install-closed-release" in recovery
    assert "verify-browser-worker-cache" in recovery
    assert "maintenance_mode.sh disable" not in recovery
    assert set(("passed", "failed", "skipped")) <= set(source.split())


def test_post_reopen_recovery_redrains_before_package_recovery():
    source = REHEARSE.read_text(encoding="utf-8")
    recovery = source.split("keep_maintenance_and_recover()", 1)[1].split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]

    redrain = [
        recovery.index("maintenance-enable"),
        recovery.index("nginx-test-closed"),
        recovery.index("nginx-reload-closed"),
        recovery.index("maintenance-probe"),
    ]
    package_recovery = recovery.index("verify-recovery-package")

    assert redrain == sorted(redrain)
    assert max(redrain) < package_recovery
    assert "TRAFFIC_STATE=unknown" in recovery
    assert "TRAFFIC_STATE=open" in source
    assert "TRAFFIC_STATE=drained" in recovery


def test_local_stub_has_a_strict_privileged_command_allowlist():
    source = STUB.read_text(encoding="utf-8")
    module = _load_module("task44_local_command_stub", STUB)

    assert "ALLOWED_COMMANDS" in source
    assert "systemctl" in source
    assert "nginx" in source
    assert "findmnt" in source
    assert "mount" in source
    assert not any(command[0] in {"pip", "npm", "tar"} for command in module.ALLOWED_COMMANDS)


def test_local_stub_models_nuxt_readiness_and_listener_transitions(tmp_path: Path):
    module = _load_module("task44_local_command_stub_transitions", STUB)
    state = tmp_path / "state.json"

    assert module.run_stub(state, ("systemctl", "stop", "vl-nuxt")) == 0
    assert module.run_stub(state, ("vl360-readiness",)) != 0
    listener_state = json.loads(state.read_text(encoding="utf-8"))
    assert ":3000" not in listener_state["ss_output"]

    assert module.run_stub(state, ("systemctl", "start", "vl-nuxt")) == 0
    assert module.run_stub(state, ("vl360-readiness",)) == 0
    listener_state = json.loads(state.read_text(encoding="utf-8"))
    assert "127.0.0.1:3000" in listener_state["ss_output"]


def test_local_stub_models_agent_and_nuxt_service_state_transitions(tmp_path: Path):
    module = _load_module("task44_local_command_stub_service_order", STUB)
    state = tmp_path / "state.json"

    assert module.run_stub(state, ("systemctl", "stop", "vl-nuxt")) == 0
    assert module.run_stub(state, ("systemctl", "is-active", "--quiet", "vl-nuxt")) != 0
    assert module.run_stub(state, ("systemctl", "stop", "vl-agent")) == 0
    assert module.run_stub(state, ("systemctl", "is-active", "--quiet", "vl-agent")) != 0
    assert module.run_stub(state, ("systemctl", "start", "vl-agent")) == 0
    assert module.run_stub(state, ("systemctl", "is-active", "--quiet", "vl-agent")) == 0
    assert module.run_stub(state, ("systemctl", "start", "vl-nuxt")) == 0
    assert module.run_stub(state, ("systemctl", "is-active", "--quiet", "vl-nuxt")) == 0


def test_local_stub_merges_partial_service_overrides_with_deterministic_defaults(
    tmp_path: Path,
):
    module = _load_module("task44_local_command_stub_service_merge", STUB)
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps({"services": {"vl-watchdog.timer": "inactive"}}) + "\n",
        encoding="ascii",
    )

    assert module.run_stub(state, ("systemctl", "is-active", "--quiet", "vl-agent")) == 0
    assert module.run_stub(state, ("systemctl", "is-active", "--quiet", "vl-nuxt")) == 0
    assert (
        module.run_stub(
            state, ("systemctl", "is-active", "--quiet", "vl-watchdog.timer")
        )
        == 3
    )


@pytest.mark.parametrize(
    ("public_status", "operator_passed", "expected_status", "expected_state"),
    [
        (503, False, 1, "unknown"),
        (200, True, 1, "unknown"),
        (503, True, 0, "drained"),
    ],
)
def test_local_stub_requires_both_public_and_operator_proof_for_drained(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    public_status: int,
    operator_passed: bool,
    expected_status: int,
    expected_state: str,
):
    module = _load_module("task44_local_command_stub_boundary", STUB)
    state = tmp_path / f"state-{public_status}-{operator_passed}.json"
    state.write_text(
        json.dumps(
            {
                "maintenance": True,
                "maintenance_public_status": public_status,
                "maintenance_operator_contract_passed": operator_passed,
            }
        )
        + "\n",
        encoding="ascii",
    )

    status = module.run_stub(state, ("vl360-maintenance-probe",))
    payload = json.loads(capsys.readouterr().out)

    assert status == expected_status
    assert payload["public"]["status"] == public_status
    assert payload["operator"]["contract_passed"] is operator_passed
    assert payload["traffic_state"] == expected_state


def test_local_stub_requires_exact_findmnt_mountpoint_form(tmp_path: Path):
    module = _load_module("task44_local_command_stub_mountpoint", STUB)
    state = tmp_path / "state.json"
    source = tmp_path / "persistent"
    target = tmp_path / "release" / "agent" / "data"
    source.mkdir()
    target.mkdir(parents=True)

    assert module.run_stub(state, ("mount", "--bind", str(source), str(target))) == 0
    assert module.run_stub(
        state, ("findmnt", "--json", "--mountpoint", str(target))
    ) == 0
    with pytest.raises(ValueError, match="allowlisted"):
        module.run_stub(state, ("findmnt", "--json", "--target", str(target)))


def test_local_rehearsal_uses_injected_authorities_instead_of_host_curl_or_pip():
    source = REHEARSE.read_text(encoding="utf-8")
    readiness = source.split("verify_readiness_and_listeners()", 1)[1].split(
        "verify_nginx_closed_boundary()", 1
    )[0]
    dependencies = source.split("verify_dependencies_units_daemon_reload()", 1)[1].split(
        "verify_readiness_and_listeners()", 1
    )[0]

    assert "LOCAL_READINESS_AUTHORITY" in source
    assert "LOCAL_LISTENER_AUTHORITY" in source
    assert "LOCAL_DEPENDENCY_AUTHORITY" in source
    local_readiness = readiness.split('if [ "$MODE" = "--local-rehearsal" ]; then', 1)[1].split(
        "elif curl", 1
    )[0]
    assert "curl " not in local_readiness
    assert "run_local_authority readiness" in local_readiness
    assert "validate_local_readiness_evidence" in readiness
    assert "python -m pip check" in dependencies
    assert "run_local_authority dependencies" in dependencies
    assert "verifier_args+=(--local-rehearsal)" in dependencies
    assert '"${verifier_args[@]}"' in dependencies


def test_local_rehearsal_allows_only_loopback_post_reopen_probe():
    source = REHEARSE.read_text(encoding="utf-8")
    post_reopen = source.split("CURRENT_PHASE=reopen-and-recover-watchdog", 1)[1].split(
        "trap - ERR", 1
    )[0]
    base_args, local_branch = post_reopen.split(
        'if [ "$MODE" = "--local-rehearsal" ]', 1
    )
    local_branch = local_branch.split("fi", 1)[0]

    assert "--local-rehearsal-base-url" not in base_args
    assert "--require-public-internal-404" not in base_args
    assert "post_reopen_probe_args+=(--local-rehearsal-base-url)" in local_branch
    assert "post_reopen_probe_args+=(--require-public-internal-404)" in local_branch
    assert '"${post_reopen_probe_args[@]}"' in post_reopen


def test_recovery_records_dependent_phases_as_skipped_after_redrain_failure():
    source = REHEARSE.read_text(encoding="utf-8")
    recovery = source.split("keep_maintenance_and_recover()", 1)[1].split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]

    assert "if [ \"$RECOVERY_CHAIN_OK\" = true ]; then" in recovery
    for phase in (
        "verify-recovery-package",
        "install-closed-release",
        "verify-dependencies-units-daemon-reload",
        "verify-readiness-and-listeners",
        "verify-nginx-closed-boundary",
        "verify-browser-worker-cache",
    ):
        assert f"{phase}" in recovery
    assert "record_recovery_result verify-recovery-package skipped 0" in recovery


def test_pre_reopen_maintenance_failure_redrains_and_restores_prior_watchdog_state():
    source = REHEARSE.read_text(encoding="utf-8")
    recovery = source.split("keep_maintenance_and_recover()", 1)[1].split(
        "CURRENT_PHASE=record-and-verify-evidence", 1
    )[0]
    enable = source.split("CURRENT_PHASE=enable-maintenance", 1)[1].split(
        "CURRENT_PHASE=stop-vl-nuxt", 1
    )[0]

    assert "MAINTENANCE_ADMISSION_ATTEMPTED=true" in enable
    assert "MAINTENANCE_ADMISSION_ATTEMPTED" in recovery
    assert 'if [ "$WATCHDOG_TIMER_WAS_ACTIVE" = true ]; then' in recovery
    assert '[ "$TRAFFIC_STATE" = drained ]' not in recovery.split(
        'if [ "$WATCHDOG_TIMER_WAS_ACTIVE" = true', 1
    )[1].split("fi", 1)[0]


def test_runbook_documents_provenance_gates_and_no_live_claim():
    source = RUNBOOK.read_text(encoding="utf-8")

    assert source.startswith("> STATUS: active")
    assert "SHA-256 sidecar is integrity evidence, not a signature" in source
    assert "provenance" in source.lower()
    assert "ACKNOWLEDGE_MAINTENANCE=launch-safety-rollback" in source
    assert "global noindex" in source.lower()
    assert "Stage 3" in source
    assert "live SLA" in source
    assert "H1" in source and "H2" in source
    assert "local rehearsal" in source.lower()


def test_bash_entrypoints_are_syntax_valid():
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")

    for path in (INSTALL, REHEARSE, OPS / "maintenance_mode.sh", OPS / "watchdog.sh"):
        result = subprocess.run(
            [str(BASH), "-n", str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{path}: {result.stderr}"
