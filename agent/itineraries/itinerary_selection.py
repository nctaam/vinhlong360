"""Dependency-free candidate pruning and selection contracts."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import combinations
import time
from typing import Sequence

from itineraries.itinerary_schedule import (
    _is_finite_nonneg,
    _is_finite_positive,
    _is_int_at_least,
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleResult,
    ScheduleStop,
    TravelMatrix,
    schedule_stop_order,
)


def _is_filled_str(value: object) -> bool:
    """Chuỗi có nội dung. CỐ Ý dùng .strip() — khác `_coerce_blocked_edges`
    bên itinerary_schedule vốn chỉ kiểm `not stop_id`. Đừng gộp hai chỗ."""
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True)
class SelectionCandidate:
    stop: ScheduleStop
    reward: float
    entity_type: str
    area: str
    fee_value: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stop, ScheduleStop):
            raise ValueError("Candidate phải chứa ScheduleStop")
        if not _is_finite_nonneg(self.reward):
            raise ValueError("Reward phải là số hữu hạn không âm")
        if not _is_filled_str(self.entity_type):
            raise ValueError("Loại entity không được để trống")
        if not _is_filled_str(self.area):
            raise ValueError("Khu vực không được để trống")
        if self.fee_value is not None and not _is_finite_nonneg(self.fee_value):
            raise ValueError("Phí phải là số hữu hạn không âm")
        object.__setattr__(self, "reward", float(self.reward))
        object.__setattr__(self, "entity_type", self.entity_type.strip())
        object.__setattr__(self, "area", self.area.strip())


@dataclass(frozen=True)
class SelectionOptions:
    target_count: int
    exact_limit: int = 8
    beam_width: int = 32
    repair_iterations: int = 32
    deadline_seconds: float = 1.5

    def __post_init__(self) -> None:
        if not _is_int_at_least(self.target_count, 1):
            raise ValueError("Số POI mục tiêu phải lớn hơn 0")
        if not _is_int_at_least(self.exact_limit, 0):
            raise ValueError("Ngưỡng giải chính xác không được âm")
        if not _is_int_at_least(self.beam_width, 1):
            raise ValueError("Độ rộng beam search phải lớn hơn 0")
        if not _is_int_at_least(self.repair_iterations, 0):
            raise ValueError("Số iteration repair không được âm")
        if not _is_finite_positive(self.deadline_seconds):
            raise ValueError("Deadline phải là số hữu hạn dương")


@dataclass(frozen=True)
class DroppedCandidate:
    stop_id: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.stop_id, str) or not self.stop_id.strip():
            raise ValueError("ID candidate bị loại không được để trống")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Lý do loại candidate không được để trống")


@dataclass(frozen=True)
class SelectionResult:
    schedule: ScheduleResult
    selected_ids: tuple[str, ...]
    dropped: tuple[DroppedCandidate, ...]
    candidate_count: int
    selected_count: int
    total_reward: float
    solver: str
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.schedule, ScheduleResult):
            raise ValueError("SelectionResult phải chứa ScheduleResult")
        selected_ids = tuple(self.selected_ids)
        dropped = tuple(self.dropped)
        if len(selected_ids) != len(set(selected_ids)):
            raise ValueError("Selected ID không được trùng")
        if any(not isinstance(item, DroppedCandidate) for item in dropped):
            raise ValueError("Dropped phải gồm DroppedCandidate")
        if not isinstance(self.candidate_count, int) or self.candidate_count < 0:
            raise ValueError("Candidate count không được âm")
        if not isinstance(self.selected_count, int) or not 0 <= self.selected_count <= self.candidate_count:
            raise ValueError("Selected count không hợp lệ")
        if not _is_finite_nonneg(self.total_reward):
            raise ValueError("Total reward phải là số hữu hạn không âm")
        object.__setattr__(self, "selected_ids", selected_ids)
        object.__setattr__(self, "dropped", dropped)
        object.__setattr__(self, "total_reward", float(self.total_reward))
        object.__setattr__(self, "warnings", tuple(self.warnings))


@dataclass(frozen=True)
class _BeamState:
    selected_ids: frozenset[str]
    remaining_ids: tuple[str, ...]
    reward_upper_bound: float
    signature: tuple[object, ...]
    schedule: ScheduleResult


def _dominates(left: SelectionCandidate, right: SelectionCandidate) -> bool:
    if left.entity_type != right.entity_type or left.area != right.area:
        return False
    if left.reward < right.reward or left.stop.visit_minutes > right.stop.visit_minutes:
        return False
    if left.fee_value is not None and right.fee_value is not None:
        if left.fee_value > right.fee_value:
            return False
        fee_strict = left.fee_value < right.fee_value
    else:
        fee_strict = False
    return (
        left.reward > right.reward
        or left.stop.visit_minutes < right.stop.visit_minutes
        or fee_strict
    )


def _validate_prune_inputs(
    candidates: Sequence[SelectionCandidate],
    required_ids: frozenset[str],
    max_candidates: int,
) -> tuple[list[SelectionCandidate], frozenset[str]]:
    """Kiểm đầu vào của prune và trả (items, required_ids đã chuẩn hoá).

    Giữ NGUYÊN thứ tự kiểm của bản gốc: `max_candidates` được xét TRƯỚC khi
    `list(candidates)` chạy, nên một Sequence lỗi vẫn báo lỗi cap trước — đổi
    thứ tự sẽ đổi thông điệp lỗi mà người gọi nhận được.
    """
    if not isinstance(required_ids, frozenset):
        required_ids = frozenset(required_ids)
    if not 1 <= max_candidates <= 20:
        raise ValueError("Candidate cap phải nằm trong khoảng 1-20")

    items = list(candidates)
    ids = [item.stop.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate ID không được trùng")
    if required_ids.difference(ids):
        raise ValueError("Required ID phải có trong candidate pool")
    if len(required_ids) > max_candidates:
        raise ValueError("Required candidate count cannot exceed candidate cap")
    return items, required_ids


def prune_candidates(
    candidates: Sequence[SelectionCandidate],
    required_ids: frozenset[str],
    max_candidates: int = 20,
) -> tuple[list[SelectionCandidate], tuple[DroppedCandidate, ...]]:
    """Drop dominated candidates and cap the deterministic solver pool."""
    items, required_ids = _validate_prune_inputs(candidates, required_ids, max_candidates)

    dropped: list[DroppedCandidate] = []
    survivors: list[SelectionCandidate] = []
    for item in items:
        if item.stop.id in required_ids:
            survivors.append(item)
            continue
        if any(
            _dominates(other, item)
            for other in items
            if other.stop.id != item.stop.id
            and other.stop.id not in required_ids
        ):
            dropped.append(DroppedCandidate(item.stop.id, "dominated"))
            continue
        survivors.append(item)

    survivors.sort(
        key=lambda item: (
            item.stop.id not in required_ids,
            -item.reward,
            item.stop.visit_minutes,
            item.stop.id,
        )
    )
    kept = survivors[:max_candidates]
    kept_ids = {item.stop.id for item in kept}
    dropped.extend(
        DroppedCandidate(item.stop.id, "candidate-cap")
        for item in survivors[max_candidates:]
        if item.stop.id not in kept_ids
    )
    dropped.sort(key=lambda item: item.stop_id)
    return kept, tuple(dropped)


@dataclass
class _SelectionSearch:
    """Trạng thái chung của một lượt tìm kiếm selection.

    Thay cho bộ closure cũ (build_subset_view/evaluate/objective là anh-em đọc
    chung 7 free-var): các helper module-level nhận MỘT tham số `search` — vẫn
    không có chữ-ký-8-tham-số trong vòng lặp nóng như comment cũ cảnh báo.
    `remaining` của _build_subset_view PHẢI là tham số — đọc lại đồng hồ ở đó
    sẽ cho deadline_seconds nhỏ hơn, tức đổi hành vi.
    """

    items: list
    required_ids: frozenset
    required: list
    fixed: tuple
    optional_order: tuple
    optional_by_id: dict
    matrix: TravelMatrix
    matrix_indexes: dict
    schedule_options: ScheduleOptions
    deadline: float
    base_visit_minutes: float
    available_minutes: float
    cache: dict = field(default_factory=dict)
    feasible_with: set = field(default_factory=set)
    visit_bound_infeasible: set = field(default_factory=set)


def _build_subset_view(
    search: _SelectionSearch, optional_ids: frozenset[str], remaining: float
) -> tuple[list[ScheduleStop], TravelMatrix, ScheduleOptions]:
    """Dựng chuỗi stop + ma trận con + option cục bộ cho một tập optional."""
    selected_optional = [
        item for item in search.optional_order if item.stop.id in optional_ids
    ]
    middle_required = [
        replace(item.stop, required=True) for item in search.required[1:-1]
    ]
    stops = [
        replace(search.required[0].stop, required=True),
        *middle_required,
        *(replace(item.stop, required=True) for item in selected_optional),
        *(replace(stop, required=True) for stop in search.fixed),
        replace(search.required[-1].stop, required=True),
    ]
    stop_ids = tuple(stop.id for stop in stops)
    stop_id_set = set(stop_ids)
    indexes = [search.matrix_indexes[stop_id] for stop_id in stop_ids]
    view = TravelMatrix(
        stop_ids,
        tuple(
            tuple(search.matrix.duration_minutes[row][column] for column in indexes)
            for row in indexes
        ),
        search.matrix.source,
    )
    local_options = replace(
        search.schedule_options,
        deadline_seconds=min(search.schedule_options.deadline_seconds, remaining),
        blocked_edges=frozenset(
            edge
            for edge in search.schedule_options.blocked_edges
            if edge[0] in stop_id_set and edge[1] in stop_id_set
        ),
    )
    return stops, view, local_options


def _evaluate_subset(
    search: _SelectionSearch, optional_ids: frozenset[str]
) -> tuple[ScheduleResult | None, bool]:
    key = frozenset(item.stop.id for item in search.required).union(optional_ids)
    cached = search.cache.get(key)
    if cached is not None:
        return cached
    if search.base_visit_minutes + sum(
        search.optional_by_id[stop_id].stop.visit_minutes for stop_id in optional_ids
    ) > search.available_minutes:
        search.visit_bound_infeasible.add(optional_ids)
        outcome = (None, False)
        search.cache[key] = outcome
        return outcome
    remaining = search.deadline - time.perf_counter()
    if remaining <= 0:
        outcome = (None, True)
        search.cache[key] = outcome
        return outcome

    stops, view, local_options = _build_subset_view(search, optional_ids, remaining)
    try:
        schedule = schedule_stop_order(stops, view, local_options)
    except NoFeasibleScheduleError:
        outcome = (None, False)
    else:
        timed_out = time.perf_counter() >= search.deadline
        outcome = (schedule, timed_out)
        search.feasible_with.update(optional_ids)
    search.cache[key] = outcome
    return outcome


def _selection_objective(
    search: _SelectionSearch,
    schedule: ScheduleResult,
    selected_optional_ids: frozenset[str],
) -> tuple[object, ...]:
    selected_ids = tuple(
        item.stop.id
        for item in search.items
        if item.stop.id in search.required_ids or item.stop.id in selected_optional_ids
    )
    selected_items = [
        item
        for item in search.items
        if item.stop.id in search.required_ids or item.stop.id in selected_optional_ids
    ]
    return (
        -len(selected_ids),
        -sum(item.reward for item in selected_items),
        -len({item.entity_type for item in selected_items}),
        schedule.total_travel_minutes,
        schedule.backtrack_ratio,
        -schedule.minimum_slack_minutes,
        selected_ids,
        schedule.ordered_ids,
    )


def _validate_selection_pool(
    items: list[SelectionCandidate],
    required_ids: frozenset[str],
    fixed_stops: Sequence[ScheduleStop],
) -> tuple[list[str], tuple[ScheduleStop, ...], tuple[str, ...]]:
    if any(not isinstance(item, SelectionCandidate) for item in items):
        raise ValueError("Candidate pool phải gồm SelectionCandidate")
    candidate_ids = [item.stop.id for item in items]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Candidate ID không được trùng")
    unknown_required = required_ids.difference(candidate_ids)
    if unknown_required:
        raise ValueError("Required ID phải có trong candidate pool")
    if any(not isinstance(stop, ScheduleStop) for stop in fixed_stops):
        raise ValueError("Fixed stop phải gồm ScheduleStop")
    fixed = tuple(fixed_stops)
    fixed_ids = tuple(stop.id for stop in fixed)
    if len(fixed_ids) != len(set(fixed_ids)):
        raise ValueError("Fixed stop ID không được trùng")
    if set(fixed_ids).intersection(candidate_ids):
        raise ValueError("Fixed stop ID không được trùng candidate ID")
    return candidate_ids, fixed, fixed_ids


def _validate_schedule_ids(
    kept: list[SelectionCandidate],
    fixed_ids: tuple[str, ...],
    matrix: TravelMatrix,
) -> dict[str, int]:
    all_stop_ids = [item.stop.id for item in kept] + list(fixed_ids)
    if len(all_stop_ids) != len(set(all_stop_ids)):
        raise ValueError("Stop ID trong lịch trình không được trùng")
    matrix_indexes = {stop_id: index for index, stop_id in enumerate(matrix.stop_ids)}
    missing_matrix_ids = set(all_stop_ids).difference(matrix_indexes)
    if missing_matrix_ids:
        raise ValueError("Ma trận thiếu ID điểm dừng")
    return matrix_indexes


def _exact_can_stop(
    incumbent: tuple[ScheduleResult, frozenset[str]] | None,
    required_count: int,
    count: int,
) -> bool:
    # Biểu thức `required_count + ...` hai vế là CỐ Ý (mìn pin sẵn) — không rút gọn.
    return (
        incumbent is not None
        and required_count + len(incumbent[1]) > required_count + count
    )


def _exact_subset_dominated(
    search: _SelectionSearch,
    incumbent: tuple[ScheduleResult, frozenset[str]] | None,
    count: int,
    required_count: int,
    required_reward: float,
    subset_reward: float,
) -> bool:
    # Hai biểu thức `required_count + ...` hai vế là CỐ Ý (mìn pin sẵn) — không rút gọn.
    return (
        incumbent is not None
        and required_count + len(incumbent[1])
        == required_count + count
        and required_reward
        + sum(
            search.optional_by_id[stop_id].reward
            for stop_id in incumbent[1]
        )
        > subset_reward
    )


def _better_incumbent(
    search: _SelectionSearch,
    incumbent: tuple[ScheduleResult, frozenset[str]] | None,
    schedule: ScheduleResult,
    subset_ids: frozenset[str],
) -> tuple[ScheduleResult, frozenset[str]]:
    if incumbent is None or _selection_objective(
        search, schedule, subset_ids
    ) < _selection_objective(search, incumbent[0], incumbent[1]):
        return (schedule, subset_ids)
    return incumbent


def _exact_search(
    search: _SelectionSearch,
    incumbent: tuple[ScheduleResult, frozenset[str]] | None,
    deadline_reached: bool,
    optional_limit: int,
    required_count: int,
    required_reward: float,
) -> tuple[tuple[ScheduleResult, frozenset[str]] | None, bool]:
    for count in range(optional_limit, 0, -1):
        if deadline_reached:
            break
        if _exact_can_stop(incumbent, required_count, count):
            break
        for subset in combinations(search.optional_order, count):
            if time.perf_counter() >= search.deadline:
                deadline_reached = True
                break
            subset_ids = frozenset(item.stop.id for item in subset)
            subset_reward = required_reward + sum(item.reward for item in subset)
            if _exact_subset_dominated(
                search, incumbent, count, required_count, required_reward, subset_reward
            ):
                continue
            schedule, timed_out = _evaluate_subset(search, subset_ids)
            deadline_reached = deadline_reached or timed_out
            if schedule is None:
                continue
            incumbent = _better_incumbent(search, incumbent, schedule, subset_ids)
            if deadline_reached:
                break
    return incumbent, deadline_reached


def _make_beam_state(
    search: _SelectionSearch,
    schedule: ScheduleResult,
    selected_ids: frozenset[str],
    optional_limit: int,
    required_reward: float,
) -> _BeamState:
    remaining_ids = tuple(
        item.stop.id
        for item in search.optional_order
        if item.stop.id not in selected_ids
    )
    remaining_slots = max(0, optional_limit - len(selected_ids))
    reward_upper_bound = (
        required_reward
        + sum(search.optional_by_id[stop_id].reward for stop_id in selected_ids)
        + sum(
            search.optional_by_id[stop_id].reward
            for stop_id in remaining_ids[:remaining_slots]
        )
    )
    return _BeamState(
        selected_ids=selected_ids,
        remaining_ids=remaining_ids,
        reward_upper_bound=reward_upper_bound,
        signature=_selection_objective(search, schedule, selected_ids),
        schedule=schedule,
    )


def _beam_search(
    search: _SelectionSearch,
    incumbent: tuple[ScheduleResult, frozenset[str]] | None,
    deadline_reached: bool,
    base_schedule: ScheduleResult | None,
    optional_limit: int,
    required_reward: float,
    beam_width: int,
) -> tuple[tuple[ScheduleResult, frozenset[str]] | None, bool]:
    frontier = (
        [_make_beam_state(search, base_schedule, frozenset(), optional_limit, required_reward)]
        if base_schedule is not None
        else []
    )
    for _depth in range(1, optional_limit + 1):
        if deadline_reached or not frontier:
            break
        expanded, deadline_reached = _expand_frontier(
            search, frontier, optional_limit, required_reward, deadline_reached
        )
        if not expanded:
            break
        frontier = sorted(
            expanded.values(),
            key=lambda state: (
                state.signature,
                -state.reward_upper_bound,
                tuple(sorted(state.selected_ids)),
            ),
        )[:beam_width]
        for state in frontier:
            if incumbent is None or state.signature < _selection_objective(
                search, incumbent[0], incumbent[1]
            ):
                incumbent = (state.schedule, state.selected_ids)
    return incumbent, deadline_reached


def _expand_frontier(
    search: _SelectionSearch,
    frontier: list[_BeamState],
    optional_limit: int,
    required_reward: float,
    deadline_reached: bool,
) -> tuple[dict[frozenset[str], _BeamState], bool]:
    expanded: dict[frozenset[str], _BeamState] = {}
    for state in frontier:
        for stop_id in state.remaining_ids:
            if time.perf_counter() >= search.deadline:
                deadline_reached = True
                break
            subset_ids = state.selected_ids.union({stop_id})
            schedule, timed_out = _evaluate_subset(search, subset_ids)
            deadline_reached = deadline_reached or timed_out
            if schedule is not None:
                expanded.setdefault(
                    subset_ids,
                    _make_beam_state(search, schedule, subset_ids, optional_limit, required_reward),
                )
            if deadline_reached:
                break
        if deadline_reached:
            break
    return expanded, deadline_reached


def _repair_neighborhoods(
    search: _SelectionSearch,
    current_ids: frozenset[str],
    optional_limit: int,
) -> tuple[set[frozenset[str]], tuple[str, ...]]:
    dropped_ids = tuple(
        item.stop.id
        for item in search.optional_order
        if item.stop.id not in current_ids
    )
    selected_by_efficiency = tuple(
        sorted(
            current_ids,
            key=lambda stop_id: (
                search.optional_by_id[stop_id].reward
                / max(1, search.optional_by_id[stop_id].stop.visit_minutes),
                search.optional_by_id[stop_id].reward,
                stop_id,
            ),
        )
    )
    neighborhoods: set[frozenset[str]] = set()
    if len(current_ids) < optional_limit:
        neighborhoods.update(
            current_ids.union({stop_id}) for stop_id in dropped_ids
        )
    neighborhoods.update(
        current_ids.difference({selected_id}).union({dropped_id})
        for selected_id in selected_by_efficiency
        for dropped_id in dropped_ids
    )
    for removed_id in selected_by_efficiency:
        rebuilt = set(current_ids.difference({removed_id}))
        for dropped_id in dropped_ids:
            if len(rebuilt) >= optional_limit:
                break
            rebuilt.add(dropped_id)
        if rebuilt != set(current_ids):
            neighborhoods.add(frozenset(rebuilt))
    return neighborhoods, selected_by_efficiency


def _repair_incumbent(
    search: _SelectionSearch,
    incumbent: tuple[ScheduleResult, frozenset[str]] | None,
    deadline_reached: bool,
    optional_limit: int,
    repair_iterations: int,
) -> tuple[tuple[ScheduleResult, frozenset[str]] | None, bool]:
    repair_deadline_reached = False
    if incumbent is None or repair_iterations <= 0 or deadline_reached:
        return incumbent, repair_deadline_reached
    optional_rank = {
        item.stop.id: index for index, item in enumerate(search.optional_order)
    }
    for _iteration in range(repair_iterations):
        if time.perf_counter() >= search.deadline:
            repair_deadline_reached = True
            break
        current_schedule, current_ids = incumbent
        neighborhoods, _ = _repair_neighborhoods(search, current_ids, optional_limit)

        best, hit_deadline = _best_repair_neighbor(
            search, incumbent, neighborhoods, optional_rank
        )
        repair_deadline_reached = repair_deadline_reached or hit_deadline
        if _selection_objective(search, best[0], best[1]) < _selection_objective(
            search, current_schedule, current_ids
        ):
            incumbent = best
        else:
            break
        if repair_deadline_reached:
            break
    return incumbent, repair_deadline_reached


def _best_repair_neighbor(
    search: _SelectionSearch,
    incumbent: tuple[ScheduleResult, frozenset[str]],
    neighborhoods: set[frozenset[str]],
    optional_rank: dict[str, int],
) -> tuple[tuple[ScheduleResult, frozenset[str]], bool]:
    best = incumbent
    for neighbor_ids in sorted(
        neighborhoods,
        key=lambda ids: tuple(sorted(ids, key=optional_rank.__getitem__)),
    ):
        schedule, timed_out = _evaluate_subset(search, neighbor_ids)
        if schedule is not None and _selection_objective(
            search, schedule, neighbor_ids
        ) < _selection_objective(search, best[0], best[1]):
            best = (schedule, neighbor_ids)
        if timed_out:
            return best, True
    return best, False


def select_and_schedule_day(
    candidates: Sequence[SelectionCandidate],
    required_ids: frozenset[str],
    fixed_stops: Sequence[ScheduleStop],
    matrix: TravelMatrix,
    schedule_options: ScheduleOptions,
    selection_options: SelectionOptions,
) -> SelectionResult:
    """Select a feasible exact subset when the post-prune pool is small."""
    if not isinstance(required_ids, frozenset):
        required_ids = frozenset(required_ids)

    items = list(candidates)
    candidate_ids, fixed, fixed_ids = _validate_selection_pool(
        items, required_ids, fixed_stops
    )

    kept, pruned_dropped = prune_candidates(items, required_ids)
    required, optional_order, solver, required_count, optional_limit = (
        _prepare_selection(items, kept, required_ids, selection_options)
    )
    matrix_indexes = _validate_schedule_ids(kept, fixed_ids, matrix)
    search = _SelectionSearch(
        items=items,
        required_ids=required_ids,
        required=required,
        fixed=fixed,
        optional_order=optional_order,
        optional_by_id={item.stop.id: item for item in optional_order},
        matrix=matrix,
        matrix_indexes=matrix_indexes,
        schedule_options=schedule_options,
        deadline=time.perf_counter() + selection_options.deadline_seconds,
        base_visit_minutes=sum(item.stop.visit_minutes for item in required)
        + sum(stop.visit_minutes for stop in fixed),
        available_minutes=(
            schedule_options.day_end_minute - schedule_options.day_start_minute
        ),
    )

    incumbent: tuple[ScheduleResult, frozenset[str]] | None = None
    deadline_reached = False
    base_schedule, base_timed_out = _evaluate_subset(search, frozenset())
    if base_schedule is not None:
        incumbent = (base_schedule, frozenset())
    deadline_reached = deadline_reached or base_timed_out

    required_reward = sum(item.reward for item in required)
    if solver == "selection-exact":
        incumbent, deadline_reached = _exact_search(
            search, incumbent, deadline_reached,
            optional_limit, required_count, required_reward,
        )
    else:
        incumbent, deadline_reached = _beam_search(
            search, incumbent, deadline_reached, base_schedule,
            optional_limit, required_reward, selection_options.beam_width,
        )

    incumbent, repair_deadline_reached = _repair_incumbent(
        search, incumbent, deadline_reached,
        optional_limit, selection_options.repair_iterations,
    )

    if incumbent is None:
        raise NoFeasibleScheduleError("Không tìm thấy lịch trình khả thi cho selection")

    return _selection_result(
        search, incumbent, kept, pruned_dropped, solver,
        deadline_reached, repair_deadline_reached,
    )


def _prepare_selection(
    items: list[SelectionCandidate],
    kept: list[SelectionCandidate],
    required_ids: frozenset[str],
    selection_options: SelectionOptions,
) -> tuple[list, tuple, str, int, int]:
    required = [item for item in items if item.stop.id in required_ids]
    optional = [item for item in kept if item.stop.id not in required_ids]
    solver = (
        "selection-exact"
        if len(optional) <= selection_options.exact_limit
        else "selection-beam"
    )
    if len(required) < 2:
        raise ValueError("Required candidate pool phải có ít nhất hai endpoint")
    required_count = len(required)
    optional_limit = min(
        len(optional),
        max(0, selection_options.target_count - required_count),
    )
    optional_order = tuple(
        sorted(
            optional,
            key=lambda item: (-item.reward, item.stop.visit_minutes, item.stop.id),
        )
    )
    return required, optional_order, solver, required_count, optional_limit


def _selection_result(
    search: _SelectionSearch,
    incumbent: tuple[ScheduleResult, frozenset[str]],
    kept: list[SelectionCandidate],
    pruned_dropped: Sequence[DroppedCandidate],
    solver: str,
    deadline_reached: bool,
    repair_deadline_reached: bool,
) -> SelectionResult:
    schedule, selected_optional_ids = incumbent
    selected_ids = tuple(
        item.stop.id
        for item in search.items
        if item.stop.id in search.required_ids or item.stop.id in selected_optional_ids
    )
    selected_set = set(selected_ids)
    dropped, deadline_reached = _dropped_diagnostics(
        search, kept, list(pruned_dropped), selected_set,
        deadline_reached, repair_deadline_reached,
    )
    warnings = list(schedule.warnings)
    if deadline_reached and "selection-deadline-reached" not in warnings:
        warnings.append("selection-deadline-reached")
    if (
        repair_deadline_reached
        and "selection-repair-deadline-reached" not in warnings
    ):
        warnings.append("selection-repair-deadline-reached")
    selected_items = [item for item in search.items if item.stop.id in selected_set]
    return SelectionResult(
        schedule=schedule,
        selected_ids=selected_ids,
        dropped=tuple(dropped),
        candidate_count=len(search.items),
        selected_count=len(selected_ids),
        total_reward=sum(item.reward for item in selected_items),
        solver=solver,
        warnings=tuple(warnings),
    )


def _singleton_drop_reason(
    search: _SelectionSearch, stop_id: str
) -> tuple[str, bool]:
    """Lý do loại một điểm chưa từng khả thi; phần tử thứ hai = chạm deadline."""
    singleton = frozenset({stop_id})
    diagnostic, diagnostic_timed_out = _evaluate_subset(search, singleton)
    if diagnostic is not None:
        return "lower-reward-alternative", False
    if diagnostic_timed_out:
        return "selection-deadline", True
    if singleton in search.visit_bound_infeasible:
        return "time-window-overflow", False
    if any(
        stop_id in edge
        for edge in search.schedule_options.blocked_edges
    ):
        return "unreachable-edge", False
    return "time-window-overflow", False


def _dropped_diagnostics(
    search: _SelectionSearch,
    kept: list[SelectionCandidate],
    dropped: list[DroppedCandidate],
    selected_set: set[str],
    deadline_reached: bool,
    repair_deadline_reached: bool,
) -> tuple[list[DroppedCandidate], bool]:
    for item in kept:
        stop_id = item.stop.id
        if stop_id in selected_set or stop_id in search.required_ids:
            continue
        if (
            deadline_reached or repair_deadline_reached
        ) and stop_id not in search.feasible_with:
            reason = "selection-deadline"
        elif stop_id in search.feasible_with:
            reason = "lower-reward-alternative"
        else:
            reason, hit_deadline = _singleton_drop_reason(search, stop_id)
            deadline_reached = deadline_reached or hit_deadline
        dropped.append(DroppedCandidate(stop_id, reason))
    dropped.sort(key=lambda item: item.stop_id)
    return dropped, deadline_reached


__all__ = [
    "DroppedCandidate",
    "SelectionCandidate",
    "SelectionOptions",
    "SelectionResult",
    "prune_candidates",
    "select_and_schedule_day",
]
