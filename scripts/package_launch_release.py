import gzip
import os
import tarfile
import tempfile
from pathlib import Path


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
