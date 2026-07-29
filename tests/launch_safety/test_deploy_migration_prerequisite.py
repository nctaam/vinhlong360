from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tarfile

from scripts.package_launch_release import build_launch_release
from tests.launch_safety.test_release_package import _write_launch_fixture


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "deploy.sh"
BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _bash_path(path: Path) -> str:
    result = subprocess.run(
        [str(BASH), "-lc", 'cygpath -u "$1"', "deploy-gate-test", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _remote_body(script: str, marker: str) -> str:
    start = script.index(marker)
    heredoc = script.index("<<EOF\n", start) + len("<<EOF\n")
    end = script.index("\nEOF", heredoc)
    return script[heredoc:end].replace("\\$", "$")


def _installer_command(script: str) -> str:
    start = script.index('"\\$LAUNCH_STAGE/archive-tools/install_closed_release.sh"')
    end = script.index("\n\nsystemctl daemon-reload", start)
    return script[start:end].replace("\\$", "$")


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def test_release_archive_snapshots_checker_verifier_and_incoming_migrations(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    audit = _write_launch_fixture(source)
    checker = source / "scripts" / "check_migration_gate.py"
    checker.write_bytes(b"packaged checker authority\n")
    verifier = source / "scripts" / "ops" / "verify_closed_release.py"
    verifier.write_bytes(b"packaged verifier authority\n")
    migration = source / "agent" / "migrations" / "070_release_gate.sql"
    migration.parent.mkdir(parents=True, exist_ok=True)
    migration.write_bytes(b"-- packaged migration authority\n")

    package = build_launch_release(
        source,
        tmp_path / "release.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )
    checker.write_bytes(b"mutated live checker\n")
    verifier.write_bytes(b"mutated live verifier\n")
    migration.write_bytes(b"-- mutated live migration\n")

    with tarfile.open(package.archive, "r:gz") as archive:
        names = set(archive.getnames())
        assert "scripts/check_migration_gate.py" in names
        assert "scripts/ops/verify_closed_release.py" in names
        assert "agent/migrations/070_release_gate.sql" in names
        assert archive.extractfile("scripts/check_migration_gate.py").read() == (
            b"packaged checker authority\n"
        )
        assert archive.extractfile("scripts/ops/verify_closed_release.py").read() == (
            b"packaged verifier authority\n"
        )
        assert archive.extractfile("agent/migrations/070_release_gate.sql").read() == (
            b"-- packaged migration authority\n"
        )


def test_deploy_does_not_scp_archive_owned_verifier_checker_or_migrations(
    tmp_path: Path,
) -> None:
    script = DEPLOY.read_text(encoding="utf-8")
    start = script.index("LAUNCH_FILES=(")
    end = script.index("\n\n# 5. Ship tarballs", start)
    staging = script[start:end]
    event_log = tmp_path / "scp.log"
    scenario = tmp_path / "stage.sh"
    scenario.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
capture_scp() {{ printf '%s\\0' "$@" >> {_bash_path(event_log)!r}; }}
SCP=(capture_scp)
VPS=fake-host
LAUNCH_STAGE=/tmp/vl360-launch-admission.test
{staging}
""",
        encoding="utf-8",
        newline="\n",
    )

    result = subprocess.run(
        [str(BASH), str(scenario)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    staged_sources = event_log.read_bytes().decode("utf-8").split("\0")
    forbidden = {
        "scripts/ops/verify_closed_release.py",
        "scripts/check_migration_gate.py",
    }
    assert forbidden.isdisjoint(staged_sources)
    assert not any(source.startswith("agent/migrations/") for source in staged_sources)


def _run_gate_and_installer_slice(
    tmp_path: Path,
    *,
    gate_status: int,
    append_installer: bool,
) -> subprocess.CompletedProcess[str]:
    script = DEPLOY.read_text(encoding="utf-8")
    body = _remote_body(script, "# 5c.")
    installer = _installer_command(script) if append_installer else ""
    stage = tmp_path / "stage"
    migrations = stage / "migrations"
    migrations.mkdir(parents=True)
    (stage / "check_migration_gate.py").write_text("# boundary stub\n", encoding="ascii")
    event_log = tmp_path / "events.log"
    authority = tmp_path / "production.env"
    canary = "postgresql://gate-user:password-canary@db/vl360"
    authority.write_text(
        "ENVIRONMENT=production\n"
        f"DATABASE_URL={canary}\n"
        "ENTITY_DETAILS_TABLES=true\n",
        encoding="ascii",
    )
    authority.chmod(0o600)
    gate_python = tmp_path / "release" / "venv" / "bin" / "python"
    gate_python.parent.mkdir(parents=True)
    _write_executable(
        gate_python,
        f"""#!/usr/bin/env bash
set -euo pipefail
event_log={_bash_path(event_log)!r}
environment_authority={_bash_path(authority)!r}
printf 'MIGRATION_PYTHON_ARG=%s\\n' "$@" >>"$event_log"
if [ "${{1:-}}" = -I ] && [ "${{2:-}}" = -c ]; then
  exit 0
fi
checker_authority=''
previous=''
for argument in "$@"; do
  if [ "$previous" = --environment-pin ]; then
    checker_authority="$argument"
  fi
  previous="$argument"
done
[ -n "$checker_authority" ] || checker_authority="$environment_authority"
if [ "$checker_authority" != "$environment_authority" ]; then
  cp -- "$environment_authority" "$checker_authority"
  chmod 600 "$checker_authority"
fi
printf 'CHECKER_AUTHORITY=%s\\n' "$checker_authority" >>"$event_log"
printf 'CHILD_ARG=%s\\n' "$@" >>"$event_log"
printf 'DATABASE_URL=postgresql://mutated:after-pin@db/vl360\\n' >{_bash_path(authority)!r}
exit {gate_status}
""",
    )
    installer_stub = stage / "archive-tools" / "install_closed_release.sh"
    installer_stub.parent.mkdir()
    _write_executable(
        installer_stub,
        """#!/usr/bin/env bash
set -euo pipefail
printf 'INSTALLER_ARG=%s\\n' "$@" >>"$EVENT_LOG"
while [ "$#" -gt 0 ]; do
  if [ "$1" = --environment-authority ]; then
    shift
    printf 'INSTALLER_AUTHORITY=%s\\n' "$1" >>"$EVENT_LOG"
    printf 'INSTALLER_MODE=%s\\n' "$(stat -c %a -- "$1")" >>"$EVENT_LOG"
    [ -f "$1" ] && printf 'INSTALLER_REGULAR=yes\\n' >>"$EVENT_LOG"
    [ ! -L "$1" ] && printf 'INSTALLER_SYMLINK=no\\n' >>"$EVENT_LOG"
    printf 'INSTALLER_DIGEST=%s\\n' "$(sha256sum -- "$1" | cut -d' ' -f1)" >>"$EVENT_LOG"
  fi
  shift
done
""",
    )
    scenario = tmp_path / "gate-and-installer.sh"
    scenario.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export EVENT_LOG={_bash_path(event_log)!r}
export ENVIRONMENT_AUTHORITY={_bash_path(authority)!r}
export LAUNCH_STAGE={_bash_path(stage)!r}
export REMOTE=/srv/vl360
export MIGRATION_GATE_PYTHON={_bash_path(gate_python)!r}
export PERSISTENT_AGENT_DATA_ROOT=/srv/vl360-data
export RUNTIME_AUTHORITY=/srv/vl360-runtime
export MOUNT_AUTHORITY=/usr/local/bin/vl360-mount
python3() {{
  printf 'SYSTEM_PYTHON_USED=%s\\n' "$*" >>"$EVENT_LOG"
  return 88
}}
{body}
{installer}
""",
        encoding="utf-8",
        newline="\n",
    )
    return subprocess.run(
        [str(BASH), str(scenario)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_environment_authority_is_pinned_once_and_secret_never_enters_child_argv(
    tmp_path: Path,
) -> None:
    result = _run_gate_and_installer_slice(
        tmp_path,
        gate_status=0,
        append_installer=True,
    )

    assert result.returncode == 0, result.stderr
    events = (tmp_path / "events.log").read_text(encoding="utf-8")
    checker_authority = next(
        line.split("=", 1)[1]
        for line in events.splitlines()
        if line.startswith("CHECKER_AUTHORITY=")
    )
    installer_authority = next(
        line.split("=", 1)[1]
        for line in events.splitlines()
        if line.startswith("INSTALLER_AUTHORITY=")
    )
    assert checker_authority == installer_authority
    assert checker_authority != _bash_path(tmp_path / "production.env")
    if os.name != "nt":
        assert "INSTALLER_MODE=600" in events
    else:
        assert "INSTALLER_MODE=" in events
    assert "INSTALLER_REGULAR=yes" in events
    assert "INSTALLER_SYMLINK=no" in events
    expected_digest = hashlib.sha256(
        (
            b"ENVIRONMENT=production\r\n"
            b"DATABASE_URL=postgresql://gate-user:password-canary@db/vl360\r\n"
            b"ENTITY_DETAILS_TABLES=true\r\n"
        )
        if os.name == "nt"
        else (
            b"ENVIRONMENT=production\n"
            b"DATABASE_URL=postgresql://gate-user:password-canary@db/vl360\n"
            b"ENTITY_DETAILS_TABLES=true\n"
        )
    ).hexdigest()
    assert f"INSTALLER_DIGEST={expected_digest}" in events
    assert "--database-url" not in events
    canary = "password-canary"
    assert canary not in events
    assert canary not in result.stdout
    assert canary not in result.stderr
    assert "SYSTEM_PYTHON_USED=" not in events


def test_deploy_uses_one_dependency_bearing_interpreter_for_both_database_gates() -> None:
    script = DEPLOY.read_text(encoding="utf-8")

    assert (
        'MIGRATION_GATE_PYTHON="${VL360_DEPLOY_MIGRATION_GATE_PYTHON:-$REMOTE/venv/bin/python}"'
        in script
    )
    assert script.count('"\\$MIGRATION_GATE_PYTHON" -I \\') == 2
    assert (
        'python3 -I "\\$LAUNCH_STAGE/migration-prerequisites/check_migration_gate.py"'
        not in script
    )


def test_failed_migration_gate_stops_before_launch_or_service_mutation(
    tmp_path: Path,
) -> None:
    result = _run_gate_and_installer_slice(
        tmp_path,
        gate_status=37,
        append_installer=False,
    )
    events = (tmp_path / "events.log").read_text(encoding="utf-8")

    assert result.returncode != 0
    assert "CHECKER_AUTHORITY=" in events
    for forbidden in (
        "close_launch_admission",
        "INSTALLER_ARG=",
        "systemctl",
        "maintenance",
    ):
        assert forbidden not in events
