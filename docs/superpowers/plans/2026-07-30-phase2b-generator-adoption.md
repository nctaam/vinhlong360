# Phase 2B Generator Adoption Implementation Plan

> **STATUS (2026-07-30): active — implementation complete locally; final review pending.**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the itinerary generator's fixed `+30` minute travel assumption with the existing local time-aware scheduler, while adding configurable meal/rest anchors without changing the legacy `day_plans` contract or adding paid services.

**Architecture:** Keep candidate selection and the public generator output stable. For a day whose selected entities have usable coordinates, adapt them into `ScheduleStop` values, build the existing Haversine fallback matrix locally, and project scheduler placements back into the legacy stop shape. If coordinates are incomplete or scheduling cannot produce a safe result, retain the current deterministic legacy timeline and expose a diagnostic warning. Meal and rest anchors are represented as fixed-window synthetic/meal stops only when a matching candidate or local coordinate exists; no meal is fabricated when no candidate is available.

**Tech Stack:** Python 3.11+, existing `agent/itinerary_schedule.py` solver, pytest, existing MCP tool wrapper. No new dependency, network request, migration, or LLM call.

## Global Constraints

- Preserve `generate_itinerary(...)`'s existing keys and `day_plans[*].stops[*]` fields; all Phase 2B fields are additive and optional.
- Do not change the saved-itinerary schema, public optimizer endpoint, or frontend contract.
- Use only local Haversine fallback for generator travel times; do not call OSRM, web services, or an LLM from the generator.
- Keep the existing fixed-order/`+30` timeline as the safe fallback when selected entities lack usable coordinates or the scheduler cannot return a valid result.
- Never fabricate a meal entity; if no dish/product candidate exists for an anchor, omit the meal and record a diagnostic warning.
- Required scheduler endpoints remain the first and last selected stops; any dropped middle stop must carry an explicit `reason`.
- Use test-first development: each production behavior is introduced only after a focused test has failed for the intended reason.
- Do not run deployment, migration, push, or paid API calls.

---

### Task 1: Time-Aware Generator Adapter

**Files:**
- Modify: `agent/itinerary_gen.py`
- Modify: `agent/tests/test_cov_itinerary_gen.py`
- Create: `agent/tests/test_itinerary_generator_schedule.py`

**Interfaces:**
- Consumes: selected candidate dictionaries from `_select_diverse(...)`; existing `itinerary_schedule` exports `ScheduleStop`, `ScheduleOptions`, `build_fallback_matrix`, `infer_visit_minutes`, `parse_opening_hours`, and `schedule_stop_order`.
- Produces: `generate_itinerary(...)` with its current arguments and output keys unchanged, plus optional per-day `schedule` diagnostics containing `solver`, `matrix_source`, `total_travel_minutes`, `waiting_minutes`, `overtime_minutes`, `minimum_slack_minutes`, `backtrack_ratio`, `skipped`, and `warnings`.

- [ ] **Step 1: Write failing tests for coordinate-aware scheduling.**

Add focused tests that patch `knowledge._entities` with candidates containing coordinates and assert:

```python
def test_generator_uses_real_leg_durations_instead_of_fixed_thirty_minutes(generator_entities):
    result = itinerary_gen.generate_itinerary(days=1, interests=["tham_quan"], areas=["vinh-long"])
    stops = result["day_plans"][0]["stops"]
    assert [stop["entity"]["id"] for stop in stops if not stop.get("is_meal")] == ["start", "near", "end"]
    assert stops[1]["time"] == "08:15"
    assert result["day_plans"][0]["schedule"]["matrix_source"] == "haversine-fallback"
```

Also add a fallback test with one missing coordinate that asserts the legacy `+30` timeline remains usable and the day diagnostic contains `coordinates-missing`.

- [ ] **Step 2: Run the focused tests and verify they fail for the missing adapter behavior.**

Run:

```powershell
python -m pytest agent/tests/test_itinerary_generator_schedule.py -q
```

Expected: the new coordinate-aware assertion fails because the generator still uses `_build_day_stops(...)` and has no per-day scheduler diagnostics.

- [ ] **Step 3: Implement the minimal adapter.**

Add small helpers in `agent/itinerary_gen.py`:

```python
def _candidate_coordinates(item: dict) -> tuple[float, float] | None: ...
def _candidate_schedule_stop(item: dict, required: bool) -> ScheduleStop | None: ...
def _build_day_schedule(day_entities: list[dict], month: int) -> tuple[list[dict], dict]: ...
```

Use entity coordinates first and the parent place coordinates second. Parse `hours`/`open_hours` through `parse_opening_hours`, infer duration from `visit_minutes`, `duration_minutes`, or `suggested_duration`, then type defaults. Build a local matrix with `build_fallback_matrix(stops, "driving")` and call `schedule_stop_order(...)` with `ScheduleOptions(day_start_minute=480, day_end_minute=1080)`. Map placements back to candidate summaries and retain `time` plus the existing notes. If any stop has no usable coordinate or the scheduler raises `NoFeasibleScheduleError`, call the unchanged legacy builder and add a warning instead of returning partial or invalid JSON.

- [ ] **Step 4: Run the focused tests and the existing generator/scheduler tests.**

Run:

```powershell
python -m pytest agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py -q
```

Expected: all tests pass; legacy fixture behavior remains green while coordinate fixtures use actual travel durations.

- [ ] **Step 5: Commit the adapter and tests.**

```powershell
git add agent/itinerary_gen.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_generator_schedule.py
git commit -m "feat: adopt time-aware scheduler in itinerary generator"
```

### Task 2: Configurable Meal and Rest Anchors

**Files:**
- Modify: `agent/itinerary_gen.py`
- Modify: `agent/tests/test_itinerary_generator_schedule.py`

**Interfaces:**
- Consumes: Task 1's coordinate-aware day adapter and diagnostics.
- Produces: optional `meal_anchors: list[str] | None = None` and `rest_anchors: list[str] | None = None` arguments on `generate_itinerary(...)`; defaults preserve one lunch-window attempt at `12:00` and no synthetic rest stops. Anchor times use the existing local `HH:MM`/`HhMM` parser grammar.

- [ ] **Step 1: Write failing tests for fixed-window anchors.**

Add tests that pass `meal_anchors=["12:00"]` and assert a real dish/product candidate is scheduled with `is_meal=True` and a start time at or after `12:00`; pass `rest_anchors=["15:00"]` and assert a synthetic `is_rest=True` stop is emitted only when a neighboring coordinate exists. Add a no-candidate test asserting no fake meal entity appears and the diagnostic includes `meal-anchor-unavailable`.

- [ ] **Step 2: Run the anchor tests and verify the expected failures.**

Run:

```powershell
python -m pytest agent/tests/test_itinerary_generator_schedule.py -q
```

Expected: `generate_itinerary` rejects the new keyword arguments or produces no fixed-window anchor stop.

- [ ] **Step 3: Implement anchor normalization and scheduling.**

Normalize anchor strings through `parse_time_range(...)` as one-point windows, reject invalid values without crashing, and add `invalid-anchor` to diagnostics. For a meal anchor, select an unused dish/product candidate in the day area and add it as a required fixed-window `ScheduleStop` with a 60-minute visit. For a rest anchor, add a synthetic stop at the previous/next route coordinate with a 30-minute fixed window and `is_rest=True`. Keep synthetic stops out of `total_stops` only if the existing contract counts content stops; otherwise document and test the additive count consistently. Preserve explicit skip reasons from `ScheduleResult.skipped`.

- [ ] **Step 4: Run anchor, generator, and scheduler tests.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py -q
```

- [ ] **Step 5: Commit the anchor implementation.**

```powershell
git add agent/itinerary_gen.py agent/tests/test_itinerary_generator_schedule.py
git commit -m "feat: add configurable itinerary meal and rest anchors"
```

### Task 3: MCP Exposure and Contract Documentation

**Files:**
- Modify: `agent/mcp_server.py`
- Modify: `agent/tests/test_cov_itinerary_gen.py`
- Create: `agent/tests/test_itinerary_generator_mcp.py`
- Modify: `docs/api-contract.md`
- Modify: `docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md`

**Interfaces:**
- Consumes: Task 2's optional generator arguments and diagnostics.
- Produces: MCP `generate_itinerary` accepts and forwards `meal_anchors`/`rest_anchors`; documentation states local fallback, warning semantics, and backward-compatible response additions.

- [ ] **Step 1: Write failing MCP and contract tests.**

Add a test that invokes the registered MCP wrapper with `meal_anchors=["12:00"]` and verifies the generator receives the value. Add source/contract assertions that the documented generator behavior names `haversine-fallback`, `coordinates-missing`, `meal-anchor-unavailable`, and explicit dropped-stop reasons.

- [ ] **Step 2: Run the focused tests and verify they fail before wiring.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_mcp.py -q
```

- [ ] **Step 3: Wire the MCP wrapper and update documentation.**

Extend only the existing `generate_itinerary` tool signature, forward the optional lists, keep defaults `None`, and document that no OSRM/LLM request is made by the generator. Update only the roadmap status for Phase 2B; do not mark Phases 3-6 complete.

- [ ] **Step 4: Run the complete Phase 2B focused verification.**

```powershell
python -m pytest agent/tests/test_itinerary_generator_mcp.py agent/tests/test_itinerary_generator_schedule.py agent/tests/test_cov_itinerary_gen.py agent/tests/test_itinerary_schedule.py -q
git diff --check
```

- [ ] **Step 5: Commit the MCP/docs changes.**

```powershell
git add agent/mcp_server.py agent/tests/test_itinerary_generator_mcp.py agent/tests/test_cov_itinerary_gen.py docs/api-contract.md docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md
git commit -m "docs: expose phase 2b generator scheduling contract"
```

## Verification Checklist

- [ ] All three task-level reviews report spec compliance and task quality approval.
- [ ] Backend focused Phase 2B matrix passes; no full-repository suite claim is made.
- [ ] No paid dependency, network call, migration, deploy, or saved-schema change is introduced.
- [ ] Final whole-branch review is clean or has only explicitly parked non-load-bearing minors.
