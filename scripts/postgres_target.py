from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs, unquote, urlsplit

IDENTITY_KEYS = (
    "database",
    "server_addr",
    "server_port",
    "server_version_num",
)
_PENDING_WRITE_ATTEMPTS = 8


def canonical_json_bytes(value: object) -> bytes:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{payload}\n".encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_database_url(environment_name: str) -> str:
    if not environment_name or environment_name == "DATABASE_URL":
        raise RuntimeError(
            "A named PostgreSQL environment variable other than DATABASE_URL is required"
        )

    database_url = os.environ.get(environment_name, "")
    try:
        parsed = urlsplit(database_url)
    except ValueError:
        parsed = None

    if (
        parsed is None
        or not database_url.startswith("postgresql://")
        or parsed.scheme != "postgresql"
        or not parsed.hostname
        or not unquote(parsed.path.lstrip("/"))
    ):
        raise RuntimeError(
            f"Environment variable {environment_name} must contain an explicit PostgreSQL URL"
        )
    return database_url


def pg_cli_connection(database_url: str) -> tuple[list[str], dict[str, str]]:
    parsed = urlsplit(database_url)
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise RuntimeError("PostgreSQL URL has an invalid port") from exc

    args = [
        "--host",
        parsed.hostname or "",
        "--port",
        str(port),
        "--username",
        unquote(parsed.username or ""),
        "--dbname",
        unquote(parsed.path.lstrip("/")),
    ]
    environment: dict[str, str] = {}
    if parsed.password is not None:
        environment["PGPASSWORD"] = unquote(parsed.password)
    sslmode = parse_qs(parsed.query).get("sslmode")
    if sslmode:
        environment["PGSSLMODE"] = sslmode[-1]
    return args, environment


def read_target_identity(cursor) -> dict[str, object]:
    cursor.execute(
        """
        SELECT
            current_database(),
            inet_server_addr()::text,
            inet_server_port(),
            current_setting('server_version_num')::int
        """
    )
    database, server_addr, server_port, server_version_num = cursor.fetchone()
    return {
        "database": database,
        "server_addr": server_addr,
        "server_port": server_port,
        "server_version_num": server_version_num,
    }


def target_fingerprint(identity: Mapping[str, object]) -> str:
    canonical_identity = {key: identity[key] for key in IDENTITY_KEYS}
    return sha256_bytes(canonical_json_bytes(canonical_identity))


def _file_identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(metadata, "st_reparse_tag", 0)) or bool(
        attributes & reparse_flag
    )


def _lstat_best_effort(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except OSError:
        return None


def _metadata_matches_owned_file(
    metadata: os.stat_result, identity: tuple[int, int]
) -> bool:
    return (
        not stat.S_ISLNK(metadata.st_mode)
        and not _is_reparse_point(metadata)
        and _file_identity(metadata) == identity
    )


def _path_matches_owned_file(path: Path, identity: tuple[int, int]) -> bool:
    metadata = _lstat_best_effort(path)
    return metadata is not None and _metadata_matches_owned_file(metadata, identity)


def _close_best_effort(stream) -> None:
    try:
        stream.close()
    except BaseException:
        return


def _open_pending_stream(path: Path):
    for _attempt in range(_PENDING_WRITE_ATTEMPTS):
        pending = path.with_name(f".pending-write-{secrets.token_hex(16)}")
        try:
            return pending, pending.open("xb")
        except FileExistsError:
            continue
    raise RuntimeError("unable to allocate exclusive pending write path")


def write_exclusive(path: Path, payload: object) -> Path:
    canonical_payload = canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending, stream = _open_pending_stream(path)
    try:
        identity = _file_identity(os.fstat(stream.fileno()))
        stream.write(canonical_payload)
        stream.flush()
        stream.close()
    except BaseException:
        _close_best_effort(stream)
        raise
    if not _path_matches_owned_file(pending, identity):
        raise RuntimeError("exclusive write staging path changed before publish")
    os.link(pending, path, follow_symlinks=False)
    if not _path_matches_owned_file(path, identity):
        raise RuntimeError("exclusive write path changed before verification")
    # A portable conditional unlink is unavailable; retaining staging avoids races.
    return path
