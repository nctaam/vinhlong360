# VinhLong360 API Contract

> **STATUS (2026-07-07): active — đã truth-sync.** Type enum synced to the 18-type registry; auth/admin path prefixes corrected to the actual routes (`/auth/*`, `/admin/*`); 2FA/trusted-devices endpoints added.

Date: 2026-06-12 (updated 2026-07-17)
Status: Production — reflects actual endpoints

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
