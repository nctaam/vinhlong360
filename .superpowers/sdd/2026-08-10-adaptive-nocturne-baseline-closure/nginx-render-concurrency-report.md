# Nginx renderer Windows concurrency repair report

> STATUS: done

Base commit: `57c0d25c8906c13db5216169c7c9509855b7b3b0`

Implementation commit: `fb36f53293bf9ee638fad3cfbafcea354f093d76`

## Root cause

`render_file()` correctly created a unique temporary file, wrote deterministic bytes, flushed and fsynced it, then atomically installed it with `os.replace()`. Two concurrent writers targeting the same destination could reach that final replace together. On Windows, one replace can transiently fail with `PermissionError: [WinError 5] Access is denied` while the other replacement is in flight.

The original code made one replace attempt, so the transient collision escaped even though the temporary file and rendered bytes were valid. An initial retry prototype also used a 100 ms wall-clock deadline. Supporting stress exposed that a delayed worker could consume that deadline without consuming retry attempts. Instrumentation across 10,000 synchronized iterations observed at most two replace attempts, confirming that attempt count, rather than elapsed scheduler time, is the reliable bound for this collision.

## Repair

- Retry only `PermissionError` values whose Windows `winerror` is exactly `5`.
- Limit replacement to five total attempts with four fixed 10 ms waits.
- Re-check destination symlink safety immediately before every replace attempt.
- Reuse the same unique, already flushed and fsynced temporary file across attempts.
- Preserve the existing `finally` cleanup so success, bounded exhaustion, unrelated errors, and symlink rejection leave no unique temporary files.
- Keep persistent access denial visible by re-raising the original exception after the fifth attempt.

This mechanism works across processes because it does not depend on an in-process mutex or shared Python state.

## TDD evidence

### RED 1

Command:

```powershell
python -m pytest tests/launch_safety/test_nginx_contract.py -q -m "" -n0 -k "retries_transient_windows_access_denied or bounds_persistent_windows_access_denied or does_not_retry_unrelated_permission_error or rechecks_destination_symlink_before_replace_retry"
```

Result before production edits: `3 failed, 1 passed, 53 deselected`.

- Transient WinError 5 escaped on the first attempt.
- Persistent WinError 5 made only one attempt.
- A destination symlink introduced after the first collision was not re-checked.
- Unrelated WinError 32 already escaped immediately, as required.

### RED 2

Command:

```powershell
python -m pytest tests/launch_safety/test_nginx_contract.py::test_render_file_retry_budget_is_not_consumed_by_scheduler_delay -q -m "" -n0
```

Result against the initial wall-clock-bounded prototype: `1 failed`. The synthetic scheduler delay exhausted the deadline before a second replace attempt, reproducing the supporting stress failure deterministically.

### GREEN

Commands and results after the final implementation:

```text
python -m pytest tests/launch_safety/test_nginx_contract.py -q -m "" -n0 -k "render_file"
10 passed, 48 deselected

python -m pytest tests/launch_safety/test_nginx_contract.py -q -m "" -n0
58 passed

python -m pytest tests/launch_safety/test_ops_scripts_portability.py -q -m "" -n0
39 passed

git diff --check
exit 0
```

Windows supporting stress used 1,000 synchronized iterations with two `ThreadPoolExecutor` writers, checking exact destination bytes and zero matching temporary files after every iteration:

```text
passed 1000 synchronized two-writer iterations
```

An earlier instrumented 10,000-iteration diagnostic completed successfully with a maximum of two observed replace attempts per unique temporary file. The final five-attempt cap therefore retains measured headroom while remaining finite.

## Files changed

- `scripts/ops/render_nginx_config.py`: added the narrowly classified, attempt-bounded replace retry and per-attempt symlink check.
- `tests/launch_safety/test_nginx_contract.py`: added deterministic transient, persistent, unrelated-error, scheduler-delay, symlink-race, cleanup, and concurrency coverage.

## Self-review from base

Reviewed the complete diff from `57c0d25c8906c13db5216169c7c9509855b7b3b0` after final verification. No unrelated renderer behavior changed. Atomic unique-temp creation, byte-for-byte rendering, flush/fsync-before-replace, source and destination symlink rejection, and cleanup behavior remain intact.

## Concerns

- The retry intentionally does not handle WinError 32 or generic `errno.EACCES`; those remain immediate failures unless a future independently reproduced collision proves another code is transient.
- The five-attempt bound is evidence-based for the reproduced race but deliberately does not hide long-lived ACL, antivirus, or operator ownership failures.
