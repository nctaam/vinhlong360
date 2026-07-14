# Entity Published-Status Migration Implementation Plan

> STATUS: proposed; PostgreSQL-only design approved; implementation must not start until this written plan is reviewed; Stage C production apply requires a separate exact-target authorization

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed PostgreSQL-only plan/apply/rollback workflow that annotates reviewed legacy entities with `status = "published"` without changing global `noindex`, weakening Task 9 indexability, or treating local SQLite/JSON as production truth.

**Architecture:** One pure `published-v1` predicate owns migration eligibility and shares the reviewed non-place type allowlist with the Task 9 index policy. Explicit PostgreSQL target helpers, validated custom-format backups, canonical immutable manifests, and a `SERIALIZABLE` transaction with an advisory lock make plan/apply/rollback target-bound, drift-safe, audited, and idempotent. Local SQLite remains a compatibility/test store only; production execution is deliberately separated into owner-authorized stages.

**Tech Stack:** Python 3.14, pytest, PostgreSQL 16, psycopg2, `pg_dump`, `pg_restore`, SQLite compatibility tests, FastAPI backend policy modules, Nuxt 4 noindex source guards, PowerShell/Git on the isolated Windows worktree.

---

## Plan Authority and Execution Rules

- Approved design: `docs/superpowers/specs/2026-07-14-entity-published-status-migration-design.md` at or after commit `89b9540`.
- Execution worktree: `C:\Users\Administrator\.config\superpowers\worktrees\vinhlong360\codex-launch-safety-gate-continuation` on branch `codex/launch-safety-gate-continuation`.
- The unrelated uncommitted `web-nuxt/tests/ai-disclosure.test.ts` change in the original worktree is outside scope and must not be touched or reverted.
- This plan authorizes Stage A engineering only: code, tests, docs, fake targets, and an explicitly disposable PostgreSQL database supplied through `ENTITY_STATUS_TEST_DATABASE_URL`.
- No task may read a production secret, run a production backup, generate a production plan, mutate production/local project data, export over `web/data.json`, deploy, push, merge, or change a real environment.
- The only permitted entity transition in this workflow is `status IS NULL -> status = 'published'`; every existing non-NULL status remains untouched.
- Global `noindex` remains active. Do not edit `NUXT_PUBLIC_SITE_NOINDEX`, activate selective indexing, or treat published-status annotation as launch approval.
- Every numbered task starts with a fresh implementer agent. The implementer records RED, makes the smallest GREEN change, runs focused checks, self-reviews, and commits one coherent change.
- A fresh spec reviewer checks the task against this plan and the approved design. The implementer fixes every Critical or Important finding and requests re-review.
- After spec approval, a separate fresh quality reviewer checks correctness, maintainability, test isolation, and failure modes. The implementer fixes every Critical or Important finding and requests re-review before the next task.
- If implementation changes a cross-task interface below, stop and update this plan before editing outside the active task.

## Locked File Structure

### Shared policy and Task 9 corrections

- Create `agent/public_entity_types.py`: exact reviewed non-place/non-itinerary type allowlist shared by indexing and publication annotation.
- Create `agent/source_policy.py`: pure external HTTP(S) source URL validation shared by R10.8 and publication annotation.
- Create `agent/publication_status.py`: pure `published-v1` predicate, external-source validation, reviewed exclusions, stable reason codes, and input immutability.
- Modify `agent/index_policy.py`: exact type gate, NFC duplicate handling, letter-bearing token count, and stable failure reasons.
- Modify `agent/launch_evidence.py`: NFC/UTF-8 canonical fingerprinting.
- Modify `scripts/checks/check_data_schema.py`: external HTTP(S) source enforcement and structured artifact-load failures.
- Modify `agent/tests/test_index_policy.py`, `tests/checks/test_hard_checks.py`, `agent/tests/test_seo_structured.py`, and `docs/standards/10-data.md`: close the remaining Task 9 review findings.

### Persistence and test isolation

- Modify `agent/tests/conftest.py`: reusable isolated SQLite database fixture.
- Modify `agent/tests/test_admin_mutations.py` and `agent/tests/test_kb_curation.py`: remove shared repository SQLite writes.
- Modify `agent/database.py`: preserve `status` and `verified` in single-row upserts and bulk imports without SQLite `INSERT OR REPLACE` field loss.
- Modify `agent/tests/test_database.py`, `agent/tests/test_admin_mutations.py`, and `tests/test_export_data.py`: exact persistence and round-trip coverage.

### PostgreSQL backup and migration tooling

- Create `scripts/postgres_target.py`: explicit DSN-env resolution, credential-free identity, target/schema fingerprints, canonical JSON, hashes, and atomic exclusive artifact writes.
- Modify `scripts/backup_data.py`: keep local backup compatibility while adding explicit PostgreSQL custom-format backup and validation.
- Create `scripts/migrate_entity_status.py`: canonical plan, transactional apply, drift-safe rollback, audit rows, CLI validation, and immutable reports.
- Create `tests/test_postgres_target.py`, `tests/test_backup_data.py`, and `tests/test_migrate_entity_status.py`: deterministic unit/refusal-path coverage without real data.
- Create `tests/test_migrate_entity_status_postgres.py`: opt-in disposable PostgreSQL transaction, lock, audit, idempotency, and rollback coverage.

### Operations and evidence

- Create `docs/runbooks/entity-published-status-migration.md`: Stage B/C commands, mandatory review evidence, refusal recovery, and rollback procedure.
- Create `tests/test_entity_status_migration_guardrails.py`: explicit PostgreSQL-only and noindex source guards.

## Phase 1: Close Task 9 Quality Findings

### Task 1: Harden the central index policy and hard check

**Files:**
- Create: `agent/public_entity_types.py`
- Create: `agent/source_policy.py`
- Create: `agent/tests/test_source_policy.py`
- Modify: `agent/index_policy.py`
- Modify: `agent/launch_evidence.py`
- Modify: `agent/tests/test_index_policy.py`
- Modify: `scripts/checks/check_data_schema.py`
- Modify: `tests/checks/test_hard_checks.py`
- Modify: `agent/tests/test_seo_structured.py`
- Modify: `docs/standards/10-data.md`

- [ ] **Step 1: Write failing type, Unicode, token, fingerprint, hard-check, and hreflang tests**

Add these cases to `agent/tests/test_index_policy.py`:

```python
import unicodedata

from public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES


@pytest.mark.parametrize("entity_type", [None, "", "itinerary", "unknown", 1, True])
def test_decide_entity_rejects_missing_malformed_and_unreviewed_types(entity_type):
    entity = _public_entity(type=entity_type)
    decision = decide_entity(entity, EVIDENCE)
    assert decision.indexable is False
    assert decision.reasons[0] in {
        "entity-type-missing",
        "entity-type-not-allowlisted",
    }


def test_reviewed_type_allowlist_is_exact_and_excludes_place_and_itinerary():
    assert REVIEWED_NON_PLACE_ENTITY_TYPES == frozenset({
        "accommodation", "attraction", "cafe", "craft_village", "dish",
        "drink", "event", "experience", "facility", "history", "nature",
        "organization", "person", "product", "restaurant",
    })
    assert "place" not in REVIEWED_NON_PLACE_ENTITY_TYPES
    assert "itinerary" not in REVIEWED_NON_PLACE_ENTITY_TYPES


def test_nfc_and_nfd_equivalent_descriptions_are_counted_once():
    summary = _words(65, "Cồn")
    description = unicodedata.normalize("NFD", summary)
    decision = decide_entity(
        _public_entity(summary=summary, description=description), EVIDENCE
    )
    assert decision.reasons == ("description-below-130-words",)


def test_tokens_without_a_unicode_letter_receive_no_word_credit():
    entity = _public_entity(summary=" ".join(["___", "123", "--"] * 100))
    assert decide_entity(entity, EVIDENCE).reasons == (
        "description-below-130-words",
    )


def test_fingerprint_normalizes_semantically_equivalent_unicode_revisions():
    nfc = "policy-cồn-v1"
    nfd = unicodedata.normalize("NFD", nfc)
    common = {
        "route_digest": "1" * 64,
        "disclosure_revision": "ai-disclosure-v1",
        "disclosure_digest": "2" * 64,
    }
    assert build_policy_fingerprint(route_revision=nfc, **common) == (
        build_policy_fingerprint(route_revision=nfd, **common)
    )
```

Create `agent/tests/test_source_policy.py`:

```python
from __future__ import annotations

import pytest

from source_policy import has_external_source_url


@pytest.mark.parametrize(
    "source",
    [
        [],
        [{"title": "Source without URL"}],
        [{"url": "/relative"}],
        [{"url": "http://localhost/source"}],
        [{"url": "http://127.0.0.1/source"}],
        [{"url": "https://vinhlong360.vn/source"}],
        [{"href": "https://www.vinhlong360.vn/source"}],
        "manual",
    ],
)
def test_local_relative_self_and_title_only_sources_fail(source):
    assert has_external_source_url(source) is False


@pytest.mark.parametrize(
    "source",
    [
        "https://example.org/source",
        {"url": "https://example.org/source"},
        [{"href": "http://example.net/source"}],
    ],
)
def test_external_http_source_shapes_pass(source):
    assert has_external_source_url(source) is True
```

Add a structured failure test to `tests/checks/test_hard_checks.py`:

```python
def test_rich_source_reports_policy_artifact_load_failure(tmp_path, monkeypatch):
    from checks.check_data_schema import DataRichSourceCheck
    import launch_evidence

    _mk_data(tmp_path, [{
        "id": "rich",
        "type": "dish",
        "name": "A",
        "status": "published",
        "verified": True,
        "description": RICH_TEXT,
        "source": [{"url": "https://example.org/source"}],
    }])
    monkeypatch.setattr(
        launch_evidence,
        "current_policy_evidence",
        lambda: (_ for _ in ()).throw(ValueError("bad artifact")),
    )

    result = DataRichSourceCheck(root=tmp_path).run()

    assert result["count"] == 1
    assert result["violations"][0]["code"] == "index-policy-artifact-load-failed"


def test_rich_source_rejects_self_local_and_title_only_sources(tmp_path):
    from checks.check_data_schema import DataRichSourceCheck

    _mk_data(tmp_path, [
        {
            "id": "self",
            "type": "dish",
            "name": "A",
            "status": "published",
            "verified": True,
            "description": RICH_TEXT,
            "source": [{"url": "https://vinhlong360.vn/source"}],
        },
        {
            "id": "title-only",
            "type": "dish",
            "name": "B",
            "status": "published",
            "verified": True,
            "description": RICH_TEXT,
            "source": [{"title": "No URL"}],
        },
    ])

    result = DataRichSourceCheck(root=tmp_path).run()

    assert result["count"] == 2
    assert {item["code"] for item in result["violations"]} == {
        "external-source-missing"
    }
```

Replace the stale entity fixture in `agent/tests/test_seo_structured.py::test_sitemap_url_has_hreflang` with:

```python
data = {
    "entities": [{
        "id": "a",
        "name": "A",
        "type": "attraction",
        "confidence": 0.9,
        "status": "published",
        "verified": True,
        "summary": " ".join(["chữ"] * 130),
    }],
    "relationships": [],
    "itineraries": [],
}
```

Then assert inside the entity block, not only against static sitemap URLs:

```python
block = re.search(r"<url>(?:(?!</url>).)*/dia-diem/a(?:(?!</url>).)*</url>", xml, re.S)
assert block is not None
assert 'hreflang="vi"' in block.group()
assert 'hreflang="x-default"' in block.group()
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest agent/tests/test_index_policy.py agent/tests/test_source_policy.py tests/checks/test_hard_checks.py agent/tests/test_seo_structured.py -q
```

Expected: FAIL because unknown types can pass, Unicode-equivalent text double-counts, underscore/digit tokens count as words, artifact failures are unstructured, and the hreflang fixture does not prove an entity URL passed policy.

- [ ] **Step 3: Implement the exact shared type and Unicode behavior**

Create `agent/public_entity_types.py`:

```python
from __future__ import annotations

REVIEWED_NON_PLACE_ENTITY_TYPES = frozenset({
    "accommodation",
    "attraction",
    "cafe",
    "craft_village",
    "dish",
    "drink",
    "event",
    "experience",
    "facility",
    "history",
    "nature",
    "organization",
    "person",
    "product",
    "restaurant",
})
```

Create `agent/source_policy.py`:

```python
from __future__ import annotations

import ipaddress
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit

CANONICAL_SOURCE_HOSTS = frozenset({"vinhlong360.vn", "www.vinhlong360.vn"})


def _source_urls(value: object):
    if type(value) is str:
        yield value
        return
    if isinstance(value, Mapping):
        for key in ("url", "href"):
            candidate = value.get(key)
            if type(candidate) is str:
                yield candidate
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _source_urls(item)


def _is_external_http_url(value: str) -> bool:
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").rstrip(".").lower()
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    if host in CANONICAL_SOURCE_HOSTS or host == "localhost":
        return False
    if host.endswith((".localhost", ".local")):
        return False
    try:
        if not ipaddress.ip_address(host).is_global:
            return False
    except ValueError:
        if "." not in host:
            return False
    return True


def has_external_source_url(value: object) -> bool:
    return any(_is_external_http_url(url) for url in _source_urls(value))
```

Update `agent/index_policy.py` imports and reason order:

```python
import re
import unicodedata

if __package__:
    from .public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES
else:
    from public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES

ENTITY_REASON_ORDER = (
    "entity-type-missing",
    "entity-type-not-allowlisted",
    "public-status-missing",
    "public-status-not-allowlisted",
    "public-verification-missing",
    "public-explicitly-unverified",
    "public-private-content",
    "public-unpublished-content",
    "description-below-130-words",
)

_UNICODE_TOKEN = re.compile(r"\w+", flags=re.UNICODE)
```

Add the type gate and replace `_descriptive_word_count`:

```python
def _entity_type_reasons(snapshot: Mapping[str, object]) -> tuple[str, ...]:
    value = snapshot["type"]
    if value is _MISSING or value is None or value == "":
        return ("entity-type-missing",)
    if type(value) is not str or value not in REVIEWED_NON_PLACE_ENTITY_TYPES:
        return ("entity-type-not-allowlisted",)
    return ()


def _normalized_text(value: object) -> str:
    if type(value) is not str:
        return ""
    return unicodedata.normalize("NFC", value).strip()


def _descriptive_word_count(snapshot: Mapping[str, object]) -> int:
    summary = _normalized_text(snapshot["summary"])
    description = _normalized_text(snapshot["description"])
    parts = [summary]
    if description.casefold() != summary.casefold():
        parts.append(description)
    tokens = _UNICODE_TOKEN.findall(" ".join(parts))
    return sum(1 for token in tokens if any(char.isalpha() for char in token))
```

Replace the start of `decide_entity` with:

```python
snapshot = _snapshot(entity)
if snapshot["type"] == "place":
    raise ValueError("decide_entity accepts non-place entities only")
reasons = list(_entity_type_reasons(snapshot))
reasons.extend(_public_eligibility_reasons(snapshot))
```

Update `agent/launch_evidence.py` canonical revision handling:

```python
import unicodedata


def _validated_revision(value: object, label: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{label} must be a string")
    normalized = unicodedata.normalize("NFC", value)
    if not normalized or normalized.strip() != normalized:
        raise ValueError(f"{label} must be a non-empty canonical revision")
    return normalized
```

Use explicit UTF-8 JSON bytes:

```python
canonical = json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

Change `DataRichSourceCheck.check_entities` to fail closed on artifact loading:

```python
try:
    evidence = current_policy_evidence()
except Exception as exc:  # noqa: BLE001 - a broken release artifact is a hard failure
    return [{
        "file": DATA_REL,
        "line": 0,
        "rule": self.rule,
        "code": "index-policy-artifact-load-failed",
        "msg": f"index policy artifacts unavailable: {type(exc).__name__}",
    }]
```

Import and enforce the shared external URL rule in the same method:

```python
from source_policy import has_external_source_url

# inside the entity loop, after decide_entity returns indexable
if not has_external_source_url(e.get("source")):
    violations.append({
        "file": DATA_REL,
        "line": 0,
        "rule": self.rule,
        "code": "external-source-missing",
        "msg": f"{e.get('id') or '<no-id>'}: RICH nhưng thiếu URL nguồn ngoài",
    })
```

Delete the legacy `has = bool(...)` / `if not has:` truthiness block so title-only mappings, self-links, local URLs, and relative paths cannot pass R10.8.

Update `docs/standards/10-data.md` R10.8 authority text to:

```markdown
| R10.8 | Entity indexable theo `agent/index_policy.py` phải có >=1 URL nguồn HTTP(S) ngoài; lỗi nạp policy artifact là hard failure | hard-ratchet | check_data_schema (`data_rich_source`, dùng `index_policy.decide_entity`) |
```

- [ ] **Step 4: Run GREEN and focused lint**

Run:

```powershell
python -m pytest agent/tests/test_index_policy.py agent/tests/test_source_policy.py tests/checks/test_hard_checks.py agent/tests/test_seo.py agent/tests/test_seo_structured.py -q
python -m ruff check agent/public_entity_types.py agent/source_policy.py agent/index_policy.py agent/launch_evidence.py scripts/checks/check_data_schema.py agent/tests/test_index_policy.py agent/tests/test_source_policy.py tests/checks/test_hard_checks.py agent/tests/test_seo_structured.py
```

Expected: all tests pass and Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add agent/public_entity_types.py agent/source_policy.py agent/index_policy.py agent/launch_evidence.py agent/tests/test_index_policy.py agent/tests/test_source_policy.py scripts/checks/check_data_schema.py tests/checks/test_hard_checks.py agent/tests/test_seo_structured.py docs/standards/10-data.md
git commit -m "fix: close index policy quality findings"
```

### Task 2: Implement the pure `published-v1` predicate

**Files:**
- Create: `agent/publication_status.py`
- Create: `agent/tests/test_publication_status.py`

- [ ] **Step 1: Write the failing predicate contract tests**

Create `agent/tests/test_publication_status.py`:

```python
from __future__ import annotations

import copy
from types import MappingProxyType

import pytest

from publication_status import (
    PUBLISHED_V1_EXCLUSIONS,
    PublicationDecision,
    decide_publication_candidate,
    has_external_source_url,
)


def _candidate(**overrides):
    row = {
        "id": "candidate",
        "type": "dish",
        "status": None,
        "verified": True,
        "attributes": {},
        "source": [{"url": "https://example.org/source"}],
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize("verified", [False, 0, None, "true", 1.0])
def test_published_v1_requires_exact_true_or_integer_one(verified):
    decision = decide_publication_candidate(_candidate(verified=verified))
    assert decision.eligible is False
    assert "verified-not-true" in decision.reasons


@pytest.mark.parametrize("status", ["", "draft", "private", "published", "verified"])
def test_published_v1_allows_only_null_to_published(status):
    decision = decide_publication_candidate(_candidate(status=status))
    assert decision.eligible is False
    assert decision.reasons[0] == "status-not-null"


def test_missing_status_is_distinct_and_fails_closed():
    row = _candidate()
    row.pop("status")
    assert decide_publication_candidate(row).reasons[0] == "status-missing"


@pytest.mark.parametrize("entity_type", ["place", "itinerary", "unknown", None, 1])
def test_place_itinerary_unknown_and_malformed_types_are_excluded(entity_type):
    decision = decide_publication_candidate(_candidate(type=entity_type))
    assert decision.eligible is False
    assert any(reason.startswith("entity-type-") for reason in decision.reasons)


@pytest.mark.parametrize(
    "source",
    [
        [],
        [{"title": "Source without URL"}],
        [{"url": "/relative"}],
        [{"url": "http://localhost/source"}],
        [{"url": "http://127.0.0.1/source"}],
        [{"url": "https://vinhlong360.vn/source"}],
        "manual",
    ],
)
def test_external_source_is_mandatory(source):
    assert has_external_source_url(source) is False
    assert decide_publication_candidate(_candidate(source=source)).reasons == (
        "external-source-missing",
    )


@pytest.mark.parametrize(
    "source",
    [
        "https://example.org/source",
        {"url": "https://example.org/source"},
        [{"href": "http://example.net/source"}],
    ],
)
def test_supported_external_source_shapes_pass(source):
    assert decide_publication_candidate(_candidate(source=source)) == (
        PublicationDecision(eligible=True, reasons=())
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("is_private", True),
        ("private", True),
        ("is_draft", True),
        ("draft", True),
        ("unpublished", True),
        ("is_public", False),
        ("published", False),
        ("visibility", "private"),
    ],
)
def test_top_level_and_attribute_non_public_flags_fail_closed(field, value):
    top = _candidate(**{field: value})
    nested = _candidate(attributes={field: value})
    assert "non-public-flag" in decide_publication_candidate(top).reasons
    assert "non-public-flag" in decide_publication_candidate(nested).reasons


def test_malformed_attributes_fail_closed():
    assert decide_publication_candidate(_candidate(attributes=[])).reasons == (
        "attributes-invalid",
    )


def test_reviewed_exclusions_are_exact_and_stable():
    assert PUBLISHED_V1_EXCLUSIONS == frozenset({
        "prov-1",
        "test-mutation-create",
        "test-mutation-update",
        "cu-lao-dai-song-co-chien-vung-liem",
    })
    decision = decide_publication_candidate(_candidate(id="prov-1"))
    assert decision.reasons == ("reviewed-exclusion",)


def test_reason_order_is_stable_unique_and_input_is_not_mutated():
    row = _candidate(
        id="prov-1",
        type="place",
        status="draft",
        verified=False,
        attributes={"private": True},
        source=[],
    )
    original = copy.deepcopy(row)
    decision = decide_publication_candidate(MappingProxyType(row))
    assert decision.reasons == (
        "status-not-null",
        "verified-not-true",
        "entity-type-not-allowlisted",
        "non-public-flag",
        "external-source-missing",
        "reviewed-exclusion",
    )
    assert row == original
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest agent/tests/test_publication_status.py -q
```

Expected: FAIL because `agent/publication_status.py` does not exist.

- [ ] **Step 3: Implement the complete pure predicate**

Create `agent/publication_status.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

if __package__:
    from .public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES
    from .source_policy import has_external_source_url
else:
    from public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES
    from source_policy import has_external_source_url

PUBLICATION_POLICY_REVISION = "published-v1"
PUBLISHED_V1_EXCLUSIONS = frozenset({
    "prov-1",
    "test-mutation-create",
    "test-mutation-update",
    "cu-lao-dai-song-co-chien-vung-liem",
})
PUBLICATION_REASON_ORDER = (
    "status-missing",
    "status-not-null",
    "verified-not-true",
    "entity-type-missing",
    "entity-type-not-allowlisted",
    "attributes-invalid",
    "non-public-flag",
    "external-source-missing",
    "reviewed-exclusion",
)

_MISSING = object()
_NON_PUBLIC_TRUE_FLAGS = (
    "is_private",
    "private",
    "is_draft",
    "draft",
    "provisional",
    "unpublished",
)
_PUBLIC_TRUE_FLAGS = ("is_public", "published")


@dataclass(frozen=True)
class PublicationDecision:
    eligible: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.eligible) is not bool:
            raise TypeError("eligible must be a boolean")
        if type(self.reasons) is not tuple:
            raise TypeError("reasons must be a tuple")
        if any(type(reason) is not str for reason in self.reasons):
            raise TypeError("reasons must contain strings")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("reasons must be unique")
        positions = tuple(PUBLICATION_REASON_ORDER.index(r) for r in self.reasons)
        if positions != tuple(sorted(positions)):
            raise ValueError("reasons must use canonical order")
        if self.eligible is bool(self.reasons):
            raise ValueError("eligible does not match reasons")


def _supported_verified(value: object) -> bool:
    return value is True or (type(value) is int and value == 1)


def _contains_non_public_flag(row: Mapping[str, object], attrs: Mapping[str, object]) -> bool:
    scopes = (row, attrs)
    for scope in scopes:
        for field in _NON_PUBLIC_TRUE_FLAGS:
            value = scope.get(field, _MISSING)
            if value is not _MISSING and (type(value) is not bool or value is True):
                return True
        for field in _PUBLIC_TRUE_FLAGS:
            value = scope.get(field, _MISSING)
            if value is not _MISSING and (type(value) is not bool or value is False):
                return True
        visibility = scope.get("visibility", _MISSING)
        if visibility is not _MISSING and (
            type(visibility) is not str or visibility != "public"
        ):
            return True
    return False


def decide_publication_candidate(
    entity: Mapping[str, object],
    *,
    reviewed_exclusions: frozenset[str] = PUBLISHED_V1_EXCLUSIONS,
) -> PublicationDecision:
    if not isinstance(entity, Mapping):
        raise TypeError("entity must be a mapping")
    reasons: list[str] = []

    status = entity.get("status", _MISSING)
    if status is _MISSING:
        reasons.append("status-missing")
    elif status is not None:
        reasons.append("status-not-null")

    if not _supported_verified(entity.get("verified", _MISSING)):
        reasons.append("verified-not-true")

    entity_type = entity.get("type", _MISSING)
    if entity_type is _MISSING or entity_type is None or entity_type == "":
        reasons.append("entity-type-missing")
    elif type(entity_type) is not str or entity_type not in REVIEWED_NON_PLACE_ENTITY_TYPES:
        reasons.append("entity-type-not-allowlisted")

    attrs_value = entity.get("attributes", {})
    attrs: Mapping[str, object]
    if not isinstance(attrs_value, Mapping):
        reasons.append("attributes-invalid")
        attrs = {}
    else:
        attrs = attrs_value
    if _contains_non_public_flag(entity, attrs):
        reasons.append("non-public-flag")

    if not has_external_source_url(entity.get("source")):
        reasons.append("external-source-missing")

    entity_id = entity.get("id")
    if type(entity_id) is str and entity_id in reviewed_exclusions:
        reasons.append("reviewed-exclusion")

    ordered = tuple(reason for reason in PUBLICATION_REASON_ORDER if reason in reasons)
    return PublicationDecision(eligible=not ordered, reasons=ordered)
```

- [ ] **Step 4: Run GREEN and lint**

Run:

```powershell
python -m pytest agent/tests/test_publication_status.py agent/tests/test_index_policy.py -q
python -m ruff check agent/publication_status.py agent/tests/test_publication_status.py
```

Expected: all tests pass and Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add agent/publication_status.py agent/tests/test_publication_status.py
git commit -m "feat: define published status candidate policy"
```

## Phase 2: Remove Local Data-Loss and Test-Contamination Risks

### Task 3: Isolate database-writing tests from repository SQLite

**Files:**
- Create: `tests/test_entity_test_isolation.py`
- Modify: `agent/tests/conftest.py`
- Modify: `agent/tests/test_admin_mutations.py`
- Modify: `agent/tests/test_kb_curation.py`

- [ ] **Step 1: Write a safe failing source-level isolation assertion**

Create `tests/test_entity_test_isolation.py` without importing the mutation test modules:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_entity_mutation_tests_declare_temporary_database_isolation():
    conftest = (ROOT / "agent" / "tests" / "conftest.py").read_text(encoding="utf-8")
    admin_tests = (
        ROOT / "agent" / "tests" / "test_admin_mutations.py"
    ).read_text(encoding="utf-8")
    kb_tests = (
        ROOT / "agent" / "tests" / "test_kb_curation.py"
    ).read_text(encoding="utf-8")
    assert "def isolated_sqlite_db" in conftest
    assert "def isolate_admin_database" in admin_tests
    assert "isolated_sqlite_db" in kb_tests
```

Run only this safe test:

```powershell
python -m pytest tests/test_entity_test_isolation.py -q
```

Expected: FAIL on source assertions without importing `server`, calling endpoints, or writing any database.

- [ ] **Step 2: Add the reusable fixture and redirect all mutation writes**

Add to `agent/tests/conftest.py`:

```python
@pytest.fixture
def isolated_sqlite_db(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import database

    instance = database.Database(str(tmp_path / "isolated.db"))
    assert Path(instance.db_path).parent == tmp_path
    return instance
```

Add to `agent/tests/test_admin_mutations.py`:

```python
@pytest.fixture(autouse=True)
def isolate_admin_database(isolated_sqlite_db, monkeypatch):
    import admin
    import database

    monkeypatch.setattr(database, "db", isolated_sqlite_db)
    monkeypatch.setattr(admin, "db", isolated_sqlite_db)
    yield


def test_admin_mutations_use_temporary_sqlite(isolated_sqlite_db):
    assert pathlib.Path(isolated_sqlite_db.db_path).name == "isolated.db"
    assert pathlib.Path(isolated_sqlite_db.db_path).resolve() != (
        pathlib.Path(__file__).resolve().parents[1] / "data" / "vinhlong360.db"
    ).resolve()
```

Replace `TestDbWriteThrough.test_promote_and_reject_hit_db` setup in `agent/tests/test_kb_curation.py` with the isolated fixture:

```python
def test_promote_and_reject_hit_db(
    self, kb_with_provisional, isolated_sqlite_db, monkeypatch
):
    import database

    monkeypatch.setattr(database, "db", isolated_sqlite_db)
    ids = ["prov-1", "prov-2"]
    isolated_sqlite_db.upsert_entity({
        "id": "prov-1", "name": "Quán mới X", "type": "dish",
        "status": "provisional", "verified": False,
    })
    isolated_sqlite_db.upsert_entity({
        "id": "prov-2", "name": "Điểm Y", "type": "attraction",
        "status": "provisional", "verified": False,
    })
    review = next(x for x in kb_curation.list_provisional() if x["id"] == "prov-1")
    assert kb_curation.promote("prov-1", review["review_token"])["ok"] is True
    assert isolated_sqlite_db.get_entity("prov-1") is not None
    assert kb_curation.reject("prov-2")["ok"] is True
    assert isolated_sqlite_db.get_entity("prov-2") is None
```

Complete fixture imports and remove shared-DB cleanup logic:

Ensure `agent/tests/conftest.py` imports are:

```python
from pathlib import Path

import pytest
```

Keep the module-level `TestClient` and endpoint assertions unchanged; only redirect `admin.db` and lazy `database.db` writes to the per-test temporary database. Remove the `finally: db.delete_entity(...)` block from the replaced KB test because the temporary database is discarded by `tmp_path`.

- [ ] **Step 3: Run the source guard and focused tests while proving byte stability**

Run:

```powershell
$before = (Get-FileHash agent/data/vinhlong360.db -Algorithm SHA256).Hash
python -m pytest tests/test_entity_test_isolation.py agent/tests/test_admin_mutations.py agent/tests/test_kb_curation.py -q
$after = (Get-FileHash agent/data/vinhlong360.db -Algorithm SHA256).Hash
if ($before -ne $after) { throw "repository SQLite changed" }
```

Expected: tests pass and the two hashes are identical.

- [ ] **Step 4: Run lint on the isolation changes**

Run:

```powershell
python -m ruff check tests/test_entity_test_isolation.py agent/tests/conftest.py agent/tests/test_admin_mutations.py agent/tests/test_kb_curation.py
```

Expected: Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_entity_test_isolation.py agent/tests/conftest.py agent/tests/test_admin_mutations.py agent/tests/test_kb_curation.py
git commit -m "test: isolate entity mutation databases"
```

### Task 4: Preserve `status` and `verified` through every entity persistence path

**Files:**
- Modify: `agent/database.py`
- Modify: `agent/tests/test_database.py`
- Modify: `agent/tests/test_admin_mutations.py`
- Modify: `tests/test_export_data.py`

- [ ] **Step 1: Write failing upsert, bulk-import, admin, and export round-trip tests**

Add to `agent/tests/test_database.py`:

```python
def test_upsert_preserves_publication_fields_when_omitted(db):
    db.upsert_entity({
        "id": "publication-preserve",
        "type": "dish",
        "name": "Initial",
        "status": "published",
        "verified": False,
    })
    db.upsert_entity({
        "id": "publication-preserve",
        "type": "dish",
        "name": "Updated",
    })
    saved = db.get_entity("publication-preserve")
    assert saved["status"] == "published"
    assert saved["verified"] in (False, 0)


def test_upsert_changes_publication_fields_only_when_explicit(db):
    db.upsert_entity({
        "id": "publication-explicit",
        "type": "dish",
        "name": "Initial",
        "status": "provisional",
        "verified": False,
    })
    db.upsert_entity({
        "id": "publication-explicit",
        "type": "dish",
        "name": "Approved",
        "status": "verified",
        "verified": True,
    })
    saved = db.get_entity("publication-explicit")
    assert saved["status"] == "verified"
    assert saved["verified"] in (True, 1)
```

Extend `MINI` in `tests/test_export_data.py` with:

```python
"status": "published",
"verified": False,
```

Extend `test_export_roundtrip_stable`:

```python
for field in (
    "name", "summary", "description", "type", "attributes", "status", "verified"
):
    assert e1[i].get(field) == e2[i].get(field), (i, field)
```

Add to `agent/tests/test_admin_mutations.py`:

```python
def test_admin_update_does_not_erase_publication_fields(isolated_sqlite_db):
    isolated_sqlite_db.upsert_entity({
        "id": "test-mutation-status",
        "name": "Published entity",
        "type": "attraction",
        "status": "published",
        "verified": True,
    })
    response = client.put(
        "/admin/entities/test-mutation-status",
        json={"name": "Renamed", "type": "attraction"},
        headers=H,
    )
    assert response.status_code == 200
    saved = isolated_sqlite_db.get_entity("test-mutation-status")
    assert saved["status"] == "published"
    assert saved["verified"] in (True, 1)
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest agent/tests/test_database.py agent/tests/test_admin_mutations.py tests/test_export_data.py -q
```

Expected: FAIL because SQLite `INSERT OR REPLACE` and bulk row tuples omit publication fields.

- [ ] **Step 3: Implement omission-aware upsert and complete bulk tuples**

Add this helper near `_normalize_upsert_fields` in `agent/database.py`:

```python
def _publication_write_fields(entity: dict) -> tuple[object, object, bool, bool]:
    return (
        entity.get("status"),
        entity.get("verified", True),
        "status" in entity,
        "verified" in entity,
    )
```

In `_write_entity_row`, compute:

```python
status, verified, has_status, has_verified = _publication_write_fields(entity)
```

Extend the PostgreSQL insert columns/values and conflict update:

```sql
INSERT INTO entities
(id, type, name, summary, description, "placeId", confidence, season,
 attributes, source, images, "updatedAt", coordinates, area, level,
 "parentId", "legacyArea", status, verified)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (id) DO UPDATE SET
    type = EXCLUDED.type,
    name = EXCLUDED.name,
    summary = EXCLUDED.summary,
    description = EXCLUDED.description,
    "placeId" = EXCLUDED."placeId",
    confidence = EXCLUDED.confidence,
    season = EXCLUDED.season,
    attributes = EXCLUDED.attributes,
    source = EXCLUDED.source,
    images = EXCLUDED.images,
    "updatedAt" = EXCLUDED."updatedAt",
    coordinates = EXCLUDED.coordinates,
    area = EXCLUDED.area,
    level = EXCLUDED.level,
    "parentId" = EXCLUDED."parentId",
    "legacyArea" = EXCLUDED."legacyArea",
    status = CASE WHEN %s THEN EXCLUDED.status ELSE entities.status END,
    verified = CASE WHEN %s THEN EXCLUDED.verified ELSE entities.verified END
```

Use this exact parameter tuple for both backend statements (JSON serialization remains backend-specific where already required):

```python
values = (
    entity["id"],
    entity["type"],
    entity["name"],
    entity.get("summary", ""),
    entity.get("description", ""),
    entity.get("placeId"),
    entity.get("confidence", 1.0),
    json.dumps(season_val, ensure_ascii=False) if season_val else None,
    json.dumps(attrs_store, ensure_ascii=False),
    json.dumps(source_val, ensure_ascii=False),
    json.dumps(images_val, ensure_ascii=False),
    updated,
    json.dumps(coords_val) if coords_val else None,
    entity.get("area"),
    entity.get("level"),
    entity.get("parentId"),
    entity.get("legacyArea"),
    status,
    verified,
    has_status,
    has_verified,
)
```

Replace the SQLite `INSERT OR REPLACE` with omission-aware UPSERT:

```sql
INSERT INTO entities
(id, type, name, summary, description, placeId, confidence, season,
 attributes, source, images, updatedAt, coordinates, area, level,
 parentId, legacyArea, status, verified)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(id) DO UPDATE SET
    type = excluded.type,
    name = excluded.name,
    summary = excluded.summary,
    description = excluded.description,
    placeId = excluded.placeId,
    confidence = excluded.confidence,
    season = excluded.season,
    attributes = excluded.attributes,
    source = excluded.source,
    images = excluded.images,
    updatedAt = excluded.updatedAt,
    coordinates = excluded.coordinates,
    area = excluded.area,
    level = excluded.level,
    parentId = excluded.parentId,
    legacyArea = excluded.legacyArea,
    status = CASE WHEN ? THEN excluded.status ELSE entities.status END,
    verified = CASE WHEN ? THEN excluded.verified ELSE entities.verified END
```

For `_build_bulk_entity_rows`, use this exact tuple tail:

```python
entity.get("legacyArea"),
entity.get("status"),
entity.get("verified", True),
```

Use these exact bulk statements in `_bulk_insert_rows`:

```python
# PostgreSQL
'INSERT INTO entities (id, type, name, summary, description, "placeId", confidence, season, '
'attributes, source, images, "updatedAt", coordinates, area, level, "parentId", "legacyArea", status, verified) '
'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
'ON CONFLICT (id) DO NOTHING'

# SQLite replacement load runs only after the guarded bulk loader clears the target tables.
"INSERT OR REPLACE INTO entities (id, type, name, summary, description, placeId, confidence, season, "
"attributes, source, images, updatedAt, coordinates, area, level, parentId, legacyArea, status, verified) "
"VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
```

- [ ] **Step 4: Run GREEN, focused database regression, and lint**

Run:

```powershell
python -m pytest agent/tests/test_database.py agent/tests/test_admin_mutations.py agent/tests/test_kb_curation.py tests/test_export_data.py tests/test_database_filters.py -q
python -m ruff check agent/database.py agent/tests/test_database.py agent/tests/test_admin_mutations.py tests/test_export_data.py
```

Expected: all tests pass; repository SQLite hash remains unchanged; Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add agent/database.py agent/tests/test_database.py agent/tests/test_admin_mutations.py tests/test_export_data.py
git commit -m "fix: preserve entity publication fields"
```

## Phase 3: Build Explicit PostgreSQL Backup Evidence

### Task 5: Add target identity helpers and validated PostgreSQL backups

**Files:**
- Create: `scripts/postgres_target.py`
- Create: `tests/test_postgres_target.py`
- Modify: `scripts/backup_data.py`
- Create: `tests/test_backup_data.py`

- [ ] **Step 1: Write failing target, canonical JSON, backup, and refusal tests**

Create `tests/test_postgres_target.py`:

```python
from __future__ import annotations

import json

import pytest

from scripts.postgres_target import (
    canonical_json_bytes,
    resolve_database_url,
    pg_cli_connection,
    target_fingerprint,
)


def test_database_url_requires_named_explicit_environment(monkeypatch):
    monkeypatch.delenv("VINHLONG360_PROD_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://wrong/fallback")
    with pytest.raises(RuntimeError, match="VINHLONG360_PROD_DATABASE_URL"):
        resolve_database_url("VINHLONG360_PROD_DATABASE_URL")


@pytest.mark.parametrize("value", ["", "sqlite:///x.db", "postgres://host/db"])
def test_database_url_accepts_only_postgresql_scheme(monkeypatch, value):
    monkeypatch.setenv("TARGET_DB", value)
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        resolve_database_url("TARGET_DB")


def test_canonical_json_is_utf8_sorted_and_newline_terminated():
    payload = {"b": "cồn", "a": [2, 1]}
    assert canonical_json_bytes(payload) == (
        '{"a":[2,1],"b":"cồn"}\n'.encode("utf-8")
    )


def test_target_fingerprint_excludes_credentials():
    identity = {
        "database": "vl360",
        "server_addr": "10.0.0.3",
        "server_port": 5432,
        "server_version_num": 160004,
    }
    digest = target_fingerprint(identity)
    assert len(digest) == 64
    assert "password" not in json.dumps(identity)


def test_pg_cli_connection_keeps_password_out_of_process_arguments():
    arguments, environment = pg_cli_connection(
        "postgresql://user:secret@db.example:5433/vl360?sslmode=require"
    )
    assert "secret" not in " ".join(arguments)
    assert environment["PGPASSWORD"] == "secret"
    assert environment["PGSSLMODE"] == "require"
```

Create `tests/test_backup_data.py` with a fake command runner:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import backup_data


class FakeRunner:
    def __init__(self, restore_output="TABLE public entities\nTABLE public entity_changes\n"):
        self.calls = []
        self.restore_output = restore_output

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if "--version" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=f"{command[0]} (PostgreSQL) 16.4\n",
                stderr="",
            )
        if command[0] == "pg_dump":
            Path(command[command.index("--file") + 1]).write_bytes(b"PGDMP-test")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout=self.restore_output, stderr="")


def test_pg_backup_writes_validated_manifest(tmp_path, monkeypatch):
    runner = FakeRunner()
    backup_dir = tmp_path / "backup"
    identity = {
        "database": "vl360",
        "server_addr": "10.0.0.3",
        "server_port": 5432,
        "server_version_num": 160004,
    }
    result = backup_data.create_postgres_backup(
        database_url="postgresql://user:secret@db.example/vl360",
        destination=backup_dir,
        identity=identity,
        runner=runner,
        now=lambda: "2026-07-14T12:00:00Z",
    )
    manifest = json.loads(result.read_text(encoding="utf-8"))
    artifact = backup_dir / manifest["artifact"]["path"]
    assert manifest["schema"] == "vinhlong360-pg-backup-v1"
    assert manifest["validation"]["pg_restore_list"] is True
    assert manifest["validation"]["required_tables"] == ["entities", "entity_changes"]
    assert manifest["tools"] == {
        "pg_dump": "pg_dump (PostgreSQL) 16.4",
        "pg_restore": "pg_restore (PostgreSQL) 16.4",
    }
    assert manifest["artifact"]["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert "secret" not in result.read_text(encoding="utf-8")
    assert all("secret" not in " ".join(call[0]) for call in runner.calls)


def test_pg_backup_refuses_missing_required_table(tmp_path):
    with pytest.raises(RuntimeError, match="entity_changes"):
        backup_data.create_postgres_backup(
            database_url="postgresql://user:secret@db.example/vl360",
            destination=tmp_path / "backup",
            identity={
                "database": "vl360", "server_addr": "10.0.0.3",
                "server_port": 5432, "server_version_num": 160004,
            },
            runner=FakeRunner(restore_output="TABLE public entities\n"),
            now=lambda: "2026-07-14T12:00:00Z",
        )
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_postgres_target.py tests/test_backup_data.py -q
```

Expected: FAIL because the target helper and PostgreSQL backup functions do not exist.

- [ ] **Step 3: Implement explicit target helpers and backup modes**

Create `scripts/postgres_target.py` with these public interfaces:

```python
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_database_url(environment_name: str) -> str:
    if not environment_name or environment_name == "DATABASE_URL":
        raise RuntimeError("a named non-default database URL environment is required")
    value = os.environ.get(environment_name, "")
    if not value.startswith("postgresql://"):
        raise RuntimeError(f"{environment_name} must contain a PostgreSQL URL")
    parsed = urlsplit(value)
    if not parsed.hostname or not parsed.path.strip("/"):
        raise RuntimeError(f"{environment_name} must identify a PostgreSQL host and database")
    return value


def pg_cli_connection(database_url: str) -> tuple[list[str], dict[str, str]]:
    parsed = urlsplit(database_url)
    database = parsed.path.strip("/")
    arguments = [
        "--host", parsed.hostname or "",
        "--port", str(parsed.port or 5432),
        "--username", unquote(parsed.username or ""),
        "--dbname", database,
    ]
    environment: dict[str, str] = {}
    if parsed.password is not None:
        environment["PGPASSWORD"] = unquote(parsed.password)
    query = parse_qs(parsed.query)
    if query.get("sslmode"):
        environment["PGSSLMODE"] = query["sslmode"][-1]
    return arguments, environment


def read_target_identity(cursor) -> dict[str, object]:
    cursor.execute(
        "SELECT current_database(), inet_server_addr()::text, "
        "inet_server_port(), current_setting('server_version_num')::int"
    )
    row = cursor.fetchone()
    return {
        "database": row[0],
        "server_addr": row[1],
        "server_port": row[2],
        "server_version_num": row[3],
    }


def target_fingerprint(identity: dict[str, object]) -> str:
    allowed = {
        key: identity[key]
        for key in ("database", "server_addr", "server_port", "server_version_num")
    }
    return sha256_bytes(canonical_json_bytes(allowed))


def write_exclusive(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(payload))
    return path
```

Refactor `scripts/backup_data.py` so `--target local` remains the default and uses `sqlite3.Connection.backup()` for the SQLite artifact. Add `--target pg`, `--database-url-env`, and `--out-dir`. Implement PostgreSQL backup with:

```python
if __package__:
    from .postgres_target import (
        pg_cli_connection,
        read_target_identity,
        resolve_database_url,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
        write_exclusive,
    )
else:
    from postgres_target import (
        pg_cli_connection,
        read_target_identity,
        resolve_database_url,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
        write_exclusive,
    )

PG_REQUIRED_TABLES = ("entities", "entity_changes")


def create_postgres_backup(
    *, database_url: str, destination: Path, identity: dict[str, object],
    runner=subprocess.run, now=_utc_now,
) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    artifact = destination / "postgres.dump"
    started_at = now()
    connection_args, connection_environment = pg_cli_connection(database_url)
    command_environment = os.environ.copy()
    command_environment.update(connection_environment)
    tool_versions = {}
    for executable in ("pg_dump", "pg_restore"):
        version = runner(
            [executable, "--version"],
            check=False, capture_output=True, text=True, env=command_environment,
        )
        if version.returncode != 0 or not version.stdout.strip():
            raise RuntimeError(f"{executable} --version failed")
        tool_versions[executable] = version.stdout.strip()
    dump = runner(
        ["pg_dump", "--format=custom", "--file", str(artifact), *connection_args],
        check=False, capture_output=True, text=True, env=command_environment,
    )
    if dump.returncode != 0 or not artifact.is_file() or artifact.stat().st_size == 0:
        raise RuntimeError("pg_dump failed or produced an empty artifact")
    listing = runner(
        ["pg_restore", "--list", str(artifact)],
        check=False, capture_output=True, text=True,
    )
    if listing.returncode != 0:
        raise RuntimeError("pg_restore --list validation failed")
    missing = [table for table in PG_REQUIRED_TABLES if table not in listing.stdout]
    if missing:
        raise RuntimeError(f"backup missing required tables: {', '.join(missing)}")
    manifest = {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target_fingerprint(identity),
        "database_identity": identity,
        "started_at": started_at,
        "completed_at": now(),
        "max_age_seconds": 3600,
        "tools": tool_versions,
        "artifact": {
            "path": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": sha256_file(artifact),
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": list(PG_REQUIRED_TABLES),
            "listing_sha256": sha256_bytes(listing.stdout.encode("utf-8")),
        },
        "policy_revision": "published-v1",
    }
    return write_exclusive(destination / "manifest.json", manifest)
```

The CLI must connect only after `resolve_database_url(args.database_url_env)`, read identity through psycopg2, and never print the DSN. If `pg_dump`, `pg_restore`, psycopg2, the target env, or required tables are missing, return exit code 1 and leave no manifest claiming success.

- [ ] **Step 4: Run GREEN, local-backup compatibility, and lint**

Run:

```powershell
python -m pytest tests/test_postgres_target.py tests/test_backup_data.py -q
python scripts/backup_data.py --target local --label plan-test --out-dir scratch/backups-plan-test
python -m ruff check scripts/postgres_target.py scripts/backup_data.py tests/test_postgres_target.py tests/test_backup_data.py
```

Expected: tests pass; local backup creates JSON/SQLite artifacts through safe APIs; no PostgreSQL command runs; Ruff exits 0. Remove only the newly created `scratch/backups-plan-test` test artifact after verifying its resolved path is inside this worktree's `scratch` directory.

- [ ] **Step 5: Commit**

```powershell
git add scripts/postgres_target.py scripts/backup_data.py tests/test_postgres_target.py tests/test_backup_data.py
git commit -m "feat: validate PostgreSQL backup evidence"
```

## Phase 4: Build Immutable Plan and Transactional Apply

### Task 6: Implement canonical PostgreSQL plan generation

**Files:**
- Create: `scripts/migrate_entity_status.py`
- Create: `tests/test_migrate_entity_status.py`

- [ ] **Step 1: Write failing deterministic plan and refusal tests**

Create `tests/test_migrate_entity_status.py` with shared fixtures and plan tests:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.migrate_entity_status import (
    PLAN_SCHEMA,
    MigrationRefusal,
    build_plan,
    candidate_id_hash,
    load_immutable_json,
    write_immutable_json,
)


IDENTITY = {
    "database": "vl360",
    "server_addr": "10.0.0.3",
    "server_port": 5432,
    "server_version_num": 160004,
}
COLUMNS = [
    ("attributes", "jsonb", "YES"),
    ("id", "text", "NO"),
    ("source", "jsonb", "YES"),
    ("status", "text", "YES"),
    ("type", "text", "NO"),
    ("verified", "integer", "YES"),
]


def _row(entity_id="a", **overrides):
    row = {
        "id": entity_id,
        "type": "dish",
        "status": None,
        "verified": 1,
        "attributes": {},
        "source": [{"url": "https://example.org/source"}],
    }
    row.update(overrides)
    return row


def test_plan_is_canonical_deterministic_and_records_every_exclusion():
    rows = [
        _row("b"),
        _row("a"),
        _row("place", type="place"),
        _row("no-source", source=[]),
        _row("existing", status="verified"),
    ]
    plan = build_plan(
        rows=rows,
        identity=IDENTITY,
        schema_columns=COLUMNS,
        created_at="2026-07-14T12:00:00Z",
        tool_source_revision="abc123",
    )
    assert plan["schema"] == PLAN_SCHEMA
    assert plan["candidate_ids"] == ["a", "b"]
    assert plan["candidate_count"] == 2
    assert plan["candidate_sha256"] == candidate_id_hash(["a", "b"])
    assert plan["exclusion_counts"] == {
        "entity-type-not-allowlisted": 1,
        "external-source-missing": 1,
        "status-not-null": 1,
    }
    assert plan["reviewed_exclusions"] == sorted(plan["reviewed_exclusions"])


def test_plan_rejects_duplicate_ids_and_empty_candidate_set():
    with pytest.raises(MigrationRefusal, match="duplicate entity id"):
        build_plan(
            rows=[_row("a"), _row("a")], identity=IDENTITY,
            schema_columns=COLUMNS, created_at="2026-07-14T12:00:00Z",
            tool_source_revision="abc123",
        )
    with pytest.raises(MigrationRefusal, match="zero candidates"):
        build_plan(
            rows=[_row("place", type="place")], identity=IDENTITY,
            schema_columns=COLUMNS, created_at="2026-07-14T12:00:00Z",
            tool_source_revision="abc123",
        )


def test_immutable_json_refuses_overwrite_and_detects_tampering(tmp_path):
    path = tmp_path / "plan.json"
    digest = write_immutable_json(path, {"schema": "x", "value": "cồn"})
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        write_immutable_json(path, {"schema": "x"})
    loaded, loaded_digest = load_immutable_json(path)
    assert loaded["value"] == "cồn"
    assert loaded_digest == digest
    path.write_text(json.dumps({"schema": "x"}), encoding="utf-8")
    assert load_immutable_json(path)[1] != digest
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
```

Expected: FAIL because `scripts/migrate_entity_status.py` does not exist.

- [ ] **Step 3: Implement plan schema, DB snapshot, canonical hashes, and CLI**

Create the module with these fixed constants and interfaces:

```python
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from publication_status import (  # noqa: E402
    PUBLICATION_POLICY_REVISION,
    PUBLISHED_V1_EXCLUSIONS,
    decide_publication_candidate,
)

if __package__:
    from .postgres_target import (  # noqa: E402
        canonical_json_bytes,
        read_target_identity,
        resolve_database_url,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
        write_exclusive,
    )
else:
    from postgres_target import (  # noqa: E402
        canonical_json_bytes,
        read_target_identity,
        resolve_database_url,
        sha256_bytes,
        sha256_file,
        target_fingerprint,
        write_exclusive,
    )

PLAN_SCHEMA = "vinhlong360-entity-status-plan-v1"
APPLY_SCHEMA = "vinhlong360-entity-status-apply-v1"
ROLLBACK_SCHEMA = "vinhlong360-entity-status-rollback-v1"
MAX_PLAN_AGE_SECONDS = 86400
LOCK_NAME = "vinhlong360:entity-status:published-v1"
REQUIRED_ENTITY_COLUMNS = {"id", "type", "status", "verified", "attributes", "source"}


class MigrationRefusal(RuntimeError):
    pass


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MigrationRefusal("timestamp is not valid UTC ISO-8601") from exc
    if parsed.tzinfo is None:
        raise MigrationRefusal("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise MigrationRefusal("runtime timestamp must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def candidate_id_hash(ids: list[str]) -> str:
    return sha256_bytes(canonical_json_bytes(ids))


def schema_fingerprint(columns: list[tuple[str, str, str]]) -> str:
    normalized = [
        {"name": name, "type": data_type, "nullable": nullable}
        for name, data_type, nullable in sorted(columns)
    ]
    return sha256_bytes(canonical_json_bytes(normalized))


def write_immutable_json(path: Path, value: object) -> str:
    write_exclusive(path, value)
    return sha256_file(path)


def load_immutable_json(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise MigrationRefusal("artifact root must be an object")
    return value, sha256_bytes(raw)
```

Implement `build_plan` exactly as follows:

```python
def _status_group(value: object) -> str:
    if value is None:
        return "<null>"
    if type(value) is str:
        return value
    return f"<{type(value).__name__}>:{value!r}"


def build_plan(
    *,
    rows: list[dict[str, object]],
    identity: dict[str, object],
    schema_columns: list[tuple[str, str, str]],
    created_at: str,
    tool_source_revision: str,
) -> dict[str, object]:
    column_names = {name for name, _data_type, _nullable in schema_columns}
    missing_columns = sorted(REQUIRED_ENTITY_COLUMNS - column_names)
    if missing_columns:
        raise MigrationRefusal(
            f"entities schema missing required columns: {', '.join(missing_columns)}"
        )

    seen: set[str] = set()
    candidate_ids: list[str] = []
    exclusion_counts: Counter[str] = Counter()
    status_groups: Counter[str] = Counter()
    published_before = 0
    null_before = 0

    for row in rows:
        if not isinstance(row, dict):
            raise MigrationRefusal("entity rows must be dictionaries")
        entity_id = row.get("id")
        if type(entity_id) is not str or not entity_id:
            raise MigrationRefusal("entity id must be a non-empty string")
        if entity_id in seen:
            raise MigrationRefusal(f"duplicate entity id: {entity_id}")
        seen.add(entity_id)

        status = row.get("status")
        status_groups[_status_group(status)] += 1
        if status is None:
            null_before += 1
        elif status == "published":
            published_before += 1

        decision = decide_publication_candidate(row)
        if decision.eligible:
            candidate_ids.append(entity_id)
        else:
            exclusion_counts.update(decision.reasons)

    candidate_ids.sort()
    if not candidate_ids:
        raise MigrationRefusal("publication plan has zero candidates")
    normalized_columns = [
        {"name": name, "type": data_type, "nullable": nullable}
        for name, data_type, nullable in sorted(schema_columns)
    ]
    return {
        "schema": PLAN_SCHEMA,
        "policy_revision": PUBLICATION_POLICY_REVISION,
        "created_at": created_at,
        "max_age_seconds": MAX_PLAN_AGE_SECONDS,
        "tool_source_revision": tool_source_revision,
        "target_fingerprint": target_fingerprint(identity),
        "database_identity": identity,
        "schema_fingerprint": schema_fingerprint(schema_columns),
        "schema_columns": normalized_columns,
        "candidate_ids": candidate_ids,
        "candidate_count": len(candidate_ids),
        "candidate_sha256": candidate_id_hash(candidate_ids),
        "reviewed_exclusions": sorted(PUBLISHED_V1_EXCLUSIONS),
        "exclusion_counts": dict(sorted(exclusion_counts.items())),
        "status_groups": dict(sorted(status_groups.items())),
        "expected_before": {"published": published_before, "null": null_before},
        "expected_after": {
            "published": published_before + len(candidate_ids),
            "null": null_before - len(candidate_ids),
        },
    }
```

The `plan` CLI must require all of:

```text
--target pg
--database-url-env <non-DATABASE_URL name>
--policy published-v1
--report-out <new path>
```

It must query identity and schema from the explicit connection, read `SELECT * FROM entities ORDER BY id` in a `REPEATABLE READ, READ ONLY` transaction, resolve the tool revision from `VINHLONG360_RELEASE_REVISION` or `git rev-parse HEAD`, write with exclusive creation, print only the report path/hash/count/target fingerprint, and never print the DSN.

- [ ] **Step 4: Run GREEN, CLI refusal checks, and lint**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
python scripts/migrate_entity_status.py plan --target sqlite --database-url-env X --policy published-v1 --report-out scratch/forbidden.json
if ($LASTEXITCODE -eq 0) { throw "SQLite target was accepted" }
python scripts/migrate_entity_status.py plan --target pg --database-url-env DATABASE_URL --policy published-v1 --report-out scratch/forbidden.json
if ($LASTEXITCODE -eq 0) { throw "default DATABASE_URL was accepted" }
python -m ruff check scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
```

Expected: unit tests pass; both unsafe CLI calls fail before connecting or writing; Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
git commit -m "feat: generate immutable publication plans"
```

### Task 7: Implement manifest-locked transactional apply

**Files:**
- Modify: `scripts/migrate_entity_status.py`
- Modify: `tests/test_migrate_entity_status.py`

- [ ] **Step 1: Write failing backup, drift, audit, and idempotency tests**

Add a fake store to `tests/test_migrate_entity_status.py`:

```python
from datetime import datetime, timezone

from scripts.migrate_entity_status import (
    BackupEvidence,
    LOCK_NAME,
    apply_plan,
)
from scripts.postgres_target import canonical_json_bytes, sha256_bytes

NOW = datetime(2026, 7, 14, 12, 10, tzinfo=timezone.utc)


def _artifact_sha(value):
    return sha256_bytes(canonical_json_bytes(value))


def _valid_plan(rows):
    return build_plan(
        rows=rows,
        identity=IDENTITY,
        schema_columns=COLUMNS,
        created_at="2026-07-14T12:00:00Z",
        tool_source_revision="abc123",
    )


def _valid_backup(tmp_path, target_fingerprint):
    root = tmp_path / "backup"
    root.mkdir()
    artifact = root / "postgres.dump"
    artifact.write_bytes(b"PGDMP-test")
    manifest = {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target_fingerprint,
        "database_identity": IDENTITY,
        "started_at": "2026-07-14T12:00:00Z",
        "completed_at": "2026-07-14T12:00:01Z",
        "max_age_seconds": 3600,
        "artifact": {
            "path": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": ["entities", "entity_changes"],
            "listing_sha256": "a" * 64,
        },
        "policy_revision": "published-v1",
    }
    return BackupEvidence(
        manifest=manifest,
        manifest_sha256=_artifact_sha(manifest),
        artifact_root=root,
    )


def _valid_apply_report(plan, plan_sha, backup_sha):
    return {
        "schema": "vinhlong360-entity-status-apply-v1",
        "policy_revision": "published-v1",
        "result": "applied",
        "target_fingerprint": plan["target_fingerprint"],
        "schema_fingerprint": plan["schema_fingerprint"],
        "plan_sha256": plan_sha,
        "backup_manifest_sha256": backup_sha,
        "candidate_ids": plan["candidate_ids"],
        "candidate_count": plan["candidate_count"],
        "candidate_sha256": plan["candidate_sha256"],
        "expected_before": plan["expected_before"],
        "expected_after": plan["expected_after"],
        "updated_ids": plan["candidate_ids"],
        "started_at": "2026-07-14T12:10:00Z",
        "completed_at": "2026-07-14T12:10:01Z",
    }


class FakeStore:
    def __init__(self, rows, identity=IDENTITY, columns=COLUMNS):
        self.rows = {row["id"]: dict(row) for row in rows}
        self.identity = identity
        self.columns = columns
        self.locked = False
        self.audit = []

    def acquire_lock(self, name):
        self.locked = name

    def target_identity(self):
        return self.identity

    def schema_columns(self):
        return self.columns

    def rows_for_update(self, ids):
        return [dict(self.rows[entity_id]) for entity_id in ids if entity_id in self.rows]

    def audit_ids(self, actor, old_value, new_value):
        return {
            row["entity_id"]
            for row in self.audit
            if row["actor"] == actor
            and row["old_value"] == old_value
            and row["new_value"] == new_value
        }

    def status_counts(self):
        return {
            "published": sum(row["status"] == "published" for row in self.rows.values()),
            "null": sum(row["status"] is None for row in self.rows.values()),
        }

    def update_to_published(self, ids):
        changed = []
        for entity_id in ids:
            if self.rows[entity_id]["status"] is None:
                self.rows[entity_id]["status"] = "published"
                changed.append(entity_id)
        return changed

    def insert_status_audit(self, ids, actor, old_value, new_value):
        for entity_id in ids:
            self.audit.append({
                "entity_id": entity_id,
                "field": "status",
                "old_value": old_value,
                "new_value": new_value,
                "actor": actor,
            })


def test_apply_requires_exact_confirmations_fresh_backup_and_target(tmp_path):
    plan = _valid_plan([_row("a")])
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    with pytest.raises(MigrationRefusal, match="plan SHA-256 confirmation"):
        apply_plan(
            FakeStore([_row("a")]),
            plan,
            plan_sha256="wrong",
            backup=backup,
            confirm_target="wrong",
            now=NOW,
            restore_validator=lambda _artifact: None,
        )

    plan_sha = _artifact_sha(plan)
    with pytest.raises(MigrationRefusal, match="target confirmation"):
        apply_plan(
            FakeStore([_row("a")]),
            plan,
            plan_sha256=plan_sha,
            backup=backup,
            confirm_target="wrong",
            now=NOW,
            restore_validator=lambda _artifact: None,
        )


def test_apply_refuses_stale_or_tampered_backup(tmp_path):
    plan = _valid_plan([_row("a")])
    plan_sha = _artifact_sha(plan)
    stale = _valid_backup(tmp_path, plan["target_fingerprint"])
    stale.manifest["completed_at"] = "2026-07-14T10:00:00Z"
    stale = BackupEvidence(
        manifest=stale.manifest,
        manifest_sha256=_artifact_sha(stale.manifest),
        artifact_root=stale.artifact_root,
    )
    with pytest.raises(MigrationRefusal, match="stale"):
        apply_plan(
            FakeStore([_row("a")]), plan,
            plan_sha256=plan_sha, backup=stale,
            confirm_target=plan["target_fingerprint"], now=NOW,
            restore_validator=lambda _artifact: None,
        )

    tampered_root = tmp_path / "tampered-backup"
    tampered_root.mkdir()
    artifact = tampered_root / "postgres.dump"
    artifact.write_bytes(b"changed")
    tampered_manifest = dict(stale.manifest)
    tampered_manifest["completed_at"] = "2026-07-14T12:00:01Z"
    tampered = BackupEvidence(
        manifest=tampered_manifest,
        manifest_sha256=_artifact_sha(tampered_manifest),
        artifact_root=tampered_root,
    )
    with pytest.raises(MigrationRefusal, match="artifact hash"):
        apply_plan(
            FakeStore([_row("a")]), plan,
            plan_sha256=plan_sha, backup=tampered,
            confirm_target=plan["target_fingerprint"], now=NOW,
            restore_validator=lambda _artifact: None,
        )


def test_apply_rechecks_rows_updates_once_and_audits_plan_hash(tmp_path):
    plan = _valid_plan([_row("a"), _row("b")])
    plan_sha = _artifact_sha(plan)
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = FakeStore([_row("a"), _row("b")])
    report = apply_plan(
        store,
        plan,
        plan_sha256=plan_sha,
        backup=backup,
        confirm_target=plan["target_fingerprint"],
        now=NOW,
        restore_validator=lambda _artifact: None,
    )
    assert report["result"] == "applied"
    assert report["updated_ids"] == ["a", "b"]
    assert {row["old_value"] for row in store.audit} == {"null"}
    assert {row["new_value"] for row in store.audit} == {"published"}
    assert all(plan_sha in row["actor"] for row in store.audit)
    assert store.locked == LOCK_NAME


def test_apply_is_idempotent_only_with_matching_audit(tmp_path):
    plan = _valid_plan([_row("a")])
    plan_sha = _artifact_sha(plan)
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = FakeStore([_row("a")])
    kwargs = {
        "plan_sha256": plan_sha,
        "backup": backup,
        "confirm_target": plan["target_fingerprint"],
        "now": NOW,
        "restore_validator": lambda _artifact: None,
    }
    first = apply_plan(store, plan, **kwargs)
    second = apply_plan(store, plan, **kwargs)
    assert first["result"] == "applied"
    assert second["result"] == "already-applied"
    assert len(store.audit) == 1


def test_apply_refuses_missing_row_candidate_or_status_drift(tmp_path):
    plan = _valid_plan([_row("a"), _row("b")])
    plan_sha = _artifact_sha(plan)
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    with pytest.raises(MigrationRefusal, match="planned IDs are missing"):
        apply_plan(
            FakeStore([_row("a")]), plan,
            plan_sha256=plan_sha, backup=backup,
            confirm_target=plan["target_fingerprint"], now=NOW,
            restore_validator=lambda _artifact: None,
        )
    with pytest.raises(MigrationRefusal, match="candidate drift"):
        apply_plan(
            FakeStore([_row("a", source=[]), _row("b")]), plan,
            plan_sha256=plan_sha, backup=backup,
            confirm_target=plan["target_fingerprint"], now=NOW,
            restore_validator=lambda _artifact: None,
        )
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
```

Expected: FAIL because apply validation/store methods do not exist.

- [ ] **Step 3: Implement backup revalidation, PostgreSQL store, and apply report**

Add these core functions to `scripts/migrate_entity_status.py`:

```python
@dataclass(frozen=True)
class BackupEvidence:
    manifest: dict[str, object]
    manifest_sha256: str
    artifact_root: Path


def audit_actor(prefix: str, plan_sha256: str) -> str:
    return f"entity-status:{prefix}:{PUBLICATION_POLICY_REVISION}:{plan_sha256}"


def validate_backup_manifest(
    backup: BackupEvidence, *,
    expected_target: str, now: datetime, require_fresh: bool,
) -> Path:
    manifest = backup.manifest
    if backup.manifest_sha256 != sha256_bytes(canonical_json_bytes(manifest)):
        raise MigrationRefusal("backup manifest hash mismatch")
    if manifest.get("schema") != "vinhlong360-pg-backup-v1":
        raise MigrationRefusal("backup schema mismatch")
    if manifest.get("target_fingerprint") != expected_target:
        raise MigrationRefusal("backup target mismatch")
    artifact_info = manifest.get("artifact")
    if not isinstance(artifact_info, dict):
        raise MigrationRefusal("backup artifact metadata missing")
    artifact_root = backup.artifact_root.resolve()
    artifact = (artifact_root / str(artifact_info.get("path", ""))).resolve()
    if artifact.parent != artifact_root or not artifact.is_file():
        raise MigrationRefusal("backup artifact path is invalid")
    if sha256_file(artifact) != artifact_info.get("sha256"):
        raise MigrationRefusal("backup artifact hash mismatch")
    validation = manifest.get("validation")
    if not isinstance(validation, dict) or validation.get("pg_restore_list") is not True:
        raise MigrationRefusal("backup restore-list validation is missing")
    if validation.get("required_tables") != ["entities", "entity_changes"]:
        raise MigrationRefusal("backup required-table evidence mismatch")
    if require_fresh:
        completed = parse_utc(str(manifest.get("completed_at", "")))
        max_age = int(manifest.get("max_age_seconds", 0))
        age = (now - completed).total_seconds()
        if max_age <= 0 or age < 0 or age > max_age:
            raise MigrationRefusal("backup evidence is stale")
    return artifact


def validate_restore_artifact(path: Path, runner=subprocess.run) -> None:
    result = runner(
        ["pg_restore", "--list", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise MigrationRefusal("pg_restore --list revalidation failed")
    missing = [
        table for table in ("entities", "entity_changes")
        if table not in result.stdout
    ]
    if missing:
        raise MigrationRefusal(
            f"backup revalidation missing tables: {', '.join(missing)}"
        )
```

Implement `PostgresPublicationStore` methods with parameterized psycopg2 SQL:

```python
def target_identity(self):
    return read_target_identity(self.cursor)

def schema_columns(self):
    self.cursor.execute(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'entities' "
        "ORDER BY column_name"
    )
    return [(row[0], row[1], row[2]) for row in self.cursor.fetchall()]

def acquire_lock(self, name):
    self.cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (name,))

def rows_for_update(self, ids):
    self.cursor.execute(
        "SELECT * FROM entities WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
        (ids,),
    )
    names = [item[0] for item in self.cursor.description]
    return [dict(zip(names, row)) for row in self.cursor.fetchall()]

def audit_ids(self, actor, old_value, new_value):
    self.cursor.execute(
        "SELECT entity_id FROM entity_changes "
        "WHERE field = 'status' AND actor = %s "
        "AND old_value = %s AND new_value = %s",
        (actor, old_value, new_value),
    )
    return {row[0] for row in self.cursor.fetchall()}

def update_to_published(self, ids):
    self.cursor.execute(
        "UPDATE entities SET status = 'published' "
        "WHERE id = ANY(%s) AND status IS NULL RETURNING id",
        (ids,),
    )
    return sorted(row[0] for row in self.cursor.fetchall())

def insert_status_audit(self, ids, actor, old_value, new_value):
    self.cursor.executemany(
        "INSERT INTO entity_changes "
        "(entity_id, field, old_value, new_value, actor) "
        "VALUES (%s, 'status', %s, %s, %s)",
        [(entity_id, old_value, new_value, actor) for entity_id in ids],
    )

def status_counts(self):
    self.cursor.execute(
        "SELECT COUNT(*) FILTER (WHERE status = 'published'), "
        "COUNT(*) FILTER (WHERE status IS NULL) FROM entities"
    )
    row = self.cursor.fetchone()
    return {"published": int(row[0]), "null": int(row[1])}
```

Implement `apply_plan` with this exact interface and state transition:

```python
def apply_plan(
    store,
    plan: dict[str, object],
    *,
    plan_sha256: str,
    backup: BackupEvidence,
    confirm_target: str,
    now: datetime,
    restore_validator,
) -> dict[str, object]:
    if plan.get("schema") != PLAN_SCHEMA:
        raise MigrationRefusal("plan schema mismatch")
    if plan.get("policy_revision") != PUBLICATION_POLICY_REVISION:
        raise MigrationRefusal("plan policy mismatch")
    if plan_sha256 != sha256_bytes(canonical_json_bytes(plan)):
        raise MigrationRefusal("plan SHA-256 confirmation mismatch")
    target = plan.get("target_fingerprint")
    if type(target) is not str or confirm_target != target:
        raise MigrationRefusal("target confirmation mismatch")
    created_at = parse_utc(str(plan.get("created_at", "")))
    max_age = int(plan.get("max_age_seconds", 0))
    age = (now - created_at).total_seconds()
    if max_age <= 0 or age < 0 or age > max_age:
        raise MigrationRefusal("plan is stale")

    artifact = validate_backup_manifest(
        backup,
        expected_target=target,
        now=now,
        require_fresh=True,
    )
    restore_validator(artifact)

    store.acquire_lock(LOCK_NAME)
    identity = store.target_identity()
    if target_fingerprint(identity) != target:
        raise MigrationRefusal("connected target drift")
    columns = store.schema_columns()
    if schema_fingerprint(columns) != plan.get("schema_fingerprint"):
        raise MigrationRefusal("entity schema drift")

    planned_ids = plan.get("candidate_ids")
    if not isinstance(planned_ids, list) or any(type(item) is not str for item in planned_ids):
        raise MigrationRefusal("plan candidate IDs are invalid")
    if planned_ids != sorted(set(planned_ids)):
        raise MigrationRefusal("plan candidate IDs are not canonical")
    if len(planned_ids) != plan.get("candidate_count"):
        raise MigrationRefusal("plan candidate count mismatch")
    if candidate_id_hash(planned_ids) != plan.get("candidate_sha256"):
        raise MigrationRefusal("plan candidate hash mismatch")

    rows = store.rows_for_update(planned_ids)
    row_ids = [row.get("id") for row in rows]
    if row_ids != planned_ids:
        raise MigrationRefusal("planned IDs are missing or reordered")

    actor = audit_actor("apply", plan_sha256)
    statuses = [row.get("status") for row in rows]
    if statuses and all(status == "published" for status in statuses):
        if store.audit_ids(actor, "null", "published") != set(planned_ids):
            raise MigrationRefusal("published rows lack apply audit ownership")
        if store.status_counts() != plan.get("expected_after"):
            raise MigrationRefusal("already-applied global count drift")
        return {
            "schema": APPLY_SCHEMA,
            "policy_revision": PUBLICATION_POLICY_REVISION,
            "result": "already-applied",
            "target_fingerprint": target,
            "schema_fingerprint": plan["schema_fingerprint"],
            "plan_sha256": plan_sha256,
            "backup_manifest_sha256": backup.manifest_sha256,
            "candidate_ids": planned_ids,
            "candidate_count": len(planned_ids),
            "candidate_sha256": candidate_id_hash(planned_ids),
            "expected_before": plan["expected_before"],
            "expected_after": plan["expected_after"],
            "updated_ids": [],
            "started_at": utc_text(now),
            "completed_at": utc_text(now),
        }
    if any(status is not None for status in statuses):
        raise MigrationRefusal("candidate status drift")
    if store.status_counts() != plan.get("expected_before"):
        raise MigrationRefusal("pre-apply global count drift")

    eligible_ids = sorted(
        str(row["id"])
        for row in rows
        if decide_publication_candidate(row).eligible
    )
    if eligible_ids != planned_ids:
        raise MigrationRefusal("candidate drift")
    if candidate_id_hash(eligible_ids) != plan.get("candidate_sha256"):
        raise MigrationRefusal("candidate hash drift")

    updated_ids = store.update_to_published(planned_ids)
    if updated_ids != planned_ids:
        raise MigrationRefusal("status update count drift")
    store.insert_status_audit(updated_ids, actor, "null", "published")
    if store.status_counts() != plan.get("expected_after"):
        raise MigrationRefusal("post-apply global count drift")
    return {
        "schema": APPLY_SCHEMA,
        "policy_revision": PUBLICATION_POLICY_REVISION,
        "result": "applied",
        "target_fingerprint": target,
        "schema_fingerprint": plan["schema_fingerprint"],
        "plan_sha256": plan_sha256,
        "backup_manifest_sha256": backup.manifest_sha256,
        "candidate_ids": planned_ids,
        "candidate_count": len(planned_ids),
        "candidate_sha256": candidate_id_hash(planned_ids),
        "expected_before": plan["expected_before"],
        "expected_after": plan["expected_after"],
        "updated_ids": updated_ids,
        "started_at": utc_text(now),
        "completed_at": utc_text(now),
    }
```

The CLI `apply` command must require:

```text
--target pg
--database-url-env <non-default env>
--plan <immutable plan path>
--backup-manifest <manifest path>
--confirm-target <exact fingerprint>
--confirm-plan-sha256 <exact digest>
--report-out <new path>
```

Set the psycopg2 connection to `SERIALIZABLE`, pass `validate_restore_artifact` as the production `restore_validator`, write the apply report only after the connection context commits, and refuse overwriting an existing report.

- [ ] **Step 4: Run GREEN, unsafe-CLI refusals, and lint**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status.py tests/test_backup_data.py -q
python scripts/migrate_entity_status.py apply --target sqlite --database-url-env X --plan x --backup-manifest y --confirm-target z --confirm-plan-sha256 q --report-out r
if ($LASTEXITCODE -eq 0) { throw "SQLite apply was accepted" }
python -m ruff check scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
```

Expected: tests pass; unsafe CLI fails before connection; Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
git commit -m "feat: apply publication plans transactionally"
```

### Task 8: Implement drift-safe atomic rollback

**Files:**
- Modify: `scripts/migrate_entity_status.py`
- Modify: `tests/test_migrate_entity_status.py`

- [ ] **Step 1: Write failing rollback success, refusal, and idempotency tests**

Add the import at module scope, then add the method inside `FakeStore`:

```python
from scripts.migrate_entity_status import rollback_apply


def rollback_to_null(self, ids):
    changed = []
    for entity_id in ids:
        if self.rows[entity_id]["status"] == "published":
            self.rows[entity_id]["status"] = None
            changed.append(entity_id)
    return changed
```

Add tests:

```python
def test_rollback_restores_only_apply_owned_unchanged_rows(tmp_path):
    plan = _valid_plan([_row("a"), _row("b")])
    plan_sha = _artifact_sha(plan)
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = FakeStore([_row("a"), _row("b")])
    apply_report = apply_plan(
        store, plan, plan_sha256=plan_sha, backup=backup,
        confirm_target=plan["target_fingerprint"], now=NOW,
        restore_validator=lambda _artifact: None,
    )
    report = rollback_apply(
        store,
        apply_report,
        apply_report_sha256=_artifact_sha(apply_report),
        backup=backup,
        confirm_target=plan["target_fingerprint"],
        now=datetime(2026, 7, 14, 12, 20, tzinfo=timezone.utc),
    )
    assert report["result"] == "rolled-back"
    assert report["restored_ids"] == ["a", "b"]
    assert all(store.rows[entity_id]["status"] is None for entity_id in ("a", "b"))


def test_rollback_aborts_on_manual_status_drift(tmp_path):
    plan = _valid_plan([_row("a")])
    plan_sha = _artifact_sha(plan)
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = FakeStore([_row("a")])
    apply_report = apply_plan(
        store, plan, plan_sha256=plan_sha, backup=backup,
        confirm_target=plan["target_fingerprint"], now=NOW,
        restore_validator=lambda _artifact: None,
    )
    store.rows["a"]["status"] = "verified"
    with pytest.raises(MigrationRefusal, match="rollback drift"):
        rollback_apply(
            store, apply_report,
            apply_report_sha256=_artifact_sha(apply_report),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=datetime(2026, 7, 14, 12, 20, tzinfo=timezone.utc),
        )


def test_rollback_requires_matching_apply_audit(tmp_path):
    plan = _valid_plan([_row("a")])
    plan_sha = _artifact_sha(plan)
    backup = _valid_backup(tmp_path, plan["target_fingerprint"])
    store = FakeStore([_row("a", status="published")])
    fake_report = _valid_apply_report(plan, plan_sha, backup.manifest_sha256)
    with pytest.raises(MigrationRefusal, match="apply audit ownership"):
        rollback_apply(
            store, fake_report,
            apply_report_sha256=_artifact_sha(fake_report),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=datetime(2026, 7, 14, 12, 20, tzinfo=timezone.utc),
        )
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
```

Expected: FAIL because rollback interfaces do not exist.

- [ ] **Step 3: Implement rollback ownership checks and report**

Add to `PostgresPublicationStore`:

```python
def rollback_to_null(self, ids):
    self.cursor.execute(
        "UPDATE entities SET status = NULL "
        "WHERE id = ANY(%s) AND status = 'published' RETURNING id",
        (ids,),
    )
    return sorted(row[0] for row in self.cursor.fetchall())
```

Implement `rollback_apply` with this exact interface and ownership check:

```python
def rollback_apply(
    store,
    apply_report: dict[str, object],
    *,
    apply_report_sha256: str,
    backup: BackupEvidence,
    confirm_target: str,
    now: datetime,
) -> dict[str, object]:
    if apply_report.get("schema") != APPLY_SCHEMA:
        raise MigrationRefusal("apply report schema mismatch")
    if apply_report.get("result") != "applied":
        raise MigrationRefusal("rollback requires an applied report")
    if apply_report_sha256 != sha256_bytes(canonical_json_bytes(apply_report)):
        raise MigrationRefusal("apply report SHA-256 mismatch")
    target = apply_report.get("target_fingerprint")
    if type(target) is not str or confirm_target != target:
        raise MigrationRefusal("target confirmation mismatch")
    if backup.manifest_sha256 != apply_report.get("backup_manifest_sha256"):
        raise MigrationRefusal("backup manifest mismatch")
    validate_backup_manifest(
        backup,
        expected_target=target,
        now=now,
        require_fresh=False,
    )

    candidate_ids = apply_report.get("candidate_ids")
    if not isinstance(candidate_ids, list) or any(type(item) is not str for item in candidate_ids):
        raise MigrationRefusal("apply report candidate IDs are invalid")
    if candidate_ids != sorted(set(candidate_ids)):
        raise MigrationRefusal("apply report candidate IDs are not canonical")
    if len(candidate_ids) != apply_report.get("candidate_count"):
        raise MigrationRefusal("apply report candidate count mismatch")
    if candidate_id_hash(candidate_ids) != apply_report.get("candidate_sha256"):
        raise MigrationRefusal("apply report candidate hash mismatch")

    store.acquire_lock(LOCK_NAME)
    if target_fingerprint(store.target_identity()) != target:
        raise MigrationRefusal("connected target drift")
    if schema_fingerprint(store.schema_columns()) != apply_report.get("schema_fingerprint"):
        raise MigrationRefusal("entity schema drift")

    rows = store.rows_for_update(candidate_ids)
    if [row.get("id") for row in rows] != candidate_ids:
        raise MigrationRefusal("rollback IDs are missing or reordered")
    plan_sha = apply_report.get("plan_sha256")
    if type(plan_sha) is not str or len(plan_sha) != 64:
        raise MigrationRefusal("apply report plan hash is invalid")
    apply_actor = audit_actor("apply", plan_sha)
    rollback_actor = audit_actor("rollback", plan_sha)
    statuses = [row.get("status") for row in rows]

    if statuses and all(status is None for status in statuses):
        if store.audit_ids(rollback_actor, "published", "null") != set(candidate_ids):
            raise MigrationRefusal("NULL rows lack rollback audit ownership")
        if store.status_counts() != apply_report.get("expected_before"):
            raise MigrationRefusal("already-rolled-back global count drift")
        return {
            "schema": ROLLBACK_SCHEMA,
            "policy_revision": PUBLICATION_POLICY_REVISION,
            "result": "already-rolled-back",
            "target_fingerprint": target,
            "apply_report_sha256": apply_report_sha256,
            "backup_manifest_sha256": backup.manifest_sha256,
            "restored_ids": [],
            "restored_count": 0,
            "completed_at": utc_text(now),
        }
    if any(status != "published" for status in statuses):
        raise MigrationRefusal("rollback drift")
    if store.audit_ids(apply_actor, "null", "published") != set(candidate_ids):
        raise MigrationRefusal("apply audit ownership mismatch")
    if store.status_counts() != apply_report.get("expected_after"):
        raise MigrationRefusal("pre-rollback global count drift")

    restored_ids = store.rollback_to_null(candidate_ids)
    if restored_ids != candidate_ids:
        raise MigrationRefusal("rollback update count drift")
    store.insert_status_audit(restored_ids, rollback_actor, "published", "null")
    if store.status_counts() != apply_report.get("expected_before"):
        raise MigrationRefusal("post-rollback global count drift")
    return {
        "schema": ROLLBACK_SCHEMA,
        "policy_revision": PUBLICATION_POLICY_REVISION,
        "result": "rolled-back",
        "target_fingerprint": target,
        "apply_report_sha256": apply_report_sha256,
        "backup_manifest_sha256": backup.manifest_sha256,
        "restored_ids": restored_ids,
        "restored_count": len(restored_ids),
        "completed_at": utc_text(now),
    }
```

The `rollback` CLI must require:

```text
--target pg
--database-url-env <non-default env>
--apply-report <path>
--backup-manifest <path>
--confirm-target <exact fingerprint>
--report-out <new path>
```

Use `SERIALIZABLE`; write the report only after commit; never make a local SQLite/JSON change.

- [ ] **Step 4: Run GREEN and lint**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status.py -q
python -m ruff check scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
```

Expected: all rollback, apply, plan, and refusal tests pass; Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add scripts/migrate_entity_status.py tests/test_migrate_entity_status.py
git commit -m "feat: rollback publication plans safely"
```

## Phase 5: Prove PostgreSQL Semantics and Operational Boundaries

### Task 9: Add opt-in disposable PostgreSQL transaction tests

**Files:**
- Create: `tests/test_migrate_entity_status_postgres.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write the disposable PostgreSQL integration fixture and scenarios**

Create `tests/test_migrate_entity_status_postgres.py`:

```python
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import pytest

from scripts.migrate_entity_status import (
    BackupEvidence,
    LOCK_NAME,
    PostgresPublicationStore,
    apply_plan,
    build_plan,
    rollback_apply,
)
from scripts.postgres_target import canonical_json_bytes, sha256_bytes

pytestmark = pytest.mark.entity_status_postgres
TEST_URL = os.environ.get("ENTITY_STATUS_TEST_DATABASE_URL")
TEST_CONFIRM = os.environ.get("ENTITY_STATUS_TEST_CONFIRM")
NOW = datetime(2026, 7, 14, 12, 10, tzinfo=timezone.utc)


def _row_dicts(cursor):
    names = [item.name for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _backup_evidence(tmp_path: Path, target: str) -> BackupEvidence:
    root = tmp_path / "backup"
    root.mkdir()
    artifact = root / "postgres.dump"
    artifact.write_bytes(b"PGDMP-disposable-test")
    manifest = {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target,
        "database_identity": {},
        "started_at": "2026-07-14T12:00:00Z",
        "completed_at": "2026-07-14T12:00:01Z",
        "max_age_seconds": 3600,
        "artifact": {
            "path": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": ["entities", "entity_changes"],
            "listing_sha256": "a" * 64,
        },
        "policy_revision": "published-v1",
    }
    return BackupEvidence(
        manifest=manifest,
        manifest_sha256=sha256_bytes(canonical_json_bytes(manifest)),
        artifact_root=root,
    )


@pytest.fixture
def pg_schema():
    if not TEST_URL or not TEST_URL.startswith("postgresql://"):
        pytest.skip("set ENTITY_STATUS_TEST_DATABASE_URL to a disposable PostgreSQL database")
    if TEST_CONFIRM != "disposable":
        pytest.skip("set ENTITY_STATUS_TEST_CONFIRM=disposable for the disposable database")
    schema = f"entity_status_{uuid.uuid4().hex}"
    conn = psycopg2.connect(TEST_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema}"')
        cur.execute(f'SET search_path TO "{schema}"')
        cur.execute(
            "CREATE TABLE entities ("
            "id TEXT PRIMARY KEY, type TEXT NOT NULL, status TEXT, verified INTEGER, "
            "attributes JSONB DEFAULT '{}'::jsonb, source JSONB DEFAULT '[]'::jsonb)"
        )
        cur.execute(
            "CREATE TABLE entity_changes ("
            "id BIGSERIAL PRIMARY KEY, entity_id TEXT NOT NULL, field TEXT NOT NULL, "
            "old_value TEXT, new_value TEXT, actor TEXT, created_at TIMESTAMPTZ DEFAULT NOW())"
        )
    try:
        yield conn, schema
    finally:
        conn.rollback()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("RESET search_path")
            cur.execute(f'DROP SCHEMA "{schema}" CASCADE')
        conn.close()


def test_postgres_apply_audit_idempotency_and_rollback(pg_schema, tmp_path):
    conn, schema = pg_schema
    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{schema}"')
        cur.executemany(
            "INSERT INTO entities(id, type, status, verified, attributes, source) "
            "VALUES (%s, 'dish', NULL, 1, '{}'::jsonb, %s::jsonb)",
            [("a", '[{"url":"https://example.org/a"}]'),
             ("b", '[{"url":"https://example.org/b"}]')],
        )
    conn.commit()

    conn.autocommit = False
    conn.set_session(isolation_level="SERIALIZABLE")
    with conn.cursor() as cur:
        store = PostgresPublicationStore(cur)
        cur.execute("SELECT * FROM entities ORDER BY id")
        rows = _row_dicts(cur)
        plan = build_plan(
            rows=rows,
            identity=store.target_identity(),
            schema_columns=store.schema_columns(),
            created_at="2026-07-14T12:00:00Z",
            tool_source_revision="postgres-test",
        )
        plan_sha = sha256_bytes(canonical_json_bytes(plan))
        backup = _backup_evidence(tmp_path, plan["target_fingerprint"])
        applied = apply_plan(
            store,
            plan,
            plan_sha256=plan_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=NOW,
            restore_validator=lambda _artifact: None,
        )
    conn.commit()
    assert applied["result"] == "applied"
    assert applied["updated_ids"] == ["a", "b"]

    conn.set_session(isolation_level="SERIALIZABLE")
    with conn.cursor() as cur:
        store = PostgresPublicationStore(cur)
        repeated = apply_plan(
            store,
            plan,
            plan_sha256=plan_sha,
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=NOW,
            restore_validator=lambda _artifact: None,
        )
    conn.commit()
    assert repeated["result"] == "already-applied"
    assert repeated["updated_ids"] == []

    conn.set_session(isolation_level="SERIALIZABLE")
    with conn.cursor() as cur:
        store = PostgresPublicationStore(cur)
        rolled_back = rollback_apply(
            store,
            applied,
            apply_report_sha256=sha256_bytes(canonical_json_bytes(applied)),
            backup=backup,
            confirm_target=plan["target_fingerprint"],
            now=datetime(2026, 7, 14, 12, 20, tzinfo=timezone.utc),
        )
    conn.commit()
    assert rolled_back["result"] == "rolled-back"
    assert rolled_back["restored_ids"] == ["a", "b"]

    with conn.cursor() as cur:
        cur.execute("SELECT id, status FROM entities ORDER BY id")
        assert cur.fetchall() == [("a", None), ("b", None)]
        cur.execute(
            "SELECT old_value, new_value, COUNT(*) FROM entity_changes "
            "GROUP BY old_value, new_value ORDER BY old_value"
        )
        assert cur.fetchall() == [("null", "published", 2), ("published", "null", 2)]


def test_postgres_advisory_lock_excludes_a_second_transaction(pg_schema):
    _fixture_conn, _schema = pg_schema
    first = psycopg2.connect(TEST_URL)
    second = psycopg2.connect(TEST_URL)
    try:
        with first.cursor() as first_cur, second.cursor() as second_cur:
            first_cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (LOCK_NAME,))
            second_cur.execute("SELECT pg_try_advisory_xact_lock(hashtext(%s))", (LOCK_NAME,))
            assert second_cur.fetchone()[0] is False
            first.rollback()
            second_cur.execute("SELECT pg_try_advisory_xact_lock(hashtext(%s))", (LOCK_NAME,))
            assert second_cur.fetchone()[0] is True
    finally:
        first.rollback()
        second.rollback()
        first.close()
        second.close()
```

Register the marker in `pyproject.toml`:

```toml
markers =
    slow: long-running quality/retrieval tests that are not part of the default unit baseline
    integration: FastAPI/TestClient or service-level integration tests
    entity_status_postgres: requires ENTITY_STATUS_TEST_DATABASE_URL and ENTITY_STATUS_TEST_CONFIRM=disposable
```

- [ ] **Step 2: Run RED or record the safe local skip**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
```

Expected without both disposable-test variables: SKIP with the exact missing URL/confirmation reason. If both are explicitly supplied, expected initial result is FAIL until store/schema handling is complete.

- [ ] **Step 3: Make schema introspection and transaction setup work against the disposable schema**

Use `current_schema()` in `PostgresPublicationStore.schema_columns`:

```python
self.cursor.execute(
    "SELECT column_name, data_type, is_nullable "
    "FROM information_schema.columns "
    "WHERE table_schema = current_schema() AND table_name = 'entities' "
    "ORDER BY column_name"
)
return [(row[0], row[1], row[2]) for row in self.cursor.fetchall()]
```

The production CLI must keep the default `public` search path. Only the opt-in test fixture changes `search_path`, and only inside the disposable database.

- [ ] **Step 4: Run PostgreSQL evidence when available and mandatory unit regression**

Run:

```powershell
python -m pytest tests/test_migrate_entity_status.py tests/test_postgres_target.py tests/test_backup_data.py -q
python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
```

Expected: unit suite passes. PostgreSQL suite either passes against the explicitly disposable URL or skips with evidence that the URL is absent. Docker unavailability is not a failure and must be recorded; do not install or start infrastructure outside the user's current setup.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_migrate_entity_status_postgres.py pyproject.toml scripts/migrate_entity_status.py
git commit -m "test: verify publication migration on PostgreSQL"
```

### Task 10: Add the runbook, noindex guards, and full Stage A evidence

**Files:**
- Create: `docs/runbooks/entity-published-status-migration.md`
- Create: `tests/test_entity_status_migration_guardrails.py`

- [ ] **Step 1: Write failing source guard tests**

Create `tests/test_entity_status_migration_guardrails.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_migration_tool_is_postgresql_only_and_never_imports_project_db_singleton():
    source = (ROOT / "scripts" / "migrate_entity_status.py").read_text(encoding="utf-8")
    assert 'choices=("pg",)' in source or 'choices=["pg"]' in source
    assert "from database import db" not in source
    assert "web/data.json" not in source
    assert "vinhlong360.db" not in source


def test_global_noindex_default_and_authoritative_header_remain_enabled():
    config = (ROOT / "web-nuxt" / "nuxt.config.ts").read_text(encoding="utf-8")
    middleware = (
        ROOT / "web-nuxt" / "server" / "middleware" / "noindex.ts"
    ).read_text(encoding="utf-8")
    assert "process.env.NUXT_PUBLIC_SITE_NOINDEX !== 'false'" in config
    assert "X-Robots-Tag" in middleware
    assert "noindex, follow" in middleware


def test_runbook_requires_exact_stage_c_authorization_and_zero_write_rerun():
    runbook = (
        ROOT / "docs" / "runbooks" / "entity-published-status-migration.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "separate Stage C authorization",
        "confirm-target",
        "confirm-plan-sha256",
        "already-applied",
        "post-apply DB export artifact",
        "X-Robots-Tag: noindex, follow",
        "Do not import web/data.json",
    ):
        assert phrase in runbook
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_entity_status_migration_guardrails.py -q
```

Expected: FAIL because the runbook does not exist and CLI source guards are not finalized.

- [ ] **Step 3: Write the exact Stage B/C runbook**

The runbook must contain these sections and commands; every angle-bracket metavariable is supplied explicitly by the owner at execution time and never resolved from a repository default:

```markdown
# Entity Published-Status Migration Runbook

## Safety boundary

- Stage A changes code/tests only.
- Stage B requires an explicitly supplied PostgreSQL environment variable and performs backup + plan only.
- Stage C requires separate Stage C authorization for the exact target fingerprint, plan SHA-256, backup manifest SHA-256, candidate count, and candidate ID hash.
- Do not import web/data.json, write local SQLite first, change Nuxt noindex settings, deploy, or infer H1/H2 completion.

## Stage B: backup and plan

python scripts/backup_data.py --target pg --database-url-env <OWNER_SUPPLIED_ENV> --out-dir <NEW_BACKUP_DIR>
python scripts/migrate_entity_status.py plan --target pg --database-url-env <OWNER_SUPPLIED_ENV> --policy published-v1 --report-out <NEW_PLAN_PATH>

Review target fingerprint, schema fingerprint, candidate IDs/count/hash, every exclusion count, status groups, backup age/hash, and `X-Robots-Tag: noindex, follow`. Stop if any value is unexplained.

## Stage C: apply only after separate authorization

python scripts/migrate_entity_status.py apply --target pg --database-url-env <OWNER_SUPPLIED_ENV> --plan <PLAN_PATH> --backup-manifest <BACKUP_MANIFEST> --confirm-target <AUTHORIZED_TARGET> --confirm-plan-sha256 <AUTHORIZED_PLAN_SHA256> --report-out <NEW_APPLY_REPORT>

Re-run the exact apply command with a different new report path and require `already-applied` with zero audit/status writes.

Create a post-apply DB export artifact at a new path; do not overwrite tracked `web/data.json` in the production command session:

export DATABASE_URL="$(printenv <OWNER_SUPPLIED_ENV>)"
python scripts/export_data.py --dry-run --out <NEW_POST_APPLY_EXPORT_PATH>
python scripts/export_data.py --out <NEW_POST_APPLY_EXPORT_PATH>
unset DATABASE_URL

Record the export SHA-256 and counts in the Stage C evidence. Reconciliation into tracked `web/data.json` or any local SQLite store is a separate reviewed task.

## Rollback

python scripts/migrate_entity_status.py rollback --target pg --database-url-env <OWNER_SUPPLIED_ENV> --apply-report <APPLY_REPORT> --backup-manifest <BACKUP_MANIFEST> --confirm-target <AUTHORIZED_TARGET> --report-out <NEW_ROLLBACK_REPORT>

Rollback must abort on any manual/later status drift. Use the validated custom-format backup for disaster recovery if logical rollback cannot pass its ownership checks.
```

- [ ] **Step 4: Run the complete Stage A regression and capture safe skips**

Run serially:

```powershell
python -m pytest agent/tests/test_index_policy.py agent/tests/test_publication_status.py agent/tests/test_database.py agent/tests/test_admin_mutations.py agent/tests/test_kb_curation.py agent/tests/test_seo.py agent/tests/test_seo_structured.py tests/checks/test_hard_checks.py tests/test_export_data.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_entity_status_migration_guardrails.py -q
python -m pytest -q
python -m ruff check agent/public_entity_types.py agent/publication_status.py agent/index_policy.py agent/launch_evidence.py agent/database.py scripts/postgres_target.py scripts/backup_data.py scripts/migrate_entity_status.py scripts/checks/check_data_schema.py tests/test_postgres_target.py tests/test_backup_data.py tests/test_migrate_entity_status.py tests/test_entity_status_migration_guardrails.py
python -m pytest tests/test_migrate_entity_status_postgres.py -q -m entity_status_postgres
git status --short
```

Expected:

- focused and default pytest suites pass;
- Ruff exits 0;
- PostgreSQL integration passes or safely skips because `ENTITY_STATUS_TEST_DATABASE_URL` is absent;
- Docker/Nginx checks are recorded as unavailable if their executables are absent, without installation attempts;
- `git status --short` contains only the intended Stage A files before the task commit;
- no production/local project data, environment, `web/data.json`, noindex setting, deployment state, or original-worktree AI disclosure change is modified.

- [ ] **Step 5: Commit**

```powershell
git add docs/runbooks/entity-published-status-migration.md tests/test_entity_status_migration_guardrails.py
git commit -m "docs: operationalize publication status migration"
```

## Final Stage A Review Gate

After Task 10 and both reviewer passes:

- Confirm every task commit exists in order and the worktree is clean.
- Confirm all Critical and Important review findings are closed.
- Confirm the plan/apply/rollback CLI refuses SQLite, `DATABASE_URL`, missing explicit target env, stale/invalid backup, changed plan bytes, target/schema/candidate drift, and overwrite of evidence artifacts.
- Confirm persistence tests prove admin/upsert/import/export paths cannot erase `status` or `verified`.
- Confirm the repository SQLite hash is unchanged by tests.
- Confirm current data still has not been mutated; no backup or plan has been run against production.
- Confirm global `noindex` source evidence remains unchanged.
- Stop and request separately scoped Stage B target context. Stage A completion is not authorization for Stage B or Stage C.
