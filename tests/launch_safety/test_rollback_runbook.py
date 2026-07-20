from __future__ import annotations

import hashlib
import importlib.util
import json
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
    assert source.index("RECOVERY_TRAP_ARMED=true") > source.index("maintenance-probe")


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
