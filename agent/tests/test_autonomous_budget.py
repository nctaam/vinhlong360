"""
Test kiểm soát ngân sách agent tự động (ngoại lệ §B8 có-kiểm-soát).

Bảo đảm cap cứng/ngày chặn rò chi phí LLM nền + kill-switch off-mặc-định.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import autonomous_budget as ab


def _fresh(tmp_path, monkeypatch, cap, enabled):
    monkeypatch.setattr(ab, "_DATA", tmp_path / "budget.json")
    monkeypatch.setenv("AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY", str(cap))
    monkeypatch.setenv("AUTONOMOUS_AGENT_ENABLED", "true" if enabled else "false")


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("AUTONOMOUS_AGENT_ENABLED", raising=False)
    assert ab.enabled() is False  # §B8: tắt mặc định


def test_enabled_flag(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch, cap=5, enabled=True)
    assert ab.enabled() is True


def test_hard_cap_blocks_overuse(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch, cap=2, enabled=True)
    assert ab.try_consume(1) is True   # 1/2
    assert ab.try_consume(1) is True   # 2/2
    assert ab.try_consume(1) is False  # vượt cap → chặn (không gọi LLM)
    st = ab.status()
    assert st["used_today"] == 2 and st["remaining_today"] == 0


def test_status_shape(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch, cap=10, enabled=False)
    st = ab.status()
    assert set(["enabled", "cap_per_day", "used_today", "remaining_today", "date"]).issubset(st)
    assert st["cap_per_day"] == 10


def test_task_noop_when_disabled(tmp_path, monkeypatch):
    # task_autonomous_agent phải KHÔNG gọi LLM/gửi gì khi flag off (kill-switch).
    import scheduler
    _fresh(tmp_path, monkeypatch, cap=5, enabled=False)
    called = {"llm": False, "send": False}
    monkeypatch.setattr(scheduler, "_send_telegram_admins", lambda *a, **k: called.__setitem__("send", True))
    scheduler.task_autonomous_agent()  # phải no-op, không ném
    assert called["send"] is False
