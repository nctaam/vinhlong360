from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts" / "ops" / "verify_closed_release.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "task5_verify_closed_release_complexity", VERIFY
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {VERIFY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_findmnt_option_normalization_preserves_raw_values():
    verifier = _load_verifier()

    assert verifier._normalize_findmnt_options(["rw", "bind", ""]) == {
        "rw",
        "bind",
    }
    assert verifier._normalize_findmnt_options("rw,bind,") == {"rw", "bind"}
    assert verifier._normalize_findmnt_options(None) == set()


def test_findmnt_source_validation_accepts_expected_and_proves_bracketed_bind(
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = _load_verifier()
    expected = Path("/authority").resolve()

    assert verifier._validate_findmnt_source(str(expected), expected) is False
    monkeypatch.setattr(
        verifier,
        "_findmnt_device_matches_source",
        lambda device, source: device == "/dev/loop0" and source == expected,
    )
    assert verifier._validate_findmnt_source("/dev/loop0[/authority]", expected) is True


def test_findmnt_source_validation_rejects_unproven_bracketed_bind():
    verifier = _load_verifier()
    expected = Path("/authority").resolve()

    with pytest.raises(ValueError, match="source device"):
        verifier._validate_findmnt_source("/dev/loop0[/authority]", expected)


def test_fingerprint_file_streams_size_and_digest(tmp_path: Path):
    verifier = _load_verifier()
    payload = b"closed-release\n" * 100
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(payload)

    size, digest = verifier._fingerprint_file(artifact)

    assert size == len(payload)
    assert digest == verifier._sha256(payload)
