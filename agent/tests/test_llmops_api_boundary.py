"""Ranh giới của gói `agent/llmops/` — lát cắt thứ hai, sau `chat/` (2026-08-27).

Cùng khuôn với `test_chat_api_boundary.py`: khoá những tính chất mà mất thì cú
bóc thành vô nghĩa.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llmops import api as llmops_api  # noqa: E402

SRC = Path(llmops_api.__file__).resolve()


def test_router_phat_du_50_route_dung_mien():
    # 42 route gốc + /search/enhanced (lát 4) + 7 route đuôi-dài server.py về
    # nhà (lát 9 đợt hoàn-thiện-sâu 2026-08-29): 2×/ab-testing,
    # /prompt-cache/stats, /confirmations, /confirm, /reject, /image/recognize
    # — toàn mặt vận-hành-LLM admin-gated, cùng module nguồn với 42 route cũ.
    paths = sorted(r.path for r in llmops_api.router.routes)
    assert len(paths) == 50, len(paths)
    mien = {"/system", "/checkpoints", "/vectors", "/freshness", "/analytics",
            "/search/enhanced", "/ab-testing", "/prompt-cache", "/confirmations",
            "/confirm", "/reject", "/image"}
    for p in paths:
        assert any(p == m or p.startswith(m + "/") for m in mien), f"route lạc miền: {p}"


def test_search_enhanced_len_app_tu_llmops():
    """/search/enhanced phải LÊN app và do llmops.api phục vụ — path y nguyên,
    handler đổi nhà; nếu server.py mọc lại bản sao thì test uniqueness đỏ trước."""
    import server

    matches = [r for r in server.app.routes if getattr(r, "path", None) == "/search/enhanced"]
    assert len(matches) == 1, f"kỳ vọng đúng 1 route /search/enhanced, có {len(matches)}"
    assert matches[0].endpoint.__module__ == "llmops.api", matches[0].endpoint.__module__


def test_7_route_duoi_dai_len_app_tu_llmops():
    """Lát 9: 7 route admin-gated về từ server.py — path y NGUYÊN TỪNG KÝ TỰ,
    handler đổi nhà, và dependant runtime trên app phải trỏ llmops.api (mọc lại
    bản sao ở server thì route trùng — smoke đếm-route đỏ trước)."""
    import server

    DOI_NHA = {
        "/ab-testing/experiments",
        "/ab-testing/results/{experiment_name}",
        "/prompt-cache/stats",
        "/confirmations/{session_id}",
        "/confirm/{confirmation_id}",
        "/reject/{confirmation_id}",
        "/image/recognize",
    }
    thay = {}
    for r in server.app.routes:
        if getattr(r, "path", None) in DOI_NHA:
            thay.setdefault(r.path, []).append(r)
    assert set(thay) == DOI_NHA, f"thiếu route trên app: {DOI_NHA - set(thay)}"
    for path, matches in thay.items():
        assert len(matches) == 1, f"route {path} bị đăng ký {len(matches)} lần"
        assert matches[0].endpoint.__module__ == "llmops.api", (
            path, matches[0].endpoint.__module__)


def test_KHONG_import_nguoc_server_va_chat():
    """`server` import `llmops.api`, nên chiều ngược là VÒNG. Và llmops không
    có việc gì với chat — import chéo giữa hai gói miền là rò rỉ ranh giới."""
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    xau = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            xau += [a.name for a in n.names if a.name.split(".")[0] in ("server", "chat")]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in ("server", "chat"):
                xau.append(n.module)
    assert not xau, f"llmops/api.py import xấu: {xau}"


def test_khong_con_route_llmops_o_server():
    """Dời mà để lại bản sao là hai nguồn sự thật trôi khác nhau."""
    import re

    import server

    src = Path(server.__file__).resolve().read_text(encoding="utf-8")
    con = re.findall(
        r'@app\.(?:get|post|put|delete)\(\s*["\'](/(?:system|checkpoints|vectors|freshness|analytics|search/enhanced|ab-testing|prompt-cache|confirmations|confirm/|reject/|image/)[^"\']*)',
        src)
    assert not con, f"server.py vẫn còn route llmops: {con}"


def test_admin_routes_expose_auth_metadata():
    for route in llmops_api.router.routes:
        path = getattr(route, "path", "")
        if path.startswith(("/system", "/analytics", "/vectors", "/freshness", "/checkpoints", "/ab-testing", "/prompt-cache", "/confirm", "/reject", "/image/")):
            extra = route.openapi_extra or {}
            assert extra.get("x-auth") == "admin-key", path
            assert "x-csrf" in extra, path
    scoped = {route.path: route for route in llmops_api.router.routes if route.path in {"/vectors/build", "/image/recognize"}}
    assert all((route.openapi_extra or {}).get("x-scope") == "ops.deploy" for route in scoped.values())


def test_admin_routes_expose_runtime_auth_dependencies():
    protected = ("/system", "/analytics", "/vectors", "/freshness", "/checkpoints",
                 "/ab-testing", "/prompt-cache", "/confirm", "/reject", "/image/")
    for route in llmops_api.router.routes:
        path = getattr(route, "path", "")
        if path.startswith(protected):
            names = {getattr(dep.call, "__name__", "") for dep in route.dependant.dependencies}
            assert any("require_admin" in name for name in names), (path, names)
            methods = set(getattr(route, "methods", set()))
            assert (route.openapi_extra or {}).get("x-csrf") == bool(
                methods & {"POST", "PUT", "PATCH", "DELETE"}
            ), (path, methods)
    scoped = {route.path: route for route in llmops_api.router.routes if route.path in llmops_api._SCOPED_PATHS}
    for path, route in scoped.items():
        names = {getattr(dep.call, "__name__", "") for dep in route.dependant.dependencies}
        assert any("require_admin_scope" in name for name in names), (path, names)


def test_llmops_dependency_prevents_handler_double_auth(monkeypatch):
    import asyncio
    import admin
    from types import SimpleNamespace

    calls = []

    async def fake_require_admin(request):
        calls.append(request)

    monkeypatch.setattr(admin, "require_admin", fake_require_admin)
    monkeypatch.setattr(llmops_api.analytics, "get_summary", lambda: {"ok": True})
    request = SimpleNamespace(
        state=SimpleNamespace(),
        method="GET",
        url=SimpleNamespace(path="/analytics/summary"),
        headers={},
        cookies={},
    )
    asyncio.run(llmops_api._llmops_require_admin(request))
    result = asyncio.run(llmops_api.analytics_summary(request))
    assert calls == [request]
    assert result == {"ok": True}
