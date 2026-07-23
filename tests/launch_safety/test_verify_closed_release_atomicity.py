from __future__ import annotations

import gzip
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import tarfile

import pytest

from scripts.package_launch_release import build_launch_release
from tests.launch_safety.test_rollback_runbook import _build_closed_package


ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts" / "ops" / "verify_closed_release.py"
CHECK_MIGRATION_GATE_MEMBER = "scripts/check_migration_gate.py"
ARCHIVED_VERIFIER_MEMBER = "scripts/ops/verify_closed_release.py"
MIGRATION_MEMBER_PREFIX = "agent/migrations/"


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "task5_verify_closed_release_atomicity", VERIFY
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {VERIFY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_migration_prerequisite_members(archive: Path) -> dict[str, bytes]:
    with tarfile.open(archive, "r:gz") as bundle:
        names = bundle.getnames()
        selected = [
            name
            for name in names
            if name == CHECK_MIGRATION_GATE_MEMBER
            or (
                name.startswith(MIGRATION_MEMBER_PREFIX)
                and name.endswith(".sql")
            )
        ]
        return {name: bundle.extractfile(name).read() for name in selected}


@pytest.fixture(scope="module")
def closed_package(tmp_path_factory: pytest.TempPathFactory):
    return _build_closed_package(tmp_path_factory.mktemp("atomicity-package"))


def test_archive_verifier_parses_admitted_bytes_after_path_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    closed_package,
):
    verifier = _load_verifier()
    archive = tmp_path / "candidate.tar.gz"
    shutil.copyfile(closed_package.archive, archive)
    admitted_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(f"{admitted_digest}  {archive.name}\n", encoding="ascii")
    replacement = b"replacement archive bytes\n"
    real_tarfile_open = verifier.tarfile.open
    path_replaced = False

    def replace_path_before_parse(*args, **kwargs):
        nonlocal path_replaced
        archive.write_bytes(replacement)
        path_replaced = True
        return real_tarfile_open(*args, **kwargs)

    monkeypatch.setattr(verifier.tarfile, "open", replace_path_before_parse)

    evidence = verifier.verify_archive(archive, sidecar)

    assert path_replaced is True
    assert archive.read_bytes() == replacement
    assert evidence["archive_sha256"] == admitted_digest


def test_archive_verifier_parses_admitted_bytes_after_atomic_path_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    closed_package,
):
    verifier = _load_verifier()
    archive = tmp_path / "candidate.tar.gz"
    shutil.copyfile(closed_package.archive, archive)
    admitted_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(f"{admitted_digest}  {archive.name}\n", encoding="ascii")
    replacement = tmp_path / "replacement.tar.gz"
    replacement_bytes = b"atomically replaced archive bytes\n"
    replacement.write_bytes(replacement_bytes)
    real_tarfile_open = verifier.tarfile.open
    path_replaced = False

    def replace_path_before_parse(*args, **kwargs):
        nonlocal path_replaced
        os.replace(replacement, archive)
        path_replaced = True
        return real_tarfile_open(*args, **kwargs)

    monkeypatch.setattr(verifier.tarfile, "open", replace_path_before_parse)

    evidence = verifier.verify_archive(archive, sidecar)

    assert path_replaced is True
    assert archive.read_bytes() == replacement_bytes
    assert evidence["archive_sha256"] == admitted_digest


def test_archive_verifier_materializes_migration_prerequisites_from_admitted_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = _load_verifier()
    package = _build_closed_package(tmp_path)
    archived = _read_migration_prerequisite_members(package.archive)
    assert CHECK_MIGRATION_GATE_MEMBER in archived
    migration_members = {
        name: raw
        for name, raw in archived.items()
        if name.startswith(MIGRATION_MEMBER_PREFIX)
    }
    assert migration_members

    source = tmp_path / "source"
    (source / CHECK_MIGRATION_GATE_MEMBER).write_bytes(b"mutated checker source\n")
    for migration in (source / "agent" / "migrations").glob("*.sql"):
        migration.write_bytes(b"mutated migration source\n")

    replacement = b"replacement live archive bytes\n"
    real_tarfile_open = verifier.tarfile.open
    path_replaced = False

    def replace_live_archive_after_admission(*args, **kwargs):
        nonlocal path_replaced
        package.archive.write_bytes(replacement)
        path_replaced = True
        return real_tarfile_open(*args, **kwargs)

    monkeypatch.setattr(verifier.tarfile, "open", replace_live_archive_after_admission)
    destination = tmp_path / "migration-prerequisites"

    verifier.verify_archive(
        package.archive,
        package.digest_file,
        migration_prerequisite_dir=destination,
    )

    assert path_replaced is True
    assert package.archive.read_bytes() == replacement
    assert (destination / "check_migration_gate.py").read_bytes() == archived[
        CHECK_MIGRATION_GATE_MEMBER
    ]
    assert {
        f"{MIGRATION_MEMBER_PREFIX}{path.name}": path.read_bytes()
        for path in (destination / "migrations").glob("*.sql")
    } == migration_members


def test_archive_verifier_refuses_migration_materialization_when_self_bytes_differ(
    tmp_path: Path,
):
    verifier = _load_verifier()
    _build_closed_package(tmp_path)
    source = tmp_path / "source"
    (source / ARCHIVED_VERIFIER_MEMBER).write_bytes(
        b"#!/usr/bin/env python3\n# verifier identity mismatch\n"
    )
    package = build_launch_release(
        source,
        tmp_path / "mismatched-verifier.tar.gz",
        compose_network_audit=source / "build" / "compose-network-audit.json",
        source_revision="reviewed-source-revision",
    )
    destination = tmp_path / "migration-prerequisites"
    before = set(tmp_path.iterdir())

    with pytest.raises(
        ValueError,
        match="running verifier bytes do not match archived verifier",
    ):
        verifier.verify_archive(
            package.archive,
            package.digest_file,
            migration_prerequisite_dir=destination,
        )

    assert not destination.exists()
    assert set(tmp_path.iterdir()) == before


def test_archive_verifier_refuses_existing_migration_prerequisite_destination(
    tmp_path: Path,
    closed_package,
):
    verifier = _load_verifier()
    destination = tmp_path / "migration-prerequisites"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_bytes(b"keep existing destination\n")
    before = set(tmp_path.iterdir())

    with pytest.raises(FileExistsError):
        verifier.verify_archive(
            closed_package.archive,
            closed_package.digest_file,
            migration_prerequisite_dir=destination,
        )

    assert list(destination.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep existing destination\n"
    assert set(tmp_path.iterdir()) == before


def test_archive_verifier_refuses_symlink_migration_prerequisite_destination(
    tmp_path: Path,
    closed_package,
):
    verifier = _load_verifier()
    victim = tmp_path / "victim"
    victim.mkdir()
    sentinel = victim / "keep.txt"
    sentinel.write_bytes(b"keep symlink target\n")
    destination = tmp_path / "migration-prerequisites"
    try:
        destination.symlink_to(victim, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    before = set(tmp_path.iterdir())

    with pytest.raises(OSError):
        verifier.verify_archive(
            closed_package.archive,
            closed_package.digest_file,
            migration_prerequisite_dir=destination,
        )

    assert destination.is_symlink()
    assert list(victim.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"keep symlink target\n"
    assert set(tmp_path.iterdir()) == before


def test_materialization_cleanup_never_deletes_a_replacement_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_verifier()
    destination = tmp_path / "migration-prerequisites"
    moved = tmp_path / "moved-created-directory"
    sentinel = destination / "competitor.txt"

    def swap_destination_then_fail(*_args, **_kwargs) -> None:
        destination.rename(moved)
        destination.mkdir()
        sentinel.write_bytes(b"competitor-owned\n")
        raise OSError("injected materialization failure")

    monkeypatch.setattr(
        verifier, "_write_exclusive_regular", swap_destination_then_fail
    )
    members = {
        verifier.CHECK_MIGRATION_GATE_MEMBER: b"checker\n",
        f"{verifier.MIGRATION_MEMBER_PREFIX}070_gate.sql": b"-- migration\n",
    }
    evidence = {"migrations": [{"name": "070_gate.sql"}]}

    with pytest.raises(OSError, match="injected materialization failure"):
        verifier._materialize_migration_prerequisites(
            destination, members, evidence
        )

    assert sentinel.read_bytes() == b"competitor-owned\n"
    assert moved.is_dir()


def test_archive_snapshot_rejects_bytes_beyond_configured_resource_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = _load_verifier()
    archive = tmp_path / "candidate.tar.gz"
    raw = b"bounded archive snapshot\n"
    archive.write_bytes(raw)
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(
        f"{hashlib.sha256(raw).hexdigest()}  {archive.name}\n",
        encoding="ascii",
    )
    monkeypatch.setattr(
        verifier,
        "MAX_ARCHIVE_SNAPSHOT_BYTES",
        len(raw) - 1,
    )

    with pytest.raises(ValueError, match="archive exceeds maximum snapshot size"):
        verifier._read_sidecar(archive, sidecar)


def test_archive_rejects_member_beyond_expanded_resource_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = _load_verifier()
    payload = tmp_path / "oversized.bin"
    raw = b"highly compressible expanded member\n" * 8
    payload.write_bytes(raw)
    archive = tmp_path / "expanded-member.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(payload, arcname="oversized.bin")
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(
        f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n",
        encoding="ascii",
    )
    monkeypatch.setattr(
        verifier,
        "MAX_ARCHIVE_MEMBER_BYTES",
        len(raw) - 1,
        raising=False,
    )

    with pytest.raises(ValueError, match="archive member exceeds maximum expanded size"):
        verifier.verify_archive(archive, sidecar)


def test_archive_rejects_oversized_member_before_gzip_scans_its_contents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = _load_verifier()
    member_limit = 64 * 1024
    raw = b"z" * (member_limit * 2)
    payload = tmp_path / "gzip-expansion.bin"
    payload.write_bytes(raw)
    archive = tmp_path / "gzip-expansion.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(payload, arcname="gzip-expansion.bin")
    assert archive.stat().st_size < len(raw) // 8
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(
        f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n",
        encoding="ascii",
    )
    monkeypatch.setattr(verifier, "MAX_ARCHIVE_MEMBER_BYTES", member_limit)

    getmembers_calls = 0
    member_data_seeks: list[int] = []
    real_getmembers = verifier.tarfile.TarFile.getmembers
    real_gzip_seek = gzip.GzipFile.seek

    def track_getmembers(bundle):
        nonlocal getmembers_calls
        getmembers_calls += 1
        return real_getmembers(bundle)

    def track_gzip_seek(stream, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET and offset > tarfile.BLOCKSIZE:
            member_data_seeks.append(offset)
        return real_gzip_seek(stream, offset, whence)

    monkeypatch.setattr(verifier.tarfile.TarFile, "getmembers", track_getmembers)
    monkeypatch.setattr(gzip.GzipFile, "seek", track_gzip_seek)

    with pytest.raises(ValueError, match="archive member exceeds maximum expanded size"):
        verifier.verify_archive(archive, sidecar)

    assert (getmembers_calls, member_data_seeks) == (0, []), (
        "oversized member metadata must be rejected before getmembers() seeks through "
        f"its compressed payload; calls={getmembers_calls}, seeks={member_data_seeks}"
    )


def test_archive_rejects_aggregate_expansion_beyond_resource_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = _load_verifier()
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"a" * 8)
    second.write_bytes(b"b" * 8)
    archive = tmp_path / "aggregate-expansion.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(first, arcname="first.bin")
        bundle.add(second, arcname="second.bin")
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(
        f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n",
        encoding="ascii",
    )
    monkeypatch.setattr(verifier, "MAX_ARCHIVE_MEMBER_BYTES", 8, raising=False)
    monkeypatch.setattr(verifier, "MAX_ARCHIVE_EXPANDED_BYTES", 15, raising=False)

    with pytest.raises(ValueError, match="archive exceeds maximum expanded size"):
        verifier.verify_archive(archive, sidecar)


def test_archive_checks_member_limit_before_eager_tar_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = _load_verifier()
    payload = tmp_path / "oversized.bin"
    payload.write_bytes(b"\0" * (2 * 1024 * 1024))
    archive = tmp_path / "streamed-limit.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(payload, arcname="oversized.bin")
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(
        f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n",
        encoding="ascii",
    )
    monkeypatch.setattr(verifier, "MAX_ARCHIVE_MEMBER_BYTES", 1)

    def fail_on_eager_member_scan(*_args, **_kwargs):
        raise AssertionError("eager tar member scan bypassed the expansion limit")

    monkeypatch.setattr(
        verifier.tarfile.TarFile,
        "getmembers",
        fail_on_eager_member_scan,
    )

    with pytest.raises(ValueError, match="archive member exceeds maximum expanded size"):
        verifier.verify_archive(archive, sidecar)


def test_cli_refuses_memory_exhaustion_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    verifier = _load_verifier()

    def exhaust_memory(*_args, **_kwargs):
        raise MemoryError

    monkeypatch.setattr(verifier, "verify_archive", exhaust_memory)

    status = verifier.main(["--archive", str(tmp_path / "candidate.tar.gz")])

    assert status == 2
    assert "memory resource limit exceeded" in capsys.readouterr().err


def test_cli_refuses_memory_exhaustion_while_serializing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    verifier = _load_verifier()

    monkeypatch.setattr(verifier, "verify_archive", lambda *_args, **_kwargs: {})

    def exhaust_memory(*_args, **_kwargs):
        raise MemoryError

    monkeypatch.setattr(verifier.json, "dumps", exhaust_memory)

    status = verifier.main(["--archive", str(tmp_path / "candidate.tar.gz")])

    assert status == 2
    assert "memory resource limit exceeded" in capsys.readouterr().err


def test_installed_terminal_revalidation_does_not_materialize_second_byte_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    closed_package,
):
    verifier = _load_verifier()
    root = tmp_path / "release"
    with tarfile.open(closed_package.archive, "r:gz") as bundle:
        bundle.extractall(root, filter="data")
    (root / ".env").write_bytes(b"excluded environment authority\n")
    persistent = root / "agent" / "data"
    persistent.mkdir(parents=True)
    (persistent / "state.bin").write_bytes(b"excluded persistent state\n")
    real_walk_installed = verifier._walk_installed
    walk_count = 0

    def count_full_byte_walk(path: Path):
        nonlocal walk_count
        walk_count += 1
        if walk_count > 1:
            raise AssertionError("terminal revalidation materialized a second byte tree")
        return real_walk_installed(path)

    monkeypatch.setattr(verifier, "_walk_installed", count_full_byte_walk)

    evidence = verifier.verify_installed_root(root)

    assert evidence["closed_verified"] is True
    assert walk_count == 1


@pytest.mark.parametrize("mutation", ["member", "root"])
def test_installed_root_rejects_tree_changes_after_initial_walk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    closed_package,
    mutation: str,
):
    verifier = _load_verifier()
    root = tmp_path / "release"
    with tarfile.open(closed_package.archive, "r:gz") as bundle:
        bundle.extractall(root, filter="data")
    real_validate_loopback_units = verifier._validate_loopback_units
    mutation_applied = False

    def mutate_after_initial_walk(members):
        nonlocal mutation_applied
        real_validate_loopback_units(members)
        if mutation_applied:
            return
        if mutation == "member":
            target = root / "nginx.conf"
            target.write_bytes(target.read_bytes() + b"\nmutation\n")
        else:
            held = tmp_path / "release-held"
            root.rename(held)
            shutil.copytree(held, root)
        mutation_applied = True

    monkeypatch.setattr(
        verifier, "_validate_loopback_units", mutate_after_initial_walk
    )

    with pytest.raises(ValueError, match="changed during verification"):
        verifier.verify_installed_root(root)

    assert mutation_applied is True


def test_installed_root_rejects_systemd_change_after_destination_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    closed_package,
):
    verifier = _load_verifier()
    root = tmp_path / "release"
    with tarfile.open(closed_package.archive, "r:gz") as bundle:
        bundle.extractall(root, filter="data")
    systemd_root = tmp_path / "systemd"
    systemd_root.mkdir()
    for relative in verifier.SYSTEMD_UNIT_PATHS:
        source = root / relative
        shutil.copyfile(source, systemd_root / source.name)
    real_verify_destination = verifier._verify_systemd_unit_destination
    mutation_applied = False

    def mutate_after_destination_check(manifest, destination):
        nonlocal mutation_applied
        verified = real_verify_destination(manifest, destination)
        if mutation_applied:
            return verified
        target = Path(destination) / Path(verifier.SYSTEMD_UNIT_PATHS[0]).name
        target.write_bytes(target.read_bytes() + b"\nmutation\n")
        mutation_applied = True
        return verified

    monkeypatch.setattr(
        verifier,
        "_verify_systemd_unit_destination",
        mutate_after_destination_check,
    )

    with pytest.raises(
        ValueError,
        match=r"changed during verification|systemd unit digest mismatch",
    ):
        verifier.verify_installed_root(
            root,
            systemd_unit_root=systemd_root,
            verify_systemd_unit_destination=True,
        )

    assert mutation_applied is True


def test_installed_root_rejects_environment_authority_change_after_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    closed_package,
):
    verifier = _load_verifier()
    root = tmp_path / "release"
    with tarfile.open(closed_package.archive, "r:gz") as bundle:
        bundle.extractall(root, filter="data")
    environment_authority = tmp_path / "release.env"
    admitted = b"SAFE_LOCAL=1\n"
    environment_authority.write_bytes(admitted)
    (root / ".env").write_bytes(admitted)
    real_verify_authority = verifier._verify_environment_authority
    mutation_applied = False

    def mutate_after_authority_check(installed_root, authority):
        nonlocal mutation_applied
        evidence = real_verify_authority(installed_root, authority)
        if mutation_applied:
            return evidence
        Path(authority).write_bytes(b"SAFE_LOCAL=mutated\n")
        mutation_applied = True
        return evidence

    monkeypatch.setattr(
        verifier,
        "_verify_environment_authority",
        mutate_after_authority_check,
    )

    with pytest.raises(
        ValueError,
        match=r"changed during verification|environment authority bytes do not match",
    ):
        verifier.verify_installed_root(
            root,
            environment_authority=environment_authority,
            verify_environment_authority=True,
        )

    assert mutation_applied is True


def test_installed_root_rejects_persistent_mountpoint_swap_after_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    closed_package,
):
    verifier = _load_verifier()
    root = tmp_path / "release"
    with tarfile.open(closed_package.archive, "r:gz") as bundle:
        bundle.extractall(root, filter="data")
    persistent_authority = tmp_path / "persistent-agent-data"
    persistent_authority.mkdir()
    mountpoint = root / "agent" / "data"
    mountpoint.mkdir(parents=True)
    (mountpoint / "state.bin").write_bytes(b"persistent state\n")
    detached_mountpoint = tmp_path / "detached-agent-data"
    real_verify_mount = verifier._verify_persistent_agent_data_mount
    mutation_applied = False

    def swap_after_mountpoint_check(installed_root, external, **kwargs):
        nonlocal mutation_applied
        evidence = real_verify_mount(installed_root, external, **kwargs)
        if mutation_applied:
            return evidence
        mountpoint.rename(detached_mountpoint)
        mountpoint.mkdir()
        mutation_applied = True
        return evidence

    monkeypatch.setattr(
        verifier,
        "_verify_persistent_agent_data_mount",
        swap_after_mountpoint_check,
    )

    with pytest.raises(
        ValueError,
        match=r"changed during verification|persistent agent data mountpoint",
    ):
        verifier.verify_installed_root(
            root,
            persistent_agent_data_root=persistent_authority,
            verify_persistent_agent_data_mount=True,
            local_rehearsal=True,
        )

    assert mutation_applied is True
