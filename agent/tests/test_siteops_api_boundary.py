"""Ranh giới gói `agent/siteops/` (lát 3 đợt cắt module, 2026-08-29).

Gói miền VẬN HÀNH SITE đủ HAI MẶT theo khuôn `agent/cases/`, `agent/entities/`,
`agent/community/`, `agent/itineraries/`: `api.py` (2 route public đọc:
site-settings, announcements active) + `admin_api.py` (22 route quản trị:
data-quality ×6, system-health, backup-status, ops-summary, backup-trigger,
export toàn-DB, site-settings ×7, announcements ×4).

Khuôn test theo test_itineraries_api_boundary.py: auth đo dependant lúc
runtime, prefix/deps rỗng, cấm import ngược, nhà cũ hết định nghĩa (AST).
Khác biệt có chủ đích: `_ops_audit_snapshot` được PHÉP một import LƯỜI
`from admin import _AUDIT_FILE, _query_admin_audit_db` trong THÂN hàm —
hạ tầng audit (writer/rotation) ở lại admin.py, tiền lệ llmops/api.py; bài
test riêng ghim đúng một ngoại lệ đó, mọi import ngược khác vẫn cấm.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from siteops import admin_api  # noqa: E402
from siteops import api  # noqa: E402

SRC_ADMIN = Path(admin_api.__file__).resolve()
SRC_PUBLIC = Path(api.__file__).resolve()


def test_router_khong_tu_mang_prefix_va_khong_tu_mang_auth():
    """Hai mặt đều mount lồng: cha public mang prefix "/api", cha admin mang
    prefix "/admin" VÀ dependencies [require_admin, require_csrf]. Con tự mang
    nữa là /api/api hoặc auth chạy hai lần."""
    assert api.router.prefix == ""
    assert api.router.dependencies == []
    assert admin_api.router.prefix == ""
    assert admin_api.router.dependencies == []


def test_moi_route_admin_len_app_duoi_admin_va_co_chot_auth():
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


def test_moi_route_public_len_app_duoi_api():
    import server

    app_paths = {r.path for r in server.app.routes if hasattr(r, "dependant")}
    thieu = [
        "/api" + r.path
        for r in api.router.routes
        if "/api" + r.path not in app_paths
    ]
    assert not thieu, f"route public không lên app: {thieu}"


def _import_hits(src_path: Path, banned: tuple[str, ...]) -> list[tuple[str, int]]:
    """[(tên module bị cấm, lineno)] cho MỌI Import/ImportFrom trong file — kể
    cả import trong thân hàm (khác itineraries: ở đây có một ngoại lệ lười
    được ghim riêng, nên phải thấy hết rồi mới trừ)."""
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            hits += [(a.name, n.lineno) for a in n.names
                     if a.name.split(".")[0] in banned]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in banned:
                hits.append((n.module, n.lineno))
    return hits


def test_KHONG_import_nguoc_tru_dung_mot_ngoai_le_audit():
    XAU = ("server", "admin", "public_api", "chat", "community", "identity",
           "llmops", "entities", "itineraries", "mcp_server")
    # Mặt public: cấm tuyệt đối.
    assert _import_hits(SRC_PUBLIC, XAU) == [], "siteops/api.py import ngược"

    # Mặt admin: đúng MỘT ngoại lệ — import lười hạ tầng audit trong thân
    # _ops_audit_snapshot (tiền lệ llmops/api.py; test dưới ghim vị trí).
    hits = [h for h in _import_hits(SRC_ADMIN, XAU) if h[0] != "admin"]
    assert hits == [], f"siteops/admin_api.py import ngược ngoài ngoại lệ audit: {hits}"
    admin_hits = [h for h in _import_hits(SRC_ADMIN, ("admin",))]
    assert len(admin_hits) == 1, f"đúng MỘT import lười từ admin, thấy: {admin_hits}"


def test_ngoai_le_audit_nam_trong_than_ops_audit_snapshot():
    """Ngoại lệ import ngược phải là import LƯỜI trong THÂN _ops_audit_snapshot
    — không được leo lên cấp module (vòng import) hay lan sang hàm khác."""
    tree = ast.parse(SRC_ADMIN.read_text(encoding="utf-8"))
    for node in tree.body:
        assert not (isinstance(node, ast.ImportFrom) and node.module == "admin"), \
            "from admin import ... ở CẤP MODULE là vòng import"
    fn = next(n for n in tree.body
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
              and n.name == "_ops_audit_snapshot")
    lazy = [n for n in ast.walk(fn)
            if isinstance(n, ast.ImportFrom) and n.module == "admin"]
    assert len(lazy) == 1
    assert sorted(a.name for a in lazy[0].names) == ["_AUDIT_FILE", "_query_admin_audit_db"]


def test_khong_con_dinh_nghia_o_nha_cu():
    """admin.py + public_api.py hết định nghĩa các hàm/model đã dời — AST cấp
    module, không so chuỗi."""
    import admin
    import public_api

    DA_DOI = {
        Path(admin.__file__): (
            "data_quality_summary", "data_quality_review", "data_quality_apply",
            "data_quality_history", "data_quality_decision", "data_quality_rollback",
            "DataQualityApplyRequest", "DataQualityDecisionRequest",
            "_system_health_server", "_system_health_pg", "system_health",
            "_format_uptime", "_latest_backup_info", "backup_status",
            "_data_quality_ops_snapshot", "_quality_trend_meta",
            "_quality_trend_fetch_rows", "_quality_trend_budget_failure",
            "_quality_trend_process_latest", "_quality_trend_ops_snapshot",
            "_ops_moderation_snapshot", "_ops_audit_snapshot", "ops_summary",
            "trigger_backup", "export_data", "_admin_actor_label",
            "admin_get_all_settings", "admin_get_settings_by_category",
            "SettingUpdate", "admin_update_setting", "BulkSettingUpdate",
            "admin_bulk_update_settings", "admin_reset_category",
            "admin_site_settings_history", "admin_site_settings_rollback",
            "AnnouncementCreate", "AnnouncementUpdate", "list_announcements",
            "create_announcement", "update_announcement", "delete_announcement",
            "_safe",
        ),
        Path(public_api.__file__): (
            "get_site_settings", "list_active_announcements",
        ),
    }
    con_lai = []
    for src_file, ten_doi in DA_DOI.items():
        tree = ast.parse(src_file.resolve().read_text(encoding="utf-8"))
        ten = {n.name for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        con_lai += [f"{src_file.name}:{f}" for f in ten_doi if f in ten]
    assert not con_lai, f"nhà cũ vẫn còn định nghĩa: {con_lai}"


def test_tai_xuat_cung_object_o_nha_cu():
    """Tái xuất là lưới kiểm chứng của cú dời: bộ test cũ vá/soi qua
    `admin.<tên>` và `public_api.<tên>` phải trỏ CÙNG object với nhà thật
    (getsource qua function object vẫn đọc được nguồn ở siteops/)."""
    import admin
    import public_api

    for ten in ("trigger_backup", "ops_summary", "system_health", "export_data",
                "data_quality_apply", "data_quality_rollback",
                "admin_update_setting", "create_announcement",
                "_latest_backup_info", "_SETTING_KEY_RE", "_admin_actor_label"):
        assert getattr(admin, ten) is getattr(admin_api, ten), ten
    for ten in ("get_site_settings", "list_active_announcements"):
        assert getattr(public_api, ten) is getattr(api, ten), ten
    # _safe hoist về admin_common (bước dọn nền lát 3) — cùng object ở cả ba nhà.
    import admin_common
    assert admin.__dict__["_safe"] is admin_common._safe
    assert admin_api.__dict__["_safe"] is admin_common._safe
