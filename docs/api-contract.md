# VinhLong360 API Contract

Date: 2026-06-12 (updated 2026-06-27)
Status: Production — reflects actual endpoints after GĐ13

This contract defines the data shapes and API endpoints shared between the FastAPI backend (`agent/`) and the Nuxt frontend (`web-nuxt/`).

## Data Shapes

### Entity

```json
{
  "id": "entity-id",
  "name": "Display name",
  "type": "attraction|place|dish|drink|product|itinerary|facility|organization|accommodation|experience|craft_village|event",
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
- `coordinates` is canonical (`[lat, lng]`). `coords` is legacy-only.
- `coords_approximate` — true when coordinates are derived from ward centroid (not exact).
- `images` — array of URLs, default `[]`. First element is the cover image.
- `source` — array of `{title, url}` objects (may also be a plain string for legacy data).
- `season` — `months` (array 1..12) and optional `peak` subset.
- `area` — province-level bucket: `vinh-long`, `ben-tre`, or `tra-vinh`.
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
| GET | `/api/entities/{id}` | Entity detail with relationships + quality score |
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

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Chat (JSON request/response) |
| GET | `/chat/stream` | SSE streaming chat |

### Authentication (`/api/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/request-otp` | No | Request SMS OTP |
| POST | `/api/auth/verify-otp` | No | Verify OTP, create session |
| POST | `/api/auth/check-phone` | No | Check if phone has password |
| POST | `/api/auth/login` | No | Login with phone + password |
| POST | `/api/auth/set-password` | Yes | Set/update password |
| POST | `/api/auth/logout` | Yes | Logout + revoke session |
| GET | `/api/auth/me` | Yes | Current user profile |
| PUT | `/api/auth/profile` | Yes | Update profile |
| POST | `/api/auth/avatar` | Yes | Upload avatar |
| POST | `/api/auth/cover` | Yes | Upload cover image |
| DELETE | `/api/auth/account` | Yes | Permanently delete account |
| POST | `/api/auth/deactivate` | Yes | Deactivate account |
| GET | `/api/auth/sessions` | Yes | List active sessions |
| DELETE | `/api/auth/sessions/{id}` | Yes | Revoke session |
| GET | `/api/auth/check-username/{username}` | No | Check username availability |
| GET | `/api/auth/login-history` | Yes | Login history |
| GET | `/api/auth/privacy` | Yes | Privacy settings |
| PUT | `/api/auth/privacy` | Yes | Update privacy settings |

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
| GET | `/sitemap.xml` | Entity sitemap |
| GET | `/sitemap-media.xml` | Media sitemap |
| GET | `/sitemap-index.xml` | Sitemap index |
| GET | `/robots.txt` | Robots directives |
| GET | `/seo/jsonld/site` | Organization + WebSite schema |
| GET | `/seo/jsonld/{entity_id}` | Entity JSON-LD + FAQ |
| GET | `/seo/jsonld/area/{slug}` | TouristDestination schema |
| GET | `/seo/jsonld/itinerary/{id}` | TouristTrip schema |
| GET | `/seo/jsonld/collection/{type}` | ItemList schema |

### Admin (`/api/admin`, requires admin key)

Organized by function — full list of 90+ admin endpoints:

**Entity CRUD:** `GET|POST|PUT|DELETE /api/admin/entities[/{id}]`, images, history, bulk-delete, unclassified, place assignment.

**Itinerary CRUD:** `GET|POST|PUT|DELETE /api/admin/itineraries[/{id}]`.

**Relationships:** `POST|DELETE /api/admin/relationships`, bulk create.

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
| GET | `/metrics` | Admin (prod) | Prometheus metrics |
| GET | `/system/*` | Admin (prod) | ~25 monitoring endpoints (logs, errors, scheduler, circuit-breakers, costs, etc.) |

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
- **User endpoints:** Bearer token from `/api/auth/verify-otp` or `/api/auth/login`.
- **Admin endpoints:** `X-Admin-Key` header matching `ADMIN_API_KEY` env var.
- **System endpoints:** Gated by `gate_internal_endpoints` middleware (404 in prod without admin key).
- **UGC endpoints:** Require Postgres — return 503 on SQLite (`_require_pg` guard).
