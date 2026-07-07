# VinhLong360 Architecture Decisions

> **STATUS (2026-07-07): active — đã truth-sync.** Decision 1's `web/` inventory corrected (`admin*.html` removed in GĐ6.1; `data.json` is a kept export, not a removal candidate); decisions 17–19 added (AI-only images, Vĩnh-Long-specific positioning + noindex, work-source governance).

Date: 2026-06-12 (updated 2026-07-07)
Status: Accepted — reflects decisions through 2026-07-07

## Decisions

1. The **only** frontend is `web-nuxt` (Nuxt 4 SSR).
   - `web-astro` has been removed (commit 949c843).
   - `web/` retains only `data.json` (tracked seed), `data.js` (legacy export), `admin*.html` (admin UI), and `media/`. These are candidates for removal in GĐ7.

2. The primary backend is the FastAPI application in `agent`.
   - New public API behavior should be implemented behind explicit routers/services.
   - Import-time side effects should be reduced as server code is touched.

3. The primary database is **PostgreSQL** (the source of truth for all knowledge data since GĐ3).
   - Docker Compose provisions PostgreSQL as `vl360-postgres`.
   - SQLite is a local/dev cache for the knowledge base only.
   - **UGC/auth is Postgres-only** (GĐ3.1 decision): `_require_pg` guards on 3 UGC routers return 503 on SQLite. No SQLite port for users/posts/comments/notifications/follows/reviews. Rationale: dev/prod parity, avoid maintaining 2 SQL dialects.

4. **Database is the source of truth** (DB-as-SoT, finalized GĐ3).
   - `web/data.json` is an **export** from the database, not the source. It serves as a tracked seed for rebuilding SQLite dev cache and as a prerender data source.
   - Admin CRUD writes to DB → `knowledge.reload()` → in-memory graph updated (split-brain eliminated).
   - `web/data.js` (`window.__DATA__`) is a legacy format kept for backward compatibility.

5. The canonical entity coordinate field is `coordinates`.
   - Existing `coords` values may remain temporarily for legacy compatibility.
   - New code should read/write `coordinates` first.

6. The canonical public relationship shape is API-friendly.
   - Public API responses should expose `source_id`, `target_id`, and `rel_type`.
   - Compatibility aliases may be kept while legacy clients are migrated.

7. Production deploy should converge on this path:

```text
PostgreSQL -> FastAPI -> Nuxt -> Nginx
                    |
Redis
```

8. Readiness must be cheap and local.
   - `/health` must not call the LLM or other external services.
   - `/health/deep` is reserved for slower dependency checks such as LLM/API pings.

9. Expensive background work must not block FastAPI startup.
   - Search index builds run in the background by default.
   - Operators can set `BUILD_SEARCH_INDEXES=false` for lightweight local smoke tests.
   - Operators can set `BACKGROUND_INDEX_BUILD=false` when a deployment must wait for indexes.

10. Local SQLite must be treated as a replaceable dev cache.
    - Use `python agent/database.py --replace` to rebuild SQLite from `web/data.json`.
    - The command backs up the SQLite file before replacing knowledge tables.

11. **CSS: pure tokens, no Tailwind** (Design System decision, 2026-06-14).
    - Keep hand-written CSS with 3-tier design tokens (`variables.css`).
    - Keep the existing color system (amber/green Mekong palette).
    - Rationale: solo dev, existing CSS is manageable, Tailwind adds build complexity and learning curve for no proportional gain at this scale.

12. **3-tỉnh sáp nhập: chủ đề thay vì địa lý** (2026-06-18+).
    - Vĩnh Long + Bến Tre + Trà Vinh merge into one province (NQ 1687/NQ-UBTVQH15).
    - Homepage/navigation organized by **topic** (du lịch, sản phẩm, ẩm thực, lưu trú) not by 3 geographic zones.
    - 124 xã/phường modeled at ward level (35 phường + 89 xã); no district level.
    - `area` field (vinh-long/ben-tre/tra-vinh) retained for data provenance and filtering.

13. **Showcase-only commerce** (GĐ13, §1.4).
    - No booking, no cart, no payment on-site. CTA = Zalo/phone/website link only.
    - Avoids NĐ52/85 e-commerce registration requirements.
    - Revenue model: B2G contracts + premium listing (Track-H).

14. **Anti-hallucination for data** (§1.4, enforced since GĐ2).
    - Never fabricate addresses, phone numbers, seasonal data, or ward assignments.
    - `placeId=None` for unclassifiable entities rather than guessing.
    - `coords_approximate=true` flag for centroid-derived coordinates.
    - Frontend shows "Gần đúng" badge when approximate.

15. **PostgreSQL schema changes are migration-only** (2026-07-02).
    - FastAPI startup verifies the required PostgreSQL schema but does not run `ALTER TABLE` or create indexes.
    - Deploys must run `scripts/apply_migrations.py` before restarting `vl-agent`.
    - `schema_version` is the release gate source for production readiness. Legacy databases without `schema_version` are treated as baseline 052, then migrations 053+ are applied by the runner.
    - `VL360_ALLOW_PG_SCHEMA_DRIFT=true` is an emergency bypass only; it must not be used as a normal deploy path.

16. **AdminCP uses route-level RBAC scopes** (2026-07-02).
    - Admin entry is based on scopes, not only coarse roles.
    - `moderator` can enter only moderation-scoped routes; content, settings, ops, and security routes require their respective scopes.
    - `admin` keeps the full standard scope set; `superadmin` and admin-key receive wildcard access.
    - New AdminCP endpoints must map to one of: `content.editor`, `moderation.manager`, `ops.deploy`, `settings.admin`, `security.admin`, or be deliberately dashboard/read-only.

## Non-goals (updated)

- ~~Rewrite the whole backend.~~ Stable; incremental improvement only.
- ~~Delete the static frontend immediately.~~ `web-astro` removed; `web/` legacy cleanup in GĐ7.
- ~~Delete SQLite immediately.~~ SQLite kept as dev cache; UGC is Postgres-only.
- Deploy to a public production environment without an explicit release step.
- Rotate secrets automatically from code.
- Add Tailwind, heavy JS frameworks, or native app targets.
- Self-generate data that requires real-world verification (addresses, phone numbers, seasonal data).
