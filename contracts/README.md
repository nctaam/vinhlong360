# VinhLong360 API Contracts

This directory is the shared boundary between the frontend and backend teams.
The backend remains the runtime owner of the API, while this directory records
the machine-readable contract that consumers can validate without importing
Python source code.

## Source of truth

- `openapi/backend-openapi.json` is the deterministic snapshot exported from the
  live FastAPI route registry.
- `schemas/error-envelope.schema.json` defines the common problem response
  shape for new endpoints.
- `schemas/pagination.schema.json` defines interoperable pagination metadata.
- `frontend-endpoints.json` records the endpoint surface currently consumed by
  the Nuxt application.
- `response-media-types.json` records runtime response media types that cannot
  be inferred reliably from FastAPI's return annotation (currently the SSE
  `/chat/stream` response); the exporter validates every override against a
  live route before applying it.
- `docs/api-contract.md` remains the human-readable business and migration
  guide; it is not a substitute for the machine-readable schemas.

## Commands

From the repository root:

```powershell
python scripts/export_openapi.py --output contracts/openapi/backend-openapi.json
python scripts/check_contract_drift.py
python -m pytest tests/contracts -q -m "" --tb=line
```

The exporter must run with development defaults and must not read production
credentials or call external providers. A contract drift is a review-required
change: regenerate the snapshot, inspect the route/schema diff, and update the
consumer tests in the same change.

## Compatibility policy

- Adding an endpoint or optional response field is additive.
- Removing or renaming a field, changing its type, changing an enum meaning, or
  changing authentication semantics is breaking.
- Breaking changes require a versioned contract and a documented migration
  window. The target URL convention is `/api/v1/...`; existing unversioned
  routes remain supported during migration.
- New endpoints should use explicit request and response schemas. Legacy
  permissive response models may remain while consumers migrate.
- Error responses should include stable `code` values and a request identifier;
  clients must not branch on localized `detail` text.

## Ownership

- Backend owns route behavior, authorization, persistence, migrations and the
  exported OpenAPI document.
- Frontend owns consumer behavior, generated-client integration, accessibility
  and UI tests.
- Both teams own compatibility review. Provider contract tests run with the
  backend; consumer contract tests run with the frontend.
- Internal launch, readiness, deployment and operations routes are platform
  contracts, not frontend product API.

## Handoff rule

An independent frontend team may work from the contract snapshot, generated
TypeScript types and mock responses. It must not copy backend database models,
read internal routes, or infer security behavior from implementation details.
