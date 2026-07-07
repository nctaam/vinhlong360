# Monitoring Stack Setup Guide — vinhlong360

> **STATUS (2026-07-07): ARCHIVED — Tài liệu LỊCH SỬ đã archive (truth-sync 2026-07-07). KHÔNG làm theo chỉ dẫn trong file này — đối chiếu CLAUDE.md + docs/README.md.**
> Guide viết cho stack container + Prometheus/Grafana + Sentry cloud KHÔNG tồn tại trên prod (systemd trên VPS 1GB, chỉ postgres trong Docker; Sentry vi phạm B8). Monitoring thật: StructuredLogger + admin metrics sau X-Admin-Key.


> Date: 2026-06-27 | Status: Reference — implements Phase 3.3 of upgrade-plan.md
> Audience: Solo dev / ops
> Budget: $0 (all free-tier or self-hosted)

---

## 1. Architecture Overview

```
                    ┌──────────────────────────────────────────────┐
                    │                 VPS (Vultr)                  │
                    │                                              │
  UptimeRobot ────→│  nginx:443 ──→ nuxt:3000 ──→ agent:8360     │
  (external)       │       │                          │            │
                    │       │                    /metrics           │
                    │       │                          │            │
                    │  prometheus:9090 ←───────────────┘            │
                    │       │                                      │
                    │  grafana:3001 ←── prometheus (datasource)    │
                    │       │          ← loki (datasource)         │
                    │       │                                      │
                    │  loki:3100 ←── promtail (log forwarder)      │
                    │                    ↑                          │
                    │              Docker container logs            │
                    └──────────────────────────────────────────────┘

  Sentry (cloud) ←── agent (error tracking, 5k events/month free)
  Umami (self-hosted) ←── nuxt (privacy-friendly analytics)
```

| Layer | Tool | Purpose | Cost |
|-------|------|---------|------|
| Metrics | Prometheus + Grafana | Time-series metrics, dashboards | Free (self-hosted) |
| Logs | Loki + Promtail | Centralized log aggregation | Free (self-hosted) |
| Uptime | UptimeRobot | External availability monitoring | Free (50 monitors) |
| Errors | Sentry | Exception tracking + context | Free (5k events/month) |
| Analytics | Umami CE | Privacy-friendly web analytics | Free (self-hosted) |
| Alerting | Telegram bot | Notifications to admin | Free |

---

## 2. Quick Start

All monitoring services are defined in `docker-compose.yml`. To launch:

```bash
# Start all services including monitoring stack
docker compose up -d

# Or start only monitoring services
docker compose up -d prometheus grafana loki promtail
```

Verify services are running:

```bash
docker compose ps | grep -E "prometheus|grafana|loki|promtail"
```

Expected output: all 4 services should show `Up (healthy)` or `Up`.

### Accessing dashboards

| Service | URL | Default credentials |
|---------|-----|---------------------|
| Grafana | http://localhost:3001 | admin / admin (change via `GRAFANA_ADMIN_PASSWORD` in .env) |
| Prometheus | http://localhost:9090 | No auth (restrict via nginx) |

**Production:** Restrict access to Grafana and Prometheus via nginx IP whitelist or VPN:

```nginx
location /grafana/ {
    allow 127.0.0.1;
    allow <your-IP>;
    deny all;
    proxy_pass http://grafana:3000/;
}
```

---

## 3. Prometheus Configuration

Prometheus scrapes metrics from the agent and (optionally) node-exporter.

### Scrape targets

Create `scripts/monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # vinhlong360 agent metrics
  - job_name: 'vl360-agent'
    static_configs:
      - targets: ['agent:8360']
    metrics_path: /metrics
    scrape_interval: 10s

  # Node exporter (system metrics — optional)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Prerequisite: enable metrics module

The agent must have `HAS_METRICS=true` in `.env` for the `/metrics` endpoint to respond. See `docs/module-activation-guide.md` for details.

### Verify Prometheus is scraping

1. Open Prometheus UI at http://localhost:9090
2. Go to Status > Targets
3. `vl360-agent` target should show state `UP`
4. Try a query: `vl360_http_requests_total`

### Data retention

Configured in `docker-compose.yml`:
- Time retention: 30 days (`--storage.tsdb.retention.time=30d`)
- Size retention: 1 GB (`--storage.tsdb.retention.size=1GB`)

At ~15s scrape interval with ~100 metrics, this is sufficient for months of data.

---

## 4. Grafana Setup

### 4.1 Datasource provisioning

Create `scripts/monitoring/grafana-datasources.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
```

This file is mounted into Grafana at startup, so datasources are pre-configured.

### 4.2 Default dashboards

After first login, create these dashboards:

**Dashboard 1: vinhlong360 Overview**

Panels:
- Request rate (req/s) — `rate(vl360_http_requests_total[5m])`
- Error rate (%) — `rate(vl360_http_errors_total[5m]) / rate(vl360_http_requests_total[5m]) * 100`
- Response time p50 — `histogram_quantile(0.5, rate(vl360_http_duration_seconds_bucket[5m]))`
- Response time p99 — `histogram_quantile(0.99, rate(vl360_http_duration_seconds_bucket[5m]))`
- Active sessions — `vl360_active_sessions`
- LLM latency p50 — `histogram_quantile(0.5, rate(vl360_llm_duration_seconds_bucket[5m]))`
- Cache hit rate — `vl360_cache_hits_total / (vl360_cache_hits_total + vl360_cache_misses_total) * 100`

**Dashboard 2: System Health**

Panels:
- CPU usage — `rate(process_cpu_seconds_total[5m]) * 100`
- Memory usage — `process_resident_memory_bytes / 1024 / 1024` (MB)
- Disk usage — from node-exporter if available
- Docker container status — from docker healthchecks
- PostgreSQL connections — `vl360_db_connections_active` (if exposed)

### 4.3 Access control

Change the default admin password:
```bash
# In .env
GRAFANA_ADMIN_PASSWORD=your-strong-password-here
```

Disable sign-up (already configured in docker-compose.yml):
```yaml
GF_USERS_ALLOW_SIGN_UP: "false"
```

---

## 5. Loki + Promtail (Log Aggregation)

### 5.1 Loki configuration

Create `scripts/monitoring/loki-config.yml`:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2026-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 720h  # 30 days

compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
```

### 5.2 Promtail configuration

Create `scripts/monitoring/promtail-config.yml`:

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Docker container logs
  - job_name: docker
    static_configs:
      - targets:
          - localhost
        labels:
          job: docker
          __path__: /var/lib/docker/containers/*/*-json.log

    pipeline_stages:
      - docker: {}
      - match:
          selector: '{job="docker"}'
          stages:
            - regex:
                expression: '.*container_name=(?P<container>[a-zA-Z0-9_-]+).*'
            - labels:
                container:
```

### 5.3 Viewing logs in Grafana

1. Open Grafana > Explore
2. Select "Loki" datasource
3. Query examples:
   - All agent logs: `{container="vl360-agent"}`
   - Agent errors only: `{container="vl360-agent"} |= "ERROR"`
   - Nginx access logs: `{container="vl360-nginx"}`
   - Search for specific text: `{container="vl360-agent"} |= "prompt_injection"`

### 5.4 Retention

Logs are retained for 30 days (configured in `loki-config.yml`). Older logs are automatically deleted by the compactor.

---

## 6. UptimeRobot (External Uptime Monitoring)

### 6.1 Setup

1. Create free account at https://uptimerobot.com (50 monitors included)
2. Add monitors:

| Monitor | Type | URL | Interval | Alert |
|---------|------|-----|----------|-------|
| Health endpoint | HTTP(S) | `https://vinhlong360.vn/health` | 5 min | Telegram |
| Homepage | HTTP(S) | `https://vinhlong360.vn/` | 5 min | Telegram |
| API | HTTP(S) | `https://vinhlong360.vn/api/v1/entities?limit=1` | 5 min | Telegram |
| SSL certificate | HTTP(S) | `https://vinhlong360.vn/` | 1 day | Email (14 days before expiry) |

### 6.2 Telegram alerts

1. Create a Telegram bot via @BotFather, save the bot token
2. Create a group/channel, add the bot
3. Get chat_id: visit `https://api.telegram.org/bot<TOKEN>/getUpdates` after sending a message to the group
4. In UptimeRobot: My Settings > Alert Contacts > Add > Telegram
   - Enter Bot Token and Chat ID
5. Assign this alert contact to all monitors

### 6.3 Status page (optional)

UptimeRobot offers a free public status page. Useful for transparency:
- URL: `stats.uptimerobot.com/your-page`
- Shows uptime percentage, response time graph, incident history

---

## 7. Sentry (Error Tracking)

### 7.1 Setup

1. Create free account at https://sentry.io (5,000 events/month)
2. Create a Python project
3. Copy the DSN (Data Source Name)
4. Add to `.env`:

```bash
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
```

5. Install SDK in agent:

```bash
pip install sentry-sdk[fastapi]
```

6. Initialize in `agent/server.py` (agent session scope — document only, do not modify):

```python
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "development"),
)
```

### 7.2 What gets captured

- Unhandled exceptions with full stack trace
- Request context (URL, method, headers — PII stripped)
- Release tracking (git commit SHA)
- Performance traces (slow endpoints)

### 7.3 Budget management

Free tier: 5,000 events/month. To stay within budget:
- Set `traces_sample_rate=0.1` (10% sampling)
- Filter out noisy errors (404s, expected validation errors)
- Use `before_send` callback to drop low-value events

---

## 8. Key Metrics to Monitor

### Application metrics (from agent /metrics)

| Metric | Type | Description | Target |
|--------|------|-------------|--------|
| `vl360_http_requests_total` | Counter | Total HTTP requests by method + path + status | — |
| `vl360_http_duration_seconds` | Histogram | Response time distribution | p50 <500ms, p99 <2s |
| `vl360_http_errors_total` | Counter | HTTP 4xx and 5xx responses | Error rate <5% |
| `vl360_llm_requests_total` | Counter | Total LLM API calls | — |
| `vl360_llm_duration_seconds` | Histogram | LLM response time | p50 <3s |
| `vl360_llm_tokens_total` | Counter | Total tokens consumed | Daily budget cap |
| `vl360_cache_hits_total` | Counter | Cache hits (prompt, semantic) | Hit rate >50% |
| `vl360_cache_misses_total` | Counter | Cache misses | — |
| `vl360_active_sessions` | Gauge | Currently active chat sessions | — |
| `vl360_db_query_duration_seconds` | Histogram | Database query time | p99 <500ms |

### System metrics (from node-exporter or docker stats)

| Metric | Target | Alert threshold |
|--------|--------|-----------------|
| CPU usage | <70% sustained | >85% for 5 min |
| Memory usage | <80% | >90% |
| Disk usage | <70% | >80% |
| Network I/O | — | Spike >10x baseline |

### Business metrics (from Umami / custom)

| Metric | Target (month 1-3) | Target (month 4-12) |
|--------|--------------------|--------------------|
| Unique visitors / week | 200+ | 2,000+ |
| Page views / session | >2 | >3 |
| Chat sessions / day | 10+ | 100+ |
| Bounce rate | <60% | <45% |

---

## 9. Alert Rules

### Grafana alerting configuration

Create alert rules in Grafana > Alerting > Alert Rules:

#### Response time alert

```yaml
name: High Response Time
condition: avg(vl360_http_duration_seconds{quantile="0.99"}) > 2
for: 5m
labels:
  severity: warning
annotations:
  summary: "p99 response time exceeds 2 seconds"
```

#### Error rate alert

```yaml
name: High Error Rate
condition: >
  rate(vl360_http_errors_total[5m]) /
  rate(vl360_http_requests_total[5m]) > 0.05
for: 5m
labels:
  severity: critical
annotations:
  summary: "Error rate exceeds 5%"
```

#### Disk usage alert

```yaml
name: Disk Space Low
condition: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.2
for: 10m
labels:
  severity: warning
annotations:
  summary: "Disk usage exceeds 80%"
```

#### LLM latency alert

```yaml
name: LLM Slow Response
condition: histogram_quantile(0.5, rate(vl360_llm_duration_seconds_bucket[5m])) > 5
for: 10m
labels:
  severity: warning
annotations:
  summary: "LLM p50 latency exceeds 5 seconds"
```

### Notification channels

Configure Grafana to send alerts via:
1. **Telegram** (primary): same bot as UptimeRobot alerts
2. **Email** (backup): for non-urgent warnings

Setup: Grafana > Alerting > Contact Points > Add > Telegram
- Bot Token: same as UptimeRobot
- Chat ID: same admin group

---

## 10. Umami Analytics (Self-hosted)

### 10.1 Why Umami

- **Privacy-friendly**: cookieless, GDPR-compliant by default
- **Self-hosted**: data stays on your VPS, no third-party tracking
- **Free**: open-source (MIT license)
- **Lightweight**: minimal impact on page load

### 10.2 Setup

Add Umami to `docker-compose.yml` (future addition):

```yaml
umami:
  image: ghcr.io/umami-software/umami:postgresql-latest
  container_name: vl360-umami
  ports:
    - "3002:3000"
  environment:
    DATABASE_URL: postgresql://vl360:${POSTGRES_PASSWORD}@postgres:5432/umami
    APP_SECRET: ${UMAMI_APP_SECRET:-change-me}
  depends_on:
    postgres:
      condition: service_healthy
  restart: unless-stopped
```

Create the Umami database:
```sql
CREATE DATABASE umami;
```

### 10.3 Integration with Nuxt

Add the Umami tracking script to `web-nuxt/nuxt.config.ts` (SEO/meta scope):

```typescript
app: {
  head: {
    script: [
      {
        src: 'https://vinhlong360.vn/umami/script.js',
        'data-website-id': '<your-website-id>',
        async: true,
        defer: true,
      }
    ]
  }
}
```

### 10.4 Key pages to track

- Homepage (`/`)
- Entity detail pages (`/kham-pha/:slug`)
- Search results (`/tim-kiem`)
- Chat interactions
- Admin pages (separate tracking for internal analytics)

---

## Docker Health Checks

All critical services have health checks configured in `docker-compose.yml`:

| Service | Check | Interval | Retries |
|---------|-------|----------|---------|
| postgres | `pg_isready -U vl360 -d vinhlong360` | 10s | 5 |
| redis | `redis-cli ping` | 10s | 3 |
| agent | `curl -f http://localhost:8360/health` | 30s | 3 |
| nuxt | `wget -qO- http://localhost:3000/` | 30s | 3 |

Docker automatically restarts containers when healthchecks fail (restart policy: `unless-stopped`).

## Resource Limits

Configured in `docker-compose.prod.yml`:

| Service | Memory | CPU |
|---------|--------|-----|
| postgres | 512M | 1.0 |
| redis | 128M | 0.5 |
| agent | 1G | 2.0 |
| bot-gw | 256M | 0.5 |
| nuxt | 512M | 1.0 |

Monitor resource usage:
```bash
docker stats --no-stream
```

---

## References

- Phase 3.3 of `docs/upgrade-plan.md` — observability roadmap
- `docs/module-activation-guide.md` — enabling the metrics module (`HAS_METRICS=true`)
- `docs/incident-runbook.md` — using monitoring data during incidents
- `docs/deployment-guide.md` — VPS deployment context
- Prometheus docs: https://prometheus.io/docs/
- Grafana docs: https://grafana.com/docs/
- Loki docs: https://grafana.com/docs/loki/
- UptimeRobot: https://uptimerobot.com
- Sentry: https://docs.sentry.io/platforms/python/integrations/fastapi/
- Umami: https://umami.is/docs
