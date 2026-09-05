# Proof-First Optimization Progress

Plan: `docs/superpowers/plans/2026-08-31-proof-first-optimization-plan.md`
Started: 2026-08-31

Task 1: complete (commits 87dc013a..b1fe1619, review clean; 137 focused tests passed)
Task 2: complete (commits b1fe1619..7a926517, review clean; 13 authority tests passed)
Task 3: complete (commits 6375bbb7..417f654f, review clean; final focused Python 95 passed/13 skipped, Nuxt 62 passed, typecheck passed)
Task 4: complete (commits 417f654f..71a6a195, review clean; final controller 264 passed/96 skipped, disposable PostgreSQL 80 passed/schema 82/drop verified)
Task 5: complete (commits 71a6a195..6e9f28f2, review clean; focused lifecycle/account 19 passed, frontend lifecycle/settings/chat 46 passed, disposable PostgreSQL schema 82 lifecycle/erasure 27 passed and database-after-drop None)
Task 6: complete (commits a88464f3..dee72e5f, review clean; schema/publication fixes approved, focused 28 passed, disposable PostgreSQL schema 83/generation/teardown verified)
Task 7: complete (commits 1b4eebbd..017e175b, review clean; focused 434 passed/8 skipped/1 xfailed, migration gates 24 passed, disposable PostgreSQL schema 84/CAS/lease/teardown verified)
Task 8: complete (commits 33f7ca76..d4e9b320, independent review clean; focused mutation/search/media suites passed, disposable PostgreSQL mutation/compensation evidence verified)
Task 9: complete (commits 59b704f0..9e273c40, independent review clean; cross-worker generation/cache consistency and invalidation suites passed)
Task 10: complete (implementation/remediation complete; focused hardening and launch/config/source-scan reviews green; legacy broad source-contract failures remain outside Task 10 surface)
Task 11: complete (implementation + second review remediation; 148 focused tests passed/1 skipped, package suite 49 passed/3 skipped, compileall/Ruff/diff-check green; PostgreSQL/Docker runtime evidence unavailable on this host)
Task 12: complete (implementation + remediation; final independent review clean; PostgreSQL rerun 256 passed/3 skipped)
Task 13: complete (scanner/registry/legal CMS remediation; 42 focused design+ratchet tests passed, scanner semantic/z-index debt 0, production CLI PASS; CMS sections now require canonical count/order/headings and claim-bearing Unicode variants fail closed)
Task 14: complete (structural evidence/receipt hardening; ops/evidence 72 passed, py_compile/Ruff green, acceptance exit 2 NO_GO, release verifier exit 2 BLOCKED; residual P1: execution receipt is unsigned and cannot attest that captured commands actually ran)
Task 15: complete (commits af14df9d..05b77b99, review clean after removing stale source-test comment contracts; shared JSONL report writer and focused boundary tests verified)

PostgreSQL integration follow-up (2026-09-02): disposable PostgreSQL 16 runtime at 127.0.0.1:55432, schema version 86 and catalog readiness `ok=True`; migration/schema suites 29 passed, full `*postgres.py` suites 94 passed/30 skipped, correction-case race/idempotency/HTTP contract regressions remediated and re-run green. Evidence is local disposable only; it does not establish production-equivalent HA, backup/restore, browser, multiprocess deployment, provider, residency, or legal sign-off.

## 2026-09-02 (dot dong gate) — honest status, khong xoa do cu

Cac dong tren la ghi nhan lich su, giu nguyen. Khoi nay bo sung va superseded moi
cach doc "Task 14: complete" nhu la "gate da dat".

- **Lo hong bundle bia dat (da dong).** Truoc dot nay mot bundle 100% bia dat van
  ra `GO_CONDITIONAL`/`PASS`: moi digest trong bundle la ham keyless cua chinh
  van ban tac gia go, nen ai giu checkout cung tinh lai duoc ca chuoi
  (`agent/control_plane/attestation.py:1-28`). Ba lop da dong:
  (a) gate parse lai `captured_output` ngay luc cham diem thay vi tin truong
  verdict co san — `_captured_output_supports_outcome()`
  (`scripts/ops/run_pilot_acceptance.py:138-186`, dung o `:734-743`);
  (b) bat buoc du bon vai ky `("runner", "owner", "countersign", "ci")`
  (`agent/control_plane/attestation.py:46`), khong vai nao duoc dung chung key_id
  (`:257-269`), va `owner`/`ci` phai co custody doc lap (`:270-278`);
  (c) mot countersigner tai-thuc-thi doc lap
  (`scripts/ops/countersign_pilot_acceptance.py`) chay lai chinh nodeids ma ban
  ghi khai — khong bao gio chay lai chuoi lenh ghi trong bundle (`:11-16`).
- **Bang chung PostgreSQL that: 3/28 P1.** Chi `F-42`, `F-49`, `F-53` co lop
  postgres chay that tren PostgreSQL disposable, qua
  `agent/tests/test_case_contention_postgres.py` (anh xa o
  `scripts/ops/run_pilot_acceptance.py:381-396`). **25 P1 con lai mang gap co
  ten**, khong phai pass. DSN chi den tu bien moi truong
  `VL360_TEST_DATABASE_URL` va bi ep loopback-only
  (`scripts/ops/run_pilot_acceptance.py:935-955`).
- **Countersigner: 3/3 confirmed, nhung UNSIGNED.** `artifacts/pilot-countersignature.json`
  ghi `complete=true`, `confirmed=3`, `expected=3`,
  `covers=["F-42/postgres","F-49/postgres","F-53/postgres"]`, bundle
  `pilot-acceptance-20260902T104323Z`, HEAD `7bd85e77`. Attestation cua no la
  `scheme="unsigned"`, `signature=""` vi key `PILOT_ATTEST_COUNTERSIGN_KEY`
  **co y vang mat** (quyet dinh cua chu du an trong phien nay). Vi vay
  `countersign_pilot_acceptance.py` tra exit 2 (`:193`).
- **Chua co bang chung cho:** browser/proxy E2E, contention da-tien-trinh/da-node,
  HA/failover, backup -> offsite -> restore -> checksum, staging rollout -> smoke ->
  rollback, alert receiver that, provider/object sandbox retry. Nhung viec nay
  **khong lam duoc tren mot laptop don le** — ghi la unavailable, khong duoc thay
  bang receipt tong hop.
- **Trang thai cong:** pilot acceptance gate = **NO_GO**; release verifier =
  **BLOCKED**. Day la ket qua DUNG va phai giu nguyen cho toi khi co quyet dinh
  cua chu du an. Khong task nao trong danh sach tren duoc doc la "da du bang
  chung de mo pilot".
- **Luu y ton tai:** `scripts/ops/run_pilot_acceptance.py`,
  `artifacts/pilot-acceptance.json` va `docs/runbooks/proof-first-pilot-acceptance.md`
  hien **UNTRACKED tai HEAD**; khoi `pilot_acceptance` trong
  `config/release-authority.json` la diff chua commit. Chua co gi trong so nay
  duoc CI giu.

Contract foundation follow-up (2026-09-03): OpenAPI export, shared schemas, governance docs, frontend endpoint inventory, and CI drift gate are complete. Contract suite `13 passed`; full backend `8761 passed, 772 skipped, 68 deselected, 1 xfailed`; frontend `2201 passed`, typecheck green; Ruff, compileall, contract drift, drill-index validation, and diff-check green. Verifier remains intentionally `BLOCKED` (CLI exit `2`) and authority remains `STALE` until human sign-off, tracked decision records, custody keys, and production-grade runtime evidence exist.

P1 review remediation (2026-09-04): frontend inventory expanded to 216 endpoint families with reverse source scanning and corrected anonymous pre-case contact auth; acceptance/verifier/countersigner now honor explicit `--root`; PostgreSQL proof requires both a loopback DSN and an exact disposable marker. Fresh verification: contract suite `15 passed`, acceptance/attestation/countersigner `140 passed`, verifier `22 passed`, full backend unchanged at `8761 passed`, frontend `2201 passed`, and release verifier remains `BLOCKED` with exit `2`.

Second P1/P2 remediation (2026-09-04): inventory expanded to 227 endpoint families, user-owned route auth metadata corrected to `session`, nested TypeScript generic calls are now scanned, relative bundle paths resolve beneath `--root`, successful pytest nodeids are retained, and countersignature `results` must exactly cover `expected`. Focused verification: contracts `17 passed`, receipt/verifier/evidence `71 passed`, attestation `35 passed`; full backend/frontend remain green from the immediately preceding regression run.

Case status contract follow-up (2026-09-04): `GET /api/cases/status` now has a
strict `CaseStatusResponse` with the 11 required camelCase fields consumed by
Nuxt, enum/nullable/revision constraints, and no undocumented top-level fields,
instead of an OpenAPI `{}` response schema. RED reproduced the missing reference
and the permissive extra-field policy; GREEN export/contract coverage passed `17`,
with Ruff, compileall, `git diff --check`, and `run_hard.py --all` clean. The
route still returns its existing `JSONResponse`, but now validates the shaped
payload through `CaseStatusResponse` before serialization so internal contract
drift fails closed. RED reproduced the previous bypass; GREEN passed the focused
runtime regression and preserved the valid HTTP journey.

## Backend Completion Closure (2026-09-05)

Task 0: complete (commits `05ed0999..85f30a1e`, review approved; focused authority/release + alternate-root acceptance `32 passed`; authority `PASS tracked=8 stale=0 mismatches=0`; hard gate clean; default pytest temp root remains blocked by Windows `WinError 5`, so workspace basetemp was used; static `closed_pilot_verdict=GO_CONDITIONAL` preserved for acceptance contract while evaluated pilot remains `NO_GO`, verifier remains `BLOCKED`).
