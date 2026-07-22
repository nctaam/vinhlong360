$MAX_LAUNCH_SAFETY_OUTPUT = 16 * 1024

function Get-LaunchSafetyLoopbackPort {
  $listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    0
  )
  try {
    $listener.Start()
    return [int]$listener.LocalEndpoint.Port
  }
  finally {
    $listener.Stop()
  }
}

function Get-BoundedLaunchSafetyFileText {
  param([string]$Path)
  if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
  $content = [System.IO.File]::ReadAllText($Path)
  if ($content.Length -le $MAX_LAUNCH_SAFETY_OUTPUT) { return $content }
  return $content.Substring($content.Length - $MAX_LAUNCH_SAFETY_OUTPUT)
}

function Start-LaunchSafetyPreviewProcess {
  param(
    [string]$Node,
    [string]$EntryPoint,
    [string]$WorkingDirectory
  )
  if (-not (Test-Path -LiteralPath $EntryPoint -PathType Leaf)) {
    $missing = [System.Exception]::new('Nuxt output server is missing; run npm run build first')
    $missing.Data['ExitCode'] = 1
    throw $missing
  }
  $stdoutPath = Join-Path ([System.IO.Path]::GetTempPath()) (
    'vl360-launch-preview-' + [guid]::NewGuid().ToString('N') + '.stdout.log'
  )
  $stderrPath = Join-Path ([System.IO.Path]::GetTempPath()) (
    'vl360-launch-preview-' + [guid]::NewGuid().ToString('N') + '.stderr.log'
  )
  try {
    $process = Start-Process -FilePath $Node -ArgumentList @($EntryPoint) `
      -WorkingDirectory $WorkingDirectory -PassThru -NoNewWindow `
      -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    return [pscustomobject]@{
      Process = $process
      StdoutPath = $stdoutPath
      StderrPath = $stderrPath
    }
  }
  catch {
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    $failure = [System.Exception]::new("Nuxt preview failed to start: $($_.Exception.Message)")
    $failure.Data['ExitCode'] = 1
    throw $failure
  }
}

function Wait-LaunchSafetyPreviewReady {
  param(
    [string]$BaseUrl,
    [object]$PreviewProcess
  )
  for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if ($PreviewProcess.Process.HasExited) { return 1 }
    try {
      $rootResponse = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 2
      $workerResponse = Invoke-WebRequest -Uri "$BaseUrl/sw.js" -UseBasicParsing -TimeoutSec 2
      if ($rootResponse.StatusCode -lt 500 -and
          $workerResponse.StatusCode -ge 200 -and
          $workerResponse.StatusCode -lt 300 -and
          -not [string]::IsNullOrWhiteSpace([string]$workerResponse.Content)) {
        return 0
      }
    }
    catch {
      # The bounded retry loop handles startup races and a released-port collision.
    }
    Start-Sleep -Milliseconds 250
  }
  return 1
}

function Invoke-LaunchSafetyBrowserSmoke {
  param(
    [string]$Npm,
    [string]$WorkingDirectory
  )
  $output = [System.Text.StringBuilder]::new()
  $priorErrorActionPreference = $ErrorActionPreference
  Push-Location $WorkingDirectory
  try {
    $ErrorActionPreference = 'Continue'
    & $Npm run smoke:launch-safety 2>&1 | ForEach-Object {
      $line = [string]$_ + [Environment]::NewLine
      if ($line.Length -ge $MAX_LAUNCH_SAFETY_OUTPUT) {
        $null = $output.Clear()
        $null = $output.Append($line.Substring($line.Length - $MAX_LAUNCH_SAFETY_OUTPUT))
      } else {
        $overflow = ($output.Length + $line.Length) - $MAX_LAUNCH_SAFETY_OUTPUT
        if ($overflow -gt 0) { $null = $output.Remove(0, $overflow) }
        $null = $output.Append($line)
      }
    }
    $exitCode = [int]$LASTEXITCODE
  }
  catch {
    $exitCode = if ($_.Exception.Data.Contains('ExitCode')) {
      [int]$_.Exception.Data['ExitCode']
    } else { 1 }
  }
  finally {
    $ErrorActionPreference = $priorErrorActionPreference
    Pop-Location
  }
  if ($output.Length -gt 0) { Write-Host $output.ToString().TrimEnd() }
  return [int]$exitCode
}

function Stop-LaunchSafetyPreviewProcess {
  param([object]$PreviewProcess)
  $cleanupExit = 0
  try {
    $process = $PreviewProcess.Process
    if ($null -ne $process -and -not $process.HasExited) {
      try { $process.Kill($true) } catch { Stop-Process -Id $process.Id -Force -ErrorAction Stop }
      if (-not $process.WaitForExit(5000)) { $cleanupExit = 1 }
    }
  }
  catch {
    $cleanupExit = 1
  }
  finally {
    $previewOutput = @(
      Get-BoundedLaunchSafetyFileText $PreviewProcess.StdoutPath
      Get-BoundedLaunchSafetyFileText $PreviewProcess.StderrPath
    ) -join [Environment]::NewLine
    if (-not [string]::IsNullOrWhiteSpace($previewOutput)) {
      Write-Host $previewOutput.Trim()
    }
    Remove-Item -LiteralPath $PreviewProcess.StdoutPath, $PreviewProcess.StderrPath `
      -Force -ErrorAction SilentlyContinue
  }
  return [int]$cleanupExit
}

function Resolve-LaunchSafetyBrowserResult {
  param(
    [int]$PrimaryExit,
    [int]$CleanupExit,
    [int]$RecorderExit
  )
  if ($PrimaryExit -ne 0) { return [int]$PrimaryExit }
  if ($CleanupExit -ne 0) { return [int]$CleanupExit }
  if ($RecorderExit -ne 0) { return [int]$RecorderExit }
  return 0
}

function Invoke-LaunchSafetyBrowserHarness {
  [OutputType([int])]
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [string]$Node = 'node',
    [string]$Npm = 'npm',
    [scriptblock]$SelectPort,
    [scriptblock]$StartPreview,
    [scriptblock]$WaitForReady,
    [scriptblock]$RunSmoke,
    [scriptblock]$StopPreview,
    [Parameter(Mandatory = $true)][scriptblock]$RecordEvidence
  )

  if ($null -eq $SelectPort) { $SelectPort = { Get-LaunchSafetyLoopbackPort } }
  if ($null -eq $StartPreview) {
    $StartPreview = {
      param($EntryPoint, $WorkingDirectory)
      Start-LaunchSafetyPreviewProcess $Node $EntryPoint $WorkingDirectory
    }
  }
  if ($null -eq $WaitForReady) {
    $WaitForReady = {
      param($BaseUrl, $PreviewProcess)
      Wait-LaunchSafetyPreviewReady $BaseUrl $PreviewProcess
    }
  }
  if ($null -eq $RunSmoke) {
    $RunSmoke = {
      param($WorkingDirectory)
      Invoke-LaunchSafetyBrowserSmoke $Npm $WorkingDirectory
    }
  }
  if ($null -eq $StopPreview) {
    $StopPreview = {
      param($PreviewProcess)
      Stop-LaunchSafetyPreviewProcess $PreviewProcess
    }
  }

  $environmentNames = @('HOST', 'NITRO_HOST', 'PORT', 'NITRO_PORT', 'SMOKE_BASE_URL')
  $environmentSnapshot = @{}
  foreach ($name in $environmentNames) {
    $exists = Test-Path -LiteralPath "Env:$name"
    $environmentSnapshot[$name] = [pscustomobject]@{
      Exists = $exists
      Value = if ($exists) { (Get-Item -LiteralPath "Env:$name").Value } else { $null }
    }
  }

  $webDirectory = Join-Path $Root 'web-nuxt'
  $entryPoint = Join-Path $Root 'web-nuxt/.output/server/index.mjs'
  $primaryExit = 0
  $cleanupExit = 0
  $recorderExit = 0
  $previewProcess = $null
  $summary = 'controlled Chrome launch-safety smoke'
  try {
    $started = $false
    for ($attempt = 0; $attempt -lt 5 -and -not $started; $attempt++) {
      $port = [int](& $SelectPort)
      $baseUrl = "http://127.0.0.1:$port"
      $env:HOST = '127.0.0.1'
      $env:NITRO_HOST = '127.0.0.1'
      $env:PORT = [string]$port
      $env:NITRO_PORT = [string]$port
      try {
        $previewProcess = & $StartPreview $entryPoint $webDirectory
        $readyExit = [int](& $WaitForReady $baseUrl $previewProcess)
        if ($readyExit -eq 0) {
          $started = $true
          break
        }
        $retryCleanupExit = [int](& $StopPreview $previewProcess)
        $previewProcess = $null
        if ($retryCleanupExit -ne 0) {
          $cleanupExit = $retryCleanupExit
          $summary = "preview retry cleanup failed with exit $cleanupExit"
          break
        }
      }
      catch {
        if ($null -ne $previewProcess) {
          $retryCleanupExit = [int](& $StopPreview $previewProcess)
          $previewProcess = $null
          if ($retryCleanupExit -ne 0) {
            $cleanupExit = $retryCleanupExit
            $summary = "preview retry cleanup failed with exit $cleanupExit"
            break
          }
        }
        if ($attempt -eq 4) { throw }
      }
    }
    if (-not $started -and $cleanupExit -eq 0) {
      $primaryExit = 1
      $summary = 'Nuxt output server readiness failed'
    } else {
      $env:SMOKE_BASE_URL = $baseUrl
      $primaryExit = [int](& $RunSmoke $webDirectory)
      if ($primaryExit -ne 0) { $summary = "browser smoke failed with exit $primaryExit" }
    }
  }
  catch {
    $primaryExit = if ($_.Exception.Data.Contains('ExitCode')) {
      [int]$_.Exception.Data['ExitCode']
    } else { 1 }
    $summary = $_.Exception.Message
  }
  finally {
    if ($null -ne $previewProcess) {
      try { $cleanupExit = [int](& $StopPreview $previewProcess) } catch { $cleanupExit = 1 }
    }
    foreach ($name in $environmentNames) {
      $prior = $environmentSnapshot[$name]
      if ($prior.Exists) {
        Set-Item -LiteralPath "Env:$name" -Value $prior.Value
      } else {
        Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
      }
    }
  }

  $evidenceExit = Resolve-LaunchSafetyBrowserResult $primaryExit $cleanupExit 0
  $status = if ($evidenceExit -eq 0) { 'pass' } else { 'fail' }
  try {
    $recorderExit = [int](& $RecordEvidence $status $evidenceExit $summary 'npm run smoke:launch-safety')
  }
  catch {
    $recorderExit = if ($_.Exception.Data.Contains('ExitCode')) {
      [int]$_.Exception.Data['ExitCode']
    } else { 1 }
  }

  return [int](Resolve-LaunchSafetyBrowserResult $primaryExit $cleanupExit $recorderExit)
}
