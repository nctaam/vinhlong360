# -*- coding: utf-8 -*-
"""Test check_coverage (R20.4) — staged skip, full enforcement, and thresholds."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_coverage import CoverageCheck  # noqa: E402


def _write(tmp_path, cov: dict, thr: dict):
    (tmp_path / "coverage.json").write_text(json.dumps(cov), encoding="utf-8")
    d = tmp_path / "docs" / "standards"
    d.mkdir(parents=True, exist_ok=True)
    (d / "coverage-thresholds.json").write_text(json.dumps(thr), encoding="utf-8")


def test_level_rule():
    c = CoverageCheck()
    assert c.level == "soft-ratchet" and c.rule == "R20.4"


def test_skip_when_no_coverage_json_for_staged_hook(tmp_path):
    result = CoverageCheck(root=tmp_path).run(files=["agent/server.py"])
    assert result["count"] == 0


def test_missing_coverage_json_KHONG_con_lam_do_run_hard(tmp_path):
    """ĐẢO CÓ CHỦ Ý 2026-08-30 — trước đây bài này ghim `count == 1`.

    Lý do đảo: cổng R20.4 chuyển sang job CI có PostgreSQL (chủ dự án chốt), nên
    `run_hard --all` ở job SQLite và ở hook pre-commit KHÔNG còn sinh
    coverage.json. Fail-closed ở đó nghĩa là chặn mọi commit vì một file mà chính
    thiết kế mới cố ý không tạo.

    Tính nghiêm KHÔNG mất — nó dời sang `check_coverage.main()`: gọi entry đó
    nghĩa là bạn vừa chạy pytest có --cov, nên thiếu file là LỖI (exit 2). Đúng
    khuôn `check_bundle` đã dùng cho R30.7 từ trước. Xem
    `test_thieu_coverage_json_thi_run_hard_BO_QUA_con_entry_rieng_thi_DO`.
    """
    result = CoverageCheck(root=tmp_path).run(files=None)
    assert result["count"] == 0


def test_below_thresholds_flagged(tmp_path):
    cov = {
        "totals": {"percent_covered": 51.0},
        "files": {
            "agent/database.py": {"summary": {"percent_covered": 78.0}},
            "agent/auth.py": {"summary": {"percent_covered": 25.0}},
        },
    }
    thr = {"agent": 60, "core": {"database.py": 80, "auth.py": 80}}
    _write(tmp_path, cov, thr)
    r = CoverageCheck(root=tmp_path).run()
    # agent 51<60, database 78<80, auth 25<80 → 3 vi phạm
    assert r["count"] == 3


def test_meets_thresholds_pass(tmp_path):
    cov = {
        "totals": {"percent_covered": 61.0},
        "files": {"agent/database.py": {"summary": {"percent_covered": 81.0}}},
    }
    thr = {"agent": 60, "core": {"database.py": 80}}
    _write(tmp_path, cov, thr)
    assert CoverageCheck(root=tmp_path).run()["count"] == 0


def test_sibling_basename_does_not_shadow_core_module(tmp_path):
    # Regression: mcp_server.py (0%) KHÔNG được che server.py (21.5%) — bug _pct
    # endswith lỏng trả nhầm 0% → false-positive vi phạm. Basename phải khớp CHÍNH XÁC.
    cov = {
        "totals": {"percent_covered": 61.0},
        "files": {
            "agent/mcp_server.py": {"summary": {"percent_covered": 0.0}},
            "agent/server.py": {"summary": {"percent_covered": 21.5}},
        },
    }
    thr = {"agent": 60, "core": {"server.py": 20}}
    _write(tmp_path, cov, thr)
    # server.py 21.5% > 20% → KHÔNG vi phạm (nếu _pct che nhầm mcp_server 0% → sẽ fail)
    assert CoverageCheck(root=tmp_path).run()["count"] == 0


def test_san_khong_khop_file_nao_phai_DO_chu_khong_bien_mat(tmp_path):
    """Sàn trỏ tới một module không còn tồn tại phải ĐỎ, không được im lặng.

    Bản cũ chỉ ghi vi phạm khi `pct is not None`, nên một khoá sàn không khớp file
    nào sẽ biến mất không tiếng động: count = 0, cổng xanh, và module đó tụt về 0%
    cũng không ai hay. Đổi tên hoặc dời module là làm được đúng điều đó — và suýt
    xảy ra thật với `itinerary_gen.py` sau khi nó dời sang `agent/itineraries/`.

    Sàn KHÔNG ĐO ĐƯỢC là sàn hỏng, không phải sàn đã đạt.
    """
    cov = {
        "totals": {"percent_covered": 90.0},
        "files": {"agent/database.py": {"summary": {"percent_covered": 95.0}}},
    }
    thr = {"agent": 60, "core": {"database.py": 80, "module_da_doi_ten.py": 90}}
    _write(tmp_path, cov, thr)

    r = CoverageCheck(root=tmp_path).run()

    assert r["count"] == 1, "khoá sàn mồ côi phải sinh đúng một vi phạm"
    (v,) = r["violations"]
    assert "module_da_doi_ten.py" in v["msg"]
    assert "KHÔNG khớp file nào" in v["msg"], "thông điệp phải nói rõ vì sao, để sửa được ngay"


def _job_blocks() -> dict[str, str]:
    """Cắt ci.yml thành từng job theo thụt lề 2 dấu cách — đủ cho phép ghim dưới,
    và KHÔNG cần PyYAML (không có trong requirements của bộ test này)."""
    import re

    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    moc = [(m.start(), m.group(1)) for m in re.finditer(r"^  ([a-z][a-z0-9-]*):$", text, re.M)]
    blocks = {}
    for i, (pos, ten) in enumerate(moc):
        het = moc[i + 1][0] if i + 1 < len(moc) else len(text)
        blocks[ten] = text[pos:het]
    return blocks


def test_cong_coverage_nam_o_JOB_CO_POSTGRES_chu_khong_o_job_sqlite():
    """Cổng R20.4 phải chạy ở nơi phép đo HỢP LỆ.

    Ngưỡng identity 85 / community 90 chỉ đạt được khi có PostgreSQL — đo
    2026-08-30 trên hai môi trường: không PG 46,2%/29,2%, có PG 88,3%/95,8%.
    Đặt cổng ở job SQLite là thực thi một phép đo thiếu và chặn MỌI lượt push.
    Chủ dự án chốt 2026-08-30: chuyển sang job `test-pg`.

    Đây là rào DUY NHẤT kiểm được điều đó ở local — kho không có remote nên CI
    chưa từng chạy, và CLAUDE.md §5b cấm vá CI bằng suy luận (sai 2/2 lần).
    """
    jobs = _job_blocks()
    assert "test" in jobs and "test-pg" in jobs, "không cắt được job từ ci.yml — regex hỏng?"

    pg = jobs["test-pg"]
    assert "postgres" in pg, "job test-pg phải thật sự có service postgres"
    assert "--cov-report=json:coverage.json" in pg, "job test-pg phải sinh coverage.json"
    assert "checks.check_coverage" in pg, "cổng R20.4 phải chạy Ở ĐÂY"

    sqlite_job = jobs["test"]
    assert "--cov-report=json:coverage.json" not in sqlite_job, (
        "job test (SQLite) KHÔNG được sinh coverage.json — có file là mời R20.4 "
        "thực thi một phép đo thiếu thay vì graceful-skip"
    )
    assert "checks.check_coverage" not in sqlite_job
    assert "python scripts/checks/run_hard.py --all" in sqlite_job, (
        "các rule khác vẫn phải được canh ở job test"
    )


def test_thieu_coverage_json_thi_run_hard_BO_QUA_con_entry_rieng_thi_DO():
    """Hai chế độ, có chủ ý — cùng khuôn với R30.7 (`check_bundle`).

    `run()` graceful-skip khi thiếu file: nó chạy ở hook pre-commit và ở job
    không sinh coverage. `main()` thì THIẾU FILE LÀ LỖI: gọi nó nghĩa là bạn vừa
    chạy pytest có --cov, không có file tức bước đó hỏng.
    """
    import scripts.checks.check_coverage as cc

    trong = CoverageCheck(root=tmp_path_khong_co_file())
    assert trong.run()["count"] == 0, "thiếu coverage.json thì run() phải im lặng"

    goc = cc.CHECKS[0]._root
    try:
        cc.CHECKS[0]._root = tmp_path_khong_co_file()
        assert cc.main() == 2, "entry riêng phải ĐỎ khi thiếu file"
    finally:
        cc.CHECKS[0]._root = goc


def tmp_path_khong_co_file():
    import tempfile
    from pathlib import Path

    return Path(tempfile.mkdtemp(prefix="vl-cov-trong-"))
