def test_case_package_exports_policy_loader():
    from cases import load_case_policy
    assert load_case_policy().revision == 'correction-pilot-v1'
