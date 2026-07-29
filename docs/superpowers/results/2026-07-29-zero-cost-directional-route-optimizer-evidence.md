> STATUS: done
> Date: 2026-07-29
> Branch: `codex/zero-cost-route-optimizer`
> Scope: local implementation and regression evidence; no deployment or production-data mutation.

# Zero-Cost Directional Route Optimizer Evidence

## Delivered behavior

- Added `POST /api/itineraries/optimize-order` with fixed first/last stops and input validation for 2-20 routable stops.
- Uses exact dynamic programming for at most 10 intermediate stops and deterministic beam/local search for larger routes.
- Enforces forward corridor constraints and preserves planner metadata plus missing-coordinate slots.
- Requests OSRM steps with `continue_straight=true`, detects U-turn legs, and performs at most one retry with offending directed edges blocked.
- Added no paid service, API key, Python/NPM dependency, schema change, migration, database write, or LLM call.

## Verification evidence

| Check | Result |
| --- | --- |
| Relevant backend baseline before implementation | `92 passed` |
| Optimizer, public API, generator, and public API regression | `113 passed`; one pre-existing Starlette/httpx deprecation warning |
| Full frontend Vitest suite | `40 files`, `938 tests passed` |
| Focused itinerary routing/optimization tests | `12 passed` |
| Nuxt typecheck | exit 0 |
| Nuxt production build | exit 0 |
| Changed-backend Ruff checks | exit 0 |
| Commit hard/ratchet pre-commit checks | passed for all feature commits |
| 20-stop optimizer smoke | `beam-search`, about `9.63 ms`, `backtrack_ratio=0` |

## Full backend suite limitation

The repository collects about 6,043 backend tests. Two direct full-suite attempts using `python -m pytest -q` did not complete within the available execution windows:

| Attempt | Timeout | Observed result |
| --- | ---: | --- |
| 1 | 600 seconds | timed out; no failure output appeared before termination |
| 2 | 1,800 seconds | timed out; no failure output appeared before termination |

This document does not claim that the complete backend suite passed. The official long-running runner is `python scripts/ops/run_backend_regression.py --deadline-seconds 7000`; it remains an optional extended gate when a sufficiently long execution window is available. Focused tests covering every changed backend area passed.

## Residual risks

- POI coordinates can be approximate, so a geometrically forward order cannot guarantee every real driveway or entrance avoids a turn-around.
- Final road validation depends on the existing public OSRM demo endpoint and inherits its availability and routing-data limits.
- The beam-search branch is deterministic and bounded for 20 stops but is heuristic rather than globally optimal above the exact-DP threshold.
