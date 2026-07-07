# -*- coding: utf-8 -*-
"""Test run_hard runner (SP01 T6) — chặn hard, ratchet, skip-soft-only, thời gian <5s."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks import common, run_hard  # noqa: E402


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _hard_check(tmp_path, count_file=True):
    return common.RegexCheck(name="h", level="hard", rule="RX.1", patterns=[r"BAD"],
                             globs=["*.md"], roots=["docs"], root=tmp_path)


def _soft_ratchet_check(tmp_path):
    return common.RegexCheck(name="s", level="soft-ratchet", rule="RX.2", patterns=[r"MEH"],
                             globs=["*.md"], roots=["docs"], root=tmp_path)


def test_hard_violation_blocks(tmp_path):
    _mk(tmp_path, "docs/a.md", "BAD\n")
    code, msgs = run_hard.run(None, checks=[_hard_check(tmp_path)], root=tmp_path, baseline={}, skips=set())
    assert code == 1 and any("HARD RX.1" in m for m in msgs)


def test_ratchet_increase_blocks_equal_passes(tmp_path):
    _mk(tmp_path, "docs/a.md", "MEH\nMEH\n")
    chk = _soft_ratchet_check(tmp_path)
    code, _ = run_hard.run(None, checks=[chk], root=tmp_path, baseline={"RX.2": 1}, skips=set())
    assert code == 1
    code, _ = run_hard.run(None, checks=[chk], root=tmp_path, baseline={"RX.2": 2}, skips=set())
    assert code == 0


def test_skip_applies_only_to_soft(tmp_path):
    _mk(tmp_path, "docs/a.md", "MEH\nMEH\n")
    chk = _soft_ratchet_check(tmp_path)
    code, msgs = run_hard.run(None, checks=[chk], root=tmp_path, baseline={"RX.2": 0}, skips={"RX.2"})
    assert code == 0 and any("SKIPPED" in m for m in msgs)
    # hard-ratchet không skip được
    hr = common.RegexCheck(name="hr", level="hard-ratchet", rule="RX.3", patterns=[r"MEH"],
                           globs=["*.md"], roots=["docs"], root=tmp_path)
    code, _ = run_hard.run(None, checks=[hr], root=tmp_path, baseline={"RX.3": 0}, skips={"RX.3"})
    assert code == 1


def test_registry_has_all_14_checks():
    assert len(run_hard.ALL_CHECKS) == 23  # 14 module → 23 check (banned=3, schema=3, fe=2, voice=2, complexity=2, content_gates=2, ruff=2; R10.10 pending)
    rules = {c.rule for c in run_hard.ALL_CHECKS}
    for r in ["R70.1", "R40.3", "R10.6", "R30.1", "R10.schema", "R20.5",
              "R10.7", "R30.3", "R30.2", "R60.1", "R60.4", "R50.2", "R10.9",
              "R50.4", "R20.7", "R20.8", "R20.3", "R10.3b", "R10.8",
              "R50.3", "R50.7", "R20.1", "R20.2"]:
        assert r in rules, r


def test_hook_budget_under_5s(tmp_path):
    for i in range(20):
        _mk(tmp_path, f"docs/f{i}.md", "nội dung sạch\n" * 50)
    checks = [_hard_check(tmp_path), _soft_ratchet_check(tmp_path)]
    t0 = time.time()
    run_hard.run([f"docs/f{i}.md" for i in range(20)], checks=checks, root=tmp_path, baseline={}, skips=set())
    assert time.time() - t0 < 5.0
