# Task 7 Report: Public Case API, Status Projection, Receipt Rotation, And ReviewCase

## Status: PARTIAL — transport and projection landed, service adapters not yet

Two of the four moving parts are complete, tested and wired. The service-side
adapters the router calls are **not implemented yet**, so this task is not done.
That is stated plainly here rather than implied by a green suite.

## Delivered

**Public status projection** (`project_public_status` in `agent/cases/service.py`,
commit `67fc42b0`). Backstage vocabulary stops at the boundary: phase, activity
and publication state select a line from a fixed catalog, so a reporter sees
received / checking / deciding / updating / closed and never triage,
investigation or fulfilment. The case id, internal owner, severity, risk class,
evidence level and any operator note are absent from the projection entirely. An
accepted decision stays separate from whether the change is publicly visible.
Only the update clock carries the public promise; the resolution clock is
measured internally and never published, matching the policy that keeps
`public_resolution_sla_enabled` false.

**Transport** (`agent/cases/public_api.py`). All eight routes exist:
`POST /corrections`, `POST /access`, `GET /status`, `POST /receipts/rotate`,
`DELETE /access`, `POST /review`, `POST /contact/request`,
`POST /contact/verify`. The router owns transport concerns only — flag gating,
origin and content type, the double-submit CSRF check, cookie policy, cache
headers and RFC 9457 problem details.

Behaviour pinned by tests: every route answers `404 capability_unavailable`
while `CASE_KERNEL_ENABLED` is off, and intake alone disappears when
`CORRECTION_INTAKE_ENABLED` is off; create returns 201 with `Cache-Control:
no-store`, the reference and the one-time capability, and never puts the
capability in a header; create rejects a foreign Origin, a cross-site
`Sec-Fetch-Site`, a non-JSON content type, an unknown JSON field, and a missing
`Idempotency-Key`; access sets an `HttpOnly`, path-scoped, 900-second access
cookie plus a readable CSRF cookie; status requires the access cookie and
serialises only the ten locked fields in camelCase; logout clears both cookies;
and every cookie-authenticated mutation refuses a missing or mismatched
`X-Case-CSRF` and a foreign Origin.

**Server wiring** (`agent/server.py`). The router mounts after `public_router`,
`Idempotency-Key` and `X-Case-CSRF` join the CORS allow-list, and `/api/cases`
joins the no-store cache classification. Mounting is inert: with the flags at
their default false every route answers 404, so this changes nothing at runtime
until rollout is explicit.

## Not delivered, and what it needs

The router calls a service surface that does not exist yet:
`create_correction_from_transport`, `exchange_receipt`, `public_status`,
`rotate_receipt`, `open_review`, `revoke_access`. The transport tests drive a
service double, so they prove the contract and not the wiring to real data.

Remaining work, roughly in order:

1. Adapters translating the transport models into `CreateCorrectionCommand` and
   the Task 5 receipt/access operations, including mapping `CorrectionRejected`,
   `SafetyRoutingRequired` and `IdempotencyConflict` onto problem details.
2. Store reads for `public_status`: load the case, its correction items and its
   review links from an access session, then feed `project_public_status`.
3. `open_review`: require a closed case, a reason and the expected terminal
   revision, then create a linked `service_kind=correction`, `category=review`,
   `review_of_case_id=<closed>` case with its own receipt, work item and audit,
   never reopening the original.
4. Per-route rate limits for access exchange, review and rotation, reusing
   `check_case_rate_limit` with the buckets already named in
   `agent/cases/rate_limit.py`.
5. Contact request/verify currently answer `503
   contact_verification_unavailable` after enforcing the full transport
   contract; the verification itself is Task 8.

## Verification

`python -m pytest -q agent/tests/test_case_public_api.py agent/tests/test_case_public_projection.py agent/tests/test_case_access_security.py agent/tests/test_server_models.py agent/tests/test_policy_http.py`

Result: `94 passed`. Case regression across service, create, idempotency, store,
rate limit, receipts and the source guard: `136 passed`. Ruff clean on
`agent/cases/`, both new test files and `agent/server.py`.

## A landmine the hard gate caught: a second module named its router `router`

The first attempt to commit the wiring was blocked by R20.9
(`policy_http_registry`) with a violation that looked unrelated to the change:
`GET /api/entities/{entity_id} route is not mounted`, pointing at
`agent/public_api.py`, a file this branch has never touched.

It was measured rather than guessed. A temporary detached worktree at the
previous commit reported **0** violations for the same check, so the regression
was definitely introduced by the `server.py` edit. Dumping the resolver state
showed why: `public_api.router` had lost its mount prefixes entirely while the
new router had gained them. The standards checker resolves an imported router
alias by the original **symbol name**, so once a second module also exported a
symbol called `router`, the import became ambiguous and the older router was
silently treated as unmounted.

FastAPI itself was never wrong — the runtime app mounts all 52 routes from
`agent/public_api.py` plus the eight new ones — but the static contract checker
could no longer prove it, which is exactly the kind of silent divergence the
rule exists to catch.

The router is therefore exported as `case_public_router`, not `router`. Any
future module under `agent/` should do the same: naming a second router `router`
does not fail loudly, it quietly unmounts somebody else's routes in the eyes of
the standards layer.

R20.5 (`api_contract`) also blocked the commit until the eight routes were
described in `docs/api-contract.md`; that section now documents the gating, the
credential rules, the cookie policy, the exact accepted request fields and the
ten public status fields.

Final gates: plan Step 5 command `97 passed`; case regression `136 passed`; Ruff
clean; `git diff --check` exit 0; staged hard gate `hard=0` with no ratchet
increase.
