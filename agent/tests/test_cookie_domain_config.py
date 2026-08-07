"""Cookie domain tham số hoá (Blocker 2 — nền tảng đa-tỉnh).

Trước đây `.vinhlong360.vn` bị ghim cứng trong `get_secure_cookie_params()`. Bản clone
(dongthap360.vn, cantho360.vn…) sẽ đặt cookie cho domain SAI → trình duyệt vứt cookie,
đăng nhập hỏng HOÀN TOÀN mà không có exception nào (lỗi im lặng).

Khoá 3 nhánh:
  1. Mặc định (không set env)     → y hệt hành vi Vĩnh Long hiện tại.
  2. COOKIE_DOMAIN=<domain khác>  → cookie theo domain của bản clone.
  3. COOKIE_DOMAIN= (rỗng)        → cookie host-only (dev/localhost).
Cộng nhánh bảo mật: host không thuộc COOKIE_DOMAIN → KHÔNG gắn Domain sai.

Test thuần logic — không DB, không mạng.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _fake_request(host: str = "", *, proto: str = "", forwarded_host: str = "",
                  url_hostname: str | None = None, scheme: str = "http"):
    """Request giả đủ dùng cho _request_is_production/_cookie_params_for_request."""
    headers: dict[str, str] = {}
    if host:
        headers["host"] = host
    if forwarded_host:
        headers["x-forwarded-host"] = forwarded_host
    if proto:
        headers["x-forwarded-proto"] = proto
    return SimpleNamespace(
        headers=headers,
        url=SimpleNamespace(hostname=url_hostname, scheme=scheme),
    )


@pytest.fixture(autouse=True)
def _clean_cookie_env(monkeypatch):
    """Mỗi test bắt đầu từ môi trường sạch (không kế thừa env của máy/CI)."""
    for name in ("COOKIE_DOMAIN", "ENVIRONMENT", "SECURE_COOKIES", "VL360_FORCE_SECURE_COOKIES"):
        monkeypatch.delenv(name, raising=False)
    yield


# ── 1. Nhánh MẶC ĐỊNH: không đổi hành vi prod hiện tại ──

class TestDefaultIsVinhLong:
    def test_get_cookie_domain_default(self):
        from auth_middleware import get_cookie_domain
        assert get_cookie_domain() == ".vinhlong360.vn"

    def test_get_site_domain_default(self):
        from auth_middleware import get_site_domain
        assert get_site_domain() == "vinhlong360.vn"

    def test_prod_params_keep_vinhlong_domain(self):
        from auth_middleware import get_secure_cookie_params
        params = get_secure_cookie_params(is_production=True)
        assert params["domain"] == ".vinhlong360.vn"
        assert params["secure"] is True
        assert params["httponly"] is True
        assert params["samesite"] == "lax"

    def test_dev_params_have_no_domain(self):
        from auth_middleware import get_secure_cookie_params
        params = get_secure_cookie_params(is_production=False)
        assert "domain" not in params
        assert "secure" not in params

    def test_apex_and_subdomain_hosts_keep_domain(self):
        from auth_middleware import get_secure_cookie_params
        for host in ("vinhlong360.vn", "www.vinhlong360.vn", "api.vinhlong360.vn",
                     "VINHLONG360.VN", "vinhlong360.vn:443"):
            params = get_secure_cookie_params(is_production=True, request_host=host)
            assert params.get("domain") == ".vinhlong360.vn", host

    def test_request_is_production_on_vinhlong_host(self):
        from auth import _request_is_production
        assert _request_is_production(_fake_request("vinhlong360.vn")) is True
        assert _request_is_production(_fake_request("www.vinhlong360.vn")) is True

    def test_request_not_production_on_localhost(self):
        from auth import _request_is_production
        assert _request_is_production(_fake_request("localhost:3000")) is False


# ── 2. Nhánh CÓ ENV: bản clone ──

class TestCloneDomain:
    def test_cookie_domain_from_env(self, monkeypatch):
        from auth_middleware import get_cookie_domain, get_site_domain
        monkeypatch.setenv("COOKIE_DOMAIN", ".dongthap360.vn")
        assert get_cookie_domain() == ".dongthap360.vn"
        assert get_site_domain() == "dongthap360.vn"

    def test_prod_params_use_clone_domain(self, monkeypatch):
        from auth_middleware import get_secure_cookie_params
        monkeypatch.setenv("COOKIE_DOMAIN", ".dongthap360.vn")
        params = get_secure_cookie_params(is_production=True, request_host="dongthap360.vn")
        assert params["domain"] == ".dongthap360.vn"
        assert params["secure"] is True

    def test_env_value_is_stripped(self, monkeypatch):
        from auth_middleware import get_cookie_domain
        monkeypatch.setenv("COOKIE_DOMAIN", "  .cantho360.vn  ")
        assert get_cookie_domain() == ".cantho360.vn"

    def test_clone_host_detected_as_production(self, monkeypatch):
        from auth import _request_is_production
        monkeypatch.setenv("COOKIE_DOMAIN", ".dongthap360.vn")
        assert _request_is_production(_fake_request("dongthap360.vn")) is True
        assert _request_is_production(_fake_request("www.dongthap360.vn")) is True
        # domain cũ KHÔNG còn được coi là "site của mình" trên bản clone
        assert _request_is_production(_fake_request("vinhlong360.vn")) is False

    def test_clone_end_to_end_session_cookie(self, monkeypatch):
        from auth import _cookie_params_for_request
        monkeypatch.setenv("COOKIE_DOMAIN", ".dongthap360.vn")
        monkeypatch.setenv("ENVIRONMENT", "production")
        params = _cookie_params_for_request(_fake_request("dongthap360.vn", proto="https"))
        assert params["domain"] == ".dongthap360.vn"
        assert params["secure"] is True
        assert params["max_age"] > 0

    def test_clone_end_to_end_trusted_device_cookie(self, monkeypatch):
        from auth import _trusted_cookie_params
        monkeypatch.setenv("COOKIE_DOMAIN", ".dongthap360.vn")
        monkeypatch.setenv("ENVIRONMENT", "production")
        params = _trusted_cookie_params(_fake_request("dongthap360.vn", proto="https"))
        assert params["domain"] == ".dongthap360.vn"


# ── 3. Nhánh KHÔNG SET DOMAIN: dev / cookie host-only ──

class TestHostOnlyCookies:
    def test_empty_env_means_no_domain_attribute(self, monkeypatch):
        from auth_middleware import get_cookie_domain, get_secure_cookie_params
        monkeypatch.setenv("COOKIE_DOMAIN", "")
        assert get_cookie_domain() == ""
        params = get_secure_cookie_params(is_production=True, request_host="anything.example")
        assert "domain" not in params
        assert params["secure"] is True  # vẫn giữ Secure khi là production

    def test_empty_env_disables_host_based_prod_detection(self, monkeypatch):
        from auth import _request_is_production
        monkeypatch.setenv("COOKIE_DOMAIN", "")
        assert _request_is_production(_fake_request("vinhlong360.vn")) is False
        # cờ env vẫn ép được production
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert _request_is_production(_fake_request("vinhlong360.vn")) is True

    def test_localhost_dev_has_no_domain_no_secure(self):
        from auth import _cookie_params_for_request
        for host in ("localhost:3000", "127.0.0.1:8360", "::1"):
            params = _cookie_params_for_request(_fake_request(host))
            assert "domain" not in params, host
            assert "secure" not in params, host

    def test_localhost_dev_trusted_cookie_has_no_domain(self):
        from auth import _trusted_cookie_params
        params = _trusted_cookie_params(_fake_request("localhost:3000"))
        assert "domain" not in params
        assert "secure" not in params

    def test_request_without_host_header_does_not_crash(self):
        from auth import _cookie_params_for_request
        params = _cookie_params_for_request(_fake_request())
        assert params["httponly"] is True


# ── 4. Bảo mật: KHÔNG BAO GIỜ gắn domain không khớp host ──

class TestNeverSetMismatchedDomain:
    """Gắn Domain=.vinhlong360.vn cho request tới host khác vừa làm hỏng đăng nhập
    (trình duyệt vứt cookie) vừa là rò cấu hình sang domain không liên quan."""

    def test_prod_on_foreign_host_drops_domain(self):
        from auth_middleware import get_secure_cookie_params
        params = get_secure_cookie_params(is_production=True, request_host="dongthap360.vn")
        assert "domain" not in params
        assert params["secure"] is True

    def test_lookalike_suffix_host_does_not_get_domain(self):
        from auth_middleware import get_secure_cookie_params
        # "evilvinhlong360.vn" khớp endswith() thô nhưng KHÔNG phải subdomain của mình
        params = get_secure_cookie_params(is_production=True, request_host="evilvinhlong360.vn")
        assert "domain" not in params

    def test_end_to_end_environment_production_on_clone_host(self, monkeypatch):
        """Kịch bản hỏng thật: clone deploy với ENVIRONMENT=production nhưng QUÊN
        đặt COOKIE_DOMAIN → tuyệt đối không được đặt cookie cho .vinhlong360.vn."""
        from auth import _cookie_params_for_request
        monkeypatch.setenv("ENVIRONMENT", "production")
        params = _cookie_params_for_request(_fake_request("dongthap360.vn", proto="https"))
        assert params.get("domain") != ".vinhlong360.vn"
        assert "domain" not in params
        assert params["secure"] is True  # cookie vẫn Secure → vẫn đăng nhập được

    def test_end_to_end_trusted_cookie_on_clone_host(self, monkeypatch):
        from auth import _trusted_cookie_params
        monkeypatch.setenv("ENVIRONMENT", "production")
        params = _trusted_cookie_params(_fake_request("dongthap360.vn", proto="https"))
        assert "domain" not in params

    def test_forwarded_host_wins_over_host_header(self, monkeypatch):
        """Sau nginx/CDN, host thật nằm ở X-Forwarded-Host."""
        from auth import _cookie_params_for_request
        monkeypatch.setenv("ENVIRONMENT", "production")
        req = _fake_request("internal-upstream:8360", forwarded_host="vinhlong360.vn", proto="https")
        assert _cookie_params_for_request(req)["domain"] == ".vinhlong360.vn"
        req2 = _fake_request("internal-upstream:8360", forwarded_host="dongthap360.vn", proto="https")
        assert "domain" not in _cookie_params_for_request(req2)


# ── 5. Hàm khớp domain (đơn vị) ──

class TestCookieDomainMatchesHost:
    @pytest.mark.parametrize("domain,host,expected", [
        (".vinhlong360.vn", "vinhlong360.vn", True),
        (".vinhlong360.vn", "www.vinhlong360.vn", True),
        (".vinhlong360.vn", "a.b.vinhlong360.vn", True),
        (".vinhlong360.vn", "vinhlong360.vn.", True),          # trailing dot (FQDN)
        (".vinhlong360.vn", "VinhLong360.VN", True),           # case-insensitive
        ("vinhlong360.vn", "www.vinhlong360.vn", True),        # domain không có dấu chấm đầu
        (".vinhlong360.vn", "dongthap360.vn", False),
        (".vinhlong360.vn", "evilvinhlong360.vn", False),      # không phải subdomain
        (".vinhlong360.vn", "vinhlong360.vn.evil.com", False),
        (".vinhlong360.vn", "localhost", False),
        (".vinhlong360.vn", "", False),                        # không biết host → không gắn
        ("", "bất-kỳ-host", True),                             # host-only luôn hợp lệ
    ])
    def test_matching(self, domain, host, expected):
        from auth_middleware import cookie_domain_matches_host
        assert cookie_domain_matches_host(domain, host) is expected
