"""Tests for Phase 4 upgrade cards: U-28, U-26, U-15, U-20."""
import inspect
from pathlib import Path
import pytest


# ── U-28: Collections model + CRUD ──────────────────────────────────

class TestCollections:

    def test_migration_file_exists(self):
        migration = Path(__file__).resolve().parent.parent / "migrations" / "027_collections.sql"
        assert migration.exists()

    def test_migration_creates_table(self):
        migration = Path(__file__).resolve().parent.parent / "migrations" / "027_collections.sql"
        sql = migration.read_text()
        assert "CREATE TABLE IF NOT EXISTS collections" in sql
        assert "slug TEXT UNIQUE NOT NULL" in sql
        assert "entity_ids JSONB" in sql
        assert "is_published BOOLEAN" in sql
        assert "idx_collections_published" in sql

    def test_admin_list_collections_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/collections" in paths

    def test_admin_create_collection_endpoint(self):
        from admin import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "POST" in methods.get("/admin/collections", set())

    def test_admin_update_collection_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/collections/{collection_id}" in paths

    def test_admin_delete_collection_endpoint(self):
        from admin import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "DELETE" in methods.get("/admin/collections/{collection_id}", set())

    def test_public_list_collections_endpoint(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/collections" in paths

    def test_public_collection_by_slug_endpoint(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/collections/{slug}" in paths

    def test_public_collections_filters_published(self):
        src = inspect.getsource(__import__("public_api").list_public_collections)
        assert "is_published = TRUE" in src

    def test_collection_create_model_validates_slug(self):
        from admin import CollectionCreate
        m = CollectionCreate(slug="top-10-mon-an", title="Top 10 món ăn")
        assert m.slug == "top-10-mon-an"

    def test_collection_create_rejects_bad_slug(self):
        from admin import CollectionCreate
        with pytest.raises(Exception):
            CollectionCreate(slug="Bad Slug!", title="X")

    def test_collection_update_model(self):
        from admin import CollectionUpdate
        m = CollectionUpdate(title="New Title", is_published=True)
        assert m.title == "New Title"
        assert m.is_published is True

    def test_public_collection_resolves_entities(self):
        src = inspect.getsource(__import__("public_api").get_collection_by_slug)
        assert "get_entities_batch" in src
        assert "entity_ids" in src

    def test_admin_create_checks_slug_unique(self):
        src = inspect.getsource(__import__("admin").create_collection)
        assert "409" in src
        assert "slug" in src.lower()


# ── U-26: Event RSVP reminders ──────────────────────────────────────

class TestEventReminders:

    def test_task_exists(self):
        from scheduler import task_event_reminders
        assert callable(task_event_reminders)

    def test_task_registered(self):
        from scheduler import TASKS
        names = [t.name for t in TASKS]
        assert "event-reminders" in names

    def test_task_queries_event_rsvp(self):
        src = inspect.getsource(__import__("scheduler").task_event_reminders)
        assert "event_rsvp" in src

    def test_task_checks_event_date(self):
        src = inspect.getsource(__import__("scheduler").task_event_reminders)
        assert "event_date" in src
        assert "timedelta(hours=24)" in src

    def test_task_dedup_12h_window(self):
        src = inspect.getsource(__import__("scheduler").task_event_reminders)
        assert "12 hours" in src
        assert "NOT EXISTS" in src

    def test_task_creates_notification(self):
        src = inspect.getsource(__import__("scheduler").task_event_reminders)
        assert "create_notification" in src
        assert "event_reminder" in src

    def test_task_requires_pg(self):
        src = inspect.getsource(__import__("scheduler").task_event_reminders)
        assert "_use_pg" in src


# ── U-15: What's-new feed ────────────────────────────────────────────

class TestWhatsNewFeed:

    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/feed/new-since" in paths

    def test_requires_since_param(self):
        src = inspect.getsource(__import__("public_api").feed_new_since)
        assert "since" in src
        assert "min_length=10" in src

    def test_validates_since_date(self):
        src = inspect.getsource(__import__("public_api").feed_new_since)
        assert "fromisoformat" in src
        assert "invalid_date" in src

    def test_returns_entities_and_posts(self):
        src = inspect.getsource(__import__("public_api").feed_new_since)
        assert '"entities"' in src
        assert '"posts"' in src
        assert '"counts"' in src

    def test_filters_public_posts_only(self):
        src = inspect.getsource(__import__("public_api").feed_new_since)
        assert "moderation_status = 'approved'" in src

    def test_limits_results(self):
        src = inspect.getsource(__import__("public_api").feed_new_since)
        assert "LIMIT" in src
        assert "[:limit]" in src

    def test_skips_place_entities(self):
        src = inspect.getsource(__import__("public_api").feed_new_since)
        assert '"place"' in src


# ── U-20: Post-visit review prompts ─────────────────────────────────

class TestReviewPrompts:

    def test_endpoint_exists(self):
        from visits import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/me/visits/review-prompts" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("visits").review_prompts)
        assert "require_user" in src

    def test_queries_visited_not_reviewed(self):
        src = inspect.getsource(__import__("visits").review_prompts)
        assert "status = 'visited'" in src
        assert "NOT IN" in src
        assert "post_type = 'review'" in src

    def test_response_shape(self):
        src = inspect.getsource(__import__("visits").review_prompts)
        assert '"prompts"' in src

    def test_has_limit_param(self):
        src = inspect.getsource(__import__("visits").review_prompts)
        assert "limit" in src
        assert "LIMIT" in src
