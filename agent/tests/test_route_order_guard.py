"""Guard: _fix_*_route_order KHÔNG được làm rỗng/mất route của router.

Bug (route-mounted fail trên CI-Linux): _reorder_static_routes match từng static,
có thể bỏ sót → other_routes ngắn hơn → `router.routes[:] = other_routes` làm rỗng
router. Guard chỉ áp reorder khi len(other_routes)==len(router.routes).
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
