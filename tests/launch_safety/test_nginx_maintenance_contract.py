from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

from tests.launch_safety.test_nginx_contract import _public_servers


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "ops" / "nginx" / "maintenance"
SCRIPT = ROOT / "scripts" / "ops" / "maintenance_mode.sh"
HTTP_CONTEXT_INCLUDE = "include /etc/nginx/vl360-maintenance/http-context.conf;"
ACTIVE_SERVER_INCLUDE = "include /etc/nginx/vl360-maintenance/active-server.conf;"

HTTP_TEMPLATE = """\
geo $launch_maintenance_operator {
    default 0;
    127.0.0.1/32 1;
    ::1/128 1;
    __OPERATOR_CIDR__ 1;
}
"""
SERVER_ENABLED = "if ($launch_maintenance_operator = 0) { return 503; }\n"
SERVER_DISABLED = (
    "# Maintenance disabled: requests continue to the reviewed server locations.\n"
)


@pytest.mark.parametrize(
    ("filename", "expected_public_servers"),
    [("nginx.conf", 1), ("nginx-ssl.conf", 2)],
)
def test_real_nginx_configs_wire_maintenance_includes_exactly_once_per_context(
    filename: str,
    expected_public_servers: int,
):
    source = (ROOT / filename).read_text(encoding="utf-8")
    assert source.count(HTTP_CONTEXT_INCLUDE) == 1
    assert source.count(ACTIVE_SERVER_INCLUDE) == expected_public_servers
    assert source.index(HTTP_CONTEXT_INCLUDE) < source.index("server {")

    servers = _public_servers(ROOT / filename)
    assert len(servers) == expected_public_servers
    for server in servers:
        assert server.children is not None
        assert sum(
            statement.parts == ("include", "/etc/nginx/vl360-maintenance/active-server.conf")
            for statement in server.children
        ) == 1


def _bash() -> str:
    discovered = shutil.which("bash")
    if discovered:
        return discovered
    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if git_bash.is_file():
        return str(git_bash)
    pytest.skip("Bash is unavailable")


def _bash_path(path: Path) -> str:
    bash = Path(_bash())
    if os.name == "nt" and bash.name.lower() == "bash.exe":
        converted = subprocess.run(
            [str(bash), "-lc", 'cygpath -u "$1"', "maintenance-test", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return converted.stdout.strip()
    return str(path)


def _create_relative_symlink(link: Path, target: str) -> None:
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"relative symlink creation unavailable: {exc}")


def _prepare_runtime(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "http-context.conf").write_text(
        HTTP_TEMPLATE.replace("__OPERATOR_CIDR__", "192.0.2.0/24"),
        encoding="utf-8",
    )
    (runtime / "server-enabled.conf").write_bytes(SERVER_ENABLED.encode("utf-8"))
    (runtime / "server-disabled.conf").write_bytes(SERVER_DISABLED.encode("utf-8"))
    _create_relative_symlink(runtime / "active-server.conf", "server-disabled.conf")

    nginx_log = tmp_path / "nginx.log"
    nginx = tmp_path / "nginx"
    nginx.write_text(
        """\
#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >>"$FAKE_NGINX_LOG"
[ "${FAKE_NGINX_FAIL:-0}" != 1 ]
""",
        encoding="utf-8",
    )
    nginx.chmod(0o755)
    return runtime, nginx, nginx_log


def _require_live_symlink_replacement() -> None:
    if os.name == "nt":
        pytest.skip("Git Bash/Windows cannot safely replace live symlinks in this contract test")


def _run_script(
    runtime: Path,
    nginx: Path,
    nginx_log: Path,
    *args: str,
    fail_nginx: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "VL360_MAINTENANCE_DIR": _bash_path(runtime),
            "VL360_NGINX_BIN": _bash_path(nginx),
            "FAKE_NGINX_LOG": _bash_path(nginx_log),
            "FAKE_NGINX_FAIL": "1" if fail_nginx else "0",
        }
    )
    return subprocess.run(
        [_bash(), _bash_path(SCRIPT), *args],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_toggle_script_is_directly_executable_from_the_git_index_archive(
    tmp_path: Path,
):
    relative_script = SCRIPT.relative_to(ROOT).as_posix()
    tracked = subprocess.run(
        ["git", "ls-files", "--stage", "--", relative_script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tracked.stdout.split(maxsplit=1)[0] == "100755"

    tree = subprocess.run(
        ["git", "write-tree"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    archive = tmp_path / "index.tar"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            f"--output={archive}",
            tree,
            relative_script,
        ],
        cwd=ROOT,
        check=True,
    )
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    subprocess.run(
        [
            _bash(),
            "-lc",
            'tar -xf "$1" -C "$2"',
            "maintenance-test",
            _bash_path(archive),
            _bash_path(extracted),
        ],
        check=True,
    )

    result = subprocess.run(
        [
            _bash(),
            "-lc",
            'script=$1; exec "$script"',
            "maintenance-test",
            _bash_path(extracted / relative_script),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stderr == (
        "usage: maintenance_mode.sh enable|disable --operator-cidr CIDR\n"
    )


def test_tracked_maintenance_includes_match_the_reviewed_contract():
    assert {path.name for path in SOURCE_ROOT.iterdir()} == {
        "http-context.conf.template",
        "server-enabled.conf",
        "server-disabled.conf",
    }
    assert (SOURCE_ROOT / "http-context.conf.template").read_text(
        encoding="utf-8"
    ) == HTTP_TEMPLATE
    assert (SOURCE_ROOT / "server-enabled.conf").read_text(
        encoding="utf-8"
    ) == SERVER_ENABLED
    assert (SOURCE_ROOT / "server-disabled.conf").read_text(
        encoding="utf-8"
    ) == SERVER_DISABLED


def test_toggle_script_has_atomic_validation_and_never_reloads_nginx():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "ipaddress.ip_network" in source
    assert "strict=False" in source
    assert "umask 077" in source
    assert "mv -Tf" in source
    assert "readlink" in source
    assert "server-enabled.conf" in source
    assert "server-disabled.conf" in source
    assert "reload" not in source.lower()
    assert "nginx -s reload" not in source
    assert "systemctl reload" not in source
    assert "service nginx reload" not in source


def test_enable_canonicalizes_cidr_copies_includes_and_selects_relative_target(
    tmp_path: Path,
):
    _require_live_symlink_replacement()
    runtime, nginx, nginx_log = _prepare_runtime(tmp_path)

    result = _run_script(
        runtime,
        nginx,
        nginx_log,
        "enable",
        "--operator-cidr",
        "10.31.7.9/24",
    )

    assert result.returncode == 0, result.stderr
    rendered = (runtime / "http-context.conf").read_text(encoding="utf-8")
    assert "10.31.7.0/24 1;" in rendered
    assert "10.31.7.9/24" not in rendered
    assert "__OPERATOR_CIDR__" not in rendered
    assert (runtime / "server-enabled.conf").read_bytes() == SERVER_ENABLED.encode()
    assert (runtime / "server-disabled.conf").read_bytes() == SERVER_DISABLED.encode()
    assert os.readlink(runtime / "active-server.conf") == "server-enabled.conf"
    assert nginx_log.read_text(encoding="utf-8").splitlines() == ["-t"]
    assert list(runtime.glob(".*.tmp")) == []


def test_enable_and_disable_are_idempotent(tmp_path: Path):
    _require_live_symlink_replacement()
    runtime, nginx, nginx_log = _prepare_runtime(tmp_path)

    for target in ("enable", "enable", "disable", "disable"):
        result = _run_script(
            runtime,
            nginx,
            nginx_log,
            target,
            "--operator-cidr",
            "2001:db8::f/64",
        )
        assert result.returncode == 0, result.stderr

    assert os.readlink(runtime / "active-server.conf") == "server-disabled.conf"
    assert "2001:db8::/64 1;" in (runtime / "http-context.conf").read_text(
        encoding="utf-8"
    )
    assert nginx_log.read_text(encoding="utf-8").splitlines() == ["-t"] * 4


@pytest.mark.parametrize(
    "cidr",
    [
        "not-a-network",
        "10.0.0.1/24\nreturn 200;",
        "10.0.0.1/24\rinclude evil.conf;",
        "__OPERATOR_CIDR__",
    ],
)
def test_invalid_or_injected_cidr_preserves_runtime_state(tmp_path: Path, cidr: str):
    runtime, nginx, nginx_log = _prepare_runtime(tmp_path)
    before_http = (runtime / "http-context.conf").read_bytes()
    before_target = os.readlink(runtime / "active-server.conf")

    result = _run_script(
        runtime,
        nginx,
        nginx_log,
        "enable",
        "--operator-cidr",
        cidr,
    )

    assert result.returncode != 0
    assert (runtime / "http-context.conf").read_bytes() == before_http
    assert os.readlink(runtime / "active-server.conf") == before_target
    assert not nginx_log.exists()
    assert cidr not in result.stderr


def test_failed_nginx_test_atomically_restores_rendered_file_and_selector(
    tmp_path: Path,
):
    _require_live_symlink_replacement()
    runtime, nginx, nginx_log = _prepare_runtime(tmp_path)
    before_http = (runtime / "http-context.conf").read_bytes()
    before_target = os.readlink(runtime / "active-server.conf")

    result = _run_script(
        runtime,
        nginx,
        nginx_log,
        "enable",
        "--operator-cidr",
        "10.20.30.40/24",
        fail_nginx=True,
    )

    assert result.returncode != 0
    assert (runtime / "http-context.conf").read_bytes() == before_http
    assert os.readlink(runtime / "active-server.conf") == before_target
    assert nginx_log.read_text(encoding="utf-8").splitlines() == ["-t"]
    assert list(runtime.glob(".*.tmp")) == []
    assert str(runtime) not in result.stderr


@pytest.mark.parametrize(
    "unsafe_target",
    [
        "/etc/nginx/vl360-maintenance/server-enabled.conf",
        "../server-enabled.conf",
        "unexpected.conf",
    ],
)
def test_existing_selector_must_be_contained_relative_and_known(
    tmp_path: Path,
    unsafe_target: str,
):
    runtime, nginx, nginx_log = _prepare_runtime(tmp_path)
    (runtime / "active-server.conf").unlink()
    _create_relative_symlink(runtime / "active-server.conf", unsafe_target)
    before_http = (runtime / "http-context.conf").read_bytes()

    result = _run_script(
        runtime,
        nginx,
        nginx_log,
        "enable",
        "--operator-cidr",
        "10.0.0.1/32",
    )

    assert result.returncode != 0
    assert (runtime / "http-context.conf").read_bytes() == before_http
    assert os.readlink(runtime / "active-server.conf") == unsafe_target
    assert not nginx_log.exists()


def test_missing_selector_is_fatal_and_does_not_initialize_implicitly(tmp_path: Path):
    runtime, nginx, nginx_log = _prepare_runtime(tmp_path)
    (runtime / "active-server.conf").unlink()

    result = _run_script(
        runtime,
        nginx,
        nginx_log,
        "disable",
        "--operator-cidr",
        "10.0.0.1/32",
    )

    assert result.returncode != 0
    assert not (runtime / "active-server.conf").exists()
    assert not nginx_log.exists()


def test_runtime_directory_symlink_is_rejected_without_touching_target(tmp_path: Path):
    real_runtime, nginx, nginx_log = _prepare_runtime(tmp_path)
    linked_runtime = tmp_path / "linked-runtime"
    try:
        linked_runtime.symlink_to(real_runtime, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation unavailable: {exc}")
    before_http = (real_runtime / "http-context.conf").read_bytes()

    result = _run_script(
        linked_runtime,
        nginx,
        nginx_log,
        "enable",
        "--operator-cidr",
        "10.0.0.1/32",
    )

    assert result.returncode != 0
    assert (real_runtime / "http-context.conf").read_bytes() == before_http
    assert os.readlink(real_runtime / "active-server.conf") == "server-disabled.conf"
    assert not nginx_log.exists()


def test_double_leading_slash_runtime_path_is_rejected_before_timeout():
    environment = os.environ.copy()
    environment["VL360_MAINTENANCE_DIR"] = "//"

    result = subprocess.run(
        [
            _bash(),
            "-lc",
            'timeout --kill-after=1 2 bash "$1" enable '
            "--operator-cidr 10.0.0.1/32",
            "maintenance-test",
            _bash_path(SCRIPT),
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode != 124, "double-leading slash path validation timed out"
    assert result.returncode != 0
    assert result.stderr == "maintenance_mode: unsafe-maintenance-path\n"


def test_windows_drive_root_runtime_path_is_rejected_before_timeout():
    environment = os.environ.copy()
    environment["VL360_MAINTENANCE_DIR"] = "C:/"

    result = subprocess.run(
        [
            _bash(),
            "-lc",
            'timeout --kill-after=1 2 bash "$1" enable '
            "--operator-cidr 10.0.0.1/32",
            "maintenance-test",
            _bash_path(SCRIPT),
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode != 124, "Windows drive root path validation timed out"
    assert result.returncode != 0
    assert result.stderr == "maintenance_mode: unsafe-maintenance-path\n"
