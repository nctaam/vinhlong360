"""Stable cross-module contract for community read helpers.

The route module keeps its implementation-private helpers private.  Consumers
outside ``community.api`` import this facade instead, so a future route split
does not turn private names into an accidental application-wide API.
"""

from __future__ import annotations

from . import api as _api


# Keep the SQL projection and helper behavior defined in one implementation
# module while exposing a stable, non-private vocabulary to other domains.
POST_COLS = _api._POST_COLS


def block_sql(user: dict | None, column: str = "u.id") -> tuple[str, list]:
    return _api._block_sql(user, column)


def mute_sql(user: dict | None, column: str = "p.user_id") -> tuple[str, list]:
    return _api._mute_sql(user, column)


def prod_seed_post_filter(alias: str = "p") -> tuple[str, list]:
    return _api._prod_seed_post_filter(alias)


def format_post(row: dict) -> dict:
    return _api._format_post(row)


def enrich_all(posts: list[dict], user: dict | None) -> list[dict]:
    return _api._enrich_all(posts, user)


# Preserve handler/helper identity for legacy introspection while the contract
# module provides the stable import path.  The implementation accepts both
# positional and keyword calls (see the signature in ``community.api``).
collect_new_entities = _api._collect_new_entities


# Route identity is intentionally preserved for FastAPI registration and old
# callers that compare the exported handler object.
feed_new_since = _api.feed_new_since


def is_blocked(user_id: str, target_id: str) -> bool:
    """Return whether either side of a user relationship is blocked."""
    from database import db

    if not user_id or not target_id or not db._use_pg:
        return False
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(
            conn,
            f"""
            SELECT 1
            FROM blocks
            WHERE (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
               OR (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
            LIMIT 1
            """,
            (str(user_id), str(target_id), str(target_id), str(user_id)),
        )
    return row is not None


__all__ = [
    "POST_COLS",
    "block_sql",
    "mute_sql",
    "prod_seed_post_filter",
    "format_post",
    "enrich_all",
    "collect_new_entities",
    "feed_new_since",
    "is_blocked",
]
