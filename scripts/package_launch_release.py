import argparse
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import os
import re
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
    "non_nginx_services_unpublished",
    "no_external_or_host_network",
    "nginx_exclusive_public_endpoints",
    "nginx_depends_on_healthy_nuxt_only",
    "nuxt_backend_independent_readiness",
    "nuxt_bind_host",
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


@dataclass(frozen=True)
class LaunchReleasePackage:
    archive: Path
    digest_file: Path
    manifest: Mapping[str, object]


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
        accepted_directories: list[str] = []
        for dirname in sorted(dirnames):
            path = current / dirname
            relative = relative_current / dirname
            excluded = filter_agent_runtime and _excluded_agent_path(
                relative, is_directory=True
            )
            if path.is_symlink() or not _is_within(path, release_root) or excluded:
                continue
            accepted_directories.append(dirname)
            payload.append((path, (Path(arcroot) / relative).as_posix()))
        dirnames[:] = accepted_directories
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
    path = _lexical_path(path)
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


def _json_object(path: Path, label: str) -> tuple[dict[str, object], bytes]:
    raw = path.read_bytes()

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


def _validated_canonical_artifacts(root: Path) -> dict[str, object]:
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
        _require_safe_source(root, path, directory=False)
        artifact, raw = _json_object(path, f"canonical artifact {relative}")
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
    route_digest = _sha256_bytes(str(route["sha256"]).encode("ascii"))
    disclosure_digest = _sha256_bytes(str(disclosure["sha256"]).encode("ascii"))
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
) -> tuple[Path, bytes]:
    path = root / Path(_READINESS_PATH)
    _require_safe_source(root, path, directory=False)
    manifest, raw = _json_object(path, "launch readiness manifest")
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
    if manifest["policy_route_classes"] != list(_READINESS_ROUTE_CLASSES):
        raise ValueError("launch readiness route classes mismatch")
    if manifest["compiled_cache_rules"] != []:
        raise ValueError("launch readiness compiled cache rules are unsafe")
    if manifest["public_prerender_files"] != []:
        raise ValueError("launch readiness contains policy-bearing prerender files")
    worker = manifest["service_worker"]
    if not isinstance(worker, dict):
        raise ValueError("launch readiness service worker evidence is invalid")
    _exact_keys(worker, {"version", "rule_digest", "cache_purge"}, "service worker")
    if worker["version"] != "vl360-launch-v1":
        raise ValueError("launch readiness service worker version mismatch")
    worker_path = root / "web-nuxt" / ".output" / "public" / "sw.js"
    _require_safe_source(root, worker_path, directory=False)
    if _require_sha256(worker["rule_digest"], "service worker digest") != _sha256_bytes(
        worker_path.read_bytes()
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
    return path, raw


def _normalized_source_digest(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"compose audit source is not UTF-8: {path}") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return _sha256_bytes(normalized)


def _validate_network_audit(root: Path, path: Path) -> bytes:
    path = _lexical_path(path if path.is_absolute() else root / path)
    _require_safe_source(root, path, directory=False)
    audit, raw = _json_object(path, "compose network audit")
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
    if audit["revision"] != "compose-network-audit-v1":
        raise ValueError("compose network audit revision mismatch")
    expected_checks = sorted(_AUDIT_CHECK_NAMES)
    if audit["check_names"] != expected_checks:
        raise ValueError("compose network audit check inventory mismatch")
    if audit["checks"] != {name: "passed" for name in expected_checks}:
        raise ValueError("compose network audit did not pass every check")
    published_ports = audit["published_ports"]
    if not isinstance(published_ports, list):
        raise ValueError("compose network audit published ports are invalid")
    for endpoint in published_ports:
        if not isinstance(endpoint, dict) or set(endpoint) != {
            "service", "host_ip", "published", "target", "protocol"
        }:
            raise ValueError("compose network audit endpoint shape is invalid")
        if (
            endpoint["service"] != "nginx"
            or endpoint["published"] not in {80, 443}
            or endpoint["target"] != endpoint["published"]
            or endpoint["protocol"] != "tcp"
        ):
            raise ValueError("compose network audit exposes a non-nginx endpoint")
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
    if audit["source_digest_kind"] != "sha256-utf8-lf-v1":
        raise ValueError("compose network audit source digest kind mismatch")
    sources = audit["sources"]
    if not isinstance(sources, list):
        raise ValueError("compose network audit sources are invalid")
    expected_sources = []
    for relative in _AUDIT_SOURCE_PATHS:
        source = root / relative
        _require_safe_source(root, source, directory=False)
        expected_sources.append(
            {"path": relative, "sha256": _normalized_source_digest(source)}
        )
    if sources != expected_sources:
        raise ValueError("compose network audit sources are stale or incomplete")
    return raw


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


def _regular_member_map(payload: list[tuple[Path, str]]) -> dict[str, object]:
    members: dict[str, object] = {}
    for source, arcname in payload:
        if source.is_file():
            raw = source.read_bytes()
            members[arcname] = {"sha256": _sha256_bytes(raw), "size": len(raw)}
    return members


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def build_launch_release_manifest(
    root: Path,
    payload: list[tuple[Path, str]],
    source_revision: str,
    *,
    compose_network_audit: Path,
) -> dict[str, object]:
    if (
        not isinstance(source_revision, str)
        or not source_revision
        or source_revision.strip() != source_revision
        or any(character in source_revision for character in "\r\n\0")
    ):
        raise ValueError("source revision must be a non-empty canonical string")
    root = _lexical_path(root)
    canonical_artifacts = _validated_canonical_artifacts(root)
    _readiness_path, readiness_raw = _validate_readiness_manifest(
        root, source_revision, canonical_artifacts
    )
    audit_raw = _validate_network_audit(root, compose_network_audit)
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
        "members": _regular_member_map(payload),
    }


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


def write_deterministic_tar_gz(
    destination: Path,
    payload: list[tuple[Path, str]],
    embedded_files: Mapping[str, bytes],
) -> None:
    entries: list[tuple[str, Path | None, bytes | None, bool]] = []
    for source, arcname in payload:
        entries.append((arcname, source, None, source.is_dir()))
    for arcname, raw in embedded_files.items():
        entries.append((arcname, None, raw, False))
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
                for arcname, source, embedded, directory in sorted(entries):
                    if directory:
                        archive.addfile(_launch_tar_info(arcname, directory=True))
                        continue
                    raw = embedded if embedded is not None else source.read_bytes()
                    archive.addfile(
                        _launch_tar_info(arcname, size=len(raw), directory=False),
                        fileobj=io.BytesIO(raw),
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
    os.link(temporary, destination, follow_symlinks=False)


def build_launch_release(
    root: Path,
    destination: Path,
    *,
    compose_network_audit: Path,
    source_revision: str,
) -> LaunchReleasePackage:
    requested_archive = Path(destination)
    requested_digest = requested_archive.with_name(requested_archive.name + ".sha256")
    root = _lexical_path(root)
    destination = _lexical_path(destination)
    digest_file = destination.with_name(destination.name + ".sha256")
    _require_safe_destination(destination)
    _require_safe_destination(digest_file)

    payload = collect_launch_release_payload(root, compose_network_audit)
    manifest = build_launch_release_manifest(
        root,
        payload,
        source_revision,
        compose_network_audit=(
            compose_network_audit
            if Path(compose_network_audit).is_absolute()
            else root / compose_network_audit
        ),
    )
    manifest_raw = _canonical_json_bytes(manifest)
    archive_descriptor, archive_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(archive_descriptor)
    digest_descriptor, digest_name = tempfile.mkstemp(
        prefix=f".{digest_file.name}.", suffix=".tmp", dir=digest_file.parent
    )
    os.close(digest_descriptor)
    temporary_archive = Path(archive_name)
    temporary_digest = Path(digest_name)
    archive_published = False
    digest_published = False
    try:
        write_deterministic_tar_gz(
            temporary_archive,
            payload,
            {"launch-release-manifest.json": manifest_raw},
        )
        archive_digest = _sha256_bytes(temporary_archive.read_bytes())
        temporary_digest.write_text(
            f"{archive_digest}  {destination.name}\n", encoding="ascii", newline="\n"
        )
        _require_safe_destination(destination)
        _require_safe_destination(digest_file)
        _publish_without_overwrite(temporary_archive, destination)
        archive_published = True
        _publish_without_overwrite(temporary_digest, digest_file)
        digest_published = True
    except BaseException:
        if digest_published:
            digest_file.unlink(missing_ok=True)
        if archive_published:
            destination.unlink(missing_ok=True)
        raise
    finally:
        temporary_archive.unlink(missing_ok=True)
        temporary_digest.unlink(missing_ok=True)
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
