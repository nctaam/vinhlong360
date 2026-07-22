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

