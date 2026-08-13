def test_case_scopes_are_action_scoped():
    from admin_permissions import ADMIN_ROLE_SCOPES, ADMIN_ENTRY_SCOPES
    expected = {"service.operator", "correction.decide", "truth.review", "publication.apply", "case.supervisor"}
    assert expected <= ADMIN_ROLE_SCOPES["admin"]
    assert expected <= ADMIN_ENTRY_SCOPES
    assert not expected & ADMIN_ROLE_SCOPES["moderator"]
