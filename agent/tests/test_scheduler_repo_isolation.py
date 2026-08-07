"""Suite KHÔNG được ghi đè file tracked `web/data.js` (hồi quy 2026-08-07).

Triệu chứng thật (đo 3 lần): chạy full suite xong `git status` luôn có
` M web/data.js` (~8 dòng đổi — data.js ở HEAD đã cũ hơn data.json). Ai chạy
suite rồi `git add -A` sẽ commit nhầm bản sinh lại.

Chuỗi nhân quả:
  1. `scheduler.SCHEDULER_ENABLED` đọc env **lúc import module**.
  2. 17 file test đặt `os.environ["SCHEDULER_ENABLED"]="false"` ở module-level —
     vô tác dụng nếu một file khác đã `import server` (→ `scheduler`) TRƯỚC đó
     (vd `test_account_deletion_transport.py` đứng trước `test_chat_*` theo thứ
     tự collect) → cờ chốt cứng True cho cả process.
  3. File test đầu tiên mở lifespan (`with TestClient(server.app)`) →
     `start_scheduler()` thật → thread nền.
  4. `_scheduler_loop` chạy TASKS ngay tick đầu; `ScheduledTask("data-sync", ...)`
     dùng `run_immediately=True` mặc định → `next_run_after=0` → chạy liền.
  5. `sync_data_json_to_js()` ghi `PROJECT_DIR/web/data.js` = file repo thật.

Tái hiện tối thiểu (trước khi vá):
    python -m pytest agent/tests/test_account_deletion_transport.py \
                     agent/tests/test_chat_history_continuity.py -q -n0
    git status --short web/data.js   # -> " M web/data.js"

Bản vá: `os.environ.setdefault("SCHEDULER_ENABLED", "false")` trong
`agent/tests/conftest.py` + `tests/conftest.py` (conftest được import trước mọi
test module nên kịp chốt cờ). File này KHÔNG tự đặt env — nó phải đỏ nếu ai gỡ
dòng đó khỏi conftest, kể cả khi chạy một mình.
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

DATA_JS = PROJECT_ROOT / "web" / "data.js"


def _scheduler_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "scheduler"]


def test_phien_test_khong_bat_scheduler_nen():
    """Cờ phải là False *trong process test*, bất kể file nào import trước."""
    assert scheduler.SCHEDULER_ENABLED is False, (
        "SCHEDULER_ENABLED đang True trong phiên test → thread nền sẽ chạy task "
        "data-sync và ghi đè web/data.js. Kiểm tra os.environ.setdefault"
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


def test_task_data_sync_van_ghi_that_khi_tro_vao_tmp(tmp_path, monkeypatch):
    """Chốt chặn ngược: hai test trên chỉ có nghĩa nếu data-sync THẬT SỰ biết ghi.

    Trỏ PROJECT_DIR vào tmp_path rồi chạy đúng hàm task → phải sinh data.js.
    Nếu ngày nào đó sync bị vô hiệu hoá, test này đỏ và ta biết hai test trên đã
    thành xanh-giả.
    """
    web = tmp_path / "web"
    web.mkdir()
    (web / "data.json").write_text(
        '{"entities": [{"id": "x", "type": "place", "name": "X"}],'
        ' "relationships": [], "itineraries": []}',
        encoding="utf-8",
    )
    monkeypatch.setattr(scheduler, "PROJECT_DIR", tmp_path)

    scheduler.task_sync_data()

    assert (web / "data.js").exists()
    assert "window.VL_DATA" in (web / "data.js").read_text(encoding="utf-8")


def test_mo_lifespan_app_khong_ghi_de_web_data_js():
    """Hồi quy end-to-end: mở/đóng lifespan của app không được đụng web/data.js.

    Đây đúng là đường đã làm bẩn worktree. Test tự khôi phục file nếu bị ghi, để
    một lần đỏ không để lại rác trong working tree.
    """
    import server
    from fastapi.testclient import TestClient

    original = DATA_JS.read_bytes()
    before_mtime = DATA_JS.stat().st_mtime_ns
    try:
        with TestClient(server.app):
            pass
        # Thread nền (nếu bị bật) ghi ngay tick đầu; chờ có giới hạn để test
        # không phải ngủ đủ 3s ở đường xanh.
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and DATA_JS.stat().st_mtime_ns == before_mtime:
            time.sleep(0.05)

        assert DATA_JS.read_bytes() == original, (
            "web/data.js (file tracked) bị suite ghi đè khi mở lifespan — "
            "scheduler nền đang chạy trong test"
        )
    finally:
        if DATA_JS.read_bytes() != original:
            DATA_JS.write_bytes(original)
