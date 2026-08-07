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
| GET | `/api/me/activity` | Yes | Dòng hoạt động của chính user (post + comment + like đã trộn). Query: `limit` (1–100, mặc định 30), `offset` (≥0). Trả `{ items: [{ action, ref_type, ref_id, content, type, created_at }], has_more }`. `ref_type` luôn là `post` nên client dựng được link; comment tham chiếu `post_id` chứ không phải id của chính comment. Handler nằm ở `agent/social.py` — chỉ một bản duy nhất, sau guard `require_pg` |
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

---

<!-- ROUTE-APPENDIX:START — sinh bởi scripts/gen_route_appendix.py, đừng sửa tay -->

## Phụ lục — bản đồ route đầy đủ

Sinh tự động từ AST của `agent/` bằng `scripts/gen_route_appendix.py` (399 route trong 12 module). Mọi thông tin dưới đây lấy trực tiếp từ mã nguồn: method, path đã ghép prefix của `APIRouter`, tên handler, và dòng đầu docstring nếu handler có. Ô mô tả trống nghĩa là **code chưa có docstring** — đó là chỗ đáng viết tiếp, không phải chỗ để đoán.

Các mục ở phần trên tài liệu mới là hợp đồng có ràng buộc (shape dữ liệu, quy tắc, ví dụ). Phụ lục này chỉ bảo đảm **không route nào tồn tại mà tài liệu không biết** — đó là điều R20.5b đo.

### `agent/achievements.py` (1 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/api/me/achievements` | `get_my_achievements` |  |

### `agent/admin.py` (132 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/admin/activity-feed` | `activity_feed` | 10 admin actions gần nhất từ audit JSONL. |
| POST | `/admin/ai/triage` | `ai_triage` | On-demand: trợ lý LLM gợi ý ≤3 việc quản trị ưu tiên từ tình hình hiện tại. |
| GET | `/admin/analytics-overview` | `analytics_overview` | GĐ9.6: gói số liệu cho trang admin Analytics (1 call, đã auth qua require_admin). |
| GET | `/admin/announcements` | `list_announcements` |  |
| POST | `/admin/announcements` | `create_announcement` |  |
| DELETE | `/admin/announcements/{announcement_id}` | `delete_announcement` |  |
| PUT | `/admin/announcements/{announcement_id}` | `update_announcement` |  |
| GET | `/admin/appeals` | `list_appeals` |  |
| POST | `/admin/appeals/{appeal_id}/approve` | `approve_appeal` |  |
| POST | `/admin/appeals/{appeal_id}/reject` | `reject_appeal` |  |
| GET | `/admin/audit-log` | `get_audit_log` | P2-7: nhật ký thao tác admin (mutation), mới nhất trước. Hỗ trợ filter server-side. |
| GET | `/admin/backup-status` | `backup_status` | B5c: route mỏng bọc _latest_backup_info() — không thêm logic mới. |
| POST | `/admin/backup-trigger` | `trigger_backup` | B5c: trigger manual backup from admin UI. |
| GET | `/admin/badge-counts` | `badge_counts` | Lightweight counts cho sidebar badges — cached 60s to avoid repeated DB+JSONL parsing. |
| GET | `/admin/claims` | `list_claims` | U-30: List entity claims for admin review. |
| POST | `/admin/claims/{claim_id}/approve` | `approve_claim` | U-30: Approve an entity claim. |
| POST | `/admin/claims/{claim_id}/reject` | `reject_claim` | U-30: Reject an entity claim with optional reason. |
| POST | `/admin/cleanup-orphan-refs` | `admin_cleanup_orphan_entity_refs` | Remove UGC records referencing entity IDs that no longer exist in knowledge base. |
| GET | `/admin/collections` | `list_collections` |  |
| POST | `/admin/collections` | `create_collection` |  |
| DELETE | `/admin/collections/{collection_id}` | `delete_collection` |  |
| PUT | `/admin/collections/{collection_id}` | `update_collection` |  |
| GET | `/admin/comments` | `admin_list_comments` | List comments for admin review with optional search and post filter. |
| DELETE | `/admin/comments/{comment_id}` | `admin_delete_comment` | Admin force-delete a comment. |
| GET | `/admin/completeness` | `completeness_overview` | Tổng quan hoàn thiện: % entities có source+images+placeId+summary. |
| GET | `/admin/completeness/details` | `completeness_details` | Per-entity completeness scores with filter. |
| GET | `/admin/contact-funnel` | `contact_funnel` | Thống kê click vào thông tin liên hệ — zalo/phone/website/map. |
| GET | `/admin/contact-funnel/export` | `contact_funnel_export` | Export contact funnel dạng CSV. |
| GET | `/admin/content-stats` | `content_stats` |  |
| GET | `/admin/content/search` | `admin_content_search` | Admin search across posts and comments by keyword. |
| GET | `/admin/cost-overview` | `cost_overview` | Bảng chi phí: chi phí LLM (cost_tracker) + ngân sách agent tự động (cap/dùng/còn). |
| GET | `/admin/dashboard-alerts` | `dashboard_alerts` | Priority-sorted alerts cho admin dashboard. |
| POST | `/admin/data-quality/apply` | `data_quality_apply` |  |
| POST | `/admin/data-quality/decision` | `data_quality_decision` |  |
| GET | `/admin/data-quality/history` | `data_quality_history` |  |
| GET | `/admin/data-quality/review` | `data_quality_review` |  |
| POST | `/admin/data-quality/rollback/{batch_id}` | `data_quality_rollback` |  |
| GET | `/admin/data-quality/summary` | `data_quality_summary` |  |
| GET | `/admin/entities` | `list_entities` | Danh sách entities với filter — đọc từ database. |
| POST | `/admin/entities` | `create_entity` | Tạo entity mới. |
| POST | `/admin/entities/bulk-delete` | `bulk_delete` | Xóa nhiều entities cùng lúc. |
| POST | `/admin/entities/bulk-place` | `bulk_assign_place` |  |
| GET | `/admin/entities/check-duplicate` | `check_duplicate` | Kiểm tra entity trùng tên (substring, case-insensitive + B2c: không phân biệt dấu). |
| GET | `/admin/entities/places` | `list_places` | Danh sách xã/phường cho dropdown. |
| DELETE | `/admin/entities/{entity_id}` | `delete_entity` | Xóa entity. |
| GET | `/admin/entities/{entity_id}` | `get_entity` | Chi tiết 1 entity. |
| PUT | `/admin/entities/{entity_id}` | `update_entity` | Cập nhật entity. |
| GET | `/admin/entities/{entity_id}/history` | `get_entity_history` | Lịch sử thay đổi entity. |
| POST | `/admin/entities/{entity_id}/images` | `add_entity_image_url` | GĐ8.4: thêm ảnh entity theo URL (chỉ nguồn cấp phép — B6). |
| POST | `/admin/entities/{entity_id}/images/upload` | `upload_entity_image` | GĐ8.4: upload file ảnh → WebP 3 cỡ → R2 (fallback đĩa) → entity.images. |
| DELETE | `/admin/entities/{entity_id}/images/{idx}` | `remove_entity_image` | Gỡ ảnh thứ idx khỏi entity.images (không xoá file R2 — tránh mất ảnh dùng chung). |
| POST | `/admin/entities/{entity_id}/place` | `assign_place` | Gán (hoặc gỡ) xã/phường cho 1 entity. Validate place_id là place thật (chống gán bừa). |
| GET | `/admin/entity-completeness` | `entity_completeness` | % điền từng trường + entity thiếu nhiều nhất — dashboard làm giàu dữ liệu theo nhóm. |
| GET | `/admin/entity-kinds` | `entity_kinds` | Đếm entity theo danh mục chủ (kind) — lớp gộp phái sinh trên 17 type. |
| GET | `/admin/entity-schema` | `get_entity_schema` | Content-model registry: per-type fields + owner-category (kind) mapping. |
| POST | `/admin/export` | `export_data` | Export toàn bộ entities từ DB — streaming JSON để không OOM. |
| GET | `/admin/export/posts` | `export_posts_csv` | CSV export of posts with author/entity info. |
| GET | `/admin/export/users` | `export_users_csv` | CSV export of all users with stats. |
| GET | `/admin/featured` | `list_featured` |  |
| POST | `/admin/featured/{entity_id}` | `toggle_featured` |  |
| GET | `/admin/image-suggestions` | `list_image_suggestions` | Liệt kê ứng viên ảnh chờ duyệt (mặc định: tất cả; lọc theo status/entity). |
| POST | `/admin/image-suggestions/create-batch` | `create_image_suggestion_batch` | Nhận lô ứng viên từ script ingest (mode=queue). KHÔNG publish — chỉ xếp hàng chờ duyệt. |
| GET | `/admin/image-suggestions/{suggestion_id}` | `get_image_suggestion` | Chi tiết 1 ứng viên ảnh (kèm tên entity để review). |
| POST | `/admin/image-suggestions/{suggestion_id}/approve` | `approve_image_suggestion` | Duyệt 1 ứng viên: tải ảnh → WebP 3 cỡ → R2 → gắn vào entity.images + lưu |
| POST | `/admin/image-suggestions/{suggestion_id}/reject` | `reject_image_suggestion` | Từ chối 1 ứng viên (ghi lý do). Không tải/không upload gì. |
| GET | `/admin/info-reports` | `get_info_reports` | Liệt kê báo-sai/báo cáo ẩn danh (reports.jsonl), mới nhất trước. Admin tự xử lý |
| POST | `/admin/info-reports/action` | `info_report_action` | Đổi trạng thái 1 báo-sai (resolve/dismiss/open) — ghi lại reports.jsonl atomic. |
| GET | `/admin/itineraries` | `list_itineraries_admin` |  |
| POST | `/admin/itineraries` | `create_itinerary` |  |
| DELETE | `/admin/itineraries/{itin_id}` | `delete_itinerary` |  |
| GET | `/admin/itineraries/{itin_id}` | `get_itinerary_admin` |  |
| PUT | `/admin/itineraries/{itin_id}` | `update_itinerary` |  |
| GET | `/admin/llm-config` | `admin_get_llm_config` | Current LLM configuration (API key masked). |
| PUT | `/admin/llm-config` | `admin_update_llm_config` | Update LLM config. Validates with a test API call before applying. |
| POST | `/admin/llm-config/reset` | `admin_reset_llm_config` | Reset LLM config to environment variables. |
| GET | `/admin/media` | `media_gallery` | B6a: Central media gallery — cached extraction, avoids re-scanning all entities per page. |
| POST | `/admin/moderation/batch` | `batch_moderation` |  |
| GET | `/admin/moderation/queue` | `moderation_queue` |  |
| GET | `/admin/moderation/stats` | `moderation_stats` |  |
| POST | `/admin/moderation/{post_id}/approve` | `approve_post` |  |
| GET | `/admin/moderation/{post_id}/history` | `moderation_history` | Admin: view full moderation action timeline for a specific post. |
| POST | `/admin/moderation/{post_id}/note` | `add_moderation_note` | B3d: Add internal admin note (not visible to poster). |
| GET | `/admin/moderation/{post_id}/notes` | `get_moderation_notes` |  |
| POST | `/admin/moderation/{post_id}/reject` | `reject_post` |  |
| POST | `/admin/notifications/cleanup` | `admin_cleanup_notifications` | Delete read notifications older than N days. |
| GET | `/admin/ops-summary` | `ops_summary` | Ops cockpit snapshot: lightweight, read-only, no background jobs. |
| GET | `/admin/posts/{post_id}` | `admin_post_detail` | Full post detail with comments for admin review. |
| POST | `/admin/posts/{post_id}/feature` | `feature_post` | Admin: toggle feature a post at the top of its entity page. |
| DELETE | `/admin/posts/{post_id}/response` | `delete_review_response` |  |
| GET | `/admin/posts/{post_id}/response` | `get_review_response` | Get the admin response for a review post. |
| POST | `/admin/posts/{post_id}/response` | `admin_review_response` | Admin/business reply to a review — one response per review (UNIQUE). |
| GET | `/admin/provisional` | `list_provisional_entities` | Liệt kê các entity tự học CHƯA kiểm chứng (chờ duyệt). |
| POST | `/admin/provisional/{entity_id}/approve` | `approve_provisional` | Duyệt 1 entity provisional → verified (tin cậy). |
| POST | `/admin/provisional/{entity_id}/reject` | `reject_provisional` | Từ chối + xóa 1 entity provisional khỏi KB. |
| GET | `/admin/qa-queue` | `qa_queue` | Admin queue: questions chưa có best answer hoặc chưa có reply. |
| POST | `/admin/qa-queue/{post_id}/set-best-answer` | `qa_set_best_answer` | Admin override: set best_answer_id cho 1 question. |
| DELETE | `/admin/relationships` | `delete_relationship` |  |
| POST | `/admin/relationships` | `add_relationship` |  |
| POST | `/admin/relationships/bulk` | `add_relationships_bulk` | B7b: thêm nhiều quan hệ cùng lúc. |
| GET | `/admin/reports` | `get_reports` |  |
| POST | `/admin/reports/bulk` | `bulk_report_action` |  |
| POST | `/admin/reports/{report_id}/dismiss` | `dismiss_report` |  |
| POST | `/admin/reports/{report_id}/resolve` | `resolve_report` |  |
| GET | `/admin/search-analytics` | `search_analytics` |  |
| GET | `/admin/site-settings` | `admin_get_all_settings` | All settings grouped by category (for admin overview). |
| GET | `/admin/site-settings-history` | `admin_site_settings_history` |  |
| POST | `/admin/site-settings-history/{history_id}/rollback` | `admin_site_settings_rollback` |  |
| POST | `/admin/site-settings/bulk` | `admin_bulk_update_settings` | Batch update multiple settings at once. |
| POST | `/admin/site-settings/reset/{category}` | `admin_reset_category` | Reset all settings in a category to their defaults. |
| GET | `/admin/site-settings/{category}` | `admin_get_settings_by_category` | Settings for a specific category (for admin editor page). |
| PUT | `/admin/site-settings/{key:path}` | `admin_update_setting` | Update a single setting value. |
| GET | `/admin/sources` | `list_sources` | Liệt kê tất cả nguồn dữ liệu. |
| GET | `/admin/stale-queue` | `stale_queue` | Danh sách entity cũ/thiếu thông tin — admin review queue. |
| POST | `/admin/stale-queue/{entity_id}/mark-reviewed` | `stale_mark_reviewed` | Đánh dấu entity đã được admin xem xét — ghi timestamp vào attributes. |
| GET | `/admin/stats` | `admin_stats` | Thống kê chi tiết cho admin. |
| GET | `/admin/system-health` | `system_health` |  |
| POST | `/admin/trigger-learn` | `trigger_learn` | Trigger 1 vòng auto-learn (chạy background). |
| GET | `/admin/unclassified` | `list_unclassified` | Entity nội dung CHƯA gán xã/phường (placeId rỗng) — để admin gán đúng (lấp nợ placeId). |
| GET | `/admin/user-engagement` | `user_engagement_stats` |  |
| GET | `/admin/user-growth` | `user_growth` |  |
| GET | `/admin/users` | `list_users` |  |
| POST | `/admin/users/bulk-ban` | `bulk_ban_users` |  |
| POST | `/admin/users/bulk-unban` | `bulk_unban_users` |  |
| GET | `/admin/users/{user_id}` | `admin_user_detail` | Comprehensive user detail for admin panel. |
| POST | `/admin/users/{user_id}/ban` | `ban_user` |  |
| GET | `/admin/users/{user_id}/mutes` | `admin_user_mutes` |  |
| GET | `/admin/users/{user_id}/notes` | `get_user_notes` | Admin: list internal notes for a user. |
| POST | `/admin/users/{user_id}/notes` | `add_user_note` | Admin: add internal note to a user profile. |
| DELETE | `/admin/users/{user_id}/notes/{note_id}` | `delete_user_note` | Admin: delete an internal note. |
| GET | `/admin/users/{user_id}/reactions` | `admin_user_reactions` |  |
| POST | `/admin/users/{user_id}/role` | `set_user_role` |  |
| POST | `/admin/users/{user_id}/unban` | `unban_user` |  |

### `agent/auth.py` (30 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| POST | `/auth/2fa/disable` | `twofa_disable` |  |
| POST | `/auth/2fa/setup` | `twofa_setup` |  |
| GET | `/auth/2fa/status` | `twofa_status` |  |
| POST | `/auth/2fa/verify` | `twofa_verify` |  |
| POST | `/auth/2fa/verify-setup` | `twofa_verify_setup` |  |
| DELETE | `/auth/account` | `delete_account` |  |
| POST | `/auth/avatar` | `upload_avatar` |  |
| POST | `/auth/check-phone` | `check_phone` |  |
| GET | `/auth/check-username/{username}` | `check_username` |  |
| GET | `/auth/consent-history` | `consent_history` |  |
| POST | `/auth/cover` | `upload_cover` |  |
| GET | `/auth/csrf` | `get_csrf` |  |
| POST | `/auth/deactivate` | `deactivate_account` |  |
| GET | `/auth/export-data` | `export_user_data` |  |
| POST | `/auth/login` | `login_password` |  |
| GET | `/auth/login-history` | `get_login_history` |  |
| POST | `/auth/logout` | `logout` |  |
| GET | `/auth/me` | `get_me` |  |
| GET | `/auth/privacy` | `get_privacy` |  |
| PUT | `/auth/privacy` | `update_privacy` |  |
| PUT | `/auth/profile` | `update_profile` |  |
| POST | `/auth/refresh` | `refresh_token` | Rotate session token — issue new token, revoke old. Reduces compromise window. |
| POST | `/auth/request-otp` | `request_otp` |  |
| POST | `/auth/reset-password-otp` | `reset_password_otp` |  |
| GET | `/auth/sessions` | `list_sessions` |  |
| DELETE | `/auth/sessions/{session_id}` | `revoke_session` |  |
| POST | `/auth/set-password` | `set_password` |  |
| GET | `/auth/trusted-devices` | `list_trusted_devices` |  |
| DELETE | `/auth/trusted-devices/{device_id}` | `delete_trusted_device` |  |
| POST | `/auth/verify-otp` | `verify_otp` |  |

### `agent/launch_policy_api.py` (2 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/_internal/launch-policy-attestation` | `launch_policy_attestation` |  |
| GET | `/_internal/launch-sitemaps/{document}` | `launch_sitemap_document` |  |

### `agent/notifications.py` (20 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| POST | `/api/block/{blocked_id}` | `toggle_block` | Bật/tắt chặn một user, trả về trạng thái blocked mới. |
| GET | `/api/blocked-users` | `list_blocked_users` | Liệt kê user bị người dùng đang đăng nhập chặn, phân trang theo page/limit. |
| GET | `/api/events/{entity_id}/rsvp` | `get_rsvp` | Trả về số RSVP của một entity và cờ going của người dùng hiện tại nếu đã đăng nhập. |
| POST | `/api/events/{entity_id}/rsvp` | `toggle_rsvp` | Bật/tắt RSVP cho một entity kiểu 'event', trả về going và tổng số RSVP của sự kiện. |
| GET | `/api/follow/check/{target_type}/{target_id}` | `check_follow` | Kiểm tra người dùng đang đăng nhập có đang follow target hay không. |
| POST | `/api/follow/{target_type}/{target_id}` | `toggle_follow` | Bật/tắt theo dõi một user hoặc entity, trả về trạng thái follow mới. |
| GET | `/api/followers/count/{target_type}/{target_id}` | `get_follower_count` | Đếm số follower của một user hoặc entity; không yêu cầu đăng nhập. |
| GET | `/api/following` | `get_following` | Liệt kê user/entity mà người dùng đang đăng nhập theo dõi, kèm total và has_more. |
| POST | `/api/mute/{muted_id}` | `toggle_mute` | Bật/tắt tắt tiếng một user bằng cách thêm/xoá dòng trong bảng user_mutes. |
| GET | `/api/muted-users` | `list_muted_users` | Liệt kê user bị người dùng đang đăng nhập tắt tiếng, phân trang theo page/limit. |
| GET | `/api/notification-preferences` | `get_notification_preferences` | Trả về 5 cờ tuỳ chọn thông báo của người dùng; chưa có bản ghi thì trả mặc định bật hết. |
| PUT | `/api/notification-preferences` | `update_notification_preferences` | Cập nhật các cờ tuỳ chọn thông báo được gửi lên; field để None thì bỏ qua. |
| DELETE | `/api/notifications` | `clear_all_notifications` | Xoá toàn bộ thông báo của người dùng đang đăng nhập, trả về số dòng đếm trước khi xoá. |
| GET | `/api/notifications` | `get_notifications` | Trả về thông báo của người dùng đang đăng nhập kèm số lượng chưa đọc. |
| POST | `/api/notifications/read-all` | `mark_all_read` | Đặt is_read = TRUE cho mọi thông báo chưa đọc của người dùng đang đăng nhập. |
| GET | `/api/notifications/stream` | `notification_stream` | Mở luồng SSE thông báo thời gian thực cho một phiên đăng nhập còn hạn. |
| GET | `/api/notifications/unread-count` | `unread_count` | Đếm số thông báo có is_read = FALSE của người dùng đang đăng nhập. |
| DELETE | `/api/notifications/{notif_id}` | `delete_notification` | Xoá một thông báo theo id, chỉ khi thông báo đó thuộc về người dùng đang đăng nhập. |
| POST | `/api/notifications/{notif_id}/read` | `mark_notification_read` | Đặt is_read = TRUE cho một thông báo thuộc về người dùng đang đăng nhập. |
| POST | `/api/report-ugc` | `create_report` | Ghi một báo cáo kiểm duyệt vào bảng reports cho target post/comment/user/entity. |

### `agent/plans.py` (7 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/api/my-plans` | `list_plans` |  |
| POST | `/api/my-plans` | `add_plan` |  |
| POST | `/api/my-plans/merge` | `merge_plans` |  |
| DELETE | `/api/my-plans/{plan_id}` | `remove_plan` |  |
| POST | `/api/my-plans/{plan_id}/publish` | `publish_plan` |  |
| GET | `/api/shared-plans` | `list_shared` |  |
| GET | `/api/shared-plans/{plan_id}` | `get_shared` |  |

### `agent/public_api.py` (47 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/api/announcements` | `list_active_announcements` | Active announcements for display to users. |
| GET | `/api/areas` | `list_areas` | LUÔN trả về danh sách rỗng ở bản hiện tại — endpoint đang hỏng, không phải theo thiết kế. |
| GET | `/api/autocomplete` | `autocomplete` | Lightweight typeahead for entity name search. |
| GET | `/api/collections` | `list_public_collections` | Trả các collection đã publish theo sort_order, entity_ids đã lọc còn entity công khai. |
| GET | `/api/collections/{slug}` | `get_collection_by_slug` | Trả một collection đã publish theo slug, kèm entities đã lọc theo quyền công khai. |
| GET | `/api/entities` | `list_entities` | Trả danh sách entity công khai đã phân trang kèm tổng số, lọc theo type/area/q/month và sort. |
| GET | `/api/entities/compare` | `compare_entities` | Side-by-side entity comparison. Pass comma-separated IDs (max 5). |
| GET | `/api/entities/map` | `entities_map_search` | Entities within a bounding box for map display. |
| GET | `/api/entities/popular` | `popular_entities` | Popular entities by review count + rating. Filter by type and area. |
| GET | `/api/entities/search` | `entity_search` | Entity search with type, area, image, and sort filters. |
| GET | `/api/entities/trending` | `entities_trending` | Entities with most activity (posts+reviews+bookmarks) in recent days. |
| GET | `/api/entities/{entity_id}` | `get_entity` | Trả chi tiết một entity công khai kèm quan hệ, quality, source_freshness và practical_facts. |
| POST | `/api/entities/{entity_id}/claim` | `submit_entity_claim` | Nhận yêu cầu xác nhận quyền sở hữu một entity từ user đăng nhập, ghi vào bảng entity_claims. |
| GET | `/api/entities/{entity_id}/gallery` | `get_entity_gallery` | Trả danh sách mô tả ảnh biên tập có thể render của một entity công khai. |
| GET | `/api/entities/{entity_id}/nearby` | `get_nearby_entities` | Trả entity công khai nằm trong bán kính radius_km quanh một entity, sắp theo khoảng cách. |
| GET | `/api/entities/{entity_id}/qa` | `get_entity_qa` | U-09: Surface Q&A posts for an entity with accepted answer resolution. |
| GET | `/api/entities/{entity_id}/rating-breakdown` | `get_entity_rating_breakdown` | 5-star rating distribution for an entity. |
| GET | `/api/entities/{entity_id}/relationships` | `get_entity_relationships` | Trả quan hệ của một entity theo trang, đã loại quan hệ trỏ tới entity không công khai. |
| POST | `/api/entities/{entity_id}/report-stale` | `report_stale_field` | U-02: Report a specific field as stale/incorrect on an entity. |
| GET | `/api/entities/{entity_id}/review-stats` | `get_review_stats` | Trả thống kê review của entity: điểm trung bình, số lượng, phân bố sao và từ khoá hay nhắc. |
| GET | `/api/entities/{entity_id}/reviews` | `get_entity_reviews` | Trả review của một entity theo trang kèm tổng, rating trung bình và phân bố sao. |
| GET | `/api/entities/{entity_id}/similar` | `get_similar_entities` | U-29: Rule-based similar entity recommendations (no ML). |
| GET | `/api/entities/{entity_id}/stats` | `get_entity_stats` | Trả số đếm cộng đồng của một entity: review, rating trung bình, post, bookmark, follower. |
| POST | `/api/entities/{entity_id}/view-contact` | `track_contact_view` | Ghi một lượt xem thông tin liên hệ (zalo/phone/website/map) của entity vào contact_views.jsonl. |
| GET | `/api/entity-types` | `entity_types` | Trả số lượng entity theo từng giá trị cột type kèm tổng cộng, sắp giảm dần theo count. |
| GET | `/api/events` | `list_events` | Trả entity type=event công khai sắp theo ngày bắt đầu, mặc định ẩn sự kiện đã qua. |
| GET | `/api/facilities` | `list_facilities` | GĐ13.4: danh bạ hành chính — cơ quan công vụ (UBND/công an/...) theo xã/phường. |
| GET | `/api/featured` | `get_featured_entities` | Trả tối đa 20 entity công khai được ghim trong bảng featured_entities, sắp theo sort_order. |
| GET | `/api/feed/new-since` | `feed_new_since` | Mới cập nhật/tạo từ `since` — entities + posts (public only). |
| GET | `/api/health` | `api_health` | Trả nguyên kết quả của server.health() dưới prefix /api, kèm Cache-Control: no-store. |
| GET | `/api/homepage` | `homepage_curated` | Curated homepage: smart-scored, type/area diverse, seasonal-aware, deduped. |
| GET | `/api/itineraries` | `list_itineraries` | Trả danh sách lịch trình theo trang, đã loại các stop trỏ tới entity không công khai. |
| POST | `/api/itineraries/optimize-order` | `optimize_itinerary_order` | Sắp lại thứ tự điểm dừng của lịch trình; có trường schedule thì chạy nhánh xếp lịch theo giờ. |
| GET | `/api/itineraries/{itin_id}` | `get_itinerary` | Trả một lịch trình theo id, stop đã lọc theo entity công khai và bổ sung dữ liệu entity. |
| GET | `/api/map-pins` | `get_map_pins` | Trả pin bản đồ (lat/lng, emoji, màu theo type, rating, place) của entity công khai có toạ độ. |
| POST | `/api/me/events` | `track_user_event` | Ghi nhận một sự kiện trải nghiệm của user đang đăng nhập vào log sự kiện (HTTP 202). |
| GET | `/api/me/insights` | `get_my_insights` | Hồ sơ quan tâm của user: interests, areas, types, recent_intents, next_actions, confidence, signal_count. |
| GET | `/api/me/recommendations/contextual` | `contextual_recommendations` | Trả entity gợi ý kèm lý do ngắn cho một context trang của user đang đăng nhập. |
| GET | `/api/places` | `list_places` | Trả entity type=place công khai (id, name, area, level), lọc tuỳ chọn theo area. |
| GET | `/api/places/{place_id}/day-plan` | `place_day_plan` | Gợi ý lịch trình 1 ngày cho xã/phường — đa dạng loại hình, sắp theo khoảng cách. |
| GET | `/api/places/{place_id}/overview` | `place_overview` | Trang hub 1 xã/phường: danh bạ hành chính + du lịch + lưu trú + sản phẩm. |
| POST | `/api/report` | `submit_report` | GĐ13.6f: tiếp nhận báo-sai (facility/entity) & báo cáo nội dung (post/comment). |
| GET | `/api/search` | `search` | Tìm hợp nhất entity + bài viết + người dùng cho một truy vấn, kèm suggestions và totals. |
| GET | `/api/site-settings` | `get_site_settings` | Public flat {key: value} dict of all site settings (cached 60s). |
| GET | `/api/stats` | `public_stats` | Trả nguyên vẹn kết quả db.stats() làm thống kê tổng hợp công khai, cache 5 phút. |
| GET | `/api/transparency` | `transparency_report` | ND 147/2024 transparency: moderation policy, contact, takedown SLA. |
| GET | `/api/users/{user_id}/engagement` | `user_engagement_stats` | Lightweight engagement stats for a user profile card. |

### `agent/saved.py` (4 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/api/saved` | `list_saved` | Trả về danh sách entity đã lưu của người dùng đăng nhập, mới nhất trước, tối đa 2000 mục. |
| POST | `/api/saved` | `add_saved` | Lưu một entity vào danh sách của người dùng; nếu đã lưu thì ghi đè snapshot (upsert). |
| POST | `/api/saved/merge` | `merge_saved` | Gộp danh sách lưu từ thiết bị vào tài khoản, rồi trả về toàn bộ danh sách sau khi gộp. |
| DELETE | `/api/saved/{entity_id}` | `remove_saved` | Xoá một entity khỏi danh sách đã lưu của người dùng theo `entity_id`. |

### `agent/seo.py` (8 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/favicon.ico` | `favicon` | Trả về phản hồi rỗng HTTP 204 cho /favicon.ico. |
| GET | `/seo/jsonld/area/{area_slug}` | `area_jsonld` | Trả về JSON-LD TouristDestination của một khu vực theo slug. |
| GET | `/seo/jsonld/collection/{collection_type}` | `collection_jsonld` | Trả về JSON-LD ItemList cho một collection danh mục khai trong COLLECTIONS. |
| GET | `/seo/jsonld/itinerary/{itinerary_id}` | `itinerary_jsonld` | Trả về JSON-LD TouristTrip của lịch trình có id trùng khớp. |
| GET | `/seo/jsonld/site` | `site_jsonld` | Trả về hai khối JSON-LD cấp site: WebSite (kèm SearchAction) và Organization. |
| GET | `/seo/jsonld/{entity_id}` | `entity_jsonld` | Trả về JSON-LD schema.org của một entity, gộp thêm khối FAQPage vào @graph nếu có. |
| GET | `/seo/og` | `site_og_meta` | Trả về map meta Open Graph/Twitter Card mặc định cấp site (không gắn entity). |
| GET | `/seo/og/{entity_id}` | `entity_og_meta` | Trả về map meta Open Graph/Twitter Card của một entity theo id. |

### `agent/server.py` (71 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/` | `home` |  |
| GET | `/ab-testing/experiments` | `ab_experiments` | List all A/B testing experiments. Admin-only. |
| GET | `/ab-testing/results/{experiment_name}` | `ab_results` | Get A/B test results with statistics. Admin-only. |
| GET | `/analytics/daily` | `analytics_daily` |  |
| GET | `/analytics/gaps` | `analytics_gaps` |  |
| GET | `/analytics/popular` | `analytics_popular` |  |
| GET | `/analytics/summary` | `analytics_summary` |  |
| GET | `/analytics/top-entities` | `analytics_top_entities` |  |
| POST | `/api/client-error` | `client_error` | P3: Nhận lỗi frontend (uncaught/unhandledrejection/component) để admin xem. |
| GET | `/api/mentions` | `mention_search` | Autocomplete cho @-mention: người dùng (PG) + địa điểm (KB in-RAM). Trả tối đa ~11 mục. |
| GET | `/autocorrect` | `autocorrect_endpoint` |  |
| POST | `/chat` | `chat` |  |
| POST | `/chat/stream` | `chat_stream` |  |
| POST | `/checkpoints` | `save_checkpoint` | Save a conversation checkpoint. Admin-only. |
| POST | `/checkpoints/{checkpoint_id}/resume` | `resume_checkpoint` | Resume from a conversation checkpoint. Admin-only. |
| GET | `/checkpoints/{session_id}` | `list_checkpoints` | List conversation checkpoints. Admin-only. |
| POST | `/confirm/{confirmation_id}` | `confirm_action` | Confirm a pending action. Admin-only. |
| GET | `/confirmations/{session_id}` | `pending_confirmations` | List pending confirmations. Admin-only. |
| GET | `/events` | `events_endpoint` |  |
| POST | `/feedback` | `user_feedback` | Consume one owner-bound receipt into deidentified aggregate telemetry. |
| GET | `/freshness/candidates` | `freshness_candidates_endpoint` |  |
| GET | `/freshness/check` | `freshness_check_endpoint` |  |
| GET | `/freshness/report` | `freshness_report_endpoint` |  |
| GET | `/graph` | `graph_endpoint` | Return subgraph data for knowledge graph visualization. |
| GET | `/health` | `health` |  |
| GET | `/health/deep` | `deep_health` |  |
| GET | `/health/details` | `health_details` |  |
| GET | `/health/internal` | `health_internal` |  |
| GET | `/health/ready` | `readiness_probe` | Lightweight readiness probe for load balancers / orchestrators. |
| GET | `/health/slo` | `slo_metrics` | Basic SLO tracking: uptime, error rate, p95 latency. Admin-only. |
| POST | `/image/recognize` | `image_recognize_endpoint` |  |
| GET | `/metrics` | `metrics_endpoint` | Prometheus-compatible metrics in text exposition format. Admin-only. |
| GET | `/prompt-cache/stats` | `prompt_cache_stats` | Get prompt cache statistics. Admin-only. |
| GET | `/recommend` | `recommend_endpoint` |  |
| POST | `/reject/{confirmation_id}` | `reject_action` | Reject a pending action. Admin-only. |
| POST | `/reload` | `reload_data` |  |
| GET | `/search/enhanced` | `enhanced_search` | Enhanced hybrid search with BM25 + contextual embeddings. |
| GET | `/system/circuit-breakers` | `circuit_breaker_stats` |  |
| GET | `/system/client-errors` | `system_client_errors` | Admin xem lỗi frontend gần đây (lọc source=client từ StructuredLogger). |
| GET | `/system/costs` | `cost_tracker_report` |  |
| GET | `/system/costs/budget` | `cost_budget_status` |  |
| GET | `/system/costs/session/{session_id}` | `cost_tracker_session` |  |
| GET | `/system/dynamic-agents` | `dynamic_agents_report` |  |
| POST | `/system/dynamic-agents/create` | `dynamic_agents_create` |  |
| GET | `/system/errors` | `system_errors` |  |
| GET | `/system/eval/history` | `eval_history` |  |
| GET | `/system/eval/latest` | `eval_latest` |  |
| GET | `/system/guardrails` | `guardrails_status` |  |
| POST | `/system/guardrails/check-input` | `guardrails_check_input` |  |
| GET | `/system/handoffs` | `system_handoffs` | Multi-agent orchestrator handoff log. Admin-only. |
| GET | `/system/judge` | `judge_report` |  |
| POST | `/system/judge/evaluate` | `judge_evaluate` |  |
| GET | `/system/learning` | `system_learning` | Trạng thái vòng lặp tự học. Admin-only. |
| POST | `/system/learning/run` | `trigger_learning` | Trigger 1 vòng lặp tự học SAU cổng fitness (admin only, eval-gated). |
| GET | `/system/logs` | `system_logs` |  |
| GET | `/system/memory` | `system_memory` |  |
| GET | `/system/memory-graph` | `system_memory_graph` | Memory graph statistics. Admin-only. |
| GET | `/system/optimizer` | `optimizer_report` |  |
| GET | `/system/quality` | `system_quality` |  |
| GET | `/system/response-times` | `system_response_times` |  |
| GET | `/system/scheduler` | `system_scheduler` |  |
| GET | `/system/self-evolution` | `system_self_evolution` | Trạng thái cơ chế tự tiến hoá. Admin-only. |
| GET | `/system/semantic-cache` | `semantic_cache_status` |  |
| POST | `/system/semantic-cache/invalidate` | `semantic_cache_invalidate` |  |
| GET | `/system/traces` | `system_traces` | OpenTelemetry trace data. Admin-only. |
| POST | `/vectors/build` | `build_vectors` | Build/rebuild vector embeddings index. |
| GET | `/vectors/search` | `vector_search_endpoint` |  |
| GET | `/vectors/stats` | `vector_stats` |  |
| GET | `/weather` | `weather_endpoint` |  |
| GET | `/weather/all` | `weather_all` |  |
| GET | `/welcome` | `welcome_message` | Welcome message cá nhân hóa. |

### `agent/social.py` (71 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| DELETE | `/api/comments/{comment_id}` | `delete_comment` |  |
| PUT | `/api/comments/{comment_id}` | `edit_comment` |  |
| POST | `/api/comments/{comment_id}/like` | `toggle_comment_like` |  |
| POST | `/api/comments/{comment_id}/report` | `report_comment` |  |
| GET | `/api/community/leaderboard` | `community_leaderboard` | Bảng xếp hạng: thành viên tích cực theo điểm danh-tiếng (1 query gộp). |
| GET | `/api/community/stats` | `community_stats` | Số liệu THẬT của cộng đồng (không phải đếm 20 bài đã tải) cho sidebar /cong-dong. |
| GET | `/api/community/suggested-follows` | `suggested_follows` | Gợi ý người để theo dõi: top contributor mình CHƯA theo dõi (loại chính mình). |
| GET | `/api/community/trending-tags` | `trending_tags` | Hashtag thịnh hành: đếm hashtag trên bài ĐÃ DUYỆT trong N ngày gần nhất. |
| GET | `/api/drafts` | `list_drafts` |  |
| POST | `/api/drafts` | `save_draft` |  |
| DELETE | `/api/drafts/{draft_id}` | `delete_draft` |  |
| PUT | `/api/drafts/{draft_id}` | `update_draft` |  |
| POST | `/api/drafts/{draft_id}/publish` | `publish_draft` | Publish a draft — runs moderation and converts to a real post. |
| POST | `/api/drafts/{draft_id}/schedule` | `schedule_draft` | Schedule a draft for future publication. |
| GET | `/api/entities/{entity_id}/feed` | `get_entity_feed` | Feed cho một entity cụ thể (điểm du lịch, sản phẩm...). |
| GET | `/api/feed` | `get_feed` | Feed cộng đồng: chronological + seasonal boost + quality boost. |
| GET | `/api/feed/explore` | `explore_feed` |  |
| GET | `/api/feed/following` | `get_following_feed` | Feed các bài từ NGƯỜI + ĐỊA ĐIỂM mình theo dõi (mới nhất trước). |
| GET | `/api/feed/friend-reviews` | `get_friend_reviews` | Đánh giá gần đây từ những NGƯỜI mình theo dõi (không phải địa điểm). |
| GET | `/api/feed/friend-saves` | `get_friend_saves` | Địa điểm gần đây được LƯU (saved_entities) bởi những người mình theo dõi. |
| GET | `/api/feed/trending` | `trending_posts` |  |
| GET | `/api/hashtags` | `list_hashtags` | All hashtags with post counts (approved posts only). |
| GET | `/api/hashtags/{tag}/posts` | `hashtag_posts` |  |
| GET | `/api/me/activity` | `user_activity` | Unified activity feed: user's recent posts, comments, likes. |
| GET | `/api/me/badge-progress` | `get_badge_progress` |  |
| GET | `/api/me/bookmarks` | `get_my_bookmarks` |  |
| GET | `/api/me/collections` | `list_my_collections` |  |
| POST | `/api/me/collections` | `create_collection` |  |
| DELETE | `/api/me/collections/{collection_id}` | `delete_collection` |  |
| GET | `/api/me/collections/{collection_id}/items` | `get_collection_items` |  |
| POST | `/api/me/collections/{collection_id}/items` | `add_to_collection` |  |
| DELETE | `/api/me/collections/{collection_id}/items/{post_id}` | `remove_from_collection` |  |
| GET | `/api/me/counts` | `user_counts` |  |
| GET | `/api/me/stats` | `user_stats` | Extended stats for the authenticated user's profile dashboard. |
| POST | `/api/posts` | `create_post` |  |
| GET | `/api/posts/hidden` | `list_hidden_posts` |  |
| DELETE | `/api/posts/{post_id}` | `delete_post` |  |
| GET | `/api/posts/{post_id}` | `get_post` |  |
| PATCH | `/api/posts/{post_id}` | `update_post` | Sửa bài của CHÍNH MÌNH (nội dung; review đổi sao). Kiểm duyệt + hashtag lại. |
| GET | `/api/posts/{post_id}/appeal` | `get_appeal_status` |  |
| POST | `/api/posts/{post_id}/appeal` | `appeal_post` |  |
| POST | `/api/posts/{post_id}/best-answer` | `set_best_answer` |  |
| POST | `/api/posts/{post_id}/bookmark` | `toggle_bookmark` |  |
| GET | `/api/posts/{post_id}/comments` | `get_comments` |  |
| POST | `/api/posts/{post_id}/comments` | `create_comment` |  |
| GET | `/api/posts/{post_id}/edit-history` | `get_post_edit_history` | View edit history for a post (public — transparency). |
| POST | `/api/posts/{post_id}/hide` | `hide_post` |  |
| POST | `/api/posts/{post_id}/like` | `toggle_like` |  |
| GET | `/api/posts/{post_id}/likers` | `get_post_likers` | List users who liked a post. |
| DELETE | `/api/posts/{post_id}/pin-comment` | `unpin_comment` |  |
| POST | `/api/posts/{post_id}/pin-comment` | `pin_comment` |  |
| POST | `/api/posts/{post_id}/pin-to-profile` | `pin_post_to_profile` |  |
| POST | `/api/posts/{post_id}/react` | `toggle_reaction` | Toggle an emoji reaction on a post. |
| GET | `/api/posts/{post_id}/reactions` | `get_reactions` | Get reaction counts and details for a post. |
| GET | `/api/posts/{post_id}/related` | `related_posts` | Bài viết liên quan: cùng entity hoặc cùng hashtag. |
| POST | `/api/posts/{post_id}/report` | `report_post` |  |
| POST | `/api/posts/{post_id}/share` | `track_share` | Track when a user shares a post (copy link, social media share). |
| POST | `/api/posts/{post_id}/unhide` | `unhide_post` |  |
| GET | `/api/scheduled` | `list_scheduled` | List user's scheduled posts (not yet published). |
| DELETE | `/api/scheduled/{post_id}` | `cancel_scheduled` | Cancel a scheduled post (converts back to draft). |
| GET | `/api/search/posts` | `search_posts` | Tìm bài viết cộng đồng theo nội dung (PG trigram `lower(content) LIKE`, |
| GET | `/api/search/users` | `search_users` | Tìm người dùng theo tên hiển thị (không phân-biệt-dấu). Thông tin hồ-sơ công-khai. |
| POST | `/api/upload/image` | `upload_image` |  |
| GET | `/api/users/{user_id}` | `get_user_profile` |  |
| GET | `/api/users/{user_id}/activity-heatmap` | `get_activity_heatmap` |  |
| GET | `/api/users/{user_id}/followers` | `list_followers` | Danh sách NGƯỜI đang theo dõi user này (hồ-sơ công-khai). |
| GET | `/api/users/{user_id}/following` | `list_following_users` | Danh sách NGƯỜI mà user này đang theo dõi (hồ-sơ công-khai). |
| GET | `/api/users/{user_id}/posts` | `get_user_posts` |  |
| POST | `/api/users/{user_id}/report` | `report_user` |  |
| GET | `/api/users/{user_id}/reviews` | `get_user_reviews` |  |
| GET | `/api/users/{user_id}/timeline` | `get_user_timeline` |  |

### `agent/visits.py` (6 route)

| Method | Path | Handler | Mô tả (docstring) |
|---|---|---|---|
| GET | `/api/me/visits` | `list_visits` | Liệt kê các entity người dùng hiện tại đã đánh dấu want/visited, lọc tuỳ chọn theo status. |
| POST | `/api/me/visits` | `set_visit` | Upsert dấu want/visited của người dùng hiện tại cho một entity, trả về status vừa ghi. |
| GET | `/api/me/visits/check/{entity_id}` | `check_visit` | Trả về status want/visited của người dùng hiện tại cho một entity, hoặc null nếu chưa đánh dấu. |
| GET | `/api/me/visits/review-prompts` | `review_prompts` | Entities visited but not yet reviewed — prompt user to write a review. |
| GET | `/api/me/visits/stats` | `visit_stats` | Thống kê visit của người dùng hiện tại: tổng, số visited, số want và tách theo loại entity. |
| DELETE | `/api/me/visits/{entity_id}` | `remove_visit` | Xoá dấu want/visited của người dùng hiện tại cho một entity, luôn trả status null. |

<!-- ROUTE-APPENDIX:END -->
