"""Dependency-free candidate pruning and selection contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from itinerary_schedule import (
    ScheduleOptions,
    ScheduleResult,
    ScheduleStop,
    TravelMatrix,
    schedule_stop_order,
)


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
        if (
            isinstance(self.reward, bool)
            or not isinstance(self.reward, (int, float))
            or not math.isfinite(self.reward)
            or self.reward < 0
        ):
            raise ValueError("Reward phải là số hữu hạn không âm")
        if not isinstance(self.entity_type, str) or not self.entity_type.strip():
            raise ValueError("Loại entity không được để trống")
        if not isinstance(self.area, str) or not self.area.strip():
            raise ValueError("Khu vực không được để trống")
        if self.fee_value is not None and (
            isinstance(self.fee_value, bool)
            or not isinstance(self.fee_value, (int, float))
            or not math.isfinite(self.fee_value)
            or self.fee_value < 0
        ):
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
        if not isinstance(self.target_count, int) or isinstance(self.target_count, bool) or self.target_count < 1:
            raise ValueError("Số POI mục tiêu phải lớn hơn 0")
        if not isinstance(self.exact_limit, int) or isinstance(self.exact_limit, bool) or self.exact_limit < 0:
            raise ValueError("Ngưỡng giải chính xác không được âm")
        if not isinstance(self.beam_width, int) or isinstance(self.beam_width, bool) or self.beam_width < 1:
            raise ValueError("Độ rộng beam search phải lớn hơn 0")
        if not isinstance(self.repair_iterations, int) or isinstance(self.repair_iterations, bool) or self.repair_iterations < 0:
            raise ValueError("Số iteration repair không được âm")
        if (
            isinstance(self.deadline_seconds, bool)
            or not isinstance(self.deadline_seconds, (int, float))
            or not math.isfinite(self.deadline_seconds)
            or self.deadline_seconds <= 0
        ):
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
        if (
            isinstance(self.total_reward, bool)
            or not isinstance(self.total_reward, (int, float))
            or not math.isfinite(self.total_reward)
            or self.total_reward < 0
        ):
            raise ValueError("Total reward phải là số hữu hạn không âm")
        object.__setattr__(self, "selected_ids", selected_ids)
        object.__setattr__(self, "dropped", dropped)
        object.__setattr__(self, "total_reward", float(self.total_reward))
        object.__setattr__(self, "warnings", tuple(self.warnings))


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


def prune_candidates(
    candidates: Sequence[SelectionCandidate],
    required_ids: frozenset[str],
    max_candidates: int = 20,
) -> tuple[list[SelectionCandidate], tuple[DroppedCandidate, ...]]:
    """Drop dominated candidates and cap the deterministic solver pool."""
    if not isinstance(required_ids, frozenset):
        required_ids = frozenset(required_ids)
    if not 1 <= max_candidates <= 20:
        raise ValueError("Candidate cap phải nằm trong khoảng 1-20")

    items = list(candidates)
    ids = [item.stop.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate ID không được trùng")
    unknown_required = required_ids.difference(ids)
    if unknown_required:
        raise ValueError("Required ID phải có trong candidate pool")
    if len(required_ids) > max_candidates:
        raise ValueError("Required candidate count cannot exceed candidate cap")

    dropped: list[DroppedCandidate] = []
    survivors: list[SelectionCandidate] = []
    for item in items:
        if item.stop.id in required_ids:
            survivors.append(item)
            continue
        if any(_dominates(other, item) for other in items if other.stop.id != item.stop.id):
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
    """Return a safe required-only result until exact search is added in Task 2."""
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

    required = [item for item in items if item.stop.id in required_ids]
    optional = [item for item in items if item.stop.id not in required_ids]
    if optional:
        raise NotImplementedError("Exact selection search is implemented in the next task")
    if len(required) < 2:
        raise ValueError("Required candidate pool phải có ít nhất hai endpoint")

    stops = [required[0].stop, *fixed_stops, required[-1].stop]
    stop_ids = [stop.id for stop in stops]
    if len(stop_ids) != len(set(stop_ids)):
        raise ValueError("Stop ID trong lịch trình không được trùng")
    schedule = schedule_stop_order(stops, matrix, schedule_options)
    selected_ids = tuple(item.stop.id for item in required)
    return SelectionResult(
        schedule=schedule,
        selected_ids=selected_ids,
        dropped=(),
        candidate_count=len(items),
        selected_count=len(selected_ids),
        total_reward=sum(item.reward for item in required),
        solver="selection-exact",
        warnings=(),
    )


__all__ = [
    "DroppedCandidate",
    "SelectionCandidate",
    "SelectionOptions",
    "SelectionResult",
    "prune_candidates",
    "select_and_schedule_day",
]
