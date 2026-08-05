"""Unit tests for Phase 3 selection contracts and pruning."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itinerary_selection as selection_module
from itinerary_schedule import (
    ScheduleOptions,
    ScheduleStop,
    TimeWindow,
    build_fallback_matrix,
)
from itinerary_selection import (
    DroppedCandidate,
    SelectionCandidate,
    SelectionOptions,
    prune_candidates,
    select_and_schedule_day,
)


def _latitude_for(stop_id: str) -> float:
    if stop_id == "start":
        return 10.0
    if stop_id == "end":
        return 10.2
    if stop_id.startswith("poi-"):
        return 10.02 + int(stop_id.removeprefix("poi-")) * 0.01
    return 10.1


def candidate(
    stop_id: str,
    reward: float,
    entity_type: str = "attraction",
    area: str = "vinh-long",
    visit: int = 60,
) -> SelectionCandidate:
    return SelectionCandidate(
        stop=ScheduleStop(stop_id, (_latitude_for(stop_id), 106.0), visit),
        reward=reward,
        entity_type=entity_type,
        area=area,
    )


def matrix_for(*stop_ids: str):
    stops = [
        ScheduleStop(stop_id, (_latitude_for(stop_id), 106.0), 0)
        for stop_id in stop_ids
    ]
    return build_fallback_matrix(stops, "driving")


def test_dominance_prune_keeps_higher_reward_shorter_candidate():
    kept, dropped = prune_candidates(
        [
            candidate("good", 10.0, visit=30),
            candidate("dominated", 8.0, visit=60),
        ],
        required_ids=frozenset(),
        max_candidates=20,
    )

    assert [item.stop.id for item in kept] == ["good"]
    assert dropped == (DroppedCandidate("dominated", "dominated"),)


def test_required_candidate_survives_dominance_and_cap():
    candidates = [candidate("required", 1.0, visit=120)] + [
        candidate(
            f"poi-{index}",
            20.0 - index,
            entity_type=f"type-{index}",
            visit=30,
        )
        for index in range(21)
    ]

    kept, dropped = prune_candidates(
        candidates,
        required_ids=frozenset({"required"}),
        max_candidates=20,
    )

    assert "required" in {item.stop.id for item in kept}
    assert any(item.reason == "candidate-cap" for item in dropped)


def test_required_candidate_does_not_dominate_optional_candidate():
    kept, dropped = prune_candidates(
        [
            candidate("required", 10.0, visit=0),
            candidate("optional", 10.0, visit=60),
        ],
        required_ids=frozenset({"required"}),
        max_candidates=20,
    )

    assert {item.stop.id for item in kept} == {"required", "optional"}
    assert dropped == ()


def test_selection_options_reject_invalid_bounds():
    with pytest.raises(ValueError):
        SelectionOptions(target_count=0)
    with pytest.raises(ValueError):
        SelectionOptions(target_count=4, exact_limit=-1)


def test_required_count_cannot_exceed_candidate_cap():
    candidates = [
        candidate(f"poi-{index}", 1.0, entity_type=f"type-{index}")
        for index in range(21)
    ]

    with pytest.raises(ValueError, match="Required"):
        prune_candidates(
            candidates,
            required_ids=frozenset(item.stop.id for item in candidates),
            max_candidates=20,
        )


def test_required_only_selection_schedules_without_optional_search():
    candidates = [
        candidate("start", 2.0, visit=0),
        candidate("end", 3.0, visit=0),
    ]

    result = select_and_schedule_day(
        candidates=candidates,
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for("start", "end"),
        schedule_options=ScheduleOptions(),
        selection_options=SelectionOptions(target_count=2),
    )

    assert result.selected_ids == ("start", "end")
    assert result.selected_count == 2
    assert result.total_reward == 5.0


def test_exact_selection_prefers_more_feasible_content_then_reward():
    result = select_and_schedule_day(
        candidates=[
            candidate("start", 1.0, visit=0),
            candidate("high", 10.0, visit=120),
            candidate("medium", 8.0, visit=60),
            candidate("end", 1.0, visit=0),
        ],
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for("start", "high", "medium", "end"),
        schedule_options=ScheduleOptions(day_start_minute=480, day_end_minute=660),
        selection_options=SelectionOptions(target_count=3, exact_limit=8),
    )

    assert result.selected_count == 3
    assert set(result.selected_ids) == {"start", "high", "end"}
    assert result.solver == "selection-exact"


def test_exact_selection_drops_optional_with_explicit_reason_when_window_overflows():
    result = select_and_schedule_day(
        candidates=[
            candidate("start", 1.0, visit=0),
            candidate("long", 9.0, visit=180),
            candidate("end", 1.0, visit=0),
        ],
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for("start", "long", "end"),
        schedule_options=ScheduleOptions(day_start_minute=480, day_end_minute=540),
        selection_options=SelectionOptions(target_count=2, exact_limit=8),
    )

    assert result.selected_ids == ("start", "end")
    assert result.dropped == (DroppedCandidate("long", "time-window-overflow"),)


def test_exact_selection_keeps_fixed_meal_in_feasibility():
    result = select_and_schedule_day(
        candidates=[
            candidate("start", 1.0, visit=0),
            candidate("poi", 8.0, visit=60),
            candidate("end", 1.0, visit=0),
        ],
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(
            ScheduleStop(
                "meal",
                (10.1, 106.0),
                60,
                (TimeWindow(720, 780),),
                True,
            ),
        ),
        matrix=matrix_for("start", "poi", "meal", "end"),
        schedule_options=ScheduleOptions(day_start_minute=480, day_end_minute=840),
        selection_options=SelectionOptions(target_count=3, exact_limit=8),
    )

    assert "meal" in result.schedule.ordered_ids


def test_exact_selection_preserves_required_endpoint_input_order():
    result = select_and_schedule_day(
        candidates=[
            candidate("start", 1.0, visit=0),
            candidate("end", 2.0, visit=0),
        ],
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for("start", "end"),
        schedule_options=ScheduleOptions(),
        selection_options=SelectionOptions(target_count=2),
    )

    assert result.schedule.ordered_ids[0] == "start"
    assert result.schedule.ordered_ids[-1] == "end"


def test_exact_selection_filters_blocked_edges_for_excluded_candidates():
    result = select_and_schedule_day(
        candidates=[
            candidate("start", 1.0, visit=0),
            candidate("blocked", 9.0, visit=30),
            candidate("end", 1.0, visit=0),
        ],
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for("start", "blocked", "end"),
        schedule_options=ScheduleOptions(
            blocked_edges=frozenset({("start", "blocked")}),
        ),
        selection_options=SelectionOptions(target_count=2),
    )

    assert result.selected_ids == ("start", "end")
    assert result.dropped == (DroppedCandidate("blocked", "unreachable-edge"),)


def test_exact_selection_prunes_visit_time_lower_bound_before_scheduler(
    monkeypatch,
):
    real_schedule = selection_module.schedule_stop_order
    scheduled_ids = []

    def counted_schedule(stops, matrix, options):
        scheduled_ids.append(tuple(stop.id for stop in stops))
        return real_schedule(stops, matrix, options)

    monkeypatch.setattr(selection_module, "schedule_stop_order", counted_schedule)
    result = select_and_schedule_day(
        candidates=[
            candidate("start", 1.0, visit=0),
            candidate("long", 9.0, visit=180),
            candidate("end", 1.0, visit=0),
        ],
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for("start", "long", "end"),
        schedule_options=ScheduleOptions(day_start_minute=480, day_end_minute=540),
        selection_options=SelectionOptions(target_count=3),
    )

    assert result.dropped == (DroppedCandidate("long", "time-window-overflow"),)
    assert scheduled_ids == [("start", "end")]


def run_selection(candidates, target_count, exact_limit):
    start = candidate("start", 1.0, visit=0)
    end = candidate("end", 1.0, visit=0)
    pool = [start, *candidates, end]
    ids = tuple(item.stop.id for item in pool)
    return select_and_schedule_day(
        candidates=pool,
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for(*ids),
        schedule_options=ScheduleOptions(day_start_minute=480, day_end_minute=1080),
        selection_options=SelectionOptions(
            target_count=target_count,
            exact_limit=exact_limit,
        ),
    )


def test_beam_selection_is_deterministic_for_large_pool():
    candidates = [
        candidate(
            f"poi-{index}",
            20.0 - index / 10,
            entity_type=f"type-{index}",
            visit=15,
        )
        for index in range(12)
    ]

    first = run_selection(candidates, target_count=5, exact_limit=2)
    second = run_selection(candidates, target_count=5, exact_limit=2)

    assert first == second
    assert first.solver == "selection-beam"
    assert first.selected_count == 5


def test_repair_replaces_a_greedy_long_stop_to_restore_cardinality():
    start = candidate("start", 1.0, visit=0)
    end = candidate("end", 1.0, visit=0)
    pool = [
        start,
        candidate("trap", 30.0, entity_type="trap", visit=540),
        candidate("high", 20.0, entity_type="high", visit=30),
        candidate("short", 19.0, entity_type="short", visit=30),
        end,
    ]

    def run(repair_iterations):
        return select_and_schedule_day(
            candidates=pool,
            required_ids=frozenset({"start", "end"}),
            fixed_stops=(),
            matrix=matrix_for(*(item.stop.id for item in pool)),
            schedule_options=ScheduleOptions(
                day_start_minute=480,
                day_end_minute=1080,
            ),
            selection_options=SelectionOptions(
                target_count=4,
                exact_limit=2,
                beam_width=1,
                repair_iterations=repair_iterations,
            ),
        )

    without_repair = run(repair_iterations=0)
    result = run(repair_iterations=32)

    assert without_repair.selected_count == 3
    assert "trap" in without_repair.selected_ids
    assert result.selected_count == 4
    assert "high" in result.selected_ids
    assert "short" in result.selected_ids
    assert "trap" not in result.selected_ids


# ── Lưới an toàn cho refactor complexity R20.8 (2026-08-05) ──────────────────
# Các __post_init__ dưới đây sắp được tách thành vị từ. Ghim TỪNG thông điệp
# lỗi trước, để bản tách nào đổi hành vi là đỏ ngay — không dựa vào việc đọc lại
# diff bằng mắt.

import math  # noqa: E402

from itinerary_schedule import ScheduleResult, TravelMatrix  # noqa: E402
from itinerary_selection import SelectionResult  # noqa: E402


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"reward": -1.0}, "Reward phải là số hữu hạn không âm"),
        ({"reward": math.nan}, "Reward phải là số hữu hạn không âm"),
        ({"reward": math.inf}, "Reward phải là số hữu hạn không âm"),
        ({"reward": True}, "Reward phải là số hữu hạn không âm"),
        ({"entity_type": ""}, "Loại entity không được để trống"),
        ({"entity_type": "   "}, "Loại entity không được để trống"),
        ({"area": ""}, "Khu vực không được để trống"),
        ({"area": "  "}, "Khu vực không được để trống"),
        ({"fee_value": -1.0}, "Phí phải là số hữu hạn không âm"),
        ({"fee_value": math.nan}, "Phí phải là số hữu hạn không âm"),
        ({"fee_value": True}, "Phí phải là số hữu hạn không âm"),
    ],
)
def test_selection_candidate_tu_choi_truong_khong_hop_le(kwargs, message):
    base = {
        "stop": ScheduleStop("a", (10.0, 106.0), 30),
        "reward": 1.0,
        "entity_type": "attraction",
        "area": "vinh-long",
    }
    with pytest.raises(ValueError, match=message):
        SelectionCandidate(**{**base, **kwargs})


def test_selection_candidate_tu_choi_stop_sai_kieu():
    with pytest.raises(ValueError, match="Candidate phải chứa ScheduleStop"):
        SelectionCandidate(stop="a", reward=1.0, entity_type="attraction", area="vinh-long")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"target_count": True}, "Số POI mục tiêu phải lớn hơn 0"),
        ({"target_count": 0}, "Số POI mục tiêu phải lớn hơn 0"),
        ({"exact_limit": True}, "Ngưỡng giải chính xác không được âm"),
        ({"exact_limit": -1}, "Ngưỡng giải chính xác không được âm"),
        ({"beam_width": 0}, "Độ rộng beam search phải lớn hơn 0"),
        ({"repair_iterations": -1}, "Số iteration repair không được âm"),
        ({"deadline_seconds": 0}, "Deadline phải là số hữu hạn dương"),
        ({"deadline_seconds": math.inf}, "Deadline phải là số hữu hạn dương"),
    ],
)
def test_selection_options_tu_choi_so_khong_hop_le(kwargs, message):
    with pytest.raises(ValueError, match=message):
        SelectionOptions(**{"target_count": 3, **kwargs})


def _schedule_result_rong() -> ScheduleResult:
    """ScheduleResult tối thiểu, hợp lệ — chỉ để SelectionResult chịu nhận."""
    return ScheduleResult(
        ordered_ids=(), placements=(), skipped=(), total_travel_minutes=0.0,
        waiting_minutes=0.0, overtime_minutes=0.0, minimum_slack_minutes=0.0,
        geometric_distance_km=0.0, backtrack_ratio=0.0, solver="test",
        matrix_source="test", warnings=(),
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"selected_ids": ("a", "a")}, "Selected ID không được trùng"),
        ({"dropped": ("khong-phai-dropped",)}, "Dropped phải gồm DroppedCandidate"),
        ({"candidate_count": -1}, "Candidate count không được âm"),
        ({"selected_count": -1}, "Selected count không hợp lệ"),
        ({"selected_count": 99, "candidate_count": 1}, "Selected count không hợp lệ"),
        ({"total_reward": -1.0}, "Total reward phải là số hữu hạn không âm"),
        ({"total_reward": math.nan}, "Total reward phải là số hữu hạn không âm"),
        ({"total_reward": True}, "Total reward phải là số hữu hạn không âm"),
    ],
)
def test_selection_result_tu_choi_truong_khong_hop_le(kwargs, message):
    base = {
        "schedule": _schedule_result_rong(), "selected_ids": (), "dropped": (),
        "candidate_count": 0, "selected_count": 0, "total_reward": 0.0,
        "solver": "test", "warnings": (),
    }
    with pytest.raises(ValueError, match=message):
        SelectionResult(**{**base, **kwargs})


def test_ghim_bat_nhat_bool_giua_selection_options_va_selection_result():
    """QUẢ MÌN 1 — hai lớp đối xử với bool KHÁC nhau, và đó là hành vi hiện tại.

    SelectionOptions loại bool (isinstance(x, bool) tường minh), còn SelectionResult
    chỉ dùng `not isinstance(x, int)` mà bool LÀ int trong Python → lọt. Test này
    ghim sự bất nhất để bản refactor nào "dọn dẹp" cho nhất quán sẽ đỏ ngay, buộc
    người sửa phải quyết định có chủ đích thay vì đổi thầm.
    """
    with pytest.raises(ValueError):
        SelectionOptions(target_count=True)

    accepted = SelectionResult(
        schedule=_schedule_result_rong(), selected_ids=(), dropped=(),
        candidate_count=True, selected_count=0, total_reward=0.0,
        solver="test", warnings=(),
    )
    assert accepted.candidate_count is True


def test_ghim_bat_nhat_whitespace_giua_travel_matrix_va_blocked_edges():
    """QUẢ MÌN 2 — TravelMatrix dùng .strip(), blocked_edges thì không.

    `TravelMatrix(stop_ids=(' ',))` bị từ chối, còn `ScheduleOptions(blocked_edges=
    {(' ', 'b')})` được nhận. Gộp hai chỗ vào chung một vị từ `_is_filled_str` sẽ
    siết ngầm blocked_edges — test này là cái chặn.
    """
    with pytest.raises(ValueError):
        TravelMatrix(stop_ids=(" ",), duration_minutes=((0.0,),), source="test")

    options = ScheduleOptions(blocked_edges={(" ", "b")})
    assert (" ", "b") in options.blocked_edges


@pytest.mark.parametrize(
    ("value", "expected"),
    [("a", True), (" a ", True), ("", False), ("   ", False), (None, False), (1, False)],
)
def test_is_filled_str(value, expected):
    """Bản của itinerary_selection CÓ .strip() — khác _coerce_blocked_edges."""
    from itinerary_selection import _is_filled_str

    assert _is_filled_str(value) is expected
