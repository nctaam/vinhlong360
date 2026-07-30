# Phase 4 Multi-day Allocation Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reallocate the content POIs already selected by Phase 3 across adjacent itinerary days, choose better internal day endpoints, and reduce maximum day load without changing the public API or adding cost.

**Architecture:** Add a dependency-free `agent/itinerary_multiday.py` module. It evaluates a fixed allocation with local Haversine matrices and the existing `schedule_stop_order(...)`, carries internal endpoints through a bounded label-setting DP, then applies deterministic adjacent-day relocate/swap neighborhoods under one shared deadline. `agent/itinerary_gen.py` remains the owner of raw entity metadata, Phase 3 selection diagnostics, projection, fallback, and the additive `schedule.allocation` envelope.

**Tech Stack:** Python 3.11+, standard library only, existing `agent/itinerary_schedule.py`, existing `agent/itinerary_selection.py`, pytest, Ruff, existing MCP/API contracts.

## Global Constraints

- Keep the existing `generate_itinerary(...)` signature, response keys, MCP wrapper, saved-itinerary schema, public optimizer endpoint, and frontend contract unchanged.
- Add fields only under `day_plans[*].schedule.allocation`; additions must be optional and backward-compatible.
- Run Phase 4 only for `days >= 2` when every day has a safe coordinate-aware Phase 3 result.
- Preserve the exact global set of content POIs selected by Phase 3; do not add, drop, or duplicate content entities.
- Keep the trip-global first content POI and last content POI locked. Internal day endpoints may change.
- Keep meal/rest anchors on their original day and include them in every feasibility evaluation.
- Keep at least two content POIs per eligible day and allow each day count to differ from its Phase 3 baseline by at most one.
- Use only local Haversine matrices; do not call OSRM, web services, paid APIs, or an LLM.
- Add no Python/NPM dependency, API key, container, migration, database table, persistent cache, or background request.
- Use a shared Phase 4 deadline of 1.0 seconds, at most 12 local-search iterations, and at most 8 labels per endpoint.
- Preserve Phase 3 `selection_*` diagnostics as pre-allocation history. Update route timing fields and `area_focus` from the final Phase 4 result.
- A synthetic overnight origin participates in travel/load calculations but must never appear in public stops or emitted ordered IDs.
- If Phase 4 cannot establish or improve a safe incumbent, retain the complete Phase 3 output and report explicit allocation diagnostics.
- Do not deploy, migrate, push, or claim the full repository suite passes.
- Prefer a fresh implementer/reviewer subagent for each task. If the configured provider still returns `404 No active credentials`, continue inline under the already approved fallback and record a scoped self-review before the next task.

---

## Task 1: Contracts and Fixed-allocation Route Evaluation

**Files:**
- Create: `agent/itinerary_multiday.py`
- Create: `agent/tests/test_itinerary_multiday.py`

**Interfaces:**
- Consumes: `SelectionCandidate` from `agent/itinerary_selection.py`; `NoFeasibleScheduleError`, `ScheduleOptions`, `ScheduleResult`, `ScheduleStop`, `build_fallback_matrix`, and `schedule_stop_order` from `agent/itinerary_schedule.py`.
- Produces: immutable `MultiDayDayInput`, `MultiDayOptions`, `MultiDayDayResult`, `MultiDayResult`; public `optimize_multi_day_allocation(...)`; a baseline evaluator that keeps Phase 3 ownership and fixed baseline endpoints while adding synthetic origins from day two onward.

- [ ] **Step 1: Write the failing contract and baseline-route tests.**

Create `agent/tests/test_itinerary_multiday.py` with these helpers and tests:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from itinerary_multiday import (
    MultiDayDayInput,
    MultiDayOptions,
    optimize_multi_day_allocation,
)
from itinerary_schedule import ScheduleOptions, ScheduleStop
from itinerary_selection import SelectionCandidate


def candidate(
    stop_id: str,
    latitude: float,
    longitude: float = 106.0,
    visit: int = 30,
    reward: float = 1.0,
    entity_type: str | None = None,
    area: str = "vinh-long",
) -> SelectionCandidate:
    return SelectionCandidate(
        stop=ScheduleStop(stop_id, (latitude, longitude), visit),
        reward=reward,
        entity_type=entity_type or stop_id,
        area=area,
    )


def day_input(
    day_index: int,
    candidates: list[SelectionCandidate],
    fixed_stops: tuple[ScheduleStop, ...] = (),
) -> MultiDayDayInput:
    return MultiDayDayInput(
        day_index=day_index,
        candidates=tuple(candidates),
        fixed_stops=fixed_stops,
        baseline_order=tuple(item.stop.id for item in candidates),
        schedule_options=ScheduleOptions(
            day_start_minute=480,
            day_end_minute=1080,
        ),
    )


def simple_two_day_inputs() -> tuple[MultiDayDayInput, MultiDayDayInput]:
    return (
        day_input(
            1,
            [
                candidate("start", 10.00, visit=0),
                candidate("day-1-end", 10.10),
            ],
        ),
        day_input(
            2,
            [
                candidate("day-2-first", 10.20),
                candidate("end", 10.30, visit=0),
            ],
        ),
    )


def test_multiday_options_reject_invalid_bounds():
    with pytest.raises(ValueError):
        MultiDayOptions(min_content_per_day=1)
    with pytest.raises(ValueError):
        MultiDayOptions(max_count_delta=-1)
    with pytest.raises(ValueError):
        MultiDayOptions(deadline_seconds=0)
    with pytest.raises(ValueError):
        MultiDayOptions(max_labels_per_endpoint=0)


def test_optimizer_rejects_duplicate_content_ids_across_days():
    first, second = simple_two_day_inputs()
    duplicate = day_input(
        2,
        [candidate("day-1-end", 10.20), candidate("end", 10.30, visit=0)],
    )

    with pytest.raises(ValueError, match="duplicate"):
        optimize_multi_day_allocation(
            (first, duplicate),
            global_start_id="start",
            global_end_id="end",
            options=MultiDayOptions(max_iterations=0),
        )


def test_optimizer_rejects_unknown_global_anchor():
    days = simple_two_day_inputs()

    with pytest.raises(ValueError, match="global"):
        optimize_multi_day_allocation(
            days,
            global_start_id="missing",
            global_end_id="end",
            options=MultiDayOptions(max_iterations=0),
        )


def test_fixed_allocation_adds_internal_origin_without_emitting_it():
    days = simple_two_day_inputs()
    result = optimize_multi_day_allocation(
        days,
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=0),
    )

    second = result.days[1]
    assert result.move_count == 0
    assert second.synthetic_origin_id is not None
    assert second.synthetic_origin_id in second.schedule.ordered_ids
    assert second.synthetic_origin_id not in second.ordered_ids
    assert set(second.content_ids) == {"day-2-first", "end"}
    assert second.load_minutes > 30.0
    assert "overnight-origin-approximated" in result.warnings
```

- [ ] **Step 2: Run the tests and verify the intended RED failure.**

Run:

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py -q
```

Expected: collection fails because `agent/itinerary_multiday.py` and its public contracts do not exist.

- [ ] **Step 3: Implement the contracts, validation, and baseline route evaluator.**

Implement the four dataclasses exactly as specified in `docs/superpowers/specs/2026-07-30-phase4-multiday-allocation-design.md`. Validation must include:

1. Positive sequential `day_index` values starting at 1.
2. At least two candidates per day.
3. Candidate IDs and fixed-stop IDs unique within a day and globally.
4. `baseline_order` contains every candidate ID exactly once and no fixed IDs.
5. Global start belongs to day 1; global end belongs to the last day; both IDs exist and differ.
6. `min_content_per_day >= 2`, `max_count_delta >= 0`, `max_iterations >= 0`, `deadline_seconds > 0`, and `max_labels_per_endpoint >= 1`.

Cross-day validation errors used by the tests must include `duplicate` for repeated IDs and `global` for missing/misplaced trip anchors.

Use these internal signatures:

```python
Allocation = tuple[tuple[str, ...], ...]


def _validate_inputs(
    days: tuple[MultiDayDayInput, ...],
    global_start_id: str,
    global_end_id: str,
    options: MultiDayOptions,
) -> dict[str, SelectionCandidate]:
    """Return the unique global candidate map after validating the problem."""


def _schedule_day(
    day: MultiDayDayInput,
    content_ids: tuple[str, ...],
    candidate_by_id: dict[str, SelectionCandidate],
    first_content_id: str | None,
    previous_end_id: str | None,
    current_end_id: str,
    remaining_seconds: float,
) -> MultiDayDayResult:
    """Schedule one fully required day with a fixed first/origin and end."""
```

For day 1, `first_content_id` is `global_start_id` and no synthetic origin is created. For later days, create the origin with this shape:

```python
origin_id = f"__multiday_origin_{day.day_index}_{previous_end_id}"
origin = ScheduleStop(
    id=origin_id,
    coordinates=candidate_by_id[previous_end_id].stop.coordinates,
    visit_minutes=0,
    required=True,
)
```

Before constructing the stop, make the ID collision-safe: if the base ID exists in any content or fixed-stop ID, append `_1`, `_2`, and so on until the first unused deterministic ID is found.

Build the scheduler sequence as first/origin, all remaining content and fixed stops, then `current_end_id`. Convert every content and fixed stop with `dataclasses.replace(stop, required=True)`. Use `build_fallback_matrix(stops, "driving")` and a copied `ScheduleOptions` whose `deadline_seconds` is `min(day.schedule_options.deadline_seconds, remaining_seconds)`.

Reject a result when it skips any stop, has overtime, omits an input ID, or fails to preserve the constructed first and last IDs. Compute:

```python
load_minutes = max(
    placement.finish_visit_minute for placement in schedule.placements
) - day.schedule_options.day_start_minute
```

Return `ordered_ids` after filtering only the synthetic origin. Fixed anchor IDs remain in the ordered IDs.

In the first implementation of `optimize_multi_day_allocation(...)`, evaluate the baseline allocation with the last baseline content ID as every day's endpoint. Return `initial_load_minutes == final_load_minutes`, empty moved lists, `move_count=0`, solver `multiday-dp-local-search`, and warning `overnight-origin-approximated`. Leave endpoint optimization and neighborhoods for later tasks.

- [ ] **Step 4: Run contract, scheduler, and Phase 3 selection regressions.**

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_schedule.py -q
python -m ruff check agent/itinerary_multiday.py agent/tests/test_itinerary_multiday.py
```

Expected: all tests pass; no network/dependency changes appear.

- [ ] **Step 5: Commit the contracts and baseline evaluator.**

```powershell
git add agent/itinerary_multiday.py agent/tests/test_itinerary_multiday.py
git commit -m "feat: add multiday allocation contracts"
```

- [ ] **Step 6: Run a Task 1 scoped spec/quality review.**

Review the Task 1 commit against the contracts, synthetic-origin isolation, fixed endpoint order, shared-deadline propagation, and validation messages. Fix every Critical or Important finding and rerun the Task 1 matrix before starting Task 2.

## Task 2: Endpoint Label-setting DP and Feasibility Cache

**Files:**
- Modify: `agent/itinerary_multiday.py`
- Modify: `agent/tests/test_itinerary_multiday.py`

**Interfaces:**
- Consumes: Task 1 contracts and `_schedule_day(...)`.
- Produces: `_solve_allocation(...)` with bounded labels per endpoint, shared deadline, feasibility cache, dynamic internal endpoints, and a complete baseline result for the unchanged Phase 3 ownership allocation.

- [ ] **Step 1: Add failing endpoint-DP and fixed-anchor tests.**

Append:

```python
from itinerary_schedule import TimeWindow


def endpoint_choice_inputs() -> tuple[MultiDayDayInput, MultiDayDayInput]:
    return (
        day_input(
            1,
            [
                candidate("start", 10.00, visit=0),
                candidate("near-next-day", 11.00),
                candidate("baseline-end", 10.01),
            ],
        ),
        day_input(
            2,
            [
                candidate("day-2-first", 11.01),
                candidate("end", 11.02, visit=0),
            ],
        ),
    )


def test_dp_changes_internal_endpoint_to_reduce_next_day_origin_travel():
    result = optimize_multi_day_allocation(
        endpoint_choice_inputs(),
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=0),
    )

    assert result.days[0].ordered_ids[0] == "start"
    assert result.days[0].ordered_ids[-1] == "near-next-day"
    assert result.days[-1].ordered_ids[-1] == "end"
    assert max(result.final_load_minutes) <= max(result.initial_load_minutes)


def test_dp_keeps_fixed_anchor_in_the_original_day():
    first, second = endpoint_choice_inputs()
    meal = ScheduleStop(
        "meal",
        (11.015, 106.0),
        60,
        (TimeWindow(720, 780),),
        True,
    )
    second = MultiDayDayInput(
        day_index=second.day_index,
        candidates=second.candidates,
        fixed_stops=(meal,),
        baseline_order=second.baseline_order,
        schedule_options=second.schedule_options,
    )

    result = optimize_multi_day_allocation(
        (first, second),
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=0),
    )

    assert "meal" not in result.days[0].ordered_ids
    assert "meal" in result.days[1].ordered_ids
    assert result.days[1].schedule.skipped == ()


def test_endpoint_dp_is_deterministic():
    first = optimize_multi_day_allocation(
        endpoint_choice_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=0),
    )
    second = optimize_multi_day_allocation(
        endpoint_choice_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=0),
    )

    assert first == second
```

- [ ] **Step 2: Run the unit file and verify RED.**

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py -q
```

Expected: the baseline evaluator keeps `baseline-end`; the endpoint-choice assertion fails while Task 1 tests remain green.

- [ ] **Step 3: Implement bounded label-setting across days.**

Add immutable internal labels:

```python
@dataclass(frozen=True)
class _AllocationLabel:
    day_results: tuple[MultiDayDayResult, ...]
    current_end_id: str
    loads: tuple[float, ...]
    total_travel_minutes: float
    total_backtrack_ratio: float
    area_switches: int
```

Use these helpers:

```python
def _solve_allocation(
    days: tuple[MultiDayDayInput, ...],
    allocation: Allocation,
    candidate_by_id: dict[str, SelectionCandidate],
    global_start_id: str,
    global_end_id: str,
    options: MultiDayOptions,
    deadline: float,
    cache: dict[tuple[object, ...], MultiDayDayResult | None],
) -> tuple[MultiDayDayResult, ...]:
    """Return the best complete route chain for one ownership allocation."""


def _label_dominates(left: _AllocationLabel, right: _AllocationLabel) -> bool:
    """Compare labels that finish on the same endpoint."""
```

For each partial label and current day:

1. Day 1 endpoint choices are all content IDs except global start.
2. Intermediate-day endpoint choices are every content ID owned by that day.
3. Last-day endpoint choices contain only global end.
4. The prior label's `current_end_id` becomes the next synthetic origin.
5. Cache `_schedule_day(...)` by `(day_index, sorted_content_ids, fixed_ids, previous_end_id, current_end_id)`.
6. Drop labels with infeasible schedules; propagate only complete required schedules.
7. Group labels by current endpoint; remove dominated labels and keep at most `max_labels_per_endpoint` by deterministic objective.

The label comparator must order by maximum load, load range, total absolute deviation, total travel, total backtrack, area switches, ordered IDs, and endpoint ID. Use the same first six metrics for dominance, requiring at least one strict improvement.

Before dynamic endpoints, evaluate the fixed Phase 3 baseline endpoints once to populate `initial_load_minutes`. The dynamic DP includes those endpoint choices, so it cannot return a worse complete objective than the fixed baseline. With `max_iterations=0`, `optimize_multi_day_allocation(...)` now returns the best endpoint-DP result and no ownership moves.

- [ ] **Step 4: Run DP, scheduler, and selection regressions.**

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
python -m ruff check agent/itinerary_multiday.py agent/tests/test_itinerary_multiday.py
```

- [ ] **Step 5: Commit endpoint DP.**

```powershell
git add agent/itinerary_multiday.py agent/tests/test_itinerary_multiday.py
git commit -m "feat: add multiday endpoint dp"
```

- [ ] **Step 6: Run a Task 2 scoped spec/quality review.**

Review endpoint enumeration, label dominance, cache keys, fixed-anchor ownership, deadline propagation, and global start/end preservation. Fix every Critical or Important finding and rerun the Task 2 matrix before starting Task 3.

## Task 3: Deterministic Adjacent-day Local Search

**Files:**
- Modify: `agent/itinerary_multiday.py`
- Modify: `agent/tests/test_itinerary_multiday.py`

**Interfaces:**
- Consumes: Task 2 `_solve_allocation(...)` and result objective.
- Produces: canonical ownership allocations, deterministic `boundary-swap`/`relocate`/`swap` neighborhoods, bounded steepest-descent, shared deadline behavior, move diagnostics, and the final `MultiDayResult`.

- [ ] **Step 1: Add failing neighborhood, balance, and deadline tests.**

Append:

```python
import itinerary_multiday as multiday_module


def imbalanced_inputs() -> tuple[MultiDayDayInput, MultiDayDayInput]:
    return (
        day_input(
            1,
            [
                candidate("start", 10.00, visit=0),
                candidate("heavy-fixed", 10.02, visit=200),
                candidate("move-me", 10.04, visit=100),
                candidate("day-1-end", 10.06, visit=0),
            ],
        ),
        day_input(
            2,
            [
                candidate("day-2-a", 10.08, visit=0),
                candidate("day-2-b", 10.10, visit=30),
                candidate("day-2-c", 10.12, visit=30),
                candidate("end", 10.14, visit=0),
            ],
        ),
    )


def test_neighbor_generator_contains_all_bounded_operation_kinds():
    days = imbalanced_inputs()
    allocation = tuple(day.baseline_order for day in days)
    baseline_rank = {
        stop_id: index
        for index, stop_id in enumerate(
            stop_id for day in allocation for stop_id in day
        )
    }
    neighbors = multiday_module._generate_neighbors(
        allocation=allocation,
        baseline_counts=tuple(len(day) for day in allocation),
        locked_ids=frozenset({"start", "end"}),
        baseline_rank=baseline_rank,
        current_day_results=(),
        options=MultiDayOptions(),
    )

    kinds = {neighbor.kind for neighbor in neighbors}
    assert {"relocate", "swap", "boundary-swap"} <= kinds
    assert len({neighbor.allocation for neighbor in neighbors}) == len(neighbors)


def test_local_search_relocates_content_to_reduce_maximum_day_load():
    result = optimize_multi_day_allocation(
        imbalanced_inputs(),
        global_start_id="start",
        global_end_id="end",
        options=MultiDayOptions(max_iterations=12),
    )

    assert "move-me" not in result.days[0].content_ids
    assert "move-me" in result.days[1].content_ids
    assert max(result.final_load_minutes) < max(result.initial_load_minutes)
    assert result.move_count == 1
    assert result.moved_out_by_day[0] == ("move-me",)
    assert result.moved_in_by_day[1] == ("move-me",)


def test_local_search_result_is_repeatable():
    first = optimize_multi_day_allocation(
        imbalanced_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=12),
    )
    second = optimize_multi_day_allocation(
        imbalanced_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=12),
    )

    assert first == second


def test_deadline_after_incumbent_returns_complete_result(monkeypatch):
    monkeypatch.setattr(
        multiday_module,
        "_local_search_deadline_reached",
        lambda _deadline: True,
    )

    result = optimize_multi_day_allocation(
        imbalanced_inputs(),
        "start",
        "end",
        MultiDayOptions(max_iterations=12),
    )

    emitted = [stop_id for day in result.days for stop_id in day.content_ids]
    assert len(emitted) == len(set(emitted)) == 8
    assert result.solver == "multiday-deadline"
    assert "multiday-deadline-reached" in result.warnings
```

- [ ] **Step 2: Run the unit file and confirm RED.**

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py -q
```

Expected: `_generate_neighbors` and `_local_search_deadline_reached` do not exist; the optimizer retains baseline ownership.

- [ ] **Step 3: Implement canonical neighborhoods, objective, and bounded search.**

Add:

```python
@dataclass(frozen=True)
class _AllocationNeighbor:
    kind: str
    allocation: Allocation


def _generate_neighbors(
    allocation: Allocation,
    baseline_counts: tuple[int, ...],
    locked_ids: frozenset[str],
    baseline_rank: dict[str, int],
    current_day_results: tuple[MultiDayDayResult, ...],
    options: MultiDayOptions,
) -> tuple[_AllocationNeighbor, ...]:
    """Return unique deterministic adjacent-day ownership neighbors."""


def _result_objective(
    result_days: tuple[MultiDayDayResult, ...],
    allocation: Allocation,
    baseline_owner: dict[str, int],
    candidate_by_id: dict[str, SelectionCandidate],
) -> tuple[object, ...]:
    """Build the final lexicographic allocation objective."""
```

Canonicalize every day by `baseline_rank` after moving IDs. Generate adjacent pairs in increasing day index. For each pair:

1. Generate the current route-boundary swap first: use final routed content positions when `current_day_results` is available; otherwise use the last and first IDs of the canonical left/right allocation. Exclude locked IDs.
2. Generate left-to-right and right-to-left relocates for every unlocked content ID.
3. Generate every unlocked cross-pair swap.
4. Reject duplicates and allocations whose day count is below `min_content_per_day` or whose absolute delta from its baseline count exceeds `max_count_delta`.
5. Return neighbors ordered by day pair, operation order `boundary-swap`, `relocate`, `swap`, then canonical allocation signature.

The final objective must be:

```python
(
    max(loads),
    max(loads) - min(loads),
    sum(abs(load - sum(loads) / len(loads)) for load in loads),
    sum(day.schedule.total_travel_minutes for day in result_days),
    sum(day.schedule.backtrack_ratio for day in result_days),
    area_switch_count,
    moved_owner_count,
    allocation,
    tuple(day.ordered_ids for day in result_days),
)
```

Start from Task 2's endpoint-DP result. Run at most `max_iterations`; evaluate every neighbor that fits before the shared deadline and accept the single best strictly improving neighbor. Stop when there is no improvement. Cache `_solve_allocation(...)` by canonical allocation.

Implement `_local_search_deadline_reached(deadline)` as a thin `time.perf_counter() >= deadline` helper so the deadline behavior is deterministic under test. When it returns true after a complete incumbent exists, return that incumbent with solver `multiday-deadline` and warning `multiday-deadline-reached`.

Compute `baseline_owner`, final owner, `move_count`, and per-day sorted moved-in/out tuples from the final allocation. Preserve `overnight-origin-approximated` for every successful multi-day result.

- [ ] **Step 4: Run Phase 4 unit and Phase 3 regression tests.**

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
python -m ruff check agent/itinerary_multiday.py agent/tests/test_itinerary_multiday.py
```

- [ ] **Step 5: Commit local search.**

```powershell
git add agent/itinerary_multiday.py agent/tests/test_itinerary_multiday.py
git commit -m "feat: balance itinerary days locally"
```

- [ ] **Step 6: Run a Task 3 scoped spec/quality review.**

Review neighborhood completeness/deduplication, count bounds, objective ordering, incumbent safety, move accounting, determinism, and deadline behavior. Fix every Critical or Important finding and rerun the Task 3 matrix before generator integration.

## Task 4: Generator Integration, Projection, and Fallback

**Files:**
- Modify: `agent/itinerary_gen.py`
- Create: `agent/tests/test_itinerary_generator_multiday.py`
- Modify: `agent/tests/test_cov_itinerary_gen.py` only when an existing exact schedule-key assertion needs an additive compatibility update.

**Interfaces:**
- Consumes: `MultiDayDayInput`, `MultiDayOptions`, `MultiDayResult`, and `optimize_multi_day_allocation(...)` from Task 3.
- Produces: unchanged `generate_itinerary(...)` arguments and top-level keys; final content ownership/order projected from Phase 4; route timing fields refreshed; nested `schedule.allocation` diagnostics; complete Phase 3 fallback.

- [ ] **Step 1: Write failing generator integration tests.**

Create `agent/tests/test_itinerary_generator_multiday.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itinerary_gen
import knowledge
from itinerary_schedule import NoFeasibleScheduleError


def _place(place_id: str, coordinates=(10.0, 106.0)) -> dict:
    return {
        "id": place_id,
        "name": place_id,
        "type": "place",
        "area": "vinh-long",
        "coordinates": coordinates,
    }


def _entity(
    entity_id: str,
    coordinates: list[float],
    entity_type: str,
    visit_minutes: int,
    confidence: float,
) -> dict:
    return {
        "id": entity_id,
        "name": entity_id.upper(),
        "type": entity_type,
        "placeId": "p-vl",
        "confidence": confidence,
        "summary": "phase 4 generator fixture",
        "coordinates": coordinates,
        "visit_minutes": visit_minutes,
    }


@pytest.fixture
def imbalanced_generator_entities(monkeypatch):
    ordered_ids = [
        "start",
        "heavy-fixed",
        "move-me",
        "day-1-end",
        "day-2-a",
        "day-2-b",
        "day-2-c",
        "end",
    ]
    entities = {
        "p-vl": _place("p-vl"),
        "start": _entity("start", [10.00, 106.0], "attraction", 0, 1.00),
        "heavy-fixed": _entity("heavy-fixed", [10.02, 106.0], "experience", 200, 0.99),
        "move-me": _entity("move-me", [10.04, 106.0], "craft_village", 100, 0.98),
        "day-1-end": _entity("day-1-end", [10.06, 106.0], "product", 0, 0.97),
        "day-2-a": _entity("day-2-a", [10.08, 106.0], "attraction", 0, 0.96),
        "day-2-b": _entity("day-2-b", [10.10, 106.0], "experience", 30, 0.95),
        "day-2-c": _entity("day-2-c", [10.12, 106.0], "craft_village", 30, 0.94),
        "end": _entity("end", [10.14, 106.0], "product", 0, 0.93),
    }
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})

    def forced_select(candidates, total, areas, days):
        by_id = {item["entity"]["id"]: item for item in candidates}
        return [by_id[stop_id] for stop_id in ordered_ids]

    monkeypatch.setattr(itinerary_gen, "_select_diverse", forced_select)
    return entities


def _content_ids(day: dict) -> list[str]:
    return [
        stop["entity"]["id"]
        for stop in day["stops"]
        if not stop.get("is_meal") and not stop.get("is_rest")
    ]


def test_generator_balances_days_and_preserves_global_endpoints(
    imbalanced_generator_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )
    first, second = result["day_plans"]
    allocation = first["schedule"]["allocation"]

    assert _content_ids(first)[0] == "start"
    assert _content_ids(second)[-1] == "end"
    assert "move-me" not in _content_ids(first)
    assert "move-me" in _content_ids(second)
    assert allocation["solver"] in {
        "multiday-dp-local-search",
        "multiday-deadline",
    }
    assert allocation["final_load_minutes"] < allocation["initial_load_minutes"]
    assert first["schedule"]["selected_count"] == 4
    assert second["schedule"]["selected_count"] == 4


def test_generator_multiday_keeps_entity_uniqueness_and_total_stops(
    imbalanced_generator_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )
    emitted = [
        stop["entity"]["id"]
        for day in result["day_plans"]
        for stop in day["stops"]
    ]

    assert len(emitted) == len(set(emitted))
    assert result["total_stops"] == len(emitted)
    assert all("allocation" in day["schedule"] for day in result["day_plans"])


def test_generator_keeps_phase3_output_when_multiday_solver_fails(
    imbalanced_generator_entities,
    monkeypatch,
):
    def fail_multiday(*_args, **_kwargs):
        raise NoFeasibleScheduleError("phase 4 unavailable")

    monkeypatch.setattr(
        itinerary_gen,
        "optimize_multi_day_allocation",
        fail_multiday,
    )
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )

    assert all(
        day["schedule"]["allocation"] == {
            "solver": "multiday-fallback",
            "move_count": 0,
            "moved_in_ids": [],
            "moved_out_ids": [],
            "warnings": ["multiday-fallback"],
        }
        for day in result["day_plans"]
    )


def test_one_day_generator_does_not_add_allocation_diagnostics(
    imbalanced_generator_entities,
):
    result = itinerary_gen.generate_itinerary(
        days=1,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=[],
    )

    assert "allocation" not in result["day_plans"][0]["schedule"]
```

- [ ] **Step 2: Run generator Phase 4 tests and confirm RED.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_multiday.py -q
```

Expected: allocation diagnostics are absent and `move-me` remains on day 1.

- [ ] **Step 3: Refactor the generator adapter and integrate Phase 4.**

Import the Task 3 contracts and keep the public generator signature unchanged:

```python
from itinerary_multiday import (
    MultiDayDayInput,
    MultiDayOptions,
    optimize_multi_day_allocation,
)
```

Refactor `_build_joint_day_plans(...)` into these exact stages:

1. Keep the existing seed-day, raw-pool, reservation, anchor, and Phase 3 selection behavior.
2. For each day, store the successful `SelectionResult`, its selected `SelectionCandidate` objects, raw item mapping, anchor items, anchor warnings, and Phase 3 selection diagnostics without projecting stops yet.
3. For a fallback Phase 3 day, store the complete existing projected day and mark the multi-day batch ineligible.
4. If `days < 2`, project the stored Phase 3 result exactly as before and do not add `schedule.allocation`.
5. If any day is ineligible, project all Phase 3 results unchanged and add the minimal fallback allocation object to every multi-day schedule.
6. Otherwise build one `MultiDayDayInput` per day from the Phase 3 selected content only. `baseline_order` is the Phase 3 schedule order after filtering anchor IDs. Fixed stops are the current day's meal/rest `ScheduleStop` values.
7. Use the first content ID of day 1 as global start and the last content ID of the final day as global end. Call `optimize_multi_day_allocation(...)` with default `MultiDayOptions()`.
8. On `ValueError` or `NoFeasibleScheduleError`, use the complete Phase 3 projection and minimal fallback allocation diagnostics. Do not catch other exceptions.
9. On success, project `MultiDayDayResult.ordered_ids` with the global raw content mapping and the original day's anchor-item mapping. Synthetic origins are absent from `ordered_ids` and must never be added to `stops`.
10. Start from the Phase 3 selection diagnostics, replace route timing fields from `MultiDayDayResult.schedule`, preserve all `selection_*` fields, and add per-day allocation diagnostics from `MultiDayResult`.
11. Recompute `area_focus` from the final content raw items and keep `total_stops` based on emitted stops.

Use these two helpers so fallback and success shapes are centralized:

```python
def _fallback_allocation_diagnostics() -> dict:
    return {
        "solver": "multiday-fallback",
        "move_count": 0,
        "moved_in_ids": [],
        "moved_out_ids": [],
        "warnings": ["multiday-fallback"],
    }


def _allocation_diagnostics(result, day_index: int) -> dict:
    return {
        "solver": result.solver,
        "initial_load_minutes": result.initial_load_minutes[day_index],
        "final_load_minutes": result.final_load_minutes[day_index],
        "max_imbalance_minutes": result.max_imbalance_minutes,
        "move_count": result.move_count,
        "moved_in_ids": list(result.moved_in_by_day[day_index]),
        "moved_out_ids": list(result.moved_out_by_day[day_index]),
        "warnings": list(result.warnings),
    }
```

When refreshing route diagnostics, filter the internal synthetic origin out of `skipped` defensively and retain the union of Phase 3 warnings, anchor warnings, and final scheduler warnings in deterministic order without duplicates.

- [ ] **Step 4: Run generator, MCP, Phase 3, and Phase 4 regressions.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_multiday.py agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_generator_selection.py agent/tests/test_itinerary_generator_mcp.py agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
python -m ruff check agent/itinerary_multiday.py agent/itinerary_gen.py agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_generator_multiday.py
git diff --check
```

Expected: new multi-day behavior passes, one-day output remains Phase 3-only, and all focused compatibility tests remain green.

- [ ] **Step 5: Commit generator integration.**

```powershell
git add agent/itinerary_gen.py agent/tests/test_itinerary_generator_multiday.py agent/tests/test_cov_itinerary_gen.py
git commit -m "feat: integrate multiday itinerary balancing"
```

- [ ] **Step 6: Run a Task 4 scoped spec/quality review.**

Review public API preservation, Phase 3 diagnostic semantics, synthetic-origin filtering, anchor ownership, uniqueness, fallback completeness, `area_focus`, and `total_stops`. Fix every Critical or Important finding and rerun the Task 4 matrix before documentation.

## Task 5: Contract Documentation and Final Regression Matrix

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md`
- Modify: `docs/superpowers/specs/2026-07-30-phase4-multiday-allocation-design.md`

**Interfaces:**
- Consumes: Task 4 final public behavior and additive allocation diagnostics.
- Produces: published Phase 4 contract, completed roadmap status, explicit pre-allocation semantics for Phase 3 selection diagnostics, zero-cost wording, and the final focused verification evidence.

- [ ] **Step 1: Re-run the behavior contract before documentation edits.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_multiday.py agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_generator_mcp.py -q
```

Expected: the public behavior is already green; documentation is the only remaining deliverable.

- [ ] **Step 2: Update the API contract and roadmap.**

In `docs/api-contract.md`, document:

1. Phase 4 runs locally only for safe multi-day Phase 3 results.
2. `schedule.allocation` fields and fallback shape.
3. Phase 3 `selection_*` fields describe pre-allocation selection; `allocation` describes final cross-day ownership.
4. Synthetic origins affect travel/load but are never emitted.
5. Generator makes zero OSRM/web/LLM/paid requests and keeps the MCP signature/saved schema unchanged.

In the roadmap, mark only Phase 4 complete. Leave Phases 5-6 pending and preserve no-deploy/no-migration wording. Change the Phase 4 algorithm description from future tense to the delivered bounded endpoint-DP plus adjacent local-search behavior.

Change the Phase 4 design status to `complete` only after the focused matrix is green.

- [ ] **Step 3: Run the complete focused Phase 4 matrix and quality checks.**

```powershell
python -m pytest agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_generator_multiday.py agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_generator_selection.py agent/tests/test_itinerary_generator_mcp.py agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
python -m ruff check agent/itinerary_multiday.py agent/itinerary_gen.py agent/tests/test_itinerary_multiday.py agent/tests/test_itinerary_generator_multiday.py agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_generator_selection.py
git diff --check
```

Expected: all focused tests pass; no dependency, network, paid API, migration, deploy, schema, MCP signature, or frontend changes appear in the diff. Do not claim the full repository suite passes.

- [ ] **Step 4: Commit documentation.**

```powershell
git add docs/api-contract.md docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md docs/superpowers/specs/2026-07-30-phase4-multiday-allocation-design.md
git commit -m "docs: publish phase 4 multiday allocation contract"
```

- [ ] **Step 5: Run final whole-branch review and record the checkpoint.**

Review the full branch diff from the Phase 3 merge base through the documentation commit. Confirm every spec invariant, focused test result, Ruff result, and zero-cost boundary. Fix all Critical/Important findings in a final scoped wave, rerun the full focused matrix, then mark the plan and design status complete in a separate checkpoint commit.

## Verification Checklist

- [ ] Every production task observes a failing test before implementation.
- [ ] Every task receives task-scoped spec and quality review before the next task.
- [ ] Global content ID set is unchanged by Phase 4 in all success fixtures.
- [ ] Global first/last content IDs remain fixed.
- [ ] Synthetic origin IDs never appear in public stops.
- [ ] Phase 3 selection diagnostics remain intact as pre-allocation history.
- [ ] Focused Phase 4 + Phase 3 matrix passes on the final branch result.
- [ ] Ruff and `git diff --check` are clean.
- [ ] No dependency, network call, paid API, migration, deploy, saved-schema change, MCP signature change, or frontend contract change is introduced.
- [ ] Final whole-branch review is clean or only contains explicitly accepted non-load-bearing minors.
