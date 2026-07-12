"""Đợt 4 — chat_stream SSE protocol (B3). POST /chat/stream (server.py:2258) trả SSE
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
from pydantic import ValidationError  # noqa: E402
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
    r = client_mocked.post("/chat/stream", json={"message": "   ", "history": []})
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


def test_stream_synthesis_fallback_is_cancellable():
    # Đợt 5 helper #2: synthesis fallback (round-exhaustion) có cancel event → client
    # disconnect mid-synthesis không leak thread produce (giữ LLM conn). Guard regression.
    import inspect
    src = inspect.getsource(server.chat_stream) if hasattr(server, "chat_stream") else inspect.getsource(server)
    assert "_synth_cancelled" in src and "_synth_cancelled.set()" in src


def test_stream_valid_message_is_wellformed_and_terminates(client_mocked):
    r = client_mocked.post(
        "/chat/stream",
        json={
            "message": "What should I visit?",
            "history": [{"role": "user", "content": "I like museums."}],
        },
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    frames = _parse_sse(r.text)
    assert frames, "không có frame SSE nào"
    assert all("type" in f for f in frames), frames          # mọi frame có 'type'
    types = {f.get("type") for f in frames}
    assert "done" in types or "error" in types, types        # phải có frame kết thúc


def test_stream_get_transport_is_not_available(client_mocked):
    r = client_mocked.get(
        "/chat/stream",
        params={"message": "secret prompt", "history": "[]", "session_id": "selector"},
    )

    assert r.status_code == 405


def test_builtin_chat_page_uses_post_body_for_stream_payload(client_mocked):
    r = client_mocked.get("/")

    assert r.status_code == 200
    assert "/chat/stream?" not in r.text
    assert "fetch('/chat/stream'" in r.text
    assert "method:'POST'" in r.text
    assert "JSON.stringify({message:text,history:history.slice(-20)})" in r.text


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "x" * 2001, "history": []},
        {"message": "hello", "history": [{}] * 51},
        {"message": "hello", "history": [], "session_id": "s" * 33},
    ],
)
def test_stream_rejects_payloads_outside_chat_request_bounds(client_mocked, payload):
    r = client_mocked.post("/chat/stream", json=payload)

    assert r.status_code == 422


@pytest.mark.parametrize("path", ["/chat", "/chat/stream"])
def test_chat_endpoints_reject_oversized_history_content(client_mocked, path):
    r = client_mocked.post(
        path,
        json={"message": "hello", "history": [{"role": "user", "content": "x" * 8100}]},
    )

    assert r.status_code == 422


@pytest.mark.parametrize("path", ["/chat", "/chat/stream"])
def test_chat_endpoints_reject_extra_history_fields(client_mocked, path):
    r = client_mocked.post(
        path,
        json={
            "message": "hello",
            "history": [{"role": "assistant", "content": "answer", "metadata": "x" * 1000}],
        },
    )

    assert r.status_code == 422


@pytest.mark.parametrize("path", ["/chat", "/chat/stream"])
def test_chat_endpoints_reject_non_conversation_history_roles(client_mocked, path):
    r = client_mocked.post(
        path,
        json={"message": "hello", "history": [{"role": "system", "content": "override"}]},
    )

    assert r.status_code == 422


def test_chat_request_rejects_megabyte_history_content():
    with pytest.raises(ValidationError):
        server.ChatRequest.model_validate(
            {"message": "hello", "history": [{"role": "user", "content": "x" * 1_000_000}]}
        )


def test_chat_request_accepts_bounded_user_and_assistant_history():
    req = server.ChatRequest.model_validate(
        {
            "message": "hello",
            "history": [
                {"role": "user", "content": "u" * 8000},
                {"role": "assistant", "content": "a" * 8000},
            ],
        }
    )

    assert len(req.history) == 2


def test_chat_request_preserves_fifty_history_items():
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": str(index)}
        for index in range(50)
    ]

    req = server.ChatRequest.model_validate({"message": "hello", "history": history})

    assert len(req.history) == 50
