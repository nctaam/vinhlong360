# -*- coding: utf-8 -*-
"""Hợp đồng BỀ MẶT API, soi trên app ĐÃ MOUNT — tầng mà 9.535 test kia bỏ trống.

Vì sao cần file này: gần như mọi test backend đều import router của riêng module
mình rồi khẳng định về router đó. Hậu quả có thật: GET /api/me/activity từng được
khai báo ở cả `public_api.py` lẫn `social.py` với cùng prefix "/api"; FastAPI giữ
bản đăng ký trước, bản sau thành code chết, và cả hai trả payload khác nhau. Suite
vẫn xanh suốt thời gian đó.

`tests/test_route_uniqueness.py` (viết ngay sau vụ đó) đã dựng `server.app` và
chặn route trùng. File này mở rộng sang phần còn lại của bề mặt: guard xác thực
trên route ghi, guard admin, guard Postgres cho UGC, và hợp đồng API khớp code.

Nguyên tắc của file này:
1. Chỉ soi `app.routes` và gọi HTTP thật qua TestClient. KHÔNG dùng
   `inspect.getsource()` để so chuỗi trong source — loại test đó đỏ khi refactor
   đúng và xanh khi hành vi sai.
2. Mọi phép đếm đều có ngưỡng sàn. Một selector hỏng (đổi tên module, đổi prefix)
   sẽ làm tập khảo sát rỗng và test "xanh" một cách rỗng tuếch — đó là cổng giả.
   Ngưỡng sàn biến cái rỗng đó thành đỏ.
3. Mọi ngoại lệ phải khai báo tường minh ngay trong file này, kèm lý do, và có
   test riêng bắt ngoại lệ chết (route đã đổi/đã xoá) phải bị gỡ khỏi danh sách.
4. Assertion nào đỏ cũng in ra đúng danh sách route vi phạm để sửa được ngay.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

API_CONTRACT = REPO_ROOT / "docs" / "api-contract.md"

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Guard BUỘC phải có người dùng/admin hợp lệ, tức là RAISE khi thiếu.
# `get_current_user` KHÔNG nằm đây: nó trả None chứ không raise, chỉ là auth tuỳ chọn.
AUTH_GUARDS = ("require_user", "require_admin", "require_role")
ADMIN_GUARDS = ("require_admin", "require_role")
PG_GUARD = "require_pg"

# Module phục vụ UGC/auth — theo CLAUDE.md §1.3 chúng là Postgres-only, chạy
# SQLite phải trả 503 rõ ràng chứ không phải 500 vỡ bụng.
UGC_MODULES = frozenset(
    {"social", "notifications", "achievements", "plans", "saved", "visits", "auth"}
)

# Route SSE: bị loại khỏi phần gọi HTTP thật vì nếu guard biến mất thì response
# không bao giờ đóng và test sẽ TREO thay vì đỏ. Vẫn được phủ ở tầng cấu trúc
# (test_ugc_routes_all_sit_behind_the_postgres_guard) nên không có lỗ hổng.
STREAMING_PATHS = frozenset({"/api/notifications/stream"})

# Route GHI dưới /api được phép ẩn danh. Mỗi dòng là một quyết định có chủ đích,
# không phải chỗ để nhét route mới cho qua cổng.
PUBLIC_WRITE_ALLOWLIST: dict[tuple[str, str], str] = {
    ("POST", "/api/client-error"): "Nhận báo lỗi từ trình duyệt khách; không đọc/ghi dữ liệu người dùng.",
    ("POST", "/api/report"): "Tố giác nội dung — phải cho khách gửi được. Chặn lạm dụng bằng rate-limit theo IP.",
    ("POST", "/api/itineraries/optimize-order"): "Tính toán thuần trên payload gửi lên, không chạm DB.",
    ("POST", "/api/entities/{entity_id}/report-stale"): "Báo thông tin lỗi thời của điểm đến; rate-limit theo IP.",
    ("POST", "/api/entities/{entity_id}/view-contact"): "Đếm lượt bấm xem liên hệ (analytics CTA); rate-limit theo IP.",
    ("POST", "/api/posts/{post_id}/share"): "Đếm lượt chia sẻ, cố ý cho cả khách vãng lai; vẫn nằm sau require_pg + CSRF.",
}

# Bốn tài liệu SEO gốc do Nuxt sở hữu. api-contract.md liệt kê chúng trong bảng
# nhưng phần diễn giải ngay dưới bảng nói rõ: "FastAPI is not a public owner of
# these paths" — nginx định tuyến thẳng sang Nuxt. Test khẳng định chiều ngược
# lại (FastAPI KHÔNG được phục vụ) thay vì lặng lẽ bỏ qua.
NUXT_OWNED_SEO_DOCS = ("/sitemap.xml", "/sitemap-media.xml", "/sitemap-index.xml", "/robots.txt")

# Ngưỡng sàn chống test xanh rỗng. Đặt thấp hơn số thực tế lúc viết
# (58 route ghi /api, 132 route admin, 83 route cần đăng nhập, 67 route UGC GET,
# 103 dòng hợp đồng) đủ để chịu được co giãn bình thường, nhưng một selector
# hỏng làm tập khảo sát tụt về 0 thì đỏ ngay.
MIN_API_WRITE_ROUTES = 40
MIN_ADMIN_ROUTES = 100
MIN_LOGIN_ROUTES = 50
MIN_UGC_PROBES = 50
MIN_CONTRACT_ROWS = 90


# ── Dựng app thật ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """App đã mount đủ router. Patch giống tests/test_route_uniqueness.py."""
    os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
    os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")
    os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
    with patch("server.start_scheduler", MagicMock()), \
         patch("server.sync_data_json_to_js", MagicMock()):
        from server import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="module")
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


class RouteInfo:
    """Một route đã mount, kèm tên mọi dependency giải được từ dependant tree."""

    __slots__ = ("methods", "path", "name", "module", "guards")

    def __init__(self, route):
        raw_methods = getattr(route, "methods", None) or ()
        self.methods = frozenset(m for m in raw_methods if m not in ("HEAD", "OPTIONS"))
        self.path = getattr(route, "path", None) or ""
        self.name = getattr(route, "name", None) or ""
        self.module = getattr(getattr(route, "endpoint", None), "__module__", "") or ""
        self.guards = _guard_names(getattr(route, "dependant", None))

    def has(self, guard_names) -> bool:
        """Có ít nhất một dependency mang tên guard trong danh sách."""
        return any(any(g in name for g in guard_names) for name in self.guards)

    def label(self, method: str | None = None) -> str:
        shown = method or "|".join(sorted(self.methods))
        return f"{shown} {self.path}  ({self.module}.{self.name})"


def _guard_names(dependant, depth: int = 0) -> frozenset[str]:
    """Tên đủ điều kiện (qualname) của mọi dependency, đệ quy xuống sub-dependency.

    Dùng qualname chứ không dùng __name__ vì guard kiểu factory (`require_role`)
    trả về closure tên là `dep`; qualname của nó là `require_role.<locals>.dep`
    nên vẫn nhận diện được.
    """
    if dependant is None or depth > 6:
        return frozenset()
    names: set[str] = set()
    for sub in getattr(dependant, "dependencies", ()):
        call = getattr(sub, "call", None)
        if call is None:
            continue
        names.add(getattr(call, "__qualname__", None) or getattr(call, "__name__", "") or repr(call))
        names |= _guard_names(sub, depth + 1)
    return frozenset(names)


def _routes(app) -> list[RouteInfo]:
    return [info for info in (RouteInfo(r) for r in app.routes) if info.path and info.methods]


def _write_routes_under_api(app) -> list[tuple[str, RouteInfo]]:
    """Cặp (method, route) cho mọi động tác GHI dưới /api."""
    out = []
    for info in _routes(app):
        if not info.path.startswith("/api"):
            continue
        for method in sorted(info.methods & WRITE_METHODS):
            out.append((method, info))
    return out


def _bullets(lines) -> str:
    return "\n".join(f"  - {line}" for line in sorted(lines))


# ── 1. Không route nào trùng (method, path) ───────────────────────────────────

def test_no_duplicate_method_path_on_mounted_app(app):
    """Route trùng = bản đăng ký sau thành code chết, OpenAPI mơ hồ.

    Trùng lặp có chủ ý với tests/test_route_uniqueness.py: file này muốn đứng
    một mình như bản hợp đồng đầy đủ của bề mặt API.
    """
    pairs = [(method, info.path) for info in _routes(app) for method in info.methods]
    duplicates = sorted(pair for pair, count in Counter(pairs).items() if count > 1)

    assert not duplicates, (
        "Route bị đăng ký hai lần trên app đã mount — bản sau không bao giờ chạy:\n"
        + _bullets(f"{m} {p}" for m, p in duplicates)
    )


# ── 2. Route ghi dưới /api phải có guard xác thực ─────────────────────────────

def test_write_routes_under_api_require_an_auth_guard(app):
    """POST/PUT/PATCH/DELETE dưới /api phải chạm được một guard biết raise.

    Đây là lớp chặn cho đúng kiểu lỗi đã ship: thêm handler ghi vào
    `public_api.py` (router KHÔNG có dependency chung) thay vì `social.py`
    (router có require_pg + handler có require_user) thì route ra đời trần trụi.
    """
    writes = _write_routes_under_api(app)
    assert len(writes) >= MIN_API_WRITE_ROUTES, (
        f"Chỉ thấy {len(writes)} route ghi dưới /api, dưới ngưỡng {MIN_API_WRITE_ROUTES}. "
        "Selector hỏng chứ không phải API teo lại — sửa test trước khi tin kết quả."
    )

    unguarded = [
        info.label(method)
        for method, info in writes
        if not info.has(AUTH_GUARDS) and (method, info.path) not in PUBLIC_WRITE_ALLOWLIST
    ]

    assert not unguarded, (
        "Route GHI dưới /api mà bất kỳ ai cũng gọi được (không có require_user/"
        "require_admin/require_role trong dependant tree):\n"
        + _bullets(unguarded)
        + "\n\nSửa bằng cách thêm guard vào handler hoặc vào router. Nếu route thật "
          "sự phải mở cho khách, khai vào PUBLIC_WRITE_ALLOWLIST kèm lý do."
    )


def test_public_write_allowlist_has_no_stale_entries(app):
    """Danh sách ngoại lệ phải luôn khớp thực tế, nếu không nó thành cổng giả.

    Ngoại lệ chết (route đã xoá, đổi path, hoặc đã được gắn guard) mà vẫn nằm lại
    sẽ âm thầm miễn trừ cho một route mới trùng tên trong tương lai.
    """
    writes = _write_routes_under_api(app)
    actually_unguarded = {
        (method, info.path) for method, info in writes if not info.has(AUTH_GUARDS)
    }
    existing = {(method, info.path) for method, info in writes}

    gone = [f"{m} {p}" for m, p in PUBLIC_WRITE_ALLOWLIST if (m, p) not in existing]
    now_guarded = [
        f"{m} {p}"
        for m, p in PUBLIC_WRITE_ALLOWLIST
        if (m, p) in existing and (m, p) not in actually_unguarded
    ]

    assert not gone, (
        "PUBLIC_WRITE_ALLOWLIST còn ngoại lệ cho route KHÔNG còn tồn tại — xoá đi:\n"
        + _bullets(gone)
    )
    assert not now_guarded, (
        "PUBLIC_WRITE_ALLOWLIST còn ngoại lệ cho route ĐÃ có guard xác thực — "
        "xoá đi để danh sách nói đúng sự thật:\n" + _bullets(now_guarded)
    )


# ── 3. Route /admin phải có guard admin ───────────────────────────────────────

def test_admin_routes_all_carry_the_admin_guard(app):
    admin_routes = [info for info in _routes(app) if info.path.startswith("/admin")]
    assert len(admin_routes) >= MIN_ADMIN_ROUTES, (
        f"Chỉ thấy {len(admin_routes)} route /admin, dưới ngưỡng {MIN_ADMIN_ROUTES} — "
        "nhiều khả năng router admin không được mount, không phải AdminCP teo lại."
    )

    unguarded = [info.label() for info in admin_routes if not info.has(ADMIN_GUARDS)]

    assert not unguarded, (
        "Route /admin thiếu require_admin trong dependant tree — AdminCP hở:\n"
        + _bullets(unguarded)
    )


def test_admin_routes_deny_anonymous_http_requests(app, client):
    """Chứng minh guard admin ĐƯỢC ĐẤU DÂY thật, không chỉ nằm trong danh sách.

    Chỉ lấy vài route GET để không tự kích rate-limit của require_admin. Chấp nhận
    429 vì require_admin chạy rate-limit TRƯỚC khi kiểm auth — 429 vẫn là từ chối.
    """
    denials = {401, 403, 429}
    sample = sorted(
        {info.path for info in _routes(app) if info.path.startswith("/admin") and "GET" in info.methods}
    )[:5]
    assert sample, "Không lấy được route /admin GET nào để thử — selector hỏng."

    leaked = []
    for path in sample:
        url = re.sub(r"\{[^}]+\}", "probe-id", path)
        response = client.get(url)
        if response.status_code not in denials:
            leaked.append(f"GET {path} -> HTTP {response.status_code}: {response.text[:120]}")

    assert not leaked, (
        f"Route /admin trả về status ngoài {sorted(denials)} khi gọi KHÔNG có X-Admin-Key. "
        "2xx nghĩa là rò dữ liệu quản trị; 5xx nghĩa là guard nổ giữa chừng:\n"
        + _bullets(leaked)
    )


# ── 4. UGC nằm sau guard Postgres ─────────────────────────────────────────────

def test_routes_requiring_login_also_require_postgres(app):
    """require_user ⟹ require_pg. Bảng users nằm ở Postgres, không có ở SQLite.

    Đây là luật suy ra, không phải danh sách cứng: module UGC mới thêm sau này
    cũng bị phủ tự động, miễn là nó dùng require_user.
    """
    login_routes = [info for info in _routes(app) if info.has(("require_user",))]
    assert len(login_routes) >= MIN_LOGIN_ROUTES, (
        f"Chỉ thấy {len(login_routes)} route dùng require_user, dưới ngưỡng "
        f"{MIN_LOGIN_ROUTES} — selector guard hỏng."
    )

    missing_pg = [info.label() for info in login_routes if not info.has((PG_GUARD,))]

    assert not missing_pg, (
        "Route đòi đăng nhập nhưng KHÔNG có require_pg: chạy SQLite nó sẽ nổ 500 "
        "khi truy vấn bảng users thay vì trả 503 rõ ràng (CLAUDE.md §1.3):\n"
        + _bullets(missing_pg)
    )


def test_ugc_routes_all_sit_behind_the_postgres_guard(app):
    """Phủ cả route SSE và route ghi — những chỗ phần gọi HTTP bên dưới không với tới."""
    ugc_routes = [info for info in _routes(app) if info.module in UGC_MODULES]
    assert len(ugc_routes) >= MIN_UGC_PROBES, (
        f"Chỉ thấy {len(ugc_routes)} route thuộc module UGC {sorted(UGC_MODULES)}, "
        f"dưới ngưỡng {MIN_UGC_PROBES} — router UGC không được mount?"
    )

    missing_pg = [info.label() for info in ugc_routes if not info.has((PG_GUARD,))]

    assert not missing_pg, (
        "Route UGC thiếu require_pg — chạy SQLite sẽ trả 500 thay vì 503:\n"
        + _bullets(missing_pg)
    )


def test_ugc_routes_answer_503_not_500_when_running_on_sqlite(app, client):
    """Gọi HTTP thật: SQLite thì mọi endpoint UGC phải trả đúng 503.

    Chỉ quét GET nên không có nguy cơ ghi dữ liệu. Route SSE bị loại vì nếu guard
    biến mất thì nó treo chứ không đỏ; route đó đã được phủ ở test cấu trúc trên.
    """
    from database import db

    if db._use_pg:
        pytest.skip("Đang chạy Postgres — hợp đồng 503-trên-SQLite không áp dụng.")

    paths = sorted(
        {
            info.path
            for info in _routes(app)
            if info.module in UGC_MODULES
            and "GET" in info.methods
            and info.path not in STREAMING_PATHS
        }
    )
    assert len(paths) >= MIN_UGC_PROBES, (
        f"Chỉ gọi thử được {len(paths)} route UGC GET, dưới ngưỡng {MIN_UGC_PROBES} — "
        "selector hỏng, đừng tin màu xanh."
    )

    wrong = []
    for path in paths:
        url = re.sub(r"\{[^}]+\}", "probe-id", path)
        response = client.get(url)
        if response.status_code != 503:
            wrong.append(f"GET {path} -> HTTP {response.status_code}: {response.text[:120]}")

    assert not wrong, (
        "Endpoint UGC không trả 503 khi chạy SQLite. 500 = guard require_pg bị "
        "đặt sau phần truy vấn; 2xx = endpoint chui lọt ra ngoài guard:\n"
        + _bullets(wrong)
    )


# ── 5. Hợp đồng trong docs/api-contract.md phải khớp app ──────────────────────

def _contract_rows() -> list[tuple[str, str]]:
    """Đọc các dòng bảng dạng `| METHOD | \\`/path\\` | ...` trong api-contract.md."""
    text = API_CONTRACT.read_text(encoding="utf-8")
    pattern = re.compile(r"^\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`]+)`\s*\|", re.M)
    return [(m.group(1), m.group(2)) for m in pattern.finditer(text)]


def _normalize(path: str) -> str:
    """Bỏ tên tham số đường dẫn: hợp đồng ghi {id}, code ghi {entity_id}."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def test_every_documented_endpoint_exists_on_the_mounted_app(app):
    """Hợp đồng nói có thì app phải có. Ngược lại frontend đọc theo doc sẽ ăn 404."""
    assert API_CONTRACT.is_file(), f"Không tìm thấy {API_CONTRACT}"

    rows = _contract_rows()
    assert len(rows) >= MIN_CONTRACT_ROWS, (
        f"Chỉ đọc được {len(rows)} dòng endpoint từ {API_CONTRACT.name}, dưới ngưỡng "
        f"{MIN_CONTRACT_ROWS}. Bảng đã đổi định dạng và regex không còn bắt được — "
        "test này đang xanh rỗng, sửa parser ngay."
    )

    mounted = {(method, _normalize(info.path)) for info in _routes(app) for method in info.methods}

    missing = []
    for method, path in rows:
        if "*" in path:
            continue  # dòng mô tả cả nhóm (ví dụ /system/*), không phải một route cụ thể
        if path in NUXT_OWNED_SEO_DOCS:
            continue  # Nuxt sở hữu — khẳng định riêng ở test dưới
        if (method, _normalize(path)) not in mounted:
            missing.append(f"{method} {path}")

    assert not missing, (
        f"{API_CONTRACT.name} mô tả endpoint KHÔNG tồn tại trên app đã mount. "
        "Hoặc route bị xoá/đổi tên mà quên sửa doc, hoặc router chưa được mount:\n"
        + _bullets(missing)
    )


def test_root_seo_documents_are_not_served_by_fastapi(app):
    """4 tài liệu SEO gốc do Nuxt phục vụ; nginx định tuyến thẳng, FastAPI không sở hữu.

    Khẳng định chiều "không được có" thay vì lẳng lặng bỏ qua chúng ở test trên.
    FastAPI mọc thêm bản thứ hai nghĩa là có hai nguồn sự thật cho sitemap/robots.
    """
    mounted = {info.path for info in _routes(app)}
    trespassing = [path for path in NUXT_OWNED_SEO_DOCS if path in mounted]

    assert not trespassing, (
        "FastAPI đang phục vụ tài liệu SEO gốc vốn thuộc về Nuxt — thành hai nguồn "
        "sự thật cho cùng một URL:\n" + _bullets(trespassing)
    )
