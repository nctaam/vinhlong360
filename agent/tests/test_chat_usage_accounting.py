"""Provider-accurate chat usage accumulation and settlement tests."""

import json
import os
import sys
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

from fastapi.testclient import TestClient  # noqa: E402

from chat_usage import UsageAccumulator  # noqa: E402
import server  # noqa: E402


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


@pytest.mark.integration
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


@pytest.mark.integration
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
