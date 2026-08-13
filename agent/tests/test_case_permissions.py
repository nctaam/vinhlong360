def test_case_scopes_are_effective_for_admin_and_explicit_grants():
    from admin_permissions import ADMIN_ROLE_SCOPES, ADMIN_ENTRY_SCOPES, admin_scopes_for_user
    expected = {"service.operator", "correction.decide", "truth.review", "publication.apply", "case.supervisor"}
    assert expected <= ADMIN_ROLE_SCOPES["admin"]
    assert expected <= ADMIN_ENTRY_SCOPES
    assert not expected & ADMIN_ROLE_SCOPES["moderator"]
    assert expected <= set(admin_scopes_for_user({'role': 'admin'}))
    assert admin_scopes_for_user({'role': 'moderator'}) == ['moderation.manager']
    assert admin_scopes_for_user({'role': 'user', 'admin_scopes': 'truth.review'}) == ['truth.review']
