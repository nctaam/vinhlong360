# Runtime Trust Boundary Implementation Plan

> STATUS: done - Runtime Trust Boundary implementation and local evidence are complete at `a0a3a02c`; the separate Verified Erasure Lifecycle plan remains pending.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure chat data crosses one mandatory privacy boundary before provider, cache, persistence, logging, or SSE use, and replace state-changing public feedback with receipt-bound aggregate telemetry.

**Architecture:** A committed privacy-policy artifact feeds backend settings, readiness, and Nuxt legal copy. `agent/privacy_boundary.py` owns source-aware input/output redaction and bounded streaming release; chat routes consume immutable safe values and sink modules accept owner-attributed safe content only. PostgreSQL stores one-time feedback receipt digests and daily aggregate counters, while chat remains available when receipt issuance is unavailable.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, PostgreSQL, psycopg2, httpx ASGI transport, pytest, Nuxt 4, Vue 3, TypeScript, Vitest.

## Global Constraints

- The approved account-erasure deadline is exactly 30 days from the account-deletion request; active accounts do not receive a rolling 30-day TTL.
- `config/privacy-policy.json` is the committed authority for `accountErasureDeadlineDays=30`, `recoveryEnabledDuringGracePeriod=true`, `feedbackMode="telemetry_only"`, `feedbackReceiptTtlHours=24`, and `retainDeidentifiedAggregates=true`.
- The privacy boundary is mandatory. Do not add `HAS_PRIVACY_BOUNDARY`, optional imports, fail-open fallbacks, or raw-data compatibility paths.
- User input, history, untrusted tool output, provider output, old cache entries, analytics, cost, optimizer, memory, graph, feedback, and logs must receive only boundary-produced values.
- Only exact contact values loaded from a published database field in the current response context may use `verified_public_contact`; provider-generated or unmatched contact data remains redacted.
- SSE may emit only confirmed-safe text. Cancellation, generator failure, or redactor failure must discard the unverified suffix.
- Public feedback accepts only `receipt` and `rating`. It must never call memory feedback, personalization, `learn_loop`, entity confidence mutation, the knowledge database, or `web/data.json` mutation.
- Feedback limits are 30 requests per IP per hour and 20 attempts per resolved owner per hour. Malformed, invalid, expired, wrong-owner, replayed, and accepted attempts all consume the applicable limit.
- Receipt TTL is 24 hours. PostgreSQL stores token digests, owner binding digests, bounded dimensions, rating, and timestamps only; it never stores raw query, reply, entity ID, or session ID.
- Do not add Redis, Kafka, a worker service, a paid anti-abuse service, a SaaS processor, or another runtime dependency.
- Do not deploy, push, rotate secrets, activate destructive erasure, run a scrub with `--apply`, or mutate production data in this plan.
- Follow strict RED-GREEN-REFACTOR TDD. Each numbered task gets a fresh implementation subagent, then an independent spec-compliance and code-quality review before the next task starts.
- Preserve the current chat owner contract (`user:<uuid>` or `anon:<sha256>`), POST/SSE request bounds, session ownership, cache isolation, usage settlement, and fail-closed guardrail behavior.
- Task 7 reserves migration number `071`; the Verified Erasure Lifecycle plan begins at migration `072`.

---

### Task 1: Shared Privacy Policy Authority

**Files:**
- Create: `config/privacy-policy.json`
- Create: `agent/privacy_policy.py`
- Modify: `agent/config.py`
- Modify: `agent/server.py:3262`
- Modify: `web-nuxt/nuxt.config.ts`
- Modify: `web-nuxt/utils/legalContent.ts`
- Create: `agent/tests/test_privacy_policy.py`
- Modify: `tests/test_config.py`
- Create: `web-nuxt/tests/legal-privacy-retention.test.ts`

**Interfaces:**
- Produces: frozen `PrivacyPolicy` and `load_privacy_policy(path: Path | None = None) -> PrivacyPolicy`.
- Produces settings fields `ACCOUNT_ERASURE_DEADLINE_DAYS`, `RECOVERY_ENABLED_DURING_GRACE_PERIOD`, `FEEDBACK_MODE`, `FEEDBACK_RECEIPT_TTL_HOURS`, and `RETAIN_DEIDENTIFIED_AGGREGATES`.
- Produces `privacy_policy_readiness(settings) -> bool`, consumed by `/health/ready` and the second implementation plan.
- Preserves `settings.ACCOUNT_DELETE_GRACE_DAYS` as a read-only compatibility property returning `ACCOUNT_ERASURE_DEADLINE_DAYS`; no independent default remains.

- [ ] **Step 1: Write failing backend policy tests**

Create `agent/tests/test_privacy_policy.py` with literal contract assertions:

```python
from pathlib import Path

import pytest

from privacy_policy import PrivacyPolicyError, load_privacy_policy


POLICY = Path(__file__).resolve().parents[2] / "config" / "privacy-policy.json"


def test_committed_privacy_policy_has_approved_values():
    policy = load_privacy_policy(POLICY)
    assert policy.account_erasure_deadline_days == 30
    assert policy.recovery_enabled_during_grace_period is True
    assert policy.feedback_mode == "telemetry_only"
    assert policy.feedback_receipt_ttl_hours == 24
    assert policy.retain_deidentified_aggregates is True


def test_policy_rejects_unknown_or_invalid_values(tmp_path):
    path = tmp_path / "privacy-policy.json"
    path.write_text('{"accountErasureDeadlineDays": 0, "extra": true}', encoding="utf-8")
    with pytest.raises(PrivacyPolicyError):
        load_privacy_policy(path)
```

Extend `tests/test_config.py` to prove development may instantiate settings with policy defaults, production rejects `ACCOUNT_ERASURE_DEADLINE_DAYS=20`, and the compatibility property equals 30.

- [ ] **Step 2: Write the failing Nuxt legal-copy test**

Create `web-nuxt/tests/legal-privacy-retention.test.ts`:

```ts
import { describe, expect, it } from 'vitest'

import privacyPolicy from '#privacy-policy'
import { LEGAL_PRIVACY } from '../utils/legalContent'

describe('privacy retention authority', () => {
  it('renders the committed account-erasure deadline', () => {
    expect(privacyPolicy.accountErasureDeadlineDays).toBe(30)
    const rights = LEGAL_PRIVACY.sections.find(section => section.heading.startsWith('4.'))
    expect(rights?.body).toContain('30 ngày kể từ khi yêu cầu xoá tài khoản')
    expect(rights?.body).not.toContain('20 ngày')
  })
})
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_policy.py tests/test_config.py
cd web-nuxt
npx vitest run tests/legal-privacy-retention.test.ts
```

Expected: backend import/file failures and Nuxt alias/import failure because the authority does not exist.

- [ ] **Step 4: Implement the committed policy loader and settings projection**

Create the exact JSON artifact:

```json
{
  "accountErasureDeadlineDays": 30,
  "recoveryEnabledDuringGracePeriod": true,
  "feedbackMode": "telemetry_only",
  "feedbackReceiptTtlHours": 24,
  "retainDeidentifiedAggregates": true
}
```

Create `agent/privacy_policy.py` with this public shape:

```python
from dataclasses import dataclass
from pathlib import Path


class PrivacyPolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrivacyPolicy:
    account_erasure_deadline_days: int
    recovery_enabled_during_grace_period: bool
    feedback_mode: str
    feedback_receipt_ttl_hours: int
    retain_deidentified_aggregates: bool
```

Implement the exact public signatures `load_privacy_policy(path: Path | None = None) -> PrivacyPolicy` and `privacy_policy_readiness(settings) -> bool`.

Use `json.loads`, reject missing/extra keys, reject booleans where integers are required, require days in `1..365`, TTL in `1..168`, and require `feedbackMode == "telemetry_only"`. Load the repository file from `Path(__file__).resolve().parents[1] / "config" / "privacy-policy.json"` when `path` is omitted.

In `agent/config.py`, set Pydantic defaults from the loaded policy and add a production-only validator that rejects contradictory environment overrides. Keep:

```python
@property
def ACCOUNT_DELETE_GRACE_DAYS(self) -> int:
    return self.ACCOUNT_ERASURE_DEADLINE_DAYS
```

Add `checks["privacy_policy"] = privacy_policy_readiness(settings)` to `/health/ready`; expose no policy secret or raw config values.

- [ ] **Step 5: Wire the Nuxt alias and legal copy**

Add to `web-nuxt/nuxt.config.ts`:

```ts
alias: {
  '#launch-config': fileURLToPath(new URL('../config', import.meta.url)),
  '#privacy-policy': fileURLToPath(new URL('../config/privacy-policy.json', import.meta.url)),
},
```

Import the JSON in `web-nuxt/utils/legalContent.ts`, interpolate the exact duration, and update only the account-deletion paragraph and `updated_date`. Do not change unrelated About/Terms content in this task.

- [ ] **Step 6: Run focused tests and readiness compatibility**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_policy.py tests/test_config.py agent/tests/test_session_be.py -k "readiness or grace or config"
cd web-nuxt
npx vitest run tests/legal-privacy-retention.test.ts
npx vue-tsc --noEmit
```

Expected: all selected tests pass; production mismatch returns a false readiness policy or validation failure without changing the committed value.

- [ ] **Step 7: Commit and review**

```powershell
git add config/privacy-policy.json agent/privacy_policy.py agent/config.py agent/server.py agent/tests/test_privacy_policy.py tests/test_config.py web-nuxt/nuxt.config.ts web-nuxt/utils/legalContent.ts web-nuxt/tests/legal-privacy-retention.test.ts
git commit -m "feat: centralize privacy policy authority"
```

Review gate: confirm there is one committed duration, no duplicated `20`/`30` runtime default, and no unrelated legal-copy rewrite.

---

### Task 2: Mandatory Privacy Boundary Core

**Files:**
- Create: `agent/privacy_boundary.py`
- Create: `agent/tests/test_privacy_boundary.py`
- Modify: `agent/guardrails.py`
- Modify: `tests/test_guardrails.py`

**Interfaces:**
- Produces: `PrivacyBoundaryBlocked`, `PrivacyBoundaryUnavailable`, `PrivacySource`, `SafeHistoryItem`, `SafeChatInput`, and `SafeText`.
- Produces: `prepare_chat_input(message, history, *, owner_key) -> SafeChatInput`.
- Produces: `redact_text(text, *, source, verified_public_contacts=()) -> SafeText` and `redact_payload(value, *, source, verified_public_contacts=())`.
- Produces: `prepare_chat_output(reply, *, query, entities, verified_public_contacts=()) -> SafeText`.
- Produces: `StreamingPIIRedactor.feed(chunk) -> str`, `finish() -> str`, and `abort() -> None`.

- [ ] **Step 1: Write failing immutable-envelope and provenance tests**

Create tests that assert exact immutable output and source rules:

```python
from dataclasses import FrozenInstanceError

import pytest

from privacy_boundary import prepare_chat_input, redact_text


def test_prepare_chat_input_redacts_message_and_every_history_item():
    safe = prepare_chat_input(
        "Goi toi 0901234567",
        [
            {"role": "user", "content": "Email a@example.com"},
            {"role": "assistant", "content": "Da ghi nhan 0909999999"},
        ],
        owner_key="user:alice",
    )
    assert "0901234567" not in safe.message
    assert "a@example.com" not in safe.history[0].content
    assert "0909999999" not in safe.history[1].content
    with pytest.raises(FrozenInstanceError):
        safe.message = "raw"


def test_verified_public_contact_requires_exact_allowlisted_value():
    allowed = redact_text(
        "Lien he 02703822000",
        source="verified_public_contact",
        verified_public_contacts=("02703822000",),
    )
    invented = redact_text(
        "Lien he 0901234567",
        source="verified_public_contact",
        verified_public_contacts=("02703822000",),
    )
    assert "02703822000" in allowed.text
    assert "0901234567" not in invented.text
```

Add rejection tests for unknown roles, extra history fields, non-string content, blocked prompt injection, and exceptions from the underlying guardrail.

- [ ] **Step 2: Write failing streaming boundary tests**

Cover PII split at every chunk boundary, normal finish, and abort:

```python
def test_stream_redactor_withholds_split_email_until_safe():
    redactor = StreamingPIIRedactor(max_pattern_span=512)
    emitted = redactor.feed("Lien he test@")
    emitted += redactor.feed("example.com de biet them")
    emitted += redactor.finish()
    assert "test@example.com" not in emitted
    assert "[EMAIL]" in emitted


def test_stream_abort_discards_unverified_suffix():
    redactor = StreamingPIIRedactor(max_pattern_span=512)
    assert redactor.feed("So dien thoai 0901") == ""
    redactor.abort()
    assert redactor.finish() == ""
```

Parametrize email, Vietnamese phone, CCCD, bank account, passport, API-key/secret sentinel, and PII-like token runs longer than the bounded suffix. The overlong case must prove the implementation replaces or withholds the candidate instead of emitting its prefix.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_boundary.py tests/test_guardrails.py
```

Expected: import failure because `privacy_boundary.py` does not exist.

- [ ] **Step 4: Expose raw PII spans from guardrails without changing existing callers**

Add a pure detector API to `PIIMasker`:

```python
@dataclass(frozen=True)
class PIISpan:
    kind: str
    start: int
    end: int


```

Add the exact method signature `detect_spans(self, text: str) -> tuple[PIISpan, ...]`.

Refactor `mask()` to consume merged spans while preserving existing replacement labels and existing `check_input()`/`check_output()` result shapes. Merge overlapping spans and never log raw matched values.

- [ ] **Step 5: Implement immutable safe types and source-aware redaction**

Create `agent/privacy_boundary.py` with these definitions:

```python
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

PrivacySource = Literal[
    "private_user_data",
    "untrusted_external",
    "verified_public_contact",
    "provider_output",
    "legacy_cache",
    "log",
]


@dataclass(frozen=True)
class SafeHistoryItem:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class SafeChatInput:
    message: str
    history: tuple[SafeHistoryItem, ...]
    redaction_types: tuple[str, ...]


@dataclass(frozen=True)
class SafeText:
    text: str
    redaction_types: tuple[str, ...] = ()
```

`prepare_chat_input()` must invoke injection/budget checks once, use `guard["message"]` rather than the raw input, validate history keys exactly as `{"role", "content"}`, redact every item, and raise typed exceptions instead of returning raw fallback data. `redact_payload()` recursively handles strings, dicts, lists, and tuples while preserving non-string scalar values.

`prepare_chat_output()` must call the current factuality/output guardrail, require its cleaned reply, then apply provider-output redaction again as defense in depth. On any exception, raise `PrivacyBoundaryUnavailable`; do not return the original reply.

- [ ] **Step 6: Implement bounded streaming release**

Use raw span coordinates, not replacement-string lengths. Define a maximum supported span for every PII pattern and a conservative token-character class for email/secret/account candidates. A candidate run that reaches the bounded suffix limit without a safe delimiter is replaced with a fixed redaction marker; it is never emitted incrementally and buffering never grows without bound.

On each `feed()`:

1. append the raw chunk to `_pending`;
2. set `candidate_cut = max(0, len(_pending) - max_pattern_span)`;
3. detect spans across the full pending buffer;
4. move `candidate_cut` left to the start of any span crossing the cut;
5. redact and emit only `_pending[:candidate_cut]`;
6. retain the unverified suffix.

`finish()` redacts and emits the remaining suffix only after normal provider completion. `abort()` clears the suffix and permanently prevents `finish()` from emitting it. Reject non-positive or unreasonably small `max_pattern_span`; use a production default of 512 characters. Unit tests must assert both bounded memory and zero raw-prefix leakage for overlong candidate tokens.

- [ ] **Step 7: Run unit and guardrail regressions**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_boundary.py tests/test_guardrails.py agent/tests/test_resilience.py -k "guardrail or privacy or pii"
```

Expected: all selected tests pass and existing guardrail result shapes remain compatible.

- [ ] **Step 8: Commit and review**

```powershell
git add agent/privacy_boundary.py agent/guardrails.py agent/tests/test_privacy_boundary.py tests/test_guardrails.py
git commit -m "feat: add mandatory privacy boundary"
```

Review gate: inspect span arithmetic, normal versus aborted flush behavior, immutable types, verified-contact exact matching, and fail-closed exceptions.

---

### Task 3: Enforce Safe Input In POST And SSE Routes

**Files:**
- Modify: `agent/server.py:1410`
- Create: `agent/tests/test_chat_privacy_transport.py`
- Modify: `agent/tests/test_chat_history_continuity.py`
- Modify: `agent/tests/test_chat_stream_sse.py`

**Interfaces:**
- Consumes: `prepare_chat_input()` and typed boundary exceptions from Task 2.
- Produces: route-local `safe_input`, `message`, and `history` values used for every downstream read.
- Produces: source invariant `_privacy_input_boundary_marker` in both routes so scanner tests can prove raw request fields are not read later.

- [ ] **Step 1: Write failing real-transport input tests**

Use `httpx.AsyncClient` with real `ASGITransport`, not direct handler calls:

```python
import httpx
import pytest

import server


@pytest.mark.anyio
async def test_post_provider_receives_only_redacted_message_and_history(monkeypatch):
    captured = {}
    fake = _fake_nonstream_client(captured)
    monkeypatch.setattr(server, "get_client", lambda: fake)
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "message": "Goi 0901234567",
                "history": [{"role": "user", "content": "Mail a@example.com"}],
            },
        )
    assert response.status_code == 200
    serialized = repr(captured["messages"])
    assert "0901234567" not in serialized
    assert "a@example.com" not in serialized
```

Add the equivalent SSE POST test and a boundary-failure test proving the provider, memory, cache, and analytics mocks receive zero calls.

- [ ] **Step 2: Write the failing source invariant**

Use `inspect.getsource` to split each route after a literal marker:

```python
@pytest.mark.parametrize("route", [server.chat, server.chat_stream])
def test_route_never_reads_raw_chat_fields_after_privacy_boundary(route):
    source = inspect.getsource(route)
    tail = source.split("_privacy_input_boundary_marker", 1)[1]
    assert "req.message" not in tail
    assert "req.history" not in tail
    assert "req.history_messages()" not in tail
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_history_continuity.py agent/tests/test_chat_stream_sse.py
```

Expected: transport captures raw sentinels or the source invariant fails.

- [ ] **Step 4: Move the boundary before every data consumer**

In each route, capture only non-content request metadata first:

```python
requested_session_id = req.session_id or ""
safe_input = prepare_chat_input(
    req.message,
    [item.model_dump() for item in req.history],
    owner_key=owner_key,
)
_privacy_input_boundary_marker = True
message = safe_input.message
history = [
    {"role": item.role, "content": item.content}
    for item in safe_input.history
]
```

After the marker, use `message` for guardrail-safe cache keys, provider prompts, analytics, optimizer, memory, graph, and quality evaluation. Use `history` for hydration and prompt assembly. Never preserve a `raw_message` alias. Keep request/session bounds enforced by Pydantic before the boundary.

Map `PrivacyBoundaryBlocked` to the current generic safety response and `PrivacyBoundaryUnavailable` to the current generic unavailable response. Log stable reason codes only.

- [ ] **Step 5: Preserve history de-duplication with safe content**

Move the trailing duplicate-user removal into `prepare_chat_input()` or a helper that operates on `SafeHistoryItem`; delete route dependence on `ChatRequest.history_messages()`. Keep the existing 50-item/8000-character bounds and `extra="forbid"` behavior.

- [ ] **Step 6: Run transport and owner/cache regressions**

Run:

```powershell
python -m pytest -q agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_history_continuity.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_usage_accounting.py
```

Expected: all selected tests pass; session ownership, semantic leases, and usage settlement remain unchanged.

- [ ] **Step 7: Commit and review**

```powershell
git add agent/server.py agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_history_continuity.py agent/tests/test_chat_stream_sse.py
git commit -m "fix: enforce safe chat input boundary"
```

Review gate: read both complete handlers and confirm the first cache/memory/provider/analytics use occurs after the boundary and uses no raw alias.

---

### Task 4: Sanitize Tools, Provider Output, And Personal Sinks

**Files:**
- Modify: `agent/server.py:1788`
- Modify: `agent/analytics.py`
- Modify: `agent/cost_tracker.py`
- Modify: `agent/self_optimizer.py`
- Modify: `agent/experience_memory.py`
- Modify: `agent/prompt_compiler.py`
- Modify: `agent/ab_testing.py`
- Create: `agent/tests/test_privacy_sink_boundary.py`
- Modify: `agent/tests/test_analytics.py`
- Modify: `agent/tests/test_experience_memory.py`
- Modify: `agent/tests/test_chat_usage_accounting.py`

**Interfaces:**
- Consumes: `redact_payload()` and `prepare_chat_output()` from Task 2.
- Produces: `_safe_tool_result(result, verified_public_contacts) -> str` and `_safe_delivered_reply(reply, query, entities, verified_public_contacts) -> SafeText` in `agent/server.py`.
- Adds explicit `owner_key` keyword parameters to personal sink APIs while preserving existing positional compatibility where tests require it.
- Produces owner-attributed records that the Verified Erasure Lifecycle plan can purge without reverse-mapping random session IDs.

- [ ] **Step 1: Write failing tool/provider/sink sentinel tests**

Create spies for memory, graph, analytics, optimizer, cost attribution, experience memory, prompt demos, and A/B records. Deliver a provider response and tool result containing distinct phone/email sentinels, then assert every captured argument excludes both values.

Add a provider-output failure case:

```python
def test_output_boundary_failure_writes_nothing(monkeypatch, client_mocked):
    monkeypatch.setattr(server, "prepare_chat_output", lambda *_a, **_k: (_ for _ in ()).throw(
        PrivacyBoundaryUnavailable("OUTPUT_REDACTION_FAILED")
    ))
    writes = _install_personal_sink_spies(monkeypatch)
    response = client_mocked.post("/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert response.json()["reply"] == server.SAFE_PRIVACY_FAILURE_REPLY
    assert writes == []
```

- [ ] **Step 2: Write failing owner-attribution tests**

For each file store, persist one record and assert it contains `owner_key="user:alice"` but contains no raw sentinel. Require:

```python
analytics.track_query("safe q", ["search"], "safe a", "sid", owner_key="user:alice")
record_outcome("sid", "safe q", "direct", [], 8, 1.0, 10, owner_key="user:alice")
experience_memory.record("safe q", [], 9, "safe a", owner_key="user:alice")
prompt_compiler.record_demo("safe q", "safe a", 9, owner_key="user:alice")
ab_manager.record_outcome("prompt_style", "sid", 9, owner_key="user:alice")
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_sink_boundary.py agent/tests/test_analytics.py agent/tests/test_experience_memory.py agent/tests/test_chat_usage_accounting.py
```

Expected: tool/provider sentinels reach sinks and owner-key keyword arguments are unsupported.

- [ ] **Step 4: Redact untrusted tool output before prompt append or persistence**

At the one tool-result admission point, parse JSON when possible, call:

```python
safe_result = redact_payload(
    parsed_or_text,
    source="untrusted_external",
    verified_public_contacts=verified_public_contacts,
)
```

Serialize the redacted structure and append only that value to provider messages. Build `verified_public_contacts` only from exact currently selected published entity fields; never infer trust from tool name or string shape.

- [ ] **Step 5: Move output redaction before the first sink**

For non-stream and every fallback/synthesis path:

```python
safe_reply = prepare_chat_output(
    reply,
    query=message,
    entities=knowledge._entities,
    verified_public_contacts=verified_public_contacts,
)
reply = safe_reply.text
_privacy_output_boundary_marker = True
```

Only after the marker may code write memory, graph, extraction, analytics, optimizer, cost, experience, prompt demos, A/B data, exact cache, or semantic cache. Boundary failure returns the generic safe failure and abandons any semantic lease without persisting the raw reply.

- [ ] **Step 6: Add owner attribution and safe-content fields to personal stores**

Add `owner_key` to record shapes and cap all retained text at the current limits. Keep aggregate/stat APIs compatible. For `cost_tracker.CostAttribution.record`, rename the persisted `session_id` semantic to `owner_key` while keeping the public positional slot stable; include a one-time loader compatibility path that maps old `session_id` records to an empty owner rather than guessing ownership.

Do not add purge code yet; the second plan owns lifecycle adapters. Do not let global learning pools consume unredacted text.

- [ ] **Step 7: Run sink and chat regressions**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_sink_boundary.py agent/tests/test_analytics.py agent/tests/test_experience_memory.py agent/tests/test_prompt_compiler.py agent/tests/test_chat_usage_accounting.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_smoke.py
```

Expected: all selected tests pass, with existing integration markers/skips preserved.

- [ ] **Step 8: Commit and review**

```powershell
git add agent/server.py agent/analytics.py agent/cost_tracker.py agent/self_optimizer.py agent/experience_memory.py agent/prompt_compiler.py agent/ab_testing.py agent/tests/test_privacy_sink_boundary.py agent/tests/test_analytics.py agent/tests/test_experience_memory.py agent/tests/test_chat_usage_accounting.py
git commit -m "fix: sanitize chat tools and personal sinks"
```

Review gate: compare the output marker against every sink call, inspect exact verified-contact provenance, and confirm no global learning path receives raw user/provider text.

---

### Task 5: Confidential SSE And Legacy Cache Delivery

**Files:**
- Modify: `agent/server.py:2544`
- Modify: `agent/tests/test_chat_stream_sse.py`
- Modify: `agent/tests/test_chat_privacy_transport.py`
- Modify: `agent/tests/test_chat_owner_boundary.py`
- Modify: `web-nuxt/tests/sse-stream.test.ts`

**Interfaces:**
- Consumes: `StreamingPIIRedactor`, `redact_text()`, and `prepare_chat_output()`.
- Produces: `_safe_cached_reply(reply) -> SafeText` shared by POST and SSE cache-hit paths, plus `_safe_stream_text_events(chunks, redactor)` behavior in the SSE generator.
- Guarantees that non-stream cached POST replies and normal provider, exact-cache, semantic-cache, fallback, and synthesis streams contain only redacted text.

- [ ] **Step 1: Write failing real-transport chunk-boundary tests**

Use a provider stream that splits `secret@example.com` at each possible index. For every split, collect actual SSE frames through `httpx.AsyncClient.stream()` and assert the raw email never appears in concatenated wire bytes.

Add exact/semantic legacy cache entries containing a raw phone sentinel and prove both cached POST responses and streamed cache hits are redacted before delivery. Assert any refreshed cache write contains only the safe value.

- [ ] **Step 2: Write failing cancellation and redactor-error tests**

Inject a redactor that withholds `0901`, then cancel the client or raise from `feed()`. Assert:

```python
assert "0901" not in wire_text
assert not memory_writes
assert not cache_writes
assert not analytics_writes
assert semantic_lease_was_abandoned is True
```

The terminal frame may be a generic `error`; it must not include raw exception text.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_chat_stream_sse.py agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_owner_boundary.py
cd web-nuxt
npx vitest run tests/sse-stream.test.ts
```

Expected: raw split PII appears in `text` frames or legacy cache paths bypass the redactor.

- [ ] **Step 4: Redact every streaming source before wire emission**

Instantiate one redactor per delivered answer. Provider chunks pass through `feed()`; emit a `text` frame only when the returned string is non-empty. After a normal provider terminal chunk, append `finish()`. On `CancelledError`, `GeneratorExit`, producer exception, or redactor exception, call `abort()`, abandon the semantic lease, skip sinks, and emit no suffix.

For exact/semantic cache and fallback strings, classify them as `legacy_cache`/`provider_output` and sanitize the entire string first. Cached POST returns use the same safe value directly; SSE chunks that safe value only for UI pacing. Never return an old cache object before the shared cache-delivery boundary.

- [ ] **Step 5: Persist the assembled safe stream only after normal completion**

Build `full_text` from emitted safe strings, not raw provider chunks. Run final factuality checks on safe text, then persist/cache only the returned safe text. Usage accounting may count raw provider token totals but must not serialize raw completion text to cost records or logs.

- [ ] **Step 6: Run backend and frontend SSE regressions**

Run:

```powershell
python -m pytest -q agent/tests/test_chat_stream_sse.py agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_history_continuity.py agent/tests/test_chat_usage_accounting.py
cd web-nuxt
npx vitest run tests/sse-stream.test.ts tests/chat-transport-security.test.ts
```

Expected: all selected tests pass and every stream still terminates with `done` or a generic safe `error`.

- [ ] **Step 7: Commit and review**

```powershell
git add agent/server.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_owner_boundary.py web-nuxt/tests/sse-stream.test.ts
git commit -m "fix: redact SSE before transport emission"
```

Review gate: inspect every `yield` of `type='text'`, confirm `full_text` is assembled from emitted safe text, and exercise cancellation before approving.

---

### Task 6: Structured Log Defense, Metrics, And Source Guards

**Files:**
- Modify: `agent/middleware.py:37`
- Modify: `agent/metrics.py`
- Modify: `agent/server.py:3262`
- Create: `agent/tests/test_privacy_logging.py`
- Create: `agent/tests/test_privacy_source_guards.py`
- Modify: `agent/tests/test_resilience.py`

**Interfaces:**
- Produces: `redact_log_value(value) -> object` in `privacy_boundary.py` or a thin middleware adapter.
- Produces metrics `privacy_redactions_total{source,type}` and `privacy_boundary_failures_total{stage}`.
- Produces source checks that reject raw request use after markers and persistence before output markers.

- [ ] **Step 1: Write failing structured logging tests**

Create a temporary `StructuredLogger`, write nested fields containing email/phone sentinels, flush, and inspect JSONL plus captured console output:

```python
logger.log(
    "error",
    "provider failed for a@example.com",
    query="call 0901234567",
    nested={"reply": "mail b@example.com"},
)
assert "a@example.com" not in persisted
assert "0901234567" not in persisted
assert "b@example.com" not in persisted
```

Also prove redaction failure produces fixed placeholders rather than original values.

- [ ] **Step 2: Write failing source scanner tests**

Assert the POST/SSE route tails contain no raw request access and that the first occurrence of each sink is after `_privacy_output_boundary_marker`. Check literal forbidden feedback calls now so later tasks cannot accidentally reintroduce them:

```python
FORBIDDEN_FEEDBACK_TOKENS = (
    "memory_manager.feedback(",
    "record_feedback(query=",
    "data.json",
)
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_logging.py agent/tests/test_privacy_source_guards.py agent/tests/test_resilience.py -k "privacy or readiness"
```

Expected: raw nested values persist and source guards fail on current ordering/feedback code.

- [ ] **Step 4: Add recursive final log redaction**

Before `entry.update(extra)` and before console serialization, redact the message and recursively redact string values in mappings/sequences. Preserve safe scalar values and field names. Never log redaction detector exceptions or raw exception text; use `"[REDACTION_FAILED]"`.

The stdlib bridge must call the same redaction path because `record.getMessage()` may contain raw PII.

- [ ] **Step 5: Add bounded privacy metrics**

Define counters with allowlisted labels only:

```python
privacy_redactions_total = Counter(
    "privacy_redactions_total",
    "Privacy redactions by source and type",
    labels=["source", "type"],
)
privacy_boundary_failures_total = Counter(
    "privacy_boundary_failures_total",
    "Privacy boundary failures by stage",
    labels=["stage"],
)
```

Allowlist source/type/stage values before incrementing; unknown values collapse to `"other"`. Add `checks["privacy_boundary"] = True` only through an imported mandatory module health function, not a constant literal.

- [ ] **Step 6: Run logging, metrics, source, and readiness tests**

Run:

```powershell
python -m pytest -q agent/tests/test_privacy_logging.py agent/tests/test_privacy_source_guards.py agent/tests/test_resilience.py agent/tests/test_session_be.py -k "privacy or readiness or metrics or log"
```

Expected: all selected tests pass; the scanner names exact routes/sinks on regression.

- [ ] **Step 7: Commit and review**

```powershell
git add agent/middleware.py agent/metrics.py agent/server.py agent/tests/test_privacy_logging.py agent/tests/test_privacy_source_guards.py agent/tests/test_resilience.py
git commit -m "fix: defend logs and privacy invariants"
```

Review gate: inspect both JSONL and console paths, metric cardinality, and scanner false-positive resistance.

---

### Task 7: PostgreSQL Feedback Receipt Store

**Files:**
- Create: `agent/migrations/071_feedback_receipts.sql`
- Modify: `init.sql`
- Create: `agent/feedback_policy.py`
- Modify: `agent/chat_identity.py`
- Modify: `agent/scheduler.py`
- Create: `agent/tests/test_feedback_policy.py`
- Create: `agent/tests/test_feedback_policy_postgres.py`
- Modify: `agent/tests/test_scheduler.py`
- Modify: `agent/tests/test_migration_chain.py`
- Modify: `agent/tests/test_migration_apply.py`

**Interfaces:**
- Produces: `owner_binding_digest(owner_key: str) -> str` using the existing chat-owner secret with domain separation.
- Produces: `FeedbackReceipt`, `FeedbackConsumeResult`, `FeedbackUnavailable`, and `FeedbackRejected`.
- Produces: `issue_feedback_receipt(owner_key, assistant_turn_digest, model_variant, tool_bucket, *, now=None) -> FeedbackReceipt | None`.
- Produces: `consume_feedback_receipt(token, owner_key, rating, *, now=None) -> FeedbackConsumeResult`.
- Produces: `cleanup_expired_feedback_receipts(*, now=None, limit=500) -> int` and a bounded scheduler invocation.
- Produces lifecycle hooks `purge_feedback_owner(owner_key)` and `verify_feedback_owner_absent(owner_key)` for the second plan.

- [ ] **Step 1: Write failing pure policy tests**

Cover token format, digest determinism/domain separation, owner-kind parsing, bounded model/tool dimensions, and assistant-turn digest without storing text:

```python
def test_receipt_token_is_high_entropy_and_only_digest_is_persisted(fake_store):
    receipt = issue_feedback_receipt(
        "user:00000000-0000-0000-0000-000000000001",
        assistant_turn_digest="a" * 64,
        model_variant="cx-gpt-5-4",
        tool_bucket="search",
        now=NOW,
    )
    assert len(receipt.token) >= 43
    assert receipt.token not in repr(fake_store.rows)
```

- [ ] **Step 2: Write failing real PostgreSQL transaction tests**

Use `TRUST_ERASURE_TEST_DATABASE_URL` with the same disposable-database safety checks as `test_account_control_plane_postgres.py`. Apply migration `071` in a fixture and test:

- authenticated and anonymous issuance;
- 24-hour expiry;
- `SELECT ... FOR UPDATE` concurrent same-rating replay counts once;
- conflicting replay rejects;
- wrong owner rejects;
- consumed rows clear `user_id` and `anonymous_owner_digest` but retain `owner_binding_digest` until expiry;
- cleanup deletes the whole row at expiry;
- scheduled cleanup deletes expired rows in bounded batches and is idempotent;
- rollup keys contain only day, owner kind, model variant, tool bucket, positive count, and negative count;
- schema has no `query`, `reply`, `entity_id`, or `session_id` columns.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_feedback_policy.py agent/tests/test_feedback_policy_postgres.py agent/tests/test_scheduler.py agent/tests/test_migration_chain.py agent/tests/test_migration_apply.py
```

Expected: missing module/migration failures; PostgreSQL tests may skip only when the disposable URL is absent.

- [ ] **Step 4: Add additive receipt and rollup schema**

Migration `071` must create:

```sql
CREATE TABLE feedback_receipts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_digest TEXT NOT NULL UNIQUE,
    owner_kind TEXT NOT NULL CHECK (owner_kind IN ('authenticated', 'anonymous')),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    anonymous_owner_digest TEXT,
    owner_binding_digest TEXT NOT NULL,
    assistant_turn_digest TEXT NOT NULL,
    model_variant TEXT NOT NULL,
    tool_bucket TEXT NOT NULL,
    rating SMALLINT CHECK (rating IN (0, 1)),
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    CHECK (
      (used_at IS NULL AND num_nonnulls(user_id, anonymous_owner_digest) = 1)
      OR
      (used_at IS NOT NULL AND user_id IS NULL AND anonymous_owner_digest IS NULL)
    )
);
```

Add indexes for token digest, expiry, user ID, anonymous digest, and owner binding. Add `feedback_daily_rollups` with one unique key over `(day, owner_kind, model_variant, tool_bucket)`. Update `init.sql` with the final schema and schema version; do not edit historical migrations.

- [ ] **Step 5: Implement transactional issue/consume behavior**

Generate tokens with `secrets.token_urlsafe(32)`, store `sha256(token)` only, use `hmac.compare_digest` for owner bindings, and use UTC injectable `now`. Consumption must:

1. validate shape before hashing;
2. lock the row;
3. reject missing/expired/wrong-owner rows with one internal unavailable class;
4. return idempotent success for same-rating replay;
5. reject conflicting replay;
6. atomically upsert one daily rollup increment;
7. set rating/use time and clear direct owner columns in the same transaction.

On database unavailability, issuance returns `None`; consumption raises `FeedbackUnavailable`. Never include raw database exceptions in public-facing exception text.

Implement `cleanup_expired_feedback_receipts()` as a bounded `DELETE` over selected expired IDs. Register it with the existing scheduler independently from chat availability. Cleanup failures log one stable code and do not change backend readiness.

- [ ] **Step 6: Run unit, PostgreSQL, and migration tests**

Run:

```powershell
python -m pytest -q agent/tests/test_feedback_policy.py agent/tests/test_feedback_policy_postgres.py agent/tests/test_scheduler.py agent/tests/test_migration_chain.py agent/tests/test_migration_apply.py
```

Expected: all non-environment-skipped tests pass, including concurrent receipt use on real PostgreSQL.

- [ ] **Step 7: Commit and review**

```powershell
git add agent/migrations/071_feedback_receipts.sql init.sql agent/feedback_policy.py agent/chat_identity.py agent/scheduler.py agent/tests/test_feedback_policy.py agent/tests/test_feedback_policy_postgres.py agent/tests/test_scheduler.py agent/tests/test_migration_chain.py agent/tests/test_migration_apply.py
git commit -m "feat: add one-time feedback receipts"
```

Review gate: inspect constraints, transaction boundaries, direct-owner clearing, replay authorization, forbidden columns, and error-oracle behavior.

---

### Task 8: Issue Receipts For Every Delivered Assistant Turn

**Files:**
- Modify: `agent/server.py:1434`
- Modify: `agent/tests/test_chat_smoke.py`
- Modify: `agent/tests/test_chat_stream_sse.py`
- Modify: `agent/tests/test_chat_privacy_transport.py`
- Modify: `agent/tests/test_chat_owner_boundary.py`

**Interfaces:**
- Consumes: `issue_feedback_receipt()` from Task 7.
- Adds optional `feedback_receipt: str | None = None` to `ChatResponse`.
- Adds optional `feedback_receipt` to terminal SSE `done` frames.
- Produces `_issue_delivered_feedback_receipt(owner_key, safe_message, safe_reply, model_variant, tools) -> str | None`.

- [ ] **Step 1: Write failing delivery-matrix tests**

For POST normal, exact-cache hit, semantic-cache hit, KB fallback, SSE normal, SSE exact-cache, and SSE semantic-cache responses, stub issuance and assert the returned receipt is attached to the actual delivered turn.

Add a store-outage test:

```python
def test_chat_succeeds_when_receipt_issue_returns_none(client_mocked, monkeypatch):
    monkeypatch.setattr(server, "issue_feedback_receipt", lambda *_a, **_k: None)
    response = client_mocked.post("/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert response.json()["reply"]
    assert response.json().get("feedback_receipt") is None
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_chat_smoke.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_owner_boundary.py
```

Expected: response model and SSE frames lack receipts.

- [ ] **Step 3: Implement safe assistant-turn digest and bounded dimensions**

Compute the digest from already-safe delivered message/reply using canonical UTF-8 separators. Do not store the text. Collapse model names and tool sets through explicit allowlists; unknown models/tools become `"other"` and `"mixed"` rather than new high-cardinality dimensions.

Call issuance only after a reply is finalized for delivery. A blocked input or privacy-boundary failure does not issue a receipt. Receipt failure is best-effort and logs only a stable code.

- [ ] **Step 4: Attach receipts to POST and terminal SSE responses**

Add the optional field to normal/cache/fallback `ChatResponse`. Add it to the final `done` frame for normal/cache/fallback SSE. Preserve all existing keys (`tools`, `suggestions`, `session_id`, `quality`) and omit/null the receipt when issuance fails.

- [ ] **Step 5: Run delivery and compatibility tests**

Run:

```powershell
python -m pytest -q agent/tests/test_chat_smoke.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_history_continuity.py agent/tests/test_chat_usage_accounting.py
```

Expected: all selected tests pass and chat availability is independent of the receipt store.

- [ ] **Step 6: Commit and review**

```powershell
git add agent/server.py agent/tests/test_chat_smoke.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_privacy_transport.py agent/tests/test_chat_owner_boundary.py
git commit -m "feat: issue feedback receipts for chat turns"
```

Review gate: verify one receipt per delivered turn, no receipt for undelivered/error text, no raw text in issuance arguments, and complete cache/fallback coverage.

---

### Task 9: Telemetry-Only Feedback Endpoint And Embedded Caller

**Files:**
- Modify: `agent/server.py:1444`
- Modify: `agent/server.py:3684`
- Modify: `agent/server.py:4307`
- Modify: `agent/middleware.py:255`
- Modify: `agent/metrics.py`
- Create: `agent/tests/test_feedback_transport.py`
- Modify: `tests/test_integration.py`
- Modify: `agent/tests/test_privacy_source_guards.py`

**Interfaces:**
- Consumes: `consume_feedback_receipt()` and `resolve_chat_owner()`.
- Produces strict `FeedbackRequest(receipt: str, rating: Literal[0, 1])` with `extra="forbid"`, invoked manually after pre-validation limits rather than as a FastAPI body parameter.
- Produces independent `feedback_ip_limiter` and `feedback_owner_limiter` singletons and reset/cleanup registration.
- Produces public success `{"success": true}`; receipt failures share one unavailable response, while rate limits return `429` with `Retry-After`.

- [ ] **Step 1: Write failing real-transport contract tests**

Use ASGI transport and assert:

- `receipt + rating` succeeds;
- `user_id`, `session_id`, `query`, or `entity_id` causes 422;
- wrong-owner, fake, expired, and store-unavailable receipts share the same status/body;
- IP budget is consumed before token-shape validation;
- owner budget counts malformed, replayed, and accepted attempts;
- 429 includes `Retry-After`;
- auth and anonymous rollups stay separate;
- same-rating replay is idempotent;
- conflicting replay rejects.

The test must prove extra fields, malformed JSON, and an invalid rating still consume the IP budget and, after owner resolution, the owner budget before returning the bounded 422 response. This requires manual model validation inside the endpoint; FastAPI dependency/body validation must not run before the limiters.

Install spies that fail if memory, `learn_loop`, entity confidence, database knowledge mutation, or `data.json` mutation is called.

- [ ] **Step 2: Write the failing embedded-page contract test**

Update the home-page integration assertion to require:

```python
assert "sendFeedback(data.feedback_receipt" in response.text
assert "JSON.stringify({receipt:receipt,rating:rating})" in response.text
assert "session_id:'web'" not in response.text
assert "query:query" not in response.text
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_feedback_transport.py tests/test_integration.py agent/tests/test_privacy_source_guards.py
```

Expected: old client-controlled fields are accepted and state-changing feedback calls occur.

- [ ] **Step 4: Add dedicated pre-database limiters**

Create 30/hour IP and 20/hour owner limiters in `middleware.py`. Include both in `_reset_limiters()` and `_all_limiters`. Change the endpoint signature to accept `Request`/`Response`, read the already body-size-bounded JSON exactly once, and manually call `FeedbackRequest.model_validate()` only after the pre-validation limits. In the endpoint:

1. consume the IP limiter using `get_client_ip(request)`;
2. resolve the signed/authenticated owner and prepare a rotated anonymous cookie for every response produced after owner resolution;
3. consume the owner limiter;
4. parse JSON and validate the strict request model, mapping JSON/Pydantic failures to the bounded 422 contract;
5. validate receipt token shape;
6. call transactional consumption.

All attempts that reach the endpoint consume the IP budget. Attempts after owner resolution consume both budgets even when the receipt is malformed or invalid.

Use one response helper for success, unavailable, 422, and 429 paths after owner resolution so the anonymous owner cookie is attached to the actual returned response object rather than a discarded FastAPI placeholder response.

- [ ] **Step 5: Replace the endpoint with aggregate-only consumption**

Delete all reads of client identity/query/entity fields and all calls to `memory_manager.feedback`, `learn_loop.record_feedback`, shared confidence updates, and raw feedback logging. Track only bounded rejection reason, owner kind, and rating metrics.

Use one public unavailable response for fake/expired/wrong-owner/store-unavailable receipts. Do not expose whether a token exists. Return explicit 429 separately.

- [ ] **Step 6: Update the embedded chat caller**

Pass the `done.feedback_receipt` into `showFeedback`. Render no buttons when absent. Submit only:

```javascript
JSON.stringify({receipt:receipt,rating:rating})
```

Disable both buttons while the request is pending, preserve one visible selected state on 2xx, and restore controls with a generic message on unavailable/429. Do not persist the receipt in localStorage, history, or logs.

- [ ] **Step 7: Run feedback, privacy, and integration tests**

Run:

```powershell
python -m pytest -q agent/tests/test_feedback_transport.py agent/tests/test_feedback_policy.py agent/tests/test_feedback_policy_postgres.py agent/tests/test_privacy_source_guards.py tests/test_integration.py agent/tests/test_chat_stream_sse.py
```

Expected: all non-environment-skipped tests pass; no state-changing feedback call remains.

- [ ] **Step 8: Commit and review**

```powershell
git add agent/server.py agent/middleware.py agent/metrics.py agent/tests/test_feedback_transport.py tests/test_integration.py agent/tests/test_privacy_source_guards.py
git commit -m "fix: make public feedback telemetry only"
```

Review gate: inspect request model, limiter order, common errors, owner binding, UI payload, forbidden call scanner, and aggregate schema together.

---

### Task 10: Runtime Trust Boundary Final Gate

**Files:**
- Create: `docs/superpowers/results/2026-07-29-runtime-trust-boundary.md`
- Modify: `docs/superpowers/plans/2026-07-29-runtime-trust-boundary.md`
- Modify: `docs/superpowers/specs/2026-07-29-trust-erasure-closure-design.md`

**Interfaces:**
- Produces: evidence mapping every Runtime Trust Boundary acceptance criterion to commands and commits.
- Marks this plan `done` only after all required commands pass or a pre-existing timeout/debt is recorded with exact evidence.
- Does not authorize the Verified Erasure Lifecycle implementation automatically.

- [ ] **Step 1: Run the focused backend gate**

```powershell
python -m pytest -q agent/tests/test_privacy_policy.py agent/tests/test_privacy_boundary.py agent/tests/test_chat_privacy_transport.py agent/tests/test_privacy_sink_boundary.py agent/tests/test_privacy_logging.py agent/tests/test_privacy_source_guards.py agent/tests/test_feedback_policy.py agent/tests/test_feedback_policy_postgres.py agent/tests/test_feedback_transport.py agent/tests/test_chat_smoke.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_history_continuity.py agent/tests/test_chat_usage_accounting.py tests/test_guardrails.py tests/test_config.py tests/test_integration.py
```

Expected: all tests pass except the documented disposable-PostgreSQL skip when its URL is absent. A final completion claim requires rerunning PostgreSQL tests with `TRUST_ERASURE_TEST_DATABASE_URL` configured.

- [ ] **Step 2: Run frontend contract and build gates**

```powershell
cd web-nuxt
npx vitest run tests/legal-privacy-retention.test.ts tests/sse-stream.test.ts tests/chat-transport-security.test.ts
npx vue-tsc --noEmit
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 3: Run repository gates**

```powershell
cd ..
git diff --check
python scripts/checks/run_hard.py --staged
python -m pytest -q
```

Expected: diff/hard checks pass. The full baseline must be allowed to finish; if the known closed-release rehearsal exceeds the configured limit, record elapsed time, last observed case, and focused-suite success without calling it a pass.

- [ ] **Step 4: Write the result evidence**

Create the result document with status, commit list, exact commands, pass/skip/timeout counts, PostgreSQL target safety statement, and a requirement-by-requirement table for:

- provider input/history privacy;
- tool/output/cache/sink privacy;
- real-transport SSE confidentiality;
- log redaction/readiness;
- receipt issuance availability behavior;
- replay/rate-limit/aggregate-only feedback;
- absence of personalization/knowledge mutations.

- [ ] **Step 5: Mark documentation status and commit**

Change this plan status to `done`. Update the shared spec status to say Runtime Trust Boundary is complete and Verified Erasure Lifecycle remains pending; do not mark the overall spec done.

```powershell
git add docs/superpowers/results/2026-07-29-runtime-trust-boundary.md docs/superpowers/plans/2026-07-29-runtime-trust-boundary.md docs/superpowers/specs/2026-07-29-trust-erasure-closure-design.md
git commit -m "docs: record runtime trust boundary evidence"
```

Final review gate: independent reviewer compares the result evidence to the approved design before the controller starts the Verified Erasure Lifecycle plan.
