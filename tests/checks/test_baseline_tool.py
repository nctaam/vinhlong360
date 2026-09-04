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


# ─────────────────────────────────────────────────────────────────────────
# Bảng 00-INDEX.md phải khớp baseline.json
# ─────────────────────────────────────────────────────────────────────────
# Backlog §31.5 ghi "Tài liệu chuẩn lệch máy: 00-INDEX.md ghi R30.2=687/R30.3=307,
# baseline.json là 330/200". Lệch tài liệu chuẩn nguy hiểm hơn vẻ ngoài của nó:
# người đọc bảng để biết còn nợ bao nhiêu, rồi lập kế hoạch trên con số sai. Rào
# này bắt lệch ngay lần commit sau chứ không đợi ai đó tình cờ đối chiếu.

import re as _re  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_ROOT = _Path(__file__).resolve().parents[2]
_HANG = _re.compile(r"^\|\s*(R\d+\.\d+\w*)\s*\|.*\|\s*(\d+|~\d+|—)\s*\|\s*[\w.-]+\s*\|\s*$")


def _bang_index() -> dict[str, int]:
    """{rule: count} đọc từ cột áp chót của bảng 00-INDEX.md."""
    ra: dict[str, int] = {}
    for line in (_ROOT / "docs/standards/00-INDEX.md").read_text(encoding="utf-8").splitlines():
        m = _HANG.match(line.strip())
        if m and m.group(2).isdigit():
            ra[m.group(1)] = int(m.group(2))
    return ra


def test_bang_00_index_khop_baseline_json():
    baseline = json.loads((_ROOT / "docs/standards/baseline.json").read_text(encoding="utf-8"))
    bang = _bang_index()
    assert bang, "không đọc được dòng nào từ bảng 00-INDEX.md — regex hỏng?"
    lech = {r: (bang[r], baseline[r]) for r in bang if r in baseline and bang[r] != baseline[r]}
    assert not lech, (
        "00-INDEX.md lệch baseline.json (bảng, máy): " + repr(lech)
        + " — sửa BẢNG cho khớp máy, đừng sửa ngược."
    )


def test_moi_rule_trong_baseline_deu_co_mat_o_bang():
    """Rule có trong baseline mà không có dòng trong bảng = nợ vô hình."""
    baseline = json.loads((_ROOT / "docs/standards/baseline.json").read_text(encoding="utf-8"))
    doc = (_ROOT / "docs/standards/00-INDEX.md").read_text(encoding="utf-8")
    thieu = [r for r in baseline if f"| {r} |" not in doc]
    assert not thieu, f"rule có baseline nhưng KHÔNG có dòng trong 00-INDEX.md: {thieu}"
