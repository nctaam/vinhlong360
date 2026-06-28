# Developer Setup Guide

Get vinhlong360 running locally for development.

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | Backend (FastAPI) |
| Node.js | 18+ | Frontend (Nuxt 4) |
| Docker | 24+ | PostgreSQL container |
| Git | 2.40+ | Version control |

Tested on Windows 10/11 (PowerShell + Git Bash) and Ubuntu 22.04.

## 1. Clone & Environment

```bash
git clone <repo-url> vinhlong360
cd vinhlong360

# Python virtualenv
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env — minimum required for dev:
#   LLM_API_KEY=<your-key>
#   LLM_BASE_URL=<openai-compatible-endpoint>
#   ADMIN_API_KEY=dev-admin-key
```

## 2. PostgreSQL (Docker)

UGC features (posts, comments, auth) require PostgreSQL. Knowledge-base works with SQLite fallback.

```bash
# Start PostgreSQL only
docker compose up -d postgres

# Wait until healthy (~5s), then verify:
docker compose ps  # should show "healthy"

# Schema is auto-initialized via init.sql mount
```

Default connection (from docker-compose.yml):
- Host: `localhost:5432`
- Database: `vinhlong360`
- User: `vl360`
- Password: `vl360_dev_password`

The `.env.example` has `DATABASE_URL=postgresql://vl360:change_me@localhost:5432/vinhlong360` — update the password to match.

## 3. Seed the Database

```bash
# Import data.json into SQLite (for knowledge-base dev without Postgres)
python agent/database.py --replace
# This creates agent/data/vinhlong360.db

# Or import into PostgreSQL (set DATABASE_URL in .env first)
ALLOW_DESTRUCTIVE_DB_REPLACE=1 python agent/database.py --replace
```

## 4. Start the Backend

```bash
python agent/server.py
# Listens on http://localhost:8360
# Health check: http://localhost:8360/health
```

Key startup environment variables (all have defaults in `.env.example`):
- `BUILD_SEARCH_INDEXES=true` — builds BM25/vector indexes at startup
- `BACKGROUND_INDEX_BUILD=true` — indexes build in background (non-blocking)
- `SCHEDULER_ENABLED=false` — disable background scheduler for dev
- `SCHEDULER_ENABLE_AUTONOMOUS_TASKS=false` — must stay false unless explicitly opted in

## 5. Start the Frontend

```bash
cd web-nuxt
npm install
npm run dev
# Listens on http://localhost:3000
# Proxies /api/* to http://localhost:8360
```

The Nuxt dev server auto-reloads on file changes (HMR).

## 6. Running Tests

```bash
# From repo root:

# Quick baseline (excludes slow + integration)
python -m pytest -q

# Full test suite (includes integration tests)
python -m pytest -m "" -q

# Only root tests/
python -m pytest tests/ -q

# Only agent tests
python -m pytest agent/tests/ -q

# With coverage
python -m pytest --cov=agent --cov-report=html

# Frontend type check
cd web-nuxt && npm run typecheck

# Frontend build (catches SSR errors)
cd web-nuxt && npm run build

# Python linting
ruff check agent/ scripts/ tests/
```

Test configuration is in `pytest.ini`:
- Default markers exclude `slow` and `integration`
- Test paths: `tests/` and `agent/tests/`
- Import mode: `importlib`

## 7. Data Validation

```bash
# Validate data.json structure and quality
python scripts/validate_data.py

# JSON output for CI
python scripts/validate_data.py --json

# Backup before any data operation (invariant B1)
python scripts/backup_data.py
```

## 8. Project Structure

```
vinhlong360/
├── agent/              # FastAPI backend (75 modules)
│   ├── server.py       # Main app entry point
│   ├── database.py     # PostgreSQL/SQLite abstraction
│   ├── knowledge.py    # In-memory entity graph
│   ├── config.py       # Environment config
│   ├── routers/        # API route handlers
│   └── tests/          # Backend unit/integration tests
├── web-nuxt/           # Nuxt 4 SSR frontend
│   ├── pages/          # File-based routing
│   ├── components/     # Vue components
│   ├── composables/    # Shared logic (useConstants, useCoords, etc.)
│   └── assets/css/     # Design tokens + stylesheets
├── web/                # Legacy (data.json, admin HTML)
├── docs/               # Documentation
├── scripts/            # Data scripts (validate, backup, deploy)
├── tests/              # Root-level tests
├── .github/            # CI workflows
├── docker-compose.yml  # Dev services
├── init.sql            # PostgreSQL DDL (UGC tables)
└── .env.example        # Environment template
```

## 9. Common Tasks

### Add a new entity type

1. Add to `VALID_TYPES` in `agent/admin.py`
2. Add to `TYPE_META` in `agent/knowledge.py` (if needed)
3. Add label in `web-nuxt/composables/useConstants.ts`
4. Validate: `python scripts/validate_data.py`

### Edit entities via admin

1. Backend running on `:8360`
2. Navigate to `http://localhost:3000/admin`
3. Need `X-Admin-Key` header matching `ADMIN_API_KEY` in `.env`

### Test chat functionality

```bash
# Quick smoke test
python scripts/check_api.py

# Or curl:
curl -X POST http://localhost:8360/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "quán ăn ngon ở Vĩnh Long"}'
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: psycopg2` | `pip install psycopg2-binary` |
| UGC endpoints return 503 | PostgreSQL not running; `docker compose up -d postgres` |
| `OperationalError: database locked` | SQLite concurrency limit; use PostgreSQL for UGC |
| Nuxt build OOM | Set `NODE_OPTIONS=--max-old-space-size=4096` |
| Tests fail on `test_config` | Missing `.env`; ensure `LLM_API_KEY` is set |
| `DESTRUCTIVE_OPS_LOCKED` error | Set `ALLOW_DESTRUCTIVE_DB_REPLACE=1` for `--replace` |
