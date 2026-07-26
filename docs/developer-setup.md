# Developer Setup Guide

> **STATUS (2026-07-07): active — đã truth-sync.** Setup steps remain valid; §3 now restricts `database.py --replace` to fresh clones only (backup first per CLAUDE.md B1/B7).

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

> ⚠️ **`--replace` is for a FRESH CLONE only** (no existing DB, or a DB you are happy to discard).
> The DB is the source of truth and carries AdminCP write-through edits that `data.json` does not —
> on an existing DB, `--replace` overwrites those edits with the (diverged) `data.json` snapshot.
> If your DB has any edits: run `python scripts/backup_data.py` FIRST. See CLAUDE.md invariants
> **B1** (snapshot before any data operation) and **B7** (`--replace` is a destructive op — never
> run it without explicit instruction + backup).

```bash
# Fresh clone only: import data.json into SQLite (knowledge-base dev without Postgres)
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
| `DESTRUCTIVE_OPS_LOCKED` error | The lock is intentional (CLAUDE.md B7). Only bypass with `ALLOW_DESTRUCTIVE_DB_REPLACE=1` on a fresh clone or after `python scripts/backup_data.py` |

---

## 10. Kích hoạt module & env flags (cơ chế THẬT)

> Gộp từ `docs/archive/module-activation-guide.md` (nay archived). Đây là cơ chế đã verify với code, không phải mô tả cũ.

**Không có "dormant module".** Các tên `HAS_*` là **biến Python, KHÔNG phải env var**. `agent/server.py` đặt mỗi cờ qua try-import guard:

```python
try:
    from guardrails import injection_detector, pii_masker, ...
    HAS_GUARDRAILS = True
except ImportError:
    HAS_GUARDRAILS = False
```

Hệ quả:
- **Không chỗ nào trong `agent/` đọc `HAS_*` từ môi trường.** Đặt `HAS_X=true/false` trong `.env` là **no-op**.
- Trên codebase hiện tại, **cả 26 module guarded đều import sạch → mọi `HAS_*` = `True` → tất cả đang BẬT** (dev lẫn prod): guardrails (PII masking + injection detection, live trên chat path), metrics, vector_search, semantic_cache, orchestrator, checkpoints, self_optimizer, dynamic_agents...
- **Cách duy nhất tắt một module là sửa code** (bỏ/guard import hoặc xoá file module) + redeploy. Không có toggle runtime.

### Env flags THẬT có tác dụng (default verify ở `agent/config.py` / `server.py`)

| Env var | Default | Tác dụng |
|---------|---------|----------|
| `LLM_JUDGE_ENABLED` | `false` | Judge chất lượng phản hồi. Chỉ chạy khi module import OK **và** flag `true`. Tốn +1 LLM call/chat — giữ off trừ khi dư ngân sách. |
| `AUTONOMOUS_AGENT_ENABLED` | `false` | Opt-in vòng lặp LLM nền (CLAUDE.md §B8: opt-in + cap cứng + kill-switch). Đọc trực tiếp bởi `agent/autonomous_budget.py`. |
| `AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY` | `20` | Cap cứng/ngày cho vòng lặp nền (`autonomous_budget.py`). |
| `SCHEDULER_ENABLED` | `true` | Scheduler nền in-process. Đặt `false` cho smoke test local. |
| `SCHEDULER_ENABLE_AUTONOMOUS_TASKS` | `false` | Job autonomous learn/discovery cũ. Giữ `false` (§B8). |
| `BUILD_SEARCH_INDEXES` | `true` | Build BM25/vector index lúc khởi động. `false` để chạy nhanh local. |
| `BACKGROUND_INDEX_BUILD` | `true` | Build index ở nền thay vì chặn readiness. |

### Đính chính vài hiểu nhầm cũ

- **`/metrics` KHÔNG mở tự do.** Middleware `gate_internal_endpoints` yêu cầu header `X-Admin-Key` hợp lệ ở **mọi** môi trường, fail-close 404. `curl /metrics` không header → 404 **theo thiết kế** (không phải module hỏng). Prometheus scrape phải gửi `X-Admin-Key`.
- **`semantic_cache` KHÔNG cần Redis.** Nó là L1 in-memory LRU + L2 disk JSON (`agent/data/semantic_cache/entries.json`). Reset L2 = xoá file JSON, không phải `redis-cli`.
- **Rollback bằng `HAS_X=false` chưa bao giờ hoạt động.** Trong sự cố, đừng phí thời gian sửa `.env` cho `HAS_*` — không đổi gì.

Quy trình ops VPS (SSH/systemctl restart) xem `docs/deployment-guide.md` + `docs/incident-runbook.md`.
