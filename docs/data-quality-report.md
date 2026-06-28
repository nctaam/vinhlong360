# Data Quality Report

Generated: 2026-06-28 (final)
Source: `web/data.json` (1746 entities, 11591 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value | Previous (06-27) | Delta |
|--------|-------|-------------------|-------|
| Entity quality score (avg) | **89.6/100** | 81.7 | +7.9 |
| Critical entities (0-29) | 0 | 0 | — |
| Needs work (30-59) | 0 | 5 | -5 |
| OK (60-79) | 2 | 955 | -953 |
| Good (80-100) | **1619** | 668 | +951 |
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
| Confidence min | 0.5 | **0.80** |
| Confidence median | 0.7 | **0.95** |
| Confidence 0.9+ | 74 | **1575** |
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
| Relationship fanout errors | 3 | **0** |
| SEO entities with zero attrs | 611 | **65** |
| History architectural_style | 0 | **130 entities** |
| Admission capitalization | inconsistent | **Normalized** |
| Price range dash format | mixed (–/-) | **All en-dash (–)** |
| Geocoded from centroid | 0 | **34 entities** |

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
| `missing_location` | 7 | 2 non-place + 5 itinerary entities without coordinates |
| `missing_place_id` | 1 | ben-xe-mien-tay-hcm (HCM, outside VL+BT+TV scope) |
| `duplicate_source_urls` | 31 | Shared sources (vinhlong360.vn, mytour.vn) — expected |

## Entities Missing Images (QA-18)

**All 1746 entities have `images: []`** — 0% image coverage.

Images should be generated via `scripts/gen_image.py` using the `cx/gpt-5.5-image` API. No stock photos (Pexels/Unsplash), UGC, or Wikimedia images per project policy.

**Impact on quality score:** -10 points per entity. Fixing images would raise avg score from 89.6 to ~99.

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
| nature | **100%** (125/125) | admission=125, hours=10 |
| product | **100%** (218/218) | ocop_star=84, price_range=64, ocop_certified=48, brand=45, ocop=24 |
| attraction | **100%** (318/318) | admission=256, hours=215, specialty=109, price_range=138 |
| craft_village | **100%** (84/84) | specialty=84, phone=1 |
| event | **100%** (67/67) | date_start=67 |
| experience | **100%** (92/92) | admission=89, price_range=50, hours=10 |
| drink | **100%** (1/1) | price_range=1 |
| accommodation | 84% (138/164) | phone=97, price_range=94, star_rating=56 |
| restaurant | 59% (55/94) | specialty=54, price_range=10, hours=7, phone=1 |

**Note:** Remaining gaps (restaurant 39, accommodation 26) require real business data (phone/hours/star ratings). These cannot be programmatically generated without external data sources or manual research. All other SEO types are at 100% coverage.

## Confidence Distribution

- Min: **0.80** (was 0.5)
- Median: **0.95** (was 0.7)
- Max: 1.0
- Entities at 0.9+: **1575** (was 74)

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
| No images | 1746 | -10 | -10.00 | Needs IMAGE_API_KEY |
| No SEO attrs | 65 | -10 | -0.40 | Restaurant (39) + accommodation (26) need real data |
| No coordinates | 2 | -15 | -0.02 | 1 HCM facility + 1 Khmer pagoda (Nominatim can't find) |
| No placeId | 1 | -10 | -0.01 | HCM entity, outside scope |

**Theoretical max without images: ~90.0.** Current: 89.6. Gap of 0.4 requires real business data for 65 entities (restaurant phone/hours, accommodation star/phone).

## Next Steps (Priority Order)

1. **Image generation** — 0% coverage, biggest impact (-10.00 avg pts). Use `scripts/gen_image.py` + `cx/gpt-5.5-image` API.
2. **Restaurant real data** — 39/94 missing specialty/phone/hours. Needs Google Places or manual research.
3. **Accommodation data** — 26/164 missing star/price/phone. Needs business directory lookup.
4. **Geocoding** — 178 entities at province centroids. Google Places API would improve coverage beyond Nominatim.
