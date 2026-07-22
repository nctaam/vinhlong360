function Invoke-RecordedComposeHarness {
  [OutputType([int])]
  param(
    [Parameter(Mandatory = $true)][string]$Section,
    [Parameter(Mandatory = $true)][string]$ComposeFile,
    [Parameter(Mandatory = $true)][string[]]$EnvironmentNames,
    [Parameter(Mandatory = $true)][scriptblock]$Body,
    [switch]$Build,
    [string]$EvidenceState = $env:LAUNCH_SAFETY_EVIDENCE_STATE,
    [string]$Python = "python"
  )

  $environmentSnapshot = @{}
  foreach ($name in $EnvironmentNames) {
    $exists = Test-Path -LiteralPath "Env:$name"
    $environmentSnapshot[$name] = [pscustomobject]@{
      Exists = $exists
      Value = if ($exists) { (Get-Item -LiteralPath "Env:$name").Value } else { $null }
    }
  }

  $primaryExit = 0
  $cleanupExit = 0
  $recordExit = 0
  try {
    $upArgs = @('compose', '-f', $ComposeFile, 'up', '-d')
    if ($Build) { $upArgs += '--build' }
    $upArgs += '--wait'
    $priorErrorActionPreference = $ErrorActionPreference
    try {
      $ErrorActionPreference = 'Continue'
      & docker @upArgs 2>&1 | Out-Host
      $primaryExit = [int]$LASTEXITCODE
    }
    finally {
      $ErrorActionPreference = $priorErrorActionPreference
    }
    if ($primaryExit -eq 0) {
      $priorErrorActionPreference = $ErrorActionPreference
      try {
        $ErrorActionPreference = 'Continue'
        & $Body 2>&1 | Out-Host
      }
      finally {
        $ErrorActionPreference = $priorErrorActionPreference
      }
    }
  }
  catch {
    if ($primaryExit -eq 0) {
      $primaryExit = if ($_.Exception.Data.Contains('ExitCode')) {
        [int]$_.Exception.Data['ExitCode']
      } else { 1 }
    }
  }
  finally {
    try {
      $priorErrorActionPreference = $ErrorActionPreference
      try {
        $ErrorActionPreference = 'Continue'
        & docker compose -f $ComposeFile down -v --remove-orphans 2>&1 | Out-Host
        $cleanupExit = [int]$LASTEXITCODE
      }
      finally {
        $ErrorActionPreference = $priorErrorActionPreference
      }
    }
    catch {
      $cleanupExit = 1
    }
    finally {
      foreach ($name in $EnvironmentNames) {
        $prior = $environmentSnapshot[$name]
        if ($prior.Exists) {
          Set-Item -LiteralPath "Env:$name" -Value $prior.Value
        } else {
          Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
        }
      }
    }
  }

  $recordArgs = @(
    'scripts/ops/record_launch_evidence.py',
    'harness-result',
    '--section', $Section,
    '--primary-exit', [string]$primaryExit,
    '--cleanup-exit', [string]$cleanupExit
  )
  if ($EvidenceState) { $recordArgs += @('--state', $EvidenceState) }
  $priorErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    & $Python @recordArgs 2>&1 | Out-Host
    $recordExit = [int]$LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $priorErrorActionPreference
  }

  $result = if ($primaryExit -ne 0) {
    $primaryExit
  } elseif ($cleanupExit -ne 0) {
    $cleanupExit
  } elseif ($recordExit -ne 0) {
    $recordExit
  } else { 0 }
  return [int]$result
}

