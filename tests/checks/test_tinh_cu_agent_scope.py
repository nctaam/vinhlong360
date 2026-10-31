# -*- coding: utf-8 -*-
"""Regression tests for Wave 14.2 (QW-42):
TinhCuCheck (R10.7) expanded to scan agent/**/*.py and catch uncontextualized
3-province listings ("Vĩnh Long, Bến Tre, Trà Vinh") without post-7/2025 context.
"""
from __future__ import annotations

from pathlib import Path
from scripts.checks.check_tinh_cu import TinhCuCheck


def test_tinh_cu_check_scans_agent_python_files(tmp_path: Path):
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir(parents=True)
    bad_py = agent_dir / "sample.py"
    bad_py.write_text(
        'reply = "Bạn thử hỏi ở Vĩnh Long, Bến Tre, Trà Vinh nhé!"\n',
        encoding="utf-8",
    )
    res = TinhCuCheck(root=tmp_path).run()
    assert res["count"] == 1
    assert res["violations"][0]["file"] == "agent/sample.py"


def test_tinh_cu_check_allows_historical_context_in_agent(tmp_path: Path):
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir(parents=True)
    ok_py = agent_dir / "sample_ok.py"
    ok_py.write_text(
        'title = "Toàn tỉnh Vĩnh Long (gồm vùng Vĩnh Long, Bến Tre, Trà Vinh trước 7-2025)"\n',
        encoding="utf-8",
    )
    res = TinhCuCheck(root=tmp_path).run()
    assert res["count"] == 0


def test_production_repo_has_zero_tinh_cu_violations():
    res = TinhCuCheck().run()
    assert res["count"] == 0, f"Unexpected R10.7 violations: {res['violations']}"
