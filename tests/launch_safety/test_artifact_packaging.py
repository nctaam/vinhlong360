from pathlib import Path
import tarfile

from scripts.package_launch_release import (
    CANONICAL_ARTIFACTS,
    build_backend_archive,
    find_duplicate_artifacts,
)


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
