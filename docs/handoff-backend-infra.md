# Session 10: Backend Infra — Core + Scripts + Legacy Cleanup

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vinhlong360/vl360-backend-infra`, nhánh `dev/backend-infra`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

**Backend core:**
- `agent/database.py` — DB abstraction (SQLite + Postgres)
- `agent/storage.py` — File/image storage
- `agent/cache.py` — Caching layer
- `agent/config.py` — Configuration
- `agent/metrics.py` — Metrics collection
- `agent/tracing.py` — Request tracing
- `agent/feature_flags.py` — Feature flags

**Scheduler/autonomous:**
- `agent/scheduler.py`, `agent/autonomous_budget.py`
- `agent/auto_learn.py`, `agent/learn_loop.py`

**Data pipeline:**
- `agent/data_quality.py`, `agent/export_data.py`
- `agent/freshness.py`, `agent/checkpoints.py`

**Import/crawl (legacy, read-mostly):**
- `agent/crawler.py`, `agent/import_*.py`, `agent/merge_*.py`

**Tests:**
- `agent/tests/test_database.py`, `agent/tests/test_knowledge.py` (thêm test mới)

**KHÔNG SỬA:** `server.py` (router chính), `admin.py`, `social.py`, `auth.py`, `notifications.py`, FE files.

## Công việc

### Đã xong (đợt trước):
- Dead code audit (docs/DEAD-CODE-AUDIT.md) — 16 legacy modules identified

### Tiếp theo:
1. **Test coverage cho database.py** — module quan trọng nhất, cần tests cho:
   - Connection pooling edge cases
   - Postgres vs SQLite behavior differences
   - Migration runner reliability
   - Batch operations (get_entities_batch)
   
2. **Cache optimization:**
   - Verify cache invalidation correctness
   - Cache warming strategy review
   
3. **Config hardening:**
   - Verify all env vars have sensible defaults
   - Document required vs optional config

4. **Legacy module assessment:**
   - Based on DEAD-CODE-AUDIT.md, mark which modules can be safely removed
   - Add deprecation warnings to unused modules
   - **KHÔNG XOÁ** — chỉ đánh dấu + document (§B2 additive-first)

**Lưu ý:**
- §B3: Test TRƯỚC khi refactor — database.py là vùng mù
- §B8: Không thêm dịch vụ trả phí
- §B1: Backup trước thao tác data

## Verify

```bash
python -m pytest -q
python -m pytest agent/tests/ -v
```

## Commit prefix: `[backend-infra]`
