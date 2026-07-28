import asyncio
import uuid
from contextlib import contextmanager

import pytest
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.testclient import TestClient

import public_api
import social
from auth_middleware import get_current_user, require_user
from database import db
from profile_access import (
    ProfileAccessDecision,
    can_view_profile_audience,
    resolve_profile_access,
)


pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="Friend-saves behavior requires PostgreSQL UGC tables.",
)

USER_ID = "11111111-1111-1111-1111-111111111111"
VIEWER_ID = "22222222-2222-2222-2222-222222222222"

HIDDEN_ENGAGEMENT = {
    "user_id": USER_ID,
    "total_posts": 0,
    "total_reviews": 0,
    "avg_rating": 0.0,
    "total_questions": 0,
    "entities_reviewed": 0,
    "followers": 0,
    "total_likes_received": 0,
}


@contextmanager
def _fake_conn():
    yield object()


def _request(_user=None):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
    )


def _unexpected_query(*_args, **_kwargs):
    raise AssertionError("profile section queried data after access was denied")


def _stub_profile_decision(
    monkeypatch,
    module,
    decision,
    *,
    viewer_id,
    require_activity,
):
    expected_require_activity = require_activity

    def _resolve(_conn, target_id, actual_viewer_id, *, require_activity: bool):
        assert target_id == USER_ID
        assert actual_viewer_id == viewer_id
        assert require_activity is expected_require_activity
        return decision

    monkeypatch.setattr(module, "resolve_profile_access", _resolve, raising=False)


def _deny_data_queries(monkeypatch, module):
    monkeypatch.setattr(module.db, "_conn", _fake_conn)
    monkeypatch.setattr(module.db, "_fetchone", _unexpected_query)
    monkeypatch.setattr(module.db, "_fetchall", _unexpected_query)


class _FetchSequence:
    def __init__(self, *rows):
        self._rows = list(rows)
        self.calls = []

    def __call__(self, _conn, sql, params):
        self.calls.append((sql, params))
        if not self._rows:
            raise AssertionError("unexpected profile access query")
        return self._rows.pop(0)

    def assert_consumed(self):
        assert self._rows == []


@pytest.mark.parametrize(
    ("visibility", "is_self", "is_follower", "expected"),
    [
        ("public", False, False, True),
        ("followers", False, False, False),
        ("followers", False, True, True),
        ("followers_only", False, True, True),
        ("private", False, True, True),
        ("private", False, False, False),
        ("unknown", False, False, False),
        ("public", True, False, True),
    ],
)
def test_profile_access_audience_matrix(
    visibility, is_self, is_follower, expected
):
    assert can_view_profile_audience(visibility, is_self, is_follower) is expected


@pytest.mark.parametrize("filtered_target", ["inactive", "deleted"])
def test_resolve_profile_access_returns_not_found_for_filtered_target(
    monkeypatch, filtered_target
):
    fetch = _FetchSequence(None)
    monkeypatch.setattr("profile_access.db._fetchone", fetch)

    decision = resolve_profile_access(
        object(), "target-1", "viewer-1", require_activity=False
    )

    assert decision.status == "not_found", filtered_target
    assert decision.target_id is None
    assert decision.is_self is False
    assert decision.can_view_activity is False
    fetch.assert_consumed()


def test_resolve_profile_access_hides_bidirectional_block(monkeypatch):
    fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": "public",
            "show_activity": True,
        },
        {"blocked": 1},
    )
    monkeypatch.setattr("profile_access.db._fetchone", fetch)
    monkeypatch.setattr("profile_access.db._row_to_dict", lambda row: row)

    decision = resolve_profile_access(
        object(), "target-1", "viewer-1", require_activity=False
    )

    assert decision.status == "hidden"
    assert decision.target_id == "target-1"
    assert fetch.calls[1][1] == (
        "viewer-1",
        "target-1",
        "target-1",
        "viewer-1",
    )
    fetch.assert_consumed()


@pytest.mark.parametrize(
    ("visibility", "follower_row"),
    [
        ("followers", None),
        ("unknown", {"follows": 1}),
    ],
)
def test_resolve_profile_access_hides_unauthorized_audience(
    monkeypatch, visibility, follower_row
):
    fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": visibility,
            "show_activity": True,
        },
        None,
        follower_row,
    )
    monkeypatch.setattr("profile_access.db._fetchone", fetch)
    monkeypatch.setattr("profile_access.db._row_to_dict", lambda row: row)

    decision = resolve_profile_access(
        object(), "target-1", "viewer-1", require_activity=False
    )

    assert decision.status == "hidden"
    assert decision.target_id == "target-1"
    fetch.assert_consumed()


@pytest.mark.parametrize("show_activity", [False, None])
def test_resolve_profile_access_requires_explicit_activity_permission(
    monkeypatch, show_activity
):
    fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": "public",
            "show_activity": show_activity,
        },
        None,
    )
    monkeypatch.setattr("profile_access.db._fetchone", fetch)
    monkeypatch.setattr("profile_access.db._row_to_dict", lambda row: row)

    decision = resolve_profile_access(
        object(), "target-1", "viewer-1", require_activity=True
    )

    assert decision.status == "hidden"
    assert decision.can_view_activity is False
    fetch.assert_consumed()


def test_resolve_profile_access_allows_self_without_relationship_queries(monkeypatch):
    fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": None,
            "show_activity": None,
        }
    )
    monkeypatch.setattr("profile_access.db._fetchone", fetch)
    monkeypatch.setattr("profile_access.db._row_to_dict", lambda row: row)

    decision = resolve_profile_access(
        object(), "target-1", "target-1", require_activity=True
    )

    assert decision.status == "ok"
    assert decision.target_id == "target-1"
    assert decision.is_self is True
    assert decision.can_view_activity is True
    assert len(fetch.calls) == 1
    fetch.assert_consumed()


def test_resolve_profile_access_allows_authorized_follower_activity(monkeypatch):
    fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": "followers",
            "show_activity": True,
        },
        None,
        {"follows": 1},
    )
    monkeypatch.setattr("profile_access.db._fetchone", fetch)
    monkeypatch.setattr("profile_access.db._row_to_dict", lambda row: row)

    decision = resolve_profile_access(
        object(), "target-1", "viewer-1", require_activity=True
    )

    assert decision.status == "ok"
    assert decision.target_id == "target-1"
    assert decision.is_self is False
    assert decision.can_view_activity is True
    fetch.assert_consumed()


def test_missing_privacy_defaults_to_follower_relationships_without_activity(
    monkeypatch,
):
    anonymous_fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": None,
            "show_activity": None,
        }
    )
    monkeypatch.setattr("profile_access.db._fetchone", anonymous_fetch)
    monkeypatch.setattr("profile_access.db._row_to_dict", lambda row: row)

    anonymous = resolve_profile_access(
        object(), "target-1", None, require_activity=False
    )

    assert anonymous.status == "hidden"
    anonymous_fetch.assert_consumed()

    follower_fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": None,
            "show_activity": None,
        },
        None,
        {"follows": 1},
    )
    monkeypatch.setattr("profile_access.db._fetchone", follower_fetch)

    relationships = resolve_profile_access(
        object(), "target-1", "viewer-1", require_activity=False
    )

    assert relationships.status == "ok"
    assert relationships.can_view_activity is False
    follower_fetch.assert_consumed()

    activity_fetch = _FetchSequence(
        {
            "id": "target-1",
            "profile_visibility": None,
            "show_activity": None,
        },
        None,
        {"follows": 1},
    )
    monkeypatch.setattr("profile_access.db._fetchone", activity_fetch)

    activity = resolve_profile_access(
        object(), "target-1", "viewer-1", require_activity=True
    )

    assert activity.status == "hidden"
    assert activity.can_view_activity is False
    activity_fetch.assert_consumed()


def test_hidden_user_posts_returns_existing_empty_shape(monkeypatch):
    monkeypatch.setattr(social, "_resolve_user_id", lambda _user_id: USER_ID)
    monkeypatch.setattr(social, "_check_show_activity", lambda *_args: False)
    _stub_profile_decision(
        monkeypatch,
        social,
        ProfileAccessDecision("hidden", USER_ID),
        viewer_id=None,
        require_activity=True,
    )
    _deny_data_queries(monkeypatch, social)

    result = asyncio.run(
        social.get_user_posts(USER_ID, _request(None), page=2, limit=20)
    )

    assert result == {"posts": [], "total": 0, "page": 2, "has_more": False}


def test_hidden_user_reviews_returns_existing_empty_shape(monkeypatch):
    monkeypatch.setattr(social, "_resolve_user_id", lambda _user_id: USER_ID)
    monkeypatch.setattr(social, "_check_show_activity", lambda *_args: False)
    _stub_profile_decision(
        monkeypatch,
        social,
        ProfileAccessDecision("hidden", USER_ID),
        viewer_id=None,
        require_activity=True,
    )
    _deny_data_queries(monkeypatch, social)

    result = asyncio.run(
        social.get_user_reviews(USER_ID, _request(None), page=3, limit=20)
    )

    assert result == {"reviews": [], "total": 0, "page": 3, "has_more": False}


def test_hidden_following_returns_existing_empty_shape(monkeypatch):
    monkeypatch.setattr(social, "_resolve_user_id", lambda _user_id: USER_ID)
    _stub_profile_decision(
        monkeypatch,
        social,
        ProfileAccessDecision("hidden", USER_ID),
        viewer_id=None,
        require_activity=False,
    )
    _deny_data_queries(monkeypatch, social)

    result = asyncio.run(
        social.list_following_users(USER_ID, limit=25, offset=50, user=None)
    )

    assert result == {"users": [], "total": 0, "offset": 50, "has_more": False}


def test_hidden_followers_returns_existing_empty_shape(monkeypatch):
    monkeypatch.setattr(social, "_resolve_user_id", lambda _user_id: USER_ID)
    _stub_profile_decision(
        monkeypatch,
        social,
        ProfileAccessDecision("hidden", USER_ID),
        viewer_id=None,
        require_activity=False,
    )
    _deny_data_queries(monkeypatch, social)

    result = asyncio.run(
        social.list_followers(USER_ID, limit=25, offset=75, user=None)
    )

    assert result == {"users": [], "total": 0, "offset": 75, "has_more": False}


def test_hidden_activity_heatmap_returns_existing_empty_shape(monkeypatch):
    _stub_profile_decision(
        monkeypatch,
        social,
        ProfileAccessDecision("hidden", USER_ID),
        viewer_id=None,
        require_activity=True,
    )
    _deny_data_queries(monkeypatch, social)

    result = asyncio.run(social.get_activity_heatmap(USER_ID, user=None))

    assert result == {"days": [], "total": 0, "max": 0}


def test_anonymous_hidden_engagement_returns_zero_shape(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    _stub_profile_decision(
        monkeypatch,
        public_api,
        ProfileAccessDecision("hidden", USER_ID),
        viewer_id=None,
        require_activity=True,
    )
    _deny_data_queries(monkeypatch, public_api)

    result = asyncio.run(
        public_api.user_engagement_stats(
            USER_ID,
            request=_request(None),
            response=Response(),
            user=None,
        )
    )

    assert result == HIDDEN_ENGAGEMENT


def test_authorized_follower_engagement_returns_approved_stats(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    _stub_profile_decision(
        monkeypatch,
        public_api,
        ProfileAccessDecision("ok", USER_ID, False, True),
        viewer_id=VIEWER_ID,
        require_activity=True,
    )
    fetch = _FetchSequence(
        {
            "total_posts": 5,
            "total_reviews": 2,
            "avg_rating": 4.24,
            "total_questions": 1,
            "entities_reviewed": 2,
        },
        {"c": 3},
        {"total_likes": 9},
    )
    monkeypatch.setattr(public_api.db, "_conn", _fake_conn)
    monkeypatch.setattr(public_api.db, "_fetchone", fetch)
    monkeypatch.setattr(public_api.db, "_row_to_dict", lambda row: row)

    result = asyncio.run(
        public_api.user_engagement_stats(
            USER_ID,
            request=_request(VIEWER_ID),
            response=Response(),
            user={"id": VIEWER_ID},
        )
    )

    assert result == {
        "user_id": USER_ID,
        "total_posts": 5,
        "total_reviews": 2,
        "avg_rating": 4.2,
        "total_questions": 1,
        "entities_reviewed": 2,
        "followers": 3,
        "total_likes_received": 9,
    }
    stats_sql = " ".join(fetch.calls[0][0].split())
    assert "post_type = 'question' AND moderation_status = 'approved'" in stats_sql
    fetch.assert_consumed()


def test_blocked_viewer_engagement_returns_zero_shape(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    _stub_profile_decision(
        monkeypatch,
        public_api,
        ProfileAccessDecision("hidden", USER_ID),
        viewer_id=VIEWER_ID,
        require_activity=True,
    )
    _deny_data_queries(monkeypatch, public_api)

    result = asyncio.run(
        public_api.user_engagement_stats(
            USER_ID,
            request=_request(VIEWER_ID),
            response=Response(),
            user={"id": VIEWER_ID},
        )
    )

    assert result == HIDDEN_ENGAGEMENT


def test_missing_target_engagement_returns_404(monkeypatch):
    monkeypatch.setattr(public_api, "require_pg", lambda: None)
    _stub_profile_decision(
        monkeypatch,
        public_api,
        ProfileAccessDecision("not_found"),
        viewer_id=None,
        require_activity=True,
    )
    _deny_data_queries(monkeypatch, public_api)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            public_api.user_engagement_stats(
                USER_ID,
                request=_request(None),
                response=Response(),
                user=None,
            )
        )

    assert exc_info.value.status_code == 404


def test_get_user_profile_restricts_followers_visibility_for_nonfollower(monkeypatch):
    profile = {
        "id": "11111111-1111-1111-1111-111111111111",
        "username": "private-profile",
        "display_name": "Private Profile",
        "avatar_url": "/avatar.webp",
        "cover_url": "/cover.webp",
        "bio": "This bio must stay hidden.",
        "created_at": "2026-07-12T08:30:00+00:00",
        "login_streak": 9,
    }
    query_result = (
        "followers",
        profile,
        False,
        False,
        {"followers": 7},
        {"c": 4},
        12,
        3,
        {"show_activity": True, "show_saved": True},
        False,
        False,
        False,
    )
    monkeypatch.setattr(social, "_profile_query", lambda *_args: query_result)

    result = asyncio.run(social.get_user_profile(profile["id"], user=None))

    assert result["user"].get("is_private") is True
    assert result["user"]["bio"] == ""
    assert result["user"]["stats"]["posts"] == 0
    assert result["user"]["stats"]["reviews"] == 0
    assert result["user"]["reputation"] is None


@pytest.mark.parametrize(
    ("visibility", "is_self", "is_follower", "expected"),
    [
        ("public", False, False, True),
        ("followers", False, False, False),
        ("followers", False, True, True),
        ("followers_only", False, False, False),
        ("private", False, True, True),
        ("private", False, False, False),
        ("unknown", False, False, False),
        ("followers", True, False, True),
    ],
)
def test_profile_can_view_full_policy(
    visibility, is_self, is_follower, expected
):
    assert social._profile_can_view_full(visibility, is_self, is_follower) is expected


def test_friend_saves_enforces_owner_visibility_in_sql(monkeypatch):
    captured = {}
    row = {
        "entity_id": "entity-1",
        "name": "Cho Vinh Long",
        "entity_type": "market",
        "display_name": "Friend",
        "avatar_url": "/avatar.webp",
        "created_at": "2026-07-12T08:30:00+00:00",
    }

    def _fetchall(_conn, sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [row]

    monkeypatch.setattr(social.db, "_conn", _fake_conn)
    monkeypatch.setattr(social.db, "_fetchall", _fetchall)
    monkeypatch.setattr(social.db, "_row_to_dict", lambda value: value)

    result = asyncio.run(social.get_friend_saves(limit=5, user={"id": "viewer-1"}))

    assert (
        "LEFT JOIN user_privacy save_privacy ON save_privacy.user_id = s.user_id"
        in captured["sql"]
    )
    assert "COALESCE(save_privacy.show_saved, TRUE) = TRUE" in captured["sql"]
    assert captured["params"] == (
        "viewer-1",
        "viewer-1",
        "viewer-1",
        "viewer-1",
        5,
    )
    assert result == {
        "saves": [
            {
                "entity_id": "entity-1",
                "entity_name": "Cho Vinh Long",
                "entity_type": "market",
                "user": {
                    "display_name": "Friend",
                    "avatar_url": "/avatar.webp",
                },
                "created_at": "2026-07-12T08:30:00+00:00",
            }
        ]
    }


def _client_as(user):
    app = FastAPI()
    app.include_router(social.router)
    app.dependency_overrides[require_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


@pg_only
def test_friend_saves_respects_owner_visibility_in_postgres():
    suffix = uuid.uuid4().hex[:8]
    users = []
    entity_ids = []

    try:
        viewer = db.create_user(
            "09" + uuid.uuid4().hex[:8], display_name=f"Privacy Viewer {suffix}"
        )
        users.append(viewer)
        private_owner = db.create_user(
            "09" + uuid.uuid4().hex[:8], display_name=f"Private Owner {suffix}"
        )
        users.append(private_owner)
        public_owner = db.create_user(
            "09" + uuid.uuid4().hex[:8], display_name=f"Public Owner {suffix}"
        )
        users.append(public_owner)
        default_owner = db.create_user(
            "09" + uuid.uuid4().hex[:8], display_name=f"Default Owner {suffix}"
        )
        users.append(default_owner)

        private_entity = f"test-private-save-{suffix}"
        shared_entity = f"test-shared-save-{suffix}"
        default_entity = f"test-default-save-{suffix}"
        for entity_id, name in (
            (private_entity, "Private saved entity"),
            (shared_entity, "Shared saved entity"),
            (default_entity, "Default saved entity"),
        ):
            db.upsert_entity(
                {
                    "id": entity_id,
                    "name": f"{name} {suffix}",
                    "type": "place",
                    "summary": "Temporary entity for friend-saves privacy testing.",
                }
            )
            entity_ids.append(entity_id)

        ph = db._ph
        with db._conn() as conn:
            db._execute(
                conn,
                f"""
                INSERT INTO user_privacy
                    (user_id, profile_visibility, show_activity, show_saved)
                VALUES ({ph}::uuid, 'public', TRUE, FALSE),
                       ({ph}::uuid, 'public', TRUE, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET
                    profile_visibility = EXCLUDED.profile_visibility,
                    show_activity = EXCLUDED.show_activity,
                    show_saved = EXCLUDED.show_saved
                """,
                (str(private_owner["id"]), str(public_owner["id"])),
            )
            db._execute(
                conn,
                f"DELETE FROM user_privacy WHERE user_id = {ph}::uuid",
                (str(default_owner["id"]),),
            )
            for owner in (private_owner, public_owner, default_owner):
                db._execute(
                    conn,
                    f"""
                    INSERT INTO follows (follower_id, target_type, target_id)
                    VALUES ({ph}::uuid, 'user', {ph})
                    """,
                    (str(viewer["id"]), str(owner["id"])),
                )

            # Privacy must filter the private owner's newer shared save before DISTINCT ON.
            db._execute(
                conn,
                f"""
                INSERT INTO saved_entities
                    (user_id, entity_id, snapshot, created_at)
                VALUES
                    ({ph}::uuid, {ph}, '{{}}'::jsonb, NOW()),
                    ({ph}::uuid, {ph}, '{{}}'::jsonb, NOW()),
                    ({ph}::uuid, {ph}, '{{}}'::jsonb, NOW() - INTERVAL '1 day'),
                    ({ph}::uuid, {ph}, '{{}}'::jsonb, NOW() - INTERVAL '2 days')
                """,
                (
                    str(private_owner["id"]),
                    private_entity,
                    str(private_owner["id"]),
                    shared_entity,
                    str(public_owner["id"]),
                    shared_entity,
                    str(default_owner["id"]),
                    default_entity,
                ),
            )

        response = _client_as(viewer).get("/api/feed/friend-saves?limit=20")

        assert response.status_code == 200, response.text
        saves = response.json()["saves"]
        saves_by_entity = {save["entity_id"]: save for save in saves}
        assert private_entity not in saves_by_entity
        assert set(saves_by_entity) == {shared_entity, default_entity}
        assert saves_by_entity[shared_entity]["user"]["display_name"] == public_owner[
            "display_name"
        ]
        assert saves_by_entity[default_entity]["user"]["display_name"] == default_owner[
            "display_name"
        ]
    finally:
        with db._conn() as conn:
            if users:
                viewer_id = str(users[0]["id"])
                db._execute(
                    conn,
                    f"DELETE FROM follows WHERE follower_id = {db._ph}::uuid",
                    (viewer_id,),
                )
            for user in reversed(users):
                db._execute(
                    conn,
                    f"DELETE FROM users WHERE id::text = {db._ph}",
                    (str(user["id"]),),
                )
            for entity_id in entity_ids:
                db._execute(
                    conn,
                    f"DELETE FROM entities WHERE id = {db._ph}",
                    (entity_id,),
                )
