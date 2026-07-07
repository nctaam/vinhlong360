# -*- coding: utf-8 -*-
"""Test 3 bước mở rộng pre_merge_check (SP01 T8) — mock runner, không đụng repo thật."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pre_merge_check as pmc  # noqa: E402


def _mock_runner(code, out=""):
    def fn(cmd):
        return types.SimpleNamespace(returncode=code, stdout=out, stderr="")
    return fn


def test_standards_hard_fail_is_required():
    issues = pmc.check_standards_hard([], runner=_mock_runner(1, "✖ HARD R70.1"))
    assert issues and "REQUIRED" in issues[0]


def test_standards_hard_clean():
    assert pmc.check_standards_hard([], runner=_mock_runner(0, "✓")) == []


def test_scorecard_regression_fail():
    issues = pmc.check_scorecard([], runner=_mock_runner(1, "TỤT ĐIỂM: data 80 → 60"))
    assert issues and "REQUIRED" in issues[0]


def test_scorecard_clean():
    assert pmc.check_scorecard([], runner=_mock_runner(0, "")) == []
