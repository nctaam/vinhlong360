import hashlib
import os
from pathlib import Path
import tarfile

import pytest

from scripts.package_launch_release import (
    CANONICAL_ARTIFACTS,
    build_backend_archive,
    find_duplicate_artifacts,
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
    assert find_duplicate_artifacts(REPO_ROOT) == []


def test_canonical_artifacts_may_exist_only_under_root_config(tmp_path: Path):
    root = tmp_path
    (root / "config").mkdir()
    (root / "web-nuxt").mkdir()
    for name in CANONICAL_ARTIFACTS:
        (root / "config" / name).write_text("{}", encoding="utf-8")
    (root / "web-nuxt" / "launch-indexing-policy.json").write_text(
        "{}", encoding="utf-8"
    )

    assert find_duplicate_artifacts(root) == [
        root / "web-nuxt" / "launch-indexing-policy.json",
    ]


def test_duplicate_detection_uses_lexical_location_for_symlink_alias(tmp_path: Path):
    root = tmp_path
    (root / "config").mkdir()
    (root / "web-nuxt").mkdir()
    canonical = root / "config" / "launch-indexing-policy.json"
    canonical.write_text("{}", encoding="utf-8")
    alias = root / "web-nuxt" / "launch-indexing-policy.json"
    alias.symlink_to(canonical)

    assert find_duplicate_artifacts(root) == [alias]


def test_canonical_artifact_must_be_a_regular_non_symlink_file(tmp_path: Path):
    root = tmp_path
    (root / "config").mkdir()
    target = root / "policy-target.json"
    target.write_text("{}", encoding="utf-8")
    canonical = root / "config" / "launch-indexing-policy.json"
    canonical.symlink_to(target)

    assert find_duplicate_artifacts(root) == [canonical]


def test_backend_archive_rejects_duplicate_artifacts_before_writing(tmp_path: Path):
    root = _release_source(tmp_path)
    (root / "config" / "launch-indexing-policy.json").write_text(
        "{}", encoding="utf-8"
    )
    (root / "web-nuxt").mkdir()
    (root / "web-nuxt" / "launch-indexing-policy.json").write_text(
        "{}", encoding="utf-8"
    )
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
