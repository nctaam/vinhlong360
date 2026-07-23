$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$stubRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("launch-gate-stubs-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $stubRoot | Out-Null

@'
@echo off
echo docker stdout %*
echo docker stderr %* 1>&2
echo CALL:%*>>"%STUB_DOCKER_LOG%"
echo ENV:COMPOSE_FILE=[%COMPOSE_FILE%]>>"%STUB_DOCKER_LOG%"
echo ENV:COMPOSE_PROJECT_NAME=[%COMPOSE_PROJECT_NAME%]>>"%STUB_DOCKER_LOG%"
echo ENV:COMPOSE_PROFILES=[%COMPOSE_PROFILES%]>>"%STUB_DOCKER_LOG%"
echo ENV:COMPOSE_ENV_FILES=[%COMPOSE_ENV_FILES%]>>"%STUB_DOCKER_LOG%"
echo ENV:COMPOSE_DISABLE_ENV_FILE=[%COMPOSE_DISABLE_ENV_FILE%]>>"%STUB_DOCKER_LOG%"
echo %* | findstr /C:" down " >nul
if %errorlevel%==0 exit /b %STUB_DOWN_EXIT%
exit /b %STUB_UP_EXIT%
'@ | Set-Content -LiteralPath (Join-Path $stubRoot 'docker.cmd') -Encoding Ascii

@'
@echo off
echo evidence stdout %*
echo evidence stderr %* 1>&2
exit /b %STUB_EVIDENCE_EXIT%
'@ | Set-Content -LiteralPath (Join-Path $stubRoot 'python.cmd') -Encoding Ascii

function Assert-Equal($Actual, $Expected, [string]$Message) {
  if ($Actual -ne $Expected) { throw "$Message; expected=$Expected actual=$Actual" }
}

function Assert-True($Condition, [string]$Message) {
  if (-not $Condition) { throw $Message }
}

. (Join-Path $repoRoot 'scripts/ops/release_gate_harness.ps1')

$bashAuthorityPath = Join-Path $stubRoot 'bash.cmd'
$bashPriorPath = $env:PATH
$bashPriorProgramFiles = $env:ProgramFiles
$bashPriorProgramFilesX86 = ${env:ProgramFiles(x86)}
$bashPriorLocalAppData = $env:LOCALAPPDATA
try {
  $env:PATH = $stubRoot
  $env:ProgramFiles = Join-Path $stubRoot 'missing-program-files'
  ${env:ProgramFiles(x86)} = Join-Path $stubRoot 'missing-program-files-x86'
  $env:LOCALAPPDATA = Join-Path $stubRoot 'missing-local-app-data'
  Remove-Item -LiteralPath $bashAuthorityPath -Force -ErrorAction SilentlyContinue
  Assert-Equal (Resolve-LaunchSafetyBash) $null 'missing bash must resolve to null'

  $userBash = Join-Path $env:LOCALAPPDATA 'Programs/Git/bin/bash.exe'
  New-Item -ItemType Directory -Path (Split-Path $userBash) -Force | Out-Null
  '' | Set-Content -LiteralPath $userBash -Encoding Ascii
  Assert-Equal (Resolve-LaunchSafetyBash) $userBash 'bash resolver must include user-scope Git for Windows'
  Remove-Item -LiteralPath $userBash -Force

  "@echo off`r`nexit /b 0`r`n" |
    Set-Content -LiteralPath $bashAuthorityPath -Encoding Ascii
  $resolvedBash = Resolve-LaunchSafetyBash
  Assert-True ($resolvedBash -eq $bashAuthorityPath) 'bash resolver must return the discovered executable authority'
}
finally {
  $env:PATH = $bashPriorPath
  if ($null -eq $bashPriorProgramFiles) { Remove-Item Env:ProgramFiles -ErrorAction SilentlyContinue } else { $env:ProgramFiles = $bashPriorProgramFiles }
  if ($null -eq $bashPriorProgramFilesX86) { Remove-Item Env:'ProgramFiles(x86)' -ErrorAction SilentlyContinue } else { ${env:ProgramFiles(x86)} = $bashPriorProgramFilesX86 }
  if ($null -eq $bashPriorLocalAppData) { Remove-Item Env:LOCALAPPDATA -ErrorAction SilentlyContinue } else { $env:LOCALAPPDATA = $bashPriorLocalAppData }
}

$priorPath = $env:PATH
$priorChromeExists = Test-Path Env:CHROME_PATH
$priorChrome = $env:CHROME_PATH
$priorNginxExists = Test-Path Env:NGINX_PROBE_URL
$priorNginx = $env:NGINX_PROBE_URL
$priorDockerLogExists = Test-Path Env:STUB_DOCKER_LOG
$priorDockerLog = $env:STUB_DOCKER_LOG
$composeControlNames = @(
  'COMPOSE_FILE',
  'COMPOSE_PROJECT_NAME',
  'COMPOSE_PROFILES',
  'COMPOSE_ENV_FILES',
  'COMPOSE_DISABLE_ENV_FILE'
)
$composeControlSnapshot = @{}
foreach ($name in $composeControlNames) {
  $exists = Test-Path -LiteralPath "Env:$name"
  $composeControlSnapshot[$name] = [pscustomobject]@{
    Exists = $exists
    Value = if ($exists) { (Get-Item -LiteralPath "Env:$name").Value } else { $null }
  }
}
$dockerLog = Join-Path $stubRoot 'docker-invocations.log'
try {
  $env:PATH = "$stubRoot;$priorPath"
  . (Join-Path $repoRoot 'scripts/ops/release_gate_harness.ps1')

  $cases = @(
    @{ Name = 'noisy-pass'; Up = 0; Body = 0; Down = 0; Evidence = 0; Expected = 0 },
    @{ Name = 'cleanup-fail'; Up = 0; Body = 0; Down = 9; Evidence = 0; Expected = 9 },
    @{ Name = 'primary-and-cleanup-fail'; Up = 0; Body = 37; Down = 9; Evidence = 0; Expected = 37 },
    @{ Name = 'compose-up-fail'; Up = 23; Body = 0; Down = 0; Evidence = 0; Expected = 23 },
    @{ Name = 'evidence-fail'; Up = 0; Body = 0; Down = 0; Evidence = 13; Expected = 13 }
  )
  $executedCases = 0
  $ownedProjects = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
  )

  foreach ($case in $cases) {
    Remove-Item -LiteralPath $dockerLog -Force -ErrorAction SilentlyContinue
    $env:STUB_DOCKER_LOG = $dockerLog
    $env:STUB_UP_EXIT = [string]$case.Up
    $env:STUB_DOWN_EXIT = [string]$case.Down
    $env:STUB_EVIDENCE_EXIT = [string]$case.Evidence
    $env:CHROME_PATH = 'C:\pre-existing\chrome.exe'
    Remove-Item Env:NGINX_PROBE_URL -ErrorAction SilentlyContinue
    $env:STUB_BODY_EXIT = [string]$case.Body
    $env:COMPOSE_FILE = 'external-compose.yml'
    $env:COMPOSE_PROJECT_NAME = 'external-project'
    $env:COMPOSE_PROFILES = 'external-profile'
    $env:COMPOSE_ENV_FILES = 'external.env'
    $env:COMPOSE_DISABLE_ENV_FILE = 'external-disable-setting'

    $result = @(Invoke-RecordedComposeHarness `
      -Section $case.Name `
      -ComposeFile 'noisy-stub.yml' `
      -EnvironmentNames @('CHROME_PATH', 'NGINX_PROBE_URL') `
      -Python 'python' `
      -Body {
        Write-Output 'body stdout must not become a return object'
        [Console]::Error.WriteLine('body stderr must not become a return object')
        $env:CHROME_PATH = 'C:\temporary\chrome.exe'
        $env:NGINX_PROBE_URL = 'http://127.0.0.1:18080'
        if ([int]$env:STUB_BODY_EXIT -ne 0) {
          $failure = [System.Exception]::new('stub primary failure')
          $failure.Data['ExitCode'] = [int]$env:STUB_BODY_EXIT
          throw $failure
        }
      })

    Assert-Equal $result.Count 1 "$($case.Name) must emit exactly one pipeline object"
    if ($result[0] -isnot [int]) { throw "$($case.Name) result must be System.Int32" }
    Assert-Equal $result[0] $case.Expected "$($case.Name) exit precedence"
    Assert-Equal $env:CHROME_PATH 'C:\pre-existing\chrome.exe' "$($case.Name) restores existing CHROME_PATH"
    if (Test-Path Env:NGINX_PROBE_URL) { throw "$($case.Name) must restore NGINX_PROBE_URL to unset" }
    Assert-Equal $env:COMPOSE_FILE 'external-compose.yml' "$($case.Name) restores COMPOSE_FILE"
    Assert-Equal $env:COMPOSE_PROJECT_NAME 'external-project' "$($case.Name) restores COMPOSE_PROJECT_NAME"
    Assert-Equal $env:COMPOSE_PROFILES 'external-profile' "$($case.Name) restores COMPOSE_PROFILES"
    Assert-Equal $env:COMPOSE_ENV_FILES 'external.env' "$($case.Name) restores COMPOSE_ENV_FILES"
    Assert-Equal $env:COMPOSE_DISABLE_ENV_FILE 'external-disable-setting' "$($case.Name) restores COMPOSE_DISABLE_ENV_FILE"

    $dockerLines = @(Get-Content -LiteralPath $dockerLog)
    $calls = @($dockerLines | Where-Object { $_.StartsWith('CALL:') })
    Assert-Equal $calls.Count 2 "$($case.Name) must invoke compose up and down exactly once"
    $upMatch = [regex]::Match(
      $calls[0],
      '^CALL:compose -p ([a-z0-9][a-z0-9_-]*) -f noisy-stub\.yml up -d --wait$'
    )
    $downMatch = [regex]::Match(
      $calls[1],
      '^CALL:compose -p ([a-z0-9][a-z0-9_-]*) -f noisy-stub\.yml down -v --remove-orphans$'
    )
    Assert-True $upMatch.Success "$($case.Name) compose up must use an invocation-owned project"
    Assert-True $downMatch.Success "$($case.Name) compose down must use an invocation-owned project"
    Assert-Equal $downMatch.Groups[1].Value $upMatch.Groups[1].Value "$($case.Name) cleanup must use the same project"
    Assert-True ($ownedProjects.Add($upMatch.Groups[1].Value)) "$($case.Name) project must be unique per invocation"

    foreach ($name in @('COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'COMPOSE_PROFILES', 'COMPOSE_ENV_FILES')) {
      Assert-Equal @($dockerLines | Where-Object { $_ -eq "ENV:$name=[]" }).Count 2 (
        "$($case.Name) must hide inherited $name from both compose calls"
      )
    }
    Assert-Equal @($dockerLines | Where-Object { $_ -eq 'ENV:COMPOSE_DISABLE_ENV_FILE=[1]' }).Count 2 (
      "$($case.Name) must disable automatic Compose env files for both calls"
    )
    $executedCases += 1
  }
  Assert-Equal $executedCases $cases.Count 'noisy stub matrix must execute every case'

  Remove-Item -LiteralPath $dockerLog -Force -ErrorAction SilentlyContinue
  $env:STUB_DOCKER_LOG = $dockerLog
  $env:STUB_UP_EXIT = '0'
  $env:STUB_DOWN_EXIT = '0'
  $env:STUB_EVIDENCE_EXIT = '0'
  foreach ($name in $composeControlNames) {
    Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
  }

  $unsetResult = @(Invoke-RecordedComposeHarness `
    -Section 'unset-compose-controls' `
    -ComposeFile 'noisy-stub.yml' `
    -EnvironmentNames @('NGINX_PROBE_URL') `
    -Python 'python' `
    -Body {})

  Assert-Equal $unsetResult.Count 1 'unset Compose controls must emit exactly one result'
  Assert-Equal $unsetResult[0] 0 'unset Compose controls harness result'
  foreach ($name in $composeControlNames) {
    if (Test-Path -LiteralPath "Env:$name") {
      throw "unset Compose controls must restore $name to unset"
    }
  }
  $unsetDockerLines = @(Get-Content -LiteralPath $dockerLog)
  foreach ($name in @('COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'COMPOSE_PROFILES', 'COMPOSE_ENV_FILES')) {
    Assert-Equal @($unsetDockerLines | Where-Object { $_ -eq "ENV:$name=[]" }).Count 2 (
      "unset Compose controls must hide $name from both compose calls"
    )
  }
  Assert-Equal @(
    $unsetDockerLines | Where-Object { $_ -eq 'ENV:COMPOSE_DISABLE_ENV_FILE=[1]' }
  ).Count 2 'unset Compose controls must disable automatic env files for both calls'
}
finally {
  $env:PATH = $priorPath
  if ($priorChromeExists) { $env:CHROME_PATH = $priorChrome } else { Remove-Item Env:CHROME_PATH -ErrorAction SilentlyContinue }
  if ($priorNginxExists) { $env:NGINX_PROBE_URL = $priorNginx } else { Remove-Item Env:NGINX_PROBE_URL -ErrorAction SilentlyContinue }
  foreach ($name in $composeControlNames) {
    $prior = $composeControlSnapshot[$name]
    if ($prior.Exists) {
      Set-Item -LiteralPath "Env:$name" -Value $prior.Value
    } else {
      Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    }
  }
  if ($priorDockerLogExists) {
    $env:STUB_DOCKER_LOG = $priorDockerLog
  } else {
    Remove-Item Env:STUB_DOCKER_LOG -ErrorAction SilentlyContinue
  }
  Remove-Item -LiteralPath $stubRoot -Recurse -Force
}

. (Join-Path $repoRoot 'scripts/ops/release_gate_browser_harness.ps1')

$noiseScript = Join-Path ([System.IO.Path]::GetTempPath()) (
  'launch-safety-noisy-preview-' + [guid]::NewGuid().ToString('N') + '.mjs'
)
'process.stdout.write("o".repeat(65536)); process.stderr.write("e".repeat(65536));' |
  Set-Content -LiteralPath $noiseScript -Encoding Ascii
try {
  $captured = Start-LaunchSafetyPreviewProcess 'node' $noiseScript $repoRoot
  try {
    Assert-True ($captured.PSObject.Properties.Name -contains 'Capture') 'preview must expose bounded capture'
    $null = $captured.Process.WaitForExit(10000)
    Start-Sleep -Milliseconds 100
    Assert-True ($captured.Capture.Stdout.Length -le 16384) 'stdout capture must stay bounded during preview'
    Assert-True ($captured.Capture.Stderr.Length -le 16384) 'stderr capture must stay bounded during preview'
  }
  finally {
    Stop-LaunchSafetyPreviewProcess $captured 6>$null | Out-Null
  }
}
finally {
  Remove-Item -LiteralPath $noiseScript -Force -ErrorAction SilentlyContinue
}

$exit120StubRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
  'launch-gate-exit120-' + [guid]::NewGuid().ToString('N')
)
$exit120State = Join-Path $exit120StubRoot 'evidence.json'
$realPython = (Get-Command python -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $exit120StubRoot | Out-Null

@"
@echo off
if "%1"=="scripts/ops/record_launch_evidence.py" (
  "$realPython" %*
  exit /b %errorlevel%
)
if "%*"=="-m pytest -q" exit /b 120
exit /b 0
"@ | Set-Content -LiteralPath (Join-Path $exit120StubRoot 'python.cmd') -Encoding Ascii

@'
@echo off
if "%1"=="rev-parse" echo 0123456789abcdef0123456789abcdef01234567
exit /b 0
'@ | Set-Content -LiteralPath (Join-Path $exit120StubRoot 'git.cmd') -Encoding Ascii

foreach ($name in @('npx.cmd', 'npm.cmd', 'bash.cmd', 'pwsh.cmd')) {
  "@echo off`r`nexit /b 0`r`n" |
    Set-Content -LiteralPath (Join-Path $exit120StubRoot $name) -Encoding Ascii
}

$exit120PriorPath = $env:PATH
$exit120DatabaseUrlExists = Test-Path Env:DATABASE_URL
$exit120DatabaseUrl = $env:DATABASE_URL
try {
  $env:PATH = "$exit120StubRoot;$exit120PriorPath"
  Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
  $powershell = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
  $priorErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $exit120Output = @(& $powershell -NoProfile -Command {
      param($root, $stubRoot, $python, $state)
      $env:PATH = "$stubRoot;$env:PATH"
      & (Join-Path $root 'scripts/release_gate.ps1') `
        -SkipBackend -SkipFrontend -SkipData `
        -Python $python `
        -LaunchSafetyEvidenceState $state
      exit $LASTEXITCODE
    } -args @(
      $repoRoot,
      $exit120StubRoot,
      (Join-Path $exit120StubRoot 'python.cmd'),
      $exit120State
    ) 2>&1)
    $exit120GateExit = [int]$LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $priorErrorActionPreference
  }

  Assert-Equal $exit120GateExit 1 (
    'required section exit 120 must fail the release gate; output=' +
    ($exit120Output -join ' | ')
  )
  $exit120Evidence = Get-Content -LiteralPath $exit120State -Raw | ConvertFrom-Json
  $backendFullEvidence = $exit120Evidence.sections.'backend-full-regression'
  Assert-Equal $backendFullEvidence.status 'fail' 'backend full exit 120 evidence status'
  Assert-Equal ([int]$backendFullEvidence.exit_code) 120 'backend full exit 120 evidence code'
}
finally {
  $env:PATH = $exit120PriorPath
  if ($exit120DatabaseUrlExists) {
    $env:DATABASE_URL = $exit120DatabaseUrl
  } else {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
  }
  Remove-Item -LiteralPath $exit120StubRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$browserEnvironmentNames = @('HOST', 'NITRO_HOST', 'PORT', 'NITRO_PORT', 'SMOKE_BASE_URL')
$browserEnvironmentSnapshot = @{}
foreach ($name in $browserEnvironmentNames) {
  $exists = Test-Path -LiteralPath "Env:$name"
  $browserEnvironmentSnapshot[$name] = [pscustomobject]@{
    Exists = $exists
    Value = if ($exists) { (Get-Item -LiteralPath "Env:$name").Value } else { $null }
  }
}

try {
  $env:HOST = 'pre-existing-host'
  Remove-Item Env:NITRO_HOST -ErrorAction SilentlyContinue
  $env:PORT = '3100'
  Remove-Item Env:NITRO_PORT -ErrorAction SilentlyContinue
  $env:SMOKE_BASE_URL = 'http://pre-existing.invalid'

  $browserCases = @(
    @{ Name = 'browser-pass'; Primary = 0; Cleanup = 0; Recorder = 0; Expected = 0 },
    @{ Name = 'browser-cleanup-fail'; Primary = 0; Cleanup = 9; Recorder = 0; Expected = 9 },
    @{ Name = 'browser-primary-and-cleanup-fail'; Primary = 37; Cleanup = 9; Recorder = 0; Expected = 37 },
    @{ Name = 'browser-recorder-fail'; Primary = 0; Cleanup = 0; Recorder = 13; Expected = 13 }
  )

  foreach ($case in $browserCases) {
    $events = [System.Collections.ArrayList]::new()
    $observed = @{}
    $result = @(Invoke-LaunchSafetyBrowserHarness `
      -Root $repoRoot `
      -Node 'node' `
      -Npm 'npm' `
      -SelectPort { return 18443 } `
      -StartPreview {
        param($EntryPoint, $WorkingDirectory)
        $null = $events.Add('preview-start')
        $observed.EntryPoint = $EntryPoint
        $observed.WorkingDirectory = $WorkingDirectory
        $observed.StartHost = $env:HOST
        $observed.StartNitroHost = $env:NITRO_HOST
        $observed.StartPort = $env:PORT
        $observed.StartNitroPort = $env:NITRO_PORT
        return [pscustomobject]@{ Id = 4242; HasExited = $false }
      } `
      -WaitForReady {
        param($BaseUrl, $PreviewProcess)
        $null = $events.Add('ready')
        $observed.BaseUrl = $BaseUrl
        return 0
      } `
      -RunSmoke {
        param($WorkingDirectory)
        $null = $events.Add('smoke')
        $observed.SmokeBaseUrl = $env:SMOKE_BASE_URL
        return [int]$case.Primary
      } `
      -StopPreview {
        param($PreviewProcess)
        $null = $events.Add('preview-stop')
        return [int]$case.Cleanup
      } `
      -RecordEvidence {
        param($Status, $ExitCode, $Summary, $Command)
        $null = $events.Add('record')
        $observed.RecordStatus = $Status
        $observed.RecordExit = $ExitCode
        return [int]$case.Recorder
      })

    Assert-Equal $result.Count 1 "$($case.Name) must emit exactly one pipeline object"
    if ($result[0] -isnot [int]) { throw "$($case.Name) result must be System.Int32" }
    Assert-Equal $result[0] $case.Expected "$($case.Name) exit precedence"
    Assert-Equal $observed.EntryPoint (Join-Path $repoRoot 'web-nuxt/.output/server/index.mjs') "$($case.Name) uses real Nuxt output"
    Assert-Equal $observed.WorkingDirectory (Join-Path $repoRoot 'web-nuxt') "$($case.Name) preview working directory"
    Assert-Equal $observed.StartHost '127.0.0.1' "$($case.Name) binds loopback HOST"
    Assert-Equal $observed.StartNitroHost '127.0.0.1' "$($case.Name) binds loopback NITRO_HOST"
    Assert-Equal $observed.StartPort '18443' "$($case.Name) sets PORT"
    Assert-Equal $observed.StartNitroPort '18443' "$($case.Name) sets NITRO_PORT"
    Assert-Equal $observed.BaseUrl 'http://127.0.0.1:18443' "$($case.Name) readiness base URL"
    if ([int]$case.Primary -eq 0) {
      Assert-Equal $observed.SmokeBaseUrl 'http://127.0.0.1:18443' "$($case.Name) smoke base URL"
    }
    Assert-Equal ($events -join ',') 'preview-start,ready,smoke,preview-stop,record' "$($case.Name) lifecycle"
    Assert-Equal $env:HOST 'pre-existing-host' "$($case.Name) restores HOST"
    if (Test-Path Env:NITRO_HOST) { throw "$($case.Name) must restore NITRO_HOST to unset" }
    Assert-Equal $env:PORT '3100' "$($case.Name) restores PORT"
    if (Test-Path Env:NITRO_PORT) { throw "$($case.Name) must restore NITRO_PORT to unset" }
    Assert-Equal $env:SMOKE_BASE_URL 'http://pre-existing.invalid' "$($case.Name) restores SMOKE_BASE_URL"
  }

  $retry = @{ Starts = 0; Stops = 0 }
  $retryResult = @(Invoke-LaunchSafetyBrowserHarness `
    -Root $repoRoot `
    -SelectPort { return (18443 + $retry.Starts) } `
    -StartPreview {
      param($EntryPoint, $WorkingDirectory)
      $retry.Starts += 1
      return [pscustomobject]@{ Id = $retry.Starts; HasExited = $false }
    } `
    -WaitForReady {
      param($BaseUrl, $PreviewProcess)
      return $(if ($retry.Starts -eq 1) { 1 } else { 0 })
    } `
    -RunSmoke { param($WorkingDirectory); return 0 } `
    -StopPreview { param($PreviewProcess); $retry.Stops += 1; return 0 } `
    -RecordEvidence { param($Status, $ExitCode, $Summary, $Command); return 0 })
  Assert-Equal $retryResult[0] 0 'readiness collision retries on a new bounded port'
  Assert-Equal $retry.Starts 2 'readiness collision starts exactly one replacement preview'
  Assert-Equal $retry.Stops 2 'readiness collision cleans both preview processes'

  $fakePreview = [pscustomobject]@{
    Process = [pscustomobject]@{ HasExited = $false }
  }
  $root404 = Wait-LaunchSafetyPreviewReady `
    -BaseUrl 'http://127.0.0.1:18443' `
    -PreviewProcess $fakePreview `
    -MaxAttempts 1 `
    -DelayMilliseconds 0 `
    -InvokeRequest {
      param($Uri)
      if ($Uri.EndsWith('/sw.js')) {
        return [pscustomobject]@{ StatusCode = 200; Content = 'worker' }
      }
      return [pscustomobject]@{ StatusCode = 404; Content = 'missing' }
    }
  Assert-Equal $root404 1 'root 4xx must fail readiness'

  $emptyWorker = Wait-LaunchSafetyPreviewReady `
    -BaseUrl 'http://127.0.0.1:18443' `
    -PreviewProcess $fakePreview `
    -MaxAttempts 1 `
    -DelayMilliseconds 0 `
    -InvokeRequest {
      param($Uri)
      if ($Uri.EndsWith('/sw.js')) {
        return [pscustomobject]@{ StatusCode = 200; Content = '' }
      }
      return [pscustomobject]@{ StatusCode = 200; Content = 'home' }
    }
  Assert-Equal $emptyWorker 1 'empty service worker must fail readiness'

  $ready = Wait-LaunchSafetyPreviewReady `
    -BaseUrl 'http://127.0.0.1:18443' `
    -PreviewProcess $fakePreview `
    -MaxAttempts 1 `
    -DelayMilliseconds 0 `
    -InvokeRequest {
      param($Uri)
      if ($Uri.EndsWith('/sw.js')) {
        return [pscustomobject]@{ StatusCode = 200; Content = 'worker' }
      }
      return [pscustomobject]@{ StatusCode = 200; Content = 'home' }
    }
  Assert-Equal $ready 0 'root and service worker success must pass readiness'

  $cleanupRetry = @{ Starts = 0; Stops = 0; Smokes = 0 }
  $cleanupRetryResult = @(Invoke-LaunchSafetyBrowserHarness `
    -Root $repoRoot `
    -SelectPort { return 18443 } `
    -StartPreview {
      param($EntryPoint, $WorkingDirectory)
      $cleanupRetry.Starts += 1
      return [pscustomobject]@{ Id = $cleanupRetry.Starts; HasExited = $false }
    } `
    -WaitForReady { param($BaseUrl, $PreviewProcess); return 1 } `
    -RunSmoke { param($WorkingDirectory); $cleanupRetry.Smokes += 1; return 37 } `
    -StopPreview { param($PreviewProcess); $cleanupRetry.Stops += 1; return 9 } `
    -RecordEvidence { param($Status, $ExitCode, $Summary, $Command); return 0 })
  Assert-Equal $cleanupRetryResult[0] 9 'failed retry cleanup takes precedence'
  Assert-Equal $cleanupRetry.Starts 1 'failed cleanup prevents another preview start'
  Assert-Equal $cleanupRetry.Stops 1 'failed cleanup is attempted once'
  Assert-Equal $cleanupRetry.Smokes 0 'failed readiness cleanup must not run browser smoke'
}
finally {
  foreach ($name in $browserEnvironmentNames) {
    $prior = $browserEnvironmentSnapshot[$name]
    if ($prior.Exists) {
      Set-Item -LiteralPath "Env:$name" -Value $prior.Value
    } else {
      Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    }
  }
}

$releaseStubRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
  'launch-gate-exit-stubs-' + [guid]::NewGuid().ToString('N')
)
$releaseState = Join-Path $releaseStubRoot 'evidence.json'
$nodeMarker = Join-Path $releaseStubRoot 'node-probe.txt'
$postgresHarnessDirectory = Join-Path $repoRoot 'tests/launch_safety/harness'
$postgresHarnessFile = Join-Path $postgresHarnessDirectory 'docker-compose.postgres.yml'
$postgresHarnessDirectoryExisted = Test-Path -LiteralPath $postgresHarnessDirectory -PathType Container
$postgresHarnessFileExisted = Test-Path -LiteralPath $postgresHarnessFile -PathType Leaf
New-Item -ItemType Directory -Path $releaseStubRoot | Out-Null
if (-not $postgresHarnessDirectoryExisted) {
  New-Item -ItemType Directory -Path $postgresHarnessDirectory -Force | Out-Null
}
if (-not $postgresHarnessFileExisted) {
  'services: {}' | Set-Content -LiteralPath $postgresHarnessFile -Encoding Ascii
}

@'
@echo off
echo %* | findstr /C:"test_sitemap_bundle_postgres.py" >nul
if %errorlevel%==0 exit /b 23
exit /b 0
'@ | Set-Content -LiteralPath (Join-Path $releaseStubRoot 'python.cmd') -Encoding Ascii

@'
@echo off
if "%1"=="rev-parse" echo 0123456789abcdef0123456789abcdef01234567
exit /b 0
'@ | Set-Content -LiteralPath (Join-Path $releaseStubRoot 'git.cmd') -Encoding Ascii

foreach ($name in @('npx.cmd', 'npm.cmd', 'bash.cmd', 'docker.cmd', 'pwsh.cmd')) {
  "@echo off`r`nexit /b 0`r`n" |
    Set-Content -LiteralPath (Join-Path $releaseStubRoot $name) -Encoding Ascii
}

"@echo off`r`necho invoked>`"$nodeMarker`"`r`nexit /b 41`r`n" |
  Set-Content -LiteralPath (Join-Path $releaseStubRoot 'node.cmd') -Encoding Ascii

$releasePriorPath = $env:PATH
$releaseDatabaseUrlExists = Test-Path Env:DATABASE_URL
$releaseDatabaseUrl = $env:DATABASE_URL
try {
  $env:PATH = "$releaseStubRoot;$releasePriorPath"
  Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
  $powershell = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
  $priorErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $releaseOutput = @(& $powershell -NoProfile -Command {
      param($root, $stubRoot, $python, $node, $state)
      $env:PATH = "$stubRoot;$env:PATH"
      & (Join-Path $root 'scripts/release_gate.ps1') `
        -SkipBackend -SkipFrontend -SkipData `
        -Python $python `
        -Node $node `
        -LaunchSafetyEvidenceState $state `
        -RunLaunchSafetyDockerOptIn `
        -RunLaunchSafetyBrowserOptIn
      exit $LASTEXITCODE
    } -args @(
      $repoRoot,
      $releaseStubRoot,
      (Join-Path $releaseStubRoot 'python.cmd'),
      (Join-Path $releaseStubRoot 'node.cmd'),
      $releaseState
    ) 2>&1)
    $releaseExit = [int]$LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $priorErrorActionPreference
  }

  Assert-Equal $releaseExit 23 (
    "first Docker opt-in failure must remain the release exit code; output=" +
    ($releaseOutput -join ' | ')
  )
  Assert-True (Test-Path -LiteralPath $nodeMarker) 'browser probe must still run after Docker opt-in failure'
  Assert-True (($releaseOutput -join "`n") -match 'Launch Safety browser opt-in') `
    'release output must report the independent browser opt-in'
}
finally {
  $env:PATH = $releasePriorPath
  if ($releaseDatabaseUrlExists) {
    $env:DATABASE_URL = $releaseDatabaseUrl
  } else {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
  }
  Remove-Item -LiteralPath $releaseStubRoot -Recurse -Force -ErrorAction SilentlyContinue
  if (-not $postgresHarnessFileExisted) {
    Remove-Item -LiteralPath $postgresHarnessFile -Force -ErrorAction SilentlyContinue
  }
  if (-not $postgresHarnessDirectoryExisted) {
    Remove-Item -LiteralPath $postgresHarnessDirectory -Force -ErrorAction SilentlyContinue
  }
}
