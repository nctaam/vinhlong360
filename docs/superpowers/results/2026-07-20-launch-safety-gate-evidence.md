> STATUS: pass
> Revision: c1875b37f643ac6ca06a4db25ccce4902b04d717
> Generated: 2026-07-25T22:07:13+00:00 UTC
> Scope: reproducible local gate evidence only; no live SLA claim.

| Section | Command | Exit | Status | Summary |
| --- | --- | ---: | --- | --- |
| `artifacts` | `pytest launch artifacts and release package` | 0 | pass | passed |
| `backend-focused` | `pytest launch-safety backend focused matrix` | 0 | pass | passed |
| `frontend-focused` | `npm test launch-safety focused matrix` | 0 | pass | passed |
| `postgres-opt-in` | `docker info` | 0 | skip | docker-cli-unavailable |
| `compose-nginx-opt-in` | `docker info` | 0 | skip | docker-cli-unavailable |
| `browser-opt-in` | `npm run smoke:launch-safety` | 0 | pass | controlled Chrome launch-safety smoke |
| `rollback-local-rehearsal` | `C:\Program Files\Git\bin\bash.exe scripts/ops/rehearse_launch_rollback.sh --local-rehearsal` | 0 | pass | passed |
| `backend-full-regression` | `python scripts/ops/run_backend_regression.py --deadline-seconds 7000` | 0 | pass | passed |
| `frontend-serial-regression` | `npm test -- --no-file-parallelism --maxWorkers=1; npm run typecheck; npm run build` | 0 | pass | passed |
| `source-scans` | `hard checks, quality gates, PowerShell harness, git diff --check` | 0 | pass | passed |
| `known-resource-timeout` | `parallel resource baseline` | 0 | skip | known parallel frontend/backend resource timeout; functional expectations unchanged |
| `external-gates` | `external launch gates` | 0 | skip | H1=blocked; H2=blocked; owner=not-authorized |

External gates: `H1=blocked`, `H2=blocked`, `owner=not-authorized`.
