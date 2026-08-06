import hashlib
import os
import stat
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

import launch_artifacts
from launch_artifacts import LoadedArtifact, load_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]


def symlink_or_skip(link, target, *, target_is_directory=False):
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")


class ReparsePointStat:
    def __init__(self, original):
        self._original = original
        self.st_file_attributes = getattr(original, "st_file_attributes", 0) | getattr(
            stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400,
        )
        self.st_reparse_tag = 0x8000001B

    def __getattr__(self, name):
        return getattr(self._original, name)


def test_load_artifact_uses_exact_fixture_bytes_for_data_and_sha(tmp_path):
    fixture = tmp_path / "fixture.json"
    raw = b'{\r\n  "name": "launch",\r\n  "enabled": true\r\n}\r\n'
    fixture.write_bytes(raw)

    loaded = load_artifact("ignored.json", fixture_path=fixture)

    assert loaded.path == fixture
    assert loaded.raw == raw
    assert loaded.data == {"name": "launch", "enabled": True}
    assert loaded.sha256 == hashlib.sha256(raw).hexdigest()
    with pytest.raises(FrozenInstanceError):
        loaded.path = tmp_path / "changed.json"


def test_load_artifact_recursively_freezes_parsed_json(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_bytes(
        b'{"revision": "v1", "routes": [{"path": "/first"}], "flags": [true]}'
    )

    loaded = load_artifact("fixture.json", fixture_path=fixture)

    assert isinstance(loaded.data, MappingProxyType)
    assert isinstance(loaded.data["routes"], tuple)
    assert isinstance(loaded.data["routes"][0], MappingProxyType)
    with pytest.raises(TypeError):
        loaded.data["revision"] = "v2"
    with pytest.raises(AttributeError):
        loaded.data["routes"].append({"path": "/second"})
    with pytest.raises(TypeError):
        loaded.data["routes"][0]["path"] = "/changed"


def test_loaded_artifact_constructor_owns_backing_data(tmp_path):
    raw = b'{"revision": "v1", "nested": {"value": 1}}'
    nested_backing = {"value": 1}
    root_backing = {
        "revision": "v1",
        "nested": MappingProxyType(nested_backing),
    }
    artifact = LoadedArtifact(
        path=tmp_path / "artifact.json",
        raw=raw,
        data=MappingProxyType(root_backing),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
    root_backing["revision"] = "v2"
    nested_backing["value"] = 2

    assert artifact.data["revision"] == "v1"
    assert artifact.data["nested"]["value"] == 1


@pytest.mark.parametrize("raw_kind", ["bytearray", "memoryview", "bytes-subclass"])
def test_loaded_artifact_constructor_owns_bytes_like_raw_evidence(tmp_path, raw_kind):
    original = b'{"revision": "v1"}'
    backing = bytearray(original)
    if raw_kind == "bytearray":
        supplied_raw = backing
    elif raw_kind == "memoryview":
        supplied_raw = memoryview(backing)
    else:
        class RawBytes(bytes):
            pass

        supplied_raw = RawBytes(original)

    artifact = LoadedArtifact(
        path=tmp_path / "artifact.json",
        raw=supplied_raw,
        data={"revision": "v1"},
        sha256=hashlib.sha256(original).hexdigest(),
    )
    backing[backing.index(ord("1"))] = ord("2")

    assert type(artifact.raw) is bytes
    assert artifact.raw == original
    assert artifact.data["revision"] == "v1"
    assert artifact.sha256 == hashlib.sha256(artifact.raw).hexdigest()


def test_loaded_artifact_constructor_rejects_non_bytes_like_raw(tmp_path):
    with pytest.raises(TypeError, match="bytes-like"):
        LoadedArtifact(
            path=tmp_path / "artifact.json",
            raw='{"revision": "v1"}',
            data={"revision": "v1"},
            sha256="0" * 64,
        )


@pytest.mark.parametrize("mismatch", ["sha", "data"])
def test_loaded_artifact_constructor_rejects_raw_evidence_mismatch(tmp_path, mismatch):
    raw = b'{"revision": "v1"}'
    data = {"revision": "different"} if mismatch == "data" else {"revision": "v1"}
    digest = "0" * 64 if mismatch == "sha" else hashlib.sha256(raw).hexdigest()

    with pytest.raises(ValueError, match="raw bytes"):
        LoadedArtifact(
            path=tmp_path / "artifact.json",
            raw=raw,
            data=data,
            sha256=digest,
        )


def test_load_artifact_reads_the_source_once(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture.json"
    fixture.write_bytes(b'{"value": 1}')
    original_open = os.open
    calls = []

    def counted_open(path, flags):
        calls.append(Path(path))
        return original_open(path, flags)

    monkeypatch.setattr(launch_artifacts.os, "open", counted_open)

    load_artifact("ignored.json", fixture_path=fixture)

    assert calls == [fixture]


def test_load_artifact_rejects_mutually_exclusive_sources(tmp_path):
    with pytest.raises(ValueError, match="mutually exclusive"):
        load_artifact(
            "launch-indexing-policy.json",
            release_root=tmp_path,
            fixture_path=tmp_path / "fixture.json",
        )


def test_load_artifact_propagates_missing_production_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_artifact("missing.json", release_root=tmp_path)


def test_load_artifact_resolves_release_root_config_exactly(tmp_path):
    configured = tmp_path / "config" / "artifact.json"
    configured.parent.mkdir()
    configured.write_bytes(b'{"source": "config"}')
    (tmp_path / "artifact.json").write_bytes(b'{"source": "fallback"}')

    loaded = load_artifact("artifact.json", release_root=tmp_path)

    assert loaded.path == configured
    assert loaded.data == {"source": "config"}


def test_load_artifact_allows_a_symlinked_release_root(tmp_path):
    real_root = tmp_path / "real-release"
    target = real_root / "config" / "artifact.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b'{"source": "real-release"}')
    release_link = tmp_path / "release-link"
    symlink_or_skip(release_link, real_root, target_is_directory=True)

    loaded = load_artifact("artifact.json", release_root=release_link)

    assert loaded.path == target.resolve()
    assert loaded.data == {"source": "real-release"}


@pytest.mark.parametrize("location", ["inside", "outside"])
def test_load_artifact_rejects_a_symlinked_production_config_directory(tmp_path, location):
    release_root = tmp_path / "release"
    release_root.mkdir()
    config_target = (
        release_root / "actual-config"
        if location == "inside"
        else tmp_path / "outside-config"
    )
    config_target.mkdir()
    (config_target / "artifact.json").write_bytes(b'{"source": "symlinked-config"}')
    symlink_or_skip(release_root / "config", config_target, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        load_artifact("artifact.json", release_root=release_root)


@pytest.mark.parametrize("location", ["inside", "outside"])
def test_load_artifact_rejects_a_symlinked_production_file(tmp_path, location):
    release_root = tmp_path / "release"
    config = release_root / "config"
    config.mkdir(parents=True)
    file_target = (
        config / "actual.json"
        if location == "inside"
        else tmp_path / "outside.json"
    )
    file_target.write_bytes(b'{"source": "symlinked-file"}')
    symlink_or_skip(config / "artifact.json", file_target)

    with pytest.raises(ValueError, match="symlink"):
        load_artifact("artifact.json", release_root=release_root)


def test_load_artifact_rejects_a_symlinked_fixture_file(tmp_path):
    target = tmp_path / "target.json"
    target.write_bytes(b'{"source": "fixture-symlink"}')
    fixture = tmp_path / "fixture.json"
    symlink_or_skip(fixture, target)

    with pytest.raises(ValueError, match="symlink"):
        load_artifact("artifact.json", fixture_path=fixture)


@pytest.mark.parametrize("source", ["production", "fixture"])
def test_load_artifact_rejects_a_directory_instead_of_a_regular_file(tmp_path, source):
    if source == "production":
        target = tmp_path / "config" / "artifact.json"
        target.mkdir(parents=True)
        kwargs = {"release_root": tmp_path}
    else:
        target = tmp_path / "fixture.json"
        target.mkdir()
        kwargs = {"fixture_path": target}

    with pytest.raises(ValueError, match="regular file"):
        load_artifact("artifact.json", **kwargs)


@pytest.mark.parametrize("source", ["production", "fixture"])
def test_load_artifact_rejects_a_regular_file_with_multiple_filesystem_links(
    tmp_path,
    source,
):
    if source == "production":
        target = tmp_path / "config" / "artifact.json"
        target.parent.mkdir()
        kwargs = {"release_root": tmp_path}
    else:
        target = tmp_path / "fixture.json"
        kwargs = {"fixture_path": target}
    target.write_bytes(b'{"source": "linked"}')
    try:
        os.link(target, tmp_path / f"{source}-alias.json")
    except OSError as exc:
        pytest.skip(f"hardlink creation unavailable: {exc}")

    assert os.lstat(target).st_nlink > 1
    with pytest.raises(ValueError, match="filesystem link"):
        load_artifact("artifact.json", **kwargs)


@pytest.mark.parametrize("source", ["production", "fixture"])
def test_load_artifact_rejects_regular_looking_windows_reparse_metadata(
    tmp_path,
    monkeypatch,
    source,
):
    if source == "production":
        # Nhánh release-root đi đường fd-based (`_regular_file_stat_at`) khi nền
        # có dir_fd — tức trên Linux — nên không hề gọi `os.lstat`, và bản
        # monkeypatch bên dưới không tới được chỗ nào. Reparse point là khái niệm
        # NTFS; `st_reparse_tag` của fstat thật trên Linux luôn 0, không có gì để
        # từ chối. Biến thể `fixture` vẫn chạy mọi nền vì nó đi nhánh lstat.
        if os.name != "nt":
            pytest.skip("nhánh release-root dùng fd-based stat ngoài Windows")
        target = tmp_path / "config" / "artifact.json"
        target.parent.mkdir()
        kwargs = {"release_root": tmp_path}
    else:
        target = tmp_path / "fixture.json"
        kwargs = {"fixture_path": target}
    target.write_bytes(b'{"source": "reparse"}')
    original_lstat = os.lstat

    def reparse_lstat(path, *args, **kwargs):
        result = original_lstat(path, *args, **kwargs)
        if Path(path) == target:
            return ReparsePointStat(result)
        return result

    monkeypatch.setattr(launch_artifacts.os, "lstat", reparse_lstat)

    with pytest.raises(ValueError, match="reparse point"):
        load_artifact("artifact.json", **kwargs)


def test_load_artifact_rejects_a_hardlink_added_between_preopen_and_fstat(
    tmp_path,
    monkeypatch,
):
    target = tmp_path / "fixture.json"
    target.write_bytes(b'{"source": "linked-during-open"}')
    alias = tmp_path / "alias.json"
    original_open = os.open

    def linking_open(path, flags, *args, **kwargs):
        descriptor = original_open(path, flags, *args, **kwargs)
        try:
            os.link(target, alias)
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor

    monkeypatch.setattr(launch_artifacts.os, "open", linking_open)

    with pytest.raises(ValueError, match="filesystem link"):
        load_artifact("artifact.json", fixture_path=target)

    assert alias.exists()


def test_load_artifact_rejects_a_hardlink_added_during_read(tmp_path, monkeypatch):
    target = tmp_path / "fixture.json"
    target.write_bytes(b'{"source": "linked-during-read"}')
    alias = tmp_path / "alias.json"
    original_fdopen = os.fdopen

    class LinkingStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self):
            os.link(target, alias)
            return self.stream.read()

    def linking_fdopen(*args, **kwargs):
        return LinkingStream(original_fdopen(*args, **kwargs))

    monkeypatch.setattr(launch_artifacts.os, "fdopen", linking_fdopen)

    with pytest.raises(ValueError, match="filesystem link"):
        load_artifact("artifact.json", fixture_path=target)

    assert alias.exists()


def test_load_artifact_rejects_a_fifo_before_reading_when_supported(tmp_path, monkeypatch):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable on this platform")
    fixture = tmp_path / "fixture.json"
    os.mkfifo(fixture)

    def forbidden_read(_path):
        pytest.fail("nonregular fixture reached file I/O")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)

    with pytest.raises(ValueError, match="regular file"):
        load_artifact("artifact.json", fixture_path=fixture)


def test_load_artifact_rejects_an_identity_swap_between_lstat_and_open(tmp_path, monkeypatch):
    target = tmp_path / "config" / "artifact.json"
    target.parent.mkdir()
    target.write_bytes(b'{"source": "original"}')
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(b'{"source": "replacement"}')
    original_open = os.open
    swapped = False

    def swapping_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if Path(path) == target and not swapped:
            replacement.replace(target)
            swapped = True
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", swapping_open)

    with pytest.raises(ValueError, match="identity"):
        load_artifact("artifact.json", release_root=tmp_path)


@pytest.mark.parametrize("location", ["inside", "outside"])
def test_load_artifact_rejects_parent_config_swap_to_symlink(
    tmp_path,
    monkeypatch,
    location,
):
    release_root = tmp_path / "release"
    config = release_root / "config"
    config.mkdir(parents=True)
    target = config / "artifact.json"
    target.write_bytes(b'{"source": "same-inode"}')
    retired_config = release_root / "config-retired"
    if location == "outside":
        redirect_target = tmp_path / "outside-config"
        redirect_target.mkdir()
        (redirect_target / "artifact.json").write_bytes(b'{"source": "outside"}')
    else:
        redirect_target = retired_config
    original_open = os.open
    swap_attempted = False

    def swapping_open(path, flags, *args, **kwargs):
        nonlocal swap_attempted
        if Path(path).name == "artifact.json" and not swap_attempted:
            swap_attempted = True
            config.rename(retired_config)
            symlink_or_skip(config, redirect_target, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", swapping_open)

    with pytest.raises(
        ValueError,
        match="config.*identity|parent.*identity|path.*identity|symlink",
    ):
        load_artifact("artifact.json", release_root=release_root)

    assert swap_attempted is True


@pytest.mark.skipif(os.name != "nt", reason="Windows directory sharing semantics")
def test_windows_production_load_pins_config_directory_before_child_open(
    tmp_path,
    monkeypatch,
):
    release_root = tmp_path / "release"
    config = release_root / "config"
    config.mkdir(parents=True)
    target = config / "artifact.json"
    original_raw = b'{"source": "original"}'
    target.write_bytes(original_raw)
    replacement = release_root / "replacement-config"
    replacement.mkdir()
    (replacement / "artifact.json").write_bytes(b'{"source": "replacement"}')
    retired = release_root / "retired-config"
    original_open = os.open
    state = {"attempted": False, "blocked": False, "restored": False}

    def replacing_and_restoring_open(path, flags, *args, **kwargs):
        if Path(path).name == target.name and not state["attempted"]:
            state["attempted"] = True
            try:
                config.rename(retired)
            except PermissionError:
                state["blocked"] = True
            else:
                replacement.rename(config)
                config.rename(replacement)
                retired.rename(config)
                state["restored"] = True
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(launch_artifacts.os, "open", replacing_and_restoring_open)

    try:
        loaded = load_artifact("artifact.json", release_root=release_root)
    except ValueError:
        loaded = None

    assert state == {"attempted": True, "blocked": True, "restored": False}
    assert target.read_bytes() == original_raw
    if loaded is not None:
        assert loaded.raw == original_raw
    after_load = release_root / "config-after-load"
    config.rename(after_load)
    after_load.rename(config)


@pytest.mark.skipif(os.name != "nt", reason="Windows directory sharing semantics")
def test_windows_production_load_releases_config_handle_after_child_open_error(
    tmp_path,
    monkeypatch,
):
    release_root = tmp_path / "release"
    config = release_root / "config"
    config.mkdir(parents=True)
    target = config / "artifact.json"
    target.write_bytes(b'{"source": "open-error"}')
    during_open = release_root / "config-during-open"
    original_open = os.open
    state = {"attempted": False, "blocked": False}

    def failing_open(path, flags, *args, **kwargs):
        if Path(path).name == target.name and not state["attempted"]:
            state["attempted"] = True
            try:
                config.rename(during_open)
            except PermissionError:
                state["blocked"] = True
            else:
                during_open.rename(config)
            raise PermissionError("synthetic child open failure")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(launch_artifacts.os, "open", failing_open)

    with pytest.raises(ValueError, match="identity changed before open"):
        load_artifact("artifact.json", release_root=release_root)

    assert state == {"attempted": True, "blocked": True}
    after_error = release_root / "config-after-error"
    config.rename(after_error)
    after_error.rename(config)


def test_load_artifact_closes_config_descriptor_when_fstat_fails(tmp_path, monkeypatch):
    target = tmp_path / "config" / "artifact.json"
    target.parent.mkdir()
    target.write_bytes(b'{"source": "descriptor-error"}')
    descriptor = 731
    closed = []

    monkeypatch.setattr(launch_artifacts, "_directory_fd_supported", lambda: True)
    monkeypatch.setattr(launch_artifacts.os, "O_DIRECTORY", 0, raising=False)
    monkeypatch.setattr(launch_artifacts.os, "open", lambda *_args, **_kwargs: descriptor)

    def failed_fstat(_descriptor):
        raise OSError("synthetic fstat failure")

    monkeypatch.setattr(launch_artifacts.os, "fstat", failed_fstat)
    monkeypatch.setattr(launch_artifacts.os, "close", closed.append)

    with pytest.raises(OSError, match="synthetic fstat failure"):
        load_artifact("artifact.json", release_root=tmp_path)

    assert closed == [descriptor]


def test_file_identity_detects_metadata_change_when_inode_is_stable(tmp_path):
    target = tmp_path / "artifact.json"
    target.write_bytes(b'{"source": "identity"}')
    before = os.stat(target)
    os.utime(
        target,
        ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000),
    )
    after = os.stat(target)

    assert launch_artifacts._file_identity(before) != launch_artifacts._file_identity(after)


def test_file_identity_includes_filesystem_link_count(tmp_path):
    target = tmp_path / "artifact.json"
    target.write_bytes(b'{"source": "identity"}')
    before = os.stat(target)
    try:
        os.link(target, tmp_path / "alias.json")
    except OSError as exc:
        pytest.skip(f"hardlink creation unavailable: {exc}")
    after = os.stat(target)

    assert before.st_nlink == 1
    assert after.st_nlink > 1
    assert launch_artifacts._file_identity(before) != launch_artifacts._file_identity(after)


def test_file_identity_includes_windows_reparse_metadata(tmp_path):
    target = tmp_path / "artifact.json"
    target.write_bytes(b'{"source": "identity"}')
    regular = os.stat(target)
    reparse = ReparsePointStat(regular)

    assert launch_artifacts._file_identity(regular) != launch_artifacts._file_identity(
        reparse
    )


@pytest.mark.parametrize("name", ["../outside.json", "nested/artifact.json"])
def test_load_artifact_rejects_production_name_path_traversal(tmp_path, name):
    (tmp_path / "config").mkdir()
    (tmp_path / "outside.json").write_bytes(b'{"source": "outside"}')

    with pytest.raises(ValueError, match="artifact name"):
        load_artifact(name, release_root=tmp_path)


def test_load_artifact_rejects_an_absolute_production_name(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_bytes(b'{"source": "outside"}')

    with pytest.raises(ValueError, match="artifact name"):
        load_artifact(str(outside), release_root=tmp_path / "release")


@pytest.mark.parametrize(
    "name",
    [
        "host.json:secret",
        "host.json.",
        "host.json ",
        "host<name>.json",
        'host"name.json',
        "host|name.json",
        "host?name.json",
        "host*name.json",
        "host\x01name.json",
        "CON",
        "nul.json",
        "COM1.txt",
        "lpt9.JSON",
    ],
    ids=[
        "alternate-data-stream",
        "trailing-dot",
        "trailing-space",
        "angle-bracket",
        "quote",
        "pipe",
        "question-mark",
        "asterisk",
        "control-character",
        "reserved-con",
        "reserved-nul",
        "reserved-com1",
        "reserved-lpt9",
    ],
)
def test_load_artifact_rejects_windows_invalid_production_names_before_read(tmp_path, name):
    with pytest.raises(ValueError, match="artifact name"):
        load_artifact(name, release_root=tmp_path)


@pytest.mark.parametrize(
    "name",
    [
        "CON .json",
        "COM\u00b9.json",
        "LPT\u00b3.txt",
        "CON.json",
        "NUL",
        "AUX.txt",
        "COM1",
        "LPT9",
        "cOn .JsOn",
        "com\u00b2 .json",
        "lPt\u00b3..txt",
    ],
    ids=[
        "con-stem-space",
        "com-superscript-one",
        "lpt-superscript-three",
        "con-extension",
        "nul",
        "aux-extension",
        "com1",
        "lpt9",
        "mixed-case-stem-space",
        "superscript-stem-space",
        "mixed-case-stem-dot",
    ],
)
@pytest.mark.parametrize("source", ["production", "fixture"])
def test_load_artifact_rejects_reserved_names_before_any_read(
    tmp_path,
    monkeypatch,
    name,
    source,
):
    reads = []

    def forbidden_read(path):
        reads.append(path)
        pytest.fail("reserved artifact name reached file I/O")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    kwargs = (
        {"release_root": tmp_path}
        if source == "production"
        else {"fixture_path": tmp_path / "fixture.json"}
    )

    with pytest.raises(ValueError, match="artifact name"):
        load_artifact(name, **kwargs)

    assert reads == []


@pytest.mark.parametrize("name", ["launch-indexing-policy.json", "ai-disclosure.json"])
def test_load_artifact_accepts_canonical_production_names(tmp_path, name):
    target = tmp_path / "config" / name
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(b'{"valid": true}')

    assert load_artifact(name, release_root=tmp_path).path == target


def test_load_artifact_defaults_to_repository_release_root():
    loaded = load_artifact("launch-indexing-policy.json")

    assert loaded.path == REPO_ROOT / "config" / "launch-indexing-policy.json"
    assert loaded.raw == loaded.path.read_bytes()
    assert loaded.data["revision"] == "launch-indexing-policy-v1"


@pytest.mark.parametrize(
    "raw",
    [
        b'{"outer": 1, "outer": 2}',
        b'{"outer": {"nested": 1, "nested": 2}}',
        b'{"items": [{"key": 1, "key": 2}]}',
    ],
    ids=["root", "nested-object", "array-object"],
)
def test_load_artifact_rejects_duplicate_object_keys(tmp_path, raw):
    fixture = tmp_path / "duplicate.json"
    fixture.write_bytes(raw)

    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_artifact("ignored.json", fixture_path=fixture)


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"-Infinity"])
def test_load_artifact_rejects_non_finite_json_numbers(tmp_path, constant):
    fixture = tmp_path / "constant.json"
    fixture.write_bytes(b'{"value": ' + constant + b"}")

    with pytest.raises(ValueError, match="non-finite JSON number"):
        load_artifact("ignored.json", fixture_path=fixture)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"value": 1e9999}',
        b'{"value": -1e9999}',
        b'{"nested": {"value": 1e9999}}',
        b'{"items": [{"value": -1e9999}]}',
    ],
    ids=["positive-root-value", "negative-root-value", "nested-object", "nested-array"],
)
def test_load_artifact_rejects_overflowed_non_finite_json_numbers(tmp_path, raw):
    fixture = tmp_path / "overflow.json"
    fixture.write_bytes(raw)

    with pytest.raises(ValueError, match="non-finite JSON number"):
        load_artifact("ignored.json", fixture_path=fixture)


def test_load_artifact_preserves_finite_json_numbers(tmp_path):
    fixture = tmp_path / "finite.json"
    fixture.write_bytes(b'{"fraction": 1.25, "exponent": -1e200}')

    loaded = load_artifact("ignored.json", fixture_path=fixture)

    assert loaded.data == {"fraction": 1.25, "exponent": -1e200}


@pytest.mark.parametrize("raw", [b"[]", b"null", b'"value"', b"1", b"true"])
def test_load_artifact_requires_a_json_object(tmp_path, raw):
    fixture = tmp_path / "non-object.json"
    fixture.write_bytes(raw)

    with pytest.raises(ValueError, match="JSON object"):
        load_artifact("ignored.json", fixture_path=fixture)


@pytest.mark.parametrize(
    "raw, message",
    [(b'{"value": "\xff"}', "UTF-8"), (b'{"value": }', "JSON")],
)
def test_load_artifact_wraps_invalid_utf8_and_json_clearly(tmp_path, raw, message):
    fixture = tmp_path / "invalid.json"
    fixture.write_bytes(raw)

    with pytest.raises(ValueError, match=message):
        load_artifact("ignored.json", fixture_path=fixture)
