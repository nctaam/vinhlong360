from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "source",
    [
        None,
        "",
        [],
        {},
        {"title": "Manual review"},
        "/relative/source",
        {"url": "/relative/source"},
        "manual",
        "http://localhost:8000/source",
        "https://api.localhost/source",
        "https://service.local/source",
        "http://127.0.0.1/source",
        "http://192.168.1.20/source",
        "http://[::1]/source",
        "http://127.1/source",
        "http://0177.0.0.1/source",
        "http://0x7f.0.0.1/source",
        "http://192.168.1/source",
        "http://169.254.1/source",
        "https://intranet/source",
        "https://vinhlong360.vn/source",
        "https://www.vinhlong360.vn/source",
        "https://foo.vinhlong360.vn/source",
        "https://vinhlong360。vn/source",
        "https://service。local/source",
        "https://api。localhost/source",
        "https://foo.test/source",
        "https://foo.invalid/source",
        "https://foo.example/source",
        "https://foo.home.arpa/source",
        "https://home.arpa/source",
        "http://224.0.0.1/source",
        "http://239.255.255.250/source",
        "http://[ff02::1]/source",
        "http://[fec0::1]/source",
        "http://[feff::1]/source",
    ],
)
def test_rejects_sources_without_an_external_http_url(source: object):
    from source_policy import has_external_source_url

    assert has_external_source_url(source) is False


@pytest.mark.parametrize(
    "source",
    [
        "https://example.org/source",
        "https://münchen.de/source",
        "https://8.8.8.8/source",
        "http://[2606:4700:4700::1111]/source",
        {"url": "http://example.org/source"},
        [{"href": "https://example.org/source"}],
    ],
)
def test_accepts_supported_external_http_source_shapes(source: object):
    from source_policy import has_external_source_url

    assert has_external_source_url(source) is True
