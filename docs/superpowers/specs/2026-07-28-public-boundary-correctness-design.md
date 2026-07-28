# Public Boundary Correctness Design

> STATUS: approved

## Goal

Close the highest-value public/session boundary defects without overlapping the
active `codex/non-public-wave0` worktree: enforce one user-visibility policy
across public profile sections, keep logout state truthful, prevent shared
caching of personalized responses, and bound Nuxt-to-backend requests.

## Scope Boundary

This worktree must not modify:

- `agent/admin.py` or admin authorization/navigation code;
- `agent/auth.py` account-state, OTP, ban, or unban behavior;
- the concurrent non-public Wave 0 spec and plan;
- homepage/design-system work, modal UX, mention autocomplete, or service-worker
  policy.

Those areas are active in other worktrees or belong to later waves. This design
touches only public privacy/cache behavior and the shared frontend transport and
logout boundaries.

## Security And Reliability Invariants

1. A non-self viewer outside a profile's permitted audience receives no posts,
   reviews, social graph, engagement metrics, timeline entries, or activity
   heatmap data.
2. A block in either direction denies the same profile sections.
3. `show_activity=false` hides posts, reviews, engagement, timeline, and the
   activity heatmap from non-self viewers.
4. Existing audience semantics remain compatible: `public` allows non-blocked
   viewers; `followers`, legacy `followers_only`, and `private` allow only self
   or a current follower. Unknown visibility fails closed. A missing privacy row
   keeps the existing `followers_only` audience fallback, while missing activity
   permission fails closed for activity-bearing sections.
5. Personalized cookie/session responses are never reusable by a shared cache.
6. Frontend logout clears local authentication state only after the backend has
   successfully revoked the server session.
7. Every ordinary Nuxt-to-backend request in this scope has a total deadline
   shorter than the outer 120-second Nginx timeout.

## Architecture

### Shared user-visibility policy

Add a focused backend module that owns the public profile-section decision. It
loads the active target and privacy row, checks self/follower/block relations,
and returns a small immutable decision containing:

- `status`: `ok`, `hidden`, or `not_found`;
- the resolved target ID;
- whether the viewer is self;
- whether activity-bearing sections may be returned.

The pure audience predicate is shared with the full-profile endpoint so the
profile card and its child endpoints cannot drift. Invalid visibility is
fail-closed; a missing row preserves the existing non-self `followers_only`
fallback while activity-bearing sections require an explicit positive activity
permission.

Posts, reviews, timeline, heatmap, following, followers, and engagement call the
same decision boundary before querying protected data. Hidden collection
endpoints return their existing empty response shapes. Hidden engagement returns
the same metric keys with zero values. A missing/inactive/deleted target remains
404.

The social graph requires the audience check but is not governed by
`show_activity`; activity-bearing endpoints require both audience and activity
permission. Self access is always allowed.

### Personalized cache policy

Centralize the final response classification in middleware rather than relying
on every endpoint to select the correct header. Successful optional-auth
resolution records the authenticated viewer on request state; invalid or absent
credentials do not. The final response policy then applies:

- anonymous response: retain the endpoint's existing short public cache policy;
- authenticated response: `Cache-Control: private, no-store`;
- API/auth/admin responses: preserve existing `Vary` members and include both
  `Authorization` and `Cookie`;
- any authenticated API response: override an endpoint-level public header with
  `Cache-Control: private, no-store`.

Entity reviews, search, and user engagement already use optional authentication
and therefore become protected without duplicating cache decisions inside those
handlers. This keeps anonymous performance while preventing `my_review`,
block/mute filtering, reactions, or privacy decisions from entering a shared
cache. Deployment must purge any previously shared cached variants.

### Truthful logout

`useAuth.logout()` remains server-authoritative:

1. obtain CSRF state;
2. call `/auth/logout` with credentials and auth headers;
3. clear token, user, CSRF, and 2FA client state only after success;
4. on transport/CSRF/server failure, retain the current client state and reject
   the promise.

`UserMenu` catches the rejection and shows an error toast stating that logout
did not complete. It must not navigate or present a logged-out state on failure.
A generic CSRF `403` is not authoritative sign-out because the backend session
may still be active.

### Frontend backend deadlines

Use explicit constants rather than relying on the Nginx ceiling:

- ordinary API/auth requests: `10_000 ms`;
- launch-policy attestation: `3_000 ms`;
- internal guarded-sitemap fetch: `5_000 ms`.

`apiFetch` supplies the ordinary default while preserving an explicit caller
override. SSR auth initialization uses the same bounded transport. Launch
attestation and sitemap proxying use their narrower deadlines because they gate
HTML or crawler responses. Deadline errors flow through existing degraded or
fail-closed handling; no new retry loop is added.

Authentication probes distinguish an authoritative `401` from transient
deadline, network, and `5xx` failures. Only an authoritative absent/expired
session clears previously established client auth state; transient failures
preserve it.

## Compatibility

- Public profiles and anonymous public search/review payloads keep their current
  shapes and anonymous cache TTLs.
- Authorized self/follower views keep the existing payload shapes.
- Restricted collection endpoints continue to return empty collections rather
  than introducing new authorization error shapes.
- Successful logout behavior and server-side revocation remain unchanged.
- Callers may still supply a shorter or longer explicit `apiFetch` timeout.
- No database migration, data rewrite, dependency addition, or API version bump
  is required.

## Error Handling

- Privacy lookup/query failure is hidden for non-self viewers rather than
  failing open.
- Logout failure is visible to the user and leaves authentication state intact.
- Backend deadline expiration uses the existing fetch error paths: launch
  attestation remains unavailable/fail-closed, guarded sitemap remains degraded,
  and ordinary callers receive their existing error handling.
- Final response policy merges `Vary` values case-insensitively and never removes
  a value already set by an endpoint.

## Testing

All behavior changes use strict red-green-refactor TDD.

- Backend privacy tests cover anonymous, follower, non-follower, self, blocked,
  missing privacy row, unknown visibility, and `show_activity=false` across each
  protected endpoint family.
- Cache tests prove anonymous responses retain public TTLs, authenticated
  responses are `private, no-store`, and `Vary` includes Cookie without dropping
  existing members.
- Frontend logout tests prove a rejected backend call preserves user/token state
  and produces the failure UI, while success clears all client auth state.
- Transport tests prove exact default/override deadlines and cover a
  never-settling injected transport for attestation and sitemap boundaries.
- Focused backend/frontend suites run after every task; the final branch gate
  includes backend privacy/cache regressions, the full frontend test suite,
  Nuxt typecheck/build, and the repository hard checks relevant to touched files.

## Non-Goals

- OTP reactivation, ban/unban hierarchy, admin route scopes, or admin navigation;
- production environment enforcement, filesystem ACLs, systemd sandboxing,
  logging retention, backup topology, or dependency upgrades;
- modal stacking, autocomplete races, or service-worker cache strategy;
- redesigning the meaning of existing privacy choices.
