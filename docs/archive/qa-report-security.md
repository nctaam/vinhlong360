> **STATUS (2026-07-07): ARCHIVED — Snapshot QA 2026-06-28 nằm sai chỗ (repo root) — archive 2026-07-07. Một phần "release blocker" đã fix từ lâu (vd /metrics đã gate sau X-Admin-Key). KHÔNG dùng làm danh sách việc hiện hành.**

# QA Security Report - vinhlong360

Audit date: 2026-06-28

Scope: FastAPI backend, Nuxt frontend security surfaces, auth/CSRF/IDOR, upload, input validation, error handling, and business-rule drift. This report is evidence-based: I did not mark protected paths as exploitable when the code has a guard.

## Summary

| Severity | Count | Notes |
|---|---:|---|
| P0 Critical | 0 | No confirmed unauthenticated RCE, SQLi, payment flow, or public PII response found. |
| P1 High | 5 | Internal/system endpoints and comment-thread integrity need release-blocker fixes. |
| P2 Medium | 18 | Validation, privacy retention, rate limits, CSP, test-policy gaps. |
| P3 Low | 3 | Maintainability and regression-test hardening. |

## Findings

### [P1] Finding-001: Internal system endpoints rely on production-only middleware instead of per-route auth

**Chiều:** Security / Deployment / API Contract  
**File:** `agent/server.py:1014`, `agent/server.py:2688`, `agent/server.py:3194`  
**OWASP:** A01:2021 Broken Access Control  
**CWE:** CWE-306

**Mô tả:** `/system/*`, `/analytics/*`, and `/metrics` are guarded only when `_IS_PROD` is true. In any staging/dev deployment accidentally reachable from a hostile network, endpoints such as `/system/logs`, `/system/errors`, `/system/costs`, and `/system/guardrails` expose operational state without a route-level dependency.

**Exploit scenario:**
1. Attacker sends `curl http://host:8360/system/logs`.
2. If `ENVIRONMENT` is not exactly production, middleware passes the request.
3. Logs, traces, scheduler, cost, or guardrail internals become queryable.

**Root cause:** Internal-route authorization is centralized in a production-only middleware gate instead of attached to every sensitive route.

**Fix:**
```python
from fastapi import Depends, Request, HTTPException

async def require_internal_admin(request: Request):
    from middleware import verify_admin_key
    if not verify_admin_key(request):
        raise HTTPException(status_code=403, detail="forbidden")

@app.get("/system/logs", dependencies=[Depends(require_internal_admin)])
async def system_logs(limit: int = Query(50, ge=1, le=500), level: str = None):
    return {"logs": logger.recent(limit, level)}
```

**Test:**
```python
def test_system_logs_requires_admin(client):
    r = client.get("/system/logs")
    assert r.status_code in (401, 403, 404)
```

**Effort:** M

### [P1] Finding-002: Checkpoint and confirmation endpoints are unauthenticated and outside the internal gate

**Chiều:** Security / Business Logic / Data Integrity  
**File:** `agent/server.py:2813`, `agent/server.py:2821`, `agent/server.py:2859`, `agent/server.py:2870`  
**OWASP:** A01:2021 Broken Access Control  
**CWE:** CWE-639

**Mô tả:** `/checkpoints/{session_id}`, `/checkpoints`, `/confirm/{confirmation_id}`, and `/reject/{confirmation_id}` expose or mutate checkpoint state by caller-supplied IDs. These paths do not begin with `/system`, so the production-only system middleware does not protect them.

**Exploit scenario:**
1. Attacker guesses or obtains a `session_id` or `confirmation_id`.
2. Attacker calls `POST /confirm/{confirmation_id}`.
3. A pending human-in-the-loop action can be confirmed or rejected by the wrong party.

**Root cause:** The checkpoint API has no ownership token, signed session binding, or admin dependency.

**Fix:**
```python
def _checkpoint_token_ok(request: Request, session_id: str) -> bool:
    expected = hmac.new(os.environ["CHECKPOINT_SECRET"].encode(), session_id.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(request.headers.get("X-Checkpoint-Token", ""), expected)

@app.get("/checkpoints/{session_id}")
async def list_checkpoints(session_id: str, request: Request):
    if not _checkpoint_token_ok(request, session_id):
        raise HTTPException(403, "forbidden")
    return {"checkpoints": checkpoint_manager.list_checkpoints(session_id)}
```

**Test:**
```python
def test_checkpoint_list_requires_signed_token(client):
    assert client.get("/checkpoints/s1").status_code in (401, 403)
```

**Effort:** M

### [P1] Finding-003: Public health endpoint leaks internal architecture and runtime state

**Chiều:** Security / Error Handling / Deployment  
**File:** `agent/server.py:2472`, `agent/server.py:2511`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-200

**Mô tả:** `GET /health` returns version, uptime, memory, database backend, model name, cache stats, response times, rate limits, error stats, scheduler state, search index state, vector stats, and feature flags. That is useful for monitoring but excessive for a public endpoint.

**Exploit scenario:**
1. Attacker sends `curl https://site/health`.
2. Response reveals enabled modules and degraded subsystems.
3. Attacker prioritizes attacks against exposed features and timing bottlenecks.

**Root cause:** One endpoint serves both public liveness and internal diagnostics.

**Fix:**
```python
@app.get("/health")
async def health_public():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/health/internal", dependencies=[Depends(require_internal_admin)])
async def health_internal():
    return await _full_health_payload()
```

**Test:**
```python
def test_public_health_is_minimal(client):
    data = client.get("/health").json()
    assert "model" not in data
    assert "scheduler" not in data
```

**Effort:** S

### [P1] Finding-004: Cross-post replies can be created because parent comment membership is not validated

**Chiều:** Business Logic / Data Integrity / Edge Cases  
**File:** `agent/social.py:1115`, `agent/social.py:1144`, `init.sql:171`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-840

**Mô tả:** `create_comment` inserts `parent_id` directly and only later reads the parent author. The schema constrains `parent_id` to an existing comment, but it does not guarantee that the parent comment belongs to the same `post_id`.

**Exploit scenario:**
1. User creates a reply under `post_b` with `parent_id` from a comment under `post_a`.
2. The row is accepted because `parent_id` exists.
3. Thread reconstruction can hide the reply, attach it to the wrong logical thread, or trigger wrong notifications.

**Root cause:** Parent ownership is enforced at the row existence level, not at the post-thread level.

**Fix:**
```python
if body.parent_id:
    parent = db._fetchone(conn, f"""
        SELECT user_id FROM comments
        WHERE id::text = {ph} AND post_id::text = {ph}
    """, (body.parent_id, post_id))
    if not parent:
        raise HTTPException(400, "Bình luận cha không thuộc bài viết này")
```

**Test:**
```python
def test_reply_parent_must_belong_to_same_post(client, auth_headers, post_a, post_b, comment_a):
    r = client.post(f"/api/posts/{post_b}/comments", json={"content": "reply ok", "parent_id": comment_a}, headers=auth_headers)
    assert r.status_code == 400
```

**Effort:** S

### [P1] Finding-005: LLM judge endpoint can be invoked without per-route admin authorization

**Chiều:** Security / Business Logic / Background Tasks  
**File:** `agent/server.py:3293`  
**OWASP:** A01:2021 Broken Access Control  
**CWE:** CWE-306

**Mô tả:** `POST /system/judge/evaluate` calls the judge function with caller-provided query/reply. It inherits only the production-only `/system` middleware gate and has no local admin check.

**Exploit scenario:**
1. Attacker calls `curl -X POST /system/judge/evaluate -d '{"query":"x","reply":"y"}'`.
2. In non-production or misconfigured production, the endpoint performs judge work.
3. LLM budget and internal evaluation behavior are exposed.

**Root cause:** Cost-bearing system endpoints do not consistently call `verify_admin_key`.

**Fix:**
```python
@app.post("/system/judge/evaluate", dependencies=[Depends(require_internal_admin)])
async def judge_evaluate(req: JudgeEvaluateRequest):
    if not HAS_LLM_JUDGE:
        raise HTTPException(503, detail="LLM Judge not available")
    return judge(req.query, req.reply)
```

**Test:**
```python
def test_judge_evaluate_requires_admin(client):
    r = client.post("/system/judge/evaluate", json={"query": "a", "reply": "b"})
    assert r.status_code in (401, 403, 404)
```

**Effort:** S

### [P2] Finding-006: Semantic-cache invalidation is reachable without per-route admin authorization

**Chiều:** Security / Performance  
**File:** `agent/server.py:3268`  
**OWASP:** A01:2021 Broken Access Control  
**CWE:** CWE-306

**Mô tả:** `POST /system/semantic-cache/invalidate` can invalidate cache entries by entity or query. Cache invalidation is operational control and should not depend only on production environment gating.

**Exploit scenario:**
1. Attacker repeatedly posts invalidation payloads.
2. Cache hit rate drops.
3. Backend and LLM/search costs increase.

**Root cause:** Cache mutation endpoint lacks route-level authorization.

**Fix:**
```python
@app.post("/system/semantic-cache/invalidate", dependencies=[Depends(require_internal_admin)])
async def semantic_cache_invalidate(req: SemanticCacheInvalidateRequest):
    ...
```

**Test:**
```python
def test_semantic_cache_invalidate_requires_admin(client):
    assert client.post("/system/semantic-cache/invalidate", json={"query": "x"}).status_code in (401, 403, 404)
```

**Effort:** S

### [P2] Finding-007: Vector search diagnostics are public

**Chiều:** Security / API Contract  
**File:** `agent/server.py:3026`, `agent/server.py:3032`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-200

**Mô tả:** `/vectors/stats` and `/vectors/search` expose embedding index availability and retrieval behavior. Search can remain public if intended, but stats and raw scoring should be separated from public discovery.

**Exploit scenario:**
1. Attacker calls `/vectors/stats`.
2. Attacker learns corpus/index size and whether vector features are enabled.
3. Attacker probes `/vectors/search` to reverse-engineer retrieval behavior.

**Root cause:** Diagnostics and user-facing search share the same unauthenticated route style.

**Fix:**
```python
@app.get("/vectors/stats", dependencies=[Depends(require_internal_admin)])
async def vector_stats():
    return {"available": True, **embedding_store.stats()}
```

**Test:**
```python
def test_vector_stats_requires_admin(client):
    assert client.get("/vectors/stats").status_code in (401, 403, 404)
```

**Effort:** S

### [P2] Finding-008: `/auth/check-phone` discloses whether an account has password login

**Chiều:** Security / Privacy / Authentication  
**File:** `agent/auth.py:446`, `agent/auth.py:459`  
**OWASP:** A07:2021 Identification and Authentication Failures  
**CWE:** CWE-203

**Mô tả:** The endpoint returns `{"has_password": true|false}` for a supplied phone number. Rate limiting reduces abuse, but the response still allows enumeration of registered/password-enabled accounts.

**Exploit scenario:**
1. Attacker submits a list of phone numbers.
2. Endpoint reveals which numbers have password login enabled.
3. Attacker prioritizes credential-stuffing or social-engineering targets.

**Root cause:** UX routing for login mode is coupled to an account-state oracle.

**Fix:**
```python
@router.post("/check-phone")
async def check_phone(body: CheckPhone, request: Request):
    check_rate(...)
    return {"next": "otp_or_password"}  # do not reveal account state
```

**Test:**
```python
def test_check_phone_does_not_reveal_has_password(client):
    data = client.post("/auth/check-phone", json={"phone": "0901234567"}).json()
    assert "has_password" not in data
```

**Effort:** M

### [P2] Finding-009: Rate limiting is in-memory and per-process

**Chiều:** Security / Performance / Deployment  
**File:** `agent/ratelimit.py:1`, `agent/ratelimit.py:16`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-770

**Mô tả:** The sliding-window buckets live in process memory. A restart resets limits, multiple workers do not share counters, and attackers can distribute requests across IPs.

**Exploit scenario:**
1. Attacker bursts reports/search/upload attempts.
2. Process restart or multiple workers reset/split counters.
3. Abuse continues below each process-local threshold.

**Root cause:** Redis is available in compose but rate limiting does not use a shared backend by default.

**Fix:**
```python
def check_rate(key: str, limit: int, window: int, msg: str = DEFAULT_MSG) -> None:
    if redis_client:
        count = redis_client.incr(f"rl:{key}:{int(time.time() // window)}")
        redis_client.expire(f"rl:{key}:{int(time.time() // window)}", window * 2)
        if count > limit:
            raise HTTPException(429, msg)
        return
    _check_rate_memory(key, limit, window, msg)
```

**Test:**
```python
def test_rate_limit_uses_redis_when_configured(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    assert rate_backend_name() == "redis"
```

**Effort:** M

### [P2] Finding-010: CSRF dependency is fail-open for unauthenticated requests, so public writes rely only on rate limits

**Chiều:** Security / Input Validation  
**File:** `agent/auth_middleware.py:124`, `agent/auth_middleware.py:127`, `agent/public_api.py:844`, `agent/public_api.py:1051`  
**OWASP:** A01:2021 Broken Access Control  
**CWE:** CWE-352

**Mô tả:** `require_csrf` returns when no user/session exists. That is safe for routes that also require `require_user`, but anonymous mutation endpoints such as `/api/report` and contact-view tracking have no CSRF or anonymous idempotency token.

**Exploit scenario:**
1. Malicious page auto-submits anonymous reports from a visitor browser.
2. Backend accepts the write if rate limit allows it.
3. Admin queues and analytics are polluted.

**Root cause:** There is no separate anti-automation token for anonymous writes.

**Fix:**
```python
async def require_public_write_token(request: Request):
    token = request.headers.get("X-Public-Write-Token")
    if not token or not verify_public_write_token(token):
        raise HTTPException(403, "public write token required")
```

**Test:**
```python
def test_anonymous_report_requires_public_write_token(client):
    r = client.post("/api/report", json={"target_id": "x", "reason": "wrong"})
    assert r.status_code in (403, 422)
```

**Effort:** M

### [P2] Finding-011: Anonymous report JSONL stores raw IP and optional contact without retention or hashing

**Chiều:** Security / Privacy / Error Handling  
**File:** `agent/public_api.py:844`, `agent/public_api.py:859`  
**OWASP:** A02:2021 Cryptographic Failures  
**CWE:** CWE-359

**Mô tả:** `/api/report` writes `contact` and raw `ip` into `reports.jsonl`. The endpoint rotates the file but does not hash IPs, redact contact, or define retention.

**Exploit scenario:**
1. User submits report with phone/email in `contact`.
2. Raw IP/contact are stored on disk.
3. Any server/log compromise exposes unnecessary personal data.

**Root cause:** Reporting stores operational anti-abuse data as plain text application records.

**Fix:**
```python
record = {
    "contact": mask_contact(payload.contact.strip()),
    "ip_hash": hmac_ip(ip),
    "retention_until": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(),
}
```

**Test:**
```python
def test_report_does_not_store_raw_ip(tmp_path, monkeypatch, client):
    client.post("/api/report", json={"target_id": "e1", "reason": "wrong", "contact": "0901234567"})
    assert "0901234567" not in REPORTS_FILE.read_text(encoding="utf-8")
```

**Effort:** M

### [P2] Finding-012: Contact-view analytics stores raw IP

**Chiều:** Security / Privacy / Analytics  
**File:** `agent/public_api.py:1051`, `agent/public_api.py:1063`  
**OWASP:** A02:2021 Cryptographic Failures  
**CWE:** CWE-359

**Mô tả:** `POST /api/entities/{id}/view-contact` writes `entity_id`, action, and raw IP to JSONL. This is analytics, not authentication, so raw IP is unnecessary.

**Exploit scenario:**
1. Visitor clicks Zalo/phone CTA.
2. IP is persisted in `contact_views.jsonl`.
3. A breach links interest in locations/products to IP addresses.

**Root cause:** Analytics event design stores direct identifiers.

**Fix:**
```python
record = {"ts": now_iso(), "entity_id": entity_id, "action": action, "ip_hash": hmac_ip(ip)}
```

**Test:**
```python
def test_contact_view_hashes_ip(client):
    client.post("/api/entities/e1/view-contact?action=phone")
    assert '"ip":' not in CONTACT_VIEWS_FILE.read_text(encoding="utf-8")
```

**Effort:** S

### [P2] Finding-013: Nginx CSP allows inline scripts and broad outbound connections

**Chiều:** Security / Deployment  
**File:** `nginx-ssl.conf:63`, `nginx.conf:31`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-693

**Mô tả:** The reverse proxy sets `script-src 'self' 'unsafe-inline'` and `connect-src 'self' http: https: ws: wss:`. The app middleware CSP is stricter for scripts, but the proxy header can override/duplicate policy depending response path.

**Exploit scenario:**
1. A template or third-party script injection occurs.
2. Inline script execution is allowed by proxy CSP.
3. Browser-side impact is higher than necessary.

**Root cause:** Nginx and FastAPI CSP policies diverge.

**Fix:**
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'nonce-$request_id'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; connect-src 'self' https://vinhlong360.vn wss://vinhlong360.vn; img-src 'self' data: blob: https:;" always;
```

**Test:**
```python
def test_csp_has_no_script_unsafe_inline(client):
    csp = client.get("/").headers["content-security-policy"]
    assert "'unsafe-inline'" not in csp.split("script-src", 1)[1].split(";", 1)[0]
```

**Effort:** M

### [P2] Finding-014: Public entity listing accepts `limit=0` or negative limits

**Chiều:** Input Validation / API Contract  
**File:** `agent/public_api.py:161`, `agent/public_api.py:169`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-20

**Mô tả:** `/api/entities` has `limit: Query(50, le=1000)` but no `ge=1`. Negative or zero limits should be rejected consistently at API boundary.

**Exploit scenario:**
1. Attacker calls `/api/entities?limit=-1`.
2. Backend passes an invalid semantic value into database pagination.
3. Behavior differs by database and can bypass expected pagination semantics.

**Root cause:** Upper bound exists without lower bound.

**Fix:**
```python
limit: int = Query(50, ge=1, le=100)
```

**Test:**
```python
def test_entities_limit_must_be_positive(client):
    assert client.get("/api/entities?limit=-1").status_code == 422
```

**Effort:** S

### [P2] Finding-015: Public search accepts invalid limit lower bounds

**Chiều:** Input Validation / API Contract  
**File:** `agent/public_api.py:357`, `agent/public_api.py:363`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-20

**Mô tả:** `/api/search` uses `limit: Query(20, le=100)` with no `ge=1`. Search endpoints should reject `limit=0` and negative limits before hitting query code.

**Exploit scenario:**
1. Attacker calls `/api/search?q=abc&limit=-100`.
2. Backend receives an invalid limit.
3. Pagination and cache behavior become inconsistent.

**Root cause:** Missing lower-bound validation.

**Fix:**
```python
limit: int = Query(20, ge=1, le=100)
```

**Test:**
```python
def test_search_limit_must_be_positive(client):
    assert client.get("/api/search?q=test&limit=0").status_code == 422
```

**Effort:** S

### [P2] Finding-016: Public event listing accepts invalid limit lower bounds

**Chiều:** Input Validation / Performance  
**File:** `agent/public_api.py:776`, `agent/public_api.py:781`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-20

**Mô tả:** `/api/events` uses `limit: Query(50, le=200)` with no `ge=1`. It also loads all events before slicing, making limit validation even more important.

**Exploit scenario:**
1. Attacker calls `/api/events?limit=-1`.
2. API accepts invalid pagination.
3. Caller can trigger edge-case behavior in sorting/slicing.

**Root cause:** Lower-bound validation is missing.

**Fix:**
```python
limit: int = Query(50, ge=1, le=100)
```

**Test:**
```python
def test_events_limit_must_be_positive(client):
    assert client.get("/api/events?limit=0").status_code == 422
```

**Effort:** S

### [P2] Finding-017: Manual `v-html` sanitizers lack a central audited policy and browser regression tests

**Chiều:** Security / Accessibility / Code Quality  
**File:** `web-nuxt/components/PostCard.vue:156`, `web-nuxt/pages/bai-viet/[id].vue:176`, `web-nuxt/components/ChatWidget.vue:112`, `web-nuxt/utils/safe.ts:12`  
**OWASP:** A03:2021 Injection  
**CWE:** CWE-79

**Mô tả:** The sampled `v-html` flows escape content before linkification, so I did not confirm stored XSS. The risk is that each component owns its own sanitizer/linkifier and there is no DOMPurify-style policy or DOM regression suite for the full list of `v-html` call sites.

**Exploit scenario:**
1. Future component adds `v-html` with partial escaping.
2. Payload such as `<img src=x onerror=alert(1)>` is missed.
3. Browser executes attacker-controlled markup.

**Root cause:** Sanitization is convention-based instead of enforced through one helper and tests.

**Fix:**
```ts
import DOMPurify from 'dompurify'
export function safeHtml(input: string) {
  return DOMPurify.sanitize(input, { ALLOWED_TAGS: ['a', 'strong', 'br', 'mark'], ALLOWED_ATTR: ['href', 'class'] })
}
```

**Test:**
```ts
test('post html escapes xss payloads', () => {
  expect(renderPost('<img src=x onerror=alert(1)>')).not.toContain('onerror')
})
```

**Effort:** M

### [P2] Finding-018: SMS delivery has timeout but no retry/backoff queue

**Chiều:** Error Handling / Resilience / Authentication  
**File:** `agent/auth.py:265`, `agent/auth.py:273`, `agent/auth.py:287`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-703

**Mô tả:** `_send_sms` uses a 10-second timeout and returns `False` on any exception. There is no retry with jitter, provider circuit breaker, or queue for transient eSMS failures.

**Exploit scenario:**
1. eSMS has a short outage.
2. OTP creation succeeds but delivery fails.
3. Users are locked out until provider recovers.

**Root cause:** External dependency failure is handled as a one-shot best effort.

**Fix:**
```python
for attempt in range(3):
    try:
        resp = await client.post(url, json=payload, timeout=10)
        if resp.json().get("CodeResult") == "100":
            return True
    except httpx.HTTPError:
        await asyncio.sleep(0.5 * (2 ** attempt))
return False
```

**Test:**
```python
async def test_sms_retries_transient_timeout(monkeypatch):
    calls = 0
    # monkeypatch client.post to fail once then succeed
    assert await _send_sms("0901234567", "code") is True
```

**Effort:** M

### [P2] Finding-019: Admin role change lacks self-demotion and step-up confirmation controls

**Chiều:** Business Logic / Authorization  
**File:** `agent/admin.py:1878`, `agent/admin.py:1889`  
**OWASP:** A01:2021 Broken Access Control  
**CWE:** CWE-269

**Mô tả:** `POST /admin/users/{id}/role` validates role enum and target existence, but it does not prevent accidental self-demotion or require step-up confirmation for granting admin.

**Exploit scenario:**
1. Admin session is compromised or mis-clicked.
2. Attacker grants admin to another account or demotes the only admin.
3. Recovery requires direct DB access.

**Root cause:** Sensitive role transitions use the same admin session guard as normal admin actions.

**Fix:**
```python
admin_user = await get_current_user(request)
if str(admin_user["id"]) == user_id:
    raise HTTPException(400, "Không thể đổi quyền của chính mình")
if role == "admin" and request.headers.get("X-Step-Up-Token") != expected_step_up(admin_user):
    raise HTTPException(403, "step-up required")
```

**Test:**
```python
def test_admin_cannot_change_own_role(client, admin_headers, admin_id):
    r = client.post(f"/admin/users/{admin_id}/role?role=user", headers=admin_headers)
    assert r.status_code == 400
```

**Effort:** M

### [P2] Finding-020: Reputation can be inflated by coordinated accounts

**Chiều:** Business Logic / Abuse Prevention  
**File:** `agent/social.py:1299`, `agent/social.py:1454`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-841

**Mô tả:** Self-like is blocked, and reputation is computed from approved contributions. There is no Sybil/cohort detection for rings of new accounts liking/following one another.

**Exploit scenario:**
1. Attacker creates many accounts.
2. Accounts follow/like/review each other within allowed rate limits.
3. Leaderboards and badges become gameable.

**Root cause:** Reputation scoring lacks trust weighting, account-age thresholds, and anomaly detection.

**Fix:**
```python
trusted_like_points = min(likes_from_accounts_older_than(conn, user_id, days=7), LIKE_CAP)
points = _calc_points(reviews, posts, photos, trusted_followers, places, trusted_like_points)
```

**Test:**
```python
def test_reputation_ignores_new_account_like_ring(pg_user_ring):
    assert reputation_for(pg_user_ring.target)["points"] < 80
```

**Effort:** L

### [P2] Finding-021: Business-rule lint does not block transactional wording in content data

**Chiều:** Business Logic / Legal / Content Quality  
**File:** `agent/database.py:382`, `web-nuxt/pages/dia-diem/[id].vue:368`, `web-nuxt/utils/legalContent.ts:106`  
**OWASP:** N/A  
**CWE:** CWE-840

**Mô tả:** I did not find on-site booking/payment/cart logic in runtime code. However, content fields such as `booking_note` can contain external tour/booking wording, so the "chỉ giới thiệu" rule depends on editorial discipline rather than automated lint.

**Exploit scenario:**
1. Data import adds "đặt tour ngay" or payment-like CTA text.
2. UI renders it as guide content.
3. The site drifts toward transactional claims without a code change.

**Root cause:** Business invariant is documented but not enforced in content ingestion.

**Fix:**
```python
FORBIDDEN_CTA = re.compile(r"\b(đặt ngay|mua ngay|thanh toán|giỏ hàng|checkout)\b", re.I)
if FORBIDDEN_CTA.search(text):
    raise ValueError("Transactional CTA is not allowed")
```

**Test:**
```python
def test_intro_only_lint_rejects_transactional_cta():
    with pytest.raises(ValueError):
        validate_intro_only_text("Mua ngay và thanh toán online")
```

**Effort:** M

### [P2] Finding-022: Error response formats are inconsistent

**Chiều:** Error Handling / API Contract  
**File:** `agent/public_api.py:353`, `agent/public_api.py:853`, `agent/social.py:431`, `agent/server.py:2843`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-391

**Mô tả:** The API returns FastAPI `{"detail": ...}`, custom `{"error": ...}`, `{"message": ...}`, and success envelopes with different shapes. This makes clients branch on endpoint-specific errors and increases missed error handling.

**Exploit scenario:**
1. Client expects `detail`.
2. Endpoint returns `error`.
3. UI treats a failed write as unknown or successful and loses user recovery guidance.

**Root cause:** No shared error envelope helper.

**Fix:**
```python
def api_error(code: str, message: str, status: int):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})
```

**Test:**
```python
def test_error_envelope_is_consistent(client):
    data = client.get("/api/entities/not-found").json()
    assert set(data["error"]) >= {"code", "message"}
```

**Effort:** M

### [P2] Finding-023: `CSRF_SECRET` auto-generation invalidates CSRF tokens on restart

**Chiều:** Security / Deployment / Resilience  
**File:** `agent/auth_middleware.py:86`, `agent/auth_middleware.py:88`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-320

**Mô tả:** If `CSRF_SECRET` is unset, the app generates a random secret at process start. That is safe from a default-secret standpoint, but it invalidates tokens on restart and allows production to boot with ephemeral CSRF state.

**Exploit scenario:**
1. Production restarts with missing `CSRF_SECRET`.
2. Existing sessions keep cookies but CSRF validation changes.
3. Users see unexplained 403s and retry unsafe flows.

**Root cause:** Missing secret is not fail-closed in production.

**Fix:**
```python
if not _CSRF_SECRET and os.getenv("ENVIRONMENT") == "production":
    raise RuntimeError("CSRF_SECRET is required in production")
```

**Test:**
```python
def test_prod_requires_csrf_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("CSRF_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        reload(auth_middleware)
```

**Effort:** S

### [P3] Finding-024: Dynamic ORDER BY is safe today but needs a focused SQLi regression test

**Chiều:** Security / Code Quality  
**File:** `agent/database.py:608`, `agent/database.py:620`  
**OWASP:** A03:2021 Injection  
**CWE:** CWE-89

**Mô tả:** `ORDER BY {order}` is built from a local whitelist, so I did not find a direct injection path. Because ORDER BY cannot be parameterized normally, this needs a dedicated regression test to prevent future caller-controlled values from entering `order`.

**Exploit scenario:**
1. Future change passes raw `sort` into `order`.
2. Attacker sends `sort=name;DROP TABLE entities`.
3. SQL text changes before parameter binding.

**Root cause:** Safety depends on local branching rather than a reusable order mapping helper.

**Fix:**
```python
ORDER_SQL = {"name": "e.name ASC", "rating": "(e.attributes->>'rating')::float DESC NULLS LAST", "newest": updated_col + " DESC"}
order = ORDER_SQL.get(sort or "newest", ORDER_SQL["newest"])
```

**Test:**
```python
def test_sort_payload_does_not_reach_order_by(db):
    rows = db.list_entities(sort="name; DROP TABLE entities; --")
    assert isinstance(rows, list)
```

**Effort:** S

### [P3] Finding-025: Security headers are split between app, Nuxt, and Nginx

**Chiều:** Security / Deployment / Code Quality  
**File:** `agent/auth_middleware.py:387`, `web-nuxt/nuxt.config.ts:206`, `nginx-ssl.conf:58`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-16

**Mô tả:** Security headers are configured in three places with different values (`DENY` vs `SAMEORIGIN`, app CSP vs proxy CSP). Drift makes audits and incident fixes slower.

**Exploit scenario:**
1. Developer tightens CSP in FastAPI only.
2. Nginx continues sending weaker CSP.
3. Browser enforces the wrong policy for proxied routes.

**Root cause:** No single source of truth for response headers.

**Fix:**
```python
# Generate nginx header snippet from the same SECURITY_HEADERS map in CI/deploy.
assert build_csp("").startswith("default-src 'self'")
```

**Test:**
```python
def test_nginx_and_app_csp_match_policy():
    assert "'unsafe-inline'" not in read_nginx_csp_script_src()
```

**Effort:** M

### [P3] Finding-026: Some broad exception handlers still hide failure detail from tests

**Chiều:** Error Handling / Code Quality  
**File:** `agent/server.py:2484`, `agent/public_api.py:1020`, `agent/admin.py:1819`  
**OWASP:** A09:2021 Security Logging and Monitoring Failures  
**CWE:** CWE-703

**Mô tả:** Several paths catch broad exceptions and return fallback data. Some are intentionally graceful, but tests should assert that critical failures are logged and observable rather than silently swallowed.

**Exploit scenario:**
1. Database or JSON parsing fails.
2. Endpoint returns empty/healthy-looking fallback.
3. Monitoring misses the degraded behavior.

**Root cause:** Graceful fallback and observability are not consistently paired.

**Fix:**
```python
except Exception as exc:
    logger.exception("review-stats query failed for %s", entity_id)
    metrics.increment("review_stats.failure")
    return _empty
```

**Test:**
```python
def test_review_stats_logs_query_failure(caplog, client, monkeypatch):
    monkeypatch.setattr(db, "_fetchall", side_effect=RuntimeError("boom"))
    client.get("/api/entities/e1/review-stats")
    assert "review-stats query failed" in caplog.text
```

**Effort:** S
