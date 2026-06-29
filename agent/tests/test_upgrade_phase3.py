"""Tests for Phase 3 upgrade cards: U-17, U-24, U-22, BE-10, BE-5."""
import inspect
import pytest


# ── U-17: Stale content admin queue ─────────────────────────────────

class TestStaleQueue:

    def test_stale_queue_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/stale-queue" in paths

    def test_stale_mark_reviewed_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/stale-queue/{entity_id}/mark-reviewed" in paths

    def test_stale_queue_has_threshold_param(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "threshold_days" in src
        assert "ge=30" in src

    def test_stale_queue_has_missing_field_filter(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "missing_field" in src
        assert "source|images|coordinates|phone|summary" in src

    def test_stale_queue_has_entity_type_filter(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "entity_type" in src

    def test_stale_queue_computes_days_since(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "days_since" in src
        assert "timedelta" in src

    def test_stale_queue_response_shape(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert '"items"' in src
        assert '"total"' in src
        assert '"days_since_update"' in src
        assert '"is_stale"' in src
        assert '"missing_fields"' in src

    def test_stale_queue_sorts_by_staleness(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "results.sort" in src
        assert "days_since_update" in src

    def test_stale_queue_skips_place_entities(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert '"place"' in src
        assert "continue" in src

    def test_stale_mark_reviewed_validates_path(self):
        src = inspect.getsource(__import__("admin").stale_mark_reviewed)
        assert "validate_path_id" in src

    def test_stale_mark_reviewed_sets_timestamp(self):
        src = inspect.getsource(__import__("admin").stale_mark_reviewed)
        assert "stale_reviewed_at" in src
        assert "isoformat" in src

    def test_stale_queue_missing_fields_constant(self):
        from admin import _STALE_QUEUE_MISSING_FIELDS
        assert "source" in _STALE_QUEUE_MISSING_FIELDS
        assert "images" in _STALE_QUEUE_MISSING_FIELDS
        assert "coordinates" in _STALE_QUEUE_MISSING_FIELDS

    def test_stale_threshold_default(self):
        from admin import _STALE_THRESHOLD_DEFAULT
        assert _STALE_THRESHOLD_DEFAULT == 180


# ── U-24: Q&A quality queue ─────────────────────────────────────────

class TestQAQueue:

    def test_qa_queue_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/qa-queue" in paths

    def test_qa_set_best_answer_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/qa-queue/{post_id}/set-best-answer" in paths

    def test_qa_queue_filters_questions_only(self):
        src = inspect.getsource(__import__("admin").qa_queue)
        assert "post_type = 'question'" in src
        assert "moderation_status = 'approved'" in src

    def test_qa_queue_has_filter_param(self):
        src = inspect.getsource(__import__("admin").qa_queue)
        assert "unanswered" in src
        assert "no_best_answer" in src
        assert "comment_count = 0" in src
        assert "best_answer_id IS NULL" in src

    def test_qa_queue_has_entity_filter(self):
        src = inspect.getsource(__import__("admin").qa_queue)
        assert "entity_id" in src

    def test_qa_queue_response_shape(self):
        src = inspect.getsource(__import__("admin").qa_queue)
        assert '"questions"' in src
        assert '"total"' in src
        assert '"filter"' in src

    def test_set_best_answer_validates_post_type(self):
        src = inspect.getsource(__import__("admin").qa_set_best_answer)
        assert "post_type" in src
        assert "question" in src

    def test_set_best_answer_validates_comment_belongs(self):
        src = inspect.getsource(__import__("admin").qa_set_best_answer)
        assert "post_id::text" in src
        assert "comments" in src

    def test_set_best_answer_body_model(self):
        from admin import SetBestAnswerBody
        m = SetBestAnswerBody(comment_id="abc-123")
        assert m.comment_id == "abc-123"

    def test_set_best_answer_validates_path_id(self):
        src = inspect.getsource(__import__("admin").qa_set_best_answer)
        assert "validate_path_id" in src


# ── U-22: Contact funnel dashboard ──────────────────────────────────

class TestContactFunnel:

    def test_contact_funnel_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/contact-funnel" in paths

    def test_contact_funnel_export_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/contact-funnel/export" in paths

    def test_contact_funnel_has_days_param(self):
        src = inspect.getsource(__import__("admin").contact_funnel)
        assert "days" in src
        assert "ge=1" in src
        assert "le=365" in src

    def test_contact_funnel_has_entity_filter(self):
        src = inspect.getsource(__import__("admin").contact_funnel)
        assert "entity_id" in src

    def test_contact_funnel_reads_jsonl(self):
        src = inspect.getsource(__import__("admin").contact_funnel)
        assert "contact_views.jsonl" in src or "CONTACT_VIEWS_FILE" in src
        assert "json.loads" in src

    def test_contact_funnel_response_shape(self):
        src = inspect.getsource(__import__("admin").contact_funnel)
        assert '"entities"' in src
        assert '"period_days"' in src
        assert '"total_contacts"' in src

    def test_contact_funnel_aggregates_actions(self):
        src = inspect.getsource(__import__("admin").contact_funnel)
        assert '"zalo"' in src
        assert '"phone"' in src
        assert '"website"' in src
        assert '"map"' in src

    def test_contact_funnel_export_csv(self):
        src = inspect.getsource(__import__("admin").contact_funnel_export)
        assert "text/csv" in src
        assert "entity_id,name,zalo,phone,website,map,total" in src

    def test_contact_funnel_sorts_by_total(self):
        src = inspect.getsource(__import__("admin").contact_funnel)
        assert 'key=lambda x: -x[1]["total"]' in src

    def test_contact_funnel_filters_by_cutoff(self):
        src = inspect.getsource(__import__("admin").contact_funnel)
        assert "cutoff" in src
        assert "ts < cutoff" in src
