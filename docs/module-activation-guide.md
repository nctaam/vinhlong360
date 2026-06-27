# Dormant Module Activation Guide — vinhlong360

> Date: 2026-06-27 | Status: Reference — implements Phase 3.2 of upgrade-plan.md
> Audience: Solo dev / ops

---

## Overview

The agent backend ships with ~15 feature modules controlled by environment variable flags. All default to `false` (dormant). This guide documents the activation order, prerequisites, verification steps, and rollback procedures for each module.

**Golden rule:** Activate one module at a time. Wait at least 24 hours between activations to isolate issues.

---

## Tier 1 — Safe to Activate Immediately

These modules are well-tested, low-risk, and provide immediate value. Activate in this order.

### 1. prompt_cache

| Property | Value |
|----------|-------|
| **Flag** | `HAS_PROMPT_CACHE=true` |
| **What it does** | Caches system prompts to reduce repeated token costs. Saves ~30% on LLM token usage by reusing cached system prompt prefixes across sessions. |
| **Prerequisites** | None (in-memory cache) |
| **How to activate** | Add `HAS_PROMPT_CACHE=true` to `.env` on VPS, then restart agent |
| **Verification** | Check logs for `prompt_cache: HIT` messages. After 10+ chats, compare daily LLM cost in `cost_tracker` output — should drop ~30%. |
| **Risks** | Low. Stale cache if system prompt changes — cache auto-invalidates on prompt hash change. |
| **Rollback** | Set `HAS_PROMPT_CACHE=false`, restart agent. No data loss. |

### 2. circuit_breaker

| Property | Value |
|----------|-------|
| **Flag** | `HAS_CIRCUIT_BREAKER=true` |
| **What it does** | Monitors external service calls (LLM API, weather API). If a service fails repeatedly (e.g., 5 failures in 60 seconds), the circuit "opens" and returns a cached/fallback response instead of hanging. Auto-recovers after a cooldown period. |
| **Prerequisites** | None |
| **How to activate** | Add `HAS_CIRCUIT_BREAKER=true` to `.env`, restart agent |
| **Verification** | Check `/health` response — features should show `circuit_breaker: true`. Simulate LLM downtime (set invalid `LLM_BASE_URL` temporarily) — chat should return a graceful fallback message within 2 seconds instead of timing out. |
| **Risks** | Low. In worst case, circuit opens too aggressively during transient failures. The cooldown period handles auto-recovery. |
| **Rollback** | Set `HAS_CIRCUIT_BREAKER=false`, restart. Direct service calls resume. |

### 3. guardrails

| Property | Value |
|----------|-------|
| **Flag** | `HAS_GUARDRAILS=true` |
| **What it does** | Three-layer input protection: (1) prompt injection detection using 30+ regex patterns for Vietnamese and English attack strings, (2) PII masking that strips phone numbers, emails, CCCD (citizen ID), bank accounts from LLM context, (3) input validation and sanitization. |
| **Prerequisites** | None |
| **How to activate** | Add `HAS_GUARDRAILS=true` to `.env`, restart agent |
| **Verification** | Send a chat message containing a known injection pattern (e.g., "ignore previous instructions"). Response should be a polite refusal. Send a message containing a phone number — check LLM logs to confirm the number was masked before being sent to the LLM. |
| **Risks** | Low. False positives on legitimate queries that resemble injection patterns. Monitor user feedback for blocked queries that should have been allowed. |
| **Rollback** | Set `HAS_GUARDRAILS=false`, restart. Input passes through unfiltered (pre-existing behavior). |

### 4. cost_tracker

| Property | Value |
|----------|-------|
| **Flag** | `HAS_COST_TRACKER=true` |
| **What it does** | Tracks per-session LLM token usage and estimated cost. Enables the daily LLM call budget cap (`AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY`). Essential for budget control on a <$40/month project. |
| **Prerequisites** | None (writes to in-memory counters and/or DB) |
| **How to activate** | Add `HAS_COST_TRACKER=true` to `.env`, restart agent |
| **Verification** | After a few chat sessions, check `/health` or admin dashboard for cost metrics. Verify daily cap is enforced by setting `AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY=2` and triggering 3 calls. |
| **Risks** | Low. Tracking overhead is negligible. |
| **Rollback** | Set `HAS_COST_TRACKER=false`, restart. Cost data stops being collected but no data loss. |

### 5. metrics

| Property | Value |
|----------|-------|
| **Flag** | `HAS_METRICS=true` |
| **What it does** | Exposes a Prometheus-compatible `/metrics` endpoint on the agent server (port 8360). Exports request counts, response times (histogram), error rates, LLM latency, cache hit rates, and active sessions. |
| **Prerequisites** | None for the endpoint itself. For collection, requires Prometheus scraping (see `docs/monitoring-setup.md`). |
| **How to activate** | Add `HAS_METRICS=true` to `.env`, restart agent |
| **Verification** | `curl http://localhost:8360/metrics` — should return Prometheus text format with `vl360_*` metric names. |
| **Risks** | Low. The `/metrics` endpoint is unauthenticated by default — restrict access via nginx (allow only from Prometheus container IP or localhost). |
| **Rollback** | Set `HAS_METRICS=false`, restart. The `/metrics` endpoint stops responding. |

**Security note:** Add to nginx.conf after enabling:
```nginx
location /metrics {
    allow 127.0.0.1;
    allow 172.16.0.0/12;  # Docker network
    deny all;
    proxy_pass http://agent:8360;
}
```

---

## Tier 2 — Activate After 1 Week Observation

These modules have higher complexity or external dependencies. Enable them after Tier 1 modules have been running stably for at least 1 week.

### 6. semantic_cache

| Property | Value |
|----------|-------|
| **Flag** | `HAS_SEMANTIC_CACHE=true` |
| **What it does** | Two-level query cache: L1 is exact-match (fast, in-memory), L2 is fuzzy/semantic (cosine similarity). If a user asks a question similar to a recently answered one, returns the cached response instead of calling the LLM. Reduces LLM costs and response latency for common queries. |
| **Prerequisites** | **Redis required** — set `REDIS_URL=redis://redis:6379/0` in `.env`. Redis is used for the L2 semantic cache persistence. |
| **How to activate** | Ensure Redis is running (`docker compose ps redis`). Add `HAS_SEMANTIC_CACHE=true` to `.env`, restart agent. |
| **Verification** | Ask the same question twice within 5 minutes. Second response should be near-instant (<100ms) and logs should show `semantic_cache: HIT`. Ask a slightly rephrased version — should also hit L2 cache. |
| **Risks** | Medium. (1) Stale responses for time-sensitive queries (weather, events). Cache TTL should be configured appropriately (default: 1 hour). (2) Memory usage grows with unique queries — monitor Redis memory. (3) False positive cache hits on semantically different queries. |
| **Rollback** | Set `HAS_SEMANTIC_CACHE=false`, restart. Flush Redis cache: `redis-cli FLUSHDB`. |

### 7. orchestrator

| Property | Value |
|----------|-------|
| **Flag** | `HAS_ORCHESTRATOR=true` |
| **What it does** | Routes incoming queries to specialized agent handlers based on intent classification. For example, a search query goes to SearchAgent (uses `LLM_MODEL_MINI`), a complex planning query goes to the full model, and a simple FAQ goes to a cached response. Optimizes cost by using cheaper models for simpler tasks. |
| **Prerequisites** | Recommend enabling `cost_tracker` first (to measure cost impact). The orchestrator uses `LLM_MODEL_MINI` env var for routing cheaper queries. |
| **How to activate** | Add `HAS_ORCHESTRATOR=true` to `.env`, restart agent |
| **Verification** | Send different query types: (1) "Tìm quán ăn ở Vĩnh Long" (search intent — should route to SearchAgent), (2) "Lập lịch trình 3 ngày" (planning intent — should route to full model). Check logs for `orchestrator: routed to <agent>` messages. |
| **Risks** | Medium. Misrouting can degrade response quality. The intent classifier may need tuning for Vietnamese queries. Test with a diverse set of queries before enabling in production. |
| **Rollback** | Set `HAS_ORCHESTRATOR=false`, restart. All queries go to the default handler. |

### 8. checkpoints

| Property | Value |
|----------|-------|
| **Flag** | `HAS_CHECKPOINTS=true` |
| **What it does** | Adds multi-turn confirmation steps for high-stakes chat operations. When the AI generates an itinerary or detailed report, it first presents a preview and asks for user confirmation before finalizing. Prevents the AI from committing to a long response that the user didn't want. |
| **Prerequisites** | None, but works best with `orchestrator` enabled (orchestrator routes to checkpoint-aware handlers). |
| **How to activate** | Add `HAS_CHECKPOINTS=true` to `.env`, restart agent |
| **Verification** | Ask the chatbot to create a 3-day itinerary. It should present an outline first and ask "Bạn muốn tôi chi tiết hóa lịch trình này không?" before generating the full version. |
| **Risks** | Medium. Adds an extra turn to conversations — may feel slow for simple queries. The checkpoint logic needs to correctly identify which queries warrant confirmation. |
| **Rollback** | Set `HAS_CHECKPOINTS=false`, restart. All responses are generated in a single turn. |

---

## Tier 3 — Activate After Images/Data Ready

These modules have external dependencies (APIs, data pipelines) that must be set up first.

### 9. llm_judge

| Property | Value |
|----------|-------|
| **Flag** | `LLM_JUDGE_ENABLED=true` |
| **What it does** | After every chat response, sends the response to a secondary LLM call that scores quality (relevance, accuracy, helpfulness) on a 1-5 scale. Scores are logged for telemetry and can be used to identify problematic queries or model regressions. |
| **Prerequisites** | `cost_tracker` should be active (this doubles LLM calls per chat). Budget must accommodate the extra cost. |
| **How to activate** | Add `LLM_JUDGE_ENABLED=true` to `.env`, restart agent |
| **Verification** | After a chat, check logs/telemetry for `llm_judge_score` entries. Each response should have a numeric score. |
| **Risks** | **Cost** — adds 1 extra LLM call per chat session. At scale, this can significantly increase costs. Enable only when you have budget headroom and need quality metrics. |
| **Rollback** | Set `LLM_JUDGE_ENABLED=false`, restart. No more judge calls. Historical scores are retained. |

### 10. image_recognition

| Property | Value |
|----------|-------|
| **Flag** | `HAS_IMAGE_RECOGNITION=true` |
| **What it does** | Enables image upload and classification in chat. Users can upload a photo and the AI identifies the location, dish, or product using a Vision API. |
| **Prerequisites** | (1) Vision API key configured, (2) S3 storage configured (`S3_*` env vars) for image upload pipeline, (3) Image upload UI in frontend (Phase 1.1 of upgrade plan). |
| **How to activate** | Configure Vision API credentials, ensure S3 is working, add `HAS_IMAGE_RECOGNITION=true` to `.env`, restart agent |
| **Verification** | Upload an image via chat. The AI should describe what it sees and attempt to match it to entities in the knowledge base. |
| **Risks** | Medium. (1) Vision API costs per image, (2) Potential for inappropriate image uploads — needs moderation, (3) Accuracy depends on Vision model quality. |
| **Rollback** | Set `HAS_IMAGE_RECOGNITION=false`, restart. Image upload feature disappears from chat. |

---

## Do NOT Activate

These modules are incomplete, high-risk, or unnecessary at current scale.

| Module | Flag | Reason |
|--------|------|--------|
| **reflexion** | (none) | ~40% complete. Self-critique loop that re-generates responses. Incomplete error handling, can loop infinitely. |
| **self_optimizer** | `HAS_OPTIMIZER` | ~20% complete. PoC that tunes prompts based on llm_judge scores. Not production-ready. |
| **dynamic_agents** | `HAS_DYNAMIC_AGENTS` | ~30% complete. Skeleton code for runtime agent creation. Security implications not audited. |
| **vector_search** | `HAS_VECTOR` | ~60% complete. BM25 full-text search is sufficient for current scale (1753 entities). Vector search adds Redis/embedding complexity without proportional benefit. Re-evaluate at 10k+ entities. |
| **realtime** | `HAS_REALTIME` | ~40% complete. WebSocket-based real-time features. Not needed for current use cases. |

---

## Activation Procedure (Generic)

```bash
# 1. SSH into VPS
ssh deploy@66.42.57.202

# 2. Edit .env
nano /opt/vinhlong360/.env
# Add: HAS_MODULE_NAME=true

# 3. Restart agent service
sudo systemctl restart vl360-agent

# 4. Verify health
curl -s http://localhost:8360/health | python3 -m json.tool
# Check that the module appears in "features" with value true

# 5. Monitor logs for 30 minutes
journalctl -u vl360-agent -f --since "30 minutes ago"
# Look for errors related to the new module

# 6. Test functionality
# (Module-specific tests — see each module's "Verification" section above)
```

## Rollback Procedure (Generic)

```bash
# 1. Set flag back to false
nano /opt/vinhlong360/.env
# Change: HAS_MODULE_NAME=false

# 2. Restart
sudo systemctl restart vl360-agent

# 3. Verify health
curl -s http://localhost:8360/health | python3 -m json.tool
```

---

## Environment Variable Quick Reference

```bash
# Tier 1 — safe to enable immediately
HAS_PROMPT_CACHE=true
HAS_CIRCUIT_BREAKER=true
HAS_GUARDRAILS=true
HAS_COST_TRACKER=true
HAS_METRICS=true

# Tier 2 — enable after 1 week observation
HAS_SEMANTIC_CACHE=true      # requires Redis
HAS_ORCHESTRATOR=true
HAS_CHECKPOINTS=true

# Tier 3 — enable after prerequisites met
LLM_JUDGE_ENABLED=true       # costs 1 extra LLM call/chat
HAS_IMAGE_RECOGNITION=true   # requires Vision API + S3

# Do NOT enable
# HAS_OPTIMIZER=true          # PoC only
# HAS_DYNAMIC_AGENTS=true     # skeleton
# HAS_VECTOR=true             # BM25 sufficient
# HAS_REALTIME=true           # incomplete
```
