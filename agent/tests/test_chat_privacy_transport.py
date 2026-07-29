"""Real-transport coverage for the mandatory chat input boundary."""

import inspect
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402
from memory import MemoryManager  # noqa: E402
from privacy_boundary import (  # noqa: E402
    PrivacyBoundaryBlocked,
    PrivacyBoundaryUnavailable,
)


PROVIDER_REPLY = "Provider reply with enough safe detail for privacy transport testing."


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_server_drain_flag():
    server._draining = False
    yield
    server._draining = False


def _manager(tmp_path):
    with patch("memory.MEMORY_DIR", tmp_path):
        return MemoryManager()


def _completion(content=PROVIDER_REPLY):
    message = SimpleNamespace(
        content=content,
        tool_calls=None,
        role="assistant",
        function_call=None,
    )
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop", index=0)],
        usage=usage,
    )


def _stream_chunks(content=PROVIDER_REPLY):
    yield SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=None))],
        usage=None,
    )
    yield SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _configure_chat(monkeypatch, tmp_path):
    manager = _manager(tmp_path)
    captured_messages = []

    async def resolve_owner(_request):
        return SimpleNamespace(owner_key="user:privacy-test", cookie_value=None)

    def create(*_args, stream=False, **kwargs):
        captured_messages.append([dict(message) for message in kwargs["messages"]])
        return _stream_chunks() if stream else _completion()

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner, raising=False)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", False)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", False)
    monkeypatch.setattr(server, "HAS_TRACING", False)
    monkeypatch.setattr(server, "HAS_DYNAMIC_AGENTS", False)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", False)
    monkeypatch.setattr(server, "HAS_MEMORY_GRAPH", False)
    monkeypatch.setattr(server, "HAS_EXPERIENCE", False)
    monkeypatch.setattr(server, "HAS_FEWSHOT", False)
    monkeypatch.setattr(server, "HAS_LLM_JUDGE", False)
    monkeypatch.setattr(server, "HAS_AB_TESTING", False)
    monkeypatch.setattr(server, "HAS_METRICS", False)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", False)
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", False)
    monkeypatch.setattr(server, "HAS_PROMPT_CACHE", False)
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    monkeypatch.setattr(server, "get_model", lambda: "test-model")
    monkeypatch.setattr(server, "get_model_mini", lambda: "test-model")
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server.cache, "put", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server.memory_manager, "on_chat_complete", lambda *_args: None)
    monkeypatch.setattr(
        server.reflexion_engine,
        "evaluate_answer",
        lambda *_args: {"score": 6, "issues": [], "good_points": []},
    )
    monkeypatch.setattr(server.quality_tracker, "record", lambda *_args: None)
    monkeypatch.setattr(server, "_hybrid_rerank_search", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(server.knowledge, "search_entities", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        server,
        "_gather_context_pieces",
        lambda *_args: {
            "proactive": "",
            "rag": "",
            "realtime": "",
            "memory": "",
            "graph": "",
            "reflexion": "",
        },
    )
    monkeypatch.setattr(server, "_resolve_base_prompt", lambda _sid: ("system", {}))
    return manager, captured_messages


def _assert_provider_inputs_are_safe(captured_messages):
    assert captured_messages
    serialized = repr(captured_messages)
    assert "0901234567" not in serialized
    assert "a@example.com" not in serialized
    assert "[PHONE]" in serialized
    assert "[EMAIL]" in serialized
    conversational = [
        item
        for item in captured_messages[0]
        if item.get("role") != "system"
    ]
    assert [item["content"] for item in conversational].count("Goi [PHONE]") == 1


@pytest.mark.anyio
async def test_post_provider_receives_only_redacted_message_and_history(
    monkeypatch,
    tmp_path,
):
    _manager_instance, captured_messages = _configure_chat(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Goi 0901234567",
                "history": [
                    {"role": "user", "content": "Mail a@example.com"},
                    {"role": "user", "content": "Goi 0901234567"},
                ],
            },
        )

    assert response.status_code == 200
    _assert_provider_inputs_are_safe(captured_messages)


@pytest.mark.anyio
async def test_sse_provider_receives_only_redacted_message_and_history(
    monkeypatch,
    tmp_path,
):
    _manager_instance, captured_messages = _configure_chat(monkeypatch, tmp_path)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/stream",
            json={
                "message": "Goi 0901234567",
                "history": [
                    {"role": "user", "content": "Mail a@example.com"},
                    {"role": "user", "content": "Goi 0901234567"},
                ],
            },
        )

    assert response.status_code == 200
    assert '"type": "done"' in response.text
    _assert_provider_inputs_are_safe(captured_messages)
    assert all("0901234567" not in repr(messages) for messages in captured_messages)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "error_type", "public_text"),
    [
        ("/chat", PrivacyBoundaryBlocked, "lý do an toàn"),
        ("/chat", PrivacyBoundaryUnavailable, "bận kiểm tra an toàn"),
        ("/chat/stream", PrivacyBoundaryBlocked, "lý do an toàn"),
        ("/chat/stream", PrivacyBoundaryUnavailable, "bận kiểm tra an toàn"),
    ],
)
async def test_boundary_failure_stops_all_content_consumers(
    monkeypatch,
    tmp_path,
    path,
    error_type,
    public_text,
):
    manager, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    boundary_call = Mock(side_effect=error_type("STABLE_TEST_CODE"))
    forbidden = Mock(side_effect=AssertionError("content consumer must not run"))

    monkeypatch.setattr(server, "prepare_chat_input", boundary_call)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "semantic_get_async", forbidden)
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server.analytics, "track_query", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    monkeypatch.setattr(manager, "create_session", forbidden)
    monkeypatch.setattr(manager, "on_message", forbidden)
    monkeypatch.setattr(manager, "on_chat_complete", forbidden)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            path,
            json={
                "message": "Raw 0901234567",
                "history": [{"role": "user", "content": "a@example.com"}],
            },
        )

    assert response.status_code == 200
    assert public_text in response.text
    boundary_call.assert_called_once()
    forbidden.assert_not_called()


@pytest.mark.anyio
async def test_stream_fallback_boundary_failure_does_not_write_memory(
    monkeypatch,
    tmp_path,
):
    manager, _captured_messages = _configure_chat(monkeypatch, tmp_path)

    def unavailable(*_args, **_kwargs):
        raise PrivacyBoundaryUnavailable("OUTPUT_REDACTION_FAILED")

    def provider_failure(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    forbidden = Mock(side_effect=AssertionError("fallback boundary failure must not write"))
    monkeypatch.setattr(server, "_safe_delivered_reply", unavailable)
    monkeypatch.setattr(server, "get_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_failure)),
    ))
    monkeypatch.setattr(manager, "on_message", forbidden)

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/stream",
            json={"message": "hello", "history": []},
        )

    assert response.status_code == 200
    assert "không thể xác minh an toàn" in response.text
    forbidden.assert_not_called()


@pytest.mark.anyio
async def test_stream_output_boundary_failure_does_not_settle_personal_usage(
    monkeypatch,
    tmp_path,
):
    _manager_instance, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    cost_writes = []
    guardrail_writes = []

    monkeypatch.setattr(server, "HAS_COST_TRACKER", True)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", True)
    monkeypatch.setattr(
        server,
        "cost_attribution",
        SimpleNamespace(record=lambda *args, **kwargs: cost_writes.append((args, kwargs))),
    )
    monkeypatch.setattr(
        server,
        "guardrail_budget",
        SimpleNamespace(record_usage=lambda *args, **kwargs: guardrail_writes.append((args, kwargs))),
    )
    monkeypatch.setattr(
        server,
        "_safe_delivered_reply",
        Mock(side_effect=PrivacyBoundaryUnavailable("OUTPUT_REDACTION_FAILED")),
    )

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/stream",
            json={"message": "hello", "history": []},
        )

    assert response.status_code == 200
    assert "không thể xác minh an toàn" in response.text
    assert cost_writes == []
    assert guardrail_writes == []


@pytest.mark.parametrize("route", [server.chat, server.chat_stream])
def test_route_never_reads_raw_chat_fields_after_privacy_boundary(route):
    source = inspect.getsource(route)
    marker = "_privacy_input_boundary_marker"

    assert marker in source
    tail = source.split(marker, 1)[1]
    assert "req.message" not in tail
    assert "req.history" not in tail
    assert "req.history_messages()" not in tail
