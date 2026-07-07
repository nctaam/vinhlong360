> **STATUS (2026-07-07): ARCHIVED — Snapshot QA 2026-06-28 nằm sai chỗ (repo root) — archive 2026-07-07. Một phần "release blocker" đã fix từ lâu (vd /metrics đã gate sau X-Admin-Key). KHÔNG dùng làm danh sách việc hiện hành.**

# QA Test Suite Plan - vinhlong360

Audit date: 2026-06-28

This file defines the regression suite to add after the audit. It is organized as runnable pytest/Vitest-style files. The functions below are intentionally focused on the findings, not broad happy-path coverage that already exists.

## `tests/test_qa_security_regression.py`

```python
import pytest

SYSTEM_ENDPOINTS = [
    "/metrics",
    "/analytics/summary",
    "/analytics/popular",
    "/analytics/gaps",
    "/analytics/daily",
    "/analytics/top-entities",
    "/system/logs",
    "/system/errors",
    "/system/response-times",
    "/system/scheduler",
    "/system/learning",
    "/system/self-evolution",
    "/system/memory",
    "/system/traces",
    "/system/handoffs",
    "/system/memory-graph",
    "/system/quality",
    "/system/circuit-breakers",
    "/system/guardrails",
    "/system/costs",
    "/system/eval/latest",
    "/system/eval/history",
    "/system/optimizer",
    "/system/semantic-cache",
    "/system/judge",
    "/system/dynamic-agents",
]

MUTATING_SYSTEM_ENDPOINTS = [
    ("/system/guardrails/check-input", {"message": "hello", "session_id": "s1"}),
    ("/system/semantic-cache/invalidate", {"query": "abc"}),
    ("/system/judge/evaluate", {"query": "q", "reply": "r"}),
    ("/system/dynamic-agents/create", {"name": "x", "description": "x", "system_prompt_addon": ""}),
]

CHECKPOINT_ENDPOINTS = [
    "/checkpoints/s1",
    "/confirmations/s1",
]

PAGINATION_CASES = [
    ("/api/entities?limit=0", 422),
    ("/api/entities?limit=-1", 422),
    ("/api/search?q=test&limit=0", 422),
    ("/api/search?q=test&limit=-1", 422),
    ("/api/events?limit=0", 422),
    ("/api/events?limit=-1", 422),
    ("/api/itineraries?limit=0", 422),
]

XSS_PAYLOADS = [
    '<script>alert("xss")</script>',
    '<img src=x onerror=alert(1)>',
    '<svg/onload=alert(1)>',
    '<a href="javascript:alert(1)">x</a>',
    '"><script>alert(document.cookie)</script>',
    '<iframe src="data:text/html,<script>alert(1)</script>">',
    '<input onfocus=alert(1) autofocus>',
]

SQLI_PAYLOADS = [
    "'; DROP TABLE entities; --",
    "1 OR 1=1",
    "1' UNION SELECT * FROM users--",
    "admin'--",
    "1; ATTACH DATABASE '/tmp/pwned.db' AS pwned;--",
    "' OR '1'='1",
    "%' OR 1=1--",
    "1 ORDER BY 99--",
]

@pytest.mark.parametrize("path", SYSTEM_ENDPOINTS)
def test_system_get_endpoints_require_admin(client, path):
    assert client.get(path).status_code in (401, 403, 404)

@pytest.mark.parametrize("path,payload", MUTATING_SYSTEM_ENDPOINTS)
def test_system_post_endpoints_require_admin(client, path, payload):
    assert client.post(path, json=payload).status_code in (401, 403, 404)

@pytest.mark.parametrize("path", CHECKPOINT_ENDPOINTS)
def test_checkpoint_reads_require_owner_token(client, path):
    assert client.get(path).status_code in (401, 403)

def test_checkpoint_create_requires_owner_token(client):
    payload = {"session_id": "s1", "messages": [], "tools_used": [], "agent_state": {}, "metadata": {}}
    assert client.post("/checkpoints", json=payload).status_code in (401, 403)

def test_checkpoint_resume_requires_owner_token(client):
    assert client.post("/checkpoints/cp1/resume").status_code in (401, 403)

def test_confirm_requires_owner_token(client):
    assert client.post("/confirm/c1").status_code in (401, 403)

def test_reject_requires_owner_token(client):
    assert client.post("/reject/c1", json={"reason": "no"}).status_code in (401, 403)

def test_public_health_is_minimal(client):
    data = client.get("/health").json()
    forbidden = {"model", "scheduler", "rate_limits", "errors", "response_times", "database", "vector_search"}
    assert forbidden.isdisjoint(data)

def test_deep_health_requires_admin(client):
    assert client.get("/health/deep").status_code in (401, 403, 404)

def test_vector_stats_requires_admin(client):
    assert client.get("/vectors/stats").status_code in (401, 403, 404)

def test_check_phone_does_not_reveal_has_password(client):
    data = client.post("/auth/check-phone", json={"phone": "0901234567"}).json()
    assert "has_password" not in data

@pytest.mark.parametrize("url,expected", PAGINATION_CASES)
def test_pagination_lower_bounds(client, url, expected):
    assert client.get(url).status_code == expected

@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_create_post_xss_payload_not_returned_raw(auth_client, payload):
    r = auth_client.post("/api/posts", json={"content": payload, "post_type": "share"})
    body = r.text
    assert "<script" not in body.lower()
    assert "onerror" not in body.lower()
    assert "javascript:" not in body.lower()

@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_create_comment_xss_payload_not_returned_raw(auth_client, post_id, payload):
    r = auth_client.post(f"/api/posts/{post_id}/comments", json={"content": payload})
    body = r.text
    assert "<script" not in body.lower()
    assert "onerror" not in body.lower()
    assert "javascript:" not in body.lower()

@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
def test_search_sql_payload_does_not_500(client, payload):
    assert client.get("/api/search", params={"q": payload}).status_code in (200, 422)

@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
def test_entities_query_sql_payload_does_not_500(client, payload):
    assert client.get("/api/entities", params={"q": payload}).status_code in (200, 422)

def test_anonymous_report_requires_public_write_token(client):
    r = client.post("/api/report", json={"target_id": "e1", "reason": "wrong"})
    assert r.status_code in (403, 422)

def test_contact_view_requires_public_write_token(client):
    r = client.post("/api/entities/e1/view-contact?action=phone")
    assert r.status_code in (403, 422)

def test_csp_script_src_has_no_unsafe_inline(client):
    csp = client.get("/").headers.get("content-security-policy", "")
    assert "'unsafe-inline'" not in csp.split("script-src", 1)[-1].split(";", 1)[0]
```

## `tests/test_qa_business_integrity.py`

```python
FORBIDDEN_TRANSACTIONAL_TEXT = [
    "Đặt ngay",
    "Mua ngay",
    "Thêm vào giỏ",
    "Thanh toán online",
    "checkout",
    "payment",
    "cart",
    "invoice",
    "purchase",
    "order confirmation",
]

UNICODE_PAYLOADS = [
    "Nguyễn Văn Ả",
    "😀🎉🏖️",
    "Café Trần Hưng Đạo",
    "\u200b\u200c\u200d",
    "A" * 100000,
    "",
    " ",
    "\u202aRTL\u202c injection",
    "Null\x00byte",
    "\n\r\n\r",
]

def test_reply_parent_must_belong_to_same_post(auth_client, post_a, post_b, comment_on_a):
    r = auth_client.post(f"/api/posts/{post_b}/comments", json={"content": "reply content", "parent_id": comment_on_a})
    assert r.status_code == 400

def test_best_answer_only_post_author(auth_client_other, post_id, comment_id):
    r = auth_client_other.post(f"/api/posts/{post_id}/best-answer", json={"comment_id": comment_id})
    assert r.status_code == 403

def test_self_like_rejected(auth_client, own_post_id):
    assert auth_client.post(f"/api/posts/{own_post_id}/like").status_code == 400

def test_self_follow_rejected(auth_client, own_user_id):
    assert auth_client.post(f"/api/follow/user/{own_user_id}").status_code == 400

def test_rsvp_non_event_rejected(auth_client, product_entity_id):
    assert auth_client.post(f"/api/events/{product_entity_id}/rsvp").status_code == 400

def test_set_role_rejects_self_change(admin_client, admin_id):
    assert admin_client.post(f"/admin/users/{admin_id}/role?role=user").status_code == 400

def test_set_role_admin_requires_step_up(admin_client, user_id):
    assert admin_client.post(f"/admin/users/{user_id}/role?role=admin").status_code == 403

def test_intro_only_lint_rejects_transactional_cta():
    for text in FORBIDDEN_TRANSACTIONAL_TEXT:
        with pytest.raises(ValueError):
            validate_intro_only_text(text)

def test_no_runtime_booking_payment_routes(app):
    routes = {getattr(r, "path", "") for r in app.routes}
    forbidden = {"booking", "payment", "checkout", "cart", "invoice"}
    assert all(not any(f in p.lower() for f in forbidden) for p in routes)

def test_reputation_ignores_new_account_like_ring(pg_user_ring):
    assert reputation_for(pg_user_ring.target)["points"] < 80

def test_reputation_requires_approved_content(pg_user, pending_post):
    assert reputation_for(pg_user.id)["points"] == 0

def test_deleted_post_clears_notifications(auth_client, post_with_notification):
    auth_client.delete(f"/api/posts/{post_with_notification.id}")
    assert notification_ref_missing("post", post_with_notification.id)

@pytest.mark.parametrize("payload", UNICODE_PAYLOADS)
def test_profile_unicode_boundaries(auth_client, payload):
    r = auth_client.put("/auth/profile", json={"display_name": payload[:50]})
    assert r.status_code in (200, 422)

@pytest.mark.parametrize("payload", UNICODE_PAYLOADS)
def test_search_unicode_boundaries(client, payload):
    r = client.get("/api/search", params={"q": payload[:200] or "a"})
    assert r.status_code in (200, 422)
```

## `tests/test_qa_performance_data.py`

```python
def test_homepage_uses_bounded_entity_query(monkeypatch, client):
    seen = {}
    monkeypatch.setattr(db, "list_entities", lambda **kw: seen.update(kw) or [])
    client.get("/api/homepage")
    assert seen["limit"] <= 2000

def test_map_pins_uses_bounded_entity_query(monkeypatch, client):
    seen = {}
    monkeypatch.setattr(db, "list_entities", lambda **kw: seen.update(kw) or [])
    client.get("/api/map-pins")
    assert seen["limit"] <= 5000

def test_events_uses_bounded_entity_query(monkeypatch, client):
    seen = {}
    monkeypatch.setattr(db, "list_entities", lambda **kw: seen.update(kw) or [])
    client.get("/api/events?limit=20")
    assert seen["limit"] <= 1000

def test_review_stats_content_query_has_limit():
    source = inspect.getsource(public_api.get_review_stats)
    assert "LIMIT" in source

def test_itineraries_endpoint_has_limit(client):
    assert client.get("/api/itineraries?limit=0").status_code == 422

def test_relationship_missing_from_entity_rejected(pg_conn):
    with pytest.raises(Exception):
        pg_conn.execute("INSERT INTO relationships(from_id,to_id,type) VALUES ('missing','e1','near')")

def test_relationship_missing_to_entity_rejected(pg_conn):
    with pytest.raises(Exception):
        pg_conn.execute("INSERT INTO relationships(from_id,to_id,type) VALUES ('e1','missing','near')")

def test_saved_entity_cleanup_removes_orphans(pg_user):
    insert_saved(pg_user.id, "missing")
    cleanup_orphan_entity_refs()
    assert not saved_exists(pg_user.id, "missing")

def test_visit_cleanup_removes_orphans(pg_user):
    insert_visit(pg_user.id, "missing")
    cleanup_orphan_entity_refs()
    assert not visit_exists(pg_user.id, "missing")

def test_rsvp_cleanup_removes_orphans(pg_user):
    insert_rsvp(pg_user.id, "missing")
    cleanup_orphan_entity_refs()
    assert not rsvp_exists(pg_user.id, "missing")

def test_pg_pool_enabled_uses_bounded_pool(monkeypatch):
    monkeypatch.setenv("PG_USE_POOL", "true")
    monkeypatch.setenv("PG_POOL_MAX", "5")
    assert db._get_pg_pool() is not None

def test_error_envelope_has_code_and_message(client):
    r = client.get("/api/entities/definitely-missing")
    assert {"code", "message"} <= set(r.json()["error"])

def test_comment_thread_pagination_keeps_reply_with_parent(client, seeded_large_thread):
    data = client.get(f"/api/posts/{seeded_large_thread.post_id}/comments?limit=10").json()
    assert all("replies" in c for c in data["comments"])

def test_duplicate_post_returns_409(auth_client):
    payload = {"content": "A unique enough duplicate post", "post_type": "share"}
    auth_client.post("/api/posts", json=payload)
    assert auth_client.post("/api/posts", json=payload).status_code == 409

def test_large_review_stats_does_not_load_all_rows(monkeypatch, client, entity_id):
    monkeypatch.setattr(public_api, "MAX_REVIEW_TEXTS", 500)
    client.get(f"/api/entities/{entity_id}/review-stats")
    assert last_query_limit() <= 500
```

## `tests/test_qa_infra_config.py`

```python
def test_compose_does_not_publish_internal_ports_to_all_interfaces():
    cfg = subprocess.check_output(["docker", "compose", "config"], text=True)
    forbidden = ["0.0.0.0:5432", "0.0.0.0:6379", "0.0.0.0:9090", "0.0.0.0:3001", "0.0.0.0:3100"]
    assert all(x not in cfg for x in forbidden)

def test_compose_requires_postgres_password():
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in text

def test_compose_requires_grafana_password():
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "GRAFANA_ADMIN_PASSWORD:?" in text

def test_deploy_uses_env_host_not_hardcoded_root_ip():
    text = Path("scripts/deploy.sh").read_text(encoding="utf-8")
    assert "root@66.42.57.202" not in text
    assert "VL360_DEPLOY_HOST" in text

def test_nginx_blocks_system_paths_at_edge():
    text = Path("nginx-ssl.conf").read_text(encoding="utf-8")
    assert "deny all" in text and "system" in text

def test_nginx_csp_has_no_script_unsafe_inline():
    csp = extract_nginx_csp("nginx-ssl.conf")
    assert "'unsafe-inline'" not in csp.split("script-src", 1)[1].split(";", 1)[0]

def test_ssl_renewal_documented():
    assert Path("scripts/renew-cert.sh").exists() or "certbot renew" in Path("docs/deployment-guide.md").read_text(encoding="utf-8")

def test_restore_script_exists():
    assert Path("scripts/restore.sh").exists()

def test_restore_dry_run_passes():
    assert subprocess.run(["bash", "scripts/restore.sh", "--dry-run", "--latest"]).returncode == 0

def test_scheduler_can_be_disabled_in_web_process(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    assert scheduler_status()["enabled"] is False

def test_autonomous_agent_default_disabled(monkeypatch):
    monkeypatch.delenv("AUTONOMOUS_AGENT_ENABLED", raising=False)
    assert autonomous_budget.enabled() is False

def test_autonomous_agent_cap_default_present():
    assert autonomous_budget.max_calls_per_day() == 20

def test_failed_telegram_notification_is_queued(monkeypatch):
    monkeypatch.setattr(httpx, "post", side_effect=httpx.TimeoutException("timeout"))
    assert _send_telegram_admins("x") is False
    assert pending_admin_notifications_count() == 1

def test_resource_limits_are_enforced_in_compose():
    cfg = subprocess.check_output(["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.prod.yml", "config"], text=True)
    assert "mem_limit" in cfg or "memory:" in cfg

def test_scheduler_doc_matches_autolearn_default():
    text = Path("agent/scheduler.py").read_text(encoding="utf-8")
    assert "3h" in text and "6h)" not in text.splitlines()[4]
```

## `web-nuxt/tests/qa-a11y.spec.ts`

```ts
import { test, expect } from '@playwright/test'

test('planner picker has no nested buttons', async ({ page }) => {
  await page.goto('/tao-lich-trinh')
  const nested = await page.locator('[role="button"] button').count()
  expect(nested).toBe(0)
})

test('autocomplete listbox options have no nested buttons', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('combobox').fill('chùa')
  const nested = await page.locator('[role="option"] button').count()
  expect(nested).toBe(0)
})

test('modal has accessible name', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /đăng nhập/i }).click()
  await expect(page.getByRole('dialog')).toHaveAccessibleName(/đăng nhập|số điện thoại/i)
})

test('skip link moves focus to main content', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Tab')
  await page.keyboard.press('Enter')
  await expect(page.locator('#main-content')).toBeFocused()
})

test('html lang is Vietnamese', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'vi')
})

test('post content does not execute inline handlers', async ({ page }) => {
  await page.goto('/cong-dong')
  await expect(page.locator('[onerror]')).toHaveCount(0)
})

test('search highlight escapes html', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('combobox').fill('<img src=x onerror=alert(1)>')
  await expect(page.locator('mark')).not.toContainText('<img')
})

test('focus outline visible on nav links', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Tab')
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle)
  expect(outline).not.toBe('none')
})
```

## Minimum Function Count

The suite above defines 26 system endpoint tests by parametrization, 4 mutating system tests, 7 checkpoint tests, 7 pagination tests, 14 XSS tests, 16 SQLi tests, 8 security singleton tests, 14 business tests, 15 performance/data tests, 15 infra tests, and 8 a11y tests: **134 logical regression cases**.
