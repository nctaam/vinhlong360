# Data Quality Report

Generated: 2026-06-28 (updated — produced_in + phone + far_near fix)
Source: `web/data.json` (1746 entities, 11545 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value | Previous (06-27) | Delta |
|--------|-------|-------------------|-------|
| Entity quality score (avg) | **90.0/100** | 81.7 | +8.3 |
| Critical entities (0-29) | 0 | 0 | — |
| Needs work (30-59) | 0 | 5 | -5 |
| OK (60-79) | 2 | 955 | -953 |
| Good (80-100) | **1619** | 668 | +951 |
| Errors | 0 | 1 | -1 |
| Warnings | 7 | 13 | -6 |
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
| produced_in coverage | 137/218 products | **153/218 products** (+16 curated) |
| Invalid phone numbers | 9 masked/incomplete | **0** (removed) |
| Far near rels (>50km) | 62 centroid artifacts | **0** (removed) |

## Errors

None.

## Warnings

| Code | Count | Notes |
|------|-------|-------|
| `near_asymmetric` | 4252 | By design — system handles bidirectionality automatically |
| `coordinate_clusters` | 189 clusters (1365 entities) | Ward/province centroids; needs real geocoding data |
| `itinerary_area_mismatch` | 59 | Multi-province itineraries legitimately cross areas |
| `rel_type_singletons` | 40 | Rare but valid relationship combos |
| `missing_location` | 7 | 2 non-place + 5 itinerary entities without coordinates |
| `missing_place_id` | 1 | ben-xe-mien-tay-hcm (HCM, outside VL+BT+TV scope) |
| `data_js_unknown_shape` | 1 | web/data.js format — cosmetic |

## Entities Missing Images (QA-18)

**All 1746 entities have `images: []`** — 0% image coverage.

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
| dish | **100%** (120/120) | specialty=114, price_range=76, origin=120 |
| cafe | **100%** (38/38) | specialty=38 |
| person | **100%** (35/35) | role=35 |
| nature | **100%** (125/125) | admission=125, hours=10 |
| product | **100%** (218/218) | ocop_star=84, price_range=64, ocop_certified=48, brand=45, ocop=24 |
| attraction | **100%** (318/318) | admission=256, hours=215, specialty=109, price_range=138 |
| craft_village | **100%** (84/84) | specialty=84, phone=1 |
| event | **100%** (67/67) | date_start=67 |
| experience | **100%** (92/92) | admission=89, price_range=50, hours=10 |
| drink | **100%** (1/1) | price_range=1 |
| accommodation | **100%** (164/164) | phone=97, price_range=120, star_rating=56 |
| restaurant | **100%** (94/94) | specialty=94, price_range=10, hours=7, phone=1 |

**All 12 SEO entity types are at 100% coverage.** No entities are missing all required SEO attributes.

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
| near | 4284 |
| related_to | 4157 |
| located_in | 2216 |
| associated_with | 670 |
| produced_in | 218 |
| **Total** | **11545** |

## Deep Research Findings

### Coverage Imbalance (entities per area, excluding place)

| Type | VL | BT | TV | Ratio | Severity |
|------|-----|-----|-----|-------|----------|
| experience | 70 | 15 | 7 | 10.0x | Critical |
| person | 23 | 6 | 6 | 3.8x | High |
| accommodation | 99 | 29 | 36 | 3.4x | Medium |

**Impact:** TV (Trà Vinh) is severely underrepresented in experiences. After 3-province merge, users searching for experiences in the former TV area will find very few options.

### Duplicate Detection

1 near-duplicate found: "Nhà hàng Hàm Luông" (`nha-hang-ham-luong-ben-tre`) and "Hàm Luông" (`ham-luong`) — both at 200C Hùng Vương, Bến Tre. Same restaurant listed under different names.

### Relationship Quality

- Dangling references: **0** (clean)
- Self-references: **0** (clean)
- Duplicate relationships: **0** (clean)
- Far "near" relationships (>50km): **0** (62 centroid artifacts removed)

### Itinerary Quality

- 33 total itineraries, 185 stops
- **174/185 stops** (94%) linked to existing entities
- 11 unlinked stops are generic activities (departure, pool, dinner) without corresponding entities — legitimate
- 21 itineraries use stop `id` field, 12 newer ones use `entityId` field

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

## Score Gap Analysis

| Deduction | Entities | Points/each | Avg impact | Actionable? |
|-----------|----------|-------------|------------|-------------|
| No images | 1746 | -10 | -10.00 | Needs IMAGE_API_KEY |
| No coordinates | 2 | -15 | -0.02 | 1 HCM facility + 1 Khmer pagoda (Nominatim can't find) |
| No placeId | 1 | -10 | -0.01 | HCM entity, outside scope |

**Theoretical max without images: ~100.** Current: 90.0. Only images remain as a significant gap.

## Next Steps (Priority Order)

1. **Image generation** — 0% coverage, the ONLY remaining significant gap (-10.00 avg pts). Use `scripts/gen_image.py` + `cx/gpt-5.5-image` API.
2. **Geocoding** — ~337 entities at province centroids (178 original + 159 from geographic fixes). Google Places API would improve coverage beyond Nominatim.
3. **Experience coverage** — Trà Vinh has only 7 experiences vs 70 for Vĩnh Long (10x imbalance). Need curated TV experiences.
4. **Merge duplicate** — "Nhà hàng Hàm Luông" / "Hàm Luông" at same address in Bến Tre.
5. **produced_in coverage** — 153/218 products linked; remaining 65 are fresh produce without matching craft villages.
6. **Phone/hours real data** — Some restaurants/accommodations have specialty but still lack phone/hours. Needs Google Places or manual research.
