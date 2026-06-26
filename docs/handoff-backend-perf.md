# Handoff: Session Backend Performance (`dev/backend-perf`)

> Paste toàn bộ nội dung này làm message đầu tiên trong session Claude Code mới.

---

## Bối cảnh

Bạn đang làm trên nhánh `dev/backend-perf` của dự án vinhlong360 — MXH du lịch/OCOP cho Vĩnh Long (3 tỉnh sáp nhập). Solo dev, Nuxt 4 SSR + FastAPI. **Đọc `CLAUDE.md` và `docs/PARALLEL-BRANCHES.md` trước khi bắt đầu.**

## Nhánh hiện tại

```bash
git checkout dev/backend-perf
```

## Phạm vi file bạn SỞ HỮU (chỉ sửa các file này)

- `agent/knowledge.py` — search & knowledge graph
- `agent/contextual_retrieval.py` — BM25/rerank
- `agent/orchestrator.py` — chat orchestration
- `agent/tools/*.py` — chat tools
- `agent/guardrails.py` — input/output guard
- `agent/middleware.py` — request middleware
- `agent/llm_judge.py` — LLM judge
- `agent/image_recognition.py` — image recognition
- `agent/tests/*.py` (thêm test mới, KHÔNG sửa test hiện tại)

**KHÔNG SỬA:** `server.py`, `database.py`, `admin.py`, `social.py`, `auth.py`, `public_api.py`, web-nuxt/**, nuxt.config.ts.

## Công việc

### 1. LLM timeout enforcement (P1-2) — ƯU TIÊN CAO
Nhiều LLM call không có timeout → backend treo nếu LLM chết.
- `llm_judge.py:401` — judge call
- `image_recognition.py:375` — vision call
- `contextual_retrieval.py:433` — rerank call
- Sửa: thêm `timeout=30` (hoặc `httpx.Timeout(30)`) cho mọi OpenAI client call
- Test: mock OpenAI → verify timeout raises → graceful fallback

### 2. Error swallowing fix (P2-11)
`except: pass` nuốt lỗi vận hành ở:
- `middleware.py:98,110`
- `guardrails.py` (nhiều chỗ)
- Sửa: thay `except: pass` → `except Exception as e: logger.warning(...)` (giữ resilience, thêm visibility)

### 3. Guardrail hardening (EH-01/02)
- `generate_followups` trong orchestrator: cần timeout + fallback empty list
- `json.loads` parsing LLM output: cần try/except + fallback
- Test: verify guardrail failure → graceful degrade (không crash request)

### 4. Test coverage cho orchestrator
- Chat tool dispatch: test các nhánh `call_tool` error path
- Orchestrator: test timeout/cancellation/malformed-tool-output
- Knowledge search: test edge cases (empty query, very long query, special chars)

### 5. Search quality (nếu còn thời gian)
- knowledge.py: kiểm tra search relevance cho Vietnamese queries
- contextual_retrieval.py: verify BM25 scoring accuracy

## Lưu ý

- **§B3** Test trước khi refactor vùng mù — module này 0% test ở một số hàm
- Mọi thay đổi phải **giữ behavior hiện tại** — chỉ thêm timeout/logging/guard, không đổi logic
- Backend KHÔNG có LLM access trong sandbox → test phải mock LLM calls

## Verify

```bash
python -m pytest -q                     # tests xanh
python -m pytest agent/tests/ -q -v     # chi tiết agent tests
```

## Commit convention

```
[backend] mô tả ngắn

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
