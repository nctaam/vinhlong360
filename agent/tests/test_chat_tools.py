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
    """TestClient context → lifespan startup load KB (knowledge globals sẵn cho call_tool).

    server dùng get_client() (llm_config singleton) — KHÔNG có server.client → patch server.get_client.
    """
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda *a, **k: _completion("ok"))))
    with patch.object(server, "get_client", lambda: fake):
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
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda *a, **k: _completion(valid))))
    with patch.object(server, "get_client", lambda: fake):
        r = kb_ctx.post("/chat", json={"message": "kể về giao thông", "session_id": "tc107"})
    assert r.status_code == 200, r.text
    reply = r.json().get("reply", "")
    assert "giao thông" in reply and "bảo trì" not in reply, f"reply bị clobber: {reply[:120]}"


# ── _run_agent helper: _prepare_pending_calls / _execute_pending_calls (extract-verbatim R20.8) ──

def test_lifespan_resets_drain_flag_on_restart():
    """Regression: lifespan reset _draining=False lúc startup → TestClient thứ 2 KHÔNG bị 503.

    Trước fix: shutdown set _draining=True nhưng startup không reset → mọi test dùng
    TestClient thứ 2+ trong cùng process trả 503 'Server shutting down'.
    """
    with TestClient(server.app):
        pass  # startup rồi shutdown → _draining=True
    assert server._draining is True
    with TestClient(server.app):
        assert server._draining is False  # startup lần 2 đã reset


def _mk_tc(tc_id, name, arguments):
    """Giả tool_call object (shape OpenAI: .id + .function.name/.arguments)."""
    return SimpleNamespace(id=tc_id, function=SimpleNamespace(name=name, arguments=arguments))


def test_prepare_pending_calls_parses_args():
    tools_used, messages = [], []
    tcs = [_mk_tc("t1", "search", '{"query": "chợ"}')]
    pending, total = server._prepare_pending_calls(tcs, tools_used, messages, 0, 15)
    assert pending == [{"id": "t1", "name": "search", "args": {"query": "chợ"}}]
    assert total == 1
    assert tools_used and "search" in tools_used[0]
    assert messages == []  # prepare chỉ parse — chưa exec nên chưa có tool-message


def test_prepare_pending_calls_bad_json_falls_back_empty():
    tools_used, messages = [], []
    tcs = [_mk_tc("t1", "search", "not-json")]
    pending, total = server._prepare_pending_calls(tcs, tools_used, messages, 0, 15)
    assert pending == [{"id": "t1", "name": "search", "args": {}}]  # EH-02: args lỗi → {}, không crash
    assert total == 1


def test_prepare_pending_calls_respects_limit():
    tools_used, messages = [], []
    tcs = [_mk_tc("t1", "search", '{"query": "x"}')]
    pending, total = server._prepare_pending_calls(tcs, tools_used, messages, 15, 15)
    assert pending == []       # đã đạt max_tool_calls → không thêm call
    assert total == 15         # counter không tăng
    assert len(messages) == 1 and "limit" in messages[0]["content"].lower()  # nhưng báo limit


def test_execute_pending_calls_serial_runs_tool():
    """Serial path: gọi call_tool, append tool-message, trả empty_results_count.

    Patch server.call_tool → unit thuần (không cần KB/fixture/lifespan).
    """
    messages, suggestions = [], []
    pending = [{"id": "t1", "name": "search", "args": {"query": "x"}}]
    fake_result = json.dumps([{"id": "e1"}])  # kết quả không rỗng → không kích self-correct
    with patch.object(server, "call_tool", lambda name, args: fake_result):
        erc = server._execute_pending_calls(pending, None, messages, suggestions, 0, 0, 1)
    assert isinstance(erc, int)                              # trả về empty_results_count
    assert len(messages) == 1 and messages[0]["role"] == "tool"
    assert messages[0]["tool_call_id"] == "t1"
    assert messages[0]["content"] == fake_result            # tool result được append nguyên vẹn


def test_execute_pending_calls_parallel_path():
    """Parallel path (parallel_exec + >1 call): dùng execute_smart, append đủ tool-message."""
    messages, suggestions = [], []
    pending = [
        {"id": "t1", "name": "search", "args": {"query": "a"}},
        {"id": "t2", "name": "stats", "args": {}},
    ]
    r1, r2 = json.dumps([{"id": "e1"}]), json.dumps({"total": 5})
    fake_exec = SimpleNamespace(execute_smart=lambda items: [
        {"result": r1, "duration_ms": 1.0}, {"result": r2, "duration_ms": 2.0}])
    erc = server._execute_pending_calls(pending, fake_exec, messages, suggestions, 0, 0, 2)
    assert isinstance(erc, int)
    assert [m["tool_call_id"] for m in messages] == ["t1", "t2"]
    assert messages[0]["content"] == r1 and messages[1]["content"] == r2
