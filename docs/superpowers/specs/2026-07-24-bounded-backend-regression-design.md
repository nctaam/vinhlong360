> STATUS: active - approved on 2026-07-24; extends Task 45 backend-full-regression execution without changing launch-safety evidence semantics.

# Bounded Backend Regression Design

## 1. Context and goal

The final launch-safety matrix at revision `72872cc2e3abe44d9407ac7e31a3301c3d8c42cc` reached the external two-hour execution bound while `backend-full-regression` was still running. The gate used one unbounded `python -m pytest -q` process. The active installer module has grown to 186 test functions and approximately 291 parametrized cases, with many installer subprocesses and recovery fixtures; the timeout was therefore a runtime-boundary failure, not evidence that the tests passed or failed.

The goal is to preserve the same backend coverage while making the full regression bounded, diagnosable, and materially faster. The release gate must continue to record exactly one `backend-full-regression` section, and a timeout must remain a functional failure that blocks final evidence rendering.

## 2. Decisions

1. Keep the backend regression sequential at the phase level. Phase A runs the complete suite except `tests/launch_safety/test_closed_installer.py` with the existing serial pytest semantics.
2. Run only `tests/launch_safety/test_closed_installer.py` in Phase B with fixed `pytest-xdist` settings: `-n 2 --dist=load --max-worker-restart=0`.
3. Enforce one monotonic global deadline of 7,000 seconds across both phases. The runner must not reset the deadline between phases.
4. On timeout, terminate the complete child process tree, return exit code `124`, and leave enough diagnostic output for the release gate to record a failed section. Never convert a timeout into a skip or pass.
5. Preserve fail-closed phase semantics: Phase B starts only after Phase A passes; a Phase A failure is returned unchanged. A Phase B failure or timeout is returned as the backend section's exit code.
6. Keep the release gate's evidence interface unchanged. The runner is an implementation detail behind the existing `backend-full-regression` command evidence row.
7. Add `pytest-xdist>=3.6,<4` to `requirements-dev.txt`, and install the development requirements in the CI job that exercises the runner contracts. Do not add xdist to `requirements.txt` or the production release package. Do not parallelize the entire backend suite: database, global-state, and resource-sensitive tests remain serial.

## 3. Architecture

Create `scripts/ops/run_backend_regression.py` as a standard-library runner. It resolves the repository root, constructs the two fixed pytest commands, starts each phase with inherited output, and waits against a shared `time.monotonic()` deadline. On POSIX it starts a process group and kills that group on timeout. On Windows it may call `taskkill /PID <pid> /T /F` only while the runner still owns a live `Popen` handle for that exact child; it must use bounded cleanup waits and must not fall back to PID-only cleanup after ownership is lost. Cleanup is best-effort but the timeout exit remains `124` even if a descendant cleanup command reports an error.

The release gate invokes the runner through its selected Python interpreter:

```text
python scripts/ops/run_backend_regression.py --deadline-seconds 7000
```

The runner returns the first failing phase's exit code when Phase A fails, `124` for a deadline breach, and the Phase B exit code otherwise. It emits phase-start, phase-complete, deadline, and cleanup diagnostics without secrets or unbounded captured output.

The installer module is suitable for two workers because its release, persistent-data, runtime, evidence, lock, and private-temp authorities are rooted under pytest-owned, worker-isolated temporary roots. The module-scoped package fixture is built separately beneath each worker's `tmp_path_factory`; individual cases still receive isolated authority roots. Internal concurrency tests remain individual pytest items, so xdist does not alter their intentional intra-test sharing.

## 4. Contracts and verification

Add Python contracts for:

- exact phase command construction and fixed xdist flags;
- one shared deadline rather than one timeout per phase;
- Phase A fail-fast and Phase B execution after a passing Phase A;
- exit-code precedence, including timeout `124`;
- descendant cleanup on Windows and POSIX through injectable process helpers;
- inherited output and repository-root working directory.

Extend the PowerShell release-gate harness to recognize the runner command and prove that a simulated runner exit `124` is recorded as `backend-full-regression=fail` while later evidence sections still execute. Extend the launch-matrix contract to reject a direct monolithic full-suite invocation, require the runner and deadline, and include the new runner contracts in the focused backend and CI contract lists. Test the exact xdist flags against the Python runner's constructed Phase B command.

Run an equivalence check before accepting the optimization:

1. Collect node IDs for the installer module with the serial command and the two-worker command, then compare the normalized sets.
2. Run the installer module serially and with two workers using separate JUnit XML outputs.
3. Compare collected IDs and per-node outcomes; any mismatch blocks adoption and restores serial execution.

Focused contracts must pass before the official matrix. The official matrix then runs the new runner from a clean worktree with an outer command timeout greater than the 7,000-second internal deadline. Docker, browser, deploy, production mutation, secret, and indexing behavior remain unchanged.

## 5. Scope and non-goals

- Modify only the runner, release-gate invocation, test-only dependency and CI installation, related Python/PowerShell contract lists, and the remediation/original-plan/spec references required to describe the bounded execution and its narrow exception to the serial-only rule.
- Do not mark the timed-out matrix as successful and do not render evidence from its partial state.
- Do not exclude installer tests, mark them slow, weaken assertions, reuse temporary roots, or parallelize unrelated backend tests.
- Do not add production runtime services, paid dependencies, deploy steps, or production-data mutations.
