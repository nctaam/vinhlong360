# Phase 3 - Joint POI and Route Selection Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate deterministic prize-collecting POI selection with time-aware route scheduling inside `generate_itinerary(...)` while preserving the existing public API and zero-cost constraints.

**Architecture:** Add a dependency-free `agent/itinerary_selection.py` wrapper that treats the existing `schedule_stop_order(...)` as the feasibility oracle. Exact bounded subset search handles small pools, deterministic beam search handles larger pools, and bounded destroy/repair improves the incumbent. `agent/itinerary_gen.py` owns candidate collection, day seeds, global entity reservations, anchor preparation, response projection, and the Phase 2B fallback.

**Tech Stack:** Python 3.11+, existing `agent/itinerary_schedule.py`, standard library only, pytest, existing MCP/API contracts.

## Global Constraints

- Keep the existing `generate_itinerary(...)` signature and all current response keys.
- Keep `day_plans[*].stops[*]`, saved-itinerary schema, MCP wrapper signature, public optimizer endpoint, and frontend contract unchanged.
- Add new fields only under `day_plans[*].schedule`; additions must be optional and backward-compatible.
- Use only local Haversine travel matrices in the generator; do not call OSRM, web services, or an LLM.
- Add no Python/NPM dependency, API key, container, migration, DB table, or background request.
- Preserve target content counts: 5 content POIs for one day, 4 content POIs per day for multi-day itineraries.
- Keep at most 20 POI candidates in a day's post-prune solver pool.
- Preserve the Phase 2B seed day's first and last content stops as required endpoints; middle content stops are optional.
- Meal/rest anchors participate in feasibility; meals must be real unused dish/product entities and rests remain synthetic local stops.
- Reserve entity IDs globally so no entity is emitted twice across days or as both content and a meal.
- If required coordinates, matrix validity, or a safe incumbent is unavailable, fall back to the unchanged Phase 2B day builder and record a warning.
- Do not deploy, migrate, push, call paid services, or claim the full backend suite passes.

---

## Task 1: Selection Contracts and Dominance Prune

**Files:**
- Create: `agent/itinerary_selection.py`
- Create: `agent/tests/test_itinerary_selection.py`

**Interfaces:**
- Consumes: `ScheduleOptions`, `ScheduleResult`, `ScheduleStop`, `TravelMatrix` from `agent/itinerary_schedule.py`.
- Produces: immutable `SelectionCandidate`, `SelectionOptions`, `DroppedCandidate`, `SelectionResult`; deterministic `prune_candidates(...)`; validation helpers used by the later objective comparator; the public `select_and_schedule_day(...)` entry point with an exact-search dispatch stub that raises no exception for an already-empty optional pool.

- [x] **Step 1: Write failing contract and prune tests.**

Add these fixtures and tests to `agent/tests/test_itinerary_selection.py`:

```python
import pytest

from itinerary_schedule import ScheduleOptions, ScheduleStop, TimeWindow, build_fallback_matrix
from itinerary_selection import (
    DroppedCandidate,
    SelectionCandidate,
    SelectionOptions,
    prune_candidates,
)


def _latitude_for(stop_id):
    if stop_id == "start":
        return 10.0
    if stop_id == "end":
        return 10.2
    if stop_id.startswith("poi-"):
        return 10.02 + int(stop_id.removeprefix("poi-")) * 0.01
    return 10.1


def candidate(stop_id, reward, entity_type="attraction", area="vinh-long", visit=60):
    return SelectionCandidate(
        stop=ScheduleStop(stop_id, (_latitude_for(stop_id), 106.0), visit),
        reward=reward,
        entity_type=entity_type,
        area=area,
    )


def matrix_for(*stop_ids):
    stops = [
        ScheduleStop(stop_id, (_latitude_for(stop_id), 106.0), 0)
        for stop_id in stop_ids
    ]
    return build_fallback_matrix(stops, "driving")


def test_dominance_prune_keeps_higher_reward_shorter_candidate():
    kept, dropped = prune_candidates([
        candidate("good", 10.0, visit=30),
        candidate("dominated", 8.0, visit=60),
    ], required_ids=frozenset(), max_candidates=20)

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


def test_selection_options_reject_invalid_bounds():
    with pytest.raises(ValueError):
        SelectionOptions(target_count=0)
    with pytest.raises(ValueError):
        SelectionOptions(target_count=4, exact_limit=-1)
```

The expectations are hand-derived: `good` dominates `dominated` because it has higher reward and shorter visit time; the required item cannot be removed by either rule.

- [x] **Step 2: Run the contract tests and verify the intended RED failure.**

Run:

```powershell
python -m pytest agent/tests/test_itinerary_selection.py -q
```

Expected: collection fails because `agent/itinerary_selection.py` and its public dataclasses do not exist yet.

- [x] **Step 3: Implement the contracts and deterministic prune.**

Implement:

```python
@dataclass(frozen=True)
class SelectionCandidate:
    stop: ScheduleStop
    reward: float
    entity_type: str
    area: str
    fee_value: float | None = None


@dataclass(frozen=True)
class SelectionOptions:
    target_count: int
    exact_limit: int = 8
    beam_width: int = 32
    repair_iterations: int = 32
    deadline_seconds: float = 1.5


@dataclass(frozen=True)
class DroppedCandidate:
    stop_id: str
    reason: str


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
```

Validate finite non-negative rewards, non-empty IDs/types/areas, positive target count, non-negative search bounds, positive deadline, and a maximum candidate cap of 20. Implement `prune_candidates(candidates, required_ids, max_candidates=20)` with same-area/same-type dominance, required preservation, coordinate validity filtering, deterministic cap ordering `(required first, -reward, visit_minutes, id)`, and one dropped reason per raw candidate.

- [x] **Step 4: Run the contract tests and the existing scheduler/optimizer tests.**

```powershell
python -m pytest agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
```

Expected: all existing tests remain green and the new contract tests pass.

- [x] **Step 5: Commit the contracts.**

```powershell
git add agent/itinerary_selection.py agent/tests/test_itinerary_selection.py
git commit -m "feat: add joint itinerary selection contracts"
```

## Task 2: Exact Subset Search and Scheduler Feasibility Cache

**Files:**
- Modify: `agent/itinerary_selection.py`
- Modify: `agent/tests/test_itinerary_selection.py`

**Interfaces:**
- Consumes: Task 1 contracts and `prune_candidates(...)`.
- Produces: `select_and_schedule_day(candidates, required_ids, fixed_stops, matrix, schedule_options, selection_options) -> SelectionResult` with exact search for at most `exact_limit` optional candidates.

- [x] **Step 1: Write failing exact-search behavior tests.**

Add a deterministic matrix helper and these tests:

```python
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
        candidates=[candidate("start", 1.0, visit=0), candidate("long", 9.0, visit=180), candidate("end", 1.0, visit=0)],
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
        candidates=[candidate("start", 1.0, visit=0), candidate("poi", 8.0, visit=60), candidate("end", 1.0, visit=0)],
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(ScheduleStop("meal", (10.1, 106.0), 60, (TimeWindow(720, 780),), True),),
        matrix=matrix_for("start", "poi", "meal", "end"),
        schedule_options=ScheduleOptions(day_start_minute=480, day_end_minute=840),
        selection_options=SelectionOptions(target_count=3, exact_limit=8),
    )

    assert "meal" in result.schedule.ordered_ids
```

The fixture must import `TimeWindow`, `ScheduleOptions`, and `select_and_schedule_day`, and `matrix_for(...)` must build a square `TravelMatrix` containing exactly the listed IDs. The test must fail because `select_and_schedule_day(...)` is not implemented, not because of fixture setup.

- [x] **Step 2: Run the exact tests and confirm RED.**

```powershell
python -m pytest agent/tests/test_itinerary_selection.py -q
```

Expected: the new selection tests fail at the missing selection entry point while Task 1 tests remain green.

- [x] **Step 3: Implement exact subset search with a shared deadline and cache.**

Implement these internal operations:

1. Validate required IDs, fixed stop IDs, unique IDs, and matrix coverage.
2. Build a full stop sequence with the required start first, required end last, optional candidates in the middle, and fixed meal/rest stops in the middle.
3. Cache scheduler calls by `frozenset(content_ids)` and create a matrix view by ID without recomputing Haversine distances.
4. Enumerate subsets in reward-descending order, preserving required IDs.
5. Prune a branch when its cardinality cannot beat the incumbent, its reward upper bound cannot beat the incumbent at equal cardinality, visit-time lower bound exceeds the day window, or the shared deadline expires.
6. Compare feasible results lexicographically: selected count, total reward, type diversity, travel minutes, backtrack ratio, minimum slack, selected IDs, ordered IDs.
7. Return `selection-deadline-reached` with the incumbent when a deadline occurs after a feasible result; return `NoFeasibleScheduleError` only internally and let the public function signal fallback when no incumbent exists.

Use `schedule_stop_order(...)` for every subset evaluation; do not import private scheduler helpers.

- [x] **Step 4: Run exact, scheduler, and optimizer tests.**

```powershell
python -m pytest agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
```

Expected: all tests pass, including fixed-anchor feasibility and explicit drop reasons.

- [x] **Step 5: Commit exact search.**

```powershell
git add agent/itinerary_selection.py agent/tests/test_itinerary_selection.py
git commit -m "feat: add exact joint itinerary selection"
```

## Task 3: Deterministic Beam Search and Bounded Repair

**Files:**
- Modify: `agent/itinerary_selection.py`
- Modify: `agent/tests/test_itinerary_selection.py`

**Interfaces:**
- Consumes: Task 2 selection entry point and feasibility cache.
- Produces: deterministic `selection-beam` results for pools above `exact_limit`; bounded destroy/repair and swap improvement with no random or network behavior.

- [x] **Step 1: Write failing beam/repair tests.**

Add:

```python
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


def run_selection_with_greedy_trap(repair_iterations):
    start = candidate("start", 1.0, visit=0)
    end = candidate("end", 1.0, visit=0)
    pool = [
        start,
        candidate("trap", 30.0, entity_type="trap", visit=540),
        candidate("high", 20.0, entity_type="high", visit=30),
        candidate("short", 19.0, entity_type="short", visit=30),
        end,
    ]
    return select_and_schedule_day(
        candidates=pool,
        required_ids=frozenset({"start", "end"}),
        fixed_stops=(),
        matrix=matrix_for(*(item.stop.id for item in pool)),
        schedule_options=ScheduleOptions(day_start_minute=480, day_end_minute=1080),
        selection_options=SelectionOptions(
            target_count=4,
            exact_limit=2,
            beam_width=1,
            repair_iterations=repair_iterations,
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
    without_repair = run_selection_with_greedy_trap(repair_iterations=0)
    result = run_selection_with_greedy_trap(repair_iterations=32)

    assert without_repair.selected_count == 3
    assert "trap" in without_repair.selected_ids
    assert result.selected_count == 4
    assert "high" in result.selected_ids
    assert "short" in result.selected_ids
    assert "trap" not in result.selected_ids
```

Fixtures must use real `ScheduleStop` objects and a controlled local matrix. Assertions must inspect public `SelectionResult`, not private frontier state.

- [x] **Step 2: Run the beam tests and confirm RED.**

```powershell
python -m pytest agent/tests/test_itinerary_selection.py -q
```

Expected: large-pool dispatch still uses the exact solver or repair is absent, so the new assertions fail for the missing behavior.

- [x] **Step 3: Implement deterministic beam and repair.**

Implement beam states with `(selected_ids, remaining_ids, reward_upper_bound, incumbent_signature)`, expand candidates in `(-reward, visit_minutes, id)` order, retain `beam_width=32`, and use the same objective comparator as exact search. Add at most `repair_iterations=32` deterministic neighborhoods:

- remove the lowest reward-efficiency selected optional;
- insert the highest reward dropped candidate;
- swap one selected optional for one dropped candidate;
- re-evaluate through the same cached scheduler oracle.

Use a monotonic deadline derived from `selection_options.deadline_seconds`. Never seed or call a random generator. Add `selection-repair-deadline-reached` only when a feasible incumbent exists and repair stops early.

- [x] **Step 4: Run deterministic and focused regression tests.**

```powershell
python -m pytest agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
```

Expected: exact and beam results are repeatable, repair never violates hard constraints, and no existing scheduler/optimizer test regresses.

- [x] **Step 5: Commit beam and repair.**

```powershell
git add agent/itinerary_selection.py agent/tests/test_itinerary_selection.py
git commit -m "feat: add deterministic beam and repair selection"
```

## Task 4: Integrate Joint Selection into the Generator

**Files:**
- Modify: `agent/itinerary_gen.py`
- Create: `agent/tests/test_itinerary_generator_selection.py`
- Modify: `agent/tests/test_cov_itinerary_gen.py` only if an existing fixture needs a narrow compatibility assertion

**Interfaces:**
- Consumes: `SelectionCandidate`, `SelectionOptions`, `SelectionResult`, `prune_candidates(...)`, and `select_and_schedule_day(...)`.
- Produces: unchanged `generate_itinerary(...)` arguments/response keys with per-day selection diagnostics and Phase 2B fallback.

- [x] **Step 1: Write failing generator integration tests.**

Create a new test fixture in `agent/tests/test_itinerary_generator_selection.py` with deterministic coordinates, durations, opening hours, scores, two areas, and one dish candidate. The fixture must patch `knowledge._entities`, `knowledge._relationships`, and `knowledge._itineraries`; define local `_place(...)` and `_entity(...)` helpers that include parent-place coordinates and an optional entity coordinate. Add:

```python
def test_generator_selects_feasible_high_reward_subset_and_reports_drops(generator_entities):
    result = itinerary_gen.generate_itinerary(days=1, interests=["tong_hop"], areas=["vinh-long"])
    schedule = result["day_plans"][0]["schedule"]

    assert schedule["selection_solver"] in {"selection-exact", "selection-beam"}
    assert schedule["candidate_count"] >= schedule["selected_count"]
    assert all(item["reason"] for item in schedule["dropped_reasons"])


def test_generator_reserves_global_ids_before_meal_selection(two_day_entities):
    result = itinerary_gen.generate_itinerary(
        days=2,
        interests=["tong_hop"],
        areas=["vinh-long"],
        meal_anchors=["12:00"],
    )

    emitted_ids = [
        stop["entity"]["id"]
        for day in result["day_plans"]
        for stop in day["stops"]
    ]
    assert len(emitted_ids) == len(set(emitted_ids))


def test_generator_uses_phase2b_fallback_when_required_endpoint_lacks_coordinates(monkeypatch, missing_coordinate_entities):
    result = itinerary_gen.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])

    assert result["day_plans"][0]["schedule"]["solver"] == "legacy-fixed-order"
    assert "coordinates-missing" in result["day_plans"][0]["schedule"]["warnings"]
```

The fixture must expose `generator_entities`, `two_day_entities`, and `missing_coordinate_entities` by returning complete real-shaped entity/place dictionaries. Use this minimum fixture shape and extend it with the named day-two/missing-coordinate variants:

```python
def _place(place_id, coordinates):
    return {
        "id": place_id,
        "name": place_id,
        "type": "place",
        "area": "vinh-long",
        "coordinates": coordinates,
    }


def _entity(entity_id, coordinates, **fields):
    entity = {
        "id": entity_id,
        "name": entity_id.upper(),
        "type": "attraction",
        "placeId": "p-vl",
        "confidence": 1.0,
        "summary": "phase 3 selection fixture",
        "coordinates": coordinates,
    }
    entity.update(fields)
    return entity


@pytest.fixture
def generator_entities(monkeypatch):
    entities = {
        "p-vl": _place("p-vl", [10.0, 106.0]),
        "start": _entity("start", [10.0, 106.0], visit_minutes=0),
        "poi-a": _entity("poi-a", [10.04, 106.0], confidence=1.0, visit_minutes=45),
        "poi-b": _entity("poi-b", [10.08, 106.0], confidence=0.8, visit_minutes=120),
        "poi-c": _entity("poi-c", [10.12, 106.0], confidence=0.7, visit_minutes=30),
        "poi-d": _entity("poi-d", [10.14, 106.0], confidence=0.6, visit_minutes=180),
        "poi-e": _entity("poi-e", [10.16, 106.0], confidence=0.5, visit_minutes=45),
        "end": _entity("end", [10.18, 106.0], visit_minutes=0),
        "food": _entity("food", [10.06, 106.0], type="dish", confidence=1.0),
    }
    monkeypatch.setattr(knowledge, "_entities", entities)
    monkeypatch.setattr(knowledge, "_relationships", [])
    monkeypatch.setattr(knowledge, "_itineraries", {})
    return entities
```

`_place(...)` and `_entity(...)` must mirror the complete shapes used by `test_itinerary_generator_schedule.py`. `two_day_entities` must provide at least eight coordinate-valid content candidates plus one dish; `missing_coordinate_entities` must remove coordinates from the seed endpoint and its parent place so `_candidate_coordinates(...)` cannot fall back to a valid coordinate. The first test must assert emitted behavior and diagnostics, not source text or private selection state.

- [x] **Step 2: Run generator integration tests and confirm RED.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_selection.py -q
```

Expected: the new diagnostics are absent and the generator still follows the Phase 2B selection path.

- [x] **Step 3: Implement the generator adapter.**

In `agent/itinerary_gen.py`:

1. Keep `_collect_candidates(...)`, `_score_entity(...)`, `_select_diverse(...)`, `_build_day_schedule(...)`, and the public function signature intact.
2. Build all seed days before solving; reserve all seed endpoints globally and remove selected IDs from later pools.
3. Convert raw candidate dictionaries to `SelectionCandidate`, carrying entity type, area, score reward, visit duration, fee, opening windows, and coordinates.
4. Pre-prune each day and reserve IDs in every capped content pool before resolving meals; preserve the Phase 2B current-day and prior-day exclusion rules.
5. Build a local Haversine matrix for each day's content pool plus fixed anchors, then call `select_and_schedule_day(...)` with target count 5 or 4 and schedule options `day_start_minute=480`, `day_end_minute=1080`.
6. Project `ScheduleResult` placements into the current stop dictionaries, preserving `time`, `note`, `is_meal`, `is_rest`, and `time_min` removal behavior.
7. Add `selection_solver`, `candidate_count`, `selected_count`, `total_reward`, and `dropped_reasons` under `schedule`; keep existing travel/waiting/slack/warning keys unchanged.
8. On required-coordinate, matrix, no-incumbent, or expected scheduler errors, call the unchanged Phase 2B day builder and append `selection-fallback` without returning partial output.
9. Keep `total_stops` based on emitted stops and preserve cross-day uniqueness even when a meal or rest anchor is unavailable.

- [x] **Step 4: Run generator, anchor, scheduler, optimizer, and MCP tests.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_selection.py agent/tests/test_itinerary_generator_mcp.py agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
```

Expected: new selection behavior is green and all Phase 2B compatibility tests remain green.

- [x] **Step 5: Commit generator integration.**

```powershell
git add agent/itinerary_gen.py agent/tests/test_itinerary_generator_selection.py agent/tests/test_cov_itinerary_gen.py
git commit -m "feat: integrate joint POI route selection into generator"
```

## Task 5: Contract Documentation and Final Regression Matrix

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md`

**Interfaces:**
- Consumes: Task 4's additive schedule diagnostics and generator behavior.
- Produces: documentation for `selection_solver`, `candidate_count`, `selected_count`, `total_reward`, `dropped_reasons`, local fallback, and Phase 3 completion status; no MCP signature change.

- [ ] **Step 1: Re-run the behavior contract before documentation edits.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_selection.py agent/tests/test_itinerary_generator_mcp.py -q
```

Expected: the behavior contract is already green from Task 4; documentation remains the only uncommitted deliverable in this task.

- [ ] **Step 2: Update the API contract and roadmap.**

Keep planner-only OSRM budget bullets separate from generator no-network wording. Document that selection runs locally, diagnostics are additive, dropped POIs carry reasons, and Phase 2B fallback remains available. Mark only Phase 3 complete; leave Phases 4-6 pending and retain no-deploy/no-migration wording.

- [ ] **Step 3: Run the complete focused Phase 3 matrix and diff checks.**

```powershell
python -m pytest agent/tests/test_itinerary_selection.py agent/tests/test_itinerary_generator_selection.py agent/tests/test_itinerary_generator_mcp.py agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
git diff --check
```

Expected: all focused tests pass; no full-repository suite claim is made; no dependency, schema, network, migration, deploy, or frontend changes appear in the diff.

- [ ] **Step 4: Commit documentation.**

```powershell
git add docs/api-contract.md docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md
git commit -m "docs: publish phase 3 joint selection contract"
```

## Verification Checklist

- [ ] Every task has a failing test observed before production code.
- [ ] Every task receives a task-scoped spec/quality review before the next task starts.
- [ ] Final whole-branch review is clean or only has explicitly parked non-load-bearing minors.
- [ ] Focused Phase 3 matrix passes on the merged result.
- [ ] `git diff --check` is clean.
- [ ] No new dependency, network call, migration, deploy, paid API, saved-schema change, or frontend contract change is introduced.
