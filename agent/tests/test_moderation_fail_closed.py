"""Regression tests for fail-closed moderation and publication scheduling."""

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import moderation


_VALID_TEXT_PROVIDER_PAYLOAD = {
    "id": "modr-test",
    "model": "omni-moderation-latest",
    "results": [{
        "flagged": False,
        "categories": {
            "sexual": False,
            "hate": False,
            "harassment": False,
            "self-harm": False,
            "sexual/minors": False,
            "hate/threatening": False,
            "violence/graphic": False,
            "self-harm/intent": False,
            "self-harm/instructions": False,
            "harassment/threatening": False,
            "violence": False,
            "illicit": False,
            "illicit/violent": False,
        },
        "category_scores": {
            "sexual": 0.001,
            "hate": 0.002,
            "harassment": 0.01,
            "self-harm": 0.001,
            "sexual/minors": 0.001,
            "hate/threatening": 0.001,
            "violence/graphic": 0.001,
            "self-harm/intent": 0.001,
            "self-harm/instructions": 0.001,
            "harassment/threatening": 0.001,
            "violence": 0.02,
            "illicit": 0.001,
            "illicit/violent": 0.001,
        },
        "category_applied_input_types": {
            "sexual": ["text"],
            "hate": ["text"],
            "harassment": ["text"],
            "self-harm": ["text"],
            "sexual/minors": ["text"],
            "hate/threatening": ["text"],
            "violence/graphic": ["text"],
            "self-harm/intent": ["text"],
            "self-harm/instructions": ["text"],
            "harassment/threatening": ["text"],
            "violence": ["text"],
            "illicit": ["text"],
            "illicit/violent": ["text"],
        },
    }],
}

_VALID_IMAGE_PROVIDER_PAYLOAD = {
    "responses": [{
        "safeSearchAnnotation": {
            "adult": "VERY_UNLIKELY",
            "spoof": "VERY_UNLIKELY",
            "medical": "UNLIKELY",
            "violence": "UNLIKELY",
            "racy": "VERY_UNLIKELY",
        },
    }],
}


class _JsonResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _JsonProviderClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        return _JsonResponse(self._payload)


def _install_provider_payload(monkeypatch, payload):
    monkeypatch.setattr(
        moderation.httpx,
        "AsyncClient",
        lambda **_kwargs: _JsonProviderClient(payload),
    )


def test_missing_text_provider_keeps_clean_content_pending(monkeypatch):
    monkeypatch.setattr(moderation, "OPENAI_API_KEY", "")

    result = asyncio.run(moderation.moderate_content("Một bài viết sạch", []))

    assert result["status"] == "pending"


def test_text_provider_error_keeps_content_non_public(monkeypatch):
    async def provider_error(_content):
        return {
            "score": 0.0,
            "reasons": ["moderation provider unavailable"],
            "categories": {},
            "available": False,
        }

    monkeypatch.setattr(moderation, "_moderate_text", provider_error)

    result = asyncio.run(moderation.moderate_content("Một bài viết sạch", []))

    assert result["status"] in {"pending", "quarantined"}


def test_missing_image_provider_keeps_content_non_public(monkeypatch):
    monkeypatch.setattr(moderation, "VISION_API_KEY", "")

    result = asyncio.run(
        moderation.moderate_content("Một bài viết có ảnh", ["https://example.test/photo.jpg"])
    )

    assert result["status"] in {"pending", "quarantined"}


def test_image_provider_error_keeps_content_non_public(monkeypatch):
    async def provider_error(_image_urls):
        return {
            "score": 0.0,
            "reasons": ["image moderation provider unavailable"],
            "categories": {},
            "available": False,
        }

    monkeypatch.setattr(moderation, "_moderate_images", provider_error)

    result = asyncio.run(
        moderation.moderate_content("Một bài viết có ảnh", ["https://example.test/photo.jpg"])
    )

    assert result["status"] in {"pending", "quarantined"}


@pytest.mark.parametrize(
    "payload",
    [
        {"results": [{}]},
        {"results": [{"flagged": False, "categories": {}, "category_scores": {}}]},
        {"results": [{"flagged": False, "categories": {"violence": False}, "category_scores": {"violence": 0.01}}]},
        {"results": [{"flagged": False, "categories": [], "category_scores": {"violence": 0.1}}]},
        {"results": [{"flagged": False, "categories": {"violence": False}, "category_scores": {"violence": "clean"}}]},
    ],
)
def test_malformed_text_provider_payload_keeps_content_pending(monkeypatch, payload):
    monkeypatch.setattr(moderation, "OPENAI_API_KEY", "test-key")
    _install_provider_payload(monkeypatch, payload)

    result = asyncio.run(moderation.moderate_content("Một nội dung sạch", []))

    assert result["status"] == "pending"
    assert result["moderation_available"] is False


def test_complete_text_provider_payload_preserves_approved_behavior(monkeypatch):
    monkeypatch.setattr(moderation, "OPENAI_API_KEY", "test-key")
    _install_provider_payload(monkeypatch, _VALID_TEXT_PROVIDER_PAYLOAD)

    result = asyncio.run(moderation.moderate_content("Một nội dung sạch", []))

    assert result["status"] == "approved"
    assert result["moderation_available"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"responses": [{}]},
        {"responses": [{"safeSearchAnnotation": {"adult": "VERY_UNLIKELY", "violence": "UNLIKELY"}}]},
        {"responses": [{"safeSearchAnnotation": {"adult": "VERY_UNLIKELY", "violence": "UNLIKELY", "racy": "VERY_UNLIKELY"}}]},
        {"responses": [{"safeSearchAnnotation": {"adult": "VERY_UNLIKELY", "spoof": "VERY_UNLIKELY", "medical": "UNKNOWN", "violence": "UNLIKELY", "racy": "VERY_UNLIKELY"}}]},
        {"responses": [{"safeSearchAnnotation": {"adult": "UNKNOWN", "violence": "UNLIKELY", "racy": "VERY_UNLIKELY"}}]},
        {"responses": [{"safeSearchAnnotation": ["not", "a", "mapping"]}]},
    ],
)
def test_malformed_image_provider_payload_keeps_content_pending(monkeypatch, payload):
    monkeypatch.setattr(moderation, "VISION_API_KEY", "test-key")
    _install_provider_payload(monkeypatch, payload)

    result = asyncio.run(
        moderation.moderate_content("", ["https://example.test/photo.jpg"])
    )

    assert result["status"] == "pending"
    assert result["moderation_available"] is False


def test_complete_image_provider_payload_preserves_approved_behavior(monkeypatch):
    monkeypatch.setattr(moderation, "VISION_API_KEY", "test-key")
    _install_provider_payload(monkeypatch, _VALID_IMAGE_PROVIDER_PAYLOAD)

    result = asyncio.run(
        moderation.moderate_content("", ["https://example.test/photo.jpg"])
    )

    assert result["status"] == "approved"
    assert result["moderation_available"] is True


def test_missing_internal_availability_signal_fails_closed(monkeypatch):
    async def text_without_signal(_content):
        return {"score": 0.01, "reasons": [], "categories": {"violence": 0.01}}

    async def complete_image_result(_urls):
        return {"score": 0.0, "reasons": [], "categories": {}, "available": True}

    monkeypatch.setattr(moderation, "_moderate_text", text_without_signal)
    monkeypatch.setattr(moderation, "_moderate_images", complete_image_result)

    result = asyncio.run(moderation.moderate_content("Một nội dung sạch", []))

    assert result["status"] == "pending"
    assert result["moderation_available"] is False


def test_enhanced_pipeline_missing_base_availability_signal_fails_closed(monkeypatch):
    async def base_without_signal(_content, _images=None):
        return {"status": "approved", "score": 0.01, "reasons": []}

    monkeypatch.setattr(moderation, "moderate_content", base_without_signal)
    monkeypatch.setattr(moderation, "get_user_trust_level", lambda _user_id: "new")

    result = asyncio.run(
        moderation.moderate_content_enhanced("Một nội dung sạch", user_id="user-1")
    )

    assert result["status"] == "pending"
    assert result["moderation_available"] is False


def test_enhanced_pipeline_preserves_fail_closed_base_status(monkeypatch):
    monkeypatch.setattr(moderation, "OPENAI_API_KEY", "")

    result = asyncio.run(
        moderation.moderate_content_enhanced("Một bài viết sạch", user_id="u-test", image_urls=[])
    )

    assert result["status"] in {"pending", "quarantined"}


def test_moderation_auto_escalation_never_approves_pending_posts(monkeypatch):
    import scheduler

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeDb:
        _use_pg = True

        def __init__(self):
            self.executed = []

        def _conn(self):
            return FakeConnection()

        def _execute(self, _conn, sql, params):
            self.executed.append((sql, params))

    fake_db = FakeDb()
    monkeypatch.setattr(scheduler, "db", fake_db, raising=False)

    scheduler.task_moderation_auto_escalation()

    assert not any("SET moderation_status = 'approved'" in sql for sql, _ in fake_db.executed)


def _request(path: str) -> Request:
    return Request({
        "type": "http",
        "method": "PUT",
        "path": path,
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    })


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("display_name", "Tên hiển thị mới"),
        ("full_name", "Nguyễn Văn Mới"),
        ("bio", "Tiểu sử công khai mới"),
    ],
)
def test_pending_moderation_never_persists_public_profile_fields(monkeypatch, field, value):
    import auth
    import ratelimit

    user = {"id": "user-1", "phone": "0901234567", "display_name": "Tên cũ"}
    persisted = []

    async def current_user(_request):
        return user

    async def pending_moderation(_content, _images=None):
        return {"status": "pending", "score": 0.0, "reasons": [], "moderation_available": False}

    async def persist(_user_id, fields):
        persisted.append(fields)
        return {**user, **fields}

    monkeypatch.setattr(auth, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(auth, "_persist_profile_fields", persist)
    monkeypatch.setattr(moderation, "moderate_content", pending_moderation)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.update_profile(auth.ProfileUpdate(**{field: value}), _request("/auth/profile")))

    assert exc.value.status_code == 503
    assert persisted == []


def test_approved_profile_moderation_still_persists(monkeypatch):
    import auth
    import ratelimit

    user = {"id": "user-1", "phone": "0901234567", "display_name": "Tên cũ"}
    persisted = []

    async def current_user(_request):
        return user

    async def approved_moderation(_content, _images=None):
        return {"status": "approved", "score": 0.01, "reasons": [], "moderation_available": True}

    async def persist(_user_id, fields):
        persisted.append(fields)
        return {**user, **fields}

    monkeypatch.setattr(auth, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(auth, "_persist_profile_fields", persist)
    monkeypatch.setattr(moderation, "moderate_content", approved_moderation)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)

    result = asyncio.run(
        auth.update_profile(auth.ProfileUpdate(display_name="Tên mới"), _request("/auth/profile"))
    )

    assert persisted == [{"display_name": "Tên mới"}]
    assert result["user"]["display_name"] == "Tên mới"


class _CollectionConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _CollectionDb:
    _ph = "%s"

    def __init__(self):
        self.inserted = []

    def _conn(self):
        return _CollectionConnection()

    def _fetchone(self, _conn, sql, params):
        if "pg_advisory_xact_lock" in sql:
            return {"locked": True}
        if "COUNT(*)" in sql:
            return {"c": 0}
        self.inserted.append(params)
        return {
            "id": "collection-1",
            "name": params[1],
            "description": params[2],
            "is_public": params[3],
            "created_at": "2026-07-26",
        }

    @staticmethod
    def _row_to_dict(row):
        return row


@pytest.mark.parametrize("statuses", [["pending"], ["approved", "pending"]])
def test_pending_moderation_never_creates_public_collection(monkeypatch, statuses):
    import social

    fake_db = _CollectionDb()
    results = iter(statuses)

    async def moderate(_content, _images=None):
        status = next(results)
        return {
            "status": status,
            "score": 0.0,
            "reasons": [],
            "moderation_available": status == "approved",
        }

    monkeypatch.setattr(social, "db", fake_db)
    monkeypatch.setattr(social, "moderate_content", moderate)
    monkeypatch.setattr(social, "check_rate", lambda *_args, **_kwargs: None)
    body = social.CreateCollection(
        name="Bộ sưu tập mới",
        description="Mô tả mới" if len(statuses) > 1 else "",
        is_public=True,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(social.create_collection(body, user={"id": "user-1"}))

    assert exc.value.status_code == 503
    assert fake_db.inserted == []


def test_private_collection_remains_storable_when_provider_is_pending(monkeypatch):
    import social

    fake_db = _CollectionDb()

    async def pending_moderation(_content, _images=None):
        return {"status": "pending", "score": 0.0, "reasons": [], "moderation_available": False}

    monkeypatch.setattr(social, "db", fake_db)
    monkeypatch.setattr(social, "moderate_content", pending_moderation)
    monkeypatch.setattr(social, "check_rate", lambda *_args, **_kwargs: None)
    body = social.CreateCollection(name="Bộ sưu tập riêng", is_public=False)

    result = asyncio.run(social.create_collection(body, user={"id": "user-1"}))

    assert result["collection"]["is_public"] is False
    assert fake_db.inserted[0][3] is False


def test_approved_public_collection_behavior_is_preserved(monkeypatch):
    import social

    fake_db = _CollectionDb()

    async def approved_moderation(_content, _images=None):
        return {"status": "approved", "score": 0.01, "reasons": [], "moderation_available": True}

    monkeypatch.setattr(social, "db", fake_db)
    monkeypatch.setattr(social, "moderate_content", approved_moderation)
    monkeypatch.setattr(social, "check_rate", lambda *_args, **_kwargs: None)
    body = social.CreateCollection(name="Bộ sưu tập công khai", is_public=True)

    result = asyncio.run(social.create_collection(body, user={"id": "user-1"}))

    assert result["collection"]["is_public"] is True
    assert fake_db.inserted[0][3] is True
