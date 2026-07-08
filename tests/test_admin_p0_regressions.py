"""P0 AdminCP regression guards."""

import inspect

import admin
import auth_middleware


def test_csrf_accepts_legacy_token_cookie_for_validation():
    src = inspect.getsource(auth_middleware.require_csrf)
    assert 'request.cookies.get("token"' in src
    assert "security_logger.csrf_failure" in src


def test_require_admin_sets_legacy_state_user_alias():
    src = inspect.getsource(admin.require_admin)
    assert "request.state.admin_user = admin_user" in src
    assert "request.state.user = admin_user" in src


def test_set_user_role_has_privilege_boundary_guards():
    # Privilege-boundary + last-admin guards were extracted into module-level helpers
    # (_assert_role_change_allowed / _assert_not_last_admin) during the complexity refactor;
    # set_user_role still wires both. Assert the guards where they now live, plus wiring.
    src = inspect.getsource(admin.set_user_role)
    priv_src = inspect.getsource(admin._assert_role_change_allowed)
    last_src = inspect.getsource(admin._assert_not_last_admin)
    assert "Không thể tự đổi role" in src
    assert "_assert_role_change_allowed" in src   # wiring
    assert "_assert_not_last_admin" in src        # wiring
    assert "role == \"admin\"" in priv_src
    assert "target_role == \"admin\"" in priv_src
    assert "Không thể hạ quyền admin cuối cùng" in last_src


def test_reports_endpoint_supports_all_status_without_details_column():
    src = inspect.getsource(admin.get_reports)
    assert "^(all|pending|resolved|dismissed)$" in src
    assert "to_jsonb(r)->>'details' AS details" in src
    assert "LEFT JOIN users" in src
    assert "require_pg()" in src


def test_badges_and_dashboard_count_pg_reports():
    badge_src = inspect.getsource(admin.badge_counts)
    alerts_src = inspect.getsource(admin.dashboard_alerts)
    assert "FROM reports WHERE status = 'pending'" in badge_src
    assert 'counts["reports"] +=' in badge_src
    assert "FROM reports WHERE status = 'pending'" in alerts_src
    assert "open_reports +=" in alerts_src
    assert 'link": "/admin/bao-cao"' in alerts_src
    assert "/admin/khieu-nai" not in alerts_src


def test_image_suggestion_fetch_revalidates_redirect_targets():
    fetch_src = inspect.getsource(admin._fetch_public_url)
    approve_src = inspect.getsource(admin.approve_image_suggestion)
    assert "follow_redirects=False" in fetch_src
    assert "_assert_public_url(current_url)" in fetch_src
    assert "urljoin" in fetch_src
    assert "follow_redirects=True" not in approve_src


def test_media_gallery_reads_entity_image_credits():
    # The credit-reading logic (image_credits -> credits_by_url -> author/license) lives
    # in the _extract_media_items helper that media_gallery calls to build the gallery.
    # The per-image credit resolution was extracted into _media_item_from_image and then
    # _media_resolve_credit (complexity refactor); _extract_media_items still wires it
    # (image_credits -> credits_by_url) and delegates through to the credit-reader, so
    # assert against the helper that now holds the author/license reads.
    src = inspect.getsource(admin._extract_media_items)
    item_src = inspect.getsource(admin._media_item_from_image)
    credit_src = inspect.getsource(admin._media_resolve_credit)
    assert "image_credits" in src
    assert "credits_by_url" in src
    assert "_media_item_from_image" in src  # wiring: extractor still calls the image-item builder
    assert "_media_resolve_credit" in item_src  # wiring: item builder still calls the credit-reader
    assert 'credit_meta.get("author")' in credit_src
    assert 'credit_meta.get("license")' in credit_src


def test_admin_delete_comment_recomputes_comment_count():
    src = inspect.getsource(admin.admin_delete_comment)
    assert "SELECT COUNT(*) FROM comments" in src
    assert "GREATEST(comment_count - 1" not in src
