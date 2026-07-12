# Public Eligibility Boundary Design

> STATUS: done

## Goal

Close the ten validated public-entity publication bypasses without changing the database schema or touching stored data. Every affected endpoint must apply the same `status != provisional` and `verified != false/0` invariant before an entity, entity ID, or entity-derived field enters a public response or cache.

## Scope

This batch covers `REVIEW-06-003` through `REVIEW-06-012`:

- autocomplete;
- featured entities;
- places directory;
- facilities directory;
- place overview;
- place day plan;
- collection list and expansion;
- trending entities;
- entity comparison;
- itinerary list, detail enrichment, and homepage projections.

Social privacy (`REVIEW-02-001`, `REVIEW-02-003`) and the admin review screen (`REVIEW-16-003`) remain separate batches because they use viewer identity and UI review contracts rather than the entity publication boundary.

## Options Considered

### Option 1: Patch each call site directly

Add `public_only=True` where available and inline `_is_public()` filters elsewhere. This is the smallest diff but leaves repeated filtering logic and makes future omissions likely.

### Option 2: Public API helper boundary (selected)

Keep database APIs backward compatible and add focused helpers in `agent/public_api.py`:

- `_filter_public_entities()`;
- `_get_public_entities_batch()`;
- `_public_entities_by_place()`;
- `_public_facilities_by_place()`.

Affected endpoints must use those helpers or an existing database method with `public_only=True`. This closes the current paths with a small, repository-native change and creates one visible boundary for public response construction.

### Option 3: New `PublicProjectionRepository`

Create a separate typed repository that is the only source for public entities. This offers the strongest long-term ownership but is too broad for the first remediation batch and would increase migration risk in the current large `public_api.py` module.

## Selected Architecture

`_is_public()` remains the canonical predicate in the public API layer. It will explicitly reject both boolean `False` and integer `0`, because SQLite and PostgreSQL parsing can represent the same persisted flag differently.

All batch and place-scoped reads pass through helper functions that filter before response shaping. Existing database APIs remain unchanged so admin, knowledge-memory, and internal tooling can still retrieve provisional entities where authorized.

```text
database/internal entities
        |
        v
public eligibility helper
  status != provisional
  verified not false/0
        |
        v
endpoint-specific shaping/cache
        |
        v
public response
```

## Endpoint Behavior

- Hidden place parents return the existing endpoint-specific 404 response.
- Hidden children and facilities are omitted from overview and day-plan results.
- Hidden autocomplete, featured, collection, trending, and comparison records are omitted while preserving the order of remaining records. Collection list responses retain their existing shape but expose only eligible entity IDs.
- Itinerary stops that reference a hidden or missing entity are omitted from list, detail, and homepage responses. Free-form stops without an entity reference remain unchanged.
- Legitimate public entities preserve current response fields, cache headers, ordering, rate limits, and error semantics.

## Error Handling

Eligibility is fail closed. Missing, provisional, or explicitly unverified entities are indistinguishable at public endpoints. No new public error detail exposes why an entity was removed.

## Testing Strategy

TDD regression coverage will first encode:

1. `_is_public()` rejects `verified=False` and `verified=0`;
2. public batch and place helpers preserve only eligible entities;
3. autocomplete requests `public_only=True`;
4. featured, overview, day-plan, collection, trending, comparison, and itinerary paths omit synthetic hidden entities;
5. public controls remain present and ordered correctly.

Tests use synthetic dictionaries and monkeypatched database boundaries. They do not mutate real data or require PostgreSQL.

## Compatibility and Rollback

No database schema or stored data changes. Database method signatures remain stable. Rollback is a normal source revert, but regression tests should remain because they encode the product's existing public quarantine invariant.

## Non-Goals

- No privacy/profile changes.
- No admin review UI changes.
- No autonomous publication-state refactor.
- No data migration, reload, export, or backup operation.
- No broad split of `agent/public_api.py` in this security patch.
