"""Tests for admin Pydantic models and validation (agent/admin.py)."""
import asyncio
import pytest
from pydantic import ValidationError
from starlette.requests import Request

import admin as admin_module
from admin import EntityCreate, EntityUpdate, _sanitize, VALID_TYPES


def make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/admin", "headers": raw_headers, "client": ("127.0.0.1", 12345)})


# ── EntityCreate ──

def test_entity_create_valid():
    entity = EntityCreate(
        id="test-entity",
        type="product",
        name="Bưởi Năm Roi",
        summary="Đặc sản Vĩnh Long",
    )
    assert entity.id == "test-entity"
    assert entity.type == "product"
    assert entity.name == "Bưởi Năm Roi"


def test_entity_create_invalid_id():
    with pytest.raises(ValidationError):
        EntityCreate(
            id="INVALID ID!",
            type="product",
            name="Test",
        )


def test_entity_create_invalid_type():
    with pytest.raises(ValidationError):
        EntityCreate(
            id="test-entity",
            type="fake",
            name="Test",
        )


def test_entity_create_sanitize_name():
    entity = EntityCreate(
        id="test-entity",
        type="product",
        name="<script>alert('xss')</script>Bưởi",
    )
    # The name should have <script> tags escaped/sanitized
    assert "<script>" not in entity.name
    assert "Bưởi" in entity.name


# ── EntityUpdate ──

def test_entity_update_valid():
    update = EntityUpdate(name="Updated Name")
    assert update.name == "Updated Name"
    assert update.type is None
    assert update.summary is None


# ── Season validation ──

def test_season_validation_valid():
    entity = EntityCreate(
        id="seasonal-test",
        type="product",
        name="Test",
        season={"months": [1, 2, 3], "peak": [2]},
    )
    assert entity.season == {"months": [1, 2, 3], "peak": [2]}


def test_season_validation_invalid():
    with pytest.raises(ValidationError):
        EntityCreate(
            id="seasonal-test",
            type="product",
            name="Test",
            season={"months": [13]},
        )


def test_season_validation_invalid_peak():
    with pytest.raises(ValidationError):
        EntityCreate(
            id="seasonal-test",
            type="product",
            name="Test",
            season={"months": [1, 2], "peak": [15]},
        )


# ── _sanitize ──

def test_sanitize_function():
    result = _sanitize("<script>alert('xss')</script>hello")
    assert "<script>" not in result
    assert "hello" in result


def test_sanitize_preserves_normal_text():
    result = _sanitize("Bưởi Năm Roi đặc sản")
    assert "Bưởi Năm Roi đặc sản" in result


def test_sanitize_html_entities():
    result = _sanitize("A & B < C > D")
    # html.escape will convert & < > to entities
    assert "&amp;" in result
    assert "&lt;" in result
    assert "&gt;" in result


# ── VALID_TYPES ──

def test_valid_types_set():
    assert "product" in VALID_TYPES
    assert "experience" in VALID_TYPES
    assert "dish" in VALID_TYPES
    assert "attraction" in VALID_TYPES
    assert "fake_type" not in VALID_TYPES


def test_require_admin_accepts_admin_key() -> None:
    from middleware import ADMIN_API_KEY

    request = make_request({"X-Admin-Key": ADMIN_API_KEY})

    assert asyncio.run(admin_module.require_admin(request)) is None


def test_require_admin_accepts_admin_session(monkeypatch) -> None:
    async def fake_current_user(_request):
        return {"id": "u1", "role": "admin"}

    monkeypatch.setattr(admin_module, "get_current_user", fake_current_user)
    request = make_request({"Authorization": "Bearer admin-token"})

    assert asyncio.run(admin_module.require_admin(request)) is None
