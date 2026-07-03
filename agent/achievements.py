"""Hệ thống thành tích (achievements) — Wave 3 W3.1.

Thành tích = bản bền vững, có mốc thời gian mở khóa + thông báo, mở rộng từ
badge compute-on-fly (get_badge_progress). Chỉ số dùng lại đúng SQL của
get_badge_progress (social.py) + thêm best_answers, login_streak.

check_achievements(): tính chỉ số, so ngưỡng, INSERT ON CONFLICT DO NOTHING vào
user_achievements, trả về thành tích MỚI mở khóa; gửi thông báo nếu notify=True.
Endpoint GET /api/me/achievements award-on-read (notify=False) để tự chữa lành
kể cả khi chưa có hook; hook (Task 3) gọi notify=True cho thông báo thời gian thực.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends

from database import db
from auth_middleware import require_user, require_pg as _require_pg

logger = logging.getLogger("achievements")

router = APIRouter(prefix="/api", tags=["achievements"], dependencies=[Depends(_require_pg)])

# metric = khóa trong dict trả về bởi _compute_metrics; target = ngưỡng đạt.
ACHIEVEMENTS: list[dict] = [
    {"id": "first_post",    "name": "Bài viết đầu tiên", "description": "Đăng bài viết đầu tiên",   "icon": "📝", "category": "content",  "target": 1,   "metric": "posts"},
    {"id": "writer_10",     "name": "Nhà văn",           "description": "Đăng 10 bài viết",          "icon": "✒️", "category": "content",  "target": 10,  "metric": "posts"},
    {"id": "reviewer_5",    "name": "Nhà phê bình",      "description": "Viết 5 đánh giá",           "icon": "📋", "category": "content",  "target": 5,   "metric": "reviews"},
    {"id": "review_master", "name": "Bậc thầy đánh giá", "description": "Viết 25 đánh giá",          "icon": "⭐", "category": "content",  "target": 25,  "metric": "reviews"},
    {"id": "photographer",  "name": "Nhiếp ảnh gia",     "description": "Đăng 10 bài có ảnh",        "icon": "📸", "category": "content",  "target": 10,  "metric": "photos"},
    {"id": "explorer_5",    "name": "Nhà thám hiểm",     "description": "Ghé thăm 5 địa điểm",       "icon": "🧭", "category": "explorer", "target": 5,   "metric": "visits"},
    {"id": "explorer_20",   "name": "Lữ khách",          "description": "Ghé thăm 20 địa điểm",      "icon": "🎒", "category": "explorer", "target": 20,  "metric": "visits"},
    {"id": "local_3",       "name": "Người địa phương",  "description": "Khám phá 3 khu vực",        "icon": "🏡", "category": "explorer", "target": 3,   "metric": "areas"},
    {"id": "social_10",     "name": "Kết nối",           "description": "Có 10 người theo dõi",      "icon": "🤝", "category": "social",   "target": 10,  "metric": "followers"},
    {"id": "social_50",     "name": "Ảnh hưởng",         "description": "Có 50 người theo dõi",      "icon": "💫", "category": "social",   "target": 50,  "metric": "followers"},
    {"id": "helpful_5",     "name": "Hữu ích",           "description": "Có 5 câu trả lời hay nhất", "icon": "💡", "category": "social",   "target": 5,   "metric": "best_answers"},
    {"id": "streak_7",      "name": "Chăm chỉ",          "description": "Đăng nhập 7 ngày liên tiếp","icon": "🔥", "category": "veteran",  "target": 7,   "metric": "login_streak"},
    {"id": "streak_30",     "name": "Kiên trì",          "description": "Đăng nhập 30 ngày liên tiếp","icon": "🏅","category": "veteran",  "target": 30,  "metric": "login_streak"},
    {"id": "veteran_6m",    "name": "Lão làng",          "description": "Thành viên 6 tháng",        "icon": "🎖️","category": "veteran",  "target": 180, "metric": "account_age_days"},
    {"id": "allrounder",    "name": "Đa tài",            "description": "Mở khóa mỗi nhóm ít nhất 1 thành tích", "icon": "🌟", "category": "special", "target": 4, "metric": "categories_covered"},
]

_ACH_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}
_CATEGORIES = ("content", "explorer", "social", "veteran")  # nhóm để tính allrounder


def _compute_metrics(conn, user_id: str) -> dict[str, int]:
    """Tính mọi chỉ số cho 1 user. Dùng lại đúng SQL của get_badge_progress
    (social.py:3406-3472) + best_answers + login_streak."""
    ph = db._ph
    post_stats = db._fetchone(conn, f"""
        SELECT COUNT(*) AS posts,
               COUNT(*) FILTER (WHERE post_type = 'review') AS reviews,
               COUNT(*) FILTER (WHERE (CASE WHEN jsonb_typeof(images)='array'
                   THEN jsonb_array_length(images) ELSE 0 END) > 0) AS photos
        FROM posts WHERE user_id::text = {ph}
        AND moderation_status = 'approved' AND deleted_at IS NULL
    """, (user_id,))
    ps = db._row_to_dict(post_stats) if post_stats else {}

    follower_row = db._fetchone(conn, f"""
        SELECT COUNT(*) c FROM follows
        WHERE target_type='user' AND target_id={ph}
    """, (user_id,))
    followers = int(db._row_to_dict(follower_row).get("c", 0)) if follower_row else 0

    visit_row = db._fetchone(conn, f"""
        SELECT COUNT(*) AS visits,
               COUNT(DISTINCT e.area) FILTER (WHERE e.area IS NOT NULL) AS areas,
               (SELECT EXTRACT(DAY FROM NOW() - created_at)::int FROM users WHERE id::text = {ph}) AS age_days
        FROM user_visits uv LEFT JOIN entities e ON e.id = uv.entity_id
        WHERE uv.user_id::text = {ph} AND uv.status = 'visited'
    """, (user_id, user_id))
    vd = db._row_to_dict(visit_row) if visit_row else {}

    best_row = db._fetchone(conn, f"""
        SELECT COUNT(*) c FROM posts p
        JOIN comments c2 ON c2.id = p.best_answer_id
        WHERE c2.user_id::text = {ph} AND p.deleted_at IS NULL
    """, (user_id,))
    best_answers = int(db._row_to_dict(best_row).get("c", 0)) if best_row else 0

    streak_row = db._fetchone(conn, f"""
        SELECT COALESCE(login_streak, 0) AS s FROM users WHERE id::text = {ph}
    """, (user_id,))
    login_streak = int(db._row_to_dict(streak_row).get("s", 0)) if streak_row else 0

    def _i(d, k):
        return int(d.get(k) or 0)

    return {
        "posts": _i(ps, "posts"),
        "reviews": _i(ps, "reviews"),
        "photos": _i(ps, "photos"),
        "followers": followers,
        "visits": _i(vd, "visits"),
        "areas": _i(vd, "areas"),
        "account_age_days": _i(vd, "age_days"),
        "best_answers": best_answers,
        "login_streak": login_streak,
    }


def check_achievements(conn, user_id: str, notify: bool = True) -> list[dict]:
    """Award thành tích mới đạt ngưỡng. Trả về danh sách def mới mở khóa.
    Idempotent qua ON CONFLICT DO NOTHING. allrounder tính sau (dựa trên nhóm
    đã có, kể cả mới mở khóa lượt này)."""
    ph = db._ph
    metrics = _compute_metrics(conn, user_id)

    earned_rows = db._fetchall(conn, f"""
        SELECT achievement_id FROM user_achievements WHERE user_id::text = {ph}
    """, (user_id,))
    earned_ids = {db._row_to_dict(r)["achievement_id"] for r in earned_rows}

    newly: list[dict] = []

    def _award(ach_id: str):
        db._execute(conn, f"""
            INSERT INTO user_achievements (user_id, achievement_id)
            VALUES ({ph}::uuid, {ph}) ON CONFLICT DO NOTHING
        """, (user_id, ach_id))
        earned_ids.add(ach_id)
        newly.append(_ACH_BY_ID[ach_id])

    # 1) Thành tích chỉ-số thường (bỏ allrounder tới cuối)
    for a in ACHIEVEMENTS:
        if a["id"] == "allrounder" or a["id"] in earned_ids:
            continue
        if metrics.get(a["metric"], 0) >= a["target"]:
            _award(a["id"])

    # 2) allrounder: đủ ≥1 thành tích ở mỗi nhóm content/explorer/social/veteran
    if "allrounder" not in earned_ids:
        cats = {_ACH_BY_ID[i]["category"] for i in earned_ids if i in _ACH_BY_ID}
        if all(c in cats for c in _CATEGORIES):
            _award("allrounder")

    # 3) Thông báo (thời gian thực khi hook gọi notify=True)
    if notify and newly:
        from notifications import create_notification
        for a in newly:
            try:
                create_notification(
                    user_id=user_id,
                    notif_type="achievement",
                    title=f"{a['icon']} Mở khóa thành tích: {a['name']}",
                    body=a.get("description") or "",
                    ref_type="achievement",
                    ref_id=a["id"],
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("achievement notify failed (%s/%s): %s", user_id, a["id"], e)

    return newly


@router.get("/me/achievements",
            summary="Achievements for current user",
            description="Tất cả thành tích với trạng thái mở khóa + tiến độ hiện tại. Award-on-read (không thông báo).")
async def get_my_achievements(user=Depends(require_user)):
    uid = str(user["id"])

    def _query():
        with db._conn() as conn:
            # award-on-read, im lặng (tránh spam thông báo lần đầu)
            check_achievements(conn, uid, notify=False)
            metrics = _compute_metrics(conn, uid)
            ph = db._ph
            rows = db._fetchall(conn, f"""
                SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id::text = {ph}
            """, (uid,))
            unlocked = {db._row_to_dict(r)["achievement_id"]: db._row_to_dict(r)["unlocked_at"] for r in rows}
            return metrics, unlocked

    metrics, unlocked = await asyncio.to_thread(_query)

    out = []
    for a in ACHIEVEMENTS:
        earned = a["id"] in unlocked
        if a["metric"] == "categories_covered":
            earned_cats = {_ACH_BY_ID[i]["category"] for i in unlocked if i in _ACH_BY_ID}
            current = sum(1 for c in _CATEGORIES if c in earned_cats)
        else:
            current = metrics.get(a["metric"], 0)
        out.append({
            "id": a["id"], "name": a["name"], "description": a["description"],
            "icon": a["icon"], "category": a["category"],
            "current": min(current, a["target"]), "target": a["target"],
            "earned": earned,
            "unlocked_at": str(unlocked[a["id"]]) if earned else None,
        })

    return {"achievements": out, "earned_count": len(unlocked), "total": len(ACHIEVEMENTS)}
