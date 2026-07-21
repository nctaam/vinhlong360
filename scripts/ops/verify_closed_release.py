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
import stat
import tarfile
import tempfile
import time
from typing import Any, Mapping


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


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _read_sidecar(archive: Path, sidecar: Path) -> str:
    if archive.is_symlink() or sidecar.is_symlink():
        raise ValueError("archive and sidecar must not be symlinks")
    if not archive.is_file() or not sidecar.is_file():
        raise FileNotFoundError("closed archive and adjacent SHA-256 sidecar are required")
    raw = sidecar.read_text(encoding="ascii")
    match = SIDECAR_RE.fullmatch(raw)
    if match is None or Path(match.group(2)).name != archive.name:
        raise ValueError("archive SHA-256 sidecar format mismatch")
    expected = match.group(1)
    observed = _sha256_file(archive)
    if observed != expected:
        raise ValueError("archive SHA-256 sidecar mismatch")
    return expected


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
    return stream.read()


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
    observed_source_resolved = Path(observed_source).resolve()
    bracketed_source = FINDMNT_SOURCE_ROOT_RE.fullmatch(observed_source)
    bind_proven_by_source = False
    if observed_source_resolved != expected_source_resolved:
        if bracketed_source is None:
            raise ValueError("findmnt source does not match persistent authority")
        normalized_root = Path(bracketed_source.group("root")).resolve()
        if normalized_root != expected_source_resolved:
            raise ValueError("findmnt source does not match persistent authority")
        if not _findmnt_device_matches_source(
            bracketed_source.group("device"), expected_source_resolved
        ):
            raise ValueError("findmnt source device does not match persistent authority")
        bind_proven_by_source = True
    if Path(observed_target).resolve() != Path(expected_target).resolve():
        raise ValueError("findmnt target does not match installed mountpoint")
    raw_option_values = (
        set(options)
        if isinstance(options, list)
        else set(str(options).split(","))
        if isinstance(options, str)
        else set()
    )
    raw_option_values.discard("")
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
    if audit.get("schema_version") != 1 or audit.get("revision") != "compose-network-audit-v1":
        raise ValueError("compose network audit revision mismatch")
    checks = audit.get("checks")
    if not isinstance(checks, dict) or not checks or any(value != "passed" for value in checks.values()):
        raise ValueError("compose network audit is not fully passed")
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


def verify_archive(archive: Path, digest_file: Path | None = None) -> dict[str, Any]:
    """Verify the archive and return sanitized evidence; sidecar is checked first."""
    started = time.monotonic()
    archive = Path(archive)
    sidecar = Path(digest_file) if digest_file is not None else archive.with_name(archive.name + ".sha256")
    archive_sha256 = _read_sidecar(archive, sidecar)
    members: dict[str, bytes] = {}
    with tarfile.open(archive, "r:gz") as bundle:
        names: set[str] = set()
        for member in bundle.getmembers():
            _validate_member_name(member.name)
            if member.name in names:
                raise ValueError(f"duplicate archive member: {member.name}")
            names.add(member.name)
            if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise ValueError(f"archive member type is unsafe: {member.name}")
            if member.isfile():
                members[member.name] = _member_bytes(member, bundle)
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
    members = _walk_installed(root)
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
    if verify_persistent_agent_data_mount:
        if persistent_agent_data_root is None:
            raise ValueError("persistent agent data root is required for mount verification")
        additional.update(
            _verify_persistent_agent_data_mount(
                root,
                persistent_agent_data_root,
                local_rehearsal=local_rehearsal,
                findmnt_evidence=persistent_mount_evidence,
            )
        )
    elif persistent_agent_data_root is not None:
        persistent = root / "agent" / "data"
        external = Path(persistent_agent_data_root)
        if external.is_symlink() or not external.is_dir():
            raise ValueError("persistent agent data authority is not a real directory")
        if persistent.is_symlink() or not persistent.is_dir():
            raise ValueError("installed persistent agent data mountpoint is missing")
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


def _write_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError("refusing to replace symlink evidence path")
    raw = (json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--archive-digest-file", type=Path)
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
            evidence = verify_archive(args.archive, args.archive_digest_file)
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
    except (FileNotFoundError, OSError, ValueError, tarfile.TarError) as exc:
        print(f"closed release verification refused: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
