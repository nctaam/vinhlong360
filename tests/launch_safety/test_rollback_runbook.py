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
    maintenance_enable = source.index(
        "maintenance_select enable", source.index("CURRENT_PHASE=enable-maintenance")
    )

    assert armed < watchdog_stop
    assert trap < watchdog_stop
    assert trap < maintenance_enable


def test_drained_requires_full_public_and_operator_maintenance_proof():
    source = REHEARSE.read_text(encoding="utf-8")
    enable_block = source.split("CURRENT_PHASE=enable-maintenance", 1)[1].split(
        "CURRENT_PHASE=stop-vl-nuxt", 1
    )[0]

    assert "verify_maintenance_boundary" in enable_block
    assert "TRAFFIC_STATE=drained" in enable_block
    assert "maintenance-http-proof.json" in enable_block
    assert "public" in source.lower()
    assert "operator" in source.lower()

    drained = source.index("TRAFFIC_STATE=drained", source.index("CURRENT_PHASE=enable-maintenance"))
    proof = source.index("verify_maintenance_boundary", source.index("CURRENT_PHASE=enable-maintenance"))
    assert proof < drained


def test_local_maintenance_probe_propagates_its_exact_failure_status():
    source = REHEARSE.read_text(encoding="utf-8")
    probe = source.split("verify_maintenance_boundary()", 1)[1].split(
        "verify_browser_worker_cache()", 1
    )[0]

    assert "local probe_status=$?" in probe
    assert 'return "$probe_status"' in probe


def _bash_path(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if len(resolved) >= 3 and resolved[1:3] == ":/":
        return f"/{resolved[0].lower()}/{resolved[3:]}"
    return resolved


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
    bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if not bash.is_file():
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
        [str(bash), "-c", command],
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
    bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if not bash.is_file():
        pytest.skip("Git Bash is unavailable")

    package = _build_closed_package(tmp_path / "package")
    later_skips = {
        "recovery:verify-recovery-package": ("skipped", 0),
        "recovery:install-closed-release": ("skipped", 0),
        "recovery:verify-dependencies-units-daemon-reload": ("skipped", 0),
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
            [str(bash), "scripts/ops/rehearse_launch_rollback.sh", "--local-rehearsal"],
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
    detach_index = source.index("detach-agent-data")
    swap_index = source.index("swap-release-root")
    restore_index = source.index("restore-bind-agent-data")
    mount_verify_index = source.index("verify-agent-data-mount")

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
        "elif ! curl", 1
    )[0]
    assert "curl " not in local_readiness
    assert "run_local_authority readiness" in local_readiness
    assert "validate_local_readiness_evidence" in readiness
    assert "python -m pip check" in dependencies
    assert "run_local_authority dependencies" in dependencies


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
    bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if not bash.is_file():
        pytest.skip("Git Bash is unavailable")

    for path in (INSTALL, REHEARSE, OPS / "maintenance_mode.sh", OPS / "watchdog.sh"):
        result = subprocess.run(
            [str(bash), "-n", str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{path}: {result.stderr}"
