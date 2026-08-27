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


def test_run_binds_supplied_root_to_checks(tmp_path, monkeypatch):
    _mk(tmp_path, "docs/a.md", "BAD\n")
    check = common.RegexCheck(
        name="h", level="hard", rule="RX.1", patterns=[r"BAD"],
        globs=["*.md"], roots=["docs"],
    )

    def unexpected_repo_root():
        raise AssertionError("check resolved repo root instead of using runner root")

    monkeypatch.setattr(common, "repo_root", unexpected_repo_root)
    code, msgs = run_hard.run(
        None, checks=[check], root=tmp_path, baseline={}, skips=set(),
    )

    assert code == 1 and any("HARD RX.1" in message for message in msgs)
    assert check._root is None


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


def test_registry_has_all_checks():
    assert len(run_hard.ALL_CHECKS) == 30
    rules = {c.rule for c in run_hard.ALL_CHECKS}
    for r in ["R70.1", "R40.3", "R10.6", "R30.1", "R10.schema", "R20.5",
              "R10.7", "R30.3", "R30.2", "R60.1", "R60.4", "R50.2", "R10.9",
              "R50.4", "R20.7", "R20.8", "R20.3", "R10.3b", "R10.8",
              "R50.3", "R50.7", "R20.1", "R20.2", "R20.4", "R30.6", "R30.7",
              "R20.9", "R20.10", "R20.5b", "R30.8"]:
        assert r in rules, r


def test_hook_budget_under_5s(tmp_path):
    for i in range(20):
        _mk(tmp_path, f"docs/f{i}.md", "nội dung sạch\n" * 50)
    checks = [_hard_check(tmp_path), _soft_ratchet_check(tmp_path)]
    t0 = time.time()
    run_hard.run([f"docs/f{i}.md" for i in range(20)], checks=checks, root=tmp_path, baseline={}, skips=set())
    assert time.time() - t0 < 5.0


# ─────────────────────────────────────────────────────────────────────────
# §44 — RATCHET THEO-FILE ở chế độ --staged
# ─────────────────────────────────────────────────────────────────────────
# Lỗ hổng: `--staged` chỉ đếm trong FILE ĐANG STAGED nhưng so với baseline TOÀN
# KHO. Với rule có baseline > 0 thì tập con gần như luôn nhỏ hơn tổng, nên phép
# so ấy KHÔNG BAO GIỜ đỏ được — hook chỉ thực sự canh được rule baseline = 0.
#
# Đo được hậu quả 2026-08-27: một hàm complexity 21 commit qua hook trót lọt,
# chỉ `--all` mới bắt (R20.8 48 > 47).

import subprocess  # noqa: E402


def _git(tmp_path, *args):
    return subprocess.run(["git", *args], cwd=str(tmp_path), capture_output=True, text=True)


def _repo(tmp_path, rel, noi_dung):
    """Kho git tí hon với một commit gốc."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.t")
    _git(tmp_path, "config", "user.name", "t")
    _mk(tmp_path, rel, noi_dung)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "goc")


def test_theo_file_bat_duoc_no_moi_du_baseline_lon(tmp_path):
    """Ca mà phép so cũ mù: thêm 1 vi phạm trong khi baseline toàn kho là 99."""
    _repo(tmp_path, "docs/a.md", "MEH\n")
    _mk(tmp_path, "docs/a.md", "MEH\nMEH\n")          # 1 -> 2 vi phạm
    check = _soft_ratchet_check(tmp_path)
    code, msgs = run_hard.run(["docs/a.md"], checks=[check], root=tmp_path,
                              baseline={"RX.2": 99}, skips=set())
    assert code == 1, "phải CHẶN: file này vừa tăng từ 1 lên 2 vi phạm"
    assert any("theo-file" in m for m in msgs), msgs


def test_theo_file_cho_qua_khi_no_GIAM(tmp_path):
    _repo(tmp_path, "docs/a.md", "MEH\nMEH\nMEH\n")
    _mk(tmp_path, "docs/a.md", "MEH\n")               # 3 -> 1
    code, msgs = run_hard.run(["docs/a.md"], checks=[_soft_ratchet_check(tmp_path)],
                              root=tmp_path, baseline={"RX.2": 99}, skips=set())
    assert code == 0, msgs


def test_theo_file_cho_qua_khi_KHONG_DOI(tmp_path):
    _repo(tmp_path, "docs/a.md", "MEH\nxin chao\n")
    _mk(tmp_path, "docs/a.md", "MEH\ntam biet\n")     # sửa nội dung, nợ giữ nguyên
    code, msgs = run_hard.run(["docs/a.md"], checks=[_soft_ratchet_check(tmp_path)],
                              root=tmp_path, baseline={"RX.2": 99}, skips=set())
    assert code == 0, msgs


def test_file_MOI_mang_no_van_bi_tinh_la_tang(tmp_path):
    """File chưa có ở HEAD => HEAD coi như 0 vi phạm. Không có nhánh này thì chỉ
    cần tạo file mới là nhét được nợ vào mà cổng im."""
    _repo(tmp_path, "docs/a.md", "sach\n")
    _mk(tmp_path, "docs/moi.md", "MEH\n")
    code, msgs = run_hard.run(["docs/moi.md"], checks=[_soft_ratchet_check(tmp_path)],
                              root=tmp_path, baseline={"RX.2": 99}, skips=set())
    assert code == 1, "file mới mang nợ phải bị chặn"


def test_theo_file_KHONG_ap_cho_rule_baseline_0(tmp_path):
    """Baseline = 0 thì phép so cũ đã đủ và chính xác; chạy thêm là phí và có thể
    nói hai lần cùng một chuyện."""
    _repo(tmp_path, "docs/a.md", "sach\n")
    _mk(tmp_path, "docs/a.md", "MEH\n")
    code, msgs = run_hard.run(["docs/a.md"], checks=[_soft_ratchet_check(tmp_path)],
                              root=tmp_path, baseline={"RX.2": 0}, skips=set())
    assert code == 1
    assert not any("theo-file" in m for m in msgs), "không được nhân đôi thông báo"


def test_skip_soft_van_ap_duoc_cho_theo_file(tmp_path):
    _repo(tmp_path, "docs/a.md", "MEH\n")
    _mk(tmp_path, "docs/a.md", "MEH\nMEH\n")
    code, msgs = run_hard.run(["docs/a.md"], checks=[_soft_ratchet_check(tmp_path)],
                              root=tmp_path, baseline={"RX.2": 99}, skips={"RX.2"})
    assert code == 0
    assert any("SKIPPED" in m for m in msgs), msgs
