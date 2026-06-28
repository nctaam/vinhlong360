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

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from pydantic import BaseModel, field_validator

from auth_middleware import get_current_user, require_user, validate_path_id, require_csrf, require_idempotency
from database import db
from moderation import moderate_content, moderate_content_enhanced, log_moderation
from notifications import create_notification
from storage import storage
from ratelimit import check_rate

logger = logging.getLogger("social")

from config import settings as _cfg

RL_POST_LIMIT, RL_POST_WINDOW = _cfg.RL_POST_LIMIT, _cfg.RL_POST_WINDOW
RL_COMMENT_LIMIT, RL_COMMENT_WINDOW = _cfg.RL_COMMENT_LIMIT, _cfg.RL_COMMENT_WINDOW
RL_UPLOAD_LIMIT, RL_UPLOAD_WINDOW = 40, 600    # 40 ảnh / 10 phút
RL_LIKE_LIMIT, RL_LIKE_WINDOW = _cfg.RL_LIKE_LIMIT, _cfg.RL_LIKE_WINDOW
RL_DELETE_LIMIT, RL_DELETE_WINDOW = 10, 300     # 10 xóa / 5 phút


from auth_middleware import require_pg as _require_pg

router = APIRouter(prefix="/api", tags=["social"], dependencies=[Depends(_require_pg)])


def _block_sql(user: dict | None, column: str = "u.id") -> tuple[str, list]:
    """Return (AND … NOT IN …, [user_id]) to exclude blocked users in both directions."""
    if not user:
        return "", []
    ph = db._ph
    uid = str(user["id"])
    return (
        f"AND {column} NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id = {ph}::uuid) "
        f"AND {column} NOT IN (SELECT blocker_id FROM blocks WHERE blocked_id = {ph}::uuid)",
        [uid, uid],
    )

# ── Models ──

POST_TYPES = ("review", "share", "recommend", "question")
ENTITY_LINK_REQUIRED = ("review",)  # These types must link to an entity


def _enrich_user_status(posts: list[dict], user) -> list[dict]:
    """Add is_liked + is_bookmarked to a list of posts for the given user."""
    if not user or not posts:
        return posts
    ph = db._ph
    post_ids = [p["id"] for p in posts]
    uid = str(user["id"])
    with db._conn() as conn:
        liked = db._fetchall(conn, f"""
            SELECT post_id::text as pid FROM likes
            WHERE user_id = {ph}::uuid AND post_id::text = ANY({ph}::text[])
        """, (uid, post_ids))
        liked_set = {r["pid"] for r in liked}
        bookmarked = db._fetchall(conn, f"""
            SELECT post_id::text as pid FROM bookmarks
            WHERE user_id = {ph}::uuid AND post_id::text = ANY({ph}::text[])
        """, (uid, post_ids))
        bm_set = {r["pid"] for r in bookmarked}
    for p in posts:
        p["is_liked"] = p["id"] in liked_set
        p["is_bookmarked"] = p["id"] in bm_set
    return posts


_HTML_TAG_RE = re.compile(r"<[^>]+>")

def _strip_html_tags(s: str) -> str:
    """Remove HTML tags from user content (defense-in-depth against stored XSS)."""
    return _HTML_TAG_RE.sub("", s)


def _extract_hashtags(content: str) -> list[str]:
    """Trích #hashtag (Unicode, tiếng Việt OK) → lowercase, dedup, cap 10."""
    seen, out = set(), []
    for t in re.findall(r'#(\w{1,30})', content or '', re.UNICODE):
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            out.append(tl)
    return out[:10]


def _clean_mentions(raw) -> list[dict]:
    """Chuẩn hoá + giới hạn mentions: [{type:'user'|'entity', id, label}]. Bỏ mục sai."""
    out = []
    for m in (raw or [])[:20]:
        if not isinstance(m, dict):
            continue
        t = m.get("type")
        mid = str(m.get("id") or "").strip()
        label = str(m.get("label") or "").strip()[:80]
        if t in ("user", "entity") and mid and label:
            out.append({"type": t, "id": mid[:64], "label": label})
    return out


def _notify_mentions(mentions: list[dict], author_id: str, author_name, post_id: str, content: str) -> None:
    """Gửi thông báo cho người-dùng được @-nhắc (bỏ tự-nhắc + trùng)."""
    preview = (content or "")[:80] + ("…" if len(content or "") > 80 else "")
    seen = set()
    for m in mentions:
        if m.get("type") != "user":
            continue
        uid = m.get("id")
        if not uid or uid == author_id or uid in seen:
            continue
        seen.add(uid)
        try:
            create_notification(uid, "mention", f"{author_name or 'Ai đó'} đã nhắc đến bạn",
                                body=preview, ref_type="post", ref_id=post_id, actor_id=author_id)
        except Exception:
            logger.exception("Failed to notify mention for user %s on post %s", uid, post_id)


def _notify_entity_followers(entity_id, author_id, author_name, post_id: str) -> None:
    """Báo cho người THEO DÕI địa-điểm khi có bài mới về địa-điểm đó (batch insert)."""
    if not entity_id:
        return
    ph = db._ph
    try:
        with db._conn() as conn:
            rows = db._fetchall(conn,
                f"SELECT follower_id FROM follows WHERE target_type='entity' AND target_id = {ph}", (entity_id,))
            follower_ids = [str(db._row_to_dict(r)["follower_id"]) for r in rows]
            follower_ids = [fid for fid in follower_ids if fid != author_id]
            if not follower_ids:
                return
            title = f"{author_name or 'Ai đó'} đã đăng về địa điểm bạn theo dõi"
            for uid in follower_ids:
                try:
                    create_notification(uid, "entity_post", title, ref_type="post", ref_id=post_id, actor_id=author_id)
                except Exception:
                    logger.exception("Failed to notify entity follower %s on post %s", uid, post_id)
    except Exception:
        logger.exception("Failed to load entity followers for entity %s", entity_id)


class CreatePost(BaseModel):
    content: str = ""
    entity_id: Optional[str] = None
    post_type: str = "share"
    rating: Optional[int] = None
    images: list[str] = []
    mentions: list[dict] = []
    repost_of: Optional[str] = None  # Threads-style repost/quote

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = _strip_html_tags((v or "").strip())
        # Cho phép RỖNG (repost không kèm lời); 1-9 ký tự = quá ngắn → chặn. ≥10 OK.
        if 0 < len(v) < 10:
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

    @field_validator("images")
    @classmethod
    def validate_images(cls, v):
        if len(v) > 20:
            raise ValueError("Tối đa 20 ảnh")
        return v


class CreateComment(BaseModel):
    content: str
    parent_id: Optional[str] = None
    mentions: list[dict] = []

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = _strip_html_tags(v.strip())
        if len(v) < 1:
            raise ValueError("Bình luận không được để trống")
        if len(v) > 2000:
            raise ValueError("Bình luận tối đa 2000 ký tự")
        return v


class UpdatePost(BaseModel):
    content: Optional[str] = None
    rating: Optional[int] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if v is None:
            return v
        v = _strip_html_tags(v.strip())
        if 0 < len(v) < 10:
            raise ValueError("Nội dung cần ít nhất 10 ký tự")
        if len(v) > 5000:
            raise ValueError("Nội dung tối đa 5000 ký tự")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Đánh giá từ 1 đến 5 sao")
        return v


# ── Post label mapping (Vietnamese) ──

POST_TYPE_LABELS = {
    "review": "Đánh giá",
    "share": "Chia sẻ trải nghiệm",
    "recommend": "Giới thiệu",
    "question": "Hỏi đáp",
}


# ── Posts ──

RL_POST_DAILY_LIMIT = _cfg.RL_POST_DAILY_LIMIT
RL_POST_DAILY_WINDOW = _cfg.RL_POST_DAILY_WINDOW

@router.post("/posts")
async def create_post(body: CreatePost, user=Depends(require_user), _csrf=Depends(require_csrf), _idem=Depends(require_idempotency)):
    check_rate(f"post:{user['id']}", RL_POST_LIMIT, RL_POST_WINDOW,
               "Bạn đăng bài quá nhanh. Vui lòng đợi ít phút rồi thử lại.")
    check_rate(f"post-day:{user['id']}", RL_POST_DAILY_LIMIT, RL_POST_DAILY_WINDOW,
               "Bạn đã đạt giới hạn đăng bài trong ngày. Vui lòng thử lại ngày mai.")

    if body.content.strip() and not body.repost_of:
        ph = db._ph
        def _check_dup():
            with db._conn() as conn:
                return db._fetchone(conn, f"""
                    SELECT 1 FROM posts
                    WHERE user_id = {ph}::uuid AND content = {ph}
                      AND created_at > NOW() - INTERVAL '1 hour'
                    LIMIT 1
                """, (str(user["id"]), body.content.strip()))
        if await asyncio.to_thread(_check_dup):
            raise HTTPException(409, "Bài viết trùng nội dung. Vui lòng chỉnh sửa trước khi đăng lại.")

    if body.post_type in ENTITY_LINK_REQUIRED and not body.entity_id:
        raise HTTPException(400, "Đánh giá phải gắn với một địa điểm hoặc sản phẩm")

    if body.post_type == "review" and body.rating is None:
        raise HTTPException(400, "Đánh giá cần có số sao (1-5)")

    if body.entity_id:
        entity = await asyncio.to_thread(db.get_entity, body.entity_id)
        if not entity:
            raise HTTPException(404, "Không tìm thấy địa điểm/sản phẩm")

    # Repost rỗng được phép; bài thường cần ≥10 ký tự
    if not body.repost_of and len(body.content.strip()) < 10:
        raise HTTPException(400, "Nội dung cần ít nhất 10 ký tự")

    ph = db._ph
    repost_snapshot = None
    orig_author_id = None
    if body.repost_of:
        def _check_repost():
            with db._conn() as conn:
                return db._fetchone(conn, f"""
                    SELECT p.id, p.content, p.user_id, p.created_at, p.repost_of, u.display_name
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE p.id::text = {ph} AND p.moderation_status = 'approved'
                """, (body.repost_of,))
        orig = await asyncio.to_thread(_check_repost)
        if not orig:
            raise HTTPException(404, "Bài gốc không tồn tại")
        od = db._row_to_dict(orig)
        if od.get("repost_of"):
            raise HTTPException(400, "Không thể đăng lại một bài đã là repost")
        orig_author_id = str(od["user_id"])
        if orig_author_id == str(user["id"]):
            raise HTTPException(400, "Không thể đăng lại bài viết của chính mình")
        repost_snapshot = {
            "id": str(od["id"]), "author": od.get("display_name") or "",
            "content": (od.get("content") or "")[:280], "created_at": str(od.get("created_at") or ""),
        }

    mod_result = await moderate_content_enhanced(body.content, user_id=str(user["id"]), image_urls=body.images)
    status = mod_result["status"]
    mentions = _clean_mentions(body.mentions)
    hashtags = _extract_hashtags(body.content)

    def _insert():
        with db._conn() as conn:
            return db._fetchone(conn, f"""
                INSERT INTO posts (user_id, entity_id, content, images, post_type, rating, moderation_status, mentions, hashtags, repost_of, repost_snapshot)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph}::jsonb, {ph}, {ph}, {ph}, {ph}::jsonb, {ph}::jsonb, {ph}, {ph}::jsonb)
                RETURNING *
            """, (
                str(user["id"]), body.entity_id, body.content,
                json.dumps(body.images), body.post_type, body.rating, status,
                json.dumps(mentions, ensure_ascii=False), json.dumps(hashtags, ensure_ascii=False),
                body.repost_of,
                json.dumps(repost_snapshot, ensure_ascii=False) if repost_snapshot else None,
            ))
    row = await asyncio.to_thread(_insert)
    post = db._row_to_dict(row)
    log_moderation("post", str(post["id"]), status, mod_result, auto=True)

    if status == "approved":
        def _notify_post():
            _notify_mentions(mentions, str(user["id"]), user.get("display_name"), str(post["id"]), body.content)
            _notify_entity_followers(body.entity_id, str(user["id"]), user.get("display_name"), str(post["id"]))
            if orig_author_id and orig_author_id != str(user["id"]):
                try:
                    create_notification(orig_author_id, "repost",
                                        f"{user.get('display_name') or 'Ai đó'} đã đăng lại bài của bạn",
                                        ref_type="post", ref_id=str(post["id"]), actor_id=str(user["id"]))
                except Exception:
                    logger.exception("Failed to notify repost to user %s", orig_author_id)
        await asyncio.to_thread(_notify_post)

    result = _enrich_post(post, user)
    if status != "approved":
        result["moderation_notice"] = (
            "Bài viết đang chờ kiểm duyệt" if status == "pending"
            else "Bài viết bị giữ lại để xem xét"
        )

    return {"post": result}


@router.get("/posts/{post_id}")
async def get_post(post_id: str, user=Depends(get_current_user)):
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    uid = str(user["id"]) if user else None

    def _get_post():
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                SELECT p.*, u.display_name, u.avatar_url, u.username,
                       e.name as entity_name, e.type as entity_type
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.id::text = {ph} AND p.moderation_status = 'approved'
            """, (post_id,))
            if not row:
                return None
            post = db._row_to_dict(row)
            post["is_liked"] = False
            post["is_bookmarked"] = False
            if uid:
                liked = db._fetchone(conn, f"""
                    SELECT 1 FROM likes WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
                """, (uid, post_id))
                bookmarked = db._fetchone(conn, f"""
                    SELECT 1 FROM bookmarks WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
                """, (uid, post_id))
                post["is_liked"] = liked is not None
                post["is_bookmarked"] = bookmarked is not None
            return post

    post = await asyncio.to_thread(_get_post)
    if not post:
        raise HTTPException(404, "Bài viết không tồn tại")

    return {"post": _format_post(post)}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    post_id = validate_path_id(post_id, "post_id")
    check_rate(f"delete:{user['id']}", RL_DELETE_LIMIT, RL_DELETE_WINDOW,
               "Bạn xóa quá nhanh. Vui lòng đợi ít phút.")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT user_id FROM posts WHERE id::text = {ph}", (post_id,))
            if not row:
                raise HTTPException(404)
            if str(row["user_id"]) != str(user["id"]) and user.get("role") not in ("admin", "moderator"):
                raise HTTPException(403, "Không có quyền xóa bài viết này")
            db._execute(conn, f"DELETE FROM posts WHERE id::text = {ph}", (post_id,))
    await asyncio.to_thread(_query)
    return {"success": True}


@router.patch("/posts/{post_id}")
async def update_post(post_id: str, body: UpdatePost, user=Depends(require_user), _csrf=Depends(require_csrf)):
    """Sửa bài của CHÍNH MÌNH (nội dung; review đổi sao). Kiểm duyệt + hashtag lại."""
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _check_owner():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT user_id, post_type FROM posts WHERE id::text = {ph}", (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            d = db._row_to_dict(row)
            if str(d["user_id"]) != str(user["id"]):
                raise HTTPException(403, "Không có quyền sửa bài viết này")
            return d
    d = await asyncio.to_thread(_check_owner)

    new_content = (body.content or "").strip()
    if len(new_content) < 10:
        raise HTTPException(400, "Nội dung cần ít nhất 10 ký tự")
    if len(new_content) > 5000:
        raise HTTPException(400, "Nội dung tối đa 5000 ký tự")

    mod_result = await moderate_content_enhanced(new_content, user_id=str(user["id"]))
    status = mod_result["status"]
    hashtags = _extract_hashtags(new_content)
    set_rating = body.rating is not None and d["post_type"] == "review"
    if set_rating and (body.rating < 1 or body.rating > 5):
        raise HTTPException(400, "Đánh giá từ 1 đến 5 sao")

    def _update():
        with db._conn() as conn:
            if set_rating:
                db._execute(conn, f"""UPDATE posts SET content={ph}, hashtags={ph}::jsonb,
                              rating={ph}, moderation_status={ph} WHERE id::text={ph}""",
                            (new_content, json.dumps(hashtags, ensure_ascii=False), body.rating, status, post_id))
            else:
                db._execute(conn, f"""UPDATE posts SET content={ph}, hashtags={ph}::jsonb,
                              moderation_status={ph} WHERE id::text={ph}""",
                            (new_content, json.dumps(hashtags, ensure_ascii=False), status, post_id))
            return db._fetchone(conn, f"""
                SELECT p.*, u.display_name, u.avatar_url, u.username,
                       e.name as entity_name, e.type as entity_type
                FROM posts p JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id WHERE p.id::text = {ph}
            """, (post_id,))
    post = await asyncio.to_thread(_update)
    return {"post": _format_post(db._row_to_dict(post)), "moderation_status": status}


# ── Feed ──

@router.get("/feed")
async def get_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    post_type: Optional[str] = Query(None, max_length=50),
    entity_type: Optional[str] = Query(None, max_length=50),
    area: Optional[str] = Query(None, max_length=50),
    tag: Optional[str] = Query(None, max_length=100),
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

    if tag:
        conditions.append(f"p.hashtags @> {ph}::jsonb")
        params.append(json.dumps([tag.lower().lstrip("#")]))

    if entity_type:
        conditions.append(f"e.type = {ph}")
        params.append(entity_type)

    if area:
        # FIX: place lưu vùng ở CỘT top-level `area`, KHÔNG ở attributes (trước dùng
        # attributes->>'area' → subquery luôn rỗng → feed?area= rỗng). Khớp pattern
        # database.list_entities/search_entities.
        conditions.append(f"""
            (e.area = {ph} OR e."placeId" IN (
                SELECT id FROM entities WHERE type = 'place' AND area = {ph}
            ))
        """)
        params.extend([area, area])

    bc, bc_p = _block_sql(user, "p.user_id")
    if bc:
        conditions.append(bc.removeprefix("AND "))
        params.extend(bc_p)

    where = " AND ".join(conditions)
    where_params = list(params)

    month = datetime.now().month
    month_str = str(month)

    query_params = where_params + [month_str, month_str, limit, offset]

    feed_sql = f"""
        SELECT p.*, u.display_name, u.avatar_url, u.username,
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
    """
    count_sql = f"""
        SELECT COUNT(*) as c FROM posts p
        LEFT JOIN entities e ON e.id = p.entity_id
        WHERE {where}
    """

    def _feed_query():
        with db._conn() as conn:
            rows = db._fetchall(conn, feed_sql, query_params)
            total = db._fetchone(conn, count_sql, where_params)
        return rows, total

    rows, total = await asyncio.to_thread(_feed_query)

    posts = [_format_post(db._row_to_dict(r)) for r in rows]

    await asyncio.to_thread(_enrich_user_status, posts, user)

    return {
        "posts": posts,
        "page": page,
        "total": total["c"] if total else 0,
        "has_more": offset + limit < (total["c"] if total else 0),
    }


@router.get("/feed/following")
async def get_following_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(require_user),
):
    """Feed các bài từ NGƯỜI + ĐỊA ĐIỂM mình theo dõi (mới nhất trước)."""
    ph = db._ph
    offset = (page - 1) * limit
    uid = str(user["id"])
    # điều kiện: tác giả là người mình follow HOẶC bài gắn địa-điểm mình follow
    bc, bc_p = _block_sql(user, "p.user_id")
    follow_cond = f"""
        (p.user_id IN (SELECT target_id::uuid FROM follows
                         WHERE follower_id = {ph}::uuid AND target_type='user')
         OR p.entity_id IN (SELECT target_id FROM follows
                              WHERE follower_id = {ph}::uuid AND target_type='entity'))
    """
    feed_sql = f"""
        SELECT p.*, u.display_name, u.avatar_url, u.username,
               e.name as entity_name, e.type as entity_type
        FROM posts p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN entities e ON e.id = p.entity_id
        WHERE p.moderation_status = 'approved' AND {follow_cond}
        {bc}
        ORDER BY p.created_at DESC
        LIMIT {ph} OFFSET {ph}
    """
    count_sql = f"""
        SELECT COUNT(*) as c FROM posts p
        WHERE p.moderation_status = 'approved' AND {follow_cond}
        {bc}
    """

    def _following_query():
        with db._conn() as conn:
            rows = db._fetchall(conn, feed_sql, (uid, uid, *bc_p, limit, offset))
            total = db._fetchone(conn, count_sql, (uid, uid, *bc_p))
        return rows, total

    rows, total = await asyncio.to_thread(_following_query)

    posts = [_format_post(db._row_to_dict(r)) for r in rows]
    await asyncio.to_thread(_enrich_user_status, posts, user)

    total_c = total["c"] if total else 0
    return {"posts": posts, "page": page, "total": total_c,
            "has_more": offset + limit < total_c}


@router.get("/search/posts")
async def search_posts(
    q: str = Query(..., min_length=2, max_length=100),
    page: int = Query(1, ge=1),
    user=Depends(get_current_user),
):
    """Tìm bài viết cộng đồng theo nội dung (PG trigram `lower(content) LIKE`,
    không phân biệt hoa-thường; chỉ bài ĐÃ DUYỆT). v1 phân-biệt-dấu."""
    uid = user["id"] if user else "anon"
    check_rate(f"search:{uid}", 30, 60, "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
    stripped = q.strip()
    if len(stripped) < 2:
        return {"posts": [], "total": 0, "page": 1}
    ph = db._ph
    limit = 20
    offset = (page - 1) * limit
    from database import escape_like
    pattern = "%" + escape_like(stripped.lower()) + "%"

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.*, u.display_name, u.avatar_url, u.username,
                       e.name as entity_name, e.type as entity_type
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.moderation_status = 'approved'
                  AND f_unaccent(lower(p.content)) LIKE f_unaccent({ph}) ESCAPE '\\'
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (pattern, limit, offset))
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts p
                WHERE p.moderation_status = 'approved' AND f_unaccent(lower(p.content)) LIKE f_unaccent({ph}) ESCAPE '\\'
            """, (pattern,))
        return rows, total
    rows, total = await asyncio.to_thread(_query)

    posts = [_format_post(db._row_to_dict(r)) for r in rows]
    await asyncio.to_thread(_enrich_user_status, posts, user)

    total_c = total["c"] if total else 0
    return {"posts": posts, "q": q, "page": page, "total": total_c,
            "has_more": offset + limit < total_c}


@router.get("/search/users")
async def search_users(
    q: str = Query(..., min_length=2, max_length=50),
    page: int = Query(1, ge=1),
    user=Depends(get_current_user),
):
    """Tìm người dùng theo tên hiển thị (không phân-biệt-dấu). Thông tin hồ-sơ công-khai."""
    uid = user["id"] if user else "anon"
    check_rate(f"search:{uid}", 30, 60, "Tìm kiếm quá nhanh. Vui lòng thử lại sau.")
    stripped = q.strip()
    if len(stripped) < 2:
        return {"users": [], "total": 0, "page": 1}
    ph = db._ph
    limit = 20
    offset = (page - 1) * limit
    from database import escape_like
    pattern = "%" + escape_like(stripped.lower()) + "%"
    bc, bc_p = _block_sql(user)
    params: list = [pattern] + bc_p + [limit, offset]

    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT u.id, u.display_name, u.avatar_url, u.username,
                       COUNT(p.id) AS post_count
                FROM users u
                LEFT JOIN posts p ON p.user_id = u.id AND p.moderation_status = 'approved'
                WHERE u.is_active = TRUE AND u.deleted_at IS NULL
                  AND f_unaccent(lower(u.display_name)) LIKE f_unaccent({ph}) ESCAPE '\\'
                  {bc}
                GROUP BY u.id, u.display_name, u.avatar_url, u.username
                ORDER BY post_count DESC, u.display_name
                LIMIT {ph} OFFSET {ph}
            """, tuple(params))
    rows = await asyncio.to_thread(_query)

    users = []
    for r in rows:
        d = db._row_to_dict(r)
        if d.get("display_name"):
            users.append({
                "id": str(d["id"]), "display_name": d["display_name"],
                "avatar_url": d.get("avatar_url"), "username": d.get("username"),
                "post_count": int(d.get("post_count") or 0),
            })
    return {"users": users, "q": q, "page": page, "total": len(users), "has_more": len(users) == limit}


@router.get("/community/stats")
async def community_stats():
    """Số liệu THẬT của cộng đồng (không phải đếm 20 bài đã tải) cho sidebar /cong-dong."""
    def _c(row):
        return int(db._row_to_dict(row)["c"]) if row else 0
    def _query():
        with db._conn() as conn:
            posts = db._fetchone(conn, "SELECT COUNT(*) c FROM posts WHERE moderation_status='approved'")
            reviews = db._fetchone(conn, "SELECT COUNT(*) c FROM posts WHERE post_type='review' AND moderation_status='approved'")
            members = db._fetchone(conn, "SELECT COUNT(*) c FROM users WHERE is_active=TRUE")
        return {"posts": _c(posts), "reviews": _c(reviews), "members": _c(members)}
    return await asyncio.to_thread(_query)


_trending_cache: dict = {"ts": 0.0, "data": {}}
_TRENDING_TTL = _cfg.TRENDING_CACHE_TTL

@router.get("/community/trending-tags")
async def trending_tags(limit: int = Query(10, ge=1, le=20)):
    """Hashtag thịnh hành: đếm hashtag trên bài ĐÃ DUYỆT trong 30 ngày gần nhất."""
    import time as _t
    now = _t.time()
    cache_key = f"tags:{limit}"
    if now - _trending_cache["ts"] < _TRENDING_TTL and cache_key in _trending_cache.get("data", {}):
        return _trending_cache["data"][cache_key]

    ph = db._ph
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT tag, COUNT(*) AS c
                FROM posts p, jsonb_array_elements_text(p.hashtags) AS tag
                WHERE p.moderation_status = 'approved'
                  AND p.created_at > NOW() - INTERVAL '30 days'
                GROUP BY tag
                ORDER BY c DESC, tag
                LIMIT {ph}
            """, (limit,))
    rows = await asyncio.to_thread(_query)
    tags = [{"tag": (d := db._row_to_dict(r))["tag"], "count": int(d["c"])} for r in rows]
    result = {"tags": tags}
    _trending_cache["ts"] = now
    _trending_cache["data"] = {cache_key: result}
    return result


_leaderboard_cache: dict = {"ts": 0.0, "data": None}

@router.get("/community/leaderboard")
async def community_leaderboard(limit: int = Query(10, ge=1, le=50), user=Depends(get_current_user)):
    """Bảng xếp hạng: thành viên tích cực theo điểm danh-tiếng (1 query gộp)."""
    import time as _t
    now = _t.time()
    ph = db._ph
    bc, bc_p = _block_sql(user)
    if not bc and _leaderboard_cache["data"] is not None and now - _leaderboard_cache["ts"] < _cfg.TRENDING_CACHE_TTL:
        return {"leaders": _leaderboard_cache["data"][:limit]}
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT u.id, u.display_name, u.avatar_url, u.username,
                       COUNT(p.id) FILTER (WHERE p.post_type='review') AS reviews,
                       COUNT(p.id) AS posts,
                       COUNT(p.id) FILTER (WHERE jsonb_typeof(p.images)='array'
                                             AND jsonb_array_length(p.images) > 0) AS photos,
                       COALESCE(fc.c, 0) AS followers,
                       COUNT(DISTINCT p.entity_id) FILTER (WHERE p.entity_id IS NOT NULL) AS places,
                       COALESCE(SUM(CASE WHEN jsonb_typeof(p.likes)='number' THEN p.likes::int
                                         WHEN jsonb_typeof(p.likes)='array' THEN jsonb_array_length(p.likes)
                                         ELSE 0 END), 0) AS likes
                FROM users u
                LEFT JOIN posts p ON p.user_id = u.id AND p.moderation_status = 'approved'
                LEFT JOIN (SELECT target_id, COUNT(*) c FROM follows
                             WHERE target_type='user' GROUP BY target_id) fc
                       ON fc.target_id = u.id::text
                WHERE u.is_active = TRUE AND u.deleted_at IS NULL AND u.display_name IS NOT NULL
                {bc}
                GROUP BY u.id, u.display_name, u.avatar_url, u.username, fc.c
                HAVING COUNT(p.id) > 0
            """, tuple(bc_p))
    rows = await asyncio.to_thread(_query)

    leaders = []
    for r in rows:
        d = db._row_to_dict(r)
        reviews = int(d["reviews"] or 0)
        posts = int(d["posts"] or 0)
        photos = int(d["photos"] or 0)
        followers = int(d["followers"] or 0)
        places = int(d["places"] or 0)
        likes = int(d["likes"] or 0)
        points = _calc_points(reviews, posts, photos, followers, places, likes)
        if points <= 0:
            continue
        level, label = _level_for(points)
        leaders.append({
            "id": str(d["id"]), "display_name": d["display_name"], "avatar_url": d.get("avatar_url"),
            "username": d.get("username"),
            "points": points, "level": level, "level_label": label,
            "posts": posts, "reviews": reviews,
        })
    leaders.sort(key=lambda x: x["points"], reverse=True)
    if not bc:
        _leaderboard_cache["ts"] = _t.time()
        _leaderboard_cache["data"] = leaders
    return {"leaders": leaders[:limit]}


@router.get("/users/{user_id}/following")
async def list_following_users(user_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """Danh sách NGƯỜI mà user này đang theo dõi (hồ-sơ công-khai)."""
    validate_path_id(user_id, "user_id")
    ph = db._ph
    uid = await asyncio.to_thread(_resolve_user_id, user_id)
    if not uid:
        raise HTTPException(404, "Người dùng không tồn tại")
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT u.id, u.display_name, u.avatar_url, u.username
                FROM follows f JOIN users u ON u.id::text = f.target_id
                WHERE f.follower_id = {ph}::uuid AND f.target_type = 'user' AND u.is_active = TRUE
                ORDER BY f.created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
    rows = await asyncio.to_thread(_query)
    users = []
    for r in rows:
        d = db._row_to_dict(r)
        users.append({"id": str(d["id"]), "display_name": d["display_name"],
                       "username": d.get("username"), "avatar_url": d.get("avatar_url")})
    return {"users": users, "offset": offset, "has_more": len(users) == limit}


@router.get("/users/{user_id}/followers")
async def list_followers(user_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """Danh sách NGƯỜI đang theo dõi user này (hồ-sơ công-khai)."""
    validate_path_id(user_id, "user_id")
    ph = db._ph
    uid = await asyncio.to_thread(_resolve_user_id, user_id)
    if not uid:
        raise HTTPException(404, "Người dùng không tồn tại")
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT u.id, u.display_name, u.avatar_url, u.username
                FROM follows f JOIN users u ON u.id = f.follower_id
                WHERE f.target_type = 'user' AND f.target_id = {ph} AND u.is_active = TRUE
                ORDER BY f.created_at DESC LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
    rows = await asyncio.to_thread(_query)
    users = []
    for r in rows:
        d = db._row_to_dict(r)
        users.append({"id": str(d["id"]), "display_name": d["display_name"],
                       "username": d.get("username"), "avatar_url": d.get("avatar_url")})
    return {"users": users, "offset": offset, "has_more": len(users) == limit}


@router.get("/community/suggested-follows")
async def suggested_follows(user=Depends(require_user), limit: int = Query(5, ge=1, le=20)):
    """Gợi ý người để theo dõi: top contributor mình CHƯA theo dõi (loại chính mình)."""
    ph = db._ph
    me = str(user["id"])
    bc, bc_p = _block_sql(user)
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT u.id, u.display_name, u.avatar_url, u.username,
                       COUNT(p.id) FILTER (WHERE p.post_type='review') AS reviews,
                       COUNT(p.id) AS posts,
                       COUNT(p.id) FILTER (WHERE jsonb_typeof(p.images)='array'
                                             AND jsonb_array_length(p.images) > 0) AS photos,
                       COALESCE(fc.c, 0) AS followers,
                       COUNT(DISTINCT p.entity_id) FILTER (WHERE p.entity_id IS NOT NULL) AS places,
                       COALESCE(SUM(CASE WHEN jsonb_typeof(p.likes)='number' THEN p.likes::int
                                         WHEN jsonb_typeof(p.likes)='array' THEN jsonb_array_length(p.likes)
                                         ELSE 0 END), 0) AS likes
                FROM users u
                LEFT JOIN posts p ON p.user_id = u.id AND p.moderation_status = 'approved'
                LEFT JOIN (SELECT target_id, COUNT(*) c FROM follows
                             WHERE target_type='user' GROUP BY target_id) fc ON fc.target_id = u.id::text
                WHERE u.is_active = TRUE AND u.deleted_at IS NULL AND u.display_name IS NOT NULL
                  AND u.id::text <> {ph}
                  AND u.id::text NOT IN (SELECT target_id FROM follows
                                           WHERE follower_id = {ph}::uuid AND target_type='user')
                  {bc}
                GROUP BY u.id, u.display_name, u.avatar_url, u.username, fc.c
            """, (me, me) + tuple(bc_p))
    rows = await asyncio.to_thread(_query)
    cands = []
    for r in rows:
        d = db._row_to_dict(r)
        reviews = int(d["reviews"] or 0); posts = int(d["posts"] or 0)
        photos = int(d["photos"] or 0); followers = int(d["followers"] or 0)
        places = int(d["places"] or 0); likes = int(d["likes"] or 0)
        points = _calc_points(reviews, posts, photos, followers, places, likes)
        if points <= 0:
            continue
        cands.append({"id": str(d["id"]), "display_name": d["display_name"],
                      "avatar_url": d.get("avatar_url"), "username": d.get("username"),
                      "points": points, "posts": posts})
    cands.sort(key=lambda x: x["points"], reverse=True)
    return {"users": cands[:limit]}


@router.get("/entities/{entity_id}/feed")
async def get_entity_feed(
    entity_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(get_current_user),
):
    """Feed cho một entity cụ thể (điểm du lịch, sản phẩm...)."""
    entity_id = validate_path_id(entity_id, "entity_id")
    entity = await asyncio.to_thread(db.get_entity, entity_id)
    if not entity:
        raise HTTPException(404, "Không tìm thấy")

    ph = db._ph
    offset = (page - 1) * limit
    bc, bc_p = _block_sql(user)
    params: list = [entity_id] + bc_p + [limit, offset]

    feed_sql = f"""
        SELECT p.*, u.display_name, u.avatar_url, u.username
        FROM posts p
        JOIN users u ON u.id = p.user_id
        WHERE p.entity_id = {ph} AND p.moderation_status = 'approved'
        {bc}
        ORDER BY (CASE WHEN jsonb_typeof(p.images)='array' AND jsonb_array_length(p.images) > 0
                       THEN 1 ELSE 0 END) DESC,
                 p.like_count DESC,
                 p.created_at DESC
        LIMIT {ph} OFFSET {ph}
    """
    feed_params = tuple(params)

    def _entity_feed_query():
        with db._conn() as conn:
            rows = db._fetchall(conn, feed_sql, feed_params)
            total = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM posts
                WHERE entity_id = {ph} AND moderation_status = 'approved'
            """, (entity_id,))
            rating_row = db._fetchone(conn, f"""
                SELECT avg_rating, rating_count FROM entity_ratings
                WHERE entity_id = {ph}
            """, (entity_id,))
        return rows, total, rating_row

    rows, total, rating_row = await asyncio.to_thread(_entity_feed_query)

    posts = [_format_post(db._row_to_dict(r)) for r in rows]
    await asyncio.to_thread(_enrich_user_status, posts, user)

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
        "posts": posts,
        "total": total["c"] if total else 0,
    }


@router.get("/posts/{post_id}/related")
async def related_posts(post_id: str, limit: int = Query(4, ge=1, le=10)):
    """Bài viết liên quan: cùng entity hoặc cùng hashtag."""
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            src = db._fetchone(conn, f"""
                SELECT entity_id, hashtags FROM posts
                WHERE id::text = {ph} AND moderation_status = 'approved'
            """, (post_id,))
            if not src:
                return []
            d = db._row_to_dict(src)
            entity_id = d.get("entity_id")
            tags = d.get("hashtags") or []

            candidates = []
            if entity_id:
                rows = db._fetchall(conn, f"""
                    SELECT p.*, u.display_name, u.avatar_url
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE p.entity_id = {ph} AND p.id::text <> {ph}
                      AND p.moderation_status = 'approved'
                    ORDER BY p.like_count DESC, p.created_at DESC
                    LIMIT {ph}
                """, (entity_id, post_id, limit))
                candidates.extend(rows)

            if len(candidates) < limit and tags:
                seen = {post_id} | {str(db._row_to_dict(r)["id"]) for r in candidates}
                tag_rows = db._fetchall(conn, f"""
                    SELECT p.*, u.display_name, u.avatar_url
                    FROM posts p JOIN users u ON u.id = p.user_id
                    WHERE p.moderation_status = 'approved' AND p.id::text <> {ph}
                      AND p.hashtags && ARRAY[{','.join(ph for _ in tags)}]::text[]
                    ORDER BY p.like_count DESC
                    LIMIT {ph}
                """, (post_id, *tags, limit))
                for r in tag_rows:
                    d = db._row_to_dict(r)
                    rid = str(d["id"])
                    if rid not in seen:
                        candidates.append(r)
                        seen.add(rid)
            return candidates
    candidates = await asyncio.to_thread(_query)
    return {"posts": [_format_post(db._row_to_dict(r)) for r in candidates[:limit]]}


# ── Comments ──

@router.get("/posts/{post_id}/comments")
async def get_comments(
    post_id: str, request: Request,
    limit: int = Query(100, ge=1, le=200),
    user=Depends(get_current_user),
):
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    bc, bc_p = _block_sql(user, "c.user_id")
    params: list = [post_id] + bc_p + [min(limit, 200)]
    comment_sql = f"""
        SELECT c.*, u.display_name, u.avatar_url
        FROM comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.post_id::text = {ph} AND c.moderation_status = 'approved'
        {bc}
        ORDER BY c.created_at ASC
        LIMIT {ph}
    """
    comment_params = tuple(params)

    def _get_comments():
        with db._conn() as conn:
            return db._fetchall(conn, comment_sql, comment_params)

    rows = await asyncio.to_thread(_get_comments)

    comments = [_format_comment(db._row_to_dict(r)) for r in rows]

    replies_by_parent: dict[str, list] = {}
    top_level = []
    for c in comments:
        pid = c.get("parent_id")
        if pid:
            replies_by_parent.setdefault(str(pid), []).append(c)
        else:
            top_level.append(c)
    for c in top_level:
        c["replies"] = replies_by_parent.get(c["id"], [])

    return {"comments": top_level}


@router.post("/posts/{post_id}/comments")
async def create_comment(post_id: str, body: CreateComment, user=Depends(require_user), _csrf=Depends(require_csrf), _idem=Depends(require_idempotency)):
    post_id = validate_path_id(post_id, "post_id")
    check_rate(f"comment:{user['id']}", RL_COMMENT_LIMIT, RL_COMMENT_WINDOW,
               "Bạn bình luận quá nhanh. Vui lòng đợi chút rồi thử lại.")
    mod_result = await moderate_content_enhanced(body.content, user_id=str(user["id"]))
    status = mod_result["status"]
    mentions = _clean_mentions(body.mentions)

    MAX_COMMENTS_PER_POST = _cfg.MAX_COMMENTS_PER_POST
    ph = db._ph
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT id FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            cnt = db._fetchone(conn, f"SELECT COUNT(*) c FROM comments WHERE post_id::text = {ph}", (post_id,))
            if cnt and int(db._row_to_dict(cnt)["c"]) >= MAX_COMMENTS_PER_POST:
                raise HTTPException(400, "Bài viết đã đạt giới hạn bình luận")
            row = db._fetchone(conn, f"""
                INSERT INTO comments (post_id, user_id, parent_id, content, moderation_status, mentions)
                VALUES ({ph}::uuid, {ph}::uuid, {ph}::uuid, {ph}, {ph}, {ph}::jsonb)
                RETURNING *
            """, (post_id, str(user["id"]),
                  body.parent_id if body.parent_id else None,
                  body.content, status, json.dumps(mentions, ensure_ascii=False)))
            post_owner = db._fetchone(conn, f"SELECT user_id FROM posts WHERE id::text = {ph}", (post_id,))
            parent_author = None
            if body.parent_id:
                pa = db._fetchone(conn, f"SELECT user_id FROM comments WHERE id::text = {ph}", (body.parent_id,))
                if pa:
                    parent_author = str(pa["user_id"])
        return row, post_owner, parent_author
    row, post_owner, parent_author = await asyncio.to_thread(_query)

    log_moderation("comment", str(db._row_to_dict(row)["id"]), status, mod_result, auto=True)

    if status == "approved":
        def _notify_comment():
            me = str(user["id"])
            owner_id = str(post_owner["user_id"]) if post_owner else None
            preview = body.content[:80] + ("..." if len(body.content) > 80 else "")
            if owner_id and owner_id != me:
                create_notification(
                    owner_id, "comment",
                    f"{user.get('display_name', 'Ai đó')} đã bình luận bài viết của bạn",
                    body=preview, ref_type="post", ref_id=post_id, actor_id=me,
                )
            if parent_author and parent_author != me and parent_author != owner_id:
                create_notification(
                    parent_author, "comment",
                    f"{user.get('display_name', 'Ai đó')} đã trả lời bình luận của bạn",
                    body=preview, ref_type="post", ref_id=post_id, actor_id=me,
                )
            _notify_mentions(mentions, str(user["id"]), user.get("display_name"), post_id, body.content)
        await asyncio.to_thread(_notify_comment)

    return {"comment": _format_comment(db._row_to_dict(row))}


class EditComment(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = _strip_html_tags((v or "").strip())
        if len(v) < 2:
            raise ValueError("Bình luận quá ngắn")
        if len(v) > 2000:
            raise ValueError("Bình luận tối đa 2000 ký tự")
        return v


@router.put("/comments/{comment_id}")
async def edit_comment(comment_id: str, body: EditComment, user=Depends(require_user), _csrf=Depends(require_csrf)):
    comment_id = validate_path_id(comment_id, "comment_id")
    ph = db._ph
    uid = str(user["id"])
    COMMENT_EDIT_WINDOW_HOURS = _cfg.COMMENT_EDIT_WINDOW_HOURS
    def _check():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT user_id, created_at FROM comments WHERE id::text = {ph}", (comment_id,))
            if not row:
                raise HTTPException(404, "Bình luận không tồn tại")
            if str(row["user_id"]) != uid:
                raise HTTPException(403, "Bạn chỉ có thể sửa bình luận của mình")
            from datetime import datetime, timezone, timedelta
            created = row["created_at"]
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - created > timedelta(hours=COMMENT_EDIT_WINDOW_HOURS):
                raise HTTPException(400, "Chỉ có thể sửa bình luận trong 24 giờ đầu")
    await asyncio.to_thread(_check)
    mod_result = await moderate_content_enhanced(body.content, user_id=uid)
    def _update():
        with db._conn() as conn:
            db._execute(conn, f"""
                UPDATE comments SET content = {ph}, moderation_status = {ph}, updated_at = NOW()
                WHERE id::text = {ph}
            """, (body.content, mod_result["status"], comment_id))
            return db._fetchone(conn, f"""
                SELECT c.*, u.display_name, u.avatar_url
                FROM comments c JOIN users u ON u.id = c.user_id
                WHERE c.id::text = {ph}
            """, (comment_id,))
    updated = await asyncio.to_thread(_update)
    return {"comment": _format_comment(db._row_to_dict(updated))}


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    comment_id = validate_path_id(comment_id, "comment_id")
    check_rate(f"del:{user['id']}", RL_DELETE_LIMIT, RL_DELETE_WINDOW,
               "Bạn xóa quá nhanh. Vui lòng đợi chút.")
    ph = db._ph
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT user_id, post_id FROM comments WHERE id::text = {ph}", (comment_id,))
            if not row:
                raise HTTPException(404, "Bình luận không tồn tại")
            if str(row["user_id"]) != uid:
                raise HTTPException(403, "Bạn chỉ có thể xóa bình luận của mình")
            db._execute(conn, f"DELETE FROM comments WHERE id::text = {ph}", (comment_id,))
    await asyncio.to_thread(_query)
    return {"success": True}


# ── Q&A: câu trả lời hay nhất (chủ bài hỏi chọn 1 bình luận) ──

class BestAnswerBody(BaseModel):
    comment_id: Optional[str] = None  # None = bỏ chọn


@router.post("/posts/{post_id}/best-answer")
async def set_best_answer(post_id: str, body: BestAnswerBody, user=Depends(require_user), _csrf=Depends(require_csrf)):
    post_id = validate_path_id(post_id, "post_id")
    ph = db._ph
    def _query():
        with db._conn() as conn:
            post = db._fetchone(conn, f"SELECT user_id, post_type FROM posts WHERE id::text = {ph}", (post_id,))
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            d = db._row_to_dict(post)
            if str(d["user_id"]) != str(user["id"]):
                raise HTTPException(403, "Chỉ người hỏi mới chọn được câu trả lời hay")
            if body.comment_id:
                c = db._fetchone(conn, f"SELECT 1 FROM comments WHERE id::text = {ph} AND post_id::text = {ph}",
                                 (body.comment_id, post_id))
                if not c:
                    raise HTTPException(400, "Bình luận không thuộc bài này")
                db._execute(conn, f"UPDATE posts SET best_answer_id = {ph}::uuid WHERE id::text = {ph}", (body.comment_id, post_id))
            else:
                db._execute(conn, f"UPDATE posts SET best_answer_id = NULL WHERE id::text = {ph}", (post_id,))
    await asyncio.to_thread(_query)
    return {"best_answer_id": body.comment_id}


# ── Likes ──

@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    post_id = validate_path_id(post_id, "post_id")
    check_rate(f"like:{user['id']}", RL_LIKE_LIMIT, RL_LIKE_WINDOW,
               "Bạn thao tác quá nhanh. Vui lòng đợi chút.")
    ph = db._ph
    uid = str(user["id"])

    def _check_self_like():
        with db._conn() as conn:
            row = db._fetchone(conn, f"SELECT user_id FROM posts WHERE id::text = {ph}", (post_id,))
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            if str(row["user_id"]) == uid:
                raise HTTPException(400, "Không thể thích bài viết của chính mình")
    await asyncio.to_thread(_check_self_like)

    def _query():
        with db._conn() as conn:
            return db._fetchone(conn, f"""
                WITH removed AS (
                    DELETE FROM likes WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
                    RETURNING 1
                ),
                inserted AS (
                    INSERT INTO likes (user_id, post_id)
                    SELECT {ph}::uuid, {ph}::uuid
                    WHERE NOT EXISTS (SELECT 1 FROM removed)
                    ON CONFLICT DO NOTHING
                    RETURNING 1
                )
                SELECT
                    EXISTS (SELECT 1 FROM inserted) AS liked,
                    (SELECT like_count FROM posts WHERE id::text = {ph}) AS like_count,
                    (SELECT user_id FROM posts WHERE id::text = {ph}) AS post_owner
            """, (uid, post_id, uid, post_id, post_id, post_id))
    result = await asyncio.to_thread(_query)

    liked = result["liked"] if result else False
    like_count = result["like_count"] if result else 0
    post_owner = str(result["post_owner"]) if result and result["post_owner"] else None

    if liked and post_owner and post_owner != uid:
        def _notify_like():
            create_notification(
                post_owner, "like",
                f"{user.get('display_name', 'Ai đó')} đã thích bài viết của bạn",
                ref_type="post", ref_id=post_id, actor_id=uid,
            )
        await asyncio.to_thread(_notify_like)

    return {"liked": liked, "like_count": like_count}


# ── Bookmarks ──

@router.post("/posts/{post_id}/bookmark")
async def toggle_bookmark(post_id: str, user=Depends(require_user), _csrf=Depends(require_csrf)):
    post_id = validate_path_id(post_id, "post_id")
    check_rate(f"bookmark:{user['id']}", RL_LIKE_LIMIT, RL_LIKE_WINDOW,
               "Bạn thao tác quá nhanh. Vui lòng đợi chút.")
    ph = db._ph
    uid = str(user["id"])
    def _query():
        with db._conn() as conn:
            deleted = db._fetchone(conn, f"""
                DELETE FROM bookmarks WHERE user_id = {ph}::uuid AND post_id = {ph}::uuid
                RETURNING 1
            """, (uid, post_id))
            if deleted:
                return False
            db._execute(conn, f"""
                INSERT INTO bookmarks (user_id, post_id) VALUES ({ph}::uuid, {ph}::uuid)
                ON CONFLICT DO NOTHING
            """, (uid, post_id))
            return True
    saved = await asyncio.to_thread(_query)
    return {"bookmarked": saved}


@router.get("/me/bookmarks")
async def get_my_bookmarks(
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50),
    user=Depends(require_user),
):
    ph = db._ph
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT p.*, u.display_name, u.avatar_url, u.username,
                       e.name as entity_name, e.type as entity_type
                FROM bookmarks b
                JOIN posts p ON p.id = b.post_id
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE b.user_id = {ph}::uuid AND p.moderation_status = 'approved'
                ORDER BY b.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (str(user["id"]), limit, offset))
    rows = await asyncio.to_thread(_query)
    posts = [_format_post(db._row_to_dict(r)) for r in rows]
    return {"posts": posts, "page": page, "has_more": len(posts) == limit}


# ── Image upload ──

@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...), user=Depends(require_user), _csrf=Depends(require_csrf)):
    check_rate(f"upload:{user['id']}", RL_UPLOAD_LIMIT, RL_UPLOAD_WINDOW,
               "Bạn tải ảnh quá nhanh. Vui lòng đợi chút rồi thử lại.")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Ảnh tối đa 5MB")

    # Không tin Content-Type client gửi — kiểm magic-byte thật (chặn SVG-script/polyglot).
    sniffed = storage.sniff_image_type(data)
    if not sniffed:
        raise HTTPException(400, "File không phải ảnh hợp lệ (JPEG/PNG/GIF/WebP)")

    try:
        url = await storage.upload_image(data, folder="posts", content_type=sniffed)
    except ValueError as e:
        logger.warning("Image upload rejected: %s", e)
        raise HTTPException(400, "File ảnh không hợp lệ hoặc quá lớn")
    return {"url": url}


# ── User profile + reputation (gamification, anti-inflation) ──

def _diminish(count: int, tiers: list[tuple[int, int]]) -> int:
    """Điểm giảm dần theo tier: [(số_lượng, điểm_mỗi_cái), ...]. Phần vượt tier cuối = 0."""
    pts, remaining = 0, count
    for tier_count, per_point in tiers:
        take = min(remaining, tier_count)
        pts += take * per_point
        remaining -= take
        if remaining <= 0:
            break
    return pts


def _calc_points(reviews: int, posts: int, photos: int,
                 followers: int, places: int, likes: int) -> int:
    """Công thức điểm chống lạm phát — dùng chung profile/leaderboard/suggested."""
    review_pts = _diminish(reviews, [(10, 5), (20, 3), (20, 1)])       # max 130
    post_pts = _diminish(max(posts - reviews, 0), [(15, 2), (15, 1)])  # max 45
    photo_pts = _diminish(photos, [(10, 3), (10, 1)])                  # max 40
    follower_pts = _diminish(followers, [(20, 1)])                     # max 20
    place_pts = _diminish(places, [(10, 2), (10, 1)])                  # max 30
    like_pts = _diminish(likes, [(50, 1)])                             # max 50
    return review_pts + post_pts + photo_pts + follower_pts + place_pts + like_pts
    # Tổng tối đa lý thuyết: 315 — Đại sứ (200+) cần đa dạng, không spam 1 loại được


def _level_for(points: int) -> tuple[int, str]:
    """Cấp độ danh tiếng theo điểm (dùng chung profile + leaderboard)."""
    if points >= 200: return 4, "Đại sứ"
    if points >= 80:  return 3, "Đóng góp tích cực"
    if points >= 20:  return 2, "Người đóng góp"
    return 1, "Người mới"


def _reputation(conn, user_id: str, posts: int, reviews: int) -> dict:
    """Danh tiếng compute-on-fly từ đóng-góp ĐÃ-DUYỆT (§1.4-safe, 0 lưu trữ).
    Gom thành 3 query thay vì 8 (N+1 fix)."""
    ph = db._ph
    def _v(row, col):
        return int(row[col]) if row and row[col] else 0

    agg = db._fetchone(conn, f"""
        SELECT
            COUNT(*) FILTER (WHERE (CASE WHEN jsonb_typeof(images)='array'
                THEN jsonb_array_length(images) ELSE 0 END) > 0) AS photos,
            COUNT(DISTINCT entity_id) FILTER (WHERE entity_id IS NOT NULL) AS places,
            COALESCE(SUM(CASE WHEN jsonb_typeof(likes)='number' THEN likes::int
                WHEN jsonb_typeof(likes)='array' THEN jsonb_array_length(likes) ELSE 0 END), 0) AS total_likes
        FROM posts WHERE user_id::text = {ph} AND moderation_status = 'approved'
    """, (user_id,))
    agg = db._row_to_dict(agg) if agg else {}
    photos = _v(agg, "photos")
    places = _v(agg, "places")
    likes = _v(agg, "total_likes")

    followers_row = db._fetchone(conn, f"SELECT COUNT(*) c FROM follows WHERE target_type='user' AND target_id={ph}", (user_id,))
    followers = _v(db._row_to_dict(followers_row) if followers_row else {}, "c")

    visit_agg = db._fetchone(conn, f"""
        SELECT COUNT(*) AS visit_count,
               COUNT(DISTINCT e.area) FILTER (WHERE e.area IS NOT NULL) AS areas,
               (SELECT EXTRACT(DAY FROM NOW() - created_at)::int FROM users WHERE id::text = {ph}) AS age_days
        FROM user_visits uv LEFT JOIN entities e ON e.id = uv.entity_id
        WHERE uv.user_id::text = {ph} AND uv.status = 'visited'
    """, (user_id, user_id))
    visit_agg = db._row_to_dict(visit_agg) if visit_agg else {}
    visits = _v(visit_agg, "visit_count")
    areas_visited = _v(visit_agg, "areas")
    account_age_days = _v(visit_agg, "age_days")

    points = _calc_points(reviews, posts, photos, followers, places, likes)
    level, label = _level_for(points)
    badges = []
    if reviews >= 1:    badges.append({"id": "first_review", "label": "Đánh giá đầu tiên", "icon": "✍️"})
    if reviews >= 25:   badges.append({"id": "review_master", "label": "Bậc thầy đánh giá", "icon": "⭐"})
    if photos >= 10:    badges.append({"id": "photographer", "label": "Nhiếp ảnh cộng đồng", "icon": "📸"})
    if places >= 10:    badges.append({"id": "explorer", "label": "Người khám phá", "icon": "🧭"})
    if followers >= 20: badges.append({"id": "popular", "label": "Được yêu thích", "icon": "💛"})
    if likes >= 50:     badges.append({"id": "quality", "label": "Nội dung chất lượng", "icon": "🏆"})
    if places >= 3 and reviews >= 5 and photos >= 3:
        badges.append({"id": "allrounder", "label": "Đa năng", "icon": "🌟"})
    if visits >= 10:    badges.append({"id": "traveler", "label": "Lữ khách", "icon": "🎒"})
    if areas_visited >= 3: badges.append({"id": "local", "label": "Người địa phương", "icon": "🏡"})
    if account_age_days >= 180: badges.append({"id": "veteran", "label": "Thành viên kỳ cựu", "icon": "🎖️"})
    return {"points": points, "level": level, "level_label": label, "badges": badges,
            "photos": photos, "followers": followers, "places": places, "likes": likes}


@router.get("/users/{user_id}")
async def get_user_profile(user_id: str, user=Depends(get_current_user)):
    validate_path_id(user_id, "user_id")
    ph = db._ph
    _is_uuid = len(user_id) == 36 and user_id.count("-") == 4
    viewer_id = str(user["id"]) if user else None

    def _query():
        with db._conn() as conn:
            if _is_uuid:
                profile = db._fetchone(conn, f"""
                    SELECT id, display_name, avatar_url, cover_url, bio, username, created_at
                    FROM users WHERE id::text = {ph} AND is_active = TRUE
                """, (user_id,))
            else:
                profile = db._fetchone(conn, f"""
                    SELECT id, display_name, avatar_url, cover_url, bio, username, created_at
                    FROM users WHERE lower(username) = {ph} AND is_active = TRUE
                """, (user_id.lower(),))

            if not profile:
                raise HTTPException(404, "Người dùng không tồn tại")

            profile = db._row_to_dict(profile)
            resolved_id = str(profile["id"])
            is_self = viewer_id == resolved_id

            if not is_self and viewer_id:
                is_blocked = db._fetchone(conn, f"""
                    SELECT 1 FROM blocks
                    WHERE (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
                       OR (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
                """, (viewer_id, resolved_id, resolved_id, viewer_id))
                if is_blocked:
                    return "blocked", profile, None, None, None, None, None, None, None

            counts = db._fetchone(conn, f"""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE post_type = 'review') as reviews
                FROM posts
                WHERE user_id::text = {ph} AND moderation_status = 'approved'
            """, (resolved_id,))
            posts_n = counts["total"] if counts else 0
            reviews_n = counts["reviews"] if counts else 0

            reputation = _reputation(conn, resolved_id, posts_n, reviews_n)
            following_row = db._fetchone(conn, f"""
                SELECT COUNT(*) as c FROM follows
                WHERE follower_id::text = {ph} AND target_type = 'user'
            """, (resolved_id,))

            privacy = None
            try:
                prow = db._fetchone(conn, f"SELECT user_id, profile_visibility, show_activity, show_saved FROM user_privacy WHERE user_id = {ph}::uuid", (resolved_id,))
                if prow:
                    privacy = db._row_to_dict(prow)
            except Exception:
                logger.warning("Failed to load privacy settings for user %s", resolved_id)

            vis = privacy["profile_visibility"] if privacy else "public"
            is_follower = False
            if not is_self and vis != "public" and viewer_id:
                frow = db._fetchone(conn, f"""
                    SELECT 1 FROM follows
                    WHERE follower_id = {ph}::uuid AND target_type = 'user' AND target_id = {ph}
                """, (viewer_id, resolved_id))
                is_follower = frow is not None

        return vis, profile, is_self, is_follower, reputation, following_row, posts_n, reviews_n, privacy

    result = await asyncio.to_thread(_query)
    vis, profile, is_self, is_follower, reputation, following_row, posts_n, reviews_n, privacy = result

    if vis == "blocked":
        return {
            "user": {
                "id": str(profile["id"]),
                "username": profile.get("username"),
                "display_name": profile["display_name"],
                "avatar_url": profile.get("avatar_url"),
                "is_blocked": True,
            },
        }

    follower_count = reputation["followers"] if reputation else 0

    if vis == "private" and not is_self and not is_follower:
        return {
            "user": {
                "id": str(profile["id"]),
                "username": profile.get("username"),
                "display_name": profile["display_name"],
                "avatar_url": profile.get("avatar_url"),
                "cover_url": profile.get("cover_url"),
                "bio": "",
                "created_at": str(profile["created_at"]),
                "stats": {"posts": 0, "reviews": 0, "followers": follower_count, "following": 0},
                "reputation": None,
                "is_private": True,
            },
        }

    show_activity = privacy["show_activity"] if privacy else True
    show_saved = privacy["show_saved"] if privacy else True

    return {
        "user": {
            "id": str(profile["id"]),
            "username": profile.get("username"),
            "display_name": profile["display_name"],
            "avatar_url": profile.get("avatar_url"),
            "cover_url": profile.get("cover_url"),
            "bio": profile.get("bio", ""),
            "created_at": str(profile["created_at"]),
            "stats": {
                "posts": posts_n,
                "reviews": reviews_n,
                "followers": follower_count,
                "following": following_row["c"] if following_row else 0,
            },
            "reputation": reputation,
            "show_activity": show_activity,
            "show_saved": show_saved,
        },
    }


@router.get("/users/{user_id}/posts")
async def get_user_posts(
    user_id: str,
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50),
):
    validate_path_id(user_id, "user_id")
    ph = db._ph
    uid = await asyncio.to_thread(_resolve_user_id, user_id)
    if not uid:
        raise HTTPException(404, "Người dùng không tồn tại")
    offset = (page - 1) * limit
    def _query():
        with db._conn() as conn:
            return db._fetchall(conn, f"""
                SELECT p.*, u.display_name, u.avatar_url, u.username,
                       e.name as entity_name, e.type as entity_type
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.user_id::text = {ph} AND p.moderation_status = 'approved'
                ORDER BY p.created_at DESC
                LIMIT {ph} OFFSET {ph}
            """, (uid, limit, offset))
    rows = await asyncio.to_thread(_query)
    posts = [_format_post(db._row_to_dict(r)) for r in rows]
    return {"posts": posts, "page": page, "has_more": len(posts) == limit}


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


def _resolve_user_id(user_id: str) -> str | None:
    """Resolve a user_id param (UUID or username) to actual UUID string."""
    _is_uuid = len(user_id) == 36 and user_id.count("-") == 4
    if _is_uuid:
        return user_id
    ph = db._ph
    with db._conn() as conn:
        row = db._fetchone(conn,
            f"SELECT id FROM users WHERE lower(username) = {ph} AND is_active = TRUE",
            (user_id.lower(),))
    return str(row["id"]) if row else None


def _format_post(row: dict) -> dict:
    images = row.get("images", [])
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except (json.JSONDecodeError, ValueError, TypeError):
            images = []

    def _jlist(val):
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, ValueError, TypeError):
                val = []
        return val if isinstance(val, list) else []

    def _jlist_obj(val):
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, ValueError, TypeError):
                val = None
        return val if isinstance(val, dict) else None
    mentions = _jlist(row.get("mentions"))
    hashtags = _jlist(row.get("hashtags"))

    return {
        "id": str(row["id"]),
        "user_id": str(row.get("user_id", "")),
        "content": row["content"],
        "mentions": mentions,
        "hashtags": hashtags,
        "best_answer_id": str(row["best_answer_id"]) if row.get("best_answer_id") else None,
        "repost_of": str(row["repost_of"]) if row.get("repost_of") else None,
        "repost": _jlist_obj(row.get("repost_snapshot")),
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
        "username": row.get("username"),
        "avatar": row.get("avatar_url"),
        "entity_id": row.get("entity_id"),
        "entity_name": row.get("entity_name"),
        "entity_type": row.get("entity_type"),
        "author": {
            "id": str(row.get("user_id", "")),
            "display_name": row.get("display_name", ""),
            "username": row.get("username"),
            "avatar_url": row.get("avatar_url"),
        },
        "entity": {
            "id": row.get("entity_id"),
            "name": row.get("entity_name"),
            "type": row.get("entity_type"),
        } if row.get("entity_id") else None,
    }


def _format_comment(row: dict) -> dict:
    mentions = row.get("mentions", [])
    if isinstance(mentions, str):
        try:
            mentions = json.loads(mentions)
        except (json.JSONDecodeError, ValueError, TypeError):
            mentions = []
    return {
        "id": str(row["id"]),
        "content": row["content"],
        "mentions": mentions if isinstance(mentions, list) else [],
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
    return _format_post(row)
