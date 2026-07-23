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

  $composeControlEnvironmentNames = @(
    'COMPOSE_FILE',
    'COMPOSE_PROJECT_NAME',
    'COMPOSE_PROFILES',
    'COMPOSE_ENV_FILES',
    'COMPOSE_DISABLE_ENV_FILE'
  )
  $environmentNamesToRestore = @(
    $EnvironmentNames + $composeControlEnvironmentNames |
      Select-Object -Unique
  )
  $environmentSnapshot = @{}
  foreach ($name in $environmentNamesToRestore) {
    $exists = Test-Path -LiteralPath "Env:$name"
    $environmentSnapshot[$name] = [pscustomobject]@{
      Exists = $exists
      Value = if ($exists) { (Get-Item -LiteralPath "Env:$name").Value } else { $null }
    }
  }
  foreach ($name in $composeControlEnvironmentNames) {
    Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
  }
  $env:COMPOSE_DISABLE_ENV_FILE = '1'
  $composeProject = 'vl360launch' + [guid]::NewGuid().ToString('N')

  $primaryExit = 0
  $cleanupExit = 0
  $recordExit = 0
  try {
    $upArgs = @('compose', '-p', $composeProject, '-f', $ComposeFile, 'up', '-d')
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
        & docker compose -p $composeProject -f $ComposeFile down -v --remove-orphans 2>&1 | Out-Host
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
      foreach ($name in $environmentNamesToRestore) {
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

function Resolve-LaunchSafetyBash {
  [OutputType([string])]
  param()

  $command = Get-Command bash -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandType -eq 'Application' } |
    Select-Object -First 1
  if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace([string]$command.Source)) {
    return [string]$command.Source
  }

  $installRoots = @(
    [pscustomobject]@{ Base = $env:ProgramFiles; GitDirectory = 'Git' },
    [pscustomobject]@{ Base = ${env:ProgramFiles(x86)}; GitDirectory = 'Git' },
    [pscustomobject]@{ Base = $env:LOCALAPPDATA; GitDirectory = 'Programs/Git' }
  )
  foreach ($installRoot in $installRoots) {
    $base = $installRoot.Base
    if ([string]::IsNullOrWhiteSpace([string]$base)) { continue }
    foreach ($candidate in @(
      (Join-Path $base "$($installRoot.GitDirectory)/bin/bash.exe"),
      (Join-Path $base "$($installRoot.GitDirectory)/usr/bin/bash.exe")
    )) {
      if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        return (Resolve-Path -LiteralPath $candidate).Path
      }
    }
  }
  return $null
}

