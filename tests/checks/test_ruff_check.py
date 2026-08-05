# -*- coding: utf-8 -*-
"""Test check_ruff (R20.1) — graceful-skip khi vắng ruff + filter non-py + parse."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks import check_ruff  # noqa: E402
from checks.check_ruff import RuffCheck  # noqa: E402


def test_level_rule():
    c = RuffCheck()
    assert c.level == "hard-ratchet" and c.rule == "R20.1" and c.name == "ruff_lint"


def test_staged_khong_chan_khi_may_thieu_ruff(monkeypatch, capsys):
    """Hook local trên máy chưa cài ruff: không chặn, nhưng phải cảnh báo.

    Trước 2026-08-05 cổng trả 0 trong im lặng ở CẢ hai chế độ — xem test dưới.
    """
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: None)
    result = RuffCheck().run(files=["agent/server.py"])
    assert result["count"] == 0
    assert "không tìm thấy ruff" in capsys.readouterr().err


def test_all_fail_closed_khi_thieu_ruff(monkeypatch):
    """`--all` chạy ở CI/pre-merge: thiếu công cụ đo là defect hạ tầng.

    Fail-open ở đây biến "cổng không chạy được" thành "cổng báo sạch", và
    R20.1/R20.2 là hạng hard-ratchet — im lặng đúng lúc chúng vô dụng.
    """
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: None)
    result = RuffCheck().run()
    assert result["count"] == 1
    assert "không thể chạy" in result["violations"][0]["msg"]


def test_run_ruff_phan_biet_sach_voi_thieu_cong_cu(monkeypatch, tmp_path):
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: None)
    assert check_ruff.run_ruff(tmp_path, ["agent"]) is None      # thiếu công cụ
    assert check_ruff.run_ruff(tmp_path, []) == []               # không target


def test_non_py_staged_returns_zero(monkeypatch):
    # File staged không phải .py trong agent/scripts → không gọi ruff, count 0.
    called = {"n": 0}
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: (called.__setitem__("n", called["n"] + 1) or ["ruff"]))
    r = RuffCheck().run(files=["docs/x.md", "web-nuxt/app.vue"])
    assert r["count"] == 0
    assert called["n"] == 0  # không target → không định vị/chạy ruff


def test_parses_ruff_json(monkeypatch):
    monkeypatch.setattr(check_ruff, "find_ruff", lambda: ["ruff"])
    fake = [
        {"filename": "agent/x.py", "code": "F401", "message": "unused import",
         "location": {"row": 3, "column": 1}},
        {"filename": "agent/y.py", "code": "F841", "message": "unused var",
         "location": {"row": 9, "column": 1}},
    ]

    class _P:
        stdout = __import__("json").dumps(fake)
    monkeypatch.setattr(check_ruff.subprocess, "run", lambda *a, **k: _P())
    r = RuffCheck().run(files=["agent/x.py"])
    assert r["count"] == 2
    assert r["violations"][0]["rule"] == "R20.1"
    assert "F401" in r["violations"][0]["msg"]
