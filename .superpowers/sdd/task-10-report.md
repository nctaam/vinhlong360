# Task 10 Report

## Scope

- Added lossy structured event redaction for phone, email, token, and message fields.
- Hardened prompt-injection detection for prompt-leak, Vietnamese unrestricted-role, URL/base64, zero-width, compact, and spaced variants while avoiding the `dan` travel-query false positive.
- Added production configuration fail-closed checks and startup validation, plus production compose requirements for PostgreSQL, explicit HTTPS CORS, and non-default secrets.
- Routed bot, scheduler, learning, and KB-curation logger records through the redaction filter; stable operational context remains visible while interpolated sensitive values are summarized.
- Restricted `/api/stats` to aggregate allowlisted fields and documented auth/scope/CSRF metadata on public and bot routes.

## Verification

- `python -m pytest tests/test_security_control_path.py tests/test_bot_gateway.py -q --basetemp .tmp-task10-pytest` -> 66 passed.
- `python -m pytest tests/test_config.py tests/test_bot_gateway.py tests/test_security_control_path.py -q --basetemp .tmp-task10-pytest` -> 86 passed.
- `python -m pytest tests/launch_safety/test_compose_contract.py -q --basetemp .tmp-task10-pytest` -> 61 passed, 3 skipped.
- `python -m pytest tests/launch_safety/test_launch_matrix_contract.py -q --basetemp .tmp-task10-pytest` -> 22 passed.
- `python -m pytest tests/test_api_surface_contract.py agent/tests/test_response_models.py agent/tests/test_integration_api.py -q --basetemp .tmp-task10-pytest` -> 121 passed.
- `python -m compileall -q` on all Task10 Python modules -> passed.
- `python -m ruff check` on all Task10 Python modules/tests -> passed.

## Concerns

- Full scheduler suites requiring PostgreSQL were not runnable in this environment; targeted launch/config/API checks passed.
- Existing repository test fixtures contain unrelated temporary directories and modified files; they were left untouched.

## Final Remediation (2026-09-02)

- `agent/guardrails.py` now routes `check_input()` through `_check_prompt_injection()`, so URL-decoded, HTML/entity, base64, escaped, zero-width, compact, and spaced variants use the same normalized admission boundary as the public checker.
- `agent/structured_logging.py` now removes raw `LogRecord.exc_info` and `stack_info` before handlers can format them, retaining only exception type, length, and a one-way digest.
- `agent/middleware.py` `ErrorTracker` stores only a bounded endpoint, stable error code, timestamp, and SHA-256 digest; caller exception text and traceback are never retained or logged.
- `agent/llmops/api.py` `/system/errors` applies an allowlist and validates legacy rows, preventing raw `error`/`details`, unsafe codes, malformed digests, query strings, or unexpected stats from reaching the API response.
- `agent/bot_gateway.py` adds `validate_standalone_config()` and invokes it before standalone production startup. Production now fails closed for weak admin/database/Zalo webhook secrets, non-PostgreSQL DSNs, missing credentials, local/non-HTTPS CORS, and mismatched Zalo ID/secret configuration.
- `docker-compose.prod.yml` passes explicit PostgreSQL and admin-key requirements to `bot-gateway`, preventing inheritance of development defaults.

## Final Verification

- `python -m pytest tests/test_task10_hardening.py -q --basetemp .tmp-task10-hardening-final` -> 10 passed.
- `python -m pytest tests/test_security_control_path.py tests/test_bot_gateway.py tests/test_middleware.py tests/test_config.py tests/test_task10_hardening.py -q --basetemp .tmp-task10-focused-final2` -> 125 passed.
- `python -m pytest tests/launch_safety/test_compose_contract.py tests/launch_safety/test_launch_matrix_contract.py -q --basetemp .tmp-task10-launch-final2` -> 84 passed, 3 skipped.
- `python -m compileall -q agent/guardrails.py agent/structured_logging.py agent/middleware.py agent/llmops/api.py agent/bot_gateway.py` -> passed.
- `python -m ruff check agent/guardrails.py agent/structured_logging.py agent/middleware.py agent/llmops/api.py agent/bot_gateway.py tests/test_task10_hardening.py` -> passed.
- Broad `agent/tests/test_security_deep_layers.py agent/tests/test_phase16_coverage.py` remains 406 passed / 9 failed due unrelated legacy source-contract drift; no failing test is in the Task 10 remediation surface.

## Independent Review Remediation (2026-09-02)

### Changed Files

- `agent/guardrails.py`
- `agent/middleware.py`
- `agent/llmops/api.py`
- `agent/config.py`
- `agent/bot_gateway.py`
- `agent/structured_logging.py`
- `tests/test_task10_hardening.py`

### Verification Evidence

- `python -m pytest tests/test_task10_hardening.py -q --basetemp .tmp-task10-review-green2` -> 27 passed.
- `python -m pytest tests/test_security_control_path.py tests/test_bot_gateway.py tests/test_middleware.py tests/test_config.py -q --basetemp .tmp-task10-focused-review` -> 115 passed.
- `python -m pytest tests/test_guardrails.py -q --basetemp .tmp-task10-guardrails-review` -> 97 passed, 2 subtests passed.
- `python -m compileall -q agent/guardrails.py agent/structured_logging.py agent/middleware.py agent/llmops/api.py agent/config.py agent/bot_gateway.py` -> passed.
- `python -m ruff check agent/guardrails.py agent/structured_logging.py agent/middleware.py agent/llmops/api.py agent/config.py agent/bot_gateway.py tests/test_task10_hardening.py` -> All checks passed.

### Root-Cause Fixes

- Prompt decisions now distinguish high-confidence `block`, ambiguous `neutralize`, and benign educational `allow` cases; neutralized input is replaced with a fixed marker before admission.
- Error telemetry projects endpoints and legacy `error_code` values onto fixed allowlists, and derives only lossy digests from legacy raw fields.
- Production CORS validation rejects wildcard, userinfo, path/query/fragment, malformed-port, local, and non-HTTPS origins.
- No-argument log records containing PII, token-shaped values, or injection text are summarized before handlers observe them.
- Production secret validation rejects repeated/predictable values (including all-zero and repeated-cycle canaries) while retaining valid mixed test canaries.

### Concerns

- Error endpoint telemetry intentionally reports `unknown` for routes outside the fixed enum; this is lossy by design and may reduce route-level diagnostics for newly added endpoints until explicitly allowlisted.
- Production CORS remains HTTPS-only, matching the existing production contract; development/test callers may still use HTTP origins outside `assert_production_config`.

## Final Findings Remediation (2026-09-02)

### Changed Files

- `agent/secret_policy.py`
- `agent/config.py`
- `agent/bot_gateway.py`
- `agent/structured_logging.py`
- `agent/guardrails.py`
- `tests/test_task10_hardening.py`

### Verification Evidence

- `python -m pytest tests/test_task10_hardening.py -q --basetemp .tmp-task10-fix-green1` -> 34 passed.
- `python -m pytest tests/test_task10_hardening.py tests/test_security_control_path.py tests/test_bot_gateway.py tests/test_middleware.py tests/test_config.py tests/test_guardrails.py -q --basetemp .tmp-task10-final-findings-focused` -> 246 passed, 2 subtests passed.

### Findings Addressed

- App and standalone bot now import one dependency-free secret policy that rejects repeated cycles of any unit length and low-entropy canaries while accepting the mixed production test canaries.
- Final log-record filtering recognizes JWT/Bearer token shapes and direct, compact, URL-decoded injection text in no-argument literals; safe operational literals remain unchanged.
- Educational mentions of `ignore previous instructions` are allowed across normalized/compact variants, while actual compact injection remains high-confidence blocked.

### Concerns

- The shared policy intentionally rejects secrets with fewer than five distinct symbols or Shannon entropy at/below 2 bits/character; operators rotating unusually constrained but legitimate credentials may need an explicit exception review.

## Final Findings Remediation (2026-09-02, Task 10 remediation fixer)

### Changed Files

- `agent/guardrails.py`
- `agent/bot_gateway.py`
- `tests/test_task10_hardening.py`

### Root-Cause Fixes

- Educational `ignore previous instructions` context is now evaluated against the bounded URL-decoded, normalized, folded, and compact variants rather than only the raw input. The classifier recognizes the supplied explain/define/translate/what-is/what-does/security-risk forms without requiring a second keyword, while a bare `ignorepreviousinstructions` remains a high-confidence block.
- Standalone Zalo validation now uses the same non-empty `ZALO_OA_ACCESS_TOKEN`-first precedence as runtime, falls back to `ZALO_OA_ID`, and fails closed when both the OA credential and webhook secret are missing.

### TDD and Verification Evidence

- `python -m pytest tests/test_task10_hardening.py -q -k "educational_ignore_previous_variants or compact_ignore_previous_injection or access_token_when_oa_id_is_empty or missing_zalo_credentials" --basetemp .tmp-task10-red` -> 9 failed, 1 passed, 34 deselected (expected RED before the fix).
- `python -m pytest tests/test_task10_hardening.py -q -k "educational_ignore_previous_variants or compact_ignore_previous_injection or access_token_when_oa_id_is_empty or missing_zalo_credentials" --basetemp .tmp-task10-green-targeted` -> 10 passed, 34 deselected.
- `python -m pytest -q tests/test_task10_hardening.py` -> 44 passed.
- `python -m pytest -q tests/test_task10_hardening.py tests/test_bot_gateway.py tests/test_guardrails.py` -> 145 passed, 2 subtests passed.
- `python -m py_compile agent/guardrails.py agent/bot_gateway.py tests/test_task10_hardening.py` -> passed.
- `git diff --check` -> passed; Git emitted only existing LF-to-CRLF normalization warnings and no whitespace errors.

## Final Findings Remediation (2026-09-02, Task 10 P1 phone-shape follow-up)

### Changed Files

- `agent/llmops/api.py`
- `tests/test_task10_hardening.py`
- `.superpowers/sdd/task-10-report.md`

### Root-Cause Fix

- `safe_error_timestamp()` now rejects only strongly phone-shaped 9-digit numeric strings (repeated or monotonic digit patterns, plus the existing leading-zero form) before epoch conversion. Ordinary integer/float epochs and valid epoch strings such as `946684800` and `1700000000` remain accepted.

### TDD and Verification Evidence

- `python -m pytest tests/test_task10_hardening.py -q -k "unprefixed_phone_like_epoch_strings" --basetemp .tmp-task10-phone-red2` -> 3 failed (expected RED before the fix).
- `python -m pytest tests/test_task10_hardening.py -q -k "unprefixed_phone_like_epoch_strings or retains_valid_epoch_values" --basetemp .tmp-task10-phone-green` -> 8 passed.
- `python -m pytest tests/test_task10_hardening.py tests/test_bot_gateway.py tests/test_guardrails.py agent/tests/test_llmops_api_boundary.py -q --basetemp .tmp-task10-phone-focused` -> 175 passed, 2 subtests passed.
- `python -m py_compile agent/llmops/api.py tests/test_task10_hardening.py` -> passed.
- `python -m ruff check agent/llmops/api.py tests/test_task10_hardening.py` -> All checks passed.
- `git diff --check` -> passed; Git emitted only existing LF-to-CRLF normalization warnings and no whitespace errors.

### Concerns

- The repository remains a shared dirty worktree with unrelated Task 12/13/14 edits and temporary test directories; those changes were preserved and not included in this remediation.

## Final Findings Remediation (2026-09-02, Task 10 final-review follow-up)

### Changed Files

- `agent/guardrails.py`
- `agent/llmops/api.py`
- `agent/bot_gateway.py`
- `tests/test_task10_hardening.py`

### Root-Cause Fixes

- Educational `ignore previous instructions` admission now uses whole-candidate matching (`fullmatch`) for readable and compact normalized forms, so injection suffixes cannot ride an educational prefix; `check_input()` receives the same blocked decision.
- `/system/errors` now projects legacy timestamps through `safe_error_timestamp()`, retaining finite numeric/ISO-8601 values and replacing malformed or sensitive values with the `unknown` sentinel.
- Runtime and standalone Zalo credential resolution now strip both aliases before applying access-token-first precedence, so whitespace access tokens cannot mask a valid OA ID while missing credentials still fail closed.

### TDD and Verification Evidence

- `python -m pytest tests/test_task10_hardening.py -q -k "educational_ignore_previous_prefix_cannot_allow_injection_suffix or malformed_timestamp_without_echoing_pii or runtime_zalo_resolution_strips_whitespace" --basetemp .tmp-task10-final3-red` -> 4 failed (expected RED before production changes).
- `python -m pytest tests/test_task10_hardening.py -q -k "educational_ignore_previous_prefix_cannot_allow_injection_suffix or malformed_timestamp_without_echoing_pii or runtime_zalo_resolution_strips_whitespace" --basetemp .tmp-task10-final3-green` -> 4 passed.
- `python -m pytest -q tests/test_task10_hardening.py --basetemp .tmp-task10-final3-hardening` -> 48 passed.
- `python -m pytest -q tests/test_bot_gateway.py tests/test_guardrails.py agent/tests/test_llmops_api_boundary.py --basetemp .tmp-task10-final3-relevant` -> 109 passed, 2 subtests passed.
- `python -m py_compile agent/guardrails.py agent/llmops/api.py agent/bot_gateway.py tests/test_task10_hardening.py` -> passed.
- `python -m ruff check agent/guardrails.py agent/llmops/api.py agent/bot_gateway.py tests/test_task10_hardening.py` -> All checks passed.
- `git diff --check` -> passed; Git emitted only existing LF-to-CRLF normalization warnings and no whitespace errors.

### Concerns

- The shared worktree still contains unrelated Task 12/13/14 edits and temporary test directories; these were preserved and not included in this follow-up.

## Final Findings Remediation (2026-09-02, Task 10 final hardening)

### Changed Files

- `agent/guardrails.py`
- `agent/structured_logging.py`
- `agent/llmops/api.py`
- `agent/bot_gateway.py`
- `tests/test_task10_hardening.py`

### Root-Cause Fixes

- The educational `jailbreak` exception now requires a complete normalized question or documented benign phrase. A suffix can no longer inherit an unanchored educational allowlist; it remains an ambiguous neutralization unless another detector pattern requires blocking.
- Final log-record redaction now treats direct `DAN`, `base64(...)`, `eval(...)`, and `exec(...)` literals as untrusted prompt-adjacent text, replacing them with a lossy digest before handlers can render raw content.
- `/system/errors` accepts numeric epoch timestamps only within the 2000-01-01 through 2100-01-01 range. Finite but implausible numeric strings, including phone-like values, become `unknown` rather than being echoed.
- Zalo webhook secrets use the same stripped normalization in module configuration, production validation, and `start_zalo()`, preventing accidental surrounding whitespace from changing signature verification.

### TDD and Verification Evidence

- `python -m pytest tests/test_task10_hardening.py -q -k "jailbreak_educational_allowlist_requires_whole_message or ambiguous_no_args_literals or suspicious_numeric_timestamp or runtime_zalo_secret_strips_whitespace" --basetemp .tmp-task10-final-red` -> 6 failed, 48 deselected (expected RED before production changes).
- `python -m pytest tests/test_task10_hardening.py -q -k "jailbreak_educational_allowlist_requires_whole_message or ambiguous_no_args_literals or suspicious_numeric_timestamp or runtime_zalo_secret_strips_whitespace" --basetemp .tmp-task10-final-green` -> 6 passed, 48 deselected.
- `python -m pytest -q tests/test_task10_hardening.py --basetemp .tmp-task10-final-hardening` -> 54 passed.
- `python -m pytest -q tests/test_task10_hardening.py tests/test_bot_gateway.py tests/test_guardrails.py agent/tests/test_llmops_api_boundary.py --basetemp .tmp-task10-final-focused` -> 163 passed, 2 subtests passed.
- `python -m py_compile agent/guardrails.py agent/structured_logging.py agent/llmops/api.py agent/bot_gateway.py tests/test_task10_hardening.py` -> passed.
- `python -m ruff check agent/guardrails.py agent/structured_logging.py agent/llmops/api.py agent/bot_gateway.py tests/test_task10_hardening.py` -> All checks passed.
- `git diff --check` -> passed; Git emitted only existing LF-to-CRLF normalization warnings and no whitespace errors.

### Concerns

- The accepted numeric timestamp window is intentionally broad enough for retained legacy telemetry while rejecting obvious identifiers; telemetry outside 2000-2100 is represented as `unknown`.
- The shared worktree still contains unrelated Task 12/13/14 edits and temporary test directories; these were preserved and not included in this follow-up.

## Final Findings Remediation (2026-09-02, Task 10 P1 follow-up)

### Changed Files

- `agent/guardrails.py`
- `agent/llmops/api.py`
- `tests/test_task10_hardening.py`
- `.superpowers/sdd/task-10-report.md`

### Root-Cause Fixes

- Educational `jailbreak` admission no longer treats arbitrary words after `in` as benign context. The complete-message matcher now accepts only a finite set of documented security topics and the explicit `what does ... mean` form; unrelated suffix instructions remain `neutralize` and cannot inherit `allow`.
- `safe_error_timestamp()` rejects ten-digit, leading-zero phone-shaped strings before epoch conversion. Valid numeric epochs such as `1700000000` continue to pass through unchanged, while suspicious phone-like values become `unknown`.

### TDD and Verification Evidence

- `python -m pytest tests/test_task10_hardening.py -q -k "unbounded_topic_suffix or phone_like_epoch_strings" --basetemp .tmp-task10-p1-red` -> 4 failed (expected RED before the fixes).
- `python -m pytest tests/test_task10_hardening.py -q -k "unbounded_topic_suffix or phone_like_epoch_strings" --basetemp .tmp-task10-p1-green` -> 4 passed.
- `python -m pytest tests/test_task10_hardening.py tests/test_bot_gateway.py tests/test_guardrails.py agent/tests/test_llmops_api_boundary.py -q --basetemp .tmp-task10-p1-focused` -> 167 passed, 2 subtests passed.
- `python -m py_compile agent/guardrails.py agent/llmops/api.py tests/test_task10_hardening.py` -> passed.
- `python -m ruff check agent/guardrails.py agent/llmops/api.py tests/test_task10_hardening.py` -> All checks passed.
- `git diff --check` -> passed; Git emitted only existing LF-to-CRLF normalization warnings and no whitespace errors.
