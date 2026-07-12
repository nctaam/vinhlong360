# Chat Ownership, Cache, Transport, and Usage Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind all chat state and accounting to one server-derived owner, remove prompt/history from streaming URLs, and charge every provider-reported model round exactly once.

**Architecture:** Resolve an authenticated account owner or signed anonymous visitor before any chat state access. Store conversations under `(owner_key, conversation_id)`, namespace caches and budgets by owner, transport streaming input in a JSON POST body, and aggregate usage at provider-call boundaries into one request settlement.

**Tech Stack:** FastAPI, Python 3.14, OpenAI-compatible completion objects, pytest, Nuxt 4, Vue 3, TypeScript, Vitest.

---

### Task 1: Server-derived owner and owned conversation memory

**Files:**
- Create: `agent/chat_identity.py`
- Modify: `agent/memory.py`
- Modify: `agent/server.py`
- Create: `agent/tests/test_chat_owner_boundary.py`
- Modify: `tests/test_memory.py`

- [ ] **Step 1: Write failing identity and memory tests**

Add tests for these concrete contracts:

```python
ctx = resolve_anonymous_owner(None)
assert ctx.owner_key.startswith("anon:")
assert ctx.cookie_value
assert resolve_anonymous_owner(ctx.cookie_value).owner_key == ctx.owner_key
assert resolve_anonymous_owner(ctx.cookie_value + "tampered").owner_key != ctx.owner_key

alice = mm.create_session("user:alice")
mm.on_message("user:alice", alice.session_id, "user", "ALICE_SENTINEL")
assert mm.require_session("user:alice", alice.session_id) is alice
with pytest.raises(UnknownConversation):
    mm.require_session("user:bob", alice.session_id)
assert ("user:bob", alice.session_id) not in mm._sessions
```

Also prove two conversations owned by Alice share `ColdMemory["user:alice"]` but keep distinct hot messages, and two owners using the same selector cannot collide.

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_chat_owner_boundary.py tests/test_memory.py -q`

Expected: FAIL because no signed owner context or owned session API exists.

- [ ] **Step 3: Implement the owner resolver**

In `agent/chat_identity.py`, add:

```python
@dataclass(frozen=True)
class ChatOwnerContext:
    owner_key: str
    cookie_value: str | None = None
    authenticated: bool = False

def resolve_anonymous_owner(cookie_value: str | None) -> ChatOwnerContext:
    visitor_id = ""
    if cookie_value and "." in cookie_value:
        candidate, supplied = cookie_value.rsplit(".", 1)
        expected = hmac.new(_OWNER_SECRET, candidate.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(supplied, expected):
            visitor_id = candidate
    if visitor_id:
        digest = hashlib.sha256(visitor_id.encode()).hexdigest()
        return ChatOwnerContext(owner_key=f"anon:{digest}")
    visitor_id = secrets.token_urlsafe(32)
    signature = hmac.new(_OWNER_SECRET, visitor_id.encode(), hashlib.sha256).hexdigest()
    digest = hashlib.sha256(visitor_id.encode()).hexdigest()
    return ChatOwnerContext(owner_key=f"anon:{digest}", cookie_value=f"{visitor_id}.{signature}")

async def resolve_chat_owner(request: Request) -> ChatOwnerContext:
    user = await _get_current_user_or_none(request)
    if user:
        return ChatOwnerContext(owner_key=f"user:{user['id']}", authenticated=True)
    return resolve_anonymous_owner(request.cookies.get(CHAT_OWNER_COOKIE))

def set_chat_owner_cookie(response: Response, context: ChatOwnerContext) -> None:
    if context.cookie_value:
        response.set_cookie(CHAT_OWNER_COOKIE, context.cookie_value, **_cookie_params())
```

Use `secrets.token_urlsafe(32)`, HMAC-SHA256, `hmac.compare_digest`, URL-safe encoding, and `sha256(visitor_id)` for the persisted owner key. Prefer `CHAT_OWNER_SECRET`, fall back to `CSRF_SECRET`, require one in production, and allow an ephemeral development secret. Cookie name: `vl360_chat_owner`; `HttpOnly`, `SameSite=Lax`, path `/`, secure in production, bounded max-age.

- [ ] **Step 4: Implement owned memory APIs**

Add `UnknownConversation`. Change `_sessions` to `dict[tuple[str, str], HotMemory]`. Add `create_session(owner_key)` using `secrets.token_hex(16)` and `require_session(owner_key, session_id)` with no implicit creation. Update `build_context`, `on_message`, `on_entity_discussed`, `on_chat_complete`, and session-end helpers so hot state receives both owner and conversation while cold profiles receive only owner.

- [ ] **Step 5: Bind POST chat and welcome before any state access**

Resolve the owner first. If `session_id` is absent, create an owned conversation; if supplied, require it and return uniform HTTP 404 on miss/mismatch. Pass `owner_key` to cold memory and memory graph. `/welcome` must ignore selector-based profile lookup and use only the resolved owner. Attach a newly issued anonymous cookie to JSON and streaming-compatible responses.

- [ ] **Step 6: Run GREEN and nearby tests**

Run: `python -m pytest agent/tests/test_chat_owner_boundary.py tests/test_memory.py agent/tests/test_chat_smoke.py tests/test_integration.py -q`

Expected: PASS; no mismatch test observes or mutates the target sentinel.

- [ ] **Step 7: Commit**

```powershell
git add agent/chat_identity.py agent/memory.py agent/server.py agent/tests/test_chat_owner_boundary.py tests/test_memory.py
git commit -m "fix: bind chat memory to server owner"
```

### Task 2: Owner-scoped exact cache, semantic cache, and budgets

**Files:**
- Modify: `agent/cache.py`
- Modify: `agent/semantic_cache.py`
- Modify: `agent/guardrails.py`
- Modify: `agent/server.py`
- Modify: `tests/test_cache.py`
- Modify: `tests/test_semantic_cache.py`
- Modify: `tests/test_guardrails.py`
- Modify: `agent/tests/test_chat_owner_boundary.py`

- [ ] **Step 1: Add failing owner-namespace regressions**

Prove exact cache, L1, L2, semantic matching, and request dedup return Alice's sentinel only for `owner_key="user:alice"`; Bob gets a miss for the identical or semantically similar query. Prove one owner cannot reset a 100-token ledger by changing conversation IDs:

```python
budget.record_usage("user:alice", 100)
assert budget.check_budget("user:alice")["allowed"] is False
assert budget.check_budget("user:bob")["allowed"] is True
```

At endpoint level, seed an Alice cache reply, present Alice's selector as Bob, and assert the request fails before cache access.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_cache.py tests/test_semantic_cache.py tests/test_guardrails.py agent/tests/test_chat_owner_boundary.py -q`

Expected: FAIL because production callers omit the existing exact-cache namespace and semantic cache/dedup have no owner namespace.

- [ ] **Step 3: Namespace cache APIs by owner**

Change exact `get/put` to accept `owner_key` and use it in Redis and memory keys. Extend semantic `_make_key`, matcher metadata/filtering, `MultiTierCache.get/put/invalidate`, and `RequestDeduplicator.acquire` so exact and fuzzy candidates are considered only within the requested owner. Persist `owner_key` in L2 entries and treat legacy entries without one as a separate non-chat namespace.

- [ ] **Step 4: Use one owner key for admission and settlement**

Rename budget parameter/documentation from session to owner where touched, preserving stored JSON compatibility. In both chat routes, call `check_input(message, owner_key)` and later `record_usage(owner_key, ...)`. Pass `owner_key` to exact and semantic cache reads/writes. Conversation IDs remain only response selectors and analytics labels.

- [ ] **Step 5: Run GREEN**

Run: `python -m pytest tests/test_cache.py tests/test_semantic_cache.py tests/test_guardrails.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_smoke.py agent/tests/test_chat_stream_sse.py -q`

Expected: PASS with isolated sentinels and owner-stable budgets.

- [ ] **Step 6: Commit**

```powershell
git add agent/cache.py agent/semantic_cache.py agent/guardrails.py agent/server.py tests/test_cache.py tests/test_semantic_cache.py tests/test_guardrails.py agent/tests/test_chat_owner_boundary.py
git commit -m "fix: scope chat caches and budgets by owner"
```

### Task 3: Protected POST streaming transport and frontend credentials

**Files:**
- Modify: `agent/server.py`
- Modify: `web-nuxt/components/ChatWidget.vue`
- Modify: `web-nuxt/composables/useAI.ts`
- Modify: `agent/tests/test_chat_stream_sse.py`
- Create: `web-nuxt/tests/chat-transport-security.test.ts`

- [ ] **Step 1: Write failing backend and frontend transport tests**

Backend: POST JSON to `/chat/stream` and assert SSE succeeds; GET with `message`, `history`, and `session_id` returns 405. Frontend source/mounted tests assert both callers use:

```ts
fetch('/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', ...authHeaders() },
  credentials: 'same-origin',
  body: JSON.stringify({ message, history, session_id })
})
```

and assert no `URLSearchParams`, `/chat/stream?`, `message=`, or serialized `history` enters a URL.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest agent/tests/test_chat_stream_sse.py -q
cd web-nuxt
npm test -- --run tests/chat-transport-security.test.ts
```

Expected: FAIL because the backend exposes GET and `ChatWidget.vue` builds a query string; `useAI.ts` omits auth headers.

- [ ] **Step 3: Replace GET streaming with bounded POST JSON**

Use `ChatRequest` for `/chat/stream`, preserving message sanitization, 50-item history bound, response media type, and SSE event shapes. Remove query JSON parsing. Do not retain a GET compatibility route.

- [ ] **Step 4: Update both frontend callers**

Use JSON POST, `authHeaders()`, and `credentials: 'same-origin'`. Keep conversation selector storage behavior unchanged. Do not place the anonymous owner cookie in JavaScript-visible state.

- [ ] **Step 5: Run GREEN, typecheck, and build**

Run:

```powershell
python -m pytest agent/tests/test_chat_stream_sse.py agent/tests/test_chat_owner_boundary.py -q
cd web-nuxt
npm test -- --run tests/chat-transport-security.test.ts tests/smoke.test.ts
npm run typecheck
npm run build
```

Expected: PASS; request URLs contain only `/chat/stream`.

- [ ] **Step 6: Commit**

```powershell
git add agent/server.py agent/tests/test_chat_stream_sse.py web-nuxt/components/ChatWidget.vue web-nuxt/composables/useAI.ts web-nuxt/tests/chat-transport-security.test.ts
git commit -m "fix: move chat streaming payload out of urls"
```

### Task 4: Provider-accurate multi-round usage settlement

**Files:**
- Create: `agent/chat_usage.py`
- Modify: `agent/server.py`
- Modify: `agent/orchestrator.py`
- Modify: `agent/cost_tracker.py`
- Create: `agent/tests/test_chat_usage_accounting.py`
- Modify: `agent/tests/test_chat_stream_sse.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing accumulator and POST regressions**

Use synthetic OpenAI-shaped responses. First response requests a benign tool and reports `120/10`; second returns text and reports `180/25`. Assert provider total `335` equals request aggregate, guardrail increment, and attributed total. Add specialist-fallback and forced-synthesis cases. A cache hit must record zero.

- [ ] **Step 2: Write failing streaming regressions**

Use one decision response and a stream whose terminal chunk reports usage. Add round-exhaustion synthesis, missing-usage fallback, provider error after one completed call, and disconnect/finalizer coverage. Assert every reported usage object is consumed exactly once.

- [ ] **Step 3: Run RED**

Run: `python -m pytest agent/tests/test_chat_usage_accounting.py agent/tests/test_chat_stream_sse.py tests/test_orchestrator.py -q`

Expected: FAIL because routes estimate only visible input/output and synthesis does not settle usage.

- [ ] **Step 4: Implement `UsageAccumulator`**

Add methods for non-stream responses, terminal stream chunks, per-call full-message fallback estimates, token totals, model-aware cost totals, and an idempotent settlement snapshot. Store prompt/completion/total tokens, cost, provider-call count, and estimated-call count.

- [ ] **Step 5: Track every provider boundary**

Wrap orchestrator and direct POST call functions so every returned response is added before its content is used. Pass one accumulator through specialist fallback and forced synthesis. In streaming, request `stream_options={"include_usage": True}`, consume decision responses and terminal stream usage, and include synthesis.

- [ ] **Step 6: Settle once on all terminal paths**

After provider work, commit accumulator totals using `owner_key` to guardrail and cost attribution. Use a finalizer for success, provider error, synthesis, and disconnect. Do not settle on cache hits. Remove outer visible-message/final-reply estimates.

- [ ] **Step 7: Run GREEN and parity tests**

Run: `python -m pytest agent/tests/test_chat_usage_accounting.py agent/tests/test_chat_stream_sse.py tests/test_orchestrator.py agent/tests/test_chat_smoke.py -q`

Expected: PASS; ledger and attribution totals exactly equal synthetic provider totals.

- [ ] **Step 8: Commit**

```powershell
git add agent/chat_usage.py agent/server.py agent/orchestrator.py agent/cost_tracker.py agent/tests/test_chat_usage_accounting.py agent/tests/test_chat_stream_sse.py tests/test_orchestrator.py
git commit -m "fix: account every chat provider round"
```

### Task 5: Cross-cutting verification and remediation evidence

**Files:**
- Modify: `docs/superpowers/plans/2026-07-12-chat-ownership-budgets.md`
- Modify: `docs/superpowers/specs/2026-07-12-chat-ownership-budgets-design.md`
- Modify: `docs/superpowers/plans/2026-07-12-security-remediation-30-60-90.md`
- Write: existing scan bundle `artifacts/fix_report.md`

- [ ] **Step 1: Run focused security suites**

```powershell
python -m pytest agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_usage_accounting.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_smoke.py tests/test_memory.py tests/test_cache.py tests/test_semantic_cache.py tests/test_guardrails.py tests/test_orchestrator.py tests/test_integration.py -q
```

- [ ] **Step 2: Run backend static and full checks**

```powershell
python -m ruff check agent/chat_identity.py agent/chat_usage.py agent/memory.py agent/cache.py agent/semantic_cache.py agent/guardrails.py agent/cost_tracker.py agent/orchestrator.py agent/server.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_usage_accounting.py agent/tests/test_chat_stream_sse.py
python -m py_compile agent/chat_identity.py agent/chat_usage.py agent/memory.py agent/cache.py agent/semantic_cache.py agent/guardrails.py agent/cost_tracker.py agent/orchestrator.py agent/server.py
git diff --check
python -m pytest -q
```

- [ ] **Step 3: Run frontend checks**

```powershell
cd web-nuxt
npm test -- --run
npm run typecheck
npm run build
```

- [ ] **Step 4: Review bypass variants**

Confirm POST, streaming, welcome, exact cache, semantic cache, dedup, guardrail admission, settlement, and cost attribution all consume the same request-scoped owner. Confirm mismatch fails before target mutation, rotating conversation IDs does not reset budget, GET URLs contain no prompt/history, legacy cache entries are not read by chat, and all provider terminal branches settle once.

- [ ] **Step 5: Update evidence and commit**

Mark Workstream 3 complete only after independent spec and quality reviews have no open important issues. Append exact commands/results and remaining uncertainty to the scan fix report, update the master roadmap, and commit documentation. Do not merge or push automatically.
