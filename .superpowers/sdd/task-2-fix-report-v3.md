# Task 2 Fix Report v3 — Scoped Baseline Authority Validation

## Outcome

Closed the remaining Task 2 review gap. Baseline validation now reads only the section selected by `baseline_source#fragment`, ending at the next heading of equal or higher level. Referenced files are decoded through a fail-closed link reader, so missing, unreadable, or invalid-anchor evidence is represented as a `BLOCKED` `AuthorityReport` instead of escaping as an exception.

## Files

- Modified `agent/control_plane/authority.py` with section-scoped baseline extraction and fail-closed link reads for baseline, rule-index, and audit references.
- Preserved the existing regression tests in `tests/control_plane/test_authority.py`, including conflicting outside/inside baseline counts and malformed baseline bytes.
- Removed only the generated Task 2 `R30.7` exception entries from `docs/standards/90-exceptions-log.md`; pre-existing exception entries remain unchanged.

## Verification

- `python -m pytest tests/control_plane/test_authority.py -q --tb=short --basetemp .tmp-task-2-fix-v3b` → `13 passed`.
- `python -m py_compile agent/control_plane/authority.py` → passed.
- `python scripts/check_release_authority.py --root .` → `PASS tracked=7 stale=0 mismatches=0`.
