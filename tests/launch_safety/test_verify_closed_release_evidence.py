from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts" / "ops" / "verify_closed_release.py"
POSIX_DIRECTORY_FD = os.name != "nt" and all(
    function in os.supports_dir_fd for function in (os.open, os.mkdir, os.replace, os.unlink)
)


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "task5_verify_closed_release_evidence", VERIFY
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {VERIFY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _symlink_directory(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def _junction_directory(link: Path, target: Path) -> None:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"cannot create Windows junction: {result.stderr or result.stdout}")


def test_write_evidence_rejects_symlinked_parent_without_touching_victim(
    tmp_path: Path,
):
    verifier = _load_verifier()
    victim = tmp_path / "victim"
    victim.mkdir()
    evidence_parent = tmp_path / "evidence"
    _symlink_directory(evidence_parent, victim)

    with pytest.raises(OSError, match="symlink"):
        verifier._write_evidence(
            evidence_parent / "closed-release.json", {"status": "passed"}
        )

    assert list(victim.iterdir()) == []


def test_write_evidence_rejects_symlinked_ancestor_without_touching_victim(
    tmp_path: Path,
):
    verifier = _load_verifier()
    authority = tmp_path / "authority"
    authority.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    redirected_ancestor = authority / "redirected"
    _symlink_directory(redirected_ancestor, victim)

    with pytest.raises(OSError, match="symlink"):
        verifier._write_evidence(
            redirected_ancestor / "nested" / "closed-release.json",
            {"status": "passed"},
        )

    assert list(victim.iterdir()) == []


def test_write_evidence_rejects_leaf_symlink_without_touching_victim(
    tmp_path: Path,
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    victim = tmp_path / "victim.json"
    victim.write_bytes(b"victim\n")
    evidence = evidence_parent / "closed-release.json"
    try:
        evidence.symlink_to(victim)
    except OSError as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    with pytest.raises(OSError, match="symlink"):
        verifier._write_evidence(evidence, {"status": "passed"})

    assert victim.read_bytes() == b"victim\n"
    assert evidence.is_symlink()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction semantics required")
def test_write_evidence_rejects_junctioned_parent_without_touching_victim(
    tmp_path: Path,
):
    verifier = _load_verifier()
    victim = tmp_path / "victim"
    victim.mkdir()
    evidence_parent = tmp_path / "evidence"
    _junction_directory(evidence_parent, victim)

    with pytest.raises(OSError, match="junction|reparse|symlink"):
        verifier._write_evidence(
            evidence_parent / "closed-release.json", {"status": "passed"}
        )

    assert list(victim.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows authority handles required")
def test_windows_missing_nested_parent_creation_never_uses_path_mkdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence = tmp_path / "missing" / "nested" / "closed-release.json"

    def reject_path_based_creation(*args, **kwargs) -> None:
        raise AssertionError("Windows evidence creation used Path.mkdir")

    monkeypatch.setattr(Path, "mkdir", reject_path_based_creation)

    verifier._write_evidence(evidence, {"status": "passed"})

    assert json.loads(evidence.read_text(encoding="utf-8")) == {
        "status": "passed"
    }
    assert evidence.parent.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="Windows authority handles required")
def test_write_evidence_windows_parent_swap_armed_during_file_fsync_cannot_forge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    held_parent = tmp_path / "evidence-held"
    evidence = evidence_parent / "closed-release.json"
    real_fsync = os.fsync
    real_trusted = verifier._trusted_evidence_directory
    file_fsynced = False
    swap_attempted = False
    swap_blocked = False

    def arm_swap_after_file_fsync(descriptor: int) -> None:
        nonlocal file_fsynced
        real_fsync(descriptor)
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            file_fsynced = True

    def attempt_swap_before_post_fsync_validation(
        path: Path, *, create: bool
    ) -> Path:
        nonlocal swap_attempted, swap_blocked
        if file_fsynced and not swap_attempted:
            swap_attempted = True
            try:
                evidence_parent.rename(held_parent)
            except OSError:
                swap_blocked = True
            else:
                evidence_parent.mkdir()
                genuine_temp = next(
                    held_parent.glob(".closed-release.json.*.tmp")
                )
                (evidence_parent / genuine_temp.name).write_text(
                    '{"status":"attacker"}\n', encoding="ascii"
                )
        return real_trusted(path, create=create)

    monkeypatch.setattr(os, "fsync", arm_swap_after_file_fsync)
    monkeypatch.setattr(
        verifier,
        "_trusted_evidence_directory",
        attempt_swap_before_post_fsync_validation,
    )

    verifier._write_evidence(evidence, {"status": "passed"})

    assert swap_attempted is True
    assert swap_blocked is True
    assert json.loads(evidence.read_text(encoding="utf-8")) == {
        "status": "passed"
    }
    assert not held_parent.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows authority handles required")
def test_write_evidence_windows_stable_authority_writes_normally(tmp_path: Path):
    verifier = _load_verifier()
    evidence = tmp_path / "evidence" / "closed-release.json"

    verifier._write_evidence(evidence, {"status": "passed"})

    assert json.loads(evidence.read_text(encoding="utf-8")) == {
        "status": "passed"
    }
    assert list(evidence.parent.glob(".closed-release.json.*.tmp")) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows native replace semantics required")
def test_write_evidence_windows_replaces_existing_regular_target(tmp_path: Path):
    verifier = _load_verifier()
    evidence = tmp_path / "evidence" / "closed-release.json"
    evidence.parent.mkdir()
    evidence.write_text('{"status":"old"}\n', encoding="ascii")

    verifier._write_evidence(evidence, {"status": "passed"})

    assert json.loads(evidence.read_text(encoding="utf-8")) == {
        "status": "passed"
    }
    assert list(evidence.parent.glob(".closed-release.json.*.tmp")) == []


def test_write_evidence_preserves_primary_error_when_cleanup_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence = tmp_path / "evidence" / "closed-release.json"
    real_fsync = os.fsync
    real_path_unlink = Path.unlink
    real_os_unlink = os.unlink
    cleanup_attempted: list[str] = []

    def fail_file_fsync(descriptor: int) -> None:
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("primary fsync failure")
        real_fsync(descriptor)

    def fail_path_cleanup(path: Path, *args, **kwargs) -> None:
        if path.name.startswith(".closed-release.json."):
            cleanup_attempted.append(path.name)
            raise OSError("cleanup unlink failure")
        real_path_unlink(path, *args, **kwargs)

    def fail_os_cleanup(path, *args, **kwargs) -> None:
        if str(path).startswith(".closed-release.json."):
            cleanup_attempted.append(str(path))
            raise OSError("cleanup unlink failure")
        real_os_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "fsync", fail_file_fsync)
    monkeypatch.setattr(Path, "unlink", fail_path_cleanup)
    monkeypatch.setattr(os, "unlink", fail_os_cleanup)

    with pytest.raises(OSError, match="primary fsync failure") as raised:
        verifier._write_evidence(evidence, {"status": "passed"})

    assert cleanup_attempted
    assert any("cleanup unlink failure" in note for note in raised.value.__notes__)


def test_posix_directory_handoff_close_failure_cleans_both_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    opened = [10]
    close_attempts: list[int] = []

    def open_root(*args, **kwargs):
        return opened[0]

    def open_next(*args, **kwargs):
        descriptor = 10 + len(opened)
        opened.append(descriptor)
        return descriptor

    def fail_first_handoff_close(descriptor: int) -> None:
        close_attempts.append(descriptor)
        if opened and descriptor == opened[0] and close_attempts.count(descriptor) == 1:
            raise OSError("handoff close failure")

    monkeypatch.setattr(os, "open", open_root)
    monkeypatch.setattr(os, "close", fail_first_handoff_close)
    monkeypatch.setattr(verifier, "_require_posix_evidence_capabilities", lambda: None)
    monkeypatch.setattr(verifier.os, "O_DIRECTORY", 0, raising=False)
    monkeypatch.setattr(verifier.os, "O_NOFOLLOW", 0, raising=False)
    monkeypatch.setattr(
        verifier, "_open_evidence_directory_component", open_next
    )

    with pytest.raises(OSError, match="handoff close failure"):
        verifier._open_trusted_posix_evidence_directory(
            evidence_parent, create=False
        )

    assert len(opened) >= 2
    assert opened[0] in close_attempts
    assert opened[1] in close_attempts
    assert close_attempts.count(opened[0]) == 1


def test_posix_non_directory_rejection_preserves_error_if_close_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    parent_descriptor = 30
    child_descriptor = 31
    close_attempts: list[int] = []
    regular_mode = stat.S_IFREG | 0o600

    monkeypatch.setattr(
        verifier,
        "_evidence_directory_open_flags",
        lambda: 0,
    )
    monkeypatch.setattr(verifier.os, "open", lambda *args, **kwargs: child_descriptor)
    monkeypatch.setattr(
        verifier.os,
        "fstat",
        lambda descriptor: os.stat_result(
            (regular_mode, 0, 0, 1, 0, 0, 0, 0, 0, 0)
        ),
    )

    def fail_close(descriptor: int) -> None:
        close_attempts.append(descriptor)
        raise OSError("descriptor close failure")

    monkeypatch.setattr(verifier.os, "close", fail_close)

    with pytest.raises(OSError, match="evidence ancestor is not a directory") as raised:
        verifier._open_evidence_directory_component(
            parent_descriptor, "child", tmp_path / "child"
        )

    assert close_attempts == [child_descriptor]
    assert any(
        "descriptor close failure" in note for note in raised.value.__notes__
    )


def test_posix_child_fstat_error_stays_primary_when_close_fails_without_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    parent_descriptor = 40
    child_descriptor = 41
    open_descriptors = {child_descriptor}

    monkeypatch.setattr(verifier, "_evidence_directory_open_flags", lambda: 0)
    monkeypatch.setattr(
        verifier.os, "open", lambda *args, **kwargs: child_descriptor
    )

    def fail_fstat(descriptor: int):
        assert descriptor == child_descriptor
        raise OSError("child fstat failure")

    def close_then_fail(descriptor: int) -> None:
        open_descriptors.remove(descriptor)
        raise OSError("descriptor close failure")

    monkeypatch.setattr(verifier.os, "fstat", fail_fstat)
    monkeypatch.setattr(verifier.os, "close", close_then_fail)

    with pytest.raises(OSError, match="child fstat failure") as raised:
        verifier._open_evidence_directory_component(
            parent_descriptor, "child", tmp_path / "child"
        )

    assert open_descriptors == set()
    assert any(
        "descriptor close failure" in note for note in raised.value.__notes__
    )


def test_posix_revalidation_close_failure_preserves_primary_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    current_descriptor = 20
    opened_descriptor = 21
    close_attempts: list[int] = []

    def fail_fstat(_: int):
        raise OSError("primary authority error")

    def fail_current_close(descriptor: int) -> None:
        close_attempts.append(descriptor)
        if descriptor == current_descriptor:
            raise OSError("cleanup close failure")

    monkeypatch.setattr(
        verifier,
        "_open_trusted_posix_evidence_directory",
        lambda path, create: current_descriptor,
    )
    monkeypatch.setattr(os, "fstat", fail_fstat)
    monkeypatch.setattr(os, "close", fail_current_close)

    with pytest.raises(OSError, match="primary authority error") as raised:
        verifier._revalidate_evidence_parent(
            evidence_parent, opened_descriptor
        )

    assert current_descriptor in close_attempts
    assert any(
        "cleanup close failure" in note for note in raised.value.__notes__
    )


def test_write_evidence_fails_closed_without_posix_no_follow_or_dir_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence = tmp_path / "evidence" / "closed-release.json"
    monkeypatch.delattr(verifier.os, "O_NOFOLLOW", raising=False)
    monkeypatch.setattr(verifier.os, "supports_dir_fd", set())

    with pytest.raises(OSError, match="POSIX evidence capabilities"):
        verifier._write_posix_evidence(evidence, b'{}\n')

    assert not evidence.parent.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows path creation semantics required")
def test_windows_native_directory_create_open_collision(tmp_path: Path):
    verifier = _load_verifier()
    parent_handle = verifier._open_windows_evidence_directory_handle(
        tmp_path, writable=True
    )
    existing = tmp_path / "existing"
    existing.mkdir()
    child_handle = -1
    try:
        child_handle = verifier._create_windows_evidence_directory_component(
            parent_handle, existing.name, existing, writable=True
        )
        assert child_handle != parent_handle
    finally:
        if child_handle != -1:
            cleanup_error = verifier._close_windows_handle(child_handle)
            if cleanup_error is not None:
                raise cleanup_error
        cleanup_error = verifier._close_windows_handle(parent_handle)
        if cleanup_error is not None:
            raise cleanup_error


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory fsync contract")
def test_write_evidence_fsyncs_file_replaces_atomically_and_fsyncs_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    evidence = evidence_parent / "closed-release.json"
    evidence.write_bytes(b"old evidence\n")
    old_stream = evidence.open("rb")
    observed_modes: list[int] = []
    real_fsync = os.fsync

    def observe_fsync(descriptor: int) -> None:
        observed_modes.append(os.fstat(descriptor).st_mode)
        real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", observe_fsync)
    try:
        verifier._write_evidence(evidence, {"status": "passed"})
        old_stream.seek(0)
        assert old_stream.read() == b"old evidence\n"
    finally:
        old_stream.close()

    assert json.loads(evidence.read_text(encoding="utf-8")) == {"status": "passed"}
    assert stat.S_ISREG(observed_modes[0])
    assert any(stat.S_ISDIR(mode) for mode in observed_modes[1:])
    assert list(evidence_parent.glob(".closed-release.json.*.tmp")) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory fsync contract")
def test_write_evidence_parent_fsync_failure_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    evidence = evidence_parent / "closed-release.json"
    real_fsync = os.fsync

    def fail_directory_fsync(descriptor: int) -> None:
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError("injected parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_directory_fsync)

    with pytest.raises(OSError, match="injected parent fsync failure"):
        verifier._write_evidence(evidence, {"status": "passed"})

    assert json.loads(evidence.read_text(encoding="utf-8")) == {"status": "passed"}
    assert list(evidence_parent.glob(".closed-release.json.*.tmp")) == []


@pytest.mark.skipif(
    not POSIX_DIRECTORY_FD, reason="POSIX symlink and directory-fd semantics required"
)
def test_write_evidence_rejects_parent_replacement_after_temp_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    held_parent = tmp_path / "evidence-held"
    victim = tmp_path / "victim"
    victim.mkdir()
    evidence = evidence_parent / "closed-release.json"
    real_fsync = os.fsync
    parent_replaced = False

    def replace_parent_after_file_fsync(descriptor: int) -> None:
        nonlocal parent_replaced
        observed = os.fstat(descriptor)
        real_fsync(descriptor)
        if stat.S_ISREG(observed.st_mode) and not parent_replaced:
            evidence_parent.rename(held_parent)
            evidence_parent.symlink_to(victim, target_is_directory=True)
            parent_replaced = True

    monkeypatch.setattr(os, "fsync", replace_parent_after_file_fsync)

    with pytest.raises(OSError, match="authority changed|symlink"):
        verifier._write_evidence(evidence, {"status": "passed"})

    assert parent_replaced is True
    assert list(victim.iterdir()) == []
    assert list(held_parent.iterdir()) == []


@pytest.mark.skipif(
    not POSIX_DIRECTORY_FD, reason="POSIX directory-fd semantics required"
)
def test_write_evidence_rejects_real_directory_parent_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    held_parent = tmp_path / "evidence-held"
    evidence = evidence_parent / "closed-release.json"
    real_fsync = os.fsync
    parent_replaced = False

    def replace_parent_after_file_fsync(descriptor: int) -> None:
        nonlocal parent_replaced
        observed = os.fstat(descriptor)
        real_fsync(descriptor)
        if stat.S_ISREG(observed.st_mode) and not parent_replaced:
            evidence_parent.rename(held_parent)
            evidence_parent.mkdir()
            parent_replaced = True

    monkeypatch.setattr(os, "fsync", replace_parent_after_file_fsync)

    with pytest.raises(OSError, match="evidence parent authority changed"):
        verifier._write_evidence(evidence, {"status": "passed"})

    assert parent_replaced is True
    assert list(evidence_parent.iterdir()) == []
    assert list(held_parent.iterdir()) == []


@pytest.mark.skipif(
    not POSIX_DIRECTORY_FD, reason="POSIX directory-fd semantics required"
)
def test_write_evidence_rejects_parent_swap_at_replace_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    verifier = _load_verifier()
    evidence_parent = tmp_path / "evidence"
    evidence_parent.mkdir()
    held_parent = tmp_path / "evidence-held"
    evidence = evidence_parent / "closed-release.json"
    attacker_payload = {"status": "attacker"}
    real_replace = os.replace
    parent_swapped = False

    def swap_parent_then_replace_through_held_descriptor(
        source: str,
        target: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal parent_swapped
        assert src_dir_fd is not None
        assert src_dir_fd == dst_dir_fd
        evidence_parent.rename(held_parent)
        evidence_parent.mkdir()
        evidence.write_text(
            json.dumps(attacker_payload) + "\n", encoding="ascii"
        )
        parent_swapped = True
        real_replace(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(verifier.os, "replace", swap_parent_then_replace_through_held_descriptor)

    failure: OSError | None = None
    try:
        verifier._write_evidence(evidence, {"status": "passed"})
    except OSError as exc:
        failure = exc

    assert parent_swapped is True
    assert json.loads(evidence.read_text(encoding="utf-8")) == attacker_payload
    assert json.loads(
        (held_parent / evidence.name).read_text(encoding="utf-8")
    ) == {"status": "passed"}
    if failure is None:
        pytest.fail(
            "writer returned success after os.replace committed evidence "
            "through a detached parent dirfd while the visible path was replaced"
        )
    assert "authority changed" in str(failure)
