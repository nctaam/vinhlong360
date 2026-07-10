# -*- coding: utf-8 -*-
"""Test scorecard (SP01 T7)."""
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


def test_new_rule_widens_origin_instead_of_zeroing_score(tmp_path):
    """SP2: bật gate mới (nợ>0) KHÔNG được đánh sập điểm về 0 — nợ gốc của
    rule = entry đầu tiên rule xuất hiện trong history (mốc ban hành per-rule)."""
    _mk(tmp_path, "docs/a.md", "BAD\nBAD\n")
    old_rule = _chk(tmp_path, "R10.7", "docs/a.md")           # nợ gốc 2
    scorecard.run([old_rule], tmp_path, append=True)
    # trả hết nợ cũ + bật rule mới với nợ 3
    _mk(tmp_path, "docs/a.md", "NEW\nNEW\nNEW\n")
    new_rule = common.RegexCheck(name="n", level="hard-ratchet", rule="R10.3b", patterns=["NEW"],
                                 globs=["*.md"], roots=["docs"], root=tmp_path)
    code, out = scorecard.run([old_rule, new_rule], tmp_path, append=True)
    # origin data = 2 (R10.7 first-seen) + 3 (R10.3b first-seen hôm nay) = 5; nợ hiện 3
    assert out["entry"]["scores"]["data"] == 40  # 100×(1−3/5) — KHÔNG phải 0
    assert code == 0  # 0 → 40 là tăng, không tụt
    # lần sau trả 1 nợ mới → điểm tăng tiếp, origin R10.3b vẫn 3
    _mk(tmp_path, "docs/a.md", "NEW\nNEW\n")
    _, out2 = scorecard.run([old_rule, new_rule], tmp_path, append=True)
    assert out2["entry"]["scores"]["data"] == 60


def test_hard_violation_exits_nonzero(tmp_path):
    _mk(tmp_path, "docs/a.md", "BAD\n")
    hard = common.RegexCheck(name="h", level="hard", rule="R70.1", patterns=["BAD"],
                             globs=["*.md"], roots=["docs"], root=tmp_path)
    code, out = scorecard.run([hard], tmp_path, append=False)
    assert code == 1 and out["entry"]["hard_violations"] == 1
