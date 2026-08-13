from cases.domain import ServiceKind


def test_only_correction_is_the_pilot_service_vocabulary():
    assert ServiceKind.CORRECTION.value == 'correction'
