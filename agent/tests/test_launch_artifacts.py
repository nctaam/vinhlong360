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
