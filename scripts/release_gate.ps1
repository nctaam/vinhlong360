param(
  [string]$Python = "python",
  [string]$Node = "node",
  [switch]$SkipBackend,
  [switch]$SkipFrontend,
  [switch]$SkipData,
  [switch]$RunAuthCheck,
  [switch]$RequireAuthCheck,
  [switch]$RunE2E,
  [switch]$RequireE2E,
  [switch]$RunLaunchSafetyDockerOptIn,
  [switch]$RunLaunchSafetyBrowserOptIn,
  [switch]$RenderLaunchSafetyFinalEvidence,
  [string]$LaunchSafetyEvidenceState = "",
  [string]$LaunchSafetyEvidenceOutput = "",
  [string]$SmokeBaseUrl = "",
  [string]$SmokeApiBaseUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
. (Join-Path $Root "scripts/ops/release_gate_harness.ps1")
$Script:Failures = 0
$Script:Warnings = 0
$Script:LaunchSafetyEvidenceEnabled = $false
$Script:LaunchSafetyRevision = ""
$Script:LaunchSafetyEvidenceOutputPath = ""
$Script:LaunchSafetyEvidenceStateOwned = $false
$Script:LaunchSafetyOptInExit = 0

if (-not $LaunchSafetyEvidenceState -and $env:LAUNCH_SAFETY_EVIDENCE_STATE) {
  $LaunchSafetyEvidenceState = $env:LAUNCH_SAFETY_EVIDENCE_STATE
}

$Script:LaunchSafetyEvidenceEnabled = [bool]($LaunchSafetyEvidenceState -or
  $RunLaunchSafetyDockerOptIn -or $RunLaunchSafetyBrowserOptIn -or
  $RenderLaunchSafetyFinalEvidence)
$Script:LaunchSafetyEvidenceStateOwned = $false
if ($Script:LaunchSafetyEvidenceEnabled -and -not $LaunchSafetyEvidenceState) {
  $LaunchSafetyEvidenceState = Join-Path ([System.IO.Path]::GetTempPath()) `
    ("vinhlong360-launch-safety-evidence-" + [guid]::NewGuid().ToString("N") + ".json")
  $Script:LaunchSafetyEvidenceStateOwned = $true
}
$Script:LaunchSafetyEvidenceOutputPath = if ($LaunchSafetyEvidenceOutput) {
  $LaunchSafetyEvidenceOutput
} else {
  Join-Path $Root "docs/superpowers/results/2026-07-20-launch-safety-gate-evidence.md"
}

if ($RequireAuthCheck) { $RunAuthCheck = $true }
if ($RequireE2E) { $RunE2E = $true }

function Write-Step {
  param([string]$Status, [string]$Name, [string]$Detail = "")
  $suffix = if ($Detail) { " - $Detail" } else { "" }
  Write-Host "[$Status] $Name$suffix"
}

function Invoke-GateStep {
  param([string]$Name, [scriptblock]$Block)
  Write-Step "RUN" $Name
  try {
    & $Block
    Write-Step "OK" $Name
  } catch {
    $Script:Failures++
    Write-Step "FAIL" $Name $_.Exception.Message
  }
}

function Invoke-GateWarning {
  param([string]$Name, [string]$Detail)
  $Script:Warnings++
  Write-Step "WARN" $Name $Detail
}

function Invoke-Native {
  param(
    [string]$File,
    [string[]]$Arguments,
    [string]$WorkingDirectory = $Root
  )
  Push-Location $WorkingDirectory
  try {
    & $File @Arguments
    $code = $LASTEXITCODE
    if ($code -ne 0) {
      $errorRecord = [System.Exception]::new(
        "$File $($Arguments -join ' ') exited with code $code"
      )
      $errorRecord.Data["ExitCode"] = [int]$code
      throw $errorRecord
    }
  } finally {
    Pop-Location
  }
}

function Invoke-NativeAllowWarning {
  param(
    [string]$Name,
    [string]$File,
    [string[]]$Arguments,
    [int[]]$WarningExitCodes = @(2),
    [string]$WorkingDirectory = $Root
  )
  Write-Step "RUN" $Name
  Push-Location $WorkingDirectory
  try {
    & $File @Arguments
    $code = $LASTEXITCODE
    if ($code -eq 0) {
      Write-Step "OK" $Name
    } elseif ($WarningExitCodes -contains $code) {
      if ($RequireAuthCheck) {
        $Script:Failures++
        Write-Step "FAIL" $Name "warning exit code $code is not allowed with -RequireAuthCheck"
      } else {
        Invoke-GateWarning $Name "completed with warning exit code $code"
      }
    } else {
      $Script:Failures++
      Write-Step "FAIL" $Name "$File $($Arguments -join ' ') exited with code $code"
    }
  } finally {
    Pop-Location
  }
}

function Invoke-LaunchSafetyRecord {
  param(
    [Parameter(Mandatory = $true)][string]$Section,
    [Parameter(Mandatory = $true)][ValidateSet("pass", "fail", "skip")][string]$Status,
    [Parameter(Mandatory = $true)][int]$ExitCode,
    [Parameter(Mandatory = $true)][string]$Summary,
    [string]$Command = "launch safety gate"
  )
  $recordArgs = @(
    "scripts/ops/record_launch_evidence.py", "record",
    "--section", $Section, "--status", $Status,
    "--exit-code", [string]$ExitCode, "--summary", $Summary,
    "--command", $Command
  )
  if ($LaunchSafetyEvidenceState) {
    $recordArgs += @("--state", $LaunchSafetyEvidenceState)
  }
  if ($Script:LaunchSafetyRevision) {
    $recordArgs += @("--revision", $Script:LaunchSafetyRevision)
  }
  Push-Location $Root
  try {
    & $Python @recordArgs
    if ($LASTEXITCODE -ne 0) {
      $recordFailure = [System.Exception]::new(
        "failed to record Launch Safety evidence for $Section (exit $LASTEXITCODE)"
      )
      $recordFailure.Data["ExitCode"] = [int]$LASTEXITCODE
      throw $recordFailure
    }
  } finally {
    Pop-Location
  }
}

function Invoke-RecordedLaunchSafetySection {
  param(
    [Parameter(Mandatory = $true)][string]$Section,
    [Parameter(Mandatory = $true)][string]$Command,
    [Parameter(Mandatory = $true)][scriptblock]$Body
  )
  Write-Step "RUN" "Launch Safety evidence: $Section"
  $exitCode = 0
  $summary = "passed"
  try {
    Push-Location $Root
    try { & $Body } finally { Pop-Location }
    Write-Step "OK" "Launch Safety evidence: $Section"
  } catch {
    $exitCode = if ($_.Exception.Data.Contains("ExitCode")) {
      [int]$_.Exception.Data["ExitCode"]
    } else { 1 }
    $summary = $_.Exception.Message
    $Script:Failures++
    Write-Step "FAIL" "Launch Safety evidence: $Section" $summary
  }
  try {
    $status = if ($exitCode -eq 0) { "pass" } else { "fail" }
    Invoke-LaunchSafetyRecord $Section $status $exitCode $summary $Command
  } catch {
    $Script:Failures++
    Write-Step "FAIL" "Launch Safety evidence recorder: $Section" $_.Exception.Message
  }
}

function Resolve-LaunchSafetyRevision {
  Push-Location $Root
  try {
    $revisionOutput = @(& git rev-parse HEAD)
    $revisionExit = $LASTEXITCODE
    $revision = if ($revisionOutput.Count -gt 0) {
      ([string]$revisionOutput[0]).Trim()
    } else { "" }
    if ($revisionExit -ne 0 -or [string]::IsNullOrWhiteSpace($revision)) {
      throw "unable to resolve clean-head revision"
    }
    return [string]$revision
  } finally {
    Pop-Location
  }
}

function Invoke-LaunchSafetyRequiredEvidence {
  if (-not $Script:LaunchSafetyEvidenceEnabled) { return }
  $Script:LaunchSafetyRevision = Resolve-LaunchSafetyRevision

  Invoke-RecordedLaunchSafetySection "artifacts" `
    "pytest launch artifacts and release package" {
      Invoke-Native $Python @(
        "-m", "pytest",
        "agent/tests/test_launch_artifacts.py",
        "tests/launch_safety/test_route_manifest_artifact.py",
        "tests/launch_safety/test_ai_disclosure_artifact.py",
        "tests/launch_safety/test_release_package.py",
        "-q"
      )
    }

  Invoke-RecordedLaunchSafetySection "backend-focused" `
    "pytest launch-safety backend focused matrix" {
      Invoke-Native $Python @(
        "-m", "pytest",
        "tests/launch_safety/test_backend_regression_runner.py",
        "tests/launch_safety/test_evidence_record.py",
        "tests/launch_safety/test_browser_probe_contract.py",
        "tests/launch_safety/test_launch_matrix_contract.py",
        "agent/tests/test_launch_artifacts.py",
        "agent/tests/test_route_manifest.py",
        "agent/tests/test_ai_disclosure.py",
        "agent/tests/test_index_policy.py",
        "agent/tests/test_public_index_policy.py",
        "agent/tests/test_policy_http.py",
        "agent/tests/test_launch_policy_api.py",
        "agent/tests/test_sitemap_snapshot.py",
        "agent/tests/test_sitemap_render.py",
        "agent/tests/test_sitemap_store.py",
        "agent/tests/test_sitemap_bundle.py",
        "agent/tests/test_image_descriptor.py",
        "agent/tests/test_image_metadata_disclosure.py",
        "-q"
      )
    }

  Invoke-RecordedLaunchSafetySection "frontend-focused" `
    "npm test launch-safety focused matrix" {
      $webDir = Join-Path $Root "web-nuxt"
      Invoke-Native "npx" @(
        "vitest", "run",
        "tests/launch-route-manifest.test.ts",
        "tests/launch-safety-decision.test.ts",
        "tests/launch-root-seo.test.ts",
        "tests/launch-readiness.test.ts",
        "tests/image-renderer-inventory.test.ts",
        "tests/image-metadata-disclosure.test.ts",
        "--testTimeout=30000", "--hookTimeout=30000"
      ) $webDir
    }

  $bashAuthority = Resolve-LaunchSafetyBash
  if ($null -eq $bashAuthority) {
    $bashSkipReason = "bash-interpreter-unavailable"
    Write-Step "SKIP" "Launch Safety evidence: rollback-local-rehearsal" $bashSkipReason
    Invoke-LaunchSafetyRecord "rollback-local-rehearsal" "skip" 0 `
      $bashSkipReason "bash scripts/ops/rehearse_launch_rollback.sh --local-rehearsal"
    $Script:Failures++
  } else {
    Invoke-RecordedLaunchSafetySection "rollback-local-rehearsal" `
      "$bashAuthority scripts/ops/rehearse_launch_rollback.sh --local-rehearsal" {
        & $bashAuthority "scripts/ops/rehearse_launch_rollback.sh" "--local-rehearsal"
        if ($LASTEXITCODE -ne 0) {
          $errorRecord = [System.Exception]::new("rollback rehearsal failed")
          $errorRecord.Data["ExitCode"] = [int]$LASTEXITCODE
          throw $errorRecord
        }
      }
  }

  Invoke-RecordedLaunchSafetySection "backend-full-regression" `
    "python scripts/ops/run_backend_regression.py --deadline-seconds 7000" {
      Invoke-Native $Python @(
        "scripts/ops/run_backend_regression.py",
        "--deadline-seconds", "7000"
      )
    }

  Invoke-RecordedLaunchSafetySection "frontend-serial-regression" `
    "npm test -- --no-file-parallelism --maxWorkers=1; npm run typecheck; npm run build" {
      $webDir = Join-Path $Root "web-nuxt"
      Invoke-Native "npm" @(
        "test", "--", "--no-file-parallelism", "--maxWorkers=1",
        "--testTimeout=30000", "--hookTimeout=30000"
      ) $webDir
      Invoke-Native "npm" @("run", "typecheck") $webDir
      Invoke-Native "npm" @("run", "build") $webDir
    }

  Invoke-RecordedLaunchSafetySection "source-scans" `
    "hard checks, quality gates, PowerShell harness, git diff --check" {
      Invoke-Native $Python @("scripts/checks/run_hard.py", "--all")
      Invoke-Native $Python @(
        "-m", "pytest", "tests/checks/test_hard_checks.py",
        "tests/test_release_quality_gates.py", "-q"
      )
      $powershell = Get-Command pwsh,powershell -ErrorAction Stop |
        Select-Object -First 1
      if ($null -eq $powershell -or [string]::IsNullOrWhiteSpace([string]$powershell.Source)) {
        throw "PowerShell executable unavailable"
      }
      & $powershell.Source -NoProfile -File `
        (Join-Path $Root "tests/launch_safety/powershell/test_release_gate_harness.ps1")
      if ($LASTEXITCODE -ne 0) {
        $errorRecord = [System.Exception]::new("PowerShell harness contract failed")
        $errorRecord.Data["ExitCode"] = [int]$LASTEXITCODE
        throw $errorRecord
      }
      & git diff --check
      if ($LASTEXITCODE -ne 0) {
        $errorRecord = [System.Exception]::new("git diff --check failed")
        $errorRecord.Data["ExitCode"] = [int]$LASTEXITCODE
        throw $errorRecord
      }
    }

  Invoke-LaunchSafetyRecord "known-resource-timeout" "skip" 0 `
    "known parallel frontend/backend resource timeout; functional expectations unchanged" `
    "parallel resource baseline"
  Invoke-LaunchSafetyRecord "external-gates" "skip" 0 `
    "H1=blocked; H2=blocked; owner=not-authorized" "external launch gates"
}

function Assert-LaunchSafetyCleanHead {
  Push-Location $Root
  try {
    $dirty = @(& git status --porcelain --untracked-files=all)
    if ($LASTEXITCODE -ne 0) { throw "unable to inspect worktree status" }
    if ($dirty.Count -gt 0) {
      throw "worktree-not-clean"
    }
  } finally {
    Pop-Location
  }
}

function Set-LaunchSafetyOptInExit {
  param([int]$ExitCode)
  if ($ExitCode -ne 0 -and $Script:LaunchSafetyOptInExit -eq 0) {
    $Script:LaunchSafetyOptInExit = [int]$ExitCode
  }
}

function Invoke-LaunchSafetyOptIns {
  if (-not $RunLaunchSafetyDockerOptIn -and -not $RunLaunchSafetyBrowserOptIn) {
    if ($Script:LaunchSafetyEvidenceEnabled) {
      Invoke-LaunchSafetyRecord "postgres-opt-in" "skip" 0 "not-requested" "docker opt-in"
      Invoke-LaunchSafetyRecord "compose-nginx-opt-in" "skip" 0 "not-requested" "docker opt-in"
      Invoke-LaunchSafetyRecord "browser-opt-in" "skip" 0 "not-requested" "browser opt-in"
    }
    return
  }
  if (-not $RunLaunchSafetyDockerOptIn -and $Script:LaunchSafetyEvidenceEnabled) {
    Invoke-LaunchSafetyRecord "postgres-opt-in" "skip" 0 "not-requested" "docker opt-in"
    Invoke-LaunchSafetyRecord "compose-nginx-opt-in" "skip" 0 "not-requested" "docker opt-in"
  }
  if (-not $RunLaunchSafetyBrowserOptIn -and $Script:LaunchSafetyEvidenceEnabled) {
    Invoke-LaunchSafetyRecord "browser-opt-in" "skip" 0 "not-requested" "browser opt-in"
  }
  if ($Script:Failures -gt 0) {
    Write-Step "SKIP" "Launch Safety opt-ins" "default release gate has failures"
    return
  }

  if ($RunLaunchSafetyDockerOptIn) {
    Write-Step "RUN" "Launch Safety Docker opt-in"
    try {
      try {
        Assert-LaunchSafetyCleanHead
      } catch {
        Invoke-LaunchSafetyRecord "postgres-opt-in" "fail" 1 $_.Exception.Message "git status --porcelain --untracked-files=all"
        Invoke-LaunchSafetyRecord "compose-nginx-opt-in" "fail" 1 $_.Exception.Message "git status --porcelain --untracked-files=all"
        throw "Launch Safety Docker opt-in requires a clean worktree"
      }
      $dockerReason = $null
      if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $dockerReason = "docker-cli-unavailable"
      } else {
        & docker info *> $null
        if ($LASTEXITCODE -ne 0) { $dockerReason = "docker-daemon-unavailable" }
      }
      if ($dockerReason) {
        Invoke-LaunchSafetyRecord "postgres-opt-in" "skip" 0 $dockerReason "docker info"
        Invoke-LaunchSafetyRecord "compose-nginx-opt-in" "skip" 0 $dockerReason "docker info"
        Write-Step "SKIP" "Launch Safety Docker opt-in" $dockerReason
      } else {
        . (Join-Path $Root "scripts/ops/release_gate_harness.ps1")
        $postgresCompose = Join-Path $Root "tests/launch_safety/harness/docker-compose.postgres.yml"
        if (-not (Test-Path -LiteralPath $postgresCompose)) {
          Invoke-LaunchSafetyRecord "postgres-opt-in" "fail" 1 "postgres harness is missing" "docker compose postgres"
          Invoke-LaunchSafetyRecord "compose-nginx-opt-in" "fail" 1 "nginx harness is missing" "pytest launch matrix"
          throw "Launch Safety Docker harness files are missing"
        }
        $postgresResult = @(Invoke-RecordedComposeHarness `
          -Section "postgres-opt-in" `
          -ComposeFile $postgresCompose `
          -EnvironmentNames @("SITEMAP_BUNDLE_TEST_DATABASE_URL") `
          -Python $Python `
          -EvidenceState $LaunchSafetyEvidenceState `
          -Body {
            $env:SITEMAP_BUNDLE_TEST_DATABASE_URL = "postgresql://vl360:vl360_launch_test@127.0.0.1:55432/vl360_launch_test"
            & $Python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q
            if ($LASTEXITCODE -ne 0) {
              $errorRecord = [System.Exception]::new("postgres launch test failed")
              $errorRecord.Data["ExitCode"] = [int]$LASTEXITCODE
              throw $errorRecord
            }
          }
        )
        if ($postgresResult.Count -ne 1 -or $postgresResult[0] -isnot [int]) {
          throw "Launch Safety PostgreSQL harness returned a non-scalar result"
        }
        $postgresExit = [int]$postgresResult[0]
        if ($postgresExit -ne 0) {
          Set-LaunchSafetyOptInExit $postgresExit
          Write-Step "FAIL" "Launch Safety PostgreSQL opt-in" "exited with code $postgresExit"
        }

        $nginxExit = 0
        & $Python -m pytest tests/launch_safety/integration/test_launch_matrix.py tests/launch_safety/integration/test_nginx_boundary.py tests/launch_safety/integration/test_network_boundary.py -m integration -q
        $nginxExit = [int]$LASTEXITCODE
        $nginxStatus = if ($nginxExit -eq 0) { "pass" } else { "fail" }
        Invoke-LaunchSafetyRecord "compose-nginx-opt-in" $nginxStatus $nginxExit "launch matrix integration" "pytest launch matrix"
        if ($nginxExit -ne 0) {
          Set-LaunchSafetyOptInExit $nginxExit
          Write-Step "FAIL" "Launch Safety Nginx opt-in" "exited with code $nginxExit"
        }
        if ($postgresExit -eq 0 -and $nginxExit -eq 0) {
          Write-Step "OK" "Launch Safety Docker opt-in"
        }
      }
    } catch {
      $dockerExit = if ($_.Exception.Data.Contains("ExitCode")) {
        [int]$_.Exception.Data["ExitCode"]
      } else { 1 }
      Set-LaunchSafetyOptInExit $dockerExit
      Write-Step "FAIL" "Launch Safety Docker opt-in" $_.Exception.Message
    }
  }

  if ($RunLaunchSafetyBrowserOptIn) {
    Write-Step "RUN" "Launch Safety browser opt-in"
    $probe = Join-Path $Root "scripts/launch_safety_browser_e2e.mjs"
    if (-not (Test-Path -LiteralPath $probe)) {
      Set-LaunchSafetyOptInExit 1
      Invoke-LaunchSafetyRecord "browser-opt-in" "fail" 1 "browser probe is missing" "node --probe-browser"
      return
    }
    & $Node $probe --probe-browser
    $probeExit = [int]$LASTEXITCODE
    if ($probeExit -eq 3) {
      Invoke-LaunchSafetyRecord "browser-opt-in" "skip" 0 "chrome-unavailable" "node --probe-browser"
      Write-Step "SKIP" "Launch Safety browser opt-in" "chrome-unavailable"
    } elseif ($probeExit -ne 0) {
      Set-LaunchSafetyOptInExit $probeExit
      Invoke-LaunchSafetyRecord "browser-opt-in" "fail" $probeExit "browser probe failed" "node --probe-browser"
      Write-Step "FAIL" "Launch Safety browser opt-in" "browser probe exited with code $probeExit"
    } else {
      . (Join-Path $Root "scripts/ops/release_gate_browser_harness.ps1")
      $browserResult = @(Invoke-LaunchSafetyBrowserHarness `
        -Root $Root `
        -Node $Node `
        -Npm "npm" `
        -RecordEvidence {
          param($Status, $ExitCode, $Summary, $Command)
          Invoke-LaunchSafetyRecord "browser-opt-in" $Status $ExitCode $Summary $Command
          return 0
        }
      )
      if ($browserResult.Count -ne 1 -or $browserResult[0] -isnot [int]) {
        Set-LaunchSafetyOptInExit 1
        Invoke-LaunchSafetyRecord "browser-opt-in" "fail" 1 "browser harness returned a non-scalar result" "npm run smoke:launch-safety"
      } else {
        $browserExit = [int]$browserResult[0]
        Set-LaunchSafetyOptInExit $browserExit
        if ($browserExit -eq 0) {
          Write-Step "OK" "Launch Safety browser opt-in"
        } else {
          Write-Step "FAIL" "Launch Safety browser opt-in" "browser harness exited with code $browserExit"
        }
      }
    }
  }
}

function Invoke-LaunchSafetyFinalRender {
  if (-not $RenderLaunchSafetyFinalEvidence) { return }
  if ($Script:Failures -gt 0) {
    Write-Step "SKIP" "Launch Safety final evidence render" "required gate has failures"
    return
  }
  if ($Script:LaunchSafetyOptInExit -ne 0) {
    Write-Step "SKIP" "Launch Safety final evidence render" "opt-in gate has failures"
    return
  }
  $evidenceOutput = if ([System.IO.Path]::IsPathRooted($Script:LaunchSafetyEvidenceOutputPath)) {
    $Script:LaunchSafetyEvidenceOutputPath
  } else {
    Join-Path $Root $Script:LaunchSafetyEvidenceOutputPath
  }
  $renderArgs = @(
    "scripts/ops/record_launch_evidence.py", "render", "--final",
    "--output", $evidenceOutput
  )
  if ($LaunchSafetyEvidenceState) {
    $renderArgs += @("--state", $LaunchSafetyEvidenceState)
  }
  Push-Location $Root
  try {
    & $Python @renderArgs
    if ($LASTEXITCODE -ne 0) {
      $Script:Failures++
      Write-Step "FAIL" "Launch Safety final evidence render" "recorder exited with code $LASTEXITCODE"
      return
    }
  } finally {
    Pop-Location
  }
  Write-Step "OK" "Launch Safety final evidence render" $evidenceOutput
  if ($Script:LaunchSafetyEvidenceStateOwned) {
    Remove-Item -LiteralPath $LaunchSafetyEvidenceState -Force -ErrorAction SilentlyContinue
  }
}

Write-Host "VinhLong360 release gate"
Write-Host "Root: $Root"
Write-Host ""

if ($RunAuthCheck -or $env:DATABASE_URL) {
  # `pwsh` trước, `powershell` chỉ là dự phòng cho Windows PowerShell 5.x:
  # ghim cứng "powershell" làm gate này chết trên Linux ("The term 'powershell'
  # is not recognized"), và CI đặt DATABASE_URL nên nhánh này LUÔN chạy ở job
  # Postgres. Cùng cách tra lệnh đã dùng ở harness phía trên.
  $authShell = Get-Command pwsh, powershell -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($null -eq $authShell) { throw "khong tim thay pwsh lan powershell" }
  Invoke-NativeAllowWarning "local dev auth check" $authShell.Source @(
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $Root "scripts/dev_auth_check.ps1"),
    "-Python", $Python
  )
} else {
  Write-Step "SKIP" "local dev auth check" "set DATABASE_URL or pass -RunAuthCheck"
}

if (!$SkipBackend) {
  Invoke-GateStep "migration/schema drift gate" {
    $migrationArgs = @("scripts/check_migration_gate.py")
    if ($env:DATABASE_URL) {
      $migrationArgs += "--db-check"
    }
    Invoke-Native $Python $migrationArgs
  }
  Invoke-GateStep "sensitive route guard matrix" {
    Invoke-Native $Python @("scripts/sensitive_route_guard_matrix.py")
  }
  Invoke-GateStep "backend QA fixes" {
    Invoke-Native $Python @("-m", "pytest", "agent/tests/test_qa_fixes.py", "-q")
  }
  Invoke-GateStep "admin cockpit regressions" {
    Invoke-Native $Python @(
      "-m", "pytest",
      "tests/test_admin_p0_regressions.py",
      "tests/test_admin_p1_p2_regressions.py",
      "tests/test_admin_validation.py",
      "-q"
    )
  }
  Invoke-GateStep "backend system/auth guards" {
    Invoke-Native $Python @(
      "-m", "pytest",
      "agent/tests/test_qa_regression.py::TestSystemEndpointGate",
      "agent/tests/test_qa_regression.py::TestHealthEndpointMinimal",
      "agent/tests/test_phase16_coverage.py::TestEndpointAuthGuards",
      "-q"
    )
  }
  Invoke-GateStep "backend saved/plans hardening" {
    Invoke-Native $Python @(
      "-m", "pytest",
      "agent/tests/test_phase16_coverage.py::TestPathValidationSaved",
      "agent/tests/test_phase16_coverage.py::TestPathValidationPlans",
      "agent/tests/test_gap_fixes.py::TestSavedModuleHardening",
      "agent/tests/test_gap_fixes.py::TestPlansModuleHardening",
      "-q"
    )
  }
  Invoke-GateStep "backend py_compile" {
    Invoke-Native $Python @(
      "-m", "py_compile",
      "agent/public_api.py",
      "agent/saved.py",
      "agent/plans.py",
      "agent/social.py",
      "agent/server.py",
      "scripts/apply_migrations.py",
      "scripts/check_migration_gate.py"
    )
  }
} else {
  Write-Step "SKIP" "backend gate"
}

if (!$SkipData) {
  Invoke-GateStep "data quality validation" {
    Invoke-Native $Python @("scripts/validate_data.py", "--data", "web/data.json")
  }
  Invoke-GateStep "data quality budgets" {
    Invoke-Native $Python @("scripts/quality_budget.py", "--data", "web/data.json")
  }
} else {
  Write-Step "SKIP" "data quality validation"
}

if (!$SkipFrontend) {
  $webDir = Join-Path $Root "web-nuxt"
  Invoke-GateStep "frontend smoke tests" {
    Invoke-Native "npx" @("vitest", "run", "tests/smoke.test.ts", "--testTimeout=30000", "--hookTimeout=30000") $webDir
  }
  Invoke-GateStep "frontend vue-tsc" {
    Invoke-Native "npx" @("vue-tsc", "--noEmit", "--pretty", "false") $webDir
  }
} else {
  Write-Step "SKIP" "frontend gate"
}

if ($RunE2E) {
  if ($SmokeBaseUrl) { $env:SMOKE_BASE_URL = $SmokeBaseUrl }
  if ($SmokeApiBaseUrl) { $env:SMOKE_API_BASE_URL = $SmokeApiBaseUrl }
  Invoke-GateStep "Chrome smoke E2E 20 routes" {
    Invoke-Native $Node @("scripts/smoke_e2e_chrome.mjs")
  }
} elseif ($RequireE2E) {
  $Script:Failures++
  Write-Step "FAIL" "Chrome smoke E2E 20 routes" "required but not run"
} else {
  Write-Step "SKIP" "Chrome smoke E2E 20 routes" "start local app/API and pass -RunE2E; use -RequireE2E in CI"
}

try {
  Invoke-LaunchSafetyRequiredEvidence
} catch {
  $Script:Failures++
  Write-Step "FAIL" "Launch Safety required evidence" $_.Exception.Message
}

try {
  Invoke-LaunchSafetyOptIns
} catch {
  $optInExit = if ($_.Exception.Data.Contains("ExitCode")) {
    [int]$_.Exception.Data["ExitCode"]
  } else { 1 }
  Set-LaunchSafetyOptInExit $optInExit
  Write-Step "FAIL" "Launch Safety opt-ins" $_.Exception.Message
}

Invoke-LaunchSafetyFinalRender

Write-Host ""
if ($Script:Failures -gt 0) {
  Write-Host "Result: FAIL ($Script:Failures failure(s), $Script:Warnings warning(s))"
  exit 1
}
if ($Script:LaunchSafetyOptInExit -ne 0) {
  Write-Host "Result: FAIL (Launch Safety opt-in exit $Script:LaunchSafetyOptInExit)"
  exit $Script:LaunchSafetyOptInExit
}
if ($Script:Warnings -gt 0) {
  Write-Host "Result: WARN ($Script:Warnings warning(s))"
  exit 2
}
Write-Host "Result: OK"
