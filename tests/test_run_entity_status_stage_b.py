from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_entity_status_stage_b.ps1"


def _run_script(env: dict[str, str], *extra: str) -> subprocess.CompletedProcess[str]:
    command = [
        "pwsh",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(SCRIPT),
        *extra,
    ]
    return subprocess.run(command, capture_output=True, text=True, env=env, check=False)


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


class FakeStageBTools:
    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "pytest-owned"
        self.root.mkdir()
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.events_path = self.root / "events.jsonl"
        self.failure_stage = ""
        self.password = "password-marker"  # marker used by secrecy assertions
        self._make_dispatcher()

    def _make_dispatcher(self) -> None:
        dispatcher = r'''
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
$event = $env:VL360_STAGE_B_FAKE_EVENT
$log = $env:VL360_STAGE_B_EVENT_LOG
if ($event) { Add-Content -LiteralPath $log -Value $event }
if ($env:VL360_STAGE_B_FAILURE_STAGE -eq $event -or ($env:VL360_STAGE_B_FAILURE_STAGE -eq "noindex" -and $event -eq "verify-source-noindex")) { exit 17 }
$root = [Environment]::GetEnvironmentVariable("VL360_STAGE_B_FAKE_ROOT")
if ($event -eq "create-root") {
  New-Item -ItemType Directory -Force -Path $root | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $root "backup") | Out-Null
}
if ($event -eq "backup") {
  $run = Join-Path $root "backup/20260716-120000"
  New-Item -ItemType Directory -Force -Path $run | Out-Null
  $listing = "1; 10 10 TABLE public entities`r`n"
  [IO.File]::WriteAllText((Join-Path $run "postgres.dump"), "dump")
  $hash = [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($listing)) | ForEach-Object ToString x2
  $manifest = @{validation=@{listing_sha256=($hash -join "")}; artifact=@{path="postgres.dump"}}
  $manifest | ConvertTo-Json -Compress | Set-Content -NoNewline (Join-Path $run "manifest.json")
}
if ($event -eq "plan") {
  @{tool_source_revision=""; schema="vinhlong360-entity-status-plan-v1"} | ConvertTo-Json -Compress | Set-Content -NoNewline (Join-Path $root "published-v1-plan.json")
}
if ($event -eq "pg-restore-list") { [Console]::Out.Write("1; 10 10 TABLE public entities`r`n") }
if ($event -eq "write-attestation") {
  [IO.File]::WriteAllText((Join-Path $root "stage-b-attestation.json"), '{"ok":true}')
}
if ($event -eq "verify-source-noindex") {
  @{status=200;x_robots_tag="noindex, follow";robots_meta_count=1;robots_meta_value="noindex, follow";body='<html><head><meta name="robots" content="noindex, follow"></head></html>'} | ConvertTo-Json -Compress
}
if ($event -eq "git-head") { Write-Output "eb956fa000000000000000000000000000000000" }
if ($event -eq "git-status") { }
'''
        path = self.tools / "fake.ps1"
        path.write_text(dispatcher, encoding="utf-8")
        self.fake = path

    @property
    def events(self) -> list[str]:
        if not self.events_path.exists():
            return []
        return [line.strip() for line in self.events_path.read_text().splitlines() if line.strip()]

    @property
    def log_text(self) -> str:
        return self.events_path.read_text() if self.events_path.exists() else ""

    def run(self, tmp_path: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "VL360_STAGE_B_TEST_MODE": "1",
                "VL360_STAGE_B_TEST_ROOT": str(self.root),
                "VL360_STAGE_B_FAKE_TOOLS_DIR": str(self.tools),
                "VL360_STAGE_B_EVENT_LOG": str(self.events_path),
                "VL360_STAGE_B_FAKE_ROOT": str(tmp_path / "artifacts"),
                "VL360_STAGE_B_FAILURE_STAGE": self.failure_stage,
            }
        )
        return _run_script(env, "-ArtifactParent", str(tmp_path / "artifacts-parent"))


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
        "verify-readonly-identity",
        "backup",
        "plan",
        "drop-role",
        "close-tunnel",
        "verify-role-absent",
        "verify-tunnel-absent",
    ]
    assert not list(tmp_path.rglob("stage-b-attestation.json"))


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
