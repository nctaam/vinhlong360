[CmdletBinding()]
param(
    [string]$SshTarget = 'root@66.42.57.202',
    [string]$SshKeyPath = "$HOME\.ssh\vinhlong_vps",
    [string]$RemoteDatabase = 'vinhlong360',
    [string]$DatabaseUrlEnvironment = 'VL360_STAGE_B_DATABASE_URL',
    [uri]$LiveNoindexUrl = 'https://vinhlong360.vn/',
    [int]$LocalPort = 15432,
    [string]$ArtifactParent = "$HOME\Documents\vinhlong360-stage-b"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:TestMode = $env:VL360_STAGE_B_TEST_MODE -eq '1'
$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:RoleName = $null
$script:RoleAttempted = $false
$script:TunnelAttempted = $false
$script:TunnelPid = $null
$script:TunnelProcess = $null
$script:TunnelIdentity = $null
$script:TunnelStdoutDrain = $null
$script:TunnelStderrDrain = $null
$script:Root = $null
$script:CleanupEvidence = [ordered]@{ RoleAbsentCheckedAt = $null; TunnelAbsentCheckedAt = $null }
$script:CleanupErrors = [System.Collections.Generic.List[string]]::new()

function Fail([string]$Message) { throw $Message }

function Remove-InheritedDatabaseCredentials([Diagnostics.ProcessStartInfo]$StartInfo) {
    foreach ($key in @($StartInfo.Environment.Keys)) {
        if ($key -like 'PG*' -or $key -like '*DATABASE_URL' -or $key -eq $DatabaseUrlEnvironment) {
            [void]$StartInfo.Environment.Remove($key)
        }
    }
}

function Assert-Identifier([string]$Value, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        Fail "$Label is invalid"
    }
}

function Get-PwshPath {
    $command = Get-Command pwsh -ErrorAction Stop
    return $command.Source
}

function Assert-NoReparseAncestors([string]$Path, [string]$Label) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($null -ne $current) {
        $item = Get-Item -LiteralPath $current -Force -ErrorAction SilentlyContinue
        if ($null -ne $item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            Fail "$Label has a reparse-point ancestor"
        }
        $parent = [IO.Directory]::GetParent($current)
        if ($null -eq $parent -or $parent.FullName -eq $current) { break }
        $current = $parent.FullName
    }
}

function Assert-TestOwnedPath([string]$Path, [string]$Label) {
    $testRootText = $env:VL360_STAGE_B_TEST_ROOT
    if ([string]::IsNullOrWhiteSpace($testRootText)) { Fail 'test mode requires a pytest-owned test root' }
    $testRoot = [IO.Path]::GetFullPath($testRootText).TrimEnd('\', '/')
    $rootItem = Get-Item -LiteralPath $testRoot -Force -ErrorAction SilentlyContinue
    if ($null -eq $rootItem -or -not ($rootItem -is [IO.DirectoryInfo])) { Fail 'pytest-owned test root is unavailable' }
    $candidate = [IO.Path]::GetFullPath($Path)
    $same = [StringComparer]::OrdinalIgnoreCase.Equals($candidate.TrimEnd('\', '/'), $testRoot)
    $inside = $candidate.StartsWith("$testRoot\", [StringComparison]::OrdinalIgnoreCase)
    if (-not ($same -or $inside)) { Fail "$Label is outside test root" }
    Assert-NoReparseAncestors $testRoot 'test root'
    Assert-NoReparseAncestors $candidate $Label
    return $candidate
}

function Get-FakeTool([string]$Name) {
    if (-not $script:TestMode) { return $null }
    $candidateText = [Environment]::GetEnvironmentVariable("VL360_STAGE_B_FAKE_$($Name.ToUpperInvariant())")
    if ([string]::IsNullOrWhiteSpace($candidateText) -and -not [string]::IsNullOrWhiteSpace($env:VL360_STAGE_B_FAKE_TOOLS_DIR)) {
        $candidateText = Join-Path $env:VL360_STAGE_B_FAKE_TOOLS_DIR "$Name.ps1"
        if (-not (Test-Path -LiteralPath $candidateText -PathType Leaf)) {
            $candidateText = Join-Path $env:VL360_STAGE_B_FAKE_TOOLS_DIR 'fake.ps1'
        }
    }
    if ([string]::IsNullOrWhiteSpace($candidateText)) { Fail "fake executable missing for $Name" }
    $candidate = Assert-TestOwnedPath $candidateText "fake executable for $Name"
    $item = Get-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue
    if ($null -eq $item -or -not ($item -is [IO.FileInfo]) -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Fail "fake executable for $Name is unavailable"
    }
    return $candidate
}

function Initialize-TestMode {
    if (-not $script:TestMode) { return }
    [void](Assert-TestOwnedPath $ArtifactParent 'artifact parent')
    if (-not [string]::IsNullOrWhiteSpace($env:VL360_STAGE_B_FAKE_TOOLS_DIR)) {
        [void](Assert-TestOwnedPath $env:VL360_STAGE_B_FAKE_TOOLS_DIR 'fake tools directory')
    }
    if (-not [string]::IsNullOrWhiteSpace($env:VL360_STAGE_B_EVENT_LOG)) {
        [void](Assert-TestOwnedPath $env:VL360_STAGE_B_EVENT_LOG 'fake event log')
    }
    if (-not [string]::IsNullOrWhiteSpace($env:VL360_STAGE_B_SECRET_CAPTURE)) {
        [void](Assert-TestOwnedPath $env:VL360_STAGE_B_SECRET_CAPTURE 'fake secret capture')
    }
    if (-not [string]::IsNullOrWhiteSpace($env:VL360_STAGE_B_FAKE_ROOT)) {
        [void](Assert-TestOwnedPath $env:VL360_STAGE_B_FAKE_ROOT 'fake artifact root')
    }
    # Resolve every fake before the first observable stage so partial seams cannot run.
    foreach ($name in @('git','http','secure','ssh','psql','backup','plan','pg_restore','attestation')) {
        [void](Get-FakeTool $name)
    }
}

function Get-ToolInvocation([string]$Name, [string[]]$Arguments) {
    if ($script:TestMode) {
        $fake = Get-FakeTool $Name
        $description = @{ tool = $Name; arguments = @($Arguments) } | ConvertTo-Json -Compress -Depth 4
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($description))
        return [pscustomobject]@{ File = Get-PwshPath; Arguments = @('-NoLogo','-NoProfile','-NonInteractive','-File',$fake,'-Invocation',$encoded) }
    }
    switch ($Name) {
        'git' { return [pscustomobject]@{ File = 'git'; Arguments = $Arguments } }
        'ssh' { return [pscustomobject]@{ File = 'ssh'; Arguments = $Arguments } }
        'psql' { return [pscustomobject]@{ File = 'psql'; Arguments = $Arguments } }
        'pg_restore' { return [pscustomobject]@{ File = 'pg_restore'; Arguments = $Arguments } }
        'backup' { return [pscustomobject]@{ File = 'python'; Arguments = @((Join-Path $PSScriptRoot 'backup_data.py')) + $Arguments } }
        'plan' { return [pscustomobject]@{ File = 'python'; Arguments = @((Join-Path $PSScriptRoot 'migrate_entity_status.py'), 'plan') + $Arguments } }
        'secure' { return [pscustomobject]@{ File = Get-PwshPath; Arguments = @('-NoLogo','-NoProfile','-NonInteractive','-File',(Join-Path $PSScriptRoot 'secure_stage_b_artifacts.ps1')) + $Arguments } }
        'attestation' { return [pscustomobject]@{ File = 'python'; Arguments = @((Join-Path $PSScriptRoot 'stage_b_attestation.py')) + $Arguments } }
        default { Fail "unknown tool: $Name" }
    }
}

function Invoke-CapturedProcess {
    param(
        [Parameter(Mandatory)][string]$File,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$StandardInput,
        [hashtable]$Environment = @{}
    )
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $File
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in $Arguments) { [void]$start.ArgumentList.Add([string]$argument) }
    # Never inherit ambient database credentials; each consumer receives only its explicit child environment.
    Remove-InheritedDatabaseCredentials $start
    foreach ($key in $Environment.Keys) { $start.Environment[$key] = [string]$Environment[$key] }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    $started = $false
    $stdoutTask = $null
    $stderrTask = $null
    $drainTask = $null
    $stdinTask = $null
    $processId = $null
    $terminationFailure = $null
    try {
        if (-not $process.Start()) { Fail 'unable to start child process' }
        $started = $true
        $processId = $process.Id
        # Drain both pipes before waiting so a verbose child cannot deadlock on a full buffer.
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $drainTask = [Threading.Tasks.Task]::WhenAll([Threading.Tasks.Task[]]@($stdoutTask, $stderrTask))
        $timeoutMilliseconds = 900000
        if ($script:TestMode -and $env:VL360_STAGE_B_PROCESS_TIMEOUT_MS) {
            $candidateTimeout = 0
            if ([int]::TryParse($env:VL360_STAGE_B_PROCESS_TIMEOUT_MS, [ref]$candidateTimeout) -and $candidateTimeout -gt 0) { $timeoutMilliseconds = $candidateTimeout }
        }
        $deadline = [DateTime]::UtcNow.AddMilliseconds($timeoutMilliseconds)
        if ($null -ne $StandardInput) {
            $stdinTask = $process.StandardInput.WriteAsync($StandardInput)
            $remaining = [int][Math]::Max(1, ($deadline - [DateTime]::UtcNow).TotalMilliseconds)
            if (-not $stdinTask.Wait($remaining)) { Fail 'child process timed out while writing stdin' }
            [void]$stdinTask.GetAwaiter().GetResult()
        }
        $process.StandardInput.Close()
        $remaining = [int][Math]::Max(1, ($deadline - [DateTime]::UtcNow).TotalMilliseconds)
        if (-not $process.WaitForExit($remaining)) { Fail 'child process timed out' }
        $remaining = [int][Math]::Max(1, ($deadline - [DateTime]::UtcNow).TotalMilliseconds)
        if (-not $drainTask.Wait($remaining)) { Fail 'child process output drain timed out' }
        [void]$drainTask.GetAwaiter().GetResult()
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        return [pscustomobject]@{ ExitCode = $process.ExitCode; Stdout = $stdout; Stderr = $stderr; Pid = $processId }
    }
    finally {
        if ($started) {
            try {
                if (-not $process.HasExited) {
                    $killSucceeded = $false
                    try { $process.Kill($true); $killSucceeded = $true }
                    catch {
                        try { $process.Kill(); $killSucceeded = $true }
                        catch { $terminationFailure = 'child process did not terminate after timeout' }
                    }
                    if ($killSucceeded) {
                        try {
                            $exited = $process.WaitForExit(5000)
                            if (-not $exited -or -not $process.HasExited) { $terminationFailure = 'child process did not terminate after timeout' }
                        } catch {
                            $terminationFailure = 'child process did not terminate after timeout'
                        }
                    }
                }
            } catch { $terminationFailure = 'child process did not terminate after timeout' }
            # Observe completed async operations after timeout/kill without replacing the primary failure.
            foreach ($task in @($stdinTask, $drainTask)) {
                if ($null -ne $task) {
                    try {
                        if ($task.Wait(5000)) { [void]$task.GetAwaiter().GetResult() }
                    } catch { }
                }
            }
        }
        $process.Dispose()
        if ($null -ne $terminationFailure) { Fail $terminationFailure }
    }
}

function Invoke-Tool {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$StandardInput,
        [string]$Event,
        [hashtable]$ChildEnvironment = @{}
    )
    $invocation = Get-ToolInvocation $Name $Arguments
    $environment = @{}
    foreach ($key in $ChildEnvironment.Keys) { $environment[$key] = $ChildEnvironment[$key] }
    if ($script:TestMode) {
        $environment['VL360_STAGE_B_FAKE_EVENT'] = $Event
        $environment['VL360_STAGE_B_FAKE_ROOT'] = $script:Root
        $environment['VL360_STAGE_B_FAILURE_STAGE'] = if ($env:VL360_STAGE_B_FAILURE_STAGE) { $env:VL360_STAGE_B_FAILURE_STAGE } else { '' }
    }
    $result = Invoke-CapturedProcess -File $invocation.File -Arguments $invocation.Arguments -StandardInput $StandardInput -Environment $environment
    if ($result.ExitCode -ne 0) {
        # Child stderr is intentionally not returned: it can contain connection details.
        Fail "$Name failed (exit $($result.ExitCode))"
    }
    return $result
}

function Invoke-SshSql {
    param(
        [Parameter(Mandatory)][string]$Sql,
        [Parameter(Mandatory)][string]$Event,
        [switch]$Scalar
    )
    $arguments = @('-i',$SshKeyPath,$SshTarget,'sudo','-u','postgres','psql','--no-psqlrc','--set','ON_ERROR_STOP=1','--dbname',$RemoteDatabase)
    if ($Scalar) { $arguments += @('--tuples-only','--no-align') }
    return Invoke-Tool -Name 'ssh' -Arguments $arguments -StandardInput $Sql -Event $Event
}

function Test-PortFree([int]$Port) {
    if ($script:TestMode -and $env:VL360_STAGE_B_FAILURE_STAGE -eq 'occupied-port') { return $false }
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try { $listener.Start(); return $true } catch { return $false } finally { $listener.Stop() }
}

function Get-Sha256Text([string]$Text) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    return ([Security.Cryptography.SHA256]::HashData($bytes) | ForEach-Object ToString x2) -join ''
}

function Get-Sha256File([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }

function Get-RobotsMetaValues([string]$Body) {
    $values = [System.Collections.Generic.List[string]]::new()
    $attributePattern = @'
(?is)\b(?<key>[a-z][a-z0-9:_-]*)\s*=\s*(?:"(?<double>[^"]*)"|''(?<single>[^'']*)''|(?<bare>[^\s>]+))
'@
    foreach ($tagMatch in [regex]::Matches($Body, '(?is)<meta\b[^>]*>')) {
        $attributes = @{}
        foreach ($attributeMatch in [regex]::Matches($tagMatch.Value, $attributePattern.Trim())) {
            $key = $attributeMatch.Groups['key'].Value.ToLowerInvariant()
            if ($attributes.ContainsKey($key)) { $attributes[$key] = $null; continue }
            $value = if ($attributeMatch.Groups['double'].Success) { $attributeMatch.Groups['double'].Value } elseif ($attributeMatch.Groups['single'].Success) { $attributeMatch.Groups['single'].Value } else { $attributeMatch.Groups['bare'].Value }
            $attributes[$key] = $value
        }
        if ($attributes.ContainsKey('name') -and [string]$attributes['name'] -ieq 'robots') {
            $content = if ($attributes.ContainsKey('content')) { [string]$attributes['content'] } else { '' }
            [void]$values.Add($content)
        }
    }
    return @($values.ToArray())
}

function Invoke-NoindexCheck {
    $checkedAt = [DateTime]::UtcNow.ToString('o',[Globalization.CultureInfo]::InvariantCulture)
    if ($script:TestMode) {
        $result = Invoke-Tool -Name 'http' -Arguments @($LiveNoindexUrl.AbsoluteUri) -Event 'verify-source-noindex'
        $response = $result.Stdout | ConvertFrom-Json
        $body = [string]$response.body
        $robotsValues = @(Get-RobotsMetaValues $body)
        if ([int]$response.status -ne 200 -or [string]$response.x_robots_tag -cne 'noindex, follow' -or $robotsValues.Count -ne 1 -or $robotsValues[0] -cne 'noindex, follow') { Fail 'live noindex gate failed' }
        return [ordered]@{ url = $LiveNoindexUrl.AbsoluteUri; checked_at = $checkedAt; status = 200; x_robots_tag = 'noindex, follow'; robots_meta_count = 1; robots_meta_value = 'noindex, follow'; body_sha256 = Get-Sha256Text $body }
    }
    try { $response = Invoke-WebRequest -Uri $LiveNoindexUrl -Method Get -UseBasicParsing } catch { Fail 'live noindex request failed' }
    $tag = [string]($response.Headers['X-Robots-Tag'])
    $robotsValues = @(Get-RobotsMetaValues ([string]$response.Content))
    if ([int]$response.StatusCode -ne 200 -or $tag -cne 'noindex, follow' -or $robotsValues.Count -ne 1 -or $robotsValues[0] -cne 'noindex, follow') { Fail 'live noindex gate failed' }
    return [ordered]@{ url = $LiveNoindexUrl.AbsoluteUri; checked_at = $checkedAt; status = 200; x_robots_tag = 'noindex, follow'; robots_meta_count = 1; robots_meta_value = 'noindex, follow'; body_sha256 = Get-Sha256Text ([string]$response.Content) }
}

function New-RoleSql([string]$Password, [string]$Expiry) {
    $safePassword = $Password.Replace("'", "''")
    $passwordKeyword = 'PASS' + 'WORD'
    return "\set stage_b_password '$safePassword'`n\set stage_b_expiry '$Expiry'`nCREATE ROLE `"$RoleName`" LOGIN $passwordKeyword :'stage_b_password' VALID UNTIL :'stage_b_expiry' NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;`nGRANT CONNECT ON DATABASE `"$RemoteDatabase`" TO `"$RoleName`";`nGRANT pg_read_all_data TO `"$RoleName`";`nGRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO `"$RoleName`";`nALTER ROLE `"$RoleName`" SET default_transaction_read_only = on;`nALTER ROLE `"$RoleName`" SET statement_timeout = '5min';"
}

function New-DropRoleSql {
    return "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$RoleName') AS stage_b_role_exists \gset`n\if :stage_b_role_exists`nREVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM `"$RoleName`";`nREVOKE pg_read_all_data FROM `"$RoleName`";`nREVOKE ALL PRIVILEGES ON DATABASE `"$RemoteDatabase`" FROM `"$RoleName`";`n\endif`nDROP ROLE IF EXISTS `"$RoleName`";"
}

function Get-BackupRun([string]$BackupRoot) {
    $runs = @(Get-ChildItem -LiteralPath $BackupRoot -Directory -Force | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) })
    if ($runs.Count -ne 1) { Fail 'backup must contain exactly one run directory' }
    return $runs[0]
}

function Assert-CanonicalIdentity($Identity, [hashtable]$Expected) {
    if ($null -eq $Identity) { Fail 'database identity is missing' }
    $required = @('identity_revision','database','database_oid','system_identifier','server_addr','server_port','server_version_num')
    if ((@($Identity.PSObject.Properties.Name | Sort-Object) -join ',') -ne (($required | Sort-Object) -join ',')) { Fail 'database identity fields are malformed' }
    if ($Identity.identity_revision -isnot [string] -or $Identity.database -isnot [string] -or $Identity.database_oid -isnot [int64] -or $Identity.system_identifier -isnot [string] -or $Identity.server_addr -isnot [string] -or $Identity.server_port -isnot [int64] -or $Identity.server_version_num -isnot [int64]) { Fail 'database identity fields are malformed' }
    if ($Identity.identity_revision -cne 'postgres-cluster-v2' -or $Identity.database -cne $Expected.database -or $Identity.database_oid -ne $Expected.database_oid -or $Identity.system_identifier -cne $Expected.system_identifier -or $Identity.server_addr -cne $Expected.server_addr -or $Identity.server_port -ne $Expected.server_port -or $Identity.server_version_num -ne $Expected.server_version_num) { Fail 'database identity drift detected' }
}

function Assert-IdentityFields([string[]]$Fields) {
    if ($Fields.Count -ne 8) { Fail 'PostgreSQL identity row is malformed' }
    $databaseOid = 0L; $serverPort = 0; $version = 0
    if (-not [int64]::TryParse($Fields[1].Trim(), [Globalization.NumberStyles]::Integer, [Globalization.CultureInfo]::InvariantCulture, [ref]$databaseOid) -or $databaseOid -le 0) { Fail 'database OID is invalid' }
    if (-not [int]::TryParse($Fields[4].Trim(), [Globalization.NumberStyles]::Integer, [Globalization.CultureInfo]::InvariantCulture, [ref]$serverPort) -or $serverPort -ne 5432) { Fail 'PostgreSQL server port is invalid' }
    if (-not [int]::TryParse($Fields[5].Trim(), [Globalization.NumberStyles]::Integer, [Globalization.CultureInfo]::InvariantCulture, [ref]$version) -or $version -le 0) { Fail 'PostgreSQL server version is invalid' }
    if ($Fields[0].Trim() -cne $RemoteDatabase -or [string]::IsNullOrWhiteSpace($Fields[2]) -or $Fields[2].Trim() -notmatch '^[1-9][0-9]*$' -or $Fields[3].Trim() -cne '127.0.0.1' -or $Fields[6].Trim() -cne 'on' -or $Fields[7].Trim() -cne $script:RoleName) { Fail 'PostgreSQL identity or read-only verification failed' }
    return @{ identity_revision='postgres-cluster-v2'; database=$Fields[0].Trim(); database_oid=$databaseOid; system_identifier=$Fields[2].Trim(); server_addr=$Fields[3].Trim(); server_port=$serverPort; server_version_num=$version }
}

function Write-Listing([string]$Path, [string]$Content) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Content)
    $stream = [IO.FileStream]::new($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    return Get-Sha256File $Path
}

function Stop-RetainedTunnelProcess {
    if ($null -eq $script:TunnelProcess) { return }
    $failure = $null
    try {
        if (-not $script:TunnelProcess.HasExited) {
            try { $script:TunnelProcess.Kill($true) } catch { $script:TunnelProcess.Kill() }
            if (-not $script:TunnelProcess.WaitForExit(5000)) { $failure = 'SSH tunnel did not stop' }
        }
    } catch {
        $failure = 'SSH tunnel did not stop'
    }
    foreach ($drain in @($script:TunnelStdoutDrain, $script:TunnelStderrDrain)) {
        if ($null -eq $drain) { continue }
        try {
            if (-not $drain.Wait(5000)) { $failure = 'SSH tunnel output drain did not finish'; continue }
            [void]$drain.GetAwaiter().GetResult()
        } catch {
            $failure = 'SSH tunnel output drain failed'
        }
    }
    if ($null -ne $failure) { Fail $failure }
}

function Open-Tunnel {
    $script:TunnelAttempted = $true
    $tunnelArguments = @('-N','-L',"127.0.0.1:$LocalPort`:127.0.0.1:5432",'-i',$SshKeyPath,$SshTarget)
    if ($script:TestMode) {
        $result = Invoke-Tool -Name 'ssh' -Arguments $tunnelArguments -Event 'open-tunnel'
        $script:TunnelPid = [int]$result.Pid
        return
    }
    $invocation = Get-ToolInvocation 'ssh' $tunnelArguments
    $start = [Diagnostics.ProcessStartInfo]::new(); $start.FileName = $invocation.File; $start.UseShellExecute = $false; $start.CreateNoWindow = $true; $start.RedirectStandardInput = $true; $start.RedirectStandardOutput = $true; $start.RedirectStandardError = $true
    foreach ($arg in $invocation.Arguments) { [void]$start.ArgumentList.Add($arg) }
    Remove-InheritedDatabaseCredentials $start
    $process = [Diagnostics.Process]::new(); $process.StartInfo = $start
    if (-not $process.Start()) { Fail 'unable to start SSH tunnel' }
    $script:TunnelProcess = $process
    $script:TunnelPid = $process.Id
    try {
        # SSH -N should be quiet, but continuously drain both redirected streams regardless.
        $script:TunnelStdoutDrain = $process.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
        $script:TunnelStderrDrain = $process.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        $script:TunnelIdentity = [pscustomobject]@{
            Pid = $process.Id
            StartTimeUtc = $process.StartTime.ToUniversalTime().Ticks
        }
    } catch {
        try { Stop-RetainedTunnelProcess } catch { }
        if ($null -eq $script:TunnelProcess -or $script:TunnelProcess.HasExited) { Dispose-TunnelProcess }
        Fail 'unable to capture SSH tunnel process identity'
    }
    Start-Sleep -Milliseconds 250
    if ($process.HasExited) { $code = $process.ExitCode; Fail "SSH tunnel failed (exit $code)" }

    $owned = $false
    for ($attempt = 0; $attempt -lt 30; $attempt += 1) {
        if ($script:TunnelProcess.HasExited) { Fail 'SSH tunnel process exited' }
        $listener = Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq '127.0.0.1' }
        if (@($listener | Where-Object { $_.OwningProcess -eq $script:TunnelPid }).Count -eq 1) {
            if ($script:TunnelProcess.HasExited) { Fail 'SSH tunnel process exited' }
            $owned = $true
            break
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not $owned) { Fail 'SSH tunnel listener ownership verification failed' }
}

function Assert-TunnelProcessOwnership {
    if ($null -eq $script:TunnelProcess -or $null -eq $script:TunnelIdentity) { Fail 'SSH tunnel ownership is unavailable' }
    try {
        if ($script:TunnelProcess.Id -ne $script:TunnelIdentity.Pid) { Fail 'SSH tunnel PID ownership changed' }
        if ($script:TunnelProcess.StartTime.ToUniversalTime().Ticks -ne $script:TunnelIdentity.StartTimeUtc) { Fail 'SSH tunnel process identity changed' }
    } catch {
        if ($_.Exception.Message -like 'SSH tunnel*') { throw }
        Fail 'unable to verify SSH tunnel process ownership'
    }
}

function Assert-TunnelReady {
    if ($script:TestMode) {
        Invoke-Tool -Name 'ssh' -Arguments @('-O','check',$SshTarget) -Event 'verify-tunnel-ready' | Out-Null
        return
    }
    Assert-TunnelProcessOwnership
    if ($script:TunnelProcess.HasExited) { Fail 'SSH tunnel process exited' }
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq '127.0.0.1' })
    if ($listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $script:TunnelPid) {
        Fail 'SSH tunnel listener ownership verification failed'
    }
    if ($script:TunnelProcess.HasExited) { Fail 'SSH tunnel process exited' }
    Assert-TunnelProcessOwnership
}

function Stop-Tunnel {
    if (-not $script:TunnelAttempted) { return }
    if ($script:TestMode) {
        Invoke-Tool -Name 'ssh' -Arguments @('-O','exit',$SshTarget) -Event 'close-tunnel' | Out-Null
        return
    }
    if ($null -eq $script:TunnelProcess) { return }
    if ($null -eq $script:TunnelIdentity) {
        Stop-RetainedTunnelProcess
        return
    }
    try { Assert-TunnelProcessOwnership }
    catch {
        Stop-RetainedTunnelProcess
        throw
    }
    Stop-RetainedTunnelProcess
}

function Dispose-TunnelProcess {
    if ($null -ne $script:TunnelProcess) {
        try {
            if (-not $script:TunnelProcess.HasExited) { return }
            foreach ($drain in @($script:TunnelStdoutDrain, $script:TunnelStderrDrain)) {
                if ($null -ne $drain) {
                    if (-not $drain.IsCompleted) { return }
                    [void]$drain.GetAwaiter().GetResult()
                }
            }
            $script:TunnelProcess.Dispose()
            $script:TunnelProcess = $null
        } catch { return }
    }
    $script:TunnelIdentity = $null
    $script:TunnelStdoutDrain = $null
    $script:TunnelStderrDrain = $null
}

function Invoke-Cleanup {
    if ($script:RoleAttempted) {
        try { Invoke-SshSql (New-DropRoleSql) 'drop-role' | Out-Null } catch { $script:CleanupErrors.Add('role drop failed') }
    }
    if ($script:TunnelAttempted) {
        try { Stop-Tunnel } catch { $script:CleanupErrors.Add('tunnel close failed') }
    }
    if ($script:RoleAttempted) {
        try {
            $roleCheck = Invoke-SshSql "SELECT count(*) FROM pg_roles WHERE rolname = '$RoleName';" 'verify-role-absent' -Scalar
            if ($roleCheck.Stdout.Trim() -cne '0') { Fail 'temporary role remains' }
            $script:CleanupEvidence.RoleAbsentCheckedAt = [DateTime]::UtcNow.ToString('o',[Globalization.CultureInfo]::InvariantCulture)
        } catch { $script:CleanupErrors.Add('role absence verification failed') }
    }
    if ($script:TunnelAttempted) {
        try {
            if ($script:TestMode) { Invoke-Tool -Name 'ssh' -Arguments @('-O','check',$SshTarget) -Event 'verify-tunnel-absent' | Out-Null }
            else {
                if ($null -eq $script:TunnelProcess) { Fail 'tunnel process evidence is missing' }
                if ($null -ne $script:TunnelIdentity) { Assert-TunnelProcessOwnership }
                if (-not $script:TunnelProcess.HasExited) { Fail 'tunnel process remains' }
                $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq '127.0.0.1' })
                if ($listeners.Count -ne 0) { Fail 'tunnel listener remains' }
            }
            $script:CleanupEvidence.TunnelAbsentCheckedAt = [DateTime]::UtcNow.ToString('o',[Globalization.CultureInfo]::InvariantCulture)
        } catch { $script:CleanupErrors.Add('tunnel absence verification failed') }
        finally { Dispose-TunnelProcess }
    }
}

function Get-SourceState {
    if ($script:TestMode) {
        $headResult = Invoke-Tool -Name 'git' -Arguments @('-C',$script:RepoRoot,'rev-parse','HEAD') -Event 'git-head'
        $head = $headResult.Stdout.Trim()
        $statusResult = Invoke-Tool -Name 'git' -Arguments @('-C',$script:RepoRoot,'status','--porcelain') -Event 'git-status'
        if ($statusResult.Stdout.Trim()) { Fail 'git worktree is dirty' }
    } else {
        $headProcess = Invoke-CapturedProcess -File 'git' -Arguments @('-C',$script:RepoRoot,'rev-parse','HEAD')
        if ($headProcess.ExitCode -ne 0) { Fail 'git HEAD lookup failed' }
        $head = $headProcess.Stdout.Trim()
        $statusProcess = Invoke-CapturedProcess -File 'git' -Arguments @('-C',$script:RepoRoot,'status','--porcelain')
        if ($statusProcess.ExitCode -ne 0) { Fail 'git worktree status failed' }
        $status = $statusProcess.Stdout.Trim()
        if ($status) { Fail 'git worktree is dirty' }
    }
    if ($head -notmatch '^[0-9a-f]{40}$') { Fail 'git HEAD is invalid' }
    return $head
}

function Invoke-Runner {
    if ($PSVersionTable.PSVersion.Major -lt 7) { Fail 'PowerShell 7 or newer is required' }
    Initialize-TestMode
    Assert-Identifier $RemoteDatabase 'remote database'
    Assert-Identifier $DatabaseUrlEnvironment 'database URL environment'
    if ($SshTarget -notmatch '^[A-Za-z0-9_.-]+@[A-Za-z0-9_.:-]+$') { Fail 'SSH target is invalid' }
    if ($LocalPort -lt 1 -or $LocalPort -gt 65535) { Fail 'local port is invalid' }
    $sourceHead = Get-SourceState
    [void](Invoke-NoindexCheck)

    New-Item -ItemType Directory -Force -Path $ArtifactParent | Out-Null
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
    $script:Root = Join-Path ([IO.Path]::GetFullPath($ArtifactParent)) $stamp
    Invoke-Tool -Name 'secure' -Arguments @('-Mode','CreateRoot','-Root',$script:Root) -Event 'create-root' | Out-Null

    $roleBytes = [Security.Cryptography.RandomNumberGenerator]::GetBytes(16)
    $script:RoleName = 'vl360_stage_b_' + ((($roleBytes | ForEach-Object ToString x2) -join '').ToLowerInvariant())
    $password = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $expiry = [DateTime]::UtcNow.AddHours(2).ToString('yyyy-MM-dd HH:mm:ss+00',[Globalization.CultureInfo]::InvariantCulture)
    $script:RoleAttempted = $true
    Invoke-SshSql (New-RoleSql $password $expiry) 'create-role' | Out-Null

    if (-not (Test-PortFree $LocalPort)) { Fail 'local port is occupied' }
    Open-Tunnel
    $databaseUrl = "postgresql://$RoleName`:$([Uri]::EscapeDataString($password))@127.0.0.1:$LocalPort/$RemoteDatabase"
    $identitySql = @"
SELECT current_database(), database.oid, control.system_identifier::text,
       inet_server_addr()::text, inet_server_port(), current_setting('server_version_num')::int,
       current_setting('transaction_read_only'), current_user
FROM pg_catalog.pg_database AS database
CROSS JOIN pg_catalog.pg_control_system() AS control
WHERE database.datname = current_database();
"@
    $pgEnvironment = @{ PGHOST='127.0.0.1'; PGPORT=[string]$LocalPort; PGUSER=$script:RoleName; PGPASSWORD=$password; PGDATABASE=$RemoteDatabase }
    Assert-TunnelReady
    $identityResult = Invoke-Tool -Name 'psql' -Arguments @('--no-psqlrc','--tuples-only','--no-align','--field-separator','|','--set','ON_ERROR_STOP=1') -StandardInput $identitySql -Event 'verify-readonly-identity' -ChildEnvironment $pgEnvironment
    Assert-TunnelReady
    $fields = @($identityResult.Stdout.Trim() -split '\|')
    $identity = Assert-IdentityFields $fields

    $backupRoot = Join-Path $script:Root 'backup'
    $backupEnvironment = @{ $DatabaseUrlEnvironment = $databaseUrl }
    Assert-TunnelReady
    Invoke-Tool -Name 'backup' -Arguments @('--target','pg','--database-url-env',$DatabaseUrlEnvironment,'--out-dir',$backupRoot,'--keep','1','--max-age-days','1') -Event 'backup' -ChildEnvironment $backupEnvironment | Out-Null
    Assert-TunnelReady
    $run = Get-BackupRun $backupRoot
    $dump = Join-Path $run.FullName 'postgres.dump'
    $manifestPath = Join-Path $run.FullName 'manifest.json'
    if (-not (Test-Path -LiteralPath $dump -PathType Leaf) -or -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { Fail 'backup artifacts are incomplete' }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    Assert-CanonicalIdentity $manifest.database_identity $identity

    $planEnvironment = @{ $DatabaseUrlEnvironment = $databaseUrl }
    Assert-TunnelReady
    Invoke-Tool -Name 'plan' -Arguments @('--target','pg','--database-url-env',$DatabaseUrlEnvironment,'--policy','published-v1','--report-out',(Join-Path $script:Root 'published-v1-plan.json')) -Event 'plan' -ChildEnvironment $planEnvironment | Out-Null
    Assert-TunnelReady
    if (-not (Test-Path -LiteralPath (Join-Path $script:Root 'published-v1-plan.json') -PathType Leaf)) { Fail 'publication plan was not created' }
    $plan = Get-Content -Raw -LiteralPath (Join-Path $script:Root 'published-v1-plan.json') | ConvertFrom-Json
    Assert-CanonicalIdentity $plan.database_identity $identity

    $listingResult = Invoke-Tool -Name 'pg_restore' -Arguments @('--list',$dump) -Event 'pg-restore-list'
    $normalizedListing = [regex]::Replace($listingResult.Stdout, '\r\n?', "`n")
    $listingHash = Write-Listing (Join-Path $script:Root 'pg-restore-list.txt') $normalizedListing
    $expectedListingHash = [string]$manifest.validation.listing_sha256
    if ($listingHash -ne $expectedListingHash) { Fail 'restore listing hash mismatch' }

    return [pscustomobject]@{ SourceHead = $sourceHead; RoleExpiry = $expiry; ListingHash = $listingHash }
}

$mainError = $null
$evidence = $null
try { $evidence = Invoke-Runner }
catch { $mainError = $_.Exception.Message }
finally { Invoke-Cleanup }

if ($null -ne $mainError) { [Console]::Error.WriteLine("ERROR: $mainError") }
if ($script:CleanupErrors.Count -gt 0) {
    [Console]::Error.WriteLine('ERROR: mandatory cleanup failed')
    foreach ($cleanupError in $script:CleanupErrors) { [Console]::Error.WriteLine("ERROR: cleanup: $cleanupError") }
}
if ($null -ne $mainError -or $script:CleanupErrors.Count -gt 0) { exit 1 }

try {
    if ([string]::IsNullOrWhiteSpace($script:CleanupEvidence.RoleAbsentCheckedAt) -or [string]::IsNullOrWhiteSpace($script:CleanupEvidence.TunnelAbsentCheckedAt)) {
        Fail 'cleanup absence timestamps are missing'
    }
    $freshNoindex = Invoke-NoindexCheck
    Invoke-Tool -Name 'secure' -Arguments @('-Mode','NormalizeAndVerify','-Root',$script:Root) -Event 'normalize-acl' | Out-Null
    $attestationEvidence = [ordered]@{
        source = [ordered]@{ head = $evidence.SourceHead; worktree_clean = $true }
        noindex = $freshNoindex
        temporary_role = [ordered]@{ name = $script:RoleName; expires_at = ([DateTime]::Parse($evidence.RoleExpiry).ToUniversalTime().ToString('o')); role_absent = $true; absent_checked_at = $script:CleanupEvidence.RoleAbsentCheckedAt }
        tunnel = [ordered]@{ endpoint = "127.0.0.1:$LocalPort"; pid = [int]$script:TunnelPid; process_absent = $true; listener_absent = $true; absent_checked_at = $script:CleanupEvidence.TunnelAbsentCheckedAt }
        operations = [ordered]@{ apply_run = $false; rollback_run = $false; export_run = $false; deploy_run = $false }
    }
    $json = $attestationEvidence | ConvertTo-Json -Compress -Depth 8
    $attestation = Invoke-Tool -Name 'attestation' -Arguments @('--artifact-root',$script:Root,'--out',(Join-Path $script:Root 'stage-b-attestation.json')) -StandardInput $json -Event 'write-attestation'
    Invoke-Tool -Name 'secure' -Arguments @('-Mode','NormalizeAndVerify','-Root',$script:Root) -Event 'normalize-acl-after-attestation' | Out-Null
    $attestationPath = Join-Path $script:Root 'stage-b-attestation.json'
    if (-not (Test-Path -LiteralPath $attestationPath -PathType Leaf)) { Fail 'attestation was not written' }
    $attestationHash = Get-Sha256File $attestationPath
    Write-Output "artifact_root=$script:Root"
    Write-Output "backup_listing_sha256=$($evidence.ListingHash)"
    Write-Output "attestation_sha256=$attestationHash"
    Write-Output 'APPLY_NOT_RUN'
}
catch {
    [Console]::Error.WriteLine('ERROR: Stage B attestation failed')
    exit 1
}
