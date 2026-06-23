"""
vinhlong360 — Social API for local tourism & community.

MXH chuyên biệt: mọi bài viết/đánh giá gắn vào entity trong Knowledge Graph
(điểm du lịch, sản phẩm OCOP, làng nghề, ẩm thực, trải nghiệm, địa điểm).
UGC nuôi ngược lại graph → AI chatbot trích dẫn đánh giá cộng đồng.

Post types:
  - review    : Đánh giá (1-5 sao) địa điểm / sản phẩm / trải nghiệm
  - share     : Chia sẻ trải nghiệm du lịch, câu chuyện cộng đồng
  - recommend : Giới thiệu nông sản / sản phẩm địa phương
  - question  : Hỏi đáp du lịch, kinh nghiệm
"""

import json
import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from pydantic import BaseModel, field_validator

from auth_middleware import get_current_user, require_user
from database import db
from moderation import moderate_content, log_moderation
from notifications import create_notification
from storage import storage


def _require_pg():
    # GĐ3.1 (quyết định): UGC chạy Postgres. SQLite dev -> 503 rõ ràng.
    if not db._use_pg:
        raise HTTPException(503, detail="Tính năng cộng đồng (UGC) cần Postgres. Local dev: docker compose up postgres.")


router = APIRouter(prefix="/api", tags=["social"], dependencies=[Depends(_require_pg)])

# ── Models ──

POST_TYPES = ("review", "share", "recommend", "question")
ENTITY_LINK_REQUIRED = ("review",)  # These types must link to an entity


class CreatePost(BaseModel):
    content: str
    entity_id: Optional[str] = None
    post_type: str = "share"
    rating: Optional[int] = None
    images: list[str] = []

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Nội dung cần ít nhất 10 ký tự")
        if len(v) > 5000:
            raise ValueError("Nội dung tối đa 5000 ký tự")
        return v

    @field_validator("post_type")
    @classmethod
    def validate_type(cls, v):
        if v not in POST_TYPES:
            raise ValueError(f"Loại bài viết: {', '.join(POST_TYPES)}")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Đánh giá từ 1 đến 5 sao")
        return v


class CreateComment(BaseModel):
    content: str
    parent_id: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Bình luận không được để trống")
        if len(v) > 2000:
            raise ValueError("Bình luận tối đa 2000 ký tự")
        return v


class UpdatePost(BaseModel):
    content: Optional[str] = None
    rating: Optional[int] = None


# ── Post label mapping (Vietnamese) ──

POST_TYPE_LABELS = {
    "review": "Đánh giá",
    "share": "Chia sẻ trải nghiệm",
    "recommend": "Giới thiệu",
    "question": "Hỏi đáp",
}


# ── Posts ──

@router.post("/posts")
async def create_post(body: CreatePost, user=Depends(require_user)):
    if body.post_type in ENTITY_LINK_REQUIRED and not body.entity_id:
        raise HTTPException(400, "Đánh giá phải gắn với một địa điểm hoặc sản phẩm")

    if body.post_type == "review" and body.rating is None:
        raise HTTPException(400, "Đánh giá cần có số sao (1-5)")

    if body.entity_id:
        entity = db.get_entity(body.entity_id)
        if not entity:
            raise HTTPException(404, "Không tìm thấy địa điểm/sản phẩm")

    mod_result = await moderate_content(body.content, body.images)
    status = mod_result["status"]

    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            INSERT INTO posts (user_id, entity_id, content, images, post_type, rating, moderation_status)
            VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, {ph}, {ph})
            RETURNING *
        """, (
            str(user["id"]), body.entity_id, body.content,
            json.dumps(body.images), body.post_type, body.rating, status,
        ))

    post = db._row_to_dict(row)
    log_moderation("post", str(post["id"]), status, mod_result, auto=True)

    result = _enrich_post(post, user)
    if status != "approved":
        result["moderation_notice"] = (
            "Bài viết đang chờ kiểm duyệt" if status == "pending"
            else "Bài viết bị giữ lại để xem xét"
        )

    return {"post": result}


@router.get("/posts/{post_id}")
async def get_post(post_id: str, user=Depends(get_current_user)):
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"""
            SELECT p.*, u.display_name, u.avatar_url, u.phone,
                   e.name as entity_name, e.type as entity_type
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE p.id::text = {ph} AND p.moderation_status = 'approved'
        """, (post_id,))

    if not row:
        raise HTTPException(404, "Bài viết không tồn tại")

    post = db._row_to_dict(row)
    post["is_liked"] = False
    post["is_bookmarked"] = False

    if user:
        with db._conn() as conn:
            liked = db._fetchone(conn, f"""
                SELECT 1 FROM likes WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
            """, (str(user["id"]), post_id))
            bookmarked = db._fetchone(conn, f"""
                SELECT 1 FROM bookmarks WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
            """, (str(user["id"]), post_id))
            post["is_liked"] = liked is not None
            post["is_bookmarked"] = bookmarked is not None

    return {"post": _format_post(post)}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT user_id FROM posts WHERE id::text = {ph}", (post_id,))
        if not row:
            raise HTTPException(404)
        if str(row["user_id"]) != str(user["id"]) and user.get("role") not in ("admin", "moderator"):
            raise HTTPException(403, "Không có quyền xóa bài viết này")
        db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (post_id,))

    return {"success": True}


# ── Feed ──

@router.get("/feed")
async def get_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    post_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    area: Optional[str] = None,
    user=Depends(get_current_user),
):
    """
    Feed cộng đồng: chronological + seasonal boost + quality boost.
    Lọc theo loại bài, loại entity (du lịch, sản phẩm...), vùng miền.
    """
    ph = db._ph
    offset = (page - 1) * limit
    conditions = ["p.moderation_status = 'approved'"]
    params = []

    if post_type and post_type in POST_TYPES:
        conditions.append(f"p.post_type = {ph}")
        params.append(post_type)

    if entity_type:
        conditions.append(f"e.type = {ph}")
        params.append(entity_type)

    if area:
        conditions.append(f"""
            e."placeId" IN (
                SELECT id FROM entities WHERE type = 'place' AND attributes->>'area' = {ph}
            )
        """)
        params.append(area)

    if user:
        conditions.append(f"""
            p.user_id NOT IN (
                SELECT blocked_id FROM blocks WHERE blocker_id = {ph}::uuid
            )
        """)
        params.append(str(user["id"]))

    where = " AND ".join(conditions)
    where_params = list(params)

    month = datetime.now().month
    month_str = str(month)

    query_params = where_params + [month_str, month_str, limit, offset]

    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT p.*, u.display_name, u.avatar_url, u.phone,
                   e.name as entity_name, e.type as entity_type, e.season as entity_season
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE {where}
            ORDER BY
                CASE WHEN e.season IS NOT NULL
                     AND (e.season->'peak' ? {ph} OR e.season->'months' ? {ph})
                     THEN 1.5 ELSE 1.0 END
                * (1.0 + LN(2 + p.like_count))
                DESC,
                p.created_at DESC
            LIMIT {ph} OFFSET {ph}
        """, query_params)

        total = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM posts p
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE {where}
        """, where_params)

    posts = [_format_post(db._row_to_dict(r)) for r in rows]

    if user:
        post_ids = [p["id"] for p in posts]
        if post_ids:
            with db._conn() as conn:
                liked = db._fetchall(conn, f"""
                    SELECT post_id::text as pid FROM likes
                    WHERE user_id = {ph}::uuid AND post_id::text = ANY({ph}::text[])
                """, (str(user["id"]), post_ids))
                liked_set = {r["pid"] for r in liked}
                for p in posts:
                    p["is_liked"] = p["id"] in liked_set

    return {
        "posts": posts,
        "page": page,
        "total": total["c"] if total else 0,
        "has_more": offset + limit < (total["c"] if total else 0),
    }


@router.get("/community/stats")
async def community_stats():
    """Số liệu THẬT của cộng đồng (không phải đếm 20 bài đã tải) cho sidebar /cong-dong."""
    def _c(row):
        return int(db._row_to_dict(row)["c"]) if row else 0
    with db._conn() as conn:
        posts = db._fetchone(conn, "SELECT COUNT(*) c FROM posts WHERE moderation_status='approved'")
        reviews = db._fetchone(conn, "SELECT COUNT(*) c FROM posts WHERE post_type='review' AND moderation_status='approved'")
        members = db._fetchone(conn, "SELECT COUNT(*) c FROM users WHERE is_active=TRUE")
    return {"posts": _c(posts), "reviews": _c(reviews), "members": _c(members)}


@router.get("/entities/{entity_id}/feed")
async def get_entity_feed(
    entity_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(get_current_user),
):
    """Feed cho một entity cụ thể (điểm du lịch, sản phẩm...)."""
    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(404, "Không tìm thấy")

    ph = db._ph
    offset = (page - 1) * limit

    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT p.*, u.display_name, u.avatar_url, u.phone
            FROM posts p
            JOIN users u ON u.id = p.user_id
            WHERE p.entity_id = {ph} AND p.moderation_status = 'approved'
            ORDER BY p.created_at DESC
            LIMIT {ph} OFFSET {ph}
        """, (entity_id, limit, offset))

        total = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM posts
            WHERE entity_id = {ph} AND moderation_status = 'approved'
        """, (entity_id,))

        rating_row = db._fetchone(conn, f"""
            SELECT avg_rating, rating_count FROM entity_ratings
            WHERE entity_id = {ph}
        """, (entity_id,))

    return {
        "entity": {
            "id": entity["id"],
            "name": entity["name"],
            "type": entity["type"],
            "summary": entity.get("summary", ""),
        },
        "rating": {
            "avg": round(rating_row["avg_rating"], 1) if rating_row else 0,
            "count": rating_row["rating_count"] if rating_row else 0,
        },
        "posts": [_format_post(db._row_to_dict(r)) for r in rows],
        "total": total["c"] if total else 0,
    }


# ── Comments ──

@router.get("/posts/{post_id}/comments")
async def get_comments(post_id: str):
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT c.*, u.display_name, u.avatar_url, u.phone
            FROM comments c
            JOIN users u ON u.id = c.user_id
            WHERE c.post_id::text = {ph} AND c.moderation_status = 'approved'
            ORDER BY c.created_at ASC
        """, (post_id,))

    comments = [_format_comment(db._row_to_dict(r)) for r in rows]

    top_level = [c for c in comments if not c.get("parent_id")]
    for c in top_level:
        c["replies"] = [r for r in comments if str(r.get("parent_id")) == c["id"]]

    return {"comments": top_level}


@router.post("/posts/{post_id}/comments")
async def create_comment(post_id: str, body: CreateComment, user=Depends(require_user)):
    # P0-7: bình luận PHẢI qua kiểm duyệt như bài viết (trước đây bỏ qua → spam/abuse public ngay).
    mod_result = await moderate_content(body.content, [])
    status = mod_result["status"]

    ph = db._ph
    with db._conn() as conn:
        post = db._fetchone(conn, f"SELECT id FROM posts WHERE id::text = {ph}", (post_id,))
        if not post:
            raise HTTPException(404, "Bài viết không tồn tại")

        row = db._fetchone(conn, f"""
            INSERT INTO comments (post_id, user_id, parent_id, content, moderation_status)
            VALUES ({ph}::uuid, {ph}::uuid, {ph}::uuid, {ph}, {ph})
            RETURNING *
        """, (post_id, str(user["id"]),
              body.parent_id if body.parent_id else None,
              body.content, status))

        post_owner = db._fetchone(conn, f"SELECT user_id FROM posts WHERE id::text = {ph}", (post_id,))

    log_moderation("comment", str(db._row_to_dict(row)["id"]), status, mod_result, auto=True)

    # chỉ báo chủ bài khi bình luận được duyệt (không báo về nội dung bị giữ/ẩn)
    if status == "approved" and post_owner and str(post_owner["user_id"]) != str(user["id"]):
        preview = body.content[:80] + ("..." if len(body.content) > 80 else "")
        create_notification(
            str(post_owner["user_id"]), "comment",
            f"{user.get('display_name', 'Ai đó')} đã bình luận bài viết của bạn",
            body=preview, ref_type="post", ref_id=post_id,
        )

    return {"comment": _format_comment(db._row_to_dict(row))}


# ── Likes ──

@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        existing = db._fetchone(conn, f"""
            SELECT 1 FROM likes WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
        """, (str(user["id"]), post_id))

        if existing:
            db._execute(conn, f"""
                DELETE FROM likes WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
            """, (str(user["id"]), post_id))
            liked = False
        else:
            db._execute(conn, f"""
                INSERT INTO likes (user_id, post_id) VALUES ({ph}::uuid, {ph}::uuid)
            """, (str(user["id"]), post_id))
            liked = True

        post_row = db._fetchone(conn, f"""
            SELECT user_id, like_count FROM posts WHERE id::text = {ph}
        """, (post_id,))

    if liked and post_row and str(post_row["user_id"]) != str(user["id"]):
        create_notification(
            str(post_row["user_id"]), "like",
            f"{user.get('display_name', 'Ai đó')} đã thích bài viết của bạn",
            ref_type="post", ref_id=post_id,
        )

    return {"liked": liked, "like_count": post_row["like_count"] if post_row else 0}


# ── Bookmarks ──

@router.post("/posts/{post_id}/bookmark")
async def toggle_bookmark(post_id: str, user=Depends(require_user)):
    ph = db._ph
    with db._conn() as conn:
        existing = db._fetchone(conn, f"""
            SELECT 1 FROM bookmarks WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
        """, (str(user["id"]), post_id))

        if existing:
            db._execute(conn, f"""
                DELETE FROM bookmarks WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
            """, (str(user["id"]), post_id))
            saved = False
        else:
            db._execute(conn, f"""
                INSERT INTO bookmarks (user_id, post_id) VALUES ({ph}::uuid, {ph}::uuid)
            """, (str(user["id"]), post_id))
            saved = True

    return {"bookmarked": saved}


@router.get("/me/bookmarks")
async def get_my_bookmarks(
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50),
    user=Depends(require_user),
):
    ph = db._ph
    offset = (page - 1) * limit
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT p.*, u.display_name, u.avatar_url, u.phone,
                   e.name as entity_name, e.type as entity_type
            FROM bookmarks b
            JOIN posts p ON p.id = b.post_id
            JOIN users u ON u.id = p.user_id
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE b.user_id = {ph}::uuid AND p.moderation_status = 'approved'
            ORDER BY b.created_at DESC
            LIMIT {ph} OFFSET {ph}
        """, (str(user["id"]), limit, offset))

    return {"posts": [_format_post(db._row_to_dict(r)) for r in rows]}


# ── Image upload ──

@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...), user=Depends(require_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Chỉ chấp nhận file ảnh")

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Ảnh tối đa 5MB")

    url = await storage.upload_image(data, folder="posts", content_type=file.content_type)
    return {"url": url}


# ── User profile ──

@router.get("/users/{user_id}")
async def get_user_profile(user_id: str, user=Depends(get_current_user)):
    ph = db._ph
    with db._conn() as conn:
        profile = db._fetchone(conn, f"""
            SELECT id, display_name, avatar_url, bio, created_at
            FROM users WHERE id::text = {ph} AND is_active = TRUE
        """, (user_id,))

    if not profile:
        raise HTTPException(404, "Người dùng không tồn tại")

    profile = db._row_to_dict(profile)

    with db._conn() as conn:
        post_count = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM posts
            WHERE user_id::text = {ph} AND moderation_status = 'approved'
        """, (user_id,))
        review_count = db._fetchone(conn, f"""
            SELECT COUNT(*) as c FROM posts
            WHERE user_id::text = {ph} AND post_type = 'review' AND moderation_status = 'approved'
        """, (user_id,))

    return {
        "user": {
            "id": str(profile["id"]),
            "display_name": profile["display_name"],
            "avatar_url": profile.get("avatar_url"),
            "bio": profile.get("bio", ""),
            "created_at": str(profile["created_at"]),
            "stats": {
                "posts": post_count["c"] if post_count else 0,
                "reviews": review_count["c"] if review_count else 0,
            },
        },
    }


@router.get("/users/{user_id}/posts")
async def get_user_posts(
    user_id: str,
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50),
):
    ph = db._ph
    offset = (page - 1) * limit
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT p.*, u.display_name, u.avatar_url, u.phone,
                   e.name as entity_name, e.type as entity_type
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE p.user_id::text = {ph} AND p.moderation_status = 'approved'
            ORDER BY p.created_at DESC
            LIMIT {ph} OFFSET {ph}
        """, (user_id, limit, offset))

    return {"posts": [_format_post(db._row_to_dict(r)) for r in rows]}


# ── Helpers for AI integration (called by tools.py) ──

def get_community_reviews(entity_id: str, limit: int = 5) -> list[dict]:
    """Get recent approved reviews for an entity — used by AI chatbot."""
    ph = db._ph
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT p.content, p.rating, p.created_at, u.display_name
            FROM posts p
            JOIN users u ON u.id = p.user_id
            WHERE p.entity_id = {ph} AND p.post_type = 'review'
                AND p.moderation_status = 'approved'
            ORDER BY p.created_at DESC
            LIMIT {ph}
        """, (entity_id, limit))
    return [db._row_to_dict(r) for r in rows]


def get_trending_posts(limit: int = 10, entity_type: str = None) -> list[dict]:
    """Get trending posts (high engagement) — used by AI chatbot."""
    ph = db._ph
    conditions = ["p.moderation_status = 'approved'"]
    params = []
    if entity_type:
        conditions.append(f"e.type = {ph}")
        params.append(entity_type)
    where = " AND ".join(conditions)
    params.append(limit)
    with db._conn() as conn:
        rows = db._fetchall(conn, f"""
            SELECT p.content, p.post_type, p.like_count, p.comment_count,
                   p.rating, p.created_at, u.display_name,
                   e.name as entity_name, e.type as entity_type
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN entities e ON e.id = p.entity_id
            WHERE {where}
            ORDER BY (p.like_count + p.comment_count * 2) DESC, p.created_at DESC
            LIMIT {ph}
        """, params)
    return [db._row_to_dict(r) for r in rows]


# ── Format helpers ──

def _format_post(row: dict) -> dict:
    images = row.get("images", [])
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except Exception:
            images = []

    return {
        "id": str(row["id"]),
        "user_id": str(row.get("user_id", "")),
        "content": row["content"],
        "post_type": row.get("post_type", "share"),
        "post_type_label": POST_TYPE_LABELS.get(row.get("post_type", "share"), "Chia sẻ"),
        "rating": row.get("rating"),
        "images": images,
        "like_count": row.get("like_count", 0),
        "likes": row.get("like_count", 0),
        "comment_count": row.get("comment_count", 0),
        "comments_count": row.get("comment_count", 0),
        "is_liked": row.get("is_liked", False),
        "user_liked": row.get("is_liked", False),
        "is_bookmarked": row.get("is_bookmarked", False),
        "user_bookmarked": row.get("is_bookmarked", False),
        "created_at": str(row.get("created_at", "")),
        "display_name": row.get("display_name", ""),
        "avatar": row.get("avatar_url"),
        # P0-8: KHÔNG trả phone (PII) trong payload công khai
        "entity_id": row.get("entity_id"),
        "entity_name": row.get("entity_name"),
        "entity_type": row.get("entity_type"),
        "author": {
            "id": str(row.get("user_id", "")),
            "display_name": row.get("display_name", ""),
            "avatar_url": row.get("avatar_url"),
        },
        "entity": {
            "id": row.get("entity_id"),
            "name": row.get("entity_name"),
            "type": row.get("entity_type"),
        } if row.get("entity_id") else None,
    }


def _format_comment(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "content": row["content"],
        "parent_id": str(row["parent_id"]) if row.get("parent_id") else None,
        "created_at": str(row.get("created_at", "")),
        "author": {
            "id": str(row.get("user_id", "")),
            "display_name": row.get("display_name", ""),
            "avatar_url": row.get("avatar_url"),
        },
    }


def _enrich_post(row: dict, user: dict) -> dict:
    row["display_name"] = user.get("display_name")
    row["avatar_url"] = user.get("avatar_url")
    row["phone"] = user.get("phone", "")
    return _format_post(row)
