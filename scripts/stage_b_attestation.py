"""Validate and write a credential-free Stage B attestation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__:
    from . import migrate_entity_status as migration
    from .migrate_entity_status import validate_restore_artifact
    from .postgres_target import (
        canonical_json_bytes,
        canonical_target_identity,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
    )
else:  # pragma: no cover - direct script execution
    import migrate_entity_status as migration
    from migrate_entity_status import validate_restore_artifact
    from postgres_target import (
        canonical_json_bytes,
        canonical_target_identity,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
    )


ROOT = Path(__file__).resolve().parent.parent
ACL_SCRIPT = Path(__file__).with_name("secure_stage_b_artifacts.ps1")
SCHEMA = "vinhlong360-stage-b-attestation-v1"
ATTESTATION_REVISION = "postgres-identity-v2"
MAX_INPUT_BYTES = 1024 * 1024
MAX_EVIDENCE_AGE_SECONDS = 300
EVIDENCE_KEYS = {"source", "noindex", "temporary_role", "tunnel", "operations"}
ACL_KEYS = {
    "checked_at",
    "allowed_principals",
    "object_count",
    "protected_object_count",
    "unexpected_principals",
    "inherited_rule_count",
    "reparse_point_count",
    "alternate_data_stream_count",
}
SECRET_KEYS = {
    "password",
    "password_hash",
    "database_url",
    "connection_url",
    "session_token",
    "otp",
    "private_key",
}
SECRET_VALUE_MARKERS = ("postgresql://", "BEGIN OPENSSH PRIVATE KEY")
SECRET_KEY_TOKENS = {key.replace("_", "") for key in SECRET_KEYS}
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
HEAD_RE = re.compile(r"[0-9a-f]{40}\Z")


class AttestationRefusal(RuntimeError):
    """Refuse malformed, stale, mutable, or unsafe attestation input."""


@dataclass(frozen=True)
class ArtifactSnapshot:
    path: Path
    identity: tuple[int, int]
    size: int
    sha256: str
    canonical_json: bool


def parse_args() -> argparse.Namespace:
    return _parser().parse_args()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AttestationRefusal("timestamp requires a timezone")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc(value: object, label: str) -> datetime:
    if type(value) is not str:
        raise AttestationRefusal(f"{label} timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AttestationRefusal(f"{label} timestamp is invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AttestationRefusal(f"{label} timestamp requires a timezone")
    return parsed.astimezone(UTC)


def _require_exact(value: object, keys: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise AttestationRefusal(f"{label} fields are malformed")
    return value


def _require_sha(value: object, label: str) -> str:
    if type(value) is not str or SHA256_RE.fullmatch(value) is None:
        raise AttestationRefusal(f"{label} is invalid")
    return value


def _normalize_key(value: object) -> str:
    if type(value) is not str:
        return ""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.casefold())).strip("_")


def _scan_secrets(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = _normalize_key(key)
            if (
                normalized in SECRET_KEYS
                or normalized.replace("_", "") in SECRET_KEY_TOKENS
            ):
                raise AttestationRefusal("secret field rejected")
            _scan_secrets(nested)
    elif isinstance(value, list):
        for nested in value:
            _scan_secrets(nested)
    elif isinstance(value, str) and any(
        marker.casefold() in value.casefold() for marker in SECRET_VALUE_MARKERS
    ):
        raise AttestationRefusal("secret value rejected")


def _read_stdin(stream: Any) -> dict[str, object]:
    source = getattr(stream, "buffer", stream)
    raw = source.read(MAX_INPUT_BYTES + 1)
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) > MAX_INPUT_BYTES:
        raise AttestationRefusal("evidence input exceeds 1 MiB")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AttestationRefusal("evidence input is invalid JSON") from None
    _scan_secrets(value)
    if type(value) is not dict:
        raise AttestationRefusal("evidence root must be an object")
    return value


def _is_reparse(metadata: os.stat_result) -> bool:
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return (
        bool(stat.S_ISLNK(metadata.st_mode))
        or bool(getattr(metadata, "st_reparse_tag", 0))
        or bool(getattr(metadata, "st_file_attributes", 0) & flag)
    )


def _lstat(path: Path, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError:
        raise AttestationRefusal(f"{label} is unavailable") from None
    if _is_reparse(metadata):
        raise AttestationRefusal(f"{label} is a reparse point")
    return metadata


def _real_dir(path: Path, label: str) -> os.stat_result:
    metadata = _lstat(path, label)
    if not stat.S_ISDIR(metadata.st_mode):
        raise AttestationRefusal(f"{label} is not a directory")
    return metadata


def _real_file(path: Path, label: str) -> os.stat_result:
    metadata = _lstat(path, label)
    if not stat.S_ISREG(metadata.st_mode):
        raise AttestationRefusal(f"{label} is not a regular file")
    return metadata


def _assert_no_reparse_ancestors(path: Path) -> None:
    current = path.absolute()
    while True:
        if current.exists() or os.path.lexists(current):
            _lstat(current, "path ancestor")
        if current.parent == current:
            return
        current = current.parent


def _validate_real_tree(root: Path) -> None:
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(directory.iterdir())
        except OSError:
            raise AttestationRefusal("artifact tree is unreadable") from None
        for entry in entries:
            metadata = _lstat(entry, "artifact tree entry")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(entry)
            elif not stat.S_ISREG(metadata.st_mode):
                raise AttestationRefusal("artifact tree entry is not regular")


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _stable_read(path: Path, label: str) -> tuple[bytes, os.stat_result]:
    before = _real_file(path, label)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            os.close(descriptor)
            raise AttestationRefusal(f"{label} changed during validation")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            raw = stream.read()
            after_read = os.fstat(stream.fileno())
    except OSError:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise AttestationRefusal(f"{label} is unreadable") from None
    after = _real_file(path, label)
    expected = (before.st_dev, before.st_ino, before.st_size)
    if expected != (
        after_read.st_dev,
        after_read.st_ino,
        after_read.st_size,
    ) or expected != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise AttestationRefusal(f"{label} changed during validation")
    if len(raw) != before.st_size:
        raise AttestationRefusal(f"{label} changed during validation")
    return raw, after


def load_canonical_object(
    path: Path, label: str = "JSON artifact"
) -> tuple[dict[str, object], str]:
    raw, _metadata = _stable_read(path, label)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AttestationRefusal(f"{label} is invalid JSON") from None
    if type(value) is not dict:
        raise AttestationRefusal(f"{label} root must be an object")
    try:
        canonical = canonical_json_bytes(value)
    except (TypeError, ValueError):
        raise AttestationRefusal(f"{label} cannot be serialized canonically") from None
    if raw != canonical:
        raise AttestationRefusal(f"{label} bytes are not canonical")
    return value, sha256_bytes(raw)


def _validate_canonical_object_bytes(raw: bytes, label: str) -> None:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AttestationRefusal(f"{label} is invalid JSON") from None
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        raise AttestationRefusal(f"{label} bytes are not canonical")


def _identity(value: object, label: str) -> dict[str, object]:
    try:
        return canonical_target_identity(value, exact_keys=True)
    except RuntimeError:
        raise AttestationRefusal(f"{label} database identity is invalid") from None


def _relative(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if not relative or relative.startswith("../") or "/../" in relative:
        raise AttestationRefusal("artifact path escapes root")
    return relative


def _find_backup_run(root: Path) -> Path:
    backup = root / "backup"
    _real_dir(backup, "backup directory")
    try:
        entries = list(backup.iterdir())
    except OSError:
        raise AttestationRefusal("backup directory is unreadable") from None
    runs: list[Path] = []
    for entry in entries:
        metadata = _lstat(entry, "backup entry")
        if stat.S_ISDIR(metadata.st_mode):
            runs.append(entry)
        else:
            raise AttestationRefusal("backup contains a non-directory entry")
    if len(runs) != 1:
        raise AttestationRefusal("backup must contain exactly one run directory")
    return runs[0]


def _validate_restore_listing(
    dump_path: Path,
    listing_path: Path,
    dump_sha: str,
    listing_sha: str,
    dump_identity: tuple[int, int, int],
    listing_identity: tuple[int, int, int],
) -> None:
    try:
        restored_listing_sha = validate_restore_artifact(dump_path)
    except Exception:
        raise AttestationRefusal("pg_restore --list revalidation failed") from None
    if restored_listing_sha != listing_sha:
        raise AttestationRefusal("pg_restore listing hash mismatch")
    current_dump = _real_file(dump_path, "postgres dump")
    current_listing = _real_file(listing_path, "restore listing")
    if (
        dump_identity
        != (current_dump.st_dev, current_dump.st_ino, current_dump.st_size)
        or listing_identity
        != (current_listing.st_dev, current_listing.st_ino, current_listing.st_size)
        or sha256_file(dump_path) != dump_sha
        or sha256_file(listing_path) != listing_sha
    ):
        raise AttestationRefusal("artifact changed during validation")


def validate_artifacts(root: Path, now: datetime | None = None) -> dict[str, object]:
    now = now or _utc_now()
    root = root.absolute()
    _assert_no_reparse_ancestors(root)
    _real_dir(root, "artifact root")
    _validate_real_tree(root)
    plan_path = root / "published-v1-plan.json"
    listing_path = root / "pg-restore-list.txt"
    _real_file(plan_path, "publication plan")
    _real_file(listing_path, "restore listing")
    run = _find_backup_run(root)
    manifest_path = run / "manifest.json"
    dump_path = run / "postgres.dump"
    _real_file(manifest_path, "backup manifest")
    _real_file(dump_path, "postgres dump")

    plan, plan_sha = load_canonical_object(plan_path, "publication plan")
    manifest, manifest_sha = load_canonical_object(manifest_path, "backup manifest")
    artifact_info = manifest.get("artifact")
    if type(artifact_info) is not dict or artifact_info.get("path") != "postgres.dump":
        raise AttestationRefusal("backup artifact path must be postgres.dump")
    plan_identity = _identity(plan.get("database_identity"), "plan")
    manifest_identity = _identity(manifest.get("database_identity"), "backup")
    if plan_identity != manifest_identity:
        raise AttestationRefusal("plan and manifest database identity mismatch")
    target = target_fingerprint(plan_identity)
    if plan.get("target_fingerprint") != target:
        raise AttestationRefusal("plan target fingerprint mismatch")
    if manifest.get("target_fingerprint") != target:
        raise AttestationRefusal("manifest target fingerprint mismatch")

    try:
        migration._validate_plan_for_apply(plan, plan_sha, target, now)
    except migration.MigrationRefusal as exc:
        raise AttestationRefusal(str(exc)) from None
    backup = migration.BackupEvidence(
        manifest=manifest,
        manifest_sha256=manifest_sha,
        artifact_root=run,
    )
    try:
        migration.validate_backup_manifest(
            backup,
            expected_target=target,
            now=now,
            require_fresh=True,
        )
    except migration.MigrationRefusal as exc:
        raise AttestationRefusal(str(exc)) from None

    dump_raw, dump_metadata = _stable_read(dump_path, "postgres dump")
    dump_identity = (dump_metadata.st_dev, dump_metadata.st_ino, dump_metadata.st_size)
    if dump_metadata.st_size != artifact_info.get("size"):
        raise AttestationRefusal("backup artifact size mismatch")
    dump_sha = hashlib.sha256(dump_raw).hexdigest()
    if dump_sha != artifact_info.get("sha256"):
        raise AttestationRefusal("backup artifact hash mismatch")
    listing_raw, listing_metadata = _stable_read(listing_path, "restore listing")
    listing_identity = (
        listing_metadata.st_dev,
        listing_metadata.st_ino,
        listing_metadata.st_size,
    )
    listing_sha = hashlib.sha256(listing_raw).hexdigest()
    validation = manifest.get("validation")
    if type(validation) is not dict or listing_sha != validation.get("listing_sha256"):
        raise AttestationRefusal("backup listing hash mismatch")
    _validate_restore_listing(
        dump_path,
        listing_path,
        dump_sha,
        listing_sha,
        dump_identity,
        listing_identity,
    )

    return {
        "plan": {"path": _relative(root, plan_path), "sha256": plan_sha},
        "manifest": {"path": _relative(root, manifest_path), "sha256": manifest_sha},
        "dump": {
            "path": _relative(root, dump_path),
            "size": int(dump_metadata.st_size),
            "sha256": dump_sha,
        },
        "restore_list": {"path": _relative(root, listing_path), "sha256": listing_sha},
        "database_identity": plan_identity,
        "target_fingerprint": target,
    }


def _capture_artifact_snapshots(
    root: Path, artifacts: dict[str, object]
) -> tuple[ArtifactSnapshot, ...]:
    snapshots: list[ArtifactSnapshot] = []
    for key, canonical_json in (
        ("plan", True),
        ("manifest", True),
        ("dump", False),
        ("restore_list", False),
    ):
        artifact = artifacts[key]
        if type(artifact) is not dict:
            raise AttestationRefusal("artifact summary is malformed")
        path = root / str(artifact["path"])
        raw, metadata = _stable_read(path, f"{key} artifact")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != artifact.get("sha256"):
            raise AttestationRefusal("artifact changed before snapshot")
        if canonical_json:
            _validate_canonical_object_bytes(raw, f"{key} artifact")
        snapshots.append(
            ArtifactSnapshot(
                path=path,
                identity=(metadata.st_dev, metadata.st_ino),
                size=metadata.st_size,
                sha256=digest,
                canonical_json=canonical_json,
            )
        )
    return tuple(snapshots)


def _revalidate_artifact_snapshots(
    snapshots: tuple[ArtifactSnapshot, ...],
) -> None:
    for snapshot in snapshots:
        raw, metadata = _stable_read(snapshot.path, "attested artifact")
        if (
            (metadata.st_dev, metadata.st_ino) != snapshot.identity
            or metadata.st_size != snapshot.size
            or hashlib.sha256(raw).hexdigest() != snapshot.sha256
        ):
            raise AttestationRefusal("artifact changed after attestation validation")
        if snapshot.canonical_json:
            _validate_canonical_object_bytes(raw, "attested JSON artifact")


def git_state(_root: Path) -> dict[str, object]:
    try:
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        raise AttestationRefusal("unable to determine source revision") from None
    head = head_result.stdout.strip()
    if head_result.returncode != 0 or HEAD_RE.fullmatch(head) is None:
        raise AttestationRefusal("unable to determine source revision")
    if status_result.returncode != 0:
        raise AttestationRefusal("unable to determine worktree state")
    return {"head": head, "worktree_clean": status_result.stdout == ""}


def run_acl_helper(mode: str, root: Path) -> dict[str, object]:
    pwsh = shutil.which("pwsh") or r"C:\Program Files\PowerShell\7\pwsh.exe"
    try:
        result = subprocess.run(
            [
                pwsh,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(ACL_SCRIPT),
                "-Mode",
                mode,
                "-Root",
                str(root),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        raise AttestationRefusal("ACL verification helper unavailable") from None
    if result.returncode != 0 or result.stderr or not result.stdout.strip():
        raise AttestationRefusal("ACL verification failed")
    try:
        evidence = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise AttestationRefusal("ACL verification returned invalid evidence") from None
    if type(evidence) is not dict:
        raise AttestationRefusal("ACL verification returned invalid evidence")
    if set(evidence) != ACL_KEYS | {"root"}:
        raise AttestationRefusal("ACL verification returned invalid evidence")
    _validate_acl_root(evidence["root"], root)
    _validate_allowed_principals(evidence["allowed_principals"])
    return evidence


def _fresh(timestamp: object, label: str, now: datetime) -> str:
    parsed = _parse_utc(timestamp, label)
    age = (now - parsed).total_seconds()
    if age < 0 or age > MAX_EVIDENCE_AGE_SECONDS:
        raise AttestationRefusal(f"{label} evidence is stale")
    return _utc_text(parsed)


def _validate_noindex(value: object, now: datetime) -> dict[str, object]:
    noindex = _require_exact(
        value,
        {
            "url",
            "checked_at",
            "status",
            "x_robots_tag",
            "robots_meta_count",
            "robots_meta_value",
            "body_sha256",
        },
        "noindex",
    )
    if type(noindex["url"]) is not str or not noindex["url"]:
        raise AttestationRefusal("noindex URL is invalid")
    _fresh(noindex["checked_at"], "noindex", now)
    if noindex["status"] != 200 or type(noindex["status"]) is not int:
        raise AttestationRefusal("noindex HTTP status is invalid")
    if noindex["x_robots_tag"] != "noindex, follow":
        raise AttestationRefusal("noindex X-Robots-Tag is invalid")
    if (
        noindex["robots_meta_count"] != 1
        or type(noindex["robots_meta_count"]) is not int
    ):
        raise AttestationRefusal("robots meta count is invalid")
    if noindex["robots_meta_value"] != "noindex, follow":
        raise AttestationRefusal("robots meta value is invalid")
    _require_sha(noindex["body_sha256"], "noindex body hash")
    return {
        "url": noindex["url"],
        "checked_at": _utc_text(_parse_utc(noindex["checked_at"], "noindex")),
        "status": 200,
        "x_robots_tag": "noindex, follow",
        "robots_meta_count": 1,
        "robots_meta_value": "noindex, follow",
        "body_sha256": noindex["body_sha256"],
    }


def _validate_role(value: object, now: datetime) -> dict[str, object]:
    role = _require_exact(
        value,
        {"name", "expires_at", "role_absent", "absent_checked_at"},
        "temporary role",
    )
    if type(role["name"]) is not str or not role["name"]:
        raise AttestationRefusal("temporary role name is invalid")
    _parse_utc(role["expires_at"], "temporary role expiry")
    _fresh(role["absent_checked_at"], "temporary role", now)
    if role["role_absent"] is not True:
        raise AttestationRefusal("role cleanup is incomplete")
    return {
        "name": role["name"],
        "expires_at": _utc_text(
            _parse_utc(role["expires_at"], "temporary role expiry")
        ),
        "role_absent": True,
        "absent_checked_at": _utc_text(
            _parse_utc(role["absent_checked_at"], "temporary role")
        ),
    }


def _validate_tunnel(value: object, now: datetime) -> dict[str, object]:
    tunnel = _require_exact(
        value,
        {"endpoint", "pid", "process_absent", "listener_absent", "absent_checked_at"},
        "tunnel",
    )
    if type(tunnel["endpoint"]) is not str or not tunnel["endpoint"]:
        raise AttestationRefusal("tunnel endpoint is invalid")
    if type(tunnel["pid"]) is not int or tunnel["pid"] <= 0:
        raise AttestationRefusal("tunnel PID is invalid")
    _fresh(tunnel["absent_checked_at"], "tunnel", now)
    if tunnel["process_absent"] is not True or tunnel["listener_absent"] is not True:
        raise AttestationRefusal("tunnel cleanup is incomplete")
    return {
        "endpoint": tunnel["endpoint"],
        "pid": tunnel["pid"],
        "process_absent": True,
        "listener_absent": True,
        "absent_checked_at": _utc_text(
            _parse_utc(tunnel["absent_checked_at"], "tunnel")
        ),
    }


def _validate_operations(value: object) -> dict[str, bool]:
    operations = _require_exact(
        value,
        {"apply_run", "rollback_run", "export_run", "deploy_run"},
        "operations",
    )
    if any(value is not False for value in operations.values()):
        raise AttestationRefusal("operation flags must all be false")
    return {
        "apply_run": False,
        "rollback_run": False,
        "export_run": False,
        "deploy_run": False,
    }


def validate_evidence(
    evidence: object,
    now: datetime | None = None,
    source_state: dict[str, object] | None = None,
) -> dict[str, object]:
    now = now or _utc_now()
    source_state = source_state or git_state(Path.cwd())
    if type(evidence) is not dict:
        raise AttestationRefusal("evidence root must be an object")
    data = _require_exact(evidence, EVIDENCE_KEYS, "evidence")
    source = _require_exact(data["source"], {"head", "worktree_clean"}, "source")
    if type(source["head"]) is not str or HEAD_RE.fullmatch(source["head"]) is None:
        raise AttestationRefusal("source head is invalid")
    if source["worktree_clean"] is not True:
        raise AttestationRefusal("source worktree is dirty")
    if (
        source["head"] != source_state["head"]
        or source_state["worktree_clean"] is not True
    ):
        raise AttestationRefusal("source revision or worktree mismatch")
    return {
        "source": {"head": source["head"], "worktree_clean": True},
        "noindex": _validate_noindex(data["noindex"], now),
        "temporary_role": _validate_role(data["temporary_role"], now),
        "tunnel": _validate_tunnel(data["tunnel"], now),
        "operations": _validate_operations(data["operations"]),
    }


def _validate_acl_root(value: object, root: Path) -> None:
    if type(value) is not str or not value:
        raise AttestationRefusal("ACL evidence root is invalid")
    try:
        reported = Path(value).absolute()
    except OSError:
        raise AttestationRefusal("ACL evidence root is invalid") from None
    if reported != root.absolute():
        raise AttestationRefusal("ACL evidence root mismatch")


def _validate_allowed_principals(value: object) -> None:
    if (
        type(value) is not list
        or len(value) != 3
        or any(type(item) is not str or not item for item in value)
    ):
        raise AttestationRefusal("ACL principals are invalid")
    normalized = {item.casefold() for item in value}
    required = {
        "NT AUTHORITY\\SYSTEM".casefold(),
        "BUILTIN\\Administrators".casefold(),
    }
    if len(normalized) != 3 or not required.issubset(normalized):
        raise AttestationRefusal("ACL principals are invalid")


def _acl_summary(value: dict[str, object], root: Path) -> dict[str, object]:
    keys = set(value)
    if keys == ACL_KEYS | {"root"}:
        _validate_acl_root(value["root"], root)
        canonical = {key: value[key] for key in ACL_KEYS}
    elif keys == ACL_KEYS:
        canonical = dict(value)
    else:
        raise AttestationRefusal("ACL evidence fields are malformed")
    _validate_allowed_principals(canonical["allowed_principals"])
    checked_at = _parse_utc(canonical["checked_at"], "ACL")
    age = (_utc_now() - checked_at).total_seconds()
    if age < 0 or age > MAX_EVIDENCE_AGE_SECONDS:
        raise AttestationRefusal("ACL evidence is stale")
    if canonical["unexpected_principals"] != []:
        raise AttestationRefusal("ACL evidence is not explicit and clean")
    for key in (
        "inherited_rule_count",
        "reparse_point_count",
        "alternate_data_stream_count",
    ):
        if type(canonical[key]) is not int or canonical[key] != 0:
            raise AttestationRefusal("ACL evidence contains hostile objects")
    for key in ("object_count", "protected_object_count"):
        if type(canonical[key]) is not int or canonical[key] < 1:
            raise AttestationRefusal("ACL object counts are invalid")
    if canonical["protected_object_count"] != canonical["object_count"]:
        raise AttestationRefusal("ACL objects are not protected")
    return canonical


def _path_identity(path: Path) -> tuple[int, int]:
    metadata = _real_file(path, "attestation path")
    return metadata.st_dev, metadata.st_ino


def _assert_empty_attestation_links(
    pending: Path,
    output: Path,
    expected_identity: tuple[int, int] | None = None,
) -> tuple[int, int]:
    pending_metadata = _real_file(pending, "attestation pending path")
    output_metadata = _real_file(output, "attestation output path")
    pending_identity = (pending_metadata.st_dev, pending_metadata.st_ino)
    output_identity = (output_metadata.st_dev, output_metadata.st_ino)
    if pending_identity != output_identity or (
        expected_identity is not None and pending_identity != expected_identity
    ):
        raise AttestationRefusal("attestation hardlink identity mismatch")
    if pending_metadata.st_size != 0 or output_metadata.st_size != 0:
        raise AttestationRefusal(
            "attestation hardlinks must remain empty before ACL normalization"
        )
    return pending_identity


def _create_empty_links(root: Path, output: Path) -> tuple[Path, tuple[int, int]]:
    if output.exists() or os.path.lexists(output):
        raise AttestationRefusal("attestation output already exists")
    if not _within(root, output.absolute()):
        raise AttestationRefusal("attestation output escapes artifact root")
    if output.parent != root:
        raise AttestationRefusal(
            "attestation output must be directly under artifact root"
        )
    _real_dir(output.parent, "attestation output directory")
    pending = root / f".pending-write-{secrets.token_hex(16)}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(pending, flags, 0o600)
        os.close(descriptor)
        os.link(pending, output, follow_symlinks=False)
    except FileExistsError:
        raise AttestationRefusal("attestation output already exists") from None
    except OSError:
        raise AttestationRefusal("unable to allocate attestation paths") from None
    identity = _assert_empty_attestation_links(pending, output)
    return pending, identity


def _write_owned_pending(
    pending: Path, output: Path, identity: tuple[int, int], payload: bytes
) -> str:
    if _path_identity(pending) != identity or _path_identity(output) != identity:
        raise AttestationRefusal("attestation hardlink identity changed")
    flags = os.O_RDWR | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(pending, flags)
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != identity:
            os.close(descriptor)
            raise AttestationRefusal("attestation pending identity changed")
        with os.fdopen(descriptor, "r+b", closefd=True) as stream:
            stream.seek(0)
            stream.truncate(0)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except AttestationRefusal:
        raise
    except OSError:
        raise AttestationRefusal("unable to write attestation") from None
    digest = hashlib.sha256(payload).hexdigest()
    for path in (pending, output):
        before = _real_file(path, "attestation path")
        if (before.st_dev, before.st_ino) != identity or before.st_size != len(payload):
            raise AttestationRefusal("attestation identity or size verification failed")
        if sha256_file(path) != digest:
            raise AttestationRefusal("attestation hash verification failed")
        after = _real_file(path, "attestation path")
        if (after.st_dev, after.st_ino, after.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise AttestationRefusal(
                "attestation path changed during hash verification"
            )
    return digest


def _verify_published_attestation(
    pending: Path,
    output: Path,
    identity: tuple[int, int],
    payload: bytes,
    digest: str,
) -> None:
    pending_raw, pending_metadata = _stable_read(pending, "attestation pending path")
    output_raw, output_metadata = _stable_read(output, "attestation output path")
    pending_identity = (pending_metadata.st_dev, pending_metadata.st_ino)
    output_identity = (output_metadata.st_dev, output_metadata.st_ino)
    if pending_identity != identity or output_identity != identity:
        raise AttestationRefusal("attestation hardlink identity changed")
    if pending_metadata.st_nlink != 2 or output_metadata.st_nlink != 2:
        raise AttestationRefusal("attestation hardlink count is invalid")
    if pending_raw != payload or output_raw != payload:
        raise AttestationRefusal("attestation canonical bytes changed")
    if hashlib.sha256(pending_raw).hexdigest() != digest:
        raise AttestationRefusal("attestation hash changed after ACL verification")
    _validate_canonical_object_bytes(output_raw, "attestation")


def build_attestation(
    root: Path,
    output: Path,
    evidence: dict[str, object],
    now: datetime | None = None,
) -> tuple[dict[str, object], str]:
    now = now or _utc_now()
    _assert_no_reparse_ancestors(root)
    _real_dir(root, "artifact root")
    _acl_summary(run_acl_helper("Verify", root), root)
    source_state = git_state(root)
    validated_evidence = validate_evidence(evidence, now, source_state)
    artifacts = validate_artifacts(root, now)
    plan, _plan_sha = load_canonical_object(
        root / "published-v1-plan.json", "publication plan"
    )
    if plan.get("tool_source_revision") != source_state["head"]:
        raise AttestationRefusal("plan source revision mismatch")
    artifact_snapshots = _capture_artifact_snapshots(root, artifacts)
    preallocation_now = _utc_now()
    validated_evidence = validate_evidence(evidence, preallocation_now, source_state)
    base = {
        "schema": SCHEMA,
        "attestation_revision": ATTESTATION_REVISION,
        "generated_at": _utc_text(preallocation_now),
        "source": validated_evidence["source"],
        "artifacts": {
            "plan": artifacts["plan"],
            "manifest": artifacts["manifest"],
            "dump": artifacts["dump"],
            "restore_list": artifacts["restore_list"],
        },
        "target": {
            "database_identity": artifacts["database_identity"],
            "target_fingerprint": artifacts["target_fingerprint"],
        },
        "noindex": validated_evidence["noindex"],
        "temporary_role": validated_evidence["temporary_role"],
        "tunnel": validated_evidence["tunnel"],
        "operations": validated_evidence["operations"],
    }
    try:
        canonical_json_bytes(base)
    except (TypeError, ValueError):
        raise AttestationRefusal("attestation sections are not serializable") from None
    pending, identity = _create_empty_links(root, output)
    _assert_empty_attestation_links(pending, output, identity)
    acl = run_acl_helper("NormalizeAndVerify", root)
    write_now = _utc_now()
    validated_evidence = validate_evidence(evidence, write_now, source_state)
    base.update(
        {
            "generated_at": _utc_text(write_now),
            "source": validated_evidence["source"],
            "noindex": validated_evidence["noindex"],
            "temporary_role": validated_evidence["temporary_role"],
            "tunnel": validated_evidence["tunnel"],
            "operations": validated_evidence["operations"],
        }
    )
    final = dict(base)
    final["acl"] = _acl_summary(acl, root)
    try:
        payload = canonical_json_bytes(final)
    except (TypeError, ValueError):
        raise AttestationRefusal("attestation is not serializable") from None
    digest = _write_owned_pending(pending, output, identity, payload)
    final_acl = _acl_summary(run_acl_helper("Verify", root), root)
    for key, value in final["acl"].items():
        if key != "checked_at" and final_acl[key] != value:
            raise AttestationRefusal("ACL evidence changed after attestation write")
    finalization_now = _utc_now()
    validate_evidence(evidence, finalization_now, source_state)
    _revalidate_artifact_snapshots(artifact_snapshots)
    _verify_published_attestation(pending, output, identity, payload, digest)
    if git_state(root) != source_state:
        raise AttestationRefusal(
            "source revision or worktree changed during attestation"
        )
    return final, digest


def main(
    argv: list[str] | None = None,
    *,
    stdin: Any | None = None,
) -> int:
    args = parse_args() if argv is None else _parser().parse_args(argv)
    try:
        evidence = _read_stdin(sys.stdin if stdin is None else stdin)
        root = args.artifact_root.absolute()
        output = args.out.absolute()
        document, digest = build_attestation(root, output, evidence)
    except AttestationRefusal as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: Stage B attestation refused", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"attestation_path": str(output), "sha256": digest},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
