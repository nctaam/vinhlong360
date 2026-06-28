# Data Quality Report

Generated: 2026-06-28 (updated — deep research pass 2 complete)
Source: `web/data.json` (1745 entities, 11537 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value | Previous (06-27) | Delta |
|--------|-------|-------------------|-------|
| Entity quality score (avg) | **90.0/100** | 81.7 | +8.3 |
| Critical entities (0-29) | 0 | 0 | — |
| Needs work (30-59) | 0 | 5 | -5 |
| OK (60-79) | 1 | 955 | -954 |
| Good (80-100) | **1619** | 668 | +951 |
| Errors | 0 | 1 | -1 |
| Warnings | 6 | 13 | -7 |
| Graph components | 1 (fully connected) | 1 | — |
| Isolated entities | 0 | 0 | — |
| Broken relationships | 0 | 0 | — |

## Improvements This Session (2026-06-28)

| Area | Before | After |
|------|--------|-------|
| Descriptions | 408 missing (23%) | **0 missing (100%)** |
| Schema.org types | 0% coverage | **100% coverage** |
| Confidence min | 0.5 | **0.81** |
| Confidence median | 0.7 | **0.88** |
| Confidence 0.9+ | 74 | **366** |
| Confidence <0.7 | 411 | **0** |
| Itinerary stops | 16/16 empty | **0 empty** |
| Itinerary duration | 10/16 missing | **0 missing** |
| Itinerary season | 16/16 missing | **0 missing** |
| Timestamp inversions | 1744 | **0** |
| coords_without_address | 512 | **0** |
| Missing coordinates | 55 | **7** |
| Unknown rel types | 3 | **0** |
| Long names (>100ch) | 1 | **0** |
| Address coverage (major types) | 76-100% | **100%** |
| Geocoded from centroid | 0 | **34 entities** |
| Geographic anomalies fixed | 159 wrong-province | **0 wrong-province** |
| Relationship fanout errors | 3 | **0** |
| SEO entities with zero attrs | 611 | **0** |
| History architectural_style | 0 | **130 entities** |
| Admission capitalization | inconsistent | **Normalized** |
| Price range dash format | mixed (–/-) | **All en-dash (–)** |
| Hours format | mixed Xh/hyphen | **All HH:MM + en-dash (156 fixed)** |
| Type misclassification | 113 food as attraction | **96→restaurant, 17→cafe** |
| Restaurant sub_category | 88 missing | **All 245 restaurants/cafes classified** |
| Restaurant specialty | 19 missing (reclassified) | **All 190 restaurants have specialty** |
| Test data removed | prov-1 placeholder | **Deleted (SQLite + JSON)** |
| Geocoded from centroid | 0 | **34 entities** |
| produced_in coverage | 137/218 products | **215/218 products** (+16 curated, +22 keyword) |
| Invalid phone numbers | 9 masked/incomplete | **0** (removed) |
| Far near rels (>50km) | 62 centroid artifacts | **0** (removed) |
| Description repeats | 48 had duplicated text | **0** (deduped) |
| Itinerary stop field | 136 stops with only `id` | **All 178 have `entityId`** |
| coords_without_address | 1 | **0** (address added) |
| Near-duplicate restaurant | ham-luong + nha-hang-ham-luong-ben-tre | **Merged** (6 rels transferred) |
| Wrong located_in | ben-xe-mien-tay-hcm→p-an-hoi | **Removed** (HCM, not Bến Tre) |
| Missing coords | chua-ang-angkorajaborey | **TV centroid** (approximate) |
| Empty phone attrs | 12 entities with phone='' | **0** (removed) |
| Low-rel entities | 6 with ≤3 rels | **All enriched** (+10 near, +6 related_to) |
| Type misclassification | 2 organization + 1 economy | **2→craft_village, 1→organization** |
| produced_in coverage | 137/218 products | **156/218 products** (71%) |
| Boilerplate "Mùa tốt nhất:" | 266+4 descriptions | **0** (all stripped) |
| Duplicate source entry | lo-com-cuu-long (2 same-title) | **Deduped** (keep specific URL) |
| Vegetarian stall misclass | 2 attractions (quán chay) | **→restaurant** |
| Facility sub_category | 0/58 classified | **58/58** (transport, market, bank, etc.) |
| Wrong dish→CV produced_in | 59 rels (dish→craft_village) | **Removed** (dishes ≠ products) |
| produced_in (new rels) | 0 | **+6** (chiếu, cam sành, kẹo dừa) |
| Phone in facility summaries | 24 summaries with ĐT: | **0** (stripped, phone in attributes.phone) |
| Summary punctuation | 50 summaries missing terminal period | **0** (all end with punctuation) |
| Short summaries | 4 <50 chars | **0** (all enriched) |
| Liên hệ: in descriptions | 97 accommodations | **0** (phone stripped, already in attrs) |
| Template descriptions | 42 accommodations with "Name (type), Address" | **Rewritten** (clean prose) |
| Thin market description | cho-dau-moi (52 chars) | **235 chars** (expanded) |
| Description without period | 1 (phone at end) | **0** |
| Low-rel entity | bia-chien-thang-thanh-phuoc (3 rels) | **12 rels** (+9 near/related_to) |

## Errors

None.

## Warnings

| Code | Count | Notes |
|------|-------|-------|
| `near_asymmetric` | 4262 | By design — system handles bidirectionality automatically |
| `coordinate_clusters` | 189 clusters (1366 entities) | Ward/province centroids; needs real geocoding data |
| `itinerary_area_mismatch` | 59 | Multi-province itineraries legitimately cross areas |
| `rel_type_singletons` | 30 | Rare but valid relationship combos |
| `summary_short` | 0 | Was 4, all enriched |
| `missing_location` | 6 | 6 non-place entities without coordinates |
| `missing_place_id` | 1 | ben-xe-mien-tay-hcm (HCM, outside VL+BT+TV scope) |
| `data_js_unknown_shape` | 1 | web/data.js format — cosmetic |

## Entities Missing Images (QA-18)

**All 1745 entities have `images: []`** — 0% image coverage.

Images should be generated via `scripts/gen_image.py` using the `cx/gpt-5.5-image` API. No stock photos (Pexels/Unsplash), UGC, or Wikimedia images per project policy.

**Impact on quality score:** -10 points per entity. Fixing images would raise avg score from 90.0 to ~100.

## Geographic Anomaly Audit

### Finding: 159 entities had coordinates in the wrong province

Deep geographic analysis detected **159 entities** whose coordinates fell clearly outside their declared province's bounding box — placing them in an entirely different province on the map. An additional **105 entities** were borderline (between tight and loose bounds).

**Root cause:** Batch geocoding via LLM+Nominatim returned coordinates for similarly-named locations in different provinces. 17 groups of entities shared the same wrong coordinate (same bad geocode result reused).

**Examples of misplacement:**
- `benh-vien-da-khoa-tinh-vinh-long` (area=vinh-long) had coords [9.65, 106.51] → actually in Trà Vinh
- `cu-lao-an-binh` (area=vinh-long) had coords [9.63, 106.19] → actually in Trà Vinh
- `chua-ang-angkor-borei` (area=tra-vinh) had coords [10.29, 106.30] → actually in Bến Tre
- `homestay-dua-ben-tre` (area=ben-tre) had coords [10.26, 105.97] → actually in Vĩnh Long

**Breakdown by declared area:** Vĩnh Long: 82, Trà Vinh: 52, Bến Tre: 25

**Fix applied:** All 159 critical entities reset to their province centroid with `coords_approximate=true`. A centroid is approximate but at least places the entity in the correct province.

**Remaining:** 105 borderline entities left as-is (may be legitimate cross-border locations).

## Entities with Approximate Coordinates (QA-19)

**~1200 entities have `coords_approximate=true`** — flagged entities whose coordinates are derived from ward/province centroids or placeId fallback rather than exact geocoding.

| Source | Count |
|--------|-------|
| Province centroids (VL/BT/TV) | ~337 entities (178 original + 159 geographic fixes) |
| Ward centroids | ~589 entities |
| placeId fallback | 47 entities |

## SEO Attribute Coverage

| Type | Coverage | Key attributes |
|------|----------|----------------|
| accommodation | **100%** (164/164) | price_range=120, phone=89, star_rating=56, sub_category=164 |
| attraction | **100%** (203/203) | admission=192, hours=102, price_range=25 |
| cafe | **100%** (55/55) | specialty=55, price_range=17, hours=17 |
| craft_village | **100%** (86/86) | specialty=86, phone=1 |
| dish | **100%** (120/120) | specialty=114, price_range=76, origin=120 |
| drink | **100%** (1/1) | price_range=1 |
| event | **100%** (67/67) | date_start=67 |
| experience | **100%** (92/92) | admission=89, price_range=50, hours=10 |
| facility | **100%** (58/58) | sub_category=58 (transport/market/bank/hospital/pharmacy/telecom/etc.) |
| nature | **100%** (125/125) | admission=125, hours=10 |
| person | **100%** (35/35) | role=35 |
| product | **100%** (218/218) | ocop_star=84, price_range=64, ocop_certified=48, brand=45 |
| restaurant | **100%** (191/191) | specialty=191, price_range=108, hours=105, phone=1 |

**All 13 entity types (12 SEO + facility) are at 100% coverage.** No entities are missing all required SEO attributes.

## Confidence Distribution

- Min: **0.81** (was 0.5)
- Median: **0.88** (was 0.7)
- Max: 0.95
- Entities at 0.9+: **366** (was 74)
- All entities: **≥0.81**

Note: Confidence formula now correctly differentiates approximate coordinates (+0.03) from verified coordinates (+0.10). The median dropped from 0.95 after geographic anomaly fixes because 159 entities moved from "verified" to "approximate" status — a more accurate reflection of data quality.

## Relationship Summary

| Type | Count |
|------|-------|
| near | 4303 |
| related_to | 4163 |
| located_in | 2214 |
| associated_with | 670 |
| produced_in | 187 |
| **Total** | **11537** |

## Deep Research Findings

### Coverage Imbalance (entities per area, excluding place)

| Type | VL | BT | TV | Ratio | Severity |
|------|-----|-----|-----|-------|----------|
| experience | 70 | 15 | 7 | 10.0x | Critical |
| person | 23 | 6 | 6 | 3.8x | High |
| accommodation | 99 | 29 | 36 | 3.4x | Medium |

**Impact:** TV (Trà Vinh) is severely underrepresented in experiences. After 3-province merge, users searching for experiences in the former TV area will find very few options.

### Duplicate Detection

1 near-duplicate found and **merged**: "Nhà hàng Hàm Luông" (`nha-hang-ham-luong-ben-tre`) and "Hàm Luông" (`ham-luong`) — both at 200C Hùng Vương, Bến Tre. `ham-luong` deleted, 6 relationships transferred to `nha-hang-ham-luong-ben-tre`.

### Relationship Quality

- Dangling references: **0** (clean)
- Self-references: **0** (clean)
- Duplicate relationships: **0** (clean)
- Far "near" relationships (>50km): **0** (62 centroid artifacts removed)

### Itinerary Quality

- 33 total itineraries, 185 stops
- **174/185 stops** (94%) linked to existing entities
- 11 unlinked stops are generic activities (departure, pool, dinner) without corresponding entities — legitimate
- All stops now have `entityId` field (136 normalized from `id`-only)

### Source Data Origins

| Source | Count |
|--------|-------|
| Curated | 336 |
| Ward Crawl 2-3 (vinhlong360) | 449 |
| Agent discovery (LLM + geocode) | 144 |
| vinhlong.gov.vn | 143 |
| vinhlong360 auto-learn | 141 |
| foody.vn | 127 |
| vinhlongtourist.vn | 49 |
| Facebook crawl | 1 |

Sources are stored as list of dicts `[{title, method}]`, not URL strings.

### Attribute Format Normalization (completed)

| Attribute | Before | After |
|-----------|--------|-------|
| Hours format | Mixed Xh/HH:MM/hyphen | All HH:MM with en-dash (156 fixed) |
| Price range dash | Mixed hyphen/en-dash | All en-dash (297 fixed, earlier session) |
| Admission capitalization | Inconsistent | Normalized (earlier session) |

### Remaining Format Variations (acceptable)

| Attribute | Variation | Reason |
|-----------|-----------|--------|
| Price range "other" (30) | "Trung bình", "Cao cấp", "Bình dân" | Qualitative tiers, not numeric ranges |
| Hours "other" (20) | "Thường tham quan ban ngày" | Places without fixed hours |

### Description Quality

- Min length: **108 chars** (craft_village)
- Median: **264 chars**
- Average: **285 chars**
- Max: **789 chars**
- Descriptions <200 chars: 335 (mostly short entity types like craft_village, dish)
- 48 descriptions had duplicated text segments → all deduplicated
- 97 template-format accommodation descriptions rewritten to clean prose
- 0 descriptions with "Liên hệ:" phone artifacts (97 cleaned)

### Attribute Completeness (key types)

| Type | Attribute | Coverage | Note |
|------|-----------|----------|------|
| restaurant | specialty | 191/191 (100%) | |
| restaurant | price_range | 108/191 (57%) | Needs external data |
| restaurant | hours | 105/191 (55%) | Needs external data |
| restaurant | phone | 1/191 (1%) | Needs external data |
| cafe | specialty | 55/55 (100%) | |
| cafe | hours | 17/55 (31%) | Needs external data |
| accommodation | price_range | 120/164 (73%) | |
| accommodation | phone | 89/164 (54%) | |
| accommodation | star_rating | 56/164 (34%) | Needs external data |

### Connectivity

- Only **1 entity** with ≤2 relationships (ben-xe-mien-tay-hcm, outside scope — HCM)
- 1 entity with 3 relationships (bia-chien-thang-thanh-phuoc) → enriched to 12
- Average 13.2 relationships per entity (counting both directions)

## Score Gap Analysis

| Deduction | Entities | Points/each | Avg impact | Actionable? |
|-----------|----------|-------------|------------|-------------|
| No images | 1745 | -10 | -10.00 | Needs IMAGE_API_KEY |
| No coordinates | 6 | -15 | -0.05 | HCM facility + 5 entities without geocodable address |
| No placeId | 1 | -10 | -0.01 | HCM entity, outside scope |

**Theoretical max without images: ~100.** Current: 90.0. Only images remain as a significant gap.

## Next Steps (Priority Order)

1. **Image generation** — 0% coverage, the ONLY remaining significant gap (-10.00 avg pts). Use `scripts/gen_image.py` + `cx/gpt-5.5-image` API.
2. **Geocoding** — ~337 entities at province centroids (178 original + 159 from geographic fixes). Google Places API would improve coverage beyond Nominatim.
3. **Experience coverage** — Trà Vinh has only 7 experiences vs 70 for Vĩnh Long (10x imbalance). Need curated TV experiences.
4. **produced_in coverage** — 156/218 products linked (71%); remaining 62 are fresh produce/processed foods without matching craft village entities.
5. **Phone/hours real data** — Some restaurants/accommodations have specialty but still lack phone/hours. Needs Google Places or manual research.

## Data Integrity Checks (all pass)

| Check | Result |
|-------|--------|
| Duplicate entity IDs | **0** |
| Self-referencing relationships | **0** |
| Dangling relationship references | **0** |
| HTML tags in descriptions | **0** |
| URLs in descriptions | **0** |
| Empty entity names | **0** |
| Empty attribute values | **0** |
| Descriptions ending without period | **0** |
| Summaries ending without punctuation | **0** |
| Phone in summaries (ĐT:) | **0** |
| Liên hệ: in descriptions | **0** |
| Template-format descriptions | **0** |
| Duplicate summaries | **0** |
| Duplicate names | **0** |
| Summary == Name (redundant) | **0** |
| Entities with only located_in | **0** (all have diverse rel types) |
