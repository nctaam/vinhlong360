# -*- coding: utf-8 -*-
"""SP4 — R30.7 bundle + R30.6 axe (pending-check kích hoạt, graceful-skip)."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_axe import AxeCheck  # noqa: E402
from checks.check_bundle import BundleCheck  # noqa: E402


# ── R30.7 bundle ──────────────────────────────────────────────────────
def _mk_chunk(tmp_path: Path, name: str, kb: int):
    d = tmp_path / "web-nuxt" / ".output" / "public" / "_nuxt"
    d.mkdir(parents=True, exist_ok=True)
    # os.urandom = KHÓ NÉN → gz size ≈ raw size (kb thật sau gz)
    (d / name).write_bytes(os.urandom(kb * 1024))


def test_bundle_skip_when_no_output(tmp_path):
    assert BundleCheck(root=tmp_path).run()["count"] == 0


def test_bundle_flags_oversized_chunk(tmp_path):
    _mk_chunk(tmp_path, "huge.js", 400)  # gz sẽ > 280kB
    (tmp_path / "docs" / "standards").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "standards" / "bundle-budget.json").write_text(
        json.dumps({"total_gz_kb": 300, "max_chunk_gz_kb": 280, "entry_target_gz_kb": 200}),
        encoding="utf-8")
    r = BundleCheck(root=tmp_path).run()
    assert r["count"] >= 1
    assert any("chunk lớn nhất" in v["msg"] for v in r["violations"])


def test_bundle_passes_under_budget(tmp_path):
    _mk_chunk(tmp_path, "small.js", 5)
    (tmp_path / "docs" / "standards").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "standards" / "bundle-budget.json").write_text(
        json.dumps({"total_gz_kb": 800, "max_chunk_gz_kb": 280, "entry_target_gz_kb": 200}),
        encoding="utf-8")
    assert BundleCheck(root=tmp_path).run()["count"] == 0


# ── R30.6 axe ─────────────────────────────────────────────────────────
def test_axe_skip_when_no_report(tmp_path):
    assert AxeCheck(root=tmp_path).run()["count"] == 0


def test_axe_flags_serious_and_critical_only(tmp_path):
    report = [
        {"url": "/", "violations": [
            {"impact": "serious", "id": "color-contrast", "nodes": [1, 2]},
            {"impact": "minor", "id": "landmark", "nodes": [1]},
        ]},
        {"url": "/x", "violations": [{"impact": "critical", "id": "aria", "nodes": [1]}]},
    ]
    (tmp_path / "axe-report.json").write_text(json.dumps(report), encoding="utf-8")
    r = AxeCheck(root=tmp_path).run()
    assert r["count"] == 2  # serious + critical; minor bỏ qua


def test_axe_clean_report_passes(tmp_path):
    (tmp_path / "axe-report.json").write_text(
        json.dumps({"violations": [{"impact": "moderate", "id": "x", "nodes": [1]}]}),
        encoding="utf-8")
    assert AxeCheck(root=tmp_path).run()["count"] == 0
