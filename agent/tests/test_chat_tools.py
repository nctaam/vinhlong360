"""TC-02 (call_tool branches) + TC-10.7 (_is_error_reply regression) — chat là lõi sản phẩm.

Marked integration (cần import server + lifespan load KB SQLite; KHÔNG cần PG). Chạy:
  python -m pytest agent/tests/test_chat_tools.py -m integration
"""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ.setdefault("DESTRUCTIVE_OPS_LOCKED", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.integration

from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402


def _completion(content):
    msg = SimpleNamespace(content=content, tool_calls=None, role="assistant", function_call=None)
    choice = SimpleNamespace(message=msg, finish_reason="stop", index=0)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], usage=usage, model="test", id="c1")


@pytest.fixture
def kb_ctx():
    """TestClient context → lifespan startup load KB (knowledge globals sẵn cho call_tool)."""
    with patch.object(server.client.chat.completions, "create",
                      side_effect=lambda *a, **k: _completion("ok")):
        with TestClient(server.app) as c:
            yield c


# ── TC-02: call_tool branches (resilience + đúng shape) ──

def test_call_tool_unknown_returns_error(kb_ctx):
    out = json.loads(server.call_tool("khong_co_tool_nay", {}))
    assert "error" in out


def test_call_tool_entity_detail_missing_arg_graceful(kb_ctx):
    # P1: thiếu entity_id KHÔNG được crash (trước đây args["entity_id"] → KeyError → 500)
    out = json.loads(server.call_tool("entity_detail", {}))
    assert "error" in out


def test_call_tool_seasonal_missing_month_graceful(kb_ctx):
    out = json.loads(server.call_tool("seasonal_now", {}))
    assert isinstance(out, (dict, list))  # không crash


def test_call_tool_search_returns_json(kb_ctx):
    out = json.loads(server.call_tool("search", {"query": "đặc sản"}))
    assert isinstance(out, list)  # danh sách card (có thể rỗng), không lỗi


def test_call_tool_stats_returns_counts(kb_ctx):
    out = json.loads(server.call_tool("stats", {}))
    assert isinstance(out, dict)


# ── TC-10.7: _is_error_reply KHÔNG ghi đè câu trả lời đúng chứa "sự cố"/"lỗi" ──

def test_valid_reply_with_su_co_not_clobbered(kb_ctx):
    """Reply hợp lệ bắt đầu 'Sự cố giao thông…' KHÔNG bị thay bằng KB-fallback 'đang bảo trì'."""
    valid = "Sự cố giao thông ở Vĩnh Long thường xảy ra vào giờ cao điểm tại các ngã tư trung tâm thành phố và gần chợ."
    with patch.object(server.client.chat.completions, "create",
                      side_effect=lambda *a, **k: _completion(valid)):
        r = kb_ctx.post("/chat", json={"message": "kể về giao thông", "session_id": "tc107"})
    assert r.status_code == 200, r.text
    reply = r.json().get("reply", "")
    assert "giao thông" in reply and "bảo trì" not in reply, f"reply bị clobber: {reply[:120]}"
