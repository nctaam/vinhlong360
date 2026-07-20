#!/usr/bin/env python3
"""Remove only the three reviewed Nuxt runtime/cache trees."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import time
from typing import Any, Mapping


EXACT_PURGE_PATHS = ["web-nuxt/.output", "web-nuxt/.nuxt", "web-nuxt/.cache"]
MINIMUM_PROTECTED_PATHS = {"agent/data", "agent/data/sitemap-bundles"}


def _load_policy(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("cache purge policy must be a real file")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("cache purge policy is not valid JSON") from exc
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise ValueError("cache purge policy schema mismatch")
    if policy.get("required_paths") != EXACT_PURGE_PATHS:
        raise ValueError("cache purge policy must contain only the reviewed runtime paths")
    protected = policy.get("protected_paths")
    if not isinstance(protected, list) or not MINIMUM_PROTECTED_PATHS <= set(protected):
        raise ValueError("cache purge protected path declaration is incomplete")
    for flag in ("reject_absolute_paths", "reject_parent_segments", "reject_symlinks"):
        if policy.get(flag) is not True:
            raise ValueError(f"cache purge policy must enable {flag}")
    return policy


def _validate_relative(relative: str, protected_paths: set[str]) -> PurePosixPath:
    if not isinstance(relative, str) or not relative:
        raise ValueError("cache purge path must be a non-empty string")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe cache purge path: {relative}")
    normalized = path.as_posix()
    for protected in protected_paths:
        if normalized == protected or normalized.startswith(protected + "/"):
            raise ValueError(f"cache purge path is protected: {relative}")
        if protected.startswith(normalized + "/"):
            raise ValueError(f"cache purge path contains a protected tree: {relative}")
    return path


def _assert_no_symlink(root: Path, relative: PurePosixPath) -> Path:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"cache purge path contains symlink: {relative.as_posix()}")
    return current


def purge_runtime(release_root: Path, policy_path: Path) -> dict[str, Any]:
    """Purge exact reviewed paths and return deterministic evidence."""
    started = time.monotonic()
    root = Path(release_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("release root must be a real directory")
    root = root.resolve(strict=True)
    policy = _load_policy(Path(policy_path))
    protected_paths = set(policy["protected_paths"])
    evidence_paths: list[dict[str, str]] = []
    for raw_relative in policy["required_paths"]:
        relative = _validate_relative(raw_relative, protected_paths)
        target = _assert_no_symlink(root, relative)
        try:
            target.resolve(strict=False).relative_to(root)
        except ValueError as exc:
            raise ValueError(f"cache purge path escapes release root: {raw_relative}") from exc
        if not target.exists():
            evidence_paths.append({"path": raw_relative, "status": "absent"})
            continue
        if not target.is_dir():
            raise ValueError(f"cache purge target is not a directory: {raw_relative}")
        shutil.rmtree(target)
        evidence_paths.append({"path": raw_relative, "status": "removed"})
    return {
        "schema_version": 1,
        "paths": evidence_paths,
        "protected_paths": sorted(protected_paths),
        "stage3_claim": False,
        "live_sla_proven": False,
        "observed_local_elapsed_seconds": round(time.monotonic() - started, 6),
    }


def _write_evidence(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError("refusing to replace a symlink evidence path")
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
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--readiness-manifest", type=Path)
    parser.add_argument("--evidence", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = purge_runtime(args.release_root, args.policy)
        if args.evidence is not None:
            _write_evidence(args.evidence, evidence)
    except (OSError, ValueError) as exc:
        print(f"launch runtime purge refused: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
