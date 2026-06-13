# VinhLong360 Stabilization Plan

Date: 2026-06-12
Status: Active

## Goal

Turn the current prototype-style codebase into a stable development baseline without rewriting the whole system.

## Phase 1: Foundation

- Add architecture decisions and API contract documents.
- Add a data validation script.
- Normalize entity coordinates toward `coordinates`.
- Fix pytest collection so the whole suite can be collected consistently.
- Establish baseline validation/test commands.

Checkpoint commands:

```powershell
python scripts/validate_data.py
python -m pytest --collect-only -q
python -m pytest tests\test_vector_search.py tests\test_middleware.py tests\test_guardrails.py agent\tests\test_knowledge.py -q
```

## Phase 2: API and frontend alignment

- Update backend relationship responses to include canonical relationship fields.
- Update Nuxt map/detail/search pages to prefer `coordinates` and canonical relationship fields.
- Keep temporary compatibility for legacy static data and old API fields.

Checkpoint commands:

```powershell
cd web-nuxt
npm run build
```

## Phase 3: Deploy and operations

- Move Docker/Nginx toward the Nuxt production path.
- Remove hard-coded localhost API proxy targets where possible.
- Harden admin access and secret handling.
- Separate runtime artifacts from source files.

Checkpoint commands:

```powershell
docker compose config
```

Additional local operations:

```powershell
# Normalize static data safely and keep web/data.js in sync.
python scripts/normalize_data.py --infer-area --infer-area-from-place --summarize-places

# Rebuild the SQLite dev cache from the normalized static export.
python agent/database.py --replace

# Start the backend without expensive search-index warmup for smoke tests.
$env:BUILD_SEARCH_INDEXES='false'; $env:BACKGROUND_INDEX_BUILD='false'; $env:SCHEDULER_ENABLED='false'; python agent/server.py

# Run deep dependency checks only when needed.
Invoke-RestMethod http://localhost:8360/health/deep
```

## Data quality checkpoints

Current safe normalization rules:

- `coordinates` remains the canonical location field.
- `area` can be inferred from entity text when exactly one province is mentioned.
- `area` can be inferred from `placeId` only when the entity text does not contradict the place area.
- Missing `place` summaries can be generated from existing administrative fields; no external facts are invented.
- `source` should not be fabricated. Use explicit internal provenance only if the project accepts that convention.

## Working rules

- Prefer additive compatibility changes before removals.
- Do not delete legacy data or UI surfaces until the replacement path is verified.
- Every schema change needs validation coverage.
- Every deploy change needs a local config/build check.
