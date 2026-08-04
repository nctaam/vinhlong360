"""Real-transport contracts for receipt-bound feedback telemetry."""

from types import SimpleNamespace

import httpx
import pytest

import feedback_policy
import middleware
import metrics
import server


USER_OWNER = "user:00000000-0000-0000-0000-000000000001"
ANON_OWNER = "anon:" + "a" * 64
VALID_RECEIPT = "A" * 43
INVALID_REQUEST = {"detail": "Invalid feedback request"}
UNAVAILABLE = {"detail": "Feedback unavailable"}
RATE_LIMITED = {"detail": "Too many feedback requests"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


class RecordingLimiter:
    def __init__(self, label, events=None, result=(True, {"retry_after": 0})):
        self.label = label
        self.events = events
        self.result = result
        self.calls = []

    def is_allowed(self, key):
        self.calls.append(key)
        if self.events is not None:
            self.events.append(self.label)
        return self.result


def _install_owner(monkeypatch, owner_key=USER_OWNER, cookie_value=None, events=None):
    async def resolve_owner(_request):
        if events is not None:
            events.append("owner")
        return SimpleNamespace(owner_key=owner_key, cookie_value=cookie_value)

    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner)


def _install_allowed_limits(monkeypatch, events=None):
    ip = RecordingLimiter("ip", events)
    owner = RecordingLimiter("owner-limit", events)
    monkeypatch.setattr(server, "feedback_ip_limiter", ip, raising=False)
    monkeypatch.setattr(server, "feedback_owner_limiter", owner, raising=False)
    return ip, owner


def _install_forbidden_state_mutations(monkeypatch):
    import database
    import learn_loop

    def forbidden(*_args, **_kwargs):
        raise AssertionError("feedback transport must not mutate personalized state")

    monkeypatch.setattr(server.memory_manager, "feedback", forbidden)
    monkeypatch.setattr(learn_loop, "record_feedback", forbidden)
    monkeypatch.setattr(learn_loop, "_adjust_entity_confidence", forbidden)
    monkeypatch.setattr(learn_loop, "_save_feedback", forbidden)
    monkeypatch.setattr(database.db, "save_feedback", forbidden)
    monkeypatch.setattr(server.knowledge, "reload", forbidden)
    monkeypatch.setattr(server, "sync_data_json_to_js", forbidden)


@pytest.mark.anyio
async def test_receipt_and_rating_succeed_without_personalization_writes(monkeypatch):
    _install_owner(monkeypatch, cookie_value="visitor.signature")
    ip_limiter, owner_limiter = _install_allowed_limits(monkeypatch)
    _install_forbidden_state_mutations(monkeypatch)
    consume_calls = []
    metric_calls = []

    def consume(receipt, owner_key, rating):
        consume_calls.append((receipt, owner_key, rating))
        return feedback_policy.FeedbackConsumeResult(rating=rating, idempotent=False)

    monkeypatch.setattr(server, "consume_feedback_receipt", consume, raising=False)
    monkeypatch.setattr(server, "HAS_METRICS", True)
    monkeypatch.setattr(
        server,
        "track_feedback_attempt",
        lambda **kwargs: metric_calls.append(kwargs),
        raising=False,
    )
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/feedback",
            json={"receipt": VALID_RECEIPT, "rating": 1},
        )

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert "vl360_chat_owner=visitor.signature" in response.headers["set-cookie"]
    assert len(ip_limiter.calls) == 1
    assert owner_limiter.calls == [USER_OWNER]
    assert consume_calls == [(VALID_RECEIPT, USER_OWNER, 1)]
    assert metric_calls == [{
        "reason": "accepted",
        "owner_kind": "authenticated",
        "rating": 1,
    }]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("json_payload", "raw_payload"),
    [
        ({"receipt": VALID_RECEIPT, "rating": 1, "user_id": "u"}, None),
        ({"receipt": VALID_RECEIPT, "rating": 1, "session_id": "s"}, None),
        ({"receipt": VALID_RECEIPT, "rating": 1, "query": "private"}, None),
        ({"receipt": VALID_RECEIPT, "rating": 1, "entity_id": "e"}, None),
        ({"receipt": VALID_RECEIPT, "rating": 2}, None),
        ({"receipt": VALID_RECEIPT, "rating": True}, None),
        (None, b'{"receipt":'),
    ],
)
async def test_invalid_payloads_consume_ip_then_owner_before_bounded_422(
    monkeypatch,
    json_payload,
    raw_payload,
):
    events = []
    _install_owner(monkeypatch, cookie_value="rotated.signature", events=events)
    ip_limiter, owner_limiter = _install_allowed_limits(monkeypatch, events=events)
    consume_calls = []
    monkeypatch.setattr(
        server,
        "consume_feedback_receipt",
        lambda *_args, **_kwargs: consume_calls.append(True),
        raising=False,
    )
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        if raw_payload is None:
            response = await client.post("/feedback", json=json_payload)
        else:
            response = await client.post(
                "/feedback",
                content=raw_payload,
                headers={"Content-Type": "application/json"},
            )

    assert response.status_code == 422
    assert response.json() == INVALID_REQUEST
    assert events == ["ip", "owner", "owner-limit"]
    assert len(ip_limiter.calls) == 1
    assert owner_limiter.calls == [USER_OWNER]
    assert consume_calls == []
    assert "vl360_chat_owner=rotated.signature" in response.headers["set-cookie"]


@pytest.mark.anyio
async def test_ip_limit_rejects_before_owner_resolution(monkeypatch):
    ip_limiter = RecordingLimiter(
        "ip",
        result=(False, {"retry_after": 17}),
    )
    monkeypatch.setattr(server, "feedback_ip_limiter", ip_limiter, raising=False)

    async def forbidden_owner(_request):
        raise AssertionError("owner resolution must follow the IP limiter")

    monkeypatch.setattr(server, "resolve_chat_owner", forbidden_owner)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/feedback", content=b"not-json")

    assert response.status_code == 429
    assert response.json() == RATE_LIMITED
    assert response.headers["retry-after"] == "17"
    assert "set-cookie" not in response.headers


@pytest.mark.anyio
async def test_owner_limit_returns_retry_after_and_rotated_cookie(monkeypatch):
    _install_owner(monkeypatch, cookie_value="rotated.signature")
    monkeypatch.setattr(
        server,
        "feedback_ip_limiter",
        RecordingLimiter("ip"),
        raising=False,
    )
    owner_limiter = RecordingLimiter(
        "owner",
        result=(False, {"retry_after": 23}),
    )
    monkeypatch.setattr(server, "feedback_owner_limiter", owner_limiter, raising=False)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/feedback", content=b"not-json")

    assert response.status_code == 429
    assert response.json() == RATE_LIMITED
    assert response.headers["retry-after"] == "23"
    assert owner_limiter.calls == [USER_OWNER]
    assert "vl360_chat_owner=rotated.signature" in response.headers["set-cookie"]


@pytest.mark.anyio
async def test_invalid_receipt_shape_uses_common_unavailable_response(monkeypatch):
    _install_owner(monkeypatch)
    ip_limiter, owner_limiter = _install_allowed_limits(monkeypatch)
    consume_calls = []
    monkeypatch.setattr(
        server,
        "consume_feedback_receipt",
        lambda *_args, **_kwargs: consume_calls.append(True),
        raising=False,
    )
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/feedback",
            json={"receipt": "short", "rating": 1},
        )

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE
    assert consume_calls == []
    assert len(ip_limiter.calls) == 1
    assert owner_limiter.calls == [USER_OWNER]


@pytest.mark.anyio
@pytest.mark.parametrize("reason", ["fake", "expired", "wrong-owner", "store"])
async def test_receipt_failures_share_one_public_response(monkeypatch, reason):
    _install_owner(monkeypatch)
    _install_allowed_limits(monkeypatch)

    def unavailable(*_args, **_kwargs):
        raise feedback_policy.FeedbackUnavailable(f"private-{reason}")

    monkeypatch.setattr(server, "consume_feedback_receipt", unavailable, raising=False)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/feedback",
            json={"receipt": VALID_RECEIPT, "rating": 0},
        )

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE
    assert reason not in response.text


@pytest.mark.anyio
async def test_same_rating_replay_is_idempotent_and_conflict_is_unavailable(monkeypatch):
    _install_owner(monkeypatch)
    _ip_limiter, owner_limiter = _install_allowed_limits(monkeypatch)
    calls = []

    def consume(_receipt, _owner_key, rating):
        calls.append(rating)
        if calls == [1]:
            return feedback_policy.FeedbackConsumeResult(rating=1, idempotent=False)
        if calls == [1, 1]:
            return feedback_policy.FeedbackConsumeResult(rating=1, idempotent=True)
        raise feedback_policy.FeedbackRejected("CONFLICTING_FEEDBACK_REPLAY")

    monkeypatch.setattr(server, "consume_feedback_receipt", consume, raising=False)
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/feedback",
            json={"receipt": VALID_RECEIPT, "rating": 1},
        )
        replay = await client.post(
            "/feedback",
            json={"receipt": VALID_RECEIPT, "rating": 1},
        )
        conflict = await client.post(
            "/feedback",
            json={"receipt": VALID_RECEIPT, "rating": 0},
        )

    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json() == {"success": True}
    assert conflict.status_code == 503
    assert conflict.json() == UNAVAILABLE
    assert calls == [1, 1, 0]
    assert owner_limiter.calls == [USER_OWNER, USER_OWNER, USER_OWNER]


@pytest.mark.anyio
async def test_authenticated_and_anonymous_feedback_keep_owner_kinds_separate(monkeypatch):
    ip_limiter, owner_limiter = _install_allowed_limits(monkeypatch)
    consumed = []
    metrics = []

    async def resolve_owner(request):
        if request.headers.get("Authorization"):
            return SimpleNamespace(owner_key=USER_OWNER, cookie_value=None)
        return SimpleNamespace(owner_key=ANON_OWNER, cookie_value=None)

    def consume(receipt, owner_key, rating):
        consumed.append((receipt, owner_key, rating))
        return feedback_policy.FeedbackConsumeResult(rating=rating, idempotent=False)

    monkeypatch.setattr(server, "resolve_chat_owner", resolve_owner)
    monkeypatch.setattr(server, "consume_feedback_receipt", consume, raising=False)
    monkeypatch.setattr(server, "HAS_METRICS", True)
    monkeypatch.setattr(
        server,
        "track_feedback_attempt",
        lambda **kwargs: metrics.append(kwargs),
        raising=False,
    )
    transport = httpx.ASGITransport(app=server.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        authenticated = await client.post(
            "/feedback",
            headers={"Authorization": "Bearer test"},
            json={"receipt": VALID_RECEIPT, "rating": 1},
        )
        anonymous = await client.post(
            "/feedback",
            json={"receipt": "B" * 43, "rating": 0},
        )

    assert authenticated.status_code == anonymous.status_code == 200
    assert [item[1] for item in consumed] == [USER_OWNER, ANON_OWNER]
    assert owner_limiter.calls == [USER_OWNER, ANON_OWNER]
    assert len(ip_limiter.calls) == 2
    assert [item["owner_kind"] for item in metrics] == ["authenticated", "anonymous"]


def test_feedback_limiters_use_approved_budgets_and_reset_registration():
    assert middleware.feedback_ip_limiter.max_requests == 30
    assert middleware.feedback_ip_limiter.window == 3600
    assert middleware.feedback_owner_limiter.max_requests == 20
    assert middleware.feedback_owner_limiter.window == 3600
    assert middleware.feedback_ip_limiter in middleware._all_limiters
    assert middleware.feedback_owner_limiter in middleware._all_limiters

    middleware.feedback_ip_limiter.is_allowed("198.51.100.10")
    middleware.feedback_owner_limiter.is_allowed(USER_OWNER)
    middleware._reset_limiters()

    assert middleware.feedback_ip_limiter._requests == {}
    assert middleware.feedback_owner_limiter._requests == {}


def test_feedback_metrics_collapse_unbounded_dimensions():
    labels = {
        "reason": "receipt_rejected",
        "owner_kind": "unknown",
        "rating": "unknown",
    }
    before = metrics.feedback_transport_total.get(labels)

    metrics.track_feedback_attempt(
        reason="attacker-controlled-reason",
        owner_kind="attacker-controlled-owner",
        rating=99,
    )

    assert metrics.feedback_transport_total.get(labels) == before + 1
