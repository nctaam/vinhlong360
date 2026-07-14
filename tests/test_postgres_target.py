from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import postgres_target


def test_canonical_json_bytes_are_sorted_compact_utf8_and_newline_terminated() -> None:
    value = {"z": 1, "a": "V\u0129nh Long"}

    payload = postgres_target.canonical_json_bytes(value)

    assert payload == '{"a":"V\u0129nh Long","z":1}\n'.encode()


def test_sha256_helpers_hash_bytes_and_streamed_file(tmp_path: Path) -> None:
    payload = b"vinhlong360\n"
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    assert postgres_target.sha256_bytes(payload) == expected
    assert postgres_target.sha256_file(path) == expected


def test_resolve_database_url_requires_named_explicit_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://fallback:secret@db/prod")
    monkeypatch.delenv("VL360_BACKUP_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="VL360_BACKUP_DATABASE_URL"):
        postgres_target.resolve_database_url("VL360_BACKUP_DATABASE_URL")


def test_resolve_database_url_rejects_default_database_url_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@db/prod")

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        postgres_target.resolve_database_url("DATABASE_URL")


@pytest.mark.parametrize(
    "database_url",
    ["", "sqlite:///x.db", "postgres://host/db", "POSTGRESQL://host/db"],
)
def test_resolve_database_url_rejects_non_postgresql_urls(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    monkeypatch.setenv("VL360_BACKUP_DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        postgres_target.resolve_database_url("VL360_BACKUP_DATABASE_URL")


@pytest.mark.parametrize(
    "database_url",
    ["postgresql:///database", "postgresql://host", "postgresql://host/"],
)
def test_resolve_database_url_requires_host_and_database(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    monkeypatch.setenv("VL360_BACKUP_DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        postgres_target.resolve_database_url("VL360_BACKUP_DATABASE_URL")


def test_resolve_database_url_accepts_explicit_postgresql_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "postgresql://user:secret@db.example:5433/vl360?sslmode=require"
    monkeypatch.setenv("VL360_BACKUP_DATABASE_URL", database_url)

    assert (
        postgres_target.resolve_database_url("VL360_BACKUP_DATABASE_URL")
        == database_url
    )


def test_pg_cli_connection_keeps_password_out_of_argv() -> None:
    secret = "s3cr%2Fet"
    args, environment = postgres_target.pg_cli_connection(
        f"postgresql://backup%20user:{secret}@db.example/vl360?sslmode=verify-full"
    )

    assert args == [
        "--host",
        "db.example",
        "--port",
        "5432",
        "--username",
        "backup user",
        "--dbname",
        "vl360",
    ]
    assert "s3cr/et" not in " ".join(args)
    assert environment == {"PGPASSWORD": "s3cr/et", "PGSSLMODE": "verify-full"}


class _Cursor:
    def __init__(self) -> None:
        self.query = ""

    def execute(self, query: str) -> None:
        self.query = query

    def fetchone(self) -> tuple[str, str, int, int]:
        return ("vl360", "10.0.0.8", 5432, 160004)


def test_read_target_identity_reads_only_server_identity() -> None:
    cursor = _Cursor()

    identity = postgres_target.read_target_identity(cursor)

    assert "current_database()" in cursor.query
    assert identity == {
        "database": "vl360",
        "server_addr": "10.0.0.8",
        "server_port": 5432,
        "server_version_num": 160004,
    }


def test_target_fingerprint_ignores_credentials_and_is_sha256() -> None:
    identity = {
        "database": "vl360",
        "server_addr": "10.0.0.8",
        "server_port": 5432,
        "server_version_num": 160004,
        "password": "must-not-be-hashed",
    }

    fingerprint = postgres_target.target_fingerprint(identity)

    assert len(fingerprint) == 64
    expected_identity = {
        key: identity[key]
        for key in (
            "database",
            "server_addr",
            "server_port",
            "server_version_num",
        )
    }
    assert fingerprint == hashlib.sha256(
        postgres_target.canonical_json_bytes(expected_identity)
    ).hexdigest()
    assert "must-not-be-hashed" not in fingerprint


def test_write_exclusive_writes_canonical_json_and_refuses_overwrite(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "manifest.json"

    result = postgres_target.write_exclusive(path, {"z": 1, "a": "ok"})

    assert result == path
    assert path.read_bytes() == b'{"a":"ok","z":1}\n'
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        postgres_target.write_exclusive(path, {"replacement": True})
    assert path.read_bytes() == original
    assert json.loads(original) == {"a": "ok", "z": 1}


def test_write_exclusive_preflights_serialization_before_creating_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "manifest.json"

    with pytest.raises(TypeError):
        postgres_target.write_exclusive(path, {"bad": object()})

    assert not path.exists()


def test_write_exclusive_cleans_up_its_partial_file_after_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    original_open = Path.open

    class PartialWriteFailure:
        def __init__(self, stream) -> None:
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            self.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def write(self, payload: bytes) -> None:
            self.stream.write(payload[:1])
            self.stream.flush()
            raise OSError("simulated partial write failure")

        def flush(self) -> None:
            self.stream.flush()

        def close(self) -> None:
            self.stream.close()

    def open_with_partial_failure(
        destination: Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ):
        stream = original_open(destination, mode, *args, **kwargs)
        if destination == path and mode == "xb":
            return PartialWriteFailure(stream)
        return stream

    monkeypatch.setattr(Path, "open", open_with_partial_failure)

    with pytest.raises(OSError, match="simulated partial write failure"):
        postgres_target.write_exclusive(path, {"valid": True})

    assert not path.exists()


def test_write_exclusive_detects_replacement_without_unlinking_foreign_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    foreign = b"other-process"
    original_open = Path.open

    class ReplaceOnClose:
        def __init__(self, stream) -> None:
            self.stream = stream
            self.replaced = False

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            self.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def write(self, payload: bytes) -> int:
            return self.stream.write(payload)

        def flush(self) -> None:
            self.stream.flush()

        def close(self) -> None:
            if self.replaced:
                return
            self.stream.close()
            path.unlink()
            path.write_bytes(foreign)
            self.replaced = True

    def open_with_replacement(
        destination: Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ):
        stream = original_open(destination, mode, *args, **kwargs)
        if destination == path and mode == "xb":
            return ReplaceOnClose(stream)
        return stream

    monkeypatch.setattr(Path, "open", open_with_replacement)

    try:
        with pytest.raises(RuntimeError, match="changed"):
            postgres_target.write_exclusive(path, {"valid": True})
    finally:
        assert path.read_bytes() == foreign


def test_write_exclusive_failure_does_not_unlink_foreign_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    foreign = b"other-process"
    original_open = Path.open

    class ReplaceThenFail:
        def __init__(self, stream) -> None:
            self.stream = stream

        def fileno(self) -> int:
            return self.stream.fileno()

        def write(self, payload: bytes) -> None:
            self.stream.write(payload[:1])
            self.stream.flush()
            self.stream.close()
            path.unlink()
            path.write_bytes(foreign)
            raise OSError("simulated replacement race")

        def flush(self) -> None:
            self.stream.flush()

        def close(self) -> None:
            self.stream.close()

    def open_with_replacement_failure(
        destination: Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ):
        stream = original_open(destination, mode, *args, **kwargs)
        if destination == path and mode == "xb":
            return ReplaceThenFail(stream)
        return stream

    monkeypatch.setattr(Path, "open", open_with_replacement_failure)

    try:
        with pytest.raises(OSError, match="simulated replacement race"):
            postgres_target.write_exclusive(path, {"valid": True})
    finally:
        assert path.read_bytes() == foreign
