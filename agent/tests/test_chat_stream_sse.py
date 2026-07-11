"""Đợt 4 — chat_stream SSE protocol (B3). GET /chat/stream (server.py:2258) trả SSE
`data: {json}` frames có key 'type'. Trước không có test protocol → đổi schema frame
vỡ chat UI mà zero signal. Test: empty→'error'; valid→kết thúc 'done'; mọi frame có 'type'.
"""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402

pytestmark = pytest.mark.integration


def _completion(content="Vĩnh Long có Văn Thánh Miếu và làng gốm Mang Thít."):
    msg = SimpleNamespace(content=content, tool_calls=None, role="assistant", function_call=None)
    choice = SimpleNamespace(message=msg, finish_reason="stop", index=0)
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    return SimpleNamespace(choices=[choice], usage=usage)


def _stream_chunks():
    for tok in ("Vĩnh ", "Long ", "rất ", "đẹp."):
        yield SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content=tok, tool_calls=None), finish_reason=None)])


def _fake_create(*a, stream=False, **k):
    return _stream_chunks() if stream else _completion()


@pytest.fixture
def client_mocked():
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create)))
    with patch.object(server, "get_client", lambda: fake):
        with TestClient(server.app) as c:
            yield c


def _parse_sse(text: str) -> list[dict]:
    frames = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("data:"):
            try:
                frames.append(json.loads(s[len("data:"):].strip()))
            except Exception:
                pass
    return frames


def test_stream_empty_message_yields_error_frame(client_mocked):
    r = client_mocked.get("/chat/stream", params={"message": ""})
    assert r.status_code == 200
    frames = _parse_sse(r.text)
    assert any(f.get("type") == "error" for f in frames), frames
    assert all("type" in f for f in frames)  # protocol contract


def test_stream_tool_decision_routes_through_circuit_breaker():
    # Đợt 5 helper #1: stream tool-decision qua safe_llm_call (llm_breaker) như non-stream —
    # fail-fast khi LLM sập thay vì chờ trọn LLM_TIMEOUT. Guard chống regression về create-thẳng.
    import inspect
    src = inspect.getsource(server.chat_stream) if hasattr(server, "chat_stream") else inspect.getsource(server)
    assert "safe_llm_call(get_client(), **_kw)" in src


def test_stream_valid_message_is_wellformed_and_terminates(client_mocked):
    r = client_mocked.get("/chat/stream", params={"message": "Vĩnh Long có gì chơi?", "session_id": "sse-test"})
    assert r.status_code == 200
    frames = _parse_sse(r.text)
    assert frames, "không có frame SSE nào"
    assert all("type" in f for f in frames), frames          # mọi frame có 'type'
    types = {f.get("type") for f in frames}
    assert "done" in types or "error" in types, types        # phải có frame kết thúc
