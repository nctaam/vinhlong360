$MAX_LAUNCH_SAFETY_OUTPUT = 16 * 1024

if (-not ('VinhLong360.LaunchSafety.BoundedProcessCapture' -as [type])) {
  Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Text;

namespace VinhLong360.LaunchSafety
{
    public sealed class BoundedProcessCapture : IDisposable
    {
        private readonly int maxLength;
        private readonly object stdoutLock = new object();
        private readonly object stderrLock = new object();
        private readonly StringBuilder stdout = new StringBuilder();
        private readonly StringBuilder stderr = new StringBuilder();

        public Process Process { get; private set; }

        public string Stdout
        {
            get { lock (stdoutLock) { return stdout.ToString(); } }
        }

        public string Stderr
        {
            get { lock (stderrLock) { return stderr.ToString(); } }
        }

        public BoundedProcessCapture(
            string executable,
            string entryPoint,
            string workingDirectory,
            int maxLength)
        {
            this.maxLength = maxLength;
            Process = new Process();
            Process.StartInfo = new ProcessStartInfo
            {
                FileName = executable,
                Arguments = QuoteArgument(entryPoint),
                WorkingDirectory = workingDirectory,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            Process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs args)
            {
                Append(stdout, stdoutLock, args.Data);
            };
            Process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs args)
            {
                Append(stderr, stderrLock, args.Data);
            };
        }

        public void Start()
        {
            if (!Process.Start())
            {
                throw new InvalidOperationException("Nuxt preview process did not start");
            }
            Process.BeginOutputReadLine();
            Process.BeginErrorReadLine();
        }

        private static string QuoteArgument(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private void Append(StringBuilder buffer, object sync, string line)
        {
            if (line == null) { return; }
            string value = line + Environment.NewLine;
            lock (sync)
            {
                if (value.Length >= maxLength)
                {
                    buffer.Clear();
                    buffer.Append(value.Substring(value.Length - maxLength));
                    return;
                }
                int overflow = buffer.Length + value.Length - maxLength;
                if (overflow > 0) { buffer.Remove(0, overflow); }
                buffer.Append(value);
            }
        }

        public void Dispose()
        {
            Process.Dispose();
        }
    }
}
'@
}

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
  $capture = $null
  try {
    $capture = [VinhLong360.LaunchSafety.BoundedProcessCapture]::new(
      $Node,
      $EntryPoint,
      $WorkingDirectory,
      $MAX_LAUNCH_SAFETY_OUTPUT
    )
    $capture.Start()
    return [pscustomobject]@{
      Process = $capture.Process
      Capture = $capture
    }
  }
  catch {
    if ($null -ne $capture) { $capture.Dispose() }
    $failure = [System.Exception]::new("Nuxt preview failed to start: $($_.Exception.Message)")
    $failure.Data['ExitCode'] = 1
    throw $failure
  }
}

function Wait-LaunchSafetyPreviewReady {
  param(
    [string]$BaseUrl,
    [object]$PreviewProcess,
    [int]$MaxAttempts = 60,
    [int]$DelayMilliseconds = 250,
    [scriptblock]$InvokeRequest
  )
  if ($null -eq $InvokeRequest) {
    $InvokeRequest = {
      param($Uri)
      Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
    }
  }
  for ($attempt = 0; $attempt -lt $MaxAttempts; $attempt++) {
    if ($PreviewProcess.Process.HasExited) { return 1 }
    try {
      $rootResponse = & $InvokeRequest "$BaseUrl/"
      $workerResponse = & $InvokeRequest "$BaseUrl/sw.js"
      if ($rootResponse.StatusCode -ge 200 -and
          $rootResponse.StatusCode -lt 400 -and
          $workerResponse.StatusCode -ge 200 -and
          $workerResponse.StatusCode -lt 300 -and
          -not [string]::IsNullOrWhiteSpace([string]$workerResponse.Content)) {
        return 0
      }
    }
    catch {
      # The bounded retry loop handles startup races and a released-port collision.
    }
    if ($DelayMilliseconds -gt 0) { Start-Sleep -Milliseconds $DelayMilliseconds }
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
    if ($null -ne $process -and $process.HasExited) { $process.WaitForExit() }
  }
  catch {
    $cleanupExit = 1
  }
  finally {
    $previewOutput = @(
      $PreviewProcess.Capture.Stdout
      $PreviewProcess.Capture.Stderr
    ) -join [Environment]::NewLine
    if (-not [string]::IsNullOrWhiteSpace($previewOutput)) {
      Write-Host $previewOutput.Trim()
    }
    if ($null -ne $PreviewProcess.Capture) { $PreviewProcess.Capture.Dispose() }
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
    if ($started) {
      $env:SMOKE_BASE_URL = $baseUrl
      $primaryExit = [int](& $RunSmoke $webDirectory)
      if ($primaryExit -ne 0) { $summary = "browser smoke failed with exit $primaryExit" }
    } elseif ($cleanupExit -eq 0) {
      $primaryExit = 1
      $summary = 'Nuxt output server readiness failed'
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
