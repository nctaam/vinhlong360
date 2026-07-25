import argparse
from dataclasses import dataclass
import gzip
import hashlib
import io
import ipaddress
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


CANONICAL_ARTIFACTS = (
    "launch-indexing-policy.json",
    "ai-disclosure.json",
)

_CACHE_DIRECTORIES = {
    "__pycache__",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
}
_RUNTIME_FILENAMES = {
    ".coverage",
    ".DS_Store",
    "coverage.xml",
    "Thumbs.db",
}
_RUNTIME_SUFFIXES = (
    ".db",
    ".jsonl",
    ".log",
    ".pid",
    ".pyc",
    ".pyo",
    ".sock",
    ".sqlite",
    ".sqlite3",
)
_LAUNCH_EXCLUDED_DIRECTORIES = _CACHE_DIRECTORIES | {
    ".git",
    "data",
    "docs",
    "node_modules",
    "tests",
}
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_READINESS_PATH = "web-nuxt/.output/server/launch-readiness-manifest.json"
_AUDIT_CHECK_NAMES = (
    "agent_bind_host",
    "bot_bind_host_and_agent_url",
    "container_names_absent",
    "developer_added_publications_loopback",
    "exact_healthcheck_commands",
    "maintenance_initializer_exact",
    "maintenance_runtime_shared_with_host",
    "non_nginx_services_unpublished",
    "no_external_or_host_network",
    "nginx_exclusive_public_endpoints",
    "nginx_depends_on_healthy_nuxt_and_completed_maintenance_init",
    "nuxt_backend_independent_readiness",
    "nuxt_bind_host",
    "nuxt_compose_api_origins",
    "no_launch_unlock_environment",
    "required_services_present",
    "shared_private_bridge_network",
    "systemd_dependency_topology",
)
_AUDIT_SOURCE_PATHS = (
    "docker-compose.dev.yml",
    "docker-compose.prod.yml",
    "docker-compose.systemd-deps.yml",
    "docker-compose.yml",
)
_READINESS_ROUTE_CLASSES = (
    "public-html",
    "public-api",
    "root-seo",
    "internal-readiness",
)
_FORBIDDEN_CACHE_CLASSES = (
    "navigation",
    "html",
    "root-seo",
    "internal",
    "api",
    "selective-open",
    "failed-open",
)
_OPEN_TEMPORARY_DESCRIPTORS: dict[Path, int] = {}


@dataclass(frozen=True)
class LaunchReleasePackage:
    archive: Path
    digest_file: Path
    manifest: Mapping[str, object]


@dataclass(frozen=True)
class _SnapshotSource:
    path: Path
    directory: bool
    identity: os.stat_result
    raw: bytes | None


@dataclass(frozen=True)
class _SnapshotMember:
    source: _SnapshotSource
    arcname: str


@dataclass(frozen=True)
class _LaunchReleaseSnapshot:
    root: Path
    members: tuple[_SnapshotMember, ...]
    sources: Mapping[Path, _SnapshotSource]


def _lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def find_duplicate_artifacts(root: Path) -> list[Path]:
    root = _lexical_path(root)
    invalid: set[Path] = set()
    for name in CANONICAL_ARTIFACTS:
        canonical = root / "config" / name
        if canonical.is_symlink() or (canonical.exists() and not canonical.is_file()):
            invalid.add(canonical)
        for path in root.rglob(name):
            lexical = _lexical_path(path)
            if lexical != canonical or path.is_symlink() or not path.is_file():
                invalid.add(lexical)
    return sorted(invalid, key=lambda path: path.as_posix())


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _excluded_agent_path(relative: Path, *, is_directory: bool) -> bool:
    if relative.parts and relative.parts[0] == "data":
        return True
    if any(part in _CACHE_DIRECTORIES for part in relative.parts):
        return True
    if is_directory:
        return False
    name = relative.name
    lower_name = name.lower()
    if name in _RUNTIME_FILENAMES or lower_name == ".env" or lower_name.startswith(
        ".env."
    ):
        return True
    return lower_name.endswith(_RUNTIME_SUFFIXES) or ".log." in lower_name


def _collect_tree(
    source: Path,
    arcroot: str,
    release_root: Path,
    *,
    filter_agent_runtime: bool,
) -> list[tuple[Path, str]]:
    payload = [(source, arcroot)]
    for current_root, dirnames, filenames in os.walk(source, topdown=True):
        current = Path(current_root)
        relative_current = current.relative_to(source)
        accepted = _collect_tree_directories(
            current,
            relative_current,
            arcroot,
            dirnames,
            release_root,
            filter_agent_runtime=filter_agent_runtime,
        )
        dirnames[:] = [dirname for dirname, _, _ in accepted]
        payload.extend((path, arcname) for _, path, arcname in accepted)
        payload.extend(
            _collect_tree_files(
                current,
                relative_current,
                filenames,
                release_root,
                arcroot,
                filter_agent_runtime=filter_agent_runtime,
            )
        )
    return payload


def _collect_tree_directories(
    current: Path,
    relative_current: Path,
    arcroot: str,
    dirnames: list[str],
    release_root: Path,
    *,
    filter_agent_runtime: bool,
) -> list[tuple[str, Path, str]]:
    accepted: list[tuple[str, Path, str]] = []
    for dirname in sorted(dirnames):
        path = current / dirname
        relative = relative_current / dirname
        excluded = filter_agent_runtime and _excluded_agent_path(
            relative, is_directory=True
        )
        if path.is_symlink() or not _is_within(path, release_root) or excluded:
            continue
        accepted.append((dirname, path, (Path(arcroot) / relative).as_posix()))
    return accepted


def _collect_tree_files(
    current: Path,
    relative_current: Path,
    filenames: list[str],
    release_root: Path,
    arcroot: str,
    *,
    filter_agent_runtime: bool,
) -> list[tuple[Path, str]]:
    payload: list[tuple[Path, str]] = []
    for filename in sorted(filenames):
        path = current / filename
        relative = relative_current / filename
        excluded = filter_agent_runtime and _excluded_agent_path(
            relative, is_directory=False
        )
        if (
            path.is_symlink()
            or not path.is_file()
            or not _is_within(path, release_root)
            or excluded
        ):
            continue
        payload.append((path, (Path(arcroot) / relative).as_posix()))
    return payload


def _require_directory(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"required release directory is unsafe: {path}")


def _require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required release file is unsafe: {path}")


def _preflight(root: Path, destination: Path) -> None:
    _require_directory(root)
    _require_directory(root / "agent")
    _require_directory(root / "config")
    _require_file(root / "requirements.txt")
    _require_file(root / "init.sql")

    destination_parent = destination.parent
    _require_directory(destination_parent)
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError(f"release destination is unsafe: {destination}")
    if _is_within(destination, root):
        raise ValueError("release destination must be outside source root")

    duplicates = find_duplicate_artifacts(root)
    if duplicates:
        details = ", ".join(path.as_posix() for path in duplicates)
        raise ValueError(f"duplicate canonical launch artifacts: {details}")


def _collect_payload(root: Path) -> list[tuple[Path, str]]:
    payload = _collect_tree(
        root / "agent",
        "agent",
        root,
        filter_agent_runtime=True,
    )
    payload.extend(
        (
            (root / "requirements.txt", "requirements.txt"),
            (root / "init.sql", "init.sql"),
        )
    )
    payload.extend(
        _collect_tree(
            root / "config",
            "config",
            root,
            filter_agent_runtime=False,
        )
    )
    data_file = root / "web" / "data.json"
    if data_file.is_symlink():
        raise ValueError(f"optional release file is unsafe: {data_file}")
    if data_file.exists():
        if not data_file.is_file() or not _is_within(data_file, root):
            raise ValueError(f"optional release file is unsafe: {data_file}")
        payload.append((data_file, "web/data.json"))
    return sorted(payload, key=lambda item: item[1])


def _normalize_tar_info(info: tarfile.TarInfo, source: Path) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.pax_headers = {}
    if info.isdir():
        info.mode = 0o755
    elif info.isfile():
        info.mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
    return info


def _write_archive(destination: Path, payload: list[tuple[Path, str]]) -> None:
    with destination.open("wb") as raw_archive:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=raw_archive,
            mtime=0,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
            ) as archive:
                for source, arcname in payload:
                    info = _normalize_tar_info(
                        archive.gettarinfo(str(source), arcname=arcname), source
                    )
                    if info.isfile():
                        with source.open("rb") as source_file:
                            archive.addfile(info, source_file)
                    else:
                        archive.addfile(info)


def build_backend_archive(root: Path, destination: Path) -> Path:
    requested_destination = Path(destination)
    root = _lexical_path(root)
    destination = _lexical_path(destination)
    _preflight(root, destination)
    payload = _collect_payload(root)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        _write_archive(temporary, payload)
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return requested_destination


def _path_exists(path: Path) -> bool:
    return os.path.lexists(path)


def _require_safe_source(root: Path, path: Path, *, directory: bool) -> None:
    root = _lexical_path(root)
    path = _lexical_path(path)
    if root.is_symlink():
        raise ValueError(f"release source contains symlink: {root}")
    if not _is_within(path, root):
        raise ValueError(f"release source escapes root: {path}")
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"release source escapes root: {path}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"release source contains symlink: {current}")
    if not path.exists():
        raise FileNotFoundError(path)
    if directory and not path.is_dir():
        raise ValueError(f"required release directory is unsafe: {path}")
    if not directory and not path.is_file():
        raise ValueError(f"required release file is unsafe: {path}")


def _launch_path_is_excluded(relative: Path) -> bool:
    parts = relative.parts
    if any(part in _LAUNCH_EXCLUDED_DIRECTORIES for part in parts):
        return True
    if any(
        token in part.lower()
        for part in parts
        for token in ("secret", "unlock")
    ):
        return True
    if not parts:
        return False
    name = parts[-1]
    lower_name = name.lower()
    if lower_name == ".env" or lower_name.startswith(".env."):
        return True
    if name in _RUNTIME_FILENAMES:
        return True
    return lower_name.endswith(_RUNTIME_SUFFIXES) or ".log." in lower_name


def _collect_launch_tree(
    root: Path,
    source: Path,
    arcroot: str,
    *,
    filter_runtime: bool,
) -> list[tuple[Path, str]]:
    _require_safe_source(root, source, directory=True)
    payload: list[tuple[Path, str]] = [(source, arcroot)]
    for current_root, dirnames, filenames in os.walk(source, topdown=True):
        current = Path(current_root)
        relative_current = current.relative_to(source)
        accepted_directories: list[str] = []
        for dirname in sorted(dirnames):
            path = current / dirname
            relative = relative_current / dirname
            if path.is_symlink():
                raise ValueError(f"release source contains symlink: {path}")
            if filter_runtime and _launch_path_is_excluded(relative):
                continue
            _require_safe_source(root, path, directory=True)
            accepted_directories.append(dirname)
            payload.append((path, (Path(arcroot) / relative).as_posix()))
        dirnames[:] = accepted_directories
        for filename in sorted(filenames):
            path = current / filename
            relative = relative_current / filename
            if path.is_symlink():
                raise ValueError(f"release source contains symlink: {path}")
            if filter_runtime and _launch_path_is_excluded(relative):
                continue
            _require_safe_source(root, path, directory=False)
            payload.append((path, (Path(arcroot) / relative).as_posix()))
    return payload


def _collect_launch_file(
    root: Path,
    relative: str,
    *,
    arcname: str | None = None,
) -> tuple[Path, str]:
    source = root / Path(relative)
    _require_safe_source(root, source, directory=False)
    return source, arcname or Path(relative).as_posix()


def _snapshot_regular_source(root: Path, path: Path) -> _SnapshotSource:
    """Read a regular source through one descriptor and retain its identity."""
    path = _lexical_path(path)
    _require_safe_source(root, path, directory=False)
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"release source changed while snapshotting: {path}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"required release file is unsafe: {path}")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(os.fspath(path), flags)
    except OSError as exc:
        raise ValueError(f"release source changed while snapshotting: {path}") from exc
    try:
        opened = os.fstat(descriptor)
        if not os.path.samestat(before, opened) or not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"release source changed while snapshotting: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as source_file:
            raw = source_file.read()
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    try:
        _require_safe_source(root, path, directory=False)
        after = path.stat(follow_symlinks=False)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"release source changed while snapshotting: {path}") from exc
    if (
        not os.path.samestat(before, after_open)
        or not os.path.samestat(before, after)
        or not stat.S_ISREG(after.st_mode)
    ):
        raise ValueError(f"release source changed while snapshotting: {path}")
    return _SnapshotSource(path, False, before, raw)


def _snapshot_directory_source(root: Path, path: Path) -> _SnapshotSource:
    path = _lexical_path(path)
    _require_safe_source(root, path, directory=True)
    try:
        identity = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"release source changed while snapshotting: {path}") from exc
    if not stat.S_ISDIR(identity.st_mode):
        raise ValueError(f"required release directory is unsafe: {path}")
    return _SnapshotSource(path, True, identity, None)


def _snapshot_launch_release(
    root: Path, payload: list[tuple[Path, str]]
) -> _LaunchReleaseSnapshot:
    root = _lexical_path(root)
    sources: dict[Path, _SnapshotSource] = {}
    members: list[_SnapshotMember] = []
    for source, arcname in payload:
        source = _lexical_path(source)
        existing = sources.get(source)
        if existing is None:
            try:
                state = source.stat(follow_symlinks=False)
            except OSError as exc:
                raise ValueError(f"release source changed while snapshotting: {source}") from exc
            if stat.S_ISLNK(state.st_mode):
                raise ValueError(f"release source contains symlink: {source}")
            if stat.S_ISDIR(state.st_mode):
                existing = _snapshot_directory_source(root, source)
            elif stat.S_ISREG(state.st_mode):
                existing = _snapshot_regular_source(root, source)
            else:
                raise ValueError(f"release source is not a regular file or directory: {source}")
            sources[source] = existing
        members.append(_SnapshotMember(existing, arcname))

    # Compose files are validated but intentionally not included in the archive.
    for relative in _AUDIT_SOURCE_PATHS:
        source = _lexical_path(root / relative)
        if source not in sources:
            sources[source] = _snapshot_regular_source(root, source)
    return _LaunchReleaseSnapshot(
        root,
        tuple(members),
        MappingProxyType(sources),
    )


def _snapshot_raw(
    root: Path,
    snapshot: _LaunchReleaseSnapshot,
    path: Path,
    label: str,
) -> bytes:
    path = _lexical_path(path)
    _require_safe_source(root, path, directory=False)
    source = snapshot.sources.get(path)
    if source is None or source.directory or source.raw is None:
        raise ValueError(f"{label} was not captured in the release snapshot")
    return source.raw


def _revalidate_snapshot(snapshot: _LaunchReleaseSnapshot) -> None:
    """Reject pathname swaps while allowing in-place writes to use captured bytes."""
    for source in snapshot.sources.values():
        if source.path.is_symlink():
            raise ValueError(f"release source contains symlink: {source.path}")
        try:
            _require_safe_source(snapshot.root, source.path, directory=source.directory)
            current = source.path.stat(follow_symlinks=False)
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise ValueError(f"release source changed: {source.path}") from exc
        if not os.path.samestat(source.identity, current):
            raise ValueError(f"release source changed: {source.path}")


def _json_object(raw: bytes, label: str) -> tuple[dict[str, object], bytes]:

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value, raw


def _exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keys mismatch")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validated_canonical_artifacts(
    root: Path, snapshot: _LaunchReleaseSnapshot
) -> dict[str, object]:
    duplicates = find_duplicate_artifacts(root)
    if duplicates:
        details = ", ".join(path.as_posix() for path in duplicates)
        raise ValueError(f"duplicate canonical launch artifacts: {details}")
    result: dict[str, object] = {}
    definitions = (
        (
            "route_manifest",
            "config/launch-indexing-policy.json",
            "launch-indexing-policy-v1",
        ),
        ("ai_disclosure", "config/ai-disclosure.json", "ai-disclosure-v1"),
    )
    for key, relative, expected_revision in definitions:
        path = root / relative
        raw = _snapshot_raw(root, snapshot, path, f"canonical artifact {relative}")
        artifact, raw = _json_object(raw, f"canonical artifact {relative}")
        expected_keys = (
            {
                "schema_version",
                "revision",
                "canonical_origin",
                "unknown_policy",
                "normalization",
                "exact_routes",
                "sensitive_prefixes",
                "dynamic_templates",
                "backend_ingress_exceptions",
            }
            if key == "route_manifest"
            else {
                "schema_version",
                "revision",
                "entity_ai",
                "placeholder",
                "ugc_photo",
                "forbidden_entity_image_claims",
            }
        )
        _exact_keys(artifact, expected_keys, f"canonical artifact {relative}")
        if type(artifact.get("schema_version")) is not int or artifact.get(
            "schema_version"
        ) != 1:
            raise ValueError(f"canonical artifact schema mismatch: {relative}")
        if artifact.get("revision") != expected_revision:
            raise ValueError(f"canonical artifact revision mismatch: {relative}")
        result[key] = {
            "revision": expected_revision,
            "sha256": _sha256_bytes(raw),
        }
    return result


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _policy_fingerprint(canonical_artifacts: Mapping[str, object]) -> str:
    route = canonical_artifacts["route_manifest"]
    disclosure = canonical_artifacts["ai_disclosure"]
    if not isinstance(route, dict) or not isinstance(disclosure, dict):
        raise ValueError("canonical artifact evidence is invalid")
    route_digest = _require_sha256(route["sha256"], "route artifact digest")
    disclosure_digest = _require_sha256(
        disclosure["sha256"], "disclosure artifact digest"
    )
    payload = {
        "cache_isolation": "launch-cache-isolation-v1",
        "disclosure_artifact": {
            "revision": "ai-disclosure-v1",
            "sha256": disclosure_digest,
        },
        "index_policy": "index-policy-v1",
        "response_matrix": "launch-safety-matrix-v1",
        "route_artifact": {
            "revision": "launch-indexing-policy-v1",
            "sha256": route_digest,
        },
        "sitemap_protocol": "pinned-sitemap-bundle-v1",
    }
    return _sha256_bytes(_canonical_json_bytes(payload).rstrip(b"\n"))


def _validate_readiness_manifest(
    root: Path,
    source_revision: str,
    canonical_artifacts: Mapping[str, object],
    snapshot: _LaunchReleaseSnapshot,
) -> tuple[Path, bytes]:
    path = root / Path(_READINESS_PATH)
    raw = _snapshot_raw(root, snapshot, path, "launch readiness manifest")
    manifest, raw = _json_object(raw, "launch readiness manifest")
    artifacts = _validate_readiness_shape(manifest, source_revision)
    _validate_readiness_artifacts(artifacts, canonical_artifacts)
    _validate_readiness_policy(manifest)
    _validate_readiness_worker(root, snapshot, manifest["service_worker"])
    return path, raw


def _validate_readiness_shape(
    manifest: dict[str, object], source_revision: str
) -> dict[str, object]:
    _exact_keys(
        manifest,
        {
            "schema_version",
            "build_revision",
            "artifacts",
            "policy_route_classes",
            "compiled_cache_rules",
            "public_prerender_files",
            "service_worker",
        },
        "launch readiness manifest",
    )
    if manifest["schema_version"] != 1 or type(manifest["schema_version"]) is not int:
        raise ValueError("launch readiness manifest schema mismatch")
    if manifest["build_revision"] != source_revision:
        raise ValueError("launch readiness manifest source revision mismatch")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict):
        raise ValueError("launch readiness artifacts must be an object")
    _exact_keys(
        artifacts,
        {"route_manifest", "ai_disclosure", "policy_fingerprint"},
        "launch readiness artifacts",
    )
    return artifacts


def _validate_readiness_artifacts(
    artifacts: dict[str, object], canonical_artifacts: Mapping[str, object]
) -> None:
    for name in ("route_manifest", "ai_disclosure"):
        evidence = artifacts[name]
        expected = canonical_artifacts[name]
        if not isinstance(evidence, dict) or not isinstance(expected, dict):
            raise ValueError(f"launch readiness {name} evidence is invalid")
        _exact_keys(evidence, {"revision", "sha256"}, f"launch readiness {name}")
        if evidence != expected:
            raise ValueError(f"launch readiness {name} evidence mismatch")
    policy_fingerprint = _require_sha256(
        artifacts["policy_fingerprint"], "launch readiness policy fingerprint"
    )
    if policy_fingerprint != _policy_fingerprint(canonical_artifacts):
        raise ValueError("launch readiness policy fingerprint mismatch")


def _validate_readiness_policy(manifest: dict[str, object]) -> None:
    if manifest["policy_route_classes"] != list(_READINESS_ROUTE_CLASSES):
        raise ValueError("launch readiness route classes mismatch")
    if manifest["compiled_cache_rules"] != []:
        raise ValueError("launch readiness compiled cache rules are unsafe")
    if manifest["public_prerender_files"] != []:
        raise ValueError("launch readiness contains policy-bearing prerender files")


def _validate_readiness_worker(
    root: Path, snapshot: _LaunchReleaseSnapshot, worker: object
) -> None:
    if not isinstance(worker, dict):
        raise ValueError("launch readiness service worker evidence is invalid")
    _exact_keys(worker, {"version", "rule_digest", "cache_purge"}, "service worker")
    if worker["version"] != "vl360-launch-v1":
        raise ValueError("launch readiness service worker version mismatch")
    worker_path = root / "web-nuxt" / ".output" / "public" / "sw.js"
    worker_raw = _snapshot_raw(root, snapshot, worker_path, "service worker")
    if _require_sha256(worker["rule_digest"], "service worker digest") != _sha256_bytes(
        worker_raw
    ):
        raise ValueError("launch readiness service worker digest mismatch")
    cache_purge = worker["cache_purge"]
    expected_purge = {
        "revision": "launch-cache-purge-v1",
        "strategy": "delete-all-except",
        "retained_cache_names": ["vl360-launch-v1-assets"],
        "forbidden_cache_classes": list(_FORBIDDEN_CACHE_CLASSES),
        "activation_verified": True,
    }
    if cache_purge != expected_purge:
        raise ValueError("launch readiness cache purge declaration mismatch")


def _normalized_source_digest(raw: bytes, path: Path) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"compose audit source is not UTF-8: {path}") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return _sha256_bytes(normalized)


def _validate_network_audit(
    root: Path, path: Path, snapshot: _LaunchReleaseSnapshot
) -> bytes:
    path = _lexical_path(path if path.is_absolute() else root / path)
    raw = _snapshot_raw(root, snapshot, path, "compose network audit")
    audit, raw = _json_object(raw, "compose network audit")
    _validate_network_audit_header(audit)
    _validate_network_audit_endpoints(audit["published_ports"])
    _validate_network_audit_sources(root, snapshot, audit)
    return raw


def _validate_network_audit_header(audit: dict[str, object]) -> None:
    _exact_keys(
        audit,
        {
            "schema_version",
            "revision",
            "check_names",
            "checks",
            "published_ports",
            "source_digest_kind",
            "sources",
        },
        "compose network audit",
    )
    if audit["schema_version"] != 1 or type(audit["schema_version"]) is not int:
        raise ValueError("compose network audit schema mismatch")
    if audit["revision"] != "compose-network-audit-v2":
        raise ValueError("compose network audit revision mismatch")
    expected_checks = sorted(_AUDIT_CHECK_NAMES)
    if audit["check_names"] != expected_checks:
        raise ValueError("compose network audit check inventory mismatch")
    if audit["checks"] != {name: "passed" for name in expected_checks}:
        raise ValueError("compose network audit did not pass every check")


def _validate_network_audit_endpoints(published_ports: object) -> None:
    if not isinstance(published_ports, list) or len(published_ports) != 2:
        raise ValueError("compose network audit published ports are invalid")
    endpoint_keys = [_network_audit_endpoint_key(endpoint) for endpoint in published_ports]
    if len(set(endpoint_keys)) != len(published_ports):
        raise ValueError("compose network audit published ports contain duplicates")
    if {
        (published, target)
        for _, _, published, target, _ in endpoint_keys
    } != {(80, 80), (443, 443)}:
        raise ValueError("compose network audit published ports are incomplete")
    if published_ports != sorted(
        published_ports,
        key=lambda endpoint: (
            str(endpoint["service"]),
            int(endpoint["published"]),
            int(endpoint["target"]),
            str(endpoint["host_ip"]),
            str(endpoint["protocol"]),
        ),
    ):
        raise ValueError("compose network audit endpoint ordering is non-canonical")


def _network_audit_endpoint_key(
    endpoint: object,
) -> tuple[str, str, int, int, str]:
    if not isinstance(endpoint, dict) or set(endpoint) != {
        "service", "host_ip", "published", "target", "protocol"
    }:
        raise ValueError("compose network audit endpoint shape is invalid")
    _validate_network_audit_endpoint_types(endpoint)
    _validate_network_audit_endpoint_host(endpoint)
    _validate_network_audit_endpoint_contract(endpoint)
    return (
        endpoint["service"],
        endpoint["host_ip"],
        endpoint["published"],
        endpoint["target"],
        endpoint["protocol"],
    )


def _validate_network_audit_endpoint_types(endpoint: dict[str, object]) -> None:
    if (
        type(endpoint["service"]) is not str
        or type(endpoint["host_ip"]) is not str
        or type(endpoint["published"]) is not int
        or type(endpoint["target"]) is not int
        or type(endpoint["protocol"]) is not str
    ):
        raise ValueError("compose network audit endpoint types are invalid")


def _validate_network_audit_endpoint_host(endpoint: dict[str, object]) -> None:
    try:
        host_ip = ipaddress.ip_address(endpoint["host_ip"])
    except ValueError as exc:
        raise ValueError("compose network audit endpoint host IP is invalid") from exc
    if endpoint["host_ip"] != host_ip.compressed or host_ip.is_loopback:
        raise ValueError("compose network audit endpoint host IP is invalid")


def _validate_network_audit_endpoint_contract(endpoint: dict[str, object]) -> None:
    if (
        endpoint["service"] != "nginx"
        or endpoint["published"] not in {80, 443}
        or endpoint["target"] != endpoint["published"]
        or endpoint["protocol"] != "tcp"
    ):
        raise ValueError("compose network audit exposes a non-nginx endpoint")


def _validate_network_audit_sources(
    root: Path, snapshot: _LaunchReleaseSnapshot, audit: dict[str, object]
) -> None:
    if audit["source_digest_kind"] != "sha256-utf8-lf-v1":
        raise ValueError("compose network audit source digest kind mismatch")
    sources = audit["sources"]
    if not isinstance(sources, list):
        raise ValueError("compose network audit sources are invalid")
    expected_sources = []
    for relative in _AUDIT_SOURCE_PATHS:
        source = root / relative
        source_raw = _snapshot_raw(root, snapshot, source, f"compose audit source {relative}")
        expected_sources.append(
            {"path": relative, "sha256": _normalized_source_digest(source_raw, source)}
        )
    if sources != expected_sources:
        raise ValueError("compose network audit sources are stale or incomplete")


def collect_launch_release_payload(
    root: Path, compose_network_audit: Path
) -> list[tuple[Path, str]]:
    root = _lexical_path(root)
    _require_safe_source(root, root, directory=True)
    payload = _collect_launch_tree(
        root, root / "agent", "agent", filter_runtime=True
    )
    payload.extend(
        _collect_launch_tree(
            root,
            root / "web-nuxt" / ".output",
            "web-nuxt/.output",
            filter_runtime=True,
        )
    )
    for relative in (
        "web-nuxt/package.json",
        "web-nuxt/package-lock.json",
        "requirements.txt",
        "init.sql",
        "nginx.conf",
        "nginx-ssl.conf",
        "scripts/check_migration_gate.py",
    ):
        payload.append(_collect_launch_file(root, relative))
    for relative in ("config", "ops/systemd", "ops/nginx/maintenance", "scripts/ops"):
        payload.extend(
            _collect_launch_tree(
                root, root / Path(relative), relative, filter_runtime=True
            )
        )
    audit_path = _lexical_path(
        compose_network_audit
        if Path(compose_network_audit).is_absolute()
        else root / compose_network_audit
    )
    _require_safe_source(root, audit_path, directory=False)
    payload.append((audit_path, "compose-network-audit.json"))
    by_name: dict[str, Path] = {}
    for source, arcname in payload:
        if arcname in by_name:
            raise ValueError(f"duplicate release archive member: {arcname}")
        by_name[arcname] = source
    return sorted(payload, key=lambda item: item[1])


def _regular_member_map(
    payload: _LaunchReleaseSnapshot | list[tuple[Path, str]]
) -> dict[str, object]:
    members: dict[str, object] = {}
    if isinstance(payload, _LaunchReleaseSnapshot):
        entries = ((member.source.raw, member.arcname, member.source.directory) for member in payload.members)
    else:
        entries = (
            (source.read_bytes() if source.is_file() else None, arcname, source.is_dir())
            for source, arcname in payload
        )
    for raw, arcname, directory in entries:
        if not directory and raw is not None:
            members[arcname] = {"sha256": _sha256_bytes(raw), "size": len(raw)}
    return members


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _validate_source_revision(source_revision: object) -> str:
    if (
        not isinstance(source_revision, str)
        or not source_revision
        or source_revision.strip() != source_revision
        or any(character in source_revision for character in "\r\n\0")
    ):
        raise ValueError("source revision must be a non-empty canonical string")
    return source_revision


def _build_launch_release_manifest_from_snapshot(
    snapshot: _LaunchReleaseSnapshot,
    source_revision: str,
    *,
    compose_network_audit: Path | None = None,
) -> dict[str, object]:
    source_revision = _validate_source_revision(source_revision)
    root = snapshot.root
    canonical_artifacts = _validated_canonical_artifacts(root, snapshot)
    _readiness_path, readiness_raw = _validate_readiness_manifest(
        root, source_revision, canonical_artifacts, snapshot
    )
    audit_members = [
        member.source.path
        for member in snapshot.members
        if member.arcname == "compose-network-audit.json"
    ]
    if len(audit_members) != 1:
        raise ValueError("release payload must contain exactly one network audit")
    payload_audit = _lexical_path(audit_members[0])
    audit_path = payload_audit
    if compose_network_audit is not None:
        audit_path = _lexical_path(
            compose_network_audit
            if Path(compose_network_audit).is_absolute()
            else root / compose_network_audit
        )
        if audit_path != payload_audit:
            raise ValueError("network audit must match the release payload member")
    audit_raw = _validate_network_audit(root, audit_path, snapshot)
    return {
        "schema_version": 1,
        "package_kind": "vl360-launch-release",
        "source_revision": source_revision,
        "launch_posture": "closed",
        "canonical_artifacts": canonical_artifacts,
        "readiness_manifest": {
            "path": _READINESS_PATH,
            "sha256": _sha256_bytes(readiness_raw),
        },
        "network_audit": {
            "path": "compose-network-audit.json",
            "sha256": _sha256_bytes(audit_raw),
        },
        "developer_override": {
            "path": "docker-compose.dev.yml",
            "included": False,
        },
        "persistent_paths": ["agent/data", "agent/data/sitemap-bundles"],
        "members": _regular_member_map(snapshot),
    }


def build_launch_release_manifest(
    root: Path,
    payload: list[tuple[Path, str]],
    source_revision: str,
    *,
    compose_network_audit: Path | None = None,
) -> dict[str, object]:
    source_revision = _validate_source_revision(source_revision)
    root = _lexical_path(root)
    snapshot = _snapshot_launch_release(root, payload)
    return _build_launch_release_manifest_from_snapshot(
        snapshot,
        source_revision,
        compose_network_audit=compose_network_audit,
    )


def _launch_tar_info(name: str, *, size: int = 0, directory: bool) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.mode = 0o755 if directory or (
        name.startswith("scripts/ops/") and name.endswith(".sh")
    ) else 0o644
    info.pax_headers = {}
    if directory:
        info.type = tarfile.DIRTYPE
        info.size = 0
    else:
        info.type = tarfile.REGTYPE
        info.size = size
    return info


def _snapshot_tar_payload(payload: list[tuple[Path, str]]) -> _LaunchReleaseSnapshot:
    root = _lexical_path(Path.cwd().anchor or Path.cwd())
    sources: dict[Path, _SnapshotSource] = {}
    members: list[_SnapshotMember] = []
    for source, arcname in payload:
        source = _lexical_path(source)
        captured = sources.get(source)
        if captured is None:
            state = source.stat(follow_symlinks=False)
            if stat.S_ISDIR(state.st_mode):
                captured = _snapshot_directory_source(root, source)
            elif stat.S_ISREG(state.st_mode):
                captured = _snapshot_regular_source(root, source)
            else:
                raise ValueError(f"release source is not a regular file or directory: {source}")
            sources[source] = captured
        members.append(_SnapshotMember(captured, arcname))
    return _LaunchReleaseSnapshot(root, tuple(members), MappingProxyType(sources))


def _write_snapshot_tar_gz(
    destination: Path,
    snapshot: _LaunchReleaseSnapshot,
    embedded_files: Mapping[str, bytes],
    *,
    destination_descriptor: int | None = None,
) -> None:
    _revalidate_snapshot(snapshot)
    entries: list[tuple[str, bytes | None, bool]] = []
    for member in snapshot.members:
        entries.append((member.arcname, member.source.raw, member.source.directory))
    for arcname, raw in embedded_files.items():
        entries.append((arcname, raw, False))
    if destination_descriptor is None:
        raw_archive_context = destination.open("wb")
    else:
        os.lseek(destination_descriptor, 0, os.SEEK_SET)
        os.ftruncate(destination_descriptor, 0)
        raw_archive_context = os.fdopen(
            os.dup(destination_descriptor), "wb", closefd=True
        )
    with raw_archive_context as raw_archive:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=raw_archive,
            mtime=0,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
            ) as archive:
                for arcname, raw, directory in sorted(entries):
                    if directory:
                        archive.addfile(_launch_tar_info(arcname, directory=True))
                        continue
                    if raw is None:
                        raise ValueError(f"snapshot has no bytes for archive member: {arcname}")
                    archive.addfile(
                        _launch_tar_info(arcname, size=len(raw), directory=False),
                        fileobj=io.BytesIO(raw),
                    )


def write_deterministic_tar_gz(
    destination: Path,
    payload: _LaunchReleaseSnapshot | list[tuple[Path, str]],
    embedded_files: Mapping[str, bytes],
    *,
    destination_descriptor: int | None = None,
) -> None:
    snapshot = payload if isinstance(payload, _LaunchReleaseSnapshot) else _snapshot_tar_payload(payload)
    _write_snapshot_tar_gz(
        destination,
        snapshot,
        embedded_files,
        destination_descriptor=destination_descriptor,
    )


def _require_safe_destination(path: Path) -> None:
    parent = path.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError(f"release destination directory is unsafe: {parent}")
    current = parent
    while True:
        if current.is_symlink():
            raise ValueError(f"release destination contains symlink: {current}")
        if current.parent == current:
            break
        current = current.parent
    if _path_exists(path):
        raise FileExistsError(f"release destination already exists: {path}")


def _publish_without_overwrite(temporary: Path, destination: Path) -> None:
    descriptor = _OPEN_TEMPORARY_DESCRIPTORS.get(_lexical_path(temporary))
    if descriptor is not None:
        _verify_open_temporary(descriptor, temporary, "temporary output")
    os.link(temporary, destination, follow_symlinks=False)
    if descriptor is None:
        return
    try:
        opened = os.fstat(descriptor)
        published = os.lstat(destination)
        if not stat.S_ISREG(published.st_mode) or not os.path.samestat(opened, published):
            raise ValueError("published output does not match temporary descriptor")
    except BaseException:
        try:
            candidate = os.lstat(destination)
            source = os.lstat(temporary)
            if os.path.samestat(candidate, source):
                destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _remove_owned_identity(
    identity: os.stat_result | None, destination: Path
) -> None:
    if identity is None:
        return
    try:
        current = os.lstat(destination)
        if stat.S_ISREG(current.st_mode) and os.path.samestat(identity, current):
            destination.unlink(missing_ok=True)
    except OSError:
        pass


def _verify_open_temporary(descriptor: int, path: Path, label: str) -> None:
    """Ensure an open temp descriptor still names the expected regular file."""
    try:
        opened = os.fstat(descriptor)
        named = os.lstat(path)
    except OSError as exc:
        raise ValueError(f"{label} changed before publish") from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or not os.path.samestat(opened, named)
    ):
        raise ValueError(f"{label} changed before publish")


def _sha256_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def _write_descriptor(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("temporary output write made no progress")
        view = view[written:]


def _cleanup_temporary_outputs(
    descriptors: tuple[int | None, ...], paths: tuple[Path | None, ...]
) -> OSError | None:
    first_error: OSError | None = None
    for descriptor in descriptors:
        if descriptor is None:
            continue
        try:
            os.close(descriptor)
        except OSError as exc:
            first_error = first_error or exc
    for path in paths:
        if path is None:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            first_error = first_error or exc
    return first_error


def build_launch_release(
    root: Path,
    destination: Path,
    *,
    compose_network_audit: Path,
    source_revision: str,
) -> LaunchReleasePackage:
    source_revision = _validate_source_revision(source_revision)
    requested_archive = Path(destination)
    requested_digest = requested_archive.with_name(requested_archive.name + ".sha256")
    root = _lexical_path(root)
    destination = _lexical_path(destination)
    digest_file = destination.with_name(destination.name + ".sha256")
    _require_safe_destination(destination)
    _require_safe_destination(digest_file)

    payload = collect_launch_release_payload(root, compose_network_audit)
    snapshot = _snapshot_launch_release(root, payload)
    manifest = _build_launch_release_manifest_from_snapshot(
        snapshot,
        source_revision,
    )
    manifest_raw = _canonical_json_bytes(manifest)
    temporary_archive: Path | None = None
    temporary_digest: Path | None = None
    archive_descriptor: int | None = None
    digest_descriptor: int | None = None
    archive_output_identity: os.stat_result | None = None
    digest_output_identity: os.stat_result | None = None
    try:
        archive_descriptor, archive_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary_archive = Path(archive_name)
        _OPEN_TEMPORARY_DESCRIPTORS[_lexical_path(temporary_archive)] = archive_descriptor
        digest_descriptor, digest_name = tempfile.mkstemp(
            prefix=f".{digest_file.name}.", suffix=".tmp", dir=digest_file.parent
        )
        temporary_digest = Path(digest_name)
        _OPEN_TEMPORARY_DESCRIPTORS[_lexical_path(temporary_digest)] = digest_descriptor
        write_deterministic_tar_gz(
            temporary_archive,
            snapshot,
            {"launch-release-manifest.json": manifest_raw},
            destination_descriptor=archive_descriptor,
        )
        os.fsync(archive_descriptor)
        _verify_open_temporary(
            archive_descriptor, temporary_archive, "temporary archive"
        )
        archive_digest = _sha256_descriptor(archive_descriptor)
        digest_raw = f"{archive_digest}  {destination.name}\n".encode("ascii")
        os.lseek(digest_descriptor, 0, os.SEEK_SET)
        os.ftruncate(digest_descriptor, 0)
        _write_descriptor(digest_descriptor, digest_raw)
        os.fsync(digest_descriptor)
        _verify_open_temporary(
            digest_descriptor, temporary_digest, "temporary digest"
        )
        _require_safe_destination(destination)
        _require_safe_destination(digest_file)
        _verify_open_temporary(
            archive_descriptor, temporary_archive, "temporary archive"
        )
        _verify_open_temporary(
            digest_descriptor, temporary_digest, "temporary digest"
        )
        archive_output_identity = os.fstat(archive_descriptor)
        digest_output_identity = os.fstat(digest_descriptor)
        _publish_without_overwrite(temporary_archive, destination)
        _publish_without_overwrite(temporary_digest, digest_file)
    except BaseException:
        _remove_owned_identity(digest_output_identity, digest_file)
        _remove_owned_identity(archive_output_identity, destination)
        raise
    finally:
        failed = sys.exc_info()[0] is not None
        cleanup_error = _cleanup_temporary_outputs(
            (digest_descriptor, archive_descriptor),
            (temporary_archive, temporary_digest),
        )
        if temporary_archive is not None:
            _OPEN_TEMPORARY_DESCRIPTORS.pop(_lexical_path(temporary_archive), None)
        if temporary_digest is not None:
            _OPEN_TEMPORARY_DESCRIPTORS.pop(_lexical_path(temporary_digest), None)
        if cleanup_error is not None and not failed:
            _remove_owned_identity(digest_output_identity, digest_file)
            _remove_owned_identity(archive_output_identity, destination)
            raise cleanup_error
    return LaunchReleasePackage(
        requested_archive,
        requested_digest,
        MappingProxyType(manifest),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build deterministic launch release packages")
    subparsers = parser.add_subparsers(dest="command", required=True)
    launch = subparsers.add_parser("launch-release")
    launch.add_argument("--root", type=Path, required=True)
    launch.add_argument("--destination", type=Path, required=True)
    launch.add_argument("--compose-network-audit", type=Path, required=True)
    launch.add_argument("--source-revision", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = build_launch_release(
            args.root,
            args.destination,
            compose_network_audit=args.compose_network_audit,
            source_revision=args.source_revision,
        )
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as exc:
        print(f"launch release package refused: {exc}", file=sys.stderr)
        return 2
    print(result.archive)
    print(result.digest_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
