# Task 3 Fix Report

Status: complete after second-review boundary fixes.

## Findings fixed

- `reportedValueKnown` uses strict boolean validation at both correction transport and shared API schema boundaries; strings and numbers return HTTP 422 before service invocation.
- Discriminator and current-value invariant errors preserve camelCase field paths (`items.0.reportedValueKnown` / `items.0.reportedValue`) and request correlation ids.
- The canonical v1 transport is carried by `X-Correction-Contract-Version`; unsupported versions return `CONTRACT_INVALID`. Headerless callers remain additive-compatible with the legacy default.
- Nuxt keeps the correction draft mounted and renders structured problem detail, field guidance, and `correlation_id` in the page/form.
- `docs/api-contract.md` now documents the discriminator, unknown-current-value semantics, version header, 422 fields, and correlation ids.
- Versioned correction requests now distinguish an omitted `reportedValue` from an explicit `null` using Pydantic's `model_fields_set`; canonical v1 rejects the omitted form with `CONTRACT_INVALID` at `items.N.reportedValue`.
- `CorrectionIntakeContract` requires explicit `reported_value` presence and validates both branches: known values are non-blank strings, unknown values are explicit `null`.
- The Nuxt intake form exposes an accessible current-value-known checkbox, clears the current value when unchecked, emits the explicit discriminator, and anchors discriminator errors to the checkbox.

## TDD evidence

RED (before second-review fixes):

```text
python -m pytest tests/control_plane/test_contracts.py agent/tests/test_case_public_api.py -q --basetemp .tmp-task3-fix-red
3 failed, 54 passed, 6 skipped: schema accepted blank/missing branch values and versioned
reportedValueKnown=false with omitted reportedValue returned HTTP 201.

npm test -- --run tests/correction-case-pages.test.ts -t "lets the reporter explicitly say the current value is unknown|renders a structured server problem"
2 failed: the unknown-value control was absent and reportedValueKnown errors linked to #item-0-reported.
```

GREEN (focused Python):

```text
python -m pytest tests/control_plane/test_contracts.py agent/tests/test_case_public_api.py agent/tests/test_case_wiring.py agent/tests/test_case_domain.py -q --basetemp .tmp-task3-fix-focused
78 passed, 6 skipped, 1 warning
```

GREEN (focused Nuxt):

```text
npm test -- --run tests/proof-first-correction.test.ts tests/correction-case-pages.test.ts tests/correction-case-security.test.ts
3 files passed, 62 tests passed

npm run typecheck
exit 0
```

## Files changed in this follow-up

`agent/api_schemas.py`, `agent/cases/public_api.py`, `agent/tests/test_case_public_api.py`, `tests/control_plane/test_contracts.py`, `web-nuxt/components/cases/CorrectionIntakeForm.vue`, `web-nuxt/tests/correction-case-pages.test.ts`.

The pre-existing `docs/standards/90-exceptions-log.md` user change was not included in this commit.

Follow-up hardening commit: `c84897ab` adds strict registry validation for the
known-current string and covers missing-value/missing-discriminator paths.
Structured error code display is included in `96bb149b`; test typing and the
latest green evidence are in `de356a1b`.
