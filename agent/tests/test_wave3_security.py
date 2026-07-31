"""Audit Đợt 3 — security. Guard các bất biến bảo mật (RBAC default-deny + login enum)."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import admin  # noqa: E402
import auth  # noqa: E402


def test_every_admin_route_has_scope_rule_or_scope_filtered_read():
    # Mọi route AdminCP phải có scope tường minh; endpoint read đa workstream chỉ được
    # miễn rule đơn khi response được lọc theo actor tại endpoint.
    offenders = []
    for r in admin.router.routes:
        p = getattr(r, "path", "")
        if not p.startswith("/admin"):
            continue
        methods = getattr(r, "methods", set()) or set()
        scope_filtered = methods <= {"GET", "HEAD", "OPTIONS"} and p in admin.ADMIN_SCOPE_AWARE_READ_PATHS
        if not admin._admin_required_scope_for_path(p) and not scope_filtered:
            offenders.append((sorted(methods), p))
    assert not offenders, f"Route AdminCP thiếu scope hoặc response filter: {offenders}"


def test_require_admin_has_default_deny_branch():
    # Guard: GET không rule cũng phải default-deny, trừ endpoint read tự lọc response.
    src = inspect.getsource(admin.require_admin)
    assert "_is_scope_aware_admin_read(request)" in src
    assert '_ensure_admin_scope(request, "*")' in src


def test_login_checks_password_before_active_status():
    # Chống user-enumeration: is_active check phải SAU khi verify password (nếu trước thì
    # attacker biết tài khoản tồn tại + bị vô hiệu hóa mà không cần credential đúng).
    src = inspect.getsource(auth.login_password)
    verify_idx = src.index("_verify_password")
    active_idx = src.index('not user.get("is_active"')
    assert active_idx > verify_idx, "is_active check phải nằm SAU verify password"
