# Public Eligibility Boundary Implementation Plan

> STATUS: done

> RESULT: Implemented on `codex/public-eligibility-boundary`; focused verification passed with `298 passed, 1 xfailed`, Ruff and diff-check passed, and the full repository suite exited `0`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the ten public entity publication bypasses through one public API eligibility boundary.

**Architecture:** Keep internal database reads backward compatible. Add public-layer helper functions around the existing `_is_public()` predicate, then route every affected endpoint through those helpers before shaping or caching responses.

**Tech Stack:** Python 3.14, FastAPI, pytest, SQLite-compatible synthetic unit fixtures.

---

### Task 1: Encode the canonical eligibility predicate

**Files:**
- Modify: `agent/public_api.py:82-120`
- Create: `agent/tests/test_public_eligibility_boundary.py`

- [x] **Step 1: Write the failing predicate and batch tests**

```python
def test_is_public_rejects_boolean_and_integer_false():
    assert public_api._is_public({"status": "published", "verified": True}) is True
    assert public_api._is_public({"status": "provisional", "verified": True}) is False
    assert public_api._is_public({"status": "published", "verified": False}) is False
    assert public_api._is_public({"status": "published", "verified": 0}) is False


def test_get_public_entities_batch_filters_hidden(monkeypatch):
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda ids: {
        "ok": {"id": "ok", "verified": True},
        "draft": {"id": "draft", "status": "provisional", "verified": True},
        "unverified": {"id": "unverified", "verified": 0},
    })
    assert list(public_api._get_public_entities_batch(["ok", "draft", "unverified"])) == ["ok"]
```

- [x] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: FAIL because `_is_public()` accepts integer `0` and `_get_public_entities_batch()` does not exist.

- [x] **Step 3: Implement the minimal helpers**

```python
def _is_public(e: dict) -> bool:
    return e.get("status") != "provisional" and e.get("verified") not in (False, 0)


def _filter_public_entities(entities: list[dict]) -> list[dict]:
    return [entity for entity in entities if _is_public(entity)]


def _get_public_entities_batch(entity_ids: list[str]) -> dict[str, dict]:
    return {
        entity_id: entity
        for entity_id, entity in db.get_entities_batch(entity_ids).items()
        if _is_public(entity)
    }
```

- [x] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: PASS.

### Task 2: Protect place and facility projections

**Files:**
- Modify: `agent/public_api.py:1427-1638`
- Test: `agent/tests/test_public_eligibility_boundary.py`

- [x] **Step 1: Add failing behavior tests**

Add tests proving hidden place rows are omitted from `/places`, hidden facilities are omitted, hidden place parents return 404, and overview/day-plan children are filtered.

- [x] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: FAIL with hidden synthetic records present.

- [x] **Step 3: Add place-scoped helpers and wire endpoints**

```python
def _public_entities_by_place(place_id: str) -> list[dict]:
    return _filter_public_entities(db.entities_by_place(place_id))


def _public_facilities_by_place(place_id: str | None = None) -> list[dict]:
    return _filter_public_entities(db.facilities_by_place(place_id))
```

Use `_get_public_entity(place_id)` for the parent and the new helpers for child lists. Include `status` and `verified` in the `/places` query only for filtering, then return the original four public fields.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: PASS with public response shapes unchanged.

### Task 3: Protect search, featured, collection list/detail, trending, and comparison

**Files:**
- Modify: `agent/public_api.py:1100-1140`
- Modify: `agent/public_api.py:1730-1755`
- Modify: `agent/public_api.py:3050-3080`
- Modify: `agent/public_api.py:3160-3225`
- Modify: `agent/public_api.py:3275-3330`
- Test: `agent/tests/test_public_eligibility_boundary.py`

- [x] **Step 1: Add failing endpoint tests**

Encode that autocomplete passes `public_only=True` and that featured, collection list/detail, trending, and comparison preserve only public synthetic records or IDs.

- [x] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: FAIL because the current paths use unfiltered batch/search reads.

- [x] **Step 3: Wire the selected boundary**

Use `public_only=True` for autocomplete and `_get_public_entities_batch()` for all affected batch expansions. Preserve input order when shaping list responses.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: PASS.

### Task 4: Protect itinerary list, detail, and homepage projections

**Files:**
- Modify: `agent/public_api.py:1611-1642`
- Test: `agent/tests/test_public_eligibility_boundary.py`

- [x] **Step 1: Add failing itinerary tests**

```python
def test_itinerary_omits_hidden_entity_stops(monkeypatch):
    monkeypatch.setattr(public_api.db, "get_itinerary", lambda _id: {
        "id": "itinerary-1",
        "stops": [
            {"entityId": "public"},
            {"entityId": "hidden"},
            {"name": "Free-form stop"},
        ],
    })
    monkeypatch.setattr(public_api.db, "get_entities_batch", lambda _ids: {
        "public": {"id": "public", "name": "Public", "verified": True},
        "hidden": {"id": "hidden", "name": "Hidden", "status": "provisional"},
    })

    result = asyncio.run(public_api.get_itinerary("itinerary-1", Response()))

    assert [stop.get("entityId") for stop in result["stops"]] == ["public", None]
```

- [x] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: FAIL because hidden referenced stops remain and are enriched.

- [x] **Step 3: Filter before enrichment**

Resolve referenced IDs through `_get_public_entities_batch()` or the already-filtered homepage entity map. Drop referenced stops whose ID is absent from that public batch; preserve free-form stops. Apply the shared helper to list, detail, and homepage variants.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: PASS. Final boundary suite: 17 passed.

### Task 5: Focused and package verification

**Files:**
- Verify: `agent/public_api.py`
- Verify: `agent/tests/test_public_eligibility_boundary.py`

- [x] **Step 1: Run focused security tests**

Run: `python -m pytest agent/tests/test_public_eligibility_boundary.py -q`

Expected: all tests pass.

- [x] **Step 2: Run nearby API/database tests**

Run: `python -m pytest agent/tests/test_database.py agent/tests/test_qa_fixes.py agent/tests/test_upgrade_phase2.py agent/tests/test_upgrade_phase4.py agent/tests/test_upgrade_integration.py -q`

Expected: all tests pass or only previously documented baseline failures appear.

- [x] **Step 3: Run Ruff on changed Python files**

Run: `python -m ruff check agent/public_api.py agent/tests/test_public_eligibility_boundary.py`

Expected: no errors.

- [x] **Step 4: Run the repository test suite**

Run: `python -m pytest -q`

Expected: no new failures relative to the recorded baseline.

- [x] **Step 5: Inspect the final diff**

Run: `git diff -- agent/public_api.py agent/tests/test_public_eligibility_boundary.py docs/superpowers/specs/2026-07-12-public-eligibility-boundary-design.md docs/superpowers/plans/2026-07-12-public-eligibility-boundary.md docs/superpowers/plans/2026-07-12-security-remediation-30-60-90.md`

Expected: only the approved public eligibility batch and planning documents.
