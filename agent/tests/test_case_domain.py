import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_correction_item_preserves_the_field_level_contract():
    from cases.domain import CorrectionItem, EvidenceLevel, PublicationState, RiskClass

    item = CorrectionItem(
        "item-1", RiskClass.R2, EvidenceLevel.E3, entity_id="entity-1",
        field_path="contact.phone", base_entity_revision=4,
        evidence_refs=("evidence-1",), publication_state=PublicationState.PENDING,
    )
    assert (item.entity_id, item.field_path, item.base_entity_revision) == (
        "entity-1", "contact.phone", 4,
    )
    assert item.publication_state is PublicationState.PENDING
