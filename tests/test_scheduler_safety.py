"""§B8 guard — vòng lặp LLM nền (auto-learn/discovery/promotion) phải TẮT mặc định.

Bất biến CLAUDE.md §B8: agent KHÔNG tự gọi LLM nền trừ khi opt-in tường minh.
Footgun đã từng tồn tại: `scheduler.py` mặc định bật khi env không đặt — lệch với
`config.py` và `.env.example`. Test này khoá default để không tái nhiễm.
"""

import importlib


def test_autonomous_tasks_off_by_default(monkeypatch):
    monkeypatch.delenv("SCHEDULER_ENABLE_AUTONOMOUS_TASKS", raising=False)
    import scheduler
    importlib.reload(scheduler)
    try:
        assert scheduler.AUTONOMOUS_TASKS_ENABLED is False

        # Mọi task gọi-LLM-nền phải disabled khi không opt-in.
        for name in (
            "auto-learn",
            "learning-loop",
            "continuous-discovery",
            "kb-promotion",
            "relationships",
        ):
            task = scheduler._get_task(name)
            assert task is not None, f"task {name!r} không tồn tại"
            assert task.enabled is False, f"task {name!r} phải TẮT mặc định (§B8)"
    finally:
        # Trả module về trạng thái khớp env hiện tại của runner.
        importlib.reload(scheduler)


def test_autonomous_tasks_can_opt_in(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLE_AUTONOMOUS_TASKS", "true")
    import scheduler
    importlib.reload(scheduler)
    try:
        assert scheduler.AUTONOMOUS_TASKS_ENABLED is True
    finally:
        monkeypatch.delenv("SCHEDULER_ENABLE_AUTONOMOUS_TASKS", raising=False)
        importlib.reload(scheduler)
