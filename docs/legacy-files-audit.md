# Legacy Files Audit — `web/`

Date: 2026-06-27

## Current State

The `web/` directory has been significantly cleaned up through GD6.1 (cleanup rounds 1-4). Only 3 items remain:

| Path | Size | Status | Notes |
|------|------|--------|-------|
| `web/data.json` | 4.9 MB | **KEEP** | Tracked seed file — DB export for rebuilding SQLite dev cache and prerender data source. Source of truth is PostgreSQL (DB-as-SoT, decision #4). |
| `web/data.js` | 4.9 MB | **REMOVABLE (GD7)** | Legacy `window.__DATA__` format kept for backward compatibility. No current consumer — `web-nuxt` reads from API, not from data.js. |
| `web/media/` | 0 files | **REMOVABLE (GD7)** | Empty directory. Media is served via external CDN URLs (weserv.nl proxy). |

## Previously Removed (GD6.1 cleanup)

The following were removed in cleanup rounds 1-4 (commits `c8e0e74`, `1056b61`, and earlier):

- `admin*.html` — Admin UI HTML files (replaced by `web-nuxt/pages/admin/`)
- `web-astro/` — Astro frontend (replaced by `web-nuxt/`)
- Static assets (CSS, JS, images, icons)
- Legacy HTML pages
- 98+ dead files totaling ~16,610 lines and ~6.3MB images

## Recommendations for GD7

1. **Remove `web/data.js`** — No consumer exists. If any legacy integration resurfaces, it can be regenerated from `data.json`.
2. **Remove `web/media/`** — Empty directory, no files to preserve.
3. **Keep `web/data.json`** — Still used as tracked seed for `database.py --replace` and as the prerender data source. Consider moving to `data/seed.json` for clarity.
