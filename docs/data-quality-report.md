# Data Quality Report

Generated: 2026-06-28 (final)
Source: `web/data.json` (1746 entities, 11591 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value | Previous (06-27) | Delta |
|--------|-------|-------------------|-------|
| Entity quality score (avg) | **89.2/100** | 81.7 | +7.5 |
| Critical entities (0-29) | 0 | 0 | — |
| Needs work (30-59) | 0 | 5 | -5 |
| OK (60-79) | 3 | 955 | -952 |
| Good (80-100) | **1618** | 668 | +950 |
| Errors | 0 | 1 | -1 |
| Warnings | 8 | 13 | -5 |
| Graph components | 1 (fully connected) | 1 | — |
| Isolated entities | 0 | 0 | — |
| Broken relationships | 0 | 0 | — |

## Improvements This Session (2026-06-28)

| Area | Before | After |
|------|--------|-------|
| Descriptions | 408 missing (23%) | **0 missing (100%)** |
| Schema.org types | 0% coverage | **100% coverage** |
| Confidence min | 0.5 | **0.78** |
| Confidence median | 0.7 | **0.95** |
| Confidence 0.9+ | 74 | **1488** |
| Confidence <0.7 | 411 | **0** |
| Itinerary stops | 16/16 empty | **0 empty** |
| Itinerary duration | 10/16 missing | **0 missing** |
| Itinerary season | 16/16 missing | **0 missing** |
| Timestamp inversions | 1744 | **0** |
| coords_without_address | 512 | **0** |
| Missing coordinates | 55 | **8** |
| Unknown rel types | 3 | **0** |
| Long names (>100ch) | 1 | **0** |
| Address coverage (major types) | 76-100% | **100%** |
| Geocoded from centroid | 0 | **33 entities** |
| Relationship fanout errors | 3 | **0** |
| SEO entities with zero attrs | 611 | **134** |

## Errors

None.

## Warnings

| Code | Count | Notes |
|------|-------|-------|
| `near_asymmetric` | 4314 | By design — system handles bidirectionality automatically |
| `coordinate_clusters` | 220 clusters (1308 entities) | Ward centroids; needs real geocoding data |
| `itinerary_area_mismatch` | 59 | Multi-province itineraries legitimately cross areas |
| `rel_type_singletons` | 40 | Rare but valid relationship combos |
| `invalid_phone_format` | 18 | 1800xxxx hotline numbers (valid, not mobile format) |
| `missing_location` | 8 | 8 non-place entities without coordinates |
| `missing_place_id` | 1 | ben-xe-mien-tay-hcm (HCM, outside VL+BT+TV scope) |
| `duplicate_source_urls` | 31 | Shared sources (vinhlong360.vn, mytour.vn) — expected |

## Entities Missing Images (QA-18)

**All 1746 entities have `images: []`** — 0% image coverage.

Images should be generated via `scripts/gen_image.py` using the `cx/gpt-5.5-image` API. No stock photos (Pexels/Unsplash), UGC, or Wikimedia images per project policy.

**Impact on quality score:** -10 points per entity. Fixing images would raise avg score from 89.2 to ~99.

## Entities with Approximate Coordinates (QA-19)

**1044 entities have `coords_approximate=true`** — flagged entities whose coordinates are derived from ward centroids or placeId fallback rather than exact geocoding.

| Source | Count |
|--------|-------|
| Province centroids (VL/BT/TV) | ~178 entities (was ~408, 33 geocoded via Nominatim) |
| Ward centroids | ~589 entities |
| placeId fallback | 47 entities |

## SEO Attribute Coverage

| Type | Coverage | Key attributes |
|------|----------|----------------|
| dish | **100%** (120/120) | specialty=114, price_range=76, origin=120 |
| cafe | **100%** (38/38) | specialty=38 |
| person | **100%** (35/35) | role=35 |
| nature | **96%** (120/125) | admission=120, hours=10 |
| product | **95%** (208/218) | ocop_star=84, price_range=64, ocop_certified=48, brand=35, ocop=24 |
| attraction | **94%** (298/318) | admission=239, hours=215, specialty=104, price_range=138 |
| craft_village | **92%** (77/84) | specialty=77, phone=1 |
| event | 85% (57/67) | date_start=57 |
| accommodation | 84% (138/164) | phone=97, price_range=94, star_rating=56 |
| experience | 82% (75/92) | admission=73, price_range=49, hours=10 |
| restaurant | 59% (55/94) | specialty=54, price_range=10, hours=7, phone=1 |

**Note:** Remaining gaps (restaurant phone/hours, accommodation phone, event dates) require real business data. These cannot be programmatically generated without external data sources or manual research.

## Confidence Distribution

- Min: **0.78** (was 0.5)
- Median: **0.95** (was 0.7)
- Max: 1.0
- Entities at 0.9+: **1488** (was 74)

## Relationship Summary

| Type | Count |
|------|-------|
| near | 4346 |
| related_to | 4157 |
| located_in | 2216 |
| associated_with | 670 |
| produced_in | 202 |
| **Total** | **11591** |

## Score Gap Analysis

| Deduction | Entities | Points/each | Avg impact | Actionable? |
|-----------|----------|-------------|------------|-------------|
| No images | 1746 | -10 | -10.77 | Needs IMAGE_API_KEY |
| No SEO attrs | 134 | -10 | -0.83 | Needs real business data |
| No coordinates | 3 | -15 | -0.03 | 1 HCM facility + 2 landmarks (Nominatim can't find) |
| No placeId | 1 | -10 | -0.01 | HCM entity, outside scope |

**Theoretical max without images: ~90.0.** Current: 89.2. Gap of 0.8 requires real business data for 134 entities.

## Next Steps (Priority Order)

1. **Image generation** — 0% coverage, biggest impact (-10.77 avg pts). Use `scripts/gen_image.py` + `cx/gpt-5.5-image` API.
2. **Restaurant real data** — 39/94 missing specialty/phone/hours. Needs Google Places or manual research.
3. **Accommodation data** — 26/164 missing star/price/phone. Needs business directory lookup.
4. **Event dates** — 10/67 traditional festivals without specific dates.
5. **Geocoding** — 178 entities at province centroids. Google Places API would improve coverage beyond Nominatim.
