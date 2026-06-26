# Dead Code Audit -- agent/ backend modules

> Audit date: 2026-06-26
> Branch: `dev/backend-infra`
> Method: grep ALL files in `agent/` for import statements, function-level references,
> and `server.py` route registrations for each target module.
> Per CLAUDE.md B2 (additive-first): NO files deleted. This document is the audit only.

---

## 1. Module-by-module analysis

### 1.1 auto_learn.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `admin.py:1119` (subprocess call), `scheduler.py:188` (subprocess call), `scheduler.py:549` (scheduled task) |
| Referenced in server.py routes? | NO (only indirect via scheduler) |
| Has its own tests? | NO |
| CLI standalone? | YES (`python agent/auto_learn.py`) |
| Mentioned in comments/docs? | YES -- `cleanup_noise.py:3`, `database.py:333`, `self_evolve.py:5`, `self_eval.py:5` |

**Verdict: ACTIVE** -- Used by admin trigger-learn endpoint and scheduler autonomous task (gated by `AUTONOMOUS_TASKS_ENABLED`). Not dead, but only runs when autonomous tasks are enabled (OFF by default per B8).

---

### 1.2 learn_loop.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `server.py:2559,2573,2787`, `scheduler.py:488`, `learn_now.py:52` |
| Referenced in server.py routes? | YES -- `/admin/ai/learning-status` (line 2559), `/admin/ai/trigger-learn` (line 2572), `/api/chat/.../feedback` (line 2787) |
| Has its own tests? | YES -- `tests/test_learn_loop.py` |
| CLI standalone? | YES (`python agent/learn_loop.py`) |

**Verdict: ACTIVE** -- Core learning feedback module, imported by server.py for 3 routes, tested, used by scheduler.

---

### 1.3 learn_now.py

| Check | Result |
|---|---|
| Imported by other modules? | NO -- not imported by any other module |
| Referenced in server.py routes? | NO |
| Has its own tests? | NO |
| CLI standalone? | YES (`python agent/learn_now.py`) |
| Internal imports | Uses `self_evolve.guarded_evolve`, `learn_loop.run_full_cycle`, `discover_province` |

**Verdict: DEAD** -- Pure CLI convenience wrapper. Not imported anywhere. Calls other modules (`learn_loop`, `discover_province`, `self_evolve`) but nothing calls it. Safe to remove.

---

### 1.4 self_eval.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `self_evolve.py:37`, `server.py:2591`, `train.py:109` |
| Referenced in server.py routes? | YES -- `/admin/ai/status` (line 2591, computes fitness) |
| Has its own tests? | YES -- tested via `tests/test_self_evolve.py` (14 references) |
| CLI standalone? | NO |
| Internal imports | Uses `retrieval_eval.run_eval` |

**Verdict: ACTIVE** -- Fitness evaluation module used by self_evolve gate and server status endpoint.

---

### 1.5 self_evolve.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `scheduler.py:197,219,487,508,540`, `server.py:2572,2586`, `learn_now.py:38` |
| Referenced in server.py routes? | YES -- `/admin/ai/trigger-learn` (line 2572), `/admin/ai/status` (line 2586) |
| Has its own tests? | YES -- `tests/test_self_evolve.py` |
| CLI standalone? | NO |
| Internal imports | Uses `self_eval`, `kb_versioning`, `knowledge` |

**Verdict: ACTIVE** -- Safety harness wrapping KB-modifying steps. Core to autonomous learning pipeline.

---

### 1.6 self_optimizer.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `server.py:225` (top-level try/import), `scheduler.py:427` |
| Referenced in server.py routes? | YES -- used in chat pipeline (lines 1404, 1671, 2078), status endpoint (line 2444) |
| Has its own tests? | Not found in tests/ directory |
| CLI standalone? | NO |
| Comment references | `dynamic_agents.py:44`, `orchestrator.py:481,483` |

**Verdict: ACTIVE** -- Prompt/parameter tuning module actively integrated into chat pipeline and server startup.

---

### 1.7 train.py

| Check | Result |
|---|---|
| Imported by other modules? | NO -- only by `tests/test_train.py:12` |
| Referenced in server.py routes? | NO |
| Has its own tests? | YES -- `tests/test_train.py` (currently FAILING: missing `data/train/trainset.json`) |
| CLI standalone? | YES (implied by module structure) |
| Internal imports | Uses `self_eval.compute_fitness` |

**Verdict: DEAD** -- Only referenced by its own tests (which fail due to missing data file). Not imported by any production code. Not called by server.py or scheduler. Safe to remove (along with its test file).

---

### 1.8 eval_framework.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `server.py:219` (top-level try/import), `run_eval.py:30` |
| Referenced in server.py routes? | YES -- status endpoint (line 2443) |
| Has its own tests? | Not found separately, but tested via `run_eval.py` |
| CLI standalone? | YES (docstring shows usage) |

**Verdict: ACTIVE** -- Benchmark evaluation framework imported by server.py. Available as optional capability.

---

### 1.9 run_eval.py

| Check | Result |
|---|---|
| Imported by other modules? | NO -- not imported by any other module |
| Referenced in server.py routes? | NO |
| Has its own tests? | NO |
| CLI standalone? | YES (`python agent/run_eval.py`) |
| Internal imports | Uses `eval_framework` |

**Verdict: DEAD** -- Pure CLI runner for eval_framework benchmarks. Not imported anywhere. Safe to remove.

---

### 1.10 retrieval_eval.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `self_eval.py:87` |
| Referenced in server.py routes? | NO (indirect via self_eval) |
| Has its own tests? | YES -- `tests/test_retrieval_eval.py` |
| CLI standalone? | YES (`python agent/retrieval_eval.py`) |

**Verdict: ACTIVE** -- Used by self_eval.py to compute retrieval fitness score. Has dedicated tests.

---

### 1.11 seed_demos.py

| Check | Result |
|---|---|
| Imported by other modules? | NO -- zero references across entire codebase |
| Referenced in server.py routes? | NO |
| Has its own tests? | NO |
| CLI standalone? | YES (standalone script) |

**Verdict: DEAD** -- Not imported, not referenced, not tested. Pure one-time seed script. Safe to remove.

---

### 1.12 seed_site_settings.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `admin.py:1762` (`from seed_site_settings import DEFAULTS`) |
| Referenced in server.py routes? | NO (indirect via admin.py) |
| Has its own tests? | NO |
| CLI standalone? | YES (`python agent/seed_site_settings.py`) |

**Verdict: ACTIVE** -- Its `DEFAULTS` constant is imported by admin.py for settings reset functionality. Not dead.

---

### 1.13 discover_province.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `learn_now.py:42`, `scheduler.py:509` |
| Referenced in server.py routes? | NO (indirect via scheduler) |
| Has its own tests? | YES -- `tests/test_discover_place.py` |
| CLI standalone? | YES (`python agent/discover_province.py`) |

**Verdict: ACTIVE** -- Used by scheduler for province discovery task (gated by `AUTONOMOUS_TASKS_ENABLED`). Has tests.

---

### 1.14 relationship_discovery.py

| Check | Result |
|---|---|
| Imported by other modules? | YES (indirect) -- `scheduler.py:212` (subprocess call), `scheduler.py:550` (scheduled task) |
| Referenced in server.py routes? | NO (only via scheduler) |
| Has its own tests? | NO |
| CLI standalone? | YES (`python agent/relationship_discovery.py`) |
| Comment references | `self_evolve.py:4,57`, `self_eval.py:5` |

**Verdict: ACTIVE** -- Used by scheduler as subprocess call for relationship discovery (gated by `AUTONOMOUS_TASKS_ENABLED`). Not dead, but only runs when autonomous tasks are enabled.

---

### 1.15 ab_testing.py

| Check | Result |
|---|---|
| Imported by other modules? | YES -- `server.py:145` (top-level try/import) |
| Referenced in server.py routes? | YES -- status endpoint (line 2433), feature flag `HAS_AB_TESTING` (line 260) |
| Has its own tests? | Not found in tests/ directory |
| CLI standalone? | NO |

**Verdict: ACTIVE** -- Imported by server.py as optional capability. Used in status/health endpoint.

---

### 1.16 _check_data.py

| Check | Result |
|---|---|
| Imported by other modules? | NO -- zero references across entire codebase |
| Referenced in server.py routes? | NO |
| Has its own tests? | NO |
| CLI standalone? | YES (standalone diagnostic script) |

**Verdict: DEAD** -- Not imported, not referenced, not tested. One-time data diagnostic script. Safe to remove.

---

## 2. Summary table

| Module | Status | Imported by | server.py route? | Tests? | Recommendation |
|---|---|---|---|---|---|
| `auto_learn.py` | ACTIVE | admin.py, scheduler.py | No (indirect) | No | Keep (scheduler task) |
| `learn_loop.py` | ACTIVE | server.py, scheduler.py, learn_now.py | Yes (3 routes) | Yes | Keep (core) |
| `learn_now.py` | **DEAD** | None | No | No | Safe to remove |
| `self_eval.py` | ACTIVE | self_evolve.py, server.py, train.py | Yes | Yes (via test_self_evolve) | Keep (fitness gate) |
| `self_evolve.py` | ACTIVE | scheduler.py, server.py, learn_now.py | Yes | Yes | Keep (safety harness) |
| `self_optimizer.py` | ACTIVE | server.py, scheduler.py | Yes (chat pipeline) | No | Keep (chat pipeline) |
| `train.py` | **DEAD** | Only tests/test_train.py | No | Yes (FAILING) | Safe to remove |
| `eval_framework.py` | ACTIVE | server.py, run_eval.py | Yes (status) | No | Keep (optional capability) |
| `run_eval.py` | **DEAD** | None | No | No | Safe to remove |
| `retrieval_eval.py` | ACTIVE | self_eval.py | No (indirect) | Yes | Keep (fitness input) |
| `seed_demos.py` | **DEAD** | None | No | No | Safe to remove |
| `seed_site_settings.py` | ACTIVE | admin.py | No (indirect) | No | Keep (admin DEFAULTS) |
| `discover_province.py` | ACTIVE | scheduler.py, learn_now.py | No (indirect) | Yes | Keep (scheduler task) |
| `relationship_discovery.py` | ACTIVE | scheduler.py | No (indirect) | No | Keep (scheduler task) |
| `ab_testing.py` | ACTIVE | server.py | Yes (status) | No | Keep (optional) |
| `_check_data.py` | **DEAD** | None | No | No | Safe to remove |

### Dead modules (5 total, safe to remove):

1. **`learn_now.py`** -- CLI wrapper, calls learn_loop + discover_province + self_evolve but nothing calls it
2. **`train.py`** -- Only referenced by its own failing tests (missing trainset.json). Not used in production
3. **`run_eval.py`** -- CLI wrapper for eval_framework. Not imported anywhere
4. **`seed_demos.py`** -- One-time seed script. Zero references in entire codebase
5. **`_check_data.py`** -- One-time data diagnostic script. Zero references in entire codebase

### Also notable (not in target list but flagged by ke-hoach-hoan-thien):

- **`burn_gpt55.py`** -- CLI-only, NOT imported by any module. **DEAD** (safe to remove)

---

## 3. `except: pass` / `except Exception: pass` patterns (silent error swallowing)

**Total: 181 `except...: pass` patterns across 57 files.**

The worst offenders by count:

| File | Count | Severity | Notes |
|---|---|---|---|
| `server.py` | 46 | HIGH | Chat pipeline, tool calls, guardrails -- errors silently lost |
| `admin.py` | 17 | MEDIUM | Admin operations, data quality checks |
| `learn_loop.py` | 9 | LOW | Autonomous learning (off by default) |
| `scheduler.py` | 8 | MEDIUM | Scheduled tasks silently failing |
| `scripts/research_engine.py` | 8 | LOW | One-time scripts |
| `database.py` | 7 | HIGH | DB schema migrations, column additions |
| `orchestrator.py` | 4 | HIGH | Chat orchestration -- silent failures affect responses |
| `self_evolve.py` | 4 | LOW | Autonomous evolution (off by default) |
| `scripts/mega_research.py` | 4 | LOW | One-time scripts |
| `middleware.py` | 3 | HIGH | Request processing, IP extraction |
| `notifications.py` | 3 | MEDIUM | User notification delivery |
| `public_api.py` | 3 | MEDIUM | Public API responses |
| `retrieval_eval.py` | 3 | LOW | Eval-only |
| `site_settings.py` | 3 | MEDIUM | Settings persistence |
| `vector_search.py` | 3 | MEDIUM | Search index building |

### High-priority `except: pass` locations (production-critical):

These are in hot paths where silent failures can cause user-visible issues:

1. **`server.py`** (46 occurrences) -- Lines include: 315, 419, 462, 808, 912, 921, 1207, 1215, 1231, 1242, 1260, 1270, 1540, 1551, 1565, 1617, 1657, 1679, 1704, 1833, 1843, 1849, 1872, 1878, 1890, 1899, 1906, 1916, 1937, 2016, 2055, 2062, 2075, 2088, 2145, 2188, 2194, 2205, 2222, 2227, 2235, 2242, 2249, 2262, 2274, 2301. Many of these are in the chat pipeline (tool execution, follow-up generation, guardrails) where errors are silently swallowed.

2. **`middleware.py`** (3 occurrences) -- Lines 98, 110, 132. Request middleware silently swallowing errors in IP extraction and request processing.

3. **`orchestrator.py`** (4 occurrences) -- Lines 494, 514, 588, 595. Chat orchestration errors silently lost.

4. **`database.py`** (7 occurrences) -- Lines 130, 298, 299, 394, 435, 980, 1058, 1208. Schema migration `sqlite3.OperationalError` catches (5 of 7) are intentional "column already exists" guards; line 130 and 1208 (`except Exception: pass`) are more concerning.

5. **`autonomous_budget.py`** (1 occurrence) -- Line 62. Budget file write failure silently ignored (documented in comment but still risks budget cap enforcement failure).

### One bare `except:` (worst form):

- **`scripts/audit_full_events.py:46`** -- `except:` with no exception type. Should at minimum be `except Exception:`.

### Recommendation:

Per P2-11 in ke-hoach-hoan-thien-10-tang.md, these should be converted to `logger.warning(...)` calls instead of `pass`. Priority order:
1. `middleware.py` (3) -- request pipeline
2. `orchestrator.py` (4) -- chat quality
3. `server.py` (46) -- bulk, but many in chat pipeline
4. `autonomous_budget.py` (1) -- budget enforcement

---

## 4. Additional dead-code-adjacent findings

### Failing tests (pre-existing):

- `tests/test_train.py::TestTrainset::test_default_trainset_loads` -- FAIL (FileNotFoundError: `data/train/trainset.json`)
- `tests/test_train.py::TestTrainset::test_trainset_covers_categories` -- FAIL (same)

These 2 failures confirm `train.py` is dead code with a broken data dependency.

### Baseline test results:

- 1268 passed, 2 failed, 21 skipped, 68 deselected, 1 xfailed
- The 2 failures are both in `test_train.py` (dead module)
