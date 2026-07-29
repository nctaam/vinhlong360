# Zero-Cost Directional Route Optimizer Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add a deterministic, zero-paid-service optimizer that reorders 2-20 planner stops from a fixed start to a fixed destination, minimizes geometric detour, prevents directional backtracking, and detects OSRM U-turn maneuvers.

**Architecture:** A dependency-free Python module owns corridor projection and the exact/beam solver. public_api.py exposes a narrow POST adapter. Nuxt keeps planner-specific merging and one bounded OSRM retry in a focused composable, while useRouting.ts remains the only OSRM parser.

**Tech Stack:** Python 3.11 standard library, existing FastAPI/Pydantic, pytest, Nuxt 4, Vue 3, TypeScript, Vitest, existing public OSRM route endpoint.

## Global Constraints

- Do not add a paid service, API key, container, Python package, or NPM package.
- Do not mutate the database, run migrations, or change saved-plan schemas.
- Do not call an LLM during optimization.
- Keep the existing 20-stop planner limit and fixed first/last stops.
- Use OSRM only for the final ordered route, with at most one retry after detecting a U-turn.
- Preserve stop metadata, manual move controls, save/share behavior, dark mode, and reduced motion.
- Do not deploy to production.
- Preserve unrelated worktree changes and stage only files owned by each task.

---

## File Structure

- Create agent/itinerary_optimizer.py for geometry, validation, solver portfolio, diagnostics, and domain errors.
- Create agent/tests/test_itinerary_optimizer.py for direct optimizer behavior.
- Modify agent/public_api.py and create agent/tests/test_public_itinerary_optimizer_api.py for the HTTP adapter.
- Modify web-nuxt/composables/useRouting.ts and create web-nuxt/tests/itinerary-routing.test.ts for OSRM step parsing.
- Create web-nuxt/composables/useItineraryOptimization.ts and web-nuxt/tests/itinerary-optimization.test.ts for planner-specific pure logic.
- Modify web-nuxt/pages/tao-lich-trinh.vue for the user-triggered flow and route-leg alignment.
- Close docs/superpowers/specs/2026-07-29-zero-cost-directional-route-optimizer-design.md only after verification.

---

### Task 1: Corridor Geometry and Input Contracts

**Files:**
- Create: agent/tests/test_itinerary_optimizer.py
- Create: agent/itinerary_optimizer.py

**Interfaces:**
- Consumes: coordinates in [latitude, longitude] order.
- Produces: RouteStop, OptimizeOptions, OptimizeResult, Projection, NoFeasibleRouteError, haversine_km(), project_onto_corridor(), and a minimal optimize_stop_order().

- [ ] **Step 1: Write failing geometry and validation tests**

~~~python
import math

import pytest

from itinerary_optimizer import (
    NoFeasibleRouteError,
    RouteStop,
    haversine_km,
    optimize_stop_order,
    project_onto_corridor,
)


def stop(stop_id: str, lat: float, lng: float) -> RouteStop:
    return RouteStop(stop_id, (lat, lng))


def test_projection_reports_station_and_lateral_distance():
    projection = project_onto_corridor(
        (10.0, 106.0), (10.0, 107.0), (10.1, 106.25),
    )
    assert projection.station == pytest.approx(0.25, abs=0.002)
    assert 11.0 < projection.lateral_km < 11.2


def test_haversine_is_zero_for_identical_coordinates():
    assert haversine_km((10.25, 105.97), (10.25, 105.97)) == 0.0


def test_optimizer_rejects_duplicate_ids():
    with pytest.raises(ValueError):
        optimize_stop_order([
            stop("same", 10.0, 106.0),
            stop("same", 10.0, 106.5),
        ])


def test_optimizer_rejects_degenerate_corridor():
    with pytest.raises(NoFeasibleRouteError, match="không xác định được hướng"):
        optimize_stop_order([
            stop("start", 10.0, 106.0),
            stop("end", 10.00001, 106.00001),
        ])


def test_route_stop_rejects_non_finite_coordinates():
    with pytest.raises(ValueError):
        RouteStop("bad", (math.nan, 106.0))
~~~

- [ ] **Step 2: Run and verify RED**

Run: python -m pytest agent/tests/test_itinerary_optimizer.py -q

Expected: collection fails because itinerary_optimizer does not exist.

- [ ] **Step 3: Implement minimal geometry contracts**

Use frozen dataclasses with the exact spec fields. RouteStop.__post_init__ validates ID, finite values, and coordinate ranges. project_onto_corridor() uses a local equirectangular projection and rejects corridors shorter than 20 meters.

The temporary optimize_stop_order() validates 2-20 unique stops and returns diagnostics for a two-stop route. For intermediate stops it raises NoFeasibleRouteError("Chưa có bộ giải cho các điểm trung gian"); Task 2 replaces this branch only after its tests fail.

- [ ] **Step 4: Run and verify GREEN**

Run: python -m pytest agent/tests/test_itinerary_optimizer.py -q

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit**

~~~powershell
git add -- agent/itinerary_optimizer.py agent/tests/test_itinerary_optimizer.py
git commit -m "feat: add directional route geometry contracts"
~~~

---

### Task 2: Exact, Beam, and Local Search Solvers

**Files:**
- Modify: agent/tests/test_itinerary_optimizer.py
- Modify: agent/itinerary_optimizer.py

**Interfaces:**
- Consumes: Task 1 contracts.
- Produces: complete optimize_stop_order() diagnostics for 2-20 stops.

- [ ] **Step 1: Add failing solver tests**

~~~python
def test_exact_solver_restores_forward_order_and_preserves_endpoints():
    stops = [
        stop("start", 10.0, 106.0),
        stop("late", 10.0, 106.7),
        stop("early", 10.0, 106.3),
        stop("end", 10.0, 107.0),
    ]
    result = optimize_stop_order(stops)
    assert result.ordered_ids == ("start", "early", "late", "end")
    assert result.solver == "exact-dp"
    assert result.backtrack_ratio == pytest.approx(0.0, abs=1e-9)
    assert result.distance_after_km < result.distance_before_km


def test_blocked_edge_is_never_used():
    stops = [
        stop("start", 10.0, 106.0),
        stop("north", 10.03, 106.5),
        stop("south", 9.97, 106.5),
        stop("end", 10.0, 107.0),
    ]
    options = OptimizeOptions(
        blocked_edges=frozenset({("start", "north")}),
    )
    result = optimize_stop_order(stops, options)
    assert ("start", "north") not in set(
        zip(result.ordered_ids, result.ordered_ids[1:]),
    )


def test_strict_solver_reports_no_route_instead_of_backtracking():
    stops = [
        stop("start", 10.0, 106.0),
        stop("middle", 10.0, 106.5),
        stop("end", 10.0, 107.0),
    ]
    options = OptimizeOptions(
        blocked_edges=frozenset({("start", "middle")}),
    )
    with pytest.raises(NoFeasibleRouteError, match="Không tìm thấy thứ tự"):
        optimize_stop_order(stops, options)


def test_duplicate_coordinates_keep_input_order():
    stops = [
        stop("start", 10.0, 106.0),
        stop("first", 10.0, 106.5),
        stop("second", 10.0, 106.5),
        stop("end", 10.0, 107.0),
    ]
    assert optimize_stop_order(stops).ordered_ids == (
        "start", "first", "second", "end",
    )


def test_beam_solver_is_deterministic_for_twenty_stops():
    middle = [
        stop(
            f"p{i:02d}",
            10.0 + ((i % 3) - 1) * 0.002,
            106.0 + i * 0.04,
        )
        for i in range(1, 19)
    ]
    stops = [
        stop("start", 10.0, 106.0),
        *reversed(middle),
        stop("end", 10.0, 106.8),
    ]
    first = optimize_stop_order(stops)
    second = optimize_stop_order(stops)
    assert first.ordered_ids == second.ordered_ids
    assert first.solver == "beam-search"
    assert first.backtrack_ratio == pytest.approx(0.0, abs=1e-9)
~~~

- [ ] **Step 2: Run and verify RED**

Run: python -m pytest agent/tests/test_itinerary_optimizer.py -q

Expected: intermediate-stop tests fail with the temporary solver error.

- [ ] **Step 3: Implement the solver portfolio**

Prepare every stop with its original index and projection. An edge is allowed only when it is not blocked and, in strict mode, target.station + tolerance >= source.station.

Implement:

- Held-Karp bitmask DP for at most exact_limit intermediate stops.
- Deterministic beam search above that limit, ranked by cost plus straight-line distance to destination, then original-index path.
- Stable ties by original input indexes.
- Constrained adjacent swap, relocate, and two-stop Or-opt passes; accept only lower-cost fully feasible paths.
- Edge cost from Haversine distance, backward-progress penalty, and lateral escape.
- Independent distance_before_km, distance_after_km, and backtrack_ratio calculations.
- NoFeasibleRouteError when all required stops cannot be visited.

- [ ] **Step 4: Run and verify GREEN**

Run: python -m pytest agent/tests/test_itinerary_optimizer.py -q

Expected: all tests pass.

- [ ] **Step 5: Run a performance smoke**

~~~powershell
@'
from time import perf_counter
from itinerary_optimizer import RouteStop, optimize_stop_order
stops = [RouteStop("start", (10.0, 106.0))]
stops += [
    RouteStop(f"p{i}", (10.0 + (i % 3) * 0.001, 106.0 + i * 0.04))
    for i in range(1, 19)
]
stops += [RouteStop("end", (10.0, 106.8))]
started = perf_counter()
result = optimize_stop_order(stops)
print(result.solver, round((perf_counter() - started) * 1000, 2))
print(result.backtrack_ratio)
'@ | python -
~~~

Expected: beam-search, less than 1000 ms on the development machine, and zero backtrack.

- [ ] **Step 6: Commit**

~~~powershell
git add -- agent/itinerary_optimizer.py agent/tests/test_itinerary_optimizer.py
git commit -m "feat: optimize stops along a forward corridor"
~~~

---

### Task 3: Public Optimize-Order API

**Files:**
- Create: agent/tests/test_public_itinerary_optimizer_api.py
- Modify: agent/public_api.py

**Interfaces:**
- Consumes: Task 2 optimizer.
- Produces: POST /api/itineraries/optimize-order.

- [ ] **Step 1: Write failing HTTP boundary tests**

~~~python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from public_api import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def payload():
    return {
        "stops": [
            {"id": "start", "coordinates": [10.0, 106.0]},
            {"id": "late", "coordinates": [10.0, 106.7]},
            {"id": "early", "coordinates": [10.0, 106.3]},
            {"id": "end", "coordinates": [10.0, 107.0]},
        ],
        "strict_direction": True,
        "blocked_edges": [],
    }


def test_optimize_order_returns_forward_order_and_diagnostics(client):
    response = client.post("/api/itineraries/optimize-order", json=payload())
    assert response.status_code == 200
    body = response.json()
    assert body["ordered_ids"] == ["start", "early", "late", "end"]
    assert body["solver"] == "exact-dp"
    assert body["saved_distance_km"] > 0


def test_optimize_order_rejects_duplicate_ids(client):
    body = payload()
    body["stops"].append(body["stops"][0])
    assert client.post(
        "/api/itineraries/optimize-order", json=body,
    ).status_code == 422


def test_optimize_order_rejects_unknown_blocked_edge(client):
    body = payload()
    body["blocked_edges"] = [["missing", "end"]]
    assert client.post(
        "/api/itineraries/optimize-order", json=body,
    ).status_code == 422


def test_optimize_order_maps_no_route_to_409(client):
    body = payload()
    body["blocked_edges"] = [["start", "early"]]
    response = client.post(
        "/api/itineraries/optimize-order", json=body,
    )
    assert response.status_code == 409
    assert "Không tìm thấy thứ tự" in response.json()["detail"]
~~~

Also add parameterized 422 cases for one stop, 21 stops, latitude 91, longitude 181, and non-finite JSON values rejected by the client/parser.

- [ ] **Step 2: Run and verify RED**

Run: python -m pytest agent/tests/test_public_itinerary_optimizer_api.py -q

Expected: POST is not registered.

- [ ] **Step 3: Implement models and endpoint**

Import field_validator and model_validator. Add ItineraryOptimizeStopIn and ItineraryOptimizeIn with 2-20 stops, finite coordinate validation, unique IDs, and blocked-edge membership validation.

Register the static POST before /itineraries/{itin_id}. Convert request stops to RouteStop, invoke optimize_stop_order(), and return ordered_ids plus distance_before_km, distance_after_km, saved_distance_km, backtrack_ratio, solver, and warnings. Catch only NoFeasibleRouteError and return _err(409, str(exc)).

- [ ] **Step 4: Run focused backend tests**

Run: python -m pytest agent/tests/test_public_itinerary_optimizer_api.py agent/tests/test_itinerary_optimizer.py -q

Expected: all tests pass.

- [ ] **Step 5: Commit**

~~~powershell
git add -- agent/public_api.py agent/tests/test_public_itinerary_optimizer_api.py
git commit -m "feat: expose directional itinerary optimization API"
~~~

---

### Task 4: OSRM U-Turn Parsing

**Files:**
- Create: web-nuxt/tests/itinerary-routing.test.ts
- Modify: web-nuxt/composables/useRouting.ts

**Interfaces:**
- Consumes: existing OSRM response.
- Produces: buildRouteUrl(), parseRouteResponse(), and RouteLeg.hasUturn.

- [ ] **Step 1: Write failing pure tests**

~~~typescript
// @vitest-environment node

import { describe, expect, it } from 'vitest'
import {
  buildRouteUrl,
  parseRouteResponse,
} from '../composables/useRouting'

describe('itinerary OSRM routing', () => {
  it('requests route steps and continue-straight', () => {
    expect(buildRouteUrl([[10, 106], [10.5, 106.5]])).toBe(
      'https://router.project-osrm.org/route/v1/car/' +
      '106,10;106.5,10.5?overview=full&geometries=geojson&' +
      'steps=true&continue_straight=true',
    )
  })

  it('marks only the leg containing a uturn maneuver', () => {
    const result = parseRouteResponse({
      code: 'Ok',
      routes: [{
        distance: 3000,
        legs: [
          { distance: 1000, steps: [{ maneuver: { type: 'turn' } }] },
          { distance: 2000, steps: [{ maneuver: { type: 'uturn' } }] },
        ],
        geometry: { coordinates: [[106, 10], [106.5, 10.5]] },
      }],
    }, 'driving')
    expect(result?.legs.map(leg => leg.hasUturn)).toEqual([false, true])
  })

  it('rejects empty route responses', () => {
    expect(parseRouteResponse(
      { code: 'NoRoute', routes: [] },
      'driving',
    )).toBeNull()
  })
})
~~~

- [ ] **Step 2: Run and verify RED**

Run from web-nuxt: npm test -- tests/itinerary-routing.test.ts

Expected: missing exports.

- [ ] **Step 3: Implement pure URL/parser boundaries**

Add hasUturn to RouteLeg. buildRouteUrl() emits steps=true and continue_straight=true. parseRouteResponse() preserves existing distance-based mode durations, converts geometry to [lat, lng], treats missing steps as empty, and detects maneuver.type === "uturn". fetchRoute() keeps the server guard and delegates to these functions.

- [ ] **Step 4: Run and verify GREEN**

Run from web-nuxt: npm test -- tests/itinerary-routing.test.ts

Expected: all tests pass.

- [ ] **Step 5: Commit**

~~~powershell
git add -- web-nuxt/composables/useRouting.ts web-nuxt/tests/itinerary-routing.test.ts
git commit -m "feat: detect u-turns in itinerary routes"
~~~

---

### Task 5: Planner Optimization Helpers

**Files:**
- Create: web-nuxt/tests/itinerary-optimization.test.ts
- Create: web-nuxt/composables/useItineraryOptimization.ts

**Interfaces:**
- Consumes: plan stops and RouteResult.
- Produces: stable occurrence keys, metadata-preserving merge, route-leg alignment, blocked-edge extraction, API adapter, and bounded two-attempt orchestration.

- [ ] **Step 1: Write failing helper tests**

~~~typescript
// @vitest-environment node

import { describe, expect, it } from 'vitest'
import {
  blockedEdgesForUturns,
  collectRoutableStops,
  mergeOptimizedStops,
  routeLegForStopIndex,
  runBoundedOptimization,
} from '../composables/useItineraryOptimization'

const stops = [
  { id: 'same', coords: [10, 106] as [number, number], notes: 'start' },
  { id: 'missing', coords: null, notes: 'keep slot' },
  { id: 'same', coords: [10, 106.7] as [number, number], notes: 'late' },
  { id: 'early', coords: [10, 106.3] as [number, number], notes: 'early' },
  { id: 'end', coords: [10, 107] as [number, number], notes: 'end' },
]

it('assigns unique keys when entity IDs repeat', () => {
  expect(collectRoutableStops(stops).map(item => item.key)).toEqual([
    'planner-stop-0',
    'planner-stop-2',
    'planner-stop-3',
    'planner-stop-4',
  ])
})

it('reorders coordinate slots without moving missing-coordinate slots', () => {
  const routed = collectRoutableStops(stops)
  const merged = mergeOptimizedStops(stops, routed, [
    'planner-stop-0',
    'planner-stop-3',
    'planner-stop-2',
    'planner-stop-4',
  ])
  expect(merged.map(stop => stop.notes)).toEqual([
    'start', 'keep slot', 'early', 'late', 'end',
  ])
})

it('aligns route legs to original coordinate-bearing origins', () => {
  const routed = collectRoutableStops(stops)
  const legs = [
    { distance: 1, duration: 1, hasUturn: false },
    { distance: 2, duration: 2, hasUturn: false },
    { distance: 3, duration: 3, hasUturn: false },
  ]
  expect(routeLegForStopIndex(0, routed, legs)?.distance).toBe(1)
  expect(routeLegForStopIndex(1, routed, legs)).toBeNull()
  expect(routeLegForStopIndex(2, routed, legs)?.distance).toBe(2)
})

it('maps uturn legs to exact directed route keys', () => {
  const routed = collectRoutableStops(stops)
  const route = {
    legs: [
      { distance: 1, duration: 1, hasUturn: false },
      { distance: 2, duration: 2, hasUturn: true },
      { distance: 3, duration: 3, hasUturn: false },
    ],
    totalDistance: 6,
    totalDuration: 6,
    geometry: [],
  }
  expect(blockedEdgesForUturns(routed, route)).toEqual([
    ['planner-stop-2', 'planner-stop-3'],
  ])
})
~~~

- [ ] **Step 2: Run and verify RED**

Run from web-nuxt: npm test -- tests/itinerary-optimization.test.ts

Expected: composable import fails.

- [ ] **Step 3: Implement pure helpers and API adapter**

Create StopWithCoords, RoutableStop, OptimizeOrderResponse, and BoundedOptimizationResult interfaces.

collectRoutableStops() accepts only finite coordinate pairs and keys by original index. mergeOptimizedStops() first verifies ordered IDs are an exact permutation, then replaces only coordinate-bearing slots. routeLegForStopIndex() maps a leg to its routed origin index. blockedEdgesForUturns() returns directed key pairs.

requestOptimizedOrder() POSTs routed keys and coordinates to /api/itineraries/optimize-order. Its injectable fetcher is a boundary seam; production defaults to $fetch.

- [ ] **Step 4: Add and verify the bounded retry tests**

~~~typescript
it('retries exactly once with the uturn edge', async () => {
  const blockedCalls: string[][][] = []
  const optimize = async (_routed: unknown, blocked: string[][]) => {
    blockedCalls.push(blocked)
    return {
      ordered_ids: blocked.length
        ? ['planner-stop-0', 'planner-stop-2', 'planner-stop-1', 'planner-stop-3']
        : ['planner-stop-0', 'planner-stop-1', 'planner-stop-2', 'planner-stop-3'],
      distance_before_km: 10,
      distance_after_km: 8,
      saved_distance_km: 2,
      backtrack_ratio: 0,
      solver: 'exact-dp' as const,
      warnings: [],
    }
  }
  let routeCall = 0
  const route = async () => ({
    legs: [
      { distance: 1, duration: 1, hasUturn: routeCall++ === 0 },
      { distance: 1, duration: 1, hasUturn: false },
      { distance: 1, duration: 1, hasUturn: false },
    ],
    totalDistance: 3,
    totalDuration: 3,
    geometry: [],
  })
  const routed = collectRoutableStops([
    { id: 'a', coords: [10, 106] as [number, number] },
    { id: 'b', coords: [10.02, 106.5] as [number, number] },
    { id: 'c', coords: [9.98, 106.5] as [number, number] },
    { id: 'd', coords: [10, 107] as [number, number] },
  ])
  const result = await runBoundedOptimization(routed, optimize, route)
  expect(blockedCalls).toEqual([
    [],
    [['planner-stop-0', 'planner-stop-1']],
  ])
  expect(result.attempts).toBe(2)
})
~~~

Add a second test where both routes contain U-turns. Assert attempts is 2, unresolvedUturn is true, and no third optimizer call occurs.

Run from web-nuxt: npm test -- tests/itinerary-optimization.test.ts

Expected before implementation: missing runBoundedOptimization export.

Implement exactly two attempts. If the retry optimizer fails, return the first usable order/route with unresolvedUturn=true rather than discarding it.

- [ ] **Step 5: Run and verify GREEN**

Run from web-nuxt: npm test -- tests/itinerary-optimization.test.ts

Expected: all tests pass.

- [ ] **Step 6: Commit**

~~~powershell
git add -- web-nuxt/composables/useItineraryOptimization.ts web-nuxt/tests/itinerary-optimization.test.ts
git commit -m "feat: add planner route optimization helpers"
~~~

---

### Task 6: Planner UI Integration

**Files:**
- Modify: web-nuxt/pages/tao-lich-trinh.vue

**Interfaces:**
- Consumes: Tasks 4-5.
- Produces: the Tối ưu tuyến action, status/warnings, bounded retry, and correct leg display with missing coordinates.

- [ ] **Step 1: Add planner state and imports**

Import collectRoutableStops, mergeOptimizedStops, routeLegForStopIndex, requestOptimizedOrder, and runBoundedOptimization.

Add optimizing, optimizationMessage, and suspendAutoRoute refs. Add computed currentRoutableStops and canOptimize. canOptimize requires at least three routable stops and valid coordinates on the actual first and last planner stops.

- [ ] **Step 2: Add the user-triggered action**

optimizePlanRoute() must:

1. Return when canOptimize is false or an optimization is already active.
2. Set suspendAutoRoute before any reorder.
3. Call runBoundedOptimization() using requestOptimizedOrder() and fetchRoute().
4. Merge ordered routed entries into only coordinate-bearing slots.
5. Preserve time, notes, names, IDs, and missing-coordinate slots.
6. Set routeResult and updateMap() from the final bounded result.
7. Announce saved distance, missing-coordinate warning, and unresolved-U-turn warning honestly.
8. Clear suspendAutoRoute and optimizing in finally.

Do not auto-run optimization on load or stop changes.

- [ ] **Step 3: Add UI and route-leg alignment**

Render Tối ưu tuyến beside transport modes when stops.length >= 3. Disable it while busy or when canOptimize is false. Add role=status text for optimizationMessage.

Change route-leg rendering to call plannerRouteLeg(idx), which delegates to routeLegForStopIndex(idx, currentRoutableStops, routeResult?.legs || []). This prevents missing coordinates from shifting leg labels.

The route watcher must skip scheduleRouteCalc() while suspendAutoRoute is true.

- [ ] **Step 4: Run focused frontend verification**

Run from web-nuxt:

~~~powershell
npm test -- tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts
npm run typecheck
~~~

Expected: tests and typecheck pass.

- [ ] **Step 5: Commit**

~~~powershell
git add -- web-nuxt/pages/tao-lich-trinh.vue
git commit -m "feat: optimize planner routes without backtracking"
~~~

---

### Task 7: Regression Verification and Closure

**Files:**
- Modify: docs/superpowers/specs/2026-07-29-zero-cost-directional-route-optimizer-design.md
- Create a results document only if known full-suite debt needs durable evidence.

**Interfaces:**
- Consumes: all implemented tasks.
- Produces: fresh verification evidence and STATUS: done.

- [ ] **Step 1: Run focused backend regression**

Run:

~~~powershell
python -m pytest agent/tests/test_itinerary_optimizer.py agent/tests/test_public_itinerary_optimizer_api.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_public_api.py -q
~~~

Expected: all selected tests pass.

- [ ] **Step 2: Run the complete frontend suite**

Run from web-nuxt: npm test

Expected: all Vitest tests pass.

- [ ] **Step 3: Run frontend typecheck and build**

Run from web-nuxt:

~~~powershell
npm run typecheck
npm run build
~~~

Expected: both commands exit 0.

- [ ] **Step 4: Run the full backend suite**

Run: python -m pytest -q

Execution timeout: 600000 ms.

Expected: exit 0. Compare any pre-existing documented debt with docs/ROADMAP.md. Any new failure stops the task and must not be weakened or hidden.

- [ ] **Step 5: Inspect scope**

Run:

~~~powershell
git diff --check
git status --short
git log -8 --oneline
~~~

Expected: no whitespace errors in feature files; unrelated pre-existing changes remain unstaged.

- [ ] **Step 6: Close and commit the design**

Change the spec header to STATUS: done, then:

~~~powershell
git add -- docs/superpowers/specs/2026-07-29-zero-cost-directional-route-optimizer-design.md
git commit -m "docs: close directional route optimizer design"
~~~

- [ ] **Step 7: Run final fresh verification**

Run:

~~~powershell
python -m pytest agent/tests/test_itinerary_optimizer.py agent/tests/test_public_itinerary_optimizer_api.py agent/tests/test_cov_itinerary_gen.py -q
cd web-nuxt
npm test -- tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts
npm run typecheck
~~~

Expected: every command exits 0. Report exact test counts and residual risk from approximate POI coordinates and the public OSRM demo service.
