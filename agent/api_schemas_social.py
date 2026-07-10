# -*- coding: utf-8 -*-
"""Pydantic response models cho social.py (UGC PG-only, SP3 W6.3-social).

Chiến lược AN TOÀN chống field-strip + chống prod-500 (endpoint 503 local nên
KHÔNG verify được bằng cách gọi thật → phải suy shape từ return-statement):

- Base `ApiModel` (api_schemas.py) đặt `extra="allow"` → FastAPI GIỮ NGUYÊN mọi
  field trả về (kể cả field không khai) → KHÔNG BAO GIỜ strip → FE luôn nhận đủ.
- CHỈ khai top-level field mà return-statement cho thấy kiểu CHẮC CHẮN:
    * `"posts": [...]` / list comprehension  → `list = []`
    * `"total": len(x)` / COUNT(*)            → `int | None = None`
    * `"has_more": <so-sanh>`                 → `bool | None = None`
    * `"q": _strip_html_tags(...)` (luôn str) → `str | None = None`
    * `"user": {...}` (nested dict)           → `dict | None = None`
- Field mơ hồ / biến-kiểu / nested-list-of-dict item-shape → KHÔNG khai
  (extra="allow" mang qua NGUYÊN KIỂU, tránh 500 ResponseValidation trên prod).

Không endpoint GET nào của social.py trả bare-list/Response/scalar → tất cả là
model dạng dict (không cần list[ItemModel]).
"""
from __future__ import annotations

from api_schemas import ApiModel


# ── Drafts / scheduled ───────────────────────────────────────────────
class DraftsListResponse(ApiModel):
    drafts: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


class ScheduledListResponse(ApiModel):
    scheduled: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


# ── Single post / edit history ───────────────────────────────────────
class PostResponse(ApiModel):
    # {"post": {...}} — post là dict nested (biến field theo enrich) → chỉ khai key.
    post: dict | None = None


class EditHistoryResponse(ApiModel):
    edits: list = []
    total: int | None = None


# ── Feeds (posts list + phân trang) ──────────────────────────────────
class FeedResponse(ApiModel):
    posts: list = []
    page: int | None = None
    total: int | None = None
    has_more: bool | None = None


class FollowingFeedResponse(ApiModel):
    posts: list = []
    page: int | None = None
    total: int | None = None
    has_more: bool | None = None


class FriendReviewsResponse(ApiModel):
    reviews: list = []


class FriendSavesResponse(ApiModel):
    saves: list = []


class TrendingPostsResponse(ApiModel):
    posts: list = []
    total: int | None = None
    has_more: bool | None = None
    window: str | None = None
    days: int | None = None


class ExploreFeedResponse(ApiModel):
    posts: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


# ── Search ───────────────────────────────────────────────────────────
class SearchPostsResponse(ApiModel):
    posts: list = []
    q: str | None = None
    page: int | None = None
    total: int | None = None
    has_more: bool | None = None


class SearchUsersResponse(ApiModel):
    users: list = []
    q: str | None = None
    page: int | None = None
    total: int | None = None
    has_more: bool | None = None


# ── Community stats / user counts ────────────────────────────────────
class CommunityStatsResponse(ApiModel):
    posts: int | None = None
    reviews: int | None = None
    members: int | None = None


class UserCountsResponse(ApiModel):
    unread_notifications: int | None = None
    posts: int | None = None
    drafts: int | None = None
    bookmarks: int | None = None
    visits: int | None = None


class UserStatsResponse(ApiModel):
    # avg_rating là float; reputation là int; còn lại int. Chỉ khai kiểu chắc chắn.
    reviews: int | None = None
    avg_rating: float | None = None
    questions: int | None = None
    followers: int | None = None
    following: int | None = None
    likes_received: int | None = None
    reactions_received: int | None = None
    entities_reviewed: int | None = None
    collections: int | None = None
    reputation: int | None = None


class UserActivityResponse(ApiModel):
    activities: list = []


# ── Hashtags / trending tags ─────────────────────────────────────────
class TrendingTagsResponse(ApiModel):
    tags: list = []
    period: str | None = None
    days: int | None = None


class HashtagsListResponse(ApiModel):
    hashtags: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


class HashtagPostsResponse(ApiModel):
    tag: str | None = None
    posts: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


# ── Leaderboard / follows / suggestions ──────────────────────────────
class LeaderboardResponse(ApiModel):
    # {"leaders": [...], "self": None|dict} — self biến-kiểu → không khai, để pass-through.
    leaders: list = []


class FollowUsersResponse(ApiModel):
    # /users/{id}/following + /followers dùng chung shape.
    users: list = []
    total: int | None = None
    offset: int | None = None
    has_more: bool | None = None


class SuggestedFollowsResponse(ApiModel):
    users: list = []


# ── Entity feed ──────────────────────────────────────────────────────
class EntityFeedResponse(ApiModel):
    # entity + rating là dict nested → chỉ khai key; posts=list; total=int.
    entity: dict | None = None
    rating: dict | None = None
    posts: list = []
    total: int | None = None


# ── Related posts / comments ─────────────────────────────────────────
class RelatedPostsResponse(ApiModel):
    posts: list = []


class CommentsResponse(ApiModel):
    comments: list = []


# ── Appeal ───────────────────────────────────────────────────────────
class AppealStatusResponse(ApiModel):
    # {"appeal": None} hoặc {"appeal": {...}} → dict|None.
    appeal: dict | None = None


# ── Likers / reactions ───────────────────────────────────────────────
class LikersResponse(ApiModel):
    likers: list = []
    total: int | None = None
    has_more: bool | None = None


class ReactionsResponse(ApiModel):
    # reactions là dict map reaction_type->count; total là int.
    reactions: dict | None = None
    total: int | None = None


# ── Bookmarks / collections ──────────────────────────────────────────
class BookmarksResponse(ApiModel):
    posts: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


class CollectionsListResponse(ApiModel):
    collections: list = []


class CollectionItemsResponse(ApiModel):
    posts: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


# ── Hidden posts ─────────────────────────────────────────────────────
class HiddenPostsResponse(ApiModel):
    posts: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


# ── Badge progress ───────────────────────────────────────────────────
class BadgeProgressResponse(ApiModel):
    badges: list = []


# ── User profile / posts / reviews / timeline / heatmap ──────────────
class UserProfileResponse(ApiModel):
    # {"user": {...}} — user là dict lớn biến-shape theo privacy → chỉ khai key.
    user: dict | None = None


class UserPostsResponse(ApiModel):
    posts: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


class UserReviewsResponse(ApiModel):
    reviews: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


class UserTimelineResponse(ApiModel):
    items: list = []
    total: int | None = None
    page: int | None = None
    has_more: bool | None = None


class ActivityHeatmapResponse(ApiModel):
    days: list = []
    total: int | None = None
    max: int | None = None
