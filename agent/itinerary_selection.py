"""Dependency-free candidate pruning and selection contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations
import time
from typing import Sequence

from itinerary_schedule import (
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

    kept, pruned_dropped = prune_candidates(items, required_ids)
    required = [item for item in items if item.stop.id in required_ids]
    optional = [item for item in kept if item.stop.id not in required_ids]
    solver = (
        "selection-exact"
        if len(optional) <= selection_options.exact_limit
        else "selection-beam"
    )
    if len(required) < 2:
        raise ValueError("Required candidate pool phải có ít nhất hai endpoint")

    all_stop_ids = [item.stop.id for item in kept] + list(fixed_ids)
    if len(all_stop_ids) != len(set(all_stop_ids)):
        raise ValueError("Stop ID trong lịch trình không được trùng")
    matrix_indexes = {stop_id: index for index, stop_id in enumerate(matrix.stop_ids)}
    missing_matrix_ids = set(all_stop_ids).difference(matrix_indexes)
    if missing_matrix_ids:
        raise ValueError("Ma trận thiếu ID điểm dừng")

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
    deadline = time.perf_counter() + selection_options.deadline_seconds
    cache: dict[frozenset[str], tuple[ScheduleResult | None, bool]] = {}
    feasible_with: set[str] = set()
    optional_by_id = {item.stop.id: item for item in optional_order}
    base_visit_minutes = sum(item.stop.visit_minutes for item in required) + sum(
        stop.visit_minutes for stop in fixed
    )
    available_minutes = (
        schedule_options.day_end_minute - schedule_options.day_start_minute
    )
    visit_bound_infeasible: set[frozenset[str]] = set()

    def build_subset_view(
        optional_ids: frozenset[str], remaining: float
    ) -> tuple[list[ScheduleStop], TravelMatrix, ScheduleOptions]:
        """Dựng chuỗi stop + ma trận con + option cục bộ cho một tập optional.

        Là closure ANH-EM của `evaluate` chứ không phải hàm module-level: nó đọc
        7 free-var (required, fixed, optional_order, matrix, matrix_indexes,
        schedule_options) mà nâng lên module-level sẽ thành chữ ký 8 tham số
        trong vòng lặp nóng. `remaining` PHẢI là tham số — đọc lại đồng hồ ở đây
        sẽ cho deadline_seconds nhỏ hơn, tức đổi hành vi.
        """
        selected_optional = [
            item for item in optional_order if item.stop.id in optional_ids
        ]
        middle_required = [
            replace(item.stop, required=True) for item in required[1:-1]
        ]
        stops = [
            replace(required[0].stop, required=True),
            *middle_required,
            *(replace(item.stop, required=True) for item in selected_optional),
            *(replace(stop, required=True) for stop in fixed),
            replace(required[-1].stop, required=True),
        ]
        stop_ids = tuple(stop.id for stop in stops)
        stop_id_set = set(stop_ids)
        indexes = [matrix_indexes[stop_id] for stop_id in stop_ids]
        view = TravelMatrix(
            stop_ids,
            tuple(
                tuple(matrix.duration_minutes[row][column] for column in indexes)
                for row in indexes
            ),
            matrix.source,
        )
        local_options = replace(
            schedule_options,
            deadline_seconds=min(schedule_options.deadline_seconds, remaining),
            blocked_edges=frozenset(
                edge
                for edge in schedule_options.blocked_edges
                if edge[0] in stop_id_set and edge[1] in stop_id_set
            ),
        )
        return stops, view, local_options

    def evaluate(optional_ids: frozenset[str]) -> tuple[ScheduleResult | None, bool]:
        key = frozenset(item.stop.id for item in required).union(optional_ids)
        cached = cache.get(key)
        if cached is not None:
            return cached
        if base_visit_minutes + sum(
            optional_by_id[stop_id].stop.visit_minutes for stop_id in optional_ids
        ) > available_minutes:
            visit_bound_infeasible.add(optional_ids)
            outcome = (None, False)
            cache[key] = outcome
            return outcome
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            outcome = (None, True)
            cache[key] = outcome
            return outcome

        stops, view, local_options = build_subset_view(optional_ids, remaining)
        try:
            schedule = schedule_stop_order(stops, view, local_options)
        except NoFeasibleScheduleError:
            outcome = (None, False)
        else:
            timed_out = time.perf_counter() >= deadline
            outcome = (schedule, timed_out)
            feasible_with.update(optional_ids)
        cache[key] = outcome
        return outcome

    def objective(
        schedule: ScheduleResult,
        selected_optional_ids: frozenset[str],
    ) -> tuple[object, ...]:
        selected_ids = tuple(
            item.stop.id
            for item in items
            if item.stop.id in required_ids or item.stop.id in selected_optional_ids
        )
        selected_items = [
            item
            for item in items
            if item.stop.id in required_ids or item.stop.id in selected_optional_ids
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

    incumbent: tuple[ScheduleResult, frozenset[str]] | None = None
    deadline_reached = False
    base_schedule, base_timed_out = evaluate(frozenset())
    if base_schedule is not None:
        incumbent = (base_schedule, frozenset())
    deadline_reached = deadline_reached or base_timed_out

    required_reward = sum(item.reward for item in required)
    if solver == "selection-exact":
        for count in range(optional_limit, 0, -1):
            if deadline_reached:
                break
            if (
                incumbent is not None
                and required_count + len(incumbent[1]) > required_count + count
            ):
                break
            for subset in combinations(optional_order, count):
                if time.perf_counter() >= deadline:
                    deadline_reached = True
                    break
                subset_ids = frozenset(item.stop.id for item in subset)
                subset_reward = required_reward + sum(item.reward for item in subset)
                if (
                    incumbent is not None
                    and required_count + len(incumbent[1])
                    == required_count + count
                    and required_reward
                    + sum(
                        optional_by_id[stop_id].reward
                        for stop_id in incumbent[1]
                    )
                    > subset_reward
                ):
                    continue
                schedule, timed_out = evaluate(subset_ids)
                deadline_reached = deadline_reached or timed_out
                if schedule is None:
                    continue
                if incumbent is None or objective(schedule, subset_ids) < objective(
                    incumbent[0], incumbent[1]
                ):
                    incumbent = (schedule, subset_ids)
                if deadline_reached:
                    break
    else:

        def make_beam_state(
            schedule: ScheduleResult,
            selected_ids: frozenset[str],
        ) -> _BeamState:
            remaining_ids = tuple(
                item.stop.id
                for item in optional_order
                if item.stop.id not in selected_ids
            )
            remaining_slots = max(0, optional_limit - len(selected_ids))
            reward_upper_bound = (
                required_reward
                + sum(optional_by_id[stop_id].reward for stop_id in selected_ids)
                + sum(
                    optional_by_id[stop_id].reward
                    for stop_id in remaining_ids[:remaining_slots]
                )
            )
            return _BeamState(
                selected_ids=selected_ids,
                remaining_ids=remaining_ids,
                reward_upper_bound=reward_upper_bound,
                signature=objective(schedule, selected_ids),
                schedule=schedule,
            )

        frontier = (
            [make_beam_state(base_schedule, frozenset())]
            if base_schedule is not None
            else []
        )
        for _depth in range(1, optional_limit + 1):
            if deadline_reached or not frontier:
                break
            expanded: dict[frozenset[str], _BeamState] = {}
            for state in frontier:
                for stop_id in state.remaining_ids:
                    if time.perf_counter() >= deadline:
                        deadline_reached = True
                        break
                    subset_ids = state.selected_ids.union({stop_id})
                    schedule, timed_out = evaluate(subset_ids)
                    deadline_reached = deadline_reached or timed_out
                    if schedule is not None:
                        expanded.setdefault(
                            subset_ids,
                            make_beam_state(schedule, subset_ids),
                        )
                    if deadline_reached:
                        break
                if deadline_reached:
                    break
            if not expanded:
                break
            frontier = sorted(
                expanded.values(),
                key=lambda state: (
                    state.signature,
                    -state.reward_upper_bound,
                    tuple(sorted(state.selected_ids)),
                ),
            )[: selection_options.beam_width]
            for state in frontier:
                if incumbent is None or state.signature < objective(
                    incumbent[0], incumbent[1]
                ):
                    incumbent = (state.schedule, state.selected_ids)

    repair_deadline_reached = False
    if (
        incumbent is not None
        and selection_options.repair_iterations > 0
        and not deadline_reached
    ):
        optional_rank = {
            item.stop.id: index for index, item in enumerate(optional_order)
        }
        for _iteration in range(selection_options.repair_iterations):
            if time.perf_counter() >= deadline:
                repair_deadline_reached = True
                break
            current_schedule, current_ids = incumbent
            dropped_ids = tuple(
                item.stop.id
                for item in optional_order
                if item.stop.id not in current_ids
            )
            selected_by_efficiency = tuple(
                sorted(
                    current_ids,
                    key=lambda stop_id: (
                        optional_by_id[stop_id].reward
                        / max(1, optional_by_id[stop_id].stop.visit_minutes),
                        optional_by_id[stop_id].reward,
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

            best = incumbent
            for neighbor_ids in sorted(
                neighborhoods,
                key=lambda ids: tuple(sorted(ids, key=optional_rank.__getitem__)),
            ):
                schedule, timed_out = evaluate(neighbor_ids)
                if schedule is not None and objective(
                    schedule, neighbor_ids
                ) < objective(best[0], best[1]):
                    best = (schedule, neighbor_ids)
                if timed_out:
                    repair_deadline_reached = True
                    break
            if objective(best[0], best[1]) < objective(
                current_schedule, current_ids
            ):
                incumbent = best
            else:
                break
            if repair_deadline_reached:
                break

    if incumbent is None:
        raise NoFeasibleScheduleError("Không tìm thấy lịch trình khả thi cho selection")

    schedule, selected_optional_ids = incumbent
    selected_ids = tuple(
        item.stop.id
        for item in items
        if item.stop.id in required_ids or item.stop.id in selected_optional_ids
    )
    selected_set = set(selected_ids)
    dropped = list(pruned_dropped)
    for item in kept:
        stop_id = item.stop.id
        if stop_id in selected_set or stop_id in required_ids:
            continue
        if (
            deadline_reached or repair_deadline_reached
        ) and stop_id not in feasible_with:
            reason = "selection-deadline"
        elif stop_id in feasible_with:
            reason = "lower-reward-alternative"
        else:
            singleton = frozenset({stop_id})
            diagnostic, diagnostic_timed_out = evaluate(singleton)
            if diagnostic is not None:
                reason = "lower-reward-alternative"
            elif diagnostic_timed_out:
                reason = "selection-deadline"
                deadline_reached = True
            elif singleton in visit_bound_infeasible:
                reason = "time-window-overflow"
            elif any(
                stop_id in edge
                for edge in schedule_options.blocked_edges
            ):
                reason = "unreachable-edge"
            else:
                reason = "time-window-overflow"
        dropped.append(DroppedCandidate(stop_id, reason))
    dropped.sort(key=lambda item: item.stop_id)
    warnings = list(schedule.warnings)
    if deadline_reached and "selection-deadline-reached" not in warnings:
        warnings.append("selection-deadline-reached")
    if (
        repair_deadline_reached
        and "selection-repair-deadline-reached" not in warnings
    ):
        warnings.append("selection-repair-deadline-reached")
    selected_items = [item for item in items if item.stop.id in selected_set]
    return SelectionResult(
        schedule=schedule,
        selected_ids=selected_ids,
        dropped=tuple(dropped),
        candidate_count=len(items),
        selected_count=len(selected_ids),
        total_reward=sum(item.reward for item in selected_items),
        solver=solver,
        warnings=tuple(warnings),
    )


__all__ = [
    "DroppedCandidate",
    "SelectionCandidate",
    "SelectionOptions",
    "SelectionResult",
    "prune_candidates",
    "select_and_schedule_day",
]
