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


def _sequence_runner(responses, calls):
    pending = list(responses)

    def fn(cmd):
        calls.append(cmd)
        code, out = pending.pop(0)
        return types.SimpleNamespace(returncode=code, stdout=out, stderr="")

    return fn


def test_standards_hard_fail_is_required():
    runner = _sequence_runner([(0, "coverage ready"), (1, "✖ HARD R70.1")], [])
    issues = pmc.check_standards_hard([], runner=runner)
    assert issues and "REQUIRED" in issues[0]


def test_standards_hard_clean():
    assert pmc.check_standards_hard([], runner=_mock_runner(0, "✓")) == []


def test_standards_hard_generates_coverage_before_gate():
    calls = []
    runner = _sequence_runner([(0, "coverage ready"), (0, "clean")], calls)

    assert pmc.check_standards_hard([], runner=runner) == []
    assert calls[0][:3] == [sys.executable, "-m", "pytest"]
    assert "--cov-report=json:coverage.json" in calls[0]
    assert "--ignore=tests/launch_safety/test_closed_installer.py" in calls[0]
    assert calls[1] == [sys.executable, "scripts/checks/run_hard.py", "--all"]


def test_standards_hard_fails_when_coverage_generation_fails():
    issues = pmc.check_standards_hard([], runner=_mock_runner(1, "coverage failed"))
    assert issues and "coverage" in issues[0].lower() and "REQUIRED" in issues[0]


def test_scorecard_regression_fail():
    issues = pmc.check_scorecard([], runner=_mock_runner(1, "TỤT ĐIỂM: data 80 → 60"))
    assert issues and "REQUIRED" in issues[0]


def test_scorecard_clean():
    assert pmc.check_scorecard([], runner=_mock_runner(0, "")) == []
