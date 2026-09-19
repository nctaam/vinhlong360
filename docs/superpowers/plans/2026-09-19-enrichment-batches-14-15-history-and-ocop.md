# Deep Knowledge Enrichment (Batches 14 & 15: Historical Relics & OCOP Specialties) and Image Quality Enhancement

> STATUS: complete (2026-09-19) — Completed Batches 14 & 15 deep knowledge and image quality enrichment.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deepen entity knowledge in `web/data.json` for 50 high-priority entities (Batch 14: 25 Historical Relics & Architectural Monuments, Batch 15: 25 OCOP 4-5 Star Agricultural Products & Craft Specialties) using Google NotebookLM sources; enhance image metadata with accessible `image_alt` and polished `image_caption`; maintain Invariant B1 and update test suite hashes.

**Architecture:** Mined facts and metadata are staged through Python operational scripts (`scripts/ops/enrich_batch14_history_relics.py` and `scripts/ops/enrich_batch15_ocop_crafts.py`), verified against hard gates (`run_hard.py --all`, `check_image_hygiene.py`, `check_content_gates.py`, `check_content_voice.py`), machine learning texts regenerated, and canonical SHA-256 hashes synchronized across 4 Vitest suites.

**Tech Stack:** Python 3.14 (Ops scripts & Gate validators), TypeScript/Vitest (Frontend regression suites), Nuxt 3 (SSR web app), JSON Schema.

**Spec:** `docs/reports/2026-09-13-notebooklm-knowledge-sources-expansion.md` & `docs/reports/2026-09-13-notebooklm-deep-enrichment-report.md`.

## Global Constraints

- Keep `agent/data/vinhlong360.db` strictly read-only and invariant to SHA-256 `20ac61bf7d247d8df35bd20bfe11140cf6eebae0980de4af5720d5ed73add742` (Invariant B1).
- Zero tolerance for editorial violations: No fillers (R50.2), no old admin districts (R10.10/R45.1), no superlatives without numbers/dates (R50.7), no formula starts (R50.3/R45.1), no out-of-province names without qualification (R10.9).
- Maintain all functions under Cyclomatic Complexity <= 11 (hard ceiling 12).
- Verification gate: `python -u scripts/checks/run_hard.py --all` must return `sạch (hard=0, ratchet không tăng)` before any commit claim.
- Ensure all 50 entities have non-empty `image_caption` and accessible `image_alt` conforming to editorial gates.

---

### Task 1: Create and Run Batch 14 Enrichment (25 Historical Relics & Architectural Monuments)

**Files:**
- Create: `scripts/ops/enrich_batch14_history_relics.py`
- Test: `tests/ops/test_enrich_batch14_history_relics.py`
- Output: `outputs/enrichment_batch14_history_relics_log.json`
- Target: `web/data.json`

**Interfaces:**
- Consumes: `web/data.json` entities list.
- Produces: 25 entities enriched with `key_facts`, `hours`, `admission`, `travel_tip`, `source_citations`, `image_caption`, `image_alt`, `verified: True`, `verifiedAt: "2026-09-19"`.

- [x] **Step 1: Write the unit test for Batch 14 enrichment**

```python
# tests/ops/test_enrich_batch14_history_relics.py
import pytest
from scripts.ops.enrich_batch14_history_relics import BATCH14_DATA, apply_batch14_enrichment

def test_batch14_data_structure():
    assert len(BATCH14_DATA) == 25
    for eid, payload in BATCH14_DATA.items():
        assert "key_facts" in payload
        assert len(payload["key_facts"]) == 3
        assert "hours" in payload
        assert "admission" in payload
        assert "travel_tip" in payload
        assert "source_citations" in payload
        assert len(payload["source_citations"]) >= 1
        assert "image_caption" in payload
        assert "image_alt" in payload

def test_apply_batch14_enrichment():
    mock_entities = [{"id": "chua-tuyen-linh-mo-cay-bac", "name": "Chùa Tuyên Linh", "attributes": {}}]
    count, logs = apply_batch14_enrichment(mock_entities)
    assert count == 1
    assert mock_entities[0]["attributes"]["verified"] is True
    assert mock_entities[0]["attributes"]["verifiedAt"] == "2026-09-19"
    assert "image_alt" in mock_entities[0]["attributes"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_enrich_batch14_history_relics.py -v --basetemp=scratch/pytest_tmp`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.ops.enrich_batch14_history_relics'`

- [x] **Step 3: Implement `scripts/ops/enrich_batch14_history_relics.py`**

Implement complete dictionary `BATCH14_DATA` with all 25 historical relics & architectural monuments:
1. `chua-tuyen-linh-mo-cay-bac`
2. `chua-vam-ray-chua-phat-nam`
3. `di-tich-khao-co-luu-cu-ii`
4. `di-tich-cay-da-doi`
5. `duong-ho-chi-minh-tren-bien-ben-xuat-phat-thanh-phong`
6. `chua-krapoumchhouk-chral-chua-cha`
7. `khu-luu-niem-nguyen-thi-dinh`
8. `mo-va-khu-luu-niem-vo-truong-toan`
9. `nha-tho-mac-bac-tieu-can`
10. `nha-tho-la-ma-den-duc-me-hang-cuu-giup-la-ma`
11. `chua-van-phuoc-binh-dai`
12. `nha-tho-chanh-toa-tra-vinh-tra-vinh`
13. `lang-ong-lang-ong-che-nguyen-van-ton`
14. `khu-mo-than-nhan-danh-than-thoai-ngoc-hau`
15. `chua-shanghamangala-khmer-vung-liem`
16. `den-tho-bac-ho-tra-vinh`
17. `chua-co-nodol`
18. `chua-samrong-ek`
19. `chua-ky-son-khmer-loan-my`
20. `khu-di-tich-luu-niem-chu-tich-pham-hung`
21. `chua-ba-thien-hau-tra-vinh`
22. `dinh-trung-my`
23. `dinh-loc-thuan`
24. `dinh-tan-hoa`
25. `san-chim-chua-phat-lon-tra-vinh`

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_enrich_batch14_history_relics.py -v --basetemp=scratch/pytest_tmp`
Expected: PASS (2/2 tests passed)

- [x] **Step 5: Execute Batch 14 enrichment script on `web/data.json`**

Run: `python -u scripts/ops/enrich_batch14_history_relics.py`
Expected: "Successfully enriched 25 / 25 historical relics in Batch 14."

---

### Task 2: Create and Run Batch 15 Enrichment (25 OCOP Products & Craft Specialties)

**Files:**
- Create: `scripts/ops/enrich_batch15_ocop_crafts.py`
- Test: `tests/ops/test_enrich_batch15_ocop_crafts.py`
- Output: `outputs/enrichment_batch15_ocop_crafts_log.json`
- Target: `web/data.json`

**Interfaces:**
- Consumes: `web/data.json` entities list.
- Produces: 25 entities enriched with `key_facts`, `hours`, `admission`, `travel_tip`, `source_citations`, `image_caption`, `image_alt`, `verified: True`, `verifiedAt: "2026-09-19"`.

- [x] **Step 1: Write the unit test for Batch 15 enrichment**

```python
# tests/ops/test_enrich_batch15_ocop_crafts.py
import pytest
from scripts.ops.enrich_batch15_ocop_crafts import BATCH15_DATA, apply_batch15_enrichment

def test_batch15_data_structure():
    assert len(BATCH15_DATA) == 25
    for eid, payload in BATCH15_DATA.items():
        assert "key_facts" in payload
        assert len(payload["key_facts"]) == 3
        assert "hours" in payload
        assert "admission" in payload
        assert "travel_tip" in payload
        assert "source_citations" in payload
        assert len(payload["source_citations"]) >= 1
        assert "image_caption" in payload
        assert "image_alt" in payload

def test_apply_batch15_enrichment():
    mock_entities = [{"id": "buoi-da-xanh-ben-tre", "name": "Bưởi Da Xanh", "attributes": {}}]
    count, logs = apply_batch15_enrichment(mock_entities)
    assert count == 1
    assert mock_entities[0]["attributes"]["verified"] is True
    assert mock_entities[0]["attributes"]["verifiedAt"] == "2026-09-19"
    assert "image_alt" in mock_entities[0]["attributes"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ops/test_enrich_batch15_ocop_crafts.py -v --basetemp=scratch/pytest_tmp`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.ops.enrich_batch15_ocop_crafts'`

- [x] **Step 3: Implement `scripts/ops/enrich_batch15_ocop_crafts.py`**

Implement complete dictionary `BATCH15_DATA` with all 25 OCOP products & craft specialties:
1. `buoi-da-xanh-ben-tre`
2. `dua-sap-tra-vinh`
3. `mut-dua-sap-cam-hang`
4. `keo-dua-mo-cay-co-so-tuyet-phung`
5. `cu-cai-muoi-chit-sa`
6. `mam-bo-hoc-prohok`
7. `banh-tet-tu-quy-hai-ly`
8. `chom-chom-cau-ke`
9. `gao-sach-tom-lua-thanh-phu-ocop`
10. `hop-tac-xa-thuy-san-thanh-loi-ngheu-thanh-hai-ocop`
11. `mat-ong-rung-ban-nguyen-van-bao`
12. `ca-bong-lau-mot-nang-binh-dai`
13. `ca-doi-kho-mot-nang-binh-dai`
14. `ca-kho-dac-san-thanh-phong-ocop`
15. `hoa-cuc-mam-xoi-long-thoi`
16. `lang-nghe-bo-choi-my-an`
17. `lang-nghe-san-xuat-muoi-bao-thanh`
18. `lang-nghe-tieu-thu-cong-nghiep-ham-giang-tre-truc`
19. `muoi-bao-thanh`
20. `lap-xuong-ngoc-huong`
21. `buoi-da-xanh-giong-trom`
22. `cua-bien-va-ngheu-thanh-phu`
23. `banh-kep-thuy-kieu`
24. `bun-tuoi-an-dao`
25. `nuoc-khoang-thien-nhien-sao-bien-starfiwa`

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ops/test_enrich_batch15_ocop_crafts.py -v --basetemp=scratch/pytest_tmp`
Expected: PASS (2/2 tests passed)

- [x] **Step 5: Execute Batch 15 enrichment script on `web/data.json`**

Run: `python -u scripts/ops/enrich_batch15_ocop_crafts.py`
Expected: "Successfully enriched 25 / 25 OCOP products in Batch 15."

---

### Task 3: Image Hygiene Gate Enhancement & Regression Check

**Files:**
- Modify: `scripts/checks/check_image_hygiene.py`
- Test: `tests/checks/test_check_image_hygiene.py`

**Interfaces:**
- Consumes: `web/data.json` entities and `web-nuxt/public/img/entities/*.webp`.
- Produces: Validated R45.1 image hygiene report with `image_alt` checks for enriched entities.

- [x] **Step 1: Add unit tests for `image_alt` verification in `test_check_image_hygiene.py`**

Test that if `image_alt` is provided, it is checked for minimum length (>=10 chars), no fillers, and no old admin district names.

- [x] **Step 2: Run test to verify failure**

Run: `python -m pytest tests/checks/test_check_image_hygiene.py -v --basetemp=scratch/pytest_tmp`
Expected: FAIL on `image_alt` check helper not found or not invoked.

- [x] **Step 3: Update `scripts/checks/check_image_hygiene.py`**

Add `_check_alt_editorial(alt: str) -> list[str]` and validate `attributes.image_alt` if present. Keep cyclomatic complexity <= 11.

- [x] **Step 4: Run unit tests to verify pass**

Run: `python -m pytest tests/checks/test_check_image_hygiene.py -v --basetemp=scratch/pytest_tmp`
Expected: PASS

- [x] **Step 5: Run full hard check suite**

Run: `python -u scripts/checks/run_hard.py --all`
Expected: `✓ run_hard: sạch (hard=0, ratchet không tăng)`

---

### Task 4: Cryptographic Sync, Machine Learning Text Generation & Vitest Suites

**Files:**
- Modify: `web-nuxt/tests/challenger-homepage-stress.test.ts`
- Modify: `web-nuxt/tests/challenger-m3-subsystems-stress.test.ts`
- Modify: `web-nuxt/tests/home-editorial-e2e.test.ts`
- Modify: `web-nuxt/tests/subsystems-unification.test.ts`
- Target: `web-nuxt/public/llms-full.txt` and `web-nuxt/public/llms.txt`

**Interfaces:**
- Consumes: Updated `web/data.json`.
- Produces: New canonical SHA-256 hash synchronized into test files, updated `llms.txt` & `llms-full.txt`.

- [x] **Step 1: Regenerate machine learning texts**

Run: `python scripts/generate_llms_txt.py`
Expected: Regenerated `web-nuxt/public/llms-full.txt` and `web-nuxt/public/llms.txt`.

- [x] **Step 2: Compute new canonical SHA-256 hash of `web/data.json`**

Run: `python -c "import hashlib; print(hashlib.sha256(open('web/data.json', 'rb').read()).hexdigest())"`
Record new hash. Verify Invariant B1 `agent/data/vinhlong360.db` is strictly `20ac61bf7d247d8df35bd20bfe11140cf6eebae0980de4af5720d5ed73add742`.

- [x] **Step 3: Synchronize new canonical hash into 4 test files**

Update the hash string in:
1. `web-nuxt/tests/challenger-homepage-stress.test.ts`
2. `web-nuxt/tests/challenger-m3-subsystems-stress.test.ts`
3. `web-nuxt/tests/home-editorial-e2e.test.ts`
4. `web-nuxt/tests/subsystems-unification.test.ts`

- [x] **Step 4: Run Vitest and TypeScript typecheck**

Run: `npm test -- run`
Expected: 121/121 tests passed.
Run: `npm run typecheck`
Expected: 0 errors.

- [x] **Step 5: Run full verification suite**

Run: `python -u scripts/checks/run_hard.py --all`
Expected: `✓ run_hard: sạch (hard=0, ratchet không tăng)`
