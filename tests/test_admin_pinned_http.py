from __future__ import annotations

import asyncio
import copy

import pytest
from fastapi import HTTPException

import admin
import pinned_http as ph
import storage


async def _inline_threadpool(fn):
    return fn()


def _response(
    status: int = 200,
    content: bytes = b"image",
    headers: tuple[tuple[str, str], ...] = (("content-type", "image/webp"),),
) -> ph.PinnedResponse:
    return ph.PinnedResponse(
        status_code=status,
        url="https://cdn.example/final.webp",
        headers=headers,
        content=content,
        redirects=(),
    )


def test_admin_fetch_passes_dynamic_image_egress_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda url, **kwargs: calls.append((url, kwargs)) or _response(),
    )
    data = asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 12 * 1024 * 1024))
    assert data == b"image"
    assert calls == [(
        "https://cdn.example/a",
        {
            "user_agent": "vinhlong360-image-review/1.0 (+https://vinhlong360.vn)",
            "policy": ph.EgressPolicy(
                max_encoded_bytes=12 * 1024 * 1024,
                max_decoded_bytes=12 * 1024 * 1024,
                accepted_encodings=("identity",),
                inactivity_timeout_seconds=25.0,
                total_timeout_seconds=25.0,
                max_redirects=5,
            ),
        },
    )]


def test_admin_fetch_does_not_redecode_http_decoded_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoded = b"already-decoded-image"
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=decoded,
            headers=(
                ("content-type", "image/webp"),
                ("content-encoding", "gzip"),
                ("content-length", "9"),
            ),
        ),
    )
    result = asyncio.run(
        admin._approve_fetch_image_data(
            "https://cdn.example/a",
            _inline_threadpool,
            1024,
        )
    )
    assert result == decoded


@pytest.mark.parametrize(
    "error",
    [
        ph.InvalidDestinationError("invalid"),
        ph.ResolutionError("dns"),
        ph.BlockedAddressError("blocked"),
        ph.PeerMismatchError("peer"),
        ph.RedirectPolicyError("redirect"),
    ],
)
def test_admin_fetch_maps_policy_failures_to_400(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    monkeypatch.setattr(admin._PINNED_HTTP, "get", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 1024))
    assert caught.value.status_code == 400


def test_admin_fetch_maps_transport_and_status_failures_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin._PINNED_HTTP, "get", lambda *_args, **_kwargs: _response(status=404))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 1024))
    assert caught.value.status_code == 502


@pytest.mark.parametrize("content", [b"", b"x" * 1025])
def test_admin_fetch_preserves_empty_and_size_rejection(
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
) -> None:
    monkeypatch.setattr(admin._PINNED_HTTP, "get", lambda *_args, **_kwargs: _response(content=content))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin._approve_fetch_image_data("https://cdn.example/a", _inline_threadpool, 1024))
    assert caught.value.status_code == 400


class RecordingDB:
    def __init__(self, entity: dict) -> None:
        self.entity = copy.deepcopy(entity)
        self.upserts: list[dict] = []

    def get_entity(self, entity_id: str) -> dict:
        assert entity_id == self.entity["id"]
        return copy.deepcopy(self.entity)

    def upsert_entity(self, entity: dict) -> None:
        saved = copy.deepcopy(entity)
        self.upserts.append(saved)
        self.entity = saved


@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (ph.InvalidDestinationError("invalid"), "URL ảnh không hợp lệ (chỉ http/https)"),
        (ph.ResolutionError("dns"), "Không phân giải được host ảnh"),
        (ph.BlockedAddressError("blocked"), "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)"),
        (ph.PeerMismatchError("peer"), "Host ảnh trỏ địa chỉ nội bộ — từ chối (SSRF)"),
    ],
)
def test_validate_public_image_url_preserves_localized_400(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    detail: str,
) -> None:
    def fail(_url: str) -> None:
        raise error

    monkeypatch.setattr(admin, "validate_public_url", fail)
    with pytest.raises(HTTPException) as caught:
        admin._validate_public_image_url("https://example.com/image.webp")
    assert caught.value.status_code == 400
    assert caught.value.detail == detail


def test_add_entity_image_url_validates_without_fetching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://licensed.example/original.webp"
    database = RecordingDB({
        "id": "entity-1",
        "name": "Entity",
        "type": "attraction",
        "images": [],
    })
    validations: list[str] = []
    monkeypatch.setattr(admin, "is_canonical_legacy_entity_image", lambda _url: True)
    monkeypatch.setattr(admin, "_validate_public_image_url", validations.append)
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: pytest.fail("validation-only route fetched content"),
    )
    monkeypatch.setattr(admin, "db", database)
    monkeypatch.setattr(admin, "_sync_kb", lambda: None)

    result = asyncio.run(
        admin.add_entity_image_url(
            "entity-1",
            admin._EntityImageURL(url=url),
        )
    )
    assert validations == [url]
    assert result == {"status": "added", "images": [url]}
    assert database.upserts[0]["images"] == [url]


def test_admin_fetch_executes_pinned_get_inside_threadpool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inside_threadpool = False

    def get(_url: str, **_kwargs) -> ph.PinnedResponse:
        assert inside_threadpool is True
        return _response(content=b"image")

    async def guarded_threadpool(fn):
        nonlocal inside_threadpool
        inside_threadpool = True
        try:
            return fn()
        finally:
            inside_threadpool = False

    monkeypatch.setattr(admin._PINNED_HTTP, "get", get)
    assert asyncio.run(
        admin._approve_fetch_image_data(
            "https://example.com/image.webp",
            guarded_threadpool,
            1024,
        )
    ) == b"image"


@pytest.mark.parametrize(
    ("outcome", "expected_status"),
    [
        (ph.BlockedAddressError("blocked"), 400),
        (ph.RedirectPolicyError("loop"), 400),
        (ph.PinnedBodyLimitError("large"), 400),
        (ph.PinnedContentEncodingError("encoding"), 400),
        (ph.PinnedDeadlineExceeded("deadline"), 502),
        (ph.ResolverSaturatedError("dns busy"), 502),
        (ph.PinnedTransportError("connect"), 502),
        (_response(status=404), 502),
        (_response(content=b""), 400),
        (_response(content=b"12345"), 400),
    ],
    ids=[
        "blocked",
        "redirect",
        "body-limit",
        "encoding",
        "deadline",
        "dns-saturated",
        "transport",
        "http-status",
        "empty",
        "oversize",
    ],
)
def test_approval_fetch_failures_leave_all_state_untouched(
    monkeypatch: pytest.MonkeyPatch,
    outcome: Exception | ph.PinnedResponse,
    expected_status: int,
) -> None:
    suggestion = {
        "id": "suggestion-1",
        "entity_id": "entity-1",
        "candidate_url": "https://licensed.example/original.webp",
        "status": "pending",
        "license": "CC BY-SA 4.0",
        "author": "Author",
        "source": "wikipedia-vi",
    }
    original_entity = {
        "id": "entity-1",
        "name": "Entity",
        "type": "attraction",
        "images": [],
        "attributes": {},
    }
    database = RecordingDB(original_entity)
    uploads: list[bytes] = []
    status_changes: list[tuple] = []
    syncs: list[bool] = []

    def get(*_args, **_kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(admin, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(admin, "db", database)
    monkeypatch.setattr(admin._imgq, "get_suggestion", lambda _id: copy.deepcopy(suggestion))
    monkeypatch.setattr(
        admin._imgq,
        "mark_status",
        lambda *args, **kwargs: status_changes.append((args, kwargs)),
    )
    monkeypatch.setattr(admin, "_sync_kb", lambda: syncs.append(True))
    monkeypatch.setattr(admin._PINNED_HTTP, "get", get)
    monkeypatch.setattr(storage, "MAX_IMAGE_SIZE", 4)
    monkeypatch.setattr(
        storage.storage,
        "upload_image_set",
        lambda data, *_args: uploads.append(data) or {"md": "/img/entities/entity-1.webp"},
    )

    with pytest.raises(HTTPException) as caught:
        asyncio.run(admin.approve_image_suggestion("suggestion-1"))
    assert caught.value.status_code == expected_status
    assert database.entity == original_entity
    assert database.upserts == []
    assert uploads == []
    assert status_changes == []
    assert syncs == []
    assert suggestion["status"] == "pending"


def test_approval_keeps_original_candidate_url_in_redirected_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_url = "https://licensed.example/original.webp"
    suggestion = {
        "id": "suggestion-1",
        "entity_id": "entity-1",
        "candidate_url": candidate_url,
        "status": "pending",
        "license": "CC BY-SA 4.0",
        "author": "Author",
        "source": "wikipedia-vi",
        "wp_title": "File:Original.webp",
    }
    database = RecordingDB({
        "id": "entity-1",
        "name": "Entity",
        "type": "attraction",
        "images": [],
        "attributes": {},
    })
    status_changes: list[tuple] = []

    monkeypatch.setattr(admin, "_reject_non_ai_media", lambda: None)
    monkeypatch.setattr(
        admin,
        "_validate_public_image_url",
        lambda _url: pytest.fail("separate validation called before pinned fetch"),
    )
    monkeypatch.setattr(admin, "db", database)
    monkeypatch.setattr(admin._imgq, "get_suggestion", lambda _id: copy.deepcopy(suggestion))
    monkeypatch.setattr(
        admin._imgq,
        "mark_status",
        lambda *args, **kwargs: status_changes.append((args, kwargs)),
    )
    monkeypatch.setattr(admin, "_sync_kb", lambda: None)
    monkeypatch.setattr(
        admin._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(content=b"image"),
    )
    monkeypatch.setattr(storage, "MAX_IMAGE_SIZE", 1024)
    monkeypatch.setattr(
        storage.storage,
        "upload_image_set",
        lambda *_args: {"md": "/img/entities/entity-1.webp"},
    )

    result = asyncio.run(admin.approve_image_suggestion("suggestion-1"))
    saved_credit = database.upserts[0]["attributes"]["image_credits"][-1]
    assert result["credits"]["source_url"] == candidate_url
    assert saved_credit["source_url"] == candidate_url
    assert status_changes == [
        (("suggestion-1", "approved"), {"approved_by": "admin"}),
    ]
