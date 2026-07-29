"""Server-derived ownership for chat conversations and long-term memory."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from fastapi import Request, Response


CHAT_OWNER_COOKIE = "vl360_chat_owner"
_IS_PRODUCTION = os.environ.get("ENVIRONMENT", "development").strip().lower() in {
    "production",
    "prod",
    "prd",
}

_secret = os.environ.get("CHAT_OWNER_SECRET") or os.environ.get("CSRF_SECRET")
if not _secret:
    if _IS_PRODUCTION:
        raise RuntimeError("CHAT_OWNER_SECRET or CSRF_SECRET is required in production")
    _secret = secrets.token_hex(32)
_CHAT_OWNER_SECRET = _secret.encode("utf-8")


async def _get_current_user_or_none(request: Request) -> dict | None:
    from auth import _get_current_user_or_none as get_current_user

    return await get_current_user(request)


@dataclass(frozen=True)
class ChatOwnerContext:
    owner_key: str
    cookie_value: str | None = None


def _sign_visitor_id(visitor_id: str) -> str:
    return hmac.new(
        _CHAT_OWNER_SECRET,
        visitor_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def owner_binding_digest(owner_key: str) -> str:
    """Create a domain-separated one-way binding for a resolved chat owner."""
    if not isinstance(owner_key, str) or not owner_key:
        raise ValueError("INVALID_CHAT_OWNER")
    payload = b"feedback-owner-binding:v1\x00" + owner_key.encode("utf-8")
    return hmac.new(_CHAT_OWNER_SECRET, payload, hashlib.sha256).hexdigest()


def _anonymous_context(visitor_id: str, *, issue_cookie: bool) -> ChatOwnerContext:
    owner_digest = hashlib.sha256(visitor_id.encode("utf-8")).hexdigest()
    cookie_value = f"{visitor_id}.{_sign_visitor_id(visitor_id)}" if issue_cookie else None
    return ChatOwnerContext(owner_key=f"anon:{owner_digest}", cookie_value=cookie_value)


def resolve_anonymous_owner(cookie_value: str | None) -> ChatOwnerContext:
    """Validate an anonymous owner cookie, rotating invalid or missing values."""
    if cookie_value and len(cookie_value) <= 512:
        try:
            visitor_id, signature = cookie_value.rsplit(".", 1)
        except ValueError:
            visitor_id = signature = ""
        if visitor_id and hmac.compare_digest(signature, _sign_visitor_id(visitor_id)):
            return _anonymous_context(visitor_id, issue_cookie=False)

    return _anonymous_context(secrets.token_urlsafe(32), issue_cookie=True)


async def resolve_chat_owner(request: Request) -> ChatOwnerContext:
    """Resolve ownership from validated auth, falling back to a signed visitor cookie."""
    user = await _get_current_user_or_none(request)
    if user is not None:
        return ChatOwnerContext(owner_key=f"user:{user['id']}")
    return resolve_anonymous_owner(request.cookies.get(CHAT_OWNER_COOKIE))


def set_chat_owner_cookie(response: Response, context: ChatOwnerContext) -> None:
    """Attach a newly issued anonymous owner cookie to a response."""
    if context.cookie_value is None:
        return
    response.set_cookie(
        key=CHAT_OWNER_COOKIE,
        value=context.cookie_value,
        max_age=60 * 60 * 24 * 365,
        path="/",
        httponly=True,
        secure=_IS_PRODUCTION,
        samesite="lax",
    )
