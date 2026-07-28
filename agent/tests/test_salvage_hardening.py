"""Salvage các fix bị bỏ quên trên nhánh session-be/friendly-mclean.

Triage 2026-07-11: các commit cũ chưa merge, kiểm còn hợp lệ với main rồi merge lại.
Nguồn: 380c394 (sort whitelist + rating null-safe), 52877e2 (admin limit lower-bound),
6f2d391 (logger.warn→warning), af90dbb (Vary header). Fix crash directory_search
list-of-dict (78a6e9e) có test riêng trong test_knowledge.py.
"""
import inspect
import re
import sys
from pathlib import Path

_AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_AGENT))

import admin  # noqa: E402


def test_no_deprecated_logger_warn():
    # 6f2d391: logger.warn() deprecated (Python logging) → logger.warning(). Guard regression.
    bad = [f.name for f in _AGENT.glob("*.py")
           if re.search(r"logger\.warn\(", f.read_text(encoding="utf-8", errors="replace"))]
    assert not bad, f"logger.warn( (deprecated) còn ở: {bad}"


def test_admin_list_entities_limit_has_lower_bound():
    # 52877e2: limit phải có ge (chống limit=0/âm gây truy vấn lạ).
    assert "ge=1" in inspect.getsource(admin.list_entities)


def test_sort_param_whitelisted_by_pattern():
    # 380c394: sort param validate qua regex whitelist (không chỉ max_length).
    for fn in ("public_api.py", "social.py"):
        src = (_AGENT / fn).read_text(encoding="utf-8")
        assert 'pattern="^(newest' in src, f"{fn}: sort thiếu pattern whitelist"


def test_review_stats_rating_null_safe():
    # 380c394: null-safe int (helper _int0) chống int(None) khi rating/cnt NULL trong review stats.
    src = (_AGENT / "public_api.py").read_text(encoding="utf-8")
    assert "def _int0(" in src, "thiếu helper _int0 null-safe"
    assert '_int0(r.get("rating"))' in src and '_int0(r.get("cnt"))' in src


def test_vary_header_for_auth_varied_paths():
    # af90dbb: Vary Authorization cho /api|/admin|/auth → cache đúng theo phiên đăng nhập.
    src = (_AGENT / "server.py").read_text(encoding="utf-8")
    assert 'response.headers["Vary"]' in src
    assert '"/api/", "/admin/", "/auth/"' in src
