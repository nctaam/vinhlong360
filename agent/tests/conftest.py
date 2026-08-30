"""
Shared fixtures for vinhlong360 agent tests.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure agent/ is on sys.path
AGENT_DIR = Path(__file__).resolve().parent.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

# ...và cả thư mục test, để các helper dùng chung (_source_window) import được
# dưới --import-mode=importlib.
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# Set test environment
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-12345")
# Scheduler nền PHẢI tắt trong test: tác vụ nền chạy ngay tick đầu tiên khi mở
# app, và có tác vụ ghi vào file tracked → worktree bẩn.
# 17 file test đã đặt cờ này ở module-level, nhưng scheduler.py đọc env LÚC IMPORT
# nên cách đó thua nếu một file khác import server (→ scheduler) trước → cờ chốt
# True → file test đầu tiên mở lifespan làm bẩn worktree. conftest được import
# TRƯỚC mọi test module nên đây là chỗ duy nhất chắc chắn kịp.
# Hồi quy: agent/tests/test_scheduler_repo_isolation.py
os.environ.setdefault("SCHEDULER_ENABLED", "false")


@pytest.fixture
def isolated_sqlite_db(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import database

    monkeypatch.setattr(database, "USE_PG", False)
    monkeypatch.setattr(database, "DATABASE_URL", "")
    instance = database.Database(str(tmp_path / "isolated.db"))
    assert instance._use_pg is False
    assert instance._dsn is None
    assert Path(instance.db_path).parent == tmp_path
    return instance


@pytest.fixture(autouse=True)
def _chuyen_huong_nhat_ky_kiem_toan(tmp_path_factory):
    """Không test nào được ghi vào nhật ký kiểm toán THẬT.

    ĐO ĐƯỢC, không phải phòng xa. Trước bản vá này, một lượt
    `pytest agent/tests/ -k admin` (547 test) làm:
        agent/data/admin_audit.jsonl   1.329.195 → 1.329.264 byte (sha đổi)
        agent/data/admin_audit.*.jsonl         254 → 260 file
    Tức mỗi lượt chạy vừa BƠM bản ghi giả vào nhật ký kiểm toán quản trị, vừa đẻ
    ra 6 file xoay vòng nằm lại trong `agent/data/`. Tới 2026-08-30 đã tích 255
    file rác, và bản thân nhật ký "thật" nay là một trộn lẫn giữa thao tác thật
    và rác test — tức nó không còn dùng được để kiểm toán bất cứ điều gì.

    `admin._AUDIT_FILE` là hằng module-level trỏ `agent/data/admin_audit.jsonl`
    (`agent/admin.py:65`), và mọi route quản trị đi qua TestClient đều ghi vào đó.
    Vài file test đã tự `monkeypatch.setattr(admin, "_AUDIT_FILE", tmp_path/...)`
    — nhưng chỉ vài file, còn các suite đi qua HTTP thì không. Rào theo từng file
    đã thua một lần rồi; chốt ở conftest là chỗ DUY NHẤT không thể quên.

    An toàn: đã rà toàn bộ `agent/tests/` + `tests/` — mọi test chạm tới nhật ký
    ĐỀU đã tự trỏ sang `tmp_path`, không test nào cần đường mặc định. Test nào
    monkeypatch trong thân hàm vẫn thắng fixture này (chạy sau).
    """
    duong_tam = tmp_path_factory.mktemp("nhat-ky-kiem-toan") / "admin_audit.jsonl"
    try:
        import admin
    except Exception:
        yield
        return
    goc = getattr(admin, "_AUDIT_FILE", None)
    admin._AUDIT_FILE = duong_tam
    try:
        yield
    finally:
        if goc is not None:
            admin._AUDIT_FILE = goc


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Reset MỌI rate-limiter TRƯỚC mỗi test.

    TestClient dùng chung client-IP nên state của check_rate (ratelimit._buckets + bảng PG
    shared_rate_limits) và admin_limiter/chat_limiter (middleware) cộng dồn qua cả suite →
    test không tự-reset (vd test_chat_smoke) bị 429 giả. Reset ở đây làm state rate-limit
    độc lập theo từng test; test rate-limit vẫn tự tích luỹ trong thân hàm nên không ảnh hưởng.
    """
    try:
        import ratelimit
        ratelimit._reset()
    except Exception:
        pass
    try:
        import middleware
        middleware._reset_limiters()
    except Exception:
        pass
    def reset_server_drain_flag():
        server_module = sys.modules.get("server")
        if server_module is not None:
            server_module._draining = False

    reset_server_drain_flag()
    try:
        yield
    finally:
        reset_server_drain_flag()


@pytest.fixture(autouse=True)
def _reset_autonomous_budget():
    """Reset bộ đếm RAM của autonomous_budget TRƯỚC mỗi test.

    `autonomous_budget._ram_count` là biến module-level: MỌI test gọi try_consume()
    (vd test_resilience::TestAutonomousBudgetLogging) đều cộng dồn vào đó và không
    trả lại. Test tự đếm với cap thấp (test_autonomous_budget::test_hard_cap_blocks_
    overuse, cap=2) do đó thấy cap đã bị tiêu trước → fail giả. monkeypatch _DATA
    sang tmp_path KHÔNG cứu được vì counter nằm trong RAM, ngoài file. Chỉ đỏ khi
    xdist --dist loadfile xếp 2 file vào cùng worker → trông như flaky.
    """
    try:
        import autonomous_budget
        autonomous_budget._ram_count.update({"date": "", "count": 0})
    except Exception:
        pass


@pytest.fixture
def sample_entities():
    """Minimal entity list for testing."""
    return [
        {
            "id": "cam-sanh-vinh-long",
            "name": "Cam sành Vĩnh Long",
            "type": "product",
            "summary": "Cam sành Vĩnh Long nổi tiếng ngọt mát, vỏ xanh.",
            "placeId": "xa-binh-hoa-phuoc",
            "confidence": 0.95,
            "images": ["https://example.com/cam.jpg"],
            "attributes": {"ocop": True, "ocopStars": 4},
            "season": {"months": [10, 11, 12, 1, 2], "peak": [11, 12]},
            "source": "manual",
            "updatedAt": "2026-06-01",
        },
        {
            "id": "bun-mam",
            "name": "Bún mắm",
            "type": "dish",
            "summary": "Bún mắm đặc sản Trà Vinh.",
            "placeId": "tp-tra-vinh",
            "confidence": 0.8,
            "images": [],
            "attributes": {},
            "source": "crawled",
            "updatedAt": "2026-06-05",
        },
        {
            "id": "xa-binh-hoa-phuoc",
            "name": "Bình Hòa Phước",
            "type": "place",
            "area": "vinh-long",
            "level": "xa",
            "parentId": "h-long-ho",
        },
        {
            "id": "tp-tra-vinh",
            "name": "TP Trà Vinh",
            "type": "place",
            "area": "tra-vinh",
            "level": "phuong",
        },
    ]


@pytest.fixture
def sample_data(sample_entities):
    """Full data structure matching data.json format."""
    return {
        "entities": sample_entities,
        "relationships": [
            {"from": "cam-sanh-vinh-long", "to": "xa-binh-hoa-phuoc", "type": "produced_in"},
        ],
        "itineraries": [
            {
                "id": "1-ngay-vinh-long",
                "name": "1 ngày Vĩnh Long",
                "area": "vinh-long",
                "days": 1,
                "stops": ["cam-sanh-vinh-long"],
            }
        ],
    }


@pytest.fixture
def tmp_data_json(sample_data, tmp_path):
    """Write sample data to a temp data.json and return the path."""
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(sample_data, ensure_ascii=False), encoding="utf-8")
    return data_path


@pytest.fixture
def tmp_analytics(tmp_path):
    """Create a temp analytics.json with sample data."""
    analytics_path = tmp_path / "analytics.json"
    data = {
        "queries": [
            {"text": "Cam sanh la gi?", "timestamp": "2026-06-10T01:00:00", "tools": [], "has_answer": True},
            {"text": "Bun mam o dau?", "timestamp": "2026-06-10T01:01:00", "tools": [], "has_answer": False},
        ],
        "entity_hits": {"cam-sanh-vinh-long": 5},
        "daily_stats": {"2026-06-10": {"queries": 10, "sessions": 2}},
        "gap_queries": ["bun mam o dau"],
        "unanswered": [{"text": "Bun mam o dau?", "timestamp": "2026-06-10T01:01:00"}],
        "tool_usage": {"search": 8, "entity_detail": 3},
        "sessions": 2,
    }
    analytics_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return analytics_path
