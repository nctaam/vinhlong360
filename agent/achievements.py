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
    {"id": "first_post",    "name": "Bài viết đầu tiên", "description": "Đăng bài viết đầu tiên",   "icon": "pencil",       "category": "content",  "target": 1,   "metric": "posts"},
    {"id": "writer_10",     "name": "Nhà văn",           "description": "Đăng 10 bài viết",          "icon": "file-text",    "category": "content",  "target": 10,  "metric": "posts"},
    {"id": "reviewer_5",    "name": "Nhà phê bình",      "description": "Viết 5 đánh giá",           "icon": "list",         "category": "content",  "target": 5,   "metric": "reviews"},
    {"id": "review_master", "name": "Bậc thầy đánh giá", "description": "Viết 25 đánh giá",          "icon": "award",        "category": "content",  "target": 25,  "metric": "reviews"},
    {"id": "photographer",  "name": "Nhiếp ảnh gia",     "description": "Đăng 10 bài có ảnh",        "icon": "camera",       "category": "content",  "target": 10,  "metric": "photos"},
    {"id": "explorer_5",    "name": "Nhà thám hiểm",     "description": "Ghé thăm 5 địa điểm",       "icon": "compass",      "category": "explorer", "target": 5,   "metric": "visits"},
    {"id": "explorer_20",   "name": "Lữ khách",          "description": "Ghé thăm 20 địa điểm",      "icon": "map",          "category": "explorer", "target": 20,  "metric": "visits"},
    {"id": "local_3",       "name": "Người địa phương",  "description": "Khám phá 3 khu vực",        "icon": "home",         "category": "explorer", "target": 3,   "metric": "areas"},
    {"id": "social_10",     "name": "Kết nối",           "description": "Có 10 người theo dõi",      "icon": "users",        "category": "social",   "target": 10,  "metric": "followers"},
    {"id": "social_50",     "name": "Ảnh hưởng",         "description": "Có 50 người theo dõi",      "icon": "heart",        "category": "social",   "target": 50,  "metric": "followers"},
    {"id": "helpful_5",     "name": "Hữu ích",           "description": "Có 5 câu trả lời hay nhất", "icon": "bulb",         "category": "social",   "target": 5,   "metric": "best_answers"},
    {"id": "streak_7",      "name": "Chăm chỉ",          "description": "Đăng nhập 7 ngày liên tiếp","icon": "flame",        "category": "veteran",  "target": 7,   "metric": "login_streak"},
    {"id": "streak_30",     "name": "Kiên trì",          "description": "Đăng nhập 30 ngày liên tiếp","icon": "shield-check","category": "veteran",  "target": 30,  "metric": "login_streak"},
    {"id": "veteran_6m",    "name": "Lão làng",          "description": "Thành viên 6 tháng",        "icon": "trophy",       "category": "veteran",  "target": 180, "metric": "account_age_days"},
    {"id": "allrounder",    "name": "Đa tài",            "description": "Mở khóa mỗi nhóm ít nhất 1 thành tích", "icon": "sparkle", "category": "special", "target": 4, "metric": "categories_covered"},
]

_ACH_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}
_METRIC_ACHIEVEMENTS = tuple(a for a in ACHIEVEMENTS if a["id"] != "allrounder")
import threading

_CATEGORIES = ("content", "explorer", "social", "veteran")  # nhóm để tính allrounder
_metrics_ctx = threading.local()


def _compute_metrics(conn, user_id: str) -> dict[str, int]:
    """Tính mọi chỉ số cho 1 user trong 1 truy vấn SQL hợp nhất."""
    ph = db._ph
    row = db._fetchone(conn, f"""
        WITH post_stats AS (
            SELECT COUNT(*) AS posts,
                   COUNT(*) FILTER (WHERE post_type = 'review') AS reviews,
                   COUNT(*) FILTER (WHERE (CASE WHEN jsonb_typeof(images)='array'
                       THEN jsonb_array_length(images) ELSE 0 END) > 0) AS photos
            FROM posts WHERE user_id::text = {ph}
            AND moderation_status = 'approved' AND deleted_at IS NULL
        ),
        visit_stats AS (
            SELECT COUNT(*) AS visits,
                   COUNT(DISTINCT e.area) FILTER (WHERE e.area IS NOT NULL) AS areas
            FROM user_visits uv LEFT JOIN entities e ON e.id = uv.entity_id
            WHERE uv.user_id::text = {ph} AND uv.status = 'visited'
        ),
        user_stats AS (
            SELECT EXTRACT(DAY FROM NOW() - created_at)::int AS age_days,
                   COALESCE(login_streak, 0) AS login_streak
            FROM users WHERE id::text = {ph}
        )
        SELECT ps.posts, ps.reviews, ps.photos,
               vs.visits, vs.areas,
               COALESCE(us.age_days, 0) AS age_days,
               COALESCE(us.login_streak, 0) AS login_streak,
               (SELECT COUNT(*) FROM follows
                WHERE target_type='user' AND target_id={ph}) AS followers,
               (SELECT COUNT(*) FROM posts p
                JOIN comments c2 ON c2.id = p.best_answer_id
                WHERE c2.user_id::text = {ph} AND p.deleted_at IS NULL) AS best_answers
        FROM post_stats ps
        CROSS JOIN visit_stats vs
        LEFT JOIN user_stats us ON TRUE
    """, (user_id, user_id, user_id, user_id, user_id))
    d = db._row_to_dict(row) if row else {}

    def _i(k: str) -> int:
        return int(d.get(k) or 0)

    return {
        "posts": _i("posts"),
        "reviews": _i("reviews"),
        "photos": _i("photos"),
        "followers": _i("followers"),
        "visits": _i("visits"),
        "areas": _i("areas"),
        "account_age_days": _i("age_days"),
        "best_answers": _i("best_answers"),
        "login_streak": _i("login_streak"),
    }


def _maybe_award_allrounder(earned_ids: set[str], _award) -> None:
    """allrounder: đủ ≥1 thành tích ở mỗi nhóm content/explorer/social/veteran.
    (extracted verbatim từ check_achievements — không đổi logic/thứ tự.)"""
    if "allrounder" not in earned_ids:
        cats = {_ACH_BY_ID[i]["category"] for i in earned_ids if i in _ACH_BY_ID}
        if all(c in cats for c in _CATEGORIES):
            _award("allrounder")


def _notify_new_achievements(user_id: str, newly: list[dict]) -> None:
    """Thông báo (thời gian thực khi hook gọi notify=True).
    (extracted verbatim từ check_achievements — không đổi logic/thứ tự.)"""
    from notifications import create_notification
    for a in newly:
        try:
            create_notification(
                user_id=user_id,
                notif_type="achievement",
                title=f"Mở khóa thành tích: {a['name']}",
                body=a.get("description") or "",
                ref_type="achievement",
                ref_id=a["id"],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("achievement notify failed (%s/%s): %s", user_id, a["id"], e)


def check_achievements(conn, user_id: str, notify: bool = True) -> list[dict]:
    """Award thành tích mới đạt ngưỡng. Trả về danh sách def mới mở khóa.
    Idempotent qua ON CONFLICT DO NOTHING. allrounder tính sau (dựa trên nhóm
    đã có, kể cả mới mở khóa lượt này)."""
    ph = db._ph
    metrics = _compute_metrics(conn, user_id)
    _metrics_ctx.last = (id(conn), str(user_id), metrics)

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
    for a in _METRIC_ACHIEVEMENTS:
        if a["id"] in earned_ids:
            continue
        if metrics.get(a["metric"], 0) >= a["target"]:
            _award(a["id"])

    # 2) allrounder: đủ ≥1 thành tích ở mỗi nhóm content/explorer/social/veteran
    _maybe_award_allrounder(earned_ids, _award)

    # 3) Thông báo (thời gian thực khi hook gọi notify=True)
    if notify and newly:
        _notify_new_achievements(user_id, newly)

    return newly


@router.get("/me/achievements",
            summary="Achievements for current user",
            description="Tất cả thành tích với trạng thái mở khóa + tiến độ hiện tại. Award-on-read (không thông báo).")
async def get_my_achievements(user=Depends(require_user)):
    uid = str(user["id"])

    def _query():
        with db._conn() as conn:
            _metrics_ctx.last = None
            # award-on-read, im lặng (tránh spam thông báo lần đầu)
            check_achievements(conn, uid, notify=False)
            cached = getattr(_metrics_ctx, "last", None)
            _metrics_ctx.last = None
            if cached and cached[0] == id(conn) and cached[1] == uid:
                metrics = cached[2]
            else:
                metrics = _compute_metrics(conn, uid)
            ph = db._ph
            rows = db._fetchall(conn, f"""
                SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id::text = {ph}
            """, (uid,))
            unlocked = {(d := db._row_to_dict(r))["achievement_id"]: d["unlocked_at"] for r in rows}
            return metrics, unlocked

    metrics, unlocked = await asyncio.to_thread(_query)

    earned_cats = {_ACH_BY_ID[i]["category"] for i in unlocked if i in _ACH_BY_ID}
    categories_covered_count = sum(1 for c in _CATEGORIES if c in earned_cats)
    out = []
    for a in ACHIEVEMENTS:
        earned = a["id"] in unlocked
        if a["metric"] == "categories_covered":
            current = categories_covered_count
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
