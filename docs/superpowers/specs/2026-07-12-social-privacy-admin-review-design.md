# Social Privacy and Admin Review Design

> STATUS: done

## Goal

Close `REVIEW-02-001`, `REVIEW-02-003`, and `REVIEW-16-003` without changing stored data or broadening the patch into unrelated social or publication-state refactors.

## Security Invariants

1. A saved entity may enter the friend-saves feed only when the owner has no privacy row or has `show_saved=true`.
2. A viewer outside a followers-only profile audience must receive the existing restricted profile response, never the full profile projection.
3. Manual approval must apply to the exact complete entity snapshot rendered to the editor. A changed, stale, or absent review token must fail closed.

## Selected Boundaries

### Friend-saves SQL boundary

Enforce `show_saved` in the query that selects `saved_entities`. Use a left join and `COALESCE(..., TRUE)` because the documented absence-of-row default is visible.

### Profile audience helper

Add one named helper for the full-profile audience decision. Preserve the current behavior for `private` (self or follower) and the fail-closed `followers_only` fallback, while adding the missing persisted literal `followers`. Unknown non-public values fail closed.

### Immutable provisional review snapshot

`kb_curation.list_provisional()` returns a complete review DTO:

- `id`;
- `review_token`, a SHA-256 digest of a canonical JSON snapshot;
- `entity`, containing every current entity field except mutable review state (`status`, `verified`).

The admin page renders the complete summary and structured publication fields, plus the full snapshot for uncommon provider fields. Approval sends `review_token`. The backend recomputes the current token and returns a conflict when it differs, so hidden or changed fields cannot be approved under an older review.

## Compatibility

- Friend-saves response shape, limits, ordering, block checks, and cache behavior remain unchanged.
- Public profiles and authorized follower/self views retain the full response shape.
- Restricted profiles retain the existing private response shape.
- Reject behavior is unchanged.
- The manual approval request intentionally gains a required JSON body containing `review_token`; the only current frontend caller is updated in the same patch.
- Automatic promotion remains separate because it is eval-gated rather than a human review decision.

## Non-Goals

- No redesign of follow approval or account discovery.
- No change to `show_activity` enforcement.
- No resolution of broader DB-versus-export source-of-truth debt.
- No publication state-machine refactor.
- No data migration, reload, export, or real-data mutation.

## Verification

- TDD unit regressions for the friend-saves SQL and profile audience boundary.
- TDD fixture regressions for complete review DTOs, valid tokens, and stale-token rejection.
- Frontend regression test proving every required field and the token-bearing approval body are present.
- Focused backend/frontend suites, Ruff, Nuxt typecheck/build, full pytest, and independent spec/code-quality review.

## Deferred Transactional Ownership

Independent review confirmed that file-level CAS protects edits made after the guarded post-apply version is captured, but it cannot assign ownership to edits made during a long `apply_fn`. Resolving that race requires the Workstream 6 transactional publication state machine: an owned atomic commit or targeted three-way rollback, explicit conflict/failure decisions, and authoritative-state compensation. It is outside this design's social-privacy and manual-review invariants.
