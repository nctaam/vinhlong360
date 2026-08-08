from __future__ import annotations

import importlib.util
import ipaddress
import socket
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import httpx
import pytest

import pinned_http as ph


ROOT = Path(__file__).resolve().parents[1]
ON_SITE_HOST = "vinhlongtourist.vn"
PUBLIC_IP = "93.184.216.34"


def _load_crawler(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("LLM_API_KEY", "test-crawler-ssrf")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("LLM_MODEL_MINI", "test-mini-model")

    module_name = "test_crawler_ssrf_crawler"
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "agent" / "crawler.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def _public_resolver(
    _host: str,
    port: int,
    _budget: ph.DeadlineBudget,
) -> tuple[ph.ResolvedAddress, ...]:
    return (
        ph.ResolvedAddress(
            ip=ipaddress.ip_address(PUBLIC_IP),
            port=port,
            family=socket.AF_INET,
            socktype=socket.SOCK_STREAM,
            protocol=socket.IPPROTO_TCP,
            sockaddr=(PUBLIC_IP, port),
        ),
    )


@pytest.fixture
def crawler(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return _load_crawler(monkeypatch)


@pytest.fixture
def egress(crawler: ModuleType, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    requested: list[httpx.URL] = []
    routes: dict[tuple[str, str], dict] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url)
        response = routes.get((request.url.host, request.url.path))
        if response is None:
            return httpx.Response(404, content=b"not routed", request=request)
        return httpx.Response(
            response["status"],
            headers=response.get("headers", {}),
            content=response.get("content", b""),
            request=request,
        )

    client = ph.PinnedHTTPClient(
        resolver=_public_resolver,
        transport_factory=lambda _hop, _policy, _budget: httpx.MockTransport(handler),
    )
    monkeypatch.setattr(crawler, "_PINNED_HTTP", client, raising=False)

    def legacy_get(*_args, **_kwargs):
        raise AssertionError("crawler must not use legacy unpinned httpx.get")

    monkeypatch.setattr(crawler.httpx, "get", legacy_get)
    return SimpleNamespace(requested=requested, routes=routes)


def test_fetch_page_neutralizes_userinfo_authority_escape(
    crawler: ModuleType,
    egress: SimpleNamespace,
) -> None:
    egress.routes[(ON_SITE_HOST, "/@evil.tld/x")] = {
        "status": 200,
        "content": b"<p>safe</p>",
    }

    assert crawler.fetch_page("@evil.tld/x") == "safe"
    assert [url.host for url in egress.requested] == [ON_SITE_HOST]


@pytest.mark.parametrize(
    "path",
    [
        "//evil.tld/x",
        "https://evil.tld/x",
        "//user@vinhlongtourist.vn/x",
        "file:///etc/passwd",
    ],
)
def test_fetch_page_refuses_offsite_or_credentialed_target_before_request(
    crawler: ModuleType,
    egress: SimpleNamespace,
    path: str,
) -> None:
    with pytest.raises(ValueError):
        crawler.fetch_page(path)

    assert egress.requested == []


def test_fetch_page_blocks_offsite_redirect_before_dial(
    crawler: ModuleType,
    egress: SimpleNamespace,
) -> None:
    egress.routes[(ON_SITE_HOST, "/old")] = {
        "status": 302,
        "headers": {"location": "https://evil.tld/x"},
    }
    egress.routes[("evil.tld", "/x")] = {
        "status": 200,
        "content": b"<p>unsafe</p>",
    }

    with pytest.raises(ph.RedirectPolicyError):
        crawler.fetch_page("/old")

    assert [url.host for url in egress.requested] == [ON_SITE_HOST]


def test_fetch_page_follows_same_origin_redirect_and_strips_html(
    crawler: ModuleType,
    egress: SimpleNamespace,
) -> None:
    egress.routes[(ON_SITE_HOST, "/old")] = {
        "status": 302,
        "headers": {"location": "/new"},
    }
    egress.routes[(ON_SITE_HOST, "/new")] = {
        "status": 200,
        "content": b"<script>bad()</script><p>Cu lao An Binh</p>",
    }

    assert crawler.fetch_page("/old") == "Cu lao An Binh"
    assert [url.host for url in egress.requested] == [ON_SITE_HOST, ON_SITE_HOST]


def test_fetch_page_raises_on_error_status(
    crawler: ModuleType, egress: SimpleNamespace
) -> None:
    """404 phải nổ, KHÔNG được trả chuỗi rỗng như một trang hợp lệ.

    Port từ nhánh `t7/crawler-pinned` trước khi bỏ nhánh đó. Trunk rộng hơn t7 về
    SSRF (chặn userinfo-authority, chặn redirect ra ngoài trước khi dial) nhưng hở
    đúng ca này — mà nó là ca dễ âm thầm nhất: nếu `raise_for_status()` bị gỡ, hàm
    vẫn trả về một chuỗi (thân trang lỗi đã lược tag) và crawler sẽ nuốt trang 404
    thành nội dung thật.

    Khác bản gốc một chỗ: t7 mong `ValueError`, còn `fetch_page` ở đây gọi
    `resp.raise_for_status()` trên một `httpx.Response` (`agent/crawler.py:171`)
    nên ngoại lệ đúng là `httpx.HTTPStatusError`.
    """
    egress.routes[(ON_SITE_HOST, "/vi/gone")] = {"status": 404, "content": b"gone"}

    with pytest.raises(httpx.HTTPStatusError):
        crawler.fetch_page("/vi/gone")
