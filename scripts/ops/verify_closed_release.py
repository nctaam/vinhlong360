#!/usr/bin/env python3
"""Verify a Task 31 closed launch archive or an installed closed tree.

The adjacent SHA-256 file is an integrity sidecar, not a signature.  Archive
verification is intentionally independent of Docker, Nginx, systemd, and
package managers so it can run before any maintenance mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import tarfile
import tempfile
import time
from typing import Any, BinaryIO, Mapping

if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    import msvcrt


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SIDECAR_RE = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)\n?$")
FINDMNT_SOURCE_ROOT_RE = re.compile(
    r"^(?P<device>[^\[\]]+)\[(?P<root>/[^\[\]]*)\]$"
)
REQUIRED_MEMBERS = frozenset(
    {
        "config/launch-indexing-policy.json",
        "config/ai-disclosure.json",
        "web-nuxt/.output/server/launch-readiness-manifest.json",
        "nginx.conf",
        "nginx-ssl.conf",
        "compose-network-audit.json",
        "ops/systemd/vl-agent.service",
        "ops/systemd/vl-nuxt.service",
        "ops/systemd/vl-bot.service",
        "ops/systemd/vl-watchdog.service",
        "ops/systemd/vl-watchdog.timer",
        "scripts/check_migration_gate.py",
        "scripts/ops/verify_closed_release.py",
        "scripts/ops/install_closed_release.sh",
    }
)
PERSISTENT_PATHS = ["agent/data", "agent/data/sitemap-bundles"]
SYSTEMD_UNIT_PATHS = (
    "ops/systemd/vl-agent.service",
    "ops/systemd/vl-nuxt.service",
    "ops/systemd/vl-bot.service",
    "ops/systemd/vl-watchdog.service",
    "ops/systemd/vl-watchdog.timer",
)
CONFIG_INGRESS_UNIT_PATHS = (
    "config/launch-indexing-policy.json",
    "config/ai-disclosure.json",
    "nginx.conf",
    "nginx-ssl.conf",
    "compose-network-audit.json",
    *SYSTEMD_UNIT_PATHS,
)
ROUTE_REVISION = "launch-indexing-policy-v1"
DISCLOSURE_REVISION = "ai-disclosure-v1"
READINESS_PATH = "web-nuxt/.output/server/launch-readiness-manifest.json"
ROUTE_CLASSES = ["public-html", "public-api", "root-seo", "internal-readiness"]
AUDIT_CHECK_NAMES = (
    "agent_bind_host",
    "bot_bind_host_and_agent_url",
    "container_names_absent",
    "developer_added_publications_loopback",
    "exact_healthcheck_commands",
    "maintenance_initializer_exact",
    "maintenance_runtime_shared_with_host",
    "nginx_depends_on_healthy_nuxt_and_completed_maintenance_init",
    "nginx_exclusive_public_endpoints",
    "no_external_or_host_network",
    "no_launch_unlock_environment",
    "non_nginx_services_unpublished",
    "nuxt_backend_independent_readiness",
    "nuxt_bind_host",
    "nuxt_compose_api_origins",
    "required_services_present",
    "shared_private_bridge_network",
    "systemd_dependency_topology",
)
CANONICAL_ARTIFACTS = (
    ("route_manifest", "config/launch-indexing-policy.json", ROUTE_REVISION),
    ("ai_disclosure", "config/ai-disclosure.json", DISCLOSURE_REVISION),
)
EXPECTED_CACHE_PURGE = {
    "revision": "launch-cache-purge-v1",
    "strategy": "delete-all-except",
    "retained_cache_names": ["vl360-launch-v1-assets"],
    "forbidden_cache_classes": [
        "navigation",
        "html",
        "root-seo",
        "internal",
        "api",
        "selective-open",
        "failed-open",
    ],
    "activation_verified": True,
}

# Protect low-cost hosts from unbounded scratch and expansion use.
MAX_ARCHIVE_SNAPSHOT_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 512 * 1024 * 1024
CHECK_MIGRATION_GATE_MEMBER = "scripts/check_migration_gate.py"
ARCHIVED_VERIFIER_MEMBER = "scripts/ops/verify_closed_release.py"
ARCHIVED_INSTALLER_MEMBER = "scripts/ops/install_closed_release.sh"
MIGRATION_MEMBER_PREFIX = "agent/migrations/"
MIGRATION_MEMBER_RE = re.compile(r"^agent/migrations/(\d{3})_[a-z0-9_]+\.sql$")
MAX_MIGRATION_PREREQUISITE_BYTES = 16 * 1024 * 1024


if os.name == "nt":
    _WINDOWS_GENERIC_READ = 0x80000000
    _WINDOWS_GENERIC_WRITE = 0x40000000
    _WINDOWS_DELETE = 0x00010000
    _WINDOWS_SYNCHRONIZE = 0x00100000
    _WINDOWS_FILE_READ_ATTRIBUTES = 0x00000080
    _WINDOWS_FILE_SHARE_READ = 0x00000001
    _WINDOWS_FILE_SHARE_WRITE = 0x00000002
    _WINDOWS_OPEN_EXISTING = 3
    _WINDOWS_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _WINDOWS_FILE_ATTRIBUTE_NORMAL = 0x00000080
    _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _WINDOWS_FILE_OPEN = 1
    _WINDOWS_FILE_CREATE = 2
    _WINDOWS_FILE_DIRECTORY_FILE = 0x00000001
    _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
    _WINDOWS_FILE_NON_DIRECTORY_FILE = 0x00000040
    _WINDOWS_FILE_OPEN_REPARSE_POINT = 0x00200000
    _WINDOWS_OBJ_CASE_INSENSITIVE = 0x00000040
    _WINDOWS_FILE_ATTRIBUTE_TAG_INFO = 9
    _WINDOWS_FILE_RENAME_INFORMATION = 10
    _WINDOWS_INVALID_HANDLE = ctypes.c_void_p(-1).value

    class _WindowsFileAttributeTagInfo(ctypes.Structure):
        _fields_ = [
            ("file_attributes", wintypes.DWORD),
            ("reparse_tag", wintypes.DWORD),
        ]

    class _WindowsUnicodeString(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.USHORT),
            ("maximum_length", wintypes.USHORT),
            ("buffer", wintypes.LPWSTR),
        ]

    class _WindowsObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.ULONG),
            ("root_directory", wintypes.HANDLE),
            ("object_name", ctypes.POINTER(_WindowsUnicodeString)),
            ("attributes", wintypes.ULONG),
            ("security_descriptor", wintypes.LPVOID),
            ("security_quality_of_service", wintypes.LPVOID),
        ]

    class _WindowsIoStatusBlock(ctypes.Structure):
        _fields_ = [
            ("status", ctypes.c_ssize_t),
            ("information", ctypes.c_size_t),
        ]

    class _WindowsFileRenameInformation(ctypes.Structure):
        _fields_ = [
            ("replace_if_exists", wintypes.BYTE),
            ("root_directory", wintypes.HANDLE),
            ("file_name_length", wintypes.ULONG),
            ("file_name", wintypes.WCHAR * 1),
        ]

    _WINDOWS_KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _WINDOWS_NTDLL = ctypes.WinDLL("ntdll", use_last_error=True)

    _WINDOWS_KERNEL32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _WINDOWS_KERNEL32.CreateFileW.restype = wintypes.HANDLE
    _WINDOWS_KERNEL32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _WINDOWS_KERNEL32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _WINDOWS_KERNEL32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _WINDOWS_KERNEL32.FlushFileBuffers.restype = wintypes.BOOL
    _WINDOWS_KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _WINDOWS_KERNEL32.CloseHandle.restype = wintypes.BOOL
    _WINDOWS_NTDLL.NtCreateFile.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(_WindowsObjectAttributes),
        ctypes.POINTER(_WindowsIoStatusBlock),
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _WINDOWS_NTDLL.NtCreateFile.restype = ctypes.c_long
    _WINDOWS_NTDLL.NtSetInformationFile.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_WindowsIoStatusBlock),
        wintypes.LPVOID,
        wintypes.ULONG,
        ctypes.c_int,
    ]
    _WINDOWS_NTDLL.NtSetInformationFile.restype = ctypes.c_long
    _WINDOWS_NTDLL.RtlNtStatusToDosError.argtypes = [ctypes.c_long]
    _WINDOWS_NTDLL.RtlNtStatusToDosError.restype = wintypes.ULONG


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _read_sidecar(archive: Path, sidecar: Path) -> tuple[str, BinaryIO]:
    if archive.is_symlink() or sidecar.is_symlink():
        raise ValueError("archive and sidecar must not be symlinks")
    if not archive.is_file() or not sidecar.is_file():
        raise FileNotFoundError("closed archive and adjacent SHA-256 sidecar are required")
    raw = sidecar.read_text(encoding="ascii")
    match = SIDECAR_RE.fullmatch(raw)
    if match is None or Path(match.group(2)).name != archive.name:
        raise ValueError("archive SHA-256 sidecar format mismatch")
    expected = match.group(1)
    snapshot = tempfile.TemporaryFile(mode="w+b")
    digest = hashlib.sha256()
    snapshot_size = 0
    try:
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                snapshot_size += len(chunk)
                if snapshot_size > MAX_ARCHIVE_SNAPSHOT_BYTES:
                    raise ValueError("archive exceeds maximum snapshot size")
                digest.update(chunk)
                snapshot.write(chunk)
        observed = digest.hexdigest()
        if observed != expected:
            raise ValueError("archive SHA-256 sidecar mismatch")
        snapshot.seek(0)
        return expected, snapshot
    except BaseException:
        snapshot.close()
        raise


def _validate_member_path(name: str) -> None:
    if not name or "\\" in name:
        raise ValueError(f"unsafe archive member: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe archive member: {name!r}")


def _validate_member_exclusions(name: str) -> None:
    if name == "agent/data" or name.startswith("agent/data/"):
        raise ValueError("persistent agent data must never be packaged")
    lower = name.lower()
    if lower == ".env" or lower.endswith("/.env") or "docker-compose.dev.yml" in lower:
        raise ValueError("developer override or environment material is not closed")
    if "unlock" in lower or "secret" in lower:
        raise ValueError("unlock or secret material is not closed")


def _validate_member_name(name: str) -> None:
    _validate_member_path(name)
    _validate_member_exclusions(name)


def _member_bytes(member: tarfile.TarInfo, archive: tarfile.TarFile) -> bytes:
    if not member.isfile():
        return b""
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"archive member cannot be read: {member.name}")
    payload = bytearray()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        payload.extend(chunk)
        if len(payload) > member.size or len(payload) > MAX_ARCHIVE_MEMBER_BYTES:
            raise ValueError(
                f"archive member exceeds maximum expanded size: {member.name}"
            )
    if len(payload) != member.size:
        raise ValueError(f"archive member size mismatch: {member.name}")
    return bytes(payload)


def _admit_archive_member(
    member: tarfile.TarInfo,
    names: set[str],
    expanded_size: int,
) -> int:
    _validate_member_name(member.name)
    if member.name in names:
        raise ValueError(f"duplicate archive member: {member.name}")
    names.add(member.name)
    if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
        raise ValueError(f"archive member type is unsafe: {member.name}")
    if not member.isfile():
        return expanded_size
    if member.size < 0 or member.size > MAX_ARCHIVE_MEMBER_BYTES:
        raise ValueError(
            f"archive member exceeds maximum expanded size: {member.name}"
        )
    expanded_size += member.size
    if expanded_size > MAX_ARCHIVE_EXPANDED_BYTES:
        raise ValueError("archive exceeds maximum expanded size")
    return expanded_size


def _read_archive_members(bundle: tarfile.TarFile) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    names: set[str] = set()
    expanded_size = 0
    while True:
        member = bundle.next()
        if member is None:
            break
        expanded_size = _admit_archive_member(member, names, expanded_size)
        if member.isfile():
            members[member.name] = _member_bytes(member, bundle)
    return members


def _validate_manifest_identity(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise ValueError("closed release manifest schema mismatch")
    if manifest.get("package_kind") != "vl360-launch-release":
        raise ValueError("package is not a vl360 launch release")
    if manifest.get("launch_posture") != "closed":
        raise ValueError("closed launch package posture is required")
    if manifest.get("persistent_paths") != PERSISTENT_PATHS:
        raise ValueError("persistent path declaration mismatch")
    developer = manifest.get("developer_override")
    if developer != {"path": "docker-compose.dev.yml", "included": False}:
        raise ValueError("developer override must be excluded")


def _validate_manifest_canonical_artifacts(
    manifest: Mapping[str, Any], members: Mapping[str, bytes]
) -> None:
    canonical = manifest.get("canonical_artifacts")
    if not isinstance(canonical, dict):
        raise ValueError("canonical artifact evidence is missing")
    for key, relative, revision in CANONICAL_ARTIFACTS:
        evidence = canonical.get(key)
        if not isinstance(evidence, dict) or evidence.get("revision") != revision:
            raise ValueError(f"canonical artifact {key} revision mismatch")
        raw = members.get(relative)
        if raw is None or _require_digest(evidence.get("sha256"), f"canonical {key}") != _sha256(raw):
            raise ValueError(f"canonical artifact {key} digest mismatch")


def _validate_manifest_member_digest(
    manifest: Mapping[str, Any],
    members: Mapping[str, bytes],
    *,
    manifest_key: str,
    expected_path: str,
    label: str,
) -> None:
    declaration = manifest.get(manifest_key)
    if not isinstance(declaration, dict) or declaration.get("path") != expected_path:
        raise ValueError(f"{label} declaration mismatch")
    raw = members.get(expected_path)
    if raw is None or _require_digest(declaration.get("sha256"), f"{label} digest") != _sha256(raw):
        raise ValueError(f"{label} digest mismatch")


def _validate_manifest_members(
    manifest: Mapping[str, Any], members: Mapping[str, bytes]
) -> None:
    member_manifest = manifest.get("members")
    if not isinstance(member_manifest, dict):
        raise ValueError("archive member manifest is missing")
    observed = {
        name: {"sha256": _sha256(raw), "size": len(raw)}
        for name, raw in members.items()
        if name != "launch-release-manifest.json"
    }
    if member_manifest != observed:
        raise ValueError("archive member digests do not match manifest")


def _verify_config_ingress_unit_digests(
    manifest: Mapping[str, Any], members: Mapping[str, bytes]
) -> tuple[str, ...]:
    """Recheck the activation-critical config, ingress, and unit bytes."""
    declarations = manifest.get("members")
    if not isinstance(declarations, dict):
        raise ValueError("archive member manifest is missing")
    for relative in CONFIG_INGRESS_UNIT_PATHS:
        declaration = declarations.get(relative)
        raw = members.get(relative)
        if not isinstance(declaration, dict) or raw is None:
            raise ValueError(f"config/ingress/unit declaration missing: {relative}")
        if declaration.get("sha256") != _sha256(raw) or declaration.get("size") != len(raw):
            raise ValueError(f"config/ingress/unit digest mismatch: {relative}")
    return CONFIG_INGRESS_UNIT_PATHS


def _verify_systemd_unit_destination(
    manifest: Mapping[str, Any], destination: Path
) -> tuple[str, ...]:
    declarations = manifest.get("members")
    if not isinstance(declarations, dict):
        raise ValueError("archive member manifest is missing")
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError("systemd unit destination is not a real directory")
    for relative in SYSTEMD_UNIT_PATHS:
        declaration = declarations.get(relative)
        path = destination / Path(relative).name
        if not isinstance(declaration, dict) or path.is_symlink() or not path.is_file():
            raise ValueError(f"installed systemd unit missing: {path.name}")
        raw = path.read_bytes()
        if declaration.get("sha256") != _sha256(raw) or declaration.get("size") != len(raw):
            raise ValueError(f"installed systemd unit digest mismatch: {path.name}")
    return SYSTEMD_UNIT_PATHS


def _verify_environment_authority(root: Path, authority: Path) -> dict[str, Any]:
    authority = Path(authority)
    target = Path(root) / ".env"
    if authority.is_symlink() or not authority.is_file():
        raise ValueError("environment authority is not a real file")
    if target.is_symlink() or not target.is_file():
        raise ValueError("installed environment authority is not a real file")
    authority_raw = authority.read_bytes()
    target_raw = target.read_bytes()
    if target_raw != authority_raw:
        raise ValueError("installed environment authority bytes do not match")
    if os.name != "nt" and target.stat().st_mode & 0o077:
        raise ValueError("installed environment authority permissions are too broad")
    return {
        "environment_authority_target": ".env",
        "environment_authority_verified": True,
    }


def _findmnt_device_matches_source(device: str, expected_source: Path) -> bool:
    try:
        device_stat = os.stat(device)
        source_stat = os.stat(expected_source)
    except OSError:
        return False
    if not stat.S_ISBLK(device_stat.st_mode):
        return False
    return (
        os.major(device_stat.st_rdev) == os.major(source_stat.st_dev)
        and os.minor(device_stat.st_rdev) == os.minor(source_stat.st_dev)
    )


def _validate_findmnt_source(
    observed_source: str, expected_source_resolved: Path
) -> bool:
    observed_source_resolved = Path(observed_source).resolve()
    if observed_source_resolved == expected_source_resolved:
        return False
    bracketed_source = FINDMNT_SOURCE_ROOT_RE.fullmatch(observed_source)
    if bracketed_source is None:
        raise ValueError("findmnt source does not match persistent authority")
    normalized_root = Path(bracketed_source.group("root")).resolve()
    if normalized_root != expected_source_resolved:
        raise ValueError("findmnt source does not match persistent authority")
    if not _findmnt_device_matches_source(
        bracketed_source.group("device"), expected_source_resolved
    ):
        raise ValueError("findmnt source device does not match persistent authority")
    return True


def _normalize_findmnt_options(options: object) -> set[str]:
    if isinstance(options, list):
        raw_option_values = set(options)
    elif isinstance(options, str):
        raw_option_values = set(options.split(","))
    else:
        raw_option_values = set()
    raw_option_values.discard("")
    return raw_option_values


def validate_findmnt_evidence(
    payload: Mapping[str, Any], *, expected_source: Path, expected_target: Path
) -> dict[str, Any]:
    filesystems = payload.get("filesystems")
    if not isinstance(filesystems, list) or len(filesystems) != 1:
        raise ValueError("findmnt evidence must contain one filesystem")
    filesystem = filesystems[0]
    if not isinstance(filesystem, dict):
        raise ValueError("findmnt filesystem evidence is invalid")
    observed_source = filesystem.get("source")
    observed_target = filesystem.get("target")
    options = filesystem.get("options")
    if not isinstance(observed_source, str) or not isinstance(observed_target, str):
        raise ValueError("findmnt source/target evidence is missing")
    expected_source_resolved = Path(expected_source).resolve()
    bind_proven_by_source = _validate_findmnt_source(
        observed_source, expected_source_resolved
    )
    if Path(observed_target).resolve() != Path(expected_target).resolve():
        raise ValueError("findmnt target does not match installed mountpoint")
    raw_option_values = _normalize_findmnt_options(options)
    option_values = set(raw_option_values)
    if bind_proven_by_source:
        option_values.add("bind")
    if "rw" not in option_values or not ({"bind", "rbind"} & option_values):
        raise ValueError("findmnt options must prove rw bind mount")
    return {
        "source": observed_source,
        "normalized_source": str(expected_source_resolved),
        "target": observed_target,
        "options": sorted(option_values),
        "raw_options": sorted(raw_option_values),
    }


def _verify_persistent_agent_data_mount(
    root: Path,
    external: Path,
    *,
    local_rehearsal: bool = False,
    findmnt_evidence: Path | None = None,
) -> dict[str, Any]:
    target = Path(root) / "agent" / "data"
    external = Path(external)
    if external.is_symlink() or not external.is_dir():
        raise ValueError("persistent agent data authority is not a real directory")
    if target.is_symlink() or not target.is_dir():
        raise ValueError("installed persistent agent data mountpoint is not a real directory")
    if local_rehearsal:
        return {
            "persistent_agent_data_mount_mode": "local-rehearsal",
            "persistent_agent_data_mount_verified": True,
        }
    if findmnt_evidence is None:
        raise ValueError("findmnt evidence is required for persistent mount verification")
    payload = json.loads(Path(findmnt_evidence).read_text(encoding="utf-8"))
    mount = validate_findmnt_evidence(
        payload,
        expected_source=external,
        expected_target=target,
    )
    return {
        "persistent_agent_data_mount_mode": "findmnt",
        "persistent_agent_data_mount_verified": True,
        "persistent_agent_data_mount": mount,
    }


def _validate_manifest(manifest: Mapping[str, Any], members: Mapping[str, bytes]) -> None:
    _validate_manifest_identity(manifest)
    _validate_manifest_canonical_artifacts(manifest, members)
    _validate_manifest_member_digest(
        manifest,
        members,
        manifest_key="readiness_manifest",
        expected_path=READINESS_PATH,
        label="readiness manifest",
    )
    _validate_manifest_member_digest(
        manifest,
        members,
        manifest_key="network_audit",
        expected_path="compose-network-audit.json",
        label="network audit",
    )
    _validate_manifest_members(manifest, members)


def _validate_readiness_identity(
    readiness: Mapping[str, Any], expected_revision: object
) -> None:
    if readiness.get("schema_version") != 1:
        raise ValueError("readiness schema mismatch")
    if not isinstance(expected_revision, str) or not expected_revision or readiness.get("build_revision") != expected_revision:
        raise ValueError("readiness source revision mismatch")
    if readiness.get("policy_route_classes") != ROUTE_CLASSES:
        raise ValueError("readiness route classes mismatch")
    if readiness.get("compiled_cache_rules") != [] or readiness.get("public_prerender_files") != []:
        raise ValueError("closed readiness contains compiled or prerender policy output")


def _validate_readiness_artifacts(
    readiness: Mapping[str, Any], members: Mapping[str, bytes]
) -> Mapping[str, Any]:
    artifacts = readiness.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("readiness artifact evidence is missing")
    for key, relative, revision in CANONICAL_ARTIFACTS:
        item = artifacts.get(key)
        if not isinstance(item, dict) or item.get("revision") != revision:
            raise ValueError(f"readiness {key} revision mismatch")
        if item.get("sha256") != _sha256(members[relative]):
            raise ValueError(f"readiness {key} digest mismatch")
    return artifacts


def _expected_policy_fingerprint(artifacts: Mapping[str, Any]) -> str:
    route = artifacts["route_manifest"]
    disclosure = artifacts["ai_disclosure"]
    payload = {
        "cache_isolation": "launch-cache-isolation-v1",
        "disclosure_artifact": {
            "revision": DISCLOSURE_REVISION,
            "sha256": _sha256(str(disclosure["sha256"]).encode("ascii")),
        },
        "index_policy": "index-policy-v1",
        "response_matrix": "launch-safety-matrix-v1",
        "route_artifact": {
            "revision": ROUTE_REVISION,
            "sha256": _sha256(str(route["sha256"]).encode("ascii")),
        },
        "sitemap_protocol": "pinned-sitemap-bundle-v1",
    }
    return _sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _validate_readiness_fingerprint(artifacts: Mapping[str, Any]) -> None:
    if artifacts.get("policy_fingerprint") != _expected_policy_fingerprint(artifacts):
        raise ValueError("readiness policy fingerprint mismatch")


def _validate_readiness_worker(
    readiness: Mapping[str, Any], members: Mapping[str, bytes]
) -> None:
    worker = readiness.get("service_worker")
    worker_raw = members.get("web-nuxt/.output/public/sw.js")
    if not isinstance(worker, dict) or worker_raw is None:
        raise ValueError("closed readiness service worker evidence is missing")
    if worker.get("version") != "vl360-launch-v1" or worker.get("rule_digest") != _sha256(worker_raw):
        raise ValueError("closed readiness service worker digest mismatch")
    if worker.get("cache_purge") != EXPECTED_CACHE_PURGE:
        raise ValueError("service worker cache purge activation is not verified")


def _validate_readiness(
    readiness: Mapping[str, Any], members: Mapping[str, bytes], expected_revision: object
) -> None:
    _validate_readiness_identity(readiness, expected_revision)
    artifacts = _validate_readiness_artifacts(readiness, members)
    _validate_readiness_fingerprint(artifacts)
    _validate_readiness_worker(readiness, members)


def _validate_network_audit(raw: bytes) -> None:
    audit = _safe_json(raw, "compose network audit")
    if audit.get("schema_version") != 1 or audit.get("revision") != "compose-network-audit-v2":
        raise ValueError("compose network audit revision mismatch")
    expected_checks = sorted(AUDIT_CHECK_NAMES)
    checks = audit.get("checks")
    if audit.get("check_names") != expected_checks or checks != {
        name: "passed" for name in expected_checks
    }:
        raise ValueError("compose network audit check inventory mismatch")
    ports = audit.get("published_ports")
    if not isinstance(ports, list) or len(ports) != 2 or {
        (item.get("service"), item.get("published"), item.get("target"), item.get("protocol"))
        for item in ports
        if isinstance(item, dict)
    } != {("nginx", 80, 80, "tcp"), ("nginx", 443, 443, "tcp")}:
        raise ValueError("compose network audit must expose only Nginx 80/443")


def _validate_loopback_units(members: Mapping[str, bytes]) -> None:
    expectations = {
        "ops/systemd/vl-agent.service": ("BIND_HOST=127.0.0.1",),
        "ops/systemd/vl-nuxt.service": ("HOST=127.0.0.1", "NITRO_HOST=127.0.0.1", "PORT=3000"),
        "ops/systemd/vl-bot.service": ("BIND_HOST=127.0.0.1", "AGENT_URL=http://127.0.0.1:8360"),
        "ops/systemd/vl-watchdog.service": ("watchdog.sh",),
        "ops/systemd/vl-watchdog.timer": ("Persistent=false",),
    }
    for relative, required in expectations.items():
        raw = members.get(relative)
        if raw is None or any(token.encode("utf-8") not in raw for token in required):
            raise ValueError(f"loopback systemd unit evidence mismatch: {relative}")


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive_regular(path: Path, raw: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, mode)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError(f"migration prerequisite write made no progress: {path}")
            view = view[written:]
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
    finally:
        os.close(descriptor)


def _directory_matches_identity(path: Path, expected: os.stat_result) -> bool:
    try:
        observed = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISDIR(observed.st_mode)
        and not stat.S_ISLNK(observed.st_mode)
        and os.path.samestat(expected, observed)
    )


def _require_directory_identity(path: Path, expected: os.stat_result) -> None:
    if not _directory_matches_identity(path, expected):
        raise OSError("migration prerequisite directory identity changed")


def _migration_prerequisite_evidence(
    members: Mapping[str, bytes], archive_sha256: str
) -> dict[str, Any]:
    missing_authorities = {
        CHECK_MIGRATION_GATE_MEMBER,
        ARCHIVED_VERIFIER_MEMBER,
        ARCHIVED_INSTALLER_MEMBER,
    } - members.keys()
    if missing_authorities:
        raise ValueError(
            "closed package is missing migration authorities: "
            f"{sorted(missing_authorities)}"
        )
    migration_names: list[str] = []
    for name in members:
        if not name.startswith(MIGRATION_MEMBER_PREFIX):
            continue
        if MIGRATION_MEMBER_RE.fullmatch(name) is None:
            raise ValueError(f"malformed migration prerequisite member: {name}")
        migration_names.append(name)
    migration_names.sort()
    if not migration_names:
        raise ValueError("closed package has no migration prerequisite members")
    total_size = sum(len(members[name]) for name in migration_names)
    if total_size > MAX_MIGRATION_PREREQUISITE_BYTES:
        raise ValueError("migration prerequisite set exceeds maximum expanded size")
    latest_match = MIGRATION_MEMBER_RE.fullmatch(migration_names[-1])
    assert latest_match is not None
    migration_records = [
        {
            "name": name.removeprefix(MIGRATION_MEMBER_PREFIX),
            "sha256": _sha256(members[name]),
            "size": len(members[name]),
        }
        for name in migration_names
    ]
    migration_set_sha256 = _sha256(
        json.dumps(
            migration_records,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    return {
        "archive_sha256": archive_sha256,
        "verifier_sha256": _sha256(members[ARCHIVED_VERIFIER_MEMBER]),
        "checker_sha256": _sha256(members[CHECK_MIGRATION_GATE_MEMBER]),
        "installer_sha256": _sha256(members[ARCHIVED_INSTALLER_MEMBER]),
        "migration_count": len(migration_names),
        "migration_latest": {
            "version": int(latest_match.group(1)),
            "migration": migration_names[-1].removeprefix(MIGRATION_MEMBER_PREFIX),
        },
        "migration_set_sha256": migration_set_sha256,
        "migrations": migration_records,
    }


def _materialize_migration_prerequisites(
    destination: Path,
    members: Mapping[str, bytes],
    evidence: Mapping[str, Any],
) -> None:
    destination = Path(os.path.abspath(os.fspath(destination)))
    if os.path.lexists(destination):
        if destination.is_symlink():
            raise OSError("migration prerequisite destination must not be a symlink")
        raise FileExistsError(destination)
    parent = destination.parent
    if parent.is_symlink() or not parent.is_dir():
        raise OSError("migration prerequisite parent must be a real directory")
    created_identity: os.stat_result | None = None
    try:
        destination.mkdir(mode=0o700)
        created_identity = destination.lstat()
        destination.chmod(0o700)
        _require_directory_identity(destination, created_identity)
        migrations_dir = destination / "migrations"
        migrations_dir.mkdir(mode=0o700)
        migrations_dir.chmod(0o700)
        migrations_identity = migrations_dir.lstat()
        _require_directory_identity(destination, created_identity)
        _write_exclusive_regular(
            destination / "check_migration_gate.py",
            members[CHECK_MIGRATION_GATE_MEMBER],
            0o600,
        )
        for item in evidence["migrations"]:
            _require_directory_identity(destination, created_identity)
            _require_directory_identity(migrations_dir, migrations_identity)
            name = item["name"]
            _write_exclusive_regular(
                migrations_dir / name,
                members[f"{MIGRATION_MEMBER_PREFIX}{name}"],
                0o600,
            )
        _require_directory_identity(destination, created_identity)
        _require_directory_identity(migrations_dir, migrations_identity)
        _fsync_directory(migrations_dir)
        _fsync_directory(destination)
        _fsync_directory(parent)
    except BaseException:
        # Leave the partial destination for the caller's private-stage cleanup;
        # path-based deletion after a race could destroy a replacement tree.
        raise


def verify_archive(
    archive: Path,
    digest_file: Path | None = None,
    *,
    migration_prerequisite_dir: Path | None = None,
) -> dict[str, Any]:
    """Verify the archive and return sanitized evidence; sidecar is checked first."""
    started = time.monotonic()
    archive = Path(archive)
    sidecar = Path(digest_file) if digest_file is not None else archive.with_name(archive.name + ".sha256")
    archive_sha256, snapshot = _read_sidecar(archive, sidecar)
    with snapshot:
        with tarfile.open(fileobj=snapshot, mode="r:gz") as bundle:
            members = _read_archive_members(bundle)
    missing = REQUIRED_MEMBERS - members.keys()
    if missing:
        raise ValueError(f"closed package is missing required members: {sorted(missing)}")
    manifest_raw = members.get("launch-release-manifest.json")
    if manifest_raw is None:
        raise ValueError("launch release manifest is missing")
    manifest = _safe_json(manifest_raw, "launch release manifest")
    _validate_manifest(manifest, members)
    _validate_readiness(
        _safe_json(members[READINESS_PATH], "launch readiness manifest"),
        members,
        manifest.get("source_revision"),
    )
    _validate_network_audit(members["compose-network-audit.json"])
    _validate_loopback_units(members)
    migration_evidence = _migration_prerequisite_evidence(members, archive_sha256)
    if migration_prerequisite_dir is not None:
        try:
            running_verifier = Path(__file__).read_bytes()
        except OSError as exc:
            raise ValueError("running verifier bytes cannot be read") from exc
        if running_verifier != members[ARCHIVED_VERIFIER_MEMBER]:
            raise ValueError("running verifier bytes do not match archived verifier")
        _materialize_migration_prerequisites(
            migration_prerequisite_dir,
            members,
            migration_evidence,
        )
    return {
        "archive": str(archive),
        "archive_sha256": archive_sha256,
        "package_kind": manifest["package_kind"],
        "launch_posture": manifest["launch_posture"],
        "required_members_verified": sorted(REQUIRED_MEMBERS),
        "member_digests_match_manifest": True,
        "persistent_paths": list(PERSISTENT_PATHS),
        "developer_override_selected": False,
        "unlock_keys_present": False,
        "canonical_digests": manifest["canonical_artifacts"],
        "readiness_digest": manifest["readiness_manifest"]["sha256"],
        "network_audit_digest": manifest["network_audit"]["sha256"],
        "migration_prerequisites": migration_evidence,
        "stage3_claim": False,
        "live_sla_proven": False,
        "observed_local_elapsed_seconds": round(time.monotonic() - started, 6),
    }


def _walk_installed(root: Path) -> dict[str, bytes]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("installed release root must be a real directory")
    result: dict[str, bytes] = {}
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for dirname in directories:
            path = current_path / dirname
            if path.is_symlink():
                raise ValueError(f"installed release contains symlink: {path}")
        for filename in files:
            path = current_path / filename
            if path.is_symlink():
                raise ValueError(f"installed release contains symlink: {path}")
            relative = path.relative_to(root).as_posix()
            if relative == "agent/data" or relative.startswith("agent/data/"):
                continue
            if relative == ".env":
                continue
            result[relative] = path.read_bytes()
    return result


def _directory_identity(path: Path, label: str) -> tuple[int, int]:
    observed = Path(path).lstat()
    if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
        raise ValueError(f"{label} must be a real directory")
    return observed.st_dev, observed.st_ino


def _installed_root_identity(root: Path) -> tuple[int, int]:
    return _directory_identity(root, "installed release root")


def _fingerprint_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _fingerprint_installed(root: Path) -> dict[str, tuple[int, str]]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("installed release root must be a real directory")
    result: dict[str, tuple[int, str]] = {}
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for dirname in directories:
            path = current_path / dirname
            if path.is_symlink():
                raise ValueError(f"installed release contains symlink: {path}")
        for filename in files:
            path = current_path / filename
            if path.is_symlink():
                raise ValueError(f"installed release contains symlink: {path}")
            relative = path.relative_to(root).as_posix()
            if relative == "agent/data" or relative.startswith("agent/data/"):
                continue
            if relative == ".env":
                continue
            result[relative] = _fingerprint_file(path)
    return result


def _validate_installed_release(
    root: Path,
) -> tuple[
    tuple[int, int],
    dict[str, tuple[int, str]],
    dict[str, bytes],
    dict[str, Any],
]:
    initial_root_identity = _installed_root_identity(root)
    members = _walk_installed(root)
    initial_fingerprints = {
        relative: (len(raw), _sha256(raw)) for relative, raw in members.items()
    }
    manifest_raw = members.get("launch-release-manifest.json")
    if manifest_raw is None:
        raise ValueError("installed launch release manifest is missing")
    manifest = _safe_json(manifest_raw, "installed launch release manifest")
    _validate_manifest(manifest, members)
    _validate_readiness(
        _safe_json(members[READINESS_PATH], "installed launch readiness manifest"),
        members,
        manifest.get("source_revision"),
    )
    _validate_network_audit(members["compose-network-audit.json"])
    _validate_loopback_units(members)
    return initial_root_identity, initial_fingerprints, members, manifest


def _persistent_directory_identities(
    root: Path, persistent_agent_data_root: Path
) -> tuple[tuple[int, int], tuple[int, int]]:
    return (
        _directory_identity(
            Path(persistent_agent_data_root),
            "persistent agent data authority",
        ),
        _directory_identity(
            root / "agent" / "data",
            "installed persistent agent data mountpoint",
        ),
    )


def _verify_requested_installed_authorities(
    root: Path,
    manifest: Mapping[str, Any],
    members: Mapping[str, bytes],
    *,
    verify_config_ingress_unit_digests: bool,
    systemd_unit_root: Path | None,
    verify_systemd_unit_destination: bool,
    environment_authority: Path | None,
    verify_environment_authority: bool,
) -> dict[str, Any]:
    additional: dict[str, Any] = {}
    if verify_config_ingress_unit_digests:
        verified = _verify_config_ingress_unit_digests(manifest, members)
        additional["config_ingress_unit_digests_verified"] = True
        additional["config_ingress_unit_paths"] = list(verified)
    if verify_systemd_unit_destination:
        if systemd_unit_root is None:
            raise ValueError("systemd unit root is required for destination verification")
        verified_units = _verify_systemd_unit_destination(manifest, systemd_unit_root)
        additional["systemd_unit_destination_verified"] = True
        additional["systemd_unit_paths"] = list(verified_units)
    if verify_environment_authority:
        if environment_authority is None:
            raise ValueError("environment authority is required for installed verification")
        additional.update(_verify_environment_authority(root, environment_authority))
    return additional


def _verify_requested_persistent_authority(
    root: Path,
    persistent_agent_data_root: Path | None,
    *,
    verify_persistent_agent_data_mount: bool,
    local_rehearsal: bool,
    persistent_mount_evidence: Path | None,
) -> tuple[dict[str, Any], tuple[tuple[int, int], tuple[int, int]] | None]:
    identities = None
    if persistent_agent_data_root is not None:
        identities = _persistent_directory_identities(root, persistent_agent_data_root)
    if verify_persistent_agent_data_mount:
        if persistent_agent_data_root is None:
            raise ValueError("persistent agent data root is required for mount verification")
        evidence = _verify_persistent_agent_data_mount(
            root,
            persistent_agent_data_root,
            local_rehearsal=local_rehearsal,
            findmnt_evidence=persistent_mount_evidence,
        )
        return evidence, identities
    if persistent_agent_data_root is None:
        return {}, identities
    external = Path(persistent_agent_data_root)
    persistent = root / "agent" / "data"
    if external.is_symlink() or not external.is_dir():
        raise ValueError("persistent agent data authority is not a real directory")
    if persistent.is_symlink() or not persistent.is_dir():
        raise ValueError("installed persistent agent data mountpoint is missing")
    return {}, identities


def _require_installed_root_unchanged(
    root: Path,
    initial_root_identity: tuple[int, int],
    initial_fingerprints: Mapping[str, tuple[int, str]],
) -> None:
    try:
        final_root_identity = _installed_root_identity(root)
        final_fingerprints = _fingerprint_installed(root)
    except (OSError, ValueError) as exc:
        raise ValueError("installed release changed during verification") from exc
    if (
        final_root_identity != initial_root_identity
        or final_fingerprints != initial_fingerprints
    ):
        raise ValueError("installed release changed during verification")


def _revalidate_installed_authorities(
    root: Path,
    manifest: Mapping[str, Any],
    *,
    systemd_unit_root: Path | None,
    verify_systemd_unit_destination: bool,
    environment_authority: Path | None,
    verify_environment_authority: bool,
    persistent_agent_data_root: Path | None,
    initial_persistent_identities: tuple[tuple[int, int], tuple[int, int]] | None,
    verify_persistent_agent_data_mount: bool,
    local_rehearsal: bool,
    persistent_mount_evidence: Path | None,
) -> None:
    try:
        if verify_systemd_unit_destination:
            _verify_systemd_unit_destination(manifest, Path(systemd_unit_root))
        if verify_environment_authority:
            _verify_environment_authority(root, Path(environment_authority))
        if initial_persistent_identities is not None:
            final_identities = _persistent_directory_identities(
                root, Path(persistent_agent_data_root)
            )
            if final_identities != initial_persistent_identities:
                raise ValueError("persistent agent data mountpoint changed")
            if verify_persistent_agent_data_mount:
                _verify_persistent_agent_data_mount(
                    root,
                    Path(persistent_agent_data_root),
                    local_rehearsal=local_rehearsal,
                    findmnt_evidence=persistent_mount_evidence,
                )
    except (OSError, ValueError) as exc:
        raise ValueError(
            "installed verification authorities changed during verification"
        ) from exc


def verify_installed_root(
    root: Path,
    *,
    persistent_agent_data_root: Path | None = None,
    verify_config_ingress_unit_digests: bool = False,
    verify_persistent_agent_data_mount: bool = False,
    local_rehearsal: bool = False,
    persistent_mount_evidence: Path | None = None,
    systemd_unit_root: Path | None = None,
    verify_systemd_unit_destination: bool = False,
    environment_authority: Path | None = None,
    verify_environment_authority: bool = False,
) -> dict[str, Any]:
    """Verify bytes installed from a closed package without touching the tree."""
    root = Path(root)
    initial_root_identity, initial_fingerprints, members, manifest = (
        _validate_installed_release(root)
    )
    additional = _verify_requested_installed_authorities(
        root,
        manifest,
        members,
        verify_config_ingress_unit_digests=verify_config_ingress_unit_digests,
        systemd_unit_root=systemd_unit_root,
        verify_systemd_unit_destination=verify_systemd_unit_destination,
        environment_authority=environment_authority,
        verify_environment_authority=verify_environment_authority,
    )
    persistent_evidence, initial_persistent_identities = (
        _verify_requested_persistent_authority(
            root,
            persistent_agent_data_root,
            verify_persistent_agent_data_mount=verify_persistent_agent_data_mount,
            local_rehearsal=local_rehearsal,
            persistent_mount_evidence=persistent_mount_evidence,
        )
    )
    additional.update(persistent_evidence)
    _require_installed_root_unchanged(
        root, initial_root_identity, initial_fingerprints
    )
    _revalidate_installed_authorities(
        root,
        manifest,
        systemd_unit_root=systemd_unit_root,
        verify_systemd_unit_destination=verify_systemd_unit_destination,
        environment_authority=environment_authority,
        verify_environment_authority=verify_environment_authority,
        persistent_agent_data_root=persistent_agent_data_root,
        initial_persistent_identities=initial_persistent_identities,
        verify_persistent_agent_data_mount=verify_persistent_agent_data_mount,
        local_rehearsal=local_rehearsal,
        persistent_mount_evidence=persistent_mount_evidence,
    )
    return {
        "installed_root": str(root),
        "closed_verified": True,
        "member_digests_match_manifest": True,
        "persistent_paths": list(PERSISTENT_PATHS),
        "stage3_claim": False,
        "live_sla_proven": False,
        "observed_local_elapsed_seconds": 0.0,
        **additional,
    }


def _is_evidence_reparse_point(observed: os.stat_result) -> bool:
    if stat.S_ISLNK(observed.st_mode):
        return True
    if os.name != "nt":
        return False
    return bool(
        getattr(observed, "st_file_attributes", 0)
        & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
    )


def _trusted_evidence_directory(path: Path, *, create: bool) -> Path:
    directory = Path(os.path.abspath(os.fspath(path)))
    current = Path(directory.anchor)
    for part in directory.parts[1:]:
        candidate = current / part
        try:
            observed = candidate.lstat()
        except FileNotFoundError:
            if not create:
                raise
            try:
                candidate.mkdir()
            except FileExistsError:
                pass
            observed = candidate.lstat()
        if _is_evidence_reparse_point(observed):
            raise OSError(
                f"refusing symlink or reparse-point evidence directory: {candidate}"
            )
        if not stat.S_ISDIR(observed.st_mode):
            raise OSError(f"evidence ancestor is not a directory: {candidate}")
        current = candidate
    return directory


def _reject_symlink_evidence_path(path: Path) -> None:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return
    if _is_evidence_reparse_point(observed):
        raise OSError("refusing to replace symlink evidence path")


def _write_evidence_bytes(descriptor: int, raw: bytes) -> None:
    remaining = memoryview(raw)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("evidence temporary write made no progress")
        remaining = remaining[written:]
    os.fsync(descriptor)


def _finish_evidence_cleanup(
    primary_error: BaseException | None, cleanup_errors: list[BaseException]
) -> None:
    if not cleanup_errors:
        return
    if primary_error is not None:
        for cleanup_error in cleanup_errors:
            primary_error.add_note(f"evidence cleanup failed: {cleanup_error}")
        return
    first_error, *remaining_errors = cleanup_errors
    for cleanup_error in remaining_errors:
        first_error.add_note(f"additional evidence cleanup failure: {cleanup_error}")
    raise first_error


def _windows_api_path(path: Path) -> str:
    raw = os.path.abspath(os.fspath(path))
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw


def _windows_os_error(error: int, action: str, path: Path) -> OSError:
    message = f"{action}: {ctypes.FormatError(error).strip()}"
    if error in (2, 3):
        return FileNotFoundError(error, message, os.fspath(path))
    if error in (80, 183):
        return FileExistsError(error, message, os.fspath(path))
    return OSError(error, message, os.fspath(path))


def _windows_nt_error(status: int, action: str, path: Path) -> OSError:
    error = int(_WINDOWS_NTDLL.RtlNtStatusToDosError(status))
    return _windows_os_error(error, action, path)


def _close_windows_handle(handle: int) -> BaseException | None:
    if _WINDOWS_KERNEL32.CloseHandle(handle):
        return None
    error = ctypes.get_last_error()
    return _windows_os_error(error, "could not close evidence authority handle", Path("."))


def _open_windows_evidence_directory_handle(
    path: Path, *, writable: bool
) -> int:
    desired_access = _WINDOWS_GENERIC_READ
    if writable:
        desired_access |= _WINDOWS_GENERIC_WRITE
    handle = _WINDOWS_KERNEL32.CreateFileW(
        _windows_api_path(path),
        desired_access,
        _WINDOWS_FILE_SHARE_READ | _WINDOWS_FILE_SHARE_WRITE,
        None,
        _WINDOWS_OPEN_EXISTING,
        _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS
        | _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _WINDOWS_INVALID_HANDLE:
        error = ctypes.get_last_error()
        raise _windows_os_error(error, "could not bind evidence directory", path)
    try:
        observed = _WindowsFileAttributeTagInfo()
        if not _WINDOWS_KERNEL32.GetFileInformationByHandleEx(
            handle,
            _WINDOWS_FILE_ATTRIBUTE_TAG_INFO,
            ctypes.byref(observed),
            ctypes.sizeof(observed),
        ):
            error = ctypes.get_last_error()
            raise _windows_os_error(
                error, "could not inspect evidence directory handle", path
            )
        if observed.file_attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT:
            raise OSError(
                f"refusing symlink or reparse-point evidence directory: {path}"
            )
        if not observed.file_attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY:
            raise OSError(f"evidence ancestor is not a directory: {path}")
        return int(handle)
    except BaseException as exc:
        cleanup_error = _close_windows_handle(int(handle))
        if cleanup_error is not None:
            exc.add_note(f"evidence cleanup failed: {cleanup_error}")
        raise


def _windows_evidence_directory_access(writable: bool) -> int:
    desired_access = _WINDOWS_GENERIC_READ | _WINDOWS_SYNCHRONIZE
    if writable:
        desired_access |= _WINDOWS_GENERIC_WRITE
    return desired_access


def _validate_windows_evidence_directory_handle(
    handle_value: int, display_path: Path
) -> None:
    observed = _WindowsFileAttributeTagInfo()
    if not _WINDOWS_KERNEL32.GetFileInformationByHandleEx(
        handle_value,
        _WINDOWS_FILE_ATTRIBUTE_TAG_INFO,
        ctypes.byref(observed),
        ctypes.sizeof(observed),
    ):
        error = ctypes.get_last_error()
        raise _windows_os_error(
            error,
            "could not inspect evidence directory handle",
            display_path,
        )
    if observed.file_attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT:
        raise OSError(
            "refusing symlink or reparse-point evidence directory: "
            f"{display_path}"
        )
    if not observed.file_attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY:
        raise OSError(f"evidence ancestor is not a directory: {display_path}")


def _create_windows_evidence_directory_component(
    parent_handle: int,
    component: str,
    display_path: Path,
    *,
    writable: bool,
) -> int:
    if not component or component in (".", "..") or any(
        separator in component for separator in ("/", "\\")
    ):
        raise ValueError("Windows evidence directory component must be a name")
    name_buffer = ctypes.create_unicode_buffer(component)
    name_length = len(component.encode("utf-16-le"))
    object_name = _WindowsUnicodeString(
        name_length,
        ctypes.sizeof(name_buffer),
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attributes = _WindowsObjectAttributes(
        ctypes.sizeof(_WindowsObjectAttributes),
        parent_handle,
        ctypes.pointer(object_name),
        _WINDOWS_OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    desired_access = _windows_evidence_directory_access(writable)

    for disposition in (_WINDOWS_FILE_CREATE, _WINDOWS_FILE_OPEN):
        status_block = _WindowsIoStatusBlock()
        native_handle = wintypes.HANDLE()
        status = _WINDOWS_NTDLL.NtCreateFile(
            ctypes.byref(native_handle),
            desired_access,
            ctypes.byref(attributes),
            ctypes.byref(status_block),
            None,
            _WINDOWS_FILE_ATTRIBUTE_NORMAL,
            _WINDOWS_FILE_SHARE_READ | _WINDOWS_FILE_SHARE_WRITE,
            disposition,
            _WINDOWS_FILE_DIRECTORY_FILE
            | _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT
            | _WINDOWS_FILE_OPEN_REPARSE_POINT,
            None,
            0,
        )
        if status < 0:
            error = _windows_nt_error(
                status, "could not create evidence directory", display_path
            )
            if disposition == _WINDOWS_FILE_CREATE and isinstance(
                error, FileExistsError
            ):
                continue
            raise error

        handle_value = int(native_handle.value)
        try:
            _validate_windows_evidence_directory_handle(handle_value, display_path)
            return handle_value
        except BaseException as exc:
            cleanup_error = _close_windows_handle(handle_value)
            if cleanup_error is not None:
                exc.add_note(f"evidence cleanup failed: {cleanup_error}")
            raise

    raise AssertionError("unreachable Windows directory create disposition")


def _open_trusted_windows_evidence_directory(
    path: Path, *, create: bool
) -> tuple[Path, list[int]]:
    directory = Path(os.path.abspath(os.fspath(path)))
    components = directory.parts[1:]
    current = Path(directory.anchor)
    handles: list[int] = []
    try:
        handles.append(
            _open_windows_evidence_directory_handle(
                current, writable=not components
            )
        )
        for index, component in enumerate(components):
            candidate = current / component
            writable = index == len(components) - 1
            try:
                handle = _open_windows_evidence_directory_handle(
                    candidate, writable=writable
                )
            except FileNotFoundError:
                if not create:
                    raise
                handle = _create_windows_evidence_directory_component(
                    handles[-1], component, candidate, writable=writable
                )
            handles.append(handle)
            current = candidate
        return directory, handles
    except BaseException as exc:
        for handle in reversed(handles):
            cleanup_error = _close_windows_handle(handle)
            if cleanup_error is not None:
                exc.add_note(f"evidence cleanup failed: {cleanup_error}")
        raise


def _create_windows_evidence_temporary(
    path: Path, parent_handle: int
) -> tuple[int, str]:
    for _ in range(100):
        name = f".{path.name}.{secrets.token_hex(8)}.tmp"
        name_buffer = ctypes.create_unicode_buffer(name)
        name_length = len(name.encode("utf-16-le"))
        object_name = _WindowsUnicodeString(
            name_length,
            ctypes.sizeof(name_buffer),
            ctypes.cast(name_buffer, wintypes.LPWSTR),
        )
        attributes = _WindowsObjectAttributes(
            ctypes.sizeof(_WindowsObjectAttributes),
            parent_handle,
            ctypes.pointer(object_name),
            _WINDOWS_OBJ_CASE_INSENSITIVE,
            None,
            None,
        )
        status_block = _WindowsIoStatusBlock()
        native_handle = wintypes.HANDLE()
        status = _WINDOWS_NTDLL.NtCreateFile(
            ctypes.byref(native_handle),
            _WINDOWS_GENERIC_WRITE
            | _WINDOWS_DELETE
            | _WINDOWS_SYNCHRONIZE
            | _WINDOWS_FILE_READ_ATTRIBUTES,
            ctypes.byref(attributes),
            ctypes.byref(status_block),
            None,
            _WINDOWS_FILE_ATTRIBUTE_NORMAL,
            0,
            _WINDOWS_FILE_CREATE,
            _WINDOWS_FILE_SYNCHRONOUS_IO_NONALERT
            | _WINDOWS_FILE_NON_DIRECTORY_FILE
            | _WINDOWS_FILE_OPEN_REPARSE_POINT,
            None,
            0,
        )
        if status < 0:
            error = _windows_nt_error(
                status, "could not create evidence temporary file", path.parent / name
            )
            if isinstance(error, FileExistsError):
                continue
            raise error
        handle_value = int(native_handle.value)
        try:
            descriptor = msvcrt.open_osfhandle(
                handle_value, os.O_WRONLY | getattr(os, "O_BINARY", 0)
            )
        except BaseException as exc:
            cleanup_error = _close_windows_handle(handle_value)
            if cleanup_error is not None:
                exc.add_note(f"evidence cleanup failed: {cleanup_error}")
            raise
        return descriptor, name
    raise FileExistsError("could not allocate evidence temporary file")


def _replace_windows_evidence_at(
    descriptor: int, parent_handle: int, target_name: str, target_path: Path
) -> None:
    encoded_name = target_name.encode("utf-16-le")
    name_offset = _WindowsFileRenameInformation.file_name.offset
    buffer_size = name_offset + len(encoded_name)
    buffer = ctypes.create_string_buffer(buffer_size)
    rename = ctypes.cast(
        buffer, ctypes.POINTER(_WindowsFileRenameInformation)
    ).contents
    rename.replace_if_exists = 1
    rename.root_directory = parent_handle
    rename.file_name_length = len(encoded_name)
    ctypes.memmove(
        ctypes.addressof(buffer) + name_offset, encoded_name, len(encoded_name)
    )
    status_block = _WindowsIoStatusBlock()
    status = _WINDOWS_NTDLL.NtSetInformationFile(
        msvcrt.get_osfhandle(descriptor),
        ctypes.byref(status_block),
        buffer,
        buffer_size,
        _WINDOWS_FILE_RENAME_INFORMATION,
    )
    if status < 0:
        raise _windows_nt_error(
            status, "could not replace evidence file", target_path
        )


def _flush_windows_evidence_directory(handle: int, path: Path) -> None:
    if _WINDOWS_KERNEL32.FlushFileBuffers(handle):
        return
    error = ctypes.get_last_error()
    raise _windows_os_error(error, "could not flush evidence directory", path)


def _require_posix_evidence_capabilities() -> None:
    missing: list[str] = []
    for constant in ("O_DIRECTORY", "O_NOFOLLOW"):
        if not hasattr(os, constant):
            missing.append(constant)
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    for function in (os.open, os.mkdir, os.replace, os.stat, os.unlink):
        if function not in supports_dir_fd:
            missing.append(f"{function.__name__}(dir_fd)")
    supports_follow_symlinks = getattr(os, "supports_follow_symlinks", set())
    if os.stat not in supports_follow_symlinks:
        missing.append("stat(follow_symlinks=False)")
    if missing:
        raise OSError(
            "required POSIX evidence capabilities unavailable: "
            + ", ".join(missing)
        )


def _evidence_directory_open_flags() -> int:
    _require_posix_evidence_capabilities()
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_evidence_directory_component(
    parent_descriptor: int, component: str, display_path: Path
) -> int:
    try:
        descriptor = os.open(
            component,
            _evidence_directory_open_flags(),
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        try:
            observed = os.stat(
                component, dir_fd=parent_descriptor, follow_symlinks=False
            )
        except FileNotFoundError:
            raise exc
        if stat.S_ISLNK(observed.st_mode):
            raise OSError(
                f"refusing symlink evidence directory: {display_path}"
            ) from exc
        if not stat.S_ISDIR(observed.st_mode):
            raise OSError(
                f"evidence ancestor is not a directory: {display_path}"
            ) from exc
        raise
    try:
        observed = os.fstat(descriptor)
        if stat.S_ISDIR(observed.st_mode):
            return descriptor
        raise OSError(f"evidence ancestor is not a directory: {display_path}")
    except BaseException as primary_error:
        try:
            os.close(descriptor)
        except BaseException as cleanup_error:
            primary_error.add_note(f"evidence cleanup failed: {cleanup_error}")
        raise


def _open_trusted_posix_evidence_directory(path: Path, *, create: bool) -> int:
    directory = Path(os.path.abspath(os.fspath(path)))
    current_path = Path(directory.anchor)
    current_descriptor = os.open(
        current_path, _evidence_directory_open_flags()
    )
    try:
        for component in directory.parts[1:]:
            next_path = current_path / component
            try:
                next_descriptor = _open_evidence_directory_component(
                    current_descriptor, component, next_path
                )
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, 0o755, dir_fd=current_descriptor)
                except FileExistsError:
                    pass
                next_descriptor = _open_evidence_directory_component(
                    current_descriptor, component, next_path
                )
            try:
                os.close(current_descriptor)
            except BaseException as exc:
                cleanup_errors: list[BaseException] = []
                try:
                    os.close(next_descriptor)
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
                current_descriptor = -1
                _finish_evidence_cleanup(exc, cleanup_errors)
                raise
            current_descriptor = next_descriptor
            current_path = next_path
        return current_descriptor
    except BaseException as exc:
        if current_descriptor != -1:
            try:
                os.close(current_descriptor)
            except BaseException as cleanup_error:
                exc.add_note(f"evidence cleanup failed: {cleanup_error}")
        raise


def _revalidate_evidence_parent(path: Path, descriptor: int) -> None:
    current_descriptor = _open_trusted_posix_evidence_directory(
        path, create=False
    )
    primary_error: BaseException | None = None
    try:
        observed = os.fstat(current_descriptor)
        opened = os.fstat(descriptor)
        if (observed.st_dev, observed.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError("evidence parent authority changed")
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors: list[BaseException] = []
        try:
            os.close(current_descriptor)
        except BaseException as exc:
            cleanup_errors.append(exc)
        _finish_evidence_cleanup(primary_error, cleanup_errors)


def _reject_symlink_evidence_at(parent_descriptor: int, name: str) -> None:
    try:
        observed = os.stat(
            name, dir_fd=parent_descriptor, follow_symlinks=False
        )
    except FileNotFoundError:
        return
    if stat.S_ISLNK(observed.st_mode):
        raise OSError("refusing to replace symlink evidence path")


def _create_posix_evidence_temporary(
    path: Path, parent_descriptor: int
) -> tuple[int, str]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    for _ in range(100):
        name = f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        return descriptor, name
    raise FileExistsError("could not allocate evidence temporary file")


def _write_windows_evidence(path: Path, raw: bytes) -> None:
    parent, authority_handles = _open_trusted_windows_evidence_directory(
        path.parent, create=True
    )
    path = parent / path.name
    parent_handle = authority_handles[-1]
    descriptor = -1
    temporary_name = ""
    temporary_present = False
    primary_error: BaseException | None = None
    try:
        _reject_symlink_evidence_path(path)
        descriptor, temporary_name = _create_windows_evidence_temporary(
            path, parent_handle
        )
        temporary_present = True
        _write_evidence_bytes(descriptor, raw)
        _trusted_evidence_directory(parent, create=False)
        _reject_symlink_evidence_path(path)
        _replace_windows_evidence_at(
            descriptor, parent_handle, path.name, path
        )
        temporary_present = False
        _flush_windows_evidence_directory(parent_handle, parent)
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors: list[BaseException] = []
        if descriptor != -1:
            try:
                os.close(descriptor)
            except BaseException as exc:
                cleanup_errors.append(exc)
        if temporary_present:
            try:
                (parent / temporary_name).unlink(missing_ok=True)
            except BaseException as exc:
                cleanup_errors.append(exc)
        for handle in reversed(authority_handles):
            cleanup_error = _close_windows_handle(handle)
            if cleanup_error is not None:
                cleanup_errors.append(cleanup_error)
        _finish_evidence_cleanup(primary_error, cleanup_errors)


def _write_posix_evidence(path: Path, raw: bytes) -> None:
    parent = Path(os.path.abspath(os.fspath(path.parent)))
    parent_descriptor = _open_trusted_posix_evidence_directory(
        parent, create=True
    )
    path = parent / path.name
    descriptor = -1
    temporary_name = ""
    temporary_present = False
    primary_error: BaseException | None = None
    try:
        _reject_symlink_evidence_at(parent_descriptor, path.name)
        descriptor, temporary_name = _create_posix_evidence_temporary(
            path, parent_descriptor
        )
        temporary_present = True
        _write_evidence_bytes(descriptor, raw)
        _revalidate_evidence_parent(parent, parent_descriptor)
        _reject_symlink_evidence_at(parent_descriptor, path.name)
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        temporary_present = False
        os.fsync(parent_descriptor)
        _revalidate_evidence_parent(parent, parent_descriptor)
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors: list[BaseException] = []
        if descriptor != -1:
            try:
                os.close(descriptor)
            except BaseException as exc:
                cleanup_errors.append(exc)
        if temporary_present:
            try:
                os.unlink(temporary_name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
            except BaseException as exc:
                cleanup_errors.append(exc)
        try:
            os.close(parent_descriptor)
        except BaseException as exc:
            cleanup_errors.append(exc)
        _finish_evidence_cleanup(primary_error, cleanup_errors)


def _write_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    path = Path(os.path.abspath(os.fspath(path)))
    raw = (
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    if os.name == "nt":
        _write_windows_evidence(path, raw)
    else:
        _write_posix_evidence(path, raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--archive-digest-file", type=Path)
    parser.add_argument("--migration-prerequisite-dir", type=Path)
    parser.add_argument("--installed-root", type=Path)
    parser.add_argument("--persistent-agent-data-root", type=Path)
    parser.add_argument("--verify-config-ingress-unit-digests", action="store_true")
    parser.add_argument("--verify-persistent-agent-data-mount", action="store_true")
    parser.add_argument("--persistent-mount-evidence", type=Path)
    parser.add_argument("--local-rehearsal", action="store_true")
    parser.add_argument("--systemd-unit-root", type=Path)
    parser.add_argument("--verify-systemd-unit-destination", action="store_true")
    parser.add_argument("--environment-authority", type=Path)
    parser.add_argument("--verify-environment-authority", action="store_true")
    parser.add_argument("--require-closed", action="store_true")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--operator")
    parser.add_argument("--candidate-id")
    parser.add_argument("--rollback-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if (args.archive is None) == (args.installed_root is None):
        raise SystemExit("supply exactly one of --archive or --installed-root")
    try:
        if args.archive is not None:
            evidence = verify_archive(
                args.archive,
                args.archive_digest_file,
                migration_prerequisite_dir=args.migration_prerequisite_dir,
            )
        else:
            evidence = verify_installed_root(
                args.installed_root,
                persistent_agent_data_root=args.persistent_agent_data_root,
                verify_config_ingress_unit_digests=args.verify_config_ingress_unit_digests,
                verify_persistent_agent_data_mount=args.verify_persistent_agent_data_mount,
                local_rehearsal=args.local_rehearsal,
                persistent_mount_evidence=args.persistent_mount_evidence,
                systemd_unit_root=args.systemd_unit_root,
                verify_systemd_unit_destination=args.verify_systemd_unit_destination,
                environment_authority=args.environment_authority,
                verify_environment_authority=args.verify_environment_authority,
            )
        if args.operator:
            evidence["operator"] = args.operator
        if args.candidate_id:
            evidence["candidate_id"] = args.candidate_id
        if args.rollback_id:
            evidence["rollback_id"] = args.rollback_id
        if args.evidence_dir:
            _write_evidence(args.evidence_dir / "closed-release.json", evidence)
        print(json.dumps(evidence, ensure_ascii=True, sort_keys=True))
    except MemoryError:
        print(
            "closed release verification refused: memory resource limit exceeded",
            file=os.sys.stderr,
        )
        return 2
    except (FileNotFoundError, OSError, ValueError, tarfile.TarError) as exc:
        print(f"closed release verification refused: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
