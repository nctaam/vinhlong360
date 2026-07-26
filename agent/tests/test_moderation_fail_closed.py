"""Regression tests for fail-closed moderation and publication scheduling."""

import asyncio

import moderation


def test_missing_text_provider_keeps_clean_content_pending(monkeypatch):
    monkeypatch.setattr(moderation, "OPENAI_API_KEY", "")

    result = asyncio.run(moderation.moderate_content("Một bài viết sạch", []))

    assert result["status"] == "pending"


def test_text_provider_error_keeps_content_non_public(monkeypatch):
    async def provider_error(_content):
        return {
            "score": 0.0,
            "reasons": ["moderation provider unavailable"],
            "categories": {},
            "available": False,
        }

    monkeypatch.setattr(moderation, "_moderate_text", provider_error)

    result = asyncio.run(moderation.moderate_content("Một bài viết sạch", []))

    assert result["status"] in {"pending", "quarantined"}


def test_missing_image_provider_keeps_content_non_public(monkeypatch):
    monkeypatch.setattr(moderation, "VISION_API_KEY", "")

    result = asyncio.run(
        moderation.moderate_content("Một bài viết có ảnh", ["https://example.test/photo.jpg"])
    )

    assert result["status"] in {"pending", "quarantined"}


def test_image_provider_error_keeps_content_non_public(monkeypatch):
    async def provider_error(_image_urls):
        return {
            "score": 0.0,
            "reasons": ["image moderation provider unavailable"],
            "categories": {},
            "available": False,
        }

    monkeypatch.setattr(moderation, "_moderate_images", provider_error)

    result = asyncio.run(
        moderation.moderate_content("Một bài viết có ảnh", ["https://example.test/photo.jpg"])
    )

    assert result["status"] in {"pending", "quarantined"}


def test_enhanced_pipeline_preserves_fail_closed_base_status(monkeypatch):
    monkeypatch.setattr(moderation, "OPENAI_API_KEY", "")

    result = asyncio.run(
        moderation.moderate_content_enhanced("Một bài viết sạch", user_id="u-test", image_urls=[])
    )

    assert result["status"] in {"pending", "quarantined"}


def test_moderation_auto_escalation_never_approves_pending_posts(monkeypatch):
    import scheduler

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeDb:
        _use_pg = True

        def __init__(self):
            self.executed = []

        def _conn(self):
            return FakeConnection()

        def _execute(self, _conn, sql, params):
            self.executed.append((sql, params))

    fake_db = FakeDb()
    monkeypatch.setattr(scheduler, "db", fake_db, raising=False)

    scheduler.task_moderation_auto_escalation()

    assert not any("SET moderation_status = 'approved'" in sql for sql, _ in fake_db.executed)
