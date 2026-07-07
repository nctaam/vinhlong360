> **STATUS (2026-07-07): ARCHIVED — Snapshot QA 2026-06-28 nằm sai chỗ (repo root) — archive 2026-07-07. Một phần "release blocker" đã fix từ lâu (vd /metrics đã gate sau X-Admin-Key). KHÔNG dùng làm danh sách việc hiện hành.**

# QA Scorecard - vinhlong360

Audit date: 2026-06-28

Verdict: **CONDITIONAL PASS**. No confirmed P0 was found, but P1 system-surface and data-integrity fixes should ship before treating the app as production-hardened.

| # | Chiều | Điểm | Findings P0/P1/P2/P3 | Đánh giá |
|---|---:|---:|---|---|
| 1 | Security | 6/10 | 0/4/9/3 | Auth on core UGC is strong; internal/system endpoints need route-level guards. |
| 2 | Input Validation | 7/10 | 0/0/3/0 | Pydantic coverage is good; pagination lower bounds are missing. |
| 3 | Error Handling | 6/10 | 0/0/3/1 | Graceful fallbacks exist, but retry/observability is uneven. |
| 4 | Business Logic | 7/10 | 0/1/3/0 | No payment/booking flow found; comment parent integrity and reputation gaming remain. |
| 5 | Edge Cases | 6/10 | 0/0/2/0 | Thread pagination and race/regression tests need stronger coverage. |
| 6 | Performance | 5/10 | 0/2/5/0 | Several public endpoints fetch very broad datasets before trimming. |
| 7 | Data Integrity | 6/10 | 0/1/3/0 | UGC cascades mostly good; entity/relationship boundaries can orphan. |
| 8 | API Contract | 6/10 | 0/0/2/0 | Response/error envelopes and list contracts are inconsistent. |
| 9 | Accessibility | 7/10 | 0/0/3/1 | `lang`, skip links, focus work exist; nested interactive widgets need fixes. |
| 10 | Code Quality | 6/10 | 0/0/1/4 | Large files and loose tests slow safe review. |
| 11 | Deployment | 5/10 | 0/2/5/1 | Non-root Dockerfile and backups are good; published ports and defaults need hardening. |
| 12 | Background Tasks | 6/10 | 0/0/3/1 | Autonomous LLM gating is good; non-autonomous task isolation/retry is weak. |
| **Tổng** | | **6.1/10** | **0/10/42/10** | **CONDITIONAL PASS** |

## Standards Mapping

| Standard | Status | Notes |
|---|---|---|
| OWASP ASVS L2 | Partial | Core auth/session paths show serious hardening, but system endpoints and public diagnostics are not L2-clean. |
| OWASP Top 10 2021/2024 themes | Partial | Main risks: Broken Access Control, Security Misconfiguration, Insecure Design, Vulnerable Components. |
| WCAG 2.2 AA | Partial | Landmarks/skip links exist; ARIA listbox/dialog/picker issues remain. |
| Dependency hygiene | Partial | `pip-audit` clean; `npm audit` has one low `esbuild` advisory. |

## Top Release-Blocker Fixes

No confirmed P0 was found. Treat these P1 items as the immediate release blockers:

| Priority | Fix | Timeline |
|---|---|---|
| 1 | Add per-route `require_internal_admin` to all `/system`, `/analytics`, `/metrics`, judge/cache/guardrail endpoints. | 1 day |
| 2 | Protect checkpoint/confirmation endpoints with signed session ownership or remove them from public routing. | 1 day |
| 3 | Split `/health` into public liveness and authenticated internal diagnostics. | 0.5 day |
| 4 | Validate `parent_id` belongs to the same post before inserting a reply. | 0.5 day |
| 5 | Restrict Docker/Nginx exposure for DB/cache/monitoring/system paths. | 1 day |

## Verification Performed

| Check | Result |
|---|---|
| `python -m pip_audit -r requirements.txt --format json` | No known Python vulnerabilities found. |
| `npm audit --omit=dev --json` in `web-nuxt` | 1 low `esbuild` advisory, fix available. |
| `python -m pytest --collect-only -q` | `3050/3118` tests collected, `68` deselected, 1 Starlette deprecation warning. |
| Booking/payment scan | No on-site booking/payment/cart/checkout endpoint found in runtime app code; content lint still needed. |
