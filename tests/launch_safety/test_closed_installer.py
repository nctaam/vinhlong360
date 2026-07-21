from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tarfile
import time

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
        "install-lock.json",
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


def _wait_for_path(path: Path, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {path}")


def _authority_lock_path(_kind: str, authority: Path) -> Path:
    canonical = os.path.normcase(os.path.realpath(authority))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return authority.parent / ".vl360-install-locks" / f"authority-{digest}.lock"


def _write_lock_owner(
    lock_dir: Path,
    *,
    pid: int,
    process_start_identity: str,
    attempt_id: str = "stale-attempt",
) -> None:
    lock_dir.mkdir(parents=True)
    (lock_dir / "owner.json").write_text(
        json.dumps(
            {
                "attempt_id": attempt_id,
                "pid": pid,
                "process_start_identity": process_start_identity,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


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


def _installer_command(
    package,
    case_root: Path,
    prepared,
    *,
    evidence_arg: str | None = None,
    runtime_arg: str | None = None,
) -> list[str]:
    release, persistent, evidence, *_ = prepared
    return [
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
        _bash_path(case_root / "runtime") if runtime_arg is None else runtime_arg,
        "--evidence-dir",
        _bash_path(evidence) if evidence_arg is None else evidence_arg,
        "--require-closed",
        "--local-rehearsal",
    ]


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
    args = _installer_command(
        package,
        case_root,
        prepared,
        evidence_arg=evidence_arg,
    )
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result


def _invoke_installer_args(prepared, args: list[str]):
    *_, values = prepared
    env = os.environ.copy()
    env.update(values)
    return subprocess.run(
        [str(BASH), "scripts/ops/install_closed_release.sh", *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


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


def test_sigkill_after_persistent_detach_is_recovered_before_retry_reset(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "sigkill-after-detach"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, values = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    detached = case_root / "detached"
    bash_env = case_root / "pause-after-detach.bash"
    bash_env.write_text(
        "mv() {\n"
        "  /usr/bin/mv \"$@\"\n"
        "  status=$?\n"
        f"  if [ \"$2\" = '{_bash_path(release / 'agent' / 'data')}' ] "
        f"&& [ \"$3\" = '{_bash_path(persistent)}' ]; then\n"
        f"    : > '{_bash_path(detached)}'\n"
        "    kill -9 \"$$\"\n"
        "  fi\n"
        "  return \"$status\"\n"
        "}\n",
        encoding="ascii",
    )
    env = os.environ.copy()
    env.update(values)
    env["BASH_ENV"] = _bash_path(bash_env)
    first = subprocess.Popen(
        _installer_command(closed_package, case_root, prepared),
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(detached)
        first_stdout, first_stderr = first.communicate(timeout=30)
    finally:
        if first.poll() is None:
            first.kill()

    assert first.returncode != 0, first_stderr + first_stdout
    assert not (release / "agent" / "data").exists()
    assert _snapshot_tree(persistent) == persistent_before

    retry = _invoke_installer(closed_package, case_root, prepared)

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    assert _snapshot_tree(persistent) == {}
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


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
    rbind_evidence = module.validate_findmnt_evidence(
        {"filesystems": [{**valid["filesystems"][0], "options": "rw,rbind"}]},
        expected_source=source,
        expected_target=target,
    )
    assert rbind_evidence["options"] == ["rbind", "rw"]
    with pytest.raises(ValueError, match="options"):
        module.validate_findmnt_evidence(
            {"filesystems": [{**valid["filesystems"][0], "options": "rw"}]},
            expected_source=source,
            expected_target=target,
        )


def test_findmnt_validation_normalizes_util_linux_bind_source_shape(monkeypatch):
    module = _load_module("task5_findmnt_realistic_bind", VERIFY)
    source = Path("/var/lib/vl360/agent/data")
    target = Path("/opt/vl360/current/agent/data")
    observed_source = f"/dev/mapper/vl-root[{source.as_posix()}]"
    monkeypatch.setattr(
        module,
        "_findmnt_device_matches_source",
        lambda device, expected: device == "/dev/mapper/vl-root"
        and expected == source.resolve(),
    )
    realistic = {
        "filesystems": [
            {
                "options": "rw,relatime",
                "source": observed_source,
                "target": target.as_posix(),
            }
        ]
    }

    evidence = module.validate_findmnt_evidence(
        realistic,
        expected_source=source,
        expected_target=target,
    )

    assert evidence["source"] == observed_source
    assert evidence["normalized_source"] == str(source.resolve())
    assert evidence["options"] == ["bind", "relatime", "rw"]
    assert evidence["raw_options"] == ["relatime", "rw"]
    with pytest.raises(ValueError, match="source"):
        module.validate_findmnt_evidence(
            {
                "filesystems": [
                    {
                        **realistic["filesystems"][0],
                        "source": "/dev/mapper/vl-root[/var/lib/vl360/other]",
                    }
                ]
            },
            expected_source=source,
            expected_target=target,
        )
    with pytest.raises(ValueError, match="device"):
        module.validate_findmnt_evidence(
            {
                "filesystems": [
                    {
                        **realistic["filesystems"][0],
                        "source": f"/dev/mapper/other[{source.as_posix()}]",
                    }
                ]
            },
            expected_source=source,
            expected_target=target,
        )
    with pytest.raises(ValueError, match="options"):
        module.validate_findmnt_evidence(
            {
                "filesystems": [
                    {**realistic["filesystems"][0], "options": "ro,relatime"}
                ]
            },
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


@pytest.mark.parametrize(
    ("failure_kind", "expected_code"),
    (("verification", 61), ("extraction", 62), ("dependency-hook", 19)),
)
def test_premutation_failure_removes_private_staging_root(
    tmp_path: Path,
    closed_package,
    failure_kind: str,
    expected_code: int,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"staging-cleanup-{failure_kind}"
    prepared = _prepare_case(case_root, closed_package)
    release, _, _, _, _, _, _ = prepared
    env_overrides = None
    if failure_kind == "dependency-hook":
        hook = case_root / "runtime" / "python-hook.sh"
        hook.write_text("#!/usr/bin/env bash\nexit 19\n", encoding="ascii")
        hook.chmod(0o755)
    else:
        bash_env = case_root / "premutation-failure.bash"
        if failure_kind == "verification":
            count_file = case_root / "verify-count"
            bash_env.write_text(
                "python() {\n"
                f"  if [ \"$1\" = '{_bash_path(VERIFY)}' ]; then\n"
                f"    count=$(cat '{_bash_path(count_file)}' 2>/dev/null || printf 0)\n"
                "    count=$((count + 1))\n"
                f"    printf '%s\\n' \"$count\" > '{_bash_path(count_file)}'\n"
                "    [ \"$count\" -ne 2 ] || return 61\n"
                "  fi\n"
                "  command python \"$@\"\n"
                "}\n",
                encoding="ascii",
            )
        else:
            bash_env.write_text("tar() { return 62; }\n", encoding="ascii")
        env_overrides = {"BASH_ENV": _bash_path(bash_env)}

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides=env_overrides,
    )

    assert result.returncode == expected_code, result.stderr + result.stdout
    assert not list(release.parent.glob(f".{release.name}.closed-stage.*"))
    assert not list(release.parent.glob(f".{release.name}.closed-old.*"))


def test_installer_extracts_only_pinned_verified_archive_bytes(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "archive-replacement"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, _, _ = prepared
    archive = case_root / "candidate.tar.gz"
    digest_file = case_root / "candidate.tar.gz.sha256"
    shutil.copy2(closed_package.archive, archive)
    verified_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    digest_file.write_text(
        f"{verified_digest}  {archive.name}\n", encoding="ascii"
    )
    package = type(closed_package)(
        archive=archive,
        digest_file=digest_file,
        manifest=closed_package.manifest,
    )

    replacement = case_root / "replacement.tar.gz"
    with tarfile.open(replacement, "w:gz") as malicious:
        marker = tarfile.TarInfo("replacement-marker.txt")
        marker_raw = b"unverified replacement\n"
        marker.size = len(marker_raw)
        malicious.addfile(marker, io.BytesIO(marker_raw))
        traversal = tarfile.TarInfo("../archive-escape.txt")
        traversal_raw = b"must never extract\n"
        traversal.size = len(traversal_raw)
        malicious.addfile(traversal, io.BytesIO(traversal_raw))
        symlink = tarfile.TarInfo("web-nuxt/.output/server/archive-link")
        symlink.type = tarfile.SYMTYPE
        symlink.linkname = "../../../../archive-escape.txt"
        malicious.addfile(symlink)
    replacement_digest = hashlib.sha256(replacement.read_bytes()).hexdigest()

    replacement_used = case_root / "replacement-used"
    extracted_digest = case_root / "extracted-archive.sha256"
    bash_env = case_root / "archive-replacement.bash"
    bash_env.write_text(
        "python() {\n"
        "  command python \"$@\"\n"
        "  status=$?\n"
        "  if [ \"$status\" -eq 0 ] && [ ! -f "
        f"'{_bash_path(replacement_used)}' ]; then\n"
        "    for argument in \"$@\"; do\n"
        "      if [ \"$argument\" = '--archive' ]; then\n"
        f"        cp -- '{_bash_path(replacement)}' '{_bash_path(archive)}'\n"
        f"        : > '{_bash_path(replacement_used)}'\n"
        "        break\n"
        "      fi\n"
        "    done\n"
        "  fi\n"
        "  return \"$status\"\n"
        "}\n"
        "tar() {\n"
        "  archive_path=''\n"
        "  previous=''\n"
        "  for argument in \"$@\"; do\n"
        "    if [ \"$previous\" = '-xzf' ]; then archive_path=\"$argument\"; break; fi\n"
        "    previous=\"$argument\"\n"
        "  done\n"
        f"  sha256sum \"$archive_path\" | cut -d' ' -f1 > '{_bash_path(extracted_digest)}'\n"
        "  command tar \"$@\"\n"
        "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert replacement_used.is_file()
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == replacement_digest
    assert extracted_digest.read_text(encoding="ascii").strip() == verified_digest
    assert not (release / "replacement-marker.txt").exists()
    assert not (case_root / "archive-escape.txt").exists()
    assert not (release / "web-nuxt" / ".output" / "server" / "archive-link").exists()
    assert not list(evidence.glob(".closed-archive-attempt.*"))


def test_same_target_concurrent_attempt_is_rejected_and_lock_is_released(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-target-concurrent"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, values = prepared
    entered = case_root / "first-hook-entered"
    release_hook = case_root / "release-first-hook"
    gate = case_root / "first-hook-gate"
    second_hook_entered = case_root / "second-hook-entered"
    hook = case_root / "runtime" / "python-hook.sh"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        f"if mkdir '{_bash_path(gate)}' 2>/dev/null; then\n"
        f"  : > '{_bash_path(entered)}'\n"
        f"  while [ ! -f '{_bash_path(release_hook)}' ]; do sleep 0.05; done\n"
        f"  rmdir '{_bash_path(gate)}'\n"
        "  exit 19\n"
        "fi\n"
        f": > '{_bash_path(second_hook_entered)}'\n"
        "exit 18\n",
        encoding="ascii",
    )
    hook.chmod(0o755)
    env = os.environ.copy()
    env.update(values)
    first = subprocess.Popen(
        _installer_command(closed_package, case_root, prepared),
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(entered)
        second_evidence = case_root / "second-evidence"
        second_evidence.mkdir()
        second = subprocess.run(
            _installer_command(
                closed_package,
                case_root,
                prepared,
                evidence_arg=_bash_path(second_evidence),
            ),
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        release_hook.touch()
        try:
            first_stdout, first_stderr = first.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            first.kill()
            first_stdout, first_stderr = first.communicate()

    assert second.returncode == 2, second.stderr + second.stdout
    assert "install-target-locked" in second.stderr
    assert not second_hook_entered.exists()
    second_lock = json.loads(
        (second_evidence / "install-lock.json").read_text(encoding="utf-8")
    )
    assert second_lock["status"] == "rejected"
    assert first.returncode == 19, first_stderr + first_stdout
    first_lock = json.loads(
        (evidence / "install-lock.json").read_text(encoding="utf-8")
    )
    assert first_lock["status"] == "released"
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent

    third_evidence = case_root / "third-evidence"
    third_evidence.mkdir()
    hook.write_text("#!/usr/bin/env bash\nexit 19\n", encoding="ascii")
    hook.chmod(0o755)
    third = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        evidence_arg=_bash_path(third_evidence),
    )
    assert third.returncode == 19, third.stderr + third.stdout
    assert "install-target-locked" not in third.stderr
    third_lock = json.loads(
        (third_evidence / "install-lock.json").read_text(encoding="utf-8")
    )
    assert third_lock["status"] == "released"


@pytest.mark.parametrize("shared_authority", ("release", "persistent", "systemd"))
def test_attempts_sharing_any_destructive_authority_are_excluded(
    tmp_path: Path, closed_package, shared_authority: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    first_root = tmp_path / f"overlap-{shared_authority}-first"
    second_root = tmp_path / f"overlap-{shared_authority}-second"
    first_prepared = _prepare_case(first_root, closed_package)
    second_prepared = _prepare_case(second_root, closed_package)
    (
        first_release,
        first_persistent,
        _,
        first_release_before,
        first_persistent_before,
        _,
        first_values,
    ) = first_prepared
    (
        second_release,
        second_persistent,
        second_evidence,
        second_release_before,
        second_persistent_before,
        _,
        second_values,
    ) = second_prepared
    first_runtime = first_root / "runtime"
    entered = first_root / "hook-entered"
    release_hook = first_root / "release-hook"
    hook_gate = first_root / "hook-gate"
    first_hook = first_runtime / "python-hook.sh"
    first_hook.write_text(
        "#!/usr/bin/env bash\n"
        f"if mkdir '{_bash_path(hook_gate)}' 2>/dev/null; then\n"
        f"  : > '{_bash_path(entered)}'\n"
        f"  while [ ! -f '{_bash_path(release_hook)}' ]; do sleep 0.05; done\n"
        f"  rmdir '{_bash_path(hook_gate)}'\n"
        "  exit 19\n"
        "fi\n"
        "exit 18\n",
        encoding="ascii",
    )
    first_hook.chmod(0o755)

    runtime_arg = None
    if shared_authority == "release":
        second_prepared = (
            first_release,
            second_persistent,
            second_evidence,
            first_release_before,
            second_persistent_before,
            second_prepared[5],
            second_values,
        )
        second_values["VL360_LOCAL_REHEARSAL_SENTINEL"] = first_values[
            "VL360_LOCAL_REHEARSAL_SENTINEL"
        ]
    elif shared_authority == "persistent":
        second_prepared = (
            second_release,
            first_persistent,
            second_evidence,
            second_release_before,
            first_persistent_before,
            second_prepared[5],
            second_values,
        )
    else:
        runtime_arg = _bash_path(first_runtime)
        for name in (
            "VL360_PYTHON_DEPENDENCY_HOOK",
            "VL360_NUXT_DEPENDENCY_HOOK",
            "VL360_UNIT_VERIFY_HOOK",
        ):
            second_values[name] = first_values[name]

    if shared_authority != "systemd":
        second_hook = second_root / "runtime" / "python-hook.sh"
        second_hook.write_text("#!/usr/bin/env bash\nexit 18\n", encoding="ascii")
        second_hook.chmod(0o755)

    first_env = os.environ.copy()
    first_env.update(first_values)
    first = subprocess.Popen(
        _installer_command(closed_package, first_root, first_prepared),
        cwd=ROOT,
        env=first_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(entered)
        second_env = os.environ.copy()
        second_env.update(second_values)
        second = subprocess.run(
            _installer_command(
                closed_package,
                second_root,
                second_prepared,
                runtime_arg=runtime_arg,
            ),
            cwd=ROOT,
            env=second_env,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        release_hook.touch()
        first_stdout, first_stderr = first.communicate(timeout=60)

    assert second.returncode == 2, second.stderr + second.stdout
    assert "install-target-locked" in second.stderr
    second_lock = json.loads(
        (second_evidence / "install-lock.json").read_text(encoding="utf-8")
    )
    assert second_lock["status"] == "rejected"
    assert first.returncode == 19, first_stderr + first_stdout
    assert _snapshot_tree(first_release) == first_release_before
    assert _snapshot_tree(first_persistent) == first_persistent_before
    assert _snapshot_tree(second_release) == second_release_before
    assert _snapshot_tree(second_persistent) == second_persistent_before


@pytest.mark.parametrize(
    ("first_role", "second_role"),
    (("release", "persistent"), ("evidence", "release")),
)
def test_same_canonical_authority_is_excluded_across_roles(
    tmp_path: Path,
    closed_package,
    first_role: str,
    second_role: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    first_root = tmp_path / f"cross-role-{first_role}-first"
    second_root = tmp_path / f"cross-role-{second_role}-second"
    first_prepared = _prepare_case(first_root, closed_package)
    second_prepared = _prepare_case(second_root, closed_package)
    first_release, _, first_evidence, _, _, _, first_values = first_prepared
    (
        second_release,
        second_persistent,
        second_evidence,
        second_release_before,
        second_persistent_before,
        second_hook_log,
        second_values,
    ) = second_prepared
    shared_authority = {
        "evidence": first_evidence,
        "release": first_release,
    }[first_role]
    if second_role == "persistent":
        second_prepared = (
            second_release,
            shared_authority,
            second_evidence,
            second_release_before,
            _snapshot_tree(shared_authority),
            second_hook_log,
            second_values,
        )
    else:
        second_prepared = (
            shared_authority,
            second_persistent,
            second_evidence,
            _snapshot_tree(shared_authority),
            second_persistent_before,
            second_hook_log,
            second_values,
        )
        second_values["VL360_LOCAL_REHEARSAL_SENTINEL"] = first_values[
            "VL360_LOCAL_REHEARSAL_SENTINEL"
        ]

    entered = first_root / "hook-entered"
    release_hook = first_root / "release-hook"
    first_hook = first_root / "runtime" / "python-hook.sh"
    first_hook.write_text(
        "#!/usr/bin/env bash\n"
        f": > '{_bash_path(entered)}'\n"
        f"while [ ! -f '{_bash_path(release_hook)}' ]; do sleep 0.05; done\n"
        "exit 19\n",
        encoding="ascii",
    )
    first_hook.chmod(0o755)
    second_hook_entered = second_root / "hook-entered"
    second_hook = second_root / "runtime" / "python-hook.sh"
    second_hook.write_text(
        "#!/usr/bin/env bash\n"
        f": > '{_bash_path(second_hook_entered)}'\n"
        "exit 18\n",
        encoding="ascii",
    )
    second_hook.chmod(0o755)

    first_env = os.environ.copy()
    first_env.update(first_values)
    first = subprocess.Popen(
        _installer_command(closed_package, first_root, first_prepared),
        cwd=ROOT,
        env=first_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(entered)
        shared_before = _snapshot_tree(shared_authority)
        second_env = os.environ.copy()
        second_env.update(second_values)
        second = subprocess.run(
            _installer_command(closed_package, second_root, second_prepared),
            cwd=ROOT,
            env=second_env,
            check=False,
            capture_output=True,
            text=True,
        )
        shared_after = _snapshot_tree(shared_authority)
    finally:
        release_hook.touch()
        first_stdout, first_stderr = first.communicate(timeout=60)

    assert second.returncode == 2, second.stderr + second.stdout
    assert "install-target-locked" in second.stderr
    assert not second_hook_entered.exists()
    assert shared_after == shared_before
    assert first.returncode == 19, first_stderr + first_stdout


def test_same_evidence_rejection_does_not_erase_active_attempt_evidence(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-evidence-concurrent"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, values = prepared
    entered = case_root / "hook-entered"
    release_hook = case_root / "release-hook"
    gate = case_root / "hook-gate"
    second_hook_entered = case_root / "second-hook-entered"
    hook = case_root / "runtime" / "python-hook.sh"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        f"if mkdir '{_bash_path(gate)}' 2>/dev/null; then\n"
        f"  : > '{_bash_path(entered)}'\n"
        f"  while [ ! -f '{_bash_path(release_hook)}' ]; do sleep 0.05; done\n"
        f"  rmdir '{_bash_path(gate)}'\n"
        "  exit 19\n"
        "fi\n"
        f": > '{_bash_path(second_hook_entered)}'\n"
        "exit 18\n",
        encoding="ascii",
    )
    hook.chmod(0o755)
    env = os.environ.copy()
    env.update(values)
    first = subprocess.Popen(
        _installer_command(closed_package, case_root, prepared),
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(entered)
        active_evidence = _snapshot_tree(evidence)
        second = subprocess.run(
            _installer_command(closed_package, case_root, prepared),
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        evidence_after_rejection = _snapshot_tree(evidence)
    finally:
        release_hook.touch()
        first_stdout, first_stderr = first.communicate(timeout=60)

    assert second.returncode == 2, second.stderr + second.stdout
    assert "install-evidence-locked" in second.stderr
    assert not second_hook_entered.exists()
    assert evidence_after_rejection == active_evidence
    assert first.returncode == 19, first_stderr + first_stdout
    final_lock = json.loads(
        (evidence / "install-lock.json").read_text(encoding="utf-8")
    )
    assert final_lock["status"] == "released"


def test_dead_evidence_lock_owner_is_reclaimed(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "dead-evidence-lock"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    stale_lock = _authority_lock_path("evidence", evidence)
    _write_lock_owner(stale_lock, pid=999999, process_start_identity="dead")

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert result.returncode == 19, result.stderr + result.stdout
    assert not stale_lock.exists()
    lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "released"
    assert lock["reclaimed_stale_locks"] >= 1


@pytest.mark.parametrize("owner_contents", (None, "{not-json\n"))
def test_ownerless_or_malformed_stale_evidence_lock_is_reclaimed(
    tmp_path: Path,
    closed_package,
    owner_contents: str | None,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "invalid-evidence-lock-owner"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    stale_lock = _authority_lock_path("evidence", evidence)
    stale_lock.mkdir(parents=True)
    if owner_contents is not None:
        (stale_lock / "owner.json").write_text(owner_contents, encoding="ascii")

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert result.returncode == 19, result.stderr + result.stdout
    assert not stale_lock.exists()
    lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "released"
    assert lock["reclaimed_stale_locks"] >= 1


def test_malformed_owner_with_live_process_identity_is_not_reclaimed(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "live-incomplete-evidence-lock-owner"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    identity_file = case_root / "holder-identity"
    stop_file = case_root / "stop-holder"
    holder = subprocess.Popen(
        [
            str(BASH),
            "-lc",
            (
                f"printf '%s %s\\n' \"$$\" \"$(awk '{{print $22}}' /proc/$$/stat)\" "
                f"> '{_bash_path(identity_file)}'; "
                f"while [ ! -f '{_bash_path(stop_file)}' ]; do sleep 0.05; done"
            ),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(identity_file)
        pid_text, start_identity = identity_file.read_text(encoding="ascii").split()
        live_lock = _authority_lock_path("evidence", evidence)
        live_lock.mkdir(parents=True)
        (live_lock / "owner.json").write_text(
            f'{{"pid":{int(pid_text)},'
            f'"process_start_identity":"{start_identity}"\n',
            encoding="ascii",
        )

        result = _invoke_installer(closed_package, case_root, prepared)
    finally:
        stop_file.touch()
        holder_stdout, holder_stderr = holder.communicate(timeout=30)

    assert holder.returncode == 0, holder_stderr + holder_stdout
    assert result.returncode == 2, result.stderr + result.stdout
    assert "install-evidence-locked" in result.stderr
    assert live_lock.is_dir()


def test_live_pid_with_mismatched_start_identity_is_reclaimed_safely(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "pid-reuse-lock"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    identity_file = case_root / "holder-identity"
    stop_file = case_root / "stop-holder"
    holder = subprocess.Popen(
        [
            str(BASH),
            "-lc",
            (
                f"printf '%s %s\\n' \"$$\" \"$(awk '{{print $22}}' /proc/$$/stat)\" "
                f"> '{_bash_path(identity_file)}'; "
                f"while [ ! -f '{_bash_path(stop_file)}' ]; do sleep 0.05; done"
            ),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(identity_file)
        pid_text, start_identity = identity_file.read_text(encoding="ascii").split()
        stale_lock = _authority_lock_path("evidence", evidence)
        _write_lock_owner(
            stale_lock,
            pid=int(pid_text),
            process_start_identity=f"{start_identity}-reused",
        )

        result = _invoke_installer(
            closed_package,
            case_root,
            prepared,
            failed_hook="python",
        )
    finally:
        stop_file.touch()
        holder_stdout, holder_stderr = holder.communicate(timeout=30)

    assert holder.returncode == 0, holder_stderr + holder_stdout
    assert result.returncode == 19, result.stderr + result.stdout
    assert not stale_lock.exists()
    lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "released"
    assert lock["reclaimed_stale_locks"] >= 1


def test_sigkill_style_multi_authority_leftovers_are_reclaimed(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "sigkill-leftovers"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    authorities = (
        ("evidence", evidence),
        ("release", release),
        ("persistent", persistent),
        ("systemd", case_root / "runtime" / "systemd-units"),
    )
    stale_locks = []
    for kind, authority in authorities:
        stale_lock = _authority_lock_path(kind, authority)
        _write_lock_owner(
            stale_lock,
            pid=999999,
            process_start_identity="dead",
            attempt_id="sigkill-attempt",
        )
        stale_locks.append(stale_lock)

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert result.returncode == 19, result.stderr + result.stdout
    assert not any(path.exists() for path in stale_locks)
    lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "released"
    assert lock["reclaimed_stale_locks"] >= len(stale_locks)


def test_reentrant_same_target_attempt_is_rejected_before_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "same-target-reentrant"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    nested_evidence = case_root / "nested-evidence"
    nested_evidence.mkdir()
    nested_code = case_root / "nested-code"
    nested_command = _installer_command(
        closed_package,
        case_root,
        prepared,
        evidence_arg=_bash_path(nested_evidence),
    )
    nested_shell = " ".join(shlex.quote(argument) for argument in nested_command[1:])
    hook = case_root / "runtime" / "python-hook.sh"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"${VL360_REENTRANT_CHILD:-}\" = true ]; then exit 18; fi\n"
        "VL360_REENTRANT_CHILD=true "
        f"{nested_shell} >/dev/null 2>&1\n"
        "nested_status=$?\n"
        f"printf '%s\\n' \"$nested_status\" > '{_bash_path(nested_code)}'\n"
        "exit 19\n",
        encoding="ascii",
    )
    hook.chmod(0o755)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 19, result.stderr + result.stdout
    assert nested_code.read_text(encoding="ascii").strip() == "2"
    nested_lock = json.loads(
        (nested_evidence / "install-lock.json").read_text(encoding="utf-8")
    )
    assert nested_lock["status"] == "rejected"
    outer_lock = json.loads(
        (evidence / "install-lock.json").read_text(encoding="utf-8")
    )
    assert outer_lock["status"] == "released"
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent


def test_distinct_target_attempts_can_hold_install_locks_concurrently(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    processes = []
    releases = []
    prepared_cases = []
    try:
        for index in range(2):
            case_root = tmp_path / f"distinct-target-{index}"
            prepared = _prepare_case(case_root, closed_package)
            entered = case_root / "hook-entered"
            release_hook = case_root / "release-hook"
            hook = case_root / "runtime" / "python-hook.sh"
            hook.write_text(
                "#!/usr/bin/env bash\n"
                f": > '{_bash_path(entered)}'\n"
                f"while [ ! -f '{_bash_path(release_hook)}' ]; do sleep 0.05; done\n"
                "exit 19\n",
                encoding="ascii",
            )
            hook.chmod(0o755)
            *_, values = prepared
            env = os.environ.copy()
            env.update(values)
            process = subprocess.Popen(
                _installer_command(closed_package, case_root, prepared),
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            processes.append(process)
            releases.append(release_hook)
            prepared_cases.append((prepared, entered))
        for _, entered in prepared_cases:
            _wait_for_path(entered)
    finally:
        for release_hook in releases:
            release_hook.touch()

    for process, (prepared, _) in zip(processes, prepared_cases, strict=True):
        stdout, stderr = process.communicate(timeout=60)
        assert process.returncode == 19, stderr + stdout
        release, persistent, evidence, before_release, before_persistent, _, _ = prepared
        lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
        assert lock["status"] == "released"
        assert _snapshot_tree(release) == before_release
        assert _snapshot_tree(persistent) == before_persistent


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


def test_environment_authority_bytes_are_pinned_before_dependency_hooks(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "environment-authority-race"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, _, values = prepared
    external = case_root / "external.env"
    admitted = external.read_bytes()
    entered = case_root / "hook-entered"
    release_hook = case_root / "release-hook"
    hook = case_root / "runtime" / "python-hook.sh"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        f": > '{_bash_path(entered)}'\n"
        f"while [ ! -f '{_bash_path(release_hook)}' ]; do sleep 0.05; done\n",
        encoding="ascii",
    )
    hook.chmod(0o755)
    env = os.environ.copy()
    env.update(values)
    process = subprocess.Popen(
        _installer_command(closed_package, case_root, prepared),
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(entered)
        external.write_text("INDEXING_UNLOCK_KEY=opened\n", encoding="ascii")
    finally:
        release_hook.touch()
        stdout, stderr = process.communicate(timeout=60)

    assert process.returncode == 0, stderr + stdout
    assert (release / ".env").read_bytes() == admitted
    assert b"opened" not in (release / ".env").read_bytes()
    for path in evidence.rglob("*"):
        if path.is_file():
            assert b"opened" not in path.read_bytes()


@pytest.mark.parametrize(
    "unlock_line",
    (
        'export INDEXING_UNLOCK_KEY = "task5-secret"\n',
        " \tINDEXING_UNLOCK_KEY\t=\t'task5-secret' \t\n",
        "INDEXING_UNLOCK_KEY = task5-secret   # accepted dotenv comment\n",
    ),
)
def test_installer_rejects_nonempty_dotenv_unlock_key_without_logging_secret(
    tmp_path: Path, closed_package, unlock_line: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "dotenv-unlock-key"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    (case_root / "external.env").write_text(unlock_line, encoding="ascii")

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2
    assert "unlock-keys-forbidden" in result.stderr
    assert "task5-secret" not in result.stdout + result.stderr
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    for path in evidence.rglob("*"):
        if path.is_file():
            assert b"task5-secret" not in path.read_bytes()


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


@pytest.mark.parametrize(
    ("case_name", "raw_args", "expected_error"),
    (
        (
            "unknown-before-evidence",
            ("--unknown", "--evidence-dir", "{evidence}"),
            "unknown-option",
        ),
        (
            "unknown-after-evidence",
            ("--evidence-dir", "{evidence}", "--unknown"),
            "unknown-option",
        ),
        (
            "missing-value-before-evidence",
            ("--archive", "--evidence-dir", "{evidence}"),
            "archive-value-required",
        ),
        (
            "missing-value-after-evidence",
            ("--evidence-dir", "{evidence}", "--archive"),
            "archive-value-required",
        ),
    ),
)
def test_same_evidence_retry_resets_before_strict_parse_failure(
    tmp_path: Path,
    closed_package,
    case_name: str,
    raw_args: tuple[str, ...],
    expected_error: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / case_name
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared

    first = _invoke_installer(closed_package, case_root, prepared)
    assert first.returncode == 0, first.stderr + first.stdout
    forensic_attempt = evidence / ".systemd-unit-attempt.parse-failure"
    forensic_attempt.mkdir()
    (forensic_attempt / "armed").write_text("armed\n", encoding="ascii")
    forensic_before = _snapshot_tree(forensic_attempt)
    evidence_arg = _bash_path_literal(evidence)
    args = [evidence_arg if value == "{evidence}" else value for value in raw_args]

    second = _invoke_installer_args(prepared, args)

    assert second.returncode == 2
    assert expected_error in second.stderr
    _assert_mutable_attempt_evidence_absent(evidence)
    assert _snapshot_tree(forensic_attempt) == forensic_before


def test_malformed_evidence_option_does_not_reset_following_directory(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "malformed-evidence-option"
    prepared = _prepare_case(case_root, closed_package)
    protected = case_root / "protected"
    (protected / "package").mkdir(parents=True)
    (protected / "install-summary.json").write_text("protected\n", encoding="ascii")
    (protected / "package" / "marker.txt").write_text("protected\n", encoding="ascii")
    protected_before = _snapshot_tree(protected)

    result = _invoke_installer_args(
        prepared,
        ["--evidence-dir", "--archive", _bash_path_literal(protected)],
    )

    assert result.returncode == 2
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
    assert "install-target-locked" not in second.stderr
    assert _snapshot_tree(release) == installed_release
    assert _snapshot_tree(unit_destination) == installed_units
    assert _unit_attempt_artifacts(evidence) == []
    lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "released"
