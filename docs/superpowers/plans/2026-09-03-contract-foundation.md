# Contract Foundation Implementation Plan

> STATUS (active): contract baseline implementation and governance plan; release approval remains separate.

> For agentic workers: use task-by-task execution with a fresh verification checkpoint. Steps use checkbox syntax for tracking.

**Goal:** Establish a machine-readable, deterministic API contract baseline that an independent frontend team can consume without changing runtime behavior.

**Architecture:** Keep the current FastAPI modular monolith. Export its live OpenAPI document through a deterministic script, add shared JSON Schemas for errors and pagination, and add contract drift checks. This first slice changes tooling and documentation only; it does not change endpoint behavior or deployment.

**Execution status (2026-09-03):** All five tasks and the verification matrix have been executed successfully. The release gate remains intentionally `NO_GO`/`BLOCKED`; this plan does not grant release approval.

**Tech Stack:** Python 3.12+, FastAPI, JSON Schema draft 2020-12, pytest, existing Nuxt/TypeScript frontend.

## Global Constraints

- Do not change endpoint behavior or production routing.
- Do not remove or rename legacy endpoints.
- Do not add microservices, service mesh, event bus, or a second database.
- Do not include secrets, browser profiles, production environment files, or runtime credentials.
- Preserve the current NO_GO/BLOCKED release verdict.
- Do not commit or push unless the owner explicitly requests it.

### Task 1: Deterministic OpenAPI Export

Files:
- Create scripts/export_openapi.py
- Create tests/contracts/test_export_openapi.py
- Create contracts/openapi/.gitkeep
- Generate contracts/openapi/backend-openapi.json

Interfaces:
- CLI: python scripts/export_openapi.py --output contracts/openapi/backend-openapi.json
- Output is UTF-8 JSON, sorted keys, two-space indentation, trailing newline.
- Output contains the live FastAPI route set and no credential values.

- [x] Step 1: Write a failing subprocess test for file creation, required keys, /api/entities, byte-identical consecutive exports, and absence of DATABASE_URL/PILOT_ATTEST/LLM_API_KEY markers.
- [x] Step 2: Run python -m pytest tests/contracts/test_export_openapi.py -q -m "" --tb=line and verify failure because the exporter is missing.
- [x] Step 3: Implement the minimal exporter: resolve repository root, add agent to sys.path, set development environment default, import server.app, call app.openapi(), serialize deterministically, and write the requested output.
- [x] Step 4: Re-run the focused test and verify it passes.
- [x] Step 5: Generate the canonical snapshot and parse it with Python json.load.

### Task 2: Shared Error and Pagination Schemas

Files:
- Create contracts/schemas/error-envelope.schema.json
- Create contracts/schemas/pagination.schema.json
- Create tests/contracts/test_shared_schemas.py

Interfaces:
- Error schema requires type, title, status, code, and detail; requestId is optional.
- Pagination schema defines limit, offset, nextCursor, and hasMore as optional interoperable metadata.
- Schemas are documentation/validation contracts only in this slice.

- [x] Step 1: Write failing tests for required error fields, invalid status, and valid pagination examples.
- [x] Step 2: Run the tests and verify expected missing-file failures.
- [x] Step 3: Add both JSON Schemas with draft 2020-12 and explicit additionalProperties rules.
- [x] Step 4: Run the tests and verify they pass.
- [x] Step 5: Run git diff --check.

### Task 3: Contract Governance Documentation

Files:
- Create contracts/README.md
- Modify docs/api-contract.md

Interfaces:
- OpenAPI is the machine-readable source of truth.
- Additive and breaking change policy is explicit.
- /api/v1 migration is documented without changing current routes.
- Backend publishes; frontend consumes; both run contract checks.
- Internal launch and operations routes are not frontend contract.

- [x] Step 1: Add contracts/README.md with generation, validation, and ownership commands.
- [x] Step 2: Add a concise pointer from docs/api-contract.md.
- [x] Step 3: Verify every referenced path exists.
- [x] Step 4: Run focused contract tests.

### Task 4: Frontend Endpoint Inventory

Files:
- Create contracts/frontend-endpoints.json
- Create tests/contracts/test_frontend_endpoint_inventory.py

Interfaces:
- Inventory only endpoints actually called by frontend source.
- Each entry includes method, path pattern, auth requirement, and owning domain.
- Direct $fetch calls remain temporarily allowed but are listed for migration.

- [x] Step 1: Extract and review endpoint paths from web-nuxt source.
- [x] Step 2: Add a test that validates every listed path appears in frontend source.
- [x] Step 3: Mark direct transport exceptions explicitly.
- [x] Step 4: Run inventory tests.

### Task 5: CI Contract Drift Gate

Files:
- Create scripts/check_contract_drift.py
- Create tests/contracts/test_contract_drift.py
- Modify .github/workflows/ci.yml

Interfaces:
- Regenerate OpenAPI to a temporary file and compare it to contracts/openapi/backend-openapi.json.
- Drift exits non-zero with a readable regeneration hint.
- The gate never reads production secrets or calls external providers.
- CI runs it after backend dependencies are installed.

- [x] Step 1: Write failing drift tests.
- [x] Step 2: Run the tests and verify failure.
- [x] Step 3: Implement deterministic comparison.
- [x] Step 4: Run drift tests and focused backend tests.
- [x] Step 5: Add the CI step.
- [x] Step 6: Run the complete contract test group.

## Verification Matrix

- [x] python -m pytest tests/contracts -q -m "" --tb=line
- [x] python -m compileall -q scripts agent
- [x] git diff --check
- [x] python scripts/check_contract_drift.py
- [x] python scripts/ops/validate_drill_index.py --root .
- [x] python scripts/ops/verify_release_bundle.py --bundle artifacts/pilot-acceptance.json (expected to remain BLOCKED)

## Explicitly Deferred

- Physical frontend repository split.
- Runtime /api/v1 route migration.
- Full typed replacement of all permissive response models.
- BFF service extraction.
- Database refactor.
- Microservices/event bus.
- Production release approval or signing.
