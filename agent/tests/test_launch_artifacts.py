import hashlib
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from launch_artifacts import load_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_load_artifact_reads_the_source_once(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture.json"
    fixture.write_bytes(b'{"value": 1}')
    original_read_bytes = Path.read_bytes
    calls = []

    def counted_read_bytes(path):
        calls.append(path)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)

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
