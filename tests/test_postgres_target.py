from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import BinaryIO, Callable

import pytest

from scripts import postgres_target


class _StreamProxy:
    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream

    def fileno(self) -> int:
        return self.stream.fileno()

    def write(self, payload: bytes) -> int:
        return self.stream.write(payload)

    def flush(self) -> None:
        self.stream.flush()

    def close(self) -> None:
        self.stream.close()


class _FailingStream(_StreamProxy):
    def __init__(self, stream: BinaryIO, failure_point: str) -> None:
        super().__init__(stream)
        self.failure_point = failure_point

    def write(self, payload: bytes) -> int:
        if self.failure_point == "write":
            self.stream.write(payload[:1])
            self.stream.flush()
            raise OSError("simulated write failure")
        return self.stream.write(payload)

    def flush(self) -> None:
        self.stream.flush()
        if self.failure_point == "flush":
            raise OSError("simulated flush failure")

    def close(self) -> None:
        self.stream.close()
        if self.failure_point == "close":
            raise OSError("simulated close failure")


class _ReplacePendingOnClose(_StreamProxy):
    def __init__(self, stream: BinaryIO, pending: Path, foreign_source: Path) -> None:
        super().__init__(stream)
        self.pending = pending
        self.foreign_source = foreign_source
        self.replaced = False

    def close(self) -> None:
        if self.replaced:
            return
        self.stream.close()
        postgres_target.os.replace(self.foreign_source, self.pending)
        self.replaced = True


def _patch_pending_stream(
    monkeypatch: pytest.MonkeyPatch,
    final_path: Path,
    factory: Callable[[BinaryIO, Path], object],
) -> None:
    original_open = Path.open

    def open_wrapped(
        destination: Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ):
        stream = original_open(destination, mode, *args, **kwargs)
        if (
            destination.parent == final_path.parent
            and destination.name.startswith(".pending-write-")
            and mode == "xb"
        ):
            return factory(stream, destination)
        return stream

    monkeypatch.setattr(Path, "open", open_wrapped)


def _assert_pending_name(pending: Path, final_path: Path) -> None:
    assert pending.parent == final_path.parent
    assert pending.name != final_path.name
    assert re.fullmatch(r"\.pending-write-[0-9a-f]{32}", pending.name)


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


def test_write_exclusive_fstat_failure_never_creates_requested_final(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"

    def fail_fstat(_descriptor: int):
        raise OSError("simulated fstat failure")

    monkeypatch.setattr(postgres_target.os, "fstat", fail_fstat)

    with pytest.raises(OSError, match="simulated fstat failure"):
        postgres_target.write_exclusive(path, {"valid": True})

    assert not path.exists()
    pending = list(path.parent.glob(".pending-write-*"))
    assert len(pending) == 1
    _assert_pending_name(pending[0], path)


def test_write_exclusive_publish_failure_leaves_final_absent_and_staging_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"

    def fail_link(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated publish failure")

    monkeypatch.setattr(postgres_target.os, "link", fail_link)

    with pytest.raises(OSError, match="simulated publish failure"):
        postgres_target.write_exclusive(path, {"valid": True})

    assert not path.exists()
    pending = list(path.parent.glob(".pending-write-*"))
    assert len(pending) == 1
    _assert_pending_name(pending[0], path)
    assert pending[0].read_bytes() == b'{"valid":true}\n'


@pytest.mark.parametrize("failure_point", ["write", "flush", "close"])
def test_write_exclusive_stream_failure_never_creates_requested_final(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    _patch_pending_stream(
        monkeypatch,
        path,
        lambda stream, _pending: _FailingStream(stream, failure_point),
    )

    with pytest.raises(OSError, match=f"simulated {failure_point} failure"):
        postgres_target.write_exclusive(path, {"valid": True})

    assert not path.exists()
    pending = list(path.parent.glob(".pending-write-*"))
    assert len(pending) == 1
    _assert_pending_name(pending[0], path)


def test_write_exclusive_preexisting_foreign_final_is_untouched(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    path.parent.mkdir(parents=True)
    foreign = b"other-process"
    path.write_bytes(foreign)

    with pytest.raises(FileExistsError):
        postgres_target.write_exclusive(path, {"valid": True})

    assert path.read_bytes() == foreign
    pending = list(path.parent.glob(".pending-write-*"))
    assert len(pending) == 1
    _assert_pending_name(pending[0], path)
    assert pending[0].read_bytes() == b'{"valid":true}\n'


def test_write_exclusive_detects_close_time_pending_replacement_before_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    foreign = b"other-process"
    foreign_source = tmp_path / "other-process.tmp"
    foreign_source.write_bytes(foreign)
    _patch_pending_stream(
        monkeypatch,
        path,
        lambda stream, pending: _ReplacePendingOnClose(
            stream, pending, foreign_source
        ),
    )

    with pytest.raises(RuntimeError, match="changed"):
        postgres_target.write_exclusive(path, {"valid": True})

    assert not path.exists()
    pending = list(path.parent.glob(".pending-write-*"))
    assert len(pending) == 1
    assert pending[0].read_bytes() == foreign


def test_write_exclusive_detects_pending_replacement_during_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    foreign = b"other-process"
    foreign_source = tmp_path / "other-process.tmp"
    foreign_source.write_bytes(foreign)
    original_link = postgres_target.os.link
    original_replace = postgres_target.os.replace

    def link_after_pending_swap(
        source,
        destination,
        *,
        follow_symlinks: bool = True,
    ) -> None:
        original_replace(foreign_source, source)
        original_link(
            source,
            destination,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(postgres_target.os, "link", link_after_pending_swap)

    with pytest.raises(RuntimeError, match="changed"):
        postgres_target.write_exclusive(path, {"valid": True})

    assert path.read_bytes() == foreign
    pending = list(path.parent.glob(".pending-write-*"))
    assert len(pending) == 1
    assert pending[0].read_bytes() == foreign


def test_write_exclusive_final_lstat_failure_does_not_reverse_successful_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "nested" / "manifest.json"
    original_lstat = Path.lstat

    def deny_final_metadata(candidate: Path):
        if candidate == path:
            raise PermissionError("simulated final lstat failure")
        return original_lstat(candidate)

    monkeypatch.setattr(Path, "lstat", deny_final_metadata)

    result = postgres_target.write_exclusive(path, {"z": 1, "a": "ok"})

    assert result == path
    assert path.read_bytes() == b'{"a":"ok","z":1}\n'
