from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tarfile

import pytest

from tests.launch_safety.test_rollback_runbook import (
    _bash_path,
    _build_closed_package,
)


ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "scripts" / "ops"
INSTALL = OPS / "install_closed_release.sh"
VERIFY = OPS / "verify_closed_release.py"
BASH = Path(r"C:\Program Files\Git\bin\bash.exe")
RUNBOOK = ROOT / "docs" / "runbooks" / "launch-safety-rollback.md"
SYSTEMD_UNIT_NAMES = (
    "vl-agent.service",
    "vl-nuxt.service",
    "vl-bot.service",
    "vl-watchdog.service",
    "vl-watchdog.timer",
)


@pytest.fixture(scope="module")
def closed_package(tmp_path_factory: pytest.TempPathFactory):
    return _build_closed_package(tmp_path_factory.mktemp("task5-package"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _unit_attempt_artifacts(evidence: Path) -> list[Path]:
    return sorted(
        [
            *evidence.glob("systemd-unit-backup*"),
            *evidence.glob("systemd-unit-mutation-armed*"),
            *evidence.glob(".systemd-unit-attempt.*"),
        ]
    )


def _assert_mutable_attempt_evidence_absent(evidence: Path) -> None:
    for name in (
        "dependency-unit-checks.json",
        "install-summary.json",
        "install-recovery.json",
        "systemd-unit-cleanup.json",
        "findmnt-before.json",
        "findmnt-after.json",
        "findmnt-recovery.json",
        "persistent-before.json",
        "persistent-after.json",
        "persistent-recovery.json",
        "package",
        "staged",
        "installed",
    ):
        assert not (evidence / name).exists()


def _bash_path_literal(path: Path) -> str:
    raw = path.absolute().as_posix()
    if len(raw) >= 3 and raw[1:3] == ":/":
        return f"/{raw[0].lower()}/{raw[3:]}"
    return raw


def _prepare_case(tmp_path: Path, package, *, fail_after: str | None = None):
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    runtime = tmp_path / "runtime"
    release_data = release / "agent" / "data"
    release_data.mkdir(parents=True)
    persistent.mkdir()
    evidence.mkdir()
    runtime.mkdir()
    sentinel = tmp_path / ".vl360-local-rehearsal"
    sentinel.write_text("vinhlong360-local-rehearsal-v1\n", encoding="ascii")
    (release / "old-release-marker.txt").write_text("old-tree\n", encoding="ascii")
    (release / ".env").write_text("OLD_ENV=1\n", encoding="ascii")
    (release_data / "app.db").write_bytes(b"persistent-db\n")
    (release_data / "sitemap-bundles" / "batch" / "metadata.json").parent.mkdir(
        parents=True
    )
    (release_data / "sitemap-bundles" / "batch" / "metadata.json").write_bytes(
        b"persistent-sitemap\n"
    )
    before_release = _snapshot_tree(release)
    before_persistent = _snapshot_tree(persistent)

    hook_log = runtime / "hooks.log"
    hooks = {}
    for name, label in (
        ("python", "python-dependencies"),
        ("nuxt", "nuxt-production-dependencies"),
        ("units", "systemd-units"),
    ):
        hook = runtime / f"{name}-hook.sh"
        hook.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s|%s\\n' '{label}' \"$*\" >> \"$INSTALL_HOOK_LOG\"\n",
            encoding="ascii",
        )
        hook.chmod(0o755)
        hooks[name] = hook

    environment = tmp_path / "external.env"
    environment.write_text("SAFE_LOCAL=1\n", encoding="ascii")
    env = {
        "KNOWN_GOOD_CLOSED": _bash_path(package.archive),
        "RELEASE_ROOT": _bash_path(release),
        "PERSISTENT_AGENT_DATA_ROOT": _bash_path(persistent),
        "ENVIRONMENT_AUTHORITY": _bash_path(environment),
        "RUNTIME_AUTHORITY": _bash_path(runtime),
        "EVIDENCE_DIR": _bash_path(evidence),
        "INSTALL_HOOK_LOG": _bash_path(hook_log),
        "VL360_PYTHON_DEPENDENCY_HOOK": _bash_path(hooks["python"]),
        "VL360_NUXT_DEPENDENCY_HOOK": _bash_path(hooks["nuxt"]),
        "VL360_UNIT_VERIFY_HOOK": _bash_path(hooks["units"]),
        "VL360_LOCAL_REHEARSAL_SENTINEL": _bash_path(sentinel),
    }
    if fail_after is not None:
        env["VL360_INSTALL_FAIL_AFTER"] = fail_after
    return (
        release,
        persistent,
        evidence,
        before_release,
        before_persistent,
        hook_log,
        env,
    )


def _run_installer(
    package,
    case_root: Path,
    *,
    fail_after: str | None = None,
    failed_hook: str | None = None,
    include_sentinel: bool = True,
):
    prepared = _prepare_case(case_root, package, fail_after=fail_after)
    result = _invoke_installer(
        package,
        case_root,
        prepared,
        failed_hook=failed_hook,
        include_sentinel=include_sentinel,
    )
    return result, prepared


def _invoke_installer(
    package,
    case_root: Path,
    prepared,
    *,
    failed_hook: str | None = None,
    include_sentinel: bool = True,
    env_overrides: dict[str, str] | None = None,
    evidence_arg: str | None = None,
):
    release, persistent, evidence, before_release, before_persistent, _, values = prepared
    if failed_hook is not None:
        hook_path = case_root / "runtime" / f"{failed_hook}-hook.sh"
        hook_path.write_text(
            "#!/usr/bin/env bash\nexit 19\n",
            encoding="ascii",
        )
        hook_path.chmod(0o755)
    if not include_sentinel:
        values.pop("VL360_LOCAL_REHEARSAL_SENTINEL", None)
    env = os.environ.copy()
    env.update(values)
    if env_overrides is not None:
        env.update(env_overrides)
    args = [
        str(BASH),
        "scripts/ops/install_closed_release.sh",
        "--archive",
        _bash_path(package.archive),
        "--archive-digest-file",
        _bash_path(package.digest_file),
        "--release-root",
        _bash_path(release),
        "--persistent-agent-data-root",
        _bash_path(persistent),
        "--environment-authority",
        _bash_path(case_root / "external.env"),
        "--runtime-authority",
        _bash_path(case_root / "runtime"),
        "--evidence-dir",
        _bash_path(evidence) if evidence_arg is None else evidence_arg,
        "--require-closed",
        "--local-rehearsal",
    ]
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result


def _run_live_mount_failure_case(package, case_root: Path):
    prepared = _prepare_case(case_root, package)
    release, persistent, evidence, before_release, _, _, values = prepared
    runtime = case_root / "runtime"
    for name in (
        "install-python-dependencies",
        "install-nuxt-production-dependencies",
        "verify-systemd-units",
    ):
        hook = runtime / name
        hook.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="ascii")
        hook.chmod(0o755)
    for name in (
        "VL360_PYTHON_DEPENDENCY_HOOK",
        "VL360_NUXT_DEPENDENCY_HOOK",
        "VL360_UNIT_VERIFY_HOOK",
    ):
        values.pop(name, None)

    findmnt_count = case_root / "findmnt-count"
    umount_count = case_root / "umount-count"
    mount_authority = case_root / "mount-authority.sh"
    mount_authority.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "case \"$1\" in\n"
        "  findmnt)\n"
        f"    count=$(cat '{_bash_path(findmnt_count)}' 2>/dev/null || printf 0)\n"
        f"    printf '%s\\n' \"$((count + 1))\" > '{_bash_path(findmnt_count)}'\n"
        "    [ \"$count\" -eq 0 ] || exit 44\n"
        f"    source_path=$(cygpath -m '{_bash_path(persistent)}')\n"
        "    target_path=$(cygpath -m \"$4\")\n"
        "    printf '{\"filesystems\":[{\"source\":\"%s\",\"target\":\"%s\",\"options\":\"rw,bind\"}]}\\n' "
        "\"$source_path\" \"$target_path\"\n"
        "    ;;\n"
        "  umount)\n"
        f"    count=$(cat '{_bash_path(umount_count)}' 2>/dev/null || printf 0)\n"
        f"    printf '%s\\n' \"$((count + 1))\" > '{_bash_path(umount_count)}'\n"
        "    [ \"$count\" -eq 0 ] || exit 51\n"
        f"    cp -a -- \"$2\"/. '{_bash_path(persistent)}/'\n"
        "    find \"$2\" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +\n"
        "    ;;\n"
        "  mount)\n"
        "    cp -a -- \"$3\"/. \"$4\"/\n"
        "    ;;\n"
        "  *) exit 64 ;;\n"
        "esac\n",
        encoding="ascii",
    )
    mount_authority.chmod(0o755)

    env = os.environ.copy()
    env.update(values)
    result = subprocess.run(
        [
            str(BASH),
            "scripts/ops/install_closed_release.sh",
            "--archive",
            _bash_path(package.archive),
            "--archive-digest-file",
            _bash_path(package.digest_file),
            "--release-root",
            _bash_path(release),
            "--persistent-agent-data-root",
            _bash_path(persistent),
            "--environment-authority",
            _bash_path(case_root / "external.env"),
            "--runtime-authority",
            _bash_path(runtime),
            "--mount-authority",
            _bash_path(mount_authority),
            "--evidence-dir",
            _bash_path(evidence),
            "--require-closed",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result, prepared, before_release


def _run_live_recovery_verification_case(
    package,
    case_root: Path,
    *,
    primary_mount_failure: bool = False,
    corrupt_primary_mount: bool = False,
):
    prepared = _prepare_case(case_root, package)
    release, persistent, evidence, _, _, _, values = prepared
    runtime = case_root / "runtime"
    for name in (
        "install-python-dependencies",
        "install-nuxt-production-dependencies",
        "verify-systemd-units",
    ):
        hook = runtime / name
        hook.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="ascii")
        hook.chmod(0o755)
    for name in (
        "VL360_PYTHON_DEPENDENCY_HOOK",
        "VL360_NUXT_DEPENDENCY_HOOK",
        "VL360_UNIT_VERIFY_HOOK",
        "VL360_LOCAL_REHEARSAL_SENTINEL",
    ):
        values.pop(name, None)

    findmnt_count = case_root / "findmnt-count"
    mount_count = case_root / "mount-count"
    umount_count = case_root / "umount-count"
    mount_authority = case_root / "mount-authority.sh"
    primary_mount_code = 52 if primary_mount_failure else 0
    corrupt_command = (
        "    [ \"$count\" -ne 0 ] || printf 'corrupt\\n' >> \"$4/app.db\"\n"
        if corrupt_primary_mount
        else ""
    )
    mount_authority.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "case \"$1\" in\n"
        "  findmnt)\n"
        f"    count=$(cat '{_bash_path(findmnt_count)}' 2>/dev/null || printf 0)\n"
        f"    printf '%s\\n' \"$((count + 1))\" > '{_bash_path(findmnt_count)}'\n"
        f"    source_path=$(cygpath -m '{_bash_path(persistent)}')\n"
        "    target_path=$(cygpath -m \"$4\")\n"
        "    printf '{\"filesystems\":[{\"source\":\"%s\",\"target\":\"%s\",\"options\":\"rw,bind\"}]}\\n' "
        "\"$source_path\" \"$target_path\"\n"
        "    ;;\n"
        "  umount)\n"
        f"    count=$(cat '{_bash_path(umount_count)}' 2>/dev/null || printf 0)\n"
        f"    printf '%s\\n' \"$((count + 1))\" > '{_bash_path(umount_count)}'\n"
        f"    if [ -z \"$(find '{_bash_path(persistent)}' -mindepth 1 -print -quit)\" ]; then\n"
        f"      cp -a -- \"$2\"/. '{_bash_path(persistent)}/'\n"
        "    fi\n"
        "    find \"$2\" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +\n"
        "    ;;\n"
        "  mount)\n"
        f"    count=$(cat '{_bash_path(mount_count)}' 2>/dev/null || printf 0)\n"
        f"    printf '%s\\n' \"$((count + 1))\" > '{_bash_path(mount_count)}'\n"
        f"    if [ \"$count\" -eq 0 ] && [ {primary_mount_code} -ne 0 ]; then exit {primary_mount_code}; fi\n"
        "    cp -a -- \"$3\"/. \"$4\"/\n"
        + corrupt_command
        + "    ;;\n"
        "  *) exit 64 ;;\n"
        "esac\n",
        encoding="ascii",
    )
    mount_authority.chmod(0o755)

    env = os.environ.copy()
    env.update(values)
    result = subprocess.run(
        [
            str(BASH),
            "scripts/ops/install_closed_release.sh",
            "--archive",
            _bash_path(package.archive),
            "--archive-digest-file",
            _bash_path(package.digest_file),
            "--release-root",
            _bash_path(release),
            "--persistent-agent-data-root",
            _bash_path(persistent),
            "--environment-authority",
            _bash_path(case_root / "external.env"),
            "--runtime-authority",
            _bash_path(runtime),
            "--mount-authority",
            _bash_path(mount_authority),
            "--evidence-dir",
            _bash_path(evidence),
            "--require-closed",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result, prepared, findmnt_count


@pytest.mark.parametrize("fail_after", ["detach-agent-data", "swap-release-root"])
def test_postmutation_failure_restores_old_tree_persistent_bytes_and_authority(
    tmp_path: Path, closed_package, fail_after: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared = _run_installer(closed_package, tmp_path / fail_after, fail_after=fail_after)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared

    assert result.returncode == 73, result.stderr + result.stdout
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not list(release.parent.glob(f".{release.name}.closed-*"))
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rolled-back"
    assert recovery["failure_point"] == fail_after
    assert recovery["persistent_restored"] is True
    assert recovery["root_restored"] is True


def test_restore_bind_failure_after_local_move_rolls_back_without_data_loss(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared = _run_installer(
        closed_package,
        tmp_path / "restore-bind-agent-data",
        fail_after="restore-bind-agent-data",
    )
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared

    assert result.returncode == 73, result.stderr + result.stdout
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not list(release.parent.glob(f".{release.name}.closed-*"))
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rolled-back"
    assert recovery["failure_point"] == "restore-bind-agent-data"
    assert recovery["persistent_restored"] is True
    assert recovery["root_restored"] is True


def test_failed_recovery_umount_preserves_new_and_old_roots_and_persistent_bytes(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared, before_release = _run_live_mount_failure_case(
        closed_package,
        tmp_path / "recovery-umount-failure",
    )
    release, persistent, evidence, _, _, _, _ = prepared

    assert result.returncode == 44, result.stderr + result.stdout
    old_roots = list(release.parent.glob(f".{release.name}.closed-old.*"))
    assert len(old_roots) == 1
    expected_old_root = {
        name: raw
        for name, raw in before_release.items()
        if not name.startswith("agent/data/")
    }
    assert _snapshot_tree(old_roots[0]) == expected_old_root
    assert (release / "launch-release-manifest.json").is_file()
    assert (release / "agent" / "data" / "app.db").read_bytes() == b"persistent-db\n"
    assert (persistent / "app.db").read_bytes() == b"persistent-db\n"
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rollback-failed"
    assert recovery["persistent_restored"] is False
    assert recovery["root_restored"] is False


def test_local_rehearsal_requires_a_sentinel_beside_the_disposable_release_root(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared = _run_installer(
        closed_package,
        tmp_path / "missing-sentinel",
        include_sentinel=False,
    )
    release, persistent, _, before_release, before_persistent, _, _ = prepared

    assert result.returncode == 2
    assert "local-rehearsal-sentinel-required" in result.stderr
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent


def test_live_mode_rejects_injected_hook_overrides_before_any_mount_or_tree_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "live-hook-override"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, values = prepared
    runtime = case_root / "runtime"
    for name in (
        "install-python-dependencies",
        "install-nuxt-production-dependencies",
        "verify-systemd-units",
    ):
        hook = runtime / name
        hook.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="ascii")
        hook.chmod(0o755)
    mount_log = case_root / "mount.log"
    mount_authority = case_root / "mount-authority.sh"
    mount_authority.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{_bash_path(mount_log)}'\n"
        "exit 97\n",
        encoding="ascii",
    )
    mount_authority.chmod(0o755)
    env = os.environ.copy()
    env.update(values)

    result = subprocess.run(
        [
            str(BASH),
            "scripts/ops/install_closed_release.sh",
            "--archive",
            _bash_path(closed_package.archive),
            "--archive-digest-file",
            _bash_path(closed_package.digest_file),
            "--release-root",
            _bash_path(release),
            "--persistent-agent-data-root",
            _bash_path(persistent),
            "--environment-authority",
            _bash_path(case_root / "external.env"),
            "--runtime-authority",
            _bash_path(runtime),
            "--mount-authority",
            _bash_path(mount_authority),
            "--evidence-dir",
            _bash_path(evidence),
            "--require-closed",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "live-hook-override-forbidden" in result.stderr
    assert not mount_log.exists()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent


def test_primary_mount_failure_restores_old_root_then_verifies_recovery_mount(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared, findmnt_count = _run_live_recovery_verification_case(
        closed_package,
        tmp_path / "primary-mount-failure",
        primary_mount_failure=True,
    )
    release, _, evidence, before_release, _, _, _ = prepared

    assert result.returncode == 52, result.stderr + result.stdout
    assert _snapshot_tree(release) == before_release
    assert findmnt_count.read_text(encoding="ascii").strip() == "2"
    assert (evidence / "findmnt-recovery.json").is_file()
    assert (evidence / "persistent-recovery.json").is_file()
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rolled-back"
    assert recovery["persistent_restored"] is True
    assert recovery["root_restored"] is True


def test_recovery_rechecks_findmnt_and_bytes_after_post_remount_failure(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared, findmnt_count = _run_live_recovery_verification_case(
        closed_package,
        tmp_path / "post-remount-verification",
        corrupt_primary_mount=True,
    )
    release, _, evidence, before_release, _, _, _ = prepared

    assert result.returncode == 2, result.stderr + result.stdout
    assert _snapshot_tree(release) == before_release
    assert findmnt_count.read_text(encoding="ascii").strip() == "3"
    assert (evidence / "findmnt-recovery.json").is_file()
    assert (evidence / "persistent-recovery.json").is_file()
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rolled-back"


def test_verifier_flags_execute_config_unit_and_persistent_mount_checks(
    tmp_path: Path, closed_package
):
    module = _load_module("task5_verify_flags", VERIFY)
    root = tmp_path / "installed"
    root.mkdir()
    with tarfile.open(closed_package.archive, "r:gz") as archive:
        archive.extractall(root, filter="data")
    (root / "agent" / "data").mkdir(parents=True)
    persistent = tmp_path / "persistent"
    persistent.mkdir()

    evidence = module.verify_installed_root(
        root,
        persistent_agent_data_root=persistent,
        verify_config_ingress_unit_digests=True,
        verify_persistent_agent_data_mount=True,
        local_rehearsal=True,
    )

    assert evidence["config_ingress_unit_digests_verified"] is True
    assert evidence["persistent_agent_data_mount_verified"] is True
    assert evidence["persistent_agent_data_mount_mode"] == "local-rehearsal"


def test_verifier_rejects_live_persistent_check_without_findmnt_evidence(
    tmp_path: Path, closed_package
):
    module = _load_module("task5_verify_live_mount", VERIFY)
    root = tmp_path / "installed"
    root.mkdir()
    with tarfile.open(closed_package.archive, "r:gz") as archive:
        archive.extractall(root, filter="data")
    (root / "agent" / "data").mkdir(parents=True)
    persistent = tmp_path / "persistent"
    persistent.mkdir()

    with pytest.raises(ValueError, match="findmnt"):
        module.verify_installed_root(
            root,
            persistent_agent_data_root=persistent,
            verify_persistent_agent_data_mount=True,
        )


def test_findmnt_validation_requires_expected_source_target_and_rw_bind_options(
    tmp_path: Path,
):
    module = _load_module("task5_findmnt_validation", VERIFY)
    source = tmp_path / "persistent"
    target = tmp_path / "release" / "agent" / "data"
    source.mkdir()
    target.mkdir(parents=True)
    valid = {
        "filesystems": [
            {
                "options": "rw,bind",
                "source": str(source),
                "target": str(target),
            }
        ]
    }

    evidence = module.validate_findmnt_evidence(
        valid,
        expected_source=source,
        expected_target=target,
    )
    assert evidence["options"] == ["bind", "rw"]
    with pytest.raises(ValueError, match="options"):
        module.validate_findmnt_evidence(
            {"filesystems": [{**valid["filesystems"][0], "options": "rw"}]},
            expected_source=source,
            expected_target=target,
        )


def test_installer_runs_injected_staged_dependency_and_unit_hooks_and_matches_units(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared = _run_installer(closed_package, tmp_path / "success")
    release, persistent, evidence, _, _, hook_log, _ = prepared

    assert result.returncode == 0, result.stderr + result.stdout
    hook_lines = hook_log.read_text(encoding="ascii").splitlines()
    assert [line.split("|", 1)[0] for line in hook_lines] == [
        "python-dependencies",
        "nuxt-production-dependencies",
        "systemd-units",
    ]
    assert all(".closed-stage." in line for line in hook_lines[:2])
    unit_destination = tmp_path / "success" / "runtime" / "systemd-units"
    assert _bash_path(unit_destination) in hook_lines[2]
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["stage3_claim"] is False
    assert checks["live_sla_proven"] is False
    assert checks["results"] == {
        "python-dependencies": "passed",
        "nuxt-production-dependencies": "passed",
        "systemd-units": "passed",
    }

    manifest = json.loads(
        (release / "launch-release-manifest.json").read_text(encoding="utf-8")
    )
    for relative in (
        "ops/systemd/vl-agent.service",
        "ops/systemd/vl-nuxt.service",
        "ops/systemd/vl-bot.service",
        "ops/systemd/vl-watchdog.service",
        "ops/systemd/vl-watchdog.timer",
    ):
        raw = (release / relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["members"][relative]["sha256"]
        destination = unit_destination / Path(relative).name
        assert destination.read_bytes() == raw
    assert _snapshot_tree(persistent) == {}


def test_installer_records_failed_authority_hook_exit_and_stops_before_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared = _run_installer(
        closed_package,
        tmp_path / "failed-hook",
        failed_hook="nuxt",
    )
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared

    assert result.returncode == 19, result.stderr + result.stdout
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["results"] == {
        "python-dependencies": "passed",
        "nuxt-production-dependencies": "failed",
    }
    assert checks["exit_codes"] == {
        "python-dependencies": 0,
        "nuxt-production-dependencies": 19,
    }


def test_local_installer_full_success_records_every_authority_and_releases_old_tree(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, prepared = _run_installer(closed_package, tmp_path / "full-success")
    release, persistent, evidence, _, _, _, _ = prepared

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(
        (evidence / "install-summary.json").read_text(encoding="utf-8")
    )
    assert summary["persistent_events"] == [
        "detach-agent-data",
        "swap-release-root",
        "restore-bind-agent-data",
        "verify-agent-data-mount",
    ]
    assert (evidence / "package" / "closed-release.json").is_file()
    assert (evidence / "staged" / "closed-release.json").is_file()
    assert (evidence / "installed" / "closed-release.json").is_file()
    assert (evidence / "dependency-unit-checks.json").is_file()
    cleanup = json.loads(
        (evidence / "systemd-unit-cleanup.json").read_text(encoding="utf-8")
    )
    assert cleanup == {
        "exit_code": 0,
        "live_sla_proven": False,
        "observed_local_elapsed_seconds": 0.0,
        "schema_version": 1,
        "stage3_claim": False,
        "status": "passed",
    }
    assert (release / "launch-release-manifest.json").is_file()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))
    assert _snapshot_tree(persistent) == {}


def test_success_materializes_external_environment_without_packaging_or_logging_bytes(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "environment-authority"
    result, prepared = _run_installer(closed_package, case_root)
    release, _, evidence, _, _, _, _ = prepared
    external = case_root / "external.env"
    target = release / ".env"

    assert result.returncode == 0, result.stderr + result.stdout
    assert target.is_file() and not target.is_symlink()
    assert target.read_bytes() == external.read_bytes()
    if os.name != "nt":
        assert target.stat().st_mode & 0o077 == 0
    manifest = json.loads(
        (release / "launch-release-manifest.json").read_text(encoding="utf-8")
    )
    assert ".env" not in manifest["members"]
    for path in evidence.rglob("*"):
        if path.is_file():
            assert b"SAFE_LOCAL=1" not in path.read_bytes()


def test_runbook_local_success_command_creates_and_selects_required_authorities():
    source = RUNBOOK.read_text(encoding="utf-8")
    local = source.split("## Local rehearsal", 1)[1].split(
        "## Host execution gate", 1
    )[0]

    assert "vinhlong360-local-rehearsal-v1" in local
    assert "VL360_LOCAL_REHEARSAL_SENTINEL=/tmp/vl360/.vl360-local-rehearsal" in local
    assert "install-python-dependencies" in local
    assert "install-nuxt-production-dependencies" in local
    assert "verify-systemd-units" in local
    assert "VL360_PYTHON_DEPENDENCY_HOOK=/tmp/vl360/runtime/install-python-dependencies" in local
    assert "VL360_NUXT_DEPENDENCY_HOOK=/tmp/vl360/runtime/install-nuxt-production-dependencies" in local
    assert "VL360_UNIT_VERIFY_HOOK=/tmp/vl360/runtime/verify-systemd-units" in local


def test_same_evidence_retry_before_units_never_keeps_prior_rollback_state(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-evidence-before-units"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    unit_destination = case_root / "runtime" / "systemd-units"

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout
    installed_units = _snapshot_tree(unit_destination)

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="nuxt",
    )

    assert second.returncode == 19, second.stderr + second.stdout
    assert _snapshot_tree(unit_destination) == installed_units
    assert _unit_attempt_artifacts(evidence) == []
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["results"]["nuxt-production-dependencies"] == "failed"
    assert checks["exit_codes"]["nuxt-production-dependencies"] == 19


def test_same_evidence_retry_after_success_resets_pre_mutation_evidence(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-evidence-reset-python"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert second.returncode == 19, second.stderr + second.stdout
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["results"] == {"python-dependencies": "failed"}
    assert checks["exit_codes"] == {"python-dependencies": 19}
    for name in (
        "install-summary.json",
        "install-recovery.json",
        "systemd-unit-cleanup.json",
        "installed",
    ):
        assert not (evidence / name).exists()
    assert (evidence / "package").is_dir()
    assert (evidence / "staged").is_dir()


@pytest.mark.parametrize(
    ("invalid_authority", "expected_error"),
    (
        ("environment", "external-environment-authority-required"),
        ("runtime", "external-runtime-authority-required"),
        ("hook", "runtime-hook-authority-required"),
    ),
)
def test_same_evidence_retry_resets_before_local_admission_failure(
    tmp_path: Path,
    closed_package,
    invalid_authority: str,
    expected_error: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"same-evidence-pre-admission-{invalid_authority}"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout
    forensic_attempt = evidence / ".systemd-unit-attempt.pre-admission"
    (forensic_attempt / "backup").mkdir(parents=True)
    (forensic_attempt / "armed").write_text("armed\n", encoding="ascii")
    (forensic_attempt / "backup" / "metadata.json").write_text(
        "{}\n", encoding="ascii"
    )
    forensic_before = _snapshot_tree(forensic_attempt)

    if invalid_authority == "environment":
        (case_root / "external.env").unlink()
    elif invalid_authority == "runtime":
        (case_root / "runtime").rename(case_root / "invalid-runtime")
    else:
        (case_root / "runtime" / "python-hook.sh").unlink()

    second = _invoke_installer(closed_package, case_root, prepared)

    assert second.returncode == 2
    assert expected_error in second.stderr
    _assert_mutable_attempt_evidence_absent(evidence)
    assert _snapshot_tree(forensic_attempt) == forensic_before


def test_same_evidence_retry_resets_before_live_override_rejection(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-evidence-pre-admission-live-override"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, values = prepared

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout
    forensic_attempt = evidence / ".systemd-unit-attempt.live-override"
    forensic_attempt.mkdir()
    (forensic_attempt / "armed").write_text("armed\n", encoding="ascii")
    forensic_before = _snapshot_tree(forensic_attempt)

    mount_authority = case_root / "mount-authority.sh"
    mount_authority.write_text("#!/usr/bin/env bash\nexit 97\n", encoding="ascii")
    mount_authority.chmod(0o755)
    env = os.environ.copy()
    env.update(values)
    second = subprocess.run(
        [
            str(BASH),
            "scripts/ops/install_closed_release.sh",
            "--archive",
            _bash_path(closed_package.archive),
            "--archive-digest-file",
            _bash_path(closed_package.digest_file),
            "--release-root",
            _bash_path(release),
            "--persistent-agent-data-root",
            _bash_path(persistent),
            "--environment-authority",
            _bash_path(case_root / "external.env"),
            "--runtime-authority",
            _bash_path(case_root / "runtime"),
            "--mount-authority",
            _bash_path(mount_authority),
            "--evidence-dir",
            _bash_path(evidence),
            "--require-closed",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert second.returncode == 2
    assert "live-hook-override-forbidden" in second.stderr
    _assert_mutable_attempt_evidence_absent(evidence)
    assert _snapshot_tree(forensic_attempt) == forensic_before


def test_retry_rejects_symlinked_evidence_dir_without_deleting_target(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-evidence-symlink"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout
    evidence.rename(case_root / "first-evidence")
    protected = case_root / "protected-evidence"
    (protected / "package").mkdir(parents=True)
    (protected / "install-summary.json").write_text("protected\n", encoding="ascii")
    (protected / "package" / "marker.txt").write_text("protected\n", encoding="ascii")
    protected_before = _snapshot_tree(protected)
    try:
        evidence.symlink_to(protected, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        evidence_arg=_bash_path_literal(evidence),
    )

    assert second.returncode == 2
    assert "evidence-dir-symlink-forbidden" in second.stderr
    assert _snapshot_tree(protected) == protected_before


def test_same_evidence_retry_after_success_resets_rollback_evidence(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-evidence-reset-units"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="units",
    )

    assert second.returncode == 19, second.stderr + second.stdout
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["results"] == {
        "python-dependencies": "passed",
        "nuxt-production-dependencies": "passed",
        "systemd-units": "failed",
    }
    assert checks["exit_codes"] == {
        "python-dependencies": 0,
        "nuxt-production-dependencies": 0,
        "systemd-units": 19,
    }
    assert not (evidence / "install-summary.json").exists()
    assert not (evidence / "systemd-unit-cleanup.json").exists()
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rolled-back"
    assert recovery["failure_point"] == "install-systemd-units"
    assert recovery["systemd_units_restored"] is True
    assert not (evidence / "installed").exists()


def test_same_evidence_retry_during_units_restores_current_not_stale_destination(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-evidence-during-units"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    unit_destination = case_root / "runtime" / "systemd-units"
    unit_destination.mkdir()
    for name in SYSTEMD_UNIT_NAMES:
        (unit_destination / name).write_bytes(f"legacy-{name}\n".encode("ascii"))

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout
    installed_units = _snapshot_tree(unit_destination)
    installed_release = _snapshot_tree(release)
    installed_persistent = _snapshot_tree(persistent)

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="units",
    )

    assert second.returncode == 19, second.stderr + second.stdout
    assert _snapshot_tree(unit_destination) == installed_units
    assert _snapshot_tree(release) == installed_release
    assert _snapshot_tree(persistent) == installed_persistent
    assert _unit_attempt_artifacts(evidence) == []
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["results"]["systemd-units"] == "failed"
    assert checks["exit_codes"]["systemd-units"] == 19
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rolled-back"
    assert recovery["systemd_units_restored"] is True


def test_cleanup_failure_keeps_completed_root_and_units_consistent_and_retry_safe(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "cleanup-failure"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, _, _ = prepared
    unit_destination = case_root / "runtime" / "systemd-units"
    failure_used = case_root / "cleanup-failure-used"
    bash_env = case_root / "cleanup-failure.bash"
    bash_env.write_text(
        "rm() {\n"
        "for argument in \"$@\"; do\n"
        "  case \"$(basename -- \"$argument\")\" in\n"
        "    .systemd-unit-attempt.*)\n"
        f"      if [ ! -f '{_bash_path(failure_used)}' ]; then\n"
        f"        : > '{_bash_path(failure_used)}'\n"
        "        return 61\n"
        "      fi\n"
        "      ;;\n"
        "  esac\n"
        "done\n"
        "/usr/bin/rm \"$@\"\n"
        "}\n",
        encoding="ascii",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert first.returncode == 0, first.stderr + first.stdout
    assert failure_used.is_file()
    assert (release / "launch-release-manifest.json").is_file()
    assert not (release / "old-release-marker.txt").exists()
    installed_release = _snapshot_tree(release)
    installed_units = _snapshot_tree(unit_destination)
    for name in SYSTEMD_UNIT_NAMES:
        assert (unit_destination / name).read_bytes() == (
            release / "ops" / "systemd" / name
        ).read_bytes()
    cleanup = json.loads(
        (evidence / "systemd-unit-cleanup.json").read_text(encoding="utf-8")
    )
    assert cleanup["status"] == "failed"
    assert cleanup["exit_code"] == 61
    assert not list(evidence.glob(".systemd-unit-attempt.*/armed"))

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="nuxt",
    )

    assert second.returncode == 19, second.stderr + second.stdout
    assert _snapshot_tree(release) == installed_release
    assert _snapshot_tree(unit_destination) == installed_units
    assert _unit_attempt_artifacts(evidence) == []
