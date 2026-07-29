"""Real-transport coverage for mandatory chat privacy boundaries."""

import asyncio
import inspect
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest
from starlette.requests import Request

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
STREAM_EMAIL = "secret@example.com"
LEGACY_PHONE = "0901234567"
LEGACY_EMAIL = "legacy-cache@example.com"
PUBLIC_PHONE = "02703822000"


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


def _tool_completion(name, arguments):
    tool_call = SimpleNamespace(
        id="tool-call-1",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )
    message = SimpleNamespace(
        content=None,
        tool_calls=[tool_call],
        role="assistant",
        function_call=None,
    )
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="tool_calls", index=0)],
        usage=usage,
    )


def _sse_frames(wire_text):
    return [
        json.loads(line.removeprefix("data:").strip())
        for line in wire_text.splitlines()
        if line.startswith("data:")
    ]


def _capture_receipts(monkeypatch, token="test-feedback-receipt"):
    calls = []

    def issue(owner_key, assistant_turn_digest, model_variant, tool_bucket, **kwargs):
        calls.append({
            "owner_key": owner_key,
            "assistant_turn_digest": assistant_turn_digest,
            "model_variant": model_variant,
            "tool_bucket": tool_bucket,
            "kwargs": kwargs,
        })
        return SimpleNamespace(token=token)

    monkeypatch.setattr(server, "issue_feedback_receipt", issue, raising=False)
    return calls


def _terminal_done(wire_text):
    done = [frame for frame in _sse_frames(wire_text) if frame.get("type") == "done"]
    assert len(done) == 1
    return done[0]


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
    receipt_calls = _capture_receipts(monkeypatch)
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
    assert response.json()["feedback_receipt"] == "test-feedback-receipt"
    assert len(receipt_calls) == 1
    assert receipt_calls[0]["owner_key"] == "user:privacy-test"
    assert len(receipt_calls[0]["assistant_turn_digest"]) == 64
    assert receipt_calls[0]["model_variant"] == "other"
    assert receipt_calls[0]["tool_bucket"] == "none"
    assert "0901234567" not in repr(receipt_calls)
    assert "a@example.com" not in repr(receipt_calls)
    _assert_provider_inputs_are_safe(captured_messages)


@pytest.mark.anyio
async def test_sse_provider_receives_only_redacted_message_and_history(
    monkeypatch,
    tmp_path,
):
    _manager_instance, captured_messages = _configure_chat(monkeypatch, tmp_path)
    receipt_calls = _capture_receipts(monkeypatch)
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
    assert _terminal_done(response.text)["feedback_receipt"] == "test-feedback-receipt"
    assert len(receipt_calls) == 1
    assert receipt_calls[0]["owner_key"] == "user:privacy-test"
    assert len(receipt_calls[0]["assistant_turn_digest"]) == 64
    assert receipt_calls[0]["model_variant"] == "other"
    assert receipt_calls[0]["tool_bucket"] == "none"
    assert "0901234567" not in repr(receipt_calls)
    assert "a@example.com" not in repr(receipt_calls)
    _assert_provider_inputs_are_safe(captured_messages)
    assert all("0901234567" not in repr(messages) for messages in captured_messages)


@pytest.mark.anyio
@pytest.mark.parametrize("split_index", range(1, len(STREAM_EMAIL)))
async def test_sse_redacts_email_across_every_provider_chunk_boundary(
    monkeypatch,
    tmp_path,
    split_index,
):
    _manager_instance, _captured_messages = _configure_chat(monkeypatch, tmp_path)

    def create(*_args, stream=False, **_kwargs):
        if not stream:
            return _completion("decision")

        def chunks():
            for content in (
                "Email ",
                STREAM_EMAIL[:split_index],
                STREAM_EMAIL[split_index:],
                " for details.",
            ):
                yield SimpleNamespace(
                    choices=[SimpleNamespace(
                        delta=SimpleNamespace(content=content, tool_calls=None),
                    )],
                    usage=None,
                )
            yield SimpleNamespace(
                choices=[],
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                ),
            )

        return chunks()

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat/stream",
            json={"message": "hello", "history": []},
        ) as response:
            wire = b"".join([chunk async for chunk in response.aiter_bytes()])

    wire_text = wire.decode("utf-8")
    delivered_text = "".join(
        frame.get("content", "")
        for frame in _sse_frames(wire_text)
        if frame.get("type") == "text"
    )
    assert STREAM_EMAIL not in wire_text
    assert STREAM_EMAIL not in delivered_text
    assert "[EMAIL]" in delivered_text


@pytest.mark.anyio
async def test_sse_redacts_provider_tool_metadata_before_wire(
    monkeypatch,
    tmp_path,
):
    _manager_instance, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    decision_count = 0

    def create(*_args, stream=False, **_kwargs):
        nonlocal decision_count
        if stream:
            return _stream_chunks("Safe final answer.")
        decision_count += 1
        if decision_count == 1:
            return _tool_completion(
                STREAM_EMAIL,
                {"query": f"Call {LEGACY_PHONE}"},
            )
        return _completion("decision complete")

    monkeypatch.setattr(
        server,
        "get_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        ),
    )
    monkeypatch.setattr(server, "call_tool", lambda *_args, **_kwargs: '{"ok": true}')
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/stream",
            json={"message": "trace a provider tool", "history": []},
        )

    assert response.status_code == 200
    assert STREAM_EMAIL not in response.text
    assert LEGACY_PHONE not in response.text
    tool_frames = [
        frame
        for frame in _sse_frames(response.text)
        if frame.get("type") in {"tool_start", "tool_done"}
    ]
    assert {frame["type"] for frame in tool_frames} == {"tool_start", "tool_done"}
    assert "[EMAIL]" in repr(tool_frames)
    assert "[PHONE]" in repr(tool_frames)


@pytest.mark.anyio
async def test_sse_preserves_only_current_verified_public_contact(
    monkeypatch,
    tmp_path,
):
    _manager_instance, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    decision_count = 0
    monkeypatch.setattr(
        server.knowledge,
        "_entities",
        {
            "public-office": {
                "id": "public-office",
                "status": "published",
                "verified": True,
                "attributes": {"phone": PUBLIC_PHONE},
            },
        },
    )

    def create(*_args, stream=False, **_kwargs):
        nonlocal decision_count
        if stream:
            return _stream_chunks(
                f"Call {PUBLIC_PHONE}; ignore invented {STREAM_EMAIL}."
            )
        decision_count += 1
        if decision_count == 1:
            return _tool_completion("entity_detail", {"entity_id": "public-office"})
        return _completion("decision complete")

    monkeypatch.setattr(
        server,
        "get_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        ),
    )
    monkeypatch.setattr(
        server,
        "call_tool",
        lambda *_args, **_kwargs: json.dumps({
            "id": "public-office",
            "phone": PUBLIC_PHONE,
        }),
    )
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/stream",
            json={"message": "show the verified public contact", "history": []},
        )

    delivered_text = "".join(
        frame.get("content", "")
        for frame in _sse_frames(response.text)
        if frame.get("type") == "text"
    )
    assert response.status_code == 200
    assert PUBLIC_PHONE in delivered_text
    assert STREAM_EMAIL not in response.text
    assert "[EMAIL]" in delivered_text


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/chat", "/chat/stream"])
@pytest.mark.parametrize("cache_kind", ["semantic", "exact"])
async def test_legacy_cache_is_sanitized_before_delivery_sinks_and_refresh(
    monkeypatch,
    tmp_path,
    path,
    cache_kind,
):
    manager, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    receipt_calls = _capture_receipts(monkeypatch)
    legacy = {
        "reply": f"Legacy phone {LEGACY_PHONE} must not be delivered raw.",
        "tool_calls": [f"lookup({LEGACY_PHONE})"],
        "suggestions": [f"Email {LEGACY_EMAIL}"],
    }
    sink_writes = []
    refresh_writes = []

    async def semantic_read(*_args, **_kwargs):
        return legacy if cache_kind == "semantic" else None

    def exact_read(*_args, **_kwargs):
        if cache_kind == "semantic":
            raise AssertionError("semantic hit must not read exact cache")
        return legacy

    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "semantic_get_async", semantic_read)
    monkeypatch.setattr(
        server,
        "semantic_take_dedup_lease",
        lambda *_args, **_kwargs: "legacy-cache-lease",
    )
    monkeypatch.setattr(server, "semantic_abandon", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        server,
        "semantic_put",
        lambda *args, **kwargs: refresh_writes.append((args, kwargs)),
    )
    monkeypatch.setattr(server.cache, "get", exact_read)
    monkeypatch.setattr(
        server,
        "get_client",
        Mock(side_effect=AssertionError("cache hit must not call provider")),
    )
    monkeypatch.setattr(
        manager,
        "on_message",
        lambda *args, **kwargs: sink_writes.append(("memory", args, kwargs)),
    )
    monkeypatch.setattr(
        server.analytics,
        "track_query",
        lambda *args, **kwargs: sink_writes.append(("analytics", args, kwargs)),
    )
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(path, json={"message": "cached", "history": []})

    assert response.status_code == 200
    assert LEGACY_PHONE not in response.text
    assert LEGACY_EMAIL not in response.text
    assert "[PHONE]" in response.text
    assert "[EMAIL]" in response.text
    assert LEGACY_PHONE not in repr(sink_writes)
    assert LEGACY_EMAIL not in repr(sink_writes)
    assert LEGACY_PHONE not in repr(refresh_writes)
    assert LEGACY_EMAIL not in repr(refresh_writes)
    if path == "/chat":
        assert response.json()["feedback_receipt"] == "test-feedback-receipt"
    else:
        assert _terminal_done(response.text)["feedback_receipt"] == "test-feedback-receipt"
    assert len(receipt_calls) == 1
    assert len(receipt_calls[0]["assistant_turn_digest"]) == 64
    assert receipt_calls[0]["model_variant"] == "other"
    assert receipt_calls[0]["tool_bucket"] in {
        "none", "search", "weather", "knowledge", "mixed",
    }
    assert LEGACY_PHONE not in repr(receipt_calls)
    assert LEGACY_EMAIL not in repr(receipt_calls)
    if cache_kind == "exact":
        assert len(refresh_writes) == 1


@pytest.mark.anyio
async def test_post_kb_fallback_issues_receipt_for_delivered_safe_turn(
    monkeypatch,
    tmp_path,
):
    _manager_instance, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    receipt_calls = _capture_receipts(monkeypatch)
    fallback_entity = {
        "id": "fallback-entity",
        "name": "Fallback Place",
        "summary": "Verified fallback summary with enough safe detail.",
        "type": "attraction",
    }

    monkeypatch.setattr(
        server,
        "get_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(
                create=lambda *_args, **_kwargs: _completion(
                    "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."
                )
            )),
        ),
    )
    monkeypatch.setattr(
        server,
        "_hybrid_rerank_search",
        lambda *_args, **_kwargs: [fallback_entity],
    )
    monkeypatch.setattr(server.knowledge, "query_relevance", lambda *_args: True)
    monkeypatch.setattr(server.knowledge, "get_place", lambda *_args: None)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"message": "fallback query", "history": []},
        )

    assert response.status_code == 200
    assert "Fallback Place" in response.json()["reply"]
    assert response.json()["feedback_receipt"] == "test-feedback-receipt"
    assert len(receipt_calls) == 1
    assert receipt_calls[0]["tool_bucket"] == "search"


@pytest.mark.anyio
async def test_post_receipt_uses_the_orchestrator_selected_mini_model(
    monkeypatch,
    tmp_path,
):
    _manager_instance, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    receipt_calls = _capture_receipts(monkeypatch)
    routed_agent = SimpleNamespace(use_mini=True)
    fake_orchestrator = SimpleNamespace(route=lambda _message: ("general", routed_agent))

    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", True)
    monkeypatch.setattr(server, "_get_orchestrator", lambda: fake_orchestrator)
    monkeypatch.setattr(
        server,
        "_run_agent_orchestrated",
        lambda *_args, **_kwargs: (PROVIDER_REPLY, [], []),
    )
    monkeypatch.setattr(server, "get_model", lambda: "cx/gpt-5.5")
    monkeypatch.setattr(server, "get_model_mini", lambda: "cx/gpt-5.5-mini")
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "message": "mini model route",
                "history": [{"role": "user", "content": "bounded context"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["feedback_receipt"] == "test-feedback-receipt"
    assert len(receipt_calls) == 1
    assert receipt_calls[0]["model_variant"] == "cx-gpt-5-5-mini"


@pytest.mark.parametrize(
    ("model_variant", "tools", "expected_model", "expected_bucket"),
    [
        ("cx/gpt-5.5", [], "cx-gpt-5-5", "none"),
        ("cx/gpt-5.4-mini", ["weather"], "cx-gpt-5-4-mini", "weather"),
        ("unknown-model", ["unknown-tool"], "other", "mixed"),
        ("cx/gpt-5.4", ["search", "weather"], "cx-gpt-5-4", "mixed"),
        ("cx/gpt-5.4", ["entity_detail"], "cx-gpt-5-4", "knowledge"),
    ],
)
def test_feedback_receipt_helper_hashes_turn_and_bounds_dimensions(
    monkeypatch,
    model_variant,
    tools,
    expected_model,
    expected_bucket,
):
    receipt_calls = _capture_receipts(monkeypatch)

    first = server._issue_delivered_feedback_receipt(
        "user:00000000-0000-0000-0000-000000000001",
        "private-message-ab",
        "private-reply-c",
        model_variant,
        tools,
    )
    second = server._issue_delivered_feedback_receipt(
        "user:00000000-0000-0000-0000-000000000001",
        "private-message-a",
        "private-reply-bc",
        model_variant,
        tools,
    )

    assert first == second == "test-feedback-receipt"
    assert len(receipt_calls) == 2
    assert receipt_calls[0]["assistant_turn_digest"] != receipt_calls[1]["assistant_turn_digest"]
    assert all(len(call["assistant_turn_digest"]) == 64 for call in receipt_calls)
    assert all(call["model_variant"] == expected_model for call in receipt_calls)
    assert all(call["tool_bucket"] == expected_bucket for call in receipt_calls)
    assert "private-message" not in repr(receipt_calls)
    assert "private-reply" not in repr(receipt_calls)


def test_feedback_receipt_helper_failure_is_best_effort_and_logs_stable_code(
    monkeypatch,
    caplog,
):
    def unavailable(*_args, **_kwargs):
        raise RuntimeError("raw database detail secret@example.com")

    monkeypatch.setattr(server, "issue_feedback_receipt", unavailable, raising=False)

    with caplog.at_level("WARNING"):
        result = server._issue_delivered_feedback_receipt(
            "user:00000000-0000-0000-0000-000000000001",
            "safe message",
            "safe reply",
            "cx/gpt-5.5",
            [],
        )

    assert result is None
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "FEEDBACK_RECEIPT_DELIVERY_ISSUE_FAILED" in output
    assert "secret@example.com" not in output


@pytest.mark.anyio
async def test_stream_redactor_error_emits_generic_error_and_writes_nothing(
    monkeypatch,
    tmp_path,
):
    manager, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    writes = []
    abandoned = []
    instances = []

    class ExplodingRedactor:
        def __init__(self, **_kwargs):
            self.aborted = False
            instances.append(self)

        def feed(self, _chunk):
            raise PrivacyBoundaryUnavailable("RAW_REDACTOR_DETAIL")

        def finish(self):
            raise AssertionError("failed redactor must not finish")

        def abort(self):
            self.aborted = True

    async def semantic_miss(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server, "StreamingPIIRedactor", ExplodingRedactor, raising=False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "semantic_get_async", semantic_miss)
    monkeypatch.setattr(
        server,
        "semantic_take_dedup_lease",
        lambda *_args, **_kwargs: "redactor-error-lease",
    )
    monkeypatch.setattr(
        server,
        "semantic_abandon",
        lambda *args, **kwargs: abandoned.append((args, kwargs)) or True,
    )
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server.cache,
        "put",
        lambda *args, **kwargs: writes.append(("cache", args, kwargs)),
    )
    monkeypatch.setattr(
        server,
        "semantic_put",
        lambda *args, **kwargs: writes.append(("semantic", args, kwargs)),
    )
    monkeypatch.setattr(
        manager,
        "on_message",
        lambda *args, **kwargs: writes.append(("memory", args, kwargs)),
    )
    monkeypatch.setattr(
        server.analytics,
        "track_query",
        lambda *args, **kwargs: writes.append(("analytics", args, kwargs)),
    )

    def create(*_args, stream=False, **_kwargs):
        return _stream_chunks(f"raw {LEGACY_PHONE} reply") if stream else _completion("decision")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/stream",
            json={"message": "redactor failure", "history": []},
        )

    assert response.status_code == 200
    assert LEGACY_PHONE not in response.text
    assert "RAW_REDACTOR_DETAIL" not in response.text
    assert any(frame.get("type") == "error" for frame in _sse_frames(response.text))
    assert writes == []
    assert abandoned
    assert instances and instances[0].aborted is True


def test_stream_cancellation_aborts_withheld_suffix_and_skips_sinks(
    monkeypatch,
    tmp_path,
):
    manager, _captured_messages = _configure_chat(monkeypatch, tmp_path)
    provider_started = threading.Event()
    release_provider = threading.Event()
    writes = []
    abandoned = []
    instances = []

    class WithholdingRedactor:
        def __init__(self, **_kwargs):
            self.aborted = False
            instances.append(self)

        def feed(self, chunk):
            assert chunk == "0901"
            return ""

        def finish(self):
            raise AssertionError("cancelled redactor must not finish")

        def abort(self):
            self.aborted = True

    class BlockingCompletions:
        def create(self, *_args, stream=False, **_kwargs):
            if not stream:
                return _completion("decision")

            def chunks():
                yield SimpleNamespace(
                    choices=[SimpleNamespace(
                        delta=SimpleNamespace(content="0901", tool_calls=None),
                    )],
                    usage=None,
                )
                provider_started.set()
                release_provider.wait(timeout=2)

            return chunks()

    async def semantic_miss(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server, "StreamingPIIRedactor", WithholdingRedactor, raising=False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "semantic_get_async", semantic_miss)
    monkeypatch.setattr(
        server,
        "semantic_take_dedup_lease",
        lambda *_args, **_kwargs: "cancelled-redactor-lease",
    )
    monkeypatch.setattr(
        server,
        "semantic_abandon",
        lambda *args, **kwargs: abandoned.append((args, kwargs)) or True,
    )
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server.cache,
        "put",
        lambda *args, **kwargs: writes.append(("cache", args, kwargs)),
    )
    monkeypatch.setattr(
        server,
        "semantic_put",
        lambda *args, **kwargs: writes.append(("semantic", args, kwargs)),
    )
    monkeypatch.setattr(
        manager,
        "on_message",
        lambda *args, **kwargs: writes.append(("memory", args, kwargs)),
    )
    monkeypatch.setattr(
        manager,
        "on_chat_complete",
        lambda *args, **kwargs: writes.append(("memory_extract", args, kwargs)),
    )
    monkeypatch.setattr(
        server.analytics,
        "track_query",
        lambda *args, **kwargs: writes.append(("analytics", args, kwargs)),
    )
    monkeypatch.setattr(
        server,
        "issue_feedback_receipt",
        lambda *args, **kwargs: writes.append(("receipt", args, kwargs)),
        raising=False,
    )
    monkeypatch.setattr(
        server,
        "get_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=BlockingCompletions()),
        ),
    )

    async def exercise():
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/chat/stream",
            "raw_path": b"/chat/stream",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
        }
        response = await server.chat_stream(
            server.ChatRequest.model_validate(
                {"message": "cancel withheld suffix", "history": []}
            ),
            Request(scope),
        )
        wire = []

        async def receive():
            await asyncio.Future()

        async def send(message):
            if message["type"] == "http.response.body":
                wire.append(message.get("body", b""))

        response_task = asyncio.create_task(response(scope, receive, send))
        await asyncio.to_thread(provider_started.wait, 2)
        response_task.cancel()
        release_provider.set()
        try:
            await response_task
        except asyncio.CancelledError:
            pass
        return b"".join(wire).decode("utf-8")

    wire_text = asyncio.run(exercise())

    assert "0901" not in wire_text
    assert writes == []
    assert abandoned
    assert instances and instances[0].aborted is True


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
    receipt_issue = Mock(side_effect=AssertionError("blocked turn must not issue receipt"))

    monkeypatch.setattr(server, "prepare_chat_input", boundary_call)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "semantic_get_async", forbidden)
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server.analytics, "track_query", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    monkeypatch.setattr(manager, "create_session", forbidden)
    monkeypatch.setattr(manager, "on_message", forbidden)
    monkeypatch.setattr(manager, "on_chat_complete", forbidden)
    monkeypatch.setattr(server, "issue_feedback_receipt", receipt_issue, raising=False)
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
    receipt_issue.assert_not_called()


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
