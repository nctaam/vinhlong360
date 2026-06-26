# Session 7: Chịu lỗi pipeline AI
<!-- Phạm vi: Pipeline LLM — orchestrator, knowledge search, contextual retrieval, guardrails, circuit breaker, LLM judge, image recognition + test resilience -->

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vinhlong360/vl360-backend-res`, nhánh `dev/backend-resilience`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

- `agent/orchestrator.py` — Chat orchestration
- `agent/knowledge.py` — Knowledge search
- `agent/contextual_retrieval.py` — BM25/rerank
- `agent/tools.py` — Chat tools
- `agent/guardrails.py` — Input/output guard
- `agent/llm_judge.py` — LLM judge
- `agent/image_recognition.py` — Vision
- `agent/circuit_breaker.py` — Circuit breaker
- `agent/tests/test_resilience.py` — Resilience tests (đã có)

**KHÔNG SỬA:** `server.py`, `database.py`, `admin.py`, `social.py`, `auth.py`, FE files.

## Công việc

### Đã xong (đợt trước):
- P0-6/7/8: LLM timeout, circuit breakers, guardrail fallbacks
- 357 lines resilience tests

### Audit tiếp:
- Timeout enforcement: verify EVERY LLM call has timeout
- Error swallowing: remaining `except: pass` → `except Exception as e: logger.warning(...)`
- Guardrail hardening: `generate_followups` timeout + fallback empty list
- `json.loads` parsing LLM output: try/except + fallback
- Knowledge search edge cases: empty query, special chars, Vietnamese diacritics
- Orchestrator: test timeout/cancellation/malformed-tool-output paths

**Lưu ý:**
- §B3: Test trước khi refactor vùng mù
- Giữ behavior hiện tại — thêm resilience, không đổi logic
- Mock LLM calls trong test

## Verify

```bash
python -m pytest -q
python -m pytest agent/tests/test_resilience.py -v
```

## Commit prefix: `[backend-resilience]`
