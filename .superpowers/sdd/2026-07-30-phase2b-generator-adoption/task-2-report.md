# Phase 2B Task 2 implementer report

## Scope and starting state

- Functional base: Task 1 commit `8076dc52e633c7e65e167d0c3d119d0e67edd49b`.
- The worktree also contained the workflow-only Task 1 report commit `ce417e67` plus pre-existing untracked SDD/plan artifacts; none of those files were modified by this task.
- Production and test edits stayed limited to `agent/itinerary_gen.py` and `agent/tests/test_itinerary_generator_schedule.py`.
- No docs, MCP, API/schema, dependency, network, or LLM changes were made.

## TDD evidence

### RED before production edits

Command:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py -q
```

First RED:

- Exit 1: 5 new anchor behavior tests failed and 6 Task 1 tests passed.
- Every new failure was `TypeError: generate_itinerary() got an unexpected keyword argument` for `meal_anchors` or `rest_anchors`.

After updating the existing fallback assertions for the required default meal-anchor diagnostic, a second RED confirmed both parts of the contract:

- Exit 1: 8 failed, 3 passed.
- Three Task 1 fallback tests lacked the new `meal-anchor-unavailable` diagnostic for the compatibility default.
- Five new tests still failed because the anchor arguments were absent.
- Failures were behavior assertions/signature gaps, not collection or harness errors.

### GREEN

Focused anchor suite:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py -q
```

- Exit 0: 11/11 tests passed.

Required matrix:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py -q
```

- Exit 0: 156/156 tests passed.

Diff check:

```text
git diff --check
```

- Exit 0; only repository LF-to-CRLF working-copy notices were printed.

## Implementation

### Public generator options

- Added optional `meal_anchors: list[str] | None = None` and `rest_anchors: list[str] | None = None` after the existing arguments, preserving existing positional calls and output fields.
- `meal_anchors=None` normalizes to `['12:00']`; `meal_anchors=[]` disables both scheduled and legacy meal insertion.
- `rest_anchors=None` normalizes to no rest anchors.

### Anchor normalization and diagnostics

- `_fixed_anchor_window()` validates `HH:MM` and `HhMM` values through the existing `parse_time_range()` grammar, then creates a duration-sized `TimeWindow`.
- A 60-minute meal window or 30-minute rest window forces the visit to start exactly at the requested minute.
- Invalid text or anchors that cannot fit within one day are omitted and add `invalid-anchor` without raising.

### Meal ownership

- Food candidates are collected independently from regular interest candidates, so `interests=['tham_quan']` can still use a real dish/product without changing regular stop selection.
- Each meal anchor selects an unused same-area dish/product with finite coordinates.
- The meal is a required 60-minute middle `ScheduleStop`, maps back with `is_meal=True`, and reuses the existing lunch note.
- Missing or coordinate-invalid candidates are not fabricated; the anchor is omitted with `meal-anchor-unavailable`.

### Rest ownership

- Each valid rest anchor creates one synthetic required 30-minute middle stop at a coordinate owned by a real selected route item.
- The emitted entity summary is `{id, name: 'Nghỉ', type: 'rest', summary: 'Khoảng nghỉ'}`, with `is_rest=True` and note `🪑 Nghỉ/đệm thời gian`.
- If no real neighboring coordinate is available, the rest is omitted with `rest-anchor-unavailable`.

### Endpoint, fallback, and diagnostics behavior

- The combined scheduler input remains ordered as original first endpoint, anchors, optional original middle stops, original last endpoint; Task 1 endpoint pinning remains intact.
- Anchors are required while original middle stops stay optional, so successful schedules preserve their skip reasons.
- Any invalid duration or infeasible combined required route returns the Task 1 legacy timeline with `schedule-fallback`, never a partial scheduled result.
- Missing original coordinates still return the legacy timeline, and legacy automatic lunch insertion remains available when meal anchors are enabled.
- Existing schedule diagnostic keys remain unchanged, and `total_stops` continues to count every emitted original, meal, and rest stop.

## Tests added or amended

- Real dish/product selection for an explicit `12h00` meal anchor.
- Synthetic rest entity, flag, note, and fixed `15h00` placement.
- Explicit empty meal anchor list disables insertion.
- Invalid meal/rest anchors are nonfatal and each add `invalid-anchor`.
- No-food fixture emits no fake meal and reports `meal-anchor-unavailable`.
- Existing fallback assertions include the compatibility-default meal diagnostic.

## Self-review

- The regular candidate pool is unchanged; food candidates cannot enter selected attraction stops merely because meal anchors are enabled.
- Meal candidates are unique within a day and never reuse a selected original entity.
- Fixed windows use the anchor plus the exact visit duration, so a late arrival makes the required combined route infeasible instead of silently shifting the anchor.
- Synthetic rest coordinates come only from finite coordinates on real day entities.
- Scheduler result mapping preserves optional skip diagnostics and excludes no required anchor from a successful schedule.
- No saved-itinerary schema, top-level field, or existing stop field was removed or renamed.

## Commit

- `3a4ad9a42c8ae84e1136a5e8447bf9ef597a29b9` - `feat: add configurable itinerary anchors`

## Concerns

- None for the scoped behavior. The worktree retains pre-existing untracked SDD/plan artifacts owned by the parent workflow.

## Review fix wave

### Findings verified

1. `legacy_stops` was built from the full food candidate pool before anchor validation. A coordinate-invalid meal could therefore be rejected by `_find_meal_anchor_candidate()` and still be emitted by `_build_day_stops()` when an original coordinate forced legacy fallback.
2. `_build_anchor_items()` initialized meal ownership only from the current day's originals. Since every day received the same food pool, the same top-ranked meal could be emitted on multiple days.

### Fix RED evidence

Command:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py -q
```

- Exit 1: 2 failed, 11 passed.
- The fallback regression emitted `is_meal=True` for the coordinate-invalid candidate while also reporting `meal-anchor-unavailable`.
- The two-day regression emitted `['food', 'food']` instead of consuming the only candidate once and reporting second-day unavailability.
- Tightened feasible meal/rest assertions required exact `12:00` and `15:00` start times.

### Review fix implementation

- `_build_day_plans()` now carries the IDs of meals actually emitted by earlier days and passes that ownership into each later day.
- `_build_anchor_items()` excludes those previously emitted meal IDs in addition to current-day original IDs.
- Ownership is updated only from final emitted `day_stops`, so a candidate is not consumed by a schedule attempt that emits no meal.
- Legacy fallback now receives only coordinate-valid meal items that passed anchor selection. An unavailable or coordinate-invalid candidate cannot reappear through the legacy lookup.
- The existing coverage fixture now includes an unused coordinate-valid food candidate, preserving its intended Task 1 legacy-lunch coverage without relying on duplicate or coordinate-invalid food.

### Review fix verification

Focused GREEN:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py -q
```

- Exit 0: 13/13 tests passed.

Required matrix:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py -q
```

- Exit 0: 158/158 tests passed.

Diff check:

- `git diff --check` exited 0; only repository LF-to-CRLF working-copy notices were printed.

### Review fix self-review

- A meal is consumed across days only after it appears in output, including a valid legacy fallback meal.
- Coordinate-invalid and unavailable candidates produce diagnostics without any meal entity in scheduled or fallback output.
- Multiple anchors can still use distinct candidates within one day; only emitted candidates are unavailable to later days.
- Fixed-window tests now prove the exact requested start, not merely a lower bound.
- No schema, dependency, network, docs, or MCP behavior changed.

### Review fix commit

- `91b372df874ce2e5490d18a66c405d0d96608de5` - `fix: preserve meal anchor ownership across fallbacks`
