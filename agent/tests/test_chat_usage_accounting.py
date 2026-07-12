"""Provider-accurate chat usage accumulation and settlement tests."""

import asyncio
import gc
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import Response  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.requests import Request  # noqa: E402

from chat_usage import UsageAccumulator  # noqa: E402
from cost_tracker import TokenCounter  # noqa: E402
import server  # noqa: E402
import orchestrator  # noqa: E402


def _response(prompt_tokens, completion_tokens, total_tokens=None, content="answer"):
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=(
            prompt_tokens + completion_tokens
            if total_tokens is None
            else total_tokens
        ),
    )
    message = SimpleNamespace(content=content, tool_calls=None, role="assistant")
    return SimpleNamespace(
        usage=usage,
        choices=[SimpleNamespace(message=message)],
    )


class _GuardrailRecorder:
    def __init__(self):
        self.calls = []

    def record_usage(self, owner_key, tokens, cost=0.0):
        self.calls.append((owner_key, tokens, cost))


class _AttributionRecorder:
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


def test_accumulator_aggregates_provider_usage_and_model_aware_cost():
    accumulator = UsageAccumulator()

    accumulator.add_response(
        _response(120, 10),
        model="cx/gpt-5.4",
        messages=[{"role": "user", "content": "first"}],
    )
    accumulator.add_response(
        _response(180, 25),
        model="cx/gpt-5.4-mini",
        messages=[{"role": "user", "content": "second"}],
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == 300
    assert snapshot.completion_tokens == 35
    assert snapshot.total_tokens == 335
    assert snapshot.provider_call_count == 2
    assert snapshot.estimated_call_count == 0
    assert snapshot.cost == 0.000801


@pytest.mark.parametrize(
    ("usage", "expected_prompt", "expected_completion"),
    [
        (SimpleNamespace(prompt_tokens=80, total_tokens=100), 80, 20),
        (SimpleNamespace(completion_tokens=20, total_tokens=100), 80, 20),
    ],
)
def test_partial_provider_usage_derives_one_missing_component(
    usage,
    expected_prompt,
    expected_completion,
):
    response = SimpleNamespace(
        usage=usage,
        choices=[SimpleNamespace(message=SimpleNamespace(content="answer", tool_calls=None))],
    )
    accumulator = UsageAccumulator()

    accumulator.add_response(
        response,
        model="cx/gpt-5.4",
        messages=[{"role": "user", "content": "complete prompt"}],
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == expected_prompt
    assert snapshot.completion_tokens == expected_completion
    assert snapshot.total_tokens == 100
    assert snapshot.estimated_call_count == 1
    assert snapshot.cost == 0.0007


@pytest.mark.parametrize(
    "provider_tokens",
    [
        {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 100},
        {"prompt_tokens": 90, "completion_tokens": 30, "total_tokens": 100},
    ],
)
def test_partial_provider_usage_scales_fallback_split_to_provider_total(provider_tokens):
    class PartialCounter:
        def count_from_response(self, _response):
            return provider_tokens

        def estimate_call_tokens(self, _messages, _completion):
            return {"prompt_tokens": 60, "completion_tokens": 40, "total_tokens": 100}

        def calculate_cost(self, tokens, model):
            from cost_tracker import TokenCounter

            return TokenCounter().calculate_cost(tokens, model)

    accumulator = UsageAccumulator(counter=PartialCounter())

    accumulator.add_response(
        SimpleNamespace(choices=[]),
        model="cx/gpt-5.4",
        messages=[{"role": "user", "content": "complete prompt"}],
        completion_text="complete answer",
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == 60
    assert snapshot.completion_tokens == 40
    assert snapshot.total_tokens == 100
    assert snapshot.estimated_call_count == 1
    assert snapshot.cost == 0.0009


def test_dict_provider_usage_shape_reconstructs_missing_component():
    response = {
        "usage": {"prompt_tokens": 80, "total_tokens": 100},
        "choices": [{"message": {"content": "answer", "tool_calls": None}}],
    }
    accumulator = UsageAccumulator()

    accumulator.add_response(
        response,
        model="cx/gpt-5.4",
        messages=[{"role": "user", "content": "complete prompt"}],
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == 80
    assert snapshot.completion_tokens == 20
    assert snapshot.total_tokens == 100
    assert snapshot.estimated_call_count == 1
    assert snapshot.cost == 0.0007


def test_prompt_only_without_total_preserves_prompt_and_estimates_completion():
    messages = [{"role": "user", "content": "complete prompt"}]
    completion_text = "generated answer"
    expected_completion = TokenCounter().estimate_tokens(completion_text)
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=80),
        choices=[SimpleNamespace(message=SimpleNamespace(content=completion_text, tool_calls=None))],
    )
    accumulator = UsageAccumulator()

    accumulator.add_response(
        response,
        model="cx/gpt-5.4",
        messages=messages,
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == 80
    assert snapshot.completion_tokens == expected_completion
    assert snapshot.total_tokens == 80 + expected_completion
    assert snapshot.estimated_call_count == 1
    assert snapshot.cost == TokenCounter().calculate_cost(
        {"prompt_tokens": 80, "completion_tokens": expected_completion},
        "cx/gpt-5.4",
    )


def test_completion_only_dict_without_total_preserves_completion_and_estimates_prompt():
    messages = [{"role": "user", "content": "complete prompt"}]
    expected_prompt = TokenCounter().estimate_call_tokens(messages, "answer")["prompt_tokens"]
    response = {
        "usage": {"completion_tokens": 20},
        "choices": [{"message": {"content": "answer", "tool_calls": None}}],
    }
    accumulator = UsageAccumulator()

    accumulator.add_response(
        response,
        model="cx/gpt-5.4",
        messages=messages,
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == expected_prompt
    assert snapshot.completion_tokens == 20
    assert snapshot.total_tokens == expected_prompt + 20
    assert snapshot.estimated_call_count == 1
    assert snapshot.cost == TokenCounter().calculate_cost(
        {"prompt_tokens": expected_prompt, "completion_tokens": 20},
        "cx/gpt-5.4",
    )


def test_explicit_total_with_missing_completion_preserves_zero_remainder():
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=100, total_tokens=100),
        choices=[SimpleNamespace(message=SimpleNamespace(content="answer", tool_calls=None))],
    )
    accumulator = UsageAccumulator()

    accumulator.add_response(
        response,
        model="cx/gpt-5.4",
        messages=[{"role": "user", "content": "complete prompt"}],
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == 100
    assert snapshot.completion_tokens == 0
    assert snapshot.total_tokens == 100
    assert snapshot.estimated_call_count == 1
    assert snapshot.cost == 0.0005


def test_components_without_total_are_preserved_and_summed():
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=80, completion_tokens=20),
        choices=[SimpleNamespace(message=SimpleNamespace(content="answer", tool_calls=None))],
    )
    accumulator = UsageAccumulator()

    accumulator.add_response(
        response,
        model="cx/gpt-5.4",
        messages=[{"role": "user", "content": "complete prompt"}],
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == 80
    assert snapshot.completion_tokens == 20
    assert snapshot.total_tokens == 100
    assert snapshot.estimated_call_count == 0
    assert snapshot.cost == 0.0007


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="generated answer", tool_calls=None),
            )],
        ),
        {
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "choices": [{"message": {"content": "generated answer", "tool_calls": None}}],
        },
    ],
)
def test_all_zero_provider_usage_uses_full_call_fallback(response):
    messages = [{"role": "user", "content": "complete prompt"}]
    expected = TokenCounter().estimate_call_tokens(messages, "generated answer")
    accumulator = UsageAccumulator()

    accumulator.add_response(
        response,
        model="cx/gpt-5.4",
        messages=messages,
    )

    snapshot = accumulator.snapshot()
    assert snapshot.prompt_tokens == expected["prompt_tokens"]
    assert snapshot.completion_tokens == expected["completion_tokens"]
    assert snapshot.total_tokens == expected["total_tokens"]
    assert snapshot.total_tokens > 0
    assert snapshot.estimated_call_count == 1
    assert snapshot.cost == TokenCounter().calculate_cost(expected, "cx/gpt-5.4")


def test_all_zero_provider_usage_marks_estimated_when_estimator_returns_zero():
    class ZeroCounter:
        def count_with_provenance(self, _response):
            tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            return tokens, {name: True for name in tokens}

        def estimate_call_tokens(self, _messages, _completion):
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        def calculate_cost(self, _tokens, _model):
            return 0.0

    accumulator = UsageAccumulator(counter=ZeroCounter())

    accumulator.add_response(
        SimpleNamespace(choices=[]),
        model="cx/gpt-5.4",
        messages=[],
        completion_text="",
    )

    snapshot = accumulator.snapshot()
    assert snapshot.total_tokens == 0
    assert snapshot.cost == 0.0
    assert snapshot.provider_call_count == 1
    assert snapshot.estimated_call_count == 1


def test_accumulator_estimates_one_missing_usage_call_from_full_messages():
    class RecordingCounter:
        def __init__(self):
            self.estimated_texts = []

        def count_from_response(self, _response):
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        def estimate_tokens(self, text):
            self.estimated_texts.append(text)
            return len(text)

        def calculate_cost(self, tokens, _model):
            return tokens["prompt_tokens"] + tokens["completion_tokens"]

    counter = RecordingCounter()
    messages = [
        {"role": "system", "content": "system context"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "call-1"}]},
        {"role": "tool", "tool_call_id": "call-1", "content": "complete tool result"},
    ]
    accumulator = UsageAccumulator(counter=counter)

    accumulator.add_response(
        SimpleNamespace(choices=[]),
        model="cx/gpt-5.4",
        messages=messages,
        completion_text="generated completion",
    )

    snapshot = accumulator.snapshot()
    serialized_messages = counter.estimated_texts[0]
    assert json.loads(serialized_messages) == messages
    assert counter.estimated_texts[1] == "generated completion"
    assert snapshot.prompt_tokens == len(serialized_messages)
    assert snapshot.completion_tokens == len("generated completion")
    assert snapshot.provider_call_count == 1
    assert snapshot.estimated_call_count == 1


def test_settlement_is_owner_scoped_exact_and_idempotent():
    accumulator = UsageAccumulator()
    guardrail = _GuardrailRecorder()
    attribution = _AttributionRecorder()
    accumulator.add_response(
        _response(120, 10),
        model="cx/gpt-5.4",
        messages=[{"role": "user", "content": "tool round"}],
    )
    accumulator.add_response(
        _response(180, 25),
        model="cx/gpt-5.4-mini",
        messages=[{"role": "user", "content": "final round"}],
    )

    first = accumulator.settle(
        owner_key="user:alice",
        query="where should I go?",
        agent_name="chat",
        guardrail_budget=guardrail,
        cost_attribution=attribution,
    )
    second = accumulator.settle(
        owner_key="user:alice",
        query="where should I go?",
        agent_name="chat",
        guardrail_budget=guardrail,
        cost_attribution=attribution,
    )

    assert second is first
    assert first.settled is True
    assert guardrail.calls == [("user:alice", 335, 0.0)]
    assert len(attribution.calls) == 1
    record = attribution.calls[0]
    assert record["session_id"] == "user:alice"
    assert record["tokens"] == {
        "prompt_tokens": 300,
        "completion_tokens": 35,
        "total_tokens": 335,
        "provider_call_count": 2,
        "estimated_call_count": 0,
    }
    assert record["cost"] == 0.000801
    assert record["model"] == "multi-model"


def test_zero_provider_calls_settle_without_charging_cache_hits():
    accumulator = UsageAccumulator()
    guardrail = _GuardrailRecorder()
    attribution = _AttributionRecorder()

    snapshot = accumulator.settle(
        owner_key="user:alice",
        query="cached",
        agent_name="chat",
        guardrail_budget=guardrail,
        cost_attribution=attribution,
    )

    assert snapshot.total_tokens == 0
    assert snapshot.provider_call_count == 0
    assert guardrail.calls == []
    assert attribution.calls == []


def test_direct_agent_path_accumulates_every_provider_response(monkeypatch):
    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="search", arguments='{"q":"test"}'),
    )
    responses = iter([
        _response(120, 10, content=None),
        _response(180, 25, content="direct final answer"),
    ])
    first = next(responses)
    first.choices[0].message.tool_calls = [tool_call]
    responses = iter([first, next(responses)])
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: next(responses))
        )
    )
    accumulator = UsageAccumulator()
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "HAS_PARALLEL", False)
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    monkeypatch.setattr(server, "get_model", lambda: "cx/gpt-5.4")
    monkeypatch.setattr(server, "call_tool", lambda *_args: "[]")

    reply, _tools, _suggestions = server._run_agent(
        [{"role": "user", "content": "test"}],
        usage_accumulator=accumulator,
    )

    assert reply == "direct final answer"
    assert accumulator.snapshot().total_tokens == 335
    assert accumulator.snapshot().provider_call_count == 2


def test_direct_agent_counts_nested_followup_provider_response(monkeypatch):
    tool_call = SimpleNamespace(
        id="call-followups",
        function=SimpleNamespace(
            name="suggest_followups",
            arguments='{"context":"direct context"}',
        ),
    )
    decision = _response(6, 4, content=None)
    decision.choices[0].message.tool_calls = [tool_call]
    responses = iter([
        decision,
        _response(6, 4, content='["Cau hoi 1?", "Cau hoi 2?", "Cau hoi 3?"]'),
        _response(6, 4, content="direct final answer"),
    ])
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: next(responses))
        )
    )
    accumulator = UsageAccumulator()
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "HAS_PARALLEL", False)
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    monkeypatch.setattr(server, "get_model", lambda: "cx/gpt-5.4")
    monkeypatch.setattr(server, "get_model_mini", lambda: "cx/gpt-5.4-mini")

    reply, _tools, suggestions = server._run_agent(
        [{"role": "user", "content": "test"}],
        usage_accumulator=accumulator,
    )

    snapshot = accumulator.snapshot()
    assert reply == "direct final answer"
    assert suggestions == ["Cau hoi 1?", "Cau hoi 2?", "Cau hoi 3?"]
    assert snapshot.prompt_tokens == 18
    assert snapshot.completion_tokens == 12
    assert snapshot.total_tokens == 30
    assert snapshot.provider_call_count == 3
    assert snapshot.cost == pytest.approx(
        2 * TokenCounter().calculate_cost(
            {"prompt_tokens": 6, "completion_tokens": 4},
            "cx/gpt-5.4",
        )
        + TokenCounter().calculate_cost(
            {"prompt_tokens": 6, "completion_tokens": 4},
            "cx/gpt-5.4-mini",
        )
    )


def test_orchestrated_agent_counts_nested_followup_provider_response(monkeypatch):
    tool_call = SimpleNamespace(
        id="call-followups",
        function=SimpleNamespace(
            name="suggest_followups",
            arguments='{"context":"orchestrated context"}',
        ),
    )
    decision = _response(6, 4, content=None)
    decision.choices[0].message.tool_calls = [tool_call]
    outer_responses = iter([
        decision,
        _response(6, 4, content="orchestrated final answer"),
    ])
    nested_response = _response(
        6,
        4,
        content='["Goi y 1?", "Goi y 2?", "Goi y 3?"]',
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: nested_response)
        )
    )
    orch = server.Orchestrator(server.TOOLS)
    monkeypatch.setattr(
        orch,
        "route",
        lambda _message: (
            orchestrator.QueryCategory.GENERAL,
            orchestrator.GENERAL_AGENT,
        ),
    )
    accumulator = UsageAccumulator()
    monkeypatch.setattr(server, "HAS_PARALLEL", False)
    monkeypatch.setattr(server, "_get_orchestrator", lambda: orch)
    monkeypatch.setattr(
        server,
        "_llm_call_fn_mini",
        lambda _messages, _tools, _temperature: next(outer_responses),
    )
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    monkeypatch.setattr(server, "get_model_mini", lambda: "cx/gpt-5.4-mini")

    reply, _tools, suggestions = server._run_agent_orchestrated(
        "test",
        [],
        "session",
        "base prompt",
        usage_accumulator=accumulator,
    )

    snapshot = accumulator.snapshot()
    assert reply == "orchestrated final answer"
    assert suggestions == ["Goi y 1?", "Goi y 2?", "Goi y 3?"]
    assert snapshot.prompt_tokens == 18
    assert snapshot.completion_tokens == 12
    assert snapshot.total_tokens == 30
    assert snapshot.provider_call_count == 3


def _configure_post_chat(monkeypatch, guardrail, attribution):
    async def resolve_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner, raising=False)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", True)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", True)
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
    monkeypatch.setattr(server, "check_input", lambda *_args: {"allowed": True})
    monkeypatch.setattr(server, "check_output", lambda reply, *_args: {"cleaned_reply": reply})
    monkeypatch.setattr(server, "guardrail_budget", guardrail)
    monkeypatch.setattr(server, "cost_attribution", attribution)
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda *_args: ([{"role": "system", "content": "test"}], {}),
    )
    monkeypatch.setattr(server.memory_manager, "on_message", lambda *_args: None)
    monkeypatch.setattr(server.memory_manager, "on_chat_complete", lambda *_args: None)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args: None)
    monkeypatch.setattr(
        server.reflexion_engine,
        "evaluate_answer",
        lambda *_args: {"score": 6},
    )
    monkeypatch.setattr(server.quality_tracker, "record", lambda *_args: None)


def test_post_chat_settles_provider_totals_once_to_owner(monkeypatch):
    guardrail = _GuardrailRecorder()
    attribution = _AttributionRecorder()
    _configure_post_chat(monkeypatch, guardrail, attribution)

    def fake_orchestrated(_message, _history, _session_id, _prompt, usage_accumulator):
        usage_accumulator.add_response(
            _response(120, 10),
            model="cx/gpt-5.4",
            messages=[{"role": "user", "content": "tool round"}],
        )
        usage_accumulator.add_response(
            _response(180, 25),
            model="cx/gpt-5.4",
            messages=[{"role": "user", "content": "final round"}],
        )
        return "provider final answer with enough content to avoid fallback", [], []

    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", True)
    monkeypatch.setattr(server, "_run_agent_orchestrated", fake_orchestrated)
    with TestClient(server.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "where should I go?",
                "history": [{"role": "user", "content": "prior context"}],
            },
        )

    assert response.status_code == 200
    assert guardrail.calls == [("user:alice", 335, 0.0)]
    assert len(attribution.calls) == 1
    assert attribution.calls[0]["tokens"]["total_tokens"] == 335
    assert attribution.calls[0]["tokens"]["prompt_tokens"] == 300
    assert attribution.calls[0]["tokens"]["completion_tokens"] == 35
    assert attribution.calls[0]["cost"] == 0.002025


def test_post_cache_hit_adds_no_usage(monkeypatch):
    guardrail = _GuardrailRecorder()
    attribution = _AttributionRecorder()
    _configure_post_chat(monkeypatch, guardrail, attribution)
    monkeypatch.setattr(
        server.cache,
        "get",
        lambda *_args, **_kwargs: {
            "reply": "cached answer",
            "tool_calls": [],
            "suggestions": [],
        },
    )
    def forbidden(*_args, **_kwargs):
        raise AssertionError("provider must not be called on cache hit")

    monkeypatch.setattr(server, "_run_agent_orchestrated", forbidden)
    with TestClient(server.app) as client:
        response = client.post("/chat", json={"message": "cached", "history": []})

    assert response.status_code == 200
    assert response.json()["cached"] is True
    assert guardrail.calls == []
    assert attribution.calls == []


def test_post_semantic_publication_uses_captured_generation_lease(monkeypatch):
    import semantic_cache as semantic_cache_mod

    guardrail = _GuardrailRecorder()
    attribution = _AttributionRecorder()
    _configure_post_chat(monkeypatch, guardrail, attribution)
    matcher = semantic_cache_mod.SemanticMatcher()
    semantic_cache = semantic_cache_mod.MultiTierCache(
        matcher,
        l1_max=10,
        l2_max=20,
    )
    semantic_cache._l2_loaded = True
    semantic_cache._save_l2 = lambda: None
    deduplicator = semantic_cache_mod.RequestDeduplicator()
    published_dedup_keys = []

    def publish_semantic(query, response, owner_key="", dedup_key=None):
        published_dedup_keys.append(dedup_key)
        return semantic_cache_mod.semantic_put(
            query,
            response,
            owner_key=owner_key,
            dedup_key=dedup_key,
        )

    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", True)
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server.cache, "put", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server, "semantic_put", publish_semantic)
    monkeypatch.setattr(
        server,
        "_run_agent_orchestrated",
        lambda *_args, **_kwargs: (
            "provider answer long enough to publish into semantic cache",
            [],
            [],
        ),
    )
    monkeypatch.setattr(semantic_cache_mod, "multi_tier_cache", semantic_cache)
    monkeypatch.setattr(semantic_cache_mod, "deduplicator", deduplicator)

    response = asyncio.run(server.chat(
        server.ChatRequest.model_validate({
            "message": "post semantic lease",
            "history": [],
        }),
        Request({
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/chat",
            "raw_path": b"/chat",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
        }),
        Response(),
    ))

    assert response.reply.startswith("provider answer")
    assert len(deduplicator._pending) == 1
    assert published_dedup_keys == list(deduplicator._pending)
    assert semantic_cache.get(
        "post semantic lease",
        owner_key="user:alice",
    )["reply"].startswith("provider answer")


def test_post_cancellation_settles_completed_worker_usage_once(monkeypatch):
    guardrail = _GuardrailRecorder()
    attribution = _AttributionRecorder()
    _configure_post_chat(monkeypatch, guardrail, attribution)
    started = threading.Event()
    release = threading.Event()

    def fake_orchestrated(_message, _history, _session_id, _prompt, usage_accumulator):
        usage_accumulator.add_response(
            _response(120, 10),
            model="cx/gpt-5.4",
            messages=[{"role": "user", "content": "completed call"}],
        )
        started.set()
        release.wait(timeout=2)
        return "unused after cancellation", [], []

    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", True)
    monkeypatch.setattr(server, "_run_agent_orchestrated", fake_orchestrated)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/chat",
        "raw_path": b"/chat",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }

    async def cancel_after_provider_usage():
        task = asyncio.create_task(
            server.chat(
                server.ChatRequest.model_validate({
                    "message": "where should I go?",
                    "history": [{"role": "user", "content": "prior"}],
                }),
                Request(scope),
                Response(),
            )
        )
        assert await asyncio.to_thread(started.wait, 2)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_after_provider_usage())

    assert guardrail.calls == [("user:alice", 130, 0.0)]
    assert len(attribution.calls) == 1
    assert attribution.calls[0]["tokens"]["provider_call_count"] == 1
    assert attribution.calls[0]["tokens"]["total_tokens"] == 130


def test_post_double_cancellation_retrieves_worker_error(monkeypatch):
    guardrail = _GuardrailRecorder()
    attribution = _AttributionRecorder()
    _configure_post_chat(monkeypatch, guardrail, attribution)
    started = threading.Event()
    release = threading.Event()
    worker_finished = threading.Event()

    def failing_orchestrated(
        _message,
        _history,
        _session_id,
        _prompt,
        usage_accumulator,
    ):
        usage_accumulator.add_response(
            _response(7, 4),
            model="cx/gpt-5.4",
            messages=[{"role": "user", "content": "completed outer call"}],
        )
        started.set()
        release.wait(timeout=5)
        worker_finished.set()
        raise RuntimeError("worker failed after cancellation")

    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", True)
    monkeypatch.setattr(server, "_run_agent_orchestrated", failing_orchestrated)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/chat",
        "raw_path": b"/chat",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }

    async def cancel_worker_twice_and_capture_loop_errors():
        loop = asyncio.get_running_loop()
        contexts = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: contexts.append(context))
        try:
            task = asyncio.create_task(
                server.chat(
                    server.ChatRequest.model_validate({
                        "message": "where should I go?",
                        "history": [{"role": "user", "content": "prior"}],
                    }),
                    Request(scope),
                    Response(),
                )
            )
            assert await asyncio.to_thread(started.wait, 2)
            task.cancel()
            loop.call_soon(task.cancel)
            await asyncio.sleep(0)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert await asyncio.to_thread(worker_finished.wait, 2)
            await asyncio.sleep(0)
            gc.collect()
            await asyncio.sleep(0)
            return contexts
        finally:
            release.set()
            loop.set_exception_handler(previous_handler)

    contexts = asyncio.run(cancel_worker_twice_and_capture_loop_errors())

    assert contexts == []
    assert guardrail.calls == [("user:alice", 11, 0.0)]
    assert len(attribution.calls) == 1
    assert attribution.calls[0]["tokens"]["provider_call_count"] == 1
    assert attribution.calls[0]["tokens"]["total_tokens"] == 11
