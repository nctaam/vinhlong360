# Task 3 Fix Report

Status: complete pending second review.

## Findings fixed

- `reportedValueKnown` uses strict boolean validation at both correction transport and shared API schema boundaries; strings and numbers return HTTP 422 before service invocation.
- Discriminator and current-value invariant errors preserve camelCase field paths (`items.0.reportedValueKnown` / `items.0.reportedValue`) and request correlation ids.
- The canonical v1 transport is carried by `X-Correction-Contract-Version`; unsupported versions return `CONTRACT_INVALID`. Headerless callers remain additive-compatible with the legacy default.
- Nuxt keeps the correction draft mounted and renders structured problem detail, field guidance, and `correlation_id` in the page/form.
- `docs/api-contract.md` now documents the discriminator, unknown-current-value semantics, version header, 422 fields, and correlation ids.

## TDD evidence

RED (before fixes):

```text
5 failed: non-boolean values were coerced or accepted; field paths were `items.0`.
```

GREEN (focused Python):

```text
python -m pytest tests/control_plane/test_contracts.py agent/tests/test_case_public_api.py agent/tests/test_case_wiring.py agent/tests/test_case_domain.py -q --basetemp .tmp-task3-final
73 passed, 6 skipped
```

GREEN (focused Nuxt):

```text
npm test -- --run tests/proof-first-correction.test.ts tests/correction-case-pages.test.ts tests/correction-case-security.test.ts
3 files passed, 60 tests passed

npm run typecheck
exit 0
```

The pre-existing `docs/standards/90-exceptions-log.md` user change was not included in this commit.

Follow-up hardening commit: `c84897ab` adds strict registry validation for the
known-current string and covers missing-value/missing-discriminator paths.
