"""Security boundary tests for server-derived chat ownership."""

import asyncio
import importlib
import importlib.util
import os
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import Response
from starlette.requests import Request
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

import server  # noqa: E402
import semantic_cache as semantic_cache_mod  # noqa: E402
from memory import MemoryManager  # noqa: E402


def _chat_identity_module():
    spec = importlib.util.find_spec("chat_identity")
    assert spec is not None, "agent/chat_identity.py must define the server-derived owner boundary"
    return importlib.import_module("chat_identity")


def _manager(tmp_path):
    with patch("memory.MEMORY_DIR", tmp_path):
        return MemoryManager()


def _capacity_manager(tmp_path):
    manager = _manager(tmp_path)
    manager._MAX_SESSIONS = 1
    existing = manager.create_session("user:existing")
    return manager, ("user:existing", existing.session_id)


async def _new_anonymous_owner(_request):
    return SimpleNamespace(owner_key="anon:new-owner", cookie_value="visitor.signature")


class _SignalingDeduplicator(semantic_cache_mod.RequestDeduplicator):
    def __init__(self, waiter_started):
        super().__init__()
        self._waiter_started = waiter_started

    def wait_for(self, dedup_key, timeout=30):
        self._waiter_started.set()
        return super().wait_for(dedup_key, timeout=5)

    async def wait_for_async(self, dedup_key, timeout=30):
        self._waiter_started.set()
        return await super().wait_for_async(dedup_key, timeout=timeout)


def _release_semantic_deadlock(
    async_release_completed,
    query,
    watchdog_sentinel,
    owner_key,
):
    if not async_release_completed.wait(timeout=2):
        semantic_cache_mod.semantic_put(
            query,
            watchdog_sentinel,
            owner_key=owner_key,
        )


async def _record_semantic_heartbeat(waiter_started, heartbeat_progressed):
    assert await asyncio.to_thread(waiter_started.wait, 1)
    heartbeat_progressed.set()


async def _record_unrelated_async_work(waiter_started, unrelated_progressed):
    assert await asyncio.to_thread(waiter_started.wait, 1)
    await asyncio.sleep(0)
    unrelated_progressed.set()


async def _exercise_semantic_waiter_handler(
    endpoint,
    query,
    owner_key,
    sentinel,
    waiter_started,
    heartbeat_progressed,
    unrelated_progressed,
    async_release_completed,
):
    path = "/chat" if endpoint == "post" else "/chat/stream"
    request = Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    })
    chat_request = server.ChatRequest.model_validate({
        "message": query,
        "history": [],
    })
    if endpoint == "post":
        handler = server.chat(chat_request, request, Response())
    else:
        handler = server.chat_stream(chat_request, request)

    handler_task = asyncio.create_task(handler)
    await asyncio.gather(
        _record_semantic_heartbeat(waiter_started, heartbeat_progressed),
        _record_unrelated_async_work(waiter_started, unrelated_progressed),
    )
    semantic_cache_mod.semantic_put(query, sentinel, owner_key=owner_key)
    async_release_completed.set()
    return await handler_task


async def _consume_stream_body(response):
    return "".join([chunk async for chunk in response.body_iterator])


class _SemanticErrorStreamCompletions:
    def create(self, *_args, stream=False, **_kwargs):
        if not stream:
            message = SimpleNamespace(
                content="decision",
                tool_calls=None,
                role="assistant",
                function_call=None,
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        def chunks():
            yield SimpleNamespace(
                choices=[SimpleNamespace(
                    delta=SimpleNamespace(
                        content=(
                            "Provider stream survives semantic lookup failure "
                            "with a complete answer."
                        ),
                        tool_calls=None,
                    ),
                    finish_reason=None,
                )]
            )

        return chunks()


def _assert_semantic_waiter_response(endpoint, response, sentinel):
    if endpoint == "post":
        assert response.reply == sentinel["reply"]
        assert response.cached is True
    else:
        body = asyncio.run(_consume_stream_body(response))
        assert sentinel["reply"] in body
        assert "semantic_cache_hit" in body


def _assert_semantic_probe_completed(
    watchdog,
    async_release_completed,
    heartbeat_progressed,
    unrelated_progressed,
):
    assert not watchdog.is_alive()
    assert async_release_completed.is_set()
    assert heartbeat_progressed.is_set()
    assert unrelated_progressed.is_set()


def _assert_exact_cache_response(endpoint, first, second, sentinel):
    if endpoint == "post":
        assert first.json()["reply"] == sentinel["reply"]
        assert second.json()["reply"] == sentinel["reply"]
    else:
        assert "cache_hit" in first.text
        assert "cache_hit" in second.text


def _assert_exact_cache_publication_success(
    deduplicator,
    semantic_cache,
    abandoned,
    query,
    owner_key,
    sentinel,
):
    assert len(deduplicator._pending) == 1
    active_key, slot = next(iter(deduplicator._pending.items()))
    assert abandoned == [(query, owner_key, active_key)]
    assert slot["result"] == sentinel
    assert semantic_cache.get(query, owner_key=owner_key) == sentinel


def _assert_exact_cache_publication_failure(
    deduplicator,
    semantic_cache,
    abandoned,
    query,
    owner_key,
    _sentinel,
):
    assert [(message, owner) for message, owner, _key in abandoned] == [
        (query, owner_key),
        (query, owner_key),
    ]
    abandoned_keys = [key for _message, _owner, key in abandoned]
    assert all(abandoned_keys)
    assert len(set(abandoned_keys)) == 2
    assert deduplicator._pending == {}
    assert semantic_cache.get(query, owner_key=owner_key) is None


def test_anonymous_owner_cookie_round_trip_and_tamper_rotation(monkeypatch):
    identity = _chat_identity_module()
    monkeypatch.setattr(identity, "_CHAT_OWNER_SECRET", b"owner-test-secret")

    first = identity.resolve_anonymous_owner(None)
    response = Response()
    identity.set_chat_owner_cookie(response, first)
    visitor_id = first.cookie_value.split(".", 1)[0]

    assert first.owner_key.startswith("anon:")
    assert len(first.owner_key.removeprefix("anon:")) == 64
    assert visitor_id not in first.owner_key
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]

    same = identity.resolve_anonymous_owner(first.cookie_value)
    assert same.owner_key == first.owner_key
    assert same.cookie_value is None

    replacement = identity.resolve_anonymous_owner(first.cookie_value[:-1] + "x")
    assert replacement.owner_key != first.owner_key
    assert replacement.cookie_value


def test_anonymous_owner_cookie_is_secure_in_production(monkeypatch):
    identity = _chat_identity_module()
    monkeypatch.setattr(identity, "_CHAT_OWNER_SECRET", b"owner-test-secret")
    monkeypatch.setattr(identity, "_IS_PRODUCTION", True)
    context = identity.resolve_anonymous_owner(None)
    response = Response()

    identity.set_chat_owner_cookie(response, context)

    assert "Secure" in response.headers["set-cookie"]


def test_production_requires_chat_owner_or_csrf_secret():
    agent_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env.pop("CHAT_OWNER_SECRET", None)
    env.pop("CSRF_SECRET", None)

    result = subprocess.run(
        [sys.executable, "-c", "import chat_identity"],
        cwd=agent_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "CHAT_OWNER_SECRET" in result.stderr


def test_authenticated_owner_uses_validated_user_id(monkeypatch):
    identity = _chat_identity_module()

    async def current_user(_request):
        return {"id": 42}

    monkeypatch.setattr(identity, "_get_current_user_or_none", current_user)
    request = SimpleNamespace(cookies={})

    context = __import__("asyncio").run(identity.resolve_chat_owner(request))

    assert context.owner_key == "user:42"
    assert context.cookie_value is None


def test_post_chat_accepts_alice_conversation_and_rejects_bob(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    conversation = manager.create_session("user:alice")
    monkeypatch.setattr(server, "memory_manager", manager)

    async def resolve_owner(request):
        user = request.headers.get("x-test-user")
        return SimpleNamespace(owner_key=f"user:{user}", cookie_value=None)

    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner, raising=False)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", True)
    monkeypatch.setattr(server, "check_input", lambda *_args: {"allowed": False})
    client = TestClient(server.app)

    alice = client.post(
        "/chat",
        headers={"X-Test-User": "alice"},
        json={"message": "continue", "session_id": conversation.session_id},
    )
    bob = client.post(
        "/chat",
        headers={"X-Test-User": "bob"},
        json={"message": "steal", "session_id": conversation.session_id},
    )

    assert alice.status_code == 200
    assert bob.status_code == 404
    assert ("user:bob", conversation.session_id) not in manager._sessions


def test_post_mismatch_fails_before_state_cache_prompt_or_provider_access(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    conversation = manager.create_session("user:alice")
    monkeypatch.setattr(server, "memory_manager", manager)
    server.cache.put(
        "alice cached query",
        {"reply": "alice sentinel"},
        owner_key="user:alice",
    )
    alice_cache_key = server.cache._normalize_key(
        "alice cached query",
        owner_key="user:alice",
    )

    async def bob_owner(_request):
        return SimpleNamespace(owner_key="user:bob", cookie_value=None)

    monkeypatch.setattr(server, "resolve_chat_owner", bob_owner, raising=False)
    forbidden = Mock(side_effect=AssertionError("must not be accessed for an ownership miss"))
    limiter = Mock(return_value=(True, {}))
    monkeypatch.setattr(manager, "on_message", forbidden)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", limiter)
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server, "semantic_get_async", forbidden)
    monkeypatch.setattr(server, "_build_messages", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    client = TestClient(server.app)

    try:
        response = client.post(
            "/chat",
            json={"message": "alice cached query", "session_id": conversation.session_id},
        )
    finally:
        server.cache._cache.pop(alice_cache_key, None)

    assert response.status_code == 404
    limiter.assert_called_once()
    forbidden.assert_not_called()
    assert ("user:bob", conversation.session_id) not in manager._sessions


def test_owned_post_cache_reads_receive_owner_key(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    conversation = manager.create_session("user:alice")
    calls = []
    sentinel = {
        "reply": "alice exact cache sentinel",
        "tool_calls": [],
        "suggestions": [],
    }

    async def alice_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    async def semantic_read(message, owner_key=""):
        calls.append(("semantic", message, owner_key))
        return None

    def exact_read(message, owner_key=""):
        calls.append(("exact", message, owner_key))
        return sentinel

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "semantic_get_async", semantic_read)
    monkeypatch.setattr(server.cache, "get", exact_read)
    client = TestClient(server.app)

    response = client.post(
        "/chat",
        json={"message": "cached query", "session_id": conversation.session_id},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == sentinel["reply"]
    assert calls == [
        ("semantic", "cached query", "user:alice"),
        ("exact", "cached query", "user:alice"),
    ]


def test_rate_limited_post_does_not_create_or_evict_session(tmp_path, monkeypatch):
    manager, existing_key = _capacity_manager(tmp_path)
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", _new_anonymous_owner)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", lambda _ip: (False, {"retry_after": 30}))
    client = TestClient(server.app)

    response = client.post("/chat", json={"message": "new conversation"})

    assert response.status_code == 429
    assert existing_key in manager._sessions
    assert len(manager._sessions) == 1
    assert "vl360_chat_owner=" in response.headers["set-cookie"]


def test_guardrail_blocked_post_uses_owner_without_creating_session(tmp_path, monkeypatch):
    manager, existing_key = _capacity_manager(tmp_path)
    checked = []
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", _new_anonymous_owner)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", True)
    monkeypatch.setattr(
        server,
        "check_input",
        lambda message, identity: checked.append((message, identity)) or {"allowed": False},
    )
    client = TestClient(server.app)

    response = client.post("/chat", json={"message": "blocked"})

    assert response.status_code == 200
    assert response.json()["session_id"] == ""
    assert checked == [("blocked", "anon:new-owner")]
    assert existing_key in manager._sessions
    assert len(manager._sessions) == 1
    assert "vl360_chat_owner=" in response.headers["set-cookie"]


def test_empty_stream_does_not_create_or_evict_session(tmp_path, monkeypatch):
    manager, existing_key = _capacity_manager(tmp_path)
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", _new_anonymous_owner)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    client = TestClient(server.app)

    response = client.post("/chat/stream", json={"message": "   ", "history": []})

    assert response.status_code == 200
    assert existing_key in manager._sessions
    assert len(manager._sessions) == 1
    assert "vl360_chat_owner=" in response.headers["set-cookie"]


def test_guardrail_blocked_stream_uses_owner_without_creating_session(tmp_path, monkeypatch):
    manager, existing_key = _capacity_manager(tmp_path)
    checked = []
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", _new_anonymous_owner)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", True)
    monkeypatch.setattr(
        server,
        "check_input",
        lambda message, identity: checked.append((message, identity)) or {"allowed": False},
    )
    client = TestClient(server.app)

    response = client.post("/chat/stream", json={"message": "blocked", "history": []})

    assert response.status_code == 200
    assert checked == [("blocked", "anon:new-owner")]
    assert existing_key in manager._sessions
    assert len(manager._sessions) == 1
    assert "vl360_chat_owner=" in response.headers["set-cookie"]


def test_stream_mismatch_fails_before_access_and_sets_anonymous_cookie(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    conversation = manager.create_session("user:alice")
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", _new_anonymous_owner)
    forbidden = Mock(side_effect=AssertionError("must not be accessed for an ownership miss"))
    limiter = Mock(return_value=(True, {}))
    monkeypatch.setattr(manager, "on_message", forbidden)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", limiter)
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server, "semantic_get_async", forbidden)
    monkeypatch.setattr(server, "_build_messages", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={"message": "steal", "history": [], "session_id": conversation.session_id},
    )

    assert response.status_code == 404
    assert "vl360_chat_owner=" in response.headers["set-cookie"]
    limiter.assert_called_once()
    forbidden.assert_not_called()


@pytest.mark.parametrize(
    ("path", "limiter_name"),
    [("/chat", "chat_limiter"), ("/chat/stream", "stream_limiter")],
)
def test_rate_limited_invalid_selector_returns_429_before_lookup_or_mutation(
    path,
    limiter_name,
    tmp_path,
    monkeypatch,
):
    manager = _manager(tmp_path)
    forbidden = Mock(side_effect=AssertionError("blocked request must not touch target state"))
    limiter = Mock(return_value=(False, {"retry_after": 30}))
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", _new_anonymous_owner)
    monkeypatch.setattr(getattr(server, limiter_name), "is_allowed", limiter)
    monkeypatch.setattr(manager, "require_session", forbidden)
    monkeypatch.setattr(manager, "create_session", forbidden)
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server, "semantic_get_async", forbidden)
    monkeypatch.setattr(server, "_build_messages", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    client = TestClient(server.app)

    response = client.post(
        path,
        json={"message": "blocked", "history": [], "session_id": "missing-selector"},
    )

    assert response.status_code == 429
    limiter.assert_called_once()
    forbidden.assert_not_called()


def test_owned_stream_cache_reads_receive_owner_key(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    conversation = manager.create_session("user:alice")
    calls = []
    sentinel = {
        "reply": "alice exact stream cache sentinel",
        "tool_calls": [],
        "suggestions": [],
    }

    async def alice_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    async def semantic_read(message, owner_key=""):
        calls.append(("semantic", message, owner_key))
        return None

    def exact_read(message, owner_key=""):
        calls.append(("exact", message, owner_key))
        return sentinel

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "semantic_get_async", semantic_read)
    monkeypatch.setattr(server.cache, "get", exact_read)
    client = TestClient(server.app)

    response = client.post(
        "/chat/stream",
        json={"message": "cached query", "history": [], "session_id": conversation.session_id},
    )

    assert response.status_code == 200
    assert "alice exact stream" in response.text
    assert "cache sentinel" in response.text
    assert calls == [
        ("semantic", "cached query", "user:alice"),
        ("exact", "cached query", "user:alice"),
    ]


@pytest.mark.parametrize("endpoint", ["post", "stream"])
@pytest.mark.parametrize("publication_fails", [False, True])
def test_exact_cache_hit_finalizes_captured_semantic_generation(
    endpoint,
    publication_fails,
    tmp_path,
    monkeypatch,
):
    manager = _manager(tmp_path)
    owner_key = "user:alice"
    query = f"{endpoint} exact cache resolves semantic generation"
    sentinel = {
        "reply": "Exact cache response resolves every semantic duplicate immediately.",
        "tool_calls": [],
        "suggestions": [],
    }
    exact_reads = []
    abandoned = []

    class NoWaitDeduplicator(semantic_cache_mod.RequestDeduplicator):
        def __init__(self):
            super().__init__()
            self.wait_calls = 0

        async def wait_for_async(self, dedup_key, timeout=30):
            self.wait_calls += 1
            return await super().wait_for_async(dedup_key, timeout=0)

    matcher = semantic_cache_mod.SemanticMatcher()
    semantic_cache = semantic_cache_mod.MultiTierCache(
        matcher,
        l1_max=10,
        l2_max=20,
    )
    semantic_cache._l2_loaded = True
    semantic_cache._save_l2 = lambda: None
    deduplicator = NoWaitDeduplicator()

    async def alice_owner(_request):
        return SimpleNamespace(owner_key=owner_key, cookie_value=None)

    def exact_read(message, owner_key=""):
        exact_reads.append((message, owner_key))
        return sentinel

    def forbidden(*_args, **_kwargs):
        raise AssertionError("provider must not run for an exact cache hit")

    def fail_publication(*_args, **_kwargs):
        raise RuntimeError("semantic exact-hit publication failed")

    def record_abandon(message, owner_key="", dedup_key=None):
        abandoned.append((message, owner_key, dedup_key))
        return semantic_cache_mod.semantic_abandon(
            message,
            owner_key=owner_key,
            dedup_key=dedup_key,
        )

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "semantic_get_async", semantic_cache_mod.semantic_get_async)
    monkeypatch.setattr(
        server,
        "semantic_take_dedup_lease",
        semantic_cache_mod.semantic_take_dedup_lease,
    )
    monkeypatch.setattr(
        server,
        "semantic_put",
        {
            False: semantic_cache_mod.semantic_put,
            True: fail_publication,
        }[publication_fails],
    )
    monkeypatch.setattr(server, "semantic_abandon", record_abandon)
    monkeypatch.setattr(server.cache, "get", exact_read)
    monkeypatch.setattr(server, "_build_messages", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    monkeypatch.setattr(semantic_cache_mod, "multi_tier_cache", semantic_cache)
    monkeypatch.setattr(semantic_cache_mod, "deduplicator", deduplicator)
    client = TestClient(server.app)
    path = "/chat" if endpoint == "post" else "/chat/stream"

    first = client.post(path, json={"message": query, "history": []})
    second = client.post(path, json={"message": query, "history": []})

    assert first.status_code == 200
    assert second.status_code == 200
    _assert_exact_cache_response(endpoint, first, second, sentinel)
    expected_exact_reads = {False: 1, True: 2}[publication_fails]
    assert exact_reads == [(query, owner_key)] * expected_exact_reads
    assert deduplicator.wait_calls == 0
    assertion = {
        False: _assert_exact_cache_publication_success,
        True: _assert_exact_cache_publication_failure,
    }[publication_fails]
    assertion(
        deduplicator,
        semantic_cache,
        abandoned,
        query,
        owner_key,
        sentinel,
    )


@pytest.mark.parametrize("terminal_mode", ["disconnect", "decision_error", "noncacheable"])
def test_stream_terminal_path_abandons_captured_semantic_lease(
    terminal_mode,
    tmp_path,
    monkeypatch,
):
    manager = _manager(tmp_path)
    owner_key = "user:alice"
    query = f"stream {terminal_mode} semantic holder"
    dedup_key = f"stream-{terminal_mode}-generation"
    abandoned = []

    class StreamCompletions:
        def create(self, *_args, stream=False, **_kwargs):
            if not stream:
                message = SimpleNamespace(
                    content="decision",
                    tool_calls=None,
                    role="assistant",
                    function_call=None,
                )
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

            def chunks():
                yield SimpleNamespace(
                    choices=[SimpleNamespace(
                        delta=SimpleNamespace(
                            content="A streamed response that must not remain an active lease.",
                            tool_calls=None,
                        ),
                        finish_reason=None,
                    )]
                )

            return chunks()

    async def alice_owner(_request):
        return SimpleNamespace(owner_key=owner_key, cookie_value=None)

    async def semantic_miss(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(manager, "on_chat_complete", lambda *_args: None)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", False)
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "HAS_DYNAMIC_AGENTS", False)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", False)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", False)
    monkeypatch.setattr(server, "HAS_MEMORY_GRAPH", False)
    monkeypatch.setattr(server, "HAS_EXPERIENCE", False)
    monkeypatch.setattr(server, "HAS_FEWSHOT", False)
    monkeypatch.setattr(server, "HAS_LLM_JUDGE", False)
    monkeypatch.setattr(server, "HAS_AB_TESTING", False)
    monkeypatch.setattr(server, "HAS_METRICS", False)
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda *_args: ([{"role": "system", "content": "test"}], {}),
    )
    monkeypatch.setattr(
        server,
        "get_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=StreamCompletions())
        ),
    )
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server.cache,
        "put",
        lambda *_args, **_kwargs: pytest.fail("terminal stream must not cache"),
    )
    monkeypatch.setattr(
        server.reflexion_engine,
        "evaluate_answer",
        lambda *_args: {"score": 4, "issues": [], "good_points": []},
    )
    monkeypatch.setattr(server.quality_tracker, "record", lambda *_args: None)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args: None)
    monkeypatch.setattr(server, "semantic_get_async", semantic_miss)
    monkeypatch.setattr(
        server,
        "semantic_take_dedup_lease",
        lambda *_args, **_kwargs: dedup_key,
    )
    monkeypatch.setattr(
        server,
        "semantic_put",
        lambda *_args, **_kwargs: pytest.fail("terminal stream must not publish"),
    )
    monkeypatch.setattr(
        server,
        "semantic_abandon",
        lambda message, owner_key="", dedup_key=None: abandoned.append(
            (message, owner_key, dedup_key)
        ) or True,
        raising=False,
    )
    if terminal_mode == "decision_error":
        monkeypatch.setattr(
            server,
            "_call_stream_decision",
            lambda *_args: {"success": False, "message": "decision failed"},
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
            server.ChatRequest.model_validate({"message": query, "history": []}),
            Request(scope),
        )

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            if terminal_mode == "disconnect" and message["type"] == "http.response.body":
                raise RuntimeError("client disconnected after response start")

        if terminal_mode == "disconnect":
            with pytest.raises(RuntimeError, match="client disconnected"):
                await response(scope, receive, send)
        else:
            await response(scope, receive, send)

    asyncio.run(exercise())

    assert abandoned == [(query, owner_key, dedup_key)]


def test_stream_setup_exception_abandons_captured_semantic_lease(
    tmp_path,
    monkeypatch,
):
    manager = _manager(tmp_path)
    owner_key = "user:alice"
    query = "stream setup exception semantic holder"
    dedup_key = "stream-setup-exception-generation"
    abandoned = []

    async def alice_owner(_request):
        return SimpleNamespace(owner_key=owner_key, cookie_value=None)

    async def semantic_miss(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", False)
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server, "semantic_get_async", semantic_miss)
    monkeypatch.setattr(
        server,
        "semantic_take_dedup_lease",
        lambda *_args, **_kwargs: dedup_key,
    )
    monkeypatch.setattr(
        server,
        "semantic_abandon",
        lambda message, owner_key="", dedup_key=None: abandoned.append(
            (message, owner_key, dedup_key)
        ) or True,
        raising=False,
    )
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("stream setup failed")),
    )

    with pytest.raises(RuntimeError, match="stream setup failed"):
        asyncio.run(server.chat_stream(
            server.ChatRequest.model_validate({"message": query, "history": []}),
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
        ))

    assert abandoned == [(query, owner_key, dedup_key)]


def test_stream_response_start_failure_abandons_before_generator_iteration(
    tmp_path,
    monkeypatch,
):
    manager = _manager(tmp_path)
    owner_key = "user:alice"
    query = "stream response start failure semantic holder"
    dedup_key = "stream-response-start-generation"
    abandoned = []
    provider_called = []

    async def alice_owner(_request):
        return SimpleNamespace(owner_key=owner_key, cookie_value=None)

    async def semantic_miss(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", False)
    monkeypatch.setattr(server, "HAS_DYNAMIC_AGENTS", False)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", False)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", False)
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(server, "semantic_get_async", semantic_miss)
    monkeypatch.setattr(
        server,
        "semantic_take_dedup_lease",
        lambda *_args, **_kwargs: dedup_key,
    )
    monkeypatch.setattr(
        server,
        "semantic_abandon",
        lambda message, owner_key="", dedup_key=None: abandoned.append(
            (message, owner_key, dedup_key)
        ) or True,
        raising=False,
    )
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda *_args: ([{"role": "system", "content": "test"}], {}),
    )
    monkeypatch.setattr(
        server,
        "get_client",
        lambda: provider_called.append(True),
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
            server.ChatRequest.model_validate({"message": query, "history": []}),
            Request(scope),
        )

        async def receive():
            return {"type": "http.disconnect"}

        async def fail_start(message):
            assert message["type"] == "http.response.start"
            raise RuntimeError("response start failed")

        with pytest.raises(RuntimeError, match="response start failed"):
            await response(scope, receive, fail_start)

    asyncio.run(exercise())

    assert provider_called == []
    assert abandoned == [(query, owner_key, dedup_key)]


@pytest.mark.parametrize("endpoint", ["post", "stream"])
def test_semantic_dedup_wait_keeps_async_handlers_responsive(
    endpoint,
    tmp_path,
    monkeypatch,
):
    manager = _manager(tmp_path)
    owner_key = "user:alice"
    query = "same owner duplicate semantic query"
    sentinel = {
        "reply": "semantic singleflight result",
        "tool_calls": [],
        "suggestions": [],
    }
    watchdog_sentinel = {
        "reply": "watchdog deadlock release",
        "tool_calls": [],
        "suggestions": [],
    }
    waiter_started = threading.Event()
    heartbeat_progressed = threading.Event()
    unrelated_progressed = threading.Event()
    async_release_completed = threading.Event()

    matcher = semantic_cache_mod.SemanticMatcher()
    semantic_cache = semantic_cache_mod.MultiTierCache(
        matcher,
        l1_max=10,
        l2_max=20,
    )
    semantic_cache._l2_loaded = True
    semantic_cache._save_l2 = lambda: None
    deduplicator = _SignalingDeduplicator(waiter_started)
    is_holder, _dedup_key = deduplicator.acquire(query, owner_key=owner_key)
    assert is_holder

    async def alice_owner(_request):
        return SimpleNamespace(owner_key=owner_key, cookie_value=None)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("semantic dedup waiter must not start provider work")

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(manager, "on_message", lambda *_args: None)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "HAS_METRICS", False)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server, "UsageAccumulator", forbidden)
    monkeypatch.setattr(server, "_build_messages", forbidden)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args: None)
    monkeypatch.setattr(semantic_cache_mod, "multi_tier_cache", semantic_cache)
    monkeypatch.setattr(semantic_cache_mod, "deduplicator", deduplicator)

    watchdog = threading.Thread(
        target=_release_semantic_deadlock,
        args=(
            async_release_completed,
            query,
            watchdog_sentinel,
            owner_key,
        ),
    )
    watchdog.start()
    response = asyncio.run(_exercise_semantic_waiter_handler(
        endpoint,
        query,
        owner_key,
        sentinel,
        waiter_started,
        heartbeat_progressed,
        unrelated_progressed,
        async_release_completed,
    ))
    watchdog.join(timeout=3)
    _assert_semantic_probe_completed(
        watchdog,
        async_release_completed,
        heartbeat_progressed,
        unrelated_progressed,
    )
    _assert_semantic_waiter_response(endpoint, response, sentinel)


def test_stream_semantic_lookup_error_rejects_missing_lease(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    exact_puts = []
    semantic_puts = []

    async def alice_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    async def semantic_error(*_args, **_kwargs):
        raise RuntimeError("semantic lookup failed")

    def forbidden_take(*_args, **_kwargs):
        raise AssertionError("failed lookup must not expose a semantic lease")

    def reject_missing_lease(query, response, owner_key="", dedup_key=None):
        semantic_puts.append((query, owner_key, dedup_key))
        return False

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=_SemanticErrorStreamCompletions())
    )
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(manager, "on_chat_complete", lambda *_args: None)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", False)
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "HAS_DYNAMIC_AGENTS", False)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", False)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", False)
    monkeypatch.setattr(server, "HAS_MEMORY_GRAPH", False)
    monkeypatch.setattr(server, "HAS_EXPERIENCE", False)
    monkeypatch.setattr(server, "HAS_FEWSHOT", False)
    monkeypatch.setattr(server, "HAS_LLM_JUDGE", False)
    monkeypatch.setattr(server, "HAS_AB_TESTING", False)
    monkeypatch.setattr(server, "HAS_METRICS", False)
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda *_args: ([{"role": "system", "content": "test"}], {}),
    )
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server.cache,
        "put",
        lambda query, *_args, **_kwargs: exact_puts.append(query),
    )
    monkeypatch.setattr(
        server.reflexion_engine,
        "evaluate_answer",
        lambda *_args: {"score": 6},
    )
    monkeypatch.setattr(server.quality_tracker, "record", lambda *_args: None)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args: None)
    monkeypatch.setattr(server, "semantic_get_async", semantic_error)
    monkeypatch.setattr(server, "semantic_take_dedup_lease", forbidden_take)
    monkeypatch.setattr(server, "semantic_put", reject_missing_lease)

    response = asyncio.run(server.chat_stream(
        server.ChatRequest.model_validate({
            "message": "stream semantic error fallback",
            "history": [],
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
    ))
    body = asyncio.run(_consume_stream_body(response))

    assert "Provider stream survives" in body
    assert exact_puts == ["stream semantic error fallback"]
    assert semantic_puts == [(
        "stream semantic error fallback",
        "user:alice",
        None,
    )]


def test_autocorrected_stream_resolves_waiter_on_original_cache_query(tmp_path, monkeypatch):
    import semantic_cache as semantic_cache_mod

    manager = _manager(tmp_path)
    owner_key = "user:alice"
    original_query = "vinh log co gi choi"
    corrected_query = "Vĩnh Long có gì chơi"
    first_acquired = threading.Event()
    waiter_started = threading.Event()
    allow_stream_finish = threading.Event()
    waiter_result = {}
    response_result = {}
    exact_put_queries = []
    holder_keys = []
    published_dedup_keys = []

    class SignalingDeduplicator(semantic_cache_mod.RequestDeduplicator):
        def acquire(self, query, timeout=5.0, owner_key=""):
            result = super().acquire(query, timeout=timeout, owner_key=owner_key)
            if result[0]:
                holder_keys.append(result[1])
                first_acquired.set()
            return result

        def wait_for(self, dedup_key, timeout=30):
            waiter_started.set()
            return super().wait_for(dedup_key, timeout=0.75)

    matcher = semantic_cache_mod.SemanticMatcher()
    semantic_cache = semantic_cache_mod.MultiTierCache(matcher, l1_max=10, l2_max=20)
    semantic_cache._l2_loaded = True
    semantic_cache._save_l2 = lambda: None
    deduplicator = SignalingDeduplicator()

    async def alice_owner(_request):
        return SimpleNamespace(owner_key=owner_key, cookie_value=None)

    def fake_create(*_args, stream=False, **_kwargs):
        if stream:
            def chunks():
                allow_stream_finish.wait(timeout=2)
                yield SimpleNamespace(
                    choices=[SimpleNamespace(
                        delta=SimpleNamespace(
                            content="Vĩnh Long có nhiều điểm tham quan rất hấp dẫn.",
                            tool_calls=None,
                        ),
                        finish_reason=None,
                    )]
                )
            return chunks()
        message = SimpleNamespace(
            content="unused",
            tool_calls=None,
            role="assistant",
            function_call=None,
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    def publish_semantic(query, response, owner_key="", dedup_key=None):
        published_dedup_keys.append(dedup_key)
        return semantic_cache_mod.semantic_put(
            query,
            response,
            owner_key=owner_key,
            dedup_key=dedup_key,
        )

    async def read_semantic(query, owner_key=""):
        return await semantic_cache_mod.semantic_get_async(
            query,
            owner_key=owner_key,
        )

    def take_semantic_lease(query, owner_key=""):
        return semantic_cache_mod.semantic_take_dedup_lease(
            query,
            owner_key=owner_key,
        )

    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(manager, "on_chat_complete", lambda *_args: None)
    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", lambda _ip: (True, {}))
    monkeypatch.setattr(server, "HAS_GUARDRAILS", False)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "HAS_AUTOCORRECT", True)
    monkeypatch.setattr(server, "HAS_CIRCUIT_BREAKER", False)
    monkeypatch.setattr(server, "HAS_DYNAMIC_AGENTS", False)
    monkeypatch.setattr(server, "HAS_OPTIMIZER", False)
    monkeypatch.setattr(server, "HAS_COST_TRACKER", False)
    monkeypatch.setattr(server, "HAS_MEMORY_GRAPH", False)
    monkeypatch.setattr(server, "HAS_EXPERIENCE", False)
    monkeypatch.setattr(server, "HAS_FEWSHOT", False)
    monkeypatch.setattr(server, "HAS_LLM_JUDGE", False)
    monkeypatch.setattr(server, "HAS_AB_TESTING", False)
    monkeypatch.setattr(server, "HAS_METRICS", False)
    monkeypatch.setattr(server, "autocorrect", lambda _query: {
        "was_corrected": True,
        "corrected": corrected_query,
    })
    monkeypatch.setattr(
        server,
        "_build_messages",
        lambda *_args: ([{"role": "system", "content": "test"}], {}),
    )
    monkeypatch.setattr(server, "get_client", lambda: fake_client)
    monkeypatch.setattr(server.cache, "get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        server.cache,
        "put",
        lambda query, *_args, **_kwargs: exact_put_queries.append(query),
    )
    monkeypatch.setattr(
        server.reflexion_engine,
        "evaluate_answer",
        lambda *_args: {"score": 6},
    )
    monkeypatch.setattr(server.quality_tracker, "record", lambda *_args: None)
    monkeypatch.setattr(server.analytics, "track_query", lambda *_args: None)
    monkeypatch.setattr(server, "semantic_get_async", read_semantic)
    monkeypatch.setattr(server, "semantic_take_dedup_lease", take_semantic_lease)
    monkeypatch.setattr(server, "semantic_put", publish_semantic)
    monkeypatch.setattr(semantic_cache_mod, "multi_tier_cache", semantic_cache)
    monkeypatch.setattr(semantic_cache_mod, "deduplicator", deduplicator)
    client = TestClient(server.app)

    request_thread = threading.Thread(
        target=lambda: response_result.setdefault(
            "response",
            client.post("/chat/stream", json={"message": original_query, "history": []}),
        )
    )
    request_thread.start()
    assert first_acquired.wait(timeout=5)

    waiter_thread = threading.Thread(
        target=lambda: waiter_result.setdefault(
            "value",
            semantic_cache_mod.semantic_get(original_query, owner_key=owner_key),
        )
    )
    waiter_thread.start()
    assert waiter_started.wait(timeout=2)
    allow_stream_finish.set()

    request_thread.join(timeout=3)
    waiter_thread.join(timeout=3)

    assert not request_thread.is_alive()
    assert not waiter_thread.is_alive()
    assert response_result["response"].status_code == 200
    assert waiter_result["value"]["reply"].startswith("Vĩnh Long")
    assert exact_put_queries == [original_query]
    assert published_dedup_keys == holder_keys


def test_admin_semantic_query_invalidation_clears_all_owner_namespaces(monkeypatch):
    import admin
    import semantic_cache as semantic_cache_mod

    matcher = semantic_cache_mod.SemanticMatcher()
    semantic_cache = semantic_cache_mod.MultiTierCache(matcher, l1_max=10, l2_max=20)
    semantic_cache._l2_loaded = True
    semantic_cache._save_l2 = lambda: None
    query = "same admin query"
    semantic_cache.put(query, {"owner": "alice"}, owner_key="user:alice")
    semantic_cache.put(query, {"owner": "bob"}, owner_key="user:bob")
    semantic_cache.put(query, {"owner": "legacy"})

    async def allow_admin(_request):
        return None

    monkeypatch.setattr(admin, "require_admin", allow_admin)
    monkeypatch.setattr(server, "HAS_SEMANTIC_CACHE", True)
    monkeypatch.setattr(server, "multi_tier_cache", semantic_cache)

    result = __import__("asyncio").run(
        server.semantic_cache_invalidate(
            server.SemanticCacheInvalidateRequest(query=query),
            SimpleNamespace(),
        )
    )

    assert result["success"] is True
    assert semantic_cache.get(query, owner_key="user:alice") is None
    assert semantic_cache.get(query, owner_key="user:bob") is None
    assert semantic_cache.get(query) is None


def test_welcome_ignores_client_profile_selector(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    alice = manager.cold.get_profile("user:alice")
    alice.interests = ["alice-only"]
    alice.conversation_count = 1
    target = manager.cold.get_profile("target-profile")
    target.interests = ["target-secret"]
    target.conversation_count = 1
    monkeypatch.setattr(server, "memory_manager", manager)

    async def alice_owner(_request):
        return SimpleNamespace(owner_key="user:alice", cookie_value=None)

    captured = {}

    def welcome(preferences):
        captured["preferences"] = preferences
        return {"greeting": "ok", "suggestions": []}

    monkeypatch.setattr(server, "resolve_chat_owner", alice_owner, raising=False)
    monkeypatch.setattr(server, "generate_welcome_message", welcome)
    client = TestClient(server.app)

    response = client.get("/welcome?session_id=target-profile")

    assert response.status_code == 200
    assert captured["preferences"]["interests"] == ["alice-only"]
    assert "target-secret" not in captured["preferences"]["interests"]


def test_welcome_does_not_create_absent_profile(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    monkeypatch.setattr(server, "memory_manager", manager)
    monkeypatch.setattr(server, "resolve_chat_owner", _new_anonymous_owner)
    captured = []
    monkeypatch.setattr(
        server,
        "generate_welcome_message",
        lambda preferences: captured.append(preferences) or {"greeting": "ok", "suggestions": []},
    )
    client = TestClient(server.app)

    response = client.get("/welcome")

    assert response.status_code == 200
    assert captured == [None]
    assert manager.cold._profiles == {}
