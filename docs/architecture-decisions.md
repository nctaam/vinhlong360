# VinhLong360 Architecture Decisions

Date: 2026-06-12
Status: Accepted for stabilization sprint

## Decisions

1. The primary frontend is `web-nuxt`.
   - `web` is treated as the legacy/static frontend during migration.
   - `web-astro` is treated as an optional SEO/static generation surface.

2. The primary backend is the FastAPI application in `agent`.
   - New public API behavior should be implemented behind explicit routers/services.
   - Import-time side effects should be reduced as server code is touched.

3. The primary database is PostgreSQL.
   - Docker Compose already provisions PostgreSQL as `vl360-postgres`.
   - SQLite is only a local/dev fallback unless a specific test depends on it.

4. Static data files are build/cache artifacts, not the long-term source of truth.
   - `web/data.json` and `web/data.js` may remain during migration.
   - Data exports must follow the same schema as the API contract.

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

## Non-goals for this sprint

- Rewrite the whole backend.
- Delete the static frontend immediately.
- Delete SQLite immediately.
- Deploy to a public production environment without an explicit release step.
- Rotate secrets automatically from code.
