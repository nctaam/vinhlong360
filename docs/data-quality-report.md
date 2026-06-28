# Data Quality Report

Generated: 2026-06-28
Source: `web/data.json` (1746 entities, 11638 relationships, 33 itineraries)
Tool: `python scripts/validate_data.py`

## Summary

| Metric | Value | Previous (06-27) |
|--------|-------|-------------------|
| Entity quality score (avg) | **84.3/100** | 81.7 |
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
| Confidence median | 0.7 | **0.9** |
| Confidence 0.9+ | 74 | **997** |
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

## Errors

None.

## Warnings

| Code | Count | Notes |
|------|-------|-------|
| `near_asymmetric` | 4393 | By design — system handles bidirectionality automatically |
| `coordinate_clusters` | 224 clusters (1317 entities) | Ward centroids; needs real geocoding data |
| `itinerary_area_mismatch` | 59 | Multi-province itineraries legitimately cross areas |
| `rel_type_singletons` | 40 | Rare but valid relationship combos |
| `invalid_phone_format` | 18 | 1800xxxx hotline numbers (valid, not mobile format) |
| `missing_location` | 8 | 3 entities + 5 itineraries without coordinates |
| `missing_place_id` | 1 | ben-xe-mien-tay-hcm (HCM, outside VL+BT+TV scope) |
| `duplicate_source_urls` | 31 | Shared sources (vinhlong360.vn, mytour.vn) — expected |

## Entities Missing Images (QA-18)

**All 1746 entities have `images: []`** — 0% image coverage.

Images should be generated via `scripts/gen_image.py` using the `cx/gpt-5.5-image` API. No stock photos (Pexels/Unsplash), UGC, or Wikimedia images per project policy.

## Entities with Approximate Coordinates (QA-19)

**1044 entities have `coords_approximate=true`** — flagged entities whose coordinates are derived from ward centroids or placeId fallback rather than exact geocoding.

| Source | Count |
|--------|-------|
| Province centroids (VL/BT/TV) | ~408 entities |
| Ward centroids | ~589 entities |
| placeId fallback (new, this round) | 47 entities |

**Recommendation:** Real geocoding via Nominatim or similar should replace approximate coordinates. Prioritize restaurants, accommodations, and attractions.

## SEO Attribute Coverage

| Type | Coverage | Key attributes |
|------|----------|----------------|
| accommodation | 82% (135/164) | star_rating=48, price_range=93, phone=97 |
| event | 85% (57/67) | date_start=57 |
| person | 100% (35/35) | role=35 |
| dish | 62% (74/120) | specialty=5, price_range=74 |
| product | 11% (24/218) | ocop=24 |
| attraction | 24% (75/318) | admission=75 |
| nature | 13% (16/125) | admission=16 |
| experience | 11% (10/92) | admission=10 |
| restaurant | 12% (11/94) | specialty=6, price_range=9, phone=1 |
| craft_village | 2% (2/84) | specialty=1, phone=1 |
| cafe | 0% (0/38) | specialty=0, price_range=0 |

**Note:** SEO attribute gaps (phone, hours, price_range, specialty) require real business data. These cannot be programmatically generated without external data sources or manual research.

## Confidence Distribution

- Min: 0.7
- Median: **0.9** (was 0.7)
- Max: 1.0
- Entities at 0.9+: **997** (was 74)
- Entities at 0.7-0.9: 749 (was 1261)
- Entities below 0.7: **0** (was 411)

## Next Steps (Remaining Gaps)

1. **Image generation** — 0% coverage. Use `scripts/gen_image.py` + `cx/gpt-5.5-image` API.
2. **Real geocoding** — 1044 approximate coordinates. Nominatim with viewbox constraints.
3. **SEO attributes** — cafe (0%), craft_village (2%), restaurant (12%) need real business data.
4. **Product OCOP data** — only 24/218 have OCOP star rating.
