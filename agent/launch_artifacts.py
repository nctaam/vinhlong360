from __future__ import annotations

import hashlib
import json
import math
import unicodedata
import warnings
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any


WINDOWS_INVALID_FILENAME_CHARACTERS = frozenset('<>:"/\\|?*')
WINDOWS_RESERVED_FILENAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
WINDOWS_SUPERSCRIPT_DIGITS = str.maketrans("\u00b9\u00b2\u00b3", "123")


@dataclass(frozen=True)
class LoadedArtifact:
    path: Path
    raw: bytes
    data: dict[str, Any]
    sha256: str


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


def _parse_json_object(raw: bytes, path: Path) -> dict[str, Any]:
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
    return data


def _is_windows_reserved_filename(name: str) -> bool:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        if PureWindowsPath(name).is_reserved():
            return True
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
    else:
        root = Path(release_root) if release_root is not None else Path(__file__).resolve().parent.parent
        path = root / "config" / artifact_name

    raw = path.read_bytes()
    return LoadedArtifact(
        path=path,
        raw=raw,
        data=_parse_json_object(raw, path),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
