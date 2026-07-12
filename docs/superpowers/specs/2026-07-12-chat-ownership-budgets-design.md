# Chat Ownership, Cache, Transport, and Usage Design

> STATUS: implemented and verified

## Goal

Close the ten validated chat findings covering POST/SSE conversation ownership, welcome-profile disclosure, exact and semantic cache isolation, query-string disclosure, budget identity, and multi-round provider usage accounting without removing anonymous chat.

## Findings

- `POST /chat` and streaming chat trust a client-selected conversation ID for hot memory and cold profile access.
- `/welcome` reads a cold profile selected only by a supplied session ID.
- Exact and semantic caches can return personalized replies across owners.
- The widget places prompt and history in a GET URL.
- POST and streaming budgets use a caller-selected conversation label, so a new label resets the ledger.
- POST and streaming accounting omit intermediate, fallback, synthesis, and full-prompt provider usage.

## Considered Approaches

### 1. Server-derived owner plus owned conversation selector (selected)

Authenticated requests derive ownership from the validated account ID. Anonymous requests receive a high-entropy server-generated visitor token in a signed `HttpOnly`, `SameSite=Lax` cookie. A public conversation ID remains only a selector and is always looked up under the resolved owner.

This preserves anonymous chat, creates one owner key for memory/cache/budget/accounting, and rejects a copied conversation ID before any target read or write.

### 2. Require login for all chat

This gives a simple owner boundary but removes the current anonymous product path and is broader than the security requirement.

### 3. Treat the conversation ID as a secret capability

A high-entropy capability could protect one conversation but would still conflate conversation selection with persistent profile and budget ownership. Rotating conversations would continue to reset owner-level controls.

## Owner Resolution

One request-scoped `ChatOwnerContext` is resolved before conversation, cache, or ledger access:

- authenticated: `owner_key = "user:" + user.id`;
- anonymous: validate the signed visitor cookie and derive `owner_key = "anon:" + sha256(visitor_id)`;
- missing or invalid anonymous cookie: generate a new random visitor ID, sign it with `CHAT_OWNER_SECRET`, and attach it to the response;
- production requires `CHAT_OWNER_SECRET` or the existing deployment secret; development may use an ephemeral secret.

The raw visitor token is never accepted from JSON/query parameters and never used in logs or persistence keys. Frontend requests include existing auth headers for signed-in users and normal same-origin credentials for the anonymous cookie.

## Conversation Ownership

`MemoryManager` stores hot sessions under `(owner_key, conversation_id)`. It exposes separate creation and owned lookup operations:

- no conversation ID: create a high-entropy server-issued ID for the current owner;
- supplied owned ID: return that owner's existing hot session;
- unknown or mismatched ID: return the same 404 before message writes, prompt construction, profile access, cache access, or provider calls;
- lookup never implicitly creates a supplied conversation ID.

Cold profiles and memory-graph context use `owner_key`, not `conversation_id`. Two conversations for one owner share only the intended owner profile and retain separate hot histories. `/welcome` ignores client conversation ownership and reads only the resolved owner's profile.

## Cache and Budget Boundaries

Exact cache keys include `owner_key`. Semantic cache entries and request-dedup slots also carry an owner namespace; semantic matching considers only entries in the same namespace. Chat never reads a shared anonymous/global personalized cache entry.

Guardrail admission and settlement both use `owner_key`. Changing or omitting a conversation ID cannot create a new budget. Cost attribution uses the same owner key. Conversation IDs may remain in non-security analytics only where they describe a conversation, not a payer or profile owner.

## Streaming Transport

Streaming becomes `POST /chat/stream` with the same bounded JSON body contract as `POST /chat`: `message`, `history`, and optional `session_id`. Prompt and history never enter the request URL. The old GET route is removed, so GET receives method-not-allowed behavior and cannot become a compatibility bypass.

Both `ChatWidget.vue` and `useAI.ts` send JSON POST requests, attach `authHeaders()`, preserve cookies, and store only the returned conversation selector in client state.

## Provider Usage Accounting

Each request owns a `UsageAccumulator`. Every provider response is consumed exactly once at the call boundary:

- normal decision/tool rounds;
- specialist fallback and forced synthesis;
- direct non-orchestrated rounds;
- streaming decision rounds;
- final stream and round-exhaustion synthesis stream.

Non-stream responses use provider `usage`. Streams request terminal usage metadata and consume it once. If a provider omits usage, the accumulator estimates that individual call from its complete serialized messages plus generated output and marks it estimated; it never falls back to only the outer user message and visible final answer.

The accumulated provider totals are committed once to the guardrail ledger and cost attribution on every terminal path after provider work. Cache hits add zero provider usage. The invariant is:

`sum(provider-call usage) == request usage == guardrail increment == attributed usage`.

## Error and Compatibility Semantics

- Owner mismatch and unknown supplied conversation IDs return a uniform 404 with no target-state mutation.
- Invalid visitor cookies are replaced with a new anonymous owner rather than producing an ownership oracle.
- Guardrail failures remain fail-closed and are charged only for provider work already completed.
- Cache hits retain existing response/SSE shapes and are not charged as provider usage.
- Anonymous chat remains available; signed-in chat uses the account owner automatically.
- Existing limits, sanitization, output validation, tool caps, and rate limits remain unchanged.

## Verification

- Endpoint regressions capture model inputs and prove another owner's sentinel never appears in POST, streaming, welcome, exact cache, or semantic cache paths.
- Memory tests prove owned creation, owned continuation, mismatch rejection, no implicit lookup creation, shared owner profile, and separate hot histories.
- Budget tests prove label rotation cannot reset usage and independent owners remain separate.
- Synthetic multi-round provider tests prove exact usage parity for POST, streaming, synthesis, fallback, missing-usage, cache-hit, and error paths without network access.
- Frontend tests prove JSON POST streaming, auth headers, cookie-compatible requests, and absence of message/history in URLs.
- Focused suites, full pytest, Ruff, `py_compile`, frontend tests, typecheck, build, and independent spec/quality review gate completion.

## Implementation Evidence

Implemented on branch `codex/chat-ownership-budgets`; fresh final verification covers code HEAD `0ae1ceb6c39addc6d1f68c9a19febb46140681ab`. The earlier production/accounting closure is `12454a59c5c95dc29ea97605163f5fb2950fb34a`, followed by cancellation harness stabilization `6d3d5e0c59590e056b804bae1702539769032cd0`.

- Final-review semantic dedup remediation landed in `b053c4a`, `f7259a3`, `4b56bc8`, `240dac6`, and `86c1353`; history continuity landed in `affa524`; fragmented SSE and reader lifecycle landed in `8c1af0a`, `cad268a`, and `0ae1ceb`.
- The exact Task 5 focused security suite completed with `350 passed, 51 deselected, 1 warning`; the separate history-continuity suite completed with `22 passed, 1 warning`.
- Specified Ruff and `py_compile` gates passed; `git diff --check` passed.
- Full backend verification completed with `6102 passed, 39 skipped, 78 deselected, 1 xfailed, 1 warning`.
- Frontend verification completed with `8` test files / `125 passed` tests, typecheck exit `0`, and production build exit `0`.
- Change-aware verification completed owner/admission/history `31 passed`, provider exact-once `13 passed`, semantic/terminal lifecycle `28 passed`, frontend transport/SSE/stale retry `23 passed`, and ten repeated cancellation iterations totaling `60/60` checks.
- Nested direct and orchestrated provider paths retained exact `3` calls / `30` tokens. Dedup saturation woke the evicted waiter and kept generation maps consistent, with a bounded 501 pending entries due to pre-insert cleanup against the nominal 500 cap.
- Fresh Browser proof rendered exactly one `Xin chào Vĩnh Long` reply from a stream fragmented across JSON and the multibyte `ĩ`, retained the clean URL `http://127.0.0.1:8360/`, and produced no Browser warning/error logs.
- The earlier review at `12454a5` was superseded by the three remediation groups above. Fresh change-aware review at `0ae1ceb` found no new Important issue.

The original issue variants no longer reproduce: admission occurs before selector lookup, owner mismatch precedes target mutation, and new sessions are created only after admission; POST/SSE/welcome/cache sentinels do not cross owners; owner rotation does not reset admission or settlement identity; GET streaming is unavailable and browser URLs contain no prompt/history; legacy cache namespaces are not read by chat; semantic leases terminate across exact-hit, miss/non-cacheable, error, cancellation, setup, and ASGI-start branches; history prior/current turns appear exactly once with hot summary/hydration continuity and context-aware cache eligibility; and provider totals match request, guardrail, and attribution totals across direct, orchestrated, parallel, nested-tool, streaming, synthesis, error, and cancellation paths.

## Verified Residuals

- Clearing the anonymous owner cookie intentionally starts a new anonymous identity, history, and budget namespace.
- Owner-correct admission does not yet reserve and commit provider capacity atomically across parallel requests.
- The unrelated `/feedback` endpoint still accepts a session-like label and is outside this workstream.
- Explicit provider all-zero usage cannot be distinguished from absent metadata, so the call is estimated conservatively.
- A settlement sink that mutates and then raises is not covered; a later retry could duplicate that individual sink's side effect.
- Disconnect before terminal stream usage arrives falls back to complete-message/output estimation rather than provider-reported totals.
- Cancellation deliberately waits for the synchronous provider worker to complete before settlement; provider completion and configured provider timeouts bound that wait.
- Dedup saturation permits 501 pending entries against the nominal 500 constant because cleanup runs before insertion; waiter wakeup and generation consistency remain correct.
- The development frontend build retains the known large-chunk/dynamic-import warning.

## Non-Goals

- No login requirement for anonymous chat.
- No database migration for persistent server-side anonymous sessions in this workstream.
- No redesign of unrelated feedback/checkpoint endpoints that also accept session-like labels.
- No global provider reservation/parallel-admission architecture; owner-correct accounting is complete, while atomic reserve/commit belongs with broader bounded-work controls.
