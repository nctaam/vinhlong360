"""Audit Đợt 3 — security. Guard các bất biến bảo mật (RBAC default-deny + login enum)."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import admin  # noqa: E402
import auth  # noqa: E402


def test_every_mutating_admin_route_has_scope_rule():
    # RBAC default-deny: MỌI route admin mutating (POST/PUT/DELETE/PATCH) phải có scope rule
    # tường minh trong ADMIN_SCOPE_RULES. Route mutating thiếu rule = fail-open (bị default-
    # deny khoá về master) — buộc dev khai rule khi thêm endpoint mutating admin mới.
    offenders = []
    for r in admin.router.routes:
        p = getattr(r, "path", "")
        if not p.startswith("/admin"):
            continue
        mutating = (getattr(r, "methods", set()) or set()) - {"GET", "HEAD", "OPTIONS"}
        if mutating and not admin._admin_required_scope_for_path(p):
            offenders.append((sorted(mutating), p))
    assert not offenders, f"Route admin mutating thiếu scope rule (fail-open): {offenders}"


def test_require_admin_has_default_deny_branch():
    # Guard: nhánh default-deny cho mutating-không-rule không bị xoá vô tình.
    src = inspect.getsource(admin.require_admin)
    assert 'request.method not in ("GET", "HEAD", "OPTIONS")' in src
    assert '_ensure_admin_scope(request, "*")' in src


def test_login_checks_password_before_active_status():
    # Chống user-enumeration: is_active check phải SAU khi verify password (nếu trước thì
    # attacker biết tài khoản tồn tại + bị vô hiệu hóa mà không cần credential đúng).
    src = inspect.getsource(auth.login_password)
    verify_idx = src.index("_verify_password")
    active_idx = src.index('not user.get("is_active"')
    assert active_idx > verify_idx, "is_active check phải nằm SAU verify password"
