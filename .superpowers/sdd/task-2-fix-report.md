# Task 2 Fix Report — Harden Release Authority Validation

## Outcome

Closed the fail-open gaps identified in the Task 2 review. Authority validation now fails closed when a baseline fragment is missing, when the registry P1 roster drifts from the audit's P1 table, when registry/active-document timestamps are future-dated, or when a caller-supplied HEAD differs from the repository HEAD.

## Files

- Modified `agent/control_plane/authority.py` with GitHub-compatible Markdown heading/anchor resolution, audit P1-section parsing and exact roster parity checks, future timestamp blocking, and repository HEAD identity verification.
- Modified `tests/control_plane/test_authority.py` with mutation tests for bogus/diacritic fragments, audit P1 drift, future timestamps, and mismatched HEAD; fixtures now include explicit P1/P2 classifications.
- Modified `docs/ROADMAP.md` with the canonical `fail-da-biet` HTML anchor required by `config/release-authority.json`.
- Preserved the pre-existing user edits in `docs/standards/90-exceptions-log.md`; that file is not included in this commit.

## Verification

- RED: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest tests/control_plane/test_authority.py -q --tb=short` → 5 new mutation tests failed against the old validator (anchor, P1 parity, future timestamps, and HEAD identity).
- GREEN: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest tests/control_plane/test_authority.py -q` → `10 passed`.
- `python -m py_compile agent/control_plane/authority.py` passed.
- `python scripts/check_release_authority.py --root .` → `PASS tracked=7 stale=0 mismatches=0`.
- `git diff --check` passed.

## Caveats

- P1 parsing intentionally reads the first Markdown heading beginning with `P1` and table rows beneath it; malformed or absent P1 sections block via roster mismatch.
- The validator compares the supplied SHA with local `git rev-parse HEAD`; callers operating on a moving checkout should obtain the SHA immediately before checking.

