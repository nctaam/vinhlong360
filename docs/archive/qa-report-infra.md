> **STATUS (2026-07-07): ARCHIVED — Snapshot QA 2026-06-28 nằm sai chỗ (repo root) — archive 2026-07-07. Một phần "release blocker" đã fix từ lâu (vd /metrics đã gate sau X-Admin-Key). KHÔNG dùng làm danh sách việc hiện hành.**

# QA Infra Report - vinhlong360

Audit date: 2026-06-28

Scope: Docker/Compose, Nginx, deployment script, runtime config, background scheduler, backups, and operational controls.

## Summary

| Severity | Count | Notes |
|---|---:|---|
| P0 Critical | 0 | No committed real secret found in `.env.example`; Dockerfile runs non-root. |
| P1 High | 2 | Host-published infrastructure ports and root/IP deploy target need hardening. |
| P2 Medium | 6 | Resource limits, backups, cert renewal, scheduler, monitoring exposure. |
| P3 Low | 1 | Documentation/config drift. |

## Findings

### [P1] Finding-044: Compose publishes database, cache, monitoring, app, and bot ports to the host

**Chiều:** Deployment / Security  
**File:** `docker-compose.yml:10`, `docker-compose.yml:26`, `docker-compose.yml:40`, `docker-compose.yml:115`, `docker-compose.yml:131`, `docker-compose.yml:146`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-200

**Mô tả:** Postgres `5432`, Redis `6379`, agent `8360`, bot gateway `8361`, Nuxt `3000`, Prometheus `9090`, Grafana `3001`, and Loki `3100` are published on the host. If firewall rules are absent or drift, these services become reachable outside the Docker network.

**Exploit scenario:**
1. VPS firewall allows one published service.
2. Attacker connects directly to Redis/Postgres/Grafana/Prometheus.
3. Internal data or control surfaces bypass Nginx/auth assumptions.

**Root cause:** Compose exposes service ports for convenience instead of binding internal services to `127.0.0.1` or Docker-only networks.

**Fix:**
```yaml
postgres:
  ports:
    - "127.0.0.1:5432:5432"
redis:
  expose:
    - "6379"
prometheus:
  ports:
    - "127.0.0.1:9090:9090"
```

**Test:**
```bash
docker compose config | grep -E '0.0.0.0:(5432|6379|9090|3001|3100)' && exit 1 || exit 0
```

**Effort:** M

### [P1] Finding-045: Deployment script hard-codes root SSH target and server IP

**Chiều:** Deployment / Security  
**File:** `scripts/deploy.sh:22`, `scripts/deploy.sh:23`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-798

**Mô tả:** The deploy script targets `root@66.42.57.202` with a fixed key path. This is not an application secret, but it normalizes root deploys and leaks infrastructure metadata into source.

**Exploit scenario:**
1. Repo is shared with a contractor or public mirror.
2. Attacker learns the production IP and SSH user.
3. SSH brute-force and targeted probing become easier.

**Root cause:** Deployment target configuration is embedded in the script.

**Fix:**
```bash
VPS="${VL360_DEPLOY_HOST:?set VL360_DEPLOY_HOST}"
KEY="${VL360_DEPLOY_KEY:?set VL360_DEPLOY_KEY}"
SSH_USER="${VL360_DEPLOY_USER:-deploy}"
```

**Test:**
```bash
VL360_DEPLOY_HOST=example VL360_DEPLOY_KEY=/tmp/key bash -n scripts/deploy.sh
```

**Effort:** S

### [P2] Finding-046: Compose default credentials are unsafe if reused in production

**Chiều:** Deployment / Secrets  
**File:** `docker-compose.yml:8`, `docker-compose.yml:44`, `docker-compose.yml:137`, `.env.example:77`, `.env.example:80`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-521

**Mô tả:** Compose defaults include `POSTGRES_PASSWORD:-vl360_dev_password` and Grafana default `admin` unless overridden. `.env.example` warns to change them, but production compose should fail closed.

**Exploit scenario:**
1. Operator forgets to set `POSTGRES_PASSWORD` or `GRAFANA_ADMIN_PASSWORD`.
2. Services boot with known defaults.
3. Published ports or local compromise expose admin/database access.

**Root cause:** Defaults favor development convenience over production fail-closed behavior.

**Fix:**
```yaml
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}
  GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:?GRAFANA_ADMIN_PASSWORD required}
```

**Test:**
```bash
unset POSTGRES_PASSWORD
docker compose config >/dev/null && exit 1 || exit 0
```

**Effort:** S

### [P2] Finding-047: Production resource limits under `deploy:` may not be enforced by classic Compose

**Chiều:** Deployment / Performance  
**File:** `docker-compose.prod.yml:3`, `docker-compose.prod.yml:26`, `docker-compose.prod.yml:54`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** `docker-compose.prod.yml` sets memory/CPU limits under `deploy.resources`. Depending on Docker Compose mode/version, `deploy` fields can be ignored outside Swarm unless translated to supported resource settings.

**Exploit scenario:**
1. Agent or Nuxt has a memory spike.
2. Compose runtime ignores `deploy.resources`.
3. VPS OOM-kills unrelated services.

**Root cause:** Runtime resource enforcement is expressed in a field that may be advisory in the chosen deployment mode.

**Fix:**
```yaml
agent:
  mem_limit: 1g
  cpus: 2.0
```

**Test:**
```bash
docker inspect vl360-agent --format '{{.HostConfig.Memory}}' | grep -v '^0$'
```

**Effort:** M

### [P2] Finding-048: Backups are created before deploy but restore is not automated or rehearsed

**Chiều:** Deployment / Data Integrity  
**File:** `scripts/deploy.sh:77`, `scripts/deploy.sh:84`, `scripts/deploy.sh:145`  
**OWASP:** A08:2021 Software and Data Integrity Failures  
**CWE:** CWE-799

**Mô tả:** `deploy.sh` creates DB and code backups and rotates the newest 6. That is good. The missing piece is an automated restore command and a periodic restore verification.

**Exploit scenario:**
1. Bad deploy corrupts entity data.
2. Backup exists but restore steps are manual.
3. Recovery time depends on operator memory during an incident.

**Root cause:** Backup creation is automated; restore verification is not.

**Fix:**
```bash
scripts/restore.sh --db backups/db-pre-deploy-TS.sql --code backups/pre-deploy-TS.tar.gz --verify
```

**Test:**
```bash
scripts/restore.sh --dry-run --latest
```

**Effort:** M

### [P2] Finding-049: SSL config assumes certificate files but does not include renewal workflow

**Chiều:** Deployment / Availability  
**File:** `nginx-ssl.conf:42`, `nginx-ssl.conf:43`, `nginx-ssl.conf:53`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-295

**Mô tả:** Nginx references `/etc/nginx/ssl/fullchain.pem` and `privkey.pem` and enables stapling. The repo does not show certbot renewal wiring or a reload hook.

**Exploit scenario:**
1. Certificate expires.
2. Nginx continues serving an invalid certificate.
3. Users and search crawlers fail TLS validation.

**Root cause:** TLS runtime config and renewal automation are split.

**Fix:**
```bash
certbot renew --deploy-hook "docker compose exec nginx nginx -s reload"
systemctl list-timers | grep certbot
```

**Test:**
```bash
openssl x509 -checkend 1209600 -noout -in ssl/certs/fullchain.pem
```

**Effort:** S

### [P2] Finding-050: Nginx proxies internal/system paths publicly and depends on app-side gating

**Chiều:** Deployment / Security  
**File:** `nginx-ssl.conf:120`, `agent/server.py:1014`  
**OWASP:** A05:2021 Security Misconfiguration  
**CWE:** CWE-306

**Mô tả:** Nginx forwards `/health`, `/analytics`, `/reload`, `/system`, `/freshness`, and similar paths to the agent. App-side gates help, but defense-in-depth should block or restrict internal paths at the edge.

**Exploit scenario:**
1. App environment gate is mis-set.
2. Nginx still forwards `/system/logs`.
3. Internal endpoint becomes externally reachable.

**Root cause:** Edge proxy does not enforce internal route policy.

**Fix:**
```nginx
location ~ ^/(analytics|system|reload|metrics) {
    allow 127.0.0.1;
    deny all;
    proxy_pass http://vl360_agent;
}
```

**Test:**
```bash
curl -I https://vinhlong360.vn/system/logs | grep -E '403|404'
```

**Effort:** S

### [P2] Finding-051: Scheduler is on by default and always runs non-autonomous jobs

**Chiều:** Background Tasks / Deployment / Resilience  
**File:** `agent/scheduler.py:61`, `agent/scheduler.py:670`, `agent/scheduler.py:681`, `agent/scheduler.py:684`  
**OWASP:** A04:2021 Insecure Design  
**CWE:** CWE-400

**Mô tả:** Autonomous LLM tasks are off by default, which is good. However `SCHEDULER_ENABLED` defaults true and non-autonomous jobs such as data-sync, cache-warmup, cleanup, and rate-limit GC run in-process by default.

**Exploit scenario:**
1. Agent starts under high user traffic.
2. Background tasks run in the same process.
3. User-facing latency competes with maintenance work.

**Root cause:** Background workload isolation is not explicit for production.

**Fix:**
```bash
SCHEDULER_ENABLED=false  # web process
python agent/scheduler.py  # separate systemd service with CPU/memory limits
```

**Test:**
```python
def test_web_process_can_disable_scheduler(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    assert scheduler_status()["enabled"] is False
```

**Effort:** M

### [P2] Finding-052: Telegram admin notifications are best-effort without retry queue

**Chiều:** Background Tasks / Error Handling  
**File:** `agent/scheduler.py:352`, `agent/scheduler.py:362`, `agent/scheduler.py:376`  
**OWASP:** A09:2021 Security Logging and Monitoring Failures  
**CWE:** CWE-778

**Mô tả:** Admin digest and admin Telegram sends use one HTTP request per chat and log errors. There is no durable retry queue for failed admin alerts.

**Exploit scenario:**
1. Telegram API times out during moderation spike.
2. Digest/alert is lost.
3. Admin misses reports or quality failures.

**Root cause:** Notification delivery is fire-and-forget.

**Fix:**
```python
enqueue_admin_notification(text)
retry_pending_admin_notifications(max_age_hours=24, max_attempts=5)
```

**Test:**
```python
def test_failed_admin_notification_is_queued(monkeypatch):
    monkeypatch.setattr(httpx, "post", side_effect=httpx.TimeoutException("timeout"))
    assert _send_telegram_admins("x") is False
    assert pending_admin_notifications_count() == 1
```

**Effort:** M

### [P3] Finding-053: Documentation and runtime scheduler comments disagree on auto-learn cadence

**Chiều:** Background Tasks / Code Quality  
**File:** `agent/scheduler.py:5`, `agent/scheduler.py:67`, `agent/scheduler.py:668`  
**OWASP:** N/A  
**CWE:** CWE-1054

**Mô tả:** The scheduler header says auto-learn runs every 6h, while `AUTO_LEARN_INTERVAL` defaults to 3h and task comments also say 3h. This is small but confusing during incident review.

**Exploit scenario:**
1. Operator estimates LLM/background cost from header comment.
2. Actual cadence is different.
3. Budget or load expectations are wrong.

**Root cause:** Comments were not updated with cadence changes.

**Fix:**
```python
"""Auto-learn from knowledge gaps every LEARN_INTERVAL_AUTOLEARN seconds (default 3h)."""
```

**Test:**
```python
def test_scheduler_doc_mentions_default_autolearn_interval():
    assert "default 3h" in Path("agent/scheduler.py").read_text(encoding="utf-8")
```

**Effort:** S
