"""Invariant: _fix_*_route_order phải bảo toàn ĐỦ route (không mất/rỗng).

_reorder_static_routes chèn từng static route trước param base tương ứng; nếu bỏ sót
static nào thì other_routes ngắn hơn. Guard `if len(other_routes)==len(router.routes)`
đảm bảo chỉ áp reorder khi bảo toàn đủ. Test này khoá bất biến đó (đếm route trước=sau).

(Ghi chú: route-mounted đỏ trên CI trước đây KHÔNG do reorder — đó là regression
fastapi 0.137+ phá include_router, đã pin <0.137 ở requirements.txt.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import admin  # noqa: E402
import social  # noqa: E402


def test_fix_admin_route_order_preserves_all_routes():
    before = len(admin.router.routes)
    assert before > 50, "admin.router phải đầy đủ route (không bị guard/reorder làm rỗng)"
    admin._fix_admin_route_order()  # idempotent + guard: không được mất route
    assert len(admin.router.routes) == before


def test_fix_social_route_order_preserves_all_routes():
    before = len(social.router.routes)
    assert before > 30, "social.router phải đầy đủ route"
    social._fix_social_route_order()
    assert len(social.router.routes) == before


def test_admin_static_route_still_registered():
    # reorder vẫn phải áp trong trường hợp bình thường (không mất route)
    paths = {getattr(r, "path", "") for r in admin.router.routes}
    assert "/admin/stats" in paths
