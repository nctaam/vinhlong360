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
  [string]$SmokeBaseUrl = "",
  [string]$SmokeApiBaseUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Script:Failures = 0
$Script:Warnings = 0

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
      throw "$File $($Arguments -join ' ') exited with code $code"
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

Write-Host "VinhLong360 release gate"
Write-Host "Root: $Root"
Write-Host ""

if ($RunAuthCheck -or $env:DATABASE_URL) {
  Invoke-NativeAllowWarning "local dev auth check" "powershell" @(
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

Write-Host ""
if ($Script:Failures -gt 0) {
  Write-Host "Result: FAIL ($Script:Failures failure(s), $Script:Warnings warning(s))"
  exit 1
}
if ($Script:Warnings -gt 0) {
  Write-Host "Result: WARN ($Script:Warnings warning(s))"
  exit 2
}
Write-Host "Result: OK"
