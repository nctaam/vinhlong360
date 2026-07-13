from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeAlias


WINDOWS_INVALID_FILENAME_CHARACTERS = frozenset('<>:"/\\|?*')
WINDOWS_RESERVED_FILENAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
WINDOWS_SUPERSCRIPT_DIGITS = str.maketrans("\u00b9\u00b2\u00b3", "123")
ImmutableJSON: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | Mapping[str, "ImmutableJSON"]
    | tuple["ImmutableJSON", ...]
)
ImmutableJSONObject: TypeAlias = Mapping[str, ImmutableJSON]


@dataclass(frozen=True)
class LoadedArtifact:
    path: Path
    raw: bytes
    data: ImmutableJSONObject
    sha256: str

    def __post_init__(self) -> None:
        expected_sha256 = hashlib.sha256(self.raw).hexdigest()
        if self.sha256 != expected_sha256:
            raise ValueError("artifact SHA-256 does not match raw bytes")
        parsed = _parse_json_object(self.raw, self.path)
        try:
            snapshot = _freeze_json(self.data)
        except TypeError as exc:
            raise ValueError("artifact data does not match raw bytes") from exc
        if snapshot != parsed:
            raise ValueError("artifact data does not match raw bytes")
        object.__setattr__(self, "data", parsed)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"duplicate JSON key: {key}")
        parsed[key] = value
    return parsed


def _reject_non_finite_number(constant: str) -> None:
    raise ValueError(f"non-finite JSON number: {constant}")


def _parse_finite_float(literal: str) -> float:
    value = float(literal)
    if not math.isfinite(value):
        raise ValueError(f"non-finite JSON number: {literal}")
    return value


def _freeze_json(value: Any) -> ImmutableJSON:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(child) for key, child in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(child) for child in value)
    if isinstance(value, MappingProxyType):
        return MappingProxyType({key: _freeze_json(child) for key, child in value.items()})
    if type(value) is tuple:
        return tuple(_freeze_json(child) for child in value)
    if value is None or type(value) in {bool, int, float, str}:
        return value
    raise TypeError(f"unsupported parsed JSON value: {type(value).__name__}")


def _parse_json_object(raw: bytes, path: Path) -> ImmutableJSONObject:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"artifact {path} is not valid UTF-8") from exc

    try:
        data = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_number,
            parse_float=_parse_finite_float,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"artifact {path} is not valid JSON: {exc.msg}") from exc

    if type(data) is not dict:
        raise ValueError(f"artifact {path} must contain a JSON object")
    frozen = _freeze_json(data)
    if not isinstance(frozen, Mapping):
        raise AssertionError("JSON object freeze did not produce a mapping")
    return frozen


def _is_windows_reserved_filename(name: str) -> bool:
    reserved_stem = (
        name.split(".", 1)[0]
        .rstrip(" .")
        .translate(WINDOWS_SUPERSCRIPT_DIGITS)
        .upper()
    )
    return reserved_stem in WINDOWS_RESERVED_FILENAMES


def _validate_artifact_name(name: object) -> Path:
    if type(name) is not str:
        raise ValueError("artifact name must be a single valid filename")
    artifact_name = Path(name)
    if (
        name in {"", ".", ".."}
        or artifact_name.is_absolute()
        or artifact_name.name != name
        or name.endswith((".", " "))
        or any(
            character in WINDOWS_INVALID_FILENAME_CHARACTERS
            or unicodedata.category(character) == "Cc"
            for character in name
        )
        or _is_windows_reserved_filename(name)
    ):
        raise ValueError("artifact name must be a single valid filename")
    return artifact_name


def _file_identity(file_stat: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        file_stat.st_dev,
        file_stat.st_ino,
        stat.S_IFMT(file_stat.st_mode),
        file_stat.st_size,
        file_stat.st_mtime_ns,
    )


def _lstat_regular_file(path: Path) -> os.stat_result:
    file_stat = os.lstat(path)
    if stat.S_ISLNK(file_stat.st_mode):
        raise ValueError(f"artifact path must not be a symlink: {path}")
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError(f"artifact path must be a regular file: {path}")
    return file_stat


def _lstat_directory(path: Path, label: str) -> os.stat_result:
    directory_stat = os.lstat(path)
    if stat.S_ISLNK(directory_stat.st_mode):
        raise ValueError(f"artifact {label} must not be a symlink: {path}")
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ValueError(f"artifact {label} must be a directory: {path}")
    if path.resolve(strict=True) != path:
        raise ValueError(f"artifact {label} must not be a symlink or reparse point: {path}")
    return directory_stat


def _regular_file_stat_at(name: str, directory_fd: int, display_path: Path) -> os.stat_result:
    file_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if stat.S_ISLNK(file_stat.st_mode):
        raise ValueError(f"artifact path must not be a symlink: {display_path}")
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError(f"artifact path must be a regular file: {display_path}")
    return file_stat


def _read_confined_file(
    open_target: str | Path,
    display_path: Path,
    initial_stat: os.stat_result,
    *,
    directory_fd: int | None = None,
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        if directory_fd is None:
            descriptor = os.open(open_target, flags)
        else:
            descriptor = os.open(open_target, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise ValueError(
            f"artifact path identity changed before open: {display_path}"
        ) from exc

    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"artifact path must be a regular file: {display_path}")
        if _file_identity(initial_stat) != _file_identity(opened_stat):
            raise ValueError(f"artifact path identity changed before open: {display_path}")

        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read()

        opened_after = os.fstat(descriptor)
        try:
            if directory_fd is None:
                path_after = os.lstat(display_path)
            else:
                path_after = os.stat(
                    open_target,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
        except FileNotFoundError as exc:
            raise ValueError(
                f"artifact path identity changed during read: {display_path}"
            ) from exc
        if (
            stat.S_ISLNK(path_after.st_mode)
            or not stat.S_ISREG(path_after.st_mode)
            or _file_identity(initial_stat) != _file_identity(opened_after)
            or _file_identity(initial_stat) != _file_identity(path_after)
        ):
            raise ValueError(f"artifact path identity changed during read: {display_path}")
        return raw
    finally:
        os.close(descriptor)


def _directory_fd_supported() -> bool:
    return (
        hasattr(os, "O_DIRECTORY")
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
    )


def _open_directory(path: Path, initial_stat: os.stat_result) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"artifact config directory identity changed: {path}") from exc
    try:
        opened_stat = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(opened_stat.st_mode)
            or _file_identity(initial_stat) != _file_identity(opened_stat)
        ):
            raise ValueError(f"artifact config directory identity changed: {path}")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _recheck_directory(path: Path, initial_stat: os.stat_result, label: str) -> None:
    try:
        current_stat = os.lstat(path)
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise ValueError(f"artifact {label} identity changed: {path}") from exc
    if (
        stat.S_ISLNK(current_stat.st_mode)
        or not stat.S_ISDIR(current_stat.st_mode)
        or resolved != path
        or _file_identity(initial_stat) != _file_identity(current_stat)
    ):
        raise ValueError(f"artifact {label} identity changed or became a symlink: {path}")


def _read_production_artifact(root: Path, artifact_name: Path) -> tuple[Path, bytes]:
    resolved_root = root.resolve(strict=True)
    root_stat = _lstat_directory(resolved_root, "release root")

    config = resolved_root / "config"
    config_stat = _lstat_directory(config, "config directory")

    path = config / artifact_name
    config_fd: int | None = None
    try:
        if _directory_fd_supported():
            config_fd = _open_directory(config, config_stat)
            open_target = artifact_name.name
            initial_stat = _regular_file_stat_at(open_target, config_fd, path)
            raw = _read_confined_file(
                open_target,
                path,
                initial_stat,
                directory_fd=config_fd,
            )
        else:
            initial_stat = _lstat_regular_file(path)
            resolved_path = path.resolve(strict=True)
            if not resolved_path.is_relative_to(resolved_root):
                raise ValueError(f"artifact path escapes the release root: {path}")
            raw = _read_confined_file(resolved_path, path, initial_stat)

        _recheck_directory(config, config_stat, "config directory")
        _recheck_directory(resolved_root, root_stat, "release root")
        return path, raw
    finally:
        if config_fd is not None:
            os.close(config_fd)


def load_artifact(
    name: str,
    *,
    release_root: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> LoadedArtifact:
    if release_root is not None and fixture_path is not None:
        raise ValueError("release_root and fixture_path are mutually exclusive")

    artifact_name = _validate_artifact_name(name)
    if fixture_path is not None:
        path = Path(fixture_path)
        initial_stat = _lstat_regular_file(path)
        raw = _read_confined_file(path, path, initial_stat)
    else:
        root = Path(release_root) if release_root is not None else Path(__file__).resolve().parent.parent
        path, raw = _read_production_artifact(root, artifact_name)

    return LoadedArtifact(
        path=path,
        raw=raw,
        data=_parse_json_object(raw, path),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
