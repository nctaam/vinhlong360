"""Suite KHÔNG được làm bẩn worktree bằng cách chạy scheduler nền.

Hồi quy 2026-08-07: mở lifespan của app trong phiên test bật thread nền, tick đầu
tiên ghi đè `web/data.js` — một file được git theo dõi — nên `git status` bẩn và
một agent khác suýt `stash` mất việc đang dở.

`web/data.js` đã được gỡ (2026-08-22: không còn ai đọc; `web/index.html`, consumer
duy nhất, đã biến mất từ trước). Nhưng *loại* lỗi thì không mất theo: bất kỳ tác vụ
nền nào chạy trong phiên test và ghi vào file tracked đều tái hiện đúng sự cố đó.
Vì vậy test cuối hỏi git xem worktree có bẩn thêm không, thay vì canh một tên file.

Ba việc suite này giữ:
  1. Phiên test không được bật scheduler nền.
  2. `start_scheduler()` không được spawn thread khi test đang chạy.
  3. Mở/đóng lifespan của app không được làm bẩn bất kỳ file tracked nào.
"""

import os
import sys
import threading
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

# Giữ lifespan nhẹ: không dựng index tìm kiếm (không liên quan điều đang test).
# CỐ Ý không đặt SCHEDULER_ENABLED ở đây — xem docstring.
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")

import scheduler  # noqa: E402


def _scheduler_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "scheduler"]


def test_phien_test_khong_bat_scheduler_nen():
    """Cờ phải là False *trong process test*, bất kể file nào import trước."""
    assert scheduler.SCHEDULER_ENABLED is False, (
        "SCHEDULER_ENABLED đang True trong phiên test → thread nền sẽ chạy và "
        "có thể ghi vào file tracked. Kiểm tra os.environ.setdefault"
        "('SCHEDULER_ENABLED','false') ở agent/tests/conftest.py và tests/conftest.py, "
        "hoặc env ngoài đang ép SCHEDULER_ENABLED=true."
    )


def test_start_scheduler_khong_spawn_thread_nen(monkeypatch):
    """Hành vi: gọi start_scheduler() trong test KHÔNG tạo thread nền nào."""
    if scheduler.SCHEDULER_ENABLED:
        pytest.fail(
            "bỏ qua để không spawn loop thật (task account-erasure/quarantine chạy "
            "kèm) — xem test_phien_test_khong_bat_scheduler_nen"
        )
    monkeypatch.setattr(scheduler, "_scheduler_thread", None)
    before = len(_scheduler_threads())

    scheduler.start_scheduler()
    try:
        assert len(_scheduler_threads()) == before
        assert scheduler._scheduler_thread is None
    finally:
        scheduler.stop_scheduler()


def test_mo_lifespan_app_khong_lam_ban_worktree():
    """Hồi quy end-to-end: mở/đóng lifespan của app không được làm bẩn worktree.

    Bản gốc canh đúng một file, `web/data.js`, vì đó là file đã bị ghi đè năm
    2026-08-07. File đó nay đã gỡ (không còn ai đọc), nhưng *loại* lỗi thì vẫn
    còn: một thread nền chạy trong phiên test và ghi vào file được git theo dõi.
    Nên test hỏi git, thay vì hỏi một tên file.
    """
    import subprocess

    import server
    from fastapi.testclient import TestClient

    def dirty() -> set[str]:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        ).stdout
        return {line[3:].strip() for line in out.splitlines() if line.strip()}

    before = dirty()
    with TestClient(server.app):
        pass
    # Thread nền (nếu bị bật) ghi ngay tick đầu; chờ có giới hạn để test không
    # phải ngủ đủ 3s ở đường xanh.
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and dirty() == before:
        time.sleep(0.05)

    assert dirty() == before, (
        "mở lifespan làm bẩn file tracked — scheduler nền đang chạy trong test"
    )
