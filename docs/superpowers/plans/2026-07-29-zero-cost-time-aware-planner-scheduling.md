# Zero-Cost Time-Aware Planner Scheduling Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a feature-flagged, zero-cost time-feasibility layer to the manual itinerary planner without changing saved-plan schemas or the existing route-optimization fallback.

**Architecture:** A dependency-free Python scheduler parses daily time windows, builds a bounded travel-time matrix fallback, and solves a fixed-start/fixed-end time-window route with exact label-setting for small inputs and deterministic beam search plus local repair for larger inputs. The existing public optimize-order endpoint accepts an optional schedule envelope, while the Nuxt planner makes at most one cached OSRM Table request per explicit optimization and falls back to the local matrix when unavailable.

**Tech Stack:** Python 3.11 standard library, existing FastAPI/Pydantic, pytest, Nuxt 4, Vue 3, TypeScript, Vitest, existing public OSRM demo endpoint.

## Global Constraints

- Do not add a paid service, API key, container, Python package, or NPM package.
- OSRM Table is called only after an explicit user action, at most once per optimization fingerprint, with no background requests.
- OSRM route validation keeps the existing one initial request plus at most one U-turn retry.
- Do not mutate the database, run migrations, or change saved-plan schemas.
- Do not call an LLM during optimization.
- Keep the existing 20-routable-stop planner limit and fixed first/last stops.
- Preserve stop metadata, manual move controls, save/share behavior, dark mode, and reduced motion.
- Existing `POST /api/itineraries/optimize-order` behavior remains unchanged when the optional `schedule` field is absent.
- If the matrix or scheduler fails, return the best valid fallback with an explicit warning; never return a partial JSON schedule.
- The local solver deadline defaults to 2.0 seconds for at most 20 routable stops.
- Do not deploy production in this plan.

---


## File Structure

- Create `agent/itinerary_schedule.py` for time-window contracts, parsers, fallback matrix creation, deterministic exact/beam scheduling, repair, and diagnostics.
- Create `agent/tests/test_itinerary_schedule.py` for parser, matrix, solver, dominance, optional-drop, and deadline fixtures.
- Modify `agent/public_api.py` and `agent/tests/test_public_itinerary_optimizer_api.py` for the optional schedule envelope.
- Modify `web-nuxt/composables/useRouting.ts` for the bounded OSRM Table URL/parser/fetch seam.
- Modify `web-nuxt/composables/useItineraryOptimization.ts` for one-table caching and schedule payload construction.
- Create `web-nuxt/tests/itinerary-time-schedule.test.ts` for Table parsing, cache budget, payload construction, and placement helpers.
- Modify `web-nuxt/pages/tao-lich-trinh.vue` for ephemeral metadata, computed placements, and feature-flagged scheduling.
- Modify `web-nuxt/nuxt.config.ts` to expose `itineraryScheduleV2` from `NUXT_PUBLIC_ITINERARY_SCHEDULE_V2 === '1'`, defaulting to false.
- Modify `docs/api-contract.md` and create a results document after focused verification passes.

## Scope Decomposition

This plan is Phase 2A and delivers time feasibility to the manual planner as the first independently testable slice. A separate Phase 2B plan will replace the generator's fixed 30-minute travel assumption and add generator-specific meal/rest anchors after Phase 2A records reliable parser, matrix, and latency evidence. Phases 3-6 remain separate specs/plans and are not implemented here.

---

### Task 1: Time Contracts, Parsing, and Local Matrix Fallback

**Files:**
- Create: `agent/itinerary_schedule.py`
- Create: `agent/tests/test_itinerary_schedule.py`

**Interfaces:**
- Consumes: existing `RouteStop`, `Coordinates`, `haversine_km()`, and `project_onto_corridor()` from `agent/itinerary_optimizer.py`.
- Produces: `TimeWindow`, `ScheduleStop`, `TravelMatrix`, `ScheduleOptions`, `SchedulePlacement`, `SkippedStop`, `ScheduleResult`, `NoFeasibleScheduleError`, `parse_time_range()`, `parse_opening_hours()`, `infer_visit_minutes()`, and `build_fallback_matrix()`.

- [ ] **Step 1: Write failing parser and contract tests**

```python
from itinerary_schedule import (
    ScheduleStop,
    TimeWindow,
    build_fallback_matrix,
    infer_visit_minutes,
    parse_opening_hours,
    parse_time_range,
)


def test_parse_time_range_accepts_vietnamese_hour_forms():
    assert parse_time_range("7h30 - 17h") == TimeWindow(450, 1020)
    assert parse_time_range("08:00-11:30") == TimeWindow(480, 690)


def test_parse_opening_hours_returns_windows_and_nonfatal_warning():
    windows, warnings = parse_opening_hours("T2-T6: 07:30-11:30, 13:00-17:00")
    assert windows == (TimeWindow(450, 690), TimeWindow(780, 1020))
    assert "weekday-specific-hours-ignored" in warnings


def test_invalid_hours_are_unknown_not_open_all_day():
    windows, warnings = parse_opening_hours("liên hệ trước")
    assert windows == ()
    assert "opening-hours-unknown" in warnings


def test_visit_duration_uses_explicit_value_then_suggested_text_then_type_default():
    assert infer_visit_minutes("attraction", 75, None) == 75
    assert infer_visit_minutes("attraction", None, "1 giờ 30 phút") == 90
    assert infer_visit_minutes("attraction", None, None) == 90


def test_fallback_matrix_is_zero_diagonal_and_mode_aware():
    stops = [
        ScheduleStop("a", (10.0, 106.0), 0),
        ScheduleStop("b", (10.0, 106.1), 30),
    ]
    matrix = build_fallback_matrix(stops, "driving")
    assert matrix.source == "haversine-fallback"
    assert matrix.duration_minutes[0][0] == 0.0
    assert matrix.duration_minutes[0][1] > 0
```

- [ ] **Step 2: Run tests and verify the module is missing**

```powershell
python -m pytest agent/tests/test_itinerary_schedule.py -q
```

Expected: collection fails because `itinerary_schedule` does not exist.

- [ ] **Step 3: Implement validated immutable contracts and parsers**

Use frozen dataclasses. `TimeWindow` enforces `0 <= start_minute <= end_minute <= 1440`. `ScheduleStop` validates a non-empty ID, finite coordinates, and `0 <= visit_minutes <= 720`. `TravelMatrix` validates a square matrix containing only `None` or finite non-negative values and requires a zero diagonal. `ScheduleOptions` defaults to day start 480, day end 1080, exact limit 10, beam width 64, station tolerance 0.02, and deadline 2.0 seconds.

`parse_time_range()` accepts `H:MM-H:MM`, `Hh-Hh`, and `HhMM-HhMM`; unsupported text returns `None`. `parse_opening_hours()` extracts every supported range, strips weekday labels, and emits `weekday-specific-hours-ignored` when a weekday prefix is present. It emits `opening-hours-unknown` when no range can be trusted.

`infer_visit_minutes()` uses explicit minutes first, then parses `suggested_duration` phrases containing hours/minutes, then falls back to the existing type defaults: attraction 90, experience 120, craft village 60, dish 45, product 30, history 60, nature 90, person 30, event 120, economy 30, accommodation 0, and unknown 60.

`build_fallback_matrix()` uses Haversine distances and existing mode speeds: driving 40 km/h, cycling 15 km/h, and foot 5 km/h. It returns a symmetric matrix labeled `haversine-fallback`; directional penalties remain the scheduler's responsibility.

- [ ] **Step 4: Run the parser and matrix tests**

```powershell
python -m pytest agent/tests/test_itinerary_schedule.py -q
```

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit the contracts and fallback**

```powershell
git add -- agent/itinerary_schedule.py agent/tests/test_itinerary_schedule.py
git commit -m "feat: add time-aware itinerary contracts"
```

---

### Task 2: Deterministic Time-Window Solver and Repair

**Files:**
- Modify: `agent/itinerary_schedule.py`
- Modify: `agent/tests/test_itinerary_schedule.py`

**Interfaces:**
- Consumes: Task 1 contracts and directional geometry from `agent/itinerary_optimizer.py`.
- Produces: `schedule_stop_order(stops, matrix, options) -> ScheduleResult` with fixed endpoints, hard windows, deterministic solver selection, skipped-stop reasons, and time diagnostics.

- [ ] **Step 1: Add failing scheduling tests**

```python
import pytest

from itinerary_schedule import (
    NoFeasibleScheduleError,
    ScheduleOptions,
    ScheduleStop,
    SkippedStop,
    TimeWindow,
    TravelMatrix,
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
    assert result.placements[1].start_visit_minute == 480
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
        matrix(["start", "must", "optional", "end"], [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]]),
        ScheduleOptions(day_start_minute=480, day_end_minute=1200),
    )
    assert result.ordered_ids == ("start", "must", "end")
    assert result.skipped == (SkippedStop("optional", "day-window-overflow"),)


def test_beam_solver_is_deterministic_for_twenty_stops():
    middle = [ScheduleStop(f"p{i}", (10.0, 106.0 + i * 0.01), 10) for i in range(1, 19)]
    stops = [ScheduleStop("start", (10.0, 106.0), 0), *reversed(middle), ScheduleStop("end", (10.0, 106.2), 0)]
    values = [[0 if i == j else 2 for j in range(20)] for i in range(20)]
    first = schedule_stop_order(stops, matrix([s.id for s in stops], values), ScheduleOptions(exact_limit=10))
    second = schedule_stop_order(stops, matrix([s.id for s in stops], values), ScheduleOptions(exact_limit=10))
    assert first.ordered_ids == second.ordered_ids
    assert first.solver == "schedule-beam"
```

- [ ] **Step 2: Run the new tests to verify the scheduling branch is red**

```powershell
python -m pytest agent/tests/test_itinerary_schedule.py -q
```

Expected: the new tests fail because `schedule_stop_order()` is not implemented.

- [ ] **Step 3: Implement label-setting, beam search, and repair**

For each transition `source -> target`, reject blocked edges and targets whose corridor station is behind the source by more than `station_tolerance`. Read `duration_minutes[source][target]`; reject `None`. Compute `arrival = finish_source + travel`, `start_visit = max(arrival, window.start)`, and `finish_visit = start_visit + visit_minutes`; accept only when `finish_visit <= window.end` and `finish_visit <= day_end_minute`.

For at most `exact_limit` intermediate stops, keep nondominated labels keyed by `(visited_mask, last_index)`. A label dominates another when it reaches the same last index with no later finish time and no greater travel time. Reconstruct the lowest lexicographic objective path, using original indexes as the final tie-breaker. Above that limit, retain `beam_width` labels ranked by hard feasibility, finish time, travel time, minimum slack, and original-index path.

The first and last stops are fixed and required. After the initial solve, try adjacent swap, single-stop relocate, and two-stop Or-opt candidates. Accept only fully feasible candidates with a better lexicographic objective. If no full route exists, remove optional stops one at a time in descending `(visit_minutes + shortest_incident_travel)` burden, tie-breaking by original index; record `day-window-overflow`. If a required stop remains infeasible, raise `NoFeasibleScheduleError` naming the first blocker.

Return ordered IDs, placements, skipped records, travel minutes, waiting minutes, overtime, minimum slack, geometric distance, backtrack ratio, matrix source, solver, and warnings. Use `time.perf_counter()` for the configurable deadline and return only a complete feasible label.

- [ ] **Step 4: Run scheduling and directional regression tests**

```powershell
python -m pytest agent/tests/test_itinerary_schedule.py agent/tests/test_itinerary_optimizer.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit the solver**

```powershell
git add -- agent/itinerary_schedule.py agent/tests/test_itinerary_schedule.py
git commit -m "feat: schedule itinerary stops within time windows"
```

---

### Task 3: Optional Schedule Envelope in the Public API

**Files:**
- Modify: `agent/public_api.py`
- Modify: `agent/tests/test_public_itinerary_optimizer_api.py`

**Interfaces:**
- Consumes: `schedule_stop_order()`, `ScheduleStop`, `ScheduleOptions`, `TravelMatrix`, and `build_fallback_matrix()`.
- Produces: backward-compatible optional `schedule` request and response fields on `POST /api/itineraries/optimize-order`.

- [ ] **Step 1: Add failing API contract tests**

```python
def schedule_payload():
    body = payload()
    body["schedule"] = {
        "day_start_minute": 480,
        "day_end_minute": 1080,
        "mode": "driving",
        "stops": [
            {"id": "start", "visit_minutes": 0, "required": True},
            {"id": "late", "visit_minutes": 30, "opening_hours": "10:00-17:00", "required": True},
            {"id": "early", "visit_minutes": 30, "opening_hours": "08:00-09:30", "required": True},
            {"id": "end", "visit_minutes": 0, "required": True},
        ],
        "duration_matrix_minutes": [
            [0, 20, 10, 40], [20, 0, 20, 20], [10, 20, 0, 30], [40, 20, 30, 0],
        ],
    }
    return body


def test_schedule_envelope_returns_placements_and_uses_matrix(client):
    response = client.post("/api/itineraries/optimize-order", json=schedule_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["ordered_ids"] == ["start", "early", "late", "end"]
    assert body["schedule"]["matrix_source"] == "request"
    assert body["schedule"]["placements"][1]["start_visit_minute"] == 480


def test_without_schedule_keeps_existing_response_shape(client):
    response = client.post("/api/itineraries/optimize-order", json=payload())
    assert response.status_code == 200
    assert "schedule" not in response.json()


@pytest.mark.parametrize("bad_schedule", [
    {"day_start_minute": 900, "day_end_minute": 480, "stops": []},
    {"day_start_minute": 480, "day_end_minute": 1080, "stops": [{"id": "missing"}]},
    {"day_start_minute": 480, "day_end_minute": 1080, "stops": [], "duration_matrix_minutes": [[0, 1]]},
])
def test_schedule_validation_returns_422(client, bad_schedule):
    body = payload()
    body["schedule"] = bad_schedule
    assert client.post("/api/itineraries/optimize-order", json=body).status_code == 422
```

- [ ] **Step 2: Run API tests and verify the new envelope is absent**

```powershell
python -m pytest agent/tests/test_public_itinerary_optimizer_api.py -q
```

Expected: the schedule success test fails because the endpoint ignores `schedule` and the nested model is not registered.

- [ ] **Step 3: Add models and preserve the order-only branch**

Add `ItineraryScheduleStopIn` with `id`, optional `visit_minutes` (`0..720`), optional `opening_hours` (`max_length=200`), optional `requested_time` (`max_length=80`), and `required`. Add `ItineraryScheduleIn` with `day_start_minute`, `day_end_minute`, `mode`, exact schedule stop IDs, and an optional square `duration_matrix_minutes` containing finite non-negative numbers or `null`.

The outer model validator must require schedule IDs to be an exact permutation of `stops`, require the first and last schedule stops, reject unknown IDs, reject non-square matrices, and reject a day end not later than the day start. When no schedule field is supplied, do not construct a matrix or call the scheduler.

When schedule is present, build `ScheduleStop` values from the request, use the supplied matrix with `source="request"`, or call `build_fallback_matrix()` with the selected mode. Invoke `schedule_stop_order()` in `asyncio.to_thread`. Map `NoFeasibleScheduleError` to HTTP 409 and return a Vietnamese detail naming the blocking stop. Compute `distance_before_km` from the input order; use the scheduler's geometric distance and backtrack ratio for the final order. Preserve the existing top-level field names and add `schedule` only for the schedule branch with placements, skipped reasons, matrix source, and time diagnostics.

- [ ] **Step 4: Run focused API and generator regression tests**

```powershell
python -m pytest agent/tests/test_public_itinerary_optimizer_api.py agent/tests/test_itinerary_schedule.py agent/tests/test_cov_itinerary_gen.py -q
```

Expected: all selected backend tests pass.

- [ ] **Step 5: Commit the API adapter**

```powershell
git add -- agent/public_api.py agent/tests/test_public_itinerary_optimizer_api.py
git commit -m "feat: expose optional time-aware itinerary scheduling"
```

---

### Task 4: Bounded OSRM Table Adapter and Cache

**Files:**
- Modify: `web-nuxt/composables/useRouting.ts`
- Modify: `web-nuxt/composables/useItineraryOptimization.ts`
- Create: `web-nuxt/tests/itinerary-time-schedule.test.ts`

**Interfaces:**
- Consumes: existing `TransportMode`, coordinates, average speeds, and the current `$fetch` seam.
- Produces: `RouteTableResult`, `buildTableUrl()`, `parseTableResponse()`, `fetchRouteTable()`, `routeTableCacheKey()`, and `getCachedRouteTable()`.

- [ ] **Step 1: Write failing Table URL/parser/cache tests**

```typescript
import {
  buildTableUrl,
  parseTableResponse,
} from '../composables/useRouting'
import {
  getCachedRouteTable,
  routeTableCacheKey,
} from '../composables/useItineraryOptimization'

it('requests all-pairs distance and duration annotations', () => {
  expect(buildTableUrl([[10, 106], [10.2, 106.4]], 'driving')).toBe(
    'https://router.project-osrm.org/table/v1/car/106,10;106.4,10.2?annotations=distance,duration',
  )
})

it('converts distances to mode durations consistently with route parsing', () => {
  const table = parseTableResponse({
    code: 'Ok',
    distances: [[0, 40000], [40000, 0]],
    durations: [[0, 3600], [3600, 0]],
  }, 'cycling')
  expect(table?.distanceKm[0][1]).toBe(40)
  expect(table?.durationMinutes[0][1]).toBe(160)
  expect(table?.source).toBe('osrm-table')
})

it('rejects incomplete or non-finite tables', () => {
  expect(parseTableResponse({ code: 'Ok', distances: [[0, 1], [1]], durations: [[0, 1], [1, 0]] }, 'driving')).toBeNull()
  expect(parseTableResponse({ code: 'NoRoute', distances: [], durations: [] }, 'driving')).toBeNull()
})

it('calls the injected table fetcher once for a cache key', async () => {
  let calls = 0
  const key = routeTableCacheKey([[10, 106], [10.2, 106.4]], 'driving')
  const fetcher = async () => {
    calls += 1
    return { distanceKm: [[0, 1], [1, 0]], durationMinutes: [[0, 2], [2, 0]], source: 'osrm-table' as const }
  }
  await getCachedRouteTable(key, fetcher)
  await getCachedRouteTable(key, fetcher)
  expect(calls).toBe(1)
})
```

- [ ] **Step 2: Run the new frontend test to verify missing exports**

```powershell
cd web-nuxt
npm test -- tests/itinerary-time-schedule.test.ts
```

Expected: import/compile failure because the Table functions do not exist.

- [ ] **Step 3: Implement one-request Table parsing and TTL cache**

`buildTableUrl()` uses the existing OSRM base and `table/v1/car`, encodes `[lat, lng]` as `lng,lat`, and requests `annotations=distance,duration`. `parseTableResponse()` validates `code === "Ok"`, square finite non-negative distances, and matching dimensions. It converts distance to mode duration using the existing average speeds for cycling and foot; driving uses OSRM duration when finite and falls back to distance/speed for a missing duration cell.

`fetchRouteTable()` performs exactly one `$fetch` with no retry and returns `null` on error. `routeTableCacheKey()` rounds coordinates to five decimals and includes transport mode. `getCachedRouteTable()` stores at most 16 entries with a 15-minute TTL and never shares a rejected request. The optimization composable reuses one table for both the first attempt and U-turn retry.

- [ ] **Step 4: Extend request construction without changing the old payload**

Add an optional schedule argument to `requestOptimizedOrder()`. When absent, serialize the exact current body. When present, send day bounds, mode, schedule metadata keyed by stable planner IDs, and the cached `duration_matrix_minutes`; reuse the same request object for the retry. Extend the response solver union with `schedule-exact` and `schedule-beam`.

- [ ] **Step 5: Run focused frontend tests and typecheck**

```powershell
npm test -- tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts tests/itinerary-time-schedule.test.ts
npm run typecheck
```

Expected: all focused tests pass and typecheck exits 0.

- [ ] **Step 6: Commit the Table adapter and cache**

```powershell
git add -- web-nuxt/composables/useRouting.ts web-nuxt/composables/useItineraryOptimization.ts web-nuxt/tests/itinerary-time-schedule.test.ts
git commit -m "feat: add cached zero-cost route time matrix"
```

---

### Task 5: Feature-Flagged Planner Integration Without Saved-Schema Changes

**Files:**
- Modify: `web-nuxt/pages/tao-lich-trinh.vue`
- Modify: `web-nuxt/nuxt.config.ts` only when the existing runtime-config convention supports it
- Modify: `web-nuxt/tests/itinerary-time-schedule.test.ts`
- Modify: `web-nuxt/tests/smoke.test.ts`

**Interfaces:**
- Consumes: Task 3 schedule envelope and Task 4 Table/cache helpers.
- Produces: `formatScheduledInterval()`, `applySchedulePlacement()`, explicit planner scheduling, ephemeral placement diagnostics, metadata-preserving fallback, and no extra saved-plan fields.

- [ ] **Step 1: Add failing pure helper tests**

```typescript
it('keeps manual time and notes while exposing computed placement separately', () => {
  const stop = { id: 'a', type: 'attraction', time: '08:00', notes: 'đã đặt trước' }
  const placement = { start_visit_minute: 510, end_visit_minute: 600 }
  const result = applySchedulePlacement(stop, placement)
  expect(result.stop.time).toBe('08:00')
  expect(result.stop.notes).toBe('đã đặt trước')
  expect(result.scheduledTime).toBe('08:30-10:00')
})

it('does not add ephemeral scheduling fields to saved stop objects', () => {
  const stop = { id: 'a', name: 'A', type: 'attraction', coords: [10, 106], time: '', notes: '' }
  const serialized = JSON.parse(JSON.stringify(stop))
  expect(serialized).toEqual(stop)
  expect(serialized.scheduledTime).toBeUndefined()
})
```

- [ ] **Step 2: Run the helper tests and verify the seams are missing**

```powershell
cd web-nuxt
npm test -- tests/itinerary-time-schedule.test.ts
```

Expected: the new helper imports fail.

- [ ] **Step 3: Add ephemeral metadata and a default-off flag**

Use `WeakMap<object, PlannerScheduleMetadata>` instead of adding persisted fields to `PlanStop`. On `addStop()`, derive visit minutes from `entity.attributes.suggested_duration` or the existing type defaults and retain raw `entity.attributes.hours`. Loaded saved plans use type defaults and emit `opening-hours-unknown`. A non-empty existing `time` string is sent as `requested_time` only when it matches the supported range syntax; invalid text remains unchanged and produces a warning.

Add `const itineraryScheduleV2 = process.env.NUXT_PUBLIC_ITINERARY_SCHEDULE_V2 === '1'` beside the existing environment-derived constants and expose it under `runtimeConfig.public`. The existing route-only optimizer remains unchanged when the flag is false.

- [ ] **Step 4: Integrate one Table call and the schedule-aware request**

In `optimizePlanRoute()`, keep `suspendAutoRoute`. When enabled, fetch one cached Table for `currentRoutableStops`, build the schedule envelope, call the existing bounded two-attempt optimizer, and reuse the same matrix for the retry. If Table returns `null`, omit the matrix so the server builds its local fallback. Never call Table when fewer than three routable stops exist or when first/last planner slots lack coordinates.

Before reordering, store response placements in a `WeakMap` keyed by original stop objects. Render computed intervals as secondary status text; do not overwrite `time`, `notes`, IDs, coordinates, or saved-plan fields. Keep missing-coordinate slots and manual controls unchanged. Display matrix fallback, unknown-hours, skipped-optional, overtime, and unresolved-U-turn warnings honestly.

- [ ] **Step 5: Add planner source-level regression assertions**

Extend `tests/smoke.test.ts` to require the default-off flag, Table cache helper, `suspendAutoRoute`, and WeakMap placement storage. Assert that the schedule path is skipped when the flag is false and that `_doSave()` still serializes only the original `PlanStop` fields.

- [ ] **Step 6: Run frontend focused tests, typecheck, and build**

```powershell
npm test -- tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts tests/itinerary-time-schedule.test.ts tests/smoke.test.ts
npm run typecheck
npm run build
```

Expected: selected tests pass, typecheck exits 0, and build exits 0. Existing Nuxt chunk/sourcemap warnings may remain documented pre-existing warnings.

- [ ] **Step 7: Commit the planner integration**

```powershell
git add -- web-nuxt/pages/tao-lich-trinh.vue web-nuxt/nuxt.config.ts web-nuxt/tests/itinerary-time-schedule.test.ts web-nuxt/tests/smoke.test.ts
git commit -m "feat: add feature-flagged time-aware planner scheduling"
```

---

### Task 6: Contract Documentation and Regression Closure

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md`
- Create: `docs/superpowers/results/2026-07-29-zero-cost-time-aware-planner-scheduling-evidence.md`

**Interfaces:**
- Consumes: all Task 1-5 interfaces and verification output.
- Produces: documented optional API fields, explicit phase status, and honest local evidence.

- [ ] **Step 1: Verify documentation does not yet claim the new contract**

```powershell
rg -n "duration_matrix_minutes|itineraryScheduleV2" docs/api-contract.md
```

Expected: no matches before documentation is updated.

- [ ] **Step 2: Document the optional envelope and feature flag**

Add request fields, response placement shape, one-Table/one-retry budget, fallback behavior, and default-off flag to `docs/api-contract.md`. Keep the existing order-only example valid. Mark only Phase 2A complete in the roadmap; do not mark the entire six-phase roadmap done.

- [ ] **Step 3: Run the complete Phase 2A verification matrix**

```powershell
python -m pytest agent/tests/test_itinerary_schedule.py agent/tests/test_public_itinerary_optimizer_api.py agent/tests/test_itinerary_optimizer.py agent/tests/test_cov_itinerary_gen.py -q
cd web-nuxt
npm test -- tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts tests/itinerary-time-schedule.test.ts tests/smoke.test.ts
npm run typecheck
npm run build
```

Expected: all selected tests pass, typecheck/build exit 0, and pre-existing warnings are recorded rather than hidden.

- [ ] **Step 4: Write evidence and inspect scope**

Record exact pass counts, the one-request cache assertion, fallback tests, build/typecheck status, and any full-suite timeout honestly. Run:

```powershell
git diff --check
git status --short
git log -8 --oneline
```

Expected: no whitespace errors; only intentional Phase 2A files are changed; unrelated user changes remain untouched.

- [ ] **Step 5: Commit documentation closure**

```powershell
git add -- docs/api-contract.md docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md docs/superpowers/results/2026-07-29-zero-cost-time-aware-planner-scheduling-evidence.md
git commit -m "docs: close time-aware planner scheduling phase"
```

- [ ] **Step 6: Run fresh post-commit focused verification**

Repeat the backend focused command, frontend focused command, typecheck, and `git diff --check` on the final commit. Do not claim the full repository backend suite passed unless it completes with exit 0.

## Self-Review Checklist

- Every Phase 2A roadmap requirement maps to a bounded task; generator adoption and Phases 3-6 remain separate plans.
- The old order-only API path, saved-plan JSON, manual controls, and U-turn retry remain compatible.
- All new types and function names are defined before later tasks consume them.
- The OSRM budget is explicit: at most one Table request, one initial route, one retry, and zero background requests.
- The only matrix fallback is local Haversine calculation; no paid service or dependency is introduced.
- Parser warnings, impossible required stops, optional drops, deadlines, stale cache behavior, and feature-flag-off behavior have explicit tests.
