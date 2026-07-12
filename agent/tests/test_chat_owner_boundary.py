"""Security boundary tests for server-derived chat ownership."""

import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import Response
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ["BUILD_SEARCH_INDEXES"] = "false"
os.environ["BACKGROUND_INDEX_BUILD"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

import server  # noqa: E402
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

    async def bob_owner(_request):
        return SimpleNamespace(owner_key="user:bob", cookie_value=None)

    monkeypatch.setattr(server, "resolve_chat_owner", bob_owner, raising=False)
    forbidden = Mock(side_effect=AssertionError("must not be accessed for an ownership miss"))
    monkeypatch.setattr(manager, "on_message", forbidden)
    monkeypatch.setattr(server.chat_limiter, "is_allowed", forbidden)
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server, "_build_messages", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    client = TestClient(server.app)

    response = client.post(
        "/chat",
        json={"message": "steal", "session_id": conversation.session_id},
    )

    assert response.status_code == 404
    forbidden.assert_not_called()
    assert ("user:bob", conversation.session_id) not in manager._sessions


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

    response = client.get("/chat/stream", params={"message": "   "})

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

    response = client.get("/chat/stream", params={"message": "blocked"})

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
    monkeypatch.setattr(manager, "on_message", forbidden)
    monkeypatch.setattr(server.stream_limiter, "is_allowed", forbidden)
    monkeypatch.setattr(server.cache, "get", forbidden)
    monkeypatch.setattr(server, "_build_messages", forbidden)
    monkeypatch.setattr(server, "get_client", forbidden)
    client = TestClient(server.app)

    response = client.get(
        "/chat/stream",
        params={"message": "steal", "session_id": conversation.session_id},
    )

    assert response.status_code == 404
    assert "vl360_chat_owner=" in response.headers["set-cookie"]
    forbidden.assert_not_called()


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
