# Data Quality Report

Generated: 2026-06-28 (final)
Source: `web/data.json` (1746 entities, 11591 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value | Previous (06-27) |
|--------|-------|-------------------|
| Entity quality score (avg) | **84.9/100** | 81.7 |
| Critical entities (0-29) | 0 | 0 |
| Needs work (30-59) | 0 | 5 |
| OK (60-79) | 8 | 955 |
| Good (80-100) | **1613** | 668 |
| Errors | 0 | 1 |
| Warnings | 8 | 13 |
| Graph components | 1 (fully connected) | 1 |
| Isolated entities | 0 | 0 |
| Broken relationships | 0 | 0 |

## Improvements This Round (2026-06-28)

| Area | Before | After |
|------|--------|-------|
| Descriptions | 408 missing (23%) | **0 missing (100%)** |
| Schema.org types | 0% coverage | **100% coverage** |
| Confidence median | 0.7 | **0.95** |
| Confidence min | 0.5 | **0.78** |
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
| Restaurant specialty | 6% (6/94) | **53% (50/94)** |
| Craft village specialty | 1% (1/84) | **71% (60/84)** |
| Cafe specialty | 0% (0/38) | **11% (4/38)** |
| Geocoded from centroid | 0 | **33 entities** |
| Relationship fanout errors | 3 | **0** |

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

## Entities with Approximate Coordinates (QA-19)

**1044 entities have `coords_approximate=true`** — flagged entities whose coordinates are derived from ward centroids or placeId fallback rather than exact geocoding.

| Source | Count |
|--------|-------|
| Province centroids (VL/BT/TV) | ~178 entities (was ~408, 33 geocoded via Nominatim) |
| Ward centroids | ~589 entities |
| placeId fallback | 47 entities |

**Recommendation:** Real geocoding via Nominatim or similar should replace approximate coordinates. Prioritize restaurants, accommodations, and attractions. Note: generic names (chain restaurants, generic cafes) have low Nominatim hit rate.

## SEO Attribute Coverage

| Type | Coverage | Key attributes |
|------|----------|----------------|
| person | 100% (35/35) | role=35 |
| event | 85% (57/67) | date_start=57 |
| accommodation | 83% (136/164) | star_rating=48, price_range=94, phone=97 |
| craft_village | 73% (61/84) | specialty=60, phone=1 |
| dish | 63% (76/120) | specialty=5, price_range=76 |
| restaurant | 54% (51/94) | specialty=50, price_range=10, phone=1, hours=7 |
| attraction | 24% (75/318) | admission=75 |
| nature | 13% (16/125) | admission=16 |
| cafe | 11% (4/38) | specialty=4 |
| product | 11% (24/218) | ocop_star=24 |
| experience | 11% (10/92) | admission=10 |

**Note:** SEO attribute gaps (phone, hours, price_range for cafe/restaurant) require real business data. These cannot be programmatically generated without external data sources or manual research.

## Confidence Distribution

- Min: **0.78** (was 0.5)
- Median: **0.95** (was 0.7)
- Max: 1.0
- Entities at 0.9+: **1488** (was 74)
- Entities at 0.78-0.9: 133 (was 1261 at 0.7-0.9)
- Entities below 0.7: **0** (was 411)

## Relationship Summary

| Type | Count |
|------|-------|
| near | 4346 |
| related_to | 4157 |
| located_in | 2216 |
| associated_with | 670 |
| produced_in | 202 |
| **Total** | **11591** |

## Next Steps (Remaining Gaps)

1. **Image generation** — 0% coverage. Biggest quality gap. Use `scripts/gen_image.py` + `cx/gpt-5.5-image` API (requires IMAGE_API_KEY).
2. **Real geocoding** — 178 entities still at province centroids. Nominatim has diminishing returns for generic names; Google Places API would improve coverage.
3. **SEO attributes** — cafe (11%), experience (11%), product (11%) need real business data.
4. **Product OCOP data** — only 24/218 have OCOP star rating. Requires OCOP registry data.
5. **Phone/hours** — restaurant (1 phone, 7 hours), cafe (0/0). Needs manual research or business directory.
