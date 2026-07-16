from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows ACL contract")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "secure_stage_b_artifacts.ps1"
PWSH = shutil.which("pwsh") or r"C:\Program Files\PowerShell\7\pwsh.exe"


def _pwsh(mode: str, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            PWSH,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(SCRIPT),
            "-Mode",
            mode,
            "-Root",
            str(root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _evidence(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert completed.stdout.strip()
    assert completed.stdout.strip().count("\n") == 0
    return json.loads(completed.stdout)


def _grant_read_rule(path: Path, principal: str) -> None:
    command = r"""
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $env:ACL_TEST_PATH
$rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
    $env:ACL_TEST_PRINCIPAL,
    [System.Security.AccessControl.FileSystemRights]::Read,
    [System.Security.AccessControl.AccessControlType]::Allow
)
$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $env:ACL_TEST_PATH -AclObject $acl
"""
    env = os.environ.copy()
    env["ACL_TEST_PATH"] = str(path)
    env["ACL_TEST_PRINCIPAL"] = principal
    completed = subprocess.run(
        [PWSH, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr


def _acl_snapshot(path: Path) -> dict[str, object]:
    command = r"""
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $env:ACL_TEST_PATH
$rules = @($acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]))
[ordered]@{
    protected = $acl.AreAccessRulesProtected
    inherited = @($rules | Where-Object IsInherited).Count
    sddl = $acl.GetSecurityDescriptorSddlForm([System.Security.AccessControl.AccessControlSections]::Access)
} | ConvertTo-Json -Compress
"""
    env = os.environ.copy()
    env["ACL_TEST_PATH"] = str(path)
    completed = subprocess.run(
        [PWSH, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    return json.loads(completed.stdout)


def test_create_root_secures_absent_root_and_emits_json_evidence(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"

    evidence = _evidence(_pwsh("CreateRoot", artifact_root))

    assert artifact_root.is_dir()
    assert evidence["root"] == str(artifact_root.resolve())
    assert evidence["object_count"] == 1
    assert evidence["protected_object_count"] == 1
    assert evidence["unexpected_principals"] == []
    assert evidence["inherited_rule_count"] == 0
    allowed = evidence["allowed_principals"]
    assert isinstance(allowed, list)
    assert allowed == sorted(set(allowed), key=str.casefold)
    assert len(allowed) == 3
    assert "NT AUTHORITY\\SYSTEM" in allowed
    assert "BUILTIN\\Administrators" in allowed


def test_create_root_rejects_existing_directory_without_touching_it(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"
    artifact_root.mkdir()
    artifact = artifact_root / "keep.txt"
    artifact.write_text("keep", encoding="utf-8")

    completed = _pwsh("CreateRoot", artifact_root)

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "already exists" in completed.stderr.lower()
    assert artifact.read_text(encoding="utf-8") == "keep"


def test_normalize_rejects_named_alternate_stream_and_preserves_artifact(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"
    _evidence(_pwsh("CreateRoot", artifact_root))
    artifact = artifact_root / "artifact.txt"
    artifact.write_text("artifact bytes", encoding="utf-8")
    with open(f"{artifact}:hostile", "w", encoding="utf-8") as stream:
        stream.write("hidden bytes")

    completed = _pwsh("NormalizeAndVerify", artifact_root)

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "alternate data stream" in completed.stderr.lower()
    assert artifact.read_text(encoding="utf-8") == "artifact bytes"
    with open(f"{artifact}:hostile", encoding="utf-8") as stream:
        assert stream.read() == "hidden bytes"


def test_verify_rejects_unexpected_principal_and_preserves_artifact(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"
    _evidence(_pwsh("CreateRoot", artifact_root))
    artifact = artifact_root / "artifact.txt"
    artifact.write_text("keep", encoding="utf-8")
    _grant_read_rule(artifact, r"BUILTIN\Users")

    completed = _pwsh("Verify", artifact_root)

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "unexpected principal" in completed.stderr.lower()
    assert artifact.read_text(encoding="utf-8") == "keep"


def test_normalize_rejects_reparse_point_before_acl_changes(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"
    _evidence(_pwsh("CreateRoot", artifact_root))
    target = artifact_root / "target.txt"
    target.write_text("target bytes", encoding="utf-8")
    link = artifact_root / "link.txt"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"Windows symlink creation unavailable: {exc}")

    completed = _pwsh("NormalizeAndVerify", artifact_root)

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "reparse point" in completed.stderr.lower()
    assert os.path.lexists(link)
    assert link.is_symlink()
    assert target.read_text(encoding="utf-8") == "target bytes"


def test_verify_rejects_new_child_with_inherited_rules_and_preserves_it(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"
    _evidence(_pwsh("CreateRoot", artifact_root))
    artifact = artifact_root / "artifact.txt"
    artifact.write_text("keep", encoding="utf-8")

    completed = _pwsh("Verify", artifact_root)

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "inherited" in completed.stderr.lower()
    assert artifact.read_text(encoding="utf-8") == "keep"


def test_normalize_rejects_inherited_rules_originating_at_nested_protected_parent(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"
    _evidence(_pwsh("CreateRoot", artifact_root))
    parent = artifact_root / "nested"
    parent.mkdir()
    _evidence(_pwsh("NormalizeAndVerify", artifact_root))
    child = parent / "child.txt"
    child.write_text("child bytes", encoding="utf-8")
    child_before = _acl_snapshot(child)

    completed = _pwsh("NormalizeAndVerify", artifact_root)

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "ancestor" in completed.stderr.lower()
    assert child.read_text(encoding="utf-8") == "child bytes"
    assert _acl_snapshot(child) == child_before


def test_normalize_preflight_preserves_safe_earlier_child_when_later_child_is_hostile(
    tmp_path: Path,
):
    artifact_root = tmp_path / "stage-b"
    _evidence(_pwsh("CreateRoot", artifact_root))
    safe = artifact_root / "a-safe.txt"
    hostile = artifact_root / "z-hostile.txt"
    safe.write_text("safe bytes", encoding="utf-8")
    hostile.write_text("hostile bytes", encoding="utf-8")
    _grant_read_rule(hostile, r"BUILTIN\Users")
    safe_before = _acl_snapshot(safe)
    hostile_before = _acl_snapshot(hostile)

    completed = _pwsh("NormalizeAndVerify", artifact_root)

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "unexpected principal" in completed.stderr.lower()
    assert safe.read_text(encoding="utf-8") == "safe bytes"
    assert hostile.read_text(encoding="utf-8") == "hostile bytes"
    assert _acl_snapshot(safe) == safe_before
    assert _acl_snapshot(hostile) == hostile_before


def test_normalize_converts_safe_inheritance_and_is_idempotent(tmp_path: Path):
    artifact_root = tmp_path / "stage-b"
    _evidence(_pwsh("CreateRoot", artifact_root))
    artifact = artifact_root / "artifact.txt"
    artifact.write_text("keep", encoding="utf-8")

    first = _evidence(_pwsh("NormalizeAndVerify", artifact_root))
    second = _evidence(_pwsh("NormalizeAndVerify", artifact_root))

    for evidence in (first, second):
        assert evidence["object_count"] == 2
        assert evidence["protected_object_count"] == 2
        assert evidence["unexpected_principals"] == []
        assert evidence["inherited_rule_count"] == 0
        assert evidence["reparse_point_count"] == 0
        assert evidence["alternate_stream_count"] == 0
    assert artifact.read_text(encoding="utf-8") == "keep"
