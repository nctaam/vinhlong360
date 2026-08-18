"""Change sets: immutable, bound to one entity revision, and never applied here."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.correction import (  # noqa: E402
    ChangeSetDraft,
    CorrectionRejected,
    ProposedChange,
    build_patches,
    validate_change_set,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _change(**overrides) -> ProposedChange:
    base = dict(
        item_id="i-1",
        entity_id="p-vinh-long",
        field_path="attributes.phone",
        before_value="0270 111 2222",
        after_value="0270 333 4444",
    )
    base.update(overrides)
    return ProposedChange(**base)


def _draft(**overrides) -> ChangeSetDraft:
    base = dict(
        case_id="c-1",
        entity_id="p-vinh-long",
        base_entity_revision=7,
        changes=(_change(),),
        risk_class="R1",
        decision_maker_ref="person:maker",
        reviewer_ref=None,
        evidence_refs=("e-1",),
    )
    base.update(overrides)
    return ChangeSetDraft(**base)


def test_the_patch_and_its_inverse_are_exact_opposites():
    before, after, inverse = build_patches(_draft())

    assert before == {"attributes.phone": "0270 111 2222"}
    assert after == {"attributes.phone": "0270 333 4444"}
    assert inverse == {"attributes.phone": "0270 111 2222"}


def test_a_no_op_change_is_refused():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(changes=(_change(after_value="0270 111 2222"),)),
            current_entity_revision=7,
            now=NOW,
        )

    assert excinfo.value.problem.code == "change_set_is_a_no_op"


def test_a_bundle_spanning_two_entities_is_refused():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(changes=(_change(), _change(item_id="i-2", entity_id="p-other"))),
            current_entity_revision=7,
            now=NOW,
        )

    assert excinfo.value.problem.code == "change_set_spans_entities"


def test_a_field_outside_the_approved_paths_is_refused():
    for path in ("verifiedAt", "attributes.__proto__", "owner_ref"):
        with pytest.raises(CorrectionRejected) as excinfo:
            validate_change_set(
                _draft(changes=(_change(field_path=path),)),
                current_entity_revision=7,
                now=NOW,
            )
        assert excinfo.value.problem.code == "field_path_not_correctable"


def test_a_change_set_is_refused_when_the_entity_moved_underneath_it():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(_draft(base_entity_revision=7), current_entity_revision=9, now=NOW)

    assert excinfo.value.problem.code == "entity_revision_moved"


def test_two_changes_to_the_same_field_are_refused():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(changes=(_change(), _change(item_id="i-2", after_value="0270 999 0000"))),
            current_entity_revision=7,
            now=NOW,
        )

    assert excinfo.value.problem.code == "duplicate_change_field"


def test_a_high_risk_change_set_carries_its_reviewer():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(
            _draft(risk_class="R3", reviewer_ref=None), current_entity_revision=7, now=NOW
        )
    assert excinfo.value.problem.code == "maker_checker_required"

    accepted = validate_change_set(
        _draft(risk_class="R3", reviewer_ref="person:checker"),
        current_entity_revision=7,
        now=NOW,
    )
    assert accepted.reviewer_ref == "person:checker"


def test_a_change_set_needs_the_evidence_it_rests_on():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_change_set(_draft(evidence_refs=()), current_entity_revision=7, now=NOW)

    assert excinfo.value.problem.code == "evidence_lineage_required"


def test_building_a_change_set_never_reaches_the_entity_writer():
    import inspect

    from cases import correction

    source = inspect.getsource(correction)
    for forbidden in ("upsert_entity", "update_entity", "db.upsert", "entity_writer"):
        assert forbidden not in source
    # apply_status starts pending; publication is a separate, later decision.
    assert 'apply_status' in source and 'pending' in source
