

def test_case_subject_links_policy_is_registered_with_its_retained_record():
    from agent.data_lifecycle import lifecycle_registry

    policy = lifecycle_registry.get("case_subject_links")

    assert policy.classification == "personal"
    assert policy.subject_linked is True
    # The answerable record — cases, decisions, audit — stays by design; this
    # registry reserves retained_fields for aggregate stores, so the policy
    # documents the retention in prose and the erasure suite proves the rows.
    assert policy.retained_fields == ()
    assert "correction-case receipts" in policy.description


def test_case_subject_links_purge_is_a_safe_no_op_off_postgres():
    from agent.data_lifecycle import (
        _purge_case_subject_links,
        _verify_case_subject_links_absent,
    )

    # The kernel is PostgreSQL-only; on SQLite there is nothing to hold, so the
    # erasure pipeline must see "absent" rather than an error it cannot clear.
    purge = _purge_case_subject_links("user:42")
    verify = _verify_case_subject_links_absent("user:42")

    assert purge.complete is True and purge.removed_count == 0
    assert verify.absent is True
