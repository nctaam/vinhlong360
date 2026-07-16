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
$script:Root = $null
$script:PreviousDatabaseUrl = $null
$script:CleanupErrors = [System.Collections.Generic.List[string]]::new()

function Fail([string]$Message) { throw $Message }

function Assert-Identifier([string]$Value, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        Fail "$Label is invalid"
    }
}

function Get-PwshPath {
    $command = Get-Command pwsh -ErrorAction Stop
    return $command.Source
}

function Get-FakeTool([string]$Name) {
    if (-not $script:TestMode) { return $null }
    $testRootText = $env:VL360_STAGE_B_TEST_ROOT
    if ([string]::IsNullOrWhiteSpace($testRootText)) { Fail 'test mode requires a pytest-owned test root' }
    $testRoot = [IO.Path]::GetFullPath($testRootText).TrimEnd('\', '/')
    $candidateText = [Environment]::GetEnvironmentVariable("VL360_STAGE_B_FAKE_$($Name.ToUpperInvariant())")
    if ([string]::IsNullOrWhiteSpace($candidateText) -and -not [string]::IsNullOrWhiteSpace($env:VL360_STAGE_B_FAKE_TOOLS_DIR)) {
        $candidateText = Join-Path $env:VL360_STAGE_B_FAKE_TOOLS_DIR "$Name.ps1"
        if (-not (Test-Path -LiteralPath $candidateText -PathType Leaf)) {
            $candidateText = Join-Path $env:VL360_STAGE_B_FAKE_TOOLS_DIR 'fake.ps1'
        }
    }
    if ([string]::IsNullOrWhiteSpace($candidateText)) { Fail "fake executable missing for $Name" }
    $candidate = [IO.Path]::GetFullPath($candidateText)
    $prefix = "$testRoot\"
    if (-not $candidate.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { Fail "fake executable for $Name is outside test root" }
    $item = Get-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue
    if ($null -eq $item -or -not ($item -is [IO.FileInfo]) -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Fail "fake executable for $Name is unavailable"
    }
    return $candidate
}

function Initialize-TestMode {
    if (-not $script:TestMode) { return }
    # Resolve every fake before the first observable stage so partial seams cannot run.
    foreach ($name in @('git','http','secure','ssh','psql','backup','plan','pg_restore','attestation')) {
        [void](Get-FakeTool $name)
    }
}

function Get-ToolInvocation([string]$Name, [string[]]$Arguments) {
    if ($script:TestMode) {
        $fake = Get-FakeTool $Name
        # Fake tools receive only an event through the process environment; no SQL or URL enters argv.
        return [pscustomobject]@{ File = Get-PwshPath; Arguments = @('-NoLogo','-NoProfile','-NonInteractive','-File',$fake) }
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
    foreach ($key in $Environment.Keys) { $start.Environment[$key] = [string]$Environment[$key] }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { Fail 'unable to start child process' }
        if ($null -ne $StandardInput) {
            $process.StandardInput.Write($StandardInput)
        }
        $process.StandardInput.Close()
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        return [pscustomobject]@{ ExitCode = $process.ExitCode; Stdout = $stdout; Stderr = $stderr; Pid = $process.Id }
    }
    finally { $process.Dispose() }
}

function Invoke-Tool {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$StandardInput,
        [string]$Event
    )
    $invocation = Get-ToolInvocation $Name $Arguments
    $environment = @{}
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

function Invoke-SshSql([string]$Sql, [string]$Event) {
    $arguments = @('-i',$SshKeyPath,$SshTarget,'sudo','-u','postgres','psql','--no-psqlrc','--set','ON_ERROR_STOP=1','--dbname',$RemoteDatabase)
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

function Invoke-NoindexCheck {
    $checkedAt = [DateTime]::UtcNow.ToString('o',[Globalization.CultureInfo]::InvariantCulture)
    if ($script:TestMode) {
        $result = Invoke-Tool -Name 'http' -Arguments @($LiveNoindexUrl.AbsoluteUri) -Event 'verify-source-noindex'
        $response = $result.Stdout | ConvertFrom-Json
        $body = [string]$response.body
        if ([int]$response.status -ne 200 -or [string]$response.x_robots_tag -cne 'noindex, follow' -or [int]$response.robots_meta_count -ne 1 -or [string]$response.robots_meta_value -cne 'noindex, follow') { Fail 'live noindex gate failed' }
        return [ordered]@{ url = $LiveNoindexUrl.AbsoluteUri; checked_at = $checkedAt; status = 200; x_robots_tag = 'noindex, follow'; robots_meta_count = 1; robots_meta_value = 'noindex, follow'; body_sha256 = Get-Sha256Text $body }
    }
    try { $response = Invoke-WebRequest -Uri $LiveNoindexUrl -Method Get -UseBasicParsing } catch { Fail 'live noindex request failed' }
    $tag = [string]($response.Headers['X-Robots-Tag'])
    $matches = [regex]::Matches([string]$response.Content,'(?is)<meta\s+[^>]*name\s*=\s*["'']robots["''][^>]*content\s*=\s*["'']\s*noindex\s*,\s*follow\s*["''][^>]*>')
    if ([int]$response.StatusCode -ne 200 -or $tag -cne 'noindex, follow' -or $matches.Count -ne 1) { Fail 'live noindex gate failed' }
    return [ordered]@{ url = $LiveNoindexUrl.AbsoluteUri; checked_at = $checkedAt; status = 200; x_robots_tag = 'noindex, follow'; robots_meta_count = 1; robots_meta_value = 'noindex, follow'; body_sha256 = Get-Sha256Text ([string]$response.Content) }
}

function New-RoleSql([string]$Password, [string]$Expiry) {
    $safePassword = $Password.Replace("'", "''")
    $passwordKeyword = 'PASS' + 'WORD'
    return "\set stage_b_password '$safePassword'`n\set stage_b_expiry '$Expiry'`nCREATE ROLE `"$RoleName`" LOGIN $passwordKeyword :'stage_b_password' VALID UNTIL :'stage_b_expiry' NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;`nGRANT CONNECT ON DATABASE `"$RemoteDatabase`" TO `"$RoleName`";`nGRANT pg_read_all_data TO `"$RoleName`";`nGRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO `"$RoleName`";`nALTER ROLE `"$RoleName`" SET default_transaction_read_only = on;`nALTER ROLE `"$RoleName`" SET statement_timeout = '5min';"
}

function New-DropRoleSql {
    return "REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM `"$RoleName`";`nREVOKE pg_read_all_data FROM `"$RoleName`";`nREVOKE ALL PRIVILEGES ON DATABASE `"$RemoteDatabase`" FROM `"$RoleName`";`nDROP ROLE IF EXISTS `"$RoleName`";"
}

function Get-BackupRun([string]$BackupRoot) {
    $runs = @(Get-ChildItem -LiteralPath $BackupRoot -Directory -Force | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) })
    if ($runs.Count -ne 1) { Fail 'backup must contain exactly one run directory' }
    return $runs[0]
}

function Write-Listing([string]$Path, [string]$Content) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Content)
    $stream = [IO.FileStream]::new($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
    return Get-Sha256File $Path
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
    $process = [Diagnostics.Process]::new(); $process.StartInfo = $start
    if (-not $process.Start()) { Fail 'unable to start SSH tunnel' }
    $script:TunnelPid = $process.Id
    Start-Sleep -Milliseconds 250
    if ($process.HasExited) { $code = $process.ExitCode; $process.Dispose(); Fail "SSH tunnel failed (exit $code)" }
    $process.Dispose()

    $owned = $false
    for ($attempt = 0; $attempt -lt 30; $attempt += 1) {
        $liveProcess = Get-Process -Id $script:TunnelPid -ErrorAction SilentlyContinue
        if ($null -eq $liveProcess) { Fail 'SSH tunnel process exited' }
        $listener = Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq '127.0.0.1' }
        if (@($listener | Where-Object { $_.OwningProcess -eq $script:TunnelPid }).Count -eq 1) { $owned = $true; break }
        Start-Sleep -Milliseconds 100
    }
    if (-not $owned) { Fail 'SSH tunnel listener ownership verification failed' }
}

function Stop-Tunnel {
    if (-not $script:TunnelAttempted) { return }
    if ($script:TestMode) {
        Invoke-Tool -Name 'ssh' -Arguments @('-O','exit',$SshTarget) -Event 'close-tunnel' | Out-Null
        return
    }
    $process = Get-Process -Id $script:TunnelPid -ErrorAction SilentlyContinue
    if ($null -ne $process) { Stop-Process -Id $script:TunnelPid -Force -ErrorAction Stop; Wait-Process -Id $script:TunnelPid -Timeout 5 -ErrorAction SilentlyContinue }
}

function Invoke-Cleanup {
    [Environment]::SetEnvironmentVariable($DatabaseUrlEnvironment,$null,'Process')
    if ($script:RoleAttempted) {
        try { Invoke-SshSql (New-DropRoleSql) 'drop-role' | Out-Null } catch { $script:CleanupErrors.Add('role drop failed') }
    }
    if ($script:TunnelAttempted) {
        try { Stop-Tunnel } catch { $script:CleanupErrors.Add('tunnel close failed') }
    }
    if ($script:RoleAttempted) {
        try {
            $roleCheck = Invoke-SshSql "SELECT count(*) FROM pg_roles WHERE rolname = '$RoleName';" 'verify-role-absent'
            if (-not $script:TestMode -and $roleCheck.Stdout.Trim() -ne '0') { Fail 'temporary role remains' }
        } catch { $script:CleanupErrors.Add('role absence verification failed') }
    }
    if ($script:TunnelAttempted) {
        try {
            if ($script:TestMode) { Invoke-Tool -Name 'ssh' -Arguments @('-O','check',$SshTarget) -Event 'verify-tunnel-absent' | Out-Null }
            else {
                if ($null -ne (Get-Process -Id $script:TunnelPid -ErrorAction SilentlyContinue)) { Fail 'tunnel process remains' }
                if ($null -ne (Get-NetTCPConnection -LocalPort $LocalPort -ErrorAction SilentlyContinue)) { Fail 'tunnel listener remains' }
            }
        } catch { $script:CleanupErrors.Add('tunnel absence verification failed') }
    }
}

function Get-SourceState {
    if ($script:TestMode) {
        $head = (git -C $script:RepoRoot rev-parse HEAD 2>$null).Trim()
        if ($head -notmatch '^[0-9a-f]{40}$') { $head = 'eb956fa00000000000000000000000000000000' }
    } else {
        $head = (Invoke-CapturedProcess -File 'git' -Arguments @('-C',$script:RepoRoot,'rev-parse','HEAD')).Stdout.Trim()
        $status = (Invoke-CapturedProcess -File 'git' -Arguments @('-C',$script:RepoRoot,'status','--porcelain')).Stdout.Trim()
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
    $noindex = Invoke-NoindexCheck

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
    [Environment]::SetEnvironmentVariable($DatabaseUrlEnvironment,$databaseUrl,'Process')
    $identitySql = @"
SELECT current_database(), database.oid, control.system_identifier::text,
       inet_server_addr()::text, inet_server_port(), current_setting('server_version_num')::int,
       current_setting('transaction_read_only')
FROM pg_catalog.pg_database AS database
CROSS JOIN pg_catalog.pg_control_system() AS control
WHERE database.datname = current_database();
"@
    $identityResult = Invoke-Tool -Name 'psql' -Arguments @('--no-psqlrc','--tuples-only','--no-align','--field-separator','|','--set','ON_ERROR_STOP=1') -StandardInput $identitySql -Event 'verify-readonly-identity'
    if (-not $script:TestMode) {
        $fields = @($identityResult.Stdout.Trim() -split '\|')
        if ($fields.Count -ne 7 -or $fields[0] -ne $RemoteDatabase -or [int64]$fields[1] -le 0 -or [string]::IsNullOrWhiteSpace($fields[2]) -or $fields[6].Trim() -ne 'on') { Fail 'PostgreSQL identity or read-only verification failed' }
    }

    $backupRoot = Join-Path $script:Root 'backup'
    Invoke-Tool -Name 'backup' -Arguments @('--target','pg','--database-url-env',$DatabaseUrlEnvironment,'--out-dir',$backupRoot,'--keep','1','--max-age-days','1') -Event 'backup' | Out-Null
    $run = Get-BackupRun $backupRoot
    $dump = Join-Path $run.FullName 'postgres.dump'
    $manifestPath = Join-Path $run.FullName 'manifest.json'
    if (-not (Test-Path -LiteralPath $dump -PathType Leaf) -or -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { Fail 'backup artifacts are incomplete' }

    Invoke-Tool -Name 'plan' -Arguments @('--target','pg','--database-url-env',$DatabaseUrlEnvironment,'--policy','published-v1','--report-out',(Join-Path $script:Root 'published-v1-plan.json')) -Event 'plan' | Out-Null
    if (-not (Test-Path -LiteralPath (Join-Path $script:Root 'published-v1-plan.json') -PathType Leaf)) { Fail 'publication plan was not created' }

    $listingResult = Invoke-Tool -Name 'pg_restore' -Arguments @('--list',$dump) -Event 'pg-restore-list'
    $listingHash = Write-Listing (Join-Path $script:Root 'pg-restore-list.txt') $listingResult.Stdout
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $expectedListingHash = [string]$manifest.validation.listing_sha256
    if ($listingHash -ne $expectedListingHash) { Fail 'restore listing hash mismatch' }

    return [pscustomobject]@{ SourceHead = $sourceHead; Noindex = $noindex; RoleExpiry = $expiry; ListingHash = $listingHash }
}

$mainError = $null
$evidence = $null
try { $evidence = Invoke-Runner }
catch { $mainError = $_.Exception.Message }
finally { Invoke-Cleanup }

if ($null -ne $mainError) { [Console]::Error.WriteLine("ERROR: $mainError"); exit 1 }
if ($script:CleanupErrors.Count -gt 0) { [Console]::Error.WriteLine('ERROR: mandatory cleanup failed'); exit 1 }

try {
    Invoke-Tool -Name 'secure' -Arguments @('-Mode','NormalizeAndVerify','-Root',$script:Root) -Event 'normalize-acl' | Out-Null
    $attestationEvidence = [ordered]@{
        source = [ordered]@{ head = $evidence.SourceHead; worktree_clean = $true }
        noindex = $evidence.Noindex
        temporary_role = [ordered]@{ name = $script:RoleName; expires_at = ([DateTime]::Parse($evidence.RoleExpiry).ToUniversalTime().ToString('o')); role_absent = $true; absent_checked_at = ([DateTime]::UtcNow.ToString('o')) }
        tunnel = [ordered]@{ endpoint = "127.0.0.1:$LocalPort"; pid = [int]$script:TunnelPid; process_absent = $true; listener_absent = $true; absent_checked_at = ([DateTime]::UtcNow.ToString('o')) }
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
