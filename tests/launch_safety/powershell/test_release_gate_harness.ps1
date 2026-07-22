$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$stubRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("launch-gate-stubs-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $stubRoot | Out-Null

@'
@echo off
echo docker stdout %*
echo docker stderr %* 1>&2
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

$priorPath = $env:PATH
$priorChromeExists = Test-Path Env:CHROME_PATH
$priorChrome = $env:CHROME_PATH
$priorNginxExists = Test-Path Env:NGINX_PROBE_URL
$priorNginx = $env:NGINX_PROBE_URL
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

  foreach ($case in $cases) {
    $env:STUB_UP_EXIT = [string]$case.Up
    $env:STUB_DOWN_EXIT = [string]$case.Down
    $env:STUB_EVIDENCE_EXIT = [string]$case.Evidence
    $env:CHROME_PATH = 'C:\pre-existing\chrome.exe'
    Remove-Item Env:NGINX_PROBE_URL -ErrorAction SilentlyContinue
    $env:STUB_BODY_EXIT = [string]$case.Body

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
    $executedCases += 1
  }
  Assert-Equal $executedCases $cases.Count 'noisy stub matrix must execute every case'
}
finally {
  $env:PATH = $priorPath
  if ($priorChromeExists) { $env:CHROME_PATH = $priorChrome } else { Remove-Item Env:CHROME_PATH -ErrorAction SilentlyContinue }
  if ($priorNginxExists) { $env:NGINX_PROBE_URL = $priorNginx } else { Remove-Item Env:NGINX_PROBE_URL -ErrorAction SilentlyContinue }
  Remove-Item -LiteralPath $stubRoot -Recurse -Force
}

. (Join-Path $repoRoot 'scripts/ops/release_gate_browser_harness.ps1')

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

  $cleanupRetry = @{ Starts = 0; Stops = 0 }
  $cleanupRetryResult = @(Invoke-LaunchSafetyBrowserHarness `
    -Root $repoRoot `
    -SelectPort { return 18443 } `
    -StartPreview {
      param($EntryPoint, $WorkingDirectory)
      $cleanupRetry.Starts += 1
      return [pscustomobject]@{ Id = $cleanupRetry.Starts; HasExited = $false }
    } `
    -WaitForReady { param($BaseUrl, $PreviewProcess); return 1 } `
    -RunSmoke { param($WorkingDirectory); return 0 } `
    -StopPreview { param($PreviewProcess); $cleanupRetry.Stops += 1; return 9 } `
    -RecordEvidence { param($Status, $ExitCode, $Summary, $Command); return 0 })
  Assert-Equal $cleanupRetryResult[0] 9 'failed retry cleanup takes precedence'
  Assert-Equal $cleanupRetry.Starts 1 'failed cleanup prevents another preview start'
  Assert-Equal $cleanupRetry.Stops 1 'failed cleanup is attempted once'
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
