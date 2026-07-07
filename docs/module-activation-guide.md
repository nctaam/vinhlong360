# Module Activation Guide — vinhlong360

> **STATUS (2026-07-07): active — đã truth-sync.** The 2026-06-27 version described a "dormant modules / HAS_* env flag" mechanism that never existed — this rewrite documents the real mechanism (try-import) and the env flags that actually work; the old tier/activation-order content is superseded.
> Original date: 2026-06-27, rewritten 2026-07-07 | Audience: Solo dev / ops

---

## Overview

There is **no dormant-module system**. The `HAS_*` names are **Python variables, not environment variables**. `agent/server.py:87-248` sets each one via a try-import guard:

```python
try:
    from guardrails import injection_detector, pii_masker, ...
    HAS_GUARDRAILS = True
except ImportError:
    HAS_GUARDRAILS = False
```

Consequences (verified against the code, 2026-07-07):

- **Nothing in `agent/` reads `HAS_*` from the environment** (grep: 0 hits). Putting `HAS_X=true` or `HAS_X=false` in `.env` is a no-op.
- **All 26 guarded modules import cleanly on the current codebase → every `HAS_*` is `True` — everything is ON, in dev and in prod, today.** That includes guardrails (PII masking + injection detection, live on the chat path), metrics, vector_search, semantic_cache, orchestrator, checkpoints, self_optimizer, and dynamic_agents.
- **The only way to disable one of these modules is a code change** (remove/guard the import, or remove the module file) plus a redeploy. There is no runtime toggle and no env rollback.
- `agent/feature_flags.py` has a `FEATURE_*` override mechanism, but `server.py` only *registers* flags there — it never gates runtime behaviour through it.

Try-import flags, in `server.py` order: `HAS_VECTOR`, `HAS_REALTIME`, `HAS_CIRCUIT_BREAKER`, `HAS_PARALLEL`, `HAS_AUTOCORRECT`, `HAS_RECOMMENDER`, `HAS_FRESHNESS`, `HAS_IMAGE_RECOGNITION`, `HAS_METRICS`, `HAS_AB_TESTING`, `HAS_PROMPT_CACHE`, `HAS_ORCHESTRATOR`, `HAS_MEMORY_GRAPH`, `HAS_TRACING`, `HAS_CONTEXTUAL`, `HAS_KB_CONTEXT`, `HAS_EXPERIENCE`, `HAS_FEWSHOT`, `HAS_CHECKPOINTS`, `HAS_GUARDRAILS`, `HAS_COST_TRACKER`, `HAS_EVAL`, `HAS_OPTIMIZER`, `HAS_SEMANTIC_CACHE`, `HAS_LLM_JUDGE`, `HAS_DYNAMIC_AGENTS`.

---

## Environment flags that DO work

These are the real runtime switches (defaults verified in `agent/config.py` / `agent/server.py`):

| Env var | Default | Effect |
|---------|---------|--------|
| `LLM_JUDGE_ENABLED` | `false` | Response-quality judge. Runs only when the `llm_judge` module imported OK **and** this is `true` (`server.py:58`, gated at the chat handler). Cost: +1 LLM call per chat — keep off unless budget headroom. |
| `AUTONOMOUS_AGENT_ENABLED` | `false` | Opt-in for the background LLM loop (CLAUDE.md §B8: opt-in + hard cap + kill-switch). Read directly from env by `agent/autonomous_budget.py`. |
| `AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY` | `20` | Hard daily cap for the background loop. Read directly from env by `agent/autonomous_budget.py:32` — **independent of cost_tracker** (the old guide's claim that cost_tracker "enables" this cap was wrong). |
| `SCHEDULER_ENABLED` | `true` | In-process background scheduler. Set `false` for local smoke tests. |
| `SCHEDULER_ENABLE_AUTONOMOUS_TASKS` | `false` | Legacy autonomous learn/discovery jobs. Keep `false` (CLAUDE.md §B8). |
| `BUILD_SEARCH_INDEXES` | `true` | Build BM25/vector indexes at startup. Set `false` for quick local runs. |
| `BACKGROUND_INDEX_BUILD` | `true` | Build indexes in the background instead of blocking readiness. |

---

## Corrections to specific old claims

- **`/metrics` is NOT unauthenticated.** The `gate_internal_endpoints` middleware (`agent/server.py:1066-1086`) requires a valid `X-Admin-Key` header in **all** environments and fail-closes with 404 (`middleware.py` `verify_admin_key`). `curl http://localhost:8360/metrics` without the header returns 404 by design — that is not the module being broken. Any Prometheus scrape config must send the `X-Admin-Key` header; a plain scrape target will stay DOWN forever. The old nginx IP-allowlist advice is not needed for auth (optional defense-in-depth only).
- **`semantic_cache` does NOT need Redis.** It is L1 in-memory LRU + L2 disk JSON (`agent/data/semantic_cache/entries.json`); the module imports no redis. Do not install Redis for it, and `redis-cli FLUSHDB` does not clear it — delete the entries JSON to reset L2.
- **"Do NOT Activate" list is moot.** `self_optimizer`, `dynamic_agents`, `vector_search`, `realtime` all import OK, so they are already running in prod. If any of them must be turned off, that is a code change + review, not an env edit.
- **Rollback via `HAS_X=false` never worked.** During an incident, do not waste time editing `.env` for `HAS_*` — it changes nothing.

---

## Ops procedure (corrected)

```bash
# 1. SSH into VPS — current reality: root with key vinhlong_vps (no "deploy" user exists)
ssh root@66.42.57.202

# 2. Edit env — ONLY the flags in the table above have any effect
nano /opt/vinhlong360/.env

# 3. Restart — systemd unit names: vl-agent (backend), vl-nuxt (frontend), vl-bot (bots)
systemctl restart vl-agent

# 4. Verify health
curl -s http://localhost:8360/health | python3 -m json.tool

# 5. Watch logs
journalctl -u vl-agent -f
```
