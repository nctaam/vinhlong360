def test_case_package_exports_policy_loader():
    from cases import Channel, PublicItemDecision, PublicItemPublication, load_case_policy
    assert load_case_policy().revision == 'correction-pilot-v1'
    assert Channel.WEB.value == 'web'
    assert PublicItemDecision.__name__ == 'PublicItemDecision'
    assert PublicItemPublication.__name__ == 'PublicItemPublication'
