"""Đợt 4 — chat_stream SSE protocol (B3). POST /chat/stream (server.py:2258) trả SSE
`data: {json}` frames có key 'type'. Trước không có test protocol → đổi schema frame
vỡ chat UI mà zero signal. Test: empty→'error'; valid→kết thúc 'done'; mọi frame có 'type'.
"""
import json
import asyncio
import os
import sys
import threading
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
import anyio  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from starlette.requests import Request  # noqa: E402
import server  # noqa: E402


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


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_server_drain_flag():
    server._draining = False
    yield
    server._draining = False


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
    helper_src = inspect.getsource(server._call_stream_decision)
    assert "_call_stream_decision" in src
    assert "safe_llm_call(get_client(), **kwargs)" in helper_src


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


class _UsageGuardrail:
    def __init__(self):
        self.calls = []

    def record_usage(self, owner_key, tokens, cost=0.0):
        self.calls.append((owner_key, tokens, cost))


class _UsageAttribution:
    def __init__(self):
        self.calls = []

    def record(self, session_id, query, agent_name, tool_name, model, tokens, cost):
        self.calls.append({
            "session_id": session_id,
            "query": query,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "model": model,
            "tokens": tokens,
            "cost": cost,
        })


def _configure_usage_stream(monkeypatch, create):
    async def resolve_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    guardrail = _UsageGuardrail()
    attribution = _UsageAttribution()
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(server, "_draining", False)
    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner, raising=False)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", True)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", True)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", False)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", False)
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "HAS_DYNAMIC_AGENTS", False)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", False)
    monkeypatch.setattr(server, "HAS_MEMORY_GRAPH", False)
    monkeypatch.setattr(server, "HAS_EXPERIENCE", False)
    monkeypatch.setattr(server, "HAS_FEWSHOT", False)
    monkeypatch.setattr(server, "HAS_LLM_JUDGE", False)
    monkeypatch.setattr(server, "HAS_AB_TESTING", False)
    monkeypatch.setattr(server, "HAS_METRICS", False)
    monkeypatch.setattr(server, "check_input", lambda *_args: {"allowed": True})
    monkeypatch.setattr(server, "check_output", lambda reply, *_args: {"cleaned_reply": reply})
    monkeypatch.setattr(server, "guardrail_budget", guardrail)
    monkeypatch.setattr(server, "cost_attribution", attribution)
    monkeypatch.setattr(server, "get_client", lambda: fake)
    monkeypatch.setattr(server, "get_model", lambda: "cx/gpt-5.4")
    monkeypatch.setattr(server, "get_model_mini", lambda: "cx/gpt-5.4")
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda *_args: ([{"role": "system", "content": "complete context"}], {}),
    )
    monkeypatch.setattr(server.memory_manager, "on_message", lambda *_args: None)
    monkeypatch.setattr(server.memory_manager, "on_chat_complete", lambda *_args: None)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server.reflexion_engine,
        "evaluate_answer",
        lambda *_args: {"score": 6},
    )
    monkeypatch.setattr(server.quality_tracker, "record", lambda *_args: None)
    return guardrail, attribution


def _assert_exact_stream_usage(guardrail, attribution):
    assert guardrail.calls == [("user:alice", 335, 0.0)]
    assert len(attribution.calls) == 1
    assert attribution.calls[0]["tokens"] == {
        "prompt_tokens": 300,
        "completion_tokens": 35,
        "total_tokens": 335,
        "provider_call_count": 2,
        "estimated_call_count": 0,
    }


def _assert_only_completed_decision_usage(guardrail, attribution):
    assert guardrail.calls == [("user:alice", 130, 0.0)]
    assert len(attribution.calls) == 1
    assert attribution.calls[0]["tokens"] == {
        "prompt_tokens": 120,
        "completion_tokens": 10,
        "total_tokens": 130,
        "provider_call_count": 1,
        "estimated_call_count": 0,
    }
    assert attribution.calls[0]["cost"] == 0.00075


def test_stream_consumes_terminal_usage_once_and_requests_usage(monkeypatch):
    stream_kwargs = []

    def create(*_args, stream=False, **kwargs):
        if not stream:
            return _completion_with_usage("decision", 120, 10)
        stream_kwargs.append(kwargs)
        return iter([
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="final answer"))],
                usage=None,
            ),
            SimpleNamespace(
                choices=[],
                usage=SimpleNamespace(
                    prompt_tokens=180,
                    completion_tokens=25,
                    total_tokens=205,
                ),
            ),
        ])

    guardrail, attribution = _configure_usage_stream(monkeypatch, create)
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        },
    )

    assert response.status_code == 200
    assert any(frame.get("type") == "done" for frame in _parse_sse(response.text))
    assert stream_kwargs[0]["stream_options"] == {"include_usage": True}
    _assert_exact_stream_usage(guardrail, attribution)


def _completion_with_usage(content, prompt_tokens, completion_tokens):
    message = SimpleNamespace(
        content=content,
        tool_calls=None,
        role="assistant",
        function_call=None,
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


class _NestedCancellationProbe:
    def __init__(self):
        self.release_nested = threading.Event()
        self.nested_started = threading.Event()
        self.nested_add_attempted = threading.Event()
        self.release_provider = self.release_nested
        self.provider_started = self.nested_started
        self.provider_add_attempted = self.nested_add_attempted
        self.add_after_settlement = threading.Event()
        self.settlement_started = threading.Event()
        self.call_count = 0
        self.accumulators = []
        self.original_record_usage = None
        self.consumer_done = threading.Event()
        self.cancelled = False
        self.frames = []

    def create(self, *_args, stream=False, **_kwargs):
        assert stream is False
        self.call_count += 1
        if self.call_count == 1:
            tool_call = SimpleNamespace(
                id="call-followups",
                function=SimpleNamespace(
                    name="suggest_followups",
                    arguments='{"context":"stream context"}',
                ),
            )
            decision = _completion_with_usage(None, 7, 4)
            decision.choices[0].message.tool_calls = [tool_call]
            return decision
        self.nested_started.set()
        self.release_nested.wait(timeout=5)
        return _completion_with_usage(
            '["Goi y 1?", "Goi y 2?", "Goi y 3?"]',
            15,
            7,
        )

    def record_usage(self, *args, **kwargs):
        self.original_record_usage(*args, **kwargs)
        self.settlement_started.set()


class _RecordingStreamAccumulator(server.UsageAccumulator):
    def __init__(self, probe):
        super().__init__()
        self._probe = probe
        probe.accumulators.append(self)

    def add_response(self, response, *args, **kwargs):
        total_tokens = getattr(getattr(response, "usage", None), "total_tokens", 0)
        settled_before_add = self.snapshot().settled
        try:
            return super().add_response(response, *args, **kwargs)
        finally:
            if total_tokens == 22:
                if settled_before_add:
                    self._probe.add_after_settlement.set()
                self._probe.nested_add_attempted.set()


class _DecisionCancellationProbe:
    def __init__(self):
        self.release_provider = threading.Event()
        self.provider_started = threading.Event()
        self.provider_add_attempted = threading.Event()
        self.add_after_settlement = threading.Event()
        self.settlement_started = threading.Event()
        self.consumer_done = threading.Event()
        self.cancelled = False
        self.frames = []
        self.accumulators = []

    def create(self, *_args, stream=False, **_kwargs):
        assert stream is False
        self.provider_started.set()
        self.release_provider.wait(timeout=5)
        return _completion_with_usage("decision", 15, 7)


class _RecordingDecisionAccumulator(server.UsageAccumulator):
    def __init__(self, probe):
        super().__init__()
        self._probe = probe
        probe.accumulators.append(self)

    def add_response(self, response, *args, **kwargs):
        settled_before_add = self.snapshot().settled
        try:
            return super().add_response(response, *args, **kwargs)
        finally:
            if settled_before_add:
                self._probe.add_after_settlement.set()
            self._probe.provider_add_attempted.set()

    def settle(self, *args, **kwargs):
        self._probe.settlement_started.set()
        return super().settle(*args, **kwargs)


async def _cancel_blocked_nested_stream(probe):
    scope = {
        "type": "http",
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
        server.ChatRequest.model_validate({
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        }),
        Request(scope),
    )
    generator = response.body_iterator
    first = await anext(generator)
    assert _parse_sse(first)[0]["name"] == "suggest_followups"
    consumer = asyncio.create_task(anext(generator))
    started = await asyncio.to_thread(probe.nested_started.wait, 2)
    if not started:
        probe.release_nested.set()
    assert started

    consumer.cancel()
    observed = {
        "settled_before_release": await asyncio.to_thread(
            probe.settlement_started.wait,
            0.25,
        ),
        "consumer_done_before_release": consumer.done(),
    }
    probe.release_nested.set()
    try:
        await consumer
    except asyncio.CancelledError:
        observed["cancelled"] = True
    observed["nested_add_attempted"] = await asyncio.to_thread(
        probe.nested_add_attempted.wait,
        2,
    )
    await generator.aclose()
    return observed


async def _consume_stream_until_anyio_cancellation(probe):
    try:
        response = await server.chat_stream(
            server.ChatRequest.model_validate({
                "message": "where should I go?",
                "history": [{"role": "user", "content": "prior"}],
            }),
            Request({
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/chat/stream",
                "raw_path": b"/chat/stream",
                "query_string": b"",
                "headers": [],
                "client": ("127.0.0.1", 1234),
                "server": ("testserver", 80),
            }),
        )
        async for event in response.body_iterator:
            probe.frames.extend(_parse_sse(event))
    except anyio.get_cancelled_exc_class():
        probe.cancelled = True
        raise
    finally:
        probe.consumer_done.set()


async def _cancel_anyio_group_after_provider_starts(probe, started_event, add_event):
    observed = {}
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(_consume_stream_until_anyio_cancellation, probe)
        observed["started"] = await anyio.to_thread.run_sync(started_event.wait, 2)
        task_group.cancel_scope.cancel()
        with anyio.CancelScope(shield=True):
            observed["settled_before_release"] = await anyio.to_thread.run_sync(
                probe.settlement_started.wait,
                0.25,
            )
            observed["consumer_done_before_release"] = probe.consumer_done.is_set()
            probe.release_provider.set()
            observed["add_attempted"] = await anyio.to_thread.run_sync(
                add_event.wait,
                2,
            )
    return observed


async def _double_cancel_stream_consumer(probe):
    consumer = asyncio.create_task(_consume_stream_until_anyio_cancellation(probe))
    started = await asyncio.to_thread(probe.provider_started.wait, 2)
    consumer.cancel()
    asyncio.get_running_loop().call_soon(consumer.cancel)
    await asyncio.sleep(0)
    observed = {
        "started": started,
        "settled_before_release": await asyncio.to_thread(
            probe.settlement_started.wait,
            0.25,
        ),
        "consumer_done_before_release": consumer.done(),
        "cancel_count": consumer.cancelling(),
    }
    probe.release_provider.set()
    observed["add_attempted"] = await asyncio.to_thread(
        probe.provider_add_attempted.wait,
        2,
    )
    try:
        await consumer
    except asyncio.CancelledError:
        observed["cancelled"] = True
    return observed


def _assert_nested_cancel_behavior(probe, observed):
    assert observed == {
        "settled_before_release": False,
        "consumer_done_before_release": False,
        "cancelled": True,
        "nested_add_attempted": True,
    }
    assert probe.add_after_settlement.is_set() is False
    assert len(probe.accumulators) == 1
    assert probe.accumulators[0].snapshot().settled is True


def _assert_nested_cancel_usage(probe, guardrail, attribution):
    snapshot = probe.accumulators[0].snapshot()
    assert snapshot.prompt_tokens == 22
    assert snapshot.completion_tokens == 11
    assert snapshot.total_tokens == 33
    assert snapshot.provider_call_count == 2
    assert guardrail.calls == [("user:alice", 33, 0.0)]
    assert len(attribution.calls) == 1
    assert attribution.calls[0]["tokens"] == {
        "prompt_tokens": 22,
        "completion_tokens": 11,
        "total_tokens": 33,
        "provider_call_count": 2,
        "estimated_call_count": 0,
    }


def _assert_anyio_cancellation_waited(probe, observed):
    assert observed == {
        "started": True,
        "settled_before_release": False,
        "consumer_done_before_release": False,
        "add_attempted": True,
    }
    assert probe.cancelled is True
    assert probe.add_after_settlement.is_set() is False
    assert probe.consumer_done.is_set() is True


def _assert_double_native_cancellation_waited(probe, observed):
    assert observed == {
        "started": True,
        "settled_before_release": False,
        "consumer_done_before_release": False,
        "cancel_count": 2,
        "add_attempted": True,
        "cancelled": True,
    }
    assert probe.add_after_settlement.is_set() is False
    assert probe.consumer_done.is_set() is True


def _assert_decision_cancel_usage(probe, guardrail, attribution):
    assert probe.frames == []
    assert len(probe.accumulators) == 1
    snapshot = probe.accumulators[0].snapshot()
    assert snapshot.settled is True
    assert snapshot.prompt_tokens == 15
    assert snapshot.completion_tokens == 7
    assert snapshot.total_tokens == 22
    assert snapshot.provider_call_count == 1
    assert guardrail.calls == [("user:alice", 22, 0.0)]
    assert attribution.calls[0]["tokens"]["total_tokens"] == 22
    assert attribution.calls[0]["tokens"]["provider_call_count"] == 1


def test_stream_missing_terminal_usage_estimates_complete_call_once(monkeypatch):
    def create(*_args, stream=False, **_kwargs):
        if not stream:
            return _completion_with_usage("decision", 120, 10)
        return iter([
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="generated output"))],
                usage=None,
            ),
        ])

    guardrail, attribution = _configure_usage_stream(monkeypatch, create)
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        },
    )

    assert response.status_code == 200
    assert len(guardrail.calls) == 1
    assert len(attribution.calls) == 1
    tokens = attribution.calls[0]["tokens"]
    assert tokens["provider_call_count"] == 2
    assert tokens["estimated_call_count"] == 1
    assert guardrail.calls[0][1] == tokens["total_tokens"]
    assert guardrail.calls[0][2] == 0.0
    assert attribution.calls[0]["cost"] > 0


def test_stream_round_exhaustion_synthesis_usage_is_included(monkeypatch):
    receipt_calls = []
    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="search", arguments='{"q":"test"}'),
    )

    def create(*_args, stream=False, **_kwargs):
        if not stream:
            response = _completion_with_usage(None, 120, 10)
            response.choices[0].message.tool_calls = [tool_call]
            return response
        return iter([
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="synthesis"))],
                usage=None,
            ),
            SimpleNamespace(
                choices=[],
                usage=SimpleNamespace(
                    prompt_tokens=180,
                    completion_tokens=25,
                    total_tokens=205,
                ),
            ),
        ])

    guardrail, attribution = _configure_usage_stream(monkeypatch, create)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", True)
    monkeypatch.setattr(
        server.parameter_tuner,
        "get_optimal_params",
        lambda _category: {"max_rounds": 1},
    )
    monkeypatch.setattr(
        server.prompt_optimizer,
        "get_current_variant",
        lambda: {"prompt_addon": ""},
    )
    monkeypatch.setattr(server, "call_tool", lambda *_args: "[]")
    monkeypatch.setattr(
        server,
        "issue_feedback_receipt",
        lambda *args, **kwargs: receipt_calls.append((args, kwargs))
        or SimpleNamespace(token="synthesis-receipt"),
    )
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        },
    )

    assert response.status_code == 200
    done = [frame for frame in _parse_sse(response.text) if frame.get("type") == "done"]
    assert len(done) == 1
    assert done[0]["feedback_receipt"] == "synthesis-receipt"
    assert len(receipt_calls) == 1
    assert receipt_calls[0][0][0] == "user:alice"
    assert len(receipt_calls[0][0][1]) == 64
    assert receipt_calls[0][0][2:] == ("cx-gpt-5-4", "search")
    assert guardrail.calls == [("user:alice", 335, 0.0)]
    assert attribution.calls[0]["tokens"]["provider_call_count"] == 2
    assert attribution.calls[0]["tokens"]["estimated_call_count"] == 0


def test_stream_provider_error_after_completed_decision_still_settles(monkeypatch):
    def create(*_args, stream=False, **_kwargs):
        if not stream:
            return _completion_with_usage("decision", 120, 10)

        def failing_stream():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="partial"))],
                usage=None,
            )
            raise ConnectionError("provider stream failed")

        return failing_stream()

    guardrail, attribution = _configure_usage_stream(monkeypatch, create)
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        },
    )

    assert response.status_code == 200
    frames = _parse_sse(response.text)
    assert any(frame.get("type") == "error" for frame in frames)
    assert "provider stream failed" not in response.text

    assert len(guardrail.calls) == 1
    assert len(attribution.calls) == 1
    tokens = attribution.calls[0]["tokens"]
    assert tokens["provider_call_count"] == 2
    assert tokens["estimated_call_count"] == 1
    assert tokens["total_tokens"] > 130


def test_stream_create_failure_does_not_invent_provider_usage(monkeypatch):
    def create(*_args, stream=False, **_kwargs):
        if not stream:
            return _completion_with_usage("decision", 120, 10)
        raise ConnectionError("stream create failed")

    guardrail, attribution = _configure_usage_stream(monkeypatch, create)
    client = TestClient(server.app)

    client.post(
        "/chat/stream",
        json={
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        },
    )

    _assert_only_completed_decision_usage(guardrail, attribution)


def test_stream_decision_failure_attaches_receipt_to_safe_fallback(monkeypatch):
    receipt_calls = []

    def create(*_args, **_kwargs):
        raise ConnectionError("decision failed")

    _configure_usage_stream(monkeypatch, create)
    monkeypatch.setattr(
        server,
        "issue_feedback_receipt",
        lambda *args, **kwargs: receipt_calls.append((args, kwargs))
        or SimpleNamespace(token="fallback-receipt"),
    )
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        },
    )

    done = [frame for frame in _parse_sse(response.text) if frame.get("type") == "done"]
    assert len(done) == 1
    assert done[0]["feedback_receipt"] == "fallback-receipt"
    assert len(receipt_calls) == 1
    assert receipt_calls[0][0][0] == "user:alice"
    assert len(receipt_calls[0][0][1]) == 64
    assert receipt_calls[0][0][2:] == ("cx-gpt-5-4", "none")


def test_stream_synthesis_create_failure_does_not_invent_usage(monkeypatch):
    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="search", arguments='{"q":"test"}'),
    )

    def create(*_args, stream=False, **_kwargs):
        if not stream:
            response = _completion_with_usage(None, 120, 10)
            response.choices[0].message.tool_calls = [tool_call]
            return response
        raise ConnectionError("synthesis create failed")

    guardrail, attribution = _configure_usage_stream(monkeypatch, create)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", True)
    monkeypatch.setattr(
        server.parameter_tuner,
        "get_optimal_params",
        lambda _category: {"max_rounds": 1},
    )
    monkeypatch.setattr(
        server.prompt_optimizer,
        "get_current_variant",
        lambda: {"prompt_addon": ""},
    )
    monkeypatch.setattr(server, "call_tool", lambda *_args: "[]")
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={
            "message": "where should I go?",
            "history": [{"role": "user", "content": "prior"}],
        },
    )

    assert response.status_code == 200
    _assert_only_completed_decision_usage(guardrail, attribution)


def test_stream_generator_close_runs_usage_finalizer(monkeypatch):
    def create(*_args, stream=False, **_kwargs):
        if not stream:
            return _completion_with_usage("decision", 120, 10)
        return iter([
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="partial"))],
                usage=None,
            ),
        ])

    guardrail, attribution = _configure_usage_stream(monkeypatch, create)
    scope = {
        "type": "http",
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

    async def close_after_first_frame():
        response = await server.chat_stream(
            server.ChatRequest.model_validate({
                "message": "where should I go?",
                "history": [{"role": "user", "content": "prior"}],
            }),
            Request(scope),
        )
        generator = response.body_iterator
        first = await anext(generator)
        assert "data:" in first
        await generator.aclose()

    asyncio.run(close_after_first_frame())

    assert len(guardrail.calls) == 1
    assert len(attribution.calls) == 1
    tokens = attribution.calls[0]["tokens"]
    assert tokens["provider_call_count"] == 2
    assert tokens["estimated_call_count"] == 1


def test_stream_cancellation_waits_for_nested_provider_before_settlement(monkeypatch):
    probe = _NestedCancellationProbe()
    guardrail, attribution = _configure_usage_stream(monkeypatch, probe.create)
    probe.original_record_usage = guardrail.record_usage
    monkeypatch.setattr(guardrail, "record_usage", probe.record_usage)
    monkeypatch.setattr(
        server,
        "UsageAccumulator",
        lambda: _RecordingStreamAccumulator(probe),
    )

    observed = asyncio.run(_cancel_blocked_nested_stream(probe))

    _assert_nested_cancel_behavior(probe, observed)
    _assert_nested_cancel_usage(probe, guardrail, attribution)


@pytest.mark.anyio
async def test_anyio_repeated_cancellation_waits_for_nested_provider(monkeypatch):
    probe = _NestedCancellationProbe()
    guardrail, attribution = _configure_usage_stream(monkeypatch, probe.create)
    probe.original_record_usage = guardrail.record_usage
    monkeypatch.setattr(guardrail, "record_usage", probe.record_usage)
    monkeypatch.setattr(
        server,
        "UsageAccumulator",
        lambda: _RecordingStreamAccumulator(probe),
    )

    observed = await _cancel_anyio_group_after_provider_starts(
        probe,
        probe.provider_started,
        probe.provider_add_attempted,
    )

    _assert_anyio_cancellation_waited(probe, observed)
    _assert_nested_cancel_usage(probe, guardrail, attribution)


@pytest.mark.anyio
@pytest.mark.parametrize("use_circuit_breaker", [False, True])
async def test_anyio_cancellation_accounts_blocked_first_decision(
    monkeypatch,
    use_circuit_breaker,
):
    probe = _DecisionCancellationProbe()
    guardrail, attribution = _configure_usage_stream(monkeypatch, probe.create)
    monkeypatch.setattr(
        server,
        "UsageAccumulator",
        lambda: _RecordingDecisionAccumulator(probe),
    )
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", use_circuit_breaker)
    if use_circuit_breaker:
        monkeypatch.setattr(
            server,
            "safe_llm_call",
            lambda *_args, **_kwargs: {
                "success": True,
                "response": probe.create(),
            },
        )

    observed = await _cancel_anyio_group_after_provider_starts(
        probe,
        probe.provider_started,
        probe.provider_add_attempted,
    )

    _assert_anyio_cancellation_waited(probe, observed)
    _assert_decision_cancel_usage(probe, guardrail, attribution)


def test_double_native_cancellation_waits_for_nested_provider(monkeypatch):
    probe = _NestedCancellationProbe()
    guardrail, attribution = _configure_usage_stream(monkeypatch, probe.create)
    probe.original_record_usage = guardrail.record_usage
    monkeypatch.setattr(guardrail, "record_usage", probe.record_usage)
    monkeypatch.setattr(
        server,
        "UsageAccumulator",
        lambda: _RecordingStreamAccumulator(probe),
    )

    observed = asyncio.run(_double_cancel_stream_consumer(probe))

    _assert_double_native_cancellation_waited(probe, observed)
    _assert_nested_cancel_usage(probe, guardrail, attribution)


def test_double_native_cancellation_accounts_first_decision(monkeypatch):
    probe = _DecisionCancellationProbe()
    guardrail, attribution = _configure_usage_stream(monkeypatch, probe.create)
    monkeypatch.setattr(
        server,
        "UsageAccumulator",
        lambda: _RecordingDecisionAccumulator(probe),
    )

    observed = asyncio.run(_double_cancel_stream_consumer(probe))

    _assert_double_native_cancellation_waited(probe, observed)
    _assert_decision_cancel_usage(probe, guardrail, attribution)
