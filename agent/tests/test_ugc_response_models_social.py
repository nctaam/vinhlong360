# -*- coding: utf-8 -*-
"""SP3 W6.3-social — response_model AN TOÀN cho GET endpoint của social.py.

Vì social.py là UGC PG-only → 503 khi không có Postgres local → KHÔNG gọi
endpoint verify được. Thay bằng SHAPE-CONTRACT test:

1. Với MỖI model: dựng payload KHỚP return-statement của endpoint (kèm field
   KHÔNG khai) → `Model.model_validate(payload)` KHÔNG raise + field không-khai
   VẪN CÒN trong model_dump() → chứng minh no-strip (extra="allow") + no-500.
2. 503-still-works: mount router vào app SQLite → GET vài endpoint → 503 (KHÔNG
   500) → model không phá path guard.
3. Mọi GET route có response_model kế ApiModel.
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_schemas_social as S  # noqa: E402
from api_schemas import ApiModel  # noqa: E402
import social  # noqa: E402


# ── Payload mẫu (khớp return-statement; kèm field KHÔNG khai để test pass-through) ──
# Mỗi tuple: (Model, payload). Payload luôn thêm field lạ ("__extra__" / item field
# không khai) để chứng minh extra="allow" mang qua nguyên vẹn.

_POST_ITEM = {"id": "p1", "content": "hi", "like_count": 3, "author": {"id": "u1"}}
_USER_ITEM = {"id": "u1", "display_name": "An", "avatar_url": None, "username": "an"}

CASES = [
    (S.DraftsListResponse, {"drafts": [{"id": "d1", "content": "x"}], "total": 1, "page": 1, "has_more": False}),
    (S.ScheduledListResponse, {"scheduled": [{"id": "s1"}], "total": 1, "page": 1, "has_more": False}),
    (S.PostResponse, {"post": _POST_ITEM}),
    (S.EditHistoryResponse, {"edits": [{"id": "e1", "old_content": "a"}], "total": 1}),
    (S.FeedResponse, {"posts": [_POST_ITEM], "page": 1, "total": 5, "has_more": True}),
    (S.FollowingFeedResponse, {"posts": [_POST_ITEM], "page": 1, "total": 2, "has_more": False}),
    (S.FriendReviewsResponse, {"reviews": [{"id": "r1", "rating": 5, "user": {"display_name": "An"}}]}),
    (S.FriendSavesResponse, {"saves": [{"entity_id": "e1", "entity_name": "X", "user": {"display_name": "An"}}]}),
    (S.TrendingPostsResponse, {"posts": [_POST_ITEM], "total": 3, "has_more": False, "window": "7d", "days": 7}),
    (S.ExploreFeedResponse, {"posts": [_POST_ITEM], "total": 3, "page": 1, "has_more": True}),
    (S.SearchPostsResponse, {"posts": [_POST_ITEM], "q": "cam", "page": 1, "total": 1, "has_more": False}),
    (S.SearchUsersResponse, {"users": [{**_USER_ITEM, "post_count": 4}], "q": "an", "page": 1, "total": 1, "has_more": False}),
    (S.CommunityStatsResponse, {"posts": 100, "reviews": 40, "members": 12}),
    (S.UserCountsResponse, {"unread_notifications": 2, "posts": 5, "drafts": 1, "bookmarks": 3, "visits": 7}),
    (S.UserStatsResponse, {"reviews": 5, "avg_rating": 4.25, "questions": 1, "followers": 3, "following": 2,
                           "likes_received": 10, "reactions_received": 4, "entities_reviewed": 3,
                           "collections": 1, "reputation": 42}),
    (S.UserActivityResponse, {"activities": [{"action": "post", "ref_id": "p1", "created_at": "2026-01-01"}]}),
    (S.TrendingTagsResponse, {"tags": [{"tag": "amthuc", "count": 9}], "period": "30d", "days": 30}),
    (S.HashtagsListResponse, {"hashtags": [{"tag": "amthuc", "post_count": 9}], "total": 1, "page": 1, "has_more": False}),
    (S.HashtagPostsResponse, {"tag": "amthuc", "posts": [_POST_ITEM], "total": 1, "page": 1, "has_more": False}),
    # leaderboard: self có thể None hoặc dict — cả 2 phải pass (self KHÔNG khai).
    (S.LeaderboardResponse, {"leaders": [{"id": "u1", "points": 100, "rank": 1}], "self": None}),
    (S.LeaderboardResponse, {"leaders": [{"id": "u1", "points": 100, "rank": 1}],
                             "self": {"id": "u2", "points": 5, "rank": 9}}),
    (S.FollowUsersResponse, {"users": [_USER_ITEM], "total": 1, "offset": 0, "has_more": False}),
    (S.SuggestedFollowsResponse, {"users": [{**_USER_ITEM, "points": 30, "posts": 5}]}),
    (S.EntityFeedResponse, {"entity": {"id": "e1", "name": "X", "type": "place", "summary": ""},
                            "rating": {"avg": 4.5, "count": 3}, "posts": [_POST_ITEM], "total": 3}),
    (S.RelatedPostsResponse, {"posts": [_POST_ITEM]}),
    (S.CommentsResponse, {"comments": [{"id": "c1", "content": "hi", "replies": [], "author": {"id": "u1"}}]}),
    # appeal: None hoặc dict — cả 2 nhánh.
    (S.AppealStatusResponse, {"appeal": None}),
    (S.AppealStatusResponse, {"appeal": {"id": "a1", "status": "pending", "reviewer_note": None,
                                         "reviewed_at": None, "created_at": "2026-01-01"}}),
    (S.LikersResponse, {"likers": [{**_USER_ITEM, "liked_at": "2026-01-01"}], "total": 1, "has_more": False}),
    (S.ReactionsResponse, {"reactions": {"heart": 3, "funny": 1}, "total": 4}),
    (S.BookmarksResponse, {"posts": [_POST_ITEM], "total": 1, "page": 1, "has_more": False}),
    (S.CollectionsListResponse, {"collections": [{"id": "col1", "name": "N", "item_count": 2}]}),
    (S.CollectionItemsResponse, {"posts": [_POST_ITEM], "total": 1, "page": 1, "has_more": False}),
    (S.HiddenPostsResponse, {"posts": [_POST_ITEM], "total": 1, "page": 1, "has_more": False}),
    (S.BadgeProgressResponse, {"badges": [{"id": "first_review", "current": 1, "target": 1, "earned": True}]}),
    (S.UserProfileResponse, {"user": {"id": "u1", "display_name": "An", "stats": {"posts": 5},
                                      "reputation": {"points": 10}, "viewer_relationship": {"is_self": True}}}),
    (S.UserPostsResponse, {"posts": [_POST_ITEM], "total": 1, "page": 1, "has_more": False}),
    (S.UserReviewsResponse, {"reviews": [_POST_ITEM], "total": 1, "page": 1, "has_more": False}),
    (S.UserTimelineResponse, {"items": [{"type": "post", "created_at": "2026-01-01", "data": {"id": "p1"}}],
                              "total": 1, "page": 1, "has_more": False}),
    (S.ActivityHeatmapResponse, {"days": [{"date": "2026-01-01", "count": 2}], "total": 2, "max": 2}),
]


@pytest.mark.parametrize("model,payload", CASES)
def test_model_validates_and_preserves_declared_fields(model, payload):
    """Payload khớp return-statement → validate KHÔNG raise; field khai còn nguyên."""
    m = model.model_validate(payload)
    dumped = m.model_dump()
    for k in payload:
        assert k in dumped, f"{model.__name__}: field khai '{k}' bị mất"


@pytest.mark.parametrize("model,payload", CASES)
def test_model_no_strip_of_undeclared_fields(model, payload):
    """Thêm field KHÔNG khai (item + top-level) → phải pass-through nhờ extra=allow."""
    enriched = dict(payload)
    enriched["__surprise_top__"] = {"nested": [1, 2, 3]}
    m = model.model_validate(enriched)
    dumped = m.model_dump()
    assert dumped.get("__surprise_top__") == {"nested": [1, 2, 3]}, \
        f"{model.__name__}: field top-level không-khai bị STRIP → FE vỡ"


def test_all_models_subclass_apimodel():
    for model, _ in CASES:
        assert issubclass(model, ApiModel), f"{model.__name__} phải kế ApiModel (extra=allow)"
    assert ApiModel.model_config.get("extra") == "allow"


# ── 503-still-works: model KHÔNG phá path guard (router-level require_pg) ──

def _client():
    app = FastAPI()
    app.include_router(social.router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("path", [
    "/api/feed",
    "/api/community/stats",
    "/api/posts/hidden",
    "/api/community/trending-tags",
])
def test_get_endpoints_return_503_not_500_on_sqlite(path):
    """SQLite (không PG) → router guard trả 503 TRƯỚC handler. Model không được
    biến nó thành 500. Chấp nhận 200/503, CẤM 500."""
    r = _client().get(path)
    assert r.status_code != 500, f"{path} → 500 (model phá path?)"
    assert r.status_code in (200, 503, 422), f"{path} → {r.status_code} bất ngờ"


def test_every_get_route_has_apimodel_response_model():
    for r in social.router.routes:
        methods = getattr(r, "methods", set()) or set()
        if "GET" not in methods:
            continue
        rm = getattr(r, "response_model", None)
        assert rm is not None, f"{getattr(r, 'path', '?')} thiếu response_model"
        assert issubclass(rm, ApiModel), \
            f"{getattr(r, 'path', '?')} response_model phải kế ApiModel"
