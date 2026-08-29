"""Ranh giới TẦNG ROUTE của gói `agent/itineraries/` (lát 2 đợt cắt module, 2026-08-29).

Gói miền lịch trình nay ĐỦ HAI MẶT theo khuôn `agent/cases/`, `agent/entities/`
và `agent/community/`: `api.py` (3 route public: optimize-order, list, get) +
`admin_api.py` (5 route CRUD quản trị) — tầng service (itinerary_*) đã về gói
từ trước, ranh giới của nó do test_itineraries_boundary.py giữ (file đó cũng
quét MỌI *.py trong gói, bao gồm hai module route mới, cấm import ngược).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from itineraries import admin_api  # noqa: E402
from itineraries import api  # noqa: E402

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


def test_KHONG_import_nguoc():
    XAU = ("server", "admin", "public_api", "chat", "community", "identity",
           "llmops", "entities", "mcp_server")
    bad = []
    for src_path in (SRC_ADMIN, SRC_PUBLIC):
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                bad += [f"{src_path.name}:{a.name}" for a in n.names
                        if a.name.split(".")[0] in XAU]
            elif isinstance(n, ast.ImportFrom) and n.module:
                if n.module.split(".")[0] in XAU:
                    bad.append(f"{src_path.name}:{n.module}")
    assert not bad, f"itineraries route-module import xấu: {bad}"


def test_khong_con_dinh_nghia_o_nha_cu():
    """admin.py + public_api.py hết định nghĩa các hàm/model đã dời — AST cấp
    module, không so chuỗi."""
    import admin
    import public_api

    DA_DOI = {
        Path(admin.__file__): (
            "list_itineraries_admin", "get_itinerary_admin", "create_itinerary",
            "update_itinerary", "delete_itinerary", "_normalize_itinerary_payload",
            "ItineraryCreate", "ItineraryUpdate",
        ),
        Path(public_api.__file__): (
            "optimize_itinerary_order", "list_itineraries", "get_itinerary",
            "_optimize_itinerary_order_only", "_schedule_itinerary",
            "_validate_itinerary_stop_id", "_validate_duration_matrix_values",
            "_validate_schedule_references", "_schedule_windows",
            "_build_schedule_stops", "_build_schedule_matrix",
            "_path_distance_km", "_serialize_schedule_result",
            "_serialize_order_result", "ItineraryOptimizeStopIn",
            "ItineraryScheduleStopIn", "ItineraryScheduleIn", "ItineraryOptimizeIn",
            "_itinerary_stop_entity_id", "_public_itinerary_stops",
        ),
    }
    con_lai = []
    for src_file, ten_doi in DA_DOI.items():
        tree = ast.parse(src_file.resolve().read_text(encoding="utf-8"))
        ten = {n.name for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        con_lai += [f"{src_file.name}:{f}" for f in ten_doi if f in ten]
    assert not con_lai, f"nhà cũ vẫn còn định nghĩa: {con_lai}"


def test_buoc_1a_hai_helper_ve_entity_read_va_tai_xuat_cung_object():
    """Bước 1a của lát: _itinerary_stop_entity_id + _public_itinerary_stops dời
    về entity_read (hạ tầng đọc dùng chung); public_api tái xuất — 3 chỗ test
    cũ soi qua public_api.<tên> phải trỏ CÙNG object với nhà thật."""
    import entity_read
    import public_api

    for ten in ("_itinerary_stop_entity_id", "_public_itinerary_stops"):
        assert getattr(public_api, ten) is getattr(entity_read, ten), ten
    assert entity_read._itinerary_stop_entity_id({"entityId": "cho-lach"}) == "cho-lach"
    assert entity_read._itinerary_stop_entity_id({}) in ("", None)
