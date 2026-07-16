[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [ValidateSet('CreateRoot','NormalizeAndVerify','Verify')]
  [string]$Mode,
  [Parameter(Mandatory)]
  [string]$Root
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Get-ResolvedRoot {
    param([Parameter(Mandatory)][string]$Path)

    return [System.IO.Path]::GetFullPath($Path)
}

function Get-AllowedPrincipals {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $candidates = @(
        [pscustomobject]@{
            Name = $identity.Name
            Sid = $identity.User
        },
        [pscustomobject]@{
            Name = 'NT AUTHORITY\SYSTEM'
            Sid = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-18')
        },
        [pscustomobject]@{
            Name = 'BUILTIN\Administrators'
            Sid = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
        }
    )

    $unique = @{}
    foreach ($candidate in $candidates) {
        if (-not $unique.ContainsKey($candidate.Sid.Value)) {
            $unique[$candidate.Sid.Value] = $candidate
        }
    }
    return @($unique.Values | Sort-Object -Property @{ Expression = { $_.Name.ToUpperInvariant() } })
}

function Test-IsDirectory {
    param([Parameter(Mandatory)][System.IO.FileSystemInfo]$Item)

    return [bool]($Item.Attributes -band [System.IO.FileAttributes]::Directory)
}

function Test-IsReparsePoint {
    param([Parameter(Mandatory)][System.IO.FileSystemInfo]$Item)

    return [bool]($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
}

function Get-TreeObjects {
    param([Parameter(Mandatory)][string]$RootPath)

    $rootItem = Get-Item -LiteralPath $RootPath -Force
    if (-not (Test-IsDirectory -Item $rootItem)) {
        throw "Artifact root is not a directory: $RootPath"
    }

    $objects = [System.Collections.Generic.List[System.IO.FileSystemInfo]]::new()
    $directories = [System.Collections.Generic.Queue[System.IO.DirectoryInfo]]::new()
    $objects.Add($rootItem)
    if (-not (Test-IsReparsePoint -Item $rootItem)) {
        $directories.Enqueue($rootItem)
    }

    while ($directories.Count -gt 0) {
        $directory = $directories.Dequeue()
        $children = @(
            [System.IO.Directory]::EnumerateFileSystemEntries($directory.FullName) |
                Sort-Object
        )
        foreach ($childPath in $children) {
            $child = Get-Item -LiteralPath $childPath -Force
            $objects.Add($child)
            if ((Test-IsDirectory -Item $child) -and -not (Test-IsReparsePoint -Item $child)) {
                $directories.Enqueue($child)
            }
        }
    }

    return @($objects)
}

function Get-SidRules {
    param([Parameter(Mandatory)]$Acl)

    return @(
        $Acl.GetAccessRules(
            $true,
            $true,
            [System.Security.Principal.SecurityIdentifier]
        )
    )
}

function Get-ExpectedInheritanceFlags {
    param([Parameter(Mandatory)][System.IO.FileSystemInfo]$Item)

    if (Test-IsDirectory -Item $Item) {
        return (
            [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
            [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
        )
    }
    return [System.Security.AccessControl.InheritanceFlags]::None
}

function Set-ExactAcl {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo]$Item,
        [Parameter(Mandatory)][object[]]$AllowedPrincipals
    )

    $acl = Get-Acl -LiteralPath $Item.FullName
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @(Get-SidRules -Acl $acl)) {
        $acl.RemoveAccessRuleSpecific($rule)
    }

    $inheritanceFlags = Get-ExpectedInheritanceFlags -Item $Item
    foreach ($principal in $AllowedPrincipals) {
        $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
            $principal.Sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            $inheritanceFlags,
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Item.FullName -AclObject $acl
}

function Assert-NoHostileObjects {
    param([Parameter(Mandatory)][System.IO.FileSystemInfo[]]$Objects)

    $reparsePoints = @($Objects | Where-Object { Test-IsReparsePoint -Item $_ })
    if ($reparsePoints.Count -gt 0) {
        throw "Reparse point detected: $($reparsePoints[0].FullName)"
    }

    foreach ($item in $Objects) {
        $namedStreams = @(
            Get-Item -LiteralPath $item.FullName -Stream * |
                Where-Object { $_.Stream -ne ':$DATA' }
        )
        if ($namedStreams.Count -gt 0) {
            throw "Alternate data stream detected: $($item.FullName)$($namedStreams[0].Stream)"
        }
    }
}

function Assert-NormalizationPreflight {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo[]]$Objects,
        [Parameter(Mandatory)][object[]]$AllowedPrincipals
    )

    $allowedSids = @{}
    foreach ($principal in $AllowedPrincipals) {
        $allowedSids[$principal.Sid.Value] = $true
    }

    $rootAcl = Get-Acl -LiteralPath $Objects[0].FullName
    $rootRules = @(Get-SidRules -Acl $rootAcl)
    if (-not $rootAcl.AreAccessRulesProtected) {
        throw 'NormalizeAndVerify requires a protected artifact root'
    }
    if (@($rootRules | Where-Object { $_.IsInherited }).Count -gt 0) {
        throw 'Inherited rules on the artifact root cannot be normalized safely'
    }

    $unexpected = [System.Collections.Generic.List[string]]::new()
    $denyCount = 0
    $unsafeInherited = [System.Collections.Generic.List[string]]::new()

    foreach ($item in $Objects) {
        $acl = Get-Acl -LiteralPath $item.FullName
        $rules = @(Get-SidRules -Acl $acl)
        $expectedFlags = Get-ExpectedInheritanceFlags -Item $item
        $inheritedAllowedSids = @{}
        foreach ($rule in $rules) {
            $sid = $rule.IdentityReference.Value
            if (-not $allowedSids.ContainsKey($sid)) {
                $unexpected.Add($sid)
            }
            if ($rule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Deny) {
                $denyCount += 1
            }
            if ($rule.IsInherited) {
                $safeShape = (
                    $allowedSids.ContainsKey($sid) -and
                    $rule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow -and
                    $rule.FileSystemRights -eq [System.Security.AccessControl.FileSystemRights]::FullControl -and
                    $rule.InheritanceFlags -eq $expectedFlags -and
                    $rule.PropagationFlags -eq [System.Security.AccessControl.PropagationFlags]::None
                )
                if (-not $safeShape -or $inheritedAllowedSids.ContainsKey($sid)) {
                    $unsafeInherited.Add($item.FullName)
                }
                $inheritedAllowedSids[$sid] = $true
            }
        }

        if ($inheritedAllowedSids.Count -ne 0 -and $inheritedAllowedSids.Count -ne $allowedSids.Count) {
            $unsafeInherited.Add($item.FullName)
        }
    }

    if ($unexpected.Count -gt 0) {
        $principals = @($unexpected | Sort-Object -Unique)
        throw "Unexpected principal detected: $($principals -join ', ')"
    }
    if ($denyCount -gt 0) {
        throw "Deny access rule detected ($denyCount rule(s))"
    }
    if ($unsafeInherited.Count -gt 0) {
        throw "Inherited rule does not originate from the protected root: $($unsafeInherited[0])"
    }
}

function Assert-StrictAclTree {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo[]]$Objects,
        [Parameter(Mandatory)][object[]]$AllowedPrincipals
    )

    $allowedSids = @{}
    foreach ($principal in $AllowedPrincipals) {
        $allowedSids[$principal.Sid.Value] = $principal.Name
    }

    $unexpected = [System.Collections.Generic.List[string]]::new()
    $inheritedRuleCount = 0
    $protectedObjectCount = 0
    $denyCount = 0
    $shapeErrors = [System.Collections.Generic.List[string]]::new()

    foreach ($item in $Objects) {
        $acl = Get-Acl -LiteralPath $item.FullName
        if ($acl.AreAccessRulesProtected) {
            $protectedObjectCount += 1
        }
        else {
            $shapeErrors.Add("unprotected ACL: $($item.FullName)")
        }

        $rules = @(Get-SidRules -Acl $acl)
        $seenAllowedSids = @{}
        $expectedFlags = Get-ExpectedInheritanceFlags -Item $item
        foreach ($rule in $rules) {
            $sid = $rule.IdentityReference.Value
            if ($rule.IsInherited) {
                $inheritedRuleCount += 1
            }
            if (-not $allowedSids.ContainsKey($sid)) {
                $unexpected.Add($sid)
                continue
            }
            if ($rule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Deny) {
                $denyCount += 1
                continue
            }
            if ($seenAllowedSids.ContainsKey($sid)) {
                $shapeErrors.Add("duplicate access rule: $($item.FullName)")
            }
            $seenAllowedSids[$sid] = $true
            if (
                $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or
                $rule.FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl -or
                $rule.InheritanceFlags -ne $expectedFlags -or
                $rule.PropagationFlags -ne [System.Security.AccessControl.PropagationFlags]::None
            ) {
                $shapeErrors.Add("incorrect access rule: $($item.FullName)")
            }
        }
        if ($seenAllowedSids.Count -ne $allowedSids.Count -or $rules.Count -ne $allowedSids.Count) {
            $shapeErrors.Add("ACL does not contain exactly the allowed principals: $($item.FullName)")
        }
    }

    if ($unexpected.Count -gt 0) {
        $principals = @($unexpected | Sort-Object -Unique)
        throw "Unexpected principal detected: $($principals -join ', ')"
    }
    if ($denyCount -gt 0) {
        throw "Deny access rule detected ($denyCount rule(s))"
    }
    if ($inheritedRuleCount -gt 0) {
        throw "Inherited access rules detected ($inheritedRuleCount rule(s))"
    }
    if ($shapeErrors.Count -gt 0) {
        throw $shapeErrors[0]
    }

    return [pscustomobject]@{
        ObjectCount = $Objects.Count
        ProtectedObjectCount = $protectedObjectCount
        InheritedRuleCount = $inheritedRuleCount
    }
}

function New-Evidence {
    param(
        [Parameter(Mandatory)][string]$RootPath,
        [Parameter(Mandatory)][object[]]$AllowedPrincipals,
        [Parameter(Mandatory)]$Stats
    )

    return [ordered]@{
        checked_at = [System.DateTime]::UtcNow.ToString(
            'o',
            [System.Globalization.CultureInfo]::InvariantCulture
        )
        root = $RootPath
        allowed_principals = @($AllowedPrincipals | ForEach-Object { $_.Name })
        object_count = $Stats.ObjectCount
        protected_object_count = $Stats.ProtectedObjectCount
        unexpected_principals = @()
        inherited_rule_count = $Stats.InheritedRuleCount
        reparse_point_count = 0
        alternate_stream_count = 0
    }
}

function Invoke-Main {
    $rootPath = Get-ResolvedRoot -Path $Root
    $allowedPrincipals = @(Get-AllowedPrincipals)

    if ($Mode -eq 'CreateRoot') {
        if ($null -ne (Get-Item -LiteralPath $rootPath -Force -ErrorAction SilentlyContinue)) {
            throw "Artifact root already exists: $rootPath"
        }
        $rootItem = [System.IO.Directory]::CreateDirectory($rootPath)
        Set-ExactAcl -Item $rootItem -AllowedPrincipals $allowedPrincipals
    }

    $objects = @(Get-TreeObjects -RootPath $rootPath)
    Assert-NoHostileObjects -Objects $objects

    if ($Mode -eq 'NormalizeAndVerify') {
        Assert-NormalizationPreflight -Objects $objects -AllowedPrincipals $allowedPrincipals
        foreach ($item in $objects) {
            Set-ExactAcl -Item $item -AllowedPrincipals $allowedPrincipals
        }
        $objects = @(Get-TreeObjects -RootPath $rootPath)
        Assert-NoHostileObjects -Objects $objects
    }

    $stats = Assert-StrictAclTree -Objects $objects -AllowedPrincipals $allowedPrincipals
    $evidence = New-Evidence -RootPath $rootPath -AllowedPrincipals $allowedPrincipals -Stats $stats
    Write-Output ($evidence | ConvertTo-Json -Compress -Depth 4)
}

try {
    Invoke-Main
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
