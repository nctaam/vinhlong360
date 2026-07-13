from pathlib import Path
import tarfile


CANONICAL_ARTIFACTS = (
    "launch-indexing-policy.json",
    "ai-disclosure.json",
)


def find_duplicate_artifacts(root: Path) -> list[Path]:
    canonical = {(root / "config" / name).resolve() for name in CANONICAL_ARTIFACTS}
    return sorted(
        path
        for name in CANONICAL_ARTIFACTS
        for path in root.rglob(name)
        if path.resolve() not in canonical
    )


def build_backend_archive(root: Path, destination: Path) -> Path:
    members = ["agent", "requirements.txt", "init.sql", "config"]
    if (root / "web/data.json").exists():
        members.append("web/data.json")
    with tarfile.open(destination, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for member in members:
            source = root / member
            if not source.exists():
                raise FileNotFoundError(source)
            archive.add(source, arcname=member, recursive=True)
    return destination
