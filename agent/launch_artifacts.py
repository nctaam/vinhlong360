from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"artifact {path} is not valid JSON: {exc.msg}") from exc

    if type(data) is not dict:
        raise ValueError(f"artifact {path} must contain a JSON object")
    return data


def load_artifact(
    name: str,
    *,
    release_root: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> LoadedArtifact:
    if release_root is not None and fixture_path is not None:
        raise ValueError("release_root and fixture_path are mutually exclusive")

    if fixture_path is not None:
        path = Path(fixture_path)
    else:
        if type(name) is not str:
            raise ValueError("artifact name must be a single filename")
        artifact_name = Path(name)
        if (
            name in {"", ".", ".."}
            or artifact_name.is_absolute()
            or artifact_name.name != name
        ):
            raise ValueError("artifact name must be a single filename")
        root = Path(release_root) if release_root is not None else Path(__file__).resolve().parent.parent
        path = root / "config" / artifact_name

    raw = path.read_bytes()
    return LoadedArtifact(
        path=path,
        raw=raw,
        data=_parse_json_object(raw, path),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
