from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_entity_status_stage_b.ps1"


def _run_script(
    env: dict[str, str], *extra: str, timeout: float = 120
) -> subprocess.CompletedProcess[str]:
    command = [
        "pwsh",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(SCRIPT),
        *extra,
    ]
    return subprocess.run(
        command, capture_output=True, text=True, env=env, check=False, timeout=timeout
    )


def test_runner_source_contract_has_safe_defaults_and_no_stage_c_paths() -> None:
    source = SCRIPT.read_text(encoding="utf-8") if SCRIPT.exists() else ""
    for forbidden in (
        "migrate_entity_status.py apply",
        "migrate_entity_status.py rollback",
        "scripts/export_data.py",
        "scripts/deploy.sh",
        "/opt/vinhlong360/.env",
        "cat .env",
    ):
        assert forbidden not in source
    assert "APPLY_NOT_RUN" in source
    assert "root@66.42.57.202" in source
    assert "VL360_STAGE_B_DATABASE_URL" in source


def test_runner_is_missing_before_implementation() -> None:
    """This test is intentionally RED before the runner is implemented."""
    if not SCRIPT.exists():
        pytest.fail("runner script is not implemented")


def test_test_mode_rejects_fake_tools_outside_pytest_root(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "VL360_STAGE_B_TEST_MODE": "1",
            "VL360_STAGE_B_TEST_ROOT": str(tmp_path),
            "VL360_STAGE_B_FAKE_SSH": str(Path(os.environ.get("TEMP", "C:/")) / "ssh.ps1"),
        }
    )
    result = _run_script(env, "-ArtifactParent", str(tmp_path / "artifacts"))
    assert result.returncode != 0
    assert "fake" in result.stderr.lower() or "test" in result.stderr.lower()


def test_runner_binds_psql_through_scoped_pg_environment_without_url_or_sql_argv() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "PGHOST" in source
    assert "PGPORT" in source
    assert "PGUSER" in source
    assert "PGPASSWORD" in source
    assert "PGDATABASE" in source
    assert "current_setting('server_version_num')" in source
    assert "current_setting('transaction_read_only')" in source
    assert "current_user" in source
    assert "--command" not in source


def test_runner_capture_drains_both_pipes_and_fails_closed_on_timeout() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ReadToEndAsync()" in source
    assert "WhenAll([Threading.Tasks.Task[]]@($stdoutTask, $stderrTask))" in source
    assert "$drainTask.GetAwaiter().GetResult()" in source
    assert "child process timed out" in source
    assert "child process did not terminate after timeout" in source
    assert "Kill($true)" in source
    assert "WaitForExit($remaining)" in source
    assert "-or -not $process.HasExited" in source


def test_runner_keeps_tunnel_handle_and_verifies_identity_before_cleanup() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    open_tunnel = source.split("function Open-Tunnel {", 1)[1].split(
        "function Assert-TunnelProcessOwnership {", 1
    )[0]
    stop_tunnel = source.split("function Stop-Tunnel {", 1)[1].split(
        "function Dispose-TunnelProcess {", 1
    )[0]
    cleanup = source.split("function Invoke-Cleanup {", 1)[1].split(
        "function Get-SourceState {", 1
    )[0]
    assert "$script:TunnelProcess" in source
    assert "$script:TunnelIdentity" in source
    assert "CopyToAsync([IO.Stream]::Null)" in source
    assert "Assert-TunnelProcessOwnership" in source
    assert "Get-Process -Id $script:TunnelPid" not in stop_tunnel
    assert "Get-Process -Id $script:TunnelPid" not in cleanup
    assert "Stop-Process -Id $script:TunnelPid" not in stop_tunnel
    assert "Stop-Process -Id $script:TunnelPid" not in cleanup
    assert "Stop-RetainedTunnelProcess" in open_tunnel
    assert "Dispose-TunnelProcess" in open_tunnel
    assert "finally { Dispose-TunnelProcess }" not in open_tunnel
    assert open_tunnel.count("if ($script:TunnelProcess.HasExited)") >= 2
    assert "finally { Dispose-TunnelProcess }" in cleanup
    assert "if ($null -ne $script:TunnelIdentity)" in cleanup


def test_runner_cleanup_listener_absence_only_checks_loopback_listeners() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    cleanup = source.split("function Invoke-Cleanup {", 1)[1].split(
        "function Get-SourceState {", 1
    )[0]
    assert (
        "Get-NetTCPConnection -State Listen -LocalPort $LocalPort "
        "-ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq '127.0.0.1' }"
        in cleanup
    )
    assert "Get-NetTCPConnection -LocalPort $LocalPort" not in cleanup


def test_runner_tunnel_readiness_requires_retained_identity_and_one_owned_listener() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    marker = "function Assert-TunnelReady {"
    assert marker in source
    ready = source.split(marker, 1)[1].split("function Stop-Tunnel {", 1)[0]
    assert "Assert-TunnelProcessOwnership" in ready
    assert ready.count("$script:TunnelProcess.HasExited") >= 2
    assert "Get-NetTCPConnection -State Listen -LocalPort $LocalPort" in ready
    assert "Where-Object { $_.LocalAddress -eq '127.0.0.1' }" in ready
    assert "$listeners.Count -ne 1" in ready
    assert "$listeners[0].OwningProcess -ne $script:TunnelPid" in ready


def test_runner_attestation_uses_cleanup_verification_timestamps() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "$script:CleanupEvidence.RoleAbsentCheckedAt = [DateTime]::UtcNow" in source
    assert "$script:CleanupEvidence.TunnelAbsentCheckedAt = [DateTime]::UtcNow" in source
    assert "absent_checked_at = $script:CleanupEvidence.RoleAbsentCheckedAt" in source
    assert "absent_checked_at = $script:CleanupEvidence.TunnelAbsentCheckedAt" in source
    assert "cleanup absence timestamps are missing" in source


def test_runner_refreshes_noindex_after_cleanup_before_attestation() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    publication = source.split("if ($null -ne $mainError)", 1)[1]
    assert "$freshNoindex = Invoke-NoindexCheck" in publication
    assert "noindex = $freshNoindex" in publication


def test_runner_passes_real_safe_arguments_and_scoped_pg_values_to_fakes(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode == 0, result.stderr
    identity = next(record for record in fake_stage_b_tools.records if record["event"] == "verify-readonly-identity")
    assert identity["arguments"] == [
        "--no-psqlrc",
        "--tuples-only",
        "--no-align",
        "--field-separator",
        "|",
        "--set",
        "ON_ERROR_STOP=1",
    ]
    assert identity["pg_environment"] == {
        "PGHOST": "127.0.0.1",
        "PGPORT": "15432",
        "PGDATABASE": "vinhlong360",
    }
    assert identity["pg_password_matches_role_sql"] is True
    create_role = next(record for record in fake_stage_b_tools.records if record["event"] == "create-role")
    assert "root@66.42.57.202" in create_role["arguments"]
    assert not any(str(argument).startswith("<") for argument in create_role["arguments"])


def test_runner_does_not_inherit_ambient_database_credentials(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "SetEnvironmentVariable($DatabaseUrlEnvironment" not in source
    assert "$script:PreviousDatabaseUrl" not in source
    env = os.environ.copy()
    env.update(
        {
            "VL360_STAGE_B_TEST_MODE": "1",
            "VL360_STAGE_B_TEST_ROOT": str(fake_stage_b_tools.root),
            "VL360_STAGE_B_FAKE_TOOLS_DIR": str(fake_stage_b_tools.tools),
            "VL360_STAGE_B_EVENT_LOG": str(fake_stage_b_tools.events_path),
            "VL360_STAGE_B_FAKE_ROOT": str(fake_stage_b_tools.root / "artifacts"),
            "VL360_STAGE_B_SECRET_CAPTURE": str(fake_stage_b_tools.secret_capture),
            "VL360_STAGE_B_FAILURE_STAGE": "",
            "VL360_STAGE_B_NOINDEX_VARIANT": "normal",
            "VL360_STAGE_B_IDENTITY_VARIANT": "normal",
            "VL360_STAGE_B_ROLE_CHECK_VARIANT": "canonical",
            "DATABASE_URL": "postgresql://ambient:secret@db/prod",
            "VL360_STAGE_B_DATABASE_URL": "postgresql://ambient:secret@db/prod",
            "PGPASSWORD": "ambient-secret",
            "PGOPTIONS": "ambient-options",
        }
    )
    result = _run_script(env, "-ArtifactParent", str(fake_stage_b_tools.root / "artifacts-parent"))
    assert result.returncode == 0, result.stderr
    records = {record["event"]: record for record in fake_stage_b_tools.records}
    assert records["verify-readonly-identity"]["pg_password_present"] is True
    assert all(
        record["pg_password_present"] is False
        for event, record in records.items()
        if event != "verify-readonly-identity"
    )
    assert records["backup"]["named_database_url_present"] is True
    assert records["plan"]["named_database_url_present"] is True
    assert records["backup"]["named_database_url_matches_generated"] is True
    assert records["plan"]["named_database_url_matches_generated"] is True
    assert all(
        record["named_database_url_present"] is False
        for event, record in records.items()
        if event not in {"backup", "plan"}
    )
    assert all(record["generic_database_url_present"] is False for record in records.values())
    assert all(record["ambient_pg_options_present"] is False for record in records.values())


def test_runner_timeout_kills_child_and_returns_without_running_later_stages(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    fake_stage_b_tools.failure_stage = "timeout"
    fake_stage_b_tools.process_timeout_ms = "5000"
    result = fake_stage_b_tools.run(tmp_path, timeout=60)
    assert result.returncode != 0
    assert fake_stage_b_tools.events == [
        "verify-source-noindex",
        "create-root",
        "create-role",
        "open-tunnel",
        "verify-tunnel-ready",
        "verify-readonly-identity",
        "verify-tunnel-ready",
        "verify-tunnel-ready",
        "backup",
        "verify-tunnel-ready",
        "verify-tunnel-ready",
        "plan",
        "drop-role",
        "close-tunnel",
        "verify-role-absent",
        "verify-tunnel-absent",
    ]
    assert "timed out" in result.stderr.lower()


def test_runner_guards_every_credentialed_database_consumer_before_and_after(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode == 0, result.stderr
    events = fake_stage_b_tools.events
    for consumer in ("verify-readonly-identity", "backup", "plan"):
        index = events.index(consumer)
        assert events[index - 1] == "verify-tunnel-ready"
        assert events[index + 1] == "verify-tunnel-ready"
    assert events.count("verify-tunnel-ready") == 6


def test_runner_fails_closed_before_database_use_when_tunnel_is_not_ready(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    fake_stage_b_tools.failure_stage = "verify-tunnel-ready"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert "verify-readonly-identity" not in fake_stage_b_tools.events
    assert "backup" not in fake_stage_b_tools.events
    assert "plan" not in fake_stage_b_tools.events
    assert "ERROR: ssh failed (exit 17)" in result.stderr
    assert "drop-role" in fake_stage_b_tools.events
    assert "close-tunnel" in fake_stage_b_tools.events


def test_runner_fails_closed_if_refreshed_noindex_check_fails_after_cleanup(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    fake_stage_b_tools.failure_stage = "fresh-noindex"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    events = fake_stage_b_tools.events
    assert events.count("verify-source-noindex") == 2
    assert events.index("drop-role") < events.index("verify-role-absent")
    assert events.index("close-tunnel") < events.index("verify-tunnel-absent")
    assert events.index("verify-role-absent") < events.index("verify-source-noindex", 1)
    assert events.index("verify-tunnel-absent") < events.index("verify-source-noindex", 1)
    assert events[-1] == "verify-source-noindex"
    assert "write-attestation" not in events
    assert not ({"apply", "rollback", "export", "deploy"} & set(events))


def test_runner_normalizes_restore_listing_to_lf_before_hashing() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "`r`n" not in source
    assert "-replace" in source or "\\r\\n?" in source


def test_runner_rejects_dirty_fake_git_worktree(fake_stage_b_tools, tmp_path: Path) -> None:
    fake_stage_b_tools.failure_stage = "dirty-worktree"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert fake_stage_b_tools.events == []


def test_runner_fails_closed_when_fake_git_fails(fake_stage_b_tools, tmp_path: Path) -> None:
    fake_stage_b_tools.failure_stage = "git"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert fake_stage_b_tools.events == []


def test_runner_rejects_noindex_attribute_order_and_conflicting_meta(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    fake_stage_b_tools.noindex_variant = "conflict"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert "create-root" not in fake_stage_b_tools.events


def test_runner_accepts_single_noindex_meta_with_content_before_name(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    fake_stage_b_tools.noindex_variant = "order"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode == 0, result.stderr


def test_runner_rejects_non_exact_robots_meta_value(fake_stage_b_tools, tmp_path: Path) -> None:
    fake_stage_b_tools.noindex_variant = "padded"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert "create-root" not in fake_stage_b_tools.events


def test_test_mode_rejects_artifact_parent_outside_pytest_root(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    env = os.environ.copy()
    env.update(
        {
            "VL360_STAGE_B_TEST_MODE": "1",
            "VL360_STAGE_B_TEST_ROOT": str(fake_stage_b_tools.root),
            "VL360_STAGE_B_FAKE_TOOLS_DIR": str(fake_stage_b_tools.tools),
            "VL360_STAGE_B_EVENT_LOG": str(fake_stage_b_tools.events_path),
        }
    )
    result = _run_script(env, "-ArtifactParent", str(tmp_path / "outside"))
    assert result.returncode != 0
    assert fake_stage_b_tools.events == []


def test_test_mode_rejects_reparse_fake_tool_ancestor(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    target = fake_stage_b_tools.root / "real-tools"
    fake_stage_b_tools.tools.rename(target)
    link = fake_stage_b_tools.root / "tools-link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Windows symlink creation unavailable: {exc}")
    env = os.environ.copy()
    env.update(
        {
            "VL360_STAGE_B_TEST_MODE": "1",
            "VL360_STAGE_B_TEST_ROOT": str(fake_stage_b_tools.root),
            "VL360_STAGE_B_FAKE_TOOLS_DIR": str(link),
            "VL360_STAGE_B_EVENT_LOG": str(fake_stage_b_tools.events_path),
        }
    )
    result = _run_script(env, "-ArtifactParent", str(fake_stage_b_tools.root / "artifacts"))
    assert result.returncode != 0


def test_runner_binds_identity_v2_and_rejects_server_drift(fake_stage_b_tools, tmp_path: Path) -> None:
    fake_stage_b_tools.identity_variant = "wrong-port"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert "backup" not in fake_stage_b_tools.events


@pytest.mark.parametrize("identity_variant", ["backup-string-oid", "plan-string-port"])
def test_runner_rejects_noncanonical_artifact_identity_types(
    fake_stage_b_tools, tmp_path: Path, identity_variant: str
) -> None:
    fake_stage_b_tools.identity_variant = identity_variant
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    if identity_variant.startswith("backup"):
        assert "plan" not in fake_stage_b_tools.events
    else:
        assert "pg-restore-list" not in fake_stage_b_tools.events


def test_cleanup_is_idempotent_when_role_is_already_absent(fake_stage_b_tools, tmp_path: Path) -> None:
    fake_stage_b_tools.failure_stage = "role-already-absent"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("role_check_variant", "should_succeed"),
    [("canonical", True), ("aligned", False), ("malformed", False), ("nonzero", False)],
)
def test_cleanup_requires_canonical_role_absence_count(
    fake_stage_b_tools, tmp_path: Path, role_check_variant: str, should_succeed: bool
) -> None:
    fake_stage_b_tools.role_check_variant = role_check_variant
    result = fake_stage_b_tools.run(tmp_path)

    assert (result.returncode == 0) is should_succeed, result.stderr
    role_check = next(
        record for record in fake_stage_b_tools.records if record["event"] == "verify-role-absent"
    )
    assert role_check["arguments"][-2:] == ["--tuples-only", "--no-align"]
    assert ("write-attestation" in fake_stage_b_tools.events) is should_succeed


def test_runner_secret_and_sql_are_absent_from_fake_argv_and_event_log(
    fake_stage_b_tools, tmp_path: Path
) -> None:
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert fake_stage_b_tools.password not in fake_stage_b_tools.log_text
    assert "postgresql://" not in fake_stage_b_tools.log_text
    assert "CREATE ROLE" not in fake_stage_b_tools.log_text
    for record in fake_stage_b_tools.records:
        assert fake_stage_b_tools.password not in json.dumps(record)
        assert "postgresql://" not in json.dumps(record)
        assert "CREATE ROLE" not in json.dumps(record)


class FakeStageBTools:
    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "pytest-owned"
        self.root.mkdir()
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.events_path = self.root / "events.jsonl"
        self.failure_stage = ""
        self.secret_capture = self.root / "secret.capture"
        self.password = ""
        self.noindex_variant = "normal"
        self.identity_variant = "normal"
        self.role_check_variant = "canonical"
        self.process_timeout_ms = ""
        self._make_dispatcher()

    def _make_dispatcher(self) -> None:
        dispatcher = r'''
param([string]$Invocation)
$event = $env:VL360_STAGE_B_FAKE_EVENT
$log = $env:VL360_STAGE_B_EVENT_LOG
$urlCapture = "$($env:VL360_STAGE_B_SECRET_CAPTURE).url"
$invocationObject = if ($Invocation) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Invocation)) | ConvertFrom-Json } else { @{tool="unknown";arguments=@()} }
$stdin = [Console]::In.ReadToEnd()
$stdinHash = if ($stdin) { (([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($stdin)) | ForEach-Object ToString x2) -join "") } else { "" }
$failureStages = @($env:VL360_STAGE_B_FAILURE_STAGE -split ',' | Where-Object { $_ })
$record = [ordered]@{
  event=$event; tool=$invocationObject.tool; arguments=@($invocationObject.arguments)
  stdin_length=$stdin.Length; stdin_sha256=$stdinHash
  pg_environment=@{PGHOST=$env:PGHOST;PGPORT=$env:PGPORT;PGDATABASE=$env:PGDATABASE}
  pg_password_present=[bool](-not [string]::IsNullOrEmpty($env:PGPASSWORD))
  named_database_url_present=[bool](-not [string]::IsNullOrEmpty($env:VL360_STAGE_B_DATABASE_URL))
  named_database_url_matches_generated=if ($event -in @("backup","plan") -and (Test-Path -LiteralPath $urlCapture)) { $env:VL360_STAGE_B_DATABASE_URL -ceq [IO.File]::ReadAllText($urlCapture) } else { $null }
  generic_database_url_present=[bool](-not [string]::IsNullOrEmpty($env:DATABASE_URL))
  ambient_pg_options_present=[bool](-not [string]::IsNullOrEmpty($env:PGOPTIONS))
  pg_password_matches_role_sql=if ($event -eq "verify-readonly-identity" -and (Test-Path -LiteralPath $env:VL360_STAGE_B_SECRET_CAPTURE)) { $env:PGPASSWORD -ceq [IO.File]::ReadAllText($env:VL360_STAGE_B_SECRET_CAPTURE) } else { $null }
}
if ($event) { Add-Content -LiteralPath $log -Value ($record | ConvertTo-Json -Compress -Depth 8) }
if ($event -eq "create-role" -and $stdin -match "\\set stage_b_password '([^']+)'") {
  $capturedPassword = $Matches[1]
  [IO.File]::WriteAllText($env:VL360_STAGE_B_SECRET_CAPTURE, $capturedPassword)
  if ($stdin -match 'CREATE ROLE "([^"]+)"') {
    $expectedUrl = "postgresql://$($Matches[1]):$([Uri]::EscapeDataString($capturedPassword))@127.0.0.1:15432/vinhlong360"
    [IO.File]::WriteAllText($urlCapture, $expectedUrl)
  }
}
if ($event -in $failureStages -or ("noindex" -in $failureStages -and $event -eq "verify-source-noindex")) { exit 17 }
if ("fresh-noindex" -in $failureStages -and $event -eq "verify-source-noindex") {
  $noindexCount = @(
    Get-Content -LiteralPath $log |
      ForEach-Object { $_ | ConvertFrom-Json } |
      Where-Object { $_.event -eq "verify-source-noindex" }
  ).Count
  if ($noindexCount -ge 2) { exit 17 }
}
if ("timeout" -in $failureStages -and $event -eq "plan") {
  $chunk = "x" * 1048576
  [Console]::Out.Write($chunk)
  [Console]::Error.Write($chunk)
  Start-Sleep -Seconds 30
}
if ("dirty-worktree" -in $failureStages -and $event -eq "git-status") { Write-Output " M dirty"; exit 0 }
if ("git" -in $failureStages -and $event -like "git-*") { exit 17 }
if ("role-already-absent" -in $failureStages -and $event -eq "drop-role" -and ($stdin -notmatch "\\if :stage_b_role_exists" -or $stdin -notmatch "DROP ROLE IF EXISTS")) { exit 17 }
$root = [Environment]::GetEnvironmentVariable("VL360_STAGE_B_FAKE_ROOT")
if ($event -eq "create-root") {
  New-Item -ItemType Directory -Force -Path $root | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $root "backup") | Out-Null
}
if ($event -eq "backup") {
  $run = Join-Path $root "backup/20260716-120000"
  New-Item -ItemType Directory -Force -Path $run | Out-Null
  $listing = "1; 10 10 TABLE public entities`n"
  [IO.File]::WriteAllText((Join-Path $run "postgres.dump"), "dump")
  $hash = [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($listing)) | ForEach-Object ToString x2
  $identity = @{identity_revision="postgres-cluster-v2";database="vinhlong360";database_oid=16384;system_identifier="123456789";server_addr="127.0.0.1";server_port=5432;server_version_num=160004}
  if ($env:VL360_STAGE_B_IDENTITY_VARIANT -eq "backup-string-oid") { $identity.database_oid = "16384" }
  $manifest = @{validation=@{listing_sha256=($hash -join "")}; artifact=@{path="postgres.dump"}; database_identity=$identity}
  $manifest | ConvertTo-Json -Compress | Set-Content -NoNewline (Join-Path $run "manifest.json")
}
if ($event -eq "plan") {
  $identity = @{identity_revision="postgres-cluster-v2";database="vinhlong360";database_oid=16384;system_identifier="123456789";server_addr="127.0.0.1";server_port=5432;server_version_num=160004}
  if ($env:VL360_STAGE_B_IDENTITY_VARIANT -eq "plan-string-port") { $identity.server_port = "5432" }
  @{tool_source_revision=""; schema="vinhlong360-entity-status-plan-v1"; database_identity=$identity} | ConvertTo-Json -Compress | Set-Content -NoNewline (Join-Path $root "published-v1-plan.json")
}
if ($event -eq "pg-restore-list") { [Console]::Out.Write("1; 10 10 TABLE public entities`r`n") }
if ($event -eq "write-attestation") {
  [IO.File]::WriteAllText((Join-Path $root "stage-b-attestation.json"), '{"ok":true}')
}
if ($event -eq "verify-source-noindex") {
  $body = switch ($env:VL360_STAGE_B_NOINDEX_VARIANT) {
    "conflict" { '<html><head><meta content="noindex, follow" name="robots"><meta name="robots" content="index, follow"></head></html>' }
    "order" { '<html><head><meta content="noindex, follow" name="robots"></head></html>' }
    "padded" { '<html><head><meta name="robots" content=" noindex, follow "></head></html>' }
    default { '<html><head><meta name="robots" content="noindex, follow"></head></html>' }
  }
  @{status=200;x_robots_tag="noindex, follow";body=$body} | ConvertTo-Json -Compress
}
if ($event -eq "git-head") { Write-Output "b6c4854b33d0c7548e5913ad6f0853b58d97e405" }
if ($event -eq "git-status") { }
if ($event -eq "verify-readonly-identity") {
  $port = if ($env:VL360_STAGE_B_IDENTITY_VARIANT -eq "wrong-port") { "5433" } else { "5432" }
  Write-Output "vinhlong360|16384|123456789|127.0.0.1|$port|160004|on|$($env:PGUSER)"
}
if ($event -eq "verify-role-absent") {
  switch ($env:VL360_STAGE_B_ROLE_CHECK_VARIANT) {
    "aligned" { [Console]::Out.Write(" count`n-------`n     0`n(1 row)`n") }
    "malformed" { [Console]::Out.Write("0`n1`n") }
    "nonzero" { [Console]::Out.Write("1`n") }
    default { [Console]::Out.Write("0`n") }
  }
}
'''
        path = self.tools / "fake.ps1"
        path.write_text(dispatcher, encoding="utf-8")
        self.fake = path

    @property
    def events(self) -> list[str]:
        if not self.events_path.exists():
            return []
        return [record["event"] for record in self.records if record["event"] not in {"git-head", "git-status"}]

    @property
    def records(self) -> list[dict[str, object]]:
        if not self.events_path.exists():
            return []
        return [json.loads(line) for line in self.events_path.read_text().splitlines() if line.strip()]

    @property
    def log_text(self) -> str:
        return self.events_path.read_text() if self.events_path.exists() else ""

    def run(self, tmp_path: Path, timeout: float = 120) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "VL360_STAGE_B_TEST_MODE": "1",
                "VL360_STAGE_B_TEST_ROOT": str(self.root),
                "VL360_STAGE_B_FAKE_TOOLS_DIR": str(self.tools),
                "VL360_STAGE_B_EVENT_LOG": str(self.events_path),
                "VL360_STAGE_B_FAKE_ROOT": str(self.root / "artifacts"),
                "VL360_STAGE_B_FAILURE_STAGE": self.failure_stage,
                "VL360_STAGE_B_NOINDEX_VARIANT": self.noindex_variant,
                "VL360_STAGE_B_IDENTITY_VARIANT": self.identity_variant,
                "VL360_STAGE_B_ROLE_CHECK_VARIANT": self.role_check_variant,
                "VL360_STAGE_B_SECRET_CAPTURE": str(self.secret_capture),
            }
        )
        if self.process_timeout_ms:
            env["VL360_STAGE_B_PROCESS_TIMEOUT_MS"] = self.process_timeout_ms
        result = _run_script(
            env,
            "-ArtifactParent",
            str(self.root / "artifacts-parent"),
            timeout=timeout,
        )
        if self.secret_capture.exists():
            self.password = self.secret_capture.read_text()
            self.secret_capture.unlink()
        return result


@pytest.fixture
def fake_stage_b_tools(tmp_path: Path) -> FakeStageBTools:
    return FakeStageBTools(tmp_path)


def test_runner_cleanup_executes_when_plan_fails(fake_stage_b_tools: FakeStageBTools, tmp_path: Path) -> None:
    fake_stage_b_tools.failure_stage = "plan"
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode != 0
    assert fake_stage_b_tools.events == [
        "verify-source-noindex",
        "create-root",
        "create-role",
        "open-tunnel",
        "verify-tunnel-ready",
        "verify-readonly-identity",
        "verify-tunnel-ready",
        "verify-tunnel-ready",
        "backup",
        "verify-tunnel-ready",
        "verify-tunnel-ready",
        "plan",
        "drop-role",
        "close-tunnel",
        "verify-role-absent",
        "verify-tunnel-absent",
    ]
    assert not list(tmp_path.rglob("stage-b-attestation.json"))


@pytest.mark.parametrize(
    ("main_stage", "cleanup_stage", "main_error"),
    [
        ("backup", "drop-role", "backup failed (exit 17)"),
        ("backup", "close-tunnel", "backup failed (exit 17)"),
        ("plan", "verify-role-absent", "plan failed (exit 17)"),
        ("plan", "verify-tunnel-absent", "plan failed (exit 17)"),
    ],
)
def test_runner_reports_main_and_mandatory_cleanup_failures(
    fake_stage_b_tools: FakeStageBTools,
    tmp_path: Path,
    main_stage: str,
    cleanup_stage: str,
    main_error: str,
) -> None:
    fake_stage_b_tools.failure_stage = f"{main_stage},{cleanup_stage}"
    result = fake_stage_b_tools.run(tmp_path)
    combined = result.stdout + result.stderr + fake_stage_b_tools.log_text
    assert result.returncode != 0
    assert f"ERROR: {main_error}" in result.stderr
    assert "ERROR: mandatory cleanup failed" in result.stderr
    assert fake_stage_b_tools.password not in combined
    assert "postgresql://" not in combined
    assert "CREATE ROLE" not in combined
    assert not ({"apply", "rollback", "export", "deploy"} & set(fake_stage_b_tools.events))


@pytest.mark.parametrize(
    ("failure_stage", "attestation_expected"),
    [
        ("noindex", False),
        ("create-role", False),
        ("occupied-port", False),
        ("open-tunnel", False),
        ("backup", False),
        ("plan", False),
        ("drop-role", False),
        ("close-tunnel", False),
        ("write-attestation", True),
    ],
)
def test_runner_failure_matrix_is_cleanup_first_and_never_runs_stage_c(
    fake_stage_b_tools: FakeStageBTools,
    tmp_path: Path,
    failure_stage: str,
    attestation_expected: bool,
) -> None:
    fake_stage_b_tools.failure_stage = failure_stage
    result = fake_stage_b_tools.run(tmp_path)
    combined = result.stdout + result.stderr + fake_stage_b_tools.log_text
    assert result.returncode != 0
    assert ("write-attestation" in fake_stage_b_tools.events) is attestation_expected
    assert not ({"apply", "rollback", "export", "deploy"} & set(fake_stage_b_tools.events))
    if fake_stage_b_tools.password:
        assert fake_stage_b_tools.password not in combined
    if "create-role" in fake_stage_b_tools.events:
        assert "drop-role" in fake_stage_b_tools.events
    if "open-tunnel" in fake_stage_b_tools.events:
        assert "close-tunnel" in fake_stage_b_tools.events


def test_success_prints_only_non_secret_hashes(fake_stage_b_tools: FakeStageBTools, tmp_path: Path) -> None:
    result = fake_stage_b_tools.run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "APPLY_NOT_RUN" in result.stdout
    assert "password" not in result.stdout.lower()
    assert hashlib.sha256(b"x").hexdigest() not in result.stdout
