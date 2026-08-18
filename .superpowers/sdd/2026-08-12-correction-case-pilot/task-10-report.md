# Task 10 Report: Evidence Registry, Risk Decisions, Domain Outcomes, Immutable Change Sets

## Status: PARTIAL — the decision rules landed, persistence did not

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
