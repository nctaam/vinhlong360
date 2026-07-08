# -*- coding: utf-8 -*-
"""Test check_coverage (R20.4) — graceful-skip khi vắng coverage.json + ngưỡng."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_coverage import CoverageCheck  # noqa: E402


def _write(tmp_path, cov: dict, thr: dict):
    (tmp_path / "coverage.json").write_text(json.dumps(cov), encoding="utf-8")
    d = tmp_path / "docs" / "standards"
    d.mkdir(parents=True, exist_ok=True)
    (d / "coverage-thresholds.json").write_text(json.dumps(thr), encoding="utf-8")


def test_level_rule():
    c = CoverageCheck()
    assert c.level == "soft-ratchet" and c.rule == "R20.4"


def test_skip_when_no_coverage_json(tmp_path):
    # Không có coverage.json → count 0 (hook staged không chặn).
    assert CoverageCheck(root=tmp_path).run()["count"] == 0


def test_below_thresholds_flagged(tmp_path):
    cov = {
        "totals": {"percent_covered": 51.0},
        "files": {
            "agent/database.py": {"summary": {"percent_covered": 78.0}},
            "agent/auth.py": {"summary": {"percent_covered": 25.0}},
        },
    }
    thr = {"agent": 60, "core": {"database.py": 80, "auth.py": 80}}
    _write(tmp_path, cov, thr)
    r = CoverageCheck(root=tmp_path).run()
    # agent 51<60, database 78<80, auth 25<80 → 3 vi phạm
    assert r["count"] == 3


def test_meets_thresholds_pass(tmp_path):
    cov = {
        "totals": {"percent_covered": 61.0},
        "files": {"agent/database.py": {"summary": {"percent_covered": 81.0}}},
    }
    thr = {"agent": 60, "core": {"database.py": 80}}
    _write(tmp_path, cov, thr)
    assert CoverageCheck(root=tmp_path).run()["count"] == 0


def test_sibling_basename_does_not_shadow_core_module(tmp_path):
    # Regression: mcp_server.py (0%) KHÔNG được che server.py (21.5%) — bug _pct
    # endswith lỏng trả nhầm 0% → false-positive vi phạm. Basename phải khớp CHÍNH XÁC.
    cov = {
        "totals": {"percent_covered": 61.0},
        "files": {
            "agent/mcp_server.py": {"summary": {"percent_covered": 0.0}},
            "agent/server.py": {"summary": {"percent_covered": 21.5}},
        },
    }
    thr = {"agent": 60, "core": {"server.py": 20}}
    _write(tmp_path, cov, thr)
    # server.py 21.5% > 20% → KHÔNG vi phạm (nếu _pct che nhầm mcp_server 0% → sẽ fail)
    assert CoverageCheck(root=tmp_path).run()["count"] == 0
