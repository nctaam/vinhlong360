# VinhLong360 API Contract

> **STATUS (2026-07-07): active — đã truth-sync.** Type enum synced to the 18-type registry; auth/admin path prefixes corrected to the actual routes (`/auth/*`, `/admin/*`); 2FA/trusted-devices endpoints added.

Date: 2026-06-12 (updated 2026-07-30)
Status: Baseline endpoints reflect production; the Phase 2A schedule contract is implemented locally, default-off, and not deployed.

This contract defines the data shapes and API endpoints shared between the FastAPI backend (`agent/`) and the Nuxt frontend (`web-nuxt/`).

## Data Shapes

### Entity

```json
{
  "id": "entity-id",
  "name": "Display name",
  "type": "attraction|place|dish|drink|restaurant|cafe|product|itinerary|facility|organization|accommodation|experience|craft_village|event|nature|history|person|economy",
  "summary": "Short description",
  "description": "Long description",
  "coordinates": [10.0, 106.0],
  "coords_approximate": false,
  "area": "vinh-long",
  "placeId": "p-xa-name",
  "level": "xa|phuong|tinh|null",
  "parentId": "parent-entity-id|null",
  "source": [{"title": "Source name", "url": "https://..."}],
  "season": {"months": [6, 7], "peak": [6]},
  "images": ["https://cdn/.../img1.webp"],
  "attributes": {},
  "confidence": 1.0,
  "updatedAt": "2026-06-22T10:00:00Z",
  "created_at": "2026-06-22 10:00:00"
}
```

Rules:
- `id`, `name`, and `type` are required.
- `type` — 18 canonical types. Source of truth: `agent/entity_schemas.py` (`KIND_OF_TYPE` / `valid_types()`, enforced by admin validation), mirrored by `web-nuxt/composables/useConstants.ts` (`TYPE_META`). Update those two files together with this enum.
- `coordinates` is canonical (`[lat, lng]`). `coords` is legacy-only.
- `coords_approximate` — true when coordinates are derived from ward centroid (not exact).
- `images` — array of URLs, default `[]`. First element is the cover image.
- `source` — array of `{title, url}` objects (may also be a plain string for legacy data).
- `season` — `months` (array 1..12) and optional `peak` subset.
- `area` — provenance bucket from the pre-merger provinces: `vinh-long`, `ben-tre`, or `tra-vinh`. Kept for filtering/provenance only — administratively there is a single merged Vĩnh Long province since 07/2025 (see architecture-decisions #12).
- `placeId` — links to a ward/commune entity. May be `null` for unclassified entities.
- `level` — only for place entities: `xa`, `phuong`, or `tinh`.
- `attributes` — always an object when present.
- `confidence` — 0.0–1.0, data trustworthiness score.

### Relationship

```json
{
  "source_id": "source-entity-id",
  "target_id": "target-entity-id",
  "rel_type": "near|related_to|associated_with|located_in|part_of|produced_in",
  "target_name": "Target display name",
  "target_type": "place",
  "source_name": "Source display name",
  "source_type": "attraction"
}
```

Legacy aliases (`from_id`, `to_id`, `type`) may be included during migration.

### Itinerary

```json
{
  "id": "itinerary-id",
  "name": "2 ngày 1 đêm Vĩnh Long",
  "summary": "...",
  "area": "vinh-long",
  "stops": [
    {"entity_id": "entity-id", "name": "Stop name", "day": 1, "order": 1, "note": "..."}
  ],
  "duration": "2 ngày 1 đêm",
  "attributes": {}
}
```

---

## API Endpoints

### Public API (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/entities` | List entities (filters: type, area, q, month, limit, offset) |
| GET | `/api/entities/{id}` | Entity detail with relationships, quality score, and mandatory `index_policy`; exact registered route is `no-store`, emits no validators, and never returns 304 |
| GET | `/api/entities/{id}/relationships` | Paginated relationships |
| GET | `/api/places` | List place entities (xã/phường/tỉnh) |
| GET | `/api/facilities` | List facility entities |
| GET | `/api/places/{id}/overview` | Place overview with child entity summary |
| GET | `/api/itineraries` | List itineraries |
| POST | `/api/itineraries/optimize-order` | Optimize 2-20 itinerary stops along a fixed start-to-end direction |
| GET | `/api/itineraries/{id}` | Itinerary detail |
| GET | `/api/search` | Full-text search entities + itineraries |
| GET | `/api/stats` | Public stats (entity counts, etc.) |
| GET | `/api/homepage` | Homepage data (seasonal, events, featured) |
| GET | `/api/events` | Upcoming events |
| GET | `/api/site-settings` | Public site settings (cached 60s) |
| GET | `/api/mentions` | @-mention autocomplete |
| POST | `/api/report` | Report content/entity (rate-limited) |
| POST | `/api/client-error` | Client-side error reporting |

The table above lists the primary endpoints; `agent/public_api.py` also serves additional public routes (autocomplete, map-pins, gallery, similar, nearby, qa, reviews, collections, announcements, featured, entity-types, areas, ...). Check the router when in doubt.

Policy-bearing HTTP responses are governed by the exact registry in `agent/policy_http.py`. Matching uses the resolved FastAPI method, path template, and route name; static `/api/entities/*` routes retain their existing cache behavior.
The same exact route identity is used for pre-routing 413/503 short-circuits; unmatched URLs remain outside the policy contract.

#### Itinerary order optimization and optional schedule

`POST /api/itineraries/optimize-order` keeps the order-only contract. A request that omits `schedule` remains valid and does not enter the time-aware scheduler:

```json
{
  "stops": [
    {"id": "start", "coordinates": [10.0, 106.0]},
    {"id": "late", "coordinates": [10.0, 106.7]},
    {"id": "early", "coordinates": [10.0, 106.3]},
    {"id": "end", "coordinates": [10.0, 107.0]}
  ],
  "strict_direction": true,
  "blocked_edges": []
}
```

The order-only response shape is unchanged:

```json
{
  "ordered_ids": ["start", "early", "late", "end"],
  "distance_before_km": 197.1,
  "distance_after_km": 109.5,
  "saved_distance_km": 87.6,
  "backtrack_ratio": 0.0,
  "solver": "exact-dp",
  "warnings": []
}
```

The optional `schedule` request envelope is:

```json
{
  "day_start_minute": 480,
  "day_end_minute": 1080,
  "mode": "driving",
  "stops": [
    {"id": "start", "visit_minutes": 0, "required": true},
    {
      "id": "late",
      "visit_minutes": 30,
      "opening_hours": "10:00-17:00",
      "required": true
    },
    {
      "id": "early",
      "visit_minutes": 30,
      "opening_hours": "08:00-09:30",
      "requested_time": "08:00-09:30",
      "required": true
    },
    {"id": "end", "visit_minutes": 0, "required": true}
  ],
  "duration_matrix_minutes": [
    [0, 20, 10, 40],
    [20, 0, 20, 20],
    [10, 20, 0, 30],
    [40, 20, 30, 0]
  ]
}
```

Request rules:

- Outer `stops` contains 2-20 unique IDs and `[lat, lng]` coordinates. `strict_direction` defaults to `true`; `blocked_edges` defaults to `[]`.
- `schedule` is optional. Its defaults are `day_start_minute=480`, `day_end_minute=1080`, `mode="driving"`, `visit_minutes=60`, and `required=true`; supported modes are `driving`, `cycling`, and `foot`.
- `day_start_minute` and `day_end_minute` must each be within `0..1440`, with `day_end_minute > day_start_minute`. Each `visit_minutes` value must be within `0..720`. Violations return HTTP 422.
- Nested schedule IDs must be an exact permutation of the outer stop IDs. The nested first and last IDs must match the outer first and last IDs, and both endpoints must be required.
- `duration_matrix_minutes` may be omitted or explicitly `null`; either form selects the local Haversine fallback. When non-null, it must be square, match the nested stop count/order, contain finite non-negative minutes or `null` only in off-diagonal cells, and contain `0` on the diagonal.
- `requested_time` accepts the supported local range grammar (for example `09:00-10:30`, `9h-10h`, or `9h00-10h30`). It is a hard window. When `opening_hours` also supplies trusted windows, the scheduler uses their intersection. An invalid `requested_time` or invalid envelope returns HTTP 422.
- Travel applies on the first hop. With the matrix fixture above, the `early` placement arrives and begins at minute `490`, not `480`.

On schedule success, the normal order response adds the optional `schedule` object. Placement fields use the public API name `end_visit_minute`:

```json
{
  "ordered_ids": ["start", "early", "late", "end"],
  "warnings": [],
  "schedule": {
    "placements": [
      {"stop_id": "start", "arrival_minute": 480.0, "start_visit_minute": 480.0, "end_visit_minute": 480.0},
      {"stop_id": "early", "arrival_minute": 490.0, "start_visit_minute": 490.0, "end_visit_minute": 520.0},
      {"stop_id": "late", "arrival_minute": 540.0, "start_visit_minute": 600.0, "end_visit_minute": 630.0},
      {"stop_id": "end", "arrival_minute": 650.0, "start_visit_minute": 650.0, "end_visit_minute": 650.0}
    ],
    "skipped": [
      {"stop_id": "optional", "reason": "day-window-overflow"}
    ],
    "matrix_source": "request",
    "total_travel_minutes": 50.0,
    "waiting_minutes": 60.0,
    "overtime_minutes": 0.0,
    "minimum_slack_minutes": 50.0
  }
}
```

Fallback and compatibility rules:

- If `duration_matrix_minutes` is omitted or explicitly `null`, the server builds a local Haversine matrix using the requested mode; successful responses report `matrix_source: "haversine-fallback"`. No paid routing service or new dependency is used.
- An impossible required schedule returns HTTP 409 with a reason and no partial schedule. Optional stops may be omitted only with entries in `schedule.skipped` that include a `reason`.
- If the scheduling implementation fails unexpectedly, the endpoint retries through the established order-only optimizer. A successful fallback has no `schedule` field and includes `schedule-fallback-order-only` in `warnings`; it never returns a partial schedule.
- The manual planner feature flag is default-off. Only `NUXT_PUBLIC_ITINERARY_SCHEDULE_V2=1` exposes `runtimeConfig.public.itineraryScheduleV2=true`; flag-off requests remain order-only and make no Table request.

### Manual planner client constraints

- For one user-triggered optimization fingerprint (transport mode plus stop coordinates rounded to five decimal places), the client performs at most one OSRM Table request, one initial OSRM Route request, and one U-turn validation retry. This feature makes zero background OSRM Table requests; existing route watchers may still request OSRM Route after planner inputs change. The same schedule envelope and matrix are reused through the bounded retry.
- Planner schedule metadata and returned placements are ephemeral `WeakMap` state. Saved `PlanStop` JSON remains exactly `id`, `name`, `type`, optional `place_name`, `coords`, `time`, and `notes`.

### Generator time-aware scheduling and joint selection (Phases 2B-3)

The existing MCP `generate_itinerary` tool accepts optional local anchor lists:

```json
{
  "meal_anchors": ["12:00"],
  "rest_anchors": ["15:00"]
}
```

The generator keeps the existing MCP signature, `day_plans`, and stop fields. Phase 3 selects POIs and schedules their route jointly for each day, using bounded exact subset search for small pools and deterministic beam/repair search for larger pools. Required first/last content endpoints and meal/rest anchors participate in feasibility, while globally reserved entity IDs prevent duplicate content or meal entities across days. The post-prune solver pool is capped at 20 content candidates.

The optional per-day `schedule` object retains the Phase 2B timing diagnostics and adds:

- `selection_solver`: `selection-exact`, `selection-beam`, or `phase2b-fallback`.
- `candidate_count`: number of raw content candidates considered for that day before coordinate filtering and dominance/cap pruning.
- `selected_count`: number of content candidates emitted by the selection solver; fixed meal/rest anchors are excluded.
- `total_reward`: sum of the local deterministic rewards for selected content candidates.
- `dropped_reasons`: one `{stop_id, reason}` entry for each unselected content candidate. Reasons include `coordinates-missing`, `dominated`, `candidate-cap`, `time-window-overflow`, `unreachable-edge`, and `lower-reward-alternative` as applicable.

The generator builds only local Haversine matrices (`matrix_source: "haversine-fallback"`) and makes zero OSRM, web, LLM, or paid-service requests. This is independent of the planner-only OSRM request budget above. `meal_anchors: null` keeps the compatibility lunch attempt; `[]` disables meal insertion. No meal entity is fabricated when a dish/product candidate is unavailable or lacks usable coordinates.

If a required endpoint lacks usable coordinates, the matrix is invalid, or no safe selection incumbent is available, the generator returns the complete Phase 2B deterministic result rather than partial output. The fallback reports `solver: "legacy-fixed-order"`, `selection_solver: "phase2b-fallback"`, and warning `selection-fallback`, together with `coordinates-missing` or `schedule-fallback` when applicable. Anchor validation may add `invalid-anchor`, `meal-anchor-unavailable`, or `rest-anchor-unavailable`; scheduler-level omissions remain represented in `schedule.skipped` with an explicit `reason`.

The saved-itinerary schema and public MCP `generate_itinerary` signature are unchanged; all Phase 3 fields are additive under `day_plans[*].schedule` and may be ignored by existing consumers.

### Internal launch safety (private network only)

`GET /_internal/launch-policy-attestation` returns exactly
`policy_fingerprint`, `route_manifest_revision`, and
`backend_policy_revision`, loaded from the current launch-policy artifacts on every
request. The response always uses `Cache-Control: no-store`, emits no `ETag`,
`Last-Modified`, or `Expires` validators, and never returns HTTP 304, including
loader-failure responses; ordinary evidence-loader failures are sanitized as HTTP
503. The route is excluded from OpenAPI and has no public authentication or admin
gate because it is intended only for private-network launch coordination. Unlike the
admin-key-protected `/system/*` endpoints, its trust boundary is the private ingress:
every public Nginx server returns 404 for `/_internal/` descendants without proxying
them upstream. This internal attestation does not change the global `noindex` launch
state.

`GET /_internal/launch-sitemaps/{document}` serves exactly the three immutable
documents `sitemap-index.xml`, `sitemap.xml`, and `sitemap-media.xml`. Every
successful request returns stored bundle bytes and never refreshes, generates,
publishes, or repairs sitemap state during the request. An unpinned
`sitemap-index.xml` request must have an empty raw query string and loads the
active bundle. Any document may instead be pinned with the exact ASCII query
`batch=<64 lowercase hexadecimal characters>`; the two child documents require
that pinned query. Duplicate keys, extra keys, empty or uppercase revisions,
percent-encoded variants, trailing separators, and every other raw query shape
are rejected. Pinned responses include `X-Launch-Sitemap-Requested-Batch`; all
successful responses include the matching `X-Launch-Sitemap-Batch-Revision`.
Missing, malformed, unknown, unsupported, mismatched, or corrupt state is
sanitized as HTTP 503. Success and failure both use the registered
no-store/no-validator contract and never return HTTP 304. The route remains
private-network-only and does not change the global `noindex` state.

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Chat JSON request/response; body uses the bounded `ChatRequest` contract described below |
| POST | `/chat/stream` | SSE streaming chat; JSON body uses `ChatRequest` (`message`, up to 50 `user`/`assistant` history items with 8,000-character content, optional `session_id`) |

### Authentication (`/auth` — note: NOT under `/api`; nginx proxies `/auth` directly to the agent)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/request-otp` | No | Request SMS OTP |
| POST | `/auth/verify-otp` | No | Verify OTP, create session |
| POST | `/auth/check-phone` | No | Check if phone has password |
| POST | `/auth/login` | No | Login with phone + password |
| POST | `/auth/set-password` | Yes | Set/update password |
| POST | `/auth/logout` | Yes | Logout + revoke session |
| GET | `/auth/me` | Yes | Current user profile |
| PUT | `/auth/profile` | Yes | Update profile |
| POST | `/auth/avatar` | Yes | Upload avatar |
| POST | `/auth/cover` | Yes | Upload cover image |
| DELETE | `/auth/account` | Yes | Permanently delete account |
| POST | `/auth/deactivate` | Yes | Deactivate account |
| GET | `/auth/sessions` | Yes | List active sessions |
| DELETE | `/auth/sessions/{id}` | Yes | Revoke session |
| GET | `/auth/check-username/{username}` | No | Check username availability |
| GET | `/auth/login-history` | Yes | Login history |
| GET | `/auth/privacy` | Yes | Privacy settings |
| PUT | `/auth/privacy` | Yes | Update privacy settings |
| POST | `/auth/2fa/setup` | Yes | Begin TOTP enrollment (secret + QR) |
| POST | `/auth/2fa/verify-setup` | Yes | Confirm TOTP setup (recovery codes returned once) |
| POST | `/auth/2fa/disable` | Yes | Disable 2FA |
| GET | `/auth/2fa/status` | Yes | 2FA status for current user |
| POST | `/auth/2fa/verify` | No (challenge token) | Complete 2FA challenge during login |
| GET | `/auth/trusted-devices` | Yes | List trusted devices |
| DELETE | `/auth/trusted-devices/{device_id}` | Yes | Remove a trusted device |

### Social & UGC (`/api`, requires Postgres)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/posts` | Yes | Create post |
| GET | `/api/posts/{id}` | Optional | Get post |
| DELETE | `/api/posts/{id}` | Yes | Delete own post |
| PATCH | `/api/posts/{id}` | Yes | Update post |
| GET | `/api/feed` | Optional | Community feed |
| GET | `/api/feed/following` | Yes | Following feed |
| GET | `/api/posts/{id}/comments` | No | List comments |
| POST | `/api/posts/{id}/comments` | Yes | Add comment |
| POST | `/api/posts/{id}/like` | Yes | Like/unlike |
| POST | `/api/posts/{id}/bookmark` | Yes | Bookmark/unbookmark |
| GET | `/api/me/bookmarks` | Yes | List bookmarks |
| POST | `/api/posts/{id}/best-answer` | Yes | Mark best answer |
| GET | `/api/users/{id}` | No | User profile |
| GET | `/api/users/{id}/posts` | No | User's posts |
| POST | `/api/follow/{type}/{id}` | Yes | Follow user/entity |
| GET | `/api/follow/check/{type}/{id}` | Yes | Check follow status |
| GET | `/api/community/stats` | No | Community stats |
| GET | `/api/community/trending-tags` | No | Trending hashtags |
| GET | `/api/community/leaderboard` | No | Top users/entities |
| GET | `/api/entities/{id}/feed` | No | Posts about entity |
| POST | `/api/report-ugc` | Yes | Report UGC violation |
| POST | `/api/block/{id}` | Yes | Block/unblock user |
| POST | `/api/upload/image` | Yes | Upload image for post |
| POST | `/api/events/{id}/rsvp` | Yes | RSVP for event |

### Saved & Plans (Postgres only)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/saved` | Yes | List saved entities |
| POST | `/api/saved` | Yes | Save entity |
| DELETE | `/api/saved/{id}` | Yes | Unsave entity |
| POST | `/api/saved/merge` | Yes | Merge local favorites on login |
| GET | `/api/my-plans` | Yes | List personal plans |
| POST | `/api/my-plans` | Yes | Create plan |
| DELETE | `/api/my-plans/{id}` | Yes | Delete plan |
| POST | `/api/my-plans/{id}/publish` | Yes | Toggle plan public/private |
| GET | `/api/shared-plans` | No | List public plans |
| GET | `/api/shared-plans/{id}` | No | View public plan |

### Visits (Postgres only)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/me/visits` | Yes | List visit marks |
| POST | `/api/me/visits` | Yes | Mark visited/want-to-visit |
| DELETE | `/api/me/visits/{id}` | Yes | Clear visit mark |
| GET | `/api/me/visits/check/{id}` | Yes | Check visit status |

### Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/notifications` | Yes | Paginated notifications |
| GET | `/api/notifications/stream` | Yes | SSE real-time notifications |
| POST | `/api/notifications/read-all` | Yes | Mark all read |
| POST | `/api/notifications/{id}/read` | Yes | Mark one read |
| GET | `/api/notification-preferences` | Yes | Get preferences |
| PUT | `/api/notification-preferences` | Yes | Update preferences |

### SEO (no auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sitemap.xml` | Main sitemap (Nuxt-owned root SEO response) |
| GET | `/sitemap-media.xml` | Media sitemap |
| GET | `/sitemap-index.xml` | Sitemap index |
| GET | `/robots.txt` | Robots directives |
| GET | `/seo/jsonld/site` | Organization + WebSite schema |
| GET | `/seo/jsonld/{entity_id}` | Entity JSON-LD + FAQ |
| GET | `/seo/jsonld/area/{slug}` | TouristDestination schema |
| GET | `/seo/jsonld/itinerary/{id}` | TouristTrip schema |
| GET | `/seo/jsonld/collection/{type}` | ItemList schema |

The four root SEO documents (`/robots.txt`, `/sitemap.xml`, `/sitemap-media.xml`,
and `/sitemap-index.xml`) are owned by Nuxt server routes and are routed to Nuxt
by the exclusive Nginx ingress. FastAPI is not a public owner of these paths.
Responses are `no-store` and preserve the launch policy/evidence headers. The
site-wide global `noindex` gate remains active, so the Nuxt responses stay in
their closed/empty form until selective indexing is explicitly admitted.

The immutable index, main, and media bytes used for launch evidence remain
available only through the internal launch-sitemap route and its exact query
contract; that private route is not a second public sitemap owner.

### Admin (`/admin`, requires admin key; exposed publicly as `/admin-api/*` via nginx proxy)

Organized by function — full list of 90+ admin endpoints:

**Entity CRUD:** `GET|POST|PUT|DELETE /admin/entities[/{id}]`, images, history, bulk-delete, unclassified, place assignment.

**Itinerary CRUD:** `GET|POST|PUT|DELETE /admin/itineraries[/{id}]`.

**Relationships:** `POST|DELETE /admin/relationships`, bulk create.

**Data Quality:** summary, review, apply (dry-run/commit), history, rollback.

**Image Suggestions:** list, detail, create-batch, approve, reject.

**Content Moderation:** queue, approve, reject, batch, notes, stats.

**User Management:** list, ban, unban, role change.

**Reports:** list, resolve, dismiss, bulk action, info-reports.

**Analytics:** overview, badge-counts, dashboard-alerts, cost-overview, AI triage.

**Site Settings:** get, get-by-category, update, bulk-update, reset.

**Maintenance:** trigger-learn, backup-trigger, notification-cleanup, media list, audit-log, export, sources, stats.

### Health & System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Quick health (no external calls) |
| GET | `/health/deep` | No | Deep health (LLM API check) |
| POST | `/reload` | Admin | Hot-reload knowledge data |
| GET | `/metrics` | Admin (all envs) | Prometheus metrics (`X-Admin-Key`; 404 without it — gated in dev too) |
| GET | `/system/*` | Admin (all envs) | ~25 monitoring endpoints (logs, errors, scheduler, circuit-breakers, costs, etc.) |

---

## Validation Gates

The data contract is healthy when:

- No relationship references a missing entity ID (0 dangling).
- Entities with location data expose `coordinates`.
- `attributes` is always an object when present.
- Non-place summary coverage at 100%.
- `validate_data.py` exits with code 0.
- Entity IDs contain no spaces or control characters.
- Phone numbers match Vietnamese format (0[2-9]...).
- `source` URLs are valid when present.

## Auth Model

- **Public endpoints:** No auth required (read-only data).
- **User endpoints:** Bearer token from `/auth/verify-otp` or `/auth/login`.
- **Admin endpoints:** `X-Admin-Key` header matching `ADMIN_API_KEY` env var.
- **System endpoints:** Gated by `gate_internal_endpoints` middleware (404 without admin key — enforced in ALL environments, not just prod; `agent/server.py` `gate_internal_endpoints`).
- **UGC endpoints:** Require Postgres — return 503 on SQLite (`_require_pg` guard).
