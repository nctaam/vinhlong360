from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path


def test_bundle_builder_exposes_candidate_path_api() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/checks/build_media_truth_artifacts.py"
    spec = importlib.util.spec_from_file_location("build_media_truth_artifacts", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert callable(module.build_candidate_artifacts)


def test_bundle_builder_fails_closed_on_manifest_error(tmp_path: Path, monkeypatch) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/checks/build_media_truth_artifacts.py"
    spec = importlib.util.spec_from_file_location("build_media_truth_artifacts_fail_closed", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "data.json").write_text('{"entities": []}', encoding="utf-8")
    with sqlite3.connect(candidate / "candidate.db") as conn:
        conn.execute("CREATE TABLE entities (id TEXT)")
    truth = tmp_path / "truth.json"
    truth.write_text('{}', encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    ledger.write_text('{}', encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text('{}', encoding="utf-8")
    monkeypatch.setattr(module.build_data_review_manifest, "build_manifest", lambda *_: (_ for _ in ()).throw(ValueError("incomplete")))
    import pytest
    with pytest.raises(ValueError, match="incomplete"):
        module.build_candidate_artifacts(candidate, tmp_path / "out", truth_manifest=truth, batch_ledger=ledger, renderer_registry=registry)
