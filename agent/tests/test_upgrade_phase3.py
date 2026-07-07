"""Tests for Phase 3 upgrade cards: U-17, U-24, U-22, BE-10, BE-5."""
import inspect


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


# ── BE-10: Completeness standalone ──────────────────────────────────

class TestCompletenessEndpoint:

    def test_completeness_overview_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/completeness" in paths

    def test_completeness_details_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/completeness/details" in paths

    def test_completeness_overview_response_shape(self):
        src = inspect.getsource(__import__("admin").completeness_overview)
        assert '"total_entities"' in src
        assert '"source"' in src
        assert '"images"' in src
        assert '"place_id"' in src
        assert '"summary"' in src

    def test_completeness_overview_uses_entity_quality(self):
        src = inspect.getsource(__import__("admin").completeness_overview)
        assert "entity_quality" in src or "data_quality.entity_quality" in src

    def test_completeness_details_has_missing_filter(self):
        src = inspect.getsource(__import__("admin").completeness_details)
        assert "source|images|place|summary" in src

    def test_completeness_details_has_type_filter(self):
        src = inspect.getsource(__import__("admin").completeness_details)
        assert "entity_type" in src

    def test_completeness_details_response_shape(self):
        src = inspect.getsource(__import__("admin").completeness_details)
        assert '"items"' in src
        assert '"total"' in src
        assert '"score"' in src
        assert '"has_source"' in src
        assert '"has_images"' in src

    def test_completeness_details_sorts_by_score(self):
        src = inspect.getsource(__import__("admin").completeness_details)
        assert 'key=lambda x: x["score"]' in src


# ── BE-5: Block enforcement audit ───────────────────────────────────

class TestBlockEnforcementAudit:
    """Verify _block_sql() is applied in all user-facing query functions."""

    def _get_social_source(self):
        import social
        return inspect.getsource(social)

    def test_block_in_search_users(self):
        src = inspect.getsource(__import__("social").search_users)
        assert "_block_sql" in src

    def test_block_in_entity_feed(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "_block_sql" in src

    def test_block_in_suggested_follows(self):
        src = inspect.getsource(__import__("social").suggested_follows)
        assert "_block_sql" in src

    def test_block_in_comments(self):
        src = inspect.getsource(__import__("social").get_comments)
        assert "_block_sql" in src

    def test_block_in_following_feed(self):
        src = inspect.getsource(__import__("social").get_following_feed)
        assert "_block_sql" in src

    def test_block_sql_is_bidirectional(self):
        src = inspect.getsource(__import__("social")._block_sql)
        assert "blocker_id" in src
        assert "blocked_id" in src

    def test_all_read_post_queries_have_block(self):
        """Every GET function that queries posts table should use _block_sql."""
        import social
        read_funcs = ["get_entity_feed", "get_following_feed", "search_users",
                      "suggested_follows", "get_comments"]
        for func_name in read_funcs:
            fn = getattr(social, func_name, None)
            assert fn is not None, f"{func_name} not found in social module"
            fn_src = inspect.getsource(fn)
            assert "_block_sql" in fn_src, f"{func_name} queries posts but has no _block_sql"
