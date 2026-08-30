"""Shared fixtures for vinhlong360 tests."""
import os
import sys
import pytest

# Add agent/ to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

# Set test environment
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8360")
# Scheduler nền PHẢI tắt trong test: tác vụ nền có thể ghi vào file tracked.
# scheduler.py đọc env lúc import → phải đặt ở conftest (chạy trước
# mọi test module) mới kịp. Chi tiết: agent/tests/test_scheduler_repo_isolation.py
os.environ.setdefault("SCHEDULER_ENABLED", "false")

@pytest.fixture(autouse=True)
def _dong_lai_cau_dao_ngat_mach():
    """Reset MỌI circuit breaker TRƯỚC mỗi test. Bản sinh đôi của fixture cùng
    tên ở `agent/tests/conftest.py` — hai thư mục test có conftest RIÊNG, đặt một
    bên là bên kia vẫn rò.

    Ba breaker là biến module-level (`agent/circuit_breaker.py:394,404,412`) nên
    trạng thái OPEN chảy từ test này sang test sau. Đo được trong chính thư mục
    này: `tests/test_integration.py::test_chat_stream_concurrent_non_blocking`
    chạy RIÊNG thì xanh, chạy CHUNG cả file thì đỏ — vì các test trước nó gọi LLM
    thật, hỏng 5 lần, mở circuit 'llm_api', và request của nó bị chặn TRƯỚC KHI
    tới client đã mock.

    Chạy-riêng-xanh / chạy-chung-đỏ là triệu chứng kinh điển của state module-level
    không được dọn. Đã đo với `-p no:randomly` nên là phụ thuộc thứ tự TẤT ĐỊNH;
    CI không tắt pytest-randomly nên ở đó nó thành chớp-tắt.
    """
    try:
        import circuit_breaker
    except Exception:
        yield
        return

    def _dong_het():
        for ten in ("llm_breaker", "weather_breaker", "web_search_breaker"):
            cb = getattr(circuit_breaker, ten, None)
            if cb is not None and hasattr(cb, "reset"):
                cb.reset()

    _dong_het()
    try:
        yield
    finally:
        _dong_het()


@pytest.fixture
def admin_headers():
    """Khoá LẤY TỪ MÔI TRƯỜNG, không ghim cứng — xem giải trình ở đầu hàm dưới."""
    return {"X-Admin-Key": os.environ["ADMIN_API_KEY"]}
