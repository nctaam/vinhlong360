import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_promise_health_converts_shared_clock_validation_to_transition_error():
    from cases.domain import PromiseClock, PromiseHealth
    from cases.transitions import TransitionRejected, promise_health

    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    clock = PromiseClock("update", now.replace(tzinfo=None), now, health=PromiseHealth.ON_TRACK)
    with pytest.raises(TransitionRejected, match="invalid_case_time"):
        promise_health(clock, now=now)
