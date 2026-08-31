# Task 3 Report — FE/BE contract registry and correction error contract

Status: complete (focused verification green)

## Changes

- Added versioned, frozen contract registry and RFC 9457-style `problem_detail` in `agent/control_plane/contracts.py`.
- Added explicit `reported_value_known`/`reported_value` discriminator validation, including unknown-current-value support through the case service and transport model.
- Mapped correction request validation to HTTP 422 problem details with `field`, `correlation_id`, and compatibility `request_id`.
- Added canonical `normalize_curation_summary()` and changed admin provisional badge/alert reads to `provisional_count`; legacy `pending` is not accepted.
- Updated Nuxt correction types, composable error handling, and intake form to send the discriminator and preserve draft state on 422.
- Added focused Python and Vitest contract tests.

## TDD evidence

RED command:

```text
python -m pytest tests/control_plane/test_contracts.py agent/tests/test_case_wiring.py -q
```

Initial result: 4 contract tests failed with `ModuleNotFoundError`/missing `normalize_curation_summary`; the wiring tests also hit the repository's Windows temp permission error (`WinError 5`) before fixture setup.

GREEN commands and outputs:

```text
python -m pytest tests/control_plane/test_contracts.py agent/tests/test_case_wiring.py agent/tests/test_case_domain.py -q --basetemp .tmp-task3-pytest
25 passed in 4.26s

python -m pytest agent/tests/test_case_public_api.py agent/tests/test_case_payload_contract.py -q --basetemp .tmp-task3-public-api
44 passed, 13 skipped

cd web-nuxt
npm test -- --run tests/proof-first-correction.test.ts
Test Files 1 passed; Tests 2 passed

npm run typecheck
exited 0
```

## Files

`agent/control_plane/contracts.py`, `agent/api_schemas.py`, `agent/cases/public_api.py`, `agent/cases/service.py`, `agent/kb_curation.py`, `agent/admin.py`, `agent/public_api.py`, `web-nuxt/types/cases.ts`, `web-nuxt/composables/useCorrectionCases.ts`, `web-nuxt/components/cases/CorrectionIntakeForm.vue`, `tests/control_plane/test_contracts.py`, `web-nuxt/tests/proof-first-correction.test.ts`.

## Concerns

- Existing legacy HTTP callers without `reportedValueKnown` remain accepted with the historical known-string default for additive compatibility; new Nuxt submissions send it explicitly.
- The repository's default pytest temp root is ACL-restricted on this machine; focused Python runs use a workspace-local `--basetemp`.
