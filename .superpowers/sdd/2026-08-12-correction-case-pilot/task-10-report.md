# Task 10 Report: Evidence Registry, Risk Decisions, Domain Outcomes, Immutable Change Sets

## Status: COMPLETE

`agent/cases/correction.py` holds the evidence model, the risk rules, the
decision contract and change-set construction, with 30 tests across the three
files the plan names. What is **not** here is the persistence half of Steps 3
and 4: `add_evidence`, `decide_item` and `build_change_set` do not yet write to
PostgreSQL, and `agent/cases/store.py` is unmodified. That is stated here rather
than implied by a green suite.

## What the rules actually enforce

**A level is a claim about provenance, not a verdict.** `usable_evidence` filters
on scope, expiry and observation time before any level is considered, and a test
asserts that recording E4 accepts nothing by itself. The review gate's "evidence
does not become truth by level alone" is enforced in three separate ways: an
authoritative level still has to be in scope and unexpired; conflicting asserted
values block acceptance outright rather than letting the higher level win; and
for R2/R3 the decision maker must not be the sole author of the supporting
record, so a decision cannot rest only on its own author's filing.

**R2 needs an authoritative source or two genuinely independent ones.** Two
pieces sharing a `source_ref` count as one source, which a test pins directly —
otherwise "two sources" would be satisfiable by citing the same page twice.

**R3 needs a second person**, and a reviewer equal to the maker is refused.

**The terminal set is exactly the locked seven**, and a test asserts no generic
`resolved`, `dismissed` or `da_xu_ly` can appear. A duplicate outcome must name
the case it duplicates.

**`accepted` is an item decision.** `requires_public_change` says a public change
is owed; nothing in this module closes a case or publishes anything, and a test
asserts the module source never mentions an entity writer.

**Change sets are bound to one entity at one revision.** A bundle spanning two
entities, a field outside the approved paths, a repeated field, a no-op, missing
evidence lineage, or a base revision that no longer matches the live entity are
each refused with their own code. Every patch ships with its inverse, so a
rollback needs no recomputation, and `apply_status` starts `pending`.

An honest note on the evidence rule: a decision recorded as
`insufficient_evidence` deliberately does **not** have to clear the R2 bar. The
way out of thin evidence is a truthful outcome, not a stronger claim, and a test
pins that path so the rules cannot push an operator into overstating what they
have.

## Not delivered

- `add_evidence(command) -> EvidenceRecord` and `decide_item(command) -> DecisionOutcome`
  as persisting commands: the validation is written and tested, the inserts are
  not. `CaseTransaction.insert_correction_evidence` already exists from Task 6.
- `build_change_set(...)` writing the change set, item linkage, transition to
  fulfilment, publication work, audit and outbox intent in one transaction.
- The action-scope and active-work-lease precondition, which needs the Task 9
  lease state read inside the same transaction.
- Encrypted evidence payload storage; `encrypt_private_payload` from Task 6 is
  the intended envelope.

Each of those is a persistence layer over rules that are now settled and tested,
which is the safer order: the transaction is easy to write once the predicates
it must enforce are pinned.

## Verification

Plan Step 5 command: `38 passed`. Case regression across work control, public
API, create, service, outbox and database: `343 passed, 1 xfailed`. Ruff clean;
`git diff --check` exit 0. Not independently reviewed.

## Completion: the persistence layer

Everything listed as not delivered above is now written and covered.

**Store.** `CaseTransaction` gained `actor_holds_lease`,
`load_correction_item_payloads`, `entity_revision`, `insert_decision`,
`insert_change_set` and `link_change_set_items`. The payload read is
deliberately separate from `load_correction_items`: the public projection's read
must never select an encrypted value, and keeping one read for each purpose is
what makes that guarantee checkable rather than a convention.

**Action precondition.** Every command requires the caller to be holding a live
work lease on that case, checked inside the same transaction that does the
write. A stranger with the decide scope but no lease is refused
`active_lease_required`, which a test pins. This is the Task 9 lease being load
bearing rather than decorative.

**Evidence.** `add_evidence` stores the payload through
`encrypt_private_payload`, so the content never lands in the clear; the test
asserts the plaintext is absent from `content_enc` and that the author is
recorded as the acting operator, not as free text from the caller.

**Decisions.** `decide_item` validates first and only then opens a transaction,
so a refused decision writes nothing — asserted directly by counting rows after
an R3 decision without a reviewer is rejected. The stored row carries the
outcome, bounded reason, evidence lineage, both refs and the policy revision.

**Change sets.** `build_change_set` reads the item ciphertexts, decrypts them to
build the before/after/inverse patches, re-reads the live entity revision and
refuses `entity_revision_moved` when the entry changed since intake — with a
test asserting no change set row is left behind on that path. On success the
change set, its item linkage, the case's move to fulfilment, the transition, the
publication work item, the audit and the notification intent all commit in one
transaction.

The test that matters most asserts what does **not** happen: after a successful
build, `entities.revision` is still 7. The change set sits at
`apply_status='pending'` with `public_projection_verified_at` null. Accepting
records a debt; paying it is Task 12's decision behind its own kill switch.

## Verification

Plan Step 5 command: `43 passed`. The three suites pass twice in a row, so the
rows they commit do not leak between runs. Case regression across work control,
public API, create, store, service, outbox, contact and database: `397 passed,
1 xfailed`. Ruff clean; `git diff --check` exit 0.
