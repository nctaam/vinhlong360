# SDD ledger — plan: docs/superpowers/plans/2026-09-05-backend-completion-closure.md

## Truth-sync 2026-09-11T16:13:28Z

- Release HEAD: `c207060d3731eae879906130222c7af1f1b29579` on `codex/correction-case-pilot`.
- Local archive: `E:\vl360-release-artifacts-20260911\dist\vl360-launch-release-c207060d.tar.gz`.
- Archive SHA-256: `65034406c012f1e282b3a62722ee4b24f9490a1570725052462758250285e6b4`.
- Closed archive verifier: PASS locally and PASS on VPS `66.42.57.202` after digest check; VPS staging files were removed after verification.
- Fresh acceptance bundle: `E:\vl360-release-artifacts-20260911\pilot-acceptance-c207060d.json`, gate `NO_GO`, 28 P1 sections and all five declared layers recorded against this HEAD.
- Fresh release-bundle verifier: `BLOCKED` for the expected reasons: acceptance `NO_GO`, missing countersignature artifact, and unsigned legal/provider/residency/public-indexing decisions.
- Quality evidence: `run_hard.py --all` hard=0; package/rollback verifier `131 passed, 4 skipped`; installer regression `6 passed`; Nuxt Vitest `185 files, 2597 tests passed`; typecheck and build exit 0.
- VPS read-only evidence: `vl-agent`, `vl-nuxt`, `vl-bot`, `nginx`, and PostgreSQL active; root filesystem 71% used; `/` and `/api/homepage` returned HTTP 200.
- Docker Compose audit remains unavailable because the VPS/local Compose runtime is not available; prior audit was reused only after all four source digests matched.
- Release remains BLOCKED/NO_GO: owner signing key, countersignature key, signed decision records, and current owner/countersigner attestations are absent. No installer run, restart, traffic change, migration, or production data mutation was performed.

## Archive refresh 2026-09-11T16:30:35Z

- Candidate source revision: `2bd4979edac5973f31f49076983c962a53494f37` (runtime/docs release commit; the following ledger-only commit does not change packaged runtime members).
- Nuxt build was rerun and generated `launch-readiness-manifest` for the candidate revision.
- Candidate archive: `E:\vl360-release-artifacts-20260911\dist\vl360-launch-release-2bd4979e.tar.gz`.
- Candidate archive SHA-256: `c8ebad369f894df9ef09c64b122aa4033f79f812b1331e33af0a9eb32119adf0`.
- Candidate archive `verify_closed_release.py --require-closed`: PASS locally and PASS on VPS after SHA-256 sidecar verification; VPS staging files were removed after verification.

## Preflight

- BASE: `0d537202c381ec75c863612b03ae25d7b1832af0`
- Branch: `codex/correction-case-pilot`
- Remote: `origin/codex/correction-case-pilot`
- Working tree contains unrelated frontend/contract edits and generated artifacts; implementers must stage only task-owned paths.
- Task 0 is the first incomplete task; Tasks 7–8 are already marked complete in the plan but the release decision remains NO_GO/BLOCKED.

## Plan scan

| Item | Shared surface / concern | Finding | Ruling |
|---|---|---|---|
| Task 0 -> Task 1 | `config/release-authority.json`, `docs/HANDOFF.md`, report authority | Task 0 must freeze provenance before Task 1 changes report ownership. | Execute Task 0 first; do not treat stale authority as release evidence. |
| Task 1 -> Task 6 | reports, lifecycle registry, erasure/export | Task 6 consumes the canonical report sink created by Task 1. | Task 1 must land before Task 6. |
| Task 2 -> Task 7 | scheduler lease and multiprocess probe | Task 7 requires a shared scheduler claim to produce meaningful evidence. | Keep Task 7 evidence fail-closed until Task 2 is complete. |
| Task 3 -> Task 7 | provider receipts and provider sandbox probe | Local fake-provider evidence cannot prove production delivery. | Preserve ambiguous state and NO_GO without staging/provider custody. |
| Task 4 -> Task 7 | image suggestion unique constraint | The race probe depends on a durable pending uniqueness invariant. | Require PostgreSQL evidence before closing the race. |
| Task 5 | module boundary and singleton topology | Refactor must preserve route identity and singleton ownership. | Require boundary and route regression tests in the same task. |
| Task 0 self-consistency | stale snapshot and untracked artifact tests | Tests named in the plan match the authority/reporting interfaces; generated artifacts must remain outside release bundles. | Implement RED/GREEN without deleting untracked artifacts. |
| Global constraints | production deploy/secrets/data | Plan explicitly forbids production mutation and deploy. | No production deploy; only local commits and explicitly requested branch pushes. |

## Rulings

- Ruling: Treat `agent/.pytest-task15-review-green/` and `outputs/` as unclassified generated artifacts, not release evidence — deleting or packaging them without ownership proof could destroy evidence or leak generated data.
- Ruling: Keep the branch's existing frontend dirty files untouched — they belong to the parallel frontend stream and are outside Task 0's scope; staging them would make the task non-attributable.
- Ruling: Treat the plan's unchecked Task 1–6 boxes as stale bookkeeping, not proof that the work is absent — HEAD already contains their implementation commits through `ec2b85f3`; Task 0 must make the authority/plan provenance explicit before any further task dispatch.

## Baseline evidence

- `git rev-parse HEAD`: `0d537202c381ec75c863612b03ae25d7b1832af0`
- `git branch --show-current`: `codex/correction-case-pilot`
- `python scripts/check_release_authority.py --root .`: `STALE tracked=8 stale=7 mismatches=0`; expired: `config/release-authority.json`, `CLAUDE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/README.md`, `docs/standards/00-INDEX.md`, `docs/audit-toan-du-an-2026-08.md`.

- Task 0: complete (commit `f4b91694`, review clean; SPEC PASS, QUALITY PASS; 32 focused tests passed; policy-approved R30.7 skip leaves release debt documented).

- Acceptance digest regression: complete (commit `ddad8165`, review clean; RED reproduced nested pytest worktree marker collapsing `_working_tree_digest()` to `unknown`; GREEN `96 passed` for `tests/integration/test_cross_boundary_proof.py`, five previously failing gate tests `5 passed`; acceptance rerun unit layer `100 passed`, final artifact remains `NO_GO` because external evidence/signoffs are absent).
