from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs, unquote, urlsplit

IDENTITY_KEYS = (
    "database",
    "server_addr",
    "server_port",
    "server_version_num",
)


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


def write_exclusive(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_json_bytes(payload))
