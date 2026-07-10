# -*- coding: utf-8 -*-
"""Test scripts/checks/common.py — nền RegexCheck + ratchet (SP01 T1)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks import common  # noqa: E402


def _mk(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_regexcheck_catches_pattern_and_reports_line(tmp_path):
    _mk(tmp_path, "docs/a.md", "dòng sạch\nảnh lấy từ Wikimedia nhé\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"],
        msg="nguồn ảnh cấm", root=tmp_path,
    )
    r = chk.run()
    assert r["count"] == 1
    v = r["violations"][0]
    assert v["file"].endswith("a.md") and v["line"] == 2 and v["rule"] == "R50.1"


def test_regexcheck_neg_context_skips_warning_lines(tmp_path):
    _mk(tmp_path, "docs/a.md", "KHÔNG dùng Wikimedia (nguồn cấm)\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"], root=tmp_path,
    )
    assert chk.run()["count"] == 0


def test_regexcheck_exclude_paths(tmp_path):
    _mk(tmp_path, "docs/archive/old.md", "Wikimedia\n")
    _mk(tmp_path, "docs/live.md", "Wikimedia\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"],
        exclude_paths=["docs/archive"], root=tmp_path,
    )
    r = chk.run()
    assert r["count"] == 1 and r["violations"][0]["file"].endswith("live.md")


def test_regexcheck_staged_mode_only_scans_given_files(tmp_path):
    _mk(tmp_path, "docs/a.md", "Wikimedia\n")
    _mk(tmp_path, "docs/b.md", "Wikimedia\n")
    chk = common.RegexCheck(
        name="banned", level="hard", rule="R50.1",
        patterns=[r"Wikimedia"], globs=["*.md"], roots=["docs"], root=tmp_path,
    )
    r = chk.run(files=["docs/a.md"])
    assert r["count"] == 1
    # file ngoài globs/roots bị lọc
    assert chk.run(files=["src/x.py"])["count"] == 0


def test_ratchet_blocks_increase_allows_equal_and_decrease(tmp_path):
    baseline = {"R10.7": 2}
    res_inc = [{"check": "tinh_cu", "level": "hard-ratchet", "rule": "R10.7", "count": 3, "violations": []}]
    res_eq = [{"check": "tinh_cu", "level": "hard-ratchet", "rule": "R10.7", "count": 2, "violations": []}]
    res_dec = [{"check": "tinh_cu", "level": "hard-ratchet", "rule": "R10.7", "count": 1, "violations": []}]
    blockers, _ = common.ratchet_violations(res_inc, baseline)
    assert len(blockers) == 1 and "R10.7" in blockers[0]
    assert common.ratchet_violations(res_eq, baseline)[0] == []
    blockers, suggestions = common.ratchet_violations(res_dec, baseline)
    assert blockers == [] and len(suggestions) == 1  # đề nghị hạ baseline


def test_ratchet_ignores_plain_hard_and_soft(tmp_path):
    baseline = {}
    res = [
        {"check": "secrets", "level": "hard", "rule": "R70.1", "count": 5, "violations": []},
        {"check": "thin", "level": "soft", "rule": "R50.4", "count": 9, "violations": []},
    ]
    blockers, suggestions = common.ratchet_violations(res, baseline)
    assert blockers == [] and suggestions == []


def test_baseline_io_roundtrip(tmp_path):
    (tmp_path / "docs" / "standards").mkdir(parents=True)
    common.save_baseline({"R10.7": 87, "R30.3": 12}, root=tmp_path)
    b = common.load_baseline(root=tmp_path)
    assert b == {"R10.7": 87, "R30.3": 12}


def test_load_baseline_missing_returns_empty(tmp_path):
    assert common.load_baseline(root=tmp_path) == {}
