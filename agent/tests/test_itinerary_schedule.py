import math
from dataclasses import FrozenInstanceError

import pytest

from itinerary_schedule import (
    ScheduleOptions,
    ScheduleStop,
    TimeWindow,
    TravelMatrix,
    build_fallback_matrix,
    infer_visit_minutes,
    parse_opening_hours,
    parse_time_range,
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
            TravelMatrix(values, "test")


def test_travel_matrix_allows_unavailable_off_diagonal_edges():
    matrix = TravelMatrix(((0.0, None), (None, 0.0)), "test")

    assert matrix.duration_minutes == ((0.0, None), (None, 0.0))


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
