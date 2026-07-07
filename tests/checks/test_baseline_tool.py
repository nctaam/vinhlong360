# -*- coding: utf-8 -*-
"""Test baseline_tool (SP01 T2)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks import baseline_tool, common  # noqa: E402


def _mk_checks(tmp_path):
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "a.md").write_text("Wikimedia\nWikimedia\n", encoding="utf-8")
    c1 = common.RegexCheck(name="banned", level="hard-ratchet", rule="R50.1",
                           patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"], root=tmp_path)
    c2 = common.RegexCheck(name="clean", level="soft-ratchet", rule="R60.1",
                           patterns=[r"KHONG_CO"], globs=["*.md"], roots=["docs"], root=tmp_path)
    return [c1, c2]


def test_collect_counts(tmp_path):
    counts = baseline_tool.collect(_mk_checks(tmp_path))
    assert counts == {"R50.1": 2, "R60.1": 0}


def test_write_baseline(tmp_path):
    checks = _mk_checks(tmp_path)
    baseline_tool.run(checks, root=tmp_path, write=True)
    b = json.loads((tmp_path / "docs" / "standards" / "baseline.json").read_text(encoding="utf-8"))
    assert b == {"R50.1": 2, "R60.1": 0}


def test_no_write_does_not_touch_disk(tmp_path):
    checks = _mk_checks(tmp_path)
    baseline_tool.run(checks, root=tmp_path, write=False)
    assert not (tmp_path / "docs" / "standards" / "baseline.json").exists()
