"""Regression coverage for request history and hot-memory continuity."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402
from memory import MemoryManager  # noqa: E402
from prompt_cache import PromptCache  # noqa: E402


PRIOR_USER = "PRIOR USER SENTINEL"
PRIOR_ASSISTANT = "PRIOR ASSISTANT SENTINEL"
CURRENT = "CURRENT REQUEST SENTINEL"
PROVIDER_REPLY = "Provider assistant reply with enough detail for continuity testing."
CACHED_REPLY = "Cached assistant reply with enough detail for continuity testing."


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
    choice = SimpleNamespace(message=message, finish_reason="stop", index=0)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], usage=usage)


def _stream_chunks(content=PROVIDER_REPLY):
    yield SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=None))],
        usage=None,
    )
    yield SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _parse_sse(text):
    frames = []
    for line in text.splitlines():
        if line.startswith("data:"):
            frames.append(json.loads(line.removeprefix("data:").strip()))
    return frames


def _session_id(response, endpoint):
    if endpoint == "post":
        return response.json()["session_id"]
    done = next(frame for frame in _parse_sse(response.text) if frame["type"] == "done")
    return done["session_id"]


def _configure_provider_chat(monkeypatch, tmp_path, prompt_cache_enabled, *, fail=False):
    manager = _manager(tmp_path)
    provider_messages = []

    async def resolve_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    def create(*_args, stream=False, **kwargs):
        provider_messages.append([dict(message) for message in kwargs["messages"]])
        if fail:
            raise RuntimeError("provider unavailable")
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
    monkeypatch.setattr(server, "HAS_PROMPT_CACHE", prompt_cache_enabled)
    monkeypatch.setattr(server, "prompt_cache", PromptCache())
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    monkeypatch.setattr(server, "get_model", lambda: "test-model")
    monkeypatch.setattr(server, "get_model_mini", lambda: "test-model")
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server.cache, "put", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args: None)
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
    return manager, provider_messages


@pytest.mark.parametrize("endpoint", ["post", "stream"])
@pytest.mark.parametrize("prompt_cache_enabled", [False, True])
def test_provider_input_preserves_prior_history_and_deduplicates_current(
    endpoint,
    prompt_cache_enabled,
    tmp_path,
    monkeypatch,
):
    manager, provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled,
    )
    path = "/chat" if endpoint == "post" else "/chat/stream"

    with TestClient(server.app) as client:
        response = client.post(
            path,
            json={
                "message": CURRENT,
                "history": [
                    {"role": "user", "content": PRIOR_USER},
                    {"role": "assistant", "content": PRIOR_ASSISTANT},
                    {"role": "user", "content": CURRENT},
                ],
            },
        )

    assert response.status_code == 200
    first_provider_input = provider_messages[0]
    conversational = [item for item in first_provider_input if item["role"] != "system"]
    assert conversational == [
        {"role": "user", "content": PRIOR_USER},
        {"role": "assistant", "content": PRIOR_ASSISTANT},
        {"role": "user", "content": CURRENT},
    ]
    sid = _session_id(response, endpoint)
    hot = manager.require_session("user:alice", sid)
    assert [(item["role"], item["content"]) for item in hot.messages] == [
        ("user", PRIOR_USER),
        ("assistant", PRIOR_ASSISTANT),
        ("user", CURRENT),
        ("assistant", PROVIDER_REPLY),
    ]


@pytest.mark.parametrize("endpoint", ["post", "stream"])
@pytest.mark.parametrize("prompt_cache_enabled", [False, True])
def test_owned_hot_history_stays_separate_from_client_history(
    endpoint,
    prompt_cache_enabled,
    tmp_path,
    monkeypatch,
):
    manager, provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled,
    )
    session = manager.create_session("user:alice")
    session.add_message("user", "OWNED HOT USER")
    session.add_message("assistant", "OWNED HOT ASSISTANT")
    path = "/chat" if endpoint == "post" else "/chat/stream"

    with TestClient(server.app) as client:
        response = client.post(
            path,
            json={
                "message": CURRENT,
                "session_id": session.session_id,
                "history": [
                    {"role": "user", "content": "CLIENT HISTORY MUST NOT REPLACE HOT"},
                    {"role": "user", "content": CURRENT},
                ],
            },
        )

    assert response.status_code == 200
    conversational = [item for item in provider_messages[0] if item["role"] != "system"]
    assert conversational == [
        {"role": "user", "content": "OWNED HOT USER"},
        {"role": "assistant", "content": "OWNED HOT ASSISTANT"},
        {"role": "user", "content": CURRENT},
    ]
    assert [item["content"] for item in session.messages] == [
        "OWNED HOT USER",
        "OWNED HOT ASSISTANT",
        CURRENT,
        PROVIDER_REPLY,
    ]


@pytest.mark.parametrize("endpoint", ["post", "stream"])
def test_owned_hot_history_bypasses_context_free_cache(endpoint, tmp_path, monkeypatch):
    manager, provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled=False,
    )
    session = manager.create_session("user:alice")
    session.add_message("user", "HOT CACHE BYPASS USER")
    session.add_message("assistant", "HOT CACHE BYPASS ASSISTANT")
    cache_read = Mock(return_value={
        "reply": CACHED_REPLY,
        "tool_calls": [],
        "suggestions": [],
    })
    monkeypatch.setattr(server.cache, "get", cache_read)
    path = "/chat" if endpoint == "post" else "/chat/stream"

    with TestClient(server.app) as client:
        response = client.post(
            path,
            json={"message": CURRENT, "history": [], "session_id": session.session_id},
        )

    assert response.status_code == 200
    cache_read.assert_not_called()
    conversational = [item for item in provider_messages[0] if item["role"] != "system"]
    assert conversational == [
        {"role": "user", "content": "HOT CACHE BYPASS USER"},
        {"role": "assistant", "content": "HOT CACHE BYPASS ASSISTANT"},
        {"role": "user", "content": CURRENT},
    ]


@pytest.mark.parametrize("prompt_cache_enabled", [False, True])
def test_compressed_hot_summary_reaches_provider_system_context(
    prompt_cache_enabled,
    tmp_path,
    monkeypatch,
):
    manager, provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled,
    )
    session = manager.create_session("user:alice")
    session.summary = "COMPRESSED HOT SUMMARY SENTINEL"
    for index in range(20):
        session.add_message(
            "user" if index % 2 == 0 else "assistant",
            f"recent-{index}",
        )

    with TestClient(server.app) as client:
        response = client.post(
            "/chat",
            json={"message": CURRENT, "history": [], "session_id": session.session_id},
        )

    assert response.status_code == 200
    assert "COMPRESSED HOT SUMMARY SENTINEL" in provider_messages[0][0]["content"]
    conversational = [item for item in provider_messages[0] if item["role"] != "system"]
    assert [item["content"] for item in conversational] == [
        *(f"recent-{index}" for index in range(20)),
        CURRENT,
    ]


@pytest.mark.parametrize("prompt_cache_enabled", [False, True])
def test_post_orchestrator_receives_resolved_owned_history(
    prompt_cache_enabled,
    tmp_path,
    monkeypatch,
):
    manager, _provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled,
    )
    session = manager.create_session("user:alice")
    session.add_message("user", "OWNED ORCHESTRATOR USER")
    session.add_message("assistant", "OWNED ORCHESTRATOR ASSISTANT")
    captured_history = []

    def orchestrate(_message, history, _session_id, _prompt, _usage):
        captured_history.extend(history)
        return PROVIDER_REPLY, [], []

    monkeypatch.setattr(server, "HAS_ORCHESTRATOR", True)
    monkeypatch.setattr(server, "_run_agent_orchestrated", orchestrate)

    with TestClient(server.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": CURRENT,
                "session_id": session.session_id,
                "history": [
                    {"role": "user", "content": "CLIENT ORCHESTRATOR HISTORY"},
                    {"role": "user", "content": CURRENT},
                ],
            },
        )

    assert response.status_code == 200
    assert captured_history == [
        {"role": "user", "content": "OWNED ORCHESTRATOR USER"},
        {"role": "assistant", "content": "OWNED ORCHESTRATOR ASSISTANT"},
    ]


@pytest.mark.parametrize("prompt_cache_enabled", [False, True])
def test_new_session_hydration_survives_later_selector_continuation(
    prompt_cache_enabled,
    tmp_path,
    monkeypatch,
):
    _manager_instance, provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled,
    )
    with TestClient(server.app) as client:
        first = client.post(
            "/chat",
            json={
                "message": "FIRST CURRENT",
                "history": [
                    {"role": "user", "content": PRIOR_USER},
                    {"role": "assistant", "content": PRIOR_ASSISTANT},
                ],
            },
        )
        second = client.post(
            "/chat",
            json={
                "message": "SECOND CURRENT",
                "history": [],
                "session_id": first.json()["session_id"],
            },
        )

    assert second.status_code == 200
    conversational = [item for item in provider_messages[1] if item["role"] != "system"]
    assert conversational == [
        {"role": "user", "content": PRIOR_USER},
        {"role": "assistant", "content": PRIOR_ASSISTANT},
        {"role": "user", "content": "FIRST CURRENT"},
        {"role": "assistant", "content": PROVIDER_REPLY},
        {"role": "user", "content": "SECOND CURRENT"},
    ]


@pytest.mark.parametrize("endpoint", ["post", "stream"])
@pytest.mark.parametrize("cache_kind", ["exact", "semantic"])
def test_cache_hit_records_user_and_assistant_once_without_provider_usage(
    endpoint,
    cache_kind,
    tmp_path,
    monkeypatch,
):
    manager, _provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled=False,
    )
    session = manager.create_session("user:alice")
    sentinel = {"reply": CACHED_REPLY, "tool_calls": [], "suggestions": []}
    provider = Mock(side_effect=AssertionError("cache hit must not call provider"))
    monkeypatch.setattr(server, "get_client", provider)
    if cache_kind == "semantic":
        async def semantic_hit(_query, owner_key=""):
            assert owner_key == "user:alice"
            return sentinel

        monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
        monkeypatch.setattr(server, "semantic_get_async", semantic_hit)
        monkeypatch.setattr(server, "semantic_take_dedup_lease", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(server.cache, "get", Mock(side_effect=AssertionError("semantic hit stops exact lookup")))
    else:
        monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: sentinel)
    path = "/chat" if endpoint == "post" else "/chat/stream"

    with TestClient(server.app) as client:
        response = client.post(
            path,
            json={"message": CURRENT, "history": [], "session_id": session.session_id},
        )

    assert response.status_code == 200
    assert [(item["role"], item["content"]) for item in session.messages] == [
        ("user", CURRENT),
        ("assistant", CACHED_REPLY),
    ]
    provider.assert_not_called()


@pytest.mark.parametrize("endpoint", ["post", "stream"])
def test_provider_error_records_current_user_at_most_once(endpoint, tmp_path, monkeypatch):
    manager, _provider_messages = _configure_provider_chat(
        monkeypatch,
        tmp_path,
        prompt_cache_enabled=False,
        fail=True,
    )
    path = "/chat" if endpoint == "post" else "/chat/stream"

    with TestClient(server.app) as client:
        response = client.post(
            path,
            json={
                "message": CURRENT,
                "history": [{"role": "user", "content": CURRENT}],
            },
        )

    assert response.status_code == 200
    sid = _session_id(response, endpoint)
    session = manager.require_session("user:alice", sid)
    assert [item["content"] for item in session.messages].count(CURRENT) == 1
