# Runtime Trust Boundary Result Evidence

> STATUS: complete - Runtime Trust Boundary focused, PostgreSQL, frontend, build, and hard gates pass; the full repository baseline is incomplete under the documented outer timeout and is not reported as passing.
> Revision under test: `fc88f56f7f76520da30c3ee0e434fc18ccf7b6e8`
> Date: 2026-07-29 (Asia/Bangkok)
> Scope: local implementation and verification only; no deploy, push, secret change, production data mutation, scrub activation, or erasure activation.

## Outcome

The Runtime Trust Boundary implementation is functionally verified by its
focused backend, real-PostgreSQL, frontend contract, typecheck, and production
build gates. The repository-wide `python -m pytest -q` baseline did not finish
inside the configured 40-minute outer limit and is not reported as passing.
Its partial progress and exact collection position are recorded below as the
pre-existing closed-installer rehearsal debt allowed by the approved final-gate
plan.

The Verified Erasure Lifecycle plan is not started or authorized by this result.

A post-final-review closure pass additionally proved that provider-generated
tool metadata is sanitized before SSE serialization, exact current-context
verified public contacts survive streaming while unmatched contacts remain
redacted, and the contact page consumes the committed 30-day authority instead
of retaining an independent literal.

## Implementation Commits

| Task | Commits | Result |
| --- | --- | --- |
| Shared policy | `02483709` | Central committed privacy-policy authority and readiness contract. |
| Privacy boundary | `0ec278c8`, `46c9bfd1` | Mandatory input/output and bounded streaming redaction. |
| Chat input boundary | `925171b2` | POST/SSE consumers use safe current/history values before content sinks. |
| Tools and personal sinks | `a6e68e22`, `5665e179` | Tool/contact provenance and sink-side defense. |
| SSE transport | `a9c83e66`, `cc2d1ed5` | Safe-before-wire streaming and hard-gate baseline restoration. |
| Logging/source invariants | `ab3ffaf1`, `90beaada` | Structured log redaction, readiness, and dominance guards. |
| Receipt storage | `06f908ea`, `7b3896f1` | One-time PostgreSQL receipts, aggregate schema, and role ownership. |
| Receipt delivery | `d95c2da7`, `4a963a9b` | POST/cache/fallback/SSE receipt issuance with availability fallback. |
| Telemetry-only endpoint | `472b44db` | Receipt/rating-only feedback, abuse bounds, and no personalization mutation. |
| Final frontend typing | `a0a3a02c` | Explicit SSE privacy-event type used by the final Nuxt typecheck. |
| Post-final review closure | `fc88f56f` | Safe-before-wire tool tracing, verified-contact SSE parity, and contact-page retention authority. |

Branch range: `2cfc0a7b..fc88f56f`.

## Verification Evidence

| Gate | Exact command | Result |
| --- | --- | --- |
| Focused backend with PostgreSQL | `python -m pytest -q agent/tests/test_privacy_policy.py agent/tests/test_privacy_boundary.py agent/tests/test_chat_privacy_transport.py agent/tests/test_privacy_sink_boundary.py agent/tests/test_privacy_logging.py agent/tests/test_privacy_source_guards.py agent/tests/test_feedback_policy.py agent/tests/test_feedback_policy_postgres.py agent/tests/test_feedback_transport.py agent/tests/test_chat_smoke.py agent/tests/test_chat_stream_sse.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_history_continuity.py agent/tests/test_chat_usage_accounting.py tests/test_guardrails.py tests/test_config.py tests/test_integration.py` | Exit `0`; `382 passed`, `53 deselected`, `2 subtests passed`, `1` pre-existing Starlette/httpx deprecation warning in `24.01s`. |
| Frontend contracts | `npx vitest run tests/legal-privacy-retention.test.ts tests/sse-stream.test.ts tests/chat-transport-security.test.ts` | Exit `0`; `3` files and `21` tests passed in `17.86s`. |
| Nuxt typecheck | `npx vue-tsc --noEmit` | Exit `0`; no diagnostics. |
| Nuxt production build | `npm run build` | Exit `0` in `233.9s`; `753` modules transformed; total `6.46 MB` (`1.62 MB` gzip). Existing sourcemap, chunk-size, and Node `DEP0155` warnings are non-blocking. |
| Launch manifest revision | `node scripts/generate-launch-readiness-manifest.mjs` | Exit `0`; manifest regenerated for `fc88f56f7f76520da30c3ee0e434fc18ccf7b6e8`. |
| Diff whitespace | `git diff --check` | Exit `0`. |
| Staged hard gate | `python scripts/checks/run_hard.py --staged` | Exit `0`; `run_hard: sach (hard=0, ratchet khong tang)`. |
| Repository baseline | `python -m pytest -q` | Outer harness exit `124` after `2404s`; incomplete at `2%`, with `215` passes and `1` skip emitted. This is not a pass. |
| Collection position audit | `python -m pytest --collect-only -q` | Exit `0`; `9229/9341` tests collected, `112 deselected`, in `49.50s`. Outcome 216 was `tests/launch_safety/test_closed_installer.py::test_stale_observed_root_topology_is_fsynced_before_recovery_advances[retire-old-root-armed]`; the next active case was `[committed-cleanup]`. |

### PostgreSQL Target Safety

- `TRUST_ERASURE_TEST_DATABASE_URL` was set only for local test processes to
  `postgresql://postgres@127.0.0.1:5432/vinhlong360_trust_erasure_test_20260729_task10`.
- The target is a purpose-named disposable database on loopback. No production
  host, database, role, or data was contacted or mutated.
- PostgreSQL-backed receipt tests ran rather than skipping. The disposable
  database remains available for final review reproduction and has not been
  dropped.

## Acceptance Mapping

| Runtime requirement | Evidence | Commits |
| --- | --- | --- |
| Provider input and history privacy | `test_privacy_boundary.py`, `test_chat_privacy_transport.py`, `test_chat_owner_boundary.py`, and `test_chat_history_continuity.py` cover current/history redaction, owner/session preservation, and boundary-before-provider behavior through ASGI transport. | `0ec278c8`, `46c9bfd1`, `925171b2` |
| Tool, output, cache, and sink privacy | `test_privacy_sink_boundary.py`, `test_chat_privacy_transport.py`, and `test_chat_usage_accounting.py` cover untrusted tools, safe-before-wire tool metadata, verified-contact provenance, old cache values, memory/graph/analytics/optimizer/cost sinks, and safe usage settlement. | `a6e68e22`, `5665e179`, `a9c83e66`, `fc88f56f` |
| Real-transport SSE confidentiality | `test_chat_stream_sse.py` and `test_chat_privacy_transport.py` cover split-chunk PII, cancellation/failure suffix discard, cache/fallback delivery, exact verified public contact parity, and safe terminal/tool events through real ASGI transport. | `46c9bfd1`, `a9c83e66`, `4a963a9b`, `fc88f56f` |
| Log redaction and readiness | `test_privacy_logging.py`, `test_privacy_source_guards.py`, `test_privacy_policy.py`, `test_config.py`, and `test_integration.py` cover final structured-log redaction, mandatory source dominance, exact policy authority, and fail-closed readiness. | `02483709`, `ab3ffaf1`, `90beaada` |
| Receipt issuance availability | `test_feedback_policy.py`, `test_feedback_policy_postgres.py`, `test_chat_smoke.py`, and `test_chat_stream_sse.py` prove one receipt per delivered turn and successful chat when receipt issuance is unavailable. | `06f908ea`, `7b3896f1`, `d95c2da7`, `4a963a9b` |
| Replay, rate limits, and aggregate-only feedback | `test_feedback_policy_postgres.py` and `test_feedback_transport.py` cover transactional one-time consumption, same/conflicting replay, wrong-owner/expired/unavailable behavior, `30/IP/hour`, `20/owner/hour`, separate owner kinds, and bounded rollups with no raw query/reply/entity/session content. | `06f908ea`, `7b3896f1`, `472b44db` |
| No personalization or knowledge mutation | `test_feedback_transport.py` plus the forbidden-call assertions in `test_privacy_source_guards.py` prove the public endpoint accepts only `receipt` and `rating` and cannot call memory feedback, personalization, `learn_loop`, entity-confidence mutation, the knowledge database, or `web/data.json`. | `472b44db` |

## Residuals And Non-Actions

- The full serial repository baseline remains incomplete under the 40-minute
  outer limit because the existing closed-installer rehearsal module dominates
  runtime. Focused Runtime Trust Boundary gates and real PostgreSQL evidence are
  green; the incomplete full run is not relabeled as success.
- Task 9 retains one deferred Minor: an embedded feedback error status remains
  visible after a later successful retry.
- The admin-only `/system/costs/session/{session_id}` compatibility route still
  carries a legacy session label while cost records are intentionally
  owner-scoped. No repository consumer calls it; resolving its API/deprecation
  contract is deferred rather than reintroducing raw session identifiers.
- Existing Nuxt build and Starlette/httpx deprecation warnings remain unchanged.
- No production activation, account erasure, legacy scrub, deploy, push, or
  secret operation occurred.
