# Phase 2B Task 1 — Time-Aware Generator Adapter

## Scope

- Implemented only Task 1 in `agent/itinerary_gen.py`.
- Added focused behavior coverage in `agent/tests/test_itinerary_generator_schedule.py`.
- Did not modify `agent/tests/test_cov_itinerary_gen.py`; no compatibility assertion required a change.
- No dependencies, network/OSRM calls, LLM calls, migrations, public optimizer endpoint, saved schema, or Task 2 meal/rest anchor behavior were changed.

## Root cause

`generate_itinerary()` always delegated each selected day to `_build_day_stops()`, whose timeline advances every stop by the type visit default plus a fixed `30` minutes. The existing local `itinerary_schedule` solver and Haversine matrix were not connected to the generator, so coordinate-rich candidates could not use their actual leg durations, opening windows, optional-middle-stop behavior, or schedule diagnostics.

## TDD evidence

### RED

New focused test command before production edits:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py -q
```

The initial run exited 1 with `4 failed`. The failures were behavior failures against the existing generator: coordinate fixtures still used the legacy `10:00` time instead of the expected coordinate-aware `08:15`, and fallback days had no `schedule` diagnostics (`KeyError: 'schedule'`). One infeasibility test was then adjusted to avoid a test-only missing-import/setup failure; the rerun still exited 1 with the same intended missing-adapter behavior failures.

After the adapter was present, a second TDD cycle added invalid-duration coverage. Its RED run exited 1 with the real scheduler validation error (`ValueError: Thời lượng tham quan phải nằm trong khoảng 0-720 phút`) escaping the generator, proving the fallback guard was still missing.

### GREEN

- Focused adapter suite after the minimal implementation: `6 passed`.
- Required Task 1 matrix after the final test additions:

```text
python -m pytest agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py -q
```

Result: exit 0, `151 passed`.

## Implementation

### Coordinate and candidate adaptation

- Added finite coordinate normalization for `[lat, lng]` sequences and common `lat`/`lng`/`latitude`/`longitude` mappings.
- `_candidate_coordinates()` prefers the selected entity coordinates and then falls back to its parent place coordinates.
- `_candidate_schedule_stop()` adapts each candidate to `ScheduleStop`, parses `hours`/`open_hours` through `parse_opening_hours()`, and infers visit duration from explicit `visit_minutes`, `duration_minutes`, `suggested_duration`/`duration`, then existing type defaults.

### Scheduler path

- `_build_day_schedule()` builds a local `build_fallback_matrix(stops, "driving")` matrix and invokes `schedule_stop_order()` with `ScheduleOptions(day_start_minute=480, day_end_minute=1080)`.
- First and last selected candidates are `required=True`; middle candidates are optional, allowing the scheduler to drop overfull middle stops while preserving endpoint order.
- Scheduler placements map back to the existing `{"time", "entity", "note"}` stop shape; placement start times are formatted as the existing `HH:MM` strings.
- Per-day diagnostics now carry exactly the requested keys: `solver`, `matrix_source`, `total_travel_minutes`, `waiting_minutes`, `overtime_minutes`, `minimum_slack_minutes`, `backtrack_ratio`, `skipped`, and `warnings`.

### Deterministic fallback

- Any missing usable coordinate returns the unchanged `_build_day_stops()` timeline with `coordinates-missing`.
- `NoFeasibleScheduleError`, scheduler validation `ValueError`, and invalid adapted stop data return the unchanged legacy timeline with `schedule-fallback`.
- Fallback diagnostics never expose partial scheduler placements; `skipped` is an empty list for fallback days.
- Existing automatic meal insertion remains on the legacy fallback path. Coordinate-aware Task 1 scheduling does not add new meal/rest anchors; those remain Task 2 scope.

## Verification and self-review

- `python -m compileall -q agent/itinerary_gen.py agent/tests/test_itinerary_generator_schedule.py` exited 0.
- `git diff --check` and staged diff checks exited 0.
- The existing generator coverage and all local scheduler tests stayed green (`151 passed` total in the required matrix).
- The generator’s public arguments and existing top-level return keys remain unchanged; `schedule` is an additive per-day field.
- No production scheduler code was changed, and no external service is called by the adapter.
- Commit hook reported `run_hard: sạch (hard=0, ratchet không tăng)`.

## Commit

- `8076dc52` — `feat: adopt time-aware scheduler in itinerary generator`

## Concerns

- None for Task 1. Task 2 remains responsible for configurable meal/rest anchors; no anchor behavior was inferred or added here.
