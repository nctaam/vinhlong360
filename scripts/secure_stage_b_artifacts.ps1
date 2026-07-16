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

function Initialize-StableIdentityType {
    if ($null -eq ('StageBFileIdentity' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class StageBFileIdentity
{
    [StructLayout(LayoutKind.Sequential)]
    private struct FileTime
    {
        public uint LowDateTime;
        public uint HighDateTime;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ByHandleFileInformation
    {
        public uint FileAttributes;
        public FileTime CreationTime;
        public FileTime LastAccessTime;
        public FileTime LastWriteTime;
        public uint VolumeSerialNumber;
        public uint FileSizeHigh;
        public uint FileSizeLow;
        public uint NumberOfLinks;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, EntryPoint = "CreateFileW", SetLastError = true)]
    private static extern SafeFileHandle CreateFile(
        string fileName,
        uint desiredAccess,
        uint shareMode,
        IntPtr securityAttributes,
        uint creationDisposition,
        uint flagsAndAttributes,
        IntPtr templateFile
    );

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetFileInformationByHandle(
        SafeFileHandle handle,
        out ByHandleFileInformation information
    );

    public static string Get(string path)
    {
        const uint shareRead = 0x00000001;
        const uint shareWrite = 0x00000002;
        const uint shareDelete = 0x00000004;
        const uint openExisting = 3;
        const uint backupSemantics = 0x02000000;
        const uint openReparsePoint = 0x00200000;

        using (SafeFileHandle handle = CreateFile(
            path,
            0,
            shareRead | shareWrite | shareDelete,
            IntPtr.Zero,
            openExisting,
            backupSemantics | openReparsePoint,
            IntPtr.Zero
        ))
        {
            if (handle.IsInvalid)
            {
                throw new IOException("Unable to open path for stable identity", new Win32Exception(Marshal.GetLastWin32Error()));
            }
            if (!GetFileInformationByHandle(handle, out ByHandleFileInformation information))
            {
                throw new IOException("Unable to read stable file identity", new Win32Exception(Marshal.GetLastWin32Error()));
            }
            return string.Format(
                "{0:X8}:{1:X8}:{2:X8}",
                information.VolumeSerialNumber,
                information.FileIndexHigh,
                information.FileIndexLow
            );
        }
    }
}
'@
    }
}

function Get-ResolvedRoot {
    param([Parameter(Mandatory)][string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $pathRoot = [System.IO.Path]::GetPathRoot($fullPath)
    if ($fullPath.Length -gt $pathRoot.Length) {
        $fullPath = $fullPath.TrimEnd('\', '/')
    }
    $existing = Get-Item -LiteralPath $fullPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        $fullPath = [System.IO.Path]::GetFullPath($existing.FullName)
        $pathRoot = [System.IO.Path]::GetPathRoot($fullPath)
        if ($fullPath.Length -gt $pathRoot.Length) {
            $fullPath = $fullPath.TrimEnd('\', '/')
        }
    }
    return $fullPath
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

function Get-ObjectPathKey {
    param([Parameter(Mandatory)][string]$Path)

    return (Get-ResolvedRoot -Path $Path).ToUpperInvariant()
}

function Assert-PathWithinRoot {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$RootPath
    )

    $candidate = Get-ResolvedRoot -Path $Path
    $root = Get-ResolvedRoot -Path $RootPath
    $same = [System.StringComparer]::OrdinalIgnoreCase.Equals($candidate, $root)
    $prefix = if ($root.EndsWith('\') -or $root.EndsWith('/')) { $root } else { "$root\" }
    $underRoot = $candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
    if (-not ($same -or $underRoot)) {
        throw "Path escapes the artifact root: $candidate"
    }
    return $candidate
}

function Assert-NoReparseAncestors {
    param([Parameter(Mandatory)][string]$Path)

    $current = Get-ResolvedRoot -Path $Path
    while ($null -ne $current) {
        $item = Get-Item -LiteralPath $current -Force -ErrorAction SilentlyContinue
        if ($null -eq $item) {
            $parent = [System.IO.Directory]::GetParent($current)
            $current = if ($null -eq $parent) { $null } else { $parent.FullName }
            continue
        }
        if (Test-IsReparsePoint -Item $item) {
            throw "Reparse point in path ancestry: $current"
        }
        $parent = [System.IO.Directory]::GetParent($current)
        if ($null -eq $parent -or $parent.FullName -eq $current) {
            break
        }
        $current = $parent.FullName
    }
}

function Get-FreshObjectSnapshot {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$RootPath,
        [string]$ExpectedIdentity
    )

    $canonicalPath = Assert-PathWithinRoot -Path $Path -RootPath $RootPath
    Assert-NoReparseAncestors -Path $canonicalPath
    $item = Get-Item -LiteralPath $canonicalPath -Force
    if (Test-IsReparsePoint -Item $item) {
        throw "Reparse point detected: $canonicalPath"
    }
    Initialize-StableIdentityType
    $identity = [StageBFileIdentity]::Get($canonicalPath)
    if (-not [string]::IsNullOrEmpty($ExpectedIdentity) -and $identity -ne $ExpectedIdentity) {
        throw "Stable identity changed: $canonicalPath"
    }
    return [pscustomobject]@{
        Item = $item
        Path = $canonicalPath
        Identity = $identity
        Attributes = $item.Attributes
        IsDirectory = Test-IsDirectory -Item $item
    }
}

function Assert-SnapshotUnchanged {
    param(
        [Parameter(Mandatory)]$Before,
        [Parameter(Mandatory)]$After
    )

    if (
        $Before.Identity -ne $After.Identity -or
        $Before.Attributes -ne $After.Attributes -or
        $Before.IsDirectory -ne $After.IsDirectory
    ) {
        throw "Stable object identity or attributes changed: $($Before.Path)"
    }
}

function Add-StableIdentity {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo]$Item,
        [Parameter(Mandatory)]$Snapshot
    )

    $Item | Add-Member -MemberType NoteProperty -Name StableIdentity -Value $Snapshot.Identity -Force
    return $Item
}

function Get-TreeObjects {
    param([Parameter(Mandatory)][string]$RootPath)

    $rootSnapshot = Get-FreshObjectSnapshot -Path $RootPath -RootPath $RootPath
    if (-not $rootSnapshot.IsDirectory) {
        throw "Artifact root is not a directory: $RootPath"
    }
    $rootItem = Add-StableIdentity -Item $rootSnapshot.Item -Snapshot $rootSnapshot

    $objects = [System.Collections.Generic.List[System.IO.FileSystemInfo]]::new()
    $directories = [System.Collections.Generic.Queue[System.IO.DirectoryInfo]]::new()
    $objects.Add($rootItem)
    if (-not (Test-IsReparsePoint -Item $rootItem)) {
        $directories.Enqueue($rootItem)
    }

    while ($directories.Count -gt 0) {
        $directory = $directories.Dequeue()
        $beforeEnumeration = Get-FreshObjectSnapshot `
            -Path $directory.FullName `
            -RootPath $RootPath `
            -ExpectedIdentity $directory.StableIdentity
        if (-not $beforeEnumeration.IsDirectory) {
            throw "Directory changed into a non-directory before enumeration: $($directory.FullName)"
        }
        $children = @(
            [System.IO.Directory]::EnumerateFileSystemEntries($directory.FullName) |
                Sort-Object
        )
        $afterEnumeration = Get-FreshObjectSnapshot `
            -Path $directory.FullName `
            -RootPath $RootPath `
            -ExpectedIdentity $directory.StableIdentity
        Assert-SnapshotUnchanged -Before $beforeEnumeration -After $afterEnumeration
        foreach ($childPath in $children) {
            $childSnapshot = Get-FreshObjectSnapshot -Path $childPath -RootPath $RootPath
            $child = Add-StableIdentity -Item $childSnapshot.Item -Snapshot $childSnapshot
            $objects.Add($child)
            if ($childSnapshot.IsDirectory) {
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

function Get-SafeAcl {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo]$Item,
        [Parameter(Mandatory)][string]$RootPath
    )

    $expectedIdentity = $null
    if ($null -ne $Item.PSObject.Properties['StableIdentity']) {
        $expectedIdentity = $Item.StableIdentity
    }
    $before = Get-FreshObjectSnapshot -Path $Item.FullName -RootPath $RootPath -ExpectedIdentity $expectedIdentity
    $acl = Get-Acl -LiteralPath $before.Item.FullName
    $after = Get-FreshObjectSnapshot -Path $before.Path -RootPath $RootPath -ExpectedIdentity $before.Identity
    Assert-SnapshotUnchanged -Before $before -After $after
    return [pscustomobject]@{
        Acl = $acl
        Snapshot = $after
    }
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
        [Parameter(Mandatory)][object[]]$AllowedPrincipals,
        [Parameter(Mandatory)][string]$RootPath
    )

    $safeAcl = Get-SafeAcl -Item $Item -RootPath $RootPath
    $acl = $safeAcl.Acl
    $freshItem = $safeAcl.Snapshot.Item
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @(Get-SidRules -Acl $acl)) {
        $acl.RemoveAccessRuleSpecific($rule)
    }

    $inheritanceFlags = Get-ExpectedInheritanceFlags -Item $freshItem
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
    $beforeWrite = Get-FreshObjectSnapshot `
        -Path $freshItem.FullName `
        -RootPath $RootPath `
        -ExpectedIdentity $safeAcl.Snapshot.Identity
    Assert-SnapshotUnchanged -Before $safeAcl.Snapshot -After $beforeWrite
    # Provider Set-Acl is path-based; post-write identity checks fail closed if a same-user swap wins the residual race.
    Set-Acl -LiteralPath $beforeWrite.Item.FullName -AclObject $acl
    $afterWrite = Get-FreshObjectSnapshot `
        -Path $beforeWrite.Path `
        -RootPath $RootPath `
        -ExpectedIdentity $beforeWrite.Identity
    Assert-SnapshotUnchanged -Before $beforeWrite -After $afterWrite
}

function Assert-NoHostileObjects {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo[]]$Objects,
        [Parameter(Mandatory)][string]$RootPath
    )

    foreach ($item in $Objects) {
        $expectedIdentity = $null
        if ($null -ne $item.PSObject.Properties['StableIdentity']) {
            $expectedIdentity = $item.StableIdentity
        }
        $before = Get-FreshObjectSnapshot -Path $item.FullName -RootPath $RootPath -ExpectedIdentity $expectedIdentity
        $namedStreams = @(
            Get-Item -LiteralPath $before.Item.FullName -Stream * |
                Where-Object { $_.Stream -ne ':$DATA' }
        )
        if ($namedStreams.Count -gt 0) {
            throw "Alternate data stream detected: $($before.Path)$($namedStreams[0].Stream)"
        }
        $after = Get-FreshObjectSnapshot -Path $before.Path -RootPath $RootPath -ExpectedIdentity $before.Identity
        Assert-SnapshotUnchanged -Before $before -After $after
    }
}

function Get-ParentDirectoryPath {
    param([Parameter(Mandatory)][System.IO.FileSystemInfo]$Item)

    if (Test-IsDirectory -Item $Item) {
        if ($null -eq $Item.Parent) {
            return $null
        }
        return $Item.Parent.FullName
    }
    return $Item.DirectoryName
}

function Assert-InheritedRuleOrigin {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo]$Item,
        [Parameter(Mandatory)][string]$RootPath,
        [Parameter(Mandatory)]$ObjectByPath,
        [Parameter(Mandatory)]$AllowedSids
    )

    $rootKey = Get-ObjectPathKey -Path $RootPath
    $parentPath = Get-ParentDirectoryPath -Item $Item
    while ($null -ne $parentPath) {
        $parentKey = Get-ObjectPathKey -Path $parentPath
        if ($parentKey -eq $rootKey) {
            return
        }
        if (-not $ObjectByPath.ContainsKey($parentKey)) {
            throw "Inherited rule has an ancestor outside the protected root: $parentPath"
        }

        $ancestor = $ObjectByPath[$parentKey]
        $ancestorAcl = (Get-SafeAcl -Item $ancestor -RootPath $RootPath).Acl
        if ($ancestorAcl.AreAccessRulesProtected) {
            throw "Inherited rule originates at a protected non-root ancestor: $($ancestor.FullName)"
        }

        $explicitRules = @(
            $ancestorAcl.GetAccessRules(
                $true,
                $false,
                [System.Security.Principal.SecurityIdentifier]
            )
        )
        foreach ($rule in $explicitRules) {
            if (
                $AllowedSids.ContainsKey($rule.IdentityReference.Value) -and
                $rule.AccessControlType -eq [System.Security.AccessControl.AccessControlType]::Allow -and
                $rule.InheritanceFlags -ne [System.Security.AccessControl.InheritanceFlags]::None
            ) {
                throw "Inherited rule originates at an explicit non-root ancestor: $($ancestor.FullName)"
            }
        }

        $parentPath = Get-ParentDirectoryPath -Item $ancestor
    }

    throw "Inherited rule has no protected root ancestor: $($Item.FullName)"
}

function Assert-NormalizationPreflight {
    param(
        [Parameter(Mandatory)][System.IO.FileSystemInfo[]]$Objects,
        [Parameter(Mandatory)][object[]]$AllowedPrincipals,
        [Parameter(Mandatory)][string]$RootPath
    )

    $allowedSids = @{}
    foreach ($principal in $AllowedPrincipals) {
        $allowedSids[$principal.Sid.Value] = $true
    }

    $objectByPath = @{}
    foreach ($object in $Objects) {
        $objectByPath[(Get-ObjectPathKey -Path $object.FullName)] = $object
    }

    $rootAcl = (Get-SafeAcl -Item $Objects[0] -RootPath $RootPath).Acl
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
        $safeAcl = Get-SafeAcl -Item $item -RootPath $RootPath
        $acl = $safeAcl.Acl
        $rules = @(Get-SidRules -Acl $acl)
        $expectedFlags = Get-ExpectedInheritanceFlags -Item $safeAcl.Snapshot.Item
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
        if ($inheritedAllowedSids.Count -gt 0) {
            Assert-InheritedRuleOrigin -Item $item -RootPath $RootPath -ObjectByPath $objectByPath -AllowedSids $allowedSids
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
        [Parameter(Mandatory)][object[]]$AllowedPrincipals,
        [Parameter(Mandatory)][string]$RootPath
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
        $safeAcl = Get-SafeAcl -Item $item -RootPath $RootPath
        $acl = $safeAcl.Acl
        if ($acl.AreAccessRulesProtected) {
            $protectedObjectCount += 1
        }
        else {
            $shapeErrors.Add("unprotected ACL: $($item.FullName)")
        }

        $rules = @(Get-SidRules -Acl $acl)
        $seenAllowedSids = @{}
        $expectedFlags = Get-ExpectedInheritanceFlags -Item $safeAcl.Snapshot.Item
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
    if ($allowedPrincipals.Count -ne 3) {
        throw "Exactly three distinct allowed principals are required; resolved $($allowedPrincipals.Count)"
    }
    Assert-NoReparseAncestors -Path $rootPath

    if ($Mode -eq 'CreateRoot') {
        if ($null -ne (Get-Item -LiteralPath $rootPath -Force -ErrorAction SilentlyContinue)) {
            throw "Artifact root already exists: $rootPath"
        }
        $rootItem = [System.IO.Directory]::CreateDirectory($rootPath)
        $rootSnapshot = Get-FreshObjectSnapshot -Path $rootPath -RootPath $rootPath
        $rootItem = Add-StableIdentity -Item $rootSnapshot.Item -Snapshot $rootSnapshot
        Set-ExactAcl -Item $rootItem -AllowedPrincipals $allowedPrincipals -RootPath $rootPath
    }

    $objects = @(Get-TreeObjects -RootPath $rootPath)
    Assert-NoHostileObjects -Objects $objects -RootPath $rootPath

    if ($Mode -eq 'NormalizeAndVerify') {
        Assert-NormalizationPreflight -Objects $objects -AllowedPrincipals $allowedPrincipals -RootPath $rootPath
        foreach ($item in $objects) {
            Set-ExactAcl -Item $item -AllowedPrincipals $allowedPrincipals -RootPath $rootPath
        }
        $objects = @(Get-TreeObjects -RootPath $rootPath)
        Assert-NoHostileObjects -Objects $objects -RootPath $rootPath
    }

    $stats = Assert-StrictAclTree -Objects $objects -AllowedPrincipals $allowedPrincipals -RootPath $rootPath
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
