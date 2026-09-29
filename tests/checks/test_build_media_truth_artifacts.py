from __future__ import annotations

import importlib.util
from pathlib import Path


def test_bundle_builder_exposes_candidate_path_api() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/checks/build_media_truth_artifacts.py"
    spec = importlib.util.spec_from_file_location("build_media_truth_artifacts", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert callable(module.build_candidate_artifacts)
