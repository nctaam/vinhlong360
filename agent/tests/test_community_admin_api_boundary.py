"""Ranh giới mặt QUẢN TRỊ của gói `agent/community/` (lát 1 đợt cắt module, 2026-08-29).

Gói miền cộng đồng nay ĐỦ HAI MẶT theo khuôn `agent/cases/` và `agent/entities/`:
`api.py` (công khai) + `admin_api.py` (quản trị, lát này — 42 route kiểm duyệt
UGC, appeals/reports, quản user, analytics/export user–post).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from community import admin_api  # noqa: E402

SRC = Path(admin_api.__file__).resolve()


def test_router_khong_tu_mang_prefix_va_khong_tu_mang_auth():
    """Mount qua `admin.router.include_router(...)` — cha mang prefix "/admin"
    VÀ dependencies [require_admin, require_csrf]. Con tự mang nữa là
    /admin/admin hoặc auth chạy hai lần."""
    assert admin_api.router.prefix == ""
    assert admin_api.router.dependencies == []


def test_moi_route_len_app_duoi_admin_va_co_chot_auth():
    """AN NINH — kiểm bằng ĐO, không tin trí nhớ API: route con phải kế thừa
    require_admin + require_csrf từ router cha khi include."""
    import server

    app_routes = {r.path: r for r in server.app.routes if hasattr(r, "dependant")}
    thieu_route, thieu_auth = [], []
    for r in admin_api.router.routes:
        path = "/admin" + r.path
        if path not in app_routes:
            thieu_route.append(path)
            continue
        deps = {getattr(d.call, "__name__", "?")
                for d in app_routes[path].dependant.dependencies}
        if not {"require_admin", "require_csrf"} <= deps:
            thieu_auth.append((path, sorted(deps)))
    assert not thieu_route, f"route không lên app: {thieu_route[:5]}"
    assert not thieu_auth, f"route THIẾU chốt auth kế thừa: {thieu_auth[:5]}"


def test_approve_route_binds_public_handler_without_query_params():
    """The approval endpoint must expose the public handler's request shape."""
    import server

    route = next(
        r for r in server.app.routes
        if r.path == "/admin/moderation/{post_id}/approve" and "POST" in r.methods
    )

    assert route.endpoint is admin_api.approve_post
    assert not route.dependant.query_params


def test_KHONG_import_nguoc():
    # community.api KHÔNG bị cấm về nguyên tắc (cùng gói, chiều đó có sẵn ở
    # api.py), nhưng admin_api.py hiện không cần — mọi hạ tầng dùng chung đi
    # qua admin_common/auth_middleware/database/notifications.
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    XAU = ("server", "admin", "public_api", "chat", "llmops", "identity")
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += [a.name for a in n.names if a.name.split(".")[0] in XAU]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in XAU:
                bad.append(n.module)
    assert not bad, f"admin_api.py import xấu: {bad}"


def test_khong_con_dinh_nghia_o_admin():
    import admin

    src = Path(admin.__file__).resolve().read_text(encoding="utf-8")
    tree = ast.parse(src)
    ten = {n.name for n in tree.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    DA_DOI = (
        "qa_queue", "qa_set_best_answer", "admin_review_response",
        "get_review_response", "user_engagement_stats", "user_growth",
        "export_users_csv", "export_posts_csv", "moderation_queue",
        "approve_post", "reject_post", "batch_moderation", "moderation_history",
        "feature_post", "delete_review_response", "add_moderation_note",
        "get_moderation_notes", "moderation_stats", "admin_content_search",
        "admin_post_detail", "list_appeals", "approve_appeal", "reject_appeal",
        "admin_list_comments", "admin_delete_comment", "content_stats",
        "get_reports", "bulk_report_action", "resolve_report", "dismiss_report",
        "list_users", "admin_user_detail", "ban_user", "unban_user",
        "bulk_ban_users", "bulk_unban_users", "set_user_role", "add_user_note",
        "get_user_notes", "delete_user_note", "admin_user_mutes",
        "admin_user_reactions",
    )
    assert len(DA_DOI) == 42
    con_lai = [f for f in DA_DOI if f in ten]
    assert not con_lai, f"admin.py vẫn còn định nghĩa: {con_lai}"
