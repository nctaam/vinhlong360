from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import shlex
import signal
import stat
import subprocess
import sys
import tarfile
import time
import venv

import pytest

# Mỗi test ở đây spawn một tiến trình installer thật (~20s). 284 test trong file
# chiếm ~95 trong 128 phút của full suite. Marker này loại chúng khỏi vòng chạy
# local mặc định; CI truyền -m riêng nên vẫn chạy đủ.
pytestmark = pytest.mark.subprocess_heavy

from tests.launch_safety.test_rollback_runbook import (
    _bash_path,
    _build_closed_package,
)


ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "scripts" / "ops"
INSTALL = OPS / "install_closed_release.sh"
VERIFY = OPS / "verify_closed_release.py"


def _find_bash() -> Path:
    candidates = (
        os.environ.get("GIT_BASH"),
        r"C:\Program Files\Git\bin\bash.exe",
        shutil.which("bash"),
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return Path("bash-unavailable")


BASH = _find_bash()
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


@pytest.fixture
def tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("case")


@pytest.mark.skipif(os.name != "nt", reason="Windows legacy path budget only")
def test_closed_installer_temp_root_reserves_windows_legacy_path_budget(
    tmp_path: Path,
):
    authority = tmp_path / "private-cleanup-archive-false-success" / "external.env"
    authority_pin = _authority_lock_path("environment", authority) / "env"

    assert len(os.fspath(authority_pin)) < 260


@pytest.mark.skipif(os.name != "nt", reason="Git Bash process identity shim only")
def test_windows_process_identity_env_stabilizes_cross_process_stat_without_faking_liveness(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    env = os.environ.copy()
    env.update(_windows_process_identity_env(tmp_path))
    identity_file = tmp_path / "holder-identity"
    stop_file = tmp_path / "stop-holder"
    probe_command = (
        'kill -0 "$1" 2>/dev/null || exit 73; '
        "awk '{print $22}' \"/proc/$1/stat\""
    )
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
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_path(identity_file)
        pid_text, recorded_identity = identity_file.read_text(
            encoding="ascii"
        ).split()
        live_probe = subprocess.run(
            [str(BASH), "-lc", probe_command, "identity-probe", pid_text],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        dead_probe = subprocess.run(
            [str(BASH), "-lc", probe_command, "identity-probe", "999999"],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        stop_file.touch()
        holder_stdout, holder_stderr = holder.communicate(timeout=30)

    assert holder.returncode == 0, holder_stderr + holder_stdout
    assert live_probe.returncode == 0, live_probe.stderr + live_probe.stdout
    assert live_probe.stdout.strip() == recorded_identity
    assert dead_probe.returncode == 73, dead_probe.stderr + dead_probe.stdout


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


def _snapshot_topology(root: Path) -> dict[str, tuple[str, int, bytes | str | None]]:
    result: dict[str, tuple[str, int, bytes | str | None]] = {}

    def visit(path: Path, relative: str) -> None:
        observed = path.lstat()
        mode = stat.S_IMODE(observed.st_mode)
        if stat.S_ISLNK(observed.st_mode):
            result[relative] = ("symlink", mode, os.readlink(path))
            return
        if stat.S_ISREG(observed.st_mode):
            result[relative] = ("file", mode, path.read_bytes())
            return
        if stat.S_ISDIR(observed.st_mode):
            result[relative] = ("directory", mode, None)
            for child in sorted(path.iterdir(), key=lambda item: item.name):
                child_relative = (
                    child.name if relative == "." else f"{relative}/{child.name}"
                )
                visit(child, child_relative)
            return
        result[relative] = ("other", mode, None)

    visit(root, ".")
    return result


def _shell_function(source: str, name: str) -> str:
    start = source.index(f"{name}() {{")
    next_marker = {
        "verify_pinned_executable": "\n\nATTEMPT_ID=",
        "run_with_sanitized_executable_environment": "\n\ninvoke_pinned_executable()",
        "invoke_pinned_executable": "\n\ninvoke_mount_authority()",
    }[name]
    end = source.index(next_marker, start)
    return source[start:end]


def _pinned_executor_python(source: str) -> str:
    delimiter = "VL360_PINNED_EXECUTOR_PY"
    start = source.index(f"<<'{delimiter}'")
    start = source.index("\n", start) + 1
    end = source.index(f"\n{delimiter}\n", start)
    return source[start:end]


def _invoke_standalone_pinned_executor(
    pin_root: Path,
    role: str,
    digest: str,
    args: list[str],
    *,
    local_rehearsal: bool,
    bash_digest: str = "unused",
    bash_executor: Path | None = None,
    env_overrides: dict[str, str] | None = None,
    runner_prelude: str | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    source = INSTALL.read_text(encoding="utf-8")
    bash_authority = (bash_executor or BASH).resolve()
    if bash_digest == "unused":
        bash_digest = hashlib.sha256(bash_authority.read_bytes()).hexdigest()
    pin_paths = {
        "mount": pin_root / "mount",
        "python-dependency": pin_root / "python-dependency",
        "nuxt-dependency": pin_root / "nuxt-dependency",
        "unit-verify": pin_root / "unit-verify",
        "bash-interpreter": pin_root / "bash-interpreter",
    }
    assignments = "\n".join(
        (
            f"PINNED_MOUNT_AUTHORITY={shlex.quote(_bash_path(pin_paths['mount']))}",
            "MOUNT_AUTHORITY_SHA256=unused",
            "PINNED_PYTHON_DEPENDENCY_HOOK="
            f"{shlex.quote(_bash_path(pin_paths['python-dependency']))}",
            "PYTHON_DEPENDENCY_HOOK_SHA256=unused",
            "PINNED_NUXT_DEPENDENCY_HOOK="
            f"{shlex.quote(_bash_path(pin_paths['nuxt-dependency']))}",
            "NUXT_DEPENDENCY_HOOK_SHA256=unused",
            "PINNED_UNIT_VERIFY_HOOK="
            f"{shlex.quote(_bash_path(pin_paths['unit-verify']))}",
            "UNIT_VERIFY_HOOK_SHA256=unused",
            "PINNED_BASH_EXECUTOR="
            f"{shlex.quote(_bash_path(pin_paths['bash-interpreter']))}",
            f"BASH_EXECUTOR_SHA256={shlex.quote(bash_digest)}",
            f"EXECUTABLE_PIN_ROOT={shlex.quote(_bash_path(pin_root))}",
            f"LOCAL_REHEARSAL={'true' if local_rehearsal else 'false'}",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable)))}",
            f"BASH_EXECUTOR={shlex.quote(_bash_path(bash_authority))}",
            "ENV_EXECUTOR=/usr/bin/env",
        )
    )
    script = "\n".join(
        (
            "set -u",
            'invoke_python() { command "$PYTHON_EXECUTOR" "$@"; }',
            _shell_function(source, "verify_pinned_executable"),
            _shell_function(source, "run_with_sanitized_executable_environment"),
            _shell_function(source, "invoke_pinned_executable"),
            assignments,
            runner_prelude or ":",
            f"invoke_pinned_executable {shlex.quote(role)} {shlex.quote(digest)} -- \"$@\"",
        )
    )
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    runner = pin_root / "standalone-pinned-executor.sh"
    runner.write_text(script + "\n", encoding="utf-8")
    runner.chmod(0o755)
    return subprocess.run(
        [str(BASH), _bash_path(runner), *args],
        cwd=ROOT,
        env=env,
        input=stdin,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_local_python_executor(path: Path, body: str) -> Path:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        f"REAL_PYTHON={shlex.quote(_bash_path(Path(sys.executable).resolve()))}\n"
        f"{body}",
        encoding="ascii",
    )
    path.chmod(0o755)
    return path.resolve()


def _run_bash_script(path: Path, script: str) -> subprocess.CompletedProcess[str]:
    path.write_text(script + "\n", encoding="utf-8")
    return subprocess.run(
        [str(BASH), _bash_path(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _stale_local_reconciliation_source() -> str:
    source = INSTALL.read_text(encoding="utf-8")
    return source[
        source.index("inspect_stale_mount()") : source.index("record_install_lock()")
    ]


def _write_mv_side_effect_fault(
    path: Path,
    *,
    marker: Path,
    condition: str,
    failure: str,
) -> Path:
    path.write_text(
        "mv() {\n"
        "  local source destination status\n"
        "  if [ \"${1:-}\" = -- ]; then\n"
        "    source=${2:-}\n"
        "    destination=${3:-}\n"
        "  else\n"
        "    source=${1:-}\n"
        "    destination=${2:-}\n"
        "  fi\n"
        '  /usr/bin/mv "$@"\n'
        "  status=$?\n"
        f"  if [ \"$status\" -eq 0 ] && [[ {condition} ]] "
        f"&& [ ! -f '{_bash_path(marker)}' ]; then\n"
        f"    : > '{_bash_path(marker)}'\n"
        f"    {failure}\n"
        "  fi\n"
        "  return \"$status\"\n"
        "}\n",
        encoding="ascii",
    )
    return path


def _write_mv_no_effect_success(
    path: Path, *, marker: Path, condition: str
) -> Path:
    path.write_text(
        "mv() {\n"
        "  local source destination\n"
        "  if [ \"${1:-}\" = -- ]; then\n"
        "    source=${2:-}\n"
        "    destination=${3:-}\n"
        "  else\n"
        "    source=${1:-}\n"
        "    destination=${2:-}\n"
        "  fi\n"
        f"  if [[ {condition} ]] && [ ! -f '{_bash_path(marker)}' ]; then\n"
        f"    : > '{_bash_path(marker)}'\n"
        "    return 0\n"
        "  fi\n"
        '  /usr/bin/mv "$@"\n'
        "}\n",
        encoding="ascii",
    )
    return path


def _write_release_rm_false_success(
    path: Path,
    *,
    journal: Path,
    marker: Path,
    partial: bool,
) -> Path:
    partial_action = (
        '      /usr/bin/rm -f -- "$argument/launch-release-manifest.json"\n'
        if partial
        else ""
    )
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "for argument in \"$@\"; do\n"
        "  case \"$(basename -- \"$argument\")\" in\n"
        "    .release.closed-candidate-cleanup.*)\n"
        f"      if [ -f '{_bash_path(journal)}' ] "
        "&& grep -Fq '\"stage\": \"recovery-remove-release-root-armed\"' "
        f"'{_bash_path(journal)}' && [ ! -f '{_bash_path(marker)}' ]; then\n"
        f"        : > '{_bash_path(marker)}'\n"
        f"{partial_action}"
        "        exit 0\n"
        "      fi\n"
        "      ;;\n"
        "  esac\n"
        "done\n"
        'exec /usr/bin/rm "$@"\n',
        encoding="ascii",
    )
    path.chmod(0o755)
    return path


def _write_cleanup_rm_fault_executor(
    path: Path,
    *,
    basename_pattern: str,
    marker: Path,
    status: int,
    partial_relative: str | None = None,
) -> Path:
    partial_action = (
        f'      /usr/bin/rm -f -- "$argument/{partial_relative}"\n'
        if partial_relative is not None
        else ""
    )
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "for argument in \"$@\"; do\n"
        "  case \"$(basename -- \"$argument\")\" in\n"
        f"    {basename_pattern})\n"
        f"      if [ ! -f '{_bash_path(marker)}' ]; then\n"
        f"        : > '{_bash_path(marker)}'\n"
        f"{partial_action}"
        f"        exit {status}\n"
        "      fi\n"
        "      ;;\n"
        "  esac\n"
        "done\n"
        'exec /usr/bin/rm "$@"\n',
        encoding="ascii",
    )
    path.chmod(0o755)
    return path.resolve()


def _write_private_staging_owner(
    owner: Path,
    stage: Path,
    *,
    attempt_id: str = "a" * 32,
    nonce: str = "b" * 64,
    root_identity: str | None = None,
) -> Path:
    observed = stage.stat(follow_symlinks=False)
    payload = {
        "attempt_id": attempt_id,
        "nonce": nonce,
        "pid": int(stage.name.rsplit(".", 1)[1]),
        "role": "private-staging",
        "root_identity": root_identity or f"{observed.st_dev}:{observed.st_ino}",
    }
    owner.write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="ascii",
    )
    return owner


def _unit_attempt_artifacts(evidence: Path) -> list[Path]:
    return sorted(
        [
            *evidence.glob("systemd-unit-backup*"),
            *evidence.glob("systemd-unit-mutation-armed*"),
            *evidence.glob(".systemd-unit-attempt.*"),
        ]
    )


def _assert_python_dependency_hook_failed(evidence: Path) -> None:
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["results"] == {"python-dependencies": "failed"}
    assert checks["exit_codes"] == {"python-dependencies": 19}


def _assert_mutable_attempt_evidence_absent(evidence: Path) -> None:
    for name in (
        "dependency-unit-checks.json",
        "install-summary.json",
        "install-recovery.json",
        "systemd-unit-cleanup.json",
        "findmnt-before.json",
        "findmnt-after-umount.json",
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


def _windows_process_identity_env(case_root: Path) -> dict[str, str]:
    bash_env = case_root / "stable-process-identity.bash"
    bash_env.write_text(
        "awk() {\n"
        "  if [ \"$#\" -eq 2 ] && [ \"$1\" = '{print $22}' ]; then\n"
        "    case \"$2\" in\n"
        "      /proc/[0-9]*/stat)\n"
        "        local pid=${2#/proc/}\n"
        "        pid=${pid%/stat}\n"
        "        case \"$pid\" in\n"
        "          ''|*[!0-9]*) ;;\n"
        "          *) printf 'vl360-test-pid-%s\\n' \"$pid\"; return 0 ;;\n"
        "        esac\n"
        "        ;;\n"
        "    esac\n"
        "  fi\n"
        "  command awk \"$@\"\n"
        "}\n",
        encoding="ascii",
    )
    return {"BASH_ENV": _bash_path(bash_env)}


def _wait_for_path(path: Path, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {path}")


def _start_file_backed_process(
    command: list[str], *, case_root: Path, env: dict[str, str]
) -> tuple[subprocess.Popen[str], Path, Path]:
    stdout_path = case_root / "background-installer.stdout"
    stderr_path = case_root / "background-installer.stderr"
    with (
        stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_stream,
        stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_stream,
    ):
        popen_kwargs: dict[str, object] = {}
        if os.name == "nt":
            popen_kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
            )
        else:
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=stdout_stream,
            stderr=stderr_stream,
            text=True,
            **popen_kwargs,
        )
    return process, stdout_path, stderr_path


def _read_file_backed_output(
    stdout_path: Path, stderr_path: Path
) -> tuple[str, str]:
    return (
        stdout_path.read_text(encoding="utf-8", errors="replace"),
        stderr_path.read_text(encoding="utf-8", errors="replace"),
    )


def _finish_file_backed_process(
    process: subprocess.Popen[str],
    stdout_path: Path,
    stderr_path: Path,
    *,
    timeout: float,
) -> tuple[str, str, list[str]]:
    errors: list[str] = []
    try:
        process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        errors.append(
            f"background installer did not exit within {timeout:g} seconds"
        )
        try:
            _, _, cleanup_errors = _terminate_owned_installer_process(process)
        except Exception as exc:
            errors.append(f"owned cleanup failed: {type(exc).__name__}: {exc}")
        else:
            errors.extend(cleanup_errors)
    except Exception as exc:
        errors.append(f"background installer wait failed: {type(exc).__name__}: {exc}")
        try:
            _, _, cleanup_errors = _terminate_owned_installer_process(process)
        except Exception as cleanup_exc:
            errors.append(
                "owned cleanup failed: "
                f"{type(cleanup_exc).__name__}: {cleanup_exc}"
            )
        else:
            errors.extend(cleanup_errors)
    try:
        stdout, stderr = _read_file_backed_output(stdout_path, stderr_path)
    except OSError as exc:
        errors.append(f"background output read failed: {type(exc).__name__}: {exc}")
        stdout, stderr = "", ""
    return stdout, stderr, errors


def _finish_file_backed_processes(
    records: list[tuple[subprocess.Popen[str], Path, Path]], *, timeout: float
) -> list[tuple[subprocess.Popen[str], str, str, list[str]]]:
    completed = []
    for process, stdout_path, stderr_path in records:
        stdout, stderr, errors = _finish_file_backed_process(
            process, stdout_path, stderr_path, timeout=timeout
        )
        completed.append((process, stdout, stderr, errors))
    return completed


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


def _private_attempt_artifacts(case_root: Path, evidence: Path) -> dict[str, list[Path]]:
    private_tmp = case_root / "private-tmp"
    lock_artifacts = []
    for lock_root in case_root.rglob(".vl360-install-locks"):
        lock_artifacts.extend(sorted(lock_root.iterdir()))
    return {
        "archive": sorted(evidence.glob(".closed-archive-attempt.*")),
        "pin": sorted(private_tmp.glob("vl360-executable-pins.*")),
        "lock": lock_artifacts,
    }


def _cleanup_failure_bash_env(
    case_root: Path,
    evidence: Path,
    cleanup_kind: str,
    failure_mode: str,
) -> tuple[Path, Path | None]:
    matched = case_root / f"{cleanup_kind}-{failure_mode}-matched"
    removed = case_root / f"{cleanup_kind}-{failure_mode}-removed"
    fsync_failed = case_root / f"{cleanup_kind}-{failure_mode}-fsync-failed"
    if cleanup_kind == "archive":
        basename_pattern = ".closed-archive-attempt.*"
        fsync_parent = _bash_path(evidence)
    elif cleanup_kind == "pin":
        basename_pattern = "vl360-executable-pins.*"
        fsync_parent = _bash_path(case_root / "private-tmp")
    else:
        basename_pattern = "*.lock.released.*"
        fsync_parent = ".vl360-install-locks"

    rm_action = {
        "false-success": "return 0",
        "nonzero": "return 61",
        "fsync": (
            '/usr/bin/rm "$@"\n'
            "  status=$?\n"
            "  [ \"$status\" -ne 0 ] || "
            f": > '{_bash_path(removed)}'\n"
            "  return \"$status\""
        ),
    }[failure_mode]
    python_executor = None
    if failure_mode == "fsync":
        if cleanup_kind == "lock":
            parent_match = (
                'if [ "$(basename -- "$argument")" = '
                f"'{fsync_parent}' ]; then"
            )
        else:
            parent_match = f"if [ \"$argument\" = '{fsync_parent}' ]; then"
        python_executor = _write_local_python_executor(
            case_root / f"{cleanup_kind}-{failure_mode}-python",
            f"  if [ \"${{1:-}}\" = - ] && [ -f '{_bash_path(removed)}' ] "
            f"&& [ ! -f '{_bash_path(fsync_failed)}' ]; then\n"
            "    for argument in \"$@\"; do\n"
            f"      {parent_match}\n"
            f"        : > '{_bash_path(fsync_failed)}'\n"
            "        exit 63\n"
            "      fi\n"
            "    done\n"
            "  fi\n"
            "command \"$REAL_PYTHON\" \"$@\"\n",
        )

    bash_env = case_root / f"{cleanup_kind}-{failure_mode}.bash"
    bash_env.write_text(
        "rm() {\n"
        "  for argument in \"$@\"; do\n"
        f"    case \"$(basename -- \"$argument\")\" in {basename_pattern})\n"
        f"      : > '{_bash_path(matched)}'\n"
        f"      {rm_action}\n"
        "      ;;\n"
        "    esac\n"
        "  done\n"
        "  /usr/bin/rm \"$@\"\n"
        "}\n",
        encoding="ascii",
    )
    return bash_env, python_executor


def _write_migration_gate_evidence(
    path: Path,
    package,
    environment: Path,
    *,
    archive_sha256: str | None = None,
    environment_pin_sha256: str | None = None,
) -> dict[str, object]:
    with tarfile.open(package.archive, "r:gz") as archive:
        tool_digests = {}
        for name, key in (
            ("scripts/ops/verify_closed_release.py", "verifier_sha256"),
            ("scripts/check_migration_gate.py", "checker_sha256"),
            ("scripts/ops/install_closed_release.sh", "installer_sha256"),
        ):
            stream = archive.extractfile(name)
            assert stream is not None
            tool_digests[key] = hashlib.sha256(stream.read()).hexdigest()
        migrations = sorted(
            member.name
            for member in archive.getmembers()
            if member.isfile()
            and member.name.startswith("agent/migrations/")
            and member.name.endswith(".sql")
        )
        records = []
        for name in migrations:
            stream = archive.extractfile(name)
            assert stream is not None
            raw = stream.read()
            records.append(
                {
                    "name": name.removeprefix("agent/migrations/"),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size": len(raw),
                }
            )
    assert records
    latest_name = str(records[-1]["name"])
    latest = {
        "version": int(latest_name.split("_", 1)[0]),
        "migration": latest_name,
    }
    migration_set = json.dumps(
        records,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    payload: dict[str, object] = {
        "schema_version": 1,
        "status": "passed",
        "archive_sha256": archive_sha256
        or hashlib.sha256(package.archive.read_bytes()).hexdigest(),
        "environment_pin_sha256": environment_pin_sha256
        or hashlib.sha256(environment.read_bytes()).hexdigest(),
        "migration_set_sha256": hashlib.sha256(migration_set).hexdigest(),
        "migration_latest": latest,
        "observed_database": dict(latest),
        **tool_digests,
    }
    path.write_text(json.dumps(payload) + "\n", encoding="ascii")
    return payload


def _prepare_case(tmp_path: Path, package, *, fail_after: str | None = None):
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    runtime = tmp_path / "runtime"
    private_tmp = tmp_path / "private-tmp"
    release_data = release / "agent" / "data"
    release_data.mkdir(parents=True)
    persistent.mkdir()
    evidence.mkdir()
    runtime.mkdir()
    private_tmp.mkdir()
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
    migration_gate_evidence = tmp_path / "migration-gate.json"
    _write_migration_gate_evidence(migration_gate_evidence, package, environment)
    env = {
        "KNOWN_GOOD_CLOSED": _bash_path(package.archive),
        "RELEASE_ROOT": _bash_path(release),
        "PERSISTENT_AGENT_DATA_ROOT": _bash_path(persistent),
        "ENVIRONMENT_AUTHORITY": _bash_path(environment),
        "MIGRATION_GATE_EVIDENCE": _bash_path(migration_gate_evidence),
        "RUNTIME_AUTHORITY": _bash_path(runtime),
        "EVIDENCE_DIR": _bash_path(evidence),
        "INSTALL_HOOK_LOG": _bash_path(hook_log),
        "VL360_PYTHON_DEPENDENCY_HOOK": _bash_path(hooks["python"]),
        "VL360_NUXT_DEPENDENCY_HOOK": _bash_path(hooks["nuxt"]),
        "VL360_UNIT_VERIFY_HOOK": _bash_path(hooks["units"]),
        "VL360_LOCAL_REHEARSAL_SENTINEL": _bash_path(sentinel),
        "VL360_PYTHON_EXECUTOR": _bash_path(Path(sys.executable).resolve()),
        "TMPDIR": _bash_path(private_tmp),
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
    environment_arg: str | None = None,
    migration_gate_evidence_arg: str | None = None,
    runtime_arg: str | None = None,
) -> list[str]:
    release, persistent, evidence, *_ = prepared
    command = [
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
        (
            _bash_path(case_root / "external.env")
            if environment_arg is None
            else environment_arg
        ),
        "--runtime-authority",
        _bash_path(case_root / "runtime") if runtime_arg is None else runtime_arg,
    ]
    if migration_gate_evidence_arg is not None:
        command.extend(
            ["--migration-gate-evidence", migration_gate_evidence_arg]
        )
    command.extend(
        [
            "--evidence-dir",
            _bash_path(evidence) if evidence_arg is None else evidence_arg,
            "--require-closed",
            "--local-rehearsal",
        ]
    )
    return command


def _invoke_installer(
    package,
    case_root: Path,
    prepared,
    *,
    failed_hook: str | None = None,
    include_sentinel: bool = True,
    env_overrides: dict[str, str] | None = None,
    evidence_arg: str | None = None,
    environment_arg: str | None = None,
    migration_gate_evidence_arg: str | None = None,
    runtime_arg: str | None = None,
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
        if "VL360_LOCAL_PYTHON_EXECUTOR" in env_overrides:
            env.pop("VL360_PYTHON_EXECUTOR", None)
        env.update(env_overrides)
    if not include_sentinel:
        env.pop("VL360_LOCAL_REHEARSAL_SENTINEL", None)
    args = _installer_command(
        package,
        case_root,
        prepared,
        evidence_arg=evidence_arg,
        environment_arg=environment_arg,
        migration_gate_evidence_arg=migration_gate_evidence_arg,
        runtime_arg=runtime_arg,
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


def _run_live_mount_failure_case(
    package, case_root: Path, *, replace_mount_source_after_admission: bool = False
):
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
        f"    source_path='{_bash_path(persistent)}'\n"
        "    target_path=$4\n"
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
    if replace_mount_source_after_admission:
        python_hook = runtime / "install-python-dependencies"
        python_hook.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '#!/usr/bin/env bash\\nexit 97\\n' > '{_bash_path(mount_authority)}'\n"
            f"chmod 0755 '{_bash_path(mount_authority)}'\n",
            encoding="ascii",
        )
        python_hook.chmod(0o755)

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
            "--migration-gate-evidence",
            _bash_path(case_root / "migration-gate.json"),
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
        f"    source_path='{_bash_path(persistent)}'\n"
        "    target_path=$4\n"
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
            "--migration-gate-evidence",
            _bash_path(case_root / "migration-gate.json"),
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


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux live bind recovery only"
)
def test_live_retry_recovers_interruption_immediately_after_bind_mount(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    case_root = tmp_path / "live-bind-interruption"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, values = prepared
    shutil.copytree(release / "agent" / "data", persistent, dirs_exist_ok=True)
    persistent_before = _snapshot_tree(persistent)
    runtime = case_root / "runtime"
    failed_hook_ran = case_root / "failed-hook-ran"
    for name, body in (
        (
            "install-python-dependencies",
            f": > '{_bash_path(failed_hook_ran)}'\nexit 19\n",
        ),
        ("install-nuxt-production-dependencies", "exit 0\n"),
        ("verify-systemd-units", "exit 0\n"),
    ):
        hook = runtime / name
        hook.write_text("#!/usr/bin/env bash\n" + body, encoding="ascii")
        hook.chmod(0o755)
    for name in (
        "VL360_PYTHON_DEPENDENCY_HOOK",
        "VL360_NUXT_DEPENDENCY_HOOK",
        "VL360_UNIT_VERIFY_HOOK",
        "VL360_LOCAL_REHEARSAL_SENTINEL",
        "VL360_INSTALL_FAIL_AFTER",
    ):
        values.pop(name, None)

    mounted = case_root / "mounted"
    interrupted = case_root / "interrupted-after-bind"
    mount_log = case_root / "mount-authority.log"
    mounted.touch()
    mount_authority = case_root / "mount-authority.sh"
    mount_authority.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        f"printf '%s\\n' \"$*\" >> '{_bash_path(mount_log)}'\n"
        "case \"$1\" in\n"
        "  findmnt)\n"
        f"    [ -f '{_bash_path(mounted)}' ] || exit 1\n"
        f"    printf '{{\"filesystems\":[{{\"source\":\"{_bash_path(persistent)}\","
        "\"target\":\"%s\",\"options\":\"rw,bind\"}]}' \"$4\"\n"
        "    ;;\n"
        "  umount)\n"
        f"    rm -f -- '{_bash_path(mounted)}'\n"
        "    find \"$2\" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +\n"
        "    ;;\n"
        "  mount)\n"
        "    cp -a -- \"$3\"/. \"$4\"/\n"
        f"    : > '{_bash_path(mounted)}'\n"
        f"    if [ ! -f '{_bash_path(interrupted)}' ]; then\n"
        f"      : > '{_bash_path(interrupted)}'\n"
        "      kill -9 \"$PPID\"\n"
        "    fi\n"
        "    ;;\n"
        "  *) exit 64 ;;\n"
        "esac\n",
        encoding="ascii",
    )
    mount_authority.chmod(0o755)
    command = [
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
        "--migration-gate-evidence",
        _bash_path(case_root / "migration-gate.json"),
        "--evidence-dir",
        _bash_path(evidence),
        "--require-closed",
    ]
    env = os.environ.copy()
    env.update(values)

    first = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert first.returncode != 0, first.stderr + first.stdout
    assert interrupted.is_file()
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "restore-bind-agent-data-armed"
    )
    assert mounted.is_file()

    retry = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" not in retry.stderr
    assert failed_hook_ran.is_file()
    assert not journal.exists()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == persistent_before
    assert any(
        line.startswith("umount ")
        for line in mount_log.read_text(encoding="ascii").splitlines()
    )


def test_sigkill_after_persistent_detach_is_recovered_before_retry_reset(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "sigkill-after-detach"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "persistent-detached"
    )
    assert not (release / "agent" / "data").exists()
    assert _snapshot_tree(persistent) == persistent_before

    retry = _invoke_installer(closed_package, case_root, prepared)

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    assert _snapshot_tree(persistent) == {}
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_journal_interruption_is_owned_and_terminated_outside_installer_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    case_root = tmp_path / "supervised-interruption"
    evidence = case_root / "evidence"
    evidence.mkdir(parents=True)
    stage = "persistent-detached"
    journal = evidence / "install-mutation-state.json"
    interrupted = case_root / f"interrupted-{stage}"
    direct_python = _bash_path((case_root / "direct-python").resolve())
    popen_calls: list[tuple[list[str], dict[str, object]]] = []
    taskkill_calls: list[list[str]] = []
    owned_handle_kills: list[object] = []

    class FakeProcess:
        pid = 2468
        returncode: int | None = None

        def poll(self):
            return self.returncode

        def communicate(self, timeout: float):
            assert timeout > 0
            assert self.returncode is not None
            return "captured stdout", "captured stderr"

        def kill(self):
            owned_handle_kills.append(self)
            self.returncode = -9
            raise ProcessLookupError(self.pid)

    process = FakeProcess()

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        popen_calls.append((command, kwargs))
        journal.write_text(json.dumps({"stage": stage}), encoding="utf-8")
        interrupted.touch()
        return process

    def fake_run(command: list[str], **kwargs: object):
        taskkill_calls.append(command)
        process.returncode = 1
        return subprocess.CompletedProcess(command, 0)

    def fake_killpg(process_group_id: int, _signal: int) -> None:
        assert process_group_id == process.pid
        process.returncode = -9

    monkeypatch.setattr(
        sys.modules[__name__],
        "_installer_command",
        lambda *_args, **_kwargs: ["installer-under-test"],
    )
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(os, "killpg", fake_killpg, raising=False)

    prepared = (
        case_root / "release",
        case_root / "persistent",
        evidence,
        {},
        {},
        case_root / "runtime",
        {"VL360_PYTHON_EXECUTOR": direct_python},
    )
    returned_journal = _interrupt_at_journal_stage(
        object(), case_root, prepared, stage
    )

    assert returned_journal == journal
    assert len(popen_calls) == 1
    command, kwargs = popen_calls[0]
    if os.name == "nt":
        assert command == [
            sys.executable,
            str(OPS / "run_backend_regression.py"),
            "--windows-job-supervisor",
            "--",
            "installer-under-test",
        ]
    else:
        assert command == ["installer-under-test"]
    assert kwargs["stdout"] != subprocess.PIPE
    assert kwargs["stderr"] != subprocess.PIPE
    assert kwargs["text"] is True
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["VL360_PYTHON_EXECUTOR"] == direct_python
    assert "VL360_LOCAL_PYTHON_EXECUTOR" not in env
    barrier_path = case_root / f"interrupt-at-{stage}.bash"
    assert env["BASH_ENV"] == _bash_path(barrier_path.resolve())
    barrier = barrier_path.read_text(encoding="ascii")
    stage_command = f"write_mutation_state {stage}"
    armed_check = '[ "$__vl360_journal_barrier_state" = armed ]'
    stage_check = f'[ "${{BASH_COMMAND-}}" = {shlex.quote(stage_command)} ]'
    journal_exists = f"[ -f {shlex.quote(_bash_path(journal))} ]"
    journal_check = f"grep -Fq {shlex.quote(json.dumps({'stage': stage})[1:-1])}"
    assert barrier_path.parent == case_root
    assert "shopt -u extdebug" in barrier
    assert "set +T" in barrier
    assert "__vl360_journal_barrier_state=waiting" in barrier
    assert armed_check in barrier
    assert stage_check in barrier
    assert barrier.index(armed_check) < barrier.index(stage_check)
    assert "__vl360_journal_barrier_state=armed" in barrier
    assert journal_exists in barrier
    assert journal_check in barrier
    assert barrier.index(journal_exists) < barrier.index(journal_check)
    assert barrier.index(journal_check) < barrier.index(f": > {shlex.quote(_bash_path(interrupted))}")
    assert barrier.index(journal_check) < barrier.index("while :; do")
    assert "trap - DEBUG" in barrier
    assert "trap '__vl360_journal_barrier' DEBUG" in barrier
    assert "kill -9" not in barrier
    if os.name == "nt":
        assert kwargs["creationflags"] == getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
        )
        assert owned_handle_kills == [process]
        assert taskkill_calls == []
    else:
        assert kwargs["start_new_session"] is True
        assert owned_handle_kills == []
        assert taskkill_calls == []


@pytest.mark.skipif(os.name != "nt", reason="Windows taskkill cleanup only")
@pytest.mark.parametrize(
    ("failure_mode", "expected_error"),
    (
        ("exception", "taskkill failed: OSError: taskkill unavailable"),
        ("nonzero", "taskkill exited 255"),
    ),
)
def test_default_windows_cleanup_preserves_taskkill_failures_after_parent_exit(
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
    expected_error: str,
):
    class FakeProcess:
        pid = 2468
        returncode: int | None = None

        def poll(self):
            return self.returncode

        def communicate(self, timeout: float):
            assert timeout > 0
            assert self.returncode is not None
            return "captured stdout", "captured stderr"

    process = FakeProcess()

    def fake_run(command: list[str], **kwargs: object):
        assert command == ["taskkill", "/PID", str(process.pid), "/T", "/F"]
        process.returncode = 1
        if failure_mode == "exception":
            raise OSError("taskkill unavailable")
        return subprocess.CompletedProcess(command, 255)

    monkeypatch.setattr(subprocess, "run", fake_run)

    stdout, stderr, errors = _terminate_owned_installer_process(process)

    assert stdout == "captured stdout"
    assert stderr == "captured stderr"
    assert errors == [expected_error]


def test_file_backed_process_timeout_is_cleaned_and_keeps_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    stdout_path = tmp_path / "background.stdout"
    stderr_path = tmp_path / "background.stderr"
    stdout_path.write_text("captured stdout", encoding="utf-8")
    stderr_path.write_text("captured stderr", encoding="utf-8")
    cleaned: list[object] = []

    class FakeProcess:
        def communicate(self, timeout: float):
            raise subprocess.TimeoutExpired(["installer"], timeout)

    process = FakeProcess()

    def fake_terminate(owned_process):
        cleaned.append(owned_process)
        return "", "", []

    monkeypatch.setattr(
        sys.modules[__name__],
        "_terminate_owned_installer_process",
        fake_terminate,
    )

    stdout, stderr, errors = _finish_file_backed_process(
        process, stdout_path, stderr_path, timeout=3
    )

    assert cleaned == [process]
    assert stdout == "captured stdout"
    assert stderr == "captured stderr"
    assert errors == ["background installer did not exit within 3 seconds"]


def test_finishing_file_backed_processes_cleans_every_started_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    first = object()
    second = object()
    calls: list[object] = []
    records = [
        (first, tmp_path / "first.stdout", tmp_path / "first.stderr"),
        (second, tmp_path / "second.stdout", tmp_path / "second.stderr"),
    ]

    def fake_finish(process, _stdout_path, _stderr_path, *, timeout):
        assert timeout == 7
        calls.append(process)
        errors = ["first failed"] if process is first else []
        return f"stdout-{len(calls)}", f"stderr-{len(calls)}", errors

    monkeypatch.setattr(
        sys.modules[__name__], "_finish_file_backed_process", fake_finish
    )

    completed = _finish_file_backed_processes(records, timeout=7)

    assert calls == [first, second]
    assert completed == [
        (first, "stdout-1", "stderr-1", ["first failed"]),
        (second, "stdout-2", "stderr-2", []),
    ]


def _wait_for_journal_interruption(
    process: subprocess.Popen[str], journal: Path, interrupted: Path, stage: str
) -> None:
    deadline = time.monotonic() + 120.0
    observed_stage = None
    while time.monotonic() < deadline:
        if interrupted.is_file() and journal.is_file():
            try:
                observed_stage = json.loads(
                    journal.read_text(encoding="utf-8")
                ).get("stage")
            except (OSError, json.JSONDecodeError):
                pass
            if observed_stage == stage:
                return
        if process.poll() is not None:
            raise AssertionError(
                f"installer exited before interruption stage {stage}; "
                f"last journal stage was {observed_stage!r}"
            )
        time.sleep(0.05)
    raise AssertionError(
        f"timed out waiting for interruption stage {stage}; "
        f"last journal stage was {observed_stage!r}"
    )


def _terminate_owned_installer_process(
    process: subprocess.Popen[str],
    *,
    windows_job_supervisor: bool = False,
) -> tuple[str, str, list[str]]:
    errors: list[str] = []
    if process.poll() is None:
        if os.name == "nt" and windows_job_supervisor:
            try:
                process.kill()
            except Exception as exc:
                if process.poll() is None:
                    errors.append(
                        f"owned-handle kill failed: {type(exc).__name__}: {exc}"
                    )
        elif os.name == "nt":
            try:
                completed = subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    timeout=15,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as exc:
                errors.append(f"taskkill failed: {type(exc).__name__}: {exc}")
            else:
                if completed.returncode != 0:
                    errors.append(f"taskkill exited {completed.returncode}")
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as exc:
                errors.append(f"killpg failed: {type(exc).__name__}: {exc}")

    stdout = ""
    stderr = ""
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        errors.append("owned process did not exit within cleanup timeout")
        try:
            process.kill()
        except Exception as exc:
            errors.append(f"owned-handle kill failed: {type(exc).__name__}: {exc}")
        try:
            stdout, stderr = process.communicate(timeout=15)
        except Exception as exc:
            errors.append(f"owned-handle wait failed: {type(exc).__name__}: {exc}")
    except Exception as exc:
        errors.append(f"owned process wait failed: {type(exc).__name__}: {exc}")
    return stdout or "", stderr or "", errors


def _interrupt_at_journal_stage(package, case_root: Path, prepared, stage: str):
    *_, evidence, _, _, _, values = prepared
    interrupted = case_root / f"interrupted-{stage}"
    journal = evidence / "install-mutation-state.json"
    barrier = case_root / f"interrupt-at-{stage}.bash"
    stage_command = f"write_mutation_state {stage}"
    stage_fragment = json.dumps({"stage": stage})[1:-1]
    barrier.write_text(
        "shopt -u extdebug\n"
        "set +T\n"
        "__vl360_journal_barrier_state=waiting\n"
        "__vl360_journal_barrier() {\n"
        '  if [ "$__vl360_journal_barrier_state" = armed ]; then\n'
        f"    if [ -f {shlex.quote(_bash_path(journal))} ] "
        f"&& grep -Fq {shlex.quote(stage_fragment)} "
        f"{shlex.quote(_bash_path(journal))}; then\n"
        "      trap - DEBUG\n"
        f"      : > {shlex.quote(_bash_path(interrupted))}\n"
        "      while :; do sleep 1; done\n"
        "    fi\n"
        "    return 0\n"
        "  fi\n"
        f'  if [ "${{BASH_COMMAND-}}" = {shlex.quote(stage_command)} ]; then\n'
        "    __vl360_journal_barrier_state=armed\n"
        "  fi\n"
        "  return 0\n"
        "}\n"
        "trap '__vl360_journal_barrier' DEBUG\n",
        encoding="ascii",
    )
    env = os.environ.copy()
    env.update(values)
    env["BASH_ENV"] = _bash_path(barrier.resolve())
    installer_command = _installer_command(package, case_root, prepared)
    if os.name == "nt":
        command = [
            sys.executable,
            str(OPS / "run_backend_regression.py"),
            "--windows-job-supervisor",
            "--",
            *installer_command,
        ]
    else:
        command = installer_command
    stdout_path = case_root / f"interrupt-{stage}.stdout"
    stderr_path = case_root / f"interrupt-{stage}.stderr"
    popen_kwargs: dict[str, object] = {
        "cwd": ROOT,
        "env": env,
        "text": True,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
        )
    else:
        popen_kwargs["start_new_session"] = True
    with (
        stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_stream,
        stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_stream,
    ):
        popen_kwargs["stdout"] = stdout_stream
        popen_kwargs["stderr"] = stderr_stream
        process = subprocess.Popen(command, **popen_kwargs)
        wait_error = None
        try:
            _wait_for_journal_interruption(process, journal, interrupted, stage)
        except AssertionError as exc:
            wait_error = str(exc)
        finally:
            _, _, cleanup_errors = _terminate_owned_installer_process(
                process, windows_job_supervisor=os.name == "nt"
            )
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    result = subprocess.CompletedProcess(
        command,
        process.returncode if process.returncode is not None else -1,
        stdout,
        stderr,
    )
    assert not cleanup_errors, "; ".join(cleanup_errors) + "\n" + stderr + stdout
    assert wait_error is None, wait_error + "\n" + stderr + stdout
    assert result.returncode != 0, result.stderr + result.stdout
    assert interrupted.is_file(), result.stderr + result.stdout
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == stage
    return journal


@pytest.mark.parametrize(
    "stage",
    (
        "swap-release-root-armed",
        "root-swapped",
        "persistent-restored",
        "systemd-backup-preparing",
        "systemd-units-armed",
        "retire-old-root-armed",
    ),
)
def test_sigkill_at_later_journal_stage_is_rolled_back_before_retry(
    tmp_path: Path, closed_package, stage: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"sigkill-{stage}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    journal = _interrupt_at_journal_stage(closed_package, case_root, prepared, stage)

    retry = _invoke_installer(closed_package, case_root, prepared)

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_primary_restore_stale_stage_accepts_old_root_topology(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index(
        '  case "$entry_stage" in',
        source.index("reconcile_stale_install_attempt()"),
    )
    topology = source[start : source.index("  candidate_root=''", start)]
    script = "\n".join(
        (
            "set -u",
            "entry_stage=recovery-restore-persistent-armed",
            "old_present=true",
            "release_present=true",
            "staging_present=false",
            "retired_present=false",
            "committed_recovery=false",
            "observed_root_topology_requires_fsync=false",
            "classify_topology() {",
            topology,
            "}",
            "classify_topology",
            "printf '%s\n' \"$?\"",
        )
    )

    result = _run_bash_script(tmp_path / "primary-restore-stale-topology.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "0"


def test_full_stale_local_restore_stage_recovers_old_root_and_persistent_bytes(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    release = tmp_path / "release"
    current_data = release / "agent" / "data"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    old_root = tmp_path / ".release.closed-old.321"
    staging = tmp_path / ".release.closed-stage.321"
    retired = tmp_path / (".release.closed-retired." + "a" * 32)
    systemd = tmp_path / "systemd"
    for directory in (current_data, evidence, old_root / "agent", systemd):
        directory.mkdir(parents=True, exist_ok=True)
    expected_db = tmp_path / "expected-app.db"
    expected_sitemap = tmp_path / "expected-sitemap.json"
    expected_db.write_bytes(b"persistent-db\n")
    expected_sitemap.write_bytes(b"persistent-sitemap\n")
    (current_data / "app.db").write_bytes(expected_db.read_bytes())
    sitemap = current_data / "sitemap-bundles" / "batch" / "metadata.json"
    sitemap.parent.mkdir(parents=True)
    sitemap.write_bytes(expected_sitemap.read_bytes())
    (release / "launch-release-manifest.json").write_text("{}\n", encoding="ascii")
    (release / "candidate-marker").write_text("candidate\n", encoding="ascii")
    (old_root / "old-marker").write_bytes(b"old\n")
    journal = evidence / "install-mutation-state.json"
    journal.write_text("{}\n", encoding="ascii")
    log = tmp_path / "full-reconcile.log"
    reconciliation = _stale_local_reconciliation_source()
    script = "\n".join(
        (
            "set -u",
            "LOCAL_REHEARSAL=true",
            "STALE_LOCAL_REHEARSAL=true",
            "CURRENT_RELEASE_KEY=release-key",
            "STALE_RELEASE_KEY=release-key",
            "CURRENT_PERSISTENT_KEY=persistent-key",
            "STALE_PERSISTENT_KEY=persistent-key",
            "CURRENT_SYSTEMD_KEY=systemd-key",
            "RELEASE_NAME=release",
            "STALE_SYSTEMD_KEY=systemd-key",
            "STALE_CANDIDATE_MANIFEST_SHA256=manifest-digest",
            "STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256=candidate-topology-digest",
            "STALE_CANDIDATE_RELEASE_ROOT_IDENTITY=3:4",
            "STALE_SOURCE_RELEASE_TOPOLOGY_SHA256=source-topology-digest",
            "STALE_SOURCE_RELEASE_ROOT_IDENTITY=1:2",
            "CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT=/candidate-topology",
            "SOURCE_RELEASE_TOPOLOGY_SNAPSHOT=/source-topology",
            "STALE_STAGE=recovery-restore-persistent-armed",
            "STALE_ATTEMPT_ID=" + "a" * 32,
            "STALE_PID=321",
            f"STALE_RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"STALE_PERSISTENT_ROOT={shlex.quote(_bash_path(persistent))}",
            f"STALE_STAGING_ROOT={shlex.quote(_bash_path(staging))}",
            f"STALE_OLD_ROOT={shlex.quote(_bash_path(old_root))}",
            f"STALE_RETIRED_ROOT={shlex.quote(_bash_path(retired))}",
            f"STALE_SYSTEMD_UNIT_DESTINATION={shlex.quote(_bash_path(systemd))}",
            "STALE_SYSTEMD_UNIT_ATTEMPT_ROOT=",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            "SNAPSHOT_BEFORE=/snapshot",
            "UNIT_VERIFY_HOOK_SHA256=",
            f"EXPECTED_DB={shlex.quote(_bash_path(expected_db))}",
            f"EXPECTED_SITEMAP={shlex.quote(_bash_path(expected_sitemap))}",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            "stale_tree_state() {",
            "  [ ! -L \"$1\" ] || return 3",
            "  [ -e \"$1\" ] || return 1",
            "  [ -d \"$1\" ] || return 3",
            "  [ -z \"$(find \"$1\" -mindepth 1 -print -quit)\" ] && return 2",
            "  return 0",
            "}",
            "tree_matches_snapshot() {",
            "  [ -f \"$1/app.db\" ] && cmp -s \"$1/app.db\" \"$EXPECTED_DB\" || return 1",
            "  [ -f \"$1/sitemap-bundles/batch/metadata.json\" ] || return 1",
            "  cmp -s \"$1/sitemap-bundles/batch/metadata.json\" \"$EXPECTED_SITEMAP\"",
            "}",
            "write_stale_mutation_state() { STALE_STAGE=\"$1\"; printf 'journal:%s\\n' \"$1\" >> \"$RECOVERY_LOG\"; printf '%s\\n' \"$1\" > \"$MUTATION_STATE\"; }",
            "fsync_directories() { return 0; }",
            "restore_systemd_units_from() { return 0; }",
            "remove_systemd_unit_attempt_root() { return 0; }",
            "invoke_pinned_executable() { return 0; }",
            "tree_matches_bound_topology() { return 0; }",
            "verify_stale_journal_bindings() { return 0; }",
            "regular_file_sha256() { printf '%s\\n' \"$STALE_CANDIDATE_MANIFEST_SHA256\"; }",
            "write_cleanup_owner_marker() { return 0; }",
            "verify_cleanup_owner_marker() { return 0; }",
            "remove_file_durably() { /usr/bin/rm -f -- \"$1\"; }",
            "invoke_rm() { rm \"$@\"; }",
            "rm() {",
            "  local argument",
            "  for argument in \"$@\"; do",
            "    if [ \"$argument\" = \"$STALE_RELEASE_ROOT\" ] || [[ \"$(basename -- \"$argument\")\" == .release.closed-candidate-cleanup.* ]]; then printf 'rm:candidate-release\\n' >> \"$RECOVERY_LOG\"; fi",
            "  done",
            "  /usr/bin/rm \"$@\"",
            "}",
            "mv() {",
            "  local source destination",
            "  if [ \"${1:-}\" = -- ]; then source=${2:-}; destination=${3:-}; else source=${1:-}; destination=${2:-}; fi",
            "  if [ \"$source\" = \"$STALE_RELEASE_ROOT/agent/data\" ] && [ \"$destination\" = \"$STALE_PERSISTENT_ROOT\" ]; then printf 'mv:detach-candidate-data\\n' >> \"$RECOVERY_LOG\"; fi",
            "  if [ \"$source\" = \"$STALE_OLD_ROOT\" ] && [ \"$destination\" = \"$STALE_RELEASE_ROOT\" ]; then printf 'mv:restore-old-root\\n' >> \"$RECOVERY_LOG\"; fi",
            "  if [ \"$source\" = \"$STALE_PERSISTENT_ROOT\" ] && [ \"$destination\" = \"$STALE_RELEASE_ROOT/agent/data\" ]; then printf 'mv:restore-persistent\\n' >> \"$RECOVERY_LOG\"; fi",
            "  /usr/bin/mv \"$@\"",
            "}",
            "clear_mutation_state() { /usr/bin/rm -f -- \"$MUTATION_STATE\"; printf 'clear\\n' >> \"$RECOVERY_LOG\"; }",
            reconciliation,
            "reconcile_stale_install_attempt",
            "printf '%s\\n' \"$?\"",
        )
    )

    result = _run_bash_script(tmp_path / "full-local-reconcile.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "0"
    assert (release / "old-marker").read_bytes() == b"old\n"
    assert not (release / "candidate-marker").exists()
    assert (release / "agent" / "data" / "app.db").read_bytes() == b"persistent-db\n"
    assert (
        release / "agent" / "data" / "sitemap-bundles" / "batch" / "metadata.json"
    ).read_bytes() == b"persistent-sitemap\n"
    assert persistent.is_dir()
    assert _snapshot_tree(persistent) == {}
    assert not old_root.exists()
    assert not staging.exists()
    assert not Path(f"{staging}.owner").exists()
    assert not retired.exists()
    assert not journal.exists()
    assert not list(tmp_path.glob(".release.closed-*"))
    lines = log.read_text(encoding="ascii").splitlines()
    ordered = [
        "mv:detach-candidate-data",
        "rm:candidate-release",
        "mv:restore-old-root",
        "mv:restore-persistent",
        "journal:recovery-create-persistent-root-armed",
        "clear",
    ]
    assert [lines.index(item) for item in ordered] == sorted(
        lines.index(item) for item in ordered
    )


def test_absent_staging_owner_fsync_failure_retains_journal_for_clean_retry(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    release = tmp_path / "release"
    current_data = release / "agent" / "data"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    staging = tmp_path / ".release.closed-stage.321"
    old_root = tmp_path / ".release.closed-old.321"
    retired = tmp_path / (".release.closed-retired." + "a" * 32)
    systemd = tmp_path / "systemd"
    for directory in (current_data, persistent, evidence, systemd):
        directory.mkdir(parents=True, exist_ok=True)
    expected_db = tmp_path / "expected-app.db"
    expected_db.write_bytes(b"persistent-db\n")
    (current_data / "app.db").write_bytes(expected_db.read_bytes())
    (release / "old-marker").write_bytes(b"old\n")
    journal = evidence / "install-mutation-state.json"
    journal.write_text("{}\n", encoding="ascii")
    failed = tmp_path / "owner-fsync-failed"
    log = tmp_path / "owner-fsync-retry.log"
    reconciliation = _stale_local_reconciliation_source()
    script = "\n".join(
        (
            "set -u",
            "LOCAL_REHEARSAL=true",
            "STALE_LOCAL_REHEARSAL=true",
            "CURRENT_RELEASE_KEY=release-key",
            "STALE_RELEASE_KEY=release-key",
            "CURRENT_PERSISTENT_KEY=persistent-key",
            "STALE_PERSISTENT_KEY=persistent-key",
            "CURRENT_SYSTEMD_KEY=systemd-key",
            "STALE_SYSTEMD_KEY=systemd-key",
            "RELEASE_NAME=release",
            "STALE_SCHEMA_VERSION=4",
            "STALE_SOURCE_RELEASE_ROOT_IDENTITY=1:2",
            "SOURCE_RELEASE_TOPOLOGY_SNAPSHOT=/source-topology",
            "STALE_STAGE=recovery-remove-staging-owner-armed",
            "STALE_ATTEMPT_ID=" + "a" * 32,
            "STALE_PID=321",
            f"STALE_RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"STALE_PERSISTENT_ROOT={shlex.quote(_bash_path(persistent))}",
            f"STALE_STAGING_ROOT={shlex.quote(_bash_path(staging))}",
            f"STALE_OLD_ROOT={shlex.quote(_bash_path(old_root))}",
            f"STALE_RETIRED_ROOT={shlex.quote(_bash_path(retired))}",
            f"STALE_SYSTEMD_UNIT_DESTINATION={shlex.quote(_bash_path(systemd))}",
            "STALE_SYSTEMD_UNIT_ATTEMPT_ROOT=",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            "SNAPSHOT_BEFORE=/snapshot",
            "UNIT_VERIFY_HOOK_SHA256=",
            f"EXPECTED_DB={shlex.quote(_bash_path(expected_db))}",
            f"FAILED={shlex.quote(_bash_path(failed))}",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            "stale_tree_state() {",
            "  [ ! -L \"$1\" ] || return 3",
            "  [ -e \"$1\" ] || return 1",
            "  [ -d \"$1\" ] || return 3",
            "  [ -z \"$(find \"$1\" -mindepth 1 -print -quit)\" ] && return 2",
            "  return 0",
            "}",
            "tree_matches_snapshot() { [ -f \"$1/app.db\" ] && cmp -s \"$1/app.db\" \"$EXPECTED_DB\"; }",
            "write_stale_mutation_state() { STALE_STAGE=\"$1\"; printf '%s\\n' \"$1\" > \"$MUTATION_STATE\"; }",
            "restore_systemd_units_from() { return 0; }",
            "remove_systemd_unit_attempt_root() { return 0; }",
            "invoke_pinned_executable() { return 0; }",
            "tree_matches_bound_topology() { return 0; }",
            "verify_stale_journal_bindings() { return 0; }",
            "fsync_directories() {",
            "  if [ \"$STALE_STAGE\" = recovery-remove-staging-owner-armed ] && [ ! -f \"$FAILED\" ]; then",
            "    : > \"$FAILED\"",
            "    printf 'fsync-fail\\n' >> \"$RECOVERY_LOG\"",
            "    return 71",
            "  fi",
            "  printf 'fsync-ok\\n' >> \"$RECOVERY_LOG\"",
            "  return 0",
            "}",
            "clear_mutation_state() { /usr/bin/rm -f -- \"$MUTATION_STATE\"; printf 'clear\\n' >> \"$RECOVERY_LOG\"; }",
            reconciliation,
            "set +e",
            "reconcile_stale_install_attempt",
            "first_status=$?",
            "[ -f \"$MUTATION_STATE\" ] && first_journal=1 || first_journal=0",
            "printf '%s|%s|%s\\n' \"$first_status\" \"$STALE_STAGE\" \"$first_journal\"",
            "reconcile_stale_install_attempt",
            "second_status=$?",
            "[ -f \"$MUTATION_STATE\" ] && second_journal=1 || second_journal=0",
            "printf '%s|%s|%s\\n' \"$second_status\" \"$STALE_STAGE\" \"$second_journal\"",
        )
    )

    result = _run_bash_script(tmp_path / "owner-fsync-retry.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.splitlines() == [
        "1|recovery-remove-staging-owner-armed|1",
        "0|recovery-remove-staging-owner-armed|0",
    ]
    assert failed.is_file()
    assert log.read_text(encoding="ascii").splitlines() == [
        "fsync-fail",
        "fsync-ok",
        "clear",
    ]
    assert (release / "old-marker").read_bytes() == b"old\n"
    assert (current_data / "app.db").read_bytes() == b"persistent-db\n"
    assert persistent.is_dir()
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()
    assert not list(tmp_path.glob(".release.closed-*"))


def test_exit_recovery_crash_after_old_root_restore_is_retryable(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "exit-recovery-old-root-crash"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    interrupted = case_root / "old-root-restored"
    bash_env = _write_mv_side_effect_fault(
        case_root / "kill-after-old-root-restore.bash",
        marker=interrupted,
        condition=(
            f'"$destination" == \'{_bash_path(release)}\' '
            f'&& "$(basename -- "$source")" == \'.{release.name}.closed-old.\'*'
        ),
        failure='kill -9 "$$"',
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_INSTALL_FAIL_AFTER": "swap-release-root",
        },
    )

    assert first.returncode != 0, first.stderr + first.stdout
    assert interrupted.is_file()
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-restore-old-root-armed"
    )
    expected_release = {
        name: raw
        for name, raw in before_release.items()
        if not name.startswith("agent/data/")
    }
    assert _snapshot_tree(release) == expected_release
    assert _snapshot_tree(persistent) == persistent_before
    assert not list(release.parent.glob(f".{release.name}.closed-old.*"))

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    _assert_python_dependency_hook_failed(evidence)
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_primary_restore_rejects_same_topology_old_root_replacement(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "replaced-old-root-before-restore"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    original_identity = (release.stat().st_dev, release.stat().st_ino)
    persistent_before = _snapshot_tree(release / "agent" / "data")
    replaced = case_root / "old-root-replaced"
    bash_env = case_root / "replace-old-root.bash"
    bash_env.write_text(
        "mv() {\n"
        "  local source destination replacement\n"
        "  if [ \"${1:-}\" = -- ]; then source=${2:-}; destination=${3:-}; "
        "else source=${1:-}; destination=${2:-}; fi\n"
        f"  if [[ \"$(basename -- \"$source\")\" == .{release.name}.closed-old.* ]] "
        f"&& [ \"$destination\" = '{_bash_path(release)}' ] "
        f"&& [ ! -f '{_bash_path(replaced)}' ]; then\n"
        "    replacement=\"$source.replacement\"\n"
        "    /usr/bin/cp -a -- \"$source\" \"$replacement\"\n"
        "    /usr/bin/rm -rf -- \"$source\"\n"
        "    /usr/bin/mv -- \"$replacement\" \"$source\"\n"
        f"    : > '{_bash_path(replaced)}'\n"
        "  fi\n"
        "  /usr/bin/mv \"$@\"\n"
        "}\n",
        encoding="ascii",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_INSTALL_FAIL_AFTER": "swap-release-root",
        },
    )

    assert first.returncode == 73, first.stderr + first.stdout
    assert replaced.is_file()
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-restore-old-root-armed"
    )
    expected_release = {
        name: raw
        for name, raw in before_release.items()
        if not name.startswith("agent/data/")
    }
    assert _snapshot_tree(release) == expected_release
    assert _snapshot_tree(persistent) == persistent_before
    assert (release.stat().st_dev, release.stat().st_ino) != original_identity

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert _snapshot_tree(release) == expected_release
    assert _snapshot_tree(persistent) == persistent_before
    assert journal.is_file()


def test_stale_post_restore_topology_is_fsynced_before_next_recovery_stage(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "stale-post-restore-fsync"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    interrupted = case_root / "old-root-restored"
    journal = evidence / "install-mutation-state.json"
    bash_env = _write_mv_side_effect_fault(
        case_root / "kill-after-old-root-restore.bash",
        marker=interrupted,
        condition=(
            f'"$destination" == \'{_bash_path(release)}\' '
            f'&& "$(basename -- "$source")" == \'.{release.name}.closed-old.\'*'
        ),
        failure='kill -9 "$$"',
    )
    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_INSTALL_FAIL_AFTER": "swap-release-root",
        },
    )
    assert first.returncode != 0, first.stderr + first.stdout
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-restore-old-root-armed"
    )

    fsync_failed = case_root / "post-restore-parent-fsync-failed"
    python_executor = _write_local_python_executor(
        case_root / "post-restore-fsync-python",
        f"  if [ \"${{1:-}}\" = - ] "
        f"&& [ \"${{2:-}}\" = '{_bash_path(release.parent)}' ] "
        f"&& [ -f '{_bash_path(journal)}' ] "
        f"&& grep -Fq '\"stage\": \"recovery-restore-old-root-armed\"' "
        f"'{_bash_path(journal)}' && [ ! -f '{_bash_path(fsync_failed)}' ]; then\n"
        f"    : > '{_bash_path(fsync_failed)}'\n"
        "    exit 71\n"
        "  fi\n"
        "command \"$REAL_PYTHON\" \"$@\"\n",
    )
    failed = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)},
    )

    assert failed.returncode == 2, failed.stderr + failed.stdout
    assert "stale-install-recovery-required" in failed.stderr
    assert fsync_failed.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-restore-old-root-armed"
    )
    expected_release = {
        name: raw
        for name, raw in before_release.items()
        if not name.startswith("agent/data/")
    }
    assert _snapshot_tree(release) == expected_release
    assert _snapshot_tree(persistent) == persistent_before


@pytest.mark.parametrize(
    "stage",
    (
        "recovery-remove-release-root-armed",
        "retire-old-root-armed",
        "committed-cleanup",
    ),
)
def test_stale_observed_root_topology_is_fsynced_before_recovery_advances(
    tmp_path: Path, stage: str
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    reconciliation = source[
        source.index("inspect_stale_mount()") : source.index("record_install_lock()")
    ]
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    systemd = tmp_path / "systemd"
    old_root = tmp_path / ".release.closed-old.321"
    retired_root = tmp_path / (".release.closed-retired." + "a" * 32)
    for directory in (persistent, evidence, systemd):
        directory.mkdir(parents=True)
    if stage == "recovery-remove-release-root-armed":
        (old_root / "agent").mkdir(parents=True)
        (persistent / "persistent-marker").write_text("data\n", encoding="ascii")
    else:
        (release / "agent" / "data").mkdir(parents=True)
        (release / "launch-release-manifest.json").write_text("{}\n", encoding="ascii")
        if stage == "retire-old-root-armed":
            retired_root.mkdir()
    journal = evidence / "install-mutation-state.json"
    journal.write_text("{}\n", encoding="ascii")
    log = tmp_path / "reconcile.log"
    release_parent = _bash_path(release.parent)
    script = "\n".join(
        (
            "set -u",
            "LOCAL_REHEARSAL=true",
            "STALE_LOCAL_REHEARSAL=true",
            "CURRENT_RELEASE_KEY=release-key",
            "STALE_RELEASE_KEY=release-key",
            "CURRENT_PERSISTENT_KEY=persistent-key",
            "STALE_PERSISTENT_KEY=persistent-key",
            "CURRENT_SYSTEMD_KEY=systemd-key",
            "STALE_SYSTEMD_KEY=systemd-key",
            "RELEASE_NAME=release",
            f"STALE_STAGE={stage}",
            "STALE_ATTEMPT_ID=" + "a" * 32,
            "STALE_PID=321",
            f"STALE_RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"STALE_PERSISTENT_ROOT={shlex.quote(_bash_path(persistent))}",
            f"STALE_STAGING_ROOT={shlex.quote(_bash_path(tmp_path / '.release.closed-stage.321'))}",
            f"STALE_OLD_ROOT={shlex.quote(_bash_path(old_root))}",
            f"STALE_RETIRED_ROOT={shlex.quote(_bash_path(retired_root))}",
            f"STALE_SYSTEMD_UNIT_DESTINATION={shlex.quote(_bash_path(systemd))}",
            "STALE_SYSTEMD_UNIT_ATTEMPT_ROOT=",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            "SNAPSHOT_BEFORE=/snapshot",
            "SOURCE_RELEASE_TOPOLOGY_SNAPSHOT=/source-topology",
            "STALE_SOURCE_RELEASE_ROOT_IDENTITY=1:2",
            "UNIT_VERIFY_HOOK_SHA256=digest",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            "tree_matches_snapshot() { return 0; }",
            "stale_tree_state() { [ \"$1\" = \"$STALE_RELEASE_ROOT/agent/data\" ] && return 0; [ \"$1\" = \"$STALE_PERSISTENT_ROOT\" ] && return 2; return 1; }",
            "write_stale_mutation_state() { printf 'journal:%s\\n' \"$1\" >> \"$RECOVERY_LOG\"; STALE_STAGE=\"$1\"; }",
            "restore_systemd_units_from() { printf 'restore-systemd\\n' >> \"$RECOVERY_LOG\"; return 1; }",
            "invoke_pinned_executable() { printf 'verify-systemd\\n' >> \"$RECOVERY_LOG\"; return 1; }",
            "remove_systemd_unit_attempt_root() { printf 'remove-systemd-attempt\\n' >> \"$RECOVERY_LOG\"; return 1; }",
            "fsync_directories() { printf 'fsync:%s\\n' \"$*\" >> \"$RECOVERY_LOG\"; return 71; }",
            "clear_mutation_state() { printf 'clear\\n' >> \"$RECOVERY_LOG\"; return 1; }",
            reconciliation,
            "tree_matches_bound_topology() { return 0; }",
            "verify_stale_journal_bindings() { return 0; }",
            "reconcile_stale_install_attempt",
            "printf '%s|%s\\n' \"$?\" \"$STALE_STAGE\"",
        )
    )
    result = _run_bash_script(tmp_path / "stale-topology-fsync.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == f"1|{stage}"
    assert log.read_text(encoding="ascii").splitlines() == [
        f"fsync:{release_parent}"
    ]


@pytest.mark.parametrize("target", ("staging", "owner"))
def test_stale_staging_cleanup_requires_verified_absence(tmp_path: Path, target: str):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index("  local stage_owner_valid=false")
    cleanup = source[start : source.index('  if [ "$committed_recovery" = true ]; then', start)]
    staging = tmp_path / ".release.closed-stage.321"
    owner = tmp_path / ".release.closed-stage.321.owner"
    staging_delete = tmp_path / (".release.closed-staging-cleanup." + "a" * 32)
    staging_delete_owner = Path(f"{staging_delete}.owner")
    if target == "staging":
        staging.mkdir()
    owner.write_text("owner\n", encoding="ascii")
    log = tmp_path / "cleanup.log"
    failed_path = staging_delete if target == "staging" else owner
    script = "\n".join(
        (
            "set -u",
            "entry_stage=persistent-detached",
            "committed_recovery=false",
            "STALE_ATTEMPT_ID=" + "a" * 32,
            "STALE_PID=321",
            "STALE_CANDIDATE_RELEASE_ROOT_IDENTITY=1:2",
            "STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256=" + "b" * 64,
            "STALE_CANDIDATE_MANIFEST_SHA256=" + "c" * 64,
            "CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT=/snapshot",
            f"STALE_STAGING_ROOT={shlex.quote(_bash_path(staging))}",
            "stale_stage_owner=\"$STALE_STAGING_ROOT.owner\"",
            f"staging_delete_root={shlex.quote(_bash_path(staging_delete))}",
            f"staging_delete_owner={shlex.quote(_bash_path(staging_delete_owner))}",
            "staging_delete_present=false",
            "staging_delete_owner_present=false",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            f"FAILED_PATH={shlex.quote(_bash_path(failed_path))}",
            "write_stale_mutation_state() { printf 'journal:%s\\n' \"$1\" >> \"$RECOVERY_LOG\"; }",
            "fsync_directories() { printf 'fsync\\n' >> \"$RECOVERY_LOG\"; return 0; }",
            "verify_observed_private_staging_owner_marker() { return 0; }",
            "tree_matches_bound_topology() { return 0; }",
            "regular_file_sha256() { printf '%s\\n' \"$STALE_CANDIDATE_MANIFEST_SHA256\"; }",
            "write_cleanup_owner_marker() { printf 'owner\\n' > \"$1\"; }",
            "verify_cleanup_owner_marker() { return 0; }",
            "invoke_rm() { for argument in \"$@\"; do [ \"$argument\" != \"$FAILED_PATH\" ] || return 0; done; /usr/bin/rm \"$@\"; }",
            "remove_file_durably() { invoke_rm -f -- \"$1\"; [ ! -e \"$1\" ] && [ ! -L \"$1\" ]; }",
            "cleanup_staging() {",
            cleanup,
            "}",
            "cleanup_staging",
            "printf '%s\\n' \"$?\"",
        )
    )
    result = _run_bash_script(tmp_path / "cleanup-staging.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "1"
    assert failed_path.exists()


def test_exit_recovery_rm_false_success_keeps_old_authority_retryable(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "exit-recovery-rm-false-success"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    journal = evidence / "install-mutation-state.json"
    intercepted = case_root / "release-rm-false-success-used"
    bash_env = _write_release_rm_false_success(
        case_root / "release-rm-false-success.bash",
        journal=journal,
        marker=intercepted,
        partial=False,
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "VL360_LOCAL_RM_EXECUTOR": _bash_path(bash_env.resolve()),
            "VL360_INSTALL_FAIL_AFTER": "swap-release-root",
        },
    )

    assert first.returncode == 73, first.stderr + first.stdout
    assert intercepted.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-remove-release-root-armed"
    )
    assert not release.exists()
    cleanup_roots = [
        path
        for path in release.parent.glob(f".{release.name}.closed-candidate-cleanup.*")
        if path.is_dir()
    ]
    assert len(cleanup_roots) == 1
    assert (cleanup_roots[0] / "launch-release-manifest.json").is_file()
    assert _snapshot_tree(persistent) == persistent_before
    old_roots = list(release.parent.glob(f".{release.name}.closed-old.*"))
    assert len(old_roots) == 1
    assert not list(release.rglob(f".{release.name}.closed-old.*"))

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    _assert_python_dependency_hook_failed(evidence)
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()


@pytest.mark.parametrize(
    "partial_relative",
    (None, "launch-release-manifest.json"),
    ids=("complete_tomb", "partial_tomb"),
)
def test_exit_recovery_staging_rm_false_success_keeps_tomb_retryable(
    tmp_path: Path, closed_package, partial_relative: str | None
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / (
        "stage-rm-false-" + ("partial" if partial_relative is not None else "complete")
    )
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    intercepted = case_root / "staging-rm-false-success-used"
    rm_executor = _write_cleanup_rm_fault_executor(
        case_root / "staging-rm-false-success",
        basename_pattern=f".{release.name}.closed-staging-cleanup.*",
        marker=intercepted,
        status=0,
        partial_relative=partial_relative,
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "VL360_LOCAL_RM_EXECUTOR": _bash_path(rm_executor),
            "VL360_INSTALL_FAIL_AFTER": "detach-agent-data",
        },
    )

    assert first.returncode == 73, first.stderr + first.stdout
    assert intercepted.is_file()
    payload = json.loads(journal.read_text(encoding="utf-8"))
    assert payload["stage"] == "recovery-remove-staging-armed"
    cleanup_root = release.parent / (
        f".{release.name}.closed-staging-cleanup.{payload['attempt_id']}"
    )
    cleanup_owner = Path(f"{cleanup_root}.owner")
    assert cleanup_root.is_dir()
    assert cleanup_owner.is_file()
    assert (cleanup_root / "launch-release-manifest.json").exists() is (
        partial_relative is None
    )
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    _assert_python_dependency_hook_failed(evidence)
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()
    assert not cleanup_root.exists()
    assert not cleanup_owner.exists()


def test_replaced_staging_cleanup_tomb_is_preserved(tmp_path: Path, closed_package):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "replaced-staging-cleanup-tomb"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    intercepted = case_root / "staging-cleanup-held"
    rm_executor = _write_cleanup_rm_fault_executor(
        case_root / "staging-cleanup-held-rm",
        basename_pattern=f".{release.name}.closed-staging-cleanup.*",
        marker=intercepted,
        status=0,
    )
    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "VL360_LOCAL_RM_EXECUTOR": _bash_path(rm_executor),
            "VL360_INSTALL_FAIL_AFTER": "detach-agent-data",
        },
    )
    assert first.returncode == 73, first.stderr + first.stdout
    payload = json.loads(journal.read_text(encoding="utf-8"))
    cleanup_root = release.parent / (
        f".{release.name}.closed-staging-cleanup.{payload['attempt_id']}"
    )
    cleanup_owner = Path(f"{cleanup_root}.owner")
    assert cleanup_root.is_dir()
    assert cleanup_owner.is_file()
    removed = subprocess.run(
        [
            str(BASH),
            "-c",
            '/usr/bin/rm -rf -- "$1"',
            "replace-staging-tomb",
            _bash_path(cleanup_root),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert removed.returncode == 0, removed.stderr + removed.stdout
    cleanup_root.mkdir()
    foreign = cleanup_root / "foreign-tree.txt"
    foreign.write_text("must survive\n", encoding="ascii")

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert foreign.read_text(encoding="ascii") == "must survive\n"
    assert cleanup_owner.is_file()
    assert journal.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent


@pytest.mark.parametrize(
    "partial_relative",
    (None, "old-release-marker.txt"),
    ids=("complete_tomb", "partial_tomb"),
)
def test_retired_cleanup_rm_false_success_keeps_tomb_retryable(
    tmp_path: Path, closed_package, partial_relative: str | None
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / (
        "retired-rm-false-" + ("partial" if partial_relative else "complete")
    )
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    intercepted = case_root / "retired-rm-false-success-used"
    rm_executor = _write_cleanup_rm_fault_executor(
        case_root / "retired-rm-false-success",
        basename_pattern=f".{release.name}.closed-retired-cleanup.*",
        marker=intercepted,
        status=0,
        partial_relative=partial_relative,
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_RM_EXECUTOR": _bash_path(rm_executor)},
    )

    assert first.returncode == 2, first.stderr + first.stdout
    assert intercepted.is_file()
    payload = json.loads(journal.read_text(encoding="utf-8"))
    assert payload["stage"] == "committed-cleanup"
    cleanup_root = release.parent / (
        f".{release.name}.closed-retired-cleanup.{payload['attempt_id']}"
    )
    cleanup_owner = Path(f"{cleanup_root}.owner")
    assert cleanup_root.is_dir()
    assert cleanup_owner.is_file()
    assert (cleanup_root / "old-release-marker.txt").exists() is (
        partial_relative is None
    )
    assert not (release / "old-release-marker.txt").exists()

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    _assert_python_dependency_hook_failed(evidence)
    assert not journal.exists()
    assert not cleanup_root.exists()
    assert not cleanup_owner.exists()
    assert not list(release.parent.glob(f".{release.name}.closed-retired.*"))
    assert _snapshot_tree(persistent) == {}


def test_replaced_retired_cleanup_tomb_is_preserved(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "replaced-retired-cleanup-tomb"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    intercepted = case_root / "retired-cleanup-held"
    rm_executor = _write_cleanup_rm_fault_executor(
        case_root / "retired-cleanup-held-rm",
        basename_pattern=f".{release.name}.closed-retired-cleanup.*",
        marker=intercepted,
        status=0,
    )
    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_RM_EXECUTOR": _bash_path(rm_executor)},
    )
    assert first.returncode == 2, first.stderr + first.stdout
    payload = json.loads(journal.read_text(encoding="utf-8"))
    cleanup_root = release.parent / (
        f".{release.name}.closed-retired-cleanup.{payload['attempt_id']}"
    )
    cleanup_owner = Path(f"{cleanup_root}.owner")
    assert cleanup_root.is_dir()
    assert cleanup_owner.is_file()
    removed = subprocess.run(
        [
            str(BASH),
            "-c",
            '/usr/bin/rm -rf -- "$1"',
            "replace-retired-tomb",
            _bash_path(cleanup_root),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert removed.returncode == 0, removed.stderr + removed.stdout
    cleanup_root.mkdir()
    foreign = cleanup_root / "foreign-release-marker.txt"
    foreign.write_text("must survive\n", encoding="ascii")

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert foreign.read_text(encoding="ascii") == "must survive\n"
    assert cleanup_owner.is_file()
    assert journal.is_file()
    assert not (release / "old-release-marker.txt").exists()
    assert _snapshot_tree(persistent) == {}


def test_replaced_candidate_cleanup_tomb_is_preserved(tmp_path: Path, closed_package):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "replaced-candidate-cleanup-tomb"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    intercepted = case_root / "candidate-cleanup-held"
    rm_executor = _write_release_rm_false_success(
        case_root / "candidate-cleanup-held-rm",
        journal=journal,
        marker=intercepted,
        partial=False,
    )
    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "VL360_LOCAL_RM_EXECUTOR": _bash_path(rm_executor.resolve()),
            "VL360_INSTALL_FAIL_AFTER": "swap-release-root",
        },
    )
    assert first.returncode == 73, first.stderr + first.stdout
    cleanup_roots = [
        path
        for path in release.parent.glob(f".{release.name}.closed-candidate-cleanup.*")
        if path.is_dir()
    ]
    assert len(cleanup_roots) == 1
    cleanup_root = cleanup_roots[0]
    removed = subprocess.run(
        [
            str(BASH),
            "-c",
            '/usr/bin/rm -rf -- "$1"',
            "replace-candidate-tomb",
            _bash_path(cleanup_root),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert removed.returncode == 0, removed.stderr + removed.stdout
    assert not cleanup_root.exists()
    cleanup_root.mkdir()
    foreign = cleanup_root / "foreign-tree.txt"
    foreign.write_text("must survive\n", encoding="ascii")

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert foreign.read_text(encoding="ascii") == "must survive\n"
    assert journal.is_file()
    assert list(release.parent.glob(f".{release.name}.closed-old.*"))
    assert _snapshot_tree(persistent) != {}


def test_candidate_cleanup_tomb_is_rejected_outside_its_armed_stage(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "candidate-tomb-wrong-stage"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, _, _ = prepared
    journal = _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "persistent-detached"
    )
    interrupted_release = _snapshot_tree(release)
    payload = json.loads(journal.read_text(encoding="utf-8"))
    cleanup_root = release.parent / (
        f".{release.name}.closed-candidate-cleanup.{payload['attempt_id']}"
    )
    cleanup_root.mkdir()
    foreign = cleanup_root / "foreign-tree.txt"
    foreign.write_text("must survive\n", encoding="ascii")

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert foreign.read_text(encoding="ascii") == "must survive\n"
    assert journal.is_file()
    assert _snapshot_tree(release) == interrupted_release


def test_stale_recovery_rm_partial_false_success_preserves_both_roots(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "stale-recovery-rm-partial-success"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    journal = _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "root-swapped"
    )
    intercepted = case_root / "stale-release-rm-partial-success-used"
    bash_env = _write_release_rm_false_success(
        case_root / "stale-release-rm-partial-success.bash",
        journal=journal,
        marker=intercepted,
        partial=True,
    )

    failed = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_RM_EXECUTOR": _bash_path(bash_env.resolve())},
    )

    assert failed.returncode == 2, failed.stderr + failed.stdout
    assert "stale-install-recovery-required" in failed.stderr
    assert intercepted.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-remove-release-root-armed"
    )
    assert not release.exists()
    cleanup_roots = [
        path
        for path in release.parent.glob(f".{release.name}.closed-candidate-cleanup.*")
        if path.is_dir()
    ]
    assert len(cleanup_roots) == 1
    assert not (cleanup_roots[0] / "launch-release-manifest.json").exists()
    assert _snapshot_tree(persistent) == persistent_before
    old_roots = list(release.parent.glob(f".{release.name}.closed-old.*"))
    assert len(old_roots) == 1
    assert not list(release.rglob(f".{release.name}.closed-old.*"))

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    _assert_python_dependency_hook_failed(evidence)
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()


def test_initial_root_rename_side_effect_then_error_restores_full_old_authority(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "initial-root-rename-side-effect-error"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    injected = case_root / "initial-root-rename-failed"
    bash_env = _write_mv_side_effect_fault(
        case_root / "fail-initial-root-rename.bash",
        marker=injected,
        condition=(
            f'"$source" == \'{_bash_path(release)}\' '
            f'&& "$(basename -- "$destination")" == \'.{release.name}.closed-old.\'*'
        ),
        failure="return 62",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert first.returncode == 62, first.stderr + first.stdout
    assert injected.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_initial_root_rename_rc0_without_effect_fails_and_restores_old_authority(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "initial-root-rename-no-effect"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    injected = case_root / "initial-root-rename-no-effect-used"
    bash_env = _write_mv_no_effect_success(
        case_root / "initial-root-rename-no-effect.bash",
        marker=injected,
        condition=(
            f'"$source" == \'{_bash_path(release)}\' '
            f'&& "$(basename -- "$destination")" == \'.{release.name}.closed-old.\'*'
        ),
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 1, result.stderr + result.stdout
    assert injected.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == {}
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_candidate_root_rename_rc0_without_effect_fails_before_activation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "candidate-root-rename-no-effect"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    injected = case_root / "candidate-root-rename-no-effect-used"
    owner_cleanup_started = case_root / "candidate-owner-cleanup-started"
    journal = evidence / "install-mutation-state.json"
    bash_env = _write_mv_no_effect_success(
        case_root / "candidate-root-rename-no-effect.bash",
        marker=injected,
        condition=(
            f'"$(basename -- "$source")" == ".{release.name}.closed-stage."* '
            f'&& "$destination" == \'{_bash_path(release)}\''
        ),
    )
    bash_env.write_text(
        bash_env.read_text(encoding="ascii")
        + "rm() {\n"
        + "  local argument\n"
        + "  for argument in \"$@\"; do\n"
        + f"    if [[ \"$(basename -- \"$argument\")\" == .{release.name}.closed-stage.*.owner ]] "
        + f"&& [ -f '{_bash_path(journal)}' ] "
        + "&& grep -Fq '\"stage\": \"swap-release-root-armed\"' "
        + f"'{_bash_path(journal)}'; then : > '{_bash_path(owner_cleanup_started)}'; fi\n"
        + "  done\n"
        + "  /usr/bin/rm \"$@\"\n"
        + "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 1, result.stderr + result.stdout
    assert injected.is_file()
    assert not owner_cleanup_started.exists()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == {}
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_staging_owner_cleanup_bypasses_rm_shadow_before_activation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "staging-owner-rm-no-effect"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    injected = case_root / "staging-owner-rm-no-effect-used"
    bash_env = case_root / "staging-owner-rm-no-effect.bash"
    bash_env.write_text(
        "rm() {\n"
        "  local argument\n"
        "  for argument in \"$@\"; do\n"
        f"    if [[ \"$(basename -- \"$argument\")\" == .{release.name}.closed-stage.*.owner ]] "
        f"&& [ -f '{_bash_path(journal)}' ] "
        "&& grep -Fq '\"stage\": \"swap-release-root-armed\"' "
        f"'{_bash_path(journal)}' && [ ! -f '{_bash_path(injected)}' ]; then\n"
        f"      : > '{_bash_path(injected)}'\n"
        "      return 0\n"
        "    fi\n"
        "  done\n"
        "  /usr/bin/rm \"$@\"\n"
        "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert not injected.exists()
    assert (release / "launch-release-manifest.json").is_file()
    assert not (release / "old-release-marker.txt").exists()
    assert persistent.is_dir()
    assert _snapshot_tree(persistent) == {}
    assert not list(release.parent.glob(f".{release.name}.closed-stage.*.owner"))
    assert not journal.exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


@pytest.mark.parametrize("target", ("staging", "owner"))
def test_failed_install_cleanup_bypasses_rm_shadow_for_private_staging(
    tmp_path: Path, closed_package, target: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"cleanup-rm-shadow-{target}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    intercepted = case_root / f"cleanup-rm-shadow-{target}-used"
    bash_env = case_root / f"cleanup-rm-shadow-{target}.bash"
    target_condition = (
        '"$argument" == "$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage."* '
        '&& "$argument" != *.owner'
        if target == "staging"
        else '"$argument" == "$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage."*.owner'
    )
    bash_env.write_text(
        "rm() {\n"
        "  local argument\n"
        "  for argument in \"$@\"; do\n"
        "    if [ -n \"${RELEASE_PARENT:-}\" ] "
        "&& [ -n \"${RELEASE_NAME:-}\" ] "
        f"&& [[ {target_condition} ]] "
        f"&& [ ! -f '{_bash_path(intercepted)}' ]; then\n"
        f"      : > '{_bash_path(intercepted)}'\n"
        "      return 0\n"
        "    fi\n"
        "  done\n"
        "  /usr/bin/rm \"$@\"\n"
        "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 19, result.stderr + result.stdout
    assert not intercepted.exists()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_primary_local_empty_detach_rc0_without_effect_fails_closed(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "primary-empty-detach-no-effect"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    current_data = release / "agent" / "data"
    for child in current_data.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    expected_release = _snapshot_tree(release)
    injected = case_root / "primary-empty-detach-no-effect-used"
    bash_env = _write_mv_no_effect_success(
        case_root / "primary-empty-detach-no-effect.bash",
        marker=injected,
        condition=(
            f'"$source" == \'{_bash_path(current_data)}\' '
            f'&& "$destination" == \'{_bash_path(persistent)}\''
        ),
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 1, result.stderr + result.stdout
    assert injected.is_file()
    assert current_data.is_dir()
    assert _snapshot_tree(release) == expected_release
    assert persistent.is_dir()
    assert _snapshot_tree(persistent) == {}
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


@pytest.mark.parametrize(
    ("fault", "expected_status"),
    (("side-effect-error", 64), ("no-effect-success", 1)),
)
def test_primary_local_persistent_restore_requires_completed_rename(
    tmp_path: Path, closed_package, fault: str, expected_status: int
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"primary-persistent-restore-{fault}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    injected = case_root / "primary-persistent-restore-fault-used"
    condition = (
        f'"$source" == \'{_bash_path(persistent)}\' '
        f'&& "$destination" == \'{_bash_path(release / "agent" / "data")}\''
    )
    if fault == "side-effect-error":
        bash_env = _write_mv_side_effect_fault(
            case_root / "primary-persistent-restore-fault.bash",
            marker=injected,
            condition=condition,
            failure="return 64",
        )
    else:
        bash_env = _write_mv_no_effect_success(
            case_root / "primary-persistent-restore-fault.bash",
            marker=injected,
            condition=condition,
        )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == expected_status, result.stderr + result.stdout
    assert injected.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_exit_recovery_persistent_detach_rc0_without_effect_preserves_data(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "recovery-persistent-detach-no-effect"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    journal = evidence / "install-mutation-state.json"
    injected = case_root / "recovery-persistent-detach-no-effect-used"
    bash_env = case_root / "recovery-persistent-detach-no-effect.bash"
    bash_env.write_text(
        "mv() {\n"
        "  local source destination\n"
        "  if [ \"${1:-}\" = -- ]; then source=${2:-}; destination=${3:-}; "
        "else source=${1:-}; destination=${2:-}; fi\n"
        f"  if [ \"$source\" = '{_bash_path(release / 'agent' / 'data')}' ] "
        f"&& [ \"$destination\" = '{_bash_path(persistent)}' ] "
        f"&& [ -f '{_bash_path(journal)}' ] "
        "&& grep -Fq '\"stage\": \"recovery-detach-persistent-armed\"' "
        f"'{_bash_path(journal)}' && [ ! -f '{_bash_path(injected)}' ]; then\n"
        f"    : > '{_bash_path(injected)}'\n"
        "    return 0\n"
        "  fi\n"
        "  /usr/bin/mv \"$@\"\n"
        "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_INSTALL_FAIL_AFTER": "restore-bind-agent-data",
        },
    )

    assert result.returncode == 73, result.stderr + result.stdout
    assert injected.is_file()
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    assert _snapshot_tree(persistent) == {}
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-detach-persistent-armed"
    )
    assert len(list(release.parent.glob(f".{release.name}.closed-old.*"))) == 1


def test_recovery_persistent_restore_fsyncs_rename_before_next_journal(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    helper = source[
        source.index("restore_local_persistent_for_recovery()") : source.index(
            "verify_recovered_persistent_state()"
        )
    ]
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    (release / "agent").mkdir(parents=True)
    persistent.mkdir()
    (persistent / "app.db").write_text("data\n", encoding="ascii")
    persistent_before = _snapshot_tree(persistent)
    log = tmp_path / "restore.log"
    script = "\n".join(
        (
            "set -u",
            "LOCAL_REHEARSAL=true",
            f"RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"PERSISTENT_AGENT_DATA_ROOT={shlex.quote(_bash_path(persistent))}",
            "PERSISTENT_ATTACHED_TO_RELEASE=false",
            "PERSISTENT_DETACHED=true",
            "PERSISTENT_MOUNT_STATE_UNKNOWN=false",
            "MUTATION_STAGE=none",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            "write_mutation_state() { MUTATION_STAGE=\"$1\"; printf 'journal:%s\\n' \"$1\" >> \"$RECOVERY_LOG\"; }",
            "fsync_directories() { printf 'fsync:%s\\n' \"$*\" >> \"$RECOVERY_LOG\"; return 71; }",
            helper,
            "attach_persistent_to_release_for_recovery",
            "printf '%s|%s|%s|%s\\n' \"$?\" \"$MUTATION_STAGE\" \"$PERSISTENT_ATTACHED_TO_RELEASE\" \"$PERSISTENT_DETACHED\"",
        )
    )
    result = _run_bash_script(tmp_path / "restore-persistent.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "71|recovery-restore-persistent-armed|true|false"
    assert log.read_text(encoding="ascii").splitlines() == [
        "journal:recovery-restore-persistent-armed",
        f"fsync:{_bash_path(persistent.parent)} {_bash_path(release / 'agent')}",
    ]
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    assert not persistent.exists()


def test_retire_rename_side_effect_then_error_leaves_retryable_tree_authority(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "retire-rename-side-effect-error"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, hook_log, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    injected = case_root / "retire-rename-failed"
    bash_env = _write_mv_side_effect_fault(
        case_root / "fail-retire-rename.bash",
        marker=injected,
        condition=(
            f'"$(basename -- "$source")" == \'.{release.name}.closed-old.\'* '
            f'&& "$(basename -- "$destination")" == \'.{release.name}.closed-retired.\'*'
        ),
        failure="return 63",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert first.returncode == 63, first.stderr + first.stdout
    assert injected.is_file()
    assert release.is_dir()
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    committed_release = _snapshot_tree(release)
    assert "launch-release-manifest.json" in committed_release
    assert "old-release-marker.txt" not in committed_release
    assert _snapshot_tree(persistent) == {}
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "retire-old-root-armed"
    )
    retired_roots = list(release.parent.glob(f".{release.name}.closed-retired.*"))
    assert len(retired_roots) == 1
    expected_retired = {
        name: raw
        for name, raw in before_release.items()
        if not name.startswith("agent/data/")
    }
    assert _snapshot_tree(retired_roots[0]) == expected_retired

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    _assert_python_dependency_hook_failed(evidence)
    assert sum(
        line.startswith("systemd-units|")
        for line in hook_log.read_text(encoding="ascii").splitlines()
    ) == 2
    assert _snapshot_tree(release) == committed_release
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_retire_rename_rc0_without_effect_fails_and_rolls_back_candidate(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "retire-root-rename-no-effect"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, _ = prepared
    injected = case_root / "retire-root-rename-no-effect-used"
    bash_env = _write_mv_no_effect_success(
        case_root / "retire-root-rename-no-effect.bash",
        marker=injected,
        condition=(
            f'"$(basename -- "$source")" == \'.{release.name}.closed-old.\'* '
            f'&& "$(basename -- "$destination")" == \'.{release.name}.closed-retired.\'*'
        ),
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 1, result.stderr + result.stdout
    assert injected.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == {}
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def _interrupt_recovery_mutation(
    package,
    case_root: Path,
    prepared,
    *,
    recovery_stage: str,
    command: str,
):
    _, _, evidence, _, _, _, values = prepared
    interrupted = case_root / f"interrupted-{recovery_stage}"
    journal = evidence / "install-mutation-state.json"
    bash_env = case_root / f"kill-at-{recovery_stage}.bash"
    if command == "rm":
        rm_executor = case_root / f"kill-at-{recovery_stage}-rm"
        rm_executor.write_text(
            "#!/usr/bin/env bash\n"
            "/usr/bin/rm \"$@\"\n"
            "status=$?\n"
            f"if [ -f '{_bash_path(journal)}' ] "
            f"&& grep -Fq '\"stage\": \"{recovery_stage}\"' '{_bash_path(journal)}'; then\n"
            f"  : > '{_bash_path(interrupted)}'\n"
            "  kill -9 \"$PPID\"\n"
            "  kill -9 \"$$\"\n"
            "fi\n"
            "exit \"$status\"\n",
            encoding="ascii",
        )
        rm_executor.chmod(0o755)
    else:
        bash_env.write_text(
            f"{command}() {{\n"
            f"  /usr/bin/{command} \"$@\"\n"
            "  status=$?\n"
            f"  if [ -f '{_bash_path(journal)}' ] "
            f"&& grep -Fq '\"stage\": \"{recovery_stage}\"' '{_bash_path(journal)}'; then\n"
            f"    : > '{_bash_path(interrupted)}'\n"
            "    kill -9 \"$$\"\n"
            "  fi\n"
            "  return \"$status\"\n"
            "}\n",
            encoding="ascii",
        )
    env = os.environ.copy()
    env.update(values)
    env.pop("VL360_INSTALL_FAIL_AFTER", None)
    if command == "rm":
        env["VL360_LOCAL_RM_EXECUTOR"] = _bash_path(rm_executor.resolve())
    else:
        env["BASH_ENV"] = _bash_path(bash_env)
    result = subprocess.run(
        _installer_command(package, case_root, prepared),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, result.stderr + result.stdout
    assert interrupted.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == recovery_stage


def test_stale_absent_staging_owner_is_fsynced_before_journal_clear(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index("  local stage_owner_valid=false")
    cleanup = source[
        start : source.index('  if [ "$committed_recovery" = true ]; then', start)
    ]
    staging = tmp_path / ".release.closed-stage.321"
    log = tmp_path / "owner-absence.log"
    script = "\n".join(
        (
            "set -u",
            "entry_stage=recovery-remove-staging-owner-armed",
            "committed_recovery=false",
            "STALE_ATTEMPT_ID=" + "a" * 32,
            "STALE_PID=321",
            "STALE_CANDIDATE_RELEASE_ROOT_IDENTITY=1:2",
            "STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256=" + "b" * 64,
            "STALE_CANDIDATE_MANIFEST_SHA256=" + "c" * 64,
            "CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT=/snapshot",
            f"STALE_STAGING_ROOT={shlex.quote(_bash_path(staging))}",
            "stale_stage_owner=\"$STALE_STAGING_ROOT.owner\"",
            f"staging_delete_root={shlex.quote(_bash_path(tmp_path / ('.release.closed-staging-cleanup.' + 'a' * 32)))}",
            f"staging_delete_owner={shlex.quote(_bash_path(tmp_path / ('.release.closed-staging-cleanup.' + 'a' * 32 + '.owner')))}",
            "staging_delete_present=false",
            "staging_delete_owner_present=false",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            "write_stale_mutation_state() { printf 'journal:%s\\n' \"$1\" >> \"$RECOVERY_LOG\"; }",
            "fsync_directories() { printf 'fsync:%s\\n' \"$*\" >> \"$RECOVERY_LOG\"; return 0; }",
            "cleanup_staging() {",
            cleanup,
            "}",
            "cleanup_staging",
            "printf '%s\\n' \"$?\"",
        )
    )
    result = _run_bash_script(tmp_path / "stale-owner-absence-fsync.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "0"
    assert log.is_file()
    assert log.read_text(encoding="ascii").splitlines() == [
        f"fsync:{_bash_path(staging.parent)}"
    ]


@pytest.mark.parametrize(
    ("initial_stage", "recovery_stage", "command", "persistent_must_exist"),
    (
        (
            "persistent-restored",
            "recovery-remove-empty-persistent-root-armed",
            "rmdir",
            True,
        ),
        (
            "persistent-restored",
            "recovery-detach-persistent-armed",
            "mv",
            True,
        ),
        ("root-swapped", "recovery-remove-release-root-armed", "rm", False),
        ("root-swapped", "recovery-restore-old-root-armed", "mv", False),
        ("persistent-detached", "recovery-restore-persistent-armed", "mv", False),
        (
            "persistent-detached",
            "recovery-create-persistent-root-armed",
            "mkdir",
            False,
        ),
        ("persistent-detached", "recovery-remove-staging-armed", "rm", False),
        (
            "persistent-detached",
            "recovery-remove-staging-owner-armed",
            "rm",
            False,
        ),
    ),
)
def test_stale_recovery_resumes_after_each_interrupted_mutation(
    tmp_path: Path,
    closed_package,
    initial_stage: str,
    recovery_stage: str,
    command: str,
    persistent_must_exist: bool,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / recovery_stage
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, _ = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    _interrupt_at_journal_stage(closed_package, case_root, prepared, initial_stage)
    if persistent_must_exist and not persistent.exists():
        persistent.mkdir()

    _interrupt_recovery_mutation(
        closed_package,
        case_root,
        prepared,
        recovery_stage=recovery_stage,
        command=command,
    )

    retry = _invoke_installer(closed_package, case_root, prepared)

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    assert _snapshot_tree(persistent) == {}
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_stale_recovery_retries_a_failed_journaled_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "failed-recovery-mkdir"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, values = prepared
    persistent_before = _snapshot_tree(release / "agent" / "data")
    _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "persistent-detached"
    )
    journal = evidence / "install-mutation-state.json"
    failed = case_root / "recovery-mkdir-failed"
    bash_env = case_root / "fail-recovery-mkdir.bash"
    bash_env.write_text(
        "mkdir() {\n"
        f"  if [ -f '{_bash_path(journal)}' ] "
        "&& grep -Fq '\"stage\": \"recovery-create-persistent-root-armed\"' "
        f"'{_bash_path(journal)}' && [ ! -f '{_bash_path(failed)}' ]; then\n"
        f"    : > '{_bash_path(failed)}'\n"
        "    return 61\n"
        "  fi\n"
        "  /usr/bin/mkdir \"$@\"\n"
        "}\n",
        encoding="ascii",
    )
    env = os.environ.copy()
    env.update(values)
    env["BASH_ENV"] = _bash_path(bash_env)
    failed_retry = subprocess.run(
        _installer_command(closed_package, case_root, prepared),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert failed_retry.returncode == 2, failed_retry.stderr + failed_retry.stdout
    assert failed.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "recovery-create-persistent-root-armed"
    )

    retry = _invoke_installer(closed_package, case_root, prepared)

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert _snapshot_tree(release / "agent" / "data") == persistent_before
    assert _snapshot_tree(persistent) == {}
    assert not journal.exists()


@pytest.mark.parametrize(
    ("fault", "expected_status", "expected_stage", "data_at_persistent"),
    (
        (
            "rmdir-no-effect",
            1,
            "recovery-remove-empty-persistent-root-armed",
            False,
        ),
        ("mv-no-effect", 1, "recovery-detach-persistent-armed", False),
        ("mv-side-effect-error", 65, "recovery-detach-persistent-armed", True),
    ),
)
def test_stale_local_detach_classifies_mutation_topology(
    tmp_path: Path,
    fault: str,
    expected_status: int,
    expected_stage: str,
    data_at_persistent: bool,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index(
        '        if stale_tree_state "$current_data"; then',
        source.index('  if [ "$old_present" = true ]; then'),
    )
    block = source[
        start : source.index(
            '      else\n        tree_matches_snapshot "$STALE_PERSISTENT_ROOT"',
            start,
        )
    ]
    remove_helper = source[
        source.index("remove_empty_directory_durably()") : source.index(
            "inspect_stale_mount()"
        )
    ]
    release = tmp_path / "release"
    current_data = release / "agent" / "data"
    persistent = tmp_path / "persistent"
    current_data.mkdir(parents=True)
    (current_data / "app.db").write_text("data\n", encoding="ascii")
    persistent.mkdir()
    log = tmp_path / "detach.log"
    script = "\n".join(
        (
            "set -u",
            f"FAULT={shlex.quote(fault)}",
            f"current_data={shlex.quote(_bash_path(current_data))}",
            f"STALE_PERSISTENT_ROOT={shlex.quote(_bash_path(persistent))}",
            "SNAPSHOT_BEFORE=/snapshot",
            "entry_stage=persistent-restored",
            "STALE_STAGE=persistent-restored",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            "stale_tree_state() {",
            "  [ ! -L \"$1\" ] || return 3",
            "  [ -e \"$1\" ] || return 1",
            "  [ -d \"$1\" ] || return 3",
            "  [ -z \"$(find \"$1\" -mindepth 1 -print -quit)\" ] && return 2",
            "  return 0",
            "}",
            "write_stale_mutation_state() { STALE_STAGE=\"$1\"; printf 'journal:%s\\n' \"$1\" >> \"$RECOVERY_LOG\"; }",
            "fsync_directories() { printf 'fsync:%s\\n' \"$*\" >> \"$RECOVERY_LOG\"; }",
            "rmdir() {",
            "  if [ \"$FAULT\" = rmdir-no-effect ]; then printf 'rmdir-no-effect\\n' >> \"$RECOVERY_LOG\"; return 0; fi",
            '  /usr/bin/rmdir "$@"',
            "}",
            "mv() {",
            "  printf 'mv\\n' >> \"$RECOVERY_LOG\"",
            "  case \"$FAULT\" in",
            "    mv-no-effect) return 0 ;;",
            '    mv-side-effect-error) /usr/bin/mv "$@"; return 65 ;;',
            "  esac",
            '  /usr/bin/mv "$@"',
            "}",
            remove_helper,
            "run_detach() {",
            block,
            "}",
            "run_detach",
            "status=$?",
            "if [ \"$status\" -eq 0 ]; then printf 'rm-release\\n' >> \"$RECOVERY_LOG\"; /usr/bin/rm -rf -- \"$(dirname -- \"$current_data\")/..\"; fi",
            "printf '%s|%s\\n' \"$status\" \"$STALE_STAGE\"",
        )
    )

    result = _run_bash_script(tmp_path / "stale-local-detach.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == f"{expected_status}|{expected_stage}"
    lines = log.read_text(encoding="ascii").splitlines()
    assert "rm-release" not in lines
    assert current_data.is_dir() is (not data_at_persistent)
    assert (persistent / "app.db").is_file() is data_at_persistent
    if fault == "rmdir-no-effect":
        assert "mv" not in lines


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux live mount harness only"
)
def test_production_shaped_retry_reconciles_stale_journal_without_live_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "production-shaped-stale-recovery"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, _, _, values = prepared
    journal = _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "detach-agent-data-armed"
    )
    shutil.copytree(release / "agent" / "data", persistent, dirs_exist_ok=True)
    persistent_before = _snapshot_tree(persistent)
    payload = json.loads(journal.read_text(encoding="utf-8"))
    payload["local_rehearsal"] = False
    journal.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    runtime = case_root / "runtime"
    for name, status in (
        ("install-python-dependencies", 19),
        ("install-nuxt-production-dependencies", 0),
        ("verify-systemd-units", 0),
    ):
        hook = runtime / name
        hook.write_text(f"#!/usr/bin/env bash\nexit {status}\n", encoding="ascii")
        hook.chmod(0o755)
    mount_log = case_root / "mount-authority.log"
    mount_authority = case_root / "mount-authority.sh"
    mount_authority.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        f"printf '%s\\n' \"$1\" >> '{_bash_path(mount_log)}'\n"
        "[ \"$1\" = findmnt ] || exit 70\n"
        f"source_path='{_bash_path(persistent)}'\n"
        "target_path=$4\n"
        "printf '{\"filesystems\":[{\"source\":\"%s\",\"target\":\"%s\",\"options\":\"rw,bind\"}]}\\n' "
        "\"$source_path\" \"$target_path\"\n",
        encoding="ascii",
    )
    mount_authority.chmod(0o755)
    env = os.environ.copy()
    env.update(values)
    for name in (
        "VL360_PYTHON_DEPENDENCY_HOOK",
        "VL360_NUXT_DEPENDENCY_HOOK",
        "VL360_UNIT_VERIFY_HOOK",
        "VL360_LOCAL_REHEARSAL_SENTINEL",
        "VL360_INSTALL_FAIL_AFTER",
    ):
        env.pop(name, None)
    retry = subprocess.run(
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
            "--migration-gate-evidence",
            _bash_path(case_root / "migration-gate.json"),
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

    assert retry.returncode == 19, retry.stderr + retry.stdout
    assert not journal.exists()
    assert mount_log.read_text(encoding="ascii").splitlines() == ["findmnt"]
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == persistent_before


@pytest.mark.parametrize("invalid_evidence", ("wrong-source", "invalid-options"))
@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux live mount harness only"
)
def test_stale_recovery_preserves_authorities_when_findmnt_evidence_is_invalid(
    tmp_path: Path, closed_package, invalid_evidence: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"stale-invalid-findmnt-{invalid_evidence}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, hook_log, values = prepared
    journal = _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "root-swapped"
    )
    current_data = release / "agent" / "data"
    current_data.mkdir()
    shutil.copytree(persistent, current_data, dirs_exist_ok=True)
    payload = json.loads(journal.read_text(encoding="utf-8"))
    payload["local_rehearsal"] = False
    journal.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    runtime = case_root / "runtime"
    for name in (
        "install-python-dependencies",
        "install-nuxt-production-dependencies",
        "verify-systemd-units",
    ):
        hook = runtime / name
        hook.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="ascii")
        hook.chmod(0o755)
    wrong_source = case_root / "wrong-source"
    wrong_source.mkdir()
    mount_log = case_root / "mount-authority.log"
    mount_authority = case_root / "mount-authority.sh"
    observed_source = wrong_source if invalid_evidence == "wrong-source" else persistent
    observed_options = "rw,bind" if invalid_evidence == "wrong-source" else "rw"
    mount_authority.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        f"printf '%s\\n' \"$1\" >> '{_bash_path(mount_log)}'\n"
        "[ \"$1\" = findmnt ] || exit 70\n"
        f"source_path='{_bash_path(observed_source)}'\n"
        "target_path=$4\n"
        f"printf '{{\"filesystems\":[{{\"source\":\"%s\",\"target\":\"%s\",\"options\":\"{observed_options}\"}}]}}\\n' "
        '"$source_path" "$target_path"\n',
        encoding="ascii",
    )
    mount_authority.chmod(0o755)
    for name in (
        "VL360_PYTHON_DEPENDENCY_HOOK",
        "VL360_NUXT_DEPENDENCY_HOOK",
        "VL360_UNIT_VERIFY_HOOK",
        "VL360_LOCAL_REHEARSAL_SENTINEL",
        "VL360_INSTALL_FAIL_AFTER",
    ):
        values.pop(name, None)
    old_root = next(release.parent.glob(f".{release.name}.closed-old.*"))
    release_before = _snapshot_tree(release)
    persistent_before = _snapshot_tree(persistent)
    old_root_before = _snapshot_tree(old_root)
    journal_before = journal.read_bytes()
    hook_log_before = hook_log.read_bytes()
    env = os.environ.copy()
    env.update(values)

    retry = subprocess.run(
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
            "--migration-gate-evidence",
            _bash_path(case_root / "migration-gate.json"),
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

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert mount_log.read_text(encoding="ascii").splitlines() == ["findmnt"]
    assert hook_log.read_bytes() == hook_log_before
    assert _snapshot_tree(release) == release_before
    assert _snapshot_tree(persistent) == persistent_before
    assert _snapshot_tree(old_root) == old_root_before
    assert journal.read_bytes() == journal_before


def test_stale_recovery_refuses_different_retry_authorities(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    first_root = tmp_path / "stale-original"
    second_root = tmp_path / "stale-different-retry"
    first_prepared = _prepare_case(first_root, closed_package)
    second_prepared = _prepare_case(second_root, closed_package)
    first_release, first_persistent, first_evidence, _, _, _, _ = (
        first_prepared
    )
    second_release, second_persistent, _, second_release_before, second_persistent_before, _, second_values = (
        second_prepared
    )
    first_bytes = _snapshot_tree(first_release / "agent" / "data")
    _interrupt_at_journal_stage(
        closed_package, first_root, first_prepared, "persistent-detached"
    )
    journal = first_evidence / "install-mutation-state.json"
    journal_before = journal.read_bytes()
    snapshot_before = (first_evidence / "persistent-before.json").read_bytes()
    stale_artifacts = sorted(first_release.parent.glob(f".{first_release.name}.closed-*"))
    assert stale_artifacts

    second_env = os.environ.copy()
    second_env.update(second_values)
    retry = subprocess.run(
        _installer_command(
            closed_package,
            second_root,
            second_prepared,
            evidence_arg=_bash_path(first_evidence),
        ),
        cwd=ROOT,
        env=second_env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert journal.read_bytes() == journal_before
    assert (first_evidence / "persistent-before.json").read_bytes() == snapshot_before
    assert not (first_release / "agent" / "data").exists()
    assert _snapshot_tree(first_persistent) == first_bytes
    assert sorted(first_release.parent.glob(f".{first_release.name}.closed-*")) == stale_artifacts
    assert _snapshot_tree(second_release) == second_release_before
    assert _snapshot_tree(second_persistent) == second_persistent_before


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux live mount harness only"
)
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
    tmp_path: Path, closed_package, monkeypatch: pytest.MonkeyPatch
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    inherited_root = tmp_path / "inherited-local-rehearsal"
    inherited_root.mkdir()
    inherited_sentinel = inherited_root / ".vl360-local-rehearsal"
    inherited_sentinel.write_text(
        "vinhlong360-local-rehearsal-v1\n", encoding="ascii"
    )
    monkeypatch.setenv(
        "VL360_LOCAL_REHEARSAL_SENTINEL", _bash_path(inherited_sentinel)
    )
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
            "--migration-gate-evidence",
            _bash_path(case_root / "migration-gate.json"),
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


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux live mount harness only"
)
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


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux live mount harness only"
)
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


def test_verifier_cli_executes_every_requested_installed_authority(
    tmp_path: Path, closed_package, monkeypatch, capsys
):
    module = _load_module("task5_verify_cli_authorities", VERIFY)
    root = tmp_path / "installed"
    root.mkdir()
    with tarfile.open(closed_package.archive, "r:gz") as archive:
        archive.extractall(root, filter="data")
    (root / "agent" / "data").mkdir(parents=True)
    persistent = tmp_path / "persistent"
    persistent.mkdir()
    systemd = tmp_path / "systemd"
    systemd.mkdir()
    environment = tmp_path / "external.env"
    environment.write_text("SAFE=1\n", encoding="ascii")
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def capture(name, result):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return inner

    monkeypatch.setattr(
        module,
        "_verify_config_ingress_unit_digests",
        capture("config", ("config/launch-indexing-policy.json",)),
    )
    monkeypatch.setattr(
        module,
        "_verify_systemd_unit_destination",
        capture("systemd", ("ops/systemd/vl-agent.service",)),
    )
    monkeypatch.setattr(
        module,
        "_verify_environment_authority",
        capture("environment", {"environment_authority_verified": True}),
    )
    monkeypatch.setattr(
        module,
        "_verify_persistent_agent_data_mount",
        capture(
            "persistent",
            {
                "persistent_agent_data_mount_verified": True,
                "persistent_agent_data_mount_mode": "local-rehearsal",
            },
        ),
    )

    status = module.main(
        [
            "--installed-root",
            str(root),
            "--persistent-agent-data-root",
            str(persistent),
            "--verify-config-ingress-unit-digests",
            "--verify-persistent-agent-data-mount",
            "--local-rehearsal",
            "--systemd-unit-root",
            str(systemd),
            "--verify-systemd-unit-destination",
            "--environment-authority",
            str(environment),
            "--verify-environment-authority",
            "--require-closed",
        ]
    )

    assert status == 0, capsys.readouterr().err
    assert [name for name, _, _ in calls] == [
        "config",
        "systemd",
        "environment",
        "persistent",
        "systemd",
        "environment",
        "persistent",
    ]
    for index in (1, 4):
        assert calls[index][1][1] == systemd
    for index in (2, 5):
        assert calls[index][1] == (root, environment)
    for index in (3, 6):
        assert calls[index][1][:2] == (root, persistent)
        assert calls[index][2] == {
            "local_rehearsal": True,
            "findmnt_evidence": None,
        }


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
    hook_entries = [line.split("|", 1) for line in hook_lines]
    assert [entry[0] for entry in hook_entries] == [
        "python-dependencies",
        "nuxt-production-dependencies",
        "systemd-units",
    ]
    unit_destination = tmp_path / "success" / "runtime" / "systemd-units"
    python_args = shlex.split(hook_entries[0][1])
    stage_root = python_args[1]
    assert Path(stage_root).name.startswith(".release.closed-stage.")
    assert python_args == [
        "--release-root",
        stage_root,
        "--requirements",
        f"{stage_root}/requirements.txt",
    ]
    assert shlex.split(hook_entries[1][1]) == [
        "--project-root",
        f"{stage_root}/web-nuxt",
        "--production-only",
    ]
    assert shlex.split(hook_entries[2][1]) == [
        "--unit-root",
        _bash_path(unit_destination),
        "--manifest",
        f"{_bash_path(release)}/launch-release-manifest.json",
    ]
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


@pytest.mark.parametrize(
    ("field", "expected_error"),
    (
        ("archive_sha256", "migration-gate-archive-mismatch"),
        ("environment_pin_sha256", "migration-gate-environment-mismatch"),
    ),
)
def test_migration_gate_binding_fails_before_fresh_install_mutation(
    tmp_path: Path,
    closed_package,
    field: str,
    expected_error: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / field
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, hook_log, _ = prepared
    migration_gate = case_root / "migration-gate.json"
    payload = _write_migration_gate_evidence(migration_gate, closed_package, case_root / "external.env")
    payload[field] = "0" * 64
    migration_gate.write_text(json.dumps(payload) + "\n", encoding="ascii")

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        migration_gate_evidence_arg=_bash_path(migration_gate),
    )

    assert result.returncode == 2
    assert expected_error in result.stderr
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not hook_log.exists()
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(case_root.glob(".release.closed-stage.*"))
    assert not (evidence / "migration-gate-evidence.json").exists()


@pytest.mark.parametrize(
    ("field", "expected_error"),
    (
        ("migration_set_sha256", "migration-gate-migration-set-mismatch"),
        ("migration_latest", "migration-gate-latest-mismatch"),
        ("verifier_sha256", "migration-gate-tool-digest-mismatch"),
        ("checker_sha256", "migration-gate-tool-digest-mismatch"),
        ("installer_sha256", "migration-gate-tool-digest-mismatch"),
    ),
)
def test_migration_gate_binding_rejects_release_authority_mismatch_before_mutation(
    tmp_path: Path,
    closed_package,
    field: str,
    expected_error: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / field
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, hook_log, _ = prepared
    migration_gate = case_root / "migration-gate.json"
    payload = _write_migration_gate_evidence(
        migration_gate, closed_package, case_root / "external.env"
    )
    if field == "migration_latest":
        payload[field] = {"version": 69, "migration": "069_forged.sql"}
        payload["observed_database"] = dict(payload[field])
    else:
        payload[field] = "0" * 64
    migration_gate.write_text(json.dumps(payload) + "\n", encoding="ascii")

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        migration_gate_evidence_arg=_bash_path(migration_gate),
    )

    assert result.returncode == 2
    assert expected_error in result.stderr
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not hook_log.exists()
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(case_root.glob(".release.closed-stage.*"))
    assert not (evidence / "migration-gate-evidence.json").exists()


def test_migration_gate_binding_is_carried_into_success_summary(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "migration-gate-success"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        migration_gate_evidence_arg=_bash_path(case_root / "migration-gate.json"),
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((evidence / "install-summary.json").read_text(encoding="utf-8"))
    gate = json.loads((case_root / "migration-gate.json").read_text(encoding="ascii"))
    assert summary["archive_sha256"] == gate["archive_sha256"]
    assert summary["environment_pin_sha256"] == gate["environment_pin_sha256"]
    assert summary["migration_gate_evidence_sha256"] == hashlib.sha256(
        (case_root / "migration-gate.json").read_bytes()
    ).hexdigest()
    assert summary["migration_set_sha256"] == gate["migration_set_sha256"]
    assert summary["migration_latest"] == gate["migration_latest"]
    assert summary["observed_database"] == gate["observed_database"]


def test_missing_agent_data_fails_closed_without_creating_live_topology(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "missing-agent-data"
    prepared = _prepare_case(case_root, closed_package, fail_after="detach-agent-data")
    release, persistent, evidence, _, before_persistent, _, _ = prepared
    shutil.rmtree(release / "agent" / "data")
    before_release = _snapshot_tree(release)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "agent-data-required" in result.stderr
    assert _snapshot_tree(release) == before_release
    assert not (release / "agent" / "data").exists()
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not (evidence / "install-recovery.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_agent_data_ancestor_symlink_is_rejected_before_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "agent-ancestor-symlink"
    prepared = _prepare_case(case_root, closed_package, fail_after="detach-agent-data")
    release, persistent, evidence, _, before_persistent, _, _ = prepared
    external_agent = case_root / "external-agent"
    shutil.move(release / "agent", external_agent)
    try:
        (release / "agent").symlink_to(external_agent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    external_before = _snapshot_tree(external_agent)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "agent-data-symlink-forbidden" in result.stderr
    assert (release / "agent").is_symlink()
    assert _snapshot_tree(external_agent) == external_before
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not (evidence / "install-recovery.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


@pytest.mark.parametrize("leaf_kind", ("symlink", "file"))
def test_agent_data_unsafe_leaf_is_rejected_before_mutation(
    tmp_path: Path, closed_package, leaf_kind: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"agent-data-{leaf_kind}"
    prepared = _prepare_case(case_root, closed_package, fail_after="detach-agent-data")
    release, persistent, evidence, _, before_persistent, _, _ = prepared
    data = release / "agent" / "data"
    if leaf_kind == "symlink":
        external = case_root / "external-data"
        shutil.move(data, external)
        try:
            data.symlink_to(external, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"directory symlinks unavailable: {exc}")
        leaf_before = _snapshot_topology(external)
    else:
        shutil.rmtree(data)
        data.write_bytes(b"not-a-directory\n")
        leaf_before = data.read_bytes()

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "agent-data-symlink-forbidden" in result.stderr
    if leaf_kind == "symlink":
        assert data.is_symlink()
        assert _snapshot_topology(external) == leaf_before
    else:
        assert data.is_file()
        assert data.read_bytes() == leaf_before
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not (evidence / "install-recovery.json").exists()


def test_valid_prejournal_staging_orphan_is_swept_before_new_install(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "staging-orphan-sweep"
    prepared = _prepare_case(case_root, closed_package)
    release, _, _, _, _, _, _ = prepared
    orphan = release.parent / f".{release.name}.closed-stage.777"
    orphan.mkdir()
    (orphan / "partial.txt").write_text("partial\n", encoding="ascii")
    owner = Path(f"{orphan}.owner")
    _write_private_staging_owner(owner, orphan)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 0, result.stderr + result.stdout
    assert not orphan.exists()
    assert not owner.exists()


def test_valid_owner_only_prejournal_orphan_is_swept_before_new_install(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "owner-only-staging-orphan-sweep"
    prepared = _prepare_case(case_root, closed_package)
    release, _, _, _, _, _, _ = prepared
    orphan = release.parent / f".{release.name}.closed-stage.777"
    orphan.mkdir()
    owner = Path(f"{orphan}.owner")
    _write_private_staging_owner(owner, orphan)
    orphan.rmdir()
    unrelated = release.parent / ".unrelated-owner"
    unrelated.write_bytes(b"preserve\n")

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert result.returncode == 19, result.stderr + result.stdout
    assert not owner.exists()
    assert unrelated.read_bytes() == b"preserve\n"


def test_prejournal_staging_sweep_rejects_forged_attempt_id_owner(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "forged-staging-owner"
    prepared = _prepare_case(case_root, closed_package)
    release, _, _, _, _, _, _ = prepared
    forged = release.parent / f".{release.name}.closed-stage.777"
    forged.mkdir()
    foreign = forged / "foreign.txt"
    foreign.write_text("must survive\n", encoding="ascii")
    owner = Path(f"{forged}.owner")
    owner.write_bytes(b"a" * 32 + b"\n")

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert result.returncode == 2, result.stderr + result.stdout
    assert "stale-staging-cleanup-required" in result.stderr
    assert foreign.read_text(encoding="ascii") == "must survive\n"
    assert owner.is_file()


@pytest.mark.parametrize(
    "artifact_kind",
    ("ownerless", "malformed-owner", "symlink-stage", "leading-zero-name"),
)
def test_prejournal_staging_sweep_rejects_unsafe_artifacts(
    tmp_path: Path, artifact_kind: str
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    if "sweep_stale_staging_attempts()" not in source:
        pytest.fail("pre-journal staging sweep is not implemented")
    sweep = source[
        source.index("sweep_stale_staging_attempts()") : source.index(
            "inspect_stale_mount()"
        )
    ]
    release_parent = tmp_path / "release-parent"
    release_parent.mkdir()
    suffix = "007" if artifact_kind == "leading-zero-name" else "777"
    stage = release_parent / f".release.closed-stage.{suffix}"
    owner = Path(f"{stage}.owner")
    if artifact_kind == "symlink-stage":
        target = tmp_path / "outside-stage"
        target.mkdir()
        try:
            stage.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"directory symlinks unavailable: {exc}")
        owner.write_text("a" * 32 + "\n", encoding="ascii")
    else:
        stage.mkdir()
        if artifact_kind == "malformed-owner" or artifact_kind == "leading-zero-name":
            owner.write_text("not-an-attempt-id\n", encoding="ascii")
    log = tmp_path / "sweep.log"
    journal = tmp_path / "install-mutation-state.json"
    script = "\n".join(
        (
            "set +e",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            f"RELEASE_PARENT={shlex.quote(_bash_path(release_parent))}",
            "RELEASE_NAME=release",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"SWEEP_LOG={shlex.quote(_bash_path(log))}",
            "remove_private_directory() { printf 'stage\\n' >> \"$SWEEP_LOG\"; /usr/bin/rm -rf -- \"$1\"; }",
            "remove_file_durably() { printf 'owner\\n' >> \"$SWEEP_LOG\"; /usr/bin/rm -f -- \"$1\"; }",
            sweep,
            "sweep_stale_staging_attempts",
            "printf '%s\\n' \"$?\"",
        )
    )

    result = _run_bash_script(tmp_path / "unsafe-staging-sweep.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "1"
    assert stage.exists() or stage.is_symlink()
    assert not log.exists()


def test_recursive_staging_fsync_uses_read_only_files_and_walks_every_directory():
    source = INSTALL.read_text(encoding="utf-8")
    helper = source[
        source.index("fsync_tree_durably()") : source.index("MUTATION_STARTED=false")
    ]
    assert "flags = os.O_RDONLY" in helper
    assert "flags = os.O_RDWR" not in helper
    assert "with os.scandir(directory) as entries" in helper
    assert "fsync_file(entry.path)" in helper
    assert "walk(child)" in helper
    assert "fsync_directory(directory)" in helper


def test_recursive_staging_fsync_accepts_read_only_regular_files(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    helper = source[
        source.index("fsync_tree_durably()") : source.index("MUTATION_STARTED=false")
    ]
    root = tmp_path / "staging"
    child = root / "child"
    child.mkdir(parents=True)
    read_only = child / "tracked.txt"
    read_only.write_text("tracked\n", encoding="ascii")
    read_only.chmod(0o444)
    script = "\n".join(
        (
            "set -e",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            helper,
            f"fsync_tree_durably {shlex.quote(_bash_path(root))}",
        )
    )

    result = _run_bash_script(tmp_path / "read-only-fsync.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fsync tracing only")
def test_recursive_staging_fsync_traces_every_file_directory_and_root(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    helper = source[
        source.index("fsync_tree_durably()") : source.index("MUTATION_STARTED=false")
    ]
    root = tmp_path / "staging"
    nested = root / "nested" / "empty"
    nested.mkdir(parents=True)
    (root / "sibling.txt").write_bytes(b"sibling\n")
    read_only = nested.parent / "read-only.txt"
    read_only.write_bytes(b"read-only\n")
    read_only.chmod(0o444)
    deep = nested.parent / "deep.txt"
    deep.write_bytes(b"deep\n")
    log = tmp_path / "fsync.log"
    instrument = (
        "import os\n"
        "_real_fsync = os.fsync\n"
        "def _traced_fsync(fd):\n"
        "    with open(os.environ['FSYNC_LOG'], 'a', encoding='utf-8') as stream:\n"
        "        stream.write(os.readlink(f'/proc/self/fd/{fd}') + '\\n')\n"
        "    return _real_fsync(fd)\n"
        "os.fsync = _traced_fsync\n"
    )
    helper = helper.replace("root = Path(sys.argv[1])", instrument + "root = Path(sys.argv[1])")
    script = "\n".join(
        (
            "set -e",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            f"FSYNC_LOG={shlex.quote(_bash_path(log))}",
            "export FSYNC_LOG",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            helper,
            f"fsync_tree_durably {shlex.quote(_bash_path(root))}",
        )
    )

    result = _run_bash_script(tmp_path / "trace-fsync.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    observed = [Path(line) for line in log.read_text(encoding="ascii").splitlines()]
    expected = {
        root / "sibling.txt",
        root / "nested" / "read-only.txt",
        root / "nested" / "deep.txt",
        root,
        root / "nested",
        root / "nested" / "empty",
    }
    assert set(observed) == expected
    assert observed[-1] == root
    assert observed.index(root / "nested" / "empty") < observed.index(root / "nested")
    assert observed.index(root / "nested") < observed.index(root)


def test_owner_writer_fsyncs_file_replaces_atomically_and_fsyncs_parent():
    source = INSTALL.read_text(encoding="utf-8")
    writer = source[
        source.index("write_durable_text_file()") : source.index(
            "inspect_stale_mount()"
        )
    ]
    assert "tempfile.mkstemp" in writer
    assert "stream.flush()" in writer
    assert "os.fsync(stream.fileno())" in writer
    assert "os.replace(temporary, target)" in writer
    assert "os.fsync(directory)" in writer


def test_topology_payload_streams_without_argv_or_environment_handoff():
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index("source_release_topology_sha256()")
    region = source[start : source.index("source_release_topology_subset()", start)]

    assert 'source_release_topology_payload "$root"' in region
    assert '| write_durable_text_file_from_stdin "$target"' in region
    assert 'source_release_topology_payload "$root" | invoke_python -c' in region
    assert "VL360_TOPOLOGY_PAYLOAD" not in region
    assert 'payload="$(source_release_topology_payload' not in region


def test_large_topology_snapshot_and_digest_stream_through_stdin(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    payload_start = source.index("source_release_topology_payload()")
    payload = source[
        payload_start : source.index("source_release_topology_subset()", payload_start)
    ]
    writer_start = source.index("write_durable_text_file_from_stdin()")
    writer = source[
        writer_start : source.index("sweep_stale_staging_attempts()", writer_start)
    ]
    root = tmp_path / "release"
    root.mkdir()
    for index in range(1200):
        (root / f"tracked-entry-{index:04d}-with-a-long-name.txt").write_bytes(b"x\n")
    snapshot = tmp_path / "snapshot.json"
    expected = tmp_path / "expected.json"
    script = "\n".join(
        (
            "set -Eeuo pipefail",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            "export PYTHON_EXECUTOR",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            payload,
            writer,
            f"ROOT={shlex.quote(_bash_path(root))}",
            f"SNAPSHOT={shlex.quote(_bash_path(snapshot))}",
            f"EXPECTED={shlex.quote(_bash_path(expected))}",
            'source_release_topology_snapshot "$ROOT" "$SNAPSHOT"',
            'source_release_topology_payload "$ROOT" > "$EXPECTED"',
            'cmp -s "$EXPECTED" "$SNAPSHOT"',
            'actual="$(source_release_topology_sha256 "$ROOT")"',
            'expected_hash="$(invoke_python -c \'from hashlib import sha256; import sys; from pathlib import Path; print(sha256(Path(sys.argv[1]).read_bytes()).hexdigest())\' "$SNAPSHOT")"',
            '[ "$actual" = "$expected_hash" ]',
        )
    )

    result = _run_bash_script(tmp_path / "large-topology-stream.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert snapshot.stat().st_size > 32 * 1024


def test_topology_digest_suppresses_output_when_stream_producer_fails(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index("source_release_topology_sha256()")
    digest_function = source[
        start : source.index("source_release_topology_snapshot()", start)
    ]
    output = tmp_path / "digest-output"
    status = tmp_path / "digest-status"
    script = "\n".join(
        (
            "set -Euo pipefail",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            "export PYTHON_EXECUTOR",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            "source_release_topology_payload() { printf 'partial-topology'; return 73; }",
            digest_function,
            "set +e",
            'digest="$(source_release_topology_sha256 ignored)"',
            "result=$?",
            "set -e",
            f"printf '%s' \"$digest\" > {shlex.quote(_bash_path(output))}",
            f"printf '%s\\n' \"$result\" > {shlex.quote(_bash_path(status))}",
        )
    )

    result = _run_bash_script(tmp_path / "topology-digest-failure.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert status.read_text(encoding="ascii").strip() == "73"
    assert output.read_bytes() == b""


def test_topology_snapshot_failure_preserves_target_and_cleans_staging(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    snapshot_start = source.index("source_release_topology_snapshot()")
    snapshot_function = source[
        snapshot_start : source.index("source_release_topology_subset()", snapshot_start)
    ]
    writer_start = source.index("write_durable_text_file_from_stdin()")
    writer = source[
        writer_start : source.index("sweep_stale_staging_attempts()", writer_start)
    ]
    target = tmp_path / "topology.json"
    original = b"reviewed-topology\n"
    target.write_bytes(original)
    status = tmp_path / "snapshot-status"
    script = "\n".join(
        (
            "set -Euo pipefail",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            "export PYTHON_EXECUTOR",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            "source_release_topology_payload() { printf 'partial-topology'; return 73; }",
            snapshot_function,
            writer,
            "set +e",
            f"source_release_topology_snapshot ignored {shlex.quote(_bash_path(target))}",
            "result=$?",
            "set -e",
            f"printf '%s\\n' \"$result\" > {shlex.quote(_bash_path(status))}",
        )
    )

    result = _run_bash_script(tmp_path / "topology-snapshot-failure.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert status.read_text(encoding="ascii").strip() == "73"
    assert target.read_bytes() == original
    assert list(tmp_path.glob(f".{target.name}.*.tmp")) == []


def test_authority_result_writer_fsyncs_file_replaces_and_fsyncs_parent():
    source = INSTALL.read_text(encoding="utf-8")
    recorder = source[
        source.index("record_authority_result()") : source.index(
            "record_systemd_unit_cleanup()"
        )
    ]
    assert "tempfile.mkstemp" in recorder
    assert "stream.flush()" in recorder
    assert "os.fsync(stream.fileno())" in recorder
    assert "os.replace(temporary, path)" in recorder
    assert "os.fsync(directory)" in recorder
    assert "temporary.unlink(missing_ok=True)" in recorder


def test_live_mount_authority_harness_is_linux_only_and_uses_posix_paths():
    source = Path(__file__).read_text(encoding="utf-8")
    live_tests = (
        "test_production_shaped_retry_reconciles_stale_journal_without_live_mutation",
        "test_stale_recovery_preserves_authorities_when_findmnt_evidence_is_invalid",
        "test_failed_recovery_umount_preserves_new_and_old_roots_and_persistent_bytes",
        "test_primary_mount_failure_restores_old_root_then_verifies_recovery_mount",
        "test_recovery_rechecks_findmnt_and_bytes_after_post_remount_failure",
        "test_live_mount_authority_is_pinned_before_dependency_hook_replaces_source",
    )
    for name in live_tests:
        start = source.index(f"def {name}(")
        preceding = source[max(0, start - 180) : start]
        assert "@pytest.mark.skipif(" in preceding
        assert 'not sys.platform.startswith("linux")' in preceding
    authority_region = source[
        source.index("def _run_live_mount_failure_case(") : source.index(
            "def test_stale_recovery_refuses_different_retry_authorities("
        )
    ]
    assert "source_path=$(cygpath -m" not in authority_region
    assert "target_path=$(cygpath -m" not in authority_region


def test_recovery_evidence_writer_uses_durable_atomic_json():
    source = INSTALL.read_text(encoding="utf-8")
    writer = source[
        source.index("write_recovery_evidence()") : source.index(
            "materialize_environment_authority()"
        )
    ]
    assert 'write_durable_atomic_json "$EVIDENCE_DIR/install-recovery.json"' in writer
    assert "Path(sys.argv[1]).write_text" not in writer


def test_systemd_cleanup_writer_uses_durable_atomic_json():
    source = INSTALL.read_text(encoding="utf-8")
    writer = source[
        source.index("record_systemd_unit_cleanup()") : source.index(
            "run_authority_hook()"
        )
    ]
    assert 'write_durable_atomic_json "$EVIDENCE_DIR/systemd-unit-cleanup.json"' in writer
    assert "Path(sys.argv[1]).write_text" not in writer


@pytest.mark.parametrize(
    ("cleanup_status", "recorder_status", "expected_status"),
    ((61, 71, 61), (0, 71, 71), (61, 0, 61), (0, 0, 0)),
)
def test_systemd_cleanup_status_precedence(
    tmp_path: Path, cleanup_status: int, recorder_status: int, expected_status: int
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    finalizer = source[
        source.index("finalize_systemd_unit_cleanup()") : source.index(
            "run_authority_hook()"
        )
    ]
    script = "\n".join(
        (
            "set +e",
            f"CLEANUP_STATUS={cleanup_status}",
            f"RECORDER_STATUS={recorder_status}",
            "remove_systemd_unit_attempt() { return \"$CLEANUP_STATUS\"; }",
            "record_systemd_unit_cleanup() { return \"$RECORDER_STATUS\"; }",
            finalizer,
            "finalize_systemd_unit_cleanup",
            "printf '%s\\n' \"$?\"",
        )
    )
    result = _run_bash_script(tmp_path / "systemd-cleanup-precedence.sh", script)
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == str(expected_status)


@pytest.mark.parametrize("fault", ("file-fsync", "replace", "parent-fsync"))
def test_recovery_evidence_durable_writer_faults_propagate(
    tmp_path: Path, fault: str
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    if fault == "parent-fsync" and not sys.platform.startswith("linux"):
        pytest.skip("POSIX directory fsync only")
    source = INSTALL.read_text(encoding="utf-8")
    durable_writer = source[
        source.index("write_durable_atomic_json()") : source.index(
            "write_mutation_state()"
        )
    ]
    recovery_writer = source[
        source.index("write_recovery_evidence()") : source.index(
            "materialize_environment_authority()"
        )
    ]
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    python_path = tmp_path / "python-path"
    python_path.mkdir()
    if fault == "replace":
        injection = (
            "def _failing_replace(source, target):\n"
            "    raise OSError('replace failed')\n"
            "os.replace = _failing_replace\n"
        )
    else:
        directory_test = "stat.S_ISDIR(os.fstat(fd).st_mode)"
        should_fail = directory_test if fault == "parent-fsync" else f"not {directory_test}"
        injection = (
            "_real_fsync = os.fsync\n"
            "def _failing_fsync(fd):\n"
            f"    if {should_fail}:\n"
            f"        raise OSError('{fault} failed')\n"
            "    return _real_fsync(fd)\n"
            "os.fsync = _failing_fsync\n"
        )
    (python_path / "sitecustomize.py").write_text(
        "import os\nimport stat\n" + injection,
        encoding="ascii",
    )
    script = "\n".join(
        (
            "set +e",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            f"PYTHONPATH={shlex.quote(_bash_path(python_path))}",
            "export PYTHONPATH",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            "INSTALL_FAILURE_POINT=swap-release-root",
            durable_writer,
            recovery_writer,
            "write_recovery_evidence rolled-back true true true",
            "printf '%s\\n' \"$?\"",
        )
    )

    result = _run_bash_script(tmp_path / f"recovery-evidence-{fault}.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() != "0"


def test_recovery_evidence_is_durable_before_rollback_journal_clear():
    source = INSTALL.read_text(encoding="utf-8")
    recovery = source[
        source.index("install_recovery()") : source.index(
            "trap install_recovery EXIT"
        )
    ]
    journal = recovery.index("write_mutation_state rollback-restored")
    evidence = recovery.index("write_recovery_evidence rolled-back true true true")
    clear = recovery.index("clear_mutation_state", journal)
    assert journal < evidence < clear
    assert "write_recovery_evidence rolled-back true true true || true" not in recovery


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fsync failure only")
def test_authority_result_parent_fsync_failure_propagates(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    recorder = source[
        source.index("record_authority_result()") : source.index(
            "record_systemd_unit_cleanup()"
        )
    ]
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    python_path = tmp_path / "python-path"
    python_path.mkdir()
    (python_path / "sitecustomize.py").write_text(
        "import os\n"
        "import stat\n"
        "_real_fsync = os.fsync\n"
        "def _failing_directory_fsync(fd):\n"
        "    if stat.S_ISDIR(os.fstat(fd).st_mode):\n"
        "        raise OSError('parent fsync failed')\n"
        "    return _real_fsync(fd)\n"
        "os.fsync = _failing_directory_fsync\n",
        encoding="ascii",
    )
    script = "\n".join(
        (
            "set +e",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            f"PYTHONPATH={shlex.quote(_bash_path(python_path))}",
            "export PYTHONPATH",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            recorder,
            "record_authority_result python-dependencies passed 0",
            "printf '%s\\n' \"$?\"",
        )
    )

    result = _run_bash_script(tmp_path / "record-parent-fsync-failure.sh", script)

    assert result.returncode == 0
    assert result.stdout.strip() != "0"
    payload = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert payload["results"] == {"python-dependencies": "passed"}
    assert payload["exit_codes"] == {"python-dependencies": 0}


def test_staged_tree_is_fsynced_after_hooks_before_activation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "staged-fsync-order"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, _ = prepared
    order_log = case_root / "order.log"
    runtime = case_root / "runtime"
    (runtime / "python-hook.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "release_root=\n"
        "while (($# > 0)); do\n"
        "  case \"$1\" in\n"
        "    --release-root) release_root=$2; shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "[ -n \"$release_root\" ]\n"
        "touch -- \"$release_root/requirements.txt\"\n"
        f"printf 'python-hook-mutation\\n' >> '{_bash_path(order_log)}'\n",
        encoding="ascii",
    )
    (runtime / "nuxt-hook.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "project_root=\n"
        "while (($# > 0)); do\n"
        "  case \"$1\" in\n"
        "    --project-root) project_root=$2; shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "[ -n \"$project_root\" ]\n"
        "touch -- \"$project_root/package.json\"\n"
        f"printf 'nuxt-hook-mutation\\n' >> '{_bash_path(order_log)}'\n",
        encoding="ascii",
    )
    for hook_name in ("python-hook.sh", "nuxt-hook.sh"):
        (runtime / hook_name).chmod(0o755)
    python_executor = _write_local_python_executor(
        case_root / "staged-fsync-python",
        "if [ \"${1:-}\" = - ] && { "
        "{ [[ \"${2:-}\" == *.closed-stage.* ]] "
        "&& [ -f \"${2:-}/launch-release-manifest.json\" ]; } "
        "|| { [[ \"${2:-}\" == *.closed-stage.*/launch-release-manifest.json ]] "
        "&& [ -f \"${2:-}\" ]; }; }; then\n"
        "  inline_script=\"$(mktemp)\"\n"
        "  cat > \"$inline_script\"\n"
        "  if [[ \"${2:-}\" == */launch-release-manifest.json ]]; then\n"
        "    event=manifest-digest\n"
        "  elif grep -Fq 'def walk(directory):' \"$inline_script\"; then\n"
        "    event=recursive-staging-fsync\n"
        "  elif grep -Fq 'for raw in sys.argv[1:]:' \"$inline_script\"; then\n"
        "    event=environment-materialized\n"
        "  elif grep -Fq 'def visit(path, relative):' \"$inline_script\"; then\n"
        "    event=candidate-topology-read\n"
        "  elif grep -Fq 'observed.st_dev' \"$inline_script\"; then\n"
        "    event=candidate-root-identity-read\n"
        "  else\n"
        "    event=unexpected-staging-python\n"
        "  fi\n"
        f"  printf '%s\\n' \"$event\" >> '{_bash_path(order_log)}'\n"
        '  "$REAL_PYTHON" "$inline_script" "${@:2}"\n'
        "  status=$?\n"
        "  rm -f -- \"$inline_script\"\n"
        "  exit \"$status\"\n"
        "fi\n"
        'exec "$REAL_PYTHON" "$@"\n',
    )
    bash_env = case_root / "staged-fsync-order.bash"
    bash_env.write_text(
        "mv() {\n"
        "  local source destination\n"
        "  if [ \"${1:-}\" = -- ]; then\n"
        "    source=${2:-}\n"
        "    destination=${3:-}\n"
        "  else\n"
        "    source=${1:-}\n"
        "    destination=${2:-}\n"
        "  fi\n"
        f"  if [ \"$source\" = '{_bash_path(release / 'agent' / 'data')}' ] "
        f"&& [ \"$destination\" = '{_bash_path(persistent)}' ]; then\n"
        f"    printf 'rename-persistent-detach\\n' >> '{_bash_path(order_log)}'\n"
        f"  elif [ \"$source\" = '{_bash_path(release)}' ] "
        "&& [[ \"$destination\" == *.closed-old.* ]]; then\n"
        f"    printf 'rename-live-release\\n' >> '{_bash_path(order_log)}'\n"
        "  elif [[ \"$source\" == *.closed-stage.* ]] "
        f"&& [ \"$destination\" = '{_bash_path(release)}' ]; then\n"
        f"    printf 'activate-staging\\n' >> '{_bash_path(order_log)}'\n"
        "  fi\n"
        '  /usr/bin/mv "$@"\n'
        "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor),
        },
    )

    assert result.returncode == 0, result.stderr + result.stdout
    events = order_log.read_text(encoding="ascii").splitlines()
    assert "unexpected-staging-python" not in events
    manifest_digests = [
        index for index, event in enumerate(events) if event == "manifest-digest"
    ]
    assert len(manifest_digests) == 2
    recursive_fsyncs = [
        index
        for index, event in enumerate(events)
        if event == "recursive-staging-fsync"
    ]
    first_live_rename = min(
        events.index(event)
        for event in (
            "rename-persistent-detach",
            "rename-live-release",
            "activate-staging",
        )
    )
    required_fsync = max(index for index in recursive_fsyncs if index < first_live_rename)
    for mutation in (
        "python-hook-mutation",
        "nuxt-hook-mutation",
    ):
        mutation_index = events.index(mutation)
        assert manifest_digests[0] < mutation_index < manifest_digests[1]
        assert mutation_index < required_fsync < first_live_rename
    assert manifest_digests[1] < events.index("environment-materialized")
    assert events.index("environment-materialized") < required_fsync
    assert events.index("candidate-topology-read") < required_fsync
    assert events.index("candidate-root-identity-read") < required_fsync
    assert required_fsync < events.index("activate-staging")


def test_staged_tree_fsync_failure_stops_before_live_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "staged-fsync-failure"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    failed = case_root / "staged-fsync-failed"
    python_executor = _write_local_python_executor(
        case_root / "staged-fsync-failure-python",
        "if [ \"${1:-}\" = - ] && [[ \"${2:-}\" == *.closed-stage.* ]] "
        "&& [ -f \"${2:-}/launch-release-manifest.json\" ]; then\n"
        '  "$REAL_PYTHON" "$@"\n'
        f"  : > '{_bash_path(failed)}'\n"
        "  exit 71\n"
        "fi\n"
        'exec "$REAL_PYTHON" "$@"\n',
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)},
    )

    assert result.returncode == 71, result.stderr + result.stdout
    assert failed.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not (evidence / "install-recovery.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


@pytest.mark.parametrize(
    ("failure_target", "expected_status"),
    (("owner", 71), ("snapshot", 72)),
)
def test_recovery_input_fsync_failure_prevents_first_journal(
    tmp_path: Path,
    closed_package,
    failure_target: str,
    expected_status: int,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"recovery-input-{failure_target}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    failed = case_root / f"{failure_target}-fsync-failed"
    if failure_target == "owner":
        condition = '[[ "${2:-}" == *.closed-stage.*.owner ]]'
        status = 71
    else:
        condition = f'[ "${{3:-}}" = \'{_bash_path(evidence / "persistent-before.json")}\' ]'
        status = 72
    python_executor = _write_local_python_executor(
        case_root / f"{failure_target}-fsync-python",
        f"if [ \"${{1:-}}\" = - ] && [ ! -f '{_bash_path(failed)}' ] "
        f"&& {condition}; then\n"
        '  "$REAL_PYTHON" "$@"\n'
        f"  : > '{_bash_path(failed)}'\n"
        f"  exit {status}\n"
        "fi\n"
        'exec "$REAL_PYTHON" "$@"\n',
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)},
    )

    assert result.returncode == expected_status, result.stderr + result.stdout
    assert failed.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not (evidence / "install-recovery.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


def test_staging_owner_and_persistent_snapshot_are_durable_before_first_journal():
    source = INSTALL.read_text(encoding="utf-8")
    snapshot = source[
        source.index("snapshot_tree()") : source.index("MUTATION_STARTED=false")
    ]
    assert "tempfile.mkstemp" in snapshot
    assert "stream.flush()" in snapshot
    assert "os.fsync(stream.fileno())" in snapshot
    assert "os.replace(temporary, target)" in snapshot
    assert "fsync_directory(target.parent)" in snapshot
    owner_write = source.index(
        'write_private_staging_owner_marker "$STAGING_OWNER_MARKER"'
    )
    snapshot_write = source.index('snapshot_tree "$CURRENT_DATA" "$SNAPSHOT_BEFORE"')
    first_journal = source.index("write_mutation_state detach-agent-data-armed")
    assert owner_write < snapshot_write < first_journal


def test_dependency_hook_tracked_byte_tamper_is_rejected_before_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "hook-tracked-byte-tamper"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, hook_log, _ = prepared
    marker = case_root / "tracked-byte-tampered"
    nuxt_hook = case_root / "runtime" / "nuxt-hook.sh"
    nuxt_hook.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "project_root=\n"
        "while (($# > 0)); do\n"
        "  case \"$1\" in\n"
        "    --project-root) project_root=$2; shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "[ -n \"$project_root\" ]\n"
        "stage_root=$(dirname -- \"$project_root\")\n"
        "printf '%s|%s\\n' 'nuxt-production-dependencies' "
        "'--project-root '\"$project_root\"' --production-only' >> \"$INSTALL_HOOK_LOG\"\n"
        "printf 'tampered\\n' >> \"$stage_root/nginx.conf\"\n"
        f": > '{_bash_path(marker)}'\n",
        encoding="ascii",
    )
    nuxt_hook.chmod(0o755)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert marker.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not (evidence / "install-recovery.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))
    assert [
        line.split("|", 1)[0]
        for line in hook_log.read_text(encoding="ascii").splitlines()
    ] == ["python-dependencies", "nuxt-production-dependencies"]


def test_dependency_hook_self_consistent_manifest_tamper_is_rejected_before_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "hook-self-consistent-manifest-tamper"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    marker = case_root / "manifest-tampered"
    nuxt_hook = case_root / "runtime" / "nuxt-hook.sh"
    nuxt_hook.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "project_root=\n"
        "while (($# > 0)); do\n"
        "  case \"$1\" in\n"
        "    --project-root) project_root=$2; shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "stage_root=$(dirname -- \"$project_root\")\n"
        f"'{_bash_path(Path(sys.executable).resolve())}' - \"$stage_root\" <<'PY'\n"
        "from hashlib import sha256\n"
        "import json\n"
        "from pathlib import Path\n"
        "import sys\n"
        "root = Path(sys.argv[1])\n"
        "target = root / 'web-nuxt' / 'package.json'\n"
        "raw = b'{\\\"self_consistent_tamper\\\":true}\\n'\n"
        "target.write_bytes(raw)\n"
        "manifest_path = root / 'launch-release-manifest.json'\n"
        "manifest = json.loads(manifest_path.read_text(encoding='utf-8'))\n"
        "manifest['members']['web-nuxt/package.json'] = {\n"
        "    'sha256': sha256(raw).hexdigest(), 'size': len(raw)\n"
        "}\n"
        "manifest_path.write_text(\n"
        "    json.dumps(manifest, indent=2, sort_keys=True) + '\\n', encoding='utf-8'\n"
        ")\n"
        "PY\n"
        f": > '{_bash_path(marker)}'\n",
        encoding="ascii",
    )
    nuxt_hook.chmod(0o755)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert marker.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not (evidence / "install-mutation-state.json").exists()
    assert not list(release.parent.glob(f".{release.name}.closed-*"))


@pytest.mark.parametrize(
    ("hook_status", "recorder_status", "expected_status"),
    ((19, 63, 19), (0, 63, 63)),
    ids=("hook-failure-wins", "recorder-failure-surfaces"),
)
def test_authority_hook_status_precedence(
    tmp_path: Path,
    hook_status: int,
    recorder_status: int,
    expected_status: int,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    hook_function = source[
        source.index("run_authority_hook()") : source.index(
            "run_authority_hook python-dependencies"
        )
    ]
    log = tmp_path / "recorder.log"
    script = "\n".join(
        (
            "set +e",
            "PYTHON_DEPENDENCY_HOOK_SHA256=digest",
            "NUXT_DEPENDENCY_HOOK_SHA256=digest",
            "UNIT_VERIFY_HOOK_SHA256=digest",
            f"HOOK_STATUS={hook_status}",
            f"RECORDER_STATUS={recorder_status}",
            f"RECORDER_LOG={shlex.quote(_bash_path(log))}",
            "invoke_pinned_executable() { return \"$HOOK_STATUS\"; }",
            "record_authority_result() { printf '%s|%s|%s\\n' \"$1\" \"$2\" \"$3\" >> \"$RECORDER_LOG\"; return \"$RECORDER_STATUS\"; }",
            hook_function,
            "run_authority_hook python-dependencies /hook --release-root /stage",
            "status=$?",
            "printf '%s\\n' \"$status\"",
        )
    )

    result = _run_bash_script(tmp_path / "hook-precedence.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == str(expected_status)
    assert log.read_text(encoding="ascii").strip() == (
        "python-dependencies|passed|0"
        if hook_status == 0
        else f"python-dependencies|failed|{hook_status}"
    )
    if hook_status != 0 and recorder_status != 0:
        assert (
            f"authority-result-record-failed:python-dependencies:{recorder_status}"
            in result.stderr
        )


def test_final_verifier_rolls_back_unit_hook_destination_byte_corruption(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "unit-hook-corrupts-destination"
    prepared = _prepare_case(case_root, closed_package)
    (
        release,
        persistent,
        evidence,
        before_release,
        before_persistent,
        _,
        _,
    ) = prepared
    unit_destination = case_root / "runtime" / "systemd-units"
    unit_destination.mkdir()
    for name in SYSTEMD_UNIT_NAMES:
        (unit_destination / name).write_bytes(f"legacy-{name}\n".encode("ascii"))
    units_before = _snapshot_tree(unit_destination)
    hook_marker = case_root / "unit-hook-corruption-used"
    unit_hook = case_root / "runtime" / "units-hook.sh"
    unit_hook.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "unit_root=\n"
        "while (($# > 0)); do\n"
        "  case \"$1\" in\n"
        "    --unit-root) unit_root=$2; shift 2 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "[ -n \"$unit_root\" ]\n"
        "printf '%s|%s\\n' 'systemd-units' \"$unit_root\" >> \"$INSTALL_HOOK_LOG\"\n"
        "printf 'corrupt\\n' > \"$unit_root/vl-agent.service\"\n"
        f": > '{_bash_path(hook_marker)}'\n"
        "exit 0\n",
        encoding="ascii",
    )
    unit_hook.chmod(0o755)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "closed release verification refused" in result.stderr
    assert hook_marker.is_file()
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert checks["results"] == {
        "python-dependencies": "passed",
        "nuxt-production-dependencies": "passed",
        "systemd-units": "passed",
    }
    assert checks["exit_codes"] == {
        "python-dependencies": 0,
        "nuxt-production-dependencies": 0,
        "systemd-units": 0,
    }
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert _snapshot_tree(unit_destination) == units_before
    assert not (evidence / "installed").exists()
    assert not (evidence / "install-mutation-state.json").exists()
    assert _unit_attempt_artifacts(evidence) == []
    assert not list(release.parent.glob(f".{release.name}.closed-*"))
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rolled-back"
    assert recovery["root_restored"] is True
    assert recovery["persistent_restored"] is True
    assert recovery["systemd_units_restored"] is True


@pytest.mark.parametrize("invalid_kind", ("symlink-component", "nonregular"))
def test_executable_authority_rejects_symlink_components_and_nonregular_sources(
    tmp_path: Path, closed_package, invalid_kind: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"invalid-executable-{invalid_kind}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, hook_log, values = prepared
    runtime = case_root / "runtime"
    if invalid_kind == "symlink-component":
        alias = case_root / "runtime-alias"
        try:
            alias.symlink_to(runtime, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"directory symlinks are unavailable: {error}")
        invalid = alias / "python-hook.sh"
    else:
        invalid = runtime / "nonregular-hook"
        invalid.mkdir()
    before_release = _snapshot_tree(release)
    before_persistent = _snapshot_tree(persistent)
    values["VL360_PYTHON_DEPENDENCY_HOOK"] = _bash_path_literal(invalid)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2
    assert "executable-authority-required" in result.stderr
    assert not hook_log.exists()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent


@pytest.mark.parametrize(
    "namespace",
    ("release", "persistent", "evidence", "systemd", "stage", "old", "retired"),
)
def test_executable_authority_rejects_protected_and_reserved_namespace_overlap(
    tmp_path: Path, closed_package, namespace: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"executable-overlap-{namespace}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, hook_log, values = prepared
    roots = {
        "release": release,
        "persistent": persistent,
        "evidence": evidence,
        "systemd": case_root / "runtime" / "systemd-units",
        "stage": release.parent / f".{release.name}.closed-stage.attacker",
        "old": release.parent / f".{release.name}.closed-old.attacker",
        "retired": release.parent / f".{release.name}.closed-retired.attacker",
    }
    authority = roots[namespace] / "authority.sh"
    authority.parent.mkdir(parents=True, exist_ok=True)
    authority.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="ascii")
    authority.chmod(0o755)
    before_release = _snapshot_tree(release)
    before_persistent = _snapshot_tree(persistent)
    values["VL360_PYTHON_DEPENDENCY_HOOK"] = _bash_path(authority)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2
    assert "executable-authority-namespace-overlap" in result.stderr
    assert not hook_log.exists()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent


def test_dependency_and_unit_sources_are_pinned_before_replacement(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "executable-source-replacement"
    prepared = _prepare_case(case_root, closed_package)
    _, _, _, _, _, hook_log, _ = prepared
    runtime = case_root / "runtime"
    python_hook = runtime / "python-hook.sh"
    nuxt_hook = runtime / "nuxt-hook.sh"
    unit_hook = runtime / "units-hook.sh"
    python_hook.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s|%s\\n' 'python-dependencies' \"$*\" >> \"$INSTALL_HOOK_LOG\"\n"
        f"printf '%s\\n' '#!/usr/bin/env bash' 'printf \"tampered-nuxt|%s\\\\n\" \"$*\" >> \"$INSTALL_HOOK_LOG\"' > '{_bash_path(nuxt_hook)}'\n"
        f"printf '%s\\n' '#!/usr/bin/env bash' 'printf \"tampered-units|%s\\\\n\" \"$*\" >> \"$INSTALL_HOOK_LOG\"' > '{_bash_path(unit_hook)}'\n"
        f"chmod 0755 '{_bash_path(nuxt_hook)}' '{_bash_path(unit_hook)}'\n",
        encoding="ascii",
    )
    python_hook.chmod(0o755)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 0, result.stderr + result.stdout
    assert [line.split("|", 1)[0] for line in hook_log.read_text().splitlines()] == [
        "python-dependencies",
        "nuxt-production-dependencies",
        "systemd-units",
    ]


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux live mount harness only"
)
def test_live_mount_authority_is_pinned_before_dependency_hook_replaces_source(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    result, _, _ = _run_live_mount_failure_case(
        closed_package,
        tmp_path / "mount-source-replacement",
        replace_mount_source_after_admission=True,
    )

    assert result.returncode == 44, result.stderr + result.stdout


def test_pinned_executable_tamper_fails_closed_before_next_hook_invocation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "executable-pin-tamper"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, hook_log, _ = prepared
    python_hook = case_root / "runtime" / "python-hook.sh"
    python_hook.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s|%s\\n' 'python-dependencies' \"$*\" >> \"$INSTALL_HOOK_LOG\"\n"
        "target=$(dirname -- \"$0\")/nuxt-dependency\n"
        "chmod 0700 -- \"$target\"\n"
        "printf '#!/usr/bin/env bash\\nexit 0\\n# executable-pin-tampered\\n' > \"$target\"\n",
        encoding="ascii",
    )
    python_hook.chmod(0o755)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 126, result.stderr + result.stdout
    assert "executable-authority-digest-mismatch" in result.stderr
    assert hook_log.read_text(encoding="ascii").splitlines()[0].startswith(
        "python-dependencies|"
    )
    assert "nuxt-production-dependencies" not in hook_log.read_text(encoding="ascii")
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    for path in evidence.rglob("*"):
        if path.is_file():
            assert b"executable-pin-tampered" not in path.read_bytes()


def test_linux_pinned_executor_copies_and_hashes_open_descriptor_before_fd_exec():
    source = INSTALL.read_text(encoding="utf-8")
    helper = _pinned_executor_python(source)

    assert 'ROLE_FILENAMES = {' in helper
    for role in ("mount", "python-dependency", "nuxt-dependency", "unit-verify"):
        assert f'"{role}": "{role}"' in helper
    assert "os.O_NOFOLLOW" in helper
    assert "dir_fd=pin_root_fd" in helper
    assert "chunk = os.read(pin_fd" in helper
    assert helper.index("digest.update(chunk)") < helper.index(
        "write_all(memfd_fd, chunk)"
    )
    assert helper.index("digest.hexdigest() != expected_sha256") < helper.index(
        "    seal_memfd(memfd_fd)"
    )
    assert "os.execve(memfd_fd, argv, env)" in helper
    assert "os.execve(pin_path" not in helper


def test_linux_pinned_executor_requires_memfd_sealing_fd_exec_and_safe_shebang():
    source = INSTALL.read_text(encoding="utf-8")
    helper = _pinned_executor_python(source)

    assert 'sys.platform.startswith("linux")' in helper
    assert 'hasattr(os, "memfd_create")' in helper
    assert "os.execve not in os.supports_fd" in helper
    for seal in ("F_SEAL_WRITE", "F_SEAL_GROW", "F_SEAL_SHRINK", "F_SEAL_SEAL"):
        assert seal in helper
    assert "os.set_inheritable(memfd_fd, True)" in helper
    assert 'b"#!/usr/bin/env bash"' in helper
    assert "executable-authority-shebang-forbidden" in helper
    assert "executable-authority-fd-exec-unavailable" in helper


def test_installer_ignores_python_function_shadowed_from_bash_env(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "python-function-shadow"
    prepared = _prepare_case(case_root, closed_package)
    marker = case_root / "shadowed-python-called"
    bash_env = case_root / "python-shadow.bash"
    bash_env.write_text(
        "python() {\n"
        f"  : > '{_bash_path(marker)}'\n"
        "  return 73\n"
        "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert not marker.exists()


def test_installer_ignores_command_and_exec_functions_shadowed_from_bash_env(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "command-exec-function-shadow"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, hook_log, _ = prepared
    command_marker = case_root / "shadowed-command-called"
    exec_marker = case_root / "shadowed-exec-called"
    bash_env = case_root / "command-exec-shadow.bash"
    bash_env.write_text(
        "command() {\n"
        "  if [ \"${1:-}\" = -v ]; then\n"
        "    builtin command \"$@\"\n"
        "    return $?\n"
        "  fi\n"
        f"  : > '{_bash_path(command_marker)}'\n"
        "  return 0\n"
        "}\n"
        "exec() {\n"
        "  if [ \"${1:-}\" != -a ]; then\n"
        "    builtin exec \"$@\"\n"
        "    return $?\n"
        "  fi\n"
        f"  : > '{_bash_path(exec_marker)}'\n"
        "  return 0\n"
        "}\n",
        encoding="ascii",
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert [
        line.split("|", 1)[0]
        for line in hook_log.read_text(encoding="ascii").splitlines()
    ] == [
        "python-dependencies",
        "nuxt-production-dependencies",
        "systemd-units",
    ]
    checks = json.loads(
        (evidence / "dependency-unit-checks.json").read_text(encoding="utf-8")
    )
    assert set(checks["results"].values()) == {"passed"}
    assert (release / "launch-release-manifest.json").is_file()
    assert not command_marker.exists()
    assert not exec_marker.exists()


def test_canonical_authority_path_normalizes_msys_python_output_in_live_mode(
    tmp_path: Path,
):
    if os.name != "nt" or not BASH.is_file():
        pytest.skip("MSYS path normalization only")
    source = INSTALL.read_text(encoding="utf-8")
    helper = source[
        source.index("canonical_authority_path()") : source.index(
            "validate_executable_authority_sources()"
        )
    ]
    assert "command -v cygpath" not in helper
    assert "if [ -x /usr/bin/cygpath ]; then" in helper
    assert '/usr/bin/cygpath -u "$canonical"' in helper
    script = "\n".join(
        (
            "set -eu",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            helper,
            'canonical_authority_path "$1" false',
        )
    )
    authority = tmp_path / "live-authority"
    authority.mkdir()

    result = subprocess.run(
        [str(BASH), "-c", script, "canonical-authority-test", _bash_path(authority)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == _bash_path(authority.resolve())


def test_conflicting_python_executor_authorities_are_rejected_before_execution(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "conflicting-python-executors"
    prepared = _prepare_case(case_root, closed_package)
    *_, values = prepared
    general_marker = case_root / "general-executor-ran"
    local_marker = case_root / "local-executor-ran"
    general_executor = _write_local_python_executor(
        case_root / "general-python",
        f": > '{_bash_path(general_marker)}'\n"
        'command "$REAL_PYTHON" "$@"\n',
    )
    local_executor = _write_local_python_executor(
        case_root / "local-python",
        f": > '{_bash_path(local_marker)}'\n"
        'command "$REAL_PYTHON" "$@"\n',
    )
    env = os.environ.copy()
    env.update(values)
    env["VL360_PYTHON_EXECUTOR"] = _bash_path(general_executor)
    env["VL360_LOCAL_PYTHON_EXECUTOR"] = _bash_path(local_executor)

    result = subprocess.run(
        _installer_command(closed_package, case_root, prepared),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "python-executor-authority-conflict" in result.stderr
    assert not general_marker.exists()
    assert not local_marker.exists()


@pytest.mark.parametrize(
    "malformed_args",
    (
        ["--archive", "--local-rehearsal"],
        ["--local-rehearsal", "--unknown-option"],
        ["--local-rehearsal"],
    ),
)
def test_malformed_value_cannot_enable_local_python_executor(
    tmp_path: Path, closed_package, malformed_args: list[str]
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "malformed-local-executor"
    prepared = _prepare_case(case_root, closed_package)
    *_, values = prepared
    marker = case_root / "local-executor-ran"
    python_executor = _write_local_python_executor(
        case_root / "malformed-local-python",
        f": > '{_bash_path(marker)}'\n"
        'command "$REAL_PYTHON" "$@"\n',
    )
    env = os.environ.copy()
    env.update(values)
    env.pop("VL360_PYTHON_EXECUTOR", None)
    env["VL360_LOCAL_PYTHON_EXECUTOR"] = _bash_path(python_executor)

    result = subprocess.run(
        [str(BASH), "scripts/ops/install_closed_release.sh", *malformed_args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert not marker.exists()


def test_local_rm_executor_is_forbidden_outside_local_rehearsal(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "live-local-rm-executor"
    prepared = _prepare_case(case_root, closed_package)
    *_, values = prepared
    rm_executor = case_root / "local-rm"
    rm_executor.write_text(
        "#!/usr/bin/env bash\nexec /usr/bin/rm \"$@\"\n", encoding="ascii"
    )
    rm_executor.chmod(0o755)
    env = os.environ.copy()
    env.update(values)
    for name in (
        "VL360_PYTHON_DEPENDENCY_HOOK",
        "VL360_NUXT_DEPENDENCY_HOOK",
        "VL360_UNIT_VERIFY_HOOK",
    ):
        env.pop(name, None)
    env["VL360_LOCAL_RM_EXECUTOR"] = _bash_path(rm_executor.resolve())
    command = _installer_command(closed_package, case_root, prepared)
    command.remove("--local-rehearsal")

    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "local-rm-executor-live-forbidden" in result.stderr


def test_local_rm_executor_requires_a_canonical_regular_executable(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "symlink-local-rm-executor"
    prepared = _prepare_case(case_root, closed_package)
    target = case_root / "local-rm-target"
    target.write_text(
        "#!/usr/bin/env bash\nexec /usr/bin/rm \"$@\"\n", encoding="ascii"
    )
    target.chmod(0o755)
    symlink = case_root / "local-rm-link"
    try:
        symlink.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_RM_EXECUTOR": _bash_path_literal(symlink)},
    )

    assert result.returncode == 2
    assert "rm-executor-authority-required" in result.stderr


def test_quarantine_deletes_use_the_admitted_rm_authority():
    source = INSTALL.read_text(encoding="utf-8")
    assert "RM_EXECUTOR_CANDIDATE=/usr/bin/rm" in source
    assert 'RM_EXECUTOR="$(canonical_executable_path "$RM_EXECUTOR_CANDIDATE")"' in source
    for cleanup_root in (
        "candidate_cleanup_root",
        "staging_delete_root",
        "retired_cleanup_root",
        "CANDIDATE_CLEANUP_ROOT",
        "STAGING_DELETE_ROOT",
        "RETIRED_CLEANUP_ROOT",
    ):
        assert f'invoke_rm -rf -- "${cleanup_root}"' in source


def test_linux_python_executor_is_bound_to_admitted_descriptor_before_mutation():
    source = INSTALL.read_text(encoding="utf-8")

    open_fd = 'exec {PYTHON_EXECUTOR_FD}<"$PYTHON_EXECUTOR_AUTHORITY"'
    pinned_path = 'PYTHON_EXECUTOR="/proc/$BASHPID/fd/$PYTHON_EXECUTOR_FD"'
    assert open_fd in source
    assert pinned_path in source
    assert source.index(open_fd) < source.index("ATTEMPT_ID=")
    assert source.index(pinned_path) < source.index("ATTEMPT_ID=")
    operational = source[source.index("fsync_directories()") :]
    assert 'command "$PYTHON_EXECUTOR"' not in operational


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd pin only")
def test_linux_installer_keeps_admitted_python_when_authority_path_is_replaced(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    case_root = tmp_path / "python-authority-replacement"
    prepared = _prepare_case(case_root, closed_package)
    python_executor = _write_local_python_executor(
        case_root / "admitted-python",
        'command "$REAL_PYTHON" "$@"\n',
    )
    marker = case_root / "replacement-python-ran"
    hook = case_root / "runtime" / "python-hook.sh"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' '#!/usr/bin/env bash' "
        f"': > {_bash_path(marker)}' 'exit 97' > \"$PYTHON_EXECUTOR_SOURCE\"\n"
        "chmod 0755 -- \"$PYTHON_EXECUTOR_SOURCE\"\n",
        encoding="ascii",
    )
    hook.chmod(0o755)

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "PYTHON_EXECUTOR_SOURCE": _bash_path(python_executor),
            "VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor),
        },
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert not marker.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd pin only")
def test_linux_python_descriptor_preserves_runtime_imports_and_prefix():
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    bootstrap = source.split("\nfsync_directories()", 1)[0]
    probe = bootstrap + """
command "$PYTHON_EXECUTOR" -c '
import json
import ssl
import dotenv
import sys
print(json.dumps({"base_prefix": sys.base_prefix, "prefix": sys.prefix}))
'
"""

    result = subprocess.run(
        [str(BASH), "-c", probe, "vl360-python-bootstrap", "--local-rehearsal"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout.splitlines()[-1])
    assert payload["prefix"]
    assert payload["base_prefix"]


def test_explicit_python_executor_preserves_isolated_venv_runtime(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    venv_root = tmp_path / "isolated-venv"
    venv.EnvBuilder(with_pip=False).create(venv_root)
    venv_python = venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    purelib = Path(
        subprocess.check_output(
            [str(venv_python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
            text=True,
        ).strip()
    )
    dotenv = purelib / "dotenv"
    dotenv.mkdir()
    (dotenv / "__init__.py").write_text("", encoding="ascii")
    (dotenv / "parser.py").write_text("def parse_stream(stream): return ()\n", encoding="ascii")
    source = INSTALL.read_text(encoding="utf-8")
    bootstrap = source.split("\nfsync_directories()", 1)[0]
    probe = bootstrap + """
command "$PYTHON_EXECUTOR" -c '
import json
import dotenv.parser
import ssl
import sys
print(json.dumps({"prefix": sys.prefix}))
'
"""
    env = os.environ.copy()
    env["VL360_PYTHON_EXECUTOR"] = _bash_path(venv_python.resolve())
    required_args = [
        "--archive",
        "archive",
        "--archive-digest-file",
        "archive.sha256",
        "--release-root",
        "release",
        "--persistent-agent-data-root",
        "persistent",
        "--environment-authority",
        "external.env",
        "--runtime-authority",
        "runtime",
        "--evidence-dir",
        "evidence",
        "--require-closed",
        "--local-rehearsal",
    ]
    # Run the long bootstrap through a file so Git Bash does not corrupt
    # backslash-newline continuations while parsing a large `-c` argument.
    probe_path = tmp_path / "python-bootstrap-probe.sh"
    probe_path.write_text(probe, encoding="ascii")

    result = subprocess.run(
        [str(BASH), _bash_path(probe_path), *required_args],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout.splitlines()[-1])
    assert Path(payload["prefix"]).resolve() == venv_root.resolve()


def test_linux_pinned_executor_routes_env_bash_through_admitted_descriptors():
    source = INSTALL.read_text(encoding="utf-8")
    helper = _pinned_executor_python(source)

    assert 'ENV_BASH_SHEBANG = b"#!/usr/bin/env bash"' in helper
    assert 'shebang.startswith(b"#!/usr/bin/env")' not in helper
    assert "bash_fd = open_canonical_executor" in helper
    assert 'f"/proc/self/fd/{memfd_fd}"' in helper
    assert "os.execve(bash_fd, argv, env)" in helper


def test_windows_local_pinned_executor_preserves_process_contract(tmp_path: Path):
    if os.name != "nt" or not BASH.is_file():
        pytest.skip("Windows Git Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    hook = pin_root / "python-dependency"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "IFS= read -r payload\n"
        "printf 'arg=%s\\nenv=%s\\nstdin=%s\\n' \"$1\" \"$PIN_TEST_ENV\" \"$payload\"\n"
        "printf 'stderr=%s\\n' \"$2\" >&2\n"
        "exit 37\n",
        encoding="ascii",
    )
    hook.chmod(0o500)
    digest = hashlib.sha256(hook.read_bytes()).hexdigest()

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        digest,
        ["first argument", "second argument"],
        local_rehearsal=True,
        env_overrides={"PIN_TEST_ENV": "preserved-env"},
        stdin="preserved-stdin\n",
    )

    assert result.returncode == 37, result.stderr + result.stdout
    assert result.stdout.splitlines() == [
        "arg=first argument",
        "env=preserved-env",
        "stdin=preserved-stdin",
    ]
    assert result.stderr == "stderr=second argument\n"


def test_windows_bash_pin_authority_is_native_openable_and_pins_exact_bytes(
    tmp_path: Path,
):
    if os.name != "nt" or not BASH.is_file():
        pytest.skip("Windows Git Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    canonical_start = source.index("canonical_executable_path()")
    canonical = source[
        canonical_start : source.index(
            '\n\nif [ "$EARLY_REQUIRED_ARGUMENTS_VALID" = true ]',
            canonical_start,
        )
    ]
    pin_start = source.index("pin_executable_authorities()")
    pin = source[
        pin_start : source.index("\n\nverify_pinned_executable()", pin_start)
    ]
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    script = "\n".join(
        (
            "set -u",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { command "$PYTHON_EXECUTOR" "$@"; }',
            canonical,
            pin,
            f"EXECUTABLE_PIN_ROOT={shlex.quote(_bash_path(pin_root))}",
            "MOUNT_AUTHORITY=",
            "PYTHON_DEPENDENCY_HOOK=",
            "NUXT_DEPENDENCY_HOOK=",
            "UNIT_VERIFY_HOOK=",
            'BASH_EXECUTOR="$(canonical_executable_path "$BASH")"',
            "BASH_PIN_AUTHORITY=$BASH_EXECUTOR",
            'digests="$(pin_executable_authorities)"',
            "printf '%s\\n%s\\n' \"$BASH_EXECUTOR\" \"$digests\"",
        )
    )

    result = _run_bash_script(tmp_path / "pin-windows-bash.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    authority, digests = result.stdout.splitlines()
    assert authority.endswith("/bash.exe")
    native_authority = subprocess.check_output(
        [str(BASH), "-lc", f"cygpath -w {shlex.quote(authority)}"],
        cwd=ROOT,
        text=True,
    ).strip()
    authority_bytes = Path(native_authority).read_bytes()
    assert (pin_root / "bash-interpreter").read_bytes() == authority_bytes
    assert digests.split("\t")[-1] == hashlib.sha256(authority_bytes).hexdigest()


def test_windows_local_pinned_bash_child_sanitizes_startup_environment(
    tmp_path: Path,
):
    if os.name != "nt" or not BASH.is_file():
        pytest.skip("Windows Git Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    poison_marker = tmp_path / "bash-env-sourced"
    env_shadow_marker = tmp_path / "env-shadow-ran"
    path_shadow_marker = tmp_path / "path-bash-ran"
    poison = tmp_path / "poison.bash"
    poison.write_text(
        f"printf poison > '{_bash_path(poison_marker)}'\n",
        encoding="ascii",
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_bash = fake_bin / "bash"
    fake_bash.write_text(
        "#!/bin/sh\n"
        f"printf path-shadow > '{_bash_path(path_shadow_marker)}'\n"
        "exit 0\n",
        encoding="ascii",
    )
    fake_bash.chmod(0o755)
    hook = pin_root / "python-dependency"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "if env | grep -Eq '^(BASH_ENV|ENV|BASHOPTS|SHELLOPTS|BASH_COMPAT|POSIXLY_CORRECT|BASH_FUNC_[^=]*%%)='; then exit 81; fi\n"
        "if declare -F poisoned_hook_function >/dev/null; then exit 82; fi\n"
        "printf 'env=%s\\n' \"$PIN_TEST_ENV\"\n"
        "exit 37\n",
        encoding="ascii",
    )
    hook.chmod(0o500)
    prelude = "\n".join(
        (
            f"BASH_ENV={shlex.quote(_bash_path(poison))}",
            f"ENV={shlex.quote(_bash_path(poison))}",
            "BASH_COMPAT=42",
            "POSIXLY_CORRECT=1",
            "export BASH_ENV ENV BASHOPTS SHELLOPTS BASH_COMPAT POSIXLY_CORRECT",
            "poisoned_hook_function() { return 0; }",
            "export -f poisoned_hook_function",
            f"env() {{ printf env-shadow > {shlex.quote(_bash_path(env_shadow_marker))}; return 90; }}",
            "export -f env",
            f"PATH={shlex.quote(_bash_path(fake_bin))}:$PATH",
            "export PATH",
        )
    )

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        hashlib.sha256(hook.read_bytes()).hexdigest(),
        [],
        local_rehearsal=True,
        env_overrides={"PIN_TEST_ENV": "preserved-env"},
        runner_prelude=prelude,
    )

    assert result.returncode == 37, result.stderr + result.stdout
    assert result.stdout == "env=preserved-env\n"
    assert not poison_marker.exists()
    assert not env_shadow_marker.exists()
    assert not path_shadow_marker.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd exec only")
def test_linux_pinned_bash_child_sanitizes_startup_environment(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    poison_marker = tmp_path / "bash-env-sourced"
    poison = tmp_path / "poison.bash"
    poison.write_text(
        f"printf poison > '{_bash_path(poison_marker)}'\n",
        encoding="ascii",
    )
    hook = pin_root / "python-dependency"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "if env | grep -Eq '^(BASH_ENV|ENV|BASHOPTS|SHELLOPTS|BASH_COMPAT|POSIXLY_CORRECT|BASH_FUNC_[^=]*%%)='; then exit 81; fi\n"
        "if declare -F poisoned_hook_function >/dev/null; then exit 82; fi\n"
        "printf 'env=%s\\n' \"$PIN_TEST_ENV\"\n"
        "exit 37\n",
        encoding="ascii",
    )
    hook.chmod(0o500)
    bash_authority = BASH.resolve()
    pinned_bash = pin_root / "bash-interpreter"
    shutil.copy2(bash_authority, pinned_bash)
    pinned_bash.chmod(0o500)
    prelude = "\n".join(
        (
            f"BASH_ENV={shlex.quote(_bash_path(poison))}",
            f"ENV={shlex.quote(_bash_path(poison))}",
            "BASH_COMPAT=42",
            "POSIXLY_CORRECT=1",
            "export BASH_ENV ENV BASHOPTS SHELLOPTS BASH_COMPAT POSIXLY_CORRECT",
            "poisoned_hook_function() { return 0; }",
            "export -f poisoned_hook_function",
        )
    )

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        hashlib.sha256(hook.read_bytes()).hexdigest(),
        [],
        local_rehearsal=False,
        bash_digest=hashlib.sha256(pinned_bash.read_bytes()).hexdigest(),
        bash_executor=bash_authority,
        env_overrides={"PIN_TEST_ENV": "preserved-env"},
        runner_prelude=prelude,
    )

    assert result.returncode == 37, result.stderr + result.stdout
    assert result.stdout == "env=preserved-env\n"
    assert not poison_marker.exists()


def test_windows_local_pinned_executor_rejects_digest_and_unknown_role(
    tmp_path: Path,
):
    if os.name != "nt" or not BASH.is_file():
        pytest.skip("Windows Git Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    hook = pin_root / "python-dependency"
    hook.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="ascii")
    hook.chmod(0o500)

    mismatch = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        "0" * 64,
        [],
        local_rehearsal=True,
    )
    unknown = _invoke_standalone_pinned_executor(
        pin_root,
        "attacker-path",
        hashlib.sha256(hook.read_bytes()).hexdigest(),
        [],
        local_rehearsal=True,
    )

    assert mismatch.returncode == 126
    assert "executable-authority-digest-mismatch" in mismatch.stderr
    assert unknown.returncode == 126
    assert "executable-authority-role-invalid" in unknown.stderr


def test_windows_nonlocal_pinned_executor_has_no_path_fallback(tmp_path: Path):
    if os.name != "nt" or not BASH.is_file():
        pytest.skip("Windows Git Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    hook = pin_root / "python-dependency"
    marker = tmp_path / "executed"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        f": > '{_bash_path(marker)}'\n",
        encoding="ascii",
    )
    hook.chmod(0o500)

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        hashlib.sha256(hook.read_bytes()).hexdigest(),
        [],
        local_rehearsal=False,
    )

    assert result.returncode == 126
    assert "executable-authority-windows-fallback-forbidden" in result.stderr
    assert not marker.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd exec only")
@pytest.mark.parametrize(
    ("digest_override", "shebang", "expected_error"),
    (
        ("0" * 64, "#!/bin/sh", "executable-authority-digest-mismatch"),
        (None, "#!/usr/bin/env sh", "executable-authority-shebang-forbidden"),
    ),
)
def test_linux_pinned_executor_fails_closed_on_digest_and_shebang(
    tmp_path: Path,
    digest_override: str | None,
    shebang: str,
    expected_error: str,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    hook = pin_root / "python-dependency"
    hook.write_text(f"{shebang}\nprintf safe-output\\n", encoding="ascii")
    hook.chmod(0o500)
    digest = digest_override or hashlib.sha256(hook.read_bytes()).hexdigest()

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        digest,
        [],
        local_rehearsal=False,
    )

    assert result.returncode == 126
    assert expected_error in result.stderr
    assert "safe-output" not in result.stdout


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd exec only")
def test_linux_pinned_executor_preserves_args_env_stdin_output_and_exit(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    hook = pin_root / "python-dependency"
    hook.write_text(
        "#!/bin/sh\n"
        "IFS= read -r payload\n"
        "printf 'arg=%s\\nenv=%s\\nstdin=%s\\n' \"$1\" \"$PIN_TEST_ENV\" \"$payload\"\n"
        "printf 'stderr=%s\\n' \"$2\" >&2\n"
        "exit 37\n",
        encoding="ascii",
    )
    hook.chmod(0o500)

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        hashlib.sha256(hook.read_bytes()).hexdigest(),
        ["first argument", "second argument"],
        local_rehearsal=False,
        env_overrides={"PIN_TEST_ENV": "preserved-env"},
        stdin="preserved-stdin\n",
    )

    assert result.returncode == 37, result.stderr + result.stdout
    assert result.stdout.splitlines() == [
        "arg=first argument",
        "env=preserved-env",
        "stdin=preserved-stdin",
    ]
    assert result.stderr == "stderr=second argument\n"


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd exec only")
def test_linux_env_bash_hook_preserves_process_contract_through_descriptors(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    hook = pin_root / "python-dependency"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "IFS= read -r payload\n"
        "printf 'argv0=%s\\narg=%s\\nenv=%s\\nstdin=%s\\n' "
        '"$0" "$1" "$PIN_TEST_ENV" "$payload"\n'
        "printf 'stderr=%s\\n' \"$2\" >&2\n"
        "exit 37\n",
        encoding="ascii",
    )
    hook.chmod(0o500)
    bash_authority = BASH.resolve()
    pinned_bash = pin_root / "bash-interpreter"
    shutil.copy2(bash_authority, pinned_bash)
    pinned_bash.chmod(0o500)

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        hashlib.sha256(hook.read_bytes()).hexdigest(),
        ["first argument", "second argument"],
        local_rehearsal=False,
        bash_digest=hashlib.sha256(pinned_bash.read_bytes()).hexdigest(),
        bash_executor=bash_authority,
        env_overrides={"PIN_TEST_ENV": "preserved-env"},
        stdin="preserved-stdin\n",
    )

    assert result.returncode == 37, result.stderr + result.stdout
    lines = result.stdout.splitlines()
    assert lines[0].startswith("argv0=/proc/self/fd/")
    assert lines[1:] == [
        "arg=first argument",
        "env=preserved-env",
        "stdin=preserved-stdin",
    ]
    assert result.stderr == "stderr=second argument\n"


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd exec only")
def test_linux_env_bash_hook_fails_closed_when_bash_pin_is_missing(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    pin_root = tmp_path / "pins"
    pin_root.mkdir(mode=0o700)
    hook = pin_root / "python-dependency"
    marker = tmp_path / "target-ran"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        f": > '{_bash_path(marker)}'\n",
        encoding="ascii",
    )
    hook.chmod(0o500)

    result = _invoke_standalone_pinned_executor(
        pin_root,
        "python-dependency",
        hashlib.sha256(hook.read_bytes()).hexdigest(),
        [],
        local_rehearsal=False,
        bash_digest="0" * 64,
        bash_executor=BASH.resolve(),
    )

    assert result.returncode == 126
    assert "executable-authority-pin-invalid" in result.stderr
    assert "Traceback" not in result.stderr
    assert not marker.exists()


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
        if failure_kind == "verification":
            count_file = case_root / "verify-count"
            python_executor = _write_local_python_executor(
                case_root / "premutation-failure-python",
                f"  if [ \"$1\" = '{_bash_path(VERIFY)}' ]; then\n"
                f"    count=$(cat '{_bash_path(count_file)}' 2>/dev/null || printf 0)\n"
                "    count=$((count + 1))\n"
                f"    printf '%s\\n' \"$count\" > '{_bash_path(count_file)}'\n"
                "    [ \"$count\" -ne 2 ] || exit 61\n"
                "  fi\n"
                "command \"$REAL_PYTHON\" \"$@\"\n",
            )
            env_overrides = {
                "VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)
            }
        else:
            bash_env = case_root / "premutation-failure.bash"
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


def test_premutation_cleanup_preserves_replaced_private_staging_root(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "replaced-private-staging"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, before_release, before_persistent, _, _ = prepared
    hook = case_root / "runtime" / "python-hook.sh"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "stage=\n"
        "while (($#)); do\n"
        "  if [ \"$1\" = --release-root ]; then stage=\"$2\"; break; fi\n"
        "  shift\n"
        "done\n"
        "[ -n \"$stage\" ] || exit 70\n"
        "/usr/bin/rm -rf -- \"$stage\"\n"
        "mkdir -- \"$stage\"\n"
        "printf 'must survive\\n' > \"$stage/foreign.txt\"\n"
        "exit 19\n",
        encoding="ascii",
    )

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 19, result.stderr + result.stdout
    staging_roots = [
        path
        for path in release.parent.glob(f".{release.name}.closed-stage.*")
        if path.is_dir()
    ]
    assert len(staging_roots) == 1
    assert (staging_roots[0] / "foreign.txt").read_text(encoding="ascii") == (
        "must survive\n"
    )
    assert Path(f"{staging_roots[0]}.owner").is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent


def test_stage_owner_cleanup_retries_before_disarming(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "stage-owner-cleanup-failure"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, before_release, before_persistent, _, _ = prepared
    failure_used = case_root / "owner-rm-failure-used"
    rm_executor = _write_cleanup_rm_fault_executor(
        case_root / "owner-rm-failure",
        basename_pattern=f".{release.name}.closed-stage.*.owner",
        marker=failure_used,
        status=61,
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_RM_EXECUTOR": _bash_path(rm_executor)},
    )

    assert result.returncode == 61, result.stderr + result.stdout
    assert failure_used.is_file()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
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
    python_executor = _write_local_python_executor(
        case_root / "archive-replacement-python",
        "command \"$REAL_PYTHON\" \"$@\"\n"
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
        "exit \"$status\"\n",
    )
    bash_env = case_root / "archive-replacement.bash"
    bash_env.write_text(
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
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor),
        },
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
    first, first_stdout_path, first_stderr_path = _start_file_backed_process(
        _installer_command(closed_package, case_root, prepared),
        case_root=case_root,
        env=env,
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
        first_stdout, first_stderr, first_cleanup_errors = (
            _finish_file_backed_process(
                first, first_stdout_path, first_stderr_path, timeout=60
            )
        )

    assert not first_cleanup_errors, (
        "; ".join(first_cleanup_errors) + "\n" + first_stderr + first_stdout
    )
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


@pytest.mark.parametrize("target_role", ("release", "persistent", "systemd"))
def test_evidence_role_collision_is_rejected_before_any_mutation(
    tmp_path: Path, closed_package, target_role: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"evidence-role-collision-{target_role}"
    prepared = _prepare_case(case_root, closed_package)
    (
        release,
        persistent,
        evidence,
        before_release,
        before_persistent,
        hook_log,
        values,
    ) = prepared
    if target_role == "release":
        evidence = release
    elif target_role == "persistent":
        evidence = persistent
    else:
        evidence = case_root / "runtime" / "systemd-units"
        evidence.mkdir()
        (evidence / "forensic-marker.txt").write_text("keep\n", encoding="ascii")
    prepared = (
        release,
        persistent,
        evidence,
        before_release,
        before_persistent,
        hook_log,
        values,
    )
    case_before = _snapshot_tree(case_root)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "install-authority-role-collision" in result.stderr
    assert not hook_log.exists()
    assert _snapshot_tree(case_root) == case_before
    assert not list(case_root.rglob("authority-*.lock"))


@pytest.mark.parametrize("colliding_role", ("persistent", "systemd"))
def test_same_attempt_rejects_canonical_authority_collision_across_roles(
    tmp_path: Path, closed_package, colliding_role: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"same-attempt-role-collision-{colliding_role}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, hook_log, values = prepared
    if colliding_role == "persistent":
        persistent = release
    else:
        collision_authority = case_root / "runtime" / "systemd-units"
        release.rename(collision_authority)
        release = collision_authority
        sentinel = case_root / "runtime" / ".vl360-local-rehearsal"
        sentinel.write_text("vinhlong360-local-rehearsal-v1\n", encoding="ascii")
        values["VL360_LOCAL_REHEARSAL_SENTINEL"] = _bash_path(sentinel)
    prepared = (release, persistent, evidence, {}, {}, hook_log, values)
    case_before = _snapshot_tree(case_root)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "install-authority-role-collision" in result.stderr
    assert not hook_log.exists()
    assert _snapshot_tree(case_root) == case_before
    assert not list(case_root.rglob("authority-*.lock"))


def test_persistent_and_systemd_role_collision_is_rejected_before_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "persistent-systemd-role-collision"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, hook_log, values = prepared
    systemd_destination = case_root / "runtime" / "systemd-units"
    persistent.rename(systemd_destination)
    persistent = systemd_destination
    prepared = (release, persistent, evidence, {}, {}, hook_log, values)
    case_before = _snapshot_tree(case_root)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "install-authority-role-collision" in result.stderr
    assert not hook_log.exists()
    assert _snapshot_tree(case_root) == case_before
    assert not list(case_root.rglob("authority-*.lock"))


def test_nested_release_and_persistent_roles_are_rejected_before_any_mutation(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "nested-release-persistent"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, hook_log, values = prepared
    nested = release / "persistent"
    persistent.rename(nested)
    persistent = nested
    prepared = (release, persistent, evidence, {}, {}, hook_log, values)
    case_before = _snapshot_tree(case_root)

    result = _invoke_installer(closed_package, case_root, prepared)

    assert result.returncode == 2, result.stderr + result.stdout
    assert "install-authority-role-collision" in result.stderr
    assert not hook_log.exists()
    assert _snapshot_tree(case_root) == case_before
    assert not list(case_root.rglob("authority-*.lock"))


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
    first, first_stdout_path, first_stderr_path = _start_file_backed_process(
        _installer_command(closed_package, first_root, first_prepared),
        case_root=first_root,
        env=first_env,
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
        first_stdout, first_stderr, first_cleanup_errors = (
            _finish_file_backed_process(
                first, first_stdout_path, first_stderr_path, timeout=60
            )
        )

    assert not first_cleanup_errors, (
        "; ".join(first_cleanup_errors) + "\n" + first_stderr + first_stdout
    )
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
    first, first_stdout_path, first_stderr_path = _start_file_backed_process(
        _installer_command(closed_package, first_root, first_prepared),
        case_root=first_root,
        env=first_env,
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
        first_stdout, first_stderr, first_cleanup_errors = (
            _finish_file_backed_process(
                first, first_stdout_path, first_stderr_path, timeout=60
            )
        )

    assert not first_cleanup_errors, (
        "; ".join(first_cleanup_errors) + "\n" + first_stderr + first_stdout
    )
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
    if os.name == "nt":
        env.update(_windows_process_identity_env(case_root))
    first, first_stdout_path, first_stderr_path = _start_file_backed_process(
        _installer_command(closed_package, case_root, prepared),
        case_root=case_root,
        env=env,
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
        first_stdout, first_stderr, first_cleanup_errors = (
            _finish_file_backed_process(
                first, first_stdout_path, first_stderr_path, timeout=60
            )
        )

    assert not first_cleanup_errors, (
        "; ".join(first_cleanup_errors) + "\n" + first_stderr + first_stdout
    )
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
    completed = []
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
            lock_barrier = case_root / "lock-barrier.bash"
            lock_barrier.write_text(
                "shopt -u extdebug\n"
                "set +T\n"
                "__vl360_lock_barrier_state=waiting\n"
                "__vl360_lock_barrier() {\n"
                "  if [ \"$__vl360_lock_barrier_state\" = armed ]; then\n"
                "    trap - DEBUG\n"
                f"    : > {shlex.quote(_bash_path(entered))}\n"
                "    while [ ! -f "
                f"{shlex.quote(_bash_path(release_hook))} ]; do sleep 0.05; done\n"
                "    return 0\n"
                "  fi\n"
                "  if [ \"${BASH_COMMAND-}\" = 'record_install_lock acquired 0' ]; then\n"
                "    __vl360_lock_barrier_state=armed\n"
                "  fi\n"
                "  return 0\n"
                "}\n"
                "trap '__vl360_lock_barrier' DEBUG\n",
                encoding="ascii",
            )
            *_, values = prepared
            env = os.environ.copy()
            env.update(values)
            env["BASH_ENV"] = _bash_path(lock_barrier)
            process, stdout_path, stderr_path = _start_file_backed_process(
                _installer_command(closed_package, case_root, prepared),
                case_root=case_root,
                env=env,
            )
            processes.append((process, stdout_path, stderr_path))
            releases.append(release_hook)
            prepared_cases.append((prepared, entered))
        for prepared, entered in prepared_cases:
            _wait_for_path(entered)
            _, _, evidence, *_ = prepared
            lock = json.loads(
                (evidence / "install-lock.json").read_text(encoding="utf-8")
            )
            assert lock["status"] == "acquired"
    finally:
        for release_hook in releases:
            release_hook.touch()
        completed = _finish_file_backed_processes(processes, timeout=60)

    for (process, stdout, stderr, cleanup_errors), (prepared, _) in zip(
        completed, prepared_cases, strict=True
    ):
        assert not cleanup_errors, (
            "; ".join(cleanup_errors) + "\n" + stderr + stdout
        )
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
    assert _private_attempt_artifacts(tmp_path / "full-success", evidence) == {
        "archive": [],
        "pin": [],
        "lock": [],
    }


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
    process, stdout_path, stderr_path = _start_file_backed_process(
        _installer_command(closed_package, case_root, prepared),
        case_root=case_root,
        env=env,
    )
    try:
        _wait_for_path(entered)
        external.write_text("INDEXING_UNLOCK_KEY=opened\n", encoding="ascii")
    finally:
        release_hook.touch()
        stdout, stderr, cleanup_errors = _finish_file_backed_process(
            process, stdout_path, stderr_path, timeout=60
        )

    assert not cleanup_errors, "; ".join(cleanup_errors) + "\n" + stderr + stdout
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
    lock_before = json.loads(
        (evidence / "install-lock.json").read_text(encoding="utf-8")
    )

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
    if invalid_authority in {"environment", "runtime"}:
        assert not (evidence / "install-lock.json").exists()
    else:
        # Hook rejection rewrites the lock with the narrowed authority set.
        lock_after = json.loads(
            (evidence / "install-lock.json").read_text(encoding="utf-8")
        )
        assert lock_after["status"] == "released"
        assert lock_after["exit_code"] == 0
        assert lock_after != lock_before


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
            "--migration-gate-evidence",
            _bash_path(case_root / "migration-gate.json"),
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
    assert not (evidence / "install-lock.json").exists()


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
    # Keep this node name for continuation replay; malformed discovery preserves evidence.
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
    evidence_before = _snapshot_tree(evidence)
    evidence_arg = _bash_path_literal(evidence)
    args = [evidence_arg if value == "{evidence}" else value for value in raw_args]

    second = _invoke_installer_args(prepared, args)

    assert second.returncode == 2
    assert expected_error in second.stderr
    assert _snapshot_tree(evidence) == evidence_before
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


def _interrupt_after_systemd_mutation(
    package,
    case_root: Path,
    prepared,
    *,
    evidence_arg: str | None = None,
    runtime_arg: str | None = None,
):
    release, _, evidence, _, _, _, values = prepared
    unit_destination = case_root / "runtime" / "systemd-units"
    unit_destination.mkdir()
    for name in SYSTEMD_UNIT_NAMES:
        (unit_destination / name).write_bytes(f"legacy-{name}\n".encode("ascii"))
    legacy_units = _snapshot_tree(unit_destination)
    interrupted = case_root / "interrupted-systemd-units"
    unit_hook = case_root / "runtime" / "units-hook.sh"
    unit_hook.write_text(
        "#!/usr/bin/env bash\n"
        f": > '{_bash_path(interrupted)}'\n"
        "kill -9 \"$PPID\"\n"
        "exit 97\n",
        encoding="ascii",
    )
    unit_hook.chmod(0o755)
    env = os.environ.copy()
    env.update(values)

    result = subprocess.run(
        _installer_command(
            package,
            case_root,
            prepared,
            evidence_arg=evidence_arg,
            runtime_arg=runtime_arg,
        ),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, result.stderr + result.stdout
    assert interrupted.is_file()
    assert _snapshot_tree(unit_destination) != legacy_units
    journal = evidence / "install-mutation-state.json"
    payload = json.loads(journal.read_text(encoding="utf-8"))
    attempts = list(evidence.glob(".systemd-unit-attempt.*"))
    assert len(attempts) == 1
    assert (attempts[0] / "armed").is_file()
    assert payload["stage"] == "systemd-units-armed"
    assert payload["systemd_unit_destination"] == _bash_path(unit_destination)
    assert payload["systemd_unit_attempt_root"] == _bash_path(attempts[0])
    assert len(payload["systemd_key_sha256"]) == 64
    return journal, attempts[0], unit_destination, legacy_units


def test_evidence_parent_alias_journal_is_canonical_and_retryable_after_sigkill(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "evidence-parent-alias"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    alias_component = case_root / "evidence-alias-component"
    alias_component.mkdir()
    evidence_arg = (
        f"{_bash_path_literal(alias_component)}/../{evidence.name}"
    )

    journal, attempt, _, _ = _interrupt_after_systemd_mutation(
        closed_package,
        case_root,
        prepared,
        evidence_arg=evidence_arg,
    )

    payload = json.loads(journal.read_text(encoding="utf-8"))
    assert payload["systemd_unit_attempt_root"] == _bash_path(attempt)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
        evidence_arg=evidence_arg,
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    assert not journal.exists()


@pytest.mark.parametrize("alias_kind", ("dot", "parent"))
def test_runtime_alias_journal_uses_canonical_systemd_destination_and_retries(
    tmp_path: Path, closed_package, alias_kind: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"runtime-alias-{alias_kind}"
    prepared = _prepare_case(case_root, closed_package)
    runtime = case_root / "runtime"
    if alias_kind == "dot":
        runtime_arg = f"{_bash_path_literal(runtime)}/."
    else:
        alias_component = runtime / "authority-alias-component"
        alias_component.mkdir()
        runtime_arg = f"{_bash_path_literal(alias_component)}/.."

    journal, _, unit_destination, _ = _interrupt_after_systemd_mutation(
        closed_package,
        case_root,
        prepared,
        runtime_arg=runtime_arg,
    )

    payload = json.loads(journal.read_text(encoding="utf-8"))
    assert payload["systemd_unit_destination"] == _bash_path(unit_destination)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
        runtime_arg=runtime_arg,
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    assert not journal.exists()


def test_environment_authority_symlink_parent_is_rejected_before_evidence_reset(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "environment-symlink-parent"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, hook_log, _ = prepared
    alias_parent = case_root / "environment-parent-alias"
    try:
        alias_parent.symlink_to(case_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    preserved = evidence / "install-summary.json"
    preserved.write_bytes(b"must-survive\n")
    release_before = _snapshot_tree(release)
    persistent_before = _snapshot_tree(persistent)

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        environment_arg=_bash_path_literal(alias_parent / "external.env"),
    )

    assert result.returncode == 2, result.stderr + result.stdout
    assert "external-environment-authority-required" in result.stderr
    assert preserved.read_bytes() == b"must-survive\n"
    assert not hook_log.exists()
    assert _snapshot_tree(release) == release_before
    assert _snapshot_tree(persistent) == persistent_before


@pytest.mark.parametrize("authority_role", ("release", "persistent", "systemd"))
def test_stale_recovery_rejects_nested_same_role_authorities_before_mutation(
    tmp_path: Path, closed_package, authority_role: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"ns-{authority_role[0]}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, hook_log, values = prepared
    journal, attempt, unit_destination, _ = _interrupt_after_systemd_mutation(
        closed_package, case_root, prepared
    )
    current_release = release
    current_persistent = persistent
    runtime_arg = None
    if authority_role == "release":
        current_release = release / "current-release"
        sentinel = release / ".vl360-current-rehearsal"
        sentinel.write_text("vinhlong360-local-rehearsal-v1\n", encoding="ascii")
        values["VL360_LOCAL_REHEARSAL_SENTINEL"] = _bash_path(sentinel)
    elif authority_role == "persistent":
        current_persistent = persistent / "current-persistent"
    else:
        runtime_arg = _bash_path(unit_destination)
    current_prepared = (
        current_release,
        current_persistent,
        evidence,
        {},
        {},
        hook_log,
        values,
    )
    python_hook = case_root / "runtime" / "python-hook.sh"
    python_hook.write_text("#!/usr/bin/env bash\nexit 19\n", encoding="ascii")
    python_hook.chmod(0o755)
    journal_before = journal.read_bytes()
    attempt_before = _snapshot_tree(attempt)
    release_before = _snapshot_tree(release)
    persistent_before = _snapshot_tree(persistent)
    units_before = _snapshot_tree(unit_destination)
    env = os.environ.copy()
    env.update(values)

    retry = subprocess.run(
        _installer_command(
            closed_package,
            case_root,
            current_prepared,
            runtime_arg=runtime_arg,
        ),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "install-authority-role-collision" in retry.stderr
    assert journal.read_bytes() == journal_before
    assert _snapshot_tree(attempt) == attempt_before
    assert _snapshot_tree(release) == release_before
    assert _snapshot_tree(persistent) == persistent_before
    assert _snapshot_tree(unit_destination) == units_before


@pytest.mark.parametrize(
    "journal_mutation",
    (
        "uppercase-attempt-id",
        "noncanonical-working-paths",
    ),
)
def test_stale_recovery_rejects_noncanonical_journal_before_file_operations(
    tmp_path: Path, closed_package, journal_mutation: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"journal-{journal_mutation}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, _ = prepared
    journal, attempt, unit_destination, _ = _interrupt_after_systemd_mutation(
        closed_package, case_root, prepared
    )
    payload = json.loads(journal.read_text(encoding="utf-8"))
    if journal_mutation == "uppercase-attempt-id":
        payload["attempt_id"] = payload["attempt_id"].upper()
        payload["retired_root"] = payload["retired_root"].rsplit(".", 1)[0] + (
            f".{payload['attempt_id']}"
        )
    else:
        release_parent, release_name = payload["release_root"].rsplit("/", 1)
        noncanonical_parent = f"{release_parent}/."
        payload["release_root"] = f"{noncanonical_parent}/{release_name}"
        payload["staging_root"] = (
            f"{noncanonical_parent}/.{release_name}.closed-stage.{payload['pid']}"
        )
        payload["old_root"] = (
            f"{noncanonical_parent}/.{release_name}.closed-old.{payload['pid']}"
        )
        payload["retired_root"] = (
            f"{noncanonical_parent}/.{release_name}.closed-retired."
            f"{payload['attempt_id']}"
        )
    journal.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    journal_before = journal.read_bytes()
    attempt_before = _snapshot_tree(attempt)
    release_before = _snapshot_tree(release)
    persistent_before = _snapshot_tree(persistent)
    units_before = _snapshot_tree(unit_destination)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert journal.read_bytes() == journal_before
    assert _snapshot_tree(attempt) == attempt_before
    assert _snapshot_tree(release) == release_before
    assert _snapshot_tree(persistent) == persistent_before
    assert _snapshot_tree(unit_destination) == units_before


@pytest.mark.parametrize(
    "authority_mutation",
    (
        "release-redundant-separator",
        "persistent-parent-traversal",
        "systemd-redundant-component",
        "systemd-attempt-redundant-separator",
        "release-symlink-parent",
    ),
)
def test_stale_recovery_rejects_noncanonical_authority_spelling_before_mutation(
    tmp_path: Path, closed_package, authority_mutation: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"ja-{authority_mutation[0]}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, _ = prepared
    journal, attempt, unit_destination, _ = _interrupt_after_systemd_mutation(
        closed_package, case_root, prepared
    )
    payload = json.loads(journal.read_text(encoding="utf-8"))
    if authority_mutation == "release-redundant-separator":
        parent, name = payload["release_root"].rsplit("/", 1)
        payload["release_root"] = f"{parent}//{name}"
    elif authority_mutation == "persistent-parent-traversal":
        alias_component = case_root / "authority-alias-component"
        alias_component.mkdir()
        parent, name = payload["persistent_root"].rsplit("/", 1)
        payload["persistent_root"] = f"{parent}/{alias_component.name}/../{name}"
    elif authority_mutation == "systemd-redundant-component":
        parent, name = payload["systemd_unit_destination"].rsplit("/", 1)
        payload["systemd_unit_destination"] = f"{parent}/./{name}"
    elif authority_mutation == "systemd-attempt-redundant-separator":
        parent, name = payload["systemd_unit_attempt_root"].rsplit("/", 1)
        payload["systemd_unit_attempt_root"] = f"{parent}//{name}"
    else:
        alias_parent = case_root / "authority-parent-alias"
        try:
            alias_parent.symlink_to(case_root, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"directory symlinks are unavailable: {exc}")
        canonical_parent = _bash_path(case_root)
        alias_prefix = _bash_path_literal(alias_parent)
        for field in ("release_root", "staging_root", "old_root", "retired_root"):
            payload[field] = payload[field].replace(
                f"{canonical_parent}/", f"{alias_prefix}/", 1
            )
    journal.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    journal_before = journal.read_bytes()
    attempt_before = _snapshot_tree(attempt)
    release_before = _snapshot_tree(release)
    persistent_before = _snapshot_tree(persistent)
    units_before = _snapshot_tree(unit_destination)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert journal.read_bytes() == journal_before
    assert _snapshot_tree(attempt) == attempt_before
    assert _snapshot_tree(release) == release_before
    assert _snapshot_tree(persistent) == persistent_before
    assert _snapshot_tree(unit_destination) == units_before


def _rewrite_systemd_backup_metadata(attempt: Path, mutation: str) -> None:
    metadata_path = attempt / "backup" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if mutation == "unexpected-service":
        metadata["unrelated.service"] = {"existed": False, "mode": 0}
    elif mutation == "missing-service":
        metadata.pop("vl-watchdog.timer")
    elif mutation == "unexpected-field":
        metadata["vl-watchdog.timer"]["destination"] = "untrusted"
    elif mutation == "wrong-type":
        metadata["vl-watchdog.timer"]["mode"] = "420"
    elif mutation == "path-key":
        metadata["../protected.service"] = metadata.pop("vl-watchdog.timer")
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


@pytest.mark.parametrize(
    "metadata_mutation",
    (
        "unexpected-service",
        "missing-service",
        "unexpected-field",
        "wrong-type",
        "path-key",
    ),
)
def test_stale_systemd_recovery_rejects_noncanonical_metadata_before_mutation(
    tmp_path: Path, closed_package, metadata_mutation: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"systemd-metadata-{metadata_mutation}"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, _ = prepared
    journal, attempt, unit_destination, _ = _interrupt_after_systemd_mutation(
        closed_package, case_root, prepared
    )
    protected = unit_destination / "unrelated.service"
    protected.write_bytes(b"must-survive\n")
    _rewrite_systemd_backup_metadata(attempt, metadata_mutation)
    journal_before = journal.read_bytes()
    attempt_before = _snapshot_tree(attempt)
    release_before = _snapshot_tree(release)
    persistent_before = _snapshot_tree(persistent)
    units_before = _snapshot_tree(unit_destination)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert journal.read_bytes() == journal_before
    assert _snapshot_tree(attempt) == attempt_before
    assert _snapshot_tree(release) == release_before
    assert _snapshot_tree(persistent) == persistent_before
    assert _snapshot_tree(unit_destination) == units_before
    assert protected.read_bytes() == b"must-survive\n"


def test_systemd_recovery_material_is_durable_before_journal_and_unit_mutation():
    source = INSTALL.read_text(encoding="utf-8")
    flow = source[source.index("INSTALL_FAILURE_POINT=install-systemd-units") :]
    assert flow.index("prepare_systemd_unit_attempt") < flow.index(
        "write_mutation_state systemd-backup-preparing"
    ) < flow.index("prepare_systemd_unit_backup") < flow.index(
        "write_mutation_state systemd-units-armed"
    ) < flow.index("install_systemd_units")

    backup = source[
        source.index("prepare_systemd_unit_backup()") : source.index(
            "install_systemd_units()"
        )
    ]
    for required in (
        "write_durable_bytes(backup_file",
        "write_durable_text(metadata_path",
        "write_durable_text(marker",
        "fsync_directory(backup)",
        "fsync_directory(backup.parent)",
        "fsync_directory(backup.parent.parent)",
    ):
        assert required in backup

    durable_writer = source[
        source.index("write_durable_atomic_json()") : source.index(
            "write_mutation_state()"
        )
    ]
    assert durable_writer.index("os.replace(temporary, path)") < durable_writer.index(
        "fsync_directory(path.parent)"
    )

    journal = source[
        source.index("write_mutation_state()") : source.index("clear_mutation_state()")
    ]
    assert 'write_durable_atomic_json "$MUTATION_STATE" "$payload"' in journal

    stale_journal = source[
        source.index("write_stale_mutation_state()") : source.index(
            "stale_tree_state()"
        )
    ]
    assert 'write_durable_atomic_json "$MUTATION_STATE" "$payload"' in stale_journal

def test_fsync_directories_uses_os_fsync_off_windows():
    source = INSTALL.read_text(encoding="utf-8")
    helper = source[source.index("fsync_directories()") : source.index("die()")]
    assert 'if os.name == "nt":' in helper
    assert "os.fsync(descriptor)" in helper


def _run_live_post_bind_runtime_reconciliation(
    tmp_path: Path,
    stage: str,
    mount_present: bool | None,
    *,
    fail_fsync_once: bool = False,
    retry_after_failure: bool = False,
    post_umount_state: str = "absent",
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    reconciliation = source[
        source.index("inspect_stale_mount()") : source.index(
            "record_install_lock()"
        )
    ]
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    old_root = tmp_path / ".release.closed-old.321"
    staging = tmp_path / ".release.closed-stage.321"
    retired = tmp_path / (".release.closed-retired." + "a" * 32)
    systemd = tmp_path / "systemd"
    for directory in (release / "agent" / "data", persistent, evidence, old_root / "agent" / "data", systemd):
        directory.mkdir(parents=True, exist_ok=True)
    (release / "launch-release-manifest.json").write_text("{}\n", encoding="ascii")
    (release / "new-marker").write_text("new\n", encoding="ascii")
    (old_root / "old-marker").write_text("old\n", encoding="ascii")
    (persistent / "app.db").write_text("persistent\n", encoding="ascii")
    journal = evidence / "install-mutation-state.json"
    journal.write_text("{}\n", encoding="ascii")
    attempt = evidence / ".systemd-unit-attempt.runtime"
    attempt_value = ""
    if stage != "persistent-restored":
        attempt.mkdir()
        attempt_value = _bash_path(attempt)
        if stage != "systemd-backup-preparing":
            (attempt / "armed").write_text("armed\n", encoding="ascii")
    log = tmp_path / "reconcile.log"
    failed = tmp_path / "fsync-failed"
    initial_mount_state = (
        "2" if mount_present is None else "0" if mount_present else "1"
    )
    fsync_stub = "fsync_directories() { return 0; }"
    if fail_fsync_once:
        fsync_stub = "\n".join(
            (
                "fsync_directories() {",
                "  if [ ! -f \"$FSYNC_FAILED\" ]; then",
                "    : > \"$FSYNC_FAILED\"",
                "    printf 'fsync-fail\\n' >> \"$RECOVERY_LOG\"",
                "    return 71",
                "  fi",
                "  return 0",
                "}",
            )
        )
    reconciliation_calls = "\n".join(
        (
            "reconcile_stale_install_attempt",
            "status=$?",
            "printf '%s|%s\\n' \"$status\" \"$MOUNT_STATE\"",
        )
    )
    if retry_after_failure:
        reconciliation_calls = "\n".join(
            (
                "reconcile_stale_install_attempt",
                "first_status=$?",
                "printf '%s|%s|%s\\n' \"$first_status\" \"$STALE_STAGE\" \"$MOUNT_STATE\"",
                "reconcile_stale_install_attempt",
                "second_status=$?",
                "printf '%s|%s\\n' \"$second_status\" \"$MOUNT_STATE\"",
            )
        )
    script = "\n".join(
        (
            "set -u",
            "LOCAL_REHEARSAL=false",
            "STALE_LOCAL_REHEARSAL=false",
            "RELEASE_NAME=release",
            "CURRENT_RELEASE_KEY=release-key",
            "STALE_RELEASE_KEY=release-key",
            "CURRENT_PERSISTENT_KEY=persistent-key",
            "STALE_PERSISTENT_KEY=persistent-key",
            "CURRENT_SYSTEMD_KEY=systemd-key",
            "STALE_SYSTEMD_KEY=systemd-key",
            "STALE_CANDIDATE_MANIFEST_SHA256=manifest-digest",
            "STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256=candidate-topology-digest",
            "STALE_CANDIDATE_RELEASE_ROOT_IDENTITY=3:4",
            "STALE_SOURCE_RELEASE_TOPOLOGY_SHA256=source-topology-digest",
            "STALE_SOURCE_RELEASE_ROOT_IDENTITY=1:2",
            "CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT=/candidate-topology",
            "SOURCE_RELEASE_TOPOLOGY_SNAPSHOT=/source-topology",
            f"STALE_STAGE={shlex.quote(stage)}",
            "STALE_ATTEMPT_ID=" + "a" * 32,
            "STALE_PID=321",
            f"STALE_RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"STALE_PERSISTENT_ROOT={shlex.quote(_bash_path(persistent))}",
            f"STALE_STAGING_ROOT={shlex.quote(_bash_path(staging))}",
            f"STALE_OLD_ROOT={shlex.quote(_bash_path(old_root))}",
            f"STALE_RETIRED_ROOT={shlex.quote(_bash_path(retired))}",
            f"STALE_SYSTEMD_UNIT_DESTINATION={shlex.quote(_bash_path(systemd))}",
            f"STALE_SYSTEMD_UNIT_ATTEMPT_ROOT={shlex.quote(attempt_value)}",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            f"VERIFY_SCRIPT={shlex.quote(_bash_path(VERIFY))}",
            "SNAPSHOT_BEFORE=/snapshot",
            f"RECOVERY_LOG={shlex.quote(_bash_path(log))}",
            f"FSYNC_FAILED={shlex.quote(_bash_path(failed))}",
            f"MOUNT_STATE={initial_mount_state}",
            f"POST_UMOUNT_STATE={shlex.quote(post_umount_state)}",
            'invoke_python() { "$PYTHON_EXECUTOR" "$@"; }',
            "tree_matches_snapshot() { return 0; }",
            "tree_matches_bound_topology() { return 0; }",
            "verify_stale_journal_bindings() { return 0; }",
            "regular_file_sha256() { printf '%s\\n' \"$STALE_CANDIDATE_MANIFEST_SHA256\"; }",
            "write_cleanup_owner_marker() { return 0; }",
            "verify_cleanup_owner_marker() { return 0; }",
            "remove_file_durably() { /usr/bin/rm -f -- \"$1\"; }",
            "invoke_rm() { rm \"$@\"; }",
            "stale_tree_state() { return 0; }",
            "write_stale_mutation_state() { STALE_STAGE=\"$1\"; printf 'journal:%s\\n' \"$1\" >> \"$RECOVERY_LOG\"; printf '{}\\n' > \"$MUTATION_STATE\"; }",
            "invoke_mount_authority() {",
            "  case \"$1\" in",
            "    findmnt)",
            "      [ \"$2\" = --json ] && [ \"$3\" = --mountpoint ] && [ \"$4\" = \"$STALE_RELEASE_ROOT/agent/data\" ] || return 64",
            "      printf 'findmnt:%s\\n' \"$MOUNT_STATE\" >> \"$RECOVERY_LOG\"",
            "      case \"$MOUNT_STATE\" in",
            "        0)",
            "          source_path=$STALE_PERSISTENT_ROOT",
            "          target_path=$4",
            "          if command -v cygpath >/dev/null 2>&1; then",
            "            source_path=$(cygpath -m \"$source_path\")",
            "            target_path=$(cygpath -m \"$target_path\")",
            "          fi",
            "          printf '{\"filesystems\":[{\"source\":\"%s\",\"target\":\"%s\",\"options\":\"rw,bind\"}]}\\n' \"$source_path\" \"$target_path\"",
            "          return 0",
            "          ;;",
            "        1) return 1 ;;",
            "        3) printf '{}\\n'; return 0 ;;",
            "        *) return 72 ;;",
            "      esac",
            "      ;;",
            "    umount)",
            "      [ \"$2\" = \"$STALE_RELEASE_ROOT/agent/data\" ] || return 64",
            "      printf 'umount\\n' >> \"$RECOVERY_LOG\"",
            "      case \"$POST_UMOUNT_STATE\" in",
            "        absent) MOUNT_STATE=1 ;;",
            "        present) MOUNT_STATE=0 ;;",
            "        invalid) MOUNT_STATE=3 ;;",
            "        *) MOUNT_STATE=2 ;;",
            "      esac",
            "      return 0",
            "      ;;",
            "    mount)",
            "      [ \"$2\" = --bind ] && [ \"$3\" = \"$STALE_PERSISTENT_ROOT\" ] && [ \"$4\" = \"$STALE_RELEASE_ROOT/agent/data\" ] || return 64",
            "      printf 'mount\\n' >> \"$RECOVERY_LOG\"; MOUNT_STATE=0; return 0",
            "      ;;",
            "    *) return 64 ;;",
            "  esac",
            "}",
            fsync_stub,
            "restore_systemd_units_from() { printf 'restore-units\\n' >> \"$RECOVERY_LOG\"; return 0; }",
            "remove_systemd_unit_attempt_root() { /usr/bin/rm -rf -- \"$1\"; }",
            "clear_mutation_state() { /usr/bin/rm -f -- \"$MUTATION_STATE\"; printf 'clear\\n' >> \"$RECOVERY_LOG\"; }",
            reconciliation,
            reconciliation_calls,
        )
    )

    result = _run_bash_script(tmp_path / "reconcile.sh", script)

    return result, release, old_root, journal, log, failed


@pytest.mark.parametrize(
    "stage",
    (
        "persistent-restored",
        "systemd-backup-preparing",
        "systemd-units-armed",
        "retire-old-root-armed",
    ),
)
@pytest.mark.parametrize("mount_present", (True, False))
def test_live_post_bind_runtime_reconciles_present_or_absent_mount(
    tmp_path: Path, stage: str, mount_present: bool
):
    result, release, old_root, journal, log, _ = (
        _run_live_post_bind_runtime_reconciliation(
            tmp_path, stage, mount_present
        )
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "0|0"
    lines = log.read_text(encoding="ascii").splitlines()
    assert ("umount" in lines) is mount_present
    assert "mount" in lines
    assert (release / "old-marker").is_file()
    assert not old_root.exists()
    assert not journal.exists()


def test_live_post_bind_runtime_fails_closed_on_unknown_mount(tmp_path: Path):
    result, release, old_root, journal, _, _ = (
        _run_live_post_bind_runtime_reconciliation(
            tmp_path, "systemd-units-armed", None
        )
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "1|2"
    assert (release / "new-marker").is_file()
    assert (old_root / "old-marker").is_file()
    assert journal.is_file()


@pytest.mark.parametrize("post_probe", ("absent", "present", "invalid"))
def test_stale_recovery_umount_requires_authoritative_absence(
    tmp_path: Path, post_probe: str
):
    result, release, old_root, journal, log, _ = (
        _run_live_post_bind_runtime_reconciliation(
            tmp_path,
            "persistent-restored",
            True,
            post_umount_state=post_probe,
        )
    )

    assert result.returncode == 0, result.stderr + result.stdout
    lines = log.read_text(encoding="ascii").splitlines()
    expected_post_state = {"absent": "1", "present": "0", "invalid": "3"}[
        post_probe
    ]
    assert lines[:4] == [
        "findmnt:0",
        "journal:recovery-detach-persistent-armed",
        "umount",
        f"findmnt:{expected_post_state}",
    ]
    if post_probe == "absent":
        assert result.stdout.strip() == "0|0"
        assert (release / "old-marker").is_file()
        assert not old_root.exists()
        assert not journal.exists()
    else:
        assert result.stdout.strip() == f"1|{expected_post_state}"
        assert (release / "new-marker").is_file()
        assert (old_root / "old-marker").is_file()
        assert json.loads(journal.read_text(encoding="ascii")) == {}


@pytest.mark.parametrize(
    ("stage", "attempt_present", "expected_status", "expected_removed", "journal_present"),
    (
        ("rollback-restored", True, "1", False, True),
        ("rollback-restored", False, "0", False, False),
        ("recovery-remove-systemd-attempt-armed", True, "0", True, False),
    ),
)
def test_terminal_systemd_attempt_stages_do_not_restore_again(
    tmp_path: Path,
    stage: str,
    attempt_present: bool,
    expected_status: str,
    expected_removed: bool,
    journal_present: bool,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    reconciliation = source[
        source.index("inspect_stale_mount()") : source.index("record_install_lock()")
    ]
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    systemd = tmp_path / "systemd"
    attempt = evidence / ".systemd-unit-attempt.rollback"
    for directory in (release / "agent" / "data", persistent, evidence, systemd):
        directory.mkdir(parents=True, exist_ok=True)
    if attempt_present:
        attempt.mkdir()
    (release / "old-marker").write_text("old\n", encoding="ascii")
    if attempt_present:
        (attempt / "armed").write_text("armed\n", encoding="ascii")
    journal = evidence / "install-mutation-state.json"
    journal.write_text("{}\n", encoding="ascii")
    restored = tmp_path / "restore-called"
    removed = tmp_path / "remove-called"
    script = "\n".join(
        (
            "set -u",
            "LOCAL_REHEARSAL=true",
            "STALE_LOCAL_REHEARSAL=true",
            "RELEASE_NAME=release",
            "CURRENT_RELEASE_KEY=release-key",
            "STALE_RELEASE_KEY=release-key",
            "CURRENT_PERSISTENT_KEY=persistent-key",
            "STALE_PERSISTENT_KEY=persistent-key",
            "CURRENT_SYSTEMD_KEY=systemd-key",
            "STALE_SYSTEMD_KEY=systemd-key",
            "STALE_CANDIDATE_MANIFEST_SHA256=manifest-digest",
            "STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256=candidate-topology-digest",
            "STALE_CANDIDATE_RELEASE_ROOT_IDENTITY=3:4",
            "STALE_SOURCE_RELEASE_TOPOLOGY_SHA256=source-topology-digest",
            "STALE_SOURCE_RELEASE_ROOT_IDENTITY=1:2",
            "CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT=/candidate-topology",
            "SOURCE_RELEASE_TOPOLOGY_SNAPSHOT=/source-topology",
            f"STALE_STAGE={stage}",
            "STALE_ATTEMPT_ID=" + "a" * 32,
            "STALE_PID=321",
            f"STALE_RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"STALE_PERSISTENT_ROOT={shlex.quote(_bash_path(persistent))}",
            f"STALE_STAGING_ROOT={shlex.quote(_bash_path(tmp_path / '.release.closed-stage.321'))}",
            f"STALE_OLD_ROOT={shlex.quote(_bash_path(tmp_path / '.release.closed-old.321'))}",
            f"STALE_RETIRED_ROOT={shlex.quote(_bash_path(tmp_path / ('.release.closed-retired.' + 'a' * 32)))}",
            f"STALE_SYSTEMD_UNIT_DESTINATION={shlex.quote(_bash_path(systemd))}",
            f"STALE_SYSTEMD_UNIT_ATTEMPT_ROOT={shlex.quote(_bash_path(attempt))}",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            "SNAPSHOT_BEFORE=/snapshot",
            f"RESTORED={shlex.quote(_bash_path(restored))}",
            f"REMOVED={shlex.quote(_bash_path(removed))}",
            "tree_matches_snapshot() { return 0; }",
            "tree_matches_bound_topology() { return 0; }",
            "verify_stale_journal_bindings() { return 0; }",
            "stale_tree_state() { [ \"$1\" = \"$STALE_RELEASE_ROOT/agent/data\" ] && return 0; [ \"$1\" = \"$STALE_PERSISTENT_ROOT\" ] && return 2; return 1; }",
            "restore_systemd_units_from() { : > \"$RESTORED\"; return 0; }",
            "write_stale_mutation_state() { STALE_STAGE=\"$1\"; }",
            "remove_systemd_unit_attempt_root() { : > \"$REMOVED\"; return 0; }",
            "fsync_directories() { return 0; }",
            "clear_mutation_state() { /usr/bin/rm -f -- \"$MUTATION_STATE\"; }",
            reconciliation,
            "reconcile_stale_install_attempt",
            "printf '%s\\n' \"$?\"",
        )
    )
    result = _run_bash_script(tmp_path / "rollback-terminal.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == expected_status
    assert not restored.exists()
    assert removed.exists() is expected_removed
    assert journal.is_file() is journal_present


def test_live_recovery_umount_fsync_failure_retries_from_mount_absence(
    tmp_path: Path,
):
    result, release, old_root, journal, log, failed = (
        _run_live_post_bind_runtime_reconciliation(
            tmp_path,
            "persistent-restored",
            True,
            fail_fsync_once=True,
            retry_after_failure=True,
        )
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.splitlines() == [
        "1|recovery-detach-persistent-armed|1",
        "0|0",
    ]
    lines = log.read_text(encoding="ascii").splitlines()
    assert lines.count("umount") == 1
    assert lines.index("journal:recovery-detach-persistent-armed") < lines.index(
        "umount"
    ) < lines.index("fsync-fail") < lines.index(
        "journal:recovery-remove-release-root-armed"
    )
    assert lines.index("mount") < lines.index("clear")
    assert failed.is_file()
    assert (release / "old-marker").is_file()
    assert not (release / "new-marker").exists()
    assert not old_root.exists()
    assert not journal.exists()


@pytest.mark.parametrize("post_probe", ("absent", "present", "unknown", "invalid"))
def test_primary_live_umount_requires_verified_absence_before_detached_flags(
    tmp_path: Path, post_probe: str
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    primary = source[
        source.index("# detach-agent-data") : source.index("# swap-release-root")
    ]
    current_data = tmp_path / "release" / "agent" / "data"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    current_data.mkdir(parents=True)
    persistent.mkdir()
    evidence.mkdir()
    log = tmp_path / "detach.log"
    script = "\n".join(
        (
            "set -Eeuo pipefail",
            "LOCAL_REHEARSAL=false",
            f"CURRENT_DATA={shlex.quote(_bash_path(current_data))}",
            f"PERSISTENT_AGENT_DATA_ROOT={shlex.quote(_bash_path(persistent))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            "PERSISTENT_ATTACHED_TO_RELEASE=true",
            "PERSISTENT_DETACHED=false",
            "PERSISTENT_MOUNT_STATE_UNKNOWN=false",
            "MOUNT_STATE=0",
            f"POST_PROBE={shlex.quote(post_probe)}",
            "MUTATION_STARTED=false",
            "INSTALL_FAILURE_POINT=",
            f"DETACH_LOG={shlex.quote(_bash_path(log))}",
            "write_mutation_state() { printf 'journal:%s\\n' \"$1\" >> \"$DETACH_LOG\"; }",
            "verify_findmnt_file() { ! grep -Fq enclosing-filesystem \"$1\" && [ \"$MOUNT_STATE\" != 3 ]; }",
            "invoke_mount_authority() {",
            "  case \"$1\" in",
            "    findmnt)",
            "      [ \"$2\" = --json ] && [ \"$4\" = \"$CURRENT_DATA\" ] || return 64",
            "      printf 'findmnt:%s\\n' \"$3\" >> \"$DETACH_LOG\"",
            "      if [ \"$3\" = --target ] && [ \"$MOUNT_STATE\" = 1 ]; then",
            "        printf '{\"filesystems\":[{\"target\":\"/\",\"source\":\"enclosing-filesystem\",\"options\":\"rw\"}]}\\n'",
            "        return 0",
            "      fi",
            "      [ \"$3\" = --mountpoint ] || [ \"$3\" = --target ] || return 64",
            "      case \"$MOUNT_STATE\" in",
            "        0) printf '{}\\n'; return 0 ;;",
            "        1) return 1 ;;",
            "        3) printf '{}\\n'; return 0 ;;",
            "        *) return 72 ;;",
            "      esac",
            "      ;;",
            "    umount)",
            "      [ \"$2\" = \"$CURRENT_DATA\" ] || return 64",
            "      printf 'umount\\n' >> \"$DETACH_LOG\"",
            "      case \"$POST_PROBE\" in",
            "        absent) MOUNT_STATE=1 ;;",
            "        present) MOUNT_STATE=0 ;;",
            "        unknown) MOUNT_STATE=2 ;;",
            "        invalid) MOUNT_STATE=3 ;;",
            "      esac",
            "      return 0",
            "      ;;",
            "    *) return 64 ;;",
            "  esac",
            "}",
            "fsync_directories() {",
            "  [ \"$1\" = \"$CURRENT_DATA\" ] && [ \"$2\" = \"$(dirname -- \"$CURRENT_DATA\")\" ] || return 64",
            "  printf 'fsync\\n' >> \"$DETACH_LOG\"",
            "  return 71",
            "}",
            "fail_after() { return 0; }",
            "report_state() {",
            "  status=$?",
            "  trap - EXIT",
            "  printf '%s|%s|%s|%s\\n' \"$status\" \"$PERSISTENT_ATTACHED_TO_RELEASE\" \"$PERSISTENT_DETACHED\" \"$PERSISTENT_MOUNT_STATE_UNKNOWN\"",
            "  exit \"$status\"",
            "}",
            "trap report_state EXIT",
            primary,
        )
    )

    result = _run_bash_script(tmp_path / "primary-detach.sh", script)

    lines = log.read_text(encoding="ascii").splitlines()
    expected_prefix = [
        "journal:detach-agent-data-armed",
        "findmnt:--mountpoint",
        "umount",
        "findmnt:--mountpoint",
    ]
    if post_probe == "present":
        assert result.returncode == 1, result.stderr + result.stdout
        assert result.stdout.strip() == "1|true|false|false"
        assert lines == expected_prefix
    elif post_probe == "unknown":
        assert result.returncode == 72, result.stderr + result.stdout
        assert result.stdout.strip() == "72|true|false|true"
        assert lines == expected_prefix
    elif post_probe == "invalid":
        assert result.returncode == 1, result.stderr + result.stdout
        assert result.stdout.strip() == "1|true|false|true"
        assert lines == expected_prefix
    else:
        assert result.returncode == 71, result.stderr + result.stdout
        assert result.stdout.strip() == "71|false|true|false"
        assert lines == [*expected_prefix, "fsync"]


@pytest.mark.parametrize("post_probe", ("absent", "present", "unknown", "invalid"))
def test_recovery_umount_requires_verified_absence_before_detached_flags(
    tmp_path: Path, post_probe: str
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    helper = source[
        source.index("inspect_current_mount()") : source.index(
            "attach_persistent_to_release_for_recovery()"
        )
    ]
    log = tmp_path / "detach.log"
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    script = "\n".join(
        (
            "set -u",
            "LOCAL_REHEARSAL=false",
            "RELEASE_ROOT=/release",
            "PERSISTENT_AGENT_DATA_ROOT=/persistent",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            "PERSISTENT_ATTACHED_TO_RELEASE=true",
            "PERSISTENT_DETACHED=false",
            "PERSISTENT_MOUNT_STATE_UNKNOWN=false",
            "MOUNT_STATE=0",
            f"POST_PROBE={shlex.quote(post_probe)}",
            f"DETACH_LOG={shlex.quote(_bash_path(log))}",
            "write_mutation_state() { printf 'journal:%s\\n' \"$1\" >> \"$DETACH_LOG\"; }",
            "verify_findmnt_file() { [ \"$MOUNT_STATE\" != 3 ]; }",
            "invoke_mount_authority() {",
            "  case \"$1\" in",
            "    findmnt)",
            "      [ \"$2\" = --json ] && [ \"$3\" = --mountpoint ] && [ \"$4\" = \"$RELEASE_ROOT/agent/data\" ] || return 64",
            "      printf 'findmnt\\n' >> \"$DETACH_LOG\"",
            "      case \"$MOUNT_STATE\" in",
            "        0) printf '{}\\n'; return 0 ;;",
            "        1) return 1 ;;",
            "        3) printf '{}\\n'; return 0 ;;",
            "        *) return 72 ;;",
            "      esac",
            "      ;;",
            "    umount)",
            "      [ \"$2\" = \"$RELEASE_ROOT/agent/data\" ] || return 64",
            "      printf 'umount\\n' >> \"$DETACH_LOG\"",
            "      case \"$POST_PROBE\" in",
            "        absent) MOUNT_STATE=1 ;;",
            "        present) MOUNT_STATE=0 ;;",
            "        unknown) MOUNT_STATE=2 ;;",
            "        invalid) MOUNT_STATE=3 ;;",
            "      esac",
            "      return 0",
            "      ;;",
            "    *) return 64 ;;",
            "  esac",
            "}",
            "fsync_directories() { printf 'fsync\\n' >> \"$DETACH_LOG\"; return 71; }",
            helper,
            "set +e",
            "detach_persistent_from_release_for_recovery",
            "status=$?",
            "set -e",
            "printf '%s|%s|%s|%s\\n' \"$status\" \"$PERSISTENT_ATTACHED_TO_RELEASE\" \"$PERSISTENT_DETACHED\" \"$PERSISTENT_MOUNT_STATE_UNKNOWN\"",
        )
    )

    result = _run_bash_script(tmp_path / "rollback.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    state = result.stdout.strip().split("|")
    lines = log.read_text(encoding="ascii").splitlines()
    expected_prefix = [
        "findmnt",
        "journal:recovery-detach-persistent-armed",
        "umount",
        "findmnt",
    ]
    if post_probe == "present":
        assert state == ["1", "true", "false", "false"]
        assert lines == expected_prefix
    elif post_probe in ("unknown", "invalid"):
        assert state == ["2", "true", "false", "true"]
        assert lines == expected_prefix
    else:
        assert state == ["71", "false", "true", "false"]
        assert lines == [*expected_prefix, "fsync"]


def test_live_bind_side_effect_then_nonzero_is_unmounted_before_root_rollback(
    tmp_path: Path,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    recovery = source[source.index("inspect_current_mount()") : source.index("fail_after()")]
    restore = source[
        source.index("# restore-bind-agent-data") : source.index(
            "# verify-agent-data-mount"
        )
    ]
    release = tmp_path / "release"
    old_root = tmp_path / ".release.closed-old.777"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    for directory in (
        release / "agent",
        old_root / "agent" / "data",
        persistent,
        evidence,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    (release / "new-marker").write_text("new\n", encoding="ascii")
    (old_root / "old-marker").write_text("old\n", encoding="ascii")
    (persistent / "app.db").write_text("persistent\n", encoding="ascii")
    journal = evidence / "install-mutation-state.json"
    mounted = tmp_path / "mounted"
    log = tmp_path / "rollback.log"
    snapshot = evidence / "persistent-before.json"
    snapshot.write_text("{}\n", encoding="ascii")
    recovery_snapshot = evidence / "persistent-recovery.json"
    script = "\n".join(
        (
            "set -Eeuo pipefail",
            "LOCAL_REHEARSAL=false",
            f"RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"OLD_ROOT={shlex.quote(_bash_path(old_root))}",
            f"PERSISTENT_AGENT_DATA_ROOT={shlex.quote(_bash_path(persistent))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"SNAPSHOT_BEFORE={shlex.quote(_bash_path(snapshot))}",
            f"SNAPSHOT_RECOVERY={shlex.quote(_bash_path(recovery_snapshot))}",
            f"RELEASE_PARENT={shlex.quote(_bash_path(tmp_path))}",
            "STAGING_ROOT=/nonexistent-staging",
            "RELEASE_NAME=release",
            "ATTEMPT_ID=777",
            "CANDIDATE_RELEASE_ROOT_IDENTITY=3:4",
            "CANDIDATE_RELEASE_TOPOLOGY_SHA256=candidate-topology-digest",
            "CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT=/candidate-topology",
            "SOURCE_RELEASE_ROOT_IDENTITY=1:2",
            "SOURCE_RELEASE_TOPOLOGY_SNAPSHOT=/source-topology",
            "CANDIDATE_MANIFEST_SHA256=candidate-manifest-digest",
            f"CANDIDATE_CLEANUP_ROOT={shlex.quote(_bash_path(tmp_path / '.release.closed-candidate-cleanup.777'))}",
            f"CANDIDATE_CLEANUP_OWNER={shlex.quote(_bash_path(tmp_path / '.release.closed-candidate-cleanup.777.owner'))}",
            "STAGING_DELETE_ROOT=/nonexistent-staging-delete",
            "STAGING_DELETE_OWNER=/nonexistent-staging-delete.owner",
            "STAGING_OWNER_MARKER=/nonexistent-staging-owner",
            "STAGING_CLEANUP_ARMED=false",
            "UNIT_ATTEMPT_ROOT=",
            "UNIT_MUTATION_MARKER=",
            "INSTALL_COMPLETE=false",
            "INSTALL_COMMITTED=false",
            "MUTATION_STARTED=true",
            "OLD_ROOT_READY=true",
            "PERSISTENT_ATTACHED_TO_RELEASE=false",
            "PERSISTENT_DETACHED=true",
            "PERSISTENT_MOUNT_STATE_UNKNOWN=false",
            "INSTALL_FAILURE_POINT=restore-bind-agent-data",
            f"MOUNTED_MARKER={shlex.quote(_bash_path(mounted))}",
            f"ROLLBACK_LOG={shlex.quote(_bash_path(log))}",
            "MOUNT_CALLS=0",
            "write_mutation_state() { printf '%s\\n' \"$1\" > \"$MUTATION_STATE\"; printf 'journal:%s\\n' \"$1\" >> \"$ROLLBACK_LOG\"; }",
            "clear_mutation_state() { /usr/bin/rm -f -- \"$MUTATION_STATE\"; printf 'clear\\n' >> \"$ROLLBACK_LOG\"; }",
            "write_recovery_evidence() { return 0; }",
            "cleanup_attempt_authorities() { return 0; }",
            "remove_systemd_unit_attempt() { return 0; }",
            "restore_systemd_units() { return 0; }",
            "verify_findmnt_file() { return 0; }",
            "tree_matches_bound_topology() { return 0; }",
            "regular_file_sha256() { printf '%s\\n' \"$CANDIDATE_MANIFEST_SHA256\"; }",
            "write_cleanup_owner_marker() { : > \"$1\"; return 0; }",
            "verify_cleanup_owner_marker() { return 0; }",
            "remove_file_durably() { /usr/bin/rm -f -- \"$1\"; }",
            "invoke_rm() { printf 'rm-release\\n' >> \"$ROLLBACK_LOG\"; /usr/bin/rm \"$@\"; }",
            "snapshot_tree() { /usr/bin/cp -- \"$SNAPSHOT_BEFORE\" \"$2\"; }",
            "fsync_directories() { return 0; }",
            "invoke_mount_authority() {",
            "  case \"$1\" in",
            "    findmnt) [ -f \"$MOUNTED_MARKER\" ] || return 1; printf '{}\\n'; return 0 ;;",
            "    umount) printf 'umount\\n' >> \"$ROLLBACK_LOG\"; /usr/bin/rm -f -- \"$MOUNTED_MARKER\"; find \"$2\" -mindepth 1 -maxdepth 1 -exec /usr/bin/rm -rf -- {} +; return 0 ;;",
            "    mount) MOUNT_CALLS=$((MOUNT_CALLS + 1)); printf 'mount:%s:unknown=%s\\n' \"$MOUNT_CALLS\" \"$PERSISTENT_MOUNT_STATE_UNKNOWN\" >> \"$ROLLBACK_LOG\"; /usr/bin/cp -a -- \"$3\"/. \"$4\"/; : > \"$MOUNTED_MARKER\"; [ \"$MOUNT_CALLS\" -ne 1 ] || return 52; return 0 ;;",
            "    *) return 64 ;;",
            "  esac",
            "}",
            "rm() { for argument in \"$@\"; do [ \"$argument\" != \"$RELEASE_ROOT\" ] || printf 'rm-release\\n' >> \"$ROLLBACK_LOG\"; done; /usr/bin/rm \"$@\"; }",
            "mv() { [ \"${1:-}\" != -- ] || shift; if [ \"${1:-}\" = \"$OLD_ROOT\" ] && [ \"${2:-}\" = \"$RELEASE_ROOT\" ]; then printf 'restore-old\\n' >> \"$ROLLBACK_LOG\"; fi; /usr/bin/mv \"$@\"; }",
            recovery,
            restore,
        )
    )

    result = _run_bash_script(tmp_path / "rollback.sh", script)

    assert result.returncode == 52, result.stderr + result.stdout
    lines = log.read_text(encoding="ascii").splitlines()
    assert lines.index("mount:1:unknown=true") < lines.index(
        "journal:recovery-detach-persistent-armed"
    ) < lines.index("umount") < lines.index("rm-release")
    assert lines.index("rm-release") < lines.index("mount:2:unknown=true") < lines.index(
        "journal:rollback-restored"
    ) < lines.index("clear")
    assert (release / "old-marker").is_file()
    assert (release / "agent" / "data" / "app.db").is_file()
    assert not (release / "new-marker").exists()
    assert not old_root.exists()
    assert not journal.exists()
    assert mounted.is_file()


def test_sigkill_before_systemd_journal_leaves_attempt_journal_bound(
    tmp_path: Path, closed_package
):
    case_root = tmp_path / "systemd-prejournal-sigkill"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    unit_root = case_root / "runtime" / "systemd-units"
    unit_root.mkdir()
    for name in SYSTEMD_UNIT_NAMES:
        (unit_root / name).write_bytes(f"legacy-{name}\n".encode())

    reached = case_root / "prejournal"
    python_executor = _write_local_python_executor(
        case_root / "prejournal-python",
        '  if [ "$1" = "-" ] && [ "${3:-}" = "systemd-units-armed" ]; then\n'
        f"    : > '{_bash_path(reached)}'\n"
        '    kill -9 "$5"\n'
        '    kill -9 "$$"\n'
        '  fi\n'
        'command "$REAL_PYTHON" "$@"\n',
    )

    result = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)},
    )

    assert result.returncode != 0
    attempt = next(evidence.glob(".systemd-unit-attempt.*"))
    assert (attempt / "armed").is_file()
    journal = json.loads(
        (evidence / "install-mutation-state.json").read_text(encoding="utf-8")
    )
    assert journal["stage"] == "systemd-backup-preparing"
    assert journal["systemd_unit_attempt_root"] == _bash_path(attempt)


def test_partial_systemd_restore_keeps_armed_material_for_retry(
    tmp_path: Path, closed_package
):
    case_root = tmp_path / "partial-systemd-restore"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    unit_root = case_root / "runtime" / "systemd-units"
    unit_root.mkdir()
    for name in SYSTEMD_UNIT_NAMES:
        (unit_root / name).write_bytes(f"legacy-{name}\n".encode())
    legacy = _snapshot_tree(unit_root)

    used = case_root / "restore-failed"
    python_executor = _write_local_python_executor(
        case_root / "restore-failed-python",
        '  case "${3:-}" in\n'
        "    */.systemd-unit-attempt.*/backup)\n"
        f"      if [ ! -f '{_bash_path(used)}' ]; then\n"
        f"        : > '{_bash_path(used)}'\n"
        '        printf partial > "$2/vl-agent.service"\n'
        "        exit 62\n"
        "      fi\n"
        "      ;;\n"
        "  esac\n"
        'command "$REAL_PYTHON" "$@"\n',
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="units",
        env_overrides={"VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)},
    )

    assert first.returncode == 19
    attempt = next(evidence.glob(".systemd-unit-attempt.*"))
    assert (attempt / "armed").is_file()
    assert (attempt / "backup" / "metadata.json").is_file()
    assert (evidence / "install-mutation-state.json").is_file()
    assert _snapshot_tree(unit_root) != legacy

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )
    assert retry.returncode == 19
    assert _snapshot_tree(unit_root) == legacy
    assert not (evidence / "install-mutation-state.json").exists()
    assert _unit_attempt_artifacts(evidence) == []


def test_false_success_rollback_cleanup_retains_journal_until_verified(
    tmp_path: Path, closed_package
):
    case_root = tmp_path / "rollback-cleanup-false-success"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared

    used = case_root / "fake-success"
    bash_env = case_root / "fake-success.bash"
    bash_env.write_text(
        "rm() {\n"
        '  for argument in "$@"; do\n'
        '    case "$(basename -- "$argument")" in\n'
        "      .systemd-unit-attempt.*)\n"
        f"        if [ ! -f '{_bash_path(used)}' ]; then\n"
        f"          : > '{_bash_path(used)}'\n"
        "          return 0\n"
        "        fi\n"
        "        ;;\n"
        "    esac\n"
        "  done\n"
        '  /usr/bin/rm "$@"\n'
        "}\n",
        encoding="ascii",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="units",
        env_overrides={"BASH_ENV": _bash_path(bash_env)},
    )

    assert first.returncode == 19
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text())["stage"] == (
        "recovery-remove-systemd-attempt-armed"
    )
    assert len(list(evidence.glob(".systemd-unit-attempt.*"))) == 1

    retry = _invoke_installer(
        closed_package, case_root, prepared, failed_hook="python"
    )
    assert retry.returncode == 19
    assert not journal.exists()
    assert _unit_attempt_artifacts(evidence) == []


def test_sigkill_after_systemd_mutation_restores_original_units_before_retry(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "sigkill-systemd-units"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    journal, _, unit_destination, legacy_units = _interrupt_after_systemd_mutation(
        closed_package, case_root, prepared
    )
    unit_hook = case_root / "runtime" / "units-hook.sh"
    unit_hook.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s|%s\\n' 'systemd-units' \"$*\" >> \"$INSTALL_HOOK_LOG\"\n",
        encoding="ascii",
    )
    unit_hook.chmod(0o755)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent
    assert _snapshot_tree(unit_destination) == legacy_units
    assert not journal.exists()
    assert _unit_attempt_artifacts(evidence) == []


def test_systemd_stale_recovery_rejects_different_runtime_without_reset(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "systemd-runtime-mismatch"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, _, _, _, _, values = prepared
    journal, attempt, unit_destination, _ = _interrupt_after_systemd_mutation(
        closed_package, case_root, prepared
    )
    journal_before = journal.read_bytes()
    attempt_before = _snapshot_tree(attempt)
    release_before = _snapshot_tree(release)
    persistent_before = _snapshot_tree(persistent)
    units_before = _snapshot_tree(unit_destination)
    different_runtime = case_root / "different-runtime"
    different_runtime.mkdir()
    env = os.environ.copy()
    env.update(values)

    retry = subprocess.run(
        _installer_command(
            closed_package,
            case_root,
            prepared,
            runtime_arg=_bash_path(different_runtime),
        ),
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert journal.read_bytes() == journal_before
    assert _snapshot_tree(attempt) == attempt_before
    assert _snapshot_tree(release) == release_before
    assert _snapshot_tree(persistent) == persistent_before
    assert _snapshot_tree(unit_destination) == units_before


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

    assert first.returncode == 61, first.stderr + first.stdout
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
    attempts = list(evidence.glob(".systemd-unit-attempt.*"))
    assert len(attempts) == 1
    assert (attempts[0] / "armed").is_file()
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "committed-cleanup"
    )

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
    assert not journal.exists()
    assert _unit_attempt_artifacts(evidence) == []
    lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "released"


def test_systemd_cleanup_recorder_failure_surfaces_and_retry_records_durably(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "systemd-cleanup-recorder-failure"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, _, _ = prepared
    cleanup_failure_used = case_root / "cleanup-failure-used"
    recorder_failure_used = case_root / "recorder-failure-used"
    bash_env = case_root / "cleanup-failure.bash"
    bash_env.write_text(
        "rm() {\n"
        "  for argument in \"$@\"; do\n"
        "    case \"$(basename -- \"$argument\")\" in\n"
        "      .systemd-unit-attempt.*)\n"
        f"        if [ ! -f '{_bash_path(cleanup_failure_used)}' ]; then\n"
        f"          : > '{_bash_path(cleanup_failure_used)}'\n"
        "          return 61\n"
        "        fi\n"
        "        ;;\n"
        "    esac\n"
        "  done\n"
        "  /usr/bin/rm \"$@\"\n"
        "}\n",
        encoding="ascii",
    )
    cleanup_evidence_path = _bash_path(evidence / "systemd-unit-cleanup.json")
    python_executor = _write_local_python_executor(
        case_root / "cleanup-recorder-python",
        f"if [ \"${{1:-}}\" = - ] "
        f"&& [ \"${{2:-}}\" = '{cleanup_evidence_path}' ] "
        f"&& [ ! -f '{_bash_path(recorder_failure_used)}' ]; then\n"
        f"  : > '{_bash_path(recorder_failure_used)}'\n"
        "  exit 71\n"
        "fi\n"
        'command "$REAL_PYTHON" "$@"\n',
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor),
        },
    )

    assert first.returncode == 61, first.stderr + first.stdout
    assert "systemd-unit-cleanup-record-failed:71" in first.stderr
    assert cleanup_failure_used.is_file()
    assert recorder_failure_used.is_file()
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "committed-cleanup"
    )
    assert not (evidence / "systemd-unit-cleanup.json").exists()
    assert len(list(evidence.glob(".systemd-unit-attempt.*"))) == 1
    installed_release = _snapshot_tree(release)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor),
        },
    )

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert _snapshot_tree(release) == installed_release
    assert not journal.exists()
    assert _unit_attempt_artifacts(evidence) == []
    assert not list(release.parent.glob(f".{release.name}.closed-retired-cleanup.*"))
    cleanup = json.loads(
        (evidence / "systemd-unit-cleanup.json").read_text(encoding="utf-8")
    )
    assert cleanup["status"] == "passed"
    assert cleanup["exit_code"] == 0


def test_false_success_systemd_cleanup_remains_nonzero_and_recoverable(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "systemd-cleanup-false-success"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, _, _ = prepared
    fake_success_used = case_root / "cleanup-fake-success-used"
    bash_env = case_root / "cleanup-fake-success.bash"
    bash_env.write_text(
        "rm() {\n"
        "for argument in \"$@\"; do\n"
        "  case \"$(basename -- \"$argument\")\" in\n"
        "    .systemd-unit-attempt.*)\n"
        f"      if [ ! -f '{_bash_path(fake_success_used)}' ]; then\n"
        f"        : > '{_bash_path(fake_success_used)}'\n"
        "        return 0\n"
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

    assert first.returncode != 0, first.stderr + first.stdout
    assert fake_success_used.is_file()
    assert (release / "launch-release-manifest.json").is_file()
    attempts = list(evidence.glob(".systemd-unit-attempt.*"))
    assert len(attempts) == 1
    assert (attempts[0] / "backup" / "metadata.json").is_file()
    journal = evidence / "install-mutation-state.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == "committed-cleanup"
    cleanup = json.loads(
        (evidence / "systemd-unit-cleanup.json").read_text(encoding="utf-8")
    )
    assert cleanup["status"] == "failed"
    assert cleanup["exit_code"] != 0

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert second.returncode == 19, second.stderr + second.stdout
    assert not journal.exists()
    assert _unit_attempt_artifacts(evidence) == []


def test_stale_committed_candidate_tamper_preserves_retired_root_and_journal(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "committed-candidate-tamper"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, values = prepared
    journal = _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "committed-cleanup"
    )
    retired_roots = list(release.parent.glob(f".{release.name}.closed-retired.*"))
    assert len(retired_roots) == 1
    retired = retired_roots[0]
    unit_destination = case_root / "runtime" / "systemd-units"
    hook_log = Path(values["INSTALL_HOOK_LOG"].replace("/", os.sep))
    if os.name == "nt":
        hook_log = case_root / "runtime" / "hooks.log"
    journal_before = journal.read_bytes()
    retired_before = _snapshot_topology(retired)
    persistent_before = _snapshot_topology(persistent)
    units_before = _snapshot_topology(unit_destination)
    hook_log_before = hook_log.read_bytes()
    tampered = release / "web-nuxt" / "package.json"
    tampered.write_bytes(b'{"tampered":true}\n')
    tampered_before = tampered.read_bytes()
    release_before = _snapshot_topology(release)

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert retry.returncode == 2, retry.stderr + retry.stdout
    assert "stale-install-recovery-required" in retry.stderr
    assert journal.read_bytes() == journal_before
    assert _snapshot_topology(retired) == retired_before
    assert _snapshot_topology(release) == release_before
    assert tampered.read_bytes() == tampered_before
    assert _snapshot_topology(persistent) == persistent_before
    assert _snapshot_topology(unit_destination) == units_before
    assert hook_log.read_bytes() == hook_log_before


def test_stale_committed_retired_tree_tamper_is_preserved_until_restored(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "committed-retired-tamper"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, _, _, _, values = prepared
    journal = _interrupt_at_journal_stage(
        closed_package, case_root, prepared, "committed-cleanup"
    )
    retired = next(release.parent.glob(f".{release.name}.closed-retired.*"))
    retired_backup = case_root / "retired-authority-backup"
    retired.rename(retired_backup)
    unit_destination = case_root / "runtime" / "systemd-units"
    hook_log = Path(values["INSTALL_HOOK_LOG"].replace("/", os.sep))
    if os.name == "nt":
        hook_log = case_root / "runtime" / "hooks.log"
    journal_before = journal.read_bytes()
    release_before = _snapshot_topology(release)
    persistent_before = _snapshot_topology(persistent)
    units_before = _snapshot_topology(unit_destination)
    hook_log_before = hook_log.read_bytes()
    retired.mkdir()
    (retired / "foreign-release-marker.txt").write_bytes(b"must-survive\n")
    tampered_retired = _snapshot_topology(retired)

    blocked = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert blocked.returncode == 2, blocked.stderr + blocked.stdout
    assert "stale-install-recovery-required" in blocked.stderr
    assert journal.read_bytes() == journal_before
    assert _snapshot_topology(retired) == tampered_retired
    assert _snapshot_topology(release) == release_before
    assert _snapshot_topology(persistent) == persistent_before
    assert _snapshot_topology(unit_destination) == units_before
    assert hook_log.read_bytes() == hook_log_before

    shutil.rmtree(retired)
    retired_backup.rename(retired)
    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    assert not journal.exists()


def test_primary_and_stale_committed_paths_share_full_installed_verifier():
    source = INSTALL.read_text(encoding="utf-8")
    helper_start = source.index("verify_installed_release_authority()")
    helper_end = source.index("\n}\n", helper_start) + 3
    helper = source[helper_start:helper_end]
    for flag in (
        "--verify-config-ingress-unit-digests",
        "--verify-persistent-agent-data-mount",
        "--verify-systemd-unit-destination",
        "--verify-environment-authority",
        "--require-closed",
    ):
        assert flag in helper
    stale = source[
        source.index('  if [ "$committed_recovery" = true ]; then') : source.index(
            "  local stage_owner_valid=false"
        )
    ]
    assert "verify_installed_release_authority" in stale
    assert stale.index("verify_installed_release_authority") < stale.index(
        "invoke_pinned_executable unit-verify"
    )
    primary_call = source.rindex("verify_installed_release_authority")
    assert primary_call < source.index("write_mutation_state retire-old-root-armed")


@pytest.mark.parametrize("local_rehearsal", (True, False))
def test_installed_verifier_helper_executes_exact_cli_contract(
    tmp_path: Path, local_rehearsal: bool
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index("verify_installed_release_authority()")
    helper = source[start : source.index("\n}\n", start) + 3]
    log = tmp_path / "verifier-argv.bin"
    installed = tmp_path / "release"
    persistent = tmp_path / "persistent"
    systemd = tmp_path / "systemd"
    evidence = tmp_path / "installed-evidence"
    mount_evidence = tmp_path / "findmnt.json"
    environment = tmp_path / "external.env"
    script = "\n".join(
        (
            "set -eu",
            f"VERIFY_SCRIPT={shlex.quote(_bash_path(VERIFY))}",
            f"PINNED_ENVIRONMENT_AUTHORITY={shlex.quote(_bash_path(environment))}",
            f"ARGV_LOG={shlex.quote(_bash_path(log))}",
            "invoke_python() { printf '%s\\0' \"$@\" > \"$ARGV_LOG\"; }",
            helper,
            "verify_installed_release_authority "
            f"{shlex.quote(_bash_path(installed))} "
            f"{shlex.quote(_bash_path(persistent))} "
            f"{shlex.quote(_bash_path(systemd))} "
            f"{shlex.quote(_bash_path(evidence))} "
            f"{shlex.quote(_bash_path(mount_evidence))} "
            f"{'true' if local_rehearsal else 'false'}",
        )
    )

    result = _run_bash_script(tmp_path / "verify-installed-helper.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    observed = [item.decode() for item in log.read_bytes().split(b"\0") if item]
    expected = [
        _bash_path(VERIFY),
        "--installed-root",
        _bash_path(installed),
        "--persistent-agent-data-root",
        _bash_path(persistent),
        "--verify-config-ingress-unit-digests",
        "--verify-persistent-agent-data-mount",
        "--systemd-unit-root",
        _bash_path(systemd),
        "--verify-systemd-unit-destination",
        "--environment-authority",
        _bash_path(environment),
        "--verify-environment-authority",
    ]
    if local_rehearsal:
        expected.append("--local-rehearsal")
    else:
        expected.extend(
            ["--persistent-mount-evidence", _bash_path(mount_evidence)]
        )
    expected.extend(["--require-closed", "--evidence-dir", _bash_path(evidence)])
    assert observed == expected


@pytest.mark.parametrize(
    ("schema_version", "committed", "tamper", "expected_status"),
    (
    (4, True, "manifest", 1),
    (4, True, "environment", 1),
    (4, True, "snapshot", 1),
    (4, False, "candidate-snapshot", 1),
    (4, False, "manifest", 1),
    (4, False, "environment", 0),
        (3, True, "none", 1),
        (3, False, "none", 1),
    ),
)
def test_stale_journal_binding_policy_is_behavioral(
    tmp_path: Path,
    schema_version: int,
    committed: bool,
    tamper: str,
    expected_status: int,
):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    digest_start = source.index("regular_file_sha256()")
    digest = source[digest_start : source.index("\n}\n", digest_start) + 3]
    binding_start = source.index("verify_stale_journal_bindings()")
    binding = source[
        binding_start : source.index("\n}\n", binding_start) + 3
    ]
    release = tmp_path / "release"
    release.mkdir()
    manifest = release / "launch-release-manifest.json"
    manifest.write_bytes(b"manifest-v1\n")
    environment = tmp_path / "external.env"
    environment.write_bytes(b"environment-v1\n")
    snapshot = tmp_path / "persistent-before.json"
    snapshot.write_bytes(b"snapshot-v1\n")
    source_topology = tmp_path / "source-release-topology.json"
    source_topology.write_bytes(b"source-topology-v1\n")
    candidate_topology = tmp_path / "candidate-release-topology.json"
    candidate_topology.write_bytes(b"candidate-topology-v1\n")
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    environment_sha = hashlib.sha256(environment.read_bytes()).hexdigest()
    snapshot_sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    source_topology_sha = hashlib.sha256(source_topology.read_bytes()).hexdigest()
    candidate_topology_sha = hashlib.sha256(candidate_topology.read_bytes()).hexdigest()
    if tamper == "manifest":
        manifest.write_bytes(b"manifest-v2\n")
    elif tamper == "environment":
        environment.write_bytes(b"environment-v2\n")
    elif tamper == "snapshot":
        snapshot.write_bytes(b"snapshot-v2\n")
    elif tamper == "candidate-snapshot":
        candidate_topology.write_bytes(b"candidate-topology-v2\n")
    script = "\n".join(
        (
            "set -u",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { command "$PYTHON_EXECUTOR" "$@"; }',
            digest,
            binding,
            f"STALE_SCHEMA_VERSION={schema_version}",
            f"STALE_RELEASE_ROOT={shlex.quote(_bash_path(release))}",
            f"PINNED_ENVIRONMENT_AUTHORITY={shlex.quote(_bash_path(environment))}",
            f"SNAPSHOT_BEFORE={shlex.quote(_bash_path(snapshot))}",
            f"SOURCE_RELEASE_TOPOLOGY_SNAPSHOT={shlex.quote(_bash_path(source_topology))}",
            f"CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT={shlex.quote(_bash_path(candidate_topology))}",
            f"STALE_CANDIDATE_MANIFEST_SHA256={manifest_sha}",
            f"STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256={candidate_topology_sha}",
            f"STALE_ENVIRONMENT_AUTHORITY_SHA256={environment_sha}",
            f"STALE_PERSISTENT_SNAPSHOT_SHA256={snapshot_sha}",
            f"STALE_SOURCE_RELEASE_TOPOLOGY_SHA256={source_topology_sha}",
            f"ENVIRONMENT_AUTHORITY_SHA256={hashlib.sha256(environment.read_bytes()).hexdigest()}",
            f"verify_stale_journal_bindings {'true' if committed else 'false'} \"$STALE_RELEASE_ROOT\"",
        )
    )

    result = _run_bash_script(tmp_path / "stale-binding.sh", script)

    assert result.returncode == expected_status, result.stderr + result.stdout


def test_schema4_journal_binds_committed_verifier_authorities():
    source = INSTALL.read_text(encoding="utf-8")
    for field in (
        '"candidate_manifest_sha256"',
        '"candidate_release_root_identity"',
        '"candidate_release_topology_sha256"',
        '"environment_authority_sha256"',
        '"persistent_snapshot_sha256"',
        '"source_release_root_identity"',
        '"source_release_topology_sha256"',
    ):
        assert source.count(field) >= 3
    assert '"schema_version": 4' in source


def test_topology_subset_uses_same_agent_data_exclusion_as_snapshot(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    payload_start = source.index("source_release_topology_payload()")
    payload = source[
        payload_start : source.index("source_release_topology_sha256()", payload_start)
    ]
    subset_start = source.index("source_release_topology_subset()")
    subset = source[
        subset_start : source.index("write_durable_atomic_json()", subset_start)
    ]
    release = tmp_path / "release"
    data = release / "agent" / "data"
    data.mkdir(parents=True)
    (release / "tracked.txt").write_bytes(b"tracked\n")
    (data / "mutable.db").write_bytes(b"before\n")
    snapshot = tmp_path / "topology.json"
    script = "\n".join(
        (
            "set -u",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { command "$PYTHON_EXECUTOR" "$@"; }',
            payload,
            subset,
            f"ROOT={shlex.quote(_bash_path(release))}",
            f"SNAPSHOT={shlex.quote(_bash_path(snapshot))}",
            'source_release_topology_payload "$ROOT" > "$SNAPSHOT"',
            f"printf 'after\\n' > {shlex.quote(_bash_path(data / 'mutable.db'))}",
            'source_release_topology_subset "$ROOT" "$SNAPSHOT"',
        )
    )

    result = _run_bash_script(tmp_path / "topology-agent-data-subset.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout


def test_topology_subset_authenticates_the_root_entry(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    payload_start = source.index("source_release_topology_payload()")
    payload = source[
        payload_start : source.index("source_release_topology_sha256()", payload_start)
    ]
    subset_start = source.index("source_release_topology_subset()")
    subset = source[
        subset_start : source.index("write_durable_atomic_json()", subset_start)
    ]
    release = tmp_path / "release"
    release.mkdir(mode=0o755)
    (release / "tracked.txt").write_bytes(b"tracked\n")
    snapshot = tmp_path / "topology.json"
    script = "\n".join(
        (
            "set -u",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { command "$PYTHON_EXECUTOR" "$@"; }',
            payload,
            subset,
            f"ROOT={shlex.quote(_bash_path(release))}",
            f"SNAPSHOT={shlex.quote(_bash_path(snapshot))}",
            'source_release_topology_payload "$ROOT" > "$SNAPSHOT"',
            'invoke_python -c \'import json,sys; path=sys.argv[1]; entries=json.load(open(path, encoding="utf-8")); json.dump([entry for entry in entries if entry[0] != "."], open(path, "w", encoding="utf-8"))\' "$SNAPSHOT"',
            'if source_release_topology_subset "$ROOT" "$SNAPSHOT"; then exit 91; fi',
        )
    )

    result = _run_bash_script(tmp_path / "topology-root-subset.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout


def test_tree_root_identity_survives_rename_and_rejects_replacement(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    identity_start = source.index("tree_root_identity()")
    identity = source[identity_start : source.index("\n}\n", identity_start) + 3]
    original = tmp_path / "original"
    renamed = tmp_path / "renamed"
    original.mkdir()
    script = "\n".join(
        (
            "set -u",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { command "$PYTHON_EXECUTOR" "$@"; }',
            identity,
            f"ORIGINAL={shlex.quote(_bash_path(original))}",
            f"RENAMED={shlex.quote(_bash_path(renamed))}",
            'before=$(tree_root_identity "$ORIGINAL")',
            'mv -- "$ORIGINAL" "$RENAMED"',
            'after=$(tree_root_identity "$RENAMED")',
            '[ "$before" = "$after" ]',
            'mkdir -- "$ORIGINAL"',
            'replacement=$(tree_root_identity "$ORIGINAL")',
            '[ "$before" != "$replacement" ]',
        )
    )

    result = _run_bash_script(tmp_path / "tree-root-identity.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout


def test_schema4_journal_loader_preserves_empty_systemd_attempt_field(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    loader = source[
        source.index("load_stale_install_state()") : source.index(
            "tree_matches_snapshot()"
        )
    ]
    release = tmp_path / "release"
    persistent = tmp_path / "persistent"
    evidence = tmp_path / "evidence"
    for path in (release, persistent, evidence):
        path.mkdir()
    journal = evidence / "install-mutation-state.json"
    attempt_id = "a" * 32
    candidate_sha = "1" * 64
    environment_sha = "2" * 64
    snapshot_sha = "3" * 64
    candidate_topology_sha = "8" * 64
    candidate_identity = "11:22"
    source_identity = "33:44"
    payload = {
        "attempt_id": attempt_id,
        "candidate_manifest_sha256": candidate_sha,
        "candidate_release_root_identity": candidate_identity,
        "candidate_release_topology_sha256": candidate_topology_sha,
        "environment_authority_sha256": environment_sha,
        "local_rehearsal": False,
        "old_root": _bash_path(tmp_path / ".release.closed-old.321"),
        "persistent_key_sha256": "4" * 64,
        "persistent_root": _bash_path(persistent),
        "pid": 321,
        "release_key_sha256": "5" * 64,
        "release_root": _bash_path(release),
        "retired_root": _bash_path(tmp_path / f".release.closed-retired.{attempt_id}"),
        "schema_version": 4,
        "source_release_root_identity": source_identity,
        "stage": "persistent-restored",
        "staging_root": _bash_path(tmp_path / ".release.closed-stage.321"),
        "systemd_key_sha256": "6" * 64,
        "systemd_unit_attempt_root": "",
        "systemd_unit_destination": _bash_path(tmp_path / "systemd"),
        "persistent_snapshot_sha256": snapshot_sha,
        "source_release_topology_sha256": "7" * 64,
    }
    journal.write_text(json.dumps(payload) + "\n", encoding="ascii")
    script = "\n".join(
        (
            "set -u",
            f"MUTATION_STATE={shlex.quote(_bash_path(journal))}",
            f"EVIDENCE_DIR={shlex.quote(_bash_path(evidence))}",
            f"PYTHON_EXECUTOR={shlex.quote(_bash_path(Path(sys.executable).resolve()))}",
            'invoke_python() { command "$PYTHON_EXECUTOR" "$@"; }',
            'canonical_authority_path() { printf "%s\\n" "$1"; }',
            "lock_spec() {",
            '  case "$1" in',
            f'    release) printf "release|%s|%s|release\\n" "$2" {shlex.quote("5" * 64)} ;;',
            f'    persistent) printf "persistent|%s|%s|persistent\\n" "$2" {shlex.quote("4" * 64)} ;;',
            f'    systemd) printf "systemd|%s|%s|systemd\\n" "$2" {shlex.quote("6" * 64)} ;;',
            "    *) return 64 ;;",
            "  esac",
            "}",
            loader,
            "set +e",
            "load_stale_install_state",
            "status=$?",
            'printf "%s|%s|%s|%s|%s|%s|%s|%s\\n" "$status" "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" "$STALE_CANDIDATE_MANIFEST_SHA256" "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" "$STALE_ENVIRONMENT_AUTHORITY_SHA256" "$STALE_PERSISTENT_SNAPSHOT_SHA256" "$STALE_SOURCE_RELEASE_ROOT_IDENTITY"',
        )
    )
    result = _run_bash_script(tmp_path / "load-state.sh", script)
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == (
        f"0||{candidate_sha}|{candidate_topology_sha}|{candidate_identity}|"
        f"{environment_sha}|{snapshot_sha}|{source_identity}"
    )


@pytest.mark.parametrize("rm_status", (0, 61), ids=("fake-success", "partial-failure"))
def test_old_root_cleanup_failure_keeps_committed_release_and_retry_finishes_cleanup(
    tmp_path: Path, closed_package, rm_status: int
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "old-root-cleanup-failure"
    prepared = _prepare_case(case_root, closed_package)
    (
        release,
        persistent,
        evidence,
        before_release,
        before_persistent,
        _,
        _,
    ) = prepared
    failure_used = case_root / f"old-root-cleanup-failure-used-{rm_status}"
    rm_executor = _write_cleanup_rm_fault_executor(
        case_root / "old-root-cleanup-failure-rm",
        basename_pattern=f".{release.name}.closed-retired-cleanup.*",
        marker=failure_used,
        status=rm_status,
        partial_relative="old-release-marker.txt",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_RM_EXECUTOR": _bash_path(rm_executor)},
    )

    assert first.returncode != 0, first.stderr + first.stdout
    assert failure_used.is_file()
    assert (release / "launch-release-manifest.json").is_file()
    assert not (release / "old-release-marker.txt").exists()
    assert _snapshot_tree(persistent) == before_persistent
    installed_release = _snapshot_tree(release)
    cleanup_roots = list(
        release.parent.glob(f".{release.name}.closed-retired-cleanup.*")
    )
    assert len([path for path in cleanup_roots if path.is_dir()]) == 1
    cleanup_root = next(path for path in cleanup_roots if path.is_dir())
    cleanup_owner = Path(f"{cleanup_root}.owner")
    assert cleanup_owner.is_file()
    assert not (cleanup_root / "old-release-marker.txt").exists()
    journal = evidence / "install-mutation-state.json"
    payload = json.loads(journal.read_text(encoding="utf-8"))
    assert payload["stage"] == "committed-cleanup"
    assert payload["retired_root"] == _bash_path(
        release.parent / f".{release.name}.closed-retired.{payload['attempt_id']}"
    )
    assert not list(release.parent.glob(f".{release.name}.closed-stage.*"))
    assert not list(release.parent.glob(f".{release.name}.closed-old.*"))

    second = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert second.returncode == 19, second.stderr + second.stdout
    assert _snapshot_tree(release) == installed_release
    assert _snapshot_tree(persistent) == before_persistent
    assert not journal.exists()
    assert _unit_attempt_artifacts(evidence) == []
    assert not list(release.parent.glob(f".{release.name}.closed-stage.*"))
    assert not list(release.parent.glob(f".{release.name}.closed-old.*"))
    assert not list(release.parent.glob(f".{release.name}.closed-retired.*"))
    assert not list(release.parent.glob(f".{release.name}.closed-retired-cleanup.*"))


@pytest.mark.parametrize(
    "rename_stage",
    ("release-to-old", "old-to-retired"),
)
def test_postrename_fsync_failure_reconciles_the_observed_filesystem_state(
    tmp_path: Path, closed_package, rename_stage: str
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"postrename-fsync-{rename_stage}"
    prepared = _prepare_case(case_root, closed_package)
    (
        release,
        persistent,
        evidence,
        before_release,
        before_persistent,
        _,
        _,
    ) = prepared
    parent = _bash_path(release.parent)
    failure_used = case_root / f"{rename_stage}-fsync-failed"
    if rename_stage == "release-to-old":
        state_probe = (
            f"[ ! -e '{_bash_path(release)}' ] "
            f"&& compgen -G '{parent}/.{release.name}.closed-old.*' >/dev/null "
            f"&& compgen -G '{parent}/.{release.name}.closed-stage.*' >/dev/null"
        )
        failure_code = 71
    else:
        state_probe = (
            f"[ -d '{_bash_path(release)}' ] "
            f"&& ! compgen -G '{parent}/.{release.name}.closed-old.*' >/dev/null "
            f"&& compgen -G '{parent}/.{release.name}.closed-retired.*' >/dev/null"
        )
        failure_code = 72
    python_executor = _write_local_python_executor(
        case_root / f"{rename_stage}-fsync-python",
        f"  if [ \"${{1:-}}\" = - ] "
        f"&& [ \"${{2:-}}\" = '{parent}' ] "
        f"&& [ ! -f '{_bash_path(failure_used)}' ] "
        f"&& {state_probe}; then\n"
        f"    : > '{_bash_path(failure_used)}'\n"
        f"    exit {failure_code}\n"
        "  fi\n"
        "command \"$REAL_PYTHON\" \"$@\"\n",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)},
    )

    assert first.returncode == failure_code, first.stderr + first.stdout
    assert failure_used.is_file()
    assert _snapshot_tree(persistent) == before_persistent
    journal = evidence / "install-mutation-state.json"
    if rename_stage == "release-to-old":
        assert _snapshot_tree(release) == before_release
        assert not journal.exists()
        assert not list(release.parent.glob(f".{release.name}.closed-old.*"))
    else:
        assert (release / "launch-release-manifest.json").is_file()
        assert not (release / "old-release-marker.txt").exists()
        installed_release = _snapshot_tree(release)
        payload = json.loads(journal.read_text(encoding="utf-8"))
        assert payload["stage"] == "retire-old-root-armed"
        assert len(list(release.parent.glob(f".{release.name}.closed-retired.*"))) == 1

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        failed_hook="python",
    )

    assert retry.returncode == 19, retry.stderr + retry.stdout
    assert _snapshot_tree(persistent) == before_persistent
    if rename_stage == "release-to-old":
        assert _snapshot_tree(release) == before_release
    else:
        assert _snapshot_tree(release) == installed_release
    assert not journal.exists()
    assert not list(release.parent.glob(f".{release.name}.closed-old.*"))
    assert not list(release.parent.glob(f".{release.name}.closed-retired.*"))


@pytest.mark.parametrize(
    ("cleanup_kind", "failure_mode"),
    (
        ("archive", "false-success"),
        ("pin", "nonzero"),
        ("lock", "fsync"),
    ),
)
def test_private_attempt_cleanup_bypasses_rm_shadow_and_releases_artifacts(
    tmp_path: Path,
    closed_package,
    cleanup_kind: str,
    failure_mode: str,
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / f"private-cleanup-{cleanup_kind}-{failure_mode}"
    prepared = _prepare_case(case_root, closed_package)
    release, _, evidence, _, _, _, _ = prepared
    bash_env, python_executor = _cleanup_failure_bash_env(
        case_root, evidence, cleanup_kind, failure_mode
    )
    env_overrides = {"BASH_ENV": _bash_path(bash_env)}
    if python_executor is not None:
        env_overrides["VL360_LOCAL_PYTHON_EXECUTOR"] = _bash_path(python_executor)

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides=env_overrides,
    )

    assert first.returncode == 0, first.stderr + first.stdout
    assert not (case_root / f"{cleanup_kind}-{failure_mode}-matched").exists()
    assert not (case_root / f"{cleanup_kind}-{failure_mode}-fsync-failed").exists()
    assert (release / "launch-release-manifest.json").is_file()
    assert not (release / "old-release-marker.txt").exists()
    assert _private_attempt_artifacts(case_root, evidence) == {
        "archive": [],
        "pin": [],
        "lock": [],
    }
    lock = json.loads((evidence / "install-lock.json").read_text(encoding="utf-8"))
    assert lock["status"] == "released"
    assert lock["exit_code"] == 0


def test_private_cleanup_preserves_primary_exit_status(tmp_path: Path):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    source = INSTALL.read_text(encoding="utf-8")
    start = source.index("cleanup_attempt_trap()")
    cleanup_trap = source[
        start : source.index("trap cleanup_attempt_trap EXIT", start)
    ]
    script = "\n".join(
        (
            "set +e",
            "cleanup_attempt_authorities() { return 61; }",
            cleanup_trap,
            "primary_failure() { return 19; }",
            "( primary_failure; cleanup_attempt_trap )",
            "primary_status=$?",
            "( true; cleanup_attempt_trap )",
            "cleanup_status=$?",
            "printf '%s|%s\\n' \"$primary_status\" \"$cleanup_status\"",
        )
    )
    result = _run_bash_script(tmp_path / "cleanup-precedence.sh", script)

    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == "19|61"


def test_rollback_journal_clear_false_success_remains_retryable(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "rollback-journal-clear-false-success"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    clear_intercepted = case_root / "clear-intercepted"
    bash_env = case_root / "clear-false-success.bash"
    bash_env.write_text(
        "rm() {\n"
        "  for argument in \"$@\"; do\n"
        f"    if [ \"$argument\" = '{_bash_path(journal)}' ] "
        "&& [ -f \"$argument\" ] "
        f"&& [ ! -f '{_bash_path(clear_intercepted)}' ]; then\n"
        f"      : > '{_bash_path(clear_intercepted)}'\n"
        "      return 0\n"
        "    fi\n"
        "  done\n"
        "  /usr/bin/rm \"$@\"\n"
        "}\n",
        encoding="ascii",
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "BASH_ENV": _bash_path(bash_env),
            "VL360_INSTALL_FAIL_AFTER": "swap-release-root",
        },
    )

    assert first.returncode == 73, first.stderr + first.stdout
    assert clear_intercepted.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "rollback-restored"
    )
    recovery = json.loads(
        (evidence / "install-recovery.json").read_text(encoding="utf-8")
    )
    assert recovery["status"] == "rollback-failed"
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent

    retry = _invoke_installer(closed_package, case_root, prepared)

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert not journal.exists()
    assert (release / "launch-release-manifest.json").is_file()
    assert _snapshot_tree(persistent) == before_persistent


def test_recovery_evidence_one_shot_failure_retains_journal_for_retry(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "recovery-evidence-one-shot-failure"
    prepared = _prepare_case(case_root, closed_package)
    release, persistent, evidence, before_release, before_persistent, _, _ = prepared
    journal = evidence / "install-mutation-state.json"
    failure_used = case_root / "recovery-evidence-failure-used"
    recovery_path = _bash_path(evidence / "install-recovery.json")
    python_executor = _write_local_python_executor(
        case_root / "recovery-evidence-python",
        f"if [ \"${{1:-}}\" = - ] "
        f"&& [ \"${{2:-}}\" = '{recovery_path}' ] "
        f"&& [ ! -f '{_bash_path(failure_used)}' ]; then\n"
        f"  : > '{_bash_path(failure_used)}'\n"
        "  exit 71\n"
        "fi\n"
        'command "$REAL_PYTHON" "$@"\n',
    )

    first = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={
            "VL360_INSTALL_FAIL_AFTER": "swap-release-root",
            "VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor),
        },
    )

    assert first.returncode == 73, first.stderr + first.stdout
    assert "recovery-evidence-record-failed:rolled-back:71" in first.stderr
    assert failure_used.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["stage"] == (
        "rollback-restored"
    )
    assert not (evidence / "install-recovery.json").exists()
    assert _snapshot_tree(release) == before_release
    assert _snapshot_tree(persistent) == before_persistent

    retry = _invoke_installer(
        closed_package,
        case_root,
        prepared,
        env_overrides={"VL360_LOCAL_PYTHON_EXECUTOR": _bash_path(python_executor)},
    )

    assert retry.returncode == 0, retry.stderr + retry.stdout
    assert not journal.exists()
    assert (release / "launch-release-manifest.json").is_file()
    assert _snapshot_tree(persistent) == before_persistent


def test_startup_sweeps_only_ownerless_or_stale_private_attempt_artifacts(
    tmp_path: Path, closed_package
):
    if not BASH.is_file():
        pytest.skip("Git Bash is unavailable")
    case_root = tmp_path / "sweep"
    prepared = _prepare_case(case_root, closed_package)
    _, _, evidence, _, _, _, _ = prepared
    private_tmp = case_root / "private-tmp"

    stale_archive = evidence / ".closed-archive-attempt.ownerless"
    stale_archive.mkdir()
    stale_pin = private_tmp / "vl360-executable-pins.999999.dead.orphan"
    stale_pin.mkdir()
    evidence_lock = _authority_lock_path("evidence", evidence)
    stale_lock = Path(f"{evidence_lock}.released.999999.dead")
    stale_lock.mkdir(parents=True)

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
        active_pin = private_tmp / (
            f"vl360-executable-pins.{pid_text}.{start_identity}.active"
        )
        active_pin.mkdir()
        active_lock = Path(f"{evidence_lock}.released.{pid_text}.{start_identity}")
        active_lock.mkdir()

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
    assert not stale_archive.exists()
    assert not stale_pin.exists()
    assert not stale_lock.exists()
    assert active_pin.is_dir()
    assert active_lock.is_dir()
