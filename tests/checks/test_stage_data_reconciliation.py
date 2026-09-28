from __future__ import annotations

from pathlib import Path

import pytest

from scripts.checks.build_media_truth_plan import build_plan
from scripts.checks.stage_data_reconciliation import StageError, stage_plan


ROOT = Path(__file__).resolve().parents[2]


def _plan():
    return build_plan(ROOT, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "docs/standards/batch-21-media-truth.json")


def test_stage_refuses_protected_outputs(tmp_path):
    with pytest.raises(StageError, match="protected"):
        stage_plan(_plan(), ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "web-nuxt/public/img/entities", ROOT)


def test_stage_creates_owned_candidate(tmp_path):
    result = stage_plan(_plan(), ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "web-nuxt/public/img/entities", tmp_path / "stage")
    candidate = result.output_dir / "candidate"
    assert (candidate / "vinhlong360.db").is_file()
    assert (candidate / "data.json").is_file()
    assert (candidate / "stage-result.json").is_file()
    assert not (candidate / "public/img/entities/prov-1.webp").exists()
    source_count = sum(1 for path in (ROOT / "web-nuxt/public/img/entities").rglob("*") if path.is_file())
    assert len(result.stage_result["assets"]["retained"]) == source_count - 1
    assert result.stage_result["assets"]["removed"] == [
        {
            "id": "prov-1",
            "path": "prov-1.webp",
            "sha256": _plan()["affectedAssets"]["prov-1"]["sha256"],
        }
    ]


def test_stage_is_byte_deterministic(tmp_path):
    plan = _plan()
    args = (plan, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "web-nuxt/public/img/entities")
    first = stage_plan(*args, tmp_path / "first")
    second = stage_plan(*args, tmp_path / "second")
    assert first.plan_bytes == second.plan_bytes
    assert first.json_bytes == second.json_bytes
    assert first.logical_sqlite_digest == second.logical_sqlite_digest
    assert first.stage_result == second.stage_result


def test_stage_refuses_sqlite_sidecars(tmp_path):
    sqlite_copy = tmp_path / "source.db"
    sqlite_copy.write_bytes((ROOT / "agent/data/vinhlong360.db").read_bytes())
    Path(f"{sqlite_copy}-wal").write_bytes(b"live")
    with pytest.raises(StageError, match="sidecar"):
        stage_plan(
            _plan(),
            sqlite_copy,
            ROOT / "web/data.json",
            ROOT / "web-nuxt/public/img/entities",
            tmp_path / "stage",
        )
