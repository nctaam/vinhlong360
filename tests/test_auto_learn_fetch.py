from __future__ import annotations

import logging

import pytest

import auto_learn
import pinned_http as ph


def _response(
    *,
    status: int = 200,
    content: bytes = b"",
    content_type: str | None = "text/html; charset=utf-8",
    extra_headers: tuple[tuple[str, str], ...] = (),
) -> ph.PinnedResponse:
    headers = extra_headers
    if content_type is not None:
        headers = (("content-type", content_type),) + headers
    return ph.PinnedResponse(status, "https://example.com/final", headers, content, ())


def test_fetch_url_uses_pinned_options_and_preserves_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []
    body = b"<script>drop()</script><style>.x{}</style><h1>Vinh Long</h1> noi dung"
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda url, **kwargs: calls.append((url, kwargs)) or _response(content=body),
    )
    assert auto_learn.fetch_url("https://example.com/a") == "Vinh Long noi dung"
    assert calls == [(
        "https://example.com/a",
        {
            "user_agent": "vinhlong360-learner/1.0",
            "timeout": 15,
            "max_redirects": 5,
        },
    )]


@pytest.mark.parametrize("status", [199, 204, 302, 399, 400, 500])
def test_fetch_url_requires_exact_200(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(status=status, content=b"ignored"),
    )
    assert auto_learn.fetch_url("https://example.com/a") is None


def test_fetch_url_keeps_httpx_charset_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    content = "café Vĩnh Long".encode("iso-8859-1", errors="replace")
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=content,
            content_type="text/html; charset=iso-8859-1",
            extra_headers=(("content-encoding", "gzip"), ("content-length", "10")),
        ),
    )
    assert "café" in auto_learn.fetch_url("https://example.com/a")


def test_fetch_url_logs_and_returns_none_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ph.PinnedTransportError("boom")),
    )
    with caplog.at_level(logging.WARNING):
        assert auto_learn.fetch_url("https://example.com/a") is None
    assert "https://example.com/a" in caplog.text


def test_fetch_url_missing_charset_uses_httpx_utf8_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = "Vĩnh Long miền sông nước".encode("utf-8")
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(content=body, content_type="text/html"),
    )
    assert auto_learn.fetch_url("https://example.com/a") == "Vĩnh Long miền sông nước"


def test_fetch_url_does_not_redecode_http_decoded_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoded_body = "Nội dung đã giải nén".encode("utf-8")
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=decoded_body,
            extra_headers=(
                ("content-encoding", "gzip"),
                ("content-length", "12"),
                ("transfer-encoding", "chunked"),
            ),
        ),
    )
    assert auto_learn.fetch_url("https://example.com/a") == "Nội dung đã giải nén"


def test_fetch_url_truncates_cleaned_text_to_exactly_6000_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auto_learn._PINNED_HTTP,
        "get",
        lambda *_args, **_kwargs: _response(
            content=("<p>" + ("x" * 6005) + "</p>").encode(),
        ),
    )
    result = auto_learn.fetch_url("https://example.com/a")
    assert result == "x" * 6000
    assert len(result) == 6000


def test_process_result_skips_text_shorter_than_200_without_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auto_learn, "fetch_url", lambda _url: "x" * 199)
    monkeypatch.setattr(
        auto_learn,
        "extract_entities_from_text",
        lambda *_args, **_kwargs: pytest.fail("extraction called for short text"),
    )
    known: set[str] = set()
    new_entities: list[dict] = []
    auto_learn._process_result(
        {"href": "https://example.com/a"},
        "query",
        known,
        new_entities,
    )
    assert known == set()
    assert new_entities == []
