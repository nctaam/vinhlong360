import hashlib
import os
from pathlib import Path
import subprocess
import tarfile

import pytest

from scripts.package_launch_release import (
    CANONICAL_ARTIFACTS,
    build_backend_archive,
    find_duplicate_artifacts,
    find_tracked_duplicate_artifacts,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _release_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    (root / "agent").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "agent" / "server.py").write_bytes(b"print('server')\n")
    (root / "requirements.txt").write_bytes(b"fastapi\n")
    (root / "init.sql").write_bytes(b"-- schema\n")
    return root


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_repository_has_no_duplicate_canonical_artifacts():
    assert find_tracked_duplicate_artifacts(REPO_ROOT) == []


def test_candidate_scanner_rejects_alias_symlink_and_non_file(tmp_path: Path) -> None:
    canonical = tmp_path / "config" / "launch-indexing-policy.json"
    canonical.parent.mkdir()
    canonical.write_bytes(b"{}")
    alias = tmp_path / "web-nuxt" / canonical.name
    alias.parent.mkdir()
    alias.symlink_to(canonical)
    directory = tmp_path / "config" / "ai-disclosure.json"
    directory.mkdir()

    assert find_duplicate_artifacts(
        (
            ("config/launch-indexing-policy.json", canonical),
            ("web-nuxt/launch-indexing-policy.json", alias),
            ("config/ai-disclosure.json", directory),
        )
    ) == ["config/ai-disclosure.json", "web-nuxt/launch-indexing-policy.json"]


def test_candidate_scanner_rejects_duplicate_canonical_member(tmp_path: Path) -> None:
    canonical = tmp_path / "config" / "launch-indexing-policy.json"
    canonical.parent.mkdir()
    canonical.write_bytes(b"{}")

    assert find_duplicate_artifacts(
        (
            ("config/launch-indexing-policy.json", canonical),
            ("config/launch-indexing-policy.json", canonical),
        )
    ) == ["config/launch-indexing-policy.json"]


def _git_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    for name in CANONICAL_ARTIFACTS:
        (root / "config" / name).write_bytes(b"{}")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "config"], check=True)
    return root


def test_tracked_scanner_detects_staged_duplicate(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    duplicate = root / "web-nuxt" / "launch-indexing-policy.json"
    duplicate.parent.mkdir()
    duplicate.write_bytes(b"{}")
    subprocess.run(["git", "-C", str(root), "add", "web-nuxt"], check=True)

    assert find_tracked_duplicate_artifacts(root) == [
        "web-nuxt/launch-indexing-policy.json"
    ]


def test_tracked_scanner_detects_committed_duplicate(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    duplicate = root / "web-nuxt" / "launch-indexing-policy.json"
    duplicate.parent.mkdir()
    duplicate.write_bytes(b"{}")
    subprocess.run(["git", "-C", str(root), "add", "web-nuxt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Scanner Test",
            "-c",
            "user.email=scanner@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )

    assert find_tracked_duplicate_artifacts(root) == [
        "web-nuxt/launch-indexing-policy.json"
    ]


def test_tracked_scanner_ignores_untracked_nested_worktree_noise(
    tmp_path: Path,
) -> None:
    root = _git_root(tmp_path)
    noise = root / ".claude" / "worktrees" / "task" / "config"
    noise.mkdir(parents=True)
    (noise / "launch-indexing-policy.json").write_bytes(b"{}")

    assert find_tracked_duplicate_artifacts(root) == []


def test_backend_archive_rejects_duplicate_artifacts_before_writing(tmp_path: Path):
    root = _release_source(tmp_path)
    (root / "config" / "launch-indexing-policy.json").write_text(
        "{}", encoding="utf-8"
    )
    duplicate = root / "agent" / "launch-indexing-policy.json"
    duplicate.write_text("{}", encoding="utf-8")
    destination = tmp_path / "backend.tar.gz"
    destination.write_bytes(b"previous archive")

    with pytest.raises(ValueError, match="duplicate canonical"):
        build_backend_archive(root, destination)

    assert destination.read_bytes() == b"previous archive"


def test_backend_archive_includes_root_config_unchanged(tmp_path: Path):
    root = tmp_path / "source"
    (root / "agent").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "requirements.txt").write_bytes(b"fastapi\n")
    (root / "init.sql").write_bytes(b"-- schema\n")
    route_bytes = b'{"revision":"launch-indexing-policy-v1"}\n'
    disclosure_bytes = b'{"revision":"ai-disclosure-v1"}\n'
    (root / "config" / "launch-indexing-policy.json").write_bytes(route_bytes)
    (root / "config" / "ai-disclosure.json").write_bytes(disclosure_bytes)

    archive = build_backend_archive(root, tmp_path / "backend.tar.gz")

    with tarfile.open(archive, "r:gz") as bundle:
        assert bundle.extractfile("config/launch-indexing-policy.json").read() == route_bytes
        assert bundle.extractfile("config/ai-disclosure.json").read() == disclosure_bytes


def test_backend_archive_excludes_private_runtime_and_unsafe_symlinks(tmp_path: Path):
    root = _release_source(tmp_path)
    required_bytes = b'{"required":true}\n'
    (root / "agent" / "required.json").write_bytes(required_bytes)
    (root / "agent" / "data").mkdir()
    (root / "agent" / "data" / "private.db").write_bytes(b"private database")
    (root / "agent" / "__pycache__").mkdir()
    (root / "agent" / "__pycache__" / "server.pyc").write_bytes(b"cache")
    (root / "agent" / ".pytest_cache").mkdir()
    (root / "agent" / ".pytest_cache" / "state").write_bytes(b"cache")
    (root / "agent" / "runtime.sqlite3").write_bytes(b"runtime database")
    (root / "agent" / "server.log").write_bytes(b"private log")
    (root / "agent" / "runtime.jsonl").write_bytes(b'{"private":true}\n')
    outside = tmp_path / "outside-secret.txt"
    outside.write_bytes(b"outside secret")
    (root / "agent" / "outside-link").symlink_to(outside)

    archive = build_backend_archive(root, tmp_path / "backend.tar.gz")

    with tarfile.open(archive, "r:gz") as bundle:
        names = set(bundle.getnames())
        assert bundle.extractfile("agent/required.json").read() == required_bytes
        assert "agent/data/private.db" not in names
        assert "agent/__pycache__/server.pyc" not in names
        assert "agent/.pytest_cache/state" not in names
        assert "agent/runtime.sqlite3" not in names
        assert "agent/server.log" not in names
        assert "agent/runtime.jsonl" not in names
        assert "agent/outside-link" not in names


def test_backend_archive_is_reproducible_across_source_mtime_changes(tmp_path: Path):
    root = _release_source(tmp_path)
    source_file = root / "agent" / "server.py"
    os.utime(source_file, (1_000, 1_000))
    first = build_backend_archive(root, tmp_path / "first.tar.gz")
    os.utime(source_file, (2_000, 2_000))
    second = build_backend_archive(root, tmp_path / "second.tar.gz")

    assert _sha256(first) == _sha256(second)


def test_missing_required_member_does_not_replace_destination(tmp_path: Path):
    root = _release_source(tmp_path)
    (root / "init.sql").unlink()
    destination = tmp_path / "backend.tar.gz"
    destination.write_bytes(b"previous archive")

    with pytest.raises(FileNotFoundError):
        build_backend_archive(root, destination)

    assert destination.read_bytes() == b"previous archive"
    assert list(tmp_path.glob(".backend.tar.gz.*.tmp")) == []


def test_backend_archive_destination_must_be_outside_source(tmp_path: Path):
    root = _release_source(tmp_path)
    destination = root / "backend.tar.gz"

    with pytest.raises(ValueError, match="outside source root"):
        build_backend_archive(root, destination)

    assert not destination.exists()
