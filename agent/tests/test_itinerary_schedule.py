import math
from dataclasses import FrozenInstanceError

import pytest
import itinerary_schedule

from itinerary_schedule import (
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleStop,
    SkippedStop,
    TimeWindow,
    TravelMatrix,
    build_fallback_matrix,
    infer_visit_minutes,
    parse_opening_hours,
    parse_time_range,
    schedule_stop_order,
)


def matrix(ids, values):
    return TravelMatrix(tuple(ids), tuple(tuple(row) for row in values), "test")


def test_exact_solver_waits_for_opening_and_keeps_endpoints():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("late", (10.0, 106.3), 30, (TimeWindow(600, 720),)),
        ScheduleStop("early", (10.0, 106.2), 30, (TimeWindow(480, 570),)),
        ScheduleStop("end", (10.0, 106.5), 0),
    ]
    result = schedule_stop_order(
        stops,
        matrix(
            ["start", "late", "early", "end"],
            [[0, 20, 10, 40], [20, 0, 20, 20], [10, 20, 0, 30], [40, 20, 30, 0]],
        ),
        ScheduleOptions(day_start_minute=480, day_end_minute=900),
    )
    assert result.ordered_ids == ("start", "early", "late", "end")
    assert result.placements[1].start_visit_minute == 490
    assert result.placements[2].start_visit_minute >= 600
    assert result.overtime_minutes == 0


def test_required_stop_with_impossible_window_raises_without_partial_output():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("closed", (10.0, 106.1), 90, (TimeWindow(480, 500),)),
        ScheduleStop("end", (10.0, 106.2), 0),
    ]
    with pytest.raises(NoFeasibleScheduleError, match="closed"):
        schedule_stop_order(
            stops,
            matrix(["start", "closed", "end"], [[0, 10, 20], [10, 0, 10], [20, 10, 0]]),
            ScheduleOptions(day_start_minute=480, day_end_minute=900),
        )


def test_optional_stop_is_dropped_with_a_reason_when_day_is_overloaded():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("must", (10.0, 106.1), 500, required=True),
        ScheduleStop("optional", (10.0, 106.2), 500, required=False),
        ScheduleStop("end", (10.0, 106.3), 0),
    ]
    result = schedule_stop_order(
        stops,
        matrix(
            ["start", "must", "optional", "end"],
            [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]],
        ),
        ScheduleOptions(day_start_minute=480, day_end_minute=1200),
    )
    assert result.ordered_ids == ("start", "must", "end")
    assert result.skipped == (SkippedStop("optional", "day-window-overflow"),)


def test_beam_solver_is_deterministic_for_twenty_stops():
    middle = [ScheduleStop(f"p{i}", (10.0, 106.0 + i * 0.01), 10) for i in range(1, 19)]
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        *reversed(middle),
        ScheduleStop("end", (10.0, 106.2), 0),
    ]
    values = [[0 if i == j else 2 for j in range(20)] for i in range(20)]
    first = schedule_stop_order(
        stops, matrix([s.id for s in stops], values), ScheduleOptions(exact_limit=10)
    )
    second = schedule_stop_order(
        stops, matrix([s.id for s in stops], values), ScheduleOptions(exact_limit=10)
    )
    assert first.ordered_ids == second.ordered_ids
    assert first.solver == "schedule-beam"


def test_matrix_ids_are_used_instead_of_assuming_stop_input_order():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("middle", (10.0, 106.1), 20),
        ScheduleStop("end", (10.0, 106.2), 0),
    ]
    result = schedule_stop_order(
        stops,
        matrix(
            ["end", "middle", "start"],
            [[0, 7, 50], [7, 0, 5], [50, 5, 0]],
        ),
        ScheduleOptions(day_start_minute=480, day_end_minute=600),
    )

    assert result.ordered_ids == ("start", "middle", "end")
    assert result.total_travel_minutes == 12


def test_result_reports_time_and_geometry_diagnostics():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("middle", (10.0, 106.1), 20, (TimeWindow(500, 600),)),
        ScheduleStop("end", (10.0, 106.2), 0),
    ]
    result = schedule_stop_order(
        stops,
        matrix(["start", "middle", "end"], [[0, 10, 50], [10, 0, 15], [50, 15, 0]]),
        ScheduleOptions(day_start_minute=480, day_end_minute=900),
    )

    assert result.placements[1].arrival_minute == 490
    assert result.placements[1].start_visit_minute == 500
    assert result.placements[1].finish_visit_minute == 520
    assert result.waiting_minutes == 10
    assert result.minimum_slack_minutes == 80
    assert result.geometric_distance_km > 0
    assert result.backtrack_ratio == pytest.approx(0.0, abs=1e-9)
    assert result.matrix_source == "test"


def test_first_hop_travel_can_make_a_required_stop_infeasible():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("middle", (10.0, 106.1), 30),
        ScheduleStop("end", (10.0, 106.2), 0),
    ]

    with pytest.raises(NoFeasibleScheduleError, match="middle"):
        schedule_stop_order(
            stops,
            matrix(
                ["start", "middle", "end"],
                [[0, 50, 70], [50, 0, 20], [70, 20, 0]],
            ),
            ScheduleOptions(day_start_minute=480, day_end_minute=540),
        )


def test_blocked_edge_names_required_stop_that_cannot_be_reached():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("middle", (10.0, 106.1), 20),
        ScheduleStop("end", (10.0, 106.2), 0),
    ]

    with pytest.raises(NoFeasibleScheduleError, match="middle"):
        schedule_stop_order(
            stops,
            matrix(["start", "middle", "end"], [[0, 10, 20], [10, 0, 10], [20, 10, 0]]),
            ScheduleOptions(blocked_edges=frozenset({("start", "middle")})),
        )


def test_local_repair_improves_a_narrow_beam_route():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("a", (10.0, 106.1), 0),
        ScheduleStop("b", (10.0, 106.2), 0),
        ScheduleStop("end", (10.0, 106.3), 0),
    ]
    result = schedule_stop_order(
        stops,
        matrix(
            ["start", "a", "b", "end"],
            [[0, 1, 2, 50], [1, 0, 100, 1], [2, 1, 0, 1], [50, 1, 1, 0]],
        ),
        ScheduleOptions(exact_limit=0, beam_width=1, station_tolerance=1.0),
    )

    assert result.ordered_ids == ("start", "b", "a", "end")
    assert result.total_travel_minutes == 4


def test_local_repair_uses_single_stop_relocate_for_a_nonadjacent_move():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("a", (10.0, 106.1), 0),
        ScheduleStop("b", (10.0, 106.2), 0),
        ScheduleStop("c", (10.0, 106.3), 0),
        ScheduleStop("d", (10.0, 106.4), 0),
        ScheduleStop("end", (10.0, 106.5), 0),
    ]
    result = schedule_stop_order(
        stops,
        matrix(
            ["start", "a", "b", "c", "d", "end"],
            [
                [0, 0, 10, 100, 100, 100],
                [100, 0, 1, 100, 100, 1],
                [100, 100, 0, 1, 100, 1],
                [100, 100, 100, 0, 1, 100],
                [100, 1, 100, 100, 0, 100],
                [100, 100, 100, 100, 100, 0],
            ],
        ),
        ScheduleOptions(exact_limit=0, beam_width=1, station_tolerance=1.0),
    )

    assert result.ordered_ids == ("start", "b", "c", "d", "a", "end")
    assert result.total_travel_minutes == 14


def test_local_repair_uses_two_stop_or_opt_to_escape_relocate_local_optimum():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("a", (10.0, 106.1), 0),
        ScheduleStop("b", (10.0, 106.2), 0),
        ScheduleStop("c", (10.0, 106.3), 0),
        ScheduleStop("d", (10.0, 106.4), 0),
        ScheduleStop("end", (10.0, 106.5), 0),
    ]
    result = schedule_stop_order(
        stops,
        matrix(
            ["start", "a", "b", "c", "d", "end"],
            [
                [0, 0, 100, 10, 100, 100],
                [100, 0, 1, 100, 100, 100],
                [100, 100, 0, 1, 100, 1],
                [100, 100, 100, 0, 1, 100],
                [100, 1, 100, 100, 0, 100],
                [100, 100, 100, 100, 100, 0],
            ],
        ),
        ScheduleOptions(exact_limit=0, beam_width=1, station_tolerance=1.0),
    )

    assert result.ordered_ids == ("start", "c", "d", "a", "b", "end")
    assert result.total_travel_minutes == 14


def test_optional_drop_prefers_the_highest_burden():
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("large", (10.0, 106.1), 200, required=False),
        ScheduleStop("small", (10.0, 106.2), 100, required=False),
        ScheduleStop("must", (10.0, 106.3), 100),
        ScheduleStop("end", (10.0, 106.4), 0),
    ]
    values = [
        [0 if source == target else 1 for target in range(5)] for source in range(5)
    ]
    result = schedule_stop_order(
        stops,
        matrix([stop.id for stop in stops], values),
        ScheduleOptions(day_start_minute=480, day_end_minute=780),
    )

    assert result.skipped == (SkippedStop("large", "day-window-overflow"),)
    assert result.ordered_ids == ("start", "small", "must", "end")


def test_deadline_never_returns_a_partial_schedule(monkeypatch):
    stops = [
        ScheduleStop("start", (10.0, 106.0), 0),
        ScheduleStop("middle", (10.0, 106.1), 10),
        ScheduleStop("end", (10.0, 106.2), 0),
    ]
    clock = iter((0.0, 2.0, 2.0, 2.0))
    monkeypatch.setattr(itinerary_schedule.time, "perf_counter", lambda: next(clock))

    with pytest.raises(NoFeasibleScheduleError):
        schedule_stop_order(
            stops,
            matrix(["start", "middle", "end"], [[0, 1, 2], [1, 0, 1], [2, 1, 0]]),
            ScheduleOptions(deadline_seconds=1.0),
        )


def test_parse_time_range_accepts_vietnamese_hour_forms():
    assert parse_time_range("7h30 - 17h") == TimeWindow(450, 1020)
    assert parse_time_range("7h-17h") == TimeWindow(420, 1020)
    assert parse_time_range("08:00-11:30") == TimeWindow(480, 690)


def test_parse_time_range_rejects_unsupported_or_invalid_text():
    assert parse_time_range("7 giờ sáng đến 5 giờ chiều") is None
    assert parse_time_range("24:30-25:00") is None


def test_parse_opening_hours_returns_windows_and_nonfatal_warning():
    windows, warnings = parse_opening_hours("T2-T6: 07:30-11:30, 13:00-17:00")
    assert windows == (TimeWindow(450, 690), TimeWindow(780, 1020))
    assert "weekday-specific-hours-ignored" in warnings


def test_parse_opening_hours_warns_for_weekday_prefix_without_colon():
    windows, warnings = parse_opening_hours("T2-T6 07:30-11:30")

    assert windows == (TimeWindow(450, 690),)
    assert "weekday-specific-hours-ignored" in warnings


def test_invalid_hours_are_unknown_not_open_all_day():
    windows, warnings = parse_opening_hours("liên hệ trước")
    assert windows == ()
    assert "opening-hours-unknown" in warnings


def test_parse_time_range_rejects_one_digit_h_minutes():
    assert parse_time_range("7h5-17h") is None


def test_parse_opening_hours_does_not_trust_one_digit_h_minutes():
    windows, warnings = parse_opening_hours("7h5-17h")

    assert windows == ()
    assert "opening-hours-unknown" in warnings


@pytest.mark.parametrize(
    ("start_minute", "end_minute"),
    [(-1, 60), (120, 119), (0, 1441)],
)
def test_time_window_rejects_values_outside_one_day(start_minute, end_minute):
    with pytest.raises(ValueError):
        TimeWindow(start_minute, end_minute)


def test_time_window_is_immutable():
    window = TimeWindow(480, 600)

    with pytest.raises(FrozenInstanceError):
        window.start_minute = 500


@pytest.mark.parametrize(
    ("stop_id", "coordinates", "visit_minutes"),
    [
        ("", (10.0, 106.0), 30),
        ("a", (math.nan, 106.0), 30),
        ("a", (10.0, math.inf), 30),
        ("a", ("north", 106.0), 30),
        ("a", (10.0,), 30),
        ("a", (10.0, 106.0), -1),
        ("a", (10.0, 106.0), 721),
    ],
)
def test_schedule_stop_rejects_invalid_core_fields(
    stop_id,
    coordinates,
    visit_minutes,
):
    with pytest.raises(ValueError):
        ScheduleStop(stop_id, coordinates, visit_minutes)


def test_travel_matrix_requires_square_nonnegative_values_and_zero_diagonal():
    invalid_matrices = (
        ((0.0, 1.0),),
        ((0.0, -1.0), (-1.0, 0.0)),
        ((0.0, math.inf), (1.0, 0.0)),
        ((None, 1.0), (1.0, 0.0)),
        ((1.0,),),
    )

    for values in invalid_matrices:
        with pytest.raises(ValueError):
            TravelMatrix(
                tuple(str(index) for index in range(len(values))), values, "test"
            )


def test_travel_matrix_allows_unavailable_off_diagonal_edges():
    matrix = TravelMatrix(("a", "b"), ((0.0, None), (None, 0.0)), "test")

    assert matrix.duration_minutes == ((0.0, None), (None, 0.0))


def test_travel_matrix_requires_unique_ids_matching_its_dimensions():
    with pytest.raises(ValueError, match="ID"):
        TravelMatrix(("same", "same"), ((0.0, 1.0), (1.0, 0.0)), "test")
    with pytest.raises(ValueError, match="ID"):
        TravelMatrix(("only-one",), ((0.0, 1.0), (1.0, 0.0)), "test")


def test_schedule_options_have_planner_defaults():
    options = ScheduleOptions()

    assert options.day_start_minute == 480
    assert options.day_end_minute == 1080
    assert options.exact_limit == 10
    assert options.beam_width == 64
    assert options.station_tolerance == 0.02
    assert options.deadline_seconds == 2.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"day_start_minute": -1},
        {"day_start_minute": 600, "day_end_minute": 599},
        {"day_end_minute": 1441},
        {"exact_limit": -1},
        {"beam_width": 0},
        {"station_tolerance": -0.01},
        {"deadline_seconds": 0},
    ],
)
def test_schedule_options_reject_invalid_search_bounds(overrides):
    with pytest.raises(ValueError):
        ScheduleOptions(**overrides)


@pytest.mark.parametrize("blocked_edges", [frozenset({"ab"}), (12,)])
def test_schedule_options_rejects_malformed_blocked_edges(blocked_edges):
    with pytest.raises(ValueError, match="Cạnh bị cấm"):
        ScheduleOptions(blocked_edges=blocked_edges)


def test_visit_duration_uses_explicit_value_then_suggested_text_then_type_default():
    assert infer_visit_minutes("attraction", 75, None) == 75
    assert infer_visit_minutes("attraction", None, "1 giờ 30 phút") == 90
    assert infer_visit_minutes("attraction", None, None) == 90


@pytest.mark.parametrize(
    ("entity_type", "expected_minutes"),
    [
        ("experience", 120),
        ("craft village", 60),
        ("dish", 45),
        ("product", 30),
        ("history", 60),
        ("nature", 90),
        ("person", 30),
        ("event", 120),
        ("economy", 30),
        ("accommodation", 0),
        ("other", 60),
    ],
)
def test_visit_duration_has_type_specific_fallbacks(entity_type, expected_minutes):
    assert infer_visit_minutes(entity_type, None, None) == expected_minutes


def test_visit_duration_parses_hour_only_and_minute_only_phrases():
    assert infer_visit_minutes("unknown", None, "khoảng 2 giờ") == 120
    assert infer_visit_minutes("unknown", None, "tham quan 45 phút") == 45


def test_fallback_matrix_is_zero_diagonal_and_mode_aware():
    stops = [
        ScheduleStop("a", (10.0, 106.0), 0),
        ScheduleStop("b", (10.0, 106.1), 30),
    ]
    matrix = build_fallback_matrix(stops, "driving")

    assert matrix.source == "haversine-fallback"
    assert matrix.stop_ids == ("a", "b")
    assert matrix.duration_minutes[0][0] == 0.0
    assert matrix.duration_minutes[0][1] == pytest.approx(16.43, abs=0.02)
    assert matrix.duration_minutes[1][0] == matrix.duration_minutes[0][1]


def test_fallback_matrix_uses_each_supported_mode_speed():
    stops = [
        ScheduleStop("a", (10.0, 106.0), 0),
        ScheduleStop("b", (10.0, 106.1), 30),
    ]

    driving = build_fallback_matrix(stops, "driving").duration_minutes[0][1]
    cycling = build_fallback_matrix(stops, "cycling").duration_minutes[0][1]
    foot = build_fallback_matrix(stops, "foot").duration_minutes[0][1]

    assert cycling == pytest.approx(driving * 40 / 15)
    assert foot == pytest.approx(driving * 40 / 5)


def test_fallback_matrix_rejects_an_unknown_mode():
    with pytest.raises(ValueError, match="mode"):
        build_fallback_matrix([ScheduleStop("a", (10.0, 106.0), 0)], "flying")


# ── Vị từ dùng chung, tách ra khi hạ complexity 5 __post_init__ (2026-08-05) ──

@pytest.mark.parametrize(
    ("value", "minimum", "expected"),
    [
        (3, 0, True), (0, 0, True), (-1, 0, False), (0, 1, False),
        (True, 0, False),      # bool là int trong Python — phải bị loại
        (3.0, 0, False),       # float không phải int
        ("3", 0, False),
    ],
)
def test_is_int_at_least(value, minimum, expected):
    from itinerary_schedule import _is_int_at_least

    assert _is_int_at_least(value, minimum) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, True), (0.0, True), (2.5, True), (-0.1, False),
        (math.nan, False), (math.inf, False), (-math.inf, False),
        (True, False), (None, False), ("1", False),
    ],
)
def test_is_finite_nonneg(value, expected):
    from itinerary_schedule import _is_finite_nonneg

    assert _is_finite_nonneg(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.1, True), (2, True), (0, False), (-1, False), (math.inf, False), (True, False)],
)
def test_is_finite_positive(value, expected):
    from itinerary_schedule import _is_finite_positive

    assert _is_finite_positive(value) is expected


def test_coerce_blocked_edges_giu_dung_do_long_leo_ve_khoang_trang():
    """Vị từ này CỐ Ý lỏng hơn _coerce_matrix_ids — xem comment trong code."""
    from itinerary_schedule import _coerce_blocked_edges

    assert _coerce_blocked_edges({(" ", "b")}) == frozenset({(" ", "b")})
    with pytest.raises(ValueError, match="Cạnh bị cấm phải là cặp ID điểm dừng"):
        _coerce_blocked_edges({("a", "b", "c")})
    with pytest.raises(ValueError, match="Cạnh bị cấm phải là cặp ID điểm dừng"):
        _coerce_blocked_edges({("a", "")})


def test_coerce_matrix_ids_bat_id_toan_khoang_trang():
    from itinerary_schedule import _coerce_matrix_ids

    assert _coerce_matrix_ids(["a", "b"]) == ("a", "b")
    with pytest.raises(ValueError, match="ID ma trận không được để trống"):
        _coerce_matrix_ids([" "])
    with pytest.raises(ValueError, match="ID ma trận không được trùng"):
        _coerce_matrix_ids(["a", "a"])


def test_validate_matrix_cells_bat_duong_cheo_khac_khong():
    from itinerary_schedule import _validate_matrix_cells

    _validate_matrix_cells(((0.0, 5.0), (5.0, 0.0)))
    with pytest.raises(ValueError, match="Đường chéo ma trận thời gian phải bằng 0"):
        _validate_matrix_cells(((1.0, 5.0), (5.0, 0.0)))
    with pytest.raises(ValueError, match="Đường chéo ma trận thời gian phải bằng 0"):
        _validate_matrix_cells(((None, 5.0), (5.0, 0.0)))
    with pytest.raises(ValueError, match="Thời gian di chuyển phải là số hoặc None"):
        _validate_matrix_cells(((0.0, True), (5.0, 0.0)))
