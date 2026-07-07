# -*- coding: utf-8 -*-
"""Test scorecard (SP01 T7)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import scorecard  # noqa: E402
from checks import common  # noqa: E402


def _chk(tmp_path, rule, text_file, pattern="BAD"):
    return common.RegexCheck(name=rule, level="soft-ratchet", rule=rule, patterns=[pattern],
                             globs=["*.md"], roots=["docs"], root=tmp_path)


def _mk(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_scores_formula():
    cur = {"data": 5, "docs": 0, "content": None}
    origin = {"data": 10, "docs": 0, "content": 0}
    s = scorecard.scores(cur, origin)
    assert s["data"] == 50 and s["docs"] == 100 and s["content"] is None


def test_first_run_appends_history_and_origin_freeze(tmp_path):
    _mk(tmp_path, "docs/a.md", "BAD\nBAD\n")
    checks = [_chk(tmp_path, "R10.7", "docs/a.md")]
    code, out = scorecard.run(checks, tmp_path, append=True)
    assert code == 0  # không hard, không entry trước → không tụt
    hist = scorecard.load_history(tmp_path)
    assert len(hist) == 1 and hist[0]["dim_debts"]["data"] == 2
    # lần 2: nợ giảm còn 1 → điểm tăng, không tụt
    _mk(tmp_path, "docs/a.md", "BAD\n")
    code2, out2 = scorecard.run(checks, tmp_path, append=True)
    assert code2 == 0 and out2["entry"]["scores"]["data"] == 50


def test_regression_exits_nonzero(tmp_path):
    _mk(tmp_path, "docs/a.md", "BAD\n")
    checks = [_chk(tmp_path, "R10.7", "docs/a.md")]
    scorecard.run(checks, tmp_path, append=True)          # gốc: nợ 1 → điểm 0
    _mk(tmp_path, "docs/a.md", "")                        # trả hết nợ
    scorecard.run(checks, tmp_path, append=True)          # điểm 100
    _mk(tmp_path, "docs/a.md", "BAD\n")                   # tái nhiễm
    code, out = scorecard.run(checks, tmp_path, append=False)
    assert code == 1 and out["regressions"]


def test_hard_violation_exits_nonzero(tmp_path):
    _mk(tmp_path, "docs/a.md", "BAD\n")
    hard = common.RegexCheck(name="h", level="hard", rule="R70.1", patterns=["BAD"],
                             globs=["*.md"], roots=["docs"], root=tmp_path)
    code, out = scorecard.run([hard], tmp_path, append=False)
    assert code == 1 and out["entry"]["hard_violations"] == 1
